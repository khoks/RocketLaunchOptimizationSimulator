"""The vertical constant-acceleration silo push (docs/physics.md, "Silo model
(constant_accel, vertical) and every reported quantity" and "Hot start").

The drive prescribes the net acceleration a along the track, so every closed form is
exact and the tests assert them at 1e-10 relative:

- kinematics: v_exit = sqrt(2 a L), t_push = sqrt(2 L / a), s(t) = a t^2 / 2;
- forces: F_drive = M (a + g_eff sin phi) - (1 - f_imp) T, F_int = m_v (a + g_eff sin
  phi) - T, felt axial acceleration (F_int + T)/m_v = a + g_eff sin phi, no track-normal
  load on a vertical track (phi = pi/2), N = m g_eff on a horizontal one (unit level);
- energy and power: E_drive = M (a + g_eff) L cold, P_peak = F_drive v_exit at release;
  hot with full thrust for the whole push (ramp completed in a hold, M0 = m0 - mdot
  t_r/2): E_drive = (a + g) a [M0 t_p^2/2 - mdot t_p^3/3] - T L at f_imp = 0,
  W_thrust = T L, and P_peak(f_imp = 1)/P_cold = (M0 - mdot t_p)/m0;
- facility: d_brake = v_exit^2/(2 a_brake) = L a/a_brake, facility = L + d_brake;
- the ``interface_tensile`` flag (F_int < 0 with F_drive > 0) and the ``drive_limit``
  status (F_drive crossing zero inside the push), whose root is solved in the test;
- the push stated by its exit speed v over L (SP1 step 2): a = v^2 / (2 L), so
  v_exit = v, t_push = 2 L / v, felt v^2 / (2 L) + g_eff, E_drive = M (v^2 / 2 +
  g_eff L); where v^2 / (2 L) and (v^2 / (2 g0 L)) g0 are the same double (the
  tested 76.71 m/s over 200 m) the run flies exactly the run stated by net_accel_g =
  v^2 / (2 g0 L) and only its assumptions gain a line; otherwise the two differ by an
  ulp or two in a and agree to integrator noise (docs/physics.md, "Silo model");
- the ramp start stated by depth, speed or closed-form height (SP1 step 3), converted
  by ``phases.prelude.resolve_ignition`` before the run: depth d -> sqrt(2 (L - d) / a)
  and speed v -> v / a from push start, height h -> the smaller root of
  v_exit t - g_eff t^2/2 = h after release, a start within ZERO_SPAN_S of the release
  snapped to it, the unreachable refused; on the 1-D model the ignition event lies at
  the requested depth or speed (1e-9), and at the requested height under an injected
  ConstantGravity (1e-9), both counted from the mouth when it is raised above the
  datum; the run equals the run stated by the converted time; a later stage's ramp
  start by depth, speed or height is refused where the specs are built.

The F9 numbers (542,570 kg, 3 g0, L = 100 m, g_eff = mu/R_E^2): 76.70717 m/s,
2.60732 s, 3.9992 g0 felt, F_int 21.2786 MN, E 2.1279 GJ, P 1.6322 GW, braking 60 m.
"""

from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
import yaml

from launchsim import sim
from launchsim.assist import build_assist
from launchsim.assist.base import normal_load_N
from launchsim.assist.constant_accel import ConstantAccelAssist
from launchsim.assist.track import VERTICAL, StraightTrack
from launchsim.config import (
    ConstantAccelConfig,
    IgnitionConfig,
    RunConfig,
    resolve_experiment,
    resolve_run,
)
from launchsim.constants import G0_MPS2, J_PER_KWH, MU_EARTH_M3S2, R_EARTH_M
from launchsim.dynamics import (
    ConstantGravity,
    InverseSquareGravity,
    TrackParams,
    rhs_track,
    track_layout,
)
from launchsim.phases import ASSIST_KIND, HOLD_KIND, IgnitionSpec, IntegratorSettings
from launchsim.phases.prelude import resolve_ignition
from launchsim.vehicle import Startup, Vehicle

G_EFF = MU_EARTH_M3S2 / R_EARTH_M**2
A = 3.0 * G0_MPS2
L = 100.0
A_BRAKE = 5.0 * G0_MPS2
ETA = 0.5
REL = 1e-10
N_ABS = 1e-6  # N: no normal load on a vertical track


def _assist(
    a: float = A,
    m_c: float = 0.0,
    f_imp: float = 0.0,
    allow_negative: bool = False,
    brake: float = A_BRAKE,
) -> ConstantAccelAssist:
    return ConstantAccelAssist(
        net_accel_mps2=a,
        carriage_mass_kg=m_c,
        brake_decel_mps2=brake,
        efficiency=ETA,
        f_imp=f_imp,
        allow_negative_drive=allow_negative,
        g_eff_mps2=G_EFF,
    )


def _silo(
    vehicle: Vehicle,
    ignition: IgnitionSpec,
    settings: IntegratorSettings,
    *,
    assist: ConstantAccelAssist | None = None,
    length: float = L,
    end: str = "stage1_burnout",
) -> sim.Result:
    """A buried vertical silo of the given length (mouth at z = 0) under mu/r^2."""
    assist = _assist() if assist is None else assist
    specs = {name: IgnitionSpec() for name in vehicle.stage_names}
    specs[vehicle.stage_names[0]] = ignition
    return sim.simulate(
        vehicle=vehicle,
        ignition=specs,
        gravity=InverseSquareGravity(MU_EARTH_M3S2),
        g_eff_mps2=G_EFF,
        assist=assist,
        track=StraightTrack(length, VERTICAL, -length),
        start=None,
        end=end,
        settings=settings,
    )


def _track_rows(result: sim.Result) -> pd.DataFrame:
    rows = result.timeseries[result.timeseries["phase"] == ASSIST_KIND]
    assert len(rows) > 10
    return rows


def _stage1(vehicle: Vehicle) -> tuple[float, float, float]:
    """(T_full, mdot, m0) of the first stage from the fixture's numbers."""
    stage = vehicle.stages[0]
    c = G0_MPS2 * stage.engine.isp_vac_s
    thrust = stage.n_engines * stage.engine.thrust_vac_N
    return thrust, thrust / c, vehicle.liftoff_mass_kg()


COLD = IgnitionSpec(0.5)  # 0.5 s delay after release, the vehicle's own ramp


def _t_ramp(vehicle: Vehicle) -> float:
    """The first stage's own ramp time t_r [s] from the fixture (2 s for the F9)."""
    return vehicle.stages[0].startup.t_ramp_s


def _hot_full(vehicle: Vehicle) -> IgnitionSpec:
    """Lit t_r before the push start: the ramp is completed in the hold, so the push
    sees full thrust throughout and M0 = m0 - mdot t_r/2 at t = 0."""
    return IgnitionSpec(-_t_ramp(vehicle), reference="push_start")


# -------------------------------------------------------------------- kinematics


@pytest.mark.parametrize("m_c", [0.0, 20_000.0])
def test_cold_push_kinematics_and_drive_force(
    m_c: float, f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """v_exit = sqrt(2 a L), t_push = sqrt(2 L/a), s = a t^2/2 at every sample and
    F_drive = M (a + g_eff) with M = m_v + m_c; the carriage changes the force only."""
    result = _silo(f9_vehicle, COLD, tight_settings, assist=_assist(m_c=m_c))
    assert result.status == "nominal" and result.flags == []
    m = result.metrics
    v_exit = math.sqrt(2.0 * A * L)
    t_push = math.sqrt(2.0 * L / A)
    assert math.isclose(m["exit_speed_mps"], v_exit, rel_tol=REL)
    assert math.isclose(m["push_time_s"], t_push, rel_tol=REL)
    assert math.isclose(m["t_release_s"], t_push, rel_tol=REL)
    assert math.isclose(m["speed_at_release_mps"], v_exit, rel_tol=REL)
    assert m["alt_at_release_m"] == 0.0 and m["track_start_altitude_m"] == -L
    assert m["propellant_burned_before_release_kg"] == 0.0
    assert m["propellant_burned_on_track_kg"] == 0.0
    assert m["carriage_mass_kg"] == m_c
    # Rounded README hand numbers: a cross-check of the constants only, never the
    # expected value (the closed forms above are).
    assert abs(v_exit - 76.70717) < 1e-5 and abs(t_push - 2.60732) < 1e-5
    rows = _track_rows(result)
    t = rows["t_s"].to_numpy()
    s = rows["s_m"].to_numpy()
    assert t[0] == 0.0 and math.isclose(t[-1], t_push, rel_tol=REL)
    np.testing.assert_allclose(s, 0.5 * A * t * t, rtol=REL, atol=REL * L)
    np.testing.assert_allclose(rows["z_m"].to_numpy(), -L + s, rtol=REL, atol=REL * L)
    np.testing.assert_allclose(rows["v_mps"].to_numpy(), A * t, rtol=REL, atol=REL * v_exit)
    m0 = f9_vehicle.liftoff_mass_kg()
    assert (rows["m_kg"] == m0).all()
    f_drive = (m0 + m_c) * (A + G_EFF)
    np.testing.assert_allclose(rows["drive_force_N"].to_numpy(), f_drive, rtol=REL)
    assert math.isclose(m["drive_force_peak_N"], f_drive, rel_tol=REL)
    # Release maps the state: the first free-flight row continues the track's.
    release = result.events[result.events["event"] == "release"].iloc[0]
    assert math.isclose(float(release["v_mps"]), v_exit, rel_tol=REL)
    assert float(release["z_m"]) == 0.0 and float(release["m_kg"]) == m0


@pytest.mark.parametrize("m_c", [0.0, 20_000.0])
def test_vertical_track_carries_no_normal_load(
    m_c: float, f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """phi = pi/2, kappa = 0: N = m (kappa sdot^2 + g_eff cos phi) = 0 for both bodies
    (|N| < 1e-6 N at every sample; the columns are in g0 per unit mass)."""
    result = _silo(f9_vehicle, COLD, tight_settings, assist=_assist(m_c=m_c))
    rows = _track_rows(result)
    m_v = rows["m_kg"].to_numpy()
    n_v = rows["track_normal_g_vehicle"].to_numpy() * G0_MPS2 * m_v
    n_c = rows["track_normal_g_carriage"].to_numpy() * G0_MPS2 * max(m_c, 1.0)
    assert np.all(np.abs(n_v) < N_ABS) and np.all(np.abs(n_c) < N_ABS)
    m = result.metrics
    assert abs(m["track_normal_g_vehicle_peak"]) * G0_MPS2 * m_v[0] < N_ABS
    assert abs(m["track_normal_g_carriage_peak"]) * G0_MPS2 * max(m_c, 1.0) < N_ABS
    assert abs(m["peak_track_normal_g"]) * G0_MPS2 * m_v[0] < N_ABS


def test_horizontal_track_unit_level() -> None:
    """phi = 0 (not reachable through the config in Phase 1): the normal load is the
    weight, N = m g_eff, and the prescribed acceleration is untouched by gravity
    (sddot = a, F_drive = M a with no weight component along the track)."""
    m, sdot, g = 1234.5, 40.0, G_EFF
    assert math.isclose(normal_load_N(m, sdot, 0.0, 0.0, g), m * g, rel_tol=1e-15)
    assert math.isclose(normal_load_N(m, sdot, 0.0, VERTICAL, g), 0.0, abs_tol=1e-9)
    # A curved-up track adds the centripetal demand; a pulled cable relieves it.
    kappa = 1.0 / 500.0
    expected = m * (kappa * sdot * sdot + g * math.cos(0.3)) - 250.0
    assert math.isclose(normal_load_N(m, sdot, kappa, 0.3, g, 250.0), expected, rel_tol=1e-15)
    assist = _assist(m_c=100.0)
    track = StraightTrack(L, 0.0, 0.0)
    params = TrackParams(track, assist, assist.carriage_mass_kg, g, schedule=None)
    layout = track_layout(assist)
    y = layout.build(s_m=10.0, sdot_mps=sdot, m_kg=m)
    dy = rhs_track(0.0, y, params)
    assert dy[layout.index("s_m")] == sdot
    assert dy[layout.index("sdot_mps")] == A
    assert dy[layout.index("m_kg")] == 0.0
    assert math.isclose(dy[layout.index("E_drive_J")], (m + 100.0) * A * sdot, rel_tol=1e-15)
    assert dy[layout.index("W_thrust_J")] == 0.0 and dy[layout.index("J_mass_J")] == 0.0
    forces = params.forces(0.0, y)
    assert math.isclose(forces.drive_force_N, (m + 100.0) * A, rel_tol=1e-15)
    assert math.isclose(forces.interface_force_N, m * A, rel_tol=1e-15)


# ------------------------------------------------------------------------- loads


@pytest.mark.parametrize("m_c", [0.0, 20_000.0])
def test_cold_felt_acceleration_and_interface_force(
    m_c: float, f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """A full stack pushed at 3 g0 net feels a + g_eff = 39.2182 m/s^2 = 3.9992 g0;
    F_int = m_v (a + g_eff) = 21.2786 MN whatever the carriage mass (the carriage
    is behind the vehicle)."""
    result = _silo(f9_vehicle, COLD, tight_settings, assist=_assist(m_c=m_c))
    rows = _track_rows(result)
    m0 = f9_vehicle.liftoff_mass_kg()
    a_felt = A + G_EFF
    assert abs(a_felt - 39.2182) < 1e-4 and abs(a_felt / G0_MPS2 - 3.9992) < 1e-4
    np.testing.assert_allclose(rows["accel_felt_g"].to_numpy(), a_felt / G0_MPS2, rtol=REL)
    np.testing.assert_allclose(rows["interface_force_N"].to_numpy(), m0 * a_felt, rtol=REL)
    m = result.metrics
    assert math.isclose(m["felt_g_track_peak"], a_felt / G0_MPS2, rel_tol=REL)
    assert math.isclose(m["interface_force_peak_N"], m0 * a_felt, rel_tol=REL)
    assert math.isclose(m["interface_force_min_N"], m0 * a_felt, rel_tol=REL)
    assert math.isclose(m["peak_interface_force_N"], m0 * a_felt, rel_tol=REL)
    assert abs(m0 * a_felt - 21.2786e6) < 1e2
    # The silo's distinctive load is the ~4 g on the full stack; the flight peak (T/m at
    # burnout, unthrottled) is the same for every variant and, at 3 g0, larger, so the
    # run-wide peak_felt_axial_g is the flight's and says so.
    assert m["peak_felt_g_flight"] > m["felt_g_track_peak"]
    assert m["peak_felt_axial_g"] == max(m["peak_felt_g_flight"], m["felt_g_track_peak"])
    assert m["peak_felt_axial_g_phase"] == "BURN"
    assert m["peak_felt_axial_g_t_s"] == m["peak_felt_g_flight_t_s"] > 0.0


def test_peak_felt_axial_g_folds_in_the_track(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """The CLAUDE.md summary item is the run-wide peak: at 5 g0 net (the sweep's top
    value) the full stack feels (a + g_eff)/g0 = 5.999 g0 on the track, above the
    unthrottled flight peak T/m_dry_stack/g0 = 5.712 g0, and a failed ignition (no
    flight thrust) still reports the track's 3.999 g0, not 0."""
    a = 5.0 * G0_MPS2
    result = _silo(f9_vehicle, COLD, tight_settings, assist=_assist(a=a))
    m = result.metrics
    thrust, _mdot, _m0 = _stage1(f9_vehicle)
    flight_peak = thrust / f9_vehicle.stack_dry_mass_kg(0) / G0_MPS2
    assert math.isclose(m["peak_felt_g_flight"], flight_peak, rel_tol=REL)
    assert math.isclose(m["felt_g_track_peak"], (a + G_EFF) / G0_MPS2, rel_tol=REL)
    assert m["felt_g_track_peak"] > m["peak_felt_g_flight"]
    assert math.isclose(m["peak_felt_axial_g"], (a + G_EFF) / G0_MPS2, rel_tol=REL)
    assert m["peak_felt_axial_g_phase"] == ASSIST_KIND
    assert m["peak_felt_axial_g_t_s"] <= 0.0  # on the track, before the release
    failed = _silo(f9_vehicle, IgnitionSpec(fails=True), tight_settings, end="impact")
    assert failed.status == "impact"
    fm = failed.metrics
    assert fm["peak_felt_g_flight"] == 0.0
    assert math.isclose(fm["peak_felt_axial_g"], (A + G_EFF) / G0_MPS2, rel_tol=REL)
    assert fm["peak_felt_axial_g_phase"] == ASSIST_KIND


@pytest.mark.parametrize("f_imp", [0.0, 1.0])
def test_hot_full_thrust_interface_and_drive_force(
    f_imp: float, f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """Full thrust for the whole push (the 2 s ramp completed in the hold before it):
    F_int(t) = m_v(t) (a + g) - T at every sample, minimal at exit; F_drive = M (a + g)
    - (1 - f_imp) T, so at f_imp = 1 the drive carries the whole M (a + g). Under a
    prescribed acceleration the hot start changes the forces, not the exit speed."""
    result = _silo(f9_vehicle, _hot_full(f9_vehicle), tight_settings, assist=_assist(f_imp=f_imp))
    assert result.status == "nominal" and result.flags == []
    thrust, mdot, m0 = _stage1(f9_vehicle)
    t_r = _t_ramp(f9_vehicle)
    rows = _track_rows(result)
    t = rows["t_s"].to_numpy()
    m_v = rows["m_kg"].to_numpy()
    # Mass on the track: M0 = m0 - mdot t_r/2 at push start, then full flow.
    m_push = m0 - mdot * t_r / 2.0
    np.testing.assert_allclose(m_v, m_push - mdot * t, rtol=REL)
    assert (rows["thrust_N"] == thrust).all()
    f_int = m_v * (A + G_EFF) - thrust
    np.testing.assert_allclose(rows["interface_force_N"].to_numpy(), f_int, rtol=REL)
    assert int(rows["interface_force_N"].to_numpy().argmin()) == len(rows) - 1
    f_drive = m_v * (A + G_EFF) - (1.0 - f_imp) * thrust
    np.testing.assert_allclose(rows["drive_force_N"].to_numpy(), f_drive, rtol=REL)
    np.testing.assert_allclose(rows["accel_felt_g"].to_numpy(), (A + G_EFF) / G0_MPS2, rtol=REL)
    m = result.metrics
    assert math.isclose(m["exit_speed_mps"], math.sqrt(2.0 * A * L), rel_tol=REL)
    assert math.isclose(m["interface_force_peak_N"], f_int[0], rel_tol=REL)
    assert math.isclose(m["interface_force_min_N"], f_int[-1], rel_tol=REL)
    assert math.isclose(m["propellant_burned_before_release_kg"], m0 - m_v[-1], rel_tol=REL)
    assert math.isclose(m["propellant_burned_on_track_kg"], m_push - m_v[-1], rel_tol=REL)
    assert math.isclose(m["hold_propellant_burned_kg"], mdot * t_r / 2.0, rel_tol=REL)
    # Rounded plan figures (12.95 -> 12.67 MN): a cross-check of the constants only.
    assert abs(f_int[0] - 12.95e6) < 1e4 and abs(f_int[-1] - 12.67e6) < 1e4


def test_interface_tensile_flag_for_a_slow_hot_push(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """At 0.5 g0 net with full thrust the vehicle would outrun the carriage: F_int =
    m_v (a + g) - T < 0 while, with f_imp = 1, the drive still pushes (F_drive =
    M (a + g) > 0): the run completes with the ``interface_tensile`` flag."""
    a = 0.5 * G0_MPS2
    hot = _hot_full(f9_vehicle)
    result = _silo(f9_vehicle, hot, tight_settings, assist=_assist(a=a, f_imp=1.0))
    assert result.status == "nominal"
    assert len(result.flags) == 1 and result.flags[0].startswith("interface_tensile")
    rows = _track_rows(result)
    thrust, _mdot, _m0 = _stage1(f9_vehicle)
    m_v = rows["m_kg"].to_numpy()
    assert np.all(rows["interface_force_N"].to_numpy() < 0.0)
    np.testing.assert_allclose(rows["drive_force_N"].to_numpy(), m_v * (a + G_EFF), rtol=REL)
    np.testing.assert_allclose(rows["interface_force_N"].to_numpy(), m_v * (a + G_EFF) - thrust)
    assert result.metrics["interface_force_min_N"] < 0.0
    assert math.isclose(result.metrics["exit_speed_mps"], math.sqrt(2.0 * a * L), rel_tol=REL)


def _drive_limit_root(vehicle: Vehicle, a: float, t_ign: float, t_r: float) -> float:
    """Time [s] at which F_drive = m(t)(a + g) - T_full (t - t_ign)/t_r crosses zero
    during a ramp lit at t_ign on a cold-started push, with m(t) = m0 - mdot
    (t - t_ign)^2 / (2 t_r): the positive root of a quadratic in u = t - t_ign."""
    thrust, mdot, m0 = _stage1(vehicle)
    qa = -mdot * (a + G_EFF) / (2.0 * t_r)
    qb = -thrust / t_r
    qc = m0 * (a + G_EFF)
    u = (-qb - math.sqrt(qb * qb - 4.0 * qa * qc)) / (2.0 * qa)
    return t_ign + u


def test_drive_limit_when_a_ramp_crosses_zero_drive_force(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """A 2 s ramp lit 2 s into a 0.5 g0 push (t_push = 6.39 s): F_drive = m (a + g) -
    T(t) falls through zero at t = 3.93 s, inside the push, so the run stops on the
    track with status ``drive_limit`` at the root solved here; with
    allow_negative_drive the same push completes with a negative drive force."""
    a = 0.5 * G0_MPS2
    t_ign, t_r = 2.0, 2.0
    ignition = IgnitionSpec(t_ign, reference="push_start", startup=Startup("ramp", t_ramp_s=t_r))
    t_root = _drive_limit_root(f9_vehicle, a, t_ign, t_r)
    assert t_ign < t_root < math.sqrt(2.0 * L / a)
    assert t_root - t_ign < t_r  # the closed form holds inside the ramp only
    result = _silo(f9_vehicle, ignition, tight_settings, assist=_assist(a=a))
    assert result.status == "drive_limit"
    assert any(f.startswith("drive_limit") for f in result.flags)
    assert result.phases[-1].spec.kind == ASSIST_KIND
    assert result.phases[-1].ended_by == "drive_limit"
    assert math.isclose(result.phases[-1].t_end, t_root, rel_tol=1e-9)
    event = result.events[result.events["event"] == "drive_limit"].iloc[0]
    assert math.isclose(float(event["t_s"]), t_root, rel_tol=1e-9)
    assert "release" not in set(result.events["event"])
    m = result.metrics
    assert m["exit_speed_mps"] is None and m["push_time_s"] is None
    assert m["facility_length_m"] is None and m["braking_distance_m"] is None
    rows = _track_rows(result)
    assert rows["drive_force_N"].to_numpy()[-1] < 1e-3  # at the root
    assert rows["drive_force_N"].to_numpy()[:-1].min() > 0.0
    assert m["stage1_burnout_speed_mps"] is None
    # Same push, negative drive allowed: completes, drive braking the engine at the end.
    allowed = _silo(f9_vehicle, ignition, tight_settings, assist=_assist(a=a, allow_negative=True))
    assert allowed.status == "nominal"
    assert "drive_limit" not in set(allowed.events["event"])
    assert allowed.timeseries[allowed.timeseries["phase"] == ASSIST_KIND]["drive_force_N"].min() < 0
    assert math.isclose(allowed.metrics["exit_speed_mps"], math.sqrt(2.0 * a * L), rel_tol=REL)
    # Drive work bookkeeping with braking: the positive part is the work up to the
    # root, which the drive_limit run integrated as its whole (net) drive energy; the
    # negative part is the braking after it; electrical energy counts the positive
    # part only (no regeneration), and the drive_braking flag is raised.
    ma = allowed.metrics
    assert math.isclose(ma["drive_work_in_J"], m["drive_energy_J"], rel_tol=1e-9)
    assert ma["drive_work_out_J"] > 0.0
    assert math.isclose(
        ma["drive_work_in_J"] - ma["drive_work_out_J"], ma["drive_energy_J"], rel_tol=REL
    )
    assert math.isclose(ma["electrical_energy_J"], ma["drive_work_in_J"] / ETA, rel_tol=REL)
    assert ma["electrical_energy_J"] > 0.0 > ma["drive_energy_J"] - ma["drive_work_in_J"]
    assert any(f.startswith("drive_braking") for f in allowed.flags)
    assert not any(f.startswith("drive_braking") for f in result.flags)
    # Cold and hot pushes that only push: no braking part, electrical = net / eta.
    cold = _silo(f9_vehicle, COLD, tight_settings)
    assert cold.metrics["drive_work_out_J"] == 0.0
    assert cold.metrics["drive_work_in_J"] == cold.metrics["drive_energy_J"]
    assert not any(f.startswith("drive_braking") for f in cold.flags)


def test_drive_force_negative_at_push_start_ends_at_t0(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """Full thrust from a hold at 0.5 g0 net and f_imp = 0: F_drive = M (a + g) - T < 0
    already at t = 0, so the engine's already-past rule ends the push at t0 with
    status ``drive_limit`` and no motion."""
    a = 0.5 * G0_MPS2
    result = _silo(f9_vehicle, _hot_full(f9_vehicle), tight_settings, assist=_assist(a=a))
    assert result.status == "drive_limit"
    last = result.phases[-1]
    assert last.spec.kind == ASSIST_KIND and last.ended_by == "drive_limit"
    assert last.t_end == 0.0 and last.spec.t0 == 0.0
    event = result.events[result.events["event"] == "drive_limit"].iloc[0]
    assert float(event["t_s"]) == 0.0 and float(event["v_mps"]) == 0.0
    # No release happened: every release item is n/a, while the hold's burn (the 2 s
    # ramp completed clamped, mdot t_r/2) and the empty push are reported as such.
    _thrust, mdot, m0 = _stage1(f9_vehicle)
    m = result.metrics
    for key in (
        "t_release_s",
        "speed_at_release_mps",
        "alt_at_release_m",
        "mass_at_release_kg",
        "propellant_burned_before_release_kg",
        "dv_vac_equiv_before_release_mps",
        "exit_speed_mps",
        "push_time_s",
        "braking_distance_m",
        "facility_length_m",
        "t_flight_start_s",
        "mass_at_flight_start_kg",
        "stage1_burnout_speed_mps",
        "t_ign_rel_release_s_stage1",
        "final_t_s",
        "peak_felt_axial_g_t_s",
    ):
        assert m[key] is None, key
    hold_burn = mdot * _t_ramp(f9_vehicle) / 2.0
    assert math.isclose(m["hold_propellant_burned_kg"], hold_burn, rel_tol=REL)
    assert m["propellant_burned_on_track_kg"] == 0.0
    assert m["liftoff_mass_kg"] == m0
    assert m["drive_energy_J"] == 0.0 and m["drive_work_in_J"] == 0.0
    assert m["drive_work_out_J"] == 0.0 and m["electrical_energy_J"] == 0.0
    assert m["drive_power_peak_W"] == 0.0 and m["drive_power_min_W"] == 0.0
    # The run-wide felt peak counts the hold's 1 g_eff and the zero-span push-start row
    # (the prescribed a + g_eff at t0, never delivered), which is the larger.
    hold_rows = result.timeseries[result.timeseries["phase"] == HOLD_KIND]
    np.testing.assert_allclose(hold_rows["accel_felt_g"].to_numpy(), G_EFF / G0_MPS2, rtol=REL)
    assert m["peak_felt_axial_g_phase"] == ASSIST_KIND
    assert math.isclose(m["peak_felt_axial_g"], (a + G_EFF) / G0_MPS2, rel_tol=REL)


def test_ramp_ending_at_the_track_end_is_logged_once(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """The README's "lit on the carriage" timing (t_ign = -t_r from release): the ramp
    ends at the instant of release, and the event log carries ramp_end once, on the
    track, right before the release, at t_push."""
    t_r = _t_ramp(f9_vehicle)
    result = _silo(f9_vehicle, IgnitionSpec(-t_r), tight_settings)
    assert result.status == "nominal"
    events = result.events
    names = list(events["event"])
    assert names.count("ramp_end") == 1
    i_ramp, i_rel = names.index("ramp_end"), names.index("release")
    assert i_ramp == i_rel - 1
    t_push = math.sqrt(2.0 * L / A)
    assert math.isclose(float(events["t_s"].iloc[i_ramp]), t_push, rel_tol=1e-12)
    assert events["phase"].iloc[i_ramp] == ASSIST_KIND
    t_ign = float(events["t_s"].iloc[names.index("ignition")])
    assert math.isclose(t_ign, t_push - t_r, rel_tol=1e-12)
    # A ramp ending inside the push is logged there too, once, at ignition + t_r.
    inside = _silo(f9_vehicle, IgnitionSpec(0.5, reference="push_start"), tight_settings)
    names_in = list(inside.events["event"])
    assert names_in.count("ramp_end") == 1
    t_end = float(inside.events["t_s"].iloc[names_in.index("ramp_end")])
    assert math.isclose(t_end, 0.5 + t_r, rel_tol=1e-12)
    assert names_in.index("ramp_end") < names_in.index("release")


def test_assist_registry_builds_every_config_model() -> None:
    """``ASSIST_MODELS`` keys are the ``model`` discriminator values of the buildable
    config classes and each class's own name; ``build_assist`` dispatches through it."""
    from typing import get_args

    from launchsim.assist import ASSIST_MODELS, build_assist
    from launchsim.config import ConstantAccelConfig, NoAssistConfig

    keys = {
        get_args(cls.model_fields["model"].annotation)[0]
        for cls in (NoAssistConfig, ConstantAccelConfig)
    }
    assert set(ASSIST_MODELS) == keys == {"none", "constant_accel"}
    assert all(cls.name == key for key, cls in ASSIST_MODELS.items())
    model, track = build_assist(NoAssistConfig(), G_EFF)
    assert model.name == "none" and track is None
    cfg = ConstantAccelConfig(
        model="constant_accel", net_accel_g=3.0, stroke_m=L, carriage_mass_t=22.0, brake_decel_g=5.0
    )
    model, track = build_assist(cfg, G_EFF)
    assert isinstance(model, ASSIST_MODELS["constant_accel"]) and model.name == "constant_accel"
    assert math.isclose(model.net_accel_mps2, 3.0 * G0_MPS2, rel_tol=1e-12)
    assert model.carriage_mass_kg == 22_000.0 and model.g_eff_mps2 == G_EFF
    assert track is not None and track.length_m == L
    assert math.isclose(track.start_altitude_m, -L, rel_tol=1e-12)
    # name and extra_state_names are class constants, not per-instance fields.
    with pytest.raises(TypeError):
        ConstantAccelAssist(
            net_accel_mps2=A, carriage_mass_kg=0.0, brake_decel_mps2=A_BRAKE, name="none"
        )  # type: ignore[call-arg]


# ------------------------------------------------------------- energy, power, facility


def test_cold_energy_power_and_facility(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """E_drive = M (a + g_eff) L = 2.1279 GJ (= delta KE + delta PE), electrical =
    E/eta, P_peak = M (a + g_eff) v_exit = 1.6322 GW at release, d_brake = v^2/(2
    a_brake) = L a/a_brake = 60.000 m and facility = L + d_brake = 160.000 m."""
    result = _silo(f9_vehicle, COLD, tight_settings)
    m = result.metrics
    m0 = f9_vehicle.liftoff_mass_kg()
    v_exit = math.sqrt(2.0 * A * L)
    e_drive = m0 * (A + G_EFF) * L
    p_peak = m0 * (A + G_EFF) * v_exit
    d_brake = L * A / A_BRAKE
    assert math.isclose(m["drive_energy_J"], e_drive, rel_tol=REL)
    assert math.isclose(m["assist_energy_J"], e_drive, rel_tol=REL)
    assert math.isclose(m["drive_energy_kWh"], e_drive / J_PER_KWH, rel_tol=REL)
    assert math.isclose(m["assist_energy_kWh"], e_drive / J_PER_KWH, rel_tol=REL)
    assert math.isclose(m["electrical_energy_J"], e_drive / ETA, rel_tol=REL)
    assert math.isclose(m["electrical_energy_kWh"], e_drive / ETA / J_PER_KWH, rel_tol=REL)
    assert math.isclose(m["drive_power_peak_W"], p_peak, rel_tol=REL)
    assert math.isclose(m["peak_drive_power_W"], p_peak, rel_tol=REL)
    assert math.isclose(m["braking_distance_m"], d_brake, rel_tol=REL)
    assert math.isclose(m["facility_length_m"], L + d_brake, rel_tol=REL)
    assert math.isclose(d_brake, 60.0, rel_tol=1e-12)
    assert math.isclose(m["braking_distance_m"], v_exit**2 / (2.0 * A_BRAKE), rel_tol=REL)
    assert m["assist_energy_residual_rel"] < 1e-9
    # Energy conservation reading of the cold push: the drive work is exactly the
    # kinetic plus potential energy the stack gains on the track.
    assert math.isclose(e_drive, m0 * (0.5 * v_exit**2 + G_EFF * L), rel_tol=1e-12)
    # Rounded README hand numbers: a cross-check of the constants only.
    assert abs(e_drive - 2.1279e9) < 1e5 and abs(p_peak - 1.6322e9) < 1e5
    rows = _track_rows(result)
    assert int(rows["drive_power_W"].to_numpy().argmax()) == len(rows) - 1
    assert _assist().braking_distance_m(v_exit) == v_exit * v_exit / (2.0 * A_BRAKE)


def test_hot_full_thrust_energy_and_peak_power(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """Full thrust for the whole push, no carriage, M0 = m0 - mdot t_r/2 at push start:
    E_drive = (a + g) a [M0 t_p^2/2 - mdot t_p^3/3] - T L (f_imp = 0), W_thrust = T L,
    and P_peak(f_imp = 1)/P_cold = (M0 - mdot t_p)/m0. The plan's finding: at fixed
    exit speed and felt g a hot start trades ~10 t of propellant for ~0.8 GJ of drive
    energy; it buys no exit speed."""
    thrust, mdot, m0 = _stage1(f9_vehicle)
    t_p = math.sqrt(2.0 * L / A)
    m_push = m0 - mdot * _t_ramp(f9_vehicle) / 2.0
    e_sys = (A + G_EFF) * A * (0.5 * m_push * t_p**2 - mdot * t_p**3 / 3.0)
    w_thrust = thrust * L
    hot_full = _hot_full(f9_vehicle)
    hot = _silo(f9_vehicle, hot_full, tight_settings, assist=_assist(f_imp=0.0))
    hot_imp = _silo(f9_vehicle, hot_full, tight_settings, assist=_assist(f_imp=1.0))
    cold = _silo(f9_vehicle, COLD, tight_settings)
    m, mi, mc = hot.metrics, hot_imp.metrics, cold.metrics
    assert math.isclose(m["drive_energy_J"], e_sys - w_thrust, rel_tol=REL)
    assert math.isclose(mi["drive_energy_J"], e_sys, rel_tol=REL)
    assert hot.assist_budget is not None and hot_imp.assist_budget is not None
    assert math.isclose(hot.assist_budget.work_thrust, w_thrust, rel_tol=REL)
    assert hot_imp.assist_budget.work_thrust == 0.0
    v_exit = math.sqrt(2.0 * A * L)
    p_cold = m0 * (A + G_EFF) * v_exit
    assert math.isclose(mc["drive_power_peak_W"], p_cold, rel_tol=REL)
    assert math.isclose(mi["drive_power_peak_W"] / p_cold, (m_push - mdot * t_p) / m0, rel_tol=REL)
    assert math.isclose(
        m["drive_power_peak_W"],
        (m_push - mdot * t_p) * (A + G_EFF) * v_exit - thrust * v_exit,
        rel_tol=REL,
    )
    # Rounded plan figures (1.276 GJ at f_imp = 0, 2.099 GJ at f_imp = 1, 0.823 GJ of
    # thrust work, 0.972 / 1.603 GW peak power): a cross-check of the constants only;
    # the hot start saves >= 35% of the cold peak power.
    assert abs(m["drive_energy_J"] - 1.276e9) < 2e6 and abs(mi["drive_energy_J"] - 2.099e9) < 2e6
    assert abs(w_thrust - 0.823e9) < 1e6
    assert abs(m["drive_power_peak_W"] - 0.972e9) < 2e6
    assert abs(mi["drive_power_peak_W"] - 1.603e9) < 2e6
    assert m["drive_power_peak_W"] < 0.65 * p_cold
    # Same exit speed and felt g as the cold push; ~9.7 t burned before release.
    assert math.isclose(m["exit_speed_mps"], mc["exit_speed_mps"], rel_tol=REL)
    assert math.isclose(m["felt_g_track_peak"], mc["felt_g_track_peak"], rel_tol=REL)
    assert abs(m["propellant_burned_before_release_kg"] - 9_730.0) < 20.0
    assert m["stage1_burnout_speed_mps"] < mc["stage1_burnout_speed_mps"]
    # These peaks sit at release (the vertex of P(t) lies far beyond the push) and the
    # drive never brakes: no negative power.
    for metrics in (m, mi, mc):
        assert math.isclose(metrics["drive_power_peak_t_s"], t_p, rel_tol=REL)
        assert metrics["drive_power_min_W"] == 0.0


def test_hot_push_peak_power_from_the_dense_output(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """Full thrust on a slow push (0.6 g0 net, no carriage): P(t) = (F0 - mdot (a + g)
    t) a t is a downward parabola with F0 = M0 (a + g) - T > 0 and its vertex t* =
    F0/(2 mdot (a + g)) inside the push, so the peak P* = F0^2 a/(4 mdot (a + g)) lies
    between samples: the metric comes from the dense output, not the sampled rows,
    and matches the closed form. F_drive turns negative before the exit (allowed
    here), so the braking peak drive_power_min_W = F_drive(t_p) v_exit < 0 at release
    is reported beside it. A push in which the drive only brakes has a zero (not
    -0.0) positive peak."""
    thrust, mdot, m0 = _stage1(f9_vehicle)
    a = 0.6 * G0_MPS2
    m_push = m0 - mdot * _t_ramp(f9_vehicle) / 2.0
    f0 = m_push * (a + G_EFF) - thrust
    t_star = f0 / (2.0 * mdot * (a + G_EFF))
    t_p = math.sqrt(2.0 * L / a)
    v_exit = math.sqrt(2.0 * a * L)
    assert f0 > 0.0 and 0.0 < t_star < t_p  # the closed form's preconditions
    p_star = f0 * f0 * a / (4.0 * mdot * (a + G_EFF))
    p_exit = ((m_push - mdot * t_p) * (a + G_EFF) - thrust) * v_exit
    assert p_exit < 0.0
    result = _silo(
        f9_vehicle, _hot_full(f9_vehicle), tight_settings, assist=_assist(a=a, allow_negative=True)
    )
    assert result.status == "nominal"
    m = result.metrics
    assert math.isclose(m["drive_power_peak_W"], p_star, rel_tol=1e-9)
    assert math.isclose(m["peak_drive_power_W"], p_star, rel_tol=1e-9)
    assert math.isclose(m["drive_power_peak_t_s"], t_star, abs_tol=1e-6)
    assert math.isclose(m["drive_power_min_W"], p_exit, rel_tol=1e-9)
    sampled = _track_rows(result)["drive_power_W"].to_numpy()
    assert sampled.max() < m["drive_power_peak_W"]  # the sampled maximum under-reads
    assert math.isclose(sampled.max(), p_star, rel_tol=1e-3)
    assert any(f.startswith("drive_braking") for f in result.flags)
    # Braking only: full thrust at 0.5 g0 net, F_drive < 0 throughout the push.
    braking = _silo(
        f9_vehicle,
        _hot_full(f9_vehicle),
        tight_settings,
        assist=_assist(a=0.5 * G0_MPS2, allow_negative=True),
    )
    bm = braking.metrics
    assert bm["drive_power_peak_W"] == 0.0 and math.copysign(1.0, bm["drive_power_peak_W"]) > 0
    assert bm["peak_drive_power_W"] == 0.0 and math.copysign(1.0, bm["peak_drive_power_W"]) > 0
    assert bm["drive_power_min_W"] < 0.0 and bm["drive_work_in_J"] == 0.0
    assert bm["drive_work_out_J"] > 0.0 and bm["drive_energy_J"] == -bm["drive_work_out_J"]
    assert bm["electrical_energy_J"] == 0.0


# ------------------------------------------------ exit-speed option (SP1 step 2)

V_EXIT_SET = 76.71
"""A configured exit speed [m/s]: the rounded exit speed of the 3 g0, 100 m silo."""
L_DEEP = 200.0
"""The stroke [m] the exit-speed runs use (twice the 3 g0 silo's, so about 1.5 g0 net)."""
HOT_ON_TRACK = IgnitionSpec(-1.0)
"""Lit 1 s before release, on the track: the ramp start is resolved against the push
time, so the hot run also exercises t_push = 2 L / v."""


def _same_value(x: object, y: object) -> bool:
    """Equality of two metric values, a NaN equal to a NaN (n/a in both runs)."""
    if isinstance(x, float) and isinstance(y, float) and math.isnan(x) and math.isnan(y):
        return True
    return bool(x == y)


def _silo_from_config(
    push: dict[str, float],
    vehicle: Vehicle,
    ignition: IgnitionSpec,
    settings: IntegratorSettings,
) -> sim.Result:
    """A buried vertical silo of L_DEEP built from a validated ConstantAccelConfig whose
    push is stated by ``push`` (``net_accel_g`` or ``exit_speed_mps``), through
    ``assist.build_assist`` (the path of ``sim.run``), under mu/r^2."""
    cfg = ConstantAccelConfig.model_validate(
        {
            "model": "constant_accel",
            "stroke_m": L_DEEP,
            "brake_decel_g": A_BRAKE / G0_MPS2,
            "drive_efficiency": ETA,
            **push,
        }
    )
    assist, track = build_assist(cfg, G_EFF)
    assert track is not None and track.length_m == L_DEEP and track.start_altitude_m == -L_DEEP
    specs = {name: IgnitionSpec() for name in vehicle.stage_names}
    specs[vehicle.stage_names[0]] = ignition
    return sim.simulate(
        vehicle=vehicle,
        ignition=specs,
        gravity=InverseSquareGravity(MU_EARTH_M3S2),
        g_eff_mps2=G_EFF,
        assist=assist,
        track=track,
        start=None,
        end="stage1_burnout",
        settings=settings,
    )


def test_exit_speed_push_closed_forms(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """A cold push stated by its exit speed v over the stroke L (a = v^2 / (2 L), never
    taken from the code): the integrated exit speed is v and the push time 2 L / v; at
    every sample s = v^2 t^2 / (4 L) and sdot = v^2 t / (2 L); the felt axial
    acceleration is v^2 / (2 L) + g_eff and the drive force M (v^2 / (2 L) + g_eff);
    the drive energy is the kinetic plus potential energy gained, M (v^2 / 2 + g_eff L),
    which does not depend on how the push is stated; the peak power is F_drive v at
    release; braking v^2 / (2 a_brake) and the facility L + that. The 1-D metrics gain
    no key."""
    v, length = V_EXIT_SET, L_DEEP
    result = _silo_from_config({"exit_speed_mps": v}, f9_vehicle, COLD, tight_settings)
    assert result.status == "nominal" and result.flags == []
    m = result.metrics
    t_push = 2.0 * length / v
    assert math.isclose(m["exit_speed_mps"], v, rel_tol=REL)
    assert math.isclose(m["speed_at_release_mps"], v, rel_tol=REL)
    assert math.isclose(m["push_time_s"], t_push, rel_tol=REL)
    assert math.isclose(m["t_release_s"], t_push, rel_tol=REL)
    assert m["alt_at_release_m"] == 0.0 and m["track_start_altitude_m"] == -length
    rows = _track_rows(result)
    t = rows["t_s"].to_numpy()
    assert t[0] == 0.0 and math.isclose(t[-1], t_push, rel_tol=REL)
    s_closed = v * v * t * t / (4.0 * length)
    np.testing.assert_allclose(rows["s_m"].to_numpy(), s_closed, rtol=REL, atol=REL * length)
    np.testing.assert_allclose(
        rows["v_mps"].to_numpy(), v * v * t / (2.0 * length), rtol=REL, atol=REL * v
    )
    m0 = f9_vehicle.liftoff_mass_kg()
    felt = v * v / (2.0 * length) + G_EFF
    assert math.isclose(m["felt_g_track_peak"], felt / G0_MPS2, rel_tol=REL)
    np.testing.assert_allclose(rows["drive_force_N"].to_numpy(), m0 * felt, rtol=REL)
    assert math.isclose(m["interface_force_peak_N"], m0 * felt, rel_tol=REL)
    assert math.isclose(m["drive_energy_J"], m0 * (0.5 * v * v + G_EFF * length), rel_tol=REL)
    assert math.isclose(m["drive_power_peak_W"], m0 * felt * v, rel_tol=REL)
    assert math.isclose(m["braking_distance_m"], v * v / (2.0 * A_BRAKE), rel_tol=REL)
    assert math.isclose(m["facility_length_m"], length + v * v / (2.0 * A_BRAKE), rel_tol=REL)
    # About half the 3 g0 silo's net acceleration at the same exit speed: the lower felt
    # g that the deeper silo is for (hand number, a cross-check of the constants only).
    assert abs(felt / G0_MPS2 - 2.4993) < 1e-4
    assert not {"net_accel_g", "net_accel_mps2", "stroke_m"} & set(m)


def test_exit_speed_vertical_1d_run_from_the_experiment_file(
    repo_root: Path, f9_vehicle_dict: dict[str, Any]
) -> None:
    """The option works on the 1-D model end to end, from the experiment dict through
    resolve_experiment and sim.run_resolved (the path of the ``run`` command): the
    shipped silo_screening_1d with a variant restating silo_cold's push by its exit
    speed v over a deeper stroke L releases at v after 2 L / v (closed forms), with the
    exit-speed assumption line and no push-setting metric (those are planar only). The
    shipped file is read, never written."""
    exp = yaml.safe_load(
        (repo_root / "experiments" / "silo_screening_1d.yaml").read_text(encoding="utf-8")
    )
    v, length = V_EXIT_SET, L_DEEP
    silo = {k: x for k, x in exp["variants"]["silo_cold"]["assist"].items() if k != "net_accel_g"}
    exp["variants"] = {
        "silo_by_speed": {
            "assist": {**silo, "exit_speed_mps": v, "stroke_m": length},
            "ignition": exp["variants"]["silo_cold"]["ignition"],
        }
    }
    for key in ("sweeps", "sensitivity"):
        exp.pop(key, None)
    run = resolve_experiment(exp, f9_vehicle_dict).variants["silo_by_speed"]
    assert run.run.dynamics == "vertical_1d" and "net_accel_g" not in run.run_dict["assist"]
    result = sim.run_resolved(run).result
    assert result.status == "nominal" and result.flags == []
    m = result.metrics
    assert math.isclose(m["exit_speed_mps"], v, rel_tol=REL)
    assert math.isclose(m["push_time_s"], 2.0 * length / v, rel_tol=REL)
    assert m["track_start_altitude_m"] == -length
    assert not {"net_accel_g", "net_accel_mps2", "stroke_m"} & set(m)
    derived = [line for line in result.assumptions if "configured exit speed" in line]
    assert derived == [
        "constant_accel: the net acceleration is derived from the configured exit speed "
        "76.71 m/s (assumed) and the track length L, a = v_exit^2 / (2 L); the push time is "
        "2 L / v_exit"
    ]


@pytest.mark.parametrize("ignition", [COLD, HOT_ON_TRACK], ids=["cold", "hot_on_track"])
def test_exit_speed_run_is_the_equivalent_net_accel_run(
    ignition: IgnitionSpec, f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """The run stated by exit speed v over L and the run stated by net_accel_g =
    v^2 / (2 g0 L) fly the same trajectory, cold and with the ramp started on the track
    (the hot run burns propellant on the push, so its thrust schedule depends on the
    push time). For this (v, L) the two accelerations, v^2 / (2 L) and (v^2 / (2 g0 L))
    g0, are the same double (asserted first), so the dynamics, which see only the
    acceleration, must give identical time series, events and metrics, compared
    exactly: any dependence on how the push is stated would show. Their assumptions
    differ by exactly the one line that names the configured exit speed, placed after
    the net-acceleration line; the run stated by its acceleration has no such line."""
    v, length = V_EXIT_SET, L_DEEP
    accel_g = v * v / (2.0 * G0_MPS2 * length)
    assert v * v / (2.0 * length) == accel_g * G0_MPS2  # the precondition of an exact test
    by_speed = _silo_from_config({"exit_speed_mps": v}, f9_vehicle, ignition, tight_settings)
    by_accel = _silo_from_config({"net_accel_g": accel_g}, f9_vehicle, ignition, tight_settings)
    assert by_speed.status == by_accel.status == "nominal"
    assert by_speed.flags == by_accel.flags == []
    assert len(by_speed.timeseries) > 10 and len(by_speed.events) > 3
    pd.testing.assert_frame_equal(by_speed.timeseries, by_accel.timeseries, check_exact=True)
    pd.testing.assert_frame_equal(by_speed.events, by_accel.events, check_exact=True)
    assert list(by_speed.metrics) == list(by_accel.metrics)
    differ = [
        key
        for key, value in by_speed.metrics.items()
        if not _same_value(value, by_accel.metrics[key])
    ]
    assert differ == []
    if ignition is HOT_ON_TRACK:
        assert by_speed.metrics["propellant_burned_on_track_kg"] > 0.0
        t_ign = by_speed.metrics["t_ign_rel_release_s_stage1"]
        assert math.isclose(t_ign, -1.0, abs_tol=1e-12)
    lines, plain = list(by_speed.assumptions), list(by_accel.assumptions)
    extra = [line for line in lines if line not in plain]
    assert len(extra) == 1 and len(lines) == len(plain) + 1
    assert extra[0].startswith("constant_accel: the net acceleration is derived from")
    assert f"exit speed {v:g} m/s" in extra[0] and "v_exit^2 / (2 L)" in extra[0]
    k = lines.index(extra[0])
    assert lines[k - 1].startswith("constant_accel: prescribed net acceleration")
    assert lines[:k] + lines[k + 1 :] == plain
    assert not [line for line in plain if "exit speed" in line]


def test_net_accel_assumptions_keep_their_phase_1_text() -> None:
    """A model built without a configured exit speed (every run stated by net_accel_g)
    emits the Phase 1 lines, written out here: nine of them, the first with the
    acceleration in g0, none naming an exit speed. With a configured exit speed the
    same nine plus one, second in the list; a non-positive or non-finite one is
    refused."""
    lines = _assist().assumptions()
    assert lines == (
        "constant_accel: prescribed net acceleration 3 g0 (assumed); drive force "
        "unconstrained, solved from the track equation",
        "constant_accel: carriage mass 0 t (assumed)",
        "constant_accel: braking deceleration 5 g0 (assumed)",
        "constant_accel: drive efficiency 0.5 (assumed)",
        "constant_accel: exhaust impingement fraction 0 (assumed); the system keeps "
        "(1 - f_imp) T of the on-track thrust",
        "constant_accel: shaft vented (no air column), no friction",
        f"constant_accel: constant g_eff = {G_EFF:.7g} m/s^2 on the track, omega_p = 0, "
        "Coriolis neglected",
        "constant_accel: infinite jerk at push start and release",
        "constant_accel: vehicle clamped to the carriage during any hold before the push",
    )
    with_speed = ConstantAccelAssist(
        net_accel_mps2=A,
        carriage_mass_kg=0.0,
        brake_decel_mps2=A_BRAKE,
        efficiency=ETA,
        g_eff_mps2=G_EFF,
        exit_speed_input_mps=V_EXIT_SET,
    ).assumptions()
    assert len(with_speed) == len(lines) + 1
    assert with_speed[0] == lines[0] and with_speed[2:] == lines[1:]
    assert with_speed[1] == (
        "constant_accel: the net acceleration is derived from the configured exit speed "
        "76.71 m/s (assumed) and the track length L, a = v_exit^2 / (2 L); the push time is "
        "2 L / v_exit"
    )
    for bad in (0.0, -1.0, math.inf, math.nan):
        with pytest.raises(ValueError, match="exit_speed_input_mps"):
            ConstantAccelAssist(
                net_accel_mps2=A,
                carriage_mass_kg=0.0,
                brake_decel_mps2=A_BRAKE,
                exit_speed_input_mps=bad,
            )


# ------------------------------------- ramp start by depth, speed and height (SP1 step 3)

T_PUSH = math.sqrt(2.0 * L / A)
"""Push time of the 3 g0, 100 m silo [s] (2.60732 s)."""
V_E = math.sqrt(2.0 * A * L)
"""Exit speed of the same silo [m/s] (76.70717 m/s)."""
TRACK = StraightTrack(L, VERTICAL, -L)
"""The buried vertical silo of ``_silo``: start at z = -L, mouth (track exit) at z = 0."""
EVENT_ABS_M = 1e-9
"""Tolerance of an ignition event's altitude [m], speed [m/s] and time [s] against its
closed form (SP1 step 3 gate: 1e-9)."""
RAMP = Startup("ramp", t_ramp_s=2.0)


def _resolve(block: dict[str, Any], g_eff: float = G_EFF, **kw: Any) -> IgnitionSpec:
    """resolve_ignition of an ignition block on the 3 g0, 100 m silo (``_assist`` and
    TRACK unless given) with the 2 s ramp as the stage's own startup."""
    assist = kw.get("assist", _assist())
    track = kw.get("track", TRACK)
    return resolve_ignition(IgnitionConfig.model_validate(block), RAMP, assist, track, g_eff)


def _height_dt(h: float, g: float = G_EFF) -> float:
    """Time after release [s] at which a drag-free coast at constant g from the mouth at
    V_E reaches the height h [m] on the way up: the smaller root of V_E t - g t^2/2 = h."""
    return (V_E - math.sqrt(V_E * V_E - 2.0 * g * h)) / g


def _ignition_row(result: sim.Result) -> pd.Series:
    """The stage-1 ignition row of a 1-D run's events."""
    rows = result.events[
        (result.events["event"] == "ignition") & (result.events["stage"] == "stage1")
    ]
    assert len(rows) == 1
    return rows.iloc[0]


@pytest.mark.parametrize("depth", [L, 75.0, 50.0, 25.0, 1e-3])
def test_resolve_depth_is_the_time_from_push_start_to_that_depth(depth: float) -> None:
    """at_depth_m d below the mouth: the push from rest at a reaches s = L - d at
    t = sqrt(2 (L - d) / a) after push start, so the spec is (that t, push_start) and
    records the request; d = L is the push start itself (t = 0)."""
    spec = _resolve({"at_depth_m": depth})
    assert spec.reference == "push_start"
    assert math.isclose(spec.t_ign_s, math.sqrt(2.0 * (L - depth) / A), rel_tol=1e-15, abs_tol=0.0)
    assert (spec.trigger_kind, spec.trigger_value) == ("depth", depth)
    assert spec.startup is None and not spec.fails


@pytest.mark.parametrize("speed", [0.0, 10.0, 30.0, 54.24, 76.0])
def test_resolve_speed_is_the_time_from_push_start_to_that_speed(speed: float) -> None:
    """at_speed_mps v on the push: sdot = a t, so t = v / a after push start."""
    spec = _resolve({"at_speed_mps": speed})
    assert spec.reference == "push_start"
    assert math.isclose(spec.t_ign_s, speed / A, rel_tol=1e-15, abs_tol=0.0)
    assert (spec.trigger_kind, spec.trigger_value) == ("speed", speed)


@pytest.mark.parametrize("height", [5.0, 40.0, 200.0, 299.0])
def test_resolve_closed_form_height_is_the_drag_free_coast_time(height: float) -> None:
    """at_height_m h, closed form: the smaller root of V_E t - g_eff t^2/2 = h after
    release, with g_eff the track's constant (here mu/R_E^2; any g_eff passed in)."""
    block = {"at_height_m": height, "height_method": "closed_form"}
    for g in (G_EFF, 9.7720917):
        spec = _resolve(block, g_eff=g)
        assert spec.reference == "release"
        assert math.isclose(spec.t_ign_s, _height_dt(height, g), rel_tol=1e-12)
        assert (spec.trigger_kind, spec.trigger_value) == ("height_closed_form", height)


def test_resolve_snaps_a_start_at_the_release_and_refuses_what_the_push_cannot_reach() -> None:
    """A conversion within ZERO_SPAN_S (1e-12 s) of the release snaps to (0, release):
    depth 0, the exit speed itself and a speed a rounding above it. A speed whose time
    lies further after the release (v > v_exit), a depth below the push start, a height
    at or above the drag-free apex V_E^2 / (2 g_eff), a height with g_eff <= 0 and a
    height reached by an event (SP1 step 4) are refused."""
    for block in ({"at_depth_m": 0.0}, {"at_speed_mps": V_E}, {"at_speed_mps": V_E * (1 + 1e-15)}):
        spec = _resolve(block)
        assert (spec.t_ign_s, spec.reference) == (0.0, "release"), block
        assert spec.trigger_kind != "time"
    with pytest.raises(ValueError, match=r"exceeds the exit speed 76\.70717"):
        _resolve({"at_speed_mps": V_E * (1 + 1e-9)})
    with pytest.raises(ValueError, match=r"at_depth_m 100\.001 m is deeper than the track"):
        _resolve({"at_depth_m": 100.001})
    apex = V_E * V_E / (2.0 * G_EFF)
    for height in (apex, 1.01 * apex):
        with pytest.raises(ValueError, match="at or above the drag-free apex"):
            _resolve({"at_height_m": height, "height_method": "closed_form"})
    with pytest.raises(ValueError, match="needs g_eff > 0"):
        _resolve({"at_height_m": 40.0, "height_method": "closed_form"}, g_eff=0.0)
    event = IgnitionConfig.model_construct(at_height_m=40.0, height_method="event")
    with pytest.raises(ValueError, match="arrives in SP1 step 4"):
        resolve_ignition(event, RAMP, _assist(), TRACK, G_EFF)


def test_resolve_needs_the_constant_accel_drive_and_leaves_time_specs_alone() -> None:
    """A depth, speed or height needs the constant_accel drive and its track (a pad's
    NoAssist, no model or no track is refused, naming the key); a time-stated config
    gives IgnitionSpec.from_config unchanged on any model, with the time trigger."""
    for block in (
        {"at_depth_m": 50.0},
        {"at_speed_mps": 30.0},
        {"at_height_m": 40.0, "height_method": "closed_form"},
    ):
        for assist, track in ((sim.NoAssist(), None), (None, None), (_assist(), None)):
            with pytest.raises(ValueError, match="needs the constant_accel drive"):
                _resolve(block, assist=assist, track=track)
    for block in ({}, {"t_ign_s": -2.0}, {"t_ign_s": -2.0, "reference": "push_start"}):
        cfg = IgnitionConfig.model_validate(block)
        for assist, track in ((sim.NoAssist(), None), (_assist(), TRACK)):
            spec = resolve_ignition(cfg, RAMP, assist, track, G_EFF)
            assert spec == IgnitionSpec.from_config(cfg, RAMP)
            assert (spec.trigger_kind, spec.trigger_value) == ("time", None)


def test_ignition_spec_trigger_defaults_keep_every_time_spec_as_it_was() -> None:
    """The two new IgnitionSpec fields default to the time trigger, so every existing
    construction is equal to, and hashes like, the same spec written with them; a
    non-time trigger needs its value and the time trigger none; an unknown kind is
    refused."""
    for spec in (IgnitionSpec(), IgnitionSpec(0.5), IgnitionSpec(-2.0, "push_start", RAMP, True)):
        full = IgnitionSpec(spec.t_ign_s, spec.reference, spec.startup, spec.fails, "time", None)
        assert spec == full and hash(spec) == hash(full)
    with pytest.raises(ValueError, match="trigger_value"):
        IgnitionSpec(1.0, "push_start", trigger_kind="depth")
    with pytest.raises(ValueError, match="trigger_value"):
        IgnitionSpec(trigger_value=50.0)
    with pytest.raises(ValueError, match="trigger_kind"):
        IgnitionSpec(trigger_kind="altitude", trigger_value=1.0)


@pytest.mark.parametrize("depth", [L, 75.0, 50.0, 10.0])
def test_one_d_ignition_event_lies_at_the_requested_depth(
    depth: float, f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """On the vertical_1d model the stage-1 ignition event of a ramp start by depth d
    lies on the push at z = z_mouth - d = -d, at the speed sqrt(2 a (L - d)) and the time
    sqrt(2 (L - d) / a) after push start, all at 1e-9 (closed forms written here); the
    run carries no ramp-start metric (1-D keeps its metric keys)."""
    result = _silo(f9_vehicle, _resolve({"at_depth_m": depth}), tight_settings)
    row = _ignition_row(result)
    assert row["phase"] == ASSIST_KIND
    assert abs(float(row["z_m"]) - (0.0 - depth)) < EVENT_ABS_M
    assert abs(float(row["v_mps"]) - math.sqrt(2.0 * A * (L - depth))) < EVENT_ABS_M
    assert abs(float(row["t_s"]) - math.sqrt(2.0 * (L - depth) / A)) < EVENT_ABS_M
    assert not [k for k in result.metrics if k.startswith("ramp_start")]


@pytest.mark.parametrize("speed", [0.0, 20.0, 54.24, 70.0])
def test_one_d_ignition_event_lies_at_the_requested_speed(
    speed: float, f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """On the vertical_1d model the ignition event of a ramp start by speed v lies on
    the push at speed v, at z = -L + v^2 / (2 a) and at t = v / a, all at 1e-9."""
    result = _silo(f9_vehicle, _resolve({"at_speed_mps": speed}), tight_settings)
    row = _ignition_row(result)
    assert row["phase"] == ASSIST_KIND
    assert abs(float(row["v_mps"]) - speed) < EVENT_ABS_M
    assert abs(float(row["z_m"]) - (-L + speed * speed / (2.0 * A))) < EVENT_ABS_M
    assert abs(float(row["t_s"]) - speed / A) < EVENT_ABS_M


@pytest.mark.parametrize("height", [5.0, 40.0, 200.0])
def test_one_d_closed_form_height_is_exact_under_constant_gravity(
    height: float, f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """With an injected ConstantGravity equal to the track's g_eff and no drag (the 1-D
    model has no atmosphere), the coast after release is the drag-free constant-g coast
    the closed form assumes, so the ignition event lies exactly at the requested height
    h above the mouth: z = h, v = sqrt(V_E^2 - 2 g h) and t - t_release = the smaller
    root of V_E t - g t^2/2 = h, all at 1e-9."""
    specs = {name: IgnitionSpec() for name in f9_vehicle.stage_names}
    specs["stage1"] = _resolve({"at_height_m": height, "height_method": "closed_form"})
    result = sim.simulate(
        vehicle=f9_vehicle,
        ignition=specs,
        gravity=ConstantGravity(G_EFF),
        g_eff_mps2=G_EFF,
        assist=_assist(),
        track=TRACK,
        start=None,
        end="stage1_burnout",
        settings=tight_settings,
    )
    row = _ignition_row(result)
    assert row["phase"] == "BURN"
    assert abs(float(row["z_m"]) - height) < EVENT_ABS_M
    assert abs(float(row["v_mps"]) - math.sqrt(V_E * V_E - 2.0 * G_EFF * height)) < EVENT_ABS_M
    t_rel = float(row["t_s"]) - result.metrics["t_release_s"]
    assert abs(t_rel - _height_dt(height)) < EVENT_ABS_M


RAISED_MOUTH_M = 30.0
"""Altitude [m] of a raised track exit (silo mouth) above the datum: the depth and the
height count from the mouth, not from the datum."""


def test_one_d_depth_and_height_count_from_a_raised_mouth(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """With the mouth RAISED_MOUTH_M above the datum (track start at z = z_m - L), a
    ramp start at depth 50 lights on the push at z = z_m - 50 with speed sqrt(2 a (L -
    50)), and a closed-form height 40 under an injected ConstantGravity lights at z =
    z_m + 40 with speed sqrt(V_E^2 - 2 g 40), at the closed-form time after release, all
    at 1e-9: a resolver or event that measured from the datum would miss by z_m."""
    z_m = RAISED_MOUTH_M
    track = StraightTrack(L, VERTICAL, z_m - L)

    def flown(block: dict[str, Any], gravity: Any) -> sim.Result:
        specs = {name: IgnitionSpec() for name in f9_vehicle.stage_names}
        specs["stage1"] = _resolve(block, track=track)
        return sim.simulate(
            vehicle=f9_vehicle,
            ignition=specs,
            gravity=gravity,
            g_eff_mps2=G_EFF,
            assist=_assist(),
            track=track,
            start=None,
            end="stage1_burnout",
            settings=tight_settings,
        )

    by_depth = flown({"at_depth_m": 50.0}, InverseSquareGravity(MU_EARTH_M3S2))
    row = _ignition_row(by_depth)
    assert row["phase"] == ASSIST_KIND
    assert abs(float(row["z_m"]) - (z_m - 50.0)) < EVENT_ABS_M
    assert abs(float(row["v_mps"]) - math.sqrt(2.0 * A * (L - 50.0))) < EVENT_ABS_M
    by_height = flown({"at_height_m": 40.0, "height_method": "closed_form"}, ConstantGravity(G_EFF))
    row = _ignition_row(by_height)
    assert row["phase"] == "BURN"
    assert abs(float(row["z_m"]) - (z_m + 40.0)) < EVENT_ABS_M
    assert abs(float(row["v_mps"]) - math.sqrt(V_E * V_E - 2.0 * G_EFF * 40.0)) < EVENT_ABS_M
    t_rel = float(row["t_s"]) - by_height.metrics["t_release_s"]
    assert abs(t_rel - _height_dt(40.0)) < EVENT_ABS_M


def test_a_later_stage_ramp_start_is_refused_where_the_specs_are_built(
    repo_root: Path, f9_vehicle_dict: dict[str, Any], f9_vehicle: Vehicle
) -> None:
    """A ramp start by depth, speed or height on stage 2 is refused by resolve_run, and
    also where the specs are built (``phases.prelude.resolve_stage_ignitions``), so a
    RunConfig validated without resolve_run and handed to sim.run is refused before
    anything is integrated (a closed-form height would otherwise convert with stage 1's
    exit speed and fly as a silent staging-coast delay). IgnitionSpec.from_config
    refuses every non-time config, which only resolve_ignition can convert."""
    exp = yaml.safe_load(
        (repo_root / "experiments" / "silo_screening_1d.yaml").read_text(encoding="utf-8")
    )
    for key in ("sweeps", "sensitivity"):
        exp.pop(key, None)
    run_dict = resolve_experiment(exp, f9_vehicle_dict).variants["silo_cold"].run_dict
    blocks = {
        "at_depth_m": {"at_depth_m": 50.0},
        "at_speed_mps": {"at_speed_mps": 30.0},
        "at_height_m": {"at_height_m": 40.0, "height_method": "closed_form"},
    }
    for key, block in blocks.items():
        bad = copy.deepcopy(run_dict)
        bad["ignition"]["stage2"] = block
        refusal = rf"ignition stage2: a ramp start by {key} is only for the first stage"
        with pytest.raises(ValueError, match=refusal):
            resolve_run("bad", bad, f9_vehicle_dict)
        cfg = RunConfig.model_validate(bad)
        with pytest.raises(ValueError, match=refusal):
            sim.run(cfg, f9_vehicle)
        with pytest.raises(ValueError, match=refusal):
            sim.run_ignition_specs(cfg, f9_vehicle)
        with pytest.raises(
            ValueError, match=rf"stated by {key} is converted by .*resolve_ignition"
        ):
            IgnitionSpec.from_config(IgnitionConfig.model_validate(block), RAMP)


def test_one_d_depth_run_is_the_converted_time_run(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """A ramp start by depth is converted before the run and nothing else changes: the
    run stated by at_depth_m 50 and the run stated by t_ign_s = sqrt(2 (L - 50) / a)
    from push_start (computed here; the same double, asserted) have identical time
    series, events and metrics (keys and values); the assumptions differ by exactly the
    one ramp-start line, which names the depth and the converted time."""
    depth = 50.0
    t = math.sqrt(2.0 * (L - depth) / A)
    spec = _resolve({"at_depth_m": depth})
    assert spec.t_ign_s == t
    by_depth = _silo(f9_vehicle, spec, tight_settings)
    by_time = _silo(f9_vehicle, IgnitionSpec(t, "push_start", None), tight_settings)
    pd.testing.assert_frame_equal(by_depth.timeseries, by_time.timeseries, check_exact=True)
    pd.testing.assert_frame_equal(by_depth.events, by_time.events, check_exact=True)
    assert by_depth.metrics == by_time.metrics and list(by_depth.metrics) == list(by_time.metrics)
    extra = [line for line in by_depth.assumptions if line not in by_time.assumptions]
    assert len(by_depth.assumptions) == len(by_time.assumptions) + 1 and len(extra) == 1
    assert extra[0] == (
        f"ramp start: stage-1 ignition stated by depth 50 m below the track exit, converted "
        f"before the run to t_ign = {t:.9g} s after push start by t = sqrt(2 (L - d) / a) "
        "(exact for the prescribed acceleration)"
    )


def test_failed_stage_flags_its_ramp_start_as_ignored(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """fails: true with a ramp start by depth: nothing burns, the depth is flagged as
    ignored by its key and value (not the t_ign_s and reference it was converted to),
    and no ramp-start assumption line is added."""
    spec = _resolve({"at_depth_m": 50.0, "fails": True})
    assert spec.fails and spec.trigger_kind == "depth"
    result = _silo(f9_vehicle, spec, tight_settings, end="impact")
    flags = [f for f in result.flags if f.startswith("ignition_failed")]
    assert flags == [
        "ignition_failed: stage 'stage1' has fails: true, so nothing burns; ignored: "
        "at_depth_m = 50"
    ]
    assert not [line for line in result.assumptions if line.startswith("ramp start")]
    assert "ignition" not in set(result.events["event"])
