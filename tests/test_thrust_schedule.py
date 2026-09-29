"""Thrust startup shapes, the closed-form propellant burned, the post-release startup
deficit, and the ambient-pressure clamp. Expected values come from the formulas in
docs/physics.md written out here, and from numerical quadrature of the schedule."""

from __future__ import annotations

import math

import pytest
from scipy.integrate import quad

from launchsim.vehicle import (
    Stage,
    Startup,
    ThrustSchedule,
    propellant_burned_kg,
    startup_deficit_s,
    thrust_fraction,
)

T_RAMP = 2.0
TAU = 1.5


def test_thrust_fraction_shapes() -> None:
    step = Startup("step")
    assert thrust_fraction(step, -1e-9) == 0.0
    assert thrust_fraction(step, 0.0) == 1.0
    ramp = Startup("ramp", t_ramp_s=T_RAMP)
    assert thrust_fraction(ramp, -0.1) == 0.0
    assert math.isclose(thrust_fraction(ramp, T_RAMP / 2), 0.5, rel_tol=1e-12)
    assert thrust_fraction(ramp, T_RAMP) == 1.0
    assert thrust_fraction(ramp, 10 * T_RAMP) == 1.0
    lag = Startup("lag", tau_s=TAU)
    assert thrust_fraction(lag, -0.1) == 0.0
    assert thrust_fraction(lag, 0.0) == 0.0
    assert math.isclose(thrust_fraction(lag, TAU), 1.0 - math.exp(-1.0), rel_tol=1e-12)


def test_zero_duration_is_a_step() -> None:
    for startup in (Startup("ramp", t_ramp_s=0.0), Startup("lag", tau_s=0.0)):
        assert startup.effective_kind == "step"
        assert thrust_fraction(startup, 0.0) == 1.0
        assert thrust_fraction(startup, -1.0) == 0.0
        assert startup_deficit_s(startup, 0.7) == 0.7
        assert startup_deficit_s(startup, -0.7) == 0.0
    with pytest.raises(ValueError):
        Startup("ramp", t_ramp_s=-1.0)
    with pytest.raises(ValueError):
        Startup("bang")  # type: ignore[arg-type]


def _schedule(
    toy_stage: Stage, startup: Startup, t_ign: float, fails: bool = False
) -> ThrustSchedule:
    return toy_stage.schedule(t_ign, startup=startup, fails=fails)


def test_propellant_burned_closed_forms(toy_stage: Stage) -> None:
    mdot = toy_stage.mdot_full_kgps
    assert math.isclose(mdot, 5.0, rel_tol=1e-12)
    t_ign = 1.0
    step = _schedule(toy_stage, Startup("step"), t_ign)
    assert propellant_burned_kg(step, 0.5) == 0.0
    assert math.isclose(propellant_burned_kg(step, t_ign + 7.0), mdot * 7.0, rel_tol=1e-12)
    ramp = _schedule(toy_stage, Startup("ramp", t_ramp_s=T_RAMP), t_ign)
    assert math.isclose(
        propellant_burned_kg(ramp, t_ign + T_RAMP), mdot * T_RAMP / 2, rel_tol=1e-12
    )
    assert math.isclose(
        propellant_burned_kg(ramp, t_ign + T_RAMP / 2), mdot * T_RAMP / 8, rel_tol=1e-12
    )
    assert math.isclose(
        propellant_burned_kg(ramp, t_ign + 9.0), mdot * (9.0 - T_RAMP / 2), rel_tol=1e-12
    )
    lag = _schedule(toy_stage, Startup("lag", tau_s=TAU), t_ign)
    for dt in (0.3, TAU, 9.0):
        expect = mdot * (dt - TAU * (1.0 - math.exp(-dt / TAU)))
        assert math.isclose(propellant_burned_kg(lag, t_ign + dt), expect, rel_tol=1e-12)
    failed = _schedule(toy_stage, Startup("step"), t_ign, fails=True)
    assert propellant_burned_kg(failed, 100.0) == 0.0
    assert failed.thrust_vac_N(100.0) == 0.0 and failed.kink_times() == ()


def test_lag_forms_are_exact_just_after_ignition(toy_stage: Stage) -> None:
    """No cancellation at small dt: burned mass is never negative and follows the series
    mdot dt^2 / (2 tau); the thrust fraction follows dt / tau."""
    lag = Startup("lag", tau_s=TAU)
    sched = _schedule(toy_stage, lag, 0.0)
    mdot = toy_stage.mdot_full_kgps
    assert propellant_burned_kg(sched, 5e-324) >= 0.0  # denormal dt: clamped, never negative
    for dt in (1e-15, 1e-12, 1e-9, 1e-6, 1e-3):
        assert propellant_burned_kg(sched, dt) > 0.0
        assert thrust_fraction(lag, dt) > 0.0
    for dt in (1e-9, 1e-6, 1e-3):  # series to O(x^4): tau (x^2/2 - x^3/6), f = x - x^2/2 + x^3/6
        x = dt / TAU
        burned = propellant_burned_kg(sched, dt)
        assert math.isclose(burned, mdot * TAU * (x * x / 2.0 - x**3 / 6.0), rel_tol=1e-6)
        assert math.isclose(thrust_fraction(lag, dt), x - x * x / 2.0 + x**3 / 6.0, rel_tol=1e-9)


@pytest.mark.parametrize(
    "startup",
    [Startup("step"), Startup("ramp", t_ramp_s=T_RAMP), Startup("lag", tau_s=TAU)],
)
def test_integrated_mass_flow_matches_closed_form(toy_stage: Stage, startup: Startup) -> None:
    t_ign = -0.75
    sched = _schedule(toy_stage, startup, t_ign)
    kinks = list(sched.kink_times())
    assert kinks[0] == t_ign
    if startup.kind == "ramp":
        assert kinks == [t_ign, t_ign + T_RAMP]
    for t_end in (0.4, 3.0, 12.0):
        pts = [k for k in kinks if -5.0 < k < t_end]
        integral, err = quad(
            sched.mass_flow_kgps, -5.0, t_end, points=pts or None, epsabs=0, epsrel=1e-12, limit=200
        )
        assert math.isclose(integral, propellant_burned_kg(sched, t_end), rel_tol=1e-9), err


def test_startup_deficit_formulas() -> None:
    ramp = Startup("ramp", t_ramp_s=T_RAMP)
    assert math.isclose(startup_deficit_s(ramp, 0.5), 0.5 + T_RAMP / 2, rel_tol=1e-12)
    t_ign = -0.5
    assert math.isclose(
        startup_deficit_s(ramp, t_ign), (T_RAMP + t_ign) ** 2 / (2 * T_RAMP), rel_tol=1e-12
    )
    assert startup_deficit_s(ramp, -T_RAMP) == 0.0
    assert startup_deficit_s(ramp, -5.0) == 0.0
    lag = Startup("lag", tau_s=TAU)
    assert math.isclose(startup_deficit_s(lag, 0.5), 0.5 + TAU, rel_tol=1e-12)
    assert math.isclose(startup_deficit_s(lag, -0.5), TAU * math.exp(-0.5 / TAU), rel_tol=1e-12)
    assert startup_deficit_s(Startup("step"), 0.3) == 0.3
    assert startup_deficit_s(Startup("step"), -0.3) == 0.0


@pytest.mark.parametrize("t_ign", [-3.0, -1.2, 0.0, 0.8])
@pytest.mark.parametrize(
    "startup", [Startup("ramp", t_ramp_s=T_RAMP), Startup("lag", tau_s=TAU), Startup("step")]
)
def test_startup_deficit_is_the_post_release_integral(startup: Startup, t_ign: float) -> None:
    horizon = 60.0 * TAU  # long enough that a lag's tail is below 1e-12 relative
    pts = [p for p in (t_ign, t_ign + T_RAMP) if 0.0 < p < horizon]
    integral, _ = quad(
        lambda t: 1.0 - thrust_fraction(startup, t - t_ign),
        0.0,
        horizon,
        points=pts or None,
        epsabs=1e-13,
        epsrel=1e-12,
        limit=200,
    )
    assert math.isclose(integral, startup_deficit_s(startup, t_ign), rel_tol=1e-9, abs_tol=1e-12)


def test_schedule_thrust_and_back_pressure(toy_stage: Stage) -> None:
    sched = ThrustSchedule(
        thrust_vac_total_N=15_000.0,
        c_mps=3000.0,
        exit_area_total_m2=0.1,
        t_ign_abs_s=2.0,
        startup=Startup("ramp", t_ramp_s=T_RAMP),
    )
    assert sched.thrust_vac_N(1.0) == 0.0
    assert math.isclose(sched.thrust_vac_N(3.0), 7500.0, rel_tol=1e-12)
    assert math.isclose(sched.mass_flow_kgps(3.0), 2.5, rel_tol=1e-12)
    assert math.isclose(sched.thrust_N(4.0, 0.0), 15_000.0, rel_tol=1e-12)
    assert math.isclose(sched.thrust_N(4.0, 101_325.0), 15_000.0 - 10_132.5, rel_tol=1e-12)
    assert sched.thrust_N(4.0, 1e6) == 0.0  # clamped, never negative
    assert sched.mass_flow_kgps(4.0) == 5.0  # mass flow follows T_vac, not the clamped thrust
    stage_sched = toy_stage.schedule(0.0)
    assert stage_sched.startup == toy_stage.startup and stage_sched.kink_times() == (0.0,)
