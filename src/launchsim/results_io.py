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

An experiment with an ``offload`` block (SP1 step 7; ``planar_offload``) also writes
the block's runs (each case's recorded run ``<case>``, each paired pad
``<case>__<baseline>``, each pad control ``<baseline>__offload_<mode>``), metrics.json
gains the ``offload`` record (``offload_record``), resolved_config.yaml ``offload_runs``
and summary.md the section "Propellant saved at fixed payload"; a planar sweep that
names offload cases adds their columns to sweep_index.csv (``offload_sweep_point``).
Without the block none of these is written. ``planar_experiment_result`` and
``planar_offload`` write nothing (an in-memory caller gets the whole result).

Both entry points first check the names and run the preflight ``sim.check_resolved``
(the assist model and the ignition specs of every resolved run built, nothing
integrated), so a configuration refused there writes nothing; then they create the run
directory before simulating anything, so an unwritable results root fails before a
long run starts. summary.md is written last; if anything
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
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
import yaml

from launchsim.compare import (
    CD_SENSITIVITY_NOTES,
    CHECK_FAIL,
    CHECK_NA,
    CHECK_PASS,
    COMPARISON_BASIS,
    INSTANT_VARIANT_NAME,
    OFFLOAD_COMPARISON_BASIS,
    OFFLOAD_SENSITIVITY_BASIS,
    PAD_CONTROL_NO_BOUND,
    SENSITIVITY_NONE_DECLARED,
    SENSITIVITY_NONE_FOR_RUNS,
    SENSITIVITY_SKIPPED,
    SENSITIVITY_SWEEP_POINT,
    MatchedRun,
    SensitivityRow,
    _delta,
    _is_finite_number,
    _is_pandas_missing,
    anchor_from,
    attributed_comparison,
    compare,
    compare_planar,
    cross_vehicle_decomposition,
    offload_energy,
    offload_matched_run,
    planar_comparison_basis,
    reference_payload_kg,
    run_sensitivity,
    sensitivity_record,
    trajectory_key,
)
from launchsim.config import (
    CALIBRATION_LABEL,
    OFFLOAD_GROSS_MODES,
    OFFLOAD_STAGE1_INDEX,
    OFFLOAD_STAGE2_INDEX,
    PLANAR_2D,
    VERTICAL_1D,
    ChecksConfig,
    OffloadEnergyConfig,
    ResolvedExperiment,
    ResolvedOffload,
    ResolvedOffloadArm,
    ResolvedOffloadCase,
    ResolvedRun,
    SweepPoint,
    offload_run_names,
    offload_solved_run,
    pad_control_run_name,
)
from launchsim.metrics import metrics_record
from launchsim.offload import (
    NO_OFFLOAD_STATUS,
    OffloadResult,
    residual_slope_kg_per_kg,
    verification_from_record,
    with_verification,
)
from launchsim.plots import CALIBRATION_RECORDS, write_plots
from launchsim.search import OK_STATUS, as_plain
from launchsim.summary import (
    OFFLOAD_SECTION_NAME,
    experiment_summary,
    offload_caveats,
    planar_sweep_summary,
    sweep_point_header,
    sweep_summary,
)
from launchsim.units import t_to_kg
from launchsim.vehicle import offload_split_kg

if TYPE_CHECKING:
    from launchsim.sim import Result, RunResult
    from launchsim.vehicle import Vehicle


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
    bound runs and their paired baselines, the paired baselines of paired sweeps
    (``run_NNNN__<baseline>``, beside run_NNNN in its sweep directory) and the runs of
    the offload block (each case's name, ``<case>__<baseline>`` of a paired pad,
    ``<baseline>__offload_<mode>`` of a pad control: ``config.offload_run_names``, each
    within MAX_NAME_LEN); raises InvalidNameError naming the offender."""
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
    if resolved.offload is not None:
        for name in offload_run_names(resolved.offload.config, resolved.baseline.name):
            check_name(name, "offload run name", RESERVED_RUN_NAME_PATTERN)


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
class OffloadReport:
    """The offload block of a planar experiment (SP1 step 7; ``planar_offload``):
    ``record``, the metrics.json ``offload`` record without its runs (plain data: the
    basis, the reference payload, the caveats, the energy inputs, the pad controls, the
    cases, the sensitivity arms, the notes; or ``skipped`` with the reason); ``runs``,
    the runs it writes (each case's recorded run, the paired pads, the pad controls'
    recorded runs), by name; ``checked_runs``, every run whose per-run checks the
    summary's Checks section lists besides those (the verification searches, the
    sensitivity arms' recorded runs), by label."""

    record: dict[str, Any]
    runs: dict[str, RunResult] = field(default_factory=dict)
    checked_runs: dict[str, RunResult] = field(default_factory=dict)


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
    other experiment. ``offload`` is the OffloadReport of the experiment's offload block
    (None when it declares none: then nothing of it is written)."""

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
    offload: OffloadReport | None = None

    @property
    def runs(self) -> dict[str, RunResult]:
        """Baseline first, then every variant, keyed by name."""
        return {self.baseline.name: self.baseline, **self.variants}

    @property
    def offload_runs(self) -> dict[str, RunResult]:
        """The runs the offload block writes, by name ({} without the block)."""
        return {} if self.offload is None else dict(self.offload.runs)


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
    offload: list[dict[str, dict[str, Any]]] = field(default_factory=list)
    """Per point, the offload records of the cases the sweep names (case name -> the
    record ``planar_offload`` gives a case; empty lists when it names none)."""
    offload_runs: list[dict[str, RunResult]] = field(default_factory=list)
    """Per point, the offload runs whose per-run checks the sweep summary lists."""


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
    vehicle dict again only for runs whose vehicle differs (sensitivity, vehicle sweeps);
    a planar experiment adds its bound runs and cases and, with an offload block, the
    offload runs it writes (``offload_runs``: each with its offloaded vehicle dict)."""
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
        if er.offload is not None:
            out["offload_runs"] = {
                name: _run_entry(rr, base_vehicle) for name, rr in er.offload_runs.items()
            }
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
    budget id, the bound records and the calibration cases (metrics only) and, only with
    an offload block, the ``offload`` record (``offload_record``)."""
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
        if er.offload is not None:
            out["offload"] = offload_record(er.offload)
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
    extra = {**_bound_runs(er), **er.cases, **er.offload_runs} if er.model == PLANAR_2D else {}
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
    offload: bool = True,
) -> tuple[ExperimentResult, Path]:
    """Run the baseline and every variant (or one), the sensitivity cases of the runs
    that ran (``run_sensitivity``, unless ``sensitivity`` is False), a planar
    experiment's offload block (``planar_offload``, unless ``offload`` is False; its
    sensitivity arms follow ``sensitivity``), write the results, return them.

    Inputs: a ResolvedExperiment (from config.resolve_experiment), the results root, the
    plots switch, an optional single variant name, the repository root for the git
    hash (default: the current directory), the sensitivity switch and the offload
    switch. Output: the ExperimentResult and the run directory
    results/<experiment>/<timestamp>/, created before any run starts and after the
    preflight (``sim.check_resolved``: every resolved run's specs, so a refused
    configuration leaves no directory); an exception after that leaves FAILED.txt in it
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
    sim.check_resolved(resolved)  # every run's specs build: a bad config writes nothing
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
                offload=offload,
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
    "screening_diagnostic_failed",
)
"""Text columns of a planar sweep_index.csv: the kick regime per point (plan decision 5),
whether the kick is faster than checks.unconstrained_kick_mps and whether the dP* is an
unthrottled/unconstrained upper bound (True/False), the search status, the screening
status (bug_suspect blocks findings; not_checked has no attribution) and the failed
diagnostic checks (M2 with checks.m2_role diagnostic: reported, blocking nothing, so a
point whose status is ok still shows its M2 fail; ``none`` when none failed; a list is
written by ``index_text``)."""
INDEX_LIST_SEPARATOR = "; "
"""Separator of a list-valued text cell of sweep_index.csv (``index_text``)."""
INDEX_EMPTY_LIST_TEXT = "none"
"""Text cell of an empty list in sweep_index.csv (``index_text``)."""


def index_text(value: Any) -> str | None:
    """One text cell of a planar sweep_index.csv: None stays None (an empty cell), a list
    or tuple is joined with INDEX_LIST_SEPARATOR (INDEX_EMPTY_LIST_TEXT when empty), any
    other value is ``str(value)``."""
    if value is None:
        return None
    if isinstance(value, list | tuple):
        return INDEX_LIST_SEPARATOR.join(str(v) for v in value) or INDEX_EMPTY_LIST_TEXT
    return str(value)


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


# ------------------------------------------------------------- offload (SP1 step 7)

OFFLOAD_SKIPPED = "(offload block declared but skipped: --no-offload)"
"""What the offload record and summary say when the block was skipped."""
OFFLOAD_ARMS_SKIPPED = "(offload sensitivity arms skipped: --no-sensitivity)"
"""What they say about the sensitivity arms of a run with --no-sensitivity."""
OFFLOAD_NOT_RUN = "not run: its variant did not run (launchsim run --variant)"
"""The note of a case whose variant was left out of the run."""
REFERENCE_FAILED_STATUS = "reference_failed"
"""Status of an offload pass or arm whose reference pad has no payload capacity P* (its
search did not end ok): there is no reference payload to solve at, so nothing is
solved."""
OFFLOAD_QUOTED_HEADLINE = "x* at P_ref, gross: stage 1, the headline"
OFFLOAD_QUOTED_NET = (
    "x* net of the pad control's x_pad: a property of the vehicle model, not of the assist"
)
OFFLOAD_QUOTED_NO_CONTROL = (
    "not quoted: the pad control in this mode has no offload to net it against (the gross "
    "rows are a property of the vehicle model)"
)
OFFLOAD_QUOTED_FAILED = "not quoted: the case's own solve did not end ok, so it has no x* to quote"
OFFLOAD_QUOTED_FIXED = "imposed: a fixed case, whose figure is its payload capacity against P_ref"
"""The basis of each case's quoted offload (``_quoted_offload``; D-SP1-10: stage 1 is the
headline, stage-2 and both-stage offloads are quoted net of the pad control)."""
OFFLOAD_VS_PAD_KEYS: tuple[str, ...] = (
    "liftoff_mass_kg",
    "stage1_burnout_t_s",
    "max_q_pa",
    "peak_felt_axial_g_flight",
)
"""Metrics an offload case reports beside the reference baseline's (with the delta)."""
OFFLOAD_TRACK_KEYS: tuple[str, ...] = (
    "speed_at_release_mps",
    "felt_g_track_peak",
    "peak_interface_force_N",
    "facility_length_m",
    "electrical_energy_J",
)
"""Metrics of the push an offload case reports (the pad has none)."""

type RunMemo = Callable[[ResolvedRun], tuple[RunResult, bool]]
"""Runs a resolved run, or reuses one flown with its trajectory key (True when reused)."""


@dataclass(frozen=True, eq=False)
class _OffloadContext:
    """What the cases of one offload pass share: the reference baseline ``base`` and its
    payload capacity ``p_ref`` [kg], its rung-2 run at P_ref (``base_matched``; None
    when it has none), the checks block, the final payload xtol [kg], the energy inputs
    and the vehicle their fuel masses describe (``energy_vehicle``: the experiment's
    baseline vehicle, whose full loads fix each stage's mixture ratio for every case,
    arm and sweep point), the run memo and the solve memo (by start trajectory key,
    P_ref and mode)."""

    base: RunResult
    p_ref: float
    base_matched: MatchedRun | None
    checks: ChecksConfig
    xtol_kg: float
    energy: OffloadEnergyConfig | None
    energy_vehicle: Vehicle
    run: RunMemo
    solves: dict[tuple[str, float, str], OffloadResult]


@dataclass(frozen=True, eq=False)
class _CaseOutcome:
    """One case of an offload pass: its record, the runs it writes, the runs whose checks
    are listed besides, and whether its solve was reused from another of one
    trajectory."""

    record: dict[str, Any]
    written: dict[str, RunResult]
    checked: dict[str, RunResult]
    reused: bool


def _run_memo(nominal: Sequence[RunResult]) -> RunMemo:
    """A run memo by ``compare.trajectory_key`` for one offload pass: a run whose key was
    flown (the nominal runs, then every run of the pass) reuses that trajectory and
    search (``sim.rerun_resolved``: its energy items and assumptions recomputed); the
    very resolved run of a nominal returns it. Runs through ``sim.run_resolved``."""
    from launchsim import sim  # late: sim imports this module

    memo = {trajectory_key(rr.resolved): rr for rr in nominal}

    def run(resolved: ResolvedRun) -> tuple[RunResult, bool]:
        key = trajectory_key(resolved)
        hit = memo.get(key)
        if hit is None:
            rr = sim.run_resolved(resolved)
            memo[key] = rr
            return rr, False
        if hit.resolved is resolved:
            return hit, True
        return sim.rerun_resolved(resolved, hit), True

    return run


def _offload_context(
    base: RunResult,
    nominal: Sequence[RunResult],
    energy: OffloadEnergyConfig | None,
    energy_vehicle: Vehicle,
) -> _OffloadContext:
    """The context of an offload pass against the reference baseline base (P_ref its
    ``reference_payload_kg``, its matched run at P_ref through ``sim.matched_run``), the
    energy inputs describing energy_vehicle (the experiment's baseline vehicle)."""
    from launchsim import sim  # late: sim imports this module

    planar = base.resolved.run.planar
    assert planar is not None  # a planar baseline (the block is planar only)
    p_ref = reference_payload_kg(base)
    return _OffloadContext(
        base=base,
        p_ref=p_ref,
        base_matched=sim.matched_run(base.resolved, base.result, p_ref),
        checks=planar.checks,
        xtol_kg=planar.search.final_payload_xtol_kg,
        energy=energy,
        energy_vehicle=energy_vehicle,
        run=_run_memo(nominal),
        solves={},
    )


def _solve(start: ResolvedRun, mode: str, ctx: _OffloadContext) -> tuple[OffloadResult, bool]:
    """The offload solve of start along mode at ctx.p_ref (``sim.solve_resolved_offload``),
    reused from ctx's solve memo for a start of the same trajectory key at the same P_ref
    (True when reused)."""
    from launchsim import sim  # late: sim imports this module

    key = (trajectory_key(start), ctx.p_ref, mode)
    hit = ctx.solves.get(key)
    if hit is not None:
        return hit, True
    res = sim.solve_resolved_offload(start, mode, ctx.p_ref)  # type: ignore[arg-type]
    ctx.solves[key] = res
    return res, False


def _verified(
    res: OffloadResult, final: ResolvedRun, ctx: _OffloadContext, label: str
) -> tuple[OffloadResult, RunResult]:
    """The independent verification of an ok solve: the payload search of the offloaded
    run ``final`` (ctx.run, so ``sim.run_resolved``), attached to res
    (``offload.with_verification``), and that run."""
    run, _ = ctx.run(final)
    record = run.result.search
    if record is None:  # a payload figure of merit always carries one
        raise ValueError(f"{label}: the verification run has no search record")
    flag_rel = ctx.checks.search_final_flag_rel
    return with_verification(res, verification_from_record(record, ctx.p_ref, flag_rel)), run


def _solve_record(res: OffloadResult) -> dict[str, Any]:
    """The metrics.json record of an offload solve: status, x* [kg], the final root, the
    load and x*/load, gamma*_ref [rad], m_res [kg] and dv margin [m/s] at x*, the
    shortfall of a no_offload solve, the evaluation count, the failure, the flags and
    the logged evaluations of its searches in x (``offload.OffloadEval``)."""
    return {
        "status": res.status,
        "offload_kg": res.offload_kg,
        "root_kg": res.root_kg,
        "load_kg": res.load_kg,
        "fraction_of_load": res.fraction_of_load,
        "gamma_star_rad": res.gamma_star_rad,
        "m_res_kg": res.m_res_kg,
        "dv_margin_mps": res.dv_margin_mps,
        "dv_shortfall_mps": res.dv_shortfall_mps,
        "n_evaluations": res.n_evaluations,
        "failure_kind": res.failure_kind,
        "failure_message": res.failure_message,
        "flags": list(res.flags),
        "evaluations": [as_plain(e) for e in res.evaluations],
    }


def _verification_record(res: OffloadResult, run: str | None) -> dict[str, Any] | None:
    """The record of a solve's independent verification (None without one): the search's
    status and P* [kg], P* - P_ref, the tolerance (checks.search_final_flag_rel x P_ref)
    [kg], whether it passed and the run that carried it."""
    v = res.verification
    if v is None:
        return None
    return {
        "status": v.status,
        "payload_kg": v.payload_kg,
        "delta_kg": v.delta_kg,
        "tolerance_kg": v.tolerance_kg,
        "passed": v.passed,
        "run": run,
    }


def _vs_pad(rr: RunResult, base: RunResult) -> dict[str, Any]:
    """OFFLOAD_VS_PAD_KEYS of an offload run beside the reference baseline's
    (``pad_<key>``, ``delta_<key>``), ``max_q_above_pad``, and the push's
    OFFLOAD_TRACK_KEYS."""
    m, b = rr.result.metrics, base.result.metrics
    out: dict[str, Any] = {}
    for key in OFFLOAD_VS_PAD_KEYS:
        out[key] = m.get(key)
        out[f"pad_{key}"] = b.get(key)
        out[f"delta_{key}"] = _delta(m.get(key), b.get(key))
    d_q = out["delta_max_q_pa"]
    out["max_q_above_pad"] = None if d_q is None else d_q > 0.0
    for key in OFFLOAD_TRACK_KEYS:
        out[key] = m.get(key)
    return out


def _removed_kg(case: ResolvedOffloadCase, offload_kg: float) -> list[float]:
    """The propellant [kg] a case takes from each stage of its variant: the stage-2
    pre-offload plus the case's offload offload_kg [kg] along its mode
    (``vehicle.offload_split_kg`` on the variant's vehicle); NaN entries for a NaN
    offload (a failed solve)."""
    vehicle = case.variant.to_vehicle()
    pre = [0.0] * vehicle.n_stages
    if case.config.stage2_offload_t is not None:
        pre[OFFLOAD_STAGE2_INDEX] = float(t_to_kg(case.config.stage2_offload_t))
    if not math.isfinite(offload_kg):
        return [math.nan] * vehicle.n_stages
    split = offload_split_kg(vehicle, case.config.mode, offload_kg)
    return [a + b for a, b in zip(pre, split, strict=True)]


def _quoted_offload(
    case: ResolvedOffloadCase, offload_kg: float, net_kg: float | None
) -> tuple[float | None, str]:
    """The offload [kg] a case quotes and its basis (D-SP1-10; docs/physics.md, "Reporting
    definitions (planar)"): a solve whose own offload offload_kg is not finite (it did
    not end ok or no_offload) nothing (OFFLOAD_QUOTED_FAILED); otherwise a stage-1 solve
    its x* (the headline, OFFLOAD_QUOTED_HEADLINE); a stage2 or both solve x* net of the
    pad control's x_pad (net_kg, OFFLOAD_QUOTED_NET), or nothing when there is no x_pad
    to net it against (OFFLOAD_QUOTED_NO_CONTROL); a fixed case its imposed offload
    (OFFLOAD_QUOTED_FIXED)."""
    cfg = case.config
    if not cfg.solved:
        return offload_kg, OFFLOAD_QUOTED_FIXED
    if not math.isfinite(offload_kg):
        return None, OFFLOAD_QUOTED_FAILED
    if cfg.mode in OFFLOAD_GROSS_MODES:
        return offload_kg, OFFLOAD_QUOTED_HEADLINE
    if net_kg is None:
        return None, OFFLOAD_QUOTED_NO_CONTROL
    return net_kg, OFFLOAD_QUOTED_NET


def _offload_assumptions(case: ResolvedOffloadCase, penalty: bool = True) -> list[str]:
    """The assumption lines of a case's offloaded run (``sim.OFFLOAD_ASSUMPTIONS`` and,
    with penalty, the assumed dry-mass line of a penalty row)."""
    from launchsim import sim  # late: sim imports this module

    lines = list(sim.OFFLOAD_ASSUMPTIONS)
    added = case.config.stage1_dry_mass_added_t
    if penalty and added is not None:
        lines.append(sim.offload_penalty_assumption(added))
    return lines


def _offload_case(
    case: ResolvedOffloadCase,
    ctx: _OffloadContext,
    *,
    verify: bool = True,
    pad_control: Mapping[str, float] | None = None,
) -> _CaseOutcome:
    """One offload case against ctx's reference baseline (docs/physics.md, "Reporting
    definitions (planar)").

    Solved: ``_solve`` of the case's start along its mode at P_ref; an ok solve is
    verified (``_verified``: the payload search of the vehicle offloaded by x*, unless
    verify is False) and its recorded run, flying P_ref, assembled
    (``sim.offload_run_result``); a no_offload solve records its full-load run (x* = 0).
    Fixed: the start (the variant with the imposed offload) is run, its payload search
    being the case's figure. Then the cross-vehicle decomposition against the baseline's
    matched run at P_ref (``compare.cross_vehicle_decomposition``: a solved case's final
    evaluation, a fixed case's run re-evaluated at P_ref by ``sim.matched_run``), the
    paired pad (``config.offload_solved_run`` of the pad start with the same offload,
    run, and compared with the case's own payload search on one vehicle by
    ``compare.attributed_comparison``), the energy comparison (``compare.offload_energy``)
    and the record."""
    from launchsim import sim  # late: sim imports this module

    cfg = case.config
    mode = cfg.mode
    written: dict[str, RunResult] = {}
    checked: dict[str, RunResult] = {}
    res: OffloadResult | None = None
    final: ResolvedRun | None = None
    silo: RunResult | None = None
    rr: RunResult | None = None
    reused = False
    if cfg.solved:
        res, reused = _solve(case.start, mode, ctx)
        if res.status == OK_STATUS:
            final = offload_solved_run(case.start, mode, res.offload_kg, cfg.name, case.start.name)
            if verify:
                res, silo = _verified(res, final, ctx, f"offload case {cfg.name!r}")
                checked[f"{case.start.name} (verification search)"] = silo
        elif res.status == NO_OFFLOAD_STATUS:
            final = case.start
        if res.recorded is not None and final is not None:
            rr = sim.offload_run_result(final, res)
        offload_kg = res.offload_kg
    else:
        final = case.start
        silo, reused = ctx.run(final)
        rr = silo
        offload_kg = math.nan if case.imposed_kg is None else case.imposed_kg
    if rr is not None:
        rr = sim.with_assumptions(rr, _offload_assumptions(case))
        written[rr.name] = rr
    decomposition = None
    base_m = ctx.base_matched
    if base_m is not None:
        vm: MatchedRun | None = None
        if res is not None:
            vm = offload_matched_run(case.start.name, res, base_m.omega_p_rads, base_m.r_datum_m)
        elif silo is not None and final is not None:
            vm = sim.matched_run(final, silo.result, ctx.p_ref)
        if vm is not None:
            decomposition = cross_vehicle_decomposition(vm, base_m, checks=ctx.checks)
    paired = None
    if case.pad_start is not None and math.isfinite(offload_kg):
        pad_x = offload_kg if cfg.solved else 0.0
        pad_run = offload_solved_run(case.pad_start, mode, pad_x, cfg.name, case.pad_start.name)
        pad, _ = ctx.run(pad_run)
        pad = sim.with_assumptions(pad, _offload_assumptions(case, penalty=False))
        written[pad.name] = pad
        if silo is None:  # a no_offload solve: the full-load start's own payload search
            silo, _ = ctx.run(case.start)
            checked[f"{case.start.name} (full load, payload search)"] = silo
        comparison = attributed_comparison(silo, pad, ctx.checks, cfg.of)
        p_pad = pad.result.metrics.get("payload_kg")
        paired = {
            "run": pad.name,
            "status": pad.result.status,
            "payload_kg": p_pad,
            "payload_delta_vs_reference_kg": _delta(p_pad, ctx.p_ref),
            "assisted_run": silo.name,
            "assisted_payload_kg": silo.result.metrics.get("payload_kg"),
            "payload_delta_kg": comparison.get("payload_delta_kg"),
            "screening_status": comparison.get("screening_status"),
            "comparison": comparison,
        }
    record = _case_record(case, ctx, res, rr, offload_kg, decomposition, paired, pad_control)
    return _CaseOutcome(record, written, checked, reused)


def _case_record(
    case: ResolvedOffloadCase,
    ctx: _OffloadContext,
    res: OffloadResult | None,
    rr: RunResult | None,
    offload_kg: float,
    decomposition: dict[str, Any] | None,
    paired: dict[str, Any] | None,
    pad_control: Mapping[str, float] | None,
) -> dict[str, Any]:
    """The metrics.json record of one offload case (see ``_offload_case``): the quoted
    offload and its basis (``_quoted_offload``), what was taken from each stage (gross)
    and its share of each load, the payload flown and its difference from P_ref, the
    solve and its verification, the pad control's offload and the net value, the
    comparison with the reference baseline (liftoff mass, MECO, max-Q, felt g, the
    push), the decomposition with the screening yardstick and ratio, the paired pad, the
    energy comparison (each stage's removed propellant split at the mixture ratio of
    ctx.energy_vehicle) and the flags. Masses in kg; ``fixed_fraction`` is the stated
    fraction of a ``*_fraction`` fixed key (None for a mass key, whose value is
    ``offload_kg``)."""
    cfg = case.config
    vehicle = case.variant.to_vehicle()
    loads = [s.propellant_mass_kg for s in vehicle.stages]
    removed = _removed_kg(case, offload_kg)
    total_load = math.fsum(loads)
    total = math.fsum(removed)
    if res is not None:
        status = res.status
    else:  # a fixed case: its payload search's status
        status = None if rr is None else rr.result.metrics.get("search_status")
    payload = None if rr is None else rr.result.metrics.get("payload_kg")
    x_pad = None if pad_control is None or not cfg.solved else pad_control.get(cfg.mode)
    net = None
    if x_pad is not None and math.isfinite(offload_kg):
        net = offload_kg - x_pad
    quoted, quoted_basis = _quoted_offload(case, offload_kg, net)
    energy = None
    if ctx.energy is not None and all(math.isfinite(x) for x in removed):
        # the mixture ratio of the energy block's vehicle (the experiment's baseline),
        # whichever load this case's vehicle carries (a sweep point or an arm)
        ref_stages = ctx.energy_vehicle.stages
        ref_loads = [s.propellant_mass_kg for s in ref_stages]
        fuel = [ctx.energy.fuel_kg(s.name) for s in ref_stages]
        elec = None if rr is None else rr.result.metrics.get("electrical_energy_J")
        lhv = ctx.energy.heating_value_J_per_kg
        energy = offload_energy(removed, ref_loads, fuel, lhv, elec)
    xv = decomposition or {}
    if rr is not None:
        flags = list(rr.result.flags)
    else:
        flags = [] if res is None else list(res.flags)
    s1, s2 = OFFLOAD_STAGE1_INDEX, OFFLOAD_STAGE2_INDEX
    return {
        "name": cfg.name,
        "of": case.variant.name,
        "kind": "solve" if cfg.solved else "fixed",
        "mode": cfg.mode,
        "fixed_key": None if cfg.fixed is None else cfg.fixed.key,
        "fixed_fraction": None if cfg.fixed is None else cfg.fixed.fraction,
        "run": None if rr is None else rr.name,
        "status": status,
        "run_status": None if rr is None else rr.result.status,
        "reference_payload_kg": ctx.p_ref,
        "quoted_offload_kg": quoted,
        "quoted_basis": quoted_basis,
        "offload_kg": offload_kg,
        "stage2_preoffload_kg": (
            0.0 if cfg.stage2_offload_t is None else float(t_to_kg(cfg.stage2_offload_t))
        ),
        "stage1_dry_mass_added_kg": (
            0.0
            if cfg.stage1_dry_mass_added_t is None
            else float(t_to_kg(cfg.stage1_dry_mass_added_t))
        ),
        "assumed_penalty": cfg.stage1_dry_mass_added_t is not None,
        "stage1_offload_kg": removed[s1],
        "stage2_offload_kg": removed[s2],
        "total_offload_kg": total,
        "stage1_load_kg": loads[s1],
        "stage2_load_kg": loads[s2],
        "total_load_kg": total_load,
        "stage1_fraction": removed[s1] / loads[s1],
        "stage2_fraction": removed[s2] / loads[s2],
        "total_fraction": total / total_load,
        "payload_kg": payload,
        "payload_delta_kg": _delta(payload, ctx.p_ref),
        "solve": None if res is None else _solve_record(res),
        "verification": None if res is None else _verification_record(res, case.start.name),
        "pad_control_offload_kg": x_pad,
        "net_offload_kg": net,
        "vs_pad": None if rr is None else _vs_pad(rr, ctx.base),
        "decomposition": decomposition,
        "decomposition_status": xv.get("xv_status"),
        "release_speed_mps": xv.get("xv_speed_at_release_mps"),
        "screening_offload_kg": xv.get("xv_screening_offload_kg"),
        "screening_ratio": xv.get("xv_offload_to_screening_ratio"),
        "beats_screening": xv.get("xv_beats_screening"),
        "paired_pad": paired,
        "energy": energy,
        "flags": flags,
    }


def _pad_control(
    mode: str, ctx: _OffloadContext
) -> tuple[dict[str, Any], dict[str, RunResult], dict[str, RunResult]]:
    """The pad control of an offload mode (D-SP1-10; docs/physics.md, "Pad control, and
    why"): the same solve on the reference baseline at P_ref, an ok solve verified like
    a case, its recorded run (``<baseline>__offload_<mode>``, with OFFLOAD_ASSUMPTIONS);
    the record carries x_pad, m_res and the dv margin at x_pad, the residual slope s =
    |dm_res/dx| from the solve's own logs (``offload.residual_slope_kg_per_kg``) and, for
    stage1, the bound final_payload_xtol_kg / s with, for an ok control, whether x_pad
    lies in [0, bound] (phase file SP1 section 5.3); ``resolution_effect``: a no_offload
    control whose m_res(0) lies in (-final_payload_xtol_kg, 0), grams below zero at the
    feasible-side convention's resolution, not a failure; and ``consistency``, the
    verdict of ``pad_control_consistency`` (a failing stage-1 control blocks findings:
    ``summary.offload_blocking_controls``)."""
    from launchsim import sim  # late: sim imports this module

    base = ctx.base
    name = pad_control_run_name(base.name, mode)
    label = f"pad control {mode}"
    written: dict[str, RunResult] = {}
    checked: dict[str, RunResult] = {}
    res, _ = _solve(base.resolved, mode, ctx)
    final: ResolvedRun | None = None
    if res.status == OK_STATUS:
        final = offload_solved_run(base.resolved, mode, res.offload_kg, label, name)
        res, ver = _verified(res, final, ctx, label)
        checked[f"{name} (verification search)"] = ver
    elif res.status == NO_OFFLOAD_STATUS:
        final = offload_solved_run(base.resolved, mode, 0.0, label, name)
    rr = None
    if final is not None and res.recorded is not None:
        rr = sim.with_assumptions(sim.offload_run_result(final, res), sim.OFFLOAD_ASSUMPTIONS)
        written[name] = rr
    slope = residual_slope_kg_per_kg(res)
    tested = mode in OFFLOAD_GROSS_MODES  # stage 1: a consistency test of the solver
    bound = None
    if tested and slope is not None and slope > 0.0:
        bound = ctx.xtol_kg / slope
    x_pad = res.offload_kg
    within = None
    if tested and bound is not None and res.status == OK_STATUS:
        within = bool(0.0 <= x_pad <= bound)
    record = {
        "mode": mode,
        "run": None if rr is None else name,
        "status": res.status,
        "reference_payload_kg": ctx.p_ref,
        "offload_kg": x_pad,
        "fraction_of_load": res.fraction_of_load,
        "m_res_kg": res.m_res_kg,
        "dv_margin_mps": res.dv_margin_mps,
        "slope_kg_per_kg": slope,
        "bound_kg": bound,
        "within_bound": within,
        "resolution_effect": bool(
            res.status == NO_OFFLOAD_STATUS and -ctx.xtol_kg < res.m_res_kg < 0.0
        ),
        "consistency": pad_control_consistency(
            mode, res.status, x_pad, res.m_res_kg, bound, ctx.xtol_kg
        ),
        "solve": _solve_record(res),
        "verification": _verification_record(res, name),
        "flags": list(res.flags) if rr is None else list(rr.result.flags),
    }
    return record, written, checked


def pad_control_consistency(
    mode: str,
    status: str,
    offload_kg: float,
    m_res_kg: float,
    bound_kg: float | None,
    xtol_kg: float,
) -> str:
    """The consistency verdict of a pad control (phase file SP1 section 5.3; docs/physics.md,
    "Pad control, and why"), pure. Inputs: the control's mode and solve status, x_pad =
    offload_kg [kg], m_res_kg [kg] at x_pad (m_res(0) for no_offload), bound_kg =
    final_payload_xtol_kg / s [kg] (None without a slope s) and xtol_kg =
    final_payload_xtol_kg [kg]. For stage 1 (``config.OFFLOAD_GROSS_MODES``): an
    ok control passes (CHECK_PASS) when 0 <= x_pad <= bound_kg and fails (CHECK_FAIL)
    outside it, and is PAD_CONTROL_NO_BOUND without a bound; a no_offload control passes
    as a resolution effect when -xtol_kg < m_res(0) < 0 (grams below zero at the
    feasible-side convention's resolution) and fails otherwise; any other status
    (search_failed) fails. A stage2 or both control has no consistency test (reported
    for the net value, a property of the vehicle model): CHECK_NA."""
    if mode not in OFFLOAD_GROSS_MODES:
        return CHECK_NA
    if status == OK_STATUS:
        if bound_kg is None:
            return PAD_CONTROL_NO_BOUND
        return CHECK_PASS if 0.0 <= offload_kg <= bound_kg else CHECK_FAIL
    if status == NO_OFFLOAD_STATUS:
        return CHECK_PASS if -xtol_kg < m_res_kg < 0.0 else CHECK_FAIL
    return CHECK_FAIL


def _offload_arm_record(
    arm_name: str,
    param: str,
    fraction: float,
    pad_perturbed: bool,
    outcome: _CaseOutcome,
    nominal: Mapping[str, Any],
) -> dict[str, Any]:
    """The record of one offload sensitivity arm: the case, the parameter and its signed
    fraction, whether the pad was perturbed, the arm's P_ref (the same-perturbation
    pad's P*) beside the nominal, its status and offload against the nominal case's,
    the shares of the load, the decomposition's status, residual and screening ratio,
    whether the solve was reused (a trajectory equal to another's: an energy-only or
    yardstick parameter) and the flags."""
    rec = outcome.record
    xv = rec.get("decomposition") or {}
    return {
        "case": rec["name"],
        "run": arm_name,
        "param": param,
        "fraction": fraction,
        "pad_perturbed": pad_perturbed,
        "reference_payload_kg": rec["reference_payload_kg"],
        "nominal_reference_payload_kg": nominal.get("reference_payload_kg"),
        "status": rec["status"],
        "offload_kg": rec["offload_kg"],
        "nominal_offload_kg": nominal.get("offload_kg"),
        "offload_delta_kg": _delta(rec["offload_kg"], nominal.get("offload_kg")),
        "payload_kg": rec["payload_kg"],
        "payload_delta_kg": rec["payload_delta_kg"],
        "stage1_fraction": rec["stage1_fraction"],
        "total_fraction": rec["total_fraction"],
        "decomposition_status": rec["decomposition_status"],
        "decomposition_residual_mps": xv.get("xv_residual_mps"),
        "screening_ratio": rec["screening_ratio"],
        "electrical_energy_J": (rec.get("vs_pad") or {}).get("electrical_energy_J"),
        "trajectory_reused": outcome.reused,
        "flags": rec["flags"],
    }


def _has_payload_capacity(rr: RunResult) -> bool:
    """True when a pad's payload search found a P* (a finite ``payload_kg``): a
    reference payload to solve the offload at (``compare.reference_payload_kg`` would
    fall back to the vehicle payload, which is not one)."""
    return _is_finite_number(rr.result.metrics.get("payload_kg"))


def _reference_failed_arm(run: str, arm: ResolvedOffloadArm, pad: RunResult) -> dict[str, Any]:
    """The record of a sensitivity arm whose same-perturbation pad has no P*: status
    REFERENCE_FAILED_STATUS, nothing solved, the pad's search status in the flags."""
    return {
        "case": arm.case,
        "run": run,
        "param": arm.param,
        "fraction": arm.fraction,
        "pad_perturbed": arm.pad_perturbed,
        "reference_payload_kg": None,
        "status": REFERENCE_FAILED_STATUS,
        "offload_kg": None,
        "trajectory_reused": False,
        "flags": [
            f"{REFERENCE_FAILED_STATUS}: the pad {pad.name} under this perturbation has no "
            f"payload capacity (search {pad.result.metrics.get('search_status')})"
        ],
    }


def offload_arms_that_run(
    offload: ResolvedOffload, variants: Collection[str]
) -> list[ResolvedOffloadArm]:
    """The sensitivity arms of a resolved offload block that a pass solves when the
    variants named in ``variants`` ran: those whose case's variant (its ``of``) ran and
    that carry their perturbed variant, in the block's order. ``planar_offload`` solves
    these and ``planar_sensitivity_note`` points to them, so the two cannot disagree."""
    of = {case.name: case.config.of for case in offload.cases}
    return [arm for arm in offload.arms if of[arm.case] in variants and arm.variant is not None]


def _energy_inputs(energy: OffloadEnergyConfig | None) -> dict[str, Any] | None:
    """The energy inputs as recorded: each stage's fuel mass [kg] with its provenance and
    the lower heating value [J/kg] with its provenance (None without the block)."""
    if energy is None:
        return None
    return {
        "fuel_mass_kg": {stage: energy.fuel_kg(stage) for stage in energy.fuel_mass_t},
        "fuel_mass_provenance": {
            stage: q.model_dump(exclude={"value"}) for stage, q in energy.fuel_mass_t.items()
        },
        "heating_value_J_per_kg": energy.heating_value_J_per_kg,
        "heating_value_provenance": energy.heating_value_MJ_per_kg.model_dump(exclude={"value"}),
    }


def planar_offload(
    resolved: ResolvedExperiment,
    baseline: RunResult,
    variants: Mapping[str, RunResult],
    *,
    sensitivity: bool = True,
    offload: bool = True,
) -> OffloadReport | None:
    """The offload block of a planar experiment whose baseline and variants ran (SP1
    step 7; docs/physics.md, "Reporting definitions (planar)"); pure apart from the runs
    it executes through ``sim`` (``solve_resolved_offload``, ``run_resolved``,
    ``matched_run``, ``offload_run_result``), so nothing is written. None when the
    experiment declares no block; with offload False a report whose record says
    OFFLOAD_SKIPPED.

    P_ref = ``compare.reference_payload_kg`` of the baseline (the block's reference).
    In order: the pad control of every distinct solve mode (``_pad_control``), every
    case whose variant ran (``_offload_case``, with the pad control's offload of its mode
    for the net value; a case whose variant did not run is noted OFFLOAD_NOT_RUN), and,
    with sensitivity, every sensitivity arm (each against the pad under the same
    perturbation, run or reused by trajectory key, P_ref its P*; no verification; the
    solve reused when the start's trajectory and P_ref equal another's;
    OFFLOAD_ARMS_SKIPPED otherwise; an arm whose pad has no P* is REFERENCE_FAILED_STATUS,
    unsolved). Runs of one trajectory key are flown once per pass (``_run_memo``, seeded
    with the baseline and the variants). A baseline without a P* solves nothing: the
    record says why (``skipped``, REFERENCE_FAILED_STATUS)."""
    ro = resolved.offload
    if ro is None:
        return None
    base_record: dict[str, Any] = {
        "basis": OFFLOAD_COMPARISON_BASIS,
        "reference": baseline.name,
    }
    if not offload:
        return OffloadReport({**base_record, "skipped": OFFLOAD_SKIPPED})
    if not _has_payload_capacity(baseline):
        status = baseline.result.metrics.get("search_status")
        note = (
            f"(offload block not solved, {REFERENCE_FAILED_STATUS}: the reference baseline "
            f"{baseline.name} has no payload capacity P* to fly; its search ended {status})"
        )
        return OffloadReport({**base_record, "skipped": note})
    from launchsim import sim  # late: sim imports this module

    energy = ro.config.energy
    ctx = _offload_context(
        baseline, [baseline, *variants.values()], energy, resolved.baseline.to_vehicle()
    )
    written: dict[str, RunResult] = {}
    checked: dict[str, RunResult] = {}
    ran = [c for c in ro.cases if c.config.of in variants]
    modes = [m for m in ro.pad_control_modes if any(c.config.solve == m for c in ran)]
    controls: list[dict[str, Any]] = []
    x_pad: dict[str, float] = {}
    for mode in modes:
        record, w, c = _pad_control(mode, ctx)
        controls.append(record)
        written.update(w)
        checked.update(c)
        if math.isfinite(record["offload_kg"]):
            x_pad[mode] = record["offload_kg"]
    cases: list[dict[str, Any]] = []
    for case in ro.cases:
        if case.config.of not in variants:
            cases.append({"name": case.name, "of": case.config.of, "skipped": OFFLOAD_NOT_RUN})
            continue
        outcome = _offload_case(case, ctx, pad_control=x_pad)
        cases.append(outcome.record)
        written.update(outcome.written)
        checked.update(outcome.checked)
    arms: list[dict[str, Any]] = []
    nominal = {rec["name"]: rec for rec in cases}
    for arm in offload_arms_that_run(ro, variants) if sensitivity else ():
        case = next(c for c in ro.cases if c.name == arm.case)
        assert arm.variant is not None  # offload_arms_that_run keeps only these
        if arm.pad is baseline.resolved:
            pad = baseline
        else:
            pad, _ = ctx.run(arm.pad)
            checked[f"{arm.pad.name} (offload sensitivity pad)"] = pad
        if not _has_payload_capacity(pad):
            arms.append(_reference_failed_arm(arm.start.name, arm, pad))
            continue
        p_ref = reference_payload_kg(pad)
        arm_ctx = replace(
            ctx,
            base=pad,
            p_ref=p_ref,
            base_matched=sim.matched_run(pad.resolved, pad.result, p_ref),
        )
        arm_case = ResolvedOffloadCase(case.config, arm.variant, arm.start, None, arm.imposed_kg)
        outcome = _offload_case(arm_case, arm_ctx, verify=False)
        for name, rr in {**outcome.written, **outcome.checked}.items():
            checked[f"{name} (offload sensitivity)"] = rr
        arms.append(
            _offload_arm_record(
                arm.start.name,
                arm.param,
                arm.fraction,
                arm.pad_perturbed,
                outcome,
                nominal.get(arm.case, {}),
            )
        )
    notes = []
    if ro.arms and not sensitivity:
        notes.append(OFFLOAD_ARMS_SKIPPED)
    vehicle_name = resolved.baseline.vehicle.name
    record = {
        **base_record,
        "reference_payload_kg": ctx.p_ref,
        "caveats": offload_caveats(vehicle_name, CALIBRATION_RECORDS.get(vehicle_name)),
        "energy_inputs": _energy_inputs(energy),
        "pad_control": ro.config.pad_control,
        "pad_controls": controls,
        "cases": cases,
        "sensitivity_basis": OFFLOAD_SENSITIVITY_BASIS if ro.arms else None,
        "sensitivity": arms,
        "notes": notes,
    }
    return OffloadReport(record, written, checked)


def offload_sweep_point(
    point: SweepPoint,
    ref: RunResult,
    point_run: RunResult,
    energy: OffloadEnergyConfig | None,
    energy_vehicle: Vehicle,
) -> tuple[dict[str, dict[str, Any]], dict[str, RunResult]]:
    """The offload cases a sweep names at one point (``SweepPoint.offload``: each built on
    the point's run), solved or fixed against ref, the point's baseline (the
    experiment's, or the paired baseline of a paired sweep), at ref's P_ref
    (``_offload_case``, verified, no paired pad and no pad control), the energy
    comparison at the mixture ratio of energy_vehicle (the experiment's baseline
    vehicle, whatever load the point carries). Returns the case records by case name and
    the runs whose per-run checks the sweep summary lists (the recorded runs and the
    verification searches, labelled ``<run>__<case>``). A baseline without a P* gives
    every case the status REFERENCE_FAILED_STATUS, nothing solved."""
    records: dict[str, dict[str, Any]] = {}
    runs: dict[str, RunResult] = {}
    if not _has_payload_capacity(ref):
        for case in point.offload:
            records[case.name] = {"name": case.name, "status": REFERENCE_FAILED_STATUS}
        return records, runs
    ctx = _offload_context(ref, [ref, point_run], energy, energy_vehicle)
    for case in point.offload:
        outcome = _offload_case(case, ctx)
        records[case.name] = outcome.record
        runs.update(outcome.written)
        runs.update(outcome.checked)
    return records, runs


OFFLOAD_SWEEP_COLUMNS: tuple[str, ...] = (
    "status",
    "offload_kg",
    "stage1_fraction",
    "total_fraction",
    "reference_payload_kg",
    "payload_kg",
    "payload_delta_kg",
    "verification_delta_kg",
    "decomposition_status",
    "screening_ratio",
    "max_q_pa",
    "electrical_energy_J",
    "solve_gamma_star_rad",
    "n_flags",
)
"""The sweep_index.csv columns of each offload case a sweep names, written
``<case>.<column>`` (``offload_index_values``): the solve's (or fixed run's) status,
the offload x [kg] (a fixed case's imposed one), its share of the stage-1 load and of
the total load, the point's P_ref [kg], the payload its recorded run flies [kg] and
that less P_ref [kg] (a solved case flies P_ref, so 0; a fixed case its own payload
capacity P*, so P* - P_ref is its figure), the verification's P* - P_ref [kg] (a solved
case's; a fixed case has none), the decomposition status, the offload-to-screening
ratio, the offloaded run's max-Q [Pa] and electrical energy [J], and (SP1 step 8a,
KI-028; appended so every earlier column keeps its name and place) the solve's own
gamma*_ref [rad] (Earth-relative flight-path angle at MECO, refined in search mode at
X1, the root of the first search in x, and held for X2 and the final search at x*: the
case record's ``solve.gamma_star_rad``, not the point's payload-search ``gamma_star_rad``
column; a fixed case has no solve, so none, and a solve that ended search_failed NaN)
and the number of the case record's flags (the solve's and its recorded run's; the
flags themselves are listed in the sweep summary's Checks section,
``summary.sweep_checks_section``, with a failed solve's status; none for a record
without a flag list, such as a reference_failed point). A sweep point writes no offload run
directory, so these columns are its solve's only record on disk."""


def offload_index_values(record: Mapping[str, Any]) -> dict[str, Any]:
    """The OFFLOAD_SWEEP_COLUMNS values of one case record (None where it has none)."""
    verification = record.get("verification") or {}
    vs_pad = record.get("vs_pad") or {}
    solve = record.get("solve") or {}
    flags = record.get("flags")
    values = {
        "status": record.get("status"),
        "offload_kg": record.get("offload_kg"),
        "stage1_fraction": record.get("stage1_fraction"),
        "total_fraction": record.get("total_fraction"),
        "reference_payload_kg": record.get("reference_payload_kg"),
        "payload_kg": record.get("payload_kg"),
        "payload_delta_kg": record.get("payload_delta_kg"),
        "verification_delta_kg": verification.get("delta_kg"),
        "decomposition_status": record.get("decomposition_status"),
        "screening_ratio": record.get("screening_ratio"),
        "max_q_pa": vs_pad.get("max_q_pa"),
        "electrical_energy_J": vs_pad.get("electrical_energy_J"),
        "solve_gamma_star_rad": solve.get("gamma_star_rad"),
        "n_flags": None if flags is None else len(flags),
    }
    return {key: values[key] for key in OFFLOAD_SWEEP_COLUMNS}


def offload_record(report: OffloadReport) -> dict[str, Any]:
    """The metrics.json ``offload`` value of a report: its record plus ``runs``, the
    metrics record (``metrics.metrics_record``) of every run it writes."""
    return {
        **report.record,
        "runs": {name: metrics_record(rr.result) for name, rr in report.runs.items()},
    }


SENSITIVITY_EMPTY_OF = (
    "no run has payload sensitivity cases: the sensitivity block's `of` lists no run"
)
"""How a planar Sensitivity note opens for a sensitivity block whose ``of`` is empty (SP1
step 8a): the block is declared, its params serving only the offload block's arms, so
"no sensitivity block declared" would be false."""
SENSITIVITY_ARMS_REPORTED = (
    "its params perturb the offload block's sensitivity arms, reported in the section "
    f'"{OFFLOAD_SECTION_NAME}"'
)
"""Where the note sends the reader when some of the offload block's sensitivity arms ran."""
SENSITIVITY_ARMS_SKIPPED = (
    "its params perturb the offload block's sensitivity arms, which --no-offload skipped "
    "with the block"
)
"""What the note says of those arms when the offload block was skipped."""
SENSITIVITY_ARMS_NOT_RUN = (
    "its params perturb the offload block's sensitivity arms, none of which ran (their "
    "case's variant did not run)"
)
"""What the note says of those arms when the offload block ran but none of its arms did
(``run --variant`` naming another variant): the offload section then has no arms table."""


def planar_sensitivity_note(
    resolved: ResolvedExperiment,
    *,
    sensitivity: bool,
    offload: bool,
    variants: Collection[str],
) -> str:
    """What a planar summary's payload Sensitivity section prints when no sensitivity case
    ran (``ExperimentResult.sensitivity_note``), given the names of the variants that ran
    (``variants``): SENSITIVITY_SKIPPED with sensitivity False; for a block whose ``of``
    lists no run, SENSITIVITY_EMPTY_OF and, when the offload block has sensitivity arms
    (``ResolvedOffload.arms``: its ``sensitivity_of`` under the block's params), what
    became of them: SENSITIVITY_ARMS_SKIPPED with offload False, SENSITIVITY_ARMS_REPORTED
    when some arm ran (``offload_arms_that_run``), SENSITIVITY_ARMS_NOT_RUN when none did;
    with no resolved case otherwise (no block, or a block without params) "no sensitivity
    block declared", as before; else (a block whose runs did not run) "no sensitivity
    cases declared for the runs that ran". Each but the skip note closes with the planar
    C_D note."""
    cd_note = CD_SENSITIVITY_NOTES[PLANAR_2D]
    block = resolved.experiment.sensitivity
    if not sensitivity:
        return SENSITIVITY_SKIPPED
    if block is not None and not block.of:
        parts = [SENSITIVITY_EMPTY_OF]
        ro = resolved.offload
        if ro is not None and ro.arms:
            if not offload:
                parts.append(SENSITIVITY_ARMS_SKIPPED)
            elif offload_arms_that_run(ro, variants):
                parts.append(SENSITIVITY_ARMS_REPORTED)
            else:
                parts.append(SENSITIVITY_ARMS_NOT_RUN)
        return f"({'; '.join(parts)}; C_D: {cd_note})"
    if not resolved.sensitivity:
        return f"(no sensitivity block declared; C_D: {cd_note})"
    return f"(no sensitivity cases declared for the runs that ran; C_D: {cd_note})"


def planar_experiment_result(
    resolved: ResolvedExperiment,
    baseline: RunResult,
    variants: dict[str, RunResult],
    git: dict[str, Any],
    timestamp_utc: str,
    *,
    sensitivity: bool,
    run_cases: bool,
    offload: bool = True,
) -> ExperimentResult:
    """The ExperimentResult of a planar experiment whose baseline and variants ran:
    the comparisons (``planar_comparisons``), the sensitivity cases (``run_sensitivity``
    with the runs already flown as the memo's nominal runs, unless ``sensitivity`` is
    False), the bounds (``planar_bounds``), with run_cases the calibration cases
    (independent runs, never compared) and, when the experiment declares an offload
    block, its report (``planar_offload``: skipped, and saying so, with offload False;
    its sensitivity arms follow ``sensitivity``). Pure apart from the runs it executes
    through ``sim``: it writes nothing, so a caller with an in-memory experiment
    (``config.resolve_experiment`` of dicts, ``sim.run_resolved`` of the baseline and the
    variants) gets the whole result without touching the disk."""
    from launchsim import sim  # late: sim imports this module

    ran = {baseline.name, *variants}
    rows = (
        run_sensitivity(resolved, baseline, ran, nominal={baseline.name: baseline, **variants})
        if sensitivity
        else []
    )
    note = planar_sensitivity_note(
        resolved, sensitivity=sensitivity, offload=offload, variants=variants
    )
    cases = {n: sim.run_resolved(r) for n, r in resolved.cases.items()} if run_cases else {}
    planar = resolved.baseline.run.planar
    comparison = planar_comparisons(resolved, baseline, variants)
    bounds = planar_bounds(resolved, baseline, ran)
    report = planar_offload(resolved, baseline, variants, sensitivity=sensitivity, offload=offload)
    return ExperimentResult(
        experiment_name=resolved.experiment.name,
        vehicle_name=resolved.baseline.vehicle.name,
        baseline=baseline,
        variants=variants,
        comparison=comparison,
        git=git,
        timestamp_utc=timestamp_utc,
        comparison_basis=shared_basis(resolved),
        sensitivity=rows,
        sensitivity_note=note,
        model=PLANAR_2D,
        label=resolved.experiment.label,
        bounds=bounds,
        cases=cases,
        search_budget_id=None if planar is None else planar.search.budget_id(),
        offload=report,
    )


def planar_sweep_index_frame(sweep: SweepResult, root: Path) -> pd.DataFrame:
    """One row per planar sweep point: point, the axis values, run_dir (relative to
    root), of, the paired baseline's name (empty unless paired), the
    PLANAR_SWEEP_INDEX_METRICS (the point's metrics, or its comparison against its
    baseline; non-finite or absent -> empty cell), the PLANAR_SWEEP_INDEX_TEXT, the
    OFFLOAD_SWEEP_COLUMNS of every offload case the sweep solved (``<case>.<column>``,
    only when it solved some: ``SweepResult.offload``) and status. ValueError when an
    axis path collides with a column."""
    fixed = {*SWEEP_INDEX_FIXED_COLUMNS, PLANAR_SWEEP_PAIRED_COLUMN}
    names = list(dict.fromkeys(n for records in sweep.offload for n in records))
    offload_cols = [f"{n}.{col}" for n in names for col in OFFLOAD_SWEEP_COLUMNS]
    clash = sorted(
        {*fixed, *PLANAR_SWEEP_INDEX_METRICS, *PLANAR_SWEEP_INDEX_TEXT, *offload_cols}
        & set(sweep.axes)
    )
    if clash:
        raise ValueError(f"sweep index: axis paths collide with index columns: {clash}")
    paired = sweep.paired or [None] * len(sweep.points)
    offloads = sweep.offload or [{}] * len(sweep.points)
    rows = []
    for point, rr, comp, run_dir, pair, records in zip(
        sweep.points,
        sweep.results,
        sweep.comparisons,
        sweep.run_dirs,
        paired,
        offloads,
        strict=True,
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
            row[key] = index_text(value)
        for name in names:
            values = offload_index_values(records.get(name, {}))
            for col, value in values.items():
                is_text = isinstance(value, str) or value is None
                row[f"{name}.{col}"] = value if is_text or _is_finite_number(value) else None
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
        *offload_cols,
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
    offload: bool = True,
) -> tuple[list[SweepResult], Path]:
    """Run every sweep of an experiment and write the results.

    Layout: results/<experiment>/<timestamp>/baseline/ (the pad baseline, flat layout),
    sweep_<n>/run_NNNN/ per grid point (flat layout, compared against the baseline),
    sweep_<n>/sweep_index.csv and a top-level summary.md. A planar sweep that names
    offload cases (``SweepConfig.offload``) solves them at every point
    (``offload_sweep_point``) unless ``offload`` is False, and adds their columns to
    sweep_index.csv (OFFLOAD_SWEEP_COLUMNS per case). Returns the SweepResults and
    the run directory, created before any run starts and after the preflight
    (``sim.check_resolved``: a refused configuration leaves no directory); an exception
    after that leaves FAILED.txt in it (write_failure_marker) and propagates.
    """
    from launchsim import sim  # late: sim imports this module

    exp = resolved.experiment
    check_result_names(resolved)
    sim.check_resolved(resolved)  # every run's specs build: a bad config writes nothing
    git = sim.git_info(_repo_root_of(repo_root))
    now = datetime.now(UTC)  # one clock read: the directory name and timestamp_utc agree
    timestamp = utc_timestamp(now)
    out_dir = make_run_dir(Path(out_root), exp.name, now=now)
    try:
        sweeps, frames, baseline = _run_sweeps_into(
            resolved, out_dir, plots, git, timestamp, offload=offload
        )
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
    *,
    offload: bool = True,
) -> tuple[list[SweepResult], list[pd.DataFrame], RunResult]:
    """Run the baseline and every sweep point into an existing run directory (see
    run_sweep); returns the SweepResults, their index frames and the baseline. A planar
    point of a paired sweep is compared with its paired baseline (run once per point
    and written beside it as ``run_NNNN__<baseline>``), every other point with the
    experiment's baseline; planar comparisons carry the matched-payload attribution
    (``planar_comparisons``). With offload, the offload cases a planar sweep names are
    solved at each point against that same baseline (``offload_sweep_point``)."""
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
        offloads: list[dict[str, dict[str, Any]]] = []
        offload_runs: list[dict[str, RunResult]] = []
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
            if planar and point.offload and offload:
                energy = None if resolved.offload is None else resolved.offload.config.energy
                energy_vehicle = resolved.baseline.to_vehicle()
                records, point_runs = offload_sweep_point(point, ref, rr, energy, energy_vehicle)
                offloads.append(records)
                offload_runs.append(point_runs)
        sweep = SweepResult(
            k,
            exp.sweeps[k - 1].of,
            axes,
            points,
            results,
            comparisons,
            run_dirs,
            paired,
            offloads,
            offload_runs,
        )
        frame = sweep_index_frame(sweep, baseline, out_dir)
        sweep_dir.mkdir(parents=True, exist_ok=True)
        write_csv(sweep_dir / "sweep_index.csv", frame)
        sweeps.append(sweep)
        frames.append(frame)
    return sweeps, frames, baseline
