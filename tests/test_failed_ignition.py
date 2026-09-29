"""Failed ignition (docs/physics.md, "Failed-ignition coast").

``fails: true`` makes the stage's T_vac identically zero for the whole run (the
config requires ``end: impact``). Through the silo the run is HOLD/ASSIST as configured,
RELEASE, COAST (sigma +1, ends at apex), FALL (sigma -1, ends at impact on z = 0) with
status ``impact``; the stage gets no ignition time, an ``ignition_failed`` event marks
where the coast began, and the ``failed_*`` metrics report it. Every expected value is a
closed form written here, with v0 = sqrt(2 a L) the exit speed and z = 0 the ground:

- constant g:  h = v0^2/(2 g), t_up = v0/g, t_return = 2 v0/g, |v_impact| = v0;
- mu/r^2 (a radial Kepler orbit, as in test_coast.py): r_a = 1/(1/R_E - v0^2/(2 mu)),
  a = r_a/2, apex at E = pi with cos E0 = 1 - R_E/a at the surface, so t_up =
  sqrt(a^3/mu) [pi - (E0 - sin E0)] = sqrt(a^3/mu) (delta + sin delta) with delta =
  pi - E0 = 2 asin(sqrt(h/r_a)), h = r_a - R_E = h_c/(1 - h_c/R_E), h_c = v0^2/(2 g_s),
  g_s = mu/R_E^2 (the asin form is the same closed form without the acos roundoff
  near cos E0 = -1, ~2e-13 relative); t_return = 2 t_up by time symmetry, |v_impact| =
  v0 by energy conservation;
- shaft bottom (derived, the mirror of the push under the track's constant g_eff):
  v_bottom^2 = v_impact^2 + 2 g_eff (z_impact - z_track_start), = v0^2 + 2 g_eff L when
  the mouth is at the ground;
- the braked carriage, parked d = v0^2/(2 a_brake) above the mouth in the fall-back
  path (the first obstacle): the vehicle comes back down to it at t_up + t_fall(h - d)
  with constant g: t_fall(x) = sqrt(2 x/g), |v| = sqrt(v0^2 - 2 g d); mu/r^2: the
  time from apex to a drop x below it is sqrt(a^3/mu) (delta + sin delta) with delta =
  2 asin(sqrt(x/r_a)) (the same form as t_up, x = h), and |v|^2 = v0^2 - 2 mu d /
  (R_E (R_E + d)) by energy;
- gravity loss (J_grav = integral of g sigma dt from the flight start, the loss
  identity's |v_f| - |v_0| = J_vac - J_grav): an unpowered rise and fall between the
  same altitude nets 0; between different altitudes it is v_start - v_end (negative
  when the vehicle comes down faster than it left).

F9, 3 g0, L = 100 m: g0 -> 300.000 m, 7.822 s, 15.644 s; mu/r^2 -> 300.270 m,
7.8291 s, 15.658 s; 76.707 m/s back at the mouth, 88.56 m/s at the shaft bottom; the
carriage (a_brake = 5 g0) parks 60.0 m above the mouth and is met at 14.83 s at
68.6 m/s.
"""

from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
import pytest
import yaml

from launchsim import sim
from launchsim.assist.constant_accel import ConstantAccelAssist
from launchsim.assist.track import VERTICAL, StraightTrack
from launchsim.config import IgnitionConfig, IntegratorConfig, RunConfig, resolve_experiment
from launchsim.constants import G0_MPS2, MU_EARTH_M3S2, R_EARTH_M
from launchsim.dynamics import ConstantGravity
from launchsim.phases import AscentStart, IgnitionSpec, IntegratorSettings
from launchsim.vehicle import Vehicle

if TYPE_CHECKING:
    from conftest import RunVertical

NET_ACCEL_G = 3.0
A = NET_ACCEL_G * G0_MPS2
L = 100.0
V0 = math.sqrt(2.0 * A * L)  # exit speed of the prescribed-acceleration push
BRAKE_G = 5.0
D_BRAKE = V0**2 / (2.0 * BRAKE_G * G0_MPS2)  # where the carriage parks above the mouth
G_EFF = MU_EARTH_M3S2 / R_EARTH_M**2
REL = 1e-9
APEX_ABS_M = 1e-5  # the apex altitude is resolved to the integrator's ATOL_M = 1e-6 m
FAILED_KEYS = (
    "failed_apex_alt_m",
    "failed_t_apex_s",
    "failed_carriage_alt_m",
    "failed_t_carriage_s",
    "failed_speed_at_carriage_mps",
    "failed_t_return_s",
    "failed_impact_speed_mps",
    "failed_speed_at_shaft_bottom_mps",
)


@pytest.fixture(scope="module")
def silo_failed_run(repo_root: Path, f9_vehicle_dict: dict[str, Any]) -> RunConfig:
    """The shipped ``silo_failed`` variant of experiments/silo_screening_1d.yaml,
    resolved through config.py; its silo block is checked against this file's
    constants so the closed forms below apply to what is actually shipped."""
    exp = yaml.safe_load(
        (repo_root / "experiments" / "silo_screening_1d.yaml").read_text(encoding="utf-8")
    )
    cfg = resolve_experiment(exp, f9_vehicle_dict).variants["silo_failed"].run
    assist = cfg.assist
    assert assist.model == "constant_accel"
    assert assist.net_accel_g == NET_ACCEL_G and assist.stroke_m == L
    assert assist.carriage_mass_t == 0.0 and assist.track.exit_altitude_m == 0.0
    assert assist.brake_decel_g == BRAKE_G
    assert cfg.ignition["stage1"].fails and cfg.end == "impact"
    return cfg


def _kepler_time_from_apex(h: float, drop: float) -> float:
    """Time [s] for a radial Kepler coast with apex h [m] above the surface to fall
    drop [m] below that apex under mu/r^2 (or, by time symmetry, to rise the same
    distance to it): sqrt(a^3/mu) (delta + sin delta), delta = 2 asin(sqrt(drop/r_a)),
    the conditioned spelling of the module docstring; drop = h gives t_up."""
    r_a = R_EARTH_M + h
    a = r_a / 2.0
    delta = 2.0 * math.asin(math.sqrt(drop / r_a))
    return math.sqrt(a**3 / MU_EARTH_M3S2) * (delta + math.sin(delta))


def _kepler_t_up(v0: float) -> tuple[float, float]:
    """(apex altitude [m], time to apex [s]) of a radial coast from r = R_E at speed v0
    under mu/r^2, from the degenerate-ellipse closed form in the conditioned
    (delta = pi - E0 through asin) spelling of the module docstring."""
    g_s = MU_EARTH_M3S2 / R_EARTH_M**2
    h_c = v0**2 / (2.0 * g_s)
    h = h_c / (1.0 - h_c / R_EARTH_M)  # = r_a - R_E with 1/r_a = 1/R_E - v0^2/(2 mu)
    return h, _kepler_time_from_apex(h, h)


def _f9_silo_assist(g: float) -> ConstantAccelAssist:
    return ConstantAccelAssist(
        net_accel_mps2=A,
        carriage_mass_kg=0.0,
        brake_decel_mps2=BRAKE_G * G0_MPS2,
        efficiency=0.5,
        f_imp=0.0,
        allow_negative_drive=False,
        g_eff_mps2=g,
    )


def _simulate_silo_failed(
    vehicle: Vehicle,
    g: float,
    settings: IntegratorSettings,
    *,
    exit_altitude_m: float = 0.0,
    stage1: IgnitionSpec | None = None,
) -> sim.Result:
    """``sim.simulate`` of the F9 through the 3 g0, 100 m silo with a failed first stage
    under ConstantGravity(g) in flight and g_eff = g on the track; the track exit
    (mouth) at exit_altitude_m in the datum frame whose ground is z = 0."""
    specs = {name: IgnitionSpec() for name in vehicle.stage_names}
    specs["stage1"] = IgnitionSpec(fails=True) if stage1 is None else stage1
    return sim.simulate(
        vehicle=vehicle,
        ignition=specs,
        gravity=ConstantGravity(g),
        g_eff_mps2=g,
        assist=_f9_silo_assist(g),
        track=StraightTrack(L, VERTICAL, exit_altitude_m - L),
        start=None,
        end="impact",
        settings=settings,
    )


def _events(result: sim.Result, name: str) -> pd.DataFrame:
    return result.events[result.events["event"] == name]


def _assert_unpowered(result: sim.Result, m_kg: float) -> None:
    """T_vac is 0 on every row of the run and the mass never changes."""
    ts = result.timeseries
    assert float(ts["thrust_vac_N"].abs().max()) == 0.0
    assert float(ts["thrust_N"].abs().max()) == 0.0
    assert float(ts["m_kg"].min()) == m_kg and float(ts["m_kg"].max()) == m_kg
    assert _events(result, "ignition").empty


def _assert_coast_shape(result: sim.Result, stage: str) -> None:
    """Status impact, exactly one apex and one impact, one ignition_failed for stage;
    with the mouth at the ground the failed_* items equal the generic apex/impact ones."""
    assert result.status == "impact"
    assert len(_events(result, "apex")) == 1
    assert len(_events(result, "impact")) == 1
    failed = _events(result, "ignition_failed")
    assert len(failed) == 1 and failed.iloc[0]["stage"] == stage
    m = result.metrics
    assert m["failed_stage"] == stage
    assert m[f"t_ign_rel_release_s_{stage}"] is None
    assert m["failed_apex_alt_m"] == m["apex_alt_m"]
    assert m["failed_t_apex_s"] == m["apex_t_s"]
    assert m["failed_t_return_s"] == m["impact_t_s"]
    assert m["failed_impact_speed_mps"] == m["impact_speed_mps"]
    assert any(a.startswith("failed ignition") for a in result.assumptions)


def test_silo_failed_under_inverse_square_gravity_via_sim_run(
    silo_failed_run: RunConfig, f9_vehicle: Vehicle
) -> None:
    """The shipped silo_failed variant: apex r_a - R_E = 300.270 m at the Kepler t_up =
    7.8291 s after release, the parked carriage (60.0 m above the mouth) met on the way
    down at 14.83 s at 68.6 m/s, back at the mouth at 2 t_up = 15.658 s at the exit
    speed, 88.56 m/s at the shaft bottom; the coast nets no gravity loss (up and down
    cancel)."""
    result = sim.run(silo_failed_run, f9_vehicle)
    # The only flags a failed stage may raise here are its ignored ignition settings
    # (the variant may inherit the baseline's t_ign_s by dict merge; with fails: true
    # they are moot). Nothing else: no disarmed event, no tensile interface.
    assert all(f.startswith("ignition_failed: stage 'stage1'") for f in result.flags)
    _assert_coast_shape(result, "stage1")
    _assert_unpowered(result, f9_vehicle.liftoff_mass_kg())
    m = result.metrics
    h, t_up = _kepler_t_up(V0)
    assert abs(m["speed_at_release_mps"] - V0) < REL * V0
    assert abs(m["failed_apex_alt_m"] - h) < APEX_ABS_M
    assert math.isclose(m["failed_t_apex_s"], t_up, rel_tol=REL)
    assert math.isclose(m["failed_t_return_s"], 2.0 * t_up, rel_tol=REL)
    assert math.isclose(m["failed_impact_speed_mps"], V0, rel_tol=REL)
    assert math.isclose(
        m["failed_speed_at_shaft_bottom_mps"], math.sqrt(V0**2 + 2.0 * G_EFF * L), rel_tol=REL
    )
    # The braked carriage parks d_brake above the mouth (the run's own braking metric)
    # and is the first obstacle on the way down: t_up + the Kepler fall of h - d_brake
    # from the apex, at the energy speed sqrt(v0^2 - 2 mu d/(R_E (R_E + d))).
    assert math.isclose(m["failed_carriage_alt_m"], D_BRAKE, rel_tol=REL)
    assert math.isclose(m["failed_carriage_alt_m"], m["braking_distance_m"], rel_tol=REL)
    t_carriage = t_up + _kepler_time_from_apex(h, h - D_BRAKE)
    v_carriage = math.sqrt(
        V0**2 - 2.0 * MU_EARTH_M3S2 * D_BRAKE / (R_EARTH_M * (R_EARTH_M + D_BRAKE))
    )
    assert math.isclose(m["failed_t_carriage_s"], t_carriage, rel_tol=REL)
    assert math.isclose(m["failed_speed_at_carriage_mps"], v_carriage, rel_tol=REL)
    assert m["failed_t_apex_s"] < m["failed_t_carriage_s"] < m["failed_t_return_s"]
    # Hand numbers quoted in the README and docs/physics.md (a cross-check of the
    # constants only; the closed forms above are the test).
    assert abs(h - 300.270) < 5e-4 and abs(t_up - 7.8291) < 5e-5
    assert abs(m["failed_speed_at_shaft_bottom_mps"] - 88.56) < 5e-3
    assert abs(t_carriage - 14.83) < 5e-3 and abs(v_carriage - 68.6) < 2e-2
    # Release onward the identity reads |v_f| - |v_0| = -J_grav with J_vac = 0, and the
    # symmetric coast cancels its gravity term.
    assert m["dv_vac_mps"] == 0.0 and m["steering_loss_mps"] == 0.0
    assert math.isclose(m["speed_end_mps"], m["speed_start_mps"], rel_tol=REL)
    assert abs(m["gravity_loss_mps"]) < 1e-6
    assert abs(m["identity_residual_mps"]) < 1e-9
    # The failed stage keeps its felt g from the push (the run-wide peak), none in flight.
    assert m["peak_felt_g_flight"] == 0.0 and m["peak_felt_axial_g_phase"] == "ASSIST"


def test_silo_failed_under_constant_gravity_via_simulate(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """ConstantGravity(g0) in flight and g_eff = g0 on the track: apex v0^2/(2 g0) =
    3 L = 300.000 m exactly, t_up = v0/g0 = 7.822 s, back at 2 v0/g0 = 15.644 s."""
    g = G0_MPS2
    result = _simulate_silo_failed(f9_vehicle, g, tight_settings)
    assert result.flags == []
    _assert_coast_shape(result, "stage1")
    _assert_unpowered(result, f9_vehicle.liftoff_mass_kg())
    m = result.metrics
    assert math.isclose(m["failed_apex_alt_m"], V0**2 / (2.0 * g), rel_tol=REL)
    assert math.isclose(m["failed_apex_alt_m"], NET_ACCEL_G * L, rel_tol=REL)  # = 3 L
    assert math.isclose(m["failed_t_apex_s"], V0 / g, rel_tol=REL)
    assert math.isclose(m["failed_t_return_s"], 2.0 * V0 / g, rel_tol=REL)
    assert math.isclose(m["failed_impact_speed_mps"], V0, rel_tol=REL)
    assert math.isclose(
        m["failed_speed_at_shaft_bottom_mps"], math.sqrt(V0**2 + 2.0 * g * L), rel_tol=REL
    )
    assert abs(m["failed_apex_alt_m"] - 300.000) < 1e-6
    assert abs(m["failed_t_apex_s"] - 7.822) < 5e-4 and abs(m["failed_t_return_s"] - 15.644) < 1e-3
    assert abs(m["gravity_loss_mps"]) < 1e-6 and abs(m["identity_residual_mps"]) < 1e-9
    # The parked carriage at d_brake: met at t_up + sqrt(2 (h - d)/g) at sqrt(v0^2 - 2 g d).
    h = V0**2 / (2.0 * g)
    assert math.isclose(m["failed_carriage_alt_m"], D_BRAKE, rel_tol=REL)
    assert math.isclose(
        m["failed_t_carriage_s"], V0 / g + math.sqrt(2.0 * (h - D_BRAKE) / g), rel_tol=REL
    )
    assert math.isclose(
        m["failed_speed_at_carriage_mps"], math.sqrt(V0**2 - 2.0 * g * D_BRAKE), rel_tol=REL
    )


def test_mouth_above_the_ground_splits_return_and_impact(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """Track exit 50 m above the ground (constant g): the vehicle is back at the mouth
    at 2 v0/g at v0 (the return), falls on to the ground at sqrt(v0^2 + 2 g 50) at
    2 v0/g + (v_impact - v0)/g (the impact), and the shaft-bottom speed counts only the
    fall from the ground to the track start at -50 m: sqrt(v_impact^2 + 2 g 50) =
    sqrt(v0^2 + 2 g L), the same as with the mouth at the ground. A flag names the
    split (with the planner's ground altitude, not the impact root's residue). The
    asymmetric coast pins the sign of the gravity loss: J_grav = v0 - v_impact < 0."""
    g = G0_MPS2
    z_exit = 50.0
    result = _simulate_silo_failed(f9_vehicle, g, tight_settings, exit_altitude_m=z_exit)
    assert result.status == "impact"
    flags = [f for f in result.flags if f.startswith("failed ignition: the track exit (mouth)")]
    assert len(flags) == 1
    assert "is at z = 50 m and the impact at the ground z = 0 m" in flags[0]
    m = result.metrics
    v_imp = math.sqrt(V0**2 + 2.0 * g * z_exit)
    assert math.isclose(m["failed_apex_alt_m"], z_exit + V0**2 / (2.0 * g), rel_tol=REL)
    assert math.isclose(m["failed_t_apex_s"], V0 / g, rel_tol=REL)
    assert math.isclose(m["failed_t_return_s"], 2.0 * V0 / g, rel_tol=REL)
    assert math.isclose(m["impact_t_s"], 2.0 * V0 / g + (v_imp - V0) / g, rel_tol=REL)
    assert m["failed_t_return_s"] < m["impact_t_s"]
    assert math.isclose(m["failed_impact_speed_mps"], v_imp, rel_tol=REL)
    assert math.isclose(
        m["failed_speed_at_shaft_bottom_mps"], math.sqrt(v_imp**2 + 2.0 * g * z_exit), rel_tol=REL
    )
    assert math.isclose(
        m["failed_speed_at_shaft_bottom_mps"], math.sqrt(V0**2 + 2.0 * g * L), rel_tol=REL
    )
    # The carriage parks d_brake above the raised mouth.
    assert math.isclose(m["failed_carriage_alt_m"], z_exit + D_BRAKE, rel_tol=REL)
    assert math.isclose(
        m["failed_speed_at_carriage_mps"], math.sqrt(V0**2 - 2.0 * g * D_BRAKE), rel_tol=REL
    )
    # Gravity loss: g t_up on the way up, -g t_fall on the way down, = v0 - v_impact.
    assert m["gravity_loss_mps"] < 0.0
    assert math.isclose(m["gravity_loss_mps"], V0 - v_imp, rel_tol=1e-8)
    assert math.isclose(
        m["speed_end_mps"] - m["speed_start_mps"], -m["gravity_loss_mps"], rel_tol=1e-8
    )


def test_mouth_below_the_ground_never_returns(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """A bookkeeping check of the altitude split only, not a consistent 1-D geometry:
    with the track exit 30 m below the ground (constant g) the vehicle rises through
    z = 0 (a rising phase lists no impact) and "hits the ground" there on the way back
    down, at sqrt(v0^2 - 2 g 30), before it can be back at the mouth (return None); the
    shaft-bottom speed counts the 130 m from the ground to the track start:
    sqrt(v_impact^2 + 2 g 130) = sqrt(v0^2 + 2 g L) again. No shipped config has a
    non-zero exit altitude (the plan's datum is mouth = ground = 0)."""
    g = G0_MPS2
    z_exit = -30.0
    result = _simulate_silo_failed(f9_vehicle, g, tight_settings, exit_altitude_m=z_exit)
    assert result.status == "impact"
    assert any(f.startswith("failed ignition: the track exit (mouth)") for f in result.flags)
    m = result.metrics
    h = z_exit + V0**2 / (2.0 * g)  # apex above the ground
    v_imp = math.sqrt(V0**2 + 2.0 * g * z_exit)
    assert math.isclose(m["failed_apex_alt_m"], h, rel_tol=REL)
    assert math.isclose(m["failed_t_apex_s"], V0 / g, rel_tol=REL)
    assert m["failed_t_return_s"] is None
    assert math.isclose(m["impact_t_s"], V0 / g + math.sqrt(2.0 * h / g), rel_tol=REL)
    assert math.isclose(m["failed_impact_speed_mps"], v_imp, rel_tol=REL)
    assert math.isclose(
        m["failed_speed_at_shaft_bottom_mps"],
        math.sqrt(v_imp**2 + 2.0 * g * (0.0 - (z_exit - L))),
        rel_tol=REL,
    )
    assert math.isclose(
        m["failed_speed_at_shaft_bottom_mps"], math.sqrt(V0**2 + 2.0 * g * L), rel_tol=REL
    )


def test_ignition_settings_of_a_failed_stage_are_flagged_as_ignored(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """fails: true with t_ign_s = -2 from push_start and a startup override: nothing
    burns (no hold, no ignition event, the same coast as the plain failure) and a run
    flag names the ignored settings."""
    g = G0_MPS2
    spec = IgnitionSpec(
        t_ign_s=-2.0, reference="push_start", startup=f9_vehicle.stages[0].startup, fails=True
    )
    result = _simulate_silo_failed(f9_vehicle, g, tight_settings, stage1=spec)
    plain = _simulate_silo_failed(f9_vehicle, g, tight_settings)
    _assert_coast_shape(result, "stage1")
    _assert_unpowered(result, f9_vehicle.liftoff_mass_kg())
    assert result.metrics["hold_duration_s"] is None
    flags = [f for f in result.flags if f.startswith("ignition_failed: stage 'stage1'")]
    assert len(flags) == 1
    assert "t_ign_s = -2" in flags[0] and "reference = 'push_start'" in flags[0]
    assert "startup override" in flags[0]
    assert [f for f in result.flags if not f.startswith("ignition_failed")] == []
    for key in ("failed_apex_alt_m", "failed_t_apex_s", "failed_t_return_s"):
        assert result.metrics[key] == plain.metrics[key]


def test_failed_ignition_on_the_pad_still_reports_no_liftoff(f9_vehicle: Vehicle) -> None:
    """Unchanged from the pad planner: a failed first stage on the pad never lifts off
    (status no_liftoff at t_max); the failed_* coast metrics are all n/a and, since no
    coast ran, none of the failed-ignition assumptions is claimed."""
    cfg = RunConfig(
        name="pad",
        ignition={"stage1": IgnitionConfig(fails=True), "stage2": IgnitionConfig()},
        end="impact",
        integrator=IntegratorConfig(t_max_s=30.0),
    )
    result = sim.run(cfg, f9_vehicle)
    assert result.status == "no_liftoff"
    assert any(f.startswith("no_liftoff") for f in result.flags)
    assert [p.spec.kind for p in result.phases] == ["HOLD"]
    _assert_unpowered(result, f9_vehicle.liftoff_mass_kg())
    assert _events(result, "ignition_failed").empty and _events(result, "apex").empty
    m = result.metrics
    assert m["failed_stage"] == "stage1"
    assert m["t_ign_rel_release_s_stage1"] is None
    for key in FAILED_KEYS:
        assert m[key] is None
    assert not any(a.startswith("failed ignition") for a in result.assumptions)


def test_falling_coast_starting_on_the_ground_ends_at_impact_at_once(
    f9_vehicle: Vehicle, run_vertical: RunVertical
) -> None:
    """A falling coast that starts within ATOL_M of the ground is the impact itself
    (the engine's disarm rule cannot fire an event the phase starts on): a pad start
    already sinking at 5 m/s with the first stage failed impacts at t = 0 at 5 m/s; a
    start rising at 1 mm/s reaches its apex v0^2/(2 g) = 51 nm (inside ATOL_M) at v0/g
    and the FALL that follows is a zero-length impact there. Neither runs to t_max."""
    g = G0_MPS2
    fails = {"stage1": IgnitionSpec(fails=True)}
    sinking = run_vertical(
        f9_vehicle, fails, ConstantGravity(g), g, AscentStart(0.0, -5.0), "impact"
    )
    assert sinking.status == "impact"
    assert [(p.spec.kind, p.ended_by) for p in sinking.phases] == [("FALL", "impact")]
    assert sinking.metrics["impact_t_s"] == 0.0 and sinking.metrics["impact_speed_mps"] == 5.0
    assert sinking.metrics["failed_apex_alt_m"] is None
    assert sinking.metrics["failed_t_return_s"] == 0.0
    assert any("starts on the ground" in f for f in sinking.flags)
    v0 = 1e-3
    grazing = run_vertical(f9_vehicle, fails, ConstantGravity(g), g, AscentStart(0.0, v0), "impact")
    assert grazing.status == "impact"
    assert [(p.spec.kind, p.ended_by) for p in grazing.phases] == [
        ("COAST", "apex"),
        ("FALL", "impact"),
    ]
    m = grazing.metrics
    assert math.isclose(m["failed_t_apex_s"], v0 / g, rel_tol=1e-6)
    assert abs(m["failed_apex_alt_m"] - v0**2 / (2.0 * g)) < 1e-9
    assert m["impact_t_s"] == m["failed_t_apex_s"] and m["failed_impact_speed_mps"] == 0.0
    assert len(_events(grazing, "impact")) == 1 and len(_events(grazing, "apex")) == 1


def _stage1_burnout_closed_forms(vehicle: Vehicle, g: float) -> tuple[float, float, float, float]:
    """(t_b, v_bo, z_bo, m_staged) of the toy's first stage from the pad under constant g
    (the vertical-burn closed forms), with the stage-1 dry mass and fairing dropped."""
    stage1 = vehicle.stages[0]
    c = g * stage1.engine.isp_vac_s
    mdot = stage1.thrust_vac_total_N / c
    m0 = vehicle.liftoff_mass_kg()
    mf = m0 - stage1.propellant_mass_kg
    t_b = stage1.propellant_mass_kg / mdot
    v_bo = c * math.log(m0 / mf) - g * t_b
    z_bo = c * (t_b - (mf / mdot) * math.log(m0 / mf)) - 0.5 * g * t_b**2
    assert v_bo > 0.0 and z_bo > 0.0
    return t_b, v_bo, z_bo, mf - stage1.dry_mass_kg - vehicle.fairing_mass_kg


def test_failed_second_stage_coasts_from_the_first_burnout(
    two_stage_toy: Vehicle, run_vertical: RunVertical
) -> None:
    """Stage 2 fails on the two-stage toy under constant g (pad, step at t = 0, no
    staging coast): after the stage-1 burnout (the vertical-burn closed forms) the
    staged vehicle coasts to apex z_bo + v_bo^2/(2 g) and falls to the ground at
    sqrt(v_bo^2 + 2 g z_bo) at t_bo + (v_bo + v_impact)/g; nothing is burned after
    staging, and the carriage and shaft-bottom items are n/a on a pad. The gravity
    loss from the flight start is g t_b (the burn) + v_bo (the rise) - v_impact (the
    fall): the coast's own share v_bo - v_impact is negative (the vehicle comes down
    faster than it left the burnout), which pins the sign of the integrand."""
    g = G0_MPS2
    t_b, v_bo, z_bo, m_staged = _stage1_burnout_closed_forms(two_stage_toy, g)
    v_imp = math.sqrt(v_bo**2 + 2.0 * g * z_bo)
    result = run_vertical(
        two_stage_toy,
        {"stage1": IgnitionSpec(0.0), "stage2": IgnitionSpec(fails=True)},
        ConstantGravity(g),
        g,
        end="impact",
    )
    assert result.flags == []
    _assert_coast_shape(result, "stage2")
    m = result.metrics
    assert math.isclose(m["stage1_burnout_t_s"], t_b, rel_tol=REL)
    assert math.isclose(m["stage1_burnout_speed_mps"], v_bo, rel_tol=REL)
    assert math.isclose(m["stage1_burnout_alt_m"], z_bo, rel_tol=1e-8)
    assert math.isclose(m["failed_apex_alt_m"], z_bo + v_bo**2 / (2.0 * g), rel_tol=1e-8)
    assert math.isclose(m["failed_t_apex_s"], t_b + v_bo / g, rel_tol=1e-8)
    assert math.isclose(m["failed_t_return_s"], t_b + (v_bo + v_imp) / g, rel_tol=1e-8)
    assert math.isclose(m["failed_impact_speed_mps"], v_imp, rel_tol=1e-8)
    for key in ("failed_carriage_alt_m", "failed_t_carriage_s", "failed_speed_at_carriage_mps"):
        assert m[key] is None
    assert m["failed_speed_at_shaft_bottom_mps"] is None
    assert math.isclose(m["final_mass_kg"], m_staged, rel_tol=REL)
    failed = _events(result, "ignition_failed").iloc[0]
    assert math.isclose(float(failed["t_s"]), t_b, rel_tol=REL) and failed["phase"] == "COAST"
    assert math.isclose(float(failed["m_kg"]), m_staged, rel_tol=REL)
    assert m["t_ign_rel_release_s_stage1"] == 0.0
    assert v_bo - v_imp < 0.0
    assert math.isclose(m["gravity_loss_mps"], g * t_b + (v_bo - v_imp), rel_tol=1e-8)
    assert abs(m["identity_residual_mps"]) < 1e-6
    assert not any(a.startswith("failed ignition: the braked carriage") for a in result.assumptions)


def test_apex_inside_a_long_staging_coast_is_the_failed_apex(
    two_stage_toy: Vehicle, run_vertical: RunVertical
) -> None:
    """A staging coast longer than v_bo/g: the apex z_bo + v_bo^2/(2 g) at t_b + v_bo/g
    falls inside COAST_STAGING, before stage 2 fails at t_b + t_coast in FALL. It is
    still the apex of the unpowered flight that ends in the failure, so the failed_*
    items report it (and the return time is still the impact on the pad's ground)."""
    g = G0_MPS2
    t_b, v_bo, z_bo, m_staged = _stage1_burnout_closed_forms(two_stage_toy, g)
    t_coast = 1.2 * v_bo / g
    stage2 = replace(two_stage_toy.stages[1], coast_before_ignition_s=t_coast)
    vehicle = replace(two_stage_toy, stages=(two_stage_toy.stages[0], stage2))
    v_imp = math.sqrt(v_bo**2 + 2.0 * g * z_bo)
    result = run_vertical(
        vehicle,
        {"stage1": IgnitionSpec(0.0), "stage2": IgnitionSpec(fails=True)},
        ConstantGravity(g),
        g,
        end="impact",
    )
    assert result.flags == []
    _assert_coast_shape(result, "stage2")
    m = result.metrics
    failed = _events(result, "ignition_failed").iloc[0]
    assert math.isclose(float(failed["t_s"]), t_b + t_coast, rel_tol=REL)
    assert failed["phase"] == "FALL"
    apex = _events(result, "apex").iloc[0]
    assert apex["phase"] == "COAST_STAGING"
    assert math.isclose(m["failed_apex_alt_m"], z_bo + v_bo**2 / (2.0 * g), rel_tol=1e-8)
    assert math.isclose(m["failed_t_apex_s"], t_b + v_bo / g, rel_tol=1e-8)
    assert math.isclose(m["failed_t_return_s"], t_b + (v_bo + v_imp) / g, rel_tol=1e-8)
    assert math.isclose(m["failed_impact_speed_mps"], v_imp, rel_tol=1e-8)
    assert math.isclose(m["final_mass_kg"], m_staged, rel_tol=REL)
