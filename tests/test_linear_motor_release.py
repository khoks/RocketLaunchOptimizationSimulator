"""The linear motor's release (SP7 step S4a; docs/physics.md, "Linear motor", "Release at
a target speed" and "The power cap on the flown force"; design 4.6, 4.7; D-SP7-50).

Every closed-form expectation is computed here, never from the package. On the F9 (1-D,
the push flown by ``prelude.fly_track`` or the run by ``sim.simulate``), with M the stack
on the carriage (m_v + m_c), g = g_eff = mu/R_E^2, cold (the release-referenced ignition
pending through the push, so M is constant):

- the power cap on the flown, tapered force (D-SP7-50, KI-045): F = min(F_h + (min(F_lim,
  F_max) - F_h) w(s), P_max/sdot) under the force law. Vertical, with the corner before
  a 40 m taper: the power phase from v_c = P/F_max (survey 01 section 9, v_inf = P/(M g))
  runs on into the taper (the flown force P/sdot, the taper changes nothing while the
  cap binds) until the tapered force meets the cap, (M g + M a_f w(s)) v = P with w =
  (L - s)/s_t (power_limit_end, root of the power phase's s(v)); then the harmonic
  taper x'' = -(a_f/s_t) x, v_e^2 = v_1^2 + Omega^2 x_1^2, t_e = t_1 + atan(Omega
  x_1/v_1)/Omega. On an injected arc whose angle rises from 0 to pi/2 the holding force
  M g sin phi(s) exceeds P/sdot inside the taper (the edge S4's order missed, where its
  flown force F_h + (P/sdot - F_h) w was above the cap): F sdot <= P (1 + 1e-12) at
  every step and every sampled row, and the exit against an independent quadrature of
  the scalar ODE (solve_ivp, rtol 1e-12, restarted at every kink);
- the release at a target speed v_release (design 4.7): the acceleration law's plateau
  inverted, s = (v^2 + a^2 t_r^2/12)/(2 a), t = t_r/2 + v/a; the force law's force phase
  s = s_r + (v^2 - v_r^2)/(2 a_f), t = t_r + (v - v_r)/a_f and power phase s = s_c +
  s(v), t = t_c + t(v); a release speed at a kink of the drive (the end of the rise, the
  power corner); z, phi and x at the release position; the 1-D and planar release maps
  there; a release speed beyond reach releases at the track end with the flag
  release_speed_not_reached and the push unchanged bit for bit; the facility max(L,
  s_release + v^2/(2 a_b)) and the parked carriage at s_release + d_brake; a height-event
  ignition after an early release lights above the mouth, not above the release point;
- a fall back inside the shaft (fix rounds 3 and 4, P3-M1, P3-M2, P4-M1): the parked
  carriage is the floor of the flight model there, also under an apex above the open
  mouth; an unpowered fall ends on it at the drag-free energy speed and the time of an
  independent quadrature, a burn lit after the release turns the vehicle around above it
  as the same push moved up out of the ground does (from an apex inside the shaft or just
  above the mouth, so the outcome does not jump at apex = mouth), a carriage braking at
  less than g parks above the apex (an impact at once there), the failed ignition's items
  (the carriage crossing is the impact, nothing at the ground), a constant_accel push to a
  buried track exit (fix round 4, P4-m1); a failed ignition after an early release whose
  carriage parks at or above the ground falls to the ground at the energy speed with
  failed_t_return_s None and the early failed-ignition lines, 1-D and planar (fix round 5,
  P5-m1); the drag of a planar fall back onto the carriage on the drag-carrying
  generic_f9_class_2d against an independent radial quadrature (fix round 5, P5-m2: the
  F9 of the other planar tests has no aero block);
- the metrics: the release position and trigger read from the flown release, the push
  settings of KI-052 (the control law, a_cmd, s_taper, v_release); the config, the
  model's refusals and the release and shaft assumption lines.

Closed forms at 1e-9 relative (positions relative to the stroke, speeds to the exit
speed, times to the push time) with rtol 1e-11 (CLAUDE.md: <= 1e-9), the power cap in
the taper at rtol 1e-10 too.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml
from pydantic import ValidationError
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

from launchsim import sim
from launchsim.assist import build_assist
from launchsim.assist.constant_accel import ConstantAccelAssist
from launchsim.assist.linear_motor import (
    RELEASE_TRIGGER_TARGET_SPEED,
    RELEASE_TRIGGER_TRACK_END,
    RELEASE_TRIGGERS,
    LinearMotorAssist,
)
from launchsim.assist.track import VERTICAL, StraightTrack
from launchsim.atmosphere import ambient_scalar
from launchsim.config import LinearMotorConfig, VehicleConfig
from launchsim.constants import G0_MPS2, MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M
from launchsim.dynamics import InverseSquareGravity
from launchsim.guidance import GuidanceSpec
from launchsim.metrics import (
    LINEAR_MOTOR_METRICS,
    carriage_park_altitude_m,
    release_point,
)
from launchsim.phases import ASSIST_KIND, IgnitionSpec, IntegratorSettings, RunTrace
from launchsim.phases.engine import ATOL_MPS, TARGET_SPEED_EVENT, ev_release_speed
from launchsim.phases.planar import (
    SHAFT_TURNAROUND_EVENT,
    PlanarEnvironment,
    PlanarPlanner,
    resume_builder,
)
from launchsim.phases.prelude import (
    IGNITION_HEIGHT_EVENT,
    RELEASE_SPEED_NOT_REACHED,
    SHAFT_FALLBACK,
    TrackExit,
    early_release_assumption,
    fly_track,
    shaft_floor_m,
)
from launchsim.phases.vertical import VerticalPlanner
from launchsim.vehicle import Vehicle

G = MU_EARTH_M3S2 / R_EARTH_M**2
"""The 1-D track's g_eff [m/s^2] (omega_p = 0)."""
L = 100.0
T_R = 0.5
A_BRAKE = 5.0 * G0_MPS2
ETA = 0.5
REL = 1e-9
LIMIT_REL = 1e-12
SETTINGS = IntegratorSettings(rtol=1e-11)
SILO = StraightTrack(L, VERTICAL, -L)
COLD = IgnitionSpec(0.5)
"""Stage 1 0.5 s after the release: pending through the push, so the push is cold."""
LM_BLOCK: dict[str, Any] = {
    "model": "linear_motor",
    "stroke_m": 100,
    "control": "force",
    "force_max_kN": 22000,
    "power_max_MW": 1100.5,
    "force_rise_time_s": 0.5,
    "brake_decel_g": 5,
}
"""A valid force-law block as YAML gives it."""


def _model(
    control: str = "force",
    *,
    f_max: float,
    p_max: float,
    t_r: float = T_R,
    a_cmd: float | None = None,
    taper: float | None = None,
    v_release: float | None = None,
    a_brake: float = A_BRAKE,
) -> LinearMotorAssist:
    """A linear motor with the test's brake (5 g0 unless stated) and efficiency (0.5)."""
    return LinearMotorAssist(
        control=control,
        force_max_N=f_max,
        power_max_W=p_max,
        rise_time_s=t_r,
        carriage_mass_kg=0.0,
        brake_decel_mps2=a_brake,
        accel_command_mps2=a_cmd,
        stop_taper_m=taper,
        efficiency=ETA,
        g_eff_mps2=G,
        release_speed_mps=v_release,
    )


def _specs(vehicle: Vehicle, first: IgnitionSpec) -> dict[str, IgnitionSpec]:
    """The ignition specs of every stage: ``first`` for stage 1, the default for the rest."""
    specs = {name: IgnitionSpec() for name in vehicle.stage_names}
    specs[vehicle.stage_names[0]] = first
    return specs


def _planner(
    vehicle: Vehicle, first: IgnitionSpec = COLD, settings: IntegratorSettings = SETTINGS
) -> VerticalPlanner:
    """The 1-D planner of ``vehicle`` (mu/r^2, the track's g_eff = G) to stage-1 burnout."""
    return VerticalPlanner(
        vehicle,
        _specs(vehicle, first),
        InverseSquareGravity(MU_EARTH_M3S2),
        G,
        "stage1_burnout",
        settings,
    )


def _push(
    vehicle: Vehicle,
    model: LinearMotorAssist | ConstantAccelAssist,
    track: Any = SILO,
    settings: IntegratorSettings = SETTINGS,
) -> tuple[TrackExit | None, RunTrace]:
    """The push alone: ``fly_track`` in the 1-D layout, cold."""
    tr = _planner(vehicle, COLD, settings).new_builder()
    exit_ = fly_track(
        tr, model, track, COLD, vehicle=vehicle, settings=settings, g_eff_mps2=G, p_amb_pa=0.0
    )
    return exit_, tr.finish()


def _simulate(vehicle: Vehicle, model: LinearMotorAssist, track: Any = SILO) -> sim.Result:
    """The 1-D run of the push to stage-1 burnout."""
    return sim.simulate(
        vehicle=vehicle,
        ignition=_specs(vehicle, COLD),
        gravity=InverseSquareGravity(MU_EARTH_M3S2),
        g_eff_mps2=G,
        assist=model,
        track=track,
        start=None,
        end="stage1_burnout",
        settings=SETTINGS,
    )


def _steps(trace: RunTrace) -> list[tuple[float, float, float, Any, np.ndarray]]:
    """(t, s, sdot, phase, state) at every integrator step of every ASSIST phase."""
    out = []
    for res in trace.assist_phases():
        lay = res.spec.params.layout
        for i, t in enumerate(res.t):
            y = np.asarray(res.y[:, i], dtype=float)
            out.append((float(t), float(lay.get(y, "s_m")), float(lay.get(y, "sdot_mps")), res, y))
    return out


def _event(trace: RunTrace, name: str) -> tuple[float, float, float]:
    """(t [s], z [m], v [m/s]) of the one event called name (1-D view)."""
    found = [e for e in trace.events if e.name == name]
    assert len(found) == 1, (name, [e.name for e in trace.events])
    return found[0].t_s, found[0].value("z_m"), found[0].value("v_mps")


def _power_phase(v: float, v_c: float, v_inf: float, g: float) -> tuple[float, float]:
    """(t - t_c, s - s_c) of the vertical power phase at speed v from the corner v_c."""
    log = math.log((v_inf - v_c) / (v_inf - v))
    dt = ((v_c - v) + v_inf * log) / g
    ds = (0.5 * (v_c * v_c - v * v) + v_inf * (v_c - v) + v_inf * v_inf * log) / g
    return dt, ds


def _force_law_forms(m: float, f_max: float, v_c: float, g: float = G) -> dict[str, float]:
    """The cold vertical force law's rise from F_0 = M g, force phase and corner: a_f,
    v_r, s_r (end of the rise), t_c, s_c (the corner v_c = P/F_max), v_inf = P/(M g); g
    [m/s^2] the track's g_eff (the 1-D G, or the planar g_ref)."""
    a_f = f_max / m - g
    v_r, s_r = a_f * T_R / 2.0, a_f * T_R**2 / 6.0
    return {
        "a_f": a_f,
        "v_r": v_r,
        "s_r": s_r,
        "t_c": T_R + (v_c - v_r) / a_f,
        "s_c": s_r + (v_c**2 - v_r**2) / (2.0 * a_f),
        "v_inf": f_max * v_c / (m * g),
    }


# ------------------------------------------------- the power cap on the flown force


@pytest.mark.parametrize("rtol", [1e-11, 1e-10])
def test_the_power_cap_applies_to_the_tapered_force_in_closed_form(
    rtol: float, f9_vehicle: Vehicle
) -> None:
    """D-SP7-50, vertical and cold: F_max = M (3 g0 + g), corner v_c = 50 m/s, a 40 m
    taper entered on the power phase. The flown force is P/sdot into the taper (the
    power phase's t(v), s(v) at every step; taper_start at s_0 = L - s_t on it) until
    the tapered force meets the cap, (M g + M a_f (L - s(v))/s_t) v = P
    (power_limit_end at (t_1, s_1, v_1)); then F = M g + M a_f w(s) and x'' = -(a_f/s_t) x:
    v^2 = v_1^2 + Omega^2 (x_1^2 - x^2), v_e^2 = v_1^2 + Omega^2 x_1^2, t_e = t_1 +
    atan(Omega x_1/v_1)/Omega; F sdot <= P (1 + 1e-12) at every step."""
    m = f9_vehicle.liftoff_mass_kg()
    f_max = m * (3.0 * G0_MPS2 + G)
    v_c, s_t = 50.0, 40.0
    p_max = f_max * v_c
    cf = _force_law_forms(m, f_max, v_c)
    a_f, v_inf = cf["a_f"], cf["v_inf"]

    def s_of(v: float) -> float:
        return cf["s_c"] + _power_phase(v, v_c, v_inf, G)[1]

    def t_of(v: float) -> float:
        return cf["t_c"] + _power_phase(v, v_c, v_inf, G)[0]

    s_0 = L - s_t
    v_top = v_inf * (1.0 - 1e-12)
    v_0 = brentq(lambda v: s_of(v) - s_0, v_c, v_top, xtol=1e-14, rtol=8.9e-16)
    v_l = brentq(lambda v: s_of(v) - L, v_c, v_top, xtol=1e-14, rtol=8.9e-16)
    v_1 = brentq(
        lambda v: (m * G + m * a_f * (L - s_of(v)) / s_t) * v - p_max,
        v_0,
        v_l,
        xtol=1e-14,
        rtol=8.9e-16,
    )
    s_1, t_1 = s_of(v_1), t_of(v_1)
    x_1 = L - s_1
    omega = math.sqrt(a_f / s_t)
    v_e = math.sqrt(v_1**2 + omega**2 * x_1**2)
    t_e = t_1 + math.atan(omega * x_1 / v_1) / omega
    model = _model(f_max=f_max, p_max=p_max, taper=s_t)
    exit_, trace = _push(f9_vehicle, model, settings=IntegratorSettings(rtol=rtol))
    assert exit_ is not None and trace.flags == ()
    assert math.isclose(exit_.sdot_mps, v_e, rel_tol=REL)
    assert math.isclose(exit_.t_release_s, t_e, rel_tol=REL)
    names = [e.name for e in trace.events]
    expected = ["push_start", "drive_ramp_end", "power_limit", "taper_start", "power_limit_end"]
    assert names == expected, names
    t, z, v = _event(trace, "taper_start")
    assert math.isclose(t, t_of(v_0), rel_tol=REL) and math.isclose(v, v_0, rel_tol=REL)
    assert math.isclose(z + L, s_0, rel_tol=REL)
    t, z, v = _event(trace, "power_limit_end")
    assert math.isclose(t, t_1, rel_tol=REL) and math.isclose(v, v_1, rel_tol=REL)
    assert math.isclose(z + L, s_1, rel_tol=REL)
    counts = {"power": 0, "taper": 0}
    for t, s, sdot, res, y in _steps(trace):
        force = res.spec.params.forces(t, y).drive_force_N
        assert force * sdot <= p_max * (1.0 + LIMIT_REL)
        if sdot <= v_c or t <= cf["t_c"]:
            continue
        if t <= t_1:
            counts["power"] += 1
            dt, ds = _power_phase(sdot, v_c, v_inf, G)
            assert abs(t - (cf["t_c"] + dt)) <= REL * t_e and abs(s - (cf["s_c"] + ds)) <= REL * L
            assert math.isclose(force, p_max / sdot, rel_tol=1e-15)
        else:
            counts["taper"] += 1
            x = L - s
            assert abs(sdot - math.sqrt(v_1**2 + omega**2 * (x_1**2 - x * x))) <= REL * v_e
            assert math.isclose(force, m * G + m * a_f * x / s_t, rel_tol=1e-12)
    assert min(counts.values()) >= 2, counts


@dataclass(frozen=True)
class ArcTrack:
    """A test-only TrackGeometry: a circular arc of length length_m [m] from horizontal
    (phi(0) = 0) to vertical (phi(L) = pi/2), radius R = L/(pi/2), starting at
    start_altitude_m [m]: phi(s) = s/R, kappa = 1/R, z(s) = R (1 - cos(s/R))."""

    length_m: float
    start_altitude_m: float = 0.0

    @property
    def radius_m(self) -> float:
        """The arc's radius R = L / (pi/2) [m]."""
        return self.length_m / (0.5 * math.pi)

    def phi(self, s_m: float) -> float:
        """The track angle above horizontal [rad] at arc length s_m [m]: s/R."""
        return s_m / self.radius_m

    def kappa(self, s_m: float) -> float:
        """The signed curvature [1/m] at s_m [m]: 1/R (curving up)."""
        return 1.0 / self.radius_m

    def z(self, s_m: float) -> float:
        """The height [m] above the track start at s_m [m] (track frame, z up): R (1 -
        cos(s/R))."""
        return self.radius_m * (1.0 - math.cos(s_m / self.radius_m))


def _arc_quadrature(
    m: float, f_max: float, p_max: float, s_t: float, track: ArcTrack
) -> tuple[float, float]:
    """(t_e [s], v_e [m/s]) of the cold force-law push on the arc by an independent
    quadrature of the scalar ODE M sddot = F - M g sin phi(s), F = min(F_h + (min(F_lim(t),
    F_max) - F_h) w(s), P/sdot), F_h = M g sin phi(s), F_lim rising from F_0 = 0 (the
    arc starts horizontal) over T_R: solve_ivp at rtol 1e-12, restarted at every kink of
    F (the rise end, the cap binding or letting go, the taper start) so no step straddles
    one; ends at s = L."""

    def g_axial(s: float) -> float:
        return G * math.sin(track.phi(s))

    def tapered(t: float, s: float) -> float:
        hold = m * g_axial(s)
        limit = f_max * min(1.0, t / T_R)
        w = min(1.0, (L - s) / s_t)
        return hold + (limit - hold) * w

    def rhs(t: float, y: np.ndarray) -> list[float]:
        force = tapered(t, y[0])
        if y[1] > 0.0:
            force = min(force, p_max / y[1])
        return [y[1], force / m - g_axial(y[0])]

    def kink(fn: Any, direction: int) -> Any:
        def ev(t: float, y: np.ndarray) -> float:
            return fn(t, y)

        ev.terminal = True  # type: ignore[attr-defined]
        ev.direction = direction  # type: ignore[attr-defined]
        return ev

    fns = (
        lambda t, y: t - T_R,
        lambda t, y: tapered(t, y[0]) * y[1] - p_max,
        lambda t, y: y[0] - (L - s_t),
    )
    events = [kink(fn, d) for fn in fns for d in (1, -1)]
    end = kink(lambda t, y: y[0] - L, 1)
    t, y, fired = 0.0, np.zeros(2), None
    for _ in range(20):
        armed = [ev for k, ev in enumerate(events) if k != fired]
        sol = solve_ivp(
            rhs,
            (t, 60.0),
            y,
            method="DOP853",
            rtol=1e-12,
            atol=[1e-12, 1e-14],
            events=[*armed, end],
        )
        hits = [(float(te[0]), k) for k, te in enumerate(sol.t_events) if len(te)]
        t_hit, k_hit = min(hits)
        y = np.asarray(sol.y_events[k_hit][0], dtype=float)
        t = t_hit
        if k_hit == len(armed):
            return t, float(y[1])
        fired = events.index(armed[k_hit])
    raise AssertionError("the quadrature did not reach the track end")


def test_the_power_cap_binds_below_the_holding_force_on_an_arc(f9_vehicle: Vehicle) -> None:
    """The edge S4's order missed (D-SP7-50, KI-045): on an injected arc rising from
    horizontal to vertical, a push power-limited from v_c = 10 m/s carries a speed
    above P/F_h into a 60 m taper, where the holding force F_h = M g sin phi(s) exceeds
    P_max/sdot. The flown force is P_max/sdot there (the stack slows), so F sdot <=
    P_max (1 + 1e-12) at every integrator step and every sampled ASSIST row; S4's order,
    F_h + (min(F_lim, P/sdot) - F_h) w, would have flown more than 1.001 P_max at those
    steps (computed here). The exit against the scalar ODE's quadrature
    (``_arc_quadrature``) at 1e-9."""
    m = f9_vehicle.liftoff_mass_kg()
    arc = ArcTrack(L, -L)
    f_max = m * 3.0 * G0_MPS2
    s_t = 60.0
    p_max = f_max * 10.0
    result = _simulate(f9_vehicle, _model(f_max=f_max, p_max=p_max, taper=s_t), track=arc)
    assert result.status == "nominal"
    assert not [f for f in result.flags if not f.startswith("interface_tensile")], result.flags
    rows = result.timeseries[result.timeseries["phase"] == ASSIST_KIND]
    assert (rows["drive_power_W"] <= p_max * (1.0 + LIMIT_REL)).all()
    _exit, trace = _push(f9_vehicle, _model(f_max=f_max, p_max=p_max, taper=s_t), track=arc)
    assert _exit is not None
    edge, s4_worst = 0, 0.0
    for t, s, sdot, res, y in _steps(trace):
        force = res.spec.params.forces(t, y).drive_force_N
        assert force * sdot <= p_max * (1.0 + LIMIT_REL)
        hold = m * G * math.sin(arc.phi(s))
        if s > L - s_t and sdot > 0.0 and hold > p_max / sdot:
            edge += 1
            assert math.isclose(force, p_max / sdot, rel_tol=1e-15)
            w = (L - s) / s_t
            s4_force = hold + (min(f_max, p_max / sdot) - hold) * w
            s4_worst = max(s4_worst, s4_force * sdot / p_max)
    assert edge >= 3 and s4_worst > 1.001, (edge, s4_worst)
    t_e, v_e = _arc_quadrature(m, f_max, p_max, s_t, arc)
    assert math.isclose(_exit.sdot_mps, v_e, rel_tol=REL)
    assert math.isclose(_exit.t_release_s, t_e, rel_tol=REL)
    assert math.isclose(result.metrics["exit_speed_mps"], v_e, rel_tol=REL)


# ----------------------------------------------------- the release at a target speed


def test_release_at_a_target_speed_on_the_acceleration_plateau(f9_vehicle: Vehicle) -> None:
    """Acceleration law (a = 3 g0, no cap binds), v_release = 60 m/s on the plateau: the
    release where v^2 = 2 a s - a^2 t_r^2/12, s_rel = (v^2 + a^2 t_r^2/12)/(2 a), at t =
    t_r/2 + v/a; the TrackExit at the release position (z = -L + s_rel, phi = pi/2, x =
    0; release_position_m and trigger target_speed), the target_speed event there, every
    step at or below s_rel, the early-release assumption line in the 1-D model's words
    (no atmosphere, no kick: fix round 1, honesty M2; vacuum thrust at its p_amb 0, and the
    thrust in the delta-v, not the losses: fix round 2, H2-m2); through ``sim.simulate``
    the release map at z(s_rel) and the release metrics. Fix round 4: the line names the
    floor of the flight model in the shaft (the parked carriage, z_rel + v^2/(2 a_b) below
    the ground, V4-2), says the vehicle flies in the vented shaft after the release (H4-m4:
    not 'the rest', which a fall back never flies) and that the carriage brakes from the
    release point, past the track end when s + d > L (H4-m4); fix round 5 (M1): the floor
    clause says that a carriage braking at less than the vehicle's deceleration can park
    above an apex inside the shaft, where the run then ends at once."""
    m = f9_vehicle.liftoff_mass_kg()
    a = 3.0 * G0_MPS2
    f_max = 2.0 * m * (a + G)
    v_release = 60.0
    model = _model("acceleration", f_max=f_max, p_max=f_max * 1e3, a_cmd=a, v_release=v_release)
    exit_, trace = _push(f9_vehicle, model)
    s_rel = (v_release**2 + a * a * T_R**2 / 12.0) / (2.0 * a)
    t_rel = T_R / 2.0 + v_release / a
    assert exit_ is not None and trace.flags == ()
    assert math.isclose(exit_.sdot_mps, v_release, rel_tol=REL)
    assert math.isclose(exit_.t_release_s, t_rel, rel_tol=REL)
    assert exit_.release_trigger == RELEASE_TRIGGER_TARGET_SPEED == TARGET_SPEED_EVENT
    assert exit_.release_position_m is not None
    assert abs(exit_.release_position_m - s_rel) <= REL * L
    assert exit_.z_exit_m == -L + exit_.release_position_m
    assert exit_.phi_rad == VERTICAL and exit_.x_exit_m == 0.0
    t, z, v = _event(trace, TARGET_SPEED_EVENT)
    assert (t, z, v) == (exit_.t_release_s, exit_.z_exit_m, exit_.sdot_mps)
    assert max(s for _t, s, _v, _r, _y in _steps(trace)) == exit_.release_position_m
    floor = exit_.z_exit_m + v_release**2 / (2.0 * A_BRAKE)
    assert floor < 0.0  # the carriage parks below the mouth
    line = early_release_assumption(
        v_release,
        exit_.release_position_m,
        L,
        exit_.z_exit_m,
        0.0,
        aerodynamic=False,
        floor_m=shaft_floor_m(exit_.z_exit_m, VERTICAL, model.braking_distance_m(v_release)),
    )
    assert trace.assumptions == (line,)
    assert line == (
        f"linear_motor: released at the release speed 60 m/s at s = "
        f"{exit_.release_position_m:.6g} m, {L - exit_.release_position_m:.6g} m before the "
        f"track end (L = 100 m; the track exit at the ground, the silo mouth), at altitude "
        f"{exit_.z_exit_m:.6g} m: the vehicle flies in the vented shaft after the release as "
        "the 1-D flight flies everywhere: drag-free, with vacuum thrust (no atmosphere; no "
        "shaft flow model, no walls); the floor of the flight model in the shaft is the "
        f"parked carriage at z = {floor:.6g} m: a fall back onto it, from inside the shaft or "
        "through the open mouth, is an impact (no catch and re-hold); a carriage braking at "
        "less than the vehicle's deceleration can park above an apex inside the shaft, and "
        "the run then ends at once at that apex (the model has no contact with the carriage "
        "on its braking path); the carriage brakes "
        "from the release point (facility max(L, s + braking distance): within the stroke "
        "left when s + braking distance <= L, else past the track end; in place of L + "
        "braking distance); the ideal screening estimate is taken at this release speed, not "
        "at the speed at the track exit, which gravity and any thrust over the rest of the "
        "track change (the gravity over it is in the flight's losses, the thrust in its "
        "delta-v)"
    )
    # no floor line without a floor below the ground (fix round 4, V4-2)
    above = early_release_assumption(v_release, 99.0, L, -1.0, 0.0, aerodynamic=False, floor_m=35.0)
    assert "floor of the flight model" not in above
    # the 1-D model has no atmosphere and no kick (fix round 1); its p_amb is 0 (round 2)
    assert "open atmosphere" not in line and "kick" not in line
    assert "constant ambient pressure 101325 Pa" in early_release_assumption(
        v_release, 50.0, L, -50.0, 0.0, aerodynamic=False, p_amb_pa=101325.0
    )
    result = _simulate(f9_vehicle, model)
    met = result.metrics
    assert result.status == "nominal" and line in result.assumptions
    assert met["release_trigger"] == RELEASE_TRIGGER_TARGET_SPEED
    assert abs(met["release_position_m"] - s_rel) <= REL * L
    assert math.isclose(met["exit_speed_mps"], v_release, rel_tol=REL)
    assert math.isclose(met["push_time_s"], t_rel, rel_tol=REL)
    assert met["push_release_speed_mps"] == v_release
    assert met["push_accel_mean_mps2"] == met["exit_speed_mps"] / met["push_time_s"]
    release = next(e for e in result.events.itertuples() if e.event == "release")
    assert release.z_m == -L + met["release_position_m"]


@pytest.mark.parametrize("v_release", [40.0, 70.0])
def test_release_at_a_target_speed_under_the_force_law(
    v_release: float, f9_vehicle: Vehicle
) -> None:
    """Force law, vertical, cold (F_max = M (3 g0 + g), corner v_c = 50 m/s): a release
    speed on the force phase (40 m/s: s = s_r + (v^2 - v_r^2)/(2 a_f), t = t_r + (v -
    v_r)/a_f) and on the power phase (70 m/s: s = s_c + s(v), t = t_c + t(v) of the
    vertical power phase); the push never passes s_rel."""
    m = f9_vehicle.liftoff_mass_kg()
    f_max = m * (3.0 * G0_MPS2 + G)
    v_c = 50.0
    cf = _force_law_forms(m, f_max, v_c)
    if v_release < v_c:
        s_rel = cf["s_r"] + (v_release**2 - cf["v_r"] ** 2) / (2.0 * cf["a_f"])
        t_rel = T_R + (v_release - cf["v_r"]) / cf["a_f"]
    else:
        dt, ds = _power_phase(v_release, v_c, cf["v_inf"], G)
        s_rel, t_rel = cf["s_c"] + ds, cf["t_c"] + dt
    model = _model(f_max=f_max, p_max=f_max * v_c, v_release=v_release)
    exit_, trace = _push(f9_vehicle, model)
    assert exit_ is not None and trace.flags == ()
    assert exit_.release_trigger == RELEASE_TRIGGER_TARGET_SPEED
    assert math.isclose(exit_.sdot_mps, v_release, rel_tol=REL)
    assert math.isclose(exit_.t_release_s, t_rel, rel_tol=REL)
    assert exit_.release_position_m is not None
    assert abs(exit_.release_position_m - s_rel) <= REL * L
    assert exit_.z_exit_m == -L + exit_.release_position_m
    assert ("power_limit" in [e.name for e in trace.events]) is (v_release > v_c)
    assert all(s <= exit_.release_position_m for _t, s, _v, _r, _y in _steps(trace))


@pytest.mark.parametrize("kink", ["rise_end", "power_corner"])
def test_a_release_speed_at_a_kink_of_the_drive_releases_there(
    kink: str, f9_vehicle: Vehicle
) -> None:
    """A release speed equal to the speed at a kink of the force law: the end of the
    rise (v_r = a_f t_r/2 at t_r, s_r = a_f t_r^2/6: the sub-phase boundary) or the
    power corner (v_c = 50 m/s at t_c, s_c, where the power_limit watch, sdot - P/F_max,
    and the target_speed event share their root): the push releases there by the
    target_speed trigger, with no flag."""
    m = f9_vehicle.liftoff_mass_kg()
    f_max = m * (3.0 * G0_MPS2 + G)
    v_c = 50.0
    cf = _force_law_forms(m, f_max, v_c)
    if kink == "rise_end":
        v_release, s_rel, t_rel = cf["v_r"], cf["s_r"], T_R
    else:
        v_release, s_rel, t_rel = v_c, cf["s_c"], cf["t_c"]
    exit_, trace = _push(f9_vehicle, _model(f_max=f_max, p_max=f_max * v_c, v_release=v_release))
    assert exit_ is not None and trace.flags == ()
    assert exit_.release_trigger == RELEASE_TRIGGER_TARGET_SPEED
    assert math.isclose(exit_.sdot_mps, v_release, rel_tol=REL)
    assert math.isclose(exit_.t_release_s, t_rel, rel_tol=REL)
    assert exit_.release_position_m is not None
    assert abs(exit_.release_position_m - s_rel) <= REL * L


def test_a_release_speed_not_reached_releases_at_the_track_end(f9_vehicle: Vehicle) -> None:
    """A release speed 5 m/s above the push's speed at L: the track_end trigger at L,
    the flag release_speed_not_reached naming both speeds, and the push itself (its
    release time and state) bit for bit that of the same drive without a release speed
    (the event never fires, and scipy's steps do not depend on an event's presence);
    the metrics read the track end and the facility is L + d, to the bit."""
    m = f9_vehicle.liftoff_mass_kg()
    f_max = m * (3.0 * G0_MPS2 + G)
    plain = _model(f_max=f_max, p_max=f_max * 50.0)
    ref, ref_trace = _push(f9_vehicle, plain)
    assert ref is not None
    v_release = ref.sdot_mps + 5.0
    model = _model(f_max=f_max, p_max=f_max * 50.0, v_release=v_release)
    exit_, trace = _push(f9_vehicle, model)
    assert exit_ is not None
    assert exit_.t_release_s == ref.t_release_s and np.array_equal(exit_.y_track, ref.y_track)
    assert (exit_.z_exit_m, exit_.phi_rad, exit_.x_exit_m) == (0.0, VERTICAL, 0.0)
    assert (exit_.release_position_m, exit_.release_trigger) == (L, RELEASE_TRIGGER_TRACK_END)
    assert trace.flags == (
        f"{RELEASE_SPEED_NOT_REACHED}: the push reached {ref.sdot_mps:.6g} m/s at the track "
        f"end (s = L = 100 m), below the release speed {v_release:g} m/s; it released at the "
        "track end",
    )
    assert [e.name for e in trace.events] == [e.name for e in ref_trace.events]
    assert trace.assumptions == ()
    met = _simulate(f9_vehicle, model).metrics
    ref_met = _simulate(f9_vehicle, plain).metrics
    assert (met["release_position_m"], met["release_trigger"]) == (L, RELEASE_TRIGGER_TRACK_END)
    assert met["facility_length_m"] == ref_met["facility_length_m"]
    assert met["exit_speed_mps"] == ref_met["exit_speed_mps"]


def test_a_track_end_release_keeps_the_exit_of_sp1_bit_for_bit(f9_vehicle: Vehicle) -> None:
    """constant_accel and a linear motor without a release speed release at L: the
    TrackExit's z, phi and x are start + z(L), phi(L) and 0 exactly (the expressions of
    SP1), release_position_m L and trigger track_end; release_point reads (L,
    track_end) from the trace."""
    m = f9_vehicle.liftoff_mass_kg()
    f_max = m * (3.0 * G0_MPS2 + G)
    for model in (
        ConstantAccelAssist(3.0 * G0_MPS2, 0.0, A_BRAKE, g_eff_mps2=G),
        _model(f_max=f_max, p_max=f_max * 50.0),
    ):
        exit_, trace = _push(f9_vehicle, model)
        assert exit_ is not None
        assert exit_.z_exit_m == SILO.start_altitude_m + SILO.z(L)
        assert (exit_.phi_rad, exit_.x_exit_m) == (SILO.phi(L), 0.0)
        assert (exit_.release_position_m, exit_.release_trigger) == (L, RELEASE_TRIGGER_TRACK_END)
        assert release_point(trace, SILO) == (L, RELEASE_TRIGGER_TRACK_END)
        assert TARGET_SPEED_EVENT not in [e.name for e in trace.events]


@pytest.mark.parametrize("brake_g", [5.0, 1.5])
def test_facility_and_carriage_after_an_early_release(brake_g: float, f9_vehicle: Vehicle) -> None:
    """After a release at 60 m/s at s_rel (acceleration law, a = 3 g0) the carriage
    brakes from the release point: facility max(L, s_rel + v^2/(2 a_b)), L with a 5 g0 brake
    (s_rel + d = 98.2 m) and s_rel + d with 1.5 g0 (the braking track runs past the
    mouth); braking time v/a_b, brake energy (1/2) m_c v^2 (1 - g/a_b) at phi(s_rel); the
    parked carriage (``carriage_park_altitude_m``) at z = -L + s_rel + d; release_point
    gives (s_rel, target_speed)."""
    m = f9_vehicle.liftoff_mass_kg()
    a = 3.0 * G0_MPS2
    a_b = brake_g * G0_MPS2
    f_max = 2.0 * m * (a + G)
    model = _model(
        "acceleration", f_max=f_max, p_max=f_max * 1e3, a_cmd=a, v_release=60.0, a_brake=a_b
    )
    met = _simulate(f9_vehicle, model).metrics
    v, s_rel = met["exit_speed_mps"], met["release_position_m"]
    d = v * v / (2.0 * a_b)
    assert math.isclose(met["braking_distance_m"], d, rel_tol=1e-15)
    assert math.isclose(met["facility_length_m"], max(L, s_rel + d), rel_tol=1e-15)
    assert (met["facility_length_m"] == L) is (brake_g == 5.0)
    assert math.isclose(met["braking_time_s"], v / a_b, rel_tol=1e-15)
    assert met["brake_energy_J"] == 0.0 and met["brake_force_N"] == 0.0  # no carriage mass
    assert math.isclose(model.facility_length_m(SILO, v, s_rel), max(L, s_rel + d), rel_tol=1e-15)
    trace = _planner(f9_vehicle).run_track(model, SILO)
    s_trace, trigger = release_point(trace, SILO)
    assert (s_trace, trigger) == (s_rel, RELEASE_TRIGGER_TARGET_SPEED)
    park = carriage_park_altitude_m(trace, model, SILO)
    assert park is not None and math.isclose(park, -L + s_rel + d, rel_tol=1e-15)


def test_a_height_event_ignition_after_an_early_release_lights_above_the_mouth(
    f9_vehicle: Vehicle,
) -> None:
    """A first stage stated by a height reached by the altitude event (an injected spec,
    h = 20 m) on a push released at 60 m/s about 39 m below the mouth lights at z = 0 +
    h, the track exit's (the mouth's) altitude plus h, not the release point's: the
    ignition_height event at 20 m (within ATOL_M of the root's altitude)."""
    m = f9_vehicle.liftoff_mass_kg()
    a = 3.0 * G0_MPS2
    f_max = 2.0 * m * (a + G)
    model = _model("acceleration", f_max=f_max, p_max=f_max * 1e3, a_cmd=a, v_release=60.0)
    first = IgnitionSpec(trigger_kind="height_event", trigger_value=20.0)
    trace = _planner(f9_vehicle, first).run_track(model, SILO)
    t_rel, z_rel, _v = _event(trace, "release")
    assert z_rel < -30.0
    t, z, _v = _event(trace, IGNITION_HEIGHT_EVENT)
    assert t > t_rel and abs(z - 20.0) <= 1e-6


def test_a_planar_push_releases_at_its_target_speed(f9_vehicle: Vehicle) -> None:
    """The planar prelude (site rotation, the track's constant g_eff = g_ref): a force-law
    push released at 60 m/s, on its power phase (corner 50 m/s), at the closed-form
    position and time of that phase with g = g_ref (fix round 3, P3-m1: s_rel = s_c +
    s(v), t = t_c + t(v), at 1e-9 of L and of the push time), maps the release at r =
    r_datum + z(s_rel) with v_r = 60 m/s and v_theta = omega_p r; the flight start's shaft
    floor is the parked carriage, -L + s_rel + v^2/(2 a_b); the planar metrics' release
    position and trigger, and the facility max(L, s_rel + d); the target_speed event and
    the early-release line."""
    from launchsim.losses import assist_energy_budget
    from launchsim.metrics_planar import planar_track_metrics, sample_trace_planar

    omega = OMEGA_EARTH_RADS * math.cos(math.radians(28.5))
    env = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), omega, ambient_scalar)
    f_max = f9_vehicle.liftoff_mass_kg() * (3.0 * G0_MPS2 + env.g_ref_mps2)
    model = _model(f_max=f_max, p_max=f_max * 50.0, v_release=60.0)
    planner = PlanarPlanner(
        f9_vehicle,
        _specs(f9_vehicle, COLD),
        GuidanceSpec(50.0, 60.0, 60.0),
        env,
        "stage1_burnout",
        SETTINGS,
    )
    start = planner.start(model, SILO)
    assert start.status == "nominal" and start.y_fs is not None
    trace = start.prefix
    s_rel, trigger = release_point(trace, SILO)
    assert trigger == RELEASE_TRIGGER_TARGET_SPEED and 0.0 < s_rel < L
    cf = _force_law_forms(f9_vehicle.liftoff_mass_kg(), f_max, 50.0, env.g_ref_mps2)
    dt, ds = _power_phase(60.0, 50.0, cf["v_inf"], env.g_ref_mps2)
    assert abs(s_rel - (cf["s_c"] + ds)) <= REL * L
    assert math.isclose(trace.t_release_s, cf["t_c"] + dt, rel_tol=REL)
    floor = -L + s_rel + 60.0**2 / (2.0 * A_BRAKE)
    assert start.shaft_floor_m is not None
    assert math.isclose(start.shaft_floor_m, floor, rel_tol=1e-12)
    r = env.r_datum_m + (-L + s_rel)
    assert math.isclose(float(start.y_fs[0]), r, rel_tol=1e-15)
    assert math.isclose(float(start.y_fs[2]), 60.0, rel_tol=REL)
    assert math.isclose(float(start.y_fs[3]), omega * r, rel_tol=1e-15)
    line = next(a for a in trace.assumptions if "released at the release speed 60 m/s" in a)
    assert line.startswith("linear_motor: released at the release speed 60 m/s at s = ")
    assert "as in the open atmosphere at its altitude (no shaft flow model and no walls" in line
    assert "the offset at the ground is the downrange of the shaft_exit event" in line
    trace = planner.to_kick(start).prefix
    phases = trace.assist_phases()
    budget = assist_energy_budget(phases, phases[0].spec.params.layout, 0.0, env.g_ref_mps2)
    frame = sample_trace_planar(trace, f9_vehicle, 0.05)
    met = planar_track_metrics(trace, model, SILO, budget, frame)
    assert (met["release_position_m"], met["release_trigger"]) == (s_rel, trigger)
    v = met["exit_speed_mps"]
    assert math.isclose(v, 60.0, rel_tol=REL)
    assert met["facility_length_m"] == max(L, s_rel + v * v / (2.0 * A_BRAKE))
    assert met["stroke_m"] == L and met["push_release_speed_mps"] == 60.0


def _planar_planner(vehicle: Vehicle, first: IgnitionSpec) -> tuple[PlanarPlanner, float]:
    """A planar planner of the F9 at the 28.5 deg site (the kick at 50 m/s) and the
    track's g_ref [m/s^2]."""
    omega = OMEGA_EARTH_RADS * math.cos(math.radians(28.5))
    env = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), omega, ambient_scalar)
    planner = PlanarPlanner(
        vehicle, _specs(vehicle, first), GuidanceSpec(50.0, 60.0, 60.0), env, "insertion", SETTINGS
    )
    return planner, env.g_ref_mps2


def test_a_planar_flight_released_below_the_mouth_leaves_the_shaft(f9_vehicle: Vehicle) -> None:
    """A planar flight that starts in the vented shaft (released at 60 m/s about 36 m
    below the mouth; stage 1 lit 0.5 s later, still inside, where the kick begins): its
    burn sub-phases below the ground list shaft_exit and shaft_apex in place of the ground
    event (the engine's already-past rule would otherwise end the kick at once as an
    impact), so the flight leaves the shaft (shaft_exit logged at the mouth, within the
    planar root's resolution of r) and flies stage 1 to MECO (kick angle 0.025 rad,
    about what the scratch gate's fixed-guidance search solved) with the ground armed
    after it; a push released at 20 m/s about 93 m down, stage 1 to light 3 s later,
    coasts to its apex inside the shaft (20 m up) and falls back onto its parked carriage
    (fix round 3, P3-M1): GuidanceFailure impact before the kick, its message 'the
    vehicle's flight ended inside the shaft at t = ... s before the kick: shaft_fallback: the
    vehicle
    fell back ... onto the parked carriage at z = <floor> m', worded for the discarded
    trace ('the run ends in an impact there (the failed trace is not kept, so no event is
    recorded)', never 'is logged': fix round 3, H3-m2; never 'hit the ground': fix round
    2, P2-M2), its prefix 'the vehicle's flight ended inside the shaft' (fix round 4,
    H4-m2: an apex impact does not fall), with its touchdown speed (P4-m2; asserted since
    fix round 5, C5-m5: a positive |v_rel| below the unpowered coast's, since stage 1 lit
    3 s after the release and its thrust ramp slowed the fall); its coast from
    the release on a resumed builder (``_coast`` with the flight start's shaft floor) lists
    the impact at the floor in place of the already-past ground and ends in one impact
    there (the floor -L + s_rel + v^2/(2 a_b) to the event root) at the drag-free speed
    from its logged apex, sqrt(2 g_ref (z_apex - z_floor)) (1e-3 m/s: the test vehicle,
    generic_f9_class.yaml, has no aero block, so no drag; mu/r^2 and omega_p against g_ref;
    fix round 5, P5-m2, C5-m6), with the plain flag 'the impact is logged there', its speed
    |v_rel| at the impact (P4-m2) and no already-past note; with no floor the coast ends at
    once at the apex, its flag saying no floor is known."""
    from launchsim.guidance import GuidanceFailure
    from launchsim.phases.planar import SHAFT_EXIT_EVENT

    planner, g_ref = _planar_planner(f9_vehicle, COLD)
    f_max = f9_vehicle.liftoff_mass_kg() * (3.0 * G0_MPS2 + g_ref)
    start = planner.start(_model(f_max=f_max, p_max=f_max * 50.0, v_release=60.0), SILO)
    assert start.y_fs is not None and float(start.y_fs[0]) - planner.env.r_datum_m < -30.0
    kick = planner.to_kick(start)
    handover = planner.from_kick(0.025, kick, through_staging=False)  # about the solved kick
    events = [(e.name, e.t_s, e.value("alt_m")) for e in handover.prefix.events]
    names = [name for name, _t, _z in events]
    assert names.count(SHAFT_EXIT_EVENT) == 1 and "impact" not in names, names
    _name, t_exit, z_exit = next(e for e in events if e[0] == SHAFT_EXIT_EVENT)
    t_ign = next(t for name, t, _z in events if name == "ignition")
    assert t_ign < t_exit and abs(z_exit) <= 1e-3
    assert names.index("kick_start") < names.index(SHAFT_EXIT_EVENT) < names.index("propellant")
    late, _g = _planar_planner(f9_vehicle, IgnitionSpec(3.0))
    deep = late.start(_model(f_max=f_max, p_max=f_max * 50.0, v_release=20.0), SILO)
    assert deep.y_fs is not None and float(deep.y_fs[0]) - late.env.r_datum_m < -90.0
    with pytest.raises(GuidanceFailure) as info:
        late.to_kick(deep)
    assert info.value.kind == "impact"
    # fix round 2 (P2-M2): the failure, the run's one flag, says it fell back in the shaft
    message = info.value.message
    floor = deep.shaft_floor_m
    z_rel = float(deep.y_fs[0]) - late.env.r_datum_m
    assert floor is not None  # z_rel read off r: to the float spacing of r (1e-9 m)
    assert abs(floor - (z_rel + 20.0**2 / (2.0 * A_BRAKE))) <= 1e-8
    assert message.startswith("the vehicle's flight ended inside the shaft at t = ")
    assert (
        f"s before the kick: {SHAFT_FALLBACK}: the vehicle fell back inside the shaft, after a "
        f"release below the ground, onto the parked carriage at z = {floor:.6g} m" in message
    )
    ends = "the run ends in an impact there (the failed trace is not kept, so no event is recorded)"
    assert ends in message and "is logged" not in message  # fix round 3, H3-m2
    assert "hit the ground" not in message
    assert deep.t_fs_s is not None
    tr = resume_builder(deep.prefix, f9_vehicle.stage_names)
    _t, _y, how = late._coast(tr, "COAST_PRE_IGN", 0, deep.t_fs_s, None, deep.y_fs, floor_m=floor)
    assert how == "impact" and tr.status == "impact"
    assert len(tr.flags) == 1, tr.flags
    flag = tr.flags[0]
    assert flag.startswith("COAST_PRE_IGN at t = ")
    assert f": {SHAFT_FALLBACK}: the vehicle fell back inside the shaft, after a release " in flag
    assert f"onto the parked carriage at z = {floor:.6g} m" in flag
    assert "the impact is logged there" in flag
    falling = tr.phases[-1].spec
    assert [ev.name for ev in falling.events] == ["impact"] and falling.t0 > deep.t_fs_s
    impact = [e for e in tr.events if e.name == "impact"]
    apex = next(e for e in tr.events if e.name == "apex")
    assert len(impact) == 1 and abs(impact[0].value("alt_m") - floor) <= 1e-6
    drop = apex.value("alt_m") - floor
    v_fall = math.sqrt(2.0 * g_ref * drop)
    assert abs(impact[0].value("speed_rel_mps") - v_fall) <= 1e-3
    speed = impact[0].value("speed_rel_mps")
    assert f"m below the ground) at {speed:.6g} m/s: the impact is logged there" in flag
    assert "any touchdown on it ends the run, no catch and re-hold being modelled" in flag
    # fix round 5 (C5-m5): the GuidanceFailure message carries its own touchdown speed
    # (``_impact_failure``'s |v_rel|, P4-m2): positive, and below the unpowered coast's,
    # stage 1's thrust (lit 3 s after the release) having slowed the fall
    found = re.search(
        r"m below the ground\) at ([0-9.eE+-]+) m/s: the run ends in an impact there", message
    )
    assert found is not None, message
    assert 0.0 < float(found.group(1)) < speed
    bare = resume_builder(deep.prefix, f9_vehicle.stage_names)  # no floor: at once
    late._coast(bare, "COAST_PRE_IGN", 0, deep.t_fs_s, None, deep.y_fs)
    assert (
        "with no shaft floor known (no track release): the impact is logged at once"
        in (bare.flags[-1])
    )
    assert (
        next(e for e in bare.events if e.name == "impact").t_s
        == next(e for e in bare.events if e.name == "apex").t_s
    )
    assert not any("already past" in f for f in (*tr.flags, *bare.flags))


def test_a_planar_burn_turns_around_above_the_parked_carriage(f9_vehicle: Vehicle) -> None:
    """Fix round 3 (P3-M1), planar: a push released at 10 m/s about 98 m down, stage 1 lit
    0.5 s later (its 2 s ramp below the weight at first), stops rising inside the shaft and
    falls; its falling burn lists the turnaround and the impact at the shaft floor (the
    parked carriage) in place of the already-past ground, so the thrust turns it around
    above the carriage and to_kick reaches the kick (no GuidanceFailure), as the same push
    on the track moved up out of the ground does: the turnaround 0.1 m and the kick start
    1 m from that twin's (moved down by L; the back pressure is higher at 100 m less
    altitude, and mu/r^2 and omega_p differ; the test vehicle, generic_f9_class.yaml, has
    no aero block, so no drag enters: fix round 5, P5-m2). A KICK burn (FixedTilt,
    vertical) that starts inside the shaft falling at 5 m/s under full thrust lists
    SHAFT_TURNAROUND_EVENT beside the floor's impact, turns around above the carriage and
    leaves the shaft (shaft_exit at the mouth), with no impact."""
    from launchsim.guidance import FixedTilt
    from launchsim.phases.planar import SHAFT_EXIT_EVENT
    from launchsim.vehicle import Startup

    planner, g_ref = _planar_planner(f9_vehicle, IgnitionSpec(0.5))
    a = 3.0 * G0_MPS2
    f_max = 2.0 * f9_vehicle.liftoff_mass_kg() * (a + g_ref)
    model = _model("acceleration", f_max=f_max, p_max=f_max * 1e3, a_cmd=a, v_release=10.0)
    turns = []
    for track in (SILO, StraightTrack(L, VERTICAL, 0.0)):
        start = planner.start(model, track)
        kick = planner.to_kick(start)  # no GuidanceFailure: the thrust recovers it
        events = {e.name: e for e in kick.prefix.events}
        turns.append((events["turnaround"], events["kick_start"], start.shaft_floor_m))
    (turn, kick_at, floor), (twin_turn, twin_kick, _f) = turns
    assert floor is not None and floor < turn.value("alt_m") < 0.0
    assert abs(turn.value("alt_m") - (twin_turn.value("alt_m") - L)) <= 0.1
    assert abs(kick_at.value("alt_m") - (twin_kick.value("alt_m") - L)) <= 1.0
    assert kick_at.value("alt_m") > 0.0
    start = planner.start(model, SILO)
    assert start.y_fs is not None and start.t_fs_s is not None and floor is not None
    y = np.array(start.y_fs, dtype=float, copy=True)
    y[0] = planner.env.r_datum_m + floor + 10.0  # 10 m above the carriage
    y[2] = -5.0  # falling at 5 m/s
    t0 = start.t_fs_s
    schedule = f9_vehicle.stages[0].schedule(t0, Startup("step"), False)
    tr = resume_builder(start.prefix, f9_vehicle.stage_names)
    ended, _t, _y = planner._burn(tr, "KICK", 0, schedule, FixedTilt(0.0), (), t0, y, floor_m=floor)
    names = [e.name for e in tr.events[len(start.prefix.events) :]]
    assert names[:2] == [SHAFT_TURNAROUND_EVENT, SHAFT_EXIT_EVENT] and "impact" not in names
    assert ended == "propellant" and tr.flags == list(start.prefix.flags)
    turnaround = next(e for e in tr.events if e.name == SHAFT_TURNAROUND_EVENT)
    assert floor < turnaround.value("alt_m") < floor + 10.0
    falling = next(ph.spec for ph in tr.phases if ph.spec.t0 == t0)
    assert [ev.name for ev in falling.events] == ["propellant", "impact", SHAFT_TURNAROUND_EVENT]


def _shaft_fall(
    t_rel: float, z_rel: float, v_release: float, z_floor: float
) -> tuple[float, float]:
    """(time [s] after the release, speed [m/s]) at which a drag-free vertical coast under
    mu/r^2 released at z_rel [m] rising at v_release [m/s] comes back down to z_floor [m]
    below its apex: an independent quadrature of z'' = -mu/(R_E + z)^2 (solve_ivp, rtol
    1e-12, the downward crossing as its terminal event), the speed its own energy
    integral."""

    def rhs(_t: float, y: np.ndarray) -> list[float]:
        return [y[1], -MU_EARTH_M3S2 / (R_EARTH_M + y[0]) ** 2]

    def down(_t: float, y: np.ndarray) -> float:
        return float(y[0] - z_floor) if y[1] < 0.0 else 1.0

    down.terminal = True  # type: ignore[attr-defined]
    down.direction = -1  # type: ignore[attr-defined]
    sol = solve_ivp(rhs, (0.0, 60.0), [z_rel, v_release], rtol=1e-12, atol=1e-12, events=down)
    v2 = v_release**2 + 2.0 * MU_EARTH_M3S2 * (
        1.0 / (R_EARTH_M + z_floor) - 1.0 / (R_EARTH_M + z_rel)
    )
    return t_rel + float(sol.t_events[0][0]), math.sqrt(v2)


def test_a_fall_back_inside_the_shaft_ends_on_the_parked_carriage(f9_vehicle: Vehicle) -> None:
    """1-D (fix round 3, P3-M1), a push released at 10 m/s about 98 m below the mouth
    (acceleration law, a = 3 g0, a 5 g0 brake): unlit (stage 1 lit 3 s after the release)
    it coasts to its apex inside the shaft and falls back; its falling coast lists the
    impact at the shaft floor, the parked carriage z_rel + v^2/(2 a_b)
    (``metrics.carriage_park_altitude_m``, ``prelude.shaft_floor_m``), in place of the
    already-past ground, and ends there at the time of an independent quadrature and the
    drag-free energy speed (1e-9 relative; the root to 1e-9 m), with the one plain flag
    'FALL_PRE_IGN at t = ...: shaft_fallback: the vehicle fell back inside the shaft ...
    onto the parked carriage at z = ...: the impact is logged there', not the engine's
    already-past note. With a 0.5 g0 brake the carriage parks above the apex (its
    braking path meets the vehicle, where the model has no contact): the falling coast
    starts below the floor and the run ends at once at the apex (v = 0), its flag saying
    so."""
    m = f9_vehicle.liftoff_mass_kg()
    a = 3.0 * G0_MPS2
    f_max = 2.0 * m * (a + G)
    model = _model("acceleration", f_max=f_max, p_max=f_max * 1e3, a_cmd=a, v_release=10.0)
    trace = _planner(f9_vehicle, IgnitionSpec(3.0)).run_track(model, SILO)
    assert trace.status == "impact"
    assert len(trace.flags) == 1, trace.flags
    flag = trace.flags[0]
    t_rel, z_rel, v_release = _event(trace, "release")
    t_imp, z_imp, v_imp = _event(trace, "impact")
    floor = z_rel + v_release**2 / (2.0 * A_BRAKE)
    park = carriage_park_altitude_m(trace, model, SILO)
    assert park is not None and math.isclose(park, floor, rel_tol=1e-15)
    assert park == shaft_floor_m(z_rel, VERTICAL, model.braking_distance_m(v_release))
    assert abs(z_imp - floor) <= 1e-9
    t_fall, v_fall = _shaft_fall(t_rel, z_rel, v_release, floor)
    assert math.isclose(t_imp, t_fall, rel_tol=REL) and math.isclose(-v_imp, v_fall, rel_tol=REL)
    assert flag.startswith(f"FALL_PRE_IGN at t = {t_imp:.6g} s: {SHAFT_FALLBACK}: the vehicle ")
    assert f"onto the parked carriage at z = {z_imp:.6g} m" in flag
    assert f"m below the ground) at {-v_imp:.6g} m/s: the impact is logged there" in flag
    assert "the impact is logged there" in flag and "already past" not in flag
    assert _event(trace, "apex")[0] < t_imp
    soft = _model(
        "acceleration",
        f_max=f_max,
        p_max=f_max * 1e3,
        a_cmd=a,
        v_release=10.0,
        a_brake=0.5 * G0_MPS2,
    )
    trace = _planner(f9_vehicle, IgnitionSpec(3.0)).run_track(soft, SILO)
    assert trace.status == "impact" and len(trace.flags) == 1
    t_imp, z_imp, v_imp = _event(trace, "impact")
    assert _event(trace, "apex")[0] == t_imp and abs(v_imp) <= 1e-6
    park = carriage_park_altitude_m(trace, soft, SILO)
    assert park is not None and z_imp < park
    assert (
        f"FALL_PRE_IGN at t = {t_imp:.6g} s: {SHAFT_FALLBACK}: the vehicle stopped rising "
        f"{-z_imp:.6g} m below the ground (z = {z_imp:.6g} m), inside the shaft after a "
        f"release below the ground, at or below the parked carriage's altitude z = "
        f"{park:.6g} m"
    ) in trace.flags[0]
    assert trace.flags[0].endswith("the impact is logged at once at that apex")


def test_a_burn_lit_after_a_release_in_the_shaft_turns_around_above_the_carriage(
    f9_vehicle: Vehicle,
) -> None:
    """1-D (fix round 3, P3-M1): released at 10 m/s about 98 m down and lit 0.5 s later
    (the shipped 2 s ramp below the weight at first), the burn stops rising inside the
    shaft; its falling sub-phase lists the turnaround and the impact at the parked
    carriage (in place of the already-past ground), so the thrust turns the vehicle around
    above the carriage and it flies on to stage-1 burnout (status nominal, no flag), as
    the same push on the track moved up so the release lies above the ground does: the
    turnaround 5e-3 m and 1e-3 s from that twin's (moved down by L; mu/r^2 differs by
    about 3e-5 between the two release radii)."""
    m = f9_vehicle.liftoff_mass_kg()
    a = 3.0 * G0_MPS2
    f_max = 2.0 * m * (a + G)
    model = _model("acceleration", f_max=f_max, p_max=f_max * 1e3, a_cmd=a, v_release=10.0)
    trace = _planner(f9_vehicle, IgnitionSpec(0.5)).run_track(model, SILO)
    twin = _planner(f9_vehicle, IgnitionSpec(0.5)).run_track(model, StraightTrack(L, VERTICAL, 0.0))
    assert trace.status == twin.status == "nominal" and trace.flags == () == twin.flags
    names = [e.name for e in trace.events]
    assert "impact" not in names and names[-1] == "end"
    t_turn, z_turn, _v = _event(trace, "turnaround")
    t_twin, z_twin, _v = _event(twin, "turnaround")
    park = carriage_park_altitude_m(trace, model, SILO)
    assert park is not None and park < z_turn < 0.0
    assert abs(z_turn - (z_twin - L)) <= 5e-3 and abs(t_turn - t_twin) <= 1e-3
    falling = next(ph.spec for ph in trace.phases if ph.spec.kind == "BURN" and ph.spec.sigma == -1)
    assert [ev.name for ev in falling.events] == ["propellant", "turnaround", "impact"]


def test_a_failed_ignition_falls_back_onto_the_parked_carriage(f9_vehicle: Vehicle) -> None:
    """1-D, fix round 3 (P3-M2): released at 15 m/s about 96 m down with stage 1's
    ignition failed (end impact), the fall back ends on the parked carriage: the carriage
    items are the impact's (failed_t_carriage_s at the quadrature's time, its speed the
    energy integral's, 1e-9 relative), failed_impact_speed_mps (at the ground) and
    failed_t_return_s are None (the fall ends on the carriage, below the ground and above
    the release altitude), the apex items as before, the shaft-bottom speed the obstacle-free
    value through the carriage (v^2 = v_c^2 + 2 g_eff (z_c + L)); the flags (the planner's
    shaft_fallback and the failed-ignition flag naming the items, fix round 4: 'the fall
    ends on the carriage, below the ground, whether or not it passed the mouth') and
    FAILED_IGNITION_SHAFT_ASSUMPTIONS in place of FAILED_IGNITION_TRACK_ASSUMPTIONS."""
    m = f9_vehicle.liftoff_mass_kg()
    a = 3.0 * G0_MPS2
    f_max = 2.0 * m * (a + G)
    model = _model("acceleration", f_max=f_max, p_max=f_max * 1e3, a_cmd=a, v_release=15.0)
    specs = _specs(f9_vehicle, IgnitionSpec(0.5, fails=True))
    result = sim.simulate(
        vehicle=f9_vehicle,
        ignition=specs,
        gravity=InverseSquareGravity(MU_EARTH_M3S2),
        g_eff_mps2=G,
        assist=model,
        track=SILO,
        start=None,
        end="impact",
        settings=SETTINGS,
    )
    met = result.metrics
    assert result.status == "impact"
    release = next(e for e in result.events.itertuples() if e.event == "release")
    z_rel, v_release, t_rel = float(release.z_m), float(release.v_mps), float(release.t_s)
    floor = z_rel + v_release**2 / (2.0 * A_BRAKE)
    t_fall, v_fall = _shaft_fall(0.0, z_rel, v_release, floor)
    assert math.isclose(met["failed_carriage_alt_m"], floor, rel_tol=1e-15)
    assert math.isclose(met["failed_t_carriage_s"], t_fall, rel_tol=REL)
    assert math.isclose(met["failed_speed_at_carriage_mps"], v_fall, rel_tol=REL)
    assert met["impact_t_s"] == met["failed_t_carriage_s"]
    assert met["failed_impact_speed_mps"] is None and met["failed_t_return_s"] is None
    assert met["failed_apex_alt_m"] > floor and met["failed_t_apex_s"] < met["failed_t_carriage_s"]
    v_bottom = math.sqrt(met["impact_speed_mps"] ** 2 + 2.0 * G * (floor + L))
    assert math.isclose(met["failed_speed_at_shaft_bottom_mps"], v_bottom, rel_tol=1e-12)
    shaft = [f for f in result.flags if f"{SHAFT_FALLBACK}: " in f]
    assert len(shaft) == 1 and shaft[0].startswith("FALL at t = ")
    assert "onto the parked carriage" in shaft[0]
    failed = [f for f in result.flags if f.startswith("failed ignition: the vehicle fell back")]
    assert failed == [_carriage_flag(floor)]
    assert all(line in result.assumptions for line in sim.FAILED_IGNITION_SHAFT_ASSUMPTIONS)
    assert not set(sim.FAILED_IGNITION_TRACK_ASSUMPTIONS) & set(result.assumptions)
    assert t_rel > 0.0


def _carriage_flag(floor: float) -> str:
    """The failed-ignition flag of an impact on the parked carriage at floor [m]
    (``metrics.failed_ignition_flags``, fix round 4)."""
    return (
        f"failed ignition: the vehicle fell back inside the shaft and its impact is at z = "
        f"{floor:.6g} m, on the parked carriage (failed_t_carriage_s and "
        "failed_speed_at_carriage_mps are its time and speed); failed_impact_speed_mps (at "
        "the ground) and failed_t_return_s are None (the fall ends on the carriage, below the "
        "ground, whether or not it passed the mouth, and above the release altitude), and "
        "the shaft-bottom speed is the obstacle-free value through the carriage"
    )


def _failed_run(
    vehicle: Vehicle, assist: LinearMotorAssist | ConstantAccelAssist, track: Any
) -> sim.Result:
    """The 1-D run of ``assist`` on ``track`` with stage 1's ignition failed (end impact)."""
    return sim.simulate(
        vehicle=vehicle,
        ignition=_specs(vehicle, IgnitionSpec(0.5, fails=True)),
        gravity=InverseSquareGravity(MU_EARTH_M3S2),
        g_eff_mps2=G,
        assist=assist,
        track=track,
        start=None,
        end="impact",
        settings=SETTINGS,
    )


@pytest.mark.parametrize("v_release", [38.0, 38.5])
def test_a_fall_back_through_the_open_mouth_turns_around_above_the_carriage(
    v_release: float, f9_vehicle: Vehicle
) -> None:
    """Fix round 4 (P4-M1), 1-D: released below the mouth at 38.0 and 38.5 m/s (a = 3 g0,
    a 5 g0 brake) and lit 4 s later, the vehicle's apex lies 1.5 m below the mouth and 1.1
    m above it; either way it falls back into the shaft (over the open mouth in the second
    case: the 1-D flight never leaves the shaft's axis), its falling burn lists the
    turnaround and the impact at the parked carriage (below the ground) in place of the
    ground, and its thrust turns it around above the carriage: status nominal, no flag,
    both turnarounds within 0.02 m and 1e-3 s of the same push moved up out of the ground
    (moved down by L; mu/r^2 differs by about 3e-5 between the two release radii, about
    1 cm over the 8.5 s flight), so the outcome does not jump at apex = mouth (before the
    fix the 38.5 m/s run ended with an impact at z = 0 at 4.2 m/s)."""
    m = f9_vehicle.liftoff_mass_kg()
    a = 3.0 * G0_MPS2
    f_max = 2.0 * m * (a + G)
    model = _model("acceleration", f_max=f_max, p_max=f_max * 1e3, a_cmd=a, v_release=v_release)
    trace = _planner(f9_vehicle, IgnitionSpec(4.0)).run_track(model, SILO)
    twin = _planner(f9_vehicle, IgnitionSpec(4.0)).run_track(model, StraightTrack(L, VERTICAL, 0.0))
    assert trace.status == twin.status == "nominal" and trace.flags == () == twin.flags
    _t, z_apex, _v = _event(trace, "apex")
    assert (z_apex > 0.0) == (v_release == 38.5)
    t_turn, z_turn, _v = _event(trace, "turnaround")
    t_twin, z_twin, _v = _event(twin, "turnaround")
    park = carriage_park_altitude_m(trace, model, SILO)
    assert park is not None and park < z_turn < 0.0
    assert abs(z_turn - (z_twin - L)) <= 0.02 and abs(t_turn - t_twin) <= 1e-3
    falling = next(ph.spec for ph in trace.phases if ph.spec.kind == "BURN" and ph.spec.sigma == -1)
    assert [ev.name for ev in falling.events] == ["propellant", "turnaround", "impact"]


def test_a_failed_ignition_falls_back_through_the_open_mouth_onto_the_carriage(
    f9_vehicle: Vehicle,
) -> None:
    """Fix round 4 (P4-M1), 1-D: released at 50 m/s about 57 m below the mouth (the gate's
    lm_cmd_target setting: a = 3 g0, a 5 g0 brake) with stage 1's ignition failed, the
    vehicle rises 70 m above the mouth and falls back through it onto the carriage parked
    31.7 m below it: the impact on the carriage at the time of an independent quadrature
    and the drag-free energy speed (1e-9 relative), the carriage items its time and speed,
    failed_impact_speed_mps and failed_t_return_s None, the shaft flag with the touchdown
    speed (P4-m2), the failed-ignition flag and FAILED_IGNITION_SHAFT_ASSUMPTIONS (never
    FAILED_IGNITION_TRACK_ASSUMPTIONS' 'beyond the track exit'); before the fix it hit the
    ground at z = 0 at 37.1 m/s with the carriage items None."""
    m = f9_vehicle.liftoff_mass_kg()
    a = 3.0 * G0_MPS2
    f_max = 2.0 * m * (a + G)
    model = _model("acceleration", f_max=f_max, p_max=f_max * 1e3, a_cmd=a, v_release=50.0)
    result = _failed_run(f9_vehicle, model, SILO)
    met = result.metrics
    assert result.status == "impact"
    release = next(e for e in result.events.itertuples() if e.event == "release")
    z_rel, v_release = float(release.z_m), float(release.v_mps)
    floor = z_rel + v_release**2 / (2.0 * A_BRAKE)
    assert floor < 0.0 < met["failed_apex_alt_m"]
    t_fall, v_fall = _shaft_fall(0.0, z_rel, v_release, floor)
    assert math.isclose(met["failed_t_carriage_s"], t_fall, rel_tol=REL)
    assert math.isclose(met["failed_speed_at_carriage_mps"], v_fall, rel_tol=REL)
    assert met["impact_speed_mps"] == met["failed_speed_at_carriage_mps"]
    assert met["failed_impact_speed_mps"] is None and met["failed_t_return_s"] is None
    shaft = [f for f in result.flags if f"{SHAFT_FALLBACK}: " in f]
    assert len(shaft) == 1 and shaft[0].startswith("FALL at t = ")
    assert f"onto the parked carriage at z = {floor:.6g} m" in shaft[0]
    assert f"below the ground) at {met['impact_speed_mps']:.6g} m/s" in shaft[0]
    assert _carriage_flag(floor) in result.flags
    assert all(line in result.assumptions for line in sim.FAILED_IGNITION_SHAFT_ASSUMPTIONS)
    assert not set(sim.FAILED_IGNITION_TRACK_ASSUMPTIONS) & set(result.assumptions)
    impact = next(e for e in result.events.itertuples() if e.event == "impact")
    assert abs(float(impact.z_m) - floor) <= 1e-9


def test_a_planar_fall_back_through_the_open_mouth_before_the_kick(f9_vehicle: Vehicle) -> None:
    """Fix round 4 (P4-M1), planar: released at 38.5 m/s and lit 4 s later, the vehicle
    rises about 1 m above the mouth before its thrust is up; before its kick it is over the
    shaft (a few centimetres of Coriolis drift), so its falling vertical rise lists the
    impact at the parked carriage in place of the ground, and to_kick turns it around above
    the carriage and reaches the kick (before the fix: GuidanceFailure 'hit the ground at t
    = 6.03 s before the kick'), the turnaround within 0.2 m and the kick start within 1 m
    of the same push moved up out of the ground (the shaft's higher back pressure, and
    mu/r^2 and omega_p at the lower radius); the failed ignition at 50 m/s ends on the
    carriage, its speed within 1e-3 m/s of sqrt(v^2 + 2 g_ref (z_rel - z_floor)) (mu/r^2
    and omega_p against g_ref over the 100 m climb; 8e-5 m/s measured), with the shaft
    flag, and no GuidanceFailure. The test vehicle, generic_f9_class.yaml, has no aero
    block, so no drag enters either comparison (fix round 5, P5-m2, C5-m6); the drag of a
    planar shaft fall-back is checked on generic_f9_class_2d by
    ``test_a_planar_fall_back_with_drag_matches_a_radial_quadrature``."""
    planner, g_ref = _planar_planner(f9_vehicle, IgnitionSpec(4.0))
    a = 3.0 * G0_MPS2
    f_max = 2.0 * f9_vehicle.liftoff_mass_kg() * (a + g_ref)
    model = LinearMotorAssist(
        control="acceleration",
        force_max_N=f_max,
        power_max_W=f_max * 1e3,
        rise_time_s=T_R,
        carriage_mass_kg=0.0,
        brake_decel_mps2=A_BRAKE,
        accel_command_mps2=a,
        efficiency=ETA,
        g_eff_mps2=g_ref,
        release_speed_mps=38.5,
    )
    turns = []
    for track in (SILO, StraightTrack(L, VERTICAL, 0.0)):
        start = planner.start(model, track)
        kick = planner.to_kick(start)  # no GuidanceFailure
        events = {e.name: e for e in kick.prefix.events}
        turns.append((events["apex"], events["turnaround"], events["kick_start"]))
    (apex, turn, kick_at), (_a, twin_turn, twin_kick) = turns
    floor = planner.start(model, SILO).shaft_floor_m
    assert floor is not None and floor < turn.value("alt_m") < 0.0 < apex.value("alt_m")
    assert abs(turn.value("alt_m") - (twin_turn.value("alt_m") - L)) <= 0.2
    assert abs(kick_at.value("alt_m") - (twin_kick.value("alt_m") - L)) <= 1.0
    failed = PlanarPlanner(
        f9_vehicle,
        _specs(f9_vehicle, IgnitionSpec(0.5, fails=True)),
        planner.guidance,
        planner.env,
        "impact",
        SETTINGS,
    )
    fast = LinearMotorAssist(
        control="acceleration",
        force_max_N=f_max,
        power_max_W=f_max * 1e3,
        rise_time_s=T_R,
        carriage_mass_kg=0.0,
        brake_decel_mps2=A_BRAKE,
        accel_command_mps2=a,
        efficiency=ETA,
        g_eff_mps2=g_ref,
        release_speed_mps=50.0,
    )
    trace = failed.run(None, fast, SILO)
    assert trace.status == "impact"
    impact = next(e for e in trace.events if e.name == "impact")
    release = next(e for e in trace.events if e.name == "release")
    start = failed.start(fast, SILO)
    assert start.shaft_floor_m is not None
    assert abs(impact.value("alt_m") - start.shaft_floor_m) <= 1e-6
    assert max(e.value("alt_m") for e in trace.events if e.name == "apex") > 0.0
    drop = release.value("alt_m") - start.shaft_floor_m
    v_free = math.sqrt(release.value("speed_rel_mps") ** 2 + 2.0 * g_ref * drop)
    assert abs(impact.value("speed_rel_mps") - v_free) <= 1e-3
    shaft = [f for f in trace.flags if f"{SHAFT_FALLBACK}: " in f]
    assert len(shaft) == 1 and "onto the parked carriage" in shaft[0]


def test_a_buried_constant_accel_exit_falls_back_onto_its_carriage(f9_vehicle: Vehicle) -> None:
    """Fix round 4 (P4-m1, C4-m2): the shaft floor applies to any release below the ground,
    a constant_accel push to a buried track exit included (TrackConfig allows
    exit_altitude_m < 0; no shipped experiment has one). A 1 g0 push of 20 m to an exit 50
    m below the ground with stage 1's ignition failed: the apex 20 m above the exit, inside
    the shaft, and the impact on the carriage parked v0^2/(2 a_b) above the exit, at the
    time of an independent quadrature and the drag-free energy speed (1e-9 relative; at
    HEAD the engine's already-past rule ended it at once at the apex with an opaque note),
    with the shaft flag and FAILED_IGNITION_SHAFT_ASSUMPTIONS. A 3 g0 push of 100 m to an
    exit 50 m below the ground, whose carriage parks 10 m above the ground, keeps Phase 1's
    obstacle-free fall to the ground (the floor lies above the ground: impact at z = 0 at
    the energy speed, FAILED_IGNITION_TRACK_ASSUMPTIONS, no shaft flag)."""
    buried = StraightTrack(20.0, VERTICAL, -70.0)
    ca = ConstantAccelAssist(G0_MPS2, 0.0, A_BRAKE, g_eff_mps2=G)
    result = _failed_run(f9_vehicle, ca, buried)
    met = result.metrics
    v0 = math.sqrt(2.0 * G0_MPS2 * 20.0)
    floor = -50.0 + v0 * v0 / (2.0 * A_BRAKE)
    t_rel = next(e for e in result.events.itertuples() if e.event == "release").t_s
    assert result.status == "impact" and t_rel > 0.0
    assert math.isclose(met["failed_carriage_alt_m"], floor, rel_tol=1e-12)
    assert -50.0 < met["failed_apex_alt_m"] < 0.0
    t_fall, v_fall = _shaft_fall(0.0, -50.0, v0, floor)
    assert math.isclose(met["failed_t_carriage_s"], t_fall, rel_tol=REL)
    assert math.isclose(met["failed_speed_at_carriage_mps"], v_fall, rel_tol=REL)
    assert met["failed_impact_speed_mps"] is None
    assert any(
        f"{SHAFT_FALLBACK}: the vehicle fell back inside the shaft" in f for f in result.flags
    )
    assert not any("already past" in f for f in result.flags)
    assert all(line in result.assumptions for line in sim.FAILED_IGNITION_SHAFT_ASSUMPTIONS)
    deep = StraightTrack(L, VERTICAL, -150.0)
    ca3 = ConstantAccelAssist(3.0 * G0_MPS2, 0.0, A_BRAKE, g_eff_mps2=G)
    open_fall = _failed_run(f9_vehicle, ca3, deep)
    om = open_fall.metrics
    v3 = math.sqrt(2.0 * 3.0 * G0_MPS2 * L)
    assert -50.0 + v3 * v3 / (2.0 * A_BRAKE) > 0.0  # the carriage parks above the ground
    impact = next(e for e in open_fall.events.itertuples() if e.event == "impact")
    assert abs(float(impact.z_m)) <= 1e-9
    v2 = v3**2 + 2.0 * MU_EARTH_M3S2 * (1.0 / R_EARTH_M - 1.0 / (R_EARTH_M - 50.0))
    assert math.isclose(om["failed_impact_speed_mps"], math.sqrt(v2), rel_tol=REL)
    assert not any(SHAFT_FALLBACK in f for f in open_fall.flags)
    assert all(line in open_fall.assumptions for line in sim.FAILED_IGNITION_TRACK_ASSUMPTIONS)


def test_a_failed_ignition_after_an_early_release_falls_to_the_ground_past_its_carriage(
    f9_vehicle: Vehicle,
) -> None:
    """Fix round 5 (P5-m1, m1, C5-m1): a failed ignition released at its release speed below
    the mouth whose carriage parks at or above the ground keeps Phase 1's obstacle-free fall
    to the ground. 1-D, released at 70 m/s about 16 m down (a = 3 g0, a 5 g0 brake): the
    carriage parks 33.5 m above the ground, z_rel + v^2/(2 a_b); the impact is at z = 0 at
    the time of an independent quadrature and the energy speed (1e-9 relative),
    failed_impact_speed_mps its speed, failed_t_carriage_s and failed_speed_at_carriage_mps
    the quadrature's crossing of the carriage's altitude on the way down, failed_t_return_s
    None (the release altitude lies below the ground, where the fall ends), no shaft flag
    and no failed-ignition flag (the mouth is at the ground), and
    FAILED_IGNITION_EARLY_TRACK_ASSUMPTIONS in place of FAILED_IGNITION_TRACK_ASSUMPTIONS'
    first line (never the shaft lines), saying both None cases; its early-release line names
    no floor (the carriage parks above the ground). With a 0.5 g0 brake at 38.5 m/s the
    carriage parks 76.6 m above the ground, above the apex 1.1 m above it:
    failed_t_carriage_s None, the impact at the ground. Planar (the 28.5 deg site, the
    drag-free F9), the same 70 m/s failed ignition ends at the ground (1e-6 m) with no shaft
    flag, and ``sim.planar_assumption_list`` carries PLANAR_FAILED_IGNITION_EARLY_ASSUMPTIONS
    in place of PLANAR_FAILED_IGNITION_ASSUMPTIONS (never the shaft line)."""
    from launchsim.config import ChecksConfig, SearchConfig
    from launchsim.search import SearchBudget

    m = f9_vehicle.liftoff_mass_kg()
    a = 3.0 * G0_MPS2
    f_max = 2.0 * m * (a + G)
    early = sim.FAILED_IGNITION_EARLY_TRACK_ASSUMPTIONS
    assert "None when it parks above the apex" in early[0]
    assert "failed_t_return_s is None after a release below the ground" in early[0]
    assert "the return to the release altitude" not in early[0]
    for v_release, brake in ((70.0, A_BRAKE), (38.5, 0.5 * G0_MPS2)):
        model = _model(
            "acceleration",
            f_max=f_max,
            p_max=f_max * 1e3,
            a_cmd=a,
            v_release=v_release,
            a_brake=brake,
        )
        result = _failed_run(f9_vehicle, model, SILO)
        met = result.metrics
        assert result.status == "impact"
        release = next(e for e in result.events.itertuples() if e.event == "release")
        z_rel = float(release.z_m)
        assert z_rel < 0.0 and math.isclose(float(release.v_mps), v_release, rel_tol=REL)
        park = z_rel + v_release**2 / (2.0 * brake)
        assert park > 0.0 and math.isclose(met["failed_carriage_alt_m"], park, rel_tol=1e-12)
        impact = next(e for e in result.events.itertuples() if e.event == "impact")
        assert abs(float(impact.z_m)) <= 1e-9
        t_ground, v_ground = _shaft_fall(0.0, z_rel, v_release, 0.0)
        assert math.isclose(met["impact_t_s"], t_ground, rel_tol=REL)
        assert math.isclose(met["failed_impact_speed_mps"], v_ground, rel_tol=REL)
        assert met["failed_t_return_s"] is None
        if park < met["failed_apex_alt_m"]:
            t_car, v_car = _shaft_fall(0.0, z_rel, v_release, park)
            assert math.isclose(met["failed_t_carriage_s"], t_car, rel_tol=REL)
            assert math.isclose(met["failed_speed_at_carriage_mps"], v_car, rel_tol=REL)
        else:  # the soft brake: the carriage parks above the apex
            assert brake < G and 0.0 < met["failed_apex_alt_m"] < park
            assert met["failed_t_carriage_s"] is None
            assert met["failed_speed_at_carriage_mps"] is None
        assert not any(SHAFT_FALLBACK in f for f in result.flags)
        assert not any(f.startswith("failed ignition:") for f in result.flags)
        assert all(line in result.assumptions for line in early)
        assert sim.FAILED_IGNITION_TRACK_ASSUMPTIONS[0] not in result.assumptions
        assert not set(sim.FAILED_IGNITION_SHAFT_ASSUMPTIONS) & set(result.assumptions)
        line = next(x for x in result.assumptions if x.startswith("linear_motor: released"))
        assert "floor of the flight model" not in line
    planner, g_ref = _planar_planner(f9_vehicle, IgnitionSpec(4.0))
    f_planar = 2.0 * m * (a + g_ref)
    fast = LinearMotorAssist(
        control="acceleration",
        force_max_N=f_planar,
        power_max_W=f_planar * 1e3,
        rise_time_s=T_R,
        carriage_mass_kg=0.0,
        brake_decel_mps2=A_BRAKE,
        accel_command_mps2=a,
        efficiency=ETA,
        g_eff_mps2=g_ref,
        release_speed_mps=70.0,
    )
    specs = _specs(f9_vehicle, IgnitionSpec(0.5, fails=True))
    failed = PlanarPlanner(f9_vehicle, specs, planner.guidance, planner.env, "impact", SETTINGS)
    trace = failed.run(None, fast, SILO)
    start = failed.start(fast, SILO)
    assert trace.status == "impact" and start.shaft_floor_m is not None
    assert start.shaft_floor_m > 0.0  # the carriage parks above the ground
    impact = next(e for e in trace.events if e.name == "impact")
    assert abs(impact.value("alt_m")) <= 1e-6
    assert not any(SHAFT_FALLBACK in f for f in trace.flags)
    checks = ChecksConfig()
    setup = sim.PlanarSetup(
        env=planner.env,
        assist=fast,
        track=SILO,
        ignition=specs,
        guidance=planner.guidance,
        budget=SearchBudget.from_config(SearchConfig(), checks),
        target=None,
        settings=SETTINGS,
        checks=checks,
    )
    lines = sim.planar_assumption_list(trace, setup, ())
    assert sim.PLANAR_FAILED_IGNITION_EARLY_ASSUMPTIONS[0] in lines
    assert sim.PLANAR_FAILED_IGNITION_ASSUMPTIONS[0] not in lines
    assert sim.PLANAR_FAILED_IGNITION_SHAFT_ASSUMPTIONS[0] not in lines


def test_a_planar_fall_back_with_drag_matches_a_radial_quadrature(repo_root: Path) -> None:
    """Fix round 5 (P5-m2, C5-m6): the drag of a planar shaft fall-back, on the
    drag-carrying generic_f9_class_2d.yaml (A_ref 10.52 m^2, its C_D(M) table). A failed
    ignition released at 50 m/s about 57 m below the mouth (a = 3 g0, a 5 g0 brake) rises
    above the mouth and falls back through it onto its parked carriage; its impact time
    after the release and |v_rel| there match an independent radial quadrature of r'' =
    -mu/r^2 + omega_p^2 r - sign(w) D/m with D = 0.5 rho w^2 C_D(|w|/a) A_ref (solve_ivp
    DOP853, rtol 1e-12; the ICAO atmosphere and the vehicle's C_D table as the model's
    inputs, the mass the release event's; Coriolis neglected: its horizontal drift of about
    2 omega_p dz, centimetres per second, moves |v_rel| by its square over 2|w|) within
    1e-4 s and 1e-5 m/s (1.5e-6 s and 1e-8 m/s measured), while the drag-free speed lies
    0.029 m/s higher, so drag is exercised (at least 0.01 m/s asserted)."""
    vehicle = VehicleConfig.model_validate(
        yaml.safe_load(
            (repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml").read_text("utf-8")
        )
    ).to_vehicle()
    drag = vehicle.aero
    assert drag is not None
    planner, g_ref = _planar_planner(vehicle, IgnitionSpec(4.0))
    a = 3.0 * G0_MPS2
    f_max = 2.0 * vehicle.liftoff_mass_kg() * (a + g_ref)
    model = LinearMotorAssist(
        control="acceleration",
        force_max_N=f_max,
        power_max_W=f_max * 1e3,
        rise_time_s=T_R,
        carriage_mass_kg=0.0,
        brake_decel_mps2=A_BRAKE,
        accel_command_mps2=a,
        efficiency=ETA,
        g_eff_mps2=g_ref,
        release_speed_mps=50.0,
    )
    specs = _specs(vehicle, IgnitionSpec(0.5, fails=True))
    failed = PlanarPlanner(vehicle, specs, planner.guidance, planner.env, "impact", SETTINGS)
    trace = failed.run(None, model, SILO)
    floor = failed.start(model, SILO).shaft_floor_m
    assert trace.status == "impact" and floor is not None and floor < 0.0
    release = next(e for e in trace.events if e.name == "release")
    impact = next(e for e in trace.events if e.name == "impact")
    assert abs(impact.value("alt_m") - floor) <= 1e-6
    assert max(e.value("alt_m") for e in trace.events if e.name == "apex") > 0.0
    z_rel, w_rel = release.value("alt_m"), release.value("speed_rel_mps")
    mass = release.value("m_kg")
    r_datum, omega = planner.env.r_datum_m, planner.env.omega_p_rads

    def rhs(_t: float, y: np.ndarray) -> list[float]:
        _p, rho, sound = ambient_scalar(float(y[0]) - r_datum)
        d = drag.force_N(0.5 * rho * y[1] * y[1], abs(float(y[1])) / sound) / mass
        return [y[1], -MU_EARTH_M3S2 / y[0] ** 2 + omega**2 * y[0] - math.copysign(d, y[1])]

    def down(_t: float, y: np.ndarray) -> float:
        return float(y[0] - (r_datum + floor)) if y[1] < 0.0 else 1.0

    down.terminal = True  # type: ignore[attr-defined]
    down.direction = -1  # type: ignore[attr-defined]
    sol = solve_ivp(
        rhs,
        (0.0, 60.0),
        [r_datum + z_rel, w_rel],
        method="DOP853",
        rtol=1e-12,
        atol=1e-9,
        events=down,
    )
    t_quad, v_quad = float(sol.t_events[0][0]), abs(float(sol.y_events[0][0][1]))
    assert abs((impact.t_s - release.t_s) - t_quad) <= 1e-4
    assert abs(impact.value("speed_rel_mps") - v_quad) <= 1e-5
    v_free = math.sqrt(w_rel**2 + 2.0 * g_ref * (z_rel - floor))
    assert v_free - impact.value("speed_rel_mps") >= 0.01


# ------------------------------------------------------ metrics, config and the model


def test_metrics_record_the_control_law_command_taper_and_release_speed(
    f9_vehicle: Vehicle,
) -> None:
    """KI-052: a linear-motor run's metrics carry push_control_law, push_accel_command_mps2
    (a_cmd, None for the force law), push_stop_taper_m (None without a taper) and
    push_release_speed_mps (None when no release speed is set) beside the other push
    settings, in LINEAR_MOTOR_METRICS's order at the end of the metrics; and (fix round
    1) push_cap_bound: None for the force law, False for an acceleration law whose caps
    never bind (it held a_cmd), True when F_max cuts the command (F_max below M (a + g):
    a drive_cap event early in the push), and (fix round 2) None for a stalled push
    (F_max below the weight: it never moved)."""
    m = f9_vehicle.liftoff_mass_kg()
    f_max = m * (3.0 * G0_MPS2 + G)
    a = 3.0 * G0_MPS2
    cases = (
        (_model(f_max=f_max, p_max=f_max * 50.0), ("force", None, None, None, None)),
        (
            _model("acceleration", f_max=2 * f_max, p_max=f_max * 1e3, a_cmd=a, taper=10.0),
            ("acceleration", a, 10.0, None, False),
        ),
        (
            _model(f_max=f_max, p_max=f_max * 50.0, v_release=60.0),
            ("force", None, None, 60.0, None),
        ),
        (
            _model("acceleration", f_max=0.9 * f_max, p_max=f_max * 1e3, a_cmd=a),
            ("acceleration", a, None, None, True),
        ),
        (
            _model("acceleration", f_max=0.5 * m * G, p_max=f_max * 1e3, a_cmd=a),
            ("acceleration", a, None, None, None),
        ),
    )
    for model, expected in cases:
        met = _simulate(f9_vehicle, model).metrics
        assert list(met)[-len(LINEAR_MOTOR_METRICS) :] == list(LINEAR_MOTOR_METRICS)
        keys = (
            "push_control_law",
            "push_accel_command_mps2",
            "push_stop_taper_m",
            "push_release_speed_mps",
            "push_cap_bound",
        )
        assert tuple(met[k] for k in keys) == expected
        assert LINEAR_MOTOR_METRICS.index("push_control_law") == 0
    assert RELEASE_TRIGGERS == ("track_end", "target_speed")


def test_release_speed_in_the_config_the_model_and_the_event() -> None:
    """``release_speed_mps`` in a linear_motor block: strict, finite, > 0, optional (left
    out of the dump when unset, dumped when given), carried by ``build_assist`` to the
    model; refused with a stop taper by the config and the model; the model refuses a
    non-finite or non-positive speed; ``ev_release_speed``: the target_speed event, sdot -
    v_release upward, terminal, zero_tol ATOL_MPS, refusing v <= 0."""
    cfg = LinearMotorConfig.model_validate({**LM_BLOCK, "release_speed_mps": 76.70717046013364})
    assert cfg.release_speed_mps == 76.70717046013364
    assert cfg.model_dump()["release_speed_mps"] == 76.70717046013364
    assert LinearMotorConfig.model_validate(cfg.model_dump()) == cfg
    assert "release_speed_mps" not in LinearMotorConfig.model_validate(LM_BLOCK).model_dump()
    model, _track = build_assist(
        LinearMotorConfig.model_validate({**LM_BLOCK, "release_speed_mps": 70}), G
    )
    assert isinstance(model, LinearMotorAssist) and model.release_speed_mps == 70.0
    with pytest.raises(ValidationError, match="refused together with stop_taper_m"):
        LinearMotorConfig.model_validate({**LM_BLOCK, "release_speed_mps": 70, "stop_taper_m": 5})
    for bad in (0.0, -1.0, math.inf, math.nan):
        with pytest.raises(ValueError, match="release_speed_mps must be finite and > 0"):
            _model(f_max=2e7, p_max=1e9, v_release=bad)
    with pytest.raises(ValueError, match="refused with a stop taper"):
        _model(f_max=2e7, p_max=1e9, v_release=70.0, taper=5.0)
    assert _model(f_max=2e7, p_max=1e9, v_release=70.0, taper=0.0).release_speed_mps == 70.0
    assert ConstantAccelAssist(3.0 * G0_MPS2, 0.0, A_BRAKE).release_speed_mps is None
    assert sim.NoAssist().release_speed_mps is None
    from launchsim.dynamics import StateLayout, track_state_names

    layout = StateLayout(track_state_names(_model(f_max=2e7, p_max=1e9)))
    ev = ev_release_speed(70.0, layout)
    assert (ev.name, ev.terminal, ev.direction, ev.zero_tol) == (
        TARGET_SPEED_EVENT,
        True,
        1,
        ATOL_MPS,
    )
    y = layout.build(s_m=10.0, sdot_mps=69.5, m_kg=5e5)
    assert ev.fn(0.0, y) == -0.5
    for bad in (0.0, -3.0, math.nan):
        with pytest.raises(ValueError, match="release speed must be finite and > 0"):
            ev_release_speed(bad, layout)


def test_the_release_and_shaft_lines_of_a_release_speed() -> None:
    """The release line of a push with a release speed replaces the track-end line
    (``release_assumption``; ten lines still, in their order), and the shaft line says
    what the neglected shaft drag does to where the push reaches that speed, by law;
    the force law's taper line names the cap's order (D-SP7-50)."""
    model = _model(f_max=2e7, p_max=1e9, v_release=76.7)
    lines = model.assumptions()
    assert len(lines) == 10 and lines[2] == model.release_assumption()
    assert lines[2] == (
        "linear_motor: release where the speed along the track reaches the release speed "
        "76.7 m/s (assumed), before the track end, or at the track end (s = L) when the push "
        "does not reach it there (flag release_speed_not_reached); no stop taper: the drive "
        "force drops to zero in a step at release, and the carriage brakes from the release "
        "(facility max(L, s_release + braking distance): within the stroke left, or past the "
        "track end when the braking distance exceeds it)"
    )
    assert lines[6].startswith(
        "linear_motor: shaft vented (no air column), no friction; air drag on the vehicle in "
        "the shaft is neglected during the push (after a release before the track end the "
        "flight model flies on in the shaft after it, as the run's early-release line says): "
        "under the force law it would delay the release at the release speed (the release "
        "position and the push time are biased low; the speed at release stays the release "
        "speed while the push still reaches it before the track end, and is biased high when "
        "the push releases at the track end without reaching it)"
    )
    # without a release speed the push is the whole shaft: S4's line, unchanged
    assert (
        _model(f_max=2e7, p_max=1e9)
        .shaft_assumption()
        .startswith(
            "linear_motor: shaft vented (no air column), no friction; air drag on the vehicle in "
            "the shaft is neglected: under the force law it would lower the exit speed"
        )
    )
    accel = _model("acceleration", f_max=2e7, p_max=1e9, a_cmd=30.0, v_release=76.7)
    assert "the release position is unchanged" in accel.shaft_assumption()
    plain = _model(f_max=2e7, p_max=1e9)
    assert plain.release_assumption() == plain.taper_assumption()
    taper = _model(f_max=2e7, p_max=1e9, taper=10.0)
    assert taper.taper_assumption() == (
        "linear_motor: release at the track end (s = L) after a stop taper over the last 10 m: "
        "the force limit is scaled toward the holding force M g_eff sin phi - (1 - f_imp) T by "
        "min(1, (L - s) / s_taper), and the power cap P_max / sdot applies to the scaled force "
        "(D-SP7-50); at L the drive force is the holding force M g_eff sin phi - (1 - f_imp) T "
        "(zero net acceleration) unless the power cap binds there (never on a straight track "
        "a config builds), and it drops to zero in a step at release"
    )
