import json, math, time, pickle
import numpy as np
from sk import *
d = json.load(open(r"D:/DEV/ClaudeProjects/SpaceRocketOptimization/results/silo_screening_2d/20260930T175743Z/metrics.json"))
veh = Veh()
res = pickle.load(open("e2.pkl","rb"))
Pref = d["runs"]["pad"]["payload_kg"]
pad = res[("pad","gp")]; sil = res[("silo_cold","gp")]; silo_own = res[("silo_cold","gs")]
def hvg(y):
    V, sg, cg, u = kin(y); return y[0]-RE, V, math.atan2(y[2], u)
def build(y_ref, h, V, g):
    y = y_ref.copy(); r = RE + h
    y[0] = r; y[2] = V*math.sin(g); y[3] = V*math.cos(g) + WP*r
    return y
def s2margin(y_meco, t_meco, a0, b0):
    y = y_meco.copy(); y[4] -= veh.s1_dry
    base = dict(P=Pref, y0=[0,0,0,0,0], pre_burn=0, t_ign=0, startup="step", t_ramp=0, v_k=50, delta=0)
    a, b, o, _ = solve_ltg(veh, a0, b0, s2_start=(t_meco, y), **base)
    J = o["J"] - y[5:]
    return o["dv_margin"], a, b, J, o
hp, Vp, gp_ = hvg(pad["y_meco"]); hs, Vs, gs_ = hvg(sil["y_meco"])
print("pad MECO", hp, Vp, math.degrees(gp_), pad["y_meco"][4]); print("silo MECO (pad g*)", hs, Vs, math.degrees(gs_), sil["y_meco"][4])
t0 = time.time()
rows = []
for lab, h, V, g, ym, tm in [
    ("pad state", hp, Vp, gp_, pad["y_meco"], pad["t_meco"]),
    ("silo state", hs, Vs, gs_, sil["y_meco"], sil["t_meco"]),
    ("pad + silo V", hp, Vs, gp_, pad["y_meco"], pad["t_meco"]),
    ("pad + silo h", hs, Vp, gp_, pad["y_meco"], pad["t_meco"]),
    ("pad + dV 1 m/s", hp, Vp+1, gp_, pad["y_meco"], pad["t_meco"]),
    ("pad + dh 1 km", hp+1000, Vp, gp_, pad["y_meco"], pad["t_meco"]),
    ("pad V+76.707", hp, Vp+76.707, gp_, pad["y_meco"], pad["t_meco"]),
]:
    y = build(ym, h, V, g)
    m, a, b, J, o = s2margin(y, tm, pad["a"], pad["b"])
    rows.append((lab, m))
    print(f"{lab:16s} h={h:9.1f} V={V:9.3f} g={math.degrees(g):.4f} -> margin {m:9.4f}  a={a:.5f} b={b:.7f} | after-MECO grav {J[1]:.3f} steer {J[3]:.3f} drag {J[2]:.3f} bp {J[4]:.4f} vac {J[0]:.3f}  [{time.time()-t0:.0f}s]", flush=True)
