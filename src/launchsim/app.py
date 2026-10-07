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
  into the run, except the server's LaunchInterrupted once it has stopped the launch
  (FAILED.txt, nothing more written). The outcome carries the reproduction lines of the
  committed names the launch kept (``reproduction_lines``, D-SP2-36).
- ``classify(out_dir)``: the outcome of a written directory by the table of design 4.6.

The local server (SP2 step A4b; design 4.6, decisions D-SP2-09, 11, 22, 29, 32, 36, 37;
survey 07 sections 3 to 6; review 04):

- ``AppServer``: a ThreadingHTTPServer bound to BIND_HOST only (IPv4, exclusive binding,
  a fixed port probed on the IPv4 wildcard and the IPv6 loopback first, no address
  reuse, no reverse lookup), owning the basis, the server-start record, the
  BaselineCache, the one job slot (check-and-start under one lock; the launch runs in one
  daemon worker thread calling ``run_launch``), the listing, row, scene-page and
  results-panel caches and a boot id; a context manager whose exit shuts the server down
  from another thread, closes its socket and joins the worker with a timeout.
  ``stop_active_job`` refuses later launches (503) and writes FAILED.txt for the running
  launch's directory, or the worker does once it makes one (Ctrl+C or Ctrl+Break on the
  console).
- ``AppHandler``: only do_GET and do_POST; HTTP/1.1 with kept connections (fix round 3 of
  A6v: one connection carries an export's frame POSTs instead of one per frame), every
  response with a Content-Length, the connection closed after a refusal or an error (its
  body may be unread) and once the server is stopping; each request must arrive within
  HANDLER_TIMEOUT_S of its start (``DeadlineReader``, armed per request); every request
  passes ``guard`` before any body byte is read (Host, Origin, the target's form,
  Sec-Fetch-Site, no query, the path split before it is decoded and each segment decoded
  once); every response carries
  FIXED_HEADERS and a frame policy and Content-Security-Policy (the app page DENY with
  its script by sha256, a scene page SAMEORIGIN, everything else DENY and nothing
  allowed); errors are JSON with a fixed message and never a traceback or a local path.
- Routes (ROUTES): GET / (the app page), GET /api/form, POST /api/launches, GET
  /api/job, GET /api/results, GET /api/results/<experiment>/<timestamp>, GET
  /api/panel/<experiment>/<timestamp>/<runs> (the results panel of the runs the page's
  scene shows; step A5), GET /scene/<experiment>/<timestamp>/<runs>; every other path is
  404.
- The page (step A5, templates/app.html): GET / says in its data block whether the
  request came from another site (``from_other_site``: Sec-Fetch-Site same-site or
  cross-site), and the page then acts on nothing until the user does; GET /api/form adds
  what the page's form needs beside the fields: a starting value per field
  (``form_defaults``), one per imposed-offload key (``fixed_defaults``), the silo details
  the form shows read-only (``silo_fixed``) and the Advanced forms with their readings.
- The run browser (``AppServer.results`` over ``listed_directories``, kept per folder by
  ``AppServer.listing``; ``directory_row``) and the results panel (``results_panel``:
  the headline with its verdicts, SP1's headline and caveat groups for SP1's case, the
  comparison with SP1's case, ``sp1_comparison``) are built from the directories on
  disk, one at a time, never written to; a directory is addressed only as
  <experiment>/<timestamp> and looked up in the server's own listing of the results root
  (``AppServer.find``).
- SP1_HEADLINE: the headline of docs/findings/RQ1-fuel-offload-2d.md (verbatim) with its
  six caveat groups, in one constant (D-SP2-36; a test finds the headline and every
  number in the note).
- The MP4 export (step A6v; design 4.8, D-SP2-30; video.py holds the session): POST
  /api/videos fixes one session (the directory and 1 to PANEL_RUNS of its runs, fps and
  width from fixed lists, 1 to 1,800 frames, the scene times the page computed, and the
  caveat footer the server computes: ``video_footer``, plots.animation_caveats of the
  shown runs; the display-only caveat is the scene page's own footer line on every
  captured frame) and answers its unguessable id; POST /api/videos/<id>/frames/<n> takes
  one image/png body (``AppHandler._png_body``: the one exception to the JSON body rule;
  Host, Origin and Sec-Fetch-Site checks unchanged), checked as a PNG of the session's
  size before it is piped to ffmpeg; a refusal of a declared body within the frame cap is
  answered after the body is read and discarded (``_drain``), so the client sees the
  refusal and not a reset connection; POST /api/videos/<id>/finish (202, then GET
  /api/videos/<id> is polled for the state and the absolute path) and POST
  /api/videos/<id>/cancel, each with an empty JSON object (any key is 422, as for every
  POST). A launch and a video never run together (409 each way). The file goes to the
  server's working directory, never into a results tree. ffmpeg is resolved once at start
  (video.find_ffmpeg, from cli.py).

Nothing here writes outside the results root it is given, and nothing under results/
unless the caller passes it (reviews and gates launch into a scratch root, D-SP2-37); the
one other thing it writes is a video in its working directory.
"""

from __future__ import annotations

import base64
import dataclasses
import errno
import hashlib
import http.server
import io
import json
import math
import os
import re
import secrets
import socket
import socketserver
import stat
import subprocess
import sys
import threading
import time
import urllib.parse
from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from importlib import resources
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from launchsim import (
    __version__,
    appform,
    plots,
    replay,
    results_io,
    run_data,
    scene,
    sim,
    summary,
    video,
)
from launchsim.compare import BUG_SUSPECT, CHECK_FAIL, CHECK_NA
from launchsim.config import (
    OFFLOAD_FIXED_MODES,
    OFFLOAD_GROSS_MODES,
    PLANAR_2D,
    VERTICAL_1D,
    ResolvedExperiment,
    ResolvedRun,
    resolve_experiment,
)
from launchsim.offload import NO_OFFLOAD_STATUS
from launchsim.phases.planar import INSERTED_STATUS
from launchsim.results_io import REFERENCE_FAILED_STATUS
from launchsim.search import NO_ORBIT_STATUS, OK_STATUS, SEARCH_FAILED_STATUS
from launchsim.units import kg_to_t, pa_to_kpa, to_percent
from launchsim.vehicle import offload_load_kg

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
M5_NOT_MADE_TEXT = (
    "; the screening check against the instant-start yardsticks (an assisted run may not "
    "beat the instant-start silo's gain at its release speed) was not made: it needs "
    "silo_instant and pad_instant in one directory, and this directory does not have both"
)
"""What a complete outcome's message adds when a comparison's M5 check reads n/a
(compare.anchor_from needs silo_instant and pad_instant in one experiment): true of an
app launch (one variant) and of a recorded directory alike. In words, not the check's
ID (the page shows it)."""
COMPLETE_CHECKS_TEXT = (
    "no flag, no failed verification and no result marked as a suspected bug "
    f"(status {BUG_SUSPECT}) recorded"
)
"""What a complete outcome's message says was checked: the three things ``classify``
reads, in words (the status name kept in parentheses, as summary.md writes it)."""
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


def baseline_reproduction_line(baseline: str, commit: str) -> str:
    """The reproduction line of a launch of the pad alone: the committed baseline of both
    experiment files at ``commit`` (its first 12 characters shown)."""
    return (
        f"{baseline}: the committed baseline of {OFFLOAD_EXPERIMENT} and "
        f"{SCREENING_EXPERIMENT} at commit {commit[:12]}: {REPRODUCTION_TAIL}"
    )


def committed_reproduction_line(basis: appform.Basis, name: str, commit: str) -> str:
    """The reproduction line of a run or case kept under its committed name ``name``: the
    same configuration as the committed one in its experiment file (the offload file for
    its variants and cases, else the screening file) at ``commit``."""
    in_offload = name in (basis.offload_experiment.get("variants") or {}) or (
        name in basis.case_fragments
    )
    source = OFFLOAD_EXPERIMENT if in_offload else SCREENING_EXPERIMENT
    return (
        f"{name}: same configuration as the committed {name} in {source} at commit "
        f"{commit[:12]}: {REPRODUCTION_TAIL}"
    )


def reproduction_lines(basis: appform.Basis, resolved: ResolvedExperiment) -> tuple[str, ...]:
    """One line per run or case of a resolved launch that kept a committed name
    (``appform.committed_names``): the same configuration as the committed one in its
    experiment file at the commit the basis was read from, so a reproduction, not new
    evidence (D-SP2-36); for a launch of the pad alone, one line saying it is the
    committed baseline of both files. () on a basis not read from a commit
    (``Basis.commit`` None). The code is not claimed to be the recorded run's."""
    if basis.commit is None:
        return ()
    if not resolved.variants:
        return (baseline_reproduction_line(resolved.baseline.name, basis.commit),)
    return tuple(
        committed_reproduction_line(basis, name, basis.commit)
        for name in appform.committed_names(basis, resolved)
    )


ProgressFn = Callable[[str, dict[str, Any]], None]
"""progress(stage, info): stage one of STAGES; info holds ``elapsed_s`` [s],
``expected_s`` ([lo, hi] s, or None) and the stage's own items."""


class _Progress:
    """Reports stages to a progress callback with the elapsed time since the launch
    started; an Exception in the callback is swallowed (a broken display must never stop
    a run). A BaseException passes: the server's LaunchInterrupted stops a launch the
    server has stopped (``AppServer._progress``)."""

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
    range (``appform.derived``); STAGE_PAD also carries ``out_dir``, the directory just
    made (the server's job snapshot, run browser and stop handling need it while the
    launch runs); it never raises into the run, except the server's LaunchInterrupted (a
    BaseException) in a launch the server has stopped, handled by step 4."""
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
        report(STAGE_PAD, cached=baseline is not None, run=resolved.baseline.name, out_dir=out_dir)
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


def read_tail(path: Path, size: int) -> bytes:
    """The last ``size`` bytes of the file at ``path`` (all of a shorter file), read
    without reading the rest (binary, io.FileIO)."""
    with io.FileIO(path, "r") as fh:
        end = fh.seek(0, io.SEEK_END)
        fh.seek(max(0, end - size))
        return fh.read() or b""


def failed_line(marker: Path) -> str:
    """The reason in a FAILED.txt: of its last FAILED_TAIL_BYTES (only those are read),
    the last line that is not blank, not indented (a traceback frame) and not pydantic's
    URL line, cut to FAILED_LINE_MAX characters; '' when there is none."""
    data = read_tail(marker, FAILED_TAIL_BYTES).decode("utf-8", errors="replace")
    for line in reversed(data.splitlines()):
        if line.strip() and not line[0].isspace() and not line.startswith(PYDANTIC_URL_LINE):
            return line.strip()[:FAILED_LINE_MAX]
    return ""


def flags_text(count: int) -> str:
    """A count of flags as an outcome row states it: '1 flag' or '<count> flags'."""
    return "1 flag" if count == 1 else f"{count} flags"


def _status_notes(name: str, m: Mapping[str, Any], notes: dict[str, list[str]]) -> None:
    """Add the outcome rows of one run's metrics record ``m`` (named ``name`` in them) to
    ``notes``: not flown (search or guidance failed), bug_suspect, not in orbit, flags."""
    status = m.get("status")
    if status in NOT_FLOWN_STATUSES:
        why = m.get("search_failure_kind") or m.get("guidance_failure_kind") or "no reason"
        notes[OUTCOME_DID_NOT_FLY].append(f"{name} did not fly: {status} ({why})")
    elif status == BUG_SUSPECT:
        notes[OUTCOME_FLAGGED].append(f"{name}: status {BUG_SUSPECT}")
    elif status != INSERTED_STATUS:
        notes[OUTCOME_NOT_IN_ORBIT].append(f"{name} did not reach the target orbit: {status}")
    if m.get("flags"):
        notes[OUTCOME_FLAGGED].append(f"{name}: {flags_text(len(m['flags']))}")


def _comparison_note(label: str, c: Any, notes: dict[str, list[str]]) -> None:
    """Add a flagged row ``<label>: bug_suspect`` when the comparison ``c`` is
    bug_suspect."""
    if isinstance(c, Mapping) and c.get("screening_status") == BUG_SUSPECT:
        notes[OUTCOME_FLAGGED].append(f"{label}: {BUG_SUSPECT}")


def _run_notes(runs: Mapping[str, Any], comparison: Mapping[str, Any]) -> dict[str, list[str]]:
    """The outcome rows of the experiment runs: not flown, not in orbit, flagged."""
    notes: dict[str, list[str]] = {
        OUTCOME_DID_NOT_FLY: [],
        OUTCOME_NOT_IN_ORBIT: [],
        OUTCOME_FLAGGED: [],
    }
    for name, m in runs.items():
        _status_notes(str(name), m, notes)
    for name, c in comparison.items():
        _comparison_note(f"{name} against the baseline", c, notes)
    return notes


def _extra_notes(metrics: Mapping[str, Any]) -> dict[str, list[str]]:
    """The outcome rows of the runs metrics.json records beside ``runs`` (the rows of
    ``_run_notes``, each run named with its kind): the calibration ``cases`` ('<name>
    (case)'), each bound's re-run and paired baseline ('<run> (bound)', '<paired>
    (paired baseline)') with both its comparisons, and each sensitivity arm ('<run>
    (sensitivity arm)': its metrics record, else the arm's own status and flags) with
    both its comparisons. summary.md's Checks section blocks findings on these runs and
    the attributed comparisons (summary.blocked_lines); the comparisons across two
    vehicles are listed here too when they are bug_suspect."""
    notes: dict[str, list[str]] = {
        OUTCOME_DID_NOT_FLY: [],
        OUTCOME_NOT_IN_ORBIT: [],
        OUTCOME_FLAGGED: [],
    }
    for name, m in run_data.as_mapping(metrics.get("cases")).items():
        if isinstance(m, Mapping):
            _status_notes(f"{name} (case)", m, notes)
    bounds = metrics.get("bounds")
    for b in bounds if isinstance(bounds, list) else []:
        b = run_data.as_mapping(b)
        run, paired = b.get("run"), b.get("paired_baseline")
        _status_notes(f"{run} (bound)", run_data.as_mapping(b.get("metrics")), notes)
        pm = run_data.as_mapping(b.get("paired_baseline_metrics"))
        if pm:
            _status_notes(f"{paired} (paired baseline)", pm, notes)
        _comparison_note(
            f"{run} (bound) against {paired}", b.get("comparison_vs_paired_baseline"), notes
        )
        _comparison_note(
            f"{run} (bound) against the baseline", b.get("comparison_vs_baseline"), notes
        )
    arms = metrics.get("sensitivity")
    for a in arms if isinstance(arms, list) else []:
        a = run_data.as_mapping(a)
        label = f"{a.get('run')} (sensitivity arm)"
        _status_notes(label, run_data.as_mapping(a.get("metrics")) or a, notes)
        _comparison_note(f"{label} against the baseline", a.get("comparison"), notes)
        _comparison_note(
            f"{label} against its same-perturbation baseline",
            a.get("comparison_vs_perturbed_baseline"),
            notes,
        )
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
        rows.append((OUTCOME_FLAGGED, f"pad control {mode}: {flags_text(len(p['flags']))}"))
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
            notes[OUTCOME_FLAGGED].append(f"offload case {name}: {flags_text(len(c['flags']))}")
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
            notes[OUTCOME_FLAGGED].append(f"{name}: {flags_text(len(m['flags']))}")
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
    apply (``_run_notes`` for ``runs``, ``_extra_notes`` for the calibration cases, the
    bounds and the sensitivity arms, ``_offload_notes``; the notes list every row), or
    OUTCOME_COMPLETE with a message that claims only what was checked: the baseline and
    the variant (the names in metrics.json's ``runs``) reached the target orbit, and no
    flag, failed verification or bug_suspect status in any run or comparison metrics.json
    records (a stage-1 pad control that ends no_offload is recorded short of orbit by
    design and is not claimed), with M5_NOT_MADE_TEXT when a comparison's M5 check reads
    n/a. Reads only metrics.json (and whether FAILED.txt and summary.md exist)."""
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
    extra = _extra_notes(metrics)
    offload = _offload_notes(metrics.get("offload") or {})
    for kind in OUTCOME_ORDER:
        rows[kind] = [*rows.get(kind, []), *extra.get(kind, []), *offload[kind]]
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
        f"complete: {names} reached the target orbit; {COMPLETE_CHECKS_TEXT}"
        + (M5_NOT_MADE_TEXT if m5_na else ""),
        notes,
    )


# ================================================================== the server (step A4b)

# ------------------------------------------------------------------ constants

BIND_HOST = "127.0.0.1"
"""The one address the app binds (D-SP2-29): a constant, never an option."""
HOST_NAMES = ("127.0.0.1", "localhost")
"""Host names the guard accepts beside the bound port: the printed one, and localhost
because a user may type it (it costs about 2 s per request here, survey 07 1.5)."""
DEFAULT_PORT = 8765
"""The default port of ``launchsim app`` (D-SP2-29; 0 picks a free one)."""
SERVE_POLL_S = 0.5
"""serve_forever's poll interval [s]: a Ctrl+C or a shutdown is noticed within it."""
MAX_JSON_BODY_BYTES = 65_536
"""The largest JSON request body [bytes] (64 KiB); a longer one is refused (413) before
any byte of it is read."""
HANDLER_TIMEOUT_S = 30.0
"""How long [s] a client has to send its whole request (line, headers and body): one
deadline from the request's start on its connection (``DeadlineReader``, armed per
request on a kept connection), so neither a client that sends nothing nor one that drips
a byte at a time holds a handler thread past it, and an idle kept connection ends after
it; also the socket timeout of writing the response."""
SCENE_LRU_SIZE = 8
"""Rendered scene pages kept, keyed by directory, run selection and metrics.json's
mtime (review 04 finding 3)."""
PANEL_LRU_SIZE = 8
"""Results-panel records kept, keyed by directory, the stat of its key files and the runs
the panel is built for."""
PANEL_RUNS = 2
"""The most runs the app page shows side by side (its two scene panels), and so the most a
results panel is built for (GET /api/panel/<experiment>/<timestamp>/<runs>)."""
MAX_METRICS_BYTES = 16 * 1024 * 1024
"""A metrics.json above this size [bytes] (16 MiB) is unreadable: never parsed."""
MAX_CONFIG_BYTES = 1024 * 1024
"""A resolved_config.yaml above this size [bytes] (1 MiB) is unreadable: never parsed.
The largest one written so far is about 136 kB (results/silo_offload_2d/20261003T112934Z),
and PyYAML's pure-Python parser takes about 4 s per MB, so one parse at the cap costs
about 4 s (a row, a panel and a scene build each parse it once)."""
SP1_DIFF_MAX_LINES = 50
"""The most setting lines ``sp1_differences`` lists (then one 'and N more' line)."""
LEAF_BUDGET = 10_000
"""The most leaves ``_leaves`` collects from one run dict (a committed run dict has about
a hundred); past it the run is reported as not compared."""
YAML_ALIAS_REFUSED = "uses YAML anchors or aliases (results_io never writes them)"
"""What an UnreadableError says of a results YAML file with an anchor or an alias (one
alias can stand for an exponential amount of data, so such a file is never read)."""
BOOT_ID_BYTES = 8
"""Random bytes of the boot id (16 hex characters): a page tells a restarted server by
it."""
MAX_CSV_BYTES = 64 * 1024 * 1024
"""A run's timeseries.csv or events.csv above this size [bytes] (64 MiB): the run is
left out of the run list (never read)."""
ROWS_PROBE_BYTES = 8192
"""How much of a timeseries.csv [bytes] is read to tell whether it holds a row."""
SIZE_WALK_MAX_ENTRIES = 20_000
"""The most directory entries a size count visits (the size is then a lower bound)."""
SHUTDOWN_TIMEOUT_S = 5.0
"""How long [s] the server's exit waits for serve_forever to return."""
WORKER_JOIN_TIMEOUT_S = 2.0
"""How long [s] the server's exit waits for the launch worker (a daemon thread that a
stopped process abandons)."""
STOP_WRITING_GRACE_S = 10.0
"""How long [s] a stop waits for a launch in its writing stage to finish (writing took
2.6-5.5 s in survey 07) before it marks the directory FAILED."""
STOP_ABORT_STAGES = (STAGE_COMPARISON, STAGE_WRITING)
"""The stages at whose report a stopped launch's worker is interrupted
(``AppServer._progress``): before the comparison's offload pass and before write_run,
so nothing is written into a directory the stop has marked FAILED."""
TIMESTAMP_PATTERN = re.compile(r"[0-9]{8}T[0-9]{6}Z(-[0-9]{1,4})?")
"""A results directory's timestamp (``fullmatch``): results_io.TIMESTAMP_FORMAT with
make_run_dir's collision suffix (-2 to -1000), ASCII digits only (``\\d`` would accept
fullwidth and other Unicode digits, a name the path guard then refuses)."""
LISTING_SETTLE_NS = 2_000_000_000
"""A folder whose mtime is newer than this [ns] when it is listed is listed again next
time: a second change within the file system's clock tick would leave its mtime
unchanged."""
PORT_UNAVAILABLE_ERRNOS = frozenset({errno.EADDRINUSE, errno.EACCES})
WINDOWS_PORT_UNAVAILABLE = frozenset({10048, 10013})
"""Bind errors that mean the port is taken or reserved: errno values, and on Windows the
WinError codes 10048 (in use) and 10013 (held exclusively or reserved by the system)."""
PROBE_ADDRESSES: tuple[tuple[socket.AddressFamily, str], ...] = (
    (socket.AF_INET, "0.0.0.0"),
    (socket.AF_INET6, "::1"),
)
"""Where a fixed port is probed before the bind (``probe_port``): the IPv4 wildcard (on
Windows a socket there does not stop a bind of 127.0.0.1 on the same port) and the IPv6
loopback (where a browser sends http://localhost:<port>/ first)."""
CONTENT_LENGTH_PATTERN = re.compile(r"^[0-9]{1,12}$")
"""A Content-Length value: ASCII digits only (str.isdigit accepts other digits)."""
JSON_MEDIA_TYPE = "application/json"
JSON_CHARSET_PARAM = "charset=utf-8"
"""A launch request's media type, with no parameter or this one only."""
JSON_CONTENT_TYPE = "application/json; charset=utf-8"
HTML_CONTENT_TYPE = "text/html; charset=utf-8"
"""Content types of the responses (every text response names its charset)."""
PNG_MEDIA_TYPE = "image/png"
"""The one media type of a video frame body (exact, no parameter; step A6v)."""
VIDEO_RUNS = PANEL_RUNS
"""The most runs one video shows: the app page's two panels."""
VIDEO_REQUEST_KEYS: frozenset[str] = frozenset(
    {"experiment", "timestamp", "runs", "fps", "width", "frames", "seconds", "times"}
)
"""The keys POST /api/videos accepts (D-SP2-31: whitelisted keys)."""
VIDEO_UNAVAILABLE_CODE = "video_unavailable"
"""The 503 of a video request when ffmpeg was not found or the folder refuses videos."""
SERVER_VERSION = "launchsim"
"""The Server header: the name only, no Python version."""
FIXED_HEADERS: tuple[tuple[str, str], ...] = (
    ("X-Content-Type-Options", "nosniff"),
    ("Cache-Control", "no-store"),
    ("Referrer-Policy", "no-referrer"),
    ("Cross-Origin-Resource-Policy", "same-origin"),
    ("Cross-Origin-Opener-Policy", "same-origin"),
)
"""Headers of every response, the standard library's own errors included."""
FRAME_DENY = "DENY"
FRAME_SAMEORIGIN = "SAMEORIGIN"
API_CSP = "default-src 'none'; frame-ancestors 'none'"
"""Frame policy and Content-Security-Policy of every response but the two pages."""
APP_CSP_TEMPLATE = (
    "default-src 'none'; script-src '{script}'; style-src 'unsafe-inline'; "
    "img-src 'self' data:; connect-src 'self'; frame-src 'self'; base-uri 'none'; "
    "form-action 'none'; frame-ancestors 'none'"
)
"""The app page's policy ({script}: the sha256 source of its one inline script)."""
SCENE_FRAME_ANCESTORS = "frame-ancestors 'self'"
"""What a served scene page's header policy adds to the page's own meta policy: the app
page (same origin) may frame it (D-SP2-22)."""
CSP_META_PATTERN = re.compile(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)">')
INLINE_SCRIPT_PATTERN = re.compile(r"<script>(.*?)</script>", re.S)
APP_TEMPLATE = ("templates", "app.html")
"""The app page template (package data)."""
APP_DATA_TOKEN = "__APP_DATA__"
"""The one token of the app page's initial JSON block."""
INTERNAL_ERROR_MESSAGE = "the server failed on this request; nothing was started by it"
"""The fixed message of a 500 (no traceback, no exception text)."""
LAUNCH_NOTE = (
    "A launch cannot be cancelled: Ctrl+C (or Ctrl+Break) on the server's console stops "
    "the server and marks a running launch FAILED."
)
"""What the form says beside the Launch button (D-SP2-09)."""

JOB_IDLE = "idle"
JOB_RUNNING = "running"
JOB_DONE = "done"
JOB_FAILED = "failed"
"""Job states: no launch yet; running; ended with a written directory; refused in the
worker, crashed or stopped."""
FAILED_OUTCOMES = (OUTCOME_CRASHED, OUTCOME_REFUSED, OUTCOME_INCOMPLETE)
"""Outcome kinds that put a job in JOB_FAILED."""

DIR_RUNNING = "running"
DIR_COMPLETE = "complete"
DIR_FAILED = "failed"
DIR_INCOMPLETE = "incomplete"
DIR_UNREADABLE = "unreadable"
"""Run-browser states (design 4.6; review 04 finding 9)."""
REASON_RUNNING = "running"
REASON_1D = "1-D"
REASON_SWEEP = "sweep"
REASON_FAILED = "failed"
REASON_INCOMPLETE = "incomplete"
REASON_UNREADABLE = "unreadable"
REASON_NO_PLANAR_RUNS = "no run holds a time series (none flew)"
REASON_NO_RUN_FOLDERS = "no run folder with a readable time series"
REASON_NOT_PLANAR = "not planar"
"""Why a listed directory cannot be played: a fixed set (a directory's own text, its
model included, never becomes a reason)."""
REASONS = (
    REASON_RUNNING,
    REASON_1D,
    REASON_SWEEP,
    REASON_FAILED,
    REASON_INCOMPLETE,
    REASON_UNREADABLE,
    REASON_NO_PLANAR_RUNS,
    REASON_NO_RUN_FOLDERS,
    REASON_NOT_PLANAR,
)
"""Every reason a row can carry (None when it can be played)."""
FINAL_STATES = (DIR_COMPLETE, DIR_FAILED)
"""Row states that never change once a directory reaches them (summary.md or FAILED.txt
is written last; the server marks only its own running directory, which it never caches):
a cached row in one of them is reused without re-reading the directory."""
GROUP_APP = "app"
GROUP_RECORDED = "recorded"
GROUP_TITLES = {
    GROUP_APP: "App runs (exploratory)",
    GROUP_RECORDED: "Recorded experiments",
}
"""The run browser's two groups: the app root (results/app) and everything else."""
SWEEP_BASELINE_DIR = "baseline"
SWEEP_DIR_PREFIX = "sweep_"
"""A sweep directory: summary.md over a baseline/ folder and sweep_<n>/ folders."""
INCOMPLETE_LINE = (
    "no summary.md and no FAILED.txt: the run was stopped before its results were "
    "written, or another process is still writing it"
)
TAG_EXPLORATORY_TEXT = "Exploratory app run: not a finding"
"""The results panel's tag of an app run (design 4.7)."""

HEADLINE_PAYLOAD = "payload_capacity"
HEADLINE_SOLVED = "offload_solved"
HEADLINE_IMPOSED = "offload_imposed"
HEADLINE_NOTHING = "offload_found_nothing"
HEADLINE_DID_NOT_FLY = "did_not_fly"
HEADLINE_NOT_IN_ORBIT = "not_in_orbit"
HEADLINE_PAIRED_PAD = "paired_pad"
HEADLINE_PAD_CONTROL = "pad_control"
HEADLINE_FLAGGED = "flagged"
"""Kinds of a run's headline in the results panel (one per launch kind, design 4.7;
HEADLINE_FLAGGED: a run whose own checks failed, status bug_suspect)."""
FINDINGS_BLOCKED_TEXT = "findings blocked until investigated (summary.md, Checks)"
"""What a headline adds for a run or a comparison that is bug_suspect."""
YARDSTICK_TEXT = "a yardstick (instant full thrust), not a design"
"""What a payload headline adds for an instant-startup run (silo_instant, pad_instant)."""
IMPOSED_VERIFICATION_TEXT = (
    "not applicable: an imposed offload flies its own payload capacity (P* - P_ref); only "
    "a solved x* is verified"
)
"""The verification text of an imposed (fixed) offload case."""
PRE_OFFLOAD_READING = "a property of the vehicle model, not netted"
"""How a stage-2 pre-offload reads beside an imposed stage-1 offload's headline (the
form's words: imposed on stage 2 first, not netted)."""
PUSH_METRICS: tuple[tuple[str, str], ...] = (
    ("exit_speed_mps", "exit_speed_mps"),
    ("net_accel_g", "net_accel_g"),
    ("stroke_m", "stroke_m"),
    ("push_time_s", "push_time_s"),
    ("felt_g_peak", "felt_g_track_peak"),
    ("interface_force_peak_N", "peak_interface_force_N"),
    ("electrical_energy_J", "electrical_energy_J"),
    ("electrical_energy_kWh", "electrical_energy_kWh"),
    ("drive_energy_J", "drive_energy_J"),
    ("peak_drive_power_W", "peak_drive_power_W"),
    ("braking_distance_m", "braking_distance_m"),
    ("facility_length_m", "facility_length_m"),
    ("carriage_mass_kg", "carriage_mass_kg"),
)
"""(panel key, metrics.json key) of a pushed run's push block."""
FLIGHT_METRICS: tuple[tuple[str, str], ...] = (
    ("liftoff_mass_kg", "liftoff_mass_kg"),
    ("meco_after_release_s", "stage1_burnout_t_s"),
    ("max_q_pa", "max_q_pa"),
    ("max_q_time_s", "max_q_time_s"),
    ("peak_felt_axial_g_flight", "peak_felt_axial_g_flight"),
    ("peak_q_alpha", "peak_q_alpha"),
    ("payload_kg", "payload_kg"),
)
"""(panel key, metrics.json key) of a run's flight block (stage1_burnout_t_s is MECO
after release, as summary.md labels it)."""


# ------------------------------------------------------------------ SP1's headline


@dataclass(frozen=True)
class HeadlineCaveat:
    """One caveat group beside SP1's headline: the note's own bold ``title``, a short
    ``text``, the ``numbers`` it quotes and the ``phrases`` it must keep from the note
    (each found verbatim in the note and in the text by a test)."""

    title: str
    text: str
    numbers: tuple[str, ...]
    phrases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Headline:
    """SP1's headline as docs/findings/RQ1-fuel-offload-2d.md states it (D-SP2-36):
    its ``source`` note and ``status``, the results ``directory`` and ``commit``, the
    ``case`` and its x* (``offload_kg``, the note's validation measurement), the
    ``text``, the ``numbers`` the text quotes and the six caveat groups."""

    source: str
    status: str
    directory: str
    commit: str
    case: str
    offload_kg: float
    text: str
    numbers: tuple[str, ...]
    caveats: tuple[HeadlineCaveat, ...]

    def record(self) -> dict[str, Any]:
        """The headline as plain data (for GET /api/form)."""
        return dataclasses.asdict(self)


SP1_HEADLINE = Headline(
    source="docs/findings/RQ1-fuel-offload-2d.md",
    status="preliminary, 2026-10-03",
    directory="results/silo_offload_2d/20261003T112934Z",
    commit="b3150c1754ee",
    case="silo_cold_s1",
    offload_kg=41_262.908,
    text=(
        "At the pad's payload and orbit, the 3 g0, 100 m cold-start silo (exit 76.7 m/s, "
        "stage 1 lit 0.5 s after release with a 2 s ramp) lets the gate vehicle leave out "
        "41.26 t of stage-1 propellant: 10.04% of the 410.9 t stage-1 load and 7.96% of the "
        "518.4 t total (silo_cold_s1, sweep-optimized). That is 2.76 times the "
        "ideal-screening estimate at the same release speed (14.98 t). It charges no "
        "structural mass for the 4 g0 push: an assumed +2, +4 and +8.1 t of stage-1 dry "
        "mass leave 32.29, 22.88 and 1.98 t, and about 8.5 t (extrapolated) leaves nothing. "
        "Under +/-10% of stage-1 dry mass, Isp, C_D and drive efficiency the offload stays "
        "between 38.67 and 44.46 t."
    ),
    numbers=(
        "76.7 m/s",
        "41.26 t",
        "10.04%",
        "410.9 t",
        "7.96%",
        "518.4 t",
        "2.76 times",
        "14.98 t",
        "+2, +4 and +8.1 t",
        "32.29, 22.88 and 1.98 t",
        "8.5 t",
        "38.67",
        "44.46 t",
    ),
    caveats=(
        HeadlineCaveat(
            "The calibration miss and the bridge.",
            "The gate vehicle carries 26,054.4 kg to the reference orbit, +14.3% against the "
            "published 22,800 kg, outside the +/-10% band. On the README-loads fork (+8.3%, "
            "inside the band) the same case removes 36.01 t, 9.10% of its 395.7 t stage-1 "
            "load. The fraction of stage 1 is 9.4% lower in relative terms on that fork, "
            "inside the pre-registered agreement band of about 10%, near its edge. Read the "
            "headline as 9 to 10% of stage 1 across the two forks, not as a Falcon 9 figure.",
            (
                "26,054.4 kg",
                "+14.3%",
                "22,800 kg",
                "+8.3%",
                "36.01 t",
                "9.10%",
                "395.7 t",
                "9.4%",
            ),
        ),
        HeadlineCaveat(
            "Structure.",
            "The penalty rows are the only stand-in for the structure a 4 g0 full-stack push "
            "needs, and the needed mass is unknown: no structural model exists. They are "
            "assumptions, not a sized structure.",
            ("4 g0",),
        ),
        HeadlineCaveat(
            "Part of it is the lighter stack, not the push.",
            "Flown without the push, the same 41.26 t offload leaves the pad 1,402.0 kg "
            "short of P_ref, so the push is needed to carry it; but 63 to 67 m/s (28 to 29%) "
            "of the 228.2 m/s of ideal delta-v the offload removes is the lighter stack's "
            "own thrust-to-weight gain, which the push makes usable but does not produce. "
            "The release speed and the head start's trajectory effects carry 64 to 66%. Read "
            "as the pre-registration worded it, the paired pad's 1,402.0 kg shortfall is "
            "small against the 41.26 t offload (3.4%), so the pre-registered reading says "
            "most of the offload is the lighter stack's thrust-to-weight; the delta-v split "
            "is a reading chosen after the run.",
            ("1,402.0 kg", "63 to 67 m/s", "28 to 29%", "228.2 m/s", "64 to 66%", "3.4%"),
        ),
        HeadlineCaveat(
            "Part of it is a baseline convention.",
            "14.4 m/s of the 228.2 m/s (6.3% of the decomposition; 15.6 m/s, 6.8%, on the "
            "paired-pad order of the split) is the pad's 2.7 t burned on the hold-down, "
            "which a silo lit after release does not pay.",
            ("14.4 m/s", "6.3%", "15.6 m/s", "6.8%", "2.7 t"),
        ),
        HeadlineCaveat(
            "Loads beside it.",
            "The offloaded run flies a max-Q 3.35% above the pad's (38,438.5 against "
            "37,191.4 Pa), where the full-load silo flew 16.0% below it; its q-alpha is 3.04 "
            "times the pad's (226.9 against 74.7 Pa rad); the stack feels 4.0 g0 on the "
            "track (20.81 MN at the interface).",
            (
                "3.35%",
                "38,438.5",
                "37,191.4",
                "16.0%",
                "3.04 times",
                "226.9",
                "74.7",
                "4.0 g0",
                "20.81 MN",
            ),
        ),
        HeadlineCaveat(
            "Sweep-optimized, unthrottled, free kick, prescribed drive, partly filled tanks.",
            "Guidance is sweep-optimized, not optimal control, and the engines never "
            "throttle, so max-Q and q-alpha are upper bounds and no max-Q limit constrains "
            "the offloaded runs; the kick has no angle-of-attack aerodynamics; the drive is "
            "a prescribed constant acceleration with no force or power limit, a massless "
            "carriage and a vented shaft with no air drag; under this drive a hot start "
            "cannot add exit speed, and drive efficiency moves only the electricity; the "
            "offloaded tanks are partly filled, every dry mass kept: an under-filled "
            "vehicle, not one redesigned around the smaller load. No ullage, "
            "centre-of-gravity or residual effect is modelled.",
            (),
            (
                "drive efficiency moves only the electricity",
                "No ullage, centre-of-gravity or residual effect is modelled",
            ),
        ),
    ),
)
"""SP1's headline and its six caveat groups, from docs/findings/RQ1-fuel-offload-2d.md
('Headline' and 'Caveats that sit beside this number'); shown only with its caveats
(D-SP2-36). tests/test_app_server.py finds the headline text verbatim in the note (only
the groups paraphrase), each group's title and numbers in it, and ``offload_kg`` as the
note's '41,262.908 kg'."""
REPRODUCTION_TOL_KG = 0.002
"""How far a directory's x* of SP1's case may be from SP1_HEADLINE.offload_kg [kg] and
still be shown with SP1's headline (design section 6, exit criterion 3: 'within 0.002
kg')."""
COMMIT_PATTERN = re.compile(r"[0-9a-f]{7,64}")
"""A commit hash a directory records that the server passes to git (hex only: never a
text git could read as an option)."""


# ------------------------------------------------------------------ errors and JSON


class Refused(Exception):
    """A request the server refuses: the HTTP ``status``, a short ``code``, a one-line
    ``message`` (never the request's own text) and ``extra`` fields of the JSON body."""

    def __init__(self, status: HTTPStatus, code: str, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.extra = extra

    def body(self) -> dict[str, Any]:
        """The JSON body: {"error": code, "message": message, **extra}."""
        return {"error": self.code, "message": self.message, **self.extra}


class LaunchInterrupted(BaseException):
    """The reason FAILED.txt gives for a launch the server stopped (Ctrl+C or
    Ctrl+Break on its console), and what the server's progress callback raises in the
    stopped launch's worker at its next comparison or writing stage
    (``AppServer._progress``). A BaseException, so the progress wrapper of run_launch
    (which swallows Exception only: a broken display never stops a run) lets it through
    to run_launch's handler, which writes FAILED.txt and returns before write_run."""


class UnreadableError(run_data.RunDataError):
    """A results file the server will not read (a link, over its size cap) or cannot
    parse."""


def plain(obj: Any) -> Any:
    """``obj`` as strict-JSON-ready plain data: mappings with string keys, lists, finite
    floats (a NaN or an infinity becomes None), ints, strings, booleans and None; a Path
    becomes its POSIX text and anything else its str."""
    if obj is None or isinstance(obj, bool | int | str):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, Mapping):
        return {str(k): plain(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [plain(v) for v in obj]
    if isinstance(obj, Path):
        return obj.as_posix()
    return str(obj)


def json_bytes(obj: Any) -> bytes:
    """``plain(obj)`` as compact strict JSON, ASCII, with '<', '>' and '&' escaped as
    \\u003c, \\u003e and \\u0026 (inside JSON strings only, so equivalent JSON): no
    response body can be read as HTML."""
    text = json.dumps(plain(obj), allow_nan=False, ensure_ascii=True, separators=(",", ":"))
    for char, escaped in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026")):
        text = text.replace(char, escaped)
    return text.encode("ascii")


def _refuse_constant(name: str) -> Any:
    """json.loads' parse_constant: NaN, Infinity and -Infinity are not JSON."""
    raise ValueError(f"{name} is not a JSON number")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """json.loads' object_pairs_hook: an object with a repeated key is refused."""
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("a key is repeated")
        out[key] = value
    return out


def strict_json_object(data: bytes) -> dict[str, Any]:
    """The JSON object in a request body: UTF-8 (strict), no NaN or Infinity, no repeated
    key, nesting within Python's limit (a RecursionError is refused), an object at the
    top level. Raises Refused (400) with a fixed message otherwise."""
    try:
        obj = json.loads(
            data.decode("utf-8"),
            parse_constant=_refuse_constant,
            object_pairs_hook=_unique_pairs,
        )
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise Refused(
            HTTPStatus.BAD_REQUEST, "bad_json", "the request body is not strict JSON"
        ) from exc
    if not isinstance(obj, dict):
        raise Refused(HTTPStatus.BAD_REQUEST, "bad_json", "the request body must be a JSON object")
    return obj


def json_type_ok(value: str) -> bool:
    """True for a Content-Type of JSON_MEDIA_TYPE with no parameter or JSON_CHARSET_PARAM
    only (case-insensitive)."""
    media, _, params = value.partition(";")
    if media.strip().lower() != JSON_MEDIA_TYPE:
        return False
    params = params.strip().lower().replace(" ", "")
    return params in ("", JSON_CHARSET_PARAM)


# ------------------------------------------------------------------ the guard


def allowed_hosts(port: int) -> frozenset[str]:
    """The Host values the server answers: HOST_NAMES with the bound port."""
    return frozenset(f"{name}:{port}" for name in HOST_NAMES)


def allowed_origins(port: int) -> frozenset[str]:
    """The Origin values the server accepts: http:// and an allowed host ('null' is
    not one)."""
    return frozenset(f"http://{host}" for host in allowed_hosts(port))


def split_target(target: str) -> list[str]:
    """The path segments of a request target that starts with '/': split on '/' BEFORE
    any decoding, then each segment decoded once with urllib.parse.unquote (never
    unquote_plus: a '+' stays '+', '%2B' gives '+'). Raises Refused (400) for a decoded
    segment holding '/', '\\\\', '%', a control character or a non-ASCII character (an
    invalid UTF-8 escape decodes to U+FFFD, which is not ASCII). '/' gives ['']."""
    out: list[str] = []
    for raw in target.split("/")[1:]:
        seg = urllib.parse.unquote(raw)
        if (
            not seg.isascii()
            or any(c in seg for c in "/\\%")
            or any(ord(c) < 0x20 or ord(c) == 0x7F for c in seg)
        ):
            raise Refused(
                HTTPStatus.BAD_REQUEST, "bad_path", "a path segment holds a character not allowed"
            )
        out.append(seg)
    return out


def guard(method: str, target: str, headers: Any, port: int) -> list[str]:
    """The checks every request passes before any body byte is read or any route runs
    (design 4.6, D-SP2-32, review 04): exactly one Host, equal (case-insensitive) to an
    allowed host with the bound ``port`` (403); Origin absent or exactly one allowed
    origin, 'null' refused (403); the target in origin form, starting with '/' (an
    absolute-form or asterisk target: 400); Sec-Fetch-Site, when present, exactly one
    and same-origin or none, except on GET / (a link from elsewhere opens the app; 403);
    no query string or fragment on any route (400); the path segments (``split_target``,
    400). ``headers``: the request's email.message.Message. Returns the segments.

    GET / is the one route another site can reach, so that a link opens the app. Exit
    criterion 17 (another origin cannot start a launch or make the server build a scene)
    therefore holds only while the page, when another site opened it, issues nothing but
    GET requests to /api/form, /api/job and /api/results until the user acts on the page
    itself: GET / tells it so (``from_other_site``: Sec-Fetch-Site same-site or
    cross-site), and the page then reads no hash, sends no dry run and requests no
    /scene/... until a trusted pointer, key or input event of its own; a launch always
    follows a click on Launch (templates/app.html, step A5). The page never reads
    location.search, document.referrer or window.name, and takes from a postMessage only
    a height from its own scene frame."""
    hosts = headers.get_all("Host") or []
    if len(hosts) != 1 or hosts[0].strip().lower() not in allowed_hosts(port):
        raise Refused(
            HTTPStatus.FORBIDDEN, "host_not_allowed", "the Host is not this server's address"
        )
    origins = headers.get_all("Origin") or []
    if len(origins) > 1 or (origins and origins[0].strip().lower() not in allowed_origins(port)):
        raise Refused(
            HTTPStatus.FORBIDDEN, "origin_not_allowed", "a request from another origin is refused"
        )
    if not target.startswith("/"):
        raise Refused(
            HTTPStatus.BAD_REQUEST, "bad_target", "the request target must be a path from /"
        )
    sites = headers.get_all("Sec-Fetch-Site") or []
    if sites and not (method == "GET" and target == "/"):
        if len(sites) != 1 or sites[0].strip().lower() not in ("same-origin", "none"):
            raise Refused(HTTPStatus.FORBIDDEN, "cross_site", "a cross-site request is refused")
    if "?" in target or "#" in target:
        raise Refused(HTTPStatus.BAD_REQUEST, "query_not_allowed", "no query string is accepted")
    return split_target(target)


OWN_SITE_VALUES = ("same-origin", "none")
"""Sec-Fetch-Site values of a request the app's own page or the user made (the guard's
set): a typed or bookmarked address, a reload, the browser opened by ``--open``, headless
QA. Any other value, or more than one, is another site's (same-site: another port on this
loopback address)."""


def from_other_site(headers: Any) -> bool:
    """Whether a request (GET /) may have come from a page of another site (step A5;
    exit criterion 17): anything but exactly one Sec-Fetch-Site of OWN_SITE_VALUES. Fail
    safe: a request without Sec-Fetch-Site (a browser without Fetch Metadata, or a client
    that is no browser) counts as another site's, so such a page restores no view from its
    address and asks for nothing until the user uses it (the guard's rule on the other
    routes, which accepts a missing header, is unchanged: this only makes the page wait).
    ``headers``: the request's email.message.Message."""
    sites = headers.get_all("Sec-Fetch-Site") or []
    return len(sites) != 1 or sites[0].strip().lower() not in OWN_SITE_VALUES


# ------------------------------------------------------------------ files and directories


def is_link(path: Path) -> bool:
    """True for a symbolic link or a junction (never followed by the server)."""
    try:
        return path.is_symlink() or path.is_junction()
    except OSError:
        return True


def valid_experiment_name(name: str) -> bool:
    """True for a name results_io.check_name accepts (one safe path component) that the
    path guard can carry back (ASCII and printable: check_name's pattern ends in '$', which
    also matches before a final newline)."""
    if not (name.isascii() and name.isprintable()):
        return False
    try:
        results_io.check_name(name, "experiment name")
    except results_io.InvalidNameError:
        return False
    return True


def _stat(path: Path) -> tuple[int, int] | None:
    """(size, mtime_ns) of a path, or None when it cannot be read."""
    try:
        st = path.stat()
    except OSError:
        return None
    return st.st_size, st.st_mtime_ns


def _dir_stamp(path: Path) -> tuple[int, int] | None:
    """(size, mtime_ns) of a directory in one stat call, or None when it is missing, not a
    directory or cannot be read."""
    try:
        st = path.stat()
    except OSError:
        return None
    return (st.st_size, st.st_mtime_ns) if stat.S_ISDIR(st.st_mode) else None


PARSE_FAILED_TEXT = {
    "JSON": "cannot be parsed (cut short, not JSON or a number too large)",
    "YAML": "cannot be parsed (cut short, not YAML or a number too large)",
}
"""What an UnreadableError says of a file run_data could not parse (fixed text: the
reader's own message names the absolute path, which no response carries)."""


def _check_capped(path: Path, cap: int) -> None:
    """UnreadableError (the file's name only) for a link, something not a file, or a file
    over ``cap`` bytes."""
    if is_link(path) or not path.is_file():
        raise UnreadableError(f"{path.name} is a link or not a file")
    if path.stat().st_size > cap:
        raise UnreadableError(f"{path.name} is over its size cap ({cap:,} bytes)")


class _AliasFound(yaml.YAMLError):
    """An anchor or an alias met by ``NoAliasLoader``."""


class NoAliasLoader(yaml.SafeLoader):
    """yaml.SafeLoader that refuses every anchor and alias as it composes (``_AliasFound``)
    before any node is built from it: an alias makes no copy when loaded, but every walk
    of the result (a leaf list, a JSON dump) expands it, and nested aliases grow tenfold
    per level for a few hundred bytes each."""

    def compose_node(self, parent: Any, index: Any) -> Any:
        """Refuse an alias or an anchored node, else compose as SafeLoader does."""
        event = self.peek_event()
        if isinstance(event, yaml.AliasEvent) or getattr(event, "anchor", None) is not None:
            raise _AliasFound("an anchor or an alias")
        return super().compose_node(parent, index)


def read_yaml_no_alias(path: Path) -> dict[str, Any]:
    """The YAML mapping in ``path`` as yaml.safe_load gives it ({} when its top level is
    not a mapping), read as UTF-8 with ``NoAliasLoader``. Raises what the reading and
    parsing raise (OSError, UnicodeDecodeError, yaml.YAMLError; ``_AliasFound`` for an
    anchor or an alias)."""
    with path.open(encoding="utf-8") as fh:
        loader = NoAliasLoader(fh)
        try:
            data = loader.get_single_data()
        finally:
            loader.dispose()
    return data if isinstance(data, dict) else {}


def _read_capped(path: Path, cap: int, kind: str) -> dict[str, Any]:
    """read_capped_json and read_capped_yaml: ``kind`` 'JSON' or 'YAML'. Every message
    names the file by its name only (never run_data's text with the local path)."""
    if not path.exists():
        return {}
    _check_capped(path, cap)
    try:
        if kind == "JSON":
            return run_data.read_json(path, error=UnreadableError)
        return read_yaml_no_alias(path)
    except RecursionError as exc:
        raise UnreadableError(f"{path.name} is nested too deeply") from exc
    except _AliasFound as exc:
        raise UnreadableError(f"{path.name} {YAML_ALIAS_REFUSED}") from exc
    except UnreadableError as exc:  # read_json's, with the local path: replaced
        if isinstance(exc.__cause__, OSError):
            raise UnreadableError(f"{path.name} cannot be read") from exc
        raise UnreadableError(f"{path.name} {PARSE_FAILED_TEXT[kind]}") from exc
    except OSError as exc:
        raise UnreadableError(f"{path.name} cannot be read") from exc
    except (ValueError, yaml.YAMLError) as exc:  # UnicodeDecodeError is a ValueError
        raise UnreadableError(f"{path.name} {PARSE_FAILED_TEXT[kind]}") from exc


def read_capped_json(path: Path, cap: int) -> dict[str, Any]:
    """The JSON mapping in ``path`` ({} when missing): UnreadableError, with fixed text
    naming the file only, for a link, a file over ``cap`` bytes, or one that cannot be
    read or parsed (a truncated file, a number too large, nesting too deep)."""
    return _read_capped(path, cap, "JSON")


def read_capped_yaml(path: Path, cap: int) -> dict[str, Any]:
    """The YAML mapping in ``path`` ({} when missing), under the rules of
    ``read_capped_json``; a file with a YAML anchor or alias is unreadable too
    (``read_yaml_no_alias``: YAML_ALIAS_REFUSED)."""
    return _read_capped(path, cap, "YAML")


def has_rows(series: Path) -> bool:
    """True when a timeseries.csv holds a header and at least one row (its first
    ROWS_PROBE_BYTES only are read; a failed search writes no row)."""
    with io.FileIO(series, "r") as fh:
        head = fh.read(ROWS_PROBE_BYTES) or b""
    lines = [line for line in head.split(b"\n") if line.strip()]
    return len(lines) >= 2


def run_folders(run_dir: Path, metrics: Mapping[str, Any]) -> dict[str, bool]:
    """The run list of a results directory: each run folder (not a link) holding a
    timeseries.csv (not a link) with both CSVs within MAX_CSV_BYTES, mapped to whether
    its series holds a row (``has_rows``); metrics.json's run order first, the other
    folders sorted after it (run_data.run_names' order)."""
    have: dict[str, bool] = {}
    for folder in run_dir.iterdir():
        series = folder / run_data.SERIES_FILE
        events = folder / run_data.EVENTS_FILE
        if is_link(folder) or not folder.is_dir() or not series.is_file() or is_link(series):
            continue
        if series.stat().st_size > MAX_CSV_BYTES:
            continue
        if events.exists() and (is_link(events) or events.stat().st_size > MAX_CSV_BYTES):
            continue
        have[folder.name] = has_rows(series)
    order = list(run_data.as_mapping(metrics.get("runs")))
    known = set(order)  # one lookup per folder, not a scan of the run list
    names = [n for n in order if n in have] + sorted(n for n in have if n not in known)
    return {n: have[n] for n in names}


def tree_size(path: Path) -> tuple[int, bool]:
    """(total bytes of the files under ``path``, links not followed, whether the count
    stopped at SIZE_WALK_MAX_ENTRIES entries and is a lower bound)."""
    total, seen = 0, 0
    stack = [path]
    while stack:
        folder = stack.pop()
        try:
            with os.scandir(folder) as it:
                entries = list(it)
        except OSError:
            continue
        for entry in entries:
            seen += 1
            if seen > SIZE_WALK_MAX_ENTRIES:
                return total, True
            try:
                if entry.is_symlink() or entry.is_junction():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    stack.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
            except OSError:
                continue
    return total, False


def directory_signature(run_dir: Path) -> tuple[Any, ...]:
    """What a cached row or panel of a directory depends on: the stat of the directory,
    metrics.json, resolved_config.yaml, summary.md and FAILED.txt."""
    return (
        _stat(run_dir),
        _stat(run_dir / run_data.METRICS_FILE),
        _stat(run_dir / run_data.CONFIG_FILE),
        _stat(run_dir / SUMMARY_FILE),
        _stat(run_dir / results_io.FAILED_MARKER),
    )


def stamp_key(timestamp: str) -> tuple[str, int]:
    """Sort key of a timestamp, its collision suffix as a number (-10 after -9)."""
    stamp, _, suffix = timestamp.partition("-")
    return stamp, int(suffix) if suffix else 1


GIT_HASH_UNKNOWN = "unknown"
"""The hash shown for a git record without one (scene.git_record's marker)."""
GIT_DIFF_SAME = 0
GIT_DIFF_DIFFERENT = 1
"""``git diff --quiet``'s exit codes for no difference and a difference (any other: git
could not compare)."""


def tree_state(dirty: Any, hash_: Any) -> str:
    """'clean', 'dirty' or 'unknown' for a git record's dirty flag and hash: a hash that
    is missing, not a non-empty string, a no-git hash or GIT_HASH_UNKNOWN, or a flag that
    is not a boolean, is unknown, never clean."""
    if (
        not isinstance(hash_, str)
        or not hash_
        or hash_ in (*summary.EXPLORATORY_NO_GIT_HASHES, GIT_HASH_UNKNOWN)
        or not isinstance(dirty, bool)
    ):
        return "unknown"
    return "dirty" if dirty else "clean"


def git_view(git: Any) -> dict[str, Any]:
    """{hash, state} of a git record as metrics.json holds it: the recorded hash
    (GIT_HASH_UNKNOWN when it is absent or not a non-empty string) and ``tree_state`` of
    the recorded flag and hash (scene.git_record's dirty: None unless a boolean)."""
    raw = run_data.as_mapping(git)
    record = scene.git_record(raw)
    hash_ = raw.get("hash")
    shown = hash_ if isinstance(hash_, str) and hash_ else GIT_HASH_UNKNOWN
    return {"hash": shown, "state": tree_state(record["dirty"], hash_)}


# ------------------------------------------------------------------ the results panel


def _t(kg: float) -> str:
    """'41.26 t' of a mass [kg]."""
    return f"{float(kg_to_t(kg)):.2f} t"


def _pct(fraction: float | None) -> str:
    """'10.04%' of a fraction, or 'an unknown share'."""
    if fraction is None:
        return "an unknown share"
    return f"{float(to_percent(fraction)):.2f}%"


def _case_control(offload: Mapping[str, Any], mode: Any) -> dict[str, Any] | None:
    """The pad control a solved case is quoted net of (a stage-2 or both-stage solve), or
    None for a gross figure (a stage-1 solve)."""
    if mode is None or mode in OFFLOAD_GROSS_MODES:
        return None
    return replay.pad_control_record(offload, mode)


def _gross_solve_text(record: Mapping[str, Any], ref: str, removed: float | None) -> str:
    """The figure of a stage-1 solve: the propellant removed (summary.md's quoted x*) in t
    and % of stage 1 with the share of all; for the frontier case (a stage-2 pre-offload
    imposed first) the quoted stage-1 x*, the imposed stage-2 tonnes said not to be netted
    (appform.ADVANCED_FIXED_READING), then the total; then the penalty clause."""
    quoted = run_data.finite(record.get("quoted_offload_kg"))
    imposed = run_data.finite(record.get("stage2_preoffload_kg"))
    if imposed is not None and imposed > 0.0:
        stage1 = quoted if quoted is not None else run_data.finite(record.get("stage1_offload_kg"))
        return (
            f"Propellant removed at {ref}: "
            + ("an unknown amount" if stage1 is None else _t(stage1))
            + f" of stage 1 ({_pct(run_data.finite(record.get('stage1_fraction')))} of the "
            f"stage-1 load), solved after {_t(imposed)} imposed on stage 2 first "
            f"({appform.ADVANCED_FIXED_READING}); "
            + ("an unknown amount" if removed is None else _t(removed))
            + f", {_pct(run_data.finite(record.get('total_fraction')))} of all, in total"
            + replay.penalty_clause(record)
        )
    figure = quoted if quoted is not None else removed
    shares = replay.offload_shares(record).removeprefix("; ")
    return (
        f"Propellant removed at {ref}: "
        + ("an unknown amount" if figure is None else _t(figure))
        + ("" if not shares else f", {shares}")
        + replay.penalty_clause(record)
    )


def case_headline(record: Mapping[str, Any], offload: Mapping[str, Any]) -> dict[str, Any]:
    """The headline of an offload case's recorded run (design 4.7, D-SP2-27): a solve
    that found nothing or failed says how it ended (replay.solve_outcome); a stage-1
    solve the propellant removed at the pad's payload in t and % of stage 1 (the frontier
    case its stage-1 x* first, the imposed stage-2 tonnes not netted); a stage-2 or both
    solve its figure net of the pad control, a property of the vehicle model
    (appform.ADVANCED_SOLVE_READING), or, when nothing is quoted or x* is at or below the
    pad control's x_pad, 'nothing net of the pad control' (as ``classify`` says); a solved
    figure carries its verdicts (replay.offload_verdict_clause: a failed verification, a
    net figure that subtracts a flagged pad control) and ``flagged``; an imposed offload
    P* - P_ref with its reading (replay.payload_reading), never 'saved', and its assumed
    stage-1 dry mass when it carries one (replay.penalty_clause, as a solved figure
    does); one whose search did not end ok says so."""
    name = record.get("name")
    mode = record.get("mode")
    p_ref = run_data.finite(offload.get("reference_payload_kg"), 1)
    removed = run_data.finite(record.get("total_offload_kg"))
    out: dict[str, Any] = {
        "case": name,
        "mode": mode,
        "reference_payload_kg": p_ref,
        "removed_kg": removed,
        "stage1_fraction": run_data.finite(record.get("stage1_fraction")),
        "stage2_fraction": run_data.finite(record.get("stage2_fraction")),
        "total_fraction": run_data.finite(record.get("total_fraction")),
        "status": record.get("status"),
    }
    if record.get("kind") == run_data.OFFLOAD_SOLVED_KIND:
        ended = replay.solve_outcome(record)
        if ended is not None:
            failed = record.get("status") == SEARCH_FAILED_STATUS
            kind = HEADLINE_DID_NOT_FLY if failed else HEADLINE_NOTHING
            return {**out, "kind": kind, "text": f"Offload case {name}: {ended}"}
        ref = "the pad's payload" + ("" if p_ref is None else f" (P_ref = {p_ref:,.1f} kg)")
        quoted = run_data.finite(record.get("quoted_offload_kg"))
        netted = mode not in OFFLOAD_GROSS_MODES
        if netted and (quoted is None or quoted <= 0.0):
            return {
                **out,
                "kind": HEADLINE_NOTHING,
                "net_of_pad_control": True,
                "quoted_kg": quoted,
                "text": (
                    f"Offload case {name}: nothing net of the pad control (x* "
                    f"{_tonnes(record.get('offload_kg'))}, pad control "
                    f"{_tonnes(record.get('pad_control_offload_kg'))}, net "
                    f"{_tonnes(record.get('net_offload_kg'))}); {appform.ADVANCED_SOLVE_READING}"
                ),
            }
        clause = replay.offload_verdict_clause(
            {**record, "flags": []}, _case_control(offload, mode)
        )
        if not netted:
            text = _gross_solve_text(record, ref, removed) + clause
            figure = quoted if quoted is not None else removed
            return {
                **out,
                "kind": HEADLINE_SOLVED,
                "net_of_pad_control": False,
                "quoted_kg": figure,
                "flagged": bool(clause),
                "text": text,
            }
        assert quoted is not None
        text = (
            f"Propellant removed at {ref}: {_t(quoted)}"
            + ("" if removed is None else f" (gross {_t(removed)})")
            + f", {appform.ADVANCED_SOLVE_READING}"
            + clause
        )
        return {
            **out,
            "kind": HEADLINE_SOLVED,
            "net_of_pad_control": True,
            "quoted_kg": quoted,
            "reading": appform.ADVANCED_SOLVE_READING,
            "flagged": bool(clause),
            "text": text,
        }
    note = _imposed_case_note(name, record.get("status"))
    if note is not None:
        kind = HEADLINE_DID_NOT_FLY if note[0] == OUTCOME_DID_NOT_FLY else HEADLINE_NOT_IN_ORBIT
        return {**out, "kind": kind, "text": note[1][0].upper() + note[1][1:]}
    payload = run_data.finite(record.get("payload_kg"), 1)
    delta = run_data.finite(record.get("payload_delta_kg"), 1)
    if delta is None and payload is not None and p_ref is not None:
        delta = round(payload - p_ref, 1)
    reading = "" if delta is None else replay.payload_reading(delta, "P_ref", imposed=True)
    pre = run_data.finite(record.get("stage2_preoffload_kg"))
    stage1 = run_data.finite(record.get("stage1_offload_kg"))
    if pre is not None and pre > 0.0 and mode in OFFLOAD_GROSS_MODES:
        # the stage-1 offload and the stage-2 pre-offload apart, as the form sets them: the
        # sum is not what the push replaces (review of A5, usability)
        amount = (
            "Imposed offload: "
            + ("an unknown amount" if stage1 is None else _t(stage1))
            + f" from stage 1, plus a {_t(pre)} stage-2 pre-offload ({PRE_OFFLOAD_READING})"
        )
    else:
        amount = "Imposed offload of " + ("an unknown amount" if removed is None else _t(removed))
    text = (
        amount
        + replay.penalty_clause(record)
        + (": P* - P_ref not recorded" if delta is None else f": P* - P_ref {delta:+,.1f} kg")
        + reading
    )
    if mode not in OFFLOAD_GROSS_MODES:
        text += f"; {appform.ADVANCED_FIXED_READING}"
    return {
        **out,
        "kind": HEADLINE_IMPOSED,
        "payload_kg": payload,
        "delta_kg": delta,
        "reading": reading.strip().removeprefix("(").removesuffix(")") or None,
        "text": text,
    }


def run_headline(
    name: str, source: Mapping[str, Any], metrics: Mapping[str, Any]
) -> dict[str, Any]:
    """The headline of one run (design 4.7): an offload case's run by ``case_headline``;
    a paired pad or a pad control by the replay page's note; a run that did not fly or
    did not reach the target orbit says so with its status; a run whose own checks
    failed (status bug_suspect, its trajectory's end kept in ``trace_status``) says
    findings are blocked, how its trajectory ended and its payload as not to be quoted
    (HEADLINE_FLAGGED), never that it missed the orbit; else its payload capacity and,
    when it is compared with a run, the difference (an upper bound flagged; a comparison
    that is bug_suspect flagged, ``flagged`` True), and for an instant-startup run
    (``replay.is_yardstick``) that it is a yardstick, not a design (YARDSTICK_TEXT,
    ``yardstick`` True)."""
    m = run_data.as_mapping(source.get("metrics"))
    offload = run_data.as_mapping(metrics.get("offload"))
    kind = source.get("offload_kind")
    if source.get("role") == run_data.ROLE_OFFLOAD:
        role = run_data.offload_role(offload, name)
        if kind == run_data.OFFLOAD_CASE and role is not None:
            return case_headline(role[1], offload)
        what = HEADLINE_PAD_CONTROL if kind == run_data.OFFLOAD_PAD_CONTROL else HEADLINE_PAIRED_PAD
        return {"kind": what, "text": str(source.get("note", ""))}
    status = str(m.get("status", "unknown"))
    if status in NOT_FLOWN_STATUSES:
        why = m.get("search_failure_kind") or m.get("guidance_failure_kind") or "no reason"
        return {
            "kind": HEADLINE_DID_NOT_FLY,
            "status": status,
            "text": f"The run did not fly: {status} ({why})",
        }
    if status == BUG_SUSPECT:
        trace = str(m.get("trace_status") or "unknown")
        why = m.get("run_checks_failed") or "its run checks failed"
        payload = run_data.finite(m.get("payload_kg"), 1)
        return {
            "kind": HEADLINE_FLAGGED,
            "status": status,
            "trace_status": trace,
            "flagged": True,
            "payload_kg": payload,
            "text": (
                f"{name}: {BUG_SUSPECT} ({why}): {FINDINGS_BLOCKED_TEXT}; its trajectory "
                f"ended {trace}"
                + (
                    ""
                    if payload is None
                    else f"; payload capacity {payload:,.1f} kg, not to be quoted"
                )
            ),
        }
    if status != INSERTED_STATUS:
        return {
            "kind": HEADLINE_NOT_IN_ORBIT,
            "status": status,
            "text": f"{name} did not reach the target orbit (status {status})",
        }
    payload = run_data.finite(m.get("payload_kg"), 1)
    against = source.get("compared_to")
    comp = run_data.as_mapping(source.get("comparison"))
    delta = None if against is None else run_data.finite(comp.get("payload_delta_kg"), 1)
    upper = against is not None and comp.get("payload_delta_upper_bound") is True
    yard = replay.is_yardstick(dict(m))
    text = "Payload capacity " + ("not recorded" if payload is None else f"{payload:,.1f} kg")
    if delta is not None:
        text += f", {delta:+,.1f} kg against {against}"
        if upper:
            text += " (an upper bound: unthrottled and unconstrained)"
    flagged = against is not None and comp.get("screening_status") == BUG_SUSPECT
    if flagged:
        text += (
            f"; flagged: its comparison with {against} is {BUG_SUSPECT}: {FINDINGS_BLOCKED_TEXT}"
        )
    if yard:
        text += f"; {YARDSTICK_TEXT}"
    return {
        "kind": HEADLINE_PAYLOAD,
        "payload_kg": payload,
        "delta_kg": delta,
        "against": against,
        "upper_bound": upper,
        "yardstick": yard,
        "flagged": flagged,
        "text": text,
    }


def push_view(m: Mapping[str, Any], assist: Mapping[str, Any]) -> dict[str, Any]:
    """The push of a pushed run (PUSH_METRICS from its metrics; ``text``: the replay
    page's assist_text; ``model``: the assist model, so the page says what a prescribed
    constant-acceleration drive does not depend on)."""
    out: dict[str, Any] = {key: run_data.finite(m.get(src)) for key, src in PUSH_METRICS}
    out["text"] = replay.assist_text(dict(assist), dict(m))
    model = assist.get("model")
    out["model"] = model if isinstance(model, str) else None
    return out


def _max_q_against(
    name: str, source: Mapping[str, Any], metrics: Mapping[str, Any]
) -> tuple[bool | None, float | None, str | None]:
    """(max-Q above the compared run's, that run's max-Q [Pa], its name) from the run's
    own comparison: a variant's or bound's ``max_q_above_baseline`` against the run it is
    compared with (a bound's paired baseline, not the pad), an offload case's
    ``vs_pad.max_q_above_pad`` and ``pad_max_q_pa`` against the baseline; (None, None,
    None) when the run has no such comparison."""
    offload = run_data.as_mapping(metrics.get("offload"))
    if source.get("offload_kind") == run_data.OFFLOAD_CASE:
        role = run_data.offload_role(offload, name)
        vs_pad = run_data.as_mapping(None if role is None else role[1].get("vs_pad"))
        above = vs_pad.get("max_q_above_pad")
        if not isinstance(above, bool):
            return None, None, None
        return above, run_data.finite(vs_pad.get("pad_max_q_pa")), str(metrics.get("baseline"))
    against = source.get("compared_to")
    comp = run_data.as_mapping(source.get("comparison"))
    above = comp.get("max_q_above_baseline")
    if against is None or not isinstance(above, bool):
        return None, None, None
    if source.get("role") == run_data.ROLE_BOUND:
        bounds = metrics.get("bounds") or []
        ref = next(
            (
                run_data.as_mapping(b).get("paired_baseline_metrics")
                for b in bounds
                if run_data.as_mapping(b).get("run") == name
            ),
            None,
        )
    else:
        ref = run_data.as_mapping(metrics.get("runs")).get(str(against))
    return above, run_data.finite(run_data.as_mapping(ref).get("max_q_pa")), str(against)


def _kpa(pa: float) -> str:
    """'37.2 kPa' of a pressure [Pa]."""
    return f"{float(pa_to_kpa(pa)):.1f} kPa"


def flight_view(name: str, source: Mapping[str, Any], metrics: Mapping[str, Any]) -> dict[str, Any]:
    """The flight of a run (FLIGHT_METRICS; MECO after release), its stage-1 ignition
    in the replay page's words, and max-Q 'above' or 'below' the compared run's from the
    run's own comparison (``_max_q_against``; None without one, and None for a run that
    ended neither inserted nor bug_suspect, whose flight is no like-for-like comparison):
    'the pad's'
    when that run is the baseline, else the run by name (a bound is compared with its
    paired baseline), named in ``max_q_against``."""
    m = run_data.as_mapping(source.get("metrics"))
    assisted = replay.is_assisted(replay.run_assist(run_data.as_mapping(source.get("config"))))
    out: dict[str, Any] = {key: run_data.finite(m.get(src)) for key, src in FLIGHT_METRICS}
    out["status"] = str(m.get("status", "unknown"))
    out["ignition"] = replay.ignition_text(dict(m), assisted)
    above, pad_q, against = _max_q_against(name, source, metrics)
    if m.get("status") not in (INSERTED_STATUS, BUG_SUSPECT):
        above, pad_q, against = None, None, None
    out["max_q_vs_pad"] = None if above is None else ("above" if above else "below")
    out["pad_max_q_pa"] = pad_q
    out["max_q_against"] = against
    q = out["max_q_pa"]
    if q is None:
        out["max_q_text"] = None
    elif above is None:
        out["max_q_text"] = f"max-Q {_kpa(q)}"
    else:
        pad_text = "" if pad_q is None else f" ({_kpa(pad_q)})"
        word = "above" if above else "below"
        whose = "the pad's" if against == str(metrics.get("baseline")) else f"{against}'s"
        out["max_q_text"] = f"max-Q {_kpa(q)}, {word} {whose}{pad_text}"
    return out


def verification_view(record: Mapping[str, Any], offload: Mapping[str, Any]) -> dict[str, Any]:
    """An offload case's verification and verdicts: passed, its P* - P_ref and
    tolerance; for a failed one the replay page's reading of its sign
    (replay.verification_reading: a flagged lower bound only above P_ref) and the case's
    verdict row (``_verdict_note``). For a stage-2 or both-stage case (quoted net of its
    pad control) a failed verification's ``text`` is the whole verdict, so it also says
    what the net figure is (uncertain both ways when the control is flagged), never only
    that the gross removal is a lower bound. An imposed (fixed) case is not verified: its
    text says so (IMPOSED_VERIFICATION_TEXT), never 'no verification recorded'."""
    v = run_data.as_mapping(record.get("verification"))
    passed = v.get("passed")
    verdict = _verdict_note(offload, record)
    out: dict[str, Any] = {
        "passed": passed if isinstance(passed, bool) else None,
        "delta_kg": run_data.finite(v.get("delta_kg")),
        "tolerance_kg": run_data.finite(v.get("tolerance_kg")),
        "status": v.get("status"),
        "lower_bound": False,
        "text": None,
        "verdict": verdict,
    }
    if record.get("kind") != run_data.OFFLOAD_SOLVED_KIND:
        out["text"] = IMPOSED_VERIFICATION_TEXT
        return out
    if not v:
        out["text"] = "no verification recorded"
    elif passed is False:
        size, reading, lower = replay.verification_reading(v)
        out["text"] = f"verification failed{size}: {reading}"
        out["lower_bound"] = lower
        mode = record.get("mode")
        if verdict is not None and mode is not None and mode not in OFFLOAD_GROSS_MODES:
            out["text"] = verdict.removeprefix(f"offload case {record.get('name')}: ")
    elif passed is True:
        delta, tol = out["delta_kg"], out["tolerance_kg"]
        size = "" if delta is None or tol is None else f" ({delta:+.2f} kg against {tol:.1f} kg)"
        out["text"] = f"verification passed{size}"
    return out


def run_view(
    name: str,
    metrics: Mapping[str, Any],
    config: Mapping[str, Any],
    rows: Mapping[str, bool],
) -> dict[str, Any]:
    """One run of a results directory for the run list and the results panel: its name,
    label, role, offload kind and note (replay.run_source over run_data.run_source: the
    replay page's own note for an offload run), status, whether its series holds a row,
    whether it is a yardstick, and its headline, push, flight, flags (the run's, its
    offload case's, and a line for a comparison with the run it is compared with that is
    bug_suspect) and (for an offload case) verification. A run folder metrics.json does
    not describe has only its name and a note saying so."""
    baseline = str(metrics.get("baseline"))
    offload = run_data.as_mapping(metrics.get("offload"))
    try:
        source = replay.run_source(dict(metrics), dict(config), name)
    except run_data.RunDataError:
        return {
            "name": name,
            "label": name,
            "role": None,
            "offload_kind": None,
            "note": "metrics.json does not describe this run folder",
            "has_rows": rows.get(name, False),
        }
    m = run_data.as_mapping(source["metrics"])
    assist = replay.run_assist(run_data.as_mapping(source["config"]))
    assisted = replay.is_assisted(assist)
    role = run_data.offload_role(offload, name)
    case = role[1] if role is not None and role[0] == run_data.OFFLOAD_CASE else None
    flags = [str(f) for f in m.get("flags") or []]
    flags += [str(f) for f in (case or {}).get("flags") or [] if str(f) not in flags]
    against = source.get("compared_to")
    comp = run_data.as_mapping(source.get("comparison"))
    if against is not None and comp.get("screening_status") == BUG_SUSPECT:
        flags.append(f"comparison with {against} is {BUG_SUSPECT}: {FINDINGS_BLOCKED_TEXT}")
    return {
        "name": name,
        "label": replay.run_label(name, source["role"], name == baseline, source["offload_kind"]),
        "role": source["role"],
        "offload_kind": source["offload_kind"],
        "note": source["note"],
        "status": str(m.get("status", "unknown")),
        "has_rows": rows.get(name, False),
        "yardstick": replay.is_yardstick(dict(m)),
        "assisted": assisted,
        "headline": run_headline(name, source, metrics),
        "push": push_view(m, assist) if assisted else None,
        "flight": flight_view(name, source, metrics),
        "flags": flags,
        "verification": None if case is None else verification_view(case, offload),
    }


def shown_run(
    metrics: Mapping[str, Any], config: Mapping[str, Any], rows: Mapping[str, bool]
) -> str | None:
    """The run the results panel describes: for an app run (label exploratory) the
    launch's own offload case run when it has one, else its variant, else the baseline;
    for a recorded directory the right-hand run of the scene's default pair
    (scene.default_pair, D-SP2-28), else its left. Only runs with a folder count."""
    names = list(rows)
    baseline = str(metrics.get("baseline"))
    if replay.is_exploratory(metrics):
        offload = run_data.as_mapping(metrics.get("offload"))
        for case in offload.get("cases") or []:
            run = run_data.as_mapping(case).get("run")
            if run in names:
                return str(run)
        variant = next((n for n in run_data.as_mapping(metrics.get("runs")) if n != baseline), None)
        if variant in names:
            return str(variant)
        return baseline if baseline in names else (names[0] if names else None)
    pair = scene.default_pair(dict(metrics), dict(config), [n for n in names if rows[n]])
    if pair:
        return pair[-1]
    return baseline if baseline in names else (names[0] if names else None)


def directory_reproduction_lines(basis: appform.Basis, metrics: Mapping[str, Any]) -> list[str]:
    """The reproduction lines of an app run's directory (D-SP2-36), from what it
    records: only for an exploratory directory whose git record has a server-start state
    and the commit its experiment files were read from; the pad alone is the committed
    baseline; a variant or case is a reproduction when it kept a committed name (a key of
    ``basis.variant_fragments`` or ``basis.case_fragments``, the committed files' names:
    the app keeps one only for the committed configuration at that commit, and no
    neutral name is one). [] otherwise."""
    if not replay.is_exploratory(metrics):
        return []
    git = run_data.as_mapping(metrics.get("git"))
    commit = git.get(summary.EXPLORATORY_BASIS_COMMIT_KEY)
    if not isinstance(git.get(summary.EXPLORATORY_SERVER_START_KEY), Mapping):
        return []
    if not isinstance(commit, str) or not commit:
        return []
    baseline = str(metrics.get("baseline"))
    runs = list(run_data.as_mapping(metrics.get("runs")))
    if runs == [baseline]:
        return [baseline_reproduction_line(baseline, commit)]
    names = [n for n in runs if n != baseline and n in basis.variant_fragments]
    for case in run_data.as_mapping(metrics.get("offload")).get("cases") or []:
        cname = run_data.as_mapping(case).get("name")
        if cname in basis.case_fragments:
            names.append(str(cname))
    return [committed_reproduction_line(basis, n, commit) for n in names]


class TooManyLeaves(Exception):
    """A run dict with more than LEAF_BUDGET leaves (``_leaves``)."""


def _leaves(obj: Any, prefix: str = "", budget: int = LEAF_BUDGET) -> dict[str, Any]:
    """The leaves of a nested mapping by dotted path (a list or an empty mapping is one
    leaf), depth first in key order. Raises TooManyLeaves once more than ``budget`` leaves
    are found (a mapping reached twice, as a YAML alias makes it, is walked twice: the
    budget bounds the walk); RecursionError for a mapping that holds itself."""
    if not isinstance(obj, Mapping):
        return {prefix: obj}
    out: dict[str, Any] = {}

    def walk(node: Mapping[str, Any], base: str) -> None:
        for key, value in node.items():
            path = f"{base}.{key}" if base else str(key)
            if isinstance(value, Mapping) and value:
                walk(value, path)
            else:
                out[path] = value
                if len(out) > budget:
                    raise TooManyLeaves(f"more than {budget:,} settings")

    walk(obj, prefix)
    return out


def _setting_text(value: Any) -> str:
    """A setting as the comparison line shows it: 'not set' for absent (so a push key
    stated the other way never reads as 'no push'), true/false, a float's shortest repr
    (every digit that differs is shown), else its text."""
    if value is None:
        return "not set"
    if isinstance(value, bool):
        return "true" if value else "false"
    return repr(value) if isinstance(value, float) else str(value)


def _tonnes_setting(kg: Any) -> str:
    """A recorded mass [kg] as the form states it in t (6 significant digits), or 'none'."""
    value = run_data.finite(kg)
    return "none" if value is None else f"{float(kg_to_t(value)):g}"


def _fragment_settings(fragment: Mapping[str, Any]) -> dict[str, str]:
    """The offload settings of a committed case fragment: how its propellant is taken
    out, the stage-2 pre-offload [t], the assumed stage-1 dry mass [t] and the paired
    pad."""
    if "solve" in fragment:
        how = f"solve {fragment['solve']}"
    else:
        ((key, value),) = dict(fragment.get("fixed") or {"unknown": None}).items()
        how = f"imposed {key} {_setting_text(value)}"
    pre = float(fragment.get("stage2_offload_t") or 0.0)
    dry = float(fragment.get("stage1_dry_mass_added_t") or 0.0)
    return {
        "offload": how,
        "stage-2 pre-offload [t]": f"{pre:g}",
        "assumed stage-1 dry mass [t]": f"{dry:g}",
        "paired pad": "yes" if fragment.get("paired_pad") else "no",
    }


def _record_settings(record: Mapping[str, Any]) -> dict[str, str]:
    """The offload settings of a directory's case record (metrics.json), in the terms of
    ``_fragment_settings``."""
    if record.get("kind") == run_data.OFFLOAD_SOLVED_KIND:
        how = f"solve {record.get('mode')}"
    else:
        fraction = run_data.finite(record.get("fixed_fraction"))
        value = (
            _setting_text(fraction)
            if fraction is not None
            else _tonnes_setting(record.get("offload_kg"))
        )
        how = f"imposed {record.get('fixed_key')} {value}"
    return {
        "offload": how,
        "stage-2 pre-offload [t]": _tonnes_setting(record.get("stage2_preoffload_kg") or 0.0),
        "assumed stage-1 dry mass [t]": _tonnes_setting(
            record.get("stage1_dry_mass_added_kg") or 0.0
        ),
        "paired pad": "yes" if isinstance(record.get("paired_pad"), Mapping) else "no",
    }


def sp1_differences(
    basis: appform.Basis, metrics: Mapping[str, Any], config: Mapping[str, Any]
) -> list[str] | None:
    """What an app run's directory records differently from SP1's headline case
    (SP1_HEADLINE.case and its variant, from the server's committed basis; design 4.7's
    comparison line), one line each, '<setting>: <this launch> (SP1's <case>: <SP1's>)':
    a launch of the pad alone, or a pad-site variant (no push), says so in one line; a
    silo variant compares every leaf of its run dict (resolved_config.yaml's
    runs.<variant>.run, the name aside) with the committed variant's; the offload compares
    how the propellant is taken out, the stage-2 pre-offload, the assumed penalty and the
    paired pad (metrics.json's case record) with the committed case. A run dict of more
    than LEAF_BUDGET leaves is not compared leaf by leaf (one line says so); at most
    SP1_DIFF_MAX_LINES lines are listed, then one 'and N more' line. [] when nothing
    differs; None when the basis does not carry SP1's case and its variant. Pure."""
    case = SP1_HEADLINE.case
    fragment = basis.case_fragments.get(case)
    committed = None if fragment is None else basis.committed_runs.get(str(fragment.get("of")))
    if fragment is None or committed is None:
        return None
    sp1 = f"SP1's {case}"
    baseline = str(metrics.get("baseline"))
    variant = next((n for n in run_data.as_mapping(metrics.get("runs")) if n != baseline), None)
    if variant is None:
        return [f"launch: the pad alone, no push and no offload ({sp1}: {committed.name}'s push)"]
    run_cfg = run_data.as_mapping(
        run_data.as_mapping(run_data.as_mapping(config.get("runs")).get(variant)).get("run")
    )
    theirs = {k: v for k, v in _leaves(committed.run_dict).items() if k != "name"}
    lines: list[str] = []
    try:
        ours = {k: v for k, v in _leaves(run_cfg).items() if k != "name"}
    except TooManyLeaves:
        ours = None
        lines.append(
            f"run: more than {LEAF_BUDGET:,} settings, not compared one by one ({sp1}: "
            f"{len(theirs)} settings)"
        )
    model = run_data.as_mapping(run_cfg.get("assist")).get("model", "none")
    if model == "none":
        lines.append(f"site: the pad, no push ({sp1}: {committed.name}'s push)")
        theirs = {k: v for k, v in theirs.items() if not k.startswith("assist.")}
        if ours is not None:
            ours = {k: v for k, v in ours.items() if not k.startswith("assist.")}
    if ours is not None:
        for path in [*theirs, *(k for k in ours if k not in theirs)]:
            if ours.get(path) != theirs.get(path):
                lines.append(
                    f"{path}: {_setting_text(ours.get(path))} ({sp1}: "
                    f"{_setting_text(theirs.get(path))})"
                )
    cases = run_data.as_mapping(metrics.get("offload")).get("cases") or []
    record = next((run_data.as_mapping(c) for c in cases), None)
    want = _fragment_settings(fragment)
    if record is None:
        lines.append(f"offload: none, a full load ({sp1}: {want['offload']})")
    else:
        have = _record_settings(record)
        lines += [
            f"{key}: {have[key]} ({sp1}: {want[key]})" for key in want if have[key] != want[key]
        ]
    if len(lines) > SP1_DIFF_MAX_LINES:
        more = len(lines) - SP1_DIFF_MAX_LINES
        lines = [*lines[:SP1_DIFF_MAX_LINES], f"and {more:,} more"]
    return lines


def sp1_files_same(
    repo_root: Path, basis: appform.Basis, commit: Any = dataclasses.MISSING
) -> bool | None:
    """Whether the files SP1's headline case is built from, OFFLOAD_EXPERIMENT and the
    vehicle file it names (``basis.vehicle_path``), are the same at ``commit`` (default:
    the basis commit; a directory's recorded basis commit for its panel) as at
    SP1_HEADLINE.commit: ``git diff --quiet <SP1's commit> <commit> -- <files>`` in
    repo_root (an argument list, read-only). True for no difference, False for one, None
    when it cannot be told (no commit, one that is not a hex hash (COMMIT_PATTERN: never
    passed to git), git missing, a timeout, a commit git does not know)."""
    if commit is dataclasses.MISSING:
        commit = basis.commit
    if not isinstance(commit, str) or not COMMIT_PATTERN.fullmatch(commit):
        return None
    files = (OFFLOAD_EXPERIMENT.as_posix(), basis.vehicle_path)
    try:
        proc = subprocess.run(
            ["git", "diff", "--quiet", SP1_HEADLINE.commit, commit, "--", *files],
            cwd=repo_root,
            capture_output=True,
            timeout=results_io.GIT_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return {GIT_DIFF_SAME: True, GIT_DIFF_DIFFERENT: False}.get(proc.returncode)


def sp1_comparison(
    basis: appform.Basis,
    metrics: Mapping[str, Any],
    config: Mapping[str, Any],
    reproduces: Sequence[str],
    sp1_same: bool | None = None,
) -> dict[str, Any] | None:
    """The results panel's comparison with SP1's headline case for an app run (design
    4.7; review 06 finding 5): ``case`` and ``directory`` (SP1's), ``reproduces`` (True
    only when the directory kept SP1's committed case name, ``reproduces`` being its
    reproduction lines, nothing differs, its x* is SP1's within REPRODUCTION_TOL_KG, and
    the basis files at the directory's recorded basis commit are SP1's: ``sp1_same``
    True, ``sp1_files_same``), ``differs`` (``sp1_differences``), ``offload_kg`` (the
    directory's x*: its case's quoted_offload_kg, None without a case or a figure) and
    one ``text``: that the settings differ and so the figure is not SP1's headline; or
    that they agree but x* is not SP1's recorded figure (the code differs; or x* is not
    recorded); or the reproduction line; or that they agree but the basis files differ
    from SP1's (or could not be checked against them), so the figure is not called SP1's
    headline; or that they agree but the launch kept no committed name (not called a
    reproduction). None for a recorded directory or a basis without SP1's case."""
    if not replay.is_exploratory(metrics):
        return None
    differs = sp1_differences(basis, metrics, config)
    if differs is None:
        return None
    case = SP1_HEADLINE.case
    line = next((ln for ln in reproduces if ln.startswith(f"{case}:")), None)
    figure = _case_figure(metrics)
    same = False
    if differs:
        n = len(differs)
        if n > SP1_DIFF_MAX_LINES:  # the last line is 'and N more'
            count = f"more than {SP1_DIFF_MAX_LINES} settings differ"
        else:
            count = f"{n} {'setting differs' if n == 1 else 'settings differ'}"
        text = (
            f"not SP1's {case}: {count} from it, so this figure is not SP1's headline "
            f"({SP1_HEADLINE.directory})"
        )
    elif not sp1_figure_matches(figure):
        shown = "not recorded" if figure is None else f"{figure:,.1f} kg"
        text = (
            f"same configuration as SP1's {case}, but x* = {shown} against SP1's recorded "
            f"{SP1_HEADLINE.offload_kg:,.1f} kg ({SP1_HEADLINE.commit}): the code differs, so "
            "this is not SP1's headline"
        )
    elif line is not None and sp1_same is True:
        same = True
        text = line
    elif line is not None:
        commit = run_data.as_mapping(metrics.get("git")).get(summary.EXPLORATORY_BASIS_COMMIT_KEY)
        at = f" at commit {commit[:12]}" if isinstance(commit, str) and commit else ""
        why = "differ from" if sp1_same is False else "could not be checked against"
        text = (
            f"same configuration as the committed {case} of the app's basis{at}, whose files "
            f"{why} SP1's at {SP1_HEADLINE.commit}: not called SP1's headline"
        )
    else:
        text = (
            f"the settings this directory records equal SP1's {case}, but the launch kept no "
            "committed name (its experiment files were not read from a commit), so it is not "
            "called a reproduction"
        )
    return {
        "case": case,
        "directory": SP1_HEADLINE.directory,
        "reproduces": same,
        "differs": differs,
        "offload_kg": figure,
        "text": text,
    }


def _case_figure(metrics: Mapping[str, Any], name: str | None = None) -> float | None:
    """The quoted x* [kg] (quoted_offload_kg) of the offload case named ``name`` in
    metrics.json (the first case when ``name`` is None: a launch's one case, the record
    ``sp1_differences`` compares), or None."""
    for case in run_data.as_mapping(metrics.get("offload")).get("cases") or []:
        record = run_data.as_mapping(case)
        if name is None or record.get("name") == name:
            return run_data.finite(record.get("quoted_offload_kg"))
    return None


def sp1_figure_matches(figure: float | None) -> bool:
    """True when an x* [kg] is SP1's recorded one (SP1_HEADLINE.offload_kg) within
    REPRODUCTION_TOL_KG."""
    return figure is not None and abs(figure - SP1_HEADLINE.offload_kg) <= REPRODUCTION_TOL_KG


SP1_GIT_VIEW = {"hash": SP1_HEADLINE.commit, "state": "clean"}
"""The git record (``git_view``) of SP1's results directory: its commit, clean."""


def sp1_headline_for(
    experiment: str,
    timestamp: str,
    shown: str | None,
    metrics: Mapping[str, Any],
    comparison: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """SP1's headline with its six caveat groups (D-SP2-36) when the panel shows SP1's
    headline case and the directory holds SP1's figure: in SP1's own directory
    (SP1_HEADLINE.directory by name) only when its git record is SP1's commit, clean
    (SP1_GIT_VIEW), and the case's x* is SP1's within REPRODUCTION_TOL_KG
    (``sp1_figure_matches``), so a copy under that name with another figure or commit
    never carries it; or in an app run whose comparison with SP1's case
    (``sp1_comparison``) says it reproduces it (its committed name kept, no setting
    different, x* SP1's, the basis files at its basis commit SP1's); else None."""
    if shown != SP1_HEADLINE.case:
        return None
    own = (
        SP1_HEADLINE.directory.endswith(f"/{experiment}/{timestamp}")
        and git_view(metrics.get("git")) == SP1_GIT_VIEW
        and sp1_figure_matches(_case_figure(metrics, SP1_HEADLINE.case))
    )
    kept = (
        replay.is_exploratory(metrics)
        and comparison is not None
        and comparison.get("reproduces") is True
    )
    return SP1_HEADLINE.record() if own or kept else None


def tag_view(metrics: Mapping[str, Any], experiment: str, timestamp: str) -> dict[str, Any]:
    """The results panel's tag (design 4.7): an app run is 'Exploratory app run: not a
    finding' with the launch's git state, the server-start state and the working tree at
    launch; any other directory 'Recorded: <experiment>/<timestamp>' with its git state
    and label."""
    git = run_data.as_mapping(metrics.get("git"))
    view = git_view(git)
    label = metrics.get("label")
    if replay.is_exploratory(metrics):
        start = git.get(summary.EXPLORATORY_SERVER_START_KEY)
        launch = git.get(summary.EXPLORATORY_LAUNCH_DIRTY_KEY, git.get("dirty"))
        return {
            "kind": "exploratory",
            "text": TAG_EXPLORATORY_TEXT,
            "git": view,
            "server_start": git_view(start) if isinstance(start, Mapping) else None,
            "launch_tree": tree_state(launch, git.get("hash")),
            "label": None if label is None else str(label),
        }
    return {
        "kind": "recorded",
        "text": f"Recorded: {experiment}/{timestamp}, git {view['hash']} ({view['state']})",
        "git": view,
        "server_start": None,
        "launch_tree": None,
        "label": None if label is None else str(label),
    }


def panel_caveats(
    run_dir: Path,
    metrics: Mapping[str, Any],
    runs: Sequence[dict[str, Any]],
    pair: Sequence[str],
) -> dict[str, Any]:
    """The caveats of the runs a panel shows (design 4.7, D-SP2-36), from the directory:
    every item replay.caveats gives those runs (replay.replay_data of the runs of
    ``pair`` that hold a row: the structure caveat names each run's own load, the
    exploratory line comes first for an app run), and, when one of them is an offload
    run, the directory's own offload.caveats word for word. When no run of the pair holds
    a row, or the replay builder refuses, the list keeps the exploratory line only and
    ``error`` says why."""
    by_name = {r["name"]: r for r in runs}
    shown = [n for n in pair if by_name.get(n, {}).get("has_rows")]
    caveats: list[str] = []
    error = None
    if shown:
        try:
            caveats = [str(c) for c in replay.replay_data(run_dir, shown)["meta"]["caveats"]]
        except Exception as exc:  # a directory the replay builder refuses still lists
            error = f"the caveat list could not be built: {type(exc).__name__}"
    else:
        error = "no run shown holds a time series"
    if not caveats and replay.is_exploratory(metrics):
        caveats = [replay.EXPLORATORY_CAVEAT]
    offload_caveats: list[str] = []
    if any(by_name.get(n, {}).get("role") == run_data.ROLE_OFFLOAD for n in pair):
        raw = run_data.as_mapping(metrics.get("offload")).get("caveats")
        offload_caveats = [str(c) for c in raw] if isinstance(raw, list) else []
    return {
        "caveats": caveats,
        "offload_caveats": offload_caveats,
        "built_for": shown,
        "error": error,
    }


def results_panel(
    run_dir: Path,
    experiment: str,
    timestamp: str,
    basis: appform.Basis,
    metrics: Mapping[str, Any],
    config: Mapping[str, Any],
    sp1_same: bool | None = None,
    chosen: Sequence[str] | None = None,
) -> dict[str, Any]:
    """The results panel data of a complete planar results directory (design 4.7),
    built from the directory alone, so a recorded directory gets the same panel as a
    fresh launch: the run list (``run_view`` of every run folder), the scene's default
    pair, the run shown (``shown_run``; with ``chosen``, 1 to PANEL_RUNS run folders the
    page shows side by side, its right-hand run, and the pair is ``chosen``), the tag, the
    shown run's headline, SP1's headline with its caveat groups when the shown run is SP1's
    case in SP1's directory or a reproduction of it (``sp1_headline_for``), the
    reproduction lines (``directory_reproduction_lines``), the comparison with SP1's case
    (``sp1_comparison``; ``sp1_same``: whether the basis files at the directory's recorded
    basis commit are SP1's, ``sp1_files_same``, ``AppServer.sp1_same_at``), the push,
    flight, flags and verification, the outcome (``classify``), the caveats of the pair
    (``panel_caveats``) and what the scene draws that the model does not compute
    (scene.DISPLAY_ONLY, design 4.9). Raises ValueError for a ``chosen`` that is not 1 to
    PANEL_RUNS distinct run folders."""
    rows = run_folders(run_dir, metrics)
    runs = [run_view(n, metrics, config, rows) for n in rows]
    available = [n for n in rows if rows[n]]
    default = scene.default_pair(dict(metrics), dict(config), available) if available else []
    baseline = str(metrics.get("baseline"))
    if chosen is not None:
        names = list(chosen)
        if not 1 <= len(names) <= PANEL_RUNS or len(set(names)) != len(names):
            raise ValueError(f"a panel describes 1 to {PANEL_RUNS} distinct runs")
        if any(n not in rows for n in names):
            raise ValueError("a run the panel would describe is not in the run list")
        shown: str | None = names[-1]
        pair = names
    else:
        shown = shown_run(metrics, config, rows)
        pair = list(dict.fromkeys(n for n in (baseline, shown) if n is not None and n in rows))
    view = next((r for r in runs if r["name"] == shown), None)
    kind, message, notes = classify(run_dir)
    reproduces = directory_reproduction_lines(basis, metrics)
    comparison = sp1_comparison(basis, metrics, config, reproduces, sp1_same)
    panel = {
        "tag": tag_view(metrics, experiment, timestamp),
        "shown": shown,
        "pair": pair,
        "headline": None if view is None else view.get("headline"),
        "sp1_headline": sp1_headline_for(experiment, timestamp, shown, metrics, comparison),
        "reproduces": reproduces,
        "sp1_comparison": comparison,
        "push": None if view is None else view.get("push"),
        "flight": None if view is None else view.get("flight"),
        "flags": [] if view is None else view.get("flags", []),
        "verification": None if view is None else view.get("verification"),
        "outcome": {"kind": kind, "message": message, "notes": list(notes)},
        **panel_caveats(run_dir, metrics, runs, pair),
        "display_only": list(scene.DISPLAY_ONLY),
    }
    return {
        "baseline": baseline,
        "runs": runs,
        "default_pair": default,
        "panel": panel,
    }


def app_description(
    metrics: Mapping[str, Any], config: Mapping[str, Any], outcome: tuple[str, str] | None = None
) -> str:
    """The run browser's one line for an app run, from its metrics and config (the form
    is not stored): the launched run (the variant, else the pad) with the replay page's
    assist and ignition text, then the headline of its offload case (its verdicts
    included), else its own; then the outcome (``classify``'s kind and message) unless it
    is OUTCOME_COMPLETE, so a flagged figure never reads as unflagged: the kind in words
    (underscores as spaces) and the message, left out only when the launched run's own
    headline already says it (a run that did not fly or did not reach orbit, with no
    offload case: the message then names that run)."""
    text = _app_line(metrics, config)
    if outcome is None or outcome[0] == OUTCOME_COMPLETE:
        return text
    kind, message = outcome
    baseline = str(metrics.get("baseline"))
    name = _launched_run(metrics)
    has_case = bool(run_data.as_mapping(metrics.get("offload")).get("cases"))
    said = kind in (OUTCOME_DID_NOT_FLY, OUTCOME_NOT_IN_ORBIT) and not has_case
    if said and name != baseline and str(message).startswith(f"{name} "):
        return text
    return f"{text}; {kind.replace('_', ' ')}: {message}"


def _launched_run(metrics: Mapping[str, Any]) -> str:
    """The run an app directory's line describes: its variant, else the pad."""
    baseline = str(metrics.get("baseline"))
    runs = run_data.as_mapping(metrics.get("runs"))
    return str(next((n for n in runs if n != baseline), baseline))


NOT_FLOWN_IGNITION = {
    SEARCH_FAILED_STATUS: "no flight recorded (its search failed), so no ignition time",
    sim.GUIDANCE_FAILED_STATUS: "no flight recorded (its guidance failed), so no ignition time",
}
"""What a run that did not fly says in place of its ignition: its metrics hold no
ignition time because nothing was flown, not because stage 1 never lit."""


def configured_ramp_start(run_cfg: Mapping[str, Any]) -> str:
    """The stage-1 ramp start a run block of resolved_config.yaml sets, in words (for a run
    that did not fly, whose metrics record no ignition): never lit by design (a failed
    ignition), a depth below the mouth, a speed on the push, a height above the mouth
    (with its method), else a time after release or after the push starts. Reads only the
    config; says nothing about whether stage 1 lit."""
    stage1 = run_data.as_mapping(run_data.as_mapping(run_cfg.get("ignition")).get("stage1"))
    if stage1.get("fails") is True:
        return "stage 1 set never to light (failed ignition)"
    depth = run_data.finite(stage1.get("at_depth_m"))
    if depth is not None:
        return f"ramp start set at {depth:g} m below the mouth"
    speed = run_data.finite(stage1.get("at_speed_mps"))
    if speed is not None:
        return f"ramp start set at {speed:g} m/s on the push"
    height = run_data.finite(stage1.get("at_height_m"))
    if height is not None:
        method = stage1.get("height_method")
        how = f" ({method} method)" if isinstance(method, str) and method else ""
        return f"ramp start set at {height:g} m above the mouth{how}"
    t = run_data.finite(stage1.get("t_ign_s"))
    origin = "push start" if stage1.get("reference") == appform.PUSH_START_REFERENCE else "release"
    return f"ramp start set at T{0.0 if t is None else t:+g} s from {origin}"


def _depth_from_config(m: Mapping[str, Any], assist: Mapping[str, Any]) -> dict[str, Any]:
    """The metrics ``m`` with the track's start altitude taken from a vertical silo's
    configured depth (exit altitude less stroke_m) when the metrics hold none (a run that
    did not fly), so the description keeps the depth the user set."""
    out = dict(m)
    if out.get("track_start_altitude_m") is None and replay.is_vertical(dict(assist)):
        stroke = run_data.finite(assist.get("stroke_m"))
        track = run_data.as_mapping(assist.get("track"))
        exit_m = run_data.finite(track.get("exit_altitude_m"))
        if stroke is not None:
            out["track_start_altitude_m"] = (0.0 if exit_m is None else exit_m) - stroke
    return out


def _app_line(metrics: Mapping[str, Any], config: Mapping[str, Any]) -> str:
    """``app_description`` without the outcome. A run that did not fly (NOT_FLOWN_STATUSES)
    is described from its config: the silo's configured depth (``_depth_from_config``),
    the ramp start it set (``configured_ramp_start``) and that no flight was recorded
    (NOT_FLOWN_IGNITION), never 'stage 1 never lit', which its metrics cannot say."""
    name = _launched_run(metrics)
    try:
        source = replay.run_source(dict(metrics), dict(config), name)
    except run_data.RunDataError:
        return f"{name}: not described in metrics.json"
    m = run_data.as_mapping(source["metrics"])
    run_cfg = run_data.as_mapping(source["config"])
    assist = replay.run_assist(run_cfg)
    status = m.get("status")
    if status in NOT_FLOWN_STATUSES:
        parts = [
            f"{name}: {replay.assist_text(dict(assist), _depth_from_config(m, assist))}",
            configured_ramp_start(run_cfg),
            NOT_FLOWN_IGNITION[status],
        ]
    else:
        parts = [
            f"{name}: {replay.assist_text(dict(assist), dict(m))}",
            replay.ignition_text(dict(m), replay.is_assisted(assist)),
        ]
    offload = run_data.as_mapping(metrics.get("offload"))
    case = next((run_data.as_mapping(c) for c in offload.get("cases") or []), None)
    if case is not None:
        parts.append(f"{case.get('name')}: {case_headline(case, offload)['text']}")
    else:
        parts.append(run_headline(name, source, metrics)["text"])
    return "; ".join(parts)


# ------------------------------------------------------------------ the run browser


def _sweep_points(run_dir: Path) -> int:
    """The number of sweep points (sweep_<n>/<point> folders, links skipped)."""
    count = 0
    for sweep in run_dir.iterdir():
        if sweep.name.startswith(SWEEP_DIR_PREFIX) and sweep.is_dir() and not is_link(sweep):
            count += sum(1 for p in sweep.iterdir() if p.is_dir() and not is_link(p))
    return count


def directory_row(
    run_dir: Path, experiment: str, timestamp: str, *, running: bool
) -> dict[str, Any]:
    """The run browser's row of one results directory (design 4.6 and 4.7; survey 07
    4.4; review 04 finding 9): experiment, timestamp, group, state (running, failed:
    FAILED.txt with its line; incomplete: neither summary.md nor FAILED.txt; complete;
    unreadable: a FAILED.txt or summary.md that is a link (never followed, so
    ``classify`` never reads through it), a metrics.json that is a link, over its cap, cut
    short or not an experiment's, or an app run's resolved_config.yaml that is a link,
    over its cap, cannot be parsed or holds a YAML anchor or alias, with fixed text naming
    the file only), whether it can be played and why not (one of REASONS: running,
    failed, incomplete, unreadable, 1-D, sweep, not planar,
    no run folder, no run with a time series), its label, git hash and state (unknown
    never clean; a sweep's from its baseline/metrics.json) with the server-start state of
    an app run, size (None while running: the directory is being written), run count,
    model, the outcome of a complete planar directory (``classify``'s kind and message:
    a flagged or failed-verification figure is never listed bare) and a one-line
    description. Reads metrics.json (capped), resolved_config.yaml for an app run
    (capped) and the first bytes of each series; writes nothing."""
    group = GROUP_APP if experiment == appform.APP_EXPERIMENT_NAME else GROUP_RECORDED
    row: dict[str, Any] = {
        "experiment": experiment,
        "timestamp": timestamp,
        "group": group,
        "state": DIR_COMPLETE,
        "playable": False,
        "reason": None,
        "line": None,
        "label": None,
        "git": {"hash": GIT_HASH_UNKNOWN, "state": "unknown"},
        "server_start": None,
        "size_bytes": None,
        "size_is_lower_bound": False,
        "run_count": 0,
        "model": None,
        "kind": None,
        "outcome": None,
        "description": "",
    }
    if running:
        row.update(state=DIR_RUNNING, reason=REASON_RUNNING, description="launch in progress")
        return row
    row["size_bytes"], row["size_is_lower_bound"] = tree_size(run_dir)
    marker = run_dir / results_io.FAILED_MARKER
    linked = [p.name for p in (marker, run_dir / SUMMARY_FILE) if is_link(p)]
    if linked:  # never followed: classify and failed_line would read the link's target
        verb = "is a link" if len(linked) == 1 else "are links"
        row.update(
            state=DIR_UNREADABLE, reason=REASON_UNREADABLE, line=f"{' and '.join(linked)} {verb}"
        )
        return row
    if marker.is_file():
        row.update(state=DIR_FAILED, reason=REASON_FAILED, line=failed_line(marker))
        row["description"] = f"failed: {row['line']}" if row["line"] else "failed"
        return row
    if not (run_dir / SUMMARY_FILE).is_file():
        row.update(state=DIR_INCOMPLETE, reason=REASON_INCOMPLETE, line=INCOMPLETE_LINE)
        row["description"] = "incomplete"
        return row
    metrics_path = run_dir / run_data.METRICS_FILE
    if not metrics_path.exists():
        if (run_dir / SWEEP_BASELINE_DIR).is_dir():
            points = _sweep_points(run_dir)
            row.update(kind="sweep", reason=REASON_SWEEP, run_count=points)
            row["description"] = f"{experiment}: a sweep of {points} points"
            try:  # each sweep records its git state in its baseline's metrics.json
                base = read_capped_json(
                    run_dir / SWEEP_BASELINE_DIR / run_data.METRICS_FILE, MAX_METRICS_BYTES
                )
            except (UnreadableError, OSError):  # the git state then stays unknown
                base = {}
            row["git"] = git_view(base.get("git"))
            return row
        row.update(state=DIR_UNREADABLE, reason=REASON_UNREADABLE, line="no metrics.json")
        return row
    try:
        metrics = read_capped_json(metrics_path, MAX_METRICS_BYTES)
    except UnreadableError as exc:
        # read_capped_json's text names the file only (never the local path)
        row.update(state=DIR_UNREADABLE, reason=REASON_UNREADABLE, line=str(exc)[:FAILED_LINE_MAX])
        return row
    if not isinstance(metrics.get("runs"), dict):
        row.update(
            state=DIR_UNREADABLE,
            reason=REASON_UNREADABLE,
            line="metrics.json lists no runs: not an experiment's results directory",
        )
        return row
    label = metrics.get("label")
    git = run_data.as_mapping(metrics.get("git"))
    start = git.get(summary.EXPLORATORY_SERVER_START_KEY)
    model = metrics.get("model") or VERTICAL_1D
    row.update(
        kind="experiment",
        label=None if label is None else str(label),
        git=git_view(git),
        server_start=git_view(start) if isinstance(start, Mapping) else None,
        model=str(model),
    )
    if model != PLANAR_2D:
        names = [p.name for p in run_dir.iterdir() if (p / run_data.SERIES_FILE).is_file()]
        row.update(
            run_count=len(names), reason=REASON_1D if model == VERTICAL_1D else REASON_NOT_PLANAR
        )
        row["description"] = f"{experiment}: {len(names)} runs, {row['reason']}"
        return row
    rows = run_folders(run_dir, metrics)
    row["run_count"] = len(rows)
    config: dict[str, Any] | None = None
    if replay.is_exploratory(metrics) and group == GROUP_APP:
        try:
            config = read_capped_yaml(run_dir / run_data.CONFIG_FILE, MAX_CONFIG_BYTES)
        except UnreadableError as exc:
            # read_capped_yaml's text names the file only (never the local path)
            row.update(
                state=DIR_UNREADABLE, reason=REASON_UNREADABLE, line=str(exc)[:FAILED_LINE_MAX]
            )
            return row
    if any(rows.values()):
        row["playable"] = True
    else:
        row["reason"] = REASON_NO_PLANAR_RUNS if rows else REASON_NO_RUN_FOLDERS
    kind, message, _ = classify(run_dir)
    row["outcome"] = {"kind": kind, "message": message}
    if config is not None:
        row["description"] = app_description(metrics, config, (kind, message))
    else:
        tag = "" if label is None else f" ({label})"
        row["description"] = f"{experiment}{tag}: {len(rows)} runs"
    return row


FINDINGS_DIR = PurePosixPath("docs") / "findings"
"""The repository folder of the findings notes (one per research question)."""
FINDINGS_NOTE_MAX_BYTES = 1024 * 1024
"""A findings note above this size [bytes] is not read for its citations."""
CITED_DIRECTORY_PATTERN = re.compile(
    r"results/([A-Za-z0-9][A-Za-z0-9_.+-]{0,127})/([0-9]{8}T[0-9]{6}Z(?:-[0-9]{1,4})?)"
)
"""A results directory as a findings note cites it: results/<experiment>/<timestamp>."""


def findings_citations(repo_root: Path) -> dict[tuple[str, str], list[dict[str, str]]]:
    """The findings notes that cite each results directory (the run browser's recorded
    rows say which note a directory rests on): every docs/findings/*.md of ``repo_root``
    (links and notes over FINDINGS_NOTE_MAX_BYTES skipped) read for
    CITED_DIRECTORY_PATTERN, as {(experiment, timestamp): [{path, title}]}, path relative
    to the repository, title the note's first '# ' heading (else its file name), each note
    once per directory, in file-name order. {} when the folder is missing."""
    folder = Path(repo_root, *FINDINGS_DIR.parts)
    out: dict[tuple[str, str], list[dict[str, str]]] = {}
    if not folder.is_dir() or is_link(folder):
        return out
    for note in sorted(folder.glob("*.md")):
        stat = _stat(note)
        if is_link(note) or not note.is_file() or stat is None:
            continue
        if stat[0] > FINDINGS_NOTE_MAX_BYTES:
            continue
        try:
            text = note.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), note.stem)
        record = {"path": str(FINDINGS_DIR / note.name), "title": title}
        for found in dict.fromkeys(CITED_DIRECTORY_PATTERN.findall(text)):
            out.setdefault(found, []).append(record)
    return out


def unreadable_row(experiment: str, timestamp: str, exc: BaseException) -> dict[str, Any]:
    """The row of a directory whose row could not be built (any error): unreadable, with
    the error's type only."""
    return {
        "experiment": experiment,
        "timestamp": timestamp,
        "group": GROUP_APP if experiment == appform.APP_EXPERIMENT_NAME else GROUP_RECORDED,
        "state": DIR_UNREADABLE,
        "playable": False,
        "reason": REASON_UNREADABLE,
        "line": f"the directory could not be read: {type(exc).__name__}",
        "label": None,
        "git": {"hash": GIT_HASH_UNKNOWN, "state": "unknown"},
        "server_start": None,
        "size_bytes": 0,
        "size_is_lower_bound": True,
        "run_count": 0,
        "model": None,
        "kind": None,
        "outcome": None,
        "description": "",
    }


def root_folders(root: Path) -> tuple[list[Path], int]:
    """(the experiment folders of a results root the browser lists, the number of other
    root entries): names results_io's rules accept (``valid_experiment_name``), no link or
    junction, a directory."""
    folders: list[Path] = []
    others = 0
    for exp_dir in sorted(root.iterdir(), key=lambda p: p.name):
        if not valid_experiment_name(exp_dir.name) or is_link(exp_dir) or not exp_dir.is_dir():
            others += 1
            continue
        folders.append(exp_dir)
    return folders, others


def folder_entries(exp_dir: Path, real_root: Path) -> tuple[list[tuple[str, Path]], int]:
    """((timestamp, path) of every results directory of one experiment folder, the number
    of other entries): names TIMESTAMP_PATTERN accepts, no link or junction, a directory
    resolving inside ``real_root``; a folder that cannot be listed counts as one other
    entry."""
    try:
        entries = sorted(exp_dir.iterdir(), key=lambda p: p.name)
    except OSError:
        return [], 1
    found: list[tuple[str, Path]] = []
    others = 0
    for run_dir in entries:
        if (
            not TIMESTAMP_PATTERN.fullmatch(run_dir.name)
            or is_link(run_dir)
            or not run_dir.is_dir()
            or not run_dir.resolve().is_relative_to(real_root)
        ):
            others += 1
            continue
        found.append((run_dir.name, run_dir))
    return found, others


def listed_directories(root: Path) -> tuple[list[tuple[str, str, Path]], int]:
    """((experiment, timestamp, path) of every results directory the browser lists,
    the number of other entries): ``root_folders`` and each folder's ``folder_entries``
    (the server keeps them per folder, ``AppServer.listing``)."""
    found: list[tuple[str, str, Path]] = []
    if not root.is_dir():
        return found, 0
    real = root.resolve()
    folders, others = root_folders(root)
    for exp_dir in folders:
        entries, n = folder_entries(exp_dir, real)
        others += n
        found += [(exp_dir.name, stamp, path) for stamp, path in entries]
    return found, others


class LruCache:
    """A small thread-safe least-recently-used cache."""

    def __init__(self, size: int) -> None:
        self._size = size
        self._items: OrderedDict[Any, Any] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: Any) -> Any:
        """The value of ``key`` (made the most recent), or None."""
        with self._lock:
            if key not in self._items:
                return None
            self._items.move_to_end(key)
            return self._items[key]

    def put(self, key: Any, value: Any) -> None:
        """Store ``value`` under ``key``, dropping the least recent beyond the size."""
        with self._lock:
            self._items[key] = value
            self._items.move_to_end(key)
            while len(self._items) > self._size:
                self._items.popitem(last=False)

    def keys(self) -> list[Any]:
        """The keys, least recent first."""
        with self._lock:
            return list(self._items)

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)


# ------------------------------------------------------------------ the job


@dataclass
class Job:
    """The one launch the server runs or last ran (mutable; the server's job lock guards
    every field): ``id`` (from 1 per server start), the form's ``description``,
    ``preset`` (the preset this launch is: the form equals that preset's, ``same_preset``;
    None when it was edited or names none), ``started_from_preset`` (the preset the
    request says the form started from, as sent), ``started_utc``, ``t0`` (monotonic),
    ``expected_s``, ``state``, ``stage``, ``pad_cached``, ``out_dir`` once made,
    ``t_end``, the ``outcome`` record, ``stopped`` (the server stopped it) and
    ``stop_reason`` (what FAILED.txt says then)."""

    id: int
    description: str
    preset: str | None
    started_from_preset: str | None
    started_utc: str
    t0: float
    expected_s: tuple[float, float] | None
    state: str = JOB_RUNNING
    stage: str = STAGE_PREFLIGHT
    pad_cached: bool | None = None
    out_dir: Path | None = None
    t_end: float | None = None
    outcome: dict[str, Any] | None = None
    stopped: bool = False
    stop_reason: str | None = None

    def snapshot(self, boot_id: str, now: float) -> dict[str, Any]:
        """The job as GET /api/job reports it (see ``idle_snapshot`` for the keys)."""
        elapsed = (self.t_end if self.t_end is not None else now) - self.t0
        expected = None if self.expected_s is None else list(self.expected_s)
        return {
            "boot_id": boot_id,
            "id": self.id,
            "state": self.state,
            "stage": self.stage,
            "stage_index": STAGES.index(self.stage) if self.stage in STAGES else None,
            "stages": list(STAGES),
            "started_utc": self.started_utc,
            "elapsed_s": round(elapsed, 1),
            "expected_s": expected,
            "longer_than_expected": (
                self.state == JOB_RUNNING and expected is not None and elapsed > expected[1]
            ),
            "pad_cached": self.pad_cached,
            "description": self.description,
            "preset": self.preset,
            "started_from_preset": self.started_from_preset,
            "preset_edited": self.started_from_preset is not None and self.preset is None,
            "directory": None
            if self.out_dir is None
            else {"experiment": self.out_dir.parent.name, "timestamp": self.out_dir.name},
            "outcome": self.outcome,
        }


def idle_snapshot(boot_id: str) -> dict[str, Any]:
    """GET /api/job before any launch: state idle and every other key null (false for
    the flags). The keys of a job (``Job.snapshot``): boot_id, id, state, stage,
    stage_index, stages, started_utc, elapsed_s, expected_s, longer_than_expected,
    pad_cached, description, preset (the preset this launch is, None when the form was
    edited from it), started_from_preset (the preset the request named), preset_edited,
    directory ({experiment, timestamp} once made) and outcome."""
    return {
        "boot_id": boot_id,
        "id": None,
        "state": JOB_IDLE,
        "stage": None,
        "stage_index": None,
        "stages": list(STAGES),
        "started_utc": None,
        "elapsed_s": None,
        "expected_s": None,
        "longer_than_expected": False,
        "pad_cached": None,
        "description": None,
        "preset": None,
        "started_from_preset": None,
        "preset_edited": False,
        "directory": None,
        "outcome": None,
    }


def same_preset(basis: appform.Basis, form: appform.Form) -> bool:
    """True when ``form`` names a preset and equals that preset's form on ``basis``
    (``appform.preset_form``; the dry-run flag aside): a launch the user did not edit after
    choosing the preset. False for an edited form, no preset, or a preset this basis
    cannot build."""
    if form.preset is None:
        return False
    try:
        preset = appform.preset_form(basis, form.preset)
    except (ValueError, KeyError):
        return False
    return dataclasses.replace(form, dry_run=False) == dataclasses.replace(preset, dry_run=False)


def outcome_record(outcome: LaunchOutcome) -> dict[str, Any]:
    """The job snapshot's outcome of a LaunchOutcome: kind, message, notes, reproduces
    and the refused field."""
    return {
        "kind": outcome.kind,
        "message": outcome.message,
        "notes": list(outcome.notes),
        "reproduces": list(outcome.reproduces),
        "field": outcome.field,
    }


# ------------------------------------------------------------------ the form's starting values

PAGE_ONLY_FIELDS = ("preset", "dry_run")
"""Request fields that are no form control (the page sets them)."""
RAMP_START_FALLBACKS: tuple[tuple[str, str], ...] = (
    ("at_depth_m", "depth_m"),
    ("at_speed_mps", "speed_mps"),
    ("at_height_m", "height_m"),
)
"""(form field, appform.derived ramp_start key) of the ramp-start ways no preset states:
the first preset whose own ramp start, converted by ``appform.derived``, has the value
(the speed only from a ramp start on the push, where the depth is set too, so it is a
speed on the push, never one of the coast after release)."""
FIXED_T_DECIMALS = 3
"""Decimals of an imposed offload's starting tonnes (to the kilogram)."""


def _default_order(presets: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """The presets with appform.DEFAULT_PRESET first, then in their order."""
    return sorted(presets, key=lambda p: p["name"] != appform.DEFAULT_PRESET)


def form_defaults(
    basis: appform.Basis,
    presets: Sequence[Mapping[str, Any]],
    ramp_starts: Mapping[str, Mapping[str, Any] | None],
) -> dict[str, Any]:
    """The value each form field starts from when the user turns to it (GET /api/form
    ``defaults``; step A5: the page's fields show their default and range), never a
    recommendation and never sent unless the field is used: a boolean false; a field of
    appform.OFFLOAD_OPTIONAL_FIELDS none (0 t or false: a stage-2 pre-offload, a penalty
    and a paired pad are each the user's choice; the presets that state them set them
    when chosen); any other field the value of the first preset that states it
    (``presets``: GET /api/form's records, appform.DEFAULT_PRESET first); a ramp-start way
    no preset states the first preset's own ramp start converted (RAMP_START_FALLBACKS,
    ``ramp_starts``: appform.derived's ramp_start by preset name); the startup ramp time
    the vehicle's own stage-1 ramp; else None (the page shows the field empty with its
    range)."""
    order = _default_order(presets)
    out: dict[str, Any] = {}
    for key, spec in appform.FIELDS.items():
        if key in PAGE_ONLY_FIELDS:
            continue
        if spec.kind == appform.BOOLEAN:
            out[key] = False
        elif key in appform.OFFLOAD_OPTIONAL_FIELDS:
            out[key] = 0
        else:
            out[key] = next((p["request"][key] for p in order if key in p["request"]), None)
    for key, derived_key in RAMP_START_FALLBACKS:
        if out.get(key) is not None:
            continue
        found = _ramp_fallback(order, ramp_starts, derived_key)
        if found is not None:
            out[key] = found[0]
    if out.get("t_ramp_s") is None:
        startup = basis.committed_runs[basis.baseline_name].to_vehicle().stages[0].startup
        if startup.effective_kind == appform.STARTUP_RAMP:
            out["t_ramp_s"] = float(startup.t_ramp_s)
    return out


def _ramp_fallback(
    order: Sequence[Mapping[str, Any]],
    ramp_starts: Mapping[str, Mapping[str, Any] | None],
    derived_key: str,
) -> tuple[float, str, Mapping[str, Any]] | None:
    """(value, preset name, that preset's converted ramp start) of the first preset in
    ``order`` whose own ramp start, converted by ``appform.derived``, has ``derived_key``
    (a speed only from a ramp start on the push, where the depth is set too), or None."""
    for preset in order:
        start = ramp_starts.get(str(preset["name"])) or {}
        value = start.get(derived_key)
        if value is None or (derived_key == "speed_mps" and start.get("depth_m") is None):
            continue
        return float(value), str(preset["name"]), start
    return None


def form_default_sources(
    presets: Sequence[Mapping[str, Any]],
    ramp_starts: Mapping[str, Mapping[str, Any] | None],
) -> dict[str, dict[str, Any]]:
    """Where each ramp-start default that no preset states comes from (GET /api/form
    ``default_sources``; the page names it beside the default, so 94.574441 m reads as
    silo_hot_ramp_on_track's ramp start stated as a depth): {field: {preset,
    time_after_release_s}} for the fields of RAMP_START_FALLBACKS that ``form_defaults``
    fills from a preset's converted ramp start (``_ramp_fallback``)."""
    order = _default_order(presets)
    out: dict[str, dict[str, Any]] = {}
    for key, derived_key in RAMP_START_FALLBACKS:
        if any(key in p["request"] for p in order):
            continue
        found = _ramp_fallback(order, ramp_starts, derived_key)
        if found is not None:
            out[key] = {
                "preset": found[1],
                "time_after_release_s": run_data.finite(found[2].get("time_after_release_s")),
            }
    return out


def push_start_default(
    presets: Sequence[Mapping[str, Any]],
    ramp_starts: Mapping[str, Mapping[str, Any] | None],
) -> dict[str, Any] | None:
    """The default of a ramp start stated as a time from push start (GET /api/form
    ``push_start_default``; review of A5): the field t_ign_s is shared with the time from
    release, whose default (+0.5 s) read from push start would be a hot start on the
    track, so the page shows this one instead: {value [s], preset, time_after_release_s}
    of the first preset (the default first) whose own ramp start converts to a time from
    push start (``appform.derived``), or None."""
    found = _ramp_fallback(_default_order(presets), ramp_starts, "time_from_push_start_s")
    if found is None:
        return None
    return {
        "value": found[0],
        "preset": found[1],
        "time_after_release_s": run_data.finite(found[2].get("time_after_release_s")),
    }


def vehicle_startup(basis: appform.Basis) -> dict[str, Any]:
    """The baseline vehicle's own stage-1 startup (GET /api/form ``vehicle_startup``; the
    page says what the startup choice 'the vehicle's own' is): its effective kind, the
    ramp time [s] of a ramp, the time constant [s] of a lag (else None) and the vehicle
    file."""
    startup = basis.committed_runs[basis.baseline_name].to_vehicle().stages[0].startup
    kind = startup.effective_kind
    return {
        "kind": kind,
        "t_ramp_s": float(startup.t_ramp_s) if kind == appform.STARTUP_RAMP else None,
        "tau_s": float(startup.tau_s) if kind == appform.STARTUP_LAG else None,
        "vehicle": basis.vehicle_path,
    }


REPOSITORY_RESULTS = run_data.RESULTS_TREE_NAME
"""The repository's own results folder (relative to the repository): app runs written
there keep their summary.md tracked and public (D-SP2-03, D-SP2-37)."""


def results_root_view(results_root: Path, repo_root: Path) -> dict[str, Any]:
    """Where the server writes launches, for the page (GET /api/form ``results_root``):
    ``path``, the results root relative to the repository (POSIX) when it is inside it,
    else None (a folder outside the repository: the page says so and names no local
    path); ``tracked``, True for the repository's own results folder
    (REPOSITORY_RESULTS)."""
    try:
        rel = Path(results_root).resolve().relative_to(Path(repo_root).resolve())
    except (OSError, ValueError):
        return {"path": None, "tracked": False}
    path = rel.as_posix()
    return {"path": path, "tracked": path == REPOSITORY_RESULTS}


def fixed_defaults(
    basis: appform.Basis, presets: Sequence[Mapping[str, Any]]
) -> dict[str, float | None]:
    """The starting value of an imposed offload for each way of stating it (GET
    /api/form ``fixed_defaults``; the page puts it in the field when the key changes
    between a fraction and tonnes): the first preset's imposed fraction (SP1's 5% case)
    for a fraction key, and the same fraction of the stage's full load in tonnes
    (vehicle.offload_load_kg of the baseline's vehicle, to FIXED_T_DECIMALS) for a tonnes
    key; all None when no preset imposes a fraction."""
    fraction = next(
        (
            float(p["request"]["fixed_value"])
            for p in _default_order(presets)
            if "fraction" in str(p["request"].get("fixed_key", ""))
        ),
        None,
    )
    vehicle = basis.committed_runs[basis.baseline_name].to_vehicle()
    out: dict[str, float | None] = {}
    for key in appform.FIXED_KEYS:
        if fraction is None:
            out[key] = None
        elif "fraction" in key:
            out[key] = fraction
        else:
            load_t = float(kg_to_t(offload_load_kg(vehicle, OFFLOAD_FIXED_MODES[key])))
            out[key] = round(fraction * load_t, FIXED_T_DECIMALS)
    return out


def offload_loads_t(basis: appform.Basis) -> dict[str, float]:
    """The full propellant load [t] of each offload mode's tanks (vehicle.offload_load_kg
    of the baseline's vehicle; GET /api/form ``loads_t``): the page states an imposed
    offload in tonnes, and a stage-2 pre-offload, against it (appform refuses a mass at or
    beyond the load)."""
    vehicle = basis.committed_runs[basis.baseline_name].to_vehicle()
    modes = dict.fromkeys(OFFLOAD_FIXED_MODES.values())
    return {mode: float(kg_to_t(offload_load_kg(vehicle, mode))) for mode in modes}


def silo_fixed(basis: appform.Basis) -> list[dict[str, Any]]:
    """The silo details the form shows read-only (design 4.7: the brake, the drive
    efficiency, the vented shaft, the vertical track): every key of the committed silo's
    assist block (appform.SILO_FRAGMENT_VARIANT) the form does not edit, as {key,
    config_key, value}, values as committed."""
    edited = {*appform.PUSH_KEYS, *appform.SILO_FIELDS, "model"}
    return [
        {"key": key, "config_key": f"assist.{key}", "value": plain(value)}
        for key, value in basis.silo_assist.items()
        if key not in edited
    ]


# ------------------------------------------------------------------ pages


def load_app_template() -> str:
    """templates/app.html (package data), as text (UTF-8; the template is ASCII)."""
    path = resources.files("launchsim").joinpath(*APP_TEMPLATE)
    return path.read_bytes().decode("utf-8")


def script_source(page: str) -> str:
    """The CSP source of a page's one inline script: 'sha256-<base64 digest>'. Raises
    RuntimeError unless the page has exactly one."""
    scripts = INLINE_SCRIPT_PATTERN.findall(page)
    if len(scripts) != 1:
        raise RuntimeError("a page must hold exactly one inline script")
    digest = hashlib.sha256(scripts[0].encode("utf-8")).digest()
    return "sha256-" + base64.b64encode(digest).decode("ascii")


def render_app_page(data: Mapping[str, Any]) -> tuple[bytes, str]:
    """(the app page with its one APP_DATA_TOKEN replaced by ``data`` as JSON with '<'
    escaped (replay.embed_json), its Content-Security-Policy header with the page's
    script by sha256). Raises RuntimeError for a template without exactly one token."""
    template = load_app_template()
    if template.count(APP_DATA_TOKEN) != 1:
        raise RuntimeError(f"app template must hold {APP_DATA_TOKEN} exactly once")
    page = template.replace(APP_DATA_TOKEN, replay.embed_json(dict(data)))
    return page.encode("utf-8"), APP_CSP_TEMPLATE.format(script=script_source(page))


def scene_header_csp() -> str:
    """The Content-Security-Policy header of a served scene page: the page's own meta
    policy (scene.load_template) with SCENE_FRAME_ANCESTORS added."""
    found = CSP_META_PATTERN.findall(scene.load_template())
    if len(found) != 1:
        raise RuntimeError("the scene template must hold one meta Content-Security-Policy")
    return f"{found[0].rstrip('; ')}; {SCENE_FRAME_ANCESTORS}"


# ------------------------------------------------------------------ the server

Runner = Callable[..., LaunchOutcome]
"""A launch function with run_launch's signature (tests pass a stub)."""
STOPPING_MESSAGE = "the app server is stopping; no launch starts now"
"""The 503 of a launch request that arrives once the server has begun to stop."""
VIDEO_BUSY_MESSAGE = "a video is being saved; a launch and a video never run together"
LAUNCH_RUNNING_MESSAGE = "a launch is running; a launch and a video never run together"
"""The 409s of a launch during a video and of a video during a launch (step A6v)."""
VIDEO_LEFTOVER_ERROR = "VideoLeftover"
"""What ``AppServer.last_error`` takes when a video session reports something it left
behind (its temporary folder, an encoder process that did not end); the line itself is
``AppServer.video_leftover`` and the session's record carries it (fix round 2)."""


def video_footer(
    run_dir: Path, names: Sequence[str], metrics: Mapping[str, Any], config: Mapping[str, Any]
) -> list[str]:
    """The caveat footer of every frame of a video of ``names`` (design 4.8; honesty
    review 02 finding 9): the three lines of plots.animation_caveats for the shown runs
    (the model and its sweep-optimized guidance; unthrottled, no sized structural mass for
    the runs' own peak push load and, when a shown run is a penalty row, that it charges an
    assumed stage-1 dry mass (fix round 2); the vehicle's calibration and the replay
    disclaimer), with the exploratory line first for a directory labelled exploratory. The
    display-only caveat of design 4.8 is the scene page's own footer line
    (scene.FOOTER_TEXT), which the page puts on every captured frame before these lines
    (frameFooterLines), so it is not repeated here (D-SP2-23: one source per caveat; fix
    round 1); the page also adds each shown pushed run's own structural line. The vehicle
    is the directory's own
    (resolved_config.yaml's top vehicle block, as the scene names it). Raises
    plots.AnimationError for a run without a planar time series."""
    runs = [plots.read_animation_run(run_dir, n, dict(metrics)) for n in names]
    vehicle = str(run_data.as_mapping(config.get("vehicle")).get("name", "unknown vehicle"))
    label = metrics.get("label")
    return list(plots.animation_caveats(runs, vehicle, None if label is None else str(label)))


def _refused_from(exc: video.VideoError) -> Refused:
    """A video module refusal as the server's Refused (status, code and message kept)."""
    return Refused(HTTPStatus(exc.status), exc.code, exc.message)


def port_unavailable(exc: OSError) -> bool:
    """True when a bind failed because the port is in use or reserved."""
    winerror = getattr(exc, "winerror", None)
    return exc.errno in PORT_UNAVAILABLE_ERRNOS or winerror in WINDOWS_PORT_UNAVAILABLE


def probe_port(port: int) -> None:
    """Raise the bind's OSError when another socket holds ``port`` where the app's bind
    of 127.0.0.1 would not notice it (D-SP2-29: a busy port is an error, never shared):
    for each of PROBE_ADDRESSES a throwaway socket is bound (never listened on) with
    SO_EXCLUSIVEADDRUSE where the platform has it, then closed. Only an in-use or reserved
    error counts (``port_unavailable``); any other (no IPv6 on this machine) is
    ignored."""
    exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
    for family, host in PROBE_ADDRESSES:
        try:
            probe = socket.socket(family, socket.SOCK_STREAM)
        except OSError:
            continue
        with probe:
            try:
                if exclusive is not None:
                    probe.setsockopt(socket.SOL_SOCKET, exclusive, 1)
                probe.bind((host, port))
            except OSError as exc:
                if port_unavailable(exc):
                    raise


class AppServer(http.server.ThreadingHTTPServer):
    """The local app's server (design 4.6): IPv4, bound to BIND_HOST and the given port
    only (0: a free port), with no address reuse and, on Windows, SO_EXCLUSIVEADDRUSE, so
    a second server on a busy port fails with OSError, as does a fixed port another
    socket holds on the IPv4 wildcard or the IPv6 loopback (``probe_port``); daemon
    handler threads; no reverse lookup at bind. It owns everything a request reads: the
    basis, the server-start record, the BaselineCache, the one job slot, the listing, row,
    panel and scene caches, the boot id, and ``sp1_same`` (``sp1_files_same``, checked
    once at start: whether the basis files are SP1's; a directory's own basis commit is
    checked once per commit, ``sp1_same_at``). Once it begins to stop
    (``stop_active_job`` or ``close``) no launch starts (503). Use it as a context manager
    (exit: ``close``, after ``stop_active_job`` when the block raised)."""

    address_family = socket.AF_INET
    allow_reuse_address = False
    daemon_threads = True

    def __init__(
        self,
        *,
        port: int,
        basis: appform.Basis,
        server_start: ServerStart,
        results_root: Path,
        repo_root: Path,
        display_dir: Path,
        runner: Runner | None = None,
        cache: BaselineCache | None = None,
        encoder: video.Encoder | None = None,
        video_reason: str = "",
        work_dir: Path | None = None,
        video_limits: video.Limits = video.DEFAULT_LIMITS,
    ) -> None:
        self.basis = basis
        self.server_start = server_start
        self.results_root = Path(results_root)
        self.repo_root = Path(repo_root)
        self.display_dir = Path(display_dir)
        self.cache = BaselineCache() if cache is None else cache
        self.runner: Runner = run_launch if runner is None else runner
        # the MP4 export (step A6v): the encoder cli.py resolved (None: not found, with the
        # reason), where videos go (the working directory at start) and the session limits
        self.encoder = encoder
        self.work_dir = Path.cwd() if work_dir is None else Path(work_dir)
        self.video_limits = video_limits
        folder = video.folder_reason(self.work_dir, self.results_root)
        if encoder is None:
            self.video_reason = video_reason or "ffmpeg not found"
        else:
            self.video_reason = folder or ""
        self._video: video.VideoSession | None = None
        self._video_last: video.VideoSession | None = None
        self._video_lock = threading.Lock()
        self.video_leftover: str | None = None
        self.boot_id = secrets.token_hex(BOOT_ID_BYTES)
        self.sp1_same = sp1_files_same(self.repo_root, basis)
        self._sp1_same_by_commit: dict[str, bool | None] = {}
        if basis.commit is not None:
            self._sp1_same_by_commit[basis.commit] = self.sp1_same
        self._sp1_lock = threading.Lock()
        self.last_error: str | None = None
        self._job: Job | None = None
        self._job_lock = threading.Lock()
        self._start_lock = threading.Lock()
        self._next_id = 1
        self._worker: threading.Thread | None = None
        self._stopping = False
        self._closed = False
        self.stopped_dir: Path | None = None
        self._rows: dict[str, tuple[tuple[Any, ...], dict[str, Any]]] = {}
        self._rows_lock = threading.Lock()
        self._listing_lock = threading.Lock()
        self._root_listing: tuple[Any, list[Path], int, Path] | None = None
        self._folder_listings: dict[str, tuple[Any, list[tuple[str, Path]], int]] = {}
        self._panels = LruCache(PANEL_LRU_SIZE)
        self._panel_lock = threading.Lock()
        self._scenes = LruCache(SCENE_LRU_SIZE)
        self._scene_lock = threading.Lock()
        self._form_info: dict[str, Any] | None = None
        self._form_lock = threading.Lock()
        self._pages: dict[bool, tuple[bytes, str]] = {}
        self._scene_csp: str | None = None
        self._serve_started = threading.Event()
        self._serve_done = threading.Event()
        super().__init__((BIND_HOST, port), AppHandler)

    # ---------------------------------------------------------- socket and lifetime

    def server_bind(self) -> None:
        """Bind exclusively (Windows: SO_EXCLUSIVEADDRUSE before bind), a fixed port only
        after ``probe_port`` found it free, without the standard library's
        socket.getfqdn reverse lookup."""
        if self.server_address[1] != 0:
            probe_port(int(self.server_address[1]))
        exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
        if exclusive is not None:
            self.socket.setsockopt(socket.SOL_SOCKET, exclusive, 1)
        socketserver.TCPServer.server_bind(self)
        self.server_name = BIND_HOST
        self.server_port = self.server_address[1]

    @property
    def port(self) -> int:
        """The bound port."""
        return int(self.server_address[1])

    @property
    def url(self) -> str:
        """http://127.0.0.1:<port>/ (the address printed and shown)."""
        return f"http://{BIND_HOST}:{self.port}/"

    def serve_forever(self, poll_interval: float = SERVE_POLL_S) -> None:
        """socketserver's serve_forever, recording that it runs (``close`` shuts it down
        only then)."""
        self._serve_started.set()
        try:
            super().serve_forever(poll_interval)
        finally:
            self._serve_done.set()

    def wait_serving(self, timeout: float) -> bool:
        """True once serve_forever has started (within ``timeout`` [s])."""
        return self._serve_started.wait(timeout)

    def handle_error(self, request: Any, client_address: Any) -> None:
        """An exception escaping a handler (a client that went away, say): recorded in
        ``last_error`` (type only), never printed."""
        exc = sys.exc_info()[1]
        self.last_error = None if exc is None else type(exc).__name__

    def begin_stopping(self) -> None:
        """Refuse every later launch (``start_launch`` answers 503 'stopping'). Taken under
        the start lock: a launch whose check-and-start is under way finishes starting
        first and is then a running job like any other."""
        with self._start_lock:
            self._stopping = True

    def close(self) -> None:
        """Once (a second call returns at once): refuse later launches
        (``begin_stopping``), shut serve_forever down from a helper thread when it runs
        (shutdown() from the serving thread would deadlock), close the socket, close an
        open video session (the encoder killed, its temporary folder removed, nothing kept),
        then join the launch worker for WORKER_JOIN_TIMEOUT_S (a daemon thread: a stopped
        process abandons it)."""
        with self._start_lock:
            self._stopping = True
            if self._closed:
                return
            self._closed = True
        if self._serve_started.is_set() and not self._serve_done.is_set():
            stopper = threading.Thread(target=self.shutdown, name="launchsim-app-shutdown")
            stopper.start()
            stopper.join(SHUTDOWN_TIMEOUT_S)
        self.server_close()
        with self._video_lock:
            session = self._video
        if session is not None:
            session.close()
        worker = self._worker
        if worker is not None:
            worker.join(WORKER_JOIN_TIMEOUT_S)

    def __enter__(self) -> AppServer:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, *args: object) -> None:
        """``close``; when the block ends by an exception (serve_forever's select failing,
        say), first ``stop_active_job``, so a running launch is marked FAILED, never left
        to read as incomplete."""
        try:
            if exc_type is not None:
                self.stop_active_job()
        finally:
            self.close()

    # ---------------------------------------------------------- the job

    def job_snapshot(self) -> dict[str, Any]:
        """GET /api/job: the current or last job (``Job.snapshot``), or ``idle_snapshot``."""
        with self._job_lock:
            job = self._job
            if job is None:
                return idle_snapshot(self.boot_id)
            return job.snapshot(self.boot_id, time.monotonic())

    def running_directory(self) -> tuple[str, str] | None:
        """(experiment, timestamp) of the running launch's directory once made, else None."""
        with self._job_lock:
            job = self._job
            if job is None or job.state != JOB_RUNNING or job.out_dir is None:
                return None
            return job.out_dir.parent.name, job.out_dir.name

    def start_launch(self, form: appform.Form) -> tuple[HTTPStatus, dict[str, Any]]:
        """Check and start one launch atomically (one lock): 503 'stopping' once the
        server has begun to stop (nothing checked, nothing started: a request whose body
        was still arriving when Ctrl+C came); 409 'busy' with the running job; 409
        'video_busy' while a video session is open (a launch and a video never run
        together, step A6v); 422 'refused' with the field and one line (``preflight``:
        nothing written); 409 'code_changed' (``code_changed`` True); else 202 with the new
        job, which a daemon worker thread runs (``_work``)."""
        with self._start_lock:
            if self._stopping:
                return HTTPStatus.SERVICE_UNAVAILABLE, {
                    "error": "stopping",
                    "message": STOPPING_MESSAGE,
                }
            with self._job_lock:
                busy = self._job is not None and self._job.state == JOB_RUNNING
            if busy:
                return HTTPStatus.CONFLICT, {
                    "error": "busy",
                    "message": "a launch is already running; one launch at a time",
                    "job": self.job_snapshot(),
                }
            if self.video_busy():
                return HTTPStatus.CONFLICT, {
                    "error": "video_busy",
                    "message": VIDEO_BUSY_MESSAGE,
                }
            resolved, refused = preflight(self.basis, form)
            if refused is not None:
                return HTTPStatus.UNPROCESSABLE_ENTITY, {
                    "error": "refused",
                    "field": refused.field,
                    "message": refused.message,
                }
            assert resolved is not None
            if code_changed(self.repo_root, self.server_start) is True:
                return HTTPStatus.CONFLICT, {
                    "error": "code_changed",
                    "message": CODE_CHANGED_MESSAGE,
                }
            cached = self.cache.has(resolved.baseline, self.server_start)
            lo, hi = appform.derived(resolved, pad_cached=cached)["expected_s"]
            job = Job(
                id=self._next_id,
                description=appform.describe(form),
                preset=form.preset if same_preset(self.basis, form) else None,
                started_from_preset=form.preset,
                started_utc=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                t0=time.monotonic(),
                expected_s=(lo, hi),
                pad_cached=cached,
            )
            self._next_id += 1
            worker = threading.Thread(
                target=self._work, args=(job, form), name=f"launchsim-launch-{job.id}", daemon=True
            )
            with self._job_lock:
                self._job = job
                self._worker = worker
            worker.start()
            return HTTPStatus.ACCEPTED, {"job": self.job_snapshot()}

    def _progress(self, job: Job, stage: str, info: dict[str, Any]) -> None:
        """run_launch's progress callback: the stage, the expected range, whether the pad
        is cached and the directory once made. After a stop (``stop_active_job``) the job
        is not updated; a directory made after the stop (the launch was still in its
        preflight then) is marked FAILED at once (``_mark_stopped``), so a stop in the
        first moments of a launch leaves FAILED.txt too; and a stopped launch reporting
        STOP_ABORT_STAGES (the comparison or the writing) raises LaunchInterrupted with the
        stop's reason, a BaseException that run_launch's progress wrapper does not swallow:
        run_launch then writes FAILED.txt with that reason and returns before
        ``write_run``, so a stop never leaves a complete summary.md beside FAILED.txt."""
        late: Path | None = None
        abort = False
        with self._job_lock:
            if job.stopped:
                abort = stage in STOP_ABORT_STAGES
                if info.get("out_dir") is not None and job.out_dir is None:
                    job.out_dir = late = Path(info["out_dir"])
            else:
                job.stage = stage
                expected = info.get("expected_s")
                if expected is not None:
                    job.expected_s = (float(expected[0]), float(expected[1]))
                if "cached" in info:
                    job.pad_cached = bool(info["cached"])
                if info.get("out_dir") is not None:
                    job.out_dir = Path(info["out_dir"])
            reason = job.stop_reason
        if late is not None:
            self._mark_stopped(job, late)
        if abort:
            raise LaunchInterrupted(reason)

    def _mark_crashed(self, job: Job, exc: BaseException) -> str:
        """FAILED.txt for a launch that raised, in its directory when one exists without
        summary.md or a marker; the marker's own reason ('' when there is none)."""
        with self._job_lock:
            out_dir = job.out_dir
        if out_dir is None:
            return ""
        marker = out_dir / results_io.FAILED_MARKER
        if out_dir.is_dir() and not (out_dir / SUMMARY_FILE).exists() and not marker.exists():
            results_io.write_failure_marker(out_dir, exc)
        return failed_line(marker) if marker.is_file() else ""

    def _work(self, job: Job, form: appform.Form) -> None:
        """The worker thread: run the launch; any exception (BaseException: nothing above
        a thread catches it) writes FAILED.txt into its directory when one exists without
        summary.md or a marker (``_mark_crashed``; a failure there is swallowed) and, in a
        finally, marks the job failed, so the slot always leaves JOB_RUNNING. Never prints
        and never lets an exception reach threading.excepthook."""
        try:
            outcome = self.runner(
                self.basis,
                form,
                results_root=self.results_root,
                repo_root=self.repo_root,
                cache=self.cache,
                server_start=self.server_start,
                progress=lambda stage, info: self._progress(job, stage, info),
            )
        except BaseException as exc:  # a thread has no caller to re-raise to
            line = ""
            try:
                # the marker's own reason, so the job and the directory read later agree
                line = self._mark_crashed(job, exc)
            except Exception:  # a locked or vanished directory: the job still ends
                line = ""
            finally:
                try:
                    message = line or _exception_line(exc)
                except Exception:  # an exception whose text cannot be made
                    message = type(exc).__name__
                with self._job_lock:
                    if not job.stopped:
                        job.state = JOB_FAILED
                        job.t_end = time.monotonic()
                        job.outcome = {
                            "kind": OUTCOME_CRASHED,
                            "message": message,
                            "notes": [],
                            "reproduces": [],
                            "field": None,
                        }
            return
        with self._job_lock:
            if job.stopped:
                return
            if outcome.out_dir is not None:
                job.out_dir = Path(outcome.out_dir)
            job.state = JOB_FAILED if outcome.kind in FAILED_OUTCOMES else JOB_DONE
            job.t_end = time.monotonic()
            job.outcome = outcome_record(outcome)

    def stop_active_job(self) -> Path | None:
        """Stop handling of the running launch (Ctrl+C or Ctrl+Break on the console):
        first refuse every later launch (``begin_stopping``); wait up to
        STOP_WRITING_GRACE_S for a launch in its writing stage; then, if it still runs,
        mark the job failed and write FAILED.txt (LaunchInterrupted with the stage and the
        elapsed time) into its directory unless that holds summary.md or a marker already
        (``_mark_stopped``). A launch still in its preflight has no directory yet: the
        worker marks the one it makes after the stop (``_progress``). The stopped worker
        itself is interrupted at its next comparison or writing stage (``_progress``), so
        it writes nothing more. Returns the directory marked now, or None."""
        self.begin_stopping()
        with self._job_lock:
            job = self._job
            if job is None or job.state != JOB_RUNNING:
                return None
            writing = job.stage == STAGE_WRITING
        worker = self._worker
        if writing and worker is not None:
            worker.join(STOP_WRITING_GRACE_S)
        with self._job_lock:
            if job.state != JOB_RUNNING:
                return None
            now = time.monotonic()
            reason = (
                f"the app server was stopped while launch {job.id} was running: stage "
                f"{job.stage}, {now - job.t0:.0f} s"
            )
            job.stopped = True
            job.stop_reason = reason
            job.state = JOB_FAILED
            job.t_end = now
            job.outcome = {
                "kind": OUTCOME_CRASHED,
                "message": f"{LaunchInterrupted.__name__}: {reason}",
                "notes": [],
                "reproduces": [],
                "field": None,
            }
            out_dir = job.out_dir
        if out_dir is None:
            return None
        return self._mark_stopped(job, out_dir)

    def _mark_stopped(self, job: Job, out_dir: Path) -> Path | None:
        """FAILED.txt (LaunchInterrupted with ``job.stop_reason``) in a stopped launch's
        directory unless it is gone or holds summary.md; a marker already there is kept
        (the worker's own, when the stopped launch reached its comparison or writing stage
        before this ran, with the same reason; or a crash's). The job's message becomes
        the marker's own reason and ``stopped_dir`` the directory. Returns the directory
        marked, or None (an OSError included: a stop never raises here)."""
        try:
            if not out_dir.is_dir() or (out_dir / SUMMARY_FILE).exists():
                return None
            marker = out_dir / results_io.FAILED_MARKER
            if not marker.exists():
                results_io.write_failure_marker(out_dir, LaunchInterrupted(job.stop_reason))
            if not marker.is_file():
                return None
            line = failed_line(marker)
        except OSError:
            return None
        with self._job_lock:
            if line:  # the marker's own reason, so the job and the directory agree
                job.outcome = {**(job.outcome or {}), "message": line}
            self.stopped_dir = out_dir
        return out_dir

    # ---------------------------------------------------------- routes' data

    def form_info(self) -> dict[str, Any]:
        """GET /api/form (built once): the presets (name, kind, label, the committed name
        when the basis was read from a commit, the expected range and its note, the form
        as a request), presets this basis cannot resolve with the reason, the default
        preset, every field with its kind, label, unit, config key, choices and range, each
        field's starting value (``form_defaults``; the preset a converted ramp-start
        default comes from, ``form_default_sources``; the time-from-push-start default,
        ``push_start_default``) and each imposed-offload key's
        (``fixed_defaults``), the vehicle's own stage-1 startup (``vehicle_startup``),
        where launches are written (``results_root_view``), each offload mode's full load
        in tonnes
        (``offload_loads_t``), the silo details shown read-only (``silo_fixed``), the
        Advanced forms with their readings, the required choices, the limits, the
        server-start record, the boot id, SP1's headline with its caveat groups, the
        exploratory line and the launch note."""
        with self._form_lock:
            if self._form_info is None:
                self._form_info = self._build_form_info()
            return self._form_info

    def _build_form_info(self) -> dict[str, Any]:
        """Build the GET /api/form record (see ``form_info``)."""
        presets: list[dict[str, Any]] = []
        unavailable: list[dict[str, str]] = []
        ramp_starts: dict[str, Any] = {}
        for name, kind in appform.PRESETS:
            try:
                form = appform.preset_form(self.basis, name)
                exp = appform.build_experiment(self.basis, form)
                values = appform.derived(resolve_experiment(exp, self.basis.vehicle_copy()))
            except (ValueError, KeyError) as exc:
                unavailable.append({"name": name, "reason": _exception_line(exc)})
                continue
            ramp_starts[name] = values["ramp_start"]
            presets.append(
                {
                    "name": name,
                    "kind": kind,
                    "label": appform.describe(form),
                    "committed_name": name if self.basis.commit is not None else None,
                    "expected_s": values["expected_s"],
                    "expected_note": values["expected_note"],
                    "request": appform.form_to_request(form),
                }
            )
        fields = [
            {
                "key": key,
                "kind": spec.kind,
                "label": spec.label,
                "unit": spec.unit,
                "config_key": spec.config_key,
                "choices": list(spec.choices),
                "lo": spec.lo,
                "hi": spec.hi,
            }
            for key, spec in appform.FIELDS.items()
        ]
        start = self.server_start.record()
        return {
            "boot_id": self.boot_id,
            "version": __version__,
            "server_start": {
                **start,
                "state": tree_state(start.get("dirty"), start.get("hash")),
                "code_check": self.server_start.head is not None,
            },
            "basis_commit": self.basis.commit,
            "presets": presets,
            "presets_unavailable": unavailable,
            "default_preset": appform.DEFAULT_PRESET,
            "fields": fields,
            "defaults": plain(form_defaults(self.basis, presets, ramp_starts)),
            "default_sources": plain(form_default_sources(presets, ramp_starts)),
            "push_start_default": plain(push_start_default(presets, ramp_starts)),
            "vehicle_startup": vehicle_startup(self.basis),
            "results_root": results_root_view(self.results_root, self.repo_root),
            "fixed_defaults": fixed_defaults(self.basis, presets),
            "loads_t": offload_loads_t(self.basis),
            "silo_fixed": silo_fixed(self.basis),
            "advanced": {
                "solve_modes": list(appform.ADVANCED_SOLVE_MODES),
                "fixed_keys": list(appform.ADVANCED_FIXED_KEYS),
                "solve_reading": appform.ADVANCED_SOLVE_READING,
                "fixed_reading": appform.ADVANCED_FIXED_READING,
            },
            "required_choices": list(appform.REQUIRED_CHOICES),
            "limits": {
                "max_body_bytes": MAX_JSON_BODY_BYTES,
                "max_refusal_chars": appform.MAX_REFUSAL_CHARS,
                "max_scene_runs": run_data.MAX_RUNS,
            },
            "headline": SP1_HEADLINE.record(),
            "exploratory_caveat": replay.EXPLORATORY_CAVEAT,
            "launch_note": LAUNCH_NOTE,
            "video": self.video_info(),
        }

    def video_info(self) -> dict[str, Any]:
        """GET /api/form ``video`` (step A6v): whether the MP4 export is available and,
        when not, the reason (ffmpeg not found, or the working directory inside a results
        tree); the format, the frame rates and widths offered with their defaults and the
        height per width, the frame and byte limits, the folder videos are written to (the
        server's working directory, absolute) and the encoder's path."""
        limits = self.video_limits
        return {
            "available": self.video_reason == "",
            "reason": self.video_reason,
            "format": video.FORMAT_MP4,
            "fps_choices": list(video.FPS_CHOICES),
            "default_fps": video.DEFAULT_FPS,
            "widths": list(video.WIDTH_CHOICES),
            "default_width": video.DEFAULT_WIDTH,
            "sizes": [[w, video.frame_height(w)] for w in video.WIDTH_CHOICES],
            "max_runs": VIDEO_RUNS,
            "max_frames": limits.max_frames,
            "max_frame_bytes": limits.max_frame_bytes,
            "byte_budget": limits.byte_budget,
            "folder": str(self.work_dir),
            "encoder": None if self.encoder is None else self.encoder.display,
        }

    # ---------------------------------------------------------- the video session

    def video_busy(self) -> bool:
        """True while a video session holds the slot (capturing or finishing)."""
        with self._video_lock:
            session = self._video
        return session is not None and session.is_open

    def _video_report(self, text: str) -> None:
        """A video session left something behind (its temporary folder, an encoder process
        that did not end): ``last_error`` takes VIDEO_LEFTOVER_ERROR and ``video_leftover``
        the line (fix round 2; the session's record carries it too)."""
        self.last_error = VIDEO_LEFTOVER_ERROR
        self.video_leftover = text

    def video_session(self, token: str) -> video.VideoSession:
        """The session ``token`` names: the current one, or the last ended one, which is
        kept beside it (fix round 3: a page polling a done session's record after the next
        session was created still gets it, with the path), each compared in constant time;
        Refused 404 for any other token (the id is never part of a path)."""
        missing = Refused(HTTPStatus.NOT_FOUND, "not_found", "no such video session")
        if not video.ID_PATTERN.fullmatch(token):
            raise missing
        with self._video_lock:
            candidates = (self._video, self._video_last)
        for session in candidates:
            if session is not None and secrets.compare_digest(
                token.encode("ascii"), session.id.encode("ascii")
            ):
                return session
        raise missing

    def _video_spec(self, obj: Mapping[str, Any]) -> video.SessionSpec:
        """POST /api/videos' body as a SessionSpec (D-SP2-31: whitelisted keys, enumerated
        choices, bounded numbers): the directory looked up in the server's own listing
        (404), not the running launch's and playable (409), 1 to VIDEO_RUNS distinct runs
        of its run list (422), fps and width from the fixed lists, the frame count from
        ``frames`` or ``seconds`` (1 to the limit), the optional scene times, and the
        footer the server computes (``video_footer``). Raises Refused."""
        unknown = set(obj) - VIDEO_REQUEST_KEYS
        if unknown:
            raise Refused(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "unknown_key",
                "the request holds a key not accepted",
            )
        experiment, timestamp = obj.get("experiment"), obj.get("timestamp")
        if not isinstance(experiment, str) or not isinstance(timestamp, str):
            raise Refused(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "bad_directory",
                "experiment and timestamp are names",
            )
        run_dir = self.find(experiment, timestamp)
        if self.running_directory() == (experiment, timestamp):
            raise Refused(HTTPStatus.CONFLICT, "running", "this directory is the running launch's")
        row = self._row(run_dir, experiment, timestamp, False)
        if not row["playable"]:
            raise Refused(
                HTTPStatus.CONFLICT,
                "not_playable",
                f"this directory has no scene to film: {row['reason']}",
                reason=row["reason"],
            )
        try:
            names = video.check_runs(obj.get("runs"), VIDEO_RUNS)
            fps = video.check_fps(obj.get("fps"))
            width = video.check_width(obj.get("width"))
            frames = video.frame_count(
                fps, obj.get("frames"), obj.get("seconds"), self.video_limits
            )
            times = video.check_times(obj.get("times"), frames)
        except video.VideoError as exc:
            raise _refused_from(exc) from exc
        try:
            metrics = read_capped_json(run_dir / run_data.METRICS_FILE, MAX_METRICS_BYTES)
            members = run_folders(run_dir, metrics)
            if any(n not in members for n in names):
                raise Refused(
                    HTTPStatus.UNPROCESSABLE_ENTITY,
                    "bad_selection",
                    "a run of the selection is not in the directory's run list",
                )
            config = read_capped_yaml(run_dir / run_data.CONFIG_FILE, MAX_CONFIG_BYTES)
            footer = video_footer(run_dir, names, metrics, config)
        except (UnreadableError, OSError, ValueError, KeyError) as exc:
            # RunDataError and pandas' ParserError and EmptyDataError are ValueErrors; a
            # series of text cells fails its float conversion with one too (fix round 3):
            # every unreadable file is the same 422, never a 500
            self.forget_row(run_dir)
            text = (
                str(exc)[:FAILED_LINE_MAX]
                if isinstance(exc, UnreadableError)  # fixed text naming the file only
                else "the directory's files cannot be read for a video"
            )
            raise Refused(HTTPStatus.UNPROCESSABLE_ENTITY, "no_video", text) from exc
        return video.SessionSpec(
            experiment=experiment,
            timestamp=timestamp,
            runs=tuple(names),
            run_dir=run_dir,
            fps=fps,
            frames=frames,
            width=width,
            height=video.frame_height(width),
            footer=tuple(footer),
            times=None if times is None else tuple(times),
        )

    def start_video(self, obj: Mapping[str, Any]) -> tuple[HTTPStatus, dict[str, Any]]:
        """POST /api/videos: under the start lock (so a launch and a video never start
        together): 503 'stopping' once the server stops; 503 VIDEO_UNAVAILABLE_CODE with
        the reason when the export is off; 409 'launch_running' while a launch runs; 409
        'video_busy' while a session is open; else the request checked (``_video_spec``),
        the session created (the encoder started) and 201 with its record, the scene times
        and the footer lines."""
        with self._start_lock:
            if self._stopping:
                return HTTPStatus.SERVICE_UNAVAILABLE, {
                    "error": "stopping",
                    "message": STOPPING_MESSAGE,
                }
            if self.video_reason or self.encoder is None:
                return HTTPStatus.SERVICE_UNAVAILABLE, {
                    "error": VIDEO_UNAVAILABLE_CODE,
                    "message": f"videos cannot be saved: {self.video_reason}",
                }
            with self._job_lock:
                launching = self._job is not None and self._job.state == JOB_RUNNING
            if launching:
                return HTTPStatus.CONFLICT, {
                    "error": "launch_running",
                    "message": LAUNCH_RUNNING_MESSAGE,
                }
            if self.video_busy():
                return HTTPStatus.CONFLICT, {
                    "error": "video_busy",
                    "message": "a video is being saved; one at a time",
                }
            spec = self._video_spec(obj)
            try:
                session = video.VideoSession(
                    spec,
                    self.encoder,
                    self.work_dir,
                    repo_root=self.repo_root,
                    results_root=self.results_root,
                    limits=self.video_limits,
                    report=self._video_report,
                )
            except video.VideoError as exc:
                raise _refused_from(exc) from exc
            with self._video_lock:
                # the ended session stays readable as the last one (fix round 3); it is
                # in a final state here, since the slot was free under the start lock
                if self._video is not None:
                    self._video_last = self._video
                self._video = session
        return HTTPStatus.CREATED, {
            "video": session.record(),
            "times": None if spec.times is None else list(spec.times),
            "footer": list(spec.footer),
        }

    def app_page(self, other_site: bool = False) -> tuple[bytes, str]:
        """GET /: the app page and its Content-Security-Policy (rendered once per value
        of ``other_site``, ``from_other_site`` of the request: the page's data block
        carries it as ``from_other_site``; the script, and so the policy, is the same)."""
        key = bool(other_site)
        page = self._pages.get(key)
        if page is None:
            page = render_app_page(
                {
                    "url": self.url,
                    "boot_id": self.boot_id,
                    "version": __version__,
                    "from_other_site": key,
                }
            )
            self._pages[key] = page
        return page

    def launch(self, obj: dict[str, Any]) -> tuple[HTTPStatus, dict[str, Any]]:
        """POST /api/launches: ``appform.parse_request``; with ``dry_run`` true, 200 with
        the derived values or the refusal (``dry_run``: nothing flown, written or
        started); else 422 for a refused form, or ``start_launch``."""
        dry = obj.get("dry_run") is True
        parsed = appform.parse_request(obj)
        if isinstance(parsed, appform.Refusal):
            refusal = {"field": parsed.field, "message": parsed.message}
            if dry:
                return HTTPStatus.OK, {"dry_run": True, "refused": refusal, "derived": None}
            return HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "refused", **refusal}
        if parsed.dry_run:
            result = dry_run(self.basis, parsed, cache=self.cache, server_start=self.server_start)
            if isinstance(result, appform.Refusal):
                refusal = {"field": result.field, "message": result.message}
                return HTTPStatus.OK, {"dry_run": True, "refused": refusal, "derived": None}
            return HTTPStatus.OK, {"dry_run": True, "refused": None, "derived": result}
        return self.start_launch(parsed)

    def _row(self, run_dir: Path, experiment: str, timestamp: str, running: bool) -> dict[str, Any]:
        """The row of one directory (``directory_row``): the running launch's built each
        time (never cached); a cached row in one of FINAL_STATES reused as it is (no file
        is read: such a directory never changes); any other cached row reused while the
        directory's signature (``directory_signature``) is unchanged; an incomplete row
        never cached; any error gives an unreadable row."""
        if running:
            return directory_row(run_dir, experiment, timestamp, running=True)
        key = str(run_dir)
        with self._rows_lock:
            hit = self._rows.get(key)
        if hit is not None and hit[1]["state"] in FINAL_STATES:
            return hit[1]
        signature = directory_signature(run_dir)
        if hit is not None and hit[0] == signature:
            return hit[1]
        try:
            row = directory_row(run_dir, experiment, timestamp, running=False)
        except Exception as exc:  # one directory never breaks the listing
            row = unreadable_row(experiment, timestamp, exc)
        if row["state"] != DIR_INCOMPLETE:
            with self._rows_lock:
                self._rows[key] = (signature, row)
        return row

    def sp1_same_at(self, metrics: Mapping[str, Any]) -> bool | None:
        """Whether the basis files at an app run's recorded basis commit (its git record's
        EXPLORATORY_BASIS_COMMIT_KEY) are SP1's (``sp1_files_same`` at that commit, one
        read-only git call per commit, kept for the server's life); None for a directory
        without one (a recorded directory, a basis not read from a commit)."""
        commit = run_data.as_mapping(metrics.get("git")).get(summary.EXPLORATORY_BASIS_COMMIT_KEY)
        if not replay.is_exploratory(metrics) or not isinstance(commit, str) or not commit:
            return None
        with self._sp1_lock:
            if commit not in self._sp1_same_by_commit:
                self._sp1_same_by_commit[commit] = sp1_files_same(
                    self.repo_root, self.basis, commit
                )
            return self._sp1_same_by_commit[commit]

    def forget_row(self, run_dir: Path) -> None:
        """Drop the cached row of a directory (a row cached in one of FINAL_STATES whose
        files a later read found changed: the next listing builds it again)."""
        with self._rows_lock:
            self._rows.pop(str(run_dir), None)

    def listing(self) -> tuple[list[tuple[str, str, Path]], int]:
        """``listed_directories`` of the results root, kept per folder (survey 07: a
        file-system call waits for the GIL behind a launch, about 9 ms each): the root's
        folders are listed again only when the root's stat changes, and an experiment
        folder's entries only when its own stat changes (creating or removing a directory
        in it changes its mtime), so an unchanged tree costs one stat of the root and one
        per experiment folder. A folder changed within LISTING_SETTLE_NS of the listing is
        listed again next time."""
        with self._listing_lock:
            state = self._root_state()
            if state is None:
                return [], 0
            folders, others, real = state
            found: list[tuple[str, str, Path]] = []
            kept: dict[str, tuple[Any, list[tuple[str, Path]], int]] = {}
            for folder in folders:
                entry = self._folder_state(folder, real)
                if entry is None:  # removed: the root's own stat changes too
                    continue
                kept[folder.name] = entry
                found += [(folder.name, ts, path) for ts, path in entry[1]]
                others += entry[2]
            self._folder_listings = kept
            return found, others

    def _root_state(self) -> tuple[list[Path], int, Path] | None:
        """(the root's experiment folders, its other entries, the resolved root), kept
        while the root's stat is unchanged (``root_folders``); None (and the kept
        listing dropped) when the root is missing. Call with the listing lock held."""
        root = self.results_root
        stamp = _dir_stamp(root)
        if stamp is None:
            self._root_listing = None
            self._folder_listings = {}
            return None
        cached = self._root_listing
        if cached is None or cached[0] != stamp:
            folders, others = root_folders(root)
            settled = time.time_ns() - stamp[1] > LISTING_SETTLE_NS
            cached = (stamp if settled else None, folders, others, root.resolve())
            self._root_listing = cached
        return cached[1], cached[2], cached[3]

    def _folder_state(
        self, folder: Path, real: Path
    ) -> tuple[Any, list[tuple[str, Path]], int] | None:
        """(its stat when settled, its (timestamp, path) entries, its other entries) of
        one experiment folder, kept while its stat is unchanged (``folder_entries``);
        None when it is gone. Call with the listing lock held."""
        stamp = _dir_stamp(folder)
        if stamp is None:
            return None
        entry = self._folder_listings.get(folder.name)
        if entry is None or entry[0] != stamp:
            entries, n = folder_entries(folder, real)
            settled = time.time_ns() - stamp[1] > LISTING_SETTLE_NS
            entry = (stamp if settled else None, entries, n)
            self._folder_listings[folder.name] = entry
        return entry

    def find(self, experiment: str, timestamp: str) -> Path:
        """The results directory <root>/<experiment>/<timestamp> of a request: both names
        checked (the experiment by results_io's naming rules, the timestamp by
        TIMESTAMP_PATTERN), then looked up by exact name in the server's own kept listing
        of the root (never joined from the request; ``listing``'s checks: no link or
        junction, a directory resolving inside the root), at the cost of a stat of the
        root and of the one experiment folder when nothing changed. Refused (404)
        otherwise."""
        missing = Refused(HTTPStatus.NOT_FOUND, "not_found", "no such results directory")
        if not valid_experiment_name(experiment) or not TIMESTAMP_PATTERN.fullmatch(timestamp):
            raise missing
        with self._listing_lock:
            state = self._root_state()
            folder = (
                None if state is None else next((f for f in state[0] if f.name == experiment), None)
            )
            entry = (
                None if state is None or folder is None else self._folder_state(folder, state[2])
            )
        path = None if entry is None else next((p for t, p in entry[1] if t == timestamp), None)
        if path is None:
            raise missing
        return path

    def results(self) -> dict[str, Any]:
        """GET /api/results: the run browser, two groups (app runs, recorded
        experiments), newest first, each directory handled on its own (``listing``,
        ``_row``), each row with the findings notes that cite it (``cited_in``,
        ``findings_citations`` of the repository); the count of the entries not listed."""
        found, others = self.listing()
        running = self.running_directory()
        cites = findings_citations(self.repo_root)
        groups: dict[str, list[dict[str, Any]]] = {GROUP_APP: [], GROUP_RECORDED: []}
        for experiment, timestamp, run_dir in found:
            row = self._row(run_dir, experiment, timestamp, (experiment, timestamp) == running)
            row = {**row, "cited_in": cites.get((experiment, timestamp), [])}
            groups[row["group"]].append(row)
        for rows in groups.values():
            rows.sort(key=lambda r: (stamp_key(r["timestamp"]), r["experiment"]), reverse=True)
        with self._rows_lock:
            keep = {str(p) for _, _, p in found}
            self._rows = {k: v for k, v in self._rows.items() if k in keep}
        return {
            "groups": [
                {"name": name, "title": GROUP_TITLES[name], "rows": rows}
                for name, rows in groups.items()
            ],
            "not_listed": others,
            "running": None
            if running is None
            else {"experiment": running[0], "timestamp": running[1]},
        }

    def result_detail(
        self, experiment: str, timestamp: str, selection: str | None = None
    ) -> dict[str, Any]:
        """GET /api/results/<experiment>/<timestamp> (``selection`` None) and GET
        /api/panel/<experiment>/<timestamp>/<runs>: the directory's row and, for a complete
        planar directory, its run list, default pair and results panel (``results_panel``
        with ``sp1_same_at`` of the directory's basis commit, cached by the directory's
        signature and the runs; one build at a time). ``selection``: the runs the panel
        describes, names joined by ',' (1 to PANEL_RUNS distinct runs of the directory's
        run list, else Refused 422 bad_selection, the scene route's rule; Refused 409
        no_panel for a directory that has no panel); None: the directory's own pair
        (``shown_run``). A panel that cannot be built leaves the row with
        ``panel_error``: an unreadable file's fixed text (UnreadableError: the file's name
        only), else the error's type only."""
        run_dir = self.find(experiment, timestamp)
        running = self.running_directory() == (experiment, timestamp)
        row = self._row(run_dir, experiment, timestamp, running)
        chosen: tuple[str, ...] | None = None
        if selection is not None:
            chosen = tuple(selection.split(","))
            if not 1 <= len(chosen) <= PANEL_RUNS or len(set(chosen)) != len(chosen):
                raise Refused(
                    HTTPStatus.UNPROCESSABLE_ENTITY,
                    "bad_selection",
                    f"a results panel describes 1 to {PANEL_RUNS} distinct runs of the "
                    "directory's run list",
                )
        out: dict[str, Any] = {
            "row": row,
            "baseline": None,
            "runs": [],
            "default_pair": [],
            "panel": None,
            "panel_error": None,
        }
        if row["state"] != DIR_COMPLETE or row["model"] != PLANAR_2D:
            if chosen is not None:
                raise Refused(
                    HTTPStatus.CONFLICT,
                    "no_panel",
                    f"this directory has no results panel: {row['reason'] or row['state']}",
                )
            return out
        key = (str(run_dir), directory_signature(run_dir), chosen)
        detail = self._panels.get(key)
        if detail is None:
            with self._panel_lock:
                detail = self._panels.get(key)
                if detail is None:
                    try:
                        metrics = read_capped_json(
                            run_dir / run_data.METRICS_FILE, MAX_METRICS_BYTES
                        )
                        if chosen is not None and any(
                            n not in run_folders(run_dir, metrics) for n in chosen
                        ):
                            raise Refused(
                                HTTPStatus.UNPROCESSABLE_ENTITY,
                                "bad_selection",
                                "a run of the selection is not in the directory's run list",
                            )
                        config = read_capped_yaml(run_dir / run_data.CONFIG_FILE, MAX_CONFIG_BYTES)
                        detail = plain(
                            results_panel(
                                run_dir,
                                experiment,
                                timestamp,
                                self.basis,
                                metrics,
                                config,
                                self.sp1_same_at(metrics),
                                chosen,
                            )
                        )
                    except Refused:
                        raise
                    except Exception as exc:  # the row stands; the panel says why it is missing
                        why = (
                            str(exc)[:FAILED_LINE_MAX]
                            if isinstance(exc, UnreadableError)
                            else type(exc).__name__
                        )
                        return {
                            **out,
                            "panel_error": f"the results panel could not be built: {why}",
                        }
                    self._panels.put(key, detail)
        return {**out, "panel_error": None, **detail}

    def scene_csp(self) -> str:
        """The served scene page's header policy (``scene_header_csp``, read once)."""
        if self._scene_csp is None:
            self._scene_csp = scene_header_csp()
        return self._scene_csp

    def scene_page(self, experiment: str, timestamp: str, selection: str) -> bytes:
        """GET /scene/<experiment>/<timestamp>/<runs>: the scene page (scene.render_page
        of scene.scene_payload) of 1 to run_data.MAX_RUNS distinct runs of the directory
        (``selection``: names joined by ',', each in the directory's run list,
        ``run_folders``; else 422). Refused (409) for the running launch's directory and
        for one that cannot be played (its row's reason). Pages are kept in an LRU keyed by
        directory, selection and metrics.json's mtime, looked up right after those checks
        (a hit reads no file: the names were checked against the run list when the page
        was built); one build at a time (a second request for the same key waits and
        reuses it). A build reads metrics.json (capped) for the run list (422 no_scene with
        its fixed text when it is a link, over its cap or cannot be parsed: a directory
        changed after its row was cached complete, whose cached row is then dropped,
        ``forget_row``) and parses resolved_config.yaml under the server's own rules first
        (``read_capped_yaml``: a file within MAX_CONFIG_BYTES with no YAML anchor or alias;
        422 with its fixed text otherwise), so scene.scene_payload, which parses it again,
        never meets a file those rules refuse."""
        run_dir = self.find(experiment, timestamp)
        if self.running_directory() == (experiment, timestamp):
            raise Refused(HTTPStatus.CONFLICT, "running", "this directory is the running launch's")
        row = self._row(run_dir, experiment, timestamp, False)
        if not row["playable"]:
            raise Refused(
                HTTPStatus.CONFLICT,
                "not_playable",
                f"this directory has no scene: {row['reason']}",
                reason=row["reason"],
            )
        names = selection.split(",")
        bad = Refused(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "bad_selection",
            f"a scene shows 1 to {run_data.MAX_RUNS} distinct runs of the directory's run list",
        )
        if not 1 <= len(names) <= run_data.MAX_RUNS or len(set(names)) != len(names):
            raise bad
        stamp = _stat(run_dir / run_data.METRICS_FILE)
        key = (str(run_dir), tuple(names), None if stamp is None else stamp[1])
        page = self._scenes.get(key)
        if page is not None:
            return page
        try:
            metrics = read_capped_json(run_dir / run_data.METRICS_FILE, MAX_METRICS_BYTES)
            members = run_folders(run_dir, metrics)
        except (UnreadableError, OSError) as exc:
            # a directory changed after its row was cached complete: its row is built again
            self.forget_row(run_dir)
            text = (
                str(exc)[:FAILED_LINE_MAX]
                if isinstance(exc, UnreadableError)  # fixed text naming the file only
                else f"{run_data.METRICS_FILE} or a run folder cannot be read"
            )
            raise Refused(HTTPStatus.UNPROCESSABLE_ENTITY, "no_scene", text) from exc
        if any(n not in members for n in names):
            raise bad
        config_path = run_dir / run_data.CONFIG_FILE
        try:
            _check_capped(config_path, MAX_CONFIG_BYTES)  # a missing file is refused too
            read_capped_yaml(config_path, MAX_CONFIG_BYTES)
        except UnreadableError as exc:  # fixed text naming the file only
            raise Refused(
                HTTPStatus.UNPROCESSABLE_ENTITY, "no_scene", str(exc)[:FAILED_LINE_MAX]
            ) from exc
        except OSError as exc:
            raise Refused(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "no_scene",
                f"{run_data.CONFIG_FILE} cannot be read",
            ) from exc
        if not self.display_dir.is_dir():
            raise Refused(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "display_missing",
                "the display files (configs/display) are missing",
            )
        with self._scene_lock:
            page = self._scenes.get(key)
            if page is None:
                try:
                    payload = scene.scene_payload(run_dir, names, display_dir=self.display_dir)
                except run_data.RunDataError as exc:
                    # the directory as <experiment>/<timestamp>, never its local path
                    text = " ".join(str(exc).split()).replace(
                        str(run_dir), f"{experiment}/{timestamp}"
                    )
                    raise Refused(
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                        "no_scene",
                        text[: appform.MAX_REFUSAL_CHARS],
                    ) from exc
                except (OSError, ValueError, KeyError) as exc:
                    # a series pandas cannot parse or convert (ParserError, a float
                    # conversion of text cells) in a directory whose row is playable (fix
                    # round 3): a fixed text, never the exception's (it can quote a cell)
                    self.forget_row(run_dir)
                    raise Refused(
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                        "no_scene",
                        "the directory's files cannot be read for a scene",
                    ) from exc
                page = scene.render_page(payload).encode("utf-8")
                self._scenes.put(key, page)
        return page


ROUTES: tuple[tuple[str, str], ...] = (
    ("GET", "/"),
    ("GET", "/api/form"),
    ("POST", "/api/launches"),
    ("GET", "/api/job"),
    ("GET", "/api/results"),
    ("GET", "/api/results/<experiment>/<timestamp>"),
    ("GET", "/api/panel/<experiment>/<timestamp>/<runs>"),
    ("GET", "/scene/<experiment>/<timestamp>/<runs>"),
    ("POST", "/api/videos"),
    ("GET", "/api/videos/<id>"),
    ("POST", "/api/videos/<id>/frames/<n>"),
    ("POST", "/api/videos/<id>/finish"),
    ("POST", "/api/videos/<id>/cancel"),
)
"""Every route (method, path); any other path is 404, any other method 501. Every POST
body is a JSON object of at most MAX_JSON_BODY_BYTES (``AppHandler._json_body``) but the
frame route's, one image/png of at most the session's frame cap and remaining budget
(``AppHandler._png_body``): the one exception to the body rule (step A6v)."""


class DeadlineReader(io.RawIOBase):
    """The read side of a request's socket under one deadline (``time.monotonic``) for
    the whole request: before each recv the socket's timeout is set to what is left of
    it, and TimeoutError is raised once nothing is left, so a client that drips a byte at
    a time cannot hold a handler thread past the deadline (a per-recv timeout alone
    restarts with every byte). ``end`` lifts the deadline once the request is read. The
    socket itself is closed by the server, never here."""

    def __init__(self, sock: socket.socket, deadline: float) -> None:
        super().__init__()
        self._sock = sock
        self._deadline: float | None = deadline

    def arm(self, deadline: float) -> None:
        """Set the deadline of the next request on this connection (fix round 3: one per
        request on a kept connection)."""
        self._deadline = deadline

    def readable(self) -> bool:
        """True: a read-only raw stream."""
        return True

    def readinto(self, buffer: Any) -> int:
        """recv_into ``buffer`` within what is left of the deadline (TimeoutError once
        none is left or the recv waits past it)."""
        if self._deadline is not None:
            left = self._deadline - time.monotonic()
            if left <= 0.0:
                raise TimeoutError("the request did not arrive within the handler timeout")
            self._sock.settimeout(left)
        return self._sock.recv_into(buffer)

    def end(self) -> None:
        """Lift the deadline (the request has been read)."""
        self._deadline = None


class AppHandler(http.server.BaseHTTPRequestHandler):
    """The app's request handler: only do_GET and do_POST (every other method gets the
    standard library's 501, answered as JSON by ``send_error``); HTTP/1.1 with kept
    connections (fix round 3: an export posts up to 1,800 frames, and one connection per
    frame let Windows' loopback stack refuse a connection now and then, which the page saw
    as a lost frame POST), every response with a Content-Length, and the connection closed
    after any refusal or error (its body may be unread, and an unread body is never read as
    the next request), after a request line of HTTP/1.0 (``default_request_version``: also
    a malformed one) and once the server is stopping; each request (line, headers, body)
    must arrive within HANDLER_TIMEOUT_S of its start (``DeadlineReader``, armed per
    request, so an idle kept connection ends after HANDLER_TIMEOUT_S, as a silent one did
    before; the response is written under the same socket timeout); a Server header
    without the Python version; no log line. Every request passes ``guard`` first; any
    exception gives a JSON 500 with a fixed message."""

    server: AppServer
    protocol_version = "HTTP/1.1"
    default_request_version = "HTTP/1.0"
    timeout = HANDLER_TIMEOUT_S
    server_version = SERVER_VERSION
    sys_version = ""
    _frame: tuple[str, str] | None = None
    _responded = False
    _reader: DeadlineReader | None = None

    def setup(self) -> None:
        """The standard library's setup, then the request read through a DeadlineReader
        (armed per request by ``handle_one_request``)."""
        super().setup()
        self.rfile.close()  # the buffered socket file the standard library made
        self._reader = DeadlineReader(self.connection, time.monotonic() + HANDLER_TIMEOUT_S)
        self.rfile = io.BufferedReader(self._reader)

    def handle_one_request(self) -> None:
        """One request of the connection: the deadline armed HANDLER_TIMEOUT_S (read now,
        so a test may change it) from now, the per-request state cleared, then the
        standard library's handle_one_request; the connection is closed afterwards when
        the server is stopping (fix round 3)."""
        if self._reader is not None:
            self._reader.arm(time.monotonic() + HANDLER_TIMEOUT_S)
        self._responded = False
        self._frame = None
        super().handle_one_request()
        if self.server._stopping:
            self.close_connection = True

    def _request_read(self) -> None:
        """End the request's deadline before a response is written; the socket's timeout
        is HANDLER_TIMEOUT_S again for the write."""
        if self._reader is not None:
            self._reader.end()
            self.connection.settimeout(HANDLER_TIMEOUT_S)

    def version_string(self) -> str:
        """The Server header: SERVER_VERSION only."""
        return SERVER_VERSION

    def log_message(self, format: str, *args: Any) -> None:
        """Silent: no line per request."""
        return

    def end_headers(self) -> None:
        """Add FIXED_HEADERS and the frame policy and Content-Security-Policy (a page's
        own, else FRAME_DENY and API_CSP) to every response, the standard library's
        errors included."""
        for name, value in FIXED_HEADERS:
            self.send_header(name, value)
        frame, csp = self._frame or (FRAME_DENY, API_CSP)
        self.send_header("X-Frame-Options", frame)
        self.send_header("Content-Security-Policy", csp)
        super().end_headers()

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        """The standard library's errors (a malformed request, 414, 431, 501) as JSON
        with the status phrase only: the request's text is never echoed."""
        try:
            phrase = HTTPStatus(code).phrase
        except ValueError:
            phrase = "Error"
        self.close_connection = True
        body = json_bytes({"error": f"http_{code}", "message": phrase})
        self._send(code, body, JSON_CONTENT_TYPE)

    def _send(
        self,
        status: int,
        body: bytes,
        content_type: str,
        frame: tuple[str, str] | None = None,
    ) -> None:
        """One response: the request's deadline ended (``_request_read``), then status,
        Content-Type, Content-Length, the headers of ``end_headers`` (``frame``: a page's
        frame policy and CSP), the body."""
        self._request_read()
        self._frame = frame
        self._responded = True
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, obj: Any) -> None:
        """Send ``obj`` as strict JSON (``json_bytes``) with ``status``."""
        self._send(status, json_bytes(obj), JSON_CONTENT_TYPE)

    def do_GET(self) -> None:
        """Dispatch a GET (``_handle``)."""
        self._handle("GET")

    def do_POST(self) -> None:
        """Dispatch a POST (``_handle``)."""
        self._handle("POST")

    def _handle(self, method: str) -> None:
        """Guard, route, answer; a Refused is its JSON error, any other exception a JSON
        500 with INTERNAL_ERROR_MESSAGE (recorded in the server's ``last_error``, type
        only), unless the response had already started."""
        try:
            parts = guard(method, self.path, self.headers, self.server.port)
            if method == "GET":
                self._route_get(parts)
            else:
                self._route_post(parts)
        except Refused as exc:
            # the body may be unread (a 413 before any byte, a refusal of the headers):
            # the connection ends with the response, so it is never read as a request
            self.close_connection = True
            if not self._responded:
                self._json(exc.status, exc.body())
        except Exception as exc:  # no traceback ever reaches a client
            self.close_connection = True
            self.server.last_error = type(exc).__name__
            if not self._responded:
                self._json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": "internal", "message": INTERNAL_ERROR_MESSAGE},
                )

    def _route_get(self, parts: list[str]) -> None:
        """Dispatch a guarded GET by its decoded path segments (ROUTES): /, /api/form,
        /api/job, /api/results, /api/results/<experiment>/<timestamp>,
        /api/panel/<experiment>/<timestamp>/<runs> and
        /scene/<experiment>/<timestamp>/<runs>; anything else is Refused 404."""
        server = self.server
        if parts == [""]:
            page, csp = server.app_page(from_other_site(self.headers))
            self._send(HTTPStatus.OK, page, HTML_CONTENT_TYPE, (FRAME_DENY, csp))
        elif parts == ["api", "form"]:
            self._json(HTTPStatus.OK, server.form_info())
        elif parts == ["api", "job"]:
            self._json(HTTPStatus.OK, server.job_snapshot())
        elif parts == ["api", "results"]:
            self._json(HTTPStatus.OK, server.results())
        elif len(parts) == 4 and parts[:2] == ["api", "results"]:
            self._json(HTTPStatus.OK, server.result_detail(parts[2], parts[3]))
        elif len(parts) == 5 and parts[:2] == ["api", "panel"]:
            self._json(HTTPStatus.OK, server.result_detail(parts[2], parts[3], parts[4]))
        elif len(parts) == 4 and parts[0] == "scene":
            page = server.scene_page(parts[1], parts[2], parts[3])
            frame = (FRAME_SAMEORIGIN, server.scene_csp())
            self._send(HTTPStatus.OK, page, HTML_CONTENT_TYPE, frame)
        elif len(parts) == 3 and parts[:2] == ["api", "videos"]:
            self._json(HTTPStatus.OK, {"video": server.video_session(parts[2]).record()})
        else:
            raise Refused(HTTPStatus.NOT_FOUND, "not_found", "no such route")

    def _route_post(self, parts: list[str]) -> None:
        """POST /api/launches (its body by ``_json_body``, then ``AppServer.launch``); the
        video routes (step A6v): POST /api/videos (JSON, ``AppServer.start_video``), POST
        /api/videos/<id>/frames/<n> (the header checks of one image/png body first,
        ``_png_headers``; then the session by its id and the index, a miss 404 answered
        after the declared body has been read and discarded, like every refusal past the
        length check (fix round 2: a 404 sent with the body unread is a reset the page saw
        as a lost connection after a server restart); then the body by ``_png_body`` and
        ``VideoSession.accept_frame``), POST /api/videos/<id>/finish and /cancel (an empty
        JSON object, ``_empty_json_body``: a key is 422, as an unknown key is for every
        POST); any other path is Refused 404. A VideoError is answered with its own
        status."""
        server = self.server
        try:
            if parts == ["api", "launches"]:
                status, body = server.launch(self._json_body())
            elif parts == ["api", "videos"]:
                status, body = server.start_video(self._json_body())
            elif len(parts) == 5 and parts[:2] == ["api", "videos"] and parts[3] == "frames":
                n = self._png_headers(server.video_limits.max_frame_bytes)
                try:
                    session = server.video_session(parts[2])
                    if not video.FRAME_INDEX_PATTERN.fullmatch(parts[4]):
                        raise Refused(HTTPStatus.NOT_FOUND, "not_found", "no such route")
                except Refused:
                    self._drain(n)
                    raise
                index = int(parts[4])
                data = self._png_body(session, index, n)
                received = session.accept_frame(index, data)
                status, body = HTTPStatus.OK, {"received": received, "frames": session.spec.frames}
            elif len(parts) == 4 and parts[:2] == ["api", "videos"] and parts[3] == "finish":
                session = server.video_session(parts[2])
                self._empty_json_body()
                session.finish()
                status, body = HTTPStatus.ACCEPTED, {"video": session.record()}
            elif len(parts) == 4 and parts[:2] == ["api", "videos"] and parts[3] == "cancel":
                session = server.video_session(parts[2])
                self._empty_json_body()
                session.cancel()
                status, body = HTTPStatus.OK, {"video": session.record()}
            else:
                raise Refused(HTTPStatus.NOT_FOUND, "not_found", "no such route")
        except video.VideoError as exc:
            raise _refused_from(exc) from exc
        self._json(status, body)

    def _png_headers(self, cap: int) -> int:
        """The frame route's header checks (the one exception to the JSON rule; review 04
        finding 1), before a byte is read and before the session is looked up (fix round
        2): exactly one Content-Type of PNG_MEDIA_TYPE with no parameter (415); no
        Transfer-Encoding (400); exactly one Content-Length of ASCII digits (411 when
        missing, 400 otherwise); at most ``cap`` bytes, the server's frame cap (413, the
        body unread: the one refusal answered without reading the body). Returns the
        declared length."""
        types = self.headers.get_all("Content-Type") or []
        if len(types) != 1 or types[0].strip().lower() != PNG_MEDIA_TYPE:
            raise Refused(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "unsupported_media_type",
                f"a frame body must be {PNG_MEDIA_TYPE}",
            )
        if self.headers.get_all("Transfer-Encoding"):
            raise Refused(
                HTTPStatus.BAD_REQUEST, "bad_request", "Transfer-Encoding is not accepted"
            )
        lengths = self.headers.get_all("Content-Length") or []
        if not lengths:
            raise Refused(
                HTTPStatus.LENGTH_REQUIRED, "length_required", "Content-Length is required"
            )
        if len(lengths) != 1 or not CONTENT_LENGTH_PATTERN.fullmatch(lengths[0].strip()):
            raise Refused(HTTPStatus.BAD_REQUEST, "bad_request", "one Content-Length of digits")
        n = int(lengths[0].strip())
        if n > cap:
            raise Refused(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "frame_too_large",
                f"a frame body is at most {cap} bytes",
            )
        return n

    def _png_body(self, session: video.VideoSession, index: int, n: int) -> bytes:
        """The frame route's body of ``n`` declared bytes (``_png_headers`` passed them):
        the remaining budget (413) and the index the session expects (409), each answered
        only after the declared body has been read and discarded (``_drain``; fix round 1:
        a refusal sent with the body unread closes the socket on unread data, which
        Windows turns into a reset the client sees as a lost connection, not the refusal);
        then exactly that many bytes under the handler timeout (400 when short)."""
        try:
            if n > session.remaining_bytes:
                raise Refused(
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                    "budget",
                    "the frame would pass the session's byte budget",
                )
            session.check_next(index)
        except (Refused, video.VideoError):
            self._drain(n)
            raise
        try:
            data = self.rfile.read(n)
        except OSError as exc:  # the handler timeout, a reset
            raise Refused(
                HTTPStatus.BAD_REQUEST, "bad_request", "the request body did not arrive"
            ) from exc
        if len(data) != n:
            raise Refused(
                HTTPStatus.BAD_REQUEST, "bad_request", "the request body is shorter than declared"
            )
        return data

    def _drain(self, n: int) -> None:
        """Read and discard the ``n`` declared body bytes (at most a frame's cap, already
        checked) before a refusal is answered, under the handler deadline; a short or
        failed read is ignored, since the refusal is sent either way (fix round 1)."""
        try:
            self.rfile.read(n)
        except OSError:
            pass

    def _empty_json_body(self) -> None:
        """The body of POST /api/videos/<id>/finish and /cancel: a JSON object
        (``_json_body``) with no key; any key is Refused 422 unknown_key, the rule every
        other POST applies to a key it does not accept (D-SP2-31; fix round 1)."""
        if self._json_body():
            raise Refused(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "unknown_key",
                "the request holds a key not accepted",
            )

    def _json_body(self) -> dict[str, Any]:
        """The request body as a JSON object, every check before a byte is read: exactly
        one Content-Type of JSON (415); no Transfer-Encoding (400); exactly one
        Content-Length of ASCII digits (411 when missing, 400 otherwise); at most
        MAX_JSON_BODY_BYTES (413); then exactly that many bytes under the handler timeout
        (400 when short) and ``strict_json_object``."""
        types = self.headers.get_all("Content-Type") or []
        if len(types) != 1 or not json_type_ok(types[0]):
            raise Refused(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "unsupported_media_type",
                "the request body must be application/json",
            )
        if self.headers.get_all("Transfer-Encoding"):
            raise Refused(
                HTTPStatus.BAD_REQUEST, "bad_request", "Transfer-Encoding is not accepted"
            )
        lengths = self.headers.get_all("Content-Length") or []
        if not lengths:
            raise Refused(
                HTTPStatus.LENGTH_REQUIRED, "length_required", "Content-Length is required"
            )
        if len(lengths) != 1 or not CONTENT_LENGTH_PATTERN.fullmatch(lengths[0].strip()):
            raise Refused(HTTPStatus.BAD_REQUEST, "bad_request", "one Content-Length of digits")
        n = int(lengths[0].strip())
        if n > MAX_JSON_BODY_BYTES:
            raise Refused(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "body_too_large",
                f"the request body is over {MAX_JSON_BODY_BYTES} bytes",
            )
        try:
            data = self.rfile.read(n)
        except OSError as exc:  # the handler timeout, a reset
            raise Refused(
                HTTPStatus.BAD_REQUEST, "bad_request", "the request body did not arrive"
            ) from exc
        if len(data) != n:
            raise Refused(
                HTTPStatus.BAD_REQUEST, "bad_request", "the request body is shorter than declared"
            )
        return strict_json_object(data)
