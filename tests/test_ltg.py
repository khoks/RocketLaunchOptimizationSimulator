"""Stage-2 linear-tangent steering and its shooting solve (docs/physics.md, "Stage 2 and
insertion (planar)" and "LTG shooting").

- The flat linear-tangent closed form: constant thrust acceleration A, uniform gravity
  g_test, tan p = tan p0 - c t from rest:

      v_x = (A/c) ln[(tan p0 + sec p0)/(tan p + sec p)]
      v_y = (A/c)(sec p0 - sec p) - g t

  on a datum of radius R = 1e14 m (curvature v^2/R ~ 2e-7 m/s^2) 1,000 km up, vacuum.
- The optimality of the linear tangent (amendment 11): on a flat Earth in uniform
  gravity with a fixed burn time, tan p linear in time maximises v_x,f for a given
  (h_f, v_y,f), so adding eps tau^2 and re-solving (a, b) for the same h_f and v_y,f = 0
  leaves v_x,f unchanged to first order: the central difference is zero while the
  second-order drop is not.
- The shooting on the gate fork (generic_f9_class_2d.yaml, 28.5 deg east, rotation,
  ICAO, Braeunig drag, the pad lit at -2 s, v_k 50 m/s, gamma* = 20 deg at the vehicle
  payload 22.8 t, rtol 1e-10 with dense output off, the shipped LtgConfig): every rung
  (warm, physics, steep) converges to the same direct root with E = E*, |r - r_t| <
  1 m, |v_r| < 1e-3 m/s and e < 1e-6; failures are typed and nothing unconverged is
  returned; 40 seeded random guesses either converge to the same root or raise typed
  (slow).
"""

from __future__ import annotations

import ast
import dataclasses
import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
import yaml
from scipy.optimize import brentq

from launchsim import guidance
from launchsim.atmosphere import ambient_scalar
from launchsim.config import LTG_GUESS_RUNGS, LtgConfig, SearchConfig, VehicleConfig
from launchsim.constants import MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M
from launchsim.dynamics import (
    PLANAR_LAYOUT,
    PLANAR_STATE_NAMES,
    InverseSquareGravity,
    PlanarParams,
    rhs_planar,
    vacuum_atmosphere,
)
from launchsim.guidance import (
    LTG_B_SCALE_S,
    LTG_RUNGS,
    DeltaSolveSettings,
    GuidanceFailure,
    GuidanceSpec,
    LinearTangent,
    LinearTangentEps,
    LtgSettings,
    is_direct_root,
    ltg_guess_ladder,
    ltg_physics_guess,
    solve_delta_for_gamma,
    solve_ltg,
)
from launchsim.orbit import TargetOrbit, orbit_elements
from launchsim.phases import IgnitionSpec, IntegratorSettings, PhaseSpec, atol_for, integrate_phase
from launchsim.phases.planar import Handover, PlanarEnvironment, PlanarPlanner, Stage2Result
from launchsim.vehicle import Startup, ThrustSchedule, Vehicle

P2 = PLANAR_LAYOUT
G_TEST = 9.81
"""Uniform gravity [m/s^2] of the flat analytic tests (never g0)."""
A_TEST = 15.0
"""Constant thrust acceleration [m/s^2] of the flat tests."""
HUGE_C_MPS = 1e30
"""Exhaust velocity of the flat tests' thrust (constant mass)."""
H0_M = 1.0e6
"""Start altitude [m] of the flat tests (no ground event needed)."""
T_BURN_S = 300.0
LAT_RAD = math.radians(28.5)
OMEGA_P = OMEGA_EARTH_RADS * math.cos(LAT_RAD)  # azimuth 90 deg
R_TARGET_M = R_EARTH_M + 200.0e3
GAMMA_STAR_RAD = math.radians(20.0)
RTOL = 1e-10


# ------------------------------------------------------------------- flat problems


def _flat_params(law: object, r_datum_m: float) -> PlanarParams:
    """Flat-Earth parameters: mu = g_test R^2 on a datum of radius R, no rotation, no
    air, a step start of A_TEST m/s^2 at t = 0 with c = 1e30 m/s."""
    schedule = ThrustSchedule(A_TEST, HUGE_C_MPS, 0.0, 0.0, Startup("step"))
    return PlanarParams(
        InverseSquareGravity(G_TEST * r_datum_m * r_datum_m),
        0.0,
        G_TEST,
        schedule,
        None,
        vacuum_atmosphere,
        law,  # type: ignore[arg-type]
        r_datum_m,
    )


def _fly_flat(law: object, r_datum_m: float, rtol: float) -> np.ndarray:
    """The state after T_BURN_S s of powered flight from rest H0_M above the datum."""
    y0 = P2.build(r_m=r_datum_m + H0_M, m_kg=1.0)
    spec = PhaseSpec(
        "LTG_BURN",
        1,
        0.0,
        T_BURN_S,
        rhs_planar,
        _flat_params(law, r_datum_m),
        (),
        atol_for(PLANAR_STATE_NAMES),
    )
    return integrate_phase(spec, y0, IntegratorSettings(rtol=rtol, dense_output=False)).y_end


def test_flat_linear_tangent_closed_form() -> None:
    """tan p = tan p0 - c t (p0 = 40 deg, c = 0.004 1/s) with A = 15 m/s^2 and g_test
    for 300 s from rest: v_theta and v_r equal the closed-form v_x and v_y within 1e-6
    relative (measured 1.4e-9 and 3.6e-8, the curvature of the R = 1e14 m datum)."""
    p0, c = math.radians(40.0), 0.004
    y = _fly_flat(LinearTangent(math.tan(p0), c, 0.0), 1e14, 1e-10)
    tan_p = math.tan(p0) - c * T_BURN_S
    sec0, sec = 1.0 / math.cos(p0), math.sqrt(1.0 + tan_p * tan_p)
    v_x = A_TEST / c * math.log((math.tan(p0) + sec0) / (tan_p + sec))
    v_y = A_TEST / c * (sec0 - sec) - G_TEST * T_BURN_S
    assert float(P2.get(y, "v_theta_mps")) == pytest.approx(v_x, rel=1e-6)
    assert float(P2.get(y, "v_r_mps")) == pytest.approx(v_y, rel=1e-6)


def test_linear_tangent_law() -> None:
    """LinearTangent(a, b, t_ign2) points along (s, 1)/sqrt(1 + s^2) with s = a - b (t -
    t_ign2), pitch atan(s); it is not along v_rel; non-finite inputs are refused.
    LinearTangentEps adds eps tau^2."""
    law = LinearTangent(0.8, 0.002, 100.0)
    for t in (100.0, 250.0, 600.0):
        s = 0.8 - 0.002 * (t - 100.0)
        e_r, e_t = law.direction(t, P2.zeros(), None)  # type: ignore[arg-type]
        assert (e_r, e_t) == pytest.approx((s / math.hypot(1.0, s), 1.0 / math.hypot(1.0, s)))
        assert math.atan2(e_r, e_t) == pytest.approx(math.atan(s), abs=1e-15)
        assert law.tan_pitch(t) == pytest.approx(s, abs=1e-15)
    assert not law.along_vrel
    with pytest.raises(ValueError):
        LinearTangent(math.nan, 0.0, 0.0)
    eps = LinearTangentEps(0.8, 0.002, 100.0, 1e-6)
    s = 0.8 - 0.002 * 50.0 + 1e-6 * 2500.0
    assert eps.direction(150.0, P2.zeros(), None)[0] == pytest.approx(  # type: ignore[arg-type]
        s / math.hypot(1.0, s)
    )


@dataclass(frozen=True)
class _FlatShot:
    """A fixed-time flat shot: the LtgShot fields plus v_x at the end."""

    r_cut_m: float
    v_r_cut_mps: float
    tau_cut_s: float
    v_x_mps: float


@pytest.mark.slow
def test_linear_tangent_is_optimal_on_a_flat_earth() -> None:
    """Amendment 11 (marked slow as the plan asks; measured 0.1 s). A = 15 m/s^2, g_test,
    300 s from rest, datum R = 1e10 m (altitude resolved to 2e-6 m): the linear tangent
    from p0 = 70 deg whose closed-form v_y(300 s) is 0 defines the target altitude. With
    eps tau^2 added (eps = +/-5.6e-7 1/s^2, a pitch change of up to 0.05 in tan p) and
    (a, b) re-solved by ``solve_ltg`` for the same altitude and v_y = 0, the central
    difference of v_x,f is below 1e-6 relative and below 1 % of the second-order drop,
    and v_x,f is a maximum at eps = 0 (measured: 5e-9 against 2.4e-6)."""
    r_datum = 1e10
    p0 = math.radians(70.0)
    sec0 = 1.0 / math.cos(p0)

    def v_y_end(b: float) -> float:
        tan_p = math.tan(p0) - b * T_BURN_S
        return A_TEST / b * (sec0 - math.sqrt(1.0 + tan_p * tan_p)) - G_TEST * T_BURN_S

    b0 = brentq(v_y_end, 1e-4, 0.05)
    target = float(P2.get(_fly_flat(LinearTangent(math.tan(p0), b0, 0.0), r_datum, 1e-12), "r_m"))
    settings = dataclasses.replace(
        _ltg_settings(), accept_r_m=1e-4, accept_vr_mps=1e-8, fd_step=1e-5, max_iters=40
    )

    def solve(eps: float) -> float:
        def shoot(a: float, b: float) -> _FlatShot:
            y = _fly_flat(LinearTangentEps(a, b, 0.0, eps), r_datum, 1e-12)
            r, v_r, v_t = (float(P2.get(y, n)) for n in ("r_m", "v_r_mps", "v_theta_mps"))
            return _FlatShot(r, v_r, T_BURN_S, v_t)

        sol = solve_ltg(shoot, target, settings, (("guess", (math.tan(p0), b0)),))
        return sol.shot.v_x_mps

    eps = 5.6e-7
    v0, v_plus, v_minus = solve(0.0), solve(eps), solve(-eps)
    first = abs(v_plus - v_minus) / (2.0 * v0)
    second = (v0 - 0.5 * (v_plus + v_minus)) / v0
    assert first < 1e-6
    assert second > 0.0 and first < 0.01 * second
    assert v0 > v_plus and v0 > v_minus


# ---------------------------------------------------------------- synthetic shooting


@dataclass(frozen=True)
class _SynthShot:
    """An LtgShot of the synthetic residual (cutoff radius, radial velocity, burn time)."""

    r_cut_m: float
    v_r_cut_mps: float
    tau_cut_s: float


SYNTH_R_T_M = 7.0e6
"""Target radius [m] of the synthetic shooting problem."""
SYNTH_ROOT_X = (0.7, 0.2)
"""Root in x = (a, 100 b) units: a = 0.7, b = 2e-3 1/s (a direct root over 300 s)."""
SYNTH_JAC = ((0.8, -0.3), (0.4, 1.1))
"""dF/dx of the linear synthetic residual F = SYNTH_JAC (x - SYNTH_ROOT_X)."""
SYNTH_GUESS_X = (1.0, 0.3)
"""Starting guess in x units."""
SYNTH_TAU_S = 300.0
"""Burn time [s] of every synthetic shot."""


def _synthetic_shoot(
    st: LtgSettings,
    calls: list[tuple[float, float]],
    fails: Callable[[tuple[float, float], int], bool],
) -> Callable[[float, float], _SynthShot]:
    """shoot(a, b) of a linear residual in x = (a, 100 b): r_c = r_t + r_scale F_1 and
    v_r,c = vr_scale F_2 with F = SYNTH_JAC (x - SYNTH_ROOT_X). Every call is logged in
    x units; fails(x, n) (n the 1-based call number) True raises GuidanceFailure."""

    def shoot(a: float, b: float) -> _SynthShot:
        x = (a, LTG_B_SCALE_S * b)
        calls.append(x)
        if fails(x, len(calls)):
            raise GuidanceFailure("impact", "synthetic failure")
        d0, d1 = x[0] - SYNTH_ROOT_X[0], x[1] - SYNTH_ROOT_X[1]
        f1 = SYNTH_JAC[0][0] * d0 + SYNTH_JAC[0][1] * d1
        f2 = SYNTH_JAC[1][0] * d0 + SYNTH_JAC[1][1] * d1
        return _SynthShot(SYNTH_R_T_M + st.r_scale_m * f1, st.vr_scale_mps * f2, SYNTH_TAU_S)

    return shoot


def _synthetic_ladder() -> tuple[tuple[str, tuple[float, float]], ...]:
    return (("guess", (SYNTH_GUESS_X[0], SYNTH_GUESS_X[1] / LTG_B_SCALE_S)),)


def test_solve_ltg_backward_difference_on_a_failed_forward_shot() -> None:
    """A linear residual whose shots raise for a > a_0 + h/2: the forward-difference shot
    of the a column fails, so the column comes from the backward shot at a_0 - h (logged
    here), and with the exact Jacobian of a linear F one Newton step lands on the root:
    1 iteration, 5 shots (guess, failed forward, backward, forward in b, the step), and
    the root a = 0.7, b = x_2 / 100 = 2e-3 1/s (1e-9). A wrong sign in the backward
    column would send the step elsewhere and change the counts."""
    st = _ltg_settings()
    h = st.fd_step
    calls: list[tuple[float, float]] = []
    shoot = _synthetic_shoot(st, calls, lambda x, n: x[0] > SYNTH_GUESS_X[0] + 0.5 * h)
    sol = solve_ltg(shoot, SYNTH_R_T_M, st, _synthetic_ladder())
    assert sol.a == pytest.approx(SYNTH_ROOT_X[0], abs=1e-9)
    assert sol.b_per_s == pytest.approx(SYNTH_ROOT_X[1] / 100.0, abs=1e-11)
    assert (sol.iters, sol.shots, sol.rung) == (1, 5, "guess")
    assert calls[1] == pytest.approx((SYNTH_GUESS_X[0] + h, SYNTH_GUESS_X[1]), abs=1e-12)
    assert calls[2] == pytest.approx((SYNTH_GUESS_X[0] - h, SYNTH_GUESS_X[1]), abs=1e-12)
    assert calls[3] == pytest.approx((SYNTH_GUESS_X[0], SYNTH_GUESS_X[1] + h), abs=1e-12)
    assert abs(sol.shot.r_cut_m - SYNTH_R_T_M) < 1e-6 and abs(sol.shot.v_r_cut_mps) < 1e-9


def test_solve_ltg_halves_the_step_on_a_typed_failure() -> None:
    """The same linear residual with its first Newton trial (call 4) raising: the step is
    halved, so call 5 lies at the midpoint of the guess and the root (1e-9) and is
    accepted (||F|| halves); the next iteration's full step reaches the root: 2
    iterations, 8 shots, the root as before."""
    st = _ltg_settings()
    calls: list[tuple[float, float]] = []
    shoot = _synthetic_shoot(st, calls, lambda x, n: n == 4)
    sol = solve_ltg(shoot, SYNTH_R_T_M, st, _synthetic_ladder())
    mid = tuple(0.5 * (g + r) for g, r in zip(SYNTH_GUESS_X, SYNTH_ROOT_X, strict=True))
    assert calls[4] == pytest.approx(mid, abs=1e-9)
    assert (sol.iters, sol.shots) == (2, 8)
    assert sol.a == pytest.approx(SYNTH_ROOT_X[0], abs=1e-9)
    assert sol.b_per_s == pytest.approx(SYNTH_ROOT_X[1] / 100.0, abs=1e-11)


# ------------------------------------------------------------------- gate shooting


def _ltg_settings(*, final: bool = False) -> LtgSettings:
    return LtgSettings.from_config(LtgConfig(), final=final)


@pytest.fixture(scope="module")
def gate_vehicle(repo_root: Path) -> Vehicle:
    """The gate fork generic_f9_class_2d.yaml (payload 22.8 t)."""
    path = repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return VehicleConfig.model_validate(raw).to_vehicle()


def _planner(vehicle: Vehicle, settings: LtgSettings | None = None) -> PlanarPlanner:
    env = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), OMEGA_P, ambient_scalar)
    return PlanarPlanner(
        vehicle,
        {"stage1": IgnitionSpec(-2.0), "stage2": IgnitionSpec(0.0)},
        GuidanceSpec(50.0, 60.0, 60.0),
        env,
        "insertion",
        IntegratorSettings(rtol=RTOL, dense_output=False),
        target=TargetOrbit(R_TARGET_M),
        ltg=_ltg_settings() if settings is None else settings,
    )


@pytest.fixture(scope="module")
def gate(gate_vehicle: Vehicle) -> tuple[PlanarPlanner, Handover]:
    """The gate pad flown to stage-2 ignition at gamma* = 20 deg (delta solved)."""
    planner = _planner(gate_vehicle)
    kick = planner.to_kick(planner.start())
    sol = solve_delta_for_gamma(
        lambda d: planner.from_kick(d, kick),
        GAMMA_STAR_RAD,
        DeltaSolveSettings.from_config(SearchConfig()),
    )
    return planner, sol.handover


def _check_insertion(shot: Stage2Result, settings: LtgSettings) -> None:
    """E = E* (1e-9 rel), |r - r_t| < 1 m, |v_r| < 1e-3 m/s, e < 1e-6, direct root."""
    y = shot.y_cut
    r, v_r, v_t = (float(P2.get(y, n)) for n in ("r_m", "v_r_mps", "v_theta_mps"))
    energy = 0.5 * (v_r * v_r + v_t * v_t) - MU_EARTH_M3S2 / r
    assert energy == pytest.approx(-MU_EARTH_M3S2 / (2.0 * R_TARGET_M), rel=1e-9)
    assert abs(r - R_TARGET_M) < 1.0 and abs(v_r) < 1e-3
    assert orbit_elements(r, v_r, v_t, MU_EARTH_M3S2).e < 1e-6
    assert shot.ended_by == "cutoff"
    assert shot.b_per_s > 0.0
    lo, hi = settings.pitch_bounds_rad
    assert math.atan(shot.a) < hi and math.atan(shot.a - shot.b_per_s * shot.tau_cut_s) > lo


def _root_tolerance(
    shoot: Callable[[float, float], Stage2Result], a: float, b_per_s: float, st: LtgSettings
) -> tuple[float, float]:
    """(tol_a, tol_b [1/s]): how far apart two roots that both meet the acceptance box
    (|r_c - r_t| < accept_r_m, |v_r,c| < accept_vr_mps) can lie, 2 |J^-1| (accept_r,
    accept_vr) with J = d(r_c, v_r,c)/d(a, b) by forward differences at (a, b) (steps
    fd_step in a and fd_step/100 in b)."""
    h_a, h_b = st.fd_step, st.fd_step / LTG_B_SCALE_S
    base = shoot(a, b_per_s)
    da, db = shoot(a + h_a, b_per_s), shoot(a, b_per_s + h_b)
    jac = np.array(
        [
            [(da.r_cut_m - base.r_cut_m) / h_a, (db.r_cut_m - base.r_cut_m) / h_b],
            [(da.v_r_cut_mps - base.v_r_cut_mps) / h_a, (db.v_r_cut_mps - base.v_r_cut_mps) / h_b],
        ]
    )
    tol = 2.0 * np.abs(np.linalg.inv(jac)) @ np.array([st.accept_r_m, st.accept_vr_mps])
    return float(tol[0]), float(tol[1])


def test_ltg_ladder_and_physics_guess(gate: tuple[PlanarPlanner, Handover]) -> None:
    """The physics guess is a = tan(gamma_in + 5 deg), b = (a - tan(-1 deg))/tau_b with
    gamma_in = atan2(v_r, v_theta) at stage-2 ignition (inertial) and tau_b = m_p2 c2 /
    T2 (computed here from the stage); the ladder is warm, physics, steep (35 deg),
    shallow (x = (0.3, 0.3), b = 0.3/100)."""
    planner, ho = gate
    assert ho.y_ign2 is not None
    v_r, v_t = (float(P2.get(ho.y_ign2, n)) for n in ("v_r_mps", "v_theta_mps"))
    gamma_in = math.atan2(v_r, v_t)
    stage2 = planner.vehicle.stages[1]
    tau_b = stage2.propellant_mass_kg * stage2.c_mps / stage2.thrust_vac_total_N
    assert planner.tau_b2_s == pytest.approx(tau_b, rel=1e-14)
    a = math.tan(gamma_in + math.radians(5.0))
    b = (a - math.tan(math.radians(-1.0))) / tau_b
    assert ltg_physics_guess(gamma_in, tau_b, math.radians(5.0), math.radians(-1.0)) == (
        pytest.approx(a, rel=1e-14),
        pytest.approx(b, rel=1e-14),
    )
    ladder = ltg_guess_ladder(_ltg_settings(), ho.gamma_in_ign2_rad, tau_b, warm=(0.7, 0.002))
    assert [name for name, _ in ladder] == ["warm", "physics", "steep", "shallow"]
    steep = math.tan(math.radians(35.0))
    assert ladder[2][1] == pytest.approx((steep, (steep - math.tan(math.radians(-1.0))) / tau_b))
    assert ladder[3][1] == pytest.approx((0.3, 0.3 / LTG_B_SCALE_S))
    assert ltg_guess_ladder(_ltg_settings(), gamma_in, tau_b)[0][0] == "physics"


def test_shooting_converges_from_every_rung(gate: tuple[PlanarPlanner, Handover]) -> None:
    """From the physics and steep guesses, and warm from 2 % off the physics root, each
    rung alone converges to a direct root that inserts (E = E*, |r - r_t| < 1 m, |v_r| <
    1e-3 m/s, e < 1e-6), and the roots agree with the full ladder's within what the
    acceptance box allows (``_root_tolerance``; measured spread about 1e-7 in a and 3e-10
    1/s in b). ``solve_stage2`` with the full ladder returns the first rung
    (physics)."""
    planner, ho = gate
    st = _ltg_settings()

    def shoot(a: float, b: float) -> Stage2Result:
        return planner.stage2(ho, a, b, virtual_propellant=True)

    full = planner.solve_stage2(ho)
    assert full.rung == "physics"
    _check_insertion(full.shot, st)
    tol_a, tol_b = _root_tolerance(shoot, full.a, full.b_per_s, st)
    assert 0.0 < tol_a < 1e-4 and 0.0 < tol_b < 1e-6
    ladder = dict(ltg_guess_ladder(st, ho.gamma_in_ign2_rad, planner.tau_b2_s))
    guesses = {
        "warm": (full.a * 1.02, full.b_per_s * 0.98),
        "physics": ladder["physics"],
        "steep": ladder["steep"],
    }
    for rung, guess in guesses.items():
        sol = solve_ltg(shoot, R_TARGET_M, st, ((rung, guess),))
        assert sol.rung == rung
        _check_insertion(sol.shot, st)
        assert sol.a == pytest.approx(full.a, abs=tol_a), rung
        assert sol.b_per_s == pytest.approx(full.b_per_s, abs=tol_b), rung
        assert sol.shots >= sol.iters


def test_shooting_failures_are_typed(gate: tuple[PlanarPlanner, Handover]) -> None:
    """A diving guess (the shallow rung: tan p from 0.3 falling at 0.003 1/s) hits the
    ground in stage 2 (GuidanceFailure impact), so a ladder of that rung alone raises
    nonconverged naming it; one Newton iteration from the physics guess is not enough
    (nonconverged: nothing unconverged is returned); a pitch window whose low end (-1
    deg) excludes the converged root's final pitch (about -2 deg) gives not_direct_root
    and then nonconverged."""
    planner, ho = gate
    st = _ltg_settings()

    def shoot(a: float, b: float) -> Stage2Result:
        return planner.stage2(ho, a, b, virtual_propellant=True)

    with pytest.raises(GuidanceFailure) as info:
        shoot(0.3, 0.3 / LTG_B_SCALE_S)
    assert info.value.kind == "impact"
    with pytest.raises(GuidanceFailure) as info:
        solve_ltg(shoot, R_TARGET_M, st, (("shallow", (0.3, 0.003)),))
    assert info.value.kind == "nonconverged" and "impact" in str(info.value)
    physics = dict(ltg_guess_ladder(st, ho.gamma_in_ign2_rad, planner.tau_b2_s))["physics"]
    one = dataclasses.replace(st, max_iters=1)
    with pytest.raises(GuidanceFailure) as info:
        solve_ltg(shoot, R_TARGET_M, one, (("physics", physics),))
    assert info.value.kind == "nonconverged"
    narrow = dataclasses.replace(st, pitch_bounds_rad=(math.radians(-1.0), math.radians(75.0)))
    with pytest.raises(GuidanceFailure) as info:
        solve_ltg(shoot, R_TARGET_M, narrow, (("physics", physics),))
    assert info.value.kind == "nonconverged" and "not_direct_root" in str(info.value)


def test_direct_root_window() -> None:
    """is_direct_root: b > 0 and atan(a - b tau) inside the open pitch window at both
    ends of the burn."""
    window = (math.radians(-45.0), math.radians(75.0))
    assert is_direct_root(0.75, 0.002, 360.0, window)
    assert not is_direct_root(0.75, -0.002, 360.0, window)
    assert not is_direct_root(math.tan(math.radians(76.0)), 0.001, 10.0, window)
    assert not is_direct_root(0.0, 0.01, 200.0, window)  # ends at atan(-2) = -63 deg
    with pytest.raises(ValueError):
        dataclasses.replace(_ltg_settings(), pitch_bounds_rad=(0.5, 0.1))
    assert LtgSettings.from_config(LtgConfig(), final=True).fd_step == LtgConfig().fd_step_final
    grid = LtgSettings.from_config(LtgConfig(), final=False, grid=True)
    assert grid.max_rungs == LtgConfig().grid_max_rungs and grid.fd_step == 1e-4
    assert LTG_RUNGS == LTG_GUESS_RUNGS  # the solver's ladder is the one config validates


def test_the_only_high_gamma_root_is_indirect_by_rule(
    gate_vehicle: Vehicle, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At gamma* = 32 deg on the gate pad (22.8 t) the physics and steep rungs converge
    to one root with b < 0 (pitch rising over the burn), so the b > 0 part of the
    direct-root rule rejects it (not_direct_root for both, then nonconverged). With
    that part disabled (the pitch window kept) the same root inserts (E = E*, |r - r_t|
    < 1 m, |v_r| < 1e-3 m/s, e < 1e-6) with a positive residual (measured a = 0.0948, b
    = -2.86e-4 1/s, m_res 1,894.7 kg): past the b = 0 boundary (about 30.2 deg on the
    pad) the grid point is infeasible by the pre-registered rule, not by the physics
    (docs/physics.md, "LTG shooting")."""
    planner = _planner(gate_vehicle)
    kick = planner.to_kick(planner.start())
    ho = solve_delta_for_gamma(
        lambda d: planner.from_kick(d, kick),
        math.radians(32.0),
        DeltaSolveSettings.from_config(SearchConfig()),
    ).handover
    with pytest.raises(GuidanceFailure) as info:
        planner.solve_stage2(ho)
    assert info.value.kind == "nonconverged"
    for rung in ("physics", "steep"):
        assert f"{rung}: not_direct_root" in str(info.value)
    lo, hi = _ltg_settings().pitch_bounds_rad

    def window_only(a: float, b: float, tau: float, bounds: tuple[float, float]) -> bool:
        ends = (math.atan(a), math.atan(a - b * tau))
        return bounds[0] < min(ends) and max(ends) < bounds[1]

    monkeypatch.setattr(guidance, "is_direct_root", window_only)
    sol = planner.solve_stage2(ho)
    shot = sol.shot
    assert sol.b_per_s < 0.0 and shot.m_res_kg > 1_000.0
    assert lo < math.atan(sol.a) < math.atan(sol.a - sol.b_per_s * sol.tau_cut_s) < hi
    y = shot.y_cut
    r, v_r, v_t = (float(P2.get(y, n)) for n in ("r_m", "v_r_mps", "v_theta_mps"))
    energy = 0.5 * (v_r * v_r + v_t * v_t) - MU_EARTH_M3S2 / r
    assert energy == pytest.approx(-MU_EARTH_M3S2 / (2.0 * R_TARGET_M), rel=1e-9)
    assert abs(r - R_TARGET_M) < 1.0 and abs(v_r) < 1e-3
    assert orbit_elements(r, v_r, v_t, MU_EARTH_M3S2).e < 1e-6


@pytest.mark.slow
def test_random_guesses_reach_the_same_root_or_fail_typed(
    gate: tuple[PlanarPlanner, Handover],
) -> None:
    """40 seeded guesses a in [-1, 3], 100 b in [-1, 2]: each single-rung solve either
    converges to the physics rung's direct root (an inserting shot, and (a, b) within
    the acceptance box's tolerance ``_root_tolerance``) or raises GuidanceFailure; no
    other exception and no other root. Measured: 13 converge
    (4 to 5 iterations), 27 dive into the ground on their first shot (impact, so the
    rung ends nonconverged); the plan's prototype had 18 of 40."""
    planner, ho = gate
    st = _ltg_settings()
    ref = planner.solve_stage2(ho)

    def shoot(a: float, b: float) -> Stage2Result:
        return planner.stage2(ho, a, b, virtual_propellant=True)

    tol_a, tol_b = _root_tolerance(shoot, ref.a, ref.b_per_s, st)
    rng = np.random.default_rng(22)
    converged = 0
    for a, x2 in zip(rng.uniform(-1.0, 3.0, 40), rng.uniform(-1.0, 2.0, 40), strict=True):
        try:
            sol = solve_ltg(shoot, R_TARGET_M, st, (("random", (float(a), x2 / LTG_B_SCALE_S)),))
        except GuidanceFailure:
            continue
        converged += 1
        _check_insertion(sol.shot, st)
        assert sol.a == pytest.approx(ref.a, abs=tol_a)
        assert sol.b_per_s == pytest.approx(ref.b_per_s, abs=tol_b)
    assert converged >= 10


@pytest.mark.parametrize(
    "module", ["guidance.py", "orbit.py", "losses.py", "metrics_planar.py", "phases/planar.py"]
)
def test_step22_modules_have_docstrings(repo_root: Path, module: str) -> None:
    """Every public function, class and method of the modules build step 22 extends has
    a docstring (tests/test_scaffold.py does not list them all yet)."""
    path = repo_root / "src" / "launchsim" / module
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assert ast.get_docstring(tree)
    missing = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.ClassDef) and not node.name.startswith("_"):
            if ast.get_docstring(node) is None:
                missing.append(node.name)
            if isinstance(node, ast.ClassDef):
                missing += [
                    f"{node.name}.{m.name}"
                    for m in node.body
                    if isinstance(m, ast.FunctionDef)
                    and not m.name.startswith("_")
                    and ast.get_docstring(m) is None
                ]
    assert not missing, missing
