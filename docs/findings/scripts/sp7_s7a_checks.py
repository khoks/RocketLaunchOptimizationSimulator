"""SP7 step S7a: the blocking checks of the pre-registration, evaluated read-only.

What it checks (docs/phases/inputs/2026-10-15-SP7-preregistration.md: section 9, "Checks
that block a citation", with section 3's P_ref, section 12's digests, and Amendment 1's
reproduction check), over the step's results directories. It never writes a file, never
flies or sizes anything and does not import launchsim: every number comes from a results
file, and the only computation is a comparison against a registered value.

1. No bug_suspect anywhere: every summary.md's blocked-findings line, every string value
   of every metrics.json (runs, comparisons, offload decompositions, arms) and every cell
   of the sweep indexes.
2. Every pad P* equal to its P_ref within 0.002 kg (section 3's registered P_ref; the pad
   inserted and its search ok, not reference_failed): run A's and run C's pads, both sweep
   directories' baselines, and the arm pads of run A's offload.sensitivity against SP1's
   arm P_ref (results/silo_offload_2d/20261003T112934Z/metrics.json).
3. The stage-1 pad controls' consistency test (their recorded fields, run A and run C;
   neither summary carrying the pad-control blocked-findings line).
4. The reproductions within 0.002 kg of section 9's registered values (run A's uncharged,
   penalty, hot-ramp and 200 m cases; run C's uncharged case), and the nine uncharged
   sweep points equal at 12 significant digits (the index's own precision) to SP1's sweep
   index and to the registered values, in both sweep directories. SP1's sweeps are matched
   to file A's by their axis columns, their variant and their axis values.
5. Every structural case's verification within 1e-4 P_ref, or flagged
   offload_verify_mismatch (a no_offload case has no verification; the arms carry none by
   design, section 3).
6. Every structural case's xv_dry_mass_delta_kg (its cross-vehicle decomposition) equal to
   dm1 + dm2 (structure_dm_kg) within 1e-6 kg; the element sums are printed beside.
7. The structure files' sha256 at HEAD (also in the working tree and at each run's
   recorded commit) equal to section 12's, and every structure sha256 recorded in the four
   directories (metrics.json records and resolved_config.yaml files) equal to them.
8. No offload_nonmonotone, capped gamma* refine (refine_capped) or fired
   structure_fixed_point_cap flag anywhere; every flag name found is listed with its cases.
9. Every no_offload structural case carrying its delta-v shortfall (and, where section 4
   registers a payload case for it, that case's payload deficit): run A's and run C's case
   records, and the re-run's sweep index column <case>.dv_shortfall_mps; the first sweep's
   lack of that column is reported (Amendment 1's reason).
10. Amendment 1's reproduction: every pre-existing column of both sweep indexes equal by
   name, cell for cell as written, between the first sweep and the re-run.

Not evaluated here (section 9 lists them; each has its own record): the frozen sets'
recomputation (tests/test_structure_search.py::test_frozen_sets_reproduce) and the
convergence check (docs/findings/scripts/sp7_convergence.py).

Reads (never writes): run A results/silo_structure_2d/20261016T171513Z, sweep A's first run
results/silo_structure_2d/20261016T171522Z, sweep A's re-run
results/silo_structure_2d/20261019T172327Z, run C
results/silo_structure_2d_readme/20261016T171529Z, SP1's sweep indexes
results/silo_offload_2d/20261003T112949Z/sweep_<k>/sweep_index.csv, SP1's run metrics
results/silo_offload_2d/20261003T112934Z/metrics.json, the two structure files under
configs/structures/ and their blobs at HEAD and at each run's commit (``git show``).

Usage, from the repository root: ``uv run python docs/findings/scripts/sp7_s7a_checks.py``
(a few seconds). Prints each check's numbers and PASS or FAIL, then one summary line;
exits 0 only if every check passes.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
import sys
import traceback
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
SCRIPT = "docs/findings/scripts/sp7_s7a_checks.py"
RESULTS = REPO / "results"
RUN_A = RESULTS / "silo_structure_2d" / "20261016T171513Z"
SWEEP_FIRST = RESULTS / "silo_structure_2d" / "20261016T171522Z"
SWEEP_RERUN = RESULTS / "silo_structure_2d" / "20261019T172327Z"
"""Sweep A's re-run under the pre-registration's Amendment 1 (D-SP7-48)."""
RUN_C = RESULTS / "silo_structure_2d_readme" / "20261016T171529Z"
SP1_SWEEPS = RESULTS / "silo_offload_2d" / "20261003T112949Z"
SP1_RUN = RESULTS / "silo_offload_2d" / "20261003T112934Z"
"""SP1's run of experiments/silo_offload_2d.yaml: its offload.sensitivity holds the arms'
P_ref (each perturbed pad's P*)."""
RUNS = {"run A": RUN_A, "run C": RUN_C}
SWEEPS = {"sweep A first": SWEEP_FIRST, "sweep A re-run": SWEEP_RERUN}
DIRS = {"run A": RUN_A, "sweep A first": SWEEP_FIRST, "sweep A re-run": SWEEP_RERUN, "run C": RUN_C}
"""The four directories the checks cover."""
FILE_A_SWEEPS = (1, 2)
"""File A's sweeps (sweep_<k> in each sweep directory)."""

# ----------------------------------------------------------------- registered values

P_REF_A_KG = 26054.396243494975
"""File A's P_ref [kg] (section 3: SP1's, tests/data/silo_offload_2d_record.json)."""
P_REF_C_KG = 24700.013061881455
"""File C's P_ref [kg] (section 3: SP1's bridge)."""
P_REF_KG = {"run A": P_REF_A_KG, "run C": P_REF_C_KG}
REPRO_KG = {
    "run A": {
        "silo_cold_s1": 41262.90803733282,
        "silo_cold_s1_dry+2t": 32285.203295407457,
        "silo_cold_s1_dry+4t": 22875.96053288855,
        "silo_cold_s1_dry+8.1t": 1980.4767886165673,
        "silo_hot_ramp_s1": 46013.43730748323,
        "silo_cold_200m_s1": 41262.97057414868,
    },
    "run C": {"silo_cold_s1": 36006.44430169878},
}
"""Section 9's registered reproductions [kg]: each case's x* at P_ref."""
REPRO_SWEEP = {
    1: {
        25.0: "18765.1262419",
        50.0: "28653.558053",
        100.0: "41262.9080373",
        200.0: "56827.1590629",
        300.0: "67285.8026498",
    },
    2: {
        50.0: "41262.9734368",
        100.0: "41262.971734",
        200.0: "41262.9705741",
        300.0: "41262.9072618",
    },
}
"""Section 9's uncharged sweep points [kg] by sweep and stroke [m], at 12 significant
digits as SP1's index writes them."""
STRUCTURE_SHA256 = {
    "configs/structures/generic_f9_class_2d.yaml": (
        "a0516875d3c3b64de32f8ed1ceeb1f71a6c67694f7b07306b242522dd3cc8232"
    ),
    "configs/structures/generic_f9_class_2d_readme_loads.yaml": (
        "a850de94ae24ab28941789d7a17da3c3ff5b48f51b762373fc99b6e22edc2997"
    ),
}
"""Section 12's digests of the frozen structure files (D-SP7-31)."""
STRUCTURE_DIR = "configs/structures/"
NO_OFFLOAD_PAYLOAD_CASE = {
    "silo_cold_s1_st_phys_hi": "silo_cold_pstar_st_phys_hi",
    "silo_cold_s1_st_outer_hi": "silo_cold_pstar_st_outer_hi",
    "silo_cold_s1_st_step": "silo_cold_pstar_st_step",
}
"""The payload case section 4 registers for each row section 7 expected to end no_offload
(its payload deficit goes beside the shortfall; section 6, item 5)."""

# ------------------------------------------------------------------------ thresholds

PAD_TOL_KG = 0.002
"""A pad's P* must equal its P_ref within this [kg] (section 9)."""
REPRO_TOL_KG = 0.002
"""A reproduction must equal its registered value within this [kg] (section 9)."""
SIG_DIGITS = 12
"""The sweep index's precision (%.12g): the uncharged points and Amendment 1's cells are
compared at it."""
VERIFY_REL = 1e-4
"""A structural case's verification must reproduce P_ref within this times P_ref
(section 9; offload_verify_mismatch otherwise)."""
DM_TOL_KG = 1e-6
"""xv_dry_mass_delta_kg must equal dm1 + dm2 within this [kg] (section 9)."""

# --------------------------------------------------------------------- recorded text

BUG_SUSPECT = "bug_suspect"
NO_BUG_SUSPECT_LINE = "No run and no comparison is bug_suspect."
"""The blocked-findings line of a summary with nothing bug_suspect (summary.blocked_lines)."""
FINDINGS_BLOCKED_PREFIX = "Findings are blocked until these are investigated (status bug_suspect"
"""summary.FINDINGS_BLOCKED, the line naming bug_suspect runs and comparisons."""
PAD_CONTROL_BLOCKED_PREFIX = (
    "Findings are blocked until these are investigated (a stage-1 pad control failed"
)
"""summary.PAD_CONTROL_BLOCKED, the line naming failed stage-1 pad controls."""
OK_STATUS = "ok"
NO_OFFLOAD_STATUS = "no_offload"
STAGE1_MODE = "stage1"
CONSISTENCY_PASS = "pass"
VERIFY_MISMATCH_FLAG = "offload_verify_mismatch"
FIXED_POINT_CAP_FLAG = "structure_fixed_point_cap"
BLOCKING_FLAGS = ("offload_nonmonotone", "refine_capped", FIXED_POINT_CAP_FLAG)
"""Flag names section 9 blocks on: a non-monotone offload search, a capped gamma* refine
(search.py's refine_capped) and a fired structure fixed-point cap."""
OFFLOAD_PREFIX = "offload:"
ABSCISSA_NOTE = "(P = offload x)"
"""offload.py's prefixes of a solve's flags (an inner search flag carries both)."""
SHORTFALL_SUFFIX = ".dv_shortfall_mps"
"""The sweep index column Amendment 1 added for each case."""
PAD_RUN = "pad"
INSERTED = "inserted"
COMPARISON_STATUS_KEYS = ("screening_status", "decomposition_status", "xv_status")
"""The comparison and decomposition status fields whose values check 1 tallies."""
LIST_CASES_UP_TO = 6
"""Check 8 lists a flag's cases when it has at most this many, else counts per directory."""

SWEEP_FLAG_LINE = re.compile(r"^- (?P<point>sweep_\d+/run_\d+) (?P<case>\S+) offload flags: (.*)$")
"""A sweep summary's line of one point's case record flags (summary.offload_sweep_flag_line)."""
FLAG_TOKEN = re.compile(
    r"(?:^|; )(offload: (?:\(P = offload x\) )?[a-z][a-z0-9_*]*|[a-z][a-z0-9_]*):"
)
"""A flag's name inside a summary's "; "-joined flag list (a snake_case token and a colon
at the start or after "; "; the offload prefixes kept)."""
YAML_SHA = re.compile(r"^(?P<indent>\s*)(?P<key>\w*sha256):\s*['\"]?(?P<digest>[0-9A-Fa-f]{64})")
YAML_FILE = re.compile(r"^(?P<indent>\s*)(?:file|structure_file):\s*['\"]?(?P<path>[^'\"\s]+)")


@dataclass(frozen=True)
class CheckResult:
    """One check's verdict and the lines that show its numbers."""

    number: int
    title: str
    passed: bool
    lines: tuple[str, ...]


# --------------------------------------------------------------------------- readers


def rel(path: Path) -> str:
    """A path relative to the repository, with forward slashes."""
    return path.relative_to(REPO).as_posix()


@cache
def read_json(path: Path) -> Any:
    """A JSON file's content (read once; never modified)."""
    return json.loads(path.read_text(encoding="utf-8"))


@cache
def read_index(path: Path) -> tuple[tuple[str, ...], tuple[dict[str, str], ...]]:
    """A sweep_index.csv as written: its header and its rows (cells as strings). Refuses a
    row whose length differs from the header's."""
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = tuple(next(reader))
        rows = tuple(dict(zip(header, row, strict=True)) for row in reader)
    return header, rows


def index_path(root: Path, k: int) -> Path:
    """sweep_<k>/sweep_index.csv under a sweep directory."""
    return root / f"sweep_{k}" / "sweep_index.csv"


def git_record(root: Path) -> dict[str, Any]:
    """The git record of a results directory (its own metrics.json, or a sweep's
    baseline/metrics.json)."""
    path = root / "metrics.json"
    if not path.exists():
        path = root / "baseline" / "metrics.json"
    return read_json(path)["git"]


def git_blob(rev: str, relpath: str) -> bytes | None:
    """The bytes of ``relpath`` at commit ``rev`` (``git show``), None on a git failure."""
    proc = subprocess.run(
        ["git", "show", f"{rev}:{relpath}"], cwd=REPO, capture_output=True, check=False
    )
    return proc.stdout if proc.returncode == 0 else None


def git_head() -> str:
    """HEAD's abbreviated hash (12 characters), 'unknown' on a git failure."""
    proc = subprocess.run(
        ["git", "rev-parse", "--short=12", "HEAD"],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def sha256(data: bytes) -> str:
    """The hex sha256 of bytes."""
    return hashlib.sha256(data).hexdigest()


def sig(value: str | float) -> str:
    """A number at the index's precision (%.12g)."""
    return format(float(value), f".{SIG_DIGITS}g")


def finite(value: Any) -> bool:
    """Whether a recorded value is a finite number (an empty cell or None is not)."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int | float):
        return math.isfinite(value)
    if isinstance(value, str) and value.strip():
        try:
            return math.isfinite(float(value))
        except ValueError:
            return False
    return False


def norm(cell: str) -> float | str:
    """An axis cell for matching: its float when numeric, else the string."""
    try:
        return float(cell)
    except ValueError:
        return cell


def iter_items(obj: Any, path: str = "") -> Iterator[tuple[str, str, Any, Mapping[str, Any]]]:
    """(path, key, value, parent mapping) of every mapping entry in a JSON tree."""
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            sub = f"{path}.{key}"
            yield sub, str(key), value, obj
            yield from iter_items(value, sub)
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            yield from iter_items(value, f"{path}[{i}]")


def iter_flag_lists(obj: Any, label: str, path: str = "") -> Iterator[tuple[str, str, list[Any]]]:
    """(case label, path, list) of every ``flags`` or ``structure_flags`` list in a JSON
    tree. The label is the nearest enclosing record's ``name`` (or ``run``), a run's key
    under a ``runs`` mapping, else ``label``."""
    if isinstance(obj, Mapping):
        own = obj.get("name") if isinstance(obj.get("name"), str) else obj.get("run")
        here = own if isinstance(own, str) and own else label
        for key, value in obj.items():
            sub = f"{path}.{key}"
            if key in ("flags", "structure_flags") and isinstance(value, list):
                yield here, sub, value
            elif path.endswith(".runs") and isinstance(value, Mapping):
                yield from iter_flag_lists(value, str(key), sub)
            else:
                yield from iter_flag_lists(value, here, sub)
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            yield from iter_flag_lists(value, label, f"{path}[{i}]")


def index_cases(header: Sequence[str]) -> tuple[list[str], list[str]]:
    """(uncharged cases, structural cases) of a sweep index: the ``<case>.status``
    columns, a structural case having ``<case>.structure_dm_kg``."""
    cases = [c[: -len(".status")] for c in header if c.endswith(".status")]
    structural = [c for c in cases if f"{c}.structure_dm_kg" in header]
    return [c for c in cases if c not in structural], structural


def axis_columns(header: Sequence[str]) -> tuple[str, ...]:
    """A sweep index's axis columns: those between ``point`` and ``run_dir``."""
    return tuple(header[header.index("point") + 1 : header.index("run_dir")])


def sweep_signature(path: Path) -> tuple[Any, ...]:
    """What identifies a sweep: its axis columns, and each point's variant and axis values."""
    header, rows = read_index(path)
    axes = axis_columns(header)
    return axes, tuple((r["of"], *(norm(r[a]) for a in axes)) for r in rows)


@cache
def sp1_sweep_for() -> dict[int, Path]:
    """File A's sweep k -> the SP1 sweep index with the same signature (exactly one)."""
    sp1 = sorted(SP1_SWEEPS.glob("sweep_*/sweep_index.csv"))
    out = {}
    for k in FILE_A_SWEEPS:
        mine = sweep_signature(index_path(SWEEP_FIRST, k))
        hits = [p for p in sp1 if sweep_signature(p) == mine]
        if len(hits) != 1:
            raise ValueError(f"file A's sweep {k} matches {len(hits)} of SP1's sweeps")
        out[k] = hits[0]
    return out


def sweep_flag_lines(root: Path) -> dict[tuple[str, str], str]:
    """(point dir, case) -> the flag text of a sweep summary's offload-flags line."""
    out = {}
    for line in (root / "summary.md").read_text(encoding="utf-8").splitlines():
        m = SWEEP_FLAG_LINE.match(line)
        if m:
            out[(m["point"], m["case"])] = m.group(3)
    return out


def flag_name(text: str) -> str:
    """A flag string's name: the text before its first colon, an offload solve's flag as
    'offload: <name>' (the abscissa note dropped)."""
    head = text
    if head.startswith(OFFLOAD_PREFIX):
        head = head[len(OFFLOAD_PREFIX) :].lstrip()
        if head.startswith(ABSCISSA_NOTE):
            head = head[len(ABSCISSA_NOTE) :].lstrip()
        return f"{OFFLOAD_PREFIX} {head.split(':', 1)[0].strip()}"
    return head.split(":", 1)[0].strip()


def yaml_sha_records(path: Path) -> list[tuple[int, str | None, str]]:
    """(line number, file path, digest) of every ``*sha256:`` line of a YAML file, its file
    the nearest ``file:`` or ``structure_file:`` line at the same indent in the same block
    (searched upward, then downward)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    for i, line in enumerate(lines):
        m = YAML_SHA.match(line)
        if not m:
            continue
        indent = len(m["indent"])
        found = None
        for order in (range(i - 1, -1, -1), range(i + 1, len(lines))):
            for j in order:
                other = lines[j]
                if not other.strip():
                    continue
                depth = len(other) - len(other.lstrip())
                if depth < indent:
                    break
                f = YAML_FILE.match(other)
                if f and len(f["indent"]) == indent:
                    found = f["path"]
                    break
            if found is not None:
                break
        out.append((i + 1, found, m["digest"].lower()))
    return out


def structural_cases(root: Path) -> list[dict[str, Any]]:
    """A run's offload case records that carry a modelled structure."""
    return [
        c
        for c in read_json(root / "metrics.json")["offload"]["cases"]
        if c.get("structure_charged")
    ]


# ----------------------------------------------------------------------------- checks


def check_bug_suspect() -> tuple[bool, list[str]]:
    """Check 1: no bug_suspect in any summary.md, metrics.json or sweep index."""
    lines: list[str] = []
    problems: list[str] = []
    for label, root in DIRS.items():
        mds = sorted(root.rglob("summary.md"))
        clean = 0
        for md in mds:
            text = md.read_text(encoding="utf-8").splitlines()
            n_line = sum(1 for t in text if t.strip() == NO_BUG_SUSPECT_LINE)
            blocked = [t for t in text if t.startswith(FINDINGS_BLOCKED_PREFIX)]
            if blocked:
                problems.append(f"{rel(md)}: {blocked[0][:300]}")
            elif n_line != 1:
                problems.append(f"{rel(md)}: {n_line} lines '{NO_BUG_SUSPECT_LINE}' (expected 1)")
            else:
                clean += 1
        lines.append(
            f"{label}: {clean} of {len(mds)} summary.md carry '{NO_BUG_SUSPECT_LINE}' and no "
            "blocked-findings line"
        )
    for label, root in DIRS.items():
        files = sorted(root.rglob("metrics.json"))
        tally: dict[str, Counter[str]] = defaultdict(Counter)
        n_strings = 0
        for path in files:
            for where, key, value, _parent in iter_items(read_json(path)):
                if isinstance(value, str):
                    n_strings += 1
                    if value == BUG_SUSPECT:
                        problems.append(f"{rel(path)}{where} = {BUG_SUSPECT}")
                    if key in COMPARISON_STATUS_KEYS:
                        tally[key][value] += 1
        counts = "; ".join(
            f"{key} x{sum(tally[key].values())} ("
            + ", ".join(f"{v} {n}" for v, n in sorted(tally[key].items()))
            + ")"
            for key in COMPARISON_STATUS_KEYS
            if tally[key]
        )
        lines.append(
            f"{label}: {len(files)} metrics.json, {n_strings} string values read, none "
            f"'{BUG_SUSPECT}' unless listed below; {counts}"
        )
    for label, root in SWEEPS.items():
        for k in FILE_A_SWEEPS:
            path = index_path(root, k)
            header, rows = read_index(path)
            status_cols = [c for c in header if c.endswith("status")]
            tally = Counter(r[c] for r in rows for c in status_cols)
            for r in rows:
                for c in header:
                    if r[c] == BUG_SUSPECT:
                        problems.append(f"{rel(path)} point {r['point']} column {c}: {BUG_SUSPECT}")
            lines.append(
                f"{label} sweep_{k}/sweep_index.csv: {len(rows)} rows x {len(header)} columns "
                f"scanned; its {len(status_cols)} status columns ("
                + ", ".join(c for c in status_cols)
                + ") hold "
                + ", ".join(f"{v or 'empty'} {n}" for v, n in sorted(tally.items()))
            )
    lines += [f"FOUND: {p}" for p in problems]
    return not problems, lines


def pad_line(label: str, metrics: Mapping[str, Any], p_ref: float) -> tuple[bool, str]:
    """A pad's P* against P_ref [kg], with its status and search status."""
    p_star = float(metrics["payload_kg"])
    diff = p_star - p_ref
    ok = (
        abs(diff) <= PAD_TOL_KG
        and metrics.get("status") == INSERTED
        and metrics.get("search_status") == OK_STATUS
    )
    return ok, (
        f"{label}: P* {p_star!r} kg against P_ref {p_ref!r} kg, diff {diff:+.3e} kg "
        f"(status {metrics.get('status')}, search {metrics.get('search_status')})"
    )


def check_pads() -> tuple[bool, list[str]]:
    """Check 2: every pad P* equals its P_ref within PAD_TOL_KG."""
    lines: list[str] = []
    passed = True
    for label, root in RUNS.items():
        data = read_json(root / "metrics.json")
        ok, line = pad_line(f"{label} pad", data["runs"][PAD_RUN], P_REF_KG[label])
        passed &= ok
        lines.append(line)
        recorded = float(data["offload"]["reference_payload_kg"])
        ok = abs(recorded - P_REF_KG[label]) <= PAD_TOL_KG
        passed &= ok
        lines.append(
            f"{label} offload.reference_payload_kg {recorded!r} kg, diff "
            f"{recorded - P_REF_KG[label]:+.3e} kg against the registered P_ref"
        )
    for label, root in SWEEPS.items():
        base = read_json(root / "baseline" / "metrics.json")
        ok, line = pad_line(f"{label} baseline {base['run']}", base["metrics"], P_REF_A_KG)
        passed &= ok
        lines.append(line)
        cells = []
        for k in FILE_A_SWEEPS:
            header, rows = read_index(index_path(root, k))
            cols = [c for c in header if c.endswith(".reference_payload_kg")]
            cells += [r[c] for r in rows for c in cols]
        ok = bool(cells) and all(sig(c) == sig(P_REF_A_KG) for c in cells)
        passed &= ok
        lines.append(
            f"{label} sweep indexes: {len(cells)} <case>.reference_payload_kg cells (each point's "
            f"P_ref), equal to P_ref at {SIG_DIGITS} digits ({sig(P_REF_A_KG)}): "
            f"{'all' if ok else 'NOT ALL: ' + ', '.join(sorted(set(cells)))}"
        )
    arms = read_json(RUN_A / "metrics.json")["offload"]["sensitivity"]
    sp1 = {
        (s["param"], float(s["fraction"])): s
        for s in read_json(SP1_RUN / "metrics.json")["offload"]["sensitivity"]
    }
    lines.append(
        f"arm pads: run A's offload.sensitivity ({len(arms)} arms) against SP1's arm P_ref "
        f"({rel(SP1_RUN / 'metrics.json')})"
    )
    for arm in arms:
        ref = sp1.get((arm["param"], float(arm["fraction"])))
        if ref is None:
            passed = False
            lines.append(f"  {arm['run']}: no SP1 arm with this parameter and change")
            continue
        p_ref, p_sp1 = float(arm["reference_payload_kg"]), float(ref["reference_payload_kg"])
        ok = abs(p_ref - p_sp1) <= PAD_TOL_KG
        passed &= ok
        what = "perturbed pad" if arm.get("pad_perturbed") else "drive arm: pad not perturbed"
        lines.append(
            f"  {arm['param']} {float(arm['fraction']):+.0%} ({what}): P_ref {p_ref!r} kg "
            f"against SP1's {p_sp1!r} kg, diff {p_ref - p_sp1:+.3e} kg (arm status "
            f"{arm.get('status')})"
        )
    return passed, lines


def check_pad_controls() -> tuple[bool, list[str]]:
    """Check 3: the stage-1 pad controls pass their consistency test."""
    lines: list[str] = []
    passed = True
    for label, root in RUNS.items():
        controls = [
            c
            for c in read_json(root / "metrics.json")["offload"].get("pad_controls") or []
            if c.get("mode") == STAGE1_MODE
        ]
        if not controls:
            passed = False
            lines.append(f"{label}: no stage-1 pad control recorded")
        for c in controls:
            ok = c.get("consistency") == CONSISTENCY_PASS
            passed &= ok
            lines.append(
                f"{label} {c['run']}: status {c['status']}, x_pad {c['offload_kg']!r} kg, "
                f"m_res(0) {c['m_res_kg']:.6g} kg, dv_margin {c['dv_margin_mps']:.6g} m/s, "
                f"bound {c['bound_kg']:.6g} kg, within_bound {c['within_bound']}, resolution "
                f"effect {c['resolution_effect']}, flags {len(c.get('flags') or [])}: "
                f"consistency {c.get('consistency')}"
            )
        summary = (root / "summary.md").read_text(encoding="utf-8").splitlines()
        blocked = [t for t in summary if t.startswith(PAD_CONTROL_BLOCKED_PREFIX)]
        passed &= not blocked
        lines.append(
            f"{label} summary.md: "
            + (
                f"BLOCKED: {blocked[0][:300]}"
                if blocked
                else "no pad-control blocked-findings line"
            )
        )
    lines.append("sweep points: no pad control by design (section 3)")
    return passed, lines


def check_reproductions() -> tuple[bool, list[str]]:
    """Check 4: section 9's reproductions within REPRO_TOL_KG, and the nine uncharged sweep
    points equal to SP1's index and the registered values at SIG_DIGITS digits."""
    lines: list[str] = []
    passed = True
    for label, root in RUNS.items():
        cases = {c["name"]: c for c in read_json(root / "metrics.json")["offload"]["cases"]}
        for name, value in REPRO_KG[label].items():
            case = cases.get(name)
            if case is None:
                passed = False
                lines.append(f"{label} {name}: no such case")
                continue
            x = float(case["offload_kg"])
            ok = case["status"] == OK_STATUS and abs(x - value) <= REPRO_TOL_KG
            passed &= ok
            lines.append(
                f"{label} {name}: x* {x!r} kg against {value!r} kg, diff {x - value:+.3e} kg "
                f"(status {case['status']})"
            )
    for k, sp1_path in sp1_sweep_for().items():
        sp1_header, sp1_rows = read_index(sp1_path)
        axes = axis_columns(sp1_header)
        lines.append(
            f"file A's sweep {k} = SP1's {sp1_path.parent.name} ({rel(sp1_path)}): "
            f"{sp1_rows[0]['of']} over {', '.join(axes)} = "
            f"{', '.join(r[axes[0]] for r in sp1_rows)}"
        )
        for label, root in SWEEPS.items():
            header, rows = read_index(index_path(root, k))
            uncharged, _ = index_cases(header)
            if len(uncharged) != 1:
                passed = False
                lines.append(f"  {label} sweep_{k}: uncharged cases {uncharged} (expected one)")
            for case in uncharged:
                seen = set()
                for r in rows:
                    key = tuple(norm(r[a]) for a in axes)
                    sp1_row = next(
                        (s for s in sp1_rows if tuple(norm(s[a]) for a in axes) == key), None
                    )
                    if sp1_row is None:
                        passed = False
                        lines.append(f"  {label} sweep_{k} {r['run_dir']}: no SP1 point {key}")
                        continue
                    stroke = float(r[axes[0]])
                    reg = REPRO_SWEEP[k].get(stroke)
                    cell, sp1_cell = r[f"{case}.offload_kg"], sp1_row[f"{case}.offload_kg"]
                    same_sp1 = sig(cell) == sig(sp1_cell)
                    same_reg = reg is not None and sig(cell) == sig(reg)
                    diff = float(cell) - float(sp1_cell)
                    ok = (
                        r[f"{case}.status"] == OK_STATUS
                        and same_sp1
                        and same_reg
                        and abs(diff) <= REPRO_TOL_KG
                    )
                    passed &= ok
                    seen.add(stroke)
                    lines.append(
                        f"  {label} sweep_{k} {r['run_dir']} {axes[0]} {r[axes[0]]}: {case} "
                        f"{cell} kg; SP1 {sp1_cell} kg ({'equal' if same_sp1 else 'DIFFERS'} at "
                        f"{SIG_DIGITS} digits, diff {diff:+.1e} kg); registered {reg} kg "
                        f"({'equal' if same_reg else 'DIFFERS'}); status {r[f'{case}.status']}"
                    )
                missing = sorted(set(REPRO_SWEEP[k]) - seen)
                if missing:
                    passed = False
                    lines.append(f"  {label} sweep_{k}: registered points not found: {missing}")
    return passed, lines


def check_verification() -> tuple[bool, list[str]]:
    """Check 5: every structural case's verification within VERIFY_REL x P_ref, or
    flagged offload_verify_mismatch."""
    lines: list[str] = []
    passed = True
    for label, root in RUNS.items():
        for case in structural_cases(root):
            tol = VERIFY_REL * float(case["reference_payload_kg"])
            ver = case.get("verification")
            flagged = any(VERIFY_MISMATCH_FLAG in str(f) for f in case.get("flags") or [])
            name, status = case["name"], case["status"]
            if ver is None:
                ok = status == NO_OFFLOAD_STATUS
                passed &= ok
                lines.append(
                    f"{label} {name} ({status}): no verification"
                    + (" (no offload to verify)" if ok else " MISSING")
                )
                continue
            d = float(ver["delta_kg"])
            ok = abs(d) <= tol or flagged
            passed &= ok
            lines.append(
                f"{label} {name} ({status}): verified P - P_ref {d:+.6f} kg, |.| <= {tol:.4f} "
                f"kg: {'yes' if abs(d) <= tol else 'NO'}"
                + (f"; flagged {VERIFY_MISMATCH_FLAG}" if flagged else "")
                + f" (recorded passed {ver.get('passed')}, status {ver.get('status')})"
            )
    tol = VERIFY_REL * P_REF_A_KG
    for label, root in SWEEPS.items():
        flags = sweep_flag_lines(root)
        for k in FILE_A_SWEEPS:
            header, rows = read_index(index_path(root, k))
            _, structural = index_cases(header)
            for case in structural:
                for r in rows:
                    status, cell = r[f"{case}.status"], r[f"{case}.verification_delta_kg"]
                    flagged = VERIFY_MISMATCH_FLAG in flags.get((r["run_dir"], case), "")
                    if not finite(cell):
                        ok = status == NO_OFFLOAD_STATUS
                        passed &= ok
                        text = "no verification" + (" (no offload to verify)" if ok else " MISSING")
                    else:
                        within = abs(float(cell)) <= tol
                        ok = within or flagged
                        passed &= ok
                        text = (
                            f"verified P - P_ref {float(cell):+.6f} kg, |.| <= {tol:.4f} kg: "
                            f"{'yes' if within else 'NO'}"
                            + (f"; flagged {VERIFY_MISMATCH_FLAG}" if flagged else "")
                        )
                    lines.append(f"{label} {r['run_dir']} {case} ({status}): {text}")
    lines.append(
        "arms: no verification search by design (section 3, OFFLOAD_SENSITIVITY_BASIS); "
        "payload cases are not offload solves"
    )
    return passed, lines


def check_dry_mass() -> tuple[bool, list[str]]:
    """Check 6: xv_dry_mass_delta_kg equals dm1 + dm2 (structure_dm_kg) within DM_TOL_KG."""
    lines: list[str] = []
    passed = True
    worst_el = 0.0
    for label, root in RUNS.items():
        for case in structural_cases(root):
            dec = case.get("decomposition") or {}
            xv = dec.get("xv_dry_mass_delta_kg")
            dm, dm2 = case.get("structure_dm_kg"), case.get("structure_dm_stage2_kg")
            if not (finite(xv) and finite(dm) and finite(dm2)):
                passed = False
                lines.append(f"{label} {case['name']}: xv {xv}, dm {dm}, dm2 {dm2}: MISSING")
                continue
            diff = float(xv) - float(dm)
            ok = abs(diff) <= DM_TOL_KG
            passed &= ok
            elements = case.get("structure_elements") or {}
            el1 = sum(float(v) for k, v in elements.items() if k.startswith("stage1."))
            el2 = sum(float(v) for k, v in elements.items() if k.startswith("stage2."))
            worst_el = max(worst_el, abs(el1 + el2 - float(dm)), abs(el2 - float(dm2)))
            lines.append(
                f"{label} {case['name']} ({case['status']}): xv_dry_mass_delta {float(xv)!r} kg; "
                f"dm1 + dm2 = {float(dm) - float(dm2):.6f} + {float(dm2):.6f} = {float(dm)!r} kg; "
                f"diff {diff:+.1e} kg"
            )
    lines.append(
        "beside (not a gate): the element sums (stage1.* and stage2.*) equal dm and dm2 to "
        f"{worst_el:.1e} kg at most"
    )
    lines.append(
        "not on disk: sweep points (no case record or decomposition is written, section 3) and "
        "the arms (decomposition status and residual only)"
    )
    return passed, lines


def check_sha256() -> tuple[bool, list[str]]:
    """Check 7: the structure files' sha256 at HEAD (also the working tree and each run's
    commit) and every recorded structure sha256 equal section 12's."""
    lines: list[str] = []
    passed = True
    head = git_head()
    commits = {label: str(git_record(root)["hash"]) for label, root in DIRS.items()}
    revs = {f"HEAD {head}": "HEAD"} | {
        f"{', '.join(k for k, v in commits.items() if v == c)}'s commit {c}": c
        for c in dict.fromkeys(commits.values())
    }
    for relpath, digest in STRUCTURE_SHA256.items():
        disk = sha256((REPO / relpath).read_bytes())
        ok = disk == digest
        passed &= ok
        lines.append(f"{relpath}: registered {digest}")
        lines.append(f"  working tree {disk}: {'equal' if ok else 'DIFFERS'}")
        for what, rev in revs.items():
            blob = git_blob(rev, relpath)
            got = None if blob is None else sha256(blob)
            ok = got == digest
            passed &= ok
            lines.append(f"  {what}: {got}: {'equal' if ok else 'DIFFERS'}")
    for label, root in DIRS.items():
        found: dict[str, Counter[str]] = {"json": Counter(), "yaml": Counter()}
        records: list[tuple[str, str, str | None, str]] = []
        jsons = sorted(root.rglob("metrics.json"))
        for path in jsons:
            for where, key, value, parent in iter_items(read_json(path)):
                if key.endswith("sha256") and isinstance(value, str):
                    file_key = "structure_file" if key == "structure_file_sha256" else "file"
                    fpath = parent.get(file_key)
                    fpath = fpath if isinstance(fpath, str) else None
                    records.append(("json", f"{rel(path)}{where}", fpath, value.lower()))
        yamls = sorted(root.rglob("resolved_config.yaml"))
        for path in yamls:
            for line_no, fpath, value in yaml_sha_records(path):
                records.append(("yaml", f"{rel(path)}:{line_no}", fpath, value))
        for kind, where, fpath, value in records:
            if fpath is None:
                passed = False
                lines.append(f"  digest with no file named beside it: {where}")
            elif not fpath.startswith(STRUCTURE_DIR):
                lines.append(f"  other digest record (not a structure file; not gated): {where}")
            else:
                ok = STRUCTURE_SHA256.get(fpath) == value
                passed &= ok
                found[kind][f"{fpath} {'equal' if ok else 'DIFFERS'}"] += 1
                if not ok:
                    lines.append(f"  DIFFERS: {where} = {value} ({fpath})")
        lines.append(
            f"{label} (git {commits[label]}): structure digest records in its {len(jsons)} "
            f"metrics.json: "
            + ("; ".join(f"{n} x {w}" for w, n in sorted(found["json"].items())) or "none")
            + f"; in its {len(yamls)} resolved_config.yaml: "
            + ("; ".join(f"{n} x {w}" for w, n in sorted(found["yaml"].items())) or "none")
        )
    return passed, lines


def flag_entries(items: Sequence[Any]) -> Iterator[tuple[str, bool, Any]]:
    """(name, fired, item) of each entry of a flags list: a string is a fired flag; a
    structure flag record (name, fired) is fired when its ``fired`` is true."""
    for item in items:
        if isinstance(item, str):
            yield flag_name(item), True, item
        elif isinstance(item, Mapping) and isinstance(item.get("name"), str):
            yield item["name"], bool(item.get("fired")), item


def check_flags() -> tuple[bool, list[str]]:
    """Check 8: no offload_nonmonotone, refine_capped or fired structure_fixed_point_cap
    flag; every flag name found, with its cases."""
    lines: list[str] = []
    found: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    blocking: list[str] = []
    cap_records = cap_fired = 0
    cap_iters: list[int] = []
    cap_steps: list[float] = []
    for label, root in DIRS.items():
        for path in sorted(root.rglob("metrics.json")):
            where = path.parent.relative_to(root).as_posix()
            for case, jpath, items in iter_flag_lists(read_json(path), where):
                who = (
                    where if where.endswith(case) else (case if where == "." else f"{where} {case}")
                )
                for name, fired, item in flag_entries(items):
                    if name == FIXED_POINT_CAP_FLAG and isinstance(item, Mapping):
                        cap_records += 1
                        cap_fired += fired
                        values = item.get("values") or {}
                        if finite(values.get("iterations")):
                            cap_iters.append(int(values["iterations"]))
                        if finite(values.get("last_step_kg")):
                            cap_steps.append(float(values["last_step_kg"]))
                    if not fired:
                        continue
                    found[name][label].add(who)
                    text = item if isinstance(item, str) else name
                    if any(b in text for b in BLOCKING_FLAGS):
                        blocking.append(f"{label} {who}: {text[:300]} ({rel(path)}{jpath})")
        if root in SWEEPS.values():
            n_agree = n_lines = 0
            counts = {}
            for k in FILE_A_SWEEPS:
                header, rows = read_index(index_path(root, k))
                uncharged, structural = index_cases(header)
                for r in rows:
                    for c in [*uncharged, *structural]:
                        counts[(r["run_dir"], c)] = r[f"{c}.n_flags"]
                        for name in filter(None, r.get(f"{c}.structure_flags", "").split("; ")):
                            found[name][label].add(f"{r['run_dir']} {c}")
                            if name in BLOCKING_FLAGS:
                                blocking.append(f"{label} {r['run_dir']} {c}: {name} (index)")
            for (point, case), text in sweep_flag_lines(root).items():
                n_lines += 1
                names = (
                    [] if text == "none" else [flag_name(t + ":") for t in FLAG_TOKEN.findall(text)]
                )
                n_agree += str(len(names)) == counts.get((point, case))
                for name in names:
                    found[name][label].add(f"{point} {case}")
                if any(b in text for b in BLOCKING_FLAGS):
                    blocking.append(f"{label} {point} {case}: {text[:300]} (summary.md)")
            lines.append(
                f"{label}: summary.md's offload-flag lines: {n_lines}, the parsed flag count "
                f"equal to the index's <case>.n_flags on {n_agree}"
            )
    lines.append("flag names found (fired), by directory:")
    for name in sorted(found):
        per_dir = found[name]
        total = sum(len(v) for v in per_dir.values())
        parts = []
        for label in DIRS:
            cases = sorted(per_dir.get(label, ()))
            if not cases:
                continue
            listed = ", ".join(cases) if len(cases) <= LIST_CASES_UP_TO else f"{len(cases)} cases"
            parts.append(f"{label}: {listed}")
        lines.append(f"  {name} ({total} case records): " + "; ".join(parts))
    lines.append(
        f"{FIXED_POINT_CAP_FLAG} records (fired or not) in the metrics.json files: {cap_records}, "
        f"fired {cap_fired} (iterations at most {max(cap_iters, default=0)}, last step at most "
        f"{max(cap_steps, default=0.0):.2e} kg); a sweep point's index lists only its fired "
        "structure flags (<case>.structure_flags, read above)"
    )
    lines.append(
        "blocking flags (" + ", ".join(BLOCKING_FLAGS) + "): " + ("none" if not blocking else "")
    )
    lines += [f"  FOUND: {b}" for b in blocking]
    return not blocking, lines


def check_shortfalls() -> tuple[bool, list[str]]:
    """Check 9: every no_offload structural case carries its delta-v shortfall (and its
    registered payload case's deficit)."""
    lines: list[str] = []
    passed = True
    for label, root in RUNS.items():
        off = read_json(root / "metrics.json")["offload"]
        payload_cases = {p["name"]: p for p in off.get("structure_payload_cases") or []}
        ended = [c for c in off["cases"] if c["status"] == NO_OFFLOAD_STATUS]
        if not ended:
            lines.append(f"{label}: no case ended {NO_OFFLOAD_STATUS}")
        for case in ended:
            short = (case.get("solve") or {}).get("dv_shortfall_mps")
            ok = finite(short)
            kind = "structural" if case.get("structure_charged") else "uncharged"
            text = f"{label} {case['name']} ({kind}): " + (
                f"solve.dv_shortfall_mps {short!r} m/s" if ok else "NO SHORTFALL"
            )
            pname = NO_OFFLOAD_PAYLOAD_CASE.get(case["name"]) if label == "run A" else None
            if pname is not None:
                pcase = payload_cases.get(pname) or {}
                deficit = pcase.get("payload_delta_kg")
                ok &= pcase.get("status") == OK_STATUS and finite(deficit)
                text += (
                    f"; payload case {pname}: deficit P_2* - P_ref {deficit!r} kg (status "
                    f"{pcase.get('status')}; its structure_payload_unconverged "
                    f"{pcase.get('unconverged')}, not blocking)"
                )
            passed &= ok
            lines.append(text)
    for label, root in SWEEPS.items():
        for k in FILE_A_SWEEPS:
            header, rows = read_index(index_path(root, k))
            uncharged, structural = index_cases(header)
            cases = [*uncharged, *structural]
            ended = [(r, c) for r in rows for c in cases if r[f"{c}.status"] == NO_OFFLOAD_STATUS]
            columns = [c for c in cases if f"{c}{SHORTFALL_SUFFIX}" in header]
            if root == SWEEP_FIRST:
                lines.append(
                    f"{label} sweep_{k}: {len(ended)} {NO_OFFLOAD_STATUS} point(s), shortfall "
                    f"columns: {', '.join(columns) or 'none'} (the reporting defect Amendment 1 "
                    "fixed; superseded by the re-run, not gated here)"
                )
                continue
            missing = [c for c in cases if c not in columns]
            if missing:
                passed = False
                lines.append(f"{label} sweep_{k}: no {SHORTFALL_SUFFIX} column for {missing}")
            for r, c in ended:
                cell = r.get(f"{c}{SHORTFALL_SUFFIX}", "")
                ok = finite(cell)
                passed &= ok
                lines.append(
                    f"{label} {r['run_dir']} {r[axis_columns(header)[0]]} m {c}: "
                    f"{c}{SHORTFALL_SUFFIX} = {cell if ok else 'EMPTY'} m/s"
                )
            if not ended:
                lines.append(f"{label} sweep_{k}: no {NO_OFFLOAD_STATUS} point")
    return passed, lines


def check_amendment1() -> tuple[bool, list[str]]:
    """Check 10: every pre-existing column of both sweep indexes equal by name, cell for
    cell as written, between the first sweep and the re-run."""
    lines: list[str] = []
    passed = True
    for k in FILE_A_SWEEPS:
        h1, rows1 = read_index(index_path(SWEEP_FIRST, k))
        h2, rows2 = read_index(index_path(SWEEP_RERUN, k))
        dupes = [c for h in (h1, h2) for c, n in Counter(h).items() if n > 1]
        missing = [c for c in h1 if c not in h2]
        added = [c for c in h2 if c not in h1]
        mismatches = []
        for r1, r2 in zip(rows1, rows2, strict=False):
            mismatches += [
                f"point {r1['point']} {c}: {r1[c]!r} -> {r2[c]!r}"
                for c in h1
                if c in r2 and r1[c] != r2[c]
            ]
        ok = not missing and not dupes and len(rows1) == len(rows2) and not mismatches
        passed &= ok
        lines.append(
            f"sweep_{k}: first {len(rows1)} rows x {len(h1)} columns, re-run {len(rows2)} rows x "
            f"{len(h2)} columns; {len(h1)} pre-existing columns compared by name over "
            f"{min(len(rows1), len(rows2))} rows ({len(h1) * min(len(rows1), len(rows2))} "
            f"cells): {len(mismatches)} differ; missing in the re-run: {missing or 'none'}; "
            f"added: {', '.join(added) or 'none'}"
            + (f"; duplicated names: {dupes}" if dupes else "")
        )
        lines += [f"  DIFFERS: {m}" for m in mismatches[:50]]
    return passed, lines


CHECKS: tuple[tuple[int, str, Callable[[], tuple[bool, list[str]]]], ...] = (
    (1, "no bug_suspect anywhere", check_bug_suspect),
    (2, "every pad P* equal to its P_ref within 0.002 kg", check_pads),
    (3, "the stage-1 pad controls pass their consistency test", check_pad_controls),
    (4, "the reproductions (0.002 kg; sweep points at 12 significant digits)", check_reproductions),
    (5, "structural verification within 1e-4 P_ref or flagged", check_verification),
    (6, "xv_dry_mass_delta_kg = dm1 + dm2 within 1e-6 kg", check_dry_mass),
    (7, "structure files' sha256 equal section 12's", check_sha256),
    (8, "no offload_nonmonotone, refine_capped or fired fixed-point cap", check_flags),
    (9, "every no_offload structural case carries its shortfall", check_shortfalls),
    (10, "Amendment 1: the re-run reproduces every pre-existing index column", check_amendment1),
)


def run_check(number: int, title: str, fn: Callable[[], tuple[bool, list[str]]]) -> CheckResult:
    """Run one check; an exception is a FAIL that names it (a script or data error to fix,
    never a pass)."""
    try:
        passed, lines = fn()
    except Exception as exc:  # report and carry on with the other checks
        tail = traceback.format_exc().strip().splitlines()[-3:]
        return CheckResult(number, title, False, (f"could not evaluate: {exc!r}", *tail))
    return CheckResult(number, title, passed, tuple(lines))


def header_lines() -> list[str]:
    """The provenance block: the script, HEAD and each directory's git record."""
    out = [
        f"{SCRIPT}: SP7 step S7a, the pre-registration's section 9 checks and Amendment 1's "
        "reproduction check (read-only)",
        f"HEAD {git_head()}",
    ]
    for label, root in DIRS.items():
        git = git_record(root)
        out.append(f"  {label:<15} {rel(root)} (git {git['hash']}, dirty {git['dirty']})")
    out.append(f"  {'SP1 sweeps':<15} {rel(SP1_SWEEPS)}")
    out.append(f"  {'SP1 arms':<15} {rel(SP1_RUN / 'metrics.json')}")
    return out


def main() -> int:
    """Run every check, print its lines and verdict, then the summary line; 0 only if
    every check passes."""
    for line in header_lines():
        print(line)
    results = [run_check(n, title, fn) for n, title, fn in CHECKS]
    for r in results:
        print()
        print(f"[{r.number}] {r.title}")
        for line in r.lines:
            print(f"    {line}")
        print(f"    -> {'PASS' if r.passed else 'FAIL'}")
    failed = [r.number for r in results if not r.passed]
    print()
    if failed:
        print(
            f"SUMMARY: FAIL: check(s) {', '.join(map(str, failed))} failed "
            f"({len(results) - len(failed)} of {len(results)} PASS)"
        )
        return 1
    print(f"SUMMARY: PASS: all {len(results)} checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
