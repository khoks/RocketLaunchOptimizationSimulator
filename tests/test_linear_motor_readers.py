"""The readers of a linear-motor run (SP7 step S4a; docs/physics.md, "Linear motor: the
flown power cap, the release at a target speed and the readers (SP7 step S4a)",
paragraph "The readers"): no single push acceleration is claimed for a drive that does
not hold one, a plateau the drive does hold is not denied (fix round 1: the acceleration
law's command after its rise when no cap bound), a mean is named a mean, and a release
before the mouth is stated.

- replay.py: ``push_accel_g`` is None for any drive but the prescribed one (even with a
  stray net_accel_g metric or key); ``linear_motor_settings`` reads the metrics of KI-052
  (and push_cap_bound) first and the config block as the fallback; ``release_text``,
  ``linear_motor_law_text`` and ``linear_motor_clause`` name the law, F_max and P_max,
  the acceleration law's command, the measured speed at release and the release (at the
  track end, on reaching the release speed some metres below the mouth, or at the track
  end with the release speed not reached); ``motor_acceleration_text`` by law and cap;
  ``assist_text``, ``drive_caveat`` and ``closeup_notes`` on hand-built metrics, configs
  and records (a prescribed run beside force-law and acceleration-law runs, a release
  below the mouth with its mouth crossing, a fall back onto the parked carriage or at the
  apex, worded from the run's shaft_fallback flag (fix round 4), through the open mouth
  from an apex above it, a turnaround above the parked carriage, and a vehicle that leaves
  the shaft before its kick; the stop taper named; the omissions of a stall, of grouped
  runs and of a massless force-law carriage);
- scene.py: ``assist_settings`` derives no a = v^2/(2 L) for a linear-motor run and adds
  its ``drive`` (payload data: the frozen template draws no push label); a constant_accel
  run's settings keep their keys and derivations; ``early_release_caveat`` and the frame
  caveat of a release below the mouth (the drawn carriage brakes from the mouth), of a
  fall back inside the shaft (the drawn impact note, both its claims) and of a push that
  never released; the display-only list's carriage item for a fall back (fix round 4);
- summary.py: LINEAR_MOTOR_ROWS in the 1-D and planar per-variant tables only when a
  linear-motor run is in the table, '-' in another run's column, "none" for an unset push
  setting, labels that name a mean a mean and claim no held value the push does not hold;
- plots.py: the force-against-speed figure written for a linear-motor run only, with its
  limit lines, corner, power cap and release speed (not reached, or set with no release)
  marked; no push load for a push that never moved;
- on a real fixed-guidance planar directory written in a temporary folder (slow: about
  12 s with its fixture): the replay and scene pages, summary.md's rows, the drive-curve
  PNGs and the app's run browser row and results panel, with a failed ignition that falls
  back inside the shaft onto its parked carriage (fix round 3) and a stalled push (fix
  round 4).

Nothing here reads or writes results/.
"""

from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml
from matplotlib.backends.backend_agg import FigureCanvasAgg

from launchsim import app, plots, replay, scene, sim, summary
from launchsim.assist.constant_accel import ConstantAccelAssist
from launchsim.assist.linear_motor import LinearMotorAssist
from launchsim.assist.track import VERTICAL, StraightTrack
from launchsim.config import LinearMotorConfig, resolve_experiment
from launchsim.constants import G0_MPS2, MU_EARTH_M3S2, R_EARTH_M
from launchsim.dynamics import InverseSquareGravity
from launchsim.metrics import LINEAR_MOTOR_METRICS
from launchsim.phases import IgnitionSpec, IntegratorSettings
from launchsim.phases.prelude import RELEASE_SPEED_NOT_REACHED, SHAFT_FALLBACK
from launchsim.vehicle import Vehicle

REPO = Path(__file__).resolve().parents[1]
DISPLAY_DIR = REPO / "configs" / "display"
G = MU_EARTH_M3S2 / R_EARTH_M**2
L = 100.0
LM_CONFIG: dict[str, Any] = {
    "model": "linear_motor",
    "stroke_m": 100,
    "control": "force",
    "force_max_kN": 22430,
    "power_max_MW": 1300,
    "force_rise_time_s": 0.5,
    "carriage_mass_t": 22,
    "brake_decel_g": 5,
    "track": {"angle_deg": 90, "exit_altitude_m": 0},
}
"""A linear-motor block as resolved_config.yaml holds it (no shaft key: vented)."""
LM_METRICS: dict[str, Any] = {
    "push_control_law": "force",
    "push_force_max_N": 22.43e6,
    "push_power_max_W": 1.3e9,
    "push_rise_time_s": 0.5,
    "push_corner_speed_mps": 1.3e9 / 22.43e6,
    "push_accel_command_mps2": None,
    "push_stop_taper_m": None,
    "push_release_speed_mps": None,
    "push_power_limited": True,
    "push_cap_bound": None,
    "push_accel_mean_mps2": 24.86,
    "release_position_m": 100.0,
    "release_trigger": "track_end",
    "exit_speed_mps": 72.54,
    "stroke_m": 100.0,
    "net_accel_mps2": None,
    "net_accel_g": None,
    "push_time_s": 2.918,
    "carriage_mass_kg": 22000.0,
    "braking_distance_m": 53.65,
    "facility_length_m": 153.65,
    "track_start_altitude_m": -100.0,
    "flags": [],
}
"""A linear-motor run's metrics (released at the track end)."""
TARGET_METRICS: dict[str, Any] = {
    **LM_METRICS,
    "push_release_speed_mps": 60.0,
    "release_position_m": 64.28,
    "release_trigger": "target_speed",
    "exit_speed_mps": 60.0,
    "push_time_s": 2.381,
    "braking_distance_m": 36.71,
    "facility_length_m": 100.99,
}
"""The same drive released at its release speed, 35.72 m below the mouth."""
CMD_CONFIG: dict[str, Any] = {
    **LM_CONFIG,
    "control": "acceleration",
    "accel_command_g": 3.0,
    "force_max_kN": 25000,
    "power_max_MW": 2000,
    "carriage_mass_t": 0,
    "release_speed_mps": 90,
}
"""An acceleration-law block (3 g0, F_max 25 MN, P_max 2000 MW), massless carriage."""
CMD_METRICS: dict[str, Any] = {
    **LM_METRICS,
    "push_control_law": "acceleration",
    "push_force_max_N": 25e6,
    "push_power_max_W": 2e9,
    "push_corner_speed_mps": 80.0,
    "push_accel_command_mps2": 3.0 * G0_MPS2,
    "push_release_speed_mps": 90.0,
    "push_power_limited": False,
    "push_cap_bound": False,
    "exit_speed_mps": 76.59,
    "carriage_mass_kg": 0.0,
    "flags": [
        f"{RELEASE_SPEED_NOT_REACHED}: the push reached 76.5895 m/s at the track end (s = L "
        "= 100 m), below the release speed 90 m/s; it released at the track end"
    ],
}
"""The acceleration law released at the track end, its 90 m/s not reached, no cap bound
(the gate's lm_cmd_unreached)."""
CLAUSE = "a linear motor (force law, F_max 22.43 MN, P_max 1300 MW)"
CMD_CLAUSE = (
    "a linear motor (acceleration law: a_cmd 3 g0 net after a 0.5 s rise, F_max 25 MN, "
    "P_max 2000 MW)"
)
FORCE_ACCEL = (
    "its acceleration is not prescribed: it follows from the force and power limits, the "
    "mass and the thrust, so no single push acceleration is quoted"
)
CAPPED_ACCEL = (
    "a cap (F_max or P_max / sdot) bound on this push, where its acceleration followed from "
    "the capped force; it flies its command, 3 g0 net after its rise, only where no cap "
    "binds, so no single push acceleration is quoted"
)
"""The acceleration law with a cap bound (fix round 2: push_cap_bound carries no timing,
so neither 'from the end of its rise' nor an order is claimed)."""


# ------------------------------------------------------------------- replay text


def test_no_acceleration_is_claimed_for_a_linear_motor_push() -> None:
    """``push_accel_g`` reads the prescribed drive's metric (then its config key, a block
    without a model key being read as one), and gives None for the linear motor even
    with a stray net_accel_g metric or key; ``linear_motor_settings`` takes the metrics
    first (KI-052 and push_cap_bound) and the config block as the fallback (kN, MW and g0
    through units.py), an unset setting's metric (None) read as such."""
    ca = {"model": "constant_accel", "net_accel_g": 3.0}
    assert replay.push_accel_g(ca, {"net_accel_g": 2.5}) == 2.5
    assert replay.push_accel_g(ca, {}) == 3.0
    assert replay.push_accel_g({"net_accel_g": 3.0}, {}) == 3.0
    stray = {**LM_CONFIG, "net_accel_g": 3.0}
    assert replay.push_accel_g(stray, {**LM_METRICS, "net_accel_g": 3.1}) is None
    assert replay.linear_motor_settings(LM_CONFIG, LM_METRICS) == {
        "control": "force",
        "force_max_N": 22.43e6,
        "power_max_W": 1.3e9,
        "rise_time_s": 0.5,
        "accel_command_mps2": None,
        "stop_taper_m": None,
        "release_speed_mps": None,
        "cap_bound": None,
    }
    assert replay.linear_motor_settings(CMD_CONFIG, CMD_METRICS)["cap_bound"] is False
    old = {"exit_speed_mps": 72.54}  # a directory written before KI-052's keys
    cfg = {**CMD_CONFIG, "release_speed_mps": 60, "stop_taper_m": 0}
    assert replay.linear_motor_settings(cfg, old) == {
        "control": "acceleration",
        "force_max_N": 25000 * 1000.0,
        "power_max_W": 2000 * 1.0e6,
        "rise_time_s": 0.5,
        "accel_command_mps2": 3.0 * G0_MPS2,
        "stop_taper_m": 0.0,
        "release_speed_mps": 60.0,
        "cap_bound": None,
    }


def test_the_release_and_the_drive_in_words() -> None:
    """``release_text``: at the track end with the measured exit speed; on reaching the
    release speed, the measured speed and the distance below the mouth (stroke - release
    position) or before the track end; the release speed not reached (the run's flag);
    None without a release. ``linear_motor_clause``: the law and limits (the acceleration
    law's command as a command) and the release; ``motor_acceleration_text`` by law and
    cap (the force law's not prescribed, the acceleration law's command held when no cap
    bound, a cap that bound worded without a timing, flown wherever none binds when
    unrecorded); a stop taper named in both forms of ``linear_motor_law_text``, among
    what the force law's acceleration follows from, and as scaling the command where it is
    flown (fix round 3, H3-m3); ``assist_text``: the
    geometry, the short law, the carriage and the speed at release said to be measured
    (an early release 'released at ... below the mouth'). None of them states a push
    acceleration."""
    assert replay.release_text(LM_METRICS) == (
        "released at the track end at a measured exit speed of 72.5 m/s"
    )
    assert replay.release_text(TARGET_METRICS, 60.0, mouth=True) == (
        "released on reaching its release speed, 60.0 m/s measured, 35.7 m below the mouth"
    )
    assert replay.release_text(TARGET_METRICS, 60.0) == (
        "released on reaching its release speed, 60.0 m/s measured, 35.7 m before the track end"
    )
    assert replay.release_text(CMD_METRICS, 90.0) == (
        "released at the track end at a measured exit speed of 76.6 m/s, its release speed "
        "90 m/s not reached"
    )
    reached = {**CMD_METRICS, "flags": []}  # the speed reached exactly at L: no flag
    assert "not reached" not in str(replay.release_text(reached, 90.0))
    assert replay.release_text({}) is None
    assert replay.linear_motor_clause(LM_CONFIG, LM_METRICS) == (
        f"{CLAUSE}, released at the track end at a measured exit speed of 72.5 m/s"
    )
    assert replay.linear_motor_clause(LM_CONFIG, TARGET_METRICS) == (
        f"{CLAUSE}, released on reaching its release speed, 60.0 m/s measured, 35.7 m below "
        "the mouth"
    )
    assert replay.linear_motor_clause(CMD_CONFIG, CMD_METRICS) == (
        f"{CMD_CLAUSE}, released at the track end at a measured exit speed of 76.6 m/s, its "
        "release speed 90 m/s not reached"
    )
    settings = replay.linear_motor_settings(CMD_CONFIG, CMD_METRICS)
    assert replay.motor_acceleration_text(settings, CMD_METRICS) == (
        "no cap bound, so it held its command, 3 g0 net, from the end of its rise to the release"
    )
    capped = {**settings, "cap_bound": True}
    assert replay.motor_acceleration_text(capped, CMD_METRICS) == CAPPED_ACCEL
    assert replay.motor_acceleration_text({**settings, "cap_bound": None}) == (
        "it flies its command, 3 g0 net after its rise, wherever no cap (F_max or P_max / "
        "sdot) binds, the acceleration following from the capped force where one does, so no "
        "single push acceleration is quoted"
    )
    assert replay.motor_acceleration_text(replay.linear_motor_settings(LM_CONFIG, LM_METRICS)) == (
        FORCE_ACCEL
    )
    # fix round 3 (H3-m3): a stop taper is named
    tapered = {**replay.linear_motor_settings(LM_CONFIG, LM_METRICS), "stop_taper_m": 20.0}
    assert replay.linear_motor_law_text(tapered) == (
        "force law, F_max 22.43 MN, P_max 1300 MW, a 20 m stop taper"
    )
    assert replay.linear_motor_law_text(tapered, short=True) == replay.linear_motor_law_text(
        tapered
    )
    assert replay.motor_acceleration_text(tapered) == (
        "its acceleration is not prescribed: it follows from the force and power limits, the "
        "stop taper, the mass and the thrust, so no single push acceleration is quoted"
    )
    cmd_tapered = {**settings, "stop_taper_m": 10.0}
    assert replay.linear_motor_law_text(cmd_tapered) == (
        "acceleration law: a_cmd 3 g0 net after a 0.5 s rise, F_max 25 MN, P_max 2000 MW, a 10 "
        "m stop taper"
    )
    assert replay.linear_motor_law_text(cmd_tapered, short=True) == (
        "acceleration law, a_cmd 3 g0, F_max 25 MN, P_max 2000 MW, a 10 m stop taper"
    )
    assert replay.motor_acceleration_text({**cmd_tapered, "cap_bound": True}, CMD_METRICS) == (
        CAPPED_ACCEL.replace("after its rise,", "after its rise (scaled down over its stop taper),")
    )
    assert replay.motor_acceleration_text({**cmd_tapered, "cap_bound": None}).startswith(
        "it flies its command, 3 g0 net after its rise (scaled down over its stop taper), "
        "wherever no cap"
    )
    assert replay.assist_text(dict(LM_CONFIG), dict(TARGET_METRICS)) == (
        "vertical silo 100 m deep, linear motor (force law, F_max 22.43 MN, P_max 1300 MW), "
        "22 t carriage, released at 60.0 m/s (measured) 35.7 m below the mouth"
    )
    assert replay.assist_text(dict(CMD_CONFIG), dict(CMD_METRICS)) == (
        "vertical silo 100 m deep, linear motor (acceleration law, a_cmd 3 g0, F_max 25 MN, "
        "P_max 2000 MW), exit 76.6 m/s (measured; its release speed 90 m/s not reached)"
    )
    for text in (
        replay.assist_text(dict(LM_CONFIG), dict(LM_METRICS)),
        replay.linear_motor_clause(LM_CONFIG, TARGET_METRICS),
        replay.linear_motor_clause(CMD_CONFIG, CMD_METRICS),
    ):
        assert not re.search(r"\bg net\b|acceleration of|net acceleration", text), text
    assert replay.is_vented(LM_CONFIG) and not replay.is_vented({"model": "constant_accel"})
    no_track = {k: v for k, v in LM_CONFIG.items() if k != "track"}  # its config default: 90
    assert replay.is_vertical(no_track) and not replay.is_vertical({"model": "constant_accel"})
    assert replay.assist_text(no_track, dict(LM_METRICS)).startswith("vertical silo 100 m deep")


def test_what_the_acceleration_law_did_in_words() -> None:
    """``motor_acceleration_text`` (fix round 2, P2-M1, H2-M1, V2-2) of the acceleration
    law claims a held command only for a push that released after its rise with no cap
    bound: a release by the end of the rise never held it; a stalled push never started
    (status drive_stall; push_cap_bound None); a push that stopped on the track has no
    release (status drive_limit), and the omissions of such a push name no release, while
    those of a stall say it never moved (fix round 3, H3-m4: the missing drag changes
    nothing, a carriage mass would only add to the load the drive could not lift); a cap
    that bound is worded without a timing (it can bind in the rise, or bind and let go); a
    step rise holds it from push start, scaled over a stop taper."""
    settings = replay.linear_motor_settings(CMD_CONFIG, CMD_METRICS)
    early = {**CMD_METRICS, "push_time_s": 0.412, "release_trigger": "target_speed"}
    assert replay.motor_acceleration_text(settings, early) == (
        "no cap bound, and it released by the end of its 0.5 s rise, so it never held its "
        "command, 3 g0 net, and no single push acceleration is quoted"
    )
    at_end = {**CMD_METRICS, "push_time_s": 0.5}  # released as the rise ended
    assert "never held its command" in replay.motor_acceleration_text(settings, at_end)
    stall = {**CMD_METRICS, "status": "drive_stall", "release_trigger": None}
    stalled = replay.motor_acceleration_text({**settings, "cap_bound": None}, stall)
    assert stalled == (
        "the push never started (status drive_stall: the drive at its force limit and the "
        "thrust cannot lift the stack), so it flew no command and no push acceleration is "
        "quoted"
    )
    stopped = {**CMD_METRICS, "status": "drive_limit", "release_trigger": None}
    assert replay.motor_acceleration_text(settings, stopped) == (
        "the push stopped on the track before any release (status drive_limit), so no push "
        "acceleration is quoted"
    )
    step = {**settings, "rise_time_s": 0.0, "stop_taper_m": 10.0}
    assert replay.motor_acceleration_text(step, CMD_METRICS) == (
        "no cap bound, so it held its command, 3 g0 net, from push start to the release "
        "(scaled down over its stop taper)"
    )
    assert "3 g0 net from push start (scaled down over its stop taper), only where" in (
        replay.motor_acceleration_text({**step, "cap_bound": True}, CMD_METRICS)
    )
    for text in (stalled, replay.motor_acceleration_text({**settings, "cap_bound": True})):
        assert "held" not in text and "until a cap" not in text, text
    # and its omissions: no release to change (a stall, a push stopped on the track)
    assert replay._motor_omission(["the missing shaft drag"], settings, stopped, False) == (
        "(acceleration law, no release) the missing shaft drag can change how the push ran on "
        "the track; its size is not established here"
    )
    both = ["the massless carriage", "the missing shaft drag"]
    assert replay._motor_omission(both, settings, stall, False) == (
        "(acceleration law, stalled) the push never moved: the missing shaft drag changes "
        "nothing and a carriage mass would only add to the load the drive could not lift"
    )
    assert replay._motor_omission(both[:1], settings, stall, False, many=True) == (
        "(acceleration law, stalled) the pushes never moved: a carriage mass would only add to "
        "the load the drive could not lift"
    )


@pytest.mark.parametrize(
    ("case", "f_max_share", "first", "cap", "words"),
    [
        ("cap in the rise", 0.9, IgnitionSpec(0.5), True, CAPPED_ACCEL),
        (
            "cap that lets go",
            0.85,
            IgnitionSpec(0.0, reference="push_start"),
            True,
            CAPPED_ACCEL,
        ),
        ("held", 2.0, IgnitionSpec(0.5), False, "no cap bound, so it held its command"),
    ],
)
def test_the_cap_record_and_its_words_on_real_pushes(
    case: str, f_max_share: float, first: IgnitionSpec, cap: bool, words: str, f9_vehicle: Vehicle
) -> None:
    """1-D F9 acceleration-law pushes (a_cmd 3 g0, t_r 0.5 s, F_max a share of M (a + g)):
    cold at 0.9 its cap (drive_cap) binds at 0.433 s, inside the rise, and never lets go,
    so the push never flies 3 g0 net; hot (lit at push start) at 0.85 the cap binds in
    the rise and lets go (drive_cap_end) after the rise, and binds no more, so the
    command is flown from there to the release; at 2.0 no cap binds. push_cap_bound is
    True for the first two, whose words claim no held command and no order
    (``CAPPED_ACCEL``), and False for the third, which held its command after the rise (fix
    round 2, P2-M1, V2-2)."""
    a = 3.0 * G0_MPS2
    f_max = f_max_share * f9_vehicle.liftoff_mass_kg() * (a + G)
    model = LinearMotorAssist(
        "acceleration",
        f_max,
        f_max * 1e3,
        0.5,
        0.0,
        5.0 * G0_MPS2,
        accel_command_mps2=a,
        g_eff_mps2=G,
    )
    specs = {name: IgnitionSpec() for name in f9_vehicle.stage_names}
    specs[f9_vehicle.stage_names[0]] = first
    result = sim.simulate(
        vehicle=f9_vehicle,
        ignition=specs,
        gravity=InverseSquareGravity(MU_EARTH_M3S2),
        g_eff_mps2=G,
        assist=model,
        track=StraightTrack(L, VERTICAL, -L),
        start=None,
        end="stage1_burnout",
        settings=IntegratorSettings(rtol=1e-10),
    )
    met = result.metrics
    events = result.events
    pushed = events[events["phase"] == "ASSIST"]
    caps = pushed[pushed["event"] == "drive_cap"]["t_s"].tolist()
    lets_go = pushed[pushed["event"] == "drive_cap_end"]["t_s"].tolist()
    assert met["push_cap_bound"] is cap
    if cap:
        assert caps and caps[0] < 0.5, caps  # bound inside the rise
        assert bool(lets_go) == (case == "cap that lets go"), lets_go
        if lets_go:  # after the rise, and no cap binds again: the command is flown on
            assert lets_go[0] > 0.5 and len(caps) == 1, (caps, lets_go)
    else:
        assert not caps
    text = replay.motor_acceleration_text(
        replay.linear_motor_settings({"model": "linear_motor"}, met), met
    )
    assert text.startswith(words), text
    assert "from the end of its rise until" not in text


def _record(
    name: str, assisted: bool = True, events: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """A replay record of ``drive_caveat`` and ``closeup_notes`` (the keys they read)."""
    return {
        "key": name,
        "assisted": assisted,
        "payload_kg": None,
        "role": replay.ROLE_RUN,
        "events": events or [],
        "start_alt_m": -100.0 if assisted else None,
        "exit_speed_mps": None,
        "push_s": None,
        "vertical": assisted,
        "phase": [],
    }


TARGET_EVENTS: list[dict[str, Any]] = [
    {"t": -2.381, "name": "push_start", "alt_m": -100.0, "x_km": 0.0, "v": 0.0},
    {"t": 0.0, "name": "release", "alt_m": -35.7, "x_km": 0.0, "v": 60.0},
    {"t": 0.5, "name": "ignition", "alt_m": -6.9, "x_km": -0.0, "v": 55.11},
    {"t": 0.5, "name": "kick_start", "alt_m": -6.9, "x_km": -0.0, "v": 55.11},
    {"t": 0.627, "name": "shaft_exit", "alt_m": 0.0, "x_km": -0.0, "v": 53.86},
]
"""lm_target's events after the gate run (time after release): lit and kicked in the
shaft, the mouth crossed at 53.86 m/s, 1.5 mm off the axis."""


def test_drive_caveat_beside_a_prescribed_push() -> None:
    """The drive caveat of a prescribed run (silo) beside three linear-motor runs (lm at
    the track end; lm_target released below the mouth, lit and kicked in the shaft;
    lm_cmd, the acceleration law with no cap bound and its release speed not reached):
    the prescribed push in the first sentence, the shaft of lm_target with no air drag on
    the push only, in the one shaft clause (fix round 2, V2-4), each linear motor in a
    sentence of its own (its clause and what its
    acceleration does, the acceleration law's held command; the early release's flight
    through the rest of the shaft), and the omissions by law and cap (the force law's
    'can change' with the drag's directions; the uncapped acceleration law's biases); a
    linear motor shown alone is 'The drive'; two runs with the same omissions share one
    sentence worded for both ('each push', fix round 3, V3-1); a force-law run with a
    massless carriage gets that omission's direction (the release position and push time
    low, or the speed at release high, and the interface force high) and the drag's
    interface clause limited to the power phase (fix round 3, V3-2)."""
    silo = {"model": "constant_accel", "net_accel_g": 3.0, "shaft": "vented"}
    sources = {
        "pad": {"config": {"assist": {"model": "none"}}, "metrics": {}},
        "silo": {"config": {"assist": silo}, "metrics": {"carriage_mass_kg": 0.0}},
        "lm": {"config": {"assist": LM_CONFIG}, "metrics": LM_METRICS},
        "lm_target": {"config": {"assist": LM_CONFIG}, "metrics": TARGET_METRICS},
        "lm_cmd": {"config": {"assist": CMD_CONFIG}, "metrics": CMD_METRICS},
    }
    runs = [
        _record("pad", False),
        _record("silo"),
        _record("lm"),
        _record("lm_target", events=TARGET_EVENTS),
        _record("lm_cmd"),
    ]
    text = replay.drive_caveat(runs, sources, {})
    assert text == (
        "The drive is a prescribed 3 g push with no force or power limit (silo), the carriage "
        "is massless (silo and lm_cmd) and the shaft has no air drag (on the push only for "
        "lm_target). "
        f"The drive of lm is {CLAUSE}, released at the track end at a measured exit speed of "
        f"72.5 m/s; {FORCE_ACCEL}. "
        f"The drive of lm_target is {CLAUSE}, released on reaching its release speed, 60.0 "
        f"m/s measured, 35.7 m below the mouth; {FORCE_ACCEL}; it then flew the rest of the "
        "shaft as in the open atmosphere (drag, dynamic pressure and Mach number computed "
        "there; no shaft flow model, no walls), where stage 1 lit and its kick began. "
        f"The drive of lm_cmd is {CMD_CLAUSE}, released at the track end at a measured exit "
        "speed of 76.6 m/s, its release speed 90 m/s not reached; no cap bound, so it held "
        "its command, 3 g0 net, from the end of its rise to the release. "
        "Under the prescribed drive of silo the release speed does not depend on the "
        "carriage mass or the shaft drag: the massless carriage biases the drive energy and "
        "peak power low, and the missing shaft drag biases the drive energy, peak power and "
        "interface force low. "
        "For lm (linear_motor drive, force law) the missing shaft drag can change the speed "
        "at release; the missing shaft drag biases the speed at release high, and the "
        "interface force and drive work low; its size is not established here. "
        "For lm_target (linear_motor drive, force law) the missing shaft drag can change "
        "where the push reaches its release speed (the release position); the missing shaft "
        "drag biases the release position and push time low, and the interface force and "
        "drive work low; its size is not established here. "
        "For lm_cmd (linear_motor drive, acceleration law, no cap bound) the massless "
        "carriage and the missing shaft drag do not change its push: the massless carriage "
        "biases the drive energy and peak power low, and the missing shaft drag biases the "
        "drive energy, peak power and interface force low; with them a cap could bind that "
        "this push never reached."
    )
    assert "holds no constant acceleration" not in text and "not a held value" not in text
    alone = replay.drive_caveat(
        [_record("pad", False), _record("lm_target", events=TARGET_EVENTS)], sources, {}
    )
    assert alone is not None and f"The drive is {CLAUSE}, released on reaching" in alone
    assert "The shaft has no air drag on the push." in alone  # every vented run is early
    capped = {**CMD_METRICS, "push_cap_bound": True}
    sources["lm_cmd"] = {"config": {"assist": CMD_CONFIG}, "metrics": capped}
    text = replay.drive_caveat([_record("lm_cmd")], sources, {})
    assert text is not None
    assert CAPPED_ACCEL in text and "until a cap" not in text
    assert (
        "For lm_cmd (linear_motor drive, acceleration law, a cap bound) the massless carriage "
        "and the missing shaft drag do not change its push while no cap binds (" in text
    )
    assert "can change the speed at release where it does; their size is not established" in text
    # fix round 3 (V3-1): two runs with the same words share a sentence worded for both
    sources["lm_cmd"] = {"config": {"assist": CMD_CONFIG}, "metrics": CMD_METRICS}
    sources["lm_cmd2"] = sources["lm_cmd"]
    text = replay.drive_caveat([_record("lm_cmd"), _record("lm_cmd2")], sources, {})
    assert text is not None and text.endswith(
        "For lm_cmd and lm_cmd2 (linear_motor drive, acceleration law, no cap bound) the "
        "massless carriage and the missing shaft drag do not change each push: the massless "
        "carriage biases the drive energy and peak power low, and the missing shaft drag "
        "biases the drive energy, peak power and interface force low; with them a cap could "
        "bind that none of these pushes reached."
    ), text
    # fix round 3 (V3-2): a massless carriage under the force law, released early
    light = {**LM_CONFIG, "carriage_mass_t": 0}
    sources["lm_light"] = {
        "config": {"assist": light},
        "metrics": {**TARGET_METRICS, "carriage_mass_kg": 0.0},
    }
    text = replay.drive_caveat([_record("lm_light", events=TARGET_EVENTS)], sources, {})
    assert text is not None and text.endswith(
        "For lm_light (linear_motor drive, force law) the massless carriage and the missing "
        "shaft drag can change where the push reaches its release speed (the release "
        "position); the massless carriage biases the release position and push time low and "
        "the interface force high (all of the drive force reaches the vehicle); the missing "
        "shaft drag biases the release position and push time low, and the interface force "
        "(in the power phase only, without a carriage mass) and drive work low; their size is "
        "not established here."
    ), text
    sources["lm_light"]["metrics"] = {**LM_METRICS, "carriage_mass_kg": 0.0}
    text = replay.drive_caveat([_record("lm_light")], sources, {})
    assert text is not None and (
        "the massless carriage biases the speed at release high and the interface force high "
        "(all of the drive force reaches the vehicle)" in text
    )


def test_close_up_notes_of_a_release_below_the_mouth() -> None:
    """``closeup_notes``: a release below the mouth in a sentence of its own (released on
    reaching its release speed, after the push time, the distance below the mouth), then
    from the record's events the mouth crossing (speed, time after release, within 1 m
    of the axis, or the offset in metres) or a fall back (an impact below the ground) or
    a departure before the kick (no crossing, fix round 1), and since fix round 2 the
    crossing read from the sampled series where no shaft_exit is logged (fix round 2:
    'about', 'unpowered' before any ignition, placed against the record's kick_start, or
    'no kick is logged'), or what is logged when the series has no crossing either; a
    fall back with the depth of its impact, on its parked carriage (the floor of the
    flight model in the shaft) or at its apex (fix round 3; and ``early_flight_text``
    flying in the shaft until it fell back), the place read from the run's shaft_fallback
    flag, never from the page's rounded speed (fix round 4, H4-M1, C4-m1: a planar apex
    keeps about 2 omega_p dz of |v_rel|, 0.01 m/s on the page), nothing said without one;
    an apex impact written out in full as one, never as a fall (fix round 5, M1: 'it stops
    rising <d> m below the mouth, below its carriage parked above it, and its impact is
    logged at once at that apex'); a release at a buried track exit that falls back onto
    its carriage in a sentence of its own after its group's, keyed on its flag (fix round
    5, M2);
    a rise above the mouth before the fall back through it (P4-M1); a turnaround above the
    parked carriage, with the mouth crossing after it (H4-m3, V4-2); a release at the
    track end keeps its 'leaves the silo mouth'; the vented-shaft note limited to the
    push, the flight in the shaft after the release computed as in the open atmosphere
    (unchanged without an early release); the results note of one and of two early
    releases ('its', 'their'; below the mouth, else before the track end)."""
    sources = {
        "lm": {"config": {"assist": LM_CONFIG}, "metrics": LM_METRICS},
        "lm_target": {"config": {"assist": LM_CONFIG}, "metrics": TARGET_METRICS},
    }
    lm = {**_record("lm"), "exit_speed_mps": 72.54, "push_s": 2.92}
    target = {**_record("lm_target", events=TARGET_EVENTS), "exit_speed_mps": 60.0}
    target["push_s"] = 2.38
    notes = replay.closeup_notes([lm, target], sources)
    assert notes == [
        "lm starts 100 m below ground and leaves the silo mouth at 72.5 m/s after 2.9 s.",
        "lm_target starts 100 m below ground and is released on reaching its release speed, "
        "60.0 m/s, after 2.4 s, 35.7 m below the silo mouth; it passes the mouth at 53.9 m/s "
        "at T+0.6 s, within 1 m of the shaft axis.",
        "The shaft is treated as vented, so no air drag, dynamic pressure or Mach number is "
        "computed inside it on the push; after the release below the mouth of lm_target the "
        "flight in the shaft is computed as in the open atmosphere, with drag, dynamic "
        "pressure and Mach number (no shaft flow model, no walls).",
    ]
    off = [*TARGET_EVENTS[:-1], {**TARGET_EVENTS[-1], "x_km": 0.004}]
    note = replay.closeup_notes([{**target, "events": off}], sources)[0]
    assert note.endswith("at T+0.6 s, 4 m off the shaft axis (no clearance is checked).")
    impact = {"t": 1.0, "name": "impact", "alt_m": -30.0, "x_km": 0.0, "v": 8.94}
    fell = [*TARGET_EVENTS[:2], impact]
    on_carriage = (
        f"FALL_PRE_IGN at t = 3 s: {SHAFT_FALLBACK}: the vehicle fell back inside the shaft, "
        "after a release below the ground, onto the parked carriage at z = -30 m (30 m below "
        "the ground) at 8.94 m/s: the impact is logged there (...)"
    )
    flagged = {
        **sources,
        "lm_target": {
            "config": {"assist": LM_CONFIG},
            "metrics": {**TARGET_METRICS, "flags": [on_carriage]},
        },
    }
    note = replay.closeup_notes([{**target, "events": fell}], flagged)[0]
    assert note.endswith(
        "; it falls back inside the shaft, its impact logged 30.0 m below the mouth on its "
        "parked carriage, the floor of the flight model in the shaft."
    )
    assert replay.early_flight_text({**target, "events": fell}, True, [on_carriage]) == (
        "it then flew in the shaft as in the open atmosphere (drag, dynamic pressure and Mach "
        "number computed there; no shaft flow model, no walls), until it fell back, its "
        "impact logged 30.0 m below the mouth on its parked carriage, the floor of the flight "
        "model in the shaft"
    )
    # fix round 4 (H4-M1, C4-m1): the place is the flag's; a planar apex reads 0.01 m/s
    at_apex_flag = (
        f"COAST at t = 3 s: {SHAFT_FALLBACK}: the vehicle stopped rising 30 m below the ground "
        "(z = -30 m), inside the shaft after a release below the ground, at or below the "
        "parked carriage's altitude z = 8 m (...): the impact is logged at once at that apex"
    )
    at_apex = [*TARGET_EVENTS[:2], {**impact, "v": 0.01}]  # its carriage parked above it
    apex_src = {
        **sources,
        "lm_target": {
            "config": {"assist": LM_CONFIG},
            "metrics": {**TARGET_METRICS, "flags": [at_apex_flag]},
        },
    }
    note = replay.closeup_notes([{**target, "events": at_apex}], apex_src)[0]
    # fix round 5 (M1, P5-M1): it stopped rising there and did not fall
    assert note == (
        "lm_target starts 100 m below ground and is released on reaching its release speed, "
        "60.0 m/s, after 2.4 s, 35.7 m below the silo mouth; it stops rising 30.0 m below the "
        "mouth, below its carriage parked above it, and its impact is logged at once at that "
        "apex."
    )
    assert replay.early_flight_text({**target, "events": at_apex}, True, [at_apex_flag]) == (
        "it then flew in the shaft as in the open atmosphere (drag, dynamic pressure and Mach "
        "number computed there; no shaft flow model, no walls), until it stopped rising 30.0 m "
        "below the mouth, below its carriage parked above it, its impact logged at once at "
        "that apex"
    )
    assert "fall" not in note.split("; ")[-1] and "fell" not in replay.early_flight_text(
        {**target, "events": at_apex}, True, [at_apex_flag]
    )
    assert replay.shaft_impact_words([at_apex_flag]) == replay.SHAFT_APEX_WORDS
    assert scene.shaft_impact_text([at_apex_flag]) == replay.SHAFT_APEX_WORDS
    assert scene.shaft_impact_text([on_carriage]) == replay.SHAFT_CARRIAGE_WORDS
    assert replay.closeup_notes([{**target, "events": fell}], sources)[0].endswith(
        "; it falls back inside the shaft, its impact logged 30.0 m below the mouth."
    )  # no shaft_fallback flag: the place is not stated
    # fix round 5 (M2): a release at a track exit below the ground (a constant_accel push to
    # a buried exit) that falls back onto its carriage gets a sentence of its own, keyed on
    # its flag, not on its release trigger; none without the flag
    ca_cfg = {
        "model": "constant_accel",
        "net_accel_g": 1.0,
        "stroke_m": 20,
        "brake_decel_g": 5,
        "shaft": "vented",
        "track": {"angle_deg": 90, "exit_altitude_m": -50},
    }
    buried_flag = (
        f"COAST at t = 5.86 s: {SHAFT_FALLBACK}: the vehicle fell back inside the shaft, after "
        "a release below the ground, onto the parked carriage at z = -46 m (46 m below the "
        "ground) at 17.72 m/s: the impact is logged there (...)"
    )
    buried = {
        **_record("ca_buried"),
        "start_alt_m": -70.0,
        "exit_speed_mps": 19.81,
        "push_s": 2.02,
        "events": [
            {"t": 0.0, "name": "release", "alt_m": -50.0, "x_km": 0.0, "v": 19.81},
            {"t": 2.03, "name": "apex", "alt_m": -29.93, "x_km": 0.0, "v": 0.0},
            {"t": 3.84, "name": "impact", "alt_m": -46.0, "x_km": 0.0, "v": 17.72},
        ],
    }
    ca_metrics = {"exit_speed_mps": 19.81, "push_time_s": 2.02, "flags": [buried_flag]}
    ca_src = {"ca_buried": {"config": {"assist": ca_cfg}, "metrics": ca_metrics}}
    assert replay.closeup_notes([buried], ca_src)[:2] == [
        "ca_buried starts 70 m below ground and leaves the silo mouth at 19.8 m/s after 2.0 s.",
        "ca_buried falls back inside the shaft, its impact logged 46.0 m below the ground on "
        "its parked carriage, the floor of the flight model in the shaft.",
    ]
    no_flag = {"ca_buried": {"config": {"assist": ca_cfg}, "metrics": {**ca_metrics, "flags": []}}}
    assert not any("falls back" in n for n in replay.closeup_notes([buried], no_flag))
    # fix round 4 (P4-M1): through the open mouth from an apex above it
    rose = [
        *TARGET_EVENTS[:2],
        {"t": 4.0, "name": "apex", "alt_m": 1.14, "x_km": 0.0, "v": 0.0},
        {**impact, "t": 9.0, "alt_m": -59.39, "v": 34.44},
    ]
    note = replay.closeup_notes([{**target, "events": rose}], flagged)[0]
    assert note.endswith(
        "; it rises 1.1 m above the mouth and falls back into the shaft, its impact logged "
        "59.4 m below the mouth on its parked carriage, the floor of the flight model in the "
        "shaft."
    ), note
    assert replay.early_flight_text({**target, "events": rose}, True, [on_carriage]).endswith(
        ", until it rose 1.1 m above the mouth and fell back into the shaft, its impact logged "
        "59.4 m below the mouth on its parked carriage, the floor of the flight model in the "
        "shaft"
    )
    # fix round 4 (H4-m3, V4-2): a burn that sank back and turned around above its carriage
    turn_metrics = {
        **TARGET_METRICS,
        "push_release_speed_mps": 10.0,
        "release_position_m": 2.07,
        "exit_speed_mps": 10.0,
        "push_time_s": 0.92,
        "braking_distance_m": 1.02,
    }
    turn_events = [
        {"t": -0.92, "name": "push_start", "alt_m": -100.0, "x_km": 0.0, "v": 0.0},
        {"t": 0.0, "name": "release", "alt_m": -97.93, "x_km": 0.0, "v": 10.0},
        {"t": 0.5, "name": "ignition", "alt_m": -93.85, "x_km": 0.0, "v": 5.1},
        {"t": 1.096, "name": "apex", "alt_m": -92.74, "x_km": 0.0, "v": 0.0},
        {"t": 3.06, "name": "turnaround", "alt_m": -96.44, "x_km": 0.0, "v": 0.0},
        {"t": 13.0, "name": "kick_start", "alt_m": 120.0, "x_km": 0.0, "v": 50.0},
    ]
    turned = {
        **_record("burn_turn", events=turn_events),
        "t": [0.0, 1.1, 3.06, 10.0, 10.4],
        "alt_m": [-97.93, -92.74, -96.44, -2.0, 6.0],
        "v": [10.0, 0.0, 0.0, 26.0, 28.0],
    }
    turn_src = {"burn_turn": {"config": {"assist": LM_CONFIG}, "metrics": turn_metrics}}
    assert replay.closeup_notes([turned], turn_src)[0] == (
        "burn_turn starts 100 m below ground and is released on reaching its release speed, "
        "10.0 m/s, after 0.9 s, 97.9 m below the silo mouth; it stops rising 92.7 m below "
        "the mouth and sinks back, and its thrust turns it around 96.4 m below the mouth, 0.5 "
        "m above its parked carriage, at T+3.1 s; it passes the mouth at about 26.5 m/s at "
        "about T+10.1 s (read from the sampled series: no mouth crossing is logged), before "
        "its kick."
    )
    assert replay.early_flight_text(turned, True, [], turn_metrics) == (
        "it then flew the rest of the shaft as in the open atmosphere (drag, dynamic pressure "
        "and Mach number computed there; no shaft flow model, no walls), where stage 1 lit; "
        "it stopped rising 92.7 m below the mouth and sank back, and its thrust turned it "
        "around 96.4 m below the mouth, 0.5 m above its parked carriage, at T+3.1 s"
    )
    # fix round 4 (H4-m5): a measured speed is formatted once, from the unrounded metric
    rounded = {**target, "exit_speed_mps": 72.65, "push_s": 2.38}
    odd = {
        **sources,
        "lm_target": {
            "config": {"assist": LM_CONFIG},
            "metrics": {**TARGET_METRICS, "exit_speed_mps": 72.6468},
        },
    }
    assert ", 72.6 m/s, after 2.4 s" in replay.closeup_notes([rounded], odd)[0]
    lm_odd = {**lm, "exit_speed_mps": 72.65}
    odd["lm"] = {
        "config": {"assist": LM_CONFIG},
        "metrics": {**LM_METRICS, "exit_speed_mps": 72.6468},
    }
    assert "leaves the silo mouth at 72.6 m/s" in replay.closeup_notes([lm_odd], odd)[0]
    # no shaft_exit event (logged only when the kick began in the shaft): nothing logged,
    # then the crossing read from the sampled series, placed against the kick
    unlit = {**target, "events": TARGET_EVENTS[:2]}
    note = replay.closeup_notes([unlit], sources)[0]
    assert note.endswith("; no mouth crossing and no kick are logged.")
    kicked_in = [*TARGET_EVENTS[:2], TARGET_EVENTS[3]]
    note = replay.closeup_notes([{**target, "events": kicked_in}], sources)[0]
    assert note.endswith("; its kick began in the shaft, and no mouth crossing is logged.")
    series = {"t": [0.0, 1.0, 1.5, 2.0], "alt_m": [-35.7, -6.0, 13.0, 30.0], "v": [50, 40, 36, 32]}
    late_kick = {"t": 8.0, "name": "kick_start", "alt_m": 300.0, "x_km": 0.0, "v": 60.0}
    lit = {"t": 4.0, "name": "ignition", "alt_m": 100.0, "x_km": 0.0, "v": 25.0}
    coasted = {**target, **series, "events": [*TARGET_EVENTS[:2], lit, late_kick]}
    note = replay.closeup_notes([coasted], sources)[0]
    assert note.endswith(
        "; it passes the mouth unpowered at about 38.7 m/s at about T+1.2 s (read from the "
        "sampled series: no mouth crossing is logged), before its kick."
    ), note
    never = {**target, **series, "events": TARGET_EVENTS[:2]}  # stage 1 never lit
    assert replay.closeup_notes([never], sources)[0].endswith(
        "(read from the sampled series: no mouth crossing is logged), and no kick is logged."
    )
    assert replay.series_mouth_crossing({"t": [0.0, 1.0], "alt_m": [-5.0, -1.0]}) is None
    assert "before its kick" not in " ".join(
        replay.closeup_notes([r], sources)[0] for r in (unlit, never)
    )
    assert replay.closeup_notes([lm], sources)[-1] == (
        "The shaft is treated as vented, so no air drag, dynamic pressure or Mach number is "
        "computed inside it."
    )
    assert replay.early_release_results_note(["lm_target"], sources) == (
        "The exit speed of lm_target is its speed at release, below the mouth (it was released "
        "on reaching its release speed; the close-up notes say where), and its ideal "
        "screening is taken at that speed, not at the speed at the mouth."
    )
    tower = {**LM_CONFIG, "track": {"angle_deg": 90, "exit_altitude_m": 20}}
    sources["lm_tower"] = {"config": {"assist": tower}, "metrics": TARGET_METRICS}
    assert replay.early_release_results_note(["lm_target", "lm_tower"], sources) == (
        "The exit speed of lm_target and lm_tower is their speed at release, before the track "
        "end (they were released on reaching their release speeds; the close-up notes say "
        "where), and their ideal screening is taken at those speeds, not at the speed at the "
        "track end."
    )
    nearly = {**LM_CONFIG, "track": {"angle_deg": 90, "exit_altitude_m": 1e-7}}
    assert replay.below_mouth(nearly) and not replay.below_mouth(tower)  # ATOL_M (C2-m6)


# --------------------------------------------------------------------- the scene


def test_scene_push_settings_of_a_linear_motor_run() -> None:
    """``scene.assist_settings``: a linear-motor run's net_accel_mps2 and net_accel_g stay
    None (no a = v^2/(2 L) from its measured exit speed) and its push time is the metric;
    its ``drive`` carries the drive clause (``replay.linear_motor_clause``, payload data
    the frozen template does not draw), the settings and the release, its source 'metric'
    (or 'config' for a directory without the drive metrics); a constant_accel run whose
    metrics hold no acceleration still derives one from its exit speed (as before S4a)
    and has no ``drive``. ``early_release_caveat`` and ``early_release_frame_text``: a
    release below the mouth (the drawn carriage brakes from the mouth; where the model's
    stops: through the stroke left to above the mouth, or in it below the mouth, with the
    facility max(L, s + d) of such a record, fix rounds 2 and 3), a release before a track
    end that is not a mouth (an exit above the ground), with the fall back's impact note
    (on the parked carriage, or at the apex: fix round 3); None for a release at the
    track end; ``early_release_lines`` groups the frame lines (one line for every run
    released below the mouth, then one for the runs that fell back inside the shaft, fix
    round 3, H3-m1, which corrects both claims of the drawn impact note, fix round 4,
    V4-1, H4-m1); fix round 5 (M1, P5-M1): ``fall_back_caveat`` and ``fall_back_frame_text``
    by ``shaft_impact_kind`` written out, an apex impact worded as one (it stopped rising,
    below its carriage parked above it; only the note's 'altitude 0' corrected, never its
    'no contact'), one frame line per kind; (M2) keyed on the flag, not on the release
    trigger: a constant_accel push to a buried exit and a track-end run with the flag get
    the fall-back caveat and frame line; ``frame_caveat`` unchanged without one;
    ``display_only_for`` swaps the display-only carriage item when a run's flight ended
    inside the shaft (carriage or apex), DISPLAY_ONLY itself unchanged (V4-1), the item
    worded on the code's rule (the apex case, then the carriage parked at or above the
    ground or below it: fix round 5, M1, M2, C5-m4); ``no_release_caveat`` and its frame
    line for a linear-motor push that never released, None for a constant_accel run (fix
    round 4, V4-3)."""
    lm = scene.assist_settings(LM_CONFIG, TARGET_METRICS)
    assert lm is not None
    assert lm["net_accel_mps2"] is None and lm["net_accel_g"] is None
    assert "net_accel_mps2" not in lm["sources"] and lm["push_time_s"] == 2.381
    assert lm["drive"] == {
        "label": replay.linear_motor_clause(LM_CONFIG, TARGET_METRICS),
        "control": "force",
        "force_max_N": 22.43e6,
        "power_max_W": 1.3e9,
        "rise_time_s": 0.5,
        "accel_command_mps2": None,
        "stop_taper_m": None,
        "release_speed_mps": 60.0,
        "cap_bound": None,
        "corner_speed_mps": 1.3e9 / 22.43e6,
        "release_trigger": "target_speed",
        "release_position_m": 64.28,
        "exit_speed_mps": 60.0,
        "power_limited": True,
        "accel_mean_mps2": 24.86,
    }
    assert lm["sources"]["drive"] == "metric"
    old = scene.assist_settings(LM_CONFIG, {"exit_speed_mps": 72.54})
    assert old is not None and old["sources"]["drive"] == "config"
    ca_cfg = {"model": "constant_accel", "stroke_m": 50, "brake_decel_g": 5, "shaft": "vented"}
    ca = scene.assist_settings(ca_cfg, {"exit_speed_mps": 50.0})
    assert ca is not None and "drive" not in ca and "drive" not in ca["sources"]
    assert ca["net_accel_mps2"] == 50.0**2 / (2.0 * 50.0)
    assert ca["sources"]["net_accel_mps2"] == "derived"
    assert ca["push_time_s"] == 50.0 / (50.0**2 / 100.0)
    record = {"key": "lm_target", "assist": lm}
    assert scene.early_release_caveat(record) == (
        "lm_target is released 35.7 m below the mouth: from the release on the scene draws its "
        "carriage at the mouth, above the vehicle still in the shaft, and braking on rails "
        "drawn above the ground (the page brakes every carriage from the end of the stroke, a "
        "limit of its drawing); the model brakes it from the release point, through the "
        "stroke left to 1.0 m above the mouth (facility 101.0 m)."
    )
    # stopping 15.7 m below the mouth, its facility is max(L, s + d) = L (fix round 3, C3-m1)
    short = {
        "key": "lm_short",
        "assist": {**lm, "braking_distance_m": 20.0, "facility_length_m": 100.0},
    }
    assert str(scene.early_release_caveat(short)).endswith(
        "the model brakes it from the release point in the stroke left, where it stops 15.7 m "
        "below the mouth (facility 100.0 m)."
    )
    tower = {"key": "lm_tower", "assist": {**lm, "exit_altitude_m": 20.0}}
    assert str(scene.early_release_caveat(tower)).startswith(
        "lm_tower is released 35.7 m before the track end: from the release on the scene "
        "draws its carriage at the track end"
    )
    tower_frame = scene.early_release_frame_text(["lm_tower"], mouth=False)
    assert tower_frame == (
        "lm_tower: released before the track end; the carriage drawn at and beyond the track "
        "end after release is a drawing limit (the model brakes it from the release point)."
    )
    caveats, frames = scene.early_release_lines([record, short, tower], {})
    assert len(caveats) == 3 and frames == [
        "lm_target and lm_short: released below the mouth; the carriage drawn at and above the "
        "mouth after release is a drawing limit (the model brakes it from the release point).",
        tower_frame,
    ]
    on_carriage = (
        f"FALL at t = 3 s: {SHAFT_FALLBACK}: the vehicle fell back inside the shaft, after a "
        "release below the ground, onto the parked carriage at z = -96.97 m (...)"
    )
    fell = scene.early_release_caveat(record, [on_carriage])
    assert fell is not None and fell.endswith(
        "lm_target fell back inside the shaft: its impact is logged there, on its parked "
        "carriage, the floor of the flight model in the shaft, not where the base returns to "
        "altitude 0 as the drawn impact note says, and the note's 'no contact with the "
        "carriage' does not hold for it."
    )
    apex = f"FALL at t = 3 s: {SHAFT_FALLBACK}: the vehicle stopped rising 84 m below (...)"
    # fix round 5 (M1, P5-M1): an apex impact did not fall, and the model had no contact
    # with the carriage, which parked above it: only the note's 'altitude 0' is wrong
    apex_text = (
        "lm_target stopped rising inside the shaft, below its carriage parked above it (the "
        "model has no contact with the carriage on its braking path): its impact is logged at "
        "once at that apex, not where the base returns to altitude 0 as the drawn impact note "
        "says."
    )
    assert scene.fall_back_caveat("lm_target", [apex]) == apex_text
    assert str(scene.early_release_caveat(record, [apex])).endswith(
        f"(facility 101.0 m). {apex_text}"
    )
    assert scene.shaft_impact_kind([apex]) == scene.SHAFT_IMPACT_APEX
    assert scene.shaft_impact_kind([on_carriage]) == scene.SHAFT_IMPACT_CARRIAGE
    assert scene.shaft_impact_kind([f"{SHAFT_FALLBACK}: other"]) == scene.SHAFT_IMPACT_UNSTATED
    assert scene.fall_back_caveat("x", [f"{SHAFT_FALLBACK}: other"]) == (
        "x fell back inside the shaft: its impact is logged there, not where the base returns "
        "to altitude 0 as the drawn impact note says."
    )
    assert scene.fall_back_caveat("x", ["other flag"]) is None
    # fix rounds 3 and 4 (H3-m1, V4-1): a captured frame says where the fall back's impact
    # is logged and that the drawn note's carriage clause does not hold
    _caveats, frames = scene.early_release_lines([record, short], {"lm_target": [on_carriage]})
    assert (
        frames[-1]
        == scene.fall_back_frame_text(["lm_target"])
        == (
            "lm_target: fell back inside the shaft, whose floor in the model is the parked "
            "carriage; the impact is logged there, not where or as the drawn impact note says "
            "(its 'no contact with the carriage' and 'altitude 0' do not hold for it)."
        )
    )
    assert scene.fall_back_frame_text(["a", "b"]).endswith("do not hold for them).")
    # fix round 5 (M1, P5-M1): the apex frame line, one line per kind
    apex_frame = scene.fall_back_frame_text(["lm_target"], scene.SHAFT_IMPACT_APEX)
    assert apex_frame == (
        "lm_target: stopped rising inside the shaft, below its carriage parked above it; the "
        "impact is logged at once at that apex, not at altitude 0 as the drawn impact note says."
    )
    assert scene.fall_back_frame_text(["a", "b"], scene.SHAFT_IMPACT_APEX) == (
        "a and b: stopped rising inside the shaft, below their carriages parked above them; "
        "each impact is logged at once at its apex, not at altitude 0 as the drawn impact note "
        "says."
    )
    assert scene.fall_back_frame_text(["x"], scene.SHAFT_IMPACT_UNSTATED) == (
        "x: fell back inside the shaft; the impact is logged there, not at altitude 0 as the "
        "drawn impact note says."
    )
    both = {**short, "key": "lm_short"}
    caveats, frames = scene.early_release_lines(
        [record, both], {"lm_target": [apex], "lm_short": [on_carriage]}
    )
    assert frames[1:] == [
        scene.fall_back_frame_text(["lm_short"]),
        apex_frame,
    ]
    assert caveats[0].endswith(apex_text) and "'no contact" not in caveats[0]
    # fix round 5 (M2): keyed on the flag, not on the release trigger: a run released at a
    # track exit below the ground (a constant_accel push to a buried exit) that fell back
    # onto its carriage gets the fall-back caveat alone and its frame line
    buried = {"key": "ca_buried", "assist": {**ca, "exit_altitude_m": -50.0}}
    assert scene.early_release_caveat(buried, [on_carriage]) is None
    assert scene.early_release_lines([buried], {"ca_buried": [on_carriage]}) == (
        [str(scene.fall_back_caveat("ca_buried", [on_carriage]))],
        [scene.fall_back_frame_text(["ca_buried"])],
    )
    assert str(scene.fall_back_caveat("ca_buried", [on_carriage])).startswith(
        "ca_buried fell back inside the shaft: its impact is logged there, on its parked "
        "carriage, the floor of the flight model in the shaft, not where"
    )
    assert scene.early_release_lines([buried], {}) == ([], [])
    # fix rounds 4 and 5 (V4-1, M1, M2, C5-m4): the display-only carriage item of a
    # selection with a flight that ended inside the shaft, on the code's rule
    plain_items = scene.display_only_for([[], ["other flag"]])
    assert plain_items == list(scene.DISPLAY_ONLY)
    assert "the model has no contact with the carriage" in plain_items[4]  # gallery text kept
    swapped = scene.display_only_for([[], [on_carriage]])
    assert swapped[scene.DISPLAY_ONLY_CARRIAGE_INDEX] == scene.DISPLAY_ONLY_SHAFT_CARRIAGE_ITEM
    assert scene.display_only_for([[apex]]) == swapped
    assert [x for i, x in enumerate(swapped) if i != 4] == list(scene.DISPLAY_ONLY[:4]) + list(
        scene.DISPLAY_ONLY[5:]
    )
    assert scene.DISPLAY_ONLY[4].startswith("The carriage after release and where it brakes")
    item = scene.DISPLAY_ONLY_SHAFT_CARRIAGE_ITEM
    assert (
        "a vehicle whose apex lies inside the shaft below its parked carriage (a carriage "
        "braking at less than the vehicle's deceleration, parked above that apex) ends its run "
        "at once at that apex (the model has no contact with the carriage on its braking path), "
        "so only the drawn impact note's 'altitude 0' does not hold for it" in item
    )
    assert (
        "Any other fall back follows the obstacle-free path to the ground when the carriage "
        "parks at or above the ground" in item
    )
    assert "after a release below the ground whose carriage parks below it" in item
    assert "released at the track end" not in item  # the rule is not the trigger (M2)
    # fix round 4 (V4-3): a linear-motor push that never released
    stall_metrics = {
        **CMD_METRICS,
        "release_trigger": None,
        "release_position_m": None,
        "exit_speed_mps": None,
        "push_time_s": None,
        "flags": [],
    }
    stall = {
        "key": "q_stall",
        "status": "drive_stall",
        "assist": scene.assist_settings(CMD_CONFIG, stall_metrics),
    }
    stall_text = (
        "q_stall was never released: its push never moved (status drive_stall), and the run "
        "ends there; the scene still draws its carriage at the mouth after T+0, away from the "
        "vehicle (a limit of the page's drawing: the model's carriage stays under the vehicle "
        "where the push stopped)."
    )
    assert scene.no_release_caveat(stall) == stall_text
    assert scene.early_release_lines([stall], {}) == (
        [stall_text],
        [
            "q_stall: never released; the carriage drawn at the mouth after T+0 is a drawing "
            "limit (the push stopped on the track)."
        ],
    )
    stopped = {**stall, "key": "q_stop", "status": "drive_limit"}
    assert "its push stopped on the track (status drive_limit)" in str(
        scene.no_release_caveat(stopped)
    )
    ca_stop = {"key": "ca", "status": "drive_limit", "assist": ca}
    assert scene.no_release_caveat(ca_stop) is None  # constant_accel: unchanged
    assert scene.no_release_caveat({**stall, "status": "nominal"}) is None
    frame = scene.early_release_frame_text(["lm_target"])
    assert frame == (
        "lm_target: released below the mouth; the carriage drawn at and above the mouth after "
        "release is a drawing limit (the model brakes it from the release point)."
    )
    at_end = {"key": "lm", "assist": scene.assist_settings(LM_CONFIG, LM_METRICS)}
    assert scene.early_release_caveat(at_end) is None
    assert scene.early_release_lines([at_end], {}) == ([], [])
    # a track-end run's lines are keyed on its flag (fix round 5, M2), never on its trigger
    assert scene.early_release_lines([at_end], {"lm": [on_carriage]})[1] == [
        scene.fall_back_frame_text(["lm"])
    ]
    vehicles = ["generic_f9_class_2d"]
    assert scene.frame_caveat(vehicles, [frame]) == scene.frame_caveat(vehicles).replace(
        scene.FRAME_MORE_TEXT, f"{frame} {scene.FRAME_MORE_TEXT}"
    )


# ------------------------------------------------------------------- the summary


def _fake_run(name: str, metrics: dict[str, Any]) -> SimpleNamespace:
    """A RunResult stand-in: the name, metrics, a status and a time-stated ramp start."""
    ignition = SimpleNamespace(ramp_start=("time", None))
    run = SimpleNamespace(ignition_for=lambda _stage: ignition)
    return SimpleNamespace(
        name=name,
        result=SimpleNamespace(metrics=metrics, status="inserted", flags=[]),
        resolved=SimpleNamespace(run=run, vehicle_dict={"stages": [{"name": "stage1"}]}),
    )


def _fake_er(runs: dict[str, dict[str, Any]]) -> SimpleNamespace:
    """An ExperimentResult stand-in whose first run is the baseline."""
    fakes = {name: _fake_run(name, m) for name, m in runs.items()}
    return SimpleNamespace(runs=fakes, baseline=next(iter(fakes.values())), comparison={})


def test_summary_rows_of_a_linear_motor_run() -> None:
    """LINEAR_MOTOR_ROWS follow the facility row of the 1-D and the planar tables when a
    linear-motor run is in the table: '-' in a run that is not one, "none" for an unset
    push setting, n/a for the cap row under the force law, the metric otherwise; a table
    without a linear-motor run gains no row; every LINEAR_MOTOR_METRICS key and KI-052's
    settings have a row; the labels name the mean a mean over the whole push and claim no
    held value the push does not hold (fix round 1; round 2: the cap row's False and the
    felt row worded for a cap in the rise, a release in the rise and a stall); a
    linear-motor run without a push record (a failed guidance) reads n/a in every row and
    still brings the rows (fix round 2, P2-m3); the brake rows say they go negative when
    a_b < g_eff sin phi (fix round 4, H4-m2); the planar failed-ignition rows read n/a for
    a run without a failed ignition, whose apex is not a fall-back coast's (V4-2), and the
    shaft impact label names the apex case (H4-m2, C4-m1)."""
    pad = {"facility_length_m": 0.0}
    lm = {**LM_METRICS, "electrical_power_peak_W": 2.6e9}
    er = _fake_er({"pad": pad, "lm": lm, "lm_cmd": CMD_METRICS})
    plain = _fake_er({"pad": pad, "silo": {"facility_length_m": 150.0}})
    keys = [key for _label, _source, key in summary.LINEAR_MOTOR_ROWS]
    assert set(keys) == set(LINEAR_MOTOR_METRICS)
    for rows_of in (summary.variant_rows, summary.planar_variant_rows):
        rows = list(rows_of(er))  # type: ignore[arg-type]
        at = next(i for i, row in enumerate(rows) if row[2] == "facility_length_m")
        assert rows[at + 1 : at + 1 + len(keys)] == list(summary.LINEAR_MOTOR_ROWS)
        assert not set(summary.LINEAR_MOTOR_ROWS) & set(rows_of(plain))  # type: ignore[arg-type]
    cell = summary._variant_cell
    cells = {
        key: tuple(cell(er, n, source, key) for n in ("pad", "lm", "lm_cmd"))  # type: ignore[arg-type]
        for _label, source, key in summary.LINEAR_MOTOR_ROWS
    }
    assert all(pad_cell == "-" for pad_cell, _lm, _cmd in cells.values())
    assert cells["push_control_law"][1:] == ("force", "acceleration")
    assert cells["push_accel_command_mps2"][1] == "none" and cells["push_stop_taper_m"][1] == "none"
    assert cells["push_release_speed_mps"][1:] == ("none", "90")
    assert cells["push_cap_bound"][1:] == ("n/a", "False")
    assert cells["release_trigger"][1] == "track_end" and cells["push_power_limited"][1] == "True"
    assert cells["push_force_max_N"][1] == "2.243e+07"
    assert cells["braking_time_s"][1] == "n/a"  # absent from these metrics
    labels = " ".join(label for label, _s, _k in summary.LINEAR_MOTOR_ROWS)
    assert "(a mean over the whole push: the rise, any capped or power-limited part" in labels
    assert (
        "felt axial g at the end of the rise [g0] (at t_r: where the acceleration law's" in labels
    )
    assert "else a capped value" in labels and "for a stalled push" in labels
    assert "rise time t_r [s] (of the force limit, or of the acceleration command)" in labels
    assert "less than the stroke L: released before the track end" in labels
    assert "holds no constant acceleration" not in labels and "not a held value" not in labels
    assert "False: a_cmd held after the rise" not in labels
    assert "negative when a_b < g_eff sin phi: the brake then holds the carriage up" in labels
    assert "(1/2) m_c v^2 (1 - g_eff sin phi / a_b); negative when a_b < g_eff sin phi" in labels
    # fix round 4 (V4-2, H4-m2, C4-m1): the planar failed-ignition rows
    burn = {"apex_alt_m": -92.8, "apex_t_s": 1.1, "impact_t_s": None}
    fail = {"failed_stage": "stage1", "apex_alt_m": -38.35, "apex_t_s": 3.0}
    er_fail = _fake_er({"pad": pad, "burn_turn": burn, "lm_fall": fail})
    failed_rows = [
        r for r in summary.planar_variant_rows(er_fail) if r in summary.PLANAR_FAILED_ROWS
    ]  # type: ignore[arg-type]
    assert failed_rows == list(summary.PLANAR_FAILED_ROWS)
    apex_row = next(r for r in failed_rows if r[2] == "apex_alt_m")
    planar_cells = [summary._planar_cell(er_fail.runs, er_fail, n, apex_row) for n in er_fail.runs]  # type: ignore[arg-type]
    assert planar_cells == ["n/a", "n/a", "-38.35"]
    assert summary.PLANAR_SHAFT_IMPACT_LABEL == (
        "  impact speed |v_rel| at the ground, or inside the shaft after a fall back there "
        "(shaft_fallback flag): on the parked carriage, or at the apex (about 0) when the "
        "carriage parks above it [m/s]"
    )
    # a linear-motor run without a push record (its guidance failed): n/a, never '-'
    failed = _fake_run("lm_failed", {"facility_length_m": None})
    failed.resolved.run.assist = LinearMotorConfig.model_validate(LM_CONFIG)
    er_failed = _fake_er({"pad": pad})
    er_failed.runs["lm_failed"] = failed
    assert summary._has_linear_motor(er_failed.runs)  # type: ignore[arg-type]
    failed_cells = {
        cell(er_failed, n, source, key)  # type: ignore[arg-type]
        for n in ("lm_failed",)
        for _label, source, key in summary.LINEAR_MOTOR_ROWS
    }
    assert failed_cells == {"n/a"}
    assert cell(er_failed, "pad", summary.LINEAR_MOTOR_SOURCE, "push_control_law") == "-"  # type: ignore[arg-type]


# ------------------------------------------------------------------- the figure


def test_the_drive_curve_is_drawn_for_a_linear_motor_run_only(
    f9_vehicle: Vehicle, tmp_path: Path
) -> None:
    """``plots.write_plots`` of a 1-D linear-motor run writes <run>_drive_curve.png beside
    its panels (drive force and power against the track speed; ``drive_curve_rows`` are
    its sampled ASSIST rows); the figure marks F_max on the force axis and P_max on the
    power axis (dashed, the axes topped at DRIVE_CURVE_FORCE_HEADROOM F_max and
    DRIVE_CURVE_POWER_HEADROOM P_max), the power cap P_max / sdot from the corner on, the
    corner speed (dotted) and, for a run with the release_speed_not_reached flag, its
    release speed '(not reached)'; a two-line title with the law; the legend below the
    axes; a constant_accel run's plot list is the panels alone; a stalled push's release
    speed is marked as set, with no release (fix round 4, V4-3)."""
    specs = {name: IgnitionSpec() for name in f9_vehicle.stage_names}
    specs[f9_vehicle.stage_names[0]] = IgnitionSpec(0.5)
    f_max = f9_vehicle.liftoff_mass_kg() * (3.0 * G0_MPS2 + G)
    common: dict[str, Any] = {
        "vehicle": f9_vehicle,
        "ignition": specs,
        "gravity": InverseSquareGravity(MU_EARTH_M3S2),
        "g_eff_mps2": G,
        "track": StraightTrack(L, VERTICAL, -L),
        "start": None,
        "end": "stage1_burnout",
        "settings": IntegratorSettings(rtol=1e-10),
    }
    p_max = f_max * 50.0
    lm = LinearMotorAssist(
        "force", f_max, p_max, 0.5, 0.0, 5.0 * G0_MPS2, g_eff_mps2=G, release_speed_mps=90.0
    )
    result = sim.simulate(assist=lm, **common)
    assert any(f.startswith(RELEASE_SPEED_NOT_REACHED) for f in result.flags)
    written = plots.write_plots(result, tmp_path / "plots", "lm")
    curve = tmp_path / "plots" / "lm_drive_curve.png"
    assert curve in written and curve.read_bytes().startswith(b"\x89PNG")
    rows = plots.drive_curve_rows(result, "v_mps")
    assert rows is not None
    speed, force, power = rows
    assert max(force) <= f_max * (1.0 + 1e-12) and max(power) <= p_max * (1.0 + 1e-12)
    assert speed[0] == 0.0 and math.isclose(max(speed), result.metrics["exit_speed_mps"])
    fig = plots.drive_curve_figure(result, "lm", "v_mps")
    assert fig is not None
    ax, twin = fig.axes[0], fig.axes[1]
    assert ax.get_xlabel() == "speed along the track sdot [m/s]"
    assert ax.get_title() == "lm (force law)\nlinear-motor drive force and power against speed"
    f_line = next(ln for ln in ax.get_lines() if ln.get_label().startswith("F_max = "))
    assert math.isclose(f_line.get_ydata()[0], f_max / 1e6, rel_tol=1e-12)
    p_line = next(ln for ln in twin.get_lines() if ln.get_label().startswith("P_max = "))
    assert math.isclose(p_line.get_ydata()[0], p_max / 1e6, rel_tol=1e-12)
    assert math.isclose(ax.get_ylim()[1], f_max / 1e6 * plots.DRIVE_CURVE_FORCE_HEADROOM)
    assert math.isclose(twin.get_ylim()[1], p_max / 1e6 * plots.DRIVE_CURVE_POWER_HEADROOM)
    corner = next(ln for ln in ax.get_lines() if ln.get_label().startswith("corner speed"))
    assert corner.get_xdata()[0] == result.metrics["push_corner_speed_mps"] == 50.0
    cap = next(ln for ln in ax.get_lines() if ln.get_label().startswith("power cap"))
    v_cap = cap.get_xdata()
    assert v_cap[0] == 50.0 and math.isclose(cap.get_ydata()[-1], p_max / v_cap[-1] / 1e6)
    release = next(ln for ln in ax.get_lines() if ln.get_label().startswith("release speed"))
    assert release.get_label() == "release speed 90 m/s (not reached)"
    legend = fig.legends[0]
    assert {t.get_text() for t in legend.get_texts()} >= {
        f_line.get_label(),
        "drive force F (sampled rows)",
    }
    canvas = FigureCanvasAgg(fig)  # the legend below the axes and labels (round 2, H2-m5)
    canvas.draw()
    renderer = canvas.get_renderer()
    legend_top = legend.get_window_extent(renderer).y1
    assert legend_top <= min(a.get_tightbbox(renderer).y0 for a in (ax, twin))
    stall_lm = LinearMotorAssist(
        "acceleration",
        3e6,
        2e9,
        0.5,
        0.0,
        5.0 * G0_MPS2,
        accel_command_mps2=3.0 * G0_MPS2,
        g_eff_mps2=G,
        release_speed_mps=50.0,
    )
    stalled = sim.simulate(assist=stall_lm, **common)
    assert stalled.status == "drive_stall" and stalled.metrics["release_trigger"] is None
    stall_fig = plots.drive_curve_figure(stalled, "stall", "v_mps")
    assert stall_fig is not None
    stall_line = next(
        ln for ln in stall_fig.axes[0].get_lines() if ln.get_label().startswith("release speed")
    )
    assert stall_line.get_label() == "release speed set 50 m/s (no release: status drive_stall)"
    ca = sim.simulate(assist=ConstantAccelAssist(3.0 * G0_MPS2, 0.0, 5.0 * G0_MPS2), **common)
    assert plots.drive_curve_rows(ca, "v_mps") is None
    ca_written = plots.write_plots(ca, tmp_path / "plots_ca", "ca")
    assert [p.stem for p in ca_written] == [
        f"ca_{quantity}" for quantity, _c, _l in plots.plot_panels(ca)
    ]


# ------------------------------------------------- a real planar linear-motor directory


def _experiment() -> dict[str, Any]:
    """A fixed-guidance planar experiment from silo_screening_2d's shared blocks (a 0.5 s
    sample step): the pad, silo_cold (constant_accel), lm (force law, released at the
    track end), lm_target (the same drive released at 60 m/s before the mouth) and
    lm_fall (released at 15 m/s about 96 m down with stage 1's ignition failed, end impact:
    it falls back inside the shaft onto its parked carriage, fix round 3) and lm_stall (an
    acceleration-law drive whose F_max of 3 MN cannot lift the stack: status drive_stall,
    fix round 4)."""
    exp = yaml.safe_load((REPO / "experiments" / "silo_screening_2d.yaml").read_text("utf-8"))
    exp = copy.deepcopy(exp)
    exp["name"] = "lm_readers"
    exp["search"].update(
        {
            "figure_of_merit": "none",
            "fixed_gamma_star_deg": 20.0,
            "fixed_ltg_a": 0.75679,
            "fixed_ltg_b_per_s": 2.19338e-3,
        }
    )
    exp["baseline"]["integrator"]["sample_dt_s"] = 0.5
    silo = exp["variants"]["silo_cold"]
    base = {k: v for k, v in silo.items() if k != "assist"}
    exp["variants"] = {
        "silo_cold": silo,
        "lm": {**base, "assist": LM_CONFIG},
        "lm_target": {**base, "assist": {**LM_CONFIG, "release_speed_mps": 60}},
        "lm_fall": {
            **base,
            "end": "impact",
            "ignition": {"stage1": {"t_ign_s": 0.5, "fails": True}},
            "assist": {**LM_CONFIG, "release_speed_mps": 15},
        },
        "lm_stall": {**base, "assist": {**CMD_CONFIG, "force_max_kN": 3000}},
    }
    for key in ("sweeps", "bounds", "sensitivity"):
        exp.pop(key, None)
    return exp


@pytest.fixture(scope="module")
def lm_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The written results directory of ``_experiment`` (with plots) under a temporary
    root, never results/."""
    veh = yaml.safe_load(
        (REPO / "configs" / "vehicles" / "generic_f9_class_2d.yaml").read_text("utf-8")
    )
    resolved = resolve_experiment(_experiment(), veh)
    root = tmp_path_factory.mktemp("lm_readers")
    _er, out = sim.run_experiment(resolved, root, plots=True, repo_root=REPO)
    return Path(out)


@pytest.mark.slow
def test_pages_summary_and_plots_of_a_linear_motor_directory(lm_dir: Path, tmp_path: Path) -> None:
    """A real directory: the replay page's details and drive caveat name each linear
    motor's law, limits, release and measured speed at release (no 'g net push' for
    them, and no claim that the push holds no acceleration); the close-up note of
    lm_target says it was released below the mouth and where it passed the mouth (its
    shaft_exit event), and the vented-shaft note is limited to the push; the scene
    payload's lm runs have no acceleration and a drive label, and lm_target its
    early-release caveat in the caveats and the frame caveat; the pages are written
    (strict JSON); summary.md has the linear-motor rows ('-' for pad and silo_cold,
    target_speed for lm_target and lm_fall, the early-release line among the assumptions)
    and, for lm_fall, the failed-ignition rows with the impact-speed label of a fall back in
    the shaft, its flag and its shaft assumption line; lm_fall's close-up note says its
    impact is logged on its parked carriage; the drive curve PNG exists for the linear
    motors only (fix round 3); the scene payload of pad and lm_fall swaps the display-only
    carriage item (fix round 4, V4-1), and that of pad and lm_stall carries the no-release
    caveat and frame line, while lm_stall's push has no push load (V4-3)."""
    data = replay.replay_data(lm_dir, ["pad", "silo_cold", "lm", "lm_target"])
    detail = {r["key"]: r["detail"] for r in data["runs"]}
    assert "3 g net push" in detail["silo_cold"]
    short = "linear motor (force law, F_max 22.43 MN, P_max 1300 MW)"
    for name in ("lm", "lm_target"):
        assert short in detail[name] and "net push" not in detail[name]
    assert re.search(
        r"released at 60\.0 m/s \(measured\) 3\d\.\d m below the mouth", detail["lm_target"]
    )
    caveats = " ".join(data["meta"]["caveats"])
    assert "The drive of lm_target is a linear motor" in caveats
    assert caveats.count(FORCE_ACCEL) == 2 and "holds no constant acceleration" not in caveats
    assert "the shaft has no air drag (on the push only for lm_target)" in caveats
    note = next(n for n in data["meta"]["closeup_notes"] if n.startswith("lm_target "))
    assert re.fullmatch(
        r"lm_target starts 100 m below ground and is released on reaching its release speed, "
        r"60\.0 m/s, after \d\.\d s, 3\d\.\d m below the silo mouth; it passes the mouth at "
        r"5\d\.\d m/s at T\+0\.\d s, within 1 m of the shaft axis\.",
        note,
    ), note
    assert any(
        "inside it on the push; after the release below the mouth of lm_target" in n
        for n in data["meta"]["closeup_notes"]
    )
    assert any(
        n.startswith("The exit speed of lm_target is its speed at release")
        for n in data["meta"]["results_notes"]
    )
    page = replay.write_replay_page(lm_dir, ["pad", "lm_target"], tmp_path / "replay.html")
    assert page.read_text(encoding="utf-8").isascii()
    payload = scene.scene_payload(lm_dir, ["pad", "lm_target"], display_dir=DISPLAY_DIR)
    assist = payload["runs"][1]["assist"]
    assert assist["net_accel_mps2"] is None and assist["drive"]["release_trigger"] == "target_speed"
    assert assist["drive"]["label"].startswith(CLAUSE)
    assert any(c.startswith("lm_target is released 3") for c in payload["caveats"])
    assert "lm_target: released below the mouth; the carriage drawn" in payload["frame_caveat"]
    json.dumps(payload, allow_nan=False)
    text = (lm_dir / "summary.md").read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if "release trigger (track_end" in line)
    assert [c.strip() for c in row.strip("|").split("|")][1:] == [
        "-",
        "-",
        "track_end",
        "target_speed",
        "target_speed",
        "n/a",
    ]
    assert "linear_motor: released at the release speed 60 m/s at s = " in text
    # fix round 3 (P3-M1, P3-M2): lm_fall falls back onto its parked carriage
    assert summary.PLANAR_SHAFT_IMPACT_LABEL in text
    assert "onto the parked carriage at z = " in text
    assert sim.PLANAR_FAILED_IGNITION_SHAFT_ASSUMPTIONS[0] in text
    fall = json.loads((lm_dir / "metrics.json").read_text(encoding="utf-8"))["runs"]["lm_fall"]
    park = -L + fall["release_position_m"] + fall["braking_distance_m"]
    assert fall["status"] == "impact" and abs(fall["final_alt_m"] - park) <= 1e-6
    assert fall["impact_speed_mps"] > 5.0
    fell = replay.replay_data(lm_dir, ["pad", "lm_fall"])
    note = next(n for n in fell["meta"]["closeup_notes"] if n.startswith("lm_fall "))
    assert note.endswith(
        f"its impact logged {abs(park):.1f} m below the mouth on its parked carriage, the "
        "floor of the flight model in the shaft."
    ), note
    assert "at the ground, or inside the shaft after a fall back there" in text
    pngs = {p.name for p in (lm_dir / "plots").glob("*_drive_curve.png")}
    assert pngs == {
        "lm_drive_curve.png",
        "lm_target_drive_curve.png",
        "lm_fall_drive_curve.png",
        "lm_stall_drive_curve.png",
    }
    # fix round 4 (V4-1): the display-only carriage item of a selection with a fall back
    fall_payload = scene.scene_payload(lm_dir, ["pad", "lm_fall"], display_dir=DISPLAY_DIR)
    assert fall_payload["display_only"][4] == scene.DISPLAY_ONLY_SHAFT_CARRIAGE_ITEM
    assert payload["display_only"] == list(scene.DISPLAY_ONLY)
    # fix round 4 (V4-3): a stalled push
    stall_payload = scene.scene_payload(lm_dir, ["pad", "lm_stall"], display_dir=DISPLAY_DIR)
    assert any(c.startswith("lm_stall was never released") for c in stall_payload["caveats"])
    assert "lm_stall: never released; the carriage drawn" in stall_payload["frame_caveat"]
    stall_run = plots.read_animation_run(
        lm_dir, "lm_stall", json.loads((lm_dir / "metrics.json").read_text(encoding="utf-8"))
    )
    assert stall_run.push_peak_g() is None


@pytest.mark.slow
def test_the_app_lists_and_panels_a_linear_motor_directory(lm_dir: Path) -> None:
    """The app's run browser row of the directory (complete, playable, planar) and its
    results panel for the pair pad and lm_target (``app.results_panel`` with the shipped
    basis; no exception): the push text is the replay's detail, with the linear motor's
    law and limits, and the caveats word the force law's acceleration as not prescribed;
    the panel's caveats carry lm_target's early-release caveat and the video footer of
    pad and lm_target (``app.video_footer``, the panel's ``video_footer``) ends with its
    frame line, while the video footer of pad and lm (released at the track end) is
    plots.animation_caveats' lines alone and the panel's caveats name nothing below the
    mouth (fix round 2, C2-M1, H2-M2, V2-1); the footer of pad and lm_fall ends with the
    early-release line and the fall-back line (fix round 3, H3-m1) and its panel's
    display-only list carries the fall-back carriage item (fix round 4, V4-1); the footer
    of pad and lm_stall names no push load and ends with the no-release line (V4-3)."""
    exp, ts = lm_dir.parent.name, lm_dir.name
    row = app.directory_row(lm_dir, exp, ts, running=False)
    assert row["state"] == app.DIR_COMPLETE and row["playable"] and row["model"] == "planar_2d"
    metrics = json.loads((lm_dir / "metrics.json").read_text(encoding="utf-8"))
    config = yaml.safe_load((lm_dir / "resolved_config.yaml").read_text(encoding="utf-8"))
    basis = app.load_basis(REPO, app.take_server_start(REPO))
    panel = app.results_panel(lm_dir, exp, ts, basis, metrics, config, chosen=["pad", "lm_target"])
    push = panel["panel"]["push"]
    assert push is not None and push["model"] == "linear_motor"
    assert "linear motor (force law, F_max 22.43 MN, P_max 1300 MW)" in push["text"]
    assert push["net_accel_g"] is None
    caveats = json.dumps(panel["panel"])
    assert FORCE_ACCEL in caveats and "holds no constant acceleration" not in caveats
    # fix round 2 (C2-M1, H2-M2, V2-1): the early-release caveat reaches the panel's list
    # (the embedded scene hides its own) and the frame line every MP4 frame's footer
    assert any(c.startswith("lm_target is released 3") for c in panel["panel"]["caveats"])
    footer = app.video_footer(lm_dir, ["pad", "lm_target"], metrics, config)
    assert footer[-1] == scene.early_release_frame_text(["lm_target"])
    assert panel["panel"]["video_footer"] == footer
    vehicle = str(config["vehicle"]["name"])
    shown = [plots.read_animation_run(lm_dir, n, metrics) for n in ("pad", "lm")]
    plain = list(plots.animation_caveats(shown, vehicle, None, width_px=None))
    assert app.video_footer(lm_dir, ["pad", "lm"], metrics, config) == plain  # unchanged
    at_end = app.results_panel(lm_dir, exp, ts, basis, metrics, config, chosen=["pad", "lm"])
    assert not any("below the mouth" in c for c in at_end["panel"]["caveats"])
    # fix round 3 (H3-m1): the fall back's frame line reaches every MP4 frame's footer
    fell = app.video_footer(lm_dir, ["pad", "lm_fall"], metrics, config)
    assert fell[-2:] == [
        scene.early_release_frame_text(["lm_fall"]),
        scene.fall_back_frame_text(["lm_fall"]),
    ]
    fall_panel = app.results_panel(
        lm_dir, exp, ts, basis, metrics, config, chosen=["pad", "lm_fall"]
    )
    assert fall_panel["panel"]["display_only"][4] == scene.DISPLAY_ONLY_SHAFT_CARRIAGE_ITEM
    assert panel["panel"]["display_only"] == list(scene.DISPLAY_ONLY)
    stalled = app.video_footer(lm_dir, ["pad", "lm_stall"], metrics, config)
    assert not any("push load" in line for line in stalled)
    assert stalled[-1] == scene.no_release_frame_text(["lm_stall"])
