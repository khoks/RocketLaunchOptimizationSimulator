"""Shared read-only access to a results directory (I/O: reads files, never writes one).

A results directory (results/<experiment>/<timestamp>) holds metrics.json,
resolved_config.yaml and one folder per run with timeseries.csv and events.csv. This
module is the one reader of those files for everything that shows a recorded run: the
animation (plots.py) and the replay page (replay.py); SP2's scene and local app are
meant to read through it too. It holds what those consumers share and nothing they draw:

- the lenient file readers (``read_json``, ``read_yaml``: a missing file or a
  non-mapping reads as {});
- the directory check, run discovery and run selection (``check_run_dir``,
  ``run_names``, ``select_runs``, ``run_identity``);
- where a run lives in metrics.json and resolved_config.yaml (``run_source``: an
  experiment run, a bound re-run, its paired baseline, a case or a run of the offload
  block; ``offload_role`` and ``offload_note`` for the last), its vehicle block and that
  block's masses (``run_vehicle_block``, ``vehicle_masses``);
- the time series (``read_series_frame`` as written, ``read_series`` sorted with one row
  per time) and the common-clock resampling of the replay page (``sample_grid``,
  ``defined_mask``, ``series_values``, ``run_series``);
- the events (``read_events``: every row of events.csv) and the mass before and after
  every drop (``with_drop_masses``, pure: the stage dropped at staging and the fairing
  in each of the four ways the planner logs it);
- the calibration records and the gate band (CALIBRATION_RECORDS and its helpers);
- the one output-path rule (``results_tree``, ``protected_tree``,
  ``default_output_path``, ``check_output`` and its three parts): nothing is ever
  written into a results tree by hand;
- the columns each dynamics model writes (MODEL_COLUMNS, keyed by model: planar_2d
  today, so a later spatial model adds one entry and reuses the readers).

Every function that can refuse its input raises the error class it is given
(``error=``, RunDataError by default) with the caller's own words where the wording
differs between commands, so plots.AnimationError and replay.ReplayError (both
RunDataError subclasses) keep their messages. SI units and radians throughout; times
are seconds, either on the run's own clock (t_s) or after release (t_rel_release_s).

Imports only units, config, metrics_planar (the column tuples and the FAIRING_* forms)
and phases.planar (phase and event names) from this package: never matplotlib, plots,
replay, results_io or summary, so a reader of run data does not load a drawing library.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from launchsim.config import PLANAR_2D, VERTICAL_1D, VehicleConfig
from launchsim.metrics_planar import (
    FAIRING_AT_IGNITION,
    FAIRING_AT_STAGING,
    FAIRING_IN_BURN,
    FAIRING_KEPT,
    PLANAR_EVENT_COLUMNS,
    PLANAR_TIMESERIES_COLUMNS,
)
from launchsim.phases.planar import COAST_STAGING, FAIRING_EVENT, LTG_BURN
from launchsim.units import kg_to_t, rad_to_deg, to_percent


class RunDataError(ValueError):
    """A user-facing problem with a results directory, a run selection, a run's files or
    an output path. plots.AnimationError and replay.ReplayError derive from it; the CLI
    prints each as one error line."""


# ------------------------------------------------------------------ names and constants

METRICS_FILE = "metrics.json"
"""The metrics file of a results directory."""
CONFIG_FILE = "resolved_config.yaml"
"""The resolved configuration of a results directory."""
SERIES_FILE = "timeseries.csv"
"""The time series of one run (<run_dir>/<run>/timeseries.csv)."""
EVENTS_FILE = "events.csv"
"""The events of one run (<run_dir>/<run>/events.csv)."""
RESULTS_TREE_NAME = "results"
"""Name of the generated results tree; nothing is written into it by hand."""
MAX_RUNS = 4
"""Most runs one animation or replay page shows."""
DEFAULT_VARIANTS = 3
"""The default selection: the baseline plus up to this many variants, in summary order."""
DEFAULT_WORDING = "this reader takes"
"""Subject and verb of a refusal when the caller gives none ('animate draws', 'replay
shows'): '<directory> is a vertical_1d run; this reader takes planar_2d runs only'."""
DEFAULT_SELECTION_NOUN = "view"
"""What a run selection is for when the caller gives no noun ('animation', 'replay')."""
DEFAULT_OUTPUT_NOUN = "file"
"""What an output path holds when the caller gives no noun ('animation', 'page')."""

ROLE_RUN = "run"
ROLE_BOUND = "bound"
ROLE_PAIRED_BASELINE = "paired_baseline"
ROLE_CASE = "case"
ROLE_OFFLOAD = "offload"
"""What a selected run is in metrics.json: an experiment run, a bound re-run, the
paired baseline of a bound re-run, a case, or a run of the offload block (an offload
case's recorded run, a paired pad or a pad control: ``offload.runs``; run_source)."""

OFFLOAD_CASE = "offload case"
OFFLOAD_PAIRED_PAD = "paired pad"
OFFLOAD_PAD_CONTROL = "pad control"
"""What a run of metrics.json's ``offload.runs`` is (``offload_role``): an offload case's
recorded run (``offload.cases``, by ``run``), the paired pad of a case (its
``paired_pad.run``: the reference baseline with the case's propellant change and no
assist) or a pad control (``offload.pad_controls``, by ``run``)."""
OFFLOAD_SOLVED_KIND = "solve"
"""``kind`` of an offload case whose offload was solved at P_ref, so it flies P_ref (a
``fixed`` case imposes its offload, and its figure is its own P* against P_ref)."""

CONFIG_RUN_SECTIONS = ("runs", "bound_runs", "cases", "offload_runs")
"""The sections of resolved_config.yaml that hold one entry per run folder (``run`` block
and, when it differs from the experiment's, ``vehicle`` block), in ``run_source`` order."""

STAGING_EVENT = "staging"
"""events.csv name of the staging map: the row holds the state after the map."""
IGNITION_EVENT = "ignition"
"""events.csv name of a stage's ignition; stage 2's row is logged in LTG_BURN."""
FAIRING_RULE_STAGING = "staging"
"""Trigger of the vehicle's fairing rule that drops the fairing in the staging map
without a ``fairing`` row (config.VehicleConfig's default when the key is absent)."""
TWO_STAGES = 2
"""Fewest stages of a vehicle whose fairing has a drop form: metrics_planar reports none
for a single stage (``fairing_items``)."""
EVENT_REQUIRED_COLUMNS = ("t_s", "event")
"""The columns ``read_events`` needs; every other column is optional."""

PLANAR_BASE_COLUMNS = (
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
"""timeseries.csv columns every reader of a planar_2d run needs (a planar_2d run writes
all of them): the animation reads exactly these (plots.ANIMATION_COLUMNS is this tuple)
and the replay page two more."""

GRID_EARLY_END_S = 40.0
"""End of the finely sampled launch segment of ``sample_grid`` [s after release]."""
GRID_EARLY_DT_S = 0.1
"""Sample step of the launch segment [s]."""
GRID_LATE_DT_S = 1.0
"""Sample step after GRID_EARLY_END_S [s]."""
GRID_DECIMALS = 6
"""Decimals [s] to which grid times are rounded before de-duplication, so a GRID_*_DT_S
step that lands on a run's first or last time does not give two samples."""
TIME_DECIMALS = 3
"""Decimals [s] of the sample times ``run_series`` returns (and of the replay page's
event times)."""

type Converter = Callable[[np.ndarray], np.ndarray]
"""A unit conversion applied to a timeseries.csv column before resampling."""
type SeriesField = tuple[str, str, Converter | None, int]
"""(output field, timeseries.csv column, unit conversion or None, decimals) of one
resampled series of ``run_series``."""


@dataclass(frozen=True)
class ModelColumns:
    """The columns a dynamics model writes: ``series``, every column of its
    timeseries.csv; ``events``, every column of its events.csv; ``base``, the
    time-series columns every reader of the model needs (a subset of ``series``);
    ``label``, the word for the model's columns in a refusal ('planar' for planar_2d:
    '<path> lacks planar columns [...]; not a planar_2d run', ``read_series_frame``)."""

    series: tuple[str, ...]
    events: tuple[str, ...]
    base: tuple[str, ...]
    label: str


PLANAR_LABEL = "planar"
"""The word for planar_2d's columns in a refusal (MODEL_COLUMNS[PLANAR_2D].label)."""

MODEL_COLUMNS: dict[str, ModelColumns] = {
    PLANAR_2D: ModelColumns(
        series=PLANAR_TIMESERIES_COLUMNS,
        events=PLANAR_EVENT_COLUMNS,
        base=PLANAR_BASE_COLUMNS,
        label=PLANAR_LABEL,
    ),
}
"""Column sets per dynamics model (metrics.json ``model``). A spatial model that writes a
superset of the planar names (D-SP1-01) adds one entry here; the readers take the columns
they are asked for and ignore the rest, so the planar consumers read such a run as it is."""


# ------------------------------------------------------------------ small helpers


def as_mapping(value: Any) -> dict[str, Any]:
    """``value`` when it is a mapping (a dict), else {}."""
    return value if isinstance(value, dict) else {}


def finite(value: Any, decimals: int | None = None) -> float | None:
    """``value`` as a float (rounded to ``decimals`` when given, a negative zero made
    0.0), or None when it is missing, a bool, not a number (int, float or numpy number)
    or not finite (JSON has no NaN). Unit: that of ``value``."""
    if isinstance(value, bool) or not isinstance(value, int | float | np.number):
        return None
    out = float(value)
    if not math.isfinite(out):
        return None
    return (out if decimals is None else round(out, decimals)) + 0.0  # -0.0 -> 0.0


def wrapped_deg(angle_rad: np.ndarray) -> np.ndarray:
    """An angle [rad] wrapped to [-180, 180] deg: a falling vehicle's flight-path angle
    reads about -90 deg, not 270 deg (atan2 of its sine and cosine; NaN stays NaN)."""
    return np.asarray(rad_to_deg(np.arctan2(np.sin(angle_rad), np.cos(angle_rad))), dtype=float)


PLOT_STEM_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")
"""Runs of characters a file stem may not hold (``plot_stem`` replaces each by '_')."""


def plot_stem(prefix: str, quantity: str) -> str:
    """File stem ``<prefix>_<quantity>`` with every run of characters outside
    ``[A-Za-z0-9_.-]`` replaced by ``_`` (a name such as ``F/N`` becomes ``F_N``)."""
    return PLOT_STEM_UNSAFE.sub("_", f"{prefix}_{quantity}")


def _one_line(exc: BaseException) -> str:
    """The text of an exception on one line (parser errors span several)."""
    return " ".join(str(exc).split())


# ------------------------------------------------------------------ files


def read_json(path: Path, *, error: type[RunDataError] | None = None) -> dict[str, Any]:
    """The JSON mapping in ``path``, read as UTF-8 (NaN and Infinity literals allowed,
    as the simulator may write them); {} when the file is missing or its top level is
    not a mapping. With ``error`` None (the default) a file that cannot be read, decoded
    or parsed raises what the standard library raises (OSError, UnicodeDecodeError,
    json.JSONDecodeError), as before SP2; with an error class it raises that class with a
    one-line message instead (for a caller that lists directories a job may still be
    writing)."""
    if not path.is_file():
        return {}
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:  # JSONDecodeError and UnicodeDecodeError: ValueError
        if error is None:
            raise
        raise error(f"cannot read {path}: {_one_line(exc)}") from exc
    return data if isinstance(data, dict) else {}


def read_yaml(path: Path, *, error: type[RunDataError] | None = None) -> dict[str, Any]:
    """The YAML mapping in ``path``, read as UTF-8; {} when the file is missing or its
    top level is not a mapping. With ``error`` None (the default) a file that cannot be
    read, decoded or parsed raises what the libraries raise (OSError, UnicodeDecodeError,
    yaml.YAMLError), as before SP2; with an error class it raises that class with a
    one-line message instead."""
    if not path.is_file():
        return {}
    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        if error is None:
            raise
        raise error(f"cannot read {path}: {_one_line(exc)}") from exc
    return data if isinstance(data, dict) else {}


# ------------------------------------------------------------------ directory and selection


def check_run_dir(
    run_dir: Path,
    *,
    models: tuple[str, ...] = (PLANAR_2D,),
    error: type[RunDataError] = RunDataError,
    wording: str = DEFAULT_WORDING,
) -> dict[str, Any]:
    """metrics.json of an experiment's results directory whose dynamics model is one of
    ``models`` (a tuple of model names; a bare string raises TypeError, since ``in`` on a
    string matches substrings: a model named '2d' would pass ``models='planar_2d'``). Raises
    ``error`` for a missing directory, one without metrics.json, a directory that is not
    an experiment's results directory (its metrics.json has no ``runs`` mapping: a sweep
    point or a single run's folder), or a run of another model (a metrics.json without
    ``model`` is a vertical_1d one, which has no downrange or flight-path angle).
    ``wording`` is the caller's subject and verb in the last message ('animate draws',
    'replay shows')."""
    if isinstance(models, str):
        raise TypeError(
            f"models must be a tuple of model names, not the string {models!r}; pass ({models!r},)"
        )
    if not run_dir.is_dir():
        raise error(f"run directory not found: {run_dir}")
    metrics = read_json(run_dir / METRICS_FILE)
    if not metrics:
        raise error(
            f"{run_dir} has no metrics.json; pass one results directory "
            "(results/<experiment>/<timestamp>)"
        )
    if not isinstance(metrics.get("runs"), dict):
        raise error(
            f"{run_dir} is not an experiment results directory (its metrics.json lists no "
            "runs: a sweep point or a single run's folder); pass "
            "results/<experiment>/<timestamp>"
        )
    model = metrics.get("model")
    if model not in models:
        shown = VERTICAL_1D if model is None else str(model)
        raise error(
            f"{run_dir} is a {shown} run; {wording} {' or '.join(models)} runs only "
            "(a vertical_1d run has no downrange or flight-path angle to show)"
        )
    return metrics


def run_names(run_dir: Path) -> tuple[list[str], list[str]]:
    """(default selection, every run with a time series) of a results directory. A run
    is a subdirectory holding timeseries.csv; metrics.json's run order (the summary
    order) comes first, other run folders (bound re-runs, cases, runs of the offload
    block) follow, sorted. The default is the baseline plus up to DEFAULT_VARIANTS
    variants, in summary order."""
    metrics = read_json(run_dir / METRICS_FILE)
    have = {p.name for p in run_dir.iterdir() if (p / SERIES_FILE).is_file()}
    ordered = [name for name in metrics.get("runs", {}) if name in have]
    available = ordered + sorted(have - set(ordered))
    baseline = metrics.get("baseline")
    head = [baseline] if baseline in ordered else []
    variants = [name for name in ordered if name != baseline]
    default = head + variants[:DEFAULT_VARIANTS]
    return (default or available[: DEFAULT_VARIANTS + 1]), available


def select_runs(
    run_dir: Path,
    runs: Sequence[str] | None,
    *,
    what: str = DEFAULT_SELECTION_NOUN,
    max_runs: int = MAX_RUNS,
    error: type[RunDataError] = RunDataError,
) -> list[str]:
    """The run names to show: ``runs`` as given, or the default of ``run_names`` when it
    is None. Raises ``error``, in this order, for unknown names, a repeated name, no
    runs, or more than ``max_runs`` names (``what`` names the thing they must fit: 'at
    most 4 fit one animation')."""
    default, available = run_names(run_dir)
    names = list(default if runs is None else runs)
    unknown = [n for n in names if n not in available]
    if unknown:
        raise error(
            f"unknown run(s) {', '.join(unknown)} in {run_dir}; available: {', '.join(available)}"
        )
    if len(set(names)) != len(names):
        raise error(f"a run is named twice: {', '.join(names)}")
    if not names:
        raise error(f"no runs with a timeseries.csv in {run_dir}")
    if len(names) > max_runs:
        raise error(f"{len(names)} runs requested; at most {max_runs} fit one {what}")
    return names


def run_identity(run_dir: Path) -> tuple[str, str]:
    """(experiment name, UTC timestamp) of a results directory: metrics.json's
    ``experiment`` and ``timestamp_utc``, else the names of the directory's parent and
    of the directory itself (results/<experiment>/<timestamp>)."""
    metrics = read_json(run_dir / METRICS_FILE)
    resolved = run_dir.resolve()
    experiment = str(metrics.get("experiment", resolved.parent.name))
    timestamp = str(metrics.get("timestamp_utc", resolved.name))
    return experiment, timestamp


def model_columns(model: str, *, error: type[RunDataError] = RunDataError) -> ModelColumns:
    """The ModelColumns of dynamics model ``model`` (MODEL_COLUMNS); raises ``error``
    naming the known models for any other."""
    columns = MODEL_COLUMNS.get(model)
    if columns is None:
        raise error(f"no column set for model {model!r}; known: {', '.join(MODEL_COLUMNS)}")
    return columns


def model_label(model: str) -> str:
    """The word for the columns of dynamics model ``model`` in a refusal: its
    ModelColumns ``label`` ('planar' for planar_2d), or the model name itself for a
    model without an entry in MODEL_COLUMNS."""
    columns = MODEL_COLUMNS.get(model)
    return model if columns is None else columns.label


# ------------------------------------------------------------------ roles and configuration


def entry_config(entry: Any) -> tuple[dict[str, Any], str | None]:
    """(run block, vehicle name or None) of one resolved_config.yaml run entry."""
    entry = as_mapping(entry)
    return as_mapping(entry.get("run")), as_mapping(entry.get("vehicle")).get("name")


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


def run_source(
    metrics: dict[str, Any],
    config: dict[str, Any],
    name: str,
    *,
    error: type[RunDataError] = RunDataError,
    wording: str = DEFAULT_WORDING,
) -> dict[str, Any]:
    """Where run ``name`` lives in metrics.json (``metrics``) and resolved_config.yaml
    (``config``): ``role`` (ROLE_RUN, ROLE_BOUND, ROLE_PAIRED_BASELINE, ROLE_CASE or
    ROLE_OFFLOAD), its ``metrics``, its ``comparison``, the run it is ``compared_to``
    (None: not compared), its run block ``config``, its ``vehicle`` name (None: the
    experiment's vehicle) and a ``note`` on what it is (for an offload run
    ``offload_note``). The sections are searched in that order: ``runs``, ``bounds``
    (config ``bound_runs``), ``cases``, ``offload.runs`` (config ``offload_runs``). Raises
    ``error`` for a run folder that metrics.json does not describe (``wording``: the
    caller's subject and verb, 'replay shows')."""
    baseline = metrics.get("baseline")
    if name in as_mapping(metrics.get("runs")):
        run_cfg, vehicle = entry_config(as_mapping(config.get("runs")).get(name))
        return {
            "role": ROLE_RUN,
            "metrics": as_mapping(metrics["runs"][name]),
            "comparison": {}
            if name == baseline
            else as_mapping(as_mapping(metrics.get("comparison")).get(name)),
            "compared_to": None if name == baseline else baseline,
            "config": run_cfg,
            "vehicle": vehicle,
            "note": "",
        }
    bound_cfgs = as_mapping(config.get("bound_runs"))
    for bound in metrics.get("bounds") or []:
        bound = as_mapping(bound)
        what = str(bound.get("bound", "bound"))
        override = overrides_text(as_mapping(bound.get("overrides")))
        if bound.get("run") == name:
            run_cfg, vehicle = entry_config(bound_cfgs.get(name))
            paired = bound.get("paired_baseline")
            return {
                "role": ROLE_BOUND,
                "metrics": as_mapping(bound.get("metrics")),
                "comparison": as_mapping(bound.get("comparison_vs_paired_baseline")),
                "compared_to": None if paired is None else str(paired),
                "config": run_cfg,
                "vehicle": vehicle,
                "note": f"{what} re-run of {bound.get('of')}{override}, compared with {paired}",
            }
        if bound.get("paired_baseline") == name:
            run_cfg, vehicle = entry_config(bound_cfgs.get(name))
            return {
                "role": ROLE_PAIRED_BASELINE,
                "metrics": as_mapping(bound.get("paired_baseline_metrics")),
                "comparison": {},
                "compared_to": None,
                "config": run_cfg,
                "vehicle": vehicle,
                "note": f"paired baseline of the {what} re-run {bound.get('run')}{override}",
            }
    if name in as_mapping(metrics.get("cases")):
        run_cfg, vehicle = entry_config(as_mapping(config.get("cases")).get(name))
        return {
            "role": ROLE_CASE,
            "metrics": as_mapping(metrics["cases"][name]),
            "comparison": {},
            "compared_to": None,
            "config": run_cfg,
            "vehicle": vehicle,
            "note": "case with its own settings, not compared with the baseline",
        }
    offload = as_mapping(metrics.get("offload"))
    if name in as_mapping(offload.get("runs")):
        run_cfg, vehicle = entry_config(as_mapping(config.get("offload_runs")).get(name))
        return {
            "role": ROLE_OFFLOAD,
            "metrics": as_mapping(offload["runs"][name]),
            "comparison": {},
            "compared_to": None,
            "config": run_cfg,
            "vehicle": vehicle,
            "note": offload_note(offload, name, str(baseline)),
        }
    raise error(
        f"{name} has a timeseries.csv but metrics.json describes it nowhere (not in runs, "
        f"bounds, cases or offload runs); {wording} the runs metrics.json records"
    )


def offload_role(offload: Mapping[str, Any], name: str) -> tuple[str, dict[str, Any]] | None:
    """(kind, record) of run ``name`` in metrics.json's ``offload`` block: OFFLOAD_CASE
    and the case record whose ``run`` it is; OFFLOAD_PAIRED_PAD and the case record whose
    ``paired_pad.run`` it is; OFFLOAD_PAD_CONTROL and its ``pad_controls`` record; None
    when the block names it in no case or control. Shared by the animation's legend
    (plots.offload_tag) and the replay page's note (``offload_note``)."""
    for case in offload.get("cases") or []:
        case = as_mapping(case)
        if case.get("run") == name:
            return OFFLOAD_CASE, case
        if as_mapping(case.get("paired_pad")).get("run") == name:
            return OFFLOAD_PAIRED_PAD, case
    for control in offload.get("pad_controls") or []:
        control = as_mapping(control)
        if control.get("run") == name:
            return OFFLOAD_PAD_CONTROL, control
    return None


def offload_note(offload: Mapping[str, Any], name: str, baseline: str) -> str:
    """What an offload run is, from metrics.json's ``offload`` record: an offload case's
    recorded run (how much propellant it carries less, in tonnes and as a share of the
    stage-1 and total loads, and the payload [kg] it flies against the reference
    payload), a paired pad (the pad with a case's propellant change) or a pad control.
    Which one is ``offload_role``, shared with the animation's labels."""
    p_ref = finite(offload.get("reference_payload_kg"), 1)
    ref = f"{p_ref:,.1f} kg" if p_ref is not None else "the reference payload"
    role = offload_role(offload, name)
    if role is None:
        return "a run of the offload block"
    kind, record = role
    if kind == OFFLOAD_PAIRED_PAD:
        return (
            f"paired pad of offload case {record.get('name')}: {baseline} with the same "
            "propellant change and no assist"
        )
    if kind == OFFLOAD_PAD_CONTROL:
        return f"pad control ({record.get('mode')}): {baseline}'s own offload at P_ref = {ref}"
    removed = finite(record.get("total_offload_kg"))
    s1 = finite(record.get("stage1_fraction"))
    tot = finite(record.get("total_fraction"))
    how = "solved" if record.get("kind") == OFFLOAD_SOLVED_KIND else "imposed"
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
    payload = finite(record.get("payload_kg"), 1)
    flies = "" if payload is None else f", flying {payload:,.1f} kg"
    return (
        f"offload case {name} of {record.get('of')}: {amount}{flies} against "
        f"{baseline}'s full load at P_ref = {ref}, the same orbit"
    )


def run_vehicle_block(config: Mapping[str, Any], name: str) -> dict[str, Any]:
    """The vehicle block run ``name`` flew, from resolved_config.yaml (``config``): the
    ``vehicle`` block of the run's own entry (under ``runs``, ``bound_runs``, ``cases``
    or ``offload_runs``; written only when it differs from the experiment's, e.g. an
    offloaded load or a dry-mass penalty), else the experiment's top-level ``vehicle``
    block; {} when the file has neither. The block is the raw vehicle file (tonnes,
    ``value`` leaves): ``vehicle_masses`` converts it."""
    for section in CONFIG_RUN_SECTIONS:
        entry = as_mapping(as_mapping(config.get(section)).get(name))
        own = as_mapping(entry.get("vehicle"))
        if own:
            return own
    return as_mapping(config.get("vehicle"))


@dataclass(frozen=True)
class VehicleMasses:
    """The masses of one vehicle block, SI: per stage in firing order its name, dry
    mass [kg] and propellant load [kg]; the fairing mass [kg]; the block's payload [kg]
    (a run may fly another: its metrics record's ``payload_kg``); and the trigger of the
    fairing rule ('staging', 'never' or 'free_molecular_heating')."""

    stage_names: tuple[str, ...]
    stage_dry_kg: tuple[float, ...]
    stage_propellant_kg: tuple[float, ...]
    fairing_kg: float
    payload_kg: float
    fairing_trigger: str


def vehicle_masses(
    block: Mapping[str, Any], *, error: type[RunDataError] = RunDataError
) -> VehicleMasses:
    """The VehicleMasses of a raw vehicle block (``run_vehicle_block``), through the
    vehicle file's own schema: ``config.VehicleConfig.model_validate(block).to_vehicle()``
    converts tonnes to kilograms (units.py) and applies the schema's defaults, so a
    block without a ``fairing_drop`` key has the rule config.py gives it (staging), not
    'no rule'. Raises ``error`` (one line) for a block that does not validate, e.g. a
    block holding only a name."""
    try:
        vehicle = VehicleConfig.model_validate(dict(block)).to_vehicle()
    except ValueError as exc:  # pydantic's ValidationError is a ValueError
        raise error(
            f"vehicle block {block.get('name')!r} is not a complete vehicle file: {_one_line(exc)}"
        ) from exc
    return VehicleMasses(
        stage_names=tuple(vehicle.stage_names),
        stage_dry_kg=tuple(float(s.dry_mass_kg) for s in vehicle.stages),
        stage_propellant_kg=tuple(float(s.propellant_mass_kg) for s in vehicle.stages),
        fairing_kg=float(vehicle.fairing_mass_kg),
        payload_kg=float(vehicle.payload_mass_kg),
        fairing_trigger=str(vehicle.fairing_rule.trigger),
    )


# ------------------------------------------------------------------ time series


def read_series_frame(
    run_dir: Path,
    name: str,
    columns: Sequence[str],
    *,
    model: str = PLANAR_2D,
    error: type[RunDataError] = RunDataError,
) -> pd.DataFrame:
    """<run_dir>/<name>/timeseries.csv as written: rows in file order, both rows of a
    phase boundary kept (the animation's read). ``columns`` are the columns the caller
    needs; other columns in the file are kept and ignored. Raises ``error`` for a series
    without one of ``columns`` or an empty one (a failed search writes no trajectory).
    ``model`` is the dynamics model whose runs write ``columns``; it words the first
    refusal ('<path> lacks planar columns [...]; not a planar_2d run' for the default,
    ``model_label`` for the adjective). SI columns, as the model wrote them."""
    path = run_dir / name / SERIES_FILE
    frame = pd.read_csv(path, encoding="utf-8")
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise error(f"{path} lacks {model_label(model)} columns {missing}; not a {model} run")
    if frame.empty:
        raise error(f"{path} is empty (a failed search writes no trajectory)")
    return frame


def read_series(
    run_dir: Path,
    name: str,
    columns: Sequence[str],
    *,
    model: str = PLANAR_2D,
    error: type[RunDataError] = RunDataError,
) -> pd.DataFrame:
    """``read_series_frame`` sorted on the time after release (stable), with one row per
    time: the last of duplicates, which phase boundaries write twice (the state after a
    map). The replay page's read; ``columns`` must include t_rel_release_s. Raises
    ``error`` as ``read_series_frame`` does (``model`` words the refusal as there)."""
    frame = read_series_frame(run_dir, name, columns, model=model, error=error)
    frame = frame.sort_values("t_rel_release_s", kind="stable")
    return frame.drop_duplicates("t_rel_release_s", keep="last").reset_index(drop=True)


def release_offset_s(frame: pd.DataFrame) -> float:
    """t_s - t_rel_release_s of the first row of a time series [s]: the release time on
    the run's own clock, subtracted from an event's t_s to get its time after release."""
    return float(frame["t_s"].iloc[0]) - float(frame["t_rel_release_s"].iloc[0])


def sample_grid(t0_s: float, t1_s: float) -> np.ndarray:
    """Common-clock sample times [s after release] of a run spanning t0_s..t1_s: t0_s,
    the GRID_EARLY_DT_S grid up to GRID_EARLY_END_S, the GRID_LATE_DT_S grid after it,
    and t1_s; sorted and unique (the replay page's clock)."""
    first = math.ceil(t0_s / GRID_EARLY_DT_S) * GRID_EARLY_DT_S
    early = np.arange(first, min(GRID_EARLY_END_S, t1_s), GRID_EARLY_DT_S)
    late = np.arange(GRID_EARLY_END_S, t1_s, GRID_LATE_DT_S)
    grid = np.concatenate([[t0_s], early, late, [t1_s]])
    return np.unique(np.round(grid, GRID_DECIMALS))


def defined_mask(t_s: np.ndarray, values: np.ndarray, grid: np.ndarray) -> list[bool]:
    """Mask of the ``grid`` samples whose bracketing source samples of ``values`` (on
    ``t_s``, increasing) are both defined; a sample on a source time needs only that
    one. ``t_s`` and ``grid`` in the same time unit."""
    defined = np.isfinite(values)
    j = np.clip(np.searchsorted(t_s, grid, side="right") - 1, 0, len(t_s) - 1)
    k = np.clip(j + 1, 0, len(t_s) - 1)
    bad = ~defined[j] | (~defined[k] & (grid > t_s[j]))
    return [not b for b in bad]


def series_values(
    t_s: np.ndarray, values: np.ndarray, grid: np.ndarray, decimals: int
) -> list[float | None]:
    """``values`` (on ``t_s``, increasing) linearly resampled on ``grid`` and rounded to
    ``decimals``; None (JSON null) where a bracketing source value is undefined (q and
    Mach in a vented shaft). The unit is that of ``values``."""
    ok = defined_mask(t_s, values, grid)
    defined = np.isfinite(values)
    if not bool(defined.any()):
        return [None] * len(grid)
    y = np.interp(grid, t_s[defined], values[defined])
    return [
        round(float(v), decimals) + 0.0 if good else None for v, good in zip(y, ok, strict=True)
    ]


def run_series(frame: pd.DataFrame, fields: Sequence[SeriesField]) -> dict[str, Any]:
    """The resampled series of one run (``frame``: ``read_series``): ``t`` [s after
    release] on ``sample_grid``, then each field of ``fields`` in order (its column,
    converted and rounded as the field says), then ``phase``, the phase name per sample
    (the phase of the last row at or before it). The caller owns the field list, so two
    consumers resample the same frame to different sets."""
    t = frame["t_rel_release_s"].to_numpy(dtype=float)
    grid = sample_grid(float(t[0]), float(t[-1]))
    out: dict[str, Any] = {"t": [round(float(v), TIME_DECIMALS) for v in grid]}
    for field, column, convert, decimals in fields:
        raw = frame[column].to_numpy(dtype=float)
        values = raw if convert is None else np.asarray(convert(raw), dtype=float)
        out[field] = series_values(t, values, grid, decimals)
    idx = np.clip(np.searchsorted(t, grid, side="right") - 1, 0, len(t) - 1)
    out["phase"] = frame["phase"].astype(str).to_numpy()[idx].tolist()
    return out


# ------------------------------------------------------------------ events


@dataclass(frozen=True)
class EventRow:
    """One row of events.csv, plus what ``with_drop_masses`` adds.

    As recorded: ``t_s`` [s, the run's clock] and ``t_rel_s`` [s after release]; the
    event ``name``; ``phase`` and ``stage`` as written (None when the file has no such
    column); altitude ``alt_m`` [m], Earth-fixed ``downrange_m`` [m], Earth-relative
    ``speed_rel_mps`` and inertial ``speed_inertial_mps`` [m/s], Earth-relative
    flight-path angle ``gamma_rel_rad`` [rad] and mass ``m_kg`` [kg]: each NaN when the
    file has no such column or the cell is not a number.

    Added: ``m_before_kg`` and ``m_after_kg`` [kg], the mass just before and just after
    the instant of the row (equal unless something is dropped there); ``dropped``, what
    left (the dropped stage's name, or 'fairing'; None when nothing did); all three None
    until ``with_drop_masses`` fills them. ``recorded`` is False only for a row that
    function adds (a fairing drop the planner logs no row for)."""

    t_s: float
    t_rel_s: float
    name: str
    phase: str | None
    stage: str | None
    alt_m: float
    downrange_m: float
    speed_rel_mps: float
    speed_inertial_mps: float
    gamma_rel_rad: float
    m_kg: float
    m_before_kg: float | None = None
    m_after_kg: float | None = None
    dropped: str | None = None
    recorded: bool = True


def _cell_float(value: Any) -> float:
    """A CSV cell as a float, NaN when it is missing or not a number (a bool is not)."""
    if isinstance(value, bool) or not isinstance(value, int | float | np.number):
        return math.nan
    return float(value)


def _cell_text(row: Mapping[str, Any], column: str) -> str | None:
    """A CSV cell as text, None when the file has no such column."""
    return str(row[column]) if column in row else None


def _event_row(row: Mapping[str, Any], offset_s: float) -> EventRow:
    """The EventRow of one events.csv record (``offset_s``: ``release_offset_s`` [s])."""
    t_s = float(row["t_s"])
    return EventRow(
        t_s=t_s,
        t_rel_s=t_s - offset_s,
        name=str(row["event"]),
        phase=_cell_text(row, "phase"),
        stage=_cell_text(row, "stage"),
        alt_m=_cell_float(row.get("alt_m")),
        downrange_m=_cell_float(row.get("downrange_m")),
        speed_rel_mps=_cell_float(row.get("speed_rel_mps")),
        speed_inertial_mps=_cell_float(row.get("speed_inertial_mps")),
        gamma_rel_rad=_cell_float(row.get("gamma_rel_rad")),
        m_kg=_cell_float(row.get("m_kg")),
    )


def read_events(
    path: Path,
    offset_s: float,
    *,
    required: Sequence[str] = EVENT_REQUIRED_COLUMNS,
    error: type[RunDataError] = RunDataError,
) -> list[EventRow]:
    """Every row of an events.csv (``path``) in file order as an EventRow, its time
    after release being t_s - ``offset_s`` [s] (``release_offset_s`` of the run's time
    series); [] when the file is missing. Only the ``required`` columns must exist
    (``error`` otherwise): by default t_s and event, so the eight-column events.csv of
    the test fixtures (tests/test_animate.py, tests/test_replay.py) reads as well as the
    ten planar columns of a recorded run. No mass arithmetic is done here
    (``with_drop_masses``)."""
    if not path.is_file():
        return []
    frame = pd.read_csv(path, encoding="utf-8")
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise error(f"{path} lacks event columns {missing}")
    return [_event_row(row, offset_s) for row in frame.to_dict("records")]


def has_fairing(masses: VehicleMasses) -> bool:
    """True when the vehicle of ``masses`` has a fairing that can be dropped: a fairing
    mass above zero and at least TWO_STAGES stages, the guard ``metrics_planar.
    fairing_items`` applies before it reads any event (its metric is None otherwise)."""
    return masses.fairing_kg > 0.0 and len(masses.stage_names) >= TWO_STAGES


def fairing_case(
    rows: Sequence[EventRow], fairing_drop: str | None, masses: VehicleMasses | None
) -> str | None:
    """How the fairing left, as one of metrics_planar's forms (FAIRING_IN_BURN,
    FAIRING_AT_IGNITION, FAIRING_AT_STAGING, FAIRING_KEPT) or None (no fairing, one
    stage, never staged, or not known): ``fairing_drop`` (the run's metric of that name)
    when it is given, else read from the event ``rows`` and the vehicle's rule as
    ``metrics_planar.fairing_items`` reads the trace, in its order: with ``masses``, a
    vehicle without a fairing mass or with one stage has no form (None), whatever the
    rows hold (the planner logs a ``fairing`` row for a zero-mass fairing whose heating
    criterion is met at staging; the metric is None for it). Then a ``fairing`` row in
    COAST_STAGING is 'at staging'; one at the time of the stage-2 ignition row (the
    ``ignition`` row logged in LTG_BURN; equal t_s) is 'at stage-2 ignition'; any other
    is 'in the stage-2 burn'. Without a ``fairing`` row the form needs ``masses``: 'at
    staging' under rule staging and 'kept' otherwise, when the rows hold a ``staging``
    row."""
    if fairing_drop is not None:
        return fairing_drop
    if masses is not None and not has_fairing(masses):
        return None
    fairing = next((r for r in rows if r.name == FAIRING_EVENT), None)
    if fairing is None:
        if masses is None or not any(r.name == STAGING_EVENT for r in rows):
            return None
        at_staging = masses.fairing_trigger == FAIRING_RULE_STAGING
        return FAIRING_AT_STAGING if at_staging else FAIRING_KEPT
    if fairing.phase == COAST_STAGING:
        return FAIRING_AT_STAGING
    lit = {r.t_s for r in rows if r.name == IGNITION_EVENT and r.phase == LTG_BURN}
    return FAIRING_AT_IGNITION if fairing.t_s in lit else FAIRING_IN_BURN


def _dropped_stage(row: EventRow, masses: VehicleMasses, earlier: int) -> int | None:
    """Index of the stage a ``staging`` row drops: the stage before the row's own
    ``stage`` (the planner logs the row with the next stage's name); when the name is
    unknown, the ``earlier``-th stage (``earlier``: staging rows before this one). None
    when that is not a stage of ``masses``."""
    if row.stage in masses.stage_names:
        index = masses.stage_names.index(row.stage) - 1
    else:
        index = earlier
    return index if 0 <= index < len(masses.stage_names) else None


def _with_drop(row: EventRow, before_kg: float, after_kg: float, dropped: str) -> EventRow:
    """``row`` with the mass before and after its drop [kg] and what was dropped; the
    masses are None when the row has no mass."""
    return replace(row, m_before_kg=finite(before_kg), m_after_kg=finite(after_kg), dropped=dropped)


def with_drop_masses(
    rows: Sequence[EventRow], masses: VehicleMasses | None, fairing_drop: str | None
) -> list[EventRow]:
    """``rows`` (``read_events``) with the mass before and after every instant
    (``m_before_kg``, ``m_after_kg`` [kg]) and what was dropped there. Pure: no I/O.

    Inputs: the event rows of one run in file order; ``masses``, the VehicleMasses of
    the run's own vehicle block (None: nothing is filled, no row is added and nothing
    can fail, for a caller without a complete vehicle block); ``fairing_drop``, the
    run's metric of that name (one of metrics_planar's FAIRING_* forms) or None, in
    which case the rows and the vehicle's rule decide (``fairing_case``).

    What the planner logs (phases/planar.py) and what is reported, with m the row's
    ``m_kg``, m_dry the dry mass of the stage dropped and F the fairing mass:

    - ``staging`` row: always the state after the staging map. Before m + m_dry, after m;
      when the map also took the fairing (the two 'at staging' cases below) before
      m + m_dry + F, after m + F, the fairing's own drop following as a second link.
    - ``fairing`` row in the stage-2 burn (the heating event) or at stage-2 ignition
      (the criterion met in the staging coast): the state before the drop. Before m,
      after m - F.
    - ``fairing`` row in COAST_STAGING (the criterion already met at staging; the row
      has the staging row's time and mass): the state after both drops. Before m + F,
      after m.
    - rule staging: the staging map takes the fairing and no ``fairing`` row is logged.
      A row is added after the staging row, at its time and state, named 'fairing' and
      marked ``recorded=False``: before m + F, after m.
    - every other row: before = after = m. A ``fairing`` row of a vehicle without a
      fairing mass (``has_fairing`` False: the planner logs one when a zero-mass
      fairing's heating criterion is met at staging) is such a row: nothing left.

    In the two 'at staging' cases the stage and the fairing leave in one map at one
    instant; reporting them as a chain (stage first, then fairing, the order of the
    rows) is a convention of this reader that keeps each 'after' equal to the next
    'before'. A ``fairing`` row's phase, not the metric, decides which side of the drop
    it holds; the metric (or the rule) decides only whether a missing row is an
    unrecorded drop at staging. A row without a mass, or a staging row whose stage
    cannot be placed, keeps None masses."""
    if masses is None:
        return list(rows)
    fairing = has_fairing(masses)
    fairing_kg = masses.fairing_kg
    fairing_rows = [r for r in rows if r.name == FAIRING_EVENT]
    logged_at_staging = fairing and any(r.phase == COAST_STAGING for r in fairing_rows)
    unrecorded = (
        fairing
        and not fairing_rows
        and fairing_case(rows, fairing_drop, masses) == FAIRING_AT_STAGING
    )
    out: list[EventRow] = []
    stagings = 0
    for row in rows:
        if row.name == STAGING_EVENT:
            index = _dropped_stage(row, masses, stagings)
            stagings += 1
            if index is None:
                out.append(row)
                continue
            with_fairing = index == 0 and (logged_at_staging or unrecorded)
            carried_kg = fairing_kg if with_fairing else 0.0
            before_kg = row.m_kg + masses.stage_dry_kg[index] + carried_kg
            out.append(_with_drop(row, before_kg, row.m_kg + carried_kg, masses.stage_names[index]))
            if with_fairing and unrecorded:
                added = replace(row, name=FAIRING_EVENT, recorded=False)
                out.append(_with_drop(added, row.m_kg + fairing_kg, row.m_kg, FAIRING_EVENT))
        elif fairing and row.name == FAIRING_EVENT and row.phase == COAST_STAGING:
            out.append(_with_drop(row, row.m_kg + fairing_kg, row.m_kg, FAIRING_EVENT))
        elif fairing and row.name == FAIRING_EVENT:
            out.append(_with_drop(row, row.m_kg, row.m_kg - fairing_kg, FAIRING_EVENT))
        else:
            out.append(replace(row, m_before_kg=finite(row.m_kg), m_after_kg=finite(row.m_kg)))
    return out


# ------------------------------------------------------------------ calibration

CALIBRATION_RECORDS: dict[str, tuple[float, float, str]] = {
    "generic_f9_class_2d": (26054.4, 22800.0, "docs/findings/CAL-f9-leo-2d"),
    "generic_f9_class_2d_readme_loads": (24700.0, 22800.0, "docs/findings/CAL-f9-leo-2d"),
}
"""Calibration record per vehicle (resolved_config.yaml vehicle.name) for the footnote:
(model payload capacity P* [kg] of its calibration run, published reference [kg], the
findings note). Both from results/calibration_f9_2d/20260930T100100Z against 22,800 kg
to LEO (spacex.com, expendable): generic_f9_class_2d, the gate vehicle (mass set C, run
pad), P* 26,054.4 kg, +14.27%, outside the band (a documented miss, accepted
2026-09-30); generic_f9_class_2d_readme_loads (mass set A, README loads, case
readme_loads; SP1 step 8a), P* 24,700.0 kg, +8.33%, inside the band. A re-run
calibration must update these entries; tests/test_animate.py checks each against the
note and tests/data/calibration_record.json. A vehicle not listed gets a 'no calibration
record' caveat. One dict object behind every name (plots.CALIBRATION_RECORDS and
results_io's import of it are this object)."""
CALIBRATION_BAND = 0.10
"""Relative payload band of the calibration gate (CLAUDE.md, Calibration: within +/-10%
of the published figure); the footnote and the replay page say when a record lies
inside it (``inside_calibration_band``)."""
CALIBRATION_BAND_EDGE_REL_TOL = 1e-12
"""Relative tolerance [-] on the band's edges: P*/reference - 1 rounds either way in
floating point (25,080 kg against 22,800 kg, exactly +10%, computes to
0.10000000000000009; 20,520 kg, exactly -10%, to -0.09999999999999998), so both edges
count as inside, as "within +/-10%" says. 1e-12 of the band is 2.3e-9 kg at 22,800 kg."""
CALIBRATION_GATE_VEHICLE = "generic_f9_class_2d"
"""The pre-registered calibration gate (mass set C), named "Gate vehicle" in the footnote."""


def calibration_gap(model_kg: float, reference_kg: float) -> float:
    """The relative gap of a calibration record: model payload capacity model_kg [kg]
    over the published reference reference_kg [kg], less 1 [-] (positive: the model
    carries more)."""
    return model_kg / reference_kg - 1.0


def inside_calibration_band(gap: float) -> bool:
    """True when a calibration gap [-] (``calibration_gap``) lies inside the gate band,
    edges included: abs(gap) <= CALIBRATION_BAND (1 + CALIBRATION_BAND_EDGE_REL_TOL)."""
    return abs(gap) <= CALIBRATION_BAND * (1.0 + CALIBRATION_BAND_EDGE_REL_TOL)


# ------------------------------------------------------------------ output paths (one rule)


def results_tree(run_dir: Path) -> Path:
    """The results tree holding ``run_dir`` (<tree>/<experiment>/<timestamp>): its
    nearest ancestor (inclusive) named exactly RESULTS_TREE_NAME; else, for a tree
    written with --results-root elsewhere, the parent of the experiment directory (the
    run directory itself when that parent is a filesystem root). Resolved path."""
    resolved = run_dir.resolve()
    for candidate in (resolved, *resolved.parents):
        if candidate.name == RESULTS_TREE_NAME:
            return candidate
    root = resolved.parent.parent
    return resolved if root == root.parent else root


def is_inside(path: Path, root: Path) -> bool:
    """True when ``path`` is ``root`` or below it (both resolved)."""
    return path.resolve().is_relative_to(root.resolve())


def results_ancestors(path: Path) -> list[Path]:
    """The resolved ancestors of ``path`` (inclusive) named RESULTS_TREE_NAME, ignoring
    case, innermost first: every results tree ``path`` lies in, whichever run it belongs
    to."""
    resolved = path.resolve()
    name = RESULTS_TREE_NAME.casefold()
    return [p for p in (resolved, *resolved.parents) if p.name.casefold() == name]


def protected_tree(path: Path, run_dir: Path) -> Path | None:
    """The outermost results tree holding ``path``: the run's own tree (``results_tree``,
    which also covers a tree written with --results-root under another name) or any
    folder named RESULTS_TREE_NAME in any letter case; None when ``path`` lies in
    neither."""
    trees = results_ancestors(path)
    own = results_tree(run_dir)
    if is_inside(path, own):
        trees.append(own.resolve())
    return min(trees, key=lambda p: len(p.parts)) if trees else None


def default_output_path(run_dir: Path, cwd: Path, file_name: str) -> Path:
    """<cwd>/<file_name>; when ``cwd`` is inside a results tree (``protected_tree``: the
    run's own or any folder named results) the file goes next to the outermost such tree
    instead (results/ is never hand-edited)."""
    tree = protected_tree(cwd, run_dir)
    return (cwd if tree is None else tree.parent) / file_name


def check_output_suffix(
    out_path: Path,
    suffixes: Sequence[str],
    suffix_text: str,
    *,
    error: type[RunDataError] = RunDataError,
) -> None:
    """Raise ``error`` for an output whose extension (any letter case) is not one of
    ``suffixes``; ``suffix_text`` completes 'output <path> must end in ...'."""
    if out_path.suffix.lower() not in suffixes:
        raise error(f"output {out_path} must end in {suffix_text}")


def check_outside_results(
    out_path: Path,
    run_dir: Path,
    *,
    what: str = DEFAULT_OUTPUT_NOUN,
    error: type[RunDataError] = RunDataError,
) -> None:
    """Raise ``error`` for an output inside a results tree (``protected_tree``: the tree
    of ``run_dir`` or any folder named results); ``what`` names the thing to write
    elsewhere ('animation', 'page')."""
    if protected_tree(out_path, run_dir) is not None:
        raise error(
            f"output {out_path} is inside the results tree; results/ is never edited by "
            f"hand, so write the {what} elsewhere (--out)"
        )


def check_output_folder(out_path: Path, *, error: type[RunDataError] = RunDataError) -> None:
    """Raise ``error`` for an output whose folder does not exist."""
    if not out_path.parent.is_dir():
        raise error(f"output folder does not exist: {out_path.parent}")


def check_output(
    out_path: Path,
    run_dir: Path,
    *,
    suffixes: Sequence[str],
    suffix_text: str,
    what: str = DEFAULT_OUTPUT_NOUN,
    error: type[RunDataError] = RunDataError,
) -> None:
    """The whole check of a writer's output path, in this order: the extension
    (``check_output_suffix``), the results trees (``check_outside_results``), the folder
    (``check_output_folder``). A writer with a check of its own between two of them (the
    animation's ffmpeg test) calls the three parts itself."""
    check_output_suffix(out_path, suffixes, suffix_text, error=error)
    check_outside_results(out_path, run_dir, what=what, error=error)
    check_output_folder(out_path, error=error)
