"""Propellant offload at fixed payload (docs/physics.md, "Figures of merit (planar)",
"Propellant offload at fixed payload"; SP1 step 5).

- ``vehicle.with_offload``: the masses of each mode against hand arithmetic (the liftoff
  mass falls by x to rounding, dry masses unchanged, ``both`` at one fraction of each load),
  the range error at a stage's whole load, and the refusals.
- The solver on a toy RecordingProblem built from a vehicle by a factory, modelled on
  ``SpeedTargetToy`` (tests/test_payload_search.py): a two-stage rocket (c = 3000 m/s
  both stages, zero gravity, vacuum, thrust along v) with a head start v0 [m/s], stage 1
  to its propellant event, its dry mass dropped, stage 2 to a speed target with virtual
  propellant (mass floor 0.5 (m_d2 + P)); the target V*(gamma*) = V* + K (gamma* -
  gamma_opt)^2 gives the gamma* sweep an interior optimum. With m0 the full-load liftoff
  mass (both stages and the payload), m1 = m0 - m_p1, m2 = m1 - m_d1, m3 = m_d2 + P and
  primes for the offloaded masses, m_res(x) = m2' exp(-(V* - v0 - c ln(m0'/m1'))/c) -
  m3, so m_res = 0 where v0 + c ln(m0'/m1') + c ln(m2'/m3) = V*. For stage 1 (m0' = m0
  - x, m1' = m1, m2' = m2) that is x* = m0 - m1 exp((V* - v0 - c ln(m2/m3))/c); for
  stage 2 and both, brentq on that speed here (never on the solver). Every expected
  value is evaluated at the solve's own gamma*, V*(gamma*_ref).
- In vacuum with no gravity, x* equals ``vehicle.stage1_propellant_saved_kg`` when the
  screening Isp is the engine Isp; no_offload above the toy's capacity at v0 = 0, with
  the shortfall V* - D_id(P_ref); the toy's own P* as the reference gives x within
  final_payload_xtol_kg / |dm_res/dx| of 0 (the pad control's rule); the range back-off;
  the typed infeasible, the store rules, the flags and the search_failed status.
- Slow, gate fork (experiments/silo_screening_2d.yaml, full shipped gamma* grid): at the
  test budget (search rtol TEST_SEARCH_RTOL = 1e-9, final 1e-10 as shipped; CLAUDE.md:
  rtol <= 1e-9 in tests), the recorded-run rule at x*, the independent payload search
  within checks.search_final_flag_rel x P_ref (plus a tighter guard on its measured
  gap), and the stage-1 pad control within the bound of the phase file's section 5.3;
  and the convergence test, which alone flies the shipped budget (search rtol 1e-8, the
  one the offload experiment will run) on its baseline side, as amendment 3 asks of
  tests/test_convergence_2d.py: against its 10x tightening (``SearchContext.tightened``)
  x* moves by less than 0.1 %.
"""

from __future__ import annotations

import dataclasses
import math
import pickle
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from scipy.optimize import brentq

from launchsim.cli import load_experiment
from launchsim.config import ChecksConfig, ConvergenceConfig, SearchConfig
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
from launchsim.offload import (
    ABSCISSA_NOTE,
    FINAL_LOG,
    NO_OFFLOAD_STATUS,
    NONMONOTONE_FLAG,
    OFFLOAD_FLAG_PREFIX,
    OFFLOAD_RANGE_KIND,
    VERIFY_MISMATCH_FLAG,
    X1_LOG,
    X2_LOG,
    OffloadEval,
    OffloadInfeasible,
    OffloadProblem,
    OffloadResult,
    OffloadWarmStore,
    nonmonotone_flags,
    planar_problem_factory,
    solve_offload,
    verify_offload,
)
from launchsim.phases import EventSpec, IntegratorSettings, PhaseSpec, integrate_phase
from launchsim.phases.engine import atol_for, ev_propellant
from launchsim.phases.planar import INSERTED_STATUS, SHORT_OF_ORBIT_STATUS, planar_rest_state
from launchsim.search import (
    FROM_FINAL_EVALUATION,
    FROM_RECORDED_RUN,
    INFEASIBLE,
    OK_STATUS,
    SEARCH_FAILED_STATUS,
    SEARCH_MODE,
    PreludeFailure,
    RecordedRun,
    ResidualResult,
    SearchBudget,
    SearchContext,
    WarmEntry,
    WarmStore,
    run_search,
)
from launchsim.vehicle import (
    Engine,
    OffloadRangeError,
    Stage,
    Startup,
    Vehicle,
    offload_load_kg,
    offload_split_kg,
    stage1_propellant_saved_kg,
    with_offload,
)

C_MPS = 3000.0
"""Exhaust velocity of both toy stages [m/s]."""
M_D1, M_P1, T1 = 200.0, 800.0, 15_000.0
"""Toy stage 1: dry and propellant mass [kg], vacuum thrust [N] (SpeedTargetToy's)."""
M_D2, M_P2, T2 = 150.0, 150.0, 3_000.0
"""Toy stage 2: dry and propellant mass [kg], vacuum thrust [N] (SpeedTargetToy's)."""
V_STAR_MPS = 4000.0
"""Toy speed target at the optimum gamma* [m/s] (the empty toy reaches 4946 m/s from
rest)."""
V0_MPS = 300.0
"""Toy head start [m/s] (the assist)."""
GAMMA_OPT_RAD = math.radians(20.3)
"""Toy optimum gamma* [rad], between grid points of the default 8-36 deg grid."""
K_GAMMA_MPS_PER_RAD2 = 1000.0
"""Toy curvature of the speed target in gamma* [m/s/rad^2]: one 2 deg grid step off the
optimum costs about 1.2 m/s."""
TOY_HALF_BRACKET_T = 0.02
"""Payload (here: offload) half-bracket of the toy budget [t]: 20 kg, doubled up to 1280
kg, so the stage-1 and both brackets close by expansion inside their loads and the
stage-2 bracket backs off once from 160 kg, beyond the 150 kg stage-2 load."""
STAGE1_RANGE_HALF_BRACKET_T = 1.0
"""A half-bracket [t] whose first high end (1000 kg) takes more than the toy's whole
stage-1 load (800 kg)."""
TOY_FLAG_REL = 2.0e-3
"""checks.search_final_flag_rel of the toy [-]: 0.12 kg at its 60 kg reference payload.
The verification's own resolution is about final_payload_xtol_kg (0.05 kg) on each side
(x* keeps up to 0.05 kg of residual, worth 0.05 kg / |dm_res/dP| of payload, and the
payload search ends up to 0.05 kg below its root), which the shipped 1e-4 covers at the
gate fork's 26 t (2.6 kg) but not at the toy's 60 kg."""
INTEGRATION_SLACK_KG = 1.0e-6
"""Slack [kg] for the toy's integration error in an offload or a residual (rtol
1e-10)."""
OVER_CAPACITY_KG = 1.0
"""How far above the toy's closed-form capacity at v0 = 0 the no_offload test flies
[kg]."""
GATE_EXPERIMENT = Path("experiments") / "silo_screening_2d.yaml"
"""The gate fork's shipped planar experiment (pad and silo_cold)."""
TEST_SEARCH_RTOL = 1.0e-9
"""Search-mode rtol of the gate validation tests (CLAUDE.md: rtol <= 1e-9 in tests); the
convergence test alone flies the shipped 1e-8, on its baseline side (amendment 3)."""
VERIFY_GAP_GUARD_XTOLS = 2.0
"""Regression guard on the verification's measured gap, in final_payload_xtol_kg (0.1
kg): the two final tolerances bound the expected gap to about +/- final_payload_xtol_kg
(x* keeps up to 0.05 kg of residual, the payload search ends up to 0.05 kg below its
root), measured +0.0084 kg. Not the flag threshold, which is coarse in offload terms
(docs/physics.md, "Independent verification")."""


# --------------------------------------------------------------------------- vehicle


def _stage(name: str, dry: float, prop: float, thrust: float) -> Stage:
    engine = Engine(thrust_vac_N=thrust, isp_vac_s=C_MPS / G0_MPS2, exit_area_m2=0.0)
    return Stage(name, dry, prop, engine, 1, Startup("step"), 0.0)


def _toy_vehicle(payload_kg: float) -> Vehicle:
    """The toy two-stage vehicle at payload_kg [kg], no fairing, screening Isp = engine
    Isp (c / g0) on both stages."""
    isp = C_MPS / G0_MPS2
    return Vehicle(
        stages=(_stage("stage1", M_D1, M_P1, T1), _stage("stage2", M_D2, M_P2, T2)),
        payload_mass_kg=payload_kg,
        screening_isp_s=(isp, isp),
    )


def test_with_offload_masses_by_mode() -> None:
    """x = 120 kg: stage1 leaves 680 kg in stage 1, stage2 leaves 30 kg in stage 2, both
    takes 120 x 800/950 from stage 1 and the rest from stage 2 (the same fraction 120/950
    of each load); in every mode the liftoff mass falls by 120 kg (1e-12 kg; the masses
    are rounded sums) and every dry mass, engine, the payload and the screening Isp are
    unchanged."""
    v = _toy_vehicle(50.0)
    x = 120.0
    out = {mode: with_offload(v, mode, x) for mode in ("stage1", "stage2", "both")}
    assert [s.propellant_mass_kg for s in out["stage1"].stages] == [680.0, 150.0]
    assert [s.propellant_mass_kg for s in out["stage2"].stages] == [800.0, 30.0]
    p1, p2 = (s.propellant_mass_kg for s in out["both"].stages)
    f = x / (M_P1 + M_P2)
    assert p1 == pytest.approx(M_P1 * (1.0 - f), abs=1e-12)
    assert p2 == pytest.approx(M_P2 * (1.0 - f), abs=1e-12)
    # The shares add up to x only to rounding in general; exactly here, because the toy's
    # m_p1 > m_p2 puts stage 1's share x1 in [x/2, x], so x - x1 is exact (Sterbenz's
    # lemma) and x1 + (x - x1) rounds to x.
    assert offload_split_kg(v, "both", x)[0] + offload_split_kg(v, "both", x)[1] == x
    for veh in out.values():
        assert veh.liftoff_mass_kg() == pytest.approx(v.liftoff_mass_kg() - x, abs=1e-12)
        assert [s.dry_mass_kg for s in veh.stages] == [M_D1, M_D2]
        assert [s.engine for s in veh.stages] == [s.engine for s in v.stages]
        assert veh.payload_mass_kg == v.payload_mass_kg
        assert veh.screening_isp_s == v.screening_isp_s
    assert with_offload(v, "stage1", 0.0) == v
    assert offload_load_kg(v, "stage1") == M_P1
    assert offload_load_kg(v, "stage2") == M_P2
    assert offload_load_kg(v, "both") == M_P1 + M_P2


def test_with_offload_range_and_refusals() -> None:
    """A stage's whole load or more is OffloadRangeError (a ValueError; Stage needs
    propellant > 0), just below it builds; negative, NaN, an unknown mode and a mode
    the vehicle lacks are ValueError."""
    v = _toy_vehicle(50.0)
    for mode, load in (("stage1", M_P1), ("stage2", M_P2), ("both", M_P1 + M_P2)):
        with pytest.raises(OffloadRangeError):
            with_offload(v, mode, load)
        with pytest.raises(OffloadRangeError):
            with_offload(v, mode, 2.0 * load)
        assert with_offload(v, mode, 0.999 * load).liftoff_mass_kg() == pytest.approx(
            v.liftoff_mass_kg() - 0.999 * load, abs=1e-9
        )
    assert issubclass(OffloadRangeError, ValueError)
    for bad in (-1.0, math.nan, math.inf):
        with pytest.raises(ValueError):
            with_offload(v, "stage1", bad)
    with pytest.raises(ValueError):
        with_offload(v, "stage3", 1.0)  # type: ignore[arg-type]
    one = Vehicle(stages=(v.stages[0],))
    for mode in ("stage2", "both"):
        with pytest.raises(ValueError):
            with_offload(one, mode, 1.0)


# ------------------------------------------------------------------------------ toy


def _toy_budget(**update: object) -> SearchBudget:
    """The toy budget: the default search block with the toy half-bracket, plus update,
    and the toy's verification tolerance (TOY_FLAG_REL)."""
    cfg = SearchConfig().model_copy(update={"payload_half_bracket_t": TOY_HALF_BRACKET_T, **update})
    return SearchBudget.from_config(cfg, ChecksConfig(search_final_flag_rel=TOY_FLAG_REL))


def _target_mps(gamma_star_rad: float) -> float:
    """The toy speed target V*(gamma*) = V* + K (gamma* - gamma_opt)^2 [m/s]."""
    return V_STAR_MPS + K_GAMMA_MPS_PER_RAD2 * (gamma_star_rad - GAMMA_OPT_RAD) ** 2


@dataclass(frozen=True, eq=False)
class HeadStartToy:
    """The toy as a RecordingProblem of a vehicle (see the module docstring): v0_mps the
    head start [m/s], radial with the thrust; the vehicle's own payload is P0. m_res =
    m_c - (m_d2 + P), dv_margin = c ln(m_c / (m_d2 + P)). ``record`` re-flies stage 2
    with the real depletion event instead of the mass floor: inserted with its own m_res
    when the target comes first, else short_of_orbit carrying the evaluation's figures."""

    vehicle: Vehicle
    v0_mps: float
    budget: SearchBudget
    settings: IntegratorSettings = field(default_factory=lambda: IntegratorSettings(rtol=1e-10))

    @property
    def payload_kg(self) -> float:
        """P0 [kg]: the vehicle's payload."""
        return self.vehicle.payload_mass_kg

    def _params(self, stage: Stage, t_ign_s: float) -> PlanarParams:
        return PlanarParams(
            ConstantGravity(0.0),
            0.0,
            0.0,
            stage.schedule(t_ign_s),
            None,
            vacuum_atmosphere,
            AlongVrel(),
        )

    def _fly(self, payload_kg: float, gamma_star_rad: float, real: bool) -> tuple[str, float]:
        """Stage 1 to burnout from v0, then stage 2 to the target (``real``: with the
        real depletion event; else with virtual propellant and the mass floor). Returns
        (ended_by, mass [kg] at the end)."""
        s1, s2 = self.vehicle.stages
        atol = atol_for(PLANAR_STATE_NAMES)
        m0 = s1.wet_mass_kg + s2.wet_mass_kg + payload_kg
        y = planar_rest_state(0.0, m0, 0.0)
        y[PLANAR_LAYOUT.index("v_r_mps")] = self.v0_mps
        burn1 = PhaseSpec(
            "BURN",
            0,
            0.0,
            None,
            rhs_planar,
            self._params(s1, 0.0),
            (ev_propellant(m0 - s1.propellant_mass_kg, PLANAR_LAYOUT),),
            atol,
        )
        r1 = integrate_phase(burn1, y, self.settings)
        y = r1.y_end.copy()
        y[PLANAR_LAYOUT.index("m_kg")] -= s1.dry_mass_kg
        m_empty = s2.dry_mass_kg + payload_kg
        v_star = _target_mps(gamma_star_rad)
        i_v = PLANAR_LAYOUT.index("v_r_mps")
        target = EventSpec("speed", lambda t, yy: float(yy[i_v]) - v_star, True, +1, 1e-9)
        if real:
            stop = ev_propellant(m_empty, PLANAR_LAYOUT)
        else:
            i_m = PLANAR_LAYOUT.index("m_kg")
            stop = EventSpec(
                "mass_floor", lambda t, yy: float(yy[i_m]) - 0.5 * m_empty, True, -1, 1e-6
            )
        burn2 = PhaseSpec(
            "BURN", 1, r1.t_end, None, rhs_planar, self._params(s2, r1.t_end), (target, stop), atol
        )
        r2 = integrate_phase(burn2, y, self.settings)
        return r2.ended_by, float(PLANAR_LAYOUT.get(r2.y_end, "m_kg"))

    def evaluate(
        self,
        payload_kg: float,
        gamma_star_rad: float,
        warm: WarmStore,
        mode: str,
        *,
        seed: WarmEntry | None = None,
    ) -> ResidualResult:
        """The toy rung 2 at (payload [kg], gamma* [rad]); a typed mass_floor failure
        when stage 2 would burn below the floor."""
        ended_by, m_c = self._fly(payload_kg, gamma_star_rad, real=False)
        if ended_by != "speed":
            raise GuidanceFailure("mass_floor", f"toy stage 2 ended by {ended_by}")
        m_empty = self.vehicle.stages[1].dry_mass_kg + payload_kg
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

    def record(self, res: ResidualResult) -> RecordedRun:
        """The toy recorded run of res (no trace): the real depletion event armed."""
        ended_by, m_end = self._fly(res.payload_kg, res.gamma_star_rad, real=True)
        if ended_by == "speed":
            m_empty = self.vehicle.stages[1].dry_mass_kg + res.payload_kg
            return RecordedRun(
                None,  # type: ignore[arg-type]
                INSERTED_STATUS,
                m_end - m_empty,
                C_MPS * math.log(m_end / m_empty),
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


def _toy_factory(
    v0_mps: float, budget: SearchBudget | None = None
) -> Callable[[Vehicle], HeadStartToy]:
    """The toy problem factory at head start v0_mps [m/s] and budget (the toy budget)."""
    b = _toy_budget() if budget is None else budget

    def factory(vehicle: Vehicle) -> HeadStartToy:
        return HeadStartToy(vehicle, v0_mps, b)

    return factory


def _masses(p_kg: float) -> tuple[float, float, float, float]:
    """(m0, m1, m2, m3) [kg] of the full-load toy at payload p_kg [kg]."""
    m0 = M_D1 + M_P1 + M_D2 + M_P2 + p_kg
    m1 = m0 - M_P1
    return m0, m1, m1 - M_D1, M_D2 + p_kg


def _offloaded_masses(mode: str, x: float, p_kg: float) -> tuple[float, float, float, float]:
    """(m0', m1', m2', m3) [kg] of the toy offloaded by x [kg] along mode at payload p_kg,
    written out per mode (both: x1 = x m_p1/(m_p1 + m_p2) from stage 1, the rest from
    stage 2)."""
    m0, m1, m2, m3 = _masses(p_kg)
    if mode == "stage1":
        return m0 - x, m1, m2, m3
    x2 = x if mode == "stage2" else x - x * M_P1 / (M_P1 + M_P2)
    return m0 - x, m1 - x2, m2 - x2, m3


def _ideal_speed(mode: str, x: float, p_kg: float, v0: float) -> float:
    """v0 + c ln(m0'/m1') + c ln(m2'/m3) [m/s]: the toy's speed with stage 2 burned to
    its empty mass."""
    m0, m1, m2, m3 = _offloaded_masses(mode, x, p_kg)
    return v0 + C_MPS * math.log(m0 / m1) + C_MPS * math.log(m2 / m3)


def _closed_m_res(mode: str, x: float, p_kg: float, v0: float, v_star: float) -> float:
    """m_res(x) = m2' exp(-(V* - v0 - c ln(m0'/m1'))/c) - m3 [kg] of the toy."""
    m0, m1, m2, m3 = _offloaded_masses(mode, x, p_kg)
    return m2 * math.exp(-(v_star - v0 - C_MPS * math.log(m0 / m1)) / C_MPS) - m3


def _closed_x_star(mode: str, p_kg: float, v0: float, v_star: float) -> float:
    """The toy's x* [kg]: the stage-1 closed form, brentq on the ideal speed otherwise."""
    if mode == "stage1":
        m0, m1, m2, m3 = _masses(p_kg)
        return m0 - m1 * math.exp((v_star - v0 - C_MPS * math.log(m2 / m3)) / C_MPS)
    load = M_P2 if mode == "stage2" else M_P1 + M_P2
    return float(
        brentq(lambda x: _ideal_speed(mode, x, p_kg, v0) - v_star, 0.0, 0.999 * load, xtol=1e-12)
    )


def _closed_capacity(v_star: float) -> float:
    """The toy's payload capacity [kg] from rest at full load: c ln(m0/m1) + c ln(m2/m3)
    = V* (brentq)."""
    return float(
        brentq(lambda p: _ideal_speed("stage1", 0.0, p, 0.0) - v_star, 0.0, 1e3, xtol=1e-12)
    )


P_REF_KG = 60.0
"""Toy reference payload [kg] of the closed-form tests (the toy's capacity from rest is
about 94 kg)."""


@pytest.fixture(scope="module")
def toy_solves() -> dict[str, OffloadResult]:
    """solve_offload on the toy at P_REF_KG with the head start V0_MPS, per mode."""
    return {
        mode: solve_offload(_toy_factory(V0_MPS), _toy_vehicle(P_REF_KG), mode, P_REF_KG)
        for mode in ("stage1", "stage2", "both")
    }


def _assert_feasible_side(res: OffloadResult, root: float, xtol_kg: float) -> None:
    """x* is the largest evaluated offload with m_res >= 0 at the final tolerance, within
    xtol_kg of the closed-form root on its feasible side."""
    final = [e for e in res.evaluations if e.search == FINAL_LOG and e.ok]
    best = max(e.offload_kg for e in final if e.m_res_kg >= 0.0)
    assert res.offload_kg == best
    assert root - xtol_kg - INTEGRATION_SLACK_KG <= res.offload_kg <= root + INTEGRATION_SLACK_KG


@pytest.mark.parametrize("mode", ["stage1", "stage2", "both"])
def test_toy_offload_matches_the_closed_form(
    toy_solves: dict[str, OffloadResult], mode: str
) -> None:
    """Each mode at P_ref = 60 kg with v0 = 300 m/s: status ok, gamma*_ref within 0.01
    deg of the toy's optimum, x* within final_payload_xtol_kg (0.05 kg) below the
    closed-form root at V*(gamma*_ref) (stage 1: m0 - m1 exp((V* - v0 - c ln(m2/m3))/c);
    stage 2 and both: brentq here), x* the largest final evaluation with m_res >= 0;
    every flown final-mode evaluation's m_res equals the closed form (1e-6 kg); the
    recorded run flies P_ref, inserted with 0 <= m_res < 0.05 kg; the independent
    payload search of the offloaded toy reproduces P_ref within TOY_FLAG_REL x P_ref; m_res
    changes sign once along x (no nonmonotone flag); the result's evaluation is labelled
    with the true payload P_ref; the offloaded vehicle is lighter by x* (1e-9 kg)."""
    res = toy_solves[mode]
    budget = _toy_budget()
    assert res.status == OK_STATUS and res.failure_kind is None
    assert abs(res.gamma_star_rad - GAMMA_OPT_RAD) < math.radians(0.01)
    v_star = _target_mps(res.gamma_star_rad)
    root = _closed_x_star(mode, P_REF_KG, V0_MPS, v_star)
    assert 0.0 < root < res.load_kg
    _assert_feasible_side(res, root, budget.final_payload_xtol_kg)
    for e in res.evaluations:
        if e.search == FINAL_LOG and e.ok:
            expected = _closed_m_res(mode, e.offload_kg, P_REF_KG, V0_MPS, v_star)
            assert e.m_res_kg == pytest.approx(expected, abs=1e-6)
    assert res.recorded is not None and res.recorded.status == INSERTED_STATUS
    assert 0.0 <= res.recorded.m_res_kg < budget.final_payload_xtol_kg
    assert res.recorded.m_res_kg == pytest.approx(res.m_res_kg, abs=INTEGRATION_SLACK_KG)
    assert res.at_offload is not None and res.at_offload.payload_kg == P_REF_KG
    assert res.verification is not None and res.verification.passed
    assert abs(res.verification.delta_kg) <= TOY_FLAG_REL * P_REF_KG
    assert res.verification.tolerance_kg == pytest.approx(TOY_FLAG_REL * P_REF_KG, rel=1e-15)
    assert not any(NONMONOTONE_FLAG in f for f in res.flags)
    assert all(f.startswith(OFFLOAD_FLAG_PREFIX) for f in res.flags)
    assert res.offloaded_vehicle is not None
    full = _toy_vehicle(P_REF_KG).liftoff_mass_kg()
    assert res.offloaded_vehicle.liftoff_mass_kg() == pytest.approx(full - res.offload_kg, abs=1e-9)
    assert res.fraction_of_load == res.offload_kg / res.load_kg
    assert {e.search for e in res.evaluations} == {X1_LOG, X2_LOG, FINAL_LOG}
    assert res.n_evaluations >= len(res.evaluations)


def test_vacuum_offload_equals_the_ideal_screening() -> None:
    """Zero gravity and vacuum with the screening Isp equal to the engine Isp: at P_ref =
    the toy's closed-form capacity from rest, the stage-1 offload for a head start v0 is
    the propellant whose removal lowers the ideal delta-v by exactly v0, which is
    ``vehicle.stage1_propellant_saved_kg``: x* equals it within final_payload_xtol_kg
    (the target's gamma* term, below 1e-3 m/s at gamma*_ref, adds at most 1e-3 m/s x m0 /
    c of offload)."""
    p_ref = _closed_capacity(V_STAR_MPS)
    vehicle = _toy_vehicle(p_ref)
    res = solve_offload(_toy_factory(V0_MPS), vehicle, "stage1", p_ref, verify=False)
    assert res.status == OK_STATUS
    dv_gamma = _target_mps(res.gamma_star_rad) - V_STAR_MPS
    assert 0.0 <= dv_gamma < 1e-3
    yardstick = stage1_propellant_saved_kg(vehicle, V0_MPS)
    slack = dv_gamma * vehicle.liftoff_mass_kg() / C_MPS + INTEGRATION_SLACK_KG
    xtol = _toy_budget().final_payload_xtol_kg
    assert yardstick - xtol - slack <= res.offload_kg <= yardstick + slack


def test_no_offload_above_the_capacity_from_rest() -> None:
    """v0 = 0 and P_ref 1 kg above the toy's closed-form capacity: the full-load toy
    cannot carry P_ref, so status no_offload, x* = 0, m_res(0) < 0, the shortfall
    -dv_margin(0) = V*(gamma*_ref) - D_id(P_ref) (1e-6 relative), the recorded run at x =
    0 short of the target carrying the evaluation's figures, and no verification."""
    p_ref = _closed_capacity(V_STAR_MPS) + OVER_CAPACITY_KG
    res = solve_offload(_toy_factory(0.0), _toy_vehicle(p_ref), "stage1", p_ref)
    assert res.status == NO_OFFLOAD_STATUS
    assert res.offload_kg == 0.0 and res.m_res_kg < 0.0 and math.isnan(res.root_kg)
    expected = _target_mps(res.gamma_star_rad) - _ideal_speed("stage1", 0.0, p_ref, 0.0)
    assert expected > 0.0
    assert res.dv_shortfall_mps == pytest.approx(expected, rel=1e-6)
    assert res.recorded is not None and res.recorded.status == SHORT_OF_ORBIT_STATUS
    assert res.recorded.figures_from == FROM_FINAL_EVALUATION
    assert res.verification is None
    assert not any(NONMONOTONE_FLAG in f for f in res.flags)


def test_own_capacity_as_reference_gives_an_offload_near_zero() -> None:
    """The pad control's rule on the toy: v0 = 0 and P_ref = the toy's own searched P*
    (run_search; 0 <= m_res(P*) < 0.05 kg): the stage-1 offload solve ends ok with 0 <=
    x <= final_payload_xtol_kg / s, s = |dm_res/dx| the secant over the final search's
    bracket (``_bracket_slope``)."""
    budget = _toy_budget()
    rec = run_search(HeadStartToy(_toy_vehicle(P_REF_KG), 0.0, budget))
    assert rec.status == OK_STATUS
    p_ref = rec.payload_kg
    res = solve_offload(_toy_factory(0.0), _toy_vehicle(p_ref), "stage1", p_ref)
    assert res.status == OK_STATUS
    slope = _bracket_slope(res)
    assert slope > 0.0
    assert 0.0 <= res.offload_kg <= budget.final_payload_xtol_kg / slope


def test_offload_beyond_the_load_backs_off() -> None:
    """With a 1 t half-bracket the first high end of X1 (1000 kg) takes more than the
    toy's whole stage-1 load (800 kg): that evaluation fails typed (offload_range, an
    OffloadInfeasible, one of search.INFEASIBLE), the bracket backs off halfway (500 kg,
    which flies with m_res < 0), the backoff is flagged with the abscissa note, and x*
    still matches the stage-1 closed form."""
    budget = _toy_budget(payload_half_bracket_t=STAGE1_RANGE_HALF_BRACKET_T)
    factory = _toy_factory(V0_MPS, budget)
    res = solve_offload(factory, _toy_vehicle(P_REF_KG), "stage1", P_REF_KG, verify=False)
    assert res.status == OK_STATUS
    x1 = [e for e in res.evaluations if e.search == X1_LOG]
    failed = [e for e in x1 if not e.ok]
    assert [e.offload_kg for e in failed] == [1000.0]
    assert failed[0].failure is not None and failed[0].failure.startswith(OFFLOAD_RANGE_KIND)
    assert 500.0 in {e.offload_kg for e in x1 if e.ok}
    backoff = [f for f in res.flags if "P1_backoff" in f]
    assert backoff and backoff[0].startswith(f"{OFFLOAD_FLAG_PREFIX} {ABSCISSA_NOTE} ")
    assert OFFLOAD_RANGE_KIND in backoff[0]
    root = _closed_x_star("stage1", P_REF_KG, V0_MPS, _target_mps(res.gamma_star_rad))
    _assert_feasible_side(res, root, budget.final_payload_xtol_kg)
    assert issubclass(OffloadInfeasible, PreludeFailure)
    assert issubclass(OffloadInfeasible, INFEASIBLE)
    exc = OffloadInfeasible(OFFLOAD_RANGE_KIND, "too much")
    again = pickle.loads(pickle.dumps(exc))
    assert (again.kind, again.message) == (OFFLOAD_RANGE_KIND, "too much")


# ------------------------------------------------------------------ problem plumbing


@dataclass
class _Probe:
    """A RecordingProblem stand-in that logs every evaluate call (payload, gamma*, the
    store, seed) and returns m_res = 1 - payload / 1e5."""

    vehicle: Vehicle
    budget: SearchBudget
    calls: list[tuple[float, float, WarmStore, WarmEntry | None]] = field(default_factory=list)

    @property
    def payload_kg(self) -> float:
        return self.vehicle.payload_mass_kg

    def evaluate(
        self,
        payload_kg: float,
        gamma_star_rad: float,
        warm: WarmStore,
        mode: str,
        *,
        seed: WarmEntry | None = None,
    ) -> ResidualResult:
        warm.claim(self)
        self.calls.append((payload_kg, gamma_star_rad, warm, seed))
        m = 1.0 - payload_kg / 1e5
        return ResidualResult(
            payload_kg, gamma_star_rad, m, m, 0.1, (1.0, 2.0), 0.0, "", 0, 0, mode
        )

    def record(self, res: ResidualResult) -> RecordedRun:
        raise AssertionError("not recorded here")


def test_offload_problem_relabels_at_its_boundary() -> None:
    """OffloadProblem.evaluate(x, ...): the factory's problem of the vehicle offloaded by x
    is evaluated at P_ref (never at x), one problem and one fresh store per offload,
    reused for the same x; the result and the warm entry carry x in the payload slot; the
    seed handed down is the nearest entry relabelled with P_ref; the protocol's grid
    abscissa is x = 0; a plain WarmStore is a TypeError, a store of another problem a
    ValueError; an offload beyond the load is OffloadInfeasible."""
    built: list[_Probe] = []
    budget = _toy_budget()

    def factory(vehicle: Vehicle) -> _Probe:
        built.append(_Probe(vehicle, budget))
        return built[-1]

    vehicle = _toy_vehicle(10.0)
    problem = OffloadProblem.from_factory(factory, vehicle, "stage2", 55.0)
    assert problem.payload_kg == 0.0 and problem.budget is budget and problem.load_kg == M_P2
    warm = OffloadWarmStore()
    r1 = problem.evaluate(40.0, 0.3, warm, SEARCH_MODE)
    r2 = problem.evaluate(40.0, 0.31, warm, SEARCH_MODE)
    r3 = problem.evaluate(70.0, 0.32, warm, SEARCH_MODE)
    assert [r.payload_kg for r in (r1, r2, r3)] == [40.0, 40.0, 70.0]
    assert [e.payload_kg for e in warm.entries] == [40.0, 40.0, 70.0]
    assert len(built) == 3  # from_factory's budget probe, then one per offload
    assert built[1].vehicle.stages[1].propellant_mass_kg == M_P2 - 40.0
    assert built[2].vehicle.stages[1].propellant_mass_kg == M_P2 - 70.0
    payloads = [c[0] for p in built[1:] for c in p.calls]
    assert payloads == [55.0, 55.0, 55.0]
    assert built[1].calls[0][2] is built[1].calls[1][2]
    assert built[1].calls[0][2] is not built[2].calls[0][2]
    assert built[1].calls[0][3] is None
    seed = built[1].calls[1][3]
    assert seed is not None and seed.payload_kg == 55.0 and seed.gamma_star_rad == 0.3
    assert warm.evaluations == 3
    with pytest.raises(TypeError):
        problem.evaluate(40.0, 0.3, WarmStore(), SEARCH_MODE)
    other = OffloadProblem.from_factory(factory, vehicle, "stage2", 55.0)
    with pytest.raises(ValueError):
        other.evaluate(40.0, 0.3, warm, SEARCH_MODE)
    with pytest.raises(OffloadInfeasible) as info:
        problem.evaluate(M_P2, 0.3, warm, SEARCH_MODE)
    assert info.value.kind == OFFLOAD_RANGE_KIND
    assert warm.evaluations == 4 and M_P2 not in warm.members
    for bad in (-1.0, math.nan):
        with pytest.raises(ValueError):
            OffloadProblem.from_factory(factory, vehicle, "stage1", bad)
    with pytest.raises(ValueError):
        OffloadProblem.from_factory(factory, Vehicle(stages=(vehicle.stages[0],)), "both", 1.0)


def test_nonmonotone_flags_on_synthetic_logs() -> None:
    """One change from m_res >= 0 to < 0 per search passes, as does a search with every
    m_res < 0 (a no_offload final search) beside searches that change sign once; two
    changes, or one from < 0 to >= 0, flag offload_nonmonotone naming the search; failed
    evaluations do not count."""

    def log(name: str, pairs: list[tuple[float, float]]) -> list[OffloadEval]:
        return [OffloadEval(name, x, m, m, None) for x, m in pairs]

    good = log(X1_LOG, [(0.0, 3.0), (20.0, 1.0), (40.0, -1.0)]) + log(FINAL_LOG, [(0.0, -0.1)])
    failed = [OffloadEval(X2_LOG, 30.0, math.nan, math.nan, "offload_range: x")]
    assert nonmonotone_flags(good + failed) == ()
    bumpy = log(X2_LOG, [(40.0, -1.0), (0.0, 3.0), (20.0, -0.5), (30.0, 0.2)])
    flags = nonmonotone_flags(good + bumpy)
    assert len(flags) == 1 and NONMONOTONE_FLAG in flags[0] and "X2" in flags[0]
    assert flags[0].startswith(OFFLOAD_FLAG_PREFIX)
    rising = log(FINAL_LOG, [(0.0, -1.0), (10.0, 1.0)])
    assert len(nonmonotone_flags(rising)) == 1


def test_verification_mismatch_is_flagged() -> None:
    """``verify_offload`` against a reference 5 kg off the toy's own capacity: not passed,
    delta = P* - P_ref, tolerance TOY_FLAG_REL x P_ref; solve_offload's flag text names
    offload_verify_mismatch (checked through the helper that writes it)."""
    from launchsim.offload import _verification_flags

    budget = _toy_budget()
    toy = HeadStartToy(_toy_vehicle(P_REF_KG), V0_MPS, budget)
    p_star = run_search(toy).payload_kg
    v = verify_offload(_toy_factory(V0_MPS), _toy_vehicle(P_REF_KG), p_star + 5.0, budget)
    assert not v.passed and v.status == OK_STATUS
    assert v.delta_kg == pytest.approx(-5.0, abs=1e-12)
    assert v.tolerance_kg == pytest.approx(TOY_FLAG_REL * (p_star + 5.0), rel=1e-15)
    flags = _verification_flags(v, 12.0)
    assert flags[0].startswith(f"{OFFLOAD_FLAG_PREFIX} {VERIFY_MISMATCH_FLAG}")


def test_a_failed_search_becomes_a_status_with_its_kind() -> None:
    """A factory whose problem cannot fly at any gamma* (every evaluation a typed
    failure): the grid at x = 0 fails, so status search_failed with failure_kind grid,
    the message marked with the abscissa note, NaN figures, no records; a figure of
    merit other than payload refuses the verification."""

    @dataclass
    class Grounded(_Probe):
        def evaluate(self, *args: object, **kwargs: object) -> ResidualResult:
            raise GuidanceFailure("no_kick", "never kicks")

    budget = _toy_budget()

    def factory(vehicle: Vehicle) -> Grounded:
        return Grounded(vehicle, budget)

    res = solve_offload(factory, _toy_vehicle(10.0), "stage1", 10.0)
    assert res.status == SEARCH_FAILED_STATUS and res.failure_kind == "grid"
    assert res.failure_message is not None and res.failure_message.startswith(ABSCISSA_NOTE)
    assert math.isnan(res.offload_kg) and math.isnan(res.m_res_kg)
    assert res.recorded is None and res.verification is None and res.at_offload is None
    assert len(res.grid) == len(budget.gamma_grid_rad) and res.n_evaluations > 0
    residual = _toy_budget(figure_of_merit="residual")
    with pytest.raises(ValueError):
        solve_offload(_toy_factory(V0_MPS, residual), _toy_vehicle(10.0), "stage1", 10.0)


# ------------------------------------------------------------------- slow: gate fork


def _gate_context(repo_root: Path, name: str, *, shipped: bool = False) -> SearchContext:
    """The SearchContext of run name of the gate fork's silo_screening_2d experiment at
    the test budget (its shared search block with search_rtol = TEST_SEARCH_RTOL), or at
    the shipped budget (the block as written) when shipped."""
    rr = load_experiment(repo_root / GATE_EXPERIMENT).runs[name]
    ctx = SearchContext.from_run(rr.run, rr.to_vehicle())
    if shipped:
        return ctx
    planar = rr.run.planar
    assert planar is not None
    cfg = planar.search.model_copy(update={"search_rtol": TEST_SEARCH_RTOL})
    return dataclasses.replace(ctx, budget=SearchBudget.from_config(cfg, planar.checks))


@dataclass(frozen=True)
class GateSolves:
    """The gate fork at one budget: the pad's P* (the reference payload, from its own
    payload search) and the stage-1 offload solves of the pad (the control; None when
    not asked for) and of silo_cold, with their contexts."""

    p_ref_kg: float
    pad: OffloadResult | None
    silo: OffloadResult
    pad_ctx: SearchContext
    silo_ctx: SearchContext


def _gate_solves(
    pad: SearchContext, silo: SearchContext, *, control: bool = True, verify: bool = True
) -> GateSolves:
    record = run_search(pad)
    assert record.status == OK_STATUS
    p_ref = record.payload_kg
    control_res = None
    if control:
        control_res = solve_offload(planar_problem_factory(pad), pad.vehicle, "stage1", p_ref)
    silo_res = solve_offload(
        planar_problem_factory(silo), silo.vehicle, "stage1", p_ref, verify=verify
    )
    return GateSolves(p_ref, control_res, silo_res, pad, silo)


@pytest.fixture(scope="module")
def gate(repo_root: Path) -> GateSolves:
    """The gate fork at the test budget (search_rtol TEST_SEARCH_RTOL, final 1e-10 as
    shipped; CLAUDE.md: rtol <= 1e-9 in tests), the full shipped gamma* grid: the pad's
    P*, the stage-1 pad control and silo_cold's stage-1 offload with its verification.
    The convergence test flies the shipped budget on its own."""
    return _gate_solves(_gate_context(repo_root, "pad"), _gate_context(repo_root, "silo_cold"))


def _bracket_slope(res: OffloadResult) -> float:
    """|dm_res/dx| [kg/kg] from the solve's own logged evaluations: the secant between the
    largest offload with m_res >= 0 and the smallest with m_res < 0 of the final search,
    or of X2 when the final search has no such pair (no_offload), else of X1."""
    for name in (FINAL_LOG, X2_LOG, X1_LOG):
        flown = [e for e in res.evaluations if e.search == name and e.ok]
        pos = [e for e in flown if e.m_res_kg >= 0.0]
        neg = [e for e in flown if e.m_res_kg < 0.0]
        if pos and neg:
            lo = max(pos, key=lambda e: e.offload_kg)
            hi = min(neg, key=lambda e: e.offload_kg)
            return (lo.m_res_kg - hi.m_res_kg) / (hi.offload_kg - lo.offload_kg)
    raise AssertionError("no logged search brackets m_res = 0")


@pytest.mark.slow
def test_gate_silo_offload_recorded_run_and_verification(gate: GateSolves) -> None:
    """silo_cold's stage-1 offload at the pad's P*: status ok, the recorded run flies
    exactly P_ref on the vehicle offloaded by x* (its release mass is the full-load
    liftoff mass minus x*: a cold start burns nothing on the track) and ends inserted
    with 0 <= m_res < final_payload_xtol_kg; the independent payload search of the
    offloaded vehicle reproduces P_ref within checks.search_final_flag_rel x P_ref (the
    spec'd flag threshold, about 66 kg of offload here) and, as a regression guard on the
    measured gap (+0.0084 kg), within VERIFY_GAP_GUARD_XTOLS x final_payload_xtol_kg;
    m_res falls through zero once along x in every logged search (no nonmonotone flag).
    The solved x* is a validation measurement only (about 41.3 t; the handoff probe read
    about 41 t off by hand); the finding comes from step 8's pre-registered experiment."""
    res = gate.silo
    budget = gate.silo_ctx.budget
    assert budget.search_rtol == TEST_SEARCH_RTOL
    assert res.status == OK_STATUS, (res.failure_kind, res.failure_message)
    assert 0.0 < res.offload_kg < res.load_kg
    rec = res.recorded
    assert rec is not None and rec.status == INSERTED_STATUS
    assert rec.figures_from == FROM_RECORDED_RUN
    assert 0.0 <= rec.m_res_kg < budget.final_payload_xtol_kg
    assert res.at_offload is not None and res.at_offload.payload_kg == gate.p_ref_kg
    v = gate.silo_ctx.vehicle
    full = sum(s.wet_mass_kg for s in v.stages) + v.fairing_mass_kg + gate.p_ref_kg
    assert rec.trace.y_release is not None
    m_release = float(PLANAR_LAYOUT.get(rec.trace.y_release, "m_kg"))
    assert m_release == pytest.approx(full - res.offload_kg, abs=1e-6)
    ver = res.verification
    assert ver is not None and ver.status == OK_STATUS
    assert ver.tolerance_kg == pytest.approx(budget.final_flag_rel * gate.p_ref_kg, rel=1e-15)
    assert abs(ver.delta_kg) <= ver.tolerance_kg and ver.passed
    assert abs(ver.delta_kg) < VERIFY_GAP_GUARD_XTOLS * budget.final_payload_xtol_kg
    assert not any(VERIFY_MISMATCH_FLAG in f or NONMONOTONE_FLAG in f for f in res.flags)


@pytest.mark.slow
def test_gate_pad_control_is_within_the_bound(gate: GateSolves) -> None:
    """The stage-1 pad control (phase file section 5.3): the pad offloaded at its own P*
    returns 0 <= x_pad <= final_payload_xtol_kg / s, s = |dm_res/dx| from the control's
    own logged evaluations (``_bracket_slope``), since the pad's reference run keeps less
    than final_payload_xtol_kg of residual for a stage-1 offload to remove. The control
    may end no_offload (x_pad = 0) when its final m_res(0) falls a few grams below zero
    (measured -0.0017 kg). The cause is not its gamma*_ref, 0.004 deg from the pad
    search's: the control's sits nearer the final-mode vertex in gamma*, so the offset is
    worth about +0.4 g, upward (cold final evaluations measure +0.53 g at the control's
    gamma*_ref against +0.16 g at the pad search's). It is the LTG shooting, warm-started
    from X2's entry at x = 0.25 kg, converging to another point inside its acceptance
    box, 2.2 g below the cold one (docs/physics.md, "Pad control, and why"). Then the
    shortfall must stay within final_payload_xtol_kg, the symmetric half of the same
    bound."""
    assert gate.pad_ctx.budget.search_rtol == TEST_SEARCH_RTOL
    res = gate.pad
    assert res is not None
    budget = gate.pad_ctx.budget
    xtol = budget.final_payload_xtol_kg
    assert res.status in (OK_STATUS, NO_OFFLOAD_STATUS), (res.failure_kind, res.failure_message)
    slope = _bracket_slope(res)
    assert slope > 0.0
    assert 0.0 <= res.offload_kg <= xtol / slope
    if res.status == NO_OFFLOAD_STATUS:
        assert res.offload_kg == 0.0 and -xtol < res.m_res_kg < 0.0
    else:
        assert 0.0 <= res.m_res_kg < xtol
    assert not any(NONMONOTONE_FLAG in f for f in res.flags)


@pytest.mark.slow
def test_gate_offload_converges_under_a_tightened_budget(repo_root: Path) -> None:
    """CLAUDE.md's convergence rule on silo_cold's stage-1 offload: the shipped budget
    (search rtol 1e-8, the budget the offload experiment will run; as in
    tests/test_convergence_2d.py, amendment 3 asks for the convergence of the shipped
    budget itself) against its tightening by the experiment's checks.convergence
    (``SearchContext.tightened``: every tolerance / 10 through ``SearchBudget.tightened``,
    the max_step caps x 0.5), each chain with its own pad P* as the reference: x* moves
    by less than rel_tol (1e-3) x x*."""
    planar = load_experiment(repo_root / GATE_EXPERIMENT).baseline.run.planar
    assert planar is not None
    conv: ConvergenceConfig = planar.checks.convergence
    pad = _gate_context(repo_root, "pad", shipped=True)
    silo = _gate_context(repo_root, "silo_cold", shipped=True)
    assert pad.budget.search_rtol == planar.search.search_rtol
    shipped = _gate_solves(pad, silo, control=False, verify=False)
    tight = _gate_solves(pad.tightened(conv), silo.tightened(conv), control=False, verify=False)
    assert shipped.silo.status == tight.silo.status == OK_STATUS
    x, x_t = shipped.silo.offload_kg, tight.silo.offload_kg
    assert abs(x_t - x) <= conv.rel_tol * x
