"""The gravity turn against the Culler-Fried closed form (docs/physics.md, "Stage-1
guidance and events (planar)", validation), including the gravity-loss quadrature.

Flat Earth, constant gravity g_test, no air, thrust along the velocity with the constant
acceleration a = n g_test (a ``const_accel_schedule``: c = 1e30 m/s, so the mass and
T/m are constant). With beta the velocity's angle from vertical and z = tan(beta/2):

    v = C z^n / sin beta,                C = v0 sin beta0 / z0^n
    t = (C/2g) [z^(n-1)/(n-1) + z^(n+1)/(n+1)]
    h = (C^2/4g) [z^(2n-2)/(2n-2) - z^(2n+2)/(2n+2)]
    x = (C^2/2g) [z^(2n-1)/(2n-1) + z^(2n+1)/(2n+1)]
    J_grav = int g cos beta dt = (C/2) [z^(n-1)/(n-1) - z^(n+1)/(n+1)]
    J_vac = n g t,  J_steer = 0

every one as the difference between z and z0, from dv/dt = g (n - cos beta) and
v dbeta/dt = g sin beta (derivation in docs/physics.md). The planar model flies it
with ``guidance.AlongVrel`` from v0 = 100 m/s at beta0 = 0.05 rad to beta = 1.2 rad,
where the kick-alignment event ``ev_kick_aligned(1.2)`` (sin(beta - 1.2) crossing zero
upward) stops it, on a datum of radius R = 1e12 m with mu = g_test R^2 (gravity changes
by 2h/R = 5e-8 relative and the local vertical by x/R = 2.3e-8 rad; the altitude is
resolved to ulp(R) = 1.2e-4 m). Measured errors 4e-8 to 1.7e-7 relative.
"""

from __future__ import annotations

import math
from collections.abc import Callable

import pytest

from launchsim.dynamics import PLANAR_LAYOUT, rhs_planar
from launchsim.guidance import AlongVrel
from launchsim.phases import IntegratorSettings, PhaseSpec, atol_for, integrate_phase
from launchsim.phases.engine import ev_kick_aligned

P2 = PLANAR_LAYOUT
G_TEST = 9.81
"""Constant gravity [m/s^2] of the analytic test (never g0)."""
N_TWR = 1.5
V0_MPS = 100.0
BETA0_RAD = 0.05
BETA1_RAD = 1.2
R_FLAT_M = 1e12
REL = 1e-6


def _culler_fried(beta: float) -> dict[str, float]:
    """The closed forms at beta [rad], as differences from beta0."""
    n, g = N_TWR, G_TEST
    z0 = math.tan(0.5 * BETA0_RAD)
    z = math.tan(0.5 * beta)
    c = V0_MPS * math.sin(BETA0_RAD) / z0**n

    def t_of(zz: float) -> float:
        return c / (2 * g) * (zz ** (n - 1) / (n - 1) + zz ** (n + 1) / (n + 1))

    def h_of(zz: float) -> float:
        return c * c / (4 * g) * (zz ** (2 * n - 2) / (2 * n - 2) - zz ** (2 * n + 2) / (2 * n + 2))

    def x_of(zz: float) -> float:
        return c * c / (2 * g) * (zz ** (2 * n - 1) / (2 * n - 1) + zz ** (2 * n + 1) / (2 * n + 1))

    def j_of(zz: float) -> float:
        return 0.5 * c * (zz ** (n - 1) / (n - 1) - zz ** (n + 1) / (n + 1))

    t = t_of(z) - t_of(z0)
    return {
        "v": c * z**n / math.sin(beta),
        "t": t,
        "h": h_of(z) - h_of(z0),
        "x": x_of(z) - x_of(z0),
        "J_grav": j_of(z) - j_of(z0),
        "J_vac": n * g * t,
    }


def test_culler_fried_gravity_turn(large_R_params, const_accel_schedule: Callable) -> None:
    """The along-v_rel burn from (v0, beta0) to beta = 1.2 rad matches the closed forms:
    the stop time, speed, altitude, downrange (R theta), J_grav and J_vac within 1e-6
    relative, J_steer exactly 0 (1e-12 abs), J_drag and J_bp 0, and the loss identity
    V_f - V_0 = J_vac - J_grav closes (the velocity at the stop is at beta = 1.2 within
    1e-9 rad)."""
    m0 = 1.0
    schedule = const_accel_schedule(N_TWR * G_TEST, m0)
    params = large_R_params(R_FLAT_M, G_TEST, schedule=schedule, steering=AlongVrel())
    y0 = P2.build(
        r_m=R_FLAT_M,
        v_r_mps=V0_MPS * math.cos(BETA0_RAD),
        v_theta_mps=V0_MPS * math.sin(BETA0_RAD),
        m_kg=m0,
    )
    spec = PhaseSpec(
        "GRAVITY_TURN",
        0,
        0.0,
        None,
        rhs_planar,
        params,
        (ev_kick_aligned(BETA1_RAD, 0.0),),
        atol_for(P2.names),
    )
    res = integrate_phase(spec, y0, IntegratorSettings(rtol=1e-10))
    assert res.ended_by == "kick_end"
    y = res.y_end
    cf = _culler_fried(BETA1_RAD)
    w, u = float(P2.get(y, "v_r_mps")), float(P2.get(y, "v_theta_mps"))
    assert math.atan2(u, w) == pytest.approx(BETA1_RAD, abs=1e-9)
    assert res.t_end == pytest.approx(cf["t"], rel=REL)
    assert math.hypot(w, u) == pytest.approx(cf["v"], rel=REL)
    assert float(P2.get(y, "r_m")) - R_FLAT_M == pytest.approx(cf["h"], rel=REL)
    assert R_FLAT_M * float(P2.get(y, "theta_rad")) == pytest.approx(cf["x"], rel=REL)
    assert float(P2.get(y, "J_grav_mps")) == pytest.approx(cf["J_grav"], rel=REL)
    assert float(P2.get(y, "J_vac_mps")) == pytest.approx(cf["J_vac"], rel=REL)
    assert abs(float(P2.get(y, "J_steer_mps"))) <= 1e-12
    assert float(P2.get(y, "J_drag_mps")) == 0.0 and float(P2.get(y, "J_bp_mps")) == 0.0
    closure = (
        math.hypot(w, u) - V0_MPS - (float(P2.get(y, "J_vac_mps")) - float(P2.get(y, "J_grav_mps")))
    )
    assert abs(closure) < 1e-9
    # The closed-form check is not vacuous: the turn spans a large range of each term.
    assert cf["h"] > 2e4 and cf["x"] > 1e4 and cf["J_grav"] > 300.0
