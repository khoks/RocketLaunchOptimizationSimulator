"""The summary.md text of an experiment run, a sweep point and a sweep (moved from
sim.py; pure: builds strings, writes nothing). A planar_2d experiment gets
``planar_experiment_summary`` and ``planar_sweep_summary`` (PLANAR_VARIANT_ROWS, the
CALIBRATION banner or, for an app run, the exploratory banner, the guidance label
(sweep-optimized or fixed), the bounds, cases and screening lines and, with an offload
block, the section "Propellant saved at fixed payload": ``offload_section`` of the
block's plain record, with its caveats, ``offload_caveats``).

``experiment_summary`` assembles the sections in the CLAUDE.md order: the per-variant
table against the baseline (``variants_table``, rows ``variant_rows``), the sensitivity
table, the flags, the attributed assumptions and the checks (identity lines and the
release-speed bound). ``sweep_summary`` is the top-level text of a sweep and
``sweep_point_header`` names a sweep point. Numbers are SI with the unit in each row
label; cells print 6 significant digits (``_fmt``). ``sim`` re-exports every name of
the module before SP2 (the exploratory banner of SP2 step A4 is read here only).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

import pandas as pd

from launchsim import run_data
from launchsim.compare import (
    ATTRIBUTION_TERMS,
    BUG_SUSPECT,
    CD_SENSITIVITY_NOTE,
    CHECK_FAIL,
    CHECK_NA,
    CHECK_PASS,
    COMPARISON_BASIS,
    CROSS_VEHICLE_TERMS,
    GRAVITY_STEERING,
    IDENTITY_TOL_MPS,
    INSTANT_VARIANT_NAME,
    OFFLOAD_ENERGY_RATIO_LABEL,
    PAD_CONTROL_NO_BOUND,
    SCREENING_NOT_CHECKED,
    SENSITIVITY_NONE_DECLARED,
    SensitivityRow,
    _delta,
    _is_finite_number,
    _is_number,
    _is_pandas_missing,
    is_diagnostic,
    planar_comparison_basis,
)
from launchsim.config import (
    CALIBRATION_LABEL,
    EXPLORATORY_LABEL,
    OFFLOAD_GROSS_MODES,
    PLANAR_2D,
    RAMP_START_TIME,
    SEARCHED_FIGURES,
    STRUCTURE_CENTRAL_SET,
    STRUCTURE_PHYSICS_SETS,
    STRUCTURE_SET_NAMES,
    STRUCTURE_SIZING_FLOWN,
    STRUCTURE_SIZING_FULL_LOAD,
    LinearMotorConfig,
    SweepPoint,
)
from launchsim.offload import NO_OFFLOAD_STATUS
from launchsim.phases.prelude import SHAFT_FALLBACK
from launchsim.search import OK_STATUS
from launchsim.structure import (
    ENTRY_AFT_RING,
    ENTRY_THRUST_STRUCTURE,
    FLAG_RELEASE_UNLOAD,
    INTERSTAGE,
    LOAD_RING,
    SEARCH_HEADLINE,
    SET_OUTER_HIGH,
    SET_OUTER_LOW,
    SET_PHYSICS_HIGH,
    SET_PHYSICS_LOW,
    THRUST_STRUCTURE,
)
from launchsim.units import (
    j_to_mj,
    kg_to_t,
    m_to_mm,
    n_to_mn,
    pa_to_kpa,
    rad_to_deg,
    to_percent,
)

if TYPE_CHECKING:
    from launchsim.results_io import ExperimentResult, SweepResult
    from launchsim.sim import RunResult


# Summary display only (metrics.json keeps the raw numbers): a magnitude below
# DISPLAY_ZERO_ABS in the quantity's own unit prints as 0 (cos(pi/2) roundoff in a
# track-normal g, a hold-down credit of -2.5e-13 m/s), and the bound lines print an
# excess whose magnitude is below EXCESS_NOISE_MPS as 0 with the bound named, so that
# rounding noise is not read as signal.
DISPLAY_ZERO_ABS = 1e-9
EXCESS_NOISE_MPS = 1e-6
# The stage-1 startup kind that is a yardstick, not an engine (config: kind step).
STEP_STARTUP_KIND = "step"


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


# ------------------------------------------------------------------- summary text


def _fmt(value: Any) -> str:
    """A summary cell: n/a for None, NaN, inf, pd.NA and pd.NaT; a finite number to 6
    significant digits, printed as 0 when its magnitude is below DISPLAY_ZERO_ABS
    (rounding noise in the quantity's own unit; metrics.json keeps the raw value)."""
    if value is None or _is_pandas_missing(value):
        return "n/a"
    if isinstance(value, bool):
        return str(value)
    if _is_number(value):
        if not _is_finite_number(value):
            return "n/a"
        x = float(value)
        return "0" if abs(x) < DISPLAY_ZERO_ABS else f"{x:.6g}"
    return str(value)


def _signed(value: Any) -> str:
    """``_fmt`` with an explicit sign on finite numbers (for the identity lines); a
    magnitude below DISPLAY_ZERO_ABS prints as +0."""
    if not _is_finite_number(value):
        return _fmt(value)
    x = float(value)
    return "+0" if abs(x) < DISPLAY_ZERO_ABS else f"{x:+.6g}"


def _excess_text(value: Any) -> str:
    """The excess of a bound line: the signed number, or ``0 (|excess| <
    EXCESS_NOISE_MPS)`` when its magnitude is rounding noise, n/a when unavailable."""
    if not _is_finite_number(value):
        return _fmt(value)
    x = float(value)
    return f"0 (|excess| < {EXCESS_NOISE_MPS:g})" if abs(x) < EXCESS_NOISE_MPS else f"{x:+.6g}"


def _table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


# Rows of the per-variant table, in the CLAUDE.md order: (label, source, key). The
# source is "m" for a run metric, "c" for a comparison item (the baseline column reads
# "(baseline)"), "phase2" for a metric Phase 2 introduces (NOT_UNTIL_PHASE2 while
# absent), "felt" for the run-wide peak felt g with its phase and "flags" for the flag
# count. Labels carry the units. ``variant_rows`` inserts the stage-1 ignition rows
# (``ignition_rows``: keyed by the first stage's name) after the flags row and the
# before-flight pair (FLIGHT_BURN_ROWS) after the before-release pair when some run
# burned more before its flight than before its release (an extended hold).
NOT_UNTIL_PHASE2 = "n/a (Phase 2)"
type VariantRow = tuple[str, str, str]
VARIANT_ROWS: tuple[VariantRow, ...] = (
    ("status", "status", ""),
    ("flags (see Flags)", "flags", ""),
    ("speed at release [m/s]", "m", "speed_at_release_mps"),
    ("  delta vs baseline [m/s]", "c", "delta_speed_at_release_mps"),
    ("propellant burned before release [kg]", "m", "propellant_burned_before_release_kg"),
    ("  its dv_vac equivalent [m/s]", "m", "dv_vac_equiv_before_release_mps"),
    ("stage-1 burnout speed [m/s]", "m", "stage1_burnout_speed_mps"),
    ("  delta vs baseline [m/s]", "c", "stage1_burnout_speed_delta_mps"),
    ("stage-1 burnout altitude [m]", "m", "stage1_burnout_alt_m"),
    ("  delta vs baseline [m]", "c", "stage1_burnout_alt_delta_m"),
    ("identity point (stage1_burnout, or the run's end)", "c", "identity_point"),
    ("identity: delta speed there [m/s]", "c", "d_speed_mps"),
    ("  = delta speed at release [m/s]", "c", "d_speed_release_mps"),
    ("  + delta dv_vac [m/s]", "c", "d_dv_vac_mps"),
    ("  - delta gravity loss, duration part [m/s]", "c", "d_gravity_duration_mps"),
    ("  - delta gravity loss, altitude part [m/s]", "c", "d_gravity_alt_mps"),
    ("  - delta drag loss [m/s]", "c", "d_drag_mps"),
    ("  - delta steering loss [m/s]", "c", "d_steering_mps"),
    ("  - delta back-pressure loss [m/s]", "c", "d_back_pressure_mps"),
    ("  identity residual [m/s] (must be < 0.01)", "c", "identity_line_residual_mps"),
    (
        "hold-down credit vs baseline [m/s] (baseline's pre-flight burn cost minus this run's)",
        "c",
        "hold_down_credit_mps",
    ),
    (
        "  pre-flight burn cost of this run [m/s] (c ln(m0/m_flight) - g_eff dt_full)",
        "m",
        "preflight_burn_cost_mps",
    ),
    (
        f"ignition loss, integrated vs {INSTANT_VARIANT_NAME} [m/s] (same release state only)",
        "c",
        "ignition_loss_integrated_mps",
    ),
    (
        "ignition loss, constant-g formula vs an instant start at release [m/s]",
        "m",
        "ignition_loss_formula_mps",
    ),
    (
        "ideal-screening payload equivalent of the burnout speed delta [kg] "
        "(ideal rocket equation at fixed losses; not a payload result)",
        "c",
        "ideal_screening_payload_equiv_kg",
    ),
    (
        "  ideal screening at this run's speed at release [kg] (the README yardstick; "
        "same equation, not a payload result)",
        "c",
        "ideal_screening_payload_at_release_speed_kg",
    ),
    ("gravity loss [m/s]", "m", "gravity_loss_mps"),
    ("  duration part [m/s]", "m", "gravity_loss_duration_mps"),
    ("  altitude part [m/s]", "m", "gravity_loss_alt_mps"),
    ("drag loss [m/s]", "m", "drag_loss_mps"),
    ("steering loss [m/s]", "m", "steering_loss_mps"),
    ("back-pressure loss [m/s]", "m", "back_pressure_loss_mps"),
    ("dv_vac from the flight start [m/s]", "m", "dv_vac_mps"),
    ("max-Q [Pa]", "phase2", "max_q_pa"),
    ("peak felt axial g, run-wide [g0] (phase)", "felt", "peak_felt_axial_g"),
    ("  at t after release [s]", "m", "peak_felt_axial_g_t_s"),
    ("  mass there [kg]", "m", "peak_felt_axial_g_mass_kg"),
    ("peak felt g on the track [g0]", "m", "felt_g_track_peak"),
    ("  at t after release [s]", "m", "felt_g_track_peak_t_s"),
    ("  mass there [kg]", "m", "felt_g_track_peak_mass_kg"),
    ("peak felt g in flight [g0]", "m", "peak_felt_g_flight"),
    ("  at t after release [s]", "m", "peak_felt_g_flight_t_s"),
    ("  mass there [kg]", "m", "peak_felt_g_flight_mass_kg"),
    ("interface force, peak [N]", "m", "peak_interface_force_N"),
    ("interface force, minimum [N]", "m", "interface_force_min_N"),
    (
        "hold-down force m g_eff - T, minimum over the hold [N] "
        "(negative = the clamps in tension, holding the vehicle down)",
        "m",
        "hold_down_force_min_N",
    ),
    ("peak track-normal g [g0]", "m", "peak_track_normal_g"),
    ("  vehicle [g0]", "m", "track_normal_g_vehicle_peak"),
    ("  carriage [g0]", "m", "track_normal_g_carriage_peak"),
    ("assist (drive) energy [J]", "m", "assist_energy_J"),
    ("assist (drive) energy [kWh]", "m", "assist_energy_kWh"),
    ("electrical energy [J] (positive drive work / efficiency)", "m", "electrical_energy_J"),
    ("electrical energy [kWh]", "m", "electrical_energy_kWh"),
    ("peak drive power [W]", "m", "peak_drive_power_W"),
    ("braking (negative) drive power, minimum [W]", "m", "drive_power_min_W"),
    ("braking distance [m]", "m", "braking_distance_m"),
    ("facility length incl. braking [m]", "m", "facility_length_m"),
)
# Inserted after the before-release pair when some run's before-flight burn differs.
FLIGHT_BURN_ROWS: tuple[VariantRow, ...] = (
    (
        "propellant burned before the free flight (incl. a hold extension) [kg]",
        "m",
        "propellant_burned_before_flight_kg",
    ),
    ("  its dv_vac equivalent [m/s]", "m", "dv_vac_equiv_before_flight_mps"),
)
FLIGHT_BURN_AFTER_KEY = "dv_vac_equiv_before_release_mps"
# Appended to VARIANT_ROWS when any run carries the failed-ignition items.
FAILED_ROWS: tuple[VariantRow, ...] = (
    ("failed ignition: stage", "m", "failed_stage"),
    ("  apex altitude of the fall-back coast [m]", "m", "failed_apex_alt_m"),
    ("  time of that apex after release [s]", "m", "failed_t_apex_s"),
    ("  parked carriage altitude [m]", "m", "failed_carriage_alt_m"),
    ("  time the vehicle comes down to the carriage [s]", "m", "failed_t_carriage_s"),
    ("  speed there [m/s]", "m", "failed_speed_at_carriage_mps"),
    ("  return to the release altitude [s]", "m", "failed_t_return_s"),
    ("  impact speed at the ground [m/s]", "m", "failed_impact_speed_mps"),
    ("  speed at the shaft bottom [m/s] (derived)", "m", "failed_speed_at_shaft_bottom_mps"),
)


LINEAR_MOTOR_SOURCE = "linear_motor"
"""Row source of a linear-motor row (``_linear_motor_cell``: the run's metric, "none" for
an unset push setting, "-" for a run that is not a linear-motor run, n/a for a
linear-motor run with no push record)."""
LINEAR_MOTOR_MARK_KEY = "push_force_max_N"
"""The metric whose presence marks a linear-motor run (``metrics.LINEAR_MOTOR_METRICS``:
written for that drive only)."""
LINEAR_MOTOR_UNSET_KEYS: frozenset[str] = frozenset(
    {"push_accel_command_mps2", "push_stop_taper_m", "push_release_speed_mps"}
)
"""The push settings a linear-motor run may leave unset (no command under the force law,
no taper, no release speed set): their cell reads "none", not n/a."""
LINEAR_MOTOR_NOT_A_MOTOR = "-"
"""The cell of a linear-motor row in the column of a run that is not one."""
LINEAR_MOTOR_ROWS: tuple[VariantRow, ...] = (
    (
        "linear motor (SP7; '-': not a linear-motor run; n/a in every row: a linear-motor "
        "run with no push record): control law",
        LINEAR_MOTOR_SOURCE,
        "push_control_law",
    ),
    ("  force limit F_max [N]", LINEAR_MOTOR_SOURCE, "push_force_max_N"),
    (
        "  power limit P_max [W] (mechanical, at the carriage)",
        LINEAR_MOTOR_SOURCE,
        "push_power_max_W",
    ),
    (
        "  rise time t_r [s] (of the force limit, or of the acceleration command)",
        LINEAR_MOTOR_SOURCE,
        "push_rise_time_s",
    ),
    ("  corner speed P_max / F_max [m/s]", LINEAR_MOTOR_SOURCE, "push_corner_speed_mps"),
    (
        "  acceleration command a_cmd [m/s^2] (acceleration law; a cap can cut it)",
        LINEAR_MOTOR_SOURCE,
        "push_accel_command_mps2",
    ),
    ("  stop taper [m]", LINEAR_MOTOR_SOURCE, "push_stop_taper_m"),
    ("  release speed set [m/s]", LINEAR_MOTOR_SOURCE, "push_release_speed_mps"),
    (
        "  power limited (the power limit bound on the push)",
        LINEAR_MOTOR_SOURCE,
        "push_power_limited",
    ),
    (
        "  a cap bound the command (acceleration law: F_max or P_max / sdot, at some time on "
        "the push; False: no cap bound before the release, so a_cmd was held after the rise, "
        "scaled by a taper if any, when the push released after its rise; n/a under the "
        "force law and for a stalled push)",
        LINEAR_MOTOR_SOURCE,
        "push_cap_bound",
    ),
    (
        "  mean push acceleration v_exit / t_push [m/s^2] (a mean over the whole push: the "
        "rise, any capped or power-limited part and the taper included)",
        LINEAR_MOTOR_SOURCE,
        "push_accel_mean_mps2",
    ),
    (
        "  felt axial g at the end of the rise [g0] (at t_r: where the acceleration law's "
        "command plateau starts when no cap bound in the rise, else a capped value; where "
        "a cold force-law push's F_max plateau starts, held until the power limit or the "
        "taper; a hot burn moves it)",
        LINEAR_MOTOR_SOURCE,
        "push_felt_g_plateau",
    ),
    (
        "  release position along the track [m] (less than the stroke L: released before "
        "the track end)",
        LINEAR_MOTOR_SOURCE,
        "release_position_m",
    ),
    ("  release trigger (track_end or target_speed)", LINEAR_MOTOR_SOURCE, "release_trigger"),
    (
        "  electrical power peak [W] (mechanical peak / efficiency)",
        LINEAR_MOTOR_SOURCE,
        "electrical_power_peak_W",
    ),
    ("  carriage braking time [s]", LINEAR_MOTOR_SOURCE, "braking_time_s"),
    (
        "  carriage brake force [N] (m_c (a_b - g_eff sin phi); negative when a_b < g_eff "
        "sin phi: the brake then holds the carriage up)",
        LINEAR_MOTOR_SOURCE,
        "brake_force_N",
    ),
    (
        "  carriage brake energy [J] ((1/2) m_c v^2 (1 - g_eff sin phi / a_b); negative when "
        "a_b < g_eff sin phi)",
        LINEAR_MOTOR_SOURCE,
        "brake_energy_J",
    ),
)
"""The linear motor's rows (SP7 step S4a; ``metrics.LINEAR_MOTOR_METRICS`` with the
settings of KI-052), inserted after the facility-length row of the 1-D and the planar
per-variant tables only when some run of the table is a linear-motor run
(``_has_linear_motor``), so the summary of every other experiment is unchanged (the
conditional-row precedent of RAMP_START_ROWS and FAILED_ROWS)."""
LINEAR_MOTOR_AFTER_KEY = "facility_length_m"
"""The row the linear motor's rows follow."""


def _is_linear_motor_run(rr: RunResult) -> bool:
    """True when a run is a linear-motor run: its metrics carry LINEAR_MOTOR_MARK_KEY, or
    its resolved run block's assist is a LinearMotorConfig (a run whose search or guidance
    failed writes no push metrics; SP7 step S4a fix round 2)."""
    if LINEAR_MOTOR_MARK_KEY in rr.result.metrics:
        return True
    run = getattr(rr.resolved, "run", None)
    return isinstance(getattr(run, "assist", None), LinearMotorConfig)


def _has_linear_motor(runs: Mapping[str, RunResult]) -> bool:
    """True when some run is a linear-motor run (``_is_linear_motor_run``)."""
    return any(_is_linear_motor_run(rr) for rr in runs.values())


def _linear_motor_cell(m: Mapping[str, Any], key: str, motor: bool = True) -> str:
    """One linear-motor cell of a run's metrics m: LINEAR_MOTOR_NOT_A_MOTOR for a run
    that is not a linear-motor run (``motor`` False, and no LINEAR_MOTOR_MARK_KEY), n/a
    (``_fmt`` of None) for a linear-motor run whose metrics hold no push record, "none"
    for an unset push setting (LINEAR_MOTOR_UNSET_KEYS), else the metric (``_fmt``)."""
    if LINEAR_MOTOR_MARK_KEY not in m:
        return _fmt(None) if motor else LINEAR_MOTOR_NOT_A_MOTOR
    value = m.get(key)
    if value is None and key in LINEAR_MOTOR_UNSET_KEYS:
        return "none"
    return _fmt(value)


def ignition_rows(stage_name: str) -> tuple[VariantRow, ...]:
    """The rows that say how the first stage (``stage_name``) ignites: t_ign relative
    to release, the startup kind (``ignition_timing_metrics``) and its duration."""
    return (
        (
            "stage-1 ignition, t_ign relative to release [s] (negative = lit before release)",
            "m",
            f"t_ign_rel_release_s_{stage_name}",
        ),
        (
            f"stage-1 startup kind ({STEP_STARTUP_KIND} = instant full thrust: a yardstick, "
            "not achievable)",
            "m",
            f"startup_kind_{stage_name}",
        ),
        ("  its t_ramp or tau [s]", "m", f"t_startup_s_{stage_name}"),
    )


def first_stage_name(er: ExperimentResult) -> str:
    """The name of the baseline vehicle's first stage (the stage the ignition rows and
    the ignition-timing metrics are keyed by)."""
    return str(er.baseline.resolved.vehicle_dict["stages"][0]["name"])


def _flight_burn_differs(er: ExperimentResult) -> bool:
    """True when some run burned more before its free flight than before its release
    (a hold extended past t = 0), so the before-flight pair is worth its rows."""
    for rr in er.runs.values():
        m = rr.result.metrics
        before_flight = m.get("propellant_burned_before_flight_kg")
        before_release = m.get("propellant_burned_before_release_kg")
        if before_flight is None and before_release is None:
            continue  # never released nor flew: nothing to tell apart
        d = _delta(before_flight, before_release)
        if d is None or d != 0.0:
            return True
    return False


def variant_rows(er: ExperimentResult) -> tuple[VariantRow, ...]:
    """VARIANT_ROWS with the ignition rows after the flags row, the before-flight pair
    after the before-release pair when it differs for some run
    (``_flight_burn_differs``), LINEAR_MOTOR_ROWS after the facility row when some run
    is a linear-motor run (SP7 step S4a), plus FAILED_ROWS when any run carries a
    failed-ignition item."""
    rows: list[VariantRow] = []
    flight_pair = _flight_burn_differs(er)
    stage = first_stage_name(er)
    motor = _has_linear_motor(er.runs)
    for row in VARIANT_ROWS:
        rows.append(row)
        if row[1] == "flags":
            rows += ignition_rows(stage)
        elif row[2] == FLIGHT_BURN_AFTER_KEY and flight_pair:
            rows += FLIGHT_BURN_ROWS
        elif row[2] == LINEAR_MOTOR_AFTER_KEY and motor:
            rows += LINEAR_MOTOR_ROWS
    if any("failed_stage" in rr.result.metrics for rr in er.runs.values()):
        rows += FAILED_ROWS
    return tuple(rows)


def step_startup_note(runs: Mapping[str, RunResult], stage_name: str) -> str:
    """One line naming the runs whose first stage starts with a step (instant full
    thrust at ignition: a yardstick that isolates the ignition-timing loss, which no
    engine achieves), or "" when none does."""
    names = [
        name
        for name, rr in runs.items()
        if rr.result.metrics.get(f"startup_kind_{stage_name}") == STEP_STARTUP_KIND
    ]
    if not names:
        return ""
    return (
        f"Note: {', '.join(names)}: stage-1 startup kind {STEP_STARTUP_KIND} is instant full "
        "thrust at ignition, a yardstick that isolates the ignition-timing loss; no engine "
        "achieves it (unphysical), so these columns bound the others, they are not designs."
    )


def _variant_cell(er: ExperimentResult, name: str, source: str, key: str) -> str:
    """One cell of the per-variant table."""
    rr = er.runs[name]
    if source == "status":
        return rr.result.status
    if source == "flags":
        return str(len(rr.result.flags)) if rr.result.flags else "-"
    if source == "phase2":
        value = rr.result.metrics.get(key)
        return NOT_UNTIL_PHASE2 if value is None else _fmt(value)
    if source == "felt":
        value = rr.result.metrics.get(key)
        phase = rr.result.metrics.get(f"{key}_phase")
        return _fmt(value) if value is None or phase is None else f"{_fmt(value)} ({phase})"
    if source == "m":
        return _fmt(rr.result.metrics.get(key))
    if source == LINEAR_MOTOR_SOURCE:
        return _linear_motor_cell(rr.result.metrics, key, _is_linear_motor_run(rr))
    if name == er.baseline.name:
        return "(baseline)"
    return _fmt(er.comparison.get(name, {}).get(key))


def variants_table(er: ExperimentResult) -> str:
    """The per-variant table against the baseline: one row per quantity of
    ``variant_rows`` (labels with units), one column per run, the baseline first."""
    names = list(er.runs)
    header = ["quantity", *(f"{n} (baseline)" if n == er.baseline.name else n for n in names)]
    rows = [
        [label, *(_variant_cell(er, n, source, key) for n in names)]
        for label, source, key in variant_rows(er)
    ]
    return _table(header, rows)


SENSITIVITY_HEADER: tuple[str, ...] = (
    "variant",
    "parameter",
    "change",
    "value [SI] (unit in the cell)",
    "value (in the parameter's YAML units)",
    "status",
    "stage-1 burnout speed [m/s]",
    "delta vs baseline, unchanged [m/s]",
    "delta vs baseline with the same vehicle perturbation [m/s]",
    "ideal-screening payload equiv. of the unchanged delta [kg]",
    "ideal-screening payload equiv. of the same-perturbation delta [kg]",
    "exit speed [m/s]",
    "electrical energy [kWh]",
    "peak drive power [W]",
)
SENSITIVITY_CASE_COLUMNS = 3  # variant, parameter, change: the columns a C_D row keeps


def sensitivity_table(rows: Sequence[SensitivityRow], note: str = SENSITIVITY_NONE_DECLARED) -> str:
    """Markdown table of the sensitivity cases (``run_sensitivity``): the perturbed
    value in SI and as in the YAML, the headline delta of the stage-1 burnout speed
    against the unchanged baseline and against the baseline with the same vehicle
    perturbation (marked "= unchanged" for a run parameter, which leaves the baseline
    alone), the payload equivalent of both deltas (the same-perturbation one is the
    concept's benefit; the unchanged one is mostly the vehicle change), plus one C_D
    row per run that has cases, which reads CD_SENSITIVITY_NOTE in Phase 1 (no drag).
    Without any case the table is replaced by ``note``, the reason none ran."""
    if not rows:
        return note
    table_rows: list[list[str]] = []
    for row in rows:
        m = row.result.result.metrics
        same = "" if row.baseline_perturbed is not None else " (= unchanged)"
        table_rows.append(
            [
                row.of,
                row.param,
                f"{row.fraction:+.0%}",
                f"{_fmt(row.value_si)} {row.value_si_unit}",
                _fmt(row.value_yaml_units),
                row.result.result.status,
                _fmt(m.get("stage1_burnout_speed_mps")),
                _signed(row.comparison.get("stage1_burnout_speed_delta_mps")),
                _signed(row.comparison_perturbed.get("stage1_burnout_speed_delta_mps")) + same,
                _signed(row.comparison.get("ideal_screening_payload_equiv_kg")),
                _signed(row.comparison_perturbed.get("ideal_screening_payload_equiv_kg")),
                _fmt(m.get("exit_speed_mps")),
                _fmt(m.get("electrical_energy_kWh")),
                _fmt(m.get("peak_drive_power_W")),
            ]
        )
    filler = [CD_SENSITIVITY_NOTE] * (len(SENSITIVITY_HEADER) - SENSITIVITY_CASE_COLUMNS)
    for name in sorted({row.of for row in rows}):
        table_rows.append([name, "C_D", "+/-10%", *filler])
    return _table(list(SENSITIVITY_HEADER), table_rows)


NOT_A_FIGURE_OF_MERIT = (
    "not a figure of merit: the identity point is not a stage-1 burnout on both sides, "
    "so this delta speed is the difference of two exact budgets at unlike points"
)


def identity_lines(er: ExperimentResult) -> list[str]:
    """One bullet per variant spelling out its identity line against the baseline with
    the residual and whether it closes (IDENTITY_TOL_MPS). A line whose identity point
    is not ``stage1_burnout`` (a variant that never burned out, written at its end) is
    marked NOT_A_FIGURE_OF_MERIT so its delta speed is not read as a result."""
    lines: list[str] = []
    for name in er.variants:
        c = er.comparison.get(name, {})
        residual = c.get("identity_line_residual_mps")
        if residual is None:
            lines.append(f"- {name}: identity line n/a (a run without a flight budget)")
            continue
        closes = "closes" if abs(residual) < IDENTITY_TOL_MPS else "DOES NOT CLOSE"
        point = c.get("identity_point")
        note = "" if point == "stage1_burnout" else f" ({NOT_A_FIGURE_OF_MERIT})"
        lines.append(
            f"- {name}: delta speed at {point} {_signed(c.get('d_speed_mps'))}"
            f" = {_signed(c.get('d_speed_release_mps'))} (speed at release)"
            f" + {_signed(c.get('d_dv_vac_mps'))} (dv_vac)"
            f" - {_signed(c.get('d_gravity_duration_mps'))} (gravity, duration)"
            f" - {_signed(c.get('d_gravity_alt_mps'))} (gravity, altitude)"
            f" - {_signed(c.get('d_drag_mps'))} (drag)"
            f" - {_signed(c.get('d_steering_mps'))} (steering)"
            f" - {_signed(c.get('d_back_pressure_mps'))} (back-pressure)"
            f"; residual {residual:.3g} m/s: {closes} (< {IDENTITY_TOL_MPS:g} m/s){note}"
        )
    return lines if lines else ["(no variants)"]


def payload_yardstick_lines(er: ExperimentResult) -> list[str]:
    """The CLAUDE.md rule in kg: one bullet per variant whose ideal-screening payload
    equivalent exceeds the README yardstick at its release speed
    (``ideal_screening_payload_at_release_speed_kg``), naming what the extra m/s beyond
    the release speed are (the hold-down credit and the altitude term of the bound
    line), then one closing sentence. Variants at or below the yardstick, or without
    both numbers, get no bullet."""
    lines: list[str] = []
    for name in er.variants:
        c = er.comparison.get(name, {})
        equiv = c.get("ideal_screening_payload_equiv_kg")
        yardstick = c.get("ideal_screening_payload_at_release_speed_kg")
        if not (_is_finite_number(equiv) and _is_finite_number(yardstick)) or equiv <= yardstick:
            continue
        beyond = _delta(c.get("d_speed_mps"), c.get("d_speed_release_mps"))
        lines.append(
            f"- {name}: payload equivalent {_fmt(equiv)} kg exceeds the README yardstick "
            f"{_fmt(yardstick)} kg at its release speed; the {_signed(beyond)} m/s beyond the "
            f"release speed are the hold-down credit {_signed(c.get('hold_down_credit_mps'))} "
            f"and the altitude term {_signed(_delta(0.0, c.get('d_gravity_alt_mps')))} m/s "
            f"(unexplained {_excess_text(c.get('unexplained_gain_mps'))} m/s)"
        )
    if lines:
        lines.append(
            "A payload equivalent above the README yardstick at the release speed is the "
            "hold-down credit and the altitude term in kg (ideal rocket equation, both); "
            "the bound lines above say whether anything else contributed."
        )
    else:
        lines.append(
            "No variant's ideal-screening payload equivalent exceeds the README yardstick "
            "at its release speed."
        )
    return lines


def checks_section(er: ExperimentResult) -> str:
    """The Checks section: every variant's identity line, then the CLAUDE.md bound: no
    variant may gain more than its release speed + the hold-down credit + the altitude
    term unexplained (``unexplained_gain_mps`` > IDENTITY_TOL_MPS names a bug; a
    variant without a stage-1 burnout on both sides is listed as not checkable), then
    the same rule in kg (``payload_yardstick_lines``)."""
    lines = [*identity_lines(er), ""]
    over: list[str] = []
    unknown: list[str] = []
    for name in er.variants:
        c = er.comparison.get(name, {})
        excess = c.get("unexplained_gain_mps")
        if excess is None:
            unknown.append(name)
            continue
        lines.append(
            f"- {name}: gain {_signed(c.get('d_speed_mps'))} m/s against the bound "
            f"{_signed(c.get('d_speed_release_mps'))} (speed at release) "
            f"{_signed(c.get('hold_down_credit_mps'))} (hold-down credit) "
            f"{_signed(-c['d_gravity_alt_mps'])} (altitude term): excess "
            f"{_excess_text(excess)} m/s"
        )
        if excess > IDENTITY_TOL_MPS:
            over.append(f"{name} ({excess:+.6g} m/s)")
    lines.append("")
    if over:
        lines.append(
            "Variants exceeding their release speed + hold-down credit + altitude term by "
            f"more than {IDENTITY_TOL_MPS:g} m/s, which the CLAUDE.md rule treats as a bug: "
            + ", ".join(over)
        )
    else:
        lines.append(
            "No variant exceeds its release speed + hold-down credit + altitude term by "
            f"more than {IDENTITY_TOL_MPS:g} m/s."
        )
    if unknown:
        lines.append(
            "Not checkable (no stage-1 burnout on both sides, or no flight budget): "
            + ", ".join(unknown)
        )
    lines += ["", *payload_yardstick_lines(er)]
    return "\n".join(lines)


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
    """The summary.md text of an experiment run, in the CLAUDE.md order: title with the
    experiment name, timestamp and git hash; the comparison basis; the per-variant
    table against the baseline (with ``step_startup_note`` under it when a run is a
    step-thrust yardstick); the sensitivity table; the flags; the assumptions (union,
    attributed); the checks (identity lines and the release-speed bound).
    ``header_lines`` (already formatted as ``- ...`` bullets, e.g. a sweep point's axis
    values) go under the baseline line. A planar experiment gets
    ``planar_experiment_summary``."""
    if er.model == PLANAR_2D:
        return planar_experiment_summary(er, header_lines)
    runs = er.runs
    note = step_startup_note(runs, first_stage_name(er))
    return "\n".join(
        [
            f"# {er.experiment_name} ({er.timestamp_utc}, git {git_label(er.git)})",
            "",
            er.comparison_basis,
            "",
            f"- Vehicle: {er.vehicle_name}",
            f"- Baseline: {er.baseline.name}",
            *header_lines,
            provenance_lines(er.git, er.timestamp_utc),
            "",
            "## Variants against the baseline",
            "",
            variants_table(er),
            *(["", note] if note else []),
            "",
            "## Sensitivity",
            "",
            sensitivity_table(er.sensitivity, er.sensitivity_note),
            "",
            "## Flags",
            "",
            flags_section(runs),
            "",
            "## Assumptions",
            "",
            assumptions_section(runs, er.baseline.name),
            "",
            "## Checks",
            "",
            checks_section(er),
            "",
        ]
    )


def sweep_point_header(sweep_index: int, point: SweepPoint, n_points: int) -> list[str]:
    """Summary header bullets naming a sweep point: the sweep_<n> directory (1-based
    ``sweep_index``), the point's position, its parent run and its axis values."""
    values = ", ".join(f"{axis} = {value}" for axis, value in point.overrides.items())
    return [
        f"- Sweep: sweep_{sweep_index}, point {point.point_index} of {n_points} "
        f"(of {point.of}): {values}"
    ]


def sweep_summary(
    exp_name: str,
    sweeps: list[SweepResult],
    frames: list[pd.DataFrame],
    baseline: RunResult,
    git: Mapping[str, Any],
    timestamp_utc: str,
) -> str:
    """The top-level summary.md text of a sweep run. The assumptions section is the
    union over the baseline and every sweep point (attributed as sweep_<n>/run_NNNN);
    a ``step_startup_note`` names the baseline or the points that are step-thrust
    yardsticks (the axis values identify a point, so the note alone suffices)."""
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
    stage = str(baseline.resolved.vehicle_dict["stages"][0]["name"])
    note = step_startup_note(all_runs, stage)
    if note:
        parts += [note, ""]
    section = assumptions_section(all_runs, baseline.name, "all sweep points")
    parts += ["## Assumptions", "", section, ""]
    return "\n".join(parts)


# ------------------------------------------------------------------ planar summary

CALIBRATION_BANNER = (
    "> **CALIBRATION, not validation.** This experiment compares the pad's payload "
    "capacity with a published figure as a benchmark, never a target: no parameter may "
    "be tuned toward it, and a miss (high or low) is reported as it is, with the same "
    "checklist as a pass (CLAUDE.md; docs/findings/CAL-f9-leo-2d.md holds the band "
    "verdict and the checklist)."
)
"""The banner every calibration-labelled summary opens with (plan section 7)."""
EXPLORATORY_BANNER_HEAD = (
    "> **EXPLORATORY app run, not a finding.** Launched from the local app's form, not from "
    "a committed experiment file, and not pre-registered."
)
"""The first two sentences of the banner an exploratory summary opens with (D-SP2-12;
``exploratory_banner`` adds the code states and the caveats)."""
EXPLORATORY_NOT_APP_HEAD = (
    "> **EXPLORATORY run, not a finding.** Labelled exploratory but not launched from the "
    "app (no server-start record), and not pre-registered."
)
"""The head of the banner instead of EXPLORATORY_BANNER_HEAD when the git record has no
server-start state: an exploratory-labelled experiment run from the command line."""
EXPLORATORY_IMPOSED_NOT_NETTED_TEXT = (
    "An imposed stage-2 or both-stage offload is a property of the vehicle model and is not "
    "netted: it has no pad control, whatever the caveats below say of netting."
)
"""What the banner adds when an imposed case takes propellant from stage 2 (D-SP2-07)."""
EXPLORATORY_REPRODUCTION_TEXT = (
    "A run or case under a committed name (every name but silo, pad_variant, a neutral case "
    "name `silo_<tag>` such as silo_s1 or silo_fix7pct, and that case's paired pad "
    "`silo_<tag>__pad`) has that name's configuration in the experiment files at commit "
    "{commit}: a reproduction, not new evidence (the code may differ from the recorded "
    "run's)."
)
"""What the banner of an app launch adds when the app read the experiment files from a
commit (D-SP2-36; the name patterns in code spans, so that a Markdown renderer does not
take ``<tag>`` for an HTML tag; ``{commit}``, the first 12 characters of the hash under
EXPLORATORY_BASIS_COMMIT_KEY): the app keeps a committed name only for the committed
configuration (appform.build_experiment), so a kept name marks a reproduction; not said
of an exploratory run without a server-start record."""
EXPLORATORY_UNCOMMITTED_BASIS_TEXT = (
    "The experiment files were not read from a commit, so every variant and case has a "
    "neutral name and no run here is called a reproduction of a committed one."
)
"""What the banner of an app launch says instead of EXPLORATORY_REPRODUCTION_TEXT when
its git record names no commit for the experiment files (git gave none at server
start)."""
EXPLORATORY_NO_ANCHOR_TEXT = (
    "The M5 anchor check (dP* against silo_instant minus pad_instant plus the pad's "
    "pre-flight term) needs both anchor runs in one experiment; an app launch flies one "
    "variant, so M5 reads n/a."
)
"""What the banner of an app launch with a variant adds (compare.anchor_from needs both
anchor runs; the app builds at most one variant)."""
EXPLORATORY_NO_SENSITIVITY_TEXT = (
    "No sensitivity check ran: the Sensitivity section's vehicle.aero.cd_scale cases are "
    "those of the committed experiments, not of this directory."
)
"""What the banner adds when no sensitivity case and no offload sensitivity arm ran (the
app declares none): CLAUDE.md's +/-10% check of a headline number was not made here."""
EXPLORATORY_BASIS_COMMIT_KEY = "basis_commit"
"""Key of the app's git record that holds the full hash of the commit the app read the
committed experiment and vehicle files from at server start (None: not read from a
commit, so no name is committed)."""
EXPLORATORY_PUSH_CAVEAT = "no structural mass for the push"
EXPLORATORY_NO_PUSH_CAVEAT = "a pad launch (no push)"
"""The banner's push caveat: the first when a run has an assist and no run of the offload
block charges a structural mass, modelled or assumed (the app's form has no structural
switch, D-SP7-08, so an app launch without a penalty row reads so word for word), else
the second; ``exploratory_push_caveat`` words the two other branches (SP7 step S3a,
D-SP7-22): a penalty row's assumed mass (an app launch whose form adds a stage-1 dry mass
too: fix round 1, H-S3a-05, a deviation from step item 1's "keeps today's text" logged in
the SP7 phase file's section 12, item 33, since the bare sentence was false beside a
penalty row), a modelled mass."""
EXPLORATORY_SERVER_START_KEY = "server_start"
"""Key of the app's git record that holds the git state the app's server recorded once at
its start (hash, dirty, error): the commit whose code the launch imported."""
EXPLORATORY_LAUNCH_DIRTY_KEY = "launch_dirty"
"""Key of the app's git record that holds the working-tree state at launch; the record's
own ``dirty`` is true when either state is dirty (D-SP2-11)."""
EXPLORATORY_NO_GIT_HASHES = ("no-git",)
"""git_info hashes whose dirty flag means nothing (git missing or not a repository): the
banner reads their state as unknown."""


def tree_state(dirty: Any, hash_: Any = None) -> str:
    """'clean', 'dirty' or 'unknown' for a git dirty flag: 'clean' for False and 'dirty'
    for True; 'unknown' for anything that is not a boolean (None: git status failed or
    timed out; a string or a number: never read by its truth value, SP7 step S3a fix
    round 1, H-S3a-08) and for a hash in EXPLORATORY_NO_GIT_HASHES. The one rule of the
    banner, the replay page's git string (KI-036, ``replay.replay_data``), the scene's
    ``git_record`` (which writes dirty None whenever this reads unknown, the no-git hash
    included: fix round 2, N2-04) and the app's ``tree_state``."""
    if hash_ in EXPLORATORY_NO_GIT_HASHES or not isinstance(dirty, bool):
        return "unknown"
    return "dirty" if dirty else "clean"


def _imposed_lines(offload: Mapping[str, Any] | None) -> list[str]:
    """The banner's sentence on imposed offloads: EXPLORATORY_IMPOSED_NOT_NETTED_TEXT when
    an imposed (kind fixed) case of the offload record takes propellant from stage 2 (a
    mode other than OFFLOAD_GROSS_MODES); [] otherwise. Since SP7 step S3a (KI-039,
    D-SP7-23) the banner no longer says that an imposed offload is not propellant saved:
    the summary files imposed cases in their own sub-section with their own basis line
    (``offload_section``, OFFLOAD_IMPOSED_BASIS)."""
    if not offload:
        return []
    fixed = [c for c in offload.get("cases") or [] if c.get("kind") == "fixed"]
    if any(c.get("mode") not in OFFLOAD_GROSS_MODES for c in fixed):
        return [EXPLORATORY_IMPOSED_NOT_NETTED_TEXT]
    return []


def exploratory_push_caveat(offload: Mapping[str, Any] | None, pushed: Sequence[str] = ()) -> str:
    """The banner's push caveat for runs with an assist, three ways from the offload
    record's case records (SP7 step S3a, D-SP7-22; the cases and the structure payload
    cases whose run was written): a modelled structural mass when some record charges one
    (``structure_charged``), naming the runs and the Structure subsection, never "assumed",
    then what the rest of the block charges (fix round 1, H-S3a-05: the penalty rows'
    assumed stage-1 dry mass by name, and that every other case charges none) and that
    the experiment's own pushed runs ``pushed`` (the pushed runs of the banner's ``runs``
    that are no record's run; fix round 2, N2-02) charge none; an assumed penalty when
    some record is a penalty row (``assumed_penalty``), EXPLORATORY_PUSH_CAVEAT then the
    penalty rows' assumed mass by name (an app launch whose form adds a stage-1 dry mass
    reads so: fix round 1, H-S3a-05, a deviation from "keeps today's text", SP7 phase file
    section 12, item 33); else
    EXPLORATORY_PUSH_CAVEAT word for word (every other app launch: the form charges none,
    D-SP7-08). A structural record whose solve wrote no run (a search that found no x*,
    or a payload case whose P_2* search failed) is named by its case name as one that
    found no sized result (fix round 3, S3A-NUM-04: the block caveat lists it among the
    structural records, so the banner never says "no structural mass" or "every other
    case charges none" of it)."""
    every: list[Mapping[str, Any]] = []
    if offload:
        every = [
            c
            for key in ("cases", "structure_payload_cases")
            for c in offload.get(key) or []
            if isinstance(c, Mapping)
        ]
    records = [c for c in every if c.get("run")]
    modelled = [str(c.get("run")) for c in records if c.get("structure_charged") is True]
    unsized = [
        str(c.get("name")) for c in every if not c.get("run") and c.get("structure_charged") is True
    ]
    penalties = [str(c.get("run")) for c in records if c.get("assumed_penalty") is True]
    rows = "penalty row" if len(penalties) == 1 else "penalty rows"
    if modelled or unsized:
        parts = []
        if modelled:
            parts.append(
                f"a modelled structural mass for the push on {_join_names(modelled)} (a "
                "first-order station sizing, not an assumed penalty; the offload section's "
                "Structure subsection)"
            )
        if unsized:
            one = len(unsized) == 1
            parts.append(
                f"the structural {'case' if one else 'cases'} {_join_names(unsized)} "
                f"found no sized result (no run written, so no structural mass flown; the "
                "offload section's Structure subsection)"
            )
        text = "; ".join(parts)
        if penalties:
            verb = "charges" if len(penalties) == 1 else "charge"
            text += (
                f"; the {rows} {_join_names(penalties)} {verb} an assumed stage-1 dry mass "
                "(an assumption, not a sized structure)"
            )
        if len(modelled) + len(penalties) < len(records):
            text += "; every other case of the block charges none"
        own = [name for name in pushed if name not in {str(c.get("run")) for c in records}]
        if own:
            one = len(own) == 1
            text += (
                f"; the experiment's pushed {'run' if one else 'runs'} {_join_names(own)} "
                f"{'charges' if one else 'charge'} none"
            )
        return text
    if penalties:
        return (
            f"{EXPLORATORY_PUSH_CAVEAT} except the assumed stage-1 dry mass of the {rows} "
            f"{_join_names(penalties)} (an assumption, not a sized structure)"
        )
    return EXPLORATORY_PUSH_CAVEAT


def _join_names(names: Sequence[str]) -> str:
    """'a', 'a and b', 'a, b and c'."""
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + f" and {names[-1]}"


def _app_lines(git: Mapping[str, Any], runs: Mapping[str, RunResult]) -> list[str]:
    """The banner's sentences of an app launch: EXPLORATORY_REPRODUCTION_TEXT with the
    commit the experiment files were read from (``git[EXPLORATORY_BASIS_COMMIT_KEY]``),
    else EXPLORATORY_UNCOMMITTED_BASIS_TEXT; EXPLORATORY_NO_ANCHOR_TEXT when ``runs``
    holds a variant beside the baseline."""
    commit = git.get(EXPLORATORY_BASIS_COMMIT_KEY)
    if isinstance(commit, str) and commit:
        out = [EXPLORATORY_REPRODUCTION_TEXT.format(commit=commit[:12])]
    else:
        out = [EXPLORATORY_UNCOMMITTED_BASIS_TEXT]
    if len(runs) > 1:
        out.append(EXPLORATORY_NO_ANCHOR_TEXT)
    return out


def exploratory_banner(
    git: Mapping[str, Any],
    vehicle_name: str,
    runs: Mapping[str, RunResult],
    offload: Mapping[str, Any] | None = None,
    *,
    sensitivity_ran: bool = False,
) -> str:
    """The banner of an exploratory (app) summary, one blockquote line (D-SP2-12):
    EXPLORATORY_BANNER_HEAD (EXPLORATORY_NOT_APP_HEAD when the git record has no
    server-start state: not an app launch); the code states, the server-start commit with
    its state (``git[EXPLORATORY_SERVER_START_KEY]``; without it, that there is no
    server-start record) and the working tree at launch
    (``git[EXPLORATORY_LAUNCH_DIRTY_KEY]``, else ``git['dirty']``), each clean, dirty or
    unknown; then where the findings are and the run's caveats: the calibration gap of
    vehicle_name from run_data.CALIBRATION_RECORDS (or that it has none), the push caveat
    (``exploratory_push_caveat`` from the offload record and the pushed runs of ``runs``:
    no structural mass for the push, a penalty row's assumed mass, or a modelled mass with
    what the block's other cases and the experiment's pushed runs charge;
    EXPLORATORY_NO_PUSH_CAVEAT when no run of ``runs`` has an assist),
    the guidance (sweep-optimized when any of ``runs`` searched, else fixed) and
    unthrottled; EXPLORATORY_NO_SENSITIVITY_TEXT unless ``sensitivity_ran`` (a
    sensitivity case or an offload sensitivity arm ran); for an app launch (a
    server-start record) whether a committed name marks a reproduction and the M5 anchor
    check (``_app_lines``, D-SP2-36); then, when ``offload`` (the offload block's record)
    has an imposed stage-2 or both-stage case, that it is not netted (``_imposed_lines``,
    D-SP2-07; the imposed-not-saved sentence of D-SP2-27 went with KI-039, D-SP7-23)."""
    start = git.get(EXPLORATORY_SERVER_START_KEY)
    launch = tree_state(git.get(EXPLORATORY_LAUNCH_DIRTY_KEY, git.get("dirty")), git.get("hash"))
    if isinstance(start, Mapping):
        head = EXPLORATORY_BANNER_HEAD
        code = (
            f"Code: the commit imported at server start ({start.get('hash', 'no-git')}, "
            f"{tree_state(start.get('dirty'), start.get('hash'))}); working tree at launch: "
            f"{launch}."
        )
    else:
        head = EXPLORATORY_NOT_APP_HEAD
        code = f"Code: no server-start record; working tree at the run: {launch}."
    record = run_data.CALIBRATION_RECORDS.get(vehicle_name)
    if record is None:
        calibration = f"No calibration record for {vehicle_name}"
    else:
        gap = run_data.calibration_gap(record[0], record[1])
        calibration = f"Calibration {float(to_percent(gap)):+.1f}%"
    searched = any(
        rr.result.metrics.get("figure_of_merit") in SEARCHED_FIGURES for rr in runs.values()
    )
    guidance = "sweep-optimized" if searched else "fixed guidance"
    pushed = [
        name
        for name, rr in runs.items()
        if getattr(rr.resolved.run.assist, "model", OFFLOAD_NO_ASSIST_MODEL)
        != OFFLOAD_NO_ASSIST_MODEL
    ]
    push = exploratory_push_caveat(offload, pushed) if pushed else EXPLORATORY_NO_PUSH_CAVEAT
    text = (
        f"{head} {code} Do not cite; findings are in docs/findings/. "
        f"{calibration}, {push}, {guidance}, unthrottled."
    )
    sensitivity = [] if sensitivity_ran else [EXPLORATORY_NO_SENSITIVITY_TEXT]
    app = _app_lines(git, runs) if head == EXPLORATORY_BANNER_HEAD else []
    return " ".join([text, *sensitivity, *app, *_imposed_lines(offload)])


PREREGISTRATION_DIRTY_FLAG = "preregistration_dirty"
"""Marker of a calibration run whose pre-registered inputs (configs/, experiments/) were
not all committed when it ran (plan amendment 1): not a valid calibration record."""


def preregistration_lines(state: Mapping[str, Any] | None) -> list[str]:
    """Summary lines stating a calibration run's frozen-input state (plan amendment 1).

    Input: ``results_io.preregistration_state``'s record, or None (not a calibration run:
    no lines). Output: one clean line naming the inputs commit, or a blockquote that
    marks the run as not a valid calibration record (dirty inputs, or a state git could
    not establish), each followed by a blank line."""
    if state is None:
        return []
    commit = state.get("inputs_commit") or "none"
    if state.get("dirty") is None:
        return [
            f"> **{PREREGISTRATION_DIRTY_FLAG}: state unknown** (git: {state.get('error')}); "
            f"inputs commit {commit}. This run is not a valid calibration record.",
            "",
        ]
    if state["dirty"]:
        paths = ", ".join(state.get("dirty_paths") or [])
        return [
            f"> **{PREREGISTRATION_DIRTY_FLAG}**: configs/ or experiments/ differ from their "
            f"last commit {commit} ({paths}). This run is not a valid calibration record; "
            "do not write docs/findings/CAL-f9-leo-2d.md from it.",
            "",
        ]
    return [f"- Pre-registered inputs: configs/ and experiments/ clean at commit {commit}.", ""]


SWEEP_OPTIMIZED_LABEL = (
    "Guidance is sweep-optimized: every run shares the guidance parametrisation, the "
    "gamma* grid and the search budget; gamma*, the kick angle delta and the LTG pair "
    "(a, b) are solved per run. Not an optimal-control solution (Phase 5)."
)
"""The label of a planar result whose runs searched their guidance (plan decision 4)."""
FIXED_GUIDANCE_LABEL = (
    "Guidance is fixed, not sweep-optimized: every run flies the shared fixed gamma* and "
    "LTG pair (a, b) (figure_of_merit none); only the kick angle delta is solved per run. "
    "There is no payload search, so no P*, and a run can end off target."
)
"""The label of a planar result in which no run searched (figure_of_merit none)."""


def guidance_label(runs: Mapping[str, RunResult]) -> str:
    """SWEEP_OPTIMIZED_LABEL when any of the runs has a searched figure of merit
    (``figure_of_merit`` in config.SEARCHED_FIGURES), else FIXED_GUIDANCE_LABEL."""
    searched = any(
        rr.result.metrics.get("figure_of_merit") in SEARCHED_FIGURES for rr in runs.values()
    )
    return SWEEP_OPTIMIZED_LABEL if searched else FIXED_GUIDANCE_LABEL


FINDINGS_BLOCKED = (
    "Findings are blocked until these are investigated (status bug_suspect, "
    "docs/physics.md, 'Screening-beat rule (2-D)')"
)
"""What the Checks section says when a run or a comparison is bug_suspect."""
SCREENING_NOT_CHECKED_TEXT = (
    "Screening not checked (no matched-payload attribution, so no loss breakdown explains "
    "the dP*; no finding about a beat rests on it)"
)
"""What the Checks section says about comparisons with status not_checked."""
DIAGNOSTIC_TAG = " (diagnostic)"
"""Appended to a diagnostic check's name (M2 with checks.m2_role diagnostic) wherever
the summary prints its verdict: it is reported, never bug_suspect."""
DIAGNOSTIC_FAILED_TEXT = (
    "Diagnostic checks that failed (computed and reported only: they give no bug_suspect "
    "and block no finding; user decision of 2026-09-30, docs/physics.md, 'Screening-beat "
    "rule (2-D)')"
)
"""What the Checks section says about comparisons with a failed diagnostic check."""
PLANAR_DEG_SOURCE = "deg"
"""Row source of a metric stored in radians and printed in degrees (summary cells are
the one place degrees appear, with plot labels)."""
PLANAR_SCREENING_SOURCE = "screening"
"""Row source of the screening status cell (``screening_cell``: the status, with the
failed diagnostic checks in brackets)."""

PLANAR_VARIANT_ROWS: tuple[VariantRow, ...] = (
    ("status", "status", ""),
    ("search status", "m", "search_status"),
    ("run checks (closure, loss identity, insertion e)", "m", "run_checks"),
    (
        "screening status (closure, attribution, M3 to M5; M2 only when blocking; "
        "a failed diagnostic check in brackets)",
        PLANAR_SCREENING_SOURCE,
        "screening_status",
    ),
    ("flags (see Flags)", "flags", ""),
    ("payload capacity P* [kg] (sweep-optimized)", "m", "payload_kg"),
    ("  dP* vs baseline [kg]", "c", "payload_delta_kg"),
    (
        "  ideal screening at this run's release speed, at the baseline's P* [kg]",
        "c",
        "ideal_screening_payload_at_release_speed_at_pbase_kg",
    ),
    (
        "  ideal screening at this run's release speed, at the vehicle payload P0 [kg]",
        "c",
        "ideal_screening_payload_at_release_speed_kg",
    ),
    ("  screening yardstick used, the stricter of the two [kg]", "c", "screening_yardstick_kg"),
    ("    its basis", "c", "screening_yardstick_basis"),
    ("  dP* beyond the screening yardstick [kg]", "c", "payload_beyond_screening_kg"),
    ("  beats the screening yardstick", "c", "beats_screening"),
    (
        "  dP* is an unthrottled/unconstrained upper bound (max-Q, q-alpha or kick)",
        "c",
        "payload_delta_upper_bound",
    ),
    ("  payload excess P0 - P* [kg]", "m", "payload_excess_kg"),
    (
        "residual propellant at P0 [kg] (signed; negative = virtual, massless shortfall)",
        "m",
        "residual_propellant_kg",
    ),
    ("  its basis", "m", "residual_propellant_basis"),
    ("dv margin at P0 [m/s] (signed)", "m", "dv_margin_mps"),
    ("gamma*_ref, the flight-path angle at MECO [deg]", PLANAR_DEG_SOURCE, "gamma_star_rad"),
    ("kick angle delta [deg]", PLANAR_DEG_SOURCE, "delta_rad"),
    ("LTG a (tan of the initial pitch)", "m", "ltg_a"),
    ("LTG b [1/s]", "m", "ltg_b_per_s"),
    ("kick regime", "m", "kick_regime"),
    ("  |v_rel| at the kick [m/s]", "m", "speed_at_kick_mps"),
    ("  unconstrained kick (faster than checks.unconstrained_kick_mps)", "c", "unconstrained_kick"),
    ("  kick steering loss [m/s]", "m", "kick_steering_loss_mps"),
    ("speed at release [m/s]", "m", "speed_at_release_mps"),
    ("propellant burned before the flight [kg]", "m", "propellant_burned_before_flight_kg"),
    ("  its dv_vac equivalent [m/s]", "m", "dv_vac_equiv_before_flight_mps"),
    ("MECO: t after release [s]", "m", "stage1_burnout_t_s"),
    ("  altitude [m]", "m", "stage1_burnout_alt_m"),
    ("  |v_rel| [m/s]", "m", "stage1_burnout_speed_mps"),
    ("  gamma_rel [deg]", PLANAR_DEG_SOURCE, "meco_gamma_rel_rad"),
    ("  downrange [m]", "m", "meco_downrange_m"),
    ("fairing drop", "m", "fairing_drop"),
    ("  t after release [s]", "m", "fairing_t_s"),
    ("  altitude [m]", "m", "fairing_alt_m"),
    ("stage-2 end: t after release [s]", "m", "stage2_end_t_s"),
    ("  eccentricity", "m", "insertion_e"),
    ("  perigee altitude [m]", "m", "perigee_alt_m"),
    ("  apogee altitude [m]", "m", "apogee_alt_m"),
    ("gravity loss [m/s]", "m", "gravity_loss_mps"),
    ("drag loss [m/s]", "m", "drag_loss_mps"),
    ("steering loss [m/s]", "m", "steering_loss_mps"),
    ("back-pressure loss [m/s]", "m", "back_pressure_loss_mps"),
    ("dv_vac from the flight start [m/s]", "m", "dv_vac_mps"),
    ("  loss-identity residual [m/s]", "m", "identity_residual_mps"),
    ("rocket-equation closure residual [m/s]", "m", "closure_residual_mps"),
    ("  pre-flight term c1 ln(m0/m_fs) [m/s]", "m", "preflight_dv_mps"),
    ("  fairing-carry term [m/s]", "m", "fairing_carry_mps"),
    ("max-Q [Pa] (unthrottled: an upper bound)", "m", "max_q_pa"),
    ("  at t after release [s]", "m", "max_q_time_s"),
    ("  altitude [m]", "m", "max_q_alt_m"),
    ("  Mach", "m", "max_q_mach"),
    ("  above the baseline", "c", "max_q_above_baseline"),
    ("peak q-alpha [Pa rad] (alpha = psi; unconstrained)", "m", "peak_q_alpha"),
    ("  at t after release [s]", "m", "peak_q_alpha_t_s"),
    ("  above the baseline", "c", "q_alpha_above_baseline"),
    ("peak felt axial g, run-wide [g0] (phase)", "felt", "peak_felt_axial_g"),
    ("peak felt axial g in flight [g0]", "m", "peak_felt_axial_g_flight"),
    ("peak felt lateral g in flight [g0]", "m", "peak_felt_lateral_g"),
    ("peak felt g on the track [g0]", "m", "felt_g_track_peak"),
    ("interface force, peak [N]", "m", "peak_interface_force_N"),
    ("interface force, minimum [N]", "m", "interface_force_min_N"),
    ("hold-down force m g_ref - T, minimum over the hold [N]", "m", "hold_down_force_min_N"),
    ("peak track-normal g [g0]", "m", "peak_track_normal_g"),
    ("  vehicle [g0]", "m", "track_normal_g_vehicle_peak"),
    ("  carriage [g0]", "m", "track_normal_g_carriage_peak"),
    ("assist (drive) energy [J]", "m", "assist_energy_J"),
    ("assist (drive) energy [kWh]", "m", "assist_energy_kWh"),
    ("electrical energy [kWh] (positive drive work / efficiency)", "m", "electrical_energy_kWh"),
    ("peak drive power [W]", "m", "peak_drive_power_W"),
    ("braking distance [m]", "m", "braking_distance_m"),
    ("facility length incl. braking [m]", "m", "facility_length_m"),
    ("search: P2 - P1 [kg]", "m", "p2_minus_p1_kg"),
    ("  search minus final payload [kg]", "m", "search_vs_final_payload_kg"),
    ("RHS evaluations of the recorded run", "m", "nfev_total"),
)
"""Rows of the planar per-variant table (label with unit, source, key): sources as
VARIANT_ROWS plus PLANAR_DEG_SOURCE; every PLANAR_REQUIRED_METRICS key is a row.
``planar_variant_rows`` inserts the stage-1 ignition rows after the flags row."""
PLANAR_FAILED_SOURCE = "failed"
"""Row source of PLANAR_FAILED_ROWS' coast cells: the run's metric for a run with a failed
ignition (``failed_stage``), n/a for every other run, whose apex or impact (a burn's apex
inside the shaft, SP7 step S4a fix round 4, V4-2) is not the fall-back coast's."""
PLANAR_FAILED_ROWS: tuple[VariantRow, ...] = (
    ("failed ignition: stage", "m", "failed_stage"),
    ("  apex altitude of the fall-back coast [m]", PLANAR_FAILED_SOURCE, "apex_alt_m"),
    ("  time of that apex after release [s]", PLANAR_FAILED_SOURCE, "apex_t_s"),
    ("  impact time after release [s]", PLANAR_FAILED_SOURCE, "impact_t_s"),
    ("  impact speed |v_rel| at the ground [m/s]", PLANAR_FAILED_SOURCE, "impact_speed_mps"),
)
"""Appended to the planar table when any run carries a failed ignition (the planar
metric names: the highest apex and the impact of the unpowered coast; n/a for a run
without a failed ignition, PLANAR_FAILED_SOURCE)."""
PLANAR_SHAFT_IMPACT_LABEL = (
    "  impact speed |v_rel| at the ground, or inside the shaft after a fall back there "
    "(shaft_fallback flag): on the parked carriage, or at the apex (about 0) when the "
    "carriage parks above it [m/s]"
)
"""The label of PLANAR_FAILED_ROWS' impact-speed row when some run of the table fell back
inside the shaft (a ``prelude.SHAFT_FALLBACK`` flag: its impact is on the parked carriage,
the floor of the flight model there, not at the ground, or, with a carriage braking at less
than the vehicle's deceleration, at the apex; SP7 step S4a fix rounds 3 and 4, P3-M2,
H4-m2); every other table keeps the label of PLANAR_FAILED_ROWS."""


RAMP_TRIGGER_SOURCE = "ramp_trigger"
"""Row source of the ramp-start trigger cell (``_ramp_trigger_cell``: the trigger the
run's config states, ``time`` included, so a run without a recorded trace still shows
it)."""
RAMP_START_ROWS: tuple[VariantRow, ...] = (
    (
        "stage-1 ramp start: stated by (time, depth, speed, height_closed_form or height_event)",
        RAMP_TRIGGER_SOURCE,
        "",
    ),
    ("  requested depth below the track exit [m]", "m", "ramp_start_requested_depth_m"),
    ("  requested speed on the push [m/s]", "m", "ramp_start_requested_speed_mps"),
    (
        "  requested height above the track exit [m] (closed form: drag-free, constant "
        "g_eff; event: the flown coast)",
        "m",
        "ramp_start_requested_height_m",
    ),
    (
        "  converted t_ign relative to release [s] (none for height_event)",
        "m",
        "ramp_start_requested_t_s",
    ),
    ("  achieved (ignition event): t relative to release [s]", "m", "ramp_start_t_rel_release_s"),
    ("  achieved: altitude [m] (datum; negative in the shaft)", "m", "ramp_start_alt_m"),
    ("  achieved: depth below the track exit [m]", "m", "ramp_start_depth_m"),
    ("  achieved: height above the track exit [m]", "m", "ramp_start_height_m"),
    ("  achieved: speed |v_rel| [m/s]", "m", "ramp_start_speed_mps"),
    ("  achieved: phase", "m", "ramp_start_phase"),
)
"""Rows of the stage-1 ramp start (SP1 step 3; ``metrics_planar.RAMP_START_METRICS``
and ``RAMP_START_REQUEST_METRICS``), inserted after the ignition rows only when some run
of the table states its ramp start by depth, speed or height (``_states_ramp_trigger``),
so the summary of an experiment that states every ramp start by time is unchanged."""


def _states_ramp_trigger(er: ExperimentResult) -> bool:
    """True when some run of the table (baseline or variant) states its first stage's
    ramp start by depth, speed or height in its config (``IgnitionConfig.ramp_start``)."""
    stage = first_stage_name(er)
    return any(
        rr.resolved.run.ignition_for(stage).ramp_start[0] != RAMP_START_TIME
        for rr in er.runs.values()
    )


def _ramp_trigger_cell(er: ExperimentResult, name: str) -> str:
    """The trigger a run's config states for its first stage's ramp start (time, depth,
    speed, height_closed_form or height_event)."""
    return er.runs[name].resolved.run.ignition_for(first_stage_name(er)).ramp_start[0]


def planar_variant_rows(er: ExperimentResult) -> tuple[VariantRow, ...]:
    """PLANAR_VARIANT_ROWS with the stage-1 ignition rows (``ignition_rows``) after the
    flags row, followed by RAMP_START_ROWS when some run states its ramp start by depth,
    speed or height (``_states_ramp_trigger``), LINEAR_MOTOR_ROWS after the facility row
    when some run is a linear-motor run (SP7 step S4a), plus PLANAR_FAILED_ROWS when any
    run carries a failed ignition (the impact-speed row labelled PLANAR_SHAFT_IMPACT_LABEL
    when some run fell back inside the shaft, fix round 3)."""
    rows: list[VariantRow] = []
    ramp = _states_ramp_trigger(er)
    motor = _has_linear_motor(er.runs)
    for row in PLANAR_VARIANT_ROWS:
        rows.append(row)
        if row[1] == "flags":
            rows += ignition_rows(first_stage_name(er))
            if ramp:
                rows += RAMP_START_ROWS
        elif row[2] == LINEAR_MOTOR_AFTER_KEY and motor:
            rows += LINEAR_MOTOR_ROWS
    if any("failed_stage" in rr.result.metrics for rr in er.runs.values()):
        shaft = any(SHAFT_FALLBACK in str(f) for rr in er.runs.values() for f in rr.result.flags)
        rows += [
            (PLANAR_SHAFT_IMPACT_LABEL, src, key)
            if shaft and key == "impact_speed_mps"
            else (label, src, key)
            for label, src, key in PLANAR_FAILED_ROWS
        ]
    return tuple(rows)


def _planar_cell(
    runs: Mapping[str, RunResult], er: ExperimentResult, name: str, row: VariantRow
) -> str:
    """One cell of the planar per-variant table: a PLANAR_DEG_SOURCE metric in degrees,
    the PLANAR_SCREENING_SOURCE row as ``screening_cell`` ("(baseline)" for the
    baseline), the RAMP_TRIGGER_SOURCE row as ``_ramp_trigger_cell``, a
    PLANAR_FAILED_SOURCE row n/a for a run without a failed ignition (no
    ``failed_stage``; SP7 step S4a fix round 4, H4-m3) and as a plain metric otherwise,
    everything else as ``_variant_cell``."""
    _label, source, key = row
    if source == PLANAR_SCREENING_SOURCE:
        if name == er.baseline.name:
            return "(baseline)"
        return screening_cell(er.comparison.get(name, {}))
    if source == RAMP_TRIGGER_SOURCE:
        return _ramp_trigger_cell(er, name)
    if source == PLANAR_FAILED_SOURCE:
        if runs[name].result.metrics.get("failed_stage") is None:
            return _fmt(None)
        source = "m"
    if source == PLANAR_DEG_SOURCE:
        value = runs[name].result.metrics.get(key)
        return _fmt(value if not _is_finite_number(value) else float(rad_to_deg(float(value))))
    return _variant_cell(er, name, source, key)


def planar_variants_table(er: ExperimentResult) -> str:
    """The planar per-variant table against the baseline (PLANAR_VARIANT_ROWS, one
    column per run, the baseline first)."""
    runs = er.runs
    names = list(runs)
    header = ["quantity", *(f"{n} (baseline)" if n == er.baseline.name else n for n in names)]
    rows = [
        [row[0], *(_planar_cell(runs, er, n, row) for n in names)]
        for row in planar_variant_rows(er)
    ]
    return _table(header, rows)


GAMMA_SENSITIVE_TEXT = (
    "Checks whose verdict changes within the variant's gamma* +/- h (the gamma*-sensitivity "
    "step; the verdict at gamma*_ref stands as pre-registered, but the gravity and steering "
    "terms trade against each other with gamma*, so these verdicts are not robust)"
)
"""What the Checks section says about checks whose verdict is not gamma*-robust."""


def _range_text(rec: Mapping[str, Any]) -> str:
    """``; over gamma* +/- h: <lo>..<hi>, robust`` (or NOT robust) for a check record
    with a gamma*-sensitivity range, else an empty string."""
    if rec.get("gamma_robust") is None:
        return ""
    span = rec.get("value_range")
    words = "robust" if rec["gamma_robust"] else "NOT robust (the verdict changes)"
    values = "n/a" if span is None else f"{_fmt(span[0])}..{_fmt(span[1])}"
    return f"; over gamma* +/- h: {values}, {words}"


def _check_name(key: str, rec: Mapping[str, Any]) -> str:
    """The printed name of a check: closure and attribution in lower case, the mechanism
    checks upper case, with DIAGNOSTIC_TAG when the record is diagnostic."""
    name = key if key in ("closure", "attribution") else key.upper()
    return name + (DIAGNOSTIC_TAG if is_diagnostic(rec) else "")


def _check_text(key: str, rec: Mapping[str, Any]) -> str:
    """One mechanism check in words: its name (marked diagnostic when it is), its status
    and the number it turned on (with its range over gamma* +/- h when the attribution
    has neighbours)."""
    status = str(rec.get("status"))
    if key in ("m2", "m3") and rec.get("ratio") is not None:
        text = (
            f"{_check_name(key, rec)} {status} (d {_signed(rec.get('d_mps'))} m/s against the "
            "time-shift "
            f"estimate {_signed(rec.get('estimate_mps'))} m/s: ratio {_fmt(rec.get('ratio'))}"
            f"{_range_text(rec)}"
        )
        if rec.get("d_stage1_mps") is not None:
            text += (
                f"; stage 1 alone d {_signed(rec.get('d_stage1_mps'))} m/s: ratio "
                f"{_fmt(rec.get('ratio_stage1'))}, a diagnostic"
            )
        return text + ")"
    if key == "attribution" and rec.get("worst_closure_mps") is not None:
        return (
            f"attribution {status} (worst closure {rec['worst_closure_mps']:.3g} m/s, worst "
            f"identity {rec['worst_identity_mps']:.3g} m/s)"
        )
    if key == "attribution" and rec.get("reason"):
        return f"attribution {status} ({rec['reason']})"
    if key == "m4" and rec.get("share") is not None:
        return (
            f"M4 {status} (drag + steering {_signed(rec.get('drag_steer_mps'))} m/s of "
            f"{_signed(rec.get('beyond_release_mps'))} m/s beyond the release speed: share "
            f"{_fmt(rec.get('share'))}{_range_text(rec)})"
        )
    if key == "m5" and rec.get("bound_kg") is not None:
        return (
            f"M5 {status} (dP* {_signed(rec.get('d_payload_kg'))} kg against the anchor "
            f"bound {_signed(rec.get('bound_kg'))} kg)"
        )
    if key == "closure" and rec.get("worst_residual_mps") is not None:
        return f"closure {status} (worst residual {rec['worst_residual_mps']:.3g} m/s)"
    if key == "closure" and status == "n/a":
        return "closure n/a (the variant burned no stage 2)"
    return f"{_check_name(key, rec)} {status}"


CHECK_KEYS: tuple[str, ...] = ("closure", "attribution", "m2", "m3", "m4", "m5")
"""The compare_planar check records, in the order the screening line prints them."""


def _attribution_text(c: Mapping[str, Any]) -> str:
    """The matched-payload attribution in words: every term's contribution to d
    dv_margin [m/s], the residual and, when dP* is known, the kg split."""
    if c.get("attr_d_dv_margin_mps") is None:
        return "matched-payload attribution n/a (no rung-2 run at the matched payload)"
    terms = ", ".join(
        f"{t.replace('_', ' ')} {_signed(c.get(f'attr_{t}_mps'))}" for t in ATTRIBUTION_TERMS
    )
    text = (
        f"matched-payload attribution at P_ref = {_fmt(c.get('attr_payload_kg'))} kg: d dv_margin "
        f"{_signed(c.get('attr_d_dv_margin_mps'))} m/s = {terms} m/s (residual "
        f"{_fmt(c.get('attr_residual_mps'))} m/s)"
    )
    joint = f"attr_{GRAVITY_STEERING}"
    text += f"; gravity + steering together {_signed(c.get(f'{joint}_mps'))} m/s"
    if c.get("attr_release_speed_kg") is not None:
        kg = ", ".join(
            f"{t.replace('_', ' ')} {_signed(c.get(f'attr_{t}_kg'))}" for t in ATTRIBUTION_TERMS
        )
        text += (
            f"; dP* split in kg: {kg} (gravity + steering together "
            f"{_signed(c.get(f'{joint}_kg'))} kg)"
        )
    text += f". {SPLIT_CAVEAT}"
    if c.get("attr_gamma_step_rad") is not None:
        step_deg = float(rad_to_deg(float(c["attr_gamma_step_rad"])))
        rates = [
            _signed(_per_deg(c.get(f"attr_{t}_dgamma_mps_per_rad")))
            for t in ("gravity", "steering", GRAVITY_STEERING)
        ]
        text += (
            f". Over gamma* +/- {_fmt(step_deg)} deg the gravity term moves {rates[0]} m/s "
            f"per deg, the steering term {rates[1]} m/s per deg, their sum {rates[2]} m/s "
            "per deg"
        )
    return text


SPLIT_CAVEAT = (
    "The gravity and steering terms trade against each other as gamma* moves (the total "
    "is nearly stationary in gamma*), so only their sum is read as physics, never the "
    "split between them (docs/physics.md, 'Screening-beat rule (2-D)')"
)
"""The caveat printed with every matched-payload attribution."""


def _per_deg(value: Any) -> float | None:
    """A rate per rad as a rate per deg (None for a missing or non-finite value)."""
    if not _is_finite_number(value):
        return None
    return float(value) / float(rad_to_deg(1.0))


UPPER_BOUND_REASONS: tuple[tuple[str, str], ...] = (
    ("max_q_above_baseline", "max-Q above the baseline"),
    ("q_alpha_above_baseline", "q-alpha above the baseline"),
    ("unconstrained_kick", "unconstrained kick"),
)
"""The comparison flags that make a dP* an unthrottled/unconstrained upper bound, with
their words."""


def _upper_bound_text(c: Mapping[str, Any]) -> str:
    """`` (an unthrottled/unconstrained upper bound: <reasons>)`` when the comparison's
    ``payload_delta_upper_bound`` is True, else an empty string."""
    if c.get("payload_delta_upper_bound") is not True:
        return ""
    why = [words for key, words in UPPER_BOUND_REASONS if c.get(key) is True]
    return f" (an unthrottled/unconstrained upper bound: {', '.join(why)})"


def screening_lines(er: ExperimentResult) -> list[str]:
    """The screening line of every variant (CLAUDE.md: a run that beats the README's
    ideal screening estimate for its release speed must be explained by its loss
    breakdown): ``screening_line`` of each."""
    lines = [
        screening_line(
            name,
            er.comparison.get(name, {}),
            er.runs[name].result.metrics.get("speed_at_release_mps"),
        )
        for name in er.variants
    ]
    return lines if lines else ["(no variants)"]


def screening_line(name: str, c: Mapping[str, Any], v0_mps: Any) -> str:
    """The screening line of the comparison c of the run name released at v0_mps [m/s]:
    dP* against the ideal yardstick at its release speed actually used (the stricter,
    smaller one of those at P0 and at the baseline's P*, both printed), whether it beats
    it, the matched-payload attribution and the checks, ending in the screening status.
    A dP* that is an unthrottled/unconstrained upper bound (``payload_delta_upper_bound``)
    says so and why (an unconstrained kick among them)."""
    beyond = c.get("payload_beyond_screening_kg")
    verdict = (
        "n/a"
        if not _is_finite_number(beyond)
        else (
            f"beats it by {_fmt(beyond)} kg (the attribution must explain this)"
            if beyond > 0
            else f"does not beat it ({_signed(beyond)} kg)"
        )
    )
    checks = "; ".join(_check_text(k, c.get(f"checks_{k}", {})) for k in CHECK_KEYS)
    at_base = _fmt(c.get("ideal_screening_payload_at_release_speed_at_pbase_kg"))
    at_p0 = _fmt(c.get("ideal_screening_payload_at_release_speed_kg"))
    used = _fmt(c.get("screening_yardstick_kg"))
    basis = _fmt(c.get("screening_yardstick_basis"))
    return (
        f"- {name}: dP* {_signed(c.get('payload_delta_kg'))} kg{_upper_bound_text(c)} "
        f"against the ideal screening yardstick {used} kg at its release speed {_fmt(v0_mps)} "
        f"m/s (the stricter of {at_p0} kg at P0 and {at_base} kg at the baseline's P*: "
        f"{basis}): {verdict}. {_attribution_text(c)}. Checks: {checks}. Screening status: "
        f"{c.get('screening_status', 'n/a')}{_diagnostic_text(c)}"
    )


def _diagnostic_failed(c: Mapping[str, Any]) -> str:
    """The failed diagnostic checks of comparison c (``screening_diagnostic_failed``),
    upper case and comma-separated; empty when none."""
    return ", ".join(k.upper() for k in c.get("screening_diagnostic_failed") or [])


def screening_cell(c: Mapping[str, Any]) -> str:
    """A table cell of comparison c's screening status: the status, followed by
    `` (diagnostic fail: M2)`` when a diagnostic check failed (it blocks no finding, but a
    reader who stops at the table still sees it)."""
    names = _diagnostic_failed(c)
    status = _fmt(c.get("screening_status"))
    return f"{status} (diagnostic fail: {names})" if names else status


def _diagnostic_text(c: Mapping[str, Any]) -> str:
    """`` (failed diagnostic checks, which block no finding: M2)`` after a screening
    status, or an empty string when no diagnostic check failed."""
    names = _diagnostic_failed(c)
    return f" (failed diagnostic checks, which block no finding: {names})" if names else ""


def run_check_lines(runs: Mapping[str, RunResult]) -> list[str]:
    """One line per run with its per-run checks (closure and identity residuals,
    insertion e) and their verdict (``run_checks``)."""
    lines = []
    for name, rr in runs.items():
        m = rr.result.metrics
        failed = m.get("run_checks_failed")
        lines.append(
            f"- {name}: closure residual {_fmt(m.get('closure_residual_mps'))} m/s, loss-identity "
            f"residual {_fmt(m.get('identity_residual_mps'))} m/s, insertion e "
            f"{_fmt(m.get('insertion_e'))}: {m.get('run_checks', 'n/a')}"
            + (f" ({failed})" if failed else "")
        )
    return lines


def planar_checks_section(er: ExperimentResult) -> str:
    """The planar Checks section: the per-run checks, the screening line of every
    variant, then which runs block findings (bug_suspect) or that none does, and which
    comparisons carry no matched-payload attribution (not_checked: their dP* is not
    explained, so no finding about a beat rests on it). With an offload block: its runs
    (written ones, verification searches, sensitivity arms) among the per-run checks,
    the decomposition line of every case and arm (``offload_check_lines``), the
    decompositions and paired-pad comparisons among what can block findings
    (``offload_check_comparisons``) and a failing stage-1 pad control in a blocked line
    of its own (``offload_blocking_controls``); no offload row enters the unexplained
    beats."""
    runs = {**er.runs, **er.cases}
    for row in er.sensitivity:
        runs.setdefault(row.result.name, row.result)
    for bound in er.bounds:
        runs.setdefault(bound.result.name, bound.result)
        runs.setdefault(bound.baseline.name, bound.baseline)
    offload: list[tuple[str, Mapping[str, Any]]] = []
    controls: list[str] = []
    offload_lines: list[str] = []
    if er.offload is not None and not er.offload.record.get("skipped"):
        for name, rr in {**er.offload.runs, **er.offload.checked_runs}.items():
            runs.setdefault(name, rr)
        offload = offload_check_comparisons(er.offload.record)
        controls = offload_blocking_controls(er.offload.record)
        offload_lines = [*offload_check_lines(er.offload.record), ""]
    lines = [*run_check_lines(runs), "", *screening_lines(er), ""]
    extra = extra_comparisons(er)
    if extra:
        lines += [
            "Sensitivity cases and bounds against the baseline of the same vehicle (the "
            "screening-beat rule applies to them too):",
            *(_compact_screening(label, c) for label, c in extra),
            "",
        ]
    lines += offload_lines
    lines += blocked_lines(runs, [*er.comparison.items(), *extra, *offload], controls)
    unexplained = [
        label
        for label, c in [*er.comparison.items(), *extra, *unattributed_comparisons(er)]
        if c.get("screening_status") == SCREENING_NOT_CHECKED and c.get("beats_screening")
    ]
    if unexplained:
        lines.append(f"{UNEXPLAINED_BEAT_TEXT}: " + ", ".join(unexplained))
    return "\n".join(lines)


UNEXPLAINED_BEAT_TEXT = (
    "Unexplained beats (not_checked and beating the screening yardstick: no loss breakdown "
    "explains them, so they support no finding)"
)
"""What the Checks section says about not_checked comparisons that beat the yardstick."""


def extra_comparisons(er: ExperimentResult) -> list[tuple[str, Mapping[str, Any]]]:
    """The attributed comparisons of the sensitivity cases and bounds, labelled: each
    case against the baseline of the same vehicle (the same-perturbation baseline for a
    vehicle parameter, the unchanged one for a run parameter) and each bound against its
    paired baseline."""
    out: list[tuple[str, Mapping[str, Any]]] = []
    for row in er.sensitivity:
        base = "same-perturbation baseline" if row.baseline_perturbed is not None else "baseline"
        out.append(
            (f"{row.of} {row.param} {row.fraction:+.0%} vs {base}", row.comparison_perturbed)
        )
    for b in er.bounds:
        out.append((f"{b.result.name} vs {b.baseline.name}", b.comparison))
    return out


def unattributed_comparisons(er: ExperimentResult) -> list[tuple[str, Mapping[str, Any]]]:
    """The comparisons across two vehicles (never attributed): a vehicle parameter's case
    against the unchanged baseline and a bound against the unchanged baseline."""
    out: list[tuple[str, Mapping[str, Any]]] = [
        (f"{row.of} {row.param} {row.fraction:+.0%} vs baseline", row.comparison)
        for row in er.sensitivity
        if row.baseline_perturbed is not None
    ]
    out += [(f"{b.result.name} vs baseline", b.comparison_vs_nominal) for b in er.bounds]
    return out


def _compact_screening(label: str, c: Mapping[str, Any]) -> str:
    """One line per extra comparison: dP*, the yardstick used, whether it beats it, the
    failed blocking checks, the failed diagnostic checks, the gamma*-sensitive checks and
    the screening status."""
    failed = ", ".join(c.get("screening_failed") or []) or "none"
    return (
        f"- {label}: dP* {_signed(c.get('payload_delta_kg'))} kg against the yardstick "
        f"{_fmt(c.get('screening_yardstick_kg'))} kg (beats: {_fmt(c.get('beats_screening'))}); "
        f"failed checks: {failed}; failed diagnostic checks: {_diagnostic_failed(c) or 'none'}; "
        f"gamma*-sensitive: {_gamma_sensitive(c) or 'none'}; "
        f"screening status {c.get('screening_status', 'n/a')}"
    )


def _gamma_sensitive(c: Mapping[str, Any]) -> str:
    """The checks of comparison c whose verdict is not gamma*-robust, comma-separated
    (a diagnostic one marked DIAGNOSTIC_TAG)."""
    names = [
        k.upper() + (DIAGNOSTIC_TAG if is_diagnostic(c[f"checks_{k}"]) else "")
        for k in CHECK_KEYS
        if isinstance(c.get(f"checks_{k}"), Mapping)
        and c[f"checks_{k}"].get("gamma_robust") is False
    ]
    return ", ".join(names)


def blocked_lines(
    runs: Mapping[str, RunResult],
    comparisons: Sequence[tuple[str, Mapping[str, Any]]],
    controls: Sequence[str] = (),
) -> list[str]:
    """The blocked-findings line (runs and comparisons that are bug_suspect, or that none
    is: only blocking checks count), then the stage-1 pad controls that failed their
    consistency test (controls, labelled; PAD_CONTROL_BLOCKED, a line of their own: a
    solver's consistency test, neither a run nor a comparison), the comparisons with a
    failed diagnostic check (DIAGNOSTIC_FAILED_TEXT: reported, not blocking), the
    not_checked comparisons and the gamma*-sensitive verdicts."""
    lines: list[str] = []
    suspects = [n for n, rr in runs.items() if rr.result.status == BUG_SUSPECT]
    suspects += [
        f"{n} (comparison)" for n, c in comparisons if c.get("screening_status") == BUG_SUSPECT
    ]
    if suspects:
        lines.append(f"{FINDINGS_BLOCKED}: " + ", ".join(suspects))
    else:
        lines.append("No run and no comparison is bug_suspect.")
    if controls:
        lines.append(f"{PAD_CONTROL_BLOCKED}: " + ", ".join(controls))
    diagnostic = [f"{n} ({_diagnostic_failed(c)})" for n, c in comparisons if _diagnostic_failed(c)]
    if diagnostic:
        lines.append(f"{DIAGNOSTIC_FAILED_TEXT}: " + ", ".join(diagnostic))
    unchecked = [n for n, c in comparisons if c.get("screening_status") == SCREENING_NOT_CHECKED]
    if unchecked:
        lines.append(f"{SCREENING_NOT_CHECKED_TEXT}: " + ", ".join(unchecked))
    sensitive = [f"{n} ({_gamma_sensitive(c)})" for n, c in comparisons if _gamma_sensitive(c)]
    if sensitive:
        lines.append(f"{GAMMA_SENSITIVE_TEXT}: " + ", ".join(sensitive))
    return lines


PLANAR_SENSITIVITY_HEADER: tuple[str, ...] = (
    "variant",
    "parameter",
    "change",
    "value [SI] (unit in the cell)",
    "value (in the parameter's YAML units)",
    "status",
    "P* [kg]",
    "dP* vs baseline, unchanged [kg]",
    "dP* vs baseline with the same vehicle perturbation [kg]",
    "trajectory reused (energy-only or yardstick case)",
    "beats the screening yardstick (vs the baseline of the same vehicle)",
    "screening status (vs the baseline of the same vehicle)",
    "electrical energy [kWh]",
    "peak drive power [W]",
)
"""Columns of the planar sensitivity table (drag is modelled: C_D is a case, no filler
row)."""


def planar_sensitivity_table(rows: Sequence[SensitivityRow], note: str) -> str:
    """Markdown table of the planar sensitivity cases: the perturbed value in SI and as
    in the YAML, P* and dP* against the unchanged baseline and against the baseline with
    the same vehicle perturbation (``= unchanged`` for a run parameter), whether the
    trajectory was reused; ``note`` when no case ran."""
    if not rows:
        return note
    table_rows = []
    for row in rows:
        m = row.result.result.metrics
        same = "" if row.baseline_perturbed is not None else " (= unchanged)"
        table_rows.append(
            [
                row.of,
                row.param,
                f"{row.fraction:+.0%}",
                f"{_fmt(row.value_si)} {row.value_si_unit}",
                _fmt(row.value_yaml_units),
                row.result.result.status,
                _fmt(m.get("payload_kg")),
                _signed(row.comparison.get("payload_delta_kg")),
                _signed(row.comparison_perturbed.get("payload_delta_kg")) + same,
                "yes" if m.get("trajectory_reused") else "no",
                _fmt(row.comparison_perturbed.get("beats_screening")),
                screening_cell(row.comparison_perturbed),
                _fmt(m.get("electrical_energy_kWh")),
                _fmt(m.get("peak_drive_power_W")),
            ]
        )
    return _table(list(PLANAR_SENSITIVITY_HEADER), table_rows)


def bounds_section(er: ExperimentResult) -> str:
    """The bounds table (amendment 6): each bound run against its paired baseline (the
    baseline re-run with the same overrides) and against the unchanged baseline."""
    if not er.bounds:
        return "(no bounds declared)"
    header = [
        "bound",
        "run",
        "overrides",
        "status",
        "P* [kg]",
        "paired baseline P* [kg]",
        "dP* vs paired baseline [kg]",
        "dP* vs baseline [kg]",
        "max-Q [Pa]",
        "beats the screening yardstick (vs paired baseline)",
        "screening status (vs paired baseline)",
    ]
    rows = []
    for row in er.bounds:
        overrides = ", ".join(f"{k} = {v}" for k, v in row.overrides.items())
        rows.append(
            [
                row.bound,
                row.result.name,
                overrides,
                row.result.result.status,
                _fmt(row.result.result.metrics.get("payload_kg")),
                _fmt(row.baseline.result.metrics.get("payload_kg")),
                _signed(row.comparison.get("payload_delta_kg")),
                _signed(row.comparison_vs_nominal.get("payload_delta_kg")),
                _fmt(row.result.result.metrics.get("max_q_pa")),
                _fmt(row.comparison.get("beats_screening")),
                screening_cell(row.comparison),
            ]
        )
    return _table(header, rows)


def cases_section(er: ExperimentResult) -> str:
    """The calibration cases: independent runs, never compared with the baseline or
    with each other (plan section 7)."""
    if not er.cases:
        return "(no cases declared)"
    header = [
        "case",
        "status",
        "search status",
        "P* [kg]",
        "gamma*_ref [deg]",
        "MECO t [s]",
        "MECO altitude [m]",
        "fairing altitude [m]",
        "max-Q [Pa]",
    ]
    rows = []
    for name, rr in er.cases.items():
        m = rr.result.metrics
        g = m.get("gamma_star_rad")
        rows.append(
            [
                name,
                rr.result.status,
                _fmt(m.get("search_status")),
                _fmt(m.get("payload_kg")),
                _fmt(None if not _is_finite_number(g) else float(rad_to_deg(float(g)))),
                _fmt(m.get("stage1_burnout_t_s")),
                _fmt(m.get("stage1_burnout_alt_m")),
                _fmt(m.get("fairing_alt_m")),
                _fmt(m.get("max_q_pa")),
            ]
        )
    note = "Independent runs: never compared with the baseline or with each other."
    return note + "\n\n" + _table(header, rows)


# ------------------------------------------------- propellant saved (offload, SP1 step 7)

OFFLOAD_SECTION_NAME = "Propellant saved at fixed payload"
"""Name of the summary section of an experiment's offload block (the payload Sensitivity
note points to it: ``results_io.planar_sensitivity_note``)."""
OFFLOAD_SECTION_TITLE = f"## {OFFLOAD_SECTION_NAME}"
"""Title of the summary section of an experiment's offload block."""
OFFLOAD_FIXED_KIND = "fixed"
"""The ``kind`` of an imposed (fixed) case's record (results_io's case record; the solved
kind is run_data.OFFLOAD_SOLVED_KIND)."""
OFFLOAD_IMPOSED_SUBSECTION_TITLE = "### Imposed offloads (fixed cases)"
"""The sub-section of the offload section that holds the imposed (fixed) cases (KI-039,
D-SP7-23, SP7 step S3a): the section's heading and basis line describe the solved cases,
which fly P_ref; an imposed case flies its own payload capacity P*."""
OFFLOAD_IMPOSED_BASIS = (
    "Imposed basis: each imposed case flies its own payload capacity P*, read as P* - P_ref "
    "(positive: it carries more than the pad, so the imposed offload is not the largest "
    "possible; negative: a payload loss at that offload); an imposed offload is never "
    "propellant saved at P_ref"
)
"""The one-line basis of the imposed sub-section (KI-039), printed above its table."""
OFFLOAD_NOT_RUN_LEAD = "Cases that did not run (solved or imposed):"
"""The line before the cases that did not run when the block also has imposed cases (fix
round 3, H-S3a-P3-06 and S3A-CMP3-01): the list sits above the imposed sub-section, so it
says that it covers both kinds (a skipped case's record names no kind)."""
OFFLOAD_ENERGY_BOTH_TABLES = (
    "The note covers the energy rows of the solved table above and of the imposed cases' "
    "table below."
)
"""What the energy note adds when the block has both solved and imposed cases that ran
(fix round 3, H-S3a-P3-06, S3A-CMP3-01 and S3A-NUM-02): the note is printed before the
imposed sub-section, so a Markdown reader never takes it for that sub-section's alone."""
OFFLOAD_ENERGY_IMPOSED_TABLE = "The note covers the energy rows of the imposed cases' table below."
"""What the energy note adds in place of OFFLOAD_ENERGY_BOTH_TABLES when every case that
ran is imposed (final clean-up, N3a-04): the section then prints OFFLOAD_NO_SOLVED_CASE,
not a solved table, so the note names the imposed cases' table alone."""
OFFLOAD_NO_SOLVED_CASE = "(no solved case ran; the imposed cases are in their sub-section below)"
"""What the offload section prints in place of the solved cases table when every case
that ran is imposed."""
OFFLOAD_MODEL_READING = (
    "read every offload as a difference between runs of the vehicle model, not as a Falcon 9 figure"
)
"""How every offload is read, closing the calibration caveat (``offload_calibration_caveat``)."""
OFFLOAD_CAVEATS: tuple[str, ...] = (
    "guidance is sweep-optimized (a shared gamma* grid refined per run, not optimal "
    "control) and the engines never throttle",
    "no structural mass is charged for the push load (the fully fuelled stack rides the "
    "push at the net acceleration plus g); the penalty rows add an assumed stage-1 dry "
    "mass, a parametric assumption, not a sized structure",
    "the drive is a prescribed constant acceleration with no force or power limit, the "
    "carriage is massless unless the variant states a carriage mass, and the shaft is "
    "vented (no air drag in it)",
    "max-Q of each offloaded run is reported beside the pad's: a lighter stack climbs "
    "faster, and no max-Q limit constrains it (there is no throttle model)",
    "the tanks are partly filled: dry masses and tank structure unchanged, the mixture "
    "ratio kept, no ullage, centre-of-gravity or tank-mass effect",
    "stage 1 is the headline: stage-2 and both-stage offloads are a property of the "
    "vehicle model (stage-2 propellant is worth about nothing at the margin on the gate "
    "vehicle), quoted net of the pad control (the gross rows beside them are not a "
    "saving of the assist); a stage-1-only offload is not assumed to maximise the total "
    "tonnes ('both' may remove more, its stage-2 share riding about free), and stage 1 "
    "stays the only headline either way",
)
"""The vehicle-independent caveats printed with every offload block (phase file SP1,
step 7 and section 10): guidance, structural mass, the drive model, max-Q, the tanks,
and the stage-2 reading. ``offload_caveats`` puts the vehicle's calibration caveat
first. The stage-2 reading says that stage-2 propellant's marginal value was measured on
the gate vehicle (docs/physics.md, "Virtual propellant") and, since SP1 step 8a, no
longer that a stage-1-only offload maximises the total tonnes, which that measurement
does not support (phase file section 5.3, corrected in step 8; pre-registration section
7 tests it)."""


def offload_calibration_caveat(
    vehicle_name: str, calibration: tuple[float, float, str] | None
) -> str:
    """The calibration caveat of an offload block on vehicle_name: from its calibration
    record (``plots.CALIBRATION_RECORDS``: the model's calibration P* [kg], the
    published reference [kg] and the findings note), the gap in percent; without a
    record, that the vehicle has none on file. Either way closed by
    OFFLOAD_MODEL_READING."""
    if calibration is None:
        return (
            f"calibration: the vehicle {vehicle_name} has no calibration record on file; "
            f"{OFFLOAD_MODEL_READING}"
        )
    model_kg, reference_kg, note = calibration
    gap_pct = float(to_percent(model_kg / reference_kg - 1.0))
    side = "high" if gap_pct >= 0.0 else "low"
    return (
        f"calibration: the vehicle {vehicle_name} carries {model_kg:,.0f} kg in its "
        f"calibration run against the published {reference_kg:,.0f} kg, {gap_pct:+.1f}% "
        f"{side}, a documented calibration result ({note}); {OFFLOAD_MODEL_READING}"
    )


OFFLOAD_STRUCTURE_CAVEAT_INDEX = 1
OFFLOAD_DRIVE_CAVEAT_INDEX = 2
OFFLOAD_TANKS_CAVEAT_INDEX = 4
"""Where the structure, drive and tanks items sit in OFFLOAD_CAVEATS (the items
``offload_caveats`` words from the block's records, SP7 step S3a)."""
OFFLOAD_STRUCTURE_UNCHARGED_TEXT = (
    "each stack rides the push at the net acceleration plus g with no structural mass for it"
)
"""What the structure item of a block with structural runs says of the cases that charge
none (named; fix round 2, H-S3a-P2-06: only when there are any)."""
OFFLOAD_STRUCTURE_PENALTY_TEXT = (
    "an assumed stage-1 dry mass, a parametric assumption, not a sized structure"
)
"""What the structure item of a block with structural runs says the penalty rows add
(named; only when there are any), in SP1's words."""
OFFLOAD_TANKS_STRUCTURE_CAVEAT = (
    "the tanks are partly filled: dry masses and tank structure unchanged except for the "
    "modelled structural increment of the push load the structural cases carry (the "
    "Structure subsection), the mixture ratio kept, no ullage, centre-of-gravity or "
    "tank-mass effect"
)
OFFLOAD_TANKS_STRUCTURE_PENALTY_CAVEAT = (
    "the tanks are partly filled: dry masses and tank structure unchanged except for the "
    "penalty rows' assumed stage-1 dry mass and the modelled structural increment of the "
    "push load the structural cases carry (the Structure subsection), the mixture ratio "
    "kept, no ullage, centre-of-gravity or tank-mass effect"
)
"""The tanks item of a block with structural runs (in place of OFFLOAD_CAVEATS' tanks
item, whose "dry masses and tank structure unchanged" would be false of them): the first
without a penalty row, the second with one (fix round 2, H-S3a-P2-06: both exceptions,
as compare.OFFLOAD_COMPARISON_BASIS names them)."""
OFFLOAD_PRESCRIBED_DRIVE = "constant_accel"
"""The assist model OFFLOAD_CAVEATS' drive item describes (a prescribed constant
acceleration); ``offload_drive_caveat`` words any other drive from its model name."""
OFFLOAD_NO_ASSIST_MODEL = "none"
"""The assist model of a variant without a push (config.NoAssistConfig): an offload case
of such a variant rides no drive, and the drive item says so (SP7 step S3a fix round 1,
S3A-R1-02) instead of calling "none" a drive."""
OFFLOAD_STRUCTURE_CASES_POINTER = (
    "the Structure subsection gives each case's and payload case's layer and set, file, "
    "band and flags"
)
OFFLOAD_STRUCTURE_ARMS_POINTER = (
    "the arms table, its structural columns and its caveat give each arm's dm, set and envelope pad"
)
"""Where the rest of a structural record's sizing is reported, by record kind (fix round
1, H-S3a-04): a case or payload case in the Structure subsection, a sensitivity arm in
the arms table (which has no layer label, file, band or flags per arm)."""


def _is_arm_record(record: Mapping[str, Any]) -> bool:
    """Whether a structural record is a sensitivity arm's (results_io's
    ``_offload_arm_record``: it names its ``case`` and its perturbed ``param``)."""
    return "param" in record and "case" in record


def _structure_caveat_entry(record: Mapping[str, Any]) -> str:
    """One structural case's or payload case's entry in the block's structure item: its
    run (or case) name, its modelled mass by stage (``modelled_mass_text``), its layer and
    set (``structure_layer_label``: a design-axis row names its axes, so two rows on one
    set never read alike), then '(plausibility-scaled, x<factor>)' when the rule scaled
    its dm and '(at x = 0: the solve found no offload)' for a no_offload end (fix round 2,
    H-S3a-P2-05)."""
    name = record.get("run") or record.get("name")
    text = f"{name}: {modelled_mass_text(record)}, layer and set {structure_layer_label(record)}"
    if record.get("structure_plausibility_scaled"):
        factor = record.get("structure_plausibility_factor")
        shown = _fmt(factor) if _is_finite_number(factor) else "n/a"
        text += f" (plausibility-scaled, x{shown})"
    if record.get("status") == NO_OFFLOAD_STATUS:
        text += " (at x = 0: the solve found no offload)"
    return text


def offload_structure_caveat(
    structural: Sequence[Mapping[str, Any]],
    *,
    penalties: Sequence[str] = (),
    uncharged: Sequence[str] = (),
) -> str:
    """The structure item of a block some of whose records charge a modelled structural
    mass (SP7 step S3a, D-SP7-22): the model named, where the rest of each record's sizing
    is reported by record kind (OFFLOAD_STRUCTURE_CASES_POINTER for the cases and payload
    cases, OFFLOAD_STRUCTURE_ARMS_POINTER for the arms; only the kinds present), that it is
    a first-order estimate with its stated ranges, not a detailed structural design; each
    structural case's and payload case's entry (``_structure_caveat_entry``: the mass by
    stage, the layer and set, a plausibility scaling, a no_offload end; a sweep point's
    case record is named by its case name); the sensitivity arms by count and case only
    (their dm and its caveat on the dry-mass arm are the arms table's, fix round 2,
    H-S3a-P2-05); then, from the block's records (fix round 2, H-S3a-P2-06), the
    ``uncharged`` cases by name with OFFLOAD_STRUCTURE_UNCHARGED_TEXT and the
    ``penalties`` (penalty rows) by name with OFFLOAD_STRUCTURE_PENALTY_TEXT, each only
    when there are any. Never "assumed" of the modelled mass."""
    named = [c for c in structural if not _is_arm_record(c)]
    arms = [c for c in structural if _is_arm_record(c)]
    pointers = []
    if named:
        pointers.append(OFFLOAD_STRUCTURE_CASES_POINTER)
    if arms:
        pointers.append(OFFLOAD_STRUCTURE_ARMS_POINTER)
    who = "the structural cases" if named else "the structural sensitivity arms"
    text = (
        f"{who} charge the modelled structural mass of the push load on their assisted "
        f"runs, {STRUCTURE_MODEL_NAME} ({STRUCTURE_ESTIMATE_TEXT}; " + "; ".join(pointers) + ")"
    )
    parts = [_structure_caveat_entry(c) for c in named]
    if arms:
        of = _join_names(list(dict.fromkeys(str(a.get("case")) for a in arms)))
        many = len(arms) > 1
        parts.append(f"{len(arms)} structural sensitivity arm{'s' if many else ''} of {of}")
    text += ": " + "; ".join(parts)
    if uncharged:
        verb = "charges" if len(uncharged) == 1 else "charge"
        text += f"; {_join_names(uncharged)} {verb} none ({OFFLOAD_STRUCTURE_UNCHARGED_TEXT})"
    if penalties:
        rows = "penalty row" if len(penalties) == 1 else "penalty rows"
        verb = "adds" if len(penalties) == 1 else "add"
        text += f"; the {rows} {_join_names(penalties)} {verb} {OFFLOAD_STRUCTURE_PENALTY_TEXT}"
    return text


def offload_drive_caveat(drives: Mapping[str, str]) -> str:
    """The drive item of a block from each case's assist model (``drives``: case name to
    model; SP7 step S3a, "by drive"): OFFLOAD_CAVEATS' drive item word for word when every
    case rides OFFLOAD_PRESCRIBED_DRIVE (or none is given); otherwise one clause per other
    model naming its cases, saying that its force and power limits, carriage and shaft are
    the variant's own settings (resolved_config.yaml records them), one for the cases of
    a variant without a push (OFFLOAD_NO_ASSIST_MODEL: they fly without a push, no
    drive; fix round 1), and the prescribed item for the constant_accel cases when there
    are any."""
    prescribed = OFFLOAD_CAVEATS[OFFLOAD_DRIVE_CAVEAT_INDEX]
    others: dict[str, list[str]] = {}
    unpushed: list[str] = []
    for name, model in drives.items():
        if model == OFFLOAD_NO_ASSIST_MODEL:
            unpushed.append(name)
        elif model != OFFLOAD_PRESCRIBED_DRIVE:
            others.setdefault(str(model), []).append(name)
    if not others and not unpushed:
        return prescribed
    clauses = [
        f"the drive of {_join_names(names)} is the {model} drive of the variant (its force "
        "and power limits, carriage and shaft are the variant's own settings, recorded in "
        "resolved_config.yaml)"
        for model, names in others.items()
    ]
    if unpushed:
        one = len(unpushed) == 1
        clauses.append(
            f"{_join_names(unpushed)} {'flies' if one else 'fly'} without a push (assist "
            f"{OFFLOAD_NO_ASSIST_MODEL}: no drive)"
        )
    rest = [n for n, m in drives.items() if m == OFFLOAD_PRESCRIBED_DRIVE]
    if rest:
        clauses.append(f"for {_join_names(rest)} {prescribed}")
    return "; ".join(clauses)


def offload_caveats(
    vehicle_name: str,
    calibration: tuple[float, float, str] | None,
    *,
    structural: Sequence[Mapping[str, Any]] = (),
    drives: Mapping[str, str] | None = None,
    penalties: Sequence[str] = (),
    uncharged: Sequence[str] = (),
) -> list[str]:
    """Every caveat of an offload block on vehicle_name: its calibration caveat
    (``offload_calibration_caveat``) then OFFLOAD_CAVEATS, word for word when
    ``structural`` is empty and every drive is the prescribed one (every SP1-type block).
    With ``structural`` (the block's records that charge a modelled structural mass: cases,
    structure payload cases, sensitivity arms; SP7 step S3a, D-SP7-22) the structure item
    is ``offload_structure_caveat`` (with the block's ``penalties``, its penalty rows'
    names, and ``uncharged``, the names of its cases that charge nothing) and the tanks
    item OFFLOAD_TANKS_STRUCTURE_CAVEAT, or OFFLOAD_TANKS_STRUCTURE_PENALTY_CAVEAT with a
    penalty row; with ``drives`` (case name to assist model) the drive item is
    ``offload_drive_caveat``."""
    items = list(OFFLOAD_CAVEATS)
    if structural:
        items[OFFLOAD_STRUCTURE_CAVEAT_INDEX] = offload_structure_caveat(
            structural, penalties=penalties, uncharged=uncharged
        )
        items[OFFLOAD_TANKS_CAVEAT_INDEX] = (
            OFFLOAD_TANKS_STRUCTURE_PENALTY_CAVEAT if penalties else OFFLOAD_TANKS_STRUCTURE_CAVEAT
        )
    if drives:
        items[OFFLOAD_DRIVE_CAVEAT_INDEX] = offload_drive_caveat(drives)
    return [offload_calibration_caveat(vehicle_name, calibration), *items]


OFFLOAD_ENERGY_TEXT = (
    "Energy comparison: the fuel (RP-1) removed is each stage's removed propellant times "
    "its fuel fraction (the energy block's fuel mass over the experiment vehicle's full "
    "load: the mixture ratio kept, on any load; the lower heating value from the energy "
    "block), the oxidiser (LOX) the rest; the combustion heat is the removed fuel's mass "
    "times its lower heating value, and the electrical energy is the offloaded run's "
    "push (positive drive work over the drive efficiency)"
)
"""What the energy rows of the offload block mean."""
OFFLOAD_DECOMPOSITION_TEXT = (
    "Cross-vehicle decomposition of each case against the pad, both at P_ref "
    "(docs/physics.md, 'Cross-vehicle decomposition'): the ideal delta-v the case's "
    "vehicle does without, D_id(pad) - D_id(case), split into the release-speed head "
    "start and the differences in the losses, the pre-flight burn, the fairing term and "
    "the margin; each cell is m/s (kg of the offload, a proportional split). Only the "
    "joint gravity + steering term is read as physics. The residual must stay below "
    "checks.closure_tol_mps: explained when it does, bug_suspect (findings blocked) "
    "when it does not"
)
"""The sentence above the decomposition table of the offload block."""
OFFLOAD_PAD_CONTROL_CHECK_CLAUSE = (
    "a stage-1 pad control is a consistency test of the solver, and a failing one blocks findings"
)
"""The pad-control clause of the experiment summary's offload Checks heading (a sweep
solves no pad control)."""
OFFLOAD_DECOMPOSITION_CHECK_CLAUSE = (
    "the screening rule for offload rows: an offload beyond the ideal screening estimate "
    "is explained only by a decomposition that closes, else bug_suspect; offload rows "
    "never enter the unexplained-beats list"
)
"""The decomposition clause of the offload Checks heading, in both summaries."""
OFFLOAD_CHECKS_TEXT = (
    f"Offload checks ({OFFLOAD_PAD_CONTROL_CHECK_CLAUSE}; {OFFLOAD_DECOMPOSITION_CHECK_CLAUSE})"
)
"""The heading of the offload lines of an experiment summary's Checks section."""
OFFLOAD_SWEEP_CHECKS_TEXT = f"Offload checks ({OFFLOAD_DECOMPOSITION_CHECK_CLAUSE})"
"""The heading of the offload lines of a sweep summary's Checks section (no pad
control: a sweep names stage-1 solves and fixed cases only)."""
OFFLOAD_SWEEP_FLAGS_TEXT = (
    "Offload flags at each point (the case record's: its solve's and its recorded run's; "
    "sweep_index.csv gives their number, `<case>.n_flags`, beside the solve's gamma*_ref, "
    "`<case>.solve_gamma_star_rad`)"
)
"""The heading of the per-point offload flag lines of a sweep summary's Checks section
(SP1 step 8a, KI-028: a sweep point writes no offload run directory, so its solve's
flags are recorded here)."""
OFFLOAD_SWEEP_NO_FLAG_LIST = "n/a: nothing solved"
"""What a point's flag line says for a case record without a flag list (a
reference_failed point solves nothing)."""
PAD_CONTROL_BLOCKED = (
    "Findings are blocked until these are investigated (a stage-1 pad control failed its "
    "consistency test of the solver, docs/physics.md, 'Pad control, and why')"
)
"""What the Checks section says when a stage-1 pad control fails its consistency test
(``blocked_lines``, ``offload_blocking_controls``): its own line, apart from the runs and
comparisons of FINDINGS_BLOCKED."""
RESOLUTION_EFFECT_TEXT = (
    "a resolution effect: the full-load pad misses P_ref by grams of residual "
    "propellant at the feasible-side convention's resolution, within "
    "final_payload_xtol_kg; not a failure"
)
"""How a stage-1 pad control that ends no_offload by grams is reported (phase file SP1,
section 12, step 5 deviation 2)."""

type OffloadRow = tuple[str, str, str]
"""A row of an offload table: (label with unit, format, key path in the record)."""
OFFLOAD_CASE_ROWS: tuple[OffloadRow, ...] = (
    ("assisted run (of)", "text", "of"),
    ("kind", "kind", ""),
    ("status (the solve, or a fixed case's payload search)", "text", "status"),
    ("recorded run (replay it beside the pad)", "text", "run"),
    ("  its status", "text", "run_status"),
    ("quoted offload [t]", "t", "quoted_offload_kg"),
    ("  basis", "text", "quoted_basis"),
    ("stage-1 propellant removed, gross [t]", "t", "stage1_offload_kg"),
    (
        "stage-2 propellant removed, gross [t] (a stage-2 pre-offload included)",
        "t",
        "stage2_offload_kg",
    ),
    ("total propellant removed, gross [t]", "t", "total_offload_kg"),
    ("  % of the stage-1 load", "pct", "stage1_fraction"),
    ("  % of the stage-2 load", "pct", "stage2_fraction"),
    ("  % of the total load", "pct", "total_fraction"),
    (
        "assumed stage-1 dry mass added [t] (an assumption, not a sized structure)",
        "penalty_t",
        "stage1_dry_mass_added_kg",
    ),
    ("payload flown [kg] (solved: P_ref; fixed: its own P*)", "num", "payload_kg"),
    ("  minus P_ref [kg]", "signed", "payload_delta_kg"),
    ("verification: P* of the offloaded vehicle [kg]", "num", "verification.payload_kg"),
    ("  P* - P_ref [kg]", "signed", "verification.delta_kg"),
    ("  tolerance [kg] (checks.search_final_flag_rel x P_ref)", "num", "verification.tolerance_kg"),
    ("  passed", "text", "verification.passed"),
    ("pad control's offload in this mode [t]", "t", "pad_control_offload_kg"),
    ("  offload net of the pad control [t]", "t", "net_offload_kg"),
    ("liftoff mass [kg]", "num", "vs_pad.liftoff_mass_kg"),
    ("  pad's [kg]", "num", "vs_pad.pad_liftoff_mass_kg"),
    ("MECO: t after release [s]", "num", "vs_pad.stage1_burnout_t_s"),
    ("  pad's [s]", "num", "vs_pad.pad_stage1_burnout_t_s"),
    ("max-Q [Pa] (unthrottled: an upper bound)", "num", "vs_pad.max_q_pa"),
    ("  pad's [Pa]", "num", "vs_pad.pad_max_q_pa"),
    ("  above the pad's", "text", "vs_pad.max_q_above_pad"),
    ("peak felt axial g in flight [g0]", "num", "vs_pad.peak_felt_axial_g_flight"),
    ("  pad's [g0]", "num", "vs_pad.pad_peak_felt_axial_g_flight"),
    ("speed at release [m/s]", "num", "vs_pad.speed_at_release_mps"),
    ("peak felt g on the track [g0]", "num", "vs_pad.felt_g_track_peak"),
    ("interface force, peak [N]", "num", "vs_pad.peak_interface_force_N"),
    ("facility length incl. braking [m]", "num", "vs_pad.facility_length_m"),
    ("ideal-screening offload at this release speed [t]", "t", "screening_offload_kg"),
    ("  stage-1 offload / screening offload", "num", "screening_ratio"),
    ("  beats the screening estimate", "text", "beats_screening"),
    ("decomposition status", "text", "decomposition_status"),
    ("  residual [m/s]", "sci", "decomposition.xv_residual_mps"),
    ("paired pad (the same propellant change, no penalty)", "text", "paired_pad.run"),
    ("  its P* [kg]", "num", "paired_pad.payload_kg"),
    ("  its P* - P_ref [kg]", "signed", "paired_pad.payload_delta_vs_reference_kg"),
    (
        "  assisted P* - paired pad P* [kg] (one vehicle, attributed)",
        "signed",
        "paired_pad.payload_delta_kg",
    ),
    ("  screening status (against the paired pad)", "text", "paired_pad.screening_status"),
    ("flags (see Flags)", "count", "flags"),
)
"""Rows of the offload cases table (one column per case). The quoted offload leads (a
stage-1 solve's x*, the headline; a stage2 or both solve's x* net of the pad control;
a fixed case's imposed offload); the gross rows follow it (for a stage2 or both case a
property of the vehicle model, not a saving of the assist)."""
OFFLOAD_ENERGY_ROWS: tuple[OffloadRow, ...] = (
    ("RP-1 removed [kg]", "num", "energy.fuel_removed_kg"),
    ("LOX removed [kg]", "num", "energy.oxidizer_removed_kg"),
    ("combustion heat of the removed RP-1, lower heating value [MJ]", "MJ", "energy.heat_J"),
    ("  [kWh]", "num", "energy.heat_kWh"),
    ("electrical energy of the push [MJ]", "MJ", "energy.electrical_energy_J"),
    ("  [kWh]", "num", "energy.electrical_energy_kWh"),
    (
        "heat / electricity (not an efficiency claim)",
        "num",
        "energy.heat_to_electricity_ratio",
    ),
)
"""Rows of the energy comparison, appended to the cases table when the block has
energy inputs."""
OFFLOAD_PAD_CONTROL_ROWS: tuple[OffloadRow, ...] = (
    ("recorded run", "text", "run"),
    ("status", "text", "status"),
    ("x_pad [kg]", "num", "offload_kg"),
    ("m_res at x_pad [kg] (signed)", "num", "m_res_kg"),
    ("dv margin at x_pad [m/s] (signed)", "num", "dv_margin_mps"),
    ("abs(dm_res/dx) from the solve's own logs [kg/kg]", "num", "slope_kg_per_kg"),
    ("stage 1: bound final_payload_xtol_kg / abs(dm_res/dx) [kg]", "num", "bound_kg"),
    ("  0 <= x_pad <= bound (an ok control)", "text", "within_bound"),
    ("ended no_offload by grams (a resolution effect)", "text", "resolution_effect"),
    ("stage 1: consistency test of the solver (section 5.3)", "text", "consistency"),
    ("verification: P* - P_ref [kg]", "signed", "verification.delta_kg"),
    ("  passed", "text", "verification.passed"),
)
"""Rows of the pad-control table (one column per mode)."""


def _dig(record: Mapping[str, Any], path: str) -> Any:
    """The value at a dotted key path of a plain record (None where a level is missing)."""
    node: Any = record
    for key in path.split("."):
        if not isinstance(node, Mapping):
            return None
        node = node.get(key)
    return node


def _offload_cell(record: Mapping[str, Any], fmt: str, path: str) -> str:
    """One cell of an offload table: ``t`` kg printed in tonnes, ``pct`` a fraction in
    percent, ``MJ`` joules in MJ, ``signed`` a signed number, ``sci`` a residual to 3
    significant digits (never rounded to 0), ``count`` a list's length, ``kind`` the
    case's solve mode or fixed offload (a fraction key with its fraction, a mass key
    with its offload in tonnes), ``penalty_t`` the assumed penalty's kg in tonnes, or
    STRUCTURE_INSTEAD_OF_PENALTY_CELL on a record that charges a modelled structural mass
    (SP7 step S3a: the row's label says "assumed", which that mass is not), ``text`` and
    ``num`` as ``_fmt``."""
    if fmt == "penalty_t":
        if record.get("structure_charged") is True:
            return STRUCTURE_INSTEAD_OF_PENALTY_CELL
        return _offload_cell(record, "t", path)
    if fmt == "kind":
        if record.get("kind") == "solve":
            return f"solved, {record.get('mode')}"
        key = record.get("fixed_key")
        fraction = record.get("fixed_fraction")
        if fraction is not None:
            return f"fixed, {key} = {_fmt(fraction)}"
        return f"fixed, {key} = {_offload_cell(record, 't', 'offload_kg')} t"
    value = _dig(record, path)
    if fmt == "count":
        return str(len(value)) if isinstance(value, list) else "n/a"
    if not _is_finite_number(value):
        return _fmt(value)
    x = float(value)
    if fmt == "t":
        return _fmt(float(kg_to_t(x)))
    if fmt == "pct":
        return _fmt(float(to_percent(x)))
    if fmt == "MJ":
        return _fmt(float(j_to_mj(x)))
    if fmt == "signed":
        return _signed(x)
    if fmt == "sci":
        return f"{x:.3g}"
    return _fmt(x)


def _offload_table(
    records: Sequence[Mapping[str, Any]], rows: Sequence[OffloadRow], label: str
) -> str:
    """A table with one row per OffloadRow and one column per record (headed by the
    record's ``label`` key)."""
    header = ["quantity", *(str(r.get(label)) for r in records)]
    body = [[row[0], *(_offload_cell(r, row[1], row[2]) for r in records)] for row in rows]
    return _table(header, body)


def offload_decomposition_table(cases: Sequence[Mapping[str, Any]]) -> str:
    """The cross-vehicle decomposition of every case that has one: per CROSS_VEHICLE_TERMS
    term ``m/s (kg)``, the joint gravity + steering term, the ideal delta-v reduction,
    the residual and the status; one column per case."""
    with_xv = [c for c in cases if c.get("decomposition")]
    if not with_xv:
        return "(no decomposition: no case has an evaluation at P_ref)"

    def cell(c: Mapping[str, Any], term: str) -> str:
        xv = c["decomposition"]
        return f"{_signed(xv.get(f'xv_{term}_mps'))} ({_signed(xv.get(f'xv_{term}_kg'))})"

    header = ["term: m/s (kg)", *(str(c["name"]) for c in with_xv)]
    rows = [[t.replace("_", " "), *(cell(c, t) for c in with_xv)] for t in CROSS_VEHICLE_TERMS]
    rows.append(["gravity + steering", *(cell(c, GRAVITY_STEERING) for c in with_xv)])
    rows.append(
        [
            "D_id(pad) - D_id(case) [m/s]",
            *(_fmt(c["decomposition"].get("xv_ideal_dv_reduction_mps")) for c in with_xv),
        ]
    )
    rows.append(
        [
            "offload split [kg]",
            *(_fmt(c["decomposition"].get("xv_offload_kg")) for c in with_xv),
        ]
    )
    rows.append(
        [
            "residual [m/s]",
            *(_offload_cell(c, "sci", "decomposition.xv_residual_mps") for c in with_xv),
        ]
    )
    rows.append(["status", *(_fmt(c["decomposition"].get("xv_status")) for c in with_xv)])
    return _table(header, rows)


PAD_CONTROL_VERDICT_TEXT: dict[str, str] = {
    CHECK_PASS: "consistency test pass",
    CHECK_FAIL: "consistency test FAIL (a consistency test of the solver: findings blocked)",
    PAD_CONTROL_NO_BOUND: "consistency test not checked (no bound)",
}
"""How the Checks section and the pad-control lines word a stage-1 control's
``consistency`` verdict (``results_io.pad_control_consistency``)."""


def _pad_control_text(c: Mapping[str, Any]) -> str:
    """One pad control in words: x_pad (by a resolution effect, or a no_offload control
    that misses P_ref by more), and for stage 1 the bound of section 5.3 (an ok control)
    and the consistency verdict; stage 2 and both as properties of the vehicle model."""
    m_res = _fmt(c.get("m_res_kg"))
    ok = c.get("status") == OK_STATUS
    if c.get("resolution_effect"):
        text = f"x_pad = 0, m_res(0) = {m_res} kg: {RESOLUTION_EFFECT_TEXT}"
    elif c.get("status") == NO_OFFLOAD_STATUS:
        text = (
            f"x_pad = 0, m_res(0) = {m_res} kg: the full-load pad misses P_ref by more than "
            "final_payload_xtol_kg in the control's own solve (its gamma*_ref and warm "
            "starts are its own, not the pad search's): the control does not reproduce "
            "P_ref at this budget"
        )
    else:
        text = f"x_pad = {_fmt(c.get('offload_kg'))} kg (status {c.get('status')})"
    verdict = c.get("consistency")
    if verdict == CHECK_NA or verdict is None:
        return text + "; a property of the vehicle model, which the assisted cases are net of"
    if ok and c.get("bound_kg") is not None:
        side = "within" if c.get("within_bound") else "OUTSIDE"
        text += f"; {side} the bound 0 to {_fmt(c.get('bound_kg'))} kg (section 5.3)"
    elif ok:
        text += "; no bound (no logged search brackets m_res = 0, so no slope)"
    return f"{text}; {PAD_CONTROL_VERDICT_TEXT.get(str(verdict), str(verdict))}"


def pad_control_lines(controls: Sequence[Mapping[str, Any]]) -> list[str]:
    """The pad-control table (one column per mode) and one line per control in words
    (``_pad_control_text``)."""
    if not controls:
        return ["(no pad control: pad_control is false, or no solved case ran)"]
    lines = [_offload_table(controls, OFFLOAD_PAD_CONTROL_ROWS, "mode"), ""]
    lines += [f"- pad control {c.get('mode')}: {_pad_control_text(c)}" for c in controls]
    return lines


STRUCTURE_ARM_COLUMNS: tuple[str, ...] = (
    "modelled dm at x* [kg] (structural arms)",
    "structure set",
    "envelope pad (the arm's own)",
)
"""The columns the arms table gains when some arm is structural (SP7 step S3b): dm1 + dm2
at the arm's x*, the set and the pad whose flight is the arm's envelope (its perturbed pad
for a vehicle parameter)."""
STRUCTURE_ARM_CAVEAT = (
    "structural sensitivity arms: an arm is sized on its perturbed vehicle and on the pad "
    "its offload was solved against (its perturbed pad for a vehicle parameter, the "
    "unchanged pad for a run parameter), not on perturbed station masses; under the "
    "vehicle.stages.stage1.dry_mass_t arm the geometry is built from the perturbed variant, "
    "but the stations are loaded from the structure file's mass breakdown, so the perturbed "
    "dry mass reaches the sizing only through the push's interface force and the perturbed "
    "pad's envelope, never through the stage-1 station loads (measured on the synthetic file "
    "at the headline with the envelope held: +10% stage-1 dry mass gives +10.4 kg of dm, "
    "+0.20%)"
)
"""The caveat printed beside the structural sensitivity arms wherever they are reported
(phase file SP7 section 12, deviation 17; SP7 step S3b: the arms table of the offload
section and the Structure subsection); ``sim`` re-exports it."""


def offload_sensitivity_table(arms: Sequence[Mapping[str, Any]]) -> str:
    """The offload sensitivity arms: case, parameter, change, whether the pad was
    perturbed, the arm's P_ref, status, offload and its change against the nominal case,
    the share of the stage-1 load, the decomposition and the screening ratio, whether
    the solve was reused; when some arm is structural (SP7 step S3b, ``structure_charged``
    on its record) also STRUCTURE_ARM_COLUMNS, and ``offload_section`` prints
    STRUCTURE_ARM_CAVEAT under the table."""
    structural = any(a.get("structure_charged") for a in arms)
    header = [
        "case",
        "parameter",
        "change",
        "pad perturbed",
        "P_ref [kg] (the same-perturbation pad's P*)",
        "status",
        "offload [t]",
        "change vs nominal [t]",
        "% of the stage-1 load",
        "decomposition",
        "offload / screening",
        "solve reused (same trajectory)",
        *(STRUCTURE_ARM_COLUMNS if structural else ()),
    ]
    rows = []
    for a in arms:
        row = [
            str(a.get("case")),
            str(a.get("param")),
            f"{a.get('fraction', 0.0):+.0%}",
            "yes" if a.get("pad_perturbed") else "no",
            _fmt(a.get("reference_payload_kg")),
            _fmt(a.get("status")),
            _offload_cell(a, "t", "offload_kg"),
            _offload_cell(a, "t", "offload_delta_kg"),
            _offload_cell(a, "pct", "stage1_fraction"),
            _fmt(a.get("decomposition_status")),
            _fmt(a.get("screening_ratio")),
            "yes" if a.get("trajectory_reused") else "no",
        ]
        if structural:
            row += _structure_arm_cells(a)
        rows.append(row)
    return _table(header, rows)


def _structure_arm_cells(arm: Mapping[str, Any]) -> list[str]:
    """The STRUCTURE_ARM_COLUMNS cells of one arm: a structural arm's dm, set and
    envelope pad; an arm that was never solved (its same-perturbation pad has no P*,
    ``offload_kg`` None) "n/a (not solved: <status>)" rather than a claim that it is
    uncharged; an arm of an unstructured case "n/a (uncharged)"."""
    if arm.get("structure_charged"):
        return [
            _fmt(arm.get("structure_dm_kg")),
            _fmt(arm.get("structure_set")),
            _fmt(arm.get("structure_envelope_pad")),
        ]
    if arm.get("offload_kg") is None:
        return [f"n/a (not solved: {arm.get('status')})", "n/a", "n/a"]
    return ["n/a (uncharged)", "n/a", "n/a"]


# ----------------------------------------------------------- structure subsection (SP7 S3b)

STRUCTURE_SUBSECTION_TITLE = "### Structure"
"""The title of the offload section's Structure subsection (printed only when the
experiment declares a structure block)."""
STRUCTURE_LAYER_LABELS: dict[str, str] = {
    STRUCTURE_CENTRAL_SET: "central (every coefficient at its central value)",
    SET_PHYSICS_LOW: "physics band, low-mass end",
    SET_PHYSICS_HIGH: "physics band, high-mass end",
    SET_OUTER_LOW: (
        "outer envelope, low-mass end (the design axes at their corner, the physics "
        "coefficients searched)"
    ),
    SET_OUTER_HIGH: (
        "outer envelope, high-mass end (the design axes at their corner, the physics "
        "coefficients searched)"
    ),
}
"""The three layers of D-SP7-18 by set name: the layer and set cell of a case at the
headline settings (``structure_layer_label`` names a case that moves a design axis as
layer 2, and one that moves the entry path or the sizing basis as a settings row)."""
STRUCTURE_OVERRIDES_LAYER = "design axis (layer 2)"
"""The layer of a case that moves a design axis off the headline (``structure_layer_label``;
D-SP7-18 and design 4.2.6: the non-optimum factors, t_r, f, the pad count and k_ts by
``overrides``, the margin, the envelope cap, and the dynamic mode, which sets the DLF's
basis): its set stays the base set (D-SP7-43), its sizing is not the set's own end."""
STRUCTURE_OUTER_SETS: tuple[str, ...] = (SET_OUTER_LOW, SET_OUTER_HIGH)
"""The outer envelope's sets: each fixes every design axis, recording its own margin and
cap, so those two never count as a departure from the headline on an outer set."""
STRUCTURE_HEADLINE_DYNAMIC = "rise_time"
"""The headline's dynamic mode (the DLF from a rise time: the structure file's assumed
real-drive one for constant_accel, the drive's own for a linear motor, SP7 step S4b; the
sets were searched under it at the headline constant_accel push): a case under
quasi_static or step moves a design axis (``structure_layer_label``)."""
STRUCTURE_FLOWN_PUSH_NOTE = (
    "on a linear-motor case (ramp cost n/a: its push is flown, SP7 step S4b) t_r is the "
    "drive's own force rise time (a constant_accel case's is the structure file's assumed "
    "real-drive t_r; an outer set's dynamics.rise_time_s does not act on a linear-motor "
    "case, so there its layer's 'design axes at their corner' leave t_r at the drive's "
    "value); n_q is the largest flown quasi-static load, not a plateau; DLF is the "
    "factor (n_peak - n_rest)/(n_q - n_rest) of the charged n_peak, which is under "
    "rise_time the larger of the rise formula's peak n_rest + min(2, 1 + T/(pi t_r)) (n_q - "
    "n_rest) and the flown load history's phase-free single-mode bound, under step the "
    "larger of n_rest + 2 (n_q - n_rest) and the flown load plus its total variation from "
    'rest, and n_q under quasi_static (docs/physics.md, "The flown push of a linear '
    'motor")'
)
"""The note printed under the case table and the payload table when a solved structural
case's push is flown (``structure_push_is_flown``; SP7 step S4b, review round 1 H-P1-06
and H-P1-07, round 2 H-P2-04, round 3 H-P3-02): the shared rows' t_r, n_q and DLF mean
the drive's own rise time, the flown load and the charged factor there, worded by mode,
and an outer set's corner rise time does not act on such a case. A summary
without such a case does not print it, so a constant_accel summary (a search_failed case
among its cases included) is unchanged."""
STRUCTURE_ROW_NOT_BAND = "a row, not a band end"
"""What the layer cell says of a case that moves the entry path or the sizing basis off the
headline (design 4.2.6: "rows, not band"); such a case is never a band end."""
STRUCTURE_KIND_MODELLED = "modelled structure (first-order station sizing of the push load)"
STRUCTURE_KIND_PENALTY = (
    "assumed stage-1 dry-mass penalty (a parametric row, not a sized structure)"
)
STRUCTURE_NO_OFFLOAD_CELL = "none (no offload at P_ref; see the no_offload line below)"
"""What the x* cell and the share cell of a structural case whose solve ended no_offload
print (D-SP7-32: never "0 t", nor 0 %)."""
STRUCTURE_NOT_FLOWN = "not flown"
"""What a band or payload line prints for a set or case the experiment did not fly."""
STRUCTURE_PAYLOAD_RECORD_KIND = "structure payload case"
"""The ``kind`` of a structure payload case's record (design 4.4, "Payload form": a record
of its own in the offload record's ``structure_payload_cases`` list, never under the
offload cases heading); ``sim`` re-exports it."""
STRUCTURE_PENALTY_ROW_LABEL = (
    "assumed stage-1 dry mass added [t] (an assumption, not a sized structure)"
)
"""The penalty rows' mass row of the Structure case table: the same words as the offload
cases table's row (``OFFLOAD_CASE_ROWS``), so the two tables read alike."""
STRUCTURE_INSTEAD_OF_PENALTY_CELL = (
    "none: a modelled structural mass is charged instead (the Structure subsection)"
)
"""The penalty row's cell of a structural case in both case tables (SP7 step S3a): its
record's ``stage1_dry_mass_added_kg`` is 0 and the modelled mass is not an assumed
penalty, so the cell says what the run carries rather than printing 0 under "assumed"."""
STRUCTURE_AT_X_NOTE = "(a no_offload end: at x = 0)"
"""The suffix of the case table's rows "at x*": a no_offload end was sized at x = 0."""
STRUCTURE_FLIGHT_CHECK_SCOPE = (
    "the tank elements with a station envelope only: the barrels, the domes and the tube; "
    "the aft skirt and the load ring are not checked"
)
"""The element scope of the post-hoc flight check (structure.FLIGHT_CHECK_ELEMENTS; phase
file SP7 section 12, deviation 24), stated wherever its mass is printed (in short in the
case table's row label, STRUCTURE_FLIGHT_CHECK_SCOPE_SHORT; in full in the note under the
table and in the flag line) so a 0 never reads as a clearance of the whole structure;
``sim`` re-exports it for the flag line."""
STRUCTURE_FLIGHT_CHECK_SCOPE_SHORT = "tank elements only, not the aft skirt or the ring"
"""The element scope in the case table's row label (visual V7 of S3b's review: the label
stays short so the table's first column keeps its width; honesty H-S3B-P3-03: the scope is
still in the label); the full sentence is STRUCTURE_FLIGHT_CHECK_SCOPE."""
STRUCTURE_FLIGHT_CHECK_ROW_LABEL = (
    "flight check: the recorded run's own flight over the pad envelope [kg] "
    f"({STRUCTURE_FLIGHT_CHECK_SCOPE_SHORT}; sized, not charged; see the note)"
)
"""The case table's flight-check row: the quantity, its unit and the element scope in
short; the full scope, the treatment of the cap, the margin and the plausibility factor
are STRUCTURE_FLIGHT_CHECK_NOTE."""
STRUCTURE_FLIGHT_CHECK_NOTE = (
    "flight check (the row above): the recorded run's own flight after its release, "
    f"{STRUCTURE_FLIGHT_CHECK_SCOPE}; the exceedance is sized and never charged or "
    "iterated; the flight's stage-1 felt n is capped as the envelope's was and evaluated "
    "unfactored against the envelope at the case's margin; the mass is the unscaled sizing "
    "(a plausibility-scaled row's dm carries the rule's factor, its exceedance does not); "
    "n/a on a run without a time series; not applicable to a structure payload case (its "
    "run flies its own P*, so the pad's envelope at P_ref is not its comparison)"
)
"""The bullet under the case table that carries the flight-check row's qualifications
(V7 of S3b's visual review: the row label stays short)."""
STRUCTURE_CASE_ROWS: tuple[OffloadRow, ...] = (
    ("assisted run (of)", "text", "of"),
    ("kind", "structure_kind", ""),
    ("layer and set (D-SP7-18)", "structure_layer", ""),
    ("design-axis overrides (path value; none)", "structure_overrides", ""),
    (
        "sizing basis (flown: re-sized at every x; full_load: once at x = 0)",
        "text",
        "structure_sizing",
    ),
    ("dynamic mode", "text", "structure_dynamic"),
    ("  rise time t_r [s]", "num", "structure_t_r_s"),
    ("  axial frequency f [Hz]", "num", "structure_f_Hz"),
    ("  dynamic load factor DLF", "num", "structure_dlf"),
    ("n_q, the quasi-static plateau [g0]", "num", "structure_n_q_g"),
    ("n_peak = n_rest + DLF (n_q - n_rest) [g0]", "num", "structure_n_peak_g"),
    ("F_peak, the peak interface force [MN]", "MN", "structure_F_peak_N"),
    ("  ramp cost (a' - a)/a (constant_accel under rise_time)", "num", "structure_ramp_cost_rel"),
    ("load entry", "text", "structure_entry"),
    ("margin on the envelope's loads and pressures", "num", "structure_margin"),
    (
        "envelope cap on the pad's stage-1 felt n [g0] (n/a: no cap)",
        "num",
        "structure_envelope_cap_g",
    ),
    (
        "plausibility-scaled (the dm carries the rule's factor)",
        "text",
        "structure_plausibility_scaled",
    ),
    (
        "  M_model / R (the model's envelope tank mass over Heineman's relation)",
        "num",
        "structure_plausibility_ratio",
    ),
    (
        "  the rule's factor for this band end (1 when it does not fire on that end; a "
        "central or design-axis case is not a band end and prints n/a)",
        "plausibility_factor",
        "structure_plausibility_factor",
    ),
    (f"dm1, stage 1 with the interstage, at x* [kg] {STRUCTURE_AT_X_NOTE}", "dm1", ""),
    (f"dm2, stage 2, at x* [kg] {STRUCTURE_AT_X_NOTE}", "num", "structure_dm_stage2_kg"),
    ("dm1 + dm2 at x = 0 [kg]", "num", "structure_dm_x0_kg"),
    (STRUCTURE_PENALTY_ROW_LABEL, "penalty_t", "stage1_dry_mass_added_kg"),
    ("status (the solve)", "text", "status"),
    ("x* [t]", "xstar", "offload_kg"),
    ("  % of the stage-1 load", "xstar_pct", "stage1_fraction"),
    ("verification: P* - P_ref [kg]", "signed", "verification.delta_kg"),
    ("  passed", "text", "verification.passed"),
    (STRUCTURE_FLIGHT_CHECK_ROW_LABEL, "num", "structure_flight_exceedance_kg"),
    (f"fixed-point sizings at x* {STRUCTURE_AT_X_NOTE}", "num", "structure_iterations"),
    ("structure flags fired (their numbers are in structure_flags)", "structure_flags", ""),
    ("flags (see Flags)", "count", "flags"),
)
"""Rows of the Structure subsection's case table (one column per structural case, SP1's
penalty rows of the same experiment beside them). dm1 is dm - dm2; a no_offload end's x*
cell and share cell are STRUCTURE_NO_OFFLOAD_CELL, its rows "at x*" its sizing at x = 0
(STRUCTURE_AT_X_NOTE); the flight-check row's qualifications are the note under the table
(STRUCTURE_FLIGHT_CHECK_NOTE)."""
STRUCTURE_FLAGS_NOT_SIZED = "n/a (no sizing at x*: the solve found no x*)"
"""What the fired-flags cell (and the sweep index's ``structure_flags`` column) prints for
a structural case whose solve ended search_failed: no sizing at x* was made, so no flag
was evaluated (never "none", which would read as "no flag fired")."""
STRUCTURE_PAYLOAD_NOT_WRITTEN = "n/a (the P_2* search failed: nothing written)"
"""What a payload case's recorded-run cell prints when its second pass found no P*."""
STRUCTURE_PAYLOAD_FLAG_NA = "n/a (the P_2* search failed)"
"""What a payload case's flag cell prints when its second pass found no P* (the record's
``unconverged`` is None: the flag was never evaluated)."""
STRUCTURE_PAYLOAD_CONTRACTION_MAX = 0.1
"""The contraction c above which the payload form's flag fires (design 4.4; the flag and
the rule live in ``sim``, which re-exports this beside the row label built from it)."""
STRUCTURE_PAYLOAD_RESIDUAL_FRACTION = 0.5
"""The fraction of final_payload_xtol_kg the payload form's residual estimate may reach
before its flag fires (design 4.4; re-exported by ``sim``)."""
STRUCTURE_PAYLOAD_FLIGHT_CHECK_NA = (
    "not applicable: the recorded run flies its own P*; the envelope is the pad's at P_ref, "
    "so a check against it would measure the payload gain P_2* - P_ref (which the pad's own "
    "flight at P_2* would need too), not the push; the check is made on the offload cases, "
    "which fly P_ref"
)
"""What a structure payload case's record (``flight_check``), its run's assumption line
and the payload table say of the post-hoc flight check (SP7 step S3b, review N-S3b-R3-01):
it is not run on a payload case, so ``structure_flight_exceedance_kg`` stays None and no
flag fires for a payload gain; ``sim`` re-exports it."""
STRUCTURE_PAYLOAD_SETTINGS_ROWS: tuple[OffloadRow, ...] = (
    ("layer and set (D-SP7-18)", "structure_layer", ""),
    ("design-axis overrides (path value; none)", "structure_overrides", ""),
    ("sizing basis (a payload case: full_load, once at the full load)", "text", "structure_sizing"),
    ("dynamic mode", "text", "structure_dynamic"),
    ("  rise time t_r [s]", "num", "structure_t_r_s"),
    ("  axial frequency f [Hz]", "num", "structure_f_Hz"),
    ("  dynamic load factor DLF", "num", "structure_dlf"),
    ("n_peak = n_rest + DLF (n_q - n_rest) [g0] (at P_1*)", "num", "structure_n_peak_g"),
    ("F_peak, the peak interface force [MN] (at P_1*)", "MN", "structure_F_peak_N"),
    ("load entry", "text", "structure_entry"),
    ("margin on the envelope's loads and pressures", "num", "structure_margin"),
    (
        "envelope cap on the pad's stage-1 felt n [g0] (n/a: no cap)",
        "num",
        "structure_envelope_cap_g",
    ),
    (
        "plausibility-scaled (dm_0 and dm_1 carry the rule's factor)",
        "text",
        "structure_plausibility_scaled",
    ),
    (
        "  M_model / R (the model's envelope tank mass over Heineman's relation)",
        "num",
        "structure_plausibility_ratio",
    ),
    (
        "  the rule's factor for this band end (1 when it does not fire on that end; a "
        "central or design-axis case is not a band end and prints n/a)",
        "plausibility_factor",
        "structure_plausibility_factor",
    ),
)
"""The settings rows of the payload cases table (SP7 step S3b, review H-S3B-P3-01): what
sized dm_0 and dm_1 (the same record keys as the case table's rows, so a scaled
physics-set payload case never reads like a central one)."""
STRUCTURE_PAYLOAD_ROWS: tuple[OffloadRow, ...] = (
    ("assisted run (of)", "text", "of"),
    ("kind", "text", "kind"),
    ("recorded run (the P_2* search's run, carrying dm_1)", "payload_run", "run"),
    ("status (the P_2* search's: ok, or the failed search's status)", "text", "status"),
    ("  pass 1 (the P_1* search's status)", "text", "search_1_status"),
    *STRUCTURE_PAYLOAD_SETTINGS_ROWS,
    ("P_ref [kg] (the pad's P*)", "num", "reference_payload_kg"),
    ("dm_0 [kg] (sized at P_ref on the full-load vehicle)", "num", "dm_0_kg"),
    ("P_1* [kg] (searched on the vehicle carrying dm_0)", "num", "payload_1_kg"),
    ("dm_1 [kg] (sized at P_1*)", "num", "dm_1_kg"),
    ("P_2* [kg] (searched on the vehicle carrying dm_1)", "num", "payload_kg"),
    ("  P_2* - P_ref [kg]", "signed", "payload_delta_kg"),
    ("  P_2* - P_1* [kg]", "signed", "payload_2_minus_1_kg"),
    (
        "contraction c = abs((P_2* - P_1*)/(dm_1 - dm_0)) x abs((dm_1 - dm_0)/(P_1* - P_ref))",
        "sci",
        "contraction",
    ),
    ("residual estimate c x abs(P_2* - P_1*) [kg]", "sci", "residual_estimate_kg"),
    (
        f"  tolerance [kg] ({STRUCTURE_PAYLOAD_RESIDUAL_FRACTION:g} x final_payload_xtol_kg)",
        "num",
        "residual_tolerance_kg",
    ),
    (
        "structure_payload_unconverged (the estimate above the tolerance, or c > "
        f"{STRUCTURE_PAYLOAD_CONTRACTION_MAX:g})",
        "payload_flag",
        "unconverged",
    ),
    ("flight check: the recorded run's own flight over the pad envelope", "text", "flight_check"),
    ("flags (see Flags)", "count", "flags"),
)
"""Rows of the payload cases table (design 4.4, "Payload form"): the case's settings
(STRUCTURE_PAYLOAD_SETTINGS_ROWS), the two passes and the flag (its label built from the
two constants above), the flight check's row (STRUCTURE_PAYLOAD_FLIGHT_CHECK_NA: not run
on a payload case); read beside the full_load row of the same variant and settings. A case
whose P_2* search failed prints its status, STRUCTURE_PAYLOAD_NOT_WRITTEN for the run and
STRUCTURE_PAYLOAD_FLAG_NA for the flag."""
STRUCTURE_PAYLOAD_OFFLOADS_NOTHING = (
    "these runs offload nothing: P_2* - P_ref is the payload change at the full load, not a "
    "propellant saving"
)
"""Printed in the payload cases' heading (they sit under the propellant-saved section)."""
STRUCTURE_ELEMENT_HOW: dict[str, str] = {
    INTERSTAGE: (
        "mass-estimating relation m_is ((N_push / N_env)^n - 1)+ on the upper-stack load, "
        "scaled by the Gerard exponent n over the pad envelope's N_env (an assumption, design "
        "4.2.4; no station envelope)"
    ),
    THRUST_STRUCTURE: (
        "thrust-structure relation k_ts max(0, F_peak + T - (1 + margin) T_max), T the thrust "
        "at the push's peak (design 4.2.3; no station envelope)"
    ),
}
"""How the element table's relation rows were sized, by element name (``_element_how``),
when the element is in the case's load path (the thrust structure under entry
thrust_structure); every other element but the ring is a station sizing over the pad
envelope."""
STRUCTURE_ELEMENT_STATION_HOW = "station sizing over the pad envelope"
STRUCTURE_ELEMENT_RING_HOW = "the ring frame: new hardware sized in closed form, no envelope credit"
STRUCTURE_ELEMENT_NOT_IN_PATH: dict[str, str] = {
    ENTRY_AFT_RING: (
        "not in the load path on entry aft_ring (the skirt and the ring carry the push; 0 by "
        "construction, not a sizing)"
    ),
    ENTRY_THRUST_STRUCTURE: (
        "not in the load path on entry thrust_structure (no ring frame; 0 by construction, "
        "not a sizing)"
    ),
}
"""What the element table says of the thrust structure under entry aft_ring and of the ring
frame under entry thrust_structure (review H-S3B-P3-06: never a relation the entry does not
apply), keyed by the entry that leaves the element unloaded."""
STRUCTURE_SETS_APPLICABILITY = (
    "the sets behind the ends above are the extremes in dm the search found, sizing only, at "
    "that one push; each x* above is this experiment's own solve with that set; a case whose "
    "push is not the search's (another variant, stroke, drive, start, vehicle or offload) "
    "reads its set as the headline's sets applied to this push, not as this push's extreme "
    "(design 4.2.6)"
)
"""The applicability line under the band lines (design 4.2.6: other pushes get central
solves and sizing-only band estimates labelled "the headline's sets"; the x* on a band line
is always a solve of this experiment, the set behind it the search's)."""
STRUCTURE_LAYER2_ROWS_LABEL = "design-axis rows (layer 2) flown on a set"
"""The line naming every structural case that moves a design axis off the headline (a
margin, a cap, another dynamic mode, overrides; their x* beside the set they move; such a
case is never a band end, ``_layer2_line``)."""
STRUCTURE_SETTINGS_ROWS_LABEL = "settings rows (the entry path or the sizing basis moved) on a set"
"""The line naming every physics- or outer-set case kept off its band for moving only the
entry path or the sizing basis (design 4.2.6: rows, not band; ``_settings_rows_line``)."""


def structure_overrides_text(overrides: Any) -> str | None:
    """A case's design-axis overrides as one cell: ``<path> <value>; ...`` (paths sorted,
    values as the file states them), ``none`` for an empty mapping, None for a value that
    is not a mapping (a failed record, or none recorded)."""
    if not isinstance(overrides, Mapping):
        return None
    if not overrides:
        return "none"
    return "; ".join(f"{path} {value!r}" for path, value in sorted(overrides.items()))


def structure_axis_departures(record: Mapping[str, Any]) -> list[str]:
    """What a structural record moves off the headline on the design axes (D-SP7-18,
    design 4.2.6), as short texts: ``margin <m>`` (a margin above 0), ``cap <c> g0`` (an
    envelope cap), ``dynamic <mode>`` (a mode other than STRUCTURE_HEADLINE_DYNAMIC) and
    ``overrides <path value; ...>``; the margin and the cap never count on an outer set,
    which records its own (STRUCTURE_OUTER_SETS). Empty for a case at the headline's
    axes."""
    out: list[str] = []
    name = record.get("structure_set")
    if name not in STRUCTURE_OUTER_SETS:
        margin = record.get("structure_margin")
        if _is_finite_number(margin) and float(margin) != 0.0:
            out.append(f"margin {float(margin):g}")
        cap = record.get("structure_envelope_cap_g")
        if _is_finite_number(cap):
            out.append(f"cap {float(cap):g} g0")
    dynamic = record.get("structure_dynamic")
    if dynamic is not None and dynamic != STRUCTURE_HEADLINE_DYNAMIC:
        out.append(f"dynamic {dynamic}")
    overrides = record.get("structure_overrides")
    if isinstance(overrides, Mapping) and overrides:
        out.append(f"overrides {structure_overrides_text(overrides)}")
    return out


def structure_row_departures(record: Mapping[str, Any]) -> list[str]:
    """What a structural record moves off the headline among the "rows, not band"
    settings of design 4.2.6 that are not design axes: ``entry <path>`` (an entry other
    than the aft ring) and ``sizing <basis>`` (a basis other than flown; a structure
    payload case is always a full-load sizing, the payload form's own basis, so it is
    not a departure there). Empty at the headline's entry and sizing."""
    out: list[str] = []
    entry = record.get("structure_entry")
    if entry is not None and entry != ENTRY_AFT_RING:
        out.append(f"entry {entry}")
    sizing = record.get("structure_sizing")
    payload_case = record.get("kind") == STRUCTURE_PAYLOAD_RECORD_KIND
    if sizing is not None and sizing != STRUCTURE_SIZING_FLOWN and not payload_case:
        out.append(f"sizing {sizing}")
    return out


def structure_is_band_end(record: Mapping[str, Any]) -> bool:
    """Whether a structural record is an end of its set's band (D-SP7-18, design 4.2.6):
    a case on a physics or an outer set at the headline settings (no design-axis
    departure, ``structure_axis_departures``, and no entry or sizing departure,
    ``structure_row_departures``); the plausibility-scaled twin of an end is an end too
    (D-SP7-41 prints it beside the unscaled one). A central case is never one."""
    name = record.get("structure_set")
    if name not in STRUCTURE_SET_NAMES:
        return False
    return not structure_axis_departures(record) and not structure_row_departures(record)


def structure_layer_label(record: Mapping[str, Any]) -> str:
    """The layer and set of a structural record (D-SP7-18, design 4.2.6): at the headline
    settings ``<layer label>: <set>`` by STRUCTURE_LAYER_LABELS (the central layer-1 label
    only for the central set at the headline settings); for a case that moves a design
    axis (``structure_axis_departures``: a margin, a cap, another dynamic mode, overrides)
    ``design axis (layer 2): <set> at margin m, cap c g0, dynamic d with overrides <path
    value; ...>`` (the set alone would present the sizing as the set's own, D-SP7-43);
    for a case that moves only the entry path or the sizing basis
    (``structure_row_departures``) ``<layer label>, a row, not a band end (entry e, sizing
    s): <set>``; a design-axis case that also moves those names them after its axes; n/a
    without a set."""
    name = record.get("structure_set")
    if name is None:
        return "n/a"
    axes = structure_axis_departures(record)
    rows = structure_row_departures(record)
    if axes:
        moved = [a for a in axes if not a.startswith("overrides ")]
        overrides = [a for a in axes if a.startswith("overrides ")]
        label = f"{STRUCTURE_OVERRIDES_LAYER}: {name}"
        if moved:
            label += f" at {', '.join(moved)}"
        if overrides:
            label += f" with {overrides[0]}"
        if rows:
            label += f"; {', '.join(rows)} ({STRUCTURE_ROW_NOT_BAND})"
        return label
    base = STRUCTURE_LAYER_LABELS.get(str(name), str(name))
    if rows:
        return f"{base}, {STRUCTURE_ROW_NOT_BAND} ({', '.join(rows)}): {name}"
    return f"{base}: {name}"


def structure_settings_text(record: Mapping[str, Any]) -> str:
    """Every departure of a record from the headline settings in one phrase (the axes,
    then the entry and sizing), or "the headline settings" when there is none."""
    moved = [*structure_axis_departures(record), *structure_row_departures(record)]
    return ", ".join(moved) if moved else "the headline settings"


def _structure_cell(record: Mapping[str, Any], fmt: str, path: str) -> str:
    """One cell of the Structure case table: ``structure_kind`` (modelled or penalty),
    ``structure_layer`` (``structure_layer_label``), ``structure_overrides`` (the
    overrides as text, none, or n/a), ``plausibility_factor`` (the end's factor on a
    physics band end, "n/a (not a band end)" on any other set, n/a on a penalty row),
    ``dm1`` (dm - dm2), ``MN`` (newtons in MN), ``xstar`` (tonnes) and ``xstar_pct``
    (percent of the stage-1 load), both STRUCTURE_NO_OFFLOAD_CELL for a no_offload solve
    (D-SP7-32), ``structure_flags`` (the fired flags' names, or none), ``payload_run``
    and ``payload_flag`` (a payload case's run and flag; STRUCTURE_PAYLOAD_NOT_WRITTEN and
    STRUCTURE_PAYLOAD_FLAG_NA when its P_2* search failed); every other format as
    ``_offload_cell``."""
    if fmt == "structure_kind":
        return (
            STRUCTURE_KIND_MODELLED if record.get("structure_charged") else STRUCTURE_KIND_PENALTY
        )
    if fmt == "structure_layer":
        return structure_layer_label(record)
    if fmt == "plausibility_factor":
        if not record.get("structure_charged"):
            return "n/a"
        if record.get("structure_set") not in STRUCTURE_PHYSICS_SETS:
            return "n/a (not a band end)"
        return _offload_cell(record, "num", path)
    if fmt == "payload_run":
        if record.get("run") is None and _payload_search_failed(record):
            return STRUCTURE_PAYLOAD_NOT_WRITTEN
        return _offload_cell(record, "text", path)
    if fmt == "payload_flag":
        if record.get("unconverged") is None and _payload_search_failed(record):
            return STRUCTURE_PAYLOAD_FLAG_NA
        return _offload_cell(record, "text", path)
    if fmt == "structure_overrides":
        if not record.get("structure_charged"):
            return "n/a"
        text = structure_overrides_text(record.get("structure_overrides"))
        return "n/a" if text is None else text
    if fmt == "dm1":
        dm, dm2 = record.get("structure_dm_kg"), record.get("structure_dm_stage2_kg")
        if not _is_finite_number(dm) or not _is_finite_number(dm2):
            return "n/a"
        return _fmt(float(dm) - float(dm2))
    if fmt == "MN":
        value = _dig(record, path)
        return _fmt(float(n_to_mn(float(value)))) if _is_finite_number(value) else "n/a"
    if fmt in ("xstar", "xstar_pct"):
        if record.get("status") == NO_OFFLOAD_STATUS:
            return STRUCTURE_NO_OFFLOAD_CELL
        return _offload_cell(record, "t" if fmt == "xstar" else "pct", path)
    if fmt == "structure_flags":
        text = structure_flags_text(record)
        return "n/a" if text is None else text
    return _offload_cell(record, fmt, path)


def structure_flags_text(record: Mapping[str, Any]) -> str | None:
    """The fired structure flags of a structural record as one cell: their names
    "; "-joined, ``none`` when none fired, STRUCTURE_FLAGS_NOT_SIZED when the solve found
    no x* (``structure_dm_kg`` None: no sizing at x*, so no flag was evaluated), None
    (n/a) when the record carries no flag list; shared by the Structure case table and
    the sweep index's ``structure_flags`` column."""
    flags = record.get("structure_flags")
    if not isinstance(flags, list):
        return None
    if record.get("structure_dm_kg") is None and "structure_dm_kg" in record:
        return STRUCTURE_FLAGS_NOT_SIZED
    fired = [str(f.get("name")) for f in flags if isinstance(f, Mapping) and f.get("fired")]
    return "; ".join(fired) if fired else "none"


STRUCTURE_MODEL_NAME = "a first-order station sizing of the push load"
"""The model's name wherever a modelled structural mass is worded (SP7 step S3a; every
reader says the same: the summary's block caveat, the replay and scene caveats, the scene
frame's footer, the animation's footnote)."""
STRUCTURE_ESTIMATE_TEXT = (
    "a first-order estimate with its stated ranges, not a detailed structural design"
)
"""How every modelled-structure sentence ends (design 4.5): what the mass is and is not."""
STRUCTURE_NO_SIZING_TEXT = "no sizing at x* (the solve found no x*)"
"""``modelled_mass_text`` of a structural record whose solve found no x* (its dm None)."""
STRUCTURE_NO_FLAG_TEXT = "no structure flag fired"
STRUCTURE_FLAGS_NOT_RECORDED_TEXT = "structure flags not recorded"
"""What ``modelled_structure_text`` says of a record that carries no flag list
(``structure_flags_text`` None; fix round 2, N2-06): never STRUCTURE_NO_FLAG_TEXT, which
would read an unrecorded list as clean."""


def structure_push_is_flown(record: Mapping[str, Any]) -> bool:
    """Whether a structural case record's push was flown (a linear motor, SP7 step S4b):
    charged and sized at its x* (``structure_dlf`` recorded: a search_failed case records
    every value at x* null, its ramp cost included, whatever its drive; review round 2,
    C-P2-01 and H-P2-01), with its ramp cost recorded as null (constant_accel's analytic
    push, once sized, always records a number, 0 outside rise_time)."""
    return (
        bool(record.get("structure_charged"))
        and record.get("structure_dlf") is not None
        and "structure_ramp_cost_rel" in record
        and record["structure_ramp_cost_rel"] is None
    )


def structure_charged(record: Mapping[str, Any]) -> bool:
    """Whether a record (a case, arm, payload-case or sweep-point record, or a run's own
    metrics record) charges a modelled structural mass: ``structure_charged`` is True
    (the run-level key of D-SP7-22, written only on a structural run). The one test every
    reader makes before wording the modelled branch (SP7 step S3a)."""
    return record.get("structure_charged") is True


def structure_run_record(
    record: Mapping[str, Any], offload: Mapping[str, Any] | None, name: str
) -> Mapping[str, Any]:
    """A run's own metrics record as every per-run reader words its structure (final
    clean-up, N3a-03): with ``kind`` STRUCTURE_PAYLOAD_RECORD_KIND when the offload
    record's ``structure_payload_cases`` names the run ``name`` (a case's ``run``), else
    the record as it is. A payload case's run carries the run-level keys
    (``sim.STRUCTURE_RECORD_KEYS``: structure_sizing full_load) but no kind, so without
    it ``structure_row_departures`` would word the run as a full-load-sizing row, "a
    row, not a band end (sizing full_load)", while the block caveat, worded from the
    case record, calls the same case by its set; the replay and scene caveats, the scene
    frame's note and the animation's and video's footnote read it through this."""
    for case in (offload or {}).get("structure_payload_cases") or []:
        if isinstance(case, Mapping) and case.get("run") == name:
            return {**record, "kind": STRUCTURE_PAYLOAD_RECORD_KIND}
    return record


def offload_charges_modelled(offload: Mapping[str, Any] | None) -> bool:
    """Whether an offload record charges a modelled structural mass anywhere (fix round 2,
    H-S3a-P2-03): a ``structure_inputs`` record (a block with a structure block), or a
    record of ``cases``, ``structure_payload_cases`` or ``sensitivity`` that is
    ``structure_charged``. The replay caveat drops SP1's program-level "no structural
    model exists" of a penalty row for any such directory, so a page never carries it
    beside the directory's block caveat that names the model."""
    if not offload:
        return False
    if isinstance(offload.get("structure_inputs"), Mapping):
        return True
    return any(
        isinstance(c, Mapping) and structure_charged(c)
        for key in ("cases", "structure_payload_cases", "sensitivity")
        for c in offload.get(key) or []
    )


def structure_band_ends(inputs: Mapping[str, Any] | None) -> tuple[float, float] | None:
    """The physics band's ends in dm [kg] at the structure file's headline push from a
    block's ``structure_inputs`` record (``sim.offload_structure_inputs``: the structure
    file's frozen sets, each set's polish of the headline search, structure.SEARCH_HEADLINE,
    its dm after polish; the push is the one the sets' ``method`` names,
    ``structure_band_push``): (low-mass end, high-mass end), unscaled; None without a sets
    record or a headline polish on either physics set (a file without frozen sets, or
    synthetic sets without polish): the readers then say nothing of the band. Sizing-only
    numbers at one push, never this experiment's x*."""
    sets = None if inputs is None else inputs.get("sets")
    if not isinstance(sets, Mapping):
        return None
    ends = []
    for name in (SET_PHYSICS_LOW, SET_PHYSICS_HIGH):
        item = sets.get(name)
        polish = item.get("polish") if isinstance(item, Mapping) else None
        dm = None
        for entry in polish if isinstance(polish, list) else []:
            if isinstance(entry, Mapping) and entry.get("search") == SEARCH_HEADLINE:
                dm = entry.get("dm_after_kg")
        if not _is_finite_number(dm):
            return None
        ends.append(float(dm))
    return ends[0], ends[1]


def structure_band_factors(inputs: Mapping[str, Any] | None) -> tuple[float, float] | None:
    """The plausibility rule's factors on the physics band's (low-mass end, high-mass end)
    from a block's ``structure_inputs`` record (``plausibility``: ``low_mass_end_factor``
    and ``high_mass_end_factor``, the rule's table on the experiment's own pad envelope at
    the central coefficients, D-SP7-33); None when either is not recorded."""
    p = None if inputs is None else inputs.get("plausibility")
    if not isinstance(p, Mapping):
        return None
    lo, hi = p.get("low_mass_end_factor"), p.get("high_mass_end_factor")
    if not (_is_finite_number(lo) and _is_finite_number(hi)):
        return None
    return float(lo), float(hi)


STRUCTURE_SETS_PUSH_PATTERN = re.compile(
    r"at\s+the\s+headline\s+push\s+of\s+(?P<experiment>[^\s']+)'s\s+(?P<variant>\S+)\s+"
    r"\(the\s+analytic\s+constant_accel\s+case\s+at\s+a\s+stage-1\s+offload\s+of\s+"
    r"(?P<offload>[-+0-9.eE]+)\s+kg"
)
"""How the frozen sets' ``method`` names the push they were searched at
(sim.structure_search_method writes it: "at the headline push of <experiment>'s <variant>
(the analytic constant_accel case at a stage-1 offload of <x> kg ..."; a test reads both
committed structure files and the writer's own sentence with it)."""
STRUCTURE_BAND_PUSH_FALLBACK = "the push its sets.method names"
"""What the band clause names as the push when the sets' ``method`` does not name one in
the writer's form (``structure_band_push`` None: a synthetic record, a hand-written
method): never a push the record does not state."""


def structure_band_push(inputs: Mapping[str, Any] | None) -> tuple[str, str, float] | None:
    """(experiment, variant, stage-1 offload [kg]) of the push the structure file's frozen
    sets were searched at, read from a block's ``structure_inputs.sets.method``
    (STRUCTURE_SETS_PUSH_PATTERN; final clean-up, N3a-02): the gate file's is
    silo_offload_2d's silo_cold at SP1's headline offload, the README-loads file's
    silo_offload_2d_readme's silo_cold at that fork's own bridge offload, so the push is
    never one constant. None when the record holds no method or it names no push in the
    writer's form."""
    sets = None if inputs is None else inputs.get("sets")
    method = sets.get("method") if isinstance(sets, Mapping) else None
    if not isinstance(method, str):
        return None
    found = STRUCTURE_SETS_PUSH_PATTERN.search(method)
    if found is None:
        return None
    try:
        offload_kg = float(found["offload"])
    except ValueError:
        return None
    return found["experiment"], found["variant"], offload_kg


def structure_band_push_text(inputs: Mapping[str, Any] | None) -> str:
    """The push the band clause names (fix round 3, H-S3a-P3-05; final clean-up, N3a-02):
    "silo_offload_2d_readme's silo_cold at a stage-1 offload of 36,006 kg, per its
    sets.method" from the record's own method (``structure_band_push``), so a reader can
    check which push and which structure file it means; STRUCTURE_BAND_PUSH_FALLBACK when
    the method names none."""
    push = structure_band_push(inputs)
    if push is None:
        return STRUCTURE_BAND_PUSH_FALLBACK
    experiment, variant, offload_kg = push
    return (
        f"{experiment}'s {variant} at a stage-1 offload of {offload_kg:,.0f} kg, "
        "per its sets.method"
    )


STRUCTURE_BAND_SCOPE_TEXT = (
    "both ends are sizing-only numbers from the frozen sets, not this run's band"
)
"""What the band clause says of the ends it quotes (fix rounds 2 and 3, H-S3a-P2-02 and
H-S3a-P3-05): the frozen sets' numbers at the structure file's headline push
(``structure_band_push_text``), never this run's own band; followed by how the run itself
is sized (``structure_band_sized_text``), which the headline's is not."""
STRUCTURE_BAND_SIZED_FLOWN = "the run is sized at its own push and offload"
"""How a ``flown`` structural run is sized, after STRUCTURE_BAND_SCOPE_TEXT: the stack it
flies at its own offload (a solved case's x*, an imposed case's offload)."""
STRUCTURE_BAND_SIZED_FULL_LOAD = "the run is sized at its own push on the full load (x = 0)"
"""How a ``full_load`` structural run is sized, after STRUCTURE_BAND_SCOPE_TEXT (final
clean-up, N3a-01): a full-load-sizing row and every structure payload case size the
full-load start vehicle (sim's ``full_load`` basis: x = 0, whatever offload the run flies;
config forces it on every payload case), never at an offload of their own."""


def structure_band_sized_text(sizing: Any) -> str:
    """How the run is sized, from its record's ``structure_sizing`` (final clean-up,
    N3a-01): STRUCTURE_BAND_SIZED_FULL_LOAD for ``full_load``, else
    STRUCTURE_BAND_SIZED_FLOWN."""
    if sizing == STRUCTURE_SIZING_FULL_LOAD:
        return STRUCTURE_BAND_SIZED_FULL_LOAD
    return STRUCTURE_BAND_SIZED_FLOWN


def _band_end_text(dm_kg: float, factor: float | None, trigger: str | None = None) -> str:
    """'3,677 kg', or with a plausibility factor other than 1 '3,677 kg unscaled (2,717 kg
    after the plausibility rule's factor 0.739)' (D-SP7-41: the two side by side), with
    ``trigger`` (the rule's trigger, ``_plausibility_trigger_text``) inside that
    parenthesis when given (fix round 3, S3A-NUM-05: the trigger sits with the end the
    rule scales)."""
    if factor is None or factor == 1.0:
        return f"{dm_kg:,.0f} kg"
    note = f"{dm_kg * factor:,.0f} kg after the plausibility rule's factor {_fmt(factor)}"
    if trigger is not None:
        note += f"; {trigger}"
    return f"{dm_kg:,.0f} kg unscaled ({note})"


def _plausibility_trigger_text(inputs: Mapping[str, Any]) -> str | None:
    """The plausibility rule's trigger in a clause (D-SP7-41: "with the trigger stated"):
    'the rule fires at M_model / R = 1.76, stage1.lox_barrel carrying 71 % of M_model in
    the pad envelope'; None when the ratio is not recorded."""
    p = inputs.get("plausibility")
    if not isinstance(p, Mapping) or not _is_finite_number(p.get("ratio")):
        return None
    text = f"the rule fires at M_model / R = {float(p['ratio']):.3g}"
    d = p.get("dominant")
    if isinstance(d, Mapping) and _is_finite_number(d.get("share")):
        share = float(to_percent(float(d["share"])))
        text += f", {d.get('element')} carrying {share:.0f} % of M_model in the pad envelope"
    return text


def structure_band_text(
    inputs: Mapping[str, Any] | None, scaled: bool = False, sizing: Any = None
) -> str | None:
    """The band clause of the modelled-structure wording (SP7 step S3a; fix rounds 2 and
    3, H-S3a-P2-02, H-S3a-P3-05 and S3A-NUM-05): the physics band's ends at the structure
    file's headline push, named from the record's sets.method (``structure_band_push_text``;
    ``structure_band_ends``), each
    end beside its value after the plausibility rule's factor when that factor is not 1
    (``structure_band_factors``, D-SP7-41: unscaled and scaled side by side), the rule's
    trigger (``_plausibility_trigger_text``) inside the parenthesis of the one end it
    scales, or after both ends "on both ends" when it scales both; a record the rule
    ``scaled`` whose block records no factors says both ends are before the rule's factor
    (fix round 1, H-S3a-03); then, as a clause of its own, STRUCTURE_BAND_SCOPE_TEXT and
    how the run is sized by its record's ``sizing`` (``structure_band_sized_text``: at
    its own push and offload, or on the full load at x = 0; final clean-up, N3a-01). None
    without the ends. Never "bounds"."""
    ends = structure_band_ends(inputs)
    if ends is None:
        return None
    assert inputs is not None  # structure_band_ends found ends in it
    factors = structure_band_factors(inputs)
    lo_f, hi_f = (None, None) if factors is None else factors
    trigger = _plausibility_trigger_text(inputs) if factors is not None else None
    lo_scaled = lo_f is not None and lo_f != 1.0
    hi_scaled = hi_f is not None and hi_f != 1.0
    both = lo_scaled and hi_scaled
    lo = _band_end_text(ends[0], lo_f, None if both else trigger)
    hi = _band_end_text(ends[1], hi_f, None if both else trigger)
    text = (
        f"the physics band's ends at the structure file's headline push "
        f"({structure_band_push_text(inputs)}) are dm {lo} and {hi}"
    )
    if both and trigger is not None:
        text += f"; {trigger}, on both ends"
    elif factors is None and scaled:
        text += "; both ends are before the plausibility rule's factor"
    return f"{text}; {STRUCTURE_BAND_SCOPE_TEXT}: {structure_band_sized_text(sizing)}"


def release_flag_pressures(record: Mapping[str, Any]) -> tuple[float, float] | None:
    """(the pad's MECO, the push) stage-2 LOX bottom gauge pressures [Pa] of a structural
    record's release flag (structure.FLAG_RELEASE_UNLOAD's ``meco_stage2_lox_...`` and
    ``stage2_lox_bottom_pressure_min_gauge_pa``) when the flag fired with a stage-1 column
    separating at the push (its ``lox_`` or ``rp1_bottom_pressure_min_abs_pa`` below 0);
    None otherwise (the flag not fired, fired for the dome's reverse pressure or the upper
    stack alone, or its numbers not recorded). D-SP7-39: the same single-mode step
    treatment is applied to the pad's own MECO shutdown, whose full stage-2 tanks it
    takes through the same comparison."""
    flags = record.get("structure_flags")
    for flag in flags if isinstance(flags, list) else []:
        if not (isinstance(flag, Mapping) and flag.get("name") == FLAG_RELEASE_UNLOAD):
            continue
        v = flag.get("values")
        if not flag.get("fired") or not isinstance(v, Mapping):
            return None
        stage1 = [v.get(f"{t}_bottom_pressure_min_abs_pa") for t in ("lox", "rp1")]
        if not any(_is_finite_number(x) and float(x) < 0.0 for x in stage1):
            return None
        meco = v.get("meco_stage2_lox_bottom_pressure_min_gauge_pa")
        push = v.get("stage2_lox_bottom_pressure_min_gauge_pa")
        if not (_is_finite_number(meco) and _is_finite_number(push)):
            return None
        return float(meco), float(push)
    return None


def _kpa(pressure_pa: float) -> str:
    """'-199.9 kPa' of a pressure [Pa]."""
    return f"{float(pa_to_kpa(pressure_pa)):.1f} kPa"


def release_flag_comparison_text(record: Mapping[str, Any]) -> str | None:
    """D-SP7-39's comparison beside a fired release flag (fix round 2, H-S3a-P2-01): the
    stage-1 column separation it names comes from the single-mode step treatment, and the
    pad's own MECO shutdown under that treatment takes the full stage-2 LOX column to the
    pressure printed (gauge; MECO's ambient is taken as 0) against the push's on the same
    tank; when MECO's value is below 0 that it separates there too, so the separation is
    not specific to the push; else that it does not. None without
    ``release_flag_pressures``."""
    pair = release_flag_pressures(record)
    if pair is None:
        return None
    meco, push = pair
    head = (
        "the release flag's stage-1 column separation comes from the single-mode step "
        "treatment, which the pad's own MECO shutdown is put through too: there the full "
        f"stage-2 LOX column's bottom is at {_kpa(meco)} gauge against {_kpa(push)} at the "
        "push"
    )
    if meco < 0.0:
        return (
            f"{head}, so it separates on the pad as well and the separation is not "
            "specific to the push (D-SP7-39)"
        )
    return f"{head}, so on the pad it does not separate (D-SP7-39)"


def release_flag_comparison_short(record: Mapping[str, Any]) -> str | None:
    """The animation footnote's form of ``release_flag_comparison_text`` (no comma or
    semicolon, so it sits inside the footnote's clause): 'D-SP7-39: the pad's own MECO
    separates stage 2's LOX column too under the same step treatment', or '... keeps
    stage 2's LOX column under the same step treatment'; None without
    ``release_flag_pressures``."""
    pair = release_flag_pressures(record)
    if pair is None:
        return None
    what = "separates stage 2's LOX column too" if pair[0] < 0.0 else "keeps stage 2's LOX column"
    return f"D-SP7-39: the pad's own MECO {what} under the same step treatment"


def plausibility_scale_text(record: Mapping[str, Any]) -> str | None:
    """'scaled x0.845549 by the plausibility rule' for a structural record whose dm carries
    the plausibility rule's factor (``structure_plausibility_scaled`` True; the factor
    ``structure_plausibility_factor``, n/a when unrecorded); None otherwise. The case
    note's and the app headline's ``replay.structure_clause`` say it beside the mass (fix
    round 3, H-S3a-P3-03), as the caveat's ``modelled_structure_text`` does."""
    if record.get("structure_plausibility_scaled") is not True:
        return None
    factor = record.get("structure_plausibility_factor")
    shown = _fmt(factor) if _is_finite_number(factor) else "n/a"
    return f"scaled x{shown} by the plausibility rule"


def modelled_mass_split_text(record: Mapping[str, Any]) -> str | None:
    """'stage 1 8,900.1 kg, stage 2 200.2 kg': the modelled mass of a structural record by
    stage, from ``structure_dm_kg`` (dm1 + dm2) and ``structure_dm_stage2_kg`` (dm1 the
    difference); None when either is unrecorded or not finite."""
    dm, dm2 = record.get("structure_dm_kg"), record.get("structure_dm_stage2_kg")
    if not (_is_finite_number(dm) and _is_finite_number(dm2)):
        return None
    return f"stage 1 {float(dm) - float(dm2):,.1f} kg, stage 2 {float(dm2):,.1f} kg"


def modelled_mass_text(record: Mapping[str, Any], *, named: bool = True) -> str:
    """The modelled mass of a structural record by stage: '9,100.3 kg of modelled
    structural mass (stage 1 8,900.1 kg, stage 2 200.2 kg)' (``named``; without it
    '9,100.3 kg (stage 1 ..., stage 2 ...)', for a sentence that has already said what
    the mass is) from ``modelled_mass_split_text``; STRUCTURE_NO_SIZING_TEXT when the dm
    is None (a solve that found no x*), with 'a modelled structural mass with' before
    it when named; the total alone when the stage-2 share is unrecorded."""
    dm = record.get("structure_dm_kg")
    if not _is_finite_number(dm):
        return (
            f"a modelled structural mass with {STRUCTURE_NO_SIZING_TEXT}"
            if named
            else (STRUCTURE_NO_SIZING_TEXT)
        )
    text = f"{float(dm):,.1f} kg" + (" of modelled structural mass" if named else "")
    split = modelled_mass_split_text(record)
    return text if split is None else f"{text} ({split})"


def modelled_structure_text(
    record: Mapping[str, Any], inputs: Mapping[str, Any] | None = None
) -> str:
    """The modelled-structure wording of one structural record (SP7 step S3a, D-SP7-22;
    design 4.5), the one sentence core every reader quotes: the mass by stage
    (``modelled_mass_text``), the model (STRUCTURE_MODEL_NAME), the layer and set
    (``structure_layer_label``), the file (``structure_file``), the physics band's ends
    at the structure file's headline push, named, where the block's ``structure_inputs``
    record them, unscaled beside scaled with the rule's trigger when the plausibility rule
    fires on an end, and that they are sizing-only numbers, not this run's band, with how
    the record itself is sized (``structure_band_text``; nothing otherwise; fix rounds 1
    to 3, H-S3a-03, H-S3a-P2-02 and H-S3a-P3-05; final clean-up, N3a-01), when the
    plausibility rule scaled the dm its factor (``structure_plausibility_scaled``,
    ``structure_plausibility_factor``), the run's own fired flags by name
    (``structure_flags_text``; STRUCTURE_NO_FLAG_TEXT when none fired,
    STRUCTURE_FLAGS_NOT_SIZED for a solve without an x*, STRUCTURE_FLAGS_NOT_RECORDED_TEXT
    for a record without a flag list), beside a fired release flag that separates a
    stage-1 column D-SP7-39's comparison with the pad's own MECO
    (``release_flag_comparison_text``, fix round 2, H-S3a-P2-01), and
    STRUCTURE_ESTIMATE_TEXT. Never "assumed", never "bounds"."""
    bits = [
        f"{modelled_mass_text(record, named=False)}: {STRUCTURE_MODEL_NAME} (layer and set "
        f"{structure_layer_label(record)}; {record.get('structure_file')})"
    ]
    scaled = bool(record.get("structure_plausibility_scaled"))
    band = structure_band_text(inputs, scaled, record.get("structure_sizing"))
    if band is not None:
        bits.append(band)
    if scaled:
        factor = record.get("structure_plausibility_factor")
        bits.append(
            "the dm carries the plausibility rule's factor "
            f"{_fmt(factor) if _is_finite_number(factor) else 'n/a'} (D-SP7-33)"
        )
    fired = structure_flags_text(record)
    if fired is None:
        bits.append(STRUCTURE_FLAGS_NOT_RECORDED_TEXT)
    elif fired == "none":
        bits.append(STRUCTURE_NO_FLAG_TEXT)
    elif fired == STRUCTURE_FLAGS_NOT_SIZED:
        bits.append(f"structure flags {fired}")
    else:
        bits.append(f"structure flags fired: {fired} (their numbers are in structure_flags)")
        release = release_flag_comparison_text(record)
        if release is not None:
            bits.append(release)
    bits.append(STRUCTURE_ESTIMATE_TEXT)
    return "; ".join(bits)


def _payload_search_failed(record: Mapping[str, Any]) -> bool:
    """Whether a payload case's second pass found no P* (its ``payload_kg`` is not a
    finite number while its first pass did: ``dm_1_kg`` recorded)."""
    return "dm_1_kg" in record and not _is_finite_number(record.get("payload_kg"))


def _structure_table(
    records: Sequence[Mapping[str, Any]], rows: Sequence[OffloadRow], label: str
) -> str:
    """A table with one row per OffloadRow (``_structure_cell``) and one column per
    record."""
    header = ["quantity", *(str(r.get(label)) for r in records)]
    body = [[row[0], *(_structure_cell(r, row[1], row[2]) for r in records)] for row in rows]
    return _table(header, body)


def structure_cases_of(record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """The structural cases of an offload record (``structure_charged``) and SP1's penalty
    rows of the same experiment (``assumed_penalty``), in the block's order, skipped cases
    left out."""
    return [
        c
        for c in record.get("cases") or []
        if not c.get("skipped") and (c.get("structure_charged") or c.get("assumed_penalty"))
    ]


STRUCTURE_SETTINGS_NAMES: tuple[str, ...] = (
    "set",
    "dynamic",
    "entry",
    "margin",
    "cap",
    "overrides",
    "plausibility-scaled",
)
"""The settings ``structure_settings_of`` compares, in order (the sizing basis left out:
a payload case is always a full-load sizing, read beside a flown case's full-load rows)."""


def structure_settings_of(record: Mapping[str, Any]) -> tuple[Any, ...]:
    """The settings that make two structural records comparable (STRUCTURE_SETTINGS_NAMES):
    the set, dynamic mode, entry, margin, cap, overrides (as text) and whether the dm is
    plausibility-scaled."""
    return (
        record.get("structure_set"),
        record.get("structure_dynamic"),
        record.get("structure_entry"),
        record.get("structure_margin"),
        record.get("structure_envelope_cap_g"),
        structure_overrides_text(record.get("structure_overrides")),
        bool(record.get("structure_plausibility_scaled")),
    )


def _xstar_text(c: Mapping[str, Any]) -> str:
    """One band end's case: its x* in tonnes with the case name and status, a no_offload
    end as such (never "0 t", D-SP7-32), or a solve that found no x* (search_failed:
    ``offload_kg`` not finite) as "no x*" with its status, never a unit on an n/a
    (review NEW-H-01)."""
    if c.get("status") == NO_OFFLOAD_STATUS:
        return f"no offload ({c.get('name')}; the no_offload line below)"
    if not _is_finite_number(c.get("offload_kg")):
        return f"no x* ({c.get('name')}, status {c.get('status')})"
    return f"{_offload_cell(c, 't', 'offload_kg')} t ({c.get('name')}, status {c.get('status')})"


def _xstar_phrase(c: Mapping[str, Any]) -> str:
    """``_xstar_text`` for a row line (the layer-2 and settings-rows lines, where no "x*"
    precedes it): "x* 15 t (...)" for a solved case, and the bare "no offload (...)" or
    "no x* (...)" otherwise, so the line never reads "x* no x*"."""
    text = _xstar_text(c)
    if c.get("status") == NO_OFFLOAD_STATUS or not _is_finite_number(c.get("offload_kg")):
        return text
    return f"x* {text}"


def _band_end(cases: Sequence[Mapping[str, Any]]) -> str:
    """One end of a band from every band-end case of its set (``structure_is_band_end``;
    D-SP7-41: the unscaled and the plausibility-scaled ends side by side, each named): the
    unscaled cases' x* (several when the set ran as several cases, joined by "and"), then
    each plausibility-scaled case's x* with its factor; a set with a scaled case only says
    so (its x* is not the physics band's end); an unscaled end whose rule fired (its
    factor differs from 1) with no scaled twin says so with the factor, so the fired rule
    is never visible in the case table alone; STRUCTURE_NOT_FLOWN for no case."""
    if not cases:
        return STRUCTURE_NOT_FLOWN
    unscaled = [c for c in cases if not c.get("structure_plausibility_scaled")]
    scaled = [c for c in cases if c.get("structure_plausibility_scaled")]
    parts = []
    if unscaled:
        parts.append(" and ".join(_xstar_text(c) for c in unscaled))
    for c in scaled:
        factor = _fmt(c.get("structure_plausibility_factor"))
        if unscaled:
            parts.append(f"plausibility-scaled end: {_xstar_text(c)}, factor {factor}")
        else:
            parts.append(
                f"scaled only: {_xstar_text(c)}, factor {factor}; the unscaled end was not flown"
            )
    if not scaled:
        fired = [
            c.get("structure_plausibility_factor")
            for c in unscaled
            if _is_finite_number(c.get("structure_plausibility_factor"))
            and float(c["structure_plausibility_factor"]) != 1.0
        ]
        if fired:
            parts.append(
                f"the rule's factor on this end is {_fmt(fired[0])}; no plausibility-scaled "
                "case was flown"
            )
    return "; ".join(parts)


def _band_line(
    label: str,
    low: Sequence[Mapping[str, Any]],
    high: Sequence[Mapping[str, Any]],
    method: str,
) -> str:
    """One line of a band: its two ends, each named (``_band_end``: x* in tonnes with the
    case names, a no_offload end as such, a scaled end beside its unscaled one with the
    factor, an end the experiment did not fly as STRUCTURE_NOT_FLOWN; the ends are
    bracketed so a scaled end's factor is never read as running to the other end) and the
    method's label. Only a case at the headline settings is an end
    (``structure_is_band_end``): the caller leaves every other case out and names it on
    the layer-2 line or the settings-rows line (``structure_section``)."""
    return (
        f"- {label}: x* at the low-mass end [{_band_end(low)}]; at the high-mass end "
        f"[{_band_end(high)}]; the sets are {method}"
    )


def _layer2_line(cases: Sequence[Mapping[str, Any]]) -> str | None:
    """The line naming every structural case that moves a design axis off the headline
    (``structure_axis_departures``: a margin, a cap, another dynamic mode, overrides), with
    its base set, what it moves (and any entry or sizing departure) and its x*
    (``_xstar_phrase``: a no_offload end or a solve without an x* as such); None when none
    ran."""
    rows = [c for c in cases if structure_axis_departures(c)]
    if not rows:
        return None
    parts = [
        f"{c.get('name')} ({c.get('structure_set')} at {structure_settings_text(c)}): "
        f"{_xstar_phrase(c)}"
        for c in rows
    ]
    return f"- {STRUCTURE_LAYER2_ROWS_LABEL}, never a band end: " + "; ".join(parts)


def _settings_rows_line(cases: Sequence[Mapping[str, Any]]) -> str | None:
    """The line naming every physics- or outer-set case kept off its band for moving the
    entry path or the sizing basis alone (``structure_row_departures``, design 4.2.6: rows,
    not band), with its set, what it moves and its x* (``_xstar_phrase``); None when none
    ran (a central case is never on a band, so it is not named here)."""
    rows = [
        c
        for c in cases
        if c.get("structure_set") in STRUCTURE_SET_NAMES
        and structure_row_departures(c)
        and not structure_axis_departures(c)
    ]
    if not rows:
        return None
    parts = [
        f"{c.get('name')} ({c.get('structure_set')} at {structure_settings_text(c)}): "
        f"{_xstar_phrase(c)}"
        for c in rows
    ]
    return f"- {STRUCTURE_SETTINGS_ROWS_LABEL}, never a band end: " + "; ".join(parts)


def _no_offload_line(case: Mapping[str, Any], payload_cases: Sequence[Mapping[str, Any]]) -> str:
    """The line of a structural case whose solve ended no_offload (D-SP7-32: printed with
    its delta-v shortfall, the solver's ``dv_shortfall_mps`` at x = 0, and its payload
    deficit from the payload case of the same variant and settings
    (``structure_settings_of``) when one was flown, never as "0 t"); a payload case of
    the same set whose other settings differ is named with what differs, not quoted."""
    solve = case.get("solve") or {}
    shortfall = _fmt(solve.get("dv_shortfall_mps"))
    dm = _fmt(case.get("structure_dm_kg"))
    mine = structure_settings_of(case)
    candidates = [
        p for p in payload_cases if not p.get("skipped") and p.get("of") == case.get("of")
    ]
    same = [p for p in candidates if structure_settings_of(p) == mine]
    if same:
        p = same[0]
        deficit = (
            f"payload deficit at the full load {_signed(p.get('payload_delta_kg'))} kg "
            f"(P_2* - P_ref of structure payload case {p.get('name')}, the same set and settings)"
        )
    else:
        near = [p for p in candidates if p.get("structure_set") == case.get("structure_set")]
        if near:
            p = near[0]
            theirs = structure_settings_of(p)
            differs = [
                n for n, a, b in zip(STRUCTURE_SETTINGS_NAMES, mine, theirs, strict=True) if a != b
            ]
            deficit = (
                f"payload deficit at the full load {STRUCTURE_NOT_FLOWN} for these settings "
                f"(structure payload case {p.get('name')} is of the same set but differs in "
                f"{', '.join(differs)})"
            )
        else:
            deficit = (
                f"payload deficit at the full load {STRUCTURE_NOT_FLOWN} (no structure payload "
                "case of the same set and settings)"
            )
    return (
        f"- {case.get('name')}: no offload at P_ref: the full-load push carrying dm {dm} kg "
        f"falls short of P_ref by {shortfall} m/s of delta-v (the solver's dv_shortfall_mps "
        f"at x = 0); {deficit}"
    )


def _element_how(name: str, entry: Any) -> str:
    """How an element of the element table was sized, by its ``<stage>.<element>`` name
    and the case's load entry: the ring frame STRUCTURE_ELEMENT_RING_HOW under entry
    aft_ring and the thrust structure its relation (STRUCTURE_ELEMENT_HOW) under entry
    thrust_structure; whichever of the two the entry leaves out of the load path
    STRUCTURE_ELEMENT_NOT_IN_PATH (its 0 is by construction, not a sizing); the
    interstage its relation; every other element a station sizing."""
    element = name.split(".")[-1]
    if element == LOAD_RING:
        if entry is not None and entry != ENTRY_AFT_RING:
            return STRUCTURE_ELEMENT_NOT_IN_PATH[ENTRY_THRUST_STRUCTURE]
        return STRUCTURE_ELEMENT_RING_HOW
    if element == THRUST_STRUCTURE and entry == ENTRY_AFT_RING:
        return STRUCTURE_ELEMENT_NOT_IN_PATH[ENTRY_AFT_RING]
    return STRUCTURE_ELEMENT_HOW.get(element, STRUCTURE_ELEMENT_STATION_HOW)


def _element_table(case: Mapping[str, Any]) -> str:
    """The element table of a case: one row per element of ``structure_elements`` [kg]
    with how it was sized under the case's entry (``_element_how``: a station sizing over
    the pad envelope, the interstage's relation, the thrust structure's relation or "not
    in the load path"), the station-sized and relation elements first with their sum
    (``structure_closed_form_kg``), then the ring frame with its sum, then dm1 + dm2."""
    elements = case.get("structure_elements") or {}
    entry = case.get("structure_entry")
    sized = [(n, kg) for n, kg in elements.items() if not n.endswith(".load_ring")]
    ring = [(n, kg) for n, kg in elements.items() if n.endswith(".load_ring")]
    rows = [[n, _fmt(kg), _element_how(n, entry)] for n, kg in sized]
    rows.append(
        [
            "station-sized and relation elements, sum",
            _fmt(case.get("structure_closed_form_kg")),
            "",
        ]
    )
    rows += [[n, _fmt(kg), _element_how(n, entry)] for n, kg in ring]
    rows.append(["ring frame, sum", _fmt(case.get("structure_ring_kg")), ""])
    rows.append(["dm1 + dm2", _fmt(case.get("structure_dm_kg")), ""])
    return _table(["element (stage.element)", "dm [kg]", "how"], rows)


def _central_case_phrase(central: Mapping[str, Any]) -> str:
    """How the element table's heading and the plausibility trigger name the central case
    they quote: ``the central case <name>`` at the headline settings, else ``the
    central-set case <name> (<what it moves>; not the headline settings)`` (review
    H-S3B-P3-11: the fallback is never called the central case)."""
    moved = [*structure_axis_departures(central), *structure_row_departures(central)]
    if not moved:
        return f"the central case {central.get('name')}"
    return (
        f"the central-set case {central.get('name')} ({', '.join(moved)}; not the headline "
        "settings)"
    )


STRUCTURE_PAYLOAD_NO_FULL_LOAD = "no full_load row of the same variant and settings ran above"
"""What the payload cases' heading says of a payload case no full_load case of the same
variant and settings (``structure_settings_of``) stands beside."""


def _payload_beside(payload: Mapping[str, Any], structural: Sequence[Mapping[str, Any]]) -> str:
    """Which full_load case of the case table a payload case is read beside: ``<name>:
    <full_load cases of the same variant and settings>`` (``structure_settings_of``: the
    set, dynamic mode, entry, margin, cap, overrides and the plausibility factor's
    application; the sizing basis is full_load on both), else STRUCTURE_PAYLOAD_NO_FULL_LOAD
    (review H-S3B-P3-01: a quasi-static or a scaled payload case is never sent to a
    rise-time or an unscaled row)."""
    mine = structure_settings_of(payload)
    matches = [
        str(c.get("name"))
        for c in structural
        if c.get("structure_sizing") == STRUCTURE_SIZING_FULL_LOAD
        and c.get("of") == payload.get("of")
        and structure_settings_of(c) == mine
    ]
    beside = ", ".join(matches) if matches else STRUCTURE_PAYLOAD_NO_FULL_LOAD
    return f"{payload.get('name')}: {beside}"


def _plausibility_trigger(p: Mapping[str, Any], central: Mapping[str, Any] | None) -> str:
    """The plausibility rule's trigger in one computed line (D-SP7-41: "the ratio and its
    trigger"): where M_model / R lies against the band, the element carrying the largest
    share of M_model (``dominant`` of the record: its share, governing mode, load case
    and station in the envelope the rule reads) and the central case's own push
    increment on that element (or that no central case was flown)."""
    ratio, band = p.get("ratio"), p.get("band_fraction")
    d = p.get("dominant") or {}
    if not (_is_finite_number(ratio) and _is_finite_number(band)):
        return "- trigger: not recorded"
    r, b = float(ratio), float(band)
    if r > 1.0 + b:
        where = (
            f"lies above {1.0 + b:g} R, so the low-mass end's factor is "
            f"{_fmt(p.get('low_mass_end_factor'))}"
        )
    elif r < 1.0 - b:
        where = (
            f"lies below {1.0 - b:g} R, so the high-mass end's factor is "
            f"{_fmt(p.get('high_mass_end_factor'))}"
        )
    else:
        where = "lies inside the band, so neither factor fires"
    element = d.get("element")
    case_label = d.get("case_label")
    under = "the minimum gauge" if case_label is None else f"load case {case_label}"
    carries = (
        f"{element} carries {_fmt(float(to_percent(float(d.get('share')))))} % of M_model, "
        f"governed by {d.get('mode')} under {under} of the pad envelope at its thickest station "
        f"(z {_fmt(d.get('z_m'))} m)"
        if _is_finite_number(d.get("share"))
        else "the dominant element is not recorded"
    )
    if central is None:
        own = "no central case was flown, so its own push increment is not printed"
    else:
        kg = (central.get("structure_elements") or {}).get(str(element))
        own = f"its own push increment in {_central_case_phrase(central)}: {_fmt(kg)} kg"
    return f"- trigger: M_model / R = {_fmt(r)} {where}; {carries}; {own}"


def _plausibility_lines(inputs: Mapping[str, Any], central: Mapping[str, Any] | None) -> list[str]:
    """The plausibility table of ``structure_inputs`` (design 4.2.5): the element masses,
    M_model, R and its band (the edges printed from the record's band fraction, the file's
    ``heineman_band_fraction``), M/R, the factor on each end, the quantities printed
    beside, the rule and its trigger (``_plausibility_trigger``)."""
    p = inputs.get("plausibility") or {}
    band = p.get("band_fraction")
    lo = "n/a" if not _is_finite_number(band) else f"{1.0 - float(band):g}"
    hi = "n/a" if not _is_finite_number(band) else f"{1.0 + float(band):g}"
    rows = [[n, _fmt(kg)] for n, kg in (p.get("element_kg") or {}).items()]
    rows += [
        [
            "M_model, the stage-1 tank elements' envelope mass with their factors",
            _fmt(p.get("m_model_kg")),
        ],
        ["  on the cylinder-equivalent lengths", _fmt(p.get("m_model_cylinder_kg"))],
        ["R, Heineman's relation on the combined tank volume", _fmt(p.get("relation_kg"))],
        ["  per tank (printed beside)", _fmt(p.get("relation_per_tank_kg"))],
        [
            "  band half-width as a fraction of R (the file's heineman_band_fraction) [-]",
            _fmt(band),
        ],
        [f"  band, lower edge ({lo} R)", _fmt(p.get("lower_kg"))],
        [f"  band, upper edge ({hi} R)", _fmt(p.get("upper_kg"))],
        ["M_model / R", _fmt(p.get("ratio"))],
        [
            f"factor on the low-mass end ({hi} R / M above {hi} R, else 1)",
            _fmt(p.get("low_mass_end_factor")),
        ],
        [
            f"factor on the high-mass end ({lo} R / M below {lo} R, else 1)",
            _fmt(p.get("high_mass_end_factor")),
        ],
        ["Akin's tank fractions (printed beside)", _fmt(p.get("akin_kg"))],
        ["the interstage relation (printed beside)", _fmt(p.get("interstage_relation_kg"))],
        [
            "k_ts T_max, the thrust-structure relation (printed beside)",
            _fmt(p.get("thrust_structure_relation_kg")),
        ],
        [
            "stage 1's dry mass less its engines (printed beside)",
            _fmt(p.get("stage1_dry_less_engines_kg")),
        ],
    ]
    return [
        "Plausibility (calibration, not validation; the envelope at the central coefficients, "
        "margin 0, no cap):",
        "",
        _table(["quantity [kg unless stated]", "value"], rows),
        "",
        f"- rule: {p.get('rule')}",
        _plausibility_trigger(p, central),
    ]


def _envelope_table(inputs: Mapping[str, Any]) -> str:
    """The pad envelope per element of ``structure_inputs``: the required thickness's
    maximum [mm], its station and height, the governing mode and load case."""
    rows = [
        [
            f"{e.get('stage')}.{e.get('element')}",
            _fmt(None if e.get("t_max_m") is None else float(m_to_mm(float(e["t_max_m"])))),
            _fmt(e.get("station_index")),
            _fmt(e.get("z_m")),
            _fmt(e.get("mode")),
            _fmt(e.get("case_label"))
            if e.get("case_label") is not None
            else "none (minimum gauge)",
        ]
        for e in inputs.get("envelope") or []
    ]
    return _table(
        [
            "element",
            "required wall, max [mm]",
            "station",
            "z [m]",
            "governing mode",
            "governing load case",
        ],
        rows,
    )


STRUCTURE_FIGURES_TEXT = (
    "figures (written when plots are on): the required wall thickness along the stations of "
    "stage 1 and, where the push sized stage 2, of stage 2, pad envelope against push, the "
    "governing mode marked per station, and dm by element"
)
"""The figures line of the Structure subsection (``structure_section``), before the list of
plots/<run>_structure.png files."""


def structure_section(record: Mapping[str, Any]) -> str:
    """The Structure subsection of the offload section (SP7 step S3b; design 4.4,
    "Summary"), printed only when the record carries ``structure_inputs`` (an experiment
    with a structure block): the case table (STRUCTURE_CASE_ROWS: one column per
    structural case, SP1's penalty rows of the same experiment beside, ``structure_cases_of``)
    with the flight-check note under it (STRUCTURE_FLIGHT_CHECK_NOTE), the no_offload lines
    (``_no_offload_line``), the physics band and the outer envelope (``_band_line``: each
    end from every case of that set at the headline settings, ``structure_is_band_end``, the
    scaled beside the unscaled, with the sets' method label), the design axes' break-even
    values (what the record says of them), the layer-2 rows that move a design axis
    (``_layer2_line``) and the settings rows that move the entry path or the sizing basis
    (``_settings_rows_line``), where the sets were found (the file's ``sets.method``) and
    the applicability line (STRUCTURE_SETS_APPLICABILITY), the element table of the central
    case (``_element_table``; the first central case at the headline settings, else the
    first central case at the headline's axes, else the first central case, named by
    ``_central_case_phrase``), the pad envelope per element and the plausibility table with
    the rule's trigger (``_plausibility_lines``), the payload cases (STRUCTURE_PAYLOAD_ROWS,
    the heading naming for each the full_load case of the same variant and settings,
    ``structure_settings_of``, or that none ran), the arms line with STRUCTURE_ARM_CAVEAT
    and the figures named (STRUCTURE_FIGURES_TEXT; plots/<run>_structure.png per structural
    run)."""
    inputs = record.get("structure_inputs")
    if inputs is None:
        return ""
    cases = structure_cases_of(record)
    structural = [c for c in cases if c.get("structure_charged")]
    payload_cases = [p for p in record.get("structure_payload_cases") or [] if not p.get("skipped")]
    lines = [
        STRUCTURE_SUBSECTION_TITLE,
        "",
        f"Structure file: {inputs.get('file')} (sha256 {inputs.get('sha256')}); the pad envelope "
        f"is {inputs.get('envelope_pad')}'s own flight at P_ref = "
        f"{_fmt(inputs.get('reference_payload_kg'))} kg. "
        "Every dm is the model's first-order station sizing of the push load, charged to the "
        "assisted run only; the pad keeps its vehicle (D-SP7-35).",
        "",
    ]
    if cases:
        lines += [_structure_table(cases, STRUCTURE_CASE_ROWS, "name"), ""]
        lines.append(f"- {STRUCTURE_FLIGHT_CHECK_NOTE}")
        if any(structure_push_is_flown(c) for c in cases):
            lines.append(f"- {STRUCTURE_FLOWN_PUSH_NOTE}")
    else:
        lines += ["(no structural case or penalty row ran)", ""]
    for c in structural:
        if c.get("status") == NO_OFFLOAD_STATUS:
            lines.append(_no_offload_line(c, payload_cases))
    sets = inputs.get("sets") or {}
    method = (
        f"{sets.get('label')} ({sets.get('source')}; the method and evaluation count are "
        f"recorded in the file's sets block: {_fmt(sets.get('evaluation_count'))} sizings, "
        f"frozen at commit {sets.get('parent_commit')}, reproduced by {sets.get('test')})"
        if sets
        else f"{inputs.get('sets_label')}: the structure file has no frozen sets"
    )

    def of_set(name: str) -> list[Mapping[str, Any]]:
        """The set's own ends: its cases at the headline settings
        (``structure_is_band_end``; every other case is a layer-2 row or a settings
        row, ``_layer2_line`` and ``_settings_rows_line``)."""
        return [
            c for c in structural if c.get("structure_set") == name and structure_is_band_end(c)
        ]

    found = (
        f"- where the sets were found (the file's sets.method; sizing only, at one push): "
        f"{sets.get('method')}"
        if sets
        else "- where the sets were found: the structure file has no frozen sets"
    )
    layer2 = _layer2_line(structural)
    settings_rows = _settings_rows_line(structural)
    lines += [
        _band_line(
            "physics band (layer 1)",
            of_set(SET_PHYSICS_LOW),
            of_set(SET_PHYSICS_HIGH),
            method,
        ),
        _band_line(
            "outer envelope (layer 3)", of_set(SET_OUTER_LOW), of_set(SET_OUTER_HIGH), method
        ),
        f"- design-axis break-even values (layer 2): {inputs.get('tornado_note')}",
        *([layer2] if layer2 else []),
        *([settings_rows] if settings_rows else []),
        found,
        f"- applicability: {STRUCTURE_SETS_APPLICABILITY}",
        "",
    ]
    centrals = [c for c in structural if c.get("structure_set") == STRUCTURE_CENTRAL_SET]
    central = next(
        (
            c
            for c in centrals
            if not structure_axis_departures(c) and not structure_row_departures(c)
        ),
        None,
    )
    if central is None:
        central = next((c for c in centrals if not structure_axis_departures(c)), None)
    if central is None and centrals:
        central = centrals[0]
    if central is not None:
        at = (
            "at x = 0 (the solve ended no_offload)"
            if central.get("status") == NO_OFFLOAD_STATUS
            else "at x*"
        )
        lines += [
            f"Elements of {_central_case_phrase(central)} {at} (the station-sized and "
            "relation elements, then the ring):",
            "",
            _element_table(central),
            "",
        ]
    lines += [
        f"Pad envelope per element ({inputs.get('envelope_basis')}):",
        "",
        _envelope_table(inputs),
        "",
    ]
    lines += [*_plausibility_lines(inputs, central), ""]
    if payload_cases:
        beside = "; ".join(_payload_beside(p, structural) for p in payload_cases)
        lines += [
            "Structure payload cases (design 4.4, the payload form: a full-load sizing like a "
            f"full_load case's, read beside the full_load row of the same variant and settings "
            f"above: {beside}; two passes, not iterated further; "
            f"{STRUCTURE_PAYLOAD_OFFLOADS_NOTHING}):",
            "",
            _structure_table(payload_cases, STRUCTURE_PAYLOAD_ROWS, "name"),
            "",
        ]
        if any(structure_push_is_flown(p) for p in payload_cases):
            lines += [f"- {STRUCTURE_FLOWN_PUSH_NOTE}", ""]
    for p in record.get("structure_payload_cases") or []:
        if p.get("skipped"):
            lines.append(f"- {p.get('name')} (of {p.get('of')}): {p['skipped']}")
    arms = [a for a in record.get("sensitivity") or [] if a.get("structure_charged")]
    if arms:
        lines += [
            f"- structural sensitivity arms: {len(arms)} (the Sensitivity table below carries "
            "their dm, set and envelope pad; the caveat follows)",
            f"- {STRUCTURE_ARM_CAVEAT}",
        ]
    figures = [
        f"plots/{run_data.plot_stem(str(c.get('run')), 'structure')}.png ({c.get('name')})"
        for c in [*structural, *payload_cases]
        if c.get("run")
    ]
    if figures:
        lines += [f"- {STRUCTURE_FIGURES_TEXT}: " + "; ".join(figures)]
    return "\n".join(lines).rstrip()


def _energy_tables_text(solved: list[Any], imposed: list[Any]) -> str:
    """Which tables the energy note covers when the block has imposed cases that ran:
    OFFLOAD_ENERGY_BOTH_TABLES beside a solved table, OFFLOAD_ENERGY_IMPOSED_TABLE when no
    solved case ran (final clean-up, N3a-04)."""
    return OFFLOAD_ENERGY_BOTH_TABLES if solved and imposed else OFFLOAD_ENERGY_IMPOSED_TABLE


def offload_section(record: Mapping[str, Any]) -> str:
    """The "Propellant saved at fixed payload" section of an offload record (the
    metrics.json ``offload`` value; pure text): the basis line with the reference
    payload, the sensitivity basis, the caveats (the record's: ``offload_caveats``), the
    solved cases table (OFFLOAD_CASE_ROWS, plus OFFLOAD_ENERGY_ROWS with energy inputs;
    OFFLOAD_NO_SOLVED_CASE when every case that ran is imposed), the cases that did not
    run (after OFFLOAD_NOT_RUN_LEAD when the block has imposed cases), the energy note
    with its exclusions (and, with imposed cases, OFFLOAD_ENERGY_BOTH_TABLES beside a solved
    table or OFFLOAD_ENERGY_IMPOSED_TABLE without one: ``_energy_tables_text``), then (KI-039,
    D-SP7-23, SP7 step S3a) the imposed cases under OFFLOAD_IMPOSED_SUBSECTION_TITLE with
    OFFLOAD_IMPOSED_BASIS and the same rows (the section's heading and basis describe
    solved cases, which fly P_ref; an imposed case flies its own P*; fix round 3,
    H-S3a-P3-06: the not-run list and the energy note come before the sub-section's
    heading, so neither reads as the imposed cases' alone), with a structure block the
    Structure subsection (``structure_section``, SP7 step S3b), the decomposition table,
    the pad controls, the sensitivity arms (with STRUCTURE_ARM_CAVEAT under the table
    when some arm is structural) and the notes. A skipped block prints only why."""
    if record.get("skipped"):
        return str(record["skipped"])
    lines = [
        f"{record.get('basis')}. Reference payload P_ref = "
        f"{_fmt(record.get('reference_payload_kg'))} kg ({record.get('reference')}'s payload "
        "capacity P*).",
        "",
    ]
    if record.get("sensitivity_basis"):
        lines += [f"{record['sensitivity_basis']}.", ""]
    lines += ["Caveats (they travel with every number below):", ""]
    lines += [f"- {c}" for c in record.get("caveats") or []]
    lines.append("")
    cases = [c for c in record.get("cases") or [] if not c.get("skipped")]
    solved = [c for c in cases if c.get("kind") != OFFLOAD_FIXED_KIND]
    imposed = [c for c in cases if c.get("kind") == OFFLOAD_FIXED_KIND]
    energy = record.get("energy_inputs") is not None
    rows = [*OFFLOAD_CASE_ROWS, *(OFFLOAD_ENERGY_ROWS if energy else ())]
    if solved:
        lines += [_offload_table(solved, rows, "name"), ""]
    elif imposed:
        lines += [OFFLOAD_NO_SOLVED_CASE, ""]
    skipped = [c for c in record.get("cases") or [] if c.get("skipped")]
    if skipped and imposed:
        lines.append(OFFLOAD_NOT_RUN_LEAD)
    for c in skipped:
        lines.append(f"- {c.get('name')} (of {c.get('of')}): {c['skipped']}")
    if energy and cases:
        excludes = next((c["energy"]["excludes"] for c in cases if c.get("energy")), [])
        lines += [
            "",
            f"{OFFLOAD_ENERGY_TEXT}. The heat / electricity ratio is "
            f"{OFFLOAD_ENERGY_RATIO_LABEL}; it leaves out "
            + "; ".join(excludes)
            + "."
            + (f" {_energy_tables_text(solved, imposed)}" if imposed else ""),
        ]
    if imposed:
        lines += [
            "",
            OFFLOAD_IMPOSED_SUBSECTION_TITLE,
            "",
            f"{OFFLOAD_IMPOSED_BASIS}.",
            "",
            _offload_table(imposed, rows, "name"),
        ]
    if record.get("structure_inputs") is not None:
        lines += ["", structure_section(record)]
    lines += ["", "### Decomposition", "", OFFLOAD_DECOMPOSITION_TEXT + ".", ""]
    lines.append(offload_decomposition_table(cases))
    lines += ["", "### Pad controls", "", *pad_control_lines(record.get("pad_controls") or [])]
    arms = record.get("sensitivity") or []
    if arms:
        lines += ["", "### Sensitivity", "", offload_sensitivity_table(arms)]
        if any(a.get("structure_charged") for a in arms):
            lines += ["", f"- {STRUCTURE_ARM_CAVEAT}"]
    for note in record.get("notes") or []:
        lines += ["", str(note)]
    return "\n".join(lines)


def offload_blocking_controls(record: Mapping[str, Any]) -> list[str]:
    """The pad controls of an offload record that block findings, labelled ``pad control
    <mode>`` for ``blocked_lines`` (its ``controls``, PAD_CONTROL_BLOCKED): a stage-1
    control that fails its consistency test (the stage-1 headline rests on that
    solver)."""
    return [
        f"pad control {p.get('mode')}"
        for p in record.get("pad_controls") or []
        if p.get("consistency") == CHECK_FAIL
    ]


def offload_check_comparisons(record: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    """The offload comparisons that can block findings, labelled, as comparison-like
    mappings for ``blocked_lines``: each case's and each sensitivity arm's decomposition
    (its status as ``screening_status``: explained, or bug_suspect) and each paired-pad
    comparison (attributed, one vehicle). None of them enters the unexplained-beats
    list. A failing pad control is not a comparison: ``offload_blocking_controls``."""
    out: list[tuple[str, Mapping[str, Any]]] = []
    for c in record.get("cases") or []:
        if c.get("decomposition_status") is not None:
            out.append(
                (
                    f"{c['name']} offload decomposition",
                    {"screening_status": c["decomposition_status"]},
                )
            )
        paired = c.get("paired_pad")
        if paired:
            out.append((f"{c['name']} vs {paired['run']}", paired.get("comparison") or {}))
    for a in record.get("sensitivity") or []:
        if a.get("decomposition_status") is not None:
            out.append(
                (
                    f"{a['run']} offload decomposition",
                    {"screening_status": a["decomposition_status"]},
                )
            )
    return out


def offload_check_lines(record: Mapping[str, Any]) -> list[str]:
    """The Checks section's offload lines: OFFLOAD_CHECKS_TEXT, then per stage-1 pad
    control its consistency verdict (``_pad_control_text``), per case (and arm) its
    decomposition status, residual and offload-to-screening ratio."""
    lines = [f"{OFFLOAD_CHECKS_TEXT}:"]
    for p in record.get("pad_controls") or []:
        if p.get("consistency") not in (None, CHECK_NA):
            lines.append(f"- pad control {p.get('mode')}: {_pad_control_text(p)}")
    items = [(c["name"], c) for c in record.get("cases") or [] if not c.get("skipped")]
    for name, c in items:
        lines.append(
            f"- {name}: decomposition {_fmt(c.get('decomposition_status'))} (residual "
            f"{_offload_cell(c, 'sci', 'decomposition.xv_residual_mps')} m/s; stage-1 "
            f"offload / screening {_fmt(c.get('screening_ratio'))})"
        )
    for a in record.get("sensitivity") or []:
        lines.append(
            f"- {a.get('run')}: decomposition {_fmt(a.get('decomposition_status'))} (residual "
            f"{_offload_cell(a, 'sci', 'decomposition_residual_mps')} m/s)"
        )
    return lines


def planar_experiment_summary(er: ExperimentResult, header_lines: Sequence[str] = ()) -> str:
    """The summary.md text of a planar experiment: the CALIBRATION banner (label
    calibration) or the exploratory banner (label exploratory, ``exploratory_banner``),
    the title, the comparison basis and the guidance label
    (``guidance_label``: sweep-optimized, or fixed guidance), the per-variant table
    (PLANAR_VARIANT_ROWS), with an offload block its section "Propellant saved at fixed
    payload" (``offload_section``; the block's runs then also join the flags and the
    assumptions), the bounds, the calibration cases, the sensitivity table, the flags,
    the assumptions (union, attributed) and the checks (``planar_checks_section``:
    per-run checks, the screening line of every variant, the attributed sensitivity and
    bound comparisons, the offload decompositions, blocked findings, unexplained beats,
    gamma*-sensitive verdicts). Without an offload block the text is what it was before
    the block existed."""
    runs = er.runs
    all_runs = {**runs, **er.cases}
    banner = [CALIBRATION_BANNER, ""] if er.label == CALIBRATION_LABEL else []
    if er.label == EXPLORATORY_LABEL:
        record = None if er.offload is None else er.offload.record
        arms = bool((record or {}).get("sensitivity"))
        banner = [
            exploratory_banner(
                er.git,
                er.vehicle_name,
                all_runs,
                record,
                sensitivity_ran=bool(er.sensitivity) or arms,
            ),
            "",
        ]
    banner += preregistration_lines(er.preregistration)
    budget = f"- Search budget id: {er.search_budget_id}" if er.search_budget_id else None
    offload: list[str] = []
    if er.offload is not None:
        offload = [OFFLOAD_SECTION_TITLE, "", offload_section(er.offload.record), ""]
    reported = {**all_runs, **er.offload_runs}
    return "\n".join(
        [
            *banner,
            f"# {er.experiment_name} ({er.timestamp_utc}, git {git_label(er.git)})",
            "",
            er.comparison_basis,
            "",
            guidance_label(all_runs),
            "",
            f"- Vehicle: {er.vehicle_name}",
            f"- Baseline: {er.baseline.name}",
            *([budget] if budget else []),
            *header_lines,
            provenance_lines(er.git, er.timestamp_utc),
            "",
            "## Variants against the baseline",
            "",
            planar_variants_table(er),
            "",
            *offload,
            "## Bounds",
            "",
            bounds_section(er),
            "",
            "## Cases",
            "",
            cases_section(er),
            "",
            "## Sensitivity",
            "",
            planar_sensitivity_table(er.sensitivity, er.sensitivity_note),
            "",
            "## Flags",
            "",
            flags_section(reported),
            "",
            "## Assumptions",
            "",
            assumptions_section(reported, er.baseline.name),
            "",
            "## Checks",
            "",
            planar_checks_section(er),
            "",
        ]
    )


def planar_sweep_summary(
    exp_name: str,
    sweeps: list[SweepResult],
    frames: list[pd.DataFrame],
    baseline: RunResult,
    git: Mapping[str, Any],
    timestamp_utc: str,
) -> str:
    """The top-level summary.md text of a planar sweep: the comparison basis and the
    guidance label (sweep-optimized, or fixed guidance), one table per sweep (the sweep
    index: release speed, P* and dP*, the screening yardstick, the kick regime per point,
    q-alpha and max-Q against the point's baseline, the screening status; a no_offload
    point's offload and share cells read SWEEP_NO_OFFLOAD_CELL, ``sweep_table_rows``,
    KI-042), the paired
    baselines of paired sweeps, the assumptions (union over the baseline and every
    point) and the Checks (``sweep_checks_section``: blocked findings, not_checked,
    gamma*-sensitive verdicts); under a table whose offload cases are structural at some
    point, ``sweep_structure_lines`` (SP7 step S3a fix round 2, H-S3a-P2-07), and under one
    at which some point's case ended no_offload, ``sweep_no_offload_lines`` (SP7 step
    S3c), each only when it has a line."""
    all_runs = {baseline.name: baseline}
    for sweep in sweeps:
        all_runs.update({f"sweep_{sweep.sweep_index}/{rr.name}": rr for rr in sweep.results})
    parts = [
        f"# {exp_name}: sweeps",
        "",
        planar_comparison_basis(baseline.result.metrics.get("figure_of_merit")),
        "",
        guidance_label(all_runs),
        "",
        f"- Baseline: {baseline.name} (status {baseline.result.status})",
        provenance_lines(git, timestamp_utc),
        "",
    ]
    if not sweeps:
        parts.append("(no sweeps declared)")
    for sweep, frame in zip(sweeps, frames, strict=True):
        parts += [f"## sweep_{sweep.sweep_index}: {sweep.of} over {', '.join(sweep.axes)}", ""]
        if any(p is not None for p in sweep.paired):
            parts += [
                "Paired sweep: every point is compared with the baseline re-run under the "
                "same overrides (column paired_baseline), not with the experiment's baseline.",
                "",
            ]
        if frame.empty:
            parts += ["(no points)", ""]
            continue
        header = [str(c) for c in frame.columns]
        parts += [_table(header, sweep_table_rows(frame)), ""]
        structure = sweep_structure_lines(sweep.offload)
        if structure:
            parts += [*structure, ""]
        no_offload = sweep_no_offload_lines(sweep)
        if no_offload:
            parts += [*no_offload, ""]
    section = assumptions_section(all_runs, baseline.name, "all sweep points")
    parts += ["## Assumptions", "", section, ""]
    parts += ["## Checks", "", sweep_checks_section(sweeps, baseline), ""]
    return "\n".join(parts)


SWEEP_NO_OFFLOAD_CELL = "n/a: no offload"
"""What a planar sweep table prints in a no_offload point's ``<case>.offload_kg``,
``<case>.stage1_fraction`` and ``<case>.total_fraction`` cells (KI-042, SP7 step S4a):
the index keeps the solver's x* = 0 (sweep_index.csv is data), but a no-offload end is
never worded as an offload of "0 t" (D-SP7-32)."""
SWEEP_NO_OFFLOAD_FIELDS: tuple[str, ...] = ("offload_kg", "stage1_fraction", "total_fraction")
"""The offload columns (``results_io.OFFLOAD_SWEEP_COLUMNS``) whose cell reads
SWEEP_NO_OFFLOAD_CELL at a point where the case's status is no_offload."""


def sweep_table_rows(frame: pd.DataFrame) -> list[list[str]]:
    """The cells of a planar sweep table, one row per sweep_index.csv point: ``_fmt`` of
    each value, except that a case's SWEEP_NO_OFFLOAD_FIELDS cells (columns
    ``<case>.offload_kg``, ``<case>.stage1_fraction``, ``<case>.total_fraction``) read
    SWEEP_NO_OFFLOAD_CELL where that point's ``<case>.status`` is no_offload (KI-042);
    the frame itself, the CSV's data, is not changed."""
    columns = [str(c) for c in frame.columns]
    status_at: dict[int, int] = {}
    for j, column in enumerate(columns):
        case, dot, field = column.rpartition(".")
        if dot and field in SWEEP_NO_OFFLOAD_FIELDS and f"{case}.status" in columns:
            status_at[j] = columns.index(f"{case}.status")
    rows: list[list[str]] = []
    for rec in frame.itertuples(index=False, name=None):
        rows.append(
            [
                SWEEP_NO_OFFLOAD_CELL
                if j in status_at and rec[status_at[j]] == NO_OFFLOAD_STATUS
                else _fmt(value)
                for j, value in enumerate(rec)
            ]
        )
    return rows


SWEEP_STRUCTURE_HEAD = "Structural offload cases of this sweep (SP7, D-SP7-22):"
"""What opens the lines under a sweep table whose offload cases charge a modelled
structural mass at some point (``sweep_structure_lines``)."""


def sweep_structure_lines(points: Sequence[Mapping[str, Mapping[str, Any]]]) -> list[str]:
    """The lines under a sweep's table that word its structural offload cases (fix round
    2, H-S3a-P2-07: a sweep point writes no case record or run directory, so its structural
    solve is otherwise worded only by the index's ``<case>.structure_*`` columns):
    SWEEP_STRUCTURE_HEAD, then one line per case that is ``structure_charged`` at some
    point (``points``: per point, case name to its record, SweepResult.offload): how many
    points, that ``<case>.structure_dm_kg`` is the modelled structural mass of the push
    load at each point's x*, the model (STRUCTURE_MODEL_NAME), the layers and sets
    (``structure_layer_label``) and files met, never an assumed penalty,
    STRUCTURE_ESTIMATE_TEXT, that the dm carries the plausibility rule's factor where
    ``<case>.structure_plausibility_scaled`` is True (when some point's is), and where its
    fired flags are (the ``<case>.structure_flags`` column and the Checks section); [] for a
    sweep without a structural case (every SP1-type sweep: these lines add nothing to its
    summary; since SP7 step S3c its table does carry ``<case>.dv_shortfall_mps``)."""
    by_case: dict[str, list[Mapping[str, Any]]] = {}
    for records in points:
        for case, record in records.items():
            if isinstance(record, Mapping) and structure_charged(record):
                by_case.setdefault(str(case), []).append(record)
    if not by_case:
        return []
    lines = [SWEEP_STRUCTURE_HEAD, ""]
    for case, records in by_case.items():
        labels = "; ".join(dict.fromkeys(structure_layer_label(r) for r in records))
        files = ", ".join(dict.fromkeys(str(r.get("structure_file")) for r in records))
        n = len(records)
        line = (
            f"- {case} ({n} point{'s' if n > 1 else ''} of {len(points)}): "
            f"{case}.structure_dm_kg is the modelled structural mass of the push load at each "
            f"point's x* (dm1 + dm2, never an assumed penalty), {STRUCTURE_MODEL_NAME} (layer "
            f"and set {labels}; {files}), {STRUCTURE_ESTIMATE_TEXT}"
        )
        if any(r.get("structure_plausibility_scaled") for r in records):
            line += (
                "; the dm carries the plausibility rule's factor where "
                f"{case}.structure_plausibility_scaled is True (D-SP7-33)"
            )
        line += f"; its fired flags are in {case}.structure_flags and the Checks section."
        lines.append(line)
    return lines


SWEEP_NO_OFFLOAD_HEAD = (
    "Sweep points at which an offload case ended no_offload (SP7 step S3c; pre-registration "
    "section 9):"
)
"""What opens the lines under a sweep table at which an offload case ended no_offload at
some point (``sweep_no_offload_lines``; a sweep may name several cases per point
(``SweepConfig.offload``: the registered SP7 sweeps two, SP1's recorded sweeps one), so
the lines are per (point, case) and a point's other cases may have ended ok)."""
SWEEP_NO_OFFLOAD_DEFICIT = (
    f"payload deficit at the full load {STRUCTURE_NOT_FLOWN} (a payload case flies a "
    "variant, not a sweep point)"
)
"""The payload-deficit clause of every sweep no_offload line: a sweep point has no
payload case, so its deficit is never quoted (pre-registration section 6, item 5)."""


def sweep_no_offload_lines(sweep: SweepResult) -> list[str]:
    """The lines under a sweep's table that report each (point, case) at which an offload
    case ended no_offload (SP7 step S3c; the pre-registration's section 9 requires the
    report, its section 6, item 5 the deficit's words: a sweep point writes no case
    record, so its shortfall is otherwise only the index's ``<case>.dv_shortfall_mps``
    cell): SWEEP_NO_OFFLOAD_HEAD, then one line per (point, case) whose record status is
    NO_OFFLOAD_STATUS, in the sweep's point order, mirroring the run summary's
    ``_no_offload_line``: the point's run and the case, the dm the full-load push carried
    (``structure_dm_kg``: at a no_offload end the sizing at x = 0, the run summary's
    STRUCTURE_AT_X_NOTE; for a ``structure_charged`` record only, an uncharged end drops
    the clause), the solver's ``dv_shortfall_mps`` at x = 0 and the column that holds it,
    and SWEEP_NO_OFFLOAD_DEFICIT. The end is worded as no offload, never as an offload of
    "0 t" (D-SP7-32). Every figure is a record field; nothing is computed. [] when no
    point ended no_offload, whatever the sweep's type (SP1's recorded sweeps among them:
    every point of theirs ended ok, so their summaries change only by the column, its
    header and ``n/a`` cells in the sweep table, and gain no line)."""
    tag = f"sweep_{sweep.sweep_index}"
    offloads = sweep.offload or [{}] * len(sweep.results)
    lines: list[str] = []
    for rr, records in zip(sweep.results, offloads, strict=True):
        for case, record in records.items():
            if not isinstance(record, Mapping) or record.get("status") != NO_OFFLOAD_STATUS:
                continue
            solve = record.get("solve") or {}
            carrying = (
                f" carrying dm {_fmt(record.get('structure_dm_kg'))} kg"
                if structure_charged(record)
                else ""
            )
            lines.append(
                f"- {tag}/{rr.name} {case}: no offload at P_ref: the full-load push{carrying} "
                f"falls short of P_ref by {_fmt(solve.get('dv_shortfall_mps'))} m/s of delta-v "
                f"(the solver's dv_shortfall_mps at x = 0; column {case}.dv_shortfall_mps); "
                f"{SWEEP_NO_OFFLOAD_DEFICIT}"
            )
    if not lines:
        return []
    return [SWEEP_NO_OFFLOAD_HEAD, "", *lines]


def sweep_checks_section(sweeps: Sequence[SweepResult], baseline: RunResult) -> str:
    """The Checks section of a planar sweep summary: the per-run checks of the baseline,
    every point and every paired baseline (and of the offload runs a sweep's offload
    cases flew), then (``blocked_lines``) the runs and point comparisons that are
    bug_suspect (FINDINGS_BLOCKED) or that none is, the not_checked comparisons, the
    gamma*-sensitive verdicts and the failed checks of every point (each point's own
    summary.md has its full screening line); a sweep with offload cases also lists each
    point's offload decompositions, a bug_suspect one blocking findings, and every
    point's offload flags (``offload_sweep_flag_line``)."""
    runs: dict[str, RunResult] = {baseline.name: baseline}
    comparisons: list[tuple[str, Mapping[str, Any]]] = []
    offload: list[tuple[str, Mapping[str, Any]]] = []
    flagged: list[str] = []
    for sweep in sweeps:
        tag = f"sweep_{sweep.sweep_index}"
        paired = sweep.paired or [None] * len(sweep.results)
        for rr, comp, pair in zip(sweep.results, sweep.comparisons, paired, strict=True):
            runs[f"{tag}/{rr.name}"] = rr
            if pair is not None:
                runs[f"{tag}/{pair.name}"] = pair
            comparisons.append((f"{tag}/{rr.name}", comp))
        for point_runs in sweep.offload_runs:
            runs.update({f"{tag}/{name}": rr for name, rr in point_runs.items()})
        for rr, records in zip(sweep.results, sweep.offload, strict=False):
            for case, rec in records.items():
                status = rec.get("decomposition_status")
                if status is not None:
                    label = f"{tag}/{rr.name} {case} offload decomposition"
                    offload.append((label, {"screening_status": status}))
                flagged.append(offload_sweep_flag_line(f"{tag}/{rr.name} {case}", rec))
    lines = [*run_check_lines(runs), ""]
    lines += [sweep_point_check_line(name, c) for name, c in comparisons]
    if offload:
        lines += ["", f"{OFFLOAD_SWEEP_CHECKS_TEXT}:"]
        lines += [f"- {label}: {c['screening_status']}" for label, c in offload]
    if flagged:
        lines += ["", f"{OFFLOAD_SWEEP_FLAGS_TEXT}:", *flagged]
    return "\n".join([*lines, "", *blocked_lines(runs, [*comparisons, *offload])])


def offload_sweep_flag_line(label: str, record: Mapping[str, Any]) -> str:
    """One sweep point's offload flag line: the case record's flags joined with "; ",
    ``none`` when the list is empty, OFFLOAD_SWEEP_NO_FLAG_LIST without one. A record
    with a flag list whose status is neither ok nor no_offload also gets that status,
    so a failed solve (whose flag list is empty) never reads as clean: "(solve
    search_failed: <failure kind>)" for a solved case (its ``solve.failure_kind``),
    "(payload search <status>)" for a fixed case."""
    flags = record.get("flags")
    if flags is None:
        return f"- {label} offload flags: {OFFLOAD_SWEEP_NO_FLAG_LIST}"
    text = "; ".join(flags) or "none"
    status = record.get("status")
    if status not in (OK_STATUS, NO_OFFLOAD_STATUS):
        solve = record.get("solve") or {}
        kind = solve.get("failure_kind")
        what = "solve" if record.get("kind") == "solve" else "payload search"
        text += f" ({what} {status}" + ("" if kind is None else f": {kind}") + ")"
    return f"- {label} offload flags: {text}"


def sweep_point_check_line(name: str, c: Mapping[str, Any]) -> str:
    """One sweep point's line in the sweep Checks section: its screening status, the
    failed blocking checks, the failed diagnostic checks (which block no finding) and the
    gamma*-sensitive checks, each ``none`` when empty."""
    return (
        f"- {name}: screening status {c.get('screening_status', 'n/a')} (failed checks: "
        f"{', '.join(c.get('screening_failed') or []) or 'none'}; failed diagnostic checks: "
        f"{_diagnostic_failed(c) or 'none'}; gamma*-sensitive: {_gamma_sensitive(c) or 'none'})"
    )
