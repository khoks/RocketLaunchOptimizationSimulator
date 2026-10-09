"""Shared inputs of the structural-model tests (SP7 step S2): the two structure files, the
gate vehicle at the reference payload, the track's g_eff, a synthetic pad flight and the
analytic headline push.

The synthetic pad flight is built here from closed forms, never read from results/: a 2 s
hold with a linear thrust ramp, a stage-1 burn at full mass flow whose delivered thrust
rises linearly from its sea-level to its vacuum value over the first 60 s (no drag), an
11 s staging coast, and the stage-2 burn with the fairing dropped 34.5 s after its
ignition. Its rows carry the planar time series' columns the adapter reads (t_s, phase,
stage, felt_axial_g, m_kg, thrust_N) and its events the planar event names. It is a test
input with the gate vehicle's masses and thrusts, not a model of the gate's flight.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from launchsim import sim, structure
from launchsim.assist.constant_accel import ConstantAccelAssist
from launchsim.assist.track import StraightTrack
from launchsim.config import StructureConfig, VehicleConfig
from launchsim.constants import G0_MPS2
from launchsim.dynamics import g_eff_track, planar_rotation_rate
from launchsim.vehicle import Vehicle, with_offload, with_payload

REPO = Path(__file__).resolve().parents[1]
GATE_STRUCTURE = REPO / "configs" / "structures" / "generic_f9_class_2d.yaml"
README_STRUCTURE = REPO / "configs" / "structures" / "generic_f9_class_2d_readme_loads.yaml"
GATE_VEHICLE = REPO / "configs" / "vehicles" / "generic_f9_class_2d.yaml"
README_VEHICLE = REPO / "configs" / "vehicles" / "generic_f9_class_2d_readme_loads.yaml"

SP1_RECORD_PATH = REPO / "tests" / "data" / "silo_offload_2d_record.json"
"""SP1's solved stage-1 offloads at full precision (D-SP7-30): the gate's headline and
penalty rows and the README-loads fork's bridge, each at its pad's P_ref, copied once from
the two runs' untracked metrics.json (git b3150c1754ee, clean; tests never read results/)."""


def sp1_record() -> dict[str, Any]:
    """tests/data/silo_offload_2d_record.json as a mapping."""
    with SP1_RECORD_PATH.open(encoding="utf-8") as fh:
        data = json.load(fh)
    assert isinstance(data, dict)
    return data


_SP1 = sp1_record()
P_REF_KG: float = _SP1["gate"]["reference_payload_kg"]
"""SP1's reference payload P_ref [kg], the gate pad baseline's P* (26,054.396243494975 kg,
the record's gate block): the slow search test's check on the flown pad and the synthetic
tests' payload."""
HEADLINE_OFFLOAD_KG: float = _SP1["gate"]["stage1_offload_cases"][0]["offload_kg"]
"""SP1's headline stage-1 offload x* [kg] (silo_cold_s1: constant_accel 3 g0 net, 100 m,
cold, at P_ref; 41,262.90803733282 kg, the record's first gate row), the sizing input of
design 4.2.6; equal to constants.SP1_PENALTY_OFFLOAD_KG[0] (a test)."""
README_P_REF_KG: float = _SP1["readme_loads"]["reference_payload_kg"]
"""The README-loads fork's P_ref [kg] (its pad's P*, 24,700.013061881455 kg)."""
README_BRIDGE_OFFLOAD_KG: float = _SP1["readme_loads"]["stage1_offload_cases"][0]["offload_kg"]
"""The README-loads fork's SP1 bridge offload x* [kg] (silo_cold_s1 at its own P_ref,
36,006.44430169878 kg)."""
STROKE_M = 100.0
NET_ACCEL_G = 3.0
G_EFF_MPS2 = g_eff_track(planar_rotation_rate(math.radians(28.5), math.radians(90.0)))
"""The gate site's track g_eff [m/s^2] (28.5 deg, east): 9.772092 (survey 05)."""


def load_yaml(path: Path) -> dict[str, Any]:
    """A YAML mapping read as UTF-8."""
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict)
    return data


def structure_config(path: Path = GATE_STRUCTURE) -> StructureConfig:
    """A validated structure file."""
    return StructureConfig.model_validate(load_yaml(path))


def vehicle(path: Path = GATE_VEHICLE, payload_kg: float = P_REF_KG) -> Vehicle:
    """A vehicle file's Vehicle at a payload [kg]."""
    return with_payload(VehicleConfig.model_validate(load_yaml(path)).to_vehicle(), payload_kg)


def synthetic_pad_result(
    veh: Vehicle,
    dt_s: float = 0.5,
    hold_s: float = 2.0,
    coast_s: float = 11.0,
    fairing_after_s: float = 34.5,
    stage2_stop_fraction: float = 1.0,
) -> sim.Result:
    """A synthetic planar pad Result of ``veh`` (see the module docstring): rows every
    dt_s [s] plus each phase's end; stage 2 burns stage2_stop_fraction of its load."""
    s1, s2 = veh.stages
    c1 = G0_MPS2 * s1.engine.isp_vac_s
    c2 = G0_MPS2 * s2.engine.isp_vac_s
    t_vac1 = s1.thrust_vac_total_N
    t_sl1 = s1.n_engines * 845.2e3
    mdot1 = t_vac1 / c1
    rows: list[dict[str, Any]] = []
    m0 = veh.stack_mass_kg(0)
    g_eff = G_EFF_MPS2

    def add(t: float, phase: str, stage: str, n: float, m: float, thrust: float) -> None:
        rows.append(
            {
                "t_s": t,
                "phase": phase,
                "stage": stage,
                "felt_axial_g": n,
                "m_kg": m,
                "thrust_N": thrust,
            }
        )

    # hold: a linear thrust ramp over hold_s; the clamp convention n = g_eff/g0
    hold_t = np.append(np.arange(-hold_s, 0.0, dt_s), 0.0)
    for t in hold_t:
        frac = (t + hold_s) / hold_s
        burned = mdot1 * (t + hold_s) ** 2 / (2.0 * hold_s)
        add(float(t), "HOLD", s1.name, g_eff / G0_MPS2, m0 - burned, frac * t_sl1)
    m_rel = m0 - mdot1 * hold_s / 2.0
    prop_rel = s1.propellant_mass_kg - mdot1 * hold_s / 2.0
    t_b = prop_rel / mdot1

    def thrust1(t: float) -> float:
        return t_sl1 + (t_vac1 - t_sl1) * min(1.0, t / 60.0)

    flight_t = np.append(np.arange(0.0, t_b, dt_s), t_b)
    for t in flight_t:
        m = m_rel - mdot1 * t
        if t == t_b:
            m = m_rel - prop_rel
        phase = "VERTICAL_RISE" if t < 10.0 else "GRAVITY_TURN"
        add(float(t), phase, s1.name, thrust1(t) / (m * G0_MPS2), m, thrust1(t))
    upper = s2.wet_mass_kg + veh.fairing_mass_kg + veh.payload_mass_kg
    for t in np.arange(t_b, t_b + coast_s, 1.0):
        add(float(t), "COAST_STAGING", s2.name, 0.0, upper, 0.0)
    t_ign2 = t_b + coast_s
    mdot2 = s2.thrust_vac_total_N / c2
    t_end2 = stage2_stop_fraction * s2.propellant_mass_kg / mdot2
    t_fair = t_ign2 + fairing_after_s
    m_fair = upper - mdot2 * fairing_after_s
    burn_t = np.append(np.arange(0.0, t_end2, dt_s), t_end2)
    for tt in burn_t:
        t = t_ign2 + tt
        m = upper - mdot2 * tt
        if t >= t_fair:
            if t == t_fair:
                add(
                    float(t),
                    "LTG_BURN",
                    s2.name,
                    s2.thrust_vac_total_N / (m * G0_MPS2),
                    m,
                    s2.thrust_vac_total_N,
                )
            m -= veh.fairing_mass_kg
        add(
            float(t),
            "LTG_BURN",
            s2.name,
            s2.thrust_vac_total_N / (m * G0_MPS2),
            m,
            s2.thrust_vac_total_N,
        )
    ts = pd.DataFrame(rows)
    events = pd.DataFrame(
        [
            {"t_s": -hold_s, "event": "ignition", "phase": "HOLD", "stage": s1.name, "m_kg": m0},
            {"t_s": 0.0, "event": "release", "phase": "HOLD", "stage": s1.name, "m_kg": m_rel},
            {
                "t_s": t_b,
                "event": "propellant",
                "phase": "GRAVITY_TURN",
                "stage": s1.name,
                "m_kg": m_rel - prop_rel,
            },
            {
                "t_s": t_b,
                "event": "staging",
                "phase": "COAST_STAGING",
                "stage": s2.name,
                "m_kg": upper,
            },
            {
                "t_s": t_fair,
                "event": "fairing",
                "phase": "LTG_BURN",
                "stage": s2.name,
                "m_kg": m_fair,
            },
        ]
    )
    return sim.Result(
        metrics={},
        timeseries=ts,
        loss_budget=None,
        assist_budget=None,
        assumptions=[],
        phases=[],
        status="inserted",  # type: ignore[arg-type]
        flags=[],
        events=events,
        model="planar_2d",
    )


def headline_push(
    veh: Vehicle,
    layout: structure.StackLayout,
    offload_kg: float = HEADLINE_OFFLOAD_KG,
    net_accel_g: float = NET_ACCEL_G,
    stroke_m: float = STROKE_M,
    stage1_ignition_s: float | None = None,
) -> structure.PushLoad:
    """The analytic constant_accel push of ``veh`` offloaded by offload_kg on stage 1 (a
    vertical silo of stroke_m at net_accel_g, cold unless stage1_ignition_s is given)."""
    assist = ConstantAccelAssist(
        net_accel_mps2=net_accel_g * G0_MPS2, carriage_mass_kg=0.0, brake_decel_mps2=5.0 * G0_MPS2
    )
    track = StraightTrack(length_m=stroke_m, start_altitude_m=-stroke_m)
    flown = with_offload(veh, "stage1", offload_kg) if offload_kg > 0.0 else veh
    return sim.constant_accel_push_load(
        flown, assist, track, layout, g_eff_mps2=G_EFF_MPS2, stage1_ignition_s=stage1_ignition_s
    )
