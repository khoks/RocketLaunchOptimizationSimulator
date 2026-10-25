"""The linear motor (SP7 step S4; docs/physics.md, "Linear motor"; design 4.6).

Every closed-form expectation is computed here, never from the package; the metric,
identity and braking checks apply their definitions to the run's own exit speed, push
time and peaks. On the F9 (1-D, the push flown by ``prelude.fly_track`` or
``sim.simulate``), with M the stack
on the carriage (m_v + m_c), g = g_eff = mu/R_E^2, cold (constant M) unless stated:

- force law, vertical, the force rising from the holding force F_0 = M g over t_r:
  constant jerk j = (F_max - F_0)/(M t_r), sddot = j t, v = j t^2/2, s = j t^3/6; then
  the force phase a_f = F_max/M - g; then the power phase from v_c = P/F_max with
  v_inf = P/(M g): t - t_c = [(v_c - v) + v_inf ln((v_inf - v_c)/(v_inf - v))]/g and
  s - s_c = [(v_c^2 - v^2)/2 + v_inf (v_c - v) + v_inf^2 ln((v_inf - v_c)/(v_inf - v))]/g;
- force law, horizontal (phi = 0, F_0 = 0): the same rise and force phase with g = 0,
  then v^3 = v_c^3 + 3 P (s - s_c)/M and v^2 = v_c^2 + 2 P (t - t_c)/M;
- acceleration law a(t) = a_cmd min(1, t/t_r): v = a t^2/(2 t_r), s = a t^3/(6 t_r), then
  v = a (t - t_r/2), s = a (t - t_r/2)^2/2 + a t_r^2/24, so v_e^2 = 2 a L - a^2 t_r^2/12 and
  t_push = t_r/2 + v_e/a; a force cap F_max = M (a_F + g) binding at t_1 = t_r a_F/a_cmd
  (then sddot = a_F); a power cap binding at v_p = P/(M (a + g)) (then the power phase);
- the stop taper (position form) over s_t: with x = L - s, x'' = -(a/s_t) x, so
  v^2 = v_0^2 + (a/s_t)(s_t^2 - x^2), v_e^2 = v_0^2 + a s_t, and the time to L
  atan(s_t Omega/v_0)/Omega with Omega = sqrt(a/s_t), for both laws, at four taper
  lengths (cold, no power limit);
- F <= F_max and F sdot <= P_max (1 + 1e-12) at every sample;
- the assist energy identity (residual < 1e-9, CLAUDE.md 1e-6) cold, hot and ramped, and
  cold E_drive = M (v_e^2/2 + g L);
- the hot interface force on the force plateau F_int = (m_v/M) F_max - T (m_c + f_imp
  m_v)/M for f_imp 0, 0.5, 1; the hot rise from the holding force F_0 = M_0 g - (1 -
  f_imp) T (sddot(0) = 0);
- the sub-phases: the track peaks at a power corner inside the rise (F_lim(t_p)), a
  corner at the end of the rise logged once without a flag, no ramp_end on an unlit
  push, ``engine.fires_on_first_step`` against the disarm guard; a corner 0.5e-6 m
  short of L still released at L, a corner just beyond the exit speed leaving the force
  phase's exit exact, a force cap released in the taper (drive_cap_end, x'' =
  -(a_cmd/s_t) x after it), a power cap binding briefly across the taper start (the
  vertical power phase into the taper, released where M (a w(s) + g) v = P, then x'' =
  -(a/s_t) x; review pass 3), a power cap binding briefly inside a 90 m taper, inside
  one integrator step (found by the scan for passed-over crossings and flown: the
  harmonic taper to the need's crossing of P, the power phase, the release, the harmonic
  taper; review pass 1 rerun), a watch changing side a third time at one instant
  refused (RuntimeError) and the F9's ramp lit on the track at sea-level pressure, split
  where its T_vac reaches p_amb A_e (the thrust clamp: the burn's closed form with the
  mass M_i (1 - q^2 tau^2) on either side; review pass 2 rerun);
- the stall at push start (F_max + (1 - f_imp) T(0) <= M_0 g sin phi) and the refused
  release-referenced t_ign_s < 0 (the stall's felt g and interface-force metrics None,
  and no interface_tensile flag from its row on a hot stall);
  the pending ignition at t_release + t_ign_s (1-D and
  planar); braking d = v^2/(2 a_b), t = v/a_b, F = m_c (a_b - g sin phi), E = (1/2) m_c
  v^2 (1 - g sin phi / a_b), all 0 for m_c = 0; the config, the metrics and the
  assumption lines.

Closed forms at 1e-9 relative (positions and speeds at the integrator's own steps
relative to the stroke and the exit speed) with rtol 1e-11 (CLAUDE.md: <= 1e-9), and
at rtol 1e-10 too for the taper, the cases at the release, both brief power caps and
the thrust clamp (whose release time and exit speed are asserted to 1e-12,
``CLAMP_REL``).
"""

from __future__ import annotations

import math
from typing import Any, get_args

import numpy as np
import pytest
from pydantic import ValidationError
from scipy.optimize import brentq, minimize_scalar

from launchsim import appform, config, sim
from launchsim.assist import ASSIST_MODELS, build_assist
from launchsim.assist.constant_accel import ConstantAccelAssist
from launchsim.assist.linear_motor import CONTROL_LAWS, LinearMotorAssist, PushStart
from launchsim.assist.track import VERTICAL, StraightTrack
from launchsim.atmosphere import ambient_scalar
from launchsim.config import (
    ChecksConfig,
    LinearMotorConfig,
    RunConfig,
    SearchConfig,
    resolve_run,
)
from launchsim.constants import G0_MPS2, MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M
from launchsim.dynamics import InverseSquareGravity, track_observables
from launchsim.guidance import GuidanceSpec
from launchsim.metrics import (
    LINEAR_MOTOR_METRICS,
    STALL_UNAVAILABLE_TRACK_METRICS,
    track_flags,
)
from launchsim.phases import ASSIST_KIND, IgnitionSpec, IntegratorSettings, PhaseResult, RunTrace
from launchsim.phases.engine import (
    ZERO_SPAN_S,
    EventSpec,
    PhaseSpec,
    fires_on_first_step,
    integrate_phase,
)
from launchsim.phases.planar import PlanarEnvironment, PlanarPlanner
from launchsim.phases.prelude import (
    DRIVE_STALL,
    TrackExit,
    _WatchBook,
    fly_track,
    pending_until_release,
    push_boundaries,
    thrust_clamp_time,
)
from launchsim.phases.vertical import VerticalPlanner
from launchsim.search import SearchBudget
from launchsim.vehicle import Startup, ThrustSchedule, Vehicle

G = MU_EARTH_M3S2 / R_EARTH_M**2
"""The 1-D track's g_eff [m/s^2] (omega_p = 0)."""
L = 100.0
T_R = 0.5
A_BRAKE = 5.0 * G0_MPS2
ETA = 0.5
REL = 1e-9
LIMIT_REL = 1e-12
SETTINGS = IntegratorSettings(rtol=1e-11)
"""Closed-form settings: with every kink of the drive force split and every crossing
and the release flown to as a fixed end, the worst error at rtol 1e-11 is 2.3e-14
relative (the power corner inside the rise: its time and the peaks; every other case
1.02e-14 or better), so the 1e-9 assertions keep a margin above 4e4, with three offsets:
the corner at the end of the rise is asserted against the unperturbed t_r and v(t_r),
which its P = (1 +- 1e-12) F_max v(t_r) moves by up to 1e-12; the brief power cap at
delta = -1e-9 logs drive_cap 4.6e-13 late (armed guarded, it fires at the edge of its
zero band); and the brief power cap inside the taper logs its events within 7.8e-13
(crossings near tangency; its exit within 1.6e-15), margins of 1e3, 2e3 and 1e3; at rtol
1e-10, which the taper, the cases at the release and both brief power caps also run, the
worst of those is 7.8e-13 (measured by scratch probes, docs/physics.md "Linear motor",
Measured)."""
SILO = StraightTrack(L, VERTICAL, -L)
FLAT = StraightTrack(L, 0.0, 0.0)
COLD = IgnitionSpec(0.5)
"""Stage 1 0.5 s after the release: pending through the push, so the push is cold."""
HOT = IgnitionSpec(-2.0, reference="push_start")
"""Lit 2 s (the F9's own ramp) before the push start: full thrust on the whole push."""


def _model(
    control: str = "force",
    *,
    f_max: float,
    p_max: float,
    t_r: float = T_R,
    m_c: float = 0.0,
    a_cmd: float | None = None,
    taper: float | None = None,
    f_imp: float = 0.0,
) -> LinearMotorAssist:
    """A linear motor with the test's brake (5 g0) and efficiency (0.5)."""
    return LinearMotorAssist(
        control=control,
        force_max_N=f_max,
        power_max_W=p_max,
        rise_time_s=t_r,
        carriage_mass_kg=m_c,
        brake_decel_mps2=A_BRAKE,
        accel_command_mps2=a_cmd,
        stop_taper_m=taper,
        efficiency=ETA,
        f_imp=f_imp,
        g_eff_mps2=G,
    )


def _specs(vehicle: Vehicle, first: IgnitionSpec) -> dict[str, IgnitionSpec]:
    specs = {name: IgnitionSpec() for name in vehicle.stage_names}
    specs[vehicle.stage_names[0]] = first
    return specs


def _push(
    vehicle: Vehicle,
    model: LinearMotorAssist,
    track: StraightTrack = SILO,
    first: IgnitionSpec = COLD,
    settings: IntegratorSettings = SETTINGS,
    p_amb_pa: float = 0.0,
) -> tuple[TrackExit | None, RunTrace]:
    """The push alone: ``fly_track`` in the 1-D layout (no release map, so a horizontal
    track flies too), at the ambient pressure p_amb_pa [Pa] (0: vacuum thrust)."""
    planner = VerticalPlanner(
        vehicle,
        _specs(vehicle, first),
        InverseSquareGravity(MU_EARTH_M3S2),
        G,
        "stage1_burnout",
        settings,
    )
    tr = planner.new_builder()
    exit_ = fly_track(
        tr,
        model,
        track,
        first,
        vehicle=vehicle,
        settings=settings,
        g_eff_mps2=G,
        p_amb_pa=p_amb_pa,
    )
    return exit_, tr.finish()


def _simulate(
    vehicle: Vehicle,
    model: LinearMotorAssist | ConstantAccelAssist,
    first: IgnitionSpec = COLD,
    settings: IntegratorSettings = SETTINGS,
) -> sim.Result:
    """The 1-D run of the silo to stage-1 burnout."""
    return sim.simulate(
        vehicle=vehicle,
        ignition=_specs(vehicle, first),
        gravity=InverseSquareGravity(MU_EARTH_M3S2),
        g_eff_mps2=G,
        assist=model,
        track=SILO,
        start=None,
        end="stage1_burnout",
        settings=settings,
    )


def _points(trace: RunTrace) -> list[tuple[float, float, float, float, PhaseResult, np.ndarray]]:
    """(t, s, sdot, m_v, phase, state) at every integrator step of every ASSIST phase."""
    out = []
    for res in trace.assist_phases():
        lay = res.spec.params.layout
        for i, t in enumerate(res.t):
            y = np.asarray(res.y[:, i], dtype=float)
            out.append(
                (
                    float(t),
                    float(lay.get(y, "s_m")),
                    float(lay.get(y, "sdot_mps")),
                    float(lay.get(y, "m_kg")),
                    res,
                    y,
                )
            )
    return out


def _event(trace: RunTrace, name: str) -> tuple[float, float, float]:
    """(t [s], z [m], v [m/s]) of the one event called name (1-D view: z = start + s on
    the silo)."""
    found = [e for e in trace.events if e.name == name]
    assert len(found) == 1, (name, [e.name for e in trace.events])
    e = found[0]
    return e.t_s, e.value("z_m"), e.value("v_mps")


def _stage1(vehicle: Vehicle) -> tuple[float, float, float]:
    """(T_full [N], mdot [kg/s], m0 [kg]) of the first stage from the fixture."""
    stage = vehicle.stages[0]
    thrust = stage.n_engines * stage.engine.thrust_vac_N
    return thrust, thrust / (G0_MPS2 * stage.engine.isp_vac_s), vehicle.liftoff_mass_kg()


def _close(x: float, expected: float, scale: float) -> bool:
    """|x - expected| <= REL * scale (scale: the stroke or the exit speed)."""
    return abs(x - expected) <= REL * scale


def _power_phase(v: float, v_c: float, v_inf: float, g: float) -> tuple[float, float]:
    """(t - t_c, s - s_c) of the vertical power phase at speed v from the corner v_c."""
    log = math.log((v_inf - v_c) / (v_inf - v))
    dt = ((v_c - v) + v_inf * log) / g
    ds = (0.5 * (v_c * v_c - v * v) + v_inf * (v_c - v) + v_inf * v_inf * log) / g
    return dt, ds


# ------------------------------------------------------------------ the force law


@pytest.mark.parametrize("m_c", [0.0, 20_000.0])
def test_force_law_vertical_rise_force_and_power_phases(m_c: float, f9_vehicle: Vehicle) -> None:
    """Cold, vertical: the rise from the holding force F_0 = M g (constant jerk), the
    force phase and the power phase (v_c = 50 m/s) at every integrator step, at the
    drive_ramp_end and power_limit events and at the release; the drive force on the
    closed form at every step."""
    m = f9_vehicle.liftoff_mass_kg() + m_c
    f_max = m * (3.0 * G0_MPS2 + G)
    v_c = 50.0
    p_max = f_max * v_c
    exit_, trace = _push(f9_vehicle, _model(f_max=f_max, p_max=p_max, m_c=m_c))
    assert exit_ is not None and trace.status == "nominal" and trace.flags == ()
    j = (f_max - m * G) / (m * T_R)
    a_f = j * T_R
    v_r, s_r = j * T_R**2 / 2.0, j * T_R**3 / 6.0
    t_c = T_R + (v_c - v_r) / a_f
    s_c = s_r + (v_c**2 - v_r**2) / (2.0 * a_f)
    v_inf = p_max / (m * G)
    v_e = brentq(lambda v: s_c + _power_phase(v, v_c, v_inf, G)[1] - L, v_c, v_inf * (1 - 1e-12))
    t_e = t_c + _power_phase(v_e, v_c, v_inf, G)[0]
    assert math.isclose(exit_.sdot_mps, v_e, rel_tol=REL)
    assert math.isclose(exit_.t_release_s, t_e, rel_tol=REL)
    t, z, v = _event(trace, "drive_ramp_end")
    assert t == T_R and math.isclose(z + L, s_r, rel_tol=REL) and math.isclose(v, v_r, rel_tol=REL)
    t, z, v = _event(trace, "power_limit")
    assert math.isclose(t, t_c, rel_tol=REL) and math.isclose(v, v_c, rel_tol=REL)
    assert math.isclose(z + L, s_c, rel_tol=REL)
    phases = {0: 0, 1: 0, 2: 0}
    for t, s, sdot, _m, res, y in _points(trace):
        force = res.spec.params.forces(t, y).drive_force_N
        if t <= T_R:
            phases[0] += 1
            assert _close(sdot, j * t * t / 2.0, v_e) and _close(s, j * t**3 / 6.0, L)
            assert math.isclose(force, m * G + (f_max - m * G) * t / T_R, rel_tol=REL)
        elif sdot <= v_c:
            phases[1] += 1
            u = t - T_R
            assert _close(sdot, v_r + a_f * u, v_e) and _close(
                s, s_r + v_r * u + a_f * u * u / 2, L
            )
            assert force == f_max
        else:
            phases[2] += 1
            dt, ds = _power_phase(sdot, v_c, v_inf, G)
            assert _close(t, t_c + dt, t_e) and _close(s, s_c + ds, L)
            assert math.isclose(force, p_max / sdot, rel_tol=1e-15)
    assert min(phases.values()) >= 2, phases


def test_force_law_horizontal_on_an_injected_track(f9_vehicle: Vehicle) -> None:
    """phi = 0: F_0 = 0, the rise j = F_max/(M t_r), a = F_max/M, then the power phase
    v^3 = v_c^3 + 3 P (s - s_c)/M and v^2 = v_c^2 + 2 P (t - t_c)/M (no gravity along the
    track), at every step and at the release; the normal load is the weight."""
    m = f9_vehicle.liftoff_mass_kg()
    f_max = m * 3.0 * G0_MPS2
    v_c = 40.0
    p_max = f_max * v_c
    exit_, trace = _push(f9_vehicle, _model(f_max=f_max, p_max=p_max), track=FLAT)
    assert exit_ is not None and trace.flags == ()
    j = f_max / (m * T_R)
    a_f = j * T_R
    v_r, s_r = j * T_R**2 / 2.0, j * T_R**3 / 6.0
    t_c = T_R + (v_c - v_r) / a_f
    s_c = s_r + (v_c**2 - v_r**2) / (2.0 * a_f)
    v_e = (v_c**3 + 3.0 * p_max * (L - s_c) / m) ** (1.0 / 3.0)
    t_e = t_c + m * (v_e**2 - v_c**2) / (2.0 * p_max)
    assert math.isclose(exit_.sdot_mps, v_e, rel_tol=REL)
    assert math.isclose(exit_.t_release_s, t_e, rel_tol=REL)
    assert exit_.phi_rad == 0.0
    power = 0
    for t, s, sdot, _m, res, y in _points(trace):
        if t <= T_R:
            assert _close(sdot, j * t * t / 2.0, v_e) and _close(s, j * t**3 / 6.0, L)
        elif sdot <= v_c:
            u = t - T_R
            assert _close(sdot, v_r + a_f * u, v_e) and _close(
                s, s_r + v_r * u + a_f * u * u / 2, L
            )
        else:
            power += 1
            assert _close(sdot, (v_c**3 + 3.0 * p_max * (s - s_c) / m) ** (1.0 / 3.0), v_e)
            assert _close(sdot, math.sqrt(v_c**2 + 2.0 * p_max * (t - t_c) / m), v_e)
        obs = track_observables(t, y, res.spec.params)
        assert math.isclose(obs["N_vehicle_g"], G / G0_MPS2, rel_tol=1e-15)
    assert power >= 2


# ----------------------------------------------------------- the acceleration law


def _accel_forms(a: float, t: float) -> tuple[float, float]:
    """(v, s) of the jerk-limited command a(t) = a min(1, t/T_R) from rest."""
    if t <= T_R:
        return a * t * t / (2.0 * T_R), a * t**3 / (6.0 * T_R)
    u = t - T_R / 2.0
    return a * u, a * u * u / 2.0 + a * T_R**2 / 24.0


def test_acceleration_law_jerk_ramp_and_plateau(f9_vehicle: Vehicle) -> None:
    """No cap binds (F_max twice the need, P_max far above it): v = a t^2/(2 t_r),
    s = a t^3/(6 t_r), then v = a (t - t_r/2), s = a (t - t_r/2)^2/2 + a t_r^2/24 at every
    step; v_e^2 = 2 a L - a^2 t_r^2/12 and t_push = t_r/2 + v_e/a at release, which the
    bound model's push-time estimate equals here (no cap, no taper); no drive_cap or
    power_limit event; felt g on the plateau (a + g)/g0."""
    m = f9_vehicle.liftoff_mass_kg()
    a = 3.0 * G0_MPS2
    f_max = 2.0 * m * (a + G)
    model = _model("acceleration", f_max=f_max, p_max=f_max * 1e3, a_cmd=a)
    exit_, trace = _push(f9_vehicle, model)
    assert exit_ is not None and trace.flags == ()
    v_e = math.sqrt(2.0 * a * L - a * a * T_R**2 / 12.0)
    t_e = T_R / 2.0 + v_e / a
    assert math.isclose(exit_.sdot_mps, v_e, rel_tol=REL)
    assert math.isclose(exit_.t_release_s, t_e, rel_tol=REL)
    names = [e.name for e in trace.events]
    assert "drive_cap" not in names and "power_limit" not in names
    assert names.count("drive_ramp_end") == 1
    bound = model.at_push_start(m, 0.0, G, SILO)
    assert math.isclose(bound.push_time_estimate(SILO), t_e, rel_tol=1e-12)
    for t, s, sdot, _m, res, y in _points(trace):
        v_cf, s_cf = _accel_forms(a, t)
        assert _close(sdot, v_cf, v_e) and _close(s, s_cf, L)
        if t >= T_R:
            felt = track_observables(t, y, res.spec.params)["felt_g"]
            assert math.isclose(felt, (a + G) / G0_MPS2, rel_tol=1e-12)


def test_acceleration_law_force_cap_binds(f9_vehicle: Vehicle) -> None:
    """a_cmd = 4 g0 with F_max = M (3 g0 + g): the cap binds at t_1 = t_r a_F/a_cmd
    (a drive_cap event there, inside the rise), after which sddot = a_F = 3 g0: v = v_1 +
    a_F (t - t_1), v_e^2 = v_1^2 + 2 a_F (L - s_1)."""
    m = f9_vehicle.liftoff_mass_kg()
    a_cmd, a_f = 4.0 * G0_MPS2, 3.0 * G0_MPS2
    f_max = m * (a_f + G)
    model = _model("acceleration", f_max=f_max, p_max=f_max * 1e3, a_cmd=a_cmd)
    exit_, trace = _push(f9_vehicle, model)
    assert exit_ is not None and trace.flags == ()
    t_1 = T_R * a_f / a_cmd
    v_1, s_1 = a_cmd * t_1**2 / (2.0 * T_R), a_cmd * t_1**3 / (6.0 * T_R)
    v_e = math.sqrt(v_1**2 + 2.0 * a_f * (L - s_1))
    assert math.isclose(exit_.sdot_mps, v_e, rel_tol=REL)
    assert math.isclose(exit_.t_release_s, t_1 + (v_e - v_1) / a_f, rel_tol=REL)
    t, z, v = _event(trace, "drive_cap")
    assert math.isclose(t, t_1, rel_tol=REL) and math.isclose(v, v_1, rel_tol=REL)
    assert math.isclose(z + L, s_1, rel_tol=REL)
    for t, s, sdot, _m, res, y in _points(trace):
        if t <= t_1:
            assert _close(sdot, a_cmd * t * t / (2.0 * T_R), v_e)
        else:
            u = t - t_1
            assert _close(sdot, v_1 + a_f * u, v_e) and _close(
                s, s_1 + v_1 * u + a_f * u * u / 2, L
            )
            assert res.spec.params.forces(t, y).drive_force_N == f_max


def test_acceleration_law_power_cap_binds(f9_vehicle: Vehicle) -> None:
    """The power cap binds on the plateau at v_p = P/(M (a + g)) (drive_cap and
    power_limit both there, at t_p = t_r/2 + v_p/a), then the vertical power phase from
    v_p with v_inf = P/(M g), at every step and at release."""
    m = f9_vehicle.liftoff_mass_kg()
    a = 3.0 * G0_MPS2
    v_p = 50.0
    p_max = m * (a + G) * v_p
    model = _model("acceleration", f_max=2.0 * m * (a + G), p_max=p_max, a_cmd=a)
    exit_, trace = _push(f9_vehicle, model)
    assert exit_ is not None and trace.flags == ()
    t_p = T_R / 2.0 + v_p / a
    s_p = (v_p**2 + a * a * T_R**2 / 12.0) / (2.0 * a)
    v_inf = p_max / (m * G)
    v_e = brentq(lambda v: s_p + _power_phase(v, v_p, v_inf, G)[1] - L, v_p, v_inf * (1 - 1e-12))
    t_e = t_p + _power_phase(v_e, v_p, v_inf, G)[0]
    assert math.isclose(exit_.sdot_mps, v_e, rel_tol=REL)
    assert math.isclose(exit_.t_release_s, t_e, rel_tol=REL)
    for name in ("drive_cap", "power_limit"):
        t, _z, v = _event(trace, name)
        assert math.isclose(t, t_p, rel_tol=REL) and math.isclose(v, v_p, rel_tol=REL)
    for t, s, sdot, _m, _res, _y in _points(trace):
        if sdot <= v_p:
            v_cf, s_cf = _accel_forms(a, t)
            assert _close(sdot, v_cf, v_e) and _close(s, s_cf, L)
        else:
            dt, ds = _power_phase(sdot, v_p, v_inf, G)
            assert _close(t, t_p + dt, t_e) and _close(s, s_p + ds, L)


# ------------------------------------------------------------------- the stop taper


TAPER_LENGTHS_M = (20.0, 23.30677966101695, 10.195, L - 3.0 * G0_MPS2 * T_R**2 / 6.0)
"""Stop tapers of the taper test [m]: 20 m; 23.30677966101695 m and 10.195 m, where a
floor of the taper weight at w = 0 (a kink at s = L, inside the release step) without
the second flight to the release missed it by 1.2e-9 at rtol 1e-11 and 2.3e-10 at rtol
1e-10; and the taper that starts at the very end of the rise (s_0 = a t_r^2/6 for a =
3 g0), where taper_start and drive_ramp_end coincide (5.6e-8 at rtol 1e-10 then)."""


@pytest.mark.parametrize("rtol", [1e-11, 1e-10])
@pytest.mark.parametrize("s_t", TAPER_LENGTHS_M)
@pytest.mark.parametrize("control", ["force", "acceleration"])
def test_stop_taper_position_form(
    control: str, s_t: float, rtol: float, f9_vehicle: Vehicle
) -> None:
    """Over the last s_t metres (TAPER_LENGTHS_M) the force law's force is scaled toward
    the holding force M g (cold) and the acceleration law's command scaled, by (L -
    s)/s_t: both give x'' = -(a/s_t) x with x = L - s and a = 3 g0 (the force law's F_max
    = M (a + g), no power limit). taper_start at s_0 = L - s_t with v_0^2 = 2 a s_0 - a^2
    t_r^2/12, t_0 = t_r/2 + v_0/a; in the taper v^2 = v_0^2 + (a/s_t)(s_t^2 - x^2) and
    s(t) = L - [s_t cos Omega (t - t_0) - (v_0/Omega) sin Omega (t - t_0)], Omega =
    sqrt(a/s_t); at release v_e^2 = v_0^2 + a s_t, t_e = t_0 + atan(s_t Omega/v_0)/Omega;
    at rtol 1e-11 (SETTINGS) and
    1e-10, 1e-9 relative."""
    m = f9_vehicle.liftoff_mass_kg()
    a = 3.0 * G0_MPS2
    if control == "force":
        f_max = m * (a + G)
        model = _model(f_max=f_max, p_max=f_max * 1e3, taper=s_t)
    else:
        f_max = 2.0 * m * (a + G)
        model = _model("acceleration", f_max=f_max, p_max=f_max * 1e3, a_cmd=a, taper=s_t)
    exit_, trace = _push(f9_vehicle, model, settings=IntegratorSettings(rtol=rtol))
    assert exit_ is not None and trace.flags == ()
    s_0 = L - s_t
    v_0 = math.sqrt(2.0 * a * s_0 - a * a * T_R**2 / 12.0)
    t_0 = T_R / 2.0 + v_0 / a
    omega = math.sqrt(a / s_t)
    v_e = math.sqrt(v_0**2 + a * s_t)
    t_e = t_0 + math.atan(s_t * omega / v_0) / omega
    assert math.isclose(exit_.sdot_mps, v_e, rel_tol=REL)
    assert math.isclose(exit_.t_release_s, t_e, rel_tol=REL)
    t, z, v = _event(trace, "taper_start")
    assert math.isclose(t, t_0, rel_tol=REL) and math.isclose(v, v_0, rel_tol=REL)
    assert math.isclose(z + L, s_0, rel_tol=REL)
    inside = 0
    for t, s, sdot, _m, _res, _y in _points(trace):
        if s <= s_0:
            v_cf, s_cf = _accel_forms(a, t)
            assert _close(sdot, v_cf, v_e) and _close(s, s_cf, L)
        else:
            inside += 1
            x = L - s
            assert _close(sdot, math.sqrt(v_0**2 + (a / s_t) * (s_t**2 - x * x)), v_e)
            u = t - t_0
            x_cf = s_t * math.cos(omega * u) - (v_0 / omega) * math.sin(omega * u)
            assert _close(s, L - x_cf, L)
    assert inside >= 2


# ------------------------------------------------------------ limits, energy, loads


def _limit_cases(m: float) -> dict[str, tuple[LinearMotorAssist, IgnitionSpec]]:
    """Pushes whose limits bind: the force law power-limited cold and hot (f_imp 0 and
    1, a 20 t carriage), the acceleration law capped by its power limit (cold) and by
    F_max from push start (hot; a step command: a rising one would ask for a negative
    drive force at push start under the full thrust, ``drive_limit``), the force law
    ramped (lit on the track 1 s after push start)."""
    f_max = m * (3.0 * G0_MPS2 + G)
    return {
        "force_cold": (_model(f_max=f_max, p_max=f_max * 50.0, m_c=2e4), COLD),
        "force_hot": (_model(f_max=f_max, p_max=f_max * 40.0, m_c=2e4), HOT),
        "force_hot_imp": (_model(f_max=f_max, p_max=f_max * 40.0, m_c=2e4, f_imp=1.0), HOT),
        "force_ramped": (
            _model(f_max=f_max, p_max=f_max * 45.0, m_c=2e4),
            IgnitionSpec(1.0, reference="push_start"),
        ),
        "accel_power": (
            _model("acceleration", f_max=2 * f_max, p_max=f_max * 50.0, a_cmd=3 * G0_MPS2),
            COLD,
        ),
        "accel_force_hot": (
            _model(
                "acceleration", f_max=0.6 * f_max, p_max=f_max * 1e3, a_cmd=3 * G0_MPS2, t_r=0.0
            ),
            HOT,
        ),
    }


@pytest.mark.parametrize(
    "case",
    ["force_cold", "force_hot", "force_hot_imp", "force_ramped", "accel_power", "accel_force_hot"],
)
def test_force_and_power_never_exceed_their_limits(case: str, f9_vehicle: Vehicle) -> None:
    """F <= F_max and F sdot <= P_max (1 + 1e-12) at every integrator step and every
    sampled ASSIST row of the run, and the limit that binds is reached."""
    model, first = _limit_cases(f9_vehicle.liftoff_mass_kg())[case]
    result = _simulate(f9_vehicle, model, first)
    assert result.status == "nominal"
    f_max, p_max = model.force_max_N, model.power_max_W
    rows = result.timeseries[result.timeseries["phase"] == ASSIST_KIND]
    assert (rows["drive_force_N"] <= f_max * (1.0 + LIMIT_REL)).all()
    assert (rows["drive_power_W"] <= p_max * (1.0 + LIMIT_REL)).all()
    phases = [p for p in result.phases if p.spec.kind == ASSIST_KIND]
    peak_f = peak_p = 0.0
    for res in phases:
        lay = res.spec.params.layout
        for i, t in enumerate(res.t):
            y = np.asarray(res.y[:, i], dtype=float)
            force = res.spec.params.forces(float(t), y).drive_force_N
            power = force * float(lay.get(y, "sdot_mps"))
            assert force <= f_max * (1.0 + LIMIT_REL) and power <= p_max * (1.0 + LIMIT_REL)
            peak_f, peak_p = max(peak_f, force), max(peak_p, power)
    assert math.isclose(peak_f, f_max, rel_tol=1e-12) or math.isclose(peak_p, p_max, rel_tol=1e-12)


def _residual_rel(result: sim.Result) -> float:
    """The assist identity recomputed here from the budget's fields."""
    b = result.assist_budget
    assert b is not None
    lhs = b.work_drive + b.work_thrust
    return abs(lhs - b.delta_mech - b.massflow_term - b.dissipated) / max(abs(lhs), 1.0)


@pytest.mark.parametrize("case", ["force_cold", "force_hot", "force_ramped", "accel_power"])
def test_assist_energy_identity_cold_hot_and_ramped(case: str, f9_vehicle: Vehicle) -> None:
    """The identity E_drive + W_thrust = delta(M sdot^2/2 + M g z) + massflow closes to
    1e-9 (CLAUDE.md 1e-6) with the model injected through ``sim.simulate``: cold (the
    push unlit), hot (full thrust) and ramped (the ramp lit on the track); cold, the
    drive work is M (v_e^2/2 + g L) with M = m0 + m_c and the thrust work and the
    mass-flow term zero."""
    model, first = _limit_cases(f9_vehicle.liftoff_mass_kg())[case]
    result = _simulate(f9_vehicle, model, first)
    assert result.status == "nominal"
    assert _residual_rel(result) < REL
    assert result.metrics["assist_energy_residual_rel"] < REL
    b = result.assist_budget
    assert b is not None and b.dissipated == 0.0
    if first is COLD:
        m = f9_vehicle.liftoff_mass_kg() + model.carriage_mass_kg
        v_e = result.metrics["exit_speed_mps"]
        assert math.isclose(b.work_drive, m * (0.5 * v_e**2 + G * L), rel_tol=REL)
        assert b.work_thrust == 0.0 and b.massflow_term == 0.0
    else:
        assert b.work_thrust > 0.0 and b.massflow_term > 0.0


@pytest.mark.parametrize("f_imp", [0.0, 0.5, 1.0])
def test_hot_interface_force_on_the_force_plateau(f_imp: float, f9_vehicle: Vehicle) -> None:
    """Hot with full thrust T on a 20 t carriage, the force law at F_max (P_max far
    above the push's power): at every step after the rise F_int = (m_v/M) F_max - T
    (m_c + f_imp m_v)/M with M = m_v + m_c, and the felt acceleration (F_max + (1 -
    f_imp) T)/M; F_int = F_max - f_imp T only for a massless carriage."""
    thrust, _mdot, m0 = _stage1(f9_vehicle)
    m_c = 20_000.0
    f_max = m0 * (3.0 * G0_MPS2 + G)
    model = _model(f_max=f_max, p_max=f_max * 1e3, m_c=m_c, f_imp=f_imp)
    exit_, trace = _push(f9_vehicle, model, first=HOT)
    assert exit_ is not None and trace.status == "nominal"
    plateau = 0
    for t, _s, _sdot, m_v, res, y in _points(trace):
        if t < T_R:
            continue
        plateau += 1
        total = m_v + m_c
        assert res.spec.params.thrust_N(t) == thrust
        f = res.spec.params.forces(t, y)
        assert f.drive_force_N == f_max
        expected = (m_v / total) * f_max - thrust * (m_c + f_imp * m_v) / total
        assert math.isclose(f.interface_force_N, expected, rel_tol=REL, abs_tol=REL * f_max)
        felt = track_observables(t, y, res.spec.params)["felt_g"]
        assert math.isclose(felt, (f_max + (1.0 - f_imp) * thrust) / total / G0_MPS2, rel_tol=REL)
    assert plateau >= 5


def test_hot_push_rises_from_the_holding_force(f9_vehicle: Vehicle) -> None:
    """Hot (full thrust T from push start, f_imp 0.5, 20 t carriage) with 0 < (1 - f_imp) T
    < M_0 g: the holding force F_0 = M_0 g - (1 - f_imp) T, with M_0 = m0 - mdot t_ramp/2
    + m_c (the 2 s ramp burned on the clamp), holds the stack at push start (sddot(0) = 0
    to 1e-12 g0), and the drive force at every step of the rise is F_0 + (F_max - F_0)
    t/t_r."""
    thrust, mdot, m0 = _stage1(f9_vehicle)
    m_c, f_imp, t_ramp = 20_000.0, 0.5, 2.0
    total = m0 - mdot * t_ramp / 2.0 + m_c
    f_0 = total * G - (1.0 - f_imp) * thrust
    assert 0.0 < f_0 < total * G
    f_max = m0 * (3.0 * G0_MPS2 + G)
    model = _model(f_max=f_max, p_max=f_max * 1e3, m_c=m_c, f_imp=f_imp)
    exit_, trace = _push(f9_vehicle, model, first=HOT)
    assert exit_ is not None and trace.status == "nominal"
    first = trace.assist_phases()[0]
    bound = first.spec.params.assist.push_start
    assert math.isclose(bound.holding_force_N, f_0, rel_tol=1e-12)
    y0 = np.asarray(first.y[:, 0], dtype=float)
    assert abs(first.spec.params.forces(0.0, y0).sddot_mps2) <= 1e-12 * G0_MPS2
    rise = 0
    for t, _s, _sdot, _m, res, y in _points(trace):
        if t <= T_R:
            rise += 1
            force = res.spec.params.forces(t, y).drive_force_N
            assert math.isclose(force, f_0 + (f_max - f_0) * t / T_R, rel_tol=1e-12)
    assert rise >= 3


def test_track_peaks_sit_at_the_power_corner_inside_the_rise(f9_vehicle: Vehicle) -> None:
    """Cold force law, t_r = 1 s, the power corner inside the rise (P = F_max 10 m/s
    against v(t_r) = 14.7 m/s; 20 t carriage): the limit binds at t_p, the root of
    F_lim(t) v(t) = P with F_lim = M g + (F_max - M g) t/t_r and v = j t^2/2, after which
    F = P/sdot falls, so the peaks are the corner's: drive force F_lim(t_p), interface
    force (m_v/M) F_lim(t_p), felt F_lim(t_p)/(M g0) at t_p, read off the sampled rows
    because the power_limit crossing ends a sub-phase; no plateau (None)."""
    m_c, t_r = 20_000.0, 1.0
    m_v = f9_vehicle.liftoff_mass_kg()
    m = m_v + m_c
    f_max = m * (3.0 * G0_MPS2 + G)
    p_max = f_max * 10.0
    j = (f_max - m * G) / (m * t_r)

    def f_lim(t: float) -> float:
        return m * G + (f_max - m * G) * t / t_r

    t_p = brentq(lambda t: f_lim(t) * j * t * t / 2.0 - p_max, 1e-3, t_r, xtol=1e-15)
    result = _simulate(f9_vehicle, _model(f_max=f_max, p_max=p_max, t_r=t_r, m_c=m_c))
    assert result.status == "nominal" and result.flags == []
    met = result.metrics
    peak = f_lim(t_p)
    assert math.isclose(met["drive_force_peak_N"], peak, rel_tol=REL)
    assert math.isclose(met["interface_force_peak_N"], m_v / m * peak, rel_tol=REL)
    assert math.isclose(met["felt_g_track_peak"], peak / m / G0_MPS2, rel_tol=REL)
    assert math.isclose(met["felt_g_track_peak_t_s"], t_p - met["push_time_s"], abs_tol=1e-9)
    events = result.events.set_index("event")["t_s"]
    assert math.isclose(events["power_limit"], t_p, rel_tol=REL)
    assert met["push_power_limited"] is True and met["push_felt_g_plateau"] is None


@pytest.mark.parametrize("ratio", [1.0, 1.0 + 1e-12, 1.0 - 1e-12])
def test_a_power_corner_at_the_rise_end_is_logged_once_without_a_flag(
    ratio: float, f9_vehicle: Vehicle
) -> None:
    """The power corner at the end of the rise (P = F_max v(t_r) (1, 1 +- 1e-12), v(t_r) =
    j t_r^2/2, cold): the power_limit watch is at zero at the drive_ramp_end boundary,
    where it starts binding; it is logged once, at t_r, with no disarmed-event flag, and
    the push is power limited."""
    m = f9_vehicle.liftoff_mass_kg()
    f_max = m * (3.0 * G0_MPS2 + G)
    j = (f_max - m * G) / (m * T_R)
    v_r = j * T_R**2 / 2.0
    result = _simulate(f9_vehicle, _model(f_max=f_max, p_max=ratio * f_max * v_r))
    assert result.status == "nominal" and result.flags == []
    events = result.events
    limit = events[events["event"] == "power_limit"]
    assert len(limit) == 1 and limit["phase"].iloc[0] == ASSIST_KIND
    assert math.isclose(float(limit["t_s"].iloc[0]), T_R, rel_tol=REL)
    assert math.isclose(float(limit["v_mps"].iloc[0]), v_r, rel_tol=REL)
    assert result.metrics["push_power_limited"] is True


def test_a_drive_kink_on_the_placeholder_ramp_end_logs_no_ramp_end(f9_vehicle: Vehicle) -> None:
    """An unlit push has no thrust kink, so a drive_ramp_end that falls on its placeholder
    schedule's ramp end logs no ramp_end: a pending ignition with t_r = the F9's t_ramp
    (2 s; the run's one ramp_end is in BURN, after the release) and a failed push_start
    stage at t_ign_s = t_r - t_ramp (-1.5 s with t_r = 0.5 s)."""
    t_ramp = f9_vehicle.stages[0].startup.t_ramp_s
    assert t_ramp == 2.0
    f_max = f9_vehicle.liftoff_mass_kg() * (3.0 * G0_MPS2 + G)
    result = _simulate(f9_vehicle, _model(f_max=f_max, p_max=f_max * 1e3, t_r=t_ramp))
    assert result.status == "nominal"
    events = result.events
    ramp_end = events[events["event"] == "ramp_end"]
    assert len(ramp_end) == 1 and ramp_end["phase"].iloc[0] != ASSIST_KIND
    assert float(ramp_end["t_s"].iloc[0]) > float(events.set_index("event")["t_s"]["release"])
    failed = IgnitionSpec(T_R - t_ramp, reference="push_start", fails=True)
    exit_, trace = _push(f9_vehicle, _model(f_max=f_max, p_max=f_max * 1e3), first=failed)
    assert exit_ is not None
    names = [e.name for e in trace.events]
    assert "ramp_end" not in names and names.count("drive_ramp_end") == 1


CLAMP_REL = 1e-12
"""The clamp split's own bound on the release time and exit speed: split, both agree
with the closed form to 7.4e-15 at rtol 1e-11 and 1e-10; unsplit, the release time errs
by 3.5e-12 to 2.3e-10 (measured by a scratch probe, review pass 2 rerun, P2-m1)."""


@pytest.mark.parametrize("rtol", [1e-11, 1e-10])
@pytest.mark.parametrize("tau0", [0.0, 0.1])
def test_a_ramp_lit_on_the_track_splits_the_thrust_clamp(
    tau0: float, rtol: float, f9_vehicle: Vehicle
) -> None:
    """The F9's 2 s ramp lit tau0 before push start at sea-level pressure (p_amb A_e =
    0.62 MN): the delivered thrust T = max(0, T_vac - p_amb A_e) leaves zero at tau_c =
    t_ramp p_amb A_e/T_full after ignition, a kink of the force law's motion that
    ``prelude.thrust_clamp_time`` makes a sub-phase boundary (review pass 2 rerun,
    P2-m1). A step force law (t_r = 0) F = F_max = 3 m0 g (P_max far above), f_imp 0, no
    carriage, a 30 m silo released inside the ramp. With tau the time since ignition,
    M = M_i (1 - q^2 tau^2), q^2 = T_full/(2 c t_ramp M_i), and A(tau) = atanh(q tau)/(q
    M_i), B = int A, Lambda = int ln(M/M_i): before tau_c sddot = F/M - g, so v = F dA -
    g dtau and s = F (dB - A_0 dtau) - g dtau^2/2; after it sddot = (F - p_amb A_e)/M -
    c Mdot/M - g adds -c ln(M/M_c) to v and -c (dLambda - ln(M_c/M_i) dtau) to s. Every
    step on the closed form (1e-9), the release time and exit speed to CLAMP_REL, and a
    sub-phase starting at the clamp."""
    stage = f9_vehicle.stages[0]
    thrust, mdot, m_i = _stage1(f9_vehicle)
    c, t_ramp = thrust / mdot, stage.startup.t_ramp_s
    p_a = ambient_scalar(0.0)[0] * stage.n_engines * stage.engine.exit_area_m2
    tau_c = t_ramp * (p_a / thrust)
    q = math.sqrt(thrust / (2.0 * c * t_ramp * m_i))
    f_max = 3.0 * m_i * G

    def big_a(tau: float) -> float:
        return math.atanh(q * tau) / (q * m_i)

    def big_b(tau: float) -> float:
        return (tau * math.atanh(q * tau) + math.log1p(-((q * tau) ** 2)) / (2 * q)) / (q * m_i)

    def ln_m(tau: float) -> float:
        return math.log1p(-((q * tau) ** 2))

    def lam(tau: float) -> float:
        return tau * ln_m(tau) - 2.0 * tau + 2.0 * math.atanh(q * tau) / q

    def leg(ta: float, tb: float, va: float, sa: float, burn: bool) -> tuple[float, float]:
        d, f = tb - ta, f_max - (p_a if burn else 0.0)
        v = va + f * (big_a(tb) - big_a(ta)) - G * d
        s = sa + va * d + f * (big_b(tb) - big_b(ta) - big_a(ta) * d) - 0.5 * G * d * d
        if burn:
            v -= c * (ln_m(tb) - ln_m(ta))
            s -= c * (lam(tb) - lam(ta) - ln_m(ta) * d)
        return v, s

    def forms(tau: float) -> tuple[float, float]:
        if tau <= tau_c:
            return leg(tau0, tau, 0.0, 0.0, False)
        return leg(tau_c, tau, *leg(tau0, tau_c, 0.0, 0.0, False), True)

    length = 30.0
    tau_e = brentq(lambda tau: forms(tau)[1] - length, tau_c, t_ramp, xtol=1e-15, rtol=1e-15)
    model = _model(f_max=f_max, p_max=f_max * 1e3, t_r=0.0)
    exit_, trace = _push(
        f9_vehicle,
        model,
        track=StraightTrack(length, VERTICAL, -length),
        first=IgnitionSpec(-tau0, reference="push_start"),
        settings=IntegratorSettings(rtol=rtol),
        p_amb_pa=ambient_scalar(0.0)[0],
    )
    assert exit_ is not None and trace.status == "nominal" and trace.flags == ()
    assert math.isclose(exit_.t_release_s, tau_e - tau0, rel_tol=CLAMP_REL)
    assert math.isclose(exit_.sdot_mps, forms(tau_e)[0], rel_tol=CLAMP_REL)
    starts = [res.spec.t0 for res in trace.assist_phases()]
    assert len(starts) == 2 and starts[0] == 0.0
    assert math.isclose(starts[1], tau_c - tau0, rel_tol=1e-12)
    for t, s, sdot, _m, _res, _y in _points(trace):
        v, s_cf = forms(t + tau0)
        assert _close(sdot, v, exit_.sdot_mps) and _close(s, s_cf, length)


def _force_phase(m: float, f_max: float) -> tuple[float, float, float, float]:
    """(j, a_f, v_r, s_r) of the cold vertical force law from the holding force M g:
    the rise's jerk, the force phase's acceleration and the state at t_r."""
    j = (f_max - m * G) / (m * T_R)
    return j, j * T_R, j * T_R**2 / 2.0, j * T_R**3 / 6.0


@pytest.mark.parametrize("rtol", [1e-11, 1e-10])
def test_a_power_corner_just_short_of_the_track_end_still_releases_at_l(
    rtol: float, f9_vehicle: Vehicle
) -> None:
    """The power corner 0.5e-6 m before L (cold force law, vertical, P = F_max v(s_c) on
    the force phase, s_c = L - 0.5e-6 m; within ATOL_M of L but beyond RELEASE_TIE_M):
    the power_limit crossing ends its sub-phase there and the push flies on to the
    track end, so the release state sits at s = L (to 1e-12 L) with the speed and time
    of the power phase's closed form over the last 0.5e-6 m (1e-9 relative); one
    power_limit, 0.5e-6 m before L."""
    m = f9_vehicle.liftoff_mass_kg()
    f_max = m * (3.0 * G0_MPS2 + G)
    _j, a_f, v_r, s_r = _force_phase(m, f_max)
    s_c = L - 0.5e-6
    v_c = math.sqrt(v_r**2 + 2.0 * a_f * (s_c - s_r))
    t_c = T_R + (v_c - v_r) / a_f
    p_max = f_max * v_c
    v_inf = p_max / (m * G)
    v_e = brentq(lambda v: s_c + _power_phase(v, v_c, v_inf, G)[1] - L, v_c, v_c * (1 + 1e-6))
    t_e = t_c + _power_phase(v_e, v_c, v_inf, G)[0]
    model = _model(f_max=f_max, p_max=p_max)
    exit_, trace = _push(f9_vehicle, model, settings=IntegratorSettings(rtol=rtol))
    assert exit_ is not None and trace.flags == ()
    lay = trace.assist_phases()[-1].spec.params.layout
    assert abs(float(lay.get(exit_.y_track, "s_m")) - L) <= 1e-12 * L
    assert math.isclose(exit_.sdot_mps, v_e, rel_tol=REL)
    assert math.isclose(exit_.t_release_s, t_e, rel_tol=REL)
    t, z, v = _event(trace, "power_limit")
    assert math.isclose(L - (z + L), 0.5e-6, rel_tol=0.0, abs_tol=1e-10)
    assert math.isclose(t, t_c, rel_tol=REL) and math.isclose(v, v_c, rel_tol=REL)


@pytest.mark.parametrize("rtol", [1e-11, 1e-10])
@pytest.mark.parametrize("excess", [1e-7, 3.1e-4, 1e-2])
def test_a_power_corner_just_beyond_the_release_leaves_the_exit_exact(
    excess: float, rtol: float, f9_vehicle: Vehicle
) -> None:
    """The power corner a hair beyond the exit speed (cold force law, vertical, P =
    (1 + excess) F_max v_e): the push never reaches it, but the trial stages of the step
    that crosses L do, so the track-end root is flown to a second time as a fixed end;
    the exit speed and time are the force phase's, v_e^2 = v_r^2 + 2 a_f (L - s_r) and
    t_e = t_r + (v_e - v_r)/a_f, to 1e-9 relative (review pass 2 measured 4.6e-9 at rtol
    1e-10 for excess 3.1e-4 before that second flight); no power_limit event and the
    force at F_max after the rise."""
    m = f9_vehicle.liftoff_mass_kg()
    f_max = m * (3.0 * G0_MPS2 + G)
    _j, a_f, v_r, s_r = _force_phase(m, f_max)
    v_e = math.sqrt(v_r**2 + 2.0 * a_f * (L - s_r))
    t_e = T_R + (v_e - v_r) / a_f
    model = _model(f_max=f_max, p_max=(1.0 + excess) * f_max * v_e)
    exit_, trace = _push(f9_vehicle, model, settings=IntegratorSettings(rtol=rtol))
    assert exit_ is not None and trace.flags == ()
    assert math.isclose(exit_.sdot_mps, v_e, rel_tol=REL)
    assert math.isclose(exit_.t_release_s, t_e, rel_tol=REL)
    assert "power_limit" not in [e.name for e in trace.events]
    for t, _s, _sdot, _m, res, y in _points(trace):
        if t > T_R:
            assert res.spec.params.forces(t, y).drive_force_N == f_max


@pytest.mark.parametrize("rtol", [1e-11, 1e-10])
def test_a_force_cap_released_in_the_taper_is_split_and_logged(
    rtol: float, f9_vehicle: Vehicle
) -> None:
    """Acceleration law, a_cmd = 4 g0 capped by F_max = M (a_F + g), a_F = 3 g0, with a
    20 m taper (cold): the cap binds at t_1 = t_r a_F/a_cmd (drive_cap), the push enters
    the taper still capped (taper_start), and the cap stops binding where a_cmd w = a_F,
    x_1 = L - s_1 = (a_F/a_cmd) s_t (drive_cap_end: a sub-phase end, logged once at
    v_1^2 = v_cap^2 + 2 a_F (s_1 - s_cap)); after it x'' = -(a_cmd/s_t) x, so v^2 = v_1^2
    + Omega^2 (x_1^2 - x^2), Omega = sqrt(a_cmd/s_t), at every step, and at release v_e^2
    = v_1^2 + Omega^2 x_1^2, t_e = t(x_1) + atan(Omega x_1/v_1)/Omega, all to 1e-9
    relative; F = F_max
    at every step while capped, M (a_cmd w(s) + g) < F_max after."""
    m = f9_vehicle.liftoff_mass_kg()
    a_cmd, a_f, s_t = 4.0 * G0_MPS2, 3.0 * G0_MPS2, 20.0
    f_max = m * (a_f + G)
    model = _model("acceleration", f_max=f_max, p_max=f_max * 1e3, a_cmd=a_cmd, taper=s_t)
    exit_, trace = _push(f9_vehicle, model, settings=IntegratorSettings(rtol=rtol))
    assert exit_ is not None and trace.flags == ()
    t_cap = T_R * a_f / a_cmd
    v_cap, s_cap = a_cmd * t_cap**2 / (2.0 * T_R), a_cmd * t_cap**3 / (6.0 * T_R)
    x_1 = (a_f / a_cmd) * s_t
    v_1 = math.sqrt(v_cap**2 + 2.0 * a_f * (L - x_1 - s_cap))
    t_1 = t_cap + (v_1 - v_cap) / a_f
    omega = math.sqrt(a_cmd / s_t)
    v_e = math.sqrt(v_1**2 + omega**2 * x_1**2)
    t_e = t_1 + math.atan(omega * x_1 / v_1) / omega
    assert math.isclose(exit_.sdot_mps, v_e, rel_tol=REL)
    assert math.isclose(exit_.t_release_s, t_e, rel_tol=REL)
    names = [e.name for e in trace.events]
    assert names[1:] == ["drive_cap", "drive_ramp_end", "taper_start", "drive_cap_end"]
    t, z, v = _event(trace, "drive_cap_end")
    assert math.isclose(t, t_1, rel_tol=REL) and math.isclose(v, v_1, rel_tol=REL)
    assert math.isclose(z + L, L - x_1, rel_tol=REL)
    after = 0
    for t, s, sdot, m_v, res, y in _points(trace):
        force = res.spec.params.forces(t, y).drive_force_N
        if t_cap * (1.0 + REL) < t < t_1 * (1.0 - REL):
            assert force == f_max
        elif t > t_1 * (1.0 + REL):
            after += 1
            x = L - s
            assert _close(sdot, math.sqrt(v_1**2 + omega**2 * (x_1**2 - x * x)), v_e)
            command = m_v * (a_cmd * min(1.0, x / s_t) + G)
            assert math.isclose(force, command, rel_tol=1e-12) and force < f_max
    assert after >= 2


BRIEF_CAP_OFFSETS = (-1e-4, -1e-5, -1e-9, -1e-11)
"""delta of ``test_a_power_cap_binding_briefly_across_the_taper_start_is_split``: the
power cap set (1 + delta) times the need at the taper start, so it binds for about 0.3
ms, 30 microseconds, 3 ns (about the look-ahead ``prelude.WATCH_LOOKAHEAD_REL`` of the
push, 2.9 ns) and 0.03 ns (far below it). Review pass 3 (P3-M1) found the planner looping
(RuntimeError after 200 phases) at delta = -1e-4 (rtol 1e-10) and logging the end at the
instant of the start from delta = -1e-6 to -2e-4, when rule 3's 1 ms first step judged a
watch at zero; without the extra flight to an earlier crossing (``prelude.
_fly_to_crossing``) delta = -1e-4 missed by 1.1e-9 at rtol 1e-10 until the scan for
passed-over crossings (``prelude._passed_over``) found that binding in the first flight
(review pass 1 rerun); without the fresh rule
(``prelude._WatchBook``) the bindings below the look-ahead change a watch's side three
times at one instant (RuntimeError) at delta = -1e-11 (measured, scratch probes)."""


@pytest.mark.parametrize("rtol", [1e-11, 1e-10])
@pytest.mark.parametrize("delta", BRIEF_CAP_OFFSETS)
@pytest.mark.parametrize("s_t", [20.0, 38.5])
def test_a_power_cap_binding_briefly_across_the_taper_start_is_split(
    s_t: float, delta: float, rtol: float, f9_vehicle: Vehicle
) -> None:
    """Acceleration law (a = 3 g0, F_max = 2 M (a + g), cold) with P = (1 + delta) M (a +
    g) v_0, v_0 the uncapped command's speed at the taper start s_0 = L - s_t: the power
    cap binds on the plateau at v_p = (1 + delta) v_0 (power_limit and drive_cap at t_p =
    t_r/2 + v_p/a), the vertical power phase (v_inf = P/(M g)) carries the push into the
    taper (taper_start at s_0, at v_s), and the cap is released where the tapered command
    falls to it, M (a w(s) + g) v = P (power_limit_end and drive_cap_end at v_1, s_1);
    after it x'' = -(a/s_t) x, so v_e^2 = v_1^2 + Omega^2 x_1^2 and t_e = t_1 + atan(Omega
    x_1/v_1)/Omega with x_1 = L - s_1, Omega = sqrt(a/s_t). The run releases with no flag;
    each event once, in that order, at its closed-form time, speed and position (so no
    end at the instant of its start); the exit to 1e-9 relative (BRIEF_CAP_OFFSETS)."""
    m = f9_vehicle.liftoff_mass_kg()
    a = 3.0 * G0_MPS2
    s_0 = L - s_t
    v_0 = math.sqrt(2.0 * a * s_0 - a * a * T_R**2 / 12.0)
    p_max = (1.0 + delta) * m * (a + G) * v_0
    model = _model("acceleration", f_max=2.0 * m * (a + G), p_max=p_max, a_cmd=a, taper=s_t)
    exit_, trace = _push(f9_vehicle, model, settings=IntegratorSettings(rtol=rtol))
    assert exit_ is not None and trace.flags == ()
    v_p = (1.0 + delta) * v_0
    t_p = T_R / 2.0 + v_p / a
    s_p = (v_p**2 + a * a * T_R**2 / 12.0) / (2.0 * a)
    v_inf = p_max / (m * G)

    def s_of(v: float) -> float:
        return s_p + _power_phase(v, v_p, v_inf, G)[1]

    v_l = brentq(lambda v: s_of(v) - L, v_p, v_inf * (1.0 - 1e-12), xtol=1e-14)
    v_s = brentq(lambda v: s_of(v) - s_0, v_p, v_l, xtol=1e-14)
    v_1 = brentq(lambda v: m * (a * (L - s_of(v)) / s_t + G) * v - p_max, v_s, v_l, xtol=1e-14)
    t_s = t_p + _power_phase(v_s, v_p, v_inf, G)[0]
    t_1 = t_p + _power_phase(v_1, v_p, v_inf, G)[0]
    x_1 = L - s_of(v_1)
    omega = math.sqrt(a / s_t)
    v_e = math.sqrt(v_1**2 + omega**2 * x_1**2)
    t_e = t_1 + math.atan(omega * x_1 / v_1) / omega
    assert math.isclose(exit_.sdot_mps, v_e, rel_tol=REL)
    assert math.isclose(exit_.t_release_s, t_e, rel_tol=REL)
    names = [e.name for e in trace.events]
    assert names[:2] == ["push_start", "drive_ramp_end"] and names[4] == "taper_start"
    assert sorted(names[2:4]) == ["drive_cap", "power_limit"]
    assert sorted(names[5:]) == ["drive_cap_end", "power_limit_end"]
    expected = {
        "power_limit": (t_p, s_p, v_p),
        "drive_cap": (t_p, s_p, v_p),
        "taper_start": (t_s, s_0, v_s),
        "power_limit_end": (t_1, L - x_1, v_1),
        "drive_cap_end": (t_1, L - x_1, v_1),
    }
    for name, (t_cf, s_cf, v_cf) in expected.items():
        t, z, v = _event(trace, name)
        assert math.isclose(t, t_cf, rel_tol=REL) and math.isclose(v, v_cf, rel_tol=REL)
        assert _close(z + L, s_cf, L)


INSIDE_CAP_OFFSETS = (-1e-6, -6e-6)
"""delta of ``test_a_power_cap_binding_briefly_inside_the_taper_is_found_and_flown``: the
power cap set (1 + delta) times the peak of the need inside a 90 m taper, so it binds for
2.8 ms and 7.0 ms, inside one integrator step of the push's flights. Before the scan for
passed-over crossings (``prelude._passed_over``; review pass 1 rerun, H1) neither binding
was logged or flown: push_power_limited read False and the exit was 7.8e-10 and 1.15e-8
fast (measured, scratch probes)."""


@pytest.mark.parametrize("rtol", [1e-11, 1e-10])
@pytest.mark.parametrize("delta", INSIDE_CAP_OFFSETS)
def test_a_power_cap_binding_briefly_inside_the_taper_is_found_and_flown(
    delta: float, rtol: float, f9_vehicle: Vehicle
) -> None:
    """Acceleration law (a = 3 g0, F_max = 2 M (a + g), cold) with a 90 m taper: past the
    taper start s_0 = 10 m (taper_start at v_0^2 = 2 a s_0 - a^2 t_r^2/12, t_0 = t_r/2 +
    v_0/a) x'' = -(a/s_t) x, x = L - s, so v^2 = v_0^2 + Omega^2 (s_t^2 - x^2) with Omega =
    sqrt(a/s_t), and the power the command needs, M (a x/s_t + g) v, peaks inside the
    taper (at s = 36.9 m). With P = (1 + delta) times that peak the cap binds where the
    need first reaches P (x_b; power_limit and drive_cap at t_b = t_0 + (acos(x_b/R) -
    phi_0)/Omega, R = hypot(s_t, v_0/Omega), phi_0 = atan2(v_0/Omega, s_t)), the
    vertical power phase (v_inf = P/(M g)) flies while it binds, it is released where M
    (a w(s) + g) v = P on that phase (v_1, s_1: power_limit_end and drive_cap_end), and
    then x'' = -(a/s_t) x to v_e^2 = v_1^2 + Omega^2 x_1^2, t_e = t_1 + atan(Omega x_1/
    v_1)/Omega. The binding lies inside one step of every flight, so only the scan finds
    it (INSIDE_CAP_OFFSETS). Asserted: the release with no flag; each event once, in
    order, at its closed-form t, s and v; the exit to 1e-9 relative; through
    ``sim.simulate``, push_power_limited True and the peak drive power P."""
    m = f9_vehicle.liftoff_mass_kg()
    a, s_t = 3.0 * G0_MPS2, 90.0
    s_0 = L - s_t
    v_0 = math.sqrt(2.0 * a * s_0 - a * a * T_R**2 / 12.0)
    t_0 = T_R / 2.0 + v_0 / a
    omega = math.sqrt(a / s_t)

    def need(x: float) -> float:
        return m * (a * x / s_t + G) * math.sqrt(v_0**2 + omega**2 * (s_t**2 - x * x))

    peak = minimize_scalar(
        lambda x: -need(x), bounds=(0.0, s_t), method="bounded", options={"xatol": 1e-12}
    )
    x_pk = float(peak.x)
    p_max = (1.0 + delta) * need(x_pk)
    x_b = brentq(lambda x: need(x) - p_max, x_pk, s_t, xtol=1e-14)
    v_b = math.sqrt(v_0**2 + omega**2 * (s_t**2 - x_b**2))
    amplitude, phase_0 = math.hypot(s_t, v_0 / omega), math.atan2(v_0 / omega, s_t)
    t_b = t_0 + (math.acos(x_b / amplitude) - phase_0) / omega
    v_inf = p_max / (m * G)

    def s_of(v: float) -> float:
        return L - x_b + _power_phase(v, v_b, v_inf, G)[1]

    v_1 = brentq(
        lambda v: m * (a * (L - s_of(v)) / s_t + G) * v - p_max,
        v_b * (1.0 + 1e-7),
        v_b * 1.01,
        xtol=1e-14,
    )
    t_1 = t_b + _power_phase(v_1, v_b, v_inf, G)[0]
    x_1 = L - s_of(v_1)
    v_e = math.sqrt(v_1**2 + omega**2 * x_1**2)
    t_e = t_1 + math.atan(omega * x_1 / v_1) / omega
    assert 2.5e-3 < t_1 - t_b < 7.5e-3  # the binding the scan must find
    model = _model("acceleration", f_max=2.0 * m * (a + G), p_max=p_max, a_cmd=a, taper=s_t)
    settings = IntegratorSettings(rtol=rtol)
    exit_, trace = _push(f9_vehicle, model, settings=settings)
    assert exit_ is not None and trace.flags == ()
    assert math.isclose(exit_.sdot_mps, v_e, rel_tol=REL)
    assert math.isclose(exit_.t_release_s, t_e, rel_tol=REL)
    names = [e.name for e in trace.events]
    assert names[:3] == ["push_start", "drive_ramp_end", "taper_start"]
    assert sorted(names[3:5]) == ["drive_cap", "power_limit"]
    assert sorted(names[5:]) == ["drive_cap_end", "power_limit_end"]
    expected = {
        "taper_start": (t_0, s_0, v_0),
        "power_limit": (t_b, L - x_b, v_b),
        "drive_cap": (t_b, L - x_b, v_b),
        "power_limit_end": (t_1, L - x_1, v_1),
        "drive_cap_end": (t_1, L - x_1, v_1),
    }
    for name, (t_cf, s_cf, v_cf) in expected.items():
        t, z, v = _event(trace, name)
        assert math.isclose(t, t_cf, rel_tol=REL) and math.isclose(v, v_cf, rel_tol=REL)
        assert _close(z + L, s_cf, L)
    met = _simulate(f9_vehicle, model, settings=settings).metrics
    assert met["push_power_limited"] is True
    assert math.isclose(met["drive_power_peak_W"], p_max, rel_tol=LIMIT_REL)


def test_a_watch_changing_side_a_third_time_at_one_instant_raises() -> None:
    """The no-progress guard (``prelude._WatchBook.set_side``): a watch may change side
    twice at one instant (a touch: the limit starting and stopping at once, within
    ZERO_SPAN_S), and becomes fresh each time; a third change there raises RuntimeError
    (a planner bug) instead of looping; a change later than ZERO_SPAN_S counts anew."""
    book = _WatchBook()
    book.set_side("power_limit", True, 1.0)
    assert book.binding == {"power_limit"} and book.fresh == {"power_limit"}
    book.set_side("power_limit", False, 1.0 + ZERO_SPAN_S / 2)
    assert book.binding == set()
    with pytest.raises(RuntimeError, match="'power_limit' changed side 3 times"):
        book.set_side("power_limit", True, 1.0 + ZERO_SPAN_S)
    later = _WatchBook()
    for i in range(4):
        later.set_side("drive_cap", i % 2 == 0, 1.0 + 2.0 * i * ZERO_SPAN_S)
    assert later.binding == set()


# --------------------------------------------------------------------- refusals


@pytest.mark.parametrize("control", ["force", "acceleration"])
def test_stall_at_push_start_ends_the_run_on_the_track(control: str, f9_vehicle: Vehicle) -> None:
    """F_max + (1 - f_imp) T(0) <= M_0 g sin phi: status drive_stall, the one flag naming
    the numbers, the push-start event only, one zero-length ASSIST phase, no release
    items; the push-start row is the drive at F_max with no support reaction, so the
    felt g and interface-force metrics (``metrics.STALL_UNAVAILABLE_TRACK_METRICS``), the
    run-wide felt peak (no other row, cold) and the brake force are None, while the drive
    force F_max, the zero drive power and energy and the normal loads (g cos(pi/2),
    vertical) stay; through ``sim.simulate`` (1-D) and the planar prelude and track metrics."""
    m0 = f9_vehicle.liftoff_mass_kg()
    a_cmd = 3.0 * G0_MPS2 if control == "acceleration" else None
    model = _model(control, f_max=0.9 * m0 * G, p_max=1e10, a_cmd=a_cmd)
    result = _simulate(f9_vehicle, model)
    assert result.status == DRIVE_STALL
    lift, weight = 0.9 * m0 * G, m0 * G
    assert result.flags == [
        f"drive_stall: the drive at F_max and the thrust together cannot lift the stack at "
        f"push start: F_max + (1 - f_imp) T(0) = {lift:.6g} N <= M_0 g_eff sin phi = "
        f"{weight:.6g} N (F_max = {lift:.6g} N, "
        f"T(0) = 0 N, f_imp = 0, M_0 = {m0:.6g} kg); the run stopped on the track (its "
        "push-start row is the drive at F_max with no support reaction, at most the loads of "
        "the stack at rest: the felt g and interface-force metrics are None)"
    ]
    assert list(result.events["event"]) == ["push_start"]
    track = [p for p in result.phases if p.spec.kind == ASSIST_KIND]
    assert len(track) == 1 and track[0].span_s == 0.0
    met = result.metrics
    unavailable = (*STALL_UNAVAILABLE_TRACK_METRICS, "peak_felt_axial_g", "brake_force_N")
    unavailable += ("exit_speed_mps", "push_felt_g_plateau", "release_trigger")
    assert all(met[key] is None for key in unavailable), [k for k in unavailable if met[k]]
    assert met["drive_force_peak_N"] == lift and met["drive_power_peak_W"] == 0.0
    assert met["drive_energy_J"] == 0.0 and abs(met["peak_track_normal_g"]) < 1e-15
    env = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), 0.0, ambient_scalar)
    planner = PlanarPlanner(
        f9_vehicle,
        _specs(f9_vehicle, COLD),
        GuidanceSpec(50.0, 60.0, 60.0),
        env,
        "stage1_burnout",
        SETTINGS,
    )
    start = planner.start(model, SILO)
    assert start.status == DRIVE_STALL and start.t_fs_s is None
    from launchsim.losses import assist_energy_budget
    from launchsim.metrics_planar import _run_wide_felt, planar_track_metrics, sample_trace_planar

    phases = start.prefix.assist_phases()
    budget = assist_energy_budget(phases, phases[0].spec.params.layout, 0.0, env.g_ref_mps2)
    frame = sample_trace_planar(start.prefix, f9_vehicle, 0.05)
    planar = planar_track_metrics(start.prefix, model, SILO, budget, frame)
    assert all(planar[key] is None for key in STALL_UNAVAILABLE_TRACK_METRICS)
    assert planar["brake_force_N"] is None and planar["drive_force_peak_N"] == lift
    assert _run_wide_felt(frame, None, start.prefix)["peak_felt_axial_g"] is None


def test_a_hot_stall_raises_no_interface_tensile_flag(f9_vehicle: Vehicle) -> None:
    """Lit 0.5 s before push start (T_vac(0) = T_full/4 on the clamp) on a 20 t carriage,
    f_imp 1, F_max 1 MN: a stall (F_max <= M_0 g). Its one ASSIST row reads F_int =
    (m_v/M_0) F_max - T(0) < 0, a tension ``track_flags`` would report, while the vehicle
    at rest on its supports presses with m_v g - T(0) > 0; so a drive_stall run raises
    the stall flag alone (``track_flags(..., stalled=True)``), through ``sim.simulate``
    (1-D, vacuum thrust) and ``sim.simulate_planar`` (the planar prelude, sea-level
    thrust T_vac - p_amb A_e); review pass 2 rerun, P2-m2 and P2H-m1."""
    thrust, mdot, m_i = _stage1(f9_vehicle)
    stage = f9_vehicle.stages[0]
    hot = IgnitionSpec(-0.5, reference="push_start")
    m_c, f_max = 20_000.0, 1.0e6
    model = _model(f_max=f_max, p_max=1e10, m_c=m_c, f_imp=1.0)
    m_v = m_i - mdot * 0.5**2 / (2.0 * stage.startup.t_ramp_s)
    p_a = ambient_scalar(0.0)[0] * stage.n_engines * stage.engine.exit_area_m2
    for t_0 in (thrust / 4.0, thrust / 4.0 - p_a):
        assert f_max <= (m_v + m_c) * G and m_v * G - t_0 > 0.0
    result = _simulate(f9_vehicle, model, hot)
    assert result.status == DRIVE_STALL
    assert [flag.split(":")[0] for flag in result.flags] == ["drive_stall"]
    rows = result.timeseries[result.timeseries["phase"] == ASSIST_KIND]
    f_int = m_v / (m_v + m_c) * f_max - thrust / 4.0
    assert len(rows) == 1 and math.isclose(rows["interface_force_N"].iloc[0], f_int, rel_tol=REL)
    assert [flag.split(":")[0] for flag in track_flags(result.timeseries)] == ["interface_tensile"]
    env = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), 0.0, ambient_scalar)
    guidance = GuidanceSpec(50.0, 60.0, 60.0)
    specs = _specs(f9_vehicle, hot)
    planner = PlanarPlanner(f9_vehicle, specs, guidance, env, "stage1_burnout", SETTINGS)
    start = planner.start(model, SILO)
    assert start.status == DRIVE_STALL
    checks = ChecksConfig()
    setup = sim.PlanarSetup(
        env=env,
        assist=model,
        track=SILO,
        ignition=specs,
        guidance=guidance,
        budget=SearchBudget.from_config(SearchConfig(), checks),
        target=None,
        settings=SETTINGS,
        checks=checks,
    )
    planar = sim.simulate_planar(start.prefix, f9_vehicle, setup, sample_dt_s=0.05, figure_items={})
    assert planar.status == DRIVE_STALL
    assert [flag.split(":")[0] for flag in planar.flags] == ["drive_stall"]
    assert [flag.split(":")[0] for flag in track_flags(planar.timeseries)] == ["interface_tensile"]


def test_stall_condition_is_the_bound_closed_form() -> None:
    """``stall_reason`` of the bound model: a stall exactly at F_max + (1 - f_imp) T(0) =
    M_0 g sin phi (<=), not just above it; the thrust counts by its system share; a
    horizontal track never stalls; the holding force F_0 = max(0, M_0 g sin phi - (1 -
    f_imp) T(0)) is bound with M_0 = m_v + m_c."""
    m_v, m_c, f_max = 500_000.0, 20_000.0, 3.0e6
    model = _model(f_max=f_max, p_max=1e9, m_c=m_c, f_imp=0.5)
    exact = 2.0 * ((m_v + m_c) * G - f_max)  # (1 - 0.5) T(0) closes the gap exactly
    bound = model.at_push_start(m_v, exact, G, SILO)
    assert bound.push_start == PushStart(m_v + m_c, exact, G, max(0.0, (m_v + m_c) * G - exact / 2))
    assert bound.stall_reason() is not None
    assert model.at_push_start(m_v, exact * (1 + 1e-9), G, SILO).stall_reason() is None
    assert model.at_push_start(m_v, 0.0, G, FLAT).stall_reason() is None
    hold = model.at_push_start(m_v, 2.0e6, G, SILO).push_start
    assert hold is not None and hold.holding_force_N == (m_v + m_c) * G - 1.0e6
    assert model.at_push_start(m_v, 1.2e7, G, SILO).push_start.holding_force_N == 0.0
    with pytest.raises(ValueError, match="bind it with at_push_start"):
        model.stall_reason()


LM_BLOCK: dict[str, Any] = {
    "model": "linear_motor",
    "stroke_m": 100,
    "control": "force",
    "force_max_kN": 22000,
    "power_max_MW": 1100.5,
    "force_rise_time_s": 0.5,
    "brake_decel_g": 5,
}
"""A valid force-law block as YAML gives it (integers stay numbers)."""


def test_release_referenced_on_track_ignition_is_refused(
    f9_vehicle_dict: dict[str, Any], f9_vehicle: Vehicle
) -> None:
    """A release-referenced stage-1 t_ign_s < 0 on the linear motor is refused when the
    run resolves (``resolve_run``, one line naming the stage and the value), and by the
    prelude for an injected spec; the same time from push_start, t_ign_s >= 0 from the
    release, a failed stage and a constant_accel run are accepted."""
    on_track = {"stage1": {"t_ign_s": -1.0}}
    with pytest.raises(
        ValueError,
        match=r"^run 'lm', ignition stage1: a release-referenced t_ign_s -1 s \(lit on the "
        r"track\) is refused on the linear_motor, whose push time is known only once the "
        r"push is flown; state it with reference push_start$",
    ):
        resolve_run("lm", {"assist": LM_BLOCK, "ignition": on_track}, f9_vehicle_dict)
    for ignition in (
        {"stage1": {"t_ign_s": -1.0, "reference": "push_start"}},
        {"stage1": {"t_ign_s": 0.0}},
        {"stage1": {"t_ign_s": 0.5}},
    ):
        resolve_run("lm", {"assist": LM_BLOCK, "ignition": ignition}, f9_vehicle_dict)
    failed = {"stage1": {"t_ign_s": -1.0, "fails": True}}
    resolve_run("lm", {"assist": LM_BLOCK, "ignition": failed, "end": "impact"}, f9_vehicle_dict)
    silo = {"model": "constant_accel", "net_accel_g": 3, "stroke_m": 100, "brake_decel_g": 5}
    resolve_run("ca", {"assist": silo, "ignition": on_track}, f9_vehicle_dict)
    model = _model(f_max=1e8, p_max=1e10)
    with pytest.raises(ValueError, match="release-referenced t_ign_s -1 s"):
        _simulate(f9_vehicle, model, IgnitionSpec(-1.0))
    assert pending_until_release(IgnitionSpec(0.0), model)
    assert not pending_until_release(IgnitionSpec(0.0, reference="push_start"), model)
    assert not pending_until_release(IgnitionSpec(-1.0, fails=True), model)
    ca = ConstantAccelAssist(3.0 * G0_MPS2, 0.0, A_BRAKE)
    assert not pending_until_release(IgnitionSpec(0.5), ca)
    assert not pending_until_release(IgnitionSpec(0.5), None)


@pytest.mark.parametrize("t_ign_s", [0.0, 0.5])
def test_pending_ignition_lights_at_the_flown_release(t_ign_s: float, f9_vehicle: Vehicle) -> None:
    """A release-referenced t_ign_s >= 0 on the linear motor is pending through the
    unlit push and lights at t_release + t_ign_s exactly, in 1-D (``ascend``) and in the
    planar prelude (``start_track`` writes it, ``to_kick`` lights there); nothing is
    flagged."""
    f_max = f9_vehicle.liftoff_mass_kg() * (3.0 * G0_MPS2 + G)
    model = _model(f_max=f_max, p_max=f_max * 50.0)
    result = _simulate(f9_vehicle, model, IgnitionSpec(t_ign_s))
    assert result.status == "nominal" and result.flags == []
    events = result.events.set_index("event")["t_s"]
    assert events["ignition"] == events["release"] + t_ign_s
    track = [p for p in result.phases if p.spec.kind == ASSIST_KIND]
    assert not any(p.spec.params.lit for p in track)
    assert result.metrics["propellant_burned_on_track_kg"] == 0.0
    omega = OMEGA_EARTH_RADS * math.cos(math.radians(28.5))
    env = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), omega, ambient_scalar)
    planner = PlanarPlanner(
        f9_vehicle,
        _specs(f9_vehicle, IgnitionSpec(t_ign_s)),
        GuidanceSpec(50.0, 60.0, 60.0),
        env,
        "stage1_burnout",
        SETTINGS,
    )
    start = planner.start(model, SILO)
    assert start.status == "nominal" and start.t_fs_s is not None
    assert start.t_ign1_s == start.t_fs_s + t_ign_s
    assert start.prefix.t_ign_abs_s == {f9_vehicle.stage_names[0]: start.t_ign1_s}
    assert start.prefix.flags == ()
    kick = planner.to_kick(start)
    ignitions = [e for e in kick.prefix.events if e.name == "ignition"]
    assert len(ignitions) == 1 and ignitions[0].t_s == start.t_ign1_s


# ------------------------------------------------------------------ braking


@pytest.mark.parametrize("m_c", [0.0, 22_000.0])
def test_braking_closed_forms(m_c: float, f9_vehicle: Vehicle) -> None:
    """Distance v^2/(2 a_b), time v/a_b, brake force m_c (a_b - g sin phi), energy
    (1/2) m_c v^2 (1 - g sin phi/a_b) = force x distance, all 0 for m_c = 0; facility
    max(L, L + d) = L + d (release at L); the run's metrics at its exit speed."""
    f_max = (f9_vehicle.liftoff_mass_kg() + m_c) * (3.0 * G0_MPS2 + G)
    model = _model(f_max=f_max, p_max=f_max * 50.0, m_c=m_c)
    v = 76.70717046013364
    d = v * v / (2.0 * A_BRAKE)
    assert math.isclose(model.braking_distance_m(v), d, rel_tol=1e-15)
    assert math.isclose(model.braking_time_s(v), v / A_BRAKE, rel_tol=1e-15)
    force = m_c * (A_BRAKE - G)
    energy = 0.5 * m_c * v * v * (1.0 - G / A_BRAKE)
    assert math.isclose(model.brake_force_N(G, VERTICAL), force, rel_tol=1e-15)
    assert math.isclose(model.brake_energy_J(v, G, VERTICAL), energy, rel_tol=1e-15)
    assert math.isclose(energy, force * d, rel_tol=1e-14)
    assert math.isclose(model.brake_force_N(G, 0.0), m_c * A_BRAKE, rel_tol=1e-15)
    assert math.isclose(model.facility_length_m(SILO, v), L + d, rel_tol=1e-15)
    if m_c == 0.0:
        assert (
            model.brake_force_N(G, VERTICAL) == 0.0 and model.brake_energy_J(v, G, VERTICAL) == 0.0
        )
    result = _simulate(f9_vehicle, model)
    met = result.metrics
    v_e = met["exit_speed_mps"]
    assert met["braking_distance_m"] == v_e**2 / (2.0 * A_BRAKE)
    assert math.isclose(met["braking_time_s"], v_e / A_BRAKE, rel_tol=1e-15)
    assert math.isclose(met["brake_force_N"], force, rel_tol=1e-15, abs_tol=0.0)
    expected = 0.5 * m_c * v_e**2 * (1.0 - G / A_BRAKE)
    assert math.isclose(met["brake_energy_J"], expected, rel_tol=1e-15, abs_tol=0.0)
    assert math.isclose(met["facility_length_m"], L + v_e**2 / (2.0 * A_BRAKE), rel_tol=1e-15)


# ------------------------------------------------------- metrics and assumptions


def test_linear_motor_metrics_and_assumption_lines(f9_vehicle: Vehicle) -> None:
    """A power-limited cold force-law run (20 t carriage) writes LINEAR_MOTOR_METRICS
    after the track keys: the settings, power limited, the mean v_e/t_push, the felt
    plateau F_max/M/g0 at t_r, release at L by track_end, the electrical peak P_max/eta
    (the power-limited peak is P_max), the braking items; a push whose corner is never
    reached is not power limited, nor one whose corner is the exit speed itself (k =
    P_max/(F_max v_e) = 1, a tie at the release: POWER_LIMIT_TIE_REL), while k = 0.999
    is; a constant_accel run
    gains none of the keys; the drive's assumption lines (four written out, and the
    acceleration law's taper and shaft lines); the electrical power of a negative
    (braking) power is zero."""
    m_c = 20_000.0
    m = f9_vehicle.liftoff_mass_kg() + m_c
    f_max = m * (3.0 * G0_MPS2 + G)
    p_max = f_max * 50.0
    model = _model(f_max=f_max, p_max=p_max, m_c=m_c)
    result = _simulate(f9_vehicle, model)
    met = result.metrics
    keys = list(met)
    assert keys[-len(LINEAR_MOTOR_METRICS) :] == list(LINEAR_MOTOR_METRICS)
    assert (met["push_force_max_N"], met["push_power_max_W"]) == (f_max, p_max)
    assert met["push_rise_time_s"] == T_R and met["push_corner_speed_mps"] == p_max / f_max
    assert met["push_power_limited"] is True
    assert met["push_accel_mean_mps2"] == met["exit_speed_mps"] / met["push_time_s"]
    assert math.isclose(met["push_felt_g_plateau"], f_max / m / G0_MPS2, rel_tol=1e-12)
    assert (met["release_position_m"], met["release_trigger"]) == (L, "track_end")
    assert math.isclose(met["drive_power_peak_W"], p_max, rel_tol=1e-12)
    assert met["electrical_power_peak_W"] == met["drive_power_peak_W"] / ETA
    assert math.isclose(met["electrical_energy_J"], met["drive_work_in_J"] / ETA, rel_tol=1e-15)
    unlimited = _simulate(f9_vehicle, _model(f_max=f_max, p_max=f_max * 1e3, m_c=m_c))
    assert unlimited.metrics["push_power_limited"] is False
    a_f = f_max / m - G  # cold: the net acceleration a_f r(t), so v_e^2 = 2 a_f L - a_f^2 t_r^2/12
    v_e = math.sqrt(2.0 * a_f * L - a_f * a_f * T_R**2 / 12.0)
    for k, limited in ((1.0, False), (0.999, True)):
        run = _simulate(f9_vehicle, _model(f_max=f_max, p_max=k * f_max * v_e, m_c=m_c))
        assert run.metrics["push_power_limited"] is limited, k
    assert model.electrical_power_W(-1.0e6) == 0.0
    ca = _simulate(f9_vehicle, ConstantAccelAssist(3.0 * G0_MPS2, m_c, A_BRAKE, g_eff_mps2=G))
    assert not set(LINEAR_MOTOR_METRICS) & set(ca.metrics)
    lines = [a for a in result.assumptions if a.startswith("linear_motor:")]
    assert len(lines) == 10 and lines == list(model.assumptions())
    assert lines[1] == (
        "linear_motor: P_max is the mechanical power at the carriage (F sdot); the "
        "electricity is the positive drive work / efficiency and the electrical power peak "
        "the mechanical peak / efficiency, drive efficiency 0.5 (assumed), which moves no "
        "trajectory"
    )
    assert lines[6] == (
        "linear_motor: shaft vented (no air column), no friction; air drag on the vehicle in "
        "the shaft is neglected: under the force law it would lower the exit speed (the exit "
        "speed is biased high) and raise the interface force (by D m_c / M at a given drive "
        "force, zero then without a carriage mass, and in the power phase also through P_max "
        "/ sdot at the lower speed) and the drive work (more of the stroke at F_max after the "
        "rise, a longer push at P_max): both are biased low; the peak drive power when "
        "P_max is not reached, the felt g and the mean acceleration are biased high"
    )
    assert lines[7] == (
        f"linear_motor: constant g_eff = {G:.7g} m/s^2 on the track, omega_p = 0, Coriolis "
        "neglected"
    )
    assert lines[9] == (
        "linear_motor: a release-referenced stage-1 ignition lights at the flown release plus "
        "t_ign_s (the push time is a result of the push); one lit on the track must be stated "
        "from push_start (a release-referenced t_ign_s < 0 on a stage that lights is refused)"
    )
    accel = _model("acceleration", f_max=f_max, p_max=p_max, a_cmd=3.0 * G0_MPS2, taper=10.0)
    assert accel.taper_assumption() == (
        "linear_motor: release at the track end (s = L) after a stop taper over the last 10 m: "
        "the acceleration command is scaled by min(1, (L - s) / s_taper); at L the drive force "
        "is the holding force M g_eff sin phi - (1 - f_imp) T (zero net acceleration) unless a "
        "cap binds there, and it drops to zero in a step at release"
    )
    assert accel.shaft_assumption().endswith(
        "under the acceleration law the drive force would absorb it while no cap binds (the "
        "drive work, the peak drive power and the interface force are biased low, as for "
        "constant_accel), and while a cap binds it would lower the exit speed (biased high; "
        "drag can also make a cap bind that the drag-free push never reaches)"
    )


def test_planar_track_metrics_of_a_linear_motor_push(f9_vehicle: Vehicle) -> None:
    """The planar track metrics of a linear-motor push (the planar prelude with the
    site's rotation): net_accel_* None (no prescribed constant: the force law has none,
    and the acceleration law's command is not what a cap lets it fly), the stroke, and
    LINEAR_MOTOR_METRICS after the push settings."""
    from launchsim.losses import assist_energy_budget
    from launchsim.metrics_planar import planar_track_metrics, sample_trace_planar

    omega = OMEGA_EARTH_RADS * math.cos(math.radians(28.5))
    env = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), omega, ambient_scalar)
    f_max = f9_vehicle.liftoff_mass_kg() * (3.0 * G0_MPS2 + env.g_ref_mps2)
    model = _model(f_max=f_max, p_max=f_max * 50.0)
    planner = PlanarPlanner(
        f9_vehicle,
        _specs(f9_vehicle, COLD),
        GuidanceSpec(50.0, 60.0, 60.0),
        env,
        "stage1_burnout",
        SETTINGS,
    )
    trace = planner.to_kick(planner.start(model, SILO)).prefix
    phases = trace.assist_phases()
    budget = assist_energy_budget(phases, phases[0].spec.params.layout, 0.0, env.g_ref_mps2)
    frame = sample_trace_planar(trace, f9_vehicle, 0.05)
    met = planar_track_metrics(trace, model, SILO, budget, frame)
    keys = list(met)
    assert keys[-len(LINEAR_MOTOR_METRICS) - 3 :][:3] == [
        "stroke_m",
        "net_accel_mps2",
        "net_accel_g",
    ]
    assert keys[-len(LINEAR_MOTOR_METRICS) :] == list(LINEAR_MOTOR_METRICS)
    assert met["net_accel_mps2"] is None and met["net_accel_g"] is None and met["stroke_m"] == L
    assert met["push_power_limited"] is True and met["release_trigger"] == "track_end"
    assert met["push_accel_mean_mps2"] == met["exit_speed_mps"] / met["push_time_s"]


# ------------------------------------------------------------------------ config


def test_linear_motor_config_si_properties_and_build() -> None:
    """The force and acceleration blocks validate (YAML integers are numbers); the SI
    properties through units.py (kN, MW, g0, t); ``build_assist`` (through
    ASSIST_MODELS) gives the unbound model and the buried track from the config."""
    cfg = LinearMotorConfig.model_validate({**LM_BLOCK, "carriage_mass_t": 22, "stop_taper_m": 10})
    assert cfg.stroke_m == 100.0 and isinstance(cfg.stroke_m, float)
    assert cfg.force_max_N == 22000 * 1000.0 and cfg.power_max_W == 1100.5 * 1.0e6
    assert cfg.carriage_mass_kg == 22_000.0 and cfg.brake_decel_mps2 == 5 * G0_MPS2
    assert cfg.accel_command_mps2 is None and cfg.drive_efficiency == 1.0
    accel = LinearMotorConfig.model_validate(
        {**LM_BLOCK, "control": "acceleration", "accel_command_g": 3.009}
    )
    assert accel.accel_command_mps2 == 3.009 * G0_MPS2
    assert ASSIST_MODELS["linear_motor"] is LinearMotorAssist
    assert CONTROL_LAWS == get_args(config.ControlLaw) == ("force", "acceleration")
    model, track = build_assist(cfg, G)
    assert isinstance(model, LinearMotorAssist) and model.push_start is None
    assert (model.control, model.force_max_N, model.power_max_W) == ("force", 2.2e7, 1.1005e9)
    assert (model.rise_time_s, model.carriage_mass_kg, model.stop_taper_m) == (0.5, 2.2e4, 10.0)
    assert (model.efficiency, model.f_imp, model.g_eff_mps2) == (1.0, 0.0, G)
    assert isinstance(track, StraightTrack) and track.length_m == L
    assert track.start_altitude_m == -L and track.phi_rad == VERTICAL
    run = RunConfig.model_validate({"name": "lm", "assist": LM_BLOCK})
    assert isinstance(run.assist, LinearMotorConfig)


@pytest.mark.parametrize(
    ("edit", "match"),
    [
        ({"control": "acceleration"}, "control acceleration needs accel_command_g"),
        ({"accel_command_g": 3.0}, "control force takes no accel_command_g"),
        ({"stop_taper_m": 100.0}, "must be shorter than the stroke"),
        ({"stop_taper_m": None}, "stop_taper_m is null"),
        ({"control": "acceleration", "accel_command_g": None}, "accel_command_g is null"),
        ({"force_max_kN": True}, "float_type"),
        ({"power_max_MW": "1100"}, "float_type"),
        ({"force_rise_time_s": math.inf}, "finite_number"),
        ({"stroke_m": math.nan}, "finite_number"),
        ({"force_rise_time_s": -0.1}, "greater_than_equal"),
        ({"force_max_kN": 0}, "greater_than"),
        ({"drive_efficiency": 1.5}, "less_than_equal"),
        ({"exhaust_impingement_fraction": -0.1}, "greater_than_equal"),
        ({"carriage_mass_t": "22"}, "float_type"),
        ({"brake_decel_g": math.inf}, "finite_number"),
        ({"shaft": "sealed"}, "literal_error"),
        ({"control": "speed"}, "literal_error"),
        ({"net_accel_g": 3.0}, "extra_forbidden"),
        ({"release_speed_mps": 76.7, "stop_taper_m": 10.0}, "refused together with stop_taper_m"),
        ({"release_speed_mps": 76.7, "stop_taper_m": 0.0}, "refused together with stop_taper_m"),
        ({"release_speed_mps": None}, "release_speed_mps is null"),
        ({"release_speed_mps": True}, "float_type"),
        ({"release_speed_mps": "76.7"}, "float_type"),
        ({"release_speed_mps": 0}, "greater_than"),
        ({"release_speed_mps": math.inf}, "finite_number"),
        ({"control": "acceleration", "accel_command_g": True}, "float_type"),
        ({"control": "acceleration", "accel_command_g": "3"}, "float_type"),
        ({"control": "acceleration", "accel_command_g": 0}, "greater_than"),
        ({"stop_taper_m": True}, "float_type"),
        ({"stop_taper_m": "5"}, "float_type"),
        ({"stop_taper_m": -1}, "greater_than_equal"),
        ({"drive_efficiency": True}, "float_type"),
        ({"drive_efficiency": "0.9"}, "float_type"),
        ({"exhaust_impingement_fraction": True}, "float_type"),
        ({"exhaust_impingement_fraction": "0.5"}, "float_type"),
        ({"power_max_MW": 0}, "greater_than"),
        ({"stroke_m": True}, "float_type"),
        ({"stroke_m": "100"}, "float_type"),
        ({"force_max_kN": "22000"}, "float_type"),
        ({"power_max_MW": True}, "float_type"),
        ({"force_rise_time_s": True}, "float_type"),
        ({"force_rise_time_s": "0.5"}, "float_type"),
        ({"carriage_mass_t": True}, "float_type"),
        ({"brake_decel_g": True}, "float_type"),
        ({"brake_decel_g": "5"}, "float_type"),
    ],
)
def test_linear_motor_config_refusals(edit: dict[str, Any], match: str) -> None:
    """Each refused block: the control-law keys, the taper, a null optional key, strict
    finite numbers (KI-030's rule: a bool and a numeric string for each of the eleven
    numbers, NaN, inf), the bounds, the vented shaft only, no assist-family key, and
    (SP7 step S4a) a release speed together with a stop taper (any stop_taper_m given,
    0 included: the taper is a release-at-L device, design 4.6)."""
    block = {**LM_BLOCK, **edit}
    with pytest.raises(ValidationError) as info:
        LinearMotorConfig.model_validate(block)
    text = str(info.value)
    assert match in text or any(e["type"] == match for e in info.value.errors()), text


def test_linear_motor_dump_states_the_given_keys() -> None:
    """``model_dump`` leaves out an optional key holding None and validates again to an
    equal model (python and json modes); a given optional key is dumped."""
    cfg = LinearMotorConfig.model_validate(LM_BLOCK)
    dump = cfg.model_dump()
    assert "accel_command_g" not in dump and "stop_taper_m" not in dump
    assert LinearMotorConfig.model_validate(dump) == cfg
    assert LinearMotorConfig.model_validate(cfg.model_dump(mode="json")) == cfg
    taper = LinearMotorConfig.model_validate({**LM_BLOCK, "stop_taper_m": 7.67})
    assert taper.model_dump()["stop_taper_m"] == 7.67
    assert LinearMotorConfig.model_validate(taper.model_dump()) == taper


def test_depth_bound_applies_to_every_track_drive(f9_vehicle_dict: dict[str, Any]) -> None:
    """``at_depth_m`` deeper than the stroke is refused on the linear motor too (the
    check generalised from constant_accel, TRACK_DRIVE_CONFIGS); a depth within it
    validates and is refused where the specs are built (the conversion needs the
    prescribed acceleration)."""
    assert config.TRACK_DRIVE_CONFIGS == (config.ConstantAccelConfig, LinearMotorConfig)
    with pytest.raises(ValidationError, match="at_depth_m 150 m is deeper than the track"):
        RunConfig.model_validate(
            {"name": "lm", "assist": LM_BLOCK, "ignition": {"stage1": {"at_depth_m": 150}}}
        )
    run = resolve_run(
        "lm", {"assist": LM_BLOCK, "ignition": {"stage1": {"at_depth_m": 50}}}, f9_vehicle_dict
    )
    with pytest.raises(ValueError, match="needs the constant_accel drive"):
        sim.run_ignition_specs(run.run, run.to_vehicle())


def test_union_tags_and_the_app_form() -> None:
    """One tuple of union tags derived from AssistConfig (linear_motor in it after it
    left PLANNED_MODELS), which the app's error locations strip; the app's form offers
    no linear motor (D-SP7-08): its site choices are the pad and the constant_accel silo,
    no drive key is a form field, and a request naming one is refused."""
    assert config.ASSIST_UNION_TAGS == ("none", "constant_accel", "linear_motor", "cable_winch")
    assert config.PLANNED_MODELS == ("cable_winch",)
    assert appform.ASSIST_UNION_TAGS == frozenset(config.ASSIST_UNION_TAGS)
    assert appform.FIELDS["site"].choices == ("pad", "silo")
    drive_keys = ("control", "force_max_kN", "power_max_MW", "force_rise_time_s")
    assert not set(drive_keys) & set(appform.FIELDS)
    assert isinstance(appform.parse_request({"site": "linear_motor"}), appform.Refusal)
    refused = appform.parse_request({"control": "force"})
    assert isinstance(refused, appform.Refusal) and refused.field is None


# -------------------------------------------------------- the push protocol seam


def test_push_boundaries_merge_the_drive_kinks() -> None:
    """With no drive kink the boundaries are the thrust kinks after the push start,
    sorted, as before SP7; a drive kink or the thrust clamp joins them, once within
    ZERO_SPAN_S of a kink already listed; kinks at or before the push start are
    dropped."""
    assert push_boundaries((2.0, 0.5, -1.0, 0.0), (), 0.0) == [0.5, 2.0]
    assert push_boundaries((2.0, 0.5), (("drive_ramp_end", 0.3),), 0.0) == [0.3, 0.5, 2.0]
    assert push_boundaries((0.5,), (("drive_ramp_end", 0.5 + ZERO_SPAN_S / 2),), 0.0) == [0.5]
    assert push_boundaries((), (("drive_ramp_end", 0.0),), 0.0) == []
    assert push_boundaries((0.0, 2.0), (), 0.0, 0.15) == [0.15, 2.0]
    assert push_boundaries((2.0,), (("drive_ramp_end", 0.5),), 0.0, 0.15) == [0.15, 0.5, 2.0]
    assert push_boundaries((2.0,), (), 0.0, -0.05) == [2.0]
    assert push_boundaries((2.0,), (), 0.0, 2.0 - ZERO_SPAN_S / 2) == [2.0]


def test_thrust_clamp_time_is_where_t_vac_reaches_the_back_pressure() -> None:
    """``prelude.thrust_clamp_time``: with share = p_amb A_e/T_full in (0, 1), a ramp
    t_ign + t_ramp share and a lag t_ign - tau ln(1 - share), where T_vac = p_amb A_e (the
    delivered thrust zero there, positive after); None for a step start, a failed
    schedule, vacuum and a back-pressure at or above T_full."""
    t_full, area, p_amb, t_ign = 8.0e6, 6.0, 101_325.0, -0.3
    share = p_amb * area / t_full

    def schedule(startup: Startup, fails: bool = False) -> ThrustSchedule:
        return ThrustSchedule(t_full, 3000.0, area, t_ign, startup, fails)

    ramp, lag = schedule(Startup("ramp", t_ramp_s=2.0)), schedule(Startup("lag", tau_s=0.4))
    for sched, expected in ((ramp, t_ign + 2.0 * share), (lag, t_ign - 0.4 * math.log(1 - share))):
        t_c = thrust_clamp_time(sched, p_amb)
        assert t_c is not None and math.isclose(t_c, expected, rel_tol=1e-15)
        assert math.isclose(sched.thrust_vac_N(t_c), p_amb * area, rel_tol=1e-12)
        assert sched.thrust_N(t_c - 1e-3, p_amb) == 0.0 < sched.thrust_N(t_c + 1e-3, p_amb)
    assert thrust_clamp_time(schedule(Startup()), p_amb) is None
    assert thrust_clamp_time(schedule(Startup("ramp", t_ramp_s=2.0), fails=True), p_amb) is None
    assert thrust_clamp_time(ramp, 0.0) is None
    assert thrust_clamp_time(lag, t_full / area) is None


def test_existing_models_keep_their_push() -> None:
    """constant_accel and none: push_time_exact, ``at_push_start`` returns the model
    itself, no kink, no watch, never a stall; the linear motor's are the opposite, its
    kink at t_r (none for a step) and its watches by law and taper."""
    ca = ConstantAccelAssist(3.0 * G0_MPS2, 0.0, A_BRAKE)
    pad = sim.NoAssist()
    for model in (ca, pad):
        assert model.push_time_exact is True
        assert model.at_push_start(5e5, 1e6, G, SILO) is model
        assert model.kink_times() == () and model.push_watches() == ()
        assert model.stall_reason() is None
    lm = _model(f_max=2e7, p_max=1e9)
    assert lm.push_time_exact is False and lm.allow_negative_drive is False
    assert lm.kink_times() == (("drive_ramp_end", T_R),)
    assert _model(f_max=2e7, p_max=1e9, t_r=0.0).kink_times() == ()
    bound = lm.at_push_start(5e5, 0.0, G, SILO)
    assert [w.name for w in bound.push_watches()] == ["power_limit"]
    accel = _model("acceleration", f_max=2e7, p_max=1e9, a_cmd=30.0, taper=5.0)
    names = [w.name for w in accel.at_push_start(5e5, 0.0, G, SILO).push_watches()]
    assert names == ["power_limit", "drive_cap", "taper_start"]
    with pytest.raises(ValueError, match="bind it with at_push_start"):
        lm.push_time_estimate(SILO)


@pytest.mark.parametrize(("rate", "direction"), [(1.0, 1), (-1.0, 1), (1.0, -1), (-1.0, -1)])
def test_fires_on_first_step_is_the_guards_own_test(rate: float, direction: int) -> None:
    """``engine.fires_on_first_step`` answers as ``integrate_phase``'s rule 3 does for an
    event at zero at t0 (x' = rate from x = 0, event x): True exactly when the phase would
    disarm the event with a note (moving into its direction), False when it moves away
    (no note, the event stays armed)."""
    zero = EventSpec("x_zero", lambda _t, y: float(y[0]), terminal=True, direction=direction)
    phase = PhaseSpec(
        "TOY", 0, 0.0, 1.0, lambda _t, _y, _p: np.array([rate]), None, (zero,), np.array([1e-9])
    )
    fires = fires_on_first_step(phase, zero, np.array([0.0]), SETTINGS)
    assert fires is (rate * direction > 0)
    res = integrate_phase(phase, np.array([0.0]), SETTINGS)
    assert any("disarmed" in note for note in res.notes) is fires


def test_step_command_capped_from_push_start_logs_drive_cap_at_t0(f9_vehicle: Vehicle) -> None:
    """A step command (t_r = 0) that the force cap already binds at push start logs
    drive_cap at t = 0 (no crossing follows) and flies the capped acceleration a_F from
    rest: v_e = sqrt(2 a_F L), t_push = sqrt(2 L / a_F); no drive_ramp_end."""
    m = f9_vehicle.liftoff_mass_kg()
    a_f = 3.0 * G0_MPS2
    model = _model("acceleration", f_max=m * (a_f + G), p_max=1e12, a_cmd=4.0 * G0_MPS2, t_r=0.0)
    exit_, trace = _push(f9_vehicle, model)
    assert exit_ is not None and trace.flags == ()
    t, z, v = _event(trace, "drive_cap")
    assert (t, z + L, v) == (0.0, 0.0, 0.0)
    assert "drive_ramp_end" not in [e.name for e in trace.events]
    assert math.isclose(exit_.sdot_mps, math.sqrt(2.0 * a_f * L), rel_tol=REL)
    assert math.isclose(exit_.t_release_s, math.sqrt(2.0 * L / a_f), rel_tol=REL)


def test_a_taper_toward_a_negative_holding_force_ends_in_drive_limit(
    f9_vehicle: Vehicle,
) -> None:
    """Hot with the full thrust above the weight, the force law's taper scales the force
    toward F_h = M g - T < 0, so the drive force crosses zero inside the taper: status
    drive_limit with the linear motor's own reason (constant_accel keeps its text), the
    run stopped on the track after taper_start."""
    m = f9_vehicle.liftoff_mass_kg()
    f_max = m * (3.0 * G0_MPS2 + G)
    exit_, trace = _push(f9_vehicle, _model(f_max=f_max, p_max=f_max * 1e3, taper=30.0), first=HOT)
    assert exit_ is None and trace.status == "drive_limit"
    t_limit = next(e.t_s for e in trace.events if e.name == "drive_limit")
    assert t_limit > next(e.t_s for e in trace.events if e.name == "taper_start")
    assert trace.flags == (
        f"drive_limit: the drive force crossed zero at t = {t_limit:.6g} s (the linear_motor "
        "drive would have to hold the vehicle back: its law asks for less force on the stack "
        "than the thrust's share (1 - f_imp) T supplies); the run stopped on the track",
    )
