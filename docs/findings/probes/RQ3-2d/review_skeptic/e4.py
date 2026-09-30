import json, math, time, pickle
import numpy as np
import sk
from sk import *
d = json.load(open(r"D:/DEV/ClaudeProjects/SpaceRocketOptimization/results/silo_screening_2d/20260930T175743Z/metrics.json"))
veh = Veh()
V0 = math.sqrt(2 * 3 * G0 * 100)
Pref = d["runs"]["pad"]["payload_kg"]
gp = d["runs"]["pad"]["gamma_star_rad"]
gsi = d["runs"]["silo_instant"]["gamma_star_rad"]
def setup(kind, P):
    if kind == "pad":
        y0, pre = pad_y0(veh, P); return dict(P=P, y0=y0, pre_burn=pre, t_ign=-2.0, startup="ramp", t_ramp=2.0, v_k=50.0)
    if kind == "silo_cold":
        y0, pre = silo_y0(veh, P, V0); return dict(P=P, y0=y0, pre_burn=pre, t_ign=0.5, startup="ramp", t_ramp=2.0, v_k=50.0)
    if kind == "silo_instant":
        y0, pre = silo_y0(veh, P, V0); return dict(P=P, y0=y0, pre_burn=pre, t_ign=0.0, startup="step", t_ramp=0.0, v_k=50.0)
    if kind == "pad_instant":
        y0, pre = pad_y0(veh, P, instant=True); return dict(P=P, y0=y0, pre_burn=pre, t_ign=0.0, startup="step", t_ramp=0.0, v_k=50.0)
def run(kind, gamma, a0=0.6, b0=0.0015):
    base = setup(kind, Pref)
    dl = solve_delta(veh, gamma, **base)
    a, b, o, s2 = solve_ltg(veh, a0, b0, delta=dl, **base)
    o1 = fly(veh, delta=dl, a=a, b=b, stop_at_meco=True, **base)
    return dict(delta=dl, a=a, b=b, o=o, meco=o1)
out = {}
for kind in ["pad_instant", "silo_instant"]:
    R = run(kind, gsi); o, m = R["o"], R["meco"]
    out[kind] = R
    Jm = m["J_meco"]; J = o["J"]
    print(f"{kind} @ g*={math.degrees(gsi):.4f}: margin {o['dv_margin']:.4f} MECO h {m['h_meco']:.1f} V {m['v_meco']:.3f} | to MECO grav {Jm[1]:.3f} drag {Jm[2]:.3f} bp {Jm[4]:.3f} steer {Jm[3]:.3f} | after grav {J[1]-Jm[1]:.3f} steer {J[3]-Jm[3]:.3f}", flush=True)
pickle.dump({k:(v['meco']['y_meco'], v['meco']['t_meco'], v['a'], v['b']) for k,v in out.items()}, open("e4.pkl","wb"))
# numerical check: max_step and rtol
r = d["runs"]
for name, kw in [("pad", dict(pre=None)), ("silo_cold", {})]:
    rr = r[name]; base = setup(name, rr["payload_kg"])
    for ms, rt in [(2.0, 1e-10), (0.1, 1e-10), (2.0, 1e-12)]:
        sk.RTOL = rt
        o = fly(veh, delta=rr["delta_rad"], a=rr["ltg_a"], b=rr["ltg_b_per_s"], max_step=ms, **base)
        print(f"{name} max_step {ms} rtol {rt}: m_res {o['m_res']:.5f} kg dr {o['dr']:.4f} vr {o['vr_cut']:.2e}", flush=True)
    sk.RTOL = 1e-10
