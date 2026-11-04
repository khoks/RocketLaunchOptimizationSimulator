"""SP7 step S7b: the blocking checks of the pre-registration's part 2 on run B, read-only.

What it evaluates, every rule from docs/phases/inputs/2026-11-03-SP7-preregistration-part2.md
("the addendum"; part 1, docs/phases/inputs/2026-10-15-SP7-preregistration.md, where the
addendum cites it), on run B's results directory (RUN_B_DIR below, or --run-b) and, for the
cross-commit check only, run A's and SP1's directories, read only:

A. The checks that block a citation (the addendum's section 9, one check per bullet, in its
   order, none added and none dropped), each printed with its values, its tolerance and
   PASS, FAIL or NOT EVALUATED:

    1. no run or comparison bug_suspect (part 1, section 9's list: the per-run closure,
       loss identity and insertion checks, the blocking screening checks, a cross-vehicle
       decomposition residual above checks.closure_tol_mps, 1e-5 m/s);
    2. the pad not reference_failed and its P* within 0.002 kg of P_ref
       26,054.396243494975 kg (section 3);
    3. the stage-1 pad control passing its consistency test;
    4. the cross-commit check (design 4.10): silo_cold_s1 within 0.002 kg of SP1's
       41,262.90803733282 kg and silo_cold_s1_st within 0.002 kg of run A's
       11,420.246638573297 kg (section 3; both read from SP1's and run A's metrics.json
       too);
    5. lm_cmd's uncharged x* within 0.25 kg of SP1's 41,262.908 kg;
    6. every structural case's verification within 1e-4 P_ref (2.605 kg), or flagged
       offload_verify_mismatch (then PASS "as a bound", noted in the SUMMARY line, and every
       line that prints the case's x* marks it as a bound);
    7. every structural case's xv_dry_mass_delta_kg equal to dm1 + dm2 at x* within 1e-6
       kg (dm1 + dm2 as run B records it: structure_dm_kg);
    8. the structure files' sha256 at run B's commit, and every structure digest run B
       records, equal to part 1, section 12's (the addendum's section 12);
    9. the linear-motor convergence check of section 1 passing (read from the report of
       docs/findings/scripts/sp7_lm_convergence.py given with --convergence). The report's
       three verdicts are recombined here from its items, run B's own record and git:
       the registered rule (both solves ok, the tightened x* within 0.1% of the shipped
       one, the shipped one within 0.002 kg of run B's own record); x* confirmed (each
       chain's independent verification ok within 1e-4 of its P_ref, recomputed from its
       status, P* and P_ref; a miss reads "x* not confirmed", an outcome of the check,
       never "not run as registered"); and run as registered (each verification flew its
       solve's x* and dm, both pads' searches ended ok, each pad flown at its chain's
       budget, every push flown with its chain's context, the same code as run B: git
       diff --quiet run here from run B's commit to each HEAD the parts recorded, and the
       scripts as committed: the recorded sha256 readings equal across readings and
       parts, and to git show run here at each recorded HEAD). Taken as the report
       records them: each part's own readings (HEAD, the code paths' cleanliness, the
       scripts' sha256 on disk), the statuses, x*, dm and P*, the budgets and the push
       contexts' tightened flags. A FAIL names which failed, and a recomputed verdict
       that disagrees with the report's own fails.
       Beside: the report's not_tightened (what the check does not bound). NOT EVALUATED
       without a report, or with one that is not of the registered check (a dry run,
       another case or experiment file), that compares no run B (its report part ran
       without --run-b) or that compares another run B: that check runs after this
       script's first use, alone;
   10. no unexplained offload_nonmonotone, capped gamma* refine (refine_capped) or fired
       structure_fixed_point_cap (this script cannot see an explanation, so any one found
       fails here and goes to the note);
   11. every no_offload case carrying its delta-v shortfall (the sentences below print
       "payload deficit not flown" with it: file B has no payload case).

B. The registered expectations (section 8), printed as met or not met, never as a check:
   E1 (lm_fixed_hot_s1_st raises structure_upper_stack_exceeded at its x*) and E2 (no
   drive_cap event and no cap flag in the recorded runs of the lm_cmd family: the three
   variant runs and their six cases' runs).

C. The fixed sentences of section 8 that fire (RB, LM, HS, TS, CM, SS, TP and PL), each
   filled in word for word as the addendum words it, the bracketed parts and the
   placeholders from the run (<what it isolates> is section 4's whole "Isolates" cell,
   its pre-registration parentheses included): "X t" an x* in tonnes to two decimals,
   "Y%" its share of SP1's uncharged 41,262.9 kg to 0.1%, "D t" a difference in tonnes to
   two decimals (unsigned beside "more" or "less", signed where the sentence prints it
   bare); a difference of two structural x* within R = 3.4 kg reads "the same within the
   resolution" (section 3; R 2.55 kg for two uncharged x* and 6 kg for two costs U - X are
   printed beside). HS's bare uncharged difference stays a number even within R 2.55 kg:
   HS's own rule replaces only <more | less>; this is this script's reading, printed
   beside the sentence whenever it matters, for the orchestrator to confirm. A difference
   beyond R that prints as 0.00 t is shown in kg beside. A no_offload case reads as the
   no-offload phrase in a sentence (its shortfall to three significant figures) and as 0 t
   in a difference; a case that ends search_failed or reference_failed fires nothing; a
   case flagged offload_verify_mismatch is marked "(a bound: offload_verify_mismatch)" in
   every line that prints its x* (the sentences, the beside lines and checks 4, 5 and 9's
   lines), and every sentence that reads it has a bound line beside it. What each
   sentence's numbers rest on goes beside it ("beside:", context only, never a reading),
   with the fixed words of HS, TS, CM, SS and PL that state a setting (the drive, as
   metrics.json records it and as resolved_config.yaml's assist blocks set it; the
   structure settings, the release trigger and stroke, the carriage, the shaft, r)
   compared with the run, the section 8 "read beside" items, the not-blocking flags of
   section 9 and section 8's "what would undercut" conditions evaluated from the numbers.

Its numbers are checks, never findings: they decide whether a number may be cited and which
of the registered sentences the findings note quotes; the note
(docs/findings/RQ1-structural-2d.md) words the findings. The script never flies, sizes or
solves anything and does not import launchsim. Its numbers come from run B's, run A's and
SP1's results files, from the convergence report (a scratch file outside the repository,
read only), from blobs at run B's commit and HEAD (``git show``) and from file hashes; it
computes comparisons against registered values, differences, shares and ratios (PL's r =
P_max / (F_max v_e)), sums (check 7's element sums), maxima and counts. It never writes
inside results/.

Exit code: 0 only when every blocking check passes; 1 when any fails; 2 when none fails but
one is NOT EVALUATED (check 9: no convergence report, or a report that is not of the
registered check, a dry run included, that compares no run B, its report part run without
--run-b, or that compares another run B). The expectations and the sentences never change
it. A check that passes with a note (check 6 "as a bound") carries the note into the
SUMMARY line.

Usage, from the repository root (a few seconds):

    uv run python docs/findings/scripts/sp7_s7b_checks.py --out-text PATH.txt \
        --out-json PATH.json [--run-b RUN_B_DIR] [--convergence DIR/report.json]

Both outputs are written (UTF-8, LF) to the paths given, never inside results/; the text
report is also printed.
"""

from __future__ import annotations

import argparse
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
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
"""The repository root (this file is docs/findings/scripts/sp7_s7b_checks.py)."""
SCRIPT = "docs/findings/scripts/sp7_s7b_checks.py"
"""This script, relative to the repository (the report's header names it)."""
RESULTS = REPO / "results"
"""The results tree: read only, and refused as an output location."""
RUN_B = RESULTS / "silo_drive_2d" / "20261103T231946Z"
"""Run B: ``uv run python -m launchsim run experiments/silo_drive_2d.yaml`` from 642e11e
(S7b's brief: started 2026-11-03T23:19:44Z, ended 2026-11-04T00:01:31Z, exit 0)."""
RUN_A = RESULTS / "silo_structure_2d" / "20261016T171513Z"
"""Run A (file A, from 1b5f9d4): the cross-commit check's silo_cold_s1_st and the read-beside
hot-ramp pair."""
SP1_RUN = RESULTS / "silo_offload_2d" / "20261003T112934Z"
"""SP1's run of experiments/silo_offload_2d.yaml: the cross-commit check's silo_cold_s1."""
CONVERGENCE_SCRIPT = "docs/findings/scripts/sp7_lm_convergence.py"
"""The script whose report check 9 reads (the addendum, section 1)."""
FILE_B = "experiments/silo_drive_2d.yaml"
"""File B, as the convergence report names it."""
CONVERGENCE_CASE = "lm_fixed_s1_st"
"""The convergence check's registered case (the addendum, section 1)."""
CONVERGENCE_SCRIPTS = (CONVERGENCE_SCRIPT, "docs/findings/scripts/sp7_convergence.py")
"""The convergence check's own scripts (its SCRIPT_PATHS: section 1's "a committed
script")."""
CONVERGENCE_PARTS = (
    "shipped-pad",
    "shipped-solve",
    "shipped-verify",
    "tightened-pad",
    "tightened-solve",
    "tightened-verify",
)
"""The convergence check's parts before its report (each records its git readings)."""
CONVERGENCE_REPORT_PART = "report"
"""The convergence check's report part (it records its scripts' readings too)."""
CODE_PATHS = ("src", "configs", "experiments", "pyproject.toml", "uv.lock", "tests")
"""The paths of "from the same code as run B" (the addendum, section 1: ``git diff --quiet
<run B's commit> HEAD -- src configs experiments pyproject.toml uv.lock tests``)."""
READINGS = ("at_import", "at_record")
"""A convergence part's two git readings: when its process loaded its modules and when it
wrote its record."""
RUN_B_METRICS_SHA256 = "08278d414db0063e9c4dcf641ae9f5ddca91ce87229cc908a8bce29cbaf7b488"
"""Run B's metrics.json sha256 at the run's end (S7b's brief; provenance, below)."""
RUN_B_TREE_SHA256 = "c67572aaca8832a5f703be8da498c952a656e67325f25813c2de2da30dc54f7d"
"""Run B's fingerprints at the run's end (S7b's brief): metrics.json's sha256, and the
sha256 of ``find DIR -type f | sort | xargs sha256sum`` run from the repository root in Git
Bash (lines "<sha256> *<path>"). Provenance, printed beside; not a check of section 9."""

# ----------------------------------------------------------------- registered values

P_REF_KG = 26054.396243494975
"""File B's P_ref [kg] (the addendum, section 3: SP1's, tests/data/silo_offload_2d_record.json)."""
SP1_SILO_COLD_S1_KG = 41262.90803733282
"""SP1's silo_cold_s1 x* [kg] (section 3's cross-commit value; section 9's lm_cmd value,
written there as 41,262.908 kg)."""
RUN_A_SILO_COLD_S1_ST_KG = 11420.246638573297
"""Run A's silo_cold_s1_st x* [kg] (section 3's cross-commit value)."""
RUN_A_HOT_RAMP_KG = {"silo_hot_ramp_s1": 46013.437, "silo_hot_ramp_s1_st": 18273.917}
"""Run A's silo_hot_ramp_on_track pair as section 8 writes it [kg] (read beside lm_cmd_hot's
pair; run A's records are read at full precision)."""
STRUCTURE_SHA256 = {
    "configs/structures/generic_f9_class_2d.yaml": (
        "a0516875d3c3b64de32f8ed1ceeb1f71a6c67694f7b07306b242522dd3cc8232"
    ),
    "configs/structures/generic_f9_class_2d_readme_loads.yaml": (
        "a850de94ae24ab28941789d7a17da3c3ff5b48f51b762373fc99b6e22edc2997"
    ),
}
"""Part 1, section 12's digests of the frozen structure files (the addendum's section 12;
file B names the first)."""
STRUCTURE_DIR = "configs/structures/"
"""The prefix of a structure file's path in a digest record (check 8 checks those)."""
VEHICLE_FILE = "configs/vehicles/generic_f9_class_2d.yaml"
"""The vehicle file file B names (its digest is provenance, below)."""
VEHICLE_SHA256 = "a8ea5203da658b6d86d690ea26b784fa6004f2b990fe2f4b7f829c9a799e59a9"
"""The addendum's section 12: the vehicle file's digest (provenance, printed beside; section
9 blocks on no vehicle digest)."""
SP1_UNCHARGED_KG = 41262.9
"""SP1's uncharged 41,262.9 kg as section 8 writes it: the denominator of "Y%"."""
HALF_KG = 20631.45
"""Section 8's RB threshold (part 1's R tests): 50% of 41,262.9 kg [kg]."""

# ------------------------------------------------------------------------ thresholds

PAD_TOL_KG = 0.002
"""A pad's P* must equal P_ref within this [kg] (section 9)."""
CROSS_COMMIT_TOL_KG = 0.002
"""The cross-commit check's tolerance [kg] (section 9)."""
LM_CMD_TOL_KG = 0.25
"""lm_cmd's uncharged x* against SP1's [kg] (section 9; design 4.10)."""
VERIFY_REL = 1e-4
"""A structural case's verification within this times P_ref (section 9)."""
DM_TOL_KG = 1e-6
"""xv_dry_mass_delta_kg against dm1 + dm2 [kg] (section 9)."""
CLOSURE_TOL_MPS = 1e-5
"""checks.closure_tol_mps (part 1, section 9's bug_suspect list) [m/s]."""
CONV_REL_TOL = 1e-3
"""The convergence check's pass rule: the tightened x* within 0.1% of the shipped one."""
CONV_RUN_B_TOL_KG = 0.002
"""The convergence check: the shipped x* equal to run B's within this [kg]."""
CONV_VERIFY_REL = 1e-4
"""The convergence check's verification rule: each chain's independent payload search ok
with |P* - P_ref| <= this times the chain's P_ref (section 1; file B's
checks.search_final_flag_rel, as ``offload.verification_from_record`` applies it)."""
R_X_KG = 3.4
"""Section 3's resolution of two structural x* at the same P_ref [kg]."""
R_U_KG = 2.55
"""Section 3's resolution of two uncharged x* at the same P_ref [kg]."""
R_COST_KG = 6.0
"""Section 3's resolution of two structural costs U - X (their sum, section 8's 6 kg) [kg]."""
R_MOVE_FRACTION = 0.05
"""Section 3: each R moves by at most about 5% on the force-law variants; a difference
within this fraction of R either side is printed beside as a near call."""
SPEED_TIE_MPS = 1e-9
"""Two release speeds within this read as equal in the "what would undercut" block, and a
target-speed release counts as at v_e within it (the release_speed_not_reached flag's 1e-9
m/s tolerance: section 5, check 3; section 7); not a registered rule of a sentence."""
TRUNCATE_CHARS = 300
"""A recorded line or flag quoted in a check's lines is cut to this many characters (S7a's
checks' length)."""

# ------------------------------------------------------- the fixed sentences' fixed words

CARRIAGE_22T_KG = 22000.0
"""CM's "22 t carriage" [kg] (section 8; section 4's lm_fixed_sled22)."""
STROKE_M = 100.0
"""TS's "the 100 m stroke" [m] (section 8; section 4: a vertical 100 m stroke)."""
SEALED_SHAFT = {"shaft": "sealed", "shaft_bore_m": 5.24, "shaft_gap_m": 5.0, "shaft_gamma": 1.4}
"""SS's "sealed shaft (bore 5.24 m, gap 5 m)" and section 4's gamma 1.4 (lm_fixed_sealed)."""
VENTED_SHAFT = "vented"
"""SS's "the vented lm_fixed": lm_fixed's shaft setting."""
SEALED_WORDS = {
    "shaft": "'In the sealed shaft'",
    "shaft_bore_m": "'bore 5.24 m'",
    "shaft_gap_m": "'gap 5 m'",
    "shaft_gamma": "section 4's 'gamma 1.4'; not in the sentence",
}
"""Where each of SEALED_SHAFT's values comes from, as printed beside SS."""
SHAFT_KEYS = tuple(SEALED_SHAFT)
"""The shaft settings read from resolved_config.yaml, in SEALED_SHAFT's order."""
PL_R = 0.7
"""PL's "r = 0.7" (section 8; section 4's lm_fixed_r07: r = P_max / (F_max v_e))."""
PL_R_REL_TOL = 1e-12
"""r recomputed from the run's F_max, P_max and v_e equals PL_R within this relative
tolerance (floating-point rounding only; this script's choice)."""
TRIGGER_TARGET = "target_speed"
"""TS's "released where its speed reaches v_e": lm_fixed_target_s1_st's release_trigger."""
TRIGGER_TRACK_END = "track_end"
"""TS's "released at the track end": lm_fixed_s1_st's release_trigger."""
DRIVE_KEYS = (
    "push_control_law",
    "push_force_max_N",
    "push_power_max_W",
    "push_rise_time_s",
    "push_accel_command_mps2",
    "push_stop_taper_m",
    "push_release_speed_mps",
    "carriage_mass_kg",
    "stroke_m",
)
"""HS's and SS's "the same drive", as metrics.json records it for a variant run (its assist
block's control, accel_command_g, force_max_kN, power_max_MW, force_rise_time_s,
stop_taper_m, release_speed_mps, carriage_mass_t and stroke_m, in SI). The rest of the
assist block (drive_efficiency, exhaust_impingement_fraction, brake_decel_g, the track, and
for HS the shaft), which metrics.json does not record, is compared from
resolved_config.yaml beside it (``assist_line``)."""
STRUCTURE_SETTING_KEYS = (
    "structure_file",
    "structure_set",
    "structure_sizing",
    "structure_dynamic",
    "structure_entry",
    "structure_margin",
    "structure_envelope_cap_g",
    "structure_overrides",
    "structure_plausibility_scaled",
)
"""HS's "the same structure settings": the structure file and the case's structure block
(set, sizing, dynamic, entry, margin, envelope_cap_g, overrides, plausibility_scaled) as a
structural case record carries them."""

# --------------------------------------------------------------------- recorded text

BUG_SUSPECT = "bug_suspect"
"""The status string of a bug_suspect run or comparison (check 1 searches every string)."""
NO_BUG_SUSPECT_LINE = "No run and no comparison is bug_suspect."
"""The blocked-findings line of a summary with nothing bug_suspect (summary.blocked_lines)."""
FINDINGS_BLOCKED_PREFIX = "Findings are blocked until these are investigated (status bug_suspect"
"""summary.FINDINGS_BLOCKED, the line naming bug_suspect runs and comparisons."""
PAD_CONTROL_BLOCKED_PREFIX = (
    "Findings are blocked until these are investigated (a stage-1 pad control failed"
)
"""summary.PAD_CONTROL_BLOCKED, the line naming failed stage-1 pad controls."""
OK_STATUS = "ok"
"""An offload case's (and a payload search's) status when it ended with a solution."""
NO_OFFLOAD_STATUS = "no_offload"
"""An offload case's status when x = 0 already misses P_ref (it carries a shortfall)."""
SOLVABLE = (OK_STATUS, NO_OFFLOAD_STATUS)
"""The case statuses a sentence reads; any other (search_failed, reference_failed) fires
nothing."""
STAGE1_MODE = "stage1"
"""A pad control's mode for the stage-1 consistency test (check 3)."""
CONSISTENCY_PASS = "pass"
"""A pad control's recorded consistency verdict when it passes (check 3)."""
INSERTED = "inserted"
"""A run's status when it reached the target orbit (the pad, check 2)."""
PAD_RUN = "pad"
"""The pad baseline's run name, and offload.reference's value (check 2)."""
VERIFY_MISMATCH_FLAG = "offload_verify_mismatch"
"""offload.py's flag on a case whose verification misses P_ref (check 6)."""
FIXED_POINT_CAP_FLAG = "structure_fixed_point_cap"
"""The structure flag record of the sizing's fixed point; blocking only when fired."""
BLOCKING_FLAGS = ("offload_nonmonotone", "refine_capped", FIXED_POINT_CAP_FLAG)
"""Flag names section 9 blocks on: a non-monotone offload search, a capped gamma* refine
(search.py's refine_capped) and a fired structure fixed-point cap."""
UPPER_STACK_FLAG = "structure_upper_stack_exceeded"
"""The upper-stack flag (E1; not blocking, section 9)."""
RELEASE_FLAG = "structure_release_unload"
"""The release flag (TP; not blocking, section 9)."""
PAYLOAD_LIMIT_FLAG = "structure_payload_limit"
"""The payload-limit flag (TP; not blocking, section 9)."""
RELEASE_SPEED_FLAG = "release_speed_not_reached"
"""The target-speed release's flag (not blocking only where section 9 says, section E)."""
DRIVE_CAP_EVENT = "drive_cap"
"""The events.csv event of a linear motor's acceleration cap binding (E2)."""
DRIVE_CAP_END_EVENT = "drive_cap_end"
"""The events.csv event of the cap's end (E2; counted beside)."""
OFFLOAD_PREFIX = "offload:"
"""offload.py's prefix of an offload solve's flags."""
ABSCISSA_NOTE = "(P = offload x)"
"""offload.py's prefixes of a solve's flags (an inner search flag carries both)."""
COMPARISON_STATUS_KEYS = ("screening_status", "decomposition_status", "xv_status")
"""The comparison and decomposition status fields whose values check 1 tallies."""
YAML_SHA = re.compile(r"^(?P<indent>\s*)(?P<key>\w*sha256):\s*['\"]?(?P<digest>[0-9A-Fa-f]{64})")
"""A ``*sha256:`` line of a YAML file (S7a's checks, copied)."""
YAML_FILE = re.compile(r"^(?P<indent>\s*)(?:file|structure_file):\s*['\"]?(?P<path>[^'\"\s]+)")
"""A ``file:`` or ``structure_file:`` line of a YAML file (S7a's checks, copied)."""
BOUND_MARK = f"(a bound: {VERIFY_MISMATCH_FLAG})"
"""The mark after a flagged case's x* wherever it is printed (check 6; section 9)."""
NOTHING_IN_SHAFT = (
    "(nothing models the exhaust in the shaft: back-pressure, heating, the carriage in the "
    "plume, which favours the hot starts)"
)
"""HS's fixed caveat, word for word."""

# -------------------------------------------------------------------- file B's cases

LM_VARIANTS = (
    "lm_cmd",
    "lm_cmd_taper",
    "lm_cmd_hot",
    "lm_fixed",
    "lm_fixed_target",
    "lm_fixed_r07",
    "lm_fixed_hot",
    "lm_fixed_sled22",
    "lm_fixed_sealed",
)
"""The nine linear-motor variants in section 4's order."""
ISOLATES = {
    "lm_cmd": (
        "constant_accel with a flown ramp (its uncharged x* equals SP1's within 0.25 kg for "
        "a cold start: pre-registered by the design)"
    ),
    "lm_cmd_taper": "the cost of a gentle stop against the release flag",
    "lm_cmd_hot": "the hot start under a structure-protecting drive (thrust replaces motor force)",
    "lm_fixed": "a facility sized for the full load, run at full force on a lighter stack",
    "lm_fixed_target": "the same exit speed from a fixed facility",
    "lm_fixed_r07": "a power-limited drive",
    "lm_fixed_hot": "the force-limited hot start (pre-registered to raise the upper-stack flag)",
    "lm_fixed_sled22": "carriage mass at a fixed force",
    "lm_fixed_sealed": "the air column",
}
"""<what it isolates>: section 4's "Isolates (design 4.10)" cells, each whole and word for
word (lm_cmd's and lm_fixed_hot's pre-registration parentheses included)."""
LM_CMD_FAMILY = ("lm_cmd", "lm_cmd_taper", "lm_cmd_hot")
"""E2's variants: the acceleration law."""
COLD = "silo_cold"
"""The comparison basis variant (file A's silo_cold, copied into file B)."""


def uncharged(variant: str) -> str:
    """A variant's uncharged stage-1 case name."""
    return f"{variant}_s1"


def structural(variant: str) -> str:
    """A variant's central structural stage-1 case name."""
    return f"{variant}_s1_st"


# --------------------------------------------------------------------------- records


@dataclass(frozen=True)
class CheckResult:
    """One blocking check's verdict (PASS, FAIL or NOT EVALUATED) with the note that
    qualifies it (why it failed, or "as a bound"; empty when there is none), the lines
    showing its numbers, what it blocks and where that scope comes from (section 9's own
    words, part 1's, this script's reading of section 9's general rule, or section 9's
    words with this script's reading of the rest)."""

    number: int
    title: str
    status: str
    lines: list[str]
    blocks: str
    source: str
    note: str = ""


Verdict = tuple[bool | None, list[str], str]
"""A check's verdict (True, False, or None for NOT EVALUATED), its lines and its note."""


@dataclass(frozen=True)
class Reading:
    """One expectation or sentence: its id, its subject, the rule that fired (or why
    nothing did), its text and the lines printed beside it."""

    rid: str
    subject: str
    rule: str
    text: str
    beside: list[str] = field(default_factory=list)
    values: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- readers


def rel(path: Path) -> str:
    """A path relative to the repository, with forward slashes (absolute when outside)."""
    try:
        return path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def shown(path: Path) -> str:
    """A path as the report prints it: relative to the repository, or, outside it, only
    its last folder and name (no machine-specific path in a committed copy), with the
    file's sha256."""
    resolved = path.resolve()
    if resolved == REPO or REPO in resolved.parents:
        where = rel(resolved)
    else:
        where = f"(outside the repository) {resolved.parent.name}/{resolved.name}"
    return f"{where} (sha256 {sha256(resolved.read_bytes())})"


@cache
def read_json(path: Path) -> Any:
    """A JSON file's content (read once; never modified)."""
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(data: bytes) -> str:
    """The hex sha256 of bytes."""
    return hashlib.sha256(data).hexdigest()


def git_blob(rev: str, relpath: str) -> bytes | None:
    """The bytes of ``relpath`` at commit ``rev`` (``git show``), None on a git failure."""
    proc = subprocess.run(
        ["git", "show", f"{rev}:{relpath}"], cwd=REPO, capture_output=True, check=False
    )
    return proc.stdout if proc.returncode == 0 else None


def git_diff_quiet(base: str, head: str) -> bool | None:
    """Whether ``git diff --quiet base head -- CODE_PATHS`` exits 0 (None on a git error,
    an unknown commit included)."""
    proc = subprocess.run(
        ["git", "diff", "--quiet", base, head, "--", *CODE_PATHS],
        cwd=REPO,
        capture_output=True,
        check=False,
    )
    return proc.returncode == 0 if proc.returncode in (0, 1) else None


def git_porcelain(relpath: str) -> str:
    """``git status --porcelain -- relpath``'s output, stripped ("" when the file is clean
    in the working tree; "?" on a git failure)."""
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--", relpath],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "?"


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


def tree_sha256(root: Path) -> str:
    """The directory fingerprint of RUN_B_TREE_SHA256's method: each file's
    "<sha256> *<path>" line, its path relative to the repository, sorted, hashed."""
    paths = sorted(rel(p) for p in root.rglob("*") if p.is_file())
    text = "".join(f"{sha256((REPO / p).read_bytes())} *{p}\n" for p in paths)
    return sha256(text.encode("utf-8"))


def finite(value: Any) -> bool:
    """Whether a recorded value is a finite number (None, a bool or a string is not)."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return False
    return math.isfinite(value)


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
    """(record label, path, list) of every ``flags`` or ``structure_flags`` list in a JSON
    tree; the label is the nearest enclosing record's ``name`` (or ``run``), a run's key
    under a ``runs`` mapping, else ``label`` (S7a's checks, copied)."""
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


def flag_entries(items: Sequence[Any]) -> Iterator[tuple[str, bool, Any]]:
    """(name, fired, item) of each entry of a flags list: a string is a fired flag; a
    structure flag record (name, fired) is fired when its ``fired`` is true."""
    for item in items:
        if isinstance(item, str):
            yield flag_name(item), True, item
        elif isinstance(item, Mapping) and isinstance(item.get("name"), str):
            yield item["name"], bool(item.get("fired")), item


def yaml_sha_records(path: Path) -> list[tuple[int, str | None, str]]:
    """(line number, file path, digest) of every ``*sha256:`` line of a YAML file, its file
    the nearest ``file:`` or ``structure_file:`` line at the same indent in the same block
    (searched upward, then downward; S7a's checks, copied)."""
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


def event_names(run_dir: Path) -> list[tuple[float, str, str]]:
    """(t_s, event, phase) of every row of a run directory's events.csv."""
    with (run_dir / "events.csv").open(encoding="utf-8", newline="") as fh:
        return [(float(r["t_s"]), r["event"], r["phase"]) for r in csv.DictReader(fh)]


@dataclass(frozen=True)
class RunB:
    """Run B's records: its directory, metrics.json and the views the checks read."""

    root: Path

    @property
    def metrics(self) -> dict[str, Any]:
        """metrics.json."""
        return read_json(self.root / "metrics.json")

    @property
    def offload(self) -> dict[str, Any]:
        """metrics.json's offload block."""
        return self.metrics["offload"]

    def case(self, name: str) -> dict[str, Any]:
        """An offload case record by name (KeyError naming it if absent)."""
        for c in self.offload["cases"]:
            if c["name"] == name:
                return c
        raise KeyError(f"run B has no offload case {name!r}")

    def case_run(self, name: str) -> dict[str, Any]:
        """A case's recorded run metrics (offload.runs[name]): at x*, or at 0 for
        no_offload."""
        return self.offload["runs"][name]

    def variant_run(self, name: str) -> dict[str, Any]:
        """A variant (or the pad) run's metrics (runs[name])."""
        return self.metrics["runs"][name]

    def structural_cases(self) -> list[dict[str, Any]]:
        """The case records that carry a modelled structure."""
        return [c for c in self.offload["cases"] if c.get("structure_charged")]

    @property
    def git(self) -> dict[str, Any]:
        """The run's git record."""
        return self.metrics["git"]


# ----------------------------------------------------------------------- formatting


def t2(kg: float) -> str:
    """kg in tonnes to two decimals ("X t" without the unit)."""
    return f"{kg / 1000.0:.2f}"


def signed_t(kg: float) -> str:
    """A signed difference [kg] in tonnes to two decimals ("D t" without the unit; section
    8: signed), its sign kept when it rounds to 0.00 ("-0.00" for a small negative one)."""
    return f"{'-' if kg < 0 else '+'}{t2(abs(kg))}"


def pct_of(kg: float, of_kg: float) -> str:
    """kg as a share of of_kg [kg] to 0.1%."""
    return f"{100.0 * kg / of_kg:.1f}%"


def pct(kg: float) -> str:
    """kg as a share of SP1's uncharged 41,262.9 kg to 0.1% ("Y%")."""
    return pct_of(kg, SP1_UNCHARGED_KG)


def sig3(value: float) -> str:
    """A number to three significant figures, in fixed notation (a no_offload case's
    shortfall [m/s], so that a small one never prints as 0.0)."""
    if value == 0.0 or not math.isfinite(value):
        return f"{value:g}"
    digits = max(0, 2 - math.floor(math.log10(abs(value))))
    return f"{value:.{digits}f}"


def mn(newtons: float) -> str:
    """A force [N] in MN to three decimals."""
    return f"{newtons / 1e6:.3f}"


def mj(joules: float) -> str:
    """An energy [J] in MJ to one decimal."""
    return f"{joules / 1e6:.1f}"


def mps(v: float) -> str:
    """A speed [m/s] to two decimals."""
    return f"{v:.2f}"


def kpa(pa: float) -> str:
    """A pressure [Pa] in kPa to the kPa."""
    return f"{pa / 1000.0:.0f}"


def g0s(g: float) -> str:
    """A load [g0] to two decimals."""
    return f"{g:.2f}"


def within(d_kg: float, r_kg: float) -> bool:
    """Whether a difference reads "the same within the resolution" (|d| <= R)."""
    return abs(d_kg) <= r_kg


def near_r(d_kg: float, r_kg: float) -> bool:
    """Whether |d| lies within R_MOVE_FRACTION of R either side (a near call, beside)."""
    return abs(abs(d_kg) - r_kg) <= R_MOVE_FRACTION * r_kg


def more_less(d_kg: float, r_kg: float = R_X_KG) -> str:
    """<D t more | D t less | the same within the resolution> for d = X - X_ref [kg]."""
    if within(d_kg, r_kg):
        return "the same within the resolution"
    return f"{t2(abs(d_kg))} t {'more' if d_kg > 0 else 'less'}"


def diff_beside(label: str, d_kg: float, r_kg: float) -> str:
    """A difference [kg] with its R and the reading, for a beside line; a difference beyond
    R that prints as 0.00 t in a sentence says so (the kg value is the reading)."""
    note = ""
    if near_r(d_kg, r_kg):
        note = f"; a near call: |D| within {R_MOVE_FRACTION:.0%} of R, which moves by up to that"
    if not within(d_kg, r_kg) and t2(abs(d_kg)) == t2(0.0):
        note += f"; beyond R, but {t2(0.0)} t to two decimals: read this kg value"
    reading = "within R" if within(d_kg, r_kg) else "beyond R"
    return f"{label} {d_kg:+.4f} kg against R {r_kg:g} kg: {reading}{note}"


def fixed(label: str, run_value: Any, want: Any, equal: bool, words: str) -> str:
    """One fixed word of a sentence against the run: the run's value, the value the words
    stand for (``words``: the sentence's, or section 4's, quoted) and "equal" or
    "DIFFERS"."""
    verdict = "equal" if equal else "DIFFERS"
    return f"{label} {run_value!r} against {want!r} ({words}): {verdict}"


# -------------------------------------------------------------------- the case values


@dataclass(frozen=True)
class CaseValue:
    """A case's status and x* as the sentences read them, and whether the case is flagged
    offload_verify_mismatch (its x* then a bound: check 6, section 9)."""

    name: str
    status: str
    x_kg: float | None
    shortfall_mps: float | None
    flagged: bool = False

    @property
    def evaluable(self) -> bool:
        """Whether a sentence reads it (ok or no_offload)."""
        return self.status in SOLVABLE

    @property
    def x_for_diff(self) -> float:
        """x* in a difference: a no_offload case counts as 0 t."""
        if self.status == NO_OFFLOAD_STATUS:
            return 0.0
        assert self.x_kg is not None
        return self.x_kg

    @property
    def mark(self) -> str:
        """BOUND_MARK after a space for a flagged case, else nothing."""
        return f" {BOUND_MARK}" if self.flagged else ""

    @property
    def label(self) -> str:
        """The case's name, marked as a bound when flagged (beside lines)."""
        return f"{self.name}{self.mark}"

    def tonnes(self) -> str:
        """ "X t" of an ok case, marked as a bound when flagged."""
        assert self.x_kg is not None
        return f"{t2(self.x_kg)} t{self.mark}"

    def no_offload_phrase(self, at_p_ref: bool = False) -> str:
        """Section 8's no-offload phrase (file B has no payload case), the shortfall to
        three significant figures."""
        s = "?" if self.shortfall_mps is None else sig3(self.shortfall_mps)
        head = "no offload at P_ref" if at_p_ref else "no offload"
        return (
            f"{head} ({s} m/s of delta-v short of P_ref at x = 0; payload deficit not "
            "flown: no payload case at these settings)"
        )

    def phrase(self) -> str:
        """ "X t", or the no-offload phrase for a no_offload case (never "0 t")."""
        if self.status == NO_OFFLOAD_STATUS:
            return self.no_offload_phrase()
        return self.tonnes()


def case_value(b: RunB, name: str) -> CaseValue:
    """The CaseValue of a run B case."""
    c = b.case(name)
    x_kg = c.get("offload_kg")
    short_mps = (c.get("solve") or {}).get("dv_shortfall_mps")
    return CaseValue(
        name,
        str(c["status"]),
        float(x_kg) if finite(x_kg) else None,
        float(short_mps) if finite(short_mps) else None,
        verify_flagged(c),
    )


def verify_flagged(case: Mapping[str, Any]) -> bool:
    """Whether a case record carries offload_verify_mismatch among its flags."""
    return any(VERIFY_MISMATCH_FLAG in str(f) for f in case.get("flags") or [])


def bound_beside(*values: CaseValue) -> list[str]:
    """A beside line for each flagged case a sentence reads: its x*, and every difference
    that uses it, is a bound, not a point value."""
    return [
        f"{v.name} is flagged {VERIFY_MISMATCH_FLAG} (check 6; section 9): its x*, and every "
        "difference above that uses it, is a bound, not a point value"
        for v in values
        if v.flagged
    ]


def not_read(*values: CaseValue) -> str | None:
    """The reason a sentence fires nothing (a case neither ok nor no_offload), else None."""
    bad = [f"{v.name} ended {v.status}" for v in values if not v.evaluable]
    return "; ".join(bad) + ": fires nothing" if bad else None


def cost(u: CaseValue, x: CaseValue) -> float:
    """The structure's offload cost U - X [kg]."""
    return u.x_for_diff - x.x_for_diff


# ------------------------------------------------------------------- blocking checks


def check_bug_suspect(b: RunB) -> tuple[bool, list[str]]:
    """Check 1: no run or comparison bug_suspect."""
    lines: list[str] = []
    problems: list[str] = []
    text = (b.root / "summary.md").read_text(encoding="utf-8").splitlines()
    n_line = sum(1 for t in text if t.strip() == NO_BUG_SUSPECT_LINE)
    blocked = [t for t in text if t.startswith(FINDINGS_BLOCKED_PREFIX)]
    if blocked:
        problems.append(f"summary.md: {blocked[0][:TRUNCATE_CHARS]}")
    elif n_line != 1:
        problems.append(f"summary.md: {n_line} lines '{NO_BUG_SUSPECT_LINE}' (expected 1)")
    lines.append(
        f"summary.md: '{NO_BUG_SUSPECT_LINE}' x{n_line}; blocked-findings lines: {len(blocked)}"
    )
    tally: dict[str, Counter[str]] = defaultdict(Counter)
    n_strings = 0
    for where, key, value, _parent in iter_items(b.metrics):
        if isinstance(value, str):
            n_strings += 1
            if value == BUG_SUSPECT:
                problems.append(f"metrics.json{where} = {BUG_SUSPECT}")
            if key in COMPARISON_STATUS_KEYS:
                tally[key][value] += 1
    counts = "; ".join(
        f"{key} x{sum(tally[key].values())} ("
        + ", ".join(f"{v} {n}" for v, n in sorted(tally[key].items()))
        + ")"
        for key in COMPARISON_STATUS_KEYS
        if tally[key]
    )
    lines.append(f"metrics.json: {n_strings} string values read, none '{BUG_SUSPECT}'; {counts}")
    runs = {**b.metrics["runs"], **b.offload["runs"]}
    failed = {n: r.get("run_checks_failed") for n, r in runs.items() if r.get("run_checks_failed")}
    for n, f in failed.items():
        problems.append(f"run {n}: run_checks_failed {f}")
    lines.append(
        f"run checks (closure, loss identity, insertion e): {len(runs)} runs (variants, pad, "
        f"cases, pad control), run_checks_failed empty on {len(runs) - len(failed)}"
    )
    worst_mps = 0.0
    n_dec = 0
    for c in b.offload["cases"]:
        dec = c.get("decomposition") or {}
        residual_mps = dec.get("xv_residual_mps")
        if finite(residual_mps):
            n_dec += 1
            worst_mps = max(worst_mps, abs(float(residual_mps)))
            if abs(float(residual_mps)) > CLOSURE_TOL_MPS:
                problems.append(f"{c['name']}: decomposition residual {residual_mps!r} m/s")
    lines.append(
        f"cross-vehicle decompositions: {n_dec} residuals, worst |r| {worst_mps:.3e} m/s against "
        f"closure_tol_mps {CLOSURE_TOL_MPS:g} m/s"
    )
    lines += [f"FOUND: {p}" for p in problems]
    return not problems, lines


def check_pad(b: RunB) -> tuple[bool, list[str]]:
    """Check 2: the pad not reference_failed, its P* within PAD_TOL_KG of P_ref."""
    pad = b.variant_run(PAD_RUN)
    p_star_kg = float(pad["payload_kg"])
    ok_pad = (
        abs(p_star_kg - P_REF_KG) <= PAD_TOL_KG
        and pad.get("status") == INSERTED
        and pad.get("search_status") == OK_STATUS
    )
    recorded_kg = float(b.offload["reference_payload_kg"])
    ok_ref = abs(recorded_kg - P_REF_KG) <= PAD_TOL_KG and b.offload.get("reference") == PAD_RUN
    refs_kg = [float(c["reference_payload_kg"]) for c in b.offload["cases"]]
    ok_cases = all(r == recorded_kg for r in refs_kg)
    lines = [
        f"pad: P* {p_star_kg!r} kg against P_ref {P_REF_KG!r} kg, diff "
        f"{p_star_kg - P_REF_KG:+.3e} kg, |.| <= {PAD_TOL_KG} kg: "
        f"{'yes' if abs(p_star_kg - P_REF_KG) <= PAD_TOL_KG else 'NO'} "
        f"(status {pad.get('status')}, search {pad.get('search_status')})",
        f"offload.reference {b.offload.get('reference')!r}, reference_payload_kg {recorded_kg!r} "
        f"kg, diff {recorded_kg - P_REF_KG:+.3e} kg against the registered P_ref",
        f"every case's reference_payload_kg equal to it: {ok_cases} ({len(refs_kg)} cases)",
    ]
    return ok_pad and ok_ref and ok_cases, lines


def check_pad_control(b: RunB) -> tuple[bool, list[str]]:
    """Check 3: the stage-1 pad control passes its consistency test."""
    lines: list[str] = []
    controls = [c for c in b.offload.get("pad_controls") or [] if c.get("mode") == STAGE1_MODE]
    passed = bool(controls)
    if not controls:
        lines.append("no stage-1 pad control recorded")
    for c in controls:
        ok = c.get("consistency") == CONSISTENCY_PASS
        passed &= ok
        lines.append(
            f"{c['run']}: status {c['status']}, x_pad {c['offload_kg']!r} kg, m_res(0) "
            f"{c['m_res_kg']:.6g} kg, dv_margin {c['dv_margin_mps']:.6g} m/s, bound "
            f"{c['bound_kg']:.6g} kg, within_bound {c['within_bound']}, resolution effect "
            f"{c['resolution_effect']}, flags {len(c.get('flags') or [])}: consistency "
            f"{c.get('consistency')}"
        )
    summary = (b.root / "summary.md").read_text(encoding="utf-8").splitlines()
    blocked = [t for t in summary if t.startswith(PAD_CONTROL_BLOCKED_PREFIX)]
    passed &= not blocked
    lines.append(
        "summary.md: "
        + (
            f"BLOCKED: {blocked[0][:TRUNCATE_CHARS]}"
            if blocked
            else "no pad-control blocked-findings line"
        )
    )
    return passed, lines


def _record_x(root: Path, name: str) -> tuple[float, str]:
    """(x* [kg], status) of a case in another results directory's metrics.json."""
    for c in read_json(root / "metrics.json")["offload"]["cases"]:
        if c["name"] == name:
            return float(c["offload_kg"]), str(c["status"])
    raise KeyError(f"{rel(root)} has no offload case {name!r}")


def check_cross_commit(b: RunB) -> tuple[bool, list[str]]:
    """Check 4: silo_cold_s1 against SP1's and silo_cold_s1_st against run A's, each
    within CROSS_COMMIT_TOL_KG (the registered values, and the records they come from)."""
    lines: list[str] = []
    passed = True
    for name, registered_kg, root, who in (
        (uncharged(COLD), SP1_SILO_COLD_S1_KG, SP1_RUN, "SP1's"),
        (structural(COLD), RUN_A_SILO_COLD_S1_ST_KG, RUN_A, "run A's"),
    ):
        v = case_value(b, name)
        rec_x_kg, rec_status = _record_x(root, name)
        git = read_json(root / "metrics.json")["git"]
        if v.x_kg is None or v.status != OK_STATUS:
            passed = False
            lines.append(f"{name}: status {v.status}, x* {v.x_kg}: NOT COMPARABLE")
            continue
        d_reg_kg, d_rec_kg = v.x_kg - registered_kg, v.x_kg - rec_x_kg
        ok = abs(d_reg_kg) <= CROSS_COMMIT_TOL_KG and abs(d_rec_kg) <= CROSS_COMMIT_TOL_KG
        passed &= ok
        lines.append(
            f"{name}: run B x* {v.x_kg!r} kg{v.mark} against {who} {registered_kg!r} kg "
            "(section 3), diff "
            f"{d_reg_kg:+.3e} kg, |.| <= {CROSS_COMMIT_TOL_KG} kg: "
            f"{'yes' if abs(d_reg_kg) <= CROSS_COMMIT_TOL_KG else 'NO'}; against {who} record "
            f"{rec_x_kg!r} kg ({rel(root)}/metrics.json, git {git['hash']}, status {rec_status}), "
            f"diff {d_rec_kg:+.3e} kg"
        )
    lines.append(
        f"run B's git {b.git['hash']} (dirty {b.git['dirty']}); run A's "
        f"{read_json(RUN_A / 'metrics.json')['git']['hash']}; SP1's "
        f"{read_json(SP1_RUN / 'metrics.json')['git']['hash']}"
    )
    return passed, lines


def check_lm_cmd(b: RunB) -> tuple[bool, list[str]]:
    """Check 5: lm_cmd's uncharged x* within LM_CMD_TOL_KG of SP1's."""
    v = case_value(b, uncharged("lm_cmd"))
    if v.x_kg is None or v.status != OK_STATUS:
        return False, [f"{v.name}: status {v.status}, x* {v.x_kg}: NOT COMPARABLE"]
    d_kg = v.x_kg - SP1_SILO_COLD_S1_KG
    ok = abs(d_kg) <= LM_CMD_TOL_KG
    return ok, [
        f"{v.name}: x* {v.x_kg!r} kg{v.mark} against SP1's {SP1_SILO_COLD_S1_KG!r} kg (section 9: "
        f"41,262.908 kg), diff {d_kg:+.6f} kg, |.| <= {LM_CMD_TOL_KG} kg: {'yes' if ok else 'NO'}"
    ]


def check_verification(b: RunB) -> Verdict:
    """Check 6: every structural case's verification within VERIFY_REL P_ref, or flagged;
    the note names each flagged case (PASS "as a bound": section 9's "the case is flagged
    and reported as a bound")."""
    lines: list[str] = []
    passed = True
    tol_kg = VERIFY_REL * P_REF_KG
    bounds: list[str] = []
    for c in b.structural_cases():
        ver = c.get("verification")
        flagged = verify_flagged(c)
        name, status = c["name"], c["status"]
        if flagged:
            bounds.append(name)
        if ver is None:
            ok = status == NO_OFFLOAD_STATUS
            passed &= ok
            lines.append(
                f"{name} ({status}): no verification"
                + (" (no offload to verify)" if ok else " MISSING")
            )
            continue
        d_kg = float(ver["delta_kg"])
        ok = abs(d_kg) <= tol_kg or flagged
        passed &= ok
        lines.append(
            f"{name} ({status}): verified P - P_ref {d_kg:+.6f} kg, |.| <= {tol_kg:.4f} kg: "
            f"{'yes' if abs(d_kg) <= tol_kg else 'NO'}"
            + (
                f"; flagged {VERIFY_MISMATCH_FLAG}: reported as a bound, marked "
                f"'{BOUND_MARK}' in every line that prints its x*"
                if flagged
                else ""
            )
            + f" (recorded passed {ver.get('passed')}, status {ver.get('status')})"
        )
    others = [c for c in b.offload["cases"] if not c.get("structure_charged")]
    worst_kg = max(
        (abs(float((c.get("verification") or {}).get("delta_kg", 0.0))) for c in others),
        default=0.0,
    )
    lines.append(
        f"beside (not this check: uncharged cases): {len(others)} verifications, the largest "
        f"|P - P_ref| {worst_kg:.4f} kg"
    )
    note = f"as a bound: {', '.join(bounds)}" if passed and bounds else ""
    return passed, lines, note


def check_dry_mass(b: RunB) -> tuple[bool, list[str]]:
    """Check 7: xv_dry_mass_delta_kg equal to dm1 + dm2 at x* within DM_TOL_KG, dm1 + dm2
    as run B records it (structure_dm_kg; run B records dm2 but no dm1 field). The element
    sums (stage1.* and stage2.*) are an independent cross-check, printed beside."""
    lines: list[str] = []
    passed = True
    worst_el_kg = 0.0
    for c in b.structural_cases():
        xv_kg = (c.get("decomposition") or {}).get("xv_dry_mass_delta_kg")
        dm_kg, dm2_kg = c.get("structure_dm_kg"), c.get("structure_dm_stage2_kg")
        if not (finite(xv_kg) and finite(dm_kg) and finite(dm2_kg)):
            passed = False
            lines.append(f"{c['name']}: xv {xv_kg}, dm {dm_kg}, dm2 {dm2_kg}: MISSING")
            continue
        diff_kg = float(xv_kg) - float(dm_kg)
        ok = abs(diff_kg) <= DM_TOL_KG
        passed &= ok
        elements = c.get("structure_elements") or {}
        el1_kg = sum(float(v) for k, v in elements.items() if k.startswith("stage1."))
        el2_kg = sum(float(v) for k, v in elements.items() if k.startswith("stage2."))
        worst_el_kg = max(
            worst_el_kg, abs(el1_kg + el2_kg - float(dm_kg)), abs(el2_kg - float(dm2_kg))
        )
        lines.append(
            f"{c['name']} ({c['status']}): xv_dry_mass_delta {float(xv_kg)!r} kg against "
            f"structure_dm_kg {float(dm_kg)!r} kg (dm1 + dm2 as recorded: dm2 "
            f"{float(dm2_kg):.6f} kg, so dm1 = dm - dm2 = {float(dm_kg) - float(dm2_kg):.6f} "
            f"kg); diff {diff_kg:+.1e} kg, |.| <= {DM_TOL_KG:g} kg: {'yes' if ok else 'NO'}"
        )
    lines.append(
        "beside (not a gate; the independent sum): the element sums stage1.* + stage2.* equal "
        f"dm, and stage2.* equals dm2, to {worst_el_kg:.1e} kg at most"
    )
    return passed, lines


def check_sha256(b: RunB) -> tuple[bool, list[str]]:
    """Check 8: the structure files' sha256 at run B's commit and every structure digest
    run B records equal section 12's."""
    lines: list[str] = []
    passed = True
    rev = str(b.git["hash"])
    for relpath, digest in STRUCTURE_SHA256.items():
        blob = git_blob(rev, relpath)
        got = None if blob is None else sha256(blob)
        ok = got == digest
        passed &= ok
        lines.append(
            f"{relpath}: registered {digest}; at run B's commit {rev}: {got}: "
            f"{'equal' if ok else 'DIFFERS'}"
        )
        disk = sha256((REPO / relpath).read_bytes())
        head = git_blob("HEAD", relpath)
        lines.append(
            f"  beside (not this check): working tree {'equal' if disk == digest else 'DIFFERS'}"
            f", HEAD {git_head()} "
            + ("equal" if head is not None and sha256(head) == digest else "DIFFERS")
        )
    found: Counter[str] = Counter()
    for where, key, value, parent in iter_items(b.metrics):
        if not (key.endswith("sha256") and isinstance(value, str)):
            continue
        fpath = parent.get("structure_file" if key == "structure_file_sha256" else "file")
        if not isinstance(fpath, str):
            passed = False
            lines.append(f"  digest with no file named beside it: metrics.json{where}")
        elif fpath.startswith(STRUCTURE_DIR):
            ok = STRUCTURE_SHA256.get(fpath) == value.lower()
            passed &= ok
            found[f"metrics.json: {fpath} {'equal' if ok else 'DIFFERS'}"] += 1
            if not ok:
                lines.append(f"  DIFFERS: metrics.json{where} = {value} ({fpath})")
        else:
            lines.append(f"  other digest record (not a structure file): metrics.json{where}")
    for line_no, fpath, value in yaml_sha_records(b.root / "resolved_config.yaml"):
        if fpath is None:
            passed = False
            lines.append(f"  digest with no file named beside it: resolved_config.yaml:{line_no}")
        elif fpath.startswith(STRUCTURE_DIR):
            ok = STRUCTURE_SHA256.get(fpath) == value
            passed &= ok
            found[f"resolved_config.yaml: {fpath} {'equal' if ok else 'DIFFERS'}"] += 1
            if not ok:
                lines.append(f"  DIFFERS: resolved_config.yaml:{line_no} = {value} ({fpath})")
    if not found:
        passed = False
    lines.append(
        "run B's recorded structure digests: "
        + ("; ".join(f"{n} x {w}" for w, n in sorted(found.items())) or "NONE")
    )
    return passed, lines


def _chain_pad_budget_as_registered(chain: Mapping[str, Any]) -> bool:
    """Whether a chain of the convergence report flew its own pad at the chain's budget:
    the pad's budget recorded and equal to the solve's (section 1: "each chain flies its
    own pad")."""
    return chain.get("pad_budget") is not None and chain.get("pad_budget") == chain.get("budget")


def _chain_push_as_registered(chain: Mapping[str, Any], tightened: bool) -> bool:
    """Whether a chain of the convergence report flew its solve's and its verification's
    pushes with its own context: each push context tightened exactly when the chain is,
    and each push context's budget equal to its search's."""
    return (
        chain.get("push_context_tightened") is tightened
        and chain.get("verify_push_context_tightened") is tightened
        and chain.get("push_budget") is not None
        and chain.get("push_budget") == chain.get("budget")
        and chain.get("verify_push_budget") is not None
        and chain.get("verify_push_budget") == chain.get("verify_budget")
    )


def _verification_recomputed(chain: Mapping[str, Any]) -> tuple[bool, str]:
    """A convergence chain's verification recomputed from its recorded status and P* and
    the chain's P_ref, by ``offload.verification_from_record``'s rule (ok with |P* - P_ref|
    <= CONV_VERIFY_REL P_ref): whether it passed, and its words for check 9's line (with
    whether the report's own P* - P_ref, tolerance and passed agree with these)."""
    status = chain.get("verification_status")
    p_ref_kg, p_kg = chain.get("p_ref_kg"), chain.get("verification_payload_kg")
    recorded = (
        f"the report's P - P_ref {chain.get('verification_delta_kg')!r} kg, tolerance "
        f"{chain.get('verification_tolerance_kg')!r} kg, passed {chain.get('verification_passed')}"
    )
    if not (finite(p_ref_kg) and finite(p_kg)):
        return False, f"status {status}, no P* to compare ({recorded})"
    delta_kg = float(p_kg) - float(p_ref_kg)
    tol_kg = CONV_VERIFY_REL * float(p_ref_kg)
    ok = status == OK_STATUS and abs(delta_kg) <= tol_kg
    same = (
        chain.get("verification_delta_kg") == delta_kg
        and chain.get("verification_tolerance_kg") == tol_kg
        and chain.get("verification_passed") is ok
    )
    return ok, (
        f"status {status}, P - P_ref {delta_kg:+.6f} kg, |.| <= {CONV_VERIFY_REL:g} of its "
        f"P_ref ({tol_kg:.4f} kg): {'yes' if ok else 'NO'} ({recorded}: "
        f"{'agree' if same else 'DIFFER'})"
    )


def _verification_miss(name: str, chain: Mapping[str, Any]) -> str:
    """Why a convergence chain's verification did not confirm its x* (check 9's note)."""
    status = chain.get("verification_status")
    p_ref_kg, p_kg = chain.get("p_ref_kg"), chain.get("verification_payload_kg")
    if status != OK_STATUS or not (finite(p_ref_kg) and finite(p_kg)):
        return f"the {name} chain's independent verification ended {status}"
    return (
        f"the {name} chain's independent verification missed P_ref by "
        f"{float(p_kg) - float(p_ref_kg):+.3f} kg (more than {CONV_VERIFY_REL:g} of its "
        f"P_ref, {CONV_VERIFY_REL * float(p_ref_kg):.3f} kg)"
    )


def _verified_as_solved(chain: Mapping[str, Any]) -> bool:
    """Whether a convergence chain's verification flew the x* and the dm its solve found
    (the report's recorded offload_kg and dm_kg of the solve and of the verification,
    compared here)."""
    pairs = (("offload_kg", "verification_offload_kg"), ("dm_kg", "verification_dm_kg"))
    return all(finite(chain.get(a)) and chain.get(a) == chain.get(v) for a, v in pairs)


def _recorded_heads(report: Mapping[str, Any]) -> set[str]:
    """Every HEAD the convergence parts recorded (the report's same_code.heads: each of
    CONVERGENCE_PARTS at both READINGS)."""
    heads = (report.get("same_code") or {}).get("heads") or {}
    return {
        h
        for part in CONVERGENCE_PARTS
        for when in READINGS
        if isinstance(h := (heads.get(part) or {}).get(when), str) and h
    }


def _same_code_recomputed(report: Mapping[str, Any], run_b_commit: str) -> tuple[bool, list[str]]:
    """Section 1's "from the same code as run B", recomputed here: ``git diff --quiet <run
    B's commit, from run B's own record> <head> -- CODE_PATHS`` run now for each HEAD the
    parts recorded (each of CONVERGENCE_PARTS at both READINGS, none missing), and each
    part's code paths clean in the working tree at both readings as the report records
    them (a reading of the working tree at the time, which this script cannot repeat).
    Whether it holds, and check 9's lines."""
    sc = report.get("same_code") or {}
    heads, clean = sc.get("heads") or {}, sc.get("code_paths_clean") or {}
    problems: list[str] = []
    all_clean = True
    for part in CONVERGENCE_PARTS:
        for when in READINGS:
            head = (heads.get(part) or {}).get(when)
            if not (isinstance(head, str) and head):
                problems.append(f"{part} {when}: no HEAD recorded")
            if (clean.get(part) or {}).get(when) is not True:
                all_clean = False
                problems.append(f"{part} {when}: code paths not recorded clean")
    quiet = {h: git_diff_quiet(run_b_commit, h) for h in sorted(_recorded_heads(report))}
    words = {True: "quiet", False: "DIFFERS", None: "git error"}
    problems += [
        f"git diff --quiet {run_b_commit[:12]} {h[:12]}: {words[q]}"
        for h, q in quiet.items()
        if q is not True
    ]
    lines = [
        "  same code as run B, recomputed here: git diff --quiet <run B's commit "
        f"{run_b_commit[:12]}> <head> -- {' '.join(CODE_PATHS)}, run now for each HEAD the "
        f"parts recorded: {'; '.join(f'{h[:12]} {words[q]}' for h, q in quiet.items()) or 'none'}"
        f"; the code paths clean at both readings in the {len(CONVERGENCE_PARTS)} parts (as "
        "the report records them): "
        + ("yes" if all_clean else "NO")
        + f" (the report's own same_code.passed {sc.get('passed')})",
        *(f"    FOUND: {p}" for p in problems),
    ]
    return not problems, lines


def _scripts_recomputed(report: Mapping[str, Any]) -> tuple[bool, list[str]]:
    """Section 1's "a committed script", recomputed here: in each convergence part (the six
    of CONVERGENCE_PARTS and the report), each of CONVERGENCE_SCRIPTS's sha256 when the
    part's process loaded it, when it wrote its record and its blob's at that part's HEAD
    all equal, one sha256 per script across the parts (those readings as the report
    records them), and ``git show`` of each script, run now at each HEAD the parts recorded
    (``_recorded_heads``), equal to that sha256. Whether it holds, and check 9's lines
    (beside, not part of it: whether HEAD now holds the same blob)."""
    per_part = (report.get("scripts") or {}).get("per_part") or {}
    keys = ("sha256_at_import", "sha256", "head_sha256")
    problems: list[str] = []
    seen: dict[str, set[Any]] = {p: set() for p in CONVERGENCE_SCRIPTS}
    for part in (*CONVERGENCE_PARTS, CONVERGENCE_REPORT_PART):
        rec = per_part.get(part)
        if not isinstance(rec, Mapping):
            problems.append(f"{part}: no script readings recorded")
            continue
        for path in CONVERGENCE_SCRIPTS:
            values = [(rec.get(path) or {}).get(k) for k in keys]
            seen[path].update(values)
            if None in values or len(set(values)) != 1:
                problems.append(
                    f"{part}: {path} at import {values[0]}, at record {values[1]}, its blob "
                    f"at the part's HEAD {values[2]}: not all equal"
                )
    for path, values in seen.items():
        if len(values) != 1 or None in values:
            problems.append(f"{path}: {len(values - {None})} sha256 across the parts")
    heads = sorted(_recorded_heads(report))
    if not heads:
        problems.append("no HEAD recorded to read the scripts' blobs at")
    for h in heads:
        for path in CONVERGENCE_SCRIPTS:
            blob = git_blob(h, path)
            got = None if blob is None else sha256(blob)
            if seen[path] != {got}:
                problems.append(f"{path} at {h[:12]} (git show, run now): {got or 'absent'}")
    at_head_now = []
    for path, values in seen.items():
        blob = git_blob("HEAD", path)
        now = "absent" if blob is None else ("equal" if {sha256(blob)} == values else "DIFFERS")
        at_head_now.append(f"{path} {now}")
    lines = [
        "  scripts as committed, recomputed here: in each of the "
        f"{len(CONVERGENCE_PARTS) + 1} parts, each script's sha256 at import, at record and "
        "its blob's at the part's HEAD equal, one sha256 per script across the parts (the "
        "parts' readings as the report records them), and git show of each script at each "
        f"recorded HEAD ({', '.join(h[:12] for h in heads) or 'none'}; run now) equal to it: "
        + "; ".join(
            f"{p} {next(iter(v)) if len(v) == 1 else sorted(map(str, v))}" for p, v in seen.items()
        )
        + f" (the report's own scripts.passed {(report.get('scripts') or {}).get('passed')})",
        *(f"    FOUND: {p}" for p in problems),
        f"    beside (not part of the check): at this script's HEAD {git_head()} now: "
        + "; ".join(at_head_now),
    ]
    return not problems, lines


def _not_tightened_lines(report: Mapping[str, Any]) -> list[str]:
    """Beside check 9 (never part of it): the report's not_tightened, what neither chain
    tightens (not exhaustive), so that the check does not bound x*'s dependence on it."""
    items = report.get("not_tightened")
    if not isinstance(items, list) or not items:
        return ["beside: not_tightened NOT RECORDED"]
    return [
        "beside: not tightened in either chain (the report's not_tightened: among what neither "
        "chain tightens, not exhaustive; the check does not bound x*'s dependence on them):",
        *(f"  - {x}" for x in items),
    ]


def check_convergence(report_path: Path | None, b: RunB) -> Verdict:
    """Check 9: the linear-motor convergence check of section 1, from the report of
    CONVERGENCE_SCRIPT; None (NOT EVALUATED) without a report of the registered check
    (file B as run B's commit holds it, case CONVERGENCE_CASE, not a dry run) against this
    run B. The report's three verdicts are recombined here from its items, run B's own
    record and git, and compared with the report's own:

    - the registered rule (section 1's pass rule): both solves ok, the tightened x* within
      CONV_REL_TOL of the shipped one, the shipped one within CONV_RUN_B_TOL_KG of run B's
      own record;
    - x* confirmed (section 1's independent payload search per chain): each chain's
      verification ok with |P* - P_ref| <= CONV_VERIFY_REL of its P_ref, recomputed from its
      status, P* and P_ref (``_verification_recomputed``); a miss is reported as x* not
      confirmed, an outcome of the check, never as a departure from its method;
    - run as registered (section 1's method): each verification flew its solve's x* and dm
      (the recorded values compared here); both pads' searches ended ok and each pad flown
      at its chain's budget (the budgets compared here); in each chain the solve's and the
      verification's pushes flown with that chain's context (the budget equalities compared
      here; the tightened flags as the report records them); the same code as run B
      (``_same_code_recomputed``: git diff --quiet run here from run B's commit to each
      recorded HEAD); the scripts as committed (``_scripts_recomputed``: the recorded
      sha256 readings compared here, and git show run here at each recorded HEAD).

    Taken as the report records them, since this script cannot repeat them: each part's
    own readings (its HEAD, its code paths' cleanliness, its scripts' sha256 on disk), the
    solves' and searches' statuses, x*, dm and P*, the budgets and the push contexts'
    tightened flags. PASS needs all three and the report's own verdicts agreeing with
    them; a FAIL's note says which failed. NOT EVALUATED notes say why: no report, not the
    registered check, no run B compared (the report part ran without --run-b) or another
    run B compared. Beside (never part of the check): the push at x*'s events and the
    report's not_tightened."""
    if report_path is None:
        return (
            None,
            [
                "no --convergence report given: the check runs after this script's first use, "
                f"alone, from the same code as run B ({CONVERGENCE_SCRIPT}, its parts, then "
                "--part report --run-b RUN_B_DIR); re-run this script with --convergence "
                "<out>/report.json"
            ],
            "no convergence report",
        )
    r = read_json(report_path.resolve())
    lines = [f"report {shown(report_path)}"]
    blob = git_blob(str(b.git["hash"]), FILE_B)
    file_b_sha = None if blob is None else sha256(blob)
    if (
        not r.get("registered")
        or r.get("dry_run")
        or r.get("case") != CONVERGENCE_CASE
        or r.get("experiment") != FILE_B
        or r.get("experiment_sha256") != file_b_sha
    ):
        lines.append(
            f"{r.get('experiment')} (sha256 {r.get('experiment_sha256')}), case {r.get('case')}, "
            f"registered {r.get('registered')}, dry run {r.get('dry_run')}: not the registered "
            f"check ({FILE_B} at run B's commit, sha256 {file_b_sha}, case {CONVERGENCE_CASE})"
        )
        return None, lines, "the report is not of the registered check"
    rb = (r.get("run_b") or {}).get("dir")
    if rb is None:
        lines.append(
            f"the report compares no run B (its run_b is {r.get('run_b')!r}): its report part "
            f"ran without --run-b; re-run that part with --run-b {rel(b.root)}"
        )
        return (
            None,
            lines,
            "the report compares no run B (its report part ran without --run-b)",
        )
    if (REPO / rb).resolve() != b.root.resolve():
        lines.append(f"the report compares run B {rb!r}, not {rel(b.root)}")
        return None, lines, "the report compares another run B"
    s, t = r["shipped"], r["tightened"]
    lines.append(
        f"case {r['case']} of {r['experiment']} (sha256 {r['experiment_sha256']}, equal to "
        f"{FILE_B} at run B's commit)"
    )
    both_ok = (
        s["status"] == t["status"] == OK_STATUS
        and finite(s["offload_kg"])
        and finite(t["offload_kg"])
    )
    v_b = case_value(b, CONVERGENCE_CASE)
    x_b_kg = v_b.x_kg
    rule_fails: list[str] = []
    if both_ok:
        x_s_kg, x_t_kg = float(s["offload_kg"]), float(t["offload_kg"])
        rel_d = (x_t_kg - x_s_kg) / x_s_kg
        d_b_kg = math.inf if x_b_kg is None else x_s_kg - x_b_kg
        ok_rel = abs(rel_d) < CONV_REL_TOL
        ok_b = abs(d_b_kg) <= CONV_RUN_B_TOL_KG
        lines += [
            f"shipped: P_ref {s['p_ref_kg']!r} kg, x* {x_s_kg!r} kg (status {s['status']}), dm "
            f"{s['dm_kg']!r} kg",
            f"tightened: P_ref {t['p_ref_kg']!r} kg, x* {x_t_kg!r} kg (status {t['status']}), "
            f"dm {t['dm_kg']!r} kg",
            f"tightened - shipped x* {x_t_kg - x_s_kg:+.6f} kg, relative {rel_d:+.3e}, |.| < "
            f"{CONV_REL_TOL:g}: {'yes' if ok_rel else 'NO'}",
            f"shipped - run B x* {d_b_kg:+.3e} kg (run B's record {x_b_kg!r} kg{v_b.mark}), "
            f"|.| <= {CONV_RUN_B_TOL_KG} kg: {'yes' if ok_b else 'NO'}",
        ]
        if not ok_rel:
            rule_fails.append(f"the tightened x* moved by {CONV_REL_TOL:.1%} or more")
        if not ok_b:
            rule_fails.append(f"the shipped x* is off run B's by more than {CONV_RUN_B_TOL_KG} kg")
    else:
        lines.append(
            f"shipped solve {s['status']} (x* {s['offload_kg']}), tightened solve {t['status']} "
            f"(x* {t['offload_kg']}): no x* to compare"
        )
        rule_fails.append("a solve did not end ok")
    rule = not rule_fails
    ver_s, ver_s_words = _verification_recomputed(s)
    ver_t, ver_t_words = _verification_recomputed(t)
    confirmed = ver_s and ver_t
    same_ok, same_lines = _same_code_recomputed(r, str(b.git["hash"]))
    scripts_ok, scripts_lines = _scripts_recomputed(r)
    how = {
        "verification_x_and_dm_as_solved": _verified_as_solved(s) and _verified_as_solved(t),
        "pad_searches_ok": (
            s.get("pad_search_status") == OK_STATUS and t.get("pad_search_status") == OK_STATUS
        ),
        "pad_budget_equals_solve": (
            _chain_pad_budget_as_registered(s) and _chain_pad_budget_as_registered(t)
        ),
        "push_contexts_as_registered": (
            _chain_push_as_registered(s, False) and _chain_push_as_registered(t, True)
        ),
        "same_code": same_ok,
        "scripts_as_committed": scripts_ok,
    }
    as_registered = all(how.values())
    mine = (rule, confirmed, as_registered, rule and confirmed and as_registered)
    theirs = (
        (r.get("registered_rule") or {}).get("passed"),
        (r.get("verifications") or {}).get("passed"),
        (r.get("run_as_registered") or {}).get("passed"),
        r.get("passed"),
    )
    agree = all(a is m for a, m in zip(theirs, mine, strict=True))
    lines += [
        f"the registered rule (section 1's pass rule: both solves ok, the tightened x* within "
        f"{CONV_REL_TOL:.1%} of the shipped one, the shipped one within {CONV_RUN_B_TOL_KG} kg "
        f"of run B's): {'PASS' if rule else 'FAIL'}",
        "x* confirmed (section 1: each chain's x* checked by an independent payload search at "
        "its own budget; recomputed from each chain's recorded status and P* against its "
        "P_ref): " + ("yes" if confirmed else "NO, x* not confirmed"),
        f"  shipped verification: {ver_s_words}",
        f"  tightened verification: {ver_t_words}",
        "run as registered (section 1's method): "
        + ("yes" if as_registered else "NO")
        + " ("
        + ", ".join(f"{k} {v}" for k, v in how.items())
        + ")",
        "  each verification flew its solve's x* and dm (the recorded values compared here): "
        f"shipped {_verified_as_solved(s)}, tightened {_verified_as_solved(t)} (the report's "
        f"own: shipped {s.get('verification_as_solved')}, tightened "
        f"{t.get('verification_as_solved')})",
        f"  pads: shipped search {s.get('pad_search_status')}, its budget equal to the solve's "
        f"{_chain_pad_budget_as_registered(s)}; tightened search {t.get('pad_search_status')}, "
        f"its budget equal to the solve's {_chain_pad_budget_as_registered(t)}",
        f"  push contexts tightened (solve, verification): shipped "
        f"{s.get('push_context_tightened')}, {s.get('verify_push_context_tightened')}; "
        f"tightened {t.get('push_context_tightened')}, {t.get('verify_push_context_tightened')}"
        f"; budgets equal to their searches' (solve, verification): shipped "
        f"{s.get('push_budget') == s.get('budget')}, "
        f"{s.get('verify_push_budget') == s.get('verify_budget')}; tightened "
        f"{t.get('push_budget') == t.get('budget')}, "
        f"{t.get('verify_push_budget') == t.get('verify_budget')} (the tightened flags as the "
        "report records them, computed there against a freshly tightened context; the budget "
        "equalities recomputed here)",
        *same_lines,
        *scripts_lines,
        f"the report's own verdicts: registered rule {theirs[0]}, x* confirmed {theirs[1]}, run "
        f"as registered {theirs[2]}, passed {theirs[3]}: "
        + ("agree" if agree else "DISAGREE WITH THE RECOMPUTED ONES"),
        f"beside: the push at x* logged {s.get('push_at_x_events')} (shipped) and "
        f"{t.get('push_at_x_events')} (tightened)",
        *_not_tightened_lines(r),
    ]
    if rule and confirmed and as_registered and agree:
        return True, lines, ""
    notes = (
        [f"the registered rule fails: {'; '.join(rule_fails)}"]
        if rule_fails
        else ["the registered rule itself passes"]
    )
    if not confirmed:
        notes.append(
            "x* not confirmed: "
            + "; ".join(
                _verification_miss(name, chain)
                for name, chain, ok in (("shipped", s, ver_s), ("tightened", t, ver_t))
                if not ok
            )
        )
    if not as_registered:
        notes.append(
            "not run as registered: " + ", ".join(k for k, v in how.items() if not v) + " false"
        )
    if not agree:
        notes.append("the report's own verdicts disagree with the recomputed ones")
    return False, lines, "; ".join(notes)


def check_flags(b: RunB) -> tuple[bool, list[str]]:
    """Check 10: no offload_nonmonotone, refine_capped or fired structure_fixed_point_cap."""
    lines: list[str] = []
    blocking: list[str] = []
    found: dict[str, set[str]] = defaultdict(set)
    cap_records = cap_fired = 0
    for who, jpath, items in iter_flag_lists(b.metrics, "."):
        for name, fired, item in flag_entries(items):
            if name == FIXED_POINT_CAP_FLAG and isinstance(item, Mapping):
                cap_records += 1
                cap_fired += fired
            if not fired:
                continue
            found[name].add(who)
            text = item if isinstance(item, str) else name
            if any(flag in text for flag in BLOCKING_FLAGS):
                blocking.append(f"{who}: {text[:TRUNCATE_CHARS]} (metrics.json{jpath})")
    summary = (b.root / "summary.md").read_text(encoding="utf-8")
    in_summary = {flag: summary.count(flag) for flag in BLOCKING_FLAGS}
    lines.append("fired flag names found in metrics.json, with their records:")
    for name in sorted(found):
        lines.append(f"  {name} ({len(found[name])}): {', '.join(sorted(found[name]))}")
    lines.append(
        f"{FIXED_POINT_CAP_FLAG} records (fired or not): {cap_records}, fired {cap_fired}; "
        "summary.md mentions: " + ", ".join(f"{k} x{n}" for k, n in in_summary.items())
    )
    lines.append(f"blocking flags ({', '.join(BLOCKING_FLAGS)}): {'none' if not blocking else ''}")
    lines += [f"  FOUND: {x}" for x in blocking]
    return not blocking, lines


def check_shortfalls(b: RunB) -> tuple[bool, list[str]]:
    """Check 11: every no_offload case carries its delta-v shortfall."""
    ended = [c for c in b.offload["cases"] if c["status"] == NO_OFFLOAD_STATUS]
    if not ended:
        return True, [
            f"no case ended {NO_OFFLOAD_STATUS} (of {len(b.offload['cases'])}); the stage-1 "
            "pad control is the solver's consistency test (check 3)"
        ]
    lines: list[str] = []
    passed = True
    for c in ended:
        short_mps = (c.get("solve") or {}).get("dv_shortfall_mps")
        ok = finite(short_mps)
        passed &= ok
        lines.append(
            f"{c['name']}: "
            + (
                f"solve.dv_shortfall_mps {short_mps!r} m/s; payload deficit not flown (no "
                "payload case)"
                if ok
                else "NO SHORTFALL"
            )
        )
    return passed, lines


SECTION_9 = "section 9's words"
"""The source of a check's scope when section 9 states it for that check."""
PART1_SECTION_9 = "part 1, section 9's words (the addendum's section 9 states none)"
"""The source of check 11's scope."""
READING = (
    "this script's reading of section 9's general rule ('a number is not cited until each "
    "check that touches it passes or is explained')"
)
"""The source of a check's scope when section 9 states none for that check."""
SECTION_9_AND_READING = (
    "section 9's words ('a bug'); 'the case' is this script's reading of its general rule"
)
"""The source of check 7's scope: section 9 calls it a bug and names no scope."""
CHECKS: tuple[tuple[int, str, str, str], ...] = (
    (1, "no run or comparison bug_suspect", "the number it touches", READING),
    (2, "the pad not reference_failed, its P* within 0.002 kg of P_ref", "every number", READING),
    (3, "the stage-1 pad control passes its consistency test", "every offload number", READING),
    (
        4,
        "the cross-commit check: silo_cold_s1 vs SP1's, silo_cold_s1_st vs run A's (0.002 kg)",
        "every number of run B until explained",
        SECTION_9,
    ),
    (
        5,
        "lm_cmd's uncharged x* within 0.25 kg of SP1's 41,262.908 kg",
        "every linear-motor number until explained",
        SECTION_9,
    ),
    (
        6,
        "structural verification within 1e-4 P_ref, or flagged offload_verify_mismatch",
        "the case is flagged and reported as a bound",
        SECTION_9,
    ),
    (
        7,
        "xv_dry_mass_delta_kg = dm1 + dm2 at x* within 1e-6 kg",
        "the case: a bug",
        SECTION_9_AND_READING,
    ),
    (
        8,
        "structure files' sha256 at run B's commit and as recorded equal section 12's",
        "every structural number",
        SECTION_9,
    ),
    (
        9,
        "the linear-motor convergence check of section 1 (0.1%)",
        "every linear-motor number until explained",
        SECTION_9,
    ),
    (
        10,
        "no unexplained offload_nonmonotone, capped gamma* refine or fired fixed-point cap",
        "the number: explained before it is quoted",
        SECTION_9,
    ),
    (
        11,
        "every no_offload case reported with its shortfall and 'payload deficit not flown'",
        "the case's report (a reporting defect to fix first)",
        PART1_SECTION_9,
    ),
)
"""Section 9's checks, one per bullet in its order: (number, title, what it blocks, where
that scope comes from)."""


def run_checks(b: RunB, convergence: Path | None) -> list[CheckResult]:
    """Every check of CHECKS on run B; an exception is a FAIL that names it (a script or
    data error to fix, never a pass)."""

    def plain(fn: Callable[[], tuple[bool, list[str]]]) -> Callable[[], Verdict]:
        """A check without a note, as a Verdict."""
        return lambda: (*fn(), "")

    fns: dict[int, Callable[[], Verdict]] = {
        1: plain(lambda: check_bug_suspect(b)),
        2: plain(lambda: check_pad(b)),
        3: plain(lambda: check_pad_control(b)),
        4: plain(lambda: check_cross_commit(b)),
        5: plain(lambda: check_lm_cmd(b)),
        6: lambda: check_verification(b),
        7: plain(lambda: check_dry_mass(b)),
        8: plain(lambda: check_sha256(b)),
        9: lambda: check_convergence(convergence, b),
        10: plain(lambda: check_flags(b)),
        11: plain(lambda: check_shortfalls(b)),
    }
    out = []
    for number, title, blocks, source in CHECKS:
        try:
            passed, lines, note = fns[number]()
        except Exception as exc:  # report and carry on with the other checks
            tail = traceback.format_exc().strip().splitlines()[-3:]
            passed, lines, note = False, [f"could not evaluate: {exc!r}", *tail], "an error"
        status = "NOT EVALUATED" if passed is None else ("PASS" if passed else "FAIL")
        out.append(CheckResult(number, title, status, lines, blocks, source, note))
    return out


# -------------------------------------------------------------------- expectations


def expectation_e1(b: RunB) -> Reading:
    """E1: lm_fixed_hot_s1_st raises structure_upper_stack_exceeded at its x*."""
    name = structural("lm_fixed_hot")
    c = b.case(name)
    rec = next((f for f in c.get("structure_flags") or [] if f.get("name") == UPPER_STACK_FLAG), {})
    met = bool(rec.get("fired")) and c["status"] in SOLVABLE
    vals = rec.get("values") or {}
    beside = [
        f"{case_value(b, name).label} ({c['status']}, x* {c['offload_kg']!r} kg): "
        f"{UPPER_STACK_FLAG} fired "
        f"{rec.get('fired')}: the push's upper-stack load {vals.get('push_n_upper_N')!r} N "
        f"against the envelope's {vals.get('envelope_n_upper_N')!r} N; dm2 "
        f"{c.get('structure_dm_stage2_kg')!r} kg"
    ]
    others = [
        x["name"]
        for x in b.structural_cases()
        if any(f.get("name") == UPPER_STACK_FLAG and f.get("fired") for f in x["structure_flags"])
    ]
    beside.append(f"beside: the flag fired on {', '.join(others) or 'no case'}")
    return Reading(
        "E1",
        name,
        "met" if met else "not met",
        f"E1 (design 4.10): lm_fixed_hot_s1_st raises the upper-stack flag at its x*: "
        f"{'met' if met else 'not met'}.",
        beside,
        {"met": met},
    )


def expectation_e2(b: RunB) -> Reading:
    """E2: no drive_cap event and no cap flag on the lm_cmd family's recorded runs."""
    beside: list[str] = []
    met = True
    for v in LM_CMD_FAMILY:
        for kind, name in (
            ("variant run", v),
            ("case run", uncharged(v)),
            ("case run", structural(v)),
        ):
            rec = b.variant_run(name) if kind == "variant run" else b.case_run(name)
            events = event_names(b.root / name)
            caps = [(t, e) for t, e, _ in events if e == DRIVE_CAP_EVENT]
            ends = [(t, e) for t, e, _ in events if e == DRIVE_CAP_END_EVENT]
            cap_flags = [f for f in rec.get("flags") or [] if DRIVE_CAP_EVENT in str(f)]
            bound = rec.get("push_cap_bound")
            ok = not caps and not cap_flags and bound is not True
            met &= ok
            beside.append(
                f"{name} ({kind}): drive_cap events {len(caps)}, drive_cap_end {len(ends)}, "
                f"push_cap_bound {bound}, cap flags {len(cap_flags)}; speed at release "
                f"{rec.get('speed_at_release_mps')!r} m/s"
            )
    return Reading(
        "E2",
        ", ".join(LM_CMD_FAMILY),
        "met" if met else "not met",
        "E2 (sources section 10; D-SP7-24): no drive_cap on the lm_cmd family (the variant "
        f"runs and the six cases' runs at their x*): {'met' if met else 'not met'}.",
        beside,
        {"met": met},
    )


# ----------------------------------------------------------------------- sentences


def reading_word(d_kg: float) -> str:
    """The rule that fired for a difference of two structural x* (R_X_KG)."""
    return "same" if within(d_kg, R_X_KG) else ("more" if d_kg > 0 else "less")


def sentence_rb(b: RunB, variant: str) -> Reading:
    """RB: a linear-motor central case against SP1's uncharged 41.26 t."""
    x = case_value(b, structural(variant))
    u = case_value(b, uncharged(variant))
    head = f"{x.name} ({ISOLATES[variant]})"
    if not x.evaluable:
        return Reading("RB", x.name, "fires nothing", f"{x.name} ended {x.status}: fires nothing")
    if x.status == NO_OFFLOAD_STATUS:
        rule, text = "cancels all", f"{head} cancels all of it: {x.no_offload_phrase(True)}."
    elif x.x_for_diff > HALF_KG:
        rule = "keeps more than half"
        text = (
            f"{head} keeps more than half of SP1's uncharged offload: {x.tonnes()} "
            f"({pct(x.x_for_diff)})."
        )
    else:
        rule = "cancels most"
        text = f"{head} cancels most of it: {x.tonnes()} is left ({pct(x.x_for_diff)})."
    own = (
        f"{pct_of(x.x_for_diff, u.x_for_diff)} of its own uncharged {t2(u.x_for_diff)} t"
        if u.evaluable and u.x_for_diff > 0.0
        else f"its own uncharged case {u.name} ended {u.status}"
    )
    beside = [
        f"beside: {own} ({u.label})",
        f"x* {x.x_for_diff!r} kg{x.mark} against the threshold {HALF_KG} kg: "
        f"{x.x_for_diff - HALF_KG:+.1f} kg",
        *bound_beside(x, u),
    ]
    return Reading("RB", x.name, rule, text, beside, {"x_kg": x.x_for_diff, "u_kg": u.x_for_diff})


def sentence_lm(b: RunB, variant: str) -> Reading:
    """LM: a linear-motor central x* against silo_cold_s1_st of file B."""
    x, u = case_value(b, structural(variant)), case_value(b, uncharged(variant))
    xc, uc = case_value(b, structural(COLD)), case_value(b, uncharged(COLD))
    reason = not_read(x, u, xc, uc)
    if reason:
        return Reading("LM", x.name, "fires nothing", reason)
    d_kg = x.x_for_diff - xc.x_for_diff
    cost_kg, cost_c_kg = cost(u, x), cost(uc, xc)
    text = (
        f"{x.name} ({ISOLATES[variant]}) leaves {x.phrase()} of stage-1 propellant against "
        f"silo_cold_s1_st's {xc.phrase()}: {more_less(d_kg)} (uncharged {u.phrase()} against "
        f"{uc.phrase()}; the structure's offload cost U - X {t2(cost_kg)} t against "
        f"{t2(cost_c_kg)} t)."
    )
    beside = [
        diff_beside("beside: X - X_c", d_kg, R_X_KG),
        diff_beside("U - U_c", u.x_for_diff - uc.x_for_diff, R_U_KG),
        diff_beside("cost - cost_c", cost_kg - cost_c_kg, R_COST_KG),
        *bound_beside(x, u, xc, uc),
    ]
    return Reading(
        "LM",
        x.name,
        reading_word(d_kg),
        text,
        beside,
        {"d_kg": d_kg, "cost_kg": cost_kg, "cost_c_kg": cost_c_kg},
    )


def sentence_hs(b: RunB, hot: str, cold: str) -> Reading:
    """HS: a hot start against the cold start of the same drive. The bare uncharged
    difference stays a number even within R_U_KG (HS's rule replaces only <more | less>;
    this script's reading, printed beside whenever it matters)."""
    xh, uh = case_value(b, structural(hot)), case_value(b, uncharged(hot))
    xk, uk = case_value(b, structural(cold)), case_value(b, uncharged(cold))
    reason = not_read(xh, uh, xk, uk)
    if reason:
        return Reading("HS", xh.name, "fires nothing", reason)
    d_kg = xh.x_for_diff - xk.x_for_diff
    du_kg = uh.x_for_diff - uk.x_for_diff
    cost_h_kg, cost_k_kg = cost(uh, xh), cost(uk, xk)
    word = (
        "the same within the resolution"
        if within(d_kg, R_X_KG)
        else ("more" if d_kg > 0 else "less")
    )
    text = (
        f"{xh.name} keeps {word} offload than {xk.name} with the same drive and the same "
        f"structure settings: {signed_t(d_kg)} t (uncharged {signed_t(du_kg)} t; the "
        f"structure's offload cost {t2(cost_h_kg)} t against {t2(cost_k_kg)} t) "
        f"{NOTHING_IN_SHAFT}."
    )
    beside = [
        diff_beside("beside: X_hot - X_cold", d_kg, R_X_KG),
        diff_beside("U_hot - U_cold", du_kg, R_U_KG),
        diff_beside("D_hot - D_cold", cost_h_kg - cost_k_kg, R_COST_KG),
        "the sentence's fixed words against the run (the drive from metrics.json's variant "
        "runs and from resolved_config.yaml's assist blocks, the structure settings from the "
        "case records): "
        + settings_line(
            f"{hot}'s drive settings against {cold}'s",
            b.variant_run(hot),
            b.variant_run(cold),
            DRIVE_KEYS,
            "'with the same drive'",
        )
        + "; "
        + assist_line(b, hot, cold, "'with the same drive'")
        + "; "
        + settings_line(
            f"{xh.name}'s structure settings against {xk.name}'s",
            b.case(xh.name),
            b.case(xk.name),
            STRUCTURE_SETTING_KEYS,
            "'the same structure settings'",
        ),
    ]
    if within(du_kg, R_U_KG) or near_r(du_kg, R_U_KG):
        beside.append(
            "this script's reading, for the orchestrator to confirm: the sentence prints the "
            f"uncharged difference as a number although it lies within or near R {R_U_KG:g} kg "
            "(section 8's general rule names that R; HS's own rule replaces only <more | less>)"
        )
    beside += bound_beside(xh, uh, xk, uk)
    rule = "same" if word.startswith("the same") else word
    return Reading("HS", xh.name, rule, text, beside, {"d_kg": d_kg, "du_kg": du_kg})


def sentence_ts(b: RunB) -> Reading:
    """TS: the target-speed release against release at L."""
    xt, ut = (
        case_value(b, structural("lm_fixed_target")),
        case_value(b, uncharged("lm_fixed_target")),
    )
    xl, ul = case_value(b, structural("lm_fixed")), case_value(b, uncharged("lm_fixed"))
    reason = not_read(xt, ut, xl, ul)
    if reason:
        return Reading("TS", xt.name, "fires nothing", reason)
    rt, rl = b.case_run(xt.name), b.case_run(xl.name)
    s_rel_m, v_l_mps = float(rt["release_position_m"]), float(rl["speed_at_release_mps"])
    d_kg = xt.x_for_diff - xl.x_for_diff
    text = (
        f"Released where its speed reaches v_e ({s_rel_m:.2f} m up the 100 m stroke at x*), "
        f"lm_fixed_target leaves {xt.phrase()} against lm_fixed's {xl.phrase()} released at the "
        f"track end at {mps(v_l_mps)} m/s: {more_less(d_kg)} (uncharged {ut.phrase()} against "
        f"{ul.phrase()})."
    )
    v_t_mps, v_e_mps = rt.get("speed_at_release_mps"), rt.get("push_release_speed_mps")
    at_v_e = finite(v_t_mps) and finite(v_e_mps) and abs(v_t_mps - v_e_mps) <= SPEED_TIE_MPS
    beside = [
        diff_beside("beside: X_T - X_L", d_kg, R_X_KG),
        diff_beside("U_T - U_L", ut.x_for_diff - ul.x_for_diff, R_U_KG),
        "the sentence's fixed words against the run: "
        + "; ".join(
            [
                fixed(
                    f"{xt.name} release_trigger",
                    rt.get("release_trigger"),
                    TRIGGER_TARGET,
                    rt.get("release_trigger") == TRIGGER_TARGET,
                    "'Released where its speed reaches v_e'",
                ),
                f"its speed at release {v_t_mps!r} m/s against v_e {v_e_mps!r} m/s "
                f"(push_release_speed_mps), within {SPEED_TIE_MPS:g} m/s: "
                + ("equal" if at_v_e else "DIFFERS"),
                fixed(
                    f"{xt.name} stroke_m",
                    rt.get("stroke_m"),
                    STROKE_M,
                    rt.get("stroke_m") == STROKE_M,
                    "'the 100 m stroke'",
                ),
                fixed(
                    f"{xl.name} release_trigger",
                    rl.get("release_trigger"),
                    TRIGGER_TRACK_END,
                    rl.get("release_trigger") == TRIGGER_TRACK_END,
                    "'released at the track end'",
                ),
                f"{xl.name} release_position_m {rl.get('release_position_m')!r} against its "
                f"stroke_m {rl.get('stroke_m')!r}: "
                + ("equal" if rl.get("release_position_m") == rl.get("stroke_m") else "DIFFERS"),
            ]
        ),
        *bound_beside(xt, ut, xl, ul),
    ]
    return Reading("TS", xt.name, reading_word(d_kg), text, beside, {"d_kg": d_kg})


def same_force_power(v: Mapping[str, Any], vf: Mapping[str, Any]) -> bool:
    """Whether two variant runs record the same F_max and P_max (CM's "at the same F_max
    and P_max")."""
    return (
        v["push_force_max_N"] == vf["push_force_max_N"]
        and v["push_power_max_W"] == vf["push_power_max_W"]
    )


def settings_line(
    label: str, mine: Mapping[str, Any], theirs: Mapping[str, Any], keys: Sequence[str], words: str
) -> str:
    """Two records' settings compared key by key (``keys``; a key either record lacks
    differs): "equal", or "DIFFERS:" with each differing key's two values; ``words`` the
    sentence's, quoted."""
    diffs = [
        f"{k} not recorded"
        if k not in mine or k not in theirs
        else f"{k} {mine[k]!r} against {theirs[k]!r}"
        for k in keys
        if k not in mine or k not in theirs or mine[k] != theirs[k]
    ]
    verdict = "equal" if not diffs else "DIFFERS: " + "; ".join(diffs)
    return f"{label} ({words}; {', '.join(keys)}): {verdict}"


def sentence_cm(b: RunB) -> Reading:
    """CM: the 22 t carriage at a fixed force."""
    x, u = case_value(b, structural("lm_fixed_sled22")), case_value(b, uncharged("lm_fixed_sled22"))
    xf, uf = case_value(b, structural("lm_fixed")), case_value(b, uncharged("lm_fixed"))
    reason = not_read(x, u, xf, uf)
    if reason:
        return Reading("CM", x.name, "fires nothing", reason)
    r, rf = b.case_run(x.name), b.case_run(xf.name)
    d_kg = x.x_for_diff - xf.x_for_diff
    text = (
        "With a 22 t carriage at the same F_max and P_max, lm_fixed_sled22 leaves "
        f"{x.phrase()} against lm_fixed's {xf.phrase()}: {more_less(d_kg)} (uncharged "
        f"{u.phrase()} against {uf.phrase()}; at x* an exit speed of "
        f"{mps(r['speed_at_release_mps'])} m/s against {mps(rf['speed_at_release_mps'])} m/s and "
        f"a peak interface force of {mn(r['peak_interface_force_N'])} MN against "
        f"{mn(rf['peak_interface_force_N'])} MN)."
    )
    v_s, v_f = b.variant_run("lm_fixed_sled22"), b.variant_run("lm_fixed")
    beside = [
        diff_beside("beside: X - X_F", d_kg, R_X_KG),
        diff_beside("U - U_F", u.x_for_diff - uf.x_for_diff, R_U_KG),
        "the sentence's fixed words against the run: "
        + fixed(
            "lm_fixed_sled22's carriage_mass_kg",
            v_s["carriage_mass_kg"],
            CARRIAGE_22T_KG,
            v_s["carriage_mass_kg"] == CARRIAGE_22T_KG,
            "'a 22 t carriage'",
        )
        + "; "
        + fixed(
            f"{x.name}'s carriage_mass_kg (the run at x*)",
            r.get("carriage_mass_kg"),
            CARRIAGE_22T_KG,
            r.get("carriage_mass_kg") == CARRIAGE_22T_KG,
            "'a 22 t carriage'",
        )
        + "; F_max and P_max equal to lm_fixed's ('at the same F_max and P_max'): "
        + ("equal" if same_force_power(v_s, v_f) else "DIFFERS"),
        f"speed_at_release_mps and peak_interface_force_N of the recorded runs at x*: "
        f"{r['speed_at_release_mps']!r} and {r['peak_interface_force_N']!r}; lm_fixed's "
        f"{rf['speed_at_release_mps']!r} and {rf['peak_interface_force_N']!r}",
        *bound_beside(x, u, xf, uf),
    ]
    return Reading("CM", x.name, reading_word(d_kg), text, beside, {"d_kg": d_kg})


def shaft_settings(b: RunB, variant: str) -> dict[str, str]:
    """A variant's shaft settings (SHAFT_KEYS) as run B's resolved_config.yaml records them
    under runs: the first occurrence of each key inside the variant's own block (from its
    two-space-indented name to the next line at that indent or less; text only, no YAML
    parser)."""
    lines = (b.root / "resolved_config.yaml").read_text(encoding="utf-8").splitlines()
    head = f"  {variant}:"
    start = next(i for i, t in enumerate(lines) if t.rstrip() == head)
    pattern = re.compile(rf"^\s*({'|'.join(SHAFT_KEYS)}):\s*(\S+)\s*$")
    out: dict[str, str] = {}
    for t in lines[start + 1 :]:
        if t.strip() and len(t) - len(t.lstrip()) <= len(head) - len(head.lstrip()):
            break
        m = pattern.match(t)
        if m and m[1] not in out:
            out[m[1]] = m[2]
        if len(out) == len(SHAFT_KEYS):
            break
    return out


def assist_settings(b: RunB, variant: str) -> dict[str, str]:
    """A variant's assist block as run B's resolved_config.yaml records it under runs: the
    ``assist:`` mapping inside the variant's own block (from its two-space-indented name to
    the next line at that indent or less), every scalar under it with its nested keys
    joined by dots (``track.angle_deg``), each value as its text (text only, no YAML
    parser; block style, as the file is written)."""
    lines = (b.root / "resolved_config.yaml").read_text(encoding="utf-8").splitlines()

    def depth(t: str) -> int:
        """A line's indent."""
        return len(t) - len(t.lstrip())

    head = f"  {variant}:"
    start = next(i for i, t in enumerate(lines) if t.rstrip() == head)
    block: list[str] = []
    for t in lines[start + 1 :]:
        if t.strip() and depth(t) <= depth(head):
            break
        block.append(t)
    at = next(i for i, t in enumerate(block) if t.strip() == "assist:")
    out: dict[str, str] = {}
    parents: list[tuple[int, str]] = []
    for t in block[at + 1 :]:
        if not t.strip():
            continue
        if depth(t) <= depth(block[at]):
            break
        key, _, value = t.strip().partition(":")
        while parents and parents[-1][0] >= depth(t):
            parents.pop()
        if value.strip():
            out[".".join([*(k for _, k in parents), key])] = value.strip()
        else:
            parents.append((depth(t), key))
    return out


def assist_line(b: RunB, mine: str, theirs: str, words: str, skip: Sequence[str] = ()) -> str:
    """Two variants' assist blocks (``assist_settings``) compared key by key over every key
    either records except ``skip`` (``settings_line``): the drive as file B sets it,
    drive_efficiency, exhaust_impingement_fraction, brake_decel_g and the track included,
    beside DRIVE_KEYS's comparison from metrics.json."""
    a, c = assist_settings(b, mine), assist_settings(b, theirs)
    keys = sorted((set(a) | set(c)) - set(skip))
    shown_skip = f" but {', '.join(skip)} (compared on their own)" if skip else ""
    return settings_line(
        f"{mine}'s assist block against {theirs}'s in resolved_config.yaml's runs, every key"
        f"{shown_skip}",
        a,
        c,
        keys,
        words,
    )


def sealed_word_equal(key: str, text: str | None) -> bool:
    """Whether a recorded shaft setting equals SEALED_SHAFT's word (numbers compared as
    floats)."""
    want = SEALED_SHAFT[key]
    if text is None:
        return False
    if isinstance(want, str):
        return text == want
    try:
        return float(text) == want
    except ValueError:
        return False


def sentence_ss(b: RunB) -> Reading:
    """SS: the sealed shaft against vented."""
    x, u = case_value(b, structural("lm_fixed_sealed")), case_value(b, uncharged("lm_fixed_sealed"))
    xf, uf = case_value(b, structural("lm_fixed")), case_value(b, uncharged("lm_fixed"))
    reason = not_read(x, u, xf, uf)
    if reason:
        return Reading("SS", x.name, "fires nothing", reason)
    r, rf = b.case_run(x.name), b.case_run(xf.name)
    d_kg = x.x_for_diff - xf.x_for_diff
    text = (
        "In the sealed shaft (bore 5.24 m, gap 5 m) the same drive leaves "
        f"{x.phrase()} against the vented lm_fixed's {xf.phrase()}: {more_less(d_kg)} (uncharged "
        f"{u.phrase()} against {uf.phrase()}; at x* the column's peak force "
        f"{mn(r['piston_force_peak_N'])} MN and its work {mj(r['piston_work_J'])} MJ, and "
        f"an exit speed of {mps(r['speed_at_release_mps'])} m/s against "
        f"{mps(rf['speed_at_release_mps'])} m/s)."
    )
    sealed, vented = shaft_settings(b, "lm_fixed_sealed"), shaft_settings(b, "lm_fixed")
    v_s, v_f = b.variant_run("lm_fixed_sealed"), b.variant_run("lm_fixed")
    words = [
        fixed(
            f"lm_fixed_sealed {k}",
            sealed.get(k),
            want,
            sealed_word_equal(k, sealed.get(k)),
            SEALED_WORDS[k],
        )
        for k, want in SEALED_SHAFT.items()
    ]
    words.append(
        fixed(
            "lm_fixed shaft",
            vented.get("shaft"),
            VENTED_SHAFT,
            vented.get("shaft") == VENTED_SHAFT,
            "'the vented lm_fixed'",
        )
    )
    words.append(
        settings_line(
            "lm_fixed_sealed's drive settings against lm_fixed's",
            v_s,
            v_f,
            DRIVE_KEYS,
            "'the same drive'",
        )
    )
    words.append(assist_line(b, "lm_fixed_sealed", "lm_fixed", "'the same drive'", SHAFT_KEYS))
    beside = [
        diff_beside("beside: X - X_F", d_kg, R_X_KG),
        diff_beside("U - U_F", u.x_for_diff - uf.x_for_diff, R_U_KG),
        "the sentence's fixed words against the run (the shaft from resolved_config.yaml's "
        "runs, the drive from metrics.json's variant runs and from resolved_config.yaml's "
        "assist blocks): " + "; ".join(words),
        f"piston_force_peak_N {r['piston_force_peak_N']!r}, piston_work_J {r['piston_work_J']!r} "
        "(the recorded run at x*)",
        *bound_beside(x, u, xf, uf),
    ]
    return Reading("SS", x.name, reading_word(d_kg), text, beside, {"d_kg": d_kg})


def _flag(case: Mapping[str, Any], name: str) -> dict[str, Any]:
    """A case's structure flag record by name ({} if absent)."""
    return next((f for f in case.get("structure_flags") or [] if f.get("name") == name), {})


def fires(rec: Mapping[str, Any]) -> str:
    """<fires | does not fire> for a structure flag record."""
    return "fires" if rec.get("fired") else "does not fire"


def sentence_tp(b: RunB) -> Reading:
    """TP: the stop taper against lm_cmd."""
    x = case_value(b, structural("lm_cmd_taper"))
    xc = case_value(b, structural("lm_cmd"))
    reason = not_read(x, xc)
    if reason:
        return Reading("TP", x.name, "fires nothing", reason)
    d_kg = x.x_for_diff - xc.x_for_diff
    rel_t, rel_c = _flag(b.case(x.name), RELEASE_FLAG), _flag(b.case(xc.name), RELEASE_FLAG)
    pl_t, pl_c = (
        _flag(b.case(x.name), PAYLOAD_LIMIT_FLAG),
        _flag(b.case(xc.name), PAYLOAD_LIMIT_FLAG),
    )
    vals_t, vals_c = rel_t.get("values") or {}, rel_c.get("values") or {}
    text = (
        f"The stop taper leaves {x.phrase()} against lm_cmd's {xc.phrase()}: {more_less(d_kg)}; "
        f"at x* its release flag {fires(rel_t)} (the stage-1 LOX bottom at "
        f"{kpa(vals_t['lox_bottom_pressure_min_abs_pa'])} kPa absolute against lm_cmd's "
        f"{kpa(vals_c['lox_bottom_pressure_min_abs_pa'])} kPa; the release swing "
        f"{g0s(vals_t['release_swing_g'])} g0 against {g0s(vals_c['release_swing_g'])} g0) and "
        f"its payload-limit flag {fires(pl_t)}."
    )
    pv_t, pv_c = pl_t.get("values") or {}, pl_c.get("values") or {}
    beside = [
        diff_beside("beside: X - X_c", d_kg, R_X_KG),
        f"lm_cmd's release flag {fires(rel_c)} and payload-limit flag {fires(pl_c)}; the "
        f"payload-limit flag's numbers: taper n_peak {pv_t.get('n_peak_g')!r} g0 and swing "
        f"{pv_t.get('release_swing_g')!r} g0 against the limits {pv_t.get('limit_axial_max_g')} "
        f"and {pv_t.get('limit_axial_min_g')} g0; lm_cmd n_peak {pv_c.get('n_peak_g')!r} g0, "
        f"swing {pv_c.get('release_swing_g')!r} g0; MECO's swing {vals_t.get('meco_swing_g')!r} g0",
        *bound_beside(x, xc),
    ]
    return Reading("TP", x.name, reading_word(d_kg), text, beside, {"d_kg": d_kg})


def sentence_pl(b: RunB) -> Reading:
    """PL: the power-limited drive against lm_fixed."""
    x, xf = case_value(b, structural("lm_fixed_r07")), case_value(b, structural("lm_fixed"))
    reason = not_read(x, xf)
    if reason:
        return Reading("PL", x.name, "fires nothing", reason)
    v, vf = b.variant_run("lm_fixed_r07"), b.variant_run("lm_fixed")
    d_kg = x.x_for_diff - xf.x_for_diff
    text = (
        f"The power-limited drive (r = 0.7, F_max {mn(v['push_force_max_N'])} MN) leaves "
        f"{x.phrase()} against lm_fixed's {xf.phrase()} (F_max {mn(vf['push_force_max_N'])} MN): "
        f"{more_less(d_kg)}."
    )
    r_ratio = v["push_power_max_W"] / (v["push_force_max_N"] * vf["push_corner_speed_mps"])
    beside = [
        diff_beside("beside: X - X_F", d_kg, R_X_KG),
        "the sentence's fixed words against the run: "
        + fixed(
            "r = P_max / (F_max v_e)",
            r_ratio,
            PL_R,
            abs(r_ratio / PL_R - 1.0) <= PL_R_REL_TOL,
            "'r = 0.7'",
        )
        + f" (relative tolerance {PL_R_REL_TOL:g}; v_e = lm_fixed's corner speed "
        f"{vf['push_corner_speed_mps']!r} m/s)",
        *bound_beside(x, xf),
    ]
    return Reading("PL", x.name, reading_word(d_kg), text, beside, {"d_kg": d_kg})


def guarded(name: str, fn: Callable[[], Reading]) -> Reading:
    """A reading, or one that says why it could not be computed (never silently dropped)."""
    try:
        return fn()
    except Exception as exc:  # report and carry on
        return Reading(name, "?", "could not evaluate", f"{name}: could not evaluate: {exc!r}")


def sentences(b: RunB) -> list[Reading]:
    """Every fixed sentence of section 8 in its order: RB and LM per variant, HS twice,
    then TS, CM, SS, TP and PL; each guarded (one that cannot be computed says so)."""
    calls: list[tuple[str, Callable[[], Reading]]] = []
    for v in LM_VARIANTS:
        calls.append(("RB", lambda v=v: sentence_rb(b, v)))
    for v in LM_VARIANTS:
        calls.append(("LM", lambda v=v: sentence_lm(b, v)))
    calls += [
        ("HS", lambda: sentence_hs(b, "lm_cmd_hot", "lm_cmd")),
        ("HS", lambda: sentence_hs(b, "lm_fixed_hot", "lm_fixed")),
        ("TS", lambda: sentence_ts(b)),
        ("CM", lambda: sentence_cm(b)),
        ("SS", lambda: sentence_ss(b)),
        ("TP", lambda: sentence_tp(b)),
        ("PL", lambda: sentence_pl(b)),
    ]
    return [guarded(name, fn) for name, fn in calls]


# --------------------------------------------------------------------- beside blocks


def beside_read(b: RunB) -> list[str]:
    """Section 8's items read beside the expectations: lm_cmd_s1_st against
    silo_cold_s1_st, and lm_cmd_hot's pair against run A's silo_hot_ramp_on_track pair,
    each difference with R beside it."""
    out = []
    x, xc = case_value(b, structural("lm_cmd")), case_value(b, structural(COLD))
    if x.evaluable and xc.evaluable:
        out.append(
            diff_beside(
                f"{x.label} {x.x_for_diff!r} kg - {xc.label} {xc.x_for_diff!r} kg =",
                x.x_for_diff - xc.x_for_diff,
                R_X_KG,
            )
        )
    for mine, theirs, r_kg in (
        (uncharged("lm_cmd_hot"), "silo_hot_ramp_s1", R_U_KG),
        (structural("lm_cmd_hot"), "silo_hot_ramp_s1_st", R_X_KG),
    ):
        v = case_value(b, mine)
        rec_kg, _ = _record_x(RUN_A, theirs)
        if v.evaluable:
            out.append(
                diff_beside(
                    f"{v.label} {v.x_for_diff!r} kg - run A's {theirs} {rec_kg!r} kg (section 8: "
                    f"{RUN_A_HOT_RAMP_KG[theirs]:,} kg) =",
                    v.x_for_diff - rec_kg,
                    r_kg,
                )
            )
    return out


def release_speed_scope(jpath: str, who: str) -> tuple[str, bool]:
    """Where a flags list sits in metrics.json, and whether section 9 lists
    release_speed_not_reached there as not blocking ("on an unrecorded evaluation or on
    lm_fixed_target's variant run")."""
    if re.fullmatch(r"\.runs\.[^.]+\.flags", jpath):
        return "variant run", who == "lm_fixed_target"
    if re.match(r"\.runs\.[^.]+\.search_record\.", jpath):
        return "its variant run's payload search: unrecorded evaluations", True
    if re.match(r"\.offload\.(cases|pad_controls)\[\d+\]\.solve\.flags$", jpath):
        return "its offload solve: unrecorded evaluations", True
    if re.fullmatch(r"\.offload\.runs\.[^.]+\.flags", jpath):
        return "case run at x*", False
    if re.fullmatch(r"\.offload\.cases\[\d+\]\.flags", jpath):
        return "case record, its verification included", False
    return f"other record metrics.json{jpath}", False


def beside_flags(b: RunB) -> list[str]:
    """Section 9's not-blocking items, reported beside: the release, upper-stack and
    payload-limit flags per structural case (the payload-limit flag's numbers against both
    limits, with its MECO comparison), and every release_speed_not_reached in metrics.json
    with where section 9 lists it as not blocking and where it departs from section 7."""
    out = []
    nan = float("nan")
    for c in b.structural_cases():
        fired = [
            n
            for n in (RELEASE_FLAG, UPPER_STACK_FLAG, PAYLOAD_LIMIT_FLAG)
            if _flag(c, n).get("fired")
        ]
        rv = _flag(c, RELEASE_FLAG).get("values") or {}
        pv = _flag(c, PAYLOAD_LIMIT_FLAG).get("values") or {}
        out.append(
            f"{c['name']}: fired {', '.join(fired) or 'none'}; release swing "
            f"{rv.get('release_swing_g', nan):.3f} g0 against {pv.get('limit_axial_min_g')} g0 "
            f"(MECO's {rv.get('meco_swing_g', nan):.3f}), n_peak {pv.get('n_peak_g', nan):.3f} g0 "
            f"against {pv.get('limit_axial_max_g')} g0, stage-1 LOX bottom "
            f"{kpa(rv.get('lox_bottom_pressure_min_abs_pa', nan))} kPa absolute"
        )
    expected = ("lm_fixed_target", "variant run")
    hits: list[tuple[str, str, bool]] = []
    for who, jpath, items in iter_flag_lists(b.metrics, "."):
        if any(RELEASE_SPEED_FLAG in str(f) for f in items):
            scope, not_blocking = release_speed_scope(jpath, who)
            hits.append((who, scope, not_blocking))
    found = ", ".join(f"{who} ({scope})" for who, scope, _ in hits) or "none"
    out.append(
        f"{RELEASE_SPEED_FLAG} in metrics.json: {found}. Section 9: not blocking on an "
        "unrecorded evaluation or on lm_fixed_target's variant run; section 7 expects it on "
        "lm_fixed_target's variant run and on none of its two cases' recorded runs at x* or "
        "their verifications"
    )
    for who, scope, not_blocking in hits:
        if not not_blocking:
            out.append(
                f"  {who} ({scope}): DEPARTS from section 7's expectation (section 9 does not "
                "list it as not blocking: to explain in the note)"
            )
    if not any((who, scope) == expected for who, scope, _ in hits):
        out.append(
            "  not on lm_fixed_target's variant run: departs from section 7's expectation "
            "(not blocking)"
        )
    return out


def beside_undercut(b: RunB) -> list[str]:
    """Section 8's "what would undercut the hypothesis" and "what would favour it",
    evaluated from the numbers (release speeds at x* from the recorded case runs; two
    speeds within SPEED_TIE_MPS read as equal; differences of x* against R_X_KG)."""
    xc = case_value(b, structural(COLD))
    v_c_mps = float(b.case_run(xc.name)["speed_at_release_mps"])
    out = [f"{xc.label}: X {xc.x_for_diff!r} kg, speed at release at x* {v_c_mps!r} m/s"]
    faster_less, slower_more, favour = [], [], []
    for v in LM_VARIANTS:
        x = case_value(b, structural(v))
        if not x.evaluable:
            out.append(f"{x.name}: ended {x.status}: not read")
            continue
        speed_mps = float(b.case_run(x.name)["speed_at_release_mps"])
        d_kg = x.x_for_diff - xc.x_for_diff
        faster = speed_mps > v_c_mps + SPEED_TIE_MPS
        slower = speed_mps < v_c_mps - SPEED_TIE_MPS
        item = f"{x.label} ({speed_mps - v_c_mps:+.3f} m/s, {d_kg:+.1f} kg)"
        if faster and d_kg < -R_X_KG:
            faster_less.append(item)
        if slower and d_kg > R_X_KG:
            slower_more.append(item)
        if faster and d_kg > R_X_KG:
            favour.append(item)
    out.append(
        "undercut (a drive that gains exit speed over silo_cold and still leaves less offload "
        f"once charged): {', '.join(faster_less) or 'none'}"
    )
    xt, xm = case_value(b, structural("lm_cmd_taper")), case_value(b, structural("lm_cmd"))
    if xt.evaluable and xm.evaluable:
        d_kg = xt.x_for_diff - xm.x_for_diff
        v_t_mps = float(b.case_run(xt.name)["speed_at_release_mps"])
        v_m_mps = float(b.case_run(xm.name)["speed_at_release_mps"])
        out.append(
            "undercut (a gentler release whose cost the model measures and whose benefit it "
            f"reports only as flags): {xt.label} - {xm.label} {d_kg:+.1f} kg at release "
            f"speeds {v_t_mps!r} and {v_m_mps!r} m/s: {'yes' if d_kg < -R_X_KG else 'no'}"
        )
    out.append(
        "undercut (a drive that exits slower and still leaves more offload once charged): "
        f"{', '.join(slower_more) or 'none'}"
    )
    xs, xf = case_value(b, structural("lm_fixed_sled22")), case_value(b, structural("lm_fixed"))
    if xs.evaluable and xf.evaluable:
        v_s_mps = float(b.case_run(xs.name)["speed_at_release_mps"])
        v_f_mps = float(b.case_run(xf.name)["speed_at_release_mps"])
        out.append(
            f"  beside it: {xs.label} against {xf.label} {v_s_mps - v_f_mps:+.3f} m/s, "
            f"{xs.x_for_diff - xf.x_for_diff:+.1f} kg"
        )
    n_pl = [v for v in LM_VARIANTS if _flag(b.case(structural(v)), PAYLOAD_LIMIT_FLAG).get("fired")]
    out.append(
        f"undercut (the payload-limit flag on the linear-motor central cases): {len(n_pl)} of "
        f"{len(LM_VARIANTS)} ({', '.join(n_pl) or 'none'}), beside part 1's MECO caveat"
    )
    above = [
        case_value(b, structural(v)).label
        for v in LM_VARIANTS
        if case_value(b, structural(v)).evaluable
        and case_value(b, structural(v)).x_for_diff > HALF_KG
    ]
    out.append(
        f"every linear-motor row below half of SP1's 41.26 t: {'yes' if not above else 'no'}"
        + (f" (above: {', '.join(above)})" if above else "")
    )
    xl = case_value(b, structural("lm_fixed"))
    if xl.evaluable:
        v_l_mps = float(b.case_run(xl.name)["speed_at_release_mps"])
        d_kg = xl.x_for_diff - xc.x_for_diff
        bounds = [v.label for v in (xl, xc) if v.flagged]
        out.append(
            "favour (lm_fixed's faster exit paying for its structure beyond R against "
            f"silo_cold_s1_st): {v_l_mps - v_c_mps:+.3f} m/s, {d_kg:+.1f} kg: "
            f"{'yes' if v_l_mps > v_c_mps + SPEED_TIE_MPS and d_kg > R_X_KG else 'no'}"
            + (f"; {', '.join(bounds)}" if bounds else "")
        )
    out.append(
        f"favour (any linear-motor row above half): {'yes: ' + ', '.join(above) if above else 'no'}"
    )
    out.append(f"  (any faster-and-more row beyond R: {', '.join(favour) or 'none'})")
    return out


def guarded_lines(name: str, fn: Callable[[], list[str]]) -> list[str]:
    """A beside block, or one line saying why it could not be computed."""
    try:
        return fn()
    except Exception as exc:  # report and carry on
        return [f"{name}: could not evaluate: {exc!r}"]


# ------------------------------------------------------------------------ the report


def script_provenance() -> str:
    """Which version of this script wrote the report (provenance, not a check): its file's
    sha256 when the report is written, whether HEAD holds the same blob, and whether the
    file is clean in the working tree (``git status --porcelain``)."""
    mine = sha256(Path(__file__).resolve().read_bytes())
    blob = git_blob("HEAD", SCRIPT)
    if blob is None:
        at_head = "not in HEAD"
    else:
        at_head = "equal" if sha256(blob) == mine else f"DIFFERS ({sha256(blob)})"
    status = git_porcelain(SCRIPT)
    tree = "clean" if not status else f"not clean ({status.split()[0]})"
    return (
        f"  beside (provenance, not a check): this script's sha256 {mine}; its blob at HEAD "
        f"{git_head()}: {at_head}; in the working tree: {tree}"
    )


def provenance(b: RunB, convergence: Path | None) -> list[str]:
    """The header: the script (and which version of it), HEAD, run B's records and
    fingerprints, and the inputs."""
    lines = [
        f"{SCRIPT}: SP7 step S7b, the pre-registration part 2's section 9 checks, section 8's "
        "expectations and fixed sentences (read-only; checks, never findings)",
        f"HEAD {git_head()}",
        script_provenance(),
        f"run B {rel(b.root)} (git {b.git['hash']}, dirty {b.git['dirty']}, "
        f"experiment {b.metrics['experiment']}, timestamp {b.metrics['timestamp_utc']})",
    ]
    m_sha = sha256((b.root / "metrics.json").read_bytes())
    t_sha = tree_sha256(b.root)
    n_files = sum(1 for p in b.root.rglob("*") if p.is_file())
    registered = b.root.resolve() == RUN_B.resolve()
    lines.append(
        f"  beside (provenance, not a check): metrics.json sha256 {m_sha}; tree sha256 {t_sha} "
        f"({n_files} files)"
        + (
            f"; both equal to the record at the run's end: "
            f"{m_sha == RUN_B_METRICS_SHA256 and t_sha == RUN_B_TREE_SHA256}"
            if registered
            else "; not the registered run B directory"
        )
    )
    blob = git_blob(str(b.git["hash"]), VEHICLE_FILE)
    v_sha = None if blob is None else sha256(blob)
    lines.append(
        f"  beside (provenance, not a check): {VEHICLE_FILE} at run B's commit {v_sha}: "
        f"{'equal' if v_sha == VEHICLE_SHA256 else 'DIFFERS'} to section 12's"
    )
    lines.append(f"  run A {rel(RUN_A)}; SP1 {rel(SP1_RUN)} (the cross-commit check, read only)")
    lines.append(f"  convergence report: {shown(convergence) if convergence else 'none given'}")
    return lines


def render(
    head: list[str],
    checks: list[CheckResult],
    expectations: list[Reading],
    readings: list[Reading],
    beside: dict[str, list[str]],
) -> tuple[list[str], int]:
    """The text report's lines and the exit code."""
    out = [*head, "", "A. Checks that block a citation (section 9, in its order)"]
    for c in checks:
        out += ["", f"[{c.number}] {c.title}", *(f"    {x}" for x in c.lines)]
        status = f"{c.status} ({c.note})" if c.note else c.status
        out.append(f"    -> {status} (blocks: {c.blocks}; {c.source})")
    out += ["", "B. Registered expectations (section 8; met or not met, never a check)"]
    for e in expectations:
        out += ["", f"{e.text}", *(f"    {x}" for x in e.beside)]
    out += [
        "",
        "C. Fixed sentences of section 8 that fire (word for word; beside: context only, never "
        "a reading)",
    ]
    for r in readings:
        out += ["", f"{r.rid} [{r.rule}] {r.text}", *(f"    {x}" for x in r.beside)]
    for title, lines in beside.items():
        out += ["", title, *(f"    {x}" for x in lines)]
    failed = [c.number for c in checks if c.status == "FAIL"]
    pending = [c.number for c in checks if c.status == "NOT EVALUATED"]
    n_pass = sum(c.status == "PASS" for c in checks)
    noted = "; ".join(f"check {c.number} {c.note}" for c in checks if c.status == "PASS" and c.note)
    out.append("")
    if failed:
        out.append(
            f"SUMMARY: FAIL: check(s) {', '.join(map(str, failed))} failed ({n_pass} of "
            f"{len(checks)} PASS"
            + (f", {noted}" if noted else "")
            + (f"; not evaluated: {', '.join(map(str, pending))}" if pending else "")
            + ")"
        )
        return out, 1
    if pending:
        out.append(
            f"SUMMARY: INCOMPLETE: {n_pass} of {len(checks)} PASS"
            + (f" ({noted})" if noted else "")
            + f", none failed; not evaluated: check(s) {', '.join(map(str, pending))}"
        )
        return out, 2
    out.append(f"SUMMARY: PASS: all {len(checks)} checks pass" + (f" ({noted})" if noted else ""))
    return out, 0


def _plain(value: Any) -> Any:
    """value with every non-finite float replaced by None (strict JSON)."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(v) for v in value]
    return value


def check_output_path(path: Path) -> Path:
    """The resolved output path; refused inside results/ (nothing here writes there)."""
    resolved = path.resolve()
    if resolved == RESULTS.resolve() or RESULTS.resolve() in resolved.parents:
        raise SystemExit(f"error: {resolved} lies inside results/: refused")
    return resolved


def main(argv: list[str] | None = None) -> int:
    """Parse the arguments, evaluate, print and write the report; the exit code."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--run-b", type=Path, default=RUN_B, help="run B's results directory")
    parser.add_argument("--convergence", type=Path, default=None, help="the convergence report")
    parser.add_argument("--out-text", type=Path, required=True, help="the text report's path")
    parser.add_argument("--out-json", type=Path, required=True, help="the JSON report's path")
    args = parser.parse_args(argv)
    out_text, out_json = check_output_path(args.out_text), check_output_path(args.out_json)
    if out_text == out_json:
        raise SystemExit("error: --out-text and --out-json name the same file")
    b = RunB(args.run_b.resolve())
    conv = None if args.convergence is None else args.convergence.resolve()
    head = provenance(b, conv)
    checks = run_checks(b, conv)
    expectations = [
        guarded("E1", lambda: expectation_e1(b)),
        guarded("E2", lambda: expectation_e2(b)),
    ]
    readings = sentences(b)
    beside = {
        "D. Read beside (section 8; not expectations of their own)": guarded_lines(
            "read beside", lambda: beside_read(b)
        ),
        "E. Not blocking (section 9), reported beside": guarded_lines(
            "flags", lambda: beside_flags(b)
        ),
        "F. Section 8's 'what would undercut' and 'what would favour', from the numbers "
        "(beside; not fixed sentences)": guarded_lines("undercut", lambda: beside_undercut(b)),
    }
    lines, code = render(head, checks, expectations, readings, beside)
    text = "\n".join(lines) + "\n"
    print(text, end="")
    out_text.parent.mkdir(parents=True, exist_ok=True)
    out_text.write_text(text, encoding="utf-8", newline="\n")
    data = {
        "script": SCRIPT,
        "provenance": head,
        "run_b": {"dir": rel(b.root), "git": b.git},
        "checks": [c.__dict__ for c in checks],
        "expectations": [e.__dict__ for e in expectations],
        "sentences": [r.__dict__ for r in readings],
        "beside": beside,
        "summary": lines[-1],
        "exit_code": code,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(_plain(data), indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n"
    )
    return code


if __name__ == "__main__":
    sys.exit(main())
