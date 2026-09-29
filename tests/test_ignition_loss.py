"""Speed lost by lighting the engines late or slowly after release, constant gravity.

Reference: instant full thrust at release (step at t = 0) from the same state (v0 = 77
m/s, the README silo exit speed; g = g0 injected). Every case burns the same propellant,
so J_vac = c ln(m0/mf) is identical and, with v > 0 throughout and constant g, the
difference at burnout is g times the extra time the burn takes:

- delay t_d then a linear ramp t_r: the ramp burns mdot t_r/2, so burnout is at
  t_d + t_r/2 + t_b and the loss is g (t_d + t_r/2), exactly;
- delay t_d then a first-order lag tau: the burn after ignition ends at s_e = tau u with
  u - 1 + e^(-u) = t_b/tau, i.e. u = 1 + t_b/tau + W0(-e^(-1 - t_b/tau)) (Lambert W,
  principal branch), and the loss is g [t_d + tau (1 - e^(-u))]; g (t_d + tau) is its
  long-burn asymptote. A short toy burn (t_b = 5 s, tau = 1 s) makes the correction
  tau e^(-u) g = 0.024 m/s resolvable; the F9 burn (t_b = 147 s) does not.

``losses.ignition_loss_analytic_mps`` must reproduce every integrated difference.
"""

from __future__ import annotations

import dataclasses
import math
from typing import TYPE_CHECKING

import pytest
from scipy.special import lambertw

from launchsim import sim
from launchsim.constants import G0_MPS2
from launchsim.dynamics import ConstantGravity
from launchsim.losses import ignition_loss_analytic_mps
from launchsim.phases import AscentStart, IgnitionSpec
from launchsim.vehicle import Stage, Startup, Vehicle

if TYPE_CHECKING:
    from conftest import RunVertical

G = G0_MPS2
V0 = 77.0
ABS = 1e-5  # m/s


def _stage1(vehicle: Vehicle) -> tuple[float, float, float, float]:
    """(c, mdot, m0, t_b) of the first stage from the fixture's masses."""
    stage = vehicle.stages[0]
    c = G0_MPS2 * stage.engine.isp_vac_s
    mdot = stage.n_engines * stage.engine.thrust_vac_N / c
    return c, mdot, vehicle.liftoff_mass_kg(), stage.propellant_mass_kg / mdot


def _burnout(vehicle: Vehicle, spec: IgnitionSpec, run_vertical: RunVertical) -> sim.Result:
    result = run_vertical(
        vehicle,
        {vehicle.stage_names[0]: spec},
        ConstantGravity(G),
        G,
        start=AscentStart(0.0, V0),
        end="stage1_burnout",
    )
    assert result.status == "nominal" and result.flags == []
    assert (result.timeseries["v_mps"] > 0.0).all()
    return result


def _reference(vehicle: Vehicle, run_vertical: RunVertical) -> sim.Result:
    return _burnout(vehicle, IgnitionSpec(0.0, startup=Startup("step")), run_vertical)


@pytest.mark.parametrize(("t_d", "t_r"), [(0.0, 1.0), (0.5, 2.0), (1.0, 3.0)])
def test_ramp_loss_is_g_times_delay_plus_half_ramp(
    t_d: float, t_r: float, f9_vehicle: Vehicle, run_vertical: RunVertical
) -> None:
    c, mdot, m0, t_b = _stage1(f9_vehicle)
    startup = Startup("ramp", t_ramp_s=t_r)
    ref = _reference(f9_vehicle, run_vertical)
    delayed = _burnout(f9_vehicle, IgnitionSpec(t_d, startup=startup), run_vertical)
    expected = G * (t_d + 0.5 * t_r)

    assert (
        abs(
            ref.metrics["stage1_burnout_speed_mps"]
            - delayed.metrics["stage1_burnout_speed_mps"]
            - expected
        )
        < ABS
    )
    assert math.isclose(delayed.metrics["dv_vac_mps"], ref.metrics["dv_vac_mps"], rel_tol=1e-10)
    assert math.isclose(
        delayed.metrics["dv_vac_mps"], c * math.log(m0 / (m0 - mdot * t_b)), rel_tol=1e-9
    )
    assert math.isclose(delayed.metrics["stage1_burnout_t_s"], t_d + 0.5 * t_r + t_b, rel_tol=1e-9)
    assert math.isclose(ref.metrics["stage1_burnout_t_s"], t_b, rel_tol=1e-9)
    # The whole difference sits in the gravity-duration term (g_ref = g: no altitude part).
    assert (
        abs(delayed.metrics["gravity_loss_mps"] - ref.metrics["gravity_loss_mps"] - expected) < ABS
    )
    assert abs(delayed.metrics["gravity_loss_alt_mps"]) < 1e-9
    assert abs(ignition_loss_analytic_mps(G, t_d, startup, c, mdot, m0) - expected) < 1e-12
    assert abs(delayed.metrics["identity_residual_mps"]) < 1e-6
    # Phase bookkeeping: coast to ignition (when delayed), ramp sub-phase, full burn.
    kinds = [p.spec.kind for p in delayed.phases]
    assert kinds == (["COAST_PRE_IGN"] if t_d > 0.0 else []) + ["BURN", "BURN"]
    assert delayed.phases[-2].t_end == t_d + t_r


def _lag_loss(t_d: float, tau: float, t_b: float) -> float:
    u = 1.0 + t_b / tau + lambertw(-math.exp(-1.0 - t_b / tau), k=0).real
    assert abs(u - 1.0 + math.exp(-u) - t_b / tau) < 1e-12  # u solves the burnout equation
    return G * (t_d + tau * (1.0 - math.exp(-u)))


@pytest.mark.parametrize("t_d", [0.0, 0.5])
def test_lag_loss_on_a_short_toy_burn_resolves_the_lambert_correction(
    t_d: float, toy_stage: Stage, run_vertical: RunVertical
) -> None:
    tau = 1.0
    stage = dataclasses.replace(toy_stage, propellant_mass_kg=25.0)  # 5 s at 5 kg/s
    vehicle = Vehicle(stages=(stage,))
    c, mdot, m0, t_b = _stage1(vehicle)
    assert math.isclose(t_b, 5.0, rel_tol=1e-12)
    startup = Startup("lag", tau_s=tau)
    ref = _reference(vehicle, run_vertical)
    lag = _burnout(vehicle, IgnitionSpec(t_d, startup=startup), run_vertical)
    expected = _lag_loss(t_d, tau, t_b)
    asymptote = G * (t_d + tau)
    assert asymptote - expected > 0.02  # the correction is resolvable here

    diff = ref.metrics["stage1_burnout_speed_mps"] - lag.metrics["stage1_burnout_speed_mps"]
    assert abs(diff - expected) < ABS
    assert abs(diff - asymptote) > 0.01
    assert math.isclose(lag.metrics["dv_vac_mps"], ref.metrics["dv_vac_mps"], rel_tol=1e-10)
    assert (
        abs(ignition_loss_analytic_mps(G, t_d, startup, c, mdot, m0, t_burn_s=t_b) - expected)
        < 1e-9
    )
    assert abs(ignition_loss_analytic_mps(G, t_d, startup, c, mdot, m0) - asymptote) < 1e-12
    assert abs(lag.metrics["identity_residual_mps"]) < 1e-6


def test_lag_loss_on_the_f9_burn(f9_vehicle: Vehicle, run_vertical: RunVertical) -> None:
    t_d, tau = 0.5, 1.0
    c, mdot, m0, t_b = _stage1(f9_vehicle)
    startup = Startup("lag", tau_s=tau)
    ref = _reference(f9_vehicle, run_vertical)
    lag = _burnout(f9_vehicle, IgnitionSpec(t_d, startup=startup), run_vertical)
    expected = _lag_loss(t_d, tau, t_b)
    diff = ref.metrics["stage1_burnout_speed_mps"] - lag.metrics["stage1_burnout_speed_mps"]
    assert abs(diff - expected) < ABS
    assert abs(expected - G * (t_d + tau)) < 1e-9  # a 147 s burn: the asymptote is exact
    assert math.isclose(lag.metrics["dv_vac_mps"], ref.metrics["dv_vac_mps"], rel_tol=1e-10)
    assert (
        abs(ignition_loss_analytic_mps(G, t_d, startup, c, mdot, m0, t_burn_s=t_b) - expected) < ABS
    )
    assert abs(ignition_loss_analytic_mps(G, t_d, startup, c, mdot, m0) - diff) < ABS
    assert abs(lag.metrics["identity_residual_mps"]) < 1e-6


def test_analytic_loss_for_an_engine_lit_before_release(f9_vehicle: Vehicle) -> None:
    """The straddle form (lit on the track; integrated in build step 7): Phi_pre full-
    thrust seconds burned before release trade delta-v c ln(m0/(m0 - mdot Phi_pre)) for
    the gravity g Phi_pre they would have cost in flight, plus g D_post for the part of
    the ramp still missing after release: t_ign = -1.5 s, t_r = 2 s gives Phi_pre =
    1.5^2/4 = 0.5625 s and D_post = 0.5^2/4 = 0.0625 s."""
    c, mdot, m0, _t_b = _stage1(f9_vehicle)
    startup = Startup("ramp", t_ramp_s=2.0)
    phi_pre, d_post = 0.5625, 0.0625
    expected = c * math.log(m0 / (m0 - mdot * phi_pre)) - G * phi_pre + G * d_post
    assert abs(ignition_loss_analytic_mps(G, -1.5, startup, c, mdot, m0) - expected) < 1e-12
    # Lit a whole ramp before release: Phi_pre = -t_ign - t_r/2, nothing missing after.
    expected_full = c * math.log(m0 / (m0 - mdot * 1.0)) - G * 1.0
    assert abs(ignition_loss_analytic_mps(G, -2.0, startup, c, mdot, m0) - expected_full) < 1e-12
    # Burning on the pad wastes the delta-v of that propellant (T/m0 per second) against
    # the gravity it saves (g per second): the 'hold-down credit' an unphysical instant
    # start enjoys over the held-down pad baseline. ln(m0/(m0 - x)) lies between x/m0 and
    # x/(m0 - x), so the credit is bracketed by T/m0 - g and T/(m0 - mdot) - g (15.16 and
    # 15.24 m/s^2 of thrust acceleration against 9.81 m/s^2), and it is the 5.39 m/s that
    # docs/physics.md quotes as the g0-injected test figure.
    thrust = c * mdot
    assert thrust / m0 - G < expected_full < thrust / (m0 - mdot) - G
    assert abs(expected_full - 5.39) < 5e-3
