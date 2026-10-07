"""scene.py, the data payload of the 2-D launch scene (SP2 step A2; design section 4.4).

Fast tier. The real data is one fixed-guidance experiment of experiments/silo_screening_2d
.yaml at a 0.5 s sample step, rtol 1e-8 and a 32-point max-Q scan (FIXTURE_RTOL,
FIXTURE_MAXQ_SCAN_POINTS: these tests check the payload builder, not the integration or
max-Q): ten flights, the pad, silo_cold, silo_failed (no guidance, a few rows), a
readme-loads case with its own vehicle file, four cases with a lighter load (one of them
with a +8.1 t stage-1 dry mass, one flying a lighter payload, one with a lighter stage-2
load) and an aero bound with its paired pad, run once per module into a temporary results
root. Measured on 2026-10-05: 4.4 s of setup shared by the module, which ``pytest
--durations`` charges to its first test (6.7 s with eleven flights at rtol 1e-10 and the
256-point scan before); every test's own call stays under 3 s. Derived directories are
copies of it with metrics.json and resolved_config.yaml rewritten (an offload block whose
runs are copies of the light case folders with records built as SP1 writes them, payload
metrics set, a wrong payload, an exploratory label, an empty time series, an unknown git
state) and synthetic folders for the refusals. results/ is never read.

Checked: strict JSON (no NaN, ASCII, '<' escaped); nulls in the shaft for q and Mach and
outside the push for the track series; a run with a null payload takes the block's
payload; bound runs and cases take their payload through run_source; a zero-offload pad
control with no vehicle block closes its mass; an offload case starts at one minus its
fraction against the full load and a case against its own block; the offload notes are
replay.replay_offload_note's (paired pad, penalty, fixed, stage-2 solve, pad control); the
offload caveats word for word; the exploratory line; the refusals (1-D, sweep directory,
sweep point, FAILED.txt, no summary.md); a run with an empty time series left out with
its reason; events labelled by name and stage with the pad's synthetic liftoff and ramp
end, and a ramp end synthesised for a hot start held before the push; each spent stage's
own measured gap from the recorded staging coast (the fairing halves none) and the
display-only text quoting named runs, never a bound on every run; R_E from constants and
omega_p from the site, a block without a full site refused; the display geometry per
vehicle and the generic fallback (for an unlisted vehicle too); the caveat list a
superset of replay.caveats for the same selection; every load-time check passing on every
real run, the row selection's convergence among them (a selection that did not converge
is a failing item); an unknown git state carried as unknown; D-SP2-28's default pair
when no run is named; each run's peak q row kept and its max-Q taken from its metrics
record (none when the record has none); the captured frames' caveat line and each pushed
run's structure note; schema
defaults labelled 'default'; the import guard that keeps
display and scene out of the run path, scene reading through run_data only and display
loading no I/O module.
"""

from __future__ import annotations

import ast
import copy
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

from launchsim import display, replay, results_io, run_data, scene, sim
from launchsim.config import resolve_experiment
from launchsim.constants import OMEGA_EARTH_RADS, R_EARTH_M

SRC = Path(__file__).resolve().parents[1] / "src" / "launchsim"
DISPLAY_DIR = Path(__file__).resolve().parents[1] / "configs" / "display"
FIXED_GAMMA_DEG = 20.0
FIXED_LTG = (0.756790, 2.19338e-3)
"""The pad's LTG pair at gamma* 20 deg (tests/test_planar_pipeline.py)."""
FAST_SAMPLE_DT_S = 0.5
FIXTURE_RTOL = 1.0e-8
"""Integrator rtol of the fixture's flights (search_rtol, final_rtol and the run's
integrator.rtol, which config.py ties together): the search block's default search_rtol,
loose enough to keep the module's setup near 4.5 s; nothing here tests integration."""
FIXTURE_DELTA_XTOL_RAD = 1.0e-8
"""Tolerance [rad] of the fixture's kick-angle solve for the fixed gamma*."""
FIXTURE_MAXQ_SCAN_POINTS = 32
"""Points per phase of the fixture's max-Q scan (checks.maxq_scan_points; 256 in the
experiment file): the scene reads no max-Q metric, and the scan is a tenth of the setup."""
FULL_S1_LOAD_T, FULL_S2_LOAD_T = 410.9, 107.5
"""The gate fork's stage-1 and stage-2 propellant loads [t] (generic_f9_class_2d.yaml)."""
STAGE1_DRY_T = 22.2
"""The gate fork's stage-1 dry mass [t]."""
LIGHT_LOAD_T = 0.9 * FULL_S1_LOAD_T
"""Stage-1 load of the ``light`` case [t]: a tenth of the gate fork's load not loaded."""
LIGHT_S2_LOAD_T = 0.9 * FULL_S2_LOAD_T
"""Stage-2 load of the ``light_stage2`` case [t]: a tenth of the stage-2 load not loaded."""
PENALTY_T = 8.1
"""Stage-1 dry mass the ``light_penalty`` case adds [t] (RQ1's +8.1 t row)."""
BLOCK_PAYLOAD_KG = 22_800.0
"""The gate fork's payload_mass_t in kg, which every fixed-guidance run flies unless its
case overrides the payload; the derived offload block's P_ref."""
PAIRED_PAYLOAD_KG = 21_398.0
"""Payload the ``lighter_payload`` case flies [kg]: the derived paired pad's own capacity,
1,402 kg short of P_ref (the real silo_cold_s1__pad's gap), and the derived fixed case's
capacity (short of P_ref: a payload loss at that imposed offload)."""
WRONG_PAYLOAD_KG = 23_800.0
"""A payload metric 1,000 kg off the flown one: the checks must flag it."""
S1_LOAD_PATH = "vehicle.stages.stage1.propellant_mass_t"
S2_LOAD_PATH = "vehicle.stages.stage2.propellant_mass_t"
S1_DRY_PATH = "vehicle.stages.stage1.dry_mass_t"
PAYLOAD_PATH = "vehicle.payload_mass_t"
"""Override paths of the fixture's cases."""
OFFLOAD_CAVEATS = (
    "first offload caveat, word for word",
    "second caveat with <angle> brackets & an ampersand",
)
"""The derived directory's offload.caveats (one with '<', to see it escaped)."""
RUN_PATH_MODULES = (
    "sim",
    "results_io",
    "search",
    "guidance",
    "dynamics",
    "offload",
    "compare",
    "metrics",
    "metrics_planar",
    "run_data",
    "phases/__init__",
    "phases/engine",
    "phases/trace",
    "phases/prelude",
    "phases/vertical",
    "phases/planar",
)
"""Modules of the run path that must never import display or scene."""
SCENE_MODULES = ("launchsim.display", "launchsim.scene")


# ------------------------------------------------------------------ fixtures


def _fixed_experiment(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """silo_screening_2d with fixed guidance (gamma* 20 deg, the pad's LTG pair), a
    0.5 s sample step, rtol FIXTURE_RTOL, a coarser max-Q scan (FIXTURE_MAXQ_SCAN_POINTS),
    the variants silo_cold and silo_failed, a
    readme-loads case with its own vehicle file, a ``light`` case with a tenth of the
    stage-1 load not loaded, three more cases the derived offload block copies
    (``lighter_payload`` at the light load flying PAIRED_PAYLOAD_KG, ``light_penalty``
    with +8.1 t of stage-1 dry mass, ``light_stage2`` with a tenth of the stage-2 load not
    loaded), and the aero bound of silo_cold with its paired pad. Every flight's mass is
    consistent with its own vehicle block, so the derived offload runs close their
    checks."""
    exp = yaml.safe_load(
        (repo_root / "experiments" / "silo_screening_2d.yaml").read_text(encoding="utf-8")
    )
    veh = yaml.safe_load(
        (repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml").read_text(
            encoding="utf-8"
        )
    )
    exp["search"].update(
        {
            "figure_of_merit": "none",
            "fixed_gamma_star_deg": FIXED_GAMMA_DEG,
            "fixed_ltg_a": FIXED_LTG[0],
            "fixed_ltg_b_per_s": FIXED_LTG[1],
            "search_rtol": FIXTURE_RTOL,
            "final_rtol": FIXTURE_RTOL,
            "delta_xtol_rad": FIXTURE_DELTA_XTOL_RAD,
        }
    )
    exp["baseline"]["integrator"]["sample_dt_s"] = FAST_SAMPLE_DT_S
    exp["baseline"]["integrator"]["rtol"] = FIXTURE_RTOL
    exp["checks"]["maxq_scan_points"] = FIXTURE_MAXQ_SCAN_POINTS
    exp["variants"] = {
        k: v for k, v in exp["variants"].items() if k in ("silo_cold", "silo_failed")
    }
    for key in ("sweeps", "sensitivity"):
        exp.pop(key, None)
    exp["label"] = "calibration"  # cases need the calibration label (config.py)
    exp["cases"] = {
        "readme_loads": {"vehicle": "configs/vehicles/generic_f9_class_2d_readme_loads.yaml"},
        "light": {"overrides": {S1_LOAD_PATH: LIGHT_LOAD_T}},
        "lighter_payload": {
            "overrides": {S1_LOAD_PATH: LIGHT_LOAD_T, PAYLOAD_PATH: PAIRED_PAYLOAD_KG / 1000.0}
        },
        "light_penalty": {
            "overrides": {S1_LOAD_PATH: LIGHT_LOAD_T, S1_DRY_PATH: STAGE1_DRY_T + PENALTY_T}
        },
        "light_stage2": {"overrides": {S2_LOAD_PATH: LIGHT_S2_LOAD_T}},
    }
    exp["bounds"] = [
        {
            "name": "aero_bound",
            "of": ["silo_cold"],
            "overrides": {"vehicle.aero.reference_area_m2": 21.24},
            "paired_baseline": True,
        }
    ]
    return exp, veh


@pytest.fixture(scope="module")
def real_dir(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The fixed-guidance experiment run once through sim.run_experiment into a temporary
    results root; the results directory."""
    exp, veh = _fixed_experiment(repo_root)

    def load_vehicle(path: str) -> dict[str, Any]:
        return yaml.safe_load((repo_root / path).read_text(encoding="utf-8"))

    resolved = resolve_experiment(exp, veh, load_vehicle)
    root = tmp_path_factory.mktemp("scene_real")
    _, out = sim.run_experiment(resolved, root, plots=False, repo_root=repo_root)
    return out


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data), encoding="utf-8", newline="\n")


OFFLOAD_COPIES = {
    "light_s1": "light",
    "light_s1__pad": "lighter_payload",
    "light_s1_dry+8.1t": "light_penalty",
    "light_fix10pct": "lighter_payload",
    "light_s2": "light_stage2",
}
"""The derived offload runs and the fixture case folder each one is a copy of (the
record's numbers are the case's own, so every copy closes its checks)."""
PAD_CONTROL_S2_KG = 500.0
"""What the derived stage-2 pad control found [kg]: the amount the stage-2 solve is quoted
net of (its record names a run folder the fixture does not fly)."""
VERIFY_DELTA_KG = 15.36
"""P* - P_ref of the derived stage-2 solve's failed verification [kg] (silo_cold_s2's)."""
VERIFY_TOL_KG = 2.28
"""Tolerance of that verification [kg] (1e-4 of P_ref, as SP1 sets it)."""


def _case_record(name: str, **fields: Any) -> dict[str, Any]:
    """An offload case record of the derived block: the solved stage-1 case's keys as the
    SP1 writer lays them out, with ``fields`` replacing or adding to them."""
    removed = (FULL_S1_LOAD_T - LIGHT_LOAD_T) * 1000.0
    total_t = FULL_S1_LOAD_T + FULL_S2_LOAD_T
    record = {
        "name": name,
        "of": "silo_cold",
        "kind": "solve",
        "mode": "stage1",
        "fixed_key": None,
        "fixed_fraction": None,
        "run": name,
        "status": "ok",
        "run_status": "inserted",
        "reference_payload_kg": BLOCK_PAYLOAD_KG,
        "quoted_offload_kg": removed,
        "quoted_basis": "x* at P_ref, gross: stage 1, the headline",
        "offload_kg": removed,
        "stage2_preoffload_kg": 0.0,
        "stage1_dry_mass_added_kg": 0.0,
        "assumed_penalty": False,
        "stage1_offload_kg": removed,
        "stage2_offload_kg": 0.0,
        "total_offload_kg": removed,
        "stage1_fraction": 1.0 - LIGHT_LOAD_T / FULL_S1_LOAD_T,
        "stage2_fraction": 0.0,
        "total_fraction": (FULL_S1_LOAD_T - LIGHT_LOAD_T) / total_t,
        "payload_kg": BLOCK_PAYLOAD_KG,
        "payload_delta_kg": 0.0,
        "verification": {
            "status": "ok",
            "payload_kg": BLOCK_PAYLOAD_KG,
            "delta_kg": 0.0,
            "tolerance_kg": VERIFY_TOL_KG,
            "passed": True,
            "run": name,
        },
        "pad_control_offload_kg": None,
        "net_offload_kg": None,
        "flags": [],
    }
    record.update(fields)
    return record


def _offload_block(metrics: dict[str, Any]) -> dict[str, Any]:
    """The derived directory's ``offload`` block: P_ref = BLOCK_PAYLOAD_KG; a solved stage-1
    case with a paired pad flying PAIRED_PAYLOAD_KG (short of P_ref); a penalty row (+8.1 t
    assumed); a fixed case flying PAIRED_PAYLOAD_KG too (short of P_ref: a payload loss at
    its imposed offload); a stage-2 solve quoted net of the stage-2 pad control, its
    verification failed by VERIFY_DELTA_KG and one flag; the stage-1 pad control (no
    offload found) and the stage-2 one; the runs' metrics records (the copied case's, with
    the flown payload set) and the caveats."""
    removed_s2 = (FULL_S2_LOAD_T - LIGHT_S2_LOAD_T) * 1000.0
    total_t = FULL_S1_LOAD_T + FULL_S2_LOAD_T

    def flown(case: str, payload_kg: float) -> dict[str, Any]:
        record = copy.deepcopy(metrics["cases"][case])
        record["payload_kg"] = payload_kg
        return record

    pad = copy.deepcopy(metrics["runs"]["pad"])
    pad["payload_kg"] = BLOCK_PAYLOAD_KG
    return {
        "basis": "test basis",
        "reference": "pad",
        "reference_payload_kg": BLOCK_PAYLOAD_KG,
        "caveats": list(OFFLOAD_CAVEATS),
        "pad_control": True,
        "pad_controls": [
            {
                "mode": "stage1",
                "run": "pad__offload_stage1",
                "status": "no_offload",
                "offload_kg": 0.0,
                "consistency": "pass",
                "resolution_effect": False,
                "flags": [],
            },
            {
                "mode": "stage2",
                "run": "pad__offload_stage2",
                "status": "ok",
                "offload_kg": PAD_CONTROL_S2_KG,
                "flags": [],
            },
        ],
        "cases": [
            _case_record(
                "light_s1",
                paired_pad={
                    "run": "light_s1__pad",
                    "status": "inserted",
                    "payload_kg": PAIRED_PAYLOAD_KG,
                    "payload_delta_vs_reference_kg": PAIRED_PAYLOAD_KG - BLOCK_PAYLOAD_KG,
                },
            ),
            _case_record(
                "light_s1_dry+8.1t",
                stage1_dry_mass_added_kg=PENALTY_T * 1000.0,
                assumed_penalty=True,
            ),
            _case_record(
                "light_fix10pct",
                kind="fixed",
                fixed_key="stage1_fraction",
                fixed_fraction=1.0 - LIGHT_LOAD_T / FULL_S1_LOAD_T,
                quoted_basis="imposed: a fixed case, whose figure is its payload capacity "
                "against P_ref",
                payload_kg=PAIRED_PAYLOAD_KG,
                payload_delta_kg=PAIRED_PAYLOAD_KG - BLOCK_PAYLOAD_KG,
                verification=None,
            ),
            _case_record(
                "light_s2",
                mode="stage2",
                quoted_offload_kg=removed_s2 - PAD_CONTROL_S2_KG,
                quoted_basis="x* net of the pad control's x_pad: a property of the vehicle "
                "model, not of the assist",
                offload_kg=removed_s2,
                stage1_offload_kg=0.0,
                stage2_offload_kg=removed_s2,
                total_offload_kg=removed_s2,
                stage1_fraction=0.0,
                stage2_fraction=1.0 - LIGHT_S2_LOAD_T / FULL_S2_LOAD_T,
                total_fraction=(FULL_S2_LOAD_T - LIGHT_S2_LOAD_T) / total_t,
                verification={
                    "status": "ok",
                    "payload_kg": BLOCK_PAYLOAD_KG + VERIFY_DELTA_KG,
                    "delta_kg": VERIFY_DELTA_KG,
                    "tolerance_kg": VERIFY_TOL_KG,
                    "passed": False,
                    "run": "light_s2",
                },
                pad_control_offload_kg=PAD_CONTROL_S2_KG,
                net_offload_kg=removed_s2 - PAD_CONTROL_S2_KG,
                flags=["offload: offload_verify_mismatch: the payload search ended ok above P_ref"],
            ),
        ],
        "runs": {
            "light_s1": flown("light", BLOCK_PAYLOAD_KG),
            "light_s1__pad": flown("lighter_payload", PAIRED_PAYLOAD_KG),
            "light_s1_dry+8.1t": flown("light_penalty", BLOCK_PAYLOAD_KG),
            "light_fix10pct": flown("lighter_payload", PAIRED_PAYLOAD_KG),
            "light_s2": flown("light_stage2", BLOCK_PAYLOAD_KG),
            "pad__offload_stage1": pad,
        },
    }


def _derive(real: Path, dst: Path, *, label: str | None = None) -> Path:
    """A copy of ``real`` under ``dst`` with: an offload block (``_offload_block``) whose
    runs are copies of the fixture's light case folders (OFFLOAD_COPIES) and whose stage-1
    pad control is a copy of the pad (no vehicle block); payload metrics equal to the flown
    payload on the bound, its paired pad, the readme-loads case and the offload runs; a
    ``wrong_payload`` case (a copy of the pad whose metric is 1,000 kg off);
    ``offload.caveats``; and the given ``label``."""
    shutil.copytree(real, dst)
    metrics = run_data.read_json(dst / run_data.METRICS_FILE)
    config = run_data.read_yaml(dst / run_data.CONFIG_FILE)
    for name, case in OFFLOAD_COPIES.items():
        shutil.copytree(real / case, dst / name)
    shutil.copytree(real / "pad", dst / "pad__offload_stage1")
    shutil.copytree(real / "pad", dst / "wrong_payload")
    metrics["bounds"][0]["metrics"]["payload_kg"] = BLOCK_PAYLOAD_KG
    metrics["bounds"][0]["paired_baseline_metrics"]["payload_kg"] = BLOCK_PAYLOAD_KG
    metrics["cases"]["readme_loads"]["payload_kg"] = BLOCK_PAYLOAD_KG
    wrong = copy.deepcopy(metrics["runs"]["pad"])
    wrong["payload_kg"] = WRONG_PAYLOAD_KG
    metrics["cases"]["wrong_payload"] = wrong
    metrics["offload"] = _offload_block(metrics)
    if label is not None:
        metrics["label"] = label
    config["offload_runs"] = {
        name: copy.deepcopy(config["cases"][case]) for name, case in OFFLOAD_COPIES.items()
    }
    config["offload_runs"]["pad__offload_stage1"] = {
        "run": copy.deepcopy(config["runs"]["pad"]["run"])
    }
    config["cases"]["wrong_payload"] = {"run": copy.deepcopy(config["runs"]["pad"]["run"])}
    _write_json(dst / run_data.METRICS_FILE, metrics)
    (dst / run_data.CONFIG_FILE).write_text(json.dumps(config), encoding="utf-8", newline="\n")
    return dst


@pytest.fixture(scope="module")
def derived_dir(real_dir: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The derived directory (``_derive``) with no label."""
    return _derive(real_dir, tmp_path_factory.mktemp("scene_derived") / "run")


@pytest.fixture(scope="module")
def exploratory_dir(real_dir: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The derived directory labelled exploratory."""
    root = tmp_path_factory.mktemp("scene_exploratory")
    return _derive(real_dir, root / "run", label=replay.EXPLORATORY_LABEL)


@pytest.fixture(scope="module")
def real_payload(real_dir: Path) -> dict[str, Any]:
    """The payload of the real directory's default selection plus its cases and bounds."""
    runs = ["pad", "silo_cold", "silo_failed", "readme_loads"]
    return scene.scene_payload(real_dir, runs, display_dir=DISPLAY_DIR)


def _run(payload: dict[str, Any], key: str) -> dict[str, Any]:
    return next(r for r in payload["runs"] if r["key"] == key)


# ------------------------------------------------------------------ JSON and nulls


def test_payload_is_strict_ascii_json_with_lt_escaped(derived_dir: Path) -> None:
    """scene_json writes no NaN or Infinity, ASCII only and no '<' (escaped as \\u003c), and
    reads back equal; the caveat holding '<' survives the round trip."""
    payload = scene.scene_payload(
        derived_dir, ["pad", "light_s1", "silo_failed"], display_dir=DISPLAY_DIR
    )
    text = scene.scene_json(payload)
    assert text.isascii() and "<" not in text and "NaN" not in text and "Infinity" not in text
    assert "\\u003c" in text and "," + ":" not in text and ", " not in text[:200]
    back = json.loads(text)
    assert back == json.loads(json.dumps(payload))
    assert OFFLOAD_CAVEATS[1] in back["caveats"]
    with pytest.raises(ValueError):
        scene.scene_json({"x": math.nan})


def test_nulls_in_the_shaft_and_outside_the_push(real_payload: dict[str, Any]) -> None:
    """silo_cold: q and Mach are null exactly on the ASSIST samples and the six track series
    are defined exactly there (s_m from 0 to the stroke); the pad's track series are null
    throughout and its q and Mach defined."""
    silo = _run(real_payload, "silo_cold")
    in_push = [p == "ASSIST" for p in silo["phase"]]
    assert any(in_push) and not all(in_push)
    for key in ("q_pa", "mach"):
        assert [v is None for v in silo[key]] == in_push, key
    for column, values in silo["track"].items():
        assert [v is not None for v in values] == in_push, column
    s_m = [v for v in silo["track"]["s_m"] if v is not None]
    assert s_m[0] == 0.0 and s_m[-1] == pytest.approx(silo["assist"]["stroke_m"], abs=1e-6)
    pad = _run(real_payload, "pad")
    assert all(v is None for values in pad["track"].values() for v in values)
    assert all(v is not None for v in pad["q_pa"]) and pad["assist"] is None
    assert len(pad["t"]) == len(pad["q_pa"]) == len(pad["prop1_kg"]) == pad["selection"]["samples"]


# ------------------------------------------------------------------ payload sources and fills


def test_null_payload_takes_the_block_and_sources_take_run_source(
    real_payload: dict[str, Any], derived_dir: Path
) -> None:
    """A fixed-guidance run has no payload_kg metric: the block's payload is used and said
    so. In the derived directory the bound, its paired pad, the readme-loads case and the
    offload runs carry the metric, found through run_source for each role; the liftoff
    identity closes for each; a wrong metric is flagged but the run still loads."""
    pad = _run(real_payload, "pad")
    assert pad["payload_kg"] == BLOCK_PAYLOAD_KG and "vehicle block" in pad["payload_source"]
    assert pad["checks"]["passed"]
    runs = ["silo_cold__aero_bound", "pad__aero_bound", "readme_loads", "light_s1", "wrong_payload"]
    payload = scene.scene_payload(derived_dir, runs[:4], display_dir=DISPLAY_DIR)
    roles = {r["key"]: r["role"] for r in payload["runs"]}
    assert roles == {
        "silo_cold__aero_bound": run_data.ROLE_BOUND,
        "pad__aero_bound": run_data.ROLE_PAIRED_BASELINE,
        "readme_loads": run_data.ROLE_CASE,
        "light_s1": run_data.ROLE_OFFLOAD,
    }
    for r in payload["runs"]:
        assert r["payload_kg"] == BLOCK_PAYLOAD_KG and "metrics" in r["payload_source"], r["key"]
        assert r["checks"]["passed"], (r["key"], r["checks"]["failed"])
    wrong = _run(
        scene.scene_payload(derived_dir, ["wrong_payload"], display_dir=DISPLAY_DIR),
        "wrong_payload",
    )
    assert wrong["payload_kg"] == WRONG_PAYLOAD_KG and not wrong["checks"]["passed"]
    assert "liftoff identity" in wrong["checks"]["failed"]
    assert len(wrong["t"]) > 100  # flagged, still loaded


def test_zero_offload_pad_control_without_a_vehicle_block_closes(derived_dir: Path) -> None:
    """pad__offload_stage1 (a pad control, no vehicle block of its own) closes its mass,
    starts full, carries the pad control's role and note, and the offload caveats come
    along word for word."""
    payload = scene.scene_payload(
        derived_dir, ["pad", "pad__offload_stage1"], display_dir=DISPLAY_DIR
    )
    control = _run(payload, "pad__offload_stage1")
    assert control["role"] == run_data.ROLE_OFFLOAD
    assert control["offload_kind"] == run_data.OFFLOAD_PAD_CONTROL
    assert control["checks"]["passed"], control["checks"]["failed"]
    assert control["tanks"]["start_fill"] == [1.0, 1.0]
    assert control["tanks"]["offload_fraction"] == [0.0, 0.0]
    assert "pad control" in control["offload_note"]
    assert "(pad control" in control["label"]
    assert payload["offload_caveats"] == list(OFFLOAD_CAVEATS)
    assert payload["caveats"][-2:] == list(OFFLOAD_CAVEATS)


def test_offload_case_and_paired_pad_fill_against_the_full_load_a_case_against_its_own(
    derived_dir: Path,
) -> None:
    """light_s1 (an offload case) and light_s1__pad (its paired pad) start at 0.9 of the
    experiment's stage-1 load, their checks taking the fraction from the case record; the
    same folder read as the case ``light`` starts full against its own block; the
    readme-loads case (395.7 t and 92.67 t loads) starts full too."""
    payload = scene.scene_payload(
        derived_dir, ["light_s1", "light_s1__pad", "light", "readme_loads"], display_dir=DISPLAY_DIR
    )
    for key in ("light_s1", "light_s1__pad"):
        r = _run(payload, key)
        assert (
            r["tanks"]["start_fill"][0] == pytest.approx(0.9, abs=1e-6)
            and r["tanks"]["start_fill"][1] == 1.0
        )
        assert r["tanks"]["offload_fraction"][0] == pytest.approx(0.1, abs=1e-6)
        assert r["tanks"]["not_loaded_kg"][0] == pytest.approx(
            (410.9 - LIGHT_LOAD_T) * 1000.0, abs=1e-3
        )
        assert "experiment's vehicle block" in r["tanks"]["fill_reference"]
        assert r["checks"]["passed"], (key, r["checks"]["failed"])
        fill_item = next(
            i for i in r["checks"]["items"] if i["name"].startswith("stage-1 start fill")
        )
        assert "case record" in fill_item["detail"]
        assert r["fill1"][0] == pytest.approx(0.9, abs=1e-6)
    light = _run(payload, "light")
    assert light["role"] == run_data.ROLE_CASE and light["tanks"]["start_fill"] == [1.0, 1.0]
    assert "own vehicle block" in light["tanks"]["fill_reference"]
    assert light["tanks"]["load_kg"][0] == pytest.approx(LIGHT_LOAD_T * 1000.0, abs=1e-6)
    readme = _run(payload, "readme_loads")
    assert readme["tanks"]["start_fill"] == [1.0, 1.0] and readme["checks"]["passed"]
    assert readme["tanks"]["load_kg"] == [395_700.0, 92_670.0]
    assert readme["vehicle"] == "generic_f9_class_2d_readme_loads"
    assert readme["geometry"] is not None and not readme["geometry"]["generic"]
    paired = _run(payload, "light_s1__pad")
    assert (
        paired["offload_kind"] == run_data.OFFLOAD_PAIRED_PAD
        and "paired pad" in paired["offload_note"]
    )
    assert paired["payload_kg"] == PAIRED_PAYLOAD_KG and paired["checks"]["passed"]


def test_offload_notes_are_the_replay_pages_own(derived_dir: Path) -> None:
    """Every offload run's ``note`` and ``offload_note`` are replay.replay_offload_note for
    the same record (the one note source of D-SP2-23), so the scene says what the replay
    page says: the paired pad flies its own payload capacity, short of P_ref; the penalty
    row names its assumed +8.1 t; the fixed case is imposed and read against P_ref (short
    of it: a payload loss at that offload, D-SP2-27); the stage-2 solve is quoted net of
    the pad control and
    says its verification failed; a pad control reports what it found; every tonnes
    figure carries two decimals (the penalty's +8.1 t is written as the findings write
    it). Each copied folder closes its checks against its own block."""
    metrics = run_data.read_json(derived_dir / run_data.METRICS_FILE)
    offload = metrics["offload"]
    for runs in (
        ["light_s1__pad", "light_s1_dry+8.1t", "light_fix10pct", "light_s2"],
        ["light_s1", "pad__offload_stage1"],
    ):
        payload = scene.scene_payload(derived_dir, runs, display_dir=DISPLAY_DIR)
        for r in payload["runs"]:
            expected = replay.replay_offload_note(offload, r["key"], "pad")
            assert r["note"] == r["offload_note"] == expected, r["key"]
            assert r["checks"]["passed"], (r["key"], r["checks"]["failed"])
            note = r["note"]
            assert not re.findall(r"(?<!\+)\b\d+\.\d t\b", note), note  # no one-decimal tonnes
            if r["offload_kind"] != run_data.OFFLOAD_PAD_CONTROL:
                assert re.search(r"\b\d+\.\d\d t\b", note), note
        notes = {r["key"]: r["note"] for r in payload["runs"]}
        if "light_s1__pad" in notes:
            paired = notes["light_s1__pad"]
            assert "flying its own payload capacity, 21,398.0 kg" in paired
            assert "(1,402.0 kg short of P_ref = 22,800.0 kg)" in paired
            assert "41.09 t stage-1 offload and no push" in paired
            penalty = notes["light_s1_dry+8.1t"]
            assert "(solved with an assumed +8.1 t of stage-1 dry mass;" in penalty
            fixed = notes["light_fix10pct"]
            assert "(imposed;" in fixed and "flying 21,398.0 kg" in fixed
            assert "1,402.0 kg short of P_ref: a payload loss at this offload" in fixed
            assert "not a propellant saving" in fixed and "saved" not in fixed
            s2 = notes["light_s2"]
            assert "10.75 t less stage-2 propellant (solved; 10.00% of the stage-2 load" in s2
            assert "quoted 10.25 t net of the pad control's 0.50 t" in s2
            assert "verification failed (+15.36 kg against 2.3 kg)" in s2
            assert "the gross removal is a flagged lower bound" in s2 and "1 flag" in s2
            assert "0.0% of the stage-1 load" not in s2
        else:
            assert (
                "41.09 t less propellant (solved; 10.00% of the stage-1 load" in notes["light_s1"]
            )
            control = notes["pad__offload_stage1"]
            assert control.startswith("pad control (stage1): pad's own offload at P_ref")
            assert "none found (status no_offload" in control


def test_offload_runs_are_labelled_by_kind_and_carry_their_flags(derived_dir: Path) -> None:
    """The scene labels an offload case's recorded run by what its offload is (a penalty
    row with its assumed dry mass, a solve, an imposed fixed case) where the replay page
    says '(offload)' alone; a stage-2 or both-stage solve says it is a property of the
    vehicle model (criterion 7) and a solve with a stage-2 pre-offload names the imposed
    part, so neither reads as the stage-1 headline; a paired pad and a pad control keep
    the replay's label. The
    flags list names a failed verification (with its reading) and each flag of the case
    record; a passed, unflagged case and a paired pad carry none. The page shows the note
    and the flags (tests/test_scene_page.py checks the template's wiring)."""
    runs = {
        r["key"]: r
        for selection in (
            ["light_s1", "light_s1__pad", "light_s1_dry+8.1t"],
            ["light_fix10pct", "light_s2"],
        )
        for r in scene.scene_payload(derived_dir, selection, display_dir=DISPLAY_DIR)["runs"]
    }
    assert runs["light_s1"]["label"] == "light_s1 (offload, solved)"
    assert runs["light_s1_dry+8.1t"]["label"] == (
        "light_s1_dry+8.1t (offload penalty row: assumed +8.1 t of stage-1 dry mass)"
    )
    assert runs["light_fix10pct"]["label"] == "light_fix10pct (offload, imposed)"
    assert runs["light_s2"]["label"] == (
        "light_s2 (offload, solved, stage 2: a property of the vehicle model)"
    )
    assert runs["light_s1__pad"]["label"] == "light_s1__pad (paired pad)"
    # a both-stage solve and a stage-1 solve with an imposed stage-2 pre-offload (records as
    # results/silo_offload_2d writes them: silo_cold_both, silo_cold_s1_s2pre2t)
    solve = {"kind": run_data.OFFLOAD_SOLVED_KIND, "status": "ok"}
    label = scene.scene_run_label
    case, role = run_data.OFFLOAD_CASE, run_data.ROLE_OFFLOAD
    assert label("b", role, False, case, {**solve, "mode": "both"}) == (
        "b (offload, solved, both stages: a property of the vehicle model)"
    )
    pre = {**solve, "mode": "stage1", "stage2_preoffload_kg": 2000.0}
    assert label("p", role, False, case, pre) == (
        "p (offload, solved, plus 2.00 t imposed on stage 2)"
    )
    assert label("z", role, False, case, {**pre, "stage2_preoffload_kg": 0.0}) == (
        "z (offload, solved)"
    )
    flags = runs["light_s2"]["flags"]
    assert flags[0] == (
        "verification failed (+15.36 kg against 2.3 kg): the gross removal is a flagged lower bound"
    )
    flag = "offload: offload_verify_mismatch: the payload search ended ok above P_ref"
    assert flags[1:] == [flag]
    for key in ("light_s1", "light_s1__pad", "light_s1_dry+8.1t", "light_fix10pct"):
        assert runs[key]["flags"] == [], key
    assert all(r["yardstick"] is False for r in runs.values())
    control = scene.scene_payload(derived_dir, ["pad__offload_stage1"], display_dir=DISPLAY_DIR)
    assert control["runs"][0]["label"] == "pad__offload_stage1 (pad control)"
    assert control["runs"][0]["flags"] == []


def test_offload_caveats_appear_only_with_an_offload_run_and_the_exploratory_line(
    derived_dir: Path, exploratory_dir: Path
) -> None:
    """Without an offload run shown the offload caveats are absent; with the exploratory
    label the replay's EXPLORATORY_CAVEAT leads the list and the payload says so."""
    plain = scene.scene_payload(derived_dir, ["pad", "silo_cold"], display_dir=DISPLAY_DIR)
    assert plain["offload_caveats"] == [] and not plain["exploratory"]
    assert plain["label"] == "calibration"  # the fixture's label: cases need it; not exploratory
    assert not any(c in plain["caveats"] for c in OFFLOAD_CAVEATS)
    marked = scene.scene_payload(exploratory_dir, ["pad", "light_s1"], display_dir=DISPLAY_DIR)
    assert marked["exploratory"] and marked["label"] == replay.EXPLORATORY_LABEL
    assert marked["caveats"][0] == replay.EXPLORATORY_CAVEAT
    assert marked["caveats"][-2:] == list(OFFLOAD_CAVEATS)


# ------------------------------------------------------------------ refusals and exclusions


def test_refusals(real_dir: Path, tmp_path: Path) -> None:
    """A 1-D directory, a sweep directory, a sweep point, a directory with FAILED.txt and one
    without summary.md are each refused with a SceneError (a RunDataError) that names the
    reason; a missing directory too."""
    one_d = tmp_path / "results" / "silo_screening_1d" / "20260101T000000Z"
    one_d.mkdir(parents=True)
    _write_json(
        one_d / run_data.METRICS_FILE, {"experiment": "x", "baseline": "pad", "runs": {"pad": {}}}
    )
    (one_d / scene.SUMMARY_FILE).write_text("# s\n", encoding="utf-8")
    with pytest.raises(scene.SceneError, match="vertical_1d run; the scene shows planar_2d"):
        scene.scene_payload(one_d, None, display_dir=DISPLAY_DIR)
    sweep = tmp_path / "results" / "sweep_exp" / "20260101T000001Z"
    (sweep / scene.SWEEP_BASELINE_DIR).mkdir(parents=True)
    (sweep / "sweep_1" / "run_0001").mkdir(parents=True)
    (sweep / scene.SUMMARY_FILE).write_text("# s\n", encoding="utf-8")
    with pytest.raises(scene.SceneError, match="is a sweep directory"):
        scene.scene_payload(sweep, None, display_dir=DISPLAY_DIR)
    point = sweep / "sweep_1" / "run_0001"
    _write_json(point / run_data.METRICS_FILE, {"experiment": "x", "run": {}, "metrics": {}})
    (point / scene.SUMMARY_FILE).write_text("# s\n", encoding="utf-8")
    with pytest.raises(scene.SceneError, match="not an experiment results directory"):
        scene.scene_payload(point, None, display_dir=DISPLAY_DIR)
    failed = tmp_path / "failed"
    shutil.copytree(real_dir, failed)
    (failed / scene.FAILED_MARKER).write_text("boom\n", encoding="utf-8")
    with pytest.raises(scene.SceneError, match=r"FAILED\.txt"):
        scene.scene_payload(failed, None, display_dir=DISPLAY_DIR)
    incomplete = tmp_path / "incomplete"
    shutil.copytree(real_dir, incomplete)
    (incomplete / scene.SUMMARY_FILE).unlink()
    with pytest.raises(scene.SceneError, match=r"no summary\.md"):
        scene.scene_payload(incomplete, None, display_dir=DISPLAY_DIR)
    with pytest.raises(scene.SceneError, match="not found"):
        scene.scene_payload(tmp_path / "nowhere", None, display_dir=DISPLAY_DIR)
    with pytest.raises(scene.SceneError, match="unknown run"):
        scene.scene_payload(real_dir, ["nope"], display_dir=DISPLAY_DIR)
    assert issubclass(scene.SceneError, run_data.RunDataError)
    assert scene.FAILED_MARKER == results_io.FAILED_MARKER
    with pytest.raises(scene.SceneError, match=r"no scene\.yaml"):
        scene.scene_payload(real_dir, ["pad"], display_dir=tmp_path / "no_display")


def test_a_run_with_an_empty_time_series_is_left_out_with_its_reason(
    real_dir: Path, tmp_path: Path
) -> None:
    """A run whose timeseries.csv has a header only (a failed search) is left out under
    ``excluded`` with a one-line reason while the others play; a selection of such runs
    alone is refused."""
    ghost = tmp_path / "ghost"
    shutil.copytree(real_dir, ghost)
    header = (real_dir / "pad" / run_data.SERIES_FILE).read_text(encoding="utf-8").splitlines()[0]
    (ghost / "ghost").mkdir()
    (ghost / "ghost" / run_data.SERIES_FILE).write_text(header + "\n", encoding="utf-8")
    events_header = (
        (real_dir / "pad" / run_data.EVENTS_FILE).read_text(encoding="utf-8").splitlines()[0]
    )
    (ghost / "ghost" / run_data.EVENTS_FILE).write_text(events_header + "\n", encoding="utf-8")
    metrics = run_data.read_json(ghost / run_data.METRICS_FILE)
    metrics["runs"]["ghost"] = {**metrics["runs"]["pad"], "status": "search_failed"}
    _write_json(ghost / run_data.METRICS_FILE, metrics)
    config = run_data.read_yaml(ghost / run_data.CONFIG_FILE)
    config["runs"]["ghost"] = {"run": config["runs"]["pad"]["run"]}
    (ghost / run_data.CONFIG_FILE).write_text(json.dumps(config), encoding="utf-8")
    payload = scene.scene_payload(ghost, ["pad", "ghost"], display_dir=DISPLAY_DIR)
    assert [r["key"] for r in payload["runs"]] == ["pad"]
    assert payload["excluded"] == [
        {
            "run": "ghost",
            "reason": "ghost has an empty time series (a failed search or guidance writes no "
            "trajectory); left out of the scene",
        }
    ]
    with pytest.raises(scene.SceneError, match="none of the selected runs"):
        scene.scene_payload(ghost, ["ghost"], display_dir=DISPLAY_DIR)


# ------------------------------------------------------------------ events, bodies, constants


def test_events_are_labelled_by_name_and_stage_with_the_pad_liftoff_synthetic(
    real_payload: dict[str, Any],
) -> None:
    """Every event is labelled '<name> (<stage>)' and sits at its matched row's time, which
    is a sample time; the pad gets a synthetic liftoff at release and a synthetic ramp end
    at t_ign + t_startup, both marked; the silo gets neither; events at one time are
    grouped; the stage-1 drop and the fairing drop carry mass before and after."""
    pad = _run(real_payload, "pad")
    labels = [e["label"] for e in pad["events"]]
    assert "liftoff (stage1)" in labels and "ramp_end (stage1)" in labels
    liftoff = next(e for e in pad["events"] if e["name"] == scene.LIFTOFF_EVENT)
    release = next(e for e in pad["events"] if e["name"] == scene.RELEASE_EVENT)
    assert liftoff["synthetic"] and not liftoff["recorded"] and liftoff["t"] == release["t"] == 0.0
    assert "release row" in liftoff["synthetic_from"]
    ramp_end = next(e for e in pad["events"] if e["name"] == scene.RAMP_END_EVENT)
    assert ramp_end["synthetic"] and ramp_end["t"] == pytest.approx(
        pad["startup"]["t_ign_rel_release_s_stage1"] + pad["startup"]["t_startup_s_stage1"]
    )
    assert ramp_end["row_matched"]
    assert all(not e["synthetic"] for e in _run(real_payload, "silo_cold")["events"])
    times = set(pad["t"])
    for e in pad["events"]:
        assert e["label"] == (e["name"] if e["stage"] is None else f"{e['name']} ({e['stage']})")
        if e["row_matched"]:
            assert e["t"] in times and e["sample"] is not None
            assert pad["t"][e["sample"]] == e["t"]
    grouped = {g["t"]: g["labels"] for g in pad["event_groups"]}
    assert set(grouped[0.0]) >= {"release (stage1)", "liftoff (stage1)", "ramp_end (stage1)"}
    staging = next(e for e in pad["events"] if e["name"] == "staging")
    assert staging["dropped"] == "stage1" and staging["m_before_kg"] - staging[
        "m_after_kg"
    ] == pytest.approx(22_200.0)
    fairing = next(e for e in pad["events"] if e["name"] == "fairing")
    assert fairing["dropped"] == "fairing" and fairing["m_before_kg"] - fairing[
        "m_after_kg"
    ] == pytest.approx(1_700.0)
    assert [e["t"] for e in pad["events"]] == sorted(e["t"] for e in pad["events"])


def _rows(times: list[float], phases: list[str]) -> display.RunRows:
    """RunRows of synthetic samples at ``times`` [s after release, the run clock equal to
    it] in ``phases``, stage 1 throughout, the other columns constant."""
    t = np.array(times, dtype=float)
    one = np.ones_like(t)
    return display.RunRows(
        t_s=t,
        t_rel_s=t,
        phase=tuple(phases),
        stage=("stage1",) * len(t),
        alt_m=one,
        downrange_m=one,
        speed_rel_mps=one,
        pitch_rad=one,
        m_kg=5.0e5 * one,
        thrust_vac_N=one,
    )


def _match(name: str, t: float, phase: str, rows: display.RunRows) -> display.EventMatch:
    """An EventRow named ``name`` at ``t`` (run clock = release clock) matched to ``rows``."""
    row = run_data.EventRow(t, t, name, phase, "stage1", 1.0, 1.0, 1.0, 1.0, 1.0, 5.0e5)
    (match,) = display.match_events(rows.t_s, [row])
    return match


def test_ramp_end_is_synthesised_for_any_run_whose_ramp_ends_inside_the_hold() -> None:
    """A hot start held before the push (silo_hot_full: ignition at -2 s in HOLD, a 2 s ramp
    ending at push start) has no ramp_end row and gets a synthetic one at the push-start row,
    matched; being assisted it gets no liftoff. A pad gets both. A run with a ramp_end row
    (a cold silo lit on the track) gets neither, and so does an instant startup."""
    rows = _rows([-4.6, -3.6, -2.6, -2.6, 0.0, 0.0, 1.0], ["HOLD"] * 3 + ["ASSIST"] * 3 + ["KICK"])
    hot = [
        _match("ignition", -4.6, "HOLD", rows),
        _match("push_start", -2.6, "ASSIST", rows),
        _match("release", 0.0, "ASSIST", rows),
    ]
    m = {
        "startup_kind_stage1": "ramp",
        "t_ign_rel_release_s_stage1": -4.6,
        "t_startup_s_stage1": 2.0,
    }
    made = scene.synthetic_events(hot, rows, m, assisted=True)
    assert [name for _, name, _ in made] == [scene.RAMP_END_EVENT]
    match, _, how = made[0]
    assert match.index == 2 and match.count == 2 and match.event.t_rel_s == -2.6
    assert match.event.phase == "ASSIST" and not match.event.recorded
    assert "hot start held before the push" in how
    pad_rows = _rows([-2.0, -1.0, 0.0, 1.0], ["HOLD"] * 3 + ["VERTICAL_RISE"])
    pad = [_match("ignition", -2.0, "HOLD", pad_rows), _match("release", 0.0, "HOLD", pad_rows)]
    m_pad = {
        "startup_kind_stage1": "ramp",
        "t_ign_rel_release_s_stage1": -2.0,
        "t_startup_s_stage1": 2.0,
    }
    assert [
        name for _, name, _ in scene.synthetic_events(pad, pad_rows, m_pad, assisted=False)
    ] == [
        scene.LIFTOFF_EVENT,
        scene.RAMP_END_EVENT,
    ]
    cold = [*hot, _match("ramp_end", 0.0, "ASSIST", rows)]
    assert scene.synthetic_events(cold, rows, m, assisted=True) == []
    assert scene.synthetic_events(hot, rows, {**m, "startup_kind_stage1": "instant"}, True) == []
    # the sentence says why no row exists: the hold is lit but sampled in closed form
    assert "in or at the end of the hold" in how and "closed form" in how
    assert "not integrated" not in how and "lit" in how
    text = scene.DISPLAY_ONLY[6]
    assert "in or at the end of the hold" in text and "closed form" in text
    assert "inside the hold" not in text and "not integrated" not in text


def test_separated_bodies_coast_from_their_events_and_are_clipped(
    real_payload: dict[str, Any],
) -> None:
    """The pad has a spent stage from the staging event and fairing halves from the fairing
    event, each with a path starting at its separation time and ending no later than the
    run's last time, its own apex and impact (inside this run), a dropped mass and a held
    angle; silo_failed has none."""
    pad = _run(real_payload, "pad")
    names = {b["name"]: b for b in pad["bodies"]}
    assert set(names) == {scene.STAGE1_BODY, scene.FAIRING_BODY}
    staging = next(e for e in pad["events"] if e["name"] == "staging")
    stage = names[scene.STAGE1_BODY]
    assert stage["from_event"] == "staging" and stage["t_separation"] == staging["t"]
    assert stage["mass_kg"] == pytest.approx(22_200.0) and stage["path"]["t"][0] == staging["t"]
    assert stage["path"]["t"][-1] <= pad["end"]["t"] + 1e-6
    assert stage["impact"]["within_run"] and stage["apex"]["within_run"]
    assert stage["apex"]["alt_m"] > staging["alt_m"] and stage["impact"]["speed_mps"] > 2_000.0
    assert stage["impact"]["downrange_m"] > staging["downrange_m"]
    assert stage["energy_drift_rel"] < 1e-8 and stage["h_drift_rel"] < 1e-8
    assert isinstance(stage["screen_angle_deg"], float) and "display-only" in stage["note"]
    halves = names[scene.FAIRING_BODY]
    assert halves["from_event"] == "fairing" and halves["mass_kg"] == pytest.approx(1_700.0)
    assert halves["t_separation"] > stage["t_separation"]
    assert _run(real_payload, "silo_failed")["bodies"] == []


def test_each_spent_stage_carries_its_own_measured_coast_gap(
    real_payload: dict[str, Any],
) -> None:
    """The spent stage's staging_coast_gap_m is the run's own number: finite, above zero
    and under 1 m for the fixture's pad and silo_cold, measured over every recorded
    COAST_STAGING sample at or after the staging sample (the row count carried beside
    it covers the whole coast, whose selected samples are a subset), and the pad's gap is
    the larger (it stages lower, in denser air); the fairing halves, dropped under thrust
    with no recorded coast after them, carry None over 0 rows; silo_failed has no body.
    The display-only text quotes figures for named recorded runs with their date and
    never a bound on every run."""
    for key in ("pad", "silo_cold"):
        run = _run(real_payload, key)
        stage = next(b for b in run["bodies"] if b["name"] == scene.STAGE1_BODY)
        gap = stage["staging_coast_gap_m"]
        assert isinstance(gap, float) and math.isfinite(gap) and 0.0 < gap < 1.0, key
        coast_samples = sum(1 for p in run["phase"] if p == "COAST_STAGING")
        assert stage["staging_coast_rows"] >= coast_samples >= 2, key
        halves = next(b for b in run["bodies"] if b["name"] == scene.FAIRING_BODY)
        assert halves["staging_coast_gap_m"] is None and halves["staging_coast_rows"] == 0
    pad_gap = next(
        b for b in _run(real_payload, "pad")["bodies"] if b["name"] == scene.STAGE1_BODY
    )["staging_coast_gap_m"]
    silo_gap = next(
        b for b in _run(real_payload, "silo_cold")["bodies"] if b["name"] == scene.STAGE1_BODY
    )["staging_coast_gap_m"]
    assert pad_gap > silo_gap
    text = scene.DISPLAY_ONLY[2]
    assert "staging_coast_gap_m" in text and "2026-10-05" in text and "0.608 m" in text
    assert "every recorded run" not in text and "every run" not in text
    assert "results/silo_screening_2d/20260930T175743Z" in text
    assert "nothing bounds it for a run not yet flown" in text


def test_site_omega_p_refuses_a_block_without_a_site() -> None:
    """omega_p comes from the run block's site and is never defaulted: a block without
    latitude or azimuth, or without a boolean include_rotation, is refused;
    include_rotation false gives 0 with the site kept."""
    with pytest.raises(scene.SceneError, match=r"site\.latitude_deg"):
        scene.site_omega_p({})
    with pytest.raises(scene.SceneError, match=r"site\.latitude_deg"):
        scene.site_omega_p({"site": {"latitude_deg": 28.5}})
    omega, site = scene.site_omega_p(
        {"site": {"latitude_deg": 28.5, "azimuth_deg": 90.0, "include_rotation": True}}
    )
    assert omega == pytest.approx(OMEGA_EARTH_RADS * math.cos(math.radians(28.5)), rel=1e-15)
    assert site == {"latitude_deg": 28.5, "azimuth_deg": 90.0, "include_rotation": True}
    still, kept = scene.site_omega_p(
        {"site": {"latitude_deg": 0.0, "azimuth_deg": 90.0, "include_rotation": False}}
    )
    assert still == 0.0 and kept["latitude_deg"] == 0.0 and not kept["include_rotation"]
    # include_rotation is never defaulted either (PlanarSiteConfig makes it explicit)
    for rotation in ({}, {"include_rotation": None}, {"include_rotation": "yes"}):
        with pytest.raises(scene.SceneError, match=r"site\.include_rotation"):
            scene.site_omega_p({"site": {"latitude_deg": 28.5, "azimuth_deg": 90.0, **rotation}})


def test_constants_geometry_and_the_generic_fallback(
    real_payload: dict[str, Any], real_dir: Path, tmp_path: Path
) -> None:
    """R_E is constants.R_EARTH_M; omega_p is omega_E cos(lat) sin(az) of the site; the
    display geometry is the f9_class file (not generic) for the experiment vehicle and the
    readme-loads case; with a display directory holding scene.yaml alone the shape is
    generic, flagged with the reason, sized from the reference area; so is a vehicle the
    shipped files do not list, and one without a reference area either is refused."""
    assert real_payload["constants"]["R_E_m"] == R_EARTH_M
    site = real_payload["constants"]["site"]
    expected = (
        OMEGA_EARTH_RADS
        * math.cos(math.radians(site["latitude_deg"]))
        * math.sin(math.radians(site["azimuth_deg"]))
    )
    assert real_payload["constants"]["omega_p_rads"] == pytest.approx(expected, rel=1e-15)
    assert _run(real_payload, "pad")["omega_p_rads"] == pytest.approx(expected, rel=1e-15)
    assert (
        not real_payload["display"]["generic"] and real_payload["display"]["stack_length_m"] == 70.0
    )
    assert real_payload["vehicle"] == "generic_f9_class_2d"
    assert (
        _run(real_payload, "pad")["geometry"] is None
    )  # the experiment vehicle: the top-level one
    assert (
        real_payload["camera"]["min_view_height_m"] == 150.0
        and real_payload["camera"]["margin"] == 1.25
    )
    assert real_payload["tolerances"]["mass_kg"] == display.MASS_TOL_KG
    assert real_payload["footer"] == scene.FOOTER_TEXT and len(real_payload["display_only"]) == 7
    only_scene = tmp_path / "display"
    only_scene.mkdir()
    shutil.copy(DISPLAY_DIR / scene.SCENE_CONFIG_FILE, only_scene / scene.SCENE_CONFIG_FILE)
    generic = scene.scene_payload(real_dir, ["pad"], display_dir=only_scene)["display"]
    assert generic["generic"] and "no display file" in generic["reason"]
    assert generic["vehicle"]["body_diameter_m"] == pytest.approx(math.sqrt(4.0 * 10.52 / math.pi))
    # a vehicle no display file lists (a new vehicle file, say) gets the generic shape,
    # flagged with its reason, beside the shipped display files (D-SP2-18)
    configs = scene.load_display_configs(DISPLAY_DIR)
    scene_cfg = scene.load_scene_config(DISPLAY_DIR)
    unlisted = "some_other_vehicle_2d"
    assert all(unlisted not in cfg.applies_to for cfg in configs)
    block = {"name": unlisted, "aero": {"reference_area_m2": {"value": 4.0, "assumed": True}}}
    other = scene.display_geometry_for(unlisted, block, configs, scene_cfg, DISPLAY_DIR)
    assert other.generic and unlisted in other.reason and "generic shape" in other.reason
    assert other.vehicle["body_diameter_m"] == pytest.approx(math.sqrt(16.0 / math.pi))
    with pytest.raises(scene.SceneError, match="no display file"):
        scene.display_geometry_for(unlisted, {"name": unlisted}, configs, scene_cfg, DISPLAY_DIR)
    # the display-only text names where each drawn length comes from
    shapes = scene.DISPLAY_ONLY[0]
    assert "configs/display" in shapes and "stroke and braking distance" in shapes


def test_caveats_are_a_superset_of_the_replay_page_for_the_same_selection(
    real_dir: Path, derived_dir: Path
) -> None:
    """Every caveat replay.caveats gives a selection is in the scene's list, in order, for
    the real directory and for the derived one with offload runs."""
    for run_dir, runs in (
        (real_dir, ["pad", "silo_cold", "silo_failed", "readme_loads"]),
        (derived_dir, ["pad", "light_s1", "light_s1__pad", "pad__offload_stage1"]),
    ):
        expected = replay.replay_data(run_dir, runs)["meta"]["caveats"]
        got = scene.scene_payload(run_dir, runs, display_dir=DISPLAY_DIR)["caveats"]
        assert got[: len(expected)] == expected and len(expected) >= 2


def test_every_real_run_passes_every_load_time_check(real_dir: Path) -> None:
    """Every run folder of the real directory loads with every applicable check passed, the
    selection converged with every field inside half its tolerance (and said so by the
    last item of the run's checks), thrust off on the last sample, the stage exact at the
    staging sample and the fairing flag off after its drop."""
    _, available = run_data.run_names(real_dir)
    assert set(available) >= {
        "pad",
        "silo_cold",
        "silo_failed",
        "readme_loads",
        "light",
        "lighter_payload",
        "light_penalty",
        "light_stage2",
        "silo_cold__aero_bound",
        "pad__aero_bound",
    }
    for start in range(0, len(available), run_data.MAX_RUNS):
        chunk = available[start : start + run_data.MAX_RUNS]
        payload = scene.scene_payload(real_dir, chunk, display_dir=DISPLAY_DIR)
        for r in payload["runs"]:
            assert r["checks"]["passed"], (r["key"], r["checks"]["failed"])
            assert (
                r["selection"]["converged"]
                and r["selection"]["passes"] <= display.SELECTION_MAX_PASSES
            )
            assert all(
                w["frac_of_tol"] <= display.SELECTION_HALF for w in r["selection"]["worst"].values()
            )
            *_, mass_item, selection_item = r["checks"]["items"]
            assert mass_item["name"].startswith(
                f"rebuilt stack mass within {display.MASS_TOL_KG:g} kg"
            )
            assert selection_item["passed"] is True
            assert selection_item["unit"] == scene.SELECTION_CHECK_UNIT
            assert selection_item["worst"] == max(
                w["frac_of_tol"] for w in r["selection"]["worst"].values()
            )
            assert not r["thrust_on"][-1]
            assert len(r["t"]) == len(r["stage"]) == len(r["fairing_on"]) == len(r["thrust_on"])
            if r["key"] != "silo_failed":
                staging = next(e for e in r["events"] if e["name"] == "staging")
                k = staging["sample"]
                assert r["stage"][k] == 1 and r["stage"][k - 1] == 0 and r["t"][k] == r["t"][k - 1]
                fairing = next(e for e in r["events"] if e["name"] == "fairing")
                j = fairing["sample"]
                assert not r["fairing_on"][j] and r["fairing_on"][j - 1]
                assert r["prop1_kg"][k - 1] == pytest.approx(0.0, abs=0.1)
            else:
                assert r["status"] == "impact" and all(not v for v in r["thrust_on"])
                assert all(
                    a == pytest.approx(90.0, abs=1e-3) for a in r["screen_angle_deg"]
                )  # held


# ------------------------------------------------------------------ settings fallbacks


def test_assist_settings_fall_back_to_the_config_and_derive_the_rest() -> None:
    """A pad gives None; an assisted run takes the metric first, the config when the metric
    is absent (a directory from before SP1) and derives the rest: a from v^2 / (2 L) when
    only an exit speed is configured, the braking distance, the facility length and the
    track start altitude; a track angle or exit altitude the block does not write is the
    schema's default, labelled 'default', never 'derived'."""
    assert scene.assist_settings({"model": "none"}, {}) is None
    assert scene.assist_settings({}, {}) is None
    cfg = {
        "model": "constant_accel",
        "exit_speed_mps": 80.0,
        "stroke_m": 200.0,
        "brake_decel_g": 5.0,
        "carriage_mass_t": 22.0,
        "shaft": "vented",
        "track": {"angle_deg": 90.0, "exit_altitude_m": 0.0},
    }
    out = scene.assist_settings(cfg, {})
    assert out["net_accel_mps2"] == pytest.approx(80.0**2 / 400.0)
    assert out["sources"]["net_accel_mps2"] == "derived" and out["sources"]["stroke_m"] == "config"
    assert out["braking_distance_m"] == pytest.approx(80.0**2 / (2.0 * 5.0 * 9.80665))
    assert out["facility_length_m"] == pytest.approx(200.0 + out["braking_distance_m"])
    assert out["track_start_altitude_m"] == pytest.approx(-200.0)
    assert out["carriage_mass_kg"] == 22_000.0 and out["sources"]["carriage_mass_kg"] == "config"
    assert out["push_time_s"] == pytest.approx(80.0 / out["net_accel_mps2"])
    metric = scene.assist_settings(
        cfg, {"stroke_m": 150.0, "net_accel_mps2": 20.0, "exit_speed_mps": 77.0}
    )
    assert metric["stroke_m"] == 150.0 and metric["sources"]["stroke_m"] == "metric"
    assert metric["net_accel_g"] == pytest.approx(20.0 / 9.80665)
    assert metric["exit_speed_mps"] == 77.0 and metric["sources"]["exit_speed_mps"] == "metric"
    assert out["sources"]["track_angle_deg"] == out["sources"]["exit_altitude_m"] == "config"
    # a track block written without its keys takes the schema's defaults, labelled so
    bare = scene.assist_settings({**cfg, "track": {}}, {})
    assert (bare["track_angle_deg"], bare["exit_altitude_m"]) == (90.0, 0.0)
    assert bare["sources"]["track_angle_deg"] == scene.SOURCE_DEFAULT
    assert bare["sources"]["exit_altitude_m"] == scene.SOURCE_DEFAULT
    assert bare["track_start_altitude_m"] == pytest.approx(-200.0)


def test_ramp_start_requested_and_achieved(real_payload: dict[str, Any]) -> None:
    """Without the SP1 metrics the achieved ramp start comes from the stage-1 ignition row;
    with them, from the metrics; a non-time trigger's request is passed through; a failed
    ignition has none."""
    silo = _run(real_payload, "silo_cold")["ramp_start"]
    assert silo["requested"] is None and silo["achieved"][
        "ramp_start_t_rel_release_s"
    ] == pytest.approx(0.5)
    assert silo["source"] == "metrics"
    assert _run(real_payload, "silo_failed")["ramp_start"]["achieved"] is None
    events = [
        run_data.EventRow(
            3.1, 0.5, "ignition", "KICK", "stage1", 37.1, 0.0, 71.8, 415.0, 1.57, 5.7e5
        )
    ]
    old = scene.ramp_start({}, events, "stage1")
    assert (
        old["source"] == "stage-1 ignition event row"
        and old["achieved"]["ramp_start_alt_m"] == 37.1
    )
    requested = scene.ramp_start(
        {
            "ramp_start_trigger": "depth",
            "ramp_start_requested_depth_m": 50.0,
            "ramp_start_alt_m": -50.0,
        },
        events,
        "stage1",
    )
    assert requested["requested"] == {
        "ramp_start_trigger": "depth",
        "ramp_start_requested_depth_m": 50.0,
    }
    assert requested["source"] == "metrics"


# ------------------------------------------------------------------ selection, git, default pair


def test_a_selection_that_did_not_converge_is_a_failing_check_item() -> None:
    """A lag ramp after 40 s (where the base grid keeps every 20th row) is outside half the
    plume tolerance until rows are inserted: with no insertion pass allowed the selection
    does not converge, and selection_check makes that a failing item of the run's
    CheckReport (worst = the largest residual over its tolerance, the field and time
    named), so the run is flagged by its checks, not by a second flag; the converged
    selection gives a passing item."""
    t = np.round(np.arange(40.0, 60.0, 0.05), 6)
    plume = 1.0 - np.exp(-(t - 40.0))
    fields = [display.SelectionField("plume", plume, display.PLUME_TOL)]
    stuck = display.select_rows(t, fields, [], max_passes=0)
    done = display.select_rows(t, fields, [])
    assert not stuck.converged and done.converged
    item = scene.selection_check(stuck)
    assert item.passed is False and item.worst == stuck.worst["plume"].frac
    assert item.worst > display.SELECTION_HALF and item.tolerance == display.SELECTION_HALF
    assert item.unit == scene.SELECTION_CHECK_UNIT
    assert "plume" in item.detail and "did not converge" in item.detail
    report = display.CheckReport((item,))
    assert not report.passed and report.failed == (item.name,)
    assert report.as_dict()["items"][0]["passed"] is False
    ok = scene.selection_check(done)
    assert ok.passed is True and ok.worst <= display.SELECTION_HALF
    assert "did not converge" not in ok.detail and ok.name == item.name


def test_git_record_keeps_an_unknown_state_unknown(
    real_payload: dict[str, Any], real_dir: Path, tmp_path: Path
) -> None:
    """The payload carries metrics.json's git record as written: a recorded dirty flag
    stays a boolean with its error; a git status that failed (dirty null, the reason in
    error) stays null with the reason, never read as clean; a record without keys reads
    hash 'unknown' and dirty null."""
    assert set(real_payload["git"]) == {"hash", "dirty", "error"}
    assert isinstance(real_payload["git"]["dirty"], bool)
    reason = "git status failed: TimeoutExpired: git status timed out"
    unknown = {"hash": "0123456789ab", "dirty": None, "error": reason}
    assert scene.git_record(unknown) == unknown
    assert scene.git_record({}) == {"hash": "unknown", "dirty": None, "error": None}
    no_git = {"hash": "no-git", "dirty": False, "error": "FileNotFoundError: git"}
    assert scene.git_record(no_git) == no_git
    assert scene.git_record({"hash": "abc", "dirty": "maybe"})["dirty"] is None
    copied = tmp_path / "unknown_git"
    shutil.copytree(real_dir, copied)
    metrics = run_data.read_json(copied / run_data.METRICS_FILE)
    metrics["git"] = unknown
    _write_json(copied / run_data.METRICS_FILE, metrics)
    payload = scene.scene_payload(copied, ["silo_failed"], display_dir=DISPLAY_DIR)
    assert payload["git"] == unknown and payload["git"]["dirty"] is None


def test_default_pair_follows_d_sp2_28(real_dir: Path, derived_dir: Path) -> None:
    """With no selection the scene shows D-SP2-28's pair, not the replay's default: the
    baseline beside the first solved stage-1 offload case (the derived directory's
    light_s1), else beside the first assisted variant that is not a yardstick (the real
    directory's silo_cold), else the baseline alone. On hand records: a stage-2 solve, a
    fixed case, a solve that found no offload and a case without a run folder are
    passed over; step-startup yardsticks and pads are never the right-hand run; with no
    baseline folder the right-hand run is shown alone."""
    real = scene.scene_payload(real_dir, None, display_dir=DISPLAY_DIR)
    assert [r["key"] for r in real["runs"]] == ["pad", "silo_cold"]
    assert run_data.run_names(real_dir)[0] != ["pad", "silo_cold"]  # the replay's default
    derived = scene.scene_payload(derived_dir, None, display_dir=DISPLAY_DIR)
    assert [r["key"] for r in derived["runs"]] == ["pad", "light_s1"]
    metrics = {
        "baseline": "pad",
        "runs": {
            "pad": {"startup_kind_stage1": "ramp"},
            "pad_instant": {"startup_kind_stage1": "step"},
            "silo_instant": {"startup_kind_stage1": "step"},
            "silo_cold": {"startup_kind_stage1": "ramp"},
        },
    }
    assisted = {"assist": {"model": "constant_accel"}}
    config = {
        "runs": {
            "pad": {"run": {"assist": {"model": "none"}}},
            "pad_instant": {"run": {"assist": {"model": "none"}}},
            "silo_instant": {"run": assisted},
            "silo_cold": {"run": assisted},
        }
    }
    names = ["pad", "pad_instant", "silo_instant", "silo_cold"]
    assert scene.default_pair(metrics, config, names) == ["pad", "silo_cold"]
    assert scene.default_pair(metrics, config, names[:3]) == ["pad"]  # yardsticks only
    cases = [
        {"kind": "solve", "mode": "stage2", "status": "ok", "run": "s2"},
        {"kind": "fixed", "mode": "stage1", "status": "ok", "run": "fix"},
        {"kind": "solve", "mode": "stage1", "status": "no_offload", "run": "none_found"},
        {"kind": "solve", "mode": "stage1", "status": "ok", "run": "missing"},
        {"kind": "solve", "mode": "stage1", "status": "ok", "run": "s1"},
    ]
    offload = {**metrics, "offload": {"cases": cases}}
    have = [*names, "s2", "fix", "none_found", "s1"]
    assert scene.default_pair(offload, config, have) == ["pad", "s1"]
    assert scene.default_pair(offload, config, have[:-1]) == ["pad", "silo_cold"]
    assert scene.default_pair(metrics, config, names[1:]) == ["silo_cold"]
    assert scene.default_pair({"baseline": "pad"}, {}, ["x", "y"]) == ["x"]


def _pushed_penalty_dir(derived_dir: Path, dst: Path) -> Path:
    """A copy of the derived directory whose offload runs light_s1 (the solved case) and
    light_s1_dry+8.1t (the penalty row) are pushed runs: each one's folder, run block and
    metrics record replaced by silo_cold's (a cold silo start), the ``offload.cases``
    records kept, so the penalty row's record still charges +8.1 t of stage-1 dry mass on a
    run with a push (A6v fix round 1: the derived fixture's own offload runs fly from the
    pad, where no structural line applies)."""
    shutil.copytree(derived_dir, dst)
    metrics = run_data.read_json(dst / run_data.METRICS_FILE)
    config = run_data.read_yaml(dst / run_data.CONFIG_FILE)
    for name in ("light_s1", "light_s1_dry+8.1t"):
        shutil.rmtree(dst / name)
        shutil.copytree(dst / "silo_cold", dst / name)
        metrics["offload"]["runs"][name] = copy.deepcopy(metrics["runs"]["silo_cold"])
        config["offload_runs"][name] = copy.deepcopy(config["runs"]["silo_cold"])
    _write_json(dst / run_data.METRICS_FILE, metrics)
    (dst / run_data.CONFIG_FILE).write_text(json.dumps(config), encoding="utf-8", newline="\n")
    return dst


def test_peak_q_row_kept_and_frame_caveats(
    real_dir: Path, real_payload: dict[str, Any], derived_dir: Path, tmp_path: Path
) -> None:
    """A3b review round 3. Each run's payload keeps its time series' peak q row at its own
    release-relative time, so the drawn path passes through it beside the page's max-Q mark
    (since fix round 4 the run's metrics max-Q, ``max_q``). The payload carries the caveat
    line every captured frame shows under its footer (the model in brief, each vehicle's
    calibration as the replay page words it, where every caveat is) and, per pushed run, what
    structural mass its own record charges for the push: none, or a penalty row's assumed
    stage-1 dry mass (A6v fix round 1: asserted on the payload of a pushed penalty row, which
    the earlier lookup named as uncharged)."""
    for r in real_payload["runs"]:
        frame = run_data.read_series_frame(
            real_dir, r["key"], scene.SCENE_COLUMNS, error=scene.SceneError
        )
        q = frame["q_pa"].to_numpy(dtype=float)
        if not np.isfinite(q).any():
            continue
        i = int(np.nanargmax(q))
        t_peak = float(scene.run_rows(frame).t_rel_s[i])
        shown = [-math.inf if v is None else v for v in r["q_pa"]]
        k = int(np.argmax(shown))
        assert shown[k] == pytest.approx(q[i], abs=0.51 * 10.0**-scene.Q_DECIMALS), r["key"]
        assert r["t"][k] == pytest.approx(t_peak, abs=0.51 * 10.0**-scene.TIME_DECIMALS), r["key"]
    caveat = real_payload["frame_caveat"]
    assert caveat.startswith(scene.FRAME_MODEL_TEXT) and caveat.endswith(scene.FRAME_MORE_TEXT)
    assert "not a forecast" in caveat
    for vehicle in {r["vehicle"] for r in real_payload["runs"]}:
        assert replay.calibration_caveat(vehicle) in caveat, vehicle
    notes = {r["key"]: r["structure_note"] for r in real_payload["runs"]}
    assert notes["pad"] is None and notes["readme_loads"] is None
    assert notes["silo_cold"] == "no structural mass is charged for the push"
    # the fixture's offload runs fly from the pad (no push): no note; a pushed penalty row's
    # record (the derived block's, read as a pushed run's) names its assumed dry mass
    derived = scene.scene_payload(
        derived_dir, ["pad", "light_s1", "light_s1_dry+8.1t"], display_dir=DISPLAY_DIR
    )
    assert all(r["structure_note"] is None for r in derived["runs"] if not r["assisted"])
    assert not any(r["assisted"] for r in derived["runs"])  # the fixture's offload runs: no push
    # the same block with the solved case and the penalty row flown as pushed runs: the payload's
    # own structure line names the penalty row's assumed dry mass and the solved case as uncharged
    penalty = (
        f"an assumed +{PENALTY_T:g} t of stage-1 dry mass is charged for the push: an "
        "assumption, not a sized structure"
    )
    uncharged = "no structural mass is charged for the push"
    pushed_dir = _pushed_penalty_dir(derived_dir, tmp_path / "pushed")
    pushed = scene.scene_payload(
        pushed_dir, ["pad", "light_s1", "light_s1_dry+8.1t"], display_dir=DISPLAY_DIR
    )
    by_key = {r["key"]: r for r in pushed["runs"]}
    assert by_key["light_s1"]["assisted"] and by_key["light_s1_dry+8.1t"]["assisted"]
    assert by_key["pad"]["structure_note"] is None
    assert by_key["light_s1"]["structure_note"] == uncharged
    assert by_key["light_s1_dry+8.1t"]["structure_note"] == penalty
    assert by_key["light_s1_dry+8.1t"]["offload_kind"] == run_data.OFFLOAD_CASE
    assert "assumed" in by_key["light_s1_dry+8.1t"]["label"]  # the label and the line agree
    # the pure function on the records run_payload finds (run_data.offload_role) and on none
    offload = run_data.read_json(pushed_dir / run_data.METRICS_FILE)["offload"]
    case = run_data.offload_role(offload, "light_s1_dry+8.1t")
    solved = run_data.offload_role(offload, "light_s1")
    assert case is not None and solved is not None
    assert scene.structure_note(case[1], True) == penalty
    assert scene.structure_note(solved[1], True) == uncharged
    assert scene.structure_note(None, True) == uncharged
    assert scene.structure_note(case[1], False) is None
    assert scene.structure_note(None, False) is None


# ------------------------------------------------------------------ import guard


def test_run_path_modules_never_import_display_or_scene() -> None:
    """No module of the run path (sim, results_io, search, guidance, dynamics, offload,
    compare, metrics, metrics_planar, run_data, the phases package) imports display or
    scene, by source scan; scene imports no run-path writer and reads no file itself;
    and in a fresh interpreter importing display loads no I/O module while importing sim
    loads neither display nor scene."""
    offenders = []
    for module in RUN_PATH_MODULES:
        tree = ast.parse((SRC / f"{module}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = str(node.module)
                names = {f"{mod}.{a.name}" for a in node.names} | {mod}
                if names & set(SCENE_MODULES):
                    offenders.append(f"{module}: from {mod} import ...")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in SCENE_MODULES:
                        offenders.append(f"{module}: import {alias.name}")
    assert not offenders, offenders
    # the scene reads through run_data and never through results_io, sim or compare
    tree = ast.parse((SRC / "scene.py").read_text(encoding="utf-8"))
    imported = {
        str(n.module)
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom) and str(n.module).startswith("launchsim")
    } | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    assert not ({"launchsim.results_io", "launchsim.sim", "launchsim.compare"} & imported)
    assert not ({"results_io", "sim", "compare", "plots"} & names)
    # ... and reads no file itself: no pandas or yaml reader call (run_data does the reading)
    calls = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not ({"read_csv", "read_parquet", "safe_load", "read_text", "open"} & calls), calls
    # one fresh interpreter: importing display (pure) loads no I/O module of the package
    # (run_data, replay, scene, plots, results_io, sim) and no yaml reader; then importing
    # sim and results_io (the run path) loads neither display nor scene
    io_modules = (
        "launchsim.run_data",
        "launchsim.replay",
        "launchsim.scene",
        "launchsim.plots",
        "launchsim.results_io",
        "launchsim.sim",
        "yaml",
    )
    code = (
        "import json, sys\n"
        "import launchsim.display\n"
        f"print(json.dumps(sorted(m for m in sys.modules if m in {io_modules!r})))\n"
        "del sys.modules['launchsim.display']\n"
        "import launchsim.sim, launchsim.results_io\n"
        f"print(json.dumps(sorted(m for m in sys.modules if m in {SCENE_MODULES!r})))\n"
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
    after_display, after_sim = done.stdout.strip().splitlines()[-2:]
    assert json.loads(after_display) == [] and json.loads(after_sim) == []
    assert np.__name__ == "numpy"  # the module under test uses numpy arrays throughout


def test_max_q_is_the_run_metrics_record(real_dir: Path, real_payload: dict[str, Any]) -> None:
    """A3b fix round 4: each run's ``max_q`` is its metrics record's max_q_pa at max_q_time_s
    (the planar metrics' refined peak, already a time after release), rounded to the
    payload's decimals, not the largest q among the payload's rows; a record without max-Q
    gives None, so the page shows none."""
    metrics = run_data.read_json(real_dir / run_data.METRICS_FILE)
    config = run_data.read_yaml(real_dir / run_data.CONFIG_FILE)
    for r in real_payload["runs"]:
        m = run_data.run_source(metrics, config, r["key"])["metrics"]
        assert r["max_q"] == {
            "t": round(float(m["max_q_time_s"]), scene.TIME_DECIMALS),
            "q_pa": round(float(m["max_q_pa"]), scene.Q_DECIMALS),
        }, r["key"]
    bare = copy.deepcopy(metrics)
    for key in ("max_q_pa", "max_q_time_s"):
        bare["runs"]["pad"].pop(key, None)
    frame = run_data.read_series_frame(real_dir, "pad", scene.SCENE_COLUMNS, error=scene.SceneError)
    record = scene.run_payload(real_dir, "pad", frame, bare, config, str(metrics["baseline"]))
    assert record["max_q"] is None
