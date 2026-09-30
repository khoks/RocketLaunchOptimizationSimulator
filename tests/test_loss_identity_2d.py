"""CLAUDE.md's loss budget over a full planar ascent (docs/physics.md, "2-D loss
identity"): from the flight start to the end of the run,

    |v_rel,f| - |v_rel,0| = dv_vac - gravity - drag - steering - back_pressure

with every term from ``losses.loss_budget`` over the run's ascent phases (the J_*
quadratures, J_drag included) and |v_rel| from the planar model, asserted below
checks.identity_tol_mps = 1e-5 m/s (CLAUDE.md asks 0.01 m/s).

Runs: the gate fork (generic_f9_class_2d.yaml) at 28.5 deg east with rotation, ICAO,
Braeunig drag, v_k 50 m/s, gamma* = 20 deg (delta solved), the LTG pair solved, then a
recorded run at rtol 1e-10 with dense output on: the pad to insertion (hold, rise, kick,
turn, the 11 s staging coast, the fairing drop, LTG); silo_cold (3 g, 100 m, lit 0.5 s
after release, 2 s ramp); silo_hot_full (lit 2 s before the push, full thrust on the
track); a clamped-thrust engine (the silo lit at release with a 10 s ramp, so the
delivered thrust max(0, T_vac - p A_e) is clamped at zero for the first 0.75 s of free
flight); and silo_failed (stage 1 never lights: coast through the apex to impact).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
import yaml

from launchsim.assist import build_assist
from launchsim.atmosphere import ambient_scalar
from launchsim.config import ConstantAccelConfig, LtgConfig, SearchConfig, VehicleConfig
from launchsim.constants import MU_EARTH_M3S2, OMEGA_EARTH_RADS, P_SEA_LEVEL_PA, R_EARTH_M
from launchsim.dynamics import PLANAR_LAYOUT, InverseSquareGravity, PlanarDynamics2D
from launchsim.guidance import (
    DeltaSolveSettings,
    GuidanceSpec,
    LtgSettings,
    solve_delta_for_gamma,
)
from launchsim.losses import LossBudget, loss_budget, pointwise_dVdt
from launchsim.orbit import TargetOrbit
from launchsim.phases import IgnitionSpec, IntegratorSettings, RunTrace
from launchsim.phases.planar import PlanarEnvironment, PlanarPlanner
from launchsim.vehicle import Startup, Vehicle

P2 = PLANAR_LAYOUT
LAT_RAD = math.radians(28.5)
OMEGA_P = OMEGA_EARTH_RADS * math.cos(LAT_RAD)  # azimuth 90 deg
R_TARGET_M = R_EARTH_M + 200.0e3
GAMMA_STAR_RAD = math.radians(20.0)
RTOL = 1e-10
IDENTITY_TOL_MPS = 1e-5
"""checks.identity_tol_mps of the shipped experiments."""
LONG_RAMP_S = 10.0
"""Ramp [s] of the clamped-thrust case: T_vac(t) < p0 A_e for t < t_r p0 A_e / T_full."""

CASES = {
    "pad": (IgnitionSpec(-2.0), False, "insertion"),
    "silo_cold": (IgnitionSpec(0.5), True, "insertion"),
    "silo_hot_full": (IgnitionSpec(-2.0, reference="push_start"), True, "insertion"),
    "clamped": (
        IgnitionSpec(0.0, startup=Startup("ramp", t_ramp_s=LONG_RAMP_S)),
        True,
        "insertion",
    ),
    "silo_failed": (IgnitionSpec(0.0, fails=True), True, "impact"),
}


@pytest.fixture(scope="module")
def gate_vehicle(repo_root: Path) -> Vehicle:
    """The gate fork generic_f9_class_2d.yaml (payload 22.8 t)."""
    path = repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return VehicleConfig.model_validate(raw).to_vehicle()


def _planner(vehicle: Vehicle, ign1: IgnitionSpec, end: str, dense: bool) -> PlanarPlanner:
    env = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), OMEGA_P, ambient_scalar)
    return PlanarPlanner(
        vehicle,
        {"stage1": ign1, "stage2": IgnitionSpec(0.0)},
        GuidanceSpec(50.0, 60.0, 60.0),
        env,
        end,
        IntegratorSettings(rtol=RTOL, dense_output=dense),
        target=TargetOrbit(R_TARGET_M),
        ltg=LtgSettings.from_config(LtgConfig(), final=False),
    )


def _fly(vehicle: Vehicle, case: str) -> tuple[RunTrace, PlanarPlanner]:
    """The recorded run of a case (search-mode delta and LTG solves first)."""
    ign1, on_silo, end = CASES[case]
    assist = track = None
    if on_silo:
        cfg = ConstantAccelConfig(
            model="constant_accel",
            net_accel_g=3.0,
            stroke_m=100.0,
            brake_decel_g=5.0,
            drive_efficiency=0.5,
        )
        g_ref = MU_EARTH_M3S2 / R_EARTH_M**2 - OMEGA_P**2 * R_EARTH_M
        assist, track = build_assist(cfg, g_ref)
    recorder = _planner(vehicle, ign1, end, dense=True)
    if ign1.fails:
        return recorder.run(None, assist, track), recorder
    search = _planner(vehicle, ign1, end, dense=False)
    kick = search.to_kick(search.start(assist, track))
    sol = solve_delta_for_gamma(
        lambda d: search.from_kick(d, kick),
        GAMMA_STAR_RAD,
        DeltaSolveSettings.from_config(SearchConfig()),
    )
    ltg = search.solve_stage2(sol.handover)
    return recorder.run(sol.delta_rad, assist, track, ltg=(ltg.a, ltg.b_per_s)), recorder


Flown = Callable[[str], RunTrace]


@pytest.fixture(scope="module")
def flown(gate_vehicle: Vehicle) -> Flown:
    """flown(case): the case's recorded trace, flown once per module (the traces are
    never mutated) so the tests that share a case do not re-fly it."""
    cache: dict[str, RunTrace] = {}

    def get(case: str) -> RunTrace:
        if case not in cache:
            cache[case] = _fly(gate_vehicle, case)[0]
        return cache[case]

    return get


def _budget(trace: RunTrace) -> LossBudget:
    model = PlanarDynamics2D(OMEGA_P, R_EARTH_M)
    return loss_budget(trace.ascent_phases(), P2, speed=model.speed)


@pytest.mark.parametrize("case", list(CASES))
def test_full_ascent_loss_budget_closes(flown: Flown, case: str) -> None:
    """V_f - V_0 = dv_vac - gravity - drag - steering - back_pressure over the whole
    run within 1e-5 m/s (measured about 1e-8), with V = |v_rel| computed here from the
    end states; the inserted runs end at V_rel = v_c - omega_p r_t (1e-2 m/s) with every
    loss term positive; the failed silo books no thrust terms and regains on the fall
    what it lost on the rise."""
    trace = flown(case)
    budget = _budget(trace)
    assert abs(budget.residual_mps()) < IDENTITY_TOL_MPS, budget
    phases = trace.ascent_phases()
    y0, y1 = phases[0].y[:, 0], phases[-1].y_end

    def v_rel(y: object) -> float:
        r, v_r, v_t = (float(P2.get(y, n)) for n in ("r_m", "v_r_mps", "v_theta_mps"))  # type: ignore[arg-type]
        return math.hypot(v_r, v_t - OMEGA_P * r)

    assert budget.speed_start == pytest.approx(v_rel(y0), rel=1e-15)
    assert budget.speed_end == pytest.approx(v_rel(y1), rel=1e-15)
    if case == "silo_failed":
        assert trace.status == "impact"
        assert budget.dv_vac == 0.0 and budget.steering == 0.0 and budget.back_pressure == 0.0
        assert budget.drag > 0.0 and abs(budget.gravity) < budget.drag + 1.0
        return
    assert trace.status == "inserted"
    v_c = math.sqrt(MU_EARTH_M3S2 / R_TARGET_M)
    assert budget.speed_end == pytest.approx(v_c - OMEGA_P * R_TARGET_M, abs=1e-2)
    assert min(budget.gravity, budget.drag, budget.steering, budget.back_pressure) > 0.0
    kinds = {p.spec.kind for p in phases}
    assert {"KICK", "GRAVITY_TURN", "COAST_STAGING", "LTG_BURN"} <= kinds
    assert "fairing" in {e.name for e in trace.events}


def test_clamped_thrust_books_back_pressure(gate_vehicle: Vehicle, flown: Flown) -> None:
    """The silo lit at release with a 10 s ramp: while T_vac(t) = T_full t/t_r is below
    p A_e (for t < t_r p A_e / T_full = 0.75 s at the mouth's pressure, computed here),
    the delivered thrust is zero, so over the first 0.5 s of flight the back-pressure
    quadrature grows exactly as J_vac (1e-12 relative) with no speed gained from
    thrust; the identity closes over the whole run (previous test)."""
    trace = flown("clamped")
    stage = gate_vehicle.stages[0]
    t_clamp = LONG_RAMP_S * P_SEA_LEVEL_PA * stage.exit_area_total_m2 / stage.thrust_vac_total_N
    assert 0.7 < t_clamp < 0.8
    first = trace.ascent_phases()[0]
    assert first.dense is not None and first.spec.t0 == trace.t_release_s
    y = first.dense(trace.t_release_s + 0.5)
    j_vac, j_bp = float(P2.get(y, "J_vac_mps")), float(P2.get(y, "J_bp_mps"))
    assert j_vac > 0.0 and j_bp == pytest.approx(j_vac, rel=1e-12)
    assert abs(_budget(trace).residual_mps()) < IDENTITY_TOL_MPS


FD_STEP_S = 1e-2
"""Central-difference step [s] of V = |v_rel| along the dense output."""
POINTWISE_SAMPLES = 20
"""Interior samples per ascent phase of the pointwise test."""


def _v_rel(y: np.ndarray) -> float:
    r, v_r, v_t = (float(P2.get(y, n)) for n in ("r_m", "v_r_mps", "v_theta_mps"))
    return math.hypot(v_r, v_t - OMEGA_P * r)


def test_pointwise_dVdt_along_the_recorded_pad(flown: Flown) -> None:
    """``losses.pointwise_dVdt`` on the recorded pad run (rotation, ICAO drag, the
    radial rise, the kick, the gravity turn, the staging coast and LTG): at 20 interior
    dense samples of every ascent phase longer than 1 s, lhs = rhs within 1e-12 x scale
    (the identity's rate), and lhs equals a central difference of V = |v_rel| computed
    here from the dense output (step 1e-2 s) within 1e-5 x scale. At the flight start V
    is 0 exactly, where the fallback T e_r/m - g_eff - D/m equals rhs within 1e-12 x
    scale and the ordinary branch's value at w = 1e-6 m/s within 1e-9 relative
    (measured: 4e-16 and 5e-8 of scale along the run)."""
    trace = flown("pad")
    checked = set()
    for res in trace.ascent_phases():
        if res.span_s <= 1.0:
            continue
        assert res.dense is not None
        params = res.spec.params
        lo, hi = res.spec.t0 + FD_STEP_S, res.t_end - FD_STEP_S
        for t in np.linspace(lo, hi, POINTWISE_SAMPLES):
            y = np.asarray(res.dense(t), dtype=float)
            lhs, rhs, scale = pointwise_dVdt(float(t), y, params)
            assert abs(lhs - rhs) <= 1e-12 * scale, (res.spec.kind, t)
            v_plus = _v_rel(np.asarray(res.dense(t + FD_STEP_S), dtype=float))
            v_minus = _v_rel(np.asarray(res.dense(t - FD_STEP_S), dtype=float))
            fd = (v_plus - v_minus) / (2.0 * FD_STEP_S)
            assert abs(lhs - fd) <= 1e-5 * scale, (res.spec.kind, t, lhs, fd)
        checked.add(res.spec.kind)
    assert {"VERTICAL_RISE", "KICK", "GRAVITY_TURN", "COAST_STAGING", "LTG_BURN"} <= checked
    first = trace.ascent_phases()[0]
    y0 = np.asarray(first.y[:, 0], dtype=float)
    assert _v_rel(y0) == 0.0
    lhs0, rhs0, scale0 = pointwise_dVdt(first.spec.t0, y0, first.spec.params)
    assert abs(lhs0 - rhs0) <= 1e-12 * scale0
    y1 = y0.copy()
    y1[P2.index("v_r_mps")] = 1e-6
    lhs1, _rhs1, _scale1 = pointwise_dVdt(first.spec.t0, y1, first.spec.params)
    assert lhs0 == pytest.approx(lhs1, rel=1e-9)
