"""The loss identity from release onward, across phases, including a fall-back through
apex and a burn against the velocity (docs/physics.md, "Loss accounting"):

    |v_f| - |v_0| = J_vac - J_grav - drag - J_steer - J_bp        (drag = J_bp = 0)

(b) the 1000 kg toy stage with 50 kg of propellant, constant g, released upward at
    300 m/s, engines lit at t = 40 s while falling (v = 300 - g 40 = -92.3 m/s, z =
    300 * 40 - g 40^2 / 2 = 4155 m), a 10 s burn (5 kg/s), then a coast to impact:
    thrust points against
    the velocity for the whole burn, so J_steer = 2 c ln(m(40)/m(50)) and v < 0
    throughout.
(c) the same with 150 kg (a 30 s burn): v crosses zero upward under thrust, so the run
    logs exactly one apex (the pre-ignition one) and one turnaround; with end
    ``impact`` the vehicle then coasts to a second apex and falls to the ground.
(d) F9 pad start v0 = 0 to stage-1 burnout under mu/r^2, the run model.
(e) an apex inside a burn: the toy released at z0 = 1000 m with v0 = 3 m/s and a 4 s
    ramp lit at release, so the thrust is below the weight until t = t_r m g/T = 2.6 s:
    the vehicle tops out under thrust (sigma +1 -> -1 in the same burn), falls, turns
    around and burns out rising; the signed burnout speed is v0 + c ln(m0/mf) -
    g (t_b + t_r/2) whatever the sign of v, and the steering loss is 2 c ln(m_apex /
    m_turn). From z0 = 0 the same start hits the ground while thrusting (status impact).

Residual < 1e-6 m/s in every case (CLAUDE.md allows 0.01). Case (a), the silo, comes
with the assist models (build step 7).
"""

from __future__ import annotations

import dataclasses
import math
from typing import TYPE_CHECKING

import numpy as np

from launchsim import sim
from launchsim.config import IgnitionConfig, RunConfig
from launchsim.constants import G0_MPS2, MU_EARTH_M3S2, R_EARTH_M
from launchsim.dynamics import VERTICAL_LAYOUT, ConstantGravity
from launchsim.losses import LossBudget
from launchsim.phases import AscentStart, IgnitionSpec
from launchsim.vehicle import Stage, Startup, Vehicle

if TYPE_CHECKING:
    from conftest import RunVertical

G = G0_MPS2
V0 = 300.0
T_IGN = 40.0
M0 = 1000.0  # liftoff mass of the toy whatever its propellant load
RESIDUAL = 1e-6


def _budget_from_metrics(m: dict) -> float:
    """The identity recomputed here from the reported terms, not the package's method."""
    gained = m["speed_end_mps"] - m["speed_start_mps"]
    explained = (
        m["dv_vac_mps"]
        - m["gravity_loss_mps"]
        - m["drag_loss_mps"]
        - m["steering_loss_mps"]
        - m["back_pressure_loss_mps"]
    )
    return gained - explained


def _falling_toy(toy_stage: Stage, propellant_kg: float) -> Vehicle:
    stage = dataclasses.replace(
        toy_stage, dry_mass_kg=M0 - propellant_kg, propellant_mass_kg=propellant_kg
    )
    return Vehicle(stages=(stage,))


def _run_falling(vehicle: Vehicle, end: str, run_vertical: RunVertical) -> sim.Result:
    return run_vertical(
        vehicle,
        {"stage1": IgnitionSpec(T_IGN, startup=Startup("step"))},
        ConstantGravity(G),
        G,
        start=AscentStart(0.0, V0),
        end=end,
    )


def test_b_burn_against_the_velocity_then_coast_to_impact(
    toy_stage: Stage, run_vertical: RunVertical
) -> None:
    c = G0_MPS2 * toy_stage.engine.isp_vac_s
    mdot = toy_stage.engine.thrust_vac_N / c
    t_burn = 50.0 / mdot  # 10 s
    m0 = M0
    v_ign = V0 - G * T_IGN
    z_ign = V0 * T_IGN - 0.5 * G * T_IGN**2
    assert v_ign < 0.0 and z_ign > 0.0
    dv_vac = c * math.log(m0 / (m0 - mdot * t_burn))
    v_bo = v_ign + dv_vac - G * t_burn
    assert v_bo < 0.0  # the burn only slows the fall

    result = _run_falling(_falling_toy(toy_stage, 50.0), "impact", run_vertical)
    m = result.metrics
    assert result.status == "impact" and result.flags == []
    assert abs(m["identity_residual_mps"]) < RESIDUAL
    assert abs(_budget_from_metrics(m)) < RESIDUAL
    assert m["drag_loss_mps"] == 0.0 and m["back_pressure_loss_mps"] == 0.0
    assert math.isclose(m["steering_loss_mps"], 2.0 * dv_vac, rel_tol=1e-9)
    assert math.isclose(m["dv_vac_mps"], dv_vac, rel_tol=1e-9)
    assert m["speed_start_mps"] == V0
    assert math.isclose(m["apex_alt_m"], V0**2 / (2.0 * G), rel_tol=1e-9)
    assert math.isclose(m["apex_t_s"], V0 / G, rel_tol=1e-9)

    events = result.events
    ign = events[events["event"] == "ignition"].iloc[0]
    assert math.isclose(float(ign["t_s"]), T_IGN, rel_tol=1e-12)
    assert math.isclose(float(ign["v_mps"]), v_ign, rel_tol=1e-9)
    assert math.isclose(float(ign["z_m"]), z_ign, rel_tol=1e-9)
    assert list(events["event"]) == ["release", "apex", "ignition", "propellant", "impact", "end"]
    burn = [p for p in result.phases if p.spec.kind == "BURN"]
    assert len(burn) == 1 and burn[0].spec.sigma == -1
    assert np.all(np.asarray(VERTICAL_LAYOUT.get(burn[0].y, "v_mps")) < 0.0)  # v < 0
    kinds = [p.spec.kind for p in result.phases]
    assert kinds == ["COAST_PRE_IGN", "FALL_PRE_IGN", "BURN", "FALL"]
    # Falling under gravity regains speed: the gravity term of the fall is negative.
    fall = result.phases[-1]
    j_grav = VERTICAL_LAYOUT.get(fall.y, "J_grav_mps")
    assert float(j_grav[-1]) - float(j_grav[0]) < 0.0
    # Impact speed from energy: the last coast is ballistic from burnout, whose altitude
    # is the vertical-burn closed form (dv/dt = T/m - g whatever the sign of v):
    # z_bo = z_ign + v_ign t_b - g t_b^2/2 + c [t_b - (mf/mdot) ln(m0/mf)].
    mf = m0 - mdot * t_burn
    z_bo = (
        z_ign
        + v_ign * t_burn
        - 0.5 * G * t_burn**2
        + c * (t_burn - (mf / mdot) * math.log(m0 / mf))
    )
    assert math.isclose(float(VERTICAL_LAYOUT.get(burn[0].y_end, "z_m")), z_bo, rel_tol=1e-9)
    v_impact = -math.sqrt(v_bo**2 + 2.0 * G * z_bo)
    assert math.isclose(m["impact_speed_mps"], -v_impact, rel_tol=1e-9)


def test_c_burn_through_turnaround_to_burnout(toy_stage: Stage, run_vertical: RunVertical) -> None:
    c = G0_MPS2 * toy_stage.engine.isp_vac_s
    mdot = toy_stage.engine.thrust_vac_N / c
    t_burn = 150.0 / mdot  # 30 s
    m0 = M0
    v_ign = V0 - G * T_IGN
    dv_vac = c * math.log(m0 / (m0 - mdot * t_burn))
    v_bo = v_ign + dv_vac - G * t_burn  # signed: dv/dt = T/m - g whatever the sign of v
    assert v_bo > 0.0  # v crosses zero upward during the burn

    result = _run_falling(_falling_toy(toy_stage, 150.0), "stage1_burnout", run_vertical)
    m = result.metrics
    assert result.status == "nominal" and result.flags == []
    names = list(result.events["event"])
    assert names.count("apex") == 1 and names.count("turnaround") == 1
    assert names == ["release", "apex", "ignition", "turnaround", "propellant", "end"]
    assert abs(m["identity_residual_mps"]) < RESIDUAL
    assert abs(_budget_from_metrics(m)) < RESIDUAL
    assert math.isclose(m["stage1_burnout_speed_mps"], v_bo, rel_tol=1e-9)
    assert math.isclose(m["dv_vac_mps"], dv_vac, rel_tol=1e-9)
    # Steering counts only the part of the burn spent falling: 2 c ln(m_ign / m_turn).
    turn = result.events[result.events["event"] == "turnaround"].iloc[0]
    m_turn = float(turn["m_kg"])
    assert abs(float(turn["v_mps"])) < 1e-9
    assert math.isclose(m["steering_loss_mps"], 2.0 * c * math.log(m0 / m_turn), rel_tol=1e-9)
    burns = [p for p in result.phases if p.spec.kind == "BURN"]
    assert [p.spec.sigma for p in burns] == [-1, 1]
    assert [p.ended_by for p in burns] == ["turnaround", "propellant"]
    assert [e.name for e in burns[1].spec.events] == [
        "propellant",
        "apex",
    ]  # never turnaround again


def test_c_with_end_impact_reaches_a_second_apex(
    toy_stage: Stage, run_vertical: RunVertical
) -> None:
    result = _run_falling(_falling_toy(toy_stage, 150.0), "impact", run_vertical)
    m = result.metrics
    assert result.status == "impact" and result.flags == []
    names = list(result.events["event"])
    assert names.count("apex") == 2 and names.count("turnaround") == 1 and names[-1] == "end"
    assert [p.spec.kind for p in result.phases] == [
        "COAST_PRE_IGN",
        "FALL_PRE_IGN",
        "BURN",
        "BURN",
        "COAST",
        "FALL",
    ]
    assert abs(m["identity_residual_mps"]) < RESIDUAL
    assert abs(_budget_from_metrics(m)) < RESIDUAL
    burn_end = result.phases[3]
    v_bo = float(VERTICAL_LAYOUT.get(burn_end.y_end, "v_mps"))
    z_bo = float(VERTICAL_LAYOUT.get(burn_end.y_end, "z_m"))
    assert math.isclose(m["apex_alt_m"], z_bo + v_bo**2 / (2.0 * G), rel_tol=1e-9)  # the higher one
    assert math.isclose(m["impact_speed_mps"], math.sqrt(v_bo**2 + 2.0 * G * z_bo), rel_tol=1e-9)
    assert m["speed_end_mps"] == m["impact_speed_mps"]


def test_d_f9_pad_start_under_inverse_square_gravity(f9_vehicle: Vehicle) -> None:
    cfg = RunConfig(
        name="pad",
        ignition={"stage1": IgnitionConfig(t_ign_s=-2.0), "stage2": IgnitionConfig()},
        end="stage1_burnout",
    )
    result = sim.run(cfg, f9_vehicle)
    m = result.metrics
    assert result.status == "nominal" and result.flags == []
    assert m["speed_start_mps"] == 0.0
    assert abs(m["identity_residual_mps"]) < RESIDUAL
    assert abs(_budget_from_metrics(m)) < RESIDUAL
    assert m["drag_loss_mps"] == 0.0 and m["back_pressure_loss_mps"] == 0.0
    assert m["steering_loss_mps"] == 0.0  # rising the whole way
    assert m["gravity_loss_alt_mps"] < 0.0  # mu/r^2 weakens with altitude
    assert m["gravity_loss_duration_mps"] > 0.0
    assert math.isclose(
        m["gravity_loss_duration_mps"] + m["gravity_loss_alt_mps"],
        m["gravity_loss_mps"],
        rel_tol=1e-12,
    )
    # g_ref = mu/R_E^2 times the burn duration: the duration part in closed form.
    g_ref = MU_EARTH_M3S2 / R_EARTH_M**2
    assert math.isclose(
        m["gravity_loss_duration_mps"], g_ref * m["stage1_burnout_t_s"], rel_tol=1e-9
    )
    stage = f9_vehicle.stages[0]
    m_release = m["mass_at_release_kg"]
    assert math.isclose(
        m["dv_vac_mps"],
        stage.c_mps * math.log(m_release / f9_vehicle.stack_dry_mass_kg(0)),
        rel_tol=1e-9,
    )
    budget = result.loss_budget
    assert isinstance(budget, LossBudget)
    assert abs(budget.residual_mps()) < RESIDUAL
    assert math.isclose(budget.speed_end, m["stage1_burnout_speed_mps"], rel_tol=1e-12)
    # No variant may beat the ideal: speed gained <= dv_vac.
    assert m["speed_end_mps"] < m["dv_vac_mps"]


def _apex_in_burn(z0: float, end: str, toy_stage: Stage, run_vertical: RunVertical) -> sim.Result:
    """The toy released at z0 with v0 = 3 m/s and a 4 s ramp lit at release, constant g:
    T/(m g) < 1 until t = t_r m g / T = 2.6 s, so the vehicle tops out under thrust."""
    return run_vertical(
        Vehicle(stages=(toy_stage,)),
        {"stage1": IgnitionSpec(0.0, startup=Startup("ramp", t_ramp_s=APEX_T_RAMP))},
        ConstantGravity(G),
        G,
        start=AscentStart(z0, APEX_V0),
        end=end,
    )


APEX_V0 = 3.0
APEX_T_RAMP = 4.0


def test_e_apex_inside_a_burn_flips_sigma_and_continues(
    toy_stage: Stage, run_vertical: RunVertical
) -> None:
    c = G0_MPS2 * toy_stage.engine.isp_vac_s
    mdot = toy_stage.engine.thrust_vac_N / c
    m0 = toy_stage.dry_mass_kg + toy_stage.propellant_mass_kg
    mf = toy_stage.dry_mass_kg
    t_b = toy_stage.propellant_mass_kg / mdot
    t_twr1 = APEX_T_RAMP * m0 * G / toy_stage.engine.thrust_vac_N  # thrust = weight
    assert 0.0 < t_twr1 < APEX_T_RAMP
    # dv/dt = T/m - g whatever the sign of v: the signed burnout speed is the vertical-burn
    # closed form with the ramp's extra t_r/2, and the vehicle burns out rising.
    v_bo = APEX_V0 + c * math.log(m0 / mf) - G * (t_b + 0.5 * APEX_T_RAMP)
    assert v_bo > 0.0

    result = _apex_in_burn(1000.0, "stage1_burnout", toy_stage, run_vertical)
    m = result.metrics
    assert result.status == "nominal" and result.flags == []
    names = list(result.events["event"])
    assert names == ["release", "ignition", "apex", "ramp_end", "turnaround", "propellant", "end"]
    burns = [p for p in result.phases if p.spec.kind == "BURN"]
    assert [p.spec.kind for p in result.phases] == ["BURN"] * 4
    assert [p.spec.sigma for p in burns] == [1, -1, -1, 1]
    assert [p.ended_by for p in burns] == ["apex", "t_end", "turnaround", "propellant"]
    # The event lists after the apex never carry apex; after the turnaround never turnaround.
    assert [e.name for e in burns[1].spec.events] == ["propellant", "turnaround", "impact"]
    assert [e.name for e in burns[3].spec.events] == ["propellant", "apex"]
    assert abs(m["identity_residual_mps"]) < RESIDUAL
    assert abs(_budget_from_metrics(m)) < RESIDUAL
    assert math.isclose(m["stage1_burnout_speed_mps"], v_bo, rel_tol=1e-9)
    assert math.isclose(m["stage1_burnout_t_s"], t_b + 0.5 * APEX_T_RAMP, rel_tol=1e-9)
    assert math.isclose(m["dv_vac_mps"], c * math.log(m0 / mf), rel_tol=1e-9)
    # Steering counts the falling part of the burn only: 2 c ln(m_apex / m_turn).
    events = result.events
    m_apex = float(events[events["event"] == "apex"]["m_kg"].iloc[0])
    m_turn = float(events[events["event"] == "turnaround"]["m_kg"].iloc[0])
    assert m0 > m_apex > m_turn > mf
    assert math.isclose(m["steering_loss_mps"], 2.0 * c * math.log(m_apex / m_turn), rel_tol=1e-9)
    assert m["steering_loss_mps"] > 0.0
    # The apex comes before the thrust reaches the weight, slightly above z0.
    assert 0.0 < m["apex_t_s"] < t_twr1 and m["apex_alt_m"] > 1000.0
    assert m["apex_alt_m"] < 1000.0 + APEX_V0**2 / (2.0 * G) * 2.0


def test_e_impact_while_thrusting_from_the_ground(
    toy_stage: Stage, run_vertical: RunVertical
) -> None:
    m0 = toy_stage.dry_mass_kg + toy_stage.propellant_mass_kg
    t_twr1 = APEX_T_RAMP * m0 * G / toy_stage.engine.thrust_vac_N

    result = _apex_in_burn(0.0, "impact", toy_stage, run_vertical)
    m = result.metrics
    assert result.status == "impact" and result.flags == []
    assert list(result.events["event"]) == ["release", "ignition", "apex", "impact"]
    burns = [p for p in result.phases if p.spec.kind == "BURN"]
    assert [p.spec.kind for p in result.phases] == ["BURN", "BURN"]
    assert [p.spec.sigma for p in burns] == [1, -1]
    assert [p.ended_by for p in burns] == ["apex", "impact"]
    assert m["stage1_burnout_t_s"] is None
    assert 0.0 < m["apex_t_s"] < m["impact_t_s"] < t_twr1
    assert m["impact_speed_mps"] > 0.0 and abs(m["final_alt_m"]) < 1e-6
    assert abs(m["identity_residual_mps"]) < RESIDUAL
    assert abs(_budget_from_metrics(m)) < RESIDUAL
    assert m["speed_end_mps"] == m["impact_speed_mps"]
