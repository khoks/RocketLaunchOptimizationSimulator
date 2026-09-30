import json, math, time, pickle
import numpy as np
from sk import *
d = json.load(open(r"D:/DEV/ClaudeProjects/SpaceRocketOptimization/results/silo_screening_2d/20260930T175743Z/metrics.json"))
veh = Veh()
V0 = math.sqrt(2 * 3 * G0 * 100)
Pref = d["runs"]["pad"]["payload_kg"]
gp = d["runs"]["pad"]["gamma_star_rad"]
gs = d["runs"]["silo_cold"]["gamma_star_rad"]
res = {}
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
t0=time.time()
for kind, gname, g in [("pad","gp",gp),("silo_cold","gs",gs),("silo_cold","gp",gp),("pad","gs",gs),("silo_instant","own",d["runs"]["silo_instant"]["gamma_star_rad"]),("pad_instant","own",d["runs"]["pad_instant"]["gamma_star_rad"]),("silo_instant","gp",gp),("pad_instant","gp",gp)]:
    R = run(kind, g)
    o, m = R["o"], R["meco"]
    res[(kind,gname)] = dict(delta=R["delta"], a=R["a"], b=R["b"], dvm=o["dv_margin"], m_res=o["m_res"], J=o["J"], Jm=m["J_meco"], h=m["h_meco"], V=m["v_meco"], gam=m["gamma_meco"], t_meco=m["t_meco"], y_meco=m["y_meco"], dr=o["dr"], vr=o["vr_cut"])
    print(f"{kind:13s} g*={math.degrees(g):.4f} ({gname}) delta={math.degrees(R['delta']):.5f} a={R['a']:.6f} b={R['b']:.8f} dr={o['dr']:.4f} vr={o['vr_cut']:.2e} margin={o['dv_margin']:.4f} m/s  MECO h={m['h_meco']:.1f} V={m['v_meco']:.3f} t={m['t_meco']:.3f}  [{time.time()-t0:.0f}s]", flush=True)
    Jm=m["J_meco"]; J=o["J"]
    print(f"     to MECO: vac {Jm[0]:.3f} grav {Jm[1]:.3f} drag {Jm[2]:.3f} steer {Jm[3]:.3f} bp {Jm[4]:.3f} | after: vac {J[0]-Jm[0]:.3f} grav {J[1]-Jm[1]:.3f} drag {J[2]-Jm[2]:.3f} steer {J[3]-Jm[3]:.3f} bp {J[4]-Jm[4]:.3f}", flush=True)
pickle.dump(res, open("e2.pkl","wb"))
