"""Planar Kepler motion and coasts (docs/physics.md, "Planar ascent state and equations
of motion", "Orbital elements and the circular target").

CLAUDE.md requires an elliptical orbit (e ~ 0.3) for 10 revolutions with specific energy
and angular momentum drift below 1e-8 relative and the period 2 pi sqrt(a^3/mu): a
circular orbit is an equilibrium of the polar equations and would pass with a wrong
dv_theta/dt term. Also the vacuum-coast apex (constant g and mu/r^2) and the orbital
elements of orbit.py. Every expected value is a closed form written here.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from launchsim.constants import MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M
from launchsim.dynamics import (
    PLANAR_LAYOUT,
    ConstantGravity,
    InverseSquareGravity,
    PlanarDynamics2D,
    PlanarParams,
    planar_rotation_rate,
    vacuum_atmosphere,
)
from launchsim.orbit import TargetOrbit, orbit_elements
from launchsim.phases import (
    EventSpec,
    IntegratorSettings,
    PhaseSpec,
    atol_for,
    integrate_phase,
)

G_TEST = 9.81
"""Constant gravity [m/s^2] of the analytic coast test (never g0)."""
ECC = 0.3
PERIAPSIS_ALT_M = 500e3
N_REV = 10
LAT_RAD = math.radians(28.5)
AZ_RAD = math.radians(90.0)

LAY = PLANAR_LAYOUT


def _coast_params(gravity, omega_p: float = 0.0) -> PlanarParams:
    """An unpowered, drag-free planar phase in vacuum."""
    g_ref = gravity(R_EARTH_M) - omega_p * omega_p * R_EARTH_M
    return PlanarParams(gravity, omega_p, g_ref, None, None, vacuum_atmosphere, None)


def _energy(r, v_r, v_theta, mu: float):
    return 0.5 * (v_r * v_r + v_theta * v_theta) - mu / r


def _ev_vr(direction: int, terminal: bool) -> EventSpec:
    i = LAY.index("v_r_mps")
    return EventSpec("v_r_zero", lambda t, y: y[i], terminal, direction)


def _coast(params, y0, t_end, events, settings):
    model = PlanarDynamics2D.for_params(params)
    model.check_params(params)
    spec = PhaseSpec(
        kind="COAST",
        stage_index=0,
        t0=0.0,
        t_end=t_end,
        rhs=model.rhs,
        params=params,
        events=events,
        atol=atol_for(model.state_names),
    )
    return integrate_phase(spec, y0, settings)


@pytest.mark.parametrize(
    ("method", "period_rel_tol"), [("DOP853", 1e-9), ("RK45", 1e-8)], ids=["DOP853", "RK45"]
)
def test_elliptical_orbit_ten_revolutions(method: str, period_rel_tol: float) -> None:
    """e = 0.3 from apoapsis, r_p = R_E + 500 km: a = r_p/(1 - e), r_a = a(1 + e),
    v_theta(apo) = sqrt(mu (1 - e)/r_a). E = -mu/(2a) and h = sqrt(mu a (1 - e^2)) stay
    constant (drift < 1e-8 at every step); P = 2 pi sqrt(a^3/mu) from the periapsis
    events (v_r crossing zero upward); theta advances 2 pi per period. Rotation is on:
    it must not touch inertial motion in vacuum."""
    mu = MU_EARTH_M3S2
    r_p = R_EARTH_M + PERIAPSIS_ALT_M
    a = r_p / (1.0 - ECC)
    r_a = a * (1.0 + ECC)
    assert r_a == pytest.approx(12_773_683.0, abs=1.0)
    v_apo = math.sqrt(mu * (1.0 - ECC) / r_a)
    period = 2.0 * math.pi * math.sqrt(a**3 / mu)
    assert period == pytest.approx(9_693.2665, abs=1e-3)
    e_exp = -mu / (2.0 * a)
    h_exp = math.sqrt(mu * a * (1.0 - ECC * ECC))

    omega_p = planar_rotation_rate(LAT_RAD, AZ_RAD)
    params = _coast_params(InverseSquareGravity(mu), omega_p)
    y0 = LAY.build(r_m=r_a, v_theta_mps=v_apo, m_kg=1000.0)
    res = _coast(
        params,
        y0,
        N_REV * period,
        (_ev_vr(+1, terminal=False),),
        IntegratorSettings(method=method, rtol=1e-10),
    )
    assert res.ended_by == "t_end"
    r = LAY.get(res.y, "r_m")
    v_r = LAY.get(res.y, "v_r_mps")
    v_t = LAY.get(res.y, "v_theta_mps")
    drift_e = np.max(np.abs(_energy(r, v_r, v_t, mu) - e_exp)) / abs(e_exp)
    drift_h = np.max(np.abs(r * v_t - h_exp)) / h_exp
    assert drift_e < 1e-8
    assert drift_h < 1e-8

    peri = np.array([t for name, t in res.event_times if name == "v_r_zero"])
    assert len(peri) == N_REV
    expected = (np.arange(N_REV) + 0.5) * period
    assert np.max(np.abs(peri - expected)) < period_rel_tol * period * N_REV
    measured_period = (peri[-1] - peri[0]) / (N_REV - 1)
    assert measured_period == pytest.approx(period, rel=period_rel_tol)
    for te in peri:
        y_e = res.dense(te)
        assert LAY.get(y_e, "r_m") == pytest.approx(r_p, rel=1e-8)

    theta_end = LAY.get(res.y_end, "theta_rad")
    assert theta_end == pytest.approx(2.0 * math.pi * N_REV, abs=1e-7)


def test_orbit_elements_of_the_ellipse() -> None:
    """orbit_elements at apoapsis, at periapsis and at a quarter-period point recovers
    a, e, r_p, r_a, E and h of the e = 0.3 ellipse; the eccentricity equals
    sqrt(1 + 2 E h^2/mu^2) (the form in the plan) away from circular."""
    mu = MU_EARTH_M3S2
    r_p = R_EARTH_M + PERIAPSIS_ALT_M
    a = r_p / (1.0 - ECC)
    r_a = a * (1.0 + ECC)
    h = math.sqrt(mu * a * (1.0 - ECC * ECC))
    # A general point: true anomaly nu, r = p/(1 + e cos nu), v_r = (mu/h) e sin nu,
    # v_theta = h / r.
    p_semi = h * h / mu
    for nu in (0.0, math.pi, 1.1, -2.3):
        r = p_semi / (1.0 + ECC * math.cos(nu))
        el = orbit_elements(r, mu / h * ECC * math.sin(nu), h / r, mu)
        assert el.a_m == pytest.approx(a, rel=1e-12)
        assert el.e == pytest.approx(ECC, rel=1e-12)
        assert el.r_p_m == pytest.approx(r_p, rel=1e-12)
        assert el.r_a_m == pytest.approx(r_a, rel=1e-12)
        assert el.energy_Jkg == pytest.approx(-mu / (2.0 * a), rel=1e-12)
        assert el.h_m2s == pytest.approx(h, rel=1e-12)
        e_sqrt = math.sqrt(1.0 + 2.0 * el.energy_Jkg * el.h_m2s**2 / mu**2)
        assert el.e == pytest.approx(e_sqrt, rel=1e-10)


def test_circular_target_and_near_circular_eccentricity() -> None:
    """The 200 km target: r_t = R_E + 200 km, E* = -mu/(2 r_t) = -30,297,365.5 J/kg,
    v_c = sqrt(mu/r_t) = 7,784.2617 m/s. A circular state has e = 0 to rounding, and a
    state with v_r = 1e-3 m/s at r_t has e = v_r/v_c (to first order), which the
    hypot form resolves where sqrt(1 + 2 E h^2/mu^2) cancels."""
    mu = MU_EARTH_M3S2
    r_t = R_EARTH_M + 200e3
    target = TargetOrbit(r_t)
    assert target.energy_Jkg(mu) == pytest.approx(-mu / (2.0 * r_t), rel=1e-15)
    assert target.energy_Jkg(mu) == pytest.approx(-30_297_365.5, abs=0.05)
    v_c = math.sqrt(mu / r_t)
    assert target.v_circ_mps(mu) == pytest.approx(v_c, rel=1e-15)
    assert target.v_circ_mps(mu) == pytest.approx(7_784.2617, abs=5e-5)

    circ = orbit_elements(r_t, 0.0, v_c, mu)
    assert circ.e < 1e-15
    assert circ.r_p_m == pytest.approx(r_t, rel=1e-14)
    assert circ.r_a_m == pytest.approx(r_t, rel=1e-14)

    v_r = 1e-3
    near = orbit_elements(r_t, v_r, v_c, mu)
    assert near.e == pytest.approx(v_r / v_c, rel=1e-6)
    assert near.e < 1e-6


def test_open_and_radial_conics() -> None:
    """Above escape speed the orbit is a hyperbola (e > 1, a < 0, r_a = inf, r_p =
    h^2/(mu (1 + e)) > 0); a purely radial state is the degenerate conic e = 1, r_p = 0,
    r_a = inf; bad inputs raise."""
    mu = MU_EARTH_M3S2
    r = R_EARTH_M
    v_esc = math.sqrt(2.0 * mu / r)
    hyp = orbit_elements(r, 0.0, 1.2 * v_esc, mu)
    assert hyp.e > 1.0
    assert hyp.a_m < 0.0
    assert hyp.r_a_m == math.inf
    assert hyp.r_p_m == pytest.approx(r, rel=1e-12)
    radial = orbit_elements(r, 3000.0, 0.0, mu)
    assert radial.e == 1.0
    assert radial.r_p_m == 0.0
    assert radial.r_a_m == math.inf
    with pytest.raises(ValueError):
        orbit_elements(0.0, 0.0, 1.0, mu)
    with pytest.raises(ValueError):
        orbit_elements(r, 0.0, 1.0, 0.0)
    with pytest.raises(ValueError):
        TargetOrbit(-1.0)


@pytest.mark.parametrize("v0", [300.0, 3000.0])
def test_radial_coast_constant_g_apex(v0: float) -> None:
    """ConstantGravity(g_test), no rotation, v_theta = 0 (so no centrifugal term):
    apex altitude v0^2/(2 g) at t = v0/g."""
    params = _coast_params(ConstantGravity(G_TEST))
    y0 = LAY.build(r_m=R_EARTH_M, v_r_mps=v0, m_kg=1000.0)
    res = _coast(params, y0, None, (_ev_vr(-1, terminal=True),), IntegratorSettings(rtol=1e-10))
    assert res.ended_by == "v_r_zero"
    alt = LAY.get(res.y_end, "r_m") - R_EARTH_M
    assert alt == pytest.approx(v0 * v0 / (2.0 * G_TEST), rel=1e-9)
    assert res.t_end == pytest.approx(v0 / G_TEST, rel=1e-9)
    assert LAY.get(res.y_end, "theta_rad") == 0.0
    assert LAY.get(res.y_end, "v_theta_mps") == 0.0


@pytest.mark.parametrize("v0", [300.0, 3000.0])
def test_radial_coast_inverse_square_apex(v0: float) -> None:
    """mu/r^2, radial from R_E: 1/r_max = 1/R_E - v0^2/(2 mu); the specific energy
    v^2/2 - mu/r is conserved at every step (1e-10 relative)."""
    mu = MU_EARTH_M3S2
    params = _coast_params(InverseSquareGravity(mu))
    y0 = LAY.build(r_m=R_EARTH_M, v_r_mps=v0, m_kg=1000.0)
    res = _coast(params, y0, None, (_ev_vr(-1, terminal=True),), IntegratorSettings(rtol=1e-10))
    r_max = 1.0 / (1.0 / R_EARTH_M - v0 * v0 / (2.0 * mu))
    alt = LAY.get(res.y_end, "r_m") - R_EARTH_M
    assert alt == pytest.approx(r_max - R_EARTH_M, rel=1e-9)
    e0 = 0.5 * v0 * v0 - mu / R_EARTH_M
    energy = _energy(
        LAY.get(res.y, "r_m"), LAY.get(res.y, "v_r_mps"), LAY.get(res.y, "v_theta_mps"), mu
    )
    assert np.max(np.abs(energy - e0)) < 1e-10 * abs(e0)


def test_non_radial_coast_conserves_energy_and_angular_momentum() -> None:
    """A suborbital coast launched 40 deg above horizontal at 5 km/s under mu/r^2, with
    rotation on (it must not act on inertial motion): E and h = r v_theta constant at
    every step to 1e-10 relative through apex and down to the start radius."""
    mu = MU_EARTH_M3S2
    omega_p = OMEGA_EARTH_RADS
    params = _coast_params(InverseSquareGravity(mu), omega_p)
    speed = 5000.0
    gamma = math.radians(40.0)
    y0 = LAY.build(
        r_m=R_EARTH_M,
        v_r_mps=speed * math.sin(gamma),
        v_theta_mps=speed * math.cos(gamma),
        m_kg=1000.0,
    )
    i_r = LAY.index("r_m")
    ground = EventSpec("ground", lambda t, y: y[i_r] - R_EARTH_M, True, -1, zero_tol=1e-6)
    res = _coast(params, y0, None, (ground,), IntegratorSettings(rtol=1e-10))
    assert res.ended_by == "ground"
    r = LAY.get(res.y, "r_m")
    v_r = LAY.get(res.y, "v_r_mps")
    v_t = LAY.get(res.y, "v_theta_mps")
    e0 = 0.5 * speed * speed - mu / R_EARTH_M
    h0 = R_EARTH_M * speed * math.cos(gamma)
    assert np.max(np.abs(_energy(r, v_r, v_t, mu) - e0)) < 1e-10 * abs(e0)
    assert np.max(np.abs(r * v_t - h0)) < 1e-10 * h0
    # Symmetric return: the speed at the start radius equals the launch speed.
    assert math.hypot(LAY.get(res.y_end, "v_r_mps"), LAY.get(res.y_end, "v_theta_mps")) == (
        pytest.approx(speed, rel=1e-9)
    )
