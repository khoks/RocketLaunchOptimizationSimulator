import json, math, time
import numpy as np
from sk import *
d = json.load(open(r"D:/DEV/ClaudeProjects/SpaceRocketOptimization/results/silo_screening_2d/20260930T175743Z/metrics.json"))
veh = Veh()
V0 = math.sqrt(2 * 3 * G0 * 100)
print("V0", V0, "Ae1", veh.Ae1, "mdot1", veh.mdot1, "WP", WP)
cases = {
 "pad": dict(t_ign=-2.0, startup="ramp", t_ramp=2.0, kind="pad"),
 "pad_instant": dict(t_ign=0.0, startup="step", t_ramp=0.0, kind="padi"),
 "silo_instant": dict(t_ign=0.0, startup="step", t_ramp=0.0, kind="silo"),
 "silo_cold": dict(t_ign=0.5, startup="ramp", t_ramp=2.0, kind="silo"),
 "silo_hot_ramp_on_track": dict(t_ign=-2.0, startup="ramp", t_ramp=2.0, kind="silo_hot"),
}
for name, c in cases.items():
    r = d["runs"][name]
    P = r["payload_kg"]
    if c["kind"] == "pad":
        y0, pre = pad_y0(veh, P)
    elif c["kind"] == "padi":
        y0, pre = pad_y0(veh, P, instant=True)
    elif c["kind"] == "silo":
        y0, pre = silo_y0(veh, P, V0)
    else:
        y0, pre = silo_y0(veh, P, V0)
        pre = veh.mdot1 * 1.0
        y0[4] -= pre
    t0 = time.time()
    o = fly(veh, P=P, y0=y0, pre_burn=pre, t_ign=c["t_ign"], startup=c["startup"], t_ramp=c["t_ramp"],
            v_k=50.0, delta=r["delta_rad"], a=r["ltg_a"], b=r["ltg_b_per_s"])
    J = o["J"]
    print(f"\n{name}: P*={P:.3f}  ({time.time()-t0:.1f}s)")
    print("  events", [(e[0], round(e[1], 4)) + tuple(round(x, 3) if isinstance(x, float) else x for x in e[2:]) for e in o["events"]])
    print(f"  MECO t {o['t_meco']:.4f} rec(rel) {r['stage1_burnout_t_s'] - r['t_flight_start_s'] if name.startswith('pad') else 'see'}; h {o['h_meco']:.2f} rec {r['stage1_burnout_alt_m']:.2f}; V {o['v_meco']:.4f} rec {r['stage1_burnout_speed_mps']:.4f}; gam {math.degrees(o['gamma_meco']):.5f} rec {math.degrees(r['meco_gamma_rel_rad']):.5f}")
    print(f"  fair t {o.get('t_fair')}  cut t {o['t_cut']:.4f}  dr {o['dr']:.3f} vr {o['vr_cut']:.5f} m_res {o['m_res']:.3f} dvm {o['dv_margin']:.4f} (rec m_res {r['recorded_m_res_kg']:.4f})")
    print(f"  J vac {J[0]:.4f} rec {r['dv_vac_mps']:.4f}; grav {J[1]:.4f} rec {r['gravity_loss_mps']:.4f}; drag {J[2]:.4f} rec {r['drag_loss_mps']:.4f}; steer {J[3]:.4f} rec {r['steering_loss_mps']:.4f}; bp {J[4]:.4f} rec {r['back_pressure_loss_mps']:.4f}")
    V0f = math.hypot(y0[2], y0[3] - WP * y0[0])
    print(f"  identity: {o['V_cut'] - V0f - (J[0]-J[1]-J[2]-J[3]-J[4]):.3e}")
