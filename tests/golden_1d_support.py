"""Golden capture and comparison for the 1-D reference (plan build step 15).

The 1-D model must stay byte-for-byte reproducible through the Phase 2 refactors. Two
golden sets pin it, each captured from the CLI with sources equal to REFERENCE_COMMIT:

- ``silo_screening_1d``: the Phase 1 experiment (experiments/silo_screening_1d.yaml),
  run and sweep (plan section 4);
- ``vertical_1d_paths``: a supplementary experiment (tests/data/golden/inputs/
  vertical_1d_paths.yaml) for the vertical_1d paths the Phase 1 experiment never
  reaches: staging and stage 2 (end all_burnout), the post-burnout coast to apex, a pad
  no_liftoff, a drive_limit stop on the track, and ignition after release (an upward
  pre-ignition coast, and a fall-back through apex with a turnaround).

This module holds everything test_golden_1d.py needs besides the test bodies: which
output files are pinned, how they are normalised (timestamp and git provenance
stripped, nothing else), a pickle-free dump of the in-memory objects the files do not
carry (loss budgets, assist energy budgets, assumptions, sensitivity rows, sweep
points), the plot file names, and two comparison tiers:

- tolerant (always on): rel 1e-12 / abs 1e-9 on floats in the JSON records and object
  dumps; exact on strings, keys and key order, ints, bools, CSV headers, the sign of
  v_mps (sign of zero included) and the resolved inputs (resolved_config, run and
  vehicle dicts, sweep overrides), which are parsed and unit-converted, never
  integrated. It is NOT an environment-robust safety net. It absorbs only
  formatting-level and last-few-ulp differences in JSON floats. The runs integrate at
  rtol 1e-10, so any change of even one ulp in the floating-point path (a numpy,
  scipy or python upgrade, another CPU, a reordered sum) moves the adaptive steps and
  the integrated metrics by more than 1e-12 relative: a 1e-15 relative change of mu
  already moves stage1_burnout_alt_m by 1.4e-12. CSV cells are printed at 12
  significant digits (%.12g), whose spacing (at least 1e-12 relative) is not below
  REL_TOL, and summary cells are compared as text, so CSV and summary files are
  effectively exact at their printed precision. After a dependency or platform
  change that alters floating-point results, expect both tiers to fail; that alone is
  not a physics regression, and the fix is never a looser tolerance.
- exact (only in the capture environment, EXACT_ENV_KEYS of the manifest; skipped with
  the reason otherwise, or failed when REQUIRE_EXACT_ENV_VAR=1): a sha256 digest of
  the provenance-stripped, LF-normalised text of every non-PNG output file (byte
  identity, formatting included), and the object dumps with floats compared by repr
  (every bit, the sign of zero included). Only this tier catches a sub-tolerance
  change such as a reordered sum, so the step 16-17 gates run it with
  REQUIRE_EXACT_ENV_VAR=1 (0 skipped).

It only uses the stable entry points (``cli.load_experiment``, ``sim.run_experiment``,
``sim.run_sweep``) and attributes of the dataclasses they return, never helper
functions that the sim.py split may move.

Recapture is valid only from a checkout whose GUARDED_PATHS equal REFERENCE_COMMIT
(104ea07, the Phase 1 commit) with no uncommitted change in them; capture() checks
both and refuses otherwise, so the golden can never be recaptured from modified
source. It also refuses to replace an existing golden set without ``--force``, to
change the recorded environment without ``--allow-env-change``, and to use an
experiment input whose sha256 differs from the existing manifest's (delete the set
first, with the user's approval of a documented golden change)::

    uv run python -m launchsim run <experiment yaml> --results-root <S>
    uv run python -m launchsim sweep <experiment yaml> --results-root <S>   # silo set only
    uv run python tests/golden_1d_support.py --set <name> \\
        --run-dir <S>/<name>/<ts1> [--sweep-dir <S>/<name>/<ts2>] \\
        --scratch <S>/inprocess [--force] [--allow-env-change]

The CLI runs must be made with plots on (their PNG names are recorded). The capture
re-runs the entry points in-process, requires their files to equal the CLI files byte
for byte (after provenance stripping), and only then writes tests/data/golden/<name>.

A new environment (for example after a uv.lock upgrade, which is itself a guarded path)
can only be captured by running the REFERENCE_COMMIT sources under the new
environment's interpreter: check them out in a git worktree of 104ea07, copy this
helper and the golden inputs into it, and run the commands above there with the new
environment's interpreter (PYTHONPATH=<worktree>/src) and ``--force
--allow-env-change``, only with the user's approval of a documented golden change.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import io
import json
import math
import platform
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
import scipy
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = REPO_ROOT / "tests" / "data" / "golden"
MANIFEST_NAME = "manifest.json"
EXPERIMENT_SECTION = "experiment"
SWEEP_SECTION = "sweep"
SECTIONS: tuple[str, ...] = (EXPERIMENT_SECTION, SWEEP_SECTION)
OBJECTS_NAME = "objects.json"

# Comparator tolerances (plan section 8, "Golden 1-D").
REL_TOL = 1e-12
ABS_TOL = 1e-9
# CSV columns whose sign is pinned exactly on every row (events and time series keep a
# signed 1-D speed; the float tolerance alone would accept a flipped sign on a speed
# below ABS_TOL, such as the apex row of a fall-back).
SIGNED_COLUMNS: frozenset[str] = frozenset({"v_mps"})
# Subtrees holding resolved inputs (parsed from YAML and unit-converted, never
# integrated): compared exactly even in the tolerant tier.
EXACT_SUBTREES: frozenset[str] = frozenset({"run_dict", "vehicle_dict", "overrides"})
# Top-level keys of metrics.json / resolved_config.yaml that change on every run.
PROVENANCE_KEYS: tuple[str, ...] = ("timestamp_utc", "git")
# Summary lines that carry the timestamp or the git state. A "- Git error:" bullet may
# span several lines (git's own multi-line message); its continuation lines run to the
# next blank line or the next bullet.
PROVENANCE_LINE_PREFIXES: tuple[str, ...] = ("- Timestamp (UTC):", "- Git:", "- Git error:")
GIT_ERROR_PREFIX = "- Git error:"
BULLET_PREFIX = "- "
TITLE_PROVENANCE_MARK = " ("  # "# <experiment> (<timestamp>, git <label>)"
NORMALISED_TITLE_SUFFIX = " (<timestamp>, git <label>)"
# Text-level provenance of the record files, as sim.write_json (indent 2) and
# sim.write_yaml (block style) lay it out; each must occur exactly once per file.
RECORD_PROVENANCE: dict[str, tuple[tuple[str, re.Pattern[str]], ...]] = {
    ".json": (
        ("timestamp_utc", re.compile(r'^  "timestamp_utc": "[^"\n]*",\n', re.MULTILINE)),
        ("git", re.compile(r'^  "git": \{\n(?:    [^\n]*\n)*?  \},\n', re.MULTILINE)),
    ),
    ".yaml": (
        ("timestamp_utc", re.compile(r"^timestamp_utc: [^\n]*\n", re.MULTILINE)),
        ("git", re.compile(r"^git:\n(?:(?: [^\n]*)?\n)*?(?=[^ \n])", re.MULTILINE)),
    ),
}
PROVENANCE_PLACEHOLDER = "<provenance:{key}>\n"
# Output files excluded from the digests (rendered images; not reproducible bytes).
DIGEST_EXCLUDED_SUFFIXES: tuple[str, ...] = (".png",)

# Exact tier: the commit whose sources the golden reflects, the paths that must equal it
# for a capture, and the environment keys that must match the manifest for the exact
# tier to run (the full platform string is recorded but not gated: an OS build number
# alone would switch the tier off).
REFERENCE_COMMIT = "104ea07"
GUARDED_PATHS: tuple[str, ...] = ("src", "configs", "experiments", "pyproject.toml", "uv.lock")
EXACT_ENV_KEYS: tuple[str, ...] = (
    "python",
    "numpy",
    "scipy",
    "pandas",
    "pyyaml",
    "system",
    "machine",
)
DIGESTS_KEY = "digests"
# Manifest keys: the sorted PNG paths of the CLI run (names only; the bytes are not
# reproducible) and the sha256 of the experiment input's LF text.
PNG_KEY = "png_files"
INPUT_DIGEST_KEY = "experiment_sha256"
PNG_SUFFIX = ".png"
# Set to "1" to make the exact tier fail instead of skip when the environment differs
# (the step 16-17 byte-identity gates).
REQUIRE_EXACT_ENV_VAR = "LAUNCHSIM_REQUIRE_EXACT_GOLDEN"
REQUIRE_EXACT_VALUE = "1"
TIER_NOTE = (
    "tolerant tier: rel/abs on JSON floats only; CSV (%.12g) and summary cells are "
    "effectively exact at their printed precision, and integrated results move by more "
    "than rel 1e-12 under any 1-ulp change of the floating-point path (rtol 1e-10), so "
    "both tiers are expected to fail after a dependency or platform change that alters "
    "floating-point results; never loosen the tolerances. Exact tier: runs only when "
    f"exact_env_keys match, skips otherwise unless {REQUIRE_EXACT_ENV_VAR}="
    f"{REQUIRE_EXACT_VALUE} (then it fails)."
)
SUMMARY_SWEEPS: tuple[int, ...] = (1,)


@dataclass(frozen=True)
class GoldenSet:
    """One golden set: ``name`` (the experiment name, the golden directory under
    GOLDEN_ROOT and the results subdirectory), the experiment input file, the runs whose
    timeseries.csv is pinned as a file (all others are pinned by digest only) and
    whether the set includes the sweep."""

    name: str
    experiment_file: Path
    timeseries_runs: tuple[str, ...]
    has_sweep: bool

    @property
    def golden_dir(self) -> Path:
        """tests/data/golden/<name>."""
        return GOLDEN_ROOT / self.name

    @property
    def sections(self) -> tuple[str, ...]:
        """The sections of this set: experiment, and sweep when the set has one."""
        return SECTIONS if self.has_sweep else (EXPERIMENT_SECTION,)


# The selection pinned for the Phase 1 experiment (plan section 4): every run's events,
# the time series of the two runs the plan names, the experiment summary and records,
# the sweep index of every sweep, every sweep point's metrics and events, and the
# summaries of sweep_1.
SILO_SET = GoldenSet(
    name="silo_screening_1d",
    experiment_file=REPO_ROOT / "experiments" / "silo_screening_1d.yaml",
    timeseries_runs=("silo_cold", "silo_failed"),
    has_sweep=True,
)
# Supplementary paths (see the module docstring); its input lives next to the golden.
PATHS_SET = GoldenSet(
    name="vertical_1d_paths",
    experiment_file=GOLDEN_ROOT / "inputs" / "vertical_1d_paths.yaml",
    timeseries_runs=("pad_no_liftoff", "silo_drive_limit", "silo_fallback_ign"),
    has_sweep=False,
)
GOLDEN_SETS: dict[str, GoldenSet] = {g.name: g for g in (SILO_SET, PATHS_SET)}

Kind = Literal["json", "yaml", "summary", "csv"]
GOLDEN_SUFFIX: dict[str, str] = {"json": ".json", "yaml": ".json", "summary": ".md", "csv": ".csv"}


# ----------------------------------------------------------------------- normalising


def normalise_summary(text: str) -> str:
    """summary.md text without its provenance: the title's ``(<timestamp>, git <label>)``
    becomes a fixed placeholder and the Timestamp/Git/Git error bullets are dropped.
    A multi-line Git error bullet is dropped whole (its continuation lines run to the
    next blank line or bullet). Line endings are normalised to LF; nothing else
    changes."""
    out: list[str] = []
    in_git_error = False
    for i, line in enumerate(text.replace("\r\n", "\n").split("\n")):
        if in_git_error and line and not line.startswith(BULLET_PREFIX):
            continue
        in_git_error = line.startswith(GIT_ERROR_PREFIX)
        if line.startswith(PROVENANCE_LINE_PREFIXES):
            continue
        if i == 0 and line.startswith("# ") and line.endswith(")") and ", git " in line:
            line = line[: line.index(TITLE_PROVENANCE_MARK)] + NORMALISED_TITLE_SUFFIX
        out.append(line)
    return "\n".join(out)


def normalise_record_text(text: str, suffix: str) -> str:
    """The text of a metrics.json (suffix ".json") or resolved_config.yaml (".yaml") with
    its top-level timestamp_utc and git entries replaced by fixed placeholder lines, byte
    for byte otherwise (LF line endings). Raises ValueError when an entry does not occur
    exactly once in the layout RECORD_PROVENANCE expects (a writer format change)."""
    text = text.replace("\r\n", "\n")
    for key, pattern in RECORD_PROVENANCE[suffix]:
        text, count = pattern.subn(PROVENANCE_PLACEHOLDER.format(key=key), text)
        if count != 1:
            raise ValueError(f"provenance entry {key!r} found {count} times, expected 1")
    return text


def normalise_output_text(rel: str, text: str) -> str:
    """Any text output file in its provenance-free, LF form, chosen by suffix: records
    via normalise_record_text, summaries via normalise_summary, everything else (CSV)
    verbatim."""
    suffix = Path(rel).suffix
    if suffix in RECORD_PROVENANCE:
        return normalise_record_text(text, suffix)
    if suffix == ".md":
        return normalise_summary(text)
    return text.replace("\r\n", "\n")


def text_digest(text: str) -> str:
    """sha256 hex digest of a text's UTF-8 bytes."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def output_digests(run_dir: Path) -> dict[str, str]:
    """Run-directory-relative POSIX path -> text_digest of normalise_output_text, for
    every file under ``run_dir`` except DIGEST_EXCLUDED_SUFFIXES, sorted by path. A file
    whose provenance cannot be normalised gets the digest of an error marker, so it
    never matches."""
    out: dict[str, str] = {}
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file() or path.suffix in DIGEST_EXCLUDED_SUFFIXES:
            continue
        rel = path.relative_to(run_dir).as_posix()
        try:
            text = normalise_output_text(rel, path.read_text(encoding="utf-8"))
        except ValueError as exc:
            text = f"<unnormalisable: {exc}>"
        out[rel] = text_digest(text)
    return out


def png_files(run_dir: Path) -> list[str]:
    """Sorted run-directory-relative POSIX paths of every PNG under ``run_dir`` (the
    plot names are pinned; their bytes are not reproducible)."""
    return sorted(
        p.relative_to(run_dir).as_posix()
        for p in run_dir.rglob("*")
        if p.is_file() and p.suffix == PNG_SUFFIX
    )


def input_digest(path: Path) -> str:
    """text_digest of an experiment input file's LF-normalised text."""
    return text_digest(path.read_text(encoding="utf-8").replace("\r\n", "\n"))


def compare_digests(actual: Mapping[str, str], expected: Mapping[str, str]) -> list[str]:
    """Differences between two output_digests maps: missing, extra and changed files."""
    out = [f"{rel}: missing" for rel in expected if rel not in actual]
    out += [f"{rel}: not in the golden set" for rel in actual if rel not in expected]
    out += [
        f"{rel}: content changed"
        for rel, digest in expected.items()
        if rel in actual and actual[rel] != digest
    ]
    return out


def environment() -> dict[str, str]:
    """The numeric stack and platform the outputs depend on (manifest "environment")."""
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "pandas": pd.__version__,
        "pyyaml": yaml.__version__,
        "system": platform.system(),
        "machine": platform.machine(),
        "platform": platform.platform(),
    }


def environment_mismatch(recorded: Mapping[str, str]) -> list[str]:
    """EXACT_ENV_KEYS whose current value differs from ``recorded`` (the manifest's
    environment), as "key: recorded -> current" messages; empty when the exact tier
    applies."""
    current = environment()
    return [
        f"{key}: {recorded.get(key)} -> {current[key]}"
        for key in EXACT_ENV_KEYS
        if recorded.get(key) != current[key]
    ]


ExactStatus = Literal["run", "skip", "fail"]


def exact_tier_status(
    recorded: Mapping[str, str], environ: Mapping[str, str]
) -> tuple[ExactStatus, str]:
    """Whether the exact tier runs against a manifest's recorded environment: ("run",
    "") when EXACT_ENV_KEYS match; otherwise ("skip", reason), or ("fail", reason) when
    ``environ`` (os.environ) sets REQUIRE_EXACT_ENV_VAR to REQUIRE_EXACT_VALUE."""
    mismatch = environment_mismatch(recorded)
    if not mismatch:
        return "run", ""
    reason = "exact golden tier needs the capture environment: " + "; ".join(mismatch)
    if environ.get(REQUIRE_EXACT_ENV_VAR) == REQUIRE_EXACT_VALUE:
        return "fail", f"{reason} ({REQUIRE_EXACT_ENV_VAR}={REQUIRE_EXACT_VALUE} requires it)"
    return "skip", f"{reason} (set {REQUIRE_EXACT_ENV_VAR}={REQUIRE_EXACT_VALUE} to fail instead)"


def drop_provenance(record: Mapping[str, Any]) -> dict[str, Any]:
    """A top-level record (metrics.json, resolved_config.yaml) without PROVENANCE_KEYS,
    key order kept."""
    return {k: v for k, v in record.items() if k not in PROVENANCE_KEYS}


def load_normalised(kind: Kind, path: Path) -> Any:
    """Read one output or golden file into its comparable form: JSON and YAML records
    parsed (provenance dropped), summaries normalised text, CSV raw text."""
    text = path.read_text(encoding="utf-8")
    if kind == "json":
        return drop_provenance(json.loads(text))
    if kind == "yaml":
        if path.suffix == ".json":  # a golden copy is stored as JSON
            return json.loads(text)
        return drop_provenance(yaml.safe_load(text))
    if kind == "summary":
        return normalise_summary(text)
    return text.replace("\r\n", "\n")


def plain(obj: Any) -> Any:
    """A pickle-free, JSON-ready copy of a nested value. Unlike the results writer it
    keeps non-finite floats distinguishable: NaN and +/-inf become the strings "NaN",
    "Infinity", "-Infinity" (pd.NA / pd.NaT become None). Dataclasses become dicts in
    field order, numpy scalars Python numbers, tuples lists, Paths POSIX strings."""
    if obj is pd.NA or obj is pd.NaT:
        return None
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: plain(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, Mapping):
        return {str(k): plain(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [plain(v) for v in obj]
    if isinstance(obj, bool | np.bool_):
        return bool(obj)
    if isinstance(obj, int | np.integer):
        return int(obj)
    if isinstance(obj, float | np.floating):
        x = float(obj)
        if math.isnan(x):
            return "NaN"
        if math.isinf(x):
            return "Infinity" if x > 0 else "-Infinity"
        return x
    if isinstance(obj, np.ndarray):
        return plain(obj.tolist())
    if isinstance(obj, Path):
        return obj.as_posix()
    if obj is None or isinstance(obj, str):
        return obj
    raise TypeError(f"golden dump: unsupported type {type(obj).__name__}")


# ------------------------------------------------------------------- object dumps


def result_objects(result: Any) -> dict[str, Any]:
    """The pinned parts of a sim.Result: status, flags, every metric, the loss budget,
    the assist energy budget and the assumption list (time series and events are
    pinned as CSV files)."""
    return {
        "status": plain(result.status),
        "flags": plain(list(result.flags)),
        "metrics": plain(result.metrics),
        "loss_budget": plain(result.loss_budget),
        "assist_budget": plain(result.assist_budget),
        "assumptions": plain(list(result.assumptions)),
    }


def run_objects(rr: Any, base_vehicle_dict: Mapping[str, Any]) -> dict[str, Any]:
    """A sim.RunResult: name, resolved run dict, the vehicle dict when it differs from
    the experiment's, and result_objects."""
    vehicle = rr.resolved.vehicle_dict
    return {
        "name": rr.name,
        "run_dict": plain(rr.resolved.run_dict),
        "vehicle_dict": None if vehicle == base_vehicle_dict else plain(vehicle),
        "result": result_objects(rr.result),
    }


def sensitivity_objects(rows: Sequence[Any], base_vehicle_dict: Mapping[str, Any]) -> list[Any]:
    """Every sim.SensitivityRow field, in declaration order; the case run and the
    perturbed baseline (None for a run parameter) as run_objects."""
    out = []
    for row in rows:
        out.append(
            {
                "of": row.of,
                "param": row.param,
                "fraction": plain(row.fraction),
                "value_yaml_units": plain(row.value_yaml_units),
                "value_si": plain(row.value_si),
                "value_si_unit": row.value_si_unit,
                "is_vehicle_param": bool(row.is_vehicle_param),
                "result": run_objects(row.result, base_vehicle_dict),
                "comparison": plain(row.comparison),
                "baseline_perturbed": (
                    None
                    if row.baseline_perturbed is None
                    else run_objects(row.baseline_perturbed, base_vehicle_dict)
                ),
                "comparison_perturbed": plain(row.comparison_perturbed),
            }
        )
    return out


def experiment_objects(er: Any) -> dict[str, Any]:
    """The pinned parts of a sim.ExperimentResult (no timestamp or git)."""
    base_vehicle = er.baseline.resolved.vehicle_dict
    return {
        "experiment_name": er.experiment_name,
        "vehicle_name": er.vehicle_name,
        "baseline": er.baseline.name,
        "comparison_basis": er.comparison_basis,
        "sensitivity_note": er.sensitivity_note,
        "runs": {name: run_objects(rr, base_vehicle) for name, rr in er.runs.items()},
        "comparison": plain(er.comparison),
        "sensitivity": sensitivity_objects(er.sensitivity, base_vehicle),
    }


def sweep_objects(
    sweeps: Sequence[Any], root: Path, base_vehicle_dict: Mapping[str, Any]
) -> dict[str, Any]:
    """The pinned parts of every sim.SweepResult: index, parent run, axes and, per
    point, its indices, overrides, run directory (relative to the run root ``root``) and
    run_objects (vehicle dict only when it differs from ``base_vehicle_dict``) with the
    point's comparison."""
    out: dict[str, Any] = {}
    for sweep in sweeps:
        points = []
        for point, rr, comp, run_dir in zip(
            sweep.points, sweep.results, sweep.comparisons, sweep.run_dirs, strict=True
        ):
            points.append(
                {
                    "sweep_index": point.sweep_index,
                    "point_index": point.point_index,
                    "of": point.of,
                    "overrides": plain(point.overrides),
                    "run_dir": Path(run_dir).relative_to(root).as_posix(),
                    "run": run_objects(rr, base_vehicle_dict),
                    "comparison": plain(comp),
                }
            )
        out[f"sweep_{sweep.sweep_index}"] = {
            "sweep_index": sweep.sweep_index,
            "of": sweep.of,
            "axes": list(sweep.axes),
            "points": points,
        }
    return out


def section_objects(
    section: str, output: Any, run_dir: Path, base_vehicle_dict: Mapping[str, Any]
) -> Any:
    """The object dump of one section: experiment_objects of an ExperimentResult, or
    sweep_objects of a SweepResult list (``output``) written under ``run_dir``."""
    if section == EXPERIMENT_SECTION:
        return experiment_objects(output)
    return sweep_objects(output, run_dir, base_vehicle_dict)


# ------------------------------------------------------------------ file selection


def experiment_selection(
    run_dir: Path, timeseries_runs: Sequence[str]
) -> dict[str, tuple[Kind, Path]]:
    """Golden-relative path (without the golden suffix change) -> (kind, output file)
    for an experiment run directory: the records, the summary, every run's events and
    the time series of ``timeseries_runs``."""
    sel: dict[str, tuple[Kind, Path]] = {
        "metrics.json": ("json", run_dir / "metrics.json"),
        "resolved_config.yaml": ("yaml", run_dir / "resolved_config.yaml"),
        "summary.md": ("summary", run_dir / "summary.md"),
    }
    runs = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))["runs"]
    for name in runs:
        sel[f"{name}/events.csv"] = ("csv", run_dir / name / "events.csv")
    for name in timeseries_runs:
        sel[f"{name}/timeseries.csv"] = ("csv", run_dir / name / "timeseries.csv")
    return sel


def sweep_selection(run_dir: Path) -> dict[str, tuple[Kind, Path]]:
    """Golden-relative path -> (kind, output file) for a sweep run directory."""
    sel: dict[str, tuple[Kind, Path]] = {
        "summary.md": ("summary", run_dir / "summary.md"),
        "baseline/metrics.json": ("json", run_dir / "baseline" / "metrics.json"),
        "baseline/summary.md": ("summary", run_dir / "baseline" / "summary.md"),
        "baseline/events.csv": ("csv", run_dir / "baseline" / "events.csv"),
    }
    for sweep_dir in sorted(run_dir.glob("sweep_*")):
        rel = sweep_dir.name
        k = int(rel.split("_")[1])
        sel[f"{rel}/sweep_index.csv"] = ("csv", sweep_dir / "sweep_index.csv")
        for point in sorted(p for p in sweep_dir.iterdir() if p.is_dir()):
            sel[f"{rel}/{point.name}/metrics.json"] = ("json", point / "metrics.json")
            sel[f"{rel}/{point.name}/events.csv"] = ("csv", point / "events.csv")
            if k in SUMMARY_SWEEPS:
                sel[f"{rel}/{point.name}/summary.md"] = ("summary", point / "summary.md")
    return sel


def golden_name(rel: str, kind: Kind) -> str:
    """The golden file name of a selected output: YAML records are stored as JSON."""
    return str(Path(rel).with_suffix(GOLDEN_SUFFIX[kind]).as_posix())


# --------------------------------------------------------------------- comparison


def _is_float(x: Any) -> bool:
    return isinstance(x, float)


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= max(ABS_TOL, REL_TOL * max(abs(a), abs(b)))


def _same_bits(a: float, b: float) -> bool:
    """Exact float equality: repr is the shortest round-trip form, so equal reprs mean
    equal bits (the sign of zero included)."""
    return repr(a) == repr(b)


def compare_tree(actual: Any, expected: Any, where: str = "$", exact: bool = False) -> list[str]:
    """Differences between two plain trees (JSON-like values). Dict keys must match in
    order; lists in length; strings, None, bools and ints exactly; floats within
    rel REL_TOL / abs ABS_TOL (an int never equals a float), or bit for bit when
    ``exact`` is set or inside an EXACT_SUBTREES key (resolved inputs). Returns
    messages."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{where}: expected a mapping, got {type(actual).__name__}"]
        if list(actual) != list(expected):
            missing = [k for k in expected if k not in actual]
            extra = [k for k in actual if k not in expected]
            detail = f"missing {missing}, extra {extra}" if missing or extra else "order differs"
            return [f"{where}: keys differ ({detail})"]
        out: list[str] = []
        for key in expected:
            sub_exact = exact or key in EXACT_SUBTREES
            out += compare_tree(actual[key], expected[key], f"{where}.{key}", sub_exact)
        return out
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            got = len(actual) if isinstance(actual, list) else type(actual).__name__
            return [f"{where}: expected a list of {len(expected)}, got {got}"]
        out = []
        for i, (a, e) in enumerate(zip(actual, expected, strict=True)):
            out += compare_tree(a, e, f"{where}[{i}]", exact)
        return out
    if _is_float(expected):
        same = _same_bits if exact else _close
        if not _is_float(actual) or not same(actual, expected):
            return [f"{where}: {actual!r} != {expected!r}"]
        return []
    if type(actual) is not type(expected) or actual != expected:
        return [f"{where}: {actual!r} != {expected!r}"]
    return []


def _cell_float(cell: str) -> float | None:
    try:
        return float(cell)
    except ValueError:
        return None


def _sign(x: float) -> tuple[int, float]:
    """(-1, 0 or +1, sign bit as +/-1.0): zero is its own class and -0 differs from 0."""
    return (x > 0.0) - (x < 0.0), math.copysign(1.0, x)


def compare_csv(actual: str, expected: str, where: str) -> list[str]:
    """Differences between two CSV texts: header and row count exact; a cell that
    parses as a number on both sides within rel REL_TOL / abs ABS_TOL, and in
    SIGNED_COLUMNS also with exactly the same sign (-1, 0, +1, and the sign bit, so
    "-0" differs from "0"), so even a speed inside the absolute tolerance, such as the
    ~1e-14 m/s apex row of a fall-back, keeps its sign; every other cell (text, empty,
    nan, inf) exactly."""
    a_rows = list(csv.reader(io.StringIO(actual)))
    e_rows = list(csv.reader(io.StringIO(expected)))
    if not e_rows:
        return [] if not a_rows else [f"{where}: expected an empty file"]
    if not a_rows or a_rows[0] != e_rows[0]:
        return [f"{where}: header {a_rows[0] if a_rows else None} != {e_rows[0]}"]
    if len(a_rows) != len(e_rows):
        return [f"{where}: {len(a_rows) - 1} rows != {len(e_rows) - 1}"]
    header = e_rows[0]
    out: list[str] = []
    for r, (a_row, e_row) in enumerate(zip(a_rows[1:], e_rows[1:], strict=True), start=1):
        if len(a_row) != len(e_row):
            out.append(f"{where} row {r}: {len(a_row)} cells != {len(e_row)}")
            continue
        for col, a_cell, e_cell in zip(header, a_row, e_row, strict=True):
            a_num, e_num = _cell_float(a_cell), _cell_float(e_cell)
            if a_num is None or e_num is None:
                ok = a_cell == e_cell
            elif math.isnan(e_num) or math.isinf(e_num):
                ok = a_cell == e_cell
            else:
                ok = _close(a_num, e_num)
                if ok and col in SIGNED_COLUMNS:
                    ok = _sign(a_num) == _sign(e_num)
            if not ok:
                out.append(f"{where} row {r} {col}: {a_cell!r} != {e_cell!r}")
    return out


def _first_line_difference(actual: str, expected: str, where: str) -> list[str]:
    if actual == expected:
        return []
    a_lines, e_lines = actual.split("\n"), expected.split("\n")
    for i, (a, e) in enumerate(zip(a_lines, e_lines, strict=False), start=1):
        if a != e:
            return [f"{where} line {i}: {a!r} != {e!r}"]
    return [f"{where}: {len(a_lines)} lines != {len(e_lines)}"]


def compare_file(
    kind: Kind, actual_path: Path, golden_path: Path, where: str, exact: bool = False
) -> list[str]:
    """Differences between one output file and its golden copy (by kind). Summaries are
    always exact text; resolved configs (kind "yaml") always exact trees; with
    ``exact`` CSV is compared as text and metrics.json floats bit for bit."""
    actual = load_normalised(kind, actual_path)
    expected = load_normalised(kind, golden_path)
    if kind == "csv":
        if exact:
            return _first_line_difference(actual, expected, where)
        return compare_csv(actual, expected, where)
    if kind == "summary":
        return _first_line_difference(actual, expected, where)
    return compare_tree(actual, expected, where, exact or kind == "yaml")


def section_selection(gset: GoldenSet, section: str, run_dir: Path) -> dict[str, tuple[Kind, Path]]:
    """experiment_selection or sweep_selection of one section of ``gset``."""
    if section == EXPERIMENT_SECTION:
        return experiment_selection(run_dir, gset.timeseries_runs)
    return sweep_selection(run_dir)


def read_manifest(golden_dir: Path) -> dict[str, Any]:
    """The golden manifest: provenance, tolerances and, per section, golden file name ->
    {"kind": Kind, "output": path of the output file relative to the run directory}."""
    return json.loads((golden_dir / MANIFEST_NAME).read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    """Write deterministic JSON (UTF-8, LF, indent 1, no NaN)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1, allow_nan=False)
        fh.write("\n")


# ------------------------------------------------------------------------- capture


def _git(args: Sequence[str], repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )


def _git_head(repo: Path) -> str:
    proc = _git(["rev-parse", "HEAD"], repo)
    if proc.returncode != 0:
        raise SystemExit(f"git rev-parse HEAD failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def source_check(repo: Path) -> str:
    """Refuse (SystemExit) unless every GUARDED_PATHS entry has no uncommitted change
    (untracked files included) and its working-tree content equals REFERENCE_COMMIT;
    return the manifest's source note stating what was checked. Read-only git calls."""
    status = _git(["status", "--porcelain", "--", *GUARDED_PATHS], repo)
    if status.returncode != 0:
        raise SystemExit(f"git status failed: {status.stderr.strip()}")
    if status.stdout.strip():
        raise SystemExit(f"refusing to capture: uncommitted changes:\n{status.stdout.strip()}")
    diff = _git(["diff", "--quiet", REFERENCE_COMMIT, "--", *GUARDED_PATHS], repo)
    if diff.returncode == 1:
        raise SystemExit(
            f"refusing to capture: {', '.join(GUARDED_PATHS)} differ from {REFERENCE_COMMIT}; "
            "the golden must never be recaptured from modified source"
        )
    if diff.returncode != 0:
        raise SystemExit(f"git diff failed: {diff.stderr.strip()}")
    return (
        f"{', '.join(GUARDED_PATHS)} identical to {REFERENCE_COMMIT} (the Phase 1 commit; "
        f"checked with git diff --quiet {REFERENCE_COMMIT} and git status at capture); "
        "captured before any Phase 2 source change"
    )


def _destination_check(gset: GoldenSet, dest: Path, force: bool, allow_env_change: bool) -> None:
    """Refuse to replace an existing golden set without ``force``, to change its
    recorded EXACT_ENV_KEYS without ``allow_env_change``, or to capture from an
    experiment input whose digest differs from the existing manifest's (no flag: the
    old set must be deleted first, with the user's approval)."""
    if not dest.exists():
        return
    if not force:
        raise SystemExit(f"refusing to replace the existing golden set {dest} without --force")
    if not (dest / MANIFEST_NAME).is_file():
        return
    manifest = read_manifest(dest)
    recorded_input = manifest.get(INPUT_DIGEST_KEY)
    if recorded_input is not None and recorded_input != input_digest(gset.experiment_file):
        raise SystemExit(
            f"refusing to capture: {gset.experiment_file} differs from the input the "
            "existing golden was captured from"
        )
    if not allow_env_change:
        changed = environment_mismatch(manifest.get("environment", {}))
        if changed:
            raise SystemExit(
                "refusing to capture: environment differs from the existing manifest "
                f"({'; '.join(changed)}); pass --allow-env-change to accept"
            )


def run_in_process(gset: GoldenSet, scratch: Path) -> tuple[Any, dict[str, tuple[Any, Path]]]:
    """``launchsim run`` (and ``sweep`` for a set with one) of ``gset`` in-process into
    ``scratch``, plots off: (the ResolvedExperiment, section -> (ExperimentResult or
    SweepResult list, run directory))."""
    from launchsim import cli, sim

    resolved = cli.load_experiment(gset.experiment_file)
    out: dict[str, tuple[Any, Path]] = {
        EXPERIMENT_SECTION: sim.run_experiment(resolved, scratch, plots=False, repo_root=REPO_ROOT)
    }
    if gset.has_sweep:
        out[SWEEP_SECTION] = sim.run_sweep(resolved, scratch, plots=False, repo_root=REPO_ROOT)
    return resolved, out


def _write_golden_file(target: Path, kind: Kind, src: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if kind in ("json", "yaml"):
        write_json(target, load_normalised(kind, src))
    else:
        with target.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(load_normalised(kind, src))


def _repo_rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def capture(
    gset: GoldenSet,
    cli_dirs: Mapping[str, Path],
    scratch: Path,
    dest: Path | None = None,
    force: bool = False,
    allow_env_change: bool = False,
) -> None:
    """Write the golden set ``gset`` into ``dest`` (default gset.golden_dir) from the CLI
    run directory of each section (``cli_dirs``: section -> directory, made with plots
    on); the objects come from an in-process re-run whose files must equal the CLI files
    byte for byte after provenance stripping (output_digests). Refuses (SystemExit)
    when the sources differ from REFERENCE_COMMIT (source_check), a section directory is
    missing or holds no PNG, or ``dest`` exists without ``force`` (see
    _destination_check)."""
    dest = gset.golden_dir if dest is None else dest
    source_note = source_check(REPO_ROOT)
    _destination_check(gset, dest, force, allow_env_change)
    if set(cli_dirs) != set(gset.sections):
        raise SystemExit(f"{gset.name} needs CLI directories for {list(gset.sections)}")
    pngs = {name: png_files(cli_dirs[name]) for name in gset.sections}
    if not all(pngs.values()):
        raise SystemExit("a CLI directory holds no PNG: run the CLI with plots on")
    resolved, outputs = run_in_process(gset, scratch)
    digests = {name: output_digests(cli_dirs[name]) for name in gset.sections}
    problems = [
        f"{name}/{p}"
        for name in gset.sections
        for p in compare_digests(output_digests(outputs[name][1]), digests[name])
    ]
    if problems:
        raise SystemExit("in-process run differs from the CLI run:\n" + "\n".join(problems[:40]))
    if dest.exists():
        shutil.rmtree(dest)
    manifest_files: dict[str, dict[str, dict[str, str]]] = {}
    base_vehicle = resolved.baseline.vehicle_dict
    for name in gset.sections:
        files: dict[str, dict[str, str]] = {}
        for rel, (kind, src) in section_selection(gset, name, cli_dirs[name]).items():
            _write_golden_file(dest / name / golden_name(rel, kind), kind, src)
            files[golden_name(rel, kind)] = {"kind": kind, "output": rel}
        manifest_files[name] = files
        output, run_dir = outputs[name]
        write_json(dest / name / OBJECTS_NAME, section_objects(name, output, run_dir, base_vehicle))
    experiment = _repo_rel(gset.experiment_file)
    commands = [f"python -m launchsim run {experiment} --results-root <S>"]
    if gset.has_sweep:
        commands.append(f"python -m launchsim sweep {experiment} --results-root <S>")
    write_json(
        dest / MANIFEST_NAME,
        {
            "experiment_file": experiment,
            INPUT_DIGEST_KEY: input_digest(gset.experiment_file),
            "source_commit": _git_head(REPO_ROOT),
            "reference_commit": REFERENCE_COMMIT,
            "guarded_paths": list(GUARDED_PATHS),
            "source_note": source_note,
            "captured_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "commands": commands,
            "normalisation": (
                "metrics.json and resolved_config.yaml: top-level timestamp_utc and git "
                "dropped (golden copies stored as parsed JSON) or, for the digests, "
                "replaced by placeholder lines; summary.md: title provenance replaced, "
                "Timestamp/Git/Git error bullets dropped; CSV: verbatim; LF line endings"
            ),
            "tolerances": {
                "rel": REL_TOL,
                "abs": ABS_TOL,
                "signed_columns": sorted(SIGNED_COLUMNS),
                "exact_subtrees": sorted(EXACT_SUBTREES),
            },
            "tier_note": TIER_NOTE,
            "environment": environment(),
            "exact_env_keys": list(EXACT_ENV_KEYS),
            "files": manifest_files,
            DIGESTS_KEY: digests,
            PNG_KEY: pngs,
        },
    )


def main(argv: list[str] | None = None) -> int:
    """Command-line capture (see the module docstring)."""
    parser = argparse.ArgumentParser(description="Capture a 1-D golden set.")
    parser.add_argument("--set", default=SILO_SET.name, choices=sorted(GOLDEN_SETS))
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--sweep-dir", type=Path, help="required for a set with a sweep")
    parser.add_argument("--scratch", required=True, type=Path)
    parser.add_argument("--dest", type=Path, help="default: tests/data/golden/<set>")
    parser.add_argument("--force", action="store_true", help="replace an existing golden set")
    parser.add_argument(
        "--allow-env-change",
        action="store_true",
        help="accept an environment different from the existing manifest's",
    )
    args = parser.parse_args(argv)
    gset = GOLDEN_SETS[args.set]
    cli_dirs = {EXPERIMENT_SECTION: args.run_dir}
    if args.sweep_dir is not None:
        cli_dirs[SWEEP_SECTION] = args.sweep_dir
    capture(gset, cli_dirs, args.scratch, args.dest, args.force, args.allow_env_change)
    print(f"golden written to {args.dest or gset.golden_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
