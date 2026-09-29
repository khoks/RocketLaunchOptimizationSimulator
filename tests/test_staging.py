"""Two-stage vertical burn under constant gravity with a staging coast.

Through ``sim.simulate`` (the planner: BURN 1, STAGING map, COAST_STAGING, BURN 2).
Closed forms written here: with constant g and v > 0 throughout, each burn adds
c ln(m_ign/m_bo) and gravity takes g times the elapsed time, so over the whole run

    v_f = v0 + c1 ln(m0/mf1) + c2 ln(m02/mf2) - g (t_b1 + t_c + t_b2)

with m02 = mf1 - dry1 - fairing (the fairing drops at staging), t_b1 = m_p1/mdot1,
t_b2 = m_p2/mdot2 and t_c the coast. J_vac = c1 ln(m0/mf1) + c2 ln(m02/mf2); J_grav =
g (t_b1 + t_c + t_b2). The g = 0 variant is the two-stage rocket equation. Asserted at
1e-9 relative (CLAUDE.md requires 1e-6).
"""

from __future__ import annotations

import dataclasses
import math
from typing import TYPE_CHECKING

import pytest

from launchsim.constants import G0_MPS2
from launchsim.dynamics import ConstantGravity
from launchsim.phases import AscentStart, IgnitionSpec
from launchsim.vehicle import Vehicle

if TYPE_CHECKING:
    from conftest import RunVertical

REL = 1e-9
V0 = 40.0


def _with_coast(vehicle: Vehicle, coast_s: float) -> Vehicle:
    stages = list(vehicle.stages)
    stages[1] = dataclasses.replace(stages[1], coast_before_ignition_s=coast_s)
    return dataclasses.replace(vehicle, stages=tuple(stages))


@pytest.mark.parametrize("g", [G0_MPS2, 0.0])
@pytest.mark.parametrize("coast_s", [0.0, 3.0])
def test_two_stage_burn_with_staging_coast(
    g: float, coast_s: float, two_stage_toy: Vehicle, run_vertical: RunVertical
) -> None:
    vehicle = _with_coast(two_stage_toy, coast_s)
    s1, s2 = vehicle.stages
    c1 = G0_MPS2 * s1.engine.isp_vac_s
    c2 = G0_MPS2 * s2.engine.isp_vac_s
    mdot1 = s1.n_engines * s1.engine.thrust_vac_N / c1
    mdot2 = s2.n_engines * s2.engine.thrust_vac_N / c2
    m0 = s1.dry_mass_kg + s1.propellant_mass_kg + s2.dry_mass_kg + s2.propellant_mass_kg
    m0 += vehicle.payload_mass_kg + vehicle.fairing_mass_kg
    mf1 = m0 - s1.propellant_mass_kg
    m02 = mf1 - s1.dry_mass_kg - vehicle.fairing_mass_kg
    mf2 = m02 - s2.propellant_mass_kg
    t_b1 = s1.propellant_mass_kg / mdot1
    t_b2 = s2.propellant_mass_kg / mdot2
    dv_vac = c1 * math.log(m0 / mf1) + c2 * math.log(m02 / mf2)
    t_total = t_b1 + coast_s + t_b2
    v_f = V0 + dv_vac - g * t_total
    assert m0 == 1360.0 and m02 == 350.0  # the fixture's stated masses
    assert s1.engine.thrust_vac_N > m0 * g  # rises from the start

    result = run_vertical(
        vehicle,
        {"stage1": IgnitionSpec(0.0), "stage2": IgnitionSpec(0.0)},
        ConstantGravity(g),
        g if g > 0.0 else G0_MPS2,
        start=AscentStart(0.0, V0),
        end="all_burnout",
    )
    m = result.metrics
    assert result.status == "nominal" and result.flags == []
    assert math.isclose(m["final_t_s"], t_total, rel_tol=REL)
    assert math.isclose(m["final_speed_mps"], v_f, rel_tol=REL)
    assert math.isclose(m["final_mass_kg"], mf2, rel_tol=REL)
    assert math.isclose(m["dv_vac_mps"], dv_vac, rel_tol=REL)
    assert math.isclose(m["gravity_loss_mps"], g * t_total, rel_tol=REL, abs_tol=1e-9)
    assert m["steering_loss_mps"] == 0.0 and m["back_pressure_loss_mps"] == 0.0
    assert abs(m["identity_residual_mps"]) < 1e-9
    assert math.isclose(m["stage1_burnout_t_s"], t_b1, rel_tol=REL)
    assert math.isclose(m["stage1_burnout_mass_kg"], mf1, rel_tol=REL)
    assert math.isclose(m["t_ign_rel_release_s_stage2"], t_b1 + coast_s, rel_tol=REL)

    events = result.events
    names = list(events["event"])
    assert names == [
        "release",
        "ignition",
        "propellant",
        "staging",
        "ignition",
        "propellant",
        "end",
    ]
    staging = events[events["event"] == "staging"].iloc[0]
    ign2 = events[(events["event"] == "ignition") & (events["stage"] == "stage2")].iloc[0]
    assert math.isclose(float(staging["m_kg"]), vehicle.mass_after_staging_kg(0), rel_tol=REL)
    assert math.isclose(float(ign2["m_kg"]), vehicle.mass_after_staging_kg(0), rel_tol=REL)
    assert math.isclose(float(ign2["t_s"]), t_b1 + coast_s, rel_tol=REL)

    kinds = [(p.spec.kind, p.ended_by) for p in result.phases]
    coast = [("COAST_STAGING", "t_end" if coast_s > 0.0 else "zero_span")]
    assert kinds == [("BURN", "propellant"), *coast, ("BURN", "propellant")]
    frame = result.timeseries
    assert (frame["v_mps"] > 0.0).all()
    assert list(frame["stage"].unique()) == ["stage1", "stage2"]
