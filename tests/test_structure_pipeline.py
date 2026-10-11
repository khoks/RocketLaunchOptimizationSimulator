"""The coupling of the structural model to the offload solve (SP7 step S3; docs/physics.md,
"Coupling the structure to the offload solve"; design 4.3 and 4.4, D-SP7-20 to D-SP7-22,
D-SP7-30, D-SP7-31, D-SP7-35).

No test here solves a pre-registered SP7 structural case (D-SP7-31): the structural model
runs on tests/data/structure_synthetic.yaml, a synthetic structure file (the gate file's
sections with fewer stations, central values moved inside their ranges and synthetic
sets; its numbers are not findings), and the slow pins solve SP1's own experiment
(experiments/silo_offload_2d.yaml) with the structure off or with a constant 2,000 kg
injected in place of the sizing. Nothing reads results/: SP1's values come from
tests/data/silo_offload_2d_record.json.

Fast:

- the transform on ``OffloadProblem``: None is SP1's ``with_offload`` exactly; a
  transform is applied once in ``vehicle_at`` (the recorded run, the result and the
  verification see the same vehicle); ``with_stage_dry_mass`` and ``charge_structure``;
- the structural transform on the synthetic file and a synthetic pad flight (structure
  support): dm'(x) > -1/(2 E) with E = constants.OFFLOAD_PER_KG_STAGE1_DRY and the
  differences at 1 kg and 10 g agreeing (the half-bound is asserted on the synthetic file
  only); the gate file's four frozen sets, sizing only on the same synthetic pad (no
  solve, D-SP7-31), against the hard bound -1/E, converging inside the cap with margin,
  the outer high-mass corner measured below the half-bound; ``vehicle_at`` bit-identical
  across call orders, repeats and a rebuilt transform; the inner iteration's steps, its
  tolerance, cap and flag (the measured contraction recorded in the flag); full_load
  constant in x; the DLF of the record against min(2, 1 + T/(pi t_r)); every record key
  in order and only on a structural run; every fired structure flag promoted to the
  run's and the case record's ``flags`` (informational, D-SP7-19); a case's overrides
  recorded and named in the provenance, the restated dry mass's source and the
  assumption line (D-SP7-43), which also name the case's sizing, dynamic, entry, margin
  and cap; a drive other than constant_accel refused naming step S4b, a start without a
  push refused;
- the configuration: the case field and the experiment block resolve (an outer set's own
  margin and cap, the provenance text, the sweep points inheriting the field, the payload
  cases); every refusal; the structure file read with its sha256 and its content without
  YAML anchors; the cli lookup next to the experiment, then at the repository root, the
  recorded path repository-relative whenever the file lies under the repository;
- the dicts SP1 resolves and solves (every offload start of both offload experiments,
  the four solved rows' dicts, the penalty row's dry mass) equal their digests captured
  at the start commit 15b4e6e; a structural solved run restates dm by stage with the
  structure's provenance, never ``assumed``;
- the pass on fake runs (the sim seams monkeypatched): a structural and an unstructured
  case of one variant never share a solve (nor the verification run), the record keys
  and the assumption line only on the structural run, whose offload line is the
  structural variant (no line says every dry mass is unchanged; the summary block and
  the console lines still render), the verification flying dm, the arms sized on the
  envelope of their own perturbed pad (their keys in memory only until S3b),
  resolved_config.yaml's ``structure`` key only when a structure was used; and a written
  fixed-guidance planar run with no structure block carries no structure key anywhere.

Slow (SP1's experiment, the shipped budget; about five minutes: 309 s measured, the two
flights 49 s, pass 1 157 s, pass 2 104 s): the pad and silo_cold
flown once; the structure-off headline silo_cold_s1 through ``planar_offload`` equal to
SP1's record within 0.002 kg (x* and its verification's P*); the constant-2 t
cross-check (the transform's sizing replaced by 2,000.0 kg on stage 1) equal to SP1's
silo_cold_s1_dry+2t row within 0.002 kg (x* and the verification's P*); a structural
case on the synthetic file solved beside them with ``xv_dry_mass_delta_kg`` = dm1 + dm2
within 1e-6 kg.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import importlib.util
import json
import math
import sys
import time
import typing
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pandas as pd
import pytest
import yaml

from launchsim import cli, config, offload, results_io, sim, structure, summary
from launchsim.assist.constant_accel import ConstantAccelAssist
from launchsim.config import (
    StructureCaseConfig,
    offload_overrides,
    offload_solved_run,
    resolve_experiment,
    resolve_structure_settings,
)
from launchsim.constants import OFFLOAD_PER_KG_STAGE1_DRY
from launchsim.offload import OffloadProblem, OffloadResult
from launchsim.vehicle import with_offload, with_stage_dry_mass


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
README_EXPERIMENT = REPO / "experiments" / "silo_offload_2d_readme.yaml"
SYNTHETIC_NAME = "tests/data/structure_synthetic.yaml"
"""The synthetic structure file as an experiment names it (the records quote this)."""
SYNTHETIC = REPO / SYNTHETIC_NAME
PROVENANCE_CENTRAL = (
    f"first-order station sizing, {SYNTHETIC_NAME}, set central, flown, rise_time, "
    "aft_ring, margin 0, no cap"
)
"""The provenance of a default structural case on the synthetic file (the restated dry
mass's ``source`` and the assumption line's model text): the model, the file, the set
and every case setting that changes dm (sizing, dynamic, entry, margin, cap)."""
E_KG_PER_KG = OFFLOAD_PER_KG_STAGE1_DRY
"""E, SP1's offload lost per kg of stage-1 dry mass at the headline (4.381 kg/kg)."""
SLOPE_FLOOR = -1.0 / (2.0 * E_KG_PER_KG)
"""The monotonicity test's bound on dm'(x) [kg/kg]: half the -1/E at which m_res(x, dm(x))
would stop falling (design 4.4); asserted on the synthetic file."""
HARD_FLOOR = -1.0 / E_KG_PER_KG
"""The hard bound -1/E [kg/kg] (about -0.228), asserted on the gate file's frozen sets:
its outer high-mass corner's dm'(x) runs from -0.128 kg/kg at x = 0 to -0.121 at 60 t,
below SLOPE_FLOOR at every one of the five offloads."""
GATE_NAME = "configs/structures/generic_f9_class_2d.yaml"
"""The gate structure file, sized here (never solved, D-SP7-31) for the hard bound."""
SMOOTH_TOL = 1.0e-5
"""How closely the 1 kg and 10 g differences of dm(x) must agree [kg/kg]: the inner
iteration stops below 1e-6 kg (measured agreement 2.5e-9)."""
CROSS_CHECK_KG = 0.002
"""The slow pins' tolerance [kg] (design section 6, criterion 3)."""
XV_TOL_KG = 1.0e-6
"""xv_dry_mass_delta_kg against dm1 + dm2 at x* [kg] (design section 6, criterion 4)."""
START_COMMIT = "15b4e6e"
"""The commit the digests below were captured at, before S3 changed anything."""
OFFLOAD_START_DIGESTS = {
    "experiments/silo_offload_2d.yaml": (
        48,
        "41ddaaf4f9c49c14d403aeca1b4d4dd835a1c24e26f2b33759c9d5b153258c69",
    ),
    "experiments/silo_offload_2d_readme.yaml": (
        2,
        "461524caa7598c43db57d2b2c9795eefc96902b000cc7c47f0cbf7c41a0a8ac9",
    ),
}
"""Per shipped offload experiment, captured at START_COMMIT by ``_offload_inventory``: the
number of offload starts (every case, paired pad, sensitivity arm with its pad and sweep
point case) and the sha256 of their (label, run-dict sha256, vehicle-dict sha256) rows."""
SOLVED_ROWS_DIGEST = "bed579b2b10f311ffd02a2cc4ea81720f0169f286df0b2a124186a5216be9900"
"""Captured at START_COMMIT: the sha256 of (case, run-dict sha256, vehicle-dict sha256) of
``offload_solved_run`` of the record's four gate rows at their x* (``_solved_rows``)."""
PENALTY_DRY_QUANTITY = {
    "value": 24.2,
    "assumed": True,
    "note": (
        "offload case 'silo_cold_s1_dry+2t': 2 t of stage-1 dry mass added, an assumed "
        "structural penalty, not a sized structure; the vehicle's value was 22.2 t (source: "
        "Espace & Exploration No.39 via Wikipedia Falcon 9 Full Thrust "
        "(en.wikipedia.org/wiki/Falcon_9_Full_Thrust, first-stage empty mass))"
    ),
}
"""The penalty row silo_cold_s1_dry+2t's restated stage-1 dry mass, as START_COMMIT wrote
it (key order included)."""


# --------------------------------------------------------------------------- helpers


def _digest(obj: Any) -> str:
    """sha256 hex of json.dumps(obj) (key order kept)."""
    return hashlib.sha256(json.dumps(obj).encode("utf-8")).hexdigest()


def _load_structure(name: str) -> config.StructureFile:
    """The test loader: a structure file by its repository-relative name."""
    return cli.read_structure_file(REPO / name, name)


def _raw() -> tuple[dict[str, Any], dict[str, Any]]:
    """silo_offload_2d.yaml and its vehicle as raw dicts."""
    exp = ss.load_yaml(EXPERIMENT)
    veh = ss.load_yaml(REPO / exp["vehicle"])
    return exp, veh


def _experiment(
    cases: list[dict[str, Any]],
    *,
    block: dict[str, Any] | None = None,
    sensitivity_of: list[str] | None = None,
    sweeps: list[dict[str, Any]] | None = None,
    variants: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """silo_offload_2d with silo_cold only (plus ``variants``), the given offload cases,
    the structure block naming the synthetic file (or ``block``; {} for none), its
    sensitivity params kept for the arms and the given sweeps (none by default)."""
    exp, veh = _raw()
    exp["variants"] = {"silo_cold": exp["variants"]["silo_cold"], **(variants or {})}
    exp["sweeps"] = sweeps or []
    exp["offload"] = {"reference": "pad", "cases": cases}
    if sensitivity_of:
        exp["offload"]["sensitivity_of"] = sensitivity_of
    if block is None:
        block = {"file": SYNTHETIC_NAME}
    if block:
        exp["structure"] = block
    else:
        exp.pop("structure", None)
    return exp, veh


def _resolve(exp: dict[str, Any], veh: dict[str, Any]) -> config.ResolvedExperiment:
    return resolve_experiment(exp, veh, load_structure=_load_structure)


ST_CASE = {"name": "s1_st", "of": "silo_cold", "solve": "stage1", "structure": {}}
PLAIN_CASE = {"name": "s1", "of": "silo_cold", "solve": "stage1"}


@pytest.fixture(scope="module")
def sp1_resolved() -> config.ResolvedExperiment:
    """experiments/silo_offload_2d.yaml through cli.load_experiment."""
    return cli.load_experiment(EXPERIMENT)


@pytest.fixture(scope="module")
def synthetic_file() -> config.StructureFile:
    return _load_structure(SYNTHETIC_NAME)


@pytest.fixture(scope="module")
def synthetic_pad(synthetic_file: config.StructureFile) -> structure.PadLoadSet:
    """The synthetic pad flight of structure_support (the gate vehicle at P_ref) as the
    envelope's load cases."""
    veh = ss.vehicle()
    layout = synthetic_file.config.stack_layout()
    return structure.pad_load_set(
        sim.structure_pad_cases(ss.synthetic_pad_result(veh), veh, layout)
    )


@pytest.fixture(scope="module")
def gate_file() -> config.StructureFile:
    return _load_structure(GATE_NAME)


@pytest.fixture(scope="module")
def gate_pad(gate_file: config.StructureFile) -> structure.PadLoadSet:
    """The same synthetic pad flight on the gate file's layout."""
    veh = ss.vehicle()
    layout = gate_file.config.stack_layout()
    return structure.pad_load_set(
        sim.structure_pad_cases(ss.synthetic_pad_result(veh), veh, layout)
    )


def _transform(
    sp1: config.ResolvedExperiment,
    sfile: config.StructureFile,
    pad: structure.PadLoadSet,
    **settings: Any,
) -> sim.StructureTransform:
    """The structural transform of SP1's silo_cold on the synthetic file and pad."""
    case = StructureCaseConfig(**settings)
    st = resolve_structure_settings(case, sfile, case.sizing, "test")
    start = sp1.variants["silo_cold"]
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


def _bits(v: Any) -> tuple[str, ...]:
    """The masses of a two-stage vehicle as float.hex strings (bit identity)."""
    out = []
    for stage in v.stages:
        out += [stage.dry_mass_kg.hex(), stage.propellant_mass_kg.hex()]
    return (*out, float(v.payload_mass_kg).hex(), float(v.fairing_mass_kg).hex())


def _problem(start_vehicle: Any, transform: Any) -> OffloadProblem:
    """An OffloadProblem whose factory is never called (``vehicle_at`` only)."""

    def factory(vehicle: Any) -> Any:
        raise AssertionError("vehicle_at calls no factory")

    return OffloadProblem(factory, start_vehicle, "stage1", ss.P_REF_KG, None, transform)  # type: ignore[arg-type]


# --------------------------------------------------------------- the transform on the solver


def test_offload_problem_without_a_transform_is_sp1s_offload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With transform None, vehicle_at is ``with_offload`` exactly (SP1's path), the field
    defaults to None and from_factory passes it through; with a transform it is applied
    once, after the offload, at P_ref; ``verify_offload`` flies the vehicle it is given
    without applying any transform again."""
    veh = ss.vehicle(payload_kg=22800.0)
    plain = _problem(veh, None)
    assert OffloadProblem.__dataclass_fields__["transform"].default is None
    for x in (0.0, 1234.5, 41262.90803733282):
        assert _bits(plain.vehicle_at(x)) == _bits(with_offload(veh, "stage1", x))
    calls: list[tuple[float, float]] = []

    def plus_one(v: Any, p_ref: float) -> Any:
        calls.append((v.stages[0].propellant_mass_kg, p_ref))
        return with_stage_dry_mass(v, 0, v.stages[0].dry_mass_kg + 1.0)

    problem = _problem(veh, plus_one)
    out = problem.vehicle_at(1000.0)
    assert calls == [(veh.stages[0].propellant_mass_kg - 1000.0, ss.P_REF_KG)]
    assert out.stages[0].dry_mass_kg == veh.stages[0].dry_mass_kg + 1.0
    assert out.payload_mass_kg == 22800.0  # the solve flies P_ref; the vehicle keeps P0
    seen: list[Any] = []
    budget = SimpleNamespace(final_flag_rel=1e-4)

    def factory(v: Any) -> Any:
        seen.append(v)
        return SimpleNamespace(budget=budget)

    fresh = OffloadProblem.from_factory(factory, veh, "stage1", ss.P_REF_KG, plus_one)
    assert fresh.transform is plus_one and fresh.budget is budget
    record = SimpleNamespace(status="ok", payload_kg=ss.P_REF_KG, flags=())
    monkeypatch.setattr(offload, "run_search", lambda problem: record)
    v = offload.verify_offload(factory, out, ss.P_REF_KG, budget)  # type: ignore[arg-type]
    assert seen[-1] is out and v.passed and len(calls) == 1


def test_stage_dry_mass_helpers() -> None:
    """``with_stage_dry_mass`` sets one stage's dry mass and keeps everything else;
    ``charge_structure`` adds dm1 to stage 1 and dm2 to stage 2, bit for bit as the sum,
    and returns the vehicle itself for dm = 0 (so an uncharged solve flies SP1's
    vehicles)."""
    veh = ss.vehicle()
    out = with_stage_dry_mass(veh, 1, 4321.0)
    assert out.stages[1].dry_mass_kg == 4321.0
    assert out.stages[0] == veh.stages[0] and out.payload_mass_kg == veh.payload_mass_kg
    assert out.stages[1].propellant_mass_kg == veh.stages[1].propellant_mass_kg
    charged = sim.charge_structure(veh, 2000.0, 12.5)
    assert charged.stages[0].dry_mass_kg == veh.stages[0].dry_mass_kg + 2000.0 == 24200.0
    assert charged.stages[1].dry_mass_kg == veh.stages[1].dry_mass_kg + 12.5
    assert sim.charge_structure(veh, 0.0, 0.0) is veh
    with pytest.raises(ValueError, match="dry mass"):
        with_stage_dry_mass(veh, 0, -1.0)


def test_dm_slope_is_bounded_and_smooth(
    sp1_resolved: config.ResolvedExperiment,
    synthetic_file: config.StructureFile,
    synthetic_pad: structure.PadLoadSet,
) -> None:
    """dm(x) = dm1 + dm2 of the flown sizing on the synthetic file: at five offloads from
    0 to 60 t its forward differences at 1 kg and at 10 g agree within SMOOTH_TOL kg/kg and
    both exceed -1/(2 E), E = 4.381 kg/kg, so m_res(x, dm(x)) keeps falling (design 4.4,
    "Monotonicity"); full_load is the same dm at every x (its x = 0 sizing). The half-bound
    is asserted on the synthetic file only: the gate file's frozen sets are held to the
    hard bound -1/E by ``test_gate_sets_exceed_the_hard_bound_inside_the_cap``."""
    tr = _transform(sp1_resolved, synthetic_file, synthetic_pad)
    full = _transform(sp1_resolved, synthetic_file, synthetic_pad, sizing="full_load")
    zero = full.sizing_at(0.0).total_kg
    for x in SLOPE_OFFLOADS_KG:
        dm = tr.sizing_at(x).total_kg
        d_1kg = tr.sizing_at(x + 1.0).total_kg - dm
        d_10g = (tr.sizing_at(x + 0.01).total_kg - dm) / 0.01
        assert d_1kg > SLOPE_FLOOR and d_10g > SLOPE_FLOOR, x
        assert d_1kg == pytest.approx(d_10g, abs=SMOOTH_TOL), x
        assert full.sizing_at(x).total_kg == zero
    assert tr.sizing_at(0.0).total_kg == zero


SLOPE_OFFLOADS_KG = (0.0, 10_000.0, 20_000.0, ss.HEADLINE_OFFLOAD_KG, 60_000.0)
"""The offloads the slope tests size at [kg]."""


@pytest.mark.parametrize(
    ("set_name", "dynamic", "below_half_bound"),
    [
        ("physics_low_mass", "rise_time", False),
        ("physics_high_mass", "rise_time", False),
        ("physics_high_mass", "step", False),
        ("outer_low_mass", "rise_time", False),
        ("outer_high_mass", "rise_time", True),
    ],
)
def test_gate_sets_exceed_the_hard_bound_inside_the_cap(
    sp1_resolved: config.ResolvedExperiment,
    gate_file: config.StructureFile,
    gate_pad: structure.PadLoadSet,
    set_name: str,
    dynamic: str,
    below_half_bound: bool,
) -> None:
    """The gate file's frozen sets, sizing only on the synthetic pad (no solve, D-SP7-31):
    at the five offloads dm'(x) by 1 kg and 10 g differences exceeds the hard bound -1/E
    (the sign change of m_res(x, dm(x)) holds), the two differences agree, and the fixed
    point converges with at least five sizings to spare under the cap (the outer high-mass
    corner, contraction 0.050, takes 10: the reason D-SP7-44 raised the cap from 10 to 25).
    Measured, that corner's dm'(x) runs from -0.128 kg/kg at x = 0 to -0.121 at 60 t,
    below the half-bound the synthetic file is held to at every offload, so the
    half-bound is a synthetic-file assertion only; the record's cap flag carries the
    contraction."""
    tr = _transform(sp1_resolved, gate_file, gate_pad, set=set_name, dynamic=dynamic)
    slopes = []
    for x in SLOPE_OFFLOADS_KG:
        s = tr.sizing_at(x)
        dm = s.total_kg
        d_1kg = tr.sizing_at(x + 1.0).total_kg - dm
        d_10g = (tr.sizing_at(x + 0.01).total_kg - dm) / 0.01
        assert d_1kg > HARD_FLOOR and d_10g > HARD_FLOOR, x
        assert d_1kg == pytest.approx(d_10g, abs=SMOOTH_TOL), x
        assert not s.capped and s.iterations + 5 <= sim.STRUCTURE_FIXED_POINT_MAX_ITERATIONS
        assert s.steps[-1] < sim.STRUCTURE_FIXED_POINT_TOL_KG <= s.steps[-2]
        assert s.contraction is not None and s.contraction < 0.06
        slopes.append(d_1kg)
    assert (min(slopes) < SLOPE_FLOOR) is below_half_bound
    record = sim.structure_record(tr, s, tr.sizing_at(0.0))
    (cap,) = (f for f in record["structure_flags"] if f["name"] == structure.FLAG_FIXED_POINT_CAP)
    assert cap["values"]["contraction"] == s.contraction and cap["fired"] is False


def test_vehicle_at_is_bit_identical_across_call_orders(
    sp1_resolved: config.ResolvedExperiment,
    synthetic_file: config.StructureFile,
    synthetic_pad: structure.PadLoadSet,
) -> None:
    """vehicle_at(x) with the structural transform gives the same bits forwards, in
    reverse, repeated and on a transform built again (each call starts from dm = 0, so
    nothing carries over between calls), equal to ``charge_structure`` of the offloaded
    vehicle with the transform's own sizing at x."""
    start = sp1_resolved.variants["silo_cold"].to_vehicle()
    xs = [ss.HEADLINE_OFFLOAD_KG, 0.0, 20_000.0, ss.HEADLINE_OFFLOAD_KG, 0.01, 60_000.0]
    tr = _transform(sp1_resolved, synthetic_file, synthetic_pad)
    problem = _problem(start, tr)
    forward = [_bits(problem.vehicle_at(x)) for x in xs]
    backward = [_bits(problem.vehicle_at(x)) for x in reversed(xs)][::-1]
    again = _problem(start, _transform(sp1_resolved, synthetic_file, synthetic_pad))
    rebuilt = [_bits(again.vehicle_at(x)) for x in xs]
    assert forward == backward == rebuilt
    assert forward[0] == forward[3]
    for x, bits in zip(xs, forward, strict=True):
        s = tr.sizing_at(x)
        expected = sim.charge_structure(
            with_offload(start, "stage1", x), s.dm_stage1_kg, s.dm_stage2_kg
        )
        assert bits == _bits(expected), x
        assert s.dm_stage1_kg > 0.0


def test_inner_iteration_converges_caps_and_flags(
    sp1_resolved: config.ResolvedExperiment,
    synthetic_file: config.StructureFile,
    synthetic_pad: structure.PadLoadSet,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The fixed point dm = S(push(m + dm)) from dm = 0 at the headline: the first step
    is dm itself, the steps shrink geometrically (the measured contraction below 0.01),
    the last is below STRUCTURE_FIXED_POINT_TOL_KG within the cap of 25 (D-SP7-44) and no
    flag fires; the record's cap flag carries the iterations, the last step, the tolerance,
    the cap and the measured contraction; with the cap lowered to 2 the iteration stops
    short, ``capped`` is set, the record's FLAG_FIXED_POINT_CAP fires with its numbers and
    the run gets the flag line, after the lines of the record's other fired flags (the
    release and payload-limit flags on the synthetic pad) and after its own flags."""
    tr = _transform(sp1_resolved, synthetic_file, synthetic_pad)
    s = tr.sizing_at(ss.HEADLINE_OFFLOAD_KG)
    assert sim.STRUCTURE_FIXED_POINT_TOL_KG == 1.0e-6
    assert sim.STRUCTURE_FIXED_POINT_MAX_ITERATIONS == 25
    assert s.steps[0] == pytest.approx(s.total_kg, rel=1e-2)
    assert all(b < a for a, b in zip(s.steps, s.steps[1:], strict=False))
    assert s.steps[-1] < sim.STRUCTURE_FIXED_POINT_TOL_KG <= s.steps[-2]
    assert 2 < s.iterations <= sim.STRUCTURE_FIXED_POINT_MAX_ITERATIONS and not s.capped
    assert s.contraction is not None and 0.0 < s.contraction < 0.01
    record = sim.structure_record(tr, s, tr.sizing_at(0.0))
    (cap,) = (f for f in record["structure_flags"] if f["name"] == structure.FLAG_FIXED_POINT_CAP)
    assert cap["fired"] is False
    assert cap["values"] == {
        "iterations": s.iterations,
        "last_step_kg": s.steps[-1],
        "tolerance_kg": 1.0e-6,
        "max_iterations": 25,
        "contraction": s.contraction,
    }
    monkeypatch.setattr(sim, "STRUCTURE_FIXED_POINT_MAX_ITERATIONS", 2)
    short = tr.sizing_at(ss.HEADLINE_OFFLOAD_KG)
    assert short.iterations == 2 and short.capped
    assert short.steps == s.steps[:2]
    capped = sim.structure_record(tr, short, short)
    (cap,) = (f for f in capped["structure_flags"] if f["name"] == structure.FLAG_FIXED_POINT_CAP)
    assert cap["fired"] is True and cap["values"]["last_step_kg"] == short.steps[-1]
    assert cap["values"]["max_iterations"] == 2 and cap["values"]["contraction"] is None
    result = dataclasses.replace(_fake_result({"a": 1}), flags=["x"])
    out = sim.with_structure_items(sim.RunResult("r", None, result), capped)  # type: ignore[arg-type]
    fired = [f["name"] for f in capped["structure_flags"] if f["fired"]]
    assert fired == [
        structure.FLAG_RELEASE_UNLOAD,
        structure.FLAG_PAYLOAD_LIMIT,
        structure.FLAG_FIXED_POINT_CAP,
    ]
    assert out.result.flags[0] == "x"
    assert [line.split(":")[0] for line in out.result.flags[1:]] == fired
    assert out.result.flags[-1] == (
        f"{structure.FLAG_FIXED_POINT_CAP}: the structural fixed point stopped at its cap "
        f"of 2 sizings, last step {short.steps[-1]:.3g} kg (tolerance 1e-06 kg)"
    )
    assert list(out.result.metrics) == ["a", *sim.STRUCTURE_RECORD_KEYS]


def test_structure_record_keys_and_values(
    sp1_resolved: config.ResolvedExperiment,
    synthetic_file: config.StructureFile,
    synthetic_pad: structure.PadLoadSet,
) -> None:
    """``structure_record``'s keys are design 4.4's, in STRUCTURE_RECORD_KEYS order; dm at
    x* (dm1 + dm2, stage 2 apart) and at x = 0 from the transform's sizings; the settings
    as resolved (the synthetic file's central rise time 0.8 s and frequency 3 Hz); the
    DLF min(2, 1 + T/(pi t_r)) with T = 1/f; the elements summing to dm and splitting
    into the closed-form elements and the ring; the governing element the largest; the
    four flags; the file's path and sha256; the envelope pad."""
    tr = _transform(sp1_resolved, synthetic_file, synthetic_pad)
    at_x, at_0 = tr.sizing_at(ss.HEADLINE_OFFLOAD_KG), tr.sizing_at(0.0)
    rec = sim.structure_record(tr, at_x, at_0)
    assert tuple(rec) == sim.STRUCTURE_RECORD_KEYS
    assert rec["structure_charged"] is True
    assert rec["structure_dm_kg"] == at_x.dm_stage1_kg + at_x.dm_stage2_kg
    assert rec["structure_dm_stage2_kg"] == at_x.dm_stage2_kg
    assert rec["structure_dm_x0_kg"] == at_0.total_kg > rec["structure_dm_kg"]
    assert (rec["structure_set"], rec["structure_sizing"]) == ("central", "flown")
    assert (rec["structure_dynamic"], rec["structure_entry"]) == ("rise_time", "aft_ring")
    assert rec["structure_margin"] == 0.0 and rec["structure_envelope_cap_g"] is None
    assert rec["structure_overrides"] == {}
    t_r, f = 0.8, 3.0  # the synthetic file's centrals
    assert rec["structure_t_r_s"] == t_r and rec["structure_f_Hz"] == f
    assert rec["structure_dlf"] == pytest.approx(min(2.0, 1.0 + (1.0 / f) / (math.pi * t_r)))
    assert rec["structure_n_peak_g"] > rec["structure_n_q_g"] > 4.0
    assert rec["structure_ramp_cost_rel"] > 0.0
    elements = rec["structure_elements"]
    assert math.fsum(elements.values()) == pytest.approx(rec["structure_dm_kg"], abs=1e-9)
    assert rec["structure_closed_form_kg"] + rec["structure_ring_kg"] == pytest.approx(
        rec["structure_dm_kg"], abs=1e-9
    )
    assert elements["stage1.load_ring"] == rec["structure_ring_kg"] > 0.0
    gov = rec["structure_governing"]
    assert elements[f"{gov['stage']}.{gov['element']}"] == max(elements.values())
    names = [flag["name"] for flag in rec["structure_flags"]]
    assert names == [
        structure.FLAG_RELEASE_UNLOAD,
        structure.FLAG_UPPER_STACK,
        structure.FLAG_PAYLOAD_LIMIT,
        structure.FLAG_FIXED_POINT_CAP,
    ]
    assert rec["structure_iterations"] == at_x.iterations
    assert rec["structure_file"] == SYNTHETIC_NAME
    assert rec["structure_file_sha256"] == hashlib.sha256(SYNTHETIC.read_bytes()).hexdigest()
    assert rec["structure_envelope_pad"] == "synthetic pad"
    json.dumps(results_io.json_safe(rec))  # plain data, writable to metrics.json


def test_transform_refuses_a_start_without_a_push_and_other_drives(
    sp1_resolved: config.ResolvedExperiment,
    synthetic_file: config.StructureFile,
    synthetic_pad: structure.PadLoadSet,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The builder refuses the pad (no push) with a ValueError and any drive other than
    constant_accel with a NotImplementedError naming step S4b (a flown push inside the
    transform is S4b's); a resolved case without structure has no transform."""
    st = resolve_structure_settings(StructureCaseConfig(), synthetic_file, "flown", "test")
    pad = sp1_resolved.baseline
    with pytest.raises(ValueError, match="no push"):
        sim.build_structure_transform(
            st, pad.to_vehicle(), pad, "stage1", synthetic_pad, ss.P_REF_KG,
            envelope_pad="p", envelope_pad_key="k",
        )  # fmt: skip
    real = sim.planar_setup

    class OtherDrive:
        """A drive that is not constant_accel."""

    def setup(run: Any, vehicle: Any) -> Any:
        return dataclasses.replace(real(run, vehicle), assist=OtherDrive())

    monkeypatch.setattr(sim, "planar_setup", setup)
    start = sp1_resolved.variants["silo_cold"]
    with pytest.raises(NotImplementedError, match="S4b"):
        sim.build_structure_transform(
            st, start.to_vehicle(), start, "stage1", synthetic_pad, ss.P_REF_KG,
            envelope_pad="p", envelope_pad_key="k",
        )  # fmt: skip
    case = next(c for c in sp1_resolved.offload.cases if c.name == "silo_cold_s1")  # type: ignore[union-attr]
    with pytest.raises(ValueError, match="no structure"):
        sim.offload_structure_transform(case, SimpleNamespace(), ss.P_REF_KG)  # type: ignore[arg-type]
    assert ConstantAccelAssist is not OtherDrive


# ------------------------------------------------------------------- the configuration


def test_structural_case_and_block_resolve(synthetic_file: config.StructureFile) -> None:
    """A structural case resolves with the defaults of design 4.3 (central, flown,
    rise_time, aft_ring, margin 0, no cap, no overrides), the provenance "first-order
    station sizing, <file>, set <set>, <sizing>, <dynamic>, <entry>, margin <m>, no cap"
    (an outer set's own cap as "cap <g> g0"), the file's central coefficients, a start equal
    to an unstructured case's (no dict changes) and a dump that carries the field while
    an unstructured case's dump does not; an outer set brings its own margin and cap,
    and a case may restate them equal; overrides of a design axis enter the coefficients;
    a sweep point's case inherits the field; a payload case resolves at the full load."""
    cases = [
        PLAIN_CASE,
        ST_CASE,
        {**ST_CASE, "name": "s1_hi", "structure": {"set": "outer_high_mass"}},
        {**ST_CASE, "name": "s1_lo", "structure": {"set": "outer_low_mass", "margin": 0.25}},
        {
            **ST_CASE,
            "name": "s1_ax",
            "structure": {
                "sizing": "full_load",
                "dynamic": "step",
                "entry": "thrust_structure",
                "margin": 0.1,
                "envelope_cap_g": 4.5,
                "overrides": {"nof.nof_barrel": 1.54, "ring.ring_pads": 4},
            },
        },
    ]
    sweep = {"of": "silo_cold", "axes": {"assist.stroke_m": [50, 100]}, "offload": ["s1_st"]}
    block = {
        "file": SYNTHETIC_NAME,
        "payload_cases": [{"name": "cold_pstar_st", "of": "silo_cold", "set": "central"}],
    }
    resolved = _resolve(*_experiment(cases, block=block, sweeps=[sweep]))
    assert resolved.offload is not None and resolved.structure is not None
    by = {c.name: c for c in resolved.offload.cases}
    assert by["s1"].structure is None
    st = by["s1_st"].structure
    assert st is not None and st.file.path == SYNTHETIC_NAME
    assert st.settings() == {
        "set": "central",
        "sizing": "flown",
        "dynamic": "rise_time",
        "entry": "aft_ring",
        "margin": 0.0,
        "envelope_cap_g": None,
        "overrides": {},
    }
    assert st.provenance == PROVENANCE_CENTRAL
    assert st.coefficients == synthetic_file.config.coefficients()
    assert sim.trajectory_key(by["s1_st"].start) == sim.trajectory_key(by["s1"].start)
    assert {**by["s1_st"].start.run_dict, "name": "s1"} == by["s1"].start.run_dict
    assert by["s1_st"].start.vehicle_dict == by["s1"].start.vehicle_dict
    assert "structure" not in by["s1"].config.model_dump()
    assert by["s1_st"].config.model_dump()["structure"]["sizing"] == "flown"
    hi, lo = by["s1_hi"].structure, by["s1_lo"].structure
    assert hi is not None and lo is not None
    assert (hi.margin, hi.envelope_cap_g) == (0.0, 4.0)
    assert (lo.margin, lo.envelope_cap_g) == (0.25, None)
    assert hi.coefficients == synthetic_file.config.coefficients("outer_high_mass")
    assert hi.provenance == (
        f"first-order station sizing, {SYNTHETIC_NAME}, set outer_high_mass, flown, "
        "rise_time, aft_ring, margin 0, cap 4 g0"
    )
    assert lo.provenance.endswith(
        ", set outer_low_mass, flown, rise_time, aft_ring, margin 0.25, no cap"
    )
    ax = by["s1_ax"].structure
    assert ax is not None and ax.sizing == "full_load" and ax.entry == "thrust_structure"
    assert (ax.margin, ax.envelope_cap_g, ax.dynamic) == (0.1, 4.5, "step")
    assert ax.coefficients.nof_barrel == 1.54 and ax.coefficients.ring_pads == 4
    assert ax.provenance == (
        f"first-order station sizing, {SYNTHETIC_NAME}, set central, full_load, step, "
        "thrust_structure, margin 0.1, cap 4.5 g0, overrides nof.nof_barrel 1.54, "
        "ring.ring_pads 4"
    )
    assert len({by[n].structure.key for n in ("s1_st", "s1_hi", "s1_lo", "s1_ax")}) == 4  # type: ignore[union-attr]
    points = resolved.sweeps[0]
    assert [p.offload[0].structure is st for p in points] == [True, True]
    (pc,) = resolved.structure.payload_cases
    assert pc.name == "cold_pstar_st" and pc.variant is resolved.variants["silo_cold"]
    assert pc.structure.sizing == config.STRUCTURE_SIZING_FULL_LOAD
    assert resolved.structure.file.sha256 == synthetic_file.sha256
    assert typing.get_args(config.StructureSetChoice) == (
        config.STRUCTURE_CENTRAL_SET,
        *config.STRUCTURE_SET_NAMES,
    )
    assert config.structure_design_axis_paths() == (
        "nof.nof_barrel",
        "nof.nof_stiffened",
        "nof.nof_dome",
        "nof.nof_entry_ratio",
        "dynamics.rise_time_s",
        "dynamics.axial_frequency_Hz",
        "thrust_structure.k_ts_kg_per_kN",
        "ring.ring_pads",
    )
    plain = _resolve(*_experiment([PLAIN_CASE], block={}))
    assert plain.structure is None and plain.offload is not None
    assert plain.offload.cases[0].structure is None


NO_PUSH = {"pad_copy": {"assist": {"model": "none"}}}
"""A variant with no push (assist none)."""


@pytest.mark.parametrize(
    ("cases", "kwargs", "match"),
    [
        (
            [{**ST_CASE, "stage1_dry_mass_added_t": 2.0}],
            {},
            "stage1_dry_mass_added_t",
        ),
        ([{**ST_CASE, "paired_pad": True}], {}, "paired_pad"),
        ([{**ST_CASE, "stage2_offload_t": 2.0}], {}, "without stage2_offload_t"),
        (
            [{"name": "f", "of": "silo_cold", "fixed": {"stage1_t": 1.0}, "structure": {}}],
            {},
            "stage-1 solve",
        ),
        ([{**ST_CASE, "solve": "both"}], {"pad_control": True}, "stage-1 solve"),
        ([{**ST_CASE, "of": "pad_copy"}], {"variants": NO_PUSH}, "no push"),
        ([ST_CASE], {"block": {}}, "no structure block"),
        ([{**ST_CASE, "structure": {"set": "corner"}}], {}, "set"),
        ([{**ST_CASE, "structure": {"sizing": "both"}}], {}, "sizing"),
        ([{**ST_CASE, "structure": {"dynamic": "sinc"}}], {}, "dynamic"),
        ([{**ST_CASE, "structure": {"entry": "nose"}}], {}, "entry"),
        ([{**ST_CASE, "structure": {"margin": -0.1}}], {}, "margin"),
        ([{**ST_CASE, "structure": {"envelope_cap_g": 1.0}}], {}, "envelope_cap_g"),
        ([{**ST_CASE, "structure": {"envelope_cap_g": None, "colour": 1}}], {}, "colour"),
        (
            [{**ST_CASE, "structure": {"overrides": {"materials.E_GPa": 75.0}}}],
            {},
            "not a design-axis",
        ),
        (
            [{**ST_CASE, "structure": {"overrides": {"nof.nof_barrel": True}}}],
            {},
            "finite number",
        ),
        (
            [{**ST_CASE, "structure": {"overrides": {"nof.nof_barrel": 3.0}}}],
            {},
            "outside",
        ),
        (
            [{**ST_CASE, "structure": {"overrides": {"ring.ring_pads": 4.5}}}],
            {},
            "whole number",
        ),
        (
            [
                {
                    **ST_CASE,
                    "structure": {"set": "outer_low_mass", "overrides": {"nof.nof_dome": 1.6}},
                }
            ],
            {},
            "outer set",
        ),
        (
            [{**ST_CASE, "structure": {"set": "outer_low_mass", "margin": 0.0}}],
            {},
            "records margin",
        ),
        (
            [{**ST_CASE, "structure": {"set": "outer_high_mass", "envelope_cap_g": None}}],
            {},
            "records envelope_cap_g",
        ),
        (
            [PLAIN_CASE],
            {"block": {"file": SYNTHETIC_NAME, "payload_cases": [{"name": "p", "of": "pad"}]}},
            "baseline",
        ),
        (
            [PLAIN_CASE],
            {"block": {"file": SYNTHETIC_NAME, "payload_cases": [{"name": "p", "of": "nope"}]}},
            "no such variant",
        ),
        (
            [PLAIN_CASE],
            {
                "block": {
                    "file": SYNTHETIC_NAME,
                    "payload_cases": [{"name": "p", "of": "pad_copy"}],
                },
                "variants": NO_PUSH,
            },
            "no push",
        ),
        (
            [PLAIN_CASE],
            {
                "block": {
                    "file": SYNTHETIC_NAME,
                    "payload_cases": [
                        {"name": "p", "of": "silo_cold"},
                        {"name": "p", "of": "silo_cold"},
                    ],
                }
            },
            "used twice",
        ),
        (
            [PLAIN_CASE],
            {
                "block": {
                    "file": SYNTHETIC_NAME,
                    "payload_cases": [{"name": "s1", "of": "silo_cold"}],
                }
            },
            "used twice",
        ),
        ([PLAIN_CASE], {"block": {"file": ""}}, "file"),
    ],
)
def test_structural_refusals(
    cases: list[dict[str, Any]], kwargs: dict[str, Any], match: str
) -> None:
    """Every refusal of design 4.3 and of this step: a structural case with the assumed
    penalty, with paired_pad, with stage2_offload_t (its x = 0 start would not be the
    full load that ``sizing: full_load`` sizes), as a fixed case or a solve other than
    stage 1, on a variant with no push, without the experiment's structure block; an
    unknown set, sizing,
    dynamic mode or entry, a negative margin, a cap at 1 g0, an unknown key, an override
    that is not a design axis, a bool, out of its range or not a whole pad count, any
    override or a different margin or cap on an outer set; a payload case on the baseline,
    on an unknown or push-less variant, twice, or named like a run; a blank file."""
    pad_control = kwargs.pop("pad_control", False)
    exp, veh = _experiment(cases, **kwargs)
    if pad_control:
        exp["offload"]["pad_control"] = True
    with pytest.raises(ValueError, match=match):
        _resolve(exp, veh)


def test_structure_block_needs_its_loader_its_vehicle_and_the_planar_payload_search(
    synthetic_file: config.StructureFile, planar_pins: Any
) -> None:
    """A block resolved without load_structure is refused (config.py does no I/O), and so
    are a file that does not serve the experiment's vehicle, a frozen set the file has
    not written, and the block on an experiment without the payload figure of merit."""
    exp, veh = _experiment([ST_CASE])
    with pytest.raises(ValueError, match="needs load_structure"):
        resolve_experiment(exp, veh)
    other = copy.deepcopy(synthetic_file.content)
    other["applies_to"] = ["another_vehicle"]
    wrong = config.StructureFile(
        SYNTHETIC_NAME, config.StructureConfig.model_validate(other), other, "x"
    )
    with pytest.raises(ValueError, match="applies to"):
        resolve_experiment(exp, veh, load_structure=lambda name: wrong)
    unfrozen = copy.deepcopy(synthetic_file.content)
    del unfrozen["sets"]
    bare = config.StructureFile(
        SYNTHETIC_NAME, config.StructureConfig.model_validate(unfrozen), unfrozen, "x"
    )
    exp_set, _ = _experiment([{**ST_CASE, "structure": {"set": "physics_low_mass"}}])
    with pytest.raises(ValueError, match="no frozen sets"):
        resolve_experiment(exp_set, veh, load_structure=lambda name: bare)
    assert resolve_experiment(exp, veh, load_structure=lambda name: bare).structure is not None
    fast = planar_pins.load_sibling("test_planar_pipeline")
    exp_fom = fast._fixed(_experiment([PLAIN_CASE], block={})[0], ("silo_cold",))
    exp_fom.pop("offload")
    _resolve(copy.deepcopy(exp_fom), veh)  # the fixed-guidance experiment resolves
    exp_fom["structure"] = {"file": SYNTHETIC_NAME}
    with pytest.raises(ValueError, match="figure_of_merit payload"):
        _resolve(exp_fom, veh)


def test_structure_file_is_read_with_its_sha256_and_plain_content(tmp_path: Path) -> None:
    """``cli.read_structure_file`` gives the validated config, the parsed mapping without
    YAML aliases (the gate file's four tanks share one MEOP anchor; the copies are
    distinct, so resolved_config.yaml writes no anchors) and the sha256 of the bytes;
    a missing, non-UTF-8, non-mapping or invalid file is one CliError. ``cli.load_experiment``
    finds the block's file next to the experiment, else at the repository root (a copy in
    both places: the one next to the experiment wins), and passes it as ``load_structure``
    under the path the records quote (``cli.recorded_config_path``: relative to the
    repository root when the file lies under it, whether named relative to the experiment
    or by a rooted path; as given for a file outside the repository); a missing one names
    "structure file"."""
    gate = cli.read_structure_file(ss.GATE_STRUCTURE, "configs/structures/generic_f9_class_2d.yaml")
    assert gate.sha256 == hashlib.sha256(ss.GATE_STRUCTURE.read_bytes()).hexdigest()
    assert gate.content == yaml.safe_load(ss.GATE_STRUCTURE.read_text(encoding="utf-8"))
    p = gate.content["pressures"]
    assert p["stage1_lox"]["p_meop_bar"] == p["stage1_rp1"]["p_meop_bar"]
    assert p["stage1_lox"]["p_meop_bar"] is not p["stage1_rp1"]["p_meop_bar"]
    dumped = yaml.safe_dump(gate.content)
    assert "&id0" not in dumped and "*id0" not in dumped
    assert gate.config.name == "generic_f9_class_2d"
    with pytest.raises(cli.CliError, match="not found"):
        cli.read_structure_file(tmp_path / "missing.yaml", "missing.yaml")
    bad = tmp_path / "bad.yaml"
    bad.write_bytes(b"name: \xff\n")
    with pytest.raises(cli.CliError, match="not UTF-8"):
        cli.read_structure_file(bad, "bad.yaml")
    bad.write_text("- a list\n", encoding="utf-8")
    with pytest.raises(cli.CliError, match="mapping"):
        cli.read_structure_file(bad, "bad.yaml")
    bad.write_text("name: x\n", encoding="utf-8")
    with pytest.raises(cli.CliError, match="invalid structure file"):
        cli.read_structure_file(bad, "bad.yaml")
    exp, _ = _experiment([ST_CASE])
    exp["vehicle"] = str(REPO / exp["vehicle"])
    project = tmp_path / "project"
    (project / "tests" / "data").mkdir(parents=True)
    (project / "pyproject.toml").write_text("", encoding="utf-8")
    (project / SYNTHETIC_NAME).write_bytes(SYNTHETIC.read_bytes())
    (project / "experiments").mkdir()
    here = project / "experiments" / "exp.yaml"
    here.write_text(yaml.safe_dump(exp), encoding="utf-8")
    resolved = cli.load_experiment(here)  # not next to the experiment: at the repository root
    assert resolved.structure is not None and resolved.structure.file.path == SYNTHETIC_NAME
    sha = hashlib.sha256(SYNTHETIC.read_bytes()).hexdigest()
    assert resolved.structure.file.sha256 == sha
    # a copy next to the experiment (one comment line longer) wins over the root's
    local_copy = project / "experiments" / SYNTHETIC_NAME
    local_copy.parent.mkdir(parents=True)
    local_bytes = SYNTHETIC.read_bytes() + b"# the copy next to the experiment\n"
    local_copy.write_bytes(local_bytes)
    nearer = cli.load_experiment(here).structure
    assert nearer is not None and nearer.file.sha256 == hashlib.sha256(local_bytes).hexdigest()
    assert nearer.file.path == f"experiments/{SYNTHETIC_NAME}"  # quoted from the root
    local = project / "experiments" / "local.yaml"
    local.write_bytes(SYNTHETIC.read_bytes())
    exp["structure"] = {"file": "local.yaml"}
    here.write_text(yaml.safe_dump(exp), encoding="utf-8")
    found = cli.load_experiment(here).structure
    assert found is not None and found.file.path == "experiments/local.yaml"
    assert found.file.sha256 == sha
    # a rooted path under the repository is quoted relative to its root; one outside, as given
    exp["structure"] = {"file": str(project / SYNTHETIC_NAME)}
    here.write_text(yaml.safe_dump(exp), encoding="utf-8")
    rooted = cli.load_experiment(here).structure
    assert rooted is not None and rooted.file.path == SYNTHETIC_NAME
    outside = tmp_path / "outside.yaml"
    outside.write_bytes(SYNTHETIC.read_bytes())
    exp["structure"] = {"file": str(outside)}
    here.write_text(yaml.safe_dump(exp), encoding="utf-8")
    away = cli.load_experiment(here).structure
    assert away is not None and away.file.path == str(outside) and away.file.sha256 == sha
    assert cli.recorded_config_path(here, outside, "as given") == "as given"
    exp["structure"] = {"file": "nowhere.yaml"}
    here.write_text(yaml.safe_dump(exp), encoding="utf-8")
    with pytest.raises(cli.CliError, match=r"structure file 'nowhere\.yaml' not found"):
        cli.load_experiment(here)


# --------------------------------------------------------------- the dicts SP1 resolves


def _offload_inventory(path: Path) -> list[tuple[str, str, str]]:
    """Every offload start an experiment resolves (cases, paired pads, arms with their
    pads, sweep point cases) as (label, run-dict sha256, vehicle-dict sha256)."""
    r = cli.load_experiment(path)
    assert r.offload is not None
    rows = []
    for c in r.offload.cases:
        rows.append((f"case {c.name}", _digest(c.start.run_dict), _digest(c.start.vehicle_dict)))
        if c.pad_start is not None:
            rows.append(
                (f"pad {c.name}", _digest(c.pad_start.run_dict), _digest(c.pad_start.vehicle_dict))
            )
    for a in r.offload.arms:
        start, pad = a.start, a.pad
        rows.append((f"arm {start.name}", _digest(start.run_dict), _digest(start.vehicle_dict)))
        rows.append((f"armpad {start.name}", _digest(pad.run_dict), _digest(pad.vehicle_dict)))
    for pts in r.sweeps:
        for p in pts:
            for c in p.offload:
                rows.append(
                    (
                        f"sweep {p.sweep_index} {c.start.name}",
                        _digest(c.start.run_dict),
                        _digest(c.start.vehicle_dict),
                    )
                )
    return rows


def _solved_rows(resolved: config.ResolvedExperiment) -> list[tuple[str, str, str]]:
    """``offload_solved_run`` of the record's four gate rows at their x*."""
    assert resolved.offload is not None
    rows = []
    for row in ss.sp1_record()["gate"]["stage1_offload_cases"]:
        c = next(c for c in resolved.offload.cases if c.name == row["case"])
        f = offload_solved_run(c.start, "stage1", row["offload_kg"], c.name, c.start.name)
        rows.append((row["case"], _digest(f.run_dict), _digest(f.vehicle_dict)))
    return rows


def test_sp1s_resolved_and_solved_dicts_are_unchanged(
    sp1_resolved: config.ResolvedExperiment,
) -> None:
    """Every offload start of the two shipped offload experiments, the solved-run dicts of
    SP1's four gate rows and the penalty row's restated dry mass equal what the start
    commit 15b4e6e produced (digests captured there; the penalty row's Quantity written
    out, key order included): the new field, block and arguments change no dict of a
    case without structure. The penalty form refuses a stage-2 mass or a note without a
    provenance, and the modelled form a blank note."""
    for rel, (count, digest) in OFFLOAD_START_DIGESTS.items():
        rows = _offload_inventory(REPO / rel)
        assert (len(rows), _digest(rows)) == (count, digest), rel
    assert _digest(_solved_rows(sp1_resolved)) == SOLVED_ROWS_DIGEST
    assert sp1_resolved.offload is not None
    pen = next(c for c in sp1_resolved.offload.cases if c.name == "silo_cold_s1_dry+2t")
    dry = pen.start.vehicle_dict["stages"][0]["dry_mass_t"]
    assert json.dumps(dry) == json.dumps(PENALTY_DRY_QUANTITY)
    vd = pen.start.vehicle_dict
    with pytest.raises(ValueError, match="only with a provenance"):
        offload_overrides(vd, [0.0, 0.0], 0.0, "w", dry_added_stage2_kg=1.0)
    with pytest.raises(ValueError, match="only with a provenance"):
        offload_overrides(vd, [0.0, 0.0], 1.0, "w", note="n")
    with pytest.raises(ValueError, match="note"):
        offload_overrides(vd, [0.0, 0.0], 1.0, "w", provenance="p")
    with pytest.raises(ValueError, match="together"):
        offload_solved_run(pen.start, "stage1", 1.0, "c", "n", provenance="p")


def test_sp1_record_carries_each_rows_verification() -> None:
    """tests/data/silo_offload_2d_record.json's rows carry, since S3, the P* of each row's
    independent verification search (copied from the same metrics.json as the offloads,
    the note says so): every one within SP1's flag tolerance 1e-4 P_ref of its block's
    P_ref, the +2 t row's 0.00299 kg above it (so the cross-check compares P* with SP1's
    own, not with P_ref within 0.002 kg: D-SP7-42)."""
    rec = ss.sp1_record()
    assert "verification_payload_kg" in rec["_note"] and "SP7 step S3" in rec["_note"]
    for block in ("gate", "readme_loads"):
        p_ref = rec[block]["reference_payload_kg"]
        for row in rec[block]["stage1_offload_cases"]:
            assert abs(row["verification_payload_kg"] - p_ref) <= 1.0e-4 * p_ref, row["case"]
    plus2 = _gate_row("silo_cold_s1_dry+2t")["verification_payload_kg"]
    assert plus2 - rec["gate"]["reference_payload_kg"] == pytest.approx(0.00299, abs=1e-5)


def test_structural_solved_run_restates_dm_with_its_provenance(
    sp1_resolved: config.ResolvedExperiment,
) -> None:
    """``offload_solved_run`` of a structural case restates each stage's dry mass with dm
    added, ``source`` the structure's provenance and the note naming the modelled mass
    (never ``assumed``); its vehicle carries dm1 and dm2; with dm > 0 its trajectory key
    differs from the unstructured run's at the same x* (with dm = 0 on both stages the
    dict is the unstructured run's, and the memo's structure key keeps the cases apart);
    a stage with dm = 0 is left as the vehicle file states it."""
    start = sp1_resolved.variants["silo_cold"]
    x = 15_000.0
    prov = PROVENANCE_CENTRAL
    final = offload_solved_run(
        start, "stage1", x, "s1_st", "s1_st", structure_dm_kg=(1234.5, 67.75), provenance=prov
    )
    plain = offload_solved_run(start, "stage1", x, "s1_st", "s1_st")
    s1, s2 = (final.vehicle_dict["stages"][i]["dry_mass_t"] for i in (0, 1))
    for q, kg, base_t in ((s1, 1234.5, 22.2), (s2, 67.75, 4.0)):
        assert list(q) == ["value", "source", "note"] and q["source"] == prov
        assert q["value"] == pytest.approx(base_t + kg / 1000.0, rel=1e-15)
        assert config.STRUCTURE_DRY_NOTE in q["note"] and "assumed" not in q
    assert "stage-1 dry mass added" in s1["note"] and "stage-2 dry mass added" in s2["note"]
    v, p = final.to_vehicle(), plain.to_vehicle()
    assert v.stages[0].dry_mass_kg == pytest.approx(p.stages[0].dry_mass_kg + 1234.5, abs=1e-9)
    assert v.stages[1].dry_mass_kg == pytest.approx(p.stages[1].dry_mass_kg + 67.75, abs=1e-9)
    assert v.stages[0].propellant_mass_kg == p.stages[0].propellant_mass_kg
    assert sim.trajectory_key(final) != sim.trajectory_key(plain)
    one = offload_solved_run(
        start, "stage1", x, "s1_st", "s1_st", structure_dm_kg=(10.0, 0.0), provenance=prov
    )
    assert one.vehicle_dict["stages"][1] == plain.vehicle_dict["stages"][1]


# --------------------------------------------------------------- the pass on fake runs

P_REF_FAKE = ss.P_REF_KG
"""The fake pad's P* [kg] (the gate's P_ref, so the synthetic pad's vehicle matches)."""
X_FAKE = 15_000.0
"""The offload x* [kg] a fake solve returns."""
DRY_PARAM = "vehicle.stages.stage1.dry_mass_t"
EFF_PARAM = "assist.drive_efficiency"


def _fake_result(metrics: dict[str, Any], search: Any = None) -> sim.Result:
    return sim.Result(
        metrics=dict(metrics),
        timeseries=pd.DataFrame(),
        loss_budget=None,
        assist_budget=None,
        assumptions=[],
        phases=[],
        status="inserted",
        flags=[],
        model=config.PLANAR_2D,
        search=search,
    )


def _fake_rr(resolved: Any, payload_kg: float) -> sim.RunResult:
    metrics = {"payload_kg": payload_kg, "search_status": "ok", "run_checks": "ok"}
    search = SimpleNamespace(status="ok", payload_kg=payload_kg, flags=())
    return sim.RunResult(resolved.name, resolved, _fake_result(metrics, search))


@pytest.fixture
def fake_pass(
    monkeypatch: pytest.MonkeyPatch,
    synthetic_pad: structure.PadLoadSet,
) -> SimpleNamespace:
    """The sim seams of the offload pass replaced by fakes: ``run_resolved`` (P* = P_ref
    + 0.5 kg, each run's name and vehicle dict logged), ``matched_run`` (None),
    ``solve_resolved_offload`` (ok at X_FAKE, each call logged with its transform),
    ``offload_run_result`` (metrics only) and ``offload_structure_transform`` (the real
    builder on the synthetic pad, each call's pad name logged), so the real structural
    sizing runs without any flight."""
    state = SimpleNamespace(solves=[], ran=[], pads=[], fail=set())

    def run_resolved(resolved: Any) -> sim.RunResult:
        state.ran.append((resolved.name, resolved.vehicle_dict))
        return _fake_rr(resolved, P_REF_FAKE + 0.5)

    def solve(start: Any, mode: str, p_ref: float, *, transform: Any = None) -> OffloadResult:
        state.solves.append((start.name, transform))
        load = start.to_vehicle().stages[0].propellant_mass_kg
        if start.name in state.fail:
            nan = math.nan
            return OffloadResult(
                mode=mode,
                reference_payload_kg=p_ref,
                load_kg=load,
                status="search_failed",
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
                n_evaluations=0,
                grid=(),
                verification=None,
                flags=(),
                failure_kind="test",
                failure_message="a failed test solve",
            )
        vehicle = with_offload(start.to_vehicle(), mode, X_FAKE)  # type: ignore[arg-type]
        if transform is not None:
            vehicle = transform(vehicle, p_ref)
        return OffloadResult(
            mode=mode,
            reference_payload_kg=p_ref,
            load_kg=load,
            status="ok",
            offload_kg=X_FAKE,
            root_kg=X_FAKE,
            gamma_star_rad=0.4,
            m_res_kg=0.01,
            dv_margin_mps=0.001,
            dv_shortfall_mps=math.nan,
            at_offload=None,
            recorded=SimpleNamespace(),
            offloaded_vehicle=vehicle,
            evaluations=(),
            n_evaluations=0,
            grid=(),
            verification=None,
            flags=(),
        )

    def offload_run_result(final: Any, res: OffloadResult) -> sim.RunResult:
        metrics = {"payload_kg": res.reference_payload_kg, "run_checks": "ok"}
        return sim.RunResult(final.name, final, _fake_result(metrics))

    def transform_for(case: Any, pad: Any, p_ref: float) -> sim.StructureTransform:
        state.pads.append((case.start.name, pad.name))
        assert case.structure is not None
        return sim.build_structure_transform(
            case.structure,
            case.variant.to_vehicle(),
            case.start,
            case.config.mode,
            synthetic_pad,
            p_ref,
            envelope_pad=pad.name,
            envelope_pad_key=sim.trajectory_key(pad.resolved),
        )

    monkeypatch.setattr(sim, "run_resolved", run_resolved)
    monkeypatch.setattr(sim, "rerun_resolved", lambda resolved, hit: run_resolved(resolved))
    monkeypatch.setattr(sim, "matched_run", lambda *a, **k: None)
    monkeypatch.setattr(sim, "solve_resolved_offload", solve)
    monkeypatch.setattr(sim, "offload_run_result", offload_run_result)
    monkeypatch.setattr(sim, "offload_structure_transform", transform_for)
    return state


def _pass(
    cases: list[dict[str, Any]], sensitivity_of: list[str] | None = None, **kwargs: Any
) -> tuple[config.ResolvedExperiment, results_io.OffloadReport]:
    """The test experiment resolved and its offload pass on fake runs."""
    exp, veh = _experiment(cases, sensitivity_of=sensitivity_of, **kwargs)
    if sensitivity_of:
        exp["sensitivity"] = {"of": [], "params": {DRY_PARAM: 0.1, EFF_PARAM: 0.1}}
    resolved = _resolve(exp, veh)
    baseline = _fake_rr(resolved.baseline, P_REF_FAKE)
    variants = {n: _fake_rr(r, P_REF_FAKE + 1500.0) for n, r in resolved.variants.items()}
    report = results_io.planar_offload(resolved, baseline, variants)
    assert report is not None
    return resolved, report


def test_structural_and_plain_cases_never_share_a_solve(fake_pass: SimpleNamespace) -> None:
    """A structural and an unstructured case of one variant (the same start trajectory
    key, since structure changes no dict) are solved separately, the structural one with
    its transform; two structural cases of other settings separately again; the same
    structural case twice in one pass (a second name) reuses its solve. The structural
    verification flies the start with dm restated under the structure's provenance (never
    the unstructured verification run), and the recorded run is assembled on the solve's
    offloaded vehicle, which carries dm."""
    cases = [
        PLAIN_CASE,
        ST_CASE,
        {**ST_CASE, "name": "s1_st_again"},
        {**ST_CASE, "name": "s1_full", "structure": {"sizing": "full_load"}},
    ]
    _resolved, report = _pass(cases)
    names = [(name, t is not None) for name, t in fake_pass.solves]
    assert names == [("s1", False), ("s1_st", True), ("s1_full", True)]
    st_t = fake_pass.solves[1][1]
    assert st_t.settings.key != fake_pass.solves[2][1].settings.key
    by = {c["name"]: c for c in report.record["cases"]}
    assert by["s1_st_again"]["structure_dm_kg"] == by["s1_st"]["structure_dm_kg"]
    verified = {name: vd for name, vd in fake_pass.ran}
    prov = PROVENANCE_CENTRAL
    assert verified["s1_st"]["stages"][0]["dry_mass_t"]["source"] == prov
    assert "source" in verified["s1"]["stages"][0]["dry_mass_t"]
    assert verified["s1"]["stages"][0]["dry_mass_t"]["value"] == 22.2
    s = st_t.sizing_at(X_FAKE)
    dm_t = verified["s1_st"]["stages"][0]["dry_mass_t"]["value"]
    assert dm_t == pytest.approx(22.2 + s.dm_stage1_kg / 1000.0, rel=1e-15)
    rr = report.runs["s1_st"]
    assert rr.resolved.vehicle_dict["stages"][0]["dry_mass_t"]["source"] == prov
    assert by["s1_st"]["structure_dm_kg"] == s.total_kg
    assert by["s1_full"]["structure_dm_kg"] == by["s1_full"]["structure_dm_x0_kg"]
    assert by["s1_st"]["structure_dm_x0_kg"] == by["s1_full"]["structure_dm_kg"]


OVERRIDES = {"nof.nof_barrel": 1.54, "dynamics.rise_time_s": 0.1}
"""A case's design-axis overrides (inside the synthetic file's ranges)."""


def test_overrides_are_recorded_and_named_at_source(fake_pass: SimpleNamespace) -> None:
    """A case that overrides design-axis coefficients (D-SP7-43): its sizing differs from
    the central case's (here dm about doubles and the record's rise time is the override),
    and the overrides are on disk and named at source: the case record and the run's
    metrics carry ``structure_overrides`` (the central case {}), the provenance on the
    restated dry mass of the verification and the recorded run reads ``..., set central,
    overrides <path> <value>, ...`` (paths sorted), the assumption line names them, and
    the two cases never share a solve. Nothing else about the record changes
    (``structure_set`` stays the base set, which the overrides modify)."""
    cases = [ST_CASE, {**ST_CASE, "name": "s1_ov", "structure": {"overrides": OVERRIDES}}]
    _resolved, report = _pass(cases)
    assert [(n, t is not None) for n, t in fake_pass.solves] == [("s1_st", True), ("s1_ov", True)]
    by = {c["name"]: c for c in report.record["cases"]}
    assert by["s1_ov"]["structure_overrides"] == OVERRIDES
    assert by["s1_st"]["structure_overrides"] == {}
    assert tuple(by["s1_ov"])[-len(sim.STRUCTURE_RECORD_KEYS) :] == sim.STRUCTURE_RECORD_KEYS
    assert by["s1_ov"]["structure_set"] == by["s1_st"]["structure_set"] == "central"
    assert (by["s1_ov"]["structure_t_r_s"], by["s1_st"]["structure_t_r_s"]) == (0.1, 0.8)
    assert by["s1_ov"]["structure_dm_kg"] > 1.5 * by["s1_st"]["structure_dm_kg"]
    prov_ov = f"{PROVENANCE_CENTRAL}, overrides dynamics.rise_time_s 0.1, nof.nof_barrel 1.54"
    prov_st = PROVENANCE_CENTRAL
    verified = {name: vd for name, vd in fake_pass.ran}
    assert verified["s1_ov"]["stages"][0]["dry_mass_t"]["source"] == prov_ov
    assert verified["s1_st"]["stages"][0]["dry_mass_t"]["source"] == prov_st
    rr_ov, rr_st = report.runs["s1_ov"], report.runs["s1_st"]
    assert rr_ov.resolved.vehicle_dict["stages"][0]["dry_mass_t"]["source"] == prov_ov
    assert rr_ov.result.metrics["structure_overrides"] == OVERRIDES
    assert rr_st.result.metrics["structure_overrides"] == {}
    (line_ov,) = (a for a in rr_ov.result.assumptions if a.startswith("structure:"))
    (line_st,) = (a for a in rr_st.result.assumptions if a.startswith("structure:"))
    assert prov_ov in line_ov and "overrides" not in line_st and prov_st in line_st
    assert fake_pass.solves[0][1].settings.key != fake_pass.solves[1][1].settings.key
    json.dumps(results_io.json_safe(results_io.offload_record(report)))


def test_record_keys_assumptions_and_resolved_config_only_with_a_structure(
    fake_pass: SimpleNamespace,
) -> None:
    """The case record and the written run's metrics of a structural case end with
    STRUCTURE_RECORD_KEYS in order (the case record after every key it had before); the
    unstructured case and its run carry none of them and keep ``stage1_dry_mass_added_kg``
    0 and ``assumed_penalty`` False; the structural case also keeps those (the modelled
    mass is never a penalty, D-SP7-22). The structure assumption line is on the
    structural run only; resolved_config.yaml's ``structure`` key (path, sha256, content)
    comes last and only when a structural case was solved."""
    _resolved, report = _pass([PLAIN_CASE, ST_CASE])
    by = {c["name"]: c for c in report.record["cases"]}
    keys = list(by["s1_st"])
    n = len(sim.STRUCTURE_RECORD_KEYS)
    assert tuple(keys[-n:]) == sim.STRUCTURE_RECORD_KEYS
    assert keys[:-n] == list(by["s1"])
    assert not [k for k in by["s1"] if k.startswith("structure")]
    for name in ("s1", "s1_st"):
        assert by[name]["stage1_dry_mass_added_kg"] == 0.0
        assert by[name]["assumed_penalty"] is False
    plain, st = report.runs["s1"].result, report.runs["s1_st"].result
    assert tuple(list(st.metrics)[-n:]) == sim.STRUCTURE_RECORD_KEYS
    assert not [k for k in plain.metrics if k.startswith("structure")]
    record = results_io.offload_record(report)
    assert record["runs"]["s1_st"]["structure_charged"] is True
    assert "structure_charged" not in record["runs"]["s1"]
    json.dumps(results_io.json_safe(record))  # metrics.json can hold it
    text = summary.offload_section(record)  # the summary and the console still render
    assert "s1_st" in text and all(line.isascii() for line in cli.offload_lines(record))
    line = [a for a in st.assumptions if a.startswith("structure:")]
    assert len(line) == 1 and SYNTHETIC_NAME in line[0] and "set central" in line[0]
    assert "pad's own flight" in line[0]
    assert not [a for a in plain.assumptions if a.startswith("structure")]
    # the structural run's offload line is the variant: no line says every dry mass is
    # unchanged one line above the structure line (the unstructured run keeps SP1's)
    (offload_line,) = (a for a in st.assumptions if a.startswith("offload:"))
    assert offload_line == sim.OFFLOAD_STRUCTURE_ASSUMPTIONS[0]
    assert (
        "every dry mass is unchanged except for the modelled structural increment" in offload_line
    )
    assert not [a for a in st.assumptions if "every dry mass (tank structure included)" in a]
    assert st.assumptions.index(offload_line) < st.assumptions.index(line[0])
    assert plain.assumptions.count(sim.OFFLOAD_ASSUMPTIONS[0]) == 1
    assert not [a for a in plain.assumptions if a == sim.OFFLOAD_STRUCTURE_ASSUMPTIONS[0]]
    assert report.structure == {
        "file": SYNTHETIC_NAME,
        "sha256": hashlib.sha256(SYNTHETIC.read_bytes()).hexdigest(),
        "content": yaml.safe_load(SYNTHETIC.read_text(encoding="utf-8")),
    }
    pad = _fake_rr(_resolved.baseline, P_REF_FAKE)
    er = results_io.ExperimentResult(
        experiment_name="e",
        vehicle_name="v",
        baseline=pad,
        variants={},
        comparison={},
        git={},
        timestamp_utc="t",
        model=config.PLANAR_2D,
        offload=report,
    )
    cfg = results_io._resolved_config_dict(er)
    assert list(cfg)[-1] == "structure" and cfg["structure"]["file"] == SYNTHETIC_NAME
    _r2, plain_report = _pass([PLAIN_CASE], block={})
    assert plain_report.structure is None
    cfg2 = results_io._resolved_config_dict(dataclasses.replace(er, offload=plain_report))
    assert "structure" not in cfg2 and list(cfg2)[-1] == "offload_runs"
    skipped = results_io.planar_offload(_resolved, pad, {}, offload=False)
    assert skipped is not None and skipped.structure is None


def test_fired_structure_flags_reach_the_run_and_the_case_record(
    fake_pass: SimpleNamespace,
) -> None:
    """Every structure flag that fired (the release, upper-stack and payload-limit checks
    of ``size_increment`` and the cap flag) is promoted to the recorded run's ``flags``
    and so to the case record's ``flags``: one ASCII line per flag, its name then its
    numbers, in ``structure_flags`` order; an unfired flag adds no line;
    ``structure_flags`` keeps every flag with its numbers; the sweep column ``n_flags``
    counts the lines and summary.md's flags section lists them. On the synthetic pad the
    central case fires the release and payload-limit flags (the swing -4.42 g0 is below
    the payload's -2 g0), a ``dynamic: step`` case all three. Informational (D-SP7-19):
    the solve's status and the run's status are unchanged."""
    cases = [ST_CASE, {**ST_CASE, "name": "s1_step", "structure": {"dynamic": "step"}}]
    _resolved, report = _pass(cases)
    by = {c["name"]: c for c in report.record["cases"]}
    expected = {
        "s1_st": [structure.FLAG_RELEASE_UNLOAD, structure.FLAG_PAYLOAD_LIMIT],
        "s1_step": [
            structure.FLAG_RELEASE_UNLOAD,
            structure.FLAG_UPPER_STACK,
            structure.FLAG_PAYLOAD_LIMIT,
        ],
    }
    for name, fired in expected.items():
        rec, rr = by[name], report.runs[name]
        assert [f["name"] for f in rec["structure_flags"] if f["fired"]] == fired
        assert [f["name"] for f in rec["structure_flags"]] == [
            structure.FLAG_RELEASE_UNLOAD,
            structure.FLAG_UPPER_STACK,
            structure.FLAG_PAYLOAD_LIMIT,
            structure.FLAG_FIXED_POINT_CAP,
        ]
        assert rec["flags"] == rr.result.flags
        assert [line.split(":")[0] for line in rr.result.flags] == fired
        assert all(line.isascii() for line in rr.result.flags)
        assert results_io.offload_index_values(rec)["n_flags"] == len(fired)
        assert rec["status"] == "ok" and rr.result.status == "inserted"
        assert rr.result.metrics["structure_flags"] == rec["structure_flags"]
    lines = {line.split(":")[0]: line for line in report.runs["s1_step"].result.flags}
    assert "release swing -7 g0 against MECO's -5.2 g0" in lines[structure.FLAG_RELEASE_UNLOAD]
    assert "exceeds the pad envelope's" in lines[structure.FLAG_UPPER_STACK]
    assert "against the payload's axial limits -2 to 6 g0" in lines[structure.FLAG_PAYLOAD_LIMIT]
    flags_text = summary.flags_section(report.runs)
    assert all(line in flags_text for line in report.runs["s1_st"].result.flags)
    json.dumps(results_io.json_safe(results_io.offload_record(report)))


def test_a_failed_structural_solve_still_records_its_structure(
    fake_pass: SimpleNamespace,
) -> None:
    """A structural case whose solve ends search_failed writes no run, and its case record
    still carries every structure key: structure_charged, the settings, dm at x = 0 and
    the file, every value at x* None and no flag (an unsolved structural case never reads
    as an uncharged one)."""
    fake_pass.fail.add("s1_st")
    _resolved, report = _pass([ST_CASE])
    (rec,) = report.record["cases"]
    assert rec["status"] == "search_failed" and "s1_st" not in report.runs
    n = len(sim.STRUCTURE_RECORD_KEYS)
    assert tuple(list(rec)[-n:]) == sim.STRUCTURE_RECORD_KEYS
    assert rec["structure_charged"] is True and rec["structure_set"] == "central"
    assert rec["structure_overrides"] == {}
    assert rec["structure_dm_x0_kg"] > 0.0 and rec["structure_file"] == SYNTHETIC_NAME
    for key in ("structure_dm_kg", "structure_dlf", "structure_elements", "structure_iterations"):
        assert rec[key] is None, key
    assert rec["structure_flags"] == []
    record = results_io.offload_record(report)
    assert "s1_st" in summary.offload_section(record) and cli.offload_lines(record)


def test_arms_size_on_their_own_perturbed_pad(
    fake_pass: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A structural case named in sensitivity_of: each arm builds its transform against
    the pad its offload is solved at (a vehicle parameter's perturbed pad, a run
    parameter's unchanged one), every arm solve has a transform, and the arm's in-memory
    case record and recorded run (the ``_CaseOutcome`` of ``_offload_case``, spied here)
    carry the structure keys with that envelope pad. Neither reaches disk at this step: the
    arm record in offload.sensitivity[] (``_offload_arm_record``) carries no structure key
    until S3b's arm columns, and the arm's recorded run goes to ``OffloadReport.checked_runs``,
    whose metrics are not written."""
    outcomes: list[tuple[str, results_io._CaseOutcome]] = []
    real = results_io._offload_case

    def spy(case: Any, ctx: Any, **kwargs: Any) -> results_io._CaseOutcome:
        out = real(case, ctx, **kwargs)
        outcomes.append((case.start.name, out))
        return out

    monkeypatch.setattr(results_io, "_offload_case", spy)
    _resolved, report = _pass([ST_CASE], sensitivity_of=["s1_st"])
    expected = {
        f"s1_st__{DRY_PARAM}__+0.1": f"pad__{DRY_PARAM}__+0.1",
        f"s1_st__{DRY_PARAM}__-0.1": f"pad__{DRY_PARAM}__-0.1",
        f"s1_st__{EFF_PARAM}__+0.1": "pad",
        f"s1_st__{EFF_PARAM}__-0.1": "pad",
    }
    arm_pads = {start: pad for start, pad in fake_pass.pads if start != "s1_st"}
    assert arm_pads == expected
    assert all(t is not None for _name, t in fake_pass.solves)
    n = len(sim.STRUCTURE_RECORD_KEYS)
    arms = {start: out for start, out in outcomes if start != "s1_st"}
    assert set(arms) == set(expected) and len(outcomes) == 5
    for start, out in arms.items():
        assert tuple(list(out.record)[-n:]) == sim.STRUCTURE_RECORD_KEYS
        assert out.record["structure_envelope_pad"] == expected[start]
        (rr,) = out.written.values()
        assert rr.result.metrics["structure_envelope_pad"] == expected[start]
        assert tuple(list(rr.result.metrics)[-n:]) == sim.STRUCTURE_RECORD_KEYS
        assert report.checked_runs[f"{rr.name} (offload sensitivity)"] is rr
    recorded = report.record["sensitivity"]
    assert len(recorded) == 4
    assert not [k for arm in recorded for k in arm if k.startswith("structure")]  # S3b's columns


def test_a_written_run_without_a_structure_block_has_no_structure_key(
    repo_root: Path, planar_pins: Any, tmp_path: Path
) -> None:
    """The output capture's fixed-guidance fast experiment (no offload, no structure
    block), resolved with a structure loader and without one, writes the same
    metrics.json and summary.md apart from the timestamp and git (byte for byte after
    normalising them) and neither file nor resolved_config.yaml holds a key or line
    starting with "structure". Both runs are made by the current code, so the "before"
    side (the start commit's output) rests on other pins: the output capture of
    tests/test_planar_pipeline.py compares every key path of metrics.json in every
    environment and the normalised sha256 of summary.md in the capture environment
    (tests/planar_pin_support.py), and ``test_sp1s_resolved_and_solved_dicts_are_unchanged``
    pins the run and vehicle dicts to digests captured at the start commit; the values of
    metrics.json before versus after are not byte-pinned by any test."""
    fast = planar_pins.load_sibling("test_planar_pipeline")
    exp, veh = fast._raw(repo_root)
    exp = fast._fixed(exp, ("silo_cold",))
    exp.pop("sensitivity", None)
    texts = []
    for loader in (None, _load_structure):
        resolved = resolve_experiment(copy.deepcopy(exp), veh, load_structure=loader)
        assert resolved.structure is None
        _er, out = sim.run_experiment(resolved, tmp_path / str(len(texts)), plots=False)
        metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
        for key in ("timestamp_utc", "git"):
            metrics.pop(key)
        summary = planar_pins.gs.normalise_summary((out / "summary.md").read_text(encoding="utf-8"))
        cfg = yaml.safe_load((out / "resolved_config.yaml").read_text(encoding="utf-8"))
        assert "structure" not in cfg
        texts.append((json.dumps(metrics), summary))
    assert texts[0] == texts[1]
    assert '"structure' not in texts[0][0]
    assert not [line for line in texts[0][1].splitlines() if line.startswith("- structure")]


# --------------------------------------------------------------------- slow pins


CONSTANT_DM_KG = 2000.0
"""The constant stage-1 dm of the cross-check [kg]: SP1's silo_cold_s1_dry+2t penalty."""


def _constant_increment(real: Any) -> Any:
    """structure.size_increment with its stage-1 dm replaced by CONSTANT_DM_KG and its
    stage-2 dm by 0 (the test-only injection of the cross-check)."""

    def sized(*args: Any, **kwargs: Any) -> Any:
        return dataclasses.replace(
            real(*args, **kwargs), dm_stage1_kg=CONSTANT_DM_KG, dm_stage2_kg=0.0
        )

    return sized


@pytest.fixture(scope="module")
def sp1_pins() -> SimpleNamespace:
    """SP1's experiment with a reduced offload block: the pad and silo_cold flown once;
    pass 1 solves the structure-off headline silo_cold_s1 and a structural case on the
    synthetic file (central, flown) beside it; pass 2 the constant-2 t structural case
    (``structure.size_increment`` replaced by ``_constant_increment``). No sensitivity
    arms, no paired pad, no pad control (none moves x*)."""
    t0 = time.perf_counter()
    cases = [
        {"name": "silo_cold_s1", "of": "silo_cold", "solve": "stage1"},
        {"name": "silo_cold_s1_syn", "of": "silo_cold", "solve": "stage1", "structure": {}},
    ]
    exp, veh = _experiment(cases)
    resolved = _resolve(exp, veh)
    pad = sim.run_resolved(resolved.baseline)
    cold = sim.run_resolved(resolved.variants["silo_cold"])
    t1 = time.perf_counter()
    first = results_io.planar_offload(resolved, pad, {"silo_cold": cold}, sensitivity=False)
    t2 = time.perf_counter()
    exp2, _ = _experiment([{**cases[1], "name": "silo_cold_s1_st2t"}])
    resolved2 = _resolve(exp2, veh)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(structure, "size_increment", _constant_increment(structure.size_increment))
        second = results_io.planar_offload(resolved2, pad, {"silo_cold": cold}, sensitivity=False)
    t3 = time.perf_counter()
    assert first is not None and second is not None
    cases_out = {c["name"]: c for c in [*first.record["cases"], *second.record["cases"]]}
    return SimpleNamespace(
        pad=pad,
        first=first,
        second=second,
        cases=cases_out,
        seconds={"flights": t1 - t0, "pass_1": t2 - t1, "pass_2": t3 - t2},
    )


def _note(request: pytest.FixtureRequest, key: str, value: Any) -> None:
    """Record a measured number in the test's user_properties (nothing printed; a junit
    XML carries it), as tests/test_structure.py does."""
    request.node.user_properties.append((key, value))


def _gate_row(case: str) -> dict[str, Any]:
    return next(r for r in ss.sp1_record()["gate"]["stage1_offload_cases"] if r["case"] == case)


@pytest.mark.slow
def test_structure_off_headline_reproduces_sp1(
    sp1_pins: SimpleNamespace, request: pytest.FixtureRequest
) -> None:
    """With the structure off, silo_cold_s1 solved through ``planar_offload`` (the shipped
    budget, the pad's freshly flown P*) equals SP1's record: P_ref, x* and the
    verification's P* within 0.002 kg (design 6, criterion 3); its record carries no
    structure key and its decomposition no dry-mass change."""
    rec, row = sp1_pins.cases["silo_cold_s1"], _gate_row("silo_cold_s1")
    _note(request, "seconds", sp1_pins.seconds)
    _note(request, "x_star_minus_record_kg", rec["offload_kg"] - row["offload_kg"])
    _note(
        request,
        "verification_minus_record_kg",
        rec["verification"]["payload_kg"] - row["verification_payload_kg"],
    )
    p_ref = ss.sp1_record()["gate"]["reference_payload_kg"]
    assert sp1_pins.first.record["reference_payload_kg"] == pytest.approx(p_ref, abs=CROSS_CHECK_KG)
    assert rec["status"] == "ok"
    assert rec["offload_kg"] == pytest.approx(row["offload_kg"], abs=CROSS_CHECK_KG)
    ver = rec["verification"]
    assert ver["passed"] and ver["payload_kg"] == pytest.approx(
        row["verification_payload_kg"], abs=CROSS_CHECK_KG
    )
    assert not [k for k in rec if k.startswith("structure")]
    assert rec["decomposition"]["xv_dry_mass_delta_kg"] == 0.0


@pytest.mark.slow
def test_constant_2t_cross_check_equals_sp1s_penalty_row(
    sp1_pins: SimpleNamespace, request: pytest.FixtureRequest
) -> None:
    """A structural case whose sizing is replaced by a constant 2,000.0 kg on stage 1,
    solved through the whole pipeline (transform, solve, verification flying dm, recorded
    run), equals SP1's silo_cold_s1_dry+2t row: x* 32,285.203295407457 kg and the
    verification's P* within 0.002 kg of SP1's recorded values (D-SP7-42: SP1's own +2 t
    verification ended 0.00299 kg above P_ref, so the step's "P* equals P_ref within 0.002
    kg" is unattainable by the run it reproduces; P* is held to P_ref within the flag
    tolerance only); the verification passes within the flag tolerance; the recorded
    run's dict restates 24.2 t with the structure's provenance; the
    decomposition's dry-mass change and the record's dm are 2,000 kg; the iteration
    converges in two sizings (the constant reached, then a zero step)."""
    rec, row = sp1_pins.cases["silo_cold_s1_st2t"], _gate_row("silo_cold_s1_dry+2t")
    _note(request, "x_star_minus_record_kg", rec["offload_kg"] - row["offload_kg"])
    _note(
        request,
        "verification_minus_record_kg",
        rec["verification"]["payload_kg"] - row["verification_payload_kg"],
    )
    assert row["offload_kg"] == 32285.203295407457
    assert rec["status"] == "ok"
    assert rec["offload_kg"] == pytest.approx(row["offload_kg"], abs=CROSS_CHECK_KG)
    ver = rec["verification"]
    assert ver["passed"] and abs(ver["delta_kg"]) <= ver["tolerance_kg"]
    assert ver["payload_kg"] == pytest.approx(row["verification_payload_kg"], abs=CROSS_CHECK_KG)
    assert rec["structure_dm_kg"] == CONSTANT_DM_KG and rec["structure_iterations"] == 2
    assert rec["decomposition"]["xv_dry_mass_delta_kg"] == pytest.approx(
        CONSTANT_DM_KG, abs=XV_TOL_KG
    )
    rr = sp1_pins.second.runs["silo_cold_s1_st2t"]
    dry = rr.resolved.vehicle_dict["stages"][0]["dry_mass_t"]
    assert dry["value"] == 24.2 and dry["source"].startswith("first-order station sizing")
    assert rr.result.metrics["structure_dm_kg"] == CONSTANT_DM_KG


@pytest.mark.slow
def test_structural_solve_charges_dm_through_the_pipeline(
    sp1_pins: SimpleNamespace, request: pytest.FixtureRequest
) -> None:
    """A structural case on the synthetic file (central, flown; a test input, not a
    finding), solved beside the unstructured headline in one pass: its own solve (the
    memo keeps them apart), status ok, a smaller x* than the headline's, the verification
    passed, no offload_nonmonotone flag, the inner iteration within its cap;
    ``xv_dry_mass_delta_kg`` = dm1 + dm2 at x* within 1e-6 kg; the recorded run's metrics
    carry the same dm and resolved_config.yaml's structure key is the synthetic file."""
    rec, head = sp1_pins.cases["silo_cold_s1_syn"], sp1_pins.cases["silo_cold_s1"]
    xv = rec["decomposition"]["xv_dry_mass_delta_kg"]
    _note(request, "xv_minus_dm_kg", xv - rec["structure_dm_kg"])
    _note(request, "synthetic_x_star_kg_not_a_finding", rec["offload_kg"])
    assert rec["status"] == "ok" and 0.0 < rec["offload_kg"] < head["offload_kg"]
    assert rec["verification"]["passed"]
    assert not [f for f in rec["flags"] if offload.NONMONOTONE_FLAG in f]
    assert rec["structure_iterations"] <= sim.STRUCTURE_FIXED_POINT_MAX_ITERATIONS
    cap = next(f for f in rec["structure_flags"] if f["name"] == structure.FLAG_FIXED_POINT_CAP)
    assert cap["fired"] is False
    assert rec["decomposition"]["xv_dry_mass_delta_kg"] == pytest.approx(
        rec["structure_dm_kg"], abs=XV_TOL_KG
    )
    assert rec["decomposition"]["xv_status"] == "explained"
    run = sp1_pins.first.runs["silo_cold_s1_syn"].result
    assert run.metrics["structure_dm_kg"] == rec["structure_dm_kg"]
    assert sp1_pins.first.structure["file"] == SYNTHETIC_NAME
    p_star = sp1_pins.pad.result.metrics["payload_kg"]
    assert sp1_pins.first.record["reference_payload_kg"] == p_star
