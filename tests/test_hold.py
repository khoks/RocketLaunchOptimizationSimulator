"""Hold-down and liftoff on the pad, through ``sim.run`` (mu/r^2, g_eff = mu/R_E^2).

- Lit at t = -2 s with the vehicle's 2 s ramp: the ramp burns mdot t_r/2 = mdot * 1 s
  while clamped, the state at release is z = v = 0, t_release = 0, the hold lasts 2 s.
- Lit at t = 0 with the ramp: T(0) = 0 < m g_eff, so the hold-down extends until the
  thrust equals the weight, the root t* of

      T_full t / t_r = (m0 - mdot t^2 / (2 t_r)) g_eff,

  a quadratic solved here; the extension is recorded as an assumption, and the
  propellant burned while clamped past t = 0 (1,122 kg, 6.3 m/s of delta-v) is
  reported as burned before flight: dv_vac + dv_vac_equiv_before_flight = c ln(m0/m_dry).
- A step lit at t = 0.5 s from rest: the engine lights at the kink with its thrust above
  the weight, so the liftoff is exactly there with the mass untouched (no root search
  across the discontinuity, no integrator bias).
- ``fails: true`` on the pad: no liftoff by t_max, status ``no_liftoff``, no exception.
- A vehicle at rest above the ground is not held down: it falls until its thrust turns
  it around.
- While clamped the felt axial acceleration is g_eff (1 g), not the thrust building
  under the hold-down.
- ``hold_closed_form`` subtracts only its segment's burn, so a lit hold split after
  ignition gives the single-call mass (the track prelude of build step 7 splits holds).
- A moving ``AscentStart`` lit before release is the test-only emulation of a burn on
  the carriage: HOLD rows keep v0, and the flight is behind an instant start by the
  straddle form.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pytest

from launchsim import sim
from launchsim.config import IgnitionConfig, IntegratorConfig, RunConfig
from launchsim.constants import G0_MPS2, MU_EARTH_M3S2, R_EARTH_M
from launchsim.dynamics import VERTICAL_LAYOUT, ConstantGravity
from launchsim.losses import ignition_loss_analytic_mps
from launchsim.phases import (
    AscentStart,
    HoldParams,
    IgnitionSpec,
    IntegratorSettings,
    TraceBuilder,
    VerticalPlanner,
)
from launchsim.vehicle import Stage, Startup, Vehicle

if TYPE_CHECKING:
    from conftest import RunVertical

G_EFF = MU_EARTH_M3S2 / R_EARTH_M**2  # omega_p = 0 in Phase 1
REL = 1e-10


def _pad(t_ign_s: float, end: str = "stage1_burnout", **kw: object) -> RunConfig:
    return RunConfig(
        name="pad",
        ignition={"stage1": IgnitionConfig(t_ign_s=t_ign_s, **kw), "stage2": IgnitionConfig()},
        end=end,
    )


def test_hold_with_ramp_lit_two_seconds_before_release(f9_vehicle: Vehicle) -> None:
    stage = f9_vehicle.stages[0]
    assert stage.startup.kind == "ramp" and stage.startup.t_ramp_s == 2.0
    m0 = f9_vehicle.liftoff_mass_kg()
    mdot = stage.thrust_vac_total_N / stage.c_mps
    burned = mdot * 1.0  # a 2 s linear ramp burns mdot t_r / 2

    result = sim.run(_pad(-2.0), f9_vehicle)
    m = result.metrics
    assert result.status == "nominal" and result.flags == []
    assert m["t_release_s"] == 0.0
    assert m["alt_at_release_m"] == 0.0 and m["speed_at_release_mps"] == 0.0
    assert math.isclose(m["mass_at_release_kg"], m0 - burned, rel_tol=REL)
    assert math.isclose(m["propellant_burned_before_release_kg"], burned, rel_tol=REL)
    assert math.isclose(
        m["dv_vac_equiv_before_release_mps"],
        stage.c_mps * math.log(m0 / (m0 - burned)),
        rel_tol=REL,
    )
    assert m["hold_duration_s"] == 2.0 and m["hold_extension_s"] == 0.0
    assert m["t_ign_rel_release_s_stage1"] == -2.0
    # No extension: the flight starts at release and the whole clamp burn is before it.
    assert m["t_flight_start_s"] == 0.0
    assert m["mass_at_flight_start_kg"] == m["mass_at_release_kg"]
    assert m["propellant_burned_before_flight_kg"] == m["propellant_burned_before_release_kg"]
    assert m["dv_vac_equiv_before_flight_mps"] == m["dv_vac_equiv_before_release_mps"]
    assert m["hold_propellant_burned_kg"] == m["propellant_burned_before_release_kg"]
    # At release the full thrust exceeds the weight: the hold-down carries tension.
    assert math.isclose(
        m["hold_down_force_min_N"], (m0 - burned) * G_EFF - stage.thrust_vac_total_N, rel_tol=REL
    )
    hold = result.phases[0]
    assert hold.spec.kind == "HOLD" and hold.spec.t0 == -2.0 and hold.t_end == 0.0
    frame = result.timeseries
    clamped = frame[frame["phase"] == "HOLD"]
    assert (clamped["z_m"] == 0.0).all() and (clamped["v_mps"] == 0.0).all()
    assert clamped["t_s"].iloc[0] == -2.0 and clamped["t_s"].iloc[-1] == 0.0
    # Clamped, the vehicle feels its weight carried by the hold-down (1 g_eff), while the
    # thrust column ramps up to full thrust at t = 0.
    assert (abs(clamped["accel_felt_g"] - G_EFF / G0_MPS2) < 1e-12).all()
    assert clamped["thrust_N"].iloc[0] == 0.0
    assert math.isclose(clamped["thrust_N"].iloc[-1], stage.thrust_vac_total_N, rel_tol=REL)
    assert (frame["t_rel_release_s"] == frame["t_s"]).all()
    assert list(result.events["event"])[:2] == ["ignition", "release"]
    assert not any("hold extended" in a for a in result.assumptions)


def test_hold_extends_to_the_liftoff_root_when_lit_at_release(f9_vehicle: Vehicle) -> None:
    stage = f9_vehicle.stages[0]
    t_r = stage.startup.t_ramp_s
    m0 = f9_vehicle.liftoff_mass_kg()
    t_full = stage.thrust_vac_total_N
    mdot = t_full / stage.c_mps
    # T_full t / t_r = (m0 - mdot t^2 / (2 t_r)) g_eff  ->  a t^2 + b t + c = 0
    a = mdot * G_EFF / (2.0 * t_r)
    b = t_full / t_r
    c = -m0 * G_EFF
    t_star = (-b + math.sqrt(b * b - 4.0 * a * c)) / (2.0 * a)
    assert 0.0 < t_star < t_r  # liftoff inside the ramp

    m_lift = m0 - mdot * t_star**2 / (2.0 * t_r)  # the ramp burns mdot t^2/(2 t_r) clamped
    c = stage.c_mps

    result = sim.run(_pad(0.0), f9_vehicle)
    m = result.metrics
    assert result.status == "nominal" and result.flags == []
    # Nothing burns before release (t = 0): the clamp burn happens in the extension.
    assert m["t_release_s"] == 0.0 and m["propellant_burned_before_release_kg"] == 0.0
    assert m["mass_at_release_kg"] == m0 and m["dv_vac_equiv_before_release_mps"] == 0.0
    assert math.isclose(m["hold_extension_s"], t_star, rel_tol=REL)
    assert math.isclose(m["hold_duration_s"], t_star, rel_tol=REL)
    assert abs(m["hold_down_force_min_N"]) < 1e-6 * m0 * G_EFF  # the root: thrust = weight
    assert f"hold extended to t = {t_star:.6g} s for liftoff (TWR < 1 at release)" in (
        result.assumptions
    )
    # The propellant burned while clamped past t = 0 is reported as burned before flight,
    # with its delta-v equivalent, and the budget from liftoff completes the rocket
    # equation: dv_vac + c ln(m0/m_lift) = c ln(m0/m_dry).
    assert math.isclose(m["t_flight_start_s"], t_star, rel_tol=REL)
    assert math.isclose(m["mass_at_flight_start_kg"], m_lift, rel_tol=REL)
    assert math.isclose(m["propellant_burned_before_flight_kg"], m0 - m_lift, rel_tol=REL)
    assert math.isclose(m["hold_propellant_burned_kg"], m0 - m_lift, rel_tol=REL)
    assert math.isclose(m["dv_vac_equiv_before_flight_mps"], c * math.log(m0 / m_lift), rel_tol=REL)
    assert math.isclose(
        m["dv_vac_mps"] + m["dv_vac_equiv_before_flight_mps"],
        c * math.log(m0 / f9_vehicle.stack_dry_mass_kg(0)),
        rel_tol=1e-9,
    )
    assert m0 - m_lift > 1000.0  # over a tonne burned on the hold-down, not zero
    liftoff = result.events[result.events["event"] == "liftoff"].iloc[0]
    assert math.isclose(float(liftoff["t_s"]), t_star, rel_tol=REL)
    assert math.isclose(float(liftoff["m_kg"]), m_lift, rel_tol=REL)
    # The ignition at t = 0 is logged inside the extended hold, before the liftoff.
    assert list(result.events["event"]) == [
        "release",
        "ignition",
        "liftoff",
        "ramp_end",
        "propellant",
        "end",
    ]
    ign = result.events[result.events["event"] == "ignition"].iloc[0]
    assert float(ign["t_s"]) == 0.0 and ign["phase"] == "HOLD" and float(ign["m_kg"]) == m0
    kinds = [(p.spec.kind, p.ended_by) for p in result.phases]
    assert kinds == [("HOLD", "liftoff"), ("BURN", "t_end"), ("BURN", "propellant")]
    # The burn starts at the liftoff root, rising; the ramp's end is a phase boundary.
    assert result.phases[1].spec.t0 == result.phases[0].t_end
    assert result.phases[1].t_end == t_r
    frame = result.timeseries
    flight = frame[frame["phase"] == "BURN"]
    assert (flight["v_mps"] >= 0.0).all() and (flight["z_m"] >= 0.0).all()
    clamped = frame[frame["phase"] == "HOLD"]
    assert (abs(clamped["accel_felt_g"] - G_EFF / G0_MPS2) < 1e-12).all()
    assert math.isclose(clamped["thrust_N"].iloc[-1], m_lift * G_EFF, rel_tol=1e-9)  # balance
    # Sitting clamped past t = 0 is not a gravity loss: the budget starts at liftoff
    # with v = 0 and the burn lasts t_b + t_r/2 from ignition regardless.
    t_b = stage.propellant_mass_kg / mdot
    assert math.isclose(m["stage1_burnout_t_s"], t_b + 0.5 * t_r, rel_tol=1e-9)
    assert abs(m["identity_residual_mps"]) < 1e-6


def test_step_lit_after_release_lifts_off_at_the_kink_with_the_mass_untouched(
    f9_vehicle: Vehicle,
) -> None:
    """A step ignition at t = 0.5 s from rest: the hold before the kink is unlit (no
    thrust, no mass flow, no events), the engine lights at the kink with T_full above
    the weight, so liftoff is exactly there with m = m0 to the bit and the burnout at
    t_ign + t_b; the integrator never sees the step's f(0) = 1 from the left."""
    stage = f9_vehicle.stages[0]
    m0 = f9_vehicle.liftoff_mass_kg()
    mdot = stage.thrust_vac_total_N / stage.c_mps
    t_b = stage.propellant_mass_kg / mdot
    t_ign = 0.5
    assert stage.thrust_vac_total_N > m0 * G_EFF

    result = sim.run(_pad(t_ign, startup={"kind": "step"}), f9_vehicle)
    m = result.metrics
    assert result.status == "nominal" and result.flags == []
    assert [(p.spec.kind, p.ended_by) for p in result.phases] == [
        ("HOLD", "t_end"),
        ("BURN", "propellant"),
    ]
    assert list(result.events["event"]) == ["release", "ignition", "liftoff", "propellant", "end"]
    liftoff = result.events[result.events["event"] == "liftoff"].iloc[0]
    assert float(liftoff["t_s"]) == t_ign and float(liftoff["m_kg"]) == m0
    assert m["hold_extension_s"] == t_ign and m["propellant_burned_before_flight_kg"] == 0.0
    assert m["mass_at_flight_start_kg"] == m0 and m["t_flight_start_s"] == t_ign
    assert math.isclose(m["stage1_burnout_t_s"], t_ign + t_b, rel_tol=1e-12)
    # The minimum hold-down force is at the kink, where the full thrust exceeds the weight.
    assert math.isclose(
        m["hold_down_force_min_N"], m0 * G_EFF - stage.thrust_vac_total_N, rel_tol=REL
    )
    clamped = result.timeseries[result.timeseries["phase"] == "HOLD"]
    assert (clamped["thrust_N"] == 0.0).all() and (clamped["m_kg"] == m0).all()
    assert (abs(clamped["accel_felt_g"] - G_EFF / G0_MPS2) < 1e-12).all()


def test_a_start_at_rest_above_the_ground_is_not_held_down(
    toy_stage: Stage, run_vertical: RunVertical
) -> None:
    """AscentStart(z0 = 1000 m, v0 = 0) with the engines lit 5 s later, constant g: no
    HOLD, the vehicle falls (sigma = -1 from rest: the net acceleration is -g), lights
    at z = z0 - g t^2/2, v = -g t, turns around under thrust and burns out rising."""
    g = G0_MPS2
    z0, t_ign = 1000.0, 5.0
    vehicle = Vehicle(stages=(toy_stage,))
    result = run_vertical(
        vehicle,
        {"stage1": IgnitionSpec(t_ign)},
        ConstantGravity(g),
        g,
        start=AscentStart(z0, 0.0),
        end="stage1_burnout",
    )
    m = result.metrics
    assert result.status == "nominal" and result.flags == []
    assert [(p.spec.kind, p.spec.sigma, p.ended_by) for p in result.phases] == [
        ("FALL_PRE_IGN", -1, "t_end"),
        ("BURN", -1, "turnaround"),
        ("BURN", 1, "propellant"),
    ]
    assert m["hold_duration_s"] is None and m["hold_propellant_burned_kg"] is None
    assert m["t_flight_start_s"] == 0.0 and m["speed_start_mps"] == 0.0
    ign = result.events[result.events["event"] == "ignition"].iloc[0]
    assert math.isclose(float(ign["z_m"]), z0 - 0.5 * g * t_ign**2, rel_tol=1e-9)
    assert math.isclose(float(ign["v_mps"]), -g * t_ign, rel_tol=1e-9)
    assert abs(m["identity_residual_mps"]) < 1e-6


def test_failed_ignition_on_the_pad_never_lifts_off(f9_vehicle: Vehicle) -> None:
    cfg = RunConfig(
        name="pad",
        ignition={"stage1": IgnitionConfig(fails=True), "stage2": IgnitionConfig()},
        end="impact",
        integrator=IntegratorConfig(t_max_s=120.0),
    )
    result = sim.run(cfg, f9_vehicle)
    assert result.status == "no_liftoff"
    assert any(f.startswith("no_liftoff") for f in result.flags)
    m = result.metrics
    assert m["propellant_burned_before_release_kg"] == 0.0
    assert m["hold_propellant_burned_kg"] == 0.0
    assert m["t_flight_start_s"] is None and m["mass_at_flight_start_kg"] is None
    assert m["propellant_burned_before_flight_kg"] is None
    assert m["hold_duration_s"] == 120.0 and m["hold_extension_s"] == 120.0
    assert math.isclose(
        m["hold_down_force_min_N"], f9_vehicle.liftoff_mass_kg() * G_EFF, rel_tol=REL
    )
    assert m["stage1_burnout_t_s"] is None and m["apex_alt_m"] is None
    assert [p.spec.kind for p in result.phases] == ["HOLD"]
    assert result.loss_budget is not None and result.loss_budget.speed_end == 0.0
    frame = result.timeseries
    assert (frame["thrust_N"] == 0.0).all() and (frame["v_mps"] == 0.0).all()
    assert frame["t_s"].iloc[-1] == 120.0


def test_a_lit_hold_split_after_ignition_burns_the_segment_increment_only(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """``hold_closed_form`` counts the closed-form burn from ignition but subtracts only
    its own segment's increment, so a lit hold split at -1 s (as a track prelude
    splitting at a startup kink would) gives the single-call mass: the F9 ramp lit at
    -2 s burns mdot t^2/(2 t_r) by t, i.e. mdot/4 by -1 s and mdot/2 by 0 s, never the
    first segment's burn twice."""
    stage = f9_vehicle.stages[0]
    t_r = stage.startup.t_ramp_s
    m0 = f9_vehicle.liftoff_mass_kg()
    mdot = stage.thrust_vac_total_N / stage.c_mps
    m_mid = m0 - mdot * 1.0**2 / (2.0 * t_r)
    m_end = m0 - mdot * t_r / 2.0
    planner = VerticalPlanner(
        f9_vehicle,
        {"stage1": IgnitionSpec(-t_r), "stage2": IgnitionSpec()},
        ConstantGravity(G_EFF),
        G_EFF,
        "stage1_burnout",
        tight_settings,
    )
    params = HoldParams(stage.schedule(-t_r, None, False), G_EFF)
    y0 = VERTICAL_LAYOUT.build(m_kg=m0)

    tr_one = planner.new_builder()
    y_one, f_one = planner.hold_closed_form(tr_one, params, -t_r, 0.0, y0)
    tr_two = planner.new_builder()
    y_mid, f_a = planner.hold_closed_form(tr_two, params, -t_r, -1.0, y0)
    y_two, f_b = planner.hold_closed_form(tr_two, params, -1.0, 0.0, y_mid)

    assert math.isclose(float(VERTICAL_LAYOUT.get(y_mid, "m_kg")), m_mid, rel_tol=REL)
    assert math.isclose(float(VERTICAL_LAYOUT.get(y_one, "m_kg")), m_end, rel_tol=REL)
    assert math.isclose(float(VERTICAL_LAYOUT.get(y_two, "m_kg")), m_end, rel_tol=REL)
    assert math.isclose(min(f_a, f_b), f_one, rel_tol=REL)
    assert math.isclose(f_one, m_end * G_EFF - stage.thrust_vac_total_N, rel_tol=REL)
    assert len(tr_one.phases) == 1 and len(tr_two.phases) == 2
    # The full mass history agrees sample by sample where the grids coincide.
    masses_one = {round(float(t), 9): float(mm) for t, mm in zip(*_t_m(tr_one), strict=True)}
    masses_two = {round(float(t), 9): float(mm) for t, mm in zip(*_t_m(tr_two), strict=True)}
    assert set(masses_two) == set(masses_one)
    assert all(math.isclose(masses_two[t], mm, rel_tol=REL) for t, mm in masses_one.items())


def _t_m(tr: TraceBuilder) -> tuple[list[float], list[float]]:
    ts = [float(t) for p in tr.phases for t in p.t]
    ms = [float(mm) for p in tr.phases for mm in VERTICAL_LAYOUT.get(p.y, "m_kg")]
    return ts, ms


def test_a_moving_start_lit_before_release_emulates_a_burn_on_the_carriage(
    f9_vehicle: Vehicle, run_vertical: RunVertical
) -> None:
    """AscentStart(v0 = 77) with the ramp lit at -2 s is the documented test-only
    emulation of "lit on the carriage" (no track model): the HOLD rows carry z = 0 and
    v = v0 unchanged (not a physical state), only the mass burns, and the flight that
    follows is behind an instant start at the same v0 by the straddle form with
    Phi_pre = t_r/2 = 1 s and nothing missing after release:
    c ln(m0/(m0 - mdot)) - g."""
    g = G0_MPS2
    v0 = 77.0
    stage = f9_vehicle.stages[0]
    t_r = stage.startup.t_ramp_s
    m0 = f9_vehicle.liftoff_mass_kg()
    mdot = stage.thrust_vac_total_N / stage.c_mps
    vehicle = f9_vehicle
    gravity = ConstantGravity(g)
    emulated = run_vertical(
        vehicle, {"stage1": IgnitionSpec(-t_r)}, gravity, g, start=AscentStart(0.0, v0)
    )
    instant = run_vertical(
        vehicle,
        {"stage1": IgnitionSpec(0.0, startup=Startup("step"))},
        gravity,
        g,
        start=AscentStart(0.0, v0),
    )
    m = emulated.metrics
    assert emulated.status == "nominal" and emulated.flags == []
    assert m["hold_duration_s"] == t_r and m["hold_extension_s"] == 0.0
    assert math.isclose(m["mass_at_release_kg"], m0 - mdot * t_r / 2.0, rel_tol=REL)
    assert m["speed_at_release_mps"] == v0 and m["speed_start_mps"] == v0
    clamped = emulated.timeseries[emulated.timeseries["phase"] == "HOLD"]
    assert (clamped["v_mps"] == v0).all() and (clamped["z_m"] == 0.0).all()
    loss = instant.metrics["stage1_burnout_speed_mps"] - m["stage1_burnout_speed_mps"]
    expected = stage.c_mps * math.log(m0 / (m0 - mdot * t_r / 2.0)) - g * t_r / 2.0
    assert abs(loss - expected) < 1e-5
    assert math.isclose(
        ignition_loss_analytic_mps(g, -t_r, stage.startup, stage.c_mps, mdot, m0),
        expected,
        rel_tol=1e-12,
    )


def test_propellant_exhausted_during_a_hold_raises(f9_vehicle: Vehicle) -> None:
    stage = f9_vehicle.stages[0]
    t_b = stage.propellant_mass_kg / (stage.thrust_vac_total_N / stage.c_mps)
    with pytest.raises(ValueError, match="propellant"):
        sim.run(_pad(-(t_b + 10.0)), f9_vehicle)
