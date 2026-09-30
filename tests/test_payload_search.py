"""Rung 3, the payload capacity (docs/physics.md, "Figures of merit (planar)", "Virtual
propellant" and "Payload and gamma* search"; plan section 8).

- Closed form: a toy two-stage rocket (c = 3000 m/s both stages, zero gravity, vacuum,
  thrust along v) flown with ``integrate_phase`` and ``rhs_planar`` to a speed target V*
  with virtual stage-2 propellant; ``payload_capacity`` must find the P* that solves
  c ln(m0/m1) + c ln(m2/(m_d2 + P)) = V* (brentq here) within the payload xtol, and
  report no_orbit with the shortfall V* - D_id(0) when even P = 0 misses V*.
- The bracket logic on analytic m_res(P): expansions, the backoff from an infeasible
  end, and the SearchFailed kinds.
- The planar model (gate fork, pad, gamma* = 20 deg, at the test budget: the shared
  search block with search_rtol = TEST_SEARCH_RTOL, 1e-9, CLAUDE.md's test rtol; final
  1e-10 as shipped): m_res(P) strictly decreasing and continuous where the real
  propellant would run out (virtual propellant), the final verification's recorded run
  (inserted, 0 <= m_res < final_payload_xtol_kg, the same trajectory as the evaluation
  it re-flies, the real depletion event armed), and a recorded run short of orbit that
  carries the signed figures of its evaluation.
- Slow: a typed failure beyond the mass floor; the nested solution against the joint
  3-equation root; a vehicle too heavy for any grid point at P0 reported as no_orbit.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pytest
from scipy.optimize import brentq

from launchsim.cli import load_experiment
from launchsim.config import ChecksConfig, SearchConfig
from launchsim.constants import G0_MPS2
from launchsim.dynamics import (
    PLANAR_LAYOUT,
    PLANAR_STATE_NAMES,
    ConstantGravity,
    PlanarParams,
    rhs_planar,
    vacuum_atmosphere,
)
from launchsim.guidance import AlongVrel, GuidanceFailure
from launchsim.phases import EventSpec, IntegratorSettings, PhaseSpec, integrate_phase
from launchsim.phases.engine import atol_for, ev_propellant
from launchsim.phases.planar import SHORT_OF_ORBIT_STATUS, planar_rest_state
from launchsim.search import (
    FINAL_MODE,
    FROM_FINAL_EVALUATION,
    NO_ORBIT_STATUS,
    OK_STATUS,
    SEARCH_MODE,
    FinalResult,
    ResidualResult,
    SearchBudget,
    SearchContext,
    SearchFailed,
    WarmEntry,
    WarmStore,
    final_residual,
    final_verify,
    joint_root_crosscheck,
    payload_capacity,
    payload_root,
    run_search,
)
from launchsim.vehicle import Engine, Stage, Startup

C_MPS = 3000.0
"""Exhaust velocity of both toy stages [m/s]."""
M_D1, M_P1, T1 = 200.0, 800.0, 15_000.0
"""Toy stage 1: dry and propellant mass [kg], vacuum thrust [N]."""
M_D2, M_P2, T2 = 150.0, 150.0, 3_000.0
"""Toy stage 2: dry and propellant mass [kg], vacuum thrust [N] (virtual propellant
beyond m_p2 in the search)."""
GAMMA_20_RAD = math.radians(20.0)
TEST_SEARCH_RTOL = 1.0e-9
"""Search-mode rtol of the planar tests (CLAUDE.md: rtol <= 1e-9 in tests); the
convergence tests alone fly the shipped 1e-8 (amendment 3)."""
SHORT_BY_KG = 3_000.0
"""How far [kg] above the payload root at 20 deg the short-of-orbit test flies."""
STAGE2_EXTRA_DRY_KG = 32_000.0
"""Stage-2 dry mass [kg] added in the slow no_orbit test: the gate pad cannot then reach
the orbit even empty, and no gamma* grid point flies at P0."""


def _stage(name: str, dry: float, prop: float, thrust: float) -> Stage:
    engine = Engine(thrust_vac_N=thrust, isp_vac_s=C_MPS / G0_MPS2, exit_area_m2=0.0)
    return Stage(name, dry, prop, engine, 1, Startup("step"), 0.0)


def _closed_form_dv(p_kg: float) -> float:
    """D_id(P) = c ln(m0/m1) + c ln(m2/(m_d2 + P)) [m/s] of the toy."""
    m0 = M_D1 + M_P1 + M_D2 + M_P2 + p_kg
    m1 = m0 - M_P1
    m2 = m1 - M_D1
    return C_MPS * math.log(m0 / m1) + C_MPS * math.log(m2 / (M_D2 + p_kg))


@dataclass
class SpeedTargetToy:
    """The toy as a SearchProblem: zero gravity, vacuum, thrust along v from rest (radial
    at V = 0), stage 1 to its propellant event, the dry mass dropped, stage 2 to the speed
    target V* [m/s] with no depletion event (virtual propellant) and a mass floor at half
    m_d2 + P. m_res = m_c - (m_d2 + P), dv_margin = c ln(m_c/(m_d2 + P))."""

    v_target_mps: float
    budget: SearchBudget = field(
        default_factory=lambda: SearchBudget.from_config(SearchConfig(), ChecksConfig())
    )
    settings: IntegratorSettings = field(default_factory=lambda: IntegratorSettings(rtol=1e-10))

    @property
    def payload_kg(self) -> float:
        """P0 [kg] (unused by the payload tests)."""
        return 50.0

    def _params(self, stage: Stage) -> PlanarParams:
        return PlanarParams(
            ConstantGravity(0.0),
            0.0,
            0.0,
            stage.schedule(0.0),
            None,
            vacuum_atmosphere,
            AlongVrel(),
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
        """The toy rung 2 (gamma* plays no part)."""
        s1, s2 = _stage("stage1", M_D1, M_P1, T1), _stage("stage2", M_D2, M_P2, T2)
        atol = atol_for(PLANAR_STATE_NAMES)
        m0 = M_D1 + M_P1 + M_D2 + M_P2 + payload_kg
        y = planar_rest_state(0.0, m0, 0.0)
        p1 = self._params(s1)
        burn1 = PhaseSpec(
            "BURN", 0, 0.0, None, rhs_planar, p1, (ev_propellant(m0 - M_P1, PLANAR_LAYOUT),), atol
        )
        r1 = integrate_phase(burn1, y, self.settings)
        y = r1.y_end.copy()
        y[PLANAR_LAYOUT.index("m_kg")] -= M_D1
        m_empty = M_D2 + payload_kg
        v_star = self.v_target_mps
        target = EventSpec("speed", lambda t, yy: float(yy[2]) - v_star, True, +1, 1e-9)
        floor = EventSpec("mass_floor", lambda t, yy: float(yy[4]) - 0.5 * m_empty, True, -1, 1e-6)
        p2 = PlanarParams(
            ConstantGravity(0.0),
            0.0,
            0.0,
            s2.schedule(r1.t_end),
            None,
            vacuum_atmosphere,
            AlongVrel(),
        )
        burn2 = PhaseSpec("BURN", 1, r1.t_end, None, rhs_planar, p2, (target, floor), atol)
        r2 = integrate_phase(burn2, y, self.settings)
        if r2.ended_by != "speed":
            raise GuidanceFailure("mass_floor", f"toy stage 2 ended by {r2.ended_by}")
        m_c = float(PLANAR_LAYOUT.get(r2.y_end, "m_kg"))
        return ResidualResult(
            payload_kg,
            gamma_star_rad,
            m_c - m_empty,
            C_MPS * math.log(m_c / m_empty),
            None,
            None,
            gamma_star_rad,
            "",
            0,
            0,
            mode,
        )


def _assert_p_lo_is_a_verified_payload(res: object) -> None:
    """P* is P_lo, an evaluated payload, never the interpolated root: payload_kg is the
    largest logged payload that flew with m_res >= 0, and at_payload is that evaluation."""
    ok = {e.payload_kg: e for e in res.evals if e.ok}  # type: ignore[attr-defined]
    p_lo = max(p for p, e in ok.items() if e.m_res_kg >= 0.0)
    assert res.payload_kg == p_lo  # type: ignore[attr-defined]
    assert res.at_payload.payload_kg == p_lo  # type: ignore[attr-defined]
    assert res.at_payload.m_res_kg == ok[p_lo].m_res_kg >= 0.0  # type: ignore[attr-defined]


def test_payload_matches_the_rocket_equation_closed_form() -> None:
    """V* = 4000 m/s (the toy reaches 4946 m/s empty): payload_capacity from a 50 kg hint
    finds P* with D_id(P*) = V* (brentq on the closed form here) within payload_xtol_kg,
    P_lo <= root, m_res(P_lo) >= 0. The first high end (2,050 kg) would need stage 2 to
    burn below the mass floor 0.5 (m_d2 + P): it fails typed (mass_floor) and backs off;
    every evaluation that flew has the rocket equation's m_res, negative ones included
    (virtual propellant past m_p2)."""
    v_star = 4000.0
    toy = SpeedTargetToy(v_star)
    res = payload_capacity(toy, 0.0, 50.0, WarmStore())
    p_star = brentq(lambda p: _closed_form_dv(p) - v_star, 0.0, 1e4, xtol=1e-12)
    assert res.status == OK_STATUS
    assert res.root_kg == pytest.approx(p_star, abs=toy.budget.payload_xtol_kg)
    assert res.payload_kg == pytest.approx(p_star, abs=toy.budget.payload_xtol_kg)
    assert res.payload_kg <= res.root_kg + 1e-9 and res.at_payload.m_res_kg >= 0.0
    _assert_p_lo_is_a_verified_payload(res)
    flown = [e for e in res.evals if e.ok]
    assert {e.m_res_kg >= 0.0 for e in flown} == {True, False}
    assert res.backoffs >= 1 and res.evals[1].payload_kg == pytest.approx(2050.0)
    assert res.evals[1].failure is not None and res.evals[1].failure.startswith("mass_floor")
    for e in flown:
        m_empty = M_D2 + e.payload_kg
        m2 = M_D2 + M_P2 + e.payload_kg
        dv1 = _closed_form_dv(e.payload_kg) - C_MPS * math.log(m2 / m_empty)
        m_c = m2 * math.exp(-(v_star - dv1) / C_MPS)
        assert e.m_res_kg == pytest.approx(m_c - m_empty, abs=1e-6)


def test_no_orbit_reports_the_shortfall_at_zero_payload() -> None:
    """V* = 5500 m/s is beyond the empty toy's 4946 m/s: status no_orbit, P* = 0, and the
    shortfall -dv_margin(0) equals V* - D_id(0) (1e-6 relative)."""
    v_star = 5500.0
    res = payload_capacity(SpeedTargetToy(v_star), 0.0, 50.0, WarmStore())
    assert res.status == NO_ORBIT_STATUS and res.payload_kg == 0.0
    assert math.isnan(res.root_kg) and res.at_payload.payload_kg == 0.0
    assert res.dv_shortfall_mps == pytest.approx(v_star - _closed_form_dv(0.0), rel=1e-6)


def _analytic(
    m_of_p: object, fail_at: float = math.inf, fail_inside: tuple[float, float] | None = None
) -> object:
    """An evaluation function with m_res(P) = m_of_p(P) that raises a typed
    GuidanceFailure at P >= fail_at [kg] and, when fail_inside = (lo, hi) is given, at
    lo < P < hi [kg]."""

    def fn(p: float) -> ResidualResult:
        inside = fail_inside is not None and fail_inside[0] < p < fail_inside[1]
        if p >= fail_at or inside:
            raise GuidanceFailure("nonconverged", f"no shot at {p} kg")
        m = m_of_p(p)  # type: ignore[operator]
        return ResidualResult(p, 0.0, m, m / 10.0, None, None, 0.0, "", 0, 0, SEARCH_MODE)

    return fn


def _root(fn: object, hint: float, halves: tuple[float, ...], backoff_max: int = 4) -> object:
    return payload_root(fn, hint, halves, backoff_max=backoff_max, xtol_kg=0.5, rtol=1e-15)  # type: ignore[arg-type]


def test_bracket_expands_backs_off_and_fails_typed() -> None:
    """m_res = 10000 - P from hint 0 with half-widths 2, 4, 8, 16 t: the high end expands
    three times (root 10 t). m_res = 100 - P from hint 5 t: the low end expands down to
    P = 0 (root 100 kg). m_res = 1000 - P failing at P >= 1500 kg from hint 0: the high
    end (2 t) fails, backs off to 1 t (m_res = 0, a new low end), then halfway to the
    lowest failure (1.5 t, fails), then to 1.25 t; P_lo = 1 t after 3 backoffs; with 2
    backoffs allowed SearchFailed('bracket'); halves exhausted likewise."""
    halves = (2000.0, 4000.0, 8000.0, 16000.0)
    res = _root(_analytic(lambda p: 1e4 - p), 0.0, halves)
    assert (res.expansions, res.backoffs) == (3, 0)  # type: ignore[attr-defined]
    assert res.root_kg == pytest.approx(1e4, abs=0.5)  # type: ignore[attr-defined]
    res = _root(_analytic(lambda p: 100.0 - p), 5000.0, halves)
    assert res.bracket_kg[0] == 0.0 and res.expansions == 2  # type: ignore[attr-defined]
    assert res.payload_kg == pytest.approx(100.0, abs=0.5)  # type: ignore[attr-defined]
    fn = _analytic(lambda p: 1000.0 - p, fail_at=1500.0)
    res = _root(fn, 0.0, halves)
    assert res.backoffs == 3 and res.bracket_kg == (1000.0, 1250.0)  # type: ignore[attr-defined]
    assert res.payload_kg == 1000.0  # type: ignore[attr-defined]
    fails = [e.payload_kg for e in res.evals if not e.ok]  # type: ignore[attr-defined]
    assert fails == [2000.0, 1500.0]
    with pytest.raises(SearchFailed) as info:
        _root(fn, 0.0, halves, backoff_max=2)
    assert info.value.kind == "bracket"
    with pytest.raises(SearchFailed) as info:
        _root(_analytic(lambda p: 1e5 - p), 0.0, halves)
    assert info.value.kind == "bracket"


def test_low_end_backs_off_toward_lighter_payloads() -> None:
    """m_res = 1.02 (10,500 - P) kg failing at P >= 25 t, from a 30 t hint (half-widths 2
    t x 2^k): the low end 28 t fails with nothing lighter flown, so it backs off halfway
    toward 0 (14 t, flies, m_res < 0: the new high end); the low end then expands below
    that high end (12 t, then 10 t, where m_res >= 0), never back up toward the failing
    hint. P_lo = 10,500 kg within the xtol after 1 backoff and 2 expansions. With
    low_toward_hint (the final verification's rule) the same failing low end backs off
    toward the hint instead (29 t, which fails too, then 29.5 t) and the backoffs run
    out: SearchFailed('bracket')."""
    halves = tuple(2000.0 * 2.0**k for k in range(7))
    fn = _analytic(lambda p: 1.02 * (10_500.0 - p), fail_at=25_000.0)
    res = _root(fn, 30_000.0, halves)
    assert res.status == OK_STATUS  # type: ignore[attr-defined]
    assert (res.backoffs, res.expansions) == (1, 2)  # type: ignore[attr-defined]
    assert [e.payload_kg for e in res.evals[:4]] == [28_000.0, 14_000.0, 12_000.0, 10_000.0]  # type: ignore[attr-defined]
    assert res.bracket_kg == (10_000.0, 12_000.0)  # type: ignore[attr-defined]
    assert res.payload_kg == pytest.approx(10_500.0, abs=0.5)  # type: ignore[attr-defined]
    assert res.payload_kg <= 10_500.0  # type: ignore[attr-defined]
    _assert_p_lo_is_a_verified_payload(res)
    with pytest.raises(SearchFailed) as info:
        payload_root(
            fn,  # type: ignore[arg-type]
            30_000.0,
            halves,
            backoff_max=2,
            xtol_kg=0.5,
            rtol=1e-15,
            low_toward_hint=True,
        )
    assert info.value.kind == "bracket" and "29500" in info.value.message


def test_a_failure_inside_the_bracket_is_search_failed_root() -> None:
    """m_res = 1000 - P from a 1 t hint (bracket ends 0 and 3 t fly) with every payload
    strictly between 1 kg and 2,999 kg failing: brentq's first interior evaluation fails,
    which is SearchFailed('root') (never a root from a bracket with a hole)."""
    fn = _analytic(lambda p: 1000.0 - p, fail_inside=(1.0, 2999.0))
    with pytest.raises(SearchFailed) as info:
        _root(fn, 1000.0, (2000.0, 4000.0))
    assert info.value.kind == "root"


# --------------------------------------------------------------- the planar model


@pytest.fixture(scope="module")
def pad(repo_root: Path) -> SearchContext:
    """The pad of experiments/silo_screening_2d.yaml (gate fork) at the test budget: the
    shared search block with search_rtol = TEST_SEARCH_RTOL."""
    exp = load_experiment(repo_root / "experiments" / "silo_screening_2d.yaml")
    base = exp.baseline
    assert base.run.planar is not None
    cfg = base.run.planar.search.model_copy(update={"search_rtol": TEST_SEARCH_RTOL})
    ctx = SearchContext.from_run(base.run, base.to_vehicle())
    return dataclasses.replace(ctx, budget=SearchBudget.from_config(cfg, base.run.planar.checks))


@dataclass
class Around:
    """Search-mode m_res at gamma* 20 deg around its zero: the secant estimate p_c [kg] of
    P*(20 deg) from the vehicle payload, the payloads [kg] and the evaluations there."""

    p_c: float
    payloads: list[float]
    results: list[ResidualResult]


@pytest.fixture(scope="module")
def around(pad: SearchContext) -> Around:
    """m_res(P) at gamma* 20 deg: at P0 and P0 + m_res(P0), the secant zero p_c, then
    p_c + (-40, -20, 0, 20, 40) kg, all in one warm store (search mode)."""
    warm = WarmStore()
    p0 = pad.payload_kg
    r0 = pad.evaluate(p0, GAMMA_20_RAD, warm, SEARCH_MODE)
    r1 = pad.evaluate(p0 + r0.m_res_kg, GAMMA_20_RAD, warm, SEARCH_MODE)
    slope = (r0.m_res_kg - r1.m_res_kg) / (r1.payload_kg - p0)
    p_c = p0 + r0.m_res_kg / slope
    payloads = [p_c + d for d in (-40.0, -20.0, 0.0, 20.0, 40.0)]
    return Around(
        p_c, payloads, [pad.evaluate(p, GAMMA_20_RAD, warm, SEARCH_MODE) for p in payloads]
    )


def test_m_res_is_monotone_and_continuous_across_depletion(around: Around) -> None:
    """Five payloads 20 kg apart spanning m_res = 0 (where a real stage 2 would run dry
    at the cutoff): m_res changes sign and falls strictly (the slope itself is a model
    output, recorded in docs/physics.md, not pinned here: 1.0255 kg/kg at this gamma* of
    20 deg), and the second differences stay below 0.05 kg (measured 2e-3 kg at the test
    rtol): the virtual propellant adds no kink at depletion."""
    m = np.array([r.m_res_kg for r in around.results])
    assert m[0] > 0.0 > m[-1]
    d1 = np.diff(m)
    assert np.all(d1 < 0.0)
    assert np.max(np.abs(np.diff(d1))) < 0.05
    # dv_margin has the sign of m_res and is c2 ln(m_c/m_empty) of the same shot
    for r in around.results:
        assert r.shot is not None
        assert r.dv_margin_mps == pytest.approx(
            r.shot.c_mps * math.log(r.shot.m_cut_kg / r.shot.m_empty_kg), rel=1e-12
        )
        assert math.copysign(1.0, r.dv_margin_mps) == math.copysign(1.0, r.m_res_kg)
        assert r.shot.ended_by == "cutoff" and r.shot.virtual_propellant


@pytest.mark.slow
def test_beyond_the_mass_floor_the_evaluation_fails_typed(pad: SearchContext) -> None:
    """Continuing in payload from 22.8 t: 35 and 45 t still reach the cutoff on virtual
    propellant (m_res negative and decreasing), and 60 t, where the ladder's warm shot
    would burn below the floor 0.5 (m_d2 + P), raises a typed GuidanceFailure naming
    mass_floor (never an m_res from a shot that ran past the floor). Slow: the fast
    toy test already pins the typed mass_floor failure."""
    warm = WarmStore()
    m = [pad.evaluate(p, GAMMA_20_RAD, warm, SEARCH_MODE).m_res_kg for p in (22_800.0, 35e3, 45e3)]
    assert m[0] > m[1] > m[2] and m[1] < 0.0
    with pytest.raises(GuidanceFailure) as info:
        pad.evaluate(60e3, GAMMA_20_RAD, warm, SEARCH_MODE)
    assert info.value.kind == "nonconverged" and "mass_floor" in info.value.message


def test_short_of_orbit_record_carries_the_signed_figures(
    pad: SearchContext, around: Around
) -> None:
    """``final_residual`` at gamma* 20 deg, SHORT_BY_KG above the payload root: the
    final-mode evaluation needs virtual propellant (m_res < 0, dv_margin < 0); its
    recorded run flies the real load, runs dry before the cutoff (short_of_orbit) and
    carries the evaluation's signed m_res and dv_margin (figures_from final_evaluation,
    no cutoff state to compare: NaN), never the ~0 left at depletion."""
    fin = final_residual(pad, GAMMA_20_RAD, around.p_c + SHORT_BY_KG, WarmStore())
    at, rec = fin.at_final, fin.recorded
    assert fin.payload is None and at.mode == FINAL_MODE
    assert at.m_res_kg < -0.5 * SHORT_BY_KG and at.dv_margin_mps < 0.0
    assert rec.status == SHORT_OF_ORBIT_STATUS
    assert rec.figures_from == FROM_FINAL_EVALUATION
    assert (rec.m_res_kg, rec.dv_margin_mps) == (at.m_res_kg, at.dv_margin_mps)
    assert math.isnan(rec.cut_state_rel_diff)
    last_burn = [ph for ph in rec.trace.phases if ph.spec.kind == "LTG_BURN"][-1]
    assert last_burn.ended_by == "propellant"


@pytest.fixture(scope="module")
def final_20(pad: SearchContext, around: Around) -> FinalResult:
    """The final verification at gamma* 20 deg from the search-mode estimate p_c."""
    return final_verify(pad, GAMMA_20_RAD, around.p_c, WarmStore())


def test_final_run_is_inserted_with_a_tiny_residual(
    pad: SearchContext, final_20: FinalResult
) -> None:
    """The recorded run at P_final (final tolerance, dense output, the real depletion
    event, no mass floor): status inserted, 0 <= m_res < final_payload_xtol_kg (0.05
    kg), its stage-2 end state equal to the final-verification evaluation's cutoff state
    (1e-9 relative; the two integrate the same steps) and every event of that evaluation
    logged again at the same time and state (1e-9 relative); P_final within 0.5 kg of the
    search estimate (no bracket expansion, no flag)."""
    rec = final_20.recorded
    at = final_20.at_final
    assert final_20.payload is not None and final_20.payload.status == OK_STATUS
    _assert_p_lo_is_a_verified_payload(final_20.payload)
    assert final_20.payload_kg == final_20.payload.payload_kg == at.payload_kg
    assert rec.status == "inserted"
    assert 0.0 <= rec.m_res_kg < pad.budget.final_payload_xtol_kg
    assert rec.m_res_kg == pytest.approx(at.m_res_kg, abs=1e-9)
    assert rec.cut_state_rel_diff < 1e-9
    assert at.mode == FINAL_MODE and at.shot is not None and at.shot.ended_by == "cutoff"
    evaluated = at.shot.prefix.events
    recorded = rec.trace.events
    assert [e.name for e in recorded[: len(evaluated)]] == [e.name for e in evaluated]
    assert [e.name for e in recorded[len(evaluated) :]] == ["end"]
    for a, b in zip(recorded, evaluated, strict=False):
        assert a.t_s == pytest.approx(b.t_s, rel=1e-9, abs=1e-9)
        assert a.m_kg == pytest.approx(b.m_kg, rel=1e-9)
        assert a.columns == b.columns
        for col in a.columns:
            assert a.value(col) == pytest.approx(b.value(col), rel=1e-9, abs=1e-9)
    last_burn = [ph for ph in rec.trace.phases if ph.spec.kind == "LTG_BURN"][-1]
    names = {e.name for e in last_burn.spec.events}
    assert "propellant" in names and "mass_floor" not in names
    shot_burn = [ph for ph in at.shot.prefix.phases if ph.spec.kind == "LTG_BURN"][-1]
    assert "mass_floor" in {e.name for e in shot_burn.spec.events}
    assert not rec.trace.dense_off and at.shot.prefix.dense_off
    assert final_20.flags == ()
    assert abs(final_20.search_vs_final_payload_kg) < 0.5


@pytest.mark.slow
def test_nested_solution_equals_the_joint_root(pad: SearchContext, final_20: FinalResult) -> None:
    """The joint 3-equation root (a, 100 b, P/1e4) of r_c = r_t, v_r,c = 0, m_res = 0 at
    gamma* 20 deg (final tolerance, delta re-solved per payload), started 200 kg above
    and, from a 2 %-off pair, 300 kg below the nested solution, lands on the nested P*
    within 1 kg (measured 0.004 kg) and on its (a, b) within the box-implied LTG
    tolerance (2e-5 in a, 1e-7 1/s in b)."""
    at = final_20.at_final
    assert at.ltg is not None
    a, b = at.ltg
    p = final_20.payload_kg
    for guess in ((a, b, p + 200.0), (1.02 * a, 0.98 * b, p - 300.0)):
        joint = joint_root_crosscheck(pad, GAMMA_20_RAD, guess, WarmStore())
        assert joint.payload_kg == pytest.approx(p, abs=1.0)
        assert joint.a == pytest.approx(a, abs=2e-5)
        assert joint.b_per_s == pytest.approx(b, abs=1e-7)
        assert abs(joint.m_res_kg) < pad.budget.final_payload_xtol_kg


@pytest.mark.slow
def test_vehicle_that_misses_orbit_is_no_orbit_through_run_search(pad: SearchContext) -> None:
    """The gate pad with STAGE2_EXTRA_DRY_KG more stage-2 dry mass: no gamma* grid point
    flies at P0 (22.8 t), so the grid is re-run at P = 0 (flagged), and the search ends
    no_orbit with P* = 0 and a positive shortfall -dv_margin(0), not NaN. The recorded run
    at P = 0 runs dry before the cutoff and carries the final evaluation's signed m_res
    and dv_margin; rung 2 at P0 cannot fly (at_p0 None, flagged)."""
    st = list(pad.vehicle.stages)
    st[1] = dataclasses.replace(st[1], dry_mass_kg=st[1].dry_mass_kg + STAGE2_EXTRA_DRY_KG)
    heavy = dataclasses.replace(pad, vehicle=dataclasses.replace(pad.vehicle, stages=tuple(st)))
    rec = run_search(heavy)
    assert rec.status == NO_ORBIT_STATUS and rec.failure_kind is None
    assert rec.payload_kg == 0.0 and rec.gamma is not None and rec.final is not None
    assert rec.gamma.grid_payload_kg == 0.0
    assert any("re-run at P = 0" in f for f in rec.flags)
    fp = rec.final.payload
    assert fp is not None and fp.status == NO_ORBIT_STATUS
    at, recorded = rec.final.at_final, rec.final.recorded
    assert at.payload_kg == 0.0 and at.m_res_kg < 0.0
    assert fp.dv_shortfall_mps == -at.dv_margin_mps and fp.dv_shortfall_mps > 0.0
    assert recorded.status == SHORT_OF_ORBIT_STATUS
    assert recorded.figures_from == FROM_FINAL_EVALUATION
    assert (recorded.m_res_kg, recorded.dv_margin_mps) == (at.m_res_kg, at.dv_margin_mps)
    assert rec.at_p0 is None and any(f.startswith("rung 2 at P0") for f in rec.flags)
