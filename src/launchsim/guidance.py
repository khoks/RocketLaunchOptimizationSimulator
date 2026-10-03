"""Planar steering laws, the stage-1 guidance specification and the gamma* inner solve
(docs/physics.md, "Stage-1 guidance and events (planar)" and "gamma* inner solve").

Steering laws implement ``dynamics.SteeringLaw``: ``direction(t, y, kin)`` returns the
unit thrust direction (e_r, e_theta) in the local frame (radial up, horizontal
downrange), and ``along_vrel`` is True only for the law that thrusts along v_rel. The
stage-1 laws are ``Radial`` (the vertical rise: inertially radial, not along v_rel,
because v_rel = 0 on the pad and leans west with rotation), ``FixedTilt`` (the
hold-to-alignment kick at the angle delta from local vertical) and ``AlongVrel`` (the
gravity turn). Stage 2 flies ``LinearTangent`` (tan p = a - b tau in the local
horizontal frame, tau from stage-2 ignition; ``LinearTangentEps`` adds a test-only
eps tau^2 term for the optimality test).

``GuidanceSpec`` is the shared stage-1 parametrisation of a run (trigger speed, kick time
limit, kick deadline), built from ``config.GuidanceConfig`` at the boundary.
``solve_delta_for_gamma`` finds the kick angle delta whose stage-1 flight reaches a target
Earth-relative flight-path angle gamma* at MECO, with the false-root guard of amendment
7. ``solve_ltg`` finds the stage-2 pair (a, b) whose energy cutoff lands on the target
radius with zero radial velocity: a damped 2x2 Newton with forward-difference
Jacobians over a guess ladder (``ltg_guess_ladder``: warm, physics, steep, shallow),
accepting only a direct root (docs/physics.md, "LTG shooting"). Every guidance failure
is a typed ``GuidanceFailure`` (never a warning), so a search can turn it into a
penalty.

Pure: no I/O, no globals, no printing. SI units and radians throughout.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

import numpy as np
from scipy.optimize import brentq

from launchsim.dynamics import PlanarKinematics

if TYPE_CHECKING:
    from launchsim.config import GuidanceConfig, LtgConfig, SearchConfig

GUIDANCE_FAILURE_KINDS = (
    "impact",
    "no_cutoff",
    "mass_floor",
    "kick_timeout",
    "no_kick",
    "nonconverged",
    "not_direct_root",
    "gamma_unattainable",
    "false_root",
    "lofted_overshoot",
    "no_ignition",
)
"""Kinds of ``GuidanceFailure``: the plan's seven (impact before the end of the flight
segment, no stage-2 cutoff, the search mass floor, the kick time limit, no kick by the
deadline, LTG non-convergence, an indirect LTG root), the two outcomes of the gamma*
inner solve (no sign change of gamma_MECO - gamma* inside the delta bracket, and a root
that brentq returned across a discontinuity), the stage-2 pre-screen
``lofted_overshoot`` (the orbital energy already at or above the target's at stage-2
ignition, so the energy cutoff cannot mark an insertion) and ``no_ignition`` (SP1 step
4: a first stage stated by ``height_method: event`` whose coast after release reaches
its apex below the ignition height, so it never lights)."""
IMPACT_GAMMA_RAD = -0.5 * math.pi
"""The flight-path angle [rad] the gamma* inner solve assigns to a flight that hits
the ground before its end (straight down): before MECO, or, for a flight through the
staging coast (``PlanarPlanner.from_kick``'s default), before stage-2 ignition, so a
MECO followed by a fall into the ground within the coast counts too. Below every real
gamma_MECO, so the map stays non-increasing at the large-delta end of the bracket."""
TIMEOUT_GAMMA_RAD = math.pi
"""The flight-path angle [rad] the gamma* inner solve assigns to a kick that times out:
pi, the top of gamma_rel's range (-pi, pi], so the sentinel lies above every real
gamma_MECO. Only a tiny kick times out, and it does so because it never aligns: with
rotation the Coriolis deflection 2 omega_p w of the rising velocity outgrows the
tilt's (T/m) sin(delta), so beta_rel peaks below delta and turns back west (the
Coriolis stall). On the gate pad at v_k 50 m/s every kick below 0.11662 deg stalls
(held to MECO it ends at gamma_rel 90.17 to 90.20 deg after 139 s); one just above
aligns after at most 19.1 s and reaches MECO at 90.96 deg, the largest real value.
So with a kick_max_s between those two times (60 s shipped) the timeouts are exactly
the stalled kicks, and gamma_MECO(delta) with this sentinel is non-increasing over the
whole bracket; a +pi/2 sentinel would sit below the aligned flights next to it."""
SENTINEL_GAMMA_RAD = {"impact": IMPACT_GAMMA_RAD, "kick_timeout": TIMEOUT_GAMMA_RAD}
"""GuidanceFailure kinds the gamma* inner solve maps to a sentinel gamma_MECO [rad]
(every other kind propagates)."""
KICK_MODES = ("hold_to_alignment",)
"""Kick laws ``GuidanceSpec`` accepts (``config.KickConfig.mode``)."""
BRENTQ_MAXITER = 100
"""Iteration cap of the delta brentq (scipy's default; a solver setting)."""
LTG_B_SCALE_S = 100.0
"""Scale [s] of the LTG unknown x = (a, LTG_B_SCALE_S b): with b ~ 1e-3 1/s both
entries of x are of order 0.1 to 1, so one forward-difference step (config
``ltg.fd_step_*``, in x units) suits both (plan section 6; a solver setting)."""


class GuidanceFailure(RuntimeError):
    """A guidance outcome that makes the flight unusable for its purpose, typed by
    ``kind`` (one of GUIDANCE_FAILURE_KINDS) with a human-readable ``message``.

    Every constructor argument is passed to RuntimeError (``args == (kind, message)``),
    so the exception pickles and re-raises intact. A search turns it into a penalty; a
    recorded run reports it.
    """

    def __init__(self, kind: str, message: str = "") -> None:
        if kind not in GUIDANCE_FAILURE_KINDS:
            raise ValueError(f"unknown guidance failure kind {kind!r}")
        super().__init__(kind, message)
        self.kind = kind
        self.message = message

    def __str__(self) -> str:
        return f"{self.kind}: {self.message}" if self.message else self.kind


# ----------------------------------------------------------------------- steering laws


@dataclass(frozen=True)
class Radial:
    """Thrust along local vertical r_hat: (e_r, e_theta) = (1, 0), pitch pi/2.

    The vertical rise. Inertially radial (the local frame is the same inertially and
    Earth-fixed), not along v_rel: on the pad v_rel = 0, and with rotation the air
    drifts past a radially rising vehicle (u = omega_p (R_E^2/r - r) < 0 without drag),
    so thrusting along v_rel would lean the rise west."""

    @property
    def along_vrel(self) -> bool:
        """False: the rise thrusts radially, not along v_rel."""
        return False

    def direction(self, t: float, y: np.ndarray, kin: PlanarKinematics) -> tuple[float, float]:
        """(1, 0) at any time t [s] and state y (local frame, radial up)."""
        return 1.0, 0.0


@dataclass(frozen=True)
class FixedTilt:
    """Thrust tilted downrange by delta_rad [rad] from local vertical:
    (e_r, e_theta) = (cos delta, sin delta), pitch pi/2 - delta above local horizontal.

    The hold-to-alignment kick: held until the Earth-relative velocity has turned to
    the same angle from vertical (``phases.engine.ev_kick_aligned``), where the gravity
    turn takes over with a continuous thrust direction. delta must be finite."""

    delta_rad: float
    _e: tuple[float, float] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not math.isfinite(self.delta_rad):
            raise ValueError(f"delta_rad must be finite, got {self.delta_rad!r}")
        object.__setattr__(self, "_e", (math.cos(self.delta_rad), math.sin(self.delta_rad)))

    @property
    def along_vrel(self) -> bool:
        """False: the kick holds a fixed attitude in the local frame."""
        return False

    def direction(self, t: float, y: np.ndarray, kin: PlanarKinematics) -> tuple[float, float]:
        """(cos delta, sin delta) at any time t [s] and state y (local frame)."""
        return self._e


@dataclass(frozen=True)
class AlongVrel:
    """Thrust along the Earth-relative velocity: (e_r, e_theta) = (sin gamma_rel,
    cos gamma_rel), the gravity turn (zero angle of attack in the model's no-lift
    aerodynamics). Below V_REL_EPS_MPS the kinematic fallback makes it radial
    (sin gamma_rel = 1). ``along_vrel`` is True, so the RHS books exactly zero
    steering loss."""

    @property
    def along_vrel(self) -> bool:
        """True: the thrust is along v_rel by construction."""
        return True

    def direction(self, t: float, y: np.ndarray, kin: PlanarKinematics) -> tuple[float, float]:
        """(kin.sin_g, kin.cos_g): the unit v_rel in the local frame (r_hat at V = 0)."""
        return kin.sin_g, kin.cos_g


@dataclass(frozen=True)
class LinearTangent:
    """Stage-2 linear-tangent steering in the local horizontal frame:
    tan p = s = a - b_per_s tau with tau = t - t_ign2_s, so (e_r, e_theta) = (s, 1) /
    sqrt(1 + s^2) and the pitch p = atan(s) above local horizontal (the frame turns with
    the radius vector; CLAUDE.md's form). a is dimensionless (tan p at stage-2 ignition),
    b_per_s [1/s] the rate at which tan p falls, t_ign2_s [s] stage 2's absolute
    ignition time. All finite. Frame: local (radial up, horizontal downrange)."""

    a: float
    b_per_s: float
    t_ign2_s: float

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) for v in (self.a, self.b_per_s, self.t_ign2_s)):
            raise ValueError("LinearTangent needs finite a, b_per_s and t_ign2_s")

    @property
    def along_vrel(self) -> bool:
        """False: the law fixes the pitch, not the velocity direction."""
        return False

    def tan_pitch(self, t: float) -> float:
        """tan p = a - b tau at absolute time t [s] (dimensionless)."""
        return self.a - self.b_per_s * (t - self.t_ign2_s)

    def direction(self, t: float, y: np.ndarray, kin: PlanarKinematics) -> tuple[float, float]:
        """(s, 1)/sqrt(1 + s^2) with s = tan p at time t [s]; the state is not read."""
        s = self.a - self.b_per_s * (t - self.t_ign2_s)
        inv = 1.0 / math.sqrt(1.0 + s * s)
        return s * inv, inv


@dataclass(frozen=True)
class LinearTangentEps:
    """Test-only perturbed linear tangent: tan p = a - b tau + eps tau^2 with
    tau = t - t0_s (a dimensionless, b_per_s [1/s], t0_s [s], eps_per_s2 [1/s^2]). For
    the LTG optimality test: a linear tangent is the optimal steering of the flat-Earth,
    uniform-gravity, fixed-time problem, so d v_x,f / d eps = 0 at eps = 0 when a and b
    are re-solved for the same terminal altitude and vertical speed. Never built from a
    config. Frame: local (radial up, horizontal downrange)."""

    a: float
    b_per_s: float
    t0_s: float
    eps_per_s2: float

    @property
    def along_vrel(self) -> bool:
        """False: the law fixes the pitch."""
        return False

    def direction(self, t: float, y: np.ndarray, kin: PlanarKinematics) -> tuple[float, float]:
        """(s, 1)/sqrt(1 + s^2) with s = a - b tau + eps tau^2 at time t [s]."""
        tau = t - self.t0_s
        s = self.a - self.b_per_s * tau + self.eps_per_s2 * tau * tau
        inv = 1.0 / math.sqrt(1.0 + s * s)
        return s * inv, inv


def pitch_rad(e_r: float, e_theta: float) -> float:
    """Pitch [rad] of a thrust direction (e_r, e_theta) above local horizontal:
    atan2(e_r, e_theta) (pi/2 for radial thrust)."""
    return math.atan2(e_r, e_theta)


# ------------------------------------------------------------------ guidance spec


@dataclass(frozen=True)
class GuidanceSpec:
    """Stage-1 guidance of a planar run (the shared parametrisation).

    v_kick_mps: the kick trigger speed [m/s], |v_rel| with v_r > 0 (math.inf: never
    kick; the vertical-only guidance of the planner-level reduction tests); kick_max_s:
    the time limit [s] of the hold-to-alignment kick (kick_timeout beyond it);
    kick_deadline_s: the time [s] after stage-1 ignition by which the kick must have
    started (no_kick otherwise; math.inf for none, required with v_kick = inf). A
    finite v_kick needs a finite deadline and time limit, so a guided flight cannot
    run into the integrator's t_max guard.
    """

    v_kick_mps: float
    kick_max_s: float
    kick_deadline_s: float

    def __post_init__(self) -> None:
        if not self.v_kick_mps > 0.0 or math.isnan(self.v_kick_mps):
            raise ValueError(f"v_kick_mps must be > 0, got {self.v_kick_mps!r}")
        if not self.kick_max_s > 0.0 or not self.kick_deadline_s > 0.0:
            raise ValueError("kick_max_s and kick_deadline_s must be > 0")
        if math.isfinite(self.v_kick_mps) and not (
            math.isfinite(self.kick_max_s) and math.isfinite(self.kick_deadline_s)
        ):
            raise ValueError("a kicking guidance needs a finite kick_max_s and kick_deadline_s")
        if not math.isfinite(self.v_kick_mps) and math.isfinite(self.kick_deadline_s):
            raise ValueError("a guidance that never kicks has no kick deadline (use inf)")

    @property
    def kicks(self) -> bool:
        """True unless the guidance is vertical-only (v_kick_mps = inf)."""
        return math.isfinite(self.v_kick_mps)

    @classmethod
    def from_config(cls, cfg: GuidanceConfig) -> GuidanceSpec:
        """The spec of a validated ``config.GuidanceConfig`` (kick block; bare SI numbers
        already: v_kick [m/s], max_duration and deadline [s]). Only the
        hold_to_alignment kick exists (KICK_MODES)."""
        kick = cfg.kick
        if kick.mode not in KICK_MODES:
            raise ValueError(f"kick mode {kick.mode!r} is not one of {KICK_MODES}")
        return cls(kick.v_kick_mps, kick.max_duration_s, kick.deadline_s)

    @classmethod
    def vertical_only(cls) -> GuidanceSpec:
        """Guidance that never kicks: stage 1 flies VERTICAL_RISE (radial thrust) to
        burnout. For the planner-level reductions to the 1-D model; never built from a
        config."""
        return cls(math.inf, math.inf, math.inf)


# --------------------------------------------------------------- gamma* inner solve


class Stage1Flight(Protocol):
    """What ``solve_delta_for_gamma`` needs from one stage-1 flight: the Earth-relative
    flight-path angle at MECO [rad] (``phases.planar.Handover`` provides it)."""

    @property
    def gamma_meco_rad(self) -> float:
        """gamma_rel at stage-1 burnout [rad]."""
        ...


@dataclass(frozen=True)
class DeltaSolveSettings:
    """Settings of the delta inner solve (from ``config.SearchConfig``; radians).

    bracket_rad: (low, high) kick angles [rad], 0 < low < high < pi/2; step_rad: the
    first bracketing step [rad] from a warm start (doubling); xtol_rad: brentq's
    absolute tolerance on delta [rad]; rtol: brentq's relative tolerance (>= 4 eps);
    root_tol_rad: the false-root guard, the largest |gamma_MECO(delta*) - gamma*| [rad]
    a root may leave (amendment 7); maxiter: brentq's iteration cap.
    """

    bracket_rad: tuple[float, float]
    step_rad: float
    xtol_rad: float
    rtol: float
    root_tol_rad: float
    maxiter: int = BRENTQ_MAXITER

    def __post_init__(self) -> None:
        lo, hi = self.bracket_rad
        if not 0.0 < lo < hi < 0.5 * math.pi:
            raise ValueError(f"bracket_rad must satisfy 0 < low < high < pi/2, got {(lo, hi)}")
        if min(self.step_rad, self.xtol_rad, self.rtol, self.root_tol_rad) <= 0.0:
            raise ValueError("step_rad, xtol_rad, rtol and root_tol_rad must be > 0")
        if self.maxiter < 1:
            raise ValueError("maxiter must be >= 1")

    @classmethod
    def from_config(cls, cfg: SearchConfig) -> DeltaSolveSettings:
        """The settings of a validated ``config.SearchConfig`` (its _rad properties)."""
        return cls(
            bracket_rad=cfg.delta_bracket_rad,
            step_rad=cfg.delta_step_rad,
            xtol_rad=cfg.delta_xtol_rad,
            rtol=cfg.brentq_rtol,
            root_tol_rad=cfg.gamma_root_tol_rad,
        )


@dataclass(frozen=True, eq=False)
class DeltaSolution[F]:
    """The solved kick: delta_rad [rad], the flight's gamma_MECO [rad] (within
    root_tol of gamma* by construction), the flight object itself (``handover``, the
    one flown at delta_rad), the number of stage-1 flights the solve flew, and the
    bracket (low, high) [rad] brentq was handed."""

    delta_rad: float
    gamma_meco_rad: float
    handover: F
    flights: int
    bracket_rad: tuple[float, float]


def solve_delta_for_gamma[F: Stage1Flight](
    fly_stage1: Callable[[float], F],
    gamma_star_rad: float,
    settings: DeltaSolveSettings,
    warm: float | None = None,
) -> DeltaSolution[F]:
    """The kick angle delta [rad] whose stage-1 flight reaches gamma_rel = gamma* at MECO.

    Inputs: fly_stage1(delta [rad]) -> a flight with ``gamma_meco_rad`` (one stage-1
    flight to MECO at the caller's tolerances; it raises GuidanceFailure on failure);
    gamma_star_rad, the target Earth-relative flight-path angle at MECO [rad];
    settings; warm, the last solved delta [rad] of this run for the nearest gamma* (None
    for a cold start). Output: a DeltaSolution. Method (docs/physics.md, "gamma* inner
    solve"): f(delta) = gamma_MECO(delta) - gamma*, decreasing in delta (a harder kick
    turns over sooner); a flight that hits the ground before the end of what
    fly_stage1 flies (GuidanceFailure kind "impact": before MECO, or in the staging
    coast before stage-2 ignition when the callable flies through staging) counts as
    gamma_MECO = -pi/2 (IMPACT_GAMMA_RAD) and a kick that
    times out (kind "kick_timeout", a kick too small to turn the velocity against the
    Coriolis deflection) as +pi (TIMEOUT_GAMMA_RAD); every other GuidanceFailure
    (no_kick, which does not depend on delta) propagates. Cold: f at both bracket ends.
    Warm: from the warm delta (clipped to the bracket) step by step_rad toward the root
    (up when f > 0), doubling, until f changes sign; reaching a bracket end without a
    sign change raises GuidanceFailure("gamma_unattainable"). Then brentq(xtol, rtol,
    maxiter) on the sign-change interval. False-root guard (amendment 7): the root must
    be a real flight with |gamma_MECO(delta*) - gamma*| <= root_tol_rad; a root brentq
    found across the impact discontinuity (gamma* inside the gap between the
    shallowest impacting flight and -pi/2), or across the timeout discontinuity,
    raises GuidanceFailure("false_root").
    Flights are cached by delta, so brentq's end-point re-evaluations fly nothing.
    """
    lo, hi = settings.bracket_rad
    cache: dict[float, tuple[float, F | None]] = {}

    def gamma_of(delta: float) -> float:
        hit = cache.get(delta)
        if hit is not None:
            return hit[0]
        flight: F | None
        try:
            flight = fly_stage1(delta)
            gamma = float(flight.gamma_meco_rad)
        except GuidanceFailure as exc:
            if exc.kind not in SENTINEL_GAMMA_RAD:
                raise
            flight, gamma = None, SENTINEL_GAMMA_RAD[exc.kind]
        cache[delta] = (gamma, flight)
        return gamma

    def f(delta: float) -> float:
        return gamma_of(delta) - gamma_star_rad

    a, b = _bracket(f, lo, hi, settings.step_rad, warm)
    if a == b:
        delta = a
    else:
        delta = float(
            brentq(
                f,
                min(a, b),
                max(a, b),
                xtol=settings.xtol_rad,
                rtol=settings.rtol,
                maxiter=settings.maxiter,
            )
        )
    gamma = gamma_of(delta)
    flight = cache[delta][1]
    if flight is None or abs(gamma - gamma_star_rad) > settings.root_tol_rad:
        raise GuidanceFailure(
            "false_root",
            f"brentq returned delta = {delta:.10g} rad for gamma* = {gamma_star_rad:.10g} "
            f"rad, but that flight reaches gamma_MECO = {gamma:.10g} rad "
            f"({'a failed flight' if flight is None else 'a real flight'}); |error| exceeds "
            f"root_tol {settings.root_tol_rad:.3g} rad: gamma* lies in a discontinuity "
            "of gamma_MECO(delta) (the impact or timeout gap)",
        )
    return DeltaSolution(delta, gamma, flight, len(cache), (min(a, b), max(a, b)))


def _bracket(
    f: Callable[[float], float], lo: float, hi: float, step: float, warm: float | None
) -> tuple[float, float]:
    """A sign-change interval (a, b) of the decreasing f inside [lo, hi] [rad], or
    (x, x) when f(x) == 0 exactly at an evaluated point; GuidanceFailure
    ("gamma_unattainable") when f keeps its sign up to a bracket end."""
    if warm is None:
        f_lo, f_hi = f(lo), f(hi)
        if f_lo == 0.0:
            return lo, lo
        if f_hi == 0.0:
            return hi, hi
        if f_lo * f_hi > 0.0:
            raise GuidanceFailure(
                "gamma_unattainable",
                f"gamma_MECO - gamma* keeps its sign over the kick bracket "
                f"[{lo:.6g}, {hi:.6g}] rad ({f_lo:.6g} and {f_hi:.6g} rad)",
            )
        return lo, hi
    a = min(max(warm, lo), hi)
    f_a = f(a)
    if f_a == 0.0:
        return a, a
    sign = 1.0 if f_a > 0.0 else -1.0
    while True:
        b = min(max(a + sign * step, lo), hi)
        f_b = f(b)
        if f_b == 0.0:
            return b, b
        if f_a * f_b < 0.0:
            return a, b
        if b in (lo, hi):
            raise GuidanceFailure(
                "gamma_unattainable",
                f"stepping from the warm delta {warm:.6g} rad reached the bracket end "
                f"{b:.6g} rad without a sign change of gamma_MECO - gamma* ({f_b:.6g} rad)",
            )
        a, f_a = b, f_b
        step *= 2.0


# ------------------------------------------------------------------ LTG shooting

LTG_RUNGS = ("warm", "physics", "steep", "shallow")
"""The LTG guess ladder in order; equal to ``config.LTG_GUESS_RUNGS``, which validates
``grid_max_rungs`` (tests/test_ltg.py asserts the two agree)."""


class LtgShot(Protocol):
    """What ``solve_ltg`` needs from one stage-2 shot (``phases.planar.Stage2Result``
    provides it): the radius [m] and the radial velocity [m/s] at the cutoff, and the
    burn time tau_c [s] from stage-2 ignition to the cutoff."""

    @property
    def r_cut_m(self) -> float:
        """Radius from Earth's centre at the cutoff [m]."""
        ...

    @property
    def v_r_cut_mps(self) -> float:
        """Radial velocity at the cutoff [m/s] (inertial = Earth-relative)."""
        ...

    @property
    def tau_cut_s(self) -> float:
        """Burn time from stage-2 ignition to the cutoff [s]."""
        ...


@dataclass(frozen=True)
class LtgSettings:
    """Settings of the LTG shooting and of the stage-2 burn limits (from
    ``config.LtgConfig``; SI and radians).

    accept_r_m [m] and accept_vr_mps [m/s]: the acceptance |r_c - r_t| < accept_r and
    |v_r,c| < accept_vr; r_scale_m [m] and vr_scale_mps [m/s]: the residual scaling
    F = ((r_c - r_t)/r_scale, v_r,c/vr_scale); fd_step: the forward-difference step in
    x = (a, LTG_B_SCALE_S b) units (the search or the final value); max_iters and
    max_halvings: the damped Newton's limits; max_rungs: the most ladder rungs a solve
    tries (``grid_max_rungs`` for a gamma* grid point, the whole ladder otherwise);
    p0_offset_rad, pf_rad and steep_p0_rad [rad] and shallow_guess (x units): the guess
    ladder; pitch_bounds_rad (low, high) [rad]: the direct-root pitch window;
    tau_max_factor: no_cutoff beyond tau_max_factor tau_b; mass_floor_factor: the
    search mass floor mass_floor_factor (m_d2 + P).
    """

    accept_r_m: float
    accept_vr_mps: float
    r_scale_m: float
    vr_scale_mps: float
    fd_step: float
    max_iters: int
    max_halvings: int
    max_rungs: int
    p0_offset_rad: float
    pf_rad: float
    steep_p0_rad: float
    shallow_guess: tuple[float, float]
    pitch_bounds_rad: tuple[float, float]
    tau_max_factor: float
    mass_floor_factor: float

    def __post_init__(self) -> None:
        scales = (self.accept_r_m, self.accept_vr_mps, self.r_scale_m, self.vr_scale_mps)
        if min(*scales, self.fd_step) <= 0.0:
            raise ValueError("LTG acceptance thresholds, scales and fd_step must be > 0")
        if self.max_iters < 1 or self.max_halvings < 0 or self.max_rungs < 1:
            raise ValueError("max_iters >= 1, max_halvings >= 0 and max_rungs >= 1 required")
        lo, hi = self.pitch_bounds_rad
        if not -0.5 * math.pi < lo < hi < 0.5 * math.pi:
            raise ValueError(f"pitch_bounds_rad must be ordered inside (-pi/2, pi/2): {(lo, hi)}")
        if not self.tau_max_factor > 1.0 or not 0.0 < self.mass_floor_factor < 1.0:
            raise ValueError("tau_max_factor must be > 1 and mass_floor_factor in (0, 1)")

    @classmethod
    def from_config(cls, cfg: LtgConfig, *, final: bool, grid: bool = False) -> LtgSettings:
        """Settings of a validated ``config.LtgConfig``: fd_step_final for a final
        solve (final True) else fd_step_search; max_rungs = grid_max_rungs for a gamma*
        grid point (grid True) else the whole ladder (len(LTG_RUNGS))."""
        return cls(
            accept_r_m=cfg.accept_r_m,
            accept_vr_mps=cfg.accept_vr_mps,
            r_scale_m=cfg.r_scale_m,
            vr_scale_mps=cfg.vr_scale_mps,
            fd_step=cfg.fd_step_final if final else cfg.fd_step_search,
            max_iters=cfg.max_iters,
            max_halvings=cfg.max_halvings,
            max_rungs=cfg.grid_max_rungs if grid else len(LTG_RUNGS),
            p0_offset_rad=cfg.p0_offset_rad,
            pf_rad=cfg.pf_rad,
            steep_p0_rad=cfg.steep_p0_rad,
            shallow_guess=cfg.shallow_guess,
            pitch_bounds_rad=cfg.pitch_bounds_rad,
            tau_max_factor=cfg.tau_max_factor,
            mass_floor_factor=cfg.mass_floor_factor,
        )


@dataclass(frozen=True, eq=False)
class LtgSolution[S: LtgShot]:
    """A converged direct LTG root: a (tan p at stage-2 ignition), b_per_s [1/s], the
    burn time tau_cut_s [s] from stage-2 ignition to the cutoff, the accepted shot
    itself, the Newton iterations of the winning rung, the total number of shots flown
    over every rung tried (finite differences and line-search trials included) and the
    winning rung's name (one of LTG_RUNGS)."""

    a: float
    b_per_s: float
    tau_cut_s: float
    shot: S
    iters: int
    shots: int
    rung: str


def ltg_physics_guess(
    gamma_in_rad: float, tau_b_s: float, p0_offset_rad: float, pf_rad: float
) -> tuple[float, float]:
    """The physics guess (a, b [1/s]) of the LTG ladder: initial pitch p0 = gamma_in +
    p0_offset_rad, final pitch p_f = pf_rad over the stage's full-thrust burn time
    tau_b_s [s], so a = tan p0 and b = (tan p0 - tan p_f)/tau_b. gamma_in_rad [rad] is
    the inertial flight-path angle atan2(v_r, v_theta) at stage-2 ignition (plan
    section 6)."""
    if not tau_b_s > 0.0:
        raise ValueError(f"tau_b_s must be > 0, got {tau_b_s!r}")
    a = math.tan(gamma_in_rad + p0_offset_rad)
    return a, (a - math.tan(pf_rad)) / tau_b_s


def ltg_guess_ladder(
    settings: LtgSettings,
    gamma_in_rad: float,
    tau_b_s: float,
    warm: tuple[float, float] | None = None,
) -> tuple[tuple[str, tuple[float, float]], ...]:
    """The guess ladder ((rung, (a, b [1/s])), ...) in LTG_RUNGS order: warm (this run's
    last converged (a, b); omitted when None), physics (``ltg_physics_guess``), steep
    (p0 = steep_p0_rad with the physics p_f) and shallow (x = shallow_guess, i.e.
    b = x_2 / LTG_B_SCALE_S). gamma_in_rad [rad]: the inertial flight-path angle at
    stage-2 ignition; tau_b_s [s]: stage 2's full-thrust burn time."""
    steep_a = math.tan(settings.steep_p0_rad)
    physics = ltg_physics_guess(gamma_in_rad, tau_b_s, settings.p0_offset_rad, settings.pf_rad)
    ladder: list[tuple[str, tuple[float, float]]] = []
    if warm is not None:
        ladder.append(("warm", (float(warm[0]), float(warm[1]))))
    ladder += [
        ("physics", physics),
        ("steep", (steep_a, (steep_a - math.tan(settings.pf_rad)) / tau_b_s)),
        ("shallow", (settings.shallow_guess[0], settings.shallow_guess[1] / LTG_B_SCALE_S)),
    ]
    return tuple(ladder)


def is_direct_root(
    a: float, b_per_s: float, tau_cut_s: float, pitch_bounds_rad: tuple[float, float]
) -> bool:
    """Whether (a, b [1/s]) is a direct LTG root: b > 0 and the pitch atan(a - b tau)
    inside the open window pitch_bounds_rad (low, high) [rad] over the whole burn
    0 <= tau <= tau_cut_s [s] (the pitch is monotone in tau, so its two ends decide).
    The b > 0 test is the plan's pre-registered rule; above a case-dependent gamma*
    (about 30 deg on the gate pad) it rejects the only root, which has b < 0 and a
    positive residual (docs/physics.md, "LTG shooting", Direct-root boundary)."""
    lo, hi = pitch_bounds_rad
    return b_per_s > 0.0 and lo < math.atan(a - b_per_s * tau_cut_s) and math.atan(a) < hi


def solve_ltg[S: LtgShot](
    shoot: Callable[[float, float], S],
    target_r_m: float,
    settings: LtgSettings,
    ladder: tuple[tuple[str, tuple[float, float]], ...],
) -> LtgSolution[S]:
    """The stage-2 linear-tangent pair (a, b) whose cutoff lands on the target radius
    with zero radial velocity (docs/physics.md, "LTG shooting").

    Inputs: shoot(a, b [1/s]) -> one stage-2 shot from the run's hand-over (it raises
    GuidanceFailure when the burn fails: impact, no_cutoff, mass_floor); target_r_m,
    the target radius r_t [m]; settings; the guess ladder (``ltg_guess_ladder``), of
    which the first settings.max_rungs rungs are tried in order. Unknowns x = (a,
    LTG_B_SCALE_S b); residual F = ((r_c - r_t)/r_scale, v_r,c/vr_scale). Each rung
    runs a damped Newton: the Jacobian by forward differences with step fd_step (a
    backward difference when the forward shot fails), the step dx = -J^-1 F, halved at
    most max_halvings times while a trial shot raises GuidanceFailure or ||F|| does not
    decrease, at most max_iters iterations. A rung converges when |r_c - r_t| <
    accept_r_m and |v_r,c| < accept_vr_mps; the root must then be direct
    (``is_direct_root``), else the rung fails with not_direct_root. A rung also fails
    on any GuidanceFailure of its starting shot, a singular Jacobian, a failed line
    search or the iteration limit, and the next rung starts. Output: the LtgSolution
    of the first converged direct root. Raises GuidanceFailure("nonconverged") naming
    every rung's outcome when the ladder is exhausted; never returns an unconverged x.
    """
    outcomes: list[str] = []
    counter = [0]
    for rung, guess in ladder[: settings.max_rungs]:
        try:
            a, b, shot, iters = _newton_ltg(shoot, target_r_m, settings, guess, counter)
        except GuidanceFailure as exc:
            outcomes.append(f"{rung}: {exc}")
            continue
        return LtgSolution(a, b, shot.tau_cut_s, shot, iters, counter[0], rung)
    raise GuidanceFailure(
        "nonconverged", "LTG guess ladder exhausted (" + "; ".join(outcomes) + ")"
    )


def _newton_ltg[S: LtgShot](
    shoot: Callable[[float, float], S],
    target_r_m: float,
    st: LtgSettings,
    guess: tuple[float, float],
    counter: list[int],
) -> tuple[float, float, S, int]:
    """One rung of ``solve_ltg``: the damped Newton from guess (a, b [1/s]). Returns
    (a, b [1/s], shot, iterations); raises GuidanceFailure on failure. counter[0]
    counts the shots flown."""

    def fly(x: np.ndarray) -> tuple[S, np.ndarray]:
        counter[0] += 1
        shot = shoot(float(x[0]), float(x[1]) / LTG_B_SCALE_S)
        dr = (shot.r_cut_m - target_r_m) / st.r_scale_m
        return shot, np.array([dr, shot.v_r_cut_mps / st.vr_scale_mps])

    x = np.array([guess[0], guess[1] * LTG_B_SCALE_S], dtype=float)
    shot, f = fly(x)
    for it in range(st.max_iters + 1):
        if (
            abs(shot.r_cut_m - target_r_m) < st.accept_r_m
            and abs(shot.v_r_cut_mps) < st.accept_vr_mps
        ):
            a, b = float(x[0]), float(x[1]) / LTG_B_SCALE_S
            if not is_direct_root(a, b, shot.tau_cut_s, st.pitch_bounds_rad):
                raise GuidanceFailure(
                    "not_direct_root",
                    f"converged to a = {a:.6g}, b = {b:.6g} 1/s (tau_c = "
                    f"{shot.tau_cut_s:.6g} s) outside the direct-root window",
                )
            return a, b, shot, it
        if it == st.max_iters:
            break
        jac = np.empty((2, 2))
        for j in range(2):
            step = np.zeros(2)
            step[j] = st.fd_step
            try:
                f_j = fly(x + step)[1]
                jac[:, j] = (f_j - f) / st.fd_step
            except GuidanceFailure:
                f_j = fly(x - step)[1]
                jac[:, j] = (f - f_j) / st.fd_step
        try:
            dx = -np.linalg.solve(jac, f)
        except np.linalg.LinAlgError:
            raise GuidanceFailure("nonconverged", "singular LTG Jacobian") from None
        if not np.all(np.isfinite(dx)):
            raise GuidanceFailure("nonconverged", "non-finite LTG Newton step")
        norm = float(np.hypot(f[0], f[1]))
        lam = 1.0
        for _halving in range(st.max_halvings + 1):
            try:
                trial_shot, trial_f = fly(x + lam * dx)
            except GuidanceFailure:
                lam *= 0.5
                continue
            if float(np.hypot(trial_f[0], trial_f[1])) < norm:
                x, shot, f = x + lam * dx, trial_shot, trial_f
                break
            lam *= 0.5
        else:
            raise GuidanceFailure(
                "nonconverged",
                f"line search failed after {st.max_halvings} halvings at ||F|| = {norm:.3g}",
            )
    raise GuidanceFailure(
        "nonconverged",
        f"{st.max_iters} Newton iterations without meeting the acceptance (|dr| = "
        f"{abs(shot.r_cut_m - target_r_m):.3g} m, |v_r| = {abs(shot.v_r_cut_mps):.3g} m/s)",
    )
