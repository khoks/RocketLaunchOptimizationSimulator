"""Max-Q, q-alpha and felt loads of the planar model (docs/physics.md, "Max-Q and loads
(planar)").

- Closed form: from rest, a constant radial thrust acceleration a = 20 m/s^2, no
  gravity, the exponential atmosphere rho0 exp(-h/H) (rho0 1.225 kg/m^3, H 7,000 m):
  V = a t, h = a t^2/2, q = 0.5 rho0 a^2 t^2 exp(-a t^2/(2H)), so t* = sqrt(2H/a) =
  26.4575 s and q* = rho0 a H / e = 63,091 Pa at h = H. On a datum of radius 1e7 m
  (altitude resolved to 1.9e-9 m; step-20 review: the plan's R = 1e12 m puts t* 3.5e-4 s
  off through the altitude quantisation), ConstantGravity(0).
- A peak on a phase boundary: the same climb with the thrust cut at t_b = 20 s < t*,
  then a coast at constant V (no gravity) while rho falls: q peaks at t_b exactly,
  q_b = 0.5 rho0 (a t_b)^2 exp(-a t_b^2/(2H)).
- The scan does not depend on the sampling: 32 to 1,024 scan points give the same peak,
  and on the gate pad no dense sample (0.01 s grid) beats the scanned max-Q.
- The felt axial and lateral acceleration and q-alpha against a hand-built state (plan
  amendment 11): the proper acceleration (T e - D v_hat_rel)/m projected on the thrust
  axis e and on its normal, in g0, with every force written here.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
import yaml

from launchsim.atmosphere import ambient_scalar
from launchsim.config import VehicleConfig
from launchsim.constants import G0_MPS2, MU_EARTH_M3S2, OMEGA_EARTH_RADS
from launchsim.dynamics import (
    PLANAR_LAYOUT,
    PLANAR_STATE_NAMES,
    ConstantGravity,
    InverseSquareGravity,
    PlanarParams,
    rhs_planar,
)
from launchsim.guidance import FixedTilt, GuidanceSpec, Radial
from launchsim.metrics_planar import (
    felt_accel_g,
    felt_axial_g,
    felt_lateral_g,
    max_q,
    psi_rad,
    q_alpha_pa_rad,
    scan_peak,
)
from launchsim.phases import IgnitionSpec, IntegratorSettings, PhaseSpec, atol_for, integrate_phase
from launchsim.phases.planar import PlanarEnvironment, PlanarPlanner
from launchsim.vehicle import CdTable, DragModel, Startup, ThrustSchedule

P2 = PLANAR_LAYOUT
A_MPS2 = 20.0
RHO0 = 1.225
H_SCALE_M = 7000.0
R_FLAT_M = 1e7
G_TEST = 9.81
"""Uniform gravity [m/s^2] of the hand-built felt-load state (never g0; gravity is not
felt, so its value does not enter the felt loads)."""
T_CUT_S = 20.0
SCAN_POINTS = 256
XATOL_S = 1e-6
KIND = "VERTICAL_RISE"


def _climb(
    const_accel_schedule: Callable[..., ThrustSchedule],
    exp_atmosphere: Callable[[float, float], object],
    t_cut: float | None,
    n_rtol: float = 1e-12,
) -> list:
    """The radial climb from rest on the flat datum, as one or two recorded phases."""
    atm = exp_atmosphere(RHO0, H_SCALE_M)

    def params(schedule: ThrustSchedule | None) -> PlanarParams:
        return PlanarParams(
            ConstantGravity(0.0),
            0.0,
            0.0,
            schedule,
            None,
            atm,  # type: ignore[arg-type]
            None if schedule is None else Radial(),
            R_FLAT_M,
        )

    settings = IntegratorSettings(rtol=n_rtol)
    atol = atol_for(PLANAR_STATE_NAMES)
    y0 = P2.build(r_m=R_FLAT_M, m_kg=1.0)
    lit = params(const_accel_schedule(A_MPS2))
    t1 = 60.0 if t_cut is None else t_cut
    burn = integrate_phase(PhaseSpec(KIND, 0, 0.0, t1, rhs_planar, lit, (), atol), y0, settings)
    if t_cut is None:
        return [burn]
    coast_spec = PhaseSpec("COAST", 0, t_cut, 60.0, rhs_planar, params(None), (), atol)
    return [burn, integrate_phase(coast_spec, burn.y_end, settings)]


def test_max_q_closed_form(
    const_accel_schedule: Callable[..., ThrustSchedule],
    exp_atmosphere: Callable[[float, float], object],
) -> None:
    """t* = sqrt(2H/a) within 1e-4 s and q* = rho0 a H/e within 1e-9 relative, at h = H
    (1e-3 m) and Mach a t*/340 (the test atmosphere's speed of sound)."""
    phases = _climb(const_accel_schedule, exp_atmosphere, None)
    peak = max_q(phases, n_points=SCAN_POINTS, xatol_s=XATOL_S)
    assert peak is not None
    t_star = math.sqrt(2.0 * H_SCALE_M / A_MPS2)
    assert abs(peak.t_s - t_star) < 1e-4
    assert peak.q_pa == pytest.approx(RHO0 * A_MPS2 * H_SCALE_M / math.e, rel=1e-9)
    assert peak.alt_m == pytest.approx(H_SCALE_M, abs=1e-3)
    assert peak.mach == pytest.approx(A_MPS2 * t_star / 340.0, rel=1e-6)
    assert peak.phase == KIND


def test_max_q_on_a_phase_boundary(
    const_accel_schedule: Callable[..., ThrustSchedule],
    exp_atmosphere: Callable[[float, float], object],
) -> None:
    """Thrust cut at t_b = 20 s (before t* = 26.5 s), then a coast at constant speed:
    the peak is the boundary itself, t = t_b exactly and q = 0.5 rho0 (a t_b)^2
    exp(-a t_b^2/(2H)) within 1e-9 relative, reported in the burn phase."""
    phases = _climb(const_accel_schedule, exp_atmosphere, T_CUT_S)
    peak = max_q(phases, n_points=SCAN_POINTS, xatol_s=XATOL_S, kinds=(KIND, "COAST"))
    assert peak is not None
    v_b = A_MPS2 * T_CUT_S
    q_b = 0.5 * RHO0 * v_b * v_b * math.exp(-0.5 * A_MPS2 * T_CUT_S**2 / H_SCALE_M)
    assert peak.t_s == T_CUT_S
    assert peak.q_pa == pytest.approx(q_b, rel=1e-9)
    assert peak.phase == KIND


def test_scan_does_not_depend_on_the_sampling(
    const_accel_schedule: Callable[..., ThrustSchedule],
    exp_atmosphere: Callable[[float, float], object],
) -> None:
    """32, 256 and 1,024 scan points give the same max-Q (t within 1e-5 s, q within
    1e-12 relative); fewer than two points and a phase without dense output are
    refused."""
    phases = _climb(const_accel_schedule, exp_atmosphere, None)
    peaks = [max_q(phases, n_points=n, xatol_s=XATOL_S) for n in (32, 256, 1024)]
    assert all(p is not None for p in peaks)
    for p in peaks[1:]:
        assert p is not None and peaks[0] is not None
        assert abs(p.t_s - peaks[0].t_s) < 1e-5
        assert p.q_pa == pytest.approx(peaks[0].q_pa, rel=1e-12)
    with pytest.raises(ValueError, match="n_points"):
        max_q(phases, n_points=1, xatol_s=XATOL_S)
    burn = phases[0]
    off = integrate_phase(
        burn.spec, burn.y[:, 0], IntegratorSettings(rtol=1e-12, dense_output=False)
    )
    with pytest.raises(ValueError, match="dense output"):
        max_q([off], n_points=SCAN_POINTS, xatol_s=XATOL_S)
    assert max_q([], n_points=SCAN_POINTS, xatol_s=XATOL_S) is None


def test_gate_pad_max_q_beats_every_dense_sample(repo_root: Path) -> None:
    """The gate pad flown to MECO (a 3 deg kick, recorded, rtol 1e-10): no sample of q on
    a 0.01 s grid over the flight phases exceeds the scanned max-Q (which lies in the
    gravity turn, unthrottled: about 39 kPa near Mach 1.5 at the tropopause, 11.02 km,
    where the density's scale height changes, above the flown 22-30 kPa, the bias the
    model states), and q-alpha and the felt loads scan the same way."""
    path = repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    vehicle = VehicleConfig.model_validate(raw).to_vehicle()
    omega_p = OMEGA_EARTH_RADS * math.cos(math.radians(28.5))
    env = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), omega_p, ambient_scalar)
    planner = PlanarPlanner(
        vehicle,
        {"stage1": IgnitionSpec(-2.0), "stage2": IgnitionSpec(0.0)},
        GuidanceSpec(50.0, 60.0, 60.0),
        env,
        "stage1_burnout",
        IntegratorSettings(rtol=1e-10),
    )
    trace = planner.run(math.radians(3.0))
    phases = trace.ascent_phases()
    peak = max_q(phases, n_points=SCAN_POINTS, xatol_s=XATOL_S)
    assert peak is not None
    sampled = 0.0
    for res in phases:
        if res.dense is None:
            continue
        for t in np.arange(res.spec.t0, res.t_end, 0.01):
            y = np.asarray(res.dense(t), dtype=float)
            sampled = max(sampled, _q_written_here(y, res.spec.params))
    assert sampled <= peak.q_pa * (1.0 + 1e-12)
    assert 20e3 < peak.q_pa < 60e3 and 0.8 < peak.mach < 2.0
    for fn in (q_alpha_pa_rad, felt_axial_g, felt_lateral_g):
        found = scan_peak(phases, fn, n_points=SCAN_POINTS, xatol_s=XATOL_S)
        assert found is not None and found.value >= 0.0


def _q_written_here(y: np.ndarray, p: PlanarParams) -> float:
    """q = 0.5 rho V^2 written here: rho from the params' atmosphere at h = r - r_datum,
    V = |v_rel|."""
    r, v_r, v_t = (float(P2.get(y, n)) for n in ("r_m", "v_r_mps", "v_theta_mps"))
    rho = p.atmosphere(r - p.r_datum_m)[1]
    return 0.5 * rho * (v_r * v_r + (v_t - p.omega_p_rads * r) ** 2)


def test_felt_loads_and_q_alpha_of_a_hand_built_state() -> None:
    """A state at 12 km with v_rel = (w, u) = (400, 300) m/s (gamma_rel = 53.1 deg),
    thrust 1.2 MN vacuum through 0.4 m^2 of exit area at p = 20 kPa, tilted 30 deg from
    vertical (pitch 60 deg), C_D 0.5 on 10 m^2 at rho 0.3 kg/m^3, mass 60 t. Written
    here: T = T_vac - p A_e, D = 0.5 rho V^2 C_D A, the proper acceleration
    a_p = (T e - D v_hat)/m; axial = a_p . e / g0, lateral = |e x a_p| / g0, psi = the
    angle between e and v_hat, q-alpha = q psi (1e-12 relative). An unpowered phase
    reports along v_rel: axial -D/(m g0), lateral 0, psi 0."""
    omega_p = 7e-5
    r = 6.39e6
    w, u = 400.0, 300.0
    m = 60_000.0
    y = P2.build(r_m=r, v_r_mps=w, v_theta_mps=u + omega_p * r, m_kg=m)
    p_amb, rho, a_sound = 20_000.0, 0.3, 300.0
    t_vac, a_e = 1.2e6, 0.4
    delta = math.radians(30.0)
    table = CdTable.pchip((0.0, 10.0), (0.5, 0.5))
    drag = DragModel(table, 10.0)
    schedule = ThrustSchedule(t_vac, 3000.0, a_e, 0.0, Startup("step"))

    def atm(alt_m: float) -> tuple[float, float, float]:
        return p_amb, rho, a_sound

    params = PlanarParams(
        ConstantGravity(G_TEST), omega_p, G_TEST, schedule, drag, atm, FixedTilt(delta)
    )
    speed = math.hypot(w, u)
    thrust = t_vac - p_amb * a_e
    q = 0.5 * rho * speed * speed
    d = q * 0.5 * 10.0
    e = (math.cos(delta), math.sin(delta))
    v_hat = (w / speed, u / speed)
    acc = ((thrust * e[0] - d * v_hat[0]) / m, (thrust * e[1] - d * v_hat[1]) / m)
    axial = (acc[0] * e[0] + acc[1] * e[1]) / G0_MPS2
    lateral = abs(e[0] * acc[1] - e[1] * acc[0]) / G0_MPS2
    psi = math.acos(e[0] * v_hat[0] + e[1] * v_hat[1])
    got_axial, got_lateral = felt_accel_g(10.0, y, params)
    assert got_axial == pytest.approx(axial, rel=1e-12)
    assert got_lateral == pytest.approx(lateral, rel=1e-12)
    assert felt_axial_g(10.0, y, params) == got_axial
    assert felt_lateral_g(10.0, y, params) == got_lateral
    assert psi_rad(10.0, y, params) == pytest.approx(psi, rel=1e-12)
    assert q_alpha_pa_rad(10.0, y, params) == pytest.approx(q * psi, rel=1e-12)
    coast = PlanarParams(ConstantGravity(G_TEST), omega_p, G_TEST, None, drag, atm, None)
    c_axial, c_lateral = felt_accel_g(10.0, y, coast)
    assert c_axial == pytest.approx(-d / (m * G0_MPS2), rel=1e-12)
    assert c_lateral == 0.0 and psi_rad(10.0, y, coast) == 0.0
