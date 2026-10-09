"""The screened search and the frozen sets (SP7 step S2, its second part; design 4.2.6, the
source note docs/phases/inputs/2026-10-08-SP7-sources.md section 9.3, D-SP7-37).

The fast tests drive the pure search of structure.py with synthetic sizing functions whose
extremes are known in closed form (separable sums over the structure file's own coefficient
paths and ranges; one with an interaction whose direction reverses at the found end, for the
polish of D-SP7-38), and the placement on SP1's penalty curve with synthetic dm(x). The slow
test flies each committed pad baseline from scratch, re-runs searches A to C at its
headline push and asserts the structure file's frozen sets (D-SP7-31: no offload is solved,
only sizings). Tests never read results/.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import math
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pytest

from launchsim import cli, sim
from launchsim import structure as st
from launchsim.config import (
    STRUCTURE_PHYSICS_SETS,
    STRUCTURE_SET_NAMES,
    StructureConfig,
    StructureSetsConfig,
)
from launchsim.constants import (
    OFFLOAD_PER_KG_STAGE1_DRY,
    OFFLOAD_PER_KG_STAGE2_DRY,
    SP1_PENALTY_DRY_MASS_KG,
    SP1_PENALTY_OFFLOAD_KG,
)


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
SP1_HEADLINE_OFFLOAD_KG = ss.HEADLINE_OFFLOAD_KG

PARENT_COMMIT = "4494fe1"
"""The commit the frozen sets were searched on (S2's parent)."""
SEARCH_FILES = (
    (
        ss.GATE_STRUCTURE,
        ss.REPO / "experiments" / "silo_offload_2d.yaml",
        ss.HEADLINE_OFFLOAD_KG,
        ss.P_REF_KG,
    ),
    (
        ss.README_STRUCTURE,
        ss.REPO / "experiments" / "silo_offload_2d_readme.yaml",
        ss.README_BRIDGE_OFFLOAD_KG,
        ss.README_P_REF_KG,
    ),
)
"""Each structure file with its committed experiment, its headline offload and P_ref."""


@pytest.fixture(scope="module")
def ranges() -> tuple[st.CoefficientRange, ...]:
    """The gate structure file's 35 coefficients."""
    return ss.structure_config().coefficient_ranges()


def _frac(item: st.CoefficientRange, value: Any) -> float:
    """(value - low)/(high - low) of a ranged coefficient."""
    assert item.low is not None and item.high is not None
    return (float(value) - float(item.low)) / (float(item.high) - float(item.low))


class Separable:
    """A synthetic sizing: dm1 and dm2 [kg] as sums of one closed-form term per coefficient
    (so every extreme is the extreme of its own term), the stage-2 terms only when the upper
    stack is "exceeded" (the step row or the 4.0 g0 cap), a margin lowering dm."""

    def __init__(self, ranges: tuple[st.CoefficientRange, ...], interior: float = 0.3) -> None:
        self.ranges = {r.path: r for r in ranges}
        self.interior = interior
        self.calls = 0
        rng = np.random.default_rng(7)
        self.weights = {r.path: float(rng.uniform(5.0, 50.0)) for r in ranges}
        self.signs = {r.path: (1.0 if i % 3 else -1.0) for i, r in enumerate(ranges)}
        self.discrete = {
            st.PATH_S_DG: {1: 0.0, 0: 30.0},
            st.PATH_GERARD_ROW: {"ring_common_z": 0.0, "plate_limited": 200.0},
            st.PATH_SKIRT_ENVELOPE_PATH: {"hold_down": 0.0, "flight_thrust": -100.0},
            st.PATH_DOME_ALLOY: {"2219-T851": 0.0, "2195": -40.0},
        }

    def term(self, path: str, value: Any) -> float:
        """The coefficient's own term [kg]."""
        item = self.ranges[path]
        if item.kind == st.KIND_DISCRETE:
            return self.discrete[path][value]
        f = _frac(item, value)
        w = self.weights[path]
        if path in (*st.PRESSURE_PATHS_STAGE1, *st.PRESSURE_PATHS_STAGE2):
            return w * (f - self.interior) ** 2
        if path == "load_entry.ring_h_over_b":
            return w * (f - 0.6) ** 2
        return self.signs[path] * w * f

    def stage2(self, case: st.SizingCase) -> bool:
        """Whether the synthetic upper stack is exceeded."""
        return case.dynamic == "step" or case.envelope_cap_g == min(st.ENVELOPE_CAP_ROWS_G)

    def __call__(self, values: Any, case: st.SizingCase) -> st.SizingSummary:
        """The synthetic SizingSummary of an assignment."""
        self.calls += 1
        dm1 = 1000.0 - 400.0 * case.margin
        dm2 = 0.0
        for path, value in values.items():
            item = self.ranges[path]
            if item.stage2_only:
                dm2 += self.term(path, value)
            elif item.kind != st.KIND_INTEGER:
                dm1 += self.term(path, value)
        dm1 += 10.0 * (8 - int(values[st.PATH_RING_PADS]))
        s2 = self.stage2(case)
        return st.SizingSummary(dm1, 100.0 + dm2 if s2 else 0.0, s2)


def _grid_best(item: st.CoefficientRange, fn: Separable, direction: str) -> Any:
    """The expected step-3 choice of an enumerated coefficient: its term's extreme over both
    ends and the interior scan point most extreme in the direction."""
    values = st.scan_values(item)
    terms = [fn.term(item.path, v) for v in values]
    pick = min if direction == st.LOW_MASS else max
    interior = pick(range(1, 4), key=lambda i: terms[i])
    candidates = (values[0], values[interior], values[-1])
    return pick(candidates, key=lambda v: fn.term(item.path, v))


def _expected_end(item: st.CoefficientRange, fn: Separable, direction: str) -> Any:
    """The expected choice of a coefficient in a separable synthetic search."""
    pick = min if direction == st.LOW_MASS else max
    if item.kind == st.KIND_DISCRETE:
        return pick(item.choices, key=lambda c: fn.term(item.path, c))
    enumerated = (*st.PRESSURE_PATHS_STAGE1, *st.PRESSURE_PATHS_STAGE2, "load_entry.ring_h_over_b")
    if item.path in enumerated:
        return _grid_best(item, fn, direction)
    return pick((item.low, item.high), key=lambda v: fn.term(item.path, v))


def test_coefficient_range_refuses_bad_ranges_and_choices() -> None:
    """A CoefficientRange refuses an unknown kind or group, a central outside its range, a
    discrete one without its central first or with a range, a ranged one with choices."""
    good = st.CoefficientRange(
        "a.b", st.KIND_CONTINUOUS, st.GROUP_PHYSICS, 1.0, 0.0, 2.0, (), False
    )
    assert good.central == 1.0
    bad = (
        ("a.b", "weird", st.GROUP_PHYSICS, 1.0, 0.0, 2.0, (), False),
        ("a.b", st.KIND_CONTINUOUS, "other", 1.0, 0.0, 2.0, (), False),
        ("a.b", st.KIND_CONTINUOUS, st.GROUP_PHYSICS, 3.0, 0.0, 2.0, (), False),
        ("a.b", st.KIND_CONTINUOUS, st.GROUP_PHYSICS, 1.0, 0.0, 2.0, (1.0,), False),
        ("a.b", st.KIND_DISCRETE, st.GROUP_PHYSICS, "x", None, None, ("y", "x"), False),
        ("a.b", st.KIND_DISCRETE, st.GROUP_PHYSICS, "x", 0.0, None, ("x", "y"), False),
        ("a.b", st.KIND_DISCRETE, st.GROUP_PHYSICS, "x", None, None, ("x", "x"), False),
    )
    for args in bad:
        with pytest.raises(ValueError):
            st.CoefficientRange(*args)


def test_search_paths_are_the_structure_files_coefficients(
    ranges: tuple[st.CoefficientRange, ...],
) -> None:
    """Every coefficient path the search names exists in the file's coefficient_ranges with
    the kind and group it is used as; the set names and case fields agree with config.py;
    the stage-2-only five are the stage-2 pressures and the interstage length."""
    by_path = {r.path: r for r in ranges}
    for path in (*st.JOINT_DISCRETE_PATHS, *st.END_DISCRETE_PATHS):
        assert by_path[path].kind == st.KIND_DISCRETE and by_path[path].group == st.GROUP_PHYSICS
    for path in (*st.PRESSURE_PATHS_STAGE1, *st.PRESSURE_PATHS_STAGE2, st.PATH_INTERSTAGE_LENGTH):
        assert by_path[path].kind == st.KIND_CONTINUOUS and by_path[path].group == st.GROUP_PHYSICS
    for path in (*st.LINEAR_AXIS_PATHS, *st.BRACKETED_AXIS_PATHS):
        assert by_path[path].kind == st.KIND_CONTINUOUS and by_path[path].group == st.GROUP_DESIGN
    assert by_path[st.PATH_RING_PADS].kind == st.KIND_INTEGER
    assert {r.path for r in ranges if r.stage2_only} == {
        *st.PRESSURE_PATHS_STAGE2,
        st.PATH_INTERSTAGE_LENGTH,
    }
    assert STRUCTURE_SET_NAMES == st.SEARCH_SET_NAMES
    assert st.SEARCH_LABEL == "the extremes found by the screened search over the stated ranges"
    assert "bound" not in st.SEARCH_LABEL


def test_classify_scan_end_and_grid_values() -> None:
    """classify_scan: flat within 1e-6 kg, monotone with ties either way, non-monotone
    otherwise; scan_values hits both ends exactly; Scan.end and grid_values by direction (three
    points: both ends and the most extreme interior point; two: the two most extreme)."""
    tol = st.MONOTONE_TOL_KG
    assert st.classify_scan([1.0, 1.0 + 0.5 * tol, 1.0]) == st.CLASS_FLAT
    assert st.classify_scan([1.0, 2.0, 2.0, 3.0]) == st.CLASS_MONOTONE
    assert st.classify_scan([3.0, 2.0, 2.0 + 0.5 * tol, 1.0]) == st.CLASS_MONOTONE
    assert st.classify_scan([1.0, 3.0, 2.0]) == st.CLASS_NON_MONOTONE
    item = st.CoefficientRange(
        "a.b", st.KIND_CONTINUOUS, st.GROUP_PHYSICS, 2.0, 1.24, 4.0, (), False
    )
    values = st.scan_values(item)
    assert len(values) == 5 and values[0] == 1.24 and values[-1] == 4.0
    scan = st.Scan("a.b", values, (5.0, 1.0, 3.0, 0.5, 9.0), st.CLASS_NON_MONOTONE)
    assert scan.end(st.LOW_MASS) == 1.24 and scan.end(st.HIGH_MASS) == 4.0
    assert scan.grid_values(st.LOW_MASS, 3) == (1.24, values[3], 4.0)
    assert scan.grid_values(st.HIGH_MASS, 3) == (1.24, values[2], 4.0)
    assert scan.grid_values(st.LOW_MASS, 2) == (values[1], values[3])
    assert scan.grid_values(st.HIGH_MASS, 2) == (1.24, 4.0)
    with pytest.raises(ValueError):
        scan.grid_values(st.LOW_MASS, 4)
    with pytest.raises(ValueError):
        scan.end("sideways")


def test_evaluator_memoizes_and_counts(ranges: tuple[st.CoefficientRange, ...]) -> None:
    """The evaluator sizes each distinct assignment and case once: a value given at its
    central is the assignment with none given; a new case is a new sizing; an unknown path
    is refused."""
    fn = Separable(ranges)
    ev = st.SearchEvaluator(fn, ranges)
    case = st.SizingCase()
    central = {r.path: r.central for r in ranges}
    a = ev.dm({}, case)
    assert ev.dm({"materials.E_GPa": central["materials.E_GPa"]}, case) == a
    assert ev.count == 1 and fn.calls == 1
    ev.dm({}, st.SizingCase(dynamic="step"))
    ev.dm({"materials.E_GPa": 72.0}, case)
    assert ev.count == 3 and fn.calls == 3
    with pytest.raises(KeyError):
        ev.dm({"materials.nope": 1.0}, case)


def test_band_search_finds_the_separable_extremes(ranges: tuple[st.CoefficientRange, ...]) -> None:
    """Search A on a separable synthetic sizing: every set value is its own term's extreme
    (a monotone coefficient at its end, the pressures and the non-monotone ring_h_over_b at
    their best grid point, each discrete one at its extreme choice), dm the sum of the
    extremes; the stage-2-only five are not varied (the upper stack is not exceeded); the
    tornado, scans and classification as the terms say; the polish moves nothing (each
    term is already at its grid's extreme, a pass confirms it); the one-coordinate check on
    9 points sees the ring's interior minimum at 0.6 of its range that the 5-point grid
    could not (the low end's excess w (0.1^2 - 0.025^2) at 7.875), and nothing beyond the
    high end; the counts as the plan of source note 9.3 (41 tornado, 54 new scan points, 2 x
    4 x 3^4 x 3 grid, 500 samples) plus the polish's bound, less the repeats the memo
    shares."""
    fn = Separable(ranges)
    ev = st.SearchEvaluator(fn, ranges)
    case = st.SizingCase()
    search = st.band_search(ev, {}, case, st.DIRECTIONS, samples=500, seed=11)
    varied = [r for r in ranges if r.group == st.GROUP_PHYSICS and not r.stage2_only]
    assert search.varied == tuple(r.path for r in varied)
    assert not search.stage2_sized
    assert len(search.tornado) == len(varied) and len(search.scans) == 18
    classes = dict(search.classification)
    assert classes["load_entry.ring_h_over_b"] == st.CLASS_NON_MONOTONE
    assert classes["materials.E_GPa"] == st.CLASS_MONOTONE
    assert classes[st.PATH_S_DG] == st.CLASS_DISCRETE
    central = {r.path: r.central for r in ranges}
    for direction in st.DIRECTIONS:
        found = search.set(direction)
        expected = dict(central)
        for item in varied:
            expected[item.path] = _expected_end(item, fn, direction)
            assert found.value(item.path) == expected[item.path], (direction, item.path)
        assert found.dm_kg == fn(expected, case).total_kg
        assert found.combos == 4 and found.grid_size == 4 * 3**5
        assert found.coordinate_swept == ()
        assert found.samples == 500 and found.excess_kg == 0.0
        assert found.polish.moves == () and found.polish.converged and found.polish.passes == 1
        assert found.polish.dm_before_kg == found.polish.dm_after_kg == found.dm_kg
        assert [c.check for c in found.checks] == [st.CHECK_SAMPLES, st.CHECK_ONE_COORDINATE]
        local = found.check(st.CHECK_ONE_COORDINATE)
        assert local.found_dm_kg == found.dm_kg and local.trials == 18 * 8 + 4
    ring = "load_entry.ring_h_over_b"
    low = search.set(st.LOW_MASS).check(st.CHECK_ONE_COORDINATE)
    assert low.path == ring and low.value == st.scan_values(fn.ranges[ring], 9)[5] == 7.875
    assert low.excess_kg == pytest.approx(fn.weights[ring] * (0.1**2 - 0.025**2), rel=1e-9)
    high = search.set(st.HIGH_MASS).check(st.CHECK_ONE_COORDINATE)
    assert high.excess_kg == 0.0 and high.extreme_dm_kg < search.set(st.HIGH_MASS).dm_kg
    assert search.evaluations == ev.count
    polish_bound = 2 * (st.POLISH_MAX_PASSES * (18 * 5 + 4) + 18 * 9 + 4)
    assert 41 + 54 + 500 < search.evaluations <= 41 + 54 + 2 * 4 * 3**5 + 500 + polish_bound


RHO_LOX = "geometry.rho_lox_kg_per_m3"
ETA_WELD = "materials.eta_weld"


class Interacting(Separable):
    """A separable sizing plus one interaction, -50 f_rho (1 - f_eta) [kg] (f the fraction of
    each range), with rho_lox's own term +10 f_rho and eta_weld's -100 f_eta: at the base
    (eta at its central 1.0, its high end) rho_lox raises dm, but at the high-mass end
    (eta at its low end) it lowers dm by 40 f_rho, the reversal review P1 found on the
    flown pad."""

    def __init__(self, ranges: tuple[st.CoefficientRange, ...]) -> None:
        super().__init__(ranges)
        self.weights[RHO_LOX], self.signs[RHO_LOX] = 10.0, 1.0
        self.weights[ETA_WELD], self.signs[ETA_WELD] = 100.0, -1.0

    def __call__(self, values: Any, case: st.SizingCase) -> st.SizingSummary:
        """The separable SizingSummary with the interaction on dm1."""
        base = super().__call__(values, case)
        f_rho = _frac(self.ranges[RHO_LOX], values[RHO_LOX])
        f_eta = _frac(self.ranges[ETA_WELD], values[ETA_WELD])
        return st.SizingSummary(
            base.dm_stage1_kg - 50.0 * f_rho * (1.0 - f_eta), base.dm_stage2_kg, base.stage2_sized
        )


def test_polish_rereads_a_direction_at_the_found_end(
    ranges: tuple[st.CoefficientRange, ...],
) -> None:
    """D-SP7-38: rho_lox scans increasing at the base, so step 3 puts the high-mass end at
    its dense end; there (eta_weld at its low end) its effect has reversed, and the polish
    moves it to its light end in its first pass (+40 kg), a second pass confirms nothing
    else moves; the move is recorded with the dm it adds, the end's dm rises by it, and the
    one-coordinate check then finds no excess beyond the high end. The low-mass end needs
    no move."""
    fn = Interacting(ranges)
    ev = st.SearchEvaluator(fn, ranges)
    search = st.band_search(ev, {}, st.SizingCase(), st.DIRECTIONS, samples=0, seed=1)
    assert classes_of(search)[RHO_LOX] == st.CLASS_MONOTONE
    item = fn.ranges[RHO_LOX]
    high = search.set(st.HIGH_MASS)
    assert high.value(ETA_WELD) == fn.ranges[ETA_WELD].low
    assert high.value(RHO_LOX) == item.low
    (move,) = high.polish.moves
    assert (move.path, move.from_value, move.to_value, move.pass_index) == (
        RHO_LOX,
        item.high,
        item.low,
        0,
    )
    assert move.dm_change_kg == pytest.approx(40.0, rel=1e-9)
    assert high.polish.passes == 2 and high.polish.converged
    assert high.polish.dm_after_kg - high.polish.dm_before_kg == pytest.approx(40.0, rel=1e-9)
    direct = fn(ev.assignment(high.as_dict()), st.SizingCase()).total_kg
    assert high.dm_kg == high.polish.dm_after_kg == pytest.approx(direct, rel=1e-12)
    assert high.check(st.CHECK_ONE_COORDINATE).excess_kg == 0.0
    low = search.set(st.LOW_MASS)
    assert low.polish.moves == () and low.value(RHO_LOX) == item.low


def _replay_samples(
    fn: Separable,
    ranges: tuple[st.CoefficientRange, ...],
    varied: list[st.CoefficientRange],
    case: st.SizingCase,
    count: int,
    seed: int,
) -> list[float]:
    """The extremality samples' dm, drawn independently in the documented order (numpy
    default_rng(seed); per sample each varied coefficient in turn: a discrete one by
    integers(len(choices)), a continuous one by uniform(low, high))."""
    rng = np.random.default_rng(seed)
    central = {r.path: r.central for r in ranges}
    out = []
    for _ in range(count):
        trial = dict(central)
        for item in varied:
            if item.kind == st.KIND_DISCRETE:
                trial[item.path] = item.choices[int(rng.integers(len(item.choices)))]
            else:
                trial[item.path] = float(rng.uniform(float(item.low), float(item.high)))
        out.append(fn(trial, case).total_kg)
    return out


def test_band_search_extremality_excess_against_a_replay(
    ranges: tuple[st.CoefficientRange, ...],
) -> None:
    """With every term flat but one stage-1 pressure whose minimum (at 0.37 of its range)
    lies between scan points, seeded samples land nearer that minimum than the grid: the
    recorded excess is the found end less the samples' minimum, replayed independently, and
    positive; the high end (the pressure's far end, exactly on the grid) has none."""
    fn = Separable(ranges, interior=0.37)
    target = st.PRESSURE_PATHS_STAGE1[0]
    fn.weights = {path: (100.0 if path == target else 0.0) for path in fn.weights}
    fn.discrete = {k: dict.fromkeys(v, 0.0) for k, v in fn.discrete.items()}
    ev = st.SearchEvaluator(fn, ranges)
    case = st.SizingCase()
    search = st.band_search(ev, {}, case, st.DIRECTIONS, samples=200, seed=5)
    varied = [r for r in ranges if r.group == st.GROUP_PHYSICS and not r.stage2_only]
    samples = _replay_samples(fn, ranges, varied, case, 200, 5)
    low, high = search.set(st.LOW_MASS), search.set(st.HIGH_MASS)
    assert low.extreme_sample_kg == min(samples)
    assert low.excess_kg == low.dm_kg - min(samples) > 0.0
    assert high.extreme_sample_kg == max(samples) and high.excess_kg == 0.0
    assert classes_of(search)[target] == st.CLASS_NON_MONOTONE


def classes_of(search: st.BandSearch) -> dict[str, str]:
    """A BandSearch's classification as a dict."""
    return dict(search.classification)


def test_band_search_coordinate_sweep_beyond_the_budget(
    ranges: tuple[st.CoefficientRange, ...],
) -> None:
    """When the extra non-monotone coefficients would take step 3 beyond STEP3_BUDGET, they
    are set by the coordinate sweep instead (two passes over their scan points): on a
    separable sizing each lands on its own term's best scan point."""
    fn = Separable(ranges)
    extras = [
        "materials.E_GPa",
        "materials.F_tu_MPa",
        "buckling.k_stiff",
        "geometry.ullage_fraction",
    ]
    original = fn.term

    def term(path: str, value: Any) -> float:
        if path in extras:
            return 20.0 * (_frac(fn.ranges[path], value) - 0.55) ** 2
        return original(path, value)

    fn.term = term  # type: ignore[method-assign]
    ev = st.SearchEvaluator(fn, ranges)
    search = st.band_search(ev, {}, st.SizingCase(), (st.LOW_MASS,), samples=0, seed=1)
    found = search.set(st.LOW_MASS)
    assert set(found.coordinate_swept) == {*extras, "load_entry.ring_h_over_b"}
    assert found.grid_size == 4 * 3**4
    for path in found.coordinate_swept:
        item = fn.ranges[path]
        best = min(st.scan_values(item), key=lambda v, p=path: fn.term(p, v))
        assert found.value(path) == best, path
    assert found.samples == 0 and found.excess_kg == 0.0 and found.extreme_sample_kg is None


def test_stage2_and_outer_searches(ranges: tuple[st.CoefficientRange, ...]) -> None:
    """Search B sets the interstage length at its end by its tornado and the four stage-2
    pressures at their best grid points with A's values, and refuses a case that does not
    size stage 2; search C takes the margin row that lowers (raises) dm, the design corners
    by construction (the high corner's rise time 1/(pi f_low), 4 pads, the 4.0 g0 cap), varies
    the stage-2-only five only at the corner that sizes stage 2 and fills the other corner's
    from the physics set; the outer sets record every coefficient and both case fields."""
    fn = Separable(ranges)
    ev = st.SearchEvaluator(fn, ranges)
    with pytest.raises(ValueError, match="sizes stage 2"):
        st.stage2_search(ev, {st.LOW_MASS: {}}, st.SizingCase(), samples_per_set=0, seeds={})
    a = st.band_search(ev, {}, st.SizingCase(), st.DIRECTIONS, samples=0, seed=1)
    a_sets = {d: a.set(d).as_dict() for d in st.DIRECTIONS}
    step = st.SizingCase(dynamic="step")
    b = st.stage2_search(
        ev, a_sets, step, samples_per_set=20, seeds={st.LOW_MASS: 2, st.HIGH_MASS: 3}
    )
    assert len(b.tornado) == 5 and len(b.scans) == 4
    for direction in st.DIRECTIONS:
        found = b.set(direction)
        for item in ranges:
            if item.stage2_only:
                assert found.value(item.path) == _expected_end(item, fn, direction), item.path
            elif item.group == st.GROUP_PHYSICS:
                assert found.value(item.path) == a_sets[direction][item.path]
        assert found.grid_size == 81 and found.samples == 20
        assert [c.check for c in found.checks] == [
            st.CHECK_SAMPLES,
            st.CHECK_ONE_COORDINATE,
            st.CHECK_ONE_COORDINATE_HELD,
        ]
        assert found.check(st.CHECK_ONE_COORDINATE).trials == 5 * 8
        assert found.check(st.CHECK_ONE_COORDINATE_HELD).trials == 18 * 8 + 4
        assert found.polish.converged
    physics = {}
    for direction in st.DIRECTIONS:
        merged = {**a_sets[direction], **b.set(direction).as_dict()}
        physics[direction] = {r.path: merged[r.path] for r in ranges if r.group == st.GROUP_PHYSICS}
    c = st.outer_search(
        ev, physics, st.SizingCase(), samples=10, seeds={st.LOW_MASS: 4, st.HIGH_MASS: 5}
    )
    assert c.margin_rows[0][0] == 0.0 and c.margin_low == 0.25 and c.margin_high == 0.0
    assert c.cap_low_g is None and c.cap_high_g == 4.0
    assert not c.low.stage2_sized and c.high.stage2_sized
    low, high = c.set_values(st.LOW_MASS), c.set_values(st.HIGH_MASS)
    every = {r.path for r in ranges} | {st.CASE_MARGIN, st.CASE_ENVELOPE_CAP}
    assert set(low) == every and set(high) == every
    assert high[st.PATH_RISE_TIME] == pytest.approx(1.0 / (math.pi * 2.0), rel=1e-15)
    assert high[st.PATH_RING_PADS] == 4 and low[st.PATH_RING_PADS] == 8
    assert low[st.PATH_RISE_TIME] == 1.0 and low[st.PATH_AXIAL_FREQUENCY] == 10.0
    assert low["nof.nof_barrel"] == 1.54 and high["nof.nof_dome"] == 2.36
    assert (low[st.CASE_MARGIN], low[st.CASE_ENVELOPE_CAP]) == (0.25, None)
    assert (high[st.CASE_MARGIN], high[st.CASE_ENVELOPE_CAP]) == (0.0, 4.0)
    for path in (*st.PRESSURE_PATHS_STAGE2, st.PATH_INTERSTAGE_LENGTH):
        assert low[path] == physics[st.LOW_MASS][path]
        assert high[path] == _expected_end(fn.ranges[path], fn, st.HIGH_MASS)
    assert c.evaluations > 0


def test_screened_search_sets_label_seeds_and_fallbacks(
    ranges: tuple[st.CoefficientRange, ...],
) -> None:
    """screened_search gives the four sets in the file's order under SEARCH_LABEL, the
    physics sets every physics coefficient (none at "whatever the search leaves", the five
    from B), the outer sets every coefficient with margin and cap; its count is the
    evaluator's; the same seed gives the same sets; fallbacks 1 and 2 put every grid on two
    points and halve the samples; an unknown fallback is refused."""
    fn = Separable(ranges)
    ev = st.SearchEvaluator(fn, ranges)
    head, step = st.SizingCase(), st.SizingCase(dynamic="step")
    full = st.screened_search(ev, headline=head, step=step)
    assert tuple(s.name for s in full.sets) == st.SEARCH_SET_NAMES
    assert full.label == st.SEARCH_LABEL and full.fallbacks == () and full.seed == st.SEARCH_SEED
    assert full.evaluations == ev.count
    physics_paths = {r.path for r in ranges if r.group == st.GROUP_PHYSICS}
    for name in STRUCTURE_PHYSICS_SETS:
        assert set(full.set(name).as_dict()) == physics_paths
        assert [(e[0], e[1].check) for e in full.set(name).extremality] == [
            ("A", st.CHECK_SAMPLES),
            ("A", st.CHECK_ONE_COORDINATE),
            ("B", st.CHECK_SAMPLES),
            ("B", st.CHECK_ONE_COORDINATE),
            ("B", st.CHECK_ONE_COORDINATE_HELD),
        ]
        assert [p[0] for p in full.set(name).polish] == ["A", "B"]
    for name in ("outer_low_mass", "outer_high_mass"):
        assert [(e[0], e[1].check) for e in full.set(name).extremality] == [
            ("C", st.CHECK_SAMPLES),
            ("C", st.CHECK_ONE_COORDINATE),
        ]
        assert [p[0] for p in full.set(name).polish] == ["C"]
    assert full.physics.samples == st.SAMPLES_PHYSICS
    again = st.screened_search(st.SearchEvaluator(fn, ranges), headline=head, step=step)
    assert again.sets == full.sets and again.evaluations == full.evaluations
    lean = st.screened_search(
        st.SearchEvaluator(fn, ranges), headline=head, step=step, fallbacks=st.SEARCH_FALLBACKS
    )
    assert lean.physics.samples == st.SAMPLES_PHYSICS // 2
    assert lean.physics.set(st.LOW_MASS).grid_size == 4 * 2**5
    assert lean.stage2.set(st.LOW_MASS).samples == st.SAMPLES_STAGE2_PER_SET // 2
    assert lean.evaluations < full.evaluations
    with pytest.raises(ValueError, match="unknown fallback"):
        st.screened_search(
            st.SearchEvaluator(fn, ranges), headline=head, step=step, fallbacks=("x",)
        )


def test_planned_sizings_and_the_fallback_choice(
    ranges: tuple[st.CoefficientRange, ...],
) -> None:
    """The note's budget (section 9.3), computed from the file's coefficients: 1,243 + 285 +
    1,689 + 46 = 3,263 sizings, 1,833 with fallback 1 and 1,283 with both; the polish of
    D-SP7-38 adds its bound, 2 x (4 x 94 + 166) for A, 2 x (4 x 25 + 45 + 166) for B and
    (4 x 94 + 166) + (4 x 119 + 211) for C, 2,935; the fallbacks are taken in order only while
    the whole estimate exceeds 600 s, and beyond both the budget goes to the user."""
    assert st.note_planned_sizings(ranges) == 1243 + 285 + 1689 + 46 == 3263
    assert st.note_planned_sizings(ranges, st.SEARCH_FALLBACKS[:1]) == 1833
    assert st.note_planned_sizings(ranges, st.SEARCH_FALLBACKS) == 1283
    polish = 2 * (4 * 94 + 166) + 2 * (4 * 25 + 45 + 166) + (4 * 94 + 166) + (4 * 119 + 211)
    assert st.polish_planned_sizings(ranges) == polish == 2935
    assert st.planned_sizings(ranges) == 3263 + 2935
    assert st.planned_sizings(ranges, st.SEARCH_FALLBACKS) == 1283 + 2935
    assert st.choose_fallbacks(0.03, ranges) == ()
    assert st.choose_fallbacks(600.0 / 6198, ranges) == ()
    assert st.choose_fallbacks(600.0 / 5000, ranges) == st.SEARCH_FALLBACKS[:1]
    assert st.choose_fallbacks(600.0 / 4300, ranges) == st.SEARCH_FALLBACKS
    with pytest.raises(st.SearchBudgetExceeded):
        st.choose_fallbacks(600.0 / 4000, ranges)
    with pytest.raises(ValueError):
        st.note_planned_sizings(ranges, ("fallback_9",))


def test_penalty_curve_against_sp1_rows() -> None:
    """SP1's curve is the recorded rows (dm 0, 2, 4, 8.1 t to x* 41,262.908 ... 1,980.477 kg):
    exact at its points, linear between them, extrapolated beyond 8.1 t along the last
    segment (the zero crossing at 8,100 + 1,980.477/5.0965 kg), inverted by dm_at; an offload
    above the uncharged one and a curve out of order are refused; the stage-2 weight is
    24/4.381."""
    curve = st.SP1_PENALTY_CURVE
    assert curve.dm_kg == SP1_PENALTY_DRY_MASS_KG and curve.x_kg == SP1_PENALTY_OFFLOAD_KG
    for dm, x in zip(curve.dm_kg, curve.x_kg, strict=True):
        assert curve.x_at(dm) == x and curve.dm_at(x) == dm
    assert curve.x_at(1000.0) == pytest.approx((41262.90803733282 + 32285.203295407457) / 2)
    slope = (1980.4767886165673 - 22875.96053288855) / 4100.0
    assert curve.x_at(9000.0) == pytest.approx(1980.4767886165673 + slope * 900.0, rel=1e-14)
    zero = curve.dm_at(0.0)
    assert zero == pytest.approx(8100.0 - 1980.4767886165673 / slope, rel=1e-14)
    assert curve.extrapolated(zero) and not curve.extrapolated(8100.0)
    half = curve.dm_at(0.5 * SP1_HEADLINE_OFFLOAD_KG)
    assert curve.x_at(half) == pytest.approx(0.5 * SP1_HEADLINE_OFFLOAD_KG, rel=1e-14)
    with pytest.raises(ValueError):
        curve.dm_at(41262.91)
    with pytest.raises(ValueError):
        st.PenaltyCurve((0.0, 1.0), (1.0, 2.0), "rising")
    with pytest.raises(ValueError):
        st.PenaltyCurve((1.0, 2.0), (2.0, 1.0), "not from 0")
    assert st.STAGE2_DM_WEIGHT == OFFLOAD_PER_KG_STAGE2_DRY / OFFLOAD_PER_KG_STAGE1_DRY


def test_sp1_record_pins_the_placement_inputs() -> None:
    """tests/data/silo_offload_2d_record.json (D-SP7-30, copied once from the two runs'
    untracked metrics.json) carries its provenance and pins every recorded SP1 value the
    structural model uses: constants.py's penalty rows equal its gate rows exactly (the
    headline their first, the curve's uncharged offload), structure_support's P_ref, the
    fork's P_ref and bridge are its values; the gate's P_ref is the screening record's pad
    P* under the same search budget; the tracked findings note RQ1 names each run directory
    with its git hash (clean) and quotes the headline and the rows to its printed digits."""
    rec = ss.sp1_record()
    gate, fork = rec["gate"], rec["readme_loads"]
    rows = gate["stage1_offload_cases"]
    assert [r["case"] for r in rows] == [
        "silo_cold_s1",
        "silo_cold_s1_dry+2t",
        "silo_cold_s1_dry+4t",
        "silo_cold_s1_dry+8.1t",
    ]
    assert tuple(r["stage1_dry_mass_added_kg"] for r in rows) == SP1_PENALTY_DRY_MASS_KG
    assert tuple(r["offload_kg"] for r in rows) == SP1_PENALTY_OFFLOAD_KG
    assert ss.HEADLINE_OFFLOAD_KG == SP1_PENALTY_OFFLOAD_KG[0] == st.SP1_PENALTY_CURVE.uncharged_kg
    assert ss.P_REF_KG == gate["reference_payload_kg"]
    assert [r["case"] for r in fork["stage1_offload_cases"]] == ["silo_cold_s1"]
    assert ss.README_P_REF_KG == fork["reference_payload_kg"]
    assert ss.README_BRIDGE_OFFLOAD_KG == fork["stage1_offload_cases"][0]["offload_kg"]
    screening_path = ss.REPO / "tests" / "data" / "silo_screening_2d_record.json"
    screening = json.loads(screening_path.read_text(encoding="utf-8"))
    assert gate["reference_payload_kg"] == screening["payload_kg"]["pad"]
    assert gate["search_budget_id"] == fork["search_budget_id"] == screening["search_budget_id"]
    finding_path = ss.REPO / "docs" / "findings" / "RQ1-fuel-offload-2d.md"
    finding = finding_path.read_text(encoding="utf-8")
    flat = " ".join(finding.split())
    for block in (gate, fork):
        assert block["git_dirty"] is False and block["reference"] == "pad"
        assert Path(block["run_dir"]).name == block["timestamp_utc"]
        row = f"| `run {block['experiment']}` | {block['run_dir']} | {block['git']}, clean |"
        assert row in finding, row
    t = [r["offload_kg"] / 1000.0 for r in rows]
    assert f"leave {t[1]:.2f}, {t[2]:.2f} and {t[3]:.2f} t" in flat
    assert f"({rows[0]['offload_kg']:,.3f} kg;" in flat


def _linear_summary(d0: float, k: float, d2: float = 0.0) -> Any:
    """x -> a SizingSummary with dm1 = d0 + k (x_h - x) (heavier stacks need more), dm2 d2."""

    def at(x: float) -> st.SizingSummary:
        return st.SizingSummary(d0 + k * (SP1_HEADLINE_OFFLOAD_KG - x), d2, d2 > 0.0)

    return at


def test_coupled_placement_fixed_point() -> None:
    """The coupled placement is the fixed point x = X(dm(x)): on a linear dm(x) inside one
    segment of the curve it equals the closed form; a dm beyond the curve's zero gives no
    offload (x 0, extrapolated); the stage-2 increment counts at its weight and the
    plausibility scale multiplies the placed dm."""
    curve = st.SP1_PENALTY_CURVE
    k = 0.012
    p = st.coupled_placement(_linear_summary(5868.0, k), curve, stage2_weight=0.0)
    # on the 4,000-8,100 kg segment X(dm) = x2 + s (dm - 4000)
    x2, s = 22875.96053288855, (1980.4767886165673 - 22875.96053288855) / 4100.0
    closed = (x2 + s * (5868.0 + k * SP1_HEADLINE_OFFLOAD_KG - 4000.0)) / (1.0 + s * k)
    assert p.converged and not p.no_offload and not p.extrapolated
    assert p.x_kg == pytest.approx(closed, abs=2e-3)
    assert p.fraction == pytest.approx(closed / SP1_HEADLINE_OFFLOAD_KG, abs=1e-7)
    none = st.coupled_placement(_linear_summary(9000.0, k), curve, stage2_weight=0.0)
    assert none.no_offload and none.x_kg == 0.0 and none.extrapolated and none.converged
    w = st.coupled_placement(_linear_summary(4000.0, 0.0, 100.0), curve, stage2_weight=2.0)
    assert w.dm_kg == 4200.0 and w.x_kg == pytest.approx(curve.x_at(4200.0), abs=1e-9)
    scaled = st.coupled_placement(
        _linear_summary(4000.0, 0.0), curve, stage2_weight=0.0, dm_scale=0.5
    )
    assert scaled.dm_kg == 2000.0 and scaled.x_kg == curve.x_at(2000.0)


class LinearAxes:
    """A synthetic sizing linear in the four factors and k_ts (through the thrust-structure
    entry only), falling in the rise time and frequency and in the pad count, rising as the
    offload falls."""

    def __init__(self, ranges: tuple[st.CoefficientRange, ...]) -> None:
        self.central = {r.path: r.central for r in ranges}

    def dm(self, v: Any, case: st.SizingCase) -> float:
        """The synthetic dm [kg]."""
        x = SP1_HEADLINE_OFFLOAD_KG if case.offload_kg is None else case.offload_kg
        base = 2000.0 + 0.01 * (SP1_HEADLINE_OFFLOAD_KG - x)
        base += 1500.0 * float(v["nof.nof_barrel"]) + 800.0 * float(v["nof.nof_dome"])
        base += 1200.0 * float(v["nof.nof_stiffened"]) + 600.0 * float(v["nof.nof_entry_ratio"])
        base += 900.0 / float(v[st.PATH_RISE_TIME]) + 4000.0 / float(v[st.PATH_AXIAL_FREQUENCY])
        base += 300.0 * (8 - int(v[st.PATH_RING_PADS]))
        if case.entry == st.ENTRY_THRUST_STRUCTURE:
            base += 9000.0 * float(v[st.PATH_K_TS])
        return base

    def __call__(self, values: Any, case: st.SizingCase) -> st.SizingSummary:
        """The synthetic SizingSummary."""
        return st.SizingSummary(self.dm(values, case), 0.0, False)


def test_break_even_closed_form_bracketed_and_integer(
    ranges: tuple[st.CoefficientRange, ...],
) -> None:
    """Search D on a synthetic sizing: each linear axis's root equals the closed form at
    the target offload (outside the range reported with its status); the rise time's root
    is brentq's to its tolerance; the pad count's bracket is the adjacent pair whose dm
    straddles the target; a level x* never reaches is not reached."""
    fn = LinearAxes(ranges)
    ev = st.SearchEvaluator(fn, ranges)
    curve = st.SP1_PENALTY_CURVE
    rows = st.break_even_search(ev, curve, case=st.SizingCase(), stage2_weight=1.0)
    assert len(rows) == 2 * 8
    by = {(r.path, r.level): r for r in rows}
    central = dict(fn.central)
    for level in st.BREAK_EVEN_LEVELS:
        x_t = level * SP1_HEADLINE_OFFLOAD_KG
        dm_t = curve.dm_at(x_t)
        case = st.SizingCase(offload_kg=x_t)
        for path, slope in (("nof.nof_barrel", 1500.0), ("nof.nof_dome", 800.0)):
            row = by[(path, level)]
            rest = fn.dm({**central, path: 0.0}, case)
            root = (dm_t - rest) / slope
            assert row.method == "linear" and row.dm_target_kg == dm_t
            if root < st.NOF_MIN:
                assert row.value is None and row.status == st.BE_BELOW_THROUGHOUT
                continue
            assert row.value == pytest.approx(root, rel=1e-12)
            item = next(r for r in ranges if r.path == path)
            inside = item.low <= row.value <= item.high
            assert row.status == (st.BE_IN_RANGE if inside else st.BE_OUTSIDE_RANGE)
        kts = by[(st.PATH_K_TS, level)]
        assert kts.entry == st.ENTRY_THRUST_STRUCTURE
        rest = fn.dm(
            {**central, st.PATH_K_TS: 0.0},
            st.SizingCase(offload_kg=x_t, entry=st.ENTRY_THRUST_STRUCTURE),
        )
        root = (dm_t - rest) / 9000.0
        if root < st.LINEAR_AXIS_FLOORS[st.PATH_K_TS]:
            assert kts.value is None and kts.status == st.BE_BELOW_THROUGHOUT
        else:
            assert kts.value == pytest.approx(root, rel=1e-12)
        rise = by[(st.PATH_RISE_TIME, level)]
        if rise.status == st.BE_IN_RANGE:
            rest = fn.dm({**central, st.PATH_RISE_TIME: 1e300}, case)
            assert rise.value == pytest.approx(900.0 / (dm_t - rest), abs=1e-5)
        pads = by[(st.PATH_RING_PADS, level)]
        assert pads.method == "integer" and pads.value is None
        gaps = {n: fn.dm({**central, st.PATH_RING_PADS: n}, case) - dm_t for n in range(3, 9)}
        if pads.status == st.BE_IN_RANGE:
            lo, hi = pads.bracket
            assert hi == lo + 1 and gaps[lo] >= 0.0 > gaps[hi]
        elif pads.status == st.BE_ABOVE_THROUGHOUT:
            assert all(g < 0.0 for g in gaps.values())
        else:
            assert all(g >= 0.0 for g in gaps.values())
    assert all(r.status in st.BREAK_EVEN_STATUSES for r in rows)
    assert by[(st.PATH_RING_PADS, 0.0)].target_extrapolated


def test_break_even_linear_root_below_the_physical_floor(
    ranges: tuple[st.CoefficientRange, ...],
) -> None:
    """A linear axis's root below its physical floor (NOF_MIN for a factor, 0 for k_ts) is
    not reached at any admissible value: value None and the side the range's dm lies on
    (below the level for a rising axis, above it for a falling one); a root between the
    floor and the range's low end stays outside_range with its value."""
    fn = LinearAxes(ranges)
    central = dict(fn.central)
    x_t = 0.5 * SP1_HEADLINE_OFFLOAD_KG
    dm_t = st.SP1_PENALTY_CURVE.dm_at(x_t)
    at = st.SizingCase(offload_kg=x_t)
    shift = dm_t - fn.dm({**central, "nof.nof_barrel": 0.5}, at)

    def shifted(values: Any, case: st.SizingCase) -> st.SizingSummary:
        return st.SizingSummary(fn.dm(values, case) + shift, 0.0, False)

    rows = st.break_even_search(
        st.SearchEvaluator(shifted, ranges),
        st.SP1_PENALTY_CURVE,
        case=st.SizingCase(),
        stage2_weight=0.0,
        levels=(0.5,),
    )
    by = {r.path: r for r in rows}
    for path in (*st.NOF_PATHS, st.PATH_K_TS):
        row = by[path]
        assert row.value is None and row.status == st.BE_BELOW_THROUGHOUT, path
        assert min(row.dm_at_ends_kg) > dm_t
    ts = st.SizingCase(offload_kg=x_t, entry=st.ENTRY_THRUST_STRUCTURE)
    shift_ts = dm_t - fn.dm({**central, st.PATH_K_TS: 0.1}, ts)

    def shifted_ts(values: Any, case: st.SizingCase) -> st.SizingSummary:
        return st.SizingSummary(fn.dm(values, case) + shift_ts, 0.0, False)

    rows = st.break_even_search(
        st.SearchEvaluator(shifted_ts, ranges),
        st.SP1_PENALTY_CURVE,
        case=st.SizingCase(),
        stage2_weight=0.0,
        levels=(0.5,),
    )
    kts = next(r for r in rows if r.path == st.PATH_K_TS)
    assert 0.0 < 0.1 < float(next(r for r in ranges if r.path == st.PATH_K_TS).low)
    assert kts.status == st.BE_OUTSIDE_RANGE and kts.value == pytest.approx(0.1, rel=1e-9)

    def falling(values: Any, case: st.SizingCase) -> st.SizingSummary:
        dm = 6000.0 - 500.0 * float(values["nof.nof_dome"])
        return st.SizingSummary(dm - (6000.0 - 500.0 * 0.5 - dm_t), 0.0, False)

    rows = st.break_even_search(
        st.SearchEvaluator(falling, ranges),
        st.SP1_PENALTY_CURVE,
        case=st.SizingCase(),
        stage2_weight=0.0,
        levels=(0.5,),
    )
    dome = next(r for r in rows if r.path == "nof.nof_dome")
    assert dome.value is None and dome.status == st.BE_ABOVE_THROUGHOUT
    assert max(dome.dm_at_ends_kg) < dm_t
    assert set(st.LINEAR_AXIS_FLOORS) == set(st.LINEAR_AXIS_PATHS)
    assert st.LINEAR_AXIS_FLOORS[st.PATH_K_TS] == 0.0
    assert all(st.LINEAR_AXIS_FLOORS[p] == st.NOF_MIN for p in st.NOF_PATHS)


def test_break_even_integer_bracket_on_a_shifted_sizing(
    ranges: tuple[st.CoefficientRange, ...],
) -> None:
    """The pad count's bracket on a sizing tuned so the 50% target falls between 5 and 6
    pads: (5, 6), found from 3, 4, 6 and 8 and the one count between 4 and 6."""
    fn = LinearAxes(ranges)
    central = dict(fn.central)
    x_t = 0.5 * SP1_HEADLINE_OFFLOAD_KG
    dm_t = st.SP1_PENALTY_CURVE.dm_at(x_t)
    shift = dm_t - fn.dm({**central, st.PATH_RING_PADS: 5}, st.SizingCase(offload_kg=x_t)) + 150.0

    def shifted(values: Any, case: st.SizingCase) -> st.SizingSummary:
        return st.SizingSummary(fn.dm(values, case) + shift, 0.0, False)

    ev = st.SearchEvaluator(shifted, ranges)
    rows = st.break_even_search(
        ev, st.SP1_PENALTY_CURVE, case=st.SizingCase(), stage2_weight=0.0, levels=(0.5,)
    )
    pads = next(r for r in rows if r.path == st.PATH_RING_PADS)
    assert pads.status == st.BE_IN_RANGE and pads.bracket == (5, 6)
    assert pads.evaluations == 5


def test_structure_sizing_on_the_synthetic_pad() -> None:
    """sim.structure_sizing is structure.size on the analytic push of the vehicle offloaded
    by the case's x (the headline's by default), with the file's coefficients by path: equal
    to a direct call; a pad count below the file's range only with check_ranges False;
    sim.time_structure_sizing (the call behind the files' recorded timing) returns two
    positive medians, the step row's (stage 2 sized) the slower."""
    cfg = ss.structure_config()
    veh = ss.vehicle()
    pad = st.pad_load_set(
        sim.structure_pad_cases(ss.synthetic_pad_result(veh, dt_s=2.0), veh, cfg.stack_layout())
    )
    resolved = cli.load_experiment(ss.REPO / "experiments" / "silo_offload_2d.yaml")
    run = resolved.runs["silo_cold"].run
    sizing = sim.structure_sizing(cfg, veh, pad, run, headline_offload_kg=ss.HEADLINE_OFFLOAD_KG)
    masses, layout = sim.stack_masses(veh), cfg.stack_layout()
    for x in (None, 0.0, 20_000.0):
        offload = ss.HEADLINE_OFFLOAD_KG if x is None else x
        push = ss.headline_push(veh, layout, offload_kg=offload)
        direct = st.size(masses, layout, cfg.coefficients(), pad, push)
        got = sizing({}, st.SizingCase(offload_kg=x))
        assert got.dm_stage1_kg == direct.dm_stage1_kg and got.dm_stage2_kg == direct.dm_stage2_kg
    with pytest.raises(ValueError):
        sizing({st.PATH_RING_PADS: 3}, st.SizingCase())
    three = sizing({st.PATH_RING_PADS: 3}, st.SizingCase(check_ranges=False))
    assert three.ring_kg > sizing({}, st.SizingCase()).ring_kg
    inputs = sim.StructureSearchInputs(
        experiment="synthetic",
        variant="silo_cold",
        pad=None,  # type: ignore[arg-type]
        payload_kg=ss.P_REF_KG,
        vehicle=veh,
        pad_cases=pad,
        headline_offload_kg=ss.HEADLINE_OFFLOAD_KG,
        push_run=run,
        sizing=sizing,
        ranges=cfg.coefficient_ranges(),
        pad_seconds=0.0,
    )
    head, step = sim.time_structure_sizing(inputs, repeats=3)
    assert 0.0 < head < step
    assert sizing({}, sim.STRUCTURE_STEP_CASE).stage2_sized


def _synthetic_inputs(ranges: tuple[st.CoefficientRange, ...]) -> sim.StructureSearchInputs:
    """StructureSearchInputs around the Separable sizing (no pad flown)."""
    veh = ss.vehicle()
    return sim.StructureSearchInputs(
        experiment="synthetic",
        variant="silo_cold",
        pad=None,  # type: ignore[arg-type]
        payload_kg=ss.P_REF_KG,
        vehicle=veh,
        pad_cases=None,  # type: ignore[arg-type]
        headline_offload_kg=ss.HEADLINE_OFFLOAD_KG,
        push_run=None,  # type: ignore[arg-type]
        sizing=Separable(ranges),  # type: ignore[arg-type]
        ranges=ranges,
        pad_seconds=0.0,
    )


def test_sets_record_validates_as_the_files_sets_block(
    ranges: tuple[st.CoefficientRange, ...],
) -> None:
    """sim.structure_sets_record gives a block the structure file accepts (label, source,
    method, count, fallbacks, seed, commit, test and the four sets with their implied stack
    lengths); config refuses a wrong label, an unknown fallback, a physics set with a design
    axis or missing a physics coefficient, an outer set without its case fields, a
    negative margin and a cap at or below 1 g0."""
    inputs = _synthetic_inputs(ranges)
    cfg = ss.structure_config()
    search, _ = sim.structure_screened_search(inputs)
    record = sim.structure_sets_record(inputs, cfg, search, parent_commit="abc1234", test="t::x")
    data = ss.load_yaml(ss.GATE_STRUCTURE)
    data["sets"] = copy.deepcopy(record)
    config = StructureConfig.model_validate(data)
    assert config.sets is not None and config.sets.label == st.SEARCH_LABEL
    assert config.sets.evaluation_count == search.evaluations
    for name in STRUCTURE_SET_NAMES:
        geometry = st.build_geometry(
            sim.stack_masses(inputs.vehicle), cfg.stack_layout(), config.coefficients(name)
        )
        length = st.implied_stack_length_m(geometry, 13.2)
        assert getattr(config.sets, name).implied_stack_length_m == length
    assert config.set_case_fields("outer_high_mass") == {"margin": 0.0, "envelope_cap_g": 4.0}
    low = config.sets.physics_low_mass
    assert [(e.search, e.check) for e in low.extremality] == [
        ("A", st.CHECK_SAMPLES),
        ("A", st.CHECK_ONE_COORDINATE),
        ("B", st.CHECK_SAMPLES),
        ("B", st.CHECK_ONE_COORDINATE),
        ("B", st.CHECK_ONE_COORDINATE_HELD),
    ]
    assert [p.search for p in low.polish] == ["A", "B"]
    breaks: list[tuple[str, Any]] = [
        ("label", "the bounds found by the search"),
        ("fallbacks", ["fallback_7"]),
    ]
    for key, value in breaks:
        bad = copy.deepcopy(data)
        bad["sets"][key] = value
        with pytest.raises(ValueError):
            StructureConfig.model_validate(bad)
    edits = (
        ("physics_low_mass", "nof.nof_barrel", 1.8),
        ("physics_low_mass", "materials.E_GPa", None),
        ("outer_low_mass", "margin", None),
        ("outer_low_mass", "margin", -0.1),
        ("outer_high_mass", "envelope_cap_g", 1.0),
    )
    for set_name, key, value in edits:
        bad = copy.deepcopy(data)
        values = bad["sets"][set_name]["values"]
        if value is None:
            del values[key]
        else:
            values[key] = value
        with pytest.raises(ValueError):
            StructureConfig.model_validate(bad)
    checks = (
        ("check", "eyeballed"),
        ("excess_kg", -1.0),
        ("extreme_dm_kg", None),
    )
    for key, value in checks:
        bad = copy.deepcopy(data)
        bad["sets"]["physics_high_mass"]["extremality"][1][key] = value
        with pytest.raises(ValueError):
            StructureConfig.model_validate(bad)
    no_polish = copy.deepcopy(data)
    del no_polish["sets"]["outer_low_mass"]["polish"]
    with pytest.raises(ValueError):
        StructureConfig.model_validate(no_polish)


@pytest.mark.parametrize("entry", SEARCH_FILES, ids=lambda e: e[0].stem)
def test_structure_files_carry_the_frozen_sets(entry: tuple[Path, Path, float, float]) -> None:
    """Both files carry the four frozen sets under SEARCH_LABEL, searched on 4494fe1 with no
    fallback, reproduced by the slow test named in the file: every set converts, the physics
    sets hold every physics coefficient and the outer ones every coefficient with their case
    fields (the high corner's 4.0 g0 cap), every extremality excess is >= 0, and the method
    names the headline offload and P_ref; each set records its searches' polish (converged;
    its moves add up to its dm change) and its checks (the samples and the one-coordinate
    checks, D-SP7-38), every check of a search against the polished end's dm."""
    path, _, offload, p_ref = entry
    config = cli.load_structure(path)
    sets = config.sets
    assert sets is not None
    assert sets.label == st.SEARCH_LABEL and sets.parent_commit == PARENT_COMMIT
    assert sets.fallbacks == [] and sets.seed == st.SEARCH_SEED
    assert sets.test == f"tests/test_structure_search.py::test_frozen_sets_reproduce[{path.stem}]"
    assert repr(offload) in sets.method and repr(p_ref) in sets.method
    ranges = config.coefficient_ranges()
    assert sets.evaluation_count > st.note_planned_sizings(ranges) - st.BREAK_EVEN_PLANNED_SIZINGS
    for name in STRUCTURE_SET_NAMES:
        frozen = getattr(sets, name)
        config.coefficients(name)
        assert all(e.excess_kg >= 0.0 for e in frozen.extremality)
        assert frozen.implied_stack_length_m > 0.0
        searches = [p.search for p in frozen.polish]
        assert searches == (["A", "B"] if name in STRUCTURE_PHYSICS_SETS else ["C"])
        for polish in frozen.polish:
            assert polish.converged and 1 <= polish.passes <= st.POLISH_MAX_PASSES
            moved = sum(m.dm_change_kg for m in polish.moves)
            assert moved == pytest.approx(polish.dm_after_kg - polish.dm_before_kg, abs=1e-6)
            for check in frozen.extremality:
                if check.search == polish.search:
                    assert check.found_dm_kg == polish.dm_after_kg
                    assert check.trials > 0 and check.extreme_dm_kg is not None
    assert config.set_case_fields("outer_high_mass")["envelope_cap_g"] == 4.0
    assert config.set_case_fields("physics_low_mass") == {}


def _approx_tree(node: Any) -> Any:
    """A dumped tree with every float as pytest.approx(rel=1e-9) (the sizing-only dm and
    stack lengths may differ in their last bits across platforms; the set values, which
    are grid points, are compared exactly by the caller)."""
    if isinstance(node, dict):
        return {k: _approx_tree(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_approx_tree(v) for v in node]
    if isinstance(node, float):
        return pytest.approx(node, rel=1e-9, abs=1e-9)
    return node


@pytest.mark.slow
@pytest.mark.parametrize("entry", SEARCH_FILES, ids=lambda e: e[0].stem)
def test_frozen_sets_reproduce(
    entry: tuple[Path, Path, float, float], request: pytest.FixtureRequest
) -> None:
    """The frozen sets reproduce from scratch (design 4.2.6; S2's gate): the committed
    experiment's pad baseline flown afresh (its P* SP1's P_ref within 0.002 kg), searches A
    to C re-run at the headline push with the file's fallbacks, and the file's sets block
    (every value exactly; the searches, the polish records, the extremality checks, the
    implied stack lengths, the count, the method, the label and the seed, their floats to
    1e-9) equal to the recomputed one; under 10 minutes, the wall time recorded."""
    path, experiment, offload, p_ref = entry
    t0 = time.perf_counter()
    config = cli.load_structure(path)
    assert config.sets is not None
    inputs = sim.structure_search_inputs(
        cli.load_experiment(experiment), config, offload_kg=offload, reference_payload_kg=p_ref
    )
    search, _ = sim.structure_screened_search(inputs, fallbacks=config.sets.fallbacks)
    record = sim.structure_sets_record(
        inputs,
        config,
        search,
        parent_commit=config.sets.parent_commit,
        test=config.sets.test,
    )
    fresh = StructureSetsConfig.model_validate(record)
    got = fresh.model_dump(exclude={"note"})
    want = config.sets.model_dump(exclude={"note"})
    for name in STRUCTURE_SET_NAMES:
        assert got[name]["values"] == want[name]["values"], name
    assert got == _approx_tree(want)
    wall = time.perf_counter() - t0
    request.node.user_properties.append(("wall_s", wall))
    request.node.user_properties.append(("pad_s", inputs.pad_seconds))
    request.node.user_properties.append(("evaluations", search.evaluations))
    assert wall < st.SEARCH_WALL_TIME_S
