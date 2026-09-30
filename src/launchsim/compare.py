"""The comparison of a run against the baseline and the sensitivity cases (moved from
sim.py).

``compare`` gives the 1-D figures of merit of a run against the baseline
(docs/physics.md, "Figures of merit in 1-D"), with ``identity_budget`` and
``payload_equiv_kg``; ``run_sensitivity`` runs the experiment's sensitivity cases and
``sensitivity_record`` gives the metrics.json record of one. Units are SI with the unit
in each key. The planar_2d counterpart is ``compare_planar`` (dP*, the screening
yardstick, the matched-payload attribution ``matched_attribution`` of rung-2 runs the
caller executes, and the screening-beat checks M2 to M5 with status ``bug_suspect``,
M2 only when ``checks.m2_role`` is blocking; docs/physics.md, "Screening-beat rule
(2-D)"). ``compare`` and its helpers are pure;
``run_sensitivity`` runs simulations through ``sim.run_resolved`` (and, for a planar
energy-only case, ``sim.rerun_resolved``), looked up on the ``sim`` module at call time
(a test that patches ``sim.run`` changes what it runs). ``sim`` re-exports every name;
patch ``compare`` and the other functions defined here on this module, not on ``sim``.
``Result`` and ``RunResult`` are imported under ``TYPE_CHECKING`` only, so
``typing.get_type_hints`` on ``compare``, ``run_sensitivity`` or ``SensitivityRow``
needs ``localns=vars(launchsim.sim)``.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Callable, Container, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from launchsim.config import (
    BLOCKING_ROLE,
    DIAGNOSTIC_ROLE,
    NO_SEARCH,
    PLANAR_2D,
    VEHICLE_PREFIX,
    VERTICAL_1D,
    ChecksConfig,
    ResolvedExperiment,
    ResolvedRun,
    read_value,
    resolve_run,
)
from launchsim.dynamics import PLANAR_LAYOUT, PlanarDynamics2D
from launchsim.losses import LossBudget, loss_budget, rocket_equation_closure
from launchsim.metrics import metrics_record
from launchsim.phases import ASCENT_KINDS, ZERO_SPAN_S, PhaseResult, RunTrace
from launchsim.units import deg_to_rad, from_g, km_to_m, kn_to_n, kwh_to_j, t_to_kg
from launchsim.vehicle import Vehicle, ideal_dv_mps, payload_gain_kg, with_payload

if TYPE_CHECKING:
    from scipy.integrate import OdeSolution

    from launchsim.config import ChecksConfig
    from launchsim.sim import Result, RunResult


COMPARISON_BASIS = (
    "Comparison basis: sweep-optimized (Phase 1 has no guidance parameters); "
    "1-D vertical, vacuum thrust, no drag, no rotation, no throttling"
)


# YAML unit suffixes of config keys (config.py converts by the same suffixes) and their
# SI conversion (units.py) and unit, for the sensitivity table's SI column
# (``si_value``); a suffix listed with the identity is already SI. A key with no listed
# suffix is taken as dimensionless (a fraction such as drive_efficiency).
SI_SUFFIX_CONVERSIONS: dict[str, tuple[Callable[[float], float], str]] = {
    "t": (t_to_kg, "kg"),
    "kN": (kn_to_n, "N"),
    "deg": (deg_to_rad, "rad"),
    "km": (km_to_m, "m"),
    "g": (from_g, "m/s^2"),
    "kWh": (kwh_to_j, "J"),
    "s": (lambda x: x, "s"),
    "m": (lambda x: x, "m"),
    "kg": (lambda x: x, "kg"),
    "N": (lambda x: x, "N"),
    "Pa": (lambda x: x, "Pa"),
    "W": (lambda x: x, "W"),
    "J": (lambda x: x, "J"),
    "mps": (lambda x: x, "m/s"),
    "mps2": (lambda x: x, "m/s^2"),
}
DIMENSIONLESS_UNIT = "-"


# CLAUDE.md: the loss budget must close to 0.01 m/s; the same bound decides whether a
# variant's speed gain is "explained" (Checks section of the summary).
IDENTITY_TOL_MPS = 0.01
# A variant's integrated ignition loss is measured against ``silo_instant`` only when both
# start their flight from the same state (speed and altitude within these tolerances).
SAME_RELEASE_SPEED_TOL_MPS = 1e-6
SAME_RELEASE_ALT_TOL_M = 1e-6
INSTANT_VARIANT_NAME = "silo_instant"


CD_SENSITIVITY_NOTE = "n/a: no drag in Phase 1"
# What the Sensitivity section prints instead of a table when no case ran: the reason,
# set by the entry point that knows it (ExperimentResult.sensitivity_note).
SENSITIVITY_NONE_DECLARED = f"(no sensitivity block declared; C_D: {CD_SENSITIVITY_NOTE})"
SENSITIVITY_NONE_FOR_RUNS = (
    f"(no sensitivity cases declared for the runs that ran; C_D: {CD_SENSITIVITY_NOTE})"
)
SENSITIVITY_SKIPPED = "(sensitivity cases skipped: --no-sensitivity)"
SENSITIVITY_SWEEP_POINT = "(no sensitivity cases: a sweep point runs none)"


@dataclass(frozen=True)
class SensitivityRow:
    """One sensitivity case: ``of`` re-run with ``param`` moved by the signed ``fraction``
    (its perturbed value ``value_yaml_units``, the number as it stands in the config,
    i.e. in the parameter's YAML units such as t or s, not SI, kept so the case can be
    reproduced from the file; ``value_si`` the same number in SI with its unit
    ``value_si_unit``, from ``si_value``), compared against the unchanged baseline
    (``comparison``) and, for a ``vehicle.`` parameter, against the baseline re-run
    with the same vehicle perturbation (``baseline_perturbed``,
    ``comparison_perturbed``); for a run parameter the baseline is unaffected, so both
    comparisons are the same and ``baseline_perturbed`` is None."""

    of: str
    param: str
    fraction: float
    value_yaml_units: float | None
    value_si: float | None
    value_si_unit: str
    result: RunResult
    comparison: dict[str, Any]
    baseline_perturbed: RunResult | None
    comparison_perturbed: dict[str, Any]

    @property
    def is_vehicle_param(self) -> bool:
        """True when the parameter lives in the vehicle file (``vehicle.`` prefix)."""
        return self.param.startswith(VEHICLE_PREFIX)


# ---------------------------------------------------------------------- comparison


def _is_number(x: object) -> bool:
    """True for int/float and numpy numbers (bool excluded), finite or not."""
    return isinstance(x, int | float | np.integer | np.floating) and not isinstance(x, bool)


def _is_finite_number(x: object) -> bool:
    """True for a number that is neither NaN nor infinite."""
    return _is_number(x) and math.isfinite(float(x))


def _is_pandas_missing(x: object) -> bool:
    """True for the pandas missing scalars pd.NA and pd.NaT (an unavailable value)."""
    return x is pd.NA or x is pd.NaT


def _is_numeric_or_missing(x: object) -> bool:
    """True for a number (finite or not) or a pandas missing scalar: a numeric metric
    whose value may be unavailable."""
    return _is_number(x) or _is_pandas_missing(x)


def _delta(a: Any, b: Any) -> float | None:
    """a - b when both are finite numbers, else None (unavailable)."""
    if _is_finite_number(a) and _is_finite_number(b):
        return float(a) - float(b)
    return None


def identity_budget(result: Result) -> tuple[LossBudget, str] | None:
    """The loss budget the identity line of a run is written at, and the name of that
    point: ``stage1_burnout`` when the run reached a stage-1 burnout (the budget over
    the ascent phases up to and including the BURN ended by the propellant event, so
    speed_end is the burnout speed whatever the run's ``end``), else ``end`` (the run's
    own budget, e.g. the impact of a failed-ignition coast). None when the run has no
    budget (a hand-built Result) or never flew (an all-zero budget, no phases)."""
    if result.loss_budget is None:
        return None
    ascent = [p for p in result.phases if p.spec.kind in ASCENT_KINDS]
    if not ascent:
        return None
    for i, phase in enumerate(ascent):
        if phase.spec.stage_index == 0 and phase.ended_by == "propellant":
            return loss_budget(ascent[: i + 1]), "stage1_burnout"
    return result.loss_budget, "end"


def payload_equiv_kg(vehicle: Vehicle, dv_mps: float) -> float | None:
    """Ideal-screening payload equivalent [kg] of a delta-v gain dv_mps [m/s]: the
    payload change at which the ideal rocket-equation delta-v (``ideal_dv_mps``, the
    vehicle's loss-averaged screening Isp) moves by exactly -dv_mps. Positive dv gives
    ``payload_gain_kg`` (payload added); negative dv the payload that would have to be
    removed (brentq on [0, payload]), or None when even an empty payload bay cannot
    recover the loss. An ideal rocket equation at fixed losses: not a payload result.
    """
    if dv_mps >= 0.0:
        return payload_gain_kg(vehicle, dv_mps)
    p0 = vehicle.payload_mass_kg
    if p0 <= 0.0:
        return None
    dv0 = ideal_dv_mps(vehicle)
    target = dv0 - dv_mps  # the higher delta-v a lighter payload must give

    def shortfall(p: float) -> float:
        return ideal_dv_mps(vehicle, p) - target

    if shortfall(0.0) < 0.0:
        return None
    return float(brentq(shortfall, 0.0, p0)) - p0


def compare(
    result: Result,
    baseline: Result,
    vehicle: Vehicle | None = None,
    instant: Result | None = None,
) -> dict[str, Any]:
    """The comparison of a run against the baseline (docs/physics.md, "Figures of merit
    in 1-D"); SI, units in the keys.

    ``delta_<metric>`` for every numeric metric both results carry (unavailable when
    either operand is NaN, inf, pd.NA or pd.NaT: None, i.e. null in JSON, an empty CSV
    cell, "n/a" in a summary); ``status`` and ``baseline_status``. Then the 1-D figures
    of merit: ``stage1_burnout_speed_delta_mps`` and ``stage1_burnout_alt_delta_m``; the
    identity decomposition of the speed delta at ``identity_point`` (``identity_budget``:
    the stage-1 burnout of both runs when they reached it, else the run's end, named
    ``<variant point> vs <baseline point>`` when they differ), ``d_speed_mps`` =
    ``d_speed_release_mps`` (the flight-start speed: 0 on a pad, the exit speed on a
    track) + ``d_dv_vac_mps`` - ``d_gravity_duration_mps`` - ``d_gravity_alt_mps`` -
    ``d_drag_mps`` - ``d_steering_mps`` - ``d_back_pressure_mps`` +
    ``identity_line_residual_mps`` (expected ~1e-12 m/s; CLAUDE.md allows 0.01);
    ``hold_down_credit_mps``, the baseline's ``preflight_burn_cost_mps`` minus the
    run's (what a run gains by not burning while clamped, or loses by burning more);
    ``ignition_loss_formula_mps`` (the run's constant-g yardstick, copied for the side
    by side); ``ignition_loss_integrated_mps``, the ``instant`` run's stage-1 burnout
    speed minus this run's, defined only when both flew from the same release state
    (speed and altitude within SAME_RELEASE_*); ``ideal_screening_payload_equiv_kg``,
    ``payload_equiv_kg`` of the burnout speed delta on ``vehicle`` (ideal rocket
    equation at fixed losses; not a payload result);
    ``ideal_screening_payload_at_release_speed_kg``, the README yardstick the CLAUDE.md
    rule names: ``payload_gain_kg`` of this run's speed at release (0 for a pad), so
    the two payload figures can be compared in summary.md itself; and
    ``unexplained_gain_mps`` = d_speed - (d_speed_release + hold_down_credit -
    d_gravity_alt), the CLAUDE.md "beats the release speed" check: a gain beyond the
    release speed, the hold-down credit and the altitude term is unexplained when it
    exceeds IDENTITY_TOL_MPS (for the same vehicle it is minus the post-release
    ignition loss, the steering and the back-pressure deltas, so at most ~0). The
    check is defined at a stage-1 burnout on both sides only (``identity_point`` ==
    ``stage1_burnout``): a run without one (a failed ignition) gets None, since the
    credit and the altitude term of an impact-to-burnout difference mean nothing.
    Items either run lacks are None.
    """
    out: dict[str, Any] = {"status": result.status, "baseline_status": baseline.status}
    for key, value in result.metrics.items():
        base = baseline.metrics.get(key)
        if _is_numeric_or_missing(value) and _is_numeric_or_missing(base):
            out[f"delta_{key}"] = _delta(value, base)
    m, b = result.metrics, baseline.metrics
    d_bo = _delta(m.get("stage1_burnout_speed_mps"), b.get("stage1_burnout_speed_mps"))
    out["stage1_burnout_speed_delta_mps"] = d_bo
    out["stage1_burnout_alt_delta_m"] = _delta(
        m.get("stage1_burnout_alt_m"), b.get("stage1_burnout_alt_m")
    )
    terms = (
        ("d_speed_mps", "speed_end"),
        ("d_speed_release_mps", "speed_start"),
        ("d_dv_vac_mps", "dv_vac"),
        ("d_gravity_duration_mps", "gravity_duration"),
        ("d_gravity_alt_mps", "gravity_alt"),
        ("d_drag_mps", "drag"),
        ("d_steering_mps", "steering"),
        ("d_back_pressure_mps", "back_pressure"),
    )
    bv, bb = identity_budget(result), identity_budget(baseline)
    if bv is None or bb is None:
        out["identity_point"] = None
        out.update(dict.fromkeys([k for k, _ in terms]))
        out["identity_line_residual_mps"] = None
    else:
        out["identity_point"] = bv[1] if bv[1] == bb[1] else f"{bv[1]} vs {bb[1]}"
        for key, attr in terms:
            out[key] = getattr(bv[0], attr) - getattr(bb[0], attr)
        out["identity_line_residual_mps"] = out["d_speed_mps"] - (
            out["d_speed_release_mps"]
            + out["d_dv_vac_mps"]
            - out["d_gravity_duration_mps"]
            - out["d_gravity_alt_mps"]
            - out["d_drag_mps"]
            - out["d_steering_mps"]
            - out["d_back_pressure_mps"]
        )
    out["hold_down_credit_mps"] = _delta(
        b.get("preflight_burn_cost_mps"), m.get("preflight_burn_cost_mps")
    )
    out["ignition_loss_formula_mps"] = m.get("ignition_loss_formula_mps")
    out["ignition_loss_integrated_mps"] = None
    if instant is not None:
        same_v = _delta(m.get("speed_at_release_mps"), instant.metrics.get("speed_at_release_mps"))
        same_z = _delta(m.get("alt_at_release_m"), instant.metrics.get("alt_at_release_m"))
        if (
            same_v is not None
            and same_z is not None
            and abs(same_v) <= SAME_RELEASE_SPEED_TOL_MPS
            and abs(same_z) <= SAME_RELEASE_ALT_TOL_M
        ):
            out["ignition_loss_integrated_mps"] = _delta(
                instant.metrics.get("stage1_burnout_speed_mps"), m.get("stage1_burnout_speed_mps")
            )
    out["ideal_screening_payload_equiv_kg"] = (
        None if vehicle is None or d_bo is None else payload_equiv_kg(vehicle, d_bo)
    )
    v_release = m.get("speed_at_release_mps")
    out["ideal_screening_payload_at_release_speed_kg"] = (
        None
        if vehicle is None or not _is_finite_number(v_release) or float(v_release) < 0.0
        else payload_gain_kg(vehicle, float(v_release))
    )
    credit = out["hold_down_credit_mps"]
    out["unexplained_gain_mps"] = (
        None
        if out["identity_point"] != "stage1_burnout" or credit is None
        else out["d_speed_mps"] - (out["d_speed_release_mps"] + credit - out["d_gravity_alt_mps"])
    )
    return out


# --------------------------------------------------------------------- sensitivity


def perturbed_value(case_run: ResolvedRun, param: str) -> float | None:
    """The number a sensitivity case's dotted parameter has after the perturbation
    (``config.read_value`` on the case's run or vehicle dict, in the parameter's YAML
    units), or None when it is not a number."""
    if param.startswith(VEHICLE_PREFIX):
        value = read_value(case_run.vehicle_dict, param[len(VEHICLE_PREFIX) :])
    else:
        value = read_value(case_run.run_dict, param)
    return float(value) if _is_finite_number(value) else None


def si_value(param: str, value_yaml: float | None) -> tuple[float | None, str]:
    """A dotted config parameter's value in SI: (value, unit). The unit follows the
    key's YAML suffix (SI_SUFFIX_CONVERSIONS: ``_t`` -> kg through units.t_to_kg,
    ``_kN`` -> N, ``_deg`` -> rad, ``_km`` -> m, ``_g`` -> m/s^2, ``_kWh`` -> J; ``_s``,
    ``_m``, ``_kg`` ... unchanged), read off the last non-index segment of the path
    (``vehicle.screening.stage_isp_eff_s.0`` -> ``stage_isp_eff_s`` -> s). A key with
    no listed suffix (``assist.drive_efficiency``) is dimensionless: unchanged, unit
    DIMENSIONLESS_UNIT. None stays None."""
    segments = [s for s in param.split(".") if not s.isdigit()]
    key = segments[-1] if segments else param
    suffix = key.rsplit("_", 1)[-1] if "_" in key else ""
    convert, unit = SI_SUFFIX_CONVERSIONS.get(suffix, (lambda x: x, DIMENSIONLESS_UNIT))
    return (None if value_yaml is None else float(convert(value_yaml))), unit


def run_sensitivity(
    resolved: ResolvedExperiment,
    baseline: RunResult,
    run_names: Container[str] | None = None,
    nominal: Mapping[str, RunResult] | None = None,
) -> list[SensitivityRow]:
    """Run every sensitivity case of the experiment (``resolved.sensitivity``, already
    perturbed in memory by ``config.apply_overrides`` at load) whose parent run is in
    ``run_names`` (every case when None) and compare each against the unchanged
    baseline and, for a ``vehicle.`` parameter, against the baseline re-run with the
    same vehicle perturbation (one re-run per distinct perturbation, shared by the
    cases; a case of the baseline itself is its own perturbed baseline). Runs nothing
    when the experiment declares no sensitivity. Returns the rows in declaration
    order. Runs through ``sim.run_resolved``, looked up at call time. A planar_2d
    experiment goes to ``_run_planar_sensitivity`` (full searched runs, memoised
    energy-only and yardstick cases, the same-perturbation baseline), with nominal the
    runs already flown (the baseline alone when None)."""
    from launchsim import sim  # late: sim imports this module

    if resolved.baseline.run.dynamics == PLANAR_2D:
        runs = {baseline.name: baseline} if nominal is None else dict(nominal)
        return _run_planar_sensitivity(resolved, baseline, run_names, runs)
    rows: list[SensitivityRow] = []
    perturbed_baselines: dict[tuple[str, float], RunResult] = {}
    for case in resolved.sensitivity:
        if run_names is not None and case.of not in run_names:
            continue
        rr = sim.run_resolved(case.run)
        vehicle = case.run.to_vehicle()
        comparison = compare(rr.result, baseline.result, vehicle)
        base_pert: RunResult | None = None
        if case.param.startswith(VEHICLE_PREFIX):
            if case.of == baseline.name:
                base_pert = rr
            else:
                key = (case.param, case.fraction)
                if key not in perturbed_baselines:
                    perturbed_baselines[key] = sim.run_resolved(
                        resolve_run(
                            baseline.name, resolved.baseline.run_dict, case.run.vehicle_dict
                        )
                    )
                base_pert = perturbed_baselines[key]
        comparison_pert = (
            comparison if base_pert is None else compare(rr.result, base_pert.result, vehicle)
        )
        value_yaml = perturbed_value(case.run, case.param)
        value_si, unit = si_value(case.param, value_yaml)
        rows.append(
            SensitivityRow(
                of=case.of,
                param=case.param,
                fraction=case.fraction,
                value_yaml_units=value_yaml,
                value_si=value_si,
                value_si_unit=unit,
                result=rr,
                comparison=comparison,
                baseline_perturbed=base_pert,
                comparison_perturbed=comparison_pert,
            )
        )
    return rows


def sensitivity_record(row: SensitivityRow) -> dict[str, Any]:
    """The metrics.json record of one sensitivity case: the case, its perturbed value
    in SI (``value_si`` with ``value_si_unit``) and as it stands in the config
    (``value_yaml_units``: the parameter's YAML units, the one key of the record not in
    SI, kept to reproduce the case), the headline deltas against both baselines, the
    full metrics record and both comparisons. A planar case gets
    ``planar_sensitivity_record`` (payload items instead of the burnout speed)."""
    if row.result.result.model == PLANAR_2D:
        return planar_sensitivity_record(row)
    m = row.result.result.metrics
    return {
        "of": row.of,
        "param": row.param,
        "fraction": row.fraction,
        "value_si": row.value_si,
        "value_si_unit": row.value_si_unit,
        "value_yaml_units": row.value_yaml_units,
        "run": row.result.name,
        "status": row.result.result.status,
        "flags": row.result.result.flags,
        "stage1_burnout_speed_mps": m.get("stage1_burnout_speed_mps"),
        "stage1_burnout_speed_delta_mps": row.comparison.get("stage1_burnout_speed_delta_mps"),
        "stage1_burnout_speed_delta_vs_perturbed_baseline_mps": row.comparison_perturbed.get(
            "stage1_burnout_speed_delta_mps"
        ),
        "baseline_perturbed": row.baseline_perturbed is not None,
        "baseline_perturbed_stage1_burnout_speed_mps": (
            None
            if row.baseline_perturbed is None
            else row.baseline_perturbed.result.metrics.get("stage1_burnout_speed_mps")
        ),
        "metrics": metrics_record(row.result.result),
        "comparison": row.comparison,
        "comparison_vs_perturbed_baseline": row.comparison_perturbed,
    }


# ------------------------------------------------------------------ planar comparison

PLANAR_COMPARISON_BASIS = (
    "Comparison basis: sweep-optimized (every run shares the guidance parametrisation, the "
    "gamma* grid and the search budget; gamma*, delta and the LTG pair are solved per run); "
    "planar_2d: rotating spherical Earth, ICAO atmosphere, drag, back-pressure, "
    "unthrottled; figure of merit: payload capacity P* at the target orbit"
)
"""The comparison basis line of a searched planar summary (the 1-D one is
COMPARISON_BASIS)."""
PLANAR_FIXED_COMPARISON_BASIS = (
    "Comparison basis: fixed guidance (every run flies the shared fixed gamma* and LTG pair "
    "(a, b); only the kick angle delta is solved per run; no payload search, so no P*); "
    "planar_2d: rotating spherical Earth, ICAO atmosphere, drag, back-pressure, "
    "unthrottled; figures of merit: residual propellant and dv margin of the recorded run "
    "at the vehicle payload (a run can end off target)"
)
"""The comparison basis line of a planar summary with figure_of_merit none."""


def planar_comparison_basis(figure_of_merit: str | None) -> str:
    """The planar comparison basis for the experiment's shared figure of merit:
    PLANAR_FIXED_COMPARISON_BASIS for none (fixed guidance), else
    PLANAR_COMPARISON_BASIS."""
    return (
        PLANAR_FIXED_COMPARISON_BASIS if figure_of_merit == NO_SEARCH else PLANAR_COMPARISON_BASIS
    )


PLANAR_CD_SENSITIVITY_NOTE = "drag is modelled: see the vehicle.aero.cd_scale cases"
"""What a planar summary says about C_D sensitivity (the 1-D model has no drag)."""
COMPARISON_BASES: dict[str, str] = {
    VERTICAL_1D: COMPARISON_BASIS,
    PLANAR_2D: PLANAR_COMPARISON_BASIS,
}
"""The comparison basis per dynamics model."""
CD_SENSITIVITY_NOTES: dict[str, str] = {
    VERTICAL_1D: CD_SENSITIVITY_NOTE,
    PLANAR_2D: PLANAR_CD_SENSITIVITY_NOTE,
}
"""The C_D sensitivity note per dynamics model."""

SCREENING_OK = "ok"
"""Screening status of a variant with a matched-payload attribution whose applicable
blocking checks all pass (a failed diagnostic check, M2 by default, does not change it)."""
SCREENING_NOT_CHECKED = "not_checked"
"""Screening status of a comparison without a matched-payload attribution and without a
failed check: by design for a comparison across two vehicles (``attribution_required``
False: a vehicle-parameter sensitivity case or a bound against the unchanged
baseline), or a variant with no rung-2 run at the matched payload that does not beat
the screening yardstick (a failed ignition). Its dP* is not explained by a loss breakdown,
so it supports no finding about a beat."""
BUG_SUSPECT = "bug_suspect"
"""Status of a run or comparison that fails a pre-registered blocking check
(docs/physics.md, "Screening-beat rule (2-D)"): it blocks findings until investigated."""
CHECK_PASS = "pass"
CHECK_FAIL = "fail"
CHECK_NA = "n/a"
"""Outcome of one mechanism check (n/a: not applicable to this pair)."""
ROLE_KEY = "role"
"""Key of a check record's role (config.CheckRole); a record without it is blocking."""


def check_role(rec: Mapping[str, Any]) -> str:
    """The role of one check record: its ``role`` item (config.DIAGNOSTIC_ROLE or
    BLOCKING_ROLE), BLOCKING_ROLE when it has none (every check but M2). Input: a
    ``checks_<name>`` record; output: the role string."""
    return str(rec.get(ROLE_KEY, BLOCKING_ROLE))


def is_diagnostic(rec: Mapping[str, Any]) -> bool:
    """True when the check record is diagnostic only: its fail is reported but gives no
    bug_suspect and blocks no finding (docs/physics.md, "Screening-beat rule (2-D)")."""
    return check_role(rec) == DIAGNOSTIC_ROLE


def gamma_sensitivity_step_rad(checks: ChecksConfig) -> float:
    """The gamma* step h [rad] of the gamma*-sensitivity diagnostic, from the
        pre-registered ``checks.gamma_sensitivity_step_deg`` (0.5 deg as shipped): a searched
    variant's matched run is also evaluated at gamma*_ref - h and + h, at P_ref. The total d
    dv_margin is (nearly) stationary in gamma* but its gravity and steering terms trade against each
    other to first order, so the per-term split, M2, M3 and M4 are read together with their
    range over +/- h (docs/physics.md, "Screening-beat rule (2-D)"). A diagnostic: it never
        changes a check's pre-registered verdict at gamma*_ref. Input: the run's checks block;
        output: h in radians."""
    return float(deg_to_rad(checks.gamma_sensitivity_step_deg))


GRAVITY_STEERING = "gravity_steering"
"""Name of the joint gravity + steering contribution: the part of the attribution that
does not move to first order with gamma* (the individual terms do)."""

ATTRIBUTION_TERMS: tuple[str, ...] = (
    "release_speed",
    "final_speed",
    "gravity",
    "drag",
    "steering",
    "back_pressure",
    "preflight",
    "fairing",
)
"""The terms of the matched-payload attribution, in the order of
d dv_margin = dV_0 - dV_f - dJ_grav - dJ_drag - dJ_steer - dJ_bp - d pre - d fair
(docs/physics.md, "Screening-beat rule (2-D)"); each is a contribution to d dv_margin
[m/s] (positive: in the variant's favour)."""


@dataclass(frozen=True, eq=False)
class MatchedRun:
    """A rung-2 run at the matched payload (amendment 16: executed in ``sim``, handed to
    ``compare_planar``): name; payload_kg [kg] (P_ref, the baseline's P*);
    gamma_star_rad [rad], the run's own sweep-optimized gamma*; the trace from the
    prelude to the stage-2 energy cutoff (a final-mode evaluation with virtual
    propellant, so it reaches the cutoff even above the run's capacity; burnouts, the
    flight start and the fairing event are what the closure reads); the vehicle at
    payload_kg; omega_p_rads [rad/s] and r_datum_m [m] of the run (|v_rel| needs them);
    neighbours, the same evaluation at gamma* - h and gamma* + h, h from
    ``gamma_sensitivity_step_rad`` (in that order; None when not evaluated: the baseline,
    a run without a search, an infeasible neighbour), for the gamma*-sensitivity
    diagnostic of the attribution and the mechanism checks. Frame: planar ECI."""

    name: str
    payload_kg: float
    gamma_star_rad: float
    trace: RunTrace
    vehicle: Vehicle
    omega_p_rads: float
    r_datum_m: float
    neighbours: tuple[MatchedRun, MatchedRun] | None = None


@dataclass(frozen=True)
class Anchor:
    """The M5 anchor of an experiment: d_payload_kg [kg], dP*(silo_instant vs
    pad_instant) (the release speed alone, both lit at release); pad_preflight_kg [kg],
    the ideal-screening payload equivalent of the baseline pad's pre-flight term
    c1 ln(m0/m_fs) (what the pad spends clamped); release_speed_mps [m/s] of
    silo_instant (the variants M5 applies to release at it)."""

    d_payload_kg: float
    pad_preflight_kg: float
    release_speed_mps: float


def attribution_terms(run: MatchedRun) -> dict[str, float]:
    """The per-run terms of the attribution [m/s]: V_0 and V_f (|v_rel| at the flight
    start and at the cutoff), J_grav, J_drag, J_steer, J_bp (the loss budget over the
    flight phases, ``losses.loss_budget`` with the planar speed), pre and fair and the
    dv margin (``losses.rocket_equation_closure`` at the run's payload), with the
    closure and identity residuals."""
    speed = PlanarDynamics2D(run.omega_p_rads, run.r_datum_m).speed
    budget = loss_budget(run.trace.ascent_phases(), PLANAR_LAYOUT, speed)
    closure = rocket_equation_closure(run.trace, run.vehicle)
    return {
        "V_0": budget.speed_start,
        "V_f": budget.speed_end,
        "J_grav": budget.gravity,
        "J_drag": budget.drag,
        "J_steer": budget.steering,
        "J_bp": budget.back_pressure,
        "pre": closure.pre_mps,
        "fair": closure.fair_mps,
        "dv_margin": closure.dv_margin_mps,
        "closure_residual": closure.residual_mps,
        "identity_residual": budget.residual_mps(),
        "J_grav_meco": _gravity_at_meco(run.trace),
    }


def _gravity_at_meco(trace: RunTrace) -> float | None:
    """J_grav [m/s] at the stage-1 burnout (the earliest burnout) of a planar trace: the
    gravity loss from the flight start to MECO; None without a burnout."""
    if not trace.burnouts:
        return None
    _t, y = min(trace.burnouts.values(), key=lambda item: item[0])
    return float(PLANAR_LAYOUT.get(np.asarray(y, dtype=float), "J_grav_mps"))


def _contributions(tv: dict[str, float], tb: dict[str, float]) -> dict[str, float]:
    """The ATTRIBUTION_TERMS contributions [m/s] from the variant's and the baseline's
    terms (d = variant - baseline): +dV_0, -dV_f, -dJ_grav, -dJ_drag, -dJ_steer,
    -dJ_bp, -d pre, -d fair."""
    return {
        "release_speed": tv["V_0"] - tb["V_0"],
        "final_speed": -(tv["V_f"] - tb["V_f"]),
        "gravity": -(tv["J_grav"] - tb["J_grav"]),
        "drag": -(tv["J_drag"] - tb["J_drag"]),
        "steering": -(tv["J_steer"] - tb["J_steer"]),
        "back_pressure": -(tv["J_bp"] - tb["J_bp"]),
        "preflight": -(tv["pre"] - tb["pre"]),
        "fairing": -(tv["fair"] - tb["fair"]),
    }


def matched_attribution(
    variant: MatchedRun, baseline: MatchedRun, d_payload_kg: float | None
) -> dict[str, Any]:
    """The matched-payload attribution of a variant against the baseline, both at
    P_ref (docs/physics.md, "Screening-beat rule (2-D)"). With d = variant - baseline
    and the same D_id(P_ref) on both sides, exactly (up to the two runs' closure and
    identity residuals):

        d dv_margin = dV_0 - dV_f - dJ_grav - dJ_drag - dJ_steer - dJ_bp - d pre - d fair

    (dV_f is carried explicitly: V_f equals the target's V_rel,f only within the LTG
    acceptance). Output keys (m/s unless kg): ``attr_payload_kg`` (P_ref),
    ``attr_gamma_star_rad`` and ``attr_baseline_gamma_star_rad``, ``attr_m_res_kg`` (the
    variant's signed residual at P_ref), ``attr_d_dv_margin_mps``, ``attr_<term>_mps``
    for every ATTRIBUTION_TERMS term, ``attr_residual_mps`` = d dv_margin - sum of the
    terms, ``attr_beyond_release_mps`` (the sum without the release-speed term) and, when
    d_payload_kg (dP*) is finite and the sum is not 0, ``attr_<term>_kg`` = dP* x term /
    sum, a split that adds up to dP* exactly (None otherwise); the two runs' closure and
    loss-identity residuals (``attr_{variant,baseline}_{closure,identity}_residual_mps``,
    checked by the ``attribution`` check); ``attr_gravity_stage1_mps``, the part of the
    gravity term from the flight start to MECO, -(d J_grav at MECO) (a diagnostic of
    M2: the rest comes from the staging coast and the stage-2 burn; None without both
    burnouts). ``attr_gravity_steering_mps`` (and ``_kg``) is the joint gravity +
    steering contribution: the individual terms trade against each other to first order
    in gamma*, the sum does not, so only the sum is read as physics. When the variant
    carries neighbours (``MatchedRun.neighbours``, gamma* -/+ h): ``attr_gamma_step_rad``
    (h), ``attr_<term>_dgamma_mps_per_rad`` for every term and the joint one (central
    difference, (c(+h) - c(-h))/(2 h), in m/s per rad) and ``attr_neighbours``, the
    contributions at -h and +h (``minus``, ``plus``: every term, the joint one and
    ``beyond_release``), which the M2 to M4 records read; all None without neighbours.
    Raises ValueError when the two runs are not at the same payload."""
    if variant.payload_kg != baseline.payload_kg:
        raise ValueError(
            f"matched attribution needs one payload: {variant.name} at {variant.payload_kg} kg, "
            f"{baseline.name} at {baseline.payload_kg} kg"
        )
    tv, tb = attribution_terms(variant), attribution_terms(baseline)
    contrib = _contributions(tv, tb)
    total = math.fsum(contrib.values())
    d_margin = tv["dv_margin"] - tb["dv_margin"]
    split = d_payload_kg is not None and _is_finite_number(d_payload_kg) and total != 0.0
    out: dict[str, Any] = {
        "attr_payload_kg": variant.payload_kg,
        "attr_gamma_star_rad": variant.gamma_star_rad,
        "attr_baseline_gamma_star_rad": baseline.gamma_star_rad,
        "attr_d_dv_margin_mps": d_margin,
    }
    for term in ATTRIBUTION_TERMS:
        out[f"attr_{term}_mps"] = contrib[term]
    out["attr_residual_mps"] = d_margin - total
    out["attr_beyond_release_mps"] = total - contrib["release_speed"]
    for term in ATTRIBUTION_TERMS:
        out[f"attr_{term}_kg"] = (
            float(d_payload_kg) * contrib[term] / total if split else None  # type: ignore[arg-type]
        )
    out["attr_variant_closure_residual_mps"] = tv["closure_residual"]
    out["attr_baseline_closure_residual_mps"] = tb["closure_residual"]
    out["attr_variant_identity_residual_mps"] = tv["identity_residual"]
    out["attr_baseline_identity_residual_mps"] = tb["identity_residual"]
    g_v, g_b = tv["J_grav_meco"], tb["J_grav_meco"]
    out["attr_gravity_stage1_mps"] = None if g_v is None or g_b is None else -(g_v - g_b)
    out[f"attr_{GRAVITY_STEERING}_mps"] = contrib["gravity"] + contrib["steering"]
    out[f"attr_{GRAVITY_STEERING}_kg"] = (
        out["attr_gravity_kg"] + out["attr_steering_kg"] if split else None
    )
    out.update(_gamma_sensitivity(variant, tb))
    return out


def _with_joint(contrib: Mapping[str, float]) -> dict[str, float]:
    """The contributions [m/s] plus the joint gravity + steering one and
    ``beyond_release`` (the sum of every term but the release speed)."""
    out = dict(contrib)
    out[GRAVITY_STEERING] = contrib["gravity"] + contrib["steering"]
    out["beyond_release"] = math.fsum(contrib.values()) - contrib["release_speed"]
    return out


def _gamma_sensitivity(variant: MatchedRun, tb: Mapping[str, float]) -> dict[str, Any]:
    """The gamma*-sensitivity items of ``matched_attribution`` (see there) from the
    variant's neighbours and the baseline's terms tb; None-valued without neighbours."""
    keys = [*ATTRIBUTION_TERMS, GRAVITY_STEERING]
    out: dict[str, Any] = {"attr_gamma_step_rad": None, "attr_neighbours": None}
    out.update({f"attr_{t}_dgamma_mps_per_rad": None for t in keys})
    if variant.neighbours is None:
        return out
    minus, plus = variant.neighbours
    step = 0.5 * (plus.gamma_star_rad - minus.gamma_star_rad)
    c_minus = _with_joint(_contributions(attribution_terms(minus), dict(tb)))
    c_plus = _with_joint(_contributions(attribution_terms(plus), dict(tb)))
    out["attr_gamma_step_rad"] = step
    out["attr_neighbours"] = {"minus": c_minus, "plus": c_plus}
    for t in keys:
        out[f"attr_{t}_dgamma_mps_per_rad"] = (c_plus[t] - c_minus[t]) / (2.0 * step)
    return out


ATTRIBUTION_KEYS: tuple[str, ...] = (
    "attr_payload_kg",
    "attr_gamma_star_rad",
    "attr_baseline_gamma_star_rad",
    "attr_d_dv_margin_mps",
    *(f"attr_{t}_mps" for t in ATTRIBUTION_TERMS),
    "attr_residual_mps",
    "attr_beyond_release_mps",
    *(f"attr_{t}_kg" for t in ATTRIBUTION_TERMS),
    "attr_variant_closure_residual_mps",
    "attr_baseline_closure_residual_mps",
    "attr_variant_identity_residual_mps",
    "attr_baseline_identity_residual_mps",
    "attr_gravity_stage1_mps",
    f"attr_{GRAVITY_STEERING}_mps",
    f"attr_{GRAVITY_STEERING}_kg",
    "attr_gamma_step_rad",
    "attr_neighbours",
    *(f"attr_{t}_dgamma_mps_per_rad" for t in (*ATTRIBUTION_TERMS, GRAVITY_STEERING)),
)
"""The keys of ``matched_attribution`` (the gamma*-sensitivity keys last); a comparison
without an attribution carries them as None (one schema for every planar
comparison)."""


def _state_at(phases: Sequence[PhaseResult], t: float) -> np.ndarray:
    """The planar state at absolute time t [s] from the recorded flight phases (the end
    state exactly at a phase end, else the dense output of the phase that spans t);
    ValueError outside them or for a phase without dense output."""
    for res in phases:
        if res.spec.t0 - ZERO_SPAN_S <= t <= res.t_end + ZERO_SPAN_S:
            if abs(t - res.t_end) <= ZERO_SPAN_S:
                return np.asarray(res.y_end, dtype=float)
            if abs(t - res.spec.t0) <= ZERO_SPAN_S:
                return np.asarray(res.y[:, 0], dtype=float)
            if res.dense is None:
                raise ValueError(f"phase {res.spec.kind} has no dense output at t = {t:.9g} s")
            return np.asarray(res.dense(t), dtype=float)
    raise ValueError(f"no flight phase spans t = {t:.9g} s")


def time_to_speed_s(
    trace: RunTrace, v0_mps: float, omega_p_rads: float, r_datum_m: float
) -> float | None:
    """t_v0 [s]: the baseline's time from its flight start to the first instant its
    Earth-relative speed |v_rel| reaches v0_mps [m/s] (brentq on the dense output of the
    first flight phase in which it does); 0 when it starts at or above v0; None when it
    never does. Frame: planar, v_rel relative to the co-rotating air."""
    speed = PlanarDynamics2D(omega_p_rads, r_datum_m).speed
    phases = trace.ascent_phases()
    if not phases or trace.t_flight_start_s is None:
        return None
    if float(speed(phases[0].y[:, 0])) >= v0_mps:
        return 0.0
    for res in phases:
        if float(speed(res.y_end)) < v0_mps:
            continue
        if res.dense is None:
            raise ValueError(f"phase {res.spec.kind} has no dense output")
        dense = res.dense

        def excess(t: float, dense: OdeSolution = dense) -> float:
            return float(speed(np.asarray(dense(t), dtype=float))) - v0_mps

        t_hit = float(brentq(excess, res.spec.t0, res.t_end))
        return t_hit - trace.t_flight_start_s
    return None


def time_shift_estimate_mps(trace: RunTrace, t_v0_s: float, quadrature: str) -> float:
    """The time-shift estimate [m/s] of a loss quadrature over the baseline's own
    recorded trajectory (docs/physics.md, "Time-shift mechanism (2-D gravity loss)"):

        est = [Q(t_MECO) - Q(t_MECO - t_v0)] - [Q(t_fs + t_v0) - Q(t_fs)]

    with Q the quadrature (J_grav_mps for M2, J_bp_mps for M3) read off the dense
    output, t_fs the flight start and t_MECO the stage-1 burnout (the earliest burnout).
    ValueError without a flight start or a burnout."""
    if not trace.burnouts or trace.t_flight_start_s is None:
        raise ValueError("the time-shift estimate needs a flight start and a stage-1 burnout")
    t_fs = trace.t_flight_start_s
    t_meco = min(t for t, _y in trace.burnouts.values())
    phases = trace.ascent_phases()

    def q(t: float) -> float:
        return float(PLANAR_LAYOUT.get(_state_at(phases, t), quadrature))

    return (q(t_meco) - q(t_meco - t_v0_s)) - (q(t_fs + t_v0_s) - q(t_fs))


def _ratio_check(
    d_mps: float, est_mps: float, bounds: tuple[float, float]
) -> tuple[str, float | None]:
    """(pass or fail, d/est): pass when d/est lies in bounds (a positive ratio: the
    same sign as the estimate); fail for a zero estimate with a nonzero d."""
    if est_mps == 0.0:
        return (CHECK_PASS, None) if d_mps == 0.0 else (CHECK_FAIL, None)
    ratio = d_mps / est_mps
    return (CHECK_PASS if bounds[0] <= ratio <= bounds[1] else CHECK_FAIL), ratio


PAD_INSTANT_NAME = "pad_instant"
"""The pad variant lit at release with a step start: with INSTANT_VARIANT_NAME the M5
anchor pair (the release speed alone)."""
ANCHOR_NAMES = frozenset({INSTANT_VARIANT_NAME, PAD_INSTANT_NAME})


def _check_row(status: str, **values: Any) -> dict[str, Any]:
    """One check's record: its status and its numbers."""
    return {"status": status, **values}


def _gamma_range(
    status: str,
    value: float | None,
    neighbours: Sequence[tuple[str, float | None]] | None,
) -> dict[str, Any]:
    """The gamma*-sensitivity items of a check record: ``value_range`` [min, max] of the
    check's number (ratio or share) at gamma*_ref and at its two neighbours (the finite
    ones), ``neighbour_status`` (the verdict at -h and +h) and ``gamma_robust`` (True
    when all three verdicts agree, False when the verdict changes within +/- h, None
    without neighbours). A diagnostic: the record's status stays the verdict at
    gamma*_ref (pre-registered)."""
    if neighbours is None:
        return {"value_range": None, "neighbour_status": None, "gamma_robust": None}
    values = [v for v in (value, *(n[1] for n in neighbours)) if v is not None]
    statuses = [status, *(n[0] for n in neighbours)]
    return {
        "value_range": [min(values), max(values)] if values else None,
        "neighbour_status": [n[0] for n in neighbours],
        "gamma_robust": len(set(statuses)) == 1,
    }


def _neighbour_terms(attribution: Mapping[str, Any]) -> list[Mapping[str, float]] | None:
    """The contributions [m/s] at gamma* - h and + h (``attr_neighbours``), or None."""
    near = attribution.get("attr_neighbours")
    return None if near is None else [near["minus"], near["plus"]]


def _m2_m3(
    result: Result,
    baseline: Result,
    attribution: Mapping[str, Any] | None,
    checks: ChecksConfig,
) -> dict[str, dict[str, Any]]:
    """Mechanism checks M2 (gravity) and M3 (back-pressure): the matched-payload d J
    (variant - baseline at P_ref, the attribution's term with its sign flipped) against
    the time-shift estimate over the baseline's recorded trajectory, t_v0 being the
    baseline's time from its flight start to the variant's release speed. Applicable
    only to a variant that releases faster than the baseline (the time-shift mechanism
    exists), with an attribution and a recorded baseline; M3 also needs |d J_bp| >
    checks.min_term_mps. Pass when d J / estimate lies in checks.grav_ratio_bounds or
    bp_ratio_bounds. The M2 record also carries, as a diagnostic that does not change
    its status, the stage-1 part of d J_grav (flight start to MECO, ``d_stage1_mps``)
    and its ratio to the same estimate (``ratio_stage1``): the estimate models stage 1
    only (docs/physics.md, "Screening-beat rule (2-D)"). Both records carry the ratio's
    range over the variant's gamma* +/- h (``_gamma_range``: ``value_range``,
    ``neighbour_status``, ``gamma_robust``) when the attribution has neighbours: the
    baseline and its estimate stay fixed, only the variant's d J moves. The M2 record's
    ``role`` (checks.m2_role) is added by ``compare_planar``; the numbers and the verdict
    here do not depend on it."""
    na = {"m2": _check_row(CHECK_NA), "m3": _check_row(CHECK_NA)}
    v0 = result.metrics.get("speed_at_release_mps")
    v0_b = baseline.metrics.get("speed_at_release_mps")
    trace = baseline.trace
    if (
        attribution is None
        or trace is None
        or not (_is_finite_number(v0) and _is_finite_number(v0_b))
        or float(v0) <= float(v0_b) + SAME_RELEASE_SPEED_TOL_MPS
    ):
        return na
    view = trace.view
    t_v0 = time_to_speed_s(
        trace,
        float(v0),
        view.omega_p_rads,
        view.r_datum_m,  # type: ignore[attr-defined]
    )
    if t_v0 is None:
        return na
    out: dict[str, dict[str, Any]] = {}
    near = _neighbour_terms(attribution)
    d_grav = -float(attribution["attr_gravity_mps"])
    est = time_shift_estimate_mps(trace, t_v0, "J_grav_mps")
    status, ratio = _ratio_check(d_grav, est, checks.grav_ratio_bounds)
    stage1 = attribution.get("attr_gravity_stage1_mps")
    d_stage1 = None if stage1 is None else -float(stage1)
    ratio_stage1 = None if d_stage1 is None or est == 0.0 else d_stage1 / est
    around = (
        None
        if near is None
        else [_ratio_check(-float(c["gravity"]), est, checks.grav_ratio_bounds) for c in near]
    )
    out["m2"] = _check_row(
        status,
        d_mps=d_grav,
        estimate_mps=est,
        ratio=ratio,
        t_v0_s=t_v0,
        d_stage1_mps=d_stage1,
        ratio_stage1=ratio_stage1,
        **_gamma_range(status, ratio, around),
    )
    d_bp = -float(attribution["attr_back_pressure_mps"])
    if abs(d_bp) <= checks.min_term_mps:
        out["m3"] = _check_row(CHECK_NA, d_mps=d_bp)
    else:
        est_bp = time_shift_estimate_mps(trace, t_v0, "J_bp_mps")
        status, ratio = _ratio_check(d_bp, est_bp, checks.bp_ratio_bounds)
        around = (
            None
            if near is None
            else [
                _ratio_check(-float(c["back_pressure"]), est_bp, checks.bp_ratio_bounds)
                for c in near
            ]
        )
        out["m3"] = _check_row(
            status,
            d_mps=d_bp,
            estimate_mps=est_bp,
            ratio=ratio,
            t_v0_s=t_v0,
            **_gamma_range(status, ratio, around),
        )
    return out


def _m4(attribution: Mapping[str, Any] | None, checks: ChecksConfig) -> dict[str, Any]:
    """Mechanism check M4: drag plus steering, d(J_drag + J_steer) as contributions in the
    variant's favour, carry at most checks.max_drag_steer_share of the gain beyond the
    release speed (``attr_beyond_release_mps``); n/a without an attribution or when that
    gain is below checks.min_term_mps (a share of a near-zero gain is noise: amendment
    3's absolute floor). With the attribution's neighbours the record carries the
    share's range over gamma* +/- h (``_gamma_range``)."""
    if attribution is None:
        return _check_row(CHECK_NA)

    def share_of(drag_steer: float, beyond: float) -> tuple[str, float | None]:
        if beyond < checks.min_term_mps:
            return CHECK_NA, None
        share = drag_steer / beyond
        return (CHECK_PASS if share <= checks.max_drag_steer_share else CHECK_FAIL), share

    beyond = float(attribution["attr_beyond_release_mps"])
    drag_steer = float(attribution["attr_drag_mps"]) + float(attribution["attr_steering_mps"])
    status, share = share_of(drag_steer, beyond)
    near = _neighbour_terms(attribution)
    around = (
        None
        if near is None
        else [share_of(c["drag"] + c["steering"], c["beyond_release"]) for c in near]
    )
    if share is None:
        return _check_row(
            status,
            drag_steer_mps=drag_steer,
            beyond_release_mps=beyond,
            **_gamma_range(status, None, around),
        )
    return _check_row(
        status,
        drag_steer_mps=drag_steer,
        beyond_release_mps=beyond,
        share=share,
        **_gamma_range(status, share, around),
    )


def _m5(
    name: str, result: Result, d_payload: float | None, anchor: Anchor | None, checks: ChecksConfig
) -> dict[str, Any]:
    """Mechanism check M5 (the anchor bound): a named variant released at the anchor's
    release speed (within SAME_RELEASE_SPEED_TOL_MPS; not an anchor run itself) must not
    beat dP*(silo_instant vs pad_instant) + the pad's pre-flight term in kg +
    checks.anchor_margin_kg."""
    v0 = result.metrics.get("speed_at_release_mps")
    if (
        anchor is None
        or name in ANCHOR_NAMES
        or d_payload is None
        or not _is_finite_number(v0)
        or abs(float(v0) - anchor.release_speed_mps) > SAME_RELEASE_SPEED_TOL_MPS
    ):
        return _check_row(CHECK_NA)
    bound = anchor.d_payload_kg + anchor.pad_preflight_kg + checks.anchor_margin_kg
    status = CHECK_PASS if d_payload <= bound else CHECK_FAIL
    return _check_row(status, d_payload_kg=d_payload, bound_kg=bound)


def _closure_check(result: Result, baseline: Result, checks: ChecksConfig) -> dict[str, Any]:
    """The rocket-equation closure of the variant and, when it has one, of the baseline
    (``closure_residual_mps`` below checks.closure_tol_mps); n/a when the variant did
    not burn stage 2 (a failed ignition: the baseline's closure is its own per-run
    check, not this variant's), with the baseline's residual recorded."""
    variant = result.metrics.get("closure_residual_mps")
    base = baseline.metrics.get("closure_residual_mps")
    base_value = float(base) if _is_finite_number(base) else None
    if not _is_finite_number(variant):
        return _check_row(CHECK_NA, variant_residual_mps=None, baseline_residual_mps=base_value)
    values = [float(variant), *([] if base_value is None else [base_value])]
    worst = max(abs(v) for v in values)
    status = CHECK_PASS if worst < checks.closure_tol_mps else CHECK_FAIL
    return _check_row(
        status,
        worst_residual_mps=worst,
        variant_residual_mps=float(variant),
        baseline_residual_mps=base_value,
    )


ATTRIBUTION_MISSING_REASON = "no rung-2 run at the matched payload"
"""Why a required attribution is missing (``sim.matched_run`` gave None: a failed
ignition, a typed guidance failure at P_ref, a failed search)."""
ATTRIBUTION_NOT_REQUIRED_REASON = (
    "not attributed by design (a comparison across a vehicle perturbation: a sensitivity "
    "case or a bound against the unchanged baseline)"
)
"""Why a comparison without ``attribution_required`` carries no attribution: the two
runs fly different vehicles, so no matched-payload attribution exists (the case against
the same-perturbation baseline, and a bound against its paired baseline, are attributed
instead)."""


def _attribution_check(
    attribution: Mapping[str, Any] | None,
    beats: bool | None,
    required: bool,
    checks: ChecksConfig,
) -> dict[str, Any]:
    """The attribution check of the screening-beat rule: an attribution must close (its
    residual and both matched runs' closure residuals below checks.closure_tol_mps [m/s],
    both matched runs' loss-identity residuals below checks.identity_tol_mps [m/s]).
    Without an attribution: fail when one was required and the run beats the screening
    yardstick (an unexplained beat, which CLAUDE.md treats as a bug), else n/a with the
    reason."""
    if attribution is None:
        if required and beats is True:
            return _check_row(
                CHECK_FAIL, reason=f"beats the screening yardstick; {ATTRIBUTION_MISSING_REASON}"
            )
        reason = ATTRIBUTION_MISSING_REASON if required else ATTRIBUTION_NOT_REQUIRED_REASON
        return _check_row(CHECK_NA, reason=reason)
    closures = (
        attribution["attr_residual_mps"],
        attribution["attr_variant_closure_residual_mps"],
        attribution["attr_baseline_closure_residual_mps"],
    )
    identities = (
        attribution["attr_variant_identity_residual_mps"],
        attribution["attr_baseline_identity_residual_mps"],
    )
    worst_closure = max(abs(float(x)) for x in closures)
    worst_identity = max(abs(float(x)) for x in identities)
    ok = worst_closure < checks.closure_tol_mps and worst_identity < checks.identity_tol_mps
    return _check_row(
        CHECK_PASS if ok else CHECK_FAIL,
        worst_closure_mps=worst_closure,
        worst_identity_mps=worst_identity,
    )


SCREENING_BASIS_P0 = "P0"
"""The screening yardstick taken on the vehicle at its own payload P0."""
SCREENING_BASIS_PBASE = "P*_base"
"""The screening yardstick taken on the vehicle at the baseline's P*."""


def compare_planar(
    result: Result,
    baseline: Result,
    vehicle: Vehicle,
    *,
    checks: ChecksConfig,
    name: str = "",
    matched: MatchedRun | None = None,
    matched_baseline: MatchedRun | None = None,
    anchor: Anchor | None = None,
    attribution_required: bool = True,
) -> dict[str, Any]:
    """The comparison of a planar run against the baseline (docs/physics.md,
    "Screening-beat rule (2-D)"); SI, units in the keys; pure (the matched-payload runs
    are executed by ``sim`` and passed in, amendment 16).

    ``status``, ``baseline_status`` and ``delta_<metric>`` for every numeric metric both
    carry (None when unavailable). The headline ``payload_delta_kg`` = dP* (variant -
    baseline). The ideal screening yardstick at this run's release speed
    (``vehicle.payload_gain_kg``) at the vehicle payload P0
    (``ideal_screening_payload_at_release_speed_kg``) and at the baseline's P*
    (``..._at_pbase_kg``); ``screening_yardstick_kg``, the stricter (smaller) of the two
    that exist, and ``screening_yardstick_basis`` (SCREENING_BASIS_P0 or
    SCREENING_BASIS_PBASE), so a run that beats either yardstick counts as a beat;
    ``payload_beyond_screening_kg`` = dP* - screening_yardstick_kg and
    ``beats_screening`` (True when positive: the loss attribution must then explain it).
    ``max_q_above_baseline``, ``q_alpha_above_baseline`` and ``unconstrained_kick``
    (this run kicks faster than checks.unconstrained_kick_mps [m/s], where the missing
    angle-of-attack aerodynamics would cost most); ``payload_delta_upper_bound`` is True
    when any of the three is (the dP* is then an unthrottled / unconstrained upper
    bound). With matched and matched_baseline (both at P_ref = P*_base):
    ``matched_attribution``. The checks (``checks_<name>`` records: closure,
    attribution, m2, m3, m4, m5; ``_attribution_check`` fails an unexplained beat when
    ``attribution_required``, which a comparison across two vehicles sets False) and
    ``screening_status``: BUG_SUSPECT when any applicable blocking check fails, else
    SCREENING_NOT_CHECKED without an attribution, else SCREENING_OK;
    ``screening_failed`` lists the failed blocking checks and
    ``screening_diagnostic_failed`` the failed diagnostic ones. The M2 record carries
    ``role`` = checks.m2_role: diagnostic (the default, the user's decision of
    2026-09-30) computes and records M2 exactly as blocking does, but its fail neither
    sets BUG_SUSPECT nor enters ``screening_failed``; every other check is blocking."""
    out: dict[str, Any] = {"status": result.status, "baseline_status": baseline.status}
    for key, value in result.metrics.items():
        base = baseline.metrics.get(key)
        if _is_numeric_or_missing(value) and _is_numeric_or_missing(base):
            out[f"delta_{key}"] = _delta(value, base)
    m, b = result.metrics, baseline.metrics
    d_payload = _delta(m.get("payload_kg"), b.get("payload_kg"))
    out["payload_delta_kg"] = d_payload
    v0 = m.get("speed_at_release_mps")
    v0_ok = _is_finite_number(v0) and float(v0) >= 0.0
    out["ideal_screening_payload_at_release_speed_kg"] = (
        payload_gain_kg(vehicle, float(v0)) if v0_ok else None
    )
    p_base = b.get("payload_kg")
    at_base = None
    if v0_ok and _is_finite_number(p_base) and float(p_base) > 0.0:
        at_base = payload_gain_kg(with_payload(vehicle, float(p_base)), float(v0))
    out["ideal_screening_payload_at_release_speed_at_pbase_kg"] = at_base
    yardsticks = [
        (value, basis)
        for value, basis in (
            (out["ideal_screening_payload_at_release_speed_kg"], SCREENING_BASIS_P0),
            (at_base, SCREENING_BASIS_PBASE),
        )
        if value is not None
    ]
    strict = min(yardsticks, key=lambda item: item[0]) if yardsticks else None
    out["screening_yardstick_kg"] = None if strict is None else strict[0]
    out["screening_yardstick_basis"] = None if strict is None else strict[1]
    beyond = None if d_payload is None or strict is None else d_payload - strict[0]
    out["payload_beyond_screening_kg"] = beyond
    out["beats_screening"] = None if beyond is None else beyond > 0.0
    for key, flag in (
        ("max_q_pa", "max_q_above_baseline"),
        ("peak_q_alpha", "q_alpha_above_baseline"),
    ):
        d = _delta(m.get(key), b.get(key))
        out[flag] = None if d is None else d > 0.0
    v_kick = m.get("speed_at_kick_mps")
    out["unconstrained_kick"] = (
        float(v_kick) > checks.unconstrained_kick_mps if _is_finite_number(v_kick) else None
    )
    bound_flags = [
        out[k] for k in ("max_q_above_baseline", "q_alpha_above_baseline", "unconstrained_kick")
    ]
    out["payload_delta_upper_bound"] = (
        True
        if any(f is True for f in bound_flags)
        else (False if any(f is not None for f in bound_flags) else None)
    )
    attribution = None
    if matched is not None and matched_baseline is not None:
        attribution = matched_attribution(matched, matched_baseline, d_payload)
    out.update(dict.fromkeys(ATTRIBUTION_KEYS) if attribution is None else attribution)
    records = {
        "closure": _closure_check(result, baseline, checks),
        "attribution": _attribution_check(
            attribution, out["beats_screening"], attribution_required, checks
        ),
        **_m2_m3(result, baseline, attribution, checks),
        "m4": _m4(attribution, checks),
        "m5": _m5(name, result, d_payload, anchor, checks),
    }
    records["m2"] = {**records["m2"], ROLE_KEY: checks.m2_role}
    for key, rec in records.items():
        out[f"checks_{key}"] = rec
    fails = [key for key, rec in records.items() if rec["status"] == CHECK_FAIL]
    failed = [key for key in fails if not is_diagnostic(records[key])]
    out["screening_failed"] = failed
    out["screening_diagnostic_failed"] = [key for key in fails if key not in failed]
    if failed:
        out["screening_status"] = BUG_SUSPECT
    elif attribution is None:
        out["screening_status"] = SCREENING_NOT_CHECKED
    else:
        out["screening_status"] = SCREENING_OK
    return out


def reference_payload_kg(rr: RunResult) -> float:
    """The matched payload P_ref [kg] a planar baseline sets: its P* when its payload
    search found one, else its vehicle payload P0 (fixed guidance, residual)."""
    p_star = rr.result.metrics.get("payload_kg")
    if _is_finite_number(p_star):
        return float(p_star)
    return rr.resolved.to_vehicle().payload_mass_kg


def anchor_from(runs: Mapping[str, Result], baseline: Result, vehicle: Vehicle) -> Anchor | None:
    """The M5 anchor of an experiment's runs (``Anchor``), or None unless both
    INSTANT_VARIANT_NAME and PAD_INSTANT_NAME ran with a P*, and the baseline has its
    pre-flight term and a P* (the pad pre-flight term in kg is ``payload_equiv_kg`` of
    that delta-v on the vehicle at the baseline's P*)."""
    silo, pad = runs.get(INSTANT_VARIANT_NAME), runs.get(PAD_INSTANT_NAME)
    if silo is None or pad is None:
        return None
    d_payload = _delta(silo.metrics.get("payload_kg"), pad.metrics.get("payload_kg"))
    pre = baseline.metrics.get("preflight_dv_mps")
    p_base = baseline.metrics.get("payload_kg")
    v0 = silo.metrics.get("speed_at_release_mps")
    if d_payload is None or not all(_is_finite_number(x) for x in (pre, p_base, v0)):
        return None
    pre_kg = payload_equiv_kg(with_payload(vehicle, float(p_base)), float(pre))
    if pre_kg is None:
        return None
    return Anchor(d_payload, pre_kg, float(v0))


# ----------------------------------------------------------------- planar sensitivity

TRAJECTORY_FREE_RUN_KEYS: tuple[tuple[str, ...], ...] = (("name",),)
"""Run-dict paths that do not change a planar trajectory for any assist model (the
run's name)."""
ENERGY_ONLY_ASSIST_KEYS: dict[str, tuple[str, ...]] = {"constant_accel": ("drive_efficiency",)}
"""Per assist model, the ``assist`` keys that enter only the energy bookkeeping, not the
trajectory: constant_accel prescribes the net acceleration, so its drive efficiency
enters only electrical_energy = work / efficiency. A model not listed has none (a
linear motor with an electrical power limit would fly differently with another
efficiency), so every key of it changes the trajectory key."""
TRAJECTORY_FREE_VEHICLE_KEYS: tuple[tuple[str, ...], ...] = (("screening",),)
"""Vehicle-dict paths that do not change a planar trajectory (the screening Isp, the
ideal yardstick only)."""


def _without(tree: Mapping[str, Any], paths: Sequence[tuple[str, ...]]) -> dict[str, Any]:
    """A deep copy of a config dict with the given key paths removed (absent ones
    ignored)."""
    out = copy.deepcopy(dict(tree))
    for path in paths:
        node: Any = out
        for key in path[:-1]:
            node = node.get(key) if isinstance(node, dict) else None
        if isinstance(node, dict):
            node.pop(path[-1], None)
    return out


def trajectory_key(run: ResolvedRun) -> str:
    """sha256 hex of the trajectory-relevant configuration of a resolved run: its run
    dict and vehicle dict in canonical JSON without TRAJECTORY_FREE_RUN_KEYS, the
    ENERGY_ONLY_ASSIST_KEYS of its assist model and TRAJECTORY_FREE_VEHICLE_KEYS. Two
    runs with one key fly the same trajectory and the same search, so an energy-only or
    yardstick sensitivity case can reuse the nominal run's trajectory and recompute only
    its metrics (plan section 3)."""
    assist = run.run_dict.get("assist")
    model = assist.get("model") if isinstance(assist, Mapping) else None
    energy_only = tuple(("assist", k) for k in ENERGY_ONLY_ASSIST_KEYS.get(str(model), ()))
    payload = {
        "run": _without(run.run_dict, (*TRAJECTORY_FREE_RUN_KEYS, *energy_only)),
        "vehicle": _without(run.vehicle_dict, TRAJECTORY_FREE_VEHICLE_KEYS),
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _run_planar_sensitivity(
    resolved: ResolvedExperiment,
    baseline: RunResult,
    run_names: Container[str] | None,
    nominal: Mapping[str, RunResult],
) -> list[SensitivityRow]:
    """The planar sensitivity cases (docs/physics.md, "Sensitivity paths"): every
    trajectory-changing case is a full searched run, compared with the unchanged
    baseline and, for a ``vehicle.`` parameter, with the baseline re-run under the same
    perturbation (once per distinct perturbation); a case whose ``trajectory_key``
    equals a run already flown (the nominal runs, then every case and perturbed
    baseline as they run: an energy-only ``assist.drive_efficiency`` or a
    ``vehicle.screening`` case) reuses that run's trajectory and search and recomputes
    only its metrics (``sim.rerun_resolved``), memoised within this call only.

    The screening-beat rule applies to every assist-versus-pad pair of one vehicle: a run
    parameter's case against the unchanged baseline, and a vehicle parameter's case
    against the same-perturbation baseline, get the matched-payload attribution
    (``attributed_comparison``: rung-2 runs at that baseline's P*, memoised by
    trajectory key). A vehicle parameter's case against the unchanged baseline compares
    two vehicles and is not attributed (not_checked)."""
    from launchsim import sim  # late: sim imports this module

    checks = resolved.baseline.run.planar.checks  # type: ignore[union-attr]
    memo: dict[str, RunResult] = {trajectory_key(rr.resolved): rr for rr in nominal.values()}
    matched_memo: dict[tuple[str, float, bool], MatchedRun | None] = {}

    def run_or_reuse(run: ResolvedRun) -> RunResult:
        key = trajectory_key(run)
        hit = memo.get(key)
        if hit is not None:
            return sim.rerun_resolved(run, hit)
        rr = sim.run_resolved(run)
        memo[key] = rr
        return rr

    rows: list[SensitivityRow] = []
    for case in resolved.sensitivity:
        if run_names is not None and case.of not in run_names:
            continue
        rr = run_or_reuse(case.run)
        vehicle = case.run.to_vehicle()
        is_vehicle = case.param.startswith(VEHICLE_PREFIX)
        if is_vehicle:
            comparison = compare_planar(
                rr.result,
                baseline.result,
                vehicle,
                checks=checks,
                name=case.of,
                attribution_required=False,
            )
        else:
            comparison = attributed_comparison(rr, baseline, checks, case.of, matched_memo)
        base_pert: RunResult | None = None
        if is_vehicle:
            if case.of == baseline.name:
                base_pert = rr
            else:
                base_pert = run_or_reuse(
                    resolve_run(baseline.name, resolved.baseline.run_dict, case.run.vehicle_dict)
                )
        comparison_pert = (
            comparison
            if base_pert is None
            else attributed_comparison(rr, base_pert, checks, case.of, matched_memo)
        )
        value_yaml = perturbed_value(case.run, case.param)
        value_si, unit = si_value(case.param, value_yaml)
        rows.append(
            SensitivityRow(
                of=case.of,
                param=case.param,
                fraction=case.fraction,
                value_yaml_units=value_yaml,
                value_si=value_si,
                value_si_unit=unit,
                result=rr,
                comparison=comparison,
                baseline_perturbed=base_pert,
                comparison_perturbed=comparison_pert,
            )
        )
    return rows


def attributed_comparison(
    rr: RunResult,
    base: RunResult,
    checks: ChecksConfig,
    name: str,
    memo: dict[tuple[str, float, bool], MatchedRun | None] | None = None,
) -> dict[str, Any]:
    """``compare_planar`` of rr against base with the matched-payload attribution
    required: the rung-2 runs at base's P_ref (``reference_payload_kg``) executed through
    ``sim.matched_run`` (amendment 16), the variant with its gamma* neighbours, memoised
    in memo by (trajectory key, P_ref, neighbours) when given. A run with base's own
    trajectory key (the baseline itself, or an energy-only case of it) gets no matched
    run: it flies base's trajectory, dP* = 0, nothing to attribute. No M5 anchor."""
    from launchsim import sim  # late: sim imports this module

    p_ref = reference_payload_kg(base)

    def matched(run: RunResult, neighbours: bool) -> MatchedRun | None:
        key = (trajectory_key(run.resolved), p_ref, neighbours)
        if memo is not None and key in memo:
            return memo[key]
        out = sim.matched_run(run.resolved, run.result, p_ref, neighbours=neighbours)
        if memo is not None:
            memo[key] = out
        return out

    same = trajectory_key(rr.resolved) == trajectory_key(base.resolved)
    mb = None if same else matched(base, False)
    mv = None if mb is None else matched(rr, True)
    return compare_planar(
        rr.result,
        base.result,
        rr.resolved.to_vehicle(),
        checks=checks,
        name=name,
        matched=mv,
        matched_baseline=mb,
    )


def planar_sensitivity_record(row: SensitivityRow) -> dict[str, Any]:
    """The metrics.json record of one planar sensitivity case: the case, its perturbed
    value in SI and in the YAML units, the P* [kg] and dP* against the unchanged
    baseline and against the same-perturbation baseline, whether the trajectory was
    reused (``trajectory_reused``: an energy-only or yardstick case), the full metrics
    record and both comparisons."""
    m = row.result.result.metrics
    return {
        "of": row.of,
        "param": row.param,
        "fraction": row.fraction,
        "value_si": row.value_si,
        "value_si_unit": row.value_si_unit,
        "value_yaml_units": row.value_yaml_units,
        "run": row.result.name,
        "status": row.result.result.status,
        "flags": row.result.result.flags,
        "trajectory_reused": bool(m.get("trajectory_reused")),
        "payload_kg": m.get("payload_kg"),
        "payload_delta_kg": row.comparison.get("payload_delta_kg"),
        "payload_delta_vs_perturbed_baseline_kg": row.comparison_perturbed.get("payload_delta_kg"),
        "baseline_perturbed": row.baseline_perturbed is not None,
        "baseline_perturbed_payload_kg": (
            None
            if row.baseline_perturbed is None
            else row.baseline_perturbed.result.metrics.get("payload_kg")
        ),
        "metrics": metrics_record(row.result.result),
        "comparison": row.comparison,
        "comparison_vs_perturbed_baseline": row.comparison_perturbed,
    }
