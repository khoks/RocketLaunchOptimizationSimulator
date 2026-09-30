"""LABELLED PROBE (step 27 fix round 2): launchsim (validated code, HEAD) evaluations of
pad, pad_instant, silo_instant and silo_cold at the matched payload P_ref (the pad's P*)
with gamma* forced to a common value. Reads the shipped experiment YAML and the recorded
metrics.json for P_ref and warm seeds; writes nothing to results/. Output: stdout."""
import json, math, sys
from pathlib import Path
import numpy as np
REPO = Path("D:/DEV/ClaudeProjects/SpaceRocketOptimization")
sys.path.insert(0, str(REPO / "src"))
from launchsim.cli import load_experiment
from launchsim import sim
from launchsim.search import WarmStore, WarmEntry, FINAL_MODE
from launchsim.compare import MatchedRun, attribution_terms
from launchsim.dynamics import PLANAR_LAYOUT, PlanarDynamics2D
from launchsim.vehicle import with_payload

M = json.load(open(REPO / "results/silo_screening_2d/20260930T175743Z/metrics.json"))
exp = load_experiment(REPO / "experiments/silo_screening_2d.yaml")
runs = exp.runs
P_REF = M["runs"]["pad"]["payload_kg"]
names = ["pad", "pad_instant", "silo_instant", "silo_cold"]
own = {n: M["runs"][n]["gamma_star_rad"] for n in names}
gammas = sys.argv[1:] and [math.radians(float(g)) for g in sys.argv[1:]] or [own["pad"], own["silo_cold"], own["silo_instant"]]
print("P_ref", P_REF, "own gamma* deg", {n: round(math.degrees(g), 4) for n, g in own.items()})

def evaluate(name, g):
    res = runs[name]
    vehicle = res.to_vehicle()
    setup = sim.planar_setup(res.run, vehicle)
    ctx = sim.search_context(setup, vehicle, res.run.end)
    r = M["runs"][name]
    seed = WarmEntry(r["gamma_star_rad"], r["payload_kg"], r["delta_rad"], (r["ltg_a"], r["ltg_b_per_s"]))
    out = ctx.evaluate(P_REF, g, WarmStore(), FINAL_MODE, seed=seed)
    trace = out.shot.prefix
    mr = MatchedRun(name=name, payload_kg=P_REF, gamma_star_rad=g, trace=trace,
                    vehicle=with_payload(vehicle, P_REF), omega_p_rads=setup.env.omega_p_rads,
                    r_datum_m=setup.env.r_datum_m)
    t = attribution_terms(mr)
    tb, y = min(trace.burnouts.values(), key=lambda it: it[0])
    y = np.asarray(y, dtype=float)
    dyn = PlanarDynamics2D(setup.env.omega_p_rads, setup.env.r_datum_m)
    alt = PLANAR_LAYOUT.get(y, "r_m") - setup.env.r_datum_m
    v = float(dyn.speed(y))
    return dict(t=t, meco_t=tb, meco_alt=float(alt), meco_v=v, m_meco=float(PLANAR_LAYOUT.get(y, "m_kg")),
                J_steer_meco=float(PLANAR_LAYOUT.get(y, "J_steer_mps")), gmeco=math.degrees(out.gamma_meco_rad))

for g in gammas:
    print(f"\n== gamma* {math.degrees(g):.4f} deg")
    rows = {n: evaluate(n, g) for n in names}
    for n, d in rows.items():
        t = d["t"]
        print(f"{n:13s} margin {t['dv_margin']:10.4f}  Jgrav_meco {t['J_grav_meco']:10.4f}  Jgrav {t['J_grav']:10.4f} "
              f"Jsteer {t['J_steer']:8.4f} Jsteer_meco {d['J_steer_meco']:8.4f} Jbp {t['J_bp']:8.4f} Jdrag {t['J_drag']:7.4f} "
              f"pre {t['pre']:8.4f} V0 {t['V_0']:8.4f} | MECO t {d['meco_t']:.3f} alt {d['meco_alt']:.1f} v_rel {d['meco_v']:.3f} m {d['m_meco']:.1f} gmeco {d['gmeco']:.4f}")
    b = rows["pad"]
    for n in names[1:]:
        d = rows[n]
        print(f"  {n} - pad: d margin {d['t']['dv_margin']-b['t']['dv_margin']:+.4f}  d Jgrav_meco {d['t']['J_grav_meco']-b['t']['J_grav_meco']:+.4f} "
              f"post-MECO g+s gain {-( (d['t']['J_grav']-d['t']['J_grav_meco']+d['t']['J_steer']-d['J_steer_meco']) - (b['t']['J_grav']-b['t']['J_grav_meco']+b['t']['J_steer']-b['J_steer_meco']) ):+.4f} "
              f"d MECO alt {d['meco_alt']-b['meco_alt']:+.1f} m, d MECO v_rel {d['meco_v']-b['meco_v']:+.3f}")
    si, pi, sc = rows["silo_instant"], rows["pad_instant"], rows["silo_cold"]
    print(f"  silo_instant - pad_instant d Jgrav_meco {si['t']['J_grav_meco']-pi['t']['J_grav_meco']:+.4f}; "
          f"silo_cold - silo_instant {sc['t']['J_grav_meco']-si['t']['J_grav_meco']:+.4f}; pad_instant - pad {pi['t']['J_grav_meco']-b['t']['J_grav_meco']:+.4f}")
