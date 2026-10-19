"""The reporting of the structural model (SP7 step S3b; docs/physics.md, "Reporting the
structure"; design 4.4: the payload form, the records, the summary, the figures, the
sweep and arm columns, the post-hoc flight check, the plausibility-scaled row).

No test here solves a pre-registered SP7 structural case (D-SP7-31): the structural model
runs on tests/data/structure_synthetic.yaml and the synthetic pad flight of
tests/structure_support.py, the passes on fake runs (the sim seams of
tests/test_structure_pipeline.py's fixture, extended here with a payload search whose P*
falls with the dry mass, so the payload form's two passes differ, and with a solve that
can end no_offload). Nothing reads results/. Every number asserted is recomputed here from
the record or from closed forms.

Fast:

- the payload form on fake runs: dm_0 sized at P_ref, P_1* on the vehicle carrying dm_0,
  dm_1 at P_1*, P_2* on dm_1; the contraction c = |(P_2* - P_1*)/(dm_1 - dm_0)| x |(dm_1 -
  dm_0)/(P_1* - P_ref)| and the residual estimate c |P_2* - P_1*| recomputed from the
  record; the flag firing when the contraction limit is tightened, its run line carrying
  the numbers; the record kind, the run written under the case's name with dm_1 restated
  under the provenance and dm_0 as its ``structure_dm_x0_kg`` (the offload case's value),
  the pass-1 run among the checked runs, the assumption lines, never under the offload
  cases; a case whose P_2* (or P_1*) search fails: its status recorded, nothing written,
  no figure, no payload flag, the summary's status rows and its n/a cells;
- ``structure_inputs`` present only with a block (its envelope per element against a
  rebuilt envelope, the plausibility table against ``structure.plausibility``, the sets'
  label, the tornado and break-even entries null with the note) and the record's keys
  unchanged without one;
- the Structure subsection: every row's label, every printed number traced to a record key
  (dm1 = dm - dm2, F_peak in MN, the penalty row's tonnes, the override case's layer and
  overrides row, the no_offload end's shortfall and payload deficit or "not flown", never
  "0 t" in its x* or share cell, the factor cell n/a off the physics ends), the band lines
  with each end named and the unscaled and the scaled end side by side (either order), a
  case with overrides on a physics set kept off the band and named on the layer-2 line, the
  where-found and applicability lines, the central element table's labels and sums, the
  plausibility table with its trigger line, the payload cases, the arms line with deviation
  17's caveat, the figures named, a uniform cell count per table, ASCII; absent without a
  block;
- the arms table's structural columns and the caveat line under it, only with a structural
  arm;
- the sweep columns: OFFLOAD_STRUCTURE_SWEEP_COLUMNS appended after every case's plain
  columns and only for a case that was structural at some point; an SP1-type index
  unchanged; a sweep point's resolved_config.yaml carries the structure file only when the
  sweep solved a structural case there (not with --no-offload, not for a plain case);
- the plausibility-scaled row: refused on the central and the outer sets and as a
  non-bool, accepted on a physics set; the factor from ``structure.plausibility`` on the
  synthetic pad (never typed in), the sized dm carrying it within the fixed point's own
  movement, the three record keys on every structural run, the provenance suffix;
- the flight check on a synthetic recorded run: the adapter's cases against the pad
  adapter's, a flight inside its own envelope giving 0.0 kg and no flag, a flight at 20%
  more felt n an exceedance above the threshold with the flag fired and promoted to the
  run's flags, the refusals; under a plate-limited stiffened row the barrels' exceedance
  equal to the push path's on the same flight (the envelope's anchor); a scaled case's
  flag naming the factor its dm carries while the exceedance stays unscaled;
- the figure writer on a record: two panels, one bar per element, the PNG written, the
  mode markers keyed by mode name, the legend from synthetic handles, the annotation off
  every drawn artist and off the stage-2 inset, the title inside the figure for every
  layer label, a relation element named in the caption only;
- the console lines of a payload case; the record JSON-safe.
"""

from __future__ import annotations

import copy
import dataclasses
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import pytest
from matplotlib.text import Text

from launchsim import cli, compare, config, plots, results_io, sim, structure, summary
from launchsim.config import (
    StructureCaseConfig,
    StructurePayloadCaseConfig,
    offload_solved_run,
    resolve_experiment,
    resolve_structure_settings,
)
from launchsim.offload import NO_OFFLOAD_STATUS, OffloadResult
from launchsim.units import kg_to_t, n_to_mn
from launchsim.vehicle import with_offload, with_payload


def _load_sibling(name: str) -> ModuleType:
    """tests/<name>.py, loaded by path (any pytest import mode)."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tsp = _load_sibling("test_structure_pipeline")
ss = tsp.ss
SYNTHETIC_NAME = tsp.SYNTHETIC_NAME
ST_CASE = tsp.ST_CASE
PLAIN_CASE = tsp.PLAIN_CASE
P_REF = ss.P_REF_KG
PAYLOAD_PER_DRY_KG = 0.25
"""The fake payload search's slope [kg of P* per kg of stage-1 dry mass]: P* = P_ref + 0.5
- 0.25 (dry1 - 22,200 kg), a test rule so the payload form's two passes differ."""
DRY1_NOMINAL_KG = 22_200.0
X_FAKE = tsp.X_FAKE
SHORTFALL_MPS = 12.5
"""The fake no_offload solve's delta-v shortfall [m/s]."""

synthetic_file = tsp.synthetic_file
synthetic_pad = tsp.synthetic_pad
sp1_resolved = tsp.sp1_resolved


@pytest.fixture
def fake_reporting_pass(
    monkeypatch: pytest.MonkeyPatch, synthetic_pad: structure.PadLoadSet
) -> SimpleNamespace:
    """test_structure_pipeline's fake pass with three differences: the payload search's P*
    falls with the stage-1 dry mass (PAYLOAD_PER_DRY_KG), a start named in
    ``state.no_offload`` ends no_offload at x = 0 with SHORTFALL_MPS, and a run named in
    ``state.search_fail`` ends its payload search search_failed (P* NaN)."""
    state = tsp.fake_pass.__wrapped__(monkeypatch, synthetic_pad)
    state.no_offload = set()
    state.search_fail = set()

    def payload_of(resolved: Any) -> float:
        dry1 = resolved.to_vehicle().stages[0].dry_mass_kg
        return P_REF + 0.5 - PAYLOAD_PER_DRY_KG * (dry1 - DRY1_NOMINAL_KG)

    def run_resolved(resolved: Any) -> sim.RunResult:
        state.ran.append((resolved.name, resolved.vehicle_dict))
        if resolved.name in state.search_fail:
            rr = tsp._fake_rr(resolved, math.nan)
            rr.result.metrics["search_status"] = "search_failed"
            return rr
        return tsp._fake_rr(resolved, payload_of(resolved))

    real_solve = sim.solve_resolved_offload

    def solve(start: Any, mode: str, p_ref: float, *, transform: Any = None) -> OffloadResult:
        if start.name not in state.no_offload:
            return real_solve(start, mode, p_ref, transform=transform)
        state.solves.append((start.name, transform))
        vehicle = start.to_vehicle()
        if transform is not None:
            vehicle = transform(vehicle, p_ref)
        return OffloadResult(
            mode=mode,
            reference_payload_kg=p_ref,
            load_kg=vehicle.stages[0].propellant_mass_kg,
            status=NO_OFFLOAD_STATUS,
            offload_kg=0.0,
            root_kg=math.nan,
            gamma_star_rad=0.4,
            m_res_kg=-10.0,
            dv_margin_mps=-SHORTFALL_MPS,
            dv_shortfall_mps=SHORTFALL_MPS,
            at_offload=None,
            recorded=SimpleNamespace(),
            offloaded_vehicle=vehicle,
            evaluations=(),
            n_evaluations=0,
            grid=(),
            verification=None,
            flags=(),
        )

    monkeypatch.setattr(sim, "run_resolved", run_resolved)
    monkeypatch.setattr(sim, "rerun_resolved", lambda resolved, hit: run_resolved(resolved))
    monkeypatch.setattr(sim, "solve_resolved_offload", solve)
    return state


def _pass(
    cases: list[dict[str, Any]],
    *,
    payload_cases: list[dict[str, Any]] | None = None,
    sensitivity_of: list[str] | None = None,
    block: dict[str, Any] | None = None,
) -> tuple[config.ResolvedExperiment, results_io.OffloadReport]:
    """The test experiment (silo_cold, the given offload cases, a structure block naming
    the synthetic file with the payload cases; ``block`` {} for none) resolved and its
    offload pass on fake runs."""
    if block is None:
        block = {"file": SYNTHETIC_NAME, "payload_cases": payload_cases or []}
    exp, veh = tsp._experiment(cases, block=block, sensitivity_of=sensitivity_of)
    if sensitivity_of:
        exp["sensitivity"] = {"of": [], "params": {tsp.DRY_PARAM: 0.1, tsp.EFF_PARAM: 0.1}}
    resolved = tsp._resolve(exp, veh)
    baseline = tsp._fake_rr(resolved.baseline, P_REF)
    variants = {n: tsp._fake_rr(r, P_REF + 1500.0) for n, r in resolved.variants.items()}
    report = results_io.planar_offload(resolved, baseline, variants)
    assert report is not None
    return resolved, report


def _table_rows(block: str) -> list[list[str]]:
    """The cells of each row of a markdown table (the separator row left out)."""
    rows = []
    for line in block.splitlines():
        if line.startswith("|") and not re.fullmatch(r"\|(---\|)+", line):
            rows.append([c.strip() for c in line.strip("|").split("|")])
    return rows


def _row(text: str, label: str) -> list[str]:
    """The cells of the table row whose first cell is ``label`` (exactly one; the cells
    are stripped, so an indented label matches by its text)."""
    rows = [r for r in _table_rows(text) if r and r[0] == label.strip()]
    assert len(rows) == 1, label
    return rows[0]


PAYLOAD_CASE = {"name": "cold_pstar_st", "of": "silo_cold", "set": "central"}


# ------------------------------------------------------------------ the payload form


def test_payload_case_two_passes_contraction_and_flag(
    fake_reporting_pass: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The payload form (design 4.4): dm_0 is the full-load sizing at P_ref, P_1* the fake
    search on the vehicle carrying dm_0 (P_ref + 0.5 - 0.25 dm_0), dm_1 the sizing at P_1*
    (smaller: a lighter payload lowers the interface force), P_2* the search on dm_1; c and
    the residual estimate equal their definitions recomputed from the record (c =
    |P_2* - P_1*| / |P_1* - P_ref| when dm_1 != dm_0); the flag is off at the design's
    limits and fires when the contraction limit is tightened below c, its run line
    carrying c, the estimate and the tolerance; the record's kind, keys and run, its
    ``structure_dm_x0_kg`` dm_0 (the same number as the offload case's of the same variant
    and settings); the written run carries dm_1 under the provenance, the payload-case and
    structure assumption lines; the pass-1 run is a checked run; nothing of it is under
    ``cases``. A case whose P_2* search fails ends search_failed with ``run`` None, nothing
    written, no figure, ``unconverged`` None and no payload flag, its dm_1 recorded; one
    whose P_1* search fails has no second pass; the summary's status rows and n/a cells
    and the console line say so."""
    _resolved, report = _pass([ST_CASE], payload_cases=[PAYLOAD_CASE])
    rec = report.record
    (p,) = rec["structure_payload_cases"]
    assert p["kind"] == sim.STRUCTURE_PAYLOAD_RECORD_KIND == "structure payload case"
    assert [c["name"] for c in rec["cases"]] == ["s1_st"]
    assert p["name"] == "cold_pstar_st" and p["of"] == "silo_cold" and p["run"] == "cold_pstar_st"
    dm0, dm1, p1, p2 = p["dm_0_kg"], p["dm_1_kg"], p["payload_1_kg"], p["payload_kg"]
    assert p["reference_payload_kg"] == P_REF
    assert p1 == pytest.approx(P_REF + 0.5 - PAYLOAD_PER_DRY_KG * dm0, rel=1e-12)
    assert 0.0 < dm1 < dm0  # sized at a lighter payload: a smaller push
    assert p2 == pytest.approx(P_REF + 0.5 - PAYLOAD_PER_DRY_KG * dm1, rel=1e-12)
    c = abs((p2 - p1) / (dm1 - dm0)) * abs((dm1 - dm0) / (p1 - P_REF))
    assert p["contraction"] == pytest.approx(c, rel=1e-12) and 0.0 < c < 0.1
    assert p["residual_estimate_kg"] == pytest.approx(c * abs(p2 - p1), rel=1e-12)
    assert p["payload_delta_kg"] == p2 - P_REF and p["payload_2_minus_1_kg"] == p2 - p1
    xtol = _resolved.baseline.run.planar.search.final_payload_xtol_kg
    assert p["residual_tolerance_kg"] == 0.5 * xtol
    assert p["unconverged"] is False and p["status"] == "ok"
    flag = next(f for f in p["structure_flags"] if f["name"] == sim.STRUCTURE_PAYLOAD_FLAG)
    assert flag["fired"] is False and flag["values"]["contraction"] == p["contraction"]
    assert tuple(list(p)[-len(sim.STRUCTURE_RECORD_KEYS) :]) == sim.STRUCTURE_RECORD_KEYS
    assert p["structure_dm_kg"] == dm1 and p["structure_sizing"] == "full_load"
    assert p["structure_dm_x0_kg"] == dm0 == rec["cases"][0]["structure_dm_x0_kg"]
    rr = report.runs["cold_pstar_st"]
    dry = rr.resolved.vehicle_dict["stages"][0]["dry_mass_t"]
    assert dry["value"] == pytest.approx(22.2 + (dm1 - p["dm_1_stage2_kg"]) / 1000.0, rel=1e-15)
    assert dry["source"].startswith("first-order station sizing") and "full_load" in dry["source"]
    # the restated mass's note names the payload case, never a solved offload case
    assert dry["note"].startswith("structure payload case 'cold_pstar_st':")
    assert "(solved)" not in dry["note"] and "offload case" not in dry["note"]
    for name, vehicle_dict in fake_reporting_pass.ran:
        if name.startswith("cold_pstar_st"):
            for stage in vehicle_dict["stages"]:
                note = stage["dry_mass_t"].get("note", "")
                assert "(solved)" not in note and "offload case" not in note, name
    assert sim.STRUCTURE_PAYLOAD_CASE_ASSUMPTION in rr.result.assumptions
    lines = [a for a in rr.result.assumptions if a.startswith("structure:")]
    assert len(lines) == 1 and "pad's own flight" in lines[0]
    assert not [a for a in rr.result.assumptions if a.startswith("offload:")]
    assert rr.result.metrics["structure_dm_kg"] == dm1
    assert "cold_pstar_st__pass1 (structure payload case, pass 1: payload search at dm_0)" in (
        report.checked_runs
    )
    assert p["flags"] == rr.result.flags and sim.STRUCTURE_PAYLOAD_FLAG not in " ".join(p["flags"])
    assert "cold_pstar_st" in report.increments
    assert (
        _resolved.structure is not None
        and not _resolved.structure.payload_cases[0].structure.plausibility_scaled
    )
    # the flag fires when the contraction limit is tightened below c
    contraction_max = sim.STRUCTURE_PAYLOAD_CONTRACTION_MAX
    monkeypatch.setattr(sim, "STRUCTURE_PAYLOAD_CONTRACTION_MAX", c / 2.0)
    _resolved2, report2 = _pass([ST_CASE], payload_cases=[PAYLOAD_CASE])
    (p2r,) = report2.record["structure_payload_cases"]
    assert p2r["unconverged"] is True
    assert any(line.startswith(sim.STRUCTURE_PAYLOAD_FLAG) for line in p2r["flags"])
    (flag_line,) = [
        line
        for line in report2.runs["cold_pstar_st"].result.flags
        if line.startswith(sim.STRUCTURE_PAYLOAD_FLAG)
    ]
    assert f"residual estimate {p2r['residual_estimate_kg']:.3g} kg" in flag_line
    assert f"tolerance {p2r['residual_tolerance_kg']:g} kg" in flag_line
    assert f"contraction {p2r['contraction']:.3g} against {c / 2.0:g}" in flag_line
    console = cli.offload_lines(results_io.offload_record(report2))
    assert any("structure payload case cold_pstar_st: ok" in line for line in console)
    assert any("structure_payload_unconverged" in line for line in console)
    assert all(line.isascii() for line in console)
    monkeypatch.setattr(sim, "STRUCTURE_PAYLOAD_CONTRACTION_MAX", contraction_max)
    # a failed P_2* search (cold_fail2) and a failed P_1* search (cold_fail1): nothing written
    fake_reporting_pass.search_fail |= {"cold_fail2", "cold_fail1__pass1"}
    failing = [
        PAYLOAD_CASE,
        {**PAYLOAD_CASE, "name": "cold_fail2"},
        {**PAYLOAD_CASE, "name": "cold_fail1"},
    ]
    _resolved3, report3 = _pass([ST_CASE], payload_cases=failing)
    ok, f2, f1 = report3.record["structure_payload_cases"]
    assert ok["status"] == "ok" and ok["run"] == "cold_pstar_st"
    assert f2["status"] == "search_failed" and f2["run"] is None and f2["run_status"] is None
    assert f2["search_1_status"] == "ok" and f2["dm_1_kg"] == ok["dm_1_kg"]
    assert f2["unconverged"] is None and f2["vs_pad"] is None
    assert math.isnan(f2["payload_kg"]) and math.isnan(f2["contraction"])
    assert sim.STRUCTURE_PAYLOAD_FLAG not in [f["name"] for f in f2["structure_flags"]]
    assert f2["structure_dm_kg"] == f2["dm_1_kg"] and f2["structure_dm_x0_kg"] == f2["dm_0_kg"]
    assert f1["status"] == "search_failed" and f1["run"] is None and "dm_1_kg" not in f1
    assert set(report3.runs) == {"s1_st", "cold_pstar_st"} and set(report3.increments) == {
        "s1_st",
        "cold_pstar_st",
    }
    rec3 = results_io.offload_record(report3)
    text = summary.offload_section(rec3)
    payload_part = text.split("Structure payload cases")[1]
    status = _row(payload_part, "status (the P_2* search's: ok, or the failed search's status)")
    assert status[1:] == ["ok", "search_failed", "search_failed"]
    assert _row(payload_part, "  pass 1 (the P_1* search's status)")[1:] == [
        "ok",
        "ok",
        "search_failed",
    ]
    run_row = _row(payload_part, "recorded run (the P_2* search's run, carrying dm_1)")
    assert run_row[1:] == ["cold_pstar_st", summary.STRUCTURE_PAYLOAD_NOT_WRITTEN, "n/a"]
    flag_row = _row(
        payload_part,
        "structure_payload_unconverged (the estimate above the tolerance, or c > 0.1)",
    )
    assert flag_row[1:] == ["False", summary.STRUCTURE_PAYLOAD_FLAG_NA, "n/a"]
    assert _row(payload_part, "dm_1 [kg] (sized at P_1*)")[1:] == [
        summary._fmt(ok["dm_1_kg"]),
        summary._fmt(f2["dm_1_kg"]),
        "n/a",
    ]
    assert "plots/cold_pstar_st_structure.png" in text
    assert "cold_fail2_structure" not in text and "cold_fail1_structure" not in text
    console3 = cli.offload_lines(rec3)
    assert any(
        "structure payload case cold_fail2: search_failed, P* n/a kg" in ln for ln in console3
    )
    assert any(
        "structure payload case cold_fail1: search_failed, P* n/a kg" in ln for ln in console3
    )
    json.dumps(results_io.json_safe(rec3))


def test_uncharged_cases_leave_out_structural_penalty_and_unpushed_cases() -> None:
    """Fix round 3, S3A-NUM-03: the structure item's tail names as riding the push with no
    structural mass (summary.OFFLOAD_STRUCTURE_UNCHARGED_TEXT) only the cases that ran,
    charge neither a modelled mass nor an assumed penalty, and are built on a variant with
    a push: a case whose drive is summary.OFFLOAD_NO_ASSIST_MODEL is left out (the drive
    item says it flies without a push), so the two items never read against each other."""
    cases = [
        {"name": "s1"},
        {"name": "s1_st", "structure_charged": True},
        {"name": "s1_dry2", "assumed_penalty": True},
        {"name": "pad_x"},
        {"name": "lm_s1"},
    ]
    drives = {
        "s1": "constant_accel",
        "s1_st": "constant_accel",
        "s1_dry2": "constant_accel",
        "pad_x": summary.OFFLOAD_NO_ASSIST_MODEL,
        "lm_s1": "linear_motor",
    }
    assert results_io.offload_uncharged_cases(cases, drives) == ["s1", "lm_s1"]
    drive_item = summary.offload_drive_caveat(drives)
    assert "pad_x" in drive_item and "without a push" in drive_item
    item = summary.offload_structure_caveat(
        [{**STRUCTURAL_KEYS_FOR_ITEM, "name": "s1_st", "run": "s1_st"}],
        penalties=["s1_dry2"],
        uncharged=results_io.offload_uncharged_cases(cases, drives),
    )
    assert "pad_x" not in item and "; s1 and lm_s1 charge none (" in item


STRUCTURAL_KEYS_FOR_ITEM: dict[str, Any] = {
    "structure_charged": True,
    "structure_dm_kg": 9100.3,
    "structure_dm_stage2_kg": 200.2,
    "structure_set": "central",
}
"""The keys a case record needs for its entry in the block's structure item (synthetic)."""


def test_block_caveats_and_case_cells_of_a_structural_pass(
    fake_reporting_pass: SimpleNamespace,
) -> None:
    """SP7 step S3a through the pipeline (D-SP7-22): a pass with a structural solved
    case, a penalty row, a plain case, a structure payload case and structural arms
    writes block caveats worded from its records: the structure item names the solved
    case's run and the payload case's run with their modelled masses by stage and layer
    and set, counts the arms (their dm is the arms table's; fix round 2, H-S3a-P2-05), never
    "assumed" of them, and names the plain case as charging none and the penalty row with
    its assumed dry mass (fix round 2, H-S3a-P2-06: from the block's records); the tanks
    item excepts the penalty row's assumed dry mass and the modelled increment; every other
    item is SP1's word for word (the drive is constant_accel); the solved case's "assumed ...
    added" cell says a modelled mass is charged instead, the penalty row's keeps its
    tonnes and the plain case's prints 0; the imposed sub-section is absent (no fixed
    case); the basis line names the two rows that change a dry mass. The same pass
    without a structural record keeps SP1's caveats word for word."""
    cases = [
        ST_CASE,
        {"name": "s1_dry2", "of": "silo_cold", "solve": "stage1", "stage1_dry_mass_added_t": 2.0},
        PLAIN_CASE,
    ]
    _resolved, report = _pass(cases, payload_cases=[PAYLOAD_CASE], sensitivity_of=["s1_st"])
    rec = results_io.offload_record(report)
    by = {c["name"]: c for c in rec["cases"]}
    arms = [a for a in rec["sensitivity"] if a.get("structure_charged")]
    payload = next(p for p in rec["structure_payload_cases"] if p["name"] == "cold_pstar_st")
    assert arms and payload["structure_charged"] is True
    caveats = rec["caveats"]
    assert caveats[0] == summary.offload_calibration_caveat(
        "generic_f9_class_2d", plots.CALIBRATION_RECORDS["generic_f9_class_2d"]
    )
    structure = caveats[1 + summary.OFFLOAD_STRUCTURE_CAVEAT_INDEX]
    assert structure.startswith("the structural cases charge the modelled structural mass")
    st = by["s1_st"]
    layer = f"layer and set {summary.structure_layer_label(st)}"
    assert f"s1_st: {summary.modelled_mass_text(st)}, {layer}" in structure
    assert f"cold_pstar_st: {summary.modelled_mass_text(payload)}, layer and set " in structure
    assert f"; {len(arms)} structural sensitivity arm{'s' if len(arms) > 1 else ''} of s1_st;" in (
        structure
    )
    for arm in arms:
        assert arm["run"] not in structure
    assert structure.endswith(
        f"; s1 charges none ({summary.OFFLOAD_STRUCTURE_UNCHARGED_TEXT}); the penalty row "
        f"s1_dry2 adds {summary.OFFLOAD_STRUCTURE_PENALTY_TEXT}"
    )
    assert "assumed" not in structure.split("; s1 charges none")[0]
    assert caveats[1 + summary.OFFLOAD_TANKS_CAVEAT_INDEX] == (
        summary.OFFLOAD_TANKS_STRUCTURE_PENALTY_CAVEAT
    )
    for i, item in enumerate(caveats[1:]):
        if i not in (summary.OFFLOAD_STRUCTURE_CAVEAT_INDEX, summary.OFFLOAD_TANKS_CAVEAT_INDEX):
            assert item == summary.OFFLOAD_CAVEATS[i], i
    assert rec["basis"] == compare.OFFLOAD_COMPARISON_BASIS
    assert "a structural case's modelled increment" in rec["basis"]
    text = summary.offload_section(rec)
    label = "assumed stage-1 dry mass added [t] (an assumption, not a sized structure)"
    row = _row(text.split(summary.STRUCTURE_SUBSECTION_TITLE)[0], label)
    names = _row(text.split(summary.STRUCTURE_SUBSECTION_TITLE)[0], "quantity")
    cells = dict(zip(names[1:], row[1:], strict=True))
    assert cells["s1_st"] == summary.STRUCTURE_INSTEAD_OF_PENALTY_CELL
    assert cells["s1_dry2"] == summary._fmt(2.0) and cells["s1"] == "0"
    assert summary.OFFLOAD_IMPOSED_SUBSECTION_TITLE not in text
    # the exploratory banner's push caveat from the same record
    push = summary.exploratory_push_caveat(rec)
    assert push.startswith("a modelled structural mass for the push on s1_st and cold_pstar_st (")
    _resolved, plain_report = _pass([PLAIN_CASE, cases[1]], block={})
    plain_rec = results_io.offload_record(plain_report)
    assert plain_rec["caveats"] == summary.offload_caveats(
        "generic_f9_class_2d", plots.CALIBRATION_RECORDS["generic_f9_class_2d"]
    )
    assert summary.exploratory_push_caveat(plain_rec) == (
        "no structural mass for the push except the assumed stage-1 dry mass of the penalty "
        "row s1_dry2 (an assumption, not a sized structure)"
    )


def test_payload_contraction_edge_cases() -> None:
    """``_payload_contraction``: equal sizings give c = 0 (the second pass flew the first's
    vehicle); P_1* = P_ref with a moved sizing is undefined, taken as inf."""
    assert results_io._payload_contraction(10.0, 11.0, 12.0, 5.0, 5.0) == (0.0, 0.0)
    assert results_io._payload_contraction(10.0, 10.0, 12.0, 5.0, 6.0) == (math.inf, math.inf)
    c, r = results_io._payload_contraction(100.0, 90.0, 91.0, 5.0, 4.0)
    assert c == pytest.approx(0.1) and r == pytest.approx(0.1)


# --------------------------------------------------------------- the block-level inputs


def test_structure_inputs_present_only_with_a_block(
    fake_reporting_pass: SimpleNamespace,
    synthetic_file: config.StructureFile,
    synthetic_pad: structure.PadLoadSet,
) -> None:
    """With a block the record carries ``structure_inputs`` after ``energy_inputs`` and
    ``structure_payload_cases`` after ``cases``: the file and its sha256, the envelope per
    element equal to an envelope rebuilt here at the central coefficients (the maximum
    thickness, its station, mode and governing case label), the plausibility table equal
    to ``structure.plausibility`` on the same envelope (M/R and the two end factors), the
    sets as the file records them with their label, ``tornado`` and ``break_even`` None
    with the note saying the file holds neither; without a block the record's keys are
    SP1's, in order, and no key starts with "structure"."""
    _resolved, report = _pass([ST_CASE])
    rec = report.record
    keys = list(rec)
    assert keys.index("structure_inputs") == keys.index("energy_inputs") + 1
    assert keys.index("structure_payload_cases") == keys.index("cases") + 1
    inputs = rec["structure_inputs"]
    assert inputs["file"] == SYNTHETIC_NAME and inputs["sha256"] == synthetic_file.sha256
    assert inputs["envelope_pad"] == "pad" and inputs["reference_payload_kg"] == P_REF
    cfg = synthetic_file.config
    coeffs = cfg.coefficients()
    geometry = structure.build_geometry(
        sim.stack_masses(_resolved.baseline.to_vehicle()), cfg.stack_layout(), coeffs
    )
    envelope = structure.build_envelope(geometry, coeffs, synthetic_pad)
    by = {(e["stage"], e["element"]): e for e in inputs["envelope"]}
    assert len(by) == 7 + 6  # stage 1 with its skirt, stage 2 without
    for (stage, name), e in by.items():
        element = envelope.element(stage, name)
        i = int(element.t_m.argmax())
        assert e["t_max_m"] == float(element.t_m[i]) and e["station_index"] == i
        assert e["mode"] == element.modes[i] and e["z_m"] == float(element.z_m[i])
        case = int(element.case_index[i])
        if case >= 0:
            assert e["case_label"] == synthetic_pad.cases[case].label
            assert e["case_t_s"] == synthetic_pad.cases[case].t_s
        else:
            assert e["case_label"] is None and e["mode"] == structure.MODE_MIN_GAUGE
    check = structure.plausibility(geometry, coeffs, envelope)
    table = inputs["plausibility"]
    assert table["m_model_kg"] == check.m_model_kg and table["relation_kg"] == check.relation_kg
    assert table["ratio"] == check.m_model_kg / check.relation_kg
    assert table["low_mass_end_factor"] == check.favourable_end_factor
    assert table["high_mass_end_factor"] == check.adverse_end_factor
    assert table["element_kg"] == dict(check.element_kg)
    assert table["band_fraction"] == check.band_fraction == coeffs.heineman_band_fraction
    assert table["rule"] == sim.plausibility_rule_text(check.band_fraction)
    assert "D-SP7-33" in table["rule"] and f"{1.0 + check.band_fraction:g} R" in table["rule"]
    assert "0.7 R" not in sim.plausibility_rule_text(0.25) and "0.75 R" in (
        sim.plausibility_rule_text(0.25)
    )
    # the rule's trigger: the element carrying the largest share of M_model, with its
    # envelope's governing mode and case at its thickest station
    dominant = table["dominant"]
    biggest = max(dict(check.element_kg), key=dict(check.element_kg).get)
    assert dominant["element"] == f"stage1.{biggest}"
    assert dominant["share"] == dict(check.element_kg)[biggest] / check.m_model_kg
    assert 0.0 < dominant["share"] < 1.0
    env_element = envelope.element("stage1", biggest)
    j = int(env_element.t_m.argmax())
    assert dominant["mode"] == env_element.modes[j] and dominant["z_m"] == float(env_element.z_m[j])
    case_j = int(env_element.case_index[j])
    assert dominant["case_label"] == (synthetic_pad.cases[case_j].label if case_j >= 0 else None)
    sets = inputs["sets"]
    assert sets["label"] == structure.SEARCH_LABEL == inputs["sets_label"]
    assert sets["evaluation_count"] == cfg.sets.evaluation_count
    assert sets["physics_low_mass"]["values"] == cfg.sets.physics_low_mass.values
    assert inputs["tornado"] is None and inputs["break_even"] is None
    assert inputs["tornado_note"] == sim.STRUCTURE_SETS_NOT_IN_FILE
    json.dumps(results_io.json_safe(results_io.offload_record(report)))
    _plain, plain_report = _pass([PLAIN_CASE], block={})
    plain_keys = list(plain_report.record)
    assert plain_keys == [
        "basis",
        "reference",
        "reference_payload_kg",
        "caveats",
        "energy_inputs",
        "pad_control",
        "pad_controls",
        "cases",
        "sensitivity_basis",
        "sensitivity",
        "notes",
    ]
    assert not [k for k in plain_keys if k.startswith("structure")]
    assert plain_report.increments == {}


def test_structure_block_with_payload_cases_needs_an_offload_block() -> None:
    """A structure block with payload cases and no ``offload`` block is refused when the
    experiment validates (review S3B-C3-01: the payload form runs inside the offload pass,
    so without the block the cases would silently never fly); a block with no payload
    case and no offload block still resolves."""
    exp, veh = tsp._experiment(
        [PLAIN_CASE], block={"file": SYNTHETIC_NAME, "payload_cases": [PAYLOAD_CASE]}
    )
    exp.pop("offload")
    with pytest.raises(ValueError, match="needs an offload: block"):
        tsp._resolve(exp, veh)
    exp_bare, veh_bare = tsp._experiment([PLAIN_CASE], block={"file": SYNTHETIC_NAME})
    exp_bare.pop("offload")
    resolved = tsp._resolve(exp_bare, veh_bare)
    assert resolved.structure is not None and resolved.offload is None


def test_structure_block_needs_the_pads_hold() -> None:
    """The preflight refuses a structure block whose reference pad lights stage 1 at or
    after its hold-down release, before any run directory is created, for the reason the
    refusal states (review N-S3b-R3-02 and its follow-up): such a pad never holds down
    under thrust above its weight, so the skirt's hold-down envelope would lack the
    restrained-thrust case. With the shipped 2 s ramp a pad lit at 0 or 0.5 s does fly
    HOLD rows (the liftoff extension at TWR < 1, which carry the weight alone), so the
    message never claims "no HOLD phase"; it names how the pad lights. The shipped pad
    (lit 2 s before the release) passes, and so does an experiment without a block."""
    exp, veh = tsp._experiment([ST_CASE])
    sim.check_resolved(tsp._resolve(exp, veh))
    for t_ign_s, how in ((0.0, "at its hold-down release"), (0.5, "0.5 s after its hold-down")):
        late, veh_late = tsp._experiment([ST_CASE])
        late["baseline"]["ignition"]["stage1"]["t_ign_s"] = t_ign_s
        resolved = tsp._resolve(late, veh_late)
        with pytest.raises(ValueError, match="never holds down under thrust above its weight"):
            sim.check_resolved(resolved)
        with pytest.raises(ValueError, match="hold-down envelope") as info:
            sim.structure_block_needs_hold(resolved.baseline)
        message = str(info.value)
        assert f"lights stage 1 {how}" in message and "TWR < 1" in message
        assert "restrained-thrust case" in message and "modelling choice" in message
        assert "no HOLD phase" not in message
    plain, veh_plain = tsp._experiment([PLAIN_CASE], block={})
    plain["baseline"]["ignition"]["stage1"]["t_ign_s"] = 0.0
    sim.check_resolved(tsp._resolve(plain, veh_plain))  # no block: no hold needed


# ------------------------------------------------------------------ the subsection


def test_structure_subsection_rows_trace_to_the_record(
    fake_reporting_pass: SimpleNamespace,
) -> None:
    """The Structure subsection of a pass with a central case, an unscaled and a
    plausibility-scaled low-mass case, a central case with design-axis overrides, a
    no_offload case (quasi-static), a penalty row, a low-mass case with design-axis
    overrides, a full_load case, a low-mass case and a central case at margin 0.1, a
    low-mass case at entry thrust_structure, a central case at margin 0.05 whose solve
    finds no x* (search_failed), three payload cases (central rise-time,
    central quasi-static, scaled low-mass) and structural arms: every STRUCTURE_CASE_ROWS
    label and every STRUCTURE_PAYLOAD_ROWS label is printed; the cells recomputed from the
    record (dm1 = dm - dm2, F_peak in MN, the DLF, the penalty row's tonnes with n/a
    elsewhere, the fired flags, the no_offload column's x* and share cells never "0 t" or
    0, the layer cells by D-SP7-18 and design 4.2.6: the central label only at the headline
    settings, "design axis (layer 2)" for overrides, a margin or another dynamic mode, "a
    row, not a band end" for the entry path or the sizing basis, the overrides row, the
    factor cell a number on the physics-set cases and "n/a (not a band end)" on the
    central ones); the flight-check row's short label naming the element scope, its
    qualifications in the note under the table; the no_offload line prints the solver's
    shortfall and the payload deficit of the payload case of the same settings, naming
    what differs otherwise; the physics band line names each end from the headline-settings
    cases only and prints the unscaled end and the scaled end side by side with the factor,
    in either order of the cases (D-SP7-41), never a case with overrides, a margin or
    another entry, which the layer-2 line and the settings-rows line name with its set,
    what it moves and its x* (a solve without one as "no x*" with its status, never "n/a
    t"); the break-even, the where-found and the applicability lines;
    the central element table's labels and sums (the thrust structure "not in the load
    path" under entry aft_ring; the override case never the central table); the
    plausibility table's M/R, band edges and trigger line; the payload table's settings
    rows and its heading naming, per payload case, the full_load row of the same variant
    and settings (or that none ran) and that they offload nothing; the arms line and
    deviation 17's caveat as its own bullet, and the caveat under the arms table; the
    figures named; a uniform cell count per table; ASCII; nothing of it without a block."""
    cases = [
        ST_CASE,
        {
            **ST_CASE,
            "name": "s1_lo_sc",
            "structure": {"set": "physics_low_mass", "plausibility_scaled": True},
        },
        {**ST_CASE, "name": "s1_none", "structure": {"dynamic": "quasi_static"}},
        {"name": "s1_dry2", "of": "silo_cold", "solve": "stage1", "stage1_dry_mass_added_t": 2.0},
        {**ST_CASE, "name": "s1_lo", "structure": {"set": "physics_low_mass"}},
        {**ST_CASE, "name": "s1_ov", "structure": {"overrides": {"nof.nof_barrel": 1.54}}},
        {
            **ST_CASE,
            "name": "s1_lo_nof",
            "structure": {"set": "physics_low_mass", "overrides": {"nof.nof_barrel": 1.54}},
        },
        {**ST_CASE, "name": "s1_full", "structure": {"sizing": "full_load"}},
        {**ST_CASE, "name": "s1_lo_m10", "structure": {"set": "physics_low_mass", "margin": 0.1}},
        {**ST_CASE, "name": "s1_m10", "structure": {"margin": 0.1}},
        {
            **ST_CASE,
            "name": "s1_lo_ts",
            "structure": {"set": "physics_low_mass", "entry": "thrust_structure"},
        },
        {**ST_CASE, "name": "s1_fail", "structure": {"margin": 0.05}},
    ]
    fake_reporting_pass.no_offload.add("s1_none")
    fake_reporting_pass.fail.add("s1_fail")  # a design-axis case whose solve finds no x*
    payload_qs = {**PAYLOAD_CASE, "name": "cold_pstar_qs", "dynamic": "quasi_static"}
    payload_sc = {
        **PAYLOAD_CASE,
        "name": "cold_pstar_sc",
        "set": "physics_low_mass",
        "plausibility_scaled": True,
    }
    _resolved, report = _pass(
        cases, payload_cases=[PAYLOAD_CASE, payload_qs, payload_sc], sensitivity_of=["s1_st"]
    )
    rec = results_io.offload_record(report)
    by = {c["name"]: c for c in rec["cases"]}
    text = summary.offload_section(rec)
    assert all(line.isascii() for line in text.splitlines())
    section = text.split(summary.STRUCTURE_SUBSECTION_TITLE)[1].split("### Decomposition")[0]
    for label, _fmt, _key in (*summary.STRUCTURE_CASE_ROWS, *summary.STRUCTURE_PAYLOAD_ROWS):
        assert f"| {label} |" in section, label
    case_part, payload_part = section.split("Structure payload cases")
    header = _row(case_part, "quantity")
    names = [
        "s1_st",
        "s1_lo_sc",
        "s1_none",
        "s1_dry2",
        "s1_lo",
        "s1_ov",
        "s1_lo_nof",
        "s1_full",
        "s1_lo_m10",
        "s1_m10",
        "s1_lo_ts",
        "s1_fail",
    ]
    assert header[1:] == names
    section = case_part  # the case table, the band lines and the element and plausibility tables
    st = by["s1_st"]
    rows_by_key = {key: label for label, _f, key in summary.STRUCTURE_CASE_ROWS if key}

    def cell(label: str, name: str) -> str:
        """The case table's cell at a row label and a case name."""
        return _row(section, label)[1 + names.index(name)]

    dm1 = _row(section, "dm1, stage 1 with the interstage, at x* [kg] (a no_offload end: at x = 0)")
    assert dm1[1] == summary._fmt(st["structure_dm_kg"] - st["structure_dm_stage2_kg"])
    assert dm1[4] == "n/a"
    f_peak = _row(section, "F_peak, the peak interface force [MN]")
    assert f_peak[1] == summary._fmt(float(n_to_mn(st["structure_F_peak_N"])))
    assert _row(section, "  dynamic load factor DLF")[1] == summary._fmt(st["structure_dlf"])
    penalty = _row(section, summary.STRUCTURE_PENALTY_ROW_LABEL)
    two_t = summary._fmt(float(kg_to_t(2000.0)))
    # SP7 step S3a: a structural case's "assumed ... added" cell says what the run carries
    # instead of printing 0 under "assumed" (STRUCTURE_INSTEAD_OF_PENALTY_CELL); the penalty
    # row keeps its tonnes
    instead = summary.STRUCTURE_INSTEAD_OF_PENALTY_CELL
    assert penalty[1:] == [instead] * 3 + [two_t] + [instead] * 8
    assert "assumed" not in instead and "modelled structural mass" in instead
    kind = _row(section, "kind")
    assert kind[1] == summary.STRUCTURE_KIND_MODELLED and kind[4] == summary.STRUCTURE_KIND_PENALTY
    layer_label = "layer and set (D-SP7-18)"
    assert cell(layer_label, "s1_st") == (
        "central (every coefficient at its central value): central"
    )
    assert cell(layer_label, "s1_lo_sc") == "physics band, low-mass end: physics_low_mass"
    assert cell(layer_label, "s1_lo") == "physics band, low-mass end: physics_low_mass"
    assert cell(layer_label, "s1_ov") == (
        "design axis (layer 2): central with overrides nof.nof_barrel 1.54"
    )
    assert cell(layer_label, "s1_lo_nof") == (
        "design axis (layer 2): physics_low_mass with overrides nof.nof_barrel 1.54"
    )
    assert cell(layer_label, "s1_dry2") == "n/a"
    # D-SP7-18, design 4.2.6: a margin, a cap and the dynamic mode are design axes (layer
    # 2); the entry path and the sizing basis are rows, not band; the central layer-1
    # label only at the headline settings
    assert cell(layer_label, "s1_none") == "design axis (layer 2): central at dynamic quasi_static"
    assert cell(layer_label, "s1_lo_m10") == "design axis (layer 2): physics_low_mass at margin 0.1"
    assert cell(layer_label, "s1_m10") == "design axis (layer 2): central at margin 0.1"
    assert cell(layer_label, "s1_fail") == "design axis (layer 2): central at margin 0.05"
    assert cell(layer_label, "s1_full") == (
        "central (every coefficient at its central value), a row, not a band end "
        "(sizing full_load): central"
    )
    assert cell(layer_label, "s1_lo_ts") == (
        "physics band, low-mass end, a row, not a band end (entry thrust_structure): "
        "physics_low_mass"
    )
    assert "central (every coefficient" not in cell(layer_label, "s1_m10")
    assert summary.structure_layer_label(
        {**by["s1_lo_m10"], "structure_envelope_cap_g": 1.5, "structure_entry": "thrust_structure"}
    ) == (
        "design axis (layer 2): physics_low_mass at margin 0.1, cap 1.5 g0; entry "
        "thrust_structure (a row, not a band end)"
    )
    # an outer set records its own margin and cap: neither counts as a departure
    outer = {**by["s1_lo"], "structure_set": "outer_high_mass", "structure_envelope_cap_g": 4.0}
    assert summary.structure_is_band_end(outer) and summary.structure_axis_departures(outer) == []
    assert not summary.structure_is_band_end(by["s1_lo_m10"])
    assert not summary.structure_is_band_end(by["s1_lo_ts"])
    assert not summary.structure_is_band_end(by["s1_st"])  # central: never an end
    assert summary.structure_is_band_end(by["s1_lo"]) and summary.structure_is_band_end(
        by["s1_lo_sc"]
    )
    overrides = _row(section, "design-axis overrides (path value; none)")
    assert overrides[1:] == [
        "none",
        "none",
        "none",
        "n/a",
        "none",
        "nof.nof_barrel 1.54",
        "nof.nof_barrel 1.54",
        "none",
        "none",
        "none",
        "none",
        "none",
    ]
    assert by["s1_ov"]["structure_overrides"] == {"nof.nof_barrel": 1.54}
    assert by["s1_ov"]["structure_dm_kg"] != st["structure_dm_kg"]  # the override sized it
    scaled = _row(section, "plausibility-scaled (the dm carries the rule's factor)")
    assert scaled[1:] == ["False", "True", "False", "n/a"] + ["False"] * 8
    factor_label = next(
        label
        for label, _f, key in summary.STRUCTURE_CASE_ROWS
        if key == "structure_plausibility_factor"
    )
    assert "a central or design-axis case is not a band end and prints n/a" in factor_label
    f_lo = by["s1_lo_sc"]["structure_plausibility_factor"]
    for name in ("s1_lo_sc", "s1_lo", "s1_lo_nof", "s1_lo_m10", "s1_lo_ts"):
        assert cell(factor_label, name) == summary._fmt(f_lo) != "1", name
    for name in ("s1_st", "s1_none", "s1_ov", "s1_full", "s1_m10", "s1_fail"):
        assert cell(factor_label, name) == "n/a (not a band end)", name
    assert cell(factor_label, "s1_dry2") == "n/a"
    assert by["s1_lo"]["structure_plausibility_factor"] == f_lo
    assert by["s1_lo_sc"]["structure_dm_kg"] < by["s1_lo"]["structure_dm_kg"]
    xstar = _row(section, "x* [t]")
    assert (
        xstar[1] == summary._fmt(float(kg_to_t(X_FAKE)))
        and xstar[3] == summary.STRUCTURE_NO_OFFLOAD_CELL
    )
    share = _row(section, "  % of the stage-1 load")
    assert share[3] == summary.STRUCTURE_NO_OFFLOAD_CELL and share[1] != "0"
    assert share[1] == summary._fmt(100.0 * by["s1_st"]["stage1_fraction"])
    assert "0 t" not in xstar[3] and "0 t" not in share[3]
    # the search_failed case: a bare n/a in the x* and share cells, never a unit on it
    assert cell("x* [t]", "s1_fail") == "n/a"
    assert cell("  % of the stage-1 load", "s1_fail") == "n/a"
    assert cell("status (the solve)", "s1_fail") == "search_failed"
    assert "n/a t" not in section
    flags = _row(section, "structure flags fired (their numbers are in structure_flags)")
    fired = [f["name"] for f in st["structure_flags"] if f["fired"]]
    assert flags[1] == "; ".join(fired) and flags[4] == "n/a"
    assert cell(flags[0], "s1_fail") == summary.STRUCTURE_FLAGS_NOT_SIZED
    # a search_failed case: no sizing at x*, so no flag was evaluated (never "none")
    failed_text = summary.structure_flags_text(
        {**st, "structure_dm_kg": None, "structure_flags": []}
    )
    assert failed_text == summary.STRUCTURE_FLAGS_NOT_SIZED and "n/a" in failed_text
    assert summary.structure_flags_text({**st, "structure_flags": []}) == "none"
    flight_label = rows_by_key["structure_flight_exceedance_kg"]
    flight = _row(section, flight_label)
    assert flight[1] == "n/a"  # the fake run has no time series to check
    assert flight_label == summary.STRUCTURE_FLIGHT_CHECK_ROW_LABEL and len(flight_label) < 160
    assert summary.STRUCTURE_FLIGHT_CHECK_SCOPE_SHORT in flight_label  # the scope, in short
    assert "not the aft skirt or the ring" in flight_label and "see the note" in flight_label
    assert summary.STRUCTURE_FLIGHT_CHECK_SCOPE not in flight_label  # the full sentence: the note
    assert "[kg]" in flight_label and "capped" not in flight_label
    assert all(len(label) < 160 for label, _f, _k in summary.STRUCTURE_CASE_ROWS)
    (note,) = [ln for ln in section.splitlines() if ln.startswith("- flight check (the row above)")]
    assert note == f"- {summary.STRUCTURE_FLIGHT_CHECK_NOTE}"
    assert "capped as the envelope's was" in note and "the unscaled sizing" in note
    assert "unfactored against the envelope at the case's margin" in note
    assert summary.STRUCTURE_FLIGHT_CHECK_SCOPE in note
    assert "not applicable to a structure payload case" in note
    none = by["s1_none"]
    assert none["status"] == NO_OFFLOAD_STATUS and none["offload_kg"] == 0.0
    (line,) = [ln for ln in section.splitlines() if ln.startswith("- s1_none: no offload at P_ref")]
    assert f"falls short of P_ref by {summary._fmt(SHORTFALL_MPS)} m/s of delta-v" in line
    assert f"carrying dm {summary._fmt(none['structure_dm_kg'])} kg" in line
    p, p_qs, p_sc = rec["structure_payload_cases"]
    assert p["name"] == "cold_pstar_st" and p_qs["name"] == "cold_pstar_qs"
    assert p_sc["name"] == "cold_pstar_sc" and p_sc["structure_plausibility_scaled"] is True
    deficit = summary._signed(p_qs["payload_delta_kg"])
    assert f"payload deficit at the full load {deficit} kg" in line
    assert "structure payload case cold_pstar_qs, the same set and settings" in line
    assert "cold_pstar_st, the same set" not in line  # rise_time: not the same settings
    (band,) = [ln for ln in section.splitlines() if ln.startswith("- physics band (layer 1)")]
    low_t = summary._fmt(float(kg_to_t(X_FAKE)))
    assert band.startswith(
        f"- physics band (layer 1): x* at the low-mass end [{low_t} t (s1_lo, status ok); "
        f"plausibility-scaled end: {low_t} t (s1_lo_sc, status ok), factor {summary._fmt(f_lo)}]; "
        "at the high-mass end [not flown]; the sets are "
    )
    # only the headline-settings cases are ends: never an override, a margin or an entry row
    for name in ("s1_lo_nof", "s1_lo_m10", "s1_lo_ts", "s1_m10", "s1_none", "s1_full"):
        assert name not in band, name
    assert (
        "- outer envelope (layer 3): x* at the low-mass end [not flown]; at the high-mass end "
        "[not flown]" in section
    )
    assert f"- design-axis break-even values (layer 2): {sim.STRUCTURE_SETS_NOT_IN_FILE}" in section
    (layer2,) = [
        ln
        for ln in section.splitlines()
        if ln.startswith(f"- {summary.STRUCTURE_LAYER2_ROWS_LABEL}")
    ]
    assert (
        f"s1_lo_nof (physics_low_mass at overrides nof.nof_barrel 1.54): x* {low_t} t "
        "(s1_lo_nof, status ok)" in layer2
    )
    assert f"s1_ov (central at overrides nof.nof_barrel 1.54): x* {low_t} t (s1_ov, status ok)" in (
        layer2
    )
    assert f"s1_lo_m10 (physics_low_mass at margin 0.1): x* {low_t} t (s1_lo_m10, status ok)" in (
        layer2
    )
    assert f"s1_m10 (central at margin 0.1): x* {low_t} t (s1_m10, status ok)" in layer2
    assert "s1_none (central at dynamic quasi_static): no offload (s1_none;" in layer2
    # a search_failed design-axis case: "no x*" with its status, never "x* n/a t" (NEW-H-01)
    assert "s1_fail (central at margin 0.05): no x* (s1_fail, status search_failed)" in layer2
    assert "x* no" not in layer2 and "n/a t" not in layer2 and "x* n/a" not in layer2
    assert "never a band end" in layer2 and "s1_lo " not in layer2 and "s1_st" not in layer2
    assert "s1_lo_ts" not in layer2 and "s1_full" not in layer2  # rows, not design axes
    failed_end = summary._xstar_text({**by["s1_fail"], "name": "lo_fail"})
    assert failed_end == "no x* (lo_fail, status search_failed)"
    assert summary._xstar_phrase(by["s1_lo"]) == f"x* {low_t} t (s1_lo, status ok)"
    (settings_rows,) = [
        ln
        for ln in section.splitlines()
        if ln.startswith(f"- {summary.STRUCTURE_SETTINGS_ROWS_LABEL}")
    ]
    assert (
        f"s1_lo_ts (physics_low_mass at entry thrust_structure): x* {low_t} t (s1_lo_ts, "
        "status ok)" in settings_rows
    )
    assert "never a band end" in settings_rows and "s1_full" not in settings_rows  # central
    assert "s1_lo_m10" not in settings_rows and "s1_lo " not in settings_rows
    # an unscaled physics end whose rule fired, with no scaled twin: the factor is named
    only_unscaled = {**rec, "cases": [c for c in rec["cases"] if c["name"] != "s1_lo_sc"]}
    (band_un,) = [
        ln
        for ln in summary.structure_section(only_unscaled).splitlines()
        if ln.startswith("- physics band (layer 1)")
    ]
    assert (
        f"[{low_t} t (s1_lo, status ok); the rule's factor on this end is {summary._fmt(f_lo)}; "
        "no plausibility-scaled case was flown]" in band_un
    )
    assert "the rule's factor on this end" not in band  # the scaled twin stands beside it
    assert structure.SEARCH_LABEL in section
    method = rec["structure_inputs"]["sets"]["method"]
    found = "- where the sets were found (the file's sets.method; sizing only, at one push): "
    assert f"{found}{method}" in section
    assert f"- applicability: {summary.STRUCTURE_SETS_APPLICABILITY}" in section
    assert "the headline's sets applied to this push" in section
    assert "each x* above is this experiment's own solve with that set" in section
    assert "as sizing-only estimates" not in section
    # the same band line whichever order the cases come in (the scaled case first above)
    swapped = {**rec, "cases": [by["s1_lo"], *[c for c in rec["cases"] if c["name"] != "s1_lo"]]}
    assert band in summary.structure_section(swapped)
    only_scaled = {**rec, "cases": [c for c in rec["cases"] if c["name"] != "s1_lo"]}
    assert (
        f"x* at the low-mass end [scaled only: {low_t} t (s1_lo_sc, status ok), factor "
        f"{summary._fmt(f_lo)}; the unscaled end was not flown]; at the high-mass end [not flown]"
        in summary.structure_section(only_scaled)
    )
    without_layer2 = {
        **rec,
        "cases": [
            c
            for c in rec["cases"]
            if c["name"] not in ("s1_ov", "s1_lo_nof", "s1_lo_m10", "s1_m10", "s1_none", "s1_fail")
        ],
    }
    assert summary.STRUCTURE_LAYER2_ROWS_LABEL not in summary.structure_section(without_layer2)
    without_rows = {**rec, "cases": [c for c in rec["cases"] if c["name"] != "s1_lo_ts"]}
    assert summary.STRUCTURE_SETTINGS_ROWS_LABEL not in summary.structure_section(without_rows)
    assert "Elements of the central case s1_st at x* (the station-sized" in section
    elements = section.split("Pad envelope per element")[0]  # the central element table
    closed = _row(elements, "station-sized and relation elements, sum")
    assert closed[1] == summary._fmt(st["structure_closed_form_kg"])
    assert _row(elements, "ring frame, sum")[1] == summary._fmt(st["structure_ring_kg"])
    assert _row(elements, "dm1 + dm2")[1] == summary._fmt(st["structure_dm_kg"])
    assert _row(elements, "stage1.interstage")[2] == summary.STRUCTURE_ELEMENT_HOW["interstage"]
    assert "Gerard exponent" in _row(elements, "stage1.interstage")[2]
    # under entry aft_ring the thrust structure is not in the load path: no relation quoted
    ts_row = _row(elements, "stage1.thrust_structure")
    assert ts_row[1] == "0" and ts_row[2] == summary.STRUCTURE_ELEMENT_NOT_IN_PATH["aft_ring"]
    assert "k_ts" not in ts_row[2] and "not in the load path on entry aft_ring" in ts_row[2]
    assert _row(elements, "stage1.lox_barrel")[2] == summary.STRUCTURE_ELEMENT_STATION_HOW
    assert _row(elements, "stage1.load_ring")[2] == summary.STRUCTURE_ELEMENT_RING_HOW
    assert "closed form over the pad envelope" not in section
    # under entry thrust_structure the relation is quoted as applied and the ring is not
    # in the load path
    ts_table = summary._element_table(by["s1_lo_ts"])
    ts_how = _row(ts_table, "stage1.thrust_structure")[2]
    assert ts_how == summary.STRUCTURE_ELEMENT_HOW["thrust_structure"]
    assert "k_ts max(0, F_peak + T - (1 + margin) T_max)" in ts_how
    assert (
        _row(ts_table, "stage1.load_ring")[2]
        == (summary.STRUCTURE_ELEMENT_NOT_IN_PATH["thrust_structure"])
    )
    # the element table and the trigger name a fallback central case as the central-set
    # case with what it moves, never as the central case
    fallback = {**rec, "cases": [c for c in rec["cases"] if c["name"] in ("s1_m10", "s1_dry2")]}
    fallback_text = summary.structure_section(fallback)
    assert "Elements of the central-set case s1_m10 (margin 0.1; not the headline settings)" in (
        fallback_text
    )
    assert "its own push increment in the central-set case s1_m10 (margin 0.1; not" in (
        fallback_text
    )
    assert "the central case s1_m10" not in fallback_text
    ratio = _row(section, "M_model / R")
    plaus = rec["structure_inputs"]["plausibility"]
    assert (
        ratio[1] == summary._fmt(plaus["ratio"]) == summary._fmt(st["structure_plausibility_ratio"])
    )
    band_fraction = plaus["band_fraction"]
    hi, lo = f"{1.0 + band_fraction:g}", f"{1.0 - band_fraction:g}"
    assert _row(section, f"  band, upper edge ({hi} R)")[1] == summary._fmt(plaus["upper_kg"])
    assert _row(section, f"  band, lower edge ({lo} R)")[1] == summary._fmt(plaus["lower_kg"])
    (trigger,) = [ln for ln in section.splitlines() if ln.startswith("- trigger: ")]
    d = plaus["dominant"]
    assert f"M_model / R = {summary._fmt(plaus['ratio'])} lies above {hi} R" in trigger
    assert f"{d['element']} carries {summary._fmt(100.0 * d['share'])} % of M_model" in trigger
    assert f"governed by {d['mode']} under load case {d['case_label']}" in trigger
    own = st["structure_elements"][d["element"]]
    assert f"its own push increment in the central case s1_st: {summary._fmt(own)} kg" in trigger
    pay = _row(
        payload_part,
        "contraction c = abs((P_2* - P_1*)/(dm_1 - dm_0)) x abs((dm_1 - dm_0)/(P_1* - P_ref))",
    )
    assert pay[1] == f"{p['contraction']:.3g}"
    dm_0 = _row(payload_part, "dm_0 [kg] (sized at P_ref on the full-load vehicle)")
    assert dm_0[1] == summary._fmt(p["dm_0_kg"])
    assert dm_0[1] == _row(section, "dm1 + dm2 at x = 0 [kg]")[1]  # the offload case's x = 0
    assert _row(payload_part, "quantity")[1:] == ["cold_pstar_st", "cold_pstar_qs", "cold_pstar_sc"]
    assert _row(payload_part, "status (the P_2* search's: ok, or the failed search's status)")[
        1:
    ] == ["ok", "ok", "ok"]
    # the settings rows of the payload table: what sized dm_0 and dm_1, per case
    assert _row(payload_part, "layer and set (D-SP7-18)")[1:] == [
        "central (every coefficient at its central value): central",
        "design axis (layer 2): central at dynamic quasi_static",
        "physics band, low-mass end: physics_low_mass",
    ]
    assert _row(payload_part, "dynamic mode")[1:] == ["rise_time", "quasi_static", "rise_time"]
    assert _row(payload_part, "  dynamic load factor DLF")[1:] == [
        summary._fmt(p["structure_dlf"]),
        "1",
        summary._fmt(p_sc["structure_dlf"]),
    ]
    assert _row(payload_part, "load entry")[1:] == ["aft_ring"] * 3
    assert _row(payload_part, "margin on the envelope's loads and pressures")[1:] == ["0"] * 3
    assert _row(payload_part, "design-axis overrides (path value; none)")[1:] == ["none"] * 3
    assert (
        _row(payload_part, "sizing basis (a payload case: full_load, once at the full load)")[1:]
        == ["full_load"] * 3
    )
    assert _row(payload_part, "plausibility-scaled (dm_0 and dm_1 carry the rule's factor)")[
        1:
    ] == ["False", "False", "True"]
    assert _row(payload_part, factor_label)[1:] == [
        "n/a (not a band end)",
        "n/a (not a band end)",
        summary._fmt(f_lo),
    ]
    assert _row(
        payload_part, "  M_model / R (the model's envelope tank mass over Heineman's relation)"
    )[3] == summary._fmt(p_sc["structure_plausibility_ratio"])
    assert _row(payload_part, "F_peak, the peak interface force [MN] (at P_1*)")[1] == (
        summary._fmt(float(n_to_mn(p["structure_F_peak_N"])))
    )
    assert p_sc["dm_1_kg"] < p["dm_1_kg"]  # the scaled set's mass, read with its factor
    # the flight check is not run on a payload case: the row says so, no flag, the key None
    flight_row = _row(
        payload_part, "flight check: the recorded run's own flight over the pad envelope"
    )
    assert flight_row[1:] == [summary.STRUCTURE_PAYLOAD_FLIGHT_CHECK_NA] * 3
    assert "not applicable" in summary.STRUCTURE_PAYLOAD_FLIGHT_CHECK_NA
    heading = payload_part.splitlines()[0]
    assert (
        "read beside the full_load row of the same variant and settings above: cold_pstar_st: "
        f"s1_full; cold_pstar_qs: {summary.STRUCTURE_PAYLOAD_NO_FULL_LOAD}; cold_pstar_sc: "
        f"{summary.STRUCTURE_PAYLOAD_NO_FULL_LOAD};" in heading
    )
    assert summary.STRUCTURE_PAYLOAD_OFFLOADS_NOTHING in heading
    no_full = {**rec, "cases": [c for c in rec["cases"] if c["name"] != "s1_full"]}
    assert f"cold_pstar_st: {summary.STRUCTURE_PAYLOAD_NO_FULL_LOAD}" in (
        summary.structure_section(no_full)
    )
    tail = payload_part
    assert (
        "- structural sensitivity arms: 4 (the Sensitivity table below carries their dm, set "
        "and envelope pad; the caveat follows)\n- " + sim.STRUCTURE_ARM_CAVEAT in tail
    )
    assert tail.count("structural sensitivity arms:") == 2  # the count line, then the caveat
    assert tail.count("structural sensitivity arms: 4 (") == 1
    assert "+10.4 kg of dm" in sim.STRUCTURE_ARM_CAVEAT
    assert "the unchanged pad for a run parameter" in sim.STRUCTURE_ARM_CAVEAT
    assert sim.STRUCTURE_ARM_CAVEAT is summary.STRUCTURE_ARM_CAVEAT
    assert f"- {summary.STRUCTURE_FIGURES_TEXT}: " in tail
    assert "where the push sized stage 2" in summary.STRUCTURE_FIGURES_TEXT
    for run in (
        "s1_st",
        "s1_lo_sc",
        "s1_none",
        "s1_lo",
        "s1_ov",
        "s1_lo_nof",
        "s1_full",
        "s1_lo_m10",
        "s1_m10",
        "s1_lo_ts",
        "cold_pstar_st",
        "cold_pstar_qs",
        "cold_pstar_sc",
    ):
        assert f"plots/{run}_structure.png" in tail
    assert "plots/s1_dry2_structure.png" not in tail
    for block in text.split("\n\n"):
        rows = _table_rows(block)
        if rows:
            assert len({len(r) for r in rows}) == 1, block.splitlines()[0]
    arms_table = text.split("### Sensitivity")[1]
    for column in summary.STRUCTURE_ARM_COLUMNS:
        assert column in arms_table
    assert f"- {sim.STRUCTURE_ARM_CAVEAT}" in arms_table
    for arm in rec["sensitivity"]:
        dm, pad = summary._fmt(arm["structure_dm_kg"]), arm["structure_envelope_pad"]
        assert f"| {dm} | central | {pad} |" in arms_table
    assert arms_table.count("structural sensitivity arms:") == 1
    # an arm that was never solved (its pad has no P*) is not called uncharged; an arm of
    # an unstructured case is
    failed_arm = {**rec["sensitivity"][0], "status": "reference_failed", "offload_kg": None}
    failed_arm = {k: v for k, v in failed_arm.items() if not k.startswith("structure")}
    plain_arm = {**failed_arm, "status": "ok", "offload_kg": 1.0}
    mixed = summary.offload_sensitivity_table([*rec["sensitivity"], failed_arm, plain_arm])
    assert "| n/a (not solved: reference_failed) | n/a | n/a |" in mixed
    assert "| n/a (uncharged) | n/a | n/a |" in mixed
    _plain, plain_report = _pass([PLAIN_CASE], block={}, sensitivity_of=["s1"])
    plain_text = summary.offload_section(results_io.offload_record(plain_report))
    assert summary.STRUCTURE_SUBSECTION_TITLE not in plain_text
    assert sim.STRUCTURE_ARM_CAVEAT not in plain_text
    assert not any(c in plain_text for c in summary.STRUCTURE_ARM_COLUMNS)
    assert summary.structure_section({"cases": []}) == ""


def test_no_offload_line_without_a_payload_case_says_not_flown(
    fake_reporting_pass: SimpleNamespace,
) -> None:
    """A no_offload structural case with no payload case of its set prints the shortfall
    and "not flown" for the payload deficit (D-SP7-32: never "0 t"); with a payload case
    of the same set whose settings differ (a quasi-static one against a rise-time case)
    it still says "not flown" and names what differs instead of quoting that case."""
    fake_reporting_pass.no_offload.add("s1_st")
    _resolved, report = _pass([ST_CASE])
    text = summary.offload_section(results_io.offload_record(report))
    (line,) = [ln for ln in text.splitlines() if ln.startswith("- s1_st: no offload at P_ref")]
    assert f"payload deficit at the full load {summary.STRUCTURE_NOT_FLOWN}" in line
    assert "no structure payload case of the same set and settings" in line
    assert "0 t" not in line and f"{summary._fmt(SHORTFALL_MPS)} m/s" in line
    assert "[no offload (s1_st; the no_offload line below)" not in text  # central: no band end
    assert summary.STRUCTURE_NO_OFFLOAD_CELL in text
    payload_qs = {**PAYLOAD_CASE, "name": "cold_pstar_qs", "dynamic": "quasi_static"}
    _resolved2, report2 = _pass([ST_CASE], payload_cases=[payload_qs])
    text2 = summary.offload_section(results_io.offload_record(report2))
    (line2,) = [ln for ln in text2.splitlines() if ln.startswith("- s1_st: no offload at P_ref")]
    assert f"payload deficit at the full load {summary.STRUCTURE_NOT_FLOWN} for these settings" in (
        line2
    )
    assert "cold_pstar_qs is of the same set but differs in dynamic)" in line2
    (p_qs,) = report2.record["structure_payload_cases"]
    assert summary._signed(p_qs["payload_delta_kg"]) not in line2


# ------------------------------------------------------------------ the sweep columns


def _sweep(root: Path, offload: list[dict[str, dict[str, Any]]]) -> results_io.SweepResult:
    point = SimpleNamespace(point_index=1, overrides={"assist.stroke_m": 100})
    rr = SimpleNamespace(name="run_0001", result=SimpleNamespace(metrics={}, status="inserted"))
    return results_io.SweepResult(
        1,
        "silo_cold",
        ["assist.stroke_m"],
        [point] * len(offload),
        [rr] * len(offload),
        [{}] * len(offload),  # type: ignore[list-item]
        [root / "sweep_1" / "run_0001"] * len(offload),
        [None] * len(offload),
        offload,
        [{} for _ in offload],
    )


def test_sweep_structure_columns_only_for_a_structural_case(
    fake_reporting_pass: SimpleNamespace, tmp_path: Path
) -> None:
    """The sweep index: a point's structural case record adds ``<case>.<column>`` for
    OFFLOAD_STRUCTURE_SWEEP_COLUMNS after every case's OFFLOAD_SWEEP_COLUMNS group and
    before ``status`` (its values from the record: the set, the cap None, dm, the fired
    flags joined); an unstructured case of the same sweep gets none; a sweep with no
    structural record keeps exactly the columns of SP1 (the KI-028 pattern)."""
    _resolved, report = _pass([PLAIN_CASE, ST_CASE])
    by = {c["name"]: c for c in report.record["cases"]}
    plain, st = by["s1"], by["s1_st"]
    base = results_io.planar_sweep_index_frame(_sweep(tmp_path, [{"s1": plain}]), tmp_path)
    plain_cols = [f"s1.{c}" for c in results_io.OFFLOAD_SWEEP_COLUMNS]
    assert [c for c in base.columns if "." in c and c.startswith("s1")] == plain_cols
    assert not [c for c in base.columns if "structure" in c]
    frame = results_io.planar_sweep_index_frame(
        _sweep(tmp_path, [{"s1": plain, "s1_st": st}]), tmp_path
    )
    expected = [
        *plain_cols,
        *[f"s1_st.{c}" for c in results_io.OFFLOAD_SWEEP_COLUMNS],
        *[f"s1_st.{c}" for c in results_io.OFFLOAD_STRUCTURE_SWEEP_COLUMNS],
    ]
    cols = list(frame.columns)
    assert cols[cols.index("s1.status") : cols.index("status")] == expected
    row = frame.iloc[0]
    assert row["s1_st.structure_set"] == "central" and row["s1_st.structure_sizing"] == "flown"
    assert pd.isna(row["s1_st.structure_cap_g"]) and row["s1_st.structure_margin"] == 0.0
    assert row["s1_st.structure_dm_kg"] == st["structure_dm_kg"]
    assert row["s1_st.structure_dm_x0_kg"] == st["structure_dm_x0_kg"]
    assert row["s1_st.structure_n_peak_g"] == st["structure_n_peak_g"]
    # the central set is not a band end: the factor column is empty, never a 1.0 that
    # would read as "the rule did not fire"; M/R is on every point
    assert pd.isna(row["s1_st.structure_plausibility_factor"])
    assert row["s1_st.structure_plausibility_ratio"] == st["structure_plausibility_ratio"] > 1.0
    fired = [f["name"] for f in st["structure_flags"] if f["fired"]]
    assert row["s1_st.structure_flags"] == "; ".join(fired)
    assert not row["s1_st.structure_plausibility_scaled"]
    assert row["s1_st.structure_overrides"] == "none"
    assert results_io.offload_structure_index_values(plain) == dict.fromkeys(
        results_io.OFFLOAD_STRUCTURE_SWEEP_COLUMNS
    )
    # a point where the case failed keeps its structural columns with None at x*; its
    # flags column says no sizing was made, never "none"
    failed = {**st, "structure_dm_kg": None, "structure_flags": []}
    values = results_io.offload_structure_index_values(failed)
    assert values["structure_dm_kg"] is None
    assert values["structure_flags"] == summary.STRUCTURE_FLAGS_NOT_SIZED
    # a scaled case with overrides records its basis: the factor applied, the overrides
    based = {
        **st,
        "structure_set": "physics_low_mass",
        "structure_plausibility_factor": 0.85,
        "structure_plausibility_scaled": True,
        "structure_overrides": {"ring.ring_pads": 4, "nof.nof_barrel": 1.54},
    }
    values = results_io.offload_structure_index_values(based)
    assert values["structure_plausibility_scaled"] is True
    assert values["structure_plausibility_factor"] == 0.85  # a physics end: the factor
    assert values["structure_overrides"] == "nof.nof_barrel 1.54; ring.ring_pads 4"
    assert (
        results_io.offload_structure_index_values({**based, "structure_set": "outer_low_mass"})[
            "structure_plausibility_factor"
        ]
        is None
    )
    assert (
        results_io.offload_structure_index_values({**st, "structure_overrides": None})[
            "structure_overrides"
        ]
        is None
    )
    path = results_io.write_csv(tmp_path / "sweep_index.csv", frame)
    back = pd.read_csv(path)
    assert list(back.columns) == cols and back.iloc[0]["s1_st.structure_set"] == "central"
    assert back.iloc[0]["s1_st.structure_overrides"] == "none"
    assert not bool(back.iloc[0]["s1_st.structure_plausibility_scaled"])
    assert results_io.OFFLOAD_STRUCTURE_SWEEP_COLUMNS == (
        "structure_set",
        "structure_sizing",
        "structure_dynamic",
        "structure_entry",
        "structure_margin",
        "structure_cap_g",
        "structure_dm_kg",
        "structure_dm_stage2_kg",
        "structure_dm_x0_kg",
        "structure_dlf",
        "structure_n_peak_g",
        "structure_F_peak_N",
        "structure_ramp_cost_rel",
        "structure_plausibility_factor",
        "structure_flags",
        "structure_plausibility_scaled",
        "structure_overrides",
        "structure_plausibility_ratio",
    )


def test_sweep_summary_words_its_structural_cases(
    fake_reporting_pass: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fix round 2, H-S3a-P2-07: a sweep point writes no case record or run directory, so
    the sweep summary words its structural offload cases under the table
    (summary.sweep_structure_lines): one line per case that is structural at some point,
    with how many points, that ``<case>.structure_dm_kg`` is the modelled structural mass
    of the push load (never an assumed penalty), the model, the layer and set, the file,
    the estimate text, the plausibility rule's factor where the column says it scaled, and
    where the fired flags are; a sweep without a structural case prints none (these lines
    add nothing to an SP1-type sweep summary)."""
    _resolved, report = _pass([PLAIN_CASE, ST_CASE])
    by = {c["name"]: c for c in report.record["cases"]}
    plain, st = by["s1"], by["s1_st"]
    lines = summary.sweep_structure_lines([{"s1": plain, "s1_st": st}, {"s1": plain}])
    assert lines[:2] == [summary.SWEEP_STRUCTURE_HEAD, ""]
    (line,) = lines[2:]
    assert line == (
        "- s1_st (1 point of 2): s1_st.structure_dm_kg is the modelled structural mass of the "
        "push load at each point's x* (dm1 + dm2, never an assumed penalty), a first-order "
        "station sizing of the push load (layer and set "
        f"{summary.structure_layer_label(st)}; {st['structure_file']}), a first-order estimate "
        "with its stated ranges, not a detailed structural design; its fired flags are in "
        "s1_st.structure_flags and the Checks section."
    )
    scaled = summary.sweep_structure_lines(
        [{"s1_st": {**st, "structure_plausibility_scaled": True}}]
    )
    assert "factor where s1_st.structure_plausibility_scaled is True (D-SP7-33)" in scaled[2]
    assert summary.sweep_structure_lines([{"s1": plain}]) == []
    assert summary.sweep_structure_lines([]) == []
    # planar_sweep_summary prints them under the sweep's table (the other sections stubbed)
    for name in ("assumptions_section", "sweep_checks_section", "guidance_label"):
        monkeypatch.setattr(summary, name, lambda *a, **k: "")
    baseline = SimpleNamespace(name="pad", result=SimpleNamespace(status="inserted", metrics={}))
    git = {"hash": "abc123", "dirty": False}
    for records, printed in (([{"s1": plain, "s1_st": st}], True), ([{"s1": plain}], False)):
        sweep = _sweep(tmp_path, records)
        frame = results_io.planar_sweep_index_frame(sweep, tmp_path)
        text = summary.planar_sweep_summary(
            "x",
            [sweep],
            [frame],
            baseline,
            git,
            "20261012T000000Z",  # type: ignore[arg-type]
        )
        assert (summary.SWEEP_STRUCTURE_HEAD in text) is printed
        if printed:
            table_end = text.index("| ", text.index("## sweep_1"))
            assert text.index(summary.SWEEP_STRUCTURE_HEAD) > table_end


def test_sweep_point_config_carries_the_block_file(
    fake_reporting_pass: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_run_sweeps_into`` passes the block's structure file to a point's
    resolved_config.yaml (``structure_block_used``: the file, its sha256 and content) only
    when the sweep solves a structural case there: None with --no-offload, None for a
    sweep naming a plain case of an experiment with a block, None without a block; the
    baseline copy never carries it."""
    sweep = {"of": "silo_cold", "axes": {"assist.stroke_m": [100]}, "offload": ["s1_st"]}
    exp, veh = tsp._experiment([ST_CASE], sweeps=[sweep])
    resolved = tsp._resolve(exp, veh)
    used = results_io.structure_block_used(resolved)
    assert used is not None and used["file"] == SYNTHETIC_NAME
    assert used["sha256"] == resolved.structure.file.sha256  # type: ignore[union-attr]
    seen: list[Any] = []

    def write_single(rr: Any, ref: Any, er: Any, out: Path, *a: Any, **k: Any) -> Path:
        seen.append((rr.name, k.get("structure")))
        return out

    monkeypatch.setattr(results_io, "write_single", write_single)
    monkeypatch.setattr(results_io, "offload_sweep_point", lambda *a, **k: ({"s1_st": {}}, {}))
    monkeypatch.setattr(
        results_io, "planar_comparisons", lambda res, ref, runs, **k: {n: {} for n in runs}
    )
    results_io._run_sweeps_into(resolved, tmp_path / "on", False, {}, "t", offload=True)
    assert [(n, s is None) for n, s in seen] == [("pad", True), ("run_0001", False)]
    assert seen[1][1] == used
    seen.clear()
    results_io._run_sweeps_into(resolved, tmp_path / "off", False, {}, "t", offload=False)
    assert [(n, s) for n, s in seen] == [("pad", None), ("run_0001", None)]  # --no-offload
    exp_plain_sweep, veh_ps = tsp._experiment(
        [ST_CASE, PLAIN_CASE], sweeps=[{**sweep, "offload": ["s1"]}]
    )
    plain_sweep = tsp._resolve(exp_plain_sweep, veh_ps)
    assert results_io.structure_block_used(plain_sweep) is not None
    seen.clear()
    results_io._run_sweeps_into(plain_sweep, tmp_path / "ps", False, {}, "t", offload=True)
    assert [s for _n, s in seen] == [None, None]  # a block, but no structural case solved
    exp2, veh2 = tsp._experiment([PLAIN_CASE], block={}, sweeps=[{**sweep, "offload": ["s1"]}])
    plain = tsp._resolve(exp2, veh2)
    assert results_io.structure_block_used(plain) is None
    seen.clear()
    results_io._run_sweeps_into(plain, tmp_path / "plain", False, {}, "t", offload=True)
    assert [s for _n, s in seen] == [None, None]
    out = tmp_path / "single"
    rr = tsp._fake_rr(resolved.baseline, P_REF)
    er = results_io.ExperimentResult("e", "v", rr, {}, {}, {}, "t", model=config.PLANAR_2D)
    real_write_single = (
        results_io.write_single.__wrapped__
        if hasattr(results_io.write_single, "__wrapped__")
        else None
    )
    assert (
        real_write_single is None
    )  # the monkeypatch above replaced it; call the module's original below
    monkeypatch.undo()
    monkeypatch.setattr(results_io, "write_timeseries", lambda *a, **k: None)
    monkeypatch.setattr(results_io, "write_plots", lambda *a, **k: [])
    results_io.write_single(rr, rr, er, out, False, structure=used)
    import yaml

    cfg = yaml.safe_load((out / "resolved_config.yaml").read_text(encoding="utf-8"))
    assert list(cfg)[-1] == "structure" and cfg["structure"]["file"] == SYNTHETIC_NAME
    results_io.write_single(rr, rr, er, tmp_path / "single2", False)
    cfg2 = yaml.safe_load(
        (tmp_path / "single2" / "resolved_config.yaml").read_text(encoding="utf-8")
    )
    assert "structure" not in cfg2


# -------------------------------------------------------------- the plausibility-scaled row


def test_plausibility_scaled_row_refusals_and_factor(
    sp1_resolved: config.ResolvedExperiment,
    synthetic_file: config.StructureFile,
    synthetic_pad: structure.PadLoadSet,
) -> None:
    """``plausibility_scaled`` is refused on the central set and on an outer set (the rule
    scales a physics band end), and as a non-bool; on a physics set it resolves with the
    provenance suffix ", plausibility-scaled" and a key of its own. The transform's factor
    equals ``structure.plausibility`` on the synthetic pad at the central coefficients
    (margin 0, no cap; never typed in): the favourable-end factor on physics_low_mass, the
    adverse-end factor on physics_high_mass (1.0 here: the model lies above 1.3 R); the
    scaled sizing's dm is the factor times the unscaled sizing's within 0.1% (the fixed
    point is taken on the scaled mass, so the push it sizes is slightly lighter); the
    record's three plausibility keys on every structural run, the elements scaled with dm,
    the unscaled twin's keys saying so."""
    for bad in ("central", "outer_low_mass", "outer_high_mass"):
        with pytest.raises(ValueError, match="physics_low_mass or physics_high_mass"):
            StructureCaseConfig(set=bad, plausibility_scaled=True)
    with pytest.raises(ValueError, match="true or false"):
        StructureCaseConfig(set="physics_low_mass", plausibility_scaled=1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="physics_low_mass or physics_high_mass"):
        StructurePayloadCaseConfig(
            name="p", of="silo_cold", set="central", plausibility_scaled=True
        )
    ok = StructureCaseConfig(set="physics_low_mass", plausibility_scaled=True)
    st = resolve_structure_settings(ok, synthetic_file, ok.sizing, "test")
    plain = resolve_structure_settings(
        StructureCaseConfig(set="physics_low_mass"), synthetic_file, "flown", "test"
    )
    assert st.plausibility_scaled and not plain.plausibility_scaled
    assert st.provenance == f"{plain.provenance}, plausibility-scaled"
    assert st.key != plain.key and st.settings()["plausibility_scaled"] is True
    cfg = synthetic_file.config
    coeffs = cfg.coefficients()
    veh = sp1_resolved.variants["silo_cold"].to_vehicle()
    geometry = structure.build_geometry(sim.stack_masses(veh), cfg.stack_layout(), coeffs)
    envelope = structure.build_envelope(geometry, coeffs, synthetic_pad, stages=("stage1",))
    check = structure.plausibility(geometry, coeffs, envelope)
    assert check.m_model_kg > check.upper_kg  # the synthetic file: the rule fires on the low end
    assert check.favourable_end_factor < 1.0 and check.adverse_end_factor == 1.0
    scaled = tsp._transform(
        sp1_resolved,
        synthetic_file,
        synthetic_pad,
        set="physics_low_mass",
        plausibility_scaled=True,
    )
    unscaled = tsp._transform(sp1_resolved, synthetic_file, synthetic_pad, set="physics_low_mass")
    high = tsp._transform(
        sp1_resolved,
        synthetic_file,
        synthetic_pad,
        set="physics_high_mass",
        plausibility_scaled=True,
    )
    central = tsp._transform(sp1_resolved, synthetic_file, synthetic_pad)
    assert scaled.plausibility_factor == check.favourable_end_factor
    assert unscaled.plausibility_factor == 1.0 and central.plausibility_factor == 1.0
    assert high.plausibility_factor == check.adverse_end_factor == 1.0
    assert scaled.plausibility_ratio == check.m_model_kg / check.relation_kg
    x = ss.HEADLINE_OFFLOAD_KG
    s_sc, s_un = scaled.sizing_at(x), unscaled.sizing_at(x)
    assert s_sc.factor == check.favourable_end_factor and s_un.factor == 1.0
    assert s_sc.total_kg == pytest.approx(check.favourable_end_factor * s_un.total_kg, rel=1e-3)
    assert s_sc.total_kg < s_un.total_kg
    assert s_sc.total_kg == pytest.approx(
        s_sc.factor * (s_sc.increment.dm_stage1_kg + s_sc.increment.dm_stage2_kg), rel=1e-15
    )
    rec_sc = sim.structure_record(scaled, s_sc, scaled.sizing_at(0.0))
    rec_un = sim.structure_record(unscaled, s_un, unscaled.sizing_at(0.0))
    rec_c = sim.structure_record(central, central.sizing_at(x), central.sizing_at(0.0))
    for rec in (rec_sc, rec_un, rec_c):
        assert tuple(rec) == sim.STRUCTURE_RECORD_KEYS
        assert rec["structure_plausibility_ratio"] == scaled.plausibility_ratio
        assert math.fsum(rec["structure_elements"].values()) == pytest.approx(
            rec["structure_dm_kg"], abs=1e-9
        )
    assert rec_sc["structure_plausibility_scaled"] is True
    assert rec_un["structure_plausibility_scaled"] is False
    assert rec_sc["structure_plausibility_factor"] == rec_un["structure_plausibility_factor"]
    assert rec_sc["structure_plausibility_factor"] == check.favourable_end_factor
    assert (
        rec_c["structure_plausibility_factor"] == 1.0
        and rec_c["structure_plausibility_scaled"] is False
    )
    assert rec_sc["structure_ring_kg"] == pytest.approx(
        s_sc.factor * s_sc.increment.ring_kg, rel=1e-15
    )
    assert sim.plausibility_end_factor("outer_high_mass", check) == 1.0
    failed = sim.structure_record(scaled, None, scaled.sizing_at(0.0))
    assert failed["structure_plausibility_scaled"] is True and failed["structure_dm_kg"] is None


# ---------------------------------------------------------------- the flight check


def _assisted_result(veh: Any, n_scale: float = 1.0) -> sim.Result:
    """The synthetic pad flight of ``veh`` relabelled as an assisted run: its HOLD rows
    become ASSIST rows (a push), its flight rows' felt n scaled by ``n_scale``."""
    result = ss.synthetic_pad_result(veh)
    ts = result.timeseries.copy()
    hold = ts["phase"] == "HOLD"
    ts.loc[hold, "phase"] = "ASSIST"
    ts.loc[~hold, "felt_axial_g"] = ts.loc[~hold, "felt_axial_g"] * n_scale
    return dataclasses.replace(result, timeseries=ts)


def test_flight_check_on_a_synthetic_recorded_run(
    sp1_resolved: config.ResolvedExperiment,
    synthetic_file: config.StructureFile,
    synthetic_pad: structure.PadLoadSet,
) -> None:
    """The flight adapter reads the rows after the release (the pad adapter refuses a push):
    its cases equal the pad adapter's non-HOLD cases of the same flight; ``flight_load_set``
    refuses a HOLD or PUSH case and a flight with no stage-1 row. A flight inside its own
    envelope gives 0.0 kg on every element and no flag; the same flight at 20% more felt n
    exceeds it (every element's kg >= 0 and summing to the total, above the 1 kg threshold,
    the flag fired with its numbers). Through ``sim.structure_flight_check`` on a RunResult
    whose vehicle carries the restated dm: ``with_flight_check`` fills
    ``structure_flight_exceedance_kg`` and appends the flag, ``with_structure_items``
    promotes it to the run's flags; a run without a time series gives None and leaves the
    items as they were; the adapter's refusals. Under the synthetic physics_high_mass set
    (its stiffened row plate_limited) and under the central set, each barrel's exceedance
    of the +5% flight equals the push path's (``_barrel_push`` and ``_barrel_increment`` on
    the same flight features against the envelope element, 1e-9 kg): the flight's
    plate-limited row is anchored at the pad envelope's N_env, not at its own load (the
    reduction's own anchoring gives a smaller excess there). A plausibility-scaled case's
    check carries the factor its dm carries under FLIGHT_DM_FACTOR_KEY (1.0 on an unscaled
    case) and its flag line says the exceedance is unscaled."""
    layout = synthetic_file.config.stack_layout()
    veh = ss.vehicle()
    assisted = _assisted_result(veh)
    cases = sim.structure_flight_cases(assisted, veh, layout, label="pad")
    pad_cases = [c for c in synthetic_pad.cases if c.kind == structure.FLIGHT]
    assert len(cases) == len(pad_cases) > 0
    for mine, theirs in zip(cases, pad_cases, strict=True):
        for name in (
            "t_s",
            "n_g",
            "lox_stage1_kg",
            "rp1_stage1_kg",
            "lox_stage2_kg",
            "rp1_stage2_kg",
            "upper_mass_stage1_kg",
            "upper_mass_stage2_kg",
            "vehicle_mass_kg",
            "thrust_N",
        ):
            assert getattr(mine, name) == getattr(theirs, name), name
        assert mine.kind == structure.FLIGHT and mine.hold_down_support_N is None
    with pytest.raises(ValueError, match="flight cases only"):
        structure.flight_load_set(synthetic_pad.cases)
    with pytest.raises(ValueError, match="stage-1 flight"):
        structure.flight_load_set([c for c in cases if not c.stage1_attached])
    flight = structure.flight_load_set(cases)
    assert flight.hold_cases.size == 0 and flight.cases[flight.meco_case].stage1_attached
    cfg = synthetic_file.config
    coeffs = cfg.coefficients()
    geometry = structure.build_geometry(sim.stack_masses(veh), layout, coeffs)
    envelope = structure.build_envelope(geometry, coeffs, synthetic_pad)
    same = structure.flight_exceedance(geometry, coeffs, envelope, flight, stage2=False)
    assert same.total_kg == 0.0 and same.stage1_kg == 0.0 and same.stage2_kg == 0.0
    assert all(e.kg == 0.0 and e.t_excess_max_m <= 0.0 for e in same.elements)
    assert [e.element for e in same.elements] == list(structure.FLIGHT_CHECK_ELEMENTS)
    assert all(e.stage == "stage1" for e in same.elements) and not same.stage2_checked
    assert same.flag.name == structure.FLAG_FLIGHT_EXCEEDANCE and not same.flag.fired
    assert same.flag.value("threshold_kg") == structure.FLIGHT_EXCEEDANCE_FLAG_KG == 1.0
    assert same.flag.value("margin") == 0.0 and math.isnan(same.flag.value("envelope_cap_g"))
    heavy_set = structure.flight_load_set(
        sim.structure_flight_cases(_assisted_result(veh, 1.2), veh, layout)
    )
    heavy = structure.flight_exceedance(geometry, coeffs, envelope, heavy_set, stage2=True)
    assert heavy.stage2_checked and len(heavy.elements) == 2 * len(structure.FLIGHT_CHECK_ELEMENTS)
    assert all(e.kg >= 0.0 for e in heavy.elements)
    assert heavy.total_kg == pytest.approx(sum(e.kg for e in heavy.elements), rel=1e-12)
    assert heavy.total_kg > structure.FLIGHT_EXCEEDANCE_FLAG_KG and heavy.flag.fired
    assert heavy.flag.value("total_kg") == heavy.total_kg
    assert heavy.flag.value("stage2_checked") == 1.0
    biggest = max(heavy.elements, key=lambda e: e.kg)
    assert biggest.t_excess_max_m > 0.0 and biggest.case_label is not None
    assert heavy.flag.value(f"{biggest.stage}.{biggest.element}_kg") == biggest.kg
    # a capped envelope: the flight's stage-1 n is capped as the envelope's was, so the
    # pad's own flight (5.2 g0 at MECO, above the cap) stays inside it; a flight at 20%
    # more felt n still exceeds it; the flag's numbers and line carry the cap
    cap_g = 4.5
    pad_n_max = max(c.n_g for c in cases if c.stage1_attached)
    assert pad_n_max > cap_g
    capped = structure.build_envelope(geometry, coeffs, synthetic_pad, envelope_cap_g=cap_g)
    same_capped = structure.flight_exceedance(geometry, coeffs, capped, flight, stage2=False)
    assert same_capped.total_kg == 0.0 and not same_capped.flag.fired
    assert all(e.kg == 0.0 and e.t_excess_max_m <= 0.0 for e in same_capped.elements)
    assert same_capped.flag.value("envelope_cap_g") == cap_g
    heavy_capped = structure.flight_exceedance(geometry, coeffs, capped, heavy_set, stage2=False)
    assert heavy_capped.total_kg > structure.FLIGHT_EXCEEDANCE_FLAG_KG and heavy_capped.flag.fired
    uncapped_line = sim._structure_flag_line(sim._flag_record(heavy.flag))
    capped_line = sim._structure_flag_line(sim._flag_record(heavy_capped.flag))
    assert "no cap" in uncapped_line and "margin 0" in uncapped_line
    assert f"capped at {cap_g:g} g0 as the envelope's was" in capped_line
    # a margin: the flight is evaluated unfactored against the factored envelope, so a
    # small exceedance fires at margin 0 and not within the margin's headroom
    mild_set = structure.flight_load_set(
        sim.structure_flight_cases(_assisted_result(veh, 1.05), veh, layout)
    )
    mild = structure.flight_exceedance(geometry, coeffs, envelope, mild_set, stage2=False)
    assert mild.total_kg > structure.FLIGHT_EXCEEDANCE_FLAG_KG and mild.flag.fired
    margined = structure.build_envelope(geometry, coeffs, synthetic_pad, margin=0.1)
    mild_margined = structure.flight_exceedance(geometry, coeffs, margined, mild_set, stage2=False)
    assert mild_margined.total_kg == 0.0 and not mild_margined.flag.fired
    assert mild_margined.flag.value("margin") == 0.1
    assert "margin 0.1" in sim._structure_flag_line(sim._flag_record(mild_margined.flag))
    # a plate-limited stiffened row: the flight anchored at the envelope's N_env, as the push
    for set_name, row in (
        ("physics_high_mass", structure.PLATE_LIMITED),
        ("central", "ring_common_z"),
    ):
        st_set = resolve_structure_settings(
            StructureCaseConfig(set=set_name), synthetic_file, "flown", "test"
        )
        c_set = st_set.coefficients
        assert structure._compression_mode(structure.RP1, c_set) == row
        g_set = structure.build_geometry(sim.stack_masses(veh), layout, c_set)
        e_set = structure.build_envelope(g_set, c_set, synthetic_pad)
        check_set = structure.flight_exceedance(g_set, c_set, e_set, mild_set, stage2=False)
        by_set = {e.element: e for e in check_set.elements}
        feats = mild_set.features("stage1", None).arrays
        sg = g_set.stage1
        for element, barrel in (
            (structure.RP1_BARREL, sg.rp1_barrel),
            (structure.LOX_BARREL, sg.lox_barrel),
        ):
            env_e = e_set.element("stage1", element)
            t_push, modes, _gap = structure._barrel_push("stage1", sg, barrel, feats, c_set, env_e)
            push_kg = structure._barrel_increment(
                "stage1", sg, barrel, env_e, t_push, modes, c_set, element=element
            ).kg
            assert by_set[element].kg == pytest.approx(push_kg, abs=1e-9), (set_name, element)
        if row == structure.PLATE_LIMITED:
            assert by_set[structure.RP1_BARREL].kg > 100.0
            own = structure._stage_envelope(
                "stage1", sg, mild_set.features("stage1", None), c_set, 1.0
            )[structure.RP1_BARREL]
            env_rp1 = e_set.element("stage1", structure.RP1_BARREL)
            assert (
                float(np.max(own.t_m - env_rp1.t_m)) < by_set[structure.RP1_BARREL].t_excess_max_m
            )
    # through the pipeline's seam on a RunResult whose vehicle carries dm
    transform = tsp._transform(sp1_resolved, synthetic_file, synthetic_pad)
    sizing = transform.sizing_at(0.0)
    start = sp1_resolved.variants["silo_cold"]
    final = offload_solved_run(
        start,
        "stage1",
        0.0,
        "s1_st",
        "s1_st",
        structure_dm_kg=(sizing.dm_stage1_kg, sizing.dm_stage2_kg),
        provenance=transform.settings.provenance,
    )
    flown = with_payload(final.to_vehicle(), P_REF)
    result = _assisted_result(flown, 1.2)
    result = dataclasses.replace(result, metrics={"payload_kg": P_REF})
    rr = sim.RunResult("s1_st", final, result)
    check = sim.structure_flight_check(transform, rr, sizing)
    assert check is not None and check.total_kg > 0.0 and check.flag.fired
    items = sim.structure_record(transform, sizing, sizing)
    assert items["structure_flight_exceedance_kg"] is None
    filled = sim.with_flight_check(items, check)
    assert filled["structure_flight_exceedance_kg"] == check.total_kg
    assert [f["name"] for f in filled["structure_flags"]][-1] == structure.FLAG_FLIGHT_EXCEEDANCE
    assert items["structure_flight_exceedance_kg"] is None  # the input is not mutated
    promoted = sim.with_structure_items(rr, filled)
    assert promoted.result.flags[-1].startswith(structure.FLAG_FLIGHT_EXCEEDANCE)
    assert "sized, not charged or iterated" in promoted.result.flags[-1]
    assert promoted.result.metrics["structure_flight_exceedance_kg"] == check.total_kg
    assert check.flag.value(sim.FLIGHT_DM_FACTOR_KEY) == 1.0
    assert "unscaled sizing" not in promoted.result.flags[-1]
    # every flag line states the element scope, and an unchecked stage 2 is never "0 kg"
    assert summary.STRUCTURE_FLIGHT_CHECK_SCOPE in promoted.result.flags[-1]
    assert "the aft skirt and the load ring are not checked" in promoted.result.flags[-1]
    assert "stage 2 not checked (not sized by the push)" in promoted.result.flags[-1]
    assert "stage 2 0 kg" not in promoted.result.flags[-1]
    assert f"stage 2 {heavy.stage2_kg:.3g} kg" in uncapped_line
    assert "stage 2 not checked" not in uncapped_line  # stage 2 was checked there
    # a plausibility-scaled case: the exceedance unscaled, the flag naming the dm's factor
    scaled_t = tsp._transform(
        sp1_resolved,
        synthetic_file,
        synthetic_pad,
        set="physics_low_mass",
        plausibility_scaled=True,
    )
    s_sc = scaled_t.sizing_at(0.0)
    final_sc = offload_solved_run(
        start,
        "stage1",
        0.0,
        "s1_lo_sc",
        "s1_lo_sc",
        structure_dm_kg=(s_sc.dm_stage1_kg, s_sc.dm_stage2_kg),
        provenance=scaled_t.settings.provenance,
    )
    flown_sc = with_payload(final_sc.to_vehicle(), P_REF)
    result_sc = dataclasses.replace(_assisted_result(flown_sc, 1.2), metrics={"payload_kg": P_REF})
    check_sc = sim.structure_flight_check(
        scaled_t, sim.RunResult("s1_lo_sc", final_sc, result_sc), s_sc
    )
    assert (
        check_sc is not None and check_sc.flag.value(sim.FLIGHT_DM_FACTOR_KEY) == s_sc.factor < 1.0
    )
    # the mass is the check's own sizing: it does not carry the factor
    plain_check = structure.flight_exceedance(
        scaled_t.geometry,
        scaled_t.settings.coefficients,
        scaled_t.envelope,
        structure.flight_load_set(
            sim.structure_flight_cases(result_sc, flown_sc, layout, label="s1_lo_sc")
        ),
        stage2=s_sc.increment.stage2_sized,
    )
    assert check_sc.total_kg == plain_check.total_kg > 0.0
    line_sc = sim._structure_flag_line(sim._flag_record(check_sc.flag))
    assert "the exceedance is the unscaled sizing" in line_sc and f"{s_sc.factor:.4g}" in line_sc
    empty = sim.RunResult("s1_st", final, tsp._fake_result({"payload_kg": P_REF}))
    assert sim.structure_flight_check(transform, empty, sizing) is None
    assert sim.with_flight_check(items, None) == items
    with pytest.raises(ValueError, match="lit stage-1 row"):
        sim.structure_flight_cases(
            dataclasses.replace(
                assisted, timeseries=assisted.timeseries[assisted.timeseries["stage"] == "stage2"]
            ),
            veh,
            layout,
        )
    with pytest.raises(ValueError, match="not the one the Result flew"):
        sim.structure_flight_cases(assisted, with_offload(veh, "stage1", 20_000.0), layout)


def test_flight_check_is_not_applicable_on_a_payload_case(
    fake_reporting_pass: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    synthetic_file: config.StructureFile,
    synthetic_pad: structure.PadLoadSet,
) -> None:
    """The flight check is not run on a structure payload case (review N-S3b-R3-01): its
    run flies its own P_2* while the envelope is the pad's at P_ref, so a check against it
    would measure the payload gain, not the push. Shown on the synthetic pad flight
    relabelled at a heavier payload (the pad's own flight with 1,500 kg more payload, its
    masses shifted alike): against its own P_ref envelope it exceeds by more than the 1 kg
    threshold, which the pad itself would need. So the pass calls the check for the
    offload case only; the payload record says "not applicable" under ``flight_check``,
    keeps ``structure_flight_exceedance_kg`` None and carries no flight flag; the run's
    assumption line and the payload table say the same."""
    layout = synthetic_file.config.stack_layout()
    veh = ss.vehicle()
    heavier = 1500.0
    veh_heavy = with_payload(veh, P_REF + heavier)
    result = _assisted_result(veh)
    ts = result.timeseries.copy()
    ts["m_kg"] = ts["m_kg"] + heavier
    events = result.events.copy()
    events["m_kg"] = events["m_kg"] + heavier
    shifted = dataclasses.replace(result, timeseries=ts, events=events)
    cases = sim.structure_flight_cases(shifted, veh_heavy, layout)
    cfg = synthetic_file.config
    coeffs = cfg.coefficients()
    geometry = structure.build_geometry(sim.stack_masses(veh), layout, coeffs)
    envelope = structure.build_envelope(geometry, coeffs, synthetic_pad)  # the pad at P_ref
    gain = structure.flight_exceedance(
        geometry, coeffs, envelope, structure.flight_load_set(cases), stage2=False
    )
    assert gain.total_kg > structure.FLIGHT_EXCEEDANCE_FLAG_KG and gain.flag.fired
    same = structure.flight_exceedance(
        geometry,
        coeffs,
        envelope,
        structure.flight_load_set(sim.structure_flight_cases(result, veh, layout)),
        stage2=False,
    )
    assert same.total_kg == 0.0  # the pad's own flight at P_ref: inside its envelope
    seen: list[str] = []
    real_check = sim.structure_flight_check

    def spy(transform: Any, rr: Any, sizing: Any) -> Any:
        seen.append(rr.name)
        return real_check(transform, rr, sizing)

    monkeypatch.setattr(sim, "structure_flight_check", spy)
    _resolved, report = _pass([ST_CASE], payload_cases=[PAYLOAD_CASE])
    assert seen == ["s1_st"]  # the offload case only, never the payload case
    (p,) = report.record["structure_payload_cases"]
    assert p["flight_check"] == sim.STRUCTURE_PAYLOAD_FLIGHT_CHECK_NA
    assert p["flight_check"].startswith("not applicable: the recorded run flies its own P*")
    assert "the envelope is the pad's at P_ref" in p["flight_check"]
    assert p["structure_flight_exceedance_kg"] is None
    assert structure.FLAG_FLIGHT_EXCEEDANCE not in [f["name"] for f in p["structure_flags"]]
    assert list(p).index("flight_check") < list(p).index("structure_charged")
    rr = report.runs["cold_pstar_st"]
    assert rr.result.metrics["structure_flight_exceedance_kg"] is None
    assert not [f for f in rr.result.flags if f.startswith(structure.FLAG_FLIGHT_EXCEEDANCE)]
    (line,) = [a for a in rr.result.assumptions if a.startswith("structure payload case:")]
    assert line.endswith(sim.STRUCTURE_PAYLOAD_FLIGHT_CHECK_NA)
    assert "the post-hoc flight check is not applicable" in line
    text = summary.offload_section(results_io.offload_record(report))
    payload_part = text.split("Structure payload cases")[1]
    row = _row(payload_part, "flight check: the recorded run's own flight over the pad envelope")
    assert row[1] == sim.STRUCTURE_PAYLOAD_FLIGHT_CHECK_NA
    assert sim.STRUCTURE_PAYLOAD_FLIGHT_CHECK_NA is summary.STRUCTURE_PAYLOAD_FLIGHT_CHECK_NA
    assert all(ln.isascii() for ln in text.splitlines())


# ------------------------------------------------------------------------ the figure


def test_structure_figure_writes_two_panels(
    sp1_resolved: config.ResolvedExperiment,
    synthetic_file: config.StructureFile,
    synthetic_pad: structure.PadLoadSet,
    tmp_path: Path,
) -> None:
    """``plots.structure_figure`` on a sizing's Increment and its record has two panels
    (the thickness profile and dm by element), one bar per element of the record with its
    kg, markers for the governing modes keyed by mode name (every mode of the model, in
    colours and shapes apart from the stage lines'), a legend from synthetic handles
    outside the plotting area (the envelope dashed, a push line per stage), the envelope
    line, a title naming the set's layer that fits the figure for every layer label, the
    governing annotation off every drawn station and label, every drawn point inside its
    axes, a caption (inside the figure and clear of the dm panel's axis label on every
    record, its sizing clause on a line of its own) saying at which offload the profile
    was sized, the governing element, whether stage 2 was sized and (a scaled record)
    that the bars carry the factor while the profile does not, never the sets' search
    label; the dm panel's axis label by the case's entry; a stage-2-sized push draws
    stage 2 in an inset the annotation stays off, its z range covering the pair at its
    lowest station; a relation governing element is named in the caption with no
    annotation; ``write_structure_figure`` writes plots/<prefix>_structure.png."""
    transform = tsp._transform(sp1_resolved, synthetic_file, synthetic_pad)
    sizing = transform.sizing_at(ss.HEADLINE_OFFLOAD_KG)
    record = sim.structure_record(transform, sizing, transform.sizing_at(0.0))
    fig = plots.structure_figure(sizing.increment, record, "s1_st")
    assert len(fig.axes) == 2
    top, bottom = fig.axes
    assert len(bottom.patches) == len(record["structure_elements"])
    widths = [p.get_width() for p in bottom.patches]
    assert widths == pytest.approx(list(record["structure_elements"].values()))
    assert any(line.get_linestyle() == "--" for line in top.get_lines())
    assert len(top.collections) >= 1  # the governing-mode markers
    stage_rgb = {
        tuple(int(c[i : i + 2], 16) / 255.0 for i in (1, 3, 5))
        for c in plots.STRUCTURE_STAGE_COLORS.values()
    }
    for markers in top.collections:
        for face in markers.get_facecolor():
            assert tuple(round(float(x), 6) for x in face[:3]) not in {
                tuple(round(x, 6) for x in rgb) for rgb in stage_rgb
            }
    assert {m for _c, m in plots.STRUCTURE_MODE_MARKERS.values()} >= {"o", "s", "^"}
    assert set(plots.STRUCTURE_STAGE_COLORS.values()).isdisjoint(
        {c for c, _m in plots.STRUCTURE_MODE_MARKERS.values()}
    )
    every_mode = {
        structure.MODE_HOOP,
        structure.MODE_MONOCOQUE,
        structure.MODE_COMBINED,
        structure.MODE_MIN_GAUGE,
        structure.MODE_MEMBRANE,
        *structure.GERARD_CHOICES,
    }
    assert set(plots.STRUCTURE_MODE_MARKERS) >= every_mode  # keyed by name: fixed per mode
    styles = list(plots.STRUCTURE_MODE_MARKERS.values())
    assert len(set(styles)) == len(styles) and plots.STRUCTURE_MODE_MARKER_UNKNOWN not in styles
    legend = top.get_legend()
    assert legend is not None
    anchor = legend.get_bbox_to_anchor().transformed(top.transAxes.inverted())
    assert anchor.y1 <= 0.0  # under the panel, outside the plotting area
    legend_labels = [t.get_text() for t in legend.get_texts()]
    assert legend_labels[:2] == [plots.STRUCTURE_LEGEND_ENVELOPE, "push: stage1"]
    assert "at the case's margin and cap" in plots.STRUCTURE_LEGEND_ENVELOPE  # H-S3B-P3-12
    assert plots.STRUCTURE_LEGEND_POINT_ENVELOPE in legend_labels  # self-contained (V4)
    assert "its pad envelope" not in legend_labels
    env_handle, push_handle = legend.get_lines()[:2]
    assert env_handle.get_linestyle() == "--" and push_handle.get_linestyle() == "-"
    assert push_handle.get_linewidth() > 0.0  # a line, whatever element was drawn first
    assert "central (every coefficient at its central value): central" in top.get_title()
    caption = _caption_text(fig)
    assert "sized at an offload the record does not state" in caption
    assert "(the dashed envelope is at margin 0, no cap)" in caption
    assert plots.STRUCTURE_STAGE2_NOT_SIZED_TEXT in caption
    _assert_labels_clear(fig, sizing.increment)
    _assert_caption_fits(fig)
    assert "stage 1 only" in top.get_xlabel()
    # the dm panel's axis label follows the case's entry (H-S3B-P3-06): under aft_ring
    # the thrust structure is not in the load path and the ring frame is hatched
    assert record["structure_entry"] == "aft_ring"
    assert "the thrust structure not in the load path on entry aft_ring" in bottom.get_xlabel()
    assert "hatched: the ring frame" in bottom.get_xlabel()
    assert "by their relations" not in bottom.get_xlabel()
    assert "by their relations where the entry loads them" in plots._dm_axis_label(None)
    assert structure.SEARCH_LABEL not in caption and "screened search" not in caption
    g = record["structure_governing"]
    assert f"governing element: {g['stage']}.{g['element']} ({g['push_mode']}; " in caption
    assert f"station {g['station_index']}, z {g['z_m']:.2f} m, annotated" in caption
    _assert_annotation_clear(fig, sizing.increment)
    path = plots.write_structure_figure(sizing.increment, record, tmp_path / "plots", "s1_st")
    assert path == tmp_path / "plots" / "s1_st_structure.png" and path.stat().st_size > 0
    # the title fits the figure for every layer label (the outer sets' are the long ones)
    renderer = fig.canvas.get_renderer()
    for name in summary.STRUCTURE_LAYER_LABELS:
        fig_n = plots.structure_figure(sizing.increment, {**record, "structure_set": name}, "s1")
        title = fig_n.axes[0].title
        box = title.get_window_extent(fig_n.canvas.get_renderer())
        assert box.x0 >= fig_n.bbox.x0 and box.x1 <= fig_n.bbox.x1, name
        assert name in title.get_text()
        _assert_caption_fits(fig_n)  # the outer sets' labels make the longest first line
    assert renderer is not None
    # a case record: the caption names x*; a no_offload end x = 0; a payload case P_2*
    case = {**record, "status": "ok", "offload_kg": ss.HEADLINE_OFFLOAD_KG}
    fig2 = plots.structure_figure(sizing.increment, case, "s1_st")
    caption2 = _caption_text(fig2)
    assert f"\nsized at x* = {ss.HEADLINE_OFFLOAD_KG / 1000.0:,.3f} t\n" in caption2  # its own line
    none = {**record, "status": NO_OFFLOAD_STATUS, "offload_kg": 0.0}
    fig3 = plots.structure_figure(sizing.increment, none, "s1_none")
    assert "\nsized at x = 0 (the solve ended no_offload)\n" in _caption_text(fig3)
    _assert_caption_fits(fig3)
    payload = {
        **record,
        "kind": sim.STRUCTURE_PAYLOAD_RECORD_KIND,
        "payload_1_kg": 25_990.5,
        "payload_kg": 26_000.0,
    }
    fig4 = plots.structure_figure(sizing.increment, payload, "cold_pstar_st")
    caption4 = _caption_text(fig4)
    # the profile and bars are dm_1, sized at P_1*; the run then flew P_2*; the clause is
    # the caption's longest line and sits on a line of its own, inside the figure (NEW-V-01)
    assert (
        "\nsized at the full load with payload P_1* 25,990.5 kg (dm_1; the run then flew P_2* "
        "26,000.0 kg; structure payload case)\n" in caption4
    )
    assert "of the P_2* run" not in caption4
    _assert_caption_fits(fig4)
    failed = {**payload, "payload_kg": math.nan}
    fig4b = plots.structure_figure(sizing.increment, failed, "cold_fail2")
    caption4b = _caption_text(fig4b)
    assert "P_1* 25,990.5 kg (dm_1; structure payload case; its P_2* search failed)" in caption4b
    _assert_caption_fits(fig4b)
    # a plausibility-scaled record: the bars carry the factor, the profile does not
    scaled = tsp._transform(
        sp1_resolved,
        synthetic_file,
        synthetic_pad,
        set="physics_low_mass",
        plausibility_scaled=True,
    )
    s_sc = scaled.sizing_at(ss.HEADLINE_OFFLOAD_KG)
    rec_sc = sim.structure_record(scaled, s_sc, scaled.sizing_at(0.0))
    fig5 = plots.structure_figure(s_sc.increment, rec_sc, "s1_lo_sc")
    top5, bottom5 = fig5.axes
    factor = rec_sc["structure_plausibility_factor"]
    assert f"(x {factor:.4f}, plausibility-scaled)" in bottom5.get_title()
    caption5 = _caption_text(fig5)
    assert "the thickness profile is the unscaled sizing; the bars and dm carry" in caption5
    assert "physics band, low-mass end: physics_low_mass" in top5.get_title()
    assert [p.get_width() for p in bottom5.patches] == pytest.approx(
        list(rec_sc["structure_elements"].values())
    )
    _assert_annotation_clear(fig5, s_sc.increment)
    _assert_caption_fits(fig5)  # the tallest caption: the scaled sentence is a seventh line
    # a stage-2-sized push (the pad's stage-1 n capped low): stage 2 in an inset the
    # annotation stays off; the panel's z range extended past stage 1's data
    capped = tsp._transform(sp1_resolved, synthetic_file, synthetic_pad, envelope_cap_g=1.5)
    s_cap = capped.sizing_at(ss.HEADLINE_OFFLOAD_KG)
    assert s_cap.increment.stage2_sized
    rec_cap = sim.structure_record(capped, s_cap, capped.sizing_at(0.0))
    fig6 = plots.structure_figure(s_cap.increment, rec_cap, "s1_cap")
    top6 = fig6.axes[0]
    assert len(fig6.axes) == 2  # the inset is a child axes of the top panel
    (inset,) = top6.child_axes
    assert inset.get_title() == plots.STRUCTURE_STAGE2_INSET_TITLE
    inset_texts = [t.get_text() for t in inset.texts]
    assert {t for t in inset_texts if t.startswith("stage2.")} >= {
        "stage2.rp1_barrel",
        "stage2.lox_barrel",
    }
    assert not [t for t in top6.texts if t.get_text().startswith("stage2.")]
    z1_max = max(
        float(np.max(e.z_stations_m))
        for e in s_cap.increment.elements
        if e.stage == "stage1" and e.z_stations_m is not None
    )
    assert top6.get_xlim()[1] > z1_max * (1.0 + 0.5 * plots.STRUCTURE_STAGE2_X_EXTENSION)
    assert "stage 2 in the inset" in top6.get_xlabel()
    assert plots.STRUCTURE_STAGE2_SIZED_TEXT in " ".join(t.get_text() for t in fig6.texts)
    assert "push: stage2" in [t.get_text() for t in top6.get_legend().get_texts()]
    _assert_annotation_clear(fig6, s_cap.increment)
    _assert_labels_clear(fig6, s_cap.increment)  # every stage-2 point inside the inset too
    # the inset's z range covers the stage-2 pair at its lowest station (the aft dome and
    # the tube, drawn at a page offset): its lower limit lies below their station (NEW-V-02)
    z2_min = min(
        float(np.min(e.z_stations_m))
        for e in s_cap.increment.elements
        if e.stage == "stage2" and e.z_stations_m is not None
    )
    assert inset.get_xlim()[0] < z2_min and inset.dataLim.x0 == pytest.approx(z2_min)
    assert any(
        np.asarray(e.z_stations_m).shape[0] == 1 and float(np.min(e.z_stations_m)) == z2_min
        for e in s_cap.increment.elements
        if e.stage == "stage2" and e.z_stations_m is not None
    )  # the lowest stage-2 station is a point element's, not a barrel's
    caption6 = _caption_text(fig6)
    assert "(the dashed envelope is at margin 0, cap 1.5 g0)" in caption6
    _assert_caption_fits(fig6)
    # a margin row: the caption's envelope line names it beside the legend's entry
    margined = tsp._transform(sp1_resolved, synthetic_file, synthetic_pad, margin=0.1)
    s_m = margined.sizing_at(ss.HEADLINE_OFFLOAD_KG)
    fig_m = plots.structure_figure(s_m.increment, sim.structure_record(margined, s_m, s_m), "s1_m")
    caption_m = _caption_text(fig_m)
    assert "(the dashed envelope is at margin 0.1, no cap)" in caption_m
    # a relation governing element (the thrust-structure entry): the caption names it, no
    # annotation is drawn
    ts_t = tsp._transform(sp1_resolved, synthetic_file, synthetic_pad, entry="thrust_structure")
    s_ts = ts_t.sizing_at(ss.HEADLINE_OFFLOAD_KG)
    rec_ts = sim.structure_record(ts_t, s_ts, ts_t.sizing_at(0.0))
    assert rec_ts["structure_governing"]["element"] == "thrust_structure"
    fig7 = plots.structure_figure(s_ts.increment, rec_ts, "s1_ts")
    caption7 = _caption_text(fig7)
    kg_ts = rec_ts["structure_elements"]["stage1.thrust_structure"]
    assert (
        f"governing element: stage1.thrust_structure (relation; {kg_ts:,.1f} kg of dm; "
        "a relation element: no station profile" in caption7
    )
    assert not [t for t in fig7.axes[0].texts if t.get_text().startswith("governing:")]
    # under entry thrust_structure the axis label quotes the relations and says there is
    # no ring frame (its hatched bar is 0 by construction), never "not in the load path"
    label7 = fig7.axes[1].get_xlabel()
    assert "the interstage and the thrust structure by their relations" in label7
    assert "no ring frame on entry thrust_structure" in label7
    assert "not in the load path" not in label7 and "hatched: the ring frame" not in label7
    _assert_caption_fits(fig7)  # the entry-specific axis label fits the figure too


def _caption_text(fig: Any) -> str:
    """The figure's caption (the one figure text saying "not a measurement") with the
    wrapped continuations joined back (STRUCTURE_CAPTION_INDENT after a newline), so a
    clause is asserted whole whether or not the wrap broke it; every drawn line stays at
    most STRUCTURE_CAPTION_WRAP_CHARS long."""
    (caption,) = [t.get_text() for t in fig.texts if "not a measurement" in t.get_text()]
    assert all(len(ln) <= plots.STRUCTURE_CAPTION_WRAP_CHARS for ln in caption.splitlines())
    return "\n" + re.sub("\n" + plots.STRUCTURE_CAPTION_INDENT, " ", caption) + "\n"


def _assert_caption_fits(fig: Any) -> None:
    """The caption's box lies inside the figure (no line clipped at the right edge) and
    below the dm panel's tight box, its x-axis label included (the panels' layout rect
    follows the caption's measured height), and that tight box lies inside the figure
    too (the axis label's lines, built per entry, never clipped), measured on the
    figure's own renderer as tight_layout measures (no draw needed; NEW-V-01 of S3b's
    third review: a payload case's sizing clause ran past the figure's edge)."""
    renderer = fig.canvas.get_renderer()
    (caption,) = [t for t in fig.texts if "not a measurement" in t.get_text()]
    box = caption.get_window_extent(renderer)
    assert box.x0 >= fig.bbox.x0 and box.x1 <= fig.bbox.x1, box
    assert box.y0 >= fig.bbox.y0 and box.y1 <= fig.bbox.y1, box
    panel = fig.axes[1].get_tightbbox(renderer)
    assert box.y1 <= panel.y0, (box, panel)
    assert panel.x0 >= fig.bbox.x0 and panel.x1 <= fig.bbox.x1, panel
    assert panel.y1 <= fig.bbox.y1, panel


def _assert_annotation_clear(fig: Any, increment: Any) -> None:
    """The governing annotation's text box (padded as the figure pads it) covers no drawn
    station or envelope point of any element, no element label and, when stage 2 is
    drawn in the inset, not the inset, measured on the figure's own renderer after a
    draw."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    top = fig.axes[0]
    axes = [top, *top.child_axes]
    (ann,) = [t for ax in axes for t in ax.texts if t.get_text().startswith("governing:")]
    ann.update_positions(renderer)
    box = Text.get_window_extent(ann, renderer).padded(plots.STRUCTURE_ANNOTATION_PAD_PX)
    holder = ann.axes
    for e in increment.elements:
        if e.z_stations_m is None or e.t_env_m is None or e.t_push_m is None:
            continue
        ax = top if e.stage == "stage1" else (top.child_axes[0] if top.child_axes else None)
        if ax is not holder:
            continue
        z = np.asarray(e.z_stations_m, dtype=float)
        for t_m in (e.t_env_m, e.t_push_m):
            pts = ax.transData.transform(np.column_stack([z, 1e3 * np.asarray(t_m, dtype=float)]))
            inside = (
                (pts[:, 0] >= box.x0)
                & (pts[:, 0] <= box.x1)
                & (pts[:, 1] >= box.y0)
                & (pts[:, 1] <= box.y1)
            )
            assert not np.any(inside), (e.stage, e.element)
    for label in holder.texts:
        if label is ann or not label.get_text().startswith(("stage1.", "stage2.")):
            continue
        label.update_positions(renderer)
        assert not box.overlaps(Text.get_window_extent(label, renderer)), label.get_text()
    for child in top.child_axes:
        assert not box.overlaps(child.get_window_extent(renderer))


def _assert_labels_clear(fig: Any, increment: Any) -> None:
    """Every drawn station and envelope point of the top panel and of the stage-2 inset
    (the point elements at their page offset) lies inside its axes' box (NEW-V-02 of
    S3b's third review: the inset's autoscale had left the aft dome and the tube outside),
    and every element label (padded as the figure pads it) covers none of those points,
    overlaps no other element label, lies inside its axes and, in the top panel, off the
    stage-2 inset, measured on the figure's own renderer after a draw (V1 to V3 of S3b's
    visual review)."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    top = fig.axes[0]
    axes = [top, *top.child_axes]
    inset_box = top.child_axes[0].get_window_extent(renderer) if top.child_axes else None
    for ax in axes:
        labels = [t for t in ax.texts if t.get_text().startswith(("stage1.", "stage2."))]
        drawn = [
            e
            for e in increment.elements
            if e.z_stations_m is not None
            and e.t_env_m is not None
            and e.t_push_m is not None
            and ((e.stage == "stage1") == (ax is top))
        ]
        assert len(labels) == len(drawn)
        offsets = plots._z_offsets_pt(drawn)
        pts_list = []
        for e in drawn:
            z = np.asarray(e.z_stations_m, dtype=float)
            dx = plots._pt_to_px(fig, offsets.get((e.stage, e.element), 0.0))
            for t_m in (e.t_env_m, e.t_push_m):
                pts = ax.transData.transform(
                    np.column_stack([z, 1e3 * np.asarray(t_m, dtype=float)])
                )
                pts_list.append(pts + np.array([dx, 0.0]))
        pts = np.concatenate(pts_list)
        ax_box = ax.get_window_extent(renderer)
        assert np.all((pts[:, 0] >= ax_box.x0) & (pts[:, 0] <= ax_box.x1)), ax.get_title()
        assert np.all((pts[:, 1] >= ax_box.y0) & (pts[:, 1] <= ax_box.y1)), ax.get_title()
        boxes = []
        for label in labels:
            label.update_positions(renderer)
            box = Text.get_window_extent(label, renderer).padded(plots.STRUCTURE_LABEL_PAD_PX)
            inside = (
                (pts[:, 0] >= box.x0)
                & (pts[:, 0] <= box.x1)
                & (pts[:, 1] >= box.y0)
                & (pts[:, 1] <= box.y1)
            )
            assert not np.any(inside), label.get_text()
            assert box.x0 >= ax_box.x0 and box.x1 <= ax_box.x1, label.get_text()
            assert box.y0 >= ax_box.y0 and box.y1 <= ax_box.y1, label.get_text()
            if ax is top and inset_box is not None:
                assert not box.overlaps(inset_box), label.get_text()
            for other in boxes:
                assert not box.overlaps(other), label.get_text()
            boxes.append(box)


def test_write_run_writes_the_figure_for_each_structural_run(
    fake_reporting_pass: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``write_run`` with plots on writes plots/<run>_structure.png for every run of
    ``OffloadReport.increments`` (a structural case's recorded run, a payload case's) and
    none for an unstructured or a penalty run; the time-series writer is stubbed (the fake
    runs have none)."""
    cases = [PLAIN_CASE, ST_CASE]
    resolved, report = _pass(cases, payload_cases=[PAYLOAD_CASE])
    pad = tsp._fake_rr(resolved.baseline, P_REF)
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
    monkeypatch.setattr(results_io, "write_timeseries", lambda *a, **k: None)
    monkeypatch.setattr(results_io, "write_plots", lambda *a, **k: [])
    drawn: list[tuple[str, Any]] = []
    real_writer = results_io.write_structure_figure

    def spy(increment: Any, record: Any, plots_dir: Path, prefix: str) -> Path:
        drawn.append((prefix, record))
        return real_writer(increment, record, plots_dir, prefix)

    monkeypatch.setattr(results_io, "write_structure_figure", spy)
    out = results_io.write_run(er, tmp_path / "run", plots=True)
    written = sorted(p.name for p in (out / "plots").glob("*_structure.png"))
    assert written == ["cold_pstar_st_structure.png", "s1_st_structure.png"]
    # each figure is drawn from its case record (the status and x*, a payload case's
    # kind and P_2*), not from the run's bare metrics
    by_prefix = dict(drawn)
    assert by_prefix["s1_st"] is results_io.structure_figure_record(report, "s1_st")
    assert by_prefix["s1_st"]["status"] == "ok" and by_prefix["s1_st"]["offload_kg"] == X_FAKE
    assert by_prefix["cold_pstar_st"]["kind"] == sim.STRUCTURE_PAYLOAD_RECORD_KIND
    assert results_io.structure_figure_record(report, "no_such_run") is None
    out2 = results_io.write_run(er, tmp_path / "noplots", plots=False)
    assert not (out2 / "plots").exists()


# --------------------------------------------------------------------- the dumps


def test_structural_case_dump_carries_plausibility_scaled_and_sp1_cases_do_not() -> None:
    """A structural case's dump carries ``plausibility_scaled`` (false by default); an
    unstructured case's dump has no ``structure`` key, as before."""
    st = config.OffloadCaseConfig(name="s", of="v", solve="stage1", structure={})  # type: ignore[arg-type]
    assert st.model_dump()["structure"]["plausibility_scaled"] is False
    plain = config.OffloadCaseConfig(name="s", of="v", solve="stage1")
    assert "structure" not in plain.model_dump()
    exp, veh = tsp._experiment([PLAIN_CASE], block={})
    resolved = resolve_experiment(copy.deepcopy(exp), veh)
    assert resolved.structure is None
