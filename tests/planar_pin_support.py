"""Regression pins of the planar pipeline (SP1 step 1; docs/phases/SP1-fuel-offload-planar.md,
sections 5.12 and 7).

SP1 touches validated code with neutral defaults (the merge rule of config.py, the
planners, the search). Two pins, captured from the untouched code of REFERENCE_COMMIT
before any of it changed, say that nothing a shipped planar experiment resolves to or
writes has moved:

- **Resolved digests** (tests/data/planar_pins/resolved_digests.json; test in
  tests/test_config_planar.py): a sha256 of ``json.dumps(run_dict)`` and of
  ``json.dumps(vehicle_dict)``, key order kept, for every run the four shipped planar
  experiments (PINNED_EXPERIMENTS) resolve: the baseline and the variants, every sweep
  point and its paired baseline, every sensitivity run, every bound run with its paired
  baseline, and every calibration case. The sweep points, sensitivity runs and bounds
  are the dicts ``config._set_path`` produces and the variants are the ones
  ``config.merge_run_dicts`` produces, the two functions SP1 step 1 changes. Resolved
  inputs are parsed and unit-converted, never integrated, so these digests do not
  depend on the numeric environment. They are never recaptured: a digest that moves
  means a shipped run resolves differently.
- **Output capture** (output_capture.json and output_summary.md in the same directory;
  tests in tests/test_planar_pipeline.py): what the fixed-guidance fast experiment of
  that file (``fast_experiment``: pad, silo_cold and silo_failed of silo_screening_2d
  with two energy-only sensitivity cases) writes. Structure, compared in every
  environment: the files written, every key path of metrics.json (per run and outside
  the runs), the top-level keys of resolved_config.yaml and the header of every CSV
  (time series and events). Content, compared only in the capture environment (the
  golden 1-D rule, golden_1d_support.exact_tier_status: the runs integrate at rtol
  1e-10, so printed residuals change with the numeric stack): the sha256 of summary.md
  after ``golden_1d_support.normalise_summary`` (the timestamp and git label of the
  title replaced by a placeholder, the Timestamp, Git and Git error bullets dropped;
  the summary holds no wall-clock time and no path). output_summary.md is that
  normalised text, kept so that a changed digest can be read as a diff. SP1 steps 2 and
  3 add planar metric keys and summary rows on purpose: each recaptures the outputs
  (``--write outputs``) and lists its additions in its commit message; step 7's gate
  is "unchanged apart from those additions". The capture file records the git state
  it was taken in (``captured_at``, ``capture_provenance``): the step 1 capture ran
  the exported sources of REFERENCE_COMMIT (``launchsim_from_checkout`` false, the
  export below with ``--write outputs``); a recapture runs the recapturing step's own
  code, so its record names that step's checkout and not REFERENCE_COMMIT.

Check or recapture, from the repository root::

    uv run python tests/planar_pin_support.py                  # compare both pins
    uv run python tests/planar_pin_support.py --write outputs  # recapture the outputs
    uv run python tests/planar_pin_support.py --write digests --force

The script reports the launchsim sources it ran (``launchsim.__file__``). To compare
against a pristine checkout, export the reference sources and put them first on the
path (the experiments and vehicle files are read from this checkout, where no SP1 step
may edit them)::

    git archive c587a08 src | tar -x -C <dir>
    PYTHONPATH=<dir>/src uv run python tests/planar_pin_support.py

The fast experiment is built by tests/test_planar_pipeline.py (``fast_experiment``, the
function behind its ``fast_run`` fixture), loaded by path, so the script and the tests
capture the same runs.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import json
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PIN_DIR = REPO_ROOT / "tests" / "data" / "planar_pins"
DIGESTS_FILE = PIN_DIR / "resolved_digests.json"
CAPTURE_FILE = PIN_DIR / "output_capture.json"
SUMMARY_FILE = PIN_DIR / "output_summary.md"
REFERENCE_COMMIT = "c587a08"
"""The commit whose untouched sources produced the resolved digests (never recaptured,
so their file records it as ``reference_commit``) and the first output capture, that of
SP1 step 1 (its src/, tests/, experiments/, configs/, pyproject.toml and uv.lock equal
those of 2eebcae, the Phase 2 handoff commit). A later output capture comes from the
code of the step that recaptures it and records its own git state (``captured_at``,
``capture_provenance``), never this constant."""
PINNED_EXPERIMENTS: tuple[str, ...] = (
    "calibration_f9_2d",
    "silo_screening_2d",
    "silo_bridge_2d_readme",
    "guidance_trigger_2d",
)
"""The four planar experiments shipped at REFERENCE_COMMIT (experiments/<name>.yaml)."""
RUN_DIGEST_KEY = "run"
VEHICLE_DIGEST_KEY = "vehicle"
LIST_SEGMENT = "[]"
"""Key-path segment standing for every item of a list (``key_paths``)."""
METRICS_NAME = "metrics.json"
RESOLVED_CONFIG_NAME = "resolved_config.yaml"
SUMMARY_NAME = "summary.md"
TIMESERIES_NAME = "timeseries.csv"
EVENTS_NAME = "events.csv"
RUNS_KEY = "runs"
MAX_DIFF_LINES = 60
"""Lines of a summary diff shown in a failure message."""


def load_sibling(name: str) -> ModuleType:
    """A module of this directory (tests/<name>.py), loaded by path and cached in
    ``sys.modules``, so it resolves under any pytest import mode and from a script."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gs = load_sibling("golden_1d_support")


# ------------------------------------------------------------------ resolved digests


def dict_digest(data: Mapping[str, Any]) -> str:
    """sha256 hex digest of ``json.dumps(data)`` (UTF-8), key order kept: the
    serialisation of test_phase1_resolved_run_dicts_are_byte_identical."""
    return hashlib.sha256(json.dumps(data).encode("utf-8")).hexdigest()


def resolved_runs(resolved: Any) -> dict[str, Any]:
    """Every ResolvedRun of a ResolvedExperiment, keyed by a label that says where it
    comes from: ``run:<name>`` (baseline, variants), ``sweep_<k>:<point>`` and
    ``sweep_<k>:<point>__<baseline>`` (a point and its paired baseline),
    ``sens:<label>``, ``bound:<bound>:<run>`` (each re-run and the paired baseline),
    ``case:<name>`` and, for an experiment with an offload block (SP1 step 7; the first
    shipped ones arrived in step 8), the start of every offload case: ``offload_sweep_<k>:
    <start>`` (a case a sweep names, at each point), ``offload:<start>`` (a case of the
    block, then its paired pad's start) and ``offload_sens:<arm>`` (a sensitivity arm,
    then ``offload_sens:<arm>:<pad>``, its perturbed pad), in the order of
    ``sim.every_resolved_run``. The four PINNED_EXPERIMENTS declare no offload block, so
    their inventory and digests are unchanged; the offload attributes are read with a
    default so the helper still runs against REFERENCE_COMMIT's sources, which predate
    them. Raises ValueError on a repeated label."""
    out: dict[str, Any] = {}

    def add(label: str, run: Any) -> None:
        if label in out:
            raise ValueError(f"label {label!r} used twice")
        out[label] = run

    for name, run in resolved.runs.items():
        add(f"run:{name}", run)
    for points in resolved.sweeps:
        for point in points:
            add(f"sweep_{point.sweep_index}:{point.run.name}", point.run)
            if point.paired_baseline is not None:
                paired = point.paired_baseline
                add(f"sweep_{point.sweep_index}:{paired.name}", paired)
    for case in resolved.sensitivity:
        add(f"sens:{case.run.name}", case.run)
    for bound in resolved.bounds:
        for run in (*bound.runs.values(), bound.baseline):
            add(f"bound:{bound.name}:{run.name}", run)
    for name, run in resolved.cases.items():
        add(f"case:{name}", run)
    for points in resolved.sweeps:
        for point in points:
            for case in getattr(point, "offload", ()):
                add(f"offload_sweep_{point.sweep_index}:{case.start.name}", case.start)
    block = getattr(resolved, "offload", None)
    if block is not None:
        for case in block.cases:
            add(f"offload:{case.start.name}", case.start)
            if case.pad_start is not None:
                add(f"offload:{case.pad_start.name}", case.pad_start)
        for arm in block.arms:
            add(f"offload_sens:{arm.start.name}", arm.start)
            if arm.pad_perturbed:
                add(f"offload_sens:{arm.start.name}:{arm.pad.name}", arm.pad)
    return out


def resolved_digests(resolved: Any) -> dict[str, dict[str, str]]:
    """label -> {"run": digest of run_dict, "vehicle": digest of vehicle_dict} for every
    run of ``resolved_runs``."""
    return {
        label: {
            RUN_DIGEST_KEY: dict_digest(run.run_dict),
            VEHICLE_DIGEST_KEY: dict_digest(run.vehicle_dict),
        }
        for label, run in resolved_runs(resolved).items()
    }


def experiment_path(repo_root: Path, name: str) -> Path:
    """experiments/<name>.yaml under ``repo_root``."""
    return repo_root / "experiments" / f"{name}.yaml"


def shipped_digests(repo_root: Path) -> dict[str, dict[str, dict[str, str]]]:
    """``resolved_digests`` of every PINNED_EXPERIMENTS file, resolved the way the CLI
    does (``cli.load_experiment``)."""
    from launchsim import cli

    return {
        name: resolved_digests(cli.load_experiment(experiment_path(repo_root, name)))
        for name in PINNED_EXPERIMENTS
    }


def compare_digests(
    actual: Mapping[str, Mapping[str, str]], expected: Mapping[str, Mapping[str, str]]
) -> list[str]:
    """Differences between two ``resolved_digests`` maps of one experiment: runs that
    are missing, new or out of order, and run or vehicle dicts that changed."""
    out = [f"{label}: no longer resolved" for label in expected if label not in actual]
    out += [f"{label}: not in the pin" for label in actual if label not in expected]
    for label, digests in expected.items():
        for key, digest in digests.items():
            if label in actual and actual[label].get(key) != digest:
                out.append(f"{label}: the {key} dict changed")
    if not out and list(actual) != list(expected):
        out.append("the order of the resolved runs changed")
    return out


# -------------------------------------------------------------------- output capture


def key_paths(node: Any, prefix: str = "") -> list[str]:
    """Dotted path of every dict key under ``node``, in first-seen order, each once. The
    items of a list share the segment LIST_SEGMENT, so a list of records contributes the
    union of its records' keys; values are not part of the result."""
    seen: dict[str, None] = {}

    def walk(item: Any, path: str) -> None:
        if isinstance(item, dict):
            for key, value in item.items():
                child = f"{path}.{key}" if path else str(key)
                seen.setdefault(child, None)
                walk(value, child)
        elif isinstance(item, list):
            for value in item:
                walk(value, f"{path}.{LIST_SEGMENT}" if path else LIST_SEGMENT)

    walk(node, prefix)
    return list(seen)


def csv_header(path: Path) -> list[str]:
    """The column names of a CSV file written by results_io (its first line)."""
    with path.open(encoding="utf-8", newline="") as fh:
        return fh.readline().rstrip("\r\n").split(",")


def normalised_summary(out_dir: Path) -> str:
    """summary.md of a run directory without its provenance (see the module docstring)."""
    return gs.normalise_summary((out_dir / SUMMARY_NAME).read_text(encoding="utf-8"))


def output_structure(out_dir: Path) -> dict[str, Any]:
    """The environment-independent part of the capture of one experiment run directory:
    ``files`` (sorted relative POSIX paths), ``metrics_keys`` (key paths of metrics.json
    outside its ``runs``), ``resolved_config_keys`` (top-level keys of
    resolved_config.yaml) and, per run, ``metrics_keys`` (key paths of its metrics
    record), ``timeseries_columns`` and ``event_columns``."""
    import yaml

    metrics = json.loads((out_dir / METRICS_NAME).read_text(encoding="utf-8"))
    config = yaml.safe_load((out_dir / RESOLVED_CONFIG_NAME).read_text(encoding="utf-8"))
    runs = {
        name: {
            "metrics_keys": key_paths(record),
            "timeseries_columns": csv_header(out_dir / name / TIMESERIES_NAME),
            "event_columns": csv_header(out_dir / name / EVENTS_NAME),
        }
        for name, record in metrics[RUNS_KEY].items()
    }
    return {
        "files": sorted(
            p.relative_to(out_dir).as_posix() for p in out_dir.rglob("*") if p.is_file()
        ),
        "metrics_keys": key_paths({k: v for k, v in metrics.items() if k != RUNS_KEY}),
        "resolved_config_keys": list(config),
        RUNS_KEY: runs,
    }


def output_capture(out_dir: Path) -> dict[str, Any]:
    """The full capture of one experiment run directory: ``output_structure`` plus
    ``summary_sha256``, the digest of ``normalised_summary``."""
    return {
        **output_structure(out_dir),
        "summary_sha256": gs.text_digest(normalised_summary(out_dir)),
    }


def compare_structure(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> list[str]:
    """Differences between an ``output_structure`` and the captured one, each naming the
    list and the entries that appeared, disappeared or moved."""
    out: list[str] = []

    def lists(where: str, got: list[str], want: list[str]) -> None:
        if got == want:
            return
        added = [x for x in got if x not in want]
        removed = [x for x in want if x not in got]
        if added or removed:
            out.append(f"{where}: added {added}, removed {removed}")
        else:
            out.append(f"{where}: order changed")

    for key in ("files", "metrics_keys", "resolved_config_keys"):
        lists(key, actual[key], expected[key])
    lists("runs", list(actual[RUNS_KEY]), list(expected[RUNS_KEY]))
    for name, want in expected[RUNS_KEY].items():
        got = actual[RUNS_KEY].get(name)
        if got is None:
            continue
        for key in ("metrics_keys", "timeseries_columns", "event_columns"):
            lists(f"runs.{name}.{key}", got[key], want[key])
    return out


def summary_diff(actual: str, expected: str) -> str:
    """A unified diff (at most MAX_DIFF_LINES lines) of two normalised summaries."""
    lines = list(
        difflib.unified_diff(
            expected.split("\n"), actual.split("\n"), "captured", "current", lineterm="", n=0
        )
    )
    more = len(lines) - MAX_DIFF_LINES
    tail = [f"... and {more} more lines"] if more > 0 else []
    return "\n".join([*lines[:MAX_DIFF_LINES], *tail])


def read_json(path: Path) -> dict[str, Any]:
    """A pin file, parsed."""
    return json.loads(path.read_text(encoding="utf-8"))


def read_summary_pin() -> str:
    """The captured normalised summary (LF line endings)."""
    return SUMMARY_FILE.read_text(encoding="utf-8").replace("\r\n", "\n")


# ---------------------------------------------------------------- check and recapture


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _write_json(path: Path, data: Any) -> None:
    _write_text(path, json.dumps(data, indent=1) + "\n")


def _run_fast_experiment(repo_root: Path, results_root: Path) -> Path:
    """Run tests/test_planar_pipeline.py's fast experiment into ``results_root`` (plots
    off) and return its run directory."""
    from launchsim import sim

    resolved = load_sibling("test_planar_pipeline").fast_experiment(repo_root)
    _er, out_dir = sim.run_experiment(resolved, results_root, plots=False, repo_root=repo_root)
    return out_dir


def _digest_record(repo_root: Path) -> dict[str, Any]:
    return {
        "_note": (
            "sha256 of json.dumps(run_dict) and json.dumps(vehicle_dict), key order kept, "
            "of every run the four shipped planar experiments resolve (baseline, "
            "variants, sweep points and paired baselines, sensitivity runs, bound runs "
            "and paired baselines, calibration cases). Captured from the untouched code "
            "before SP1 step 1 changed config.merge_run_dicts and config._set_path; "
            "never recaptured. See tests/planar_pin_support.py."
        ),
        "reference_commit": REFERENCE_COMMIT,
        "experiments": shipped_digests(repo_root),
    }


def capture_provenance(repo_root: Path) -> dict[str, Any]:
    """The git state an output capture is taken in, read when it is taken: ``git`` (the
    12-character hash of the checkout's HEAD, or ``no-git``/``unborn``), ``dirty``
    (uncommitted changes outside results/; None when git status failed), both from
    ``results_io.git_info``, and ``launchsim_from_checkout`` (False when the launchsim
    sources that ran are not ``repo_root``/src, as in a capture with an exported
    reference commit put first on the path: ``git`` then names the checkout that holds
    the experiments and tests, not the sources)."""
    import launchsim
    from launchsim import sim

    info = sim.git_info(repo_root)
    sources = Path(launchsim.__file__).resolve().parent
    return {
        "git": info["hash"],
        "dirty": info["dirty"],
        "launchsim_from_checkout": sources == (repo_root / "src" / "launchsim").resolve(),
    }


def _capture_record(out_dir: Path, repo_root: Path) -> dict[str, Any]:
    return {
        "_note": (
            "What the fixed-guidance fast experiment of tests/test_planar_pipeline.py "
            "(fast_experiment: pad, silo_cold, silo_failed) writes: files, metrics.json "
            "key paths, CSV columns, and the sha256 of the provenance-free summary.md "
            "(output_summary.md beside this file is that text). Structure is compared "
            "in every environment, the summary digest only in the capture environment. "
            "captured_at is the git state at this capture (HEAD of the checkout, "
            "uncommitted changes, whether launchsim ran from the checkout's src). "
            "See tests/planar_pin_support.py."
        ),
        "captured_at": capture_provenance(repo_root),
        "environment": gs.environment(),
        **output_capture(out_dir),
    }


def check(repo_root: Path) -> list[str]:
    """Compare both pins with the sources on the path; returns the differences."""
    problems: list[str] = []
    pinned = read_json(DIGESTS_FILE)["experiments"]
    actual = shipped_digests(repo_root)
    for name in PINNED_EXPERIMENTS:
        problems += [f"{name}: {p}" for p in compare_digests(actual[name], pinned[name])]
    capture = read_json(CAPTURE_FILE)
    with tempfile.TemporaryDirectory(prefix="planar_pins_") as tmp:
        out_dir = _run_fast_experiment(repo_root, Path(tmp))
        problems += compare_structure(output_structure(out_dir), capture)
        summary = normalised_summary(out_dir)
    mismatch = gs.environment_mismatch(capture["environment"])
    if mismatch:
        print("summary digest not compared (not the capture environment): " + "; ".join(mismatch))
    elif gs.text_digest(summary) != capture["summary_sha256"]:
        problems.append("summary.md changed:\n" + summary_diff(summary, read_summary_pin()))
    return problems


def write(repo_root: Path, what: str, force: bool) -> None:
    """Recapture the digests, the outputs or both (``what``: digests, outputs, all). The
    digests file is replaced only with ``force``: it pins the code of REFERENCE_COMMIT."""
    if what in ("digests", "all"):
        if DIGESTS_FILE.exists() and not force:
            raise SystemExit(
                f"{DIGESTS_FILE} exists: it pins the sources of {REFERENCE_COMMIT} and is "
                "not recaptured (--force replaces it; run it on those sources only)"
            )
        _write_json(DIGESTS_FILE, _digest_record(repo_root))
        print(f"wrote {DIGESTS_FILE}")
    if what in ("outputs", "all"):
        with tempfile.TemporaryDirectory(prefix="planar_pins_") as tmp:
            out_dir = _run_fast_experiment(repo_root, Path(tmp))
            _write_json(CAPTURE_FILE, _capture_record(out_dir, repo_root))
            _write_text(SUMMARY_FILE, normalised_summary(out_dir))
        print(f"wrote {CAPTURE_FILE}")
        print(f"wrote {SUMMARY_FILE}")


def main(argv: list[str] | None = None) -> int:
    """Command line: compare the pins (default) or recapture them (``--write``)."""
    import launchsim

    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--write", choices=("digests", "outputs", "all"), default=None)
    parser.add_argument("--force", action="store_true", help="replace the digests file")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    print(f"launchsim sources: {Path(launchsim.__file__).resolve().parent}")
    if args.write is not None:
        write(args.repo_root, args.write, args.force)
        return 0
    problems = check(args.repo_root)
    for problem in problems:
        print(problem)
    print("pins match" if not problems else f"{len(problems)} difference(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
