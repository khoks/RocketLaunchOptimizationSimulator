"""The shared read-only run-data module (run_data.py, SP2 step A1) on synthetic results
directories under tmp_path, and on real event rows built with the planar planner.

- Readers: a missing file or a non-mapping reads as {}; NaN literals and UTF-8 text are
  read; a corrupt file is one RunDataError message only when the caller asks; nothing
  is ever written.
- Compatibility: every name plots.py and replay.py had is the run_data object (or a
  wrapper that keeps its error class); run_data imports no drawing or writer module.
- Directory check, run names, selection and the five roles of ``run_source``; the run's
  own vehicle block and its masses.
- Series: the replay's sort and keep-last read against animate's read as written; the
  common-clock grid and the resampling, against hand-computed values; a pinned digest
  of the data (series, phases, events) of the replay page's ``runs`` block, computed
  with the code of the SP2 start commit.
- Events: every row of an eight-column events.csv; the mass before and after each drop
  for the four ways the planner logs a fairing drop, on hand-written rows (the recorded
  pad's numbers) and on rows the planner itself produced.
- The one output-path rule, and the two deliberate changes of ``launchsim animate``
  (D-SP2-14): the stricter output-path rule and the sweep-point message.

Expected values are closed forms or the fixtures' own numbers; no simulation here runs
longer than a second (the stage-2 guidance solve of the insertion cases, once)."""

from __future__ import annotations

import ast
import copy
import dataclasses
import hashlib
import json
import math
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
import yaml

from launchsim import metrics_planar, plots, replay, results_io, run_data, sim
from launchsim.atmosphere import ambient_scalar
from launchsim.cli import main
from launchsim.config import PLANAR_2D, LtgConfig, SearchConfig, VehicleConfig
from launchsim.constants import MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M
from launchsim.dynamics import PLANAR_LAYOUT, InverseSquareGravity
from launchsim.guidance import DeltaSolveSettings, GuidanceSpec, LtgSettings, solve_delta_for_gamma
from launchsim.orbit import TargetOrbit
from launchsim.phases import IgnitionSpec, IntegratorSettings, RunTrace
from launchsim.phases.planar import (
    COAST_STAGING,
    LTG_BURN,
    PlanarEnvironment,
    PlanarPlanner,
    fmh_rate_W_m2,
)
from launchsim.vehicle import Vehicle

# ---------------------------------------------------------------- synthetic directory
#
# The SYNTH_* constants and the _synth_* functions are self-contained on purpose: they
# use only json, math and Path, and nothing of launchsim, so the scratch script that
# computed RUNS_DIGESTS could build the same directory under the code of the SP2 start
# commit, which has no run_data module.

SYNTH_EXPERIMENT = "synth_run_data_2d"
SYNTH_TIMESTAMP = "20260101T000000Z"
SYNTH_PUSH_S = 2.0371
"""Length of the push (or of the pad's hold-down) [s]: the series starts at -SYNTH_PUSH_S,
a time with digits beyond the page's TIME_DECIMALS, so the first sample time and the
first event time are rounded on the page (to -2.037); every other row lies on the 0.5 s
grid from SYNTH_GRID_START_S."""
SYNTH_OFFSET_S = SYNTH_PUSH_S
"""t_s - t_rel_release_s of every synthetic run [s] (t_s starts at 0)."""
SYNTH_STEP_S = 0.5
"""Spacing of the synthetic time-series rows [s] from SYNTH_GRID_START_S on."""
SYNTH_GRID_START_S = -2.0
"""First time of the SYNTH_STEP_S row grid [s after release]; the row at -SYNTH_PUSH_S
precedes it (row times -2.0371, -2.0, -1.5, ..., 60.0)."""
SYNTH_T_KICK_END_S = 12.4937
"""End of the pitch kick [s after release]: off the row grid, with digits beyond
TIME_DECIMALS that round up on the page (to 12.494)."""
SYNTH_T_STAGING_S = 40.0
"""Staging [s after release]: the time series holds two rows at this time."""
SYNTH_T_IGN2_S = 41.0
"""Stage-2 ignition [s after release]."""
SYNTH_T_FAIRING_S = 50.2713
"""Fairing drop [s after release], in the stage-2 burn: off the row grid, with digits
beyond TIME_DECIMALS that round down on the page (to 50.271)."""
SYNTH_T_END_S = 60.0
SYNTH_DEPTH_M = 50.0
"""Depth of the synthetic silo [m]."""
SYNTH_EXIT_SPEED_MPS = 50.0
SYNTH_M0_KG = 1000.0
SYNTH_BURN1_KGPS = 10.0
SYNTH_BURN2_KGPS = 5.0
SYNTH_STAGE_DROP_KG = 100.0
"""Mass the synthetic staging row drops [kg]: 600 kg before the map, 500 kg after."""
SYNTH_KICK_DOWNRANGE_M = -0.157654
"""Downrange of the kick_start event [m]: small and negative, as the recorded pad's is
(-0.157654 m), so the replay page's x_km of that event is the token -0.0."""
SYNTH_SERIES_COLUMNS = (
    "t_s",
    "t_rel_release_s",
    "phase",
    "alt_m",
    "downrange_m",
    "speed_rel_mps",
    "felt_axial_g",
    "q_pa",
    "m_kg",
    "gamma_rel_rad",
    "mach",
    "stage",
    "extra",
)
"""Header of a synthetic timeseries.csv: the replay's eleven columns, the stage and one
column no reader asks for."""
SYNTH_EVENT_COLUMNS = (
    "t_s",
    "event",
    "phase",
    "stage",
    "alt_m",
    "downrange_m",
    "speed_rel_mps",
    "m_kg",
)
"""Header of a synthetic events.csv: the eight columns of the fixtures of
tests/test_animate.py and tests/test_replay.py (no speed_inertial_mps, no gamma_rel_rad)."""
SYNTH_RUNS = {
    "pad": False,
    "silo": True,
    "silo__aero_bound": True,
    "pad__aero_bound": False,
    "alt_low": False,
    "silo_s1": True,
    "silo_s1__pad": False,
    "pad__offload_stage1": False,
}
"""Run folder -> assisted: the experiment runs pad (baseline) and silo; the bound re-run
silo__aero_bound with its paired baseline pad__aero_bound; the case alt_low; and the
offload block's case silo_s1, its paired pad and the stage-1 pad control."""
SYNTH_P_REF_KG = 1000.0
SYNTH_OFFLOAD_KG = 41262.9
SYNTH_PAIRED_PAD_KG = 958.6
SYNTH_STAGE1_DRY_T = 22.2
SYNTH_STAGE1_PROPELLANT_T = 410.9
SYNTH_STAGE2_DRY_T = 4.0
SYNTH_STAGE2_PROPELLANT_T = 107.5
SYNTH_FAIRING_T = 1.7
SYNTH_PAYLOAD_T = 22.8
SYNTH_OFFLOADED_PROPELLANT_T = 369.6371
"""Stage-1 load of the offloaded vehicle block [t]: 410.9 t less the 41.2629 t offload."""
SYNTH_LIGHT_DRY_T = 20.0
"""Stage-1 dry mass of the case's own vehicle (toy_2d_light) [t]."""


SYNTH_DECIMALS = 6
"""Decimals every number of a synthetic row is rounded to (``_synth_clean``): the
shortest repr of such a value is its decimal text, which the CSV reader parses back to
the same float (a 17-digit repr such as 14.530800000000001 need not survive pandas'
default parser), so a test may compare a cell read back with the builder's own value
exactly. Far below any tolerance of the closed-form checks."""


def _synth_clean(row: dict[str, Any]) -> dict[str, Any]:
    """``row`` with every float rounded to SYNTH_DECIMALS (NaN stays NaN)."""
    return {k: round(v, SYNTH_DECIMALS) if isinstance(v, float) else v for k, v in row.items()}


def _synth_row(t_rel: float, assist: bool, staged: bool) -> dict[str, Any]:
    """One synthetic time-series row at t_rel [s after release]. Before release: a
    vented-shaft push from -SYNTH_DEPTH_M (q and Mach undefined) for an assisted run, a
    hold on the pad otherwise. After: a climb in polynomials of t_rel (alt 10 t^2 m,
    downrange t^3 m, speed 50 + 20 t m/s, q 25 t (60 - t) Pa), stage 1 burning
    SYNTH_BURN1_KGPS; ``staged`` rows (from the second row at SYNTH_T_STAGING_S on) are
    SYNTH_STAGE_DROP_KG lighter, coast to SYNTH_T_IGN2_S, then burn SYNTH_BURN2_KGPS.
    Every number is rounded to SYNTH_DECIMALS."""
    base = {"t_s": t_rel + SYNTH_OFFSET_S, "t_rel_release_s": t_rel, "extra": 7.0}
    if t_rel < 0.0:
        frac = 1.0 + t_rel / SYNTH_PUSH_S
        return _synth_clean(
            {
                **base,
                "phase": "ASSIST" if assist else "HOLD",
                "stage": "stage1",
                "alt_m": -SYNTH_DEPTH_M * (1.0 - frac * frac) if assist else 0.0,
                "downrange_m": 0.0,
                "speed_rel_mps": SYNTH_EXIT_SPEED_MPS * frac if assist else 0.0,
                "felt_axial_g": 4.0 if assist else 1.0,
                "q_pa": math.nan if assist else 0.0,
                "m_kg": SYNTH_M0_KG,
                "gamma_rel_rad": math.pi / 2,
                "mach": math.nan if assist else 0.0,
            }
        )
    if staged:
        phase = "COAST_STAGING" if t_rel < SYNTH_T_IGN2_S else "LTG_BURN"
        burned = SYNTH_BURN1_KGPS * SYNTH_T_STAGING_S + SYNTH_STAGE_DROP_KG
        burned += SYNTH_BURN2_KGPS * max(0.0, t_rel - SYNTH_T_IGN2_S)
    else:
        phase = "GRAVITY_TURN"
        burned = SYNTH_BURN1_KGPS * t_rel
    return _synth_clean(
        {
            **base,
            "phase": phase,
            "stage": "stage2" if staged else "stage1",
            "alt_m": 10.0 * t_rel * t_rel,
            "downrange_m": t_rel**3,
            "speed_rel_mps": SYNTH_EXIT_SPEED_MPS + 20.0 * t_rel,
            "felt_axial_g": 1.5 + t_rel / 40.0,
            "q_pa": 25.0 * t_rel * (SYNTH_T_END_S - t_rel),
            "m_kg": SYNTH_M0_KG - burned,
            "gamma_rel_rad": math.pi / 2 - t_rel / SYNTH_T_END_S,
            "mach": t_rel / 10.0,
        }
    )


def _synth_series_rows(assist: bool) -> list[dict[str, Any]]:
    """The rows of a synthetic timeseries.csv in file order: the first at -SYNTH_PUSH_S,
    then every SYNTH_STEP_S from SYNTH_GRID_START_S to SYNTH_T_END_S, with two rows at
    SYNTH_T_STAGING_S (the state before the staging map, then after it), as a phase
    boundary writes them: SYNTH_SERIES_ROWS rows."""
    count = round((SYNTH_T_END_S - SYNTH_GRID_START_S) / SYNTH_STEP_S)
    rows = [_synth_row(-SYNTH_PUSH_S, assist, False)]
    for k in range(count + 1):
        t_rel = k * SYNTH_STEP_S + SYNTH_GRID_START_S
        if t_rel == SYNTH_T_STAGING_S:
            rows.append(_synth_row(t_rel, assist, False))
        rows.append(_synth_row(t_rel, assist, t_rel >= SYNTH_T_STAGING_S))
    return rows


SYNTH_SERIES_ROWS = round((SYNTH_T_END_S - SYNTH_GRID_START_S) / SYNTH_STEP_S) + 3
"""Rows of a synthetic timeseries.csv: the grid rows (both ends included), the row at
-SYNTH_PUSH_S and the second row at staging."""


def _synth_events(assist: bool) -> list[dict[str, Any]]:
    """The rows of a synthetic events.csv (SYNTH_EVENT_COLUMNS) in file order: each
    event takes its state from ``_synth_row`` at its time; kick_start has the downrange
    SYNTH_KICK_DOWNRANGE_M and staging is logged in COAST_STAGING. Three times carry
    digits beyond TIME_DECIMALS (the first row's, SYNTH_T_KICK_END_S, SYNTH_T_FAIRING_S),
    so the page's rounding of event times, and of the polynomial state at an off-grid
    time, is exercised."""
    listed: list[tuple[str, float, bool]] = [
        ("push_start" if assist else "ignition", -SYNTH_PUSH_S, False),
        ("release", 0.0, False),
        ("ignition" if assist else "liftoff", 0.5, False),
        ("kick_start", 1.0, False),
        ("kick_end", SYNTH_T_KICK_END_S, False),
        ("propellant", SYNTH_T_STAGING_S, False),
        ("staging", SYNTH_T_STAGING_S, True),
        ("ignition", SYNTH_T_IGN2_S, True),
        ("fairing", SYNTH_T_FAIRING_S, True),
        ("cutoff", SYNTH_T_END_S, True),
        ("end", SYNTH_T_END_S, True),
    ]
    out = []
    for event, t_rel, staged in listed:
        row = _synth_row(t_rel, assist, staged)
        record = {"event": event, **{c: row[c] for c in SYNTH_EVENT_COLUMNS if c != "event"}}
        if event == "kick_start":
            record["downrange_m"] = SYNTH_KICK_DOWNRANGE_M
        out.append(record)
    return out


def _synth_csv(columns: tuple[str, ...], rows: list[dict[str, Any]]) -> str:
    """CSV text of ``rows``: floats by repr (the shortest text that reads back equal),
    NaN as nan."""
    lines = [",".join(columns)]
    for row in rows:
        cells = [row[c] if isinstance(row[c], str) else repr(float(row[c])) for c in columns]
        lines.append(",".join(cells))
    return "\n".join(lines) + "\n"


def _synth_write_run(run_dir: Path, name: str, assist: bool) -> None:
    """<run_dir>/<name>/timeseries.csv and events.csv of one synthetic run."""
    folder = run_dir / name
    folder.mkdir(parents=True)
    series = _synth_csv(SYNTH_SERIES_COLUMNS, _synth_series_rows(assist))
    (folder / "timeseries.csv").write_text(series, encoding="utf-8", newline="\n")
    events = _synth_csv(SYNTH_EVENT_COLUMNS, _synth_events(assist))
    (folder / "events.csv").write_text(events, encoding="utf-8", newline="\n")


def _synth_record(assist: bool, payload_kg: float) -> dict[str, Any]:
    """metrics.json record of a synthetic run (its drag loss NaN, as a failed term
    writes it)."""
    record: dict[str, Any] = {
        "status": "inserted",
        "payload_kg": payload_kg,
        "startup_kind_stage1": "ramp",
        "t_startup_s_stage1": 2.0,
        "t_ign_rel_release_s_stage1": 0.5 if assist else -2.0,
        "max_q_pa": 22500.0,
        "peak_felt_axial_g_flight": 3.0,
        "gravity_loss_mps": 1400.0,
        "drag_loss_mps": math.nan,
        "steering_loss_mps": 90.0,
        "back_pressure_loss_mps": 50.0,
        "assist_model": "constant_accel" if assist else "none",
        "fairing_drop": "in the stage-2 burn (heating event)",
    }
    if assist:
        record.update(
            exit_speed_mps=SYNTH_EXIT_SPEED_MPS,
            felt_g_track_peak=4.0,
            push_time_s=SYNTH_PUSH_S,
            track_start_altitude_m=-SYNTH_DEPTH_M,
            net_accel_g=3.0,
        )
    return record


def _synth_run_block(
    assist: bool, orbit_km: float = 200.0, rotation: bool = True
) -> dict[str, Any]:
    """The ``run`` block of a resolved_config.yaml entry of a synthetic run."""
    block: dict[str, Any] = {"model": "none"}
    if assist:
        block = {
            "model": "constant_accel",
            "net_accel_g": 3.0,
            "stroke_m": SYNTH_DEPTH_M,
            "carriage_mass_t": 0,
            "shaft": "vented",
            "track": {"angle_deg": 90, "exit_altitude_m": 0},
        }
    return {
        "site": {"latitude_deg": 28.5, "azimuth_deg": 90, "include_rotation": rotation},
        "planar": {"target_orbit": {"kind": "circular", "altitude_km": orbit_km}},
        "assist": block,
    }


def _synth_quantity(value: float) -> dict[str, Any]:
    """A vehicle-file number: ``{value, assumed: true}``."""
    return {"value": value, "assumed": True}


def _synth_vehicle(
    name: str = "toy_2d",
    stage1_dry_t: float = SYNTH_STAGE1_DRY_T,
    stage1_propellant_t: float = SYNTH_STAGE1_PROPELLANT_T,
) -> dict[str, Any]:
    """A complete raw vehicle block (the vehicle file's schema, tonnes): two stages, a
    fairing and a payload, and no ``fairing_drop`` key."""
    return {
        "name": name,
        "stages": [
            {
                "name": "stage1",
                "dry_mass_t": _synth_quantity(stage1_dry_t),
                "propellant_mass_t": _synth_quantity(stage1_propellant_t),
                "engine": {
                    "count": _synth_quantity(9),
                    "thrust_vac_kN": _synth_quantity(914.1),
                    "isp_vac_s": _synth_quantity(311),
                },
            },
            {
                "name": "stage2",
                "dry_mass_t": _synth_quantity(SYNTH_STAGE2_DRY_T),
                "propellant_mass_t": _synth_quantity(SYNTH_STAGE2_PROPELLANT_T),
                "engine": {
                    "count": _synth_quantity(1),
                    "thrust_vac_kN": _synth_quantity(981),
                    "isp_vac_s": _synth_quantity(348),
                },
            },
        ],
        "fairing_mass_t": _synth_quantity(SYNTH_FAIRING_T),
        "payload_mass_t": _synth_quantity(SYNTH_PAYLOAD_T),
    }


def _synth_metrics() -> dict[str, Any]:
    """metrics.json of the synthetic directory: every section ``run_source`` reads."""
    comparison = {
        "payload_delta_kg": 100.0,
        "ideal_screening_payload_at_release_speed_at_pbase_kg": 60.0,
        "payload_delta_upper_bound": False,
    }
    bound = {
        "bound": "aero_bound",
        "of": "silo",
        "run": "silo__aero_bound",
        "paired_baseline": "pad__aero_bound",
        "overrides": {"vehicle.aero.reference_area_m2": 21.24},
        "metrics": _synth_record(True, 1090.0),
        "paired_baseline_metrics": _synth_record(False, 990.0),
        "comparison_vs_paired_baseline": {**comparison, "payload_delta_kg": 90.0},
    }
    offload = {
        "reference": "pad",
        "reference_payload_kg": SYNTH_P_REF_KG,
        "cases": [
            {
                "name": "silo_s1",
                "run": "silo_s1",
                "of": "silo",
                "kind": "solve",
                "mode": "stage1",
                "total_offload_kg": SYNTH_OFFLOAD_KG,
                "stage1_fraction": 0.1004,
                "total_fraction": 0.0796,
                "payload_kg": SYNTH_P_REF_KG,
                "paired_pad": {"run": "silo_s1__pad", "payload_kg": SYNTH_PAIRED_PAD_KG},
            }
        ],
        "pad_controls": [
            {
                "mode": "stage1",
                "run": "pad__offload_stage1",
                "status": "no_offload",
                "offload_kg": 0.0,
            }
        ],
        "runs": {
            "silo_s1": _synth_record(True, SYNTH_P_REF_KG),
            "silo_s1__pad": _synth_record(False, SYNTH_PAIRED_PAD_KG),
            "pad__offload_stage1": _synth_record(False, SYNTH_P_REF_KG),
        },
    }
    return {
        "experiment": SYNTH_EXPERIMENT,
        "timestamp_utc": SYNTH_TIMESTAMP,
        "model": "planar_2d",
        "git": {"hash": "abc123", "dirty": False},
        "baseline": "pad",
        "runs": {"pad": _synth_record(False, 1000.0), "silo": _synth_record(True, 1100.0)},
        "comparison": {"silo": comparison},
        "bounds": [bound],
        "cases": {"alt_low": _synth_record(False, 1050.0)},
        "offload": offload,
    }


def _synth_config() -> dict[str, Any]:
    """resolved_config.yaml of the synthetic directory: the experiment's vehicle block,
    and per run an entry with its ``run`` block and, where it flew another vehicle, its
    own ``vehicle`` block (the offloaded load, the case's lighter stage); the pad
    control's entry has ``run`` only, as results_io writes a zero-offload control."""
    offloaded = _synth_vehicle(stage1_propellant_t=SYNTH_OFFLOADED_PROPELLANT_T)
    return {
        "experiment": SYNTH_EXPERIMENT,
        "vehicle": _synth_vehicle(),
        "runs": {
            "pad": {"run": _synth_run_block(False)},
            "silo": {"run": _synth_run_block(True)},
        },
        "bound_runs": {
            "silo__aero_bound": {"run": _synth_run_block(True), "vehicle": _synth_vehicle()},
            "pad__aero_bound": {"run": _synth_run_block(False), "vehicle": _synth_vehicle()},
        },
        "cases": {
            "alt_low": {
                "run": _synth_run_block(False, orbit_km=150.0, rotation=False),
                "vehicle": _synth_vehicle("toy_2d_light", stage1_dry_t=SYNTH_LIGHT_DRY_T),
            }
        },
        "offload_runs": {
            "silo_s1": {"run": _synth_run_block(True), "vehicle": offloaded},
            "silo_s1__pad": {"run": _synth_run_block(False), "vehicle": offloaded},
            "pad__offload_stage1": {"run": _synth_run_block(False)},
        },
    }


def _synth_run_dir(root: Path) -> Path:
    """Write the synthetic results/<experiment>/<timestamp> directory under ``root`` and
    return it: SYNTH_RUNS with their two CSV files, a ``plots`` folder (no time series:
    not a run), metrics.json (with a NaN literal) and resolved_config.yaml (written as
    JSON, which is YAML)."""
    run_dir = root / "results" / SYNTH_EXPERIMENT / SYNTH_TIMESTAMP
    run_dir.mkdir(parents=True)
    for name, assist in SYNTH_RUNS.items():
        _synth_write_run(run_dir, name, assist)
    (run_dir / "plots").mkdir()
    metrics = json.dumps(_synth_metrics())
    (run_dir / "metrics.json").write_text(metrics, encoding="utf-8", newline="\n")
    config = json.dumps(_synth_config())
    (run_dir / "resolved_config.yaml").write_text(config, encoding="utf-8", newline="\n")
    return run_dir


# ---------------------------------------------------------------- shared test helpers

REPLAY_FIELDS = replay.SERIES_FIELDS
"""A field list for ``run_data.run_series``: the replay page's own."""
MASS_TOL_KG = 1e-5
"""Tolerance [kg] on a mass read back from a CSV written with %.12g: a 1.6e5 kg mass
keeps 1e-6 kg."""


def _snapshot(folder: Path) -> dict[str, tuple[int, int]]:
    """{relative path: (size, modification time [ns])} of everything under ``folder``."""
    return {
        p.relative_to(folder).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
        for p in sorted(folder.rglob("*"))
    }


def _sign(value: float) -> float:
    """+1.0 or -1.0: the sign bit of ``value`` (tells -0.0 from 0.0)."""
    return math.copysign(1.0, value)


def _sweep_point(root: Path) -> Path:
    """A sweep point's folder: its metrics.json has no ``runs`` and no ``model`` (the
    keys results_io writes for one: experiment, run, metrics, comparison)."""
    point = root / "results" / SYNTH_EXPERIMENT / SYNTH_TIMESTAMP / "sweep_1" / "run_0001"
    point.mkdir(parents=True)
    record = {"experiment": SYNTH_EXPERIMENT, "run": {}, "metrics": {}, "comparison": {}}
    (point / "metrics.json").write_text(json.dumps(record), encoding="utf-8")
    return point


# ---------------------------------------------------------------- readers and helpers


def test_readers_are_lenient_and_read_utf8(tmp_path: Path) -> None:
    """A missing file and a top level that is not a mapping read as {}; JSON's NaN and
    Infinity literals are accepted; a non-ASCII character written as UTF-8 bytes reads
    back as itself (never through the console's code page)."""
    assert run_data.read_json(tmp_path / "missing.json") == {}
    assert run_data.read_yaml(tmp_path / "missing.yaml") == {}
    (tmp_path / "list.json").write_text("[1, 2]", encoding="utf-8")
    (tmp_path / "list.yaml").write_text("- 1\n- 2\n", encoding="utf-8")
    assert run_data.read_json(tmp_path / "list.json") == {}
    assert run_data.read_yaml(tmp_path / "list.yaml") == {}
    (tmp_path / "nan.json").write_text('{"a": NaN, "b": Infinity, "c": 1.5}', encoding="utf-8")
    data = run_data.read_json(tmp_path / "nan.json")
    assert math.isnan(data["a"]) and data["b"] == math.inf and data["c"] == 1.5
    text = "caf\u00e9 \u00b110%"  # e acute and plus-minus, by code point
    (tmp_path / "text.json").write_bytes(
        json.dumps({"s": text}, ensure_ascii=False).encode("utf-8")
    )
    (tmp_path / "text.yaml").write_bytes(f's: "{text}"\n'.encode())
    assert run_data.read_json(tmp_path / "text.json") == {"s": text}
    assert run_data.read_yaml(tmp_path / "text.yaml") == {"s": text}


def test_a_corrupt_file_is_one_message_only_when_asked(tmp_path: Path) -> None:
    """Default behaviour is the one plots.py and replay.py had: the parser's or the
    decoder's own exception propagates. With ``error=`` it is that class, on one line,
    naming the file."""
    bad_json = tmp_path / "bad.json"
    bad_json.write_text('{"a": [1, 2\n', encoding="utf-8")
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("a: [1, 2\nb: }\n", encoding="utf-8")
    not_utf8 = tmp_path / "latin.json"
    not_utf8.write_bytes(b'{"s": "caf\xe9"}')
    with pytest.raises(json.JSONDecodeError):
        run_data.read_json(bad_json)
    with pytest.raises(yaml.YAMLError):
        run_data.read_yaml(bad_yaml)
    with pytest.raises(UnicodeDecodeError):
        run_data.read_json(not_utf8)
    cases: list[tuple[Callable[..., dict[str, Any]], Path]] = [
        (run_data.read_json, bad_json),
        (run_data.read_yaml, bad_yaml),
        (run_data.read_json, not_utf8),
        (run_data.read_yaml, not_utf8),
    ]
    for reader, path in cases:
        with pytest.raises(run_data.RunDataError) as info:
            reader(path, error=run_data.RunDataError)
        message = str(info.value)
        assert message.startswith(f"cannot read {path}: ") and "\n" not in message
        with pytest.raises(replay.ReplayError):
            reader(path, error=replay.ReplayError)


def test_finite_and_as_mapping() -> None:
    """finite: a bool, None, text, NaN and the infinities give None; a number comes
    back as a float, rounded when asked; -0.0 becomes +0.0, also after rounding; numpy
    numbers count. as_mapping: the dict itself, {} for anything else."""
    for value in (True, False, None, "1.5", math.nan, math.inf, -math.inf, [1.0]):
        assert run_data.finite(value) is None
    assert run_data.finite(3) == 3.0 and isinstance(run_data.finite(3), float)
    assert run_data.finite(1.23456, 2) == 1.23 and run_data.finite(1.5, 0) == 2.0
    assert run_data.finite(np.float32(0.5)) == 0.5 and run_data.finite(np.int64(7), 1) == 7.0
    assert run_data.finite(np.float64("nan")) is None
    for value, decimals in ((-0.0, None), (-0.0, 1), (-0.0004, 3)):
        zero = run_data.finite(value, decimals)
        assert zero == 0.0 and _sign(zero) == 1.0
    mapping = {"a": 1}
    assert run_data.as_mapping(mapping) is mapping
    assert [run_data.as_mapping(v) for v in (None, [1], "a", 3)] == [{}, {}, {}, {}]


def test_plot_stem_and_wrapped_deg() -> None:
    assert run_data.plot_stem("silo cold", "F/N") == "silo_cold_F_N"
    assert run_data.plot_stem("a.b-c_1", "x") == "a.b-c_1_x"
    # 3 pi / 2 is the falling vehicle's unwrapped angle: -90 deg, not 270 deg.
    wrapped = run_data.wrapped_deg(np.array([0.0, math.pi / 2, 3 * math.pi / 2, math.nan]))
    assert wrapped[:3] == pytest.approx([0.0, 90.0, -90.0], abs=1e-12)
    assert math.isnan(wrapped[3])


def test_calibration_helpers() -> None:
    """The gap is model / reference - 1; the band holds both edges (25,080 kg and
    20,520 kg against 22,800 kg are exactly +/-10 %) and nothing 1e-9 beyond them."""
    assert run_data.calibration_gap(24700.0, 22800.0) == pytest.approx(1900.0 / 22800.0, rel=1e-12)
    assert run_data.inside_calibration_band(run_data.calibration_gap(25080.0, 22800.0))
    assert run_data.inside_calibration_band(run_data.calibration_gap(20520.0, 22800.0))
    assert not run_data.inside_calibration_band(0.1 + 1e-9)
    assert not run_data.inside_calibration_band(-0.1 - 1e-9)
    gate = run_data.CALIBRATION_RECORDS[run_data.CALIBRATION_GATE_VEHICLE]
    assert not run_data.inside_calibration_band(run_data.calibration_gap(gate[0], gate[1]))


def test_readers_write_nothing(tmp_path: Path) -> None:
    """The listing of a results directory (paths, sizes, modification times) is the
    same after every reader of run_data has been through it."""
    run_dir = _synth_run_dir(tmp_path)
    before = _snapshot(tmp_path)
    metrics = run_data.check_run_dir(run_dir)
    config = run_data.read_yaml(run_dir / run_data.CONFIG_FILE)
    run_data.run_identity(run_dir)
    names = run_data.select_runs(run_dir, None)
    for name in run_data.run_names(run_dir)[1]:
        run_data.run_source(metrics, config, name)
        run_data.vehicle_masses(run_data.run_vehicle_block(config, name))
        run_data.read_series_frame(run_dir, name, run_data.PLANAR_BASE_COLUMNS)
        frame = run_data.read_series(run_dir, name, replay.REPLAY_COLUMNS)
        run_data.run_series(frame, REPLAY_FIELDS)
        offset_s = run_data.release_offset_s(frame)
        run_data.read_events(run_dir / name / run_data.EVENTS_FILE, offset_s)
    run_data.default_output_path(run_dir, run_dir, "a.html")
    run_data.protected_tree(run_dir / "a.html", run_dir)
    replay.replay_data(run_dir, names)
    plots.load_animation_runs(run_dir, names)
    assert _snapshot(tmp_path) == before


# ---------------------------------------------------------------- compatibility

PLOTS_NAMES = [
    ("plot_stem", "plot_stem"),
    ("PLOT_STEM_UNSAFE", "PLOT_STEM_UNSAFE"),
    ("CALIBRATION_RECORDS", "CALIBRATION_RECORDS"),
    ("CALIBRATION_BAND", "CALIBRATION_BAND"),
    ("CALIBRATION_BAND_EDGE_REL_TOL", "CALIBRATION_BAND_EDGE_REL_TOL"),
    ("CALIBRATION_GATE_VEHICLE", "CALIBRATION_GATE_VEHICLE"),
    ("calibration_gap", "calibration_gap"),
    ("inside_calibration_band", "inside_calibration_band"),
    ("RESULTS_TREE_NAME", "RESULTS_TREE_NAME"),
    ("OFFLOAD_CASE", "OFFLOAD_CASE"),
    ("OFFLOAD_PAIRED_PAD", "OFFLOAD_PAIRED_PAD"),
    ("OFFLOAD_PAD_CONTROL", "OFFLOAD_PAD_CONTROL"),
    ("OFFLOAD_SOLVED_KIND", "OFFLOAD_SOLVED_KIND"),
    ("offload_role", "offload_role"),
    ("ANIMATION_MAX_RUNS", "MAX_RUNS"),
    ("ANIMATION_DEFAULT_VARIANTS", "DEFAULT_VARIANTS"),
    ("ANIMATION_COLUMNS", "PLANAR_BASE_COLUMNS"),
    ("animation_run_names", "run_names"),
]
"""(name in plots, name in run_data): each plots name is the run_data object."""
REPLAY_NAMES = [
    ("ROLE_RUN", "ROLE_RUN"),
    ("ROLE_BOUND", "ROLE_BOUND"),
    ("ROLE_PAIRED_BASELINE", "ROLE_PAIRED_BASELINE"),
    ("ROLE_CASE", "ROLE_CASE"),
    ("ROLE_OFFLOAD", "ROLE_OFFLOAD"),
    ("REPLAY_EARLY_END_S", "GRID_EARLY_END_S"),
    ("REPLAY_EARLY_DT_S", "GRID_EARLY_DT_S"),
    ("REPLAY_LATE_DT_S", "GRID_LATE_DT_S"),
    ("REPLAY_GRID_DECIMALS", "GRID_DECIMALS"),
    ("REPLAY_TIME_DECIMALS", "TIME_DECIMALS"),
    ("_finite", "finite"),
    ("_mapping", "as_mapping"),
    ("_entry_config", "entry_config"),
    ("overrides_text", "overrides_text"),
    ("offload_note", "offload_note"),
    ("replay_grid", "sample_grid"),
    ("defined_mask", "defined_mask"),
    ("series_values", "series_values"),
    ("wrapped_deg", "wrapped_deg"),
    ("Converter", "Converter"),
    ("results_ancestors", "results_ancestors"),
    ("protected_tree", "protected_tree"),
]
"""(name in replay, name in run_data): each replay name is the run_data object."""


@pytest.mark.parametrize(("old", "new"), PLOTS_NAMES)
def test_plots_names_are_the_run_data_objects(old: str, new: str) -> None:
    assert getattr(plots, old) is getattr(run_data, new)


@pytest.mark.parametrize(("old", "new"), REPLAY_NAMES)
def test_replay_names_are_the_run_data_objects(old: str, new: str) -> None:
    assert getattr(replay, old) is getattr(run_data, new)


def test_one_object_behind_every_importer() -> None:
    """results_io's calibration table and sim's plot_stem are the run_data objects (one
    dict, never a copy); the column tuples keep their content and order; SERIES_FIELDS
    holds the wrapped_deg object replay exports."""
    assert results_io.CALIBRATION_RECORDS is run_data.CALIBRATION_RECORDS
    assert sim.plot_stem is run_data.plot_stem
    assert sim.PLOT_STEM_UNSAFE is run_data.PLOT_STEM_UNSAFE
    base = (
        "t_s",
        "t_rel_release_s",
        "phase",
        "alt_m",
        "downrange_m",
        "speed_rel_mps",
        "felt_axial_g",
        "q_pa",
        "m_kg",
    )
    assert plots.ANIMATION_COLUMNS == base
    assert replay.REPLAY_COLUMNS == (*base, "gamma_rel_rad", "mach")
    fields = {field: convert for field, _, convert, _ in replay.SERIES_FIELDS}
    assert fields["gamma_deg"] is replay.wrapped_deg is run_data.wrapped_deg


def test_duplicate_helpers_are_gone() -> None:
    """The two copies of the JSON and YAML readers and of the mapping helper are one
    function each in run_data, and replay's finite helper is run_data's: plots and
    replay define none of them. plots keeps its own ``_finite_kg`` for the animation's
    legend (survey 06 section 1.1: STAY; it takes only int and float, rounds nothing and
    keeps a negative zero, so the legend's text is as before SP2)."""
    for module, names in (
        (plots, ("_read_json", "_read_yaml", "_as_dict", "_results_tree", "_is_inside")),
        (replay, ("_read_json", "_read_yaml")),
    ):
        for name in names:
            assert not hasattr(module, name), f"{module.__name__}.{name}"
    for module in (plots, replay):
        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        defined = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
        assert not defined & {"_finite", "_mapping", "_as_dict", "_read_json", "_read_yaml"}
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "read_csv" not in source and "json.load" not in source
        assert "safe_load" not in source
    assert plots._finite_kg(-0.0) == 0.0 and math.copysign(1.0, plots._finite_kg(-0.0)) == -1.0
    assert run_data.finite(-0.0) == 0.0 and math.copysign(1.0, run_data.finite(-0.0)) == 1.0
    assert plots._finite_kg(np.int64(1)) is None and run_data.finite(np.int64(1)) == 1.0


def test_replay_calls_no_private_plots_name() -> None:
    """The SP2 A1 gate item, kept as a test: replay.py holds no ``plots._`` (and, since
    plot_stem moved too, no import of plots at all)."""
    source = Path(replay.__file__).read_text(encoding="utf-8")
    assert "plots._" not in source
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add(str(node.module))
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    assert "launchsim.plots" not in imported and "matplotlib" not in imported


def test_error_classes_derive_from_run_data_error() -> None:
    for cls in (plots.AnimationError, replay.ReplayError):
        assert issubclass(cls, run_data.RunDataError) and issubclass(cls, ValueError)
    assert issubclass(run_data.RunDataError, ValueError)
    assert not issubclass(plots.AnimationError, replay.ReplayError)
    assert not issubclass(replay.ReplayError, plots.AnimationError)


RAISING_CALLS: dict[str, Callable[[Path, type[run_data.RunDataError] | None], Any]] = {
    "check_run_dir": lambda d, e: run_data.check_run_dir(d / "missing", **_err(e)),
    "select_runs": lambda d, e: run_data.select_runs(d, ["nope"], **_err(e)),
    "run_source": lambda d, e: run_data.run_source({}, {}, "stray", **_err(e)),
    "model_columns": lambda d, e: run_data.model_columns("spatial_9d", **_err(e)),
    "vehicle_masses": lambda d, e: run_data.vehicle_masses({"name": "toy"}, **_err(e)),
    "read_series_frame": lambda d, e: run_data.read_series_frame(d, "pad", ["nope"], **_err(e)),
    "read_series": lambda d, e: run_data.read_series(d, "pad", ["nope"], **_err(e)),
    "read_events": lambda d, e: run_data.read_events(
        d / "pad" / "events.csv", 0.0, required=["nope"], **_err(e)
    ),
    "check_output_suffix": lambda d, e: run_data.check_output_suffix(
        d / "a.txt", (".html",), ".html", **_err(e)
    ),
    "check_outside_results": lambda d, e: run_data.check_outside_results(
        d / "a.html", d, **_err(e)
    ),
    "check_output_folder": lambda d, e: run_data.check_output_folder(
        d / "no" / "a.html", **_err(e)
    ),
    "check_output": lambda d, e: run_data.check_output(
        d / "a.html", d, suffixes=(".html",), suffix_text=".html", **_err(e)
    ),
}
"""Each raising function of run_data, called on the synthetic directory so that it
refuses its input; the second argument is the error class to pass (None: the default)."""


def _err(error: type[run_data.RunDataError] | None) -> dict[str, Any]:
    """The ``error=`` keyword, or nothing (the default class)."""
    return {} if error is None else {"error": error}


@pytest.fixture(scope="module")
def synth_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The synthetic results directory, built once for the tests that only read it."""
    return _synth_run_dir(tmp_path_factory.mktemp("synth"))


@pytest.mark.parametrize("name", sorted(RAISING_CALLS))
def test_each_raising_function_raises_the_class_it_is_given(synth_dir: Path, name: str) -> None:
    """RunDataError itself by default; the caller's class, exactly, when one is given."""
    call = RAISING_CALLS[name]
    with pytest.raises(run_data.RunDataError) as info:
        call(synth_dir, None)
    assert type(info.value) is run_data.RunDataError
    for cls in (plots.AnimationError, replay.ReplayError):
        with pytest.raises(cls) as given:
            call(synth_dir, cls)
        assert type(given.value) is cls
        assert str(given.value) == str(info.value)  # the class changes, the words do not


BANNED_MODULES = (
    "launchsim.plots",
    "launchsim.replay",
    "launchsim.results_io",
    "launchsim.summary",
)
ALLOWED_IMPORTS = {
    "launchsim.config",
    "launchsim.metrics_planar",
    "launchsim.phases.planar",
    "launchsim.units",
}


def test_importing_run_data_loads_no_drawing_or_writer_module() -> None:
    """In a fresh interpreter, ``import launchsim.run_data`` loads no matplotlib module
    and none of plots, replay, results_io and summary; its own launchsim imports are
    exactly config, metrics_planar, phases.planar and units."""
    code = (
        "import json, sys\n"
        "import launchsim.run_data\n"
        f"banned = {BANNED_MODULES!r}\n"
        "hit = sorted(m for m in sys.modules "
        "if m == 'matplotlib' or m.startswith('matplotlib.') or m in banned)\n"
        "print(json.dumps(hit))\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout.strip().splitlines()[-1]) == []
    tree = ast.parse(Path(run_data.__file__).read_text(encoding="utf-8"))
    own = {
        str(node.module)
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and str(node.module).startswith("launchsim")
    }
    plain = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    assert own == ALLOWED_IMPORTS
    assert not [name for name in plain if name.split(".")[0] in ("launchsim", "matplotlib")]


# ---------------------------------------------------------------- directory and selection


def test_check_run_dir(tmp_path: Path) -> None:
    """The refusals in order (missing directory, no metrics.json, no ``runs`` mapping,
    another model) with the caller's wording in the last; a metrics.json without
    ``model`` is a vertical_1d one; a second model passes only when it is accepted."""
    run_dir = _synth_run_dir(tmp_path)
    metrics = run_data.check_run_dir(run_dir)
    assert metrics["baseline"] == "pad" and set(metrics["runs"]) == {"pad", "silo"}
    with pytest.raises(run_data.RunDataError, match="run directory not found"):
        run_data.check_run_dir(tmp_path / "nowhere")
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(run_data.RunDataError, match=r"has no metrics\.json; pass one results"):
        run_data.check_run_dir(empty)
    with pytest.raises(run_data.RunDataError, match="not an experiment results directory") as err:
        run_data.check_run_dir(_sweep_point(tmp_path / "sweep"))
    assert "vertical_1d" not in str(err.value) and "sweep point" in str(err.value)

    def rewrite(**changes: Any) -> None:
        record = {**_synth_metrics(), **changes}
        record = {k: v for k, v in record.items() if v is not None}
        (run_dir / "metrics.json").write_text(json.dumps(record), encoding="utf-8")

    rewrite(model=None)  # a vertical_1d metrics.json has no model key
    with pytest.raises(run_data.RunDataError) as err:
        run_data.check_run_dir(run_dir, wording="animate draws")
    assert f"{run_dir} is a vertical_1d run; animate draws planar_2d runs only" in str(err.value)
    rewrite(model="spatial_3d")
    with pytest.raises(run_data.RunDataError) as err:
        run_data.check_run_dir(run_dir, wording="replay shows")
    assert "is a spatial_3d run; replay shows planar_2d runs only" in str(err.value)
    assert (
        run_data.check_run_dir(run_dir, models=(PLANAR_2D, "spatial_3d"))["model"] == "spatial_3d"
    )
    with pytest.raises(run_data.RunDataError, match="planar_2d or other_4d runs only"):
        run_data.check_run_dir(run_dir, models=(PLANAR_2D, "other_4d"))
    rewrite(runs=["pad"])  # a list is not a runs mapping
    with pytest.raises(run_data.RunDataError, match="not an experiment results directory"):
        run_data.check_run_dir(run_dir)


def test_check_run_dir_refuses_a_bare_string_for_models(tmp_path: Path) -> None:
    """``models`` is a tuple: a bare string is a programming error (TypeError, not a
    RunDataError, before any file is looked at), since ``in`` on a string would match
    substrings and let a run of model '2d' pass ``models='planar_2d'``."""
    run_dir = _synth_run_dir(tmp_path)
    (run_dir / "metrics.json").write_text(
        json.dumps({**_synth_metrics(), "model": "2d"}), encoding="utf-8"
    )
    with pytest.raises(TypeError) as err:
        run_data.check_run_dir(run_dir, models=PLANAR_2D)  # type: ignore[arg-type]
    assert str(err.value) == (
        "models must be a tuple of model names, not the string 'planar_2d'; pass ('planar_2d',)"
    )
    assert not isinstance(err.value, ValueError)
    with pytest.raises(TypeError, match="not the string 'planar_2d'"):
        run_data.check_run_dir(tmp_path / "nowhere", models=PLANAR_2D)  # type: ignore[arg-type]
    with pytest.raises(run_data.RunDataError, match="is a 2d run; this reader takes planar_2d"):
        run_data.check_run_dir(run_dir, models=(PLANAR_2D,))
    assert run_data.check_run_dir(run_dir, models=("2d",))["model"] == "2d"


def test_run_names_and_identity(tmp_path: Path) -> None:
    """The default is the baseline plus three variants in metrics.json order; every
    other folder with a time series follows, sorted; a folder without one is not a
    run; the identity comes from metrics.json, else from the folder names."""
    run_dir = _synth_run_dir(tmp_path)
    default, available = run_data.run_names(run_dir)
    assert default == ["pad", "silo"]
    others = sorted(set(SYNTH_RUNS) - {"pad", "silo"})
    assert available == ["pad", "silo", *others] and "plots" not in available
    assert run_data.run_identity(run_dir) == (SYNTH_EXPERIMENT, SYNTH_TIMESTAMP)
    # more variants than fit, written in an order that is not the sorted one
    record = _synth_metrics()
    extra = ["zeta", "alpha", "mid", "beta"]
    record["runs"] = {"silo": {}, **{n: {} for n in extra}, "pad": {}}
    (run_dir / "metrics.json").write_text(json.dumps(record), encoding="utf-8")
    for name in extra:
        _synth_write_run(run_dir, name, False)
    default, available = run_data.run_names(run_dir)
    assert default == ["pad", "silo", "zeta", "alpha"]  # baseline first, then summary order
    assert available[:6] == ["silo", "zeta", "alpha", "mid", "beta", "pad"]
    assert available[6:] == others
    bare = tmp_path / "out" / "some_experiment" / "20270101T000000Z"
    bare.mkdir(parents=True)
    assert run_data.run_identity(bare) == ("some_experiment", "20270101T000000Z")
    _synth_write_run(bare, "b_run", False)
    _synth_write_run(bare, "a_run", False)
    assert run_data.run_names(bare) == (["a_run", "b_run"], ["a_run", "b_run"])


def test_select_runs(synth_dir: Path) -> None:
    """Unknown names first, then a repeated name, then no runs, then too many; ``what``
    and ``max_runs`` appear in the last message."""
    assert run_data.select_runs(synth_dir, None) == ["pad", "silo"]
    assert run_data.select_runs(synth_dir, ["silo_s1", "pad"]) == ["silo_s1", "pad"]
    available = ", ".join(run_data.run_names(synth_dir)[1])
    with pytest.raises(run_data.RunDataError) as err:
        run_data.select_runs(synth_dir, ["nope", "nope", "pad"])
    assert str(err.value) == f"unknown run(s) nope, nope in {synth_dir}; available: {available}"
    five = ["pad", "silo", "alt_low", "silo_s1", "pad"]
    with pytest.raises(run_data.RunDataError, match="a run is named twice: pad, silo"):
        run_data.select_runs(synth_dir, five)
    with pytest.raises(run_data.RunDataError, match=r"no runs with a timeseries\.csv"):
        run_data.select_runs(synth_dir, [])
    five[-1] = "silo_s1__pad"
    with pytest.raises(run_data.RunDataError) as err:
        run_data.select_runs(synth_dir, five, what="animation")
    assert str(err.value) == "5 runs requested; at most 4 fit one animation"
    with pytest.raises(run_data.RunDataError, match="3 runs requested; at most 2 fit one scene"):
        run_data.select_runs(synth_dir, five[:3], what="scene", max_runs=2)
    assert run_data.select_runs(synth_dir, five, max_runs=5) == five


def test_run_source_gives_each_role_its_own_metrics_and_config(synth_dir: Path) -> None:
    """One directory with all five roles: each run's role, metrics record, comparison,
    compared run, run block, vehicle name and note come from its own section."""
    metrics = run_data.read_json(synth_dir / run_data.METRICS_FILE)
    config = run_data.read_yaml(synth_dir / run_data.CONFIG_FILE)
    source = {n: run_data.run_source(metrics, config, n) for n in SYNTH_RUNS}
    roles = {n: s["role"] for n, s in source.items()}
    assert roles == {
        "pad": run_data.ROLE_RUN,
        "silo": run_data.ROLE_RUN,
        "silo__aero_bound": run_data.ROLE_BOUND,
        "pad__aero_bound": run_data.ROLE_PAIRED_BASELINE,
        "alt_low": run_data.ROLE_CASE,
        "silo_s1": run_data.ROLE_OFFLOAD,
        "silo_s1__pad": run_data.ROLE_OFFLOAD,
        "pad__offload_stage1": run_data.ROLE_OFFLOAD,
    }
    payloads = {n: s["metrics"]["payload_kg"] for n, s in source.items()}
    assert payloads == {
        "pad": 1000.0,
        "silo": 1100.0,
        "silo__aero_bound": 1090.0,
        "pad__aero_bound": 990.0,
        "alt_low": 1050.0,
        "silo_s1": SYNTH_P_REF_KG,
        "silo_s1__pad": SYNTH_PAIRED_PAD_KG,
        "pad__offload_stage1": SYNTH_P_REF_KG,
    }
    compared = {n: s["compared_to"] for n, s in source.items() if s["compared_to"] is not None}
    assert compared == {"silo": "pad", "silo__aero_bound": "pad__aero_bound"}
    assert source["pad"]["comparison"] == {} and source["pad"]["note"] == ""
    assert source["silo"]["comparison"]["payload_delta_kg"] == 100.0
    assert source["silo__aero_bound"]["comparison"]["payload_delta_kg"] == 90.0
    assert all(source[n]["comparison"] == {} for n in ("pad__aero_bound", "alt_low", "silo_s1"))
    for name, assisted in SYNTH_RUNS.items():
        model = "constant_accel" if assisted else "none"
        assert source[name]["config"]["assist"]["model"] == model
    assert source["alt_low"]["config"]["planar"]["target_orbit"]["altitude_km"] == 150.0
    vehicles = {n: s["vehicle"] for n, s in source.items()}
    assert vehicles == {
        "pad": None,
        "silo": None,
        "silo__aero_bound": "toy_2d",
        "pad__aero_bound": "toy_2d",
        "alt_low": "toy_2d_light",
        "silo_s1": "toy_2d",
        "silo_s1__pad": "toy_2d",
        "pad__offload_stage1": None,
    }
    override = "(with vehicle.aero.reference_area_m2 = 21.24)"
    assert source["silo__aero_bound"]["note"] == (
        f"aero_bound re-run of silo {override}, compared with pad__aero_bound"
    )
    assert source["pad__aero_bound"]["note"] == (
        f"paired baseline of the aero_bound re-run silo__aero_bound {override}"
    )
    assert source["alt_low"]["note"] == "case with its own settings, not compared with the baseline"
    with pytest.raises(run_data.RunDataError) as err:
        run_data.run_source(metrics, config, "stray", wording="replay shows")
    assert "stray has a timeseries.csv but metrics.json describes it nowhere" in str(err.value)
    assert str(err.value).endswith("replay shows the runs metrics.json records")


def test_offload_role_and_note(synth_dir: Path) -> None:
    """A case's recorded run, its paired pad and a pad control are told apart from the
    offload block; the note gives 41,262.9 kg as 41.3 t, the fractions 0.1004 and
    0.0796 as 10.0 % and 8.0 %, and the payloads in kg."""
    offload = run_data.read_json(synth_dir / run_data.METRICS_FILE)["offload"]
    kind, record = run_data.offload_role(offload, "silo_s1") or ("", {})
    assert kind == run_data.OFFLOAD_CASE == "offload case" and record["name"] == "silo_s1"
    kind, record = run_data.offload_role(offload, "silo_s1__pad") or ("", {})
    assert kind == run_data.OFFLOAD_PAIRED_PAD == "paired pad" and record["name"] == "silo_s1"
    kind, record = run_data.offload_role(offload, "pad__offload_stage1") or ("", {})
    assert kind == run_data.OFFLOAD_PAD_CONTROL == "pad control" and record["mode"] == "stage1"
    assert run_data.offload_role(offload, "pad") is None
    assert run_data.offload_role({}, "silo_s1") is None
    tonnes = SYNTH_OFFLOAD_KG / 1000.0
    assert run_data.offload_note(offload, "silo_s1", "pad") == (
        f"offload case silo_s1 of silo: {tonnes:.1f} t less propellant (solved; "
        f"{100 * 0.1004:.1f}% of the stage-1 load, {100 * 0.0796:.1f}% of all), flying "
        f"{SYNTH_P_REF_KG:,.1f} kg against pad's full load at P_ref = {SYNTH_P_REF_KG:,.1f} kg, "
        "the same orbit"
    )
    assert "41.3 t less propellant (solved; 10.0% of the stage-1 load, 8.0% of all)" in (
        run_data.offload_note(offload, "silo_s1", "pad")
    )
    assert run_data.offload_note(offload, "silo_s1__pad", "pad") == (
        "paired pad of offload case silo_s1: pad with the same propellant change and no assist"
    )
    assert run_data.offload_note(offload, "pad__offload_stage1", "pad") == (
        "pad control (stage1): pad's own offload at P_ref = 1,000.0 kg"
    )
    assert run_data.offload_note(offload, "nowhere", "pad") == "a run of the offload block"
    fixed = copy.deepcopy(offload)
    fixed["cases"][0].update(kind="fixed", stage1_fraction=None)
    del fixed["reference_payload_kg"]
    note = run_data.offload_note(fixed, "silo_s1", "pad")
    assert "41.3 t less propellant (imposed)" in note and "P_ref = the reference payload" in note


def test_run_vehicle_block_is_the_runs_own_else_the_experiments(synth_dir: Path) -> None:
    """The entry's own vehicle block when it has one (the offloaded load, the case's
    lighter stage, a bound's block), the experiment's top-level block for an entry with
    ``run`` only (the zero-offload pad control, the experiment runs), {} without any."""
    config = run_data.read_yaml(synth_dir / run_data.CONFIG_FILE)
    top = config["vehicle"]
    for name in ("pad", "silo", "pad__offload_stage1", "not_a_run"):
        assert run_data.run_vehicle_block(config, name) is top
    own = run_data.run_vehicle_block(config, "silo_s1")
    assert own is config["offload_runs"]["silo_s1"]["vehicle"] and own is not top
    assert own["stages"][0]["propellant_mass_t"]["value"] == SYNTH_OFFLOADED_PROPELLANT_T
    assert run_data.run_vehicle_block(config, "alt_low")["name"] == "toy_2d_light"
    assert (
        run_data.run_vehicle_block(config, "silo__aero_bound")
        is (config["bound_runs"]["silo__aero_bound"]["vehicle"])
    )
    assert run_data.run_vehicle_block({"runs": {"pad": {"run": {}}}}, "pad") == {}
    # masses per run: tonnes times 1000, from each run's own block
    load = {n: run_data.vehicle_masses(run_data.run_vehicle_block(config, n)) for n in SYNTH_RUNS}
    assert load["pad"].stage_propellant_kg[0] == pytest.approx(410_900.0, rel=1e-12)
    assert load["silo_s1"].stage_propellant_kg[0] == pytest.approx(369_637.1, rel=1e-12)
    assert load["pad__offload_stage1"] == load["pad"]
    assert load["alt_low"].stage_dry_kg[0] == pytest.approx(20_000.0, rel=1e-12)


def test_vehicle_masses_go_through_the_vehicle_schema() -> None:
    """22.2 t is 22,200 kg and 1.7 t is 1,700 kg; the fairing trigger comes from a
    block, from a string, and is ``staging`` when the key is absent (config.py's
    default, not 'no rule'); a block that is not a vehicle file is refused in one line."""
    block = _synth_vehicle()
    masses = run_data.vehicle_masses(block)
    assert masses.stage_names == ("stage1", "stage2")
    assert masses.stage_dry_kg == pytest.approx((22_200.0, 4_000.0), rel=1e-12)
    assert masses.stage_propellant_kg == pytest.approx((410_900.0, 107_500.0), rel=1e-12)
    assert masses.fairing_kg == pytest.approx(1_700.0, rel=1e-12)
    assert masses.payload_kg == pytest.approx(22_800.0, rel=1e-12)
    assert "fairing_drop" not in block and masses.fairing_trigger == "staging"
    assert VehicleConfig.model_fields["fairing_drop"].default == "staging"
    assert run_data.vehicle_masses({**block, "fairing_drop": "never"}).fairing_trigger == "never"
    heating = {"trigger": "free_molecular_heating", "limit_W_m2": _synth_quantity(1135.0)}
    assert run_data.vehicle_masses({**block, "fairing_drop": heating}).fairing_trigger == (
        "free_molecular_heating"
    )
    assert run_data.vehicle_masses({**block, "fairing_drop": {"trigger": "staging"}}) == masses
    with pytest.raises(run_data.RunDataError) as err:
        run_data.vehicle_masses({"name": "toy_2d"})
    message = str(err.value)
    assert message.startswith("vehicle block 'toy_2d' is not a complete vehicle file: ")
    assert "\n" not in message and "stages" in message
    with pytest.raises(dataclasses.FrozenInstanceError):
        masses.fairing_kg = 0.0  # type: ignore[misc]


# ---------------------------------------------------------------- series and resampling

TINY_COLUMNS = ("t_s", "t_rel_release_s", "phase", "m_kg")


def _tiny_series(run_dir: Path, name: str, lines: list[str], header: str | None = None) -> None:
    """<run_dir>/<name>/timeseries.csv with TINY_COLUMNS (or ``header``) and ``lines``."""
    folder = run_dir / name
    folder.mkdir(parents=True)
    text = "\n".join([header or ",".join(TINY_COLUMNS), *lines]) + "\n"
    (folder / "timeseries.csv").write_text(text, encoding="utf-8")


def test_read_series_sorts_and_keeps_the_later_row(tmp_path: Path) -> None:
    """Rows out of order come back sorted on the time after release; of two rows at
    one time the later one in the file is kept (the state after a map), also when
    another row sits between them; ``read_series_frame`` returns the file as written."""
    lines = [
        "3.0,1.0,B,90.0",
        "2.0,0.0,A,100.0",
        "4.0,2.0,B,80.0",
        "4.0,2.0,C,70.0",
        "2.0,0.0,A2,99.0",
        "5.0,3.0,C,60.0",
    ]
    _tiny_series(tmp_path, "run", lines)
    frame = run_data.read_series(tmp_path, "run", TINY_COLUMNS)
    assert frame["t_rel_release_s"].tolist() == [0.0, 1.0, 2.0, 3.0]
    assert frame["phase"].tolist() == ["A2", "B", "C", "C"]
    assert frame["m_kg"].tolist() == [99.0, 90.0, 70.0, 60.0]
    assert frame.index.tolist() == [0, 1, 2, 3]
    assert run_data.release_offset_s(frame) == 2.0
    raw = run_data.read_series_frame(tmp_path, "run", TINY_COLUMNS)
    assert raw["t_rel_release_s"].tolist() == [1.0, 0.0, 2.0, 2.0, 0.0, 3.0]
    assert raw["phase"].tolist() == ["B", "A", "B", "C", "A2", "C"]
    assert run_data.release_offset_s(raw) == 3.0 - 1.0  # its first row, as animate reads it


def test_read_series_takes_the_columns_it_is_asked_for(tmp_path: Path) -> None:
    """The column list is the caller's: a column the file lacks is named in the
    refusal, columns nobody asked for are ignored, and an empty series is refused."""
    _tiny_series(tmp_path, "run", ["2.0,0.0,A,100.0"])
    path = tmp_path / "run" / "timeseries.csv"
    assert len(run_data.read_series(tmp_path, "run", ["t_rel_release_s"])) == 1
    assert len(run_data.read_series(tmp_path, "run", TINY_COLUMNS)) == 1
    for reader in (run_data.read_series, run_data.read_series_frame):
        with pytest.raises(run_data.RunDataError) as err:
            reader(tmp_path, "run", [*TINY_COLUMNS, "mach", "q_pa"])
        assert str(err.value) == (
            f"{path} lacks planar columns ['mach', 'q_pa']; not a planar_2d run"
        )
    with pytest.raises(plots.AnimationError, match="lacks planar columns"):
        plots.read_animation_run(tmp_path, "run", {})
    with pytest.raises(replay.ReplayError, match="lacks planar columns"):
        replay.read_series(tmp_path, "run")
    _tiny_series(tmp_path, "empty", [])
    for reader in (run_data.read_series, run_data.read_series_frame):
        with pytest.raises(run_data.RunDataError, match=r"is empty \(a failed search writes no"):
            reader(tmp_path, "empty", TINY_COLUMNS)


def test_read_series_words_the_refusal_from_the_columns_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The missing-column refusal names the model whose columns were asked for: the
    planar words (byte for byte what animate and replay said before A1) by default; for
    another model its ModelColumns label, or the model name itself when it has no column
    set; the empty-series refusal does not depend on the model."""
    _tiny_series(tmp_path, "run", ["2.0,0.0,A,100.0"])
    path = tmp_path / "run" / "timeseries.csv"
    spatial = ("t_s", "crossrange_m", "heading_rad")
    for reader in (run_data.read_series, run_data.read_series_frame):
        with pytest.raises(run_data.RunDataError) as err:
            reader(tmp_path, "run", spatial, model=PLANAR_2D)
        assert str(err.value) == (
            f"{path} lacks planar columns ['crossrange_m', 'heading_rad']; not a planar_2d run"
        )
        with pytest.raises(run_data.RunDataError) as err:
            reader(tmp_path, "run", spatial, model="spatial_3d")
        assert str(err.value) == (
            f"{path} lacks spatial_3d columns ['crossrange_m', 'heading_rad']; not a spatial_3d run"
        )
    assert run_data.model_label(PLANAR_2D) == "planar" and run_data.model_label("x") == "x"
    planar = run_data.MODEL_COLUMNS[PLANAR_2D]
    monkeypatch.setitem(
        run_data.MODEL_COLUMNS,
        "spatial_3d",
        run_data.ModelColumns(
            series=(*planar.series, *spatial[1:]),
            events=planar.events,
            base=spatial,
            label="spatial",
        ),
    )
    assert run_data.model_label("spatial_3d") == "spatial"
    with pytest.raises(run_data.RunDataError) as err:
        run_data.read_series(tmp_path, "run", spatial, model="spatial_3d")
    assert str(err.value) == (
        f"{path} lacks spatial columns ['crossrange_m', 'heading_rad']; not a spatial_3d run"
    )
    _tiny_series(tmp_path, "empty", [])
    with pytest.raises(run_data.RunDataError, match=r"is empty \(a failed search writes no"):
        run_data.read_series_frame(tmp_path, "empty", ("t_s",), model="spatial_3d")


def test_animate_reads_the_series_as_written_and_replay_one_row_per_time(synth_dir: Path) -> None:
    """The synthetic series holds two rows at staging (600 kg, then 500 kg). The
    animation keeps both, in file order (its data did not change in SP2 A1); the replay
    read keeps the later one."""
    expected_rows = SYNTH_SERIES_ROWS
    before_kg = SYNTH_M0_KG - SYNTH_BURN1_KGPS * SYNTH_T_STAGING_S
    runs, _ = plots.load_animation_runs(synth_dir, ["pad"])
    pad = runs[0]
    assert len(pad.t_s) == expected_rows
    assert pad.t_s[0] == -SYNTH_PUSH_S and pad.t_s[1] == SYNTH_GRID_START_S
    at_staging = pad.t_s == SYNTH_T_STAGING_S
    assert pad.m_kg[at_staging].tolist() == [before_kg, before_kg - SYNTH_STAGE_DROP_KG]
    assert pad.phase[at_staging].tolist() == ["GRAVITY_TURN", "COAST_STAGING"]
    frame = replay.read_series(synth_dir, "pad")
    assert len(frame) == expected_rows - 1
    row = frame[frame["t_rel_release_s"] == SYNTH_T_STAGING_S]
    assert row["m_kg"].tolist() == [before_kg - SYNTH_STAGE_DROP_KG]
    assert row["phase"].tolist() == ["COAST_STAGING"]


def test_sample_grid() -> None:
    """Both ends, 0.1 s steps up to 40 s and 1 s steps after it; an end that lies on a
    step is one sample, not two; a run that ends before 40 s has no late part."""
    grid = run_data.sample_grid(-2.6073, 60.0)
    assert grid[0] == -2.6073 and grid[1] == pytest.approx(-2.6, abs=1e-12)
    assert grid[-1] == 60.0 and run_data.GRID_EARLY_END_S in grid
    inner = grid[1:-1]
    early = inner[:-1] < run_data.GRID_EARLY_END_S
    assert np.allclose(np.diff(inner)[early], run_data.GRID_EARLY_DT_S)
    assert np.allclose(np.diff(inner)[~early], run_data.GRID_LATE_DT_S)
    # -2.6 to 39.9 in 0.1 s steps (426), 40 to 59 in 1 s steps (20), and the two ends
    assert len(grid) == 426 + 20 + 2
    on_step = run_data.sample_grid(-2.0, 60.0)
    assert on_step[0] == -2.0 and on_step[1] == pytest.approx(-1.9, abs=1e-12)
    assert len(on_step) == 420 + 20 + 1 and len(set(on_step.tolist())) == len(on_step)
    short = run_data.sample_grid(0.0, 0.35)
    assert short.tolist() == pytest.approx([0.0, 0.1, 0.2, 0.3, 0.35], abs=1e-12)
    assert np.all(np.diff(grid) > 0.0)


def test_defined_mask_and_series_values() -> None:
    """Linear interpolation between the bracketing source rows, rounded; None where a
    bracketing value is undefined, but a sample on a defined source time needs only
    that one; an all-NaN series is all None; -0.0 is written 0.0."""
    t = np.array([0.0, 1.0, 2.0, 3.0])
    values = np.array([math.nan, 10.0, 20.0, 40.0])
    grid = np.array([0.0, 0.5, 1.0, 1.25, 2.0, 2.5, 3.0])
    assert run_data.defined_mask(t, values, grid) == [False, False, True, True, True, True, True]
    out = run_data.series_values(t, values, grid, 2)
    # 10 + 0.25 (20 - 10) = 12.5 and 20 + 0.5 (40 - 20) = 30
    assert out == [None, None, 10.0, 12.5, 20.0, 30.0, 40.0]
    gap = np.array([1.0, math.nan, 3.0, 4.0])
    assert run_data.series_values(t, gap, np.array([0.0, 0.5, 1.0, 1.5, 2.0, 2.5]), 1) == [
        1.0,
        None,
        None,
        None,
        3.0,
        3.5,
    ]
    assert run_data.series_values(t, np.full(4, math.nan), grid, 1) == [None] * len(grid)
    third = run_data.series_values(t, np.array([0.0, 1.0, 2.0, 3.0]) / 3.0, np.array([0.5]), 3)
    assert third == [0.167]  # (0 + 1/3) / 2 = 0.1666...
    zero = run_data.series_values(t, np.array([-1e-9, -1e-9, 0.0, 0.0]), np.array([0.5]), 3)
    assert zero == [0.0] and _sign(zero[0]) == 1.0


def test_run_series_takes_the_field_list(synth_dir: Path) -> None:
    """Keys are t, the fields in list order, phase; values follow the fixture's closed
    forms (10.3 s lies between the rows at 10.0 and 10.5 s); a field added to the list
    leaves every other list as it was."""
    frame = run_data.read_series(synth_dir, "silo", SYNTH_SERIES_COLUMNS)
    series = run_data.run_series(frame, REPLAY_FIELDS)
    assert list(series) == ["t", *(field for field, *_ in REPLAY_FIELDS), "phase"]
    grid = run_data.sample_grid(-SYNTH_PUSH_S, SYNTH_T_END_S)
    assert series["t"] == [round(float(t), run_data.TIME_DECIMALS) for t in grid]
    assert all(len(values) == len(grid) for values in series.values())
    k = series["t"].index(10.3)
    lo, hi = _synth_row(10.0, True, False), _synth_row(10.5, True, False)
    for field, column, scale, decimals in (
        ("alt_m", "alt_m", 1.0, 1),
        ("x_km", "downrange_m", 1e-3, 3),
        ("v", "speed_rel_mps", 1.0, 2),
        ("m_t", "m_kg", 1e-3, 3),
        ("q_kpa", "q_pa", 1e-3, 3),
        ("mach", "mach", 1.0, 3),
    ):
        expected = scale * (lo[column] + 0.6 * (hi[column] - lo[column]))
        assert series[field][k] == pytest.approx(expected, abs=0.5 * 10.0**-decimals + 1e-9), field
    shaft = [q for t, q in zip(series["t"], series["q_kpa"], strict=True) if t < 0.0]
    assert shaft and all(q is None for q in shaft)  # the vented shaft has no q
    assert series["phase"][0] == "ASSIST" and series["phase"][-1] == "LTG_BURN"
    at_staging = series["t"].index(SYNTH_T_STAGING_S)
    assert series["phase"][at_staging] == "COAST_STAGING"  # the later of the two rows
    assert series["m_t"][at_staging] == pytest.approx(0.5, abs=1e-12)
    more = run_data.run_series(frame, [*REPLAY_FIELDS, ("extra", "extra", None, 1)])
    assert list(more) == [*list(series)[:-1], "extra", "phase"]
    assert {k: v for k, v in more.items() if k != "extra"} == series
    assert set(more["extra"]) == {7.0}
    only = run_data.run_series(frame, [("m_kg", "m_kg", None, 1)])
    assert list(only) == ["t", "m_kg", "phase"] and only["m_kg"][0] == SYNTH_M0_KG


RUNS_DATA_KEYS = ("t", *(field for field, *_ in replay.SERIES_FIELDS), "phase", "events")
"""The keys of a replay-page run record that hold the run's data: the clock, the eight
resampled series, the phase per sample and the events. The other keys hold text (label,
detail), flags and headline metrics, which later steps may deliberately reword (A1a,
D-SP2-23: the paired-pad label and the offload note), so they are not pinned here."""
RUNS_DIGESTS = {
    (
        "pad",
        "silo",
        "silo__aero_bound",
        "pad__aero_bound",
    ): "374ec4c19a86f2a5b5d21f7396f7b7ef807a283ee83862a9b83b68332ccc83b0",
    (
        "pad",
        "alt_low",
        "silo_s1",
        "silo_s1__pad",
    ): "57c85bf3f742305eaeb1979f21d8cab4b30763253d19b932276f045b536a77b4",
}
"""sha256 of ``json.dumps([{k: r[k] for k in RUNS_DATA_KEYS} for r in runs])``, with
``runs = replay.replay_data(run_dir, names)["runs"]``, for two selections of the
synthetic directory (``_synth_run_dir``), which between them hold every role. Computed
with the ORIGINAL code, before run_data existed: the package as it was at the SP2 start
commit a5b8133 put first on PYTHONPATH, the directory built by this file's _synth_*
functions (which need nothing of launchsim). They pin the series (the sort, the
keep-last rows, the grid, the rounding of the sample times to TIME_DECIMALS: the first
sample is at -2.0371 s), the phase per sample and the events (file order, the six keys,
the rounding of three event times that carry digits beyond TIME_DECIMALS, the -0.0 of a
small negative downrange), without pinning the page template or the records' text
(survey 06, gate step 5). Never recaptured for a refactor: a digest that moves means
the replay page's data moved. The numbers behind them depend on numpy's interpolation
and pandas' float parser only."""


def test_runs_block_digest_is_the_one_of_the_sp2_start_commit(tmp_path: Path) -> None:
    run_dir = _synth_run_dir(tmp_path)
    for names, digest in RUNS_DIGESTS.items():
        runs = replay.replay_data(run_dir, list(names))["runs"]
        assert all(set(RUNS_DATA_KEYS) <= set(record) for record in runs)
        text = json.dumps([{key: record[key] for key in RUNS_DATA_KEYS} for record in runs])
        assert hashlib.sha256(text.encode("utf-8")).hexdigest() == digest, names
        assert text.count('"x_km": -0.0') == len(names)  # one kick_start per run
    pad = replay.replay_data(run_dir, ["pad"])["runs"][0]
    kick = next(e for e in pad["events"] if e["name"] == "kick_start")
    assert kick["x_km"] == 0.0 and _sign(kick["x_km"]) == -1.0
    # the pinned data exercise the page's rounding of times to TIME_DECIMALS
    assert pad["t"][:2] == [-2.037, -2.0]
    times = [e["t"] for e in pad["events"]]
    assert (times[0], times[4], times[8]) == (-2.037, 12.494, 50.271)


# ---------------------------------------------------------------- events


def test_read_events_returns_every_row_of_an_eight_column_file(synth_dir: Path) -> None:
    """Every row in file order (propellant, end and the second ignition included), the
    time after release, and NaN or None for what the eight-column file does not hold."""
    path = synth_dir / "pad" / "events.csv"
    assert path.read_text(encoding="utf-8").splitlines()[0] == ",".join(SYNTH_EVENT_COLUMNS)
    rows = run_data.read_events(path, SYNTH_OFFSET_S)
    listed = _synth_events(False)
    assert [r.name for r in rows] == [e["event"] for e in listed]
    assert [r.name for r in rows] == [
        "ignition",
        "release",
        "liftoff",
        "kick_start",
        "kick_end",
        "propellant",
        "staging",
        "ignition",
        "fairing",
        "cutoff",
        "end",
    ]
    for row, event in zip(rows, listed, strict=True):
        assert row.t_s == event["t_s"] and row.t_rel_s == event["t_s"] - SYNTH_OFFSET_S
        assert (row.phase, row.stage) == (event["phase"], event["stage"])
        assert (row.alt_m, row.downrange_m) == (event["alt_m"], event["downrange_m"])
        assert (row.speed_rel_mps, row.m_kg) == (event["speed_rel_mps"], event["m_kg"])
        assert math.isnan(row.speed_inertial_mps) and math.isnan(row.gamma_rel_rad)
        assert (row.m_before_kg, row.m_after_kg, row.dropped, row.recorded) == (
            None,
            None,
            None,
            True,
        )
    assert rows[3].downrange_m == SYNTH_KICK_DOWNRANGE_M
    staging = rows[6]
    assert staging.phase == COAST_STAGING and staging.stage == "stage2"
    assert staging.m_kg == rows[5].m_kg - SYNTH_STAGE_DROP_KG
    with pytest.raises(dataclasses.FrozenInstanceError):
        staging.m_kg = 0.0  # type: ignore[misc]


def test_read_events_needs_only_time_and_name(tmp_path: Path) -> None:
    """A two-column file reads (everything else NaN or None); a ``required`` column the
    file lacks is refused; a missing file is no events."""
    path = tmp_path / "events.csv"
    path.write_text("t_s,event\n5.0,release\n7.5,end\n", encoding="utf-8")
    rows = run_data.read_events(path, 5.0)
    assert [(r.name, r.t_s, r.t_rel_s) for r in rows] == [("release", 5.0, 0.0), ("end", 7.5, 2.5)]
    assert rows[0].phase is None and rows[0].stage is None
    assert all(
        math.isnan(v)
        for v in (rows[0].alt_m, rows[0].downrange_m, rows[0].speed_rel_mps, rows[0].m_kg)
    )
    with pytest.raises(run_data.RunDataError) as err:
        run_data.read_events(path, 0.0, required=("t_s", "event", "m_kg", "phase"))
    assert str(err.value) == f"{path} lacks event columns ['m_kg', 'phase']"
    path.write_text("t,event\n5.0,release\n", encoding="utf-8")
    with pytest.raises(run_data.RunDataError, match=r"lacks event columns \['t_s'\]"):
        run_data.read_events(path, 0.0)
    assert run_data.read_events(tmp_path / "missing.csv", 0.0) == []


# The recorded pad of results/silo_screening_2d/20260930T175743Z (events.csv, kg and s):
# the stage-1 propellant row, the staging row 22,200 kg lighter, stage-2 ignition 11 s
# later at the same mass, the fairing row in the burn, the cutoff.
T_STAGING_S = 151.328437545
T_IGN2_S = 162.328437545
T_FAIRING_S = 196.807530921
T_CUTOFF_S = 536.300685158
M_PROPELLANT_KG = 161_454.396243
M_STAGING_KG = 139_254.396243
M_FAIRING_KG = 129_343.226242
M_CUTOFF_KG = 30_054.3967097
M_DRY1_KG = 22_200.0
M_FAIR_KG = 1_700.0
HEATING = "free_molecular_heating"


def _event(
    name: str, t_s: float, phase: str | None, stage: str | None, m_kg: float
) -> run_data.EventRow:
    """A hand-written EventRow (finite everywhere unless ``m_kg`` is not, so rows
    compare with ==)."""
    return run_data.EventRow(
        t_s=t_s,
        t_rel_s=t_s,
        name=name,
        phase=phase,
        stage=stage,
        alt_m=1000.0 * t_s,
        downrange_m=2000.0 * t_s,
        speed_rel_mps=10.0 * t_s,
        speed_inertial_mps=10.0 * t_s + 400.0,
        gamma_rel_rad=0.4,
        m_kg=m_kg,
    )


def _masses(trigger: str, fairing_kg: float = M_FAIR_KG) -> run_data.VehicleMasses:
    """The gate vehicle's masses with the given fairing rule (22.2 t, 4.0 t, 1.7 t)."""
    return run_data.VehicleMasses(
        stage_names=("stage1", "stage2"),
        stage_dry_kg=(M_DRY1_KG, 4_000.0),
        stage_propellant_kg=(410_900.0, 107_500.0),
        fairing_kg=fairing_kg,
        payload_kg=22_800.0,
        fairing_trigger=trigger,
    )


def _hand_rows(
    propellant_kg: float, fairing: run_data.EventRow | None = None, after: str = "ignition"
) -> list[run_data.EventRow]:
    """The event rows of a staged run in file order: stage-1 depletion at
    ``propellant_kg``, the staging row at M_STAGING_KG (after the map), stage-2
    ignition, the cutoff and the end, with ``fairing`` (when given) right after the
    last row named ``after``, where the planner logs it."""
    rows = [
        _event("ignition", -2.0, "HOLD", "stage1", 572_354.396243),
        _event("release", 0.0, "HOLD", "stage1", 569_656.935371),
        _event("propellant", T_STAGING_S, "GRAVITY_TURN", "stage1", propellant_kg),
        _event("staging", T_STAGING_S, COAST_STAGING, "stage2", M_STAGING_KG),
        _event("ignition", T_IGN2_S, LTG_BURN, "stage2", M_STAGING_KG),
        _event("cutoff", T_CUTOFF_S, LTG_BURN, "stage2", M_CUTOFF_KG),
        _event("end", T_CUTOFF_S, LTG_BURN, "stage2", M_CUTOFF_KG),
    ]
    if fairing is not None:
        at = max(i for i, r in enumerate(rows) if r.name == after)
        rows.insert(at + 1, fairing)
    return rows


FAIRING_IN_BURN_ROW = _event("fairing", T_FAIRING_S, LTG_BURN, "stage2", M_FAIRING_KG)
FAIRING_AT_IGNITION_ROW = _event("fairing", T_IGN2_S, LTG_BURN, "stage2", M_STAGING_KG)
FAIRING_AT_STAGING_ROW = _event("fairing", T_STAGING_S, COAST_STAGING, "stage2", M_STAGING_KG)
WITH_FAIRING_KG = M_PROPELLANT_KG + M_FAIR_KG
"""Mass at stage-1 depletion of a run whose staging map also drops the fairing and
leaves M_STAGING_KG [kg]: 139,254.396243 + 22,200 + 1,700 = 163,154.396243."""

HAND_CASES: dict[str, tuple[list[run_data.EventRow], run_data.VehicleMasses, str | None]] = {
    "in_burn": (
        _hand_rows(M_PROPELLANT_KG, FAIRING_IN_BURN_ROW),
        _masses(HEATING),
        metrics_planar.FAIRING_IN_BURN,
    ),
    "at_ignition": (
        _hand_rows(M_PROPELLANT_KG, FAIRING_AT_IGNITION_ROW),
        _masses(HEATING),
        metrics_planar.FAIRING_AT_IGNITION,
    ),
    "at_staging_recorded": (
        _hand_rows(WITH_FAIRING_KG, FAIRING_AT_STAGING_ROW, after="staging"),
        _masses(HEATING),
        metrics_planar.FAIRING_AT_STAGING,
    ),
    "at_staging_unrecorded": (
        _hand_rows(WITH_FAIRING_KG),
        _masses("staging"),
        metrics_planar.FAIRING_AT_STAGING,
    ),
    "kept_rule_never": (
        _hand_rows(M_PROPELLANT_KG),
        _masses("never"),
        metrics_planar.FAIRING_KEPT,
    ),
    "kept_criterion_not_met": (
        _hand_rows(M_PROPELLANT_KG),
        _masses(HEATING),
        metrics_planar.FAIRING_KEPT,
    ),
    "no_fairing": (_hand_rows(M_PROPELLANT_KG), _masses("staging", 0.0), None),
}
"""name -> (event rows, vehicle masses, the run's ``fairing_drop`` metric): the four ways
the planner logs a fairing drop, the two ways a fairing is kept, and a vehicle without
a fairing (its metric is None)."""

HAND_EXPECTED: dict[str, tuple[tuple[float, float], tuple[float, float] | None]] = {
    "in_burn": ((M_PROPELLANT_KG, M_STAGING_KG), (M_FAIRING_KG, M_FAIRING_KG - M_FAIR_KG)),
    "at_ignition": ((M_PROPELLANT_KG, M_STAGING_KG), (M_STAGING_KG, M_STAGING_KG - M_FAIR_KG)),
    "at_staging_recorded": (
        (WITH_FAIRING_KG, M_STAGING_KG + M_FAIR_KG),
        (M_STAGING_KG + M_FAIR_KG, M_STAGING_KG),
    ),
    "at_staging_unrecorded": (
        (WITH_FAIRING_KG, M_STAGING_KG + M_FAIR_KG),
        (M_STAGING_KG + M_FAIR_KG, M_STAGING_KG),
    ),
    "kept_rule_never": ((M_PROPELLANT_KG, M_STAGING_KG), None),
    "kept_criterion_not_met": ((M_PROPELLANT_KG, M_STAGING_KG), None),
    "no_fairing": ((M_PROPELLANT_KG, M_STAGING_KG), None),
}
"""name -> ((mass before, after) of the stage drop, (before, after) of the fairing drop
or None) [kg], by hand: 139,254.396243 + 22,200 = 161,454.396243 and, when the staging
map takes the fairing too, + 1,700 = 163,154.396243 before and 140,954.396243 between
the two links; 129,343.226242 - 1,700 = 127,643.226242 after the drop in the burn."""


@pytest.mark.parametrize("case", sorted(HAND_CASES))
def test_drop_masses_of_the_fairing_cases_on_hand_rows(case: str) -> None:
    """The mass before and after the stage drop and the fairing drop of each case, from
    the run's metric and, the metric removed, from the rows and the vehicle's rule; the
    stage-1 depletion row holds the staging 'before'; the two drops form a chain; only
    rule staging adds a row, marked not recorded."""
    rows, masses, metric = HAND_CASES[case]
    (stage_before, stage_after), fairing_expected = HAND_EXPECTED[case]
    out = run_data.with_drop_masses(rows, masses, metric)
    assert run_data.with_drop_masses(rows, masses, None) == out  # the metric is not needed
    assert run_data.fairing_case(rows, None, masses) == metric
    assert run_data.fairing_case(rows, metric, masses) == metric
    staging = next(r for r in out if r.name == "staging")
    assert staging.m_before_kg == pytest.approx(stage_before, abs=1e-9)
    assert staging.m_after_kg == pytest.approx(stage_after, abs=1e-9)
    assert staging.dropped == "stage1" and staging.recorded
    propellant = next(r for r in out if r.name == "propellant")
    assert propellant.m_before_kg == propellant.m_after_kg == propellant.m_kg
    assert propellant.m_kg == pytest.approx(staging.m_before_kg, abs=1e-9)
    fairings = [r for r in out if r.name == "fairing"]
    added = [r for r in out if not r.recorded]
    if fairing_expected is None:
        assert fairings == [] and added == [] and len(out) == len(rows)
    else:
        (fairing,) = fairings
        assert fairing.m_before_kg == pytest.approx(fairing_expected[0], abs=1e-9)
        assert fairing.m_after_kg == pytest.approx(fairing_expected[1], abs=1e-9)
        assert fairing.dropped == "fairing"
        if case.startswith("at_staging"):  # one map, two links: stage first, then fairing
            assert out.index(fairing) == out.index(staging) + 1
            assert fairing.m_before_kg == staging.m_after_kg
            assert (fairing.t_s, fairing.phase, fairing.m_kg) == (
                staging.t_s,
                COAST_STAGING,
                staging.m_kg,
            )
        assert added == ([fairing] if case == "at_staging_unrecorded" else [])
        assert len(out) == len(rows) + len(added)
    for row in out:  # nothing recorded is changed, and every other row drops nothing
        if row.recorded:
            source = dataclasses.replace(row, m_before_kg=None, m_after_kg=None, dropped=None)
            assert source in rows
        if row.name not in ("staging", "fairing"):
            assert (row.m_before_kg, row.m_after_kg, row.dropped) == (row.m_kg, row.m_kg, None)
    assert [r for r in out if r.recorded and r.dropped is None and r.name == "staging"] == []


def test_drop_masses_follow_the_row_phase_and_the_metric_only_fills_the_gap() -> None:
    """A fairing row's phase decides which side of the drop it holds, whatever the
    metric says; without a fairing row the metric 'at staging' (or, without a metric,
    rule staging) makes the unrecorded drop, and 'kept' prevents it; a run that never
    staged, a row without a mass and a staging row of an unknown stage keep None."""
    rows, masses, _ = HAND_CASES["in_burn"]
    wrong = run_data.with_drop_masses(rows, masses, metrics_planar.FAIRING_AT_STAGING)
    assert wrong == run_data.with_drop_masses(rows, masses, metrics_planar.FAIRING_IN_BURN)
    rows, masses, _ = HAND_CASES["at_staging_unrecorded"]
    kept = run_data.with_drop_masses(rows, masses, metrics_planar.FAIRING_KEPT)
    assert len(kept) == len(rows) and all(r.recorded for r in kept)
    staging = next(r for r in kept if r.name == "staging")
    assert staging.m_before_kg == pytest.approx(M_STAGING_KG + M_DRY1_KG, abs=1e-9)
    forced = run_data.with_drop_masses(rows, _masses("never"), metrics_planar.FAIRING_AT_STAGING)
    assert [r.name for r in forced if not r.recorded] == ["fairing"]
    # idempotent: the added row reads back as a drop logged at staging
    again = run_data.with_drop_masses(forced, _masses("staging"), None)
    assert [(r.name, r.m_before_kg, r.m_after_kg, r.recorded) for r in again] == [
        (r.name, r.m_before_kg, r.m_after_kg, r.recorded) for r in forced
    ]
    failed = [
        _event("push_start", 0.0, "ASSIST", "stage1", 500_000.0),
        _event("ignition_failed", 2.6, "COAST", "stage1", 500_000.0),
        _event("impact", 15.7, "COAST", "stage1", 500_000.0),
    ]
    assert run_data.fairing_case(failed, None, _masses("staging")) is None
    out = run_data.with_drop_masses(failed, _masses("staging"), None)
    assert [(r.m_before_kg, r.m_after_kg, r.dropped) for r in out] == [
        (500_000.0,) * 2 + (None,)
    ] * 3
    massless = [_event("staging", 5.0, COAST_STAGING, "stage2", math.nan)]
    (row,) = run_data.with_drop_masses(massless, _masses("never"), None)
    assert (row.m_before_kg, row.m_after_kg, row.dropped) == (None, None, "stage1")
    unknown = [_event("staging", 5.0, COAST_STAGING, "stage1", 100.0)]  # nothing before stage1
    (row,) = run_data.with_drop_masses(unknown, _masses("never"), None)
    assert (row.m_before_kg, row.m_after_kg, row.dropped) == (None, None, None)
    unnamed = [_event("staging", 5.0, COAST_STAGING, None, 100.0)]  # no stage column
    (row,) = run_data.with_drop_masses(unnamed, _masses("never"), None)
    assert (row.m_before_kg, row.m_after_kg, row.dropped) == (100.0 + M_DRY1_KG, 100.0, "stage1")


def test_without_masses_nothing_is_filled_and_nothing_fails() -> None:
    """A caller without a complete vehicle block (the fixtures' ``{name: toy_2d}``)
    passes None: the rows come back as they are, no row is added, whatever the metric
    and whatever the rows hold."""
    odd = [
        _event("staging", 1.0, None, None, math.nan),
        _event("fairing", 1.0, "NOWHERE", "stage2", -5.0),
        _event("staging", 2.0, COAST_STAGING, "stage2", 10.0),
    ]
    for rows in (HAND_CASES["at_staging_unrecorded"][0], odd, []):
        for metric in (None, metrics_planar.FAIRING_AT_STAGING, "not a form"):
            out = run_data.with_drop_masses(rows, None, metric)
            assert len(out) == len(rows) and out is not rows
            assert all(a is b for a, b in zip(out, rows, strict=True))
    assert run_data.fairing_case(HAND_CASES["kept_rule_never"][0], None, None) is None
    assert run_data.fairing_case(HAND_CASES["in_burn"][0], None, None) == (
        metrics_planar.FAIRING_IN_BURN
    )
    assert run_data.fairing_case(HAND_CASES["at_ignition"][0], None, None) == (
        metrics_planar.FAIRING_AT_IGNITION
    )


def test_projections_show_recorded_rows_only_and_no_mass_key(tmp_path: Path) -> None:
    """The replay's and the animation's event lists are projections of the recorded
    rows: on a directory of a rule-staging run (no fairing row) neither gains the row
    ``with_drop_masses`` adds, and the replay's dicts hold exactly their six keys, in
    order, with a small negative downrange kept as -0.0."""
    path = tmp_path / "events.csv"
    lines = [
        ",".join(SYNTH_EVENT_COLUMNS),
        "0.0,release,HOLD,stage1,0.0,0.0,0.0,1000.0",
        "1.0,kick_start,VERTICAL_RISE,stage1,301.049,-0.157654,50.0,990.0",
        "40.0,propellant,GRAVITY_TURN,stage1,69485.82156,99171.0175,2665.0318,600.0",
        "40.0,staging,COAST_STAGING,stage2,69485.82156,99171.0175,2665.0318,500.0",
        "41.0,ignition,LTG_BURN,stage2,80432.6,125813.4,2625.5,500.0",
        "60.0,cutoff,LTG_BURN,stage2,199999.98,1660290.86,7362.706,300.0",
        "60.0,end,LTG_BURN,stage2,199999.98,1660290.86,7362.706,300.0",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rows = run_data.read_events(path, 0.0)
    added = run_data.with_drop_masses(rows, _masses("staging"), None)
    assert len(added) == len(rows) + 1
    events = replay.run_events(path, 0.0)
    assert [e["name"] for e in events] == [r.name for r in rows]
    assert all(list(e) == ["t", "name", "stage", "alt_m", "x_km", "v"] for e in events)
    assert events[1] == {
        "t": 1.0,
        "name": "kick_start",
        "stage": "stage1",
        "alt_m": 301.0,
        "x_km": -0.0,
        "v": 50.0,
    }
    assert _sign(events[1]["x_km"]) == -1.0  # not routed through finite
    assert events[3] == {
        "t": 40.0,
        "name": "staging",
        "stage": "stage2",
        "alt_m": 69485.8,
        "x_km": 99.171,
        "v": 2665.03,
    }
    drawn = plots._events(path, 0.0)
    assert [e.label for e in drawn] == ["release", "MECO/staging", "S2 ignition", "cutoff"]
    assert drawn[1] == plots.AnimationEvent(
        40.0, "MECO/staging", 69485.82156, 99171.0175, 2665.0318
    )
    assert replay.run_events(tmp_path / "missing.csv", 0.0) == []
    assert plots._events(tmp_path / "missing.csv", 0.0) == ()


# ---------------------------------------------------------------- real rows from the planner

P2 = PLANAR_LAYOUT
OMEGA_P = OMEGA_EARTH_RADS * math.cos(math.radians(28.5))  # azimuth 90 deg
ENV = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), OMEGA_P, ambient_scalar)
SAMPLE_DT_S = 0.5
"""Sampling interval [s] of the time series written from a planner trace."""
STAGE1_DELTA_RAD = math.radians(3.0)
"""Kick angle of the stage-1 flights (tests/test_planar_events.py flies the same)."""
GAMMA_STAR_RAD = math.radians(20.0)
"""Flight-path angle the insertion flights turn to (tests/test_engine_planar.py)."""
MET_AT_STAGING_W_M2 = 1.0e12
"""A heating limit far above the rate at MECO: the criterion is already met at staging."""
PLANAR_SERIES = run_data.MODEL_COLUMNS[PLANAR_2D].series
PLANAR_EVENTS = run_data.MODEL_COLUMNS[PLANAR_2D].events


@pytest.fixture(scope="module")
def gate_block(repo_root: Path) -> dict[str, Any]:
    """The raw vehicle file of the gate fork (generic_f9_class_2d.yaml): a vehicle block
    as resolved_config.yaml holds it."""
    path = repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _block_with_rule(block: dict[str, Any], rule: Any) -> dict[str, Any]:
    """A copy of a vehicle block with ``fairing_drop`` set to ``rule``: a string, a
    heating limit [W/m^2] (a float), or None for no key at all."""
    out = copy.deepcopy(block)
    out.pop("fairing_drop", None)
    if isinstance(rule, float):
        limit = {"value": rule, "assumed": True}
        out["fairing_drop"] = {"trigger": HEATING, "limit_W_m2": limit}
    elif rule is not None:
        out["fairing_drop"] = rule
    return out


def _planner(vehicle: Vehicle, end: str, *, dense: bool = True) -> PlanarPlanner:
    """The planner of tests/test_engine_planar.py and tests/test_planar_events.py: the
    pad lit 2 s before release, kick at 50 m/s, rtol 1e-10; ``end`` 'stage1_burnout' or
    'insertion' (to a 200 km circular orbit)."""
    return PlanarPlanner(
        vehicle,
        {"stage1": IgnitionSpec(-2.0), "stage2": IgnitionSpec(0.0)},
        GuidanceSpec(50.0, 60.0, 60.0),
        ENV,
        end,
        IntegratorSettings(rtol=1e-10, dense_output=dense),
        target=TargetOrbit(R_EARTH_M + 200.0e3),
        ltg=LtgSettings.from_config(LtgConfig(), final=False),
    )


@dataclasses.dataclass(frozen=True)
class RealRun:
    """A planner flight written as a run folder and read back through run_data: the
    vehicle flown, the masses run_data reads from the same vehicle block, the planner's
    trace, the series as replay reads it (one row per time) and as written, the event
    rows, and the run's ``fairing_drop`` metric (metrics_planar.fairing_items)."""

    vehicle: Vehicle
    masses: run_data.VehicleMasses
    trace: RunTrace
    frame: pd.DataFrame
    raw: pd.DataFrame
    rows: list[run_data.EventRow]
    metric: str | None

    @property
    def m_meco_kg(self) -> float:
        """Mass at stage-1 burnout, before the staging map [kg] (the planner's state)."""
        return float(P2.get(self.trace.burnouts["stage1"][1], "m_kg"))

    def series_mass_kg(self, t_s: float, *, first: bool = False) -> float:
        """m_kg of the time-series row at the absolute time t_s [s]: the later of two
        rows at a boundary (as replay reads it), or with ``first`` the earlier one."""
        frame = self.raw if first else self.frame
        at = frame[np.isclose(frame["t_s"], t_s, rtol=0.0, atol=1e-9)]
        assert len(at) == (2 if first else 1)
        return float(at["m_kg"].iloc[0])


def _real_run(
    root: Path, name: str, block: dict[str, Any], fly: Callable[[Vehicle], RunTrace]
) -> RealRun:
    """Fly the vehicle of ``block`` with ``fly``, write its time series and events under
    ``root``/``name`` with results_io's CSV writer (%.12g), and read both back."""
    vehicle = VehicleConfig.model_validate(block).to_vehicle()
    trace = fly(vehicle)
    folder = root / name
    folder.mkdir(parents=True)
    series = metrics_planar.sample_trace_planar(trace, vehicle, SAMPLE_DT_S)
    results_io.write_csv(folder / run_data.SERIES_FILE, series)
    results_io.write_csv(folder / run_data.EVENTS_FILE, metrics_planar.events_frame_planar(trace))
    frame = run_data.read_series(root, name, PLANAR_SERIES)
    return RealRun(
        vehicle=vehicle,
        masses=run_data.vehicle_masses(block),
        trace=trace,
        frame=frame,
        raw=run_data.read_series_frame(root, name, PLANAR_SERIES),
        rows=run_data.read_events(folder / run_data.EVENTS_FILE, run_data.release_offset_s(frame)),
        metric=metrics_planar.fairing_items(trace, vehicle)["fairing_drop"],
    )


def _fly_stage1(vehicle: Vehicle) -> RunTrace:
    """Stage 1 through staging and the staging coast (the planner call of
    tests/test_planar_events.py::test_staging_map_and_coast, dense output on)."""
    planner = _planner(vehicle, "stage1_burnout")
    return planner.stage1(STAGE1_DELTA_RAD, planner.start()).prefix


def _check_real_staging(run: RealRun, out: list[run_data.EventRow], fairing_kg: float) -> None:
    """The stage drop of a real run: before = the planner's burnout mass, after = that
    less stage 1's dry mass (the staging row itself holding ``fairing_kg`` less when the
    map took the fairing); the stage-1 depletion row and the earlier series row at that
    time hold the 'before'."""
    m_dry = run.vehicle.stages[0].dry_mass_kg
    staging = next(r for r in out if r.name == "staging")
    assert staging.dropped == "stage1" and staging.phase == COAST_STAGING
    assert staging.m_before_kg == pytest.approx(run.m_meco_kg, abs=MASS_TOL_KG)
    assert staging.m_after_kg == pytest.approx(run.m_meco_kg - m_dry, abs=MASS_TOL_KG)
    assert staging.m_kg == pytest.approx(run.m_meco_kg - m_dry - fairing_kg, abs=MASS_TOL_KG)
    propellant = next(r for r in out if r.name == "propellant")
    assert propellant.m_after_kg == pytest.approx(staging.m_before_kg, abs=MASS_TOL_KG)
    assert run.series_mass_kg(staging.t_s, first=True) == pytest.approx(
        staging.m_before_kg, abs=MASS_TOL_KG
    )


@pytest.mark.parametrize(
    ("rule", "form", "recorded"),
    [
        (MET_AT_STAGING_W_M2, metrics_planar.FAIRING_AT_STAGING, True),
        ("staging", metrics_planar.FAIRING_AT_STAGING, False),
        (None, metrics_planar.FAIRING_AT_STAGING, False),  # no key: config.py's default
    ],
    ids=["criterion_met_at_staging", "rule_staging", "rule_absent"],
)
def test_fairing_dropped_at_staging_on_planner_rows(
    tmp_path: Path, gate_block: dict[str, Any], rule: Any, form: str, recorded: bool
) -> None:
    """Real rows of the two 'at staging' cases. Criterion already met at staging: the
    planner logs a fairing row in COAST_STAGING holding the mass after both drops. Rule
    staging (stated, or absent from the block): no fairing row, and the reader adds one
    at the staging time, marked not recorded. Either way the chain runs from the
    planner's burnout mass, less stage 1's dry mass (22,200 kg), less the fairing
    (1,700 kg), to the mass of the first row of the staging coast."""
    block = _block_with_rule(gate_block, rule)
    run = _real_run(tmp_path, "run", block, _fly_stage1)
    m_dry, fairing_kg = run.vehicle.stages[0].dry_mass_kg, run.vehicle.fairing_mass_kg
    assert (m_dry, fairing_kg) == (pytest.approx(22_200.0), pytest.approx(1_700.0))
    assert run.masses.fairing_trigger == ("staging" if isinstance(rule, str | None) else HEATING)
    assert run.metric == form
    logged = [r for r in run.rows if r.name == "fairing"]
    assert len(logged) == (1 if recorded else 0)
    out = run_data.with_drop_masses(run.rows, run.masses, run.metric)
    assert run_data.with_drop_masses(run.rows, run.masses, None) == out
    assert run_data.fairing_case(run.rows, None, run.masses) == form
    _check_real_staging(run, out, fairing_kg)
    staging = next(r for r in out if r.name == "staging")
    (fairing,) = [r for r in out if r.name == "fairing"]
    assert fairing.recorded is recorded and len(out) == len(run.rows) + (0 if recorded else 1)
    assert out.index(fairing) == out.index(staging) + 1
    assert (fairing.t_s, fairing.phase, fairing.dropped) == (staging.t_s, COAST_STAGING, "fairing")
    assert fairing.m_before_kg == staging.m_after_kg
    assert fairing.m_after_kg == pytest.approx(run.m_meco_kg - m_dry - fairing_kg, abs=MASS_TOL_KG)
    # the first row of the staging coast (the later row at the staging time) agrees
    assert run.series_mass_kg(staging.t_s) == pytest.approx(fairing.m_after_kg, abs=MASS_TOL_KG)


@pytest.mark.parametrize("rule", ["never", "gate"], ids=["rule_never", "criterion_not_met"])
def test_fairing_kept_through_staging_on_planner_rows(
    tmp_path: Path, gate_block: dict[str, Any], rule: str
) -> None:
    """Real rows of a fairing that stays on at staging (rule never; the gate's own
    heating rule, not met at MECO): the staging map drops stage 1 alone and nothing is
    added."""
    block = gate_block if rule == "gate" else _block_with_rule(gate_block, rule)
    run = _real_run(tmp_path, "run", block, _fly_stage1)
    assert run.metric == metrics_planar.FAIRING_KEPT
    assert run_data.fairing_case(run.rows, None, run.masses) == metrics_planar.FAIRING_KEPT
    out = run_data.with_drop_masses(run.rows, run.masses, run.metric)
    assert run_data.with_drop_masses(run.rows, run.masses, None) == out
    assert len(out) == len(run.rows) and not [r for r in out if r.name == "fairing"]
    _check_real_staging(run, out, 0.0)
    staging = next(r for r in out if r.name == "staging")
    assert run.series_mass_kg(staging.t_s) == pytest.approx(staging.m_after_kg, abs=MASS_TOL_KG)


def test_zero_mass_fairing_row_is_no_drop_on_planner_rows(
    tmp_path: Path, gate_block: dict[str, Any]
) -> None:
    """Real rows of a vehicle without a fairing mass under a heating rule met at
    staging: the planner logs a ``fairing`` row in COAST_STAGING all the same (its guard
    is the rule, not the mass), while metrics_planar.fairing_items reports no form. The
    reader follows the metric: no case, the staging map drops stage 1 alone, the fairing
    row is an ordinary row (before = after = its mass, nothing dropped) and no row is
    added."""
    block = _block_with_rule(gate_block, MET_AT_STAGING_W_M2)
    block["fairing_mass_t"] = {"value": 0.0, "assumed": True}
    run = _real_run(tmp_path, "run", block, _fly_stage1)
    assert run.masses.fairing_kg == 0.0 and not run_data.has_fairing(run.masses)
    assert run.metric is None
    logged = [r for r in run.rows if r.name == "fairing"]
    assert len(logged) == 1 and logged[0].phase == COAST_STAGING
    assert run_data.fairing_case(run.rows, None, run.masses) is None
    for metric in (run.metric, None):
        out = run_data.with_drop_masses(run.rows, run.masses, metric)
        assert len(out) == len(run.rows) and all(r.recorded for r in out)
        assert [r.name for r in out if r.dropped is not None] == ["staging"]
        _check_real_staging(run, out, 0.0)
        (fairing,) = [r for r in out if r.name == "fairing"]
        assert fairing.dropped is None and fairing.m_before_kg == fairing.m_after_kg == fairing.m_kg
        staging = next(r for r in out if r.name == "staging")
        assert fairing.m_kg == staging.m_after_kg == pytest.approx(run.m_meco_kg - 22_200.0)
    # one stage: no form either, whatever the rows hold
    one_stage = dataclasses.replace(
        run.masses, stage_names=run.masses.stage_names[:1], fairing_kg=1_700.0
    )
    assert not run_data.has_fairing(one_stage)
    assert run_data.fairing_case(run.rows, None, one_stage) is None
    out = run_data.with_drop_masses(run.rows, one_stage, None)
    assert len(out) == len(run.rows) and all(r.dropped != "fairing" for r in out)


@pytest.fixture(scope="module")
def insertion_guidance(gate_block: dict[str, Any]) -> tuple[float, float, float]:
    """(delta, a, b) of the gate pad at gamma* = 20 deg: the kick angle and the
    linear-tangent pair that insert it (the recipe of tests/test_engine_planar.py, its
    ``guidance_inputs`` fixture; search mode, dense output off)."""
    vehicle = VehicleConfig.model_validate(gate_block).to_vehicle()
    planner = _planner(vehicle, "insertion", dense=False)
    kick = planner.to_kick(planner.start())
    sol = solve_delta_for_gamma(
        lambda d: planner.from_kick(d, kick),
        GAMMA_STAR_RAD,
        DeltaSolveSettings.from_config(SearchConfig()),
    )
    ltg = planner.solve_stage2(sol.handover)
    return sol.delta_rad, ltg.a, ltg.b_per_s


def test_fairing_dropped_in_the_stage2_burn_on_planner_rows(
    tmp_path: Path, gate_block: dict[str, Any], insertion_guidance: tuple[float, float, float]
) -> None:
    """Real rows of the heating event inside the stage-2 burn (the gate's own rule,
    flown to insertion): the fairing row holds the mass before the drop. Its 'after' is
    1,700 kg less and equals the first series row after the drop; the staging map dropped
    stage 1 alone."""
    delta, a, b = insertion_guidance
    run = _real_run(
        tmp_path, "run", gate_block, lambda v: _planner(v, "insertion").run(delta, ltg=(a, b))
    )
    assert run.trace.status == "inserted" and run.metric == metrics_planar.FAIRING_IN_BURN
    assert tuple(run.raw.columns) == PLANAR_SERIES  # what the model writes is what is listed
    events_header = (tmp_path / "run" / run_data.EVENTS_FILE).read_text(encoding="utf-8")
    assert tuple(events_header.splitlines()[0].split(",")) == PLANAR_EVENTS
    assert run_data.fairing_case(run.rows, None, run.masses) == metrics_planar.FAIRING_IN_BURN
    out = run_data.with_drop_masses(run.rows, run.masses, run.metric)
    assert run_data.with_drop_masses(run.rows, run.masses, None) == out
    assert len(out) == len(run.rows) and all(r.recorded for r in out)
    _check_real_staging(run, out, 0.0)
    (fairing,) = [r for r in out if r.name == "fairing"]
    ignition = next(r for r in out if r.name == "ignition" and r.phase == LTG_BURN)
    assert fairing.phase == LTG_BURN and fairing.t_s > ignition.t_s
    fairing_kg = run.vehicle.fairing_mass_kg
    assert fairing.m_before_kg == fairing.m_kg and fairing.dropped == "fairing"
    assert fairing.m_after_kg == pytest.approx(fairing.m_kg - fairing_kg, abs=1e-9)
    # the two series rows at the event: before the map, then after it
    assert run.series_mass_kg(fairing.t_s, first=True) == pytest.approx(
        fairing.m_before_kg, abs=MASS_TOL_KG
    )
    assert run.series_mass_kg(fairing.t_s) == pytest.approx(fairing.m_after_kg, abs=MASS_TOL_KG)
    assert not math.isnan(fairing.speed_inertial_mps) and not math.isnan(fairing.gamma_rel_rad)


def test_fairing_dropped_at_stage2_ignition_on_planner_rows(
    tmp_path: Path, gate_block: dict[str, Any], insertion_guidance: tuple[float, float, float]
) -> None:
    """Real rows of a criterion first met during the staging coast (a heating limit at
    the geometric mean of the rates at MECO and at stage-2 ignition, the recipe of
    tests/test_engine_planar.py): the fairing row is logged at stage-2 ignition, in
    LTG_BURN, with the ignition row's time and mass, and holds the mass before the
    drop: the burnout mass less stage 1's dry mass (the coast burns nothing)."""
    delta, a, b = insertion_guidance
    gate = VehicleConfig.model_validate(gate_block).to_vehicle()
    probe = _planner(gate, "insertion", dense=False)
    handover = probe.stage1(delta, probe.start())
    assert handover.y_ign2 is not None
    rate_meco = fmh_rate_W_m2(handover.prefix.burnouts["stage1"][1], ENV)
    rate_ign = fmh_rate_W_m2(handover.y_ign2, ENV)
    assert rate_ign < rate_meco
    block = _block_with_rule(gate_block, math.sqrt(rate_meco * rate_ign))
    run = _real_run(
        tmp_path, "run", block, lambda v: _planner(v, "insertion").run(delta, ltg=(a, b))
    )
    assert run.metric == metrics_planar.FAIRING_AT_IGNITION
    assert run_data.fairing_case(run.rows, None, run.masses) == metrics_planar.FAIRING_AT_IGNITION
    out = run_data.with_drop_masses(run.rows, run.masses, run.metric)
    assert run_data.with_drop_masses(run.rows, run.masses, None) == out
    assert len(out) == len(run.rows) and all(r.recorded for r in out)
    _check_real_staging(run, out, 0.0)
    (fairing,) = [r for r in out if r.name == "fairing"]
    ignition = next(r for r in out if r.name == "ignition" and r.phase == LTG_BURN)
    assert out.index(fairing) == out.index(ignition) + 1
    assert (fairing.t_s, fairing.phase, fairing.m_kg) == (ignition.t_s, LTG_BURN, ignition.m_kg)
    m_dry, fairing_kg = run.vehicle.stages[0].dry_mass_kg, run.vehicle.fairing_mass_kg
    assert fairing.m_before_kg == pytest.approx(run.m_meco_kg - m_dry, abs=MASS_TOL_KG)
    assert fairing.m_after_kg == pytest.approx(run.m_meco_kg - m_dry - fairing_kg, abs=MASS_TOL_KG)
    # the first row of the burn (the later row at the ignition time) is already lighter
    assert run.series_mass_kg(fairing.t_s) == pytest.approx(fairing.m_after_kg, abs=MASS_TOL_KG)
    assert run.series_mass_kg(fairing.t_s, first=True) == pytest.approx(
        fairing.m_before_kg, abs=MASS_TOL_KG
    )


# ---------------------------------------------------------------- the output-path rule


def test_results_tree_is_the_runs_own_tree_case_sensitive(tmp_path: Path) -> None:
    """The nearest ancestor named exactly 'results'; else the parent of the experiment
    directory (a tree written with --results-root); a run directory too close to the
    filesystem root is its own tree."""
    run_dir = tmp_path / "results" / "exp" / "ts"
    assert run_data.results_tree(run_dir) == (tmp_path / "results").resolve()
    nested = tmp_path / "results" / "a" / "results" / "exp" / "ts"
    assert run_data.results_tree(nested) == (tmp_path / "results" / "a" / "results").resolve()
    capital = tmp_path / "Results" / "group" / "exp" / "ts"
    assert run_data.results_tree(capital) == (tmp_path / "Results" / "group").resolve()
    custom = tmp_path / "out" / "exp" / "ts"
    assert run_data.results_tree(custom) == (tmp_path / "out").resolve()
    anchor = Path(tmp_path.anchor)
    assert run_data.results_tree(anchor / "zz_exp" / "zz_ts") == (anchor / "zz_exp" / "zz_ts")
    assert run_data.results_tree(anchor / "zz_root" / "zz_exp" / "zz_ts") == anchor / "zz_root"
    assert run_data.is_inside(run_dir / "x" / "a.gif", tmp_path / "results")
    assert run_data.is_inside(tmp_path / "results", tmp_path / "results")
    assert not run_data.is_inside(tmp_path / "results2" / "a.gif", tmp_path / "results")


def test_results_ancestors_and_protected_tree(tmp_path: Path) -> None:
    """Every ancestor named results in any letter case, innermost first; the protected
    tree is the outermost of those and of the run's own tree; None outside all."""
    path = tmp_path / "Results" / "a" / "RESULTS" / "b" / "results" / "page.html"
    assert run_data.results_ancestors(path) == [
        (tmp_path / "Results" / "a" / "RESULTS" / "b" / "results").resolve(),
        (tmp_path / "Results" / "a" / "RESULTS").resolve(),
        (tmp_path / "Results").resolve(),
    ]
    assert run_data.results_ancestors(tmp_path / "resultsx" / "page.html") == []
    run_dir = tmp_path / "elsewhere" / "results" / "exp" / "ts"
    assert run_data.protected_tree(path, run_dir) == (tmp_path / "Results").resolve()
    assert run_data.protected_tree(run_dir / "a.html", run_dir) == (
        tmp_path / "elsewhere" / "results"
    )
    assert run_data.protected_tree(tmp_path / "work" / "a.html", run_dir) is None
    custom = tmp_path / "out" / "exp" / "ts"
    assert run_data.protected_tree(tmp_path / "out" / "other" / "a.html", custom) == (
        (tmp_path / "out").resolve()
    )
    assert run_data.protected_tree(tmp_path / "out2" / "a.html", custom) is None
    # a custom tree that itself lies in a results folder: the outer one is protected
    inner = tmp_path / "results" / "custom" / "exp" / "ts"
    assert run_data.protected_tree(inner / "a.html", inner) == (tmp_path / "results").resolve()


def test_default_output_path_moves_out_of_every_results_tree(tmp_path: Path) -> None:
    run_dir = tmp_path / "elsewhere" / "results" / "exp" / "ts"
    work = tmp_path / "work"
    assert run_data.default_output_path(run_dir, work, "a.html") == work / "a.html"
    for cwd in (run_dir, tmp_path / "elsewhere" / "results"):
        assert run_data.default_output_path(run_dir, cwd, "a.html") == (
            tmp_path / "elsewhere" / "a.html"
        )
    foreign = tmp_path / "repo" / "Results" / "exp"
    assert run_data.default_output_path(run_dir, foreign, "a.html") == tmp_path / "repo" / "a.html"
    nested = tmp_path / "repo" / "results" / "a" / "results" / "b"
    assert run_data.default_output_path(run_dir, nested, "a.html") == tmp_path / "repo" / "a.html"


def test_check_output_order_words_and_class(tmp_path: Path) -> None:
    """Suffix, then the results trees, then the folder, each with the caller's words."""
    run_dir = tmp_path / "results" / "exp" / "ts"
    run_dir.mkdir(parents=True)
    ok = tmp_path / "work"
    ok.mkdir()

    def check(path: Path) -> None:
        run_data.check_output(
            path,
            run_dir,
            suffixes=(".html", ".htm"),
            suffix_text=".html",
            what="page",
            error=replay.ReplayError,
        )

    check(ok / "a.html")
    check(ok / "A.HTM")  # the extension is compared in lower case
    with pytest.raises(replay.ReplayError) as err:
        check(run_dir / "missing" / "a.txt")  # all three wrong: the suffix is named
    assert str(err.value) == f"output {run_dir / 'missing' / 'a.txt'} must end in .html"
    with pytest.raises(replay.ReplayError) as err:
        check(run_dir / "missing" / "a.html")  # tree and folder wrong: the tree is named
    assert str(err.value) == (
        f"output {run_dir / 'missing' / 'a.html'} is inside the results tree; results/ is "
        "never edited by hand, so write the page elsewhere (--out)"
    )
    with pytest.raises(replay.ReplayError) as err:
        check(tmp_path / "nowhere" / "a.html")
    assert str(err.value) == f"output folder does not exist: {tmp_path / 'nowhere'}"
    with pytest.raises(run_data.RunDataError, match="write the scene elsewhere"):
        run_data.check_outside_results(run_dir / "a.html", run_dir, what="scene")


# ---------------------------------------------------------------- animate's two changes


def _no_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(plots.FFMpegWriter, "isAvailable", classmethod(lambda cls: False))


def test_animate_output_is_refused_in_any_results_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deliberate change 1 of SP2 A1 (D-SP2-14, KI-017): animate's output-path check is
    the rule replay uses. An output inside another folder named results (any letter
    case), or in the outer tree of a nested pair, is refused; at the SP2 start commit
    both were accepted, because only the run's own tree was protected. The order of
    animate's checks is unchanged: extension, tree, ffmpeg, folder."""
    run_dir = _synth_run_dir(tmp_path / "elsewhere")
    foreign = tmp_path / "repo" / "Results" / "exp"
    foreign.mkdir(parents=True)
    with pytest.raises(plots.AnimationError) as err:
        plots.check_animation_out(foreign / "a.gif", run_dir)
    assert str(err.value) == (
        f"output {foreign / 'a.gif'} is inside the results tree; results/ is never edited "
        "by hand, so write the animation elsewhere (--out)"
    )
    with pytest.raises(plots.AnimationError, match="results tree"):
        plots.write_ascent_animation(run_dir, None, foreign / "a.gif", fps=2, seconds=1, width=320)
    assert not (foreign / "a.gif").exists()
    inner = tmp_path / "nest" / "results" / "a" / "results" / "exp" / "ts"
    inner.mkdir(parents=True)
    outer_sibling = tmp_path / "nest" / "results" / "zzz"
    outer_sibling.mkdir()
    with pytest.raises(plots.AnimationError, match="results tree"):
        plots.check_animation_out(outer_sibling / "a.gif", inner)
    capital = tmp_path / "cap" / "Results" / "group" / "exp" / "ts"
    capital.mkdir(parents=True)
    with pytest.raises(plots.AnimationError, match="results tree"):
        plots.check_animation_out(tmp_path / "cap" / "Results" / "a.gif", capital)
    # still accepted: a folder outside every results tree
    work = tmp_path / "work"
    work.mkdir()
    plots.check_animation_out(work / "a.gif", run_dir)
    # the order: extension, tree, ffmpeg, folder
    _no_ffmpeg(monkeypatch)
    with pytest.raises(plots.AnimationError, match=r"must end in \.mp4 or \.gif \(the extension"):
        plots.check_animation_out(foreign / "missing" / "a.avi", run_dir)
    with pytest.raises(plots.AnimationError, match="results tree"):
        plots.check_animation_out(foreign / "missing" / "a.mp4", run_dir)
    with pytest.raises(plots.AnimationError, match="needs ffmpeg"):
        plots.check_animation_out(tmp_path / "nowhere" / "a.mp4", run_dir)
    with pytest.raises(plots.AnimationError, match="output folder does not exist"):
        plots.check_animation_out(tmp_path / "nowhere" / "a.gif", run_dir)


def test_animate_default_output_moves_out_of_any_results_tree(tmp_path: Path) -> None:
    """The default path of the same change: from a working directory inside another
    results folder, or inside nested trees, the animation goes next to the outermost
    tree (at the SP2 start commit it went into the working directory, that is, into
    the other results folder, or next to the inner tree and so inside the outer one)."""
    run_dir = _synth_run_dir(tmp_path / "elsewhere")
    name = f"{SYNTH_EXPERIMENT}_{SYNTH_TIMESTAMP}_animation.gif"
    work = tmp_path / "work"
    assert plots.default_animation_path(run_dir, work, ffmpeg=False) == work / name
    foreign = tmp_path / "repo" / "Results" / "exp"
    assert plots.default_animation_path(run_dir, foreign, ffmpeg=False) == tmp_path / "repo" / name
    nested_cwd = tmp_path / "repo" / "results" / "a" / "results" / "b"
    assert plots.default_animation_path(run_dir, nested_cwd, ffmpeg=False) == (
        tmp_path / "repo" / name
    )
    inner = tmp_path / "nest" / "results" / "a" / "results" / SYNTH_EXPERIMENT / SYNTH_TIMESTAMP
    inner_tree = tmp_path / "nest" / "results" / "a" / "results"
    assert plots.default_animation_path(inner, inner_tree, ffmpeg=True) == (
        tmp_path / "nest" / f"{SYNTH_EXPERIMENT}_{SYNTH_TIMESTAMP}_animation.mp4"
    )
    # replay's default follows the same rule (one rule for both commands)
    assert replay.default_replay_path(run_dir, foreign).parent == tmp_path / "repo"


def test_animate_calls_a_sweep_point_not_an_experiment_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Deliberate change 2 of SP2 A1 (D-SP2-14): a sweep point, or any directory whose
    metrics.json has no ``runs`` mapping, is reported as 'not an experiment results
    directory', in replay's words; at the SP2 start commit animate called it 'a
    vertical_1d run'. A directory with runs and no model is still a vertical_1d run."""
    point = _sweep_point(tmp_path)
    with pytest.raises(plots.AnimationError) as err:
        plots.load_animation_runs(point, None)
    assert str(err.value) == (
        f"{point} is not an experiment results directory (its metrics.json lists no runs: a "
        "sweep point or a single run's folder); pass results/<experiment>/<timestamp>"
    )
    assert "vertical_1d" not in str(err.value)
    with pytest.raises(replay.ReplayError) as same:
        replay.check_replay_run_dir(point)
    assert str(same.value) == str(err.value)
    code = main(["animate", str(point), "--out", str(tmp_path / "a.gif")])
    printed = capsys.readouterr().out
    assert code == 1 and "error:" in printed and "Traceback" not in printed
    assert "not an experiment results directory" in printed
    assert not (tmp_path / "a.gif").exists()
    run_dir = _synth_run_dir(tmp_path / "one_d")
    record = {k: v for k, v in _synth_metrics().items() if k != "model"}
    (run_dir / "metrics.json").write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(plots.AnimationError, match="is a vertical_1d run; animate draws planar_2d"):
        plots.load_animation_runs(run_dir, None)


def test_animate_and_replay_keep_their_words_through_the_shared_checks(synth_dir: Path) -> None:
    """The wrappers pass their own class and words: 'one animation' against 'one
    replay', 'animate draws' against 'replay shows', and the directory is checked before
    the selection."""
    five = list(SYNTH_RUNS)[:5]
    with pytest.raises(plots.AnimationError) as animate:
        plots.load_animation_runs(synth_dir, five)
    assert str(animate.value) == "5 runs requested; at most 4 fit one animation"
    with pytest.raises(replay.ReplayError) as shown:
        replay.select_runs(synth_dir, five)
    assert str(shown.value) == "5 runs requested; at most 4 fit one replay"
    missing = synth_dir / "missing"
    with pytest.raises(plots.AnimationError, match="run directory not found"):
        plots.load_animation_runs(missing, ["nope"])
    with pytest.raises(replay.ReplayError, match="run directory not found"):
        replay.replay_data(missing, ["nope"])
    with pytest.raises(replay.ReplayError, match=r"replay shows the runs metrics\.json records"):
        replay.run_source({}, {}, "stray")


# ---------------------------------------------------------------- model-keyed columns


def test_model_columns_are_keyed_by_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """planar_2d holds the two tuples metrics_planar writes; every column a consumer
    asks for is one the model writes; an unknown model is refused with the known ones
    named; a second model whose files hold a superset of the planar names reads through
    the same readers, with the planar field list, to the planar values."""
    planar = run_data.model_columns(PLANAR_2D)
    assert planar is run_data.MODEL_COLUMNS[PLANAR_2D]
    assert planar.series is metrics_planar.PLANAR_TIMESERIES_COLUMNS
    assert planar.events is metrics_planar.PLANAR_EVENT_COLUMNS
    assert planar.base is run_data.PLANAR_BASE_COLUMNS
    assert planar.label == run_data.PLANAR_LABEL == "planar"
    assert set(planar.base) <= set(planar.series)
    assert set(replay.REPLAY_COLUMNS) <= set(planar.series)
    assert {column for _, column, _, _ in replay.SERIES_FIELDS} <= set(planar.series)
    assert set(run_data.EVENT_REQUIRED_COLUMNS) <= set(planar.events)
    with pytest.raises(run_data.RunDataError) as err:
        run_data.model_columns("spatial_3d")
    assert str(err.value) == "no column set for model 'spatial_3d'; known: planar_2d"
    spatial = run_data.ModelColumns(
        series=(*planar.series, "crossrange_m", "heading_rad"),
        events=(*planar.events, "crossrange_m"),
        base=planar.base,
        label="spatial",
    )
    monkeypatch.setitem(run_data.MODEL_COLUMNS, "spatial_3d", spatial)
    assert run_data.model_columns("spatial_3d") is spatial
    assert ", ".join(run_data.MODEL_COLUMNS) == "planar_2d, spatial_3d"
    # one run written twice: with the planar columns, and with two more per row
    rows = _synth_series_rows(True)
    wide_columns = (*SYNTH_SERIES_COLUMNS, "crossrange_m", "heading_rad")
    wide_rows = [
        {**row, "crossrange_m": 3.0 * k, "heading_rad": 0.01 * k} for k, row in enumerate(rows)
    ]
    for name, columns, data in (
        ("flat", SYNTH_SERIES_COLUMNS, rows),
        ("wide", wide_columns, wide_rows),
    ):
        folder = tmp_path / name
        folder.mkdir()
        (folder / "timeseries.csv").write_text(_synth_csv(columns, data), encoding="utf-8")
    flat = run_data.run_series(
        run_data.read_series(tmp_path, "flat", replay.REPLAY_COLUMNS), REPLAY_FIELDS
    )
    wide_frame = run_data.read_series(tmp_path, "wide", replay.REPLAY_COLUMNS)
    assert run_data.run_series(wide_frame, REPLAY_FIELDS) == flat
    more = run_data.run_series(wide_frame, [*REPLAY_FIELDS, ("y_m", "crossrange_m", None, 1)])
    assert more["y_m"][0] == 0.0 and more["y_m"][-1] == 3.0 * (len(rows) - 1)
    assert {k: v for k, v in more.items() if k != "y_m"} == flat
