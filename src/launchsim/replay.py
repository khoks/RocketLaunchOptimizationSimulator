"""Interactive replay page of planar_2d runs (the ``launchsim replay`` command; I/O: reads
one results directory, writes one HTML file).

``write_replay_page`` reads a results directory (results/<experiment>/<timestamp>:
metrics.json, resolved_config.yaml, <run>/timeseries.csv, <run>/events.csv), never
writes inside results/, and writes a single self-contained HTML page: the trajectory
(altitude against downrange), a launch close-up with the silo shaft or track start
below ground, live telemetry, strip charts of speed, felt g and dynamic pressure, the
headline metrics against the baseline, and the caveats that apply to the selected
runs. The page replays the recorded time series; nothing is re-simulated in it.

``replay_data`` builds the embedded data set: per run the series resampled on a common
clock (the time after release: REPLAY_EARLY_DT_S steps up to REPLAY_EARLY_END_S, then
REPLAY_LATE_DT_S), q and Mach as JSON null where they are undefined (inside a vented
shaft, where no air drag is modelled), the events of events.csv and the headline
metrics of metrics.json, plus the text of the page (subtitle, run labels, notes,
caveats) generated from the run data. Run selection and the output-path rule are the
shared ones of run_data, which ``launchsim animate`` uses too (run_data.run_names: the
baseline plus up to three variants in summary order; at most run_data.MAX_RUNS runs; the
default output goes to the current directory, never into a results tree).

The reading itself lives in run_data.py (SP2 step A1): the file readers, the directory
check, run selection, ``run_source``, the series and event readers, the resampling
helpers, the calibration records and the output-path rule. The names this module had
for them stay importable here, as the same objects or as thin wrappers that raise
ReplayError with the replay's wording.

A selected run is an experiment run (metrics.json ``runs``, compared with the
baseline), a bound re-run or its paired baseline (``bounds``: compared with the paired
baseline, configured by resolved_config.yaml ``bound_runs``), a case (``cases``, its
own settings, compared with nothing) or a run of the offload block (``offload.runs``,
configured by ``offload_runs``: a case's recorded run flying the reference payload,
shown beside the full-load pad, its saving reported in summary.md; a paired pad, the
pad with the same offload and no push, flying its own payload capacity; or a pad
control); ``run_source`` finds which.

The page's text is built from the run data and the metrics, never fixed (SP2 step A1a,
D-SP2-23, KI-029): the drive caveat says what each omission of the assist model does to
the numbers of the runs shown (``drive_caveat``), the structure caveat names each pushed
run's own flown load and peak felt g and, for a penalty row, the assumed stage-1 dry mass
its record charges (``structure_caveat``), an offload run's label and note say which kind
it is, what it measures and how it is quoted (a stage-2 or both-stage solve net of the pad
control, a failed verification read by its sign, a solve that found no offload, the
flags, a pad control's own result: ``run_label``, ``replay_offload_note``,
``offload_comparison_caveat``), and a
directory the local app launched (metrics.json label EXPLORATORY_LABEL) gets
EXPLORATORY_CAVEAT first. The scene page of SP2 reuses these functions, so the two pages
cannot word a caveat differently.

The page's template is package data (src/launchsim/templates/replay.html, shipped in
the wheel by uv_build); its single placeholder REPLAY_DATA_TOKEN is replaced by the
JSON, which must hold no NaN or Infinity (JavaScript's JSON.parse rejects them) and
has every "<" escaped so the data cannot close its <script> element or open an HTML
comment in it.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from importlib import resources
from pathlib import Path
from typing import Any

import pandas as pd

from launchsim import __version__, run_data
from launchsim.compare import CHECK_NA
from launchsim.config import OFFLOAD_GROSS_MODES
from launchsim.metrics_planar import KICK_NONE
from launchsim.offload import NO_OFFLOAD_STATUS
from launchsim.phases import HOLD_KIND
from launchsim.search import OK_STATUS, SEARCH_FAILED_STATUS
from launchsim.summary import UPPER_BOUND_REASONS
from launchsim.units import kg_to_t, m_to_km, pa_to_kpa, t_to_kg, to_percent


class ReplayError(run_data.RunDataError):
    """A user-facing replay problem (a wrong run directory, run name or output path, a
    run without planar columns): the CLI prints it as one error line. A
    run_data.RunDataError (so still a ValueError): the shared readers raise it when the
    replay calls them."""


REPLAY_TEMPLATE = ("templates", "replay.html")
"""Package-relative path of the page template (launchsim/templates/replay.html)."""
REPLAY_DATA_TOKEN = "__REPLAY_DATA__"
"""The template's placeholder for the embedded JSON."""
REPLAY_SUFFIXES = (".html", ".htm")
"""Output extensions ``write_replay_page`` accepts."""
REPLAY_WORDING = "replay shows"
"""Subject and verb of the replay's refusals in the shared checks (run_data.check_run_dir,
run_data.run_source)."""
REPLAY_EARLY_END_S = run_data.GRID_EARLY_END_S
"""End of the finely sampled launch segment [s after release] (run_data.GRID_EARLY_END_S)."""
REPLAY_EARLY_DT_S = run_data.GRID_EARLY_DT_S
"""Sample step of the launch segment [s] (run_data.GRID_EARLY_DT_S)."""
REPLAY_LATE_DT_S = run_data.GRID_LATE_DT_S
"""Sample step after REPLAY_EARLY_END_S [s] (run_data.GRID_LATE_DT_S)."""
REPLAY_GRID_DECIMALS = run_data.GRID_DECIMALS
"""Decimals [s] to which grid times are rounded before de-duplication
(run_data.GRID_DECIMALS)."""
REPLAY_TIME_DECIMALS = run_data.TIME_DECIMALS
"""Decimals [s] of the sample and event times written into the page
(run_data.TIME_DECIMALS)."""
YARDSTICK_SHOWN_KG = 0.5
"""|ideal screening - screening yardstick| [kg] above which the page shows the summary's
yardstick under the ideal screening (they differ when the yardstick basis is P0)."""
PAYLOAD_DECIMALS = 1
"""Decimals of every payload and payload difference [kg] the page writes (0.1 kg): the
reference payload P_ref, a run's payload, a paired pad's or fixed case's difference from
P_ref, the payload change and the screening estimates."""
VERTICAL_TRACK_DEG = 90.0
"""Track angle [deg] of a vertical silo (assist.track.angle_deg)."""
TRACK_ANGLE_TOL_DEG = 1e-6
"""Tolerance [deg] on the vertical-track test."""
INSTANT_IGNITION_TOL_S = 1e-6
"""|t_ign| [s] below which a stage-1 ignition counts as at release."""
DRY_MASS_PARAM = "vehicle.stages.stage1.dry_mass_t"
"""Sensitivity parameter whose +/- cases give dP*/d(stage-1 dry mass)."""
INSERTED = "inserted"
"""metrics.json status of a run that reached the target orbit."""
CONSTANT_ACCEL_MODEL = "constant_accel"
"""Assist model of a prescribed-acceleration push (assist.model), under which the
release speed and the payload do not depend on the carriage mass or the shaft drag."""
VENTED_SHAFT = "vented"
"""assist.shaft of a silo whose air column is not modelled (no shaft drag)."""
EXPLORATORY_LABEL = "exploratory"
"""metrics.json ``label`` of a directory launched from the local app's form (SP2,
D-SP2-12); every other value, and no label, is a recorded experiment. config.py takes
the value as an ExperimentLabel in step A4."""
EXPLORATORY_CAVEAT = (
    "EXPLORATORY app run, not a finding: launched from the local app's form, not from a "
    "committed experiment file, and not pre-registered."
)
"""The first caveat of an exploratory directory's page (``is_exploratory``) and, as
plots.EXPLORATORY_FOOTNOTE, the first footnote line of its animation: one string for the
one mark (D-SP2-12, D-SP2-23)."""

ROLE_RUN = run_data.ROLE_RUN
ROLE_BOUND = run_data.ROLE_BOUND
ROLE_PAIRED_BASELINE = run_data.ROLE_PAIRED_BASELINE
ROLE_CASE = run_data.ROLE_CASE
ROLE_OFFLOAD = run_data.ROLE_OFFLOAD
"""What a selected run is in metrics.json: an experiment run, a bound re-run, the
paired baseline of a bound re-run, a case, or a run of the offload block (an offload
case's recorded run, a paired pad or a pad control: ``offload.runs``; run_source). The
run_data constants under their names here."""

REPLAY_COLUMNS = (
    *run_data.PLANAR_BASE_COLUMNS,
    "gamma_rel_rad",
    "mach",
)
"""timeseries.csv columns the replay reads (a planar_2d run writes all of them): the
shared base columns (the animation's nine) and two more."""

wrapped_deg = run_data.wrapped_deg
"""run_data.wrapped_deg (the same object): an angle [rad] wrapped to [-180, 180] deg."""
Converter = run_data.Converter
"""A unit conversion applied to a timeseries.csv column before resampling."""

SERIES_FIELDS: tuple[run_data.SeriesField, ...] = (
    ("alt_m", "alt_m", None, 1),
    ("x_km", "downrange_m", m_to_km, 3),
    ("v", "speed_rel_mps", None, 2),
    ("gamma_deg", "gamma_rel_rad", wrapped_deg, 2),
    ("m_t", "m_kg", kg_to_t, 3),
    ("g_ax", "felt_axial_g", None, 3),
    ("q_kpa", "q_pa", pa_to_kpa, 3),
    ("mach", "mach", None, 3),
)
"""(page field, timeseries.csv column, unit conversion or None, decimals) of each
resampled series; v is the Earth-relative speed and gamma the flight-path angle of the
Earth-relative velocity, wrapped to [-180, 180] deg before resampling. The replay page's
own field list: run_data.run_series takes it as an argument."""

LOSS_KEYS = (
    "gravity_loss_mps",
    "drag_loss_mps",
    "steering_loss_mps",
    "back_pressure_loss_mps",
)
"""Loss integrals of metrics.json shown per run [m/s]."""

DEG = "\u00b0"
PLUS_MINUS = "\u00b1"


# ------------------------------------------------------------------ reading
#
# The readers live in run_data. The names below are what this module called them before
# SP2 step A1: plain re-exports where the function cannot raise, thin wrappers that pass
# ReplayError and the replay's words where it can.

_mapping = run_data.as_mapping
"""run_data.as_mapping: ``value`` when it is a mapping, else {}."""
_entry_config = run_data.entry_config
"""run_data.entry_config: (run block, vehicle name or None) of one run entry."""
_finite = run_data.finite
"""run_data.finite: a finite float (rounded, a negative zero made 0.0), or None."""
overrides_text = run_data.overrides_text
offload_note = run_data.offload_note
replay_grid = run_data.sample_grid
"""run_data.sample_grid: the common-clock sample times [s after release] of a run."""
defined_mask = run_data.defined_mask
series_values = run_data.series_values
results_ancestors = run_data.results_ancestors
protected_tree = run_data.protected_tree


def check_replay_run_dir(run_dir: Path) -> dict[str, Any]:
    """metrics.json of a planar_2d results directory; raises ReplayError for a missing
    directory, one without metrics.json, a directory that is not an experiment's
    results directory (a sweep point's metrics.json has no ``runs``), or a run of
    another model (vertical_1d has no downrange or flight-path angle to replay).

    run_data.check_run_dir with the replay's wording; plots.check_planar_run_dir is the
    same check with animate's."""
    return run_data.check_run_dir(run_dir, error=ReplayError, wording=REPLAY_WORDING)


def select_runs(run_dir: Path, runs: Sequence[str] | None) -> list[str]:
    """The run names to replay: ``runs`` as given, or the default of run_data.run_names
    (the baseline plus up to three variants, summary order). Raises ReplayError for
    unknown or repeated names, no runs, or more than run_data.MAX_RUNS
    (run_data.select_runs)."""
    return run_data.select_runs(run_dir, runs, what="replay", error=ReplayError)


def run_source(metrics: dict[str, Any], config: dict[str, Any], name: str) -> dict[str, Any]:
    """Where run ``name`` lives in metrics.json and resolved_config.yaml: role (ROLE_RUN,
    ROLE_BOUND, ROLE_PAIRED_BASELINE, ROLE_CASE or ROLE_OFFLOAD), its metrics, its
    comparison, the run it is compared with (None: not compared), its run block, its
    vehicle name (None: the experiment's vehicle), a note on what it is and, for a run
    of the offload block, its ``offload_kind`` (run_data.offload_role: OFFLOAD_CASE,
    OFFLOAD_PAIRED_PAD or OFFLOAD_PAD_CONTROL; None otherwise). An offload run's note is
    the page's own (``replay_offload_note``: two decimals, a paired pad said to fly its
    own payload capacity), not run_data.offload_note's. Raises ReplayError for a run
    folder that metrics.json does not describe (run_data.run_source)."""
    out = run_data.run_source(metrics, config, name, error=ReplayError, wording=REPLAY_WORDING)
    out["offload_kind"] = None
    if out["role"] == ROLE_OFFLOAD:
        offload = _mapping(metrics.get("offload"))
        role = run_data.offload_role(offload, name)
        out["offload_kind"] = None if role is None else role[0]
        out["note"] = replay_offload_note(offload, name, str(metrics.get("baseline")))
    return out


def _tonnes(kg: float) -> str:
    """'41.26 t' of a mass [kg], two decimals."""
    return f"{float(kg_to_t(kg)):.2f} t"


def _percent(fraction: float) -> str:
    """'10.04%' of a fraction, two decimals."""
    return f"{float(to_percent(fraction)):.2f}%"


def offload_stage_word(record: Mapping[str, Any]) -> str | None:
    """Which stage an offload case's propellant comes from, read from its fractions:
    'stage-1' (a stage-2 fraction recorded as 0), 'stage-2' (a stage-1 fraction recorded
    as 0), None when both stages carry some of it or a fraction is missing (results from
    before the stage-2 fraction was written)."""
    s1 = _finite(record.get("stage1_fraction"))
    s2 = _finite(record.get("stage2_fraction"))
    if s1 is None or s2 is None:
        return None
    if s2 == 0.0:
        return "stage-1"
    if s1 == 0.0:
        return "stage-2"
    return None


def offload_shares(record: Mapping[str, Any]) -> str:
    """The share clause of an offload case's note: '; 10.04% of the stage-1 load, 7.96%
    of all' for a stage-1 offload; '; 29.68% of the stage-2 load, 6.15% of all' for a
    stage-2 one (never '0.00% of the stage-1 load'); '; 8.91% of the stage-1 and 8.91% of
    the stage-2 load, 8.91% of all' when both stages carry some; '' without the
    fractions."""
    s1 = _finite(record.get("stage1_fraction"))
    s2 = _finite(record.get("stage2_fraction"))
    tot = _finite(record.get("total_fraction"))
    if tot is None or (s1 is None and s2 is None):
        return ""
    if s2 is not None and s2 > 0.0 and (s1 is None or s1 == 0.0):
        return f"; {_percent(s2)} of the stage-2 load, {_percent(tot)} of all"
    if s1 is None:
        return ""
    if s2 is not None and s2 > 0.0:
        return (
            f"; {_percent(s1)} of the stage-1 and {_percent(s2)} of the stage-2 load, "
            f"{_percent(tot)} of all"
        )
    return f"; {_percent(s1)} of the stage-1 load, {_percent(tot)} of all"


def offload_how(record: Mapping[str, Any], removed: float | None) -> str:
    """How an offload case's propellant was taken out: 'solved', 'imposed' (a fixed
    case), or, for a solve with a stage-2 pre-offload (the frontier case), '40.77 t
    solved on stage 1 plus 2.00 t imposed on stage 2' (``stage2_preoffload_kg``, else
    the gross total less the quoted stage-1 figure)."""
    if record.get("kind") != run_data.OFFLOAD_SOLVED_KIND:
        return "imposed"
    imposed = _finite(record.get("stage2_preoffload_kg"))
    if imposed is None and record.get("mode") in OFFLOAD_GROSS_MODES:
        quoted = _finite(record.get("quoted_offload_kg"))
        if quoted is not None and removed is not None:
            imposed = removed - quoted
    if imposed is None or imposed <= 0.0 or removed is None:
        return "solved"
    solved = _tonnes(removed - imposed)
    return f"{solved} solved on stage 1 plus {_tonnes(imposed)} imposed on stage 2"


def offload_quoted_clause(record: Mapping[str, Any]) -> str:
    """How a solved stage-2 or both-stage case is quoted (D-SP1-10; summary.md's basis
    row): '; quoted 31.39 t net of the pad control's 0.51 t (summary.md basis row: a
    property of the vehicle model, not of the assist)' from ``quoted_offload_kg`` and
    ``pad_control_offload_kg``; the record's own ``quoted_basis`` when nothing is quoted
    ('not quoted: ...'); '' for a stage-1 solve (gross, the headline), a fixed case or a
    record without the keys."""
    if record.get("kind") != run_data.OFFLOAD_SOLVED_KIND:
        return ""
    mode = record.get("mode")
    if mode is None or mode in OFFLOAD_GROSS_MODES:
        return ""
    quoted = _finite(record.get("quoted_offload_kg"))
    basis = record.get("quoted_basis")
    if quoted is None:
        return f"; {basis}" if isinstance(basis, str) and basis else ""
    control = _finite(record.get("pad_control_offload_kg"))
    against = "" if control is None else f"'s {_tonnes(control)}"
    return (
        f"; quoted {_tonnes(quoted)} net of the pad control{against} (summary.md basis row: "
        "a property of the vehicle model, not of the assist)"
    )


def has_flags(record: Mapping[str, Any]) -> bool:
    """True when a case or pad-control record carries flags (a non-empty ``flags`` list)."""
    flags = record.get("flags")
    return isinstance(flags, Sequence) and not isinstance(flags, str) and bool(flags)


def pad_control_record(offload: Mapping[str, Any], mode: Any) -> dict[str, Any] | None:
    """The ``pad_controls`` record of metrics.json's ``offload`` block for ``mode``
    (stage1, stage2 or both), or None when the block has none for it."""
    for control in offload.get("pad_controls") or []:
        control = _mapping(control)
        if control.get("mode") == mode:
            return control
    return None


def verification_reading(verification: Mapping[str, Any]) -> tuple[str, str, bool]:
    """What a failed verification says about x*, the gross removal, read from the sign of
    its P* - P_ref (``delta_kg`` against ``tolerance_kg``; RQ1-fuel-offload-2d
    'Definition', docs/physics.md 'Independent verification'): (the size, ' (+15.36 kg
    against 2.6 kg)' or '' without the numbers; the reading; whether it is the lower-bound
    one). Above P_ref by more than the tolerance the independent search carries more than
    P_ref at x*, so the solve left gamma* suboptimal and 'the gross removal is a flagged
    lower bound' (the project's rule; silo_cold_s2's +15.36 kg). Below it by more than the
    tolerance the independent search carried less than P_ref at x*, which the recorded run
    (flying P_ref, inserted) contradicts, so nothing is a bound: 'the gross removal is
    uncertain both ways, not a lower bound (...)'. Otherwise the verification search did
    not end ok (or recorded no delta): 'the gross removal is unverified (the verification
    search ended <status>)'."""
    delta = _finite(verification.get("delta_kg"))
    tol = _finite(verification.get("tolerance_kg"))
    size = "" if delta is None or tol is None else f" ({delta:+.2f} kg against {tol:.1f} kg)"
    if delta is not None and tol is not None and delta > tol:
        return size, "the gross removal is a flagged lower bound", True
    if delta is not None and tol is not None and delta < -tol:
        return (
            size,
            "the gross removal is uncertain both ways, not a lower bound (the independent search "
            "carried less than P_ref at this removal)",
            False,
        )
    status = verification.get("status")
    ended = "" if status in (None, OK_STATUS) else f" (the verification search ended {status})"
    return size, f"the gross removal is unverified{ended}", False


def offload_verdict_clause(
    record: Mapping[str, Any], control: Mapping[str, Any] | None = None
) -> str:
    """The verdicts of a case's record. The verification verdict is on x*, the gross
    removal (RQ1-fuel-offload-2d, 'Verification'), and depends on the sign of the
    verification's P* - P_ref (``verification_reading``): '; verification failed (+15.36 kg
    against 2.6 kg): the gross removal is a flagged lower bound' when the independent
    search returned a payload above P_ref; '...: the gross removal is uncertain both ways,
    not a lower bound (...)' when it returned one below; '...: the gross removal is
    unverified (...)' when the search did not end ok. ``control`` is the pad control
    record the case is quoted net of (a stage-2 or both-stage solve; None for a gross
    figure): when it carries flags the net figure is said to be uncertain both ways (it
    subtracts a flagged control), after the verification verdict when there is one. Then
    '; 4 flags (summary.md, Flags)' when the case carries flags; '' for a passed,
    unverified and unflagged case."""
    text = ""
    verification = _mapping(record.get("verification"))
    failed = verification.get("passed") is False
    flagged_control = control is not None and has_flags(control)
    if failed:
        size, reading, lower = verification_reading(verification)
        text += f"; verification failed{size}: {reading}"
        if flagged_control and lower:
            text += (
                " and the net figure, which also subtracts a flagged pad control, is uncertain "
                "both ways"
            )
        elif flagged_control:
            text += ", as is the net figure, which also subtracts a flagged pad control"
    elif flagged_control:
        text += "; the net figure subtracts a flagged pad control and is uncertain both ways"
    if has_flags(record):
        n = len(record["flags"])
        text += f"; {n} flag{'' if n == 1 else 's'} (summary.md, Flags)"
    return text


def pad_control_result(record: Mapping[str, Any], with_flags: bool = True) -> str | None:
    """What a pad control found, from its record: 'none found (status no_offload,
    consistency pass; its recorded run at x = 0 ends 0.0016 kg short, a resolution
    effect)' or '0.51 t (status ok)', then (``with_flags``) its verdict clause
    (``offload_verdict_clause``: the flags); None for a record without ``offload_kg`` or
    ``status``."""
    offload = _finite(record.get("offload_kg"))
    status = record.get("status")
    if offload is None and status is None:
        return None
    none = status == NO_OFFLOAD_STATUS or (status is None and offload == 0.0)
    text = "none found" if none else ("an unknown amount" if offload is None else _tonnes(offload))
    verdicts = [] if status is None else [f"status {status}"]
    verdict = record.get("consistency")
    if isinstance(verdict, str) and verdict and verdict != CHECK_NA:
        verdicts.append(f"consistency {verdict}")
    inside = [", ".join(verdicts)] if verdicts else []
    m_res = _finite(record.get("m_res_kg"))
    if record.get("resolution_effect") is True and m_res is not None:
        inside.append(
            f"its recorded run at x = 0 ends {abs(m_res):.4f} kg short, a resolution effect"
        )
    if inside:
        text += f" ({'; '.join(inside)})"
    return text + (offload_verdict_clause(record) if with_flags else "")


def payload_reading(delta: float, ref: str, imposed: bool) -> str:
    """How a recorded payload stands against P_ref, for the page, from ``delta`` =
    payload - P_ref [kg] (rounded to 0.1 kg) and ``ref``, how the sentence calls the
    reference ('P_ref = 1,000.0 kg', or 'P_ref' when its value was just given): ' (41.4 kg
    short of P_ref = 1,000.0 kg)', ' (10.0 kg above P_ref = 1,000.0 kg)' or ' (equal to
    P_ref = 1,000.0 kg)' for a paired pad; for a fixed case (``imposed``) the sign carries
    its reading (D-SP2-27): above P_ref the run carries more than the pad, so the imposed
    offload is not the largest possible; short of it, a payload loss at that offload, not
    a propellant saving."""
    if delta == 0.0:
        return f" (equal to {ref})"
    if delta > 0.0:
        why = ": it carries more than the pad, so the imposed offload is not the largest possible"
        return f" ({delta:,.1f} kg above {ref}{why if imposed else ''})"
    why = ": a payload loss at this offload, not a propellant saving"
    return f" ({abs(delta):,.1f} kg short of {ref}{why if imposed else ''})"


def penalty_added_kg(record: Mapping[str, Any]) -> float | None:
    """The assumed stage-1 dry mass a penalty row charges on its run [kg], from the case
    record: ``stage1_dry_mass_added_kg`` when it is above 0; 0.0 for a record whose
    ``assumed_penalty`` is true but whose mass is unrecorded; None for a case without a
    penalty (RQ1-fuel-offload-2d, 'Structural penalty rows and break-even': a parametric
    assumption added to the assisted run only, not a sized structure)."""
    added = _finite(record.get("stage1_dry_mass_added_kg"))
    if added is not None and added > 0.0:
        return added
    return 0.0 if record.get("assumed_penalty") is True else None


def penalty_mass_text(added_kg: float) -> str:
    """'+8.1 t of stage-1 dry mass' (the tonnes as the findings write them: +2 t, +8.1 t);
    'stage-1 dry mass of unrecorded size' for the 0.0 of ``penalty_added_kg``."""
    if added_kg <= 0.0:
        return "stage-1 dry mass of unrecorded size"
    return f"+{float(kg_to_t(added_kg)):g} t of stage-1 dry mass"


def penalty_clause(record: Mapping[str, Any]) -> str:
    """' with an assumed +8.1 t of stage-1 dry mass' for a penalty row's note, after how
    its propellant was taken out; '' for a case without a penalty."""
    added = penalty_added_kg(record)
    return "" if added is None else f" with an assumed {penalty_mass_text(added)}"


def solve_outcome(record: Mapping[str, Any]) -> str | None:
    """How a solved case's solve ended when it found no x*, so the note never reads like
    a successful solve of 0.00 t: 'the solve found no offload (status no_offload)' (the
    full load already falls short of P_ref; the recorded run is the one at x = 0), 'the
    solve failed (status search_failed: edge)' with the ``solve.failure_kind`` when it is
    recorded, 'the solve did not end ok (status <other>)' for any other status; None for
    an ok solve, a record without a status, or a fixed case."""
    if record.get("kind") != run_data.OFFLOAD_SOLVED_KIND:
        return None
    status = record.get("status")
    if status in (None, OK_STATUS):
        return None
    if status == NO_OFFLOAD_STATUS:
        return f"the solve found no offload (status {status})"
    kind = _mapping(record.get("solve")).get("failure_kind")
    detail = f"status {status}" + ("" if kind is None else f": {kind}")
    verb = "failed" if status == SEARCH_FAILED_STATUS else "did not end ok"
    return f"the solve {verb} ({detail})"


def replay_offload_note(offload: Mapping[str, Any], name: str, baseline: str) -> str:
    """What an offload run is, for the page, from metrics.json's ``offload`` block
    (run_data.offload_role tells which): an offload case's recorded run (the propellant
    it carries less, in tonnes, naming the stage when one stage carries it all, how it
    was taken out (``offload_how``, with the assumed stage-1 dry mass of a penalty row,
    ``penalty_clause``), its shares of the loads (``offload_shares``) and the payload [kg]
    it flies against the reference payload; for a fixed case the payload's difference
    from P_ref with its reading (``payload_reading``, D-SP2-27); for a stage-2 or
    both-stage solve how it is quoted, net of the pad control (``offload_quoted_clause``);
    a failed verification, a flagged pad control behind a net figure and the flags
    (``offload_verdict_clause``); for a solve that found no x* (status no_offload or
    search_failed) how it ended instead of an amount, with the recorded run at x = 0 when
    there is one (``solve_outcome``)), a paired pad (the baseline with the case's offload
    and no push, flying its own payload capacity, the recorded ``payload_kg``, against
    P_ref) or a pad control with what it found (``pad_control_result``). Tonnes and
    percentages carry two decimals, as every other page of the project prints them
    (run_data.offload_note, the animation's wording, keeps one); payloads
    PAYLOAD_DECIMALS."""
    p_ref = _finite(offload.get("reference_payload_kg"), PAYLOAD_DECIMALS)
    ref = f"{p_ref:,.1f} kg" if p_ref is not None else "the reference payload"
    role = run_data.offload_role(offload, name)
    if role is None:
        return "a run of the offload block"
    kind, record = role
    if kind == run_data.OFFLOAD_PAD_CONTROL:
        text = f"pad control ({record.get('mode')}): {baseline}'s own offload at P_ref = {ref}"
        result = pad_control_result(record)
        return text if result is None else f"{text}: {result}"
    removed = _finite(record.get("total_offload_kg"))
    stage = offload_stage_word(record)
    if kind == run_data.OFFLOAD_PAIRED_PAD:
        paired = _mapping(record.get("paired_pad"))
        own = _mapping(_mapping(offload.get("runs")).get(name))
        payload = _finite(own.get("payload_kg"), PAYLOAD_DECIMALS)
        if payload is None:
            payload = _finite(paired.get("payload_kg"), PAYLOAD_DECIMALS)
        delta = _finite(paired.get("payload_delta_vs_reference_kg"), PAYLOAD_DECIMALS)
        if delta is None and payload is not None and p_ref is not None:
            delta = round(payload - p_ref, PAYLOAD_DECIMALS)
        same = " ".join(
            bit
            for bit in ("" if removed is None else _tonnes(removed), stage or "", "offload")
            if bit
        )
        text = (
            f"paired pad of offload case {record.get('name')}: {baseline} with the same "
            f"{same} and no push, flying its own payload capacity"
        )
        if payload is not None:
            text += f", {payload:,.1f} kg"
        if delta is None:
            return text + f", not P_ref = {ref}"
        return text + payload_reading(delta, f"P_ref = {ref}", imposed=False)
    payload = _finite(record.get("payload_kg"), PAYLOAD_DECIMALS)
    solved = record.get("kind") == run_data.OFFLOAD_SOLVED_KIND
    outcome = solve_outcome(record)
    if outcome is not None:
        # no x*: no amount, no shares, nothing quoted; the flags still count
        flies = "" if payload is None else f", its recorded run at x = 0 flying {payload:,.1f} kg"
        return (
            f"offload case {name} of {record.get('of')}: {outcome}{flies} against "
            f"{baseline}'s full load at P_ref = {ref}, the same orbit"
            f"{offload_verdict_clause(record)}"
        )
    what = "stage-2 propellant" if stage == "stage-2" else "propellant"
    amount = (
        "an unknown amount of propellant"
        if removed is None
        else f"{_tonnes(removed)} less {what} ({offload_how(record, removed)}"
        f"{penalty_clause(record)}{offload_shares(record)})"
    )
    flies = "" if payload is None else f", flying {payload:,.1f} kg"
    reading = ""
    if not solved and payload is not None and p_ref is not None:
        reading = payload_reading(round(payload - p_ref, PAYLOAD_DECIMALS), "P_ref", imposed=True)
    control = None
    if (
        solved
        and record.get("mode") not in (None, *OFFLOAD_GROSS_MODES)
        and _finite(record.get("quoted_offload_kg")) is not None
    ):
        control = pad_control_record(offload, record.get("mode"))
    return (
        f"offload case {name} of {record.get('of')}: {amount}{flies} against "
        f"{baseline}'s full load at P_ref = {ref}, the same orbit{reading}"
        f"{offload_quoted_clause(record)}{offload_verdict_clause(record, control)}"
    )


def read_series(run_dir: Path, name: str) -> pd.DataFrame:
    """<run_dir>/<name>/timeseries.csv sorted on the time after release, one row per
    time (the last of duplicates, which phase boundaries write twice). Raises
    ReplayError for a series without REPLAY_COLUMNS or an empty one
    (run_data.read_series)."""
    return run_data.read_series(run_dir, name, REPLAY_COLUMNS, error=ReplayError)


# ------------------------------------------------------------------ resampling


def run_series(frame: pd.DataFrame) -> dict[str, Any]:
    """The resampled series of one run: t [s after release], each SERIES_FIELDS field
    and the phase name per sample (the phase of the last row at or before it)
    (run_data.run_series with the replay's field list)."""
    return run_data.run_series(frame, SERIES_FIELDS)


def run_events(path: Path, offset_s: float) -> list[dict[str, Any]]:
    """Every event of events.csv: time after release (t_s - ``offset_s``) [s], name,
    stage, altitude [m], downrange [km] and Earth-relative speed [m/s]. A projection of
    run_data.read_events to these six keys, in this order, with the page's rounding; the
    downrange is rounded without the negative-zero fix of ``_finite``, so a small
    negative downrange stays -0.0 (as the page has always written it)."""
    out = []
    for row in run_data.read_events(path, offset_s, error=ReplayError):
        downrange = _finite(row.downrange_m)
        out.append(
            {
                "t": _finite(row.t_rel_s, REPLAY_TIME_DECIMALS),
                "name": row.name,
                "stage": "" if row.stage is None else row.stage,
                "alt_m": _finite(row.alt_m, 1),
                "x_km": None if downrange is None else round(float(m_to_km(downrange)), 3),
                "v": _finite(row.speed_rel_mps, 2),
            }
        )
    return out


# ------------------------------------------------------------------ run text


def run_assist(run_cfg: Mapping[str, Any]) -> dict[str, Any]:
    """The assist block of a run block of resolved_config.yaml ({} when absent)."""
    return _mapping(run_cfg.get("assist"))


def is_assisted(assist: dict[str, Any]) -> bool:
    """True for a run with a ground assist (assist model other than none)."""
    return str(assist.get("model", "none")) != "none"


def is_vertical(assist: dict[str, Any]) -> bool:
    """True when the assist track is a vertical silo (track angle 90 deg)."""
    angle = (assist.get("track") or {}).get("angle_deg")
    return angle is not None and abs(float(angle) - VERTICAL_TRACK_DEG) < TRACK_ANGLE_TOL_DEG


def startup_text(m: dict[str, Any]) -> str:
    """Stage-1 startup shape of a run's metrics: '2 s ramp', 'lag, tau 1 s', 'instant'."""
    kind = m.get("startup_kind_stage1")
    t = _finite(m.get("t_startup_s_stage1"))
    if kind == "ramp" and t is not None:
        return f"{t:g} s ramp"
    if kind == "lag" and t is not None:
        return f"lag, tau {t:g} s"
    if kind == "step":
        return "instant"
    return str(kind) if kind else "startup unknown"


def ignition_text(m: dict[str, Any], assisted: bool) -> str:
    """When and how stage 1 lights, relative to release, from a run's metrics."""
    t_ign = _finite(m.get("t_ign_rel_release_s_stage1"))
    shape = startup_text(m)
    if t_ign is None:
        return "stage 1 never lit"
    if abs(t_ign) < INSTANT_IGNITION_TOL_S:
        if m.get("startup_kind_stage1") == "step":
            return "instant full thrust at release (yardstick)"
        return f"stage 1 lit at release ({shape})"
    if t_ign > 0.0:
        return f"cold start: stage 1 lit T+{t_ign:.1f} s after release ({shape})"
    before = f"T\u2212{abs(t_ign):.1f} s before release"
    if not assisted:
        return f"stage 1 lit {before}, held down on the pad ({shape})"
    if _finite(m.get("hold_duration_s")) is None:
        return f"stage 1 lit on the track, {before} ({shape})"
    return f"stage 1 lit {before}, held at the start of the track ({shape})"


def push_accel_g(assist: Mapping[str, Any], m: Mapping[str, Any]) -> float | None:
    """The net acceleration of a run's push in g0, for labels: the run's ``net_accel_g``
    metric (metrics.json; written for every planar push whichever way its config
    states it, so a push defined by ``exit_speed_mps`` has it too), else the assist
    block's ``net_accel_g`` key (resolved_config.yaml; results written before the
    metric existed). None when neither holds a finite number."""
    accel = _finite(m.get("net_accel_g"))
    return _finite(assist.get("net_accel_g")) if accel is None else accel


def carriage_mass_kg(assist: Mapping[str, Any], m: Mapping[str, Any]) -> float | None:
    """The carriage mass of a run's push [kg]: the run's ``carriage_mass_kg`` metric
    (metrics.json), else the assist block's ``carriage_mass_t`` (resolved_config.yaml;
    results written before the metric existed). None when neither holds a finite
    number."""
    mass = _finite(m.get("carriage_mass_kg"))
    if mass is not None:
        return mass
    tonnes = _finite(assist.get("carriage_mass_t"))
    return None if tonnes is None else float(t_to_kg(tonnes))


def is_vented(assist: Mapping[str, Any]) -> bool:
    """True when a run's shaft is vented (assist.shaft; the only setting the config
    takes today, so the air column is never modelled). No metric records it."""
    return assist.get("shaft") == VENTED_SHAFT


def kicked(m: Mapping[str, Any]) -> bool:
    """True when a run's metrics record a pitch kick: ``kick_regime`` other than
    KICK_NONE, else (results without the key) a finite ``kick_t_s``. A run whose stage 1
    never lit (a failed ignition) has none."""
    regime = m.get("kick_regime")
    if regime is not None:
        return str(regime) != KICK_NONE
    return _finite(m.get("kick_t_s")) is not None


def is_exploratory(metrics: Mapping[str, Any]) -> bool:
    """True when metrics.json carries the EXPLORATORY_LABEL (an app run, D-SP2-12); a
    recorded directory (label null, calibration or guidance_study) is not."""
    return metrics.get("label") == EXPLORATORY_LABEL


def assist_text(assist: dict[str, Any], m: dict[str, Any]) -> str:
    """The ground start of a run: 'pad start' or the assist geometry, drive (the net
    acceleration of ``push_accel_g``), carriage mass and exhaust impingement fraction
    (when non-zero) and exit speed, from resolved_config.yaml and metrics.json."""
    if not is_assisted(assist):
        return "pad start"
    depth = _finite(m.get("track_start_altitude_m"))
    angle = _finite((assist.get("track") or {}).get("angle_deg"))
    if is_vertical(assist):
        where = "vertical silo"
    elif angle is not None:
        where = f"track at {angle:g}{DEG}"
    else:
        where = "track"
    if depth is not None and depth < 0.0:
        where += f" {abs(depth):.0f} m deep"
    model = str(assist.get("model"))
    drive = f"{model} drive"
    accel = push_accel_g(assist, m)
    if model == CONSTANT_ACCEL_MODEL and accel is not None:
        drive = f"{accel:g} g net push"
    parts = [where, drive]
    carriage = _finite(assist.get("carriage_mass_t"))
    if carriage is not None and carriage > 0.0:
        parts.append(f"{carriage:g} t carriage")
    impinged = _finite(assist.get("exhaust_impingement_fraction"))
    if impinged is not None and impinged > 0.0:
        parts.append(f"exhaust impingement fraction {impinged:g}")
    exit_v = _finite(m.get("exit_speed_mps"))
    if exit_v is not None:
        parts.append(f"exit {exit_v:.1f} m/s")
    return ", ".join(parts)


def is_yardstick(m: dict[str, Any]) -> bool:
    """True for a run whose stage 1 starts instantly (step startup): a yardstick, since
    no real engine reaches full thrust instantly; drawn dashed."""
    return m.get("startup_kind_stage1") == "step"


def orbit_text(run_cfg: Mapping[str, Any]) -> str:
    """The target orbit of a run block ('200 km circular orbit'), or 'target orbit'."""
    target = _mapping(_mapping(run_cfg.get("planar")).get("target_orbit"))
    alt = _finite(target.get("altitude_km"))
    if alt is None:
        return "target orbit"
    return f"{alt:g} km {target.get('kind', 'circular')} orbit"


def is_rotating(run_cfg: Mapping[str, Any]) -> bool:
    """True when a run block flies over a rotating Earth (site.include_rotation)."""
    return bool(_mapping(run_cfg.get("site")).get("include_rotation", True))


def earth_text(rotating: bool) -> str:
    """'rotating Earth' or 'non-rotating Earth'."""
    return "rotating Earth" if rotating else "non-rotating Earth"


def settings_text(source: Mapping[str, Any], base_cfg: Mapping[str, Any], vehicle: str) -> str:
    """How a run's own settings differ from the baseline's (target orbit, Earth
    rotation, vehicle), e.g. '185 km circular orbit, non-rotating Earth'; '' when none
    does."""
    run_cfg = source["config"]
    parts = []
    if orbit_text(run_cfg) != orbit_text(base_cfg):
        parts.append(orbit_text(run_cfg))
    if is_rotating(run_cfg) != is_rotating(base_cfg):
        parts.append(earth_text(is_rotating(run_cfg)))
    own = source["vehicle"]
    if own is not None and own != vehicle:
        parts.append(f"vehicle {own}")
    return ", ".join(parts)


def site_tags(base_cfg: Mapping[str, Any]) -> list[str]:
    """Tags of the page header from the baseline's run block: model, Earth, losses,
    guidance, throttling, orbit, site."""
    site = _mapping(base_cfg.get("site"))
    tags = [
        "planar 2-D",
        earth_text(is_rotating(base_cfg)),
        "drag and back-pressure",
        "sweep-optimized guidance",
        "unthrottled",
        orbit_text(base_cfg).removesuffix(" orbit"),
    ]
    lat, az = _finite(site.get("latitude_deg")), _finite(site.get("azimuth_deg"))
    if lat is not None and az is not None:
        tags.append(f"latitude {lat:g}{DEG}, azimuth {az:g}{DEG}")
    return tags


# ------------------------------------------------------------------ page text


def _names(names: Sequence[str]) -> str:
    """'a', 'a and b', 'a, b and c'."""
    items = list(names)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def dry_mass_slopes(metrics: dict[str, Any]) -> dict[str, tuple[float, float, float]]:
    """Per run with a + and a - DRY_MASS_PARAM sensitivity case: (dP*/d(stage-1 dry
    mass) [kg/kg] by central difference of the cases' absolute payload capacities, the
    - and + case fractions). The slope rests on those payloads alone, so how a case
    compares with the unperturbed baseline has no bearing on it."""
    cases: dict[str, dict[float, tuple[float, float]]] = {}
    for case in metrics.get("sensitivity") or []:
        case = _mapping(case)
        if case.get("param") != DRY_MASS_PARAM:
            continue
        value, payload = _finite(case.get("value_si")), _finite(case.get("payload_kg"))
        frac = _finite(case.get("fraction"))
        if value is None or payload is None or frac is None:
            continue
        cases.setdefault(str(case.get("of")), {})[frac] = (value, payload)
    out: dict[str, tuple[float, float, float]] = {}
    for name, pts in cases.items():
        hi, lo = max(pts), min(pts)
        if hi > 0.0 > lo and pts[hi][0] != pts[lo][0]:
            slope = (pts[hi][1] - pts[lo][1]) / (pts[hi][0] - pts[lo][0])
            out[name] = (slope, lo, hi)
    return out


def fraction_text(lo: float, hi: float) -> str:
    """'+/-10%' for symmetric case fractions (-0.1, 0.1), else '-5%/+10%'."""
    if math.isclose(-lo, hi):
        return f"{PLUS_MINUS}{100 * hi:g}%"
    return f"{100 * lo:+g}%/{100 * hi:+g}%"


def calibration_caveat(vehicle: str) -> str:
    """The calibration caveat of a vehicle from run_data.CALIBRATION_RECORDS: its gap and
    whether it lies within the gate band (``run_data.inside_calibration_band``) or
    outside it, a documented miss; or a note that it has no calibration record."""
    record = run_data.CALIBRATION_RECORDS.get(vehicle)
    if record is None:
        return (
            f"Vehicle {vehicle} has no calibration record on file: read these numbers as "
            "differences between runs, not as absolute payloads."
        )
    model_kg, reference_kg, note = record
    gap = run_data.calibration_gap(model_kg, reference_kg)
    side = "high" if gap >= 0.0 else "low"
    band_pct = 100 * run_data.CALIBRATION_BAND
    band = (
        f"within the {PLUS_MINUS}{band_pct:.0f}% gate"
        if run_data.inside_calibration_band(gap)
        else f"outside the {PLUS_MINUS}{band_pct:.0f}% gate, a documented miss"
    )
    return (
        f"The vehicle ({vehicle}) calibrates {100 * gap:+.1f}% {side}: its calibration "
        f"run carries {model_kg:,.0f} kg against the published {reference_kg:,.0f} kg, "
        f"{band} ({note}). Read these numbers as differences between runs."
    )


def case_record(
    source: Mapping[str, Any], offload: Mapping[str, Any], name: str
) -> dict[str, Any] | None:
    """The ``offload.cases`` record of run ``name`` when it is an offload case's recorded
    run (``offload_kind`` of run_source is OFFLOAD_CASE; run_data.offload_role finds the
    record); None for every other run."""
    if source.get("offload_kind") != run_data.OFFLOAD_CASE:
        return None
    role = run_data.offload_role(offload, name)
    return None if role is None else role[1]


def flown_load_bits(
    run: Mapping[str, Any], source: Mapping[str, Any], offload: Mapping[str, Any]
) -> list[str]:
    """The load a pushed run flew, as clauses: the stack mass [t] when the push began (the
    ``liftoff_mass_kg`` metric, the stack before ignition, less the
    ``hold_propellant_burned_kg`` of a run lit and held at the track start before the
    push; for a cold start, or a run lit during the push, the liftoff mass itself) and,
    for an offload case's recorded run, the propellant it carries less (the case's
    ``total_offload_kg``, two decimals; nothing for a solve that found no offload); []
    when neither is recorded."""
    bits = []
    mass = _finite(source["metrics"].get("liftoff_mass_kg"))
    if mass is not None:
        hold = _finite(source["metrics"].get("hold_propellant_burned_kg"))
        if hold is not None and hold > 0.0:
            mass -= hold
        bits.append(f"{float(kg_to_t(mass)):.1f} t at push start")
    record = case_record(source, offload, run["key"])
    removed = None if record is None else _finite(record.get("total_offload_kg"))
    if removed is not None and removed > 0.0:
        bits.append(f"{float(kg_to_t(removed)):.2f} t less propellant")
    return bits


def flown_load_text(
    run: Mapping[str, Any], source: Mapping[str, Any], offload: Mapping[str, Any]
) -> str:
    """A pushed run's name with the load it flew in parentheses (``flown_load_bits``):
    'silo_cold_s1 (531.1 t at push start, 41.26 t less propellant)'; the name alone when
    nothing is recorded."""
    bits = flown_load_bits(run, source, offload)
    return run["key"] + (f" ({', '.join(bits)})" if bits else "")


def uncharged_structure_sentence(
    assisted: Sequence[dict[str, Any]],
    sources: Mapping[str, Mapping[str, Any]],
    offload: Mapping[str, Any],
) -> str:
    """The sentence of the pushed runs that carry no structural penalty: 'No structural
    mass is charged for the assist load case: ' then each run's own flown load
    (``flown_load_text``) and its own peak felt g on the track (runs with the same peak
    grouped, 'silo_cold_s1 (...) feels up to 4.0 g during the push'; a run without a
    recorded peak 'rides the push with no recorded peak felt g')."""
    by_peak: dict[str | None, list[str]] = {}
    for r in assisted:
        peak = None if r["felt_g_track"] is None else f"{r['felt_g_track']:.1f} g"
        by_peak.setdefault(peak, []).append(flown_load_text(r, sources[r["key"]], offload))
    clauses = []
    for k, (peak, loads) in enumerate(item for item in by_peak.items() if item[0] is not None):
        verb = "" if k else (" feels" if len(loads) == 1 else " feel")
        clauses.append(f"{_names(loads)}{verb} up to {peak}")
    text = "No structural mass is charged for the assist load case: "
    if clauses:
        text += " and ".join(clauses) + " during the push"
    unknown = by_peak.get(None)
    if unknown:
        if clauses:
            text += "; "
        text += f"{_names(unknown)} {'rides' if len(unknown) == 1 else 'ride'} the push"
        text += " with no recorded peak felt g"
    return text + "."


def penalty_structure_sentence(
    charged: Sequence[dict[str, Any]],
    penalties: Mapping[str, float],
    sources: Mapping[str, Mapping[str, Any]],
    offload: Mapping[str, Any],
) -> str:
    """The sentence of the pushed runs that are penalty rows (RQ1-fuel-offload-2d,
    'Structural penalty rows and break-even'), each with its own flown load and peak felt
    g: 'An assumed +8.1 t of stage-1 dry mass is charged on silo_cold_s1_dry+8.1t (578.5 t
    at push start, 1.98 t less propellant, up to 4.0 g during the push): a parametric
    assumption, not a sized structure; no structural model exists.' Runs with the same
    penalty are grouped; another penalty follows as 'and an assumed +2 t of stage-1 dry
    mass on ...'. ``penalties``: ``penalty_added_kg`` per run key."""
    groups: dict[float, list[str]] = {}
    for r in charged:
        bits = flown_load_bits(r, sources[r["key"]], offload)
        if r["felt_g_track"] is not None:
            bits.append(f"up to {r['felt_g_track']:.1f} g during the push")
        item = r["key"] + (f" ({', '.join(bits)})" if bits else "")
        groups.setdefault(penalties[r["key"]], []).append(item)
    pieces = [
        f"an assumed {penalty_mass_text(kg)} {'is charged ' if k == 0 else ''}on {_names(items)}"
        for k, (kg, items) in enumerate(groups.items())
    ]
    text = " and ".join(pieces)
    closing = (
        "a parametric assumption, not a sized structure"
        if len(charged) == 1
        else "parametric assumptions, not sized structures"
    )
    return f"{text[0].upper()}{text[1:]}: {closing}; no structural model exists."


def structure_caveat(
    runs: Sequence[dict[str, Any]],
    metrics: dict[str, Any],
    sources: Mapping[str, Mapping[str, Any]],
) -> str | None:
    """The structural-mass caveat of the assisted runs, worded from each run's record:
    for the runs without a structural penalty, that none is charged, with each run's own
    flown load and peak felt g (``uncharged_structure_sentence``); for a penalty row (an
    offload case whose record charges an assumed stage-1 dry mass, ``penalty_added_kg``),
    that this assumed mass is charged on it, an assumption and not a sized structure, and
    that no structural model exists (``penalty_structure_sentence``); then, when
    sensitivity cases give dP*/d(stage-1 dry mass), the extra stage-1 structure that
    would cancel each positive gain. Each run uses its own dry-mass cases; a run without
    them borrows the slope of the first selected assisted run that has them (else any
    run's) and the text says so. None without an assisted run."""
    assisted = [r for r in runs if r["assisted"]]
    if not assisted:
        return None
    offload = _mapping(metrics.get("offload"))
    penalties: dict[str, float] = {}
    for r in assisted:
        record = case_record(sources[r["key"]], offload, r["key"])
        added = None if record is None else penalty_added_kg(record)
        if added is not None:
            penalties[r["key"]] = added
    free = [r for r in assisted if r["key"] not in penalties]
    charged = [r for r in assisted if r["key"] in penalties]
    sentences = []
    if free:
        sentences.append(uncharged_structure_sentence(free, sources, offload))
    if charged:
        sentences.append(penalty_structure_sentence(charged, penalties, sources, offload))
    text = " ".join(sentences)
    slopes = {k: v for k, v in dry_mass_slopes(metrics).items() if v[0] < 0.0}
    gains = [r for r in assisted if (r["payload_delta_kg"] or 0.0) > 0.0]
    if not slopes or not gains:
        return text
    fallback = next((r["key"] for r in assisted if r["key"] in slopes), sorted(slopes)[0])
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in gains:
        groups.setdefault(r["key"] if r["key"] in slopes else fallback, []).append(r)
    kg_per_t = float(t_to_kg(1.0))
    pieces = []
    for src, members in groups.items():
        slope, lo, hi = slopes[src]
        tonnes = [
            f"{float(kg_to_t(r['payload_delta_kg'] / -slope)):.1f} t for {r['key']}"
            for r in members
        ]
        piece = (
            f"{_names(tonnes)} ({src}'s {fraction_text(lo, hi)} dry-mass cases: "
            f"{-slope * kg_per_t:.0f} kg of payload per tonne of stage-1 dry mass"
        )
        borrowed = [r["key"] for r in members if r["key"] != src]
        if borrowed:
            one = len(borrowed) == 1
            piece += (
                f", applied to {_names(borrowed)}, which {'has' if one else 'have'} no "
                f"such cases of {'its' if one else 'their'} own"
            )
        pieces.append(piece + ")")
    text += " Extra stage-1 structure of about " + "; ".join(pieces) + " would cancel the gain."
    return text


def _unless_all(names: Sequence[str], assisted: Sequence[str]) -> str:
    """' (a and b)' naming the runs a clause applies to, '' when it applies to every
    assisted run."""
    return "" if list(names) == list(assisted) else f" ({_names(names)})"


def paired_baseline_metrics(metrics: Mapping[str, Any], name: str) -> dict[str, Any]:
    """The ``paired_baseline_metrics`` of the bounds record whose ``run`` is ``name`` (the
    metrics of the paired baseline a bound re-run is compared with); {} when metrics.json
    has no such record."""
    for bound in metrics.get("bounds") or []:
        bound = _mapping(bound)
        if bound.get("run") == name:
            return _mapping(bound.get("paired_baseline_metrics"))
    return {}


def kick_partner(
    name: str, source: Mapping[str, Any], metrics: Mapping[str, Any]
) -> tuple[str, bool, float | None]:
    """(name, paired, peak q-alpha [Pa rad]) of the run a pushed run's kick is judged
    against: for a bound re-run (ROLE_BOUND) its paired baseline, the run it is compared
    with (``compared_to``; its metrics from the bounds record, ``paired_baseline_metrics``;
    ``paired`` True); for every other run the experiment baseline (``paired`` False). The
    peak q-alpha is None when the partner has none recorded."""
    baseline = str(metrics.get("baseline"))
    partner = source.get("compared_to") if source.get("role") == ROLE_BOUND else None
    if partner is None:
        base_q = _mapping(_mapping(metrics.get("runs")).get(baseline)).get("peak_q_alpha")
        return baseline, False, _finite(base_q)
    return str(partner), True, _finite(paired_baseline_metrics(metrics, name).get("peak_q_alpha"))


def kick_clause(
    assisted: Sequence[str], sources: Mapping[str, Mapping[str, Any]], metrics: dict[str, Any]
) -> str | None:
    """Whom the free kick favours, read from the metrics: a pushed run whose peak q-alpha
    (``peak_q_alpha`` [Pa rad]) exceeds its comparison partner's is favoured by the kick
    the model leaves unpenalised; one whose peak is not above it is not. The partner is
    the run the page compares it with (``kick_partner``): the experiment baseline, or for
    a bound re-run its paired baseline, which carries the same override, worded 'its
    paired baseline pad__aero_bound's'. A run with no kick (``kicked``: a failed
    ignition), without the metric, or whose partner has no peak q-alpha is left out; None
    when nothing can be said."""
    groups: dict[tuple[str, bool], dict[str, Any]] = {}
    for name in assisted:
        m = sources[name]["metrics"]
        q = _finite(m.get("peak_q_alpha"))
        if q is None or not kicked(m):
            continue
        partner, paired, partner_q = kick_partner(name, sources[name], metrics)
        if partner_q is None:
            continue
        group = groups.setdefault((partner, paired), {"q": partner_q, "above": [], "below": []})
        (group["above"] if q > partner_q else group["below"]).append((name, q))
    if not groups:
        return None

    def names_of(items: Sequence[tuple[str, float]]) -> str:
        """The run names of (name, peak q-alpha) items, joined as a list."""
        return _names([name for name, _ in items])

    def values(items: Sequence[tuple[str, float]]) -> str:
        """The peak q-alpha values of (name, peak q-alpha) items, one decimal, as a list."""
        return _names([f"{q:.1f}" for _, q in items])

    def partner_text(partner: str, paired: bool, items: Sequence[tuple[str, float]]) -> str:
        """Whose peak the items are judged against: 'the baseline pad's' or 'its (their)
        paired baseline pad__aero_bound's'."""
        if not paired:
            return f"the baseline {partner}'s"
        return f"{'its' if len(items) == 1 else 'their'} paired baseline {partner}'s"

    pieces = []
    for (partner, paired), group in groups.items():
        above, below, partner_q = group["above"], group["below"], group["q"]
        partner_value = f"{partner_q:.1f} Pa rad"
        if above:
            pieces.append(
                f"favours {names_of(above)}, whose peak q-alpha is above "
                f"{partner_text(partner, paired, above)} ({values(above)} against {partner_value})"
            )
        if below:
            side = "below" if all(q < partner_q for _, q in below) else "not above"
            where = (
                f"it ({values(below)} Pa rad)"
                if above
                else f"{partner_text(partner, paired, below)} ({values(below)} against "
                f"{partner_value})"
            )
            pieces.append(
                f"does not favour {names_of(below)}, whose peak q-alpha is {side} {where}"
            )
    return "The free kick " + ", and ".join(pieces) + "."


def drive_caveat(
    runs: Sequence[dict[str, Any]],
    sources: Mapping[str, Mapping[str, Any]],
    metrics: dict[str, Any],
) -> str | None:
    """What the assist model leaves out (the prescribed push first, with each net
    acceleration shown and its runs, then the massless carriage, the vented shaft, and,
    for the runs that kicked, a kick without aerodynamic penalty), each naming its runs
    unless it applies to every assisted run, then what each omission does to the numbers
    shown, built from the runs shown. Under a prescribed-acceleration drive ('this drive'
    when every pushed run shown is prescribed at one acceleration, 'these prescribed
    drives' for several accelerations, else 'the prescribed drive(s) of <names>') the
    release speed, the payload (when a prescribed run has one) and the offload (when a
    prescribed run is an offload run) do not depend on the carriage mass or the shaft
    drag; there a massless carriage biases the drive energy and peak power low and a
    vented shaft's missing drag biases the drive energy, peak power and interface force
    low (RQ3-silo-screening-2d, established for the prescribed drive only: a 22 t
    carriage raises the drive force and leaves the interface force unchanged). Under any
    other drive model the same omissions change the release speed itself, so no bias
    direction is claimed: their size is said to be not established here. Then the kick
    clause of ``kick_clause``. None without an assisted run, or when nothing applies.
    ``sources``: run_source per run (its metrics give the push's net acceleration,
    ``push_accel_g``, the carriage mass, ``carriage_mass_kg``, the kick regime and the
    peak q-alpha); ``metrics``: the directory's metrics.json (the baseline's and the
    paired baselines' peak q-alpha)."""
    assisted = [r["key"] for r in runs if r["assisted"]]
    if not assisted:
        return None
    by_key = {r["key"]: r for r in runs}
    pushes: dict[float | None, list[str]] = {}
    applies: dict[str, list[str]] = {}
    prescribed: list[str] = []
    others: dict[str, list[str]] = {}
    massless: list[str] = []
    vented: list[str] = []
    omitted: dict[str, list[str]] = {}
    kicking: list[str] = []
    for name in assisted:
        assist = run_assist(sources[name]["config"])
        m = sources[name]["metrics"]
        accel = push_accel_g(assist, m)
        is_prescribed = assist.get("model") == CONSTANT_ACCEL_MODEL
        if is_prescribed:
            prescribed.append(name)
            pushes.setdefault(accel, []).append(name)
        else:
            others.setdefault(str(assist.get("model")), []).append(name)
        if carriage_mass_kg(assist, m) == 0.0:
            applies.setdefault("the carriage is massless", []).append(name)
            if is_prescribed:
                massless.append(name)
            else:
                omitted.setdefault(name, []).append("the massless carriage")
        if is_vented(assist):
            applies.setdefault("the shaft has no air drag", []).append(name)
            if is_prescribed:
                vented.append(name)
            else:
                omitted.setdefault(name, []).append("the missing shaft drag")
        if kicked(m):
            kicking.append(name)
    if kicking:
        applies["the pitch kick has no aerodynamic penalty"] = kicking
    sentences = []
    parts = []
    stated = [
        f"a prescribed {accel:g} g push with no force or power limit" + _unless_all(names, assisted)
        for accel, names in pushes.items()
        if accel is not None
    ]
    if stated:
        parts.append("the drive is " + _names(stated))
    parts += [part + _unless_all(names, assisted) for part, names in applies.items()]
    if parts:
        text = _names(parts)
        sentences.append(text[0].upper() + text[1:] + ".")
    if prescribed:
        figures = ["the release speed"]
        if any(by_key[n]["payload_kg"] is not None for n in prescribed):
            figures.append("the payload")
        if any(by_key[n]["role"] == ROLE_OFFLOAD for n in prescribed):
            figures.append("the offload")
        one_drive = len(pushes) == 1
        if prescribed == assisted:
            drive = "this drive" if one_drive else "these prescribed drives"
        else:
            drive = f"the prescribed drive{'' if one_drive else 's'} of {_names(prescribed)}"
        verb = "does" if len(figures) == 1 else "do"
        effects = (
            f"Under {drive} {_names(figures)} {verb} not depend on the carriage mass or the "
            "shaft drag"
        )
        biases = []
        if massless:
            biases.append(
                "the massless carriage biases the drive energy and peak power low"
                + _unless_all(massless, prescribed)
            )
        if vented:
            biases.append(
                "the missing shaft drag biases the drive energy, peak power and interface "
                "force low" + _unless_all(vented, prescribed)
            )
        if biases:
            effects += ": " + ", and ".join(biases)
        sentences.append(effects + ".")
    for model, names in others.items():
        left_out = [n for n in names if n in omitted]
        if not left_out:
            continue
        bits = list(dict.fromkeys(bit for n in left_out for bit in omitted[n]))
        changed = "the release speed"
        if any(by_key[n]["payload_kg"] is not None for n in left_out):
            changed += " and the payload"
        sentences.append(
            f"For {_names(left_out)} ({model} drive) {_names(bits)} "
            f"{'changes' if len(bits) == 1 else 'change'} {changed}; "
            f"{'its' if len(bits) == 1 else 'their'} size is not established here."
        )
    kick = kick_clause(assisted, sources, metrics)
    if kick is not None:
        sentences.append(kick)
    return " ".join(sentences) if sentences else None


def model_caveat(
    runs: Sequence[dict[str, Any]],
    sources: Mapping[str, Mapping[str, Any]],
    base_cfg: Mapping[str, Any],
) -> str:
    """The model sentence: planar point mass over the baseline's Earth (naming any
    selected run that flies over the other one), drag, back-pressure, guidance."""
    rotating = is_rotating(base_cfg)
    other = [r["key"] for r in runs if is_rotating(sources[r["key"]]["config"]) != rotating]
    earth = f"a {earth_text(rotating).replace('Earth', 'spherical Earth')}"
    if other:
        earth += f" ({earth_text(not rotating)} for {_names(other)})"
    return (
        f"Planar 2-D point-mass model over {earth}, with drag and back-pressure. Guidance "
        "is sweep-optimized, not optimal control, and the engines never throttle."
    )


def upper_bound_caveat(runs: Sequence[dict[str, Any]]) -> str | None:
    """The runs whose payload change is an unthrottled/unconstrained upper bound, with
    the flags metrics.json records for each (summary.UPPER_BOUND_REASONS words; runs
    with the same flags grouped); None when no selected run has one."""
    bound = [r for r in runs if r["upper_bound"]]
    if not bound:
        return None
    one = len(bound) == 1
    groups: dict[tuple[str, ...], list[str]] = {}
    for r in bound:
        groups.setdefault(tuple(r["upper_bound_reasons"]), []).append(r["key"])
    items = [
        f"{_names(names)} ({', '.join(reasons)})" if reasons else _names(names)
        for reasons, names in groups.items()
    ]
    return (
        f"The payload {'change' if one else 'changes'} of {'; '.join(items)} "
        f"{'is an upper bound' if one else 'are upper bounds'} (unthrottled and "
        "unconstrained): a max-Q or q-alpha limit, or the angle-of-attack aerodynamics "
        f"the model leaves out, would reduce {'it' if one else 'them'}."
    )


def _plural(names: Sequence[str], one: str, many: str) -> str:
    """``one`` for a single name, ``many`` otherwise."""
    return one if len(names) == 1 else many


def offload_comparison_caveat(
    runs: Sequence[dict[str, Any]],
    baseline: str,
    sources: Mapping[str, Mapping[str, Any]],
    metrics: dict[str, Any],
) -> str | None:
    """What the selected runs of the offload block measure, by kind
    (``offload_kind`` of run_source): a solved stage-1 case's recorded run and a pad
    control fly P_ref and measure propellant saved at the same payload and orbit, not a
    payload change (the control being what the baseline alone saves without a push, with
    what it found, ``pad_control_result``); a solved stage-2 or both-stage case flies
    P_ref and measures propellant the vehicle model does without, quoted net of the pad
    control as a property of the model's stage-2 sizing and guidance, not the assist's
    stage-1 headline (D-SP1-10; summary.md's basis row); a fixed case imposes its offload
    and flies its own payload capacity, a payload change at that offload; a paired pad
    (the baseline with the case's offload and no push) flies its own payload capacity
    and measures a payload change against P_ref, not propellant saved. One sentence per
    kind shown, with the runs named when more than one kind is; None without an offload
    run."""
    offload = [r["key"] for r in runs if r["role"] == ROLE_OFFLOAD]
    if not offload:
        return None
    block = _mapping(metrics.get("offload"))
    p_ref = _finite(block.get("reference_payload_kg"), PAYLOAD_DECIMALS)
    ref = f"P_ref = {p_ref:,.1f} kg" if p_ref is not None else "P_ref, the reference payload"
    cases = {str(c.get("run")): c for c in map(_mapping, block.get("cases") or [])}
    kinds: dict[str, list[str]] = {"at_ref": [], "net": [], "fixed": [], "paired": []}
    controls: list[str] = []
    for name in offload:
        kind = sources[name].get("offload_kind")
        case = cases.get(name, {})
        if kind == run_data.OFFLOAD_PAIRED_PAD:
            kinds["paired"].append(name)
        elif kind == run_data.OFFLOAD_CASE and case.get("kind") != run_data.OFFLOAD_SOLVED_KIND:
            kinds["fixed"].append(name)
        elif (
            kind == run_data.OFFLOAD_CASE
            and case.get("mode") is not None
            and case.get("mode") not in OFFLOAD_GROSS_MODES
        ):
            kinds["net"].append(name)
        else:
            kinds["at_ref"].append(name)
            if kind == run_data.OFFLOAD_PAD_CONTROL:
                controls.append(name)
    shown = {k: v for k, v in kinds.items() if v}

    def sentence(kind: str, names: Sequence[str], subject: str) -> str:
        """What the runs of one kind measure, with ``subject`` ('it', 'they' or the names)
        and the verbs agreeing with their number."""
        one = len(names) == 1
        its, s = ("its", "") if one else ("their", "s")
        if kind == "at_ref":
            return (
                f"{subject} {'flies' if one else 'fly'} {ref} and "
                f"{'measures' if one else 'measure'} propellant saved at the same payload and "
                "orbit, not a payload change (summary.md, 'Propellant saved at fixed payload', "
                "with its caveats)"
            )
        if kind == "net":
            return (
                f"{subject} {'flies' if one else 'fly'} {ref} and "
                f"{'measures' if one else 'measure'} propellant the vehicle model does "
                "without, quoted net of the pad control as a property of the model's stage-2 "
                "sizing and guidance, not the assist's stage-1 headline (summary.md, basis row, "
                "with its caveats)"
            )
        if kind == "fixed":
            return (
                f"{subject} {'imposes' if one else 'impose'} {its} offload and "
                f"{'flies' if one else 'fly'} {its} own payload capacity: {its} figure is that "
                f"payload against {ref}, a payload change at the imposed offload"
            )
        return (
            f"{subject} {'is' if one else 'are'} the paired pad{s} ({baseline} with the same "
            f"offload and no push), {'flies' if one else 'fly'} {its} own payload capacity and "
            f"{'measures' if one else 'measure'} a payload change ({its} payload against {ref}), "
            "not propellant saved"
        )

    text = (
        f"{_names(offload)} {_plural(offload, 'is a run', 'are runs')} of the offload block, "
        f"not compared with {baseline} here"
    )
    if len(shown) == 1:
        (kind, names), *_ = shown.items()
        text += ": " + sentence(kind, names, "it" if len(names) == 1 else "they") + "."
    else:
        text += ". " + " ".join(f"{sentence(k, v, _names(v))}." for k, v in shown.items())
    if controls:
        found: dict[str, str] = {}
        for name in controls:
            role = run_data.offload_role(block, name)
            result = None if role is None else pad_control_result(role[1], with_flags=False)
            if result is not None:
                found[name] = result
        if not found:
            what = ""
        elif len(controls) == 1:
            what = f": {found[controls[0]]}"
        else:
            what = ": " + _names(
                [f"{found[n]} for {n}" if n in found else f"unrecorded for {n}" for n in controls]
            )
        text += (
            f" {_names(controls)} {_plural(controls, 'is', 'are')} {baseline}'s own pad "
            f"control{_plural(controls, '', 's')} at P_ref, what the pad alone saves without a "
            f"push (summary.md, 'Pad controls'){what}."
        )
    return text


def comparison_caveats(
    runs: Sequence[dict[str, Any]],
    baseline: str,
    sources: Mapping[str, Mapping[str, Any]],
    metrics: dict[str, Any],
) -> list[str]:
    """What bound re-runs and cases are compared with: a bound re-run with its paired
    baseline (same override), a paired baseline and a case with nothing; what each run of
    the offload block measures (``offload_comparison_caveat``)."""
    out = []
    bounds = [f"{r['key']} with {r['compared_to']}" for r in runs if r["role"] == ROLE_BOUND]
    if bounds:
        out.append(
            "Bound re-runs are compared with their paired baseline, which carries the same "
            f"override, not with {baseline}: {_names(bounds)}."
        )
    for role, one_text, many_text in (
        (ROLE_CASE, "is a case with its own settings", "are cases with their own settings"),
        (
            ROLE_PAIRED_BASELINE,
            "is the paired baseline of a bound re-run",
            "are paired baselines of bound re-runs",
        ),
    ):
        names = [r["key"] for r in runs if r["role"] == role]
        if names:
            what = one_text if len(names) == 1 else many_text
            out.append(
                f"{_names(names)} {what}, not compared with {baseline}: no payload change "
                "or screening estimate is shown."
            )
    offload = offload_comparison_caveat(runs, baseline, sources, metrics)
    if offload is not None:
        out.append(offload)
    return out


def caveats(
    runs: Sequence[dict[str, Any]],
    metrics: dict[str, Any],
    sources: Mapping[str, Mapping[str, Any]],
    base_cfg: Mapping[str, Any],
    vehicle: str,
) -> list[str]:
    """The 'read before quoting' list for the selected runs, each item conditional on
    the runs, their vehicles and the experiment; EXPLORATORY_CAVEAT first for a directory
    the local app launched (``is_exploratory``), nothing extra for a recorded one."""
    baseline = str(metrics.get("baseline"))
    vehicles = list(dict.fromkeys(sources[r["key"]]["vehicle"] or vehicle for r in runs))
    out = [EXPLORATORY_CAVEAT] if is_exploratory(metrics) else []
    out += [model_caveat(runs, sources, base_cfg), *map(calibration_caveat, vehicles)]
    for item in (
        structure_caveat(runs, metrics, sources),
        drive_caveat(runs, sources, metrics),
        upper_bound_caveat(runs),
    ):
        if item is not None:
            out.append(item)
    out += comparison_caveats(runs, baseline, sources, metrics)
    yard = [r["key"] for r in runs if r["dashed"]]
    if yard:
        one = len(yard) == 1
        out.append(
            f"{_names(yard)} {'lights' if one else 'light'} stage 1 instantly (step "
            f"startup, drawn dashed): {'a yardstick' if one else 'yardsticks'}, not "
            f"{'a design' if one else 'designs'}, since no real engine reaches full "
            "thrust instantly."
        )
    for r in runs:
        if r["status"] != INSERTED:
            out.append(
                f"{r['key']} did not reach orbit (status {r['status']}): no payload "
                "capacity, payload change, screening estimate or loss budget."
            )
    return out


def closeup_notes(
    runs: Sequence[dict[str, Any]], sources: Mapping[str, Mapping[str, Any]]
) -> list[str]:
    """Sentences under the launch close-up: where each assisted group starts and how it
    leaves the track; how a held run is released; the vented shaft."""
    notes: list[str] = []
    groups: dict[tuple[Any, ...], list[str]] = {}
    for r in runs:
        if r["assisted"]:
            key = (r["start_alt_m"], r["exit_speed_mps"], r["push_s"], r["vertical"])
            groups.setdefault(key, []).append(r["key"])
    for (start, v_exit, push, vertical), names in groups.items():
        text = _names(names)
        if start is not None and start < 0.0:
            text += f" start{'s' if len(names) == 1 else ''} {abs(start):.0f} m below ground"
        else:
            text += f" start{'s' if len(names) == 1 else ''} at ground level"
        exit_at = "the silo mouth" if vertical else "the end of the track"
        if v_exit is not None and push is not None:
            leave = "leaves" if len(names) == 1 else "leave"
            text += f" and {leave} {exit_at} at {v_exit:.1f} m/s after {push:.1f} s"
        notes.append(text + ".")
    held = [r for r in runs if r["phase"] and r["phase"][0] == HOLD_KIND]
    on_pad = [r["key"] for r in held if not r["assisted"]]
    on_track = [r["key"] for r in held if r["assisted"]]
    if on_pad:
        notes.append(
            f"{_names(on_pad)} {'is' if len(on_pad) == 1 else 'are'} held down "
            "while the engines ramp up, then released at T+0."
        )
    if on_track:
        notes.append(
            f"{_names(on_track)} {'is' if len(on_track) == 1 else 'are'} held at the start "
            "of the track while the engines ramp up, then pushed."
        )
    vented = [
        r["key"]
        for r in runs
        if r["assisted"] and is_vented(run_assist(sources[r["key"]]["config"]))
    ]
    if vented:
        notes.append(
            "The shaft is treated as vented, so no air drag, dynamic pressure or Mach "
            "number is computed inside it."
        )
    return notes


def floors(runs: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Below-ground track starts drawn in the close-up: depth [m], label and whether it
    is a silo (vertical track), one per distinct depth (a silo floor or a track start;
    the first selected run at a depth names it). The page calls the ground line the
    silo mouth only when the deepest start is a silo."""
    out: dict[float, tuple[str, bool]] = {}
    for r in runs:
        start = r["start_alt_m"]
        if r["assisted"] and start is not None and start < 0.0:
            what = "silo floor" if r["vertical"] else "track start"
            out.setdefault(round(-start, 1), (f"{what}, {abs(start):.0f} m down", r["vertical"]))
    return [
        {"depth_m": d, "label": label, "vertical": vertical}
        for d, (label, vertical) in sorted(out.items())
    ]


def downrange_note(
    runs: Sequence[dict[str, Any]],
    sources: Mapping[str, Mapping[str, Any]],
    base_cfg: Mapping[str, Any],
) -> str:
    """The trajectory legend's sentence on downrange: the ground arc from the launch
    site over the Earth's surface (dynamics: R_datum (theta - omega_p t)), naming the
    Earth of the baseline and any selected run that flies over the other one."""
    rotating = is_rotating(base_cfg)
    other = [r["key"] for r in runs if is_rotating(sources[r["key"]]["config"]) != rotating]
    text = f"Downrange is the ground arc from the launch site over the {earth_text(rotating)}"
    if other:
        text += f" (the {earth_text(not rotating)} for {_names(other)})"
    return text + "."


# ------------------------------------------------------------------ data set


ROLE_LABELS = {
    ROLE_PAIRED_BASELINE: "paired baseline",
    ROLE_CASE: "case",
    ROLE_OFFLOAD: "offload",
}
"""Label suffix of a run by role (an experiment run or a bound re-run has none); a run
of the offload block takes OFFLOAD_LABELS' suffix for its kind instead when the block
names it."""
OFFLOAD_LABELS = {
    run_data.OFFLOAD_CASE: "offload",
    run_data.OFFLOAD_PAIRED_PAD: "paired pad",
    run_data.OFFLOAD_PAD_CONTROL: "pad control",
}
"""Label suffix of a run of the offload block by kind (run_data.offload_role): an
offload case's recorded run, the paired pad of a case (the baseline with the same
offload and no push, flying its own payload capacity) or a pad control."""


def run_label(name: str, role: str, baseline: bool, offload_kind: str | None = None) -> str:
    """The run's chip and table label: 'pad (baseline)', 'alt_185 (case)', 'silo',
    'silo_s1 (offload)', 'silo_s1__pad (paired pad)', 'pad__offload_stage1 (pad
    control)'. ``offload_kind``: the run_source key of a run of the offload block."""
    if baseline:
        return f"{name} (baseline)"
    suffix = ROLE_LABELS.get(role)
    if role == ROLE_OFFLOAD and offload_kind in OFFLOAD_LABELS:
        suffix = OFFLOAD_LABELS[offload_kind]
    return name if suffix is None else f"{name} ({suffix})"


def run_record(
    run_dir: Path,
    name: str,
    source: Mapping[str, Any],
    baseline_name: str,
    base_cfg: Mapping[str, Any],
    vehicle: str,
    index: int,
) -> dict[str, Any]:
    """The page record of one run: resampled series, events and headline metrics from
    its ``source`` (run_source). Changes against another run appear only for a run
    that is compared with one and reached orbit; losses only for a run that reached
    orbit (a run that fell back has no meaningful loss budget)."""
    frame = read_series(run_dir, name)
    offset_s = run_data.release_offset_s(frame)
    m, comp = source["metrics"], source["comparison"]
    assist = run_assist(source["config"])
    assisted = is_assisted(assist)
    baseline = name == baseline_name
    status = str(m.get("status", "unknown"))
    inserted = status == INSERTED
    compared = inserted and source["compared_to"] is not None
    upper_bound = compared and comp.get("payload_delta_upper_bound") is True
    max_q = _finite(m.get("max_q_pa"))
    detail = [
        source["note"],
        settings_text(source, base_cfg, vehicle),
        assist_text(assist, m),
        ignition_text(m, assisted),
    ]
    record: dict[str, Any] = {
        "key": name,
        "label": run_label(name, source["role"], baseline, source.get("offload_kind")),
        "detail": "; ".join(part for part in detail if part),
        "role": source["role"],
        "compared_to": source["compared_to"],
        "color": index,
        "dashed": is_yardstick(m),
        "baseline": baseline,
        "assisted": assisted,
        "vertical": is_vertical(assist),
        "status": status,
        "inserted": inserted,
        **run_series(frame),
        "events": run_events(run_dir / name / run_data.EVENTS_FILE, offset_s),
        "payload_kg": _finite(m.get("payload_kg"), PAYLOAD_DECIMALS),
        "payload_delta_kg": _finite(comp.get("payload_delta_kg"), PAYLOAD_DECIMALS)
        if compared
        else None,
        "ideal_screening_kg": _finite(
            comp.get("ideal_screening_payload_at_release_speed_at_pbase_kg"), PAYLOAD_DECIMALS
        )
        if compared
        else None,
        "screening_yardstick_kg": _finite(comp.get("screening_yardstick_kg"), PAYLOAD_DECIMALS)
        if compared
        else None,
        "upper_bound": upper_bound,
        "upper_bound_reasons": [w for k, w in UPPER_BOUND_REASONS if comp.get(k) is True]
        if upper_bound
        else [],
        "max_q_kpa": None if max_q is None else round(float(pa_to_kpa(max_q)), 2) + 0.0,
        "peak_g_flight": _finite(m.get("peak_felt_axial_g_flight"), 2),
        "losses_mps": {k: _finite(m.get(k), 1) if inserted else None for k in LOSS_KEYS},
        "exit_speed_mps": _finite(m.get("exit_speed_mps"), 2) if assisted else None,
        "felt_g_track": _finite(m.get("felt_g_track_peak"), 3) if assisted else None,
        "push_s": _finite(m.get("push_time_s"), 2) if assisted else None,
        "start_alt_m": _finite(m.get("track_start_altitude_m"), 1) if assisted else None,
    }
    if not assisted:
        record["pre_label"] = "Waiting on the pad"
    elif record["vertical"]:
        record["pre_label"] = "Waiting at the bottom of the shaft"
    else:
        record["pre_label"] = "Waiting at the start of the track"
    if record["phase"] and record["phase"][0] == HOLD_KIND:
        record["pre_label"] += ", engines not yet lit"
    record["end_label"] = (
        f"In orbit, {orbit_text(source['config'])}".removesuffix(" orbit")
        if inserted
        else f"Ended: {status}"
    )
    return record


def source_text(run_dir: Path) -> str:
    """The run directory as results/<experiment>/<timestamp> (POSIX), relative to the
    parent of its results tree."""
    resolved = run_dir.resolve()
    tree = run_data.results_tree(run_dir)  # the run's own tree, case-sensitive
    try:
        return resolved.relative_to(tree.parent).as_posix()
    except ValueError:
        return resolved.as_posix()


def subtitle_text(
    experiment: str,
    vehicle: str,
    orbit: str,
    baseline: str,
    records: Sequence[dict[str, Any]],
    sources: Mapping[str, Mapping[str, Any]],
) -> str:
    """The page subtitle: experiment, vehicle and orbit (naming runs that fly another
    vehicle or aim elsewhere), run count, the assisted runs and the baseline: compared
    against, by name, when it is one of the records; said to be absent, without its name,
    otherwise (design 4.3: the subtitle does not name a baseline that is not on the
    page)."""
    other_vehicle = [
        r["key"] for r in records if (sources[r["key"]]["vehicle"] or vehicle) != vehicle
    ]
    elsewhere = [r["key"] for r in records if orbit_text(sources[r["key"]]["config"]) != orbit]
    text = f"Experiment {experiment}: the {vehicle} vehicle"
    if other_vehicle:
        text += f" (another vehicle for {_names(other_vehicle)})"
    text += f" flown to a {orbit}"
    if elsewhere:
        text += f" (another orbit for {_names(elsewhere)})"
    text += f" in {len(records)} run{'s' if len(records) != 1 else ''}"
    assisted = [r["key"] for r in records if r["assisted"]]
    if assisted:
        one = len(assisted) == 1
        text += f"; {_names(assisted)} {'starts' if one else 'start'} with a ground assist"
    text += (
        ". Replay the simulated flights side by side, scrub to any moment, and compare "
        "what each run carries to orbit"
    )
    if any(r["key"] == baseline for r in records):
        return text + f" against the baseline, {baseline}."
    return text + " (the baseline is not on this page)."


def replay_data(run_dir: Path, runs: Sequence[str] | None) -> dict[str, Any]:
    """The page's data set for the selected runs of a planar results directory (see the
    module docstring); raises ReplayError for a wrong directory or run selection."""
    metrics = check_replay_run_dir(run_dir)
    names = select_runs(run_dir, runs)
    config = run_data.read_yaml(run_dir / run_data.CONFIG_FILE)
    sources = {n: run_source(metrics, config, n) for n in names}
    baseline = str(metrics.get("baseline"))
    base_cfg, _ = _entry_config(_mapping(config.get("runs")).get(baseline))
    vehicle = str(_mapping(config.get("vehicle")).get("name", "unknown vehicle"))
    records = [
        run_record(run_dir, n, sources[n], baseline, base_cfg, vehicle, k)
        for k, n in enumerate(names)
    ]
    orbit = orbit_text(base_cfg)
    experiment = str(metrics.get("experiment", run_dir.resolve().parent.name))
    git = _mapping(metrics.get("git"))
    results_notes = [
        "Payload capacity is the largest payload that still reaches the run's target orbit "
        "with zero propellant left, found by the simulator's search (sweep-optimized).",
        "Ideal screening is the rocket-equation estimate of the gain from the release "
        "speed alone, at the baseline's payload, holding every loss constant; the loss "
        "columns show where a gain beyond it comes from.",
    ]
    if any(
        r["screening_yardstick_kg"] is not None
        and r["ideal_screening_kg"] is not None
        and abs(r["screening_yardstick_kg"] - r["ideal_screening_kg"]) > YARDSTICK_SHOWN_KG
        for r in records
    ):
        results_notes.append(
            "summary.md flags a gain beyond screening against the stricter of two estimates, "
            "its screening yardstick, shown under the ideal screening where it differs."
        )
    if any(r["compared_to"] not in (None, baseline) for r in records):
        results_notes.append(f"Changes are against {baseline} unless the row names another run.")
    meta = {
        "experiment": experiment,
        "timestamp": str(metrics.get("timestamp_utc", run_dir.resolve().name)),
        "source": source_text(run_dir),
        "git": str(git.get("hash", "unknown")),
        "dirty": bool(git.get("dirty")),
        "version": __version__,
        "vehicle": vehicle,
        "baseline": baseline,
        "orbit": orbit,
        "subtitle": subtitle_text(experiment, vehicle, orbit, baseline, records, sources),
        "tags": site_tags(base_cfg),
        "closeup_notes": closeup_notes(records, sources),
        "results_notes": results_notes,
        "caveats": caveats(records, metrics, sources, base_cfg, vehicle),
        "floors": floors(records),
        "downrange_note": downrange_note(records, sources, base_cfg),
        "yardstick_shown_kg": YARDSTICK_SHOWN_KG,
    }
    return {"meta": meta, "runs": records}


# ------------------------------------------------------------------ page


def embed_json(data: dict[str, Any]) -> str:
    """``data`` as compact ASCII JSON safe inside a <script> element: no NaN or
    Infinity (ValueError otherwise) and every '<' escaped as the JSON escape \\u003c,
    so neither '</script>' nor '<!--' can appear in the data block."""
    text = json.dumps(data, separators=(",", ":"), allow_nan=False, ensure_ascii=True)
    return text.replace("<", "\\u003c")


def load_template() -> str:
    """The page template (package data launchsim/templates/replay.html)."""
    path = resources.files("launchsim").joinpath(*REPLAY_TEMPLATE)
    return path.read_text(encoding="utf-8")


def render_page(data: dict[str, Any]) -> str:
    """The HTML page with ``data`` embedded at REPLAY_DATA_TOKEN."""
    template = load_template()
    if template.count(REPLAY_DATA_TOKEN) != 1:
        raise RuntimeError(f"replay template must hold {REPLAY_DATA_TOKEN} exactly once")
    return template.replace(REPLAY_DATA_TOKEN, embed_json(data))


def default_replay_path(run_dir: Path, cwd: Path) -> Path:
    """<cwd>/<experiment>_<timestamp>_replay.html; when cwd is inside a results tree (the
    run's own or any folder named results) the file goes next to the outermost such
    tree instead (results/ is never hand-edited; run_data.default_output_path)."""
    experiment, timestamp = run_data.run_identity(run_dir)
    name = run_data.plot_stem(f"{experiment}_{timestamp}", "replay") + REPLAY_SUFFIXES[0]
    return run_data.default_output_path(run_dir, cwd, name)


def check_replay_out(out_path: Path, run_dir: Path) -> None:
    """Raise ReplayError for an output that is not .html, lies inside a results tree
    (run_data.protected_tree: the run's own or any folder named results), or whose
    folder does not exist, in that order (run_data.check_output)."""
    run_data.check_output(
        out_path,
        run_dir,
        suffixes=REPLAY_SUFFIXES,
        suffix_text=REPLAY_SUFFIXES[0],
        what="page",
        error=ReplayError,
    )


def write_replay_page(run_dir: Path, runs: Sequence[str] | None, out_path: Path) -> Path:
    """Write the replay page of the selected runs of ``run_dir`` to ``out_path`` (UTF-8)
    and return the path. Validates the directory, the runs and the output first."""
    data = replay_data(run_dir, runs)
    check_replay_out(out_path, run_dir)
    page = render_page(data)
    out_path.write_text(page, encoding="utf-8", newline="\n")
    return out_path
