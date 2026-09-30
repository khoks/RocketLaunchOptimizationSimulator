"""Stage-1 events and phases of the planar planner (docs/physics.md, "Stage-1 guidance
and events (planar)"): the pad liftoff with back-pressure and rotation, the kick trigger
and alignment, the kick at the first lit instant, a falling vehicle that never kicks,
the typed kick timeout and deadline, the staging map and coast, the loss identity to
MECO and stage-2 ignition, failed ignitions, the event-list discipline, and the
search mode (dense output off).

The runs fly the gate fork (generic_f9_class_2d.yaml) at 28.5 deg east with rotation,
the ICAO atmosphere and the Braeunig drag, at rtol 1e-10.
"""

from __future__ import annotations

import ast
import dataclasses
import itertools
import math
from pathlib import Path

import numpy as np
import pytest
import yaml
from ambiance import Atmosphere

from launchsim.assist import build_assist
from launchsim.assist.base import AssistModel, TrackGeometry
from launchsim.atmosphere import ambient_scalar
from launchsim.config import ConstantAccelConfig, VehicleConfig
from launchsim.constants import MU_EARTH_M3S2, OMEGA_EARTH_RADS, P_SEA_LEVEL_PA, R_EARTH_M
from launchsim.dynamics import PLANAR_LAYOUT, InverseSquareGravity, planar_kinematics
from launchsim.guidance import AlongVrel, FixedTilt, GuidanceFailure, GuidanceSpec
from launchsim.phases import IgnitionSpec, IntegratorSettings, RunTrace
from launchsim.phases.planar import (
    COAST,
    COAST_PRE_IGN,
    COAST_STAGING,
    GRAVITY_TURN,
    KICK,
    VERTICAL_RISE,
    PlanarEnvironment,
    PlanarPlanner,
    fmh_rate_W_m2,
)
from launchsim.vehicle import FairingDrop, Startup, Vehicle

P2 = PLANAR_LAYOUT
LAT_RAD = math.radians(28.5)
OMEGA_P = OMEGA_EARTH_RADS * math.cos(LAT_RAD)  # azimuth 90 deg
V_KICK_MPS = 50.0
DELTA_RAD = math.radians(3.0)
SETTINGS = IntegratorSettings(rtol=1e-10)
LOSS_NAMES = ("J_grav_mps", "J_drag_mps", "J_steer_mps", "J_bp_mps")
IDENTITY_TOL_MPS = 1e-5
"""checks.identity_tol_mps of the shipped experiments (measured residuals ~1e-9 m/s)."""


@pytest.fixture(scope="module")
def gate_vehicle(repo_root: Path) -> Vehicle:
    """The gate fork generic_f9_class_2d.yaml."""
    path = repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return VehicleConfig.model_validate(raw).to_vehicle()


PAD_IGNITION = IgnitionSpec(-2.0)
"""The shipped pad: stage 1 lit 2 s before release (its 2 s ramp done at release)."""
STAGE2_IGNITION = IgnitionSpec(0.0)
GUIDANCE = GuidanceSpec(V_KICK_MPS, 60.0, 60.0)
"""The shipped kick: v_k 50 m/s, 60 s limit, 60 s deadline."""
ENV = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), OMEGA_P, ambient_scalar)


def _planner(
    vehicle: Vehicle,
    ign1: IgnitionSpec = PAD_IGNITION,
    *,
    ign2: IgnitionSpec = STAGE2_IGNITION,
    guidance: GuidanceSpec = GUIDANCE,
    end: str = "stage1_burnout",
    settings: IntegratorSettings = SETTINGS,
) -> PlanarPlanner:
    return PlanarPlanner(vehicle, {"stage1": ign1, "stage2": ign2}, guidance, ENV, end, settings)


def _silo() -> tuple[AssistModel, TrackGeometry]:
    cfg = ConstantAccelConfig(
        model="constant_accel",
        net_accel_g=3.0,
        stroke_m=100.0,
        brake_decel_g=5.0,
        drive_efficiency=0.5,
    )
    return build_assist(cfg, ENV.g_ref_mps2)


def _names(trace: RunTrace) -> list[str]:
    return [e.name for e in trace.events]


def _speed_rel(y: np.ndarray) -> float:
    return planar_kinematics(y, OMEGA_P).V_mps


def _closure_mps(y: np.ndarray, v0: float) -> float:
    """V - V0 - (J_vac - J_grav - J_drag - J_steer - J_bp) of a planar state [m/s]."""
    losses = sum(float(P2.get(y, n)) for n in LOSS_NAMES)
    return _speed_rel(y) - v0 - (float(P2.get(y, "J_vac_mps")) - losses)


# ---------------------------------------------------------------------------- liftoff


def test_liftoff_with_back_pressure_and_rotation(gate_vehicle: Vehicle) -> None:
    """Stage 1 lit at release (t = 0) with its 2 s ramp: the hold-down extends to the
    root of the delivered-thrust balance T_vac t/t_r - p0 A_e = (m0 - mdot t^2/(2 t_r))
    g_ref, with p0 = 101,325 Pa, A_e = 9 x 0.680 m^2 from the config and g_ref =
    mu/R_E^2 - omega_p^2 R_E (rotation), solved here as a quadratic. The liftoff event
    and the flight start land on it within 1e-9 s with the closed-form mass; the pad
    state stays Earth-fixed (theta = 0, v_theta = omega_p R_E); the release row is
    labelled RELEASE (nothing lit before t = 0); without back-pressure the root would
    come earlier."""
    stage = gate_vehicle.stages[0]
    t_r = stage.startup.t_ramp_s
    m0 = gate_vehicle.liftoff_mass_kg()
    mdot = stage.mdot_full_kgps
    t_full = stage.thrust_vac_total_N
    a_e = stage.exit_area_total_m2
    assert a_e == pytest.approx(9 * (914.1e3 - 845.2e3) / P_SEA_LEVEL_PA, rel=1e-12)
    g_ref = MU_EARTH_M3S2 / R_EARTH_M**2 - OMEGA_P**2 * R_EARTH_M

    def root(p0: float) -> float:
        c2, c1, c0 = mdot * g_ref / (2 * t_r), t_full / t_r, p0 * a_e + m0 * g_ref
        return 2 * c0 / (c1 + math.sqrt(c1 * c1 + 4 * c2 * c0))

    t_star = root(P_SEA_LEVEL_PA)
    start = _planner(gate_vehicle, IgnitionSpec(0.0)).start()
    liftoff = start.prefix.first_event("liftoff")
    assert liftoff is not None
    assert liftoff.t_s == pytest.approx(t_star, abs=1e-9)
    assert start.t_fs_s == liftoff.t_s
    y = start.y_fs
    assert y is not None
    assert float(P2.get(y, "m_kg")) == pytest.approx(m0 - mdot * t_star**2 / (2 * t_r), rel=1e-12)
    assert float(P2.get(y, "theta_rad")) == 0.0 and float(P2.get(y, "v_r_mps")) == 0.0
    assert float(P2.get(y, "v_theta_mps")) == OMEGA_P * R_EARTH_M
    assert start.prefix.hold is not None
    assert start.prefix.hold.extension_s == pytest.approx(t_star, abs=1e-9)
    release = start.prefix.first_event("release")
    assert release is not None and release.phase == "RELEASE"
    assert root(0.0) < t_star - 0.1
    # The rise from the liftoff root (v_r = 0 and dv_r/dt = 0) is split at the apex and
    # does not list the ground event, so nothing is disarmed and no flag is raised.
    kick = _planner(gate_vehicle, IgnitionSpec(0.0)).to_kick(start)
    rise = next(p for p in kick.prefix.phases if p.spec.kind == VERTICAL_RISE)
    assert rise.spec.t0 == start.t_fs_s and "impact" not in {e.name for e in rise.spec.events}
    assert kick.prefix.flags == () and kick.kicked


# ------------------------------------------------------------------------------ kicks


def test_kick_trigger_and_alignment(gate_vehicle: Vehicle) -> None:
    """On the pad the kick starts where |v_rel| = v_k while rising (within 1e-9 m/s;
    w > 0, leaning 0.03 deg west by the Coriolis drift of the radial rise) and ends
    where the Earth-relative flight-path angle equals the thrust pitch pi/2 - delta
    (within 1e-9 rad); the gravity turn then starts with the same thrust direction
    (continuity at the switch), and MECO follows in the turn."""
    trace = _planner(gate_vehicle).run(DELTA_RAD)
    names = _names(trace)
    assert names == ["ignition", "release", "kick_start", "kick_end", "propellant", "end"]
    kick = trace.first_event("kick_start")
    assert kick is not None and kick.phase == VERTICAL_RISE
    assert abs(kick.value("speed_rel_mps") - V_KICK_MPS) < 1e-9
    # Rising (w > 0), leaning slightly west of vertical: the ground drifts east under a
    # radial rise (u = omega_p (R_E^2/r - r) < 0 without drag), so gamma_rel > pi/2.
    assert 0.5 * math.pi < kick.value("gamma_rel_rad") < 0.5 * math.pi + 1e-3
    end = trace.first_event("kick_end")
    assert end is not None and end.phase == KICK
    assert abs(end.value("gamma_rel_rad") - (0.5 * math.pi - DELTA_RAD)) < 1e-9
    kinds = [p.spec.kind for p in trace.phases]
    assert kinds == ["HOLD", VERTICAL_RISE, KICK, GRAVITY_TURN]
    turn = trace.phases[-1]
    y0 = turn.y[:, 0]
    kin = planar_kinematics(y0, OMEGA_P)
    e_turn = AlongVrel().direction(turn.spec.t0, y0, kin)
    e_kick = FixedTilt(DELTA_RAD).direction(turn.spec.t0, y0, kin)
    assert e_turn == pytest.approx(e_kick, abs=1e-9)
    assert trace.phases[2].spec.t0 == kick.t_s and turn.spec.t0 == end.t_s


@pytest.mark.parametrize(
    ("case", "ign1"),
    [
        ("cold", IgnitionSpec(0.5)),
        ("hot_ramp", IgnitionSpec(-2.0)),
    ],
)
def test_kick_at_the_first_lit_instant_when_already_past(
    gate_vehicle: Vehicle, case: str, ign1: IgnitionSpec
) -> None:
    """A silo release at 76.7 m/s is past the trigger: a cold start (lit 0.5 s after
    release, still at about 72 m/s) kicks at its ignition, a hot start (lit on the
    carriage) at release, the first free-flight instant. The planner decides this at
    the first lit instant itself: kick_start is logged there (phase KICK, like the cold
    start's ignition), KICK starts there, there is no VERTICAL_RISE phase, and the
    nominal case raises no run flag."""
    assist, track = _silo()
    trace = _planner(gate_vehicle, ign1).run(DELTA_RAD, assist, track)
    kick = trace.first_event("kick_start")
    assert kick is not None and kick.phase == KICK
    t_first = trace.t_release_s + (0.5 if case == "cold" else 0.0)
    assert kick.t_s == pytest.approx(t_first, abs=1e-12)
    assert kick.value("speed_rel_mps") > V_KICK_MPS
    assert all(p.spec.kind != VERTICAL_RISE for p in trace.phases)
    assert next(p for p in trace.phases if p.spec.kind == KICK).spec.t0 == kick.t_s
    assert trace.flags == ()
    if case == "cold":
        ignition = trace.first_event("ignition")
        assert ignition is not None and ignition.t_s == kick.t_s and ignition.phase == KICK
        assert [p.spec.kind for p in trace.phases][:3] == ["ASSIST", COAST_PRE_IGN, KICK]


def test_falling_vehicle_never_kicks(gate_vehicle: Vehicle) -> None:
    """A silo release at 76.7 m/s lit 9 s later (step start) is falling at ignition,
    faster than v_k = 5 m/s: g = min(V - v_k, w) = w < 0, so no kick at ignition. The
    rise brakes the fall (split at the radial turnaround) and the kick starts only once
    the vehicle rises at v_k (w > 0), within 1e-9 m/s. (Flown to the kick trigger
    only: a 3 deg kick at 5 m/s and 270 m would dive into the ground.)"""
    assist, track = _silo()
    planner = _planner(
        gate_vehicle,
        IgnitionSpec(9.0, startup=Startup("step")),
        guidance=GuidanceSpec(5.0, 60.0, 60.0),
    )
    trace = planner.to_kick(planner.start(assist, track)).prefix
    names = _names(trace)
    assert names.index("apex") < names.index("ignition") < names.index("turnaround")
    assert names.index("turnaround") < names.index("kick_start")
    ignition = trace.first_event("ignition")
    assert ignition is not None
    assert ignition.value("speed_rel_mps") > 5.0 and ignition.value("gamma_rel_rad") < 0.0
    kick = trace.first_event("kick_start")
    assert kick is not None and 0.0 < kick.value("gamma_rel_rad")
    assert abs(kick.value("speed_rel_mps") - 5.0) < 1e-9
    turnaround = trace.first_event("turnaround")
    assert turnaround is not None and kick.t_s > turnaround.t_s
    assert names[-1] == "kick_start" and trace.status == "nominal"


def test_kick_timeout_and_deadline_are_typed(gate_vehicle: Vehicle) -> None:
    """A kick held longer than kick_max_s (1 s here; the 3 deg kick needs 5.3 s) raises
    GuidanceFailure("kick_timeout"); no trigger within the deadline (5 s after ignition;
    50 m/s takes 14.3 s) or no trigger before burnout (v_k = 1e5 m/s) raises
    GuidanceFailure("no_kick"), from ``run`` and from ``to_kick`` alike."""
    cases = [
        (GuidanceSpec(V_KICK_MPS, 1.0, 60.0), "kick_timeout"),
        (GuidanceSpec(V_KICK_MPS, 60.0, 5.0), "no_kick"),
        (GuidanceSpec(1.0e5, 60.0, 1.0e4), "no_kick"),
    ]
    for guidance, kind in cases:
        planner = _planner(gate_vehicle, guidance=guidance)
        with pytest.raises(GuidanceFailure) as info:
            planner.run(DELTA_RAD)
        assert info.value.kind == kind, guidance
        if kind == "no_kick":
            with pytest.raises(GuidanceFailure) as info:
                planner.to_kick(planner.start())
            assert info.value.kind == "no_kick"


def test_kick_deadline_counts_from_ignition(gate_vehicle: Vehicle) -> None:
    """The kick deadline is measured from stage-1 ignition (amendment 13), not from the
    flight start: the pad lit at -2 s reaches the trigger at t_k (about 12.3 s after
    release, 14.3 s after ignition). A deadline 0.75 s shorter than t_k - t_ign raises
    no_kick, although measured from the flight start (t = 0) it would lie 1.25 s after
    the trigger; a deadline 0.25 s longer lets the kick start."""
    planner = _planner(gate_vehicle)
    start = planner.start()
    t_k = planner.to_kick(start).t_s
    t_ign = start.t_ign1_s
    assert t_ign == -2.0 and start.t_fs_s == 0.0
    late = _planner(gate_vehicle, guidance=GuidanceSpec(V_KICK_MPS, 60.0, t_k - t_ign + 0.25))
    assert late.to_kick(late.start()).t_s == t_k
    early = _planner(gate_vehicle, guidance=GuidanceSpec(V_KICK_MPS, 60.0, t_k - t_ign - 0.75))
    with pytest.raises(GuidanceFailure) as info:
        early.to_kick(early.start())
    assert info.value.kind == "no_kick"


def test_a_dive_ends_at_the_ground(gate_vehicle: Vehicle) -> None:
    """A 10 deg kick at 50 m/s dives into the ground before MECO: the recorded run ends
    with status impact at the ground event (altitude 0), and the search's stage-1
    flight raises GuidanceFailure("impact") (the inner solve's -pi/2 sentinel)."""
    planner = _planner(gate_vehicle)
    trace = planner.run(math.radians(10.0))
    assert trace.status == "impact"
    impact = trace.events[-1]
    assert impact.name == "impact" and abs(impact.value("alt_m")) < 1e-3
    assert "propellant" not in _names(trace)
    with pytest.raises(GuidanceFailure) as info:
        planner.stage1(math.radians(10.0), planner.start())
    assert info.value.kind == "impact"


# --------------------------------------------------------------- staging and closure


@pytest.mark.parametrize(
    ("rule", "drop_fairing"),
    [
        (None, False),  # the fork's heating rule, not yet met at MECO (~69 km)
        ("staging", True),
        ("never", False),
        (FairingDrop("free_molecular_heating", 1.0e12), True),  # already met at staging
    ],
    ids=["heating_not_met", "staging", "never", "heating_met"],
)
def test_staging_map_and_coast(
    gate_vehicle: Vehicle, rule: str | FairingDrop | None, drop_fairing: bool
) -> None:
    """At MECO the staging map removes exactly stage 1's dry mass, plus the fairing
    under rule staging or when the heating criterion 0.5 rho V^3 < limit already holds
    (logged as ``fairing`` with a flag); r, theta, v_r, v_theta and every quadrature
    are unchanged. The 11 s staging coast (stage 2's coast_before_ignition_s) ends at
    stage-2 ignition, which the handover carries."""
    vehicle = gate_vehicle if rule is None else dataclasses.replace(gate_vehicle, fairing_drop=rule)
    planner = _planner(vehicle, settings=IntegratorSettings(rtol=1e-10, dense_output=False))
    ho = planner.stage1(DELTA_RAD, planner.start())
    trace = ho.prefix
    t_meco, y_meco = trace.burnouts["stage1"]
    coast = next(p for p in trace.phases if p.spec.kind == COAST_STAGING)
    y_mapped = coast.y[:, 0]
    dropped = vehicle.stages[0].dry_mass_kg + (vehicle.fairing_mass_kg if drop_fairing else 0.0)
    i_m = P2.index("m_kg")
    assert y_meco[i_m] - y_mapped[i_m] == pytest.approx(dropped, rel=1e-12)
    others = [i for i in range(len(P2)) if i != i_m]
    np.testing.assert_array_equal(y_meco[others], y_mapped[others])
    assert ho.fairing_on is not drop_fairing
    assert ("fairing" in _names(trace)) is (rule is not None and not isinstance(rule, str))
    assert ho.t_ign2_s == pytest.approx(t_meco + 11.0, abs=1e-12)
    assert coast.spec.t0 == t_meco
    staging = trace.first_event("staging")
    assert staging is not None and staging.stage == "stage2" and staging.t_s == t_meco


def _heating_rate(y: np.ndarray, speed_mps: float) -> float:
    """0.5 rho V^3 [W/m^2] with rho from ambiance at h = r - R_E (the test's own
    density) and the given speed V [m/s]."""
    h = float(P2.get(y, "r_m")) - R_EARTH_M
    rho = float(Atmosphere(h).density[0])
    return 0.5 * rho * speed_mps**3


def _speeds(y: np.ndarray) -> tuple[float, float]:
    """(|v_rel|, |v_in|) [m/s] of a planar state, computed here: v_rel = (v_r, v_theta -
    omega_p r)."""
    r, v_r, v_t = (float(P2.get(y, n)) for n in ("r_m", "v_r_mps", "v_theta_mps"))
    return math.hypot(v_r, v_t - OMEGA_P * r), math.hypot(v_r, v_t)


def test_heating_rate_uses_v_rel_and_the_local_density(gate_vehicle: Vehicle) -> None:
    """The fairing criterion fmh_rate_W_m2 = 0.5 rho(h) |v_rel|^3, with rho from
    ambiance at h = r - R_E and v_rel = (v_r, v_theta - omega_p r) computed here, at 40
    seeded states from the ground to 80 km (1e-12 relative) and at the pad MECO. The
    staging decision turns on it: at MECO the rate with the inertial speed is 1.5x the
    rate with |v_rel| ((V_in/V_rel)^3), and a heating limit between the two drops the
    fairing with stage 1, while a limit just below the |v_rel| rate keeps it on."""
    rng = np.random.default_rng(21)
    for h, v_r, u in zip(
        rng.uniform(0.0, 80.0e3, 40),
        rng.uniform(-500.0, 3000.0, 40),
        rng.uniform(-400.0, 3000.0, 40),
        strict=True,
    ):
        r = R_EARTH_M + h
        y = P2.build(r_m=r, v_r_mps=v_r, v_theta_mps=OMEGA_P * r + u, m_kg=1.0e5)
        expected = _heating_rate(y, math.hypot(v_r, u))
        assert fmh_rate_W_m2(y, ENV) == pytest.approx(expected, rel=1e-12)
    planner = _planner(gate_vehicle, settings=IntegratorSettings(rtol=1e-10, dense_output=False))
    ho = planner.stage1(DELTA_RAD, planner.start(), through_staging=False)
    _t, y_meco = ho.prefix.burnouts["stage1"]
    v_rel, v_in = _speeds(y_meco)
    rate_rel, rate_in = _heating_rate(y_meco, v_rel), _heating_rate(y_meco, v_in)
    assert fmh_rate_W_m2(y_meco, ENV) == pytest.approx(rate_rel, rel=1e-12)
    assert rate_in > 1.4 * rate_rel
    for limit, drops in ((math.sqrt(rate_rel * rate_in), True), (rate_rel * (1 - 1e-9), False)):
        rule = FairingDrop("free_molecular_heating", limit)
        vehicle = dataclasses.replace(gate_vehicle, fairing_drop=rule)
        p = _planner(vehicle, settings=IntegratorSettings(rtol=1e-10, dense_output=False))
        staged = p.stage1(DELTA_RAD, p.start())
        assert staged.fairing_on is not drops, limit
        assert ("fairing" in _names(staged.prefix)) is drops


def test_vertical_only_guidance_takes_no_kick_angle(gate_vehicle: Vehicle) -> None:
    """Vertical-only guidance flies the rise to burnout without a kick: its hand-over
    records delta_rad None, and a kick angle passed to ``from_kick`` or ``run`` is
    refused (ValueError) instead of being recorded for a flight that never kicked."""
    planner = _planner(gate_vehicle, guidance=GuidanceSpec.vertical_only())
    kick = planner.to_kick(planner.start())
    assert not kick.kicked
    ho = planner.from_kick(None, kick, through_staging=False)
    assert ho.delta_rad is None and math.isnan(ho.meco["t_kick_s"])
    with pytest.raises(ValueError, match="must be None"):
        planner.from_kick(DELTA_RAD, kick, through_staging=False)
    with pytest.raises(ValueError, match="must be None"):
        planner.run(DELTA_RAD)


def test_later_stage_ignition_delay_adds_a_coast(gate_vehicle: Vehicle) -> None:
    """A stage-2 t_ign_s of 1.5 s adds a COAST_PRE_IGN after the 11 s staging coast;
    stage 2 ignites 12.5 s after MECO. A negative later-stage t_ign_s is refused."""
    planner = _planner(gate_vehicle, ign2=IgnitionSpec(1.5))
    ho = planner.stage1(DELTA_RAD, planner.start())
    t_meco = ho.prefix.burnouts["stage1"][0]
    assert ho.t_ign2_s == pytest.approx(t_meco + 12.5, abs=1e-12)
    assert ho.prefix.phases[-1].spec.kind == COAST_PRE_IGN
    with pytest.raises(ValueError, match="t_ign_s >= 0"):
        _planner(gate_vehicle, ign2=IgnitionSpec(-1.0))


@pytest.mark.parametrize("case", ["pad", "silo_cold"])
def test_loss_identity_closes_to_stage2_ignition(gate_vehicle: Vehicle, case: str) -> None:
    """From the flight start (pad: V0 = 0 after the hold; silo: V0 = the release
    speed) to MECO and on through the staging map and coast to stage-2 ignition,
    V - V0 = J_vac - J_grav - J_drag - J_steer - J_bp within the shipped identity
    tolerance 1e-5 m/s (measured ~1e-9 m/s). The gravity turn and the coasts book
    exactly zero steering loss; the kick books a small one."""
    planner = _planner(gate_vehicle, IgnitionSpec(-2.0 if case == "pad" else 0.5))
    if case == "pad":
        trace = planner.run(DELTA_RAD)
        ho = planner.stage1(DELTA_RAD, planner.start())
    else:
        assist, track = _silo()
        trace = planner.run(DELTA_RAD, assist, track)
        ho = planner.stage1(DELTA_RAD, planner.start(assist, track))
    assert trace.y_flight_start is not None and ho.y_ign2 is not None
    v0 = _speed_rel(trace.y_flight_start)
    _t, y_meco = trace.burnouts["stage1"]
    assert abs(_closure_mps(y_meco, v0)) < IDENTITY_TOL_MPS
    assert abs(_closure_mps(ho.y_ign2, v0)) < IDENTITY_TOL_MPS
    i_s = P2.index("J_steer_mps")
    for p in ho.prefix.phases:
        if p.spec.kind in (GRAVITY_TURN, COAST_STAGING, COAST_PRE_IGN):
            assert p.y_end[i_s] == p.y[i_s, 0], p.spec.kind
    assert 0.0 < ho.meco["kick_steering_loss_mps"] < 1.0
    assert ho.meco["J_steer_mps"] == pytest.approx(ho.meco["kick_steering_loss_mps"], abs=1e-3)


# ------------------------------------------------------------------ failed ignitions


def test_failed_stage1_ignition_on_a_silo(gate_vehicle: Vehicle) -> None:
    """silo_failed: stage 1 never lights; after release the vehicle coasts to its
    radial apex (a phase split) and falls back to the silo mouth: status impact, the
    ignition_failed event at release, apex, impact at altitude 0, end; the whole coast
    is COAST, and the loss identity closes from release to impact."""
    assist, track = _silo()
    planner = _planner(gate_vehicle, IgnitionSpec(0.0, fails=True), end="impact")
    trace = planner.run(None, assist, track)
    assert trace.status == "impact" and trace.failed_stage == "stage1"
    assert trace.t_fail_s == trace.t_release_s
    assert _names(trace) == [
        "push_start",
        "release",
        "ignition_failed",
        "apex",
        "impact",
        "end",
    ]
    assert [p.spec.kind for p in trace.phases if p.spec.kind != "ASSIST"] == [COAST, COAST]
    impact = trace.first_event("impact")
    assert impact is not None and abs(impact.value("alt_m")) < 1e-3
    assert trace.y_flight_start is not None
    v0 = _speed_rel(trace.y_flight_start)
    assert abs(_closure_mps(trace.phases[-1].y_end, v0)) < IDENTITY_TOL_MPS
    assert "stage1" not in trace.t_ign_abs_s


def test_failed_stage1_ignition_on_the_pad(gate_vehicle: Vehicle) -> None:
    """On the pad a failed stage 1 never lifts off: status no_liftoff, no flight."""
    planner = _planner(gate_vehicle, IgnitionSpec(0.0, fails=True), end="impact")
    trace = planner.run(None)
    assert trace.status == "no_liftoff" and trace.failed_stage == "stage1"
    assert trace.t_flight_start_s is None


def test_failed_stage2_ignition_coasts_to_the_ground(gate_vehicle: Vehicle) -> None:
    """Stage 2 fails after the staging coast: the vehicle coasts to its apex and back
    to the ground (status impact), the ignition_failed event is stage 2's at the coast
    end, and the loss identity closes from the pad to the impact."""
    planner = _planner(gate_vehicle, ign2=IgnitionSpec(0.0, fails=True), end="impact")
    trace = planner.run(DELTA_RAD)
    assert trace.status == "impact" and trace.failed_stage == "stage2"
    names = _names(trace)
    assert names[-5:] == ["staging", "ignition_failed", "apex", "impact", "end"]
    t_meco = trace.burnouts["stage1"][0]
    assert trace.t_fail_s == pytest.approx(t_meco + 11.0, abs=1e-12)
    assert abs(_closure_mps(trace.phases[-1].y_end, 0.0)) < IDENTITY_TOL_MPS


# ----------------------------------------------------------------- engine discipline


def test_no_phase_lists_the_event_that_ended_the_previous_one(gate_vehicle: Vehicle) -> None:
    """Across a pad run, a silo run and a falling-start run, the phase after one that
    a terminal event ended never lists that event, and every flight phase lists the
    ground event or, while rising, the apex split that ends it before the ground. No
    run carries a flag."""
    assist, track = _silo()
    traces = [
        _planner(gate_vehicle).run(DELTA_RAD),
        _planner(gate_vehicle, IgnitionSpec(0.5)).run(DELTA_RAD, assist, track),
        _planner(
            gate_vehicle,
            IgnitionSpec(9.0, startup=Startup("step")),
            guidance=GuidanceSpec(5.0, 60.0, 60.0),
        ).run(DELTA_RAD, assist, track),
    ]
    for trace in traces:
        flight = [p for p in trace.phases if p.spec.kind not in ("HOLD", "ASSIST")]
        for prev, nxt in itertools.pairwise(flight):
            listed = {e.name for e in nxt.spec.events}
            if prev.ended_by not in ("t_end", "zero_span"):
                assert prev.ended_by not in listed, (prev.spec.kind, prev.ended_by)
        for p in flight:
            names = {e.name for e in p.spec.events}
            assert "impact" in names or "apex" in names, p.spec.kind
        assert trace.flags == (), trace.flags


def test_search_mode_flies_the_same_stage1(gate_vehicle: Vehicle) -> None:
    """Dense output off (the search mode) takes the same steps: the stage-1 handover
    (MECO record, stage-2 ignition state) and every event record equal the dense-on
    flight's exactly; only the dense-on trace can be resampled."""
    on = _planner(gate_vehicle)
    off = _planner(gate_vehicle, settings=IntegratorSettings(rtol=1e-10, dense_output=False))
    ho_on = on.stage1(DELTA_RAD, on.start())
    ho_off = off.stage1(DELTA_RAD, off.start())
    assert dict(ho_on.meco) == dict(ho_off.meco)
    assert ho_on.y_ign2 is not None and ho_off.y_ign2 is not None
    np.testing.assert_array_equal(ho_on.y_ign2, ho_off.y_ign2)
    assert ho_on.prefix.events == ho_off.prefix.events
    assert ho_off.prefix.dense_off and not ho_on.prefix.dense_off


@pytest.mark.parametrize("module", ["guidance.py", "phases/planar.py", "phases/engine.py"])
def test_planar_modules_have_docstrings(repo_root: Path, module: str) -> None:
    """Every public function, class and method of the step-21 modules (and of
    phases/engine.py, which holds the planar event factories) has a docstring
    (tests/test_scaffold.py does not list them yet)."""
    path = repo_root / "src" / "launchsim" / module
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assert ast.get_docstring(tree)
    missing = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.ClassDef) and not node.name.startswith("_"):
            if ast.get_docstring(node) is None:
                missing.append(node.name)
            if isinstance(node, ast.ClassDef):
                missing += [
                    f"{node.name}.{m.name}"
                    for m in node.body
                    if isinstance(m, ast.FunctionDef)
                    and not m.name.startswith("_")
                    and ast.get_docstring(m) is None
                ]
    assert not missing, missing
