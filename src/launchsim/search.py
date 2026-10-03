"""Figures of merit of a planar run found by search: rung 2 (``residual``: the residual
stage-2 propellant m_res and the delta-v margin at a fixed payload) and rung 3
(``payload_capacity``: the payload P* at which m_res = 0), with the shared gamma* sweep
(``optimise_gamma``) and the tight final verification (``final_verify``) that produces
the recorded run (docs/physics.md, "Figures of merit (planar)", "Virtual propellant",
"Payload and gamma* search" and "Shared budget").

Every result is "sweep-optimized" (plan decision 4; Phase 5 replaces the sweep by an
optimiser): the guidance parametrisation, the gamma* grid and the search budget
(``SearchBudget``, from the experiment-level ``config.SearchConfig``) are the same for
every run of an experiment, and only the free guidance inputs (gamma*, delta, a, b) and
the payload are solved per run.

The algorithms work on any ``SearchProblem``: a ``budget`` and an ``evaluate(P, gamma*,
warm, mode)`` that returns a ``ResidualResult`` or raises one of the ``INFEASIBLE``
exceptions (a typed ``guidance.GuidanceFailure`` or a ``PreludeFailure``).
``SearchContext`` is the planar problem (frozen parameters: vehicle, ignition, guidance,
environment, target, integrator settings, budget, assist and track); ``WarmStore`` is the
per-run warm-start memory (the last solved delta and LTG pair for the nearest gamma*, and
the delta-independent kick point per payload), created fresh for every run, so no result
depends on which run went before (no cross-run seeding, no module-level cache).

Failures of the search itself raise ``SearchFailed`` (kind in SEARCH_FAILURE_KINDS);
``run_search`` turns one into a ``SearchRecord`` with status ``search_failed``. Guidance
failures of single evaluations become finite penalties on the gamma* grid, never -inf
(a bounded Brent would warn on it, and warnings fail the tests). ``joint_root_crosscheck``
is test-only (the joint 3-equation root, rejected in production, plan section 3).

Pure: no I/O, no globals, no printing. SI units and radians throughout (payloads [kg],
angles [rad], speeds [m/s]); frames as in ``phases.planar`` (planar ECI; gamma* is the
Earth-relative flight-path angle at MECO).
"""

from __future__ import annotations

import dataclasses
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np
from scipy.optimize import brentq, minimize_scalar

from launchsim.assist import build_assist
from launchsim.atmosphere import ambient_scalar
from launchsim.constants import MU_EARTH_M3S2
from launchsim.dynamics import PLANAR_LAYOUT, InverseSquareGravity
from launchsim.guidance import (
    LTG_B_SCALE_S,
    DeltaSolveSettings,
    GuidanceFailure,
    GuidanceSpec,
    LtgSettings,
    solve_delta_for_gamma,
)
from launchsim.orbit import TargetOrbit
from launchsim.phases.engine import IntegratorSettings
from launchsim.phases.planar import (
    INSERTED_STATUS,
    OFF_TARGET_STATUS,
    SHORT_OF_ORBIT_STATUS,
    KickPoint,
    PlanarEnvironment,
    PlanarPlanner,
    Stage2Result,
)
from launchsim.phases.prelude import IgnitionSpec, resolve_stage_ignitions
from launchsim.phases.trace import RunTrace
from launchsim.vehicle import Vehicle, with_payload

if TYPE_CHECKING:
    from launchsim.assist.base import AssistModel, TrackGeometry
    from launchsim.config import ChecksConfig, ConvergenceConfig, RunConfig, SearchConfig

GRID_MODE = "grid"
"""Evaluation mode of a gamma* grid point: search tolerances, at most
``ltg.grid_max_rungs`` LTG ladder rungs."""
SEARCH_MODE = "search"
"""Evaluation mode of the payload searches and the refine: search tolerances (rtol
``search_rtol``, atol x ``search_atol_scale``, dense output off), the whole ladder."""
FINAL_MODE = "final"
"""Evaluation mode of the final verification: the run's final tolerance (rtol
``final_rtol``, the per-state atol), ``ltg.fd_step_final``, the whole ladder, dense
output off (the recorded run re-flies the last evaluation with it on)."""
EVAL_MODES = (GRID_MODE, SEARCH_MODE, FINAL_MODE)
"""Every evaluation mode."""
OK_STATUS = "ok"
"""Status of a payload search that found P* > 0 (m_res(P*) = 0)."""
NO_ORBIT_STATUS = "no_orbit"
"""Status of a payload search whose m_res(0) < 0: even an empty vehicle misses the
orbit; P* = 0 and the shortfall is -dv_margin(0)."""
SEARCH_FAILED_STATUS = "search_failed"
"""Status of a run whose search raised SearchFailed (NaN figures of merit, flags)."""
SEARCH_SHORT_STATUS = SHORT_OF_ORBIT_STATUS
"""Status of a figure_of_merit residual search whose final-tolerance m_res at the
vehicle payload is negative (plan section 5: a negative rung 2 is short_of_orbit; the
signed m_res and dv_margin are the figures)."""
FROM_RECORDED_RUN = "recorded_run"
"""``RecordedRun.figures_from``: m_res and dv_margin measured at the recorded run's
energy cutoff (it reached the cutoff)."""
FROM_FINAL_EVALUATION = "final_evaluation"
"""``RecordedRun.figures_from``: the recorded run's real propellant ran out before the
cutoff (or stage 2 never finished its burn), so m_res and dv_margin are the signed
values of the final-tolerance virtual-propellant evaluation it re-flies (never the ~0
left at depletion)."""
CUT_STATE_SCALE_FLOOR = 1.0
"""Floor of the per-component scale of ``RecordedRun.cut_state_rel_diff``, in each
component's own unit (m, rad, m/s, kg): it keeps components near zero (theta, the
quadratures early on) from dividing by ~0, so the diagnostic is absolute below 1 unit."""
SEARCH_FAILURE_KINDS = ("edge", "grid", "bracket", "root", "final_bracket", "final_run")
"""Kinds of ``SearchFailed``: the best gamma* grid point, or the refined gamma*_ref, on
a grid bound (edge; widen the shared grid for every run), no feasible grid point at P0
nor at P = 0 (grid), no payload bracket (bracket), an infeasible evaluation inside the
payload bracket or the final bisection (root), no bracket of the final verification
within final_bracket_kg (final_bracket), and a recorded run that disagrees with its
evaluation (final_run: with m_res >= 0 it must end inserted with 0 <= m_res <
final_payload_xtol_kg; with m_res < 0 it must stop short of the cutoff), or a final
residual evaluation that cannot fly."""
FEASIBLE_POINT = "feasible"
"""Grid-point label: the evaluation converged (m_res is the objective)."""
INFEASIBLE_POINT = "infeasible"
"""Grid-point label: a guidance or prelude failure (the penalty is the objective)."""
RETRY_KINDS = ("nonconverged",)
"""GuidanceFailure kinds after which a failed grid point is retried from a converged
neighbour's delta and LTG pair: an exhausted LTG ladder depends on its starting pair
(docs/physics.md, "LTG shooting", Cold-ladder coverage); the stage-1 failures
(gamma_unattainable, false_root, no_kick) and lofted_overshoot do not."""
RULE_INFEASIBLE_POINT = "not_direct_root"
"""Grid-point label: the LTG ladder converged only to roots the pre-registered
direct-root rule rejects (b <= 0 or the pitch window; docs/physics.md, "LTG shooting",
Direct-root boundary): infeasible by the rule, not by the physics."""
NOT_DIRECT_ROOT_PATTERN = re.compile(r"\bnot_direct_root:")
"""How a rung outcome inside a GuidanceFailure('nonconverged') message names a
converged indirect root (``guidance.solve_ltg`` lists 'rung: kind: message' per rung)."""
JOINT_P_SCALE_KG = 1.0e4
"""Scale [kg] of the payload unknown of the test-only joint root, x_3 = P / scale."""
JOINT_M_SCALE_KG = 1.0e3
"""Scale [kg] of the m_res residual of the test-only joint root."""


class PreludeFailure(RuntimeError):
    """The prelude of an evaluation ended without a flight (kind ``no_liftoff`` or
    ``drive_limit``, the planner's status) or stage 1 does not light (``ignition``): the
    payload or the configuration cannot fly. All arguments go to RuntimeError, so the
    exception pickles; a search treats it like a GuidanceFailure."""

    def __init__(self, kind: str, message: str = "") -> None:
        super().__init__(kind, message)
        self.kind = kind
        self.message = message

    def __str__(self) -> str:
        return f"{self.kind}: {self.message}" if self.message else self.kind


INFEASIBLE: tuple[type[Exception], ...] = (GuidanceFailure, PreludeFailure)
"""Exceptions an evaluation raises for an infeasible (payload, gamma*) point; the searches
turn them into penalties, backoffs or statuses. Every other exception is a code error
and propagates."""


class SearchFailed(RuntimeError):
    """A search that cannot produce its figure of merit: kind (one of
    SEARCH_FAILURE_KINDS), a message, and ``grid`` (the gamma* grid table evaluated so
    far, plain GridPoint records, or empty). Every argument goes to RuntimeError
    (``args == (kind, message, grid)``), so it pickles and re-raises intact. The run gets
    status ``search_failed`` with NaN figures of merit (``run_search``)."""

    def __init__(self, kind: str, message: str = "", grid: tuple[GridPoint, ...] = ()) -> None:
        if kind not in SEARCH_FAILURE_KINDS:
            raise ValueError(f"unknown search failure kind {kind!r}")
        super().__init__(kind, message, grid)
        self.kind = kind
        self.message = message
        self.grid = grid

    def __str__(self) -> str:
        return f"{self.kind}: {self.message}" if self.message else self.kind


# ---------------------------------------------------------------------------- budget


@dataclass(frozen=True)
class SearchBudget:
    """The shared search budget of an experiment, in SI and radians (from
    ``config.SearchConfig`` and the flag threshold of ``config.ChecksConfig``).

    figure_of_merit: payload, residual or none. gamma_grid_rad: the gamma* grid points
    [rad]; refine_halfwidth_rad, gamma_xatol_rad [rad] and refine_maxiter: the bounded
    Brent refine. delta: the inner delta solve. payload_halves_kg: the half-widths [kg]
    of the payload bracket around its hint, first try then each x2 expansion
    (payload_max_expand of them); payload_backoff_max: the halvings back toward the last
    feasible payload; payload_xtol_kg [kg] and brentq_rtol: the payload brentq.
    final_halves_kg: the final verification's half-widths [kg] (final_bracket_kg's start,
    doubled up to its maximum); final_payload_xtol_kg [kg]: its brentq tolerance, also
    the largest residual [kg] the recorded run may keep. search_rtol, search_atol_scale
    (a factor on the final atol, >= 1), final_rtol, final_atol_scale (a factor on the
    per-state atol, 1 as shipped): the integration tolerances. penalty_base_kg [kg] and
    penalty_per_rad_kg [kg/rad]: the infeasible-point objective. ltg_grid, ltg_search and
    ltg_final: the LTG settings per mode. final_flag_rel: flag |P_search - P_final| above
    this fraction of P_final (``checks.search_final_flag_rel``). budget_id: the sha256
    of the search block (``SearchConfig.budget_id``), with a suffix when tightened.
    """

    figure_of_merit: str
    gamma_grid_rad: tuple[float, ...]
    refine_halfwidth_rad: float
    gamma_xatol_rad: float
    refine_maxiter: int
    delta: DeltaSolveSettings
    payload_halves_kg: tuple[float, ...]
    payload_backoff_max: int
    payload_xtol_kg: float
    brentq_rtol: float
    final_halves_kg: tuple[float, ...]
    final_payload_xtol_kg: float
    search_rtol: float
    search_atol_scale: float
    final_rtol: float
    final_atol_scale: float
    penalty_base_kg: float
    penalty_per_rad_kg: float
    ltg_grid: LtgSettings
    ltg_search: LtgSettings
    ltg_final: LtgSettings
    final_flag_rel: float
    budget_id: str

    def __post_init__(self) -> None:
        if len(self.gamma_grid_rad) < 1 or list(self.gamma_grid_rad) != sorted(
            set(self.gamma_grid_rad)
        ):
            raise ValueError("gamma_grid_rad must be strictly increasing and non-empty")
        for name in ("payload_halves_kg", "final_halves_kg"):
            halves = getattr(self, name)
            if not halves or min(halves) <= 0.0 or list(halves) != sorted(halves):
                raise ValueError(f"{name} must be positive and non-decreasing")
        positive = (
            self.refine_halfwidth_rad,
            self.gamma_xatol_rad,
            self.payload_xtol_kg,
            self.final_payload_xtol_kg,
            self.search_rtol,
            self.final_rtol,
            self.final_atol_scale,
            self.penalty_base_kg,
        )
        if min(positive) <= 0.0 or self.search_atol_scale < 1.0 or self.penalty_per_rad_kg < 0.0:
            raise ValueError("search budget tolerances, scales and penalties out of range")
        if self.refine_maxiter < 1 or self.payload_backoff_max < 0:
            raise ValueError("refine_maxiter >= 1 and payload_backoff_max >= 0 required")

    @classmethod
    def from_config(cls, search: SearchConfig, checks: ChecksConfig) -> SearchBudget:
        """The budget of a validated SearchConfig (its ``_rad`` and ``_kg`` properties;
        the LTG settings per mode from ``search.ltg``) and ChecksConfig (the final-vs-search
        flag threshold)."""
        half = search.payload_half_bracket_kg
        start, cap = search.final_bracket_kg
        return cls(
            figure_of_merit=search.figure_of_merit,
            gamma_grid_rad=search.gamma_grid_points_rad,
            refine_halfwidth_rad=search.gamma_refine_halfwidth_rad,
            gamma_xatol_rad=search.gamma_xatol_rad,
            refine_maxiter=search.gamma_refine_maxiter,
            delta=DeltaSolveSettings.from_config(search),
            payload_halves_kg=tuple(half * 2.0**k for k in range(search.payload_max_expand + 1)),
            payload_backoff_max=search.payload_backoff_max,
            payload_xtol_kg=search.payload_xtol_kg,
            brentq_rtol=search.brentq_rtol,
            final_halves_kg=doubling_halves(start, cap),
            final_payload_xtol_kg=search.final_payload_xtol_kg,
            search_rtol=search.search_rtol,
            search_atol_scale=search.search_atol_scale,
            final_rtol=search.final_rtol,
            final_atol_scale=1.0,
            penalty_base_kg=search.penalty.base_kg,
            penalty_per_rad_kg=search.penalty.per_rad_kg,
            ltg_grid=LtgSettings.from_config(search.ltg, final=False, grid=True),
            ltg_search=LtgSettings.from_config(search.ltg, final=False),
            ltg_final=LtgSettings.from_config(search.ltg, final=True),
            final_flag_rel=checks.search_final_flag_rel,
            budget_id=search.budget_id(),
        )

    def ltg_for(self, mode: str) -> LtgSettings:
        """The LTG settings of an evaluation mode (EVAL_MODES)."""
        return {GRID_MODE: self.ltg_grid, SEARCH_MODE: self.ltg_search, FINAL_MODE: self.ltg_final}[
            mode
        ]

    def tightened(self, factor: float) -> SearchBudget:
        """The budget with every tolerance divided by factor (> 1; amendment 3): search
        and final rtol, the atol (final_atol_scale, which the search atol multiplies),
        the LTG acceptance thresholds, and the delta, payload, final-payload and gamma
        xtols. The LTG finite-difference steps, the brackets, the penalties and the
        false-root guard are unchanged. The budget_id gains the suffix ``:tightened/<f>``."""
        if not factor > 1.0:
            raise ValueError(f"factor must be > 1, got {factor!r}")

        def ltg(s: LtgSettings) -> LtgSettings:
            return dataclasses.replace(
                s, accept_r_m=s.accept_r_m / factor, accept_vr_mps=s.accept_vr_mps / factor
            )

        return dataclasses.replace(
            self,
            gamma_xatol_rad=self.gamma_xatol_rad / factor,
            delta=dataclasses.replace(self.delta, xtol_rad=self.delta.xtol_rad / factor),
            payload_xtol_kg=self.payload_xtol_kg / factor,
            final_payload_xtol_kg=self.final_payload_xtol_kg / factor,
            search_rtol=self.search_rtol / factor,
            final_rtol=self.final_rtol / factor,
            final_atol_scale=self.final_atol_scale / factor,
            ltg_grid=ltg(self.ltg_grid),
            ltg_search=ltg(self.ltg_search),
            ltg_final=ltg(self.ltg_final),
            budget_id=f"{self.budget_id}:tightened/{factor:g}",
        )


def doubling_halves(start_kg: float, cap_kg: float) -> tuple[float, ...]:
    """Half-widths [kg] start, 2 start, 4 start, ... while below cap_kg, then cap_kg (the
    final verification's bracket, ``final_bracket_kg``: 20, 40, ..., 640, 1000 kg)."""
    if not 0.0 < start_kg <= cap_kg:
        raise ValueError(f"need 0 < start <= cap, got {(start_kg, cap_kg)}")
    halves = [start_kg]
    while halves[-1] < cap_kg:
        halves.append(min(2.0 * halves[-1], cap_kg))
    return tuple(halves)


# ------------------------------------------------------------------------ warm store


@dataclass(frozen=True)
class WarmEntry:
    """One solved evaluation remembered for warm starts: gamma* [rad], payload [kg], the
    kick angle delta [rad] (None for a problem without one) and the LTG pair (a, b [1/s])
    (None likewise)."""

    gamma_star_rad: float
    payload_kg: float
    delta_rad: float | None
    ltg: tuple[float, float] | None


@dataclass
class WarmStore:
    """The warm-start memory of one run (plan section 6: within one run only, in the
    run's deterministic evaluation order; no cross-run seeding, no LRU).

    entries: every solved evaluation in order; ``nearest(gamma*)`` returns the entry
    with the nearest gamma* (the latest one on a tie), so a solve starts from the last
    delta and LTG pair solved for the nearest gamma*. kicks: the delta-independent stage-1
    kick point per (payload [kg], tolerance class), or the infeasibility it raised
    (``KickPoint`` is flown once per payload and tolerance; plan section 9). owner: the
    problem the store belongs to (``claim``): the kick points depend on the vehicle,
    the assist, the ignition and the tolerances, not only on the key, so a store serves
    one problem object only (a perturbed or tightened context is another object)."""

    entries: list[WarmEntry] = field(default_factory=list)
    kicks: dict[tuple[float, str], KickPoint | Exception] = field(default_factory=dict)
    owner: object | None = field(default=None, repr=False, compare=False)

    def claim(self, owner: object) -> None:
        """Bind the store to owner (the problem evaluating with it) on first use; a
        store already bound to another object raises ValueError (one store per run and
        problem: a shared store would hand one problem another's cached kick point)."""
        if self.owner is None:
            self.owner = owner
        elif self.owner is not owner:
            raise ValueError(
                "this WarmStore belongs to another search problem; use a fresh WarmStore "
                "for every run and every perturbed or tightened context"
            )

    def add(self, entry: WarmEntry) -> None:
        """Remember a solved evaluation."""
        self.entries.append(entry)

    def nearest(self, gamma_star_rad: float) -> WarmEntry | None:
        """The entry with the gamma* nearest to gamma_star_rad [rad] (the latest on a
        tie), or None when the store is empty."""
        best: WarmEntry | None = None
        best_d = math.inf
        for entry in self.entries:
            d = abs(entry.gamma_star_rad - gamma_star_rad)
            if d <= best_d:
                best, best_d = entry, d
        return best

    def kick_point(self, key: tuple[float, str], make: Callable[[], KickPoint]) -> KickPoint:
        """The cached kick point for key (payload [kg], tolerance class), made with
        ``make`` on the first request; an infeasibility ``make`` raised is cached and
        raised again."""
        if key not in self.kicks:
            try:
                self.kicks[key] = make()
            except INFEASIBLE as exc:
                self.kicks[key] = exc
        hit = self.kicks[key]
        if isinstance(hit, Exception):
            raise hit
        return hit


# -------------------------------------------------------------------- problem protocol


@dataclass(frozen=True, eq=False)
class ResidualResult:
    """Rung 2 at one (payload, gamma*): the residual stage-2 propellant m_res_kg =
    m_c - m_empty [kg] (negative when the virtual propellant was needed) and the signed
    delta-v margin c2 ln(m_c/m_empty) [m/s] at the energy cutoff, with the guidance that
    produced them: delta_rad [rad] and ltg = (a, b [1/s]) (None for a problem without
    them), gamma_meco_rad [rad] (the flight's gamma_rel at MECO, within the false-root
    guard of gamma*), the LTG rung that converged, the stage-1 flights and stage-2 shots
    flown, the mode, and the accepted stage-2 shot (``Stage2Result``; None for a
    problem without one)."""

    payload_kg: float
    gamma_star_rad: float
    m_res_kg: float
    dv_margin_mps: float
    delta_rad: float | None
    ltg: tuple[float, float] | None
    gamma_meco_rad: float
    rung: str
    flights: int
    shots: int
    mode: str
    shot: Stage2Result | None = None


@dataclass(frozen=True, eq=False)
class RecordedRun:
    """The recorded run at the final payload: the trace (dense output on, the real
    stage-2 depletion event, final tolerance) and its status; the signed residual
    propellant m_res_kg [kg] and dv_margin_mps [m/s]; figures_from, where those two come
    from: FROM_RECORDED_RUN when the run reached the energy cutoff (inserted or
    off_target; measured at its cutoff), FROM_FINAL_EVALUATION when it did not (the real
    propellant ran out first, short_of_orbit: the values of the virtual-propellant
    evaluation it re-flies, negative, never the ~0 left at depletion); and
    cut_state_rel_diff, the largest per-component |y_recorded - y_evaluation| /
    max(|y_evaluation|, CUT_STATE_SCALE_FLOOR) at the cutoff against that evaluation (0
    when the two integrate the same steps; NaN without a recorded cutoff state)."""

    trace: RunTrace
    status: str
    m_res_kg: float
    dv_margin_mps: float
    cut_state_rel_diff: float
    figures_from: str = FROM_RECORDED_RUN


class SearchProblem(Protocol):
    """What the search algorithms need: the shared budget, the payload the gamma* grid
    runs at, and one evaluation of rung 2."""

    @property
    def budget(self) -> SearchBudget:
        """The shared search budget."""
        ...

    @property
    def payload_kg(self) -> float:
        """P0 [kg]: the payload of the gamma* grid (the vehicle's own payload)."""
        ...

    def evaluate(
        self,
        payload_kg: float,
        gamma_star_rad: float,
        warm: WarmStore,
        mode: str,
        *,
        seed: WarmEntry | None = None,
    ) -> ResidualResult:
        """Rung 2 at (payload [kg], gamma* [rad]) in mode (EVAL_MODES), warm-started from
        seed when given, else from ``warm.nearest(gamma*)``; the solved evaluation is added
        to warm. Raises one of INFEASIBLE when the point cannot fly."""
        ...


class RecordingProblem(SearchProblem, Protocol):
    """A SearchProblem that can also re-fly an evaluation as the recorded run."""

    def record(self, res: ResidualResult) -> RecordedRun:
        """The recorded run at res's payload with res's guidance (final tolerance, dense
        output on, the real depletion event)."""
        ...


# ------------------------------------------------------------------------ the context


@dataclass(frozen=True, eq=False)
class SearchContext:
    """The planar search problem of one run (frozen parameters; the warm store is kept
    apart, one per run).

    vehicle: the Vehicle at its own payload P0 [kg] (``with_payload`` gives each
    evaluation's); ignition: an IgnitionSpec per stage; guidance: the stage-1 GuidanceSpec
    (it must kick); env: the PlanarEnvironment; target: the circular TargetOrbit; settings:
    the run's IntegratorSettings (the recorded run's; rtol = final_rtol); budget: the
    SearchBudget; assist and track: the assist model and its track (None, None for a pad);
    z_ground_m [m]: the ground of the impact event; end: the run's end (insertion for a
    search). Frame: planar ECI (``phases.planar``).
    """

    vehicle: Vehicle
    ignition: Mapping[str, IgnitionSpec]
    guidance: GuidanceSpec
    env: PlanarEnvironment
    target: TargetOrbit
    settings: IntegratorSettings
    budget: SearchBudget
    assist: AssistModel | None = None
    track: TrackGeometry | None = None
    z_ground_m: float = 0.0
    end: str = "insertion"

    def __post_init__(self) -> None:
        if not self.guidance.kicks:
            raise ValueError("a gamma* search needs a kicking guidance (finite v_kick_mps)")
        if self.vehicle.n_stages != 2:
            raise ValueError("a planar search needs a two-stage vehicle")

    @classmethod
    def from_run(
        cls, run: RunConfig, vehicle: Vehicle, checks: ChecksConfig | None = None
    ) -> SearchContext:
        """The context of a validated planar_2d RunConfig and its Vehicle: mu/r^2
        gravity (MU_EARTH_M3S2), omega_p from the site, the ICAO atmosphere
        (``ambient_scalar``), the datum R_E, the assist and track built with the track's
        g_eff = g_ref, the IgnitionSpecs of the run's ignition block (through
        ``phases.prelude.resolve_stage_ignitions`` with that assist, track and g_ref, as
        ``sim.ignition_specs`` builds them), the kick guidance, the target orbit radius,
        the run's integrator settings and the shared budget (checks: the run's own
        ``planar.checks`` unless given)."""
        if run.planar is None or run.planar.target_orbit is None:
            raise ValueError("a planar search needs a planar_2d run with a target orbit")
        env = PlanarEnvironment(
            InverseSquareGravity(MU_EARTH_M3S2), run.site.omega_p_rads, ambient_scalar
        )
        assist, track = build_assist(run.assist, env.g_ref_mps2)
        ignition = resolve_stage_ignitions(run, vehicle, assist, track, env.g_ref_mps2)
        return cls(
            vehicle=vehicle,
            ignition=ignition,
            guidance=GuidanceSpec.from_config(run.planar.guidance),
            env=env,
            target=TargetOrbit(run.planar.target_orbit.radius_m),
            settings=IntegratorSettings.from_config(run.integrator),
            budget=SearchBudget.from_config(run.planar.search, checks or run.planar.checks),
            assist=assist,
            track=track,
            end=run.end,
        )

    @property
    def payload_kg(self) -> float:
        """P0 [kg]: the vehicle's own payload (the gamma* grid runs at it)."""
        return self.vehicle.payload_mass_kg

    def settings_for(self, mode: str, *, dense: bool = False) -> IntegratorSettings:
        """The integrator settings of an evaluation mode: rtol search_rtol and atol x
        final_atol_scale x search_atol_scale for grid and search, rtol final_rtol and atol x
        final_atol_scale for final; dense output as asked (off for evaluations, on for the
        recorded run)."""
        b = self.budget
        if mode == FINAL_MODE:
            rtol, scale = b.final_rtol, b.final_atol_scale
        elif mode in (GRID_MODE, SEARCH_MODE):
            rtol, scale = b.search_rtol, b.final_atol_scale * b.search_atol_scale
        else:
            raise ValueError(f"unknown mode {mode!r}")
        return dataclasses.replace(self.settings, rtol=rtol, atol_scale=scale, dense_output=dense)

    def planner(self, payload_kg: float, mode: str, *, dense: bool = False) -> PlanarPlanner:
        """The PlanarPlanner of the vehicle at payload_kg [kg] in mode."""
        return PlanarPlanner(
            with_payload(self.vehicle, payload_kg),
            self.ignition,
            self.guidance,
            self.env,
            self.end,
            self.settings_for(mode, dense=dense),
            z_ground_m=self.z_ground_m,
            target=self.target,
            ltg=self.budget.ltg_for(mode),
        )

    def _kick(self, planner: PlanarPlanner) -> KickPoint:
        """The prelude and the vertical rise of one payload (PreludeFailure when no
        flight follows or stage 1 does not light)."""
        start = planner.start(self.assist, self.track)
        if start.status != "nominal":
            raise PreludeFailure(start.status, f"the prelude ended with status {start.status}")
        if start.t_ign1_s is None:
            raise PreludeFailure("ignition", "stage 1's ignition fails")
        return planner.to_kick(start)

    def evaluate(
        self,
        payload_kg: float,
        gamma_star_rad: float,
        warm: WarmStore,
        mode: str,
        *,
        seed: WarmEntry | None = None,
    ) -> ResidualResult:
        """Rung 2 at (payload [kg], gamma* [rad]) in mode: the kick point of this payload
        (cached in warm per tolerance class), the delta solve for gamma* (warm from seed or
        the nearest gamma* in warm, cold when none), the LTG shooting from its hand-over
        (warm pair likewise; at most grid_max_rungs rungs in grid mode) with virtual
        propellant, and m_res and dv_margin of the accepted shot. The solved evaluation is
        added to warm. Raises GuidanceFailure or PreludeFailure, and ValueError when warm
        belongs to another problem (``WarmStore.claim``)."""
        warm.claim(self)
        planner = self.planner(payload_kg, mode)
        tol_class = FINAL_MODE if mode == FINAL_MODE else SEARCH_MODE
        kick = warm.kick_point((payload_kg, tol_class), lambda: self._kick(planner))
        near = seed if seed is not None else warm.nearest(gamma_star_rad)
        d_warm = None if near is None else near.delta_rad
        l_warm = None if near is None else near.ltg
        sol = solve_delta_for_gamma(
            lambda d: planner.from_kick(d, kick), gamma_star_rad, self.budget.delta, d_warm
        )
        lt = planner.solve_stage2(sol.handover, warm=l_warm)
        warm.add(WarmEntry(gamma_star_rad, payload_kg, sol.delta_rad, (lt.a, lt.b_per_s)))
        return ResidualResult(
            payload_kg=payload_kg,
            gamma_star_rad=gamma_star_rad,
            m_res_kg=lt.shot.m_res_kg,
            dv_margin_mps=lt.shot.dv_margin_mps,
            delta_rad=sol.delta_rad,
            ltg=(lt.a, lt.b_per_s),
            gamma_meco_rad=sol.gamma_meco_rad,
            rung=lt.rung,
            flights=sol.flights,
            shots=lt.shots,
            mode=mode,
            shot=lt.shot,
        )

    def record(self, res: ResidualResult) -> RecordedRun:
        """Re-fly the evaluation res as the recorded run: the planner at res's payload with
        final settings and dense output on, ``PlanarPlanner.run`` at res's delta and LTG
        pair (the real stage-2 depletion event, no mass floor). When it reaches the energy
        cutoff (status inserted or off_target), m_res = m_end - m_empty [kg] with m_empty
        from the evaluation's shot (m_d2 + P, plus a fairing still on) and dv_margin =
        c2 ln(m_end / m_empty) [m/s], measured at its cutoff. When it does not (the real
        propellant runs out first: short_of_orbit), the signed m_res and dv_margin of
        res (negative) are carried instead, with cut_state_rel_diff NaN."""
        if res.shot is None or res.ltg is None:
            raise ValueError("record needs an evaluation with a stage-2 shot")
        trace = self.planner(res.payload_kg, FINAL_MODE, dense=True).run(
            res.delta_rad, self.assist, self.track, ltg=res.ltg
        )
        end = trace.burnouts.get(self.vehicle.stages[1].name)
        if end is None or trace.status not in (INSERTED_STATUS, OFF_TARGET_STATUS):
            return RecordedRun(
                trace,
                trace.status,
                res.m_res_kg,
                res.dv_margin_mps,
                math.nan,
                FROM_FINAL_EVALUATION,
            )
        y_end = end[1]
        m_end = float(PLANAR_LAYOUT.get(y_end, "m_kg"))
        m_empty = res.shot.m_empty_kg
        y_ref = res.shot.y_cut
        scale = np.maximum(np.abs(y_ref), CUT_STATE_SCALE_FLOOR)
        diff = float(np.max(np.abs(y_end - y_ref) / scale))
        return RecordedRun(
            trace=trace,
            status=trace.status,
            m_res_kg=m_end - m_empty,
            dv_margin_mps=res.shot.c_mps * math.log(m_end / m_empty),
            cut_state_rel_diff=diff,
            figures_from=FROM_RECORDED_RUN,
        )

    def tightened(self, conv: ConvergenceConfig) -> SearchContext:
        """The context with the budget tightened by conv.tighten_factor
        (``SearchBudget.tightened``) and the max_step caps multiplied by
        conv.max_step_factor (ramp, lag and push step counts divided by it, rounded up;
        the planar flight-phase cap planar_max_step_s multiplied by it): the
        convergence check of amendment 3."""
        s = self.settings

        def steps(n: int) -> int:
            return math.ceil(n / conv.max_step_factor)

        settings = dataclasses.replace(
            s,
            ramp_steps=steps(s.ramp_steps),
            lag_steps_per_tau=steps(s.lag_steps_per_tau),
            push_steps=steps(s.push_steps),
            planar_max_step_s=s.planar_max_step_s * conv.max_step_factor,
        )
        return dataclasses.replace(
            self, settings=settings, budget=self.budget.tightened(conv.tighten_factor)
        )


def residual(
    problem: SearchProblem,
    payload_kg: float,
    gamma_star_rad: float,
    warm: WarmStore,
    mode: str = SEARCH_MODE,
) -> ResidualResult:
    """Rung 2: m_res and dv_margin at (payload [kg], gamma* [rad]) with the inner delta
    solve and the LTG shooting (``problem.evaluate``), warm-started from warm. Raises one
    of INFEASIBLE."""
    if mode not in EVAL_MODES:
        raise ValueError(f"mode must be one of {EVAL_MODES}, got {mode!r}")
    return problem.evaluate(payload_kg, gamma_star_rad, warm, mode)


# ------------------------------------------------------------------- payload capacity


@dataclass(frozen=True)
class PayloadEval:
    """One logged evaluation of a payload search: payload [kg], m_res [kg] and dv_margin
    [m/s] (NaN when it failed) and the failure (``kind: message``; None when it flew)."""

    payload_kg: float
    m_res_kg: float
    dv_margin_mps: float
    failure: str | None

    @property
    def ok(self) -> bool:
        """True when the evaluation flew."""
        return self.failure is None


@dataclass(frozen=True, eq=False)
class PayloadResult:
    """Rung 3 at one gamma* [rad]: payload_kg, the largest evaluated payload with
    m_res >= 0 [kg] (P_lo; 0 for no_orbit), root_kg the brentq root [kg] (NaN for
    no_orbit), status (ok or no_orbit), dv_shortfall_mps = -dv_margin(0) [m/s] for
    no_orbit (NaN otherwise), the bracket (low, high) [kg] brentq was handed (NaN for
    no_orbit), the half-width expansions and the backoffs used, the mode, every logged
    evaluation in order, and ``at_payload``, the evaluation at payload_kg (the guidance
    that flies it)."""

    gamma_star_rad: float
    payload_kg: float
    root_kg: float
    status: str
    dv_shortfall_mps: float
    bracket_kg: tuple[float, float]
    expansions: int
    backoffs: int
    mode: str
    evals: tuple[PayloadEval, ...]
    at_payload: ResidualResult


class _PayloadLog:
    """The logging wrapper around the payload evaluations of one payload search: every
    call is logged (brentq returns only a root, not its bracket), results are kept by
    payload, and ``best_feasible`` gives P_lo, the largest payload with m_res >= 0."""

    def __init__(self, fn: Callable[[float], ResidualResult]) -> None:
        self.fn = fn
        self.evals: list[PayloadEval] = []
        self.results: dict[float, ResidualResult] = {}

    def __call__(self, payload_kg: float) -> ResidualResult:
        p = float(payload_kg)
        hit = self.results.get(p)
        if hit is not None:
            return hit
        try:
            res = self.fn(p)
        except INFEASIBLE as exc:
            self.evals.append(PayloadEval(p, math.nan, math.nan, str(exc)))
            raise
        self.evals.append(PayloadEval(p, res.m_res_kg, res.dv_margin_mps, None))
        self.results[p] = res
        return res

    def m_res(self, payload_kg: float) -> float:
        """m_res [kg] at payload_kg (brentq's function)."""
        return self(payload_kg).m_res_kg

    def best_feasible(self) -> ResidualResult | None:
        """The logged evaluation with the largest payload whose m_res >= 0."""
        good = [r for p, r in self.results.items() if r.m_res_kg >= 0.0]
        return max(good, key=lambda r: r.payload_kg) if good else None


def payload_root(
    fn: Callable[[float], ResidualResult],
    hint_kg: float,
    halves_kg: Sequence[float],
    *,
    backoff_max: int,
    xtol_kg: float | Callable[[ResidualResult, ResidualResult], float],
    rtol: float,
    gamma_star_rad: float = math.nan,
    mode: str = SEARCH_MODE,
    low_toward_hint: bool = False,
) -> PayloadResult:
    """The payload P* [kg] at which m_res(P) = fn(P).m_res_kg crosses zero (fn decreasing
    in P, continuous under virtual propellant), with the P = 0 floor.

    Bracket: low = max(0, hint - h), high = hint + h with h = halves_kg[k] (k = 0, then
    one more for each expansion). The low end must fly with m_res >= 0: a negative one
    becomes the high end and the low end expands downward (k + 1; never above the
    lightest negative payload minus halves_kg[0]) until m_res >= 0, and m_res(0) < 0 is
    ``no_orbit`` (P* = 0, shortfall -dv_margin(0)). The high end must fly with m_res < 0:
    a non-negative one becomes the new low end and the high end expands (k + 1). An end
    that raises one of INFEASIBLE backs off, at most backoff_max times in all: the low
    end halfway toward the nearest payload above it that flew, or, when none flew, halfway
    toward 0 (a lighter vehicle is the likelier to fly; toward the hint only from P = 0),
    or halfway toward the hint when low_toward_hint (the final verification, whose hint
    is a payload that flew at search tolerance); the high end is never probed again at
    or above a payload that failed, so after a failure it moves halfway between the low
    end and the lowest failure. Out of expansions or backoffs: SearchFailed('bracket').
    Then brentq (xtol, rtol) through
    the logging wrapper, with xtol = xtol_kg [kg], or xtol_kg(low, high) when it is a
    callable of the two bracket evaluations; an infeasible evaluation inside the bracket
    raises SearchFailed('root').
    Output: the PayloadResult with payload_kg = P_lo, the largest logged payload with
    m_res >= 0."""
    if not hint_kg >= 0.0:
        raise ValueError(f"hint_kg must be >= 0, got {hint_kg!r}")
    log = _PayloadLog(fn)
    k = 0
    backoffs = 0

    def probe(p: float) -> ResidualResult | None:
        try:
            return log(p)
        except INFEASIBLE:
            return None

    def back_off(p: float, toward: float, end: str) -> float:
        nonlocal backoffs
        if toward == p or backoffs >= backoff_max:
            raise SearchFailed(
                "bracket",
                f"the {end} payload end {p:.6g} kg cannot fly and no backoff is left "
                f"({backoffs} of {backoff_max} used): " + _last_failure(log),
            )
        backoffs += 1
        return 0.5 * (p + toward)

    def expand(end: str) -> None:
        nonlocal k
        if k + 1 >= len(halves_kg):
            raise SearchFailed(
                "bracket",
                f"no sign change of m_res within {halves_kg[-1]:.6g} kg of {hint_kg:.6g} kg "
                f"(the {end} end; {len(halves_kg) - 1} expansions used)",
            )
        k += 1

    # low end: flies with m_res >= 0, or P = 0 with m_res < 0 (no_orbit)
    p = max(0.0, hint_kg - halves_kg[0])
    high: ResidualResult | None = None
    while True:
        res = probe(p)
        if res is None:
            above = [q for q in log.results if q > p]
            if above:
                toward = min(above)
            elif low_toward_hint or p == 0.0:
                toward = hint_kg
            else:
                toward = 0.0
            p = back_off(p, toward, "low")
            continue
        if res.m_res_kg >= 0.0:
            low = res
            break
        if high is None or res.payload_kg < high.payload_kg:
            high = res
        if p == 0.0:
            return PayloadResult(
                gamma_star_rad,
                0.0,
                math.nan,
                NO_ORBIT_STATUS,
                -res.dv_margin_mps,
                (math.nan, math.nan),
                k,
                backoffs,
                mode,
                tuple(log.evals),
                res,
            )
        expand("low")
        p = max(0.0, min(hint_kg - halves_kg[k], high.payload_kg - halves_kg[0]))
    # high end: flies with m_res < 0; never probed again at or above a payload that failed
    if high is None:
        ceiling = math.inf
        p = max(hint_kg + halves_kg[k], low.payload_kg + halves_kg[0])
        while True:
            res = probe(p)
            if res is None:
                ceiling = min(ceiling, p)
                p = back_off(ceiling, low.payload_kg, "high")
                continue
            if res.m_res_kg < 0.0:
                high = res
                break
            low = res
            if math.isfinite(ceiling):
                p = back_off(ceiling, low.payload_kg, "high")
                continue
            expand("high")
            p = max(hint_kg + halves_kg[k], low.payload_kg + halves_kg[0])
    bracket = (low.payload_kg, high.payload_kg)
    xtol = xtol_kg(low, high) if callable(xtol_kg) else xtol_kg
    try:
        root = float(brentq(log.m_res, bracket[0], bracket[1], xtol=xtol, rtol=rtol))
    except INFEASIBLE as exc:
        raise SearchFailed(
            "root", f"an evaluation inside the payload bracket {bracket} kg failed: {exc}"
        ) from exc
    best = log.best_feasible()
    assert best is not None  # the low end flew with m_res >= 0
    return PayloadResult(
        gamma_star_rad,
        best.payload_kg,
        root,
        OK_STATUS,
        math.nan,
        bracket,
        k,
        backoffs,
        mode,
        tuple(log.evals),
        best,
    )


def _last_failure(log: _PayloadLog) -> str:
    """The last logged failure of a payload search (for SearchFailed messages)."""
    failed = [e.failure for e in log.evals if e.failure is not None]
    return failed[-1] if failed else "no evaluation failed"


def backoff_flags(name: str, payload: PayloadResult) -> tuple[str, ...]:
    """The flag of a payload search (name: P1, P2 or final) that backed off from failed
    evaluations: the backoff count, the failed payloads [kg] and their failure kinds (an
    evaluation that fails near P* is reported, not only counted); () without backoffs."""
    failed = [e for e in payload.evals if e.failure is not None]
    if payload.backoffs == 0 and not failed:
        return ()
    kinds = sorted({e.failure.split(":", 1)[0] for e in failed if e.failure is not None})
    where = ", ".join(f"{e.payload_kg:.6g}" for e in failed)
    return (
        f"{name}_backoff: the {name} payload search backed off {payload.backoffs} time(s) "
        f"from evaluations that failed at P = {where} kg ({', '.join(kinds)})",
    )


def payload_capacity(
    problem: SearchProblem,
    gamma_star_rad: float,
    hint_kg: float,
    warm: WarmStore,
    mode: str = SEARCH_MODE,
) -> PayloadResult:
    """Rung 3 at gamma* [rad]: ``payload_root`` of m_res(P; gamma*) = ``problem.evaluate``
    in mode (search as shipped) from hint_kg [kg] (the vehicle payload for the first
    call of a run, then its P1), with the budget's payload half-widths, backoffs, xtol
    and brentq rtol. Each evaluation warm-starts from the last solved one at the nearest
    gamma* (in practice this gamma* at the previous payload)."""
    b = problem.budget

    def fn(p: float) -> ResidualResult:
        return problem.evaluate(p, gamma_star_rad, warm, mode)

    return payload_root(
        fn,
        hint_kg,
        b.payload_halves_kg,
        backoff_max=b.payload_backoff_max,
        xtol_kg=b.payload_xtol_kg,
        rtol=b.brentq_rtol,
        gamma_star_rad=gamma_star_rad,
        mode=mode,
    )


# -------------------------------------------------------------------- gamma* sweep


@dataclass(frozen=True)
class GridPoint:
    """One point of the gamma* grid (plain data, picklable): gamma* [rad]; label
    (feasible, infeasible, or not_direct_root: infeasible by the direct-root rule);
    m_res_kg [kg] and dv_margin_mps [m/s] (NaN unless feasible); objective_kg [kg]
    (m_res, or the penalty); delta_rad [rad], ltg_a and ltg_b_per_s [1/s] (NaN unless
    feasible); rung, the LTG rung that converged ('' unless feasible); retried, whether
    it was retried from a converged neighbour after its first attempt failed; failure,
    the last failure (``kind: message``; None when it flew first time)."""

    gamma_star_rad: float
    label: str
    m_res_kg: float
    dv_margin_mps: float
    objective_kg: float
    delta_rad: float
    ltg_a: float
    ltg_b_per_s: float
    rung: str
    retried: bool
    failure: str | None


@dataclass(frozen=True)
class RefineRecord:
    """The bounded Brent refine: the window(s) (low, high) [rad] searched (two when the
    window was shifted), the evaluations (gamma* [rad], objective [kg], label) in order,
    the result gamma* [rad] and objective [kg] (m_res at the refine payload; NaN when
    the refine fell back to the best grid point), the function evaluations, whether
    scipy reported success, and whether the window was shifted once."""

    windows: tuple[tuple[float, float], ...]
    evals: tuple[tuple[float, float, str], ...]
    gamma_star_rad: float
    objective_kg: float
    nfev: int
    converged: bool
    shifted: bool


@dataclass(frozen=True, eq=False)
class GammaResult:
    """The shared gamma* sweep of one run: gamma_star_rad [rad] (the refined gamma*_ref),
    gamma_best_grid_rad [rad], the payload the grid ran at [kg] (P0, or 0 when no grid
    point flew at P0 and the grid was re-run there, flagged) and the payload the refine
    ran at [kg] (P1, or P0 for figure_of_merit residual), p1 and p2 (the payload
    searches at the best grid point and at gamma*_ref; None for residual), the grid table,
    the refine record, the refine's final evaluation, and flags."""

    gamma_star_rad: float
    gamma_best_grid_rad: float
    grid_payload_kg: float
    refine_payload_kg: float
    p1: PayloadResult | None
    p2: PayloadResult | None
    grid: tuple[GridPoint, ...]
    refine: RefineRecord
    flags: tuple[str, ...]

    @property
    def p2_minus_p1_kg(self) -> float:
        """P2 - P1 [kg] (NaN without payload searches)."""
        if self.p1 is None or self.p2 is None:
            return math.nan
        return self.p2.payload_kg - self.p1.payload_kg


def centre_out_order(n: int) -> tuple[int, ...]:
    """Grid indices from the midpoint outward, the upper side first on each ring
    (n = 15: 7, 8, 6, 9, 5, ..., 14, 0): each point after the first has an evaluated
    neighbour closer to the centre."""
    mid = (n - 1) // 2
    order = [mid]
    for step in range(1, n):
        for i in (mid + step, mid - step):
            if 0 <= i < n:
                order.append(i)
    return tuple(order)


def is_rule_infeasible(exc: Exception) -> bool:
    """Whether an evaluation failure is an LTG ladder that converged only to roots the
    direct-root rule rejects: GuidanceFailure 'not_direct_root', or 'nonconverged' whose
    rung outcomes name at least one not_direct_root."""
    if not isinstance(exc, GuidanceFailure):
        return False
    return exc.kind == "not_direct_root" or (
        exc.kind == "nonconverged" and NOT_DIRECT_ROOT_PATTERN.search(exc.message) is not None
    )


def _retryable(exc: Exception) -> bool:
    """Whether a failed grid point is worth a retry from a neighbour (RETRY_KINDS)."""
    return isinstance(exc, GuidanceFailure) and exc.kind in RETRY_KINDS


def _failure_text(exc: Exception) -> str:
    """``kind: message`` of an infeasibility."""
    return str(exc)


def penalty_kg(gamma_rad: float, feasible_rad: Sequence[float], budget: SearchBudget) -> float:
    """The objective [kg] of an infeasible gamma* [rad]: -(penalty_base + penalty_per_rad x
    the distance to the nearest feasible grid point), finite and decreasing with that
    distance (-penalty_base when there is none, only in a message)."""
    d = min((abs(gamma_rad - g) for g in feasible_rad), default=0.0)
    return -(budget.penalty_base_kg + budget.penalty_per_rad_kg * d)


def _evaluate_grid(
    problem: SearchProblem, payload_kg: float, warm: WarmStore
) -> tuple[GridPoint, ...]:
    """The gamma* grid at payload_kg [kg]: centre-out, each point warm-started from its
    nearest solved neighbour (the store's nearest gamma*); then, in the same order, every
    point that failed with a RETRY_KINDS failure is retried from each adjacent converged
    grid point whose solution it did not start from, pass after pass until a pass solves
    no new point (a point whose neighbours converge only in a retry gets its turn;
    bounded, since each neighbour seeds a point once); penalties at the end."""
    b = problem.budget
    grid = b.gamma_grid_rad
    order = centre_out_order(len(grid))
    solved: dict[int, ResidualResult] = {}
    failed: dict[int, Exception] = {}
    seeds_used: dict[int, set[int]] = {}
    for i in order:
        near = warm.nearest(grid[i])
        seeds_used[i] = {j for j in solved if near is not None and grid[j] == near.gamma_star_rad}
        try:
            solved[i] = problem.evaluate(payload_kg, grid[i], warm, GRID_MODE)
        except INFEASIBLE as exc:
            failed[i] = exc
    retried: set[int] = set()
    progress = True
    while progress:  # until a pass solves no new point (each seed is tried once: bounded)
        progress = False
        for i in order:
            if i not in failed or not _retryable(failed[i]):
                continue
            for j in (i - 1, i + 1):
                if j not in solved or j in seeds_used[i]:
                    continue
                nb = solved[j]
                seed = WarmEntry(nb.gamma_star_rad, nb.payload_kg, nb.delta_rad, nb.ltg)
                seeds_used[i].add(j)
                retried.add(i)
                try:
                    solved[i] = problem.evaluate(payload_kg, grid[i], warm, GRID_MODE, seed=seed)
                except INFEASIBLE as exc:
                    failed[i] = exc
                    continue
                del failed[i]
                progress = True
                break
    feasible = [grid[i] for i in solved]
    if not feasible:
        points = tuple(
            _grid_point(grid[i], None, failed[i], math.nan, i in retried) for i in range(len(grid))
        )
        raise SearchFailed(
            "grid",
            f"no gamma* grid point flies at P = {payload_kg:.6g} kg (first failure: "
            f"{_failure_text(failed[order[0]])})",
            points,
        )
    return tuple(
        _grid_point(
            grid[i],
            solved.get(i),
            failed.get(i),
            penalty_kg(grid[i], feasible, b),
            i in retried,
        )
        for i in range(len(grid))
    )


def _grid_point(
    gamma_rad: float,
    res: ResidualResult | None,
    exc: Exception | None,
    penalty: float,
    retried: bool,
) -> GridPoint:
    """The GridPoint of one grid evaluation (res when it flew, else its failure exc)."""
    if res is not None:
        a, b = res.ltg if res.ltg is not None else (math.nan, math.nan)
        return GridPoint(
            gamma_rad,
            FEASIBLE_POINT,
            res.m_res_kg,
            res.dv_margin_mps,
            res.m_res_kg,
            math.nan if res.delta_rad is None else res.delta_rad,
            a,
            b,
            res.rung,
            retried,
            None,
        )
    assert exc is not None
    label = RULE_INFEASIBLE_POINT if is_rule_infeasible(exc) else INFEASIBLE_POINT
    return GridPoint(
        gamma_rad,
        label,
        math.nan,
        math.nan,
        penalty,
        math.nan,
        math.nan,
        math.nan,
        "",
        retried,
        _failure_text(exc),
    )


def _refine(
    problem: SearchProblem,
    payload_kg: float,
    best: GridPoint,
    grid: tuple[GridPoint, ...],
    warm: WarmStore,
) -> tuple[RefineRecord, list[str]]:
    """Bounded Brent on -m_res(gamma*; payload_kg) over best +/- refine_halfwidth,
    clipped to the grid (xatol gamma_xatol, at most refine_maxiter evaluations); an
    infeasible evaluation scores its penalty (distance to the nearest feasible grid
    point). A result within xatol of an interior window edge shifts the window once
    (centred on it, clipped) and is flagged with both results; a result again within
    xatol of an interior edge of the shifted window is flagged ``refine_capped`` (the
    window, not the physics, may cap it). A result that is not a feasible evaluation
    (every evaluation failed) falls back to the best grid point, flagged, with the
    record's objective NaN (no m_res at payload_kg there). Returns the record and the
    flags."""
    b = problem.budget
    g_lo, g_hi = b.gamma_grid_rad[0], b.gamma_grid_rad[-1]
    feasible = [p.gamma_star_rad for p in grid if p.label == FEASIBLE_POINT]
    evals: list[tuple[float, float, str]] = []
    flags: list[str] = []

    def objective(g: float) -> float:
        g = float(g)
        try:
            res = problem.evaluate(payload_kg, g, warm, SEARCH_MODE)
        except INFEASIBLE as exc:
            label = RULE_INFEASIBLE_POINT if is_rule_infeasible(exc) else INFEASIBLE_POINT
            value = penalty_kg(g, feasible, b)
            evals.append((g, value, label))
            if label == RULE_INFEASIBLE_POINT:
                flags.append(
                    f"refine: gamma* = {g:.9g} rad is infeasible only by the direct-root rule"
                )
            return -value
        evals.append((g, res.m_res_kg, FEASIBLE_POINT))
        return -res.m_res_kg

    def window(centre: float) -> tuple[float, float]:
        return (
            max(g_lo, centre - b.refine_halfwidth_rad),
            min(g_hi, centre + b.refine_halfwidth_rad),
        )

    def brent(win: tuple[float, float]) -> Any:
        if win[1] - win[0] <= b.gamma_xatol_rad:
            x = 0.5 * (win[0] + win[1])
            return _Minimum(x, objective(x), 1, True)
        return minimize_scalar(
            objective,
            bounds=win,
            method="bounded",
            options={"xatol": b.gamma_xatol_rad, "maxiter": b.refine_maxiter},
        )

    def at_edge(g: float, win: tuple[float, float]) -> bool:
        lo, hi = win
        return (g - lo <= b.gamma_xatol_rad and lo > g_lo) or (
            hi - g <= b.gamma_xatol_rad and hi < g_hi
        )

    windows = [window(best.gamma_star_rad)]
    res = brent(windows[0])
    nfev, success = int(res.nfev), bool(res.success)
    x, fx = float(res.x), float(res.fun)
    shifted = False
    if at_edge(x, windows[0]):
        shifted = True
        x1 = x
        windows.append(window(x1))
        res2 = brent(windows[1])
        nfev += int(res2.nfev)
        success = bool(res2.success)
        x2 = float(res2.x)
        if float(res2.fun) <= fx:
            x, fx = x2, float(res2.fun)
        flags.append(
            f"refine: the first optimum {x1:.9g} rad ended within gamma_xatol of an interior "
            f"edge of [{windows[0][0]:.9g}, {windows[0][1]:.9g}] rad; the window was shifted "
            f"once to [{windows[1][0]:.9g}, {windows[1][1]:.9g}] rad, where the search ended "
            f"at {x2:.9g} rad"
        )
        if at_edge(x, windows[1]):
            flags.append(
                f"refine_capped: gamma*_ref {x:.9g} rad is again within gamma_xatol of an "
                "interior edge of the shifted window: the optimum at "
                f"P = {payload_kg:.6g} kg may lie beyond it (capped by the refine window, "
                "not by the physics; the grid payload and this one differ)"
            )
    if not success:
        flags.append(f"refine: bounded Brent stopped at maxiter ({b.refine_maxiter}) evaluations")
    if not any(g == x and label == FEASIBLE_POINT for g, _v, label in evals):
        flags.append(
            f"refine: no feasible evaluation beat the penalties; gamma*_ref falls back to the "
            f"best grid point {best.gamma_star_rad:.9g} rad (the refine objective is NaN: "
            f"that point's m_res is known only at the grid payload, not at "
            f"{payload_kg:.6g} kg)"
        )
        x, fx = best.gamma_star_rad, math.nan
    record = RefineRecord(tuple(windows), tuple(evals), x, -fx, nfev, success, shifted)
    return record, flags


@dataclass(frozen=True)
class _Minimum:
    """A degenerate refine window's result, in the fields scipy's OptimizeResult has."""

    x: float
    fun: float
    nfev: int
    success: bool


def optimise_gamma(
    problem: SearchProblem, warm: WarmStore, payload_kg: float, *, find_payload: bool = True
) -> GammaResult:
    """The shared gamma* sweep of one run (plan section 6), deterministic.

    1. The grid at payload_kg [kg] (P0, the vehicle payload), objective m_res, evaluated
       centre-out with warm starts from the nearest solved neighbour; nonconverged points
       retried from each adjacent converged point, in passes until a pass solves no new
       point; infeasible points score the penalty
       (``penalty_kg``), and points infeasible only by the direct-root rule are labelled
       not_direct_root. No feasible point: for a payload search (find_payload) with P0 >
       0 the grid is run once more at P = 0 (flagged; a vehicle too heavy at P0 is
       reported as no_orbit or as its small P*, not NaN), else, or when that fails too,
       SearchFailed('grid').
    2. The best grid point on a grid bound: SearchFailed('edge') (widen the shared grid
       for every run).
    3. P1 = payload_capacity(gamma_best, hint = the grid payload) (find_payload; else the
       refine runs at P0, figure_of_merit residual).
    4. Bounded Brent on -m_res(gamma*; P1) over gamma_best +/- refine_halfwidth, clipped to
       the grid (``_refine``), giving gamma*_ref. A gamma*_ref within gamma_xatol of a
       grid bound (the optimum at P1 lies at or beyond the shared grid) is
       SearchFailed('edge') too.
    5. P2 = payload_capacity(gamma*_ref, hint P1).

    Every SearchFailed raised after the grid carries the grid table. Flags: the grid
    re-run at P = 0, points solved only after a retry from a neighbour, rule-infeasible
    points in the refine window, backoffs of P1 and P2 (``backoff_flags``), the window
    shift, a result capped by the shifted window (refine_capped) and a refine that hit
    maxiter.
    """
    flags: list[str] = []
    grid_payload = payload_kg
    try:
        grid = _evaluate_grid(problem, payload_kg, warm)
    except SearchFailed as exc:
        if not (find_payload and exc.kind == "grid" and payload_kg > 0.0):
            raise
        grid_payload = 0.0
        flags.append(
            f"grid: no gamma* grid point flies at P0 = {payload_kg:.6g} kg; the grid was "
            f"re-run at P = 0 ({exc.message})"
        )
        try:
            grid = _evaluate_grid(problem, grid_payload, warm)
        except SearchFailed as exc0:
            raise SearchFailed(
                "grid",
                f"at P0 = {payload_kg:.6g} kg: {exc.message}; at P = 0: {exc0.message}",
                exc0.grid,
            ) from exc0
    try:
        return _sweep_after_grid(problem, warm, grid_payload, grid, find_payload, flags)
    except SearchFailed as exc:
        if exc.grid:
            raise
        raise SearchFailed(exc.kind, exc.message, grid) from exc


def _sweep_after_grid(
    problem: SearchProblem,
    warm: WarmStore,
    grid_payload: float,
    grid: tuple[GridPoint, ...],
    find_payload: bool,
    flags: list[str],
) -> GammaResult:
    """Steps 2 to 5 of ``optimise_gamma`` on the evaluated grid (at grid_payload [kg]);
    flags gathered so far are extended."""
    b = problem.budget
    best_i = max(range(len(grid)), key=lambda i: (grid[i].objective_kg, -i))
    best = grid[best_i]
    if best_i in (0, len(grid) - 1):
        raise SearchFailed(
            "edge",
            f"the best gamma* grid point {best.gamma_star_rad:.9g} rad lies on a grid bound "
            "(widen the shared gamma* grid for every run)",
            grid,
        )
    retried = [p for p in grid if p.retried and p.label == FEASIBLE_POINT]
    if retried:
        flags.append(
            "grid: solved only after a warm retry from a converged neighbour at gamma* = "
            + ", ".join(f"{p.gamma_star_rad:.9g}" for p in retried)
            + " rad"
        )
    hw = b.refine_halfwidth_rad
    touching = [
        p
        for p in grid
        if p.label == RULE_INFEASIBLE_POINT and abs(p.gamma_star_rad - best.gamma_star_rad) <= hw
    ]
    if touching:
        flags.append(
            "grid: the refine window touches points infeasible only by the direct-root rule "
            "at gamma* = " + ", ".join(f"{p.gamma_star_rad:.9g}" for p in touching) + " rad"
        )
    p1 = None
    refine_payload = grid_payload
    if find_payload:
        p1 = payload_capacity(problem, best.gamma_star_rad, grid_payload, warm)
        flags += backoff_flags("P1", p1)
        refine_payload = p1.payload_kg
    refine, refine_flags = _refine(problem, refine_payload, best, grid, warm)
    flags += refine_flags
    g_lo, g_hi = b.gamma_grid_rad[0], b.gamma_grid_rad[-1]
    g_ref = refine.gamma_star_rad
    if g_ref - g_lo <= b.gamma_xatol_rad or g_hi - g_ref <= b.gamma_xatol_rad:
        raise SearchFailed(
            "edge",
            f"the refined gamma*_ref {g_ref:.9g} rad at P = {refine_payload:.6g} kg lies "
            "within gamma_xatol of a grid bound (widen the shared gamma* grid for every run)",
            grid,
        )
    p2 = None
    if find_payload:
        assert p1 is not None
        p2 = payload_capacity(problem, g_ref, p1.payload_kg, warm)
        flags += backoff_flags("P2", p2)
    return GammaResult(
        gamma_star_rad=g_ref,
        gamma_best_grid_rad=best.gamma_star_rad,
        grid_payload_kg=grid_payload,
        refine_payload_kg=refine_payload,
        p1=p1,
        p2=p2,
        grid=grid,
        refine=refine,
        flags=tuple(flags),
    )


# ---------------------------------------------------------------- final verification


@dataclass(frozen=True, eq=False)
class FinalResult:
    """The final verification of one run: gamma_star_rad [rad]; payload (the final-mode
    PayloadResult; None for figure_of_merit residual, which verifies at P0);
    at_final, the final-mode evaluation the recorded run re-flies (its m_res_kg and
    dv_margin_mps are the signed final-tolerance figures at the final payload); recorded,
    that run (``RecordedRun.figures_from`` says whether its figures were measured at its
    cutoff or carried from at_final); search_vs_final_payload_kg [kg] (P_search -
    P_final; NaN for residual); flags."""

    gamma_star_rad: float
    payload: PayloadResult | None
    at_final: ResidualResult
    recorded: RecordedRun
    search_vs_final_payload_kg: float
    flags: tuple[str, ...]

    @property
    def payload_kg(self) -> float:
        """The final payload [kg] (P_final; the evaluated payload for residual)."""
        return self.at_final.payload_kg


def _check_recorded(rec: RecordedRun, at_final: ResidualResult, xtol_kg: float) -> None:
    """SearchFailed('final_run') unless the recorded run agrees with the final evaluation
    at_final it re-flies: with m_res >= 0 it must end inserted with 0 <= m_res < xtol_kg
    [kg] (math.inf when no upper limit applies: figure_of_merit residual); with m_res < 0
    (no_orbit at P = 0, or a residual run above capacity) it must not reach the energy
    cutoff (its real propellant runs out first) and carries the evaluation's signed
    figures."""
    if at_final.m_res_kg >= 0.0:
        if rec.status != INSERTED_STATUS or not 0.0 <= rec.m_res_kg < xtol_kg:
            raise SearchFailed(
                "final_run",
                f"the recorded run at {at_final.payload_kg:.6g} kg ended {rec.status!r} with "
                f"m_res = {rec.m_res_kg:.6g} kg (needs inserted and 0 <= m_res < {xtol_kg:g} "
                "kg)",
            )
    elif rec.figures_from != FROM_FINAL_EVALUATION:
        raise SearchFailed(
            "final_run",
            f"the recorded run at {at_final.payload_kg:.6g} kg ended {rec.status!r} at the "
            f"energy cutoff although its evaluation needs virtual propellant (m_res = "
            f"{at_final.m_res_kg:.6g} kg)",
        )


def _final_xtol(xtol_kg: float) -> Callable[[ResidualResult, ResidualResult], float]:
    """brentq's payload xtol [kg] of the final verification from its bracket ends:
    min(xtol_kg, xtol_kg / |slope|) with |slope| = (m_res(low) - m_res(high)) / (P_high -
    P_low) > 0 [kg/kg], so the bracket brentq leaves spans about xtol_kg of m_res at
    most (``_bisect_to_residual`` covers a local slope above the secant)."""

    def xtol(low: ResidualResult, high: ResidualResult) -> float:
        slope = abs((low.m_res_kg - high.m_res_kg) / (high.payload_kg - low.payload_kg))
        return min(xtol_kg, xtol_kg / slope)

    return xtol


def _bisect_to_residual(
    fn: Callable[[float], ResidualResult], payload: PayloadResult, xtol_kg: float
) -> tuple[PayloadResult, int]:
    """Bisect the logged final bracket until m_res(P_lo) < xtol_kg [kg]: between P_lo
    (m_res >= 0) and the lightest logged payload with m_res < 0, until the midpoint no
    longer differs from an end in floating point. A local slope above the bracket's
    secant (curvature, noise) can leave brentq's P_lo with m_res >= xtol_kg; this keeps
    the recorded run's 0 <= m_res < xtol_kg rule without a hard failure. Returns the
    updated PayloadResult (P_lo, at_payload, evals) and the bisections flown. An
    infeasible midpoint raises SearchFailed('root')."""
    best = payload.at_payload
    if best.m_res_kg < xtol_kg:
        return payload, 0
    hi = min(e.payload_kg for e in payload.evals if e.ok and e.m_res_kg < 0.0)
    lo = best.payload_kg
    evals = list(payload.evals)
    n = 0
    while best.m_res_kg >= xtol_kg:
        mid = 0.5 * (lo + hi)
        if not lo < mid < hi:
            break
        try:
            res = fn(mid)
        except INFEASIBLE as exc:
            raise SearchFailed(
                "root", f"final verification: the bisection at {mid:.9g} kg failed: {exc}"
            ) from exc
        n += 1
        evals.append(PayloadEval(mid, res.m_res_kg, res.dv_margin_mps, None))
        if res.m_res_kg >= 0.0:
            lo, best = mid, res
        else:
            hi = mid
    updated = dataclasses.replace(
        payload, payload_kg=best.payload_kg, evals=tuple(evals), at_payload=best
    )
    return updated, n


def final_verify(
    problem: RecordingProblem, gamma_star_rad: float, p_lo_kg: float, warm: WarmStore
) -> FinalResult:
    """The final verification at gamma* [rad] (plan section 6): ``payload_root`` of
    m_res(P) in final mode (final tolerance, delta re-solved at it, fd_step_final),
    bracket p_lo_kg +/- final_halves_kg[0] expanding x2 up to the last half-width
    (expansion flags ``search_final_mismatch`` and the final value is used; no bracket:
    SearchFailed('final_bracket')); a failing low end with nothing lighter flown backs
    off halfway toward p_lo_kg (it flew at search tolerance), and every backoff is
    flagged with its failures (``backoff_flags``); brentq to xtol = min(final_payload_xtol_kg,
    final_payload_xtol_kg / |slope|) [kg] with |slope| the bracket's secant slope
    |d m_res / d P| (so that P_final = the largest P with m_res >= 0 keeps m_res <
    final_payload_xtol_kg); should m_res(P_final) still be >= final_payload_xtol_kg (a
    local slope above the secant), the logged bracket is bisected until it is not
    (flagged). Then the recorded run at P_final re-flying that evaluation: it must end
    inserted with 0 <= m_res < final_payload_xtol_kg (no_orbit: short of the cutoff,
    with the signed figures), else SearchFailed('final_run'). search_vs_final_payload_kg
    = p_lo_kg - P_final is flagged above final_flag_rel x P_final."""
    b = problem.budget
    flags: list[str] = []

    def fn(p: float) -> ResidualResult:
        return problem.evaluate(p, gamma_star_rad, warm, FINAL_MODE)

    try:
        payload = payload_root(
            fn,
            p_lo_kg,
            b.final_halves_kg,
            backoff_max=b.payload_backoff_max,
            xtol_kg=_final_xtol(b.final_payload_xtol_kg),
            rtol=b.brentq_rtol,
            gamma_star_rad=gamma_star_rad,
            mode=FINAL_MODE,
            low_toward_hint=True,
        )
    except SearchFailed as exc:
        if exc.kind != "bracket":
            raise
        raise SearchFailed("final_bracket", f"final verification: {exc.message}") from exc
    if payload.expansions > 0:
        flags.append(
            f"search_final_mismatch: the final verification's bracket expanded "
            f"{payload.expansions} time(s) around the search payload {p_lo_kg:.6g} kg; the "
            "final value is used"
        )
    flags += backoff_flags("final", payload)
    if payload.status == OK_STATUS:
        payload, n_bisect = _bisect_to_residual(fn, payload, b.final_payload_xtol_kg)
        if n_bisect:
            flags.append(
                f"final: m_res at brentq's P_lo was >= {b.final_payload_xtol_kg:g} kg; the "
                f"final bracket was bisected {n_bisect} more time(s)"
            )
    at_final = payload.at_payload
    recorded = problem.record(at_final)
    _check_recorded(recorded, at_final, b.final_payload_xtol_kg)
    diff = p_lo_kg - payload.payload_kg
    if abs(diff) > b.final_flag_rel * max(payload.payload_kg, 0.0):
        flags.append(
            f"search_vs_final_payload: the search payload {p_lo_kg:.6g} kg differs from the "
            f"final {payload.payload_kg:.6g} kg by {diff:.6g} kg (above "
            f"{b.final_flag_rel:g} of P_final)"
        )
    return FinalResult(gamma_star_rad, payload, at_final, recorded, diff, tuple(flags))


def final_residual(
    problem: RecordingProblem, gamma_star_rad: float, payload_kg: float, warm: WarmStore
) -> FinalResult:
    """The final verification of figure_of_merit residual: one final-mode evaluation at
    (payload [kg], gamma* [rad]) and its recorded run. With m_res >= 0 the recorded run
    must end inserted with m_res >= 0; with m_res < 0 its real propellant runs out before
    the cutoff (short_of_orbit) and it carries the evaluation's signed m_res and
    dv_margin (``SearchContext.record``); otherwise SearchFailed('final_run'). No payload
    search. An infeasible final evaluation raises SearchFailed('final_run')."""
    try:
        at_final = problem.evaluate(payload_kg, gamma_star_rad, warm, FINAL_MODE)
    except INFEASIBLE as exc:
        raise SearchFailed("final_run", f"the final evaluation failed: {exc}") from exc
    recorded = problem.record(at_final)
    _check_recorded(recorded, at_final, math.inf)
    return FinalResult(gamma_star_rad, None, at_final, recorded, math.nan, ())


# ------------------------------------------------------------------------ run search


@dataclass(frozen=True, eq=False)
class SearchRecord:
    """What the search of one run found (the planner's ``RunTrace.search`` in build step
    24): figure_of_merit; status (ok, no_orbit or search_failed for a payload search; ok,
    short_of_orbit or search_failed for residual); budget_id; the gamma* sweep and the
    final verification (None when the search failed before them); the failure kind and
    message (None unless search_failed); flags (sweep, final and rung 2 at P0); grid, the
    gamma* grid table (also after most failures); and at_p0, the final-tolerance rung-2
    evaluation at the vehicle payload P0 and gamma*_ref, whose signed m_res and
    dv_margin are the figures reported at P0 (for residual it is the final evaluation;
    None when the search failed or P0 cannot fly, flagged). For a payload search
    gamma*_ref is the P*-optimal gamma* (refined at P1), not re-optimised at P0, so its
    m_res at P0 sits a few kg below the best m_res at P0 (docs/physics.md, "Figures of
    merit (planar)"); for residual gamma* is refined at P0 itself. The two are not the
    same quantity and are not compared across figures of merit. A negative m_res is
    virtual (massless) propellant, not a stretched tank ("Virtual propellant")."""

    figure_of_merit: str
    status: str
    budget_id: str
    gamma: GammaResult | None
    final: FinalResult | None
    failure_kind: str | None
    failure_message: str | None
    flags: tuple[str, ...]
    grid: tuple[GridPoint, ...] = ()
    at_p0: ResidualResult | None = None

    @property
    def payload_kg(self) -> float:
        """P* [kg]: the final payload (payload search), NaN when the search failed or the
        figure is residual."""
        if self.final is None or self.final.payload is None:
            return math.nan
        return self.final.payload.payload_kg

    @property
    def m_res_p0_kg(self) -> float:
        """The signed residual stage-2 propellant [kg] at the vehicle payload P0
        (final tolerance, gamma*_ref, virtual propellant: a negative value is a virtual,
        massless shortfall); NaN without at_p0."""
        return math.nan if self.at_p0 is None else self.at_p0.m_res_kg

    @property
    def dv_margin_p0_mps(self) -> float:
        """The signed delta-v margin [m/s] at the vehicle payload P0; NaN without at_p0."""
        return math.nan if self.at_p0 is None else self.at_p0.dv_margin_mps

    @property
    def trace(self) -> RunTrace | None:
        """The recorded run's trace (None when the search failed)."""
        return None if self.final is None else self.final.recorded.trace


def _rung2_at_p0(
    problem: RecordingProblem, gamma_star_rad: float, p0_kg: float, warm: WarmStore
) -> tuple[ResidualResult | None, tuple[str, ...]]:
    """The final-mode rung-2 evaluation at the vehicle payload p0_kg [kg] and gamma*
    [rad] of a payload search (after the final verification, so it changes nothing
    before it), or None with a flag when P0 cannot fly."""
    try:
        return problem.evaluate(p0_kg, gamma_star_rad, warm, FINAL_MODE), ()
    except INFEASIBLE as exc:
        return None, (f"rung 2 at P0 = {p0_kg:.6g} kg cannot fly at gamma*_ref: {exc}",)


def run_search(problem: RecordingProblem, warm: WarmStore | None = None) -> SearchRecord:
    """The whole search of one run for the budget's figure of merit: payload
    (``optimise_gamma`` with P1 and P2, then ``final_verify`` at gamma*_ref from P2's
    P_lo, then the final-mode rung 2 at P0 and gamma*_ref for the signed margins at the
    vehicle payload) or residual (``optimise_gamma`` at P0 without payload searches, then
    ``final_residual``; status short_of_orbit when its m_res < 0). A fresh WarmStore
    unless one is given. SearchFailed becomes a record with status search_failed (NaN
    figures of merit, the grid table when one was evaluated); every other exception
    propagates."""
    b = problem.budget
    fom = b.figure_of_merit
    if fom not in ("payload", "residual"):
        raise ValueError(f"run_search needs figure_of_merit payload or residual, got {fom!r}")
    warm = WarmStore() if warm is None else warm
    p0 = problem.payload_kg
    grid: tuple[GridPoint, ...] = ()
    try:
        gamma = optimise_gamma(problem, warm, p0, find_payload=fom == "payload")
        grid = gamma.grid
        if fom == "payload":
            assert gamma.p2 is not None
            final = final_verify(problem, gamma.gamma_star_rad, gamma.p2.payload_kg, warm)
            assert final.payload is not None
            status = final.payload.status
        else:
            final = final_residual(problem, gamma.gamma_star_rad, p0, warm)
            status = OK_STATUS if final.at_final.m_res_kg >= 0.0 else SEARCH_SHORT_STATUS
    except SearchFailed as exc:
        return SearchRecord(
            fom,
            SEARCH_FAILED_STATUS,
            b.budget_id,
            None,
            None,
            exc.kind,
            exc.message,
            (),
            exc.grid or grid,
        )
    if fom == "payload":
        at_p0, p0_flags = _rung2_at_p0(problem, gamma.gamma_star_rad, p0, warm)
    else:
        at_p0, p0_flags = final.at_final, ()
    return SearchRecord(
        fom,
        status,
        b.budget_id,
        gamma,
        final,
        None,
        None,
        gamma.flags + final.flags + p0_flags,
        gamma.grid,
        at_p0,
    )


PLAIN_SKIPPED_FIELDS = frozenset({"shot", "trace"})
"""Fields ``as_plain`` leaves out: the stage-2 shot and the run trace (integration
results, not search results; the recorded trace is reported by the pipeline)."""


def as_plain(obj: object) -> Any:
    """A plain, JSON-shaped copy of a search result (for comparisons and metrics files):
    dataclasses become dicts of their fields in order (PLAIN_SKIPPED_FIELDS left out),
    tuples and lists become lists, numpy scalars Python numbers; floats (NaN included),
    ints, strings, booleans and None stay as they are."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {
            f.name: as_plain(getattr(obj, f.name))
            for f in dataclasses.fields(obj)
            if f.name not in PLAIN_SKIPPED_FIELDS
        }
    if isinstance(obj, (tuple, list)):
        return [as_plain(v) for v in obj]
    if isinstance(obj, np.generic):
        return obj.item()
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    raise TypeError(f"as_plain: unsupported {type(obj).__name__}")


# ---------------------------------------------------------------- test-only joint root


@dataclass(frozen=True)
class JointRoot:
    """The test-only joint root: a, b_per_s [1/s], payload_kg [kg], the Newton
    iterations and the residual components at the root (r_c - r_t [m], v_r,c [m/s],
    m_res [kg])."""

    a: float
    b_per_s: float
    payload_kg: float
    iters: int
    dr_m: float
    v_r_mps: float
    m_res_kg: float


def joint_root_crosscheck(
    ctx: SearchContext,
    gamma_star_rad: float,
    guess: tuple[float, float, float],
    warm: WarmStore,
    mode: str = FINAL_MODE,
) -> JointRoot:
    """Test-only (plan section 3: the joint root is rejected in production): solve the
    three equations r_c = r_t, v_r,c = 0, m_res = 0 jointly for x = (a, LTG_B_SCALE_S b,
    P / JOINT_P_SCALE_KG) at gamma* [rad], with delta re-solved per payload (warm) and
    one virtual-propellant stage-2 shot per x, by a damped Newton with forward-difference
    Jacobians (the mode's LTG fd_step in x units, max_iters, max_halvings). Converged
    when |r_c - r_t| < accept_r_m, |v_r,c| < accept_vr_mps and |m_res| <
    final_payload_xtol_kg; raises GuidanceFailure('nonconverged') otherwise. guess:
    (a, b [1/s], P [kg])."""
    st = ctx.budget.ltg_for(mode)
    m_tol = ctx.budget.final_payload_xtol_kg
    warm.claim(ctx)

    def shot(x: np.ndarray) -> tuple[Stage2Result, np.ndarray]:
        p = float(x[2]) * JOINT_P_SCALE_KG
        planner = ctx.planner(p, mode)
        tol_class = FINAL_MODE if mode == FINAL_MODE else SEARCH_MODE
        kick = warm.kick_point((p, tol_class), lambda: ctx._kick(planner))
        near = warm.nearest(gamma_star_rad)
        sol = solve_delta_for_gamma(
            lambda d: planner.from_kick(d, kick),
            gamma_star_rad,
            ctx.budget.delta,
            None if near is None else near.delta_rad,
        )
        warm.add(WarmEntry(gamma_star_rad, p, sol.delta_rad, None))
        s = planner.stage2(
            sol.handover, float(x[0]), float(x[1]) / LTG_B_SCALE_S, virtual_propellant=True
        )
        f = np.array(
            [
                (s.r_cut_m - ctx.target.r_m) / st.r_scale_m,
                s.v_r_cut_mps / st.vr_scale_mps,
                s.m_res_kg / JOINT_M_SCALE_KG,
            ]
        )
        return s, f

    x = np.array([guess[0], guess[1] * LTG_B_SCALE_S, guess[2] / JOINT_P_SCALE_KG])
    s, f = shot(x)
    for it in range(st.max_iters + 1):
        dr = s.r_cut_m - ctx.target.r_m
        if (
            abs(dr) < st.accept_r_m
            and abs(s.v_r_cut_mps) < st.accept_vr_mps
            and abs(s.m_res_kg) < m_tol
        ):
            return JointRoot(
                float(x[0]),
                float(x[1]) / LTG_B_SCALE_S,
                float(x[2]) * JOINT_P_SCALE_KG,
                it,
                dr,
                s.v_r_cut_mps,
                s.m_res_kg,
            )
        if it == st.max_iters:
            break
        jac = np.empty((3, 3))
        for j in range(3):
            step = np.zeros(3)
            step[j] = st.fd_step
            jac[:, j] = (shot(x + step)[1] - f) / st.fd_step
        dx = -np.linalg.solve(jac, f)
        norm = float(np.linalg.norm(f))
        lam = 1.0
        for _h in range(st.max_halvings + 1):
            try:
                s_t, f_t = shot(x + lam * dx)
            except INFEASIBLE:
                lam *= 0.5
                continue
            if float(np.linalg.norm(f_t)) < norm:
                x, s, f = x + lam * dx, s_t, f_t
                break
            lam *= 0.5
        else:
            raise GuidanceFailure(
                "nonconverged", f"joint root: line search failed at ||F|| = {norm:.3g}"
            )
    raise GuidanceFailure(
        "nonconverged", f"joint root: {st.max_iters} iterations without convergence"
    )
