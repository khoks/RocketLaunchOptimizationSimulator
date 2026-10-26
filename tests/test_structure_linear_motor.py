"""The structural transform on a flown linear-motor push (SP7 step S4b; docs/physics.md,
"The flown push of a linear motor"; design 4.2.1, 4.2.2, 4.4, the S4b row of section 5
and exit criterion 6).

No test here solves a pre-registered SP7 case (D-SP7-31): the sizing runs on
tests/data/structure_synthetic.yaml (its central axial frequency 3 Hz and rise time 0.8 s)
and a synthetic pad flight (tests/structure_support.py), and every push is a short
synthetic linear-motor push on the gate vehicle at SP1's P_ref (planar, the experiment
silo_offload_2d's shared blocks; a 1-D push on the generic F9 for the run metrics). Every
closed-form expectation is computed here, never from the package; the engine numbers are
read from the vehicle (its sea-level thrust T_vac - p_sl A_e, mass flow and startup
ramp). With M = m_v + m_c, g the track's g_eff (the planar g_ref at 28.5 deg east, or
mu/R_E^2 in 1-D), g0 the unit:

- force law, cold, vertical, on its force plateau: n_q = F_max/(M g0), F_int = (m_v/M)
  F_max; hot (stage 1 lit 2 s before the push start, its ramp ending there, delivered
  thrust T at sea level, mass flow T_vac/(g0 Isp_vac)) with a carriage and impingement
  f_imp: n(t) = (F_max + (1 - f_imp) T)/(M(t) g0), largest at the release (M falls), and
  F_int(t) = (m_v/M)(F_max + (1 - f_imp) T) - T, largest at the end of the rise (it falls
  with m_v when m_c > 0), as are n m_v and n m_prop1; the hot interface formula of S4;
- acceleration law: n_q = (a_cmd + g)/g0; cold F_int = m_v (a_cmd + g); hot F_int(t) =
  m_v(t) (a_cmd + g) - T, largest at the end of the rise;
- the resting values n_0 = g/g0 and F_0 = m_v(0) g - T(0) (the hold's for a hot start);
- the rise formula: DLF = min(2, 1 + T_ax/(pi t_r)) with the drive's own t_r and T_ax =
  1/f (f = 3 Hz), n_0 + DLF (n_q - n_0) and F_0 + DLF (F_q - F_0); quasi_static 1, step 2;
- the flown history's phase-free single-mode bound (``structure.single_mode_bound``, the
  fix of review round 1: M1, M2, H-P1-02): on closed-form PL loads, a ramp from rest to a
  plateau gives min(Delta, 2 r/w) = (DLF - 1) Delta (the formula), a step J before the
  ramp adds J, a falling corner off a plateau adds nothing to the envelope while one
  inside a rise lets q + rho rise at the old slope r for 1/w more (r/w), a release
  mid-ramp leaves r min(t, 2/w), and a sub-phase shorter than SINGLE_MODE_STEP_FRACTION T
  (the planner leaves some of 3e-15 to 1e-10 s at a taper's start or a power corner) is a
  step, so its rounding never enters a slope (review round 2, P2-M1); on the flown pushes
  whose n and F_int ramp linearly from rest (cold, a cold stop taper after the rise
  included, or the acceleration law's n) it equals the formula to rounding; elsewhere each
  charged value is the larger of the two;
- the release: at the track end on the plateau (n_before = n_q); at a target speed in the
  power phase (n_before = P_max/(v_release M g0) below n_q, the release time from the
  vertical power phase's t(v)) and inside the rise (n_before = n_q, the bound's 2 r/w);
  after a stop taper over the last s_t metres (40 m of 100 and 10 m of 50: n_before =
  n_0, the taper time atan(s_t Omega/v_0)/Omega with Omega = sqrt(a_f/s_t), its own DLF);
  n_peak,rel = n_before + the larger of (DLF - 1)(n_q - n_0) [+ (DLF_taper - 1) x the
  taper's drop] and the bound's residual; with A = n_peak,rel - n_before the mode keeps
  about n_after at most |n_before - n_after| + A, so a release that unloads swings to 2
  n_after - n_peak,rel and compresses to n_peak,rel, and one in tension (F_int < 0 at
  the release: a hot force law at 6 MN on a 250 t carriage with f_imp 0.5, n_after =
  T/(m_v g0) above n_before) swings to n_before - A and compresses to 2 n_after - n_before
  + A (review round 3, H-P3-01);
- the single-mode oracle: x'' = -w^2 (x - q(t)) integrated on the flown dense output
  from rest at the resting value (DOP853, rtol 1e-10), which reproduces the ramp's exact
  peak where |sin(pi t_r/T)| = 1; on the configurations review round 1 found
  unconservative (a hot push whose clamp release is a step, an acceleration law capped
  in its rise, a taper entered in the rise, a power corner before the release at 5 Hz, a
  release just past a corner, a corner and a release inside the rise) and the release in
  tension the charged n_peak and F_peak are at least its maxima, the release swing at
  most the lowest load it keeps after the release and the charged compression at least
  the largest;
- a flat maximum (review round 3, P3-M1): on a hot force-law push without a carriage
  F_int = F_max and n m_v = (F_max + T)/g0 are flat from the end of the rise, so
  ``track_peaks`` keeps their earliest instant, t_r, whatever dm (rounding had placed them
  anywhere on the plateau);
- the exact maxima (KI-046, closed here): a cold force-law push whose 90 m stop taper
  begins during its 4 s rise peaks inside a sub-phase; with j = a_f/t_r the taper
  flies x'' = -(j t/s_t) x (x = L - s), Airy's equation, x = alpha Ai(-k t) + beta Bi(-k t)
  with k = (j/s_t)^(1/3), so n = (g + j t x/s_t)/g0 and F_int = M (g + j t x/s_t) peak at
  the root of x + t x' = 0, found here on the Airy closed form; ``track_peaks`` matches it
  to 1e-9 and the run metrics felt_g_track_peak and interface_force_peak_N carry it,
  above the sampled rows' maximum.

Closed forms at 1e-9 relative (the flown states at the final tolerance 1e-10 of the
shipped budget, rtol 1e-11 in 1-D). The transform: the record keys (structure_t_r_s the
drive's, structure_ramp_cost_rel null), the fixed point from dm = 0 to 1e-6 kg with its
contraction measured and recorded, vehicle_at bit-identical across call orders and
repeats, dm'(x) bounded and smooth and the fixed point uncapped on a plain, a tapered and a
cornered push (review round 2, P2-M1) and a hot push without a carriage (review round 3,
P3-M1), a full-load push that does not release refused at
build and an offload whose push does not release infeasible, constant_accel's transform
free of every flown key, the assumption line by mode and sizing basis. Slow: one
synthetic linear-motor structural case solved (no offload_nonmonotone; dm' and the
contraction recorded) and its x* under the 10x-tightened budget within 0.1%.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import math
import sys
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
from scipy.special import airy

from launchsim import cli, metrics, offload, sim, structure
from launchsim.assist.linear_motor import LinearMotorAssist
from launchsim.assist.track import VERTICAL, StraightTrack
from launchsim.config import (
    ResolvedExperiment,
    ResolvedRun,
    StructureCaseConfig,
    resolve_experiment,
    resolve_structure_settings,
)
from launchsim.constants import (
    G0_MPS2,
    MU_EARTH_M3S2,
    OFFLOAD_PER_KG_STAGE1_DRY,
    P_SEA_LEVEL_PA,
    R_EARTH_M,
)
from launchsim.dynamics import InverseSquareGravity
from launchsim.offload import NONMONOTONE_FLAG, OK_STATUS, planar_problem_factory, solve_offload
from launchsim.phases import IgnitionSpec, IntegratorSettings
from launchsim.search import INFEASIBLE, PreludeFailure
from launchsim.units import kn_to_n, n_to_kn, t_to_kg, w_to_mw
from launchsim.vehicle import Vehicle, with_offload, with_payload


def _load_support() -> ModuleType:
    """tests/structure_support.py, loaded by path (any pytest import mode)."""
    name = "structure_support"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ss = _load_support()
REPO = ss.REPO
EXPERIMENT = REPO / "experiments" / "silo_offload_2d.yaml"
SYNTHETIC_NAME = "tests/data/structure_synthetic.yaml"
REL = 1e-9
"""Closed forms against the flown push [relative]."""
F_AX_HZ = 3.0
"""The synthetic structure file's central axial frequency f [Hz] (T_ax = 1/f)."""
T_R_FILE_S = 0.8
"""The synthetic file's central assumed real-drive rise time [s], which a linear-motor
push does not use."""
G_REF = ss.G_EFF_MPS2
"""The planar track's g_eff [m/s^2] (28.5 deg, east)."""
F_MAX_N = 22.0e6
"""The short pushes' force limit F_max [N] (LM's force_max_kN)."""
T_R_S = 0.5
"""The short pushes' drive rise time t_r [s] (LM's force_rise_time_s)."""
E_KG_PER_KG = OFFLOAD_PER_KG_STAGE1_DRY
"""SP1's payload-equivalent of a kilogram of stage-1 dry mass E [kg/kg]."""
SLOPE_FLOOR = -1.0 / (2.0 * E_KG_PER_KG)
"""The monotonicity bound on dm'(x) [kg/kg] (design 4.4), as test_structure_pipeline."""
SMOOTH_TOL = 1.0e-5
"""How closely dm'(x) by 1 kg and 10 g differences agree [kg/kg]."""
CARRIAGE_T = 20.0
"""The hot carriage push's carriage mass [t]."""
ACCEL_CMD_G = 3.0
"""The acceleration-law pushes' command a_cmd [g0]."""
AIRY_STROKE_M = 100.0
"""The KI-046 push's stroke L [m]."""
AIRY_TAPER_M = 90.0
"""The KI-046 push's stop taper s_t [m] (it begins inside the rise)."""
AIRY_RISE_S = 4.0
"""The KI-046 push's force rise time t_r [s]."""
AIRY_ACCEL_G = 3.0
"""The KI-046 push's plateau net acceleration [g0]: F_max = M (AIRY_ACCEL_G g0 + g)."""
TENSION_CARRIAGE_T = 250.0
"""The release-in-tension push's carriage mass [t] (review round 3, H-P3-01)."""
TENSION_F_IMP = 0.5
"""The release-in-tension push's exhaust impingement fraction f_imp."""
TENSION_F_MAX_N = 6.0e6
"""The release-in-tension push's force limit F_max [N]."""
LM: dict[str, Any] = {
    "model": "linear_motor",
    "stroke_m": 30,
    "control": "force",
    "force_max_kN": n_to_kn(F_MAX_N),
    "power_max_MW": 5000,
    "force_rise_time_s": T_R_S,
    "brake_decel_g": 5,
    "drive_efficiency": 0.5,
    "track": {"angle_deg": 90, "exit_altitude_m": 0},
}
"""A short force-law push (30 m; P_max never binds) as YAML gives it."""
COLD = {"stage1": {"t_ign_s": 0.5, "reference": "release"}}
"""Stage 1 lit 0.5 s after the flown release: the push is cold."""
HOT = {"stage1": {"t_ign_s": -2.0, "reference": "push_start"}}
"""Stage 1 lit 2 s before the push start: its ramp ends there, full thrust on the push."""
TENSION = {
    **LM,
    "force_max_kN": n_to_kn(TENSION_F_MAX_N),
    "carriage_mass_t": TENSION_CARRIAGE_T,
    "exhaust_impingement_fraction": TENSION_F_IMP,
}
"""A hot force-law push (with HOT) whose interface is in tension at the release: F_int =
(m_v/M)(F_max + (1 - f_imp) T) - T, about -0.85 MN, so n_after = T/(m_v g0) exceeds
n_before (review round 3, H-P3-01, its probe5)."""


# --------------------------------------------------------------------------- helpers


def _resolved(variants: dict[str, dict[str, Any]]) -> ResolvedExperiment:
    """silo_offload_2d's shared blocks and pad with the given variants (no sweeps, no
    offload block)."""
    exp = ss.load_yaml(EXPERIMENT)
    veh = ss.load_yaml(REPO / exp["vehicle"])
    exp["variants"] = variants
    exp["sweeps"] = []
    exp.pop("offload", None)
    exp.pop("sensitivity", None)
    return resolve_experiment(exp, veh)


def _start(lm: dict[str, Any], ignition: dict[str, Any] | None = None) -> ResolvedRun:
    """The resolved planar run of one linear-motor variant."""
    return _resolved({"lm": {"assist": lm, "ignition": ignition or COLD}}).variants["lm"]


def _engine() -> tuple[float, float, float]:
    """Stage 1 of the gate vehicle: (its delivered thrust at the silo mouth, T_vac - p_sl
    A_e [N]; its mass flow at full thrust, T_vac/(g0 Isp_vac) [kg/s]; its linear startup
    ramp [s]), read from the vehicle file."""
    s1 = _start(LM).to_vehicle().stages[0]
    thrust = s1.thrust_vac_total_N - P_SEA_LEVEL_PA * s1.exit_area_total_m2
    return thrust, s1.mdot_full_kgps, s1.startup.t_ramp_s


@dataclasses.dataclass(frozen=True)
class Flown:
    """One flown push: the run, the vehicle at P_ref, its trace, the drive and the
    PushLoad."""

    start: ResolvedRun
    vehicle: Vehicle
    trace: Any
    assist: LinearMotorAssist
    push: structure.PushLoad


def _fly(lm: dict[str, Any], ignition: dict[str, Any] | None = None) -> Flown:
    """The push of the variant's vehicle at P_ref, flown alone and reduced
    (``sim.flown_push_trace``, ``sim.linear_motor_push_load``) on the synthetic layout."""
    start = _start(lm, ignition)
    v0 = start.to_vehicle()
    setup = sim.planar_setup(start.run, v0)
    ctx = sim.search_context(setup, v0, start.run.end)
    vehicle = with_payload(v0, ss.P_REF_KG)
    trace = sim.flown_push_trace(ctx, vehicle)
    assert isinstance(setup.assist, LinearMotorAssist)
    push = sim.linear_motor_push_load(trace, vehicle, setup.assist, _layout())
    return Flown(start, vehicle, trace, setup.assist, push)


def _sfile() -> Any:
    """The synthetic structure file, read through the CLI's reader."""
    return cli.read_structure_file(REPO / SYNTHETIC_NAME, SYNTHETIC_NAME)


def _layout() -> structure.StackLayout:
    """The synthetic file's StackLayout."""
    return _sfile().config.stack_layout()


def _coeffs(f_hz: float = F_AX_HZ) -> structure.StructureCoefficients:
    """The synthetic file's central coefficients, at axial frequency f_hz [Hz]."""
    coeffs = _sfile().config.coefficients()
    if f_hz == coeffs.axial_frequency_hz:
        return coeffs
    return dataclasses.replace(coeffs, axial_frequency_hz=f_hz)


def _dlf(t_r_s: float, f_hz: float = F_AX_HZ) -> float:
    """min(2, 1 + T_ax/(pi t_r)) at f_hz (2 at t_r = 0)."""
    if t_r_s == 0.0:
        return 2.0
    return min(2.0, 1.0 + (1.0 / f_hz) / (math.pi * t_r_s))


def _close(a: float, b: float, rel: float = REL) -> bool:
    """a and b within rel relative (no absolute floor)."""
    return math.isclose(a, b, rel_tol=rel, abs_tol=0.0)


def _tags(case: structure.LoadCase) -> list[str]:
    """The sample tags of a flown push's case ("push <tag>, <tag> t=<t> s")."""
    return case.label[len("push ") : case.label.rindex(" t=")].split(", ")


def _case(push: structure.PushLoad, tag: str) -> structure.LoadCase:
    """The push's one case whose label names tag."""
    (case,) = [c for c in push.cases if tag in _tags(c)]
    return case


def _m_fixed(vehicle: Vehicle) -> float:
    """Everything on the push but stage 1's propellant [kg]."""
    s1, s2 = vehicle.stages
    return s1.dry_mass_kg + s2.wet_mass_kg + vehicle.fairing_mass_kg + vehicle.payload_mass_kg


def _assert_requirement(
    push: structure.PushLoad,
    *,
    n_q: float,
    f_q: float,
    f_0: float,
    t_r: float,
    n_before: float,
    n_after: float,
    taper: tuple[float, float] | None = None,
    linear: bool = True,
) -> structure.PushRequirement:
    """The PushRequirement of push under rise_time (and the two other modes) against the
    closed forms: n_rest g/g0 and F_rest f_0; dlf_rise from the drive's t_r; the rise
    formula's n_0 + DLF (n_q - n_0) and F_0 + DLF (F_q - F_0); its release residual (DLF -
    1)(n_q - n_0) [+ (DLF_taper - 1) drop]; each charged value the larger of the formula's
    and the flown history's bound (n_bound_g, f_bound_N, release_bound_residual_g), the
    swing 2 n_after - peak and the compression after the release the peak itself (every
    push here unloads at its release, n_after <= n_before), the requirement's dlf the
    factor the charged n_peak carries; the bound replaces a formula's value only above
    FLOWN_BOUND_REL_TOL. linear: n and F_int rise linearly from rest to their plateau
    (cold pushes, the acceleration law), so the bound's envelopes equal the formula's
    peaks to rounding and the charged values are the formula's. quasi_static charges n_q;
    step charges n_0 + 2 (n_q - n_0) (a load that rises monotonically, falls only after
    its largest value: its total variation does not exceed that). taper: (the taper's time
    [s], its drop [g0])."""
    coeffs = _coeffs()
    n_0 = G_REF / G0_MPS2
    assert _close(push.n_rest_g, n_0, 1e-15) and _close(push.f_rest_N, f_0)
    assert push.ramp is None and push.rise_time_s == t_r and push.history is not None
    req = structure.push_requirement(push, coeffs, "rise_time")
    dlf = _dlf(t_r)
    assert req.dlf_rise is not None and _close(req.dlf_rise, dlf, 1e-15)
    assert req.rise_time_s == t_r != T_R_FILE_S
    assert req.accel_raise_mps2 == 0.0 and req.ramp_cost_rel is None
    assert _close(req.n_quasi_g, n_q)
    n_formula = n_0 + dlf * (n_q - n_0)
    f_formula = f_0 + dlf * (f_q - f_0)
    assert req.n_bound_g is not None and req.f_bound_N is not None
    assert req.release_bound_residual_g is not None
    if linear:
        assert _close(req.n_bound_g, n_formula, 1e-11) and _close(req.f_bound_N, f_formula, 1e-11)
        assert _close(req.n_peak_g, n_formula) and _close(req.f_peak_N, f_formula)
        assert req.dlf == req.dlf_rise
    else:
        tol = structure.FLOWN_BOUND_REL_TOL
        assert _close(req.n_peak_g, max(n_formula, req.n_bound_g), tol)
        assert _close(req.f_peak_N, max(f_formula, req.f_bound_N), tol)
        assert _close(req.dlf, (req.n_peak_g - n_0) / (n_q - n_0), 1e-12) and req.dlf >= dlf
    assert _close(req.release_n_before_g, n_before)
    assert req.release_n_after_g == pytest.approx(n_after, rel=REL, abs=1e-15)
    rise = (dlf - 1.0) * (n_q - n_0)
    assert _close(req.release_rise_residual_g or 0.0, rise)
    formula_rel = n_before + rise
    if taper is not None:
        t_taper, drop = taper
        dlf_t = _dlf(t_taper)
        assert _close(req.release_taper_time_s or 0.0, t_taper)
        assert _close(req.release_taper_dlf or 0.0, dlf_t)
        formula_rel += (dlf_t - 1.0) * drop
    else:
        assert req.release_taper_time_s is None and req.release_taper_dlf is None
    assert _close(req.release_rise_plateau_g or 0.0, n_q)
    peak_rel = max(formula_rel, n_before + req.release_bound_residual_g)
    assert _close(req.release_n_peak_g, peak_rel, structure.FLOWN_BOUND_REL_TOL)
    assert req.release_n_after_g <= req.release_n_before_g
    assert req.release_swing_g == pytest.approx(2.0 * n_after - peak_rel, rel=REL, abs=1e-12)
    assert req.release_compression_g == req.release_n_peak_g
    qs = structure.push_requirement(push, coeffs, "quasi_static")
    assert qs.dlf == 1.0 and _close(qs.n_peak_g, n_q) and qs.n_bound_g is None
    assert qs.release_n_peak_g == qs.release_n_before_g
    step = structure.push_requirement(push, coeffs, "step")
    assert _close(step.dlf, 2.0) and _close(step.n_peak_g, n_0 + 2.0 * (n_q - n_0))
    return req


# ------------------------------------------------------- the flown history's bound


W_3HZ = 2.0 * math.pi * F_AX_HZ
"""The synthetic file's axial circular frequency w = 2 pi f [rad/s]."""
BOUND_REL = 1e-10
"""The bound against its closed forms on PL loads [relative]: the slopes come from grid
differences, so their rounding (about 1e-12 measured) enters the sums."""


def _ramp_grid(
    pieces: list[tuple[float, float]], q_start: float, points: int = 201
) -> tuple[np.ndarray, np.ndarray]:
    """A PL load as FlownHistory lays it out: from q_start, each piece (duration [s],
    slope [unit/s]) on its own linspace of ``points`` entries, a boundary appearing at the
    end of one piece and the start of the next."""
    ts, qs = [], []
    t, q = 0.0, q_start
    for duration, slope in pieces:
        local = np.linspace(0.0, duration, points)
        ts.append(t + local)
        qs.append(q + slope * local)
        t, q = t + duration, q + slope * duration
    return np.concatenate(ts), np.concatenate(qs)


def test_the_bound_of_a_ramp_from_rest_is_the_rise_formula() -> None:
    """A load that ramps from rest (n_0 = 1) to a plateau 3 above over t_r and holds it 2
    s: rho = min(V, sum |D_k| min(1/w, max(0, t - t_k*))) saturates at min(Delta, 2 r/w) =
    (DLF - 1) Delta once the plateau has lasted, so the envelope is n_0 + DLF Delta, for
    t_r on either side of the cap (T/pi); inside the rise the ramp's start (a slope
    increase, t_k* = T/2) is uncharged for half a period, then r min(1/w, t - T/2) (the
    lagging mode stays below the ramp: -r sin(w t)/w <= 0 there); the release (slope 0)
    keeps 2 r/w; step charges the load plus its total variation, n_1 + V = 2 n_1 - n_0,
    quasi_static nothing."""
    n_0, delta = 1.0, 3.0
    for t_r in (0.5, 0.05):
        r = delta / t_r
        t, q = _ramp_grid([(t_r, r), (2.0, 0.0)], n_0)
        b = structure.single_mode_bound(t, q, n_0, 1.0 / F_AX_HZ, "rise_time")
        assert _close(b.envelope, n_0 + _dlf(t_r) * delta, BOUND_REL)
        assert _close(b.release_residual, (_dlf(t_r) - 1.0) * delta, BOUND_REL)
        rise = t <= t_r
        late = np.maximum(0.0, t[rise] - 0.5 / F_AX_HZ)
        expected = np.minimum(r * t[rise], r * np.minimum(late, 1.0 / W_3HZ))
        np.testing.assert_allclose(b.residual[rise], expected, rtol=BOUND_REL, atol=1e-11)
        s = structure.single_mode_bound(t, q, n_0, 1.0 / F_AX_HZ, "step")
        assert _close(s.envelope, n_0 + 2.0 * delta) and _close(s.release_residual, delta)
        qs = structure.single_mode_bound(t, q, n_0, 1.0 / F_AX_HZ, "quasi_static")
        assert qs.envelope == n_0 + delta and qs.release_residual == 0.0
        assert not np.any(qs.residual)


def test_the_bound_charges_a_step_at_push_start_and_an_early_peak() -> None:
    """M1 of review round 1. A step J at push start (a hot push's clamp release: the load
    jumps from its resting value) before a ramp: the envelope is n_1 + min(V, J + 2 r/w)
    with r the ramp's own slope, above the formula n_0 + DLF (n_1 - n_0) of the drive's
    t_r. A load that reaches its largest value at t' < t_r (an acceleration law capped in
    its rise) is charged 2 r/w = (DLF(t') - 1)(n_1 - n_0), the factor of t', not t_r."""
    n_0, n_1, t_r, jump = 1.0, 4.0, 0.5, 0.4
    r = (n_1 - n_0 - jump) / t_r
    t, q = _ramp_grid([(t_r, r), (2.0, 0.0)], n_0 + jump)
    b = structure.single_mode_bound(t, q, n_0, 1.0 / F_AX_HZ, "rise_time")
    assert _close(b.envelope, n_1 + min(n_1 - n_0, jump + 2.0 * r / W_3HZ), BOUND_REL)
    assert b.envelope > n_0 + _dlf(t_r) * (n_1 - n_0) + 0.3
    assert b.residual[0] == pytest.approx(jump, rel=1e-15)
    t_cap = 0.3
    r = (n_1 - n_0) / t_cap
    t, q = _ramp_grid([(t_cap, r), (2.0, 0.0)], n_0)
    b = structure.single_mode_bound(t, q, n_0, 1.0 / F_AX_HZ, "rise_time")
    assert _close(b.envelope, n_0 + _dlf(t_cap) * (n_1 - n_0), BOUND_REL)


def test_a_falling_corner_adds_to_the_release_not_to_the_envelope() -> None:
    """M2 of review round 1. A ramp (0.5 s), a plateau (1 s) and a fall at slope -s (1 s):
    a slope change contributes |D| min(tau, 1/w), nothing at its own instant, so a corner
    off a plateau leaves the envelope at n_1 + 2 r/w (the fall takes back what it adds; a
    corner inside a rise does not, the next test); at the
    release, cut while falling, the amplitude bound is the smallest of V, (sum |D| + |q'|)/w
    = 2 (r + s)/w and sum |D| min(tau, 2/w) = (4 r + 2 s)/w: 2 (r + s)/w, above the rise
    formula's 2 r/w by the corner's 2 s/w."""
    n_0, n_1, t_r, s = 1.0, 4.0, 0.5, 1.0
    r = (n_1 - n_0) / t_r
    t, q = _ramp_grid([(t_r, r), (1.0, 0.0), (1.0, -s)], n_0)
    b = structure.single_mode_bound(t, q, n_0, 1.0 / F_AX_HZ, "rise_time")
    assert _close(b.envelope, n_1 + 2.0 * r / W_3HZ, BOUND_REL)
    assert _close(b.release_residual, 2.0 * (r + s) / W_3HZ, BOUND_REL)
    st = structure.single_mode_bound(t, q, n_0, 1.0 / F_AX_HZ, "step")
    assert _close(st.release_residual, (n_1 - n_0) + s, BOUND_REL)


def test_a_corner_inside_a_rise_keeps_q_plus_rho_rising_for_1_over_w() -> None:
    """Review round 2, H-P2-02: a ramp of slope r from rest cut at t_c (past T/2 + 1/w) by
    a fall at -s. At the corner q + rho = n_0 + r t_c + r/w (the ramp's start charged r/w);
    the corner's term (r + s) min(tau, 1/w) outgrows the fall, so q + rho keeps rising at
    r for 1/w more, to the envelope n_0 + r t_c + 2 r/w at t_c + 1/w (part of the bound's
    conservatism on a corner inside a rise); the single mode's exact response, n_0 + r t
    - r sin(w t)/w before the corner and less s (t - t_c) - (r + s) sin(w (t - t_c))/w
    after it, stays below the envelope."""
    n_0, r, s, t_c = 1.0, 6.0, 4.0, 0.3
    t, q = _ramp_grid([(t_c, r), (1.0, -s)], n_0)
    b = structure.single_mode_bound(t, q, n_0, 1.0 / F_AX_HZ, "rise_time")
    k = int(np.flatnonzero(t == t_c)[-1])
    assert _close(q[k] + b.residual[k], n_0 + r * t_c + r / W_3HZ, BOUND_REL)
    assert _close(b.envelope, n_0 + r * t_c + 2.0 * r / W_3HZ, BOUND_REL)
    fine = np.linspace(0.0, float(t[-1]), 20001)
    after = np.maximum(fine - t_c, 0.0)
    exact = (
        np.interp(fine, t, q)
        - r * np.sin(W_3HZ * fine) / W_3HZ
        + (r + s) * np.sin(W_3HZ * after) / W_3HZ
    )
    assert float(exact.max()) <= b.envelope


def test_a_sub_phase_shorter_than_the_step_floor_is_a_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Review round 2, P2-M1: the planner leaves ASSIST sub-phases of 3e-15 to 1e-10 s at a
    stop taper's start and at a power corner, each scanned at 256 points, whose differences
    are rounding. A grid interval no longer than SINGLE_MODE_STEP_FRACTION T is a step: its
    change enters J and V, never a slope. A ramp, a plateau and a fall with a 1e-14 s
    sub-phase at the corner, its 256 values carrying 1 ulp of alternating noise, has the
    bound of the same history without it (within 1e-11: the noise's total variation, about
    5e-13, enters J and V); with the step rule of fix round 1 (a step only where dt = 0)
    those differences read as slopes of order 10 g0/s and lift the envelope."""
    n_0, r, s, t_c = 1.0, 6.0, 4.0, 1.5
    t1, q1 = _ramp_grid([(0.5, r), (1.0, 0.0)], n_0)
    t2, q2 = _ramp_grid([(0.5, -s)], float(q1[-1]))
    tiny_t = t_c + np.linspace(0.0, 1.0e-14, 256)
    sign = np.where(np.arange(256) % 2 == 0, 1.0, -1.0)
    tiny_q = q1[-1] + sign * np.spacing(q1[-1])
    tiny_q[0] = tiny_q[-1] = q1[-1]
    plain = (np.concatenate((t1, t_c + t2)), np.concatenate((q1, q2)))
    tiny = (np.concatenate((t1, tiny_t, t_c + 1.0e-14 + t2)), np.concatenate((q1, tiny_q, q2)))
    period = 1.0 / F_AX_HZ
    b0 = structure.single_mode_bound(*plain, n_0, period, "rise_time")
    b1 = structure.single_mode_bound(*tiny, n_0, period, "rise_time")
    assert b1.envelope == pytest.approx(b0.envelope, rel=0.0, abs=1e-11)
    assert b1.release_residual == pytest.approx(b0.release_residual, rel=0.0, abs=1e-11)
    assert _close(b0.envelope, n_0 + 3.0 + 2.0 * r / W_3HZ, BOUND_REL)
    monkeypatch.setattr(structure, "SINGLE_MODE_STEP_FRACTION", 0.0)
    old = structure.single_mode_bound(*tiny, n_0, period, "rise_time")
    assert old.envelope > b0.envelope + 0.1


def test_a_release_inside_the_rise_keeps_the_cut_ramp_s_residual() -> None:
    """H-P1-02 of review round 1: a ramp of slope r cut at t: the amplitude it leaves,
    (2 r/w)|sin(w t/2)| exactly, is bounded by r min(t, 2/w) (the release's slope cut
    included), which the rise formula's (DLF - 1) r t (t_r 0.5 s) undercharges once t
    exceeds about a tenth of a period."""
    r = 6.0
    for t_rel in (0.05, 0.3):
        t, q = _ramp_grid([(t_rel, r)], 1.0)
        b = structure.single_mode_bound(t, q, 1.0, 1.0 / F_AX_HZ, "rise_time")
        bound = r * min(t_rel, 2.0 / W_3HZ)
        assert _close(b.release_residual, bound, BOUND_REL)
        exact = 2.0 * r / W_3HZ * abs(math.sin(W_3HZ * t_rel / 2.0))
        assert exact <= b.release_residual * (1.0 + BOUND_REL)
    assert b.release_residual > (_dlf(T_R_S) - 1.0) * r * 0.3


def test_the_bound_weights_and_its_refusals() -> None:
    """A weight scales the envelope where it is constant (weighted = c x envelope) and is
    taken on the same breakpoints; a grid that decreases, arrays of other lengths, a
    non-finite grid or load, a weight off the grid, a period <= 0 and an unknown mode are
    refused; FlownHistory refuses a non-finite or one-entry array, arrays of other
    lengths, a grid that decreases, a case index off its grid, case kinds of another count
    and unknown kinds; a PushLoad's history indexes every case and goes with no
    RampedPlateau (review round 3, C-P3-02)."""
    t, q = _ramp_grid([(0.5, 6.0), (1.0, 0.0)], 1.0)
    period = 1.0 / F_AX_HZ
    b = structure.single_mode_bound(t, q, 1.0, period, "rise_time", (np.full(t.size, 2.5),))
    assert _close(b.weighted[0], 2.5 * b.envelope, 1e-15)
    t_nan, q_inf = t.copy(), q.copy()
    t_nan[3], q_inf[3] = math.nan, math.inf
    for args in (
        (t[::-1], q, 1.0, period, "rise_time"),
        (t, q[:-1], 1.0, period, "rise_time"),
        (t_nan, q, 1.0, period, "rise_time"),
        (t, q_inf, 1.0, period, "rise_time"),
        (t, q, 1.0, 0.0, "rise_time"),
        (t, q, 1.0, period, "nope"),
    ):
        with pytest.raises(ValueError):
            structure.single_mode_bound(*args)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        structure.single_mode_bound(t, q, 1.0, period, "rise_time", (np.ones(3),))
    good = {"t_s": t, "n_g": q, "f_N": q, "m_vehicle_kg": q, "m_prop1_kg": q}
    one = {"case_index": (0,), "case_kinds": (("n",),)}
    structure.FlownHistory(**good, **one)
    for arrays in (
        {**good, "n_g": q_inf},
        {**good, "f_N": q[:1], "t_s": t[:1], "n_g": q[:1], "m_vehicle_kg": q[:1],
         "m_prop1_kg": q[:1]},
        {**good, "m_prop1_kg": q[:-1]},
        {**good, "t_s": t[::-1]},
    ):  # fmt: skip
        with pytest.raises(ValueError):
            structure.FlownHistory(**arrays, **one)
    for kwargs in (
        {"case_index": (t.size,), "case_kinds": (("n",),)},
        {"case_index": (0,), "case_kinds": ()},
        {"case_index": (0,), "case_kinds": (("head",),)},
    ):
        with pytest.raises(ValueError):
            structure.FlownHistory(**good, **kwargs)
    push = _fly(LM).push
    with pytest.raises(ValueError, match="indexes every case"):
        dataclasses.replace(push, cases=push.cases[:1])
    with pytest.raises(ValueError, match="no RampedPlateau"):
        dataclasses.replace(push, ramp=structure.RampedPlateau(30.0, 60.0, 60.0))


def test_track_peaks_and_track_scan_refuse_what_they_cannot_read() -> None:
    """Review round 3, C-P3-02: ``track_scan`` and ``track_peaks`` refuse fewer than three
    scan points, a quantity count that does not match fn's (with the scan computed or
    given) and a phase that spans time without dense output (a search evaluation's);
    ``track_peaks`` refuses no phase and a scan list of another length."""
    phases = _fly(LM).trace.assist_phases()
    fn, count = metrics.track_felt_and_interface, metrics.FELT_AND_INTERFACE_COUNT
    scans = metrics.track_scan(phases, fn, count)
    no_dense = tuple(dataclasses.replace(res, dense=None) for res in phases)
    for call in (
        lambda: metrics.track_scan(phases, fn, count, n_points=2),
        lambda: metrics.track_scan(phases, fn, count + 1),
        lambda: metrics.track_scan(no_dense, fn, count),
        lambda: metrics.track_peaks((), fn, count),
        lambda: metrics.track_peaks(phases, fn, count, n_points=2),
        lambda: metrics.track_peaks(phases, fn, count + 1),
        lambda: metrics.track_peaks(phases, fn, count + 1, scans=scans),
        lambda: metrics.track_peaks(no_dense, fn, count),
        lambda: metrics.track_peaks(phases, fn, count, scans=scans[:-1]),
    ):
        with pytest.raises(ValueError):
            call()


# ------------------------------------------------------- closed forms of the push load


def test_cold_force_law_push_load_against_its_closed_forms() -> None:
    """A cold force-law push (30 m, F_max 22 MN, P_max never binding) on the vehicle at
    P_ref: n_q = F_max/(M g0) on the plateau, F_q = F_max (no carriage), n m_v and n
    m_prop1 on the same plateau (the contents do not change), n_0 = g/g0 and F_0 = M g;
    the max-n case on the plateau (from the end of the rise to the release: n is constant
    there, so ``track_peaks`` keeps its earliest instant, the end of the rise; review round
    3, P3-M1), the push start and the end of the rise
    (drive_ramp_end) among the cases, every sample tag named; the release at the track end
    on the plateau (n_before = n_q, n_after 0) with the stage-1 tanks full; the DLF of the
    drive's t_r 0.5 s (1.2122 at 3 Hz), not the file's 0.8 s; n and F_int ramp linearly
    from rest, so the flown history's bound equals the formula."""
    f = _fly(LM)
    v = f.vehicle
    m = v.liftoff_mass_kg()
    n_q = F_MAX_N / (m * G0_MPS2)
    plateau = _case(f.push, "max n")
    assert plateau.t_s == T_R_S and _close(plateau.n_g, n_q)
    assert _close(_case(f.push, "max F_int").interface_force_N or 0.0, F_MAX_N)
    assert _case(f.push, "push_start").t_s == 0.0
    assert _case(f.push, "drive_ramp_end").t_s == T_R_S
    assert {tag for c in f.push.cases for tag in _tags(c)} >= {*sim.PUSH_SAMPLE_TAGS}
    s1 = v.stages[0]
    f1 = _layout().stage1.lox_mass_fraction
    assert _close(plateau.lox_stage1_kg, f1 * s1.propellant_mass_kg)
    rel = f.push.release.case
    assert rel.t_s == f.trace.t_release_s and _close(rel.n_g, n_q)
    req = _assert_requirement(
        f.push, n_q=n_q, f_q=F_MAX_N, f_0=m * G_REF, t_r=T_R_S, n_before=n_q, n_after=0.0
    )
    assert _close(req.release_bound_residual_g or 0.0, req.release_rise_residual_g or 0.0, 1e-11)
    assert _close(_dlf(T_R_S), 1.0 + 1.0 / (3.0 * math.pi * 0.5), 1e-15)


def test_hot_force_law_with_a_carriage_peaks_at_different_instants(
    request: pytest.FixtureRequest,
) -> None:
    """Hot (lit 2 s before the push start: the hold burned mdot x 1 s, full sea-level
    thrust T on the push), a 20 t carriage and f_imp 0.5: n(t) = (F_max + T/2)/(M(t) g0)
    rises to the release, where the max-n case sits; F_int = (m_v/M)(F_max + T/2) - T, n
    m_v and n m_prop1 fall on the plateau, so their cases sit at the end of the rise t_r;
    masses from the closed-form burn m_v(t) = m_v(0) - mdot t; n_0 = g/g0 and F_0 = m_v(0)
    g - T (the hold's); n_after = T/(m_v g0) at the release. The flown loads curve (the
    mass burns), so the history's bound may exceed the formula: by under 1e-4 relative
    here (recorded)."""
    thrust, mdot, t_ramp = _engine()
    lm = {**LM, "carriage_mass_t": CARRIAGE_T, "exhaust_impingement_fraction": 0.5}
    f = _fly(lm, HOT)
    v = f.vehicle
    m_c = float(t_to_kg(CARRIAGE_T))
    m_v0 = v.liftoff_mass_kg() - mdot * t_ramp / 2.0
    lift = F_MAX_N + 0.5 * thrust
    t_rel = f.trace.t_release_s
    m_rel = m_v0 - mdot * t_rel
    m_r = m_v0 - mdot * T_R_S
    n_q = lift / ((m_rel + m_c) * G0_MPS2)
    f_q = m_r / (m_r + m_c) * lift - thrust
    top = _case(f.push, "max n")
    assert top.t_s == t_rel and _close(top.n_g, n_q) and _close(top.vehicle_mass_kg, m_rel)
    for tag in ("max F_int", "max n m_v", "max n m_prop1"):
        assert _case(f.push, tag).t_s == T_R_S, tag
    assert _close(_case(f.push, "max F_int").interface_force_N or 0.0, f_q)
    assert _close(top.thrust_N, thrust)
    s1 = v.stages[0]
    prop_rel = s1.propellant_mass_kg - mdot * (t_ramp / 2.0 + t_rel)
    f1 = _layout().stage1.lox_mass_fraction
    assert _close(f.push.release.case.lox_stage1_kg, f1 * prop_rel)
    assert _close(_case(f.push, "max n m_v").vehicle_mass_kg, m_r)
    f_0 = m_v0 * G_REF - thrust
    req = _assert_requirement(
        f.push,
        n_q=n_q,
        f_q=f_q,
        f_0=f_0,
        t_r=T_R_S,
        n_before=n_q,
        n_after=thrust / (m_rel * G0_MPS2),
        linear=False,
    )
    n_0 = G_REF / G0_MPS2
    excess_n = req.n_peak_g / (n_0 + _dlf(T_R_S) * (n_q - n_0)) - 1.0
    excess_f = req.f_peak_N / (f_0 + _dlf(T_R_S) * (f_q - f_0)) - 1.0
    request.node.user_properties.append(("bound_excess_rel", (excess_n, excess_f)))
    assert -1e-12 <= excess_n < 1e-4 and -1e-12 <= excess_f < 1e-4


@pytest.mark.parametrize("hot", [False, True])
def test_acceleration_law_push_load_against_its_closed_forms(hot: bool) -> None:
    """The acceleration law at a_cmd = 3 g0 (F_max 40 MN and P_max never binding): n_q =
    (a + g)/g0 on the plateau; cold F_q = m_v (a + g), hot F_q = m_v(t_r)(a + g) - T at the
    end of the rise (m_v falls), the release at the track end with n_before = n_q. The hot
    push rides a 250 t carriage: its command starts from 0, so the drive holds M g - T at
    push start, which the full thrust would make negative on the vehicle alone (a
    drive_limit stop). n ramps linearly from rest under this law, and so does the cold
    F_int; the hot F_int curves with the burning mass (the bound may exceed the formula)."""
    thrust, mdot, t_ramp = _engine()
    lm = {**LM, "control": "acceleration", "accel_command_g": ACCEL_CMD_G, "force_max_kN": 40000}
    if hot:
        lm["carriage_mass_t"] = 250.0
    f = _fly(lm, HOT if hot else COLD)
    v = f.vehicle
    a = ACCEL_CMD_G * G0_MPS2
    n_q = (a + G_REF) / G0_MPS2
    burn = mdot * t_ramp / 2.0 if hot else 0.0
    m_v0 = v.liftoff_mass_kg() - burn
    on = thrust if hot else 0.0
    m_r = m_v0 - (mdot * T_R_S if hot else 0.0)
    f_q = m_r * (a + G_REF) - on
    assert _close(_case(f.push, "max F_int").interface_force_N or 0.0, f_q)
    m_rel = m_v0 - (mdot * f.trace.t_release_s if hot else 0.0)
    _assert_requirement(
        f.push,
        n_q=n_q,
        f_q=f_q,
        f_0=m_v0 * G_REF - on,
        t_r=T_R_S,
        n_before=n_q,
        n_after=on / (m_rel * G0_MPS2),
        linear=not hot,
    )


def test_release_at_a_target_speed_in_the_power_phase() -> None:
    """A cold force-law push with a corner at v_c = 30 m/s (P_max = 30 F_max) released at
    40 m/s in its power phase: n_before = P_max/(v_release M g0), below n_q = F_max/(M
    g0); the release time t_r + (v_c - v_r)/a_f + [(v_c - v) + v_inf ln((v_inf - v_c)/
    (v_inf - v))]/g (the vertical power phase, v_inf = P/(M g)); the release peak n_before
    + the larger of (DLF - 1)(n_q - n_0) and the bound (the corner's slope change and the
    release's cut charged: here the bound governs, M2 of review round 1); under step the
    release carries the total variation (n_q - n_0) + (n_q - n_before), the fall
    included."""
    v_c, v_rel = 30.0, 40.0
    p_max = F_MAX_N * v_c
    lm = {**LM, "stroke_m": 100, "power_max_MW": w_to_mw(p_max), "release_speed_mps": v_rel}
    f = _fly(lm)
    m = f.vehicle.liftoff_mass_kg()
    a_f = F_MAX_N / m - G_REF
    v_r = a_f * T_R_S / 2.0
    v_inf = p_max / (m * G_REF)
    t_c = T_R_S + (v_c - v_r) / a_f
    dt = ((v_c - v_rel) + v_inf * math.log((v_inf - v_c) / (v_inf - v_rel))) / G_REF
    rel = f.push.release.case
    assert _close(rel.t_s, t_c + dt)
    n_q = F_MAX_N / (m * G0_MPS2)
    n_before = p_max / (v_rel * m * G0_MPS2)
    assert n_before < n_q and _close(rel.n_g, n_before)
    req = _assert_requirement(
        f.push,
        n_q=n_q,
        f_q=F_MAX_N,
        f_0=m * G_REF,
        t_r=T_R_S,
        n_before=n_before,
        n_after=0.0,
        linear=False,
    )
    assert (req.release_bound_residual_g or 0.0) > (req.release_rise_residual_g or 0.0)
    n_0 = G_REF / G0_MPS2
    step = structure.push_requirement(f.push, _coeffs(), "step")
    total = (n_q - n_0) + (n_q - n_before)
    assert _close(step.release_n_peak_g, n_before + total, 1e-11)


def test_release_inside_the_rise_carries_the_cut_ramp() -> None:
    """H-P1-02 and H-P1-03 of review round 1: a cold force-law push released at 1 m/s,
    inside its 0.5 s rise: n rises through the rise, so n_before = n_q = n(t_rel) =
    g/g0 + r t_rel with r = (F_max/M - g)/(g0 t_r) and t_rel = sqrt(2 t_r v/a_f); the
    release residual is the cut ramp's bound r min(t_rel, 2/w) = 2 r/w (t_rel > 2/w at
    3 Hz), not the formula's (DLF - 1) r t_rel; the release unloads (cold: n_after = 0)
    and its compression is the release peak (review round 4, C-P4-02)."""
    v_rel = 1.0
    f = _fly({**LM, "release_speed_mps": v_rel})
    m = f.vehicle.liftoff_mass_kg()
    a_f = F_MAX_N / m - G_REF
    t_rel = math.sqrt(2.0 * T_R_S * v_rel / a_f)
    r = a_f / (G0_MPS2 * T_R_S)
    n_q = G_REF / G0_MPS2 + r * t_rel
    assert _close(f.push.release.case.t_s, t_rel) and _close(f.push.release.n_before_g, n_q)
    req = structure.push_requirement(f.push, _coeffs(), "rise_time")
    assert _close(req.n_quasi_g, n_q) and t_rel > 2.0 / W_3HZ
    assert _close(req.release_bound_residual_g or 0.0, 2.0 * r / W_3HZ, 1e-9)
    assert _close(req.release_n_peak_g, n_q + 2.0 * r / W_3HZ, 1e-9)
    assert (req.release_rise_residual_g or 0.0) < 0.5 * 2.0 * r / W_3HZ
    assert req.release_n_after_g <= req.release_n_before_g
    assert req.release_compression_g == req.release_n_peak_g


@pytest.mark.parametrize(("s_t", "length"), [(40.0, 100.0), (10.0, 50.0)])
def test_release_after_a_stop_taper_uses_the_tapers_own_factor(s_t: float, length: float) -> None:
    """A cold force-law push with a stop taper after its rise (40 m of 100; 10 m of 50,
    TAPERED, whose taper_start leaves a 4.7e-14 s sub-phase): on the taper x'' = -(a_f/s_t)
    x, so it takes atan(s_t Omega/v_0)/Omega (Omega = sqrt(a_f/s_t), v_0 the speed at L -
    s_t), ends at the holding force (n_before = n_0) and drops the load by n_q - n_0; the
    rise formula's release peak n_0 + (DLF - 1)(n_q - n_0) + (DLF_taper - 1)(n_q - n_0)
    with DLF_taper = min(2, 1 + T_ax/(pi t_taper)), or the bound's where larger. n and
    F_int ramp linearly from rest to a plateau that outlasts the bound's saturation, and
    the taper's fall only lowers q + rho, so the bound's envelopes equal the formula's
    (review round 2, P2-M1: before SINGLE_MODE_STEP_FRACTION the 10 m taper's tiny
    sub-phase lifted n_bound to 6.35 g0 against the formula's 4.54)."""
    f = _fly({**LM, "stroke_m": length, "stop_taper_m": s_t})
    m = f.vehicle.liftoff_mass_kg()
    a_f = F_MAX_N / m - G_REF
    v_r, s_r = a_f * T_R_S / 2.0, a_f * T_R_S**2 / 6.0
    v_0 = math.sqrt(v_r * v_r + 2.0 * a_f * (length - s_t - s_r))
    omega = math.sqrt(a_f / s_t)
    t_taper = math.atan(s_t * omega / v_0) / omega
    n_q, n_0 = F_MAX_N / (m * G0_MPS2), G_REF / G0_MPS2
    _assert_requirement(
        f.push,
        n_q=n_q,
        f_q=F_MAX_N,
        f_0=m * G_REF,
        t_r=T_R_S,
        n_before=n_0,
        n_after=0.0,
        taper=(t_taper, n_q - n_0),
    )
    assert f.push.release.taper_time_s is not None and _close(f.push.release.taper_time_s, t_taper)


def test_a_release_in_tension_loads_the_stack() -> None:
    """Review round 3, H-P3-01: TENSION (hot, F_max 6 MN, a 250 t carriage, f_imp 0.5)
    releases with the interface in tension, F_int = (m_v/M)(F_max + T/2) - T < 0, so n_after
    = T/(m_v g0) exceeds n_before = (F_max + T/2)/(M g0) (M = m_v + m_c, m_v(t) = m_v(0) -
    mdot t, the closed forms of the hot carriage test). The drop to n_after is a rise: with
    A = n_peak,rel - n_before the mode keeps about n_after at most (n_after - n_before) + A,
    so the swing is n_before - A, the compression after the release 2 n_after - n_before +
    A (above n_peak,rel and n_peak), and the swing with every residual damped n_before
    (quasi_static, A = 0: the swing n_before and the compression 2 n_after - n_before)."""
    thrust, mdot, t_ramp = _engine()
    f = _fly(TENSION, HOT)
    m_c = float(t_to_kg(TENSION_CARRIAGE_T))
    m_rel = f.vehicle.liftoff_mass_kg() - mdot * (t_ramp / 2.0 + f.trace.t_release_s)
    lift = TENSION_F_MAX_N + (1.0 - TENSION_F_IMP) * thrust
    n_before = lift / ((m_rel + m_c) * G0_MPS2)
    n_after = thrust / (m_rel * G0_MPS2)
    f_rel = m_rel / (m_rel + m_c) * lift - thrust
    rel = f.push.release
    assert _close(rel.case.interface_force_N or 0.0, f_rel) and f_rel < 0.0
    assert _close(rel.n_before_g, n_before) and _close(rel.n_after_g, n_after)
    assert n_after > n_before
    for mode in ("rise_time", "quasi_static"):
        req = structure.push_requirement(f.push, _coeffs(), mode)  # type: ignore[arg-type]
        amp = req.release_n_peak_g - req.release_n_before_g
        assert amp >= 0.0 and (amp == 0.0) is (mode == "quasi_static")
        assert req.release_swing_g == pytest.approx(n_before - amp, rel=1e-12)
        assert req.release_compression_g is not None
        top = 2.0 * n_after - n_before + amp
        assert req.release_compression_g == pytest.approx(top, rel=1e-12)
        assert req.release_swing_plateau_g == pytest.approx(n_before, rel=1e-12)
        assert req.release_compression_g > max(req.release_n_peak_g, req.n_peak_g) + 0.1


def test_a_flown_release_state_refuses_an_incomplete_taper() -> None:
    """``ReleaseState``'s flown fields: a taper states its time and its drop together, only
    on a flown release (rise_plateau_g given), neither negative; rise_plateau_g finite;
    ``from_flown_push`` is True exactly when rise_plateau_g is given (constant_accel's
    state is not, and ``push_requirement`` then keeps S2's arithmetic: no release key of a
    flown push set)."""
    case = _fly(LM).push.release.case
    base = structure.ReleaseState(4.0, 0.0, case)
    assert not base.from_flown_push
    assert structure.ReleaseState(4.0, 0.0, case, rise_plateau_g=4.0).from_flown_push
    bad: list[dict[str, Any]] = [
        {"rise_plateau_g": 4.0, "taper_time_s": 0.5},
        {"rise_plateau_g": 4.0, "taper_drop_g": 1.0},
        {"taper_time_s": 0.5, "taper_drop_g": 1.0},
        {"rise_plateau_g": 4.0, "taper_time_s": -0.1, "taper_drop_g": 1.0},
        {"rise_plateau_g": 4.0, "taper_time_s": 0.5, "taper_drop_g": -1.0},
        {"rise_plateau_g": math.inf},
    ]
    for kwargs in bad:
        with pytest.raises(ValueError):
            structure.ReleaseState(4.0, 0.0, case, **kwargs)
    push = dataclasses.replace(_fly(LM).push, release=base, history=None)
    req = structure.push_requirement(push, _coeffs(), "rise_time")
    assert req.release_rise_plateau_g is None and req.release_taper_dlf is None
    assert req.release_bound_residual_g is None and req.dlf_rise is None
    assert req.release_n_peak_g == structure.peak_load(4.0, push.n_rest_g, req.dlf)


# ------------------------------------------------------- the single-mode oracle


def _oracle(trace: Any, which: int, rest: float, f_hz: float) -> tuple[float, float, float]:
    """The single mode x'' = -w^2 (x - q(t)), w = 2 pi f_hz, driven by the flown load q
    (which = 0: the felt load n [g0]; 1: the interface force [N];
    ``metrics.track_felt_and_interface`` on the dense output) from rest at q = rest at push
    start, DOP853 at rtol 1e-10 over every ASSIST sub-phase: (the largest x over the
    push, its local maxima refined at the roots of x' on 2001 samples per sub-phase; x
    and x' at the release)."""
    w = 2.0 * math.pi * f_hz
    state = np.array([rest, 0.0])
    top = rest
    scale = 1.0 if which == 0 else 1.0e6
    for res in trace.assist_phases():
        if res.span_s <= 0.0:
            continue
        params, dense = res.spec.params, res.dense

        def rhs(t: float, s: np.ndarray, params: Any = params, dense: Any = dense) -> list[float]:
            q = metrics.track_felt_and_interface(t, np.asarray(dense(t), dtype=float), params)
            return [s[1], -w * w * (s[0] - q[which])]

        sol = solve_ivp(
            rhs,
            (res.spec.t0, res.t_end),
            state,
            method="DOP853",
            rtol=1e-10,
            atol=1e-12 * scale,
            dense_output=True,
        )
        ts = np.linspace(res.spec.t0, res.t_end, 2001)
        xs, vs = sol.sol(ts)
        top = max(top, float(xs.max()))
        for i in np.flatnonzero((vs[:-1] > 0.0) & (vs[1:] <= 0.0)):
            t_star = brentq(lambda t, sol=sol: float(sol.sol(t)[1]), ts[i], ts[i + 1], xtol=1e-13)
            top = max(top, float(sol.sol(t_star)[0]))
        state = sol.y[:, -1]
    return top, float(state[0]), float(state[1])


def test_the_oracle_reproduces_the_ramp_s_exact_peak() -> None:
    """The oracle against the classical rise-time result on the cold 30 m push (n and
    F_int ramp linearly from rest over t_r 0.5 s to a plateau that lasts beyond the
    peak): at 3 Hz t_r/T = 1.5, where |sin(pi t_r/T)| = 1, so the exact peak is the
    formula n_0 + DLF (n_q - n_0) (and F likewise) within 1e-7."""
    f = _fly(LM)
    m = f.vehicle.liftoff_mass_kg()
    n_0 = G_REF / G0_MPS2
    n_q = F_MAX_N / (m * G0_MPS2)
    n_top, _x, _v = _oracle(f.trace, 0, f.push.n_rest_g, F_AX_HZ)
    f_top, _x, _v = _oracle(f.trace, 1, f.push.f_rest_N, F_AX_HZ)
    assert _close(n_top, n_0 + _dlf(T_R_S) * (n_q - n_0), 1e-7)
    assert _close(f_top, m * G_REF + _dlf(T_R_S) * (F_MAX_N - m * G_REF), 1e-7)


def _airy_lm() -> dict[str, Any]:
    """The KI-046 push: F_max = M (AIRY_ACCEL_G g0 + g), t_r AIRY_RISE_S, a taper of
    AIRY_TAPER_M on a stroke of AIRY_STROKE_M (3 g0, 4 s, 90 m of 100: the taper begins
    about 2 s into the rise)."""
    v = with_payload(_start(LM).to_vehicle(), ss.P_REF_KG)
    f_max = v.liftoff_mass_kg() * (AIRY_ACCEL_G * G0_MPS2 + G_REF)
    return {
        **LM,
        "stroke_m": AIRY_STROKE_M,
        "stop_taper_m": AIRY_TAPER_M,
        "force_rise_time_s": AIRY_RISE_S,
        "force_max_kN": n_to_kn(f_max),
    }


ACCEL_CAPPED = {
    **LM,
    "control": "acceleration",
    "accel_command_g": ACCEL_CMD_G,
    "force_max_kN": 15000,
    "stroke_m": 80,
}
"""An acceleration law at 3 g0 capped by F_max 15 MN inside its rise."""
FIXED_R07 = {
    **LM,
    "force_max_kN": 24000,
    "power_max_MW": w_to_mw(0.7 * kn_to_n(24000) * 77.0),
    "stroke_m": 100,
}
"""A force law like design table B's lm_fixed_r07 (F_max 24 MN, P_max 0.7 F_max x 77 m/s),
released at the track end after its power corner."""
ORACLE_CASES: dict[str, tuple[Any, dict[str, Any], float]] = {
    "hot_step_tr05_5hz": (LM, HOT, 5.0),
    "hot_step_tr2_3hz": ({**LM, "force_rise_time_s": 2.0, "stroke_m": 60}, HOT, 3.0),
    "hot_step_tr2_5hz": ({**LM, "force_rise_time_s": 2.0, "stroke_m": 60}, HOT, 5.0),
    "accel_capped_tr2_3hz": ({**ACCEL_CAPPED, "force_rise_time_s": 2.0}, COLD, 3.0),
    "accel_capped_tr05_5hz": (ACCEL_CAPPED, COLD, 5.0),
    "taper_in_rise_5hz": (_airy_lm, COLD, 5.0),
    "fixed_r07_like_5hz": (FIXED_R07, COLD, 5.0),
    "release_past_corner_3hz": (
        {
            **LM,
            "force_rise_time_s": 1.0,
            "power_max_MW": w_to_mw(F_MAX_N * 10.0),
            "stroke_m": 100,
            "release_speed_mps": 12.0,
        },
        COLD,
        3.0,
    ),
    "release_past_corner_5hz": (
        {
            **LM,
            "force_rise_time_s": 1.0,
            "power_max_MW": w_to_mw(F_MAX_N * 10.0),
            "stroke_m": 100,
            "release_speed_mps": 12.0,
        },
        COLD,
        5.0,
    ),
    "corner_in_rise_vc5_3hz": ({**LM, "power_max_MW": w_to_mw(F_MAX_N * 5.0)}, COLD, 3.0),
    "release_in_rise_1mps_3hz": ({**LM, "release_speed_mps": 1.0}, COLD, 3.0),
    "release_in_tension_3hz": (TENSION, HOT, 3.0),
    "release_in_tension_5hz": (TENSION, HOT, 5.0),
}
"""The configurations review round 1 found the rise formula unconservative on (M1: a hot
push whose clamp release is a step: with the default carriage 0 t and f_imp 0 the thrust
exceeds the weight, so the drive's force at push start is 0 and F_int steps at clamp
release from F_0 = m_v g - T, about -2.04 MN, to 0; an acceleration law capped in its
rise; a taper entered in the rise; M2: a corner before
a release at the track end, at 5 Hz, and a target-speed release just past a 10 m/s
corner; H-P1-02: a 5 m/s corner inside the rise and a release at 1 m/s inside it), and
the release in tension of review round 3 (H-P3-01: TENSION, whose release loads the
stack), each with the axial frequency of the check (the synthetic file's at another
value)."""


@pytest.mark.parametrize("name", sorted(ORACLE_CASES))
def test_the_charged_push_bounds_the_single_mode_oracle(
    name: str, request: pytest.FixtureRequest
) -> None:
    """Review round 1 (M1, M2, H-P1-02, m3) and round 3 (H-P3-01): on each configuration
    the charged n_peak and F_peak (rise_time, the larger of the formula and the flown
    history's bound) are at least the single-mode oracle's maxima of n and F_int, the
    charged release swing is at most the lowest load the oracle keeps after the release
    (n_after less the amplitude about n_after) and the charged compression after the
    release at least the largest (n_after plus it); the margins are recorded (F's relative
    to |F|: the release in tension's interface force is negative throughout)."""
    lm, ignition, f_hz = ORACLE_CASES[name]
    f = _fly(lm() if callable(lm) else lm, ignition)
    req = structure.push_requirement(f.push, _coeffs(f_hz), "rise_time")
    n_top, x_rel, v_rel = _oracle(f.trace, 0, f.push.n_rest_g, f_hz)
    f_top, _x, _v = _oracle(f.trace, 1, f.push.f_rest_N, f_hz)
    w = 2.0 * math.pi * f_hz
    after = req.release_n_after_g
    kept = math.hypot(x_rel - after, v_rel / w)
    assert req.release_compression_g is not None
    margins = (
        req.n_peak_g - n_top,
        (req.f_peak_N - f_top) / abs(f_top),
        (after - kept) - req.release_swing_g,
        req.release_compression_g - (after + kept),
    )
    request.node.user_properties.append(("margins_n_g_F_rel_swing_g_compression_g", margins))
    assert req.n_peak_g >= n_top - 1e-9
    assert req.f_peak_N >= f_top - 1e-9 * abs(f_top)
    assert req.release_swing_g <= after - kept + 1e-9
    assert req.release_compression_g >= after + kept - 1e-9


# ----------------------------------------------------- the exact maxima (KI-046)


def _airy_peak(length: float, s_t: float, t_r: float) -> tuple[float, float]:
    """(t*, t* x(t*)) of a cold vertical force-law push from the holding force with F_max
    = M (AIRY_ACCEL_G g0 + g), whose stop taper over the last s_t metres begins inside its
    rise of t_r: s = j t^3/6 to the taper start (j = AIRY_ACCEL_G g0/t_r, whatever M and
    g), then Airy's x'' = -(j t/s_t) x; the maximum of t x on the taper inside the rise,
    from the root of x + t x' = 0."""
    j = AIRY_ACCEL_G * G0_MPS2 / t_r
    t_1 = (6.0 * (length - s_t) / j) ** (1.0 / 3.0)
    v_1 = j * t_1 * t_1 / 2.0
    k = (j / s_t) ** (1.0 / 3.0)
    ai, aip, bi, bip = airy(-k * t_1)
    alpha, beta = np.linalg.solve(np.array([[ai, bi], [-k * aip, -k * bip]]), [s_t, -v_1])

    def x(t: float) -> float:
        a_i, _a, b_i, _b = airy(-k * t)
        return float(alpha * a_i + beta * b_i)

    def dx(t: float) -> float:
        _a, a_p, _b, b_p = airy(-k * t)
        return float(-k * (alpha * a_p + beta * b_p))

    def slope(t: float) -> float:
        return x(t) + t * dx(t)

    assert slope(t_1) > 0.0 > slope(t_r)
    t_star = brentq(slope, t_1, t_r, xtol=1e-14, rtol=4 * np.finfo(float).eps)
    return t_star, t_star * x(t_star)


def test_track_peaks_find_the_interior_peak_of_a_taper_entered_in_the_rise() -> None:
    """KI-046: a cold planar force-law push, F_max = M (3 g0 + g), t_r 4 s, a 90 m taper on
    a 100 m stroke (the taper begins about 2 s into the rise). ``track_peaks`` locates the
    felt-g and interface-force maxima inside a sub-phase at Airy's closed form: n = (g + j
    (t x)*/s_t)/g0 and F_int = M (g + j (t x)*/s_t) within 1e-9, the time within 1e-4 s;
    the reduced push's max-n case is that state."""
    length, s_t, t_r = AIRY_STROKE_M, AIRY_TAPER_M, AIRY_RISE_S
    f = _fly(_airy_lm())
    m = f.vehicle.liftoff_mass_kg()
    t_star, tx = _airy_peak(length, s_t, t_r)
    j = AIRY_ACCEL_G * G0_MPS2 / t_r
    n_star = (G_REF + j * tx / s_t) / G0_MPS2
    felt, f_int = metrics.track_peaks(
        f.trace.assist_phases(), metrics.track_felt_and_interface, metrics.FELT_AND_INTERFACE_COUNT
    )
    assert _close(felt.value, n_star) and abs(felt.t_s - t_star) < 1e-4
    assert _close(f_int.value, m * (G_REF + j * tx / s_t))
    assert _case(f.push, "max n").t_s == felt.t_s
    peaks = metrics.linear_motor_track_peaks(f.trace)
    assert peaks["felt_g_track_peak"] == felt.value
    assert peaks["interface_force_peak_N"] == peaks["peak_interface_force_N"] == f_int.value


def test_run_metrics_carry_the_exact_track_peak_on_a_linear_motor_run(f9_vehicle: Vehicle) -> None:
    """The same push in 1-D (``sim.simulate`` on the generic F9, g = mu/R_E^2, rtol
    1e-11): felt_g_track_peak and interface_force_peak_N (and its alias) equal the Airy
    peak within 1e-9 and lie above the sampled rows' maximum (by about 2e-5 relative, the
    gap KI-046 measured); the run-wide peak is never below the track's
    (``metrics.run_wide_felt_with_track_peak``, lifted when the track peak exceeds the
    sampled run-wide value)."""
    g = MU_EARTH_M3S2 / R_EARTH_M**2
    length, s_t, t_r = AIRY_STROKE_M, AIRY_TAPER_M, AIRY_RISE_S
    m = f9_vehicle.liftoff_mass_kg()
    model = LinearMotorAssist(
        control="force",
        force_max_N=m * (AIRY_ACCEL_G * G0_MPS2 + g),
        power_max_W=5.0e9,
        rise_time_s=t_r,
        carriage_mass_kg=0.0,
        brake_decel_mps2=5.0 * G0_MPS2,
        stop_taper_m=s_t,
        g_eff_mps2=g,
    )
    specs = {name: IgnitionSpec() for name in f9_vehicle.stage_names}
    specs[f9_vehicle.stage_names[0]] = IgnitionSpec(0.5)
    result = sim.simulate(
        vehicle=f9_vehicle,
        ignition=specs,
        gravity=InverseSquareGravity(MU_EARTH_M3S2),
        g_eff_mps2=g,
        assist=model,
        track=StraightTrack(length, VERTICAL, -length),
        start=None,
        end="stage1_burnout",
        settings=IntegratorSettings(rtol=1e-11),
    )
    t_star, tx = _airy_peak(length, s_t, t_r)
    j = AIRY_ACCEL_G * G0_MPS2 / t_r
    met = result.metrics
    assert _close(met["felt_g_track_peak"], (g + j * tx / s_t) / G0_MPS2)
    assert _close(met["interface_force_peak_N"], m * (g + j * tx / s_t))
    assert met["peak_interface_force_N"] == met["interface_force_peak_N"]
    assert abs(met["felt_g_track_peak_t_s"] - (t_star - met["push_time_s"])) < 1e-4
    rows = result.timeseries[result.timeseries["phase"] == "ASSIST"]
    sampled = float(rows["accel_felt_g"].max())
    gap = met["felt_g_track_peak"] / sampled - 1.0
    assert 1e-7 < gap < 1e-4, gap
    assert float(rows["interface_force_N"].max()) < met["interface_force_peak_N"]
    assert met["peak_felt_axial_g"] >= met["felt_g_track_peak"]
    lifted = metrics.run_wide_felt_with_track_peak(
        {**met, "peak_felt_axial_g": sampled, "peak_felt_axial_g_phase": "ASSIST"}
    )
    assert lifted == {
        "peak_felt_axial_g": met["felt_g_track_peak"],
        "peak_felt_axial_g_t_s": met["felt_g_track_peak_t_s"],
        "peak_felt_axial_g_mass_kg": met["felt_g_track_peak_mass_kg"],
        "peak_felt_axial_g_phase": "ASSIST",
    }
    assert metrics.run_wide_felt_with_track_peak(met) == {}


def test_a_flat_maximum_keeps_its_earliest_instant() -> None:
    """Review round 3, P3-M1: SHORT lit 2 s before its push (HOT) with no carriage and f_imp
    0. On the force plateau M = m_v, so F_int = F_max and n m_v = (F_max + T)/g0 are flat
    from the end of the rise to the release, while n = (F_max + T)/(m_v g0) rises (m_v
    burns) and n m_prop1 = (F_max + T)(1 - m_fixed/m_v)/g0 falls. ``track_peaks`` offers
    its candidates in time order and replaces the incumbent only above TRACK_PEAK_TIE_REL,
    so the max-F_int, max-n m_v and max-n m_prop1 cases sit at the end of the rise t_r
    (one case with the drive_ramp_end event) and the max-n case at the release, at each of
    six dm 0.2 kg apart (the vehicle carrying dm), with one history grid size; before the
    rule rounding placed the flat maxima anywhere from 0.500 to 0.577 s as dm changed by
    0.2 kg, and the grid had 512 to 514 entries."""
    thrust, _mdot, _t_ramp = _engine()
    f = _fly(SHORT, HOT)
    v0 = f.start.to_vehicle()
    ctx = sim.search_context(sim.planar_setup(f.start.run, v0), v0, f.start.run.end)
    layout = _layout()
    sizes = set()
    for dm in np.linspace(9_745.0, 9_746.0, 6):
        vehicle = sim.charge_structure(f.vehicle, float(dm), 0.0)
        trace = sim.flown_push_trace(ctx, vehicle)
        push = sim.linear_motor_push_load(trace, vehicle, f.assist, layout)
        flat = _case(push, "max F_int")
        assert flat.t_s == T_R_S and "drive_ramp_end" in _tags(flat), (dm, flat.label)
        assert {"max n m_v", "max n m_prop1"} <= set(_tags(flat))
        assert _close(flat.interface_force_N or 0.0, F_MAX_N)
        assert _close(flat.n_g * flat.vehicle_mass_kg, (F_MAX_N + thrust) / G0_MPS2)
        assert _case(push, "max n").t_s == trace.t_release_s
        assert push.history is not None
        sizes.add(push.history.t_s.size)
    assert len(sizes) == 1


MIXED_PUSHES: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {
    "plateau": ({**LM, "carriage_mass_t": CARRIAGE_T, "exhaust_impingement_fraction": 0.5}, HOT),
    "lit_on_track_power": (
        {**LM, "stroke_m": 60, "power_max_MW": w_to_mw(F_MAX_N * 15.0)},
        {"stage1": {"t_ign_s": 0.3, "reference": "push_start"}},
    ),
}
"""Two hot pushes whose maxima of n and of n m_prop1 lie at different instants: the force
plateau with a carriage (the hot test above), and a push lit 0.3 s after its start (the
ramp running on the track) whose corner at 15 m/s puts it in its power phase."""


@pytest.mark.parametrize("name", sorted(MIXED_PUSHES))
def test_a_hot_push_reads_mixed_station_drivers_at_its_samples(
    name: str, request: pytest.FixtureRequest
) -> None:
    """The reduction's limit, measured: a station driver n (m_prop1 + c) that mixes n and
    the stage-1 contents (a head above a barrel's bottom, c < 0; the aft and common domes
    at their crowns and the transfer tube at its bottom, c > 0; a barrel's compression
    with the column above it, c > 0) is read at the push's cases only (the sizing reads
    ``push.cases``; the release case is not among them). On two hot pushes, over c from
    -0.9 m_prop1 to 2 m_prop1 (30 values), the cases' maximum equals the dense maximum
    (``track_peaks`` of the driver) to rounding: on a
    force plateau with constant thrust n (m + c) is a ratio of two linear functions of t,
    so monotone between the samples, and the power-phase push measures the same (the gap
    recorded; asserted below 1e-9). A cold push has constant contents, so there every
    driver peaks with n."""
    lm, ignition = MIXED_PUSHES[name]
    f = _fly(lm, ignition)
    m_fixed = _m_fixed(f.vehicle)
    prop0 = f.vehicle.stages[0].propellant_mass_kg
    worst = 0.0
    for c in np.linspace(-0.9 * prop0, 2.0 * prop0, 30):

        def driver(t: float, y: np.ndarray, p: Any, c: float = float(c)) -> tuple[float]:
            felt, _f = metrics.track_felt_and_interface(t, y, p)
            return (felt * (float(p.layout.get(y, "m_kg")) - m_fixed + c),)

        (dense,) = metrics.track_peaks(f.trace.assist_phases(), driver, 1)
        sampled = max(
            case.n_g * (case.lox_stage1_kg + case.rp1_stage1_kg + c) for case in f.push.cases
        )
        worst = max(worst, 1.0 - sampled / dense.value)
    request.node.user_properties.append(("mixed_driver_gap_rel", worst))
    assert worst < 1e-9


# ------------------------------------------------------------------- the transform


def _transform(
    lm: dict[str, Any], ignition: dict[str, Any] | None = None, **settings: Any
) -> sim.StructureTransform:
    """The structural transform of the variant on the synthetic file and pad."""
    sfile = _sfile()
    case = StructureCaseConfig(**settings)
    st = resolve_structure_settings(case, sfile, case.sizing, "test")
    start = _start(lm, ignition)
    veh = ss.vehicle()
    layout = sfile.config.stack_layout()
    pad = structure.pad_load_set(sim.structure_pad_cases(ss.synthetic_pad_result(veh), veh, layout))
    return sim.build_structure_transform(
        st,
        start.to_vehicle(),
        start,
        "stage1",
        pad,
        ss.P_REF_KG,
        envelope_pad="synthetic pad",
        envelope_pad_key="synthetic",
    )


SHORT = {**LM, "stroke_m": 50}
"""The transform's push: the force law over 50 m (F_max 22 MN, t_r 0.5 s)."""
TAPERED = {**SHORT, "stop_taper_m": 10}
"""SHORT with a 10 m stop taper after its rise (its taper_start leaves a 4.7e-14 s ASSIST
sub-phase)."""
CORNERED = {**LM, "power_max_MW": w_to_mw(F_MAX_N * 5.0)}
"""LM with its power corner at 5 m/s, inside the 0.5 s rise (its power_limit leaves a
2.1e-11 s ASSIST sub-phase): ORACLE_CASES' corner_in_rise_vc5_3hz."""


@pytest.fixture(scope="module")
def lm_transform() -> sim.StructureTransform:
    """The structural transform of SHORT (cold) on the synthetic file and pad, central,
    flown, rise_time, aft_ring."""
    return _transform(SHORT)


@pytest.fixture(scope="module")
def lm_taper_transform() -> sim.StructureTransform:
    """The structural transform of TAPERED (cold), as ``lm_transform``."""
    return _transform(TAPERED)


def _bits(v: Vehicle) -> tuple[str, ...]:
    """The masses of a two-stage vehicle as float.hex strings (bit identity)."""
    out = []
    for stage in v.stages:
        out += [stage.dry_mass_kg.hex(), stage.propellant_mass_kg.hex()]
    return (*out, float(v.payload_mass_kg).hex(), float(v.fairing_mass_kg).hex())


def test_the_transform_flies_the_push_and_records_the_flown_values(
    lm_transform: sim.StructureTransform, request: pytest.FixtureRequest
) -> None:
    """A linear-motor structural case flies its push in every sizing: the record keys are
    STRUCTURE_RECORD_KEYS (no new key), structure_t_r_s the drive's 0.5 s (the file's
    0.8 s unused), structure_dlf min(2, 1 + T_ax/(pi t_r)) (a cold push: the flown
    history's bound equals the formula), structure_ramp_cost_rel null, structure_n_q_g
    the flown push's largest n on the vehicle carrying dm (F_max/(M g0) with M = the
    offloaded stack + dm), structure_n_peak_g and structure_F_peak_N the charged peaks
    (the rise formula's or the bound's; here the formula's); the release flag records the
    rise's plateau, its residual and the bound's, the payload-limit flag the rise
    formula's factor, the bound's envelopes and, last, the compression after the release
    it also checks (review rounds 2 and 3, P2-m2 and H-P3-01: here the release peak, the
    release unloading the stack); the fixed
    point from dm = 0 converges below 1e-6 kg inside the cap with its contraction
    measured and recorded in the cap flag."""
    tr = lm_transform
    assert tr.flies_push and tr.push_context is not None and tr.stage1_ignition_s is None
    x = 20_000.0
    at_x, at_0 = tr.sizing_at(x), tr.sizing_at(0.0)
    rec = sim.structure_record(tr, at_x, at_0)
    assert tuple(rec) == sim.STRUCTURE_RECORD_KEYS
    assert rec["structure_t_r_s"] == T_R_S and rec["structure_f_Hz"] == F_AX_HZ
    assert rec["structure_dlf"] == _dlf(T_R_S) and rec["structure_ramp_cost_rel"] is None
    flown = with_offload(tr.start_vehicle, "stage1", x)
    m = with_payload(flown, ss.P_REF_KG).liftoff_mass_kg() + at_x.total_kg
    req = at_x.increment.requirement
    n_q = F_MAX_N / (m * G0_MPS2)
    # the increment was sized on the iterate before the last (within the 1e-6 kg step)
    assert math.isclose(rec["structure_n_q_g"], n_q, rel_tol=1e-11)
    n_0 = G_REF / G0_MPS2
    assert _close(rec["structure_n_peak_g"], n_0 + _dlf(T_R_S) * (req.n_quasi_g - n_0))
    assert rec["structure_F_peak_N"] == req.f_peak_N
    flags = {fl["name"]: fl["values"] for fl in rec["structure_flags"]}
    release = flags[structure.FLAG_RELEASE_UNLOAD]
    assert release["release_rise_plateau_g"] == req.n_quasi_g
    assert _close(release["release_rise_residual_g"], (_dlf(T_R_S) - 1.0) * (req.n_quasi_g - n_0))
    assert release["release_bound_residual_g"] == req.release_bound_residual_g
    assert "release_taper_dlf" not in release
    payload = flags[structure.FLAG_PAYLOAD_LIMIT]
    assert payload["dlf_rise"] == _dlf(T_R_S) and payload["n_bound_g"] == req.n_bound_g
    assert payload["f_bound_N"] == req.f_bound_N
    key = structure.FLOWN_PUSH_RELEASE_COMPRESSION_KEY
    assert list(payload)[-1] == key
    assert payload[key] == req.release_compression_g == req.release_n_peak_g
    assert at_x.steps[-1] < sim.STRUCTURE_FIXED_POINT_TOL_KG <= at_x.steps[-2]
    assert not at_x.capped and at_x.iterations + 5 <= sim.STRUCTURE_FIXED_POINT_MAX_ITERATIONS
    assert at_x.contraction is not None and 0.0 < at_x.contraction < 0.05
    cap = flags[structure.FLAG_FIXED_POINT_CAP]
    assert cap["contraction"] == at_x.contraction
    request.node.user_properties.extend(
        [
            ("iterations", at_x.iterations),
            ("contraction", at_x.contraction),
            ("steps_kg", list(at_x.steps)),
            ("dm_kg_synthetic_not_a_finding", at_x.total_kg),
        ]
    )


S2_RELEASE_HEAD = (
    "release_n_before_g",
    "release_n_peak_g",
    "release_n_after_g",
    "release_swing_g",
    "release_swing_plateau_g",
    "release_p_amb_pa",
    "meco_n_g",
    "meco_swing_g",
)
"""The release flag's first values, S2's, before its per-tank pressures."""
S2_PAYLOAD_KEYS = (
    "n_peak_g",
    "release_swing_g",
    "release_swing_plateau_g",
    "limit_axial_max_g",
    "limit_axial_min_g",
)
"""The payload-limit flag's values, S2's."""


def test_constant_accel_transform_carries_no_flown_key() -> None:
    """A constant_accel structural case keeps the analytic push (no context, no flown
    push, no history): its release flag's values start with S2's head and carry none of a
    flown release's keys, its payload-limit flag carries S2's five values only, its
    requirement none of a flown push's numbers, and its runs no flown push's assumption
    line. (That its values are unchanged is the frozen sets' and the headline pins'
    test.)"""
    exp = ss.load_yaml(EXPERIMENT)
    tr = _transform_constant_accel(exp["variants"]["silo_cold"])
    assert not tr.flies_push and tr.push_context is None
    s = tr.sizing_at(ss.HEADLINE_OFFLOAD_KG)
    flags = {f.name: [k for k, _v in f.values] for f in s.increment.flags}
    release = flags[structure.FLAG_RELEASE_UNLOAD]
    assert tuple(release[: len(S2_RELEASE_HEAD)]) == S2_RELEASE_HEAD
    assert not set(release) & set(structure.FLOWN_RELEASE_FLAG_KEYS)
    assert tuple(flags[structure.FLAG_PAYLOAD_LIMIT]) == S2_PAYLOAD_KEYS
    req = s.increment.requirement
    flown_fields = (
        "release_rise_plateau_g",
        "release_bound_residual_g",
        "dlf_rise",
        "n_bound_g",
        "f_bound_N",
        "release_compression_g",
    )
    assert all(getattr(req, name) is None for name in flown_fields)
    assert sim.structure_push_assumptions(tr) == []


@pytest.mark.parametrize("name", ["release_past_corner_3hz", "release_in_tension_3hz"])
def test_the_payload_limit_flag_checks_the_compression_after_a_flown_release(
    name: str, lm_transform: sim.StructureTransform
) -> None:
    """Review rounds 2 and 3, P2-m2 and H-P3-01: the largest load after a flown release,
    release_compression_g = n_after + |n_before - n_after| + A (A = n_peak,rel - n_before),
    can exceed n_peak: through the phase-free release bound (a release just past a 10 m/s
    corner at 3 Hz, which unloads: the compression is n_peak,rel, about 4.08 against 3.88
    g0) and through a release in tension (TENSION at 3 Hz: about 1.61 against n_peak and
    n_peak,rel of 1.29 g0). With the payload's upper axial limit between n_peak and the
    compression (and the lower one out of reach) the payload-limit flag fires, the
    compression recorded last (FLOWN_PUSH_RELEASE_COMPRESSION_KEY) and named in the run
    flag's line; with the limit above it the flag does not fire."""
    lm, ignition, f_hz = ORACLE_CASES[name]
    push = _fly(lm, ignition).push
    coeffs = _coeffs(f_hz)
    req = structure.push_requirement(push, coeffs, "rise_time")
    top = req.release_compression_g
    assert top is not None and req.n_peak_g + 0.1 < top
    if name == "release_in_tension_3hz":
        assert req.release_n_peak_g + 0.1 < top  # the release peak alone would not fire
        below = max(req.n_peak_g, req.release_n_peak_g)
    else:
        assert top == req.release_n_peak_g
        below = req.n_peak_g
    tr = lm_transform
    for limit, fired in ((0.5 * (below + top), True), (5.0, False)):
        c = dataclasses.replace(
            coeffs, payload_limit_axial_max_g=limit, payload_limit_axial_min_g=-20.0
        )
        inc = structure.size_increment(tr.geometry, c, tr.envelope, push)
        (flag,) = [f for f in inc.flags if f.name == structure.FLAG_PAYLOAD_LIMIT]
        assert flag.fired is fired and below < limit
        assert flag.values[-1] == (structure.FLOWN_PUSH_RELEASE_COMPRESSION_KEY, top)
        line = sim._structure_flag_line(sim._flag_record(flag))
        assert f"the largest load after the flown release {top:.3g} g0" in line


def _transform_constant_accel(variant: dict[str, Any]) -> sim.StructureTransform:
    """The structural transform of silo_cold (constant_accel) on the synthetic file and
    pad."""
    sfile = _sfile()
    case = StructureCaseConfig()
    st = resolve_structure_settings(case, sfile, case.sizing, "test")
    start = _resolved({"silo_cold": variant}).variants["silo_cold"]
    veh = ss.vehicle()
    layout = sfile.config.stack_layout()
    pad = structure.pad_load_set(sim.structure_pad_cases(ss.synthetic_pad_result(veh), veh, layout))
    return sim.build_structure_transform(
        st, start.to_vehicle(), start, "stage1", pad, ss.P_REF_KG,
        envelope_pad="synthetic pad", envelope_pad_key="synthetic",
    )  # fmt: skip


def test_vehicle_at_is_bit_identical_across_call_orders_on_a_flown_push(
    lm_transform: sim.StructureTransform,
) -> None:
    """vehicle_at(x) with the flown-push transform gives the same bits forwards and in
    reverse (each offload computed twice, in either order) and on a transform built again
    (each call flies its pushes afresh from dm = 0), equal to ``charge_structure`` with the
    transform's own sizing. Seven sizings in all (two forwards, two in reverse, the
    rebuilt transform's own at x = 0 and its one at 20 t, one for charge_structure), about
    1 s on an idle machine and under 3 s throttled (review rounds 1 and 2, C-P1-09,
    C-P2-03 and P2-m4)."""
    start = lm_transform.start_vehicle
    xs = [20_000.0, 0.0]

    def problem(tr: Any) -> offload.OffloadProblem:
        def factory(vehicle: Any) -> Any:
            raise AssertionError("vehicle_at calls no factory")

        return offload.OffloadProblem(factory, start, "stage1", ss.P_REF_KG, None, tr)  # type: ignore[arg-type]

    p = problem(lm_transform)
    forward = [_bits(p.vehicle_at(x)) for x in xs]
    backward = [_bits(p.vehicle_at(x)) for x in reversed(xs)][::-1]
    assert forward == backward and forward[0] != forward[1]
    rebuilt = problem(_transform(SHORT))
    assert _bits(rebuilt.vehicle_at(xs[0])) == forward[0]
    s = lm_transform.sizing_at(xs[0])
    expected = sim.charge_structure(
        with_offload(start, "stage1", xs[0]), s.dm_stage1_kg, s.dm_stage2_kg
    )
    assert forward[0] == _bits(expected) and s.dm_stage1_kg > 0.0


SLOPE_PUSHES: dict[str, tuple[str, tuple[float, ...]]] = {
    "plain": ("lm_transform", (0.0, 20_000.0, 40_000.0)),
    "taper_10m": ("lm_taper_transform", (0.0,)),
    "corner_in_rise": ("", (20_000.0,)),
    "hot_no_carriage": ("lm_hot_transform", (0.0, 20_000.0)),
}
"""The transforms whose dm(x) is checked, by name: (the module fixture that holds it, ""
for CORNERED's, built in the test, which flies its sizing at x = 0; the offloads [kg],
fewer on the cases added in review rounds 2 and 3 to keep each near 2 to 3 s)."""


@pytest.fixture(scope="module")
def lm_hot_transform() -> sim.StructureTransform:
    """The structural transform of SHORT lit 2 s before its push (HOT), no carriage and
    f_imp 0, as ``lm_transform`` (review round 3, P3-M1)."""
    return _transform(SHORT, HOT)


@pytest.mark.parametrize("name", list(SLOPE_PUSHES))
def test_dm_slope_of_a_flown_push_is_bounded_and_smooth(
    name: str, request: pytest.FixtureRequest
) -> None:
    """dm(x) of the flown force-law push (SHORT; TAPERED and CORNERED, whose
    taper_start and power_limit leave ASSIST sub-phases of 4.7e-14 and 2.1e-11 s: review
    round 2, P2-M1, where rounding read as slopes left 13 of 16 sizings of TAPERED at the
    cap of 25 and dm jumping by tonnes per kilogram; SHORT lit before its push with no
    carriage, whose flat F_int and n m_v review round 3 found placed by rounding, P3-M1,
    every sizing at the cap of 25 and the 10 g slopes -29 and -44 kg/kg): at each offload
    the fixed point converges uncapped with five sizings to spare, and the differences at
    1 kg and 10 g agree within 1e-5 kg/kg and exceed -1/(2 E) (design 4.4's monotonicity
    bound). Its sign is recorded, not asserted: design 4.4 reports its probe giving dm' > 0
    under a force-controlled motor, but on the cold synthetic pushes the stage-1 tanks'
    heads n m_prop = F m_prop/(M g0) fall as the offload empties them while the cold
    interface force stays F_max, and dm' comes out slightly negative (about -4e-4 kg/kg on
    SHORT and TAPERED, -4e-3 on CORNERED); on the hot push it is positive (about +0.009
    and +0.010 kg/kg at 0 and 20 t; docs/physics.md, "The flown push of a linear motor")."""
    fixture, offloads = SLOPE_PUSHES[name]
    tr = request.getfixturevalue(fixture) if fixture else _transform(CORNERED)
    cap = sim.STRUCTURE_FIXED_POINT_MAX_ITERATIONS
    slopes = []
    for x in offloads:
        sizings = [tr.sizing_at(x + dx) for dx in (0.0, 1.0, 0.01)]
        for s in sizings:
            assert not s.capped and s.iterations + 5 <= cap, (x, s.iterations)
        dm, dm_1kg, dm_10g = (s.total_kg for s in sizings)
        d_1kg, d_10g = dm_1kg - dm, (dm_10g - dm) / 0.01
        assert d_1kg > SLOPE_FLOOR and d_10g > SLOPE_FLOOR, x
        assert d_1kg == pytest.approx(d_10g, abs=SMOOTH_TOL), x
        slopes.append(d_1kg)
    request.node.user_properties.append(("dm_slope_kg_per_kg", slopes))


def test_a_full_load_push_that_cannot_release_is_refused_at_build() -> None:
    """Review round 1, m1: a drive whose F_max of 3 MN cannot lift the stack stalls at
    push start, so the transform's sizing at x = 0 (the full-load stack at P_ref, where
    the solve and the record start) cannot fly: ``build_structure_transform`` refuses it
    with a ValueError naming the planner's status and the iterate rule (the first iterate
    that fails ends the build; review round 4, H-P4-03), before any solve."""
    with pytest.raises(
        ValueError,
        match=(
            r"fails to release \(drive_stall\) at one of its fixed point's iterates from "
            r"dm = 0 \(the first that fails ends the build\)"
        ),
    ):
        _transform({**SHORT, "force_max_kN": 3000})


def test_an_offload_whose_push_cannot_release_is_infeasible() -> None:
    """A hot acceleration-law push on a 250 t carriage flies at x = 0 (its weight above
    the delivered thrust at push start), but an offload of 60 t leaves the thrust above
    the stack's weight, so the command's force at push start is negative (a drive_limit
    stop): the transform's sizing there raises PreludeFailure, one of
    ``search.INFEASIBLE``, which an offload search reads as an infeasible evaluation."""
    lm = {
        **SHORT,
        "control": "acceleration",
        "accel_command_g": ACCEL_CMD_G,
        "force_max_kN": 40000,
        "carriage_mass_t": 250.0,
    }
    tr = _transform(lm, HOT)
    with pytest.raises(PreludeFailure) as info:
        tr.sizing_at(60_000.0)
    assert isinstance(info.value, INFEASIBLE) and info.value.args[0] == "drive_limit"


def test_the_flown_push_assumption_line(
    lm_transform: sim.StructureTransform, lm_taper_transform: sim.StructureTransform
) -> None:
    """``structure_push_assumptions``, worded by the case's mode and sizing basis: under
    rise_time the larger of the rise formula with the drive's own t_r and the flown
    history's bound, at each offload x carrying each fixed-point iterate (sizing flown);
    under step every change as a step, the peak the larger of n_rest + 2 (n_q - n_rest)
    and the flown load plus its total variation (review round 2, P2-m3, C-P2-02, H-P2-03),
    t_r recorded, not used; under quasi_static no residual; on the full-load vehicle
    whatever x the solve tries, at P_ref and a payload case's dm_1 at P_1* (sizing
    full_load, every structure payload case; review round 2, H-P2-05); the taper's own
    factor only with a taper; the reduction's limit."""
    (line,) = sim.structure_push_assumptions(lm_transform)
    assert line.startswith("structure: the push is the linear motor's as flown")
    assert "the drive's own force rise time t_r = 0.5 s (structure_t_r_s" in line
    assert "phase-free single-mode bound of the flown history" in line
    assert "on the vehicle at each offload x at P_ref, carrying each fixed-point iterate" in line
    assert "full-load" not in line
    assert "taper" not in line and "read at those samples only" in line
    for mode, words in (
        ("step", "the dynamic mode step charges every change of the flown load as a step"),
        ("quasi_static", "the dynamic mode quasi_static charges the flown quasi-static loads"),
    ):
        other = dataclasses.replace(
            lm_transform, settings=dataclasses.replace(lm_transform.settings, dynamic=mode)
        )
        (text,) = sim.structure_push_assumptions(other)
        assert words in text and "recorded, not used" in text
        assert "phase-free" not in text
        if mode == "step":
            assert "the flown load plus its total variation from rest, n + V" in text
    full = dataclasses.replace(
        lm_transform, settings=dataclasses.replace(lm_transform.settings, sizing="full_load")
    )
    (line_full,) = sim.structure_push_assumptions(full)
    assert "on the full-load vehicle (x = 0) whatever x the solve tries, at P_ref" in line_full
    assert "at P_1* for the dm_1 its run carries" in line_full
    assert "each offload" not in line_full and "once per sizing" not in line_full
    (line_taper,) = sim.structure_push_assumptions(lm_taper_transform)
    assert (
        "(plus, after a stop taper, the taper's own residual: its ramp factor over the time "
        "from its start on the drop it flew)" in line_taper
    )


# ------------------------------------------------- the sealed shaft (SP7 step S5)


SEALED = {"shaft": "sealed", "shaft_bore_m": 3.7, "shaft_gap_m": 5.0, "shaft_gamma": 1.4}
"""A sealed shaft (sources section 10: the 3.7 m bore, a 5 m gap, gamma 1.4)."""


def _column_N(s_m: float, p0_pa: float) -> float:
    """The trapped column's force (p_0 - p_0 (h_0/(h_0 + s))^gamma) pi d^2/4 [N] of SEALED
    at s_m [m], p_0 = p0_pa [Pa] (the test's own formula)."""
    h0, gamma, bore = SEALED["shaft_gap_m"], SEALED["shaft_gamma"], SEALED["shaft_bore_m"]
    return (p0_pa - p0_pa * (h0 / (h0 + s_m)) ** gamma) * math.pi * bore**2 / 4.0


def test_a_sealed_push_lowers_the_flown_interface_peak_by_the_column_share() -> None:
    """SP7 step S5 (the brief's note from S4b): a cold force-law push (LM, 30 m, F_max 22
    MN) on a 20 t carriage, sealed and vented, flown alone and reduced by
    ``sim.linear_motor_push_load`` (no sealed branch on that path). Both pushes' max-F_int
    case is the end of the rise t_r (after it the vented F_int is flat at (m_v/M) F_max and
    the sealed one falls as the column's force grows); there the sealed F_int is the
    vented peak less (m_v/M) F_p(s*), with s* the sealed push's position at t_r and F_p
    from the closed form at p_0 = p_atm(-30 m) (the track start), at 1e-9, and equals the
    vented drive evaluated at the sealed state less the same share; the max-n case is
    lower by F_p(s*)/(M g0) the same way (cold: n = (F - F_p)/(M g0))."""
    from launchsim.atmosphere import ambient_scalar
    from launchsim.phases.engine import ZERO_SPAN_S

    lm = {**LM, "carriage_mass_t": CARRIAGE_T}
    vented, sealed = _fly(lm), _fly({**lm, **SEALED})
    assert sealed.assist.shaft is not None and vented.assist.shaft is None
    p0 = ambient_scalar(-30.0)[0]
    assert sealed.assist.shaft.p0_pa == p0
    m_v = vented.vehicle.liftoff_mass_kg()
    total = m_v + t_to_kg(CARRIAGE_T)
    share = m_v / total
    peak_v, peak_s = _case(vented.push, "max F_int"), _case(sealed.push, "max F_int")
    assert peak_v.t_s == peak_s.t_s == T_R_S
    assert _close(peak_v.interface_force_N or 0.0, share * F_MAX_N)
    (res,) = [r for r in sealed.trace.assist_phases() if abs(r.t_end - T_R_S) <= ZERO_SPAN_S]
    params = res.spec.params
    y = np.asarray(res.y_end, dtype=float)
    s_star = float(params.layout.get(y, "s_m"))
    assert 0.5 < s_star < 2.0
    column = _column_N(s_star, p0)
    expected = (peak_v.interface_force_N or 0.0) - share * column
    assert _close(peak_s.interface_force_N or 0.0, expected)
    open_drive = dataclasses.replace(params.assist, shaft=None)
    at_state = open_drive.state_rate(
        T_R_S,
        s_star,
        float(params.layout.get(y, "sdot_mps")),
        np.zeros(0),
        float(params.layout.get(y, "m_kg")),
        params.carriage_mass_kg,
        params.thrust_N(T_R_S),
        params.g_eff_mps2,
        params.track,
    )
    assert _close(peak_s.interface_force_N or 0.0, at_state.interface_force_N - share * column)
    n_v, n_s = _case(vented.push, "max n"), _case(sealed.push, "max n")
    assert n_v.t_s == n_s.t_s == T_R_S
    assert _close(n_s.n_g, n_v.n_g - column / (total * G0_MPS2))


def test_a_sealed_shaft_does_not_raise_the_structural_mass(
    lm_transform: sim.StructureTransform, request: pytest.FixtureRequest
) -> None:
    """SP7 step S5: the structural transform of SHORT in a sealed shaft on the synthetic
    file (the flown push carries the column's lower interface force and felt load into
    the sizing through the S4b path, no new branch): its record's keys are
    STRUCTURE_RECORD_KEYS (no new key), and at x = 20 t its quasi-static n_q, its charged
    n_peak and F_peak are below the vented push's (``lm_transform``) and its dm is not
    larger (a smaller interface force and felt load need no more structure)."""
    sealed = _transform({**SHORT, **SEALED})
    x = 20_000.0
    at_s, at_v = sealed.sizing_at(x), lm_transform.sizing_at(x)
    rec = sim.structure_record(sealed, at_s, sealed.sizing_at(0.0))
    assert tuple(rec) == sim.STRUCTURE_RECORD_KEYS
    req_s, req_v = at_s.increment.requirement, at_v.increment.requirement
    assert req_s.n_quasi_g < req_v.n_quasi_g
    assert req_s.n_peak_g < req_v.n_peak_g and req_s.f_peak_N < req_v.f_peak_N
    assert at_s.total_kg <= at_v.total_kg
    request.node.user_properties.extend(
        [
            ("dm_sealed_kg_synthetic_not_a_finding", at_s.total_kg),
            ("dm_vented_kg_synthetic_not_a_finding", at_v.total_kg),
        ]
    )


# --------------------------------------------------------------------- slow: the solve


SOLVED = {**LM, "stroke_m": 100}
"""The solved case's push: the force law (F_max 22 MN, t_r 0.5 s) over 100 m, about 3.9 to
4.0 g0 felt (4.5 to 4.6 with the DLF) and 76 m/s at the mouth. SHORT's 50 m push carrying
the synthetic file's structure (about 5.9 t) ends no_offload at P_ref (measured), which
would leave no x* to converge."""


@pytest.fixture(scope="module")
def lm_solves() -> SimpleNamespace:
    """The synthetic linear-motor structural case (SOLVED on the synthetic file, central,
    flown, rise_time, aft_ring) solved at SP1's P_ref along stage 1 with the shipped budget
    (verified), and again with the budget tightened 10x by the experiment's
    checks.convergence (``SearchContext.tightened``) and the same tightened context passed
    to the transform as its push_context (nothing tightens it automatically; not
    verified). A test input, not a finding."""
    start = _start(SOLVED)
    v0 = start.to_vehicle()
    ctx = sim.search_context(sim.planar_setup(start.run, v0), v0, start.run.end)
    planar = start.run.planar
    assert planar is not None
    conv = planar.checks.convergence
    tr = _transform(SOLVED)
    t0 = time.perf_counter()
    shipped = solve_offload(planar_problem_factory(ctx), v0, "stage1", ss.P_REF_KG, transform=tr)
    t1 = time.perf_counter()
    tight_ctx = ctx.tightened(conv)
    tight_tr = dataclasses.replace(tr, push_context=tight_ctx)
    tight = solve_offload(
        planar_problem_factory(tight_ctx),
        v0,
        "stage1",
        ss.P_REF_KG,
        verify=False,
        transform=tight_tr,
    )
    t2 = time.perf_counter()
    return SimpleNamespace(
        tr=tr, shipped=shipped, tight=tight, conv=conv, seconds=(t1 - t0, t2 - t1)
    )


@pytest.mark.slow
def test_a_linear_motor_structural_case_solves(
    lm_solves: SimpleNamespace, request: pytest.FixtureRequest
) -> None:
    """The coupled solve of the synthetic linear-motor structural case: status ok, no
    offload_nonmonotone in any logged search, the verification passed, the offloaded
    vehicle carrying the transform's dm at x* (charged once), the fixed point at x*
    inside its cap; dm'(x*) (1 kg and 10 g differences) and the contraction recorded,
    dm'(x*) above -1/(2 E)."""
    res, tr = lm_solves.shipped, lm_solves.tr
    assert res.status == OK_STATUS, (res.failure_kind, res.failure_message)
    assert not [f for f in res.flags if NONMONOTONE_FLAG in f]
    assert res.verification is not None and res.verification.passed
    x = res.offload_kg
    s = tr.sizing_at(x)
    assert not s.capped and s.steps[-1] < sim.STRUCTURE_FIXED_POINT_TOL_KG
    expected = sim.charge_structure(
        with_offload(tr.start_vehicle, "stage1", x), s.dm_stage1_kg, s.dm_stage2_kg
    )
    assert res.offloaded_vehicle is not None and _bits(res.offloaded_vehicle) == _bits(expected)
    d_1kg = tr.sizing_at(x + 1.0).total_kg - s.total_kg
    d_10g = (tr.sizing_at(x + 0.01).total_kg - s.total_kg) / 0.01
    assert d_1kg > SLOPE_FLOOR and d_1kg == pytest.approx(d_10g, abs=SMOOTH_TOL)
    request.node.user_properties.extend(
        [
            ("seconds", lm_solves.seconds),
            ("x_star_kg_synthetic_not_a_finding", x),
            ("dm_at_x_star_kg", s.total_kg),
            ("dm_slope_at_x_star_kg_per_kg", d_1kg),
            ("contraction_at_x_star", s.contraction),
            ("iterations_at_x_star", s.iterations),
            ("n_evaluations", res.n_evaluations),
        ]
    )


@pytest.mark.slow
def test_a_linear_motor_structural_x_star_converges(
    lm_solves: SimpleNamespace, request: pytest.FixtureRequest
) -> None:
    """Exit criterion 6 for the linear motor: with every search tolerance divided by 10 and
    the step caps halved (``SearchContext.tightened`` by checks.convergence, the same
    tightened context passed as the transform's push_context), the synthetic case's x*
    moves by less than rel_tol (1e-3) x x*."""
    shipped, tight = lm_solves.shipped, lm_solves.tight
    assert shipped.status == tight.status == OK_STATUS
    x, x_t = shipped.offload_kg, tight.offload_kg
    request.node.user_properties.append(("x_star_rel_change", (x_t - x) / x))
    assert abs(x_t - x) <= lm_solves.conv.rel_tol * x
