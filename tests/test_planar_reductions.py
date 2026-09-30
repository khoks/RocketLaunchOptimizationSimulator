"""Exact reductions of the planar model (docs/physics.md, "Planar reductions").

RHS level (build step 20) and planner level (build step 21, amendment 11: the pad and
silo_cold runs to stage-1 burnout through ``PlanarPlanner`` against ``VerticalPlanner``):

- No rotation, v_theta = 0, radial thrust, no drag, a constant ambient pressure: every
  row of rhs_planar equals the 1-D rhs_vertical row it maps to (r - R_E = z, v_r = v,
  sigma = sign(v)), and the extra rows (theta, v_theta, J_drag) are zero. Integrated,
  a stage-1 burn gives the 1-D altitude, speed, mass and every loss quadrature.
- CLAUDE.md's vertical burn under constant g through the planar RHS:
  v_f = v0 + c ln(m0/mf) - g t_b and the altitude closed form.
- Rotation with inertially radial thrust and no drag (the h0 reduction): r v_theta =
  h0 = omega_p R_E^2 is conserved, the radial motion is the 1-D model with
  g = mu/r^2 - h0^2/r^3 (H0Gravity), and u = omega_p (R_E^2/r - r).
- The planar planner with no rotation, no drag, a constant ambient pressure and the
  vertical-only guidance (radial thrust to burnout) reproduces the 1-D planner's pad
  and silo_cold runs: hold-down, track push, release, pre-ignition coast, ramp and
  burnout, with the same events and burnout state.

Altitude comparisons are relative (1e-10) with a 1e-6 m floor: the planar state
integrates r, which the step-size control resolves to about rtol R_E per step, not
ATOL_M (docs/physics.md, "Integrator", atol table), so the planar altitude error
grows with the burn (measured values at ALT_ABS_M).
"""

from __future__ import annotations

import dataclasses
import itertools
import math
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
import yaml

from launchsim.assist import build_assist
from launchsim.config import ConstantAccelConfig, VehicleConfig
from launchsim.constants import MU_EARTH_M3S2, OMEGA_EARTH_RADS, P_SEA_LEVEL_PA, R_EARTH_M
from launchsim.dynamics import (
    PLANAR_LAYOUT,
    PLANAR_STATE_NAMES,
    VERTICAL_LAYOUT,
    VERTICAL_STATE_NAMES,
    AtmosphereFn,
    ConstantGravity,
    H0Gravity,
    InverseSquareGravity,
    PlanarKinematics,
    PlanarParams,
    VerticalParams,
    planar_rotation_rate,
    rhs_planar,
    rhs_vertical,
    vacuum_atmosphere,
)
from launchsim.guidance import GuidanceSpec
from launchsim.phases import (
    IgnitionSpec,
    IntegratorSettings,
    PhaseSpec,
    VerticalPlanner,
    atol_for,
    integrate_phase,
)
from launchsim.phases.planar import PlanarEnvironment, PlanarPlanner
from launchsim.vehicle import Stage, Startup, ThrustSchedule, Vehicle

P2 = PLANAR_LAYOUT
V1 = VERTICAL_LAYOUT
G_TEST = 9.81
"""Constant gravity [m/s^2] of the analytic vertical-burn test (never g0)."""
TOY_C_MPS = 3000.0
SEED = 20260930
RTOL = 1e-10
PLANNER_RTOL = 1e-12
"""rtol of the planner-level reduction. At the shared 1e-10 each model's own global
error at the silo_cold burnout (114 km) is up to 5.0e-5 m in altitude (1-D; planar
8.3e-7 m) against its rtol-1e-13 reference, so the two runs differ by 4.2e-10 relative
in altitude and 1.0e-10 in speed; at 1e-12 they differ by 3.1e-11 and 1.3e-11 (pad:
4.6e-13 and 1.5e-13), well inside the plan's 1e-10."""
N_GRID = 16
"""Common comparison times of the h0 reduction (segment ends, no interpolation)."""
ALT_ABS_M = 1e-6
"""Absolute altitude allowance [m] of the integrated comparisons (plan section 8), next
to 1e-10 relative. Measured at rtol 1e-10: planar vs 1-D stage-1 burn 2.6e-9 m at
208 km; constant-g closed form -3.2e-6 to -4.5e-6 m at 161-209 km (2e-11 relative, so
the relative term governs); h0 reduction 1.6e-7 m."""

# 1-D row -> planar row of the reduction.
ROW_MAP = {
    "z_m": "r_m",
    "v_mps": "v_r_mps",
    "m_kg": "m_kg",
    "J_vac_mps": "J_vac_mps",
    "J_grav_mps": "J_grav_mps",
    "J_alt_mps": "J_alt_mps",
    "J_bp_mps": "J_bp_mps",
    "J_steer_mps": "J_steer_mps",
}


class Radial:
    """Thrust along r_hat (test implementation of the SteeringLaw protocol)."""

    along_vrel = False

    def direction(self, t: float, y: np.ndarray, kin: PlanarKinematics) -> tuple[float, float]:
        return 1.0, 0.0


@pytest.fixture(scope="module")
def gate_vehicle(repo_root: Path) -> Vehicle:
    """The gate fork generic_f9_class_2d.yaml."""
    path = repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return VehicleConfig.model_validate(raw).to_vehicle()


def _pair_params(
    gravity,
    g_ref: float,
    schedule: ThrustSchedule | None,
    p_amb: float,
    sigma: int,
    const_atmosphere: Callable[[float], AtmosphereFn],
):
    """The 1-D parameters and the planar parameters of the same no-rotation phase; the
    planar atmosphere is the conftest const_atmosphere(p_amb) (rho = 0, no drag)."""
    one = VerticalParams(gravity, g_ref, schedule, R_EARTH_M, p_amb, sigma)
    two = PlanarParams(gravity, 0.0, g_ref, schedule, None, const_atmosphere(p_amb), Radial())
    return one, two


def _to_planar(y1: np.ndarray) -> np.ndarray:
    """The planar state of a 1-D state: r = R_E + z, v_r = v, theta = v_theta = 0."""
    return P2.build(
        r_m=R_EARTH_M + V1.get(y1, "z_m"),
        **{ROW_MAP[n]: float(V1.get(y1, n)) for n in VERTICAL_STATE_NAMES if n != "z_m"},
    )


def _fly(rhs, params, y0, segments, sigma: int = 1):
    """Integrate consecutive fixed-time segments [(t0, t1), ...] with one params."""
    names = P2.names if rhs is rhs_planar else V1.names
    y = np.asarray(y0, dtype=float)
    results = []
    for t0, t1 in segments:
        spec = PhaseSpec("BURN", 0, t0, t1, rhs, params, (), atol_for(tuple(names)), sigma=sigma)
        res = integrate_phase(spec, y, IntegratorSettings(rtol=RTOL))
        results.append(res)
        y = res.y_end
    return results


def test_rhs_rows_equal_the_vertical_rows(
    gate_vehicle: Vehicle, const_atmosphere: Callable[[float], AtmosphereFn]
) -> None:
    """On 500 seeded states (z in [-100 m, 300 km], v of either sign and 0, the F9
    stage-1 2 s ramp from before ignition to full thrust, a constant 101,325 Pa or 0 for
    the clamp): dr = dz, dv_r = dv, dm, and every quadrature row equal the 1-D rows
    (1e-15 relative), with sigma = sign(v) (+1 at v = 0, the planar local-vertical
    fallback), and dtheta = dv_theta = dJ_drag = 0 exactly."""
    rng = np.random.default_rng(SEED)
    stage = gate_vehicle.stages[0]
    grav = InverseSquareGravity(MU_EARTH_M3S2)
    g_ref = grav(R_EARTH_M)
    for k in range(500):
        t = float(rng.uniform(-0.5, 4.0))
        v = 0.0 if k % 10 == 0 else float(rng.uniform(-3000.0, 3000.0))
        sigma = -1 if v < 0.0 else 1
        p_amb = P_SEA_LEVEL_PA if k % 2 else 0.0
        one, two = _pair_params(grav, g_ref, stage.schedule(0.0), p_amb, sigma, const_atmosphere)
        y1 = V1.build(
            z_m=float(rng.uniform(-100.0, 300e3)),
            v_mps=v,
            m_kg=float(rng.uniform(3e4, 5.6e5)),
            J_vac_mps=5.0,
        )
        d1 = rhs_vertical(t, y1, one)
        d2 = rhs_planar(t, _to_planar(y1), two)
        for n1, n2 in ROW_MAP.items():
            a, b = d1[V1.index(n1)], d2[P2.index(n2)]
            assert b == pytest.approx(a, rel=1e-15, abs=0.0), (k, n1)
        assert d2[P2.index("theta_rad")] == 0.0
        assert d2[P2.index("v_theta_mps")] == 0.0
        assert d2[P2.index("J_drag_mps")] == 0.0


def test_integrated_stage1_burn_matches_the_vertical_model(
    gate_vehicle: Vehicle, const_atmosphere: Callable[[float], AtmosphereFn]
) -> None:
    """The F9 gate stage 1 released upward at 77 m/s and lit at release with its 2 s
    ramp (split at the ramp kink), constant 101,325 Pa (so the clamp books J_bp), mu/r^2,
    to burnout at t_r/2 + m_p/mdot: the planar run's r - R_E, v_r, m and every loss
    quadrature equal the 1-D run's (1e-10 relative; altitude with ALT_ABS_M), and
    theta, v_theta and J_drag stay 0."""
    stage = gate_vehicle.stages[0]
    grav = InverseSquareGravity(MU_EARTH_M3S2)
    g_ref = grav(R_EARTH_M)
    sched = stage.schedule(0.0)
    t_r = stage.startup.t_ramp_s
    t_b = 0.5 * t_r + stage.propellant_mass_kg / stage.mdot_full_kgps
    one, two = _pair_params(grav, g_ref, sched, P_SEA_LEVEL_PA, 1, const_atmosphere)
    y1 = V1.build(v_mps=77.0, m_kg=stage.wet_mass_kg + 30e3)
    segs = [(0.0, t_r), (t_r, t_b)]
    r1 = _fly(rhs_vertical, one, y1, segs)[-1].y_end
    r2 = _fly(rhs_planar, two, _to_planar(y1), segs)[-1].y_end
    assert P2.get(r2, "r_m") - R_EARTH_M == pytest.approx(
        V1.get(r1, "z_m"), rel=1e-10, abs=ALT_ABS_M
    )
    for n1, n2 in ROW_MAP.items():
        if n1 != "z_m":
            assert P2.get(r2, n2) == pytest.approx(V1.get(r1, n1), rel=1e-10, abs=1e-9), n1
    assert V1.get(r1, "J_bp_mps") > 0.0
    for n in ("theta_rad", "v_theta_mps", "J_drag_mps"):
        assert P2.get(r2, n) == 0.0


@pytest.mark.parametrize("v0", [0.0, 30.0, 77.0, 300.0])
def test_vertical_burn_constant_g_through_the_planar_rhs(toy_stage: Stage, v0: float) -> None:
    """CLAUDE.md's vertical burn with ConstantGravity(g_test), no rotation, radial
    thrust, vacuum, a step start at t = 0 and burnout at t_b = m_p/mdot:
    v_f = v0 + c ln(m0/mf) - g t_b (1e-10 relative), z_f = v0 t_b - g t_b^2/2 +
    c [t_b - (mf/mdot) ln(m0/mf)] (1e-10 relative with ALT_ABS_M), J_grav = g t_b."""
    m0 = toy_stage.wet_mass_kg
    mf = toy_stage.dry_mass_kg
    mdot = toy_stage.mdot_full_kgps
    t_b = toy_stage.propellant_mass_kg / mdot
    params = PlanarParams(
        ConstantGravity(G_TEST),
        0.0,
        G_TEST,
        toy_stage.schedule(0.0, Startup("step")),
        None,
        vacuum_atmosphere,
        Radial(),
    )
    y0 = P2.build(r_m=R_EARTH_M, v_r_mps=v0, m_kg=m0)
    y = _fly(rhs_planar, params, y0, [(0.0, t_b)])[-1].y_end
    ln = math.log(m0 / mf)
    v_f = v0 + TOY_C_MPS * ln - G_TEST * t_b
    z_f = v0 * t_b - 0.5 * G_TEST * t_b * t_b + TOY_C_MPS * (t_b - (mf / mdot) * ln)
    assert P2.get(y, "v_r_mps") == pytest.approx(v_f, rel=1e-10)
    assert P2.get(y, "r_m") - R_EARTH_M == pytest.approx(z_f, rel=1e-10, abs=ALT_ABS_M)
    assert P2.get(y, "J_grav_mps") == pytest.approx(G_TEST * t_b, rel=1e-10)
    assert P2.get(y, "J_vac_mps") == pytest.approx(TOY_C_MPS * ln, rel=1e-10)


@pytest.mark.parametrize(
    "omega_p",
    [planar_rotation_rate(math.radians(28.5), math.pi / 2), OMEGA_EARTH_RADS],
    ids=["lat28.5", "equator"],
)
def test_h0_reduction(toy_stage: Stage, omega_p: float) -> None:
    """Rotation on, inertially radial thrust, no drag, A_e = 0, from the pad at rest
    relative to the ground (r = R_E, v_theta = omega_p R_E, V = 0): with no tangential
    force r v_theta = h0 = omega_p R_E^2 at every step (1e-12 relative), the altitude,
    radial speed and mass equal the 1-D model under H0Gravity(mu, h0) (g = mu/r^2 -
    h0^2/r^3) on a common time grid (1e-10 relative, altitude with ALT_ABS_M), J_vac
    agrees, u = v_theta - omega_p r = omega_p (R_E^2/r - r) (westward above the pad), the
    2-D steering loss is positive (u != 0 tilts v_rel away from the thrust) and the
    planar loss identity closes."""
    h0 = omega_p * R_EARTH_M * R_EARTH_M
    m0 = toy_stage.wet_mass_kg
    t_b = toy_stage.propellant_mass_kg / toy_stage.mdot_full_kgps
    sched = toy_stage.schedule(0.0, Startup("step"))
    grav = InverseSquareGravity(MU_EARTH_M3S2)
    g_ref = grav(R_EARTH_M) - omega_p * omega_p * R_EARTH_M
    two = PlanarParams(grav, omega_p, g_ref, sched, None, vacuum_atmosphere, Radial())
    h0_grav = H0Gravity(MU_EARTH_M3S2, h0)
    one = VerticalParams(h0_grav, h0_grav(R_EARTH_M), sched, R_EARTH_M, 0.0, 1)
    assert h0_grav(R_EARTH_M) == pytest.approx(g_ref, rel=1e-14)

    y2 = P2.build(r_m=R_EARTH_M, v_theta_mps=omega_p * R_EARTH_M, m_kg=m0)
    y1 = V1.build(m_kg=m0)
    grid = np.linspace(0.0, t_b, N_GRID + 1)
    segs = [(float(a), float(b)) for a, b in itertools.pairwise(grid)]
    runs2 = _fly(rhs_planar, two, y2, segs)
    runs1 = _fly(rhs_vertical, one, y1, segs)

    r = np.concatenate([P2.get(res.y, "r_m") for res in runs2])
    v_t = np.concatenate([P2.get(res.y, "v_theta_mps") for res in runs2])
    assert np.max(np.abs(r * v_t - h0)) <= 1e-12 * h0
    u = v_t - omega_p * r
    u_closed = omega_p * (R_EARTH_M * R_EARTH_M / r - r)
    assert np.max(np.abs(u - u_closed)) <= 1e-11 * omega_p * R_EARTH_M
    assert u[-1] < 0.0

    # Segment ends are common grid times: compare the integrated states there.
    s2 = np.stack([res.y_end for res in runs2], axis=1)
    s1 = np.stack([res.y_end for res in runs1], axis=1)
    np.testing.assert_allclose(
        P2.get(s2, "r_m") - R_EARTH_M, V1.get(s1, "z_m"), rtol=1e-10, atol=ALT_ABS_M
    )
    np.testing.assert_allclose(P2.get(s2, "v_r_mps"), V1.get(s1, "v_mps"), rtol=1e-10, atol=1e-9)
    np.testing.assert_allclose(P2.get(s2, "m_kg"), V1.get(s1, "m_kg"), rtol=1e-12)
    res2, res1 = runs2[-1], runs1[-1]
    assert P2.get(res2.y_end, "J_vac_mps") == pytest.approx(
        V1.get(res1.y_end, "J_vac_mps"), rel=1e-10
    )

    assert P2.get(res2.y_end, "J_steer_mps") > 0.0
    y_f = res2.y_end
    speed_f = math.hypot(P2.get(y_f, "v_r_mps"), P2.get(y_f, "v_theta_mps") - omega_p * r[-1])
    losses = sum(P2.get(y_f, n) for n in ("J_grav_mps", "J_drag_mps", "J_steer_mps", "J_bp_mps"))
    assert speed_f - 0.0 == pytest.approx(P2.get(y_f, "J_vac_mps") - losses, abs=1e-9)


def test_state_names_share_the_1d_quadratures() -> None:
    """The planar layout carries every 1-D quadrature under the same name plus J_drag,
    so the loss budget reads both models by name."""
    quads_1d = {n for n in VERTICAL_STATE_NAMES if n.startswith("J_")}
    quads_2d = {n for n in PLANAR_STATE_NAMES if n.startswith("J_")}
    assert quads_2d == quads_1d | {"J_drag_mps"}


@pytest.mark.parametrize("case", ["pad", "silo_cold"])
def test_planner_reduces_to_the_vertical_planner(
    gate_vehicle: Vehicle, const_atmosphere: Callable[[float], AtmosphereFn], case: str
) -> None:
    """Planner level (amendment 11): the gate stage 1 with no drag (aero None), no
    rotation, a constant 101,325 Pa (the 1-D p_amb, so the hold-down balance, the
    track and the clamp book the same back-pressure), mu/r^2 and the vertical-only
    guidance flies the 1-D planner's run to burnout: the pad lit 2 s before release
    (closed-form hold), and silo_cold (3 g, 100 m, lit 0.5 s after release: push,
    release, 0.5 s coast, ramp, burn). The event names, times and phase kinds (COAST_
    PRE_IGN for COAST_PRE_IGN, VERTICAL_RISE for BURN) agree; at burnout t, r - R_E,
    v_r, m and every loss quadrature equal the 1-D values (1e-10 relative, altitude
    with the 1e-6 m floor), and theta, v_theta and J_drag stay 0."""
    vehicle = dataclasses.replace(gate_vehicle, aero=None)
    grav = InverseSquareGravity(MU_EARTH_M3S2)
    g_eff = grav(R_EARTH_M)
    ignition = {
        "stage1": IgnitionSpec(-2.0 if case == "pad" else 0.5),
        "stage2": IgnitionSpec(0.0),
    }
    settings = IntegratorSettings(rtol=PLANNER_RTOL)
    one = VerticalPlanner(
        vehicle, ignition, grav, g_eff, "stage1_burnout", settings, p_amb_pa=P_SEA_LEVEL_PA
    )
    env = PlanarEnvironment(grav, 0.0, const_atmosphere(P_SEA_LEVEL_PA))
    two = PlanarPlanner(
        vehicle, ignition, GuidanceSpec.vertical_only(), env, "stage1_burnout", settings
    )
    assert env.g_ref_mps2 == g_eff
    if case == "pad":
        t1, t2 = one.run_pad(), two.run(None)
    else:
        cfg = ConstantAccelConfig(
            model="constant_accel",
            net_accel_g=3.0,
            stroke_m=100.0,
            brake_decel_g=5.0,
            drive_efficiency=0.5,
        )
        assist, track = build_assist(cfg, g_eff)
        t1, t2 = one.run_track(assist, track), two.run(None, assist, track)
    assert [e.name for e in t2.events] == [e.name for e in t1.events]
    for e1, e2 in zip(t1.events, t2.events, strict=True):
        assert e2.t_s == pytest.approx(e1.t_s, rel=1e-10, abs=1e-12), e1.name
    kinds = {"BURN": "VERTICAL_RISE"}
    assert [p.spec.kind for p in t2.phases] == [
        kinds.get(p.spec.kind, p.spec.kind) for p in t1.phases
    ]
    assert t2.t_release_s == t1.t_release_s
    tb1, y1 = t1.burnouts["stage1"]
    tb2, y2 = t2.burnouts["stage1"]
    assert tb2 == pytest.approx(tb1, rel=1e-10)
    assert P2.get(y2, "r_m") - R_EARTH_M == pytest.approx(
        V1.get(y1, "z_m"), rel=1e-10, abs=ALT_ABS_M
    )
    for n1, n2 in ROW_MAP.items():
        if n1 != "z_m":
            assert P2.get(y2, n2) == pytest.approx(V1.get(y1, n1), rel=1e-10, abs=1e-9), n1
    assert V1.get(y1, "J_bp_mps") > 0.0
    for n in ("theta_rad", "v_theta_mps", "J_drag_mps"):
        assert P2.get(y2, n) == 0.0
