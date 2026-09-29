"""Vertical burn under constant gravity, no drag, step thrust at t = 0, several v0.

Closed forms (derived here). With constant g, m(t) = m0 - mdot t and c = g0 Isp:

    dv/dt = c mdot / (m0 - mdot t) - g
    v(t)  = v0 - g t + c ln(m0 / (m0 - mdot t))
    v_f   = v0 + c ln(m0/mf) - g t_b                          t_b = (m0 - mf) / mdot

Integrating v once more, with u = m0 - mdot t (du = -mdot dt) and
integral of ln(m0/u) du = u ln(m0/u) + u:

    integral_0^{t_b} c ln(m0/(m0 - mdot t)) dt
        = (c/mdot) [u ln(m0/u) + u]_{u=mf}^{u=m0}
        = (c/mdot) [m0 - mf ln(m0/mf) - mf]
        = c [t_b - (mf/mdot) ln(m0/mf)]
    z_f = z0 + v0 t_b - g t_b^2 / 2 + c [t_b - (mf/mdot) ln(m0/mf)]

The gravity quadrature is J_grav = integral g sigma dt = g t_b for a phase that stays
rising (sigma = +1), and J_alt = 0 because g_ref = g. ConstantGravity is an analytic
device: runs use mu/r^2.

Two further cases exercise the branches of the RHS that a rising, vacuum burn never
touches: a burn while falling (sigma = -1: J_steer = 2 T/m, J_grav runs backwards) and
a burn with p_amb > 0 (delivered thrust clamped at zero while the ramp is below
p_amb A_e, mass and J_vac still following the vacuum thrust, J_bp = J_vac). Both check
the per-phase loss identity |v_f| - |v_0| = J_vac - J_grav - J_steer - J_bp.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from launchsim.constants import G0_MPS2, P_SEA_LEVEL_PA
from launchsim.dynamics import (
    VERTICAL_LAYOUT,
    VERTICAL_STATE_NAMES,
    ConstantGravity,
    VerticalParams,
    rhs_vertical,
)
from launchsim.phases import (
    EventSpec,
    IntegratorSettings,
    PhaseResult,
    PhaseSpec,
    atol_for,
    ev_propellant,
    integrate_phase,
)
from launchsim.vehicle import Stage, Startup, ThrustSchedule

G = G0_MPS2
Z0 = 12.5
REL_V = 1e-9
REL_Z = 1e-8


def _get(y: np.ndarray, name: str) -> float:
    return float(VERTICAL_LAYOUT.get(y, name))


def _identity_residual_mps(res: PhaseResult, y0: np.ndarray) -> float:
    """|v_f| - |v_0| - (J_vac - J_grav - J_steer - J_bp) over one phase, from the
    quadrature states (drag is zero in Phase 1)."""
    dj = {name: _get(res.y_end, name) - _get(y0, name) for name in VERTICAL_STATE_NAMES}
    lhs = abs(_get(res.y_end, "v_mps")) - abs(_get(y0, "v_mps"))
    rhs = dj["J_vac_mps"] - dj["J_grav_mps"] - dj["J_steer_mps"] - dj["J_bp_mps"]
    return lhs - rhs


def _phase(
    params: VerticalParams,
    t0: float,
    t_end: float | None,
    events: tuple[EventSpec, ...] = (),
    sigma: int = 1,
) -> PhaseSpec:
    return PhaseSpec(
        kind="BURN",
        stage_index=0,
        t0=t0,
        t_end=t_end,
        rhs=rhs_vertical,
        params=params,
        events=events,
        atol=atol_for(VERTICAL_STATE_NAMES),
        sigma=sigma,
    )


@pytest.mark.parametrize("v0", [0.0, 30.0, 77.0, 300.0])
def test_vertical_burn_closed_form(
    v0: float, toy_stage: Stage, tight_settings: IntegratorSettings
) -> None:
    m0 = toy_stage.dry_mass_kg + toy_stage.propellant_mass_kg
    mf = toy_stage.dry_mass_kg
    c = G0_MPS2 * toy_stage.engine.isp_vac_s
    mdot = toy_stage.engine.thrust_vac_N / c
    t_b = (m0 - mf) / mdot
    v_f = v0 + c * math.log(m0 / mf) - G * t_b
    z_f = Z0 + v0 * t_b - 0.5 * G * t_b**2 + c * (t_b - (mf / mdot) * math.log(m0 / mf))
    assert toy_stage.engine.thrust_vac_N > m0 * G  # TWR > 1: the toy rises from rest

    params = VerticalParams(
        gravity=ConstantGravity(G), g_ref_mps2=G, schedule=toy_stage.schedule(0.0), v_sign=1
    )
    spec = PhaseSpec(
        kind="BURN",
        stage_index=0,
        t0=0.0,
        t_end=None,
        rhs=rhs_vertical,
        params=params,
        events=(ev_propellant(mf),),
        atol=atol_for(VERTICAL_STATE_NAMES),
    )
    y0 = VERTICAL_LAYOUT.build(z_m=Z0, v_mps=v0, m_kg=m0)
    res = integrate_phase(spec, y0, tight_settings)

    assert res.ended_by == "propellant"
    assert math.isclose(res.t_end, t_b, rel_tol=REL_V)
    assert math.isclose(float(VERTICAL_LAYOUT.get(res.y_end, "v_mps")), v_f, rel_tol=REL_V)
    assert math.isclose(float(VERTICAL_LAYOUT.get(res.y_end, "z_m")), z_f, rel_tol=REL_Z)
    assert math.isclose(float(VERTICAL_LAYOUT.get(res.y_end, "J_grav_mps")), G * t_b, rel_tol=REL_V)
    assert abs(float(VERTICAL_LAYOUT.get(res.y_end, "J_alt_mps"))) < 1e-9
    assert math.isclose(
        float(VERTICAL_LAYOUT.get(res.y_end, "J_vac_mps")), c * math.log(m0 / mf), rel_tol=REL_V
    )
    v_series = np.asarray(VERTICAL_LAYOUT.get(res.y, "v_mps"))
    assert v_series[0] == v0
    assert np.all(v_series[1:] > 0.0)


def test_burn_while_falling_counts_steering_and_regained_speed(
    toy_stage: Stage, tight_settings: IntegratorSettings
) -> None:
    """Toy stage, constant g, falling at v0 = -300 m/s, engine lit (step) at t = 40 s for
    10 s with sigma = -1 (v stays negative: the burn adds at most c ln(1000/950) = 154 m/s).
    Thrust points up, against the velocity (psi = pi), so for the phase

        v_f     = v0 + c ln(m0/mf) - g t         (dv/dt = T/m - g, signed)
        J_vac   = c ln(m0/mf)
        J_grav  = -g t                           (sigma = -1: speed is regained)
        J_steer = 2 c ln(m0/mf)                  ((T/m)(1 - sigma) = 2 T/m)

    and |v_f| - |v0| = J_vac - J_grav - J_steer - J_bp closes.
    """
    t0, t_burn = 40.0, 10.0
    v0 = -300.0
    m0 = toy_stage.dry_mass_kg + toy_stage.propellant_mass_kg
    c = G0_MPS2 * toy_stage.engine.isp_vac_s
    mdot = toy_stage.engine.thrust_vac_N / c
    mf = m0 - mdot * t_burn
    dv_vac = c * math.log(m0 / mf)
    v_f = v0 + dv_vac - G * t_burn
    assert v_f < 0.0

    params = VerticalParams(
        gravity=ConstantGravity(G), g_ref_mps2=G, schedule=toy_stage.schedule(t0), v_sign=-1
    )
    y0 = VERTICAL_LAYOUT.build(z_m=5000.0, v_mps=v0, m_kg=m0)
    res = integrate_phase(_phase(params, t0, t0 + t_burn, sigma=-1), y0, tight_settings)

    assert res.ended_by == "t_end"
    assert np.all(np.asarray(VERTICAL_LAYOUT.get(res.y, "v_mps")) < 0.0)
    assert math.isclose(_get(res.y_end, "v_mps"), v_f, rel_tol=REL_V)
    assert math.isclose(_get(res.y_end, "m_kg"), mf, rel_tol=REL_V)
    assert math.isclose(_get(res.y_end, "J_vac_mps"), dv_vac, rel_tol=REL_V)
    assert math.isclose(_get(res.y_end, "J_grav_mps"), -G * t_burn, rel_tol=REL_V)
    assert math.isclose(_get(res.y_end, "J_steer_mps"), 2.0 * dv_vac, rel_tol=REL_V)
    assert _get(res.y_end, "J_bp_mps") == 0.0
    assert abs(_identity_residual_mps(res, y0)) < 1e-9


def test_back_pressure_clamp_burns_mass_without_thrust(
    tight_settings: IntegratorSettings,
) -> None:
    """A 2 s ramp at sea level with an exit area chosen so p_amb A_e = T_full / 2: the
    delivered thrust T = max(0, T_vac - p_amb A_e) is zero for t < 1 s while the mass
    flow and J_vac follow the vacuum thrust. No gravity, so v stays exactly 0 while
    T = 0. With T_vac = T_full t / t_r and k = mdot / (2 t_r):

        m(t)    = m0 - k t^2                                (ramp burns mdot t^2 / (2 t_r))
        J_vac   = c ln(m0 / m(t))                           (dJ_vac = -c dm / m)
        J_bp    = J_vac                                     while T = 0
        dv/dt   = (T_vac - p_amb A_e) / m                   for 1 <= t <= 2, so
        v(2)    = c ln(m(1)/m(2)) - p_amb A_e I,  I = integral_1^2 dt / (m0 - k t^2)
                = c ln(m(1)/m(2)) - J_bp(1..2)
        I       = [ln((sqrt(m0) + sqrt(k) t) / (sqrt(m0) - sqrt(k) t))]_1^2 / (2 sqrt(m0 k))

    and the identity |v_f| - |v_0| = J_vac - J_grav - J_steer - J_bp closes over the
    powered window. The RHS clamp is also checked against ThrustSchedule.thrust_N.
    """
    t_full, c, m0, t_r = 15_000.0, 3000.0, 1000.0, 2.0
    p_amb = P_SEA_LEVEL_PA
    a_e = 0.5 * t_full / p_amb
    schedule = ThrustSchedule(t_full, c, a_e, 0.0, Startup("ramp", t_ramp_s=t_r))
    mdot = t_full / c
    k = mdot / (2.0 * t_r)

    def m_of(t: float) -> float:
        return m0 - k * t * t

    def i_of(t: float) -> float:
        return math.log((math.sqrt(m0) + math.sqrt(k) * t) / (math.sqrt(m0) - math.sqrt(k) * t))

    params = VerticalParams(
        gravity=ConstantGravity(0.0), g_ref_mps2=0.0, schedule=schedule, p_amb_pa=p_amb, v_sign=1
    )
    # The inlined clamp in rhs_vertical must agree with the schedule's own thrust_N.
    for t in (0.5, 1.0, 1.5, 2.5):
        y = VERTICAL_LAYOUT.build(m_kg=m_of(min(t, t_r)))
        dv = float(rhs_vertical(t, y, params)[VERTICAL_LAYOUT.index("v_mps")])
        assert math.isclose(dv * _get(y, "m_kg"), schedule.thrust_N(t, p_amb), rel_tol=1e-12)

    y0 = VERTICAL_LAYOUT.build(m_kg=m0)
    clamped = integrate_phase(_phase(params, 0.0, 1.0), y0, tight_settings)
    assert clamped.ended_by == "t_end"
    assert np.all(np.asarray(VERTICAL_LAYOUT.get(clamped.y, "v_mps")) == 0.0)
    assert math.isclose(_get(clamped.y_end, "m_kg"), m_of(1.0), rel_tol=REL_V)
    assert math.isclose(
        _get(clamped.y_end, "J_vac_mps"), c * math.log(m0 / m_of(1.0)), rel_tol=REL_V
    )
    assert math.isclose(
        _get(clamped.y_end, "J_bp_mps"), _get(clamped.y_end, "J_vac_mps"), rel_tol=1e-12
    )
    assert abs(_identity_residual_mps(clamped, y0)) < 1e-9

    y1 = clamped.y_end
    powered = integrate_phase(_phase(params, 1.0, 2.0), y1, tight_settings)
    j_bp_expected = p_amb * a_e * (i_of(2.0) - i_of(1.0)) / (2.0 * math.sqrt(m0 * k))
    v_expected = c * math.log(m_of(1.0) / m_of(2.0)) - j_bp_expected
    assert math.isclose(_get(powered.y_end, "m_kg"), m_of(2.0), rel_tol=REL_V)
    assert math.isclose(_get(powered.y_end, "v_mps"), v_expected, rel_tol=REL_V)
    assert math.isclose(
        _get(powered.y_end, "J_bp_mps") - _get(y1, "J_bp_mps"), j_bp_expected, rel_tol=REL_V
    )
    assert abs(_identity_residual_mps(powered, y1)) < 1e-9
