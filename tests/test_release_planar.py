"""The planar release map (docs/physics.md, "Planar release map"): the pad and a
vertical-silo exit in the rotating planar frame, the exact general map for a tilted
exit downrange of the site (the Phase 3 seam), the Phase 2 vertical assertion, and the
Earth-fixed downrange of a radial rise (the Coriolis drift, amendment 11).

Every expected value is computed here from its own inputs: omega_E R_E and omega_E
cos(lat) R_E for the pad; a Cartesian projection for the general map; a closed-form
integral for the drift.

Also (SP1 step 3): a stage-1 ramp start stated by depth or speed on the 3 g0, 100 m silo
lights at the requested depth or speed on the push (the ignition event against the
closed forms of a push from rest, 1e-9); one stated by a closed-form height lights at
the closed-form time after release, and the height it reaches there differs from the
request by the drag, mu/r^2 and rotation the closed form leaves out (reported, bounded,
not asserted to vanish).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
import yaml

from launchsim.assist import build_assist
from launchsim.atmosphere import ambient_scalar
from launchsim.config import ConstantAccelConfig, IgnitionConfig, VehicleConfig
from launchsim.constants import G0_MPS2, MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M
from launchsim.dynamics import (
    PLANAR_LAYOUT,
    InverseSquareGravity,
    planar_kinematics,
    vacuum_atmosphere,
)
from launchsim.guidance import GuidanceSpec
from launchsim.phases import IgnitionSpec, IntegratorSettings, TrackExit
from launchsim.phases.planar import (
    PlanarEnvironment,
    PlanarPlanner,
    map_release_planar,
    planar_rest_state,
    release_state_planar,
)
from launchsim.phases.prelude import resolve_ignition
from launchsim.vehicle import Engine, Stage, Startup, Vehicle

P2 = PLANAR_LAYOUT
G_TEST = 9.81
"""Constant part of the test gravity [m/s^2] (never g0)."""
HUGE_C_MPS = 1e30
LAT_RAD = math.radians(28.5)
SETTINGS = IntegratorSettings(rtol=1e-10)


@pytest.fixture(scope="module")
def gate_vehicle(repo_root: Path) -> Vehicle:
    """The gate fork generic_f9_class_2d.yaml."""
    path = repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return VehicleConfig.model_validate(raw).to_vehicle()


def _planner(vehicle: Vehicle, omega_p: float, ign1: IgnitionSpec) -> PlanarPlanner:
    env = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), omega_p, ambient_scalar)
    return PlanarPlanner(
        vehicle,
        {"stage1": ign1, "stage2": IgnitionSpec(0.0)},
        GuidanceSpec(50.0, 60.0, 60.0),
        env,
        "stage1_burnout",
        SETTINGS,
    )


@pytest.mark.parametrize(
    ("lat_deg", "expected_mps", "rounded"),
    [(0.0, 465.1011, 465.1), (28.5, 408.7388, 408.7)],
    ids=["equator", "lat28.5"],
)
def test_pad_starts_at_the_ground_speed(
    gate_vehicle: Vehicle, lat_deg: float, expected_mps: float, rounded: float
) -> None:
    """An east pad launch starts at |v_in| = omega_E cos(lat) R_E: 465.1 m/s on the
    equator (CLAUDE.md's release-mapping test), 408.7388 m/s at 28.5 deg; v_r = 0 and
    |v_rel| = 0 exactly, so the release row reports gamma_rel = pi/2 (the fallback to
    local vertical); theta = 0 at the flight start. The pad state is the planner's own
    flight start after the hold-down."""
    omega = OMEGA_EARTH_RADS * math.cos(math.radians(lat_deg))  # sin(az 90 deg) = 1
    start = _planner(gate_vehicle, omega, IgnitionSpec(-2.0)).start()
    y = start.y_fs
    assert y is not None and start.t_fs_s == 0.0
    v_in = math.hypot(float(P2.get(y, "v_r_mps")), float(P2.get(y, "v_theta_mps")))
    assert v_in == pytest.approx(omega * R_EARTH_M, rel=0.0, abs=1e-9)
    assert abs(v_in - expected_mps) < 1e-4
    assert round(v_in, 1) == rounded
    assert float(P2.get(y, "v_r_mps")) == 0.0 and float(P2.get(y, "theta_rad")) == 0.0
    assert planar_kinematics(y, omega).V_mps == 0.0
    assert float(P2.get(y, "r_m")) == R_EARTH_M
    release = start.prefix.first_event("release")
    assert release is not None
    assert release.value("speed_inertial_mps") == pytest.approx(v_in, abs=1e-9)
    assert release.value("speed_rel_mps") == 0.0 and release.value("downrange_m") == 0.0
    assert release.value("gamma_rel_rad") == 0.5 * math.pi


def test_vertical_silo_release(gate_vehicle: Vehicle) -> None:
    """A vertical 100 m silo at a prescribed 3 g net releases at its mouth (the datum)
    with v_r = sdot = sqrt(2 a L) (a = 3 g0), v_theta = omega_p R_E, theta = 0, at
    t = sqrt(2 L / a); the flight starts there; the push rows are Earth-fixed
    (downrange 0) and the release row is the flight's first."""
    omega = OMEGA_EARTH_RADS * math.cos(LAT_RAD)
    planner = _planner(gate_vehicle, omega, IgnitionSpec(0.5))
    cfg = ConstantAccelConfig(
        model="constant_accel",
        net_accel_g=3.0,
        stroke_m=100.0,
        brake_decel_g=5.0,
        drive_efficiency=0.5,
    )
    assist, track = build_assist(cfg, planner.env.g_ref_mps2)
    start = planner.start(assist, track)
    a, length = 3.0 * G0_MPS2, 100.0
    y = start.y_fs
    assert y is not None and start.status == "nominal"
    assert start.t_fs_s == pytest.approx(math.sqrt(2.0 * length / a), rel=1e-9)
    assert float(P2.get(y, "v_r_mps")) == pytest.approx(math.sqrt(2.0 * a * length), rel=1e-9)
    assert float(P2.get(y, "v_theta_mps")) == omega * R_EARTH_M
    assert float(P2.get(y, "r_m")) == R_EARTH_M and float(P2.get(y, "theta_rad")) == 0.0
    push = start.prefix.first_event("push_start")
    assert push is not None and push.value("downrange_m") == 0.0
    assert push.value("alt_m") == pytest.approx(-length, abs=1e-9)


def test_silo_flight_rows_use_the_release_datum(gate_vehicle: Vehicle) -> None:
    """After a track start the Earth-fixed downrange of a flight row is measured from
    the release (t_fs = t_release, theta = 0 at the silo mouth), not from push start.
    The cold silo start coasts 0.5 s from its release at v0 = 76.7 m/s before ignition;
    its ignition row shows the classical Coriolis drift of a vertical throw,
    x = -omega_p (v0 t^2 - g t^3/3) with g = mu/R_E^2 - omega_p^2 R_E (about -1.2 mm,
    west), within 1e-3 relative (drag and the spherical terms: measured 1.2e-4). A view
    bound to push start instead would shift the row by -R_E omega_p t_release (about
    -1,066 m); an ignition deadline measured from the flight start is covered in
    test_planar_events."""
    omega = OMEGA_EARTH_RADS * math.cos(LAT_RAD)
    planner = _planner(gate_vehicle, omega, IgnitionSpec(0.5))
    cfg = ConstantAccelConfig(
        model="constant_accel",
        net_accel_g=3.0,
        stroke_m=100.0,
        brake_decel_g=5.0,
        drive_efficiency=0.5,
    )
    assist, track = build_assist(cfg, planner.env.g_ref_mps2)
    trace = planner.run(math.radians(3.0), assist, track)
    assert trace.t_flight_start_s == trace.t_release_s and trace.y_flight_start is not None
    ignition = trace.first_event("ignition")
    assert ignition is not None
    t = ignition.t_s - trace.t_release_s
    assert t == pytest.approx(0.5, abs=1e-12)
    v0 = float(P2.get(trace.y_flight_start, "v_r_mps"))
    g = MU_EARTH_M3S2 / R_EARTH_M**2 - omega**2 * R_EARTH_M
    drift = -omega * (v0 * t * t - g * t**3 / 3.0)
    assert ignition.value("downrange_m") == pytest.approx(drift, rel=1e-3)
    assert -2e-3 < drift < -1e-3


def _cartesian_release(
    z_e: float, x_e: float, sdot: float, phi: float, omega: float, r_datum: float
) -> dict[str, float]:
    """The release state by projecting the flat-frame vectors (the test's own
    construction): position P = (x_e, r_datum + z_e), Earth-relative velocity
    V = sdot (cos phi, sin phi), r_hat = P/|P|, theta_hat = (P_z, -P_x)/|P|."""
    px, pz = x_e, r_datum + z_e
    r = math.hypot(px, pz)
    rhat = (px / r, pz / r)
    that = (pz / r, -px / r)
    vx, vz = sdot * math.cos(phi), sdot * math.sin(phi)
    return {
        "r": r,
        "theta": math.atan2(px, pz),
        "v_r": vx * rhat[0] + vz * rhat[1],
        "u": vx * that[0] + vz * that[1],
    }


@pytest.mark.parametrize(
    ("z_e", "x_e", "phi_deg"),
    [(3.0e3, 5.0e4, 30.0), (0.0, 1.2e4, 10.0), (500.0, 0.0, 60.0), (-80.0, 2.0e3, 89.0)],
)
def test_general_release_map(z_e: float, x_e: float, phi_deg: float) -> None:
    """The exact general map for an exit x_e downrange of the site at altitude z_e with
    the track angle phi < pi/2: r, theta, v_r and v_theta - omega_p r equal the
    Cartesian projection within 1e-12 relative; |v_rel| = sdot, the Earth-relative
    flight-path angle is phi + theta_x (the local horizontal at the exit is tilted by
    theta_x), and |v_in| is the vector sum with the ground speed omega_p r."""
    omega = OMEGA_EARTH_RADS * math.cos(LAT_RAD)
    sdot, m = 300.0, 1.0e5
    phi = math.radians(phi_deg)
    y = release_state_planar(z_e, x_e, sdot, phi, m, omega)
    cart = _cartesian_release(z_e, x_e, sdot, phi, omega, R_EARTH_M)
    r = float(P2.get(y, "r_m"))
    assert r == pytest.approx(cart["r"], rel=1e-15)
    assert float(P2.get(y, "theta_rad")) == pytest.approx(cart["theta"], rel=1e-12, abs=1e-18)
    assert float(P2.get(y, "v_r_mps")) == pytest.approx(cart["v_r"], rel=1e-12, abs=1e-12)
    u = float(P2.get(y, "v_theta_mps")) - omega * r
    assert u == pytest.approx(cart["u"], rel=1e-12, abs=1e-12)
    kin = planar_kinematics(y, omega)
    assert kin.V_mps == pytest.approx(sdot, rel=1e-12)
    theta_x = math.atan2(x_e, R_EARTH_M + z_e)
    assert math.atan2(kin.w_mps, kin.u_mps) == pytest.approx(phi + theta_x, abs=1e-12)
    assert float(P2.get(y, "m_kg")) == m
    assert all(float(P2.get(y, n)) == 0.0 for n in P2.names if n.startswith("J_"))


@pytest.mark.parametrize("z_e", [0.0, 500.0], ids=["mouth_at_datum", "elevated_exit"])
def test_vertical_map_is_the_general_map_at_x0(z_e: float) -> None:
    """At x_e = 0, phi = pi/2 the general map gives v_r = sdot and v_theta = omega_p r
    (to the 6e-17 of cos(pi/2) in floating point), which map_release_planar writes
    exactly, with r = R_E + z_e: an exit 500 m above the datum (config
    track.exit_altitude_m) carries the ground speed at its own radius, omega_p (R_E +
    z_e), not omega_p R_E; planar_rest_state is the sdot = 0 case."""
    omega = OMEGA_EARTH_RADS * math.cos(LAT_RAD)
    exit_ = TrackExit(2.6, np.zeros(3), 76.7, 5.6e5, 0.5 * math.pi, 0.0, z_e)
    exact = map_release_planar(exit_, omega)
    general = release_state_planar(z_e, 0.0, 76.7, 0.5 * math.pi, 5.6e5, omega)
    np.testing.assert_allclose(general, exact, rtol=0.0, atol=1e-13)
    r = R_EARTH_M + z_e
    assert float(P2.get(exact, "r_m")) == r and float(P2.get(exact, "theta_rad")) == 0.0
    assert float(P2.get(exact, "v_r_mps")) == 76.7
    assert float(P2.get(exact, "v_theta_mps")) == omega * r
    rest = planar_rest_state(z_e, 5.6e5, omega)
    np.testing.assert_array_equal(rest, release_state_planar(z_e, 0.0, 0.0, 0.0, 5.6e5, omega))


@pytest.mark.parametrize(
    ("x_exit", "phi", "match"),
    [
        (None, 0.5 * math.pi, "no x"),
        (1.0, 0.5 * math.pi, "vertical tracks only"),
        (0.0, 1.0, "vertical tracks only"),
    ],
)
def test_map_release_refuses_non_vertical_exits(
    x_exit: float | None, phi: float, match: str
) -> None:
    """The Phase 2 assertion: map_release_planar refuses an exit whose downrange offset
    is unknown (a geometry without x(s)), non-zero, or not vertical."""
    exit_ = TrackExit(2.6, np.zeros(3), 76.7, 5.6e5, phi, x_exit, 0.0)
    with pytest.raises(ValueError, match=match):
        map_release_planar(exit_, 6.4e-5)


@dataclass(frozen=True)
class _CentrifugalPlusConstant:
    """g(r) = h0^2/r^3 + g_c [m/s^2]: cancels the centrifugal term of a radial flight
    with angular momentum h0 exactly, so the radial acceleration is T/m - g_c."""

    h0_m2s: float
    g_c_mps2: float

    def __call__(self, r_m: float) -> float:
        return self.h0_m2s * self.h0_m2s / (r_m * r_m * r_m) + self.g_c_mps2


def test_radial_rise_earth_fixed_downrange() -> None:
    """Amendment 11: the Earth-fixed downrange of a radial rise (the Coriolis drift).

    Rotation on (the equatorial rate), thrust inertially radial (the planner's
    VERTICAL_RISE), no air: no tangential force, so r v_theta = h0 = omega R^2 is
    conserved (1e-10 relative: the integration error of v_theta). The test gravity
    h0^2/r^3 + g_c leaves the radial acceleration the constant a = A - g_c (A = 20
    m/s^2 thrust acceleration, mass constant with c = 1e30), so r = R + a t^2/2 and
    theta = h0 int dt/r^2 in closed form:
    int_0^t dt/(R + b s^2)^2 = t/(2R(R + b t^2)) + atan(t sqrt(b/R))/(2 R sqrt(R b)),
    b = a/2. The planner's kick-trigger event (v_k = 1500 m/s, about 147 s and 110 km
    up) reports downrange = R (theta - omega t) equal to it within 1e-7 relative (-778
    m: the vehicle falls behind the rotating ground; measured 1.2e-8), the altitude
    a t^2/2 within 1e-9 relative (measured 1.4e-11), and the leading Coriolis term
    -omega a t^3/3 times (1 - 0.9 h/R) within (h/R)^2."""
    omega = OMEGA_EARTH_RADS
    h0 = omega * R_EARTH_M * R_EARTH_M
    a_thrust = 20.0
    m0 = 1020.0
    engine1 = Engine(thrust_vac_N=a_thrust * m0, isp_vac_s=HUGE_C_MPS / G0_MPS2)
    engine2 = Engine(thrust_vac_N=1.0, isp_vac_s=HUGE_C_MPS / G0_MPS2)
    stages = (
        Stage("stage1", 500.0, 500.0, engine1, startup=Startup("step")),
        Stage("stage2", 10.0, 10.0, engine2, startup=Startup("step")),
    )
    vehicle = Vehicle(stages=stages)
    assert vehicle.liftoff_mass_kg() == m0
    env = PlanarEnvironment(_CentrifugalPlusConstant(h0, G_TEST), omega, vacuum_atmosphere)
    planner = PlanarPlanner(
        vehicle,
        {"stage1": IgnitionSpec(0.0, startup=Startup("step")), "stage2": IgnitionSpec(0.0)},
        GuidanceSpec(1500.0, 60.0, 1.0e4),
        env,
        "stage1_burnout",
        SETTINGS,
    )
    kick = planner.to_kick(planner.start())
    ev = kick.prefix.first_event("kick_start")
    assert ev is not None and kick.kicked
    t = ev.t_s
    a = a_thrust - G_TEST
    b = 0.5 * a
    big_r = R_EARTH_M
    integral = t / (2 * big_r * (big_r + b * t * t)) + math.atan(t * math.sqrt(b / big_r)) / (
        2 * big_r * math.sqrt(big_r * b)
    )
    downrange = big_r * (h0 * integral - omega * t)
    assert ev.value("downrange_m") == pytest.approx(downrange, rel=1e-7)
    alt = b * t * t
    assert ev.value("alt_m") == pytest.approx(alt, rel=1e-9)
    y = kick.y
    assert float(P2.get(y, "r_m")) * float(P2.get(y, "v_theta_mps")) == pytest.approx(h0, rel=1e-10)
    eps = alt / big_r
    ratio = downrange / (-omega * a * t**3 / 3.0)
    assert abs(ratio - (1.0 - 0.9 * eps)) < eps * eps
    assert downrange < -700.0


# ------------------------------------- ramp start by depth, speed and height (SP1 step 3)

SILO_A_MPS2 = 3.0 * G0_MPS2
"""Net acceleration of the 3 g0 silo [m/s^2]."""
SILO_L_M = 100.0
"""Its stroke [m]; the mouth (track exit) is at the datum, z = 0."""
EVENT_ABS = 1e-9
"""Tolerance of a planar ignition event's altitude [m], |v_rel| [m/s] and time [s]
against its closed form (SP1 step 3 gate)."""
HEIGHT_MISS_BOUND_M = 0.5
"""A loose bound [m] on the achieved minus requested closed-form height up to 200 m: the
flown coast has drag, mu/r^2 and rotation, the closed form none (measured: about -4 mm
at 40 m and -0.1 m at 200 m; docs/physics.md, "Silo model")."""


def _silo_start(gate_vehicle: Vehicle, block: dict) -> tuple[PlanarPlanner, object, object]:
    """The planner of the gate fork at 28.5 deg with stage 1's IgnitionSpec resolved from
    ``block`` on the 3 g0, 100 m silo (``resolve_ignition`` with the site's g_ref, as both
    spec build sites do), and the silo's assist and track."""
    omega = OMEGA_EARTH_RADS * math.cos(LAT_RAD)
    env = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), omega, ambient_scalar)
    cfg = ConstantAccelConfig(
        model="constant_accel",
        net_accel_g=3.0,
        stroke_m=SILO_L_M,
        brake_decel_g=5.0,
        drive_efficiency=0.5,
    )
    assist, track = build_assist(cfg, env.g_ref_mps2)
    stage1 = gate_vehicle.stages[0]
    spec = resolve_ignition(
        IgnitionConfig.model_validate(block), stage1.startup, assist, track, env.g_ref_mps2
    )
    return _planner(gate_vehicle, omega, spec), assist, track


@pytest.mark.parametrize("depth", [SILO_L_M, 75.0, 50.0, 25.0, 1.0])
def test_planar_ignition_event_lies_at_the_requested_depth(
    gate_vehicle: Vehicle, depth: float
) -> None:
    """On the planar model the stage-1 ignition event of a ramp start by depth d lies on
    the push at alt = z_mouth - d = -d, |v_rel| = sqrt(2 a (L - d)) and t = sqrt(2 (L -
    d) / a) after push start, all at 1e-9 (closed forms written here; the altitude
    passes through r = R_E + z, so it carries ulp(R_E) = 9.3e-10 m of rounding)."""
    planner, assist, track = _silo_start(gate_vehicle, {"at_depth_m": depth})
    start = planner.start(assist, track)
    ev = start.prefix.first_event("ignition")
    assert ev is not None and ev.phase == "ASSIST" and ev.stage == "stage1"
    a, length = SILO_A_MPS2, SILO_L_M
    assert abs(ev.value("alt_m") - (0.0 - depth)) < EVENT_ABS
    assert abs(ev.value("speed_rel_mps") - math.sqrt(2.0 * a * (length - depth))) < EVENT_ABS
    assert abs(ev.t_s - math.sqrt(2.0 * (length - depth) / a)) < EVENT_ABS


@pytest.mark.parametrize("speed", [0.0, 17.9, 54.24, 76.0])
def test_planar_ignition_event_lies_at_the_requested_speed(
    gate_vehicle: Vehicle, speed: float
) -> None:
    """On the planar model the ignition event of a ramp start by speed v lies on the push
    at |v_rel| = v, alt = -L + v^2 / (2 a) and t = v / a after push start, at 1e-9."""
    planner, assist, track = _silo_start(gate_vehicle, {"at_speed_mps": speed})
    start = planner.start(assist, track)
    ev = start.prefix.first_event("ignition")
    assert ev is not None and ev.phase == "ASSIST"
    a, length = SILO_A_MPS2, SILO_L_M
    assert abs(ev.value("speed_rel_mps") - speed) < EVENT_ABS
    assert abs(ev.value("alt_m") - (-length + speed * speed / (2.0 * a))) < EVENT_ABS
    assert abs(ev.t_s - speed / a) < EVENT_ABS


@pytest.mark.parametrize("height", [5.0, 40.0, 200.0])
def test_planar_closed_form_height_is_reached_at_the_closed_form_time(
    gate_vehicle: Vehicle, height: float
) -> None:
    """The closed-form height on the planar model: stage 1 lights exactly at the
    closed-form time after release, dt = (v_e - sqrt(v_e^2 - 2 g h)) / g with v_e =
    sqrt(2 a L) and the site's g = mu/R_E^2 - omega_p^2 R_E (1e-9 s), above the mouth.
    The height it reaches there is not h: the flown coast has drag, mu/r^2 and rotation
    and the closed form none, so achieved minus requested is reported, not asserted to
    vanish: it is non-zero (above 1e-6 m) and within HEIGHT_MISS_BOUND_M."""
    planner, assist, track = _silo_start(
        gate_vehicle, {"at_height_m": height, "height_method": "closed_form"}
    )
    trace = planner.run(math.radians(3.0), assist, track)
    ev = trace.first_event("ignition")
    assert ev is not None and ev.phase not in ("HOLD", "ASSIST")
    omega = OMEGA_EARTH_RADS * math.cos(LAT_RAD)
    g = MU_EARTH_M3S2 / R_EARTH_M**2 - omega**2 * R_EARTH_M
    v_e = math.sqrt(2.0 * SILO_A_MPS2 * SILO_L_M)
    dt = (v_e - math.sqrt(v_e * v_e - 2.0 * g * height)) / g
    assert abs((ev.t_s - trace.t_release_s) - dt) < EVENT_ABS
    miss = ev.value("alt_m") - height
    assert 1e-6 < abs(miss) < HEIGHT_MISS_BOUND_M
