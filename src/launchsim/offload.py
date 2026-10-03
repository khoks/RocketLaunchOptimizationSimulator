"""Propellant offload at fixed payload (docs/physics.md, "Figures of merit (planar)",
"Propellant offload at fixed payload"; SP1 step 5).

The offload x >= 0 [kg] is propellant removed along a mode (``vehicle.OFFLOAD_MODES``:
``stage1``, ``stage2``, or ``both`` at the same fraction of each stage's load) with the
tanks partly filled and every dry mass unchanged (``vehicle.with_offload``). At a fixed
reference payload P_ref [kg] (the full-load pad's payload capacity on the same vehicle
and orbit), F(x) = m_res, the residual stage-2 propellant at insertion with gamma*
optimised, and the reported offload x* is the largest evaluated x with F(x) >= 0 at the
final tolerance: the feasible-side convention of the payload capacity P*. F(0) < 0 (the
vehicle cannot carry P_ref even with full tanks) is the status ``no_offload``.

``OffloadProblem`` presents the offload to the algorithms of ``search.py`` as their
abscissa. It implements ``search.RecordingProblem``: ``evaluate(x, gamma*, warm, mode)``
flies the vehicle offloaded by x at P_ref, so ``search.optimise_gamma``
(find_payload=True: the grid at x = 0, X1, the refine, X2) and ``search.final_verify``
(the final bracket in x and the recorded run, which flies exactly P_ref and must end
inserted with 0 <= m_res < final_payload_xtol_kg) run on it unchanged. An offload at or
beyond a stage's load raises ``OffloadInfeasible`` (a ``search.PreludeFailure``, so one
of ``search.INFEASIBLE``), which the bracket backs off from like any evaluation that
cannot fly. The problem is built from a problem factory, a callable vehicle ->
RecordingProblem (``planar_problem_factory`` for the planar SearchContext), never from a
context's internals, so a model that supplies a RecordingProblem (the 3-D contexts of
SP3) gets the solver unchanged.

**The abscissa.** The protocol's payload slot carries x. Inside a solve, every
``payload_kg`` field of a ResidualResult, PayloadResult, PayloadEval or WarmEntry, every
"payload" or "P" in a search flag or failure message, and the problem's own
``payload_kg`` property (the grid abscissa x0 = 0) name the offload x [kg], not a
payload. ``solve_offload`` translates at the boundary: ``OffloadResult`` names the offload
``offload_kg``, carries the final evaluation relabelled with its true payload P_ref
(``at_offload``), translates the search logs (``OffloadEval``) and prefixes every inner
flag and failure message with ``ABSCISSA_NOTE``. The search's own records stay available
under ``inner_*`` names, with that warning in their docstrings.

After the solve, the solver checks itself: the logged evaluations of each search in x
(one gamma*, one mode) may change sign at most once, from m_res >= 0 to m_res < 0, as x
grows (flag ``offload_nonmonotone`` otherwise: monotonicity is argued, not assumed), and an
independent payload search (``search.run_search`` on a fresh problem for the vehicle
offloaded by x*) must reproduce P_ref within ``checks.search_final_flag_rel`` x P_ref
(flag ``offload_verify_mismatch`` otherwise). Flags start with ``OFFLOAD_FLAG_PREFIX``; a
SearchFailed becomes the status ``search_failed`` carrying its kind.

Pure: no I/O, no globals, no printing. SI units: masses [kg], speeds [m/s], angles
[rad]; frames are the factory's problem's (planar ECI for the SearchContext).
"""

from __future__ import annotations

import dataclasses
import itertools
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from launchsim.search import (
    OK_STATUS,
    SEARCH_FAILED_STATUS,
    FinalResult,
    GammaResult,
    GridPoint,
    PayloadEval,
    PreludeFailure,
    RecordedRun,
    RecordingProblem,
    ResidualResult,
    SearchBudget,
    SearchContext,
    SearchFailed,
    SearchRecord,
    WarmEntry,
    WarmStore,
    final_verify,
    optimise_gamma,
    run_search,
)
from launchsim.vehicle import (
    OffloadMode,
    OffloadRangeError,
    Vehicle,
    offload_load_kg,
    with_offload,
)

type ProblemFactory = Callable[[Vehicle], RecordingProblem]
"""A problem factory: the RecordingProblem of a vehicle (its payload P0 is the vehicle's
own; every other parameter is the factory's)."""

OFFLOAD_FLAG_PREFIX = "offload:"
"""Prefix of every flag an offload solve raises."""
ABSCISSA_NOTE = "(P = offload x)"
"""Marks an inner search flag or failure message: in it, "payload" and "P" name the
offload x [kg], the abscissa of the solve, not a payload."""
NO_OFFLOAD_STATUS = "no_offload"
"""Status of an offload solve whose m_res(0) < 0 at P_ref: the vehicle cannot carry the
reference payload even with full tanks (x* = 0, shortfall -dv_margin(0))."""
OFFLOAD_STATUSES = (OK_STATUS, NO_OFFLOAD_STATUS, SEARCH_FAILED_STATUS)
"""Every status of an offload solve: ok (x* found), no_offload, search_failed (the
search in x raised SearchFailed; ``OffloadResult.failure_kind`` carries its kind)."""
OFFLOAD_GRID_X_KG = 0.0
"""The offload x [kg] the gamma* grid runs at: the full load."""
OFFLOAD_RANGE_KIND = "offload_range"
"""Kind of ``OffloadInfeasible``: the offload takes a stage's whole load or more."""
NONMONOTONE_FLAG = "offload_nonmonotone"
"""Flag name: a logged search in x whose m_res changes sign more than once, or once from
< 0 to >= 0, as x grows."""
VERIFY_MISMATCH_FLAG = "offload_verify_mismatch"
"""Flag name: the independent payload search of the offloaded vehicle does not reproduce
P_ref within ``checks.search_final_flag_rel`` x P_ref (or does not end ok)."""
X1_LOG, X2_LOG, FINAL_LOG = "X1", "X2", "final"
"""Names of the logged searches in x: the search's P1 (at the best grid gamma*), P2 (at
gamma*_ref) and the final verification."""


class OffloadInfeasible(PreludeFailure):
    """An offload at or beyond the load it is taken from: the offloaded vehicle cannot be
    built (raised as ``OffloadInfeasible(OFFLOAD_RANGE_KIND, message)``). A
    PreludeFailure, so one of ``search.INFEASIBLE``: the payload root backs off from it
    like from any evaluation that cannot fly, and it pickles like its parent."""


@dataclass
class OffloadWarmStore(WarmStore):
    """The warm store of one offload solve, bound to its OffloadProblem
    (``WarmStore.claim``). Its own entries are the solved evaluations with the offload x
    [kg] in their payload_kg field, so the nearest-gamma* warm start runs across offloads
    as it runs across payloads in a payload search. members: per evaluated offload x [kg],
    the problem the factory built for that vehicle and that problem's own fresh WarmStore
    (the kick point of an evaluation depends on the vehicle, so each offloaded vehicle
    keeps its own cache: one store per problem). evaluations: the number of
    ``OffloadProblem.evaluate`` calls, failed ones included."""

    members: dict[float, tuple[RecordingProblem, WarmStore]] = field(
        default_factory=dict, repr=False, compare=False
    )
    evaluations: int = 0

    def member(
        self, offload_kg: float, make: Callable[[], RecordingProblem]
    ) -> tuple[RecordingProblem, WarmStore]:
        """The problem and store of offload_kg [kg], made with ``make`` (and a fresh
        WarmStore) on the first request; an exception ``make`` raises is not cached."""
        hit = self.members.get(offload_kg)
        if hit is None:
            hit = (make(), WarmStore())
            self.members[offload_kg] = hit
        return hit


@dataclass(frozen=True, eq=False)
class OffloadProblem:
    """The offload at fixed payload as a ``search.RecordingProblem`` whose abscissa is
    the offload x [kg] (see the module docstring, "The abscissa").

    factory: vehicle -> RecordingProblem; vehicle: the full-load vehicle (its own payload
    is not flown here: every evaluation flies reference_payload_kg); mode: one of
    ``vehicle.OFFLOAD_MODES``; reference_payload_kg: P_ref [kg]; budget: the shared
    SearchBudget, the factory's problem's (``from_factory``). Frame: the factory's
    problem's."""

    factory: ProblemFactory
    vehicle: Vehicle
    mode: OffloadMode
    reference_payload_kg: float
    budget: SearchBudget

    def __post_init__(self) -> None:
        offload_load_kg(self.vehicle, self.mode)  # ValueError for a mode the vehicle lacks
        p = self.reference_payload_kg
        if not (math.isfinite(p) and p >= 0.0):
            raise ValueError(f"reference_payload_kg must be finite and >= 0, got {p!r}")

    @classmethod
    def from_factory(
        cls,
        factory: ProblemFactory,
        vehicle: Vehicle,
        mode: OffloadMode,
        reference_payload_kg: float,
    ) -> OffloadProblem:
        """The problem of factory, vehicle, mode and P_ref [kg], with the budget of
        ``factory(vehicle)``."""
        return cls(factory, vehicle, mode, reference_payload_kg, factory(vehicle).budget)

    @property
    def payload_kg(self) -> float:
        """The protocol's grid abscissa: the offload x0 = OFFLOAD_GRID_X_KG [kg] (the full
        load) at which the gamma* grid runs. Not a payload: the payload is
        reference_payload_kg."""
        return OFFLOAD_GRID_X_KG

    @property
    def load_kg(self) -> float:
        """The full load [kg] the offload is taken from (``vehicle.offload_load_kg``)."""
        return offload_load_kg(self.vehicle, self.mode)

    def vehicle_at(self, offload_kg: float) -> Vehicle:
        """The vehicle offloaded by offload_kg [kg] along the mode
        (``vehicle.with_offload``); OffloadInfeasible when a stage would keep no
        propellant."""
        try:
            return with_offload(self.vehicle, self.mode, offload_kg)
        except OffloadRangeError as exc:
            raise OffloadInfeasible(OFFLOAD_RANGE_KIND, str(exc)) from exc

    def problem_at(self, offload_kg: float) -> RecordingProblem:
        """The factory's problem of the vehicle offloaded by offload_kg [kg]."""
        return self.factory(self.vehicle_at(offload_kg))

    def evaluate(
        self,
        offload_kg: float,
        gamma_star_rad: float,
        warm: WarmStore,
        mode: str,
        *,
        seed: WarmEntry | None = None,
    ) -> ResidualResult:
        """Rung 2 of the vehicle offloaded by offload_kg [kg] (the protocol's payload
        slot) at P_ref and gamma* [rad] in mode: the problem of that vehicle (made once
        per offload, with its own store, in the OffloadWarmStore warm) evaluated at
        reference_payload_kg, warm-started from seed, else from the entry of warm with
        the nearest gamma* (both relabelled with P_ref for that problem). The solved
        evaluation is added to warm labelled with offload_kg, and the result is returned
        with payload_kg = offload_kg (the abscissa). Raises OffloadInfeasible for an
        offload at or beyond the load, the problem's own INFEASIBLE exceptions, TypeError
        when warm is not an OffloadWarmStore, and ValueError when it belongs to another
        problem."""
        if not isinstance(warm, OffloadWarmStore):
            raise TypeError(
                "an OffloadProblem evaluates with an OffloadWarmStore (one problem and one "
                f"store per offload), got {type(warm).__name__}"
            )
        warm.claim(self)
        warm.evaluations += 1
        x = float(offload_kg)
        problem, store = warm.member(x, lambda: self.problem_at(x))
        near = seed if seed is not None else warm.nearest(gamma_star_rad)
        start = (
            None
            if near is None
            else dataclasses.replace(near, payload_kg=self.reference_payload_kg)
        )
        res = problem.evaluate(self.reference_payload_kg, gamma_star_rad, store, mode, seed=start)
        warm.add(WarmEntry(gamma_star_rad, x, res.delta_rad, res.ltg))
        return dataclasses.replace(res, payload_kg=x)

    def record(self, res: ResidualResult) -> RecordedRun:
        """The recorded run of the evaluation res, whose payload_kg is the offload x [kg]:
        the factory's problem of the vehicle offloaded by x records res relabelled with
        P_ref (it flies exactly the reference payload)."""
        payload_res = dataclasses.replace(res, payload_kg=self.reference_payload_kg)
        return self.problem_at(res.payload_kg).record(payload_res)


def planar_problem_factory(ctx: SearchContext) -> ProblemFactory:
    """The planar problem factory of ctx: ctx with its vehicle replaced
    (``dataclasses.replace``), every other parameter (ignition, guidance, environment,
    target, settings, budget, assist, track) kept."""

    def factory(vehicle: Vehicle) -> RecordingProblem:
        return dataclasses.replace(ctx, vehicle=vehicle)

    return factory


@dataclass(frozen=True)
class OffloadEval:
    """One logged evaluation of a search in x: search (X1_LOG, X2_LOG or FINAL_LOG),
    offload_kg [kg], m_res_kg [kg] and dv_margin_mps [m/s] (NaN when it failed) and the
    failure (``kind: message``; None when it flew)."""

    search: str
    offload_kg: float
    m_res_kg: float
    dv_margin_mps: float
    failure: str | None

    @property
    def ok(self) -> bool:
        """True when the evaluation flew."""
        return self.failure is None

    @classmethod
    def from_payload_eval(cls, search: str, e: PayloadEval) -> OffloadEval:
        """The OffloadEval of a PayloadEval of a search in x (its payload_kg is x)."""
        return cls(search, e.payload_kg, e.m_res_kg, e.dv_margin_mps, e.failure)


@dataclass(frozen=True, eq=False)
class OffloadVerification:
    """The independent check of a solved offload: the payload search (``run_search``,
    fresh store) of the vehicle offloaded by x*. status: that search's; payload_kg: its P*
    [kg] (NaN when it failed); delta_kg = payload_kg - P_ref [kg]; tolerance_kg:
    ``checks.search_final_flag_rel`` x P_ref [kg]; passed: status ok and |delta_kg| <=
    tolerance_kg; record: the SearchRecord (true payloads throughout)."""

    status: str
    payload_kg: float
    delta_kg: float
    tolerance_kg: float
    passed: bool
    record: SearchRecord


@dataclass(frozen=True, eq=False)
class OffloadResult:
    """What an offload solve found (``solve_offload``).

    mode, reference_payload_kg (P_ref [kg]) and load_kg (the full load the offload is
    taken from [kg]); status (OFFLOAD_STATUSES); offload_kg: x* [kg], the largest
    final-tolerance evaluated offload with m_res >= 0 (0 for no_offload, NaN for
    search_failed); root_kg: the final brentq root in x [kg] (NaN unless ok);
    gamma_star_rad [rad]: the solve's gamma*_ref; m_res_kg [kg] and dv_margin_mps [m/s]:
    the signed final-tolerance figures at x* (0 <= m_res < final_payload_xtol_kg when
    ok; negative at x = 0 for no_offload); dv_shortfall_mps: -dv_margin(0) [m/s] for
    no_offload, NaN otherwise; at_offload: the final evaluation at x*, relabelled with
    its true payload (payload_kg = P_ref); recorded: its recorded run (flies P_ref);
    offloaded_vehicle: the vehicle at x*; evaluations: the logs of the X1, X2 and final
    searches in order; n_evaluations: OffloadProblem.evaluate calls of the solve (failed
    ones included; the verification not counted); grid: the gamma* grid table (at x =
    0); verification: OffloadVerification (None unless ok and asked for); flags: every
    flag, prefixed OFFLOAD_FLAG_PREFIX; failure_kind and failure_message: the
    SearchFailed's (None unless search_failed; the message carries ABSCISSA_NOTE).
    inner_gamma and inner_final: the search's own GammaResult and FinalResult, in which
    every payload_kg field is the offload x [kg], not a payload. None means "not
    reached"."""

    mode: str
    reference_payload_kg: float
    load_kg: float
    status: str
    offload_kg: float
    root_kg: float
    gamma_star_rad: float
    m_res_kg: float
    dv_margin_mps: float
    dv_shortfall_mps: float
    at_offload: ResidualResult | None
    recorded: RecordedRun | None
    offloaded_vehicle: Vehicle | None
    evaluations: tuple[OffloadEval, ...]
    n_evaluations: int
    grid: tuple[GridPoint, ...]
    verification: OffloadVerification | None
    flags: tuple[str, ...]
    failure_kind: str | None = None
    failure_message: str | None = None
    inner_gamma: GammaResult | None = None
    inner_final: FinalResult | None = None

    @property
    def fraction_of_load(self) -> float:
        """x* / load_kg (dimensionless; NaN without x*)."""
        return self.offload_kg / self.load_kg


def offload_logs(gamma: GammaResult, final: FinalResult) -> tuple[OffloadEval, ...]:
    """The logged evaluations of the three searches in x of a solve (X1, X2, final), in
    order, as OffloadEvals."""
    logs = []
    for name, payload in ((X1_LOG, gamma.p1), (X2_LOG, gamma.p2), (FINAL_LOG, final.payload)):
        if payload is not None:
            logs += [OffloadEval.from_payload_eval(name, e) for e in payload.evals]
    return tuple(logs)


def sign_changes(evals: Sequence[OffloadEval]) -> tuple[int, bool]:
    """The sign pattern of m_res along the evaluations that flew, sorted by offload: the
    number of changes between m_res >= 0 and m_res < 0, and whether the first (lightest
    offload) is negative."""
    flown = sorted((e for e in evals if e.ok), key=lambda e: e.offload_kg)
    feasible = [e.m_res_kg >= 0.0 for e in flown]
    changes = sum(a != b for a, b in itertools.pairwise(feasible))
    return changes, bool(feasible) and not feasible[0]


def nonmonotone_flags(evals: Sequence[OffloadEval]) -> tuple[str, ...]:
    """The ``offload_nonmonotone`` flag of each logged search in x whose m_res does not
    change sign at most once, from >= 0 to < 0, as x grows (two or more changes, or one
    from < 0 to >= 0); () when every search passes. The rule is the same for every
    status, and a search with no change passes: a no_offload solve's final search has
    none (its low end walks down to x = 0 without meeting m_res >= 0, so every
    evaluation is negative), while its X1 and X2 may still change sign once."""
    flags = []
    for name in (X1_LOG, X2_LOG, FINAL_LOG):
        log = [e for e in evals if e.search == name]
        changes, starts_negative = sign_changes(log)
        if changes > 1 or (changes == 1 and starts_negative):
            pattern = ", ".join(
                f"{e.offload_kg:.6g} kg: {e.m_res_kg:+.4g} kg"
                for e in sorted((e for e in log if e.ok), key=lambda e: e.offload_kg)
            )
            flags.append(
                f"{OFFLOAD_FLAG_PREFIX} {NONMONOTONE_FLAG}: the {name} search's m_res(x) "
                f"changes sign {changes} time(s) along x (first sign "
                f"{'negative' if starts_negative else 'non-negative'}): {pattern}"
            )
    return tuple(flags)


def verify_offload(
    factory: ProblemFactory, offloaded: Vehicle, reference_payload_kg: float, budget: SearchBudget
) -> OffloadVerification:
    """The independent check of a solved offload: ``run_search`` (fresh WarmStore) on
    ``factory(offloaded)``, the vehicle offloaded by x* at its own payload P0, must end
    ok with |P* - P_ref| <= budget.final_flag_rel x P_ref [kg]."""
    record = run_search(factory(offloaded))
    tolerance = budget.final_flag_rel * reference_payload_kg
    delta = record.payload_kg - reference_payload_kg
    passed = record.status == OK_STATUS and abs(delta) <= tolerance
    return OffloadVerification(record.status, record.payload_kg, delta, tolerance, passed, record)


def _verification_flags(v: OffloadVerification, offload_kg: float) -> list[str]:
    """The mismatch flag (when the check failed) and the verification search's own flags,
    prefixed."""
    flags = []
    if not v.passed:
        flags.append(
            f"{OFFLOAD_FLAG_PREFIX} {VERIFY_MISMATCH_FLAG}: the payload search of the vehicle "
            f"offloaded by {offload_kg:.6g} kg ended {v.status!r} with P* = "
            f"{v.payload_kg:.6g} kg, {v.delta_kg:+.6g} kg from P_ref (tolerance "
            f"{v.tolerance_kg:.6g} kg)"
        )
    flags += [f"{OFFLOAD_FLAG_PREFIX} verification: {f}" for f in v.record.flags]
    return flags


def solve_offload(
    factory: ProblemFactory,
    vehicle: Vehicle,
    mode: OffloadMode,
    reference_payload_kg: float,
    *,
    verify: bool = True,
) -> OffloadResult:
    """The largest offload x* [kg] along mode at which the vehicle still carries
    reference_payload_kg (P_ref [kg]) to the factory problem's orbit, at the shared budget.

    ``search.optimise_gamma`` (find_payload=True) on the OffloadProblem with a fresh
    OffloadWarmStore: the gamma* grid at x = 0, X1 = the search in x at the best grid
    point (hint 0, the budget's payload half-widths and backoffs), the bounded Brent
    refine at X1, X2 at gamma*_ref; then ``search.final_verify`` from X2 (final bracket,
    xtol min(final_payload_xtol_kg, final_payload_xtol_kg / |dm_res/dx|), the recorded
    run at x*, flying P_ref, inserted with 0 <= m_res < final_payload_xtol_kg). Status ok
    with x* = the final P_lo in x; no_offload when the final m_res(0) < 0 (x* = 0, the
    shortfall -dv_margin(0)); search_failed with the SearchFailed's kind and message.
    Then the sign check of every logged search (``nonmonotone_flags``) and, for ok with
    verify, the independent payload search (``verify_offload``; it needs
    figure_of_merit payload). Flags: the inner search's (with ABSCISSA_NOTE), the
    monotonicity and verification flags and the verification search's own, all prefixed
    OFFLOAD_FLAG_PREFIX. ValueError for an unknown mode, a vehicle without the mode's
    stages, a negative P_ref, or verify with another figure of merit."""
    problem = OffloadProblem.from_factory(factory, vehicle, mode, reference_payload_kg)
    budget = problem.budget
    if verify and budget.figure_of_merit != "payload":
        raise ValueError(
            "the offload's independent verification is a payload search: it needs "
            f"search.figure_of_merit payload, got {budget.figure_of_merit!r}"
        )
    warm = OffloadWarmStore()
    nan = math.nan
    try:
        gamma = optimise_gamma(problem, warm, problem.payload_kg, find_payload=True)
        assert gamma.p2 is not None
        final = final_verify(problem, gamma.gamma_star_rad, gamma.p2.payload_kg, warm)
    except SearchFailed as exc:
        return OffloadResult(
            mode=mode,
            reference_payload_kg=reference_payload_kg,
            load_kg=problem.load_kg,
            status=SEARCH_FAILED_STATUS,
            offload_kg=nan,
            root_kg=nan,
            gamma_star_rad=nan,
            m_res_kg=nan,
            dv_margin_mps=nan,
            dv_shortfall_mps=nan,
            at_offload=None,
            recorded=None,
            offloaded_vehicle=None,
            evaluations=(),
            n_evaluations=warm.evaluations,
            grid=exc.grid,
            verification=None,
            flags=(),
            failure_kind=exc.kind,
            failure_message=f"{ABSCISSA_NOTE} {exc.message}",
        )
    payload = final.payload
    assert payload is not None
    ok = payload.status == OK_STATUS
    x_star = payload.payload_kg
    evals = offload_logs(gamma, final)
    flags = [f"{OFFLOAD_FLAG_PREFIX} {ABSCISSA_NOTE} {f}" for f in gamma.flags + final.flags]
    flags += nonmonotone_flags(evals)
    offloaded = problem.vehicle_at(x_star)
    verification = None
    if ok and verify:
        verification = verify_offload(factory, offloaded, reference_payload_kg, budget)
        flags += _verification_flags(verification, x_star)
    at = final.at_final
    return OffloadResult(
        mode=mode,
        reference_payload_kg=reference_payload_kg,
        load_kg=problem.load_kg,
        status=OK_STATUS if ok else NO_OFFLOAD_STATUS,
        offload_kg=x_star,
        root_kg=payload.root_kg,
        gamma_star_rad=gamma.gamma_star_rad,
        m_res_kg=at.m_res_kg,
        dv_margin_mps=at.dv_margin_mps,
        dv_shortfall_mps=payload.dv_shortfall_mps,
        at_offload=dataclasses.replace(at, payload_kg=reference_payload_kg),
        recorded=final.recorded,
        offloaded_vehicle=offloaded,
        evaluations=evals,
        n_evaluations=warm.evaluations,
        grid=gamma.grid,
        verification=verification,
        flags=tuple(flags),
        inner_gamma=gamma,
        inner_final=final,
    )
