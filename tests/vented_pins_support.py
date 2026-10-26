"""Byte pins of vented linear-motor and constant_accel pushes (SP7 step S5).

SP7 step S5 adds the sealed shaft to the linear motor. A vented linear-motor run and every
constant_accel run must stay byte-identical to the code before it (the brief; D-SP7-26,
D-SP7-27). This module builds a fixed set of such runs with the API that existed before
S5 (no sealed-shaft name is used here) and reduces each to sha256 digests of its parts:
the integrator's ASSIST states bit for bit (every phase of a 1-D run), the metrics in
their order (``json.dumps`` writes each float's shortest round-trip repr, so the digest
moves with any bit), the sampled time series and events, the assumption lines, the flags,
the status and the assist energy budget. The digests were captured from the commit
before S5, e12e524 (SOURCE_COMMIT; ``capture``, run from a scratch script against that
commit's ``src``, extracted with ``git archive e12e524 src``; tests/data/vented_pins.json,
with the numeric environment they hold in). tests/test_sealed_shaft.py compares a fresh
run with them in that environment (the exact golden tier's EXACT_ENV_KEYS) and skips the
comparison elsewhere, where a 1-ulp change of the floating-point path moves every
integrated bit; the metric key lists are compared everywhere.

The runs: the generic F9 in 1-D through ``sim.simulate`` (rtol 1e-11): the force law cold
with its power phase, the force law hot on a 20 t carriage with f_imp 0.5, the
acceleration law with a 20 m stop taper, the force law released at 60 m/s, and
constant_accel at 3 g0 cold; the gate vehicle's planar flown push (``sim.
flown_push_trace``, the S4b path, through the config and ``build_assist``) of a 30 m
force-law push: its phases bit for bit, events, flags, status and the drive's assumption
lines, and the planar track metrics of that push (``metrics_planar.planar_track_metrics``
on the flown push with its sampled ASSIST rows, the code S5 changed), its sampled time
series and its assist energy budget, with the metric keys.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from launchsim import sim
from launchsim.assist.constant_accel import ConstantAccelAssist
from launchsim.assist.linear_motor import LinearMotorAssist
from launchsim.assist.track import VERTICAL, StraightTrack
from launchsim.config import VehicleConfig, resolve_experiment
from launchsim.constants import G0_MPS2, MU_EARTH_M3S2, R_EARTH_M
from launchsim.dynamics import InverseSquareGravity
from launchsim.losses import assist_energy_budget
from launchsim.metrics_planar import planar_track_metrics, sample_trace_planar
from launchsim.phases import IgnitionSpec, IntegratorSettings
from launchsim.vehicle import Vehicle, with_payload

REPO = Path(__file__).resolve().parents[1]
PINS_PATH = REPO / "tests" / "data" / "vented_pins.json"
SOURCE_COMMIT = "e12e5247a18e12f5e63891f5eefe8df364e083cc"
"""The commit the pins were captured from: the last before SP7 step S5 (S4b's trackers).
A re-capture runs ``capture`` against this commit's ``src`` (``git archive e12e524 src``),
never against HEAD once S5 is committed."""
F9_PATH = REPO / "configs" / "vehicles" / "generic_f9_class.yaml"
GATE_EXPERIMENT = REPO / "experiments" / "silo_offload_2d.yaml"
SP1_RECORD_PATH = REPO / "tests" / "data" / "silo_offload_2d_record.json"
G = MU_EARTH_M3S2 / R_EARTH_M**2
"""The 1-D track's g_eff [m/s^2] (omega_p = 0)."""
L_M = 100.0
SILO = StraightTrack(L_M, VERTICAL, -L_M)
SETTINGS = IntegratorSettings(rtol=1e-11)
A_BRAKE = 5.0 * G0_MPS2
COLD = IgnitionSpec(0.5)
HOT = IgnitionSpec(-2.0, reference="push_start")
PLANAR_LM: dict[str, Any] = {
    "model": "linear_motor",
    "stroke_m": 30,
    "control": "force",
    "force_max_kN": 22000.0,
    "power_max_MW": 5000,
    "force_rise_time_s": 0.5,
    "brake_decel_g": 5,
    "drive_efficiency": 0.5,
    "track": {"angle_deg": 90, "exit_altitude_m": 0},
}
"""The planar pin's short force-law push (test_structure_linear_motor's LM)."""
PLANAR_COLD = {"stage1": {"t_ign_s": 0.5, "reference": "release"}}
PLANAR_SAMPLE_DT_S = 0.05
"""The sampling step [s] of the planar pin's track metrics and time series."""


def _yaml(path: Path) -> dict[str, Any]:
    """A YAML mapping read as UTF-8."""
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict)
    return data


def f9() -> Vehicle:
    """The generic F9 (configs/vehicles/generic_f9_class.yaml)."""
    return VehicleConfig.model_validate(_yaml(F9_PATH)).to_vehicle()


def _lm(**kw: Any) -> LinearMotorAssist:
    """A vented linear motor with the pins' brake (5 g0), efficiency 0.5 and g_eff."""
    base: dict[str, Any] = {
        "control": "force",
        "rise_time_s": 0.5,
        "carriage_mass_kg": 0.0,
        "brake_decel_mps2": A_BRAKE,
        "efficiency": 0.5,
        "g_eff_mps2": G,
    }
    base.update(kw)
    return LinearMotorAssist(**base)


def one_d_models(vehicle: Vehicle) -> dict[str, tuple[Any, IgnitionSpec]]:
    """The 1-D pinned runs: name -> (assist model, first-stage IgnitionSpec)."""
    m = vehicle.liftoff_mass_kg()
    f_cold = m * (3.0 * G0_MPS2 + G)
    m_c = 20_000.0
    f_hot = (m + m_c) * (3.0 * G0_MPS2 + G)
    a = 3.0 * G0_MPS2
    return {
        "lm_force_cold": (_lm(force_max_N=f_cold, power_max_W=f_cold * 50.0), COLD),
        "lm_force_hot_carriage": (
            _lm(
                force_max_N=f_hot,
                power_max_W=f_hot * 60.0,
                carriage_mass_kg=m_c,
                f_imp=0.5,
            ),
            HOT,
        ),
        "lm_accel_taper": (
            _lm(
                control="acceleration",
                force_max_N=2.0 * m * (a + G),
                power_max_W=2.0 * m * (a + G) * 200.0,
                accel_command_mps2=a,
                stop_taper_m=20.0,
            ),
            COLD,
        ),
        "lm_force_release": (
            _lm(force_max_N=f_cold, power_max_W=f_cold * 50.0, release_speed_mps=60.0),
            COLD,
        ),
        "ca_cold": (
            ConstantAccelAssist(
                net_accel_mps2=a, carriage_mass_kg=0.0, brake_decel_mps2=A_BRAKE, g_eff_mps2=G
            ),
            COLD,
        ),
    }


def simulate_1d(vehicle: Vehicle, model: Any, first: IgnitionSpec) -> sim.Result:
    """The 1-D run of the silo to stage-1 burnout (rtol 1e-11)."""
    specs = {name: IgnitionSpec() for name in vehicle.stage_names}
    specs[vehicle.stage_names[0]] = first
    return sim.simulate(
        vehicle=vehicle,
        ignition=specs,
        gravity=InverseSquareGravity(MU_EARTH_M3S2),
        g_eff_mps2=G,
        assist=model,
        track=SILO,
        start=None,
        end="stage1_burnout",
        settings=SETTINGS,
    )


def _sha(text: str | bytes) -> str:
    """sha256 hex of a text (UTF-8) or bytes."""
    data = text.encode("utf-8") if isinstance(text, str) else text
    return hashlib.sha256(data).hexdigest()


def _phase_bytes(phases: Any) -> bytes:
    """Every phase's kind, start time, times and states as raw float64 bytes."""
    out = bytearray()
    for res in phases:
        out += f"{res.spec.kind}|{res.spec.t0!r}|{res.ended_by}|".encode()
        out += np.ascontiguousarray(np.asarray(res.t, dtype=float)).tobytes()
        out += np.ascontiguousarray(np.asarray(res.y, dtype=float)).tobytes()
    return bytes(out)


def result_digests(result: sim.Result) -> dict[str, str]:
    """sha256 digests of a 1-D Result's parts (see the module docstring)."""
    budget = result.assist_budget
    return {
        "phases": _sha(_phase_bytes(result.phases)),
        "metrics": _sha(json.dumps(result.metrics, default=repr)),
        "timeseries": _sha(result.timeseries.to_csv(index=False)),
        "events": _sha(result.events.to_csv(index=False)),
        "assumptions": _sha("\n".join(result.assumptions)),
        "flags": _sha("\n".join(result.flags)),
        "status": _sha(str(result.status)),
        "assist_budget": _sha(
            "" if budget is None else json.dumps([float(x).hex() for x in vars(budget).values()])
        ),
    }


def planar_flown() -> dict[str, Any]:
    """The planar pin's flown push: silo_offload_2d's shared blocks with one variant (the
    30 m force-law push, cold), the gate vehicle at SP1's P_ref, flown alone by
    ``sim.flown_push_trace``; with the resolved drive and track, the vehicle and the
    track's g_eff (g_ref) [m/s^2]."""
    exp = _yaml(GATE_EXPERIMENT)
    veh = _yaml(REPO / exp["vehicle"])
    exp["variants"] = {"lm": {"assist": PLANAR_LM, "ignition": PLANAR_COLD}}
    exp["sweeps"] = []
    exp.pop("offload", None)
    exp.pop("sensitivity", None)
    start = resolve_experiment(exp, veh).variants["lm"]
    v0 = start.to_vehicle()
    setup = sim.planar_setup(start.run, v0)
    ctx = sim.search_context(setup, v0, start.run.end)
    record = json.loads(SP1_RECORD_PATH.read_text(encoding="utf-8"))
    vehicle = with_payload(v0, float(record["gate"]["reference_payload_kg"]))
    assert isinstance(setup.assist, LinearMotorAssist)
    return {
        "trace": sim.flown_push_trace(ctx, vehicle),
        "assist": setup.assist,
        "track": setup.track,
        "vehicle": vehicle,
        "g_ref": setup.env.g_ref_mps2,
    }


def planar_track_record(flown: dict[str, Any]) -> tuple[dict[str, Any], Any, Any]:
    """The planar flown push's track metrics (``planar_track_metrics``), its sampled time
    series (PLANAR_SAMPLE_DT_S) and its AssistEnergyBudget, as a planar run writes them
    (``sim.simulate_planar``'s calls, on the push alone)."""
    trace, assist = flown["trace"], flown["assist"]
    phases = trace.assist_phases()
    layout = phases[0].spec.params.layout
    budget = assist_energy_budget(phases, layout, assist.carriage_mass_kg, flown["g_ref"])
    frame = sample_trace_planar(trace, flown["vehicle"], PLANAR_SAMPLE_DT_S)
    metrics = planar_track_metrics(trace, assist, flown["track"], budget, frame)
    return metrics, frame, budget


def planar_digests() -> dict[str, str]:
    """sha256 digests of the planar flown push: its phases bit for bit, its events, flags
    and status, the resolved drive's assumption lines, and its track metrics, sampled
    time series and assist energy budget (``planar_track_record``)."""
    flown = planar_flown()
    trace, assist = flown["trace"], flown["assist"]
    metrics, frame, budget = planar_track_record(flown)
    events = [(e.name, e.t_s.hex(), e.phase, e.stage) for e in trace.events]
    return {
        "phases": _sha(_phase_bytes(trace.phases)),
        "events": _sha(json.dumps(events)),
        "flags": _sha("\n".join(trace.flags)),
        "status": _sha(str(trace.status)),
        "assumptions": _sha("\n".join(assist.assumptions())),
        "track_metrics": _sha(json.dumps(metrics, default=repr)),
        "timeseries": _sha(frame.to_csv(index=False)),
        "assist_budget": _sha(json.dumps([float(x).hex() for x in vars(budget).values()])),
    }


def all_digests() -> dict[str, dict[str, str]]:
    """Every pinned run's digests, by run name."""
    vehicle = f9()
    out = {
        name: result_digests(simulate_1d(vehicle, model, first))
        for name, (model, first) in one_d_models(vehicle).items()
    }
    out["lm_planar_flown"] = planar_digests()
    return out


def metric_keys() -> dict[str, list[str]]:
    """The metric keys, in order, of every 1-D pinned run and of the planar flown push's
    track metrics (``lm_planar_flown``)."""
    vehicle = f9()
    out = {
        name: list(simulate_1d(vehicle, model, first).metrics)
        for name, (model, first) in one_d_models(vehicle).items()
    }
    out["lm_planar_flown"] = list(planar_track_record(planar_flown())[0])
    return out


def capture(environment: dict[str, str]) -> dict[str, Any]:
    """The pins file's content: the environment, the digests and the metric keys."""
    return {
        "note": (
            "Digests of vented linear-motor and constant_accel pushes captured from the "
            "commit before SP7 step S5, e12e524 (source_commit; its src extracted with git "
            "archive; tests/vented_pins_support.py); compared exactly only in this "
            "environment's EXACT_ENV_KEYS."
        ),
        "source_commit": SOURCE_COMMIT,
        "environment": environment,
        "digests": all_digests(),
        "metric_keys": metric_keys(),
    }


def read_pins() -> dict[str, Any]:
    """tests/data/vented_pins.json as a mapping."""
    data = json.loads(PINS_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data
