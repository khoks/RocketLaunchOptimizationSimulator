"""The local app's launch function, I/O and no HTTP (SP2 step A4; the server is step A4b,
the page A5; docs/phases/inputs/2026-10-05-SP2-design.md, section 4.6 and decisions
D-SP2-09, 10, 11, 12, 25, 26, 37).

- ``load_basis(repo_root, start)``: reads experiments/silo_offload_2d.yaml,
  experiments/silo_screening_2d.yaml and the vehicle file they name as committed at the
  server-start HEAD (``git cat-file``, read-only; the working tree only when git gave no
  HEAD, and then no name is committed) into an ``appform.Basis``; one clear error
  (BasisError) when the checkout or the commit lacks them.
- ``take_server_start(repo_root) -> ServerStart``: ``sim.git_info`` taken once at server
  start, with the full HEAD hash (``head_commit``) for ``load_basis`` and
  ``code_changed``.
- ``code_changed(repo_root, start)``: ``git diff --quiet <start> HEAD -- src configs
  experiments pyproject.toml uv.lock`` (an argument list, never a shell): False for no
  change, True (refused) for a change or when git cannot compare them now, None when git
  was not available at server start (the git record says the check was not made).
- ``BaselineCache``: the pad's RunResult in memory, keyed by the sha256 of the baseline's
  run dict, vehicle dict and server-start git state; a hit is re-wrapped with this
  launch's resolved baseline (dataclasses.replace), so the composition equals the CLI's
  (survey 02 section 3.1); thread-safe.
- ``preflight(basis, form)``: build, resolve, name check and ``sim.check_resolved``; a
  refusal writes nothing.
- ``run_launch(...) -> LaunchOutcome``: the composition of ``results_io.run_experiment``
  with the cached pad (results_io.py unchanged): preflight; the code check; the git
  record (launch-time state, the server-start state, the combined dirty flag);
  ``make_run_dir``; the pad (cache or ``sim.run_resolved``), the variant,
  ``planar_experiment_result`` (sensitivity on, as ``launchsim run`` has it: the app's
  experiment declares no sensitivity block or arm, so none runs; the offload block on) and
  ``write_run`` with no PNG plots by default (D-SP2-26); FAILED.txt on any exception.
  ``progress(stage, info)`` is told each of STAGES with the elapsed time; it never raises
  into the run. The outcome carries the reproduction lines of the committed names the
  launch kept (``reproduction_lines``, D-SP2-36).
- ``classify(out_dir)``: the outcome of a written directory by the table of design 4.6.

Nothing here writes outside the results root it is given, and nothing under results/
unless the caller passes it (reviews and gates launch into a scratch root, D-SP2-37).
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import subprocess
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from launchsim import appform, replay, results_io, run_data, sim, summary
from launchsim.compare import BUG_SUSPECT, CHECK_FAIL, CHECK_NA
from launchsim.config import (
    OFFLOAD_GROSS_MODES,
    ResolvedExperiment,
    ResolvedRun,
    resolve_experiment,
)
from launchsim.offload import NO_OFFLOAD_STATUS
from launchsim.phases.planar import INSERTED_STATUS
from launchsim.results_io import REFERENCE_FAILED_STATUS
from launchsim.search import NO_ORBIT_STATUS, OK_STATUS, SEARCH_FAILED_STATUS
from launchsim.units import kg_to_t

OFFLOAD_EXPERIMENT = PurePosixPath("experiments") / "silo_offload_2d.yaml"
"""The committed experiment whose shared blocks, baseline, silo, offload cases and
energy block every launch copies (D-SP2-31)."""
SCREENING_EXPERIMENT = PurePosixPath("experiments") / "silo_screening_2d.yaml"
"""The committed experiment of the Phase 2 screening variants (the presets of D-SP2-05)."""
CODE_PATHS = ("src", "configs", "experiments", "pyproject.toml", "uv.lock")
"""The paths whose change between the server-start commit and HEAD refuses a launch
(D-SP2-11): committing summaries or documents does not."""
SUMMARY_FILE = "summary.md"
"""results_io.write_summary's file, written last: a directory with it is complete."""
INCOMPLETE_MESSAGE = "neither summary.md nor FAILED.txt: the launch stopped"
METRICS_UNREADABLE_MESSAGE = "metrics.json unreadable: the launch stopped"
METRICS_MISSING_MESSAGE = "metrics.json missing or not a mapping: the launch stopped"
"""The messages of an incomplete directory (``classify``)."""
FAILED_TAIL_BYTES = 8192
"""How much of the end of FAILED.txt ``failed_line`` reads."""
FAILED_LINE_MAX = 200
"""The longest line ``failed_line`` returns."""
PYDANTIC_URL_LINE = "For further information visit"
"""The start of the URL line pydantic appends to an error; never shown as the reason."""

STAGE_PREFLIGHT = "preflight"
STAGE_PAD = "pad"
STAGE_VARIANT = "variant"
STAGE_COMPARISON = "comparison"
STAGE_WRITING = "writing"
STAGES = (STAGE_PREFLIGHT, STAGE_PAD, STAGE_VARIANT, STAGE_COMPARISON, STAGE_WRITING)
"""The five stages the app owns (D-SP2-25): resolve and checks; the pad (cached or
running); the variant; the comparison and the offload pass (one opaque call); writing."""

OUTCOME_REFUSED = "refused"
OUTCOME_CRASHED = "crashed"
OUTCOME_INCOMPLETE = "incomplete"
OUTCOME_DID_NOT_FLY = "did_not_fly"
OUTCOME_NOT_IN_ORBIT = "not_in_orbit"
OUTCOME_OFFLOAD_NOTHING = "offload_found_nothing"
OUTCOME_FLAGGED = "flagged"
OUTCOME_COMPLETE = "complete"
"""The outcomes of design 4.6: refused (nothing written); crashed (FAILED.txt);
incomplete (neither summary.md nor FAILED.txt: a process stopped mid-write); complete
but a run did not fly (a failed search or guidance, an empty time series); complete but
a run did not reach the target orbit (impact, short of orbit, off target); complete
but an offload case found nothing; complete and flagged (flags, a failed verification,
a failing pad control, bug_suspect); complete."""
NOT_FLOWN_STATUSES = (SEARCH_FAILED_STATUS, sim.GUIDANCE_FAILED_STATUS)
"""Run statuses with no recorded run (an empty time series)."""
M5_NOT_MADE_TEXT = "; the M5 anchor check was not made (one variant per launch)"
"""What a complete outcome's message adds when the variant's M5 check reads n/a
(compare.anchor_from needs silo_instant and pad_instant in one experiment)."""
CODE_CHANGED_MESSAGE = (
    "the code under src, configs, experiments, pyproject.toml or uv.lock differs from the "
    "commit the app imported at its start, or git could not compare them: restart the app"
)
"""The refusal of a launch after a code change (D-SP2-11)."""
CODE_CHECK_DONE = (
    "HEAD compared with the server-start commit under src, configs, experiments, "
    "pyproject.toml and uv.lock: no change"
)
CODE_CHECK_SKIPPED = "not checked: git was not available at server start"
"""What the git record's ``code_check`` says."""
CODE_CHECK_KEY = "code_check"
"""Key of the app's git record that says whether the code-change check was made."""
NO_SENSITIVITY_MESSAGE = (
    "the app's experiment declares no sensitivity case and no offload sensitivity arm"
)
"""The refusal of an experiment that would run sensitivity work (a guard: the app's
builder never declares any)."""


class BasisError(run_data.RunDataError):
    """The committed files a launch is built from are missing or unreadable."""


# ------------------------------------------------------------------ basis


def _read(repo_root: Path, rel: PurePosixPath) -> dict[str, Any]:
    """The YAML mapping of a file of the working tree under repo_root (BasisError when it
    is missing, unreadable or not a mapping)."""
    path = Path(repo_root).joinpath(*rel.parts)
    if not path.is_file():
        raise BasisError(
            f"{rel} not found under {repo_root}: the app needs a repository checkout "
            "(experiments/ and configs/ do not ship in the package)"
        )
    data = run_data.read_yaml(path, error=BasisError)
    if not data:
        raise BasisError(f"{rel} under {repo_root} is not a YAML mapping")
    return data


def _read_committed(repo_root: Path, commit: str, rel: PurePosixPath) -> dict[str, Any]:
    """The YAML mapping of the file ``rel`` as committed at ``commit``: ``git cat-file blob
    <commit>:./<rel>`` in repo_root (an argument list, read-only), decoded as UTF-8.
    BasisError when git cannot read it (the file is not in that commit, git is missing, a
    timeout) or it is not a YAML mapping."""
    short = commit[:12]
    try:
        proc = subprocess.run(
            ["git", "cat-file", "blob", f"{commit}:./{rel.as_posix()}"],
            cwd=repo_root,
            capture_output=True,
            timeout=results_io.GIT_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BasisError(f"cannot read {rel} at commit {short}: {_exception_line(exc)}") from exc
    if proc.returncode != 0:
        raise BasisError(
            f"{rel} is not in commit {short} under {repo_root}: commit it, then start the app"
        )
    try:
        data = yaml.safe_load(proc.stdout.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise BasisError(f"cannot read {rel} at commit {short}: {_exception_line(exc)}") from exc
    if not isinstance(data, dict) or not data:
        raise BasisError(f"{rel} at commit {short} is not a YAML mapping")
    return data


def load_basis(repo_root: Path, start: ServerStart) -> appform.Basis:
    """The Basis of a launch from OFFLOAD_EXPERIMENT, SCREENING_EXPERIMENT and the vehicle
    file OFFLOAD_EXPERIMENT names (a path relative to the repository root), read as UTF-8
    YAML. With a server-start HEAD (``start.head``) each file is read as committed at
    that commit (``_read_committed``), never from the working tree, so an uncommitted
    edit of one of them is not used and every name the app keeps as committed is
    committed at that commit (D-SP2-31; ``Basis.commit``). Without one (git not available
    at server start) they are read from the working tree and ``Basis.commit`` is None:
    every name is then neutral and nothing is called a reproduction. Raises BasisError
    with one line when a file is missing or unreadable or the files do not form a basis
    (``appform.make_basis``)."""
    root = Path(repo_root)
    commit = start.head

    def read(rel: PurePosixPath) -> dict[str, Any]:
        return _read(root, rel) if commit is None else _read_committed(root, commit, rel)

    offload = read(OFFLOAD_EXPERIMENT)
    screening = read(SCREENING_EXPERIMENT)
    vehicle_path = offload.get("vehicle")
    if not isinstance(vehicle_path, str) or PurePosixPath(vehicle_path).is_absolute():
        raise BasisError(f"{OFFLOAD_EXPERIMENT}: 'vehicle' must be a path inside the repository")
    vehicle = read(PurePosixPath(vehicle_path))
    try:
        return appform.make_basis(offload, screening, vehicle, commit=commit)
    except ValueError as exc:
        raise BasisError(f"the committed experiments do not form a launch basis: {exc}") from exc


# ------------------------------------------------------------------ provenance


@dataclass(frozen=True)
class ServerStart:
    """The git state of the code the server imported, taken once at its start: ``git``,
    ``sim.git_info``'s record (hash, dirty, error); ``head``, the full HEAD hash for the
    code-change check, None when git was not available."""

    git: dict[str, Any]
    head: str | None

    def record(self) -> dict[str, Any]:
        """The server-start record a launch stores in its git record (a copy)."""
        return dict(self.git)


def head_commit(repo_root: Path) -> str | None:
    """The full hash of HEAD in repo_root, or None (no git, not a repository, no commit,
    a timeout)."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=results_io.GIT_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    head = proc.stdout.strip()
    return head if proc.returncode == 0 and head else None


def take_server_start(repo_root: Path) -> ServerStart:
    """The ServerStart of the repository at repo_root: ``sim.git_info`` and the HEAD
    hash."""
    return ServerStart(git=sim.git_info(Path(repo_root)), head=head_commit(Path(repo_root)))


def code_changed(repo_root: Path, start: ServerStart) -> bool | None:
    """The code-change check of a launch (D-SP2-11): None when it cannot be made because
    git was not available at server start (``start.head`` None; the git record says so,
    CODE_CHECK_SKIPPED); False only when ``git diff --quiet <start.head> HEAD --
    CODE_PATHS`` in repo_root succeeded with no change (committing summaries or documents
    moves HEAD and is not a change); True when it shows a change (HEAD moved and the code
    with it) or git, present at start, cannot compare them now (git missing, a timeout,
    an unknown commit): the launch is refused (CODE_CHANGED_MESSAGE)."""
    if start.head is None:
        return None
    try:
        proc = subprocess.run(
            ["git", "diff", "--quiet", start.head, "HEAD", "--", *CODE_PATHS],
            cwd=repo_root,
            capture_output=True,
            timeout=results_io.GIT_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return True
    return proc.returncode != 0


def combined_dirty(a: bool | None, b: bool | None) -> bool | None:
    """True when either state is dirty; None when either is unknown and neither is
    dirty; else False (D-SP2-11: uncommitted code must never read clean)."""
    if a is True or b is True:
        return True
    if a is None or b is None:
        return None
    return False


def known_dirty(state: Mapping[str, Any]) -> bool | None:
    """The dirty flag of a ``sim.git_info`` record, None (unknown) when its hash is one of
    summary.EXPLORATORY_NO_GIT_HASHES: git_info then reports dirty False although nothing
    is known of the tree."""
    if state.get("hash") in summary.EXPLORATORY_NO_GIT_HASHES:
        return None
    return state.get("dirty")


def launch_git_record(
    launch: Mapping[str, Any],
    start: ServerStart,
    *,
    checked: bool | None,
    basis_commit: str | None = None,
) -> dict[str, Any]:
    """The git record of a launch: the launch-time ``sim.git_info`` record (hash, error)
    with ``dirty`` true when either the launch-time or the server-start tree is dirty and
    None when either is unknown (``combined_dirty`` of ``known_dirty``: a no-git state
    never reads clean), the launch-time flag (``known_dirty``) under
    summary.EXPLORATORY_LAUNCH_DIRTY_KEY, the server-start record under
    summary.EXPLORATORY_SERVER_START_KEY, CODE_CHECK_KEY: CODE_CHECK_DONE only when
    ``checked`` (``code_changed``'s result) is False, else CODE_CHECK_SKIPPED, and the
    commit the experiment files were read from (``Basis.commit``, None when not read from
    a commit) under summary.EXPLORATORY_BASIS_COMMIT_KEY. Plain types only."""
    out = dict(launch)
    out["dirty"] = combined_dirty(known_dirty(launch), known_dirty(start.git))
    out[summary.EXPLORATORY_LAUNCH_DIRTY_KEY] = known_dirty(launch)
    out[summary.EXPLORATORY_SERVER_START_KEY] = start.record()
    out[CODE_CHECK_KEY] = CODE_CHECK_DONE if checked is False else CODE_CHECK_SKIPPED
    out[summary.EXPLORATORY_BASIS_COMMIT_KEY] = basis_commit
    return out


# ------------------------------------------------------------------ baseline cache


class BaselineCache:
    """The pad's RunResult of earlier launches, in memory only (never persisted),
    thread-safe. Key (``key``): the sha256 of the canonical JSON of the baseline's run
    dict, its vehicle dict and the server-start git state (hash, dirty). A hit is
    re-wrapped with this launch's resolved baseline (``dataclasses.replace(cached,
    name=..., resolved=baseline)``): results_io compares the baseline's ResolvedRun by
    identity, and the re-wrap gives exactly the CLI's composition (survey 02, 3.1)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, sim.RunResult] = {}

    @staticmethod
    def key(baseline: ResolvedRun, start: ServerStart) -> str:
        """The cache key of a resolved baseline under a server start (sha256 hex)."""
        payload = {
            "run": baseline.run_dict,
            "vehicle": baseline.vehicle_dict,
            "code": {"hash": start.git.get("hash"), "dirty": start.git.get("dirty")},
        }
        text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, baseline: ResolvedRun, start: ServerStart) -> sim.RunResult | None:
        """The cached pad re-wrapped with ``baseline``, or None."""
        with self._lock:
            hit = self._entries.get(self.key(baseline, start))
        if hit is None:
            return None
        return dataclasses.replace(hit, name=baseline.name, resolved=baseline)

    def has(self, baseline: ResolvedRun, start: ServerStart) -> bool:
        """True when the pad of ``baseline`` is cached."""
        with self._lock:
            return self.key(baseline, start) in self._entries

    def put(self, baseline: ResolvedRun, start: ServerStart, result: sim.RunResult) -> None:
        """Cache the pad ``result`` flown for ``baseline``."""
        with self._lock:
            self._entries[self.key(baseline, start)] = result

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)


# ------------------------------------------------------------------ launch


@dataclass(frozen=True)
class LaunchOutcome:
    """What a launch gave: ``kind`` (one of the OUTCOME_* values); ``out_dir``, the
    directory written (None when refused); ``field``, the form field a refusal marks;
    ``message``, one line (the refusal, the crash's last line or the outcome's headline);
    ``notes``, every row of the outcome table that applies, one line each; ``elapsed_s``;
    ``expected_s``, the expected range [s] (None when refused before it was known);
    ``result``, the in-memory ExperimentResult (None when refused or crashed);
    ``reproduces``, one line per committed name the launch kept (``reproduction_lines``:
    a reproduction, not new evidence; empty when refused before the build)."""

    kind: str
    out_dir: Path | None
    field: str | None
    message: str
    notes: tuple[str, ...] = ()
    elapsed_s: float = 0.0
    expected_s: tuple[float, float] | None = None
    result: results_io.ExperimentResult | None = None
    reproduces: tuple[str, ...] = ()


REPRODUCTION_TAIL = "a reproduction, not new evidence (the code may differ from the recorded run's)"
"""How every reproduction line ends (D-SP2-36)."""


def reproduction_lines(basis: appform.Basis, resolved: ResolvedExperiment) -> tuple[str, ...]:
    """One line per run or case of a resolved launch that kept a committed name
    (``appform.committed_names``): the same configuration as the committed one in its
    experiment file at the commit the basis was read from, so a reproduction, not new
    evidence (D-SP2-36); for a launch of the pad alone, one line saying it is the
    committed baseline of both files. () on a basis not read from a commit
    (``Basis.commit`` None). The code is not claimed to be the recorded run's."""
    if basis.commit is None:
        return ()
    commit = basis.commit[:12]
    if not resolved.variants:
        return (
            f"{resolved.baseline.name}: the committed baseline of {OFFLOAD_EXPERIMENT} and "
            f"{SCREENING_EXPERIMENT} at commit {commit}: {REPRODUCTION_TAIL}",
        )
    out: list[str] = []
    for name in appform.committed_names(basis, resolved):
        in_offload = name in (basis.offload_experiment.get("variants") or {}) or (
            name in basis.case_fragments
        )
        source = OFFLOAD_EXPERIMENT if in_offload else SCREENING_EXPERIMENT
        out.append(
            f"{name}: same configuration as the committed {name} in {source} at commit "
            f"{commit}: {REPRODUCTION_TAIL}"
        )
    return tuple(out)


ProgressFn = Callable[[str, dict[str, Any]], None]
"""progress(stage, info): stage one of STAGES; info holds ``elapsed_s`` [s],
``expected_s`` ([lo, hi] s, or None) and the stage's own items."""


class _Progress:
    """Reports stages to a progress callback with the elapsed time since the launch
    started; an exception in the callback is swallowed (it must never stop a run)."""

    def __init__(self, callback: ProgressFn | None) -> None:
        self.callback = callback
        self.t0 = time.monotonic()
        self.expected: tuple[float, float] | None = None

    def elapsed(self) -> float:
        """Seconds since the launch started."""
        return time.monotonic() - self.t0

    def __call__(self, stage: str, **items: Any) -> None:
        if self.callback is None:
            return
        info = {
            "elapsed_s": self.elapsed(),
            "expected_s": None if self.expected is None else list(self.expected),
            **items,
        }
        try:
            self.callback(stage, info)
        except Exception:  # a broken progress display never stops a run
            pass


def preflight(
    basis: appform.Basis, form: appform.Form
) -> tuple[ResolvedExperiment, None] | tuple[None, appform.Refusal]:
    """(resolved experiment, None) for a launch that passes every check before anything
    is written, else (None, Refusal): ``appform.build_experiment``, ``resolve_experiment``
    against a copy of the basis vehicle, ``results_io.check_result_names``,
    ``sim.check_resolved`` (the ramp-start conversions and the drag-free apex), no
    sensitivity case or offload sensitivity arm (the app declares none, so
    ``run_launch``'s sensitivity switch runs nothing: NO_SENSITIVITY_MESSAGE) and
    ``appform.derived`` (every derived value finite), each ValueError turned into one
    line by ``appform.refusal_text``."""
    try:
        exp = appform.build_experiment(basis, form)
        resolved = resolve_experiment(exp, basis.vehicle_copy())
        results_io.check_result_names(resolved)
        sim.check_resolved(resolved)
        if resolved.sensitivity or (resolved.offload is not None and resolved.offload.arms):
            raise ValueError(NO_SENSITIVITY_MESSAGE)
        appform.derived(resolved)
    except ValueError as exc:
        return None, appform.refusal(exc, form)
    return resolved, None


def dry_run(
    basis: appform.Basis,
    form: appform.Form,
    *,
    cache: BaselineCache | None = None,
    server_start: ServerStart | None = None,
) -> dict[str, Any] | appform.Refusal:
    """The check a page runs as the form changes (nothing written, nothing flown): the
    Refusal of ``preflight``, or ``appform.derived`` of the resolved launch with the pad
    left out of the expected duration when it is cached (a Refusal, never a non-finite
    value, when a derived value is not finite) and ``reproduces``
    (``reproduction_lines``)."""
    resolved, refused = preflight(basis, form)
    if refused is not None:
        return refused
    assert resolved is not None
    cached = (
        cache is not None
        and server_start is not None
        and cache.has(resolved.baseline, server_start)
    )
    try:
        values = appform.derived(resolved, pad_cached=cached)
    except ValueError as exc:
        return appform.refusal(exc, form)
    return {**values, "reproduces": list(reproduction_lines(basis, resolved))}


def offload_work(resolved: ResolvedExperiment) -> list[str]:
    """What the comparison stage's offload pass will do, known before it starts (survey
    02, 7.1): each pad control, each case (solved with its verification, or imposed) and
    each paired pad; [] without an offload block."""
    if resolved.offload is None:
        return []
    out = [f"pad control {mode}" for mode in resolved.offload.pad_control_modes]
    for case in resolved.offload.cases:
        kind = "solve with its verification" if case.config.solved else "imposed offload"
        out.append(f"{kind}: {case.name}")
        if case.pad_start is not None:
            out.append(f"paired pad: {case.pad_start.name}")
    return out


def _exception_line(exc: BaseException) -> str:
    """'<type>: <first line>' of an exception, at most FAILED_LINE_MAX characters."""
    lines = str(exc).strip().splitlines()
    text = f"{type(exc).__name__}: {lines[0]}" if lines else type(exc).__name__
    return text[:FAILED_LINE_MAX]


def run_launch(
    basis: appform.Basis,
    form: appform.Form,
    *,
    results_root: Path,
    repo_root: Path,
    cache: BaselineCache,
    server_start: ServerStart,
    plots: bool = False,
    progress: ProgressFn | None = None,
) -> LaunchOutcome:
    """Launch one form (no HTTP), composing results_io's public pieces in
    ``run_experiment``'s order with the pad from the cache:

    1. STAGE_PREFLIGHT: ``preflight`` (a refusal returns OUTCOME_REFUSED and writes
       nothing); ``code_changed`` True refuses too (CODE_CHANGED_MESSAGE);
    2. the git record (``launch_git_record`` of ``sim.git_info`` at launch, server_start,
       the code check's result and the basis commit); ``results_io.make_run_dir(
       results_root, 'app', now)``;
    3. STAGE_PAD: the cached pad (re-wrapped) or ``sim.run_resolved(resolved.baseline)``,
       then cached; STAGE_VARIANT: ``sim.run_resolved`` of the variant;
       STAGE_COMPARISON: ``results_io.planar_experiment_result`` (sensitivity on, as
       ``launchsim run`` has it: the app's experiment declares no sensitivity block or
       arm, so none runs and summary.md says none is declared; the calibration cases and
       the offload block on); STAGE_WRITING: ``results_io.write_run`` (``plots`` False by
       default: an app launch writes no PNG, D-SP2-26);
    4. any exception after the directory exists writes FAILED.txt
       (``results_io.write_failure_marker``) and returns OUTCOME_CRASHED with the
       marker's reason (``failed_line``, as ``classify`` reads it later; the exception's
       first line only when no marker could be written), except KeyboardInterrupt and
       SystemExit, which are re-raised after the marker;
    5. otherwise the outcome of the written directory (``classify``), with the
       reproduction lines of the committed names it kept (``reproduction_lines``).

    ``progress(stage, info)`` is told each stage with the elapsed time and the expected
    range (``appform.derived``); it never raises into the run."""
    report = _Progress(progress)
    report(STAGE_PREFLIGHT)
    resolved, refused = preflight(basis, form)
    if refused is not None:
        return LaunchOutcome(
            OUTCOME_REFUSED, None, refused.field, refused.message, elapsed_s=report.elapsed()
        )
    assert resolved is not None
    reproduces = reproduction_lines(basis, resolved)
    root = Path(repo_root)
    checked = code_changed(root, server_start)
    if checked is True:
        return LaunchOutcome(
            OUTCOME_REFUSED,
            None,
            None,
            CODE_CHANGED_MESSAGE,
            elapsed_s=report.elapsed(),
            reproduces=reproduces,
        )
    cached = cache.has(resolved.baseline, server_start)
    lo, hi = appform.derived(resolved, pad_cached=cached)["expected_s"]
    report.expected = (lo, hi)
    git = launch_git_record(
        sim.git_info(root), server_start, checked=checked, basis_commit=basis.commit
    )
    now = datetime.now(UTC)  # one clock read: the directory name and timestamp_utc agree
    out_dir = results_io.make_run_dir(Path(results_root), resolved.experiment.name, now=now)
    try:
        baseline = cache.get(resolved.baseline, server_start)
        report(STAGE_PAD, cached=baseline is not None, run=resolved.baseline.name)
        if baseline is None:
            baseline = sim.run_resolved(resolved.baseline)
            cache.put(resolved.baseline, server_start, baseline)
        report(STAGE_VARIANT, runs=list(resolved.variants))
        variants = {name: sim.run_resolved(run) for name, run in resolved.variants.items()}
        report(STAGE_COMPARISON, offload=offload_work(resolved))
        er = results_io.planar_experiment_result(
            resolved,
            baseline,
            variants,
            git,
            results_io.utc_timestamp(now),
            sensitivity=True,
            run_cases=True,
            offload=True,
        )
        report(STAGE_WRITING)
        results_io.write_run(er, out_dir, plots)
    except BaseException as exc:
        results_io.write_failure_marker(out_dir, exc)
        if isinstance(exc, KeyboardInterrupt | SystemExit):
            raise
        marker = out_dir / results_io.FAILED_MARKER
        # the marker's own reason, so a fresh launch and the directory read later agree
        message = (failed_line(marker) if marker.is_file() else "") or _exception_line(exc)
        return LaunchOutcome(
            OUTCOME_CRASHED,
            out_dir,
            None,
            message,
            elapsed_s=report.elapsed(),
            expected_s=(lo, hi),
            reproduces=reproduces,
        )
    kind, message, notes = classify(out_dir)
    return LaunchOutcome(
        kind, out_dir, None, message, notes, report.elapsed(), (lo, hi), er, reproduces
    )


# ------------------------------------------------------------------ outcome of a directory


def failed_line(marker: Path) -> str:
    """The reason in a FAILED.txt: of its last FAILED_TAIL_BYTES, the last line that is
    not blank, not indented (a traceback frame) and not pydantic's URL line, cut to
    FAILED_LINE_MAX characters; '' when there is none."""
    data = marker.read_bytes()[-FAILED_TAIL_BYTES:].decode("utf-8", errors="replace")
    for line in reversed(data.splitlines()):
        if line.strip() and not line[0].isspace() and not line.startswith(PYDANTIC_URL_LINE):
            return line.strip()[:FAILED_LINE_MAX]
    return ""


def _run_notes(runs: Mapping[str, Any], comparison: Mapping[str, Any]) -> dict[str, list[str]]:
    """The outcome rows of the experiment runs: not flown, not in orbit, flagged."""
    notes: dict[str, list[str]] = {
        OUTCOME_DID_NOT_FLY: [],
        OUTCOME_NOT_IN_ORBIT: [],
        OUTCOME_FLAGGED: [],
    }
    for name, m in runs.items():
        status = m.get("status")
        if status in NOT_FLOWN_STATUSES:
            why = m.get("search_failure_kind") or m.get("guidance_failure_kind") or "no reason"
            notes[OUTCOME_DID_NOT_FLY].append(f"{name} did not fly: {status} ({why})")
        elif status == BUG_SUSPECT:
            notes[OUTCOME_FLAGGED].append(f"{name}: status {BUG_SUSPECT}")
        elif status != INSERTED_STATUS:
            notes[OUTCOME_NOT_IN_ORBIT].append(f"{name} did not reach the target orbit: {status}")
        if m.get("flags"):
            notes[OUTCOME_FLAGGED].append(f"{name}: {len(m['flags'])} flag(s)")
    for name, c in comparison.items():
        if isinstance(c, Mapping) and c.get("screening_status") == BUG_SUSPECT:
            notes[OUTCOME_FLAGGED].append(f"{name} against the baseline: {BUG_SUSPECT}")
    return notes


def _imposed_case_note(name: Any, status: Any) -> tuple[str, str] | None:
    """(outcome, line) of an imposed (fixed) offload case whose payload search did not
    end ok: its offloaded vehicle did not fly (search_failed, or no run), reaches no orbit
    at any payload (no_orbit), or another search status; None when ok. Nothing was
    searched for, so an imposed case never 'finds nothing'."""
    if status == OK_STATUS:
        return None
    if status is None or status == SEARCH_FAILED_STATUS:
        return (
            OUTCOME_DID_NOT_FLY,
            f"imposed offload {name}: the offloaded vehicle did not fly ({status})",
        )
    if status == NO_ORBIT_STATUS:
        return (
            OUTCOME_NOT_IN_ORBIT,
            f"imposed offload {name}: the offloaded vehicle reaches no orbit at any payload "
            f"({NO_ORBIT_STATUS})",
        )
    return OUTCOME_NOT_IN_ORBIT, f"imposed offload {name}: its payload search ended {status}"


def _tonnes(value: Any) -> str:
    """A mass [kg] of an offload record in tonnes for an outcome line, or 'none'."""
    if isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value):
        return f"{float(kg_to_t(float(value))):.3f} t"
    return "none"


def _solved_case_note(c: Mapping[str, Any], verdict: str) -> tuple[str, str] | None:
    """(outcome, line) of a solved offload case ``c`` (its metrics.json record) that did
    not end ok, or that nets to nothing: the solve did not fly (search_failed); found no
    offload at P_ref (no_offload, with the pad controls' verdicts); nothing solved because
    the pad has no P* (reference_failed); another status; a stage-2 or both solve that
    ended ok but quotes nothing net of its pad control (no x_pad to net against, or x*
    minus x_pad at or below zero: what such a case reports is the net value, D-SP1-10);
    None otherwise."""
    name, status = c.get("name"), c.get("status")
    if status == OK_STATUS:
        net = c.get("net_offload_kg")
        netted = c.get("mode") is not None and c.get("mode") not in OFFLOAD_GROSS_MODES
        if netted and (
            c.get("quoted_offload_kg") is None
            or (isinstance(net, int | float) and not isinstance(net, bool) and net <= 0.0)
        ):
            return (
                OUTCOME_OFFLOAD_NOTHING,
                f"offload case {name}: nothing net of the pad control (x* "
                f"{_tonnes(c.get('offload_kg'))}, pad control "
                f"{_tonnes(c.get('pad_control_offload_kg'))}, net {_tonnes(net)}) ({verdict})",
            )
        return None
    if status == SEARCH_FAILED_STATUS:
        return OUTCOME_DID_NOT_FLY, f"offload case {name}: the solve did not fly ({status})"
    if status == NO_OFFLOAD_STATUS:
        return (
            OUTCOME_OFFLOAD_NOTHING,
            f"offload case {name} found no offload at P_ref: {status} ({verdict})",
        )
    if status == REFERENCE_FAILED_STATUS:
        return (
            OUTCOME_OFFLOAD_NOTHING,
            f"offload case {name}: nothing solved, the pad has no P* ({status})",
        )
    return OUTCOME_OFFLOAD_NOTHING, f"offload case {name}: {status} ({verdict})"


def _pad_control_notes(p: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(outcome, line) rows of one pad control record ``p``: a control whose solve did
    not end ok or no_offload did not fly (a stage-1 control was the solver's consistency
    test on the pad; a stage-2 or both control is what its cases are netted against); a
    control with no recorded run whose solve carries flags (no run of the offload block
    carries them); a failing consistency; a failed verification."""
    mode, status = p.get("mode"), p.get("status")
    rows: list[tuple[str, str]] = []
    if status not in (OK_STATUS, NO_OFFLOAD_STATUS):
        lost = (
            "the solver's consistency test on the pad was not made"
            if mode in OFFLOAD_GROSS_MODES
            else f"no {mode} case can be netted against it"
        )
        rows.append((OUTCOME_DID_NOT_FLY, f"pad control {mode} did not fly ({status}): {lost}"))
    if p.get("run") is None and p.get("flags"):
        rows.append((OUTCOME_FLAGGED, f"pad control {mode}: {len(p['flags'])} flag(s)"))
    if p.get("consistency") == CHECK_FAIL:
        rows.append(
            (OUTCOME_FLAGGED, f"pad control {mode}: consistency {CHECK_FAIL} (blocks findings)")
        )
    if (p.get("verification") or {}).get("passed") is False:
        rows.append((OUTCOME_FLAGGED, f"pad control {mode}: verification failed"))
    return rows


def _verdict_note(offload: Mapping[str, Any], c: Mapping[str, Any]) -> str | None:
    """The flagged row of a case's verdicts, in the words of the replay page and the
    scene (``replay.offload_verdict_clause``, its flag count left out: case flags are a
    row of their own): a failed verification read from the sign of its P* - P_ref (a
    flagged lower bound only above P_ref; below it uncertain both ways; a search that
    did not end ok, unverified), and for a stage-2 or both-stage case whose pad control
    carries flags, that the net figure is uncertain both ways; None when neither
    applies."""
    mode = c.get("mode")
    control = (
        None
        if mode is None or mode in OFFLOAD_GROSS_MODES
        else replay.pad_control_record(offload, mode)
    )
    clause = replay.offload_verdict_clause({**c, "flags": []}, control)
    if not clause:
        return None
    return f"offload case {c.get('name')}: {clause.removeprefix('; ')}"


def _paired_pad_note(c: Mapping[str, Any]) -> str | None:
    """The not-in-orbit row of a case's paired pad (its record in the case) that ended
    neither inserted nor bug_suspect (a flagged row of the offload runs) nor without a
    recorded run (a did-not-fly row of the offload runs): short of orbit, impact, off
    target; None otherwise, and for a record without a status."""
    pp = c.get("paired_pad")
    if not isinstance(pp, Mapping):
        return None
    status = pp.get("status")
    if status is None or status in (INSERTED_STATUS, BUG_SUSPECT, *NOT_FLOWN_STATUSES):
        return None
    return f"paired pad {pp.get('run')} did not reach the target orbit: {status}"


def _offload_notes(offload: Mapping[str, Any]) -> dict[str, list[str]]:
    """The outcome rows of an offload record (every kind of OUTCOME_ORDER): a case that
    did not end ok or nets to nothing (``_imposed_case_note`` for an imposed case,
    ``_solved_case_note`` for a solved one, with the pad controls' verdicts); a case's
    paired pad that did not reach the target orbit (``_paired_pad_note``); each pad
    control (``_pad_control_notes``: not flown, flags without a run, a failing
    consistency, a failed verification); flagged: a case's verdicts (``_verdict_note``: a
    failed verification read from the sign of its P* - P_ref, and a net figure that
    subtracts a flagged pad control), case flags, a bug_suspect offload decomposition or
    paired-pad comparison (``summary.offload_check_comparisons``, as summary.md's Checks
    section reads them); and every run the block wrote (pad controls, paired pads; a
    case's own run when its case row did not already say so): not flown (search or
    guidance failed), bug_suspect, flags."""
    controls = [
        f"pad control {p.get('mode')}: {p.get('status')}, consistency {p.get('consistency')}"
        for p in offload.get("pad_controls") or []
    ]
    verdict = "; ".join(controls) if controls else "no pad control"
    notes: dict[str, list[str]] = {kind: [] for kind in OUTCOME_ORDER}
    case_runs: set[str] = set()
    said_not_flown: set[str] = set()
    for c in offload.get("cases") or []:
        if c.get("skipped"):
            continue
        name = c.get("name")
        if c.get("kind") == "fixed":
            row = _imposed_case_note(name, c.get("status"))
        else:
            row = _solved_case_note(c, verdict)
        if row is not None:
            notes[row[0]].append(row[1])
        if c.get("run"):
            case_runs.add(str(c["run"]))
            if row is not None and row[0] == OUTCOME_DID_NOT_FLY:
                said_not_flown.add(str(c["run"]))
        paired = _paired_pad_note(c)
        if paired is not None:
            notes[OUTCOME_NOT_IN_ORBIT].append(paired)
        verdict_row = _verdict_note(offload, c)
        if verdict_row is not None:
            notes[OUTCOME_FLAGGED].append(verdict_row)
        if c.get("flags"):
            notes[OUTCOME_FLAGGED].append(f"offload case {name}: {len(c['flags'])} flag(s)")
    for label, c in summary.offload_check_comparisons(offload):
        if c.get("screening_status") == BUG_SUSPECT:
            notes[OUTCOME_FLAGGED].append(f"{label}: {BUG_SUSPECT}")
    for p in offload.get("pad_controls") or []:
        for kind, line in _pad_control_notes(p):
            notes[kind].append(line)
    for name, m in (offload.get("runs") or {}).items():
        if not isinstance(m, Mapping):
            continue
        if m.get("status") in NOT_FLOWN_STATUSES and name not in said_not_flown:
            notes[OUTCOME_DID_NOT_FLY].append(f"{name} did not fly: {m['status']}")
        if name in case_runs:
            continue
        if m.get("status") == BUG_SUSPECT:
            notes[OUTCOME_FLAGGED].append(f"{name}: status {BUG_SUSPECT}")
        if m.get("flags"):
            notes[OUTCOME_FLAGGED].append(f"{name}: {len(m['flags'])} flag(s)")
    return notes


OUTCOME_ORDER = (
    OUTCOME_DID_NOT_FLY,
    OUTCOME_NOT_IN_ORBIT,
    OUTCOME_OFFLOAD_NOTHING,
    OUTCOME_FLAGGED,
)
"""The order in which a complete directory's rows decide its kind (the first that
applies)."""


def classify(out_dir: Path) -> tuple[str, str, tuple[str, ...]]:
    """(kind, one-line message, notes) of a results directory by the table of design
    4.6: OUTCOME_CRASHED with ``failed_line`` when FAILED.txt exists; OUTCOME_INCOMPLETE
    without summary.md, or with a metrics.json that is missing, not a mapping or cannot
    be read (cut short by a killed process); else the first of OUTCOME_ORDER whose rows
    apply (``_run_notes``, ``_offload_notes``; the notes list every row), or
    OUTCOME_COMPLETE with a message that claims only what was checked: the baseline and
    the variant (the names in metrics.json's ``runs``) reached the target orbit, and no
    flag, failed verification or bug_suspect check (a stage-1 pad control that ends
    no_offload is recorded short of orbit by design and is not claimed), with
    M5_NOT_MADE_TEXT when a comparison's M5 check reads n/a. Reads only metrics.json (and
    whether FAILED.txt and summary.md exist)."""
    out_dir = Path(out_dir)
    marker = out_dir / results_io.FAILED_MARKER
    if marker.is_file():
        return OUTCOME_CRASHED, failed_line(marker), ()
    if not (out_dir / SUMMARY_FILE).is_file():
        return OUTCOME_INCOMPLETE, INCOMPLETE_MESSAGE, ()
    try:
        metrics = run_data.read_json(out_dir / run_data.METRICS_FILE, error=run_data.RunDataError)
    except run_data.RunDataError:
        return OUTCOME_INCOMPLETE, METRICS_UNREADABLE_MESSAGE, ()
    if not metrics:
        return OUTCOME_INCOMPLETE, METRICS_MISSING_MESSAGE, ()
    runs = metrics.get("runs") or {}
    rows = _run_notes(runs, metrics.get("comparison") or {})
    offload = _offload_notes(metrics.get("offload") or {})
    for kind in OUTCOME_ORDER:
        rows[kind] = [*rows.get(kind, []), *offload[kind]]
    notes = tuple(line for kind in OUTCOME_ORDER for line in rows[kind])
    for kind in OUTCOME_ORDER:
        if rows[kind]:
            return kind, rows[kind][0], notes
    names = ", ".join(str(name) for name in runs)
    comparison = metrics.get("comparison") or {}
    m5_na = any(
        isinstance(c, Mapping)
        and isinstance(c.get("checks_m5"), Mapping)
        and c["checks_m5"].get("status") == CHECK_NA
        for c in comparison.values()
    )
    return (
        OUTCOME_COMPLETE,
        f"complete: {names} reached the target orbit; no flag, failed verification or "
        f"{BUG_SUSPECT} check" + (M5_NOT_MADE_TEXT if m5_na else ""),
        notes,
    )
