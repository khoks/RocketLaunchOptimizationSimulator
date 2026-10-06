"""The app's form, pure (SP2 step A4; src/launchsim/appform.py; design
docs/phases/inputs/2026-10-05-SP2-design.md, section 4.7, D-SP2-07, 25, 31).

All fast, on the committed files (nothing is flown or written):

- every preset of design 4.7 builds the committed run: the resolved RunConfig and vehicle
  equal the committed experiment's (a case: its start run, paired pad and imposed
  offload) and so do the raw run dicts, the search budget id is the same, the six shared
  blocks and the baseline are byte-equal as raw dicts, and the committed name is kept;
  each preset's form survives a JSON request round trip, also with integer-valued floats
  spelled as a browser spells them (the raw run dict and the trajectory key unchanged);
  the 200 m silo keeps its full exit-speed double; each preset carries the duration note;
- an edited preset takes the neutral names (silo, silo_<mode>), never the committed ones,
  and never silo_instant or pad_instant unless the form is that preset;
- every refusal of the phase file's section 5.7 is one line with its form field
  (through ``app.preflight``, which adds the name check and the preflight); 1e400,
  -1e400, a 400-digit int, NaN, true and "3" in a number field, an unknown key and a long
  value are refused without being repeated; the stage-2 and both-stage forms need
  ``advanced`` and their labels say their readings; a push whose acceleration or exit
  speed, typed or derived, lies outside the form's ranges is refused; a lag time constant
  below 0.5 s and a denormal ramp time are refused; a Form built without the parser is
  checked like a request (its choices and booleans); a pydantic error never reaches the
  page whole;
- the pad-only launch has no variants and no offload;
- the derived values against hand numbers (3 g0 over 100 m, the drag-free apex, the
  felt g of the recorded run's metric) and the ramp-start conversions against the
  simulator's own IgnitionSpecs (``sim.run_ignition_specs``); the expected durations;
- the label constant equals the replay's; appform loads no I/O module; the run path
  imports neither appform nor app (source scan and a fresh interpreter); building never
  mutates the basis.
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from launchsim import app, appform, compare, config, replay, sim
from launchsim.config import SHARED_KEYS, ResolvedExperiment, resolve_experiment
from launchsim.constants import G0_MPS2, MU_EARTH_M3S2, R_EARTH_M


def _load_support() -> ModuleType:
    """tests/app_support.py, loaded by path (any pytest import mode)."""
    name = "app_support"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sup = _load_support()

SRC = Path(__file__).resolve().parents[1] / "src" / "launchsim"
GATE_EXIT_SPEED_MPS = math.sqrt(2.0 * 3.0 * G0_MPS2 * 100.0)
"""Hand exit speed [m/s] of the committed silo: 3 g0 net over 100 m from rest."""
RECORDED_FELT_G = 3.9964760359053533
"""felt_g_track_peak of silo_cold in results/silo_offload_2d/20261003T112934Z (read once
by hand; the derived value must equal it to rounding)."""
IO_MODULES = (
    "launchsim.run_data",
    "launchsim.replay",
    "launchsim.scene",
    "launchsim.plots",
    "launchsim.results_io",
    "launchsim.sim",
    "launchsim.summary",
    "launchsim.app",
    "launchsim.cli",
    "yaml",
)
"""Modules a pure appform must not load."""
RUN_PATH_MODULES = (
    "sim",
    "results_io",
    "search",
    "guidance",
    "dynamics",
    "offload",
    "compare",
    "summary",
    "metrics",
    "metrics_planar",
    "run_data",
    "config",
)
"""Modules of the run path that must never import appform or app."""


@pytest.fixture(scope="module")
def basis() -> appform.Basis:
    return sup.shipped_basis()


@pytest.fixture(scope="module")
def committed() -> dict[str, Any]:
    """The two committed experiments as raw dicts and resolved whole."""
    off, scr, veh = sup.raw_files()
    return {
        "off": off,
        "scr": scr,
        "veh": veh,
        "off_resolved": resolve_experiment(copy.deepcopy(off), copy.deepcopy(veh)),
        "scr_resolved": resolve_experiment(copy.deepcopy(scr), copy.deepcopy(veh)),
    }


def _resolve(basis: appform.Basis, form: appform.Form) -> tuple[dict, ResolvedExperiment]:
    exp = appform.build_experiment(basis, form)
    return exp, resolve_experiment(exp, basis.vehicle_copy())


def _request(basis: appform.Basis, name: str = "silo_cold", **changes: Any) -> dict[str, Any]:
    """The request of a preset with ``changes`` (a None value removes the key)."""
    req = appform.form_to_request(appform.preset_form(basis, name))
    for key, value in changes.items():
        if value is None:
            req.pop(key, None)
        else:
            req[key] = value
    return req


def _refused(basis: appform.Basis, req: dict[str, Any]) -> appform.Refusal:
    """The refusal of a request: by the parser, else by app.preflight."""
    parsed = appform.parse_request(req)
    if isinstance(parsed, appform.Refusal):
        return parsed
    resolved, refusal = app.preflight(basis, parsed)
    assert resolved is None and refusal is not None, req
    return refusal


def _one_line(refusal: appform.Refusal) -> None:
    assert "\n" not in refusal.message and "\r" not in refusal.message
    assert 0 < len(refusal.message) <= appform.MAX_REFUSAL_CHARS


# ------------------------------------------------------------------ presets


def test_every_preset_builds_the_committed_run(
    basis: appform.Basis, committed: dict[str, Any]
) -> None:
    """Each preset's experiment: name app, label exploratory; the six shared blocks and
    the baseline byte-equal to both committed files' raw dicts (json.dumps, key order
    included); the same search budget id; its variant (or case) under its committed
    name, with RunConfig and vehicle equal to the committed experiment's (a case: start
    run, paired pad, imposed offload, config); the pad preset alone has no variants and
    no offload."""
    off_r, scr_r = committed["off_resolved"], committed["scr_resolved"]
    budget = off_r.baseline.run.planar.search.budget_id()
    assert budget == scr_r.baseline.run.planar.search.budget_id()
    for preset in appform.presets(basis):
        exp, resolved = _resolve(basis, preset.form)
        assert exp["name"] == appform.APP_EXPERIMENT_NAME and exp["label"] == "exploratory"
        for raw in (committed["off"], committed["scr"]):
            assert json.dumps({k: exp[k] for k in SHARED_KEYS}) == json.dumps(
                {k: raw[k] for k in SHARED_KEYS}
            )
            assert json.dumps(exp["baseline"]) == json.dumps(raw["baseline"])
        assert resolved.baseline.run.planar.search.budget_id() == budget
        assert resolved.baseline.run == off_r.baseline.run
        assert resolved.baseline.run_dict == off_r.baseline.run_dict
        if preset.kind == appform.PRESET_BASELINE:
            assert "variants" not in exp and "offload" not in exp
            assert resolved.variants == {} and resolved.offload is None
            continue
        if preset.kind == appform.PRESET_VARIANT:
            source = off_r if preset.name in off_r.variants else scr_r
            assert list(resolved.variants) == [preset.name] and resolved.offload is None
            mine, theirs = resolved.variants[preset.name], source.variants[preset.name]
            assert mine.run == theirs.run and mine.vehicle == theirs.vehicle, preset.name
            assert mine.run_dict == theirs.run_dict, preset.name
            continue
        (case,) = resolved.offload.cases
        (theirs,) = [c for c in off_r.offload.cases if c.name == preset.name]
        assert case.name == preset.name and list(resolved.variants) == [theirs.config.of]
        assert case.config == theirs.config
        assert case.start.run == theirs.start.run and case.start.vehicle == theirs.start.vehicle
        assert case.imposed_kg == theirs.imposed_kg
        assert (case.pad_start is None) == (theirs.pad_start is None)
        if case.pad_start is not None:
            assert case.pad_start.run == theirs.pad_start.run
            assert case.pad_start.vehicle == theirs.pad_start.vehicle
        variant = resolved.variants[theirs.config.of]
        assert variant.run == off_r.variants[theirs.config.of].run
        assert variant.run_dict == off_r.variants[theirs.config.of].run_dict
        assert case.start.run_dict == theirs.start.run_dict
        assert resolved.offload.config.pad_control is case.config.solved


def test_presets_are_the_design_list_with_labels_and_durations(basis: appform.Basis) -> None:
    """The 17 presets of design 4.7 in order, each with a label, an expected range lo <=
    hi and a form that survives the JSON request round trip; the 200 m silo keeps the
    committed exit speed's full double; the default preset is silo_cold."""
    presets = appform.presets(basis)
    assert [p.name for p in presets] == list(appform.PRESET_NAMES)
    assert len(presets) == 17 and appform.DEFAULT_PRESET in appform.PRESET_NAMES
    for p in presets:
        assert p.label and 0.0 < p.expected_s[0] <= p.expected_s[1]
        request = json.loads(json.dumps(appform.form_to_request(p.form)))
        assert appform.parse_request(request) == p.form, p.name
        assert p.note == appform.EXPECTED_DURATION_NOTE
    by_name = {p.name: p for p in presets}
    committed = basis.variant_fragments["silo_cold_200m"]["assist"]["exit_speed_mps"]
    assert by_name["silo_cold_200m"].form.exit_speed_mps == committed
    assert repr(committed) == "76.70717046013364"


def _js_spelling(value: Any) -> Any:
    """A request value as a browser's JSON.stringify spells it: an integer-valued float
    loses its '.0' (3.0 is sent as 3, -2.0 as -2)."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def test_a_preset_sent_back_by_a_browser_is_the_committed_run(
    basis: appform.Basis, committed: dict[str, Any]
) -> None:
    """Every preset's request with integer-valued floats spelled as JSON.stringify spells
    them: a kept committed name carries the committed fragment, so the raw run dict and
    compare.trajectory_key equal the committed run's (and the case's start run's); -0.0
    is kept as 0.0."""
    off_r, scr_r = committed["off_resolved"], committed["scr_resolved"]
    for preset in appform.presets(basis):
        request = {k: _js_spelling(v) for k, v in appform.form_to_request(preset.form).items()}
        form = appform.parse_request(json.loads(json.dumps(request)))
        assert isinstance(form, appform.Form), (preset.name, form)
        _, resolved = _resolve(basis, form)
        if preset.kind == appform.PRESET_BASELINE:
            assert resolved.variants == {}
            continue
        if preset.kind == appform.PRESET_CASE:
            (case,) = resolved.offload.cases
            (theirs,) = [c for c in off_r.offload.cases if c.name == preset.name]
            assert case.name == preset.name
            assert case.start.run_dict == theirs.start.run_dict
            assert compare.trajectory_key(case.start) == compare.trajectory_key(theirs.start)
            run, source_run = resolved.variants[theirs.config.of], off_r.variants[theirs.config.of]
        else:
            source = off_r if preset.name in off_r.variants else scr_r
            run, source_run = resolved.variants[preset.name], source.variants[preset.name]
        assert run.run_dict == source_run.run_dict, preset.name
        assert compare.trajectory_key(run) == compare.trajectory_key(source_run), preset.name
    zero = appform.parse_request(
        {**_request(basis), "carriage_mass_t": -0.0, "exhaust_impingement_fraction": -0.0}
    )
    assert isinstance(zero, appform.Form)
    assert math.copysign(1.0, zero.carriage_mass_t) == 1.0
    assert math.copysign(1.0, zero.exhaust_impingement_fraction) == 1.0


def test_edited_presets_take_the_neutral_names(basis: appform.Basis) -> None:
    """A changed configuration is never written under a committed name (D-SP2-31):
    silo_cold with a 150 m stroke is 'silo'; its stage-1 solve 'silo_s1' (also without
    the paired pad, while the variant keeps silo_cold); other imposed offloads and
    penalties are silo_<mode>; the committed frontier case keeps its name only as
    committed (no paired pad); silo_instant with an offload is 'silo'."""
    cold = appform.preset_form(basis, "silo_cold")
    s1 = appform.preset_form(basis, "silo_cold_s1")

    def names(form: appform.Form) -> tuple[list[str], list[str]]:
        exp = appform.build_experiment(basis, form)
        cases = [c["name"] for c in exp.get("offload", {}).get("cases", [])]
        return list(exp.get("variants", {})), cases

    assert names(dataclasses.replace(cold, stroke_m=150)) == (["silo"], [])
    assert names(dataclasses.replace(s1, stroke_m=150)) == (["silo"], ["silo_s1"])
    assert names(dataclasses.replace(s1, paired_pad=False)) == (["silo_cold"], ["silo_s1"])
    fixed7 = dataclasses.replace(
        s1, propellant="fixed", solve_mode=None, fixed_key="stage1_fraction", fixed_value=0.07
    )
    assert names(fixed7) == (["silo_cold"], ["silo_fix7pct"])
    assert names(dataclasses.replace(s1, paired_pad=False, stage1_dry_mass_added_t=3)) == (
        ["silo_cold"],
        ["silo_s1_dry+3t"],
    )
    frontier = dataclasses.replace(s1, paired_pad=False, stage2_offload_t=2)
    assert names(frontier) == (["silo_cold"], ["silo_cold_s1_s2pre2t"])
    assert names(dataclasses.replace(frontier, paired_pad=True)) == (
        ["silo_cold"],
        ["silo_s1_s2pre2t"],
    )
    instant = appform.preset_form(basis, "silo_instant")
    assert names(instant) == (["silo_instant"], [])
    with_case = dataclasses.replace(instant, propellant="solve", solve_mode="stage1")
    assert names(with_case) == (["silo"], ["silo_s1"])
    pad_instant = appform.preset_form(basis, "pad_instant")
    assert names(pad_instant) == (["pad_instant"], [])
    lag = dataclasses.replace(pad_instant, startup="lag", tau_s=1.0)
    assert names(lag) == (["pad_variant"], [])


def test_a_basis_not_read_from_a_commit_keeps_no_committed_name(basis: appform.Basis) -> None:
    """The same files with no commit (git gave none at server start, or a basis edited in
    memory): every preset takes the neutral names, the anchors included, and nothing is a
    committed name (D-SP2-31: a committed name only for a configuration in a commit)."""
    assert basis.commit is not None and len(basis.commit) == 40
    loose = dataclasses.replace(basis, commit=None)

    def names(form: appform.Form) -> tuple[list[str], list[str]]:
        exp = appform.build_experiment(loose, form)
        resolved = resolve_experiment(exp, loose.vehicle_copy())
        assert appform.committed_names(loose, resolved) == ()
        cases = [c["name"] for c in exp.get("offload", {}).get("cases", [])]
        return list(exp.get("variants", {})), cases

    assert names(appform.preset_form(loose, "silo_cold")) == (["silo"], [])
    assert names(appform.preset_form(loose, "silo_cold_s1")) == (["silo"], ["silo_s1"])
    assert names(appform.preset_form(loose, "silo_cold_fix5pct")) == (["silo"], ["silo_fix5pct"])
    assert names(appform.preset_form(loose, "silo_instant")) == (["silo"], [])
    assert names(appform.preset_form(loose, "pad_instant")) == (["pad_variant"], [])
    assert names(appform.preset_form(loose, "pad")) == ([], [])


def test_the_pad_alone_resolves_with_no_variants(basis: appform.Basis) -> None:
    """The pad preset is the committed baseline verbatim with no variants key and no
    offload; derived names only the pad and has no push; a pad form whose ignition
    restates the baseline's is the pad alone too."""
    exp, resolved = _resolve(basis, appform.preset_form(basis, "pad"))
    assert set(exp) == {"name", "vehicle", "label", *SHARED_KEYS, "baseline"}
    assert resolved.variants == {} and resolved.offload is None
    d = appform.derived(resolved)
    assert d["variant"] is None and d["runs"] == ["pad"] and d["push"] is None
    assert (
        d["ramp_start"]["time_after_release_s"] == basis.baseline["ignition"]["stage1"]["t_ign_s"]
    )
    as_float = dataclasses.replace(appform.preset_form(basis, "pad"), t_ign_s=-2)
    assert "variants" not in appform.build_experiment(basis, as_float)


# ------------------------------------------------------------------ refusals


def test_the_refusals_of_the_phase_file_are_one_line_with_their_field(
    basis: appform.Basis,
) -> None:
    """Phase file 5.7, 'Refusals that must work', each one line naming its form field:
    both push keys; two ramp-start families; a depth below the shaft floor; a speed
    above the exit speed; a height at or above the drag-free apex by either method; a
    push-relative ramp start on a pad (push_start, depth, speed, height); an imposed
    offload at or beyond the load or a fraction outside (0, 1); a stage-2 pre-offload
    before a stage-2 or both case; a paired pad with a penalty; a missing and a
    non-numeric value; an invalid name (a name key is unknown to the form). A stage-2
    or both solve without the pad control cannot be sent: the pad control is always on."""
    pad = _request(basis, "pad")
    s1 = _request(basis, "silo_cold_s1")
    cases: list[tuple[dict[str, Any], str | None, str]] = [
        (_request(basis, exit_speed_mps=76.7), "push_by", "not both"),
        (_request(basis, at_depth_m=50), "ramp_by", "one way"),
        (_request(basis, ramp_by="depth", t_ign_s=None, at_depth_m=150), "at_depth_m", "deeper"),
        (_request(basis, ramp_by="speed", t_ign_s=None, at_speed_mps=80), "at_speed_mps", "exit"),
        (
            _request(basis, ramp_by="height_event", t_ign_s=None, at_height_m=301.5),
            "at_height_m",
            "apex",
        ),
        (
            _request(basis, ramp_by="height_closed_form", t_ign_s=None, at_height_m=301.5),
            "at_height_m",
            "apex",
        ),
        ({**pad, "ramp_by": "time_push_start"}, "ramp_by", "push_start"),
        ({**pad, "ramp_by": "depth", "t_ign_s": None, "at_depth_m": 10}, "ramp_by", "assist"),
        ({**pad, "ramp_by": "speed", "t_ign_s": None, "at_speed_mps": 10}, "ramp_by", "assist"),
        (
            {**pad, "ramp_by": "height_event", "t_ign_s": None, "at_height_m": 10},
            "ramp_by",
            "assist",
        ),
        (
            _request(basis, "silo_cold_fix5pct", fixed_key="stage1_t", fixed_value=410.9),
            "fixed_value",
            "carries",
        ),
        (_request(basis, "silo_cold_fix5pct", fixed_value=0), "fixed_value", "greater than 0"),
        (_request(basis, "silo_cold_fix5pct", fixed_value=1), "fixed_value", "less than 1"),
        (_request(basis, "silo_cold_fix5pct", fixed_value=1.2), "fixed_value", "less than 1"),
        (
            {
                **s1,
                "solve_mode": "stage2",
                "advanced": True,
                "paired_pad": False,
                "stage2_offload_t": 2,
            },
            "stage2_offload_t",
            "stage-1 case only",
        ),
        (
            {
                **s1,
                "solve_mode": "both",
                "advanced": True,
                "paired_pad": False,
                "stage2_offload_t": 2,
            },
            "stage2_offload_t",
            "stage-1 case only",
        ),
        ({**s1, "stage1_dry_mass_added_t": 2}, "paired_pad", "paired_pad"),
        (_request(basis, stroke_m=None), "stroke_m", "missing"),
        (_request(basis, stroke_m="abc"), "stroke_m", "number"),
        ({**_request(basis), "name": "silo cold"}, None, "does not know"),
    ]
    for req, field, needle in cases:
        req = {k: v for k, v in req.items() if v is not None}
        refusal = _refused(basis, req)
        _one_line(refusal)
        assert refusal.field == field, (req, refusal)
        assert needle in refusal.message, (needle, refusal)
    for mode in appform.ADVANCED_SOLVE_MODES:
        req = {**s1, "solve_mode": mode, "advanced": True, "paired_pad": False}
        form = appform.parse_request(req)
        assert isinstance(form, appform.Form)
        assert appform.build_experiment(basis, form)["offload"]["pad_control"] is True


def test_a_fixed_mass_beyond_the_stage2_load_and_a_preoffload_beyond_it(
    basis: appform.Basis,
) -> None:
    """An offload taken from stage 2 is refused at its own field: the imposed stage-2
    mass (fixed_value) or the stage-2 pre-offload of a stage-1 case (stage2_offload_t)."""
    s1 = _request(basis, "silo_cold_s1", paired_pad=False)
    fixed = {
        **_request(basis, "silo_cold_fix5pct"),
        "fixed_key": "stage2_t",
        "fixed_value": 107.5,
        "advanced": True,
    }
    assert _refused(basis, fixed).field == "fixed_value"
    assert _refused(basis, {**s1, "stage2_offload_t": 107.5}).field == "stage2_offload_t"


def test_number_fields_refuse_what_is_not_a_finite_bounded_number(basis: appform.Basis) -> None:
    """1e400 and -1e400 (what json.loads makes of them), NaN, a 400-digit int, true and
    "3" in a number field are refused at that field without the value being repeated;
    an unknown key and an over-long choice value are refused without being repeated;
    a choice outside its enumeration and a boolean given as 1 are refused; a value
    outside the form's range names the range."""
    label = appform.FIELDS["stroke_m"].label
    expected = {
        "finite": f"stroke_m: must be a finite number ({label})",
        "large": f"stroke_m: the number is too large for the form ({label})",
        "type": f"stroke_m: must be a number ({label})",
    }
    cases = [
        (float("inf"), "finite"),  # json.loads('1e400')
        (float("-inf"), "finite"),  # json.loads('-1e400')
        (float("nan"), "finite"),
        (int("9" * 400), "large"),
        (True, "type"),
        ("3", "type"),
        (None, "type"),
        ([3], "type"),
        ({"v": 3}, "type"),
    ]
    for bad, kind in cases:
        refusal = appform.parse_request({**_request(basis), "stroke_m": bad})
        assert isinstance(refusal, appform.Refusal), bad
        _one_line(refusal)
        assert refusal == appform.Refusal("stroke_m", expected[kind]), bad
    secret = "<img src=x onerror=1>" + "x" * 60
    unknown = appform.parse_request({**_request(basis), secret: 1})
    assert isinstance(unknown, appform.Refusal) and unknown.field is None
    assert secret not in unknown.message and "img" not in unknown.message
    long_value = appform.parse_request({**_request(basis), "site": secret})
    assert isinstance(long_value, appform.Refusal) and long_value.field == "site"
    assert "img" not in long_value.message
    assert appform.parse_request({**_request(basis), "fails": 1}).field == "fails"
    out_of_range = appform.parse_request({**_request(basis), "t_ign_s": 1e9})
    assert out_of_range.field == "t_ign_s" and "range" in out_of_range.message
    assert appform.parse_request([1, 2]).field is None
    assert appform.parse_request({**_request(basis), "site": None}).field == "site"


def test_unused_fields_and_the_advanced_forms_are_refused(basis: appform.Basis) -> None:
    """A field the choices do not use is refused (a pad with a depth, a full load with
    an offload mode), a false boolean may stay; a pad launch carries no offload, a
    failed ignition none; the stage-2 and both-stage forms need advanced."""
    pad = _request(basis, "pad")
    assert appform.parse_request({**pad, "stroke_m": 100}).field == "stroke_m"
    assert isinstance(appform.parse_request({**pad, "paired_pad": False}), appform.Form)
    assert appform.parse_request({**_request(basis), "solve_mode": "stage1"}).field == "solve_mode"
    assert (
        appform.parse_request({**pad, "propellant": "solve", "solve_mode": "stage1"}).field
        == "propellant"
    )
    failed = _request(basis, "silo_failed")
    assert (
        appform.parse_request({**failed, "propellant": "solve", "solve_mode": "stage1"}).field
        == "propellant"
    )
    s1 = _request(basis, "silo_cold_s1", paired_pad=False)
    assert appform.parse_request({**s1, "solve_mode": "stage2"}).field == "solve_mode"
    assert appform.parse_request({**s1, "solve_mode": "both"}).field == "solve_mode"
    fixed = _request(basis, "silo_cold_fix5pct")
    for key in appform.ADVANCED_FIXED_KEYS:
        refusal = appform.parse_request({**fixed, "fixed_key": key, "fixed_value": 0.01})
        assert refusal.field == "fixed_key", key
        allowed = appform.parse_request(
            {**fixed, "fixed_key": key, "fixed_value": 0.01, "advanced": True}
        )
        assert isinstance(allowed, appform.Form)


def test_the_advanced_forms_say_their_readings(basis: appform.Basis) -> None:
    """A form's label states D-SP2-07's readings: a stage-2 or both solve is quoted net of
    its pad control, a property of the vehicle model; an imposed stage-2 or both offload
    is not netted (no pad control); the stage-1 forms say neither."""
    s1 = appform.preset_form(basis, "silo_cold_s1")
    fix5 = appform.preset_form(basis, "silo_cold_fix5pct")
    for mode in appform.ADVANCED_SOLVE_MODES:
        form = dataclasses.replace(s1, solve_mode=mode, advanced=True, paired_pad=False)
        assert appform.describe(form).endswith(appform.ADVANCED_SOLVE_READING)
    for key in appform.ADVANCED_FIXED_KEYS:
        form = dataclasses.replace(fix5, fixed_key=key, fixed_value=0.05, advanced=True)
        assert appform.describe(form).endswith(appform.ADVANCED_FIXED_READING)
    for form in (s1, fix5):
        text = appform.describe(form)
        assert appform.ADVANCED_SOLVE_READING not in text
        assert appform.ADVANCED_FIXED_READING not in text


def test_a_push_outside_the_ranges_is_refused_however_typed(basis: appform.Basis) -> None:
    """The push's net acceleration and exit speed are checked together (A4 numerics
    review): a stroke below 1 m, a net acceleration below 0.01 g0 and an exit speed below
    1 m/s are refused by their own range; an exit speed over a short stroke (a derived
    acceleration above 20 g0, or below 0.01 g0 over a long one) is refused at the exit
    speed; a net acceleration over a long stroke (a derived exit speed above 500 m/s) at
    the net acceleration. The committed sweeps' corners pass."""
    long = _request(basis, "silo_cold_200m")
    cold = _request(basis)
    cases = [
        ({**long, "stroke_m": 1e-9}, "stroke_m"),
        ({**long, "stroke_m": 1e-300}, "stroke_m"),
        ({**cold, "net_accel_g": 5e-324}, "net_accel_g"),
        ({**long, "exit_speed_mps": 0.5}, "exit_speed_mps"),
        ({**long, "stroke_m": 1.0}, "exit_speed_mps"),
        ({**long, "stroke_m": 1000, "exit_speed_mps": 1.0}, "exit_speed_mps"),
        ({**cold, "stroke_m": 1000, "net_accel_g": 20}, "net_accel_g"),
        ({**cold, "stroke_m": 1, "net_accel_g": 0.01}, "net_accel_g"),
    ]
    for req, field in cases:
        refusal = appform.parse_request(req)
        assert isinstance(refusal, appform.Refusal), req
        _one_line(refusal)
        assert refusal.field == field and "range" in refusal.message, (req, refusal)
    for stroke, accel in ((25, 0.5), (300, 5), (50, 6), (1, 20), (1000, 0.01)):
        assert isinstance(
            appform.parse_request({**cold, "stroke_m": stroke, "net_accel_g": accel}),
            appform.Form,
        ), (stroke, accel)
    accel_g, speed = appform.push_numbers(appform.preset_form(basis, "silo_cold_200m"))
    assert accel_g == pytest.approx(1.5, rel=1e-12)
    assert speed == pytest.approx(GATE_EXIT_SPEED_MPS, rel=1e-15)


def test_the_startup_durations_have_positive_floors(basis: appform.Basis) -> None:
    """A lag time constant below 0.5 s is refused at tau_s (the integrator caps its step
    at tau / lag_steps_per_tau for the whole burn: 86 s for one fixed-guidance flight at
    0.01 s, a crash at 5e-324; A4 numerics review), through the parser and through
    app.preflight and app.dry_run on a Form built directly; a denormal ramp time is
    refused at t_ramp_s (it overflows the thrust fraction). silo_cold_lag (tau 1 s) still
    round-trips, and a 0.5 s lag is accepted."""
    lag = appform.preset_form(basis, "silo_cold_lag")
    assert lag.tau_s == 1.0
    request = json.loads(json.dumps(appform.form_to_request(lag)))
    assert appform.parse_request(request) == lag
    for tau in (0.01, 1e-300, 5e-324):
        refusal = appform.parse_request(_request(basis, "silo_cold_lag", tau_s=tau))
        assert isinstance(refusal, appform.Refusal) and refusal.field == "tau_s", tau
        assert "range" in refusal.message
        _one_line(refusal)
        form = dataclasses.replace(lag, tau_s=tau)
        resolved, refused = app.preflight(basis, form)
        assert resolved is None and refused is not None and refused.field == "tau_s", tau
        dry = app.dry_run(basis, form)
        assert isinstance(dry, appform.Refusal) and dry.field == "tau_s", tau
    assert isinstance(
        appform.parse_request(_request(basis, "silo_cold_lag", tau_s=0.5)), appform.Form
    )
    ramp = _request(basis, startup="ramp", t_ramp_s=5e-324)
    refusal = appform.parse_request(ramp)
    assert isinstance(refusal, appform.Refusal) and refusal.field == "t_ramp_s"
    ramp_form = dataclasses.replace(
        appform.preset_form(basis, "silo_cold"), startup="ramp", t_ramp_s=5e-324
    )
    assert app.preflight(basis, ramp_form)[1].field == "t_ramp_s"
    assert isinstance(appform.parse_request({**ramp, "t_ramp_s": 2.0}), appform.Form)


def test_a_form_built_directly_is_checked_like_a_request(basis: appform.Basis) -> None:
    """check_form re-checks what the parser checks for a Form built without it (A4
    numerics review): a choice outside its values (fixed_key, solve_mode, push_by) and a
    boolean that is not a bool (paired_pad 'no', fails 'yes') come back from app.preflight
    and app.dry_run as Refusals at their field, never as a KeyError or a truthy string
    written as true."""
    cold = appform.preset_form(basis, "silo_cold")
    s1 = appform.preset_form(basis, "silo_cold_s1")
    fix = appform.preset_form(basis, "silo_cold_fix5pct")
    cases = [
        (dataclasses.replace(fix, fixed_key="bogus"), "fixed_key"),
        (dataclasses.replace(s1, solve_mode="bogus"), "solve_mode"),
        (dataclasses.replace(cold, push_by="bogus", exit_speed_mps=76.7), "push_by"),
        (dataclasses.replace(s1, paired_pad="no"), "paired_pad"),
        (dataclasses.replace(cold, fails="yes"), "fails"),
        (dataclasses.replace(cold, preset="bogus"), "preset"),
    ]
    for form, field in cases:
        resolved, refusal = app.preflight(basis, form)
        assert resolved is None and refusal is not None, field
        assert refusal.field == field, (field, refusal)
        _one_line(refusal)
        dry = app.dry_run(basis, form)
        assert isinstance(dry, appform.Refusal) and dry.field == field


def test_a_pydantic_error_is_never_shown_whole() -> None:
    """refusal_text of a ValidationError: the first error's location (union tag dropped)
    and message (the 'Value error, ' prefix dropped), no input value, no URL, one line."""
    with pytest.raises(ValidationError) as caught:
        config.RunConfig.model_validate(
            {"name": "x", "assist": {"model": "constant_accel", "stroke_m": "abc<b>"}}
        )
    field, text = appform.refusal_text(caught.value)
    assert "input_value" not in text and "pydantic.dev" not in text and "abc<b>" not in text
    assert "constant_accel" not in text and "\n" not in text and field == "stroke_m"
    assert str(caught.value).count("\n") > 1  # what the page must never get
    with pytest.raises(ValidationError) as caught:
        config.ConstantAccelConfig.model_validate(
            {"model": "constant_accel", "stroke_m": 100, "brake_decel_g": 5}
        )
    field, text = appform.refusal_text(caught.value)
    assert not text.startswith("Value error") and "Value error, " not in text
    assert "exactly one of" in text


# ------------------------------------------------------------------ derived values


def test_derived_push_values_against_hand_numbers(basis: appform.Basis) -> None:
    """silo_cold: exit speed sqrt(2 x 3 g0 x 100 m), push time sqrt(2 L / a), felt
    (a + g_eff) / g0 with g_eff = mu/R_E^2 - omega_p^2 R_E (the recorded run's metric),
    braking v^2 / (2 x 5 g0) = 60 m, facility 160 m, the drag-free apex v^2 / (2 g_eff);
    silo_cold_200m typed by exit speed: net acceleration v^2 / (2 x 200 m) = 1.5 g0."""
    _, resolved = _resolve(basis, appform.preset_form(basis, "silo_cold"))
    push = appform.derived(resolved)["push"]
    a = 3.0 * G0_MPS2
    omega_p = resolved.variants["silo_cold"].run.site.omega_p_rads
    g_eff = MU_EARTH_M3S2 / R_EARTH_M**2 - omega_p**2 * R_EARTH_M
    assert push["typed"] == "net_accel_g"
    assert push["exit_speed_mps"] == pytest.approx(GATE_EXIT_SPEED_MPS, rel=1e-15)
    assert push["push_time_s"] == pytest.approx(math.sqrt(2.0 * 100.0 / a), rel=1e-15)
    assert push["felt_g"] == pytest.approx((a + g_eff) / G0_MPS2, rel=1e-15)
    assert push["felt_g"] == pytest.approx(RECORDED_FELT_G, rel=1e-14)
    assert push["braking_distance_m"] == pytest.approx(60.0, rel=1e-14)
    assert push["facility_length_m"] == pytest.approx(160.0, rel=1e-14)
    assert push["g_eff_mps2"] == pytest.approx(g_eff, rel=1e-15)
    assert push["drag_free_apex_m"] == pytest.approx(
        GATE_EXIT_SPEED_MPS**2 / (2.0 * g_eff), rel=1e-14
    )
    _, resolved = _resolve(basis, appform.preset_form(basis, "silo_cold_200m"))
    push = appform.derived(resolved)["push"]
    assert push["typed"] == "exit_speed_mps" and push["stroke_m"] == 200.0
    assert push["net_accel_g"] == pytest.approx(1.5, rel=1e-12)
    assert push["exit_speed_mps"] == pytest.approx(GATE_EXIT_SPEED_MPS, rel=1e-15)


def test_ramp_start_conversions_against_the_simulator(basis: appform.Basis) -> None:
    """The ramp start four ways for each way of stating it, on the 3 g0, 100 m silo,
    against the IgnitionSpec the simulator builds (sim.run_ignition_specs: the same
    conversions as a run): depth 50 m, speed 30 m/s, closed-form height 40 m (back to
    40 m), event height 40 m (an estimate, the closed form's time), 2 s before release
    on the carriage (94.6 m below the mouth at 17.9 m/s: the committed file's comment),
    2 s before push start (on the floor at rest) and 0.5 s after release (above the
    mouth, the drag-free coast)."""
    a = 3.0 * G0_MPS2
    t_push = math.sqrt(2.0 * 100.0 / a)

    def ramp(**changes: Any) -> tuple[dict[str, Any], Any]:
        form = dataclasses.replace(appform.preset_form(basis, "silo_cold"), **changes)
        _, resolved = _resolve(basis, form)
        run = resolved.variants[next(iter(resolved.variants))]
        spec = sim.run_ignition_specs(run.run, run.to_vehicle())["stage1"]
        return appform.derived(resolved)["ramp_start"], spec

    r, spec = ramp(ramp_by="depth", t_ign_s=None, at_depth_m=50)
    assert spec.reference == "push_start" and r["time_from_push_start_s"] == spec.t_ign_s
    assert r["time_from_push_start_s"] == pytest.approx(math.sqrt(2.0 * 50.0 / a), rel=1e-14)
    assert r["depth_m"] == pytest.approx(50.0, rel=1e-12) and r["height_m"] is None
    r, spec = ramp(ramp_by="speed", t_ign_s=None, at_speed_mps=30)
    assert r["time_from_push_start_s"] == spec.t_ign_s == pytest.approx(30.0 / a, rel=1e-15)
    assert r["speed_mps"] == pytest.approx(30.0, rel=1e-14)
    r, spec = ramp(ramp_by="height_closed_form", t_ign_s=None, at_height_m=40)
    assert spec.reference == "release" and r["time_after_release_s"] == spec.t_ign_s
    assert r["height_m"] == pytest.approx(40.0, rel=1e-12) and not r["estimate"]
    closed = r["time_after_release_s"]
    r, spec = ramp(ramp_by="height_event", t_ign_s=None, at_height_m=40)
    assert spec.lights_at_height and r["estimate"]
    assert r["time_after_release_s"] == pytest.approx(closed, rel=1e-15)
    r, _ = ramp(t_ign_s=-2.0)
    t_ps = t_push - 2.0
    assert r["time_from_push_start_s"] == pytest.approx(t_ps, rel=1e-14)
    assert r["depth_m"] == pytest.approx(100.0 - 0.5 * a * t_ps**2, rel=1e-13)
    assert r["speed_mps"] == pytest.approx(a * t_ps, rel=1e-13)
    assert round(r["depth_m"], 1) == 94.6 and round(r["speed_mps"], 1) == 17.9
    r, _ = ramp(ramp_by="time_push_start", t_ign_s=-2.0)
    assert r["time_from_push_start_s"] == -2.0 and r["depth_m"] == 100 and r["speed_mps"] == 0.0
    r, _ = ramp()
    assert r["time_after_release_s"] == 0.5 and r["depth_m"] is None
    g = appform.derived(_resolve(basis, appform.preset_form(basis, "silo_cold"))[1])["push"][
        "g_eff_mps2"
    ]
    assert r["height_m"] == pytest.approx(GATE_EXIT_SPEED_MPS * 0.5 - 0.5 * g * 0.25, rel=1e-14)


def test_derived_names_and_expected_durations(basis: appform.Basis) -> None:
    """The run names a launch writes and its expected range from the work in the
    offload block: pad, variant, the stage-1 pad control, the solve with its
    verification, the paired pad; the pad left out when cached."""
    _, resolved = _resolve(basis, appform.preset_form(basis, "silo_cold_s1"))
    d = appform.derived(resolved)
    assert d["runs"] == [
        "pad",
        "silo_cold",
        "silo_cold_s1",
        "silo_cold_s1__pad",
        "pad__offload_stage1",
    ]
    parts = [
        appform.SEARCHED_RUN_S,
        appform.SEARCHED_RUN_S,
        appform.PAD_CONTROL_S["stage1"],
        appform.SOLVE_WITH_VERIFICATION_S,
        appform.PAIRED_PAD_S,
    ]
    assert d["expected_s"] == [sum(p[0] for p in parts), sum(p[1] for p in parts)]
    cached = appform.derived(resolved, pad_cached=True)
    assert cached["expected_s"] == [
        d["expected_s"][0] - appform.SEARCHED_RUN_S[0],
        d["expected_s"][1] - appform.SEARCHED_RUN_S[1],
    ]
    assert "measured" in d["expected_note"] and "load" in d["expected_note"]
    # the shipped silo_cold_s1 preset launched in 90 s in all in the A4 review (pad 13 s,
    # variant 16 s, comparison 59 s, writing 2 s): the range's lower end is not above it
    assert d["expected_s"][0] <= 90.0 <= d["expected_s"][1]


def test_a_lag_startup_scales_its_expected_durations(basis: appform.Basis) -> None:
    """A stage-1 lag of time constant tau multiplies the runs that fly it by 1 + 1 s /
    tau (LAG_SLOWDOWN_REF_S): silo_cold_lag's variant (tau 1 s) 2x, tau 0.5 s 3x, a lag
    stage-1 solve's solve with its verification 3x at 0.5 s; the pad, the stage-1 pad
    control and the paired pad fly the baseline's ramp and keep their ranges; a ramp or a
    step override and a failed ignition are not scaled."""
    assert appform.LAG_SLOWDOWN_REF_S == 1.0

    def items(form: appform.Form) -> dict[str, tuple[float, float]]:
        d = appform.derived(_resolve(basis, form)[1])
        los = [i[1] for i in d["expected_items"]]
        his = [i[2] for i in d["expected_items"]]
        assert d["expected_s"] == [sum(los), sum(his)]
        return {label: (lo, hi) for label, lo, hi in d["expected_items"]}

    lo, hi = appform.SEARCHED_RUN_S
    lag = appform.preset_form(basis, "silo_cold_lag")
    assert lag.startup == "lag" and lag.tau_s == 1.0
    got = items(lag)
    assert got["pad baseline pad"] == (lo, hi)
    assert got["variant silo_cold_lag"] == (2 * lo, 2 * hi)
    fast = dataclasses.replace(lag, tau_s=0.5)
    assert items(fast)["variant silo"] == (3 * lo, 3 * hi)
    solve = dataclasses.replace(fast, propellant="solve", solve_mode="stage1", paired_pad=True)
    got = items(solve)
    s_lo, s_hi = appform.SOLVE_WITH_VERIFICATION_S
    assert got["solve silo_s1"] == (3 * s_lo, 3 * s_hi)
    assert got["pad control stage1"] == appform.PAD_CONTROL_S["stage1"]
    assert got["paired pad silo_s1__pad"] == appform.PAIRED_PAD_S
    failed = appform.preset_form(basis, "silo_failed")
    for form in (
        dataclasses.replace(lag, startup="ramp", tau_s=None, t_ramp_s=3.0),
        dataclasses.replace(lag, startup="step", tau_s=None),
        dataclasses.replace(failed, startup="lag", tau_s=0.5),
    ):
        (run,) = _resolve(basis, form)[1].variants.values()
        assert appform.stage1_lag_tau_s(run) is None and appform.lag_slowdown(run) == 1.0


def test_the_exploratory_label_is_planar_and_unswept(committed: dict[str, Any]) -> None:
    """label exploratory (the app's) is refused on an experiment with sweeps and on a 1-D
    one: only the planar experiment summary prints the exploratory banner."""
    scr = copy.deepcopy(committed["scr"])
    assert scr["sweeps"]
    scr["label"] = "exploratory"
    with pytest.raises(ValueError, match="label: exploratory is the app's"):
        resolve_experiment(scr, copy.deepcopy(committed["veh"]))
    one_d = yaml.safe_load(
        (sup.REPO_ROOT / "experiments" / "silo_screening_1d.yaml").read_text(encoding="utf-8")
    )
    one_d.pop("sweeps", None)
    one_d["label"] = "exploratory"
    vehicle_1d = yaml.safe_load((sup.REPO_ROOT / one_d["vehicle"]).read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="label: exploratory is the app's"):
        resolve_experiment(one_d, vehicle_1d)
    off = copy.deepcopy(committed["off"])
    off.pop("sweeps")
    off["label"] = "exploratory"
    assert (
        resolve_experiment(off, copy.deepcopy(committed["veh"])).experiment.label == "exploratory"
    )


# ------------------------------------------------------------------ guards


def test_the_label_is_the_replays() -> None:
    """config.EXPLORATORY_LABEL is an ExperimentLabel and equals replay.EXPLORATORY_LABEL."""
    assert config.EXPLORATORY_LABEL == replay.EXPLORATORY_LABEL == "exploratory"
    assert "exploratory" in config.ExperimentLabel.__args__


def test_building_never_mutates_the_basis(basis: appform.Basis) -> None:
    """Every preset built and resolved twice leaves the basis's dicts as they were."""
    before = copy.deepcopy(
        (basis.offload_experiment, basis.screening_experiment, basis.vehicle, basis.shared)
    )
    for _ in range(2):
        appform.presets(basis)
    after = (basis.offload_experiment, basis.screening_experiment, basis.vehicle, basis.shared)
    assert after == before


def test_appform_is_pure_and_off_the_run_path() -> None:
    """In a fresh interpreter importing appform loads no I/O module (run_data, replay,
    scene, plots, results_io, sim, summary, app, cli) and no YAML reader; importing sim
    and results_io (the run path, with everything it pulls in) loads neither appform nor
    app (D-SP2-18); no module of the run path imports appform or app (source scan)."""
    code = (
        "import json, sys\n"
        "import launchsim.appform\n"
        f"print(json.dumps(sorted(m for m in sys.modules if m in {IO_MODULES!r})))\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout.strip().splitlines()[-1]) == []
    run_path = (
        "import json, sys\n"
        "import launchsim.sim, launchsim.results_io\n"
        "print(json.dumps(sorted(m for m in sys.modules "
        "if m in ('launchsim.app', 'launchsim.appform'))))\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", run_path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout.strip().splitlines()[-1]) == []
    banned = {"launchsim.app", "launchsim.appform"}
    offenders = []
    for module in RUN_PATH_MODULES:
        tree = ast.parse((SRC / f"{module}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                names = {f"{node.module}.{a.name}" for a in node.names} | {str(node.module)}
                if names & banned:
                    offenders.append(module)
            elif isinstance(node, ast.Import) and {a.name for a in node.names} & banned:
                offenders.append(module)
    assert not offenders, offenders
