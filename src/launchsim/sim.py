"""Run one configuration and return a Result; results I/O (the only module besides cli.py
that touches the file system).

Build step 4 ships the results layout and a placeholder ``run`` (status
``not_simulated``); build steps 5-9 replace ``run`` and extend the metrics and summary
content. ``run_experiment`` and ``run_sweep`` are the stable entry points the CLI calls.

Results layout (never overwritten; CLAUDE.md)::

    results/<experiment>/<YYYYMMDDTHHMMSSZ>[-n]/
        resolved_config.yaml   experiment name, vehicle dict, every run dict, git, timestamp
        metrics.json           per-run metrics and the comparison against the baseline
        summary.md             tables against the baseline, assumptions, git hash, timestamp
        <run>/timeseries.csv   sampled state (t_s, z_m, v_mps, m_kg, ...)
        <run>/events.csv       phase-boundary events (t_s, event, phase)
        plots/<run>_<name>.png only when a run has time-series data (plot_stem sanitises)

Experiment and run names become directory names, so they must be single safe path
components (check_name); the CLI validates them before anything is written.

A sweep writes ``sweep_<n>/run_NNNN/`` (flat single-run layout: resolved_config.yaml,
metrics.json, summary.md, timeseries.csv, events.csv, plots/) plus
``sweep_<n>/sweep_index.csv`` and a top-level summary.md; the baseline it compares
against is written once under ``baseline/``.

Both entry points create the run directory before simulating anything, so an unwritable
results root fails before a long run starts. summary.md is written last; if anything
raises before it, ``FAILED.txt`` with the traceback is written into the directory and the
exception propagates, so a directory without summary.md is partial and never mistaken
for a good run (the next run creates a sibling; nothing is ever overwritten).

Every file is written with ``encoding="utf-8"`` and ``newline="\\n"``.
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import traceback
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
import yaml
from matplotlib.figure import Figure

from launchsim.config import (
    ConstantAccelConfig,
    ResolvedExperiment,
    ResolvedRun,
    RunConfig,
    SweepPoint,
)
from launchsim.vehicle import Vehicle

Status = Literal["nominal", "impact", "no_liftoff", "drive_limit", "not_simulated"]

COMPARISON_BASIS = (
    "Comparison basis: sweep-optimized (Phase 1 has no guidance parameters); "
    "1-D vertical, vacuum thrust, no drag, no rotation, no throttling"
)
TIMESERIES_COLUMNS: tuple[str, ...] = ("t_s", "z_m", "v_mps", "m_kg")
EVENT_COLUMNS: tuple[str, ...] = ("t_s", "event", "phase")
TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"
GIT_TIMEOUT_S = 5.0
GIT_EXCLUDE_RESULTS = ":(exclude)results"  # pathspec: the results tree never counts as dirty
NOT_A_REPO_MARKER = "not a git repository"
CSV_FLOAT_FORMAT = "%.12g"
MAX_DIR_SUFFIX = 1000
FAILED_MARKER = "FAILED.txt"  # written into a run directory that raised before summary.md
PLOT_SERIES_COLOR = "#2a78d6"
PLOT_GRID_COLOR = "#d8d8d4"
PLOT_LINE_WIDTH = 2.0
PLOT_GRID_LINE_WIDTH = 0.6
PLOT_FIGSIZE_IN = (6.4, 3.6)
PLOT_DPI = 120
# Metric keys the results records add themselves (Result.status, Result.flags); a metric
# with one of these names would be silently overwritten in metrics.json, so it is refused.
RESERVED_METRIC_KEYS: frozenset[str] = frozenset({"status", "flags"})
PHASE1_ASSUMPTIONS: tuple[str, ...] = (
    "1-D vertical motion; gravity mu/r^2 in flight",
    "vacuum thrust from sea level (no back-pressure), no atmosphere, no drag",
    "no Earth rotation (omega_p = 0), Coriolis neglected",
    "no throttling; instantaneous cutoff at propellant depletion",
)
# Metric keys every summary must report (CLAUDE.md "Every summary reports"). metrics_table
# prints them first, "n/a" when a run does not carry one, so a missing item is visible;
# build step 9 fills them in with these names.
REQUIRED_METRICS: tuple[str, ...] = (
    "payload_equiv_ideal_kg",  # ideal-screening payload equivalent (Phase 1: no payload)
    "loss_gravity_mps",
    "loss_drag_mps",
    "loss_steering_mps",
    "loss_back_pressure_mps",
    "max_q_pa",
    "peak_felt_axial_g",
    "peak_interface_force_N",
    "peak_track_normal_g",
    "assist_energy_J",
    "assist_energy_kWh",
    "peak_drive_power_W",
    "facility_length_m",
)

# Names that become directories inside the results tree: one safe path component. The
# length cap keeps results/<name>/<ts>/sweep_n/run_NNNN/plots/<png> under Windows'
# default MAX_PATH (260) from a repository at a normal depth.
NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.+-]*$")
MAX_NAME_LEN = 64
RESERVED_RUN_NAME_PATTERN = re.compile(r"^(plots|baseline|sweep_\d+|run_\d+)$")
WINDOWS_DEVICE_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
)
PLOT_STEM_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")


class InvalidNameError(ValueError):
    """An experiment or run name that cannot be a single, safe results-directory name."""


def check_name(name: str, what: str, reserved: re.Pattern[str] | None = None) -> str:
    """Validate a name that becomes a results directory and return it.

    Allowed: ``[A-Za-z0-9][A-Za-z0-9_.+-]*`` of at most MAX_NAME_LEN characters, not
    ending in ``.`` (Windows strips trailing dots), no Windows device names (CON, NUL,
    COM1, ...), and not matching ``reserved``. Raises InvalidNameError otherwise.
    """
    if not isinstance(name, str) or not NAME_PATTERN.match(name) or name.endswith("."):
        raise InvalidNameError(
            f"{what} {name!r} is not a valid results directory name: use letters, digits, "
            "'_', '.', '+' or '-', starting with a letter or digit and not ending in '.'"
        )
    if len(name) > MAX_NAME_LEN:
        raise InvalidNameError(
            f"{what} {name!r} is longer than {MAX_NAME_LEN} characters ({len(name)}); "
            "results paths must stay short on Windows"
        )
    if name.split(".")[0].upper() in WINDOWS_DEVICE_NAMES:
        raise InvalidNameError(f"{what} {name!r} is a reserved Windows device name")
    if reserved is not None and reserved.match(name):
        raise InvalidNameError(f"{what} {name!r} is reserved by the results layout")
    return name


def check_run_name(name: str) -> str:
    """check_name for a run: additionally rejects plots, baseline, sweep_<n>, run_<n>."""
    return check_name(name, "run name", RESERVED_RUN_NAME_PATTERN)


def check_result_names(resolved: ResolvedExperiment) -> None:
    """Validate the experiment name and every baseline/variant name before anything is
    written; raises InvalidNameError naming the offender."""
    check_name(resolved.experiment.name, "experiment name")
    for name in resolved.runs:
        check_run_name(name)


# ------------------------------------------------------------------------------ results


def empty_timeseries() -> pd.DataFrame:
    """An empty time-series frame with the standard columns (t_s, z_m, v_mps, m_kg)."""
    return pd.DataFrame({c: pd.Series(dtype="float64") for c in TIMESERIES_COLUMNS})


def empty_events() -> pd.DataFrame:
    """An empty events frame with columns t_s [s], event, phase."""
    return pd.DataFrame(
        {
            "t_s": pd.Series(dtype="float64"),
            "event": pd.Series(dtype="str"),
            "phase": pd.Series(dtype="str"),
        }
    )


@dataclass(frozen=True)
class Result:
    """Outcome of one run (SI; times are seconds since the run's internal t = 0).

    metrics: flat name -> value dict (numbers, strings, None); written to metrics.json.
    timeseries: sampled state, columns t_s, z_m, v_mps, m_kg (more in later steps).
    events: phase-boundary events, columns t_s, event, phase.
    loss_budget / assist_budget: LossBudget / AssistEnergyBudget from build steps 6-7.
    assumptions: attributed assumption strings for the summary.
    phases: PhaseResult list (build step 5); empty in the placeholder.
    status: nominal, impact, no_liftoff, drive_limit or not_simulated.
    flags: warnings such as interface_tensile.
    """

    metrics: dict[str, Any]
    timeseries: pd.DataFrame
    loss_budget: object | None
    assist_budget: object | None
    assumptions: list[str]
    phases: list[Any]
    status: Status
    flags: list[str]
    events: pd.DataFrame = field(default_factory=empty_events)


@dataclass(frozen=True)
class RunResult:
    """A resolved run together with its Result."""

    name: str
    resolved: ResolvedRun
    result: Result


@dataclass(frozen=True)
class ExperimentResult:
    """Baseline, variants, their comparison, and the provenance of one experiment run."""

    experiment_name: str
    vehicle_name: str
    baseline: RunResult
    variants: dict[str, RunResult]
    comparison: dict[str, dict[str, Any]]
    git: dict[str, Any]
    timestamp_utc: str
    comparison_basis: str = COMPARISON_BASIS

    @property
    def runs(self) -> dict[str, RunResult]:
        """Baseline first, then every variant, keyed by name."""
        return {self.baseline.name: self.baseline, **self.variants}


@dataclass(frozen=True)
class SweepResult:
    """One sweep: its 1-based index, the run it perturbs, the axis paths and the points.

    ``sweep_index`` is 1-based and names the ``sweep_<n>`` directory;
    config.SweepPoint.sweep_index (on every entry of ``points``) is 0-based, so
    ``point.sweep_index + 1 == sweep_index`` (checked by run_sweep). Build paths and
    labels from this field, not from the points.
    """

    sweep_index: int
    of: str
    axes: list[str]
    points: list[SweepPoint]
    results: list[RunResult]
    comparisons: list[dict[str, Any]]
    run_dirs: list[Path]


# ------------------------------------------------------------------- placeholder run


def constant_accel_assumptions(cfg: ConstantAccelConfig) -> list[str]:
    """Assumptions of the constant_accel screening drive, listed from its config.

    Every parameter of the drive is an assumption in Phase 1 (nothing is sourced).
    """
    return [
        f"constant_accel: prescribed net acceleration {cfg.net_accel_g:g} g0 over "
        f"{cfg.stroke_m:g} m (assumed)",
        f"constant_accel: carriage mass {cfg.carriage_mass_t:g} t (assumed)",
        f"constant_accel: braking deceleration {cfg.brake_decel_g:g} g0 (assumed)",
        f"constant_accel: drive efficiency {cfg.drive_efficiency:g} (assumed)",
        "constant_accel: exhaust impingement fraction "
        f"{cfg.exhaust_impingement_fraction:g} (assumed)",
        f"constant_accel: shaft {cfg.shaft}; no air column, no friction",
        "constant_accel: constant g_eff = mu/R_E^2 on the track, omega_p = 0, Coriolis neglected",
        "constant_accel: drive force unconstrained; infinite jerk at push start and release",
        "constant_accel: vehicle clamped to the carriage during any hold",
    ]


def run_assumptions(run_config: RunConfig) -> list[str]:
    """Phase 1 assumptions of a run plus those of its assist model."""
    out = list(PHASE1_ASSUMPTIONS)
    if isinstance(run_config.assist, ConstantAccelConfig):
        out += constant_accel_assumptions(run_config.assist)
    return out


def run(run_config: RunConfig, vehicle: Vehicle) -> Result:
    """Run one configuration (placeholder until build steps 5-9 land).

    Inputs: a validated RunConfig and the Vehicle dataclass (SI). Output: a Result with
    status ``not_simulated``, an empty time series and the metrics the layout needs
    (the status lives on Result.status; metrics must not use RESERVED_METRIC_KEYS).
    """
    metrics: dict[str, Any] = {
        "liftoff_mass_kg": vehicle.liftoff_mass_kg(),
        "assist_model": run_config.assist.model,
    }
    return Result(
        metrics=metrics,
        timeseries=empty_timeseries(),
        loss_budget=None,
        assist_budget=None,
        assumptions=[*run_assumptions(run_config), "placeholder: no dynamics yet (steps 5-9)"],
        phases=[],
        status="not_simulated",
        flags=[],
    )


def run_resolved(resolved: ResolvedRun) -> RunResult:
    """Run a ResolvedRun and wrap the Result with its name and config."""
    return RunResult(resolved.name, resolved, run(resolved.run, resolved.to_vehicle()))


# ---------------------------------------------------------------------- comparison


def _is_number(x: object) -> bool:
    """True for int/float and numpy numbers (bool excluded), finite or not."""
    return isinstance(x, int | float | np.integer | np.floating) and not isinstance(x, bool)


def _is_finite_number(x: object) -> bool:
    """True for a number that is neither NaN nor infinite."""
    return _is_number(x) and math.isfinite(float(x))


def _is_pandas_missing(x: object) -> bool:
    """True for the pandas missing scalars pd.NA and pd.NaT (an unavailable value)."""
    return x is pd.NA or x is pd.NaT


def _is_numeric_or_missing(x: object) -> bool:
    """True for a number (finite or not) or a pandas missing scalar: a numeric metric
    whose value may be unavailable."""
    return _is_number(x) or _is_pandas_missing(x)


def compare(result: Result, baseline: Result) -> dict[str, Any]:
    """Deltas (variant minus baseline) of every numeric metric both results carry.

    Keys are ``delta_<metric>``; non-numeric metrics are skipped. A delta whose operands
    are not both finite (NaN, inf, pd.NA, pd.NaT) is None (written as null in JSON, an
    empty CSV cell, "n/a" in a summary). Status is always carried as ``status`` and
    ``baseline_status``.
    """
    out: dict[str, Any] = {"status": result.status, "baseline_status": baseline.status}
    for key, value in result.metrics.items():
        base = baseline.metrics.get(key)
        if _is_numeric_or_missing(value) and _is_numeric_or_missing(base):
            finite = _is_finite_number(value) and _is_finite_number(base)
            out[f"delta_{key}"] = float(value) - float(base) if finite else None
    return out


# ---------------------------------------------------------------------- run dir / git


def utc_timestamp(now: datetime | None = None) -> str:
    """UTC timestamp as YYYYMMDDTHHMMSSZ (no colons: NTFS-safe)."""
    now = datetime.now(UTC) if now is None else now.astimezone(UTC)
    return now.strftime(TIMESTAMP_FORMAT)


def make_run_dir(root: Path, experiment_name: str, now: datetime | None = None) -> Path:
    """Create results/<experiment>/<YYYYMMDDTHHMMSSZ>/ and return it.

    On a collision the suffixes -2, -3, ... are tried; every attempt uses
    ``mkdir(exist_ok=False)`` so an existing directory is never reused. The experiment
    name must be a safe single path component (check_name).
    """
    base = Path(root) / check_name(experiment_name, "experiment name")
    base.mkdir(parents=True, exist_ok=True)
    stamp = utc_timestamp(now)
    for n in range(1, MAX_DIR_SUFFIX + 1):
        candidate = base / (stamp if n == 1 else f"{stamp}-{n}")
        try:
            candidate.mkdir(exist_ok=False)
        except FileExistsError:
            continue
        return candidate
    raise FileExistsError(f"more than {MAX_DIR_SUFFIX} run directories for {stamp} in {base}")


def _git(args: list[str], cwd: Path) -> str:
    """Run one git command and return its stdout (raises on failure or timeout)."""
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=GIT_TIMEOUT_S,
        check=True,
    )
    return proc.stdout.strip()


def git_info(repo_root: Path) -> dict[str, Any]:
    """Describe the git state of the repository containing a directory, for provenance.

    Returns ``{"hash": "<sha12>" | "unborn" | "no-git", "dirty": bool | None,
    "error": str | None}``. ``no-git`` when git is missing, fails or the directory is
    outside a repository; ``unborn`` for a repository without commits. ``dirty`` is
    evaluated at the repository top level (``git rev-parse --show-toplevel``), whatever
    subdirectory was given, and counts tracked changes and untracked files outside the
    top-level results tree (results/ holds tracked summaries, so it must not make the
    code look modified); it is None when ``git status`` itself failed or timed out, with
    the reason in ``error``. ``error`` otherwise carries git's own message when git
    refused (for example "dubious ownership"), None for a plain "not a repository".
    Never raises.
    """
    try:
        inside = _git(["rev-parse", "--is-inside-work-tree"], repo_root)
        top = Path(_git(["rev-parse", "--show-toplevel"], repo_root)) if inside == "true" else None
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return {"hash": "no-git", "dirty": False, "error": f"{type(exc).__name__}: {exc}"}
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        error = None if not stderr or NOT_A_REPO_MARKER in stderr else stderr
        return {"hash": "no-git", "dirty": False, "error": error}
    if top is None:  # inside a bare repository: no work tree, nothing to describe
        return {"hash": "no-git", "dirty": False, "error": None}
    try:
        sha = _git(["rev-parse", "--short=12", "HEAD"], top)
    except subprocess.CalledProcessError:
        sha = "unborn"
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"hash": "no-git", "dirty": False, "error": f"{type(exc).__name__}: {exc}"}
    try:
        dirty: bool | None = bool(
            _git(["status", "--porcelain", "--", ".", GIT_EXCLUDE_RESULTS], top)
        )
        error = None
    except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
        dirty, error = None, f"git status failed: {type(exc).__name__}: {exc}"
    return {"hash": sha, "dirty": dirty, "error": error}


def git_label(git: Mapping[str, Any]) -> str:
    """``<sha12>``, ``<sha12>-dirty``, ``<sha12>-dirty?`` (status unknown), ``unborn`` or
    ``no-git`` for summaries."""
    label = str(git.get("hash", "no-git"))
    if label in ("unborn", "no-git"):
        return label
    dirty = git.get("dirty")
    if dirty is None:
        return label + "-dirty?"
    return label + "-dirty" if dirty else label


# -------------------------------------------------------------------------- writers


def json_safe(obj: Any) -> Any:
    """Convert a nested structure to JSON-safe values: NaN/inf/pd.NA/pd.NaT -> None, numpy
    scalars -> Python, tuples/sets -> lists, Path -> POSIX str, keys -> str."""
    if _is_pandas_missing(obj):
        return None
    if isinstance(obj, Mapping):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple | set | frozenset):
        return [json_safe(v) for v in obj]
    if isinstance(obj, bool | np.bool_):
        return bool(obj)
    if isinstance(obj, int | np.integer):
        return int(obj)
    if isinstance(obj, float | np.floating):
        x = float(obj)
        return x if math.isfinite(x) else None
    if isinstance(obj, np.ndarray):
        return json_safe(obj.tolist())
    if isinstance(obj, Path):
        return obj.as_posix()
    if obj is None or isinstance(obj, str):
        return obj
    return str(obj)


def write_json(path: Path, data: Any) -> Path:
    """Write JSON (UTF-8, LF, indent 2, allow_nan=False after json_safe)."""
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(json_safe(data), fh, ensure_ascii=False, indent=2, allow_nan=False)
        fh.write("\n")
    return path


def write_yaml(path: Path, data: Any) -> Path:
    """Write YAML (UTF-8, LF, key order preserved, unicode allowed)."""
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)
    return path


def write_summary(out_dir: Path, text: str) -> Path:
    """Write summary.md (UTF-8, LF) and return its path."""
    path = Path(out_dir) / "summary.md"
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text if text.endswith("\n") else text + "\n")
    return path


def write_csv(path: Path, frame: pd.DataFrame) -> Path:
    """Write a DataFrame as CSV (UTF-8, LF, %.12g floats, no index; header even if empty)."""
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        frame.to_csv(fh, float_format=CSV_FLOAT_FORMAT, lineterminator="\n", index=False)
    return path


def write_timeseries(result: Result, out_dir: Path) -> None:
    """Write <out_dir>/timeseries.csv and <out_dir>/events.csv."""
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "timeseries.csv", result.timeseries)
    write_csv(out_dir / "events.csv", result.events)


def _plot_columns(frame: pd.DataFrame) -> list[str]:
    return [c for c in frame.columns if c != "t_s" and pd.api.types.is_numeric_dtype(frame[c])]


def plot_stem(prefix: str, column: str) -> str:
    """File stem ``<prefix>_<column>`` with every run of characters outside
    ``[A-Za-z0-9_.-]`` replaced by ``_`` (a column such as ``F/N`` becomes ``F_N``)."""
    return PLOT_STEM_UNSAFE.sub("_", f"{prefix}_{column}")


def _plot_text(text: str) -> str:
    """Escape ``$`` so matplotlib does not read the label as mathtext."""
    return text.replace("$", "\\$")


def write_plots(result: Result, plots_dir: Path, prefix: str) -> list[Path]:
    """Write plots/<plot_stem(prefix, column)>.png, one single-series panel per numeric
    column against t_s. Nothing is written when the time series is empty.

    Figures are built from matplotlib.figure.Figure and saved through the Agg canvas
    that PNG output selects, so no pyplot state and no global backend switch is needed:
    importing this module leaves a notebook's inline backend alone.
    """
    frame = result.timeseries
    if frame.empty or "t_s" not in frame.columns:
        return []
    plots_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for col in _plot_columns(frame):
        fig = Figure(figsize=PLOT_FIGSIZE_IN, dpi=PLOT_DPI)
        ax = fig.subplots()
        ax.plot(frame["t_s"], frame[col], color=PLOT_SERIES_COLOR, linewidth=PLOT_LINE_WIDTH)
        ax.set_xlabel("t [s]")
        ax.set_ylabel(_plot_text(col))
        ax.set_title(_plot_text(f"{prefix}: {col}"))
        ax.grid(True, color=PLOT_GRID_COLOR, linewidth=PLOT_GRID_LINE_WIDTH)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        fig.tight_layout()
        path = plots_dir / f"{plot_stem(prefix, col)}.png"
        fig.savefig(path, format="png")
        written.append(path)
    return written


def write_failure_marker(out_dir: Path, exc: BaseException) -> Path:
    """Write <out_dir>/FAILED.txt with the exception's traceback and return its path.

    Called when a run raised after its directory was created and before summary.md was
    written, so a partial results directory is recognisable. Best effort: a second error
    while writing the marker is swallowed so the original exception propagates.
    """
    path = Path(out_dir) / FAILED_MARKER
    text = (
        "This run raised before its results were complete; the files here are partial.\n\n"
        + "".join(traceback.format_exception(exc))
    )
    try:
        with path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    except OSError:
        pass
    return path


# ------------------------------------------------------------------- summary text


def _fmt(value: Any) -> str:
    if value is None or _is_pandas_missing(value):
        return "n/a"
    if isinstance(value, bool):
        return str(value)
    if _is_number(value):
        return f"{float(value):.6g}" if _is_finite_number(value) else "n/a"
    return str(value)


def _metric_keys(results: Iterable[Result]) -> list[str]:
    """REQUIRED_METRICS first, then every other metric key in first-seen order."""
    keys = list(REQUIRED_METRICS)
    for r in results:
        for k in r.metrics:
            if k not in RESERVED_METRIC_KEYS and k not in keys:  # status has its own column
                keys.append(k)
    return keys


def _table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def metrics_table(runs: Mapping[str, RunResult], baseline_name: str) -> str:
    """Markdown table of every metric per run, baseline first; the REQUIRED_METRICS
    columns always come first and read "n/a" when a run does not carry them."""
    keys = _metric_keys(r.result for r in runs.values())
    rows = []
    for name, rr in runs.items():
        label = f"{name} (baseline)" if name == baseline_name else name
        rows.append([label, rr.result.status, *(_fmt(rr.result.metrics.get(k)) for k in keys)])
    return _table(["run", "status", *keys], rows)


def comparison_table(comparison: Mapping[str, Mapping[str, Any]]) -> str:
    """Markdown table of the deltas of every variant against the baseline."""
    if not comparison:
        return "(no variants)"
    keys: list[str] = []
    for comp in comparison.values():
        keys += [k for k in comp if k.startswith("delta_") and k not in keys]
    rows = [[name, *(_fmt(comp.get(k)) for k in keys)] for name, comp in comparison.items()]
    return _table(["variant", *keys], rows)


def assumptions_section(
    runs: Mapping[str, RunResult],
    baseline_name: str | None = None,
    others_label: str = "all variants",
) -> str:
    """Union of assumptions, each attributed to the runs that carry it: ``all runs``,
    ``others_label`` when every run except ``baseline_name`` carries it, else the names."""
    carriers: dict[str, list[str]] = {}
    for name, rr in runs.items():
        for a in rr.result.assumptions:
            carriers.setdefault(a, []).append(name)
    n_runs = len(runs)
    others = [name for name in runs if name != baseline_name]
    lines = []
    for a, names in carriers.items():
        if len(names) == n_runs:
            who = "all runs"
        elif baseline_name is not None and others and names == others:
            who = others_label
        else:
            who = ", ".join(names)
        lines.append(f"- {a} [{who}]")
    return "\n".join(lines) if lines else "(none)"


def flags_section(runs: Mapping[str, RunResult]) -> str:
    """Flags per run, or a note that there are none."""
    lines = [
        f"- {name}: {', '.join(rr.result.flags)}" for name, rr in runs.items() if rr.result.flags
    ]
    return "\n".join(lines) if lines else "(none)"


def provenance_lines(git: Mapping[str, Any], timestamp_utc: str) -> str:
    """Timestamp and git lines for a summary header."""
    lines = [f"- Timestamp (UTC): {timestamp_utc}", f"- Git: {git_label(git)}"]
    if git.get("error"):
        lines.append(f"- Git error: {git['error']}")
    return "\n".join(lines)


def experiment_summary(er: ExperimentResult, header_lines: Sequence[str] = ()) -> str:
    """The summary.md text of an experiment run; ``header_lines`` (already formatted as
    ``- ...`` bullets, e.g. a sweep point's axis values) go under the baseline line."""
    runs = er.runs
    return "\n".join(
        [
            f"# {er.experiment_name}",
            "",
            er.comparison_basis,
            "",
            f"- Vehicle: {er.vehicle_name}",
            f"- Baseline: {er.baseline.name}",
            *header_lines,
            provenance_lines(er.git, er.timestamp_utc),
            "",
            "## Metrics",
            "",
            metrics_table(runs, er.baseline.name),
            "",
            "## Deltas against the baseline",
            "",
            comparison_table(er.comparison),
            "",
            "## Flags",
            "",
            flags_section(runs),
            "",
            "## Assumptions",
            "",
            assumptions_section(runs, er.baseline.name),
            "",
        ]
    )


# ------------------------------------------------------------------ experiment I/O


def _resolved_config_dict(er: ExperimentResult) -> dict[str, Any]:
    """The resolved_config.yaml content: one vehicle dict, a run dict per run, and the
    vehicle dict again only for runs whose vehicle differs (sensitivity, vehicle sweeps)."""
    base_vehicle = er.baseline.resolved.vehicle_dict
    runs: dict[str, Any] = {}
    for name, rr in er.runs.items():
        entry: dict[str, Any] = {"run": rr.resolved.run_dict}
        if rr.resolved.vehicle_dict != base_vehicle:
            entry["vehicle"] = rr.resolved.vehicle_dict
        runs[name] = entry
    return {
        "experiment": er.experiment_name,
        "timestamp_utc": er.timestamp_utc,
        "git": dict(er.git),
        "comparison_basis": er.comparison_basis,
        "baseline": er.baseline.name,
        "vehicle": base_vehicle,
        "runs": runs,
    }


def metrics_record(result: Result) -> dict[str, Any]:
    """The metrics.json record of one run: its metrics plus ``status`` and ``flags``.

    Raises ValueError when a metric uses a RESERVED_METRIC_KEYS name, which would
    otherwise be overwritten here while summary.md kept the metric (a schema error).
    """
    clash = sorted(RESERVED_METRIC_KEYS & set(result.metrics))
    if clash:
        raise ValueError(f"metrics use reserved keys {clash}; see sim.RESERVED_METRIC_KEYS")
    return {**result.metrics, "status": result.status, "flags": result.flags}


def _metrics_dict(er: ExperimentResult) -> dict[str, Any]:
    return {
        "experiment": er.experiment_name,
        "timestamp_utc": er.timestamp_utc,
        "git": dict(er.git),
        "comparison_basis": er.comparison_basis,
        "baseline": er.baseline.name,
        "runs": {name: metrics_record(rr.result) for name, rr in er.runs.items()},
        "comparison": er.comparison,
    }


def write_run(experiment_result: ExperimentResult, out_dir: Path, plots: bool) -> Path:
    """Write an experiment's results into out_dir (see the module docstring) and return it."""
    out_dir = Path(out_dir)
    er = experiment_result
    for name in er.runs:
        check_run_name(name)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_yaml(out_dir / "resolved_config.yaml", _resolved_config_dict(er))
    write_json(out_dir / "metrics.json", _metrics_dict(er))
    for name, rr in er.runs.items():
        write_timeseries(rr.result, out_dir / name)
        if plots:
            write_plots(rr.result, out_dir / "plots", name)
    write_summary(out_dir, experiment_summary(er))
    return out_dir


def sweep_point_header(sweep_index: int, point: SweepPoint, n_points: int) -> list[str]:
    """Summary header bullets naming a sweep point: the sweep_<n> directory (1-based
    ``sweep_index``), the point's position, its parent run and its axis values."""
    values = ", ".join(f"{axis} = {value}" for axis, value in point.overrides.items())
    return [
        f"- Sweep: sweep_{sweep_index}, point {point.point_index} of {n_points} "
        f"(of {point.of}): {values}"
    ]


def write_single(
    run_result: RunResult,
    baseline: RunResult,
    er: ExperimentResult,
    out_dir: Path,
    plots: bool,
    header_lines: Sequence[str] = (),
) -> Path:
    """Flat single-run layout for a sweep point (or the sweep's baseline copy):
    resolved_config.yaml, metrics.json, summary.md, timeseries.csv, events.csv, plots/.
    ``header_lines`` (see sweep_point_header) name the point in its summary.md."""
    out_dir = Path(out_dir)
    rr = run_result
    check_name(rr.name, "run name")  # sweep points are run_NNNN, so no reserved check here
    out_dir.mkdir(parents=True, exist_ok=True)
    comparison = {} if rr is baseline else {rr.name: compare(rr.result, baseline.result)}
    write_yaml(
        out_dir / "resolved_config.yaml",
        {
            "experiment": er.experiment_name,
            "timestamp_utc": er.timestamp_utc,
            "git": dict(er.git),
            "run": rr.resolved.run_dict,
            "vehicle": rr.resolved.vehicle_dict,
        },
    )
    write_json(
        out_dir / "metrics.json",
        {
            "experiment": er.experiment_name,
            "timestamp_utc": er.timestamp_utc,
            "git": dict(er.git),
            "run": rr.name,
            "baseline": baseline.name,
            "metrics": metrics_record(rr.result),
            "comparison": comparison.get(rr.name, {}),
        },
    )
    write_timeseries(rr.result, out_dir)
    if plots:
        write_plots(rr.result, out_dir / "plots", rr.name)
    single = ExperimentResult(
        experiment_name=er.experiment_name,
        vehicle_name=er.vehicle_name,
        baseline=baseline,
        variants={} if rr is baseline else {rr.name: rr},
        comparison=comparison,
        git=er.git,
        timestamp_utc=er.timestamp_utc,
        comparison_basis=er.comparison_basis,
    )
    write_summary(out_dir, experiment_summary(single, header_lines))
    return out_dir


# --------------------------------------------------------------------- entry points


def _repo_root_of(repo_root: Path | None) -> Path:
    return Path.cwd() if repo_root is None else Path(repo_root)


def run_experiment(
    resolved: ResolvedExperiment,
    out_root: Path,
    plots: bool,
    only_variant: str | None = None,
    repo_root: Path | None = None,
) -> tuple[ExperimentResult, Path]:
    """Run the baseline and every variant (or one), write the results, return them.

    Inputs: a ResolvedExperiment (from config.resolve_experiment), the results root, the
    plots switch, an optional single variant name, and the repository root for the git
    hash (default: the current directory). Output: the ExperimentResult and the run
    directory results/<experiment>/<timestamp>/, created before any run starts; an
    exception after that leaves FAILED.txt in it (write_failure_marker) and propagates.
    """
    exp = resolved.experiment
    variants = resolved.variants
    if only_variant is not None:
        if only_variant not in variants:
            raise ValueError(
                f"variant {only_variant!r} not in experiment {exp.name!r}: {sorted(variants)}"
            )
        variants = {only_variant: variants[only_variant]}
    check_result_names(resolved)
    git = git_info(_repo_root_of(repo_root))
    now = datetime.now(UTC)  # one clock read: the directory name and timestamp_utc agree
    out_dir = make_run_dir(Path(out_root), exp.name, now=now)
    try:
        baseline = run_resolved(resolved.baseline)
        variant_results = {name: run_resolved(r) for name, r in variants.items()}
        comparison = {
            name: compare(rr.result, baseline.result) for name, rr in variant_results.items()
        }
        er = ExperimentResult(
            experiment_name=exp.name,
            vehicle_name=resolved.baseline.vehicle.name,
            baseline=baseline,
            variants=variant_results,
            comparison=comparison,
            git=git,
            timestamp_utc=utc_timestamp(now),
        )
        write_run(er, out_dir, plots)
    except BaseException as exc:
        write_failure_marker(out_dir, exc)
        raise
    return er, out_dir


SWEEP_INDEX_FIXED_COLUMNS: tuple[str, ...] = ("point", "run_dir", "of", "status")


def sweep_index_frame(sweep: SweepResult, baseline: RunResult, root: Path) -> pd.DataFrame:
    """One row per sweep point: point, run_dir (relative to root), of, the axis values,
    status, every numeric metric (non-finite -> empty cell) and its delta against the
    baseline. Raises ValueError if a metric or delta key collides with a bookkeeping
    column (a programming error in the metrics schema, not a user error)."""
    rows = []
    bookkeeping = {*SWEEP_INDEX_FIXED_COLUMNS, *sweep.axes}
    for point, rr, comp, run_dir in zip(
        sweep.points, sweep.results, sweep.comparisons, sweep.run_dirs, strict=True
    ):
        row: dict[str, Any] = {
            "point": point.point_index,
            "run_dir": run_dir.relative_to(root).as_posix(),
            "of": sweep.of,
        }
        row.update({axis: point.overrides[axis] for axis in sweep.axes})
        row["status"] = rr.result.status
        values = {k: v for k, v in rr.result.metrics.items() if _is_numeric_or_missing(v)}
        values.update({k: v for k, v in comp.items() if k.startswith("delta_")})
        clash = sorted(bookkeeping & set(values))
        if clash:
            raise ValueError(f"sweep index: metric keys collide with index columns: {clash}")
        row.update({k: (v if _is_finite_number(v) else None) for k, v in values.items()})
        rows.append(row)
    return pd.DataFrame(rows)


def sweep_summary(
    exp_name: str,
    sweeps: list[SweepResult],
    frames: list[pd.DataFrame],
    baseline: RunResult,
    git: Mapping[str, Any],
    timestamp_utc: str,
) -> str:
    """The top-level summary.md text of a sweep run. The assumptions section is the
    union over the baseline and every sweep point (attributed as sweep_<n>/run_NNNN)."""
    parts = [
        f"# {exp_name}: sweeps",
        "",
        COMPARISON_BASIS,
        "",
        f"- Baseline: {baseline.name} (status {baseline.result.status})",
        provenance_lines(git, timestamp_utc),
        "",
    ]
    if not sweeps:
        parts.append("(no sweeps declared)")
    for sweep, frame in zip(sweeps, frames, strict=True):
        parts += [
            f"## sweep_{sweep.sweep_index}: {sweep.of} over {', '.join(sweep.axes)}",
            "",
        ]
        if frame.empty:
            parts += ["(no points)", ""]
            continue
        header = [str(c) for c in frame.columns]
        rows = [[_fmt(v) for v in rec] for rec in frame.itertuples(index=False, name=None)]
        parts += [_table(header, rows), ""]
    all_runs = {baseline.name: baseline}
    for sweep in sweeps:
        all_runs.update({f"sweep_{sweep.sweep_index}/{rr.name}": rr for rr in sweep.results})
    section = assumptions_section(all_runs, baseline.name, "all sweep points")
    parts += ["## Assumptions", "", section, ""]
    return "\n".join(parts)


def run_sweep(
    resolved: ResolvedExperiment,
    out_root: Path,
    plots: bool,
    repo_root: Path | None = None,
) -> tuple[list[SweepResult], Path]:
    """Run every sweep of an experiment and write the results.

    Layout: results/<experiment>/<timestamp>/baseline/ (the pad baseline, flat layout),
    sweep_<n>/run_NNNN/ per grid point (flat layout, compared against the baseline),
    sweep_<n>/sweep_index.csv and a top-level summary.md. Returns the SweepResults and
    the run directory, created before any run starts; an exception after that leaves
    FAILED.txt in it (write_failure_marker) and propagates.
    """
    exp = resolved.experiment
    check_result_names(resolved)
    git = git_info(_repo_root_of(repo_root))
    now = datetime.now(UTC)  # one clock read: the directory name and timestamp_utc agree
    timestamp = utc_timestamp(now)
    out_dir = make_run_dir(Path(out_root), exp.name, now=now)
    try:
        sweeps, frames, baseline = _run_sweeps_into(resolved, out_dir, plots, git, timestamp)
        write_summary(out_dir, sweep_summary(exp.name, sweeps, frames, baseline, git, timestamp))
    except BaseException as exc:
        write_failure_marker(out_dir, exc)
        raise
    return sweeps, out_dir


def _run_sweeps_into(
    resolved: ResolvedExperiment,
    out_dir: Path,
    plots: bool,
    git: Mapping[str, Any],
    timestamp: str,
) -> tuple[list[SweepResult], list[pd.DataFrame], RunResult]:
    """Run the baseline and every sweep point into an existing run directory (see
    run_sweep); returns the SweepResults, their index frames and the baseline."""
    exp = resolved.experiment
    baseline = run_resolved(resolved.baseline)
    er = ExperimentResult(
        experiment_name=exp.name,
        vehicle_name=resolved.baseline.vehicle.name,
        baseline=baseline,
        variants={},
        comparison={},
        git=dict(git),
        timestamp_utc=timestamp,
    )
    write_single(baseline, baseline, er, out_dir / "baseline", plots)

    sweeps: list[SweepResult] = []
    frames: list[pd.DataFrame] = []
    for k, points in enumerate(resolved.sweeps, start=1):
        if any(p.sweep_index != k - 1 for p in points):
            raise ValueError(f"sweep_{k}: config.SweepPoint.sweep_index is expected 0-based")
        sweep_dir = out_dir / f"sweep_{k}"
        axes = list(exp.sweeps[k - 1].axes)
        results: list[RunResult] = []
        comparisons: list[dict[str, Any]] = []
        run_dirs: list[Path] = []
        for point in points:
            rr = run_resolved(point.run)
            header = sweep_point_header(k, point, len(points))
            run_dir = write_single(rr, baseline, er, sweep_dir / point.run.name, plots, header)
            results.append(rr)
            comparisons.append(compare(rr.result, baseline.result))
            run_dirs.append(run_dir)
        sweep = SweepResult(k, exp.sweeps[k - 1].of, axes, points, results, comparisons, run_dirs)
        frame = sweep_index_frame(sweep, baseline, out_dir)
        sweep_dir.mkdir(parents=True, exist_ok=True)
        write_csv(sweep_dir / "sweep_index.csv", frame)
        sweeps.append(sweep)
        frames.append(frame)
    return sweeps, frames, baseline
