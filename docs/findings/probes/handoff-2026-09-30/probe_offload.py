"""Probe: stage-1 propellant offload on the gate F9 (generic_f9_class_2d), payload-searched
planar runs (shipped shared blocks of silo_screening_2d), pad vs silo_cold (3 g, 100 m,
ignition 0.5 s after release, 2 s ramp). Nothing is written to results/."""
import copy
import time
from pathlib import Path

import yaml

from launchsim import sim
from launchsim.config import resolve_experiment

REPO = Path("D:/DEV/ClaudeProjects/SpaceRocketOptimization")


def load(p):
    with open(REPO / p, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


exp0 = load("experiments/silo_screening_2d.yaml")
veh = load("configs/vehicles/generic_f9_class_2d.yaml")
for k in ("sweeps", "sensitivity", "bounds"):
    exp0.pop(k, None)
exp0["variants"] = {"silo_cold": exp0["variants"]["silo_cold"]}
M1 = 410.9
fracs = [0.0, 0.02, 0.05, 0.10]
exp0["sweeps"] = [{"of": "silo_cold", "paired": True,
                   "axes": {"vehicle.stages.stage1.propellant_mass_t": [round(M1 * (1 - f), 4) for f in fracs]}}]
res = resolve_experiment(exp0, veh)
KEYS = ("payload_kg", "liftoff_mass_kg", "stage1_burnout_t_s", "meco_speed_inertial_mps",
        "stage1_burnout_alt_m", "gravity_loss_mps", "drag_loss_mps", "max_q_pa",
        "hold_down_force_min_N", "residual_propellant_kg", "status")


def show(label, rr, dt):
    m = rr.result.metrics
    vals = []
    for k in KEYS:
        v = m.get(k)
        vals.append(f"{k}={v:.1f}" if isinstance(v, float) else f"{k}={v}")
    print(f"{label:28s} ({dt:5.1f} s) " + " ".join(vals), flush=True)


for f, point in zip(fracs, res.sweeps[0], strict=True):
    for which, run in (("silo_cold", point.run), ("pad", point.paired_baseline)):
        if f in (0.02, 0.05) and which == "pad":
            continue
        t0 = time.perf_counter()
        rr = sim.run_resolved(run)
        show(f"{which} offload {f:.0%}", rr, time.perf_counter() - t0)
