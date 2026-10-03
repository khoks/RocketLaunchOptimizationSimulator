"""The ramp start stated by a height reached by an altitude event (SP1 step 4;
docs/physics.md, "Event rules", "Phases and events", "Stage-1 guidance and events
(planar)" and "Silo model", ramp-start conversions).

``height_method: event`` is not converted to a time before the run: the push flies
unlit (a pending ignition, never a failed one), and the planner lights stage 1 at the
root of the ``ignition_height`` event, altitude = track exit + h crossed upward on the
coast after release (``engine.ev_altitude_up``, listed only in the rising coast). The
expected values are closed forms computed here:

- the event root lies at z_exit + h to the event tolerance (ATOL_M), on the 1-D model
  under mu/r^2 and on the planar gate fork with drag and rotation, also from a mouth
  raised above the datum;
- in a drag-free constant-g coast (an injected ConstantGravity equal to the track's
  g_eff on the 1-D model) the root is at the smaller root of v_e t - g t^2/2 = h after
  release, with v = sqrt(v_e^2 - 2 g h), and the event and closed-form methods light at
  the same time (1e-9);
- from the root on, the thrust schedule (ramp end t_ramp after it, burnout t_ramp / 2 +
  m_prop / mdot_full after it) and the planar kick deadline count from the root, as
  after a time-lit ignition;
- the preflight bound V_E^2 / (2 g_eff) is conservative without drag: the 1-D coast
  under mu/r^2 peaks at h_0 / (1 - h_0 / R_E) above it (energy conservation), and a
  height between the two is refused (with drag it is permissive: next item);
- an apex below the height: GuidanceFailure("no_ignition") on the planar model when h
  lies between the apex of the flown coast (with drag, measured here from a failed
  ignition's coast) and the drag-free apex v_e^2 / (2 g_eff), status guidance_failed for
  a fixed-guidance run and search_failed for a searched one; a ValueError on the 1-D
  model (whose apex lies at or above the drag-free one unless the flight's gravity is
  stronger than g_eff: here an injected 1.01 g_eff);
- a flight start already within ATOL_M of the altitude lights at once (no coast);
- the resolver and the preflight refuse a height at or above the drag-free apex by
  either method; ``fails: true`` flags the height as ignored (a failed-ignition run);
- the new ``extra`` argument of both ``_coast`` functions, at its default, leaves their
  event lists and trajectories as before;
- the planar ramp-start metrics report trigger height_event, the requested height, no
  converted time and the achieved height of the event root, and the summary table shows
  them in the step-3 ramp-start rows; a searched planar run with a height-event ramp
  start completes (slow).
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

from launchsim import sim, summary
from launchsim.assist import build_assist
from launchsim.assist.constant_accel import ConstantAccelAssist
from launchsim.assist.track import VERTICAL, StraightTrack
from launchsim.atmosphere import ambient_scalar
from launchsim.config import (
    PLANAR_2D,
    ConstantAccelConfig,
    IgnitionConfig,
    RunConfig,
    VehicleConfig,
    resolve_experiment,
)
from launchsim.constants import G0_MPS2, MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M
from launchsim.dynamics import (
    PLANAR_LAYOUT,
    VERTICAL_LAYOUT,
    VERTICAL_STATE_NAMES,
    ConstantGravity,
    InverseSquareGravity,
    PlanarDynamics2D,
    VerticalDynamics1D,
    VerticalParams,
    rhs_vertical,
)
from launchsim.guidance import GUIDANCE_FAILURE_KINDS, GuidanceFailure, GuidanceSpec
from launchsim.phases import ASSIST_KIND, IgnitionSpec, IntegratorSettings, PhaseSpec, engine
from launchsim.phases.engine import (
    APEX_FOLD_ACCEL_MPS2,
    APEX_FOLD_GAIN_S2PM,
    ATOL_M,
    atol_for,
    ev_altitude_up,
    ev_apex,
    integrate_phase,
)
from launchsim.phases.planar import (
    COAST_PRE_IGN,
    FlightStart,
    PlanarEnvironment,
    PlanarPlanner,
    resume_builder,
)
from launchsim.phases.prelude import IGNITION_HEIGHT_EVENT, resolve_ignition
from launchsim.phases.vertical import VerticalPlanner
from launchsim.results_io import ExperimentResult
from launchsim.vehicle import Vehicle

G_EFF_1D = MU_EARTH_M3S2 / R_EARTH_M**2
"""The track's g_eff on the 1-D model [m/s^2] (omega_p = 0)."""
A = 3.0 * G0_MPS2
"""Net acceleration of the 3 g0 silo [m/s^2]."""
L = 100.0
"""Its stroke [m]."""
V_E = math.sqrt(2.0 * A * L)
"""Its exit speed [m/s] (76.70717 m/s)."""
TRACK = StraightTrack(L, VERTICAL, -L)
"""The buried vertical silo: start at z = -L, mouth (track exit) at the datum."""
EVENT_TOL_M = ATOL_M
"""The altitude event's tolerance [m] (``ev_altitude_up`` zero_tol)."""
CLOSED_FORM_ABS = 1e-9
"""Tolerance of an ignition time [s] or speed [m/s] against its closed form."""
STATE_REL = 1e-9
"""Relative tolerance of a burnout state between two runs lit at the same instant to
1e-9 s (a start lit near the apex, at almost no speed, falls back first, so absolute
differences of the state grow to about 6e-6 m over the 148 s burn)."""
SCHEDULE_ABS_S = 1e-12
"""Tolerance [s] of the ramp end against ignition + t_ramp (a phase boundary at that
time; rounding of the absolute times only)."""
RAISED_MOUTH_M = 30.0
"""Altitude [m] of a raised mouth above the datum: the height counts from the mouth."""
LAT_RAD = math.radians(28.5)
"""The shipped site latitude (azimuth 90 deg)."""
OMEGA_P = OMEGA_EARTH_RADS * math.cos(LAT_RAD)
"""The planar rotation rate at the shipped site [rad/s]."""
G_REF = MU_EARTH_M3S2 / R_EARTH_M**2 - OMEGA_P**2 * R_EARTH_M
"""The planar track's g_eff = mu/R_E^2 - omega_p^2 R_E [m/s^2] at the shipped site."""
SETTINGS = IntegratorSettings(rtol=1e-10)
FIXED_GAMMA_DEG = 20.0
"""The fixed gamma* of the fixed-guidance experiment [deg] (tests/test_planar_pipeline.py)."""
FIXED_LTG = (0.756790, 2.19338e-3)
"""The pad's LTG pair at gamma* 20 deg (tests/test_planar_pipeline.py)."""
KICK_DEG = 3.0
"""A kick angle [deg] for planner-level runs to stage-1 burnout."""
V_KICK_MPS = 50.0
"""The kick trigger speed [m/s] of the planner-level runs."""
SILO_GUIDANCE = GuidanceSpec(V_KICK_MPS, 60.0, 60.0)
"""Stage-1 guidance of the planner-level runs (v_k, kick time limit, kick deadline)."""


def _height_dt(h: float, g: float) -> float:
    """Time after release [s] at which a drag-free coast at constant g from the mouth at
    V_E reaches the height h [m] on the way up: the smaller root of V_E t - g t^2/2 = h."""
    return (V_E - math.sqrt(V_E * V_E - 2.0 * g * h)) / g


def _event_block(h: float) -> dict[str, Any]:
    """An ignition block stating the ramp start by height h [m], event method."""
    return {"at_height_m": h, "height_method": "event"}


# --------------------------------------------------------------------------- 1-D


def _assist_1d() -> ConstantAccelAssist:
    """The 3 g0, 100 m silo of the 1-D model (g_eff = mu/R_E^2)."""
    return ConstantAccelAssist(
        net_accel_mps2=A,
        carriage_mass_kg=0.0,
        brake_decel_mps2=5.0 * G0_MPS2,
        efficiency=0.5,
        g_eff_mps2=G_EFF_1D,
    )


def _resolve_1d(
    block: dict[str, Any], vehicle: Vehicle, track: StraightTrack = TRACK
) -> IgnitionSpec:
    """resolve_ignition of a stage-1 block on the 1-D silo, with the stage's startup."""
    return resolve_ignition(
        IgnitionConfig.model_validate(block),
        vehicle.stages[0].startup,
        _assist_1d(),
        track,
        G_EFF_1D,
    )


def _fly_1d(
    vehicle: Vehicle,
    spec: IgnitionSpec,
    settings: IntegratorSettings,
    gravity: Any,
    *,
    track: StraightTrack = TRACK,
    end: str = "stage1_burnout",
) -> sim.Result:
    """A 1-D silo run (sim.simulate) with stage 1's spec, the gravity model given."""
    specs = {name: IgnitionSpec() for name in vehicle.stage_names}
    specs[vehicle.stage_names[0]] = spec
    return sim.simulate(
        vehicle=vehicle,
        ignition=specs,
        gravity=gravity,
        g_eff_mps2=G_EFF_1D,
        assist=_assist_1d(),
        track=track,
        start=None,
        end=end,
        settings=settings,
    )


def _rows(result: sim.Result, name: str) -> pd.DataFrame:
    """The stage-1 event rows of a 1-D run called name."""
    ev = result.events
    return ev[(ev["event"] == name) & (ev["stage"] == "stage1")]


def test_ev_altitude_up_is_the_altitude_crossing_with_a_fold_past_the_apex() -> None:
    """ev_altitude_up(model, z, name): terminal, direction +1, zero_tol ATOL_M, g =
    altitude - z while rising or at rest (either model), plus k w^2 (k =
    APEX_FOLD_GAIN_S2PM, w the altitude rate) past an apex (w < 0), which is continuous
    at w = 0 and never below apex - z for a fall at a >= APEX_FOLD_ACCEL_MPS2 from the
    apex (w^2 = 2 a (apex - z) for constant a, computed here). A non-finite altitude
    is refused."""
    h = 50.0
    ev = ev_altitude_up(VerticalDynamics1D(), h, IGNITION_HEIGHT_EVENT)
    assert (ev.name, ev.terminal, ev.direction, ev.zero_tol) == (
        "ignition_height",
        True,
        1,
        ATOL_M,
    )
    assert ev.fn(0.0, VERTICAL_LAYOUT.build(z_m=20.0, v_mps=30.0, m_kg=1.0)) == 20.0 - h
    assert ev.fn(0.0, VERTICAL_LAYOUT.build(z_m=20.0, m_kg=1.0)) == 20.0 - h
    k = APEX_FOLD_GAIN_S2PM
    assert k == 1.0 / (2.0 * APEX_FOLD_ACCEL_MPS2)
    apex = 49.0
    for a in (APEX_FOLD_ACCEL_MPS2, G0_MPS2):
        for drop in (1e-6, 0.5, 30.0):
            w = -math.sqrt(2.0 * a * drop)
            y = VERTICAL_LAYOUT.build(z_m=apex - drop, v_mps=w, m_kg=1.0)
            assert ev.fn(0.0, y) == pytest.approx(apex - drop - h + k * w * w, abs=1e-12)
            assert ev.fn(0.0, y) >= apex - h - 1e-12
    planar = ev_altitude_up(PlanarDynamics2D(OMEGA_P, R_EARTH_M), h, "up")
    y_p = PLANAR_LAYOUT.build(r_m=R_EARTH_M + 70.0, v_r_mps=5.0, m_kg=1.0)
    assert planar.fn(0.0, y_p) == pytest.approx(70.0 - h, abs=1e-9)
    y_p = PLANAR_LAYOUT.build(r_m=R_EARTH_M + 70.0, v_r_mps=-5.0, m_kg=1.0)
    assert planar.fn(0.0, y_p) == pytest.approx(70.0 - h + 25.0 * k, abs=1e-9)
    with pytest.raises(ValueError, match="finite"):
        ev_altitude_up(VerticalDynamics1D(), math.inf, "up")


@pytest.mark.parametrize("below_apex_m", [10.0, 1.0, 1e-2, 1e-4])
def test_ev_altitude_up_finds_a_crossing_just_below_the_apex(
    below_apex_m: float, tight_settings: IntegratorSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A constant-g vacuum coast from z = 0 at v0 = 60 m/s, uncapped steps (the 1-D
    coast), listing the apex and the altitude event at apex - d: it ends by the event at
    t = (v0 - sqrt(v0^2 - 2 g z)) / g with z = apex - d (1e-9), also when the crossing
    lies inside the step that overshoots the apex (d = 1, 1e-2 and 1e-4 m: the altitude
    is back below z at that step's end, so with the fold switched off, gain 0, the same
    coast ends at the apex and misses the crossing). An altitude d above the apex is
    never reached: the apex ends the coast, the event is not logged; and a state above
    the altitude ends a phase listing it at t0 (already past)."""
    v0, g = 60.0, G0_MPS2
    apex = v0 * v0 / (2.0 * g)
    atol = atol_for(VERTICAL_STATE_NAMES)
    params = VerticalParams(ConstantGravity(g), g, schedule=None, v_sign=1)

    def coast(z_event: float, z0: float = 0.0, v_0: float = v0) -> Any:
        ev = ev_altitude_up(VerticalDynamics1D(), z_event, IGNITION_HEIGHT_EVENT)
        spec = PhaseSpec("COAST", 0, 0.0, None, rhs_vertical, params, (ev_apex(), ev), atol)
        return integrate_phase(
            spec, VERTICAL_LAYOUT.build(z_m=z0, v_mps=v_0, m_kg=1.0), tight_settings
        )

    z = apex - below_apex_m
    res = coast(z)
    assert res.ended_by == "ignition_height"
    assert abs(res.t_end - (v0 - math.sqrt(max(v0 * v0 - 2.0 * g * z, 0.0))) / g) < 1e-9
    assert abs(float(VERTICAL_LAYOUT.get(res.y_end, "z_m")) - z) < CLOSED_FORM_ABS
    res = coast(apex + below_apex_m)
    assert res.ended_by == "apex" and [n for n, _ in res.event_times] == ["apex"]
    res = coast(z, z0=z + 1.0, v_0=1.0)
    assert res.ended_by == "ignition_height" and res.t_end == 0.0 and res.notes
    if below_apex_m <= 1.0:
        monkeypatch.setattr(engine, "APEX_FOLD_GAIN_S2PM", 0.0)
        assert coast(z).ended_by == "apex"


@pytest.mark.parametrize("height", [5.0, 40.0, 200.0, 299.0])
def test_one_d_event_lies_at_the_requested_height(
    height: float, f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """On the 1-D model under mu/r^2 (the run model) stage 1 lights at the event root:
    the ignition row lies at z = z_mouth + h = h within the event tolerance, in BURN,
    at the same time and state as the ``ignition_height`` row; the push before it is
    unlit (no ignition on the track, nothing burned before release) and nothing is
    flagged; the ignition time is the root (t_ign_rel_release_s_stage1); the run states
    the event in one ramp-start assumption line and has no ramp-start metric (1-D keeps
    its metric keys)."""
    spec = _resolve_1d(_event_block(height), f9_vehicle)
    assert spec.lights_at_height and spec.trigger_value == height
    result = _fly_1d(f9_vehicle, spec, tight_settings, InverseSquareGravity(MU_EARTH_M3S2))
    ign, root = _rows(result, "ignition"), _rows(result, "ignition_height")
    assert len(ign) == 1 and len(root) == 1
    row = ign.iloc[0]
    assert row["phase"] == "BURN" and root.iloc[0]["phase"] == "COAST_PRE_IGN"
    assert abs(float(row["z_m"]) - (0.0 + height)) < EVENT_TOL_M
    assert float(row["t_s"]) == float(root.iloc[0]["t_s"])
    assert float(row["z_m"]) == float(root.iloc[0]["z_m"])
    t_rel = float(row["t_s"]) - result.metrics["t_release_s"]
    assert result.metrics["t_ign_rel_release_s_stage1"] == pytest.approx(t_rel, abs=1e-12)
    assert t_rel > 0.0
    assert result.metrics["propellant_burned_before_release_kg"] == 0.0
    assert result.status == "nominal" and result.flags == []
    assert "failed_stage" not in result.metrics
    assert "ignition_failed" not in set(result.events["event"])
    lines = [a for a in result.assumptions if a.startswith("ramp start")]
    assert len(lines) == 1 and "reached by an altitude event" in lines[0]
    assert f"height {height:g} m" in lines[0]
    assert not [k for k in result.metrics if k.startswith("ramp_start")]


def test_one_d_event_counts_from_a_raised_mouth(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """With the mouth RAISED_MOUTH_M above the datum the event lights at z = z_m + 40
    (event tolerance): an event measured from the datum would miss by z_m."""
    track = StraightTrack(L, VERTICAL, RAISED_MOUTH_M - L)
    spec = _resolve_1d(_event_block(40.0), f9_vehicle, track)
    result = _fly_1d(
        f9_vehicle, spec, tight_settings, InverseSquareGravity(MU_EARTH_M3S2), track=track
    )
    row = _rows(result, "ignition").iloc[0]
    assert abs(float(row["z_m"]) - (RAISED_MOUTH_M + 40.0)) < EVENT_TOL_M


@pytest.mark.parametrize("height", [5.0, 40.0, 200.0, 299.0, V_E * V_E / (2.0 * G_EFF_1D) - 1e-3])
def test_one_d_event_time_is_the_closed_form_in_a_drag_free_constant_g_coast(
    height: float, f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """Under an injected ConstantGravity equal to the track's g_eff (the 1-D model has
    no drag) the coast is the one the closed form assumes: the event lights at t -
    t_release = the smaller root of V_E t - g t^2/2 = h, at v = sqrt(V_E^2 - 2 g h)
    (1e-9), and the closed-form method lights at the same time and state (1e-9); also
    1 mm below the apex V_E^2 / (2 g), 14 ms before it (inside the uncapped coast's
    last step). The thrust schedule counts from the event root: the ramp ends t_ramp
    after it (1e-12 s) and stage 1 burns out t_ramp / 2 + m_prop / mdot_full after it
    (mass flow follows the linear ramp; mdot_full = n T_vac / (g0 Isp), computed here;
    1e-9 s); the ramp-end rows (t, z, v) of the two methods agree to 1e-9 and their
    burnout rows to 1e-9 s and 1e-9 relative in z and v."""
    gravity = ConstantGravity(G_EFF_1D)
    by_event = _fly_1d(
        f9_vehicle, _resolve_1d(_event_block(height), f9_vehicle), tight_settings, gravity
    )
    closed = {"at_height_m": height, "height_method": "closed_form"}
    by_closed_form = _fly_1d(f9_vehicle, _resolve_1d(closed, f9_vehicle), tight_settings, gravity)
    ev = _rows(by_event, "ignition").iloc[0]
    cf = _rows(by_closed_form, "ignition").iloc[0]
    t_event = float(ev["t_s"]) - by_event.metrics["t_release_s"]
    assert abs(t_event - _height_dt(height, G_EFF_1D)) < CLOSED_FORM_ABS
    v_closed = math.sqrt(V_E * V_E - 2.0 * G_EFF_1D * height)
    assert abs(float(ev["v_mps"]) - v_closed) < CLOSED_FORM_ABS
    assert abs(float(ev["t_s"]) - float(cf["t_s"])) < CLOSED_FORM_ABS
    assert abs(float(ev["z_m"]) - float(cf["z_m"])) < CLOSED_FORM_ABS
    assert by_event.metrics["t_release_s"] == by_closed_form.metrics["t_release_s"]
    stage = f9_vehicle.stages[0]
    t_ramp = stage.startup.t_ramp_s
    mdot_full = stage.n_engines * stage.engine.thrust_vac_N / (G0_MPS2 * stage.engine.isp_vac_s)
    t_burn = 0.5 * t_ramp + stage.propellant_mass_kg / mdot_full
    t_ign = float(ev["t_s"])
    rows = {
        (name, method): _rows(run, name)
        for name in ("ramp_end", "propellant")
        for method, run in (("event", by_event), ("closed_form", by_closed_form))
    }
    assert {key: len(r) for key, r in rows.items()} == dict.fromkeys(rows, 1)
    ramp_ev, ramp_cf = (rows["ramp_end", m].iloc[0] for m in ("event", "closed_form"))
    burn_ev, burn_cf = (rows["propellant", m].iloc[0] for m in ("event", "closed_form"))
    assert abs(float(ramp_ev["t_s"]) - t_ign - t_ramp) < SCHEDULE_ABS_S
    assert abs(float(burn_ev["t_s"]) - t_ign - t_burn) < CLOSED_FORM_ABS
    for col in ("t_s", "z_m", "v_mps"):
        assert abs(float(ramp_ev[col]) - float(ramp_cf[col])) < CLOSED_FORM_ABS, col
    assert abs(float(burn_ev["t_s"]) - float(burn_cf["t_s"])) < CLOSED_FORM_ABS
    for col in ("z_m", "v_mps"):
        assert float(burn_ev[col]) == pytest.approx(float(burn_cf[col]), rel=STATE_REL), col


def test_one_d_flown_apex_lies_above_the_preflight_bound(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """The preflight bound V_E^2 / (2 g_eff) is conservative for the event method on the
    1-D model, which has no drag: the 1-D coast from the mouth at the datum under
    mu/r^2 (a failed ignition's run to apex) peaks at h_0 / (1 - h_0 / R_E) with
    h_0 = V_E^2 / (2 g_eff) (energy
    conservation, mu/R_E - mu/(R_E + h) = V_E^2 / 2; 300.270237 m against 300.256102 m;
    1e-6 m; the apex record of the run to impact), and the resolver refuses a height
    between the two by either method, although that coast reaches it."""
    h_0 = V_E * V_E / (2.0 * G_EFF_1D)
    apex_true = h_0 / (1.0 - h_0 / R_EARTH_M)
    result = _fly_1d(
        f9_vehicle,
        _resolve_1d({"fails": True}, f9_vehicle),
        tight_settings,
        InverseSquareGravity(MU_EARTH_M3S2),
        end="impact",
    )
    apex = _rows(result, "apex")
    assert len(apex) == 1
    assert abs(float(apex.iloc[0]["z_m"]) - apex_true) < 1e-6
    assert apex_true - h_0 > 0.01
    between = 0.5 * (h_0 + apex_true)
    for method in ("event", "closed_form"):
        with pytest.raises(ValueError, match="at or above the drag-free apex"):
            _resolve_1d({"at_height_m": between, "height_method": method}, f9_vehicle)


def test_one_d_apex_below_the_height_is_refused(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """A 1-D coast whose gravity exceeds the track's g_eff (an injected 1.01 g_eff)
    peaks at V_E^2 / (2 x 1.01 g_eff), below the drag-free apex V_E^2 / (2 g_eff) that
    the resolver checks: a height between the two resolves, but the run raises
    ValueError at the apex (stage 1 never lights)."""
    g_true = 1.01 * G_EFF_1D
    apex_true = V_E * V_E / (2.0 * g_true)
    apex_free = V_E * V_E / (2.0 * G_EFF_1D)
    height = 0.5 * (apex_true + apex_free)
    spec = _resolve_1d(_event_block(height), f9_vehicle)
    with pytest.raises(ValueError, match="never reaches its ignition altitude"):
        _fly_1d(f9_vehicle, spec, tight_settings, ConstantGravity(g_true))


def test_one_d_failed_stage_flags_the_event_height_as_ignored(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """fails: true with a height-event ramp start: a failed-ignition run as today (the
    ignition_failed event at release, status impact), the height flagged as ignored by
    its key and value, no ignition or ignition_height event, no ramp-start line."""
    spec = _resolve_1d({**_event_block(40.0), "fails": True}, f9_vehicle)
    assert spec.fails and spec.lights_at_height
    result = _fly_1d(
        f9_vehicle, spec, tight_settings, InverseSquareGravity(MU_EARTH_M3S2), end="impact"
    )
    assert result.status == "impact" and result.metrics["failed_stage"] == "stage1"
    flags = [f for f in result.flags if f.startswith("ignition_failed")]
    assert flags == [
        "ignition_failed: stage 'stage1' has fails: true, so nothing burns; ignored: "
        "at_height_m = 40"
    ]
    names = set(result.events["event"])
    assert "ignition_failed" in names
    assert not {"ignition", IGNITION_HEIGHT_EVENT} & names
    assert not [line for line in result.assumptions if line.startswith("ramp start")]


def test_a_start_within_the_tolerance_lights_at_once(
    f9_vehicle: Vehicle, gate_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """A height below the event tolerance (1e-7 m < ATOL_M) is reached at the release
    itself: both planners light stage 1 there, deciding it themselves (no
    COAST_PRE_IGN phase, no ignition_height event, no run flag)."""
    h = 1e-7
    result = _fly_1d(
        f9_vehicle,
        _resolve_1d(_event_block(h), f9_vehicle),
        tight_settings,
        InverseSquareGravity(MU_EARTH_M3S2),
    )
    row = _rows(result, "ignition").iloc[0]
    assert float(row["t_s"]) == result.metrics["t_release_s"]
    assert "COAST_PRE_IGN" not in set(result.timeseries["phase"])
    assert IGNITION_HEIGHT_EVENT not in set(result.events["event"])
    assert result.flags == []
    planner, assist, track = _silo_planner(gate_vehicle, _event_block(h))
    trace = planner.run(math.radians(KICK_DEG), assist, track)
    ign = trace.first_event("ignition")
    assert ign is not None and ign.t_s == trace.t_release_s
    assert COAST_PRE_IGN not in {p.spec.kind for p in trace.phases}
    assert trace.first_event(IGNITION_HEIGHT_EVENT) is None and trace.flags == ()


def test_one_d_coast_events_are_unchanged_by_the_default_extra(
    f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """VerticalPlanner._coast from z = 0 at 80 m/s to the ground: at the default extra
    (and with extra=() given) the rising phase lists (apex,) and the falling one
    (impact,), as before, with bit-identical samples; an extra event that never fires
    (an altitude above the apex) is listed in the rising phase only and leaves the
    samples bit-identical."""
    specs = {name: IgnitionSpec() for name in f9_vehicle.stage_names}
    planner = VerticalPlanner(
        f9_vehicle, specs, InverseSquareGravity(MU_EARTH_M3S2), G_EFF_1D, "impact", tight_settings
    )
    y0 = VERTICAL_LAYOUT.build(v_mps=80.0, m_kg=1.0e5)
    kinds = ("COAST", "FALL")

    def coast(**kw: Any) -> list[Any]:
        tr = planner.new_builder()
        planner._coast(tr, kinds, 0, 0.0, None, y0, None, **kw)
        return tr.phases

    default = coast()
    assert [tuple(e.name for e in p.spec.events) for p in default] == [("apex",), ("impact",)]
    high = ev_altitude_up(VerticalDynamics1D(), 1.0e4, IGNITION_HEIGHT_EVENT)
    for other, listed in (
        (coast(extra=()), [("apex",), ("impact",)]),
        (coast(extra=(high,)), [("apex", IGNITION_HEIGHT_EVENT), ("impact",)]),
    ):
        assert [tuple(e.name for e in p.spec.events) for p in other] == listed
        for a, b in zip(default, other, strict=True):
            assert np.array_equal(a.t, b.t) and np.array_equal(a.y, b.y)
            assert a.ended_by == b.ended_by


# ------------------------------------------------------------------------ planar


@pytest.fixture(scope="module")
def gate_vehicle(repo_root: Path) -> Vehicle:
    """The gate fork generic_f9_class_2d.yaml at its file payload."""
    path = repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml"
    return VehicleConfig.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    ).to_vehicle()


def _silo_planner(
    vehicle: Vehicle,
    block: dict[str, Any],
    end: str = "stage1_burnout",
    *,
    guidance: GuidanceSpec = SILO_GUIDANCE,
) -> tuple[PlanarPlanner, Any, Any]:
    """The planar planner of the gate fork at 28.5 deg (mu/r^2, ICAO, the vehicle's drag)
    with stage 1's IgnitionSpec resolved from block on the 3 g0, 100 m silo (with the
    site's g_ref, as both spec build sites do), and the silo's assist and track."""
    env = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), OMEGA_P, ambient_scalar)
    cfg = ConstantAccelConfig(
        model="constant_accel", net_accel_g=3.0, stroke_m=L, brake_decel_g=5.0, drive_efficiency=0.5
    )
    assist, track = build_assist(cfg, env.g_ref_mps2)
    spec = resolve_ignition(
        IgnitionConfig.model_validate(block), vehicle.stages[0].startup, assist, track, G_REF
    )
    planner = PlanarPlanner(
        vehicle, {"stage1": spec, "stage2": IgnitionSpec(0.0)}, guidance, env, end, SETTINGS
    )
    return planner, assist, track


@pytest.mark.parametrize("height", [5.0, 40.0, 200.0, 280.0])
def test_planar_event_lies_at_the_requested_height(height: float, gate_vehicle: Vehicle) -> None:
    """On the planar gate fork with drag, mu/r^2 and rotation the flight starts with a
    pending ignition (no time, the altitude z_mouth + h = h, stage1_lights) after an
    unlit push (no ignition on the track, no ignition_failed); stage 1 lights at the
    event root, alt = h within the event tolerance, at the time of the ignition_height
    record, which becomes its ignition time (tr.t_ign_abs_s); no flag; the thrust
    schedule counts from that root: stage 1's ramp ends t_ramp after it (1e-12 s). The
    closed-form time of the same h lies elsewhere (the flown coast is not the drag-free
    one)."""
    planner, assist, track = _silo_planner(gate_vehicle, _event_block(height))
    start = planner.start(assist, track)
    assert start.t_ign1_s is None and start.stage1_lights
    assert start.ign1_alt_m == pytest.approx(0.0 + height, abs=1e-12)
    assert start.prefix.first_event("ignition") is None
    assert "stage1" not in start.prefix.t_ign_abs_s
    trace = planner.run(math.radians(KICK_DEG), assist, track)
    ign, root = trace.first_event("ignition"), trace.first_event(IGNITION_HEIGHT_EVENT)
    assert ign is not None and root is not None
    assert ign.phase not in ("HOLD", ASSIST_KIND) and root.phase == COAST_PRE_IGN
    assert abs(ign.value("alt_m") - height) < EVENT_TOL_M
    assert ign.t_s == root.t_s and trace.t_ign_abs_s["stage1"] == ign.t_s
    assert trace.status == "nominal" and trace.flags == () and trace.failed_stage is None
    assert trace.first_event("ignition_failed") is None
    ramp = trace.first_event("ramp_end")
    assert ramp is not None and ramp.phase not in ("HOLD", ASSIST_KIND)
    assert abs((ramp.t_s - ign.t_s) - gate_vehicle.stages[0].startup.t_ramp_s) < SCHEDULE_ABS_S
    dt_closed = _height_dt(height, G_REF)
    assert abs((ign.t_s - trace.t_release_s) - dt_closed) > 1e-9


def test_planar_kick_deadline_counts_from_the_event_root(gate_vehicle: Vehicle) -> None:
    """The kick deadline of a stage lit at a height counts from the event root, its
    ignition time, as for a time-lit stage
    (``test_planar_events.py::test_kick_deadline_counts_from_ignition``): at h = 200 m
    the vehicle is below v_k at the root, so a vertical rise precedes the trigger at t_k
    (about 5.35 s after the root, which lies about 3.30 s after the release). The
    rise's thrust schedule is lit at the root. A deadline 0.25 s longer than t_k -
    t_root lets the kick start at t_k; one 0.75 s shorter raises no_kick. A deadline
    counted from the release, or from any time more than 0.25 s before the root, would
    fail the first; one counted from more than 0.75 s after the root would fail the
    second."""
    planner, assist, track = _silo_planner(gate_vehicle, _event_block(200.0))
    kick = planner.to_kick(planner.start(assist, track))
    root = kick.prefix.first_event(IGNITION_HEIGHT_EVENT)
    assert root is not None and kick.kicked
    t_k, t_root = kick.t_s, root.t_s
    assert kick.schedule.t_ign_abs_s == t_root and not kick.schedule.fails
    assert kick.prefix.t_ign_abs_s["stage1"] == t_root
    assert t_root - kick.prefix.t_release_s > 1.0
    late = GuidanceSpec(V_KICK_MPS, 60.0, t_k - t_root + 0.25)
    p, a, t = _silo_planner(gate_vehicle, _event_block(200.0), guidance=late)
    assert p.to_kick(p.start(a, t)).t_s == t_k
    early = GuidanceSpec(V_KICK_MPS, 60.0, t_k - t_root - 0.75)
    p, a, t = _silo_planner(gate_vehicle, _event_block(200.0), guidance=early)
    with pytest.raises(GuidanceFailure) as info:
        p.to_kick(p.start(a, t))
    assert info.value.kind == "no_kick"


def test_planar_failed_stage_flags_the_event_height_as_ignored(gate_vehicle: Vehicle) -> None:
    """fails: true with a height-event ramp start on the planar model: the flight starts
    with no ignition time and no ignition altitude (a failed ignition, stage1_lights
    False), the run is the failed-ignition coast to the ground (status impact), the
    height is flagged as ignored, and no altitude event is listed or logged."""
    planner, assist, track = _silo_planner(
        gate_vehicle, {**_event_block(40.0), "fails": True}, end="impact"
    )
    start = planner.start(assist, track)
    assert start.t_ign1_s is None and start.ign1_alt_m is None and not start.stage1_lights
    trace = planner.run(None, assist, track)
    assert trace.status == "impact" and trace.failed_stage == "stage1"
    assert [f for f in trace.flags if f.startswith("ignition_failed")] == [
        "ignition_failed: stage 'stage1' has fails: true, so nothing burns; ignored: "
        "at_height_m = 40"
    ]
    assert trace.first_event(IGNITION_HEIGHT_EVENT) is None
    assert trace.first_event("ignition") is None
    assert all(IGNITION_HEIGHT_EVENT not in {e.name for e in p.spec.events} for p in trace.phases)


def test_flight_start_tells_a_pending_ignition_from_a_failed_one(gate_vehicle: Vehicle) -> None:
    """FlightStart: a time, or an altitude (pending), lights; neither is a failed
    ignition; both at once is refused."""
    prefix = gate_vehicle_trace(gate_vehicle)
    assert FlightStart(prefix, "nominal", 0.0, None, 1.0).stage1_lights
    assert FlightStart(prefix, "nominal", 0.0, None, None, ign1_alt_m=40.0).stage1_lights
    assert not FlightStart(prefix, "nominal", 0.0, None, None).stage1_lights
    with pytest.raises(ValueError, match="not both"):
        FlightStart(prefix, "nominal", 0.0, None, 1.0, ign1_alt_m=40.0)


def gate_vehicle_trace(vehicle: Vehicle) -> Any:
    """An empty planar RunTrace of the vehicle (the prefix a FlightStart carries)."""
    planner, _assist, _track = _silo_planner(vehicle, {})
    return planner.new_builder().finish()


def _coast_apex_with_drag(vehicle: Vehicle) -> float:
    """The apex altitude [m] of the unlit coast after release on the planar gate fork
    (drag, mu/r^2, rotation): a failed ignition's run to apex."""
    planner, assist, track = _silo_planner(vehicle, {"fails": True}, end="apex")
    trace = planner.run(None, assist, track)
    apex = trace.first_event("apex")
    assert apex is not None
    return apex.value("alt_m")


def test_planar_apex_below_the_height_is_no_ignition(gate_vehicle: Vehicle) -> None:
    """A height between the apex of the flown coast (with drag, measured here) and the
    drag-free apex V_E^2 / (2 g_ref) resolves (the resolver checks the drag-free one)
    but never lights: to_kick and run raise GuidanceFailure("no_ignition"), a kind of
    GUIDANCE_FAILURE_KINDS."""
    apex_drag = _coast_apex_with_drag(gate_vehicle)
    apex_free = V_E * V_E / (2.0 * G_REF)
    assert apex_drag < apex_free
    height = 0.5 * (apex_drag + apex_free)
    planner, assist, track = _silo_planner(gate_vehicle, _event_block(height))
    assert "no_ignition" in GUIDANCE_FAILURE_KINDS
    start = planner.start(assist, track)
    with pytest.raises(GuidanceFailure) as info:
        planner.to_kick(start)
    assert info.value.kind == "no_ignition"
    with pytest.raises(GuidanceFailure, match="no_ignition"):
        planner.run(math.radians(KICK_DEG), assist, track)


@pytest.mark.parametrize("below_apex_m", [0.5, 1e-2, 1e-4])
def test_planar_event_just_below_the_flown_apex_lights(
    below_apex_m: float, gate_vehicle: Vehicle
) -> None:
    """A height d below the apex of the flown coast (measured here) lights there, within
    the event tolerance and before any apex, although the crossing lies within
    sqrt(2 d / g) of the apex. (On the gate fork the planar steps shrink near the apex,
    where the drag direction turns as |v_rel| goes to 0, so the fold of ev_altitude_up
    is a guard here; the uncapped 1-D coast needs it, see the engine test above. The
    ramp then starts from almost no speed, so the lit rise passes an apex of its own,
    later.)"""
    height = _coast_apex_with_drag(gate_vehicle) - below_apex_m
    planner, assist, track = _silo_planner(gate_vehicle, _event_block(height))
    trace = planner.run(math.radians(KICK_DEG), assist, track)
    ign = trace.first_event("ignition")
    assert ign is not None and abs(ign.value("alt_m") - height) < EVENT_TOL_M
    assert all(e.t_s > ign.t_s for e in trace.events if e.name == "apex")
    assert ign.phase == "VERTICAL_RISE"


def test_planar_coast_events_are_unchanged_by_the_default_extra(gate_vehicle: Vehicle) -> None:
    """PlanarPlanner._coast from a silo release to the ground: at the default extra (and
    with extra=() given) the rising sub-phase lists (apex,) and the falling one
    (impact,), as before, with bit-identical samples; an extra event that never fires
    is listed in the rising sub-phase only and leaves the samples bit-identical."""
    planner, assist, track = _silo_planner(gate_vehicle, {"t_ign_s": 0.5})
    start = planner.start(assist, track)
    assert start.t_fs_s is not None and start.y_fs is not None

    def coast(**kw: Any) -> list[Any]:
        tr = resume_builder(start.prefix, gate_vehicle.stage_names)
        n0 = len(tr.phases)
        planner._coast(tr, COAST_PRE_IGN, 0, start.t_fs_s, None, start.y_fs, hint=True, **kw)
        return tr.phases[n0:]

    default = coast()
    assert [tuple(e.name for e in p.spec.events) for p in default] == [("apex",), ("impact",)]
    high = ev_altitude_up(planner.model, 1.0e4, IGNITION_HEIGHT_EVENT)
    for other, listed in (
        (coast(extra=()), [("apex",), ("impact",)]),
        (coast(extra=(high,)), [("apex", IGNITION_HEIGHT_EVENT), ("impact",)]),
    ):
        assert [tuple(e.name for e in p.spec.events) for p in other] == listed
        for a, b in zip(default, other, strict=True):
            assert np.array_equal(a.t, b.t) and np.array_equal(a.y, b.y)
            assert a.ended_by == b.ended_by


def test_a_height_event_spec_has_no_time_and_needs_a_push(gate_vehicle: Vehicle) -> None:
    """IgnitionSpec of height_event: lights_at_height, t_ign_s and reference at their
    defaults (others refused), no ignition time (t_ign_abs_s refuses it); a pad run
    refuses it on both planners, and RunConfig refuses the block on a pad."""
    spec = IgnitionSpec(trigger_kind="height_event", trigger_value=40.0)
    assert spec.lights_at_height and not IgnitionSpec().lights_at_height
    with pytest.raises(ValueError, match="no ignition time"):
        spec.t_ign_abs_s(2.6)
    with pytest.raises(ValueError, match="not at a time"):
        IgnitionSpec(0.5, trigger_kind="height_event", trigger_value=40.0)
    with pytest.raises(ValueError, match="not at a time"):
        IgnitionSpec(reference="push_start", trigger_kind="height_event", trigger_value=40.0)
    env = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), OMEGA_P, ambient_scalar)
    specs = {"stage1": spec, "stage2": IgnitionSpec(0.0)}
    pad = PlanarPlanner(gate_vehicle, specs, SILO_GUIDANCE, env, "stage1_burnout", SETTINGS)
    with pytest.raises(ValueError, match="no track exit"):
        pad.start()
    vertical = VerticalPlanner(
        gate_vehicle,
        specs,
        InverseSquareGravity(MU_EARTH_M3S2),
        G_EFF_1D,
        "stage1_burnout",
        SETTINGS,
    )
    with pytest.raises(ValueError, match="no track exit"):
        vertical.run_pad()
    with pytest.raises(ValueError, match="needs an assist model"):
        RunConfig.model_validate({"name": "pad", "ignition": {"stage1": _event_block(40.0)}})


# ---------------------------------------------------------------- pipeline (planar)


def _raw(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """silo_screening_2d.yaml and the gate fork as raw dicts."""
    exp = yaml.safe_load(
        (repo_root / "experiments" / "silo_screening_2d.yaml").read_text(encoding="utf-8")
    )
    veh = yaml.safe_load(
        (repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml").read_text(
            encoding="utf-8"
        )
    )
    return exp, veh


def _experiment(
    repo_root: Path, variants: dict[str, dict[str, Any]], *, fixed: bool
) -> dict[str, Any]:
    """silo_screening_2d with the given variants on the shipped silo (merged onto its
    silo_cold assist block), no sweeps, sensitivity or bounds; with fixed, the fixed
    guidance of tests/test_planar_pipeline.py (figure_of_merit none)."""
    exp, _veh = _raw(repo_root)
    exp = copy.deepcopy(exp)
    silo = exp["variants"]["silo_cold"]["assist"]
    exp["variants"] = {name: {"assist": silo, **v} for name, v in variants.items()}
    for key in ("sweeps", "sensitivity", "bounds"):
        exp.pop(key, None)
    if fixed:
        exp["search"].update(
            {
                "figure_of_merit": "none",
                "fixed_gamma_star_deg": FIXED_GAMMA_DEG,
                "fixed_ltg_a": FIXED_LTG[0],
                "fixed_ltg_b_per_s": FIXED_LTG[1],
            }
        )
    return exp


def _no_ignition_height(gate_vehicle: Vehicle) -> float:
    """A height [m] between the flown coast's apex and the drag-free apex (gate fork)."""
    return 0.5 * (_coast_apex_with_drag(gate_vehicle) + V_E * V_E / (2.0 * G_REF))


@pytest.fixture(scope="module")
def fixed_runs(repo_root: Path, gate_vehicle: Vehicle) -> dict[str, Any]:
    """Fixed-guidance runs to stage-1 burnout through sim.run_resolved: ``event40``
    (at_height_m 40 by event), ``closed40`` (at_height_m 40 by the closed form) and
    ``no_ignition`` (a height in the band between the two apexes)."""
    _exp, veh = _raw(repo_root)
    end = "stage1_burnout"
    closed = {"at_height_m": 40.0, "height_method": "closed_form"}
    variants = {
        "event40": {"ignition": {"stage1": _event_block(40.0)}, "end": end},
        "closed40": {"ignition": {"stage1": closed}, "end": end},
        "no_ignition": {
            "ignition": {"stage1": _event_block(_no_ignition_height(gate_vehicle))},
            "end": end,
        },
    }
    resolved = resolve_experiment(_experiment(repo_root, variants, fixed=True), veh)
    return {name: sim.run_resolved(run) for name, run in resolved.variants.items()}


def test_planar_ramp_start_metrics_of_a_height_event(fixed_runs: dict[str, Any]) -> None:
    """The planar ramp-start metrics of the event run: trigger height_event, requested
    height 40, no converted time (requested_t_s None), the other requested keys None;
    achieved after release (not on the track) at height 40 above the mouth within the
    event tolerance, at the run's stage-1 ignition time; the run is nominal, not failed,
    and states the event in its assumptions."""
    result = fixed_runs["event40"].result
    m = result.metrics
    assert m["ramp_start_trigger"] == "height_event"
    assert m["ramp_start_requested_height_m"] == 40.0
    assert m["ramp_start_requested_t_s"] is None
    assert m["ramp_start_requested_depth_m"] is None
    assert m["ramp_start_requested_speed_mps"] is None
    assert abs(m["ramp_start_height_m"] - 40.0) < EVENT_TOL_M
    assert m["ramp_start_depth_m"] is None
    assert m["ramp_start_phase"] not in ("HOLD", ASSIST_KIND)
    assert m["ramp_start_t_rel_release_s"] == m["t_ign_rel_release_s_stage1"]
    assert result.status == "nominal" and "failed_stage" not in m
    assert [line for line in result.assumptions if "reached by an altitude event" in line]


def _table_cells(lines: list[str], label: str) -> list[str]:
    """The value cells of the summary table row whose first cell is ``label``."""
    row = next(ln for ln in lines if ln.startswith(f"| {label} |"))
    return [cell.strip() for cell in row.strip().strip("|").split("|")][1:]


def test_ramp_start_rows_of_a_height_event_run(fixed_runs: dict[str, Any]) -> None:
    """The planar summary table of the closed-form run (baseline column) and the event
    run, both at 40 m: summary.RAMP_START_ROWS come right after the stage-1 ignition
    rows (the step-3 gating: some run states a trigger); the trigger row reads
    height_closed_form and height_event, the requested height 40 in both columns; the
    converted t_ign row reads the closed form (v_e - sqrt(v_e^2 - 2 g_ref h)) / g_ref
    (computed here, to the table's 6 digits) for the closed-form run and n/a for the
    event run (nothing is converted); the achieved height reads 40 for the event run
    (its root, to 6 digits) and not 40 for the closed-form run (the flown coast is not
    the drag-free one), lit after release in both."""
    er = ExperimentResult(
        experiment_name="height_event",
        vehicle_name="generic_f9_class_2d",
        baseline=fixed_runs["closed40"],
        variants={"event40": fixed_runs["event40"]},
        comparison={},
        git={},
        timestamp_utc="t",
        model=PLANAR_2D,
    )
    rows = summary.planar_variant_rows(er)
    last_ignition = rows.index(summary.ignition_rows(summary.first_stage_name(er))[-1])
    block = rows[last_ignition + 1 : last_ignition + 1 + len(summary.RAMP_START_ROWS)]
    assert block == summary.RAMP_START_ROWS
    table = summary.planar_variants_table(er).splitlines()
    by_key = {key: label for label, _source, key in summary.RAMP_START_ROWS[1:]}
    labels = [label for label, _source, _key in summary.RAMP_START_ROWS]
    assert _table_cells(table, labels[0]) == ["height_closed_form", "height_event"]
    assert _table_cells(table, by_key["ramp_start_requested_height_m"]) == ["40", "40"]
    assert _table_cells(table, by_key["ramp_start_requested_depth_m"]) == ["n/a", "n/a"]
    converted = _table_cells(table, by_key["ramp_start_requested_t_s"])
    assert converted == [f"{_height_dt(40.0, G_REF):.6g}", "n/a"]
    closed_h, event_h = _table_cells(table, by_key["ramp_start_height_m"])
    assert event_h == "40" and closed_h != "40"
    phases = _table_cells(table, by_key["ramp_start_phase"])
    assert not {"HOLD", ASSIST_KIND} & set(phases)


def test_a_fixed_guidance_run_that_never_lights_is_guidance_failed(
    fixed_runs: dict[str, Any],
) -> None:
    """A fixed-guidance run whose coast peaks below its event height: status
    guidance_failed with guidance_failure_kind no_ignition, not a crash and not a
    failed ignition."""
    result = fixed_runs["no_ignition"].result
    assert result.status == "guidance_failed"
    assert result.metrics["guidance_failure_kind"] == "no_ignition"
    assert "failed_stage" not in result.metrics


def test_a_searched_run_that_never_lights_is_search_failed(
    repo_root: Path, gate_vehicle: Vehicle
) -> None:
    """A searched run whose coast peaks below its event height at the vehicle's payload:
    every gamma* grid point fails with no_ignition, so the search fails (status
    search_failed, kind grid) and names no_ignition."""
    _exp, veh = _raw(repo_root)
    block = _event_block(_no_ignition_height(gate_vehicle))
    variants = {"no_ignition": {"ignition": {"stage1": block}}}
    resolved = resolve_experiment(_experiment(repo_root, variants, fixed=False), veh)
    result = sim.run_resolved(resolved.variants["no_ignition"]).result
    assert result.status == "search_failed"
    assert result.metrics["search_failure_kind"] == "grid"
    assert "no_ignition" in result.metrics["search_failure_message"]


def test_the_preflight_refuses_a_height_at_the_drag_free_apex_for_both_methods(
    repo_root: Path,
) -> None:
    """sim.check_resolved (before any results directory) refuses a height at or above
    the drag-free apex V_E^2 / (2 g_ref) of the planar silo by either method, naming the
    run; just below it both resolve."""
    _exp, veh = _raw(repo_root)
    apex = V_E * V_E / (2.0 * G_REF)
    for method in ("event", "closed_form"):
        for height, refused in ((apex, True), (1.001 * apex, True), (0.999 * apex, False)):
            block = {"at_height_m": height, "height_method": method}
            exp = _experiment(repo_root, {"high": {"ignition": {"stage1": block}}}, fixed=True)
            resolved = resolve_experiment(exp, veh)
            if refused:
                with pytest.raises(ValueError, match=r"run 'high'.*drag-free apex"):
                    sim.check_resolved(resolved)
            else:
                sim.check_resolved(resolved)


@pytest.mark.slow
def test_a_searched_run_with_a_height_event_ramp_start_completes(repo_root: Path) -> None:
    """A searched planar run (the shipped payload search and budget) whose stage 1
    lights at the 40 m altitude event: the search succeeds and the recorded run inserts
    with its per-run checks passing; its stage 1 lit at 40 m above the mouth (event
    tolerance) after release."""
    _exp, veh = _raw(repo_root)
    variants = {"event40": {"ignition": {"stage1": _event_block(40.0)}}}
    resolved = resolve_experiment(_experiment(repo_root, variants, fixed=False), veh)
    result = sim.run_resolved(resolved.variants["event40"]).result
    m = result.metrics
    assert result.status == "inserted", (result.status, result.flags)
    assert m["payload_kg"] is not None and m["payload_kg"] > 0.0
    assert m["run_checks"] == "ok"
    assert m["ramp_start_trigger"] == "height_event"
    assert abs(m["ramp_start_height_m"] - 40.0) < EVENT_TOL_M
