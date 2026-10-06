"""The offload block, its pipeline and its reporting (SP1 step 7; docs/physics.md,
"Experiment schema (planar)", "Offload block", and "Reporting definitions (planar)",
"Propellant saved at fixed payload").

Fast:

- the block resolves on silo_screening_2d's gate fork: each case's start restates the
  vehicle masses it changes (the fixed offload, the stage-2 pre-offload, the assumed
  dry mass) against hand numbers from the vehicle file, paired-pad starts carry the
  propellant change without the penalty, the sensitivity arms perturb pad and assisted
  run alike for a vehicle parameter and the assisted run only for a run parameter, the
  pad-control modes are the distinct solve modes; ``offload_solved_run`` removes x*
  along a mode; ``OffloadFixedConfig.offload_kg`` against hand numbers;
- every schema refusal of the brief (unknown variant, reference not the baseline, solve
  and fixed together, two fixed keys, fractions out of (0, 1), an offload beyond the
  load, a fuel mass above the propellant, a case on the baseline) and the related ones,
  names that collide or exceed MAX_NAME_LEN, the preflight of the offload runs;
- the energy arithmetic against hand numbers, the unit factors, the figure items of an
  offload run, the verification and slope helpers, the KI-024 guard of
  ``compare._attribution_check`` (a NaN residual fails, whatever its position);
- the summary block on a synthetic record (every row, caveat and exclusion, tonnes and
  percent against hand numbers, no "|" inside a label), a bug_suspect decomposition
  blocking findings while no offload row enters the unexplained beats, a failing pad
  control in a blocked line of its own, the offload role of the replay on a synthetic
  results directory, the sweep columns (a fixed case's P* - P_ref among them), the CLI
  flags and console lines, and the metrics.json and resolved_config.yaml keys appearing
  only with the block;
- the pass itself on fake runs (the sim seams monkeypatched): each case's record against
  hand numbers (removed per stage, shares, the net value, the quoted offload, the
  penalty fields, the energy split at the vehicle file's mixture ratio, also on an arm
  and a sweep point whose load is below the fuel mass), the assumptions of every written
  run, the skipped arms and the reference_failed paths, the stage-1 pad control as a
  consistency test (its bound, verdict and its own blocked line), stage-2 cases quoted
  net, a failed case solve not quoted for its own reason (not the pad control's), the
  calibration caveat by vehicle, and the sweep columns following the offload flag;
- SP1 step 8a: the payload Sensitivity note of a block with an empty `of` (with and
  without offload arms, and with --no-offload); each sweep point's solve gamma*_ref and
  flag count in sweep_index.csv, with the flag lines in the sweep's Checks section (a
  failed solve's status said); the README-loads fork's calibration caveat; the stage-2
  caveat that no longer assumes a stage-1-only offload maximises the total tonnes.

Slow (a small searched grid on the gate fork, gamma* 18-28 deg): the experiment run in
memory writes nothing; the solved case, its verification, recorded run, decomposition
(the D_id change against c1 ln(m0/(m0 - x)) from the vehicle file), paired pad and
energy; the fixed case; the pad control; the sensitivity arms (an energy-only arm
reuses the solve and scales the electrical energy by the efficiency ratio); the written
outputs and the replay of the pad beside the offloaded run; --no-offload; a sweep that
names a case gets its columns, with the same x* as the experiment's solve at the same
inputs, and (SP1 step 8a) the same solve gamma*_ref, its flag count and its flag line.

Expected values are computed here from the vehicle file and closed forms. The fuel
masses and the heating value are test inputs (TEST_LHV_MJ_PER_KG is a test constant, not
a sourced value: SP1 step 8's experiment cites one).
"""

from __future__ import annotations

import contextlib
import copy
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest
import yaml

from launchsim import cli, compare, config, plots, replay, results_io, sim, summary, units
from launchsim.config import (
    ChecksConfig,
    OffloadFixedConfig,
    VehicleConfig,
    offload_run_names,
    offload_solved_run,
    resolve_experiment,
)
from launchsim.constants import G0_MPS2
from launchsim.metrics_planar import (
    OFFLOAD_FIGURE,
    OFFLOAD_METRIC_KEYS,
    SEARCH_METRIC_KEYS,
    offload_metrics,
)
from launchsim.offload import (
    FINAL_LOG,
    VERIFY_MISMATCH_FLAG,
    X2_LOG,
    OffloadEval,
    OffloadResult,
    residual_slope_kg_per_kg,
    verification_from_record,
    with_verification,
)
from launchsim.results_io import (
    MAX_NAME_LEN,
    OFFLOAD_SWEEP_COLUMNS,
    PLANAR_SWEEP_INDEX_METRICS,
    PLANAR_SWEEP_INDEX_TEXT,
    InvalidNameError,
    OffloadReport,
)
from launchsim.search import SEARCH_FAILED_STATUS
from launchsim.vehicle import offload_load_kg, with_offload

EXPERIMENT = Path("experiments") / "silo_screening_2d.yaml"
VEHICLE = Path("configs") / "vehicles" / "generic_f9_class_2d.yaml"
VEHICLE_1D = Path("configs") / "vehicles" / "generic_f9_class.yaml"
EXPERIMENT_1D = Path("experiments") / "silo_screening_1d.yaml"
TEST_LHV_MJ_PER_KG = 43.0
"""Heating value of the test energy block [MJ/kg]: a test input, not a sourced value."""
FUEL_T = {"stage1": 123.5, "stage2": 32.3}
"""Fuel (RP-1) per stage of the test energy block [t] (the gate file's source strings)."""
KG_PER_T = 1000.0
"""Hand conversion of the expected values [kg/t]."""
J_PER_MJ = 1.0e6
J_PER_KWH_HAND = 3.6e6
DRY_PARAM = "vehicle.stages.stage1.dry_mass_t"
EFF_PARAM = "assist.drive_efficiency"
LOAD_PARAM = "vehicle.stages.stage1.propellant_mass_t"
FRACTION = 0.1
GATE = "generic_f9_class_2d"
"""The gate vehicle's name (its calibration record: plots.CALIBRATION_RECORDS)."""
README_FORK = "generic_f9_class_2d_readme_loads"
"""The README-loads fork's name (its calibration record since SP1 step 8a)."""


# ------------------------------------------------------------------------ helpers


def _raw(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """silo_screening_2d.yaml and the gate fork as raw dicts."""
    exp = yaml.safe_load((repo_root / EXPERIMENT).read_text(encoding="utf-8"))
    veh = yaml.safe_load((repo_root / VEHICLE).read_text(encoding="utf-8"))
    return exp, veh


def _masses_t(veh: dict[str, Any]) -> dict[str, float]:
    """The gate fork's stage masses [t] from the vehicle file (m_p1, m_p2, m_d1)."""
    s1, s2 = veh["stages"]
    return {
        "m_p1": s1["propellant_mass_t"]["value"],
        "m_p2": s2["propellant_mass_t"]["value"],
        "m_d1": s1["dry_mass_t"]["value"],
    }


def _energy() -> dict[str, Any]:
    return {
        "fuel_mass_t": {s: {"value": v, "source": "test input"} for s, v in FUEL_T.items()},
        "heating_value_MJ_per_kg": {"value": TEST_LHV_MJ_PER_KG, "assumed": True, "note": "test"},
    }


def _block() -> dict[str, Any]:
    """The test offload block: a solved stage-1 case with a paired pad, a penalty row,
    a frontier point (stage-2 pre-offload), a stage-2 case, a fixed 10 % case with a
    paired pad; pad controls, sensitivity of s1 and the energy inputs."""
    return {
        "reference": "pad",
        "pad_control": True,
        "sensitivity_of": ["s1"],
        "cases": [
            {"name": "s1", "of": "silo_cold", "solve": "stage1", "paired_pad": True},
            {
                "name": "s1_pen2",
                "of": "silo_cold",
                "solve": "stage1",
                "stage1_dry_mass_added_t": 2.0,
            },
            {"name": "s1_s2", "of": "silo_cold", "solve": "stage1", "stage2_offload_t": 2.0},
            {"name": "s2", "of": "silo_cold", "solve": "stage2"},
            {
                "name": "f10",
                "of": "silo_cold",
                "fixed": {"stage1_fraction": 0.1},
                "paired_pad": True,
            },
        ],
        "energy": _energy(),
    }


def _experiment(repo_root: Path, block: dict[str, Any] | None = None) -> tuple[dict, dict]:
    """silo_screening_2d with silo_cold only, no sweeps or bounds, the sensitivity params
    of the arms (no sensitivity case of its own) and the offload block."""
    exp, veh = _raw(repo_root)
    exp["variants"] = {k: v for k, v in exp["variants"].items() if k == "silo_cold"}
    for key in ("sweeps", "bounds"):
        exp.pop(key, None)
    exp["sensitivity"] = {"of": [], "params": {DRY_PARAM: FRACTION, EFF_PARAM: FRACTION}}
    exp["offload"] = _block() if block is None else block
    return exp, veh


def _case(resolved: Any, name: str) -> Any:
    return next(c for c in resolved.offload.cases if c.name == name)


def _without_name(run_dict: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in run_dict.items() if k != "name"}


# ------------------------------------------------------------------- the schema


def test_offload_block_resolves_every_case_through_vehicle_overrides(repo_root: Path) -> None:
    """Each case's start is its variant (run dict unchanged, named after the case) with
    the vehicle masses it changes restated as assumed Quantities: f10's stage-1 load
    0.9 m_p1 and its imposed offload 0.1 m_p1 (liftoff mass down by it), s1_pen2's
    stage-1 dry mass m_d1 + 2 t, s1_s2's stage-2 load m_p2 - 2 t; s1 changes nothing;
    paired pads are the baseline's run with the propellant change and no penalty; the
    pad-control modes are the distinct solve modes; each sensitivity parameter gives a
    + and a - arm of s1, a vehicle parameter perturbing the pad by the same factor, a
    run parameter leaving it the baseline itself."""
    exp, veh = _experiment(repo_root)
    m = _masses_t(veh)
    resolved = resolve_experiment(exp, veh)
    ro = resolved.offload
    assert ro is not None and ro.pad_control_modes == ("stage1", "stage2")
    variant = resolved.variants["silo_cold"]
    for case in ro.cases:
        assert case.start.name == case.name
        assert _without_name(case.start.run_dict) == _without_name(variant.run_dict)
    s1 = _case(resolved, "s1")
    assert s1.start.vehicle_dict == variant.vehicle_dict and s1.imposed_kg is None
    assert s1.pad_start.name == "s1__pad"
    assert _without_name(s1.pad_start.run_dict) == _without_name(resolved.baseline.run_dict)
    pen = _case(resolved, "s1_pen2").start.vehicle_dict["stages"][0]["dry_mass_t"]
    assert pen["value"] == pytest.approx(m["m_d1"] + 2.0, abs=1e-12) and pen["assumed"]
    assert "assumed structural penalty" in pen["note"]
    s2 = _case(resolved, "s1_s2").start.vehicle_dict["stages"][1]["propellant_mass_t"]
    assert s2["value"] == pytest.approx(m["m_p2"] - 2.0, abs=1e-12) and s2["assumed"]
    f10 = _case(resolved, "f10")
    assert f10.imposed_kg == pytest.approx(0.1 * m["m_p1"] * KG_PER_T, rel=1e-15)
    for run in (f10.start, f10.pad_start):
        load = run.vehicle_dict["stages"][0]["propellant_mass_t"]
        assert load["value"] == pytest.approx(0.9 * m["m_p1"], rel=1e-14) and load["assumed"]
        assert run.vehicle_dict["stages"][0]["dry_mass_t"]["value"] == m["m_d1"]
    full = variant.to_vehicle().liftoff_mass_kg()
    assert f10.start.to_vehicle().liftoff_mass_kg() == pytest.approx(
        full - 0.1 * m["m_p1"] * KG_PER_T, abs=1e-6
    )
    assert _case(resolved, "s1_pen2").pad_start is None
    arms = [(a.param, a.fraction) for a in ro.arms]
    assert arms == [
        (DRY_PARAM, FRACTION),
        (DRY_PARAM, -FRACTION),
        (EFF_PARAM, FRACTION),
        (EFF_PARAM, -FRACTION),
    ]
    for arm in ro.arms:
        assert arm.case == "s1"
        sign = 1.0 if arm.fraction > 0 else -1.0
        dry = arm.start.vehicle_dict["stages"][0]["dry_mass_t"]["value"]
        eff = arm.start.run_dict["assist"]["drive_efficiency"]
        if arm.param == DRY_PARAM:
            assert arm.pad_perturbed and dry == pytest.approx(m["m_d1"] * (1 + sign * FRACTION))
            pad_dry = arm.pad.vehicle_dict["stages"][0]["dry_mass_t"]["value"]
            assert pad_dry == pytest.approx(m["m_d1"] * (1 + sign * FRACTION), rel=1e-15)
        else:
            assert not arm.pad_perturbed and arm.pad is resolved.baseline
            assert eff == pytest.approx(0.5 * (1 + sign * FRACTION), rel=1e-15)


def test_fixed_offload_masses_by_key(repo_root: Path) -> None:
    """OffloadFixedConfig.offload_kg on the gate fork against the vehicle file: a mass
    in t is that many kg x 1000, a fraction takes that share of its stage's load
    (both_fraction: of both loads together); each key's mode."""
    _exp, veh = _raw(repo_root)
    m = _masses_t(veh)
    vehicle = VehicleConfig.model_validate(veh).to_vehicle()
    cases = {
        "stage1_t": (41.09, 41.09 * KG_PER_T, "stage1"),
        "stage1_fraction": (0.1, 0.1 * m["m_p1"] * KG_PER_T, "stage1"),
        "stage2_t": (2.0, 2.0 * KG_PER_T, "stage2"),
        "stage2_fraction": (0.5, 0.5 * m["m_p2"] * KG_PER_T, "stage2"),
        "both_fraction": (0.1, 0.1 * (m["m_p1"] + m["m_p2"]) * KG_PER_T, "both"),
    }
    for key, (value, expected, mode) in cases.items():
        fixed = OffloadFixedConfig.model_validate({key: value})
        assert fixed.key == key and fixed.mode == mode
        assert fixed.offload_kg(vehicle) == pytest.approx(expected, rel=1e-15), key


def test_solved_offload_run_restates_the_load(repo_root: Path) -> None:
    """offload_solved_run of s1's start: stage-1 load (m_p1 x 1000 - x)/1000 t, assumed,
    the liftoff mass that of ``vehicle.with_offload`` (1e-6 kg); both splits x by the
    loads; x = 0 renames only."""
    exp, veh = _experiment(repo_root)
    m = _masses_t(veh)
    start = _case(resolve_experiment(exp, veh), "s1").start
    x = 41262.9
    run = offload_solved_run(start, "stage1", x, "s1", "s1_final")
    load = run.vehicle_dict["stages"][0]["propellant_mass_t"]
    assert run.name == "s1_final" and load["assumed"]
    assert load["value"] == pytest.approx((m["m_p1"] * KG_PER_T - x) / KG_PER_T, rel=1e-15)
    offloaded = with_offload(start.to_vehicle(), "stage1", x)
    assert run.to_vehicle().liftoff_mass_kg() == pytest.approx(
        offloaded.liftoff_mass_kg(), abs=1e-6
    )
    both = offload_solved_run(start, "both", x, "s1", "s1_both")
    share = x * m["m_p2"] / (m["m_p1"] + m["m_p2"])
    s2 = both.vehicle_dict["stages"][1]["propellant_mass_t"]["value"]
    assert s2 == pytest.approx((m["m_p2"] * KG_PER_T - share) / KG_PER_T, rel=1e-12)
    same = offload_solved_run(start, "stage1", 0.0, "s1", "s1_zero")
    assert same.vehicle_dict == start.vehicle_dict and same.name == "s1_zero"


def _set(path: str, value: Any) -> Any:
    """A mutation that sets a dotted path of the offload block (list items by index)."""

    def mutate(exp: dict[str, Any], veh: dict[str, Any]) -> None:
        node: Any = exp["offload"]
        keys = path.split(".")
        for key in keys[:-1]:
            node = node[int(key)] if isinstance(node, list) else node[key]
        last = keys[-1]
        if value is _DELETE:
            del node[last]
        elif isinstance(node, list):
            node[int(last)] = value
        else:
            node[last] = value

    return mutate


_DELETE = object()


def _no_block_sweep(exp: dict[str, Any], veh: dict[str, Any]) -> None:
    exp.pop("offload")
    exp["sweeps"] = [{"of": "silo_cold", "axes": {"assist.stroke_m": [100]}, "offload": ["s1"]}]


def _sweep_unknown(exp: dict[str, Any], veh: dict[str, Any]) -> None:
    exp["sweeps"] = [{"of": "silo_cold", "axes": {"assist.stroke_m": [100]}, "offload": ["nope"]}]


def _fixed_guidance(exp: dict[str, Any], veh: dict[str, Any]) -> None:
    exp["search"].update(
        {
            "figure_of_merit": "none",
            "fixed_gamma_star_deg": 20.0,
            "fixed_ltg_a": 0.75679,
            "fixed_ltg_b_per_s": 2.19338e-3,
        }
    )


def _no_sensitivity(exp: dict[str, Any], veh: dict[str, Any]) -> None:
    exp.pop("sensitivity")


def _fuel_above(exp: dict[str, Any], veh: dict[str, Any]) -> None:
    stage1 = exp["offload"]["energy"]["fuel_mass_t"]["stage1"]
    stage1["value"] = _masses_t(veh)["m_p1"] + 0.1


def _beyond_stage1(exp: dict[str, Any], veh: dict[str, Any]) -> None:
    exp["offload"]["cases"][4]["fixed"] = {"stage1_t": _masses_t(veh)["m_p1"]}


def _beyond_stage2(exp: dict[str, Any], veh: dict[str, Any]) -> None:
    exp["offload"]["cases"][2]["stage2_offload_t"] = _masses_t(veh)["m_p2"]


def _named_like_a_variant(exp: dict[str, Any], veh: dict[str, Any]) -> None:
    exp["offload"]["cases"][0]["name"] = "silo_cold"
    exp["offload"]["sensitivity_of"] = ["silo_cold"]


def _sweep_of_the_baseline(exp: dict[str, Any], veh: dict[str, Any]) -> None:
    exp["sweeps"] = [{"of": "pad", "axes": {"ignition.stage1.t_ign_s": [-1.5]}, "offload": ["s1"]}]


def _sweep_of_a_stage2_solve(exp: dict[str, Any], veh: dict[str, Any]) -> None:
    exp["sweeps"] = [{"of": "silo_cold", "axes": {"assist.stroke_m": [100]}, "offload": ["s2"]}]


def _both_solve_without_pad_control(exp: dict[str, Any], veh: dict[str, Any]) -> None:
    exp["offload"]["pad_control"] = False
    exp["offload"]["cases"] = [c for c in exp["offload"]["cases"] if c["name"] != "s2"]
    exp["offload"]["cases"].append({"name": "b", "of": "silo_cold", "solve": "both"})


REFUSALS = {
    "unknown variant": (_set("cases.0.of", "nope"), "no such variant"),
    "reference not the baseline": (_set("reference", "silo_cold"), "must be the baseline"),
    "solve and fixed": (_set("cases.0.fixed", {"stage1_t": 1.0}), "exactly one of solve"),
    "neither solve nor fixed": (_set("cases.0.solve", _DELETE), "exactly one of solve"),
    "two fixed keys": (
        _set("cases.4.fixed", {"stage1_fraction": 0.1, "stage1_t": 1.0}),
        "exactly one of stage1_t",
    ),
    "fixed null": (_set("cases.4.fixed", {"stage1_t": None}), "is null"),
    "fraction 1": (_set("cases.4.fixed", {"stage1_fraction": 1.0}), "less than 1"),
    "fraction 0": (_set("cases.4.fixed", {"stage2_fraction": 0.0}), "greater than 0"),
    "fraction negative": (_set("cases.4.fixed", {"both_fraction": -0.1}), "greater than 0"),
    "both fraction above 1": (_set("cases.4.fixed", {"both_fraction": 1.5}), "less than 1"),
    "offload beyond the stage-1 load": (_beyond_stage1, "offload beyond the load"),
    "stage-2 pre-offload beyond its load": (_beyond_stage2, "offload beyond the load"),
    "stage-2 pre-offload on a stage-2 case": (
        _set("cases.3.stage2_offload_t", 1.0),
        "stage-1 case only",
    ),
    "paired pad on a penalty row": (_set("cases.1.paired_pad", True), "without paired_pad"),
    "dry mass penalty not positive": (
        _set("cases.1.stage1_dry_mass_added_t", 0.0),
        "greater than 0",
    ),
    "fuel mass above the propellant": (_fuel_above, "more than the stage's propellant"),
    "fuel of a stage missing": (_set("energy.fuel_mass_t.stage2", _DELETE), "needs every stage"),
    "fuel of an unknown stage": (
        _set("energy.fuel_mass_t.stage3", {"value": 1.0, "source": "x"}),
        "names no stage",
    ),
    "fuel not positive": (
        _set("energy.fuel_mass_t.stage1", {"value": 0.0, "source": "x"}),
        "must be > 0",
    ),
    "fuel without provenance": (_set("energy.fuel_mass_t.stage1", {"value": 1.0}), "source"),
    "heating value not positive": (
        _set("energy.heating_value_MJ_per_kg", {"value": -1.0, "assumed": True}),
        "must be > 0",
    ),
    "a case on the baseline": (_set("cases.0.of", "pad"), "is the baseline"),
    "case names twice": (_set("cases.1.name", "s1"), "used twice"),
    "a case named like a variant": (_named_like_a_variant, "used twice"),
    "sensitivity_of names no case": (_set("sensitivity_of", ["nope"]), "names no case"),
    "sensitivity_of names a case twice": (_set("sensitivity_of", ["s1", "s1"]), "twice"),
    "sensitivity_of without the sensitivity block": (_no_sensitivity, "sensitivity block"),
    "fixed guidance": (_fixed_guidance, "figure_of_merit payload"),
    "unknown key": (_set("extra", 1), "Extra inputs"),
    "no case": (_set("cases", []), "at least 1"),
    "sweep names no case": (_sweep_unknown, "names no case"),
    "sweep offload without a block": (_no_block_sweep, "does not declare"),
    "sweep of the baseline names cases": (_sweep_of_the_baseline, "is the baseline"),
    "sweep names a stage-2 solve": (_sweep_of_a_stage2_solve, "stage-1 solves and fixed"),
    "stage-2 solve without pad control": (_set("pad_control", False), "needs pad_control"),
    "both solve without pad control": (_both_solve_without_pad_control, "needs pad_control"),
    "stage-2 solve in sensitivity_of": (
        _set("sensitivity_of", ["s1", "s2"]),
        "an arm does not solve",
    ),
}


@pytest.mark.parametrize("label", list(REFUSALS))
def test_offload_schema_refusals(repo_root: Path, label: str) -> None:
    """Each malformed block is refused at resolve time with the reason named (a
    ValueError: pydantic's ValidationError, or the vehicle checks of resolve)."""
    mutate, match = REFUSALS[label]
    exp, veh = _experiment(repo_root)
    mutate(exp, veh)
    with pytest.raises(ValueError, match=match):
        resolve_experiment(exp, veh)


def test_offload_is_planar_only(repo_root: Path) -> None:
    """A vertical_1d experiment with an offload block is refused (a planar_2d block)."""
    exp = yaml.safe_load((repo_root / EXPERIMENT_1D).read_text(encoding="utf-8"))
    veh = yaml.safe_load((repo_root / VEHICLE_1D).read_text(encoding="utf-8"))
    exp["offload"] = {
        "reference": "pad",
        "cases": [{"name": "s1", "of": "silo_cold", "solve": "stage1"}],
    }
    with pytest.raises(ValueError, match="a planar_2d block"):
        resolve_experiment(exp, veh)


def test_offload_run_names_are_checked(repo_root: Path, tmp_path: Path) -> None:
    """The names an offload block writes (cases, paired pads, pad controls) in order;
    a case name whose paired pad ``<case>__pad`` exceeds MAX_NAME_LEN, or a case name
    itself too long, is refused by ``check_result_names`` and by the CLI before
    anything is written."""
    exp, veh = _experiment(repo_root)
    resolved = resolve_experiment(exp, veh)
    assert offload_run_names(resolved.offload.config, "pad") == [
        "s1",
        "s1__pad",
        "s1_pen2",
        "s1_s2",
        "s2",
        "f10",
        "f10__pad",
        "pad__offload_stage1",
        "pad__offload_stage2",
    ]
    results_io.check_result_names(resolved)
    long_name = "c" * (MAX_NAME_LEN - len("__pad") + 1)
    exp["offload"]["cases"][0]["name"] = long_name
    exp["offload"]["sensitivity_of"] = [long_name]
    long_resolved = resolve_experiment(exp, veh)
    with pytest.raises(InvalidNameError, match="longer than"):
        results_io.check_result_names(long_resolved)
    exp["offload"]["cases"][0]["paired_pad"] = False
    exp["offload"]["cases"][0]["name"] = "d" * (MAX_NAME_LEN + 1)
    exp["offload"]["sensitivity_of"] = []
    with pytest.raises(InvalidNameError, match="longer than"):
        results_io.check_result_names(resolve_experiment(exp, veh))
    exp["offload"]["cases"][0]["name"] = long_name
    exp["offload"]["cases"][0]["paired_pad"] = True
    exp["vehicle"] = str(repo_root / VEHICLE)
    path = tmp_path / "offload_long.yaml"
    path.write_text(yaml.safe_dump(exp), encoding="utf-8")
    with pytest.raises(cli.CliError, match="longer than"):
        cli.load_experiment(path)


def test_offload_runs_are_preflighted(repo_root: Path) -> None:
    """``sim.every_resolved_run`` lists every offload start (cases, paired pads,
    sensitivity runs and their perturbed pads, a sweep point's cases), so the preflight
    builds their specs before a results directory exists."""
    exp, veh = _experiment(repo_root)
    exp["sweeps"] = [{"of": "silo_cold", "axes": {"assist.stroke_m": [100]}, "offload": ["s1"]}]
    resolved = resolve_experiment(exp, veh)
    labels = [label for label, _run in sim.every_resolved_run(resolved)]
    for label in (
        "offload case 's1'",
        "offload case 's1' paired pad",
        "offload case 'f10' paired pad",
        f"offload sensitivity run 's1__{DRY_PARAM}__+0.1'",
        f"offload sensitivity run 'pad__{DRY_PARAM}__-0.1'",
        f"offload sensitivity run 's1__{EFF_PARAM}__+0.1'",
        "sweep 1 point run_0001 offload 's1'",
    ):
        assert label in labels, label
    assert f"offload sensitivity run 'pad__{EFF_PARAM}__+0.1'" not in labels
    point_case = resolved.sweeps[0][0].offload[0]
    assert point_case.start.name == "run_0001__s1" and point_case.variant.name == "run_0001"
    sim.check_resolved(resolved)


# ----------------------------------------------------------------- arithmetic


def test_offload_energy_against_hand_numbers() -> None:
    """A 10 % stage-1 offload of the gate fork's 410.9 t (123.5 t RP-1) removes 12,350 kg
    of RP-1 and 28,740 kg of LOX (41,090 kg x 123.5/410.9 is exact); with 2 t from stage
    2 (32.3/107.5 RP-1) the RP-1 adds 2000 x 32.3/107.5 kg; heat = RP-1 x LHV, kWh at
    3.6e6 J, the ratio heat / electricity; no positive electricity gives no ratio."""
    loads = [410.9 * KG_PER_T, 107.5 * KG_PER_T]
    fuel = [123.5 * KG_PER_T, 32.3 * KG_PER_T]
    lhv = TEST_LHV_MJ_PER_KG * J_PER_MJ
    one = compare.offload_energy([41090.0, 0.0], loads, fuel, lhv, 4.0e9)
    assert one["fuel_removed_kg"] == pytest.approx(12350.0, rel=1e-15)
    assert one["oxidizer_removed_kg"] == pytest.approx(28740.0, rel=1e-15)
    assert one["heat_J"] == pytest.approx(12350.0 * 43.0e6, rel=1e-15)
    assert one["heat_kWh"] == pytest.approx(12350.0 * 43.0e6 / J_PER_KWH_HAND, rel=1e-15)
    assert one["electrical_energy_kWh"] == pytest.approx(4.0e9 / J_PER_KWH_HAND, rel=1e-15)
    assert one["heat_to_electricity_ratio"] == pytest.approx(12350.0 * 43.0e6 / 4.0e9, rel=1e-15)
    assert one["ratio_label"] == "not an efficiency claim"
    assert one["excludes"] == list(compare.OFFLOAD_ENERGY_EXCLUSIONS)
    two = compare.offload_energy([41090.0, 2000.0], loads, fuel, lhv, None)
    rp1 = 12350.0 + 2000.0 * 32.3 / 107.5
    assert two["fuel_removed_kg"] == pytest.approx(rp1, rel=1e-14)
    assert two["oxidizer_removed_kg"] == pytest.approx(43090.0 - rp1, rel=1e-14)
    assert two["fuel_fraction_per_stage"] == pytest.approx([123.5 / 410.9, 32.3 / 107.5])
    assert two["heat_to_electricity_ratio"] is None and two["electrical_energy_J"] is None
    for elec in (0.0, math.nan):
        out = compare.offload_energy([41090.0, 0.0], loads, fuel, lhv, elec)
        assert out["heat_to_electricity_ratio"] is None
    # propellant from a vehicle with a larger load (a sweep point, an arm) keeps the
    # energy block's mixture ratio
    big = compare.offload_energy([500e3, 0.0], loads, fuel, lhv, None)
    assert big["fuel_removed_kg"] == pytest.approx(500e3 * 123.5 / 410.9, rel=1e-15)
    bad = (([1.0, 0.0], [500e3, 32.3e3]), ([-1.0, 0.0], fuel), ([math.nan, 0.0], fuel))
    for removed, f in bad:
        with pytest.raises(ValueError, match="offload energy"):
            compare.offload_energy(removed, loads, f, lhv, 1.0)
    with pytest.raises(ValueError, match="one removed mass"):
        compare.offload_energy([1.0], loads, fuel, lhv, 1.0)


def test_unit_factors_of_the_energy_comparison() -> None:
    """MJ = 1e6 J (and MJ/kg = 1e6 J/kg), percent = 100 x fraction; round trips."""
    assert units.mj_to_j(1.0) == 1.0e6 and units.j_to_mj(2.5e6) == 2.5
    assert units.mj_to_j(units.j_to_mj(123.456)) == pytest.approx(123.456, rel=1e-15)
    assert units.to_percent(0.25) == 25.0 and units.to_percent(0.1234) == pytest.approx(12.34)


def _fake_offload(**update: Any) -> SimpleNamespace:
    """A stand-in for an OffloadResult with the fields offload_metrics reads."""
    at = SimpleNamespace(delta_rad=0.05, ltg=(0.7, 2e-3), rung="warm")
    fields: dict[str, Any] = {
        "at_offload": at,
        "recorded": SimpleNamespace(
            m_res_kg=0.03, dv_margin_mps=0.004, figures_from="recorded_run"
        ),
        "inner_gamma": SimpleNamespace(gamma_best_grid_rad=0.4),
        "m_res_kg": 0.03,
        "dv_margin_mps": 0.004,
        "dv_shortfall_mps": math.nan,
        "gamma_star_rad": 0.401,
        "status": "ok",
        "failure_kind": None,
        "failure_message": None,
        "mode": "stage1",
        "offload_kg": 41262.9,
        "reference_payload_kg": 26054.4,
    }
    fields.update(update)
    return SimpleNamespace(**fields)


def test_offload_metrics_items() -> None:
    """The figure items of an offload's recorded run: SEARCH_METRIC_KEYS then
    OFFLOAD_METRIC_KEYS, payload_kg = P_ref (the payload flown), payload_excess = P0 -
    P_ref, figure_of_merit ``offload``, the payload-term search diagnostics and the
    search record None, NaN as None."""
    items = offload_metrics(_fake_offload(), 26000.0)  # type: ignore[arg-type]
    assert list(items) == [*SEARCH_METRIC_KEYS, *OFFLOAD_METRIC_KEYS]
    assert items["figure_of_merit"] == OFFLOAD_FIGURE == "offload"
    assert items["payload_kg"] == 26054.4 and items["offload_reference_payload_kg"] == 26054.4
    assert items["payload_excess_kg"] == pytest.approx(26000.0 - 26054.4, abs=1e-12)
    assert items["offload_kg"] == 41262.9 and items["offload_mode"] == "stage1"
    assert items["residual_propellant_kg"] == 0.03 and not items["residual_propellant_virtual"]
    assert items["dv_shortfall_mps"] is None and items["search_record"] is None
    for key in ("gamma_grid_payload_kg", "gamma_refine_payload_kg", "p2_minus_p1_kg"):
        assert items[key] is None
    assert (items["ltg_a"], items["ltg_b_per_s"], items["delta_rad"]) == (0.7, 2e-3, 0.05)


def _offload_result(status: str = "ok", evals: tuple[OffloadEval, ...] = ()) -> OffloadResult:
    """A minimal OffloadResult (no trajectory) for the helper tests."""
    return OffloadResult(
        mode="stage1",
        reference_payload_kg=26054.4,
        load_kg=410900.0,
        status=status,
        offload_kg=41262.9 if status == "ok" else 0.0,
        root_kg=41262.92,
        gamma_star_rad=0.4,
        m_res_kg=0.03,
        dv_margin_mps=0.004,
        dv_shortfall_mps=math.nan,
        at_offload=None,
        recorded=None,
        offloaded_vehicle=None,
        evaluations=evals,
        n_evaluations=len(evals),
        grid=(),
        verification=None,
        flags=("offload: inner",),
    )


def test_verification_and_slope_helpers() -> None:
    """verification_from_record: passed when ok and |P* - P_ref| <= rel x P_ref;
    with_verification attaches it, appends the mismatch flag when it failed and the
    search's own flags prefixed, and refuses a solve that is not ok; the residual slope
    is the secant of the final search's bracket, else X2's, else None."""
    p_ref, rel = 26054.4, 1e-4
    good = verification_from_record(
        SimpleNamespace(status="ok", payload_kg=p_ref + 0.5, flags=("v1",)),
        p_ref,
        rel,  # type: ignore[arg-type]
    )
    assert good.passed and good.delta_kg == pytest.approx(0.5, abs=1e-9)
    assert good.tolerance_kg == pytest.approx(rel * p_ref, rel=1e-15)
    bad = verification_from_record(
        SimpleNamespace(status="ok", payload_kg=p_ref + 5.0, flags=()),
        p_ref,
        rel,  # type: ignore[arg-type]
    )
    assert not bad.passed
    res = with_verification(_offload_result(), good)
    assert res.verification is good and res.flags == ("offload: inner", "offload: verification: v1")
    res = with_verification(_offload_result(), bad)
    assert any(VERIFY_MISMATCH_FLAG in f for f in res.flags)
    with pytest.raises(ValueError, match="only an ok"):
        with_verification(_offload_result("no_offload"), good)
    final = (
        OffloadEval(FINAL_LOG, 0.0, 0.03, 0.0, None),
        OffloadEval(FINAL_LOG, 20.0, -0.6, 0.0, None),
        OffloadEval(FINAL_LOG, 40.0, -1.3, 0.0, None),
    )
    assert residual_slope_kg_per_kg(_offload_result(evals=final)) == pytest.approx(0.63 / 20.0)
    x2 = (
        OffloadEval(FINAL_LOG, 0.0, -0.01, 0.0, None),
        OffloadEval(X2_LOG, 0.0, 0.2, 0.0, None),
        OffloadEval(X2_LOG, 10.0, -0.1, 0.0, None),
    )
    assert residual_slope_kg_per_kg(_offload_result(evals=x2)) == pytest.approx(0.3 / 10.0)
    assert residual_slope_kg_per_kg(_offload_result(evals=final[1:])) is None


def test_attribution_check_fails_a_nan_residual_anywhere() -> None:
    """KI-024: a NaN residual fails the attribution check in every position of its
    tuple (it used to be skipped when not first), with the worst value of its group
    NaN; finite residuals below the tolerances pass with the worst magnitude as
    before."""
    checks = ChecksConfig()
    keys = (
        "attr_residual_mps",
        "attr_variant_closure_residual_mps",
        "attr_baseline_closure_residual_mps",
        "attr_variant_identity_residual_mps",
        "attr_baseline_identity_residual_mps",
    )
    finite = dict.fromkeys(keys, 1e-9) | {"attr_baseline_closure_residual_mps": -3e-9}
    ok = compare._attribution_check(finite, None, True, checks)
    assert ok["status"] == "pass" and ok["worst_closure_mps"] == 3e-9
    for key in keys:
        rec = compare._attribution_check({**finite, key: math.nan}, None, True, checks)
        assert rec["status"] == "fail", key
        group = "worst_identity_mps" if "identity" in key else "worst_closure_mps"
        assert math.isnan(rec[group]), key


# -------------------------------------------------------------------- reporting


def _xv(status: str = "explained") -> dict[str, Any]:
    """A decomposition record with every CROSS_VEHICLE_TERMS term."""
    out: dict[str, Any] = {f"xv_{t}_mps": 1.0 for t in compare.CROSS_VEHICLE_TERMS}
    out.update({f"xv_{t}_kg": 100.0 for t in compare.CROSS_VEHICLE_TERMS})
    out.update(
        {
            "xv_gravity_steering_mps": 2.0,
            "xv_gravity_steering_kg": 200.0,
            "xv_ideal_dv_reduction_mps": 228.2,
            "xv_offload_kg": 41262.9,
            "xv_residual_mps": -4.1e-12,
            "xv_status": status,
        }
    )
    return out


def _synthetic_record(status: str = "explained") -> dict[str, Any]:
    """A plain offload record as planar_offload builds it: a solved stage-1 case with a
    paired pad and energy, a fixed case, a stage-1 pad control ending no_offload by
    grams, two sensitivity arms."""
    energy = compare.offload_energy(
        [41262.9, 0.0], [410900.0, 107500.0], [123500.0, 32300.0], 43.0e6, 4.16e9
    )
    s1 = {
        "name": "s1",
        "of": "silo_cold",
        "kind": "solve",
        "mode": "stage1",
        "fixed_key": None,
        "fixed_fraction": None,
        "run": "s1",
        "status": "ok",
        "run_status": "inserted",
        "reference_payload_kg": 26054.4,
        "quoted_offload_kg": 41262.9,
        "quoted_basis": results_io.OFFLOAD_QUOTED_HEADLINE,
        "offload_kg": 41262.9,
        "stage2_preoffload_kg": 0.0,
        "stage1_dry_mass_added_kg": 0.0,
        "stage1_offload_kg": 41262.9,
        "stage2_offload_kg": 0.0,
        "total_offload_kg": 41262.9,
        "stage1_fraction": 41262.9 / 410900.0,
        "stage2_fraction": 0.0,
        "total_fraction": 41262.9 / 518400.0,
        "payload_kg": 26054.4,
        "payload_delta_kg": 0.0,
        "verification": {
            "payload_kg": 26054.41,
            "delta_kg": 0.01,
            "tolerance_kg": 2.6,
            "passed": True,
        },
        "pad_control_offload_kg": 0.0,
        "net_offload_kg": 41262.9,
        "vs_pad": {"max_q_pa": 38591.0, "pad_max_q_pa": 37337.7, "max_q_above_pad": True},
        "decomposition": _xv(status),
        "decomposition_status": status,
        "screening_offload_kg": 14976.6,
        "screening_ratio": 2.755,
        "beats_screening": True,
        "paired_pad": {
            "run": "s1__pad",
            "payload_kg": 24652.3,
            "payload_delta_vs_reference_kg": -1402.1,
            "payload_delta_kg": 1398.4,
            "screening_status": "ok",
            "comparison": {"screening_status": "ok"},
        },
        "energy": energy,
        "flags": ["offload: a flag"],
    }
    f10 = {
        **s1,
        "name": "f10",
        "kind": "fixed",
        "fixed_key": "stage1_fraction",
        "fixed_fraction": 0.1,
        "run": "f10",
        "quoted_offload_kg": 41090.0,
        "quoted_basis": results_io.OFFLOAD_QUOTED_FIXED,
        "offload_kg": 41090.0,
        "stage1_offload_kg": 41090.0,
        "total_offload_kg": 41090.0,
        "verification": None,
        "pad_control_offload_kg": None,
        "net_offload_kg": None,
        "decomposition": _xv(),
        "decomposition_status": "explained",
        "paired_pad": None,
    }
    control = {
        "mode": "stage1",
        "run": "pad__offload_stage1",
        "status": "no_offload",
        "offload_kg": 0.0,
        "m_res_kg": -0.0016,
        "slope_kg_per_kg": 0.0307,
        "bound_kg": 1.63,
        "within_bound": None,
        "resolution_effect": True,
        "consistency": compare.CHECK_PASS,
        "verification": None,
    }
    arm = {
        "case": "s1",
        "run": f"s1__{DRY_PARAM}__+0.1",
        "param": DRY_PARAM,
        "fraction": 0.1,
        "pad_perturbed": True,
        "reference_payload_kg": 25660.1,
        "status": "ok",
        "offload_kg": 41418.9,
        "offload_delta_kg": 156.0,
        "stage1_fraction": 41418.9 / 410900.0,
        "decomposition_status": "explained",
        "decomposition_residual_mps": 1e-12,
        "screening_ratio": 2.76,
        "trajectory_reused": False,
    }
    return {
        "basis": compare.OFFLOAD_COMPARISON_BASIS,
        "reference": "pad",
        "reference_payload_kg": 26054.4,
        "caveats": summary.offload_caveats(GATE, plots.CALIBRATION_RECORDS[GATE]),
        "energy_inputs": {"heating_value_J_per_kg": 43.0e6},
        "pad_controls": [control],
        "cases": [s1, f10, {"name": "x", "of": "silo_hot", "skipped": results_io.OFFLOAD_NOT_RUN}],
        "sensitivity_basis": compare.OFFLOAD_SENSITIVITY_BASIS,
        "sensitivity": [arm, {**arm, "run": "arm2", "fraction": -0.1, "trajectory_reused": True}],
        "notes": ["a note"],
    }


def _table_rows(text: str) -> list[list[str]]:
    """The rows of every markdown table in text, as cell lists."""
    return [line.split("|")[1:-1] for line in text.splitlines() if line.startswith("|")]


def test_offload_section_renders_every_row_and_caveat() -> None:
    """The summary block of a synthetic record: the basis with P_ref, the sensitivity
    basis, every caveat (the record's: the calibration caveat, then OFFLOAD_CAVEATS),
    every case and energy row (tonnes = kg / 1000, percent = 100 x fraction; the quoted
    offload leading the gross rows), the energy note with "not an efficiency claim" and
    every exclusion, the decomposition table (every term, the residual unrounded), the
    pad control's resolution effect and consistency verdict (no bound text: the bound
    judges an ok control only), the arms, a case that did not run, the notes; every
    table row has its table's cell count (no "|" inside a label); without energy inputs
    no energy row; a skipped block prints only why."""
    record = _synthetic_record()
    text = summary.offload_section(record)
    assert text.startswith(compare.OFFLOAD_COMPARISON_BASIS)
    assert "Reference payload P_ref = 26054.4 kg" in text
    assert compare.OFFLOAD_SENSITIVITY_BASIS in text
    for caveat in record["caveats"]:
        assert f"- {caveat}" in text
    for caveat in summary.OFFLOAD_CAVEATS:
        assert caveat in record["caveats"]
    for label, _fmt, _key in (*summary.OFFLOAD_CASE_ROWS, *summary.OFFLOAD_ENERGY_ROWS):
        assert f"| {label} |" in text, label
    t1, t10 = f"{41262.9 / 1000:.6g}", f"{41090 / 1000:.6g}"
    assert f"| stage-1 propellant removed, gross [t] | {t1} | {t10} |" in text
    assert f"| quoted offload [t] | {t1} | {t10} |" in text
    assert f"|   % of the stage-1 load | {100 * 41262.9 / 410900:.6g} |" in text
    assert "| kind | solved, stage1 | fixed, stage1_fraction = 0.1 |" in text
    assert "not an efficiency claim" in text
    for item in compare.OFFLOAD_ENERGY_EXCLUSIONS:
        assert item in text
    for term in compare.CROSS_VEHICLE_TERMS:
        assert f"| {term.replace('_', ' ')} | +1 (+100) | +1 (+100) |" in text
    assert "| residual [m/s] | -4.1e-12 | -4.1e-12 |" in text
    control = "x_pad = 0, m_res(0) = -0.0016 kg: " + summary.RESOLUTION_EFFECT_TEXT
    assert f"{control}; consistency test pass" in text
    assert "the bound 0 to" not in text  # the bound judges an ok control only
    assert f"| s1 | {DRY_PARAM} | +10% | yes | 25660.1 | ok | 41.4189 |" in text
    assert f"- x (of silo_hot): {results_io.OFFLOAD_NOT_RUN}" in text
    assert text.rstrip().endswith("a note")
    tables = text.split("\n\n")
    for block in tables:
        rows = _table_rows(block)
        if rows:
            assert len({len(r) for r in rows}) == 1, block.splitlines()[0]
    no_energy = summary.offload_section({**record, "energy_inputs": None})
    assert "RP-1 removed" not in no_energy and "not an efficiency claim" not in no_energy
    skipped = {"basis": "b", "skipped": results_io.OFFLOAD_SKIPPED}
    assert summary.offload_section(skipped) == results_io.OFFLOAD_SKIPPED


def _fake_run(name: str, status: str = "inserted", **metrics: Any) -> SimpleNamespace:
    result = SimpleNamespace(metrics={"run_checks": "ok", **metrics}, status=status, flags=[])
    return SimpleNamespace(name=name, result=result)


def _fake_er(record: dict[str, Any], comparison: dict[str, Any]) -> SimpleNamespace:
    pad, silo = _fake_run("pad"), _fake_run("silo_cold", speed_at_release_mps=76.7)
    report = OffloadReport(record, runs={"s1": _fake_run("s1")}, checked_runs={})
    return SimpleNamespace(
        runs={"pad": pad, "silo_cold": silo},
        variants={"silo_cold": silo},
        cases={},
        sensitivity=[],
        bounds=[],
        comparison={"silo_cold": comparison},
        offload=report,
    )


def test_bug_suspect_decomposition_blocks_findings_and_no_offload_beat_is_unexplained() -> None:
    """In the Checks section the offload runs get their per-run lines and every case and
    arm its decomposition line; a bug_suspect decomposition (and a bug_suspect
    paired-pad comparison) enters the blocked-findings line, an explained one does not;
    the unexplained-beats list holds the not_checked variant that beats its yardstick,
    never an offload row, although every case beats the screening estimate. A failing
    stage-1 pad control gets a blocked line of its own (PAD_CONTROL_BLOCKED), is never
    labelled a comparison, and the Checks heading states the pad-control clause."""
    beating = {"screening_status": "not_checked", "beats_screening": True}
    record = _synthetic_record("bug_suspect")
    record["cases"][0]["paired_pad"]["comparison"] = {"screening_status": "bug_suspect"}
    text = summary.planar_checks_section(_fake_er(record, beating))  # type: ignore[arg-type]
    assert "- s1: closure residual" in text
    assert "- s1: decomposition bug_suspect (residual" in text
    assert f"- s1__{DRY_PARAM}__+0.1: decomposition explained" in text
    blocked = next(ln for ln in text.splitlines() if ln.startswith(summary.FINDINGS_BLOCKED))
    assert "s1 offload decomposition (comparison)" in blocked
    assert "s1 vs s1__pad (comparison)" in blocked
    assert "f10 offload decomposition" not in blocked
    unexplained = next(
        ln for ln in text.splitlines() if ln.startswith(summary.UNEXPLAINED_BEAT_TEXT)
    )
    assert unexplained == f"{summary.UNEXPLAINED_BEAT_TEXT}: silo_cold"
    clean = summary.planar_checks_section(
        _fake_er(_synthetic_record(), {"screening_status": "ok"})  # type: ignore[arg-type]
    )
    assert "No run and no comparison is bug_suspect." in clean
    assert summary.UNEXPLAINED_BEAT_TEXT not in clean
    assert f"{summary.OFFLOAD_CHECKS_TEXT}:" in clean
    assert summary.OFFLOAD_PAD_CONTROL_CHECK_CLAUSE in summary.OFFLOAD_CHECKS_TEXT
    assert summary.PAD_CONTROL_BLOCKED not in clean
    failing = _synthetic_record()
    failing["pad_controls"][0] = {
        **failing["pad_controls"][0],
        "resolution_effect": False,
        "m_res_kg": -0.5,
        "consistency": compare.CHECK_FAIL,
    }
    text = summary.planar_checks_section(
        _fake_er(failing, {"screening_status": "ok"})  # type: ignore[arg-type]
    )
    lines = text.splitlines()
    assert "No run and no comparison is bug_suspect." in lines
    assert f"{summary.PAD_CONTROL_BLOCKED}: pad control stage1" in lines
    assert "pad control stage1 (comparison)" not in text
    assert not any(ln.startswith(summary.FINDINGS_BLOCKED) for ln in lines)


SERIES_COLUMNS = [*replay.REPLAY_COLUMNS, "stage"]
EVENT_COLUMNS = ["t_s", "event", "phase", "stage", "alt_m", "downrange_m", "speed_rel_mps", "m_kg"]


def _write_series(run_dir: Path, name: str, assisted: bool) -> None:
    """A tiny planar timeseries.csv and events.csv: a push (or a hold) then a climb."""
    folder = run_dir / name
    folder.mkdir(parents=True)
    rows = []
    for k in range(-4, 41):
        t = 0.5 * k
        on_track = t < 0.0
        rows.append(
            {
                "t_s": t + 2.0,
                "t_rel_release_s": t,
                "phase": ("ASSIST" if assisted else "HOLD") if on_track else "GRAVITY_TURN",
                "stage": "stage1",
                "alt_m": (-50.0 * (t / -2.0) if assisted else 0.0) if on_track else 10.0 * t * t,
                "downrange_m": 0.0 if on_track else t**3,
                "speed_rel_mps": (25.0 * (2.0 + t) if assisted else 0.0)
                if on_track
                else 50.0 + 20 * t,
                "gamma_rel_rad": math.pi / 2 - (0.0 if on_track else t / 40.0),
                "felt_axial_g": 4.0 if on_track else 1.5,
                "q_pa": (math.nan if assisted else 0.0) if on_track else 100.0 * t,
                "mach": (math.nan if assisted else 0.0) if on_track else t / 10.0,
                "m_kg": 1000.0 - t,
            }
        )
    header = ",".join(SERIES_COLUMNS)
    lines = [header, *(",".join(str(r[c]) for c in SERIES_COLUMNS) for r in rows)]
    (folder / "timeseries.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    events = [",".join(EVENT_COLUMNS), "2.0,release,COAST,stage1,0.0,0.0,50.0,1000.0"]
    (folder / "events.csv").write_text("\n".join(events) + "\n", encoding="utf-8")


def _replay_dir(root: Path) -> Path:
    """A synthetic planar results directory: the pad, and the offload block's runs (s1,
    its paired pad, the stage-1 pad control) recorded in metrics.json ``offload`` and
    resolved_config.yaml ``offload_runs``."""
    run_dir = root / "results" / "synth_offload" / "20260101T000000Z"
    run_dir.mkdir(parents=True)
    pad_metrics = {"status": "inserted", "payload_kg": 1000.0, "assist_model": "none"}
    silo_metrics = {
        "status": "inserted",
        "payload_kg": 1000.0,
        "assist_model": "constant_accel",
        "exit_speed_mps": 50.0,
        "felt_g_track_peak": 4.0,
        "push_time_s": 2.0,
        "track_start_altitude_m": -50.0,
        "net_accel_g": 3.0,
    }
    offload = {
        "reference": "pad",
        "reference_payload_kg": 1000.0,
        "cases": [
            {
                "name": "s1",
                "run": "s1",
                "of": "silo",
                "kind": "solve",
                "total_offload_kg": 41262.9,
                "stage1_fraction": 0.1004,
                "total_fraction": 0.0796,
                "payload_kg": 1000.0,
                "paired_pad": {"run": "s1__pad"},
            }
        ],
        "pad_controls": [{"mode": "stage1", "run": "pad__offload_stage1"}],
        "runs": {"s1": silo_metrics, "s1__pad": pad_metrics, "pad__offload_stage1": pad_metrics},
    }
    metrics = {
        "experiment": "synth_offload",
        "timestamp_utc": "20260101T000000Z",
        "model": "planar_2d",
        "baseline": "pad",
        "runs": {"pad": pad_metrics},
        "comparison": {},
        "offload": offload,
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    pad_cfg = {"assist": {"model": "none"}, "site": {"include_rotation": True}}
    silo_cfg = {
        "assist": {"model": "constant_accel", "net_accel_g": 3.0, "track": {"angle_deg": 90}},
        "site": {"include_rotation": True},
    }
    cfg = {
        "vehicle": {"name": "synth"},
        "runs": {"pad": {"run": pad_cfg}},
        "offload_runs": {
            "s1": {"run": silo_cfg, "vehicle": {"name": "synth"}},
            "s1__pad": {"run": pad_cfg, "vehicle": {"name": "synth"}},
            "pad__offload_stage1": {"run": pad_cfg},
        },
    }
    (run_dir / "resolved_config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    for name, assisted in (("pad", False), ("s1", True), ("s1__pad", False)):
        _write_series(run_dir, name, assisted)
    _write_series(run_dir, "pad__offload_stage1", False)
    return run_dir


def test_replay_shows_an_offload_run_beside_the_pad(tmp_path: Path) -> None:
    """run_source gives each run of metrics.json ``offload.runs`` the offload role, its
    metrics and config from the block, no comparison, and a note: how much propellant
    the case carries less (tonnes, % of the stage-1 load and of all) and the payload it
    flies against P_ref; the paired pad and the pad control say what they are. The page
    of the pad and s1 renders with s1 labelled "(offload)", no payload change and the
    offload caveat."""
    run_dir = _replay_dir(tmp_path)
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    cfg = yaml.safe_load((run_dir / "resolved_config.yaml").read_text(encoding="utf-8"))
    source = replay.run_source(metrics, cfg, "s1")
    assert source["role"] == replay.ROLE_OFFLOAD == "offload"
    assert source["compared_to"] is None and source["comparison"] == {}
    assert source["metrics"]["net_accel_g"] == 3.0
    assert source["config"]["assist"]["model"] == "constant_accel"
    note = source["note"]
    assert note.startswith("offload case s1 of silo: 41.26 t less propellant (solved; 10.04%")
    assert "7.96% of all" in note and "flying 1,000.0 kg" in note and "P_ref = 1,000.0 kg" in note
    assert "paired pad of offload case s1" in replay.run_source(metrics, cfg, "s1__pad")["note"]
    control = replay.run_source(metrics, cfg, "pad__offload_stage1")["note"]
    assert control.startswith("pad control (stage1)")
    data = replay.replay_data(run_dir, ["pad", "s1"])
    s1 = next(r for r in data["runs"] if r["key"] == "s1")
    assert s1["label"] == "s1 (offload)" and s1["role"] == "offload" and s1["assisted"]
    assert s1["payload_delta_kg"] is None
    assert any("of the offload block" in c for c in data["meta"]["caveats"])
    out = replay.write_replay_page(run_dir, ["pad", "s1"], tmp_path / "page.html")
    assert "s1 (offload)" in out.read_text(encoding="utf-8")


def _sweep(root: Path, offload: list[dict[str, dict[str, Any]]]) -> results_io.SweepResult:
    point = SimpleNamespace(point_index=1, overrides={"assist.stroke_m": 100})
    rr = SimpleNamespace(name="run_0001", result=SimpleNamespace(metrics={}, status="inserted"))
    return results_io.SweepResult(
        1,
        "silo_cold",
        ["assist.stroke_m"],
        [point],
        [rr],
        [{}],  # type: ignore[list-item]
        [root / "sweep_1" / "run_0001"],
        [None],
        offload,
        [{} for _ in offload],
    )


def test_sweep_index_gains_offload_columns_only_when_a_sweep_names_cases(tmp_path: Path) -> None:
    """A planar sweep that solved an offload case adds ``<case>.<column>`` for every
    OFFLOAD_SWEEP_COLUMNS column before ``status`` (values from the case record: the
    verification's delta, the offloaded run's max-Q; a solved case flies P_ref, so its
    payload delta is 0; a fixed case's figure P* - P_ref, here 0.5 kg, with no
    verification); one that solved none keeps the columns it had; the 1-D
    SWEEP_INDEX_METRICS are unchanged; a bug_suspect point decomposition blocks the
    sweep's findings, under a heading that makes no claim about pad controls (a sweep
    solves none)."""
    base = [
        "point",
        "assist.stroke_m",
        "run_dir",
        "of",
        "paired_baseline",
        *PLANAR_SWEEP_INDEX_METRICS,
        *PLANAR_SWEEP_INDEX_TEXT,
        "status",
    ]
    plain = results_io.planar_sweep_index_frame(_sweep(tmp_path, []), tmp_path)
    assert list(plain.columns) == base
    record, fixed = _synthetic_record()["cases"][:2]
    p_ref, p_fixed = record["reference_payload_kg"], record["reference_payload_kg"] + 0.5
    fixed = {**fixed, "payload_kg": p_fixed, "payload_delta_kg": p_fixed - p_ref}
    points = [{"s1": record, "f10": fixed}]
    frame = results_io.planar_sweep_index_frame(_sweep(tmp_path, points), tmp_path)
    added = [f"{n}.{c}" for n in ("s1", "f10") for c in OFFLOAD_SWEEP_COLUMNS]
    assert list(frame.columns) == [*base[:-1], *added, "status"]
    row = frame.iloc[0]
    assert row["s1.offload_kg"] == 41262.9 and row["s1.status"] == "ok"
    assert row["s1.verification_delta_kg"] == 0.01 and row["s1.max_q_pa"] == 38591.0
    assert row["s1.decomposition_status"] == "explained" and row["s1.screening_ratio"] == 2.755
    assert row["s1.payload_kg"] == p_ref and row["s1.payload_delta_kg"] == 0.0
    assert row["f10.offload_kg"] == 41090.0 and row["f10.reference_payload_kg"] == p_ref
    assert row["f10.payload_kg"] == p_fixed
    assert row["f10.payload_delta_kg"] == pytest.approx(0.5, abs=1e-9)
    assert pd.isna(row["f10.verification_delta_kg"])
    assert results_io.SWEEP_INDEX_METRICS == (
        "exit_speed_mps",
        "stage1_burnout_speed_mps",
        "stage1_burnout_speed_delta_mps",
        "ignition_loss_formula_mps",
        "drive_energy_J",
        "drive_power_peak_W",
        "felt_g_track_peak",
        "facility_length_m",
    )
    suspect = _sweep(tmp_path, [{"s1": {**record, "decomposition_status": "bug_suspect"}}])
    suspect.comparisons[0].update(screening_status="ok")
    baseline = _fake_run("pad")
    text = summary.sweep_checks_section([suspect], baseline)  # type: ignore[arg-type]
    assert "- sweep_1/run_0001 s1 offload decomposition: bug_suspect" in text
    assert f"{summary.FINDINGS_BLOCKED}: sweep_1/run_0001 s1 offload decomposition" in text
    assert f"{summary.OFFLOAD_SWEEP_CHECKS_TEXT}:" in text.splitlines()
    assert "pad control" not in text


SWEEP_COLUMNS_BEFORE_8A = (
    "status",
    "offload_kg",
    "stage1_fraction",
    "total_fraction",
    "reference_payload_kg",
    "payload_kg",
    "payload_delta_kg",
    "verification_delta_kg",
    "decomposition_status",
    "screening_ratio",
    "max_q_pa",
    "electrical_energy_J",
)
"""OFFLOAD_SWEEP_COLUMNS as step 7 shipped them (commit 6719f92), in order."""
CSV_SIGNIFICANT_DIGITS = 12
"""Significant digits of a float in sweep_index.csv (results_io.write_csv's %.12g)."""


def test_sweep_index_records_each_point_solves_gamma_star_and_flags(tmp_path: Path) -> None:
    """KI-028 (SP1 step 8a): every offload case of a sweep point records its solve's own
    gamma*_ref [rad] (the record's ``solve.gamma_star_rad``, here 23.4 deg, not the
    point's payload-search ``gamma_star_rad``, here 22.0 deg) and its flag count as two
    columns appended after step 7's twelve, which keep their names and order; a fixed
    case (no solve) leaves gamma*_ref empty and counts its flags (0 here); a
    reference_failed point (no flag list) leaves both empty. The CSV keeps gamma*_ref to
    12 significant digits. The sweep's Checks section lists each
    point's flags (joined by "; ", ``none`` for an empty list, OFFLOAD_SWEEP_NO_FLAG_LIST
    without a list) under OFFLOAD_SWEEP_FLAGS_TEXT, apart from the decomposition lines; a
    solve that ended search_failed (an empty flag list, no gamma*_ref, as
    ``_case_record`` builds it) says so with its failure kind, never a bare "none"."""
    assert OFFLOAD_SWEEP_COLUMNS == (*SWEEP_COLUMNS_BEFORE_8A, "solve_gamma_star_rad", "n_flags")
    gamma_solve, gamma_point = math.radians(23.4), math.radians(22.0)
    flags = ["offload: a flag", "offload_verify_mismatch: a second"]
    record, fixed = _synthetic_record()["cases"][:2]
    s1 = {**record, "solve": {"status": "ok", "gamma_star_rad": gamma_solve}, "flags": flags}
    fixed = {**fixed, "flags": []}
    failed = {"name": "s1", "status": results_io.REFERENCE_FAILED_STATUS}
    search_failed = {
        **record,
        "status": SEARCH_FAILED_STATUS,
        "solve": {
            "status": SEARCH_FAILED_STATUS,
            "gamma_star_rad": math.nan,
            "failure_kind": "bracket",
            "flags": [],
        },
        "decomposition_status": None,
        "flags": [],
    }
    point = SimpleNamespace(point_index=1, overrides={"assist.stroke_m": 100})
    rr = SimpleNamespace(
        name="run_0001",
        result=SimpleNamespace(
            metrics={"gamma_star_rad": gamma_point, "run_checks": "ok"}, status="inserted"
        ),
    )
    names = ("run_0001", "run_0002", "run_0003")
    sweep = results_io.SweepResult(
        1,
        "silo_cold",
        ["assist.stroke_m"],
        [point] * 3,
        [rr, *(SimpleNamespace(name=n, result=rr.result) for n in names[1:])],
        [{}, {}, {}],  # type: ignore[list-item]
        [tmp_path / "sweep_1" / n for n in names],
        [None, None, None],
        [{"s1": s1, "f10": fixed}, {"s1": failed}, {"s1": search_failed}],
        [{}, {}, {}],
    )
    frame = results_io.planar_sweep_index_frame(sweep, tmp_path)  # type: ignore[arg-type]
    added = [f"{n}.{c}" for n in ("s1", "f10") for c in OFFLOAD_SWEEP_COLUMNS]
    assert [c for c in frame.columns if "." in c and c.split(".")[0] in ("s1", "f10")] == added
    first, second, third = frame.iloc[0], frame.iloc[1], frame.iloc[2]
    assert first["s1.solve_gamma_star_rad"] == gamma_solve and first["s1.n_flags"] == len(flags)
    assert first["gamma_star_rad"] == gamma_point  # the point's own payload search
    assert pd.isna(first["f10.solve_gamma_star_rad"]) and first["f10.n_flags"] == 0
    assert pd.isna(second["s1.solve_gamma_star_rad"]) and pd.isna(second["s1.n_flags"])
    assert second["s1.status"] == results_io.REFERENCE_FAILED_STATUS
    assert third["s1.status"] == SEARCH_FAILED_STATUS and third["s1.n_flags"] == 0
    assert pd.isna(third["s1.solve_gamma_star_rad"])
    path = results_io.write_csv(tmp_path / "sweep_index.csv", frame)
    written = pd.read_csv(path)
    assert written["s1.solve_gamma_star_rad"][0] == pytest.approx(
        gamma_solve, rel=0.5 * 10.0 ** (1 - CSV_SIGNIFICANT_DIGITS)
    )
    assert written["s1.n_flags"][0] == len(flags)
    text = summary.sweep_checks_section([sweep], _fake_run("pad"))  # type: ignore[arg-type]
    lines = text.splitlines()
    heading = lines.index(f"{summary.OFFLOAD_SWEEP_FLAGS_TEXT}:")
    assert lines.index(f"{summary.OFFLOAD_SWEEP_CHECKS_TEXT}:") < heading
    assert lines[heading + 1 : heading + 5] == [
        f"- sweep_1/run_0001 s1 offload flags: {flags[0]}; {flags[1]}",
        "- sweep_1/run_0001 f10 offload flags: none",
        f"- sweep_1/run_0002 s1 offload flags: {summary.OFFLOAD_SWEEP_NO_FLAG_LIST}",
        "- sweep_1/run_0003 s1 offload flags: none (solve search_failed: bracket)",
    ]
    fixed_failed = {**fixed, "status": SEARCH_FAILED_STATUS}
    assert summary.offload_sweep_flag_line("p f10", fixed_failed) == (
        "- p f10 offload flags: none (payload search search_failed)"
    )
    assert "pad control" not in text
    plain = summary.sweep_checks_section([_sweep(tmp_path, [])], _fake_run("pad"))  # type: ignore[arg-type]
    assert summary.OFFLOAD_SWEEP_FLAGS_TEXT not in plain


def test_payload_sensitivity_note_for_an_empty_of_points_to_the_offload_arms(
    repo_root: Path, fake_sim: SimpleNamespace
) -> None:
    """SP1 step 8a: a sensitivity block whose ``of`` lists no run, kept for the offload
    arms, is not reported as "no sensitivity block declared": the payload Sensitivity
    note says no run has payload sensitivity cases and that the arms are in the section
    "Propellant saved at fixed payload" (or that --no-offload skipped them); without
    arms it says only the first. When the arms' case variant did not run (``run
    --variant`` naming another variant), the note says none of the arms ran instead of
    pointing to an arms table the offload section does not print. No block at all, a
    block whose ``of`` lists runs, and --no-sensitivity keep their notes.
    planar_experiment_result carries the note, which the Sensitivity section prints
    when no case ran."""
    cd = compare.CD_SENSITIVITY_NOTES[config.PLANAR_2D]
    empty = "no run has payload sensitivity cases: the sensitivity block's `of` lists no run"
    arms = (
        "its params perturb the offload block's sensitivity arms, reported in the section "
        '"Propellant saved at fixed payload"'
    )
    skipped = (
        "its params perturb the offload block's sensitivity arms, which --no-offload "
        "skipped with the block"
    )
    not_run = (
        "its params perturb the offload block's sensitivity arms, none of which ran "
        "(their case's variant did not run)"
    )
    assert summary.OFFLOAD_SECTION_TITLE == "## Propellant saved at fixed payload"
    block = {
        "reference": "pad",
        "pad_control": True,
        "sensitivity_of": ["s1"],
        "cases": [{"name": "s1", "of": "silo_cold", "solve": "stage1"}],
    }
    resolved, baseline, variants, _masses = _fake_pass(repo_root, block)
    assert set(variants) == {"silo_cold"}

    def note(r: Any, *, sensitivity: bool, offload: bool, ran: Any = variants) -> str:
        return results_io.planar_sensitivity_note(
            r, sensitivity=sensitivity, offload=offload, variants=ran
        )

    assert note(resolved, sensitivity=True, offload=True) == f"({empty}; {arms}; C_D: {cd})"
    assert note(resolved, sensitivity=True, offload=False) == f"({empty}; {skipped}; C_D: {cd})"
    assert note(resolved, sensitivity=False, offload=True) == compare.SENSITIVITY_SKIPPED
    assert note(resolved, sensitivity=True, offload=True, ran=[]) == (
        f"({empty}; {not_run}; C_D: {cd})"
    )
    assert note(resolved, sensitivity=True, offload=False, ran=[]) == (
        f"({empty}; {skipped}; C_D: {cd})"
    )
    for text in (note(resolved, sensitivity=True, offload=b) for b in (True, False)):
        assert "no sensitivity block declared" not in text
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(results_io, "planar_comparisons", lambda *a, **k: {})
        mp.setattr(results_io, "planar_bounds", lambda *a, **k: [])
        er = results_io.planar_experiment_result(
            resolved, baseline, variants, {}, "t", sensitivity=True, run_cases=False
        )
        er_other = results_io.planar_experiment_result(
            resolved, baseline, {}, {}, "t", sensitivity=True, run_cases=False
        )
    assert er.sensitivity == [] and er.sensitivity_note == f"({empty}; {arms}; C_D: {cd})"
    # a + and a - arm of s1 for each of _experiment's two sensitivity params
    assert er.offload is not None and len(er.offload.record["sensitivity"]) == 2 * 2
    assert summary.planar_sensitivity_table(er.sensitivity, er.sensitivity_note) == (
        er.sensitivity_note
    )
    assert er_other.sensitivity_note == f"({empty}; {not_run}; C_D: {cd})"
    assert er_other.offload is not None and er_other.offload.record["sensitivity"] == []
    assert "### Sensitivity" not in summary.offload_section(er_other.offload.record)
    exp, veh = _experiment(repo_root, {**block, "sensitivity_of": []})
    no_arms = resolve_experiment(exp, veh)
    assert note(no_arms, sensitivity=True, offload=True) == f"({empty}; C_D: {cd})"
    assert note(no_arms, sensitivity=True, offload=True, ran=[]) == f"({empty}; C_D: {cd})"
    exp, veh = _experiment(repo_root, {**block, "sensitivity_of": []})
    exp.pop("sensitivity")
    no_block = resolve_experiment(exp, veh)
    declared = f"(no sensitivity block declared; C_D: {cd})"
    assert note(no_block, sensitivity=True, offload=True) == declared
    exp, veh = _experiment(repo_root, block)
    exp["sensitivity"]["of"] = ["silo_cold"]
    listed = resolve_experiment(exp, veh)
    assert note(listed, sensitivity=True, offload=True) == (
        f"(no sensitivity cases declared for the runs that ran; C_D: {cd})"
    )


def test_cli_offload_flags_and_console_lines() -> None:
    """``run`` and ``sweep`` take --no-offload (off by default); --no-sensitivity's help
    names the offload arms; the console lines of an offload block are ASCII: the skip
    note, or each case's status, tonnes and shares (a fixed case then its figure P* -
    P_ref, signed), its decomposition, and each pad control with its consistency
    verdict."""
    parser = cli.build_parser()
    assert parser.parse_args(["run", "x.yaml"]).no_offload is False
    assert parser.parse_args(["run", "x.yaml", "--no-offload"]).no_offload is True
    assert parser.parse_args(["sweep", "x.yaml", "--no-offload"]).no_offload is True
    assert cli.offload_lines({"skipped": results_io.OFFLOAD_SKIPPED}) == [
        f"  offload: {results_io.OFFLOAD_SKIPPED}"
    ]
    record = _synthetic_record()
    f10 = record["cases"][1]
    record["cases"][1] = {**f10, "payload_kg": 26054.9, "payload_delta_kg": 26054.9 - 26054.4}
    lines = cli.offload_lines(record)
    assert lines[0] == "  offload at P_ref 26054.4 kg:"
    assert lines[1] == (
        f"    s1: ok, {41.2629:.6g} t removed ({100 * 41262.9 / 410900:.6g} % of stage 1, "
        f"{100 * 41262.9 / 518400:.6g} % of the total), decomposition explained"
    )
    assert lines[2] == (
        f"    f10: ok, {41.09:.6g} t removed ({100 * f10['stage1_fraction']:.6g} % of stage 1, "
        f"{100 * f10['total_fraction']:.6g} % of the total), P* - P_ref "
        f"{26054.9 - 26054.4:+.6g} kg, decomposition explained"
    )
    assert lines[3] == f"    x: {results_io.OFFLOAD_NOT_RUN}"
    assert lines[4] == "    pad control stage1: no_offload, x_pad 0 kg, consistency pass"
    assert all(line.isascii() for line in lines)


def _fake_resolved_run(name: str, vehicle: dict[str, Any]) -> SimpleNamespace:
    result = SimpleNamespace(metrics={"payload_kg": 1.0}, status="inserted", flags=[])
    resolved = SimpleNamespace(run_dict={"name": name}, vehicle_dict=vehicle)
    return SimpleNamespace(name=name, result=result, resolved=resolved)


def test_metrics_and_resolved_config_keys_appear_only_with_the_block() -> None:
    """Without an offload report metrics.json has no ``offload`` key and
    resolved_config.yaml no ``offload_runs``; with one, ``offload`` comes last in
    metrics.json (its record plus each written run's metrics record) and
    ``offload_runs`` last in resolved_config.yaml, a run on another vehicle dict with
    its vehicle."""
    pad = _fake_resolved_run("pad", {"name": "v", "m": 1})
    er = results_io.ExperimentResult(
        experiment_name="e",
        vehicle_name="v",
        baseline=pad,  # type: ignore[arg-type]
        variants={},
        comparison={},
        git={},
        timestamp_utc="t",
        model=config.PLANAR_2D,
    )
    assert "offload" not in results_io._metrics_dict(er)
    assert "offload_runs" not in results_io._resolved_config_dict(er)
    s1 = _fake_resolved_run("s1", {"name": "v", "m": 0.9})
    report = OffloadReport({"basis": "b", "cases": []}, runs={"s1": s1})  # type: ignore[dict-item]
    with_block = results_io._metrics_dict(_replace_er(er, report))
    assert list(with_block)[-1] == "offload"
    assert with_block["offload"]["runs"] == {
        "s1": {"payload_kg": 1.0, "status": "inserted", "flags": []}
    }
    cfg = results_io._resolved_config_dict(_replace_er(er, report))
    assert list(cfg)[-1] == "offload_runs"
    assert cfg["offload_runs"]["s1"] == {"run": {"name": "s1"}, "vehicle": {"name": "v", "m": 0.9}}


def _replace_er(
    er: results_io.ExperimentResult, report: OffloadReport
) -> results_io.ExperimentResult:
    import dataclasses

    return dataclasses.replace(er, offload=report)


def test_an_experiment_without_the_block_has_no_offload(repo_root: Path, planar_pins: Any) -> None:
    """The fixed-guidance fast experiment of tests/test_planar_pipeline.py (the output
    capture's) declares no block: its resolved offload is None and no sweep point carries
    an offload case, so planar_offload returns None before touching a run and nothing of
    the block is computed or written (that file's capture tests compare the written
    outputs with the step 1 capture)."""
    resolved = planar_pins.load_sibling("test_planar_pipeline").fast_experiment(repo_root)
    assert resolved.offload is None
    assert not any(p.offload for points in resolved.sweeps for p in points)
    assert results_io.planar_offload(resolved, None, {}) is None  # type: ignore[arg-type]


# ------------------------------------------------- the pass on fake runs (fast)

P_REF_KG = 26000.0
"""The fake pad's payload capacity P* [kg]."""
VERIFY_EXCESS_KG = 0.5
"""What a fake payload search finds above P_ref [kg] (within search_final_flag_rel x P_ref)."""
FAKE_SHARE = 0.08
"""Share of its mode's load a fake case solve takes as x* [-]."""
FAKE_X_PAD_KG = {"stage2": 1500.0, "both": 900.0}
"""x_pad [kg] of the fake stage2 and both pad controls."""
FAKE_ELEC_J = 4.0e9
"""Electrical energy of a fake assisted run [J]."""
CONTROL_LOGS = (
    OffloadEval(X2_LOG, 0.0, 0.03, 0.0, None),
    OffloadEval(X2_LOG, 2.0, -0.033, 0.0, None),
)
"""Logged evaluations of a fake stage-1 control: one bracket of m_res = 0."""


def _fake_result(metrics: dict[str, Any], search: Any = None) -> sim.Result:
    """A planar Result holding only metrics (and a search record)."""
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


def _assisted(resolved: Any) -> bool:
    return resolved.run_dict.get("assist", {}).get("model", "none") != "none"


def _fake_rr(resolved: Any, payload_kg: float | None) -> sim.RunResult:
    """A RunResult of a resolved run whose payload search found payload_kg (None: the
    search failed); an assisted run carries FAKE_ELEC_J."""
    status = "search_failed" if payload_kg is None else "ok"
    metrics = {
        "payload_kg": payload_kg,
        "search_status": status,
        "electrical_energy_J": FAKE_ELEC_J if _assisted(resolved) else None,
        "run_checks": "ok",
    }
    p_star = math.nan if payload_kg is None else payload_kg
    search = SimpleNamespace(status=status, payload_kg=p_star, flags=())
    return sim.RunResult(resolved.name, resolved, _fake_result(metrics, search))


def _solve_result(
    start: Any,
    mode: str,
    p_ref: float,
    status: str = "ok",
    x_kg: float | None = None,
    m_res_kg: float = 0.03,
    evals: tuple[OffloadEval, ...] = (),
) -> OffloadResult:
    """A fake solve on start: ok takes x_kg (default FAKE_SHARE of its mode's load),
    no_offload x = 0 with m_res(0) = m_res_kg, search_failed nothing."""
    load = offload_load_kg(start.to_vehicle(), mode)
    x = {"ok": FAKE_SHARE * load if x_kg is None else x_kg, "no_offload": 0.0}.get(status, math.nan)
    failed = status == "search_failed"
    return OffloadResult(
        mode=mode,
        reference_payload_kg=p_ref,
        load_kg=load,
        status=status,
        offload_kg=x,
        root_kg=x,
        gamma_star_rad=0.4,
        m_res_kg=math.nan if failed else m_res_kg,
        dv_margin_mps=math.nan if failed else 0.001,
        dv_shortfall_mps=math.nan,
        at_offload=None,
        recorded=None if failed else SimpleNamespace(),
        offloaded_vehicle=None,
        evaluations=evals,
        n_evaluations=len(evals),
        grid=(),
        verification=None,
        flags=(),
    )


@pytest.fixture
def fake_sim(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """The sim seams of the offload pass replaced by fakes: ``run_resolved`` (P* =
    P_REF_KG + VERIFY_EXCESS_KG unless ``payloads`` names the run), ``rerun_resolved``
    (the nominal's result), ``matched_run`` (None: no decomposition), the case solves
    (``_solve_result``, or the factory ``cases`` names for the start; the baseline's from
    ``controls`` per mode, default a stage-1 no_offload by grams with CONTROL_LOGS and
    the FAKE_X_PAD_KG controls), ``offload_run_result`` (no assumptions of its own) and
    the paired-pad comparison."""
    state = SimpleNamespace(payloads={}, controls={}, cases={}, baseline="pad", solved=[], ran=[])

    def run_resolved(resolved: Any) -> sim.RunResult:
        state.ran.append(resolved.name)
        return _fake_rr(resolved, state.payloads.get(resolved.name, P_REF_KG + VERIFY_EXCESS_KG))

    def solve(start: Any, mode: str, p_ref: float) -> OffloadResult:
        state.solved.append((start.name, mode, p_ref))
        if start.name != state.baseline:
            return state.cases.get(start.name, _solve_result)(start, mode, p_ref)
        if mode in state.controls:
            return state.controls[mode](start, mode, p_ref)
        if mode == "stage1":
            return _solve_result(
                start, mode, p_ref, "no_offload", m_res_kg=-0.0016, evals=CONTROL_LOGS
            )
        return _solve_result(start, mode, p_ref, x_kg=FAKE_X_PAD_KG[mode])

    def offload_run_result(final: Any, res: OffloadResult) -> sim.RunResult:
        metrics = {
            "payload_kg": res.reference_payload_kg,
            "electrical_energy_J": FAKE_ELEC_J if _assisted(final) else None,
            "run_checks": "ok",
        }
        return sim.RunResult(final.name, final, _fake_result(metrics))

    def paired(silo: Any, pad: Any, checks: Any, name: str) -> dict[str, Any]:
        p_silo, p_pad = silo.result.metrics["payload_kg"], pad.result.metrics["payload_kg"]
        return {"payload_delta_kg": p_silo - p_pad, "screening_status": "ok"}

    monkeypatch.setattr(sim, "run_resolved", run_resolved)
    monkeypatch.setattr(sim, "rerun_resolved", lambda resolved, hit: run_resolved(resolved))
    monkeypatch.setattr(sim, "matched_run", lambda *a, **k: None)
    monkeypatch.setattr(sim, "solve_resolved_offload", solve)
    monkeypatch.setattr(sim, "offload_run_result", offload_run_result)
    monkeypatch.setattr(results_io, "attributed_comparison", paired)
    return state


def _fake_block() -> dict[str, Any]:
    """Every case shape: a stage-1 solve with a paired pad, a penalty row, a frontier
    point with a penalty, stage-2 and both solves, a fixed fraction with a paired pad
    and a fixed stage-2 mass; pad controls, s1's arms and the energy inputs."""
    return {
        "reference": "pad",
        "pad_control": True,
        "sensitivity_of": ["s1"],
        "cases": [
            {"name": "s1", "of": "silo_cold", "solve": "stage1", "paired_pad": True},
            {
                "name": "s1_pen",
                "of": "silo_cold",
                "solve": "stage1",
                "stage1_dry_mass_added_t": 2.0,
            },
            {
                "name": "s1_s2pen",
                "of": "silo_cold",
                "solve": "stage1",
                "stage2_offload_t": 2.0,
                "stage1_dry_mass_added_t": 2.0,
            },
            {"name": "s2", "of": "silo_cold", "solve": "stage2"},
            {"name": "b", "of": "silo_cold", "solve": "both"},
            {
                "name": "f10",
                "of": "silo_cold",
                "fixed": {"stage1_fraction": 0.1},
                "paired_pad": True,
            },
            {"name": "f2t", "of": "silo_cold", "fixed": {"stage2_t": 2.0}},
        ],
        "energy": _energy(),
    }


def _fake_pass(
    repo_root: Path, block: dict[str, Any], params: dict[str, float] | None = None
) -> tuple[Any, sim.RunResult, dict[str, sim.RunResult], dict[str, float]]:
    """The test experiment with block (and the sensitivity params), resolved, with fake
    baseline (P* = P_REF_KG) and variant runs, and the gate fork's masses [t]."""
    exp, veh = _experiment(repo_root, block)
    if params is not None:
        exp["sensitivity"]["params"] = params
    resolved = resolve_experiment(exp, veh)
    baseline = _fake_rr(resolved.baseline, P_REF_KG)
    variants = {n: _fake_rr(r, P_REF_KG + 1500.0) for n, r in resolved.variants.items()}
    return resolved, baseline, variants, _masses_t(veh)


def test_offload_pass_records_each_case_against_hand_numbers(
    repo_root: Path, fake_sim: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """planar_offload on fake runs: per case what was removed from each stage (stage-2
    pre-offload included), its shares of the variant's loads, the net value x - x_pad
    (x_pad = 0 for the stage-1 control ending no_offload by grams, FAKE_X_PAD_KG for
    stage2 and both), the quoted offload (stage 1 gross, stage2 and both net, fixed the
    imposed offload), the penalty fields, the energy split at the vehicle file's mixture
    ratio (123.5/410.9 and 32.3/107.5 RP-1), all against hand numbers from the vehicle
    file; the record's caveats are the gate vehicle's. A load arm whose load falls below
    the stage's fuel mass solves, and its case record (captured from
    ``_offload_arm_record``, whose arm record carries no energy block) splits the
    removed propellant at the vehicle file's ratio too."""
    params = {DRY_PARAM: FRACTION, EFF_PARAM: FRACTION, LOAD_PARAM: 0.7}
    resolved, baseline, variants, m = _fake_pass(repo_root, _fake_block(), params)
    arm_cases: list[tuple[str, float, dict[str, Any]]] = []
    arm_record = results_io._offload_arm_record

    def capture(
        name: str, param: str, fraction: float, pad: bool, outcome: Any, nominal: Any
    ) -> dict[str, Any]:
        arm_cases.append((param, fraction, outcome.record))
        return arm_record(name, param, fraction, pad, outcome, nominal)

    monkeypatch.setattr(results_io, "_offload_arm_record", capture)
    report = results_io.planar_offload(resolved, baseline, variants)
    assert report is not None
    record = report.record
    cases = {c["name"]: c for c in record["cases"]}
    m_p1, m_p2 = m["m_p1"] * KG_PER_T, m["m_p2"] * KG_PER_T
    total_load = m_p1 + m_p2
    rp1, rp2 = FUEL_T["stage1"] / m["m_p1"], FUEL_T["stage2"] / m["m_p2"]
    x1, x2, xb = FAKE_SHARE * m_p1, FAKE_SHARE * m_p2, FAKE_SHARE * total_load
    pre = 2.0 * KG_PER_T
    expected = {  # name: (stage-1 removed, stage-2 removed, x, x_pad, quoted)
        "s1": (x1, 0.0, x1, 0.0, x1),
        "s1_pen": (x1, 0.0, x1, 0.0, x1),
        "s1_s2pen": (x1, pre, x1, 0.0, x1),
        "s2": (0.0, x2, x2, FAKE_X_PAD_KG["stage2"], x2 - FAKE_X_PAD_KG["stage2"]),
        "b": (
            xb * m_p1 / total_load,
            xb * m_p2 / total_load,
            xb,
            FAKE_X_PAD_KG["both"],
            xb - FAKE_X_PAD_KG["both"],
        ),
        "f10": (0.1 * m_p1, 0.0, 0.1 * m_p1, None, 0.1 * m_p1),
        "f2t": (0.0, pre, pre, None, pre),
    }
    for name, (r1, r2, x, x_pad, quoted) in expected.items():
        c = cases[name]
        assert c["offload_kg"] == pytest.approx(x, rel=1e-12), name
        assert c["stage1_offload_kg"] == pytest.approx(r1, rel=1e-12, abs=1e-9), name
        assert c["stage2_offload_kg"] == pytest.approx(r2, rel=1e-12, abs=1e-9), name
        assert c["total_offload_kg"] == pytest.approx(r1 + r2, rel=1e-12), name
        assert c["stage1_fraction"] == pytest.approx(r1 / m_p1, rel=1e-12, abs=1e-15), name
        assert c["stage2_fraction"] == pytest.approx(r2 / m_p2, rel=1e-12, abs=1e-15), name
        assert c["total_fraction"] == pytest.approx((r1 + r2) / total_load, rel=1e-12), name
        assert c["pad_control_offload_kg"] == x_pad, name
        if x_pad is None:
            assert c["net_offload_kg"] is None, name
        else:
            assert c["net_offload_kg"] == pytest.approx(x - x_pad, rel=1e-12), name
        assert c["quoted_offload_kg"] == pytest.approx(quoted, rel=1e-12), name
        energy = c["energy"]
        assert energy["fuel_removed_kg"] == pytest.approx(r1 * rp1 + r2 * rp2, rel=1e-12), name
        assert energy["oxidizer_removed_kg"] == pytest.approx(
            r1 + r2 - (r1 * rp1 + r2 * rp2), rel=1e-12
        ), name
    assert cases["s1"]["quoted_basis"] == results_io.OFFLOAD_QUOTED_HEADLINE
    assert (
        cases["s2"]["quoted_basis"] == cases["b"]["quoted_basis"] == results_io.OFFLOAD_QUOTED_NET
    )
    assert cases["f10"]["quoted_basis"] == results_io.OFFLOAD_QUOTED_FIXED
    assert cases["f10"]["fixed_fraction"] == 0.1 and cases["f2t"]["fixed_fraction"] is None
    for name in ("s1_pen", "s1_s2pen"):
        assert cases[name]["assumed_penalty"] and cases[name]["stage1_dry_mass_added_kg"] == 2000.0
    assert cases["s1_s2pen"]["stage2_preoffload_kg"] == pre
    assert not cases["s1"]["assumed_penalty"] and cases["s1"]["stage1_dry_mass_added_kg"] == 0.0
    assert cases["s1"]["paired_pad"]["payload_delta_kg"] == pytest.approx(0.0, abs=1e-12)
    assert record["caveats"] == summary.offload_caveats(GATE, plots.CALIBRATION_RECORDS[GATE])
    # the arms: a load arm whose load falls below the stage's fuel mass (0.3 x 410.9 t <
    # 123.5 t) still solves, its energy at the vehicle file's mixture ratio
    load_arms = [a for a in record["sensitivity"] if a["param"] == LOAD_PARAM]
    assert [a["status"] for a in load_arms] == ["ok", "ok"]
    x_low = FAKE_SHARE * 0.3 * m_p1
    assert load_arms[1]["offload_kg"] == pytest.approx(x_low, rel=1e-12)
    (low,) = (rec for p, f, rec in arm_cases if p == LOAD_PARAM and f < 0.0)
    assert 0.3 * m["m_p1"] < FUEL_T["stage1"]  # the arm's load is below its fuel mass
    assert low["offload_kg"] == pytest.approx(x_low, rel=1e-12)
    assert low["energy"]["fuel_removed_kg"] == pytest.approx(x_low * rp1, rel=1e-12)
    assert low["energy"]["oxidizer_removed_kg"] == pytest.approx(x_low * (1.0 - rp1), rel=1e-12)


def test_offload_runs_carry_their_assumptions(repo_root: Path, fake_sim: SimpleNamespace) -> None:
    """Every run the block writes (cases, paired pads, pad controls) carries
    OFFLOAD_ASSUMPTIONS; the assumed dry-mass line of a penalty row
    (``sim.offload_penalty_assumption`` of its 2 t) only the penalty rows' runs, never a
    paired pad or a pad control."""
    resolved, baseline, variants, _m = _fake_pass(repo_root, _fake_block())
    report = results_io.planar_offload(resolved, baseline, variants)
    assert report is not None
    names = set(report.runs)
    assert names == {
        "s1",
        "s1__pad",
        "s1_pen",
        "s1_s2pen",
        "s2",
        "b",
        "f10",
        "f10__pad",
        "f2t",
        "pad__offload_stage1",
        "pad__offload_stage2",
        "pad__offload_both",
    }
    penalty = sim.offload_penalty_assumption(2.0)
    for name, rr in report.runs.items():
        for line in sim.OFFLOAD_ASSUMPTIONS:
            assert line in rr.result.assumptions, name
        assert (penalty in rr.result.assumptions) == (name in ("s1_pen", "s1_s2pen")), name


def test_offload_pass_skips_what_it_cannot_solve(
    repo_root: Path, fake_sim: SimpleNamespace
) -> None:
    """Without sensitivity no arm is solved and the record says OFFLOAD_ARMS_SKIPPED (also
    through planar_experiment_result, the path of ``launchsim run --no-sensitivity``); an
    arm whose same-perturbation pad has no P* is REFERENCE_FAILED_STATUS, unsolved; a
    baseline without a P* solves nothing and the record says reference_failed."""
    block = {
        "reference": "pad",
        "pad_control": True,
        "sensitivity_of": ["s1"],
        "cases": [{"name": "s1", "of": "silo_cold", "solve": "stage1"}],
    }
    resolved, baseline, variants, _masses = _fake_pass(repo_root, block)
    off = results_io.planar_offload(resolved, baseline, variants, sensitivity=False)
    assert off is not None
    assert off.record["sensitivity"] == [] and off.record["notes"] == [
        results_io.OFFLOAD_ARMS_SKIPPED
    ]
    assert [s for s, _mode, _p in fake_sim.solved if s.startswith("s1__")] == []
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(results_io, "planar_comparisons", lambda *a, **k: {})
        mp.setattr(results_io, "planar_bounds", lambda *a, **k: [])
        er = results_io.planar_experiment_result(
            resolved, baseline, variants, {}, "t", sensitivity=False, run_cases=False
        )
    assert er.offload is not None and er.offload.record["notes"] == [
        results_io.OFFLOAD_ARMS_SKIPPED
    ]
    failed_pad = f"pad__{DRY_PARAM}__+0.1"
    fake_sim.payloads[failed_pad] = None
    fake_sim.solved.clear()
    full = results_io.planar_offload(resolved, baseline, variants)
    assert full is not None
    arms = {(a["param"], a["fraction"]): a for a in full.record["sensitivity"]}
    failed = arms[(DRY_PARAM, FRACTION)]
    assert failed["status"] == results_io.REFERENCE_FAILED_STATUS and failed["offload_kg"] is None
    assert failed_pad in failed["flags"][0]
    solved = {s: p_ref for s, _mode, p_ref in fake_sim.solved}
    assert f"s1__{DRY_PARAM}__+0.1" not in solved  # nothing solved without a P_ref
    assert arms[(DRY_PARAM, -FRACTION)]["status"] == "ok"
    assert solved[f"s1__{DRY_PARAM}__-0.1"] == P_REF_KG + VERIFY_EXCESS_KG  # its own pad's P*
    fake_sim.solved.clear()
    no_ref = results_io.planar_offload(resolved, _fake_rr(resolved.baseline, None), variants)
    assert no_ref is not None and no_ref.runs == {}
    assert results_io.REFERENCE_FAILED_STATUS in no_ref.record["skipped"]
    assert fake_sim.solved == []


def _ok_control(x_kg: float, evals: tuple[OffloadEval, ...] = CONTROL_LOGS) -> Any:
    return lambda start, mode, p_ref: _solve_result(start, mode, p_ref, x_kg=x_kg, evals=evals)


def _no_offload_control(m_res_kg: float) -> Any:
    return lambda start, mode, p_ref: _solve_result(
        start, mode, p_ref, "no_offload", m_res_kg=m_res_kg, evals=CONTROL_LOGS
    )


def _failed_control() -> Any:
    return lambda start, mode, p_ref: _solve_result(start, mode, p_ref, "search_failed")


CONTROL_OUTCOMES = {
    "ok within the bound": (_ok_control(0.044), True, "pass"),
    "ok outside the bound": (_ok_control(5.0), False, "fail"),
    "ok without a slope": (_ok_control(0.044, ()), None, "not_checked"),
    "no_offload by grams": (_no_offload_control(-0.0016), None, "pass"),
    "no_offload by more than xtol": (_no_offload_control(-0.5), None, "fail"),
    "search_failed": (_failed_control(), None, "fail"),
}


@pytest.mark.parametrize("label", list(CONTROL_OUTCOMES))
def test_stage1_pad_control_is_a_consistency_test(
    repo_root: Path, fake_sim: SimpleNamespace, label: str
) -> None:
    """The stage-1 pad control (phase file SP1 section 5.3): the bound is
    final_payload_xtol_kg / s with s the secant of the control's logged bracket
    (computed here); an ok control passes inside [0, bound] and fails outside it, and is
    not_checked without a slope; a no_offload control passes only as a resolution
    effect (-xtol < m_res(0) < 0); search_failed fails. ``within_bound`` judges an ok
    control only. A failing control gets a blocked-findings line of its own
    (PAD_CONTROL_BLOCKED, "pad control stage1", never labelled a comparison) and the
    line saying no run or comparison is bug_suspect stays; every verdict is printed in
    the Checks lines and the console."""
    control, within, verdict = CONTROL_OUTCOMES[label]
    fake_sim.controls["stage1"] = control
    block = {
        "reference": "pad",
        "pad_control": True,
        "cases": [{"name": "s1", "of": "silo_cold", "solve": "stage1"}],
    }
    resolved, baseline, variants, _m = _fake_pass(repo_root, block)
    report = results_io.planar_offload(resolved, baseline, variants)
    assert report is not None
    (rec,) = report.record["pad_controls"]
    xtol = resolved.baseline.run.planar.search.final_payload_xtol_kg
    lo, hi = CONTROL_LOGS
    slope = (lo.m_res_kg - hi.m_res_kg) / (hi.offload_kg - lo.offload_kg)
    if label in ("ok without a slope", "search_failed"):
        assert rec["bound_kg"] is None
    else:
        assert rec["bound_kg"] == pytest.approx(xtol / slope, rel=1e-12)
    assert rec["within_bound"] is within and rec["consistency"] == verdict
    record = report.record
    blocked = summary.blocked_lines(
        {}, summary.offload_check_comparisons(record), summary.offload_blocking_controls(record)
    )
    control_line = f"{summary.PAD_CONTROL_BLOCKED}: pad control stage1"
    failed = [control_line] if verdict == "fail" else []
    assert blocked == ["No run and no comparison is bug_suspect.", *failed]
    assert "Pad control, and why" in summary.PAD_CONTROL_BLOCKED
    check_lines = summary.offload_check_lines(report.record)
    line = next(ln for ln in check_lines if ln.startswith("- pad control stage1: "))
    assert line.endswith(summary.PAD_CONTROL_VERDICT_TEXT[verdict])
    assert f"consistency {verdict}" in "\n".join(cli.offload_lines(report.record))


def test_pad_control_consistency_rule() -> None:
    """``pad_control_consistency`` branch by branch, with xtol = 0.05 kg and a bound of
    1.6 kg: stage 1 ok inside / at / outside [0, bound], without a bound; no_offload
    just inside and at -xtol; search_failed; stage 2 and both n/a whatever their
    status."""
    rule = results_io.pad_control_consistency
    xtol, bound = 0.05, 1.6
    assert rule("stage1", "ok", 0.0, 0.03, bound, xtol) == compare.CHECK_PASS
    assert rule("stage1", "ok", bound, 0.0, bound, xtol) == compare.CHECK_PASS
    assert rule("stage1", "ok", bound + 1e-9, 0.0, bound, xtol) == compare.CHECK_FAIL
    assert rule("stage1", "ok", 0.044, 0.0, None, xtol) == compare.PAD_CONTROL_NO_BOUND
    assert rule("stage1", "no_offload", 0.0, -0.0499, bound, xtol) == compare.CHECK_PASS
    assert rule("stage1", "no_offload", 0.0, -xtol, bound, xtol) == compare.CHECK_FAIL
    assert rule("stage1", "search_failed", math.nan, math.nan, None, xtol) == compare.CHECK_FAIL
    for mode in ("stage2", "both"):
        for status in ("ok", "no_offload", "search_failed"):
            assert rule(mode, status, 1.0, -1.0, None, xtol) == compare.CHECK_NA


def test_stage2_and_both_cases_are_quoted_net_of_the_pad_control() -> None:
    """The cases table leads with the quoted offload and its basis (a stage-2 case: x -
    x_pad, labelled a property of the vehicle model), the gross rows after it; the
    console line of a stage-2 case leads with the net tonnes and the label, the gross
    after it, and says "not quoted" and why from its basis: no pad-control offload, or
    its own solve did not end ok (then without the vehicle-model label)."""
    record = _synthetic_record()
    s2 = {
        **record["cases"][0],
        "name": "s2",
        "mode": "stage2",
        "offload_kg": 3000.0,
        "stage1_offload_kg": 0.0,
        "stage2_offload_kg": 3000.0,
        "total_offload_kg": 3000.0,
        "pad_control_offload_kg": 1500.0,
        "net_offload_kg": 1500.0,
        "quoted_offload_kg": 1500.0,
        "quoted_basis": results_io.OFFLOAD_QUOTED_NET,
    }
    record["cases"] = [record["cases"][0], s2]
    text = summary.offload_section(record)
    assert f"| quoted offload [t] | {41.2629:.6g} | 1.5 |" in text
    head = f"|   basis | {results_io.OFFLOAD_QUOTED_HEADLINE} | {results_io.OFFLOAD_QUOTED_NET} |"
    assert head in text
    assert f"| total propellant removed, gross [t] | {41.2629:.6g} | 3 |" in text
    lines = cli.offload_lines(record)
    assert lines[2].startswith(
        "    s2: ok, 1.5 t net of the pad control, a property of the vehicle model; gross 3 t"
    )
    record["cases"][1] = {
        **s2,
        "quoted_offload_kg": None,
        "net_offload_kg": None,
        "pad_control_offload_kg": None,
        "quoted_basis": results_io.OFFLOAD_QUOTED_NO_CONTROL,
    }
    assert cli.offload_lines(record)[2].startswith(
        "    s2: ok, not quoted (no pad-control offload to net it against), a property of "
        "the vehicle model; gross 3 t removed"
    )
    record["cases"][1] = {
        **s2,
        "status": "search_failed",
        "offload_kg": math.nan,
        "stage2_offload_kg": math.nan,
        "total_offload_kg": math.nan,
        "quoted_offload_kg": None,
        "net_offload_kg": None,
        "quoted_basis": results_io.OFFLOAD_QUOTED_FAILED,
    }
    assert cli.offload_lines(record)[2].startswith(
        "    s2: search_failed, not quoted (the case's own solve did not end ok); gross n/a t"
    )


def test_a_failed_case_solve_is_not_quoted_for_its_own_reason(
    repo_root: Path, fake_sim: SimpleNamespace
) -> None:
    """A stage-2 case whose own solve ends search_failed beside an ok stage-2 pad control
    (x_pad = FAKE_X_PAD_KG): the record keeps the control's x_pad, has no net value and
    quotes nothing, on the basis OFFLOAD_QUOTED_FAILED (not the pad control's
    OFFLOAD_QUOTED_NO_CONTROL), and the console says its own solve did not end ok; a
    failed stage-1 case quotes nothing on the same basis; a case beside them that solved
    is quoted as usual."""
    fake_sim.cases["s2"] = _failed_control()
    fake_sim.cases["s1"] = _failed_control()
    block = {
        "reference": "pad",
        "pad_control": True,
        "cases": [
            {"name": "s1", "of": "silo_cold", "solve": "stage1"},
            {"name": "s2", "of": "silo_cold", "solve": "stage2"},
            {"name": "b", "of": "silo_cold", "solve": "both"},
        ],
    }
    resolved, baseline, variants, m = _fake_pass(repo_root, block)
    report = results_io.planar_offload(resolved, baseline, variants)
    assert report is not None
    controls = {p["mode"]: p for p in report.record["pad_controls"]}
    assert controls["stage2"]["status"] == "ok"
    assert controls["stage2"]["offload_kg"] == FAKE_X_PAD_KG["stage2"]
    cases = {c["name"]: c for c in report.record["cases"]}
    s2 = cases["s2"]
    assert s2["status"] == "search_failed" and math.isnan(s2["offload_kg"])
    assert s2["pad_control_offload_kg"] == FAKE_X_PAD_KG["stage2"]
    assert s2["net_offload_kg"] is None and s2["quoted_offload_kg"] is None
    assert s2["quoted_basis"] == results_io.OFFLOAD_QUOTED_FAILED
    s1 = cases["s1"]
    assert s1["quoted_offload_kg"] is None
    assert s1["quoted_basis"] == results_io.OFFLOAD_QUOTED_FAILED
    xb = FAKE_SHARE * (m["m_p1"] + m["m_p2"]) * KG_PER_T
    assert cases["b"]["quoted_basis"] == results_io.OFFLOAD_QUOTED_NET
    assert cases["b"]["quoted_offload_kg"] == pytest.approx(xb - FAKE_X_PAD_KG["both"], rel=1e-12)
    lines = {ln.split(":")[0].strip(): ln for ln in cli.offload_lines(report.record)}
    assert lines["s2"].startswith(
        "    s2: search_failed, not quoted (the case's own solve did not end ok); gross n/a t"
    )
    assert lines["s1"].startswith(
        "    s1: search_failed, not quoted (the case's own solve did not end ok); gross n/a t"
    )
    assert "pad-control" not in lines["s2"] + lines["s1"]


def test_calibration_caveat_follows_the_vehicle() -> None:
    """The calibration caveat of the gate vehicle states its gap 100 (26054.4/22800 - 1)
    % from its record (+14.3 % high); a vehicle without a record says it has none; both
    end with the model reading."""
    record = plots.CALIBRATION_RECORDS[GATE]
    gate = summary.offload_calibration_caveat(GATE, record)
    gap = 100.0 * (record[0] / record[1] - 1.0)
    assert f"{gap:+.1f}% high" in gate and "+14.3% high" in gate and "26,054 kg" in gate
    other = summary.offload_calibration_caveat("readme_loads_fork", None)
    assert "readme_loads_fork has no calibration record on file" in other
    for text in (gate, other):
        assert text.endswith(summary.OFFLOAD_MODEL_READING)
    assert summary.offload_caveats(GATE, record) == [gate, *summary.OFFLOAD_CAVEATS]


def test_calibration_caveat_of_the_readme_loads_fork() -> None:
    """SP1 step 8a: the README-loads fork has its calibration record (case readme_loads of
    docs/findings/CAL-f9-leo-2d), so an offload block on it (the bridge) states
    100 (24,700/22,800 - 1) = +8.3 % high with its masses, not "no calibration record"."""
    record = plots.CALIBRATION_RECORDS[README_FORK]
    text = summary.offload_calibration_caveat(README_FORK, record)
    gap = 100.0 * (24700.0 / 22800.0 - 1.0)
    assert f"{gap:+.1f}% high" in text and "+8.3% high" in text
    assert "carries 24,700 kg in its calibration run against the published 22,800 kg" in text
    assert "no calibration record" not in text and text.endswith(summary.OFFLOAD_MODEL_READING)


def test_stage2_caveat_does_not_assume_a_stage1_offload_maximises_total_tonnes() -> None:
    """SP1 step 8a (pre-registration Amendment 1, item 4): the stage-2 caveat printed with
    every offload block no longer says that total tonnes are maximised by a stage-1-only
    offload, so 'both' cannot beat the headline (the pre-registration, section 7, tests
    that instead); it says that it is not assumed, keeps stage 1 as the only headline,
    and places the measured marginal value of stage-2 propellant on the gate vehicle."""
    stage2 = summary.OFFLOAD_CAVEATS[-1]
    assert stage2 == (
        "stage 1 is the headline: stage-2 and both-stage offloads are a property of the "
        "vehicle model (stage-2 propellant is worth about nothing at the margin on the gate "
        "vehicle), quoted net of the pad control (the gross rows beside them are not a "
        "saving of the assist); a stage-1-only offload is not assumed to maximise the total "
        "tonnes ('both' may remove more, its stage-2 share riding about free), and stage 1 "
        "stays the only headline either way"
    )
    for caveat in summary.offload_caveats(GATE, plots.CALIBRATION_RECORDS[GATE]):
        assert "cannot beat the headline" not in caveat
        assert "are maximised by a stage-1-only offload" not in caveat


def test_sweep_point_energy_keeps_the_vehicle_files_mixture_ratio(
    repo_root: Path, fake_sim: SimpleNamespace
) -> None:
    """A paired sweep point with a 100 t stage-1 load (below the energy block's 123.5 t of
    RP-1) solves its case and splits the removed propellant at the vehicle file's ratio
    123.5/410.9; its share of the load is the point's own."""
    exp, veh = _experiment(repo_root, _fake_block())
    exp["sweeps"] = [
        {"of": "silo_cold", "paired": True, "axes": {LOAD_PARAM: [100.0]}, "offload": ["s1"]}
    ]
    resolved = resolve_experiment(exp, veh)
    (point,) = resolved.sweeps[0]
    ref = _fake_rr(point.paired_baseline, P_REF_KG)
    energy = resolved.offload.config.energy
    records, _runs = results_io.offload_sweep_point(
        point, ref, _fake_rr(point.run, P_REF_KG), energy, resolved.baseline.to_vehicle()
    )
    rec = records["s1"]
    x = FAKE_SHARE * 100.0 * KG_PER_T
    assert rec["offload_kg"] == pytest.approx(x, rel=1e-12)
    assert rec["stage1_fraction"] == pytest.approx(FAKE_SHARE, rel=1e-12)
    rp1 = x * FUEL_T["stage1"] / _masses_t(veh)["m_p1"]
    assert rec["energy"]["fuel_removed_kg"] == pytest.approx(rp1, rel=1e-12)


def test_sweep_offload_columns_follow_the_offload_flag(
    repo_root: Path, fake_sim: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_run_sweeps_into`` (run_sweep's body) with offload False solves no sweep case
    and writes no ``<case>.*`` column; with offload True each point's cases are solved
    against the point's baseline with the experiment's baseline vehicle for the energy,
    and their columns appear."""
    exp, veh = _experiment(repo_root, _fake_block())
    exp["sweeps"] = [{"of": "silo_cold", "axes": {"assist.stroke_m": [100]}, "offload": ["s1"]}]
    resolved = resolve_experiment(exp, veh)
    calls: list[Any] = []

    def sweep_point(point: Any, ref: Any, rr: Any, energy: Any, energy_vehicle: Any) -> Any:
        calls.append((point.run.name, ref.name, energy_vehicle))
        return {"s1": {"name": "s1", "status": "ok", "offload_kg": 1.0}}, {}

    monkeypatch.setattr(results_io, "offload_sweep_point", sweep_point)
    monkeypatch.setattr(results_io, "write_single", lambda rr, ref, er, out, *a, **k: out)
    monkeypatch.setattr(
        results_io, "planar_comparisons", lambda res, ref, runs, **k: {n: {} for n in runs}
    )
    _sweeps, frames, _base = results_io._run_sweeps_into(
        resolved, tmp_path / "off", False, {}, "t", offload=False
    )
    assert calls == [] and not [c for c in frames[0].columns if c.startswith("s1.")]
    _sweeps, frames, _base = results_io._run_sweeps_into(
        resolved, tmp_path / "on", False, {}, "t", offload=True
    )
    assert [(p, r) for p, r, _v in calls] == [("run_0001", "pad")]
    assert calls[0][2].stages[0].propellant_mass_kg == _masses_t(veh)["m_p1"] * KG_PER_T
    assert [f"s1.{c}" for c in OFFLOAD_SWEEP_COLUMNS] == [
        c for c in frames[0].columns if c.startswith("s1.")
    ]


# ------------------------------------------------------------------------ slow


SMALL_GRID = {
    "gamma_grid_deg": [18.0, 28.0, 2.0],
    "gamma_refine_maxiter": 3,
    "gamma_refine_halfwidth_deg": 1.0,
    "search_rtol": 1.0e-9,
}
"""A small searched budget (the vehicle payload set near the pad's capacity so the
payload brackets close at once; search rtol 1e-9: CLAUDE.md's test rule)."""


def _searched_experiment(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """silo_screening_2d on the small grid with silo_cold, the sensitivity params
    (dry mass and drive efficiency, +/- 10 %) and a block: s1 solved in stage 1 with a
    paired pad, f5 fixed at 5 % of the stage-1 load, the pad control, s1's arms and the
    energy inputs."""
    exp, veh = _raw(repo_root)
    exp["search"].update(SMALL_GRID)
    exp["baseline"]["integrator"]["sample_dt_s"] = 0.5
    veh["payload_mass_t"]["value"] = 26.0
    exp["variants"] = {k: v for k, v in exp["variants"].items() if k == "silo_cold"}
    for key in ("sweeps", "bounds"):
        exp.pop(key, None)
    exp["sensitivity"] = {"of": [], "params": {DRY_PARAM: FRACTION, EFF_PARAM: FRACTION}}
    exp["offload"] = {
        "reference": "pad",
        "pad_control": True,
        "sensitivity_of": ["s1"],
        "cases": [
            {"name": "s1", "of": "silo_cold", "solve": "stage1", "paired_pad": True},
            {"name": "f5", "of": "silo_cold", "fixed": {"stage1_fraction": 0.05}},
        ],
        "energy": _energy(),
    }
    return exp, veh


@pytest.fixture(scope="module")
def offload_e2e(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> SimpleNamespace:
    """The searched experiment resolved from dicts and run in memory (baseline and
    variants through sim.run_resolved, then planar_experiment_result) with the working
    directory in an empty folder, whose listing is kept; then written by write_run."""
    exp, veh = _searched_experiment(repo_root)
    cwd = tmp_path_factory.mktemp("offload_cwd")
    with contextlib.chdir(cwd):
        resolved = resolve_experiment(exp, veh)
        baseline = sim.run_resolved(resolved.baseline)
        variants = {name: sim.run_resolved(run) for name, run in resolved.variants.items()}
        er = results_io.planar_experiment_result(
            resolved, baseline, variants, {}, "20260101T000000Z", sensitivity=True, run_cases=True
        )
        listing = sorted(p.name for p in cwd.iterdir())
    out = results_io.write_run(er, tmp_path_factory.mktemp("offload_out") / "run", plots=False)
    return SimpleNamespace(exp=exp, veh=veh, resolved=resolved, er=er, out=out, listing=listing)


@pytest.mark.slow
def test_offload_in_memory_writes_nothing(offload_e2e: SimpleNamespace) -> None:
    """resolve_experiment of dicts, sim.run_resolved and planar_experiment_result leave
    the working directory empty and return the block's report (the SP2 app's path)."""
    assert offload_e2e.listing == []
    report = offload_e2e.er.offload
    assert isinstance(report, OffloadReport)
    assert [c["name"] for c in report.record["cases"]] == ["s1", "f5"]
    assert set(report.runs) == {"s1", "s1__pad", "f5", "pad__offload_stage1"}


@pytest.mark.slow
def test_offload_cases_end_to_end(offload_e2e: SimpleNamespace) -> None:
    """The solved stage-1 case: ok, its recorded run flies exactly P_ref (inserted, 0 <=
    m_res < final_payload_xtol_kg) at the liftoff mass of the pad at P_ref less x*
    (stage and fairing masses from the vehicle file), verified within
    search_final_flag_rel x P_ref, its decomposition explained with the D_id change
    c1 ln(m0/(m0 - x*)) (c1 = g0 Isp_vac,1, m0 the pad's liftoff mass) and the ratio the
    offload over the yardstick; its shares of the loads and its energy against hand
    arithmetic; the paired pad offloaded by x*, its comparison the assisted P* less its
    own. The fixed case: x = 5 % of m_p1, its P* against P_ref, its margin term of the
    sign opposite to P* - P_ref. The pad control's consistency verdict by the rule of
    section 5.3 applied here to its own fields (on this small grid it may fail: the
    control's own gamma*_ref need not reproduce P_ref at a coarse refine). Every written
    run carries OFFLOAD_ASSUMPTIONS. The arms: the dry-mass arms solved at their own
    pad's P*, the efficiency arms reusing x* with the electrical energy scaled by
    0.5/(0.5 (1 +/- 0.1))."""
    er, veh = offload_e2e.er, offload_e2e.veh
    m = _masses_t(veh)
    record = er.offload.record
    checks = er.baseline.resolved.run.planar.checks
    search = er.baseline.resolved.run.planar.search
    p_ref = er.baseline.result.metrics["payload_kg"]
    assert record["reference_payload_kg"] == p_ref
    s1, f5 = record["cases"]
    x = s1["offload_kg"]
    assert s1["status"] == "ok" and 0.0 < x < m["m_p1"] * KG_PER_T
    run = er.offload.runs["s1"].result
    assert run.status == "inserted" and run.metrics["payload_kg"] == p_ref
    assert 0.0 <= run.metrics["recorded_m_res_kg"] < search.final_payload_xtol_kg
    stages = veh["stages"]
    wet = sum((s["dry_mass_t"]["value"] + s["propellant_mass_t"]["value"]) for s in stages)
    m0 = (wet + veh["fairing_mass_t"]["value"]) * KG_PER_T + p_ref
    assert er.baseline.result.metrics["liftoff_mass_kg"] == pytest.approx(m0, abs=1e-6)
    assert run.metrics["liftoff_mass_kg"] == pytest.approx(m0 - x, abs=1e-6)
    ver = s1["verification"]
    assert ver["passed"] and abs(ver["delta_kg"]) <= checks.search_final_flag_rel * p_ref
    xv = s1["decomposition"]
    assert (
        s1["decomposition_status"] == "explained"
        and abs(xv["xv_residual_mps"]) < checks.closure_tol_mps
    )
    c1 = G0_MPS2 * stages[0]["engine"]["isp_vac_s"]["value"]
    assert xv["xv_ideal_dv_reduction_mps"] == pytest.approx(c1 * math.log(m0 / (m0 - x)), abs=1e-8)
    assert s1["screening_ratio"] == pytest.approx(x / s1["screening_offload_kg"], rel=1e-15)
    assert s1["stage1_fraction"] == pytest.approx(x / (m["m_p1"] * KG_PER_T), rel=1e-14)
    total = (m["m_p1"] + m["m_p2"]) * KG_PER_T
    assert s1["total_fraction"] == pytest.approx(x / total, rel=1e-14)
    energy = s1["energy"]
    rp1 = x * FUEL_T["stage1"] / m["m_p1"]
    assert energy["fuel_removed_kg"] == pytest.approx(rp1, rel=1e-14)
    assert energy["heat_J"] == pytest.approx(rp1 * TEST_LHV_MJ_PER_KG * J_PER_MJ, rel=1e-14)
    assert energy["electrical_energy_J"] == run.metrics["electrical_energy_J"] > 0.0
    assert energy["heat_to_electricity_ratio"] == pytest.approx(
        energy["heat_J"] / run.metrics["electrical_energy_J"], rel=1e-15
    )
    paired = s1["paired_pad"]
    pad_dict = er.offload.runs["s1__pad"].resolved.vehicle_dict
    assert pad_dict["stages"][0]["propellant_mass_t"]["value"] == pytest.approx(
        (m["m_p1"] * KG_PER_T - x) / KG_PER_T, rel=1e-15
    )
    assert paired["payload_delta_kg"] == pytest.approx(
        ver["payload_kg"] - paired["payload_kg"], abs=1e-9
    )
    assert paired["screening_status"] is not None
    assert f5["offload_kg"] == pytest.approx(0.05 * m["m_p1"] * KG_PER_T, rel=1e-15)
    assert f5["payload_delta_kg"] == pytest.approx(f5["payload_kg"] - p_ref, abs=1e-9)
    assert f5["decomposition_status"] == "explained"
    margin = f5["decomposition"]["xv_margin_mps"]
    assert margin * f5["payload_delta_kg"] < 0.0
    (control,) = record["pad_controls"]
    assert control["status"] in ("ok", "no_offload") and control["offload_kg"] >= 0.0
    xtol = search.final_payload_xtol_kg
    if control["status"] == "ok":
        slope = control["slope_kg_per_kg"]
        inside = slope is not None and 0.0 <= control["offload_kg"] <= xtol / slope
        expected = "not_checked" if slope is None else ("pass" if inside else "fail")
    else:  # no_offload: a pass only as a resolution effect
        expected = "pass" if -xtol < control["m_res_kg"] < 0.0 else "fail"
        assert control["within_bound"] is None
    assert control["consistency"] == expected
    for name, rr in er.offload.runs.items():
        assert all(line in rr.result.assumptions for line in sim.OFFLOAD_ASSUMPTIONS), name
    arms = {(a["param"], a["fraction"]): a for a in record["sensitivity"]}
    assert len(arms) == 4
    for sign in (1.0, -1.0):
        dry = arms[(DRY_PARAM, sign * FRACTION)]
        assert dry["status"] == "ok" and not dry["trajectory_reused"]
        assert dry["reference_payload_kg"] != p_ref and dry["decomposition_status"] == "explained"
        eff = arms[(EFF_PARAM, sign * FRACTION)]
        assert eff["trajectory_reused"] and eff["offload_kg"] == x
        assert eff["electrical_energy_J"] == pytest.approx(
            run.metrics["electrical_energy_J"] / (1.0 + sign * FRACTION), rel=1e-12
        )


@pytest.mark.slow
def test_offload_outputs_written_and_replayed(offload_e2e: SimpleNamespace) -> None:
    """write_run adds metrics.json ``offload`` (last; the record and the written runs'
    metrics), resolved_config.yaml ``offload_runs`` (with the offloaded vehicle
    dicts), the summary section with its basis and caveats, the offload decompositions
    and the pad control's verdict in Checks (a failing control in a blocked-findings
    line of its own, PAD_CONTROL_BLOCKED), and a folder per offload run with planar CSVs;
    the replay page shows the pad beside s1, which reached orbit and carries the offload
    label."""
    out = offload_e2e.out
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    assert list(metrics)[-1] == "offload"
    assert set(metrics["offload"]["runs"]) == {"s1", "s1__pad", "f5", "pad__offload_stage1"}
    cfg = yaml.safe_load((out / "resolved_config.yaml").read_text(encoding="utf-8"))
    assert list(cfg)[-1] == "offload_runs" and "vehicle" in cfg["offload_runs"]["s1"]
    text = (out / "summary.md").read_text(encoding="utf-8")
    assert summary.OFFLOAD_SECTION_TITLE in text and compare.OFFLOAD_COMPARISON_BASIS in text
    assert all(c in text for c in summary.OFFLOAD_CAVEATS)
    assert summary.OFFLOAD_CHECKS_TEXT in text and "- s1: decomposition explained" in text
    lines = text.splitlines()
    failed = metrics["offload"]["pad_controls"][0]["consistency"] == "fail"
    assert (f"{summary.PAD_CONTROL_BLOCKED}: pad control stage1" in lines) == failed
    assert "pad control stage1 (comparison)" not in text
    assert any(ln.startswith("- pad control stage1: ") for ln in lines)
    for name in ("s1", "s1__pad", "f5", "pad__offload_stage1"):
        header = (out / name / "timeseries.csv").read_text(encoding="utf-8").splitlines()[0]
        assert header.split(",") == list(sim.PLANAR_TIMESERIES_COLUMNS)
        assert (out / name / "events.csv").is_file()
    data = replay.replay_data(out, ["pad", "s1"])
    s1 = next(r for r in data["runs"] if r["key"] == "s1")
    assert s1["role"] == "offload" and s1["inserted"] and s1["label"] == "s1 (offload)"


@pytest.mark.slow
def test_no_offload_skips_the_block(offload_e2e: SimpleNamespace) -> None:
    """planar_experiment_result with offload False keeps the block's record to the skip
    note, which is all its summary section prints; nothing is solved or written."""
    er = offload_e2e.er
    variants = dict(er.variants)
    skipped = results_io.planar_experiment_result(
        offload_e2e.resolved,
        er.baseline,
        variants,
        {},
        "t",
        sensitivity=False,
        run_cases=False,
        offload=False,
    )
    assert skipped.offload is not None and skipped.offload.runs == {}
    assert skipped.offload.record["skipped"] == results_io.OFFLOAD_SKIPPED
    assert summary.offload_section(skipped.offload.record) == results_io.OFFLOAD_SKIPPED


@pytest.mark.slow
def test_sweep_offload_columns_match_the_experiment_solve(
    offload_e2e: SimpleNamespace, tmp_path: Path
) -> None:
    """A one-point sweep of silo_cold at its own stroke that names s1 solves it against
    the same baseline: the same x* as the experiment's solve (identical inputs), in the
    index's ``s1.*`` columns, and the decomposition line in the sweep's Checks. SP1 step
    8a (KI-028): the index's ``s1.solve_gamma_star_rad`` is the run command's
    ``solve.gamma_star_rad`` for the same flight, within the CSV's 12 significant digits,
    ``s1.n_flags`` the length of the point's flag list, and the Checks section lists the
    point's flag line under OFFLOAD_SWEEP_FLAGS_TEXT."""
    exp = copy.deepcopy(offload_e2e.exp)
    exp["sweeps"] = [{"of": "silo_cold", "axes": {"assist.stroke_m": [100]}, "offload": ["s1"]}]
    resolved = resolve_experiment(exp, offload_e2e.veh)
    sweeps, out = results_io.run_sweep(resolved, tmp_path, plots=False)
    (record,) = (rec["s1"] for rec in sweeps[0].offload)
    nominal = offload_e2e.er.offload.record["cases"][0]
    assert record["offload_kg"] == pytest.approx(nominal["offload_kg"], abs=1e-9)
    index = (out / "sweep_1" / "sweep_index.csv").read_text(encoding="utf-8").splitlines()
    assert all(f"s1.{c}" in index[0].split(",") for c in OFFLOAD_SWEEP_COLUMNS)
    (row,) = pd.read_csv(out / "sweep_1" / "sweep_index.csv").to_dict("records")
    assert row["s1.solve_gamma_star_rad"] == pytest.approx(
        nominal["solve"]["gamma_star_rad"], rel=0.5 * 10.0 ** (1 - CSV_SIGNIFICANT_DIGITS)
    )
    assert row["s1.n_flags"] == len(record["flags"])
    text = (out / "summary.md").read_text(encoding="utf-8")
    assert "sweep_1/run_0001 s1 offload decomposition: explained" in text
    lines = text.splitlines()
    heading = lines.index(f"{summary.OFFLOAD_SWEEP_FLAGS_TEXT}:")
    assert lines[heading + 1] == summary.offload_sweep_flag_line("sweep_1/run_0001 s1", record)
    assert lines[heading + 1].startswith("- sweep_1/run_0001 s1 offload flags: ")
