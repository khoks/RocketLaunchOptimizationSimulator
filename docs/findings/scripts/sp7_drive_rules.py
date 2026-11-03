"""SP7 step S6b: the linear-motor rule values of experiments/silo_drive_2d.yaml (file B).

Every drive number file B registers that a rule fixes (design
docs/phases/inputs/2026-10-08-SP7-design.md, section 4.10: "computed by the closed forms
before any run, written into the file with a comment naming the rule, and independently
recomputed by S6b's gate to 1e-12 relative; nothing changes after any run") is computed
here by the closed forms of docs/phases/inputs/2026-10-08-SP7-sources.md, section 10, and
printed at full precision (``repr``), with each closed form's validity conditions checked
and printed. The values are rules applied to fixed inputs, never tuned: no run of file B
exists when they are written, and the script flies nothing.

Inputs (sources section 10), each read from its file:

- M, the pad's full-load vehicle [kg]: stage 1's dry mass and propellant, stage 2's dry
  mass and propellant and the fairing of configs/vehicles/generic_f9_class_2d.yaml (read
  through ``config.VehicleConfig``, SI by units.py), plus P_ref, the pad's payload
  capacity P* of SP1 (tests/data/silo_offload_2d_record.json, gate.reference_payload_kg,
  26,054.396243494975 kg). The sources write it 572,354.4 kg, its rounding to 0.1 kg; the
  values below are this full-precision M's (a recomputation from the rounded M differs by
  6.6e-9 relative on every force and power value).
- v_e, SP1's exit speed [m/s]: sqrt(2 a g0 L) of silo_cold in experiments/silo_offload_2d.yaml
  (net_accel_g 3, stroke_m 100), checked equal to the unrounded 76.70717046013364 m/s that
  silo_cold_200m writes.
- L = 100 m, silo_cold's stroke; t_r = 0.5 s, the drive's rise time (sources section 10).
- g_eff [m/s^2], the code's track gravity mu/R_E^2 - omega_p^2 R_E
  (``dynamics.g_eff_track``) with omega_p = omega_E cos(lat) sin(az)
  (``dynamics.planar_rotation_rate``) at the shared site block of
  experiments/silo_offload_2d.yaml (28.5 deg, azimuth 90 deg; file B copies the block
  verbatim, a test pins it).
- The stage-1 startup ramp t_ramp [s], vacuum thrust and full mass flow of the vehicle
  file (the ramp's 2.0 s is itself assumed there).
- For the sealed bore (D-SP7-54, TODO.md): the 5.2 m fairing diameter (spacex.com) and the
  3.66 m body diameter (Falcon User's Guide 2021 Table 2-1, through the vehicle file's
  A_ref) as configs/display/f9_class.yaml records them, read for D-SP7-54's provenance
  only: the model reads the literal 5.24 m from file B, never the display file, and an edit
  of either display value fails the bore check, because the registered bore would no
  longer follow its stated rule. The bore is the fairing plus the sources' 3.7 m bore
  (README.md line 246) less the 3.66 m body: a clearance of 0.04 m that is nominal, since
  3.7 m is also SpaceX's rounding of the 3.66 m body (2 cm radial around the fairing).

The rules (sources section 10; the variants of design 4.10):

- the plateau a_p: a net acceleration a_p min(1, t/t_r) from rest reaches v_e at L when
  v_e^2 = 2 a_p L - a_p^2 t_r^2 / 12, the smaller root a_p = [L - sqrt(L^2 - v_e^2 t_r^2 /
  12)] / (t_r^2 / 12), computed in the cancellation-free form v_e^2 / (L + sqrt(L^2 - v_e^2
  t_r^2 / 12)); valid while the ramp ends inside the stroke (a_p t_r^2 / 6 < L and a_p t_r /
  2 < v_e);
- lm_cmd: accel_command_g = a_p / g0; force_max_kN = 1.10 M (a_cmd + g_eff) / 1e3;
  power_max_MW = force_max_kN v_e / 1e3 (a_cmd in m/s^2);
- lm_cmd_taper: stop_taper_m = v_e t_r; a_cmd the same root with L replaced by L -
  s_taper / 2 (valid while the ramp ends before L - s_taper); caps by lm_cmd's rule with
  this a_cmd;
- lm_cmd_hot: lm_cmd's a_cmd and caps; t_ign_s = t_push - t_ramp (push_start reference),
  t_push = t_r / 2 + v_e / a_cmd, lm_cmd's exact push time while no cap binds and the drive
  force stays positive (the drive never pulls back);
- lm_fixed: force_max_kN = M (a_p + g_eff) / 1e3 (the force law ramping from the holding
  force M g_eff); power_max_MW = r force_max_kN v_e / 1e3 with r = 1;
- lm_fixed_target, lm_fixed_hot, lm_fixed_sled22, lm_fixed_sealed: lm_fixed's F_max and
  P_max (release_speed_mps = v_e; t_ign_s = 0 at push start; carriage_mass_t = 22; the
  sealed shaft);
- lm_fixed_r07: r = 0.7; F_max the bracketed root (``scipy.optimize.brentq``) of s(v_e) = L
  for the full-load stack: the ramp to t_r and a force-limited plateau to v_c = P_max /
  F_max = 0.7 v_e, s_c = (v_c^2 + a'^2 t_r^2 / 12) / (2 a') with a' = F_max / M - g_eff,
  then the power-limited phase on the vertical track, s(v) - s_c = (1/g)[-(v^2 - v_c^2)/2
  - v_inf (v - v_c) - v_inf^2 ln((v_inf - v)/(v_inf - v_c))], v_inf = P_max / (M g); valid
  while a' t_r / 2 < v_c, s_c < L and v_e < v_inf.

Usage, from the repository root: ``uv run python docs/findings/scripts/sp7_drive_rules.py``
(under a second; ``--json PATH`` also writes the values as strict JSON, outside the
repository). It prints every value, marks a failing validity condition FAIL and then exits
1 if any failed (2 if the --json path lies inside the repository), so a value is usable
only from a run that exits 0.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import yaml
from scipy.optimize import brentq

from launchsim import units
from launchsim.atmosphere import KAPPA_AIR, standard_atmosphere
from launchsim.config import VehicleConfig
from launchsim.constants import G0_MPS2
from launchsim.dynamics import g_eff_track, planar_rotation_rate
from launchsim.structure import ramped_plateau_accel_mps2

REPO = Path(__file__).resolve().parents[3]
"""The repository root (this file is docs/findings/scripts/sp7_drive_rules.py)."""
VEHICLE_FILE = REPO / "configs" / "vehicles" / "generic_f9_class_2d.yaml"
"""The gate vehicle (file B's vehicle, frozen since SP7's start commit 22c62e9)."""
SP1_RECORD = REPO / "tests" / "data" / "silo_offload_2d_record.json"
"""SP1's record of its solved offloads and P_ref (gate.reference_payload_kg)."""
SHARED_SOURCE = REPO / "experiments" / "silo_offload_2d.yaml"
"""The file whose shared site block file B copies verbatim, and whose silo_cold and
silo_cold_200m state SP1's push (net_accel_g, stroke_m, exit_speed_mps)."""
DISPLAY_FILE = REPO / "configs" / "display" / "f9_class.yaml"
"""The display geometry recording the sourced 5.2 m fairing and 3.66 m body diameters,
D-SP7-54's inputs; read for that decision's provenance only (nothing here enters the
model, which reads file B's literal 5.24 m)."""
V_E_WRITTEN_MPS = 76.70717046013364
"""SP1's exit speed as silo_cold_200m writes it (Python repr of sqrt(2 x 3 x g0 x 100))."""
RISE_TIME_S = 0.5
"""t_r [s], the drive's force or command rise time (sources section 10's input; the
structure file's central assumed real-drive rise time is the same 0.5 s, D-SP7-09)."""
CAP_FACTOR = 1.10
"""The acceleration law's caps sit this factor above the full-load need (sources section
10, lm_cmd's row)."""
R_FIXED = 1.0
"""lm_fixed's r = P_max / (F_max v_e) (sources section 10)."""
R_POWER = 0.7
"""lm_fixed_r07's r (sources section 10)."""
CARRIAGE_T = 22.0
"""lm_fixed_sled22's carriage [t] (sources section 10: experiments/silo_screening_2d.yaml
line 86, "MagLifter ~4% of liftoff"; assumed)."""
SOURCES_BORE_M = 3.7
"""The sources' sealed bore [m] (README.md line 246), replaced by D-SP7-54."""
BORE_WRITTEN_M = 5.24
"""lm_fixed_sealed's shaft_bore_m as D-SP7-54 fixes it (5.2 m fairing + 0.04 m)."""
GAP_M = 5.0
"""lm_fixed_sealed's shaft_gap_m (sources section 10's central)."""
GAMMA = 1.4
"""lm_fixed_sealed's shaft_gamma (sources section 10), checked equal to the ICAO adiabatic
index atmosphere.py carries (``atmosphere.KAPPA_AIR``)."""
HOT_LIGHTEST_OFFLOAD_KG = 60.0e3
"""The largest offload [kg] of the checks before registration (check 2: x = 0, 20, 40 and
60 t), at which lm_cmd_hot's drive-force condition is also checked, with no dm (the
lightest stack there; KI-073's first iterate carries no dm)."""
ROOT_XTOL_N = 1.0e-9
"""brentq's absolute tolerance on F_max [N] (its relative tolerance, BRENTQ_RTOL, governs)."""
BRENTQ_RTOL = 4.0 * sys.float_info.epsilon
"""brentq's relative tolerance on F_max: 4 eps, scipy brentq's floor."""
R07_BRACKET_HIGH_FACTOR = 2.0
"""lm_fixed_r07's bracket high end as a multiple of lm_fixed's F_max (its low end): a
bracket, not a tuned value; both ends are checked to straddle L, and s(v_e) falls
monotonically with F_max, so any straddling bracket gives the same root."""
SAME_FORM_REL_TOL = 1.0e-15
"""Two evaluations of the same closed form (the script's plateau and
``structure.ramped_plateau_accel_mps2``) agree to a few ulps (eps = 2.2e-16)."""
IDENTITY_REL_TOL = 1.0e-13
"""An algebraic identity re-evaluated in floating point (the taper's closed form returning
v_e at L; the corner speed P_max / F_max = r v_e): ten times tighter than the registered
tolerance."""
REGISTERED_REL_TOL = 1.0e-12
"""The registered tolerance of a rule value against its closed form (design 4.10)."""


def load_yaml(path: Path) -> dict[str, Any]:
    """A YAML file as a mapping."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), path
    return data


def plateau_root(v_e_mps: float, length_m: float, t_r_s: float) -> float:
    """The smaller root a_p [m/s^2] of v_e^2 = 2 a_p L - a_p^2 t_r^2 / 12 (sources section
    10), written v_e^2 / (L + sqrt(L^2 - v_e^2 t_r^2 / 12)), the rationalised form of
    [L - sqrt(L^2 - v_e^2 t_r^2 / 12)] / (t_r^2 / 12); v_e_mps [m/s], length_m [m], t_r_s
    [s]."""
    disc = length_m * length_m - v_e_mps * v_e_mps * t_r_s * t_r_s / 12.0
    if not disc > 0.0:
        raise ValueError("no real root: L^2 <= v_e^2 t_r^2 / 12")
    return v_e_mps * v_e_mps / (length_m + math.sqrt(disc))


def plateau_root_textbook(v_e_mps: float, length_m: float, t_r_s: float) -> float:
    """The same root as the sources write it, [L - sqrt(L^2 - v_e^2 t_r^2/12)] /
    (t_r^2/12) [m/s^2], printed beside the rationalised form; v_e_mps [m/s], length_m [m],
    t_r_s [s]."""
    k = t_r_s * t_r_s / 12.0
    return (length_m - math.sqrt(length_m * length_m - v_e_mps * v_e_mps * k)) / k


def r07_stroke_m(
    f_max_n: float, m_kg: float, g_mps2: float, v_e_mps: float, t_r_s: float, r: float
) -> tuple[float, dict[str, float]]:
    """s(v_e) [m] of the full-load force-law push (cold, vertical, from the holding force
    M g) with F_max = f_max_n [N] and P_max = r F_max v_e (r dimensionless): the ramp to
    t_r, the force plateau to v_c = r v_e and the power phase to v_e (sources section 10,
    lm_fixed_r07's row); m_kg the stack [kg], g_mps2 the track gravity [m/s^2], v_e_mps
    [m/s], t_r_s [s]; with its parts (a' [m/s^2], v_c and v_inf [m/s], s_c [m])."""
    a_net = f_max_n / m_kg - g_mps2
    v_c = r * v_e_mps
    v_inf = r * f_max_n * v_e_mps / (m_kg * g_mps2)
    s_c = (v_c * v_c + a_net * a_net * t_r_s * t_r_s / 12.0) / (2.0 * a_net)
    power = (
        -(v_e_mps * v_e_mps - v_c * v_c) / 2.0
        - v_inf * (v_e_mps - v_c)
        - v_inf * v_inf * math.log((v_inf - v_e_mps) / (v_inf - v_c))
    ) / g_mps2
    return s_c + power, {"a_net_mps2": a_net, "v_c_mps": v_c, "v_inf_mps": v_inf, "s_c_m": s_c}


def compute() -> dict[str, Any]:
    """Every input, rule value and validity condition (SI unless the key names a YAML
    unit). Raises ValueError where a closed form has no root."""
    vehicle = VehicleConfig.model_validate(load_yaml(VEHICLE_FILE)).to_vehicle()
    s1, s2 = vehicle.stages
    record = json.loads(SP1_RECORD.read_text(encoding="utf-8"))
    p_ref_kg = float(record["gate"]["reference_payload_kg"])
    m_full = (
        s1.dry_mass_kg
        + s1.propellant_mass_kg
        + s2.dry_mass_kg
        + s2.propellant_mass_kg
        + vehicle.fairing_mass_kg
        + p_ref_kg
    )
    shared = load_yaml(SHARED_SOURCE)
    site = shared["site"]
    omega_p_rads = planar_rotation_rate(
        units.deg_to_rad(site["latitude_deg"]), units.deg_to_rad(site["azimuth_deg"])
    )
    g_mps2 = g_eff_track(omega_p_rads)
    cold = shared["variants"]["silo_cold"]["assist"]
    length_m = float(cold["stroke_m"])
    v_e = math.sqrt(2.0 * units.from_g(cold["net_accel_g"]) * length_m)
    v_written = float(shared["variants"]["silo_cold_200m"]["assist"]["exit_speed_mps"])
    t_r = RISE_TIME_S
    t_ramp = s1.startup.t_ramp_s
    display = load_yaml(DISPLAY_FILE)["vehicle"]
    fairing_d_m = float(display["fairing_diameter_m"]["value"])
    body_d_m = float(display["body_diameter_m"]["value"])

    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, text: str) -> None:
        """Record one validity condition: its name, whether it holds, the values."""
        checks.append((name, ok, text))

    check("v_e as written", v_e == v_written, f"sqrt(2 a g0 L) = {v_e!r} == {v_written!r}")

    # the plateau a_p (shared kinematics)
    a_p = plateau_root(v_e, length_m, t_r)
    a_p_text = plateau_root_textbook(v_e, length_m, t_r)
    check(
        "a_p: ramp ends inside the stroke (a_p t_r^2/6 < L)",
        a_p * t_r * t_r / 6.0 < length_m,
        f"{a_p * t_r * t_r / 6.0!r} m < {length_m!r} m",
    )
    check(
        "a_p: ramp ends below v_e (a_p t_r/2 < v_e)",
        a_p * t_r / 2.0 < v_e,
        f"{a_p * t_r / 2.0!r} m/s < {v_e!r} m/s",
    )
    a_code = ramped_plateau_accel_mps2(length_m, v_e, t_r)
    check(
        "a_p equals design 4.2.1's plateau a' (structure.ramped_plateau_accel_mps2)",
        math.isclose(a_p, a_code, rel_tol=SAME_FORM_REL_TOL),
        f"{a_code!r} m/s^2 (the plateau file A's constant_accel rise_time row charges)",
    )

    def caps(a_cmd_mps2: float) -> tuple[float, float]:
        """lm_cmd's caps for a command a_cmd_mps2 [m/s^2]: (force_max_kN, power_max_MW)."""
        f_n = CAP_FACTOR * m_full * (a_cmd_mps2 + g_mps2)
        return units.n_to_kn(f_n), units.w_to_mw(f_n * v_e)

    cmd_f_kn, cmd_p_mw = caps(a_p)

    # lm_cmd_taper
    s_taper = v_e * t_r
    a_taper = plateau_root(v_e, length_m - s_taper / 2.0, t_r)
    check(
        "lm_cmd_taper: ramp ends before the taper (a t_r^2/6 < L - s_taper)",
        a_taper * t_r * t_r / 6.0 < length_m - s_taper,
        f"{a_taper * t_r * t_r / 6.0!r} m < {length_m - s_taper!r} m",
    )
    v_taper_start = math.sqrt(2.0 * a_taper * (length_m - s_taper) - a_taper**2 * t_r**2 / 12.0)
    v_end_taper = math.sqrt(v_taper_start**2 + a_taper * s_taper)
    check(
        "lm_cmd_taper: the taper's closed form returns v_e at L",
        math.isclose(v_end_taper, v_e, rel_tol=IDENTITY_REL_TOL),
        f"sqrt(v(L - s_t)^2 + a s_t) = {v_end_taper!r} m/s",
    )
    taper_f_kn, taper_p_mw = caps(a_taper)

    # lm_cmd_hot
    t_push = t_r / 2.0 + v_e / a_p
    t_ign_hot = t_push - t_ramp
    check(
        "lm_cmd_hot: lit on the track after push start (t_ign_s >= 0)",
        t_ign_hot >= 0.0,
        f"t_push - t_ramp = {t_push!r} - {t_ramp!r} = {t_ign_hot!r} s",
    )
    check(
        "lm_cmd_hot: lit after the command's rise (t_ign_s >= t_r)",
        t_ign_hot >= t_r,
        f"{t_ign_hot!r} s >= {t_r!r} s (the peak command force comes before ignition)",
    )
    burned_max_kg = s1.mdot_full_kgps * t_ramp / 2.0
    t_vac_n = s1.thrust_vac_total_N
    f_need_end_n = (m_full - burned_max_kg) * (a_p + g_mps2) - t_vac_n
    check(
        "lm_cmd_hot: the drive force stays above 0 at full vacuum thrust (full load)",
        f_need_end_n > 0.0,
        f"(M - mdot t_ramp/2)(a + g) - T_vac = {f_need_end_n!r} N",
    )
    f_need_light_n = (m_full - HOT_LIGHTEST_OFFLOAD_KG - burned_max_kg) * (a_p + g_mps2) - t_vac_n
    hot_offload_limit_kg = m_full - burned_max_kg - t_vac_n / (a_p + g_mps2)
    check(
        "lm_cmd_hot: the drive force stays above 0 at full vacuum thrust (60 t offloaded, no dm)",
        f_need_light_n > 0.0,
        f"{f_need_light_n!r} N; zero only beyond an offload of {hot_offload_limit_kg!r} kg",
    )

    # lm_fixed
    fixed_f_n = m_full * (a_p + g_mps2)
    fixed_f_kn = units.n_to_kn(fixed_f_n)
    fixed_p_mw = units.w_to_mw(R_FIXED * fixed_f_n * v_e)
    corner_mps = units.mw_to_w(fixed_p_mw) / units.kn_to_n(fixed_f_kn)
    check(
        "lm_fixed: corner speed P_max/F_max equals v_e",
        math.isclose(corner_mps, v_e, rel_tol=IDENTITY_REL_TOL),
        f"{corner_mps!r} m/s",
    )

    # lm_fixed_r07
    def miss(f_n: float) -> float:
        """s(v_e) - L [m] of the r = 0.7 full-load push at F_max = f_n [N]."""
        return r07_stroke_m(f_n, m_full, g_mps2, v_e, t_r, R_POWER)[0] - length_m

    lo_n = fixed_f_n
    hi_n = R07_BRACKET_HIGH_FACTOR * fixed_f_n
    check(
        "lm_fixed_r07: bracket low end overshoots L",
        miss(lo_n) > 0.0,
        f"s(v_e) - L = {miss(lo_n)!r}",
    )
    check(
        "lm_fixed_r07: bracket high end falls short",
        miss(hi_n) < 0.0,
        f"s(v_e) - L = {miss(hi_n)!r}",
    )
    r07_f_n = float(brentq(miss, lo_n, hi_n, xtol=ROOT_XTOL_N, rtol=BRENTQ_RTOL))
    _s, parts = r07_stroke_m(r07_f_n, m_full, g_mps2, v_e, t_r, R_POWER)
    check(
        "lm_fixed_r07: ramp ends before v_c (a' t_r/2 < v_c)",
        parts["a_net_mps2"] * t_r / 2.0 < parts["v_c_mps"],
        f"{parts['a_net_mps2'] * t_r / 2.0!r} m/s < {parts['v_c_mps']!r} m/s",
    )
    check(
        "lm_fixed_r07: v_e < v_inf",
        v_e < parts["v_inf_mps"],
        f"{v_e!r} m/s < {parts['v_inf_mps']!r} m/s",
    )
    check(
        "lm_fixed_r07: the plateau reaches v_c inside the stroke (s_c < L)",
        parts["s_c_m"] < length_m,
        f"s_c = {parts['s_c_m']!r} m",
    )
    r07_f_kn = units.n_to_kn(r07_f_n)
    r07_p_mw = units.w_to_mw(R_POWER * r07_f_n * v_e)

    # lm_fixed_sealed (D-SP7-54)
    bore_m = fairing_d_m + (SOURCES_BORE_M - body_d_m)
    check(
        "lm_fixed_sealed: bore = fairing + (3.7 - 3.66) m equals the written 5.24 m",
        math.isclose(bore_m, BORE_WRITTEN_M, rel_tol=REGISTERED_REL_TOL),
        f"{fairing_d_m!r} + ({SOURCES_BORE_M!r} - {body_d_m!r}) = {bore_m!r} m",
    )
    a_ref_m2 = vehicle.aero.reference_area_m2 if vehicle.aero is not None else float("nan")
    body_ref_m = math.sqrt(4.0 * a_ref_m2 / math.pi)
    check(
        "lm_fixed_sealed: bore above the run's body diameter sqrt(4 A_ref/pi)",
        BORE_WRITTEN_M > body_ref_m,
        f"{BORE_WRITTEN_M!r} m > {body_ref_m!r} m",
    )
    check(
        "lm_fixed_sealed: gamma equals the ICAO adiabatic index (atmosphere.KAPPA_AIR)",
        GAMMA == KAPPA_AIR,
        f"{GAMMA!r} == {KAPPA_AIR!r}",
    )
    p0_pa = float(standard_atmosphere(-length_m).p_pa)
    area_m2 = math.pi * BORE_WRITTEN_M**2 / 4.0
    f_p_end_n = p0_pa * area_m2 * (1.0 - (GAP_M / (GAP_M + length_m)) ** GAMMA)
    check(
        "lm_fixed_sealed: F_max > M g_eff + F_p(L) (no stall on the stroke: F_p is largest at L)",
        fixed_f_n > m_full * g_mps2 + f_p_end_n,
        f"{fixed_f_n!r} N > {m_full * g_mps2 + f_p_end_n!r} N",
    )
    sled_hold_n = (m_full + units.t_to_kg(CARRIAGE_T)) * g_mps2
    check(
        "lm_fixed_sled22: F_max above the stack and carriage's weight (no stall)",
        fixed_f_n > sled_hold_n,
        f"{fixed_f_n!r} N > {sled_hold_n!r} N",
    )

    return {
        "inputs": {
            "M_kg": m_full,
            "M_parts_kg": {
                "stage1_dry": s1.dry_mass_kg,
                "stage1_propellant": s1.propellant_mass_kg,
                "stage2_dry": s2.dry_mass_kg,
                "stage2_propellant": s2.propellant_mass_kg,
                "fairing": vehicle.fairing_mass_kg,
                "P_ref": p_ref_kg,
            },
            "v_e_mps": v_e,
            "L_m": length_m,
            "t_r_s": t_r,
            "g_eff_mps2": g_mps2,
            "omega_p_rads": omega_p_rads,
            "g0_mps2": G0_MPS2,
            "t_ramp_s": t_ramp,
            "stage1_thrust_vac_N": t_vac_n,
            "stage1_mdot_full_kgps": s1.mdot_full_kgps,
            "fairing_diameter_m": fairing_d_m,
            "body_diameter_m": body_d_m,
        },
        "derived": {
            "a_p_mps2": a_p,
            "a_p_textbook_form_mps2": a_p_text,
            "a_p_g0": units.to_g(a_p),
            "lm_cmd_t_push_s": t_push,
            "lm_cmd_taper_a_cmd_mps2": a_taper,
            "lm_cmd_hot_drive_force_full_load_N": f_need_end_n,
            "lm_cmd_hot_drive_force_60t_N": f_need_light_n,
            "lm_cmd_hot_offload_limit_kg": hot_offload_limit_kg,
            "lm_fixed_F_max_N": fixed_f_n,
            "lm_fixed_corner_speed_mps": corner_mps,
            "lm_fixed_r07_F_max_N": r07_f_n,
            "lm_fixed_r07_parts": parts,
            "lm_fixed_sealed_p0_pa": p0_pa,
            "lm_fixed_sealed_force_bound_N": p0_pa * area_m2,
            "lm_fixed_sealed_F_p_L_N": f_p_end_n,
            "body_diameter_from_A_ref_m": body_ref_m,
        },
        "yaml": {
            "lm_cmd": {
                "accel_command_g": units.to_g(a_p),
                "force_max_kN": cmd_f_kn,
                "power_max_MW": cmd_p_mw,
            },
            "lm_cmd_taper": {
                "accel_command_g": units.to_g(a_taper),
                "force_max_kN": taper_f_kn,
                "power_max_MW": taper_p_mw,
                "stop_taper_m": s_taper,
            },
            "lm_cmd_hot": {
                "accel_command_g": units.to_g(a_p),
                "force_max_kN": cmd_f_kn,
                "power_max_MW": cmd_p_mw,
                "t_ign_s": t_ign_hot,
            },
            "lm_fixed": {"force_max_kN": fixed_f_kn, "power_max_MW": fixed_p_mw},
            "lm_fixed_target": {
                "force_max_kN": fixed_f_kn,
                "power_max_MW": fixed_p_mw,
                "release_speed_mps": v_e,
            },
            "lm_fixed_r07": {"force_max_kN": r07_f_kn, "power_max_MW": r07_p_mw},
            "lm_fixed_hot": {
                "force_max_kN": fixed_f_kn,
                "power_max_MW": fixed_p_mw,
                "t_ign_s": 0.0,
            },
            "lm_fixed_sled22": {
                "force_max_kN": fixed_f_kn,
                "power_max_MW": fixed_p_mw,
                "carriage_mass_t": CARRIAGE_T,
            },
            "lm_fixed_sealed": {
                "force_max_kN": fixed_f_kn,
                "power_max_MW": fixed_p_mw,
                "shaft_bore_m": BORE_WRITTEN_M,
                "shaft_gap_m": GAP_M,
                "shaft_gamma": GAMMA,
            },
        },
        "checks": [{"check": n, "pass": ok, "values": t} for n, ok, t in checks],
    }


def _print(values: dict[str, Any]) -> None:
    """Print every input, derived value, YAML value and check, floats as repr."""
    print("SP7 S6b: file B's linear-motor rule values (sources section 10)")
    for section in ("inputs", "derived"):
        print(f"\n[{section}]")
        for key, value in values[section].items():
            print(f"  {key} = {value!r}")
    print("\n[yaml values, per variant]")
    for variant, keys in values["yaml"].items():
        print(f"  {variant}:")
        for key, value in keys.items():
            print(f"    {key}: {value!r}")
    print("\n[validity conditions]")
    for item in values["checks"]:
        state = "PASS" if item["pass"] else "FAIL"
        print(f"  {state}  {item['check']}: {item['values']}")


def main(argv: list[str] | None = None) -> int:
    """Compute, print and (with --json) write the values; 1 if any check fails, 2 for a
    --json path inside the repository."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", type=Path, help="also write the values as strict JSON here")
    args = parser.parse_args(argv)
    values = compute()
    _print(values)
    if args.json is not None:
        out = args.json.resolve()
        if out == REPO or REPO in out.parents:
            print(f"error: --json {out} lies inside the repository", file=sys.stderr)
            return 2
        out.write_text(json.dumps(values, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    failed = [c for c in values["checks"] if not c["pass"]]
    print(f"\n{len(values['checks']) - len(failed)} of {len(values['checks'])} checks pass")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
