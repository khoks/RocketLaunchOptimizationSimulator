"""Independent planar ascent integrator (review probe, physics-skeptic lens).

Written from CLAUDE.md's equations and the vehicle YAML only; it does not import
launchsim. Atmosphere: ambiance (ICAO) tabulated on a 1 m grid below 81,020 m and an
isothermal extension above (H = R T_top / (mu/(R_E+h_top)^2)). All SI.
"""

from __future__ import annotations

import math

import numpy as np
from ambiance import Atmosphere
from scipy.integrate import solve_ivp
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq

MU = 3.986004418e14
RE = 6378137.0
WE = 7.2921150e-5
G0 = 9.80665
LAT = math.radians(28.5)
AZ = math.radians(90.0)
WP = WE * math.cos(LAT) * math.sin(AZ)
R_AIR = 287.05287
H_TOP = 81020.0
R_T = RE + 200000.0
E_T = -MU / (2 * R_T)

# ---------------------------------------------------------------- atmosphere table
_H = np.arange(-200.0, H_TOP + 1.0, 1.0)
_H[-1] = H_TOP
_A = Atmosphere(_H)
_LNP = np.log(_A.pressure)
_LNR = np.log(_A.density)
_SOS = np.array(_A.speed_of_sound)
_T_TOP = float(Atmosphere([H_TOP]).temperature[0])
_P_TOP = float(Atmosphere([H_TOP]).pressure[0])
_R_TOP = float(Atmosphere([H_TOP]).density[0])
_A_TOP = float(Atmosphere([H_TOP]).speed_of_sound[0])
_HS = R_AIR * _T_TOP / (MU / (RE + H_TOP) ** 2)


def atmo(h: float) -> tuple[float, float, float]:
    """(p [Pa], rho [kg/m^3], a [m/s]) at geometric altitude h [m]."""
    if h >= H_TOP:
        f = math.exp(-(h - H_TOP) / _HS)
        return _P_TOP * f, _R_TOP * f, _A_TOP
    if h < -200.0:
        h = -200.0
    i = int(h + 200.0)
    if i >= len(_H) - 1:
        i = len(_H) - 2
    w = (h - _H[i]) / (_H[i + 1] - _H[i])
    p = math.exp(_LNP[i] + w * (_LNP[i + 1] - _LNP[i]))
    r = math.exp(_LNR[i] + w * (_LNR[i + 1] - _LNR[i]))
    a = _SOS[i] + w * (_SOS[i + 1] - _SOS[i])
    return p, r, a


# ---------------------------------------------------------------- vehicle
MACH = [0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.2, 1.3, 1.5, 1.75,
        2.0, 2.5, 3.0, 3.25, 3.5, 4.0, 4.5]
CD = [0.460, 0.404, 0.387, 0.385, 0.388, 0.400, 0.450, 0.510, 0.589, 0.660, 0.710, 0.730,
      0.722, 0.680, 0.606, 0.527, 0.460, 0.350, 0.273, 0.250, 0.236, 0.222, 0.220]
_CDI = PchipInterpolator(MACH, CD, extrapolate=False)


def cd_of(M: float, scale: float = 1.0) -> float:
    if M <= 0.0:
        return CD[0] * scale
    if M >= MACH[-1]:
        return CD[-1] * scale
    return float(_CDI(M)) * scale


class Veh:
    def __init__(self, s1_dry=22200.0, s1_prop=410900.0, s2_dry=4000.0, s2_prop=107500.0,
                 fairing=1700.0, T1=9 * 914.1e3, T1sl=9 * 845.2e3, isp1=311.0, T2=981e3,
                 isp2=348.0, Ae2=8.6, Aref=10.52, cd_scale=1.0, coast2=11.0,
                 fair_lim=1135.0):
        self.s1_dry, self.s1_prop, self.s2_dry, self.s2_prop = s1_dry, s1_prop, s2_dry, s2_prop
        self.fairing = fairing
        self.T1, self.isp1 = T1, isp1
        self.Ae1 = (T1 - T1sl) / 101325.0
        self.T2, self.isp2, self.Ae2 = T2, isp2, Ae2
        self.Aref, self.cd_scale, self.coast2, self.fair_lim = Aref, cd_scale, coast2, fair_lim
        self.c1 = isp1 * G0
        self.c2 = isp2 * G0
        self.mdot1 = T1 / self.c1
        self.mdot2 = T2 / self.c2

    def gross(self, P: float) -> float:
        return self.s1_dry + self.s1_prop + self.s2_dry + self.s2_prop + self.fairing + P


# state: r, th, vr, vt, m, Jvac, Jgrav, Jdrag, Jsteer, Jbp
def kin(y):
    r, _, vr, vt = y[0], y[1], y[2], y[3]
    u = vt - WP * r
    V = math.hypot(vr, u)
    if V < 1e-9:
        sg, cg = 1.0, 0.0
    else:
        sg, cg = vr / V, u / V
    return V, sg, cg, u


def make_rhs(veh: Veh, Tvac_fn, Ae, c, dirfn):
    def rhs(t, y):
        r, th, vr, vt, m = y[0], y[1], y[2], y[3], y[4]
        V, sg, cg, u = kin(y)
        h = r - RE
        p, rho, a = atmo(h)
        Tv = Tvac_fn(t)
        T = max(0.0, Tv - p * Ae) if Tv > 0 else 0.0
        er, et = dirfn(t, y, sg, cg)
        M = V / a
        D = 0.5 * rho * V * V * cd_of(M, veh.cd_scale) * veh.Aref
        Dr, Dt = -D * sg, -D * cg
        g = MU / (r * r)
        dvr = vt * vt / r - g + (T * er + Dr) / m
        dvt = -vr * vt / r + (T * et + Dt) / m
        dm = -Tv / c if Tv > 0 else 0.0
        geff = g - WP * WP * r
        cpsi = er * sg + et * cg
        return [vr, vt / r, dvr, dvt, dm, Tv / m, geff * sg, D / m,
                (T / m) * (1.0 - cpsi), (Tv - T) / m]
    return rhs


RTOL = 1e-10
ATOL = np.array([1e-5, 1e-12, 1e-8, 1e-8, 1e-6, 1e-8, 1e-8, 1e-8, 1e-8, 1e-8])


def seg(rhs, t0, y0, t1, events=(), max_step=2.0):
    for e in events:
        e.terminal = True
    sol = solve_ivp(rhs, (t0, t1), y0, method="DOP853", rtol=RTOL, atol=ATOL,
                    events=list(events) if events else None, max_step=max_step,
                    dense_output=False)
    if sol.status == 1:
        for k, te in enumerate(sol.t_events):
            if len(te):
                return sol.t_events[k][0], sol.y_events[k][0].copy(), k, sol
    return sol.t[-1], sol.y[:, -1].copy(), None, sol


def stage1(veh: Veh, *, y0, t_ign, startup, t_ramp, v_k, delta, gamma_stop=None,
           max_step=2.0, record=False):
    """Fly stage 1 from t=0 (release / flight start) to burnout.

    y0: [r, th, vr, vt, m] at t=0. t_ign: stage-1 ignition time (<=0: lit before).
    startup 'ramp' or 'step'. Returns (t_bo, y_bo, info).
    """
    T1 = veh.T1
    if startup == "step":
        def Tv(t):
            return T1 if t >= t_ign else 0.0
        t_full = t_ign
    else:
        def Tv(t):
            if t < t_ign:
                return 0.0
            x = (t - t_ign) / t_ramp
            return T1 * min(1.0, x)
        t_full = t_ign + t_ramp
    m_bo = veh.gross(0) - veh.s1_prop  # placeholder, replaced below
    info = {"segments": []}
    y = np.concatenate([np.asarray(y0, float), np.zeros(5)])
    m_bo = y0[4] - (veh.s1_prop - info.get("pre", 0.0))
    return Tv, t_full


def fly(veh: Veh, *, P, y0, pre_burn, t_ign, startup, t_ramp, v_k, delta, a, b,
        max_step=2.0, stop_at_meco=False, meco_override=None, s2_start=None,
        verbose=False):
    """Full flight. t=0 is the flight start (release). y0 = [r, th, vr, vt, m0_at_t0].
    pre_burn: stage-1 propellant already burned before t=0 [kg].
    Returns dict with events, integrals, and residual at cutoff.
    """
    out = {}
    T1 = veh.T1
    if startup == "step":
        def Tv1(t):
            return T1 if t >= t_ign - 1e-12 else 0.0
        t_full = t_ign
    else:
        def Tv1(t):
            if t < t_ign:
                return 0.0
            return T1 * min(1.0, (t - t_ign) / t_ramp)
        t_full = t_ign + t_ramp
    m_bo = y0[4] - (veh.s1_prop - pre_burn)

    def d_radial(t, y, sg, cg):
        return 1.0, 0.0

    cd, sd = math.cos(delta), math.sin(delta)

    def d_tilt(t, y, sg, cg):
        return cd, sd

    def d_vrel(t, y, sg, cg):
        return sg, cg

    y = np.concatenate([np.asarray(y0, float), np.zeros(5)])
    t = 0.0
    mode = None
    lit = t_ign <= 0.0
    if lit:
        V, sg, cg, _ = kin(y)
        mode = "KICK" if (V >= v_k and y[2] > 0) else "VERT"
    else:
        mode = "COAST"
    ev_log = []
    if s2_start is None:
        while True:
            dfn = {"COAST": d_radial, "VERT": d_radial, "KICK": d_tilt, "GT": d_vrel}[mode]
            rhs = make_rhs(veh, Tv1, veh.Ae1, veh.c1, dfn)
            evs = []
            names = []

            def ev_bo(t, yy):
                return yy[4] - m_bo
            ev_bo.direction = -1
            evs.append(ev_bo); names.append("burnout")
            t_end = 1e4
            if mode == "COAST":
                t_end = t_ign
            elif t < t_full - 1e-12:
                t_end = t_full
            if mode == "VERT":
                def ev_k(t, yy):
                    V, sg, cg, _ = kin(yy)
                    return V - v_k
                ev_k.direction = 1
                evs.append(ev_k); names.append("kick_start")
            if mode == "KICK":
                def ev_al(t, yy):
                    V, sg, cg, u = kin(yy)
                    return math.atan2(yy[2], u) - (math.pi / 2 - delta)
                ev_al.direction = -1
                evs.append(ev_al); names.append("kick_end")
            t1, y1, k, sol = seg(rhs, t, y, t_end, evs, max_step)
            if k is None:
                # reached t_end: ignition or ramp end
                t, y = t1, y1
                if mode == "COAST":
                    V, sg, cg, _ = kin(y)
                    mode = "KICK" if (V >= v_k and y[2] > 0) else "VERT"
                    ev_log.append(("ignition", t, mode, V))
                else:
                    ev_log.append(("ramp_end", t, mode))
                continue
            t, y = t1, y1
            nm = names[k]
            ev_log.append((nm, t, float(kin(y)[0])))
            if nm == "burnout":
                break
            if nm == "kick_start":
                mode = "KICK"
            elif nm == "kick_end":
                mode = "GT"
        out["t_meco"] = t
        out["y_meco"] = y.copy()
        V, sg, cg, u = kin(y)
        out["gamma_meco"] = math.atan2(y[2], u)
        out["v_meco"] = V
        out["h_meco"] = y[0] - RE
        out["J_meco"] = y[5:].copy()
        if stop_at_meco:
            out["events"] = ev_log
            return out
        # staging
        y = y.copy()
        y[4] -= veh.s1_dry
    else:
        t, y = s2_start
        y = np.asarray(y, float).copy()
        out["t_meco"] = t
        out["J_meco"] = y[5:].copy()
    fairing_on = True
    # coast
    rhs_c = make_rhs(veh, lambda tt: 0.0, 0.0, veh.c2, d_radial)
    t_ign2 = t + veh.coast2
    t, y, _, _ = seg(rhs_c, t, y, t_ign2, (), max_step)
    out["t_ign2"] = t_ign2

    def heat(yy):
        V, sg, cg, u = kin(yy)
        p, rho, aa = atmo(yy[0] - RE)
        return 0.5 * rho * V ** 3

    if heat(y) < veh.fair_lim:
        y[4] -= veh.fairing
        fairing_on = False
        out["t_fair"] = t

    def d_ltg(tt, yy, sg, cg):
        s = a - b * (tt - t_ign2)
        inv = 1.0 / math.sqrt(1.0 + s * s)
        return s * inv, inv

    rhs2 = make_rhs(veh, lambda tt: veh.T2, veh.Ae2, veh.c2, d_ltg)

    def ev_cut(tt, yy):
        return 0.5 * (yy[2] ** 2 + yy[3] ** 2) - MU / yy[0] - E_T
    ev_cut.direction = 1

    def ev_fair(tt, yy):
        return heat(yy) - veh.fair_lim
    ev_fair.direction = -1
    m_floor = veh.s2_dry + P + (veh.fairing if fairing_on else 0.0) - 60000.0
    while True:
        evs = [ev_cut] + ([ev_fair] if fairing_on else [])
        t1, y1, k, _ = seg(rhs2, t, y, t + 2000.0, evs, max_step)
        t, y = t1, y1
        if k is None:
            raise RuntimeError("no cutoff")
        if k == 1:
            y = y.copy()
            y[4] -= veh.fairing
            fairing_on = False
            out["t_fair"] = t
            continue
        break
    out["t_cut"] = t
    out["y_cut"] = y
    m_empty = veh.s2_dry + P + (veh.fairing if fairing_on else 0.0)
    m_res = y[4] - m_empty
    out["m_res"] = m_res
    out["dv_margin"] = veh.c2 * math.log(y[4] / (y[4] - m_res)) if y[4] - m_res > 0 else float("nan")
    out["dr"] = y[0] - R_T
    out["vr_cut"] = y[2]
    out["J"] = y[5:].copy()
    V, sg, cg, u = kin(y)
    out["V_cut"] = V
    out["events"] = ev_log
    return out


# ---------------------------------------------------------------- scenario helpers
def pad_y0(veh, P, t_ramp=2.0, instant=False):
    m0 = veh.gross(P)
    pre = 0.0 if instant else veh.mdot1 * t_ramp / 2.0
    return [RE, 0.0, 0.0, WP * RE, m0 - pre], pre


def silo_y0(veh, P, V0):
    m0 = veh.gross(P)
    return [RE, 0.0, V0, WP * RE, m0], 0.0


def solve_delta(veh, gamma_star, lo=0.001, hi=0.3, **kw):
    def f(d):
        o = fly(veh, delta=d, stop_at_meco=True, a=0, b=0, **kw)
        return o["gamma_meco"] - gamma_star
    return brentq(f, lo, hi, xtol=1e-13, rtol=8.9e-16)


def solve_ltg(veh, a0, b0, *, P, y0, pre_burn, t_ign, startup, t_ramp, v_k, delta,
              s2_start=None, tol_r=1e-3, tol_vr=1e-6, max_it=30, **kw):
    """Newton on (a, 100 b) for r_cut = R_T and v_r = 0. Returns (a, b, out)."""
    x = np.array([a0, 100 * b0])
    base = dict(P=P, y0=y0, pre_burn=pre_burn, t_ign=t_ign, startup=startup, t_ramp=t_ramp,
                v_k=v_k, delta=delta, **kw)
    if s2_start is None:
        # fly stage 1 once
        o1 = fly(veh, a=0, b=0, stop_at_meco=True, **base)
        y = o1["y_meco"].copy()
        y[4] -= veh.s1_dry
        s2_start = (o1["t_meco"], y)

    def F(xx):
        o = fly(veh, a=xx[0], b=xx[1] / 100, s2_start=s2_start, **base)
        return np.array([o["dr"] / 1e4, o["vr_cut"] / 100]), o
    f, o = F(x)
    for it in range(max_it):
        if abs(o["dr"]) < tol_r and abs(o["vr_cut"]) < tol_vr:
            break
        J = np.zeros((2, 2))
        h = 1e-6
        for j in range(2):
            xp = x.copy(); xp[j] += h
            fp, _ = F(xp)
            J[:, j] = (fp - f) / h
        dx = np.linalg.solve(J, -f)
        lam = 1.0
        for _ in range(8):
            xn = x + lam * dx
            try:
                fn, on = F(xn)
            except RuntimeError:
                lam /= 2
                continue
            if np.linalg.norm(fn) < np.linalg.norm(f) or lam < 0.05:
                break
            lam /= 2
        x, f, o = xn, fn, on
    return x[0], x[1] / 100, o, s2_start
