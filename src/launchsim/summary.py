"""The summary.md text of an experiment run, a sweep point and a sweep (moved from
sim.py; pure: builds strings, writes nothing). A planar_2d experiment gets
``planar_experiment_summary`` and ``planar_sweep_summary`` (PLANAR_VARIANT_ROWS, the
CALIBRATION banner, the guidance label (sweep-optimized or fixed), the bounds, cases and
screening lines and, with an offload block, the section "Propellant saved at fixed
payload": ``offload_section`` of the block's plain record, with its caveats,
``offload_caveats``).

``experiment_summary`` assembles the sections in the CLAUDE.md order: the per-variant
table against the baseline (``variants_table``, rows ``variant_rows``), the sensitivity
table, the flags, the attributed assumptions and the checks (identity lines and the
release-speed bound). ``sweep_summary`` is the top-level text of a sweep and
``sweep_point_header`` names a sweep point. Numbers are SI with the unit in each row
label; cells print 6 significant digits (``_fmt``). ``sim`` re-exports every name.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

import pandas as pd

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
    PLANAR_2D,
    RAMP_START_TIME,
    SEARCHED_FIGURES,
    SweepPoint,
)
from launchsim.offload import NO_OFFLOAD_STATUS
from launchsim.search import OK_STATUS
from launchsim.units import j_to_mj, kg_to_t, rad_to_deg, to_percent

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
    (``_flight_burn_differs``), plus FAILED_ROWS when any run carries a
    failed-ignition item."""
    rows: list[VariantRow] = []
    flight_pair = _flight_burn_differs(er)
    stage = first_stage_name(er)
    for row in VARIANT_ROWS:
        rows.append(row)
        if row[1] == "flags":
            rows += ignition_rows(stage)
        elif row[2] == FLIGHT_BURN_AFTER_KEY and flight_pair:
            rows += FLIGHT_BURN_ROWS
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
PLANAR_FAILED_ROWS: tuple[VariantRow, ...] = (
    ("failed ignition: stage", "m", "failed_stage"),
    ("  apex altitude of the fall-back coast [m]", "m", "apex_alt_m"),
    ("  time of that apex after release [s]", "m", "apex_t_s"),
    ("  impact time after release [s]", "m", "impact_t_s"),
    ("  impact speed |v_rel| at the ground [m/s]", "m", "impact_speed_mps"),
)
"""Appended to the planar table when any run carries a failed ignition (the planar
metric names: the highest apex and the impact of the unpowered coast)."""


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
    speed or height (``_states_ramp_trigger``), plus PLANAR_FAILED_ROWS when any run
    carries a failed ignition."""
    rows: list[VariantRow] = []
    ramp = _states_ramp_trigger(er)
    for row in PLANAR_VARIANT_ROWS:
        rows.append(row)
        if row[1] == "flags":
            rows += ignition_rows(first_stage_name(er))
            if ramp:
                rows += RAMP_START_ROWS
    if any("failed_stage" in rr.result.metrics for rr in er.runs.values()):
        rows += PLANAR_FAILED_ROWS
    return tuple(rows)


def _planar_cell(
    runs: Mapping[str, RunResult], er: ExperimentResult, name: str, row: VariantRow
) -> str:
    """One cell of the planar per-variant table: a PLANAR_DEG_SOURCE metric in degrees,
    the PLANAR_SCREENING_SOURCE row as ``screening_cell`` ("(baseline)" for the
    baseline), everything else as ``_variant_cell``."""
    _label, source, key = row
    if source == PLANAR_SCREENING_SOURCE:
        if name == er.baseline.name:
            return "(baseline)"
        return screening_cell(er.comparison.get(name, {}))
    if source == RAMP_TRIGGER_SOURCE:
        return _ramp_trigger_cell(er, name)
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


def offload_caveats(vehicle_name: str, calibration: tuple[float, float, str] | None) -> list[str]:
    """Every caveat of an offload block on vehicle_name: its calibration caveat
    (``offload_calibration_caveat``) then OFFLOAD_CAVEATS."""
    return [offload_calibration_caveat(vehicle_name, calibration), *OFFLOAD_CAVEATS]


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
        "t",
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
    with its offload in tonnes), ``text`` and ``num`` as ``_fmt``."""
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


def offload_sensitivity_table(arms: Sequence[Mapping[str, Any]]) -> str:
    """The offload sensitivity arms: case, parameter, change, whether the pad was
    perturbed, the arm's P_ref, status, offload and its change against the nominal case,
    the share of the stage-1 load, the decomposition and the screening ratio, whether
    the solve was reused."""
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
    ]
    rows = [
        [
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
        for a in arms
    ]
    return _table(header, rows)


def offload_section(record: Mapping[str, Any]) -> str:
    """The "Propellant saved at fixed payload" section of an offload record (the
    metrics.json ``offload`` value; pure text): the basis line with the reference
    payload, the sensitivity basis, the caveats (the record's: ``offload_caveats``), the
    cases table (OFFLOAD_CASE_ROWS, plus OFFLOAD_ENERGY_ROWS with energy inputs) and the
    cases that did not run, the energy note with its exclusions, the decomposition
    table, the pad controls, the sensitivity arms and the notes. A skipped block prints
    only why."""
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
    energy = record.get("energy_inputs") is not None
    if cases:
        rows = [*OFFLOAD_CASE_ROWS, *(OFFLOAD_ENERGY_ROWS if energy else ())]
        lines += [_offload_table(cases, rows, "name"), ""]
    for c in record.get("cases") or []:
        if c.get("skipped"):
            lines.append(f"- {c.get('name')} (of {c.get('of')}): {c['skipped']}")
    if energy and cases:
        excludes = next((c["energy"]["excludes"] for c in cases if c.get("energy")), [])
        lines += [
            "",
            f"{OFFLOAD_ENERGY_TEXT}. The heat / electricity ratio is "
            f"{OFFLOAD_ENERGY_RATIO_LABEL}; it leaves out " + "; ".join(excludes) + ".",
        ]
    lines += ["", "### Decomposition", "", OFFLOAD_DECOMPOSITION_TEXT + ".", ""]
    lines.append(offload_decomposition_table(cases))
    lines += ["", "### Pad controls", "", *pad_control_lines(record.get("pad_controls") or [])]
    arms = record.get("sensitivity") or []
    if arms:
        lines += ["", "### Sensitivity", "", offload_sensitivity_table(arms)]
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
    calibration), the title, the comparison basis and the guidance label
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
    banner = [CALIBRATION_BANNER, ""] if er.label == CALIBRATION_LABEL else []
    banner += preregistration_lines(er.preregistration)
    budget = f"- Search budget id: {er.search_budget_id}" if er.search_budget_id else None
    all_runs = {**runs, **er.cases}
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
    q-alpha and max-Q against the point's baseline, the screening status), the paired
    baselines of paired sweeps, the assumptions (union over the baseline and every
    point) and the Checks (``sweep_checks_section``: blocked findings, not_checked,
    gamma*-sensitive verdicts)."""
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
        rows = [[_fmt(v) for v in rec] for rec in frame.itertuples(index=False, name=None)]
        parts += [_table(header, rows), ""]
    section = assumptions_section(all_runs, baseline.name, "all sweep points")
    parts += ["## Assumptions", "", section, ""]
    parts += ["## Checks", "", sweep_checks_section(sweeps, baseline), ""]
    return "\n".join(parts)


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
