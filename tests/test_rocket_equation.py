"""Rocket equation in vacuum without gravity: delta-v = c ln(m0/mf).

Each case is one BURN phase driven directly through the phase engine with
ConstantGravity(0). Expected values are the closed forms written here from the fixture
masses and constants; nothing is taken from the package's own formulas. Required
accuracy 1e-6 relative (CLAUDE.md); asserted at 1e-9.
"""

from __future__ import annotations

import math

import numpy as np

from launchsim.constants import G0_MPS2
from launchsim.dynamics import (
    VERTICAL_LAYOUT,
    VERTICAL_STATE_NAMES,
    ConstantGravity,
    VerticalParams,
    rhs_vertical,
)
from launchsim.phases import (
    IntegratorSettings,
    PhaseResult,
    PhaseSpec,
    atol_for,
    ev_propellant,
    integrate_phase,
)
from launchsim.vehicle import Stage, Startup, ThrustSchedule, Vehicle

REL = 1e-9

# Generic F9-class stage 1 as the README states it (the fixture is checked against these).
F9_M0_KG = 542_570.0
F9_MF_KG = 146_870.0
F9_ISP_S = 311.0


def _burn(
    schedule: ThrustSchedule, m0_kg: float, m_dry_kg: float, settings: IntegratorSettings
) -> PhaseResult:
    """One vacuum, zero-gravity burn from rest at z = 0 until the propellant event."""
    params = VerticalParams(
        gravity=ConstantGravity(0.0), g_ref_mps2=0.0, schedule=schedule, v_sign=1
    )
    spec = PhaseSpec(
        kind="BURN",
        stage_index=0,
        t0=0.0,
        t_end=None,
        rhs=rhs_vertical,
        params=params,
        events=(ev_propellant(m_dry_kg),),
        atol=atol_for(VERTICAL_STATE_NAMES),
    )
    y0 = VERTICAL_LAYOUT.build(m_kg=m0_kg)
    return integrate_phase(spec, y0, settings)


def _get(y: np.ndarray, name: str) -> float:
    return float(VERTICAL_LAYOUT.get(y, name))


def test_toy_step_thrust_matches_rocket_equation(
    toy_stage: Stage, tight_settings: IntegratorSettings
) -> None:
    m0 = toy_stage.dry_mass_kg + toy_stage.propellant_mass_kg
    mf = toy_stage.dry_mass_kg
    c = G0_MPS2 * toy_stage.engine.isp_vac_s
    mdot = toy_stage.n_engines * toy_stage.engine.thrust_vac_N / c
    v_expected = c * math.log(m0 / mf)  # = 3000 ln 5
    t_b_expected = toy_stage.propellant_mass_kg / mdot  # = 160 s
    assert math.isclose(c, 3000.0, rel_tol=1e-12)
    assert math.isclose(t_b_expected, 160.0, rel_tol=1e-12)

    res = _burn(toy_stage.schedule(0.0), m0, mf, tight_settings)

    assert res.ended_by == "propellant"
    assert math.isclose(res.t_end, t_b_expected, rel_tol=REL)
    assert math.isclose(_get(res.y_end, "v_mps"), v_expected, rel_tol=REL)
    assert math.isclose(_get(res.y_end, "J_vac_mps"), v_expected, rel_tol=REL)
    assert math.isclose(_get(res.y_end, "m_kg"), mf, rel_tol=REL)
    for name in ("J_grav_mps", "J_alt_mps", "J_bp_mps", "J_steer_mps"):
        assert _get(res.y_end, name) == 0.0


def test_toy_ramp_gives_the_same_delta_v(
    toy_stage: Stage, tight_settings: IntegratorSettings
) -> None:
    """A 2 s linear ramp burns the same propellant, so delta-v is identical; the burn
    lasts t_ramp/2 longer (the ramp burns mdot t_ramp/2)."""
    t_ramp = 2.0
    m0 = toy_stage.dry_mass_kg + toy_stage.propellant_mass_kg
    mf = toy_stage.dry_mass_kg
    c = G0_MPS2 * toy_stage.engine.isp_vac_s
    mdot = toy_stage.engine.thrust_vac_N / c
    v_expected = c * math.log(m0 / mf)
    t_b_expected = toy_stage.propellant_mass_kg / mdot + 0.5 * t_ramp

    schedule = toy_stage.schedule(0.0, startup=Startup("ramp", t_ramp_s=t_ramp))
    res = _burn(schedule, m0, mf, tight_settings)

    assert res.ended_by == "propellant"
    assert math.isclose(res.t_end, t_b_expected, rel_tol=REL)
    assert math.isclose(_get(res.y_end, "v_mps"), v_expected, rel_tol=REL)
    assert math.isclose(_get(res.y_end, "J_vac_mps"), v_expected, rel_tol=REL)


def test_f9_stage1_matches_rocket_equation(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    stage = f9_vehicle.stages[0]
    c = G0_MPS2 * F9_ISP_S
    v_expected = c * math.log(F9_M0_KG / F9_MF_KG)
    # The fixture must be the README vehicle these literals describe.
    assert math.isclose(f9_vehicle.liftoff_mass_kg(), F9_M0_KG, rel_tol=1e-12)
    assert math.isclose(F9_M0_KG - stage.propellant_mass_kg, F9_MF_KG, rel_tol=1e-12)
    assert stage.engine.isp_vac_s == F9_ISP_S

    res = _burn(stage.schedule(0.0, startup=Startup("step")), F9_M0_KG, F9_MF_KG, tight_settings)

    assert res.ended_by == "propellant"
    assert math.isclose(_get(res.y_end, "v_mps"), v_expected, rel_tol=REL)
    assert math.isclose(_get(res.y_end, "J_vac_mps"), v_expected, rel_tol=REL)
    assert math.isclose(_get(res.y_end, "m_kg"), F9_MF_KG, rel_tol=REL)
