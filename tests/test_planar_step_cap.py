"""The planar max_step cap (user decision of 2026-09-30; docs/physics.md, "Integrator"):
every planar flight phase (COAST_PRE_IGN, VERTICAL_RISE, KICK, GRAVITY_TURN,
COAST_STAGING, LTG_BURN, COAST) integrates with max_step = min(its ramp or lag cap,
``IntegratorSettings.planar_max_step_s``); the prelude (HOLD, the ASSIST push) keeps its
own caps, and the 1-D planner never reads the setting (the 1-D golden stays
byte-identical, tests/test_golden_1d.py). The runs are flown from
experiments/silo_screening_2d.yaml at fixed guidance inputs (a 3 deg kick and a fixed
LTG pair; the status they end in does not matter here)."""

from __future__ import annotations

import dataclasses
import math
from pathlib import Path

import numpy as np
import pytest

from launchsim import sim
from launchsim.cli import load_experiment
from launchsim.config import ResolvedExperiment
from launchsim.constants import MU_EARTH_M3S2, R_EARTH_M
from launchsim.dynamics import InverseSquareGravity
from launchsim.phases import (
    ASSIST_KIND,
    HOLD_KIND,
    IgnitionSpec,
    IntegratorSettings,
    RunTrace,
    VerticalPlanner,
    max_step_cap,
)
from launchsim.phases.planar import (
    COAST,
    COAST_PRE_IGN,
    COAST_STAGING,
    GRAVITY_TURN,
    KICK,
    LTG_BURN,
    VERTICAL_RISE,
    PlanarPlanner,
)
from launchsim.search import FINAL_MODE
from launchsim.vehicle import Vehicle

PLANAR_FLIGHT_KINDS = frozenset(
    {COAST_PRE_IGN, VERTICAL_RISE, KICK, GRAVITY_TURN, COAST_STAGING, LTG_BURN, COAST}
)
"""Every phase kind the planar planner integrates after the flight start."""
PRELUDE_KINDS = frozenset({HOLD_KIND, ASSIST_KIND})
"""The prelude's phase kinds, which keep their own caps (ramp, lag, push)."""
SHIPPED_CAP_S = 2.0
"""The shipped integrator.planar_max_step_s [s]."""
SMALL_CAP_S = 0.5
"""A cap [s] below the shipped one (still above the push cap, t_push / push_steps =
0.052 s on silo_cold), to show which phases follow the setting."""
DELTA_RAD = math.radians(3.0)
"""A fixed kick angle [rad] (gamma_MECO about 22 deg on the pad)."""
LTG_PAIR = (0.47, 0.0012)
"""A fixed stage-2 linear-tangent pair (a, b [1/s]): about 25 deg pitch at ignition."""
EXPECTED_KINDS = {
    "pad": frozenset({HOLD_KIND, VERTICAL_RISE, KICK, GRAVITY_TURN, COAST_STAGING, LTG_BURN}),
    "silo_cold": frozenset(
        {ASSIST_KIND, COAST_PRE_IGN, KICK, GRAVITY_TURN, COAST_STAGING, LTG_BURN}
    ),
    "silo_failed": frozenset({ASSIST_KIND, COAST}),
}
"""The phase kinds each run flies (so every planar flight kind is covered)."""


@pytest.fixture(scope="module")
def experiment(repo_root: Path) -> ResolvedExperiment:
    """experiments/silo_screening_2d.yaml, resolved."""
    return load_experiment(repo_root / "experiments" / "silo_screening_2d.yaml")


def _fly(exp: ResolvedExperiment, name: str, cap_s: float | None = None) -> RunTrace:
    """Run ``name`` recorded at the fixed guidance inputs, with its own integrator
    settings (cap_s None) or with planar_max_step_s replaced by cap_s."""
    run = exp.runs[name]
    vehicle = run.to_vehicle()
    setup = sim.planar_setup(run.run, vehicle)
    settings = setup.settings
    if cap_s is not None:
        settings = dataclasses.replace(settings, planar_max_step_s=cap_s)
    planner = PlanarPlanner(
        vehicle,
        setup.ignition,
        setup.guidance,
        setup.env,
        run.run.end,
        settings,
        target=setup.target,
        ltg=setup.budget.ltg_for(FINAL_MODE),
    )
    fails = setup.ignition[vehicle.stage_names[0]].fails
    delta = None if fails else DELTA_RAD
    return planner.run(delta, setup.assist, setup.track, ltg=None if fails else LTG_PAIR)


def test_shipped_setting_is_the_two_second_cap(experiment: ResolvedExperiment) -> None:
    """Every run of the experiment carries the shipped, shared planar cap."""
    caps = {r.run.integrator.planar_max_step_s for r in experiment.runs.values()}
    assert caps == {SHIPPED_CAP_S}
    assert IntegratorSettings().planar_max_step_s == SHIPPED_CAP_S


@pytest.mark.parametrize("name", sorted(EXPECTED_KINDS))
def test_every_planar_flight_phase_is_capped(experiment: ResolvedExperiment, name: str) -> None:
    """In the recorded trace every planar flight phase carries exactly max_step =
    min(the ramp or lag cap of ``max_step_cap`` for its own schedule and start time,
    planar_max_step_s) (the shipped 2 s, and 0.5 s when the setting says so), so no
    flight phase is given a smaller cap (the push cap, say) by mistake; the prelude
    phases keep their own caps and fly bit for bit the same whatever the planar cap."""
    shipped = _fly(experiment, name)
    small = _fly(experiment, name, SMALL_CAP_S)
    assert {p.spec.kind for p in shipped.phases} == EXPECTED_KINDS[name]
    run = experiment.runs[name]
    settings = sim.planar_setup(run.run, run.to_vehicle()).settings
    for trace, cap in ((shipped, SHIPPED_CAP_S), (small, SMALL_CAP_S)):
        flight = [p for p in trace.phases if p.spec.kind in PLANAR_FLIGHT_KINDS]
        assert flight
        for p in flight:
            own = max_step_cap(p.spec.params.schedule, p.spec.t0, settings)
            assert p.spec.max_step == min(own, cap), (p.spec.kind, p.spec.t0)
        assert all(p.spec.max_step <= cap for p in flight)
        assert any(p.spec.max_step == cap for p in flight)
    prelude_a = [p for p in shipped.phases if p.spec.kind in PRELUDE_KINDS]
    prelude_b = [p for p in small.phases if p.spec.kind in PRELUDE_KINDS]
    assert len(prelude_a) == len(prelude_b) > 0
    for pa, pb in zip(prelude_a, prelude_b, strict=True):
        assert pa.spec.max_step == pb.spec.max_step
        assert np.array_equal(pa.y_end, pb.y_end)
    if name == "silo_cold":  # the 2 s ramp lit 0.5 s after release: its cap is smaller
        ramp_cap = 2.0 / settings.ramp_steps
        kicks = [p.spec.max_step for p in shipped.phases if p.spec.kind == KICK]
        assert min(kicks) == pytest.approx(ramp_cap, rel=1e-12)
        pushes = [p.spec.max_step for p in shipped.phases if p.spec.kind == ASSIST_KIND]
        assert all(0.0 < s < SMALL_CAP_S for s in pushes)


def test_one_d_phases_ignore_the_planar_cap(f9_vehicle: Vehicle) -> None:
    """The 1-D planner never reads planar_max_step_s: a pad run of the F9 (its 2 s ramp
    lit at -2 s, to stage-1 burnout) flies the same phases with the same max_step and
    the same end states bit for bit with the cap at 2 s, 0.05 s or none, and its burn
    after the ramp stays uncapped."""
    g_eff = MU_EARTH_M3S2 / R_EARTH_M**2
    ignition = {"stage1": IgnitionSpec(-2.0), "stage2": IgnitionSpec()}
    traces = [
        VerticalPlanner(
            f9_vehicle,
            ignition,
            InverseSquareGravity(MU_EARTH_M3S2),
            g_eff,
            "stage1_burnout",
            IntegratorSettings(planar_max_step_s=cap),
        ).run_pad()
        for cap in (SHIPPED_CAP_S, 0.05, math.inf)
    ]
    ref = traces[0]
    assert any(math.isinf(p.spec.max_step) for p in ref.phases)
    for tr in traces[1:]:
        assert [p.spec.max_step for p in tr.phases] == [p.spec.max_step for p in ref.phases]
        for pa, pb in zip(ref.phases, tr.phases, strict=True):
            assert np.array_equal(pa.y_end, pb.y_end)
    stage = f9_vehicle.stages[0]
    schedule = stage.schedule(-2.0, None, False)
    assert max_step_cap(schedule, 10.0, IntegratorSettings(planar_max_step_s=0.05)) == math.inf


def test_planar_cap_must_be_positive() -> None:
    """IntegratorSettings refuses a planar cap <= 0 or NaN (math.inf means none)."""
    for bad in (0.0, -1.0, math.nan):
        with pytest.raises(ValueError, match="planar_max_step_s"):
            IntegratorSettings(planar_max_step_s=bad)
    assert IntegratorSettings(planar_max_step_s=math.inf).planar_max_step_s == math.inf
