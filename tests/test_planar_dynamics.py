"""The planar right-hand side (docs/physics.md, "Planar ascent state and equations of
motion" and "2-D loss identity").

- The 2-D rocket equation (mu = 0, no rotation, thrust along v, non-radial start):
  V_f - V_0 = c ln(m0/m_f), and the motion is a straight line in inertial space.
- Every component of rhs_planar against the equations of motion written here.
- The pointwise identity dV/dt = dJ_vac - dJ_grav - dJ_drag - dJ_steer - dJ_bp, with
  dV/dt = (w w' + u u')/V from the kinematic rows of the same RHS and against
  -g_eff w/V + (T cos psi - D)/m written here, on 1,000 seeded states with rotation,
  drag, the back-pressure clamp, every steering law form and the V < 1e-9 fallback.
- The atmosphere is evaluated at h = r - r_datum (a flat-Earth datum R = 1e7 m), and
  the planar fixture factories of conftest.py do what their docstrings say.
- PlanarParams validation, PlanarDynamics2D and planar_observables.

The steering laws are test implementations of the SteeringLaw protocol in the four
forms of plan section 5 (radial, fixed tilt, along v_rel, linear tangent); the run laws
arrive with guidance.py in build step 21.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
import yaml

from launchsim.atmosphere import ambient_scalar
from launchsim.config import VehicleConfig
from launchsim.constants import MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M, V_REL_EPS_MPS
from launchsim.dynamics import (
    PLANAR_LAYOUT,
    PLANAR_STATE_NAMES,
    ConstantGravity,
    InverseSquareGravity,
    PlanarDynamics2D,
    PlanarKinematics,
    PlanarParams,
    planar_forces,
    planar_kinematics,
    planar_observables,
    planar_rotation_rate,
    rhs_planar,
    vacuum_atmosphere,
)
from launchsim.phases import IntegratorSettings, PhaseSpec, atol_for, integrate_phase
from launchsim.vehicle import Startup, ThrustSchedule, Vehicle

LAY = PLANAR_LAYOUT
TOY_C_MPS = 3000.0
N_IDENTITY_STATES = 1000
IDENTITY_REL = 1e-12
SEED = 20260929
G_TEST = 9.81
"""Constant gravity [m/s^2] of the analytic fixture tests (never g0)."""
FLAT_DATUM_M = 1.0e7
"""Datum radius [m] of the flat-Earth tests (h resolution ulp(1e7) = 1.9e-9 m)."""


@dataclass(frozen=True)
class Radial:
    """Thrust along r_hat."""

    along_vrel: bool = False

    def direction(self, t: float, y: np.ndarray, kin: PlanarKinematics) -> tuple[float, float]:
        return 1.0, 0.0


@dataclass(frozen=True)
class FixedTilt:
    """Thrust tilted delta from local vertical toward downrange."""

    delta_rad: float
    along_vrel: bool = False

    def direction(self, t: float, y: np.ndarray, kin: PlanarKinematics) -> tuple[float, float]:
        return math.cos(self.delta_rad), math.sin(self.delta_rad)


@dataclass(frozen=True)
class AlongVrel:
    """Thrust along v_rel (local vertical below V_REL_EPS_MPS)."""

    along_vrel: bool = True

    def direction(self, t: float, y: np.ndarray, kin: PlanarKinematics) -> tuple[float, float]:
        return kin.sin_g, kin.cos_g


@dataclass(frozen=True)
class LinearTangent:
    """tan(pitch) = a - b (t - t0) in the local horizontal frame."""

    a: float
    b_per_s: float
    t0_s: float
    along_vrel: bool = False

    def direction(self, t: float, y: np.ndarray, kin: PlanarKinematics) -> tuple[float, float]:
        s = self.a - self.b_per_s * (t - self.t0_s)
        n = math.sqrt(1.0 + s * s)
        return s / n, 1.0 / n


@pytest.fixture(scope="module")
def gate_vehicle(repo_root: Path) -> Vehicle:
    """The gate fork generic_f9_class_2d.yaml (engines, A_e and the Braeunig drag)."""
    path = repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return VehicleConfig.model_validate(raw).to_vehicle()


def _g_eff(r: float, omega_p: float) -> float:
    return MU_EARTH_M3S2 / (r * r) - omega_p * omega_p * r


# --------------------------------------------------------------- rocket equation


@pytest.mark.parametrize("v0", [1e-3, 100.0, 3000.0])
def test_rocket_equation_2d_along_velocity(toy_stage, v0: float) -> None:
    """mu = 0, omega_p = 0, thrust along v from a start 30 deg above horizontal: the
    path is a straight line and V_f - V_0 = c ln(m0/m_f) (1e-9 relative; CLAUDE.md asks
    1e-6). J_vac equals it, J_steer and J_grav stay exactly 0, and the Cartesian end
    point lies on the start line at the distance v0 t_b + c [t_b - (m_f/mdot)
    ln(m0/m_f)] (1e-9 relative)."""
    stage = toy_stage
    m0 = stage.wet_mass_kg
    mf = stage.dry_mass_kg
    mdot = stage.mdot_full_kgps
    t_b = stage.propellant_mass_kg / mdot
    params = PlanarParams(
        ConstantGravity(0.0),
        0.0,
        0.0,
        stage.schedule(0.0, Startup("step")),
        None,
        vacuum_atmosphere,
        AlongVrel(),
    )
    gamma0 = math.radians(30.0)
    y0 = LAY.build(
        r_m=R_EARTH_M,
        v_r_mps=v0 * math.sin(gamma0),
        v_theta_mps=v0 * math.cos(gamma0),
        m_kg=m0,
    )
    spec = PhaseSpec("BURN", 0, 0.0, t_b, rhs_planar, params, (), atol_for(PLANAR_STATE_NAMES))
    res = integrate_phase(spec, y0, IntegratorSettings(rtol=1e-10))
    y = res.y_end
    speed = math.hypot(LAY.get(y, "v_r_mps"), LAY.get(y, "v_theta_mps"))
    dv = TOY_C_MPS * math.log(m0 / mf)
    assert LAY.get(y, "m_kg") == pytest.approx(mf, rel=1e-12)
    assert speed - v0 == pytest.approx(dv, rel=1e-9)
    assert LAY.get(y, "J_vac_mps") == pytest.approx(dv, rel=1e-9)
    assert LAY.get(res.y, "J_steer_mps").max() == 0.0
    assert np.all(LAY.get(res.y, "J_grav_mps") == 0.0)
    # Straight line: Cartesian (x downrange, z up at the start) end point.
    dist = v0 * t_b + TOY_C_MPS * (t_b - (mf / mdot) * math.log(m0 / mf))
    r = LAY.get(y, "r_m")
    th = LAY.get(y, "theta_rad")
    x_end = r * math.sin(th)
    z_end = r * math.cos(th) - R_EARTH_M
    assert x_end == pytest.approx(dist * math.cos(gamma0), rel=1e-9)
    assert z_end == pytest.approx(dist * math.sin(gamma0), rel=1e-9)


# ----------------------------------------------------------- random state helpers


def _laws(rng: np.random.Generator) -> list:
    return [
        None,
        Radial(),
        FixedTilt(float(rng.uniform(0.0, 0.8))),
        AlongVrel(),
        LinearTangent(float(rng.uniform(-1.0, 3.0)), float(rng.uniform(-0.01, 0.02)), 0.0),
    ]


def _random_case(rng: np.random.Generator, vehicle: Vehicle, k: int):
    """One seeded (t, y, params) with rotation, drag, a lit or unlit schedule, the
    back-pressure clamp and, for every tenth state, V below V_REL_EPS_MPS."""
    omega_p = float(
        rng.choice([0.0, planar_rotation_rate(math.radians(28.5), math.pi / 2), OMEGA_EARTH_RADS])
    )
    clamp_case = k % 5 == 0
    stage = vehicle.stages[0 if clamp_case else int(rng.integers(0, 2))]
    schedule = stage.schedule(0.0)
    laws = _laws(rng)
    law = laws[1 + int(rng.integers(0, 4))] if clamp_case else laws[int(rng.integers(0, 5))]
    if law is None:
        schedule = None
    alt = float(rng.uniform(-50.0, 250e3))
    t = float(rng.uniform(-1.0, 12.0))
    if clamp_case:
        # Stage 1 in dense air inside the back-pressure clamp window of its 2 s ramp
        # (T_vac < p A_e for the first ~0.15 s at sea level).
        alt = float(rng.uniform(-50.0, 500.0))
        t = float(rng.uniform(0.0, 0.14))
    r = R_EARTH_M + alt
    if k % 10 == 0:
        w = float(rng.uniform(-1.0, 1.0)) * 1e-10
        u = float(rng.uniform(-1.0, 1.0)) * 1e-10
    else:
        w = float(rng.uniform(-3000.0, 3000.0))
        u = float(rng.uniform(-3000.0, 8000.0))
    y = LAY.build(
        r_m=r,
        theta_rad=float(rng.uniform(0.0, 0.5)),
        v_r_mps=w,
        v_theta_mps=u + omega_p * r,
        m_kg=float(rng.uniform(2e4, 6e5)),
        J_vac_mps=1.0,
        J_grav_mps=2.0,
    )
    params = PlanarParams(
        InverseSquareGravity(MU_EARTH_M3S2),
        omega_p,
        _g_eff(R_EARTH_M, omega_p),
        schedule,
        vehicle.aero,
        ambient_scalar,
        law,
    )
    return t, y, params


def _expected_terms(t: float, y: np.ndarray, p: PlanarParams, vehicle: Vehicle) -> dict:
    """The model terms written out here from the inputs (atmosphere function, datum,
    drag table, schedule and law are inputs; the formulas are this test's; gravity is
    mu/r^2 with Earth's mu)."""
    r = y[LAY.index("r_m")]
    v_r = y[LAY.index("v_r_mps")]
    v_t = y[LAY.index("v_theta_mps")]
    m = y[LAY.index("m_kg")]
    w = v_r
    u = v_t - p.omega_p_rads * r
    speed = math.sqrt(w * w + u * u)
    if speed < V_REL_EPS_MPS:
        sg, cg = 1.0, 0.0
    else:
        sg, cg = w / speed, u / speed
    p_amb, rho, a = p.atmosphere(r - p.r_datum_m)
    if p.schedule is None:
        t_vac = 0.0
        thrust = 0.0
        c = math.inf
        e_r, e_t = sg, cg
    else:
        t_vac = p.schedule.thrust_vac_N(t)
        thrust = max(0.0, t_vac - p_amb * p.schedule.exit_area_total_m2)
        c = p.schedule.c_mps
        e_r, e_t = p.steering.direction(t, y, PlanarKinematics(w, u, speed, sg, cg))
    cos_psi = e_r * sg + e_t * cg
    drag_model = vehicle.aero
    drag = 0.5 * rho * speed * speed * drag_model.cd(speed / a) * drag_model.reference_area_m2
    g = MU_EARTH_M3S2 / (r * r)
    return {
        "w": w,
        "u": u,
        "V": speed,
        "sg": sg,
        "cg": cg,
        "t_vac": t_vac,
        "T": thrust,
        "c": c,
        "e_r": e_r,
        "e_t": e_t,
        "cos_psi": cos_psi,
        "D": drag,
        "g": g,
        "g_eff": g - p.omega_p_rads**2 * r,
        "m": m,
        "r": r,
        "v_r": v_r,
        "v_t": v_t,
    }


# --------------------------------------------------------------- RHS components


def test_rhs_components_match_the_equations_of_motion(gate_vehicle: Vehicle) -> None:
    """Every row of rhs_planar against the EOM written here, on 300 seeded states:
    dr = v_r; dtheta = v_theta/r; dv_r = v_theta^2/r - g + (T e_r - D sin_g)/m;
    dv_theta = -v_r v_theta/r + (T e_theta - D cos_g)/m; dm = -T_vac/c; the quadratures
    T_vac/m, g_eff sin_g, (g_eff - g_ref) sin_g, D/m, (T/m)(1 - cos psi) (0 along
    v_rel), (T_vac - T)/m. 1e-12 relative to the largest term of each row."""
    rng = np.random.default_rng(SEED)
    for k in range(300):
        t, y, p = _random_case(rng, gate_vehicle, k)
        x = _expected_terms(t, y, p, gate_vehicle)
        dy = rhs_planar(t, y, p)
        m = x["m"]
        along = p.steering is None or p.steering.along_vrel
        steer = 0.0 if along else x["T"] / m * (1.0 - x["cos_psi"])
        rows = {
            "r_m": (x["v_r"], abs(x["v_r"])),
            "theta_rad": (x["v_t"] / x["r"], abs(x["v_t"] / x["r"])),
            "v_r_mps": (
                x["v_t"] ** 2 / x["r"] - x["g"] + (x["T"] * x["e_r"] - x["D"] * x["sg"]) / m,
                x["v_t"] ** 2 / x["r"] + x["g"] + (x["T"] + x["D"]) / m,
            ),
            "v_theta_mps": (
                -x["v_r"] * x["v_t"] / x["r"] + (x["T"] * x["e_t"] - x["D"] * x["cg"]) / m,
                abs(x["v_r"] * x["v_t"] / x["r"]) + (x["T"] + x["D"]) / m,
            ),
            "m_kg": (-x["t_vac"] / x["c"], x["t_vac"] / x["c"]),
            "J_vac_mps": (x["t_vac"] / m, x["t_vac"] / m),
            "J_grav_mps": (x["g_eff"] * x["sg"], x["g_eff"]),
            "J_alt_mps": ((x["g_eff"] - p.g_ref_mps2) * x["sg"], x["g_eff"]),
            "J_drag_mps": (x["D"] / m, x["D"] / m),
            "J_steer_mps": (steer, x["T"] / m),
            "J_bp_mps": ((x["t_vac"] - x["T"]) / m, x["t_vac"] / m),
        }
        for name, (expected, scale) in rows.items():
            got = dy[LAY.index(name)]
            assert abs(got - expected) <= IDENTITY_REL * max(scale, 1e-300), (k, name)
        if along:
            assert dy[LAY.index("J_steer_mps")] == 0.0


# --------------------------------------------------------------- pointwise identity


def test_pointwise_speed_identity(gate_vehicle: Vehicle) -> None:
    """dV/dt from the kinematic rows, (w w' + u u')/V with u' = v_theta' - omega_p r',
    equals dJ_vac - dJ_grav - dJ_drag - dJ_steer - dJ_bp from the quadrature rows of the
    same RHS and the closed form -g_eff w/V + (T cos psi - D)/m, on 1,000 seeded states
    (rotation 0, 28.5 deg and equatorial; ICAO drag; stage 1 in its back-pressure clamp
    and at full thrust, stage 2, unlit and unpowered; radial, fixed tilt, along v_rel
    and linear-tangent laws). Tolerance 1e-12 x max(T/m, T_vac/m, g_eff, D/m,
    |w w'|/V, |u u'|/V). Below V_REL_EPS_MPS the quadrature sum is the one-sided limit
    T e_r/m - g_eff - D/m (v_hat_rel = r_hat). Every regime is visited."""
    rng = np.random.default_rng(SEED + 1)
    seen = {"clamped": 0, "lit": 0, "unlit": 0, "fallback": 0, "drag": 0, "rotation": 0}
    for k in range(N_IDENTITY_STATES):
        t, y, p = _random_case(rng, gate_vehicle, k)
        x = _expected_terms(t, y, p, gate_vehicle)
        dy = rhs_planar(t, y, p)
        m = x["m"]
        quad = (
            dy[LAY.index("J_vac_mps")]
            - dy[LAY.index("J_grav_mps")]
            - dy[LAY.index("J_drag_mps")]
            - dy[LAY.index("J_steer_mps")]
            - dy[LAY.index("J_bp_mps")]
        )
        scale0 = max(x["T"] / m, x["t_vac"] / m, x["g_eff"], x["D"] / m)
        if x["V"] < V_REL_EPS_MPS:
            seen["fallback"] += 1
            limit = x["T"] * x["e_r"] / m - x["g_eff"] - x["D"] / m
            assert abs(quad - limit) <= IDENTITY_REL * scale0, k
            continue
        w_dot = dy[LAY.index("v_r_mps")]
        u_dot = dy[LAY.index("v_theta_mps")] - p.omega_p_rads * dy[LAY.index("r_m")]
        lhs = (x["w"] * w_dot + x["u"] * u_dot) / x["V"]
        closed = -x["g_eff"] * x["sg"] + (x["T"] * x["cos_psi"] - x["D"]) / m
        scale = max(scale0, abs(x["w"] * w_dot) / x["V"], abs(x["u"] * u_dot) / x["V"])
        assert abs(lhs - quad) <= IDENTITY_REL * scale, k
        assert abs(lhs - closed) <= IDENTITY_REL * scale, k
        seen["clamped"] += x["t_vac"] > 0.0 and x["T"] == 0.0
        seen["lit"] += x["T"] > 0.0
        seen["unlit"] += x["t_vac"] == 0.0
        seen["drag"] += x["D"] > 0.0
        seen["rotation"] += p.omega_p_rads > 0.0
    assert all(n > 10 for n in seen.values()), seen


def test_fallback_is_the_one_sided_limit() -> None:
    """On the pad with rotation (w = u = 0, V = 0) and radial thrust T > m g_eff:

    - at V = 0 the quadrature sum and dv_r/dt equal T/m - g_eff and dv_theta/dt = 0;
    - at a small V along +r_hat (w = 1e-6 m/s, u = 0) the ordinary identity
      (w w' + u u')/V = w' equals the quadrature sum and the V = 0 value (1e-14
      relative);
    - integrated for h = 1e-3 s from the pad, V(h) equals the rocket closed form
      c ln(m0/(m0 - mdot h)) - g_eff h (1e-9 relative: g_eff changes by about 1e-12
      over the 5 micrometres climbed and u = -omega_p z enters V at second order), so
      V(h)/h -> T/m - g_eff (1e-5 relative at this h), and the planar loss identity
      closes to 1e-14 m/s.
    """
    omega_p = planar_rotation_rate(math.radians(28.5), math.pi / 2)
    g_eff = _g_eff(R_EARTH_M, omega_p)
    thrust, c, m = 2.0e4, 3000.0, 1000.0
    sched = ThrustSchedule(thrust, c, 0.0, 0.0, Startup("step"))
    grav = InverseSquareGravity(MU_EARTH_M3S2)
    p = PlanarParams(grav, omega_p, g_eff, sched, None, vacuum_atmosphere, Radial())
    limit = thrust / m - g_eff
    losses = ("J_grav_mps", "J_drag_mps", "J_steer_mps", "J_bp_mps")

    def quad_sum(dy: np.ndarray) -> float:
        return dy[LAY.index("J_vac_mps")] - sum(dy[LAY.index(n)] for n in losses)

    y0 = LAY.build(r_m=R_EARTH_M, v_theta_mps=omega_p * R_EARTH_M, m_kg=m)
    dy = rhs_planar(0.5, y0, p)
    assert quad_sum(dy) == pytest.approx(limit, rel=1e-14)
    assert dy[LAY.index("v_theta_mps")] == 0.0  # no tangential force at the pad
    assert dy[LAY.index("v_r_mps")] == pytest.approx(limit, rel=1e-14)

    w_small = 1e-6
    y_small = LAY.build(r_m=R_EARTH_M, v_r_mps=w_small, v_theta_mps=omega_p * R_EARTH_M, m_kg=m)
    kin = planar_kinematics(y_small, omega_p)
    assert kin.V_mps >= V_REL_EPS_MPS
    ds = rhs_planar(0.5, y_small, p)
    u_dot = ds[LAY.index("v_theta_mps")] - omega_p * ds[LAY.index("r_m")]
    lhs = (kin.w_mps * ds[LAY.index("v_r_mps")] + kin.u_mps * u_dot) / kin.V_mps
    assert lhs == pytest.approx(limit, rel=1e-14)
    assert quad_sum(ds) == pytest.approx(limit, rel=1e-14)

    h = 1e-3
    spec = PhaseSpec("BURN", 0, 0.0, h, rhs_planar, p, (), atol_for(PLANAR_STATE_NAMES))
    y = integrate_phase(spec, y0, IntegratorSettings(rtol=1e-10)).y_end
    u = LAY.get(y, "v_theta_mps") - omega_p * LAY.get(y, "r_m")
    speed = math.hypot(LAY.get(y, "v_r_mps"), u)
    mdot = thrust / c
    assert speed == pytest.approx(c * math.log(m / (m - mdot * h)) - g_eff * h, rel=1e-9)
    assert speed / h == pytest.approx(limit, rel=1e-5)
    closure = speed - (LAY.get(y, "J_vac_mps") - sum(LAY.get(y, n) for n in losses))
    assert abs(closure) <= 1e-14


# ------------------------------------------------------- datum and the fixtures


def test_atmosphere_is_evaluated_above_the_datum(
    gate_vehicle: Vehicle, large_R_params, exp_atmosphere
) -> None:
    """With the altitude datum at R = FLAT_DATUM_M (not R_E), planar_forces reads the
    atmosphere at h = r - R: under the ICAO atmosphere p, rho and a are those of h, the
    clamp T = max(0, T_vac - p(h) A_e) holds inside the 2 s ramp (T = 0 at 5 km) and at
    full thrust, q = 0.5 rho(h) V^2 and D = q C_D(V/a(h)) A_ref; under
    exp_atmosphere(1.225, 7000) rho = 1.225 exp(-h/7000) and p = 0 (no clamp). Gravity
    is g_test (R/r)^2 and the dv_r row matches (1e-12 relative). R - R_E = 3.6e6 m, so
    reading the atmosphere at r - R_E would give near-vacuum values."""
    stage = gate_vehicle.stages[0]
    aero = gate_vehicle.aero
    sched = stage.schedule(0.0)
    alt = 5000.0
    r = FLAT_DATUM_M + alt
    w, u = 200.0, 100.0
    m = 4e5
    speed = math.hypot(w, u)
    y = LAY.build(r_m=r, v_r_mps=w, v_theta_mps=u, m_kg=m)
    law = FixedTilt(0.1)
    g = G_TEST * (FLAT_DATUM_M / r) ** 2

    p = large_R_params(FLAT_DATUM_M, G_TEST, sched, law, aero, ambient_scalar)
    p_amb, rho, a = ambient_scalar(alt)
    for t in (0.05, 3.0):
        f = planar_forces(t, y, p)
        assert (f.p_pa, f.rho_kgm3, f.a_mps) == (p_amb, rho, a)
        expected_thrust = max(0.0, sched.thrust_vac_N(t) - p_amb * stage.exit_area_total_m2)
        assert f.T_N == pytest.approx(expected_thrust, rel=1e-12)
        q = 0.5 * rho * speed * speed
        assert f.q_pa == pytest.approx(q, rel=1e-12)
        assert f.D_N == pytest.approx(q * aero.cd(speed / a) * aero.reference_area_m2, rel=1e-12)
        dv_r = u * u / r - g + (expected_thrust * math.cos(0.1) - f.D_N * w / speed) / m
        assert rhs_planar(t, y, p)[LAY.index("v_r_mps")] == pytest.approx(dv_r, rel=1e-12)
    assert planar_forces(0.05, y, p).T_N == 0.0

    rho0, scale_h = 1.225, 7000.0
    p_exp = large_R_params(FLAT_DATUM_M, G_TEST, sched, law, aero, exp_atmosphere(rho0, scale_h))
    f = planar_forces(3.0, y, p_exp)
    rho_exp = rho0 * math.exp(-alt / scale_h)
    assert f.rho_kgm3 == pytest.approx(rho_exp, rel=1e-12)
    assert f.p_pa == 0.0
    assert f.T_N == f.T_vac_N > 0.0
    assert f.q_pa == pytest.approx(0.5 * rho_exp * speed * speed, rel=1e-12)
    assert planar_observables(3.0, y, p_exp, 0.0)["alt_m"] == pytest.approx(alt, abs=1e-8)


def test_planar_fixture_factories(
    large_R_params, const_accel_schedule, exp_atmosphere, const_atmosphere
) -> None:
    """The conftest factories: large_R_params(R, g) has g = g_test at the datum and
    g_test (R/r)^2 above it, no rotation, g_ref = g_test and datum R; exp_atmosphere(
    1.225, 7000) at 7,000 m is (0, 1.225/e, 340); const_atmosphere(p) is (p, 0, 340) at
    any altitude; const_accel_schedule(A, m, t_ign) has no thrust before t_ign and
    T/m = A to rounding: integrated radially from rest at t_ign for 100 s under
    ConstantGravity(g_test) in vacuum, the mass stays m exactly, J_vac = A t (1e-12
    relative), v = (A - g) t and z = (A - g) t^2/2 (1e-10 relative)."""
    p = large_R_params(FLAT_DATUM_M, G_TEST)
    assert p.gravity(FLAT_DATUM_M) == pytest.approx(G_TEST, rel=1e-15)
    assert p.gravity(FLAT_DATUM_M + 1e4) == pytest.approx(
        G_TEST / (1.0 + 1e4 / FLAT_DATUM_M) ** 2, rel=1e-14
    )
    assert (p.omega_p_rads, p.g_ref_mps2, p.r_datum_m) == (0.0, G_TEST, FLAT_DATUM_M)
    assert (p.schedule, p.steering, p.drag) == (None, None, None)

    p0, rho, a = exp_atmosphere(1.225, 7000.0)(7000.0)
    assert (p0, a) == (0.0, 340.0)
    assert rho == pytest.approx(1.225 / math.e, rel=1e-15)
    for alt in (-50.0, 0.0, 3e4, 2e5):
        assert const_atmosphere(101_325.0)(alt) == (101_325.0, 0.0, 340.0)

    accel, m0, t_ign, t_burn = 20.0, 500.0, 1.0, 100.0
    sched = const_accel_schedule(accel, m_kg=m0, t_ign_s=t_ign)
    assert sched.thrust_vac_N(0.5) == 0.0
    params = PlanarParams(
        ConstantGravity(G_TEST), 0.0, G_TEST, sched, None, vacuum_atmosphere, Radial()
    )
    y0 = LAY.build(r_m=R_EARTH_M, m_kg=m0)
    spec = PhaseSpec(
        "BURN", 0, t_ign, t_ign + t_burn, rhs_planar, params, (), atol_for(PLANAR_STATE_NAMES)
    )
    y = integrate_phase(spec, y0, IntegratorSettings(rtol=1e-10)).y_end
    net = accel - G_TEST
    assert LAY.get(y, "m_kg") == m0
    assert LAY.get(y, "J_vac_mps") == pytest.approx(accel * t_burn, rel=1e-12)
    assert LAY.get(y, "v_r_mps") == pytest.approx(net * t_burn, rel=1e-10)
    assert LAY.get(y, "r_m") - R_EARTH_M == pytest.approx(0.5 * net * t_burn**2, rel=1e-10)


# ------------------------------------------------------------ params and the model


def test_planar_params_validate(toy_stage) -> None:
    """A thrust schedule without a steering law, a non-positive datum, a negative g_ref
    and a non-finite rotation rate raise."""
    grav = InverseSquareGravity(MU_EARTH_M3S2)
    sched = toy_stage.schedule(0.0)
    with pytest.raises(ValueError, match="steering law"):
        PlanarParams(grav, 0.0, 9.8, sched, None, vacuum_atmosphere, None)
    with pytest.raises(ValueError, match="r_datum_m"):
        PlanarParams(grav, 0.0, 9.8, None, None, vacuum_atmosphere, None, r_datum_m=0.0)
    with pytest.raises(ValueError, match="g_ref"):
        PlanarParams(grav, 0.0, -1.0, None, None, vacuum_atmosphere, None)
    with pytest.raises(ValueError, match="omega_p"):
        PlanarParams(grav, math.nan, 9.8, None, None, vacuum_atmosphere, None)


def test_kinematics_and_model_views() -> None:
    """planar_kinematics: w = v_r, u = v_theta - omega_p r, V = hypot(w, u), the
    local-vertical fallback below V_REL_EPS_MPS; PlanarDynamics2D: layout, i_mass,
    altitude r - r_datum and speed |v_rel| for a vector and a series; omega_p_rads and
    r_datum_m are required, for_params copies them from the phase parameters and
    check_params refuses parameters that disagree."""
    omega_p = 7e-5
    r = R_EARTH_M + 1000.0
    y = LAY.build(r_m=r, v_r_mps=30.0, v_theta_mps=omega_p * r + 40.0, m_kg=5.0)
    kin = planar_kinematics(y, omega_p)
    assert kin.w_mps == 30.0
    assert kin.u_mps == pytest.approx(40.0, abs=1e-9)
    assert kin.V_mps == pytest.approx(50.0, rel=1e-12)
    assert kin.sin_g == pytest.approx(0.6, rel=1e-12)
    assert kin.cos_g == pytest.approx(0.8, rel=1e-11)
    pad = LAY.build(r_m=R_EARTH_M, v_theta_mps=omega_p * R_EARTH_M, m_kg=5.0)
    k0 = planar_kinematics(pad, omega_p)
    assert k0.V_mps < V_REL_EPS_MPS
    assert (k0.sin_g, k0.cos_g) == (1.0, 0.0)

    model = PlanarDynamics2D(omega_p_rads=omega_p, r_datum_m=R_EARTH_M)
    assert model.state_names == PLANAR_STATE_NAMES
    assert model.layout is PLANAR_LAYOUT
    assert model.i_mass == LAY.index("m_kg")
    assert model.altitude(y) == pytest.approx(1000.0, abs=1e-9)
    assert model.speed(y) == pytest.approx(50.0, rel=1e-12)
    series = np.stack([y, pad], axis=1)
    np.testing.assert_allclose(model.speed(series), [50.0, 0.0], atol=1e-8)
    np.testing.assert_allclose(model.altitude(series), [1000.0, 0.0], atol=1e-9)

    with pytest.raises(TypeError):
        PlanarDynamics2D()  # type: ignore[call-arg]
    grav = InverseSquareGravity(MU_EARTH_M3S2)
    params = PlanarParams(grav, omega_p, 9.8, None, None, vacuum_atmosphere, None, 7e6)
    built = PlanarDynamics2D.for_params(params)
    assert (built.omega_p_rads, built.r_datum_m) == (omega_p, 7e6)
    built.check_params(params)
    with pytest.raises(ValueError, match="disagree"):
        model.check_params(params)
    with pytest.raises(ValueError, match="disagree"):
        PlanarDynamics2D(omega_p_rads=0.0, r_datum_m=7e6).check_params(params)


def test_planar_observables(gate_vehicle: Vehicle) -> None:
    """Reported quantities of a hand state: alt r - R_E, Earth-fixed downrange
    R_E (theta - omega_p (t - t_fs)), speeds, gamma_rel = atan2(w, u), pitch
    atan2(e_r, e_theta), psi, q = 0.5 rho V^2, M = V/a and the thrust clamp; the pad
    state reports gamma_rel = pi/2 and downrange 0 at t_fs."""
    omega_p = planar_rotation_rate(math.radians(28.5), math.pi / 2)
    delta = 0.2
    r = R_EARTH_M + 10e3
    t_fs, t = 1.5, 21.5
    theta = omega_p * (t - t_fs) + 500.0 / R_EARTH_M
    w, u = 300.0, 100.0
    y = LAY.build(r_m=r, theta_rad=theta, v_r_mps=w, v_theta_mps=u + omega_p * r, m_kg=4e5)
    stage = gate_vehicle.stages[0]
    p = PlanarParams(
        InverseSquareGravity(MU_EARTH_M3S2),
        omega_p,
        _g_eff(R_EARTH_M, omega_p),
        stage.schedule(0.0),
        gate_vehicle.aero,
        ambient_scalar,
        FixedTilt(delta),
    )
    obs = planar_observables(t, y, p, t_fs)
    p_amb, rho, a = ambient_scalar(10e3)
    speed = math.hypot(w, u)
    assert obs["alt_m"] == pytest.approx(10e3, abs=1e-9)
    assert obs["downrange_m"] == pytest.approx(500.0, abs=1e-6)
    assert obs["speed_rel_mps"] == pytest.approx(speed, rel=1e-12)
    assert obs["speed_inertial_mps"] == pytest.approx(math.hypot(w, u + omega_p * r), rel=1e-12)
    assert obs["gamma_rel_rad"] == pytest.approx(math.atan2(w, u), rel=1e-12)
    assert obs["pitch_rad"] == pytest.approx(math.pi / 2 - delta, rel=1e-12)
    assert obs["psi_rad"] == pytest.approx(abs(math.atan2(w, u) - (math.pi / 2 - delta)), rel=1e-9)
    assert obs["q_pa"] == pytest.approx(0.5 * rho * speed**2, rel=1e-12)
    assert obs["mach"] == pytest.approx(speed / a, rel=1e-12)
    t_vac = stage.thrust_vac_total_N
    assert obs["thrust_vac_N"] == pytest.approx(t_vac, rel=1e-12)
    assert obs["thrust_N"] == pytest.approx(t_vac - p_amb * stage.exit_area_total_m2, rel=1e-12)
    forces = planar_forces(t, y, p)
    assert obs["drag_N"] == forces.D_N > 0.0

    pad = LAY.build(r_m=R_EARTH_M, v_theta_mps=omega_p * R_EARTH_M, m_kg=4e5)
    obs0 = planar_observables(t_fs, pad, p, t_fs)
    assert obs0["gamma_rel_rad"] == math.pi / 2
    assert obs0["downrange_m"] == 0.0
    assert obs0["drag_N"] == 0.0
