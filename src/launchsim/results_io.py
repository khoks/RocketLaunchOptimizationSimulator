"""Results I/O (moved from sim.py): names, run directories, git provenance, writers and
the ``run_experiment`` / ``run_sweep`` entry points the CLI calls (through ``sim``,
which re-exports every name).

The entry points run simulations through ``sim.run_resolved`` and read the git state
through ``sim.git_info``, and ``git_info`` runs git through ``sim._git``: all three are
looked up on the ``launchsim.sim`` module at call time, so a test that patches
``sim.run`` or ``sim._git`` changes what these functions execute. Every other function
they call (``compare``, ``run_sensitivity``, ``experiment_summary``, ``write_plots``,
``make_run_dir``, ``write_run``, ...) is bound here at import time: patch it on this
module (or its owning module), not on ``sim``, where a patch no longer reaches them.

``Result`` and ``RunResult`` are imported under ``TYPE_CHECKING`` only, so the string
annotations here (including the fields of ``ExperimentResult`` and ``SweepResult``) do
not resolve at run time; ``typing.get_type_hints`` needs ``localns=vars(launchsim.sim)``.

Results layout (never overwritten; CLAUDE.md)::

    results/<experiment>/<YYYYMMDDTHHMMSSZ>[-n]/
        resolved_config.yaml   experiment name, vehicle dict, every run dict, git, timestamp
        metrics.json           per-run metrics, the comparison against the baseline
                               (``compare``) and the sensitivity cases (``run_sensitivity``)
        summary.md             the per-variant table against the baseline, the sensitivity
                               table, the attributed assumptions and the identity checks
        <run>/timeseries.csv   sampled state (t_s, z_m, v_mps, m_kg, ...)
        <run>/events.csv       phase-boundary events (t_s, event, phase)
        plots/<run>_<quantity>.png  altitude, speed, mass_thrust, felt_g and, for a run
                               with a track phase, track_forces and drive_power (PLOT_PANELS)

Experiment and run names become directory names, so they must be single safe path
components (check_name); the CLI validates them before anything is written.

A sweep writes ``sweep_<n>/run_NNNN/`` (flat single-run layout: resolved_config.yaml,
metrics.json, summary.md, timeseries.csv, events.csv, plots/) plus
``sweep_<n>/sweep_index.csv`` and a top-level summary.md; the baseline it compares
against is written once under ``baseline/``.

A planar_2d experiment (``planar_experiment_result``) also writes, beside the runs,
every bound run and its paired baseline (``<of>__<bound>``, ``<baseline>__<bound>``)
and every calibration case (``<case>``), and its metrics.json and resolved_config.yaml
gain the model, the label, the search budget id, the bound records and the cases; a
point of a paired sweep has its paired baseline written beside it
(``sweep_<n>/run_NNNN__<baseline>/``). The comparisons are ``compare.compare_planar``
with the matched-payload runs executed here through ``sim.matched_run``.

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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
import yaml

from launchsim.compare import (
    CD_SENSITIVITY_NOTES,
    COMPARISON_BASIS,
    INSTANT_VARIANT_NAME,
    SENSITIVITY_NONE_DECLARED,
    SENSITIVITY_NONE_FOR_RUNS,
    SENSITIVITY_SKIPPED,
    SENSITIVITY_SWEEP_POINT,
    MatchedRun,
    SensitivityRow,
    _is_finite_number,
    _is_pandas_missing,
    anchor_from,
    attributed_comparison,
    compare,
    compare_planar,
    planar_comparison_basis,
    reference_payload_kg,
    run_sensitivity,
    sensitivity_record,
)
from launchsim.config import (
    CALIBRATION_LABEL,
    PLANAR_2D,
    VERTICAL_1D,
    ResolvedExperiment,
    SweepPoint,
)
from launchsim.metrics import metrics_record
from launchsim.plots import write_plots
from launchsim.summary import (
    experiment_summary,
    planar_sweep_summary,
    sweep_point_header,
    sweep_summary,
)

if TYPE_CHECKING:
    from launchsim.sim import Result, RunResult


TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"
GIT_TIMEOUT_S = 5.0
GIT_EXCLUDE_RESULTS = ":(exclude)results"  # pathspec: the results tree never counts as dirty
NOT_A_REPO_MARKER = "not a git repository"
CSV_FLOAT_FORMAT = "%.12g"
MAX_DIR_SUFFIX = 1000
FAILED_MARKER = "FAILED.txt"  # written into a run directory that raised before summary.md


# Metric columns of sweep_index.csv, after the axis values and the run directory.
SWEEP_INDEX_METRICS: tuple[str, ...] = (
    "exit_speed_mps",
    "stage1_burnout_speed_mps",
    "stage1_burnout_speed_delta_mps",
    "ignition_loss_formula_mps",
    "drive_energy_J",
    "drive_power_peak_W",
    "felt_g_track_peak",
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
    """Validate the experiment name and every name that becomes a results directory
    before anything is written: the baseline and variants, the calibration cases, the
    bound runs and their paired baselines, and the paired baselines of paired sweeps
    (``run_NNNN__<baseline>``, beside run_NNNN in its sweep directory); raises
    InvalidNameError naming the offender."""
    check_name(resolved.experiment.name, "experiment name")
    for name in resolved.runs:
        check_run_name(name)
    for name in resolved.cases:
        check_run_name(name)
    for bound in resolved.bounds:
        for run in (bound.baseline, *bound.runs.values()):
            check_run_name(run.name)
    for points in resolved.sweeps:
        for point in points:
            if point.paired_baseline is not None:
                check_run_name(point.paired_baseline.name)


@dataclass(frozen=True)
class BoundRow:
    """One run of a bound (amendment 6): the bound's name, the run it re-runs (``of``),
    its overrides, the re-run (``<of>__<bound>``) and the baseline re-run with the same
    overrides (its pair), the comparison against that pair and against the unchanged
    baseline (``compare.compare_planar``)."""

    bound: str
    of: str
    overrides: dict[str, Any]
    result: RunResult
    baseline: RunResult
    comparison: dict[str, Any]
    comparison_vs_nominal: dict[str, Any]


@dataclass(frozen=True)
class ExperimentResult:
    """Baseline, variants, their comparison, the sensitivity cases and the provenance of
    one experiment run. ``sensitivity_note`` is what the summary's Sensitivity section
    prints when ``sensitivity`` is empty (why no case ran: none declared, skipped, a
    sweep point). ``model`` is the dynamics model (vertical_1d; planar_2d adds
    ``label``, the experiment's label, ``bounds``, the BoundRows, ``cases``, the
    calibration cases run independently and never compared, and
    ``search_budget_id``, the shared budget's id). ``preregistration`` is the
    frozen-input state of a calibration run (``preregistration_state``), None for any
    other experiment."""

    experiment_name: str
    vehicle_name: str
    baseline: RunResult
    variants: dict[str, RunResult]
    comparison: dict[str, dict[str, Any]]
    git: dict[str, Any]
    timestamp_utc: str
    comparison_basis: str = COMPARISON_BASIS
    sensitivity: list[SensitivityRow] = field(default_factory=list)
    sensitivity_note: str = SENSITIVITY_NONE_DECLARED
    model: str = VERTICAL_1D
    label: str | None = None
    bounds: list[BoundRow] = field(default_factory=list)
    cases: dict[str, RunResult] = field(default_factory=dict)
    search_budget_id: str | None = None
    preregistration: dict[str, Any] | None = None

    @property
    def runs(self) -> dict[str, RunResult]:
        """Baseline first, then every variant, keyed by name."""
        return {self.baseline.name: self.baseline, **self.variants}


@dataclass(frozen=True)
class SweepResult:
    """One sweep: its 1-based index, the run it perturbs, the axis paths and the points.

    ``sweep_index`` is 1-based and names the ``sweep_<n>`` directory; it equals
    config.SweepPoint.sweep_index on every entry of ``points`` (checked by run_sweep).
    """

    sweep_index: int
    of: str
    axes: list[str]
    points: list[SweepPoint]
    results: list[RunResult]
    comparisons: list[dict[str, Any]]
    run_dirs: list[Path]
    paired: list[RunResult | None] = field(default_factory=list)


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
    Never raises. Git runs through ``sim._git``, looked up at call time.
    """
    from launchsim import sim  # late: sim imports this module

    try:
        inside = sim._git(["rev-parse", "--is-inside-work-tree"], repo_root)
        top = (
            Path(sim._git(["rev-parse", "--show-toplevel"], repo_root))
            if inside == "true"
            else None
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return {"hash": "no-git", "dirty": False, "error": f"{type(exc).__name__}: {exc}"}
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        error = None if not stderr or NOT_A_REPO_MARKER in stderr else stderr
        return {"hash": "no-git", "dirty": False, "error": error}
    if top is None:  # inside a bare repository: no work tree, nothing to describe
        return {"hash": "no-git", "dirty": False, "error": None}
    try:
        sha = sim._git(["rev-parse", "--short=12", "HEAD"], top)
    except subprocess.CalledProcessError:
        sha = "unborn"
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"hash": "no-git", "dirty": False, "error": f"{type(exc).__name__}: {exc}"}
    try:
        dirty: bool | None = bool(
            sim._git(["status", "--porcelain", "--", ".", GIT_EXCLUDE_RESULTS], top)
        )
        error = None
    except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
        dirty, error = None, f"git status failed: {type(exc).__name__}: {exc}"
    return {"hash": sha, "dirty": dirty, "error": error}


PREREGISTERED_PATHS: tuple[str, ...] = ("configs", "experiments")
"""Repository paths that hold a calibration run's frozen inputs (plan amendment 1)."""


def _porcelain_path(line: str) -> str:
    """The path of one ``git status --porcelain`` line (its leading status code dropped;
    robust to the leading blank that ``_git``'s strip removes from the first line)."""
    parts = line.split(maxsplit=1)
    return parts[1] if len(parts) == 2 else parts[0]


def preregistration_state(
    repo_root: Path, paths: Sequence[str] = PREREGISTERED_PATHS
) -> dict[str, Any]:
    """The frozen-input state of a calibration run (plan amendment 1), for provenance.

    Inputs: a directory inside the repository and the pre-registered paths (relative to
    the repository top level). Returns ``{"inputs_commit": "<sha12>" | None, "dirty":
    bool | None, "dirty_paths": [str, ...], "error": str | None}``: the last commit that
    touched ``paths`` (None when there is none), whether any of them has uncommitted or
    untracked changes, which ones, and git's failure when ``dirty`` is None (git missing,
    not a repository, timeout). A dirty or unknown state means the run is not a valid
    calibration record. Never raises; git runs through ``sim._git``.
    """
    from launchsim import sim  # late: sim imports this module

    failures = (
        FileNotFoundError,
        OSError,
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
    )
    try:
        top = Path(sim._git(["rev-parse", "--show-toplevel"], repo_root))
    except failures as exc:
        return _prereg_record(None, None, [], f"{type(exc).__name__}: {exc}")
    try:
        commit = sim._git(["log", "-1", "--abbrev=12", "--format=%h", "--", *paths], top)
    except failures:
        commit = ""
    try:
        status = sim._git(["status", "--porcelain", "--untracked-files=all", "--", *paths], top)
    except failures as exc:
        return _prereg_record(commit or None, None, [], f"{type(exc).__name__}: {exc}")
    dirty_paths = [_porcelain_path(line) for line in status.splitlines() if line.strip()]
    return _prereg_record(commit or None, bool(dirty_paths), dirty_paths, None)


def _prereg_record(
    commit: str | None, dirty: bool | None, dirty_paths: list[str], error: str | None
) -> dict[str, Any]:
    """The record ``preregistration_state`` returns (keys in a fixed order)."""
    return {"inputs_commit": commit, "dirty": dirty, "dirty_paths": dirty_paths, "error": error}


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
    out: dict[str, Any] = {
        "experiment": er.experiment_name,
        "timestamp_utc": er.timestamp_utc,
        "git": dict(er.git),
        "comparison_basis": er.comparison_basis,
        "baseline": er.baseline.name,
        "vehicle": base_vehicle,
        "runs": runs,
    }
    if er.model == PLANAR_2D:
        out["model"] = er.model
        out["label"] = er.label
        out["bound_runs"] = {
            rr.name: _run_entry(rr, base_vehicle) for rr in _bound_runs(er).values()
        }
        out["cases"] = {name: _run_entry(rr, base_vehicle) for name, rr in er.cases.items()}
    return out


def _run_entry(rr: RunResult, base_vehicle: Mapping[str, Any]) -> dict[str, Any]:
    """The resolved_config entry of one run: its run dict, and its vehicle dict when it
    differs from the experiment's."""
    entry: dict[str, Any] = {"run": rr.resolved.run_dict}
    if rr.resolved.vehicle_dict != base_vehicle:
        entry["vehicle"] = rr.resolved.vehicle_dict
    return entry


def _bound_runs(er: ExperimentResult) -> dict[str, RunResult]:
    """Every run of the experiment's bounds (the re-runs and their paired baselines),
    keyed by name, in declaration order."""
    out: dict[str, RunResult] = {}
    for row in er.bounds:
        out.setdefault(row.baseline.name, row.baseline)
        out.setdefault(row.result.name, row.result)
    return out


def _bound_record(row: BoundRow) -> dict[str, Any]:
    """The metrics.json record of one bound run: names, overrides, both metrics records
    and both comparisons."""
    return {
        "bound": row.bound,
        "of": row.of,
        "overrides": row.overrides,
        "run": row.result.name,
        "paired_baseline": row.baseline.name,
        "metrics": metrics_record(row.result.result),
        "paired_baseline_metrics": metrics_record(row.baseline.result),
        "comparison_vs_paired_baseline": row.comparison,
        "comparison_vs_baseline": row.comparison_vs_nominal,
    }


def _metrics_dict(er: ExperimentResult) -> dict[str, Any]:
    """The metrics.json content; a planar experiment adds its model, label, search
    budget id, the bound records and the calibration cases (metrics only)."""
    out: dict[str, Any] = {
        "experiment": er.experiment_name,
        "timestamp_utc": er.timestamp_utc,
        "git": dict(er.git),
        "comparison_basis": er.comparison_basis,
        "baseline": er.baseline.name,
        "runs": {name: metrics_record(rr.result) for name, rr in er.runs.items()},
        "comparison": er.comparison,
        "sensitivity": [sensitivity_record(row) for row in er.sensitivity],
    }
    if er.model == PLANAR_2D:
        out["model"] = er.model
        out["label"] = er.label
        out["search_budget_id"] = er.search_budget_id
        out["bounds"] = [_bound_record(row) for row in er.bounds]
        out["cases"] = {name: metrics_record(rr.result) for name, rr in er.cases.items()}
        if er.preregistration is not None:
            out["preregistration"] = dict(er.preregistration)
    return out


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
    extra = {**_bound_runs(er), **er.cases} if er.model == PLANAR_2D else {}
    for name, rr in extra.items():
        check_run_name(name)
        write_timeseries(rr.result, out_dir / name)
        if plots:
            write_plots(rr.result, out_dir / "plots", name)
    write_summary(out_dir, experiment_summary(er))
    return out_dir


def write_single(
    run_result: RunResult,
    baseline: RunResult,
    er: ExperimentResult,
    out_dir: Path,
    plots: bool,
    header_lines: Sequence[str] = (),
    comparison: Mapping[str, Any] | None = None,
) -> Path:
    """Flat single-run layout for a sweep point (or the sweep's baseline copy):
    resolved_config.yaml, metrics.json, summary.md, timeseries.csv, events.csv, plots/.
    ``header_lines`` (see sweep_point_header) name the point in its summary.md;
    ``comparison`` is the point's ``compare`` dict against the baseline when the caller
    already has it (the sweep index uses the same one), computed here otherwise; the
    baseline copy has none. A sweep point runs no sensitivity case, and its summary
    says so (SENSITIVITY_SWEEP_POINT)."""
    out_dir = Path(out_dir)
    rr = run_result
    check_name(rr.name, "run name")  # sweep points are run_NNNN, so no reserved check here
    out_dir.mkdir(parents=True, exist_ok=True)
    if rr is baseline:
        comparison = {}
    elif comparison is None and rr.result.model == PLANAR_2D:
        checks = rr.resolved.run.planar.checks  # type: ignore[union-attr]
        comparison = {
            rr.name: compare_planar(
                rr.result, baseline.result, rr.resolved.to_vehicle(), checks=checks, name=rr.name
            )
        }
    elif comparison is None:
        comparison = {rr.name: compare(rr.result, baseline.result, rr.resolved.to_vehicle())}
    else:
        comparison = {rr.name: dict(comparison)}
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
        sensitivity_note=SENSITIVITY_SWEEP_POINT,
        model=er.model,
        label=er.label,
        search_budget_id=er.search_budget_id,
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
    sensitivity: bool = True,
) -> tuple[ExperimentResult, Path]:
    """Run the baseline and every variant (or one), the sensitivity cases of the runs
    that ran (``run_sensitivity``, unless ``sensitivity`` is False), write the results,
    return them.

    Inputs: a ResolvedExperiment (from config.resolve_experiment), the results root, the
    plots switch, an optional single variant name, the repository root for the git
    hash (default: the current directory) and the sensitivity switch. Output: the
    ExperimentResult and the run directory results/<experiment>/<timestamp>/, created
    before any run starts; an exception after that leaves FAILED.txt in it
    (write_failure_marker) and propagates. Every variant is compared with ``compare``
    against the baseline, with its own vehicle and, when the experiment has a variant
    named INSTANT_VARIANT_NAME, that run as the integrated ignition-loss yardstick.
    When no sensitivity case ran, ``ExperimentResult.sensitivity_note`` says why
    (skipped, none declared, or none for the variants that ran).
    """
    from launchsim import sim  # late: sim imports this module

    exp = resolved.experiment
    variants = resolved.variants
    if only_variant is not None:
        if only_variant not in variants:
            raise ValueError(
                f"variant {only_variant!r} not in experiment {exp.name!r}: {sorted(variants)}"
            )
        variants = {only_variant: variants[only_variant]}
    check_result_names(resolved)
    git = sim.git_info(_repo_root_of(repo_root))
    now = datetime.now(UTC)  # one clock read: the directory name and timestamp_utc agree
    out_dir = make_run_dir(Path(out_root), exp.name, now=now)
    try:
        baseline = sim.run_resolved(resolved.baseline)
        variant_results = {name: sim.run_resolved(r) for name, r in variants.items()}
        if is_planar(resolved):
            er = planar_experiment_result(
                resolved,
                baseline,
                variant_results,
                git,
                utc_timestamp(now),
                sensitivity=sensitivity,
                run_cases=only_variant is None,
            )
            if exp.label == CALIBRATION_LABEL:
                er = replace(er, preregistration=preregistration_state(_repo_root_of(repo_root)))
            write_run(er, out_dir, plots)
            return er, out_dir
        instant = variant_results.get(INSTANT_VARIANT_NAME)
        comparison = {
            name: compare(
                rr.result,
                baseline.result,
                rr.resolved.to_vehicle(),
                None if instant is None else instant.result,
            )
            for name, rr in variant_results.items()
        }
        rows = (
            run_sensitivity(resolved, baseline, {baseline.name, *variant_results})
            if sensitivity
            else []
        )
        if not sensitivity:
            note = SENSITIVITY_SKIPPED
        elif not resolved.sensitivity:
            note = SENSITIVITY_NONE_DECLARED
        else:
            note = SENSITIVITY_NONE_FOR_RUNS  # declared, but for variants that did not run
        er = ExperimentResult(
            experiment_name=exp.name,
            vehicle_name=resolved.baseline.vehicle.name,
            baseline=baseline,
            variants=variant_results,
            comparison=comparison,
            git=git,
            timestamp_utc=utc_timestamp(now),
            sensitivity=rows,
            sensitivity_note=note,
        )
        write_run(er, out_dir, plots)
    except BaseException as exc:
        write_failure_marker(out_dir, exc)
        raise
    return er, out_dir


SWEEP_INDEX_FIXED_COLUMNS: tuple[str, ...] = ("point", "run_dir", "of", "status")
PLANAR_SWEEP_INDEX_METRICS: tuple[str, ...] = (
    "exit_speed_mps",
    "payload_kg",
    "payload_delta_kg",
    "ideal_screening_payload_at_release_speed_at_pbase_kg",
    "screening_yardstick_kg",
    "payload_beyond_screening_kg",
    "gamma_star_rad",
    "speed_at_kick_mps",
    "peak_q_alpha",
    "delta_peak_q_alpha",
    "max_q_pa",
    "delta_max_q_pa",
    "facility_length_m",
    "drive_energy_J",
    "drive_power_peak_W",
)
"""Numeric columns of a planar sweep_index.csv (point metrics, or its comparison against
its baseline: the experiment's, or the paired baseline of a paired sweep)."""
PLANAR_SWEEP_INDEX_TEXT: tuple[str, ...] = (
    "kick_regime",
    "unconstrained_kick",
    "payload_delta_upper_bound",
    "search_status",
    "screening_status",
)
"""Text columns of a planar sweep_index.csv: the kick regime per point (plan decision 5),
whether the kick is faster than checks.unconstrained_kick_mps and whether the dP* is an
unthrottled/unconstrained upper bound (True/False), the search status and the screening
status (bug_suspect blocks findings; not_checked has no attribution)."""
PLANAR_SWEEP_PAIRED_COLUMN = "paired_baseline"
"""Column naming each point's paired baseline (empty for an unpaired sweep)."""


def is_planar(resolved: ResolvedExperiment) -> bool:
    """True for a planar_2d experiment (its baseline's dynamics)."""
    return resolved.baseline.run.dynamics == PLANAR_2D


def shared_basis(resolved: ResolvedExperiment) -> str:
    """The comparison basis line of a planar experiment (``compare.planar_comparison_basis``
    of its shared figure of merit: fixed guidance or sweep-optimized)."""
    planar = resolved.baseline.run.planar
    return planar_comparison_basis(None if planar is None else planar.search.figure_of_merit)


def planar_comparisons(
    resolved: ResolvedExperiment,
    baseline: RunResult,
    runs: Mapping[str, RunResult],
    *,
    with_anchor: bool = True,
) -> dict[str, dict[str, Any]]:
    """The ``compare_planar`` of every planar run against the baseline: the rung-2 runs
    at the matched payload P_ref (``compare.reference_payload_kg`` of the baseline)
    executed here through ``sim.matched_run`` (amendment 16: compare stays pure), each
    run's with its gamma* neighbours (the gamma*-sensitivity diagnostic), and the M5
    anchor of silo_instant and pad_instant when both ran (``compare.anchor_from``)."""
    from launchsim import sim  # late: sim imports this module

    checks = baseline.resolved.run.planar.checks  # type: ignore[union-attr]
    p_ref = reference_payload_kg(baseline)
    base_matched = sim.matched_run(baseline.resolved, baseline.result, p_ref)
    anchor = None
    if with_anchor:
        results = {name: rr.result for name, rr in runs.items()}
        anchor = anchor_from(results, baseline.result, baseline.resolved.to_vehicle())
    out: dict[str, dict[str, Any]] = {}
    for name, rr in runs.items():
        matched: MatchedRun | None = None
        if base_matched is not None:
            matched = sim.matched_run(rr.resolved, rr.result, p_ref, neighbours=True)
        out[name] = compare_planar(
            rr.result,
            baseline.result,
            rr.resolved.to_vehicle(),
            checks=checks,
            name=name,
            matched=matched,
            matched_baseline=base_matched,
            anchor=anchor,
        )
    return out


def planar_bounds(
    resolved: ResolvedExperiment, baseline: RunResult, ran: set[str]
) -> list[BoundRow]:
    """Run every bound of the experiment whose ``of`` runs ran (amendment 6): the
    baseline re-run with the bound's overrides once per bound (its pair), each listed
    run re-run with them, compared with the pair (one vehicle: the matched-payload
    attribution is required, ``compare.attributed_comparison``, so a bound that beats
    its yardstick is explained or bug_suspect) and with the unchanged baseline (two
    vehicles: not attributed, not_checked)."""
    from launchsim import sim  # late: sim imports this module

    checks = baseline.resolved.run.planar.checks  # type: ignore[union-attr]
    rows: list[BoundRow] = []
    for bound in resolved.bounds:
        listed = {of: run for of, run in bound.runs.items() if of in ran}
        if not listed:
            continue
        pair = sim.run_resolved(bound.baseline)
        for of, run in listed.items():
            rr = sim.run_resolved(run)
            vehicle = run.to_vehicle()
            rows.append(
                BoundRow(
                    bound=bound.name,
                    of=of,
                    overrides=dict(bound.overrides),
                    result=rr,
                    baseline=pair,
                    comparison=attributed_comparison(rr, pair, checks, of),
                    comparison_vs_nominal=compare_planar(
                        rr.result,
                        baseline.result,
                        vehicle,
                        checks=checks,
                        name=of,
                        attribution_required=False,
                    ),
                )
            )
    return rows


def planar_experiment_result(
    resolved: ResolvedExperiment,
    baseline: RunResult,
    variants: dict[str, RunResult],
    git: dict[str, Any],
    timestamp_utc: str,
    *,
    sensitivity: bool,
    run_cases: bool,
) -> ExperimentResult:
    """The ExperimentResult of a planar experiment whose baseline and variants ran:
    the comparisons (``planar_comparisons``), the sensitivity cases (``run_sensitivity``
    with the runs already flown as the memo's nominal runs, unless ``sensitivity`` is
    False), the bounds (``planar_bounds``) and, with run_cases, the calibration cases
    (independent runs, never compared)."""
    from launchsim import sim  # late: sim imports this module

    ran = {baseline.name, *variants}
    rows = (
        run_sensitivity(resolved, baseline, ran, nominal={baseline.name: baseline, **variants})
        if sensitivity
        else []
    )
    cd_note = CD_SENSITIVITY_NOTES[PLANAR_2D]
    if not sensitivity:
        note = SENSITIVITY_SKIPPED
    elif not resolved.sensitivity:
        note = f"(no sensitivity block declared; C_D: {cd_note})"
    else:
        note = f"(no sensitivity cases declared for the runs that ran; C_D: {cd_note})"
    cases = {n: sim.run_resolved(r) for n, r in resolved.cases.items()} if run_cases else {}
    planar = resolved.baseline.run.planar
    return ExperimentResult(
        experiment_name=resolved.experiment.name,
        vehicle_name=resolved.baseline.vehicle.name,
        baseline=baseline,
        variants=variants,
        comparison=planar_comparisons(resolved, baseline, variants),
        git=git,
        timestamp_utc=timestamp_utc,
        comparison_basis=shared_basis(resolved),
        sensitivity=rows,
        sensitivity_note=note,
        model=PLANAR_2D,
        label=resolved.experiment.label,
        bounds=planar_bounds(resolved, baseline, ran),
        cases=cases,
        search_budget_id=None if planar is None else planar.search.budget_id(),
    )


def planar_sweep_index_frame(sweep: SweepResult, root: Path) -> pd.DataFrame:
    """One row per planar sweep point: point, the axis values, run_dir (relative to
    root), of, the paired baseline's name (empty unless paired), the
    PLANAR_SWEEP_INDEX_METRICS (the point's metrics, or its comparison against its
    baseline; non-finite or absent -> empty cell), the PLANAR_SWEEP_INDEX_TEXT and
    status. ValueError when an axis path collides with a column."""
    fixed = {*SWEEP_INDEX_FIXED_COLUMNS, PLANAR_SWEEP_PAIRED_COLUMN}
    clash = sorted(
        {*fixed, *PLANAR_SWEEP_INDEX_METRICS, *PLANAR_SWEEP_INDEX_TEXT} & set(sweep.axes)
    )
    if clash:
        raise ValueError(f"sweep index: axis paths collide with index columns: {clash}")
    paired = sweep.paired or [None] * len(sweep.points)
    rows = []
    for point, rr, comp, run_dir, pair in zip(
        sweep.points, sweep.results, sweep.comparisons, sweep.run_dirs, paired, strict=True
    ):
        row: dict[str, Any] = {"point": point.point_index}
        row.update({axis: point.overrides[axis] for axis in sweep.axes})
        row["run_dir"] = run_dir.relative_to(root).as_posix()
        row["of"] = sweep.of
        row[PLANAR_SWEEP_PAIRED_COLUMN] = None if pair is None else pair.name
        for key in PLANAR_SWEEP_INDEX_METRICS:
            value = comp.get(key) if key in comp else rr.result.metrics.get(key)
            row[key] = value if _is_finite_number(value) else None
        for key in PLANAR_SWEEP_INDEX_TEXT:
            value = comp.get(key) if key in comp else rr.result.metrics.get(key)
            row[key] = None if value is None else str(value)
        row["status"] = rr.result.status
        rows.append(row)
    columns = [
        "point",
        *sweep.axes,
        "run_dir",
        "of",
        PLANAR_SWEEP_PAIRED_COLUMN,
        *PLANAR_SWEEP_INDEX_METRICS,
        *PLANAR_SWEEP_INDEX_TEXT,
        "status",
    ]
    return pd.DataFrame(rows, columns=columns)


def sweep_index_frame(sweep: SweepResult, baseline: RunResult, root: Path) -> pd.DataFrame:
    """One row per sweep point: point, the axis values, run_dir (relative to root), of,
    the SWEEP_INDEX_METRICS (from the point's metrics, or its comparison against the
    baseline for the delta; non-finite or absent -> empty cell) and status. Raises
    ValueError if an axis path collides with a fixed or metric column (a programming
    error in the schema, not a user error). A planar sweep (the baseline's model) gets
    ``planar_sweep_index_frame``."""
    if baseline.result.model == PLANAR_2D:
        return planar_sweep_index_frame(sweep, root)
    clash = sorted({*SWEEP_INDEX_FIXED_COLUMNS, *SWEEP_INDEX_METRICS} & set(sweep.axes))
    if clash:
        raise ValueError(f"sweep index: axis paths collide with index columns: {clash}")
    rows = []
    for point, rr, comp, run_dir in zip(
        sweep.points, sweep.results, sweep.comparisons, sweep.run_dirs, strict=True
    ):
        row: dict[str, Any] = {"point": point.point_index}
        row.update({axis: point.overrides[axis] for axis in sweep.axes})
        row["run_dir"] = run_dir.relative_to(root).as_posix()
        row["of"] = sweep.of
        for key in SWEEP_INDEX_METRICS:
            value = comp.get(key) if key in comp else rr.result.metrics.get(key)
            row[key] = value if _is_finite_number(value) else None
        row["status"] = rr.result.status
        rows.append(row)
    columns = ["point", *sweep.axes, "run_dir", "of", *SWEEP_INDEX_METRICS, "status"]
    return pd.DataFrame(rows, columns=columns)


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
    from launchsim import sim  # late: sim imports this module

    exp = resolved.experiment
    check_result_names(resolved)
    git = sim.git_info(_repo_root_of(repo_root))
    now = datetime.now(UTC)  # one clock read: the directory name and timestamp_utc agree
    timestamp = utc_timestamp(now)
    out_dir = make_run_dir(Path(out_root), exp.name, now=now)
    try:
        sweeps, frames, baseline = _run_sweeps_into(resolved, out_dir, plots, git, timestamp)
        if is_planar(resolved):
            text = planar_sweep_summary(exp.name, sweeps, frames, baseline, git, timestamp)
        else:
            text = sweep_summary(exp.name, sweeps, frames, baseline, git, timestamp)
        write_summary(out_dir, text)
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
    run_sweep); returns the SweepResults, their index frames and the baseline. A planar
    point of a paired sweep is compared with its paired baseline (run once per point
    and written beside it as ``run_NNNN__<baseline>``), every other point with the
    experiment's baseline; planar comparisons carry the matched-payload attribution
    (``planar_comparisons``)."""
    from launchsim import sim  # late: sim imports this module

    exp = resolved.experiment
    baseline = sim.run_resolved(resolved.baseline)
    planar = is_planar(resolved)
    extra: dict[str, Any] = {}
    if planar:
        shared = resolved.baseline.run.planar
        extra = {
            "comparison_basis": shared_basis(resolved),
            "model": PLANAR_2D,
            "label": exp.label,
            "search_budget_id": None if shared is None else shared.search.budget_id(),
        }
    er = ExperimentResult(
        experiment_name=exp.name,
        vehicle_name=resolved.baseline.vehicle.name,
        baseline=baseline,
        variants={},
        comparison={},
        git=dict(git),
        timestamp_utc=timestamp,
        **extra,
    )
    write_single(baseline, baseline, er, out_dir / "baseline", plots)

    sweeps: list[SweepResult] = []
    frames: list[pd.DataFrame] = []
    for k, points in enumerate(resolved.sweeps, start=1):
        if any(p.sweep_index != k for p in points):
            raise ValueError(f"sweep_{k}: config.SweepPoint.sweep_index must equal {k}")
        sweep_dir = out_dir / f"sweep_{k}"
        axes = list(exp.sweeps[k - 1].axes)
        results: list[RunResult] = []
        comparisons: list[dict[str, Any]] = []
        run_dirs: list[Path] = []
        paired: list[RunResult | None] = []
        for point in points:
            rr = sim.run_resolved(point.run)
            header = sweep_point_header(k, point, len(points))
            ref, pair = baseline, None
            if planar and point.paired_baseline is not None:
                pair = sim.run_resolved(point.paired_baseline)
                write_single(pair, pair, er, sweep_dir / pair.name, plots)
                ref = pair
            if planar:
                comparison = planar_comparisons(resolved, ref, {rr.name: rr}, with_anchor=False)[
                    rr.name
                ]
            else:
                comparison = compare(rr.result, baseline.result, point.run.to_vehicle())
            run_dir = write_single(
                rr, ref, er, sweep_dir / point.run.name, plots, header, comparison
            )
            results.append(rr)
            comparisons.append(comparison)
            run_dirs.append(run_dir)
            paired.append(pair)
        sweep = SweepResult(
            k, exp.sweeps[k - 1].of, axes, points, results, comparisons, run_dirs, paired
        )
        frame = sweep_index_frame(sweep, baseline, out_dir)
        sweep_dir.mkdir(parents=True, exist_ok=True)
        write_csv(sweep_dir / "sweep_index.csv", frame)
        sweeps.append(sweep)
        frames.append(frame)
    return sweeps, frames, baseline
