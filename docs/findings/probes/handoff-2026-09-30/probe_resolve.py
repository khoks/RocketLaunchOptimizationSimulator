"""Probe: what the config layer accepts today for depth, ignition timing, propellant offload."""
import copy
import math
from pathlib import Path

import yaml

from launchsim.assist import build_assist
from launchsim.config import resolve_experiment

REPO = Path("D:/DEV/ClaudeProjects/SpaceRocketOptimization")


def load(p):
    with open(REPO / p, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


exp0 = load("experiments/silo_screening_2d.yaml")
veh = load("configs/vehicles/generic_f9_class_2d.yaml")
for k in ("sweeps", "sensitivity", "bounds"):
    exp0.pop(k, None)
SILO = copy.deepcopy(exp0["variants"]["silo_cold"]["assist"])


def tryres(label, exp):
    try:
        r = resolve_experiment(exp, veh)
        print(f"[OK]   {label}")
        return r
    except Exception as e:  # noqa: BLE001
        msg = str(e).replace("\n", " ")[:260]
        print(f"[FAIL] {label}: {type(e).__name__}: {msg}")
        return None


def track_info(run):
    a = run.run.assist
    from launchsim.constants import MU_EARTH_M3S2, R_EARTH_M  # noqa: F401
    model, track = build_assist(a, 9.7720917)
    v = math.sqrt(2 * a.net_accel_mps2 * a.stroke_m)
    t = math.sqrt(2 * a.stroke_m / a.net_accel_mps2)
    return (f"stroke={a.stroke_m} m, accel={a.net_accel_g} g, exit_alt={a.track.exit_altitude_m} m, "
            f"track start alt={track.start_altitude_m} m, exit alt={track.exit_altitude_m} m, "
            f"v_exit={v:.3f} m/s, t_push={t:.4f} s, brake={model.braking_distance_m(v):.2f} m")


print("== 1. depth (stroke) and exit speed")
for name, ov in {
    "depth50_3g": {"stroke_m": 50},
    "depth300_3g": {"stroke_m": 300},
    "depth200_same_v_as_100m_3g": {"stroke_m": 200, "net_accel_g": 1.5},
    "mouth_raised_10m": {"track": {"angle_deg": 90, "exit_altitude_m": 10}},
    "mouth_below_ground_-20m": {"track": {"angle_deg": 90, "exit_altitude_m": -20}},
    "tilted_80deg": {"track": {"angle_deg": 80, "exit_altitude_m": 0}},
}.items():
    exp = copy.deepcopy(exp0)
    a = copy.deepcopy(SILO)
    for k, v in ov.items():
        a[k] = v
    exp["variants"] = {name: {"assist": a, "ignition": {"stage1": {"t_ign_s": 0.5}}}}
    r = tryres(name, exp)
    if r:
        print("       ", track_info(r.variants[name]))

print("== 2. ignition timing")
for name, ign in {
    "ign_push_start_+1.0": {"t_ign_s": 1.0, "reference": "push_start"},
    "ign_release_-1.0": {"t_ign_s": -1.0, "reference": "release"},
    "ign_release_-5.0 (before push)": {"t_ign_s": -5.0, "reference": "release"},
    "ign_release_+3.0": {"t_ign_s": 3.0},
    "ign_lag_tau1.5": {"t_ign_s": 0.0, "startup": {"kind": "lag", "tau_s": 1.5}},
    "ign_ramp_4s": {"t_ign_s": -1.0, "startup": {"t_ramp_s": 4.0}},
    "ign_depth_key (does not exist)": {"at_depth_m": 50.0},
}.items():
    exp = copy.deepcopy(exp0)
    exp["variants"] = {"v": {"assist": copy.deepcopy(SILO), "ignition": {"stage1": ign}}}
    r = tryres(name, exp)
    if r:
        i = r.variants["v"].run.ignition["stage1"]
        st = i.resolved_startup(r.variants["v"].vehicle.stages[0].startup.to_startup())
        print(f"        t_ign_s={i.t_ign_s} ref={i.reference} startup={st}")
exp = copy.deepcopy(exp0)
exp["baseline"]["ignition"]["stage1"] = {"t_ign_s": -2.0, "reference": "push_start"}
tryres("pad with reference push_start", exp)

print("== 3. propellant offload")
exp = copy.deepcopy(exp0)
exp["variants"] = {"silo_off10": {"assist": copy.deepcopy(SILO), "ignition": {"stage1": {"t_ign_s": 0.5}},
                                  "vehicle": {"stages": [{"name": "stage1", "propellant_mass_t": 369.81}]}}}
tryres("variant with a vehicle: key", exp)
exp = copy.deepcopy(exp0)
exp["variants"] = {"silo_cold": {"assist": copy.deepcopy(SILO), "ignition": {"stage1": {"t_ign_s": 0.5}}}}
exp["sweeps"] = [{"of": "silo_cold", "axes": {"vehicle.stages.stage1.propellant_mass_t": [410.9, 390.355, 369.81]}}]
tryres("unpaired planar sweep of vehicle.stages.stage1.propellant_mass_t", exp)
exp["sweeps"][0]["paired"] = True
r = tryres("paired planar sweep of vehicle.stages.stage1.propellant_mass_t", exp)
if r:
    for p in r.sweeps[0]:
        v = p.run.vehicle_dict["stages"][0]["propellant_mass_t"]
        b = p.paired_baseline.vehicle_dict["stages"][0]["propellant_mass_t"]
        print(f"        {p.run.name}: silo stage1 prop={v} | paired {p.paired_baseline.name}: {b}"
              f" | liftoff {p.run.to_vehicle().liftoff_mass_kg():.1f} kg")
exp = copy.deepcopy(exp0)
exp["variants"] = {"silo_cold": {"assist": copy.deepcopy(SILO), "ignition": {"stage1": {"t_ign_s": 0.5}}}}
exp["bounds"] = [{"name": "offload10", "of": ["silo_cold"], "overrides": {"vehicle.stages.stage1.propellant_mass_t": 369.81}, "paired_baseline": True}]
r = tryres("bound offload10 on stage1 propellant", exp)
if r:
    b = r.bounds[0]
    print("        runs:", {k: v.vehicle_dict["stages"][0]["propellant_mass_t"] for k, v in b.runs.items()},
          "paired:", b.baseline.name, b.baseline.vehicle_dict["stages"][0]["propellant_mass_t"])
exp = copy.deepcopy(exp0)
exp["variants"] = {"silo_cold": {"assist": copy.deepcopy(SILO), "ignition": {"stage1": {"t_ign_s": 0.5}}}}
exp["sensitivity"] = {"of": ["silo_cold"], "params": {"vehicle.stages.stage1.propellant_mass_t": 0.10}}
r = tryres("sensitivity +/-10% stage1 propellant", exp)
if r:
    for c in r.sensitivity:
        print("       ", c.run.name, c.run.vehicle_dict["stages"][0]["propellant_mass_t"])
exp = copy.deepcopy(exp0)
exp["variants"] = {"silo_cold": {"assist": copy.deepcopy(SILO), "ignition": {"stage1": {"t_ign_s": 0.5}}}}
exp["bounds"] = [{"name": "s2off", "of": ["silo_cold"], "overrides": {"vehicle.stages.stage2.propellant_mass_t": 96.75}, "paired_baseline": True}]
tryres("bound on stage2 propellant", exp)
# offload only the silo (not the pad) -- is there any route?
exp = copy.deepcopy(exp0)
exp["variants"] = {"silo_cold": {"assist": copy.deepcopy(SILO), "ignition": {"stage1": {"t_ign_s": 0.5}}}}
exp["sweeps"] = [{"of": "pad", "axes": {"vehicle.stages.stage1.propellant_mass_t": [369.81]}, "paired": True}]
tryres("paired sweep of the baseline itself", exp)
