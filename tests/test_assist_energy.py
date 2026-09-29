"""The assist energy identity (CLAUDE.md; docs/physics.md, "Assist energy identity"):

    integral (F_drive + T_sys) sdot dt
        = delta(M sdot^2/2 + M g_eff z) - integral Mdot (sdot^2/2 + g_eff z) dt + dissipated

with M = m_v + m_c, T_sys = (1 - f_imp) T and z the height above the track start. The
left side is E_drive + W_thrust, the right side delta_mech + massflow_term (both from
the quadrature states of the ASSIST phase, so the closure tests the integration, not
a trapezoid). Required 1e-6 relative; asserted 1e-9 (measured ~1e-13).

Closed forms on the 3 g0 / 100 m F9 silo (g_eff = mu/R_E^2, t_p = sqrt(2L/a)):

- cold: E_drive = M (a + g) L, W_thrust = 0, massflow 0;
- hot, full thrust for the whole push with mass M(t) = M0 - mdot t and sdot = a t:
  E_drive + W_thrust = (a + g) a [M0 t_p^2/2 - mdot t_p^3/3] whatever f_imp (the
  impinged thrust is just moved from W_thrust to E_drive), W_thrust = (1 - f_imp) T L,
  delta_mech = M_exit (a + g) L, massflow_term = mdot (a + g) a t_p^3/6;
- a ramp lit inside the push (the README's "lit on the carriage"): residual only.
"""

from __future__ import annotations

import math

import pytest

from launchsim import sim
from launchsim.assist.constant_accel import ConstantAccelAssist
from launchsim.assist.track import VERTICAL, StraightTrack
from launchsim.constants import G0_MPS2, MU_EARTH_M3S2, R_EARTH_M
from launchsim.dynamics import InverseSquareGravity
from launchsim.losses import AssistEnergyBudget
from launchsim.phases import ASSIST_KIND, IgnitionSpec, IntegratorSettings
from launchsim.vehicle import Vehicle

G_EFF = MU_EARTH_M3S2 / R_EARTH_M**2
A = 3.0 * G0_MPS2
L = 100.0
REL = 1e-9  # required 1e-6
FLOOR_J = 1.0


def _budget(
    vehicle: Vehicle,
    ignition: IgnitionSpec,
    settings: IntegratorSettings,
    m_c: float = 0.0,
    f_imp: float = 0.0,
) -> tuple[AssistEnergyBudget, sim.Result]:
    assist = ConstantAccelAssist(
        net_accel_mps2=A,
        carriage_mass_kg=m_c,
        brake_decel_mps2=5.0 * G0_MPS2,
        efficiency=0.5,
        f_imp=f_imp,
        g_eff_mps2=G_EFF,
    )
    specs = {name: IgnitionSpec() for name in vehicle.stage_names}
    specs[vehicle.stage_names[0]] = ignition
    result = sim.simulate(
        vehicle=vehicle,
        ignition=specs,
        gravity=InverseSquareGravity(MU_EARTH_M3S2),
        g_eff_mps2=G_EFF,
        assist=assist,
        track=StraightTrack(L, VERTICAL, -L),
        start=None,
        end="stage1_burnout",
        settings=settings,
    )
    assert result.status == "nominal"
    assert result.assist_budget is not None
    return result.assist_budget, result


def _residual_rel(b: AssistEnergyBudget) -> float:
    """The identity recomputed here from the budget's fields, not its method."""
    lhs = b.work_drive + b.work_thrust
    rhs = b.delta_mech + b.massflow_term + b.dissipated
    return abs(lhs - rhs) / max(abs(lhs), FLOOR_J)


def _stage1(vehicle: Vehicle) -> tuple[float, float, float]:
    stage = vehicle.stages[0]
    c = G0_MPS2 * stage.engine.isp_vac_s
    thrust = stage.n_engines * stage.engine.thrust_vac_N
    return thrust, thrust / c, vehicle.liftoff_mass_kg()


def _t_ramp(vehicle: Vehicle) -> float:
    """The first stage's own ramp time t_r [s] from the fixture (2 s for the F9)."""
    return vehicle.stages[0].startup.t_ramp_s


@pytest.mark.parametrize("m_c", [0.0, 20_000.0])
def test_cold_push_energy_is_the_mechanical_energy_gained(
    m_c: float, f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    b, result = _budget(f9_vehicle, IgnitionSpec(0.5), tight_settings, m_c=m_c)
    m0 = f9_vehicle.liftoff_mass_kg()
    e = (m0 + m_c) * (A + G_EFF) * L
    assert math.isclose(b.work_drive, e, rel_tol=1e-10)
    assert b.work_thrust == 0.0 and b.massflow_term == 0.0 and b.dissipated == 0.0
    v_exit = math.sqrt(2.0 * A * L)
    assert math.isclose(b.delta_mech, (m0 + m_c) * (0.5 * v_exit**2 + G_EFF * L), rel_tol=1e-10)
    assert _residual_rel(b) < REL
    assert b.residual_rel() < REL
    assert result.metrics["assist_energy_residual_rel"] < REL
    # The quadrature states themselves start at zero and end at the budget's sums.
    track = [p for p in result.phases if p.spec.kind == ASSIST_KIND]
    layout = track[0].spec.params.layout
    assert layout.get(track[0].y[:, 0], "E_drive_J") == 0.0
    assert math.isclose(layout.get(track[-1].y_end, "E_drive_J"), e, rel_tol=1e-10)


@pytest.mark.parametrize("f_imp", [0.0, 0.5, 1.0])
def test_hot_full_thrust_energy_closed_forms(
    f_imp: float, f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """Ramp completed in the hold (t_ign = -t_r from push start, the vehicle's own
    ramp): full thrust and full mass flow for the whole push."""
    t_r = _t_ramp(f9_vehicle)
    hot = IgnitionSpec(-t_r, reference="push_start")
    b, _result = _budget(f9_vehicle, hot, tight_settings, f_imp=f_imp)
    thrust, mdot, m0 = _stage1(f9_vehicle)
    t_p = math.sqrt(2.0 * L / A)
    m_push = m0 - mdot * t_r / 2.0  # burned in the hold
    e_sys = (A + G_EFF) * A * (0.5 * m_push * t_p**2 - mdot * t_p**3 / 3.0)
    w_thrust = (1.0 - f_imp) * thrust * L
    assert math.isclose(b.work_drive + b.work_thrust, e_sys, rel_tol=1e-10)
    assert math.isclose(b.work_drive, e_sys - w_thrust, rel_tol=1e-10)
    assert math.isclose(b.work_thrust, w_thrust, rel_tol=1e-10, abs_tol=1e-3)
    m_exit = m_push - mdot * t_p
    assert math.isclose(b.delta_mech, m_exit * (A + G_EFF) * L, rel_tol=1e-10)
    assert math.isclose(b.massflow_term, mdot * (A + G_EFF) * A * t_p**3 / 6.0, rel_tol=1e-10)
    assert b.massflow_term > 0.0  # the expelled propellant carries energy away
    assert b.dissipated == 0.0
    assert _residual_rel(b) < REL
    assert b.residual_rel() < REL


def test_ramp_straddling_the_push_closes(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """Lit on the carriage t_r before release (t_ign_abs = t_p - t_r): unlit sub-phase,
    then the ramp, with the release inside the ramp's last instant. The mass at
    release is m0 - mdot t_r/2 (the ramp ends exactly at release) and the identity
    closes from the quadrature states across the sub-phase boundary."""
    t_r = _t_ramp(f9_vehicle)
    b, result = _budget(f9_vehicle, IgnitionSpec(-t_r), tight_settings, f_imp=0.0)
    _thrust, mdot, m0 = _stage1(f9_vehicle)
    assert _residual_rel(b) < REL
    assert b.residual_rel() < REL
    assert b.work_thrust > 0.0 and b.massflow_term > 0.0
    m = result.metrics
    assert math.isclose(m["propellant_burned_on_track_kg"], mdot * t_r / 2.0, rel_tol=1e-9)
    assert math.isclose(m["mass_at_release_kg"], m0 - mdot * t_r / 2.0, rel_tol=1e-9)
    assert m["hold_propellant_burned_kg"] is None  # nothing was clamped before the push
    events = result.events
    t_ign = float(events[events["event"] == "ignition"]["t_s"].iloc[0])
    assert math.isclose(t_ign, math.sqrt(2.0 * L / A) - t_r, rel_tol=1e-12)
    assert set(events["phase"][events["event"] == "ignition"]) == {ASSIST_KIND}
    track = [p for p in result.phases if p.spec.kind == ASSIST_KIND]
    assert len(track) == 2  # unlit, then the ramp until the track end
    assert track[0].ended_by == "t_end"
    # The ramp ends exactly at the track end, so scipy may report the last sub-phase
    # as the track_end event or as t_end (a ~1e-13 residue decides); either way the
    # release happened at t_push with s = L.
    assert track[1].ended_by in ("track_end", "t_end")
    assert math.isclose(track[1].t_end, math.sqrt(2.0 * L / A), rel_tol=1e-12)
    assert abs(track[1].spec.params.layout.get(track[1].y_end, "s_m") - L) < 1e-9
    release = result.events[result.events["event"] == "release"]
    assert math.isclose(float(release["t_s"].iloc[0]), math.sqrt(2.0 * L / A), rel_tol=1e-12)
    assert not track[0].spec.params.lit and track[1].spec.params.lit
    assert math.isclose(m["exit_speed_mps"], math.sqrt(2.0 * A * L), rel_tol=1e-10)
