"""The shared gamma* sweep and the search bookkeeping (docs/physics.md, "Payload and
gamma* search" and "Shared budget"; plan section 8, "Search determinism and failure
penalty").

Most tests run the algorithms of ``launchsim.search`` on a toy problem with a closed-form
residual, m_res(P, gamma*) = A - K (gamma* - g0)^2 - S (P - P0) [kg], with failures
placed by the test, so every expected value (optimum, P1, P2, labels, penalties) is
computed here. The planar tests fly the real model (gate fork, pad and silo_cold of
experiments/silo_screening_2d.yaml) at the test budget, the shared search block with
search_rtol = TEST_SEARCH_RTOL (1e-9; CLAUDE.md: rtol <= 1e-9 in tests; plan section 8,
test_budget; final 1e-10 as shipped): the fast swapped-order test at two rung-2 points,
the slow ones through the whole search on a three-point grid.
"""

from __future__ import annotations

import ast
import dataclasses
import json
import math
import pickle
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from launchsim.cli import load_experiment
from launchsim.config import ChecksConfig, ResolvedExperiment, SearchConfig
from launchsim.guidance import GuidanceFailure
from launchsim.phases.planar import INSERTED_STATUS, OFF_TARGET_STATUS, SHORT_OF_ORBIT_STATUS
from launchsim.search import (
    FEASIBLE_POINT,
    FROM_FINAL_EVALUATION,
    FROM_RECORDED_RUN,
    GRID_MODE,
    INFEASIBLE_POINT,
    NO_ORBIT_STATUS,
    OK_STATUS,
    RULE_INFEASIBLE_POINT,
    SEARCH_FAILED_STATUS,
    SEARCH_MODE,
    SEARCH_SHORT_STATUS,
    PreludeFailure,
    RecordedRun,
    ResidualResult,
    SearchBudget,
    SearchContext,
    SearchFailed,
    WarmEntry,
    WarmStore,
    as_plain,
    centre_out_order,
    doubling_halves,
    final_verify,
    is_rule_infeasible,
    optimise_gamma,
    run_search,
)
from launchsim.vehicle import with_payload

A_KG = 3_000.0
"""Toy m_res at the optimum gamma* and the grid payload [kg]."""
K_KG_PER_DEG2 = 25.0
"""Toy curvature of m_res in gamma* [kg/deg^2] (the gate pad's is about 22)."""
S = 1.02
"""Toy |d m_res / d P| (the gate pad's is about 1.0 to 1.03)."""
P0_KG = 22_800.0
"""Toy grid payload [kg]."""
G0_DEG = 22.3
"""Toy optimum gamma* [deg], between grid points."""
TEST_SEARCH_RTOL = 1.0e-9
"""Search-mode rtol of the planar tests (CLAUDE.md: rtol <= 1e-9 in tests); the
convergence tests alone fly the shipped 1e-8 (amendment 3)."""
SMALL_GRID = {"gamma_grid_deg": (18.0, 26.0, 4.0), "gamma_refine_maxiter": 6}
"""A three-point gamma* grid (18, 22, 26 deg) and a short refine for whole planar
searches in tests."""
HEAVY_P0_KG = 30_000.0
"""A vehicle payload [kg] far above what the gate pad can carry (it still flies to the
cutoff on virtual propellant)."""
INDIRECT = (
    "LTG guess ladder exhausted (warm: not_direct_root: converged to a = 0.09, b = -2.8e-4 "
    "1/s (tau_c = 360 s) outside the direct-root window; physics: impact: dive)"
)
"""A nonconverged message in the form ``guidance.solve_ltg`` writes, with a rung that
converged to an indirect root."""


def _toy_residual(
    p_kg: float, g_rad: float, peak_deg: float, a_kg: float = A_KG, drift: float = 0.0
) -> float:
    """The toy m_res [kg] at payload p_kg [kg] and gamma* g_rad [rad]: A - K (gamma* -
    peak(P))^2 - S (P - P0), peak(P) = peak_deg - drift max(0, P - P0) [deg] (the
    optimum drifts above P0 only)."""
    peak = peak_deg - drift * max(0.0, p_kg - P0_KG)
    return a_kg - K_KG_PER_DEG2 * (math.degrees(g_rad) - peak) ** 2 - S * (p_kg - P0_KG)


@dataclass
class Toy:
    """A SearchProblem (and RecordingProblem) with the closed-form toy residual; a_kg is
    A, drift [deg/kg] moves the optimum with the payload above P0; ``fail(g_deg, near)`` returns
    the exception an evaluation at gamma* g_deg [deg] raises (None: it flies), near being
    the warm entry it starts from, every payload at or above fail_above_kg [kg] raises a
    typed impact, and so does every (payload [kg], mode) with ``fail_payload(P, mode)``
    true. m_of_p(P) [kg], when given, replaces the closed form (no gamma* dependence).
    dv_margin = m_res / 10. ``record`` stands in for the recorded run: inserted with the
    evaluation's figures when m_res >= 0, short_of_orbit carrying them otherwise, or
    ``record_fn(res)`` when given. Every call is logged in ``calls``."""

    budget: SearchBudget
    peak_deg: float = G0_DEG
    fail: object = None
    a_kg: float = A_KG
    drift: float = 0.0
    fail_above_kg: float = math.inf
    fail_payload: object = None
    m_of_p: object = None
    record_fn: object = None
    calls: list[tuple[float, float, str, WarmEntry | None]] = field(default_factory=list)

    @property
    def payload_kg(self) -> float:
        """P0 [kg]."""
        return P0_KG

    def record(self, res: ResidualResult) -> RecordedRun:
        """The toy recorded run of res (no trace)."""
        if self.record_fn is not None:
            return self.record_fn(res)  # type: ignore[operator,no-any-return]
        if res.m_res_kg >= 0.0:
            return RecordedRun(
                None,  # type: ignore[arg-type]
                INSERTED_STATUS,
                res.m_res_kg,
                res.dv_margin_mps,
                0.0,
                FROM_RECORDED_RUN,
            )
        return RecordedRun(
            None,  # type: ignore[arg-type]
            SHORT_OF_ORBIT_STATUS,
            res.m_res_kg,
            res.dv_margin_mps,
            math.nan,
            FROM_FINAL_EVALUATION,
        )

    def evaluate(
        self,
        payload_kg: float,
        gamma_star_rad: float,
        warm: WarmStore,
        mode: str,
        *,
        seed: WarmEntry | None = None,
    ) -> ResidualResult:
        """The toy rung 2 (the SearchProblem protocol)."""
        near = seed if seed is not None else warm.nearest(gamma_star_rad)
        self.calls.append((payload_kg, gamma_star_rad, mode, near))
        exc = None if self.fail is None else self.fail(math.degrees(gamma_star_rad), near)  # type: ignore[operator]
        heavy = payload_kg >= self.fail_above_kg
        if exc is None and (heavy or (self.fail_payload and self.fail_payload(payload_kg, mode))):  # type: ignore[operator]
            exc = GuidanceFailure("nonconverged", "physics: impact: stage 2 hit the ground")
        if exc is not None:
            raise exc
        if self.m_of_p is not None:
            m = float(self.m_of_p(payload_kg))  # type: ignore[operator]
        else:
            m = _toy_residual(payload_kg, gamma_star_rad, self.peak_deg, self.a_kg, self.drift)
        warm.add(WarmEntry(gamma_star_rad, payload_kg, None, None))
        rung = "warm" if near is not None else "physics"
        return ResidualResult(
            payload_kg, gamma_star_rad, m, m / 10.0, None, None, gamma_star_rad, rung, 0, 0, mode
        )


def _budget(**search: object) -> SearchBudget:
    """The shipped-default budget, with SearchConfig fields overridden."""
    return SearchBudget.from_config(SearchConfig(**search), ChecksConfig())


def _plain_text(obj: object) -> str:
    """A search result as JSON text (``as_plain``; NaN written as NaN, floats by repr), so
    two results compare equal exactly when every field is bitwise equal."""
    return json.dumps(as_plain(obj))


def _deg(xs: object) -> list[float]:
    return [round(math.degrees(x), 9) for x in xs]  # type: ignore[attr-defined]


def test_centre_out_order_and_halves() -> None:
    """Grid order from the midpoint outward, the upper side first on each ring; the final
    verification's half-widths double from final_bracket_kg's start up to its cap."""
    assert centre_out_order(15) == (7, 8, 6, 9, 5, 10, 4, 11, 3, 12, 2, 13, 1, 14, 0)
    assert centre_out_order(4) == (1, 2, 0, 3)
    assert centre_out_order(1) == (0,)
    assert doubling_halves(20.0, 1000.0) == (20.0, 40.0, 80.0, 160.0, 320.0, 640.0, 1000.0)
    assert doubling_halves(5.0, 5.0) == (5.0,)
    with pytest.raises(ValueError):
        doubling_halves(0.0, 10.0)


def test_budget_from_the_shared_config_and_tightened() -> None:
    """SearchBudget carries the SearchConfig in SI and radians (grid 8-36 deg step 2, 15
    points; payload half-widths 2 t x 2^k for k = 0..6; final 20 to 1000 kg), its
    budget_id, and ChecksConfig's flag threshold; tightening by 10 divides every
    tolerance (rtol, atol, the LTG acceptance, the delta, payload and gamma xtols) and
    keeps the rest."""
    cfg, checks = SearchConfig(), ChecksConfig()
    b = SearchBudget.from_config(cfg, checks)
    assert _deg(b.gamma_grid_rad) == [8.0 + 2.0 * i for i in range(15)]
    assert b.payload_halves_kg == tuple(2000.0 * 2.0**k for k in range(7))
    assert b.final_halves_kg == (20.0, 40.0, 80.0, 160.0, 320.0, 640.0, 1000.0)
    assert b.budget_id == cfg.budget_id()
    assert b.final_flag_rel == checks.search_final_flag_rel
    assert b.ltg_grid.max_rungs == cfg.ltg.grid_max_rungs
    assert b.ltg_search.max_rungs == b.ltg_final.max_rungs == 4
    assert b.ltg_final.fd_step == cfg.ltg.fd_step_final
    assert b.penalty_per_rad_kg == pytest.approx(cfg.penalty.per_deg_kg * 180.0 / math.pi)
    t = b.tightened(10.0)
    assert (t.search_rtol, t.final_rtol, t.final_atol_scale) == pytest.approx((1e-9, 1e-11, 0.1))
    assert t.search_atol_scale == b.search_atol_scale
    assert t.delta.xtol_rad == pytest.approx(1e-11)
    assert (t.payload_xtol_kg, t.final_payload_xtol_kg) == pytest.approx((0.05, 0.005))
    assert math.degrees(t.gamma_xatol_rad) == pytest.approx(0.001)
    assert (t.ltg_final.accept_r_m, t.ltg_final.accept_vr_mps) == pytest.approx((0.1, 1e-4))
    assert t.ltg_final.fd_step == b.ltg_final.fd_step
    assert t.delta.root_tol_rad == b.delta.root_tol_rad
    assert t.budget_id == f"{b.budget_id}:tightened/10"
    with pytest.raises(ValueError):
        b.tightened(1.0)


def test_warm_store_nearest_and_kick_cache() -> None:
    """The nearest gamma* wins, the latest entry on a tie; a kick point (or the
    infeasibility its making raised) is made once per key."""
    w = WarmStore()
    assert w.nearest(0.3) is None
    for g, d in ((0.25, 1.0), (0.5, 2.0), (0.5, 3.0), (0.125, 4.0)):
        w.add(WarmEntry(g, P0_KG, d, None))
    assert w.nearest(0.51).delta_rad == 3.0  # type: ignore[union-attr]
    assert w.nearest(0.375).delta_rad == 3.0  # type: ignore[union-attr]  # tie: the latest
    assert w.nearest(0.26).delta_rad == 1.0  # type: ignore[union-attr]
    made: list[int] = []

    def boom() -> object:
        made.append(1)
        raise PreludeFailure("no_liftoff", "too heavy")

    for _ in range(2):
        with pytest.raises(PreludeFailure, match="no_liftoff"):
            w.kick_point((1.0, SEARCH_MODE), boom)  # type: ignore[arg-type]
    assert made == [1]


def test_failures_are_typed_and_pickle() -> None:
    """SearchFailed and PreludeFailure pass every argument to RuntimeError (they pickle
    intact, the grid table included); an unknown kind is refused; the direct-root rule
    is recognised from the typed failure."""
    grid = (dataclasses.replace(_toy_point(), label=INFEASIBLE_POINT),)
    exc = pickle.loads(pickle.dumps(SearchFailed("edge", "on a bound", grid)))
    assert (exc.kind, exc.message) == ("edge", "on a bound")
    assert _plain_text(exc.grid) == _plain_text(grid)
    assert str(exc) == "edge: on a bound"
    pf = pickle.loads(pickle.dumps(PreludeFailure("no_liftoff", "m g > T")))
    assert (pf.kind, str(pf)) == ("no_liftoff", "no_liftoff: m g > T")
    with pytest.raises(ValueError):
        SearchFailed("nope")
    assert is_rule_infeasible(GuidanceFailure("nonconverged", INDIRECT))
    assert is_rule_infeasible(GuidanceFailure("not_direct_root", "b < 0"))
    assert not is_rule_infeasible(GuidanceFailure("nonconverged", "physics: impact: dive"))
    assert not is_rule_infeasible(PreludeFailure("no_liftoff"))


def _toy_point() -> object:
    """A GridPoint from a quick toy grid (for the pickling test)."""
    toy = Toy(_budget(gamma_grid_deg=(20.0, 24.0, 2.0)))
    return optimise_gamma(toy, WarmStore(), P0_KG, find_payload=False).grid[0]


def test_toy_sweep_is_deterministic_and_finds_the_closed_form() -> None:
    """optimise_gamma on the toy: the same inputs give an identical result (every field,
    as plain data), the grid is flown centre-out at P0 (22 deg first), the best grid
    point is 22 deg, P1 is the root at 22 deg, the refine finds g0 = 22.3 deg within the
    refine tolerance, and P2 is the root at g0, each within payload_xtol (P_lo <= root)."""
    b = _budget()
    runs = []
    for _ in range(2):
        toy = Toy(b)
        runs.append((optimise_gamma(toy, WarmStore(), P0_KG), toy.calls))
    (res, calls), (res2, calls2) = runs
    assert _plain_text(res) == _plain_text(res2)
    assert [(c[0], c[1], c[2]) for c in calls] == [(c[0], c[1], c[2]) for c in calls2]
    assert math.degrees(calls[0][1]) == pytest.approx(22.0) and calls[0][3] is None
    assert all(c[2] == GRID_MODE for c in calls[:15]) and all(c[0] == P0_KG for c in calls[:15])
    assert all(p.label == FEASIBLE_POINT for p in res.grid)
    assert math.degrees(res.gamma_best_grid_rad) == pytest.approx(22.0)
    root1 = P0_KG + (A_KG - K_KG_PER_DEG2 * (22.0 - G0_DEG) ** 2) / S
    assert res.p1 is not None and res.p2 is not None
    assert res.p1.payload_kg <= res.p1.root_kg + 1e-9
    assert res.p1.payload_kg == pytest.approx(root1, abs=b.payload_xtol_kg)
    assert math.degrees(res.gamma_star_rad) == pytest.approx(G0_DEG, abs=0.01)
    assert len(res.refine.windows) == 1
    assert _deg(res.refine.windows[0]) == pytest.approx([18.0, 26.0])
    assert res.refine_payload_kg == res.p1.payload_kg
    assert res.p2.payload_kg == pytest.approx(P0_KG + A_KG / S, abs=b.payload_xtol_kg)
    assert res.p2_minus_p1_kg == pytest.approx(K_KG_PER_DEG2 * 0.09 / S, abs=2 * b.payload_xtol_kg)
    assert res.flags == ()


def test_grid_labels_penalties_and_warm_retry() -> None:
    """Failures on the grid: gamma* <= 8 deg unattainable (infeasible, never retried),
    gamma* >= 32 deg with only an indirect LTG root (labelled not_direct_root), and 16
    deg nonconverged when started from above (18 deg) but solved when warm-started from
    14 deg (retried from that neighbour and flagged). Penalties are -(base + per_deg x
    distance to the nearest feasible grid point) [kg]."""

    def fail(g: float, near: WarmEntry | None) -> Exception | None:
        if g <= 8.0 + 1e-9:
            return GuidanceFailure("gamma_unattainable", "no sign change")
        if g >= 32.0 - 1e-9:
            return GuidanceFailure("nonconverged", INDIRECT)
        if abs(g - 16.0) < 1e-9 and near is not None and math.degrees(near.gamma_star_rad) > g:
            return GuidanceFailure("nonconverged", "physics: impact: dive")
        return None

    cfg = SearchConfig()
    toy = Toy(_budget(), fail=fail)
    res = optimise_gamma(toy, WarmStore(), P0_KG, find_payload=False)
    by_deg = {round(math.degrees(p.gamma_star_rad)): p for p in res.grid}
    assert by_deg[8].label == INFEASIBLE_POINT and not by_deg[8].retried
    for g in (32, 34, 36):
        assert by_deg[g].label == RULE_INFEASIBLE_POINT
        assert by_deg[g].objective_kg == pytest.approx(
            -(cfg.penalty.base_kg + cfg.penalty.per_deg_kg * (g - 30))
        )
    assert by_deg[8].objective_kg == pytest.approx(
        -(cfg.penalty.base_kg + 2.0 * cfg.penalty.per_deg_kg)
    )
    assert by_deg[16].label == FEASIBLE_POINT and by_deg[16].retried
    assert by_deg[16].m_res_kg == pytest.approx(_toy_residual(P0_KG, math.radians(16.0), G0_DEG))
    calls_at = [round(math.degrees(c[1])) for c in toy.calls if c[2] == GRID_MODE]
    assert calls_at.count(16) == 2 and calls_at.count(8) == 1 and calls_at.count(32) == 1
    retry = [c for c in toy.calls if round(math.degrees(c[1])) == 16][1]
    assert retry[3] is not None and math.degrees(retry[3].gamma_star_rad) == pytest.approx(14.0)
    assert any("warm retry" in f for f in res.flags)
    assert not any("direct-root rule" in f for f in res.flags)  # 32 deg is > 4 deg from 22


def test_edge_optimum_is_search_failed_edge() -> None:
    """A toy optimum beyond the grid (40 deg): the best grid point is the 36 deg bound, so
    optimise_gamma raises SearchFailed('edge') with the grid attached, and run_search
    reports status search_failed with NaN figures of merit (the experiment goes on)."""
    toy = Toy(_budget(), peak_deg=40.0)
    with pytest.raises(SearchFailed) as info:
        optimise_gamma(toy, WarmStore(), P0_KG)
    assert info.value.kind == "edge" and len(info.value.grid) == 15
    assert math.degrees(max(info.value.grid, key=lambda p: p.objective_kg).gamma_star_rad) == (
        pytest.approx(36.0)
    )
    rec = run_search(Toy(_budget(), peak_deg=40.0))  # type: ignore[arg-type]
    assert rec.status == SEARCH_FAILED_STATUS and rec.failure_kind == "edge"
    assert math.isnan(rec.payload_kg) and rec.final is None and len(rec.grid) == 15


def test_failing_refine_interval_scores_a_finite_penalty_without_warnings() -> None:
    """Every evaluation in (23, 27) deg fails (grid points 24 and 26 included): the grid
    scores them with finite penalties, the bounded Brent refine sees finite penalties
    too (never -inf, so scipy never warns: warnings are errors here), and gamma*_ref
    lands on the feasible side, at the boundary of the failing interval or at g0 when
    that is lower (22.3 deg)."""

    def fail(g: float, near: WarmEntry | None) -> Exception | None:
        if 23.0 < g < 27.0:
            return GuidanceFailure("nonconverged", "physics: impact: dive")
        return None

    toy = Toy(_budget(), fail=fail)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        res = optimise_gamma(toy, WarmStore(), P0_KG, find_payload=False)
    labels = [e[2] for e in res.refine.evals]
    assert INFEASIBLE_POINT in labels and FEASIBLE_POINT in labels
    assert all(math.isfinite(e[1]) for e in res.refine.evals)
    assert math.degrees(res.gamma_star_rad) == pytest.approx(G0_DEG, abs=0.01)
    assert res.refine.objective_kg == pytest.approx(
        _toy_residual(P0_KG, res.gamma_star_rad, G0_DEG), abs=1e-6
    )


def test_infeasible_grid_is_search_failed_grid() -> None:
    """No grid point flies: SearchFailed('grid') with every point labelled."""

    def fail(g: float, near: WarmEntry | None) -> Exception:
        return PreludeFailure("no_liftoff", "too heavy")

    with pytest.raises(SearchFailed) as info:
        optimise_gamma(Toy(_budget(), fail=fail), WarmStore(), P0_KG)
    assert info.value.kind == "grid"
    assert {p.label for p in info.value.grid} == {INFEASIBLE_POINT}


def test_refine_onto_a_grid_bound_is_search_failed_edge() -> None:
    """An optimum that drifts with the payload, peak(P) = 9.6 deg - 1e-3 deg/kg (P - P0)
    above P0:
    the best grid point at P0 is 10 deg (interior), but at P1 (about P0 + 2.7 t) the
    optimum is about 6.9 deg, beyond the 8 deg bound, so the refine converges onto the
    bound: SearchFailed('edge') with the grid attached, and run_search reports
    search_failed(edge) with the grid table."""
    toy = Toy(_budget(), peak_deg=9.6, drift=1e-3)
    with pytest.raises(SearchFailed) as info:
        optimise_gamma(toy, WarmStore(), P0_KG)
    assert info.value.kind == "edge" and len(info.value.grid) == 15
    best = max(info.value.grid, key=lambda p: p.objective_kg)
    assert math.degrees(best.gamma_star_rad) == pytest.approx(10.0)
    rec = run_search(Toy(_budget(), peak_deg=9.6, drift=1e-3))  # type: ignore[arg-type]
    assert rec.status == SEARCH_FAILED_STATUS and rec.failure_kind == "edge"
    assert len(rec.grid) == 15 and math.isnan(rec.payload_kg)


def test_vehicle_too_heavy_at_p0_is_no_orbit_not_nan() -> None:
    """Every evaluation at P >= 1 t fails (typed impact) and m_res(0, gamma*) = -100 -
    K (gamma* - g0)^2 kg: the grid at P0 = 22.8 t has no feasible point, so it is re-run
    at P = 0 (flagged), and the payload searches and the final verification report
    no_orbit with P* = 0 and the shortfall -dv_margin(0) = 10 m/s at gamma*_ref = g0
    (dv_margin = m_res / 10 in the toy). The recorded run stops short of the cutoff and
    carries the signed m_res and dv_margin of the final evaluation; rung 2 at P0 cannot
    fly (at_p0 None, flagged)."""
    toy = Toy(_budget(), a_kg=-S * P0_KG - 100.0, fail_above_kg=1000.0)
    rec = run_search(toy)  # type: ignore[arg-type]
    assert rec.status == NO_ORBIT_STATUS and rec.failure_kind is None
    assert rec.payload_kg == 0.0
    assert rec.gamma is not None and rec.final is not None and rec.final.payload is not None
    assert rec.gamma.grid_payload_kg == 0.0
    assert all(p.label == FEASIBLE_POINT for p in rec.grid)
    assert any("re-run at P = 0" in f for f in rec.flags)
    assert math.degrees(rec.gamma.gamma_star_rad) == pytest.approx(G0_DEG, abs=0.01)
    at, recorded = rec.final.at_final, rec.final.recorded
    assert at.payload_kg == 0.0 and at.m_res_kg == pytest.approx(-100.0, abs=0.01)
    assert rec.final.payload.dv_shortfall_mps == -at.dv_margin_mps
    assert rec.final.payload.dv_shortfall_mps == pytest.approx(10.0, abs=1e-3)
    assert recorded.figures_from == FROM_FINAL_EVALUATION
    assert (recorded.m_res_kg, recorded.dv_margin_mps) == (at.m_res_kg, at.dv_margin_mps)
    assert rec.at_p0 is None and math.isnan(rec.m_res_p0_kg)
    assert any(f.startswith("rung 2 at P0") for f in rec.flags)


def test_signed_figures_at_the_vehicle_payload() -> None:
    """The rung-2 figures at P0 reach the record signed. Payload search: at_p0 is one
    final-mode evaluation at (P0, gamma*_ref) after the final verification, m_res =
    A - K (gamma*_ref - g0)^2. figure_of_merit residual: at_p0 is the final evaluation;
    A = 3000 kg gives status ok, A = -500 kg gives status short_of_orbit with m_res = -500
    and dv_margin = -50 m/s carried into the recorded run (never clipped to 0)."""
    toy = Toy(_budget())
    rec = run_search(toy)  # type: ignore[arg-type]
    assert rec.status == OK_STATUS and rec.at_p0 is not None and rec.gamma is not None
    assert toy.calls[-1][:3] == (P0_KG, rec.gamma.gamma_star_rad, "final")
    assert rec.m_res_p0_kg == pytest.approx(A_KG, abs=0.01)
    assert rec.dv_margin_p0_mps == pytest.approx(A_KG / 10.0, abs=1e-3)
    for a_kg, status in ((A_KG, OK_STATUS), (-500.0, SEARCH_SHORT_STATUS)):
        rec = run_search(Toy(_budget(figure_of_merit="residual"), a_kg=a_kg))  # type: ignore[arg-type]
        assert rec.status == status and rec.final is not None
        assert rec.at_p0 is rec.final.at_final and rec.final.at_final.payload_kg == P0_KG
        assert rec.m_res_p0_kg == pytest.approx(a_kg, abs=0.01)
        assert rec.dv_margin_p0_mps == pytest.approx(a_kg / 10.0, abs=1e-3)
        recorded = rec.final.recorded
        assert (recorded.m_res_kg, recorded.dv_margin_mps) == (
            rec.m_res_p0_kg,
            rec.dv_margin_p0_mps,
        )
        assert recorded.figures_from == (FROM_RECORDED_RUN if a_kg > 0.0 else FROM_FINAL_EVALUATION)


def test_a_failed_payload_search_keeps_the_grid_table() -> None:
    """Every payload above P0 + 1 kg fails, so P1's high end cannot fly and its backoffs
    run out: SearchFailed('bracket') carries the evaluated grid, and so does the
    search_failed record."""
    toy = Toy(_budget(), fail_above_kg=P0_KG + 1.0)
    with pytest.raises(SearchFailed) as info:
        optimise_gamma(toy, WarmStore(), P0_KG)
    assert info.value.kind == "bracket" and len(info.value.grid) == 15
    rec = run_search(Toy(_budget(), fail_above_kg=P0_KG + 1.0))  # type: ignore[arg-type]
    assert rec.status == SEARCH_FAILED_STATUS and rec.failure_kind == "bracket"
    assert len(rec.grid) == 15 and all(p.label == FEASIBLE_POINT for p in rec.grid)


def test_refine_with_every_evaluation_failing_falls_back_to_the_grid() -> None:
    """Only the grid points fly (every off-grid gamma* fails): the refine scores finite
    penalties (no warning), falls back to the best grid point (22 deg), flags it, and
    records a NaN objective (that point's m_res is known only at P0, not at P1)."""

    def fail(g: float, near: WarmEntry | None) -> Exception | None:
        on_grid = abs(g - round(g)) < 1e-9 and round(g) % 2 == 0
        return None if on_grid else GuidanceFailure("nonconverged", "physics: impact: dive")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        res = optimise_gamma(Toy(_budget(), fail=fail), WarmStore(), P0_KG)
    assert res.gamma_star_rad == res.gamma_best_grid_rad
    assert math.degrees(res.gamma_star_rad) == pytest.approx(22.0)
    assert math.isnan(res.refine.objective_kg)
    assert {e[2] for e in res.refine.evals} == {INFEASIBLE_POINT}
    assert any("falls back to the best grid point" in f for f in res.flags)
    assert res.p2 is not None and res.p1 is not None


def _needs_seed(need: dict[int, tuple[int, ...]]) -> object:
    """A toy failure rule: the grid point k [deg] in need fails nonconverged unless its
    warm start comes from one of the grid points need[k] [deg] or from k itself (a
    solution at the same gamma*, as in the payload searches)."""

    def fail(g: float, near: WarmEntry | None) -> Exception | None:
        k = round(g)
        src = None if near is None else round(math.degrees(near.gamma_star_rad))
        if abs(g - k) < 1e-9 and k in need and src not in (*need[k], k):
            return GuidanceFailure("nonconverged", "physics: impact: dive")
        return None

    return fail


def test_grid_retry_repeats_until_no_new_point_solves() -> None:
    """22 deg converges only from 20 or 24, 24 only from 26 and 20 only from 18. The
    first pass fails at 22, 24 and 20 (cold); the first retry pass solves 24 (from 26)
    and 20 (from 18) after 22 was visited, so a second pass retries 22 (from 20) and
    solves it: every point is feasible, the best grid point is 22 deg (never displaced
    by a stale penalty), and the three retried points are flagged."""
    toy = Toy(_budget(), fail=_needs_seed({22: (20, 24), 24: (26,), 20: (18,)}))
    res = optimise_gamma(toy, WarmStore(), P0_KG, find_payload=False)
    by_deg = {round(math.degrees(p.gamma_star_rad)): p for p in res.grid}
    assert all(p.label == FEASIBLE_POINT for p in res.grid)
    assert {g for g, p in by_deg.items() if p.retried} == {20, 22, 24}
    assert math.degrees(res.gamma_best_grid_rad) == pytest.approx(22.0)
    calls_at = [round(math.degrees(c[1])) for c in toy.calls if c[2] == GRID_MODE]
    assert (calls_at.count(22), calls_at.count(24), calls_at.count(20)) == (2, 2, 2)
    retry_22 = [c for c in toy.calls if round(math.degrees(c[1])) == 22 and c[2] == GRID_MODE]
    assert math.degrees(retry_22[1][3].gamma_star_rad) == pytest.approx(20.0)  # type: ignore[union-attr]
    assert any("warm retry" in f for f in res.flags)


def test_refine_capped_by_the_shifted_window_is_flagged() -> None:
    """An optimum drifting with the payload above P0, peak(P) = 30 deg - 8e-3 deg/kg (P -
    P0): the
    grid at P0 picks 30 deg, P1 = P0 + 1,087 kg there, where the optimum is 21.3 deg.
    The refine's first window (26, 34) deg ends at its lower edge, the shifted window
    (about 22, 30) deg ends at its lower edge again: gamma*_ref is capped by the window,
    which is flagged refine_capped, and the shift flag names both results."""
    b = _budget()
    res = optimise_gamma(Toy(b, peak_deg=30.0, drift=8e-3), WarmStore(), P0_KG)
    assert math.degrees(res.gamma_best_grid_rad) == pytest.approx(30.0)
    assert res.refine.shifted and len(res.refine.windows) == 2
    lo2 = res.refine.windows[1][0]
    assert res.gamma_star_rad - lo2 <= b.gamma_xatol_rad
    shift = [f for f in res.flags if f.startswith("refine: the first optimum")]
    assert len(shift) == 1 and f"{res.gamma_star_rad:.9g}" in shift[0]
    assert any(f.startswith("refine_capped:") for f in res.flags)


def test_payload_search_backoffs_are_flagged() -> None:
    """P1's high end at 26.8 t fails (search mode): the backoff is flagged with the
    failed payload and its failure kind, and P1 still finds its root."""
    toy = Toy(_budget(), fail_payload=lambda p, mode: mode == SEARCH_MODE and p == 26_800.0)
    res = optimise_gamma(toy, WarmStore(), P0_KG)
    assert res.p1 is not None and res.p1.backoffs == 1
    flag = [f for f in res.flags if f.startswith("P1_backoff:")]
    assert len(flag) == 1 and "26800" in flag[0] and "nonconverged" in flag[0]
    root1 = P0_KG + (A_KG - K_KG_PER_DEG2 * (22.0 - G0_DEG) ** 2) / S
    assert res.p1.payload_kg == pytest.approx(root1, abs=_budget().payload_xtol_kg)
    assert not any(f.startswith("P2_backoff:") for f in res.flags)


R_KG = 25_000.3
"""Root [kg] of the toy m_res(P) = S (R_KG - P) of the final-verification tests."""


def _linear(p: float) -> float:
    return S * (R_KG - p)


def test_final_verification_backs_off_toward_the_hint_and_flags() -> None:
    """The final verification from the search payload 25,000 kg (m_res = S (R - P)):
    the low end 24,980 kg fails in final mode with nothing lighter flown, so it backs off
    halfway toward the hint (24,990 kg, never toward P = 0), flagged final_backoff with
    the failure; P_final is the verified payload below R within the final xtol. From a
    hint 100 kg low the bracket expands (search_final_mismatch) and the 100 kg gap is
    flagged search_vs_final_payload."""
    b = _budget()
    toy = Toy(b, m_of_p=_linear, fail_payload=lambda p, mode: mode == "final" and p == 24_980.0)
    fin = final_verify(toy, 0.4, 25_000.0, WarmStore())
    assert fin.payload is not None and fin.payload.backoffs == 1
    assert [e.payload_kg for e in fin.payload.evals[:2]] == [24_980.0, 24_990.0]
    assert any(f.startswith("final_backoff:") and "24980" in f for f in fin.flags)
    assert 0.0 <= R_KG - fin.payload_kg < b.final_payload_xtol_kg / S
    assert fin.payload_kg == fin.at_final.payload_kg == fin.payload.at_payload.payload_kg
    fin = final_verify(Toy(b, m_of_p=_linear), 0.4, R_KG - 100.0, WarmStore())
    assert fin.payload is not None and fin.payload.expansions >= 1
    assert any(f.startswith("search_final_mismatch:") for f in fin.flags)
    assert any(f.startswith("search_vs_final_payload:") for f in fin.flags)
    assert 0.0 <= R_KG - fin.payload_kg < b.final_payload_xtol_kg / S


def _recorded(status: str, m_res_kg: float, figures_from: str) -> object:
    """A record_fn returning a fixed toy recorded run."""

    def fn(res: ResidualResult) -> RecordedRun:
        return RecordedRun(None, status, m_res_kg, res.dv_margin_mps, 0.0, figures_from)  # type: ignore[arg-type]

    return fn


def test_final_verification_failures_are_typed() -> None:
    """No final bracket within 1 t of the hint: SearchFailed('final_bracket'). A recorded
    run that disagrees with its evaluation: SearchFailed('final_run') when it ends
    off_target, when it keeps m_res >= final_payload_xtol_kg, when it stops short of the
    cutoff although its evaluation has m_res >= 0, and when a no_orbit evaluation (m_res
    < 0 at P = 0) is recorded as reaching the cutoff."""
    b = _budget()
    with pytest.raises(SearchFailed) as info:
        final_verify(Toy(b, m_of_p=_linear), 0.4, R_KG - 5_000.0, WarmStore())
    assert info.value.kind == "final_bracket"
    bad = (
        _recorded(OFF_TARGET_STATUS, 0.0, FROM_RECORDED_RUN),
        _recorded(INSERTED_STATUS, b.final_payload_xtol_kg, FROM_RECORDED_RUN),
        _recorded(SHORT_OF_ORBIT_STATUS, -1.0, FROM_FINAL_EVALUATION),
    )
    for record_fn in bad:
        with pytest.raises(SearchFailed) as info:
            final_verify(Toy(b, m_of_p=_linear, record_fn=record_fn), 0.4, 25_000.0, WarmStore())
        assert info.value.kind == "final_run"
    toy = Toy(
        b,
        m_of_p=lambda p: -100.0 - p,
        record_fn=_recorded(INSERTED_STATUS, 0.0, FROM_RECORDED_RUN),
    )
    with pytest.raises(SearchFailed) as info:
        final_verify(toy, 0.4, 0.0, WarmStore())
    assert info.value.kind == "final_run"


def test_final_bisection_keeps_the_residual_rule() -> None:
    """m_res(P) = -10 tanh((P - R)/0.05 kg) - 1e-3 (P - R) kg, from a search payload 3 kg
    below R: the secant slope over the +/-20 kg bracket is about 0.5 kg/kg but the local
    slope at R is 200 kg/kg, so brentq's P_lo keeps m_res >= final_payload_xtol_kg; the
    logged bracket is then bisected (flagged) until 0 <= m_res(P_final) <
    final_payload_xtol_kg, and P_final is still the largest evaluated payload with m_res
    >= 0."""
    b = _budget()

    def steep(p: float) -> float:
        return -10.0 * math.tanh((p - R_KG) / 0.05) - 1e-3 * (p - R_KG)

    fin = final_verify(Toy(b, m_of_p=steep), 0.4, R_KG - 3.0, WarmStore())
    assert any(f.startswith("final: m_res at brentq's P_lo") for f in fin.flags)
    assert 0.0 <= fin.at_final.m_res_kg < b.final_payload_xtol_kg
    assert fin.payload is not None
    ok = [e for e in fin.payload.evals if e.ok and e.m_res_kg >= 0.0]
    assert fin.payload_kg == max(e.payload_kg for e in ok) == fin.payload.payload_kg
    assert fin.recorded.m_res_kg == fin.at_final.m_res_kg


def test_whole_toy_searches_do_not_depend_on_the_run_order() -> None:
    """Two toy runs whose grid convergence depends on their warm starts (different
    optima and retry rules), searched whole (grid, P1, refine, P2, final verification,
    rung 2 at P0) in both orders: identical records as plain data and identical
    evaluation sequences (no state shared between runs)."""
    b = _budget()

    def make() -> dict[str, Toy]:
        return {
            "a": Toy(b, fail=_needs_seed({22: (20, 24), 24: (26,)})),
            "b": Toy(b, peak_deg=19.4, a_kg=2_500.0, fail=_needs_seed({18: (16,), 20: (22,)})),
        }

    first, second = make(), make()
    rec1 = {n: run_search(first[n]) for n in ("a", "b")}  # type: ignore[arg-type]
    rec2 = {n: run_search(second[n]) for n in ("b", "a")}  # type: ignore[arg-type]
    for n in ("a", "b"):
        assert rec1[n].status == OK_STATUS
        assert _plain_text(rec1[n]) == _plain_text(rec2[n])
        assert first[n].calls == second[n].calls


# --------------------------------------------------------------- the real planar model


@pytest.fixture(scope="module")
def silo_2d(repo_root: Path) -> ResolvedExperiment:
    """experiments/silo_screening_2d.yaml, resolved (gate fork, shared blocks)."""
    return load_experiment(repo_root / "experiments" / "silo_screening_2d.yaml")


def _shipped_contexts(exp: ResolvedExperiment) -> dict[str, SearchContext]:
    """SearchContexts of pad and silo_cold at the experiment's shipped budget."""
    runs = exp.runs
    return {
        n: SearchContext.from_run(runs[n].run, runs[n].to_vehicle()) for n in ("pad", "silo_cold")
    }


def _contexts(exp: ResolvedExperiment, **search: object) -> dict[str, SearchContext]:
    """SearchContexts of pad and silo_cold at the test budget: the shared search block
    with search_rtol = TEST_SEARCH_RTOL (CLAUDE.md: rtol <= 1e-9 in tests) and the
    SearchConfig fields in search overridden."""
    base = exp.baseline.run
    assert base.planar is not None
    cfg = base.planar.search.model_copy(update={"search_rtol": TEST_SEARCH_RTOL, **search})
    budget = SearchBudget.from_config(cfg, base.planar.checks)
    return {n: dataclasses.replace(c, budget=budget) for n, c in _shipped_contexts(exp).items()}


def test_context_from_the_resolved_runs(silo_2d: ResolvedExperiment) -> None:
    """SearchContext.from_run: the pad has no track, silo_cold a 100 m vertical track;
    omega_p = omega_E cos(28.5 deg) at azimuth 90 (the value the site computes); the
    target radius is R_E + 200 km; the integrator settings are the run's (rtol =
    final_rtol); the budget id is the experiment's; the grid runs at the vehicle's
    payload; the shipped search mode is rtol 1e-8 with atol x 10 (no integration here),
    the tests' search mode rtol TEST_SEARCH_RTOL."""
    ctx = _shipped_contexts(silo_2d)
    site = silo_2d.baseline.run.site
    assert ctx["pad"].track is None and ctx["silo_cold"].track is not None
    assert ctx["silo_cold"].track.length_m == pytest.approx(100.0)  # type: ignore[union-attr]
    for c in ctx.values():
        assert c.env.omega_p_rads == site.omega_p_rads
        assert c.target.r_m == silo_2d.baseline.run.planar.target_orbit.radius_m  # type: ignore[union-attr]
        assert c.settings.rtol == c.budget.final_rtol == 1e-10
        assert c.budget.budget_id == silo_2d.baseline.run.planar.search.budget_id()  # type: ignore[union-attr]
        assert c.payload_kg == pytest.approx(22_800.0)
        assert c.settings_for(SEARCH_MODE).rtol == 1e-8
        assert c.settings_for(SEARCH_MODE).atol_scale == 10.0
        assert not c.settings_for(SEARCH_MODE).dense_output
    for c in _contexts(silo_2d).values():
        assert c.settings_for(SEARCH_MODE).rtol == TEST_SEARCH_RTOL
        assert c.settings_for(GRID_MODE).rtol == TEST_SEARCH_RTOL
        assert c.settings_for("final").rtol == 1e-10


def test_swapped_run_order_gives_identical_evaluations(silo_2d: ResolvedExperiment) -> None:
    """Two runs, each with its own WarmStore, evaluated pad-then-silo and silo-then-pad at
    (22.8 t, 20 deg) and (22.8 t, 22 deg, warm from 20): every m_res, dv_margin, delta and
    LTG pair is bitwise identical in both orders (no state leaks between runs)."""
    ctx = _contexts(silo_2d)
    gammas = (math.radians(20.0), math.radians(22.0))

    def fly(name: str) -> list[tuple[float, ...]]:
        warm, out = WarmStore(), []
        for g in gammas:
            r = ctx[name].evaluate(P0_KG, g, warm, SEARCH_MODE)
            assert r.ltg is not None and r.delta_rad is not None
            out.append((r.m_res_kg, r.dv_margin_mps, r.delta_rad, *r.ltg))
        return out

    first = {"pad": fly("pad"), "silo_cold": fly("silo_cold")}
    second = {"silo_cold": fly("silo_cold"), "pad": fly("pad")}
    assert first == second
    # wiring only (no direction asserted): the two runs are different problems
    assert first["silo_cold"] != first["pad"]
    assert all(math.isfinite(v) for run in first.values() for row in run for v in row)


def test_a_warm_store_serves_one_problem(silo_2d: ResolvedExperiment) -> None:
    """A WarmStore is bound to the first problem that evaluates with it: a second
    context (another run, or the same run tightened) raises ValueError before it flies
    anything, so no context reuses another's cached kick point."""
    ctx = _shipped_contexts(silo_2d)
    warm = WarmStore()
    warm.claim(ctx["pad"])
    warm.claim(ctx["pad"])
    g = math.radians(20.0)
    with pytest.raises(ValueError, match="another search problem"):
        ctx["silo_cold"].evaluate(P0_KG, g, warm, SEARCH_MODE)
    conv = silo_2d.baseline.run.planar.checks.convergence  # type: ignore[union-attr]
    with pytest.raises(ValueError, match="another search problem"):
        ctx["pad"].tightened(conv).evaluate(P0_KG, g, warm, SEARCH_MODE)
    assert warm.entries == [] and warm.kicks == {}


@pytest.mark.slow
def test_residual_figure_short_of_orbit_is_signed(silo_2d: ResolvedExperiment) -> None:
    """figure_of_merit residual on the pad with the vehicle payload set to 30 t, far above
    what it can carry (three-point grid 18, 22, 26 deg; refine at most 6 evaluations): no
    payload searches (P1, P2 None), the refine runs at P0, and the final verification is
    one final-mode evaluation at P0 and its recorded run. m_res < 0 there, so the status
    is short_of_orbit, the recorded run stops short of the cutoff (the real propellant
    runs out), and the negative m_res and dv_margin of the final evaluation reach the
    record unchanged (at_p0, and the recorded run with figures_from final_evaluation and
    a NaN cutoff-state difference), never the ~0 left at depletion."""
    pad = _contexts(silo_2d, figure_of_merit="residual", **SMALL_GRID)["pad"]
    ctx = dataclasses.replace(pad, vehicle=with_payload(pad.vehicle, HEAVY_P0_KG))
    rec = run_search(ctx)
    assert rec.status == SEARCH_SHORT_STATUS and rec.gamma is not None and rec.final is not None
    assert rec.gamma.p1 is None and rec.gamma.p2 is None
    assert rec.gamma.refine_payload_kg == HEAVY_P0_KG
    assert rec.final.payload is None and math.isnan(rec.payload_kg)
    at, recorded = rec.final.at_final, rec.final.recorded
    assert at.payload_kg == HEAVY_P0_KG and at.mode == "final"
    assert at.m_res_kg < 0.0 and at.dv_margin_mps < 0.0
    assert rec.at_p0 is at
    assert (rec.m_res_p0_kg, rec.dv_margin_p0_mps) == (at.m_res_kg, at.dv_margin_mps)
    assert recorded.status == SHORT_OF_ORBIT_STATUS
    assert recorded.figures_from == FROM_FINAL_EVALUATION
    assert (recorded.m_res_kg, recorded.dv_margin_mps) == (at.m_res_kg, at.dv_margin_mps)
    assert math.isnan(recorded.cut_state_rel_diff)


@pytest.mark.slow
def test_swapped_order_whole_searches_are_identical(silo_2d: ResolvedExperiment) -> None:
    """The whole search (grid, P1, refine, P2, final verification, the recorded run and
    rung 2 at P0) of pad and silo_cold on a three-point grid (18, 22, 26 deg; refine at
    most 6 evaluations), run in both orders: the search records are identical as plain
    data."""
    ctx = _contexts(silo_2d, **SMALL_GRID)
    first = {n: run_search(ctx[n]) for n in ("pad", "silo_cold")}
    second = {n: run_search(ctx[n]) for n in ("silo_cold", "pad")}
    for n in first:
        assert _plain_text(first[n]) == _plain_text(second[n])
        assert first[n].status == "ok" and first[n].failure_kind is None
        assert first[n].at_p0 is not None


def test_search_module_has_docstrings(repo_root: Path) -> None:
    """Every public function, class and method of search.py has a docstring
    (tests/test_scaffold.py's module list does not include it yet)."""
    path = repo_root / "src" / "launchsim" / "search.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assert ast.get_docstring(tree)
    missing = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.ClassDef) and not node.name.startswith("_"):
            if ast.get_docstring(node) is None:
                missing.append(node.name)
            if isinstance(node, ast.ClassDef):
                missing += [
                    f"{node.name}.{m.name}"
                    for m in node.body
                    if isinstance(m, ast.FunctionDef)
                    and not m.name.startswith("_")
                    and ast.get_docstring(m) is None
                ]
    assert not missing, missing
