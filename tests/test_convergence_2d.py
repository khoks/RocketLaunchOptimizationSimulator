"""Convergence of the planar figures of merit under the shipped budget (CLAUDE.md:
tightening the tolerances 10x changes payload and margins by < 0.1 %; plan section 8,
"Convergence, fixed gamma*" and "Convergence, gamma* re-optimised"; amendment 3;
docs/physics.md, "Convergence (planar)").

The shipped budget of experiments/silo_screening_2d.yaml (search rtol 1e-8 with atol x
10, final rtol 1e-10, LTG acceptance 1 m and 1e-3 m/s, delta xtol 1e-10 rad, payload
xtols 0.5 and 0.05 kg, gamma xatol 0.01 deg) is compared with the same budget tightened
by ``checks.convergence`` (``SearchContext.tightened``: every tolerance divided by
tighten_factor = 10, the max_step caps multiplied by max_step_factor = 0.5; the LTG
finite-difference steps unchanged). Each compared value must agree within rel_tol =
1e-3, with the absolute floors of amendment 3 for near-zero terms: loss_floor_mps =
1e-3 m/s for any loss term and margin_floor_kg = 0.5 kg-equivalent for margins; gamma*
is compared only to gamma_resolution_deg = 0.1 deg. The fixed-gamma tests fly the pad
of the gate fork (P0 = 22.8 t) at a fixed gamma*. On the pad the halved max_step caps change
nothing: its 2 s startup ramp runs in the closed-form hold (lit at -2 s) and MVac starts
at a step, so the ramp, lag and push step counts are not used (the step-23 review
measured bit-identical m_res). The fixed-gamma tests therefore also fly silo_cold (the
push cap on the track and the ramp cap of its 2 s ramp lit 0.5 s after release) and
silo_cold_lag (the push cap and the lag cap of its first-order startup, which caps the
whole stage-1 burn), where the halving acts (build step 25); silo_cold_lag is slow.
Amendment 3's per-term loss rule is checked there, at a common gamma*, where it isolates
the convergence of the integration. The slow re-optimised test repeats the whole search
of the same three runs and compares gravity plus steering jointly: after a
re-optimisation the two terms trade with the shift of gamma*_ref, which at the shipped
search setting is set by search-mode integration noise (a first_step-only perturbation
moves it by up to 1e-2 deg and the split by up to 1.5e-3 relative on the pad and
silo_cold), so the split is not a convergence measure there (docs/physics.md,
"Convergence (planar)").

These are the only planar tests that fly the shipped search rtol of 1e-8 (atol x 10):
amendment 3 requires the convergence of the shipped budget itself, so the baseline side
of each comparison is the budget every experiment runs. Every other planar test uses
the test budget (search rtol 1e-9, CLAUDE.md's "rtol <= 1e-9 in tests"); the
tightened side here flies 1e-9 search and 1e-11 final.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from launchsim.cli import load_experiment
from launchsim.config import ChecksConfig, ConvergenceConfig
from launchsim.dynamics import PLANAR_LAYOUT, PlanarDynamics2D
from launchsim.losses import LossBudget, loss_budget
from launchsim.metrics_planar import MaxQ, max_q
from launchsim.phases import ASSIST_KIND, RunTrace
from launchsim.phases.planar import GRAVITY_TURN, KICK
from launchsim.search import (
    FINAL_MODE,
    FinalResult,
    ResidualResult,
    SearchContext,
    SearchRecord,
    WarmStore,
    final_verify,
    run_search,
)

GAMMA_FIXED_RAD = math.radians(20.0)
"""The fixed gamma* of the fast test [rad] (a grid point near the pad's optimum)."""
LOSS_TERMS = ("dv_vac", "gravity", "drag", "steering", "back_pressure")
"""The LossBudget terms compared [m/s]."""
SPLIT_TERMS = ("gravity", "steering")
"""The two loss terms that trade with gamma*_ref (about 15.2 and 14.5 m/s per deg, in
opposite directions, on silo_cold; measured in build step 25): after a re-optimisation
test_reoptimised_search_converges compares their sum, at the steering term's tolerance;
one by one they are compared only at a fixed gamma* [m/s]."""


@dataclass(frozen=True)
class Shipped:
    """One run's context, its checks and the convergence block, from the experiment."""

    ctx: SearchContext
    checks: ChecksConfig
    conv: ConvergenceConfig


REOPTIMISED_RUNS = ("pad", "silo_cold", "silo_cold_lag")
"""Runs of experiments/silo_screening_2d.yaml whose whole search the slow test repeats
tightened: the pad (no step cap in use), silo_cold (push and ramp caps) and
silo_cold_lag (push and lag caps)."""
FIXED_RUNS = (
    "pad",
    "silo_cold",
    pytest.param("silo_cold_lag", marks=pytest.mark.slow),
)
"""The same runs flown at the fixed gamma*; silo_cold_lag (about 9 s, its lag cap spans
the whole stage-1 burn) is slow."""
CAPPED_KINDS = {
    "pad": frozenset(),
    "silo_cold": frozenset({ASSIST_KIND, KICK}),
    "silo_cold_lag": frozenset({ASSIST_KIND, KICK, GRAVITY_TURN}),
}
"""The phase kinds of each run's recorded trace that fly a finite max_step: the push cap
on the track (ASSIST), the ramp cap of silo_cold's 2 s ramp (KICK) and the lag cap of
silo_cold_lag's first-order startup (KICK and the whole GRAVITY_TURN); the pad has none
(its ramp runs in the closed-form hold)."""
CAP_RATIO_RTOL = 1e-12
"""Relative tolerance [-] on the tightened/shipped max_step ratio (both are the same
quotient t / n with n doubled exactly)."""


def _shipped_of(repo_root: Path, name: str) -> Shipped:
    """Run ``name`` of experiments/silo_screening_2d.yaml at the shipped budget."""
    exp = load_experiment(repo_root / "experiments" / "silo_screening_2d.yaml")
    run = exp.runs[name]
    assert run.run.planar is not None
    checks = run.run.planar.checks
    return Shipped(SearchContext.from_run(run.run, run.to_vehicle()), checks, checks.convergence)


def _close(a: float, b: float, rel: float, floor: float) -> bool:
    """|a - b| within rel of the larger magnitude, or within the absolute floor."""
    return abs(a - b) <= max(rel * max(abs(a), abs(b)), floor)


def _budget_of(trace: RunTrace, ctx: SearchContext) -> LossBudget:
    model = PlanarDynamics2D(ctx.env.omega_p_rads, ctx.env.r_datum_m)
    return loss_budget(trace.ascent_phases(), PLANAR_LAYOUT, speed=model.speed)


def _max_q(trace: RunTrace, checks: ChecksConfig) -> MaxQ:
    peak = max_q(trace.phases, n_points=checks.maxq_scan_points, xatol_s=checks.maxq_xatol_s)
    assert peak is not None
    return peak


def _margin_floor_mps(res: ResidualResult, floor_kg: float) -> float:
    """The dv_margin equivalent [m/s] of floor_kg of residual propellant at the cutoff:
    d(c2 ln(m_c/m_empty)) = c2 dm/m_c."""
    assert res.shot is not None
    return res.shot.c_mps * floor_kg / res.shot.m_cut_kg


@dataclass(frozen=True)
class Fixed:
    """At fixed gamma*: the final-mode evaluation at P0, the final verification and the
    payload [kg] it started from."""

    at_p0: ResidualResult
    final: FinalResult
    hint_kg: float


def _fixed_shipped(shipped: Shipped) -> Fixed:
    """Fixed gamma* at the shipped budget: final-mode m_res at P0 and at P0 + m_res(P0),
    their secant zero as the start of the final verification (all in one warm store)."""
    ctx, warm = shipped.ctx, WarmStore()
    p0 = ctx.payload_kg
    r0 = ctx.evaluate(p0, GAMMA_FIXED_RAD, warm, FINAL_MODE)
    r1 = ctx.evaluate(p0 + r0.m_res_kg, GAMMA_FIXED_RAD, warm, FINAL_MODE)
    hint = p0 + r0.m_res_kg * (r1.payload_kg - p0) / (r0.m_res_kg - r1.m_res_kg)
    return Fixed(r0, final_verify(ctx, GAMMA_FIXED_RAD, hint, warm), hint)


def _fixed_tight(tight: SearchContext, hint_kg: float) -> Fixed:
    """Fixed gamma* at the tightened budget, from the same start payload."""
    warm = WarmStore()
    at_p0 = tight.evaluate(tight.payload_kg, GAMMA_FIXED_RAD, warm, FINAL_MODE)
    return Fixed(at_p0, final_verify(tight, GAMMA_FIXED_RAD, hint_kg, warm), hint_kg)


@dataclass(frozen=True)
class FixedPair:
    """One run at the fixed gamma*: shipped (a) and tightened 10x (b), with the shipped
    context and the tightened one."""

    shipped: Shipped
    tight: SearchContext
    a: Fixed
    b: Fixed


@pytest.fixture(scope="module")
def fixed(repo_root: Path) -> Callable[[str], FixedPair]:
    """Run name -> its FixedPair, each flown once per module (the two fixed-gamma tests
    share them)."""
    cache: dict[str, FixedPair] = {}

    def get(name: str) -> FixedPair:
        if name not in cache:
            shipped = _shipped_of(repo_root, name)
            tight = shipped.ctx.tightened(shipped.conv)
            a = _fixed_shipped(shipped)
            cache[name] = FixedPair(shipped, tight, a, _fixed_tight(tight, a.hint_kg))
        return cache[name]

    return get


def _caps(trace: RunTrace) -> dict[str, float]:
    """Phase kind -> the smallest finite max_step [s] its phases flew (kinds with no cap
    left out)."""
    caps: dict[str, float] = {}
    for p in trace.phases:
        if math.isfinite(p.spec.max_step):
            caps[p.spec.kind] = min(caps.get(p.spec.kind, math.inf), p.spec.max_step)
    return caps


def _assert_capped_where_pushed(
    ta: RunTrace, tb: RunTrace, conv: ConvergenceConfig, name: str
) -> None:
    """The run pushes on the track exactly when it is not the pad; the recorded shipped
    (ta) and tightened (tb) traces fly a finite max_step in exactly the kinds of
    CAPPED_KINDS[name], and each tightened cap is max_step_factor times the shipped one
    (the halving really reaches the flown phases)."""
    assert any(p.spec.kind == ASSIST_KIND for p in ta.phases) == (name != "pad")
    ca, cb = _caps(ta), _caps(tb)
    assert set(ca) == set(cb) == CAPPED_KINDS[name]
    for kind, cap in ca.items():
        ratio = cb[kind] / cap
        assert ratio == pytest.approx(conv.max_step_factor, rel=CAP_RATIO_RTOL), kind


@pytest.mark.parametrize("name", FIXED_RUNS)
def test_fixed_gamma_payload_and_margins_converge(
    fixed: Callable[[str], FixedPair], name: str
) -> None:
    """At gamma* = 20 deg: P* (the final verification's P_final), and m_res and dv_margin
    at 22.8 t, move by less than rel_tol or margin_floor_kg (its dv equivalent for
    dv_margin) when every tolerance is tightened 10x. Both recorded runs end inserted
    with 0 <= m_res < their final xtol. Measured (build step 25), dP* / d m_res(P0) /
    d dv_margin(P0): pad -8.0e-4 kg / -5.6e-4 kg / -6.4e-5 m/s; silo_cold -1.0e-3 kg /
    -1.6e-6 kg / -1.8e-7 m/s; silo_cold_lag -1.0e-3 kg / +8.2e-7 kg / +8.9e-8 m/s."""
    pair = fixed(name)
    shipped, conv = pair.shipped, pair.shipped.conv
    a, b = pair.a, pair.b
    assert _close(a.final.payload_kg, b.final.payload_kg, conv.rel_tol, conv.margin_floor_kg)
    assert abs(a.final.payload_kg - b.final.payload_kg) < conv.margin_floor_kg
    assert _close(a.at_p0.m_res_kg, b.at_p0.m_res_kg, conv.rel_tol, conv.margin_floor_kg)
    assert abs(a.at_p0.m_res_kg - b.at_p0.m_res_kg) < conv.margin_floor_kg
    floor = _margin_floor_mps(a.at_p0, conv.margin_floor_kg)
    assert _close(a.at_p0.dv_margin_mps, b.at_p0.dv_margin_mps, conv.rel_tol, floor)
    for f, ctx in ((a, shipped.ctx), (b, pair.tight)):
        assert f.final.recorded.status == "inserted"
        assert 0.0 <= f.final.recorded.m_res_kg < ctx.budget.final_payload_xtol_kg


@pytest.mark.parametrize("name", FIXED_RUNS)
def test_fixed_gamma_losses_and_max_q_converge(
    fixed: Callable[[str], FixedPair], name: str
) -> None:
    """The recorded runs at P_final (gamma* = 20 deg): amendment 3's per-term rule, every
    loss term (J_vac, gravity, drag, steering, back-pressure) one by one within rel_tol
    or loss_floor_mps, and max-Q (value and time) within rel_tol. On the silo runs the
    recorded run pushes on the track. Measured (build step 25): every loss term within
    4.6e-5 m/s on the pad (gravity; J_vac 3.5e-5, steering 2.0e-5), 4.0e-5 m/s on
    silo_cold and 4.1e-5 m/s on silo_cold_lag (steering 1.1e-5 on both, 9e-8
    relative); max-Q within 5.2e-9 and its time within 1.7e-9 relative on all three.
    The recorded traces fly the push, ramp and lag caps where CAPPED_KINDS says, halved
    in the tightened run."""
    pair = fixed(name)
    shipped, conv = pair.shipped, pair.shipped.conv
    ta, tb = pair.a.final.recorded.trace, pair.b.final.recorded.trace
    la, lb = _budget_of(ta, shipped.ctx), _budget_of(tb, shipped.ctx)
    for term in LOSS_TERMS:
        va, vb = getattr(la, term), getattr(lb, term)
        assert _close(va, vb, conv.rel_tol, conv.loss_floor_mps), term
    qa, qb = _max_q(ta, shipped.checks), _max_q(tb, shipped.checks)
    assert _close(qa.q_pa, qb.q_pa, conv.rel_tol, 0.0)
    assert _close(qa.t_s, qb.t_s, conv.rel_tol, 0.0)
    _assert_capped_where_pushed(ta, tb, conv, name)


@dataclass(frozen=True)
class Reoptimised:
    """The whole search of one run at the shipped budget (a) and tightened 10x (b), with
    the shipped context and the tightened one."""

    shipped: Shipped
    tight: SearchContext
    a: SearchRecord
    b: SearchRecord


@pytest.fixture(scope="module")
def reoptimised(repo_root: Path) -> Callable[[str], Reoptimised]:
    """Run name -> its Reoptimised, each pair of searches flown once per module (the two
    slow tests below share them)."""
    cache: dict[str, Reoptimised] = {}

    def get(name: str) -> Reoptimised:
        if name not in cache:
            shipped = _shipped_of(repo_root, name)
            tight = shipped.ctx.tightened(shipped.conv)
            cache[name] = Reoptimised(shipped, tight, run_search(shipped.ctx), run_search(tight))
        return cache[name]

    return get


def _recorded_budgets(r: Reoptimised) -> tuple[LossBudget, LossBudget]:
    """The loss budgets of the shipped and the tightened recorded runs."""
    assert r.a.trace is not None and r.b.trace is not None
    return _budget_of(r.a.trace, r.shipped.ctx), _budget_of(r.b.trace, r.shipped.ctx)


@pytest.mark.slow
@pytest.mark.parametrize("name", REOPTIMISED_RUNS)
def test_reoptimised_search_converges(reoptimised: Callable[[str], Reoptimised], name: str) -> None:
    """The whole search (the 15-point grid, P1, the refine, P2, the final verification,
    the recorded run and rung 2 at P0) of the pad, silo_cold and silo_cold_lag at the
    shipped budget and tightened 10x (gamma_xatol included; the ramp, lag and push step
    counts doubled): P* within rel_tol or margin_floor_kg, the signed m_res at P0
    likewise and its dv_margin within rel_tol or the dv equivalent of margin_floor_kg
    (CLAUDE.md's payload and margins), gamma* within gamma_resolution_deg, the recorded
    runs' J_vac, drag and back-pressure within rel_tol or loss_floor_mps, gravity plus
    steering jointly within the steering term's own tolerance (rel_tol of |steering| or
    loss_floor_mps, about 0.09 m/s; SPLIT_TERMS: one by one they trade with the
    noise-set shift of gamma*_ref and are compared only at a fixed gamma*, in the tests
    above) and their max-Q (value and time) within rel_tol. The recorded traces fly the
    push, ramp and lag caps where CAPPED_KINDS says, halved in the tightened run (the
    halving acts on the silo runs, unlike on the pad). Measured (build step 25),
    shipped to tightened: dP* -9.2e-4 kg (pad), -3.4e-3 kg (silo_cold), -2.8e-3 kg
    (silo_cold_lag); m_res at P0 +0.021, +0.25 and +0.21 kg (gamma*_ref moves 8.1e-4,
    6.3e-3 and 5.2e-3 deg); gravity plus steering -6.2e-4, -4.3e-3 and -3.6e-3 m/s;
    max-Q 6.8e-6, 4.3e-5 and 3.6e-5 relative (time 8.6e-7, 5.6e-6, 4.7e-6)
    (docs/physics.md, "Convergence (planar)")."""
    r = reoptimised(name)
    conv = r.shipped.conv
    ra, rb = r.a, r.b
    assert ra.status == rb.status == "ok"
    assert _close(ra.payload_kg, rb.payload_kg, conv.rel_tol, conv.margin_floor_kg)
    assert ra.at_p0 is not None and rb.at_p0 is not None
    assert _close(ra.m_res_p0_kg, rb.m_res_p0_kg, conv.rel_tol, conv.margin_floor_kg)
    floor = _margin_floor_mps(ra.at_p0, conv.margin_floor_kg)
    assert _close(ra.dv_margin_p0_mps, rb.dv_margin_p0_mps, conv.rel_tol, floor)
    assert ra.gamma is not None and rb.gamma is not None
    assert abs(ra.gamma.gamma_star_rad - rb.gamma.gamma_star_rad) <= conv.gamma_resolution_rad
    la, lb = _recorded_budgets(r)
    for term in LOSS_TERMS:
        if term not in SPLIT_TERMS:
            va, vb = getattr(la, term), getattr(lb, term)
            assert _close(va, vb, conv.rel_tol, conv.loss_floor_mps), term
    ja = sum(getattr(la, term) for term in SPLIT_TERMS)
    jb = sum(getattr(lb, term) for term in SPLIT_TERMS)
    steering_tol = max(conv.rel_tol * max(abs(la.steering), abs(lb.steering)), conv.loss_floor_mps)
    assert abs(ja - jb) <= steering_tol
    assert ra.trace is not None and rb.trace is not None
    qa, qb = _max_q(ra.trace, r.shipped.checks), _max_q(rb.trace, r.shipped.checks)
    assert _close(qa.q_pa, qb.q_pa, conv.rel_tol, 0.0)
    assert _close(qa.t_s, qb.t_s, conv.rel_tol, 0.0)
    _assert_capped_where_pushed(ra.trace, rb.trace, conv, name)
