"""Interactive replay page of planar_2d runs (the ``launchsim replay`` command; I/O: reads
one results directory, writes one HTML file).

``write_replay_page`` reads a results directory (results/<experiment>/<timestamp>:
metrics.json, resolved_config.yaml, <run>/timeseries.csv, <run>/events.csv), never
writes inside results/, and writes a single self-contained HTML page: the trajectory
(altitude against downrange), a launch close-up with the silo shaft or track start
below ground, live telemetry, strip charts of speed, felt g and dynamic pressure, the
headline metrics against the baseline, and the caveats that apply to the selected
runs. The page replays the recorded time series; nothing is re-simulated in it.

``replay_data`` builds the embedded data set: per run the series resampled on a common
clock (the time after release: REPLAY_EARLY_DT_S steps up to REPLAY_EARLY_END_S, then
REPLAY_LATE_DT_S), q and Mach as JSON null where they are undefined (inside a vented
shaft, where no air drag is modelled), the events of events.csv and the headline
metrics of metrics.json, plus the text of the page (subtitle, run labels, notes,
caveats) generated from the run data. Run selection and the output-path rules are
those of ``launchsim animate`` (plots.animation_run_names: the baseline plus up to
three variants in summary order; at most plots.ANIMATION_MAX_RUNS runs; the default
output goes to the current directory, never into the results tree).

A selected run is an experiment run (metrics.json ``runs``, compared with the
baseline), a bound re-run or its paired baseline (``bounds``: compared with the paired
baseline, configured by resolved_config.yaml ``bound_runs``), a case (``cases``, its
own settings, compared with nothing) or a run of the offload block (``offload.runs``,
configured by ``offload_runs``: an offloaded run flying the reference payload, shown
beside the full-load pad, its saving reported in summary.md); ``run_source`` finds
which.

The page's template is package data (src/launchsim/templates/replay.html, shipped in
the wheel by uv_build); its single placeholder REPLAY_DATA_TOKEN is replaced by the
JSON, which must hold no NaN or Infinity (JavaScript's JSON.parse rejects them) and
has every "<" escaped so the data cannot close its <script> element or open an HTML
comment in it.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping, Sequence
from importlib import resources
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from launchsim import __version__, plots
from launchsim.config import PLANAR_2D, VERTICAL_1D
from launchsim.phases import HOLD_KIND
from launchsim.summary import UPPER_BOUND_REASONS
from launchsim.units import kg_to_t, m_to_km, pa_to_kpa, rad_to_deg, t_to_kg, to_percent


class ReplayError(ValueError):
    """A user-facing replay problem (a wrong run directory, run name or output path, a
    run without planar columns): the CLI prints it as one error line."""


REPLAY_TEMPLATE = ("templates", "replay.html")
"""Package-relative path of the page template (launchsim/templates/replay.html)."""
REPLAY_DATA_TOKEN = "__REPLAY_DATA__"
"""The template's placeholder for the embedded JSON."""
REPLAY_SUFFIXES = (".html", ".htm")
"""Output extensions ``write_replay_page`` accepts."""
REPLAY_EARLY_END_S = 40.0
"""End of the finely sampled launch segment [s after release]."""
REPLAY_EARLY_DT_S = 0.1
"""Sample step of the launch segment [s]."""
REPLAY_LATE_DT_S = 1.0
"""Sample step after REPLAY_EARLY_END_S [s]."""
REPLAY_GRID_DECIMALS = 6
"""Decimals [s] to which grid times are rounded before de-duplication, so a REPLAY_*_DT_S
step that lands on a run's first or last time does not give two samples."""
REPLAY_TIME_DECIMALS = 3
"""Decimals [s] of the sample and event times written into the page."""
YARDSTICK_SHOWN_KG = 0.5
"""|ideal screening - screening yardstick| [kg] above which the page shows the summary's
yardstick under the ideal screening (they differ when the yardstick basis is P0)."""
VERTICAL_TRACK_DEG = 90.0
"""Track angle [deg] of a vertical silo (assist.track.angle_deg)."""
TRACK_ANGLE_TOL_DEG = 1e-6
"""Tolerance [deg] on the vertical-track test."""
INSTANT_IGNITION_TOL_S = 1e-6
"""|t_ign| [s] below which a stage-1 ignition counts as at release."""
DRY_MASS_PARAM = "vehicle.stages.stage1.dry_mass_t"
"""Sensitivity parameter whose +/- cases give dP*/d(stage-1 dry mass)."""
INSERTED = "inserted"
"""metrics.json status of a run that reached the target orbit."""

ROLE_RUN = "run"
ROLE_BOUND = "bound"
ROLE_PAIRED_BASELINE = "paired_baseline"
ROLE_CASE = "case"
ROLE_OFFLOAD = "offload"
"""What a selected run is in metrics.json: an experiment run, a bound re-run, the
paired baseline of a bound re-run, a case, or a run of the offload block (an offload
case's recorded run, a paired pad or a pad control: ``offload.runs``; run_source)."""

REPLAY_COLUMNS = (
    *plots.ANIMATION_COLUMNS,
    "gamma_rel_rad",
    "mach",
)
"""timeseries.csv columns the replay reads (a planar_2d run writes all of them)."""


def wrapped_deg(angle_rad: np.ndarray) -> np.ndarray:
    """An angle [rad] wrapped to [-180, 180] deg: a falling vehicle's flight-path angle
    reads about -90 deg, not 270 deg (atan2 of its sine and cosine; NaN stays NaN)."""
    return np.asarray(rad_to_deg(np.arctan2(np.sin(angle_rad), np.cos(angle_rad))), dtype=float)


Converter = Callable[[np.ndarray], np.ndarray]
"""A unit conversion applied to a timeseries.csv column before resampling."""

SERIES_FIELDS: tuple[tuple[str, str, Converter | None, int], ...] = (
    ("alt_m", "alt_m", None, 1),
    ("x_km", "downrange_m", m_to_km, 3),
    ("v", "speed_rel_mps", None, 2),
    ("gamma_deg", "gamma_rel_rad", wrapped_deg, 2),
    ("m_t", "m_kg", kg_to_t, 3),
    ("g_ax", "felt_axial_g", None, 3),
    ("q_kpa", "q_pa", pa_to_kpa, 3),
    ("mach", "mach", None, 3),
)
"""(page field, timeseries.csv column, unit conversion or None, decimals) of each
resampled series; v is the Earth-relative speed and gamma the flight-path angle of the
Earth-relative velocity, wrapped to [-180, 180] deg before resampling."""

LOSS_KEYS = (
    "gravity_loss_mps",
    "drag_loss_mps",
    "steering_loss_mps",
    "back_pressure_loss_mps",
)
"""Loss integrals of metrics.json shown per run [m/s]."""

DEG = "\u00b0"
PLUS_MINUS = "\u00b1"


# ------------------------------------------------------------------ reading


def _read_json(path: Path) -> dict[str, Any]:
    """A JSON mapping read as UTF-8 (NaN literals allowed), or {} when missing."""
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, dict) else {}


def _read_yaml(path: Path) -> dict[str, Any]:
    """A YAML mapping read as UTF-8, or {} when missing."""
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


def check_replay_run_dir(run_dir: Path) -> dict[str, Any]:
    """metrics.json of a planar_2d results directory; raises ReplayError for a missing
    directory, one without metrics.json, a directory that is not an experiment's
    results directory (a sweep point's metrics.json has no ``runs``), or a run of
    another model (vertical_1d has no downrange or flight-path angle to replay).

    Not plots.check_planar_run_dir: that one raises AnimationError with animate's
    wording and cannot tell a sweep point from a vertical_1d run."""
    if not run_dir.is_dir():
        raise ReplayError(f"run directory not found: {run_dir}")
    metrics = _read_json(run_dir / "metrics.json")
    if not metrics:
        raise ReplayError(
            f"{run_dir} has no metrics.json; pass one results directory "
            "(results/<experiment>/<timestamp>)"
        )
    if not isinstance(metrics.get("runs"), dict):
        raise ReplayError(
            f"{run_dir} is not an experiment results directory (its metrics.json lists no "
            "runs: a sweep point or a single run's folder); pass "
            "results/<experiment>/<timestamp>"
        )
    model = metrics.get("model")
    if model != PLANAR_2D:
        shown = VERTICAL_1D if model is None else str(model)
        raise ReplayError(
            f"{run_dir} is a {shown} run; replay shows planar_2d runs only "
            "(a vertical_1d run has no downrange or flight-path angle to show)"
        )
    return metrics


def select_runs(run_dir: Path, runs: Sequence[str] | None) -> list[str]:
    """The run names to replay: ``runs`` as given, or the default of
    plots.animation_run_names (the baseline plus up to three variants, summary order).
    Raises ReplayError for unknown or repeated names, no runs, or more than
    plots.ANIMATION_MAX_RUNS."""
    default, available = plots.animation_run_names(run_dir)
    names = list(default if runs is None else runs)
    unknown = [n for n in names if n not in available]
    if unknown:
        raise ReplayError(
            f"unknown run(s) {', '.join(unknown)} in {run_dir}; available: {', '.join(available)}"
        )
    if len(set(names)) != len(names):
        raise ReplayError(f"a run is named twice: {', '.join(names)}")
    if not names:
        raise ReplayError(f"no runs with a timeseries.csv in {run_dir}")
    if len(names) > plots.ANIMATION_MAX_RUNS:
        raise ReplayError(
            f"{len(names)} runs requested; at most {plots.ANIMATION_MAX_RUNS} fit one replay"
        )
    return names


def _mapping(value: Any) -> dict[str, Any]:
    """``value`` when it is a mapping, else {}."""
    return value if isinstance(value, dict) else {}


def _entry_config(entry: Any) -> tuple[dict[str, Any], str | None]:
    """(run block, vehicle name or None) of one resolved_config.yaml run entry."""
    entry = _mapping(entry)
    return _mapping(entry.get("run")), _mapping(entry.get("vehicle")).get("name")


def overrides_text(overrides: Mapping[str, Any]) -> str:
    """' (with vehicle.aero.reference_area_m2 = 21.24)' for a bound's config overrides
    (YAML keys and units, as metrics.json records them), '' when there are none."""
    if not overrides:
        return ""
    items = [
        f"{key} = {value:g}" if isinstance(value, int | float) else f"{key} = {value}"
        for key, value in overrides.items()
    ]
    return f" (with {', '.join(items)})"


def run_source(metrics: dict[str, Any], config: dict[str, Any], name: str) -> dict[str, Any]:
    """Where run ``name`` lives in metrics.json and resolved_config.yaml: role (ROLE_RUN,
    ROLE_BOUND, ROLE_PAIRED_BASELINE, ROLE_CASE or ROLE_OFFLOAD), its metrics, its
    comparison, the run it is compared with (None: not compared), its run block, its
    vehicle name (None: the experiment's vehicle) and a note on what it is (for an
    offload run ``offload_note``). Raises ReplayError for a run folder that metrics.json
    does not describe."""
    baseline = metrics.get("baseline")
    if name in _mapping(metrics.get("runs")):
        run_cfg, vehicle = _entry_config(_mapping(config.get("runs")).get(name))
        return {
            "role": ROLE_RUN,
            "metrics": _mapping(metrics["runs"][name]),
            "comparison": {}
            if name == baseline
            else _mapping(_mapping(metrics.get("comparison")).get(name)),
            "compared_to": None if name == baseline else baseline,
            "config": run_cfg,
            "vehicle": vehicle,
            "note": "",
        }
    bound_cfgs = _mapping(config.get("bound_runs"))
    for bound in metrics.get("bounds") or []:
        bound = _mapping(bound)
        what = str(bound.get("bound", "bound"))
        override = overrides_text(_mapping(bound.get("overrides")))
        if bound.get("run") == name:
            run_cfg, vehicle = _entry_config(bound_cfgs.get(name))
            paired = bound.get("paired_baseline")
            return {
                "role": ROLE_BOUND,
                "metrics": _mapping(bound.get("metrics")),
                "comparison": _mapping(bound.get("comparison_vs_paired_baseline")),
                "compared_to": None if paired is None else str(paired),
                "config": run_cfg,
                "vehicle": vehicle,
                "note": f"{what} re-run of {bound.get('of')}{override}, compared with {paired}",
            }
        if bound.get("paired_baseline") == name:
            run_cfg, vehicle = _entry_config(bound_cfgs.get(name))
            return {
                "role": ROLE_PAIRED_BASELINE,
                "metrics": _mapping(bound.get("paired_baseline_metrics")),
                "comparison": {},
                "compared_to": None,
                "config": run_cfg,
                "vehicle": vehicle,
                "note": f"paired baseline of the {what} re-run {bound.get('run')}{override}",
            }
    if name in _mapping(metrics.get("cases")):
        run_cfg, vehicle = _entry_config(_mapping(config.get("cases")).get(name))
        return {
            "role": ROLE_CASE,
            "metrics": _mapping(metrics["cases"][name]),
            "comparison": {},
            "compared_to": None,
            "config": run_cfg,
            "vehicle": vehicle,
            "note": "case with its own settings, not compared with the baseline",
        }
    offload = _mapping(metrics.get("offload"))
    if name in _mapping(offload.get("runs")):
        run_cfg, vehicle = _entry_config(_mapping(config.get("offload_runs")).get(name))
        return {
            "role": ROLE_OFFLOAD,
            "metrics": _mapping(offload["runs"][name]),
            "comparison": {},
            "compared_to": None,
            "config": run_cfg,
            "vehicle": vehicle,
            "note": offload_note(offload, name, str(baseline)),
        }
    raise ReplayError(
        f"{name} has a timeseries.csv but metrics.json describes it nowhere (not in runs, "
        "bounds, cases or offload runs); replay shows the runs metrics.json records"
    )


def offload_note(offload: Mapping[str, Any], name: str, baseline: str) -> str:
    """What an offload run is, from metrics.json's ``offload`` record: an offload case's
    recorded run (how much propellant it carries less, in tonnes and as a share of the
    stage-1 and total loads, and the payload it flies against the reference payload), a
    paired pad (the pad with a case's propellant change) or a pad control."""
    p_ref = _finite(offload.get("reference_payload_kg"), 1)
    ref = f"{p_ref:,.1f} kg" if p_ref is not None else "the reference payload"
    for case in offload.get("cases") or []:
        case = _mapping(case)
        if case.get("run") == name:
            removed = _finite(case.get("total_offload_kg"))
            s1 = _finite(case.get("stage1_fraction"))
            tot = _finite(case.get("total_fraction"))
            how = "solved" if case.get("kind") == "solve" else "imposed"
            amount = (
                "an unknown amount of propellant"
                if removed is None
                else f"{float(kg_to_t(removed)):.1f} t less propellant ({how}"
                + (
                    ""
                    if s1 is None or tot is None
                    else f"; {float(to_percent(s1)):.1f}% of the stage-1 load, "
                    f"{float(to_percent(tot)):.1f}% of all"
                )
                + ")"
            )
            payload = _finite(case.get("payload_kg"), 1)
            flies = "" if payload is None else f", flying {payload:,.1f} kg"
            return (
                f"offload case {name} of {case.get('of')}: {amount}{flies} against "
                f"{baseline}'s full load at P_ref = {ref}, the same orbit"
            )
        paired = _mapping(case.get("paired_pad"))
        if paired.get("run") == name:
            return (
                f"paired pad of offload case {case.get('name')}: {baseline} with the same "
                "propellant change and no assist"
            )
    for control in offload.get("pad_controls") or []:
        control = _mapping(control)
        if control.get("run") == name:
            return f"pad control ({control.get('mode')}): {baseline}'s own offload at P_ref = {ref}"
    return "a run of the offload block"


def read_series(run_dir: Path, name: str) -> pd.DataFrame:
    """<run_dir>/<name>/timeseries.csv sorted on the time after release, one row per
    time (the last of duplicates, which phase boundaries write twice). Raises
    ReplayError for a series without REPLAY_COLUMNS or an empty one."""
    path = run_dir / name / "timeseries.csv"
    frame = pd.read_csv(path, encoding="utf-8")
    missing = [c for c in REPLAY_COLUMNS if c not in frame.columns]
    if missing:
        raise ReplayError(f"{path} lacks planar columns {missing}; not a planar_2d run")
    if frame.empty:
        raise ReplayError(f"{path} is empty (a failed search writes no trajectory)")
    frame = frame.sort_values("t_rel_release_s", kind="stable")
    return frame.drop_duplicates("t_rel_release_s", keep="last").reset_index(drop=True)


# ------------------------------------------------------------------ resampling


def _finite(value: Any, decimals: int | None = None) -> float | None:
    """``value`` as a float (rounded to ``decimals``, a negative zero made 0.0), or None
    when it is missing, not a number or not finite (JSON has no NaN)."""
    if isinstance(value, bool) or not isinstance(value, int | float | np.number):
        return None
    out = float(value)
    if not math.isfinite(out):
        return None
    return (out if decimals is None else round(out, decimals)) + 0.0  # -0.0 -> 0.0


def replay_grid(t0_s: float, t1_s: float) -> np.ndarray:
    """Common-clock sample times [s after release] of a run spanning t0_s..t1_s:
    t0_s, the REPLAY_EARLY_DT_S grid up to REPLAY_EARLY_END_S, the REPLAY_LATE_DT_S grid
    after it, and t1_s; sorted and unique."""
    first = math.ceil(t0_s / REPLAY_EARLY_DT_S) * REPLAY_EARLY_DT_S
    early = np.arange(first, min(REPLAY_EARLY_END_S, t1_s), REPLAY_EARLY_DT_S)
    late = np.arange(REPLAY_EARLY_END_S, t1_s, REPLAY_LATE_DT_S)
    grid = np.concatenate([[t0_s], early, late, [t1_s]])
    return np.unique(np.round(grid, REPLAY_GRID_DECIMALS))


def defined_mask(t_s: np.ndarray, values: np.ndarray, grid: np.ndarray) -> list[bool]:
    """Mask of the ``grid`` samples whose bracketing source samples of ``values`` (on
    ``t_s``) are both defined; a sample on a source time needs only that one."""
    defined = np.isfinite(values)
    j = np.clip(np.searchsorted(t_s, grid, side="right") - 1, 0, len(t_s) - 1)
    k = np.clip(j + 1, 0, len(t_s) - 1)
    bad = ~defined[j] | (~defined[k] & (grid > t_s[j]))
    return [not b for b in bad]


def series_values(
    t_s: np.ndarray, values: np.ndarray, grid: np.ndarray, decimals: int
) -> list[float | None]:
    """``values`` (on ``t_s``) linearly resampled on ``grid`` and rounded; None (JSON
    null) where a bracketing source value is undefined (q and Mach in a vented shaft)."""
    ok = defined_mask(t_s, values, grid)
    defined = np.isfinite(values)
    if not bool(defined.any()):
        return [None] * len(grid)
    y = np.interp(grid, t_s[defined], values[defined])
    return [
        round(float(v), decimals) + 0.0 if good else None for v, good in zip(y, ok, strict=True)
    ]


def run_series(frame: pd.DataFrame) -> dict[str, Any]:
    """The resampled series of one run: t [s after release], each SERIES_FIELDS field
    and the phase name per sample (the phase of the last row at or before it)."""
    t = frame["t_rel_release_s"].to_numpy(dtype=float)
    grid = replay_grid(float(t[0]), float(t[-1]))
    out: dict[str, Any] = {"t": [round(float(v), REPLAY_TIME_DECIMALS) for v in grid]}
    for field, column, convert, decimals in SERIES_FIELDS:
        raw = frame[column].to_numpy(dtype=float)
        values = raw if convert is None else np.asarray(convert(raw), dtype=float)
        out[field] = series_values(t, values, grid, decimals)
    idx = np.clip(np.searchsorted(t, grid, side="right") - 1, 0, len(t) - 1)
    out["phase"] = frame["phase"].astype(str).to_numpy()[idx].tolist()
    return out


def run_events(path: Path, offset_s: float) -> list[dict[str, Any]]:
    """Every event of events.csv: time after release (t_s - ``offset_s``) [s], name,
    stage, altitude [m], downrange [km] and Earth-relative speed [m/s]."""
    if not path.is_file():
        return []
    frame = pd.read_csv(path, encoding="utf-8")
    out = []
    for row in frame.to_dict("records"):
        downrange = _finite(row.get("downrange_m"))
        out.append(
            {
                "t": _finite(float(row["t_s"]) - offset_s, REPLAY_TIME_DECIMALS),
                "name": str(row["event"]),
                "stage": str(row.get("stage", "")),
                "alt_m": _finite(row.get("alt_m"), 1),
                "x_km": None if downrange is None else round(float(m_to_km(downrange)), 3),
                "v": _finite(row.get("speed_rel_mps"), 2),
            }
        )
    return out


# ------------------------------------------------------------------ run text


def run_assist(run_cfg: Mapping[str, Any]) -> dict[str, Any]:
    """The assist block of a run block of resolved_config.yaml ({} when absent)."""
    return _mapping(run_cfg.get("assist"))


def is_assisted(assist: dict[str, Any]) -> bool:
    """True for a run with a ground assist (assist model other than none)."""
    return str(assist.get("model", "none")) != "none"


def is_vertical(assist: dict[str, Any]) -> bool:
    """True when the assist track is a vertical silo (track angle 90 deg)."""
    angle = (assist.get("track") or {}).get("angle_deg")
    return angle is not None and abs(float(angle) - VERTICAL_TRACK_DEG) < TRACK_ANGLE_TOL_DEG


def startup_text(m: dict[str, Any]) -> str:
    """Stage-1 startup shape of a run's metrics: '2 s ramp', 'lag, tau 1 s', 'instant'."""
    kind = m.get("startup_kind_stage1")
    t = _finite(m.get("t_startup_s_stage1"))
    if kind == "ramp" and t is not None:
        return f"{t:g} s ramp"
    if kind == "lag" and t is not None:
        return f"lag, tau {t:g} s"
    if kind == "step":
        return "instant"
    return str(kind) if kind else "startup unknown"


def ignition_text(m: dict[str, Any], assisted: bool) -> str:
    """When and how stage 1 lights, relative to release, from a run's metrics."""
    t_ign = _finite(m.get("t_ign_rel_release_s_stage1"))
    shape = startup_text(m)
    if t_ign is None:
        return "stage 1 never lit"
    if abs(t_ign) < INSTANT_IGNITION_TOL_S:
        if m.get("startup_kind_stage1") == "step":
            return "instant full thrust at release (yardstick)"
        return f"stage 1 lit at release ({shape})"
    if t_ign > 0.0:
        return f"cold start: stage 1 lit T+{t_ign:.1f} s after release ({shape})"
    before = f"T\u2212{abs(t_ign):.1f} s before release"
    if not assisted:
        return f"stage 1 lit {before}, held down on the pad ({shape})"
    if _finite(m.get("hold_duration_s")) is None:
        return f"stage 1 lit on the track, {before} ({shape})"
    return f"stage 1 lit {before}, held at the start of the track ({shape})"


def push_accel_g(assist: Mapping[str, Any], m: Mapping[str, Any]) -> float | None:
    """The net acceleration of a run's push in g0, for labels: the run's ``net_accel_g``
    metric (metrics.json; written for every planar push whichever way its config
    states it, so a push defined by ``exit_speed_mps`` has it too), else the assist
    block's ``net_accel_g`` key (resolved_config.yaml; results written before the
    metric existed). None when neither holds a finite number."""
    accel = _finite(m.get("net_accel_g"))
    return _finite(assist.get("net_accel_g")) if accel is None else accel


def assist_text(assist: dict[str, Any], m: dict[str, Any]) -> str:
    """The ground start of a run: 'pad start' or the assist geometry, drive (the net
    acceleration of ``push_accel_g``), carriage mass and exhaust impingement fraction
    (when non-zero) and exit speed, from resolved_config.yaml and metrics.json."""
    if not is_assisted(assist):
        return "pad start"
    depth = _finite(m.get("track_start_altitude_m"))
    angle = _finite((assist.get("track") or {}).get("angle_deg"))
    if is_vertical(assist):
        where = "vertical silo"
    elif angle is not None:
        where = f"track at {angle:g}{DEG}"
    else:
        where = "track"
    if depth is not None and depth < 0.0:
        where += f" {abs(depth):.0f} m deep"
    model = str(assist.get("model"))
    drive = f"{model} drive"
    accel = push_accel_g(assist, m)
    if model == "constant_accel" and accel is not None:
        drive = f"{accel:g} g net push"
    parts = [where, drive]
    carriage = _finite(assist.get("carriage_mass_t"))
    if carriage is not None and carriage > 0.0:
        parts.append(f"{carriage:g} t carriage")
    impinged = _finite(assist.get("exhaust_impingement_fraction"))
    if impinged is not None and impinged > 0.0:
        parts.append(f"exhaust impingement fraction {impinged:g}")
    exit_v = _finite(m.get("exit_speed_mps"))
    if exit_v is not None:
        parts.append(f"exit {exit_v:.1f} m/s")
    return ", ".join(parts)


def is_yardstick(m: dict[str, Any]) -> bool:
    """True for a run whose stage 1 starts instantly (step startup): a yardstick, since
    no real engine reaches full thrust instantly; drawn dashed."""
    return m.get("startup_kind_stage1") == "step"


def orbit_text(run_cfg: Mapping[str, Any]) -> str:
    """The target orbit of a run block ('200 km circular orbit'), or 'target orbit'."""
    target = _mapping(_mapping(run_cfg.get("planar")).get("target_orbit"))
    alt = _finite(target.get("altitude_km"))
    if alt is None:
        return "target orbit"
    return f"{alt:g} km {target.get('kind', 'circular')} orbit"


def is_rotating(run_cfg: Mapping[str, Any]) -> bool:
    """True when a run block flies over a rotating Earth (site.include_rotation)."""
    return bool(_mapping(run_cfg.get("site")).get("include_rotation", True))


def earth_text(rotating: bool) -> str:
    """'rotating Earth' or 'non-rotating Earth'."""
    return "rotating Earth" if rotating else "non-rotating Earth"


def settings_text(source: Mapping[str, Any], base_cfg: Mapping[str, Any], vehicle: str) -> str:
    """How a run's own settings differ from the baseline's (target orbit, Earth
    rotation, vehicle), e.g. '185 km circular orbit, non-rotating Earth'; '' when none
    does."""
    run_cfg = source["config"]
    parts = []
    if orbit_text(run_cfg) != orbit_text(base_cfg):
        parts.append(orbit_text(run_cfg))
    if is_rotating(run_cfg) != is_rotating(base_cfg):
        parts.append(earth_text(is_rotating(run_cfg)))
    own = source["vehicle"]
    if own is not None and own != vehicle:
        parts.append(f"vehicle {own}")
    return ", ".join(parts)


def site_tags(base_cfg: Mapping[str, Any]) -> list[str]:
    """Tags of the page header from the baseline's run block: model, Earth, losses,
    guidance, throttling, orbit, site."""
    site = _mapping(base_cfg.get("site"))
    tags = [
        "planar 2-D",
        earth_text(is_rotating(base_cfg)),
        "drag and back-pressure",
        "sweep-optimized guidance",
        "unthrottled",
        orbit_text(base_cfg).removesuffix(" orbit"),
    ]
    lat, az = _finite(site.get("latitude_deg")), _finite(site.get("azimuth_deg"))
    if lat is not None and az is not None:
        tags.append(f"latitude {lat:g}{DEG}, azimuth {az:g}{DEG}")
    return tags


# ------------------------------------------------------------------ page text


def _names(names: Sequence[str]) -> str:
    """'a', 'a and b', 'a, b and c'."""
    items = list(names)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def dry_mass_slopes(metrics: dict[str, Any]) -> dict[str, tuple[float, float, float]]:
    """Per run with a + and a - DRY_MASS_PARAM sensitivity case: (dP*/d(stage-1 dry
    mass) [kg/kg] by central difference of the cases' absolute payload capacities, the
    - and + case fractions). The slope rests on those payloads alone, so how a case
    compares with the unperturbed baseline has no bearing on it."""
    cases: dict[str, dict[float, tuple[float, float]]] = {}
    for case in metrics.get("sensitivity") or []:
        case = _mapping(case)
        if case.get("param") != DRY_MASS_PARAM:
            continue
        value, payload = _finite(case.get("value_si")), _finite(case.get("payload_kg"))
        frac = _finite(case.get("fraction"))
        if value is None or payload is None or frac is None:
            continue
        cases.setdefault(str(case.get("of")), {})[frac] = (value, payload)
    out: dict[str, tuple[float, float, float]] = {}
    for name, pts in cases.items():
        hi, lo = max(pts), min(pts)
        if hi > 0.0 > lo and pts[hi][0] != pts[lo][0]:
            slope = (pts[hi][1] - pts[lo][1]) / (pts[hi][0] - pts[lo][0])
            out[name] = (slope, lo, hi)
    return out


def fraction_text(lo: float, hi: float) -> str:
    """'+/-10%' for symmetric case fractions (-0.1, 0.1), else '-5%/+10%'."""
    if math.isclose(-lo, hi):
        return f"{PLUS_MINUS}{100 * hi:g}%"
    return f"{100 * lo:+g}%/{100 * hi:+g}%"


def calibration_caveat(vehicle: str) -> str:
    """The calibration caveat of a vehicle from plots.CALIBRATION_RECORDS: its gap and
    whether it lies within the gate band (``plots.inside_calibration_band``) or outside
    it, a documented miss; or a note that it has no calibration record."""
    record = plots.CALIBRATION_RECORDS.get(vehicle)
    if record is None:
        return (
            f"Vehicle {vehicle} has no calibration record on file: read these numbers as "
            "differences between runs, not as absolute payloads."
        )
    model_kg, reference_kg, note = record
    gap = plots.calibration_gap(model_kg, reference_kg)
    side = "high" if gap >= 0.0 else "low"
    band_pct = 100 * plots.CALIBRATION_BAND
    band = (
        f"within the {PLUS_MINUS}{band_pct:.0f}% gate"
        if plots.inside_calibration_band(gap)
        else f"outside the {PLUS_MINUS}{band_pct:.0f}% gate, a documented miss"
    )
    return (
        f"The vehicle ({vehicle}) calibrates {100 * gap:+.1f}% {side}: its calibration "
        f"run carries {model_kg:,.0f} kg against the published {reference_kg:,.0f} kg, "
        f"{band} ({note}). Read these numbers as differences between runs."
    )


def structure_caveat(runs: Sequence[dict[str, Any]], metrics: dict[str, Any]) -> str | None:
    """The structural-mass caveat of the assisted runs: the peak felt g of the push and,
    when sensitivity cases give dP*/d(stage-1 dry mass), the extra stage-1 structure
    that would cancel each positive gain. Each run uses its own dry-mass cases; a run
    without them borrows the slope of the first selected assisted run that has them
    (else any run's) and the text says so. None without an assisted run."""
    assisted = [r for r in runs if r["assisted"]]
    if not assisted:
        return None
    peaks = [r["felt_g_track"] for r in assisted if r["felt_g_track"] is not None]
    text = "No structural mass is charged for the assist load case"
    if peaks:
        text += f": the fully fuelled stack feels up to {max(peaks):.1f} g during the push"
    text += "."
    slopes = {k: v for k, v in dry_mass_slopes(metrics).items() if v[0] < 0.0}
    gains = [r for r in assisted if (r["payload_delta_kg"] or 0.0) > 0.0]
    if not slopes or not gains:
        return text
    fallback = next((r["key"] for r in assisted if r["key"] in slopes), sorted(slopes)[0])
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in gains:
        groups.setdefault(r["key"] if r["key"] in slopes else fallback, []).append(r)
    kg_per_t = float(t_to_kg(1.0))
    pieces = []
    for src, members in groups.items():
        slope, lo, hi = slopes[src]
        tonnes = [
            f"{float(kg_to_t(r['payload_delta_kg'] / -slope)):.1f} t for {r['key']}"
            for r in members
        ]
        piece = (
            f"{_names(tonnes)} ({src}'s {fraction_text(lo, hi)} dry-mass cases: "
            f"{-slope * kg_per_t:.0f} kg of payload per tonne of stage-1 dry mass"
        )
        borrowed = [r["key"] for r in members if r["key"] != src]
        if borrowed:
            one = len(borrowed) == 1
            piece += (
                f", applied to {_names(borrowed)}, which {'has' if one else 'have'} no "
                f"such cases of {'its' if one else 'their'} own"
            )
        pieces.append(piece + ")")
    text += " Extra stage-1 structure of about " + "; ".join(pieces) + " would cancel the gain."
    return text


def drive_caveat(
    runs: Sequence[dict[str, Any]], sources: Mapping[str, Mapping[str, Any]]
) -> str | None:
    """What the assist model leaves out (prescribed push, massless carriage, vented
    shaft, kick without aerodynamic penalty), each naming its runs unless it applies to
    every assisted run; None without an assisted run. ``sources``: run_source per run
    (its metrics give the push's net acceleration, ``push_accel_g``)."""
    assisted = [r["key"] for r in runs if r["assisted"]]
    if not assisted:
        return None
    applies: dict[str, list[str]] = {}
    for name in assisted:
        assist = run_assist(sources[name]["config"])
        accel = push_accel_g(assist, sources[name]["metrics"])
        if assist.get("model") == "constant_accel" and accel is not None:
            part = f"the drive is a prescribed {accel:g} g push with no force or power limit"
            applies.setdefault(part, []).append(name)
        if _finite(assist.get("carriage_mass_t")) == 0.0:
            applies.setdefault("the carriage is massless", []).append(name)
        if assist.get("shaft") == "vented":
            applies.setdefault("the shaft has no air drag", []).append(name)
    parts = [
        part if names == assisted else f"{part} ({_names(names)})"
        for part, names in applies.items()
    ]
    parts.append("the pitch kick has no aerodynamic penalty")
    text = _names(parts)
    return text[0].upper() + text[1:] + ". Each of these favours the assisted runs."


def model_caveat(
    runs: Sequence[dict[str, Any]],
    sources: Mapping[str, Mapping[str, Any]],
    base_cfg: Mapping[str, Any],
) -> str:
    """The model sentence: planar point mass over the baseline's Earth (naming any
    selected run that flies over the other one), drag, back-pressure, guidance."""
    rotating = is_rotating(base_cfg)
    other = [r["key"] for r in runs if is_rotating(sources[r["key"]]["config"]) != rotating]
    earth = f"a {earth_text(rotating).replace('Earth', 'spherical Earth')}"
    if other:
        earth += f" ({earth_text(not rotating)} for {_names(other)})"
    return (
        f"Planar 2-D point-mass model over {earth}, with drag and back-pressure. Guidance "
        "is sweep-optimized, not optimal control, and the engines never throttle."
    )


def upper_bound_caveat(runs: Sequence[dict[str, Any]]) -> str | None:
    """The runs whose payload change is an unthrottled/unconstrained upper bound, with
    the flags metrics.json records for each (summary.UPPER_BOUND_REASONS words; runs
    with the same flags grouped); None when no selected run has one."""
    bound = [r for r in runs if r["upper_bound"]]
    if not bound:
        return None
    one = len(bound) == 1
    groups: dict[tuple[str, ...], list[str]] = {}
    for r in bound:
        groups.setdefault(tuple(r["upper_bound_reasons"]), []).append(r["key"])
    items = [
        f"{_names(names)} ({', '.join(reasons)})" if reasons else _names(names)
        for reasons, names in groups.items()
    ]
    return (
        f"The payload {'change' if one else 'changes'} of {'; '.join(items)} "
        f"{'is an upper bound' if one else 'are upper bounds'} (unthrottled and "
        "unconstrained): a max-Q or q-alpha limit, or the angle-of-attack aerodynamics "
        f"the model leaves out, would reduce {'it' if one else 'them'}."
    )


def comparison_caveats(runs: Sequence[dict[str, Any]], baseline: str) -> list[str]:
    """What bound re-runs and cases are compared with: a bound re-run with its paired
    baseline (same override), a paired baseline and a case with nothing; an offload run
    flies less propellant, its saving reported in summary.md, not on the page."""
    out = []
    bounds = [f"{r['key']} with {r['compared_to']}" for r in runs if r["role"] == ROLE_BOUND]
    if bounds:
        out.append(
            "Bound re-runs are compared with their paired baseline, which carries the same "
            f"override, not with {baseline}: {_names(bounds)}."
        )
    for role, one_text, many_text in (
        (ROLE_CASE, "is a case with its own settings", "are cases with their own settings"),
        (
            ROLE_PAIRED_BASELINE,
            "is the paired baseline of a bound re-run",
            "are paired baselines of bound re-runs",
        ),
    ):
        names = [r["key"] for r in runs if r["role"] == role]
        if names:
            what = one_text if len(names) == 1 else many_text
            out.append(
                f"{_names(names)} {what}, not compared with {baseline}: no payload change "
                "or screening estimate is shown."
            )
    offload = [r["key"] for r in runs if r["role"] == ROLE_OFFLOAD]
    if offload:
        one = len(offload) == 1
        out.append(
            f"{_names(offload)} {'is a run' if one else 'are runs'} of the offload block, not "
            f"compared with {baseline} here: what {'it measures' if one else 'they measure'} "
            "is propellant saved at the same payload and orbit, not a payload change "
            "(summary.md, 'Propellant saved at fixed payload', with its caveats)."
        )
    return out


def caveats(
    runs: Sequence[dict[str, Any]],
    metrics: dict[str, Any],
    sources: Mapping[str, Mapping[str, Any]],
    base_cfg: Mapping[str, Any],
    vehicle: str,
) -> list[str]:
    """The 'read before quoting' list for the selected runs, each item conditional on
    the runs, their vehicles and the experiment."""
    baseline = str(metrics.get("baseline"))
    vehicles = list(dict.fromkeys(sources[r["key"]]["vehicle"] or vehicle for r in runs))
    out = [model_caveat(runs, sources, base_cfg), *map(calibration_caveat, vehicles)]
    for item in (
        structure_caveat(runs, metrics),
        drive_caveat(runs, sources),
        upper_bound_caveat(runs),
    ):
        if item is not None:
            out.append(item)
    out += comparison_caveats(runs, baseline)
    yard = [r["key"] for r in runs if r["dashed"]]
    if yard:
        one = len(yard) == 1
        out.append(
            f"{_names(yard)} {'lights' if one else 'light'} stage 1 instantly (step "
            f"startup, drawn dashed): {'a yardstick' if one else 'yardsticks'}, not "
            f"{'a design' if one else 'designs'}, since no real engine reaches full "
            "thrust instantly."
        )
    for r in runs:
        if r["status"] != INSERTED:
            out.append(
                f"{r['key']} did not reach orbit (status {r['status']}): no payload "
                "capacity, payload change, screening estimate or loss budget."
            )
    return out


def closeup_notes(
    runs: Sequence[dict[str, Any]], sources: Mapping[str, Mapping[str, Any]]
) -> list[str]:
    """Sentences under the launch close-up: where each assisted group starts and how it
    leaves the track; how a held run is released; the vented shaft."""
    notes: list[str] = []
    groups: dict[tuple[Any, ...], list[str]] = {}
    for r in runs:
        if r["assisted"]:
            key = (r["start_alt_m"], r["exit_speed_mps"], r["push_s"], r["vertical"])
            groups.setdefault(key, []).append(r["key"])
    for (start, v_exit, push, vertical), names in groups.items():
        text = _names(names)
        if start is not None and start < 0.0:
            text += f" start{'s' if len(names) == 1 else ''} {abs(start):.0f} m below ground"
        else:
            text += f" start{'s' if len(names) == 1 else ''} at ground level"
        exit_at = "the silo mouth" if vertical else "the end of the track"
        if v_exit is not None and push is not None:
            text += f" and leave {exit_at} at {v_exit:.1f} m/s after {push:.1f} s"
        notes.append(text + ".")
    held = [r for r in runs if r["phase"] and r["phase"][0] == HOLD_KIND]
    on_pad = [r["key"] for r in held if not r["assisted"]]
    on_track = [r["key"] for r in held if r["assisted"]]
    if on_pad:
        notes.append(
            f"{_names(on_pad)} {'is' if len(on_pad) == 1 else 'are'} held down "
            "while the engines ramp up, then released at T+0."
        )
    if on_track:
        notes.append(
            f"{_names(on_track)} {'is' if len(on_track) == 1 else 'are'} held at the start "
            "of the track while the engines ramp up, then pushed."
        )
    vented = [
        r["key"]
        for r in runs
        if r["assisted"] and run_assist(sources[r["key"]]["config"]).get("shaft") == "vented"
    ]
    if vented:
        notes.append(
            "The shaft is treated as vented, so no air drag, dynamic pressure or Mach "
            "number is computed inside it."
        )
    return notes


def floors(runs: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Below-ground track starts drawn in the close-up: depth [m], label and whether it
    is a silo (vertical track), one per distinct depth (a silo floor or a track start;
    the first selected run at a depth names it). The page calls the ground line the
    silo mouth only when the deepest start is a silo."""
    out: dict[float, tuple[str, bool]] = {}
    for r in runs:
        start = r["start_alt_m"]
        if r["assisted"] and start is not None and start < 0.0:
            what = "silo floor" if r["vertical"] else "track start"
            out.setdefault(round(-start, 1), (f"{what}, {abs(start):.0f} m down", r["vertical"]))
    return [
        {"depth_m": d, "label": label, "vertical": vertical}
        for d, (label, vertical) in sorted(out.items())
    ]


def downrange_note(
    runs: Sequence[dict[str, Any]],
    sources: Mapping[str, Mapping[str, Any]],
    base_cfg: Mapping[str, Any],
) -> str:
    """The trajectory legend's sentence on downrange: the ground arc from the launch
    site over the Earth's surface (dynamics: R_datum (theta - omega_p t)), naming the
    Earth of the baseline and any selected run that flies over the other one."""
    rotating = is_rotating(base_cfg)
    other = [r["key"] for r in runs if is_rotating(sources[r["key"]]["config"]) != rotating]
    text = f"Downrange is the ground arc from the launch site over the {earth_text(rotating)}"
    if other:
        text += f" (the {earth_text(not rotating)} for {_names(other)})"
    return text + "."


# ------------------------------------------------------------------ data set


ROLE_LABELS = {
    ROLE_PAIRED_BASELINE: "paired baseline",
    ROLE_CASE: "case",
    ROLE_OFFLOAD: "offload",
}
"""Label suffix of a run by role (an experiment run or a bound re-run has none)."""


def run_label(name: str, role: str, baseline: bool) -> str:
    """The run's chip and table label: 'pad (baseline)', 'alt_185 (case)', 'silo'."""
    if baseline:
        return f"{name} (baseline)"
    suffix = ROLE_LABELS.get(role)
    return name if suffix is None else f"{name} ({suffix})"


def run_record(
    run_dir: Path,
    name: str,
    source: Mapping[str, Any],
    baseline_name: str,
    base_cfg: Mapping[str, Any],
    vehicle: str,
    index: int,
) -> dict[str, Any]:
    """The page record of one run: resampled series, events and headline metrics from
    its ``source`` (run_source). Changes against another run appear only for a run
    that is compared with one and reached orbit; losses only for a run that reached
    orbit (a run that fell back has no meaningful loss budget)."""
    frame = read_series(run_dir, name)
    offset_s = float(frame["t_s"].iloc[0]) - float(frame["t_rel_release_s"].iloc[0])
    m, comp = source["metrics"], source["comparison"]
    assist = run_assist(source["config"])
    assisted = is_assisted(assist)
    baseline = name == baseline_name
    status = str(m.get("status", "unknown"))
    inserted = status == INSERTED
    compared = inserted and source["compared_to"] is not None
    upper_bound = compared and comp.get("payload_delta_upper_bound") is True
    max_q = _finite(m.get("max_q_pa"))
    detail = [
        source["note"],
        settings_text(source, base_cfg, vehicle),
        assist_text(assist, m),
        ignition_text(m, assisted),
    ]
    record: dict[str, Any] = {
        "key": name,
        "label": run_label(name, source["role"], baseline),
        "detail": "; ".join(part for part in detail if part),
        "role": source["role"],
        "compared_to": source["compared_to"],
        "color": index,
        "dashed": is_yardstick(m),
        "baseline": baseline,
        "assisted": assisted,
        "vertical": is_vertical(assist),
        "status": status,
        "inserted": inserted,
        **run_series(frame),
        "events": run_events(run_dir / name / "events.csv", offset_s),
        "payload_kg": _finite(m.get("payload_kg"), 1),
        "payload_delta_kg": _finite(comp.get("payload_delta_kg"), 1) if compared else None,
        "ideal_screening_kg": _finite(
            comp.get("ideal_screening_payload_at_release_speed_at_pbase_kg"), 1
        )
        if compared
        else None,
        "screening_yardstick_kg": _finite(comp.get("screening_yardstick_kg"), 1)
        if compared
        else None,
        "upper_bound": upper_bound,
        "upper_bound_reasons": [w for k, w in UPPER_BOUND_REASONS if comp.get(k) is True]
        if upper_bound
        else [],
        "max_q_kpa": None if max_q is None else round(float(pa_to_kpa(max_q)), 2) + 0.0,
        "peak_g_flight": _finite(m.get("peak_felt_axial_g_flight"), 2),
        "losses_mps": {k: _finite(m.get(k), 1) if inserted else None for k in LOSS_KEYS},
        "exit_speed_mps": _finite(m.get("exit_speed_mps"), 2) if assisted else None,
        "felt_g_track": _finite(m.get("felt_g_track_peak"), 3) if assisted else None,
        "push_s": _finite(m.get("push_time_s"), 2) if assisted else None,
        "start_alt_m": _finite(m.get("track_start_altitude_m"), 1) if assisted else None,
    }
    if not assisted:
        record["pre_label"] = "Waiting on the pad"
    elif record["vertical"]:
        record["pre_label"] = "Waiting at the bottom of the shaft"
    else:
        record["pre_label"] = "Waiting at the start of the track"
    if record["phase"] and record["phase"][0] == HOLD_KIND:
        record["pre_label"] += ", engines not yet lit"
    record["end_label"] = (
        f"In orbit, {orbit_text(source['config'])}".removesuffix(" orbit")
        if inserted
        else f"Ended: {status}"
    )
    return record


def source_text(run_dir: Path) -> str:
    """The run directory as results/<experiment>/<timestamp> (POSIX), relative to the
    parent of its results tree."""
    resolved = run_dir.resolve()
    tree = plots._results_tree(run_dir)  # the animate command's results-tree rule
    try:
        return resolved.relative_to(tree.parent).as_posix()
    except ValueError:
        return resolved.as_posix()


def subtitle_text(
    experiment: str,
    vehicle: str,
    orbit: str,
    baseline: str,
    records: Sequence[dict[str, Any]],
    sources: Mapping[str, Mapping[str, Any]],
) -> str:
    """The page subtitle: experiment, vehicle and orbit (naming runs that fly another
    vehicle or aim elsewhere), run count, the assisted runs and the baseline."""
    other_vehicle = [
        r["key"] for r in records if (sources[r["key"]]["vehicle"] or vehicle) != vehicle
    ]
    elsewhere = [r["key"] for r in records if orbit_text(sources[r["key"]]["config"]) != orbit]
    text = f"Experiment {experiment}: the {vehicle} vehicle"
    if other_vehicle:
        text += f" (another vehicle for {_names(other_vehicle)})"
    text += f" flown to a {orbit}"
    if elsewhere:
        text += f" (another orbit for {_names(elsewhere)})"
    text += f" in {len(records)} run{'s' if len(records) != 1 else ''}"
    assisted = [r["key"] for r in records if r["assisted"]]
    if assisted:
        one = len(assisted) == 1
        text += f"; {_names(assisted)} {'starts' if one else 'start'} with a ground assist"
    return text + (
        ". Replay the simulated flights side by side, scrub to any moment, and compare "
        f"what each run carries to orbit against the baseline, {baseline}."
    )


def replay_data(run_dir: Path, runs: Sequence[str] | None) -> dict[str, Any]:
    """The page's data set for the selected runs of a planar results directory (see the
    module docstring); raises ReplayError for a wrong directory or run selection."""
    metrics = check_replay_run_dir(run_dir)
    names = select_runs(run_dir, runs)
    config = _read_yaml(run_dir / "resolved_config.yaml")
    sources = {n: run_source(metrics, config, n) for n in names}
    baseline = str(metrics.get("baseline"))
    base_cfg, _ = _entry_config(_mapping(config.get("runs")).get(baseline))
    vehicle = str(_mapping(config.get("vehicle")).get("name", "unknown vehicle"))
    records = [
        run_record(run_dir, n, sources[n], baseline, base_cfg, vehicle, k)
        for k, n in enumerate(names)
    ]
    orbit = orbit_text(base_cfg)
    experiment = str(metrics.get("experiment", run_dir.resolve().parent.name))
    git = _mapping(metrics.get("git"))
    results_notes = [
        "Payload capacity is the largest payload that still reaches the run's target orbit "
        "with zero propellant left, found by the simulator's search (sweep-optimized).",
        "Ideal screening is the rocket-equation estimate of the gain from the release "
        "speed alone, at the baseline's payload, holding every loss constant; the loss "
        "columns show where a gain beyond it comes from.",
    ]
    if any(
        r["screening_yardstick_kg"] is not None
        and r["ideal_screening_kg"] is not None
        and abs(r["screening_yardstick_kg"] - r["ideal_screening_kg"]) > YARDSTICK_SHOWN_KG
        for r in records
    ):
        results_notes.append(
            "summary.md flags a gain beyond screening against the stricter of two estimates, "
            "its screening yardstick, shown under the ideal screening where it differs."
        )
    if any(r["compared_to"] not in (None, baseline) for r in records):
        results_notes.append(f"Changes are against {baseline} unless the row names another run.")
    meta = {
        "experiment": experiment,
        "timestamp": str(metrics.get("timestamp_utc", run_dir.resolve().name)),
        "source": source_text(run_dir),
        "git": str(git.get("hash", "unknown")),
        "dirty": bool(git.get("dirty")),
        "version": __version__,
        "vehicle": vehicle,
        "baseline": baseline,
        "orbit": orbit,
        "subtitle": subtitle_text(experiment, vehicle, orbit, baseline, records, sources),
        "tags": site_tags(base_cfg),
        "closeup_notes": closeup_notes(records, sources),
        "results_notes": results_notes,
        "caveats": caveats(records, metrics, sources, base_cfg, vehicle),
        "floors": floors(records),
        "downrange_note": downrange_note(records, sources, base_cfg),
        "yardstick_shown_kg": YARDSTICK_SHOWN_KG,
    }
    return {"meta": meta, "runs": records}


# ------------------------------------------------------------------ page


def embed_json(data: dict[str, Any]) -> str:
    """``data`` as compact ASCII JSON safe inside a <script> element: no NaN or
    Infinity (ValueError otherwise) and every '<' escaped as the JSON escape \\u003c,
    so neither '</script>' nor '<!--' can appear in the data block."""
    text = json.dumps(data, separators=(",", ":"), allow_nan=False, ensure_ascii=True)
    return text.replace("<", "\\u003c")


def load_template() -> str:
    """The page template (package data launchsim/templates/replay.html)."""
    path = resources.files("launchsim").joinpath(*REPLAY_TEMPLATE)
    return path.read_text(encoding="utf-8")


def render_page(data: dict[str, Any]) -> str:
    """The HTML page with ``data`` embedded at REPLAY_DATA_TOKEN."""
    template = load_template()
    if template.count(REPLAY_DATA_TOKEN) != 1:
        raise RuntimeError(f"replay template must hold {REPLAY_DATA_TOKEN} exactly once")
    return template.replace(REPLAY_DATA_TOKEN, embed_json(data))


def results_ancestors(path: Path) -> list[Path]:
    """The resolved ancestors of ``path`` (inclusive) named plots.RESULTS_TREE_NAME,
    ignoring case, innermost first: every results tree ``path`` lies in, whichever run
    it belongs to."""
    resolved = path.resolve()
    name = plots.RESULTS_TREE_NAME.casefold()
    return [p for p in (resolved, *resolved.parents) if p.name.casefold() == name]


def protected_tree(path: Path, run_dir: Path) -> Path | None:
    """The outermost results tree holding ``path``: the run's own tree (the animate
    command's rule, plots._results_tree, which also covers a tree written with
    --results-root under another name) or any folder named plots.RESULTS_TREE_NAME;
    None when ``path`` lies in neither."""
    trees = results_ancestors(path)
    own = plots._results_tree(run_dir)
    if plots._is_inside(path, own):
        trees.append(own.resolve())
    return min(trees, key=lambda p: len(p.parts)) if trees else None


def default_replay_path(run_dir: Path, cwd: Path) -> Path:
    """<cwd>/<experiment>_<timestamp>_replay.html; when cwd is inside a results tree (the
    run's own or any folder named results) the file goes next to the outermost such
    tree instead (results/ is never hand-edited)."""
    metrics = _read_json(run_dir / "metrics.json")
    resolved = run_dir.resolve()
    experiment = str(metrics.get("experiment", resolved.parent.name))
    timestamp = str(metrics.get("timestamp_utc", resolved.name))
    name = plots.plot_stem(f"{experiment}_{timestamp}", "replay") + REPLAY_SUFFIXES[0]
    tree = protected_tree(cwd, run_dir)
    return (cwd if tree is None else tree.parent) / name


def check_replay_out(out_path: Path, run_dir: Path) -> None:
    """Raise ReplayError for an output that is not .html, lies inside a results tree
    (protected_tree: the run's own or any folder named results), or whose folder does
    not exist."""
    if out_path.suffix.lower() not in REPLAY_SUFFIXES:
        raise ReplayError(f"output {out_path} must end in .html")
    if protected_tree(out_path, run_dir) is not None:
        raise ReplayError(
            f"output {out_path} is inside the results tree; results/ is never edited by "
            "hand, so write the page elsewhere (--out)"
        )
    if not out_path.parent.is_dir():
        raise ReplayError(f"output folder does not exist: {out_path.parent}")


def write_replay_page(run_dir: Path, runs: Sequence[str] | None, out_path: Path) -> Path:
    """Write the replay page of the selected runs of ``run_dir`` to ``out_path`` (UTF-8)
    and return the path. Validates the directory, the runs and the output first."""
    data = replay_data(run_dir, runs)
    check_replay_out(out_path, run_dir)
    page = render_page(data)
    out_path.write_text(page, encoding="utf-8", newline="\n")
    return out_path
