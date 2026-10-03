"""Planar experiment schema (build step 19): the model selector, the experiment-level
shared blocks (dynamics, site, guidance, search, target_orbit, checks) injected into
every run and refused per run, end: insertion, integrator.method, the search, LTG and
checks blocks, paired sweeps (guidance_study only), calibration cases, bounds, the
automatic search skip (amendment 4), sensitivity paths (amendment 5), the aero bound
(amendment 6) and baseline identity across experiments (amendment 15). The shipped
Phase 2 experiments must resolve, the Phase 1 run dicts must stay byte-identical
to the 1-D golden, and every run and vehicle dict the four shipped planar experiments
resolve keeps its pinned sha256 (SP1 step 1; tests/planar_pin_support.py). The two
pre-registered offload experiments of SP1 step 8 (silo_offload_2d and its README-loads
bridge) are checked for the properties their design rests on. Expected numbers are
computed here from the YAML inputs."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from launchsim import cli, plots, results_io, sim, summary
from launchsim.assist.constant_accel import ConstantAccelAssist
from launchsim.config import (
    BLOCKING_ROLE,
    BRENTQ_MIN_RTOL,
    DIAGNOSTIC_ROLE,
    PLANAR_SHARED_KEYS,
    SHARED_KEYS,
    ChecksConfig,
    ConstantAccelConfig,
    ConvergenceConfig,
    ExperimentConfig,
    GuidanceConfig,
    IntegratorConfig,
    KickConfig,
    LtgConfig,
    PenaltyConfig,
    PlanarSiteConfig,
    ResolvedExperiment,
    RunConfig,
    SearchConfig,
    SiteConfig,
    Stage2GuidanceConfig,
    TrackConfig,
    inject_shared,
    offload_run_names,
    resolve_experiment,
    resolve_run,
    shared_run_blocks,
)
from launchsim.constants import G0_MPS2, MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M
from launchsim.phases import IntegratorSettings
from launchsim.results_io import check_name

PLANAR_EXPERIMENTS = (
    "calibration_f9_2d",
    "silo_screening_2d",
    "silo_bridge_2d_readme",
    "guidance_trigger_2d",
    "silo_offload_2d",
    "silo_offload_2d_readme",
)
SITE_LAT_DEG = 28.5
KM = 1000.0
EQUATOR_EAST_SITE_SPEED_MPS = 465.1  # CLAUDE.md release-mapping value, 4 figures


def _load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _experiment_path(repo_root: Path, name: str) -> Path:
    return repo_root / "experiments" / f"{name}.yaml"


def _resolve_file(path: Path) -> ResolvedExperiment:
    """Resolve an experiment file the way the CLI will: its vehicle and every case
    vehicle located by cli.resolve_vehicle_path and read by cli.load_yaml."""
    exp = cli.load_yaml(path)
    vehicle = cli.load_yaml(cli.resolve_vehicle_path(path, exp["vehicle"]))
    return resolve_experiment(
        exp, vehicle, lambda p: cli.load_yaml(cli.resolve_vehicle_path(path, p))
    )


@pytest.fixture(scope="module")
def raw(repo_root: Path) -> dict[str, dict[str, Any]]:
    """Raw dicts of every shipped planar experiment (PLANAR_EXPERIMENTS)."""
    return {n: _load(_experiment_path(repo_root, n)) for n in PLANAR_EXPERIMENTS}


@pytest.fixture(scope="module")
def resolved(repo_root: Path) -> dict[str, ResolvedExperiment]:
    """Every shipped planar experiment (PLANAR_EXPERIMENTS), resolved."""
    return {n: _resolve_file(_experiment_path(repo_root, n)) for n in PLANAR_EXPERIMENTS}


@pytest.fixture(scope="module")
def gate_vehicle(repo_root: Path) -> dict[str, Any]:
    """Raw dict of the calibration gate fork."""
    return _load(repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml")


@pytest.fixture()
def silo2d(raw: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """A fresh copy of silo_screening_2d to break."""
    return copy.deepcopy(raw["silo_screening_2d"])


def _small(exp: dict[str, Any]) -> dict[str, Any]:
    """The experiment without sweeps, sensitivity and bounds (fast to resolve)."""
    return {k: v for k, v in exp.items() if k not in ("sweeps", "sensitivity", "bounds")}


# ------------------------------------------------------------------ shipped experiments


def test_shipped_planar_experiments_resolve(resolved: dict[str, ResolvedExperiment]) -> None:
    cal = resolved["calibration_f9_2d"]
    assert cal.experiment.label == "calibration" and not cal.variants and not cal.sweeps
    assert list(cal.cases) == [
        "readme_loads",
        "recorded_scope",
        "aref_fairing",
        "alt_185",
        "alt_250",
        "alt_300",
        "no_rotation",
    ]
    assert len(cal.sensitivity) == 4 * 2
    silo = resolved["silo_screening_2d"]
    assert list(silo.variants) == [
        "pad_instant",
        "silo_instant",
        "silo_cold",
        "silo_cold_lag",
        "silo_hot_ramp_on_track",
        "silo_hot_full",
        "silo_hot_full_impinged",
        "silo_failed",
        "silo_sled_22t",
    ]
    assert [len(s) for s in silo.sweeps] == [4 * 3, 3 * 3, 3]  # amendment 12: ignition sweeps
    assert len(silo.sensitivity) == 2 * 6 * 2
    assert list(resolved["silo_bridge_2d_readme"].variants) == [
        "pad_instant",
        "silo_instant",
        "silo_cold",
    ]
    trig = resolved["guidance_trigger_2d"]
    assert trig.experiment.label == "guidance_study" and [len(s) for s in trig.sweeps] == [4]
    for r in resolved.values():
        for run in [*r.runs.values(), *r.cases.values()]:
            assert run.run.dynamics == "planar_2d"
            assert isinstance(run.run.site, PlanarSiteConfig)
            assert run.run.planar is not None
            assert run.run.integrator.rtol == run.run.planar.search.final_rtol


def test_shared_blocks_are_identical_across_the_planar_experiments(
    raw: dict[str, dict[str, Any]], resolved: dict[str, ResolvedExperiment]
) -> None:
    ref = {k: raw["calibration_f9_2d"][k] for k in SHARED_KEYS}
    for name in PLANAR_EXPERIMENTS:
        assert {k: raw[name][k] for k in SHARED_KEYS} == ref, name
    planar = {r.baseline.run.planar for r in resolved.values()}
    assert len(planar) == 1
    ids = {r.baseline.run.planar.search.budget_id() for r in resolved.values()}
    assert len(ids) == 1
    # the calibration and silo experiments fly the same vehicle file
    assert raw["calibration_f9_2d"]["vehicle"] == raw["silo_screening_2d"]["vehicle"]
    assert raw["guidance_trigger_2d"]["vehicle"] == raw["silo_screening_2d"]["vehicle"]


def test_calibration_and_silo_baselines_differ_only_in_sample_dt(
    resolved: dict[str, ResolvedExperiment],
) -> None:
    """Amendment 15: resolved baseline run dicts identical except sample_dt_s."""
    cal = copy.deepcopy(resolved["calibration_f9_2d"].baseline.run_dict)
    silo = copy.deepcopy(resolved["silo_screening_2d"].baseline.run_dict)
    assert cal["integrator"].pop("sample_dt_s") != silo["integrator"].pop("sample_dt_s")
    assert json.dumps(cal) == json.dumps(silo)  # key order included
    assert (
        resolved["calibration_f9_2d"].baseline.vehicle_dict
        == resolved["silo_screening_2d"].baseline.vehicle_dict
    )


def test_shipped_blocks_state_every_threshold(raw: dict[str, dict[str, Any]]) -> None:
    """Pre-registration: every search, LTG, checks and guidance field is written out in
    the shipped files (no silent default), and the headline values are the plan's."""
    exp = raw["calibration_f9_2d"]
    fixed = {"fixed_gamma_star_deg", "fixed_ltg_a", "fixed_ltg_b_per_s"}
    assert set(exp["search"]) == set(SearchConfig.model_fields) - fixed
    assert set(exp["search"]["ltg"]) == set(LtgConfig.model_fields)
    assert set(exp["checks"]) == set(ChecksConfig.model_fields)
    assert set(exp["checks"]["convergence"]) == set(ConvergenceConfig.model_fields)
    assert set(exp["guidance"]) == set(GuidanceConfig.model_fields)
    assert set(exp["guidance"]["kick"]) == set(KickConfig.model_fields)
    assert set(exp["guidance"]["stage2"]) == set(Stage2GuidanceConfig.model_fields)
    assert set(exp["search"]["penalty"]) == set(PenaltyConfig.model_fields)
    search = SearchConfig.model_validate(exp["search"])
    assert search.gamma_grid_points_deg == tuple(float(g) for g in range(8, 37, 2))
    assert search.brentq_rtol == BRENTQ_MIN_RTOL
    assert (search.search_rtol, search.final_rtol) == (1e-8, 1e-10)
    assert exp["guidance"]["kick"]["v_kick_mps"] == 50
    assert exp["target_orbit"] == {"kind": "circular", "altitude_km": 200}
    assert exp["site"] == {
        "latitude_deg": SITE_LAT_DEG,
        "azimuth_deg": 90,
        "include_rotation": True,
    }


def test_injected_blocks_and_site_quantities(resolved: dict[str, ResolvedExperiment]) -> None:
    run = resolved["calibration_f9_2d"].baseline
    assert list(run.run_dict)[:4] == ["name", "dynamics", "site", "planar"]
    assert list(run.run_dict["planar"]) == list(PLANAR_SHARED_KEYS)
    lat = math.radians(SITE_LAT_DEG)
    assert run.run.site.omega_p_rads == pytest.approx(OMEGA_EARTH_RADS * math.cos(lat), rel=1e-15)
    target = run.run.planar.target_orbit
    assert target.radius_m == R_EARTH_M + 200 * KM
    assert run.run.figure_of_merit == "payload" and run.run.search_skip_reason is None
    assert run.to_vehicle().aero is not None


# ------------------------------------------------------------------- Phase 1 unchanged


def _golden_run_dicts(repo_root: Path, gset: str) -> dict[str, Any]:
    """Every run dict (and differing vehicle dict) the 1-D golden pinned for a set."""
    golden = repo_root / "tests" / "data" / "golden" / gset
    out: dict[str, Any] = {}
    cfg = json.loads((golden / "experiment" / "resolved_config.json").read_text(encoding="utf-8"))
    for name, entry in cfg["runs"].items():
        out[f"run:{name}"] = entry["run"]
    objects = json.loads((golden / "experiment" / "objects.json").read_text(encoding="utf-8"))
    for row in objects["sensitivity"]:
        out[f"sens:{row['result']['name']}"] = (
            row["result"]["run_dict"],
            row["result"]["vehicle_dict"],
        )
    sweep_objects = golden / "sweep" / "objects.json"
    if sweep_objects.exists():
        sweeps = json.loads(sweep_objects.read_text(encoding="utf-8"))
        for key, sweep in sweeps.items():
            for pt in sweep["points"]:
                out[f"{key}:{pt['run']['name']}"] = (
                    pt["run"]["run_dict"],
                    pt["run"]["vehicle_dict"],
                )
    return out


@pytest.mark.parametrize(
    ("gset", "experiment"),
    [
        ("silo_screening_1d", "experiments/silo_screening_1d.yaml"),
        ("vertical_1d_paths", "tests/data/golden/inputs/vertical_1d_paths.yaml"),
    ],
)
def test_phase1_resolved_run_dicts_are_byte_identical(
    repo_root: Path, gset: str, experiment: str
) -> None:
    """1-D experiments declare no shared block, so nothing is injected: every run,
    sweep-point and sensitivity run dict equals the golden (key order included)."""
    r = _resolve_file(repo_root / experiment)
    base_vehicle = r.baseline.vehicle_dict
    actual: dict[str, Any] = {f"run:{n}": rr.run_dict for n, rr in r.runs.items()}
    for case in r.sensitivity:
        v = None if case.run.vehicle_dict == base_vehicle else case.run.vehicle_dict
        actual[f"sens:{case.run.name}"] = (case.run.run_dict, v)
    for points in r.sweeps:
        for pt in points:
            v = None if pt.run.vehicle_dict == base_vehicle else pt.run.vehicle_dict
            actual[f"sweep_{pt.sweep_index}:{pt.run.name}"] = (pt.run.run_dict, v)
            assert pt.paired_baseline is None
    golden = _golden_run_dicts(repo_root, gset)
    assert json.dumps(actual) == json.dumps(golden)
    assert not r.bounds and not r.cases
    for rr in r.runs.values():
        assert rr.run.dynamics == "vertical_1d" and rr.run.planar is None
        assert rr.run.figure_of_merit is None and rr.run.search_skip_reason is None


def test_inject_shared_is_a_plain_copy_when_nothing_is_declared(
    repo_root: Path,
) -> None:
    exp = _load(repo_root / "experiments" / "silo_screening_1d.yaml")
    assert shared_run_blocks(exp) == {}
    out = inject_shared(exp["baseline"], {})
    assert out == exp["baseline"] and out is not exp["baseline"]
    assert list(out) == list(exp["baseline"])


# ------------------------------------------------- shipped planar experiments unchanged


def _declared_run_count(exp: dict[str, Any]) -> int:
    """How many runs a raw experiment dict declares, counted from the YAML alone: the
    baseline, the variants, every sweep grid point (the product of its axis lengths,
    twice when paired: the point and its paired baseline), two runs (+ and -) per
    sensitivity run and parameter, every bound re-run plus its paired baseline, and
    the calibration cases."""
    count = 1 + len(exp.get("variants", {}))
    for sweep in exp.get("sweeps", []):
        points = math.prod(len(values) for values in sweep["axes"].values())
        count += points * (2 if sweep.get("paired", False) else 1)
    sensitivity = exp.get("sensitivity")
    if sensitivity is not None:
        count += 2 * len(sensitivity["of"]) * len(sensitivity["params"])
    count += sum(len(bound["of"]) + 1 for bound in exp.get("bounds", []))
    return count + len(exp.get("cases", {}))


def test_shipped_planar_resolved_dicts_match_the_pinned_digests(
    raw: dict[str, dict[str, Any]],
    resolved: dict[str, ResolvedExperiment],
    planar_pins: ModuleType,
) -> None:
    """SP1 step 1 guard (tests/planar_pin_support.py): every run and vehicle dict the
    four shipped planar experiments resolve (runs, sweep points and their paired
    baselines, sensitivity runs, bound runs, calibration cases) has the sha256 of
    ``json.dumps`` (key order kept) that the untouched code produced before
    merge_run_dicts and _set_path learned the exclusive key families. The number of
    pinned dicts per experiment equals the count declared in the YAML, so nothing a
    file resolves escapes the pin."""
    pinned = planar_pins.read_json(planar_pins.DIGESTS_FILE)["experiments"]
    assert tuple(pinned) == planar_pins.PINNED_EXPERIMENTS
    assert set(planar_pins.PINNED_EXPERIMENTS) <= set(PLANAR_EXPERIMENTS)
    for name in planar_pins.PINNED_EXPERIMENTS:
        actual = planar_pins.resolved_digests(resolved[name])
        assert len(pinned[name]) == _declared_run_count(raw[name]), name
        problems = planar_pins.compare_digests(actual, pinned[name])
        assert not problems, f"{name}:\n" + "\n".join(problems)


def test_pinned_digest_is_the_sha256_of_the_json_text(planar_pins: ModuleType) -> None:
    """The digest is sha256(json.dumps(d)) over UTF-8, so it sees values, added keys and
    key order; compare_digests names what changed."""
    assert planar_pins.dict_digest({"a": 1}) == hashlib.sha256(b'{"a": 1}').hexdigest()
    base = {"a": 1, "b": {"c": 2.0}}
    digest = planar_pins.dict_digest(base)
    assert planar_pins.dict_digest({"b": {"c": 2.0}, "a": 1}) != digest  # key order
    assert planar_pins.dict_digest({"a": 1, "b": {"c": 2.0, "d": None}}) != digest
    assert planar_pins.dict_digest({"a": 1, "b": {"c": 2.0000000000000004}}) != digest
    pin = {"run:x": {"run": "1", "vehicle": "2"}, "run:y": {"run": "3", "vehicle": "2"}}
    assert planar_pins.compare_digests(pin, pin) == []
    moved = {"run:x": {"run": "9", "vehicle": "2"}, "run:z": {"run": "3", "vehicle": "2"}}
    assert planar_pins.compare_digests(moved, pin) == [
        "run:y: no longer resolved",
        "run:z: not in the pin",
        "run:x: the run dict changed",
    ]
    swapped = {"run:y": pin["run:y"], "run:x": pin["run:x"]}
    assert planar_pins.compare_digests(swapped, pin) == ["the order of the resolved runs changed"]


# ---------------------------------------------------------------------- model rules


def test_rotation_only_for_planar(silo2d: dict[str, Any], gate_vehicle: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="Phase 2 feature: it needs dynamics: planar_2d"):
        SiteConfig(include_rotation=True)
    with pytest.raises(ValidationError, match="needs dynamics: planar_2d"):
        RunConfig.model_validate({"name": "x", "site": {"include_rotation": True}})
    rotating = PlanarSiteConfig(latitude_deg=SITE_LAT_DEG, azimuth_deg=90.0, include_rotation=True)
    with pytest.raises(ValidationError, match="needs dynamics: planar_2d"):
        RunConfig(name="x", site=rotating)  # a planar site instance on a vertical_1d run
    one_d = {k: v for k, v in _small(silo2d).items() if k not in (*PLANAR_SHARED_KEYS, "dynamics")}
    one_d["baseline"] = {**one_d["baseline"], "end": "stage1_burnout"}
    one_d.pop("variants")
    with pytest.raises(ValidationError, match="needs dynamics: planar_2d"):
        ExperimentConfig.model_validate(one_d)
    # planar: rotation on and off are both allowed, and stated
    no_rot = copy.deepcopy(_small(silo2d))
    no_rot["site"]["include_rotation"] = False
    r = resolve_experiment(no_rot, gate_vehicle)
    assert r.baseline.run.site.omega_p_rads == 0.0


def test_planar_needs_an_explicit_site(
    silo2d: dict[str, Any], gate_vehicle: dict[str, Any]
) -> None:
    exp = _small(silo2d)
    missing = {k: v for k, v in exp.items() if k != "site"}
    with pytest.raises(ValidationError, match="explicit experiment-level site"):
        resolve_experiment(missing, gate_vehicle)
    partial = copy.deepcopy(exp)
    del partial["site"]["include_rotation"]
    with pytest.raises(ValidationError, match="each given explicitly"):
        resolve_experiment(partial, gate_vehicle)
    in_baseline = copy.deepcopy(missing)
    in_baseline["baseline"]["site"] = exp["site"]
    with pytest.raises(ValidationError, match="baseline sets 'site'"):
        resolve_experiment(in_baseline, gate_vehicle)


def test_planar_needs_guidance_search_checks_and_a_target(
    silo2d: dict[str, Any], gate_vehicle: dict[str, Any]
) -> None:
    exp = _small(silo2d)
    for key in ("guidance", "search", "checks"):
        bad = {k: v for k, v in exp.items() if k != key}
        with pytest.raises(ValidationError, match=rf"planar\.{key}"):
            resolve_experiment(bad, gate_vehicle)
    bad = {k: v for k, v in exp.items() if k != "target_orbit"}
    with pytest.raises(ValidationError, match="needs target_orbit"):
        resolve_experiment(bad, gate_vehicle)


def test_planar_needs_aero_and_two_stages(
    silo2d: dict[str, Any], gate_vehicle: dict[str, Any], f9_vehicle_dict: dict[str, Any]
) -> None:
    exp = _small(silo2d)
    with pytest.raises(ValueError, match="needs the vehicle's aero block"):
        resolve_experiment(exp, f9_vehicle_dict)
    one_stage = copy.deepcopy(gate_vehicle)
    one_stage["stages"] = one_stage["stages"][:1]
    one_stage["screening"]["stage_isp_eff_s"] = one_stage["screening"]["stage_isp_eff_s"][:1]
    exp["baseline"] = {**exp["baseline"], "ignition": {"stage1": {"t_ign_s": -2.0}}}
    with pytest.raises(ValueError, match="needs a 2-stage vehicle, got 1"):
        resolve_experiment(exp, one_stage)


def test_integrator_rtol_must_equal_final_rtol(
    silo2d: dict[str, Any], gate_vehicle: dict[str, Any]
) -> None:
    exp = _small(silo2d)
    exp["baseline"]["integrator"]["rtol"] = 1.0e-9
    with pytest.raises(ValidationError, match=r"integrator\.rtol \(1e-09\) must equal"):
        resolve_experiment(exp, gate_vehicle)
    exp["search"]["final_rtol"] = 1.0e-9
    assert resolve_experiment(exp, gate_vehicle).baseline.run.integrator.rtol == 1.0e-9


def test_insertion_end_rules(silo2d: dict[str, Any], gate_vehicle: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="end: insertion needs dynamics: planar_2d"):
        RunConfig.model_validate({"name": "x", "end": "insertion"})
    exp = _small(silo2d)
    exp["baseline"]["end"] = "all_burnout"
    with pytest.raises(ValidationError, match="not a planar_2d end"):
        resolve_experiment(exp, gate_vehicle)
    exp["baseline"]["end"] = "apex"
    with pytest.raises(ValidationError, match="payload needs end: insertion"):
        resolve_experiment(exp, gate_vehicle)


def test_planar_blocks_need_planar_dynamics(silo2d: dict[str, Any]) -> None:
    exp = _small(silo2d)
    exp["dynamics"] = "vertical_1d"
    exp.pop("site")
    with pytest.raises(ValidationError, match="are planar_2d blocks"):
        ExperimentConfig.model_validate(exp)


def test_integrator_method_round_trip() -> None:
    doc = yaml.safe_load("integrator: {method: RK45, rtol: 1.0e-10}")
    cfg = IntegratorConfig.model_validate(doc["integrator"])
    assert IntegratorSettings.from_config(cfg).method == "RK45"
    assert IntegratorSettings.from_config(IntegratorConfig()).method == "DOP853"
    with pytest.raises(ValidationError):
        IntegratorConfig.model_validate({"method": "LSODA"})


def test_tilted_track_names_phase_3() -> None:
    with pytest.raises(ValidationError, match="Phase 3 feature"):
        TrackConfig(angle_deg=45)


def test_heating_fairing_is_refused_only_on_vertical_1d(
    repo_root: Path, gate_vehicle: dict[str, Any], resolved: dict[str, ResolvedExperiment]
) -> None:
    exp = _load(repo_root / "experiments" / "silo_screening_1d.yaml")
    with pytest.raises(ValueError, match="free_molecular_heating is a planar_2d feature"):
        resolve_run("pad", exp["baseline"], gate_vehicle)
    assert resolved["silo_screening_2d"].baseline.to_vehicle().fairing_rule.trigger == (
        "free_molecular_heating"
    )


# -------------------------------------------------------- shared blocks stay shared


@pytest.mark.parametrize(
    "variant",
    [
        {"search": {"final_rtol": 1.0e-11}},
        {"guidance": {"kick": {"v_kick_mps": 80}}},
        {"target_orbit": {"altitude_km": 300}},
        {"checks": {"closure_tol_mps": 1.0}},
        {"site": {"include_rotation": False}},
        {"dynamics": "vertical_1d"},
        {"planar": {}},
    ],
)
def test_variants_may_not_touch_shared_blocks(
    silo2d: dict[str, Any], gate_vehicle: dict[str, Any], variant: dict[str, Any]
) -> None:
    exp = _small(silo2d)
    exp["variants"] = {"silo_cold": {**exp["variants"]["silo_cold"], **variant}}
    with pytest.raises(ValidationError, match="experiment-level shared block"):
        resolve_experiment(exp, gate_vehicle)


def test_phase1_variants_may_not_move_the_site(repo_root: Path, f9_vehicle_dict: dict) -> None:
    exp = _load(repo_root / "experiments" / "silo_screening_1d.yaml")
    exp["variants"]["silo_cold"]["site"] = {"latitude_deg": 0.0}
    with pytest.raises(ValidationError, match="variant 'silo_cold' sets 'site'"):
        resolve_experiment(exp, f9_vehicle_dict)
    exp = _load(repo_root / "experiments" / "silo_screening_1d.yaml")
    exp["site"] = {"latitude_deg": 0.0}
    with pytest.raises(ValidationError, match="declare it once"):
        resolve_experiment(exp, f9_vehicle_dict)
    # declared once at experiment level instead, it is injected into every run
    del exp["baseline"]["site"]
    r = resolve_experiment(exp, f9_vehicle_dict)
    for rr in r.runs.values():
        assert list(rr.run_dict)[:2] == ["name", "site"]
        assert rr.run.site == SiteConfig(latitude_deg=0.0)
        assert rr.run.dynamics == "vertical_1d" and "dynamics" not in rr.run_dict


@pytest.mark.parametrize(
    "path",
    ["search.final_rtol", "guidance.kick.v_kick_mps", "site.latitude_deg", "planar.checks"],
)
def test_sweeps_sensitivity_and_bounds_may_not_touch_shared_blocks(
    silo2d: dict[str, Any], gate_vehicle: dict[str, Any], path: str
) -> None:
    sweep = copy.deepcopy(silo2d)
    sweep["sweeps"] = [{"of": "silo_cold", "axes": {path: [1.0]}}]
    with pytest.raises(ValidationError, match="shared block"):
        resolve_experiment(sweep, gate_vehicle)
    sens = copy.deepcopy(silo2d)
    sens["sensitivity"] = {"of": ["silo_cold"], "params": {path: 0.1}}
    with pytest.raises(ValidationError, match="shared block"):
        resolve_experiment(sens, gate_vehicle)
    bound = copy.deepcopy(silo2d)
    bound["bounds"] = [{"name": "b", "of": ["silo_cold"], "overrides": {path: 1.0}}]
    with pytest.raises(ValidationError, match="shared block"):
        resolve_experiment(bound, gate_vehicle)


@pytest.mark.parametrize("key", ["dynamics", "search", "planar"])
def test_baseline_may_not_declare_shared_blocks(
    silo2d: dict[str, Any], gate_vehicle: dict[str, Any], key: str
) -> None:
    exp = _small(silo2d)
    exp["baseline"][key] = copy.deepcopy(exp.get(key, {}))
    with pytest.raises(ValidationError, match=f"baseline sets '{key}'"):
        resolve_experiment(exp, gate_vehicle)


# ------------------------------------------------------------------ paired sweeps


def test_paired_sweep_reruns_the_baseline_with_the_same_guidance(
    resolved: dict[str, ResolvedExperiment],
) -> None:
    trig = resolved["guidance_trigger_2d"]
    for pt, v_k in zip(trig.sweeps[0], (30, 50, 80, 120), strict=True):
        assert pt.overrides == {"guidance.kick.v_kick_mps": v_k}
        assert pt.run.run.planar.guidance.kick.v_kick_mps == v_k
        pair = pt.paired_baseline
        assert pair is not None and pair.name == f"{pt.run.name}__pad"
        assert pair.run.planar.guidance.kick.v_kick_mps == v_k
        assert pair.run.assist.model == "none" and pt.run.run.assist.model == "constant_accel"
        rest = copy.deepcopy(pair.run_dict)
        base = copy.deepcopy(trig.baseline.run_dict)
        for d in (rest, base):
            d.pop("name")
            d["planar"]["guidance"]["kick"].pop("v_kick_mps")
        assert rest == base  # the pair differs from the baseline only in v_k
    assert trig.baseline.run.planar.guidance.kick.v_kick_mps == 50


def test_paired_sweep_rules(raw: dict[str, dict[str, Any]], gate_vehicle: dict[str, Any]) -> None:
    exp = copy.deepcopy(raw["guidance_trigger_2d"])
    unlabelled = {k: v for k, v in exp.items() if k != "label"}
    with pytest.raises(ValidationError, match="paired sweeps need label: guidance_study"):
        ExperimentConfig.model_validate(unlabelled)
    unpaired = copy.deepcopy(exp)
    unpaired["sweeps"][0]["paired"] = False
    with pytest.raises(ValidationError, match="only a paired sweep of a guidance_study"):
        ExperimentConfig.model_validate(unpaired)
    mixed = copy.deepcopy(exp)
    mixed["sweeps"][0]["axes"]["assist.stroke_m"] = [100]
    with pytest.raises(ValidationError, match=r"varies guidance\.\* and vehicle\.\* paths only"):
        ExperimentConfig.model_validate(mixed)
    of_base = copy.deepcopy(exp)
    of_base["sweeps"][0]["of"] = "pad"
    with pytest.raises(ValidationError, match="paired sweep of the baseline has no pair"):
        ExperimentConfig.model_validate(of_base)


def test_paired_sweeps_need_planar_dynamics(repo_root: Path) -> None:
    """A paired sweep in a vertical_1d experiment fails with the rule, not with the
    missing planar blocks of each resolved point."""
    exp = _small(_load(repo_root / "experiments" / "silo_screening_1d.yaml"))
    exp["label"] = "guidance_study"
    exp["sweeps"] = [
        {"of": "silo_cold", "paired": True, "axes": {"guidance.kick.v_kick_mps": [30]}}
    ]
    with pytest.raises(ValidationError, match=r"paired sweep .* needs dynamics: planar_2d"):
        ExperimentConfig.model_validate(exp)


def test_planar_vehicle_sweeps_rerun_the_baseline(
    silo2d: dict[str, Any], gate_vehicle: dict[str, Any]
) -> None:
    """A vehicle axis moves both sides of the comparison, never the assisted run alone."""
    area = "vehicle.aero.reference_area_m2"
    exp = _small(silo2d)
    exp["sweeps"] = [{"of": "silo_cold", "axes": {area: [5.0]}}]
    with pytest.raises(ValidationError, match=r"sweep of vehicle\.\* paths needs paired: true"):
        ExperimentConfig.model_validate(exp)
    exp["sweeps"][0]["paired"] = True  # no guidance axis: no guidance_study label needed
    (pt,) = resolve_experiment(exp, gate_vehicle).sweeps[0]
    assert pt.paired_baseline is not None and pt.paired_baseline.name == "run_0001__pad"
    for run in (pt.run, pt.paired_baseline):
        assert run.vehicle_dict["aero"]["reference_area_m2"]["value"] == 5.0
    assert pt.paired_baseline.run.assist.model == "none"
    guided = copy.deepcopy(exp)
    guided["sweeps"][0]["axes"]["guidance.kick.v_kick_mps"] = [30]
    with pytest.raises(ValidationError, match="paired sweeps need label: guidance_study"):
        ExperimentConfig.model_validate(guided)


def test_one_d_vehicle_sweeps_stay_unpaired(
    repo_root: Path, f9_vehicle_dict: dict[str, Any]
) -> None:
    """Phase 1 keeps its sweep freedom: the vehicle-axis rule is planar_2d only."""
    exp = _small(_load(repo_root / "experiments" / "silo_screening_1d.yaml"))
    exp["sweeps"] = [{"of": "silo_cold", "axes": {"vehicle.stages.stage1.dry_mass_t": [25.0]}}]
    (pt,) = resolve_experiment(exp, f9_vehicle_dict).sweeps[0]
    assert pt.paired_baseline is None


# ------------------------------------------------------------------ calibration cases


def test_cases_resolve_as_independent_runs(
    resolved: dict[str, ResolvedExperiment], gate_vehicle: dict[str, Any]
) -> None:
    cal = resolved["calibration_f9_2d"]
    base = cal.baseline
    assert set(cal.cases).isdisjoint(cal.runs)
    readme = cal.cases["readme_loads"]
    assert readme.vehicle.name == "generic_f9_class_2d_readme_loads"
    assert cal.cases["recorded_scope"].vehicle.name == "generic_f9_class_2d_recorded_scope"
    area = cal.cases["aref_fairing"].vehicle.aero.reference_area_m2
    assert area.value == 21.24 and area.assumed and area.note == "override"
    assert (
        base.vehicle.aero.reference_area_m2.value
        == (gate_vehicle["aero"]["reference_area_m2"]["value"])
    )
    for alt in (185, 250, 300):
        target = cal.cases[f"alt_{alt}"].run.planar.target_orbit
        assert target.altitude_km == alt and target.radius_m == R_EARTH_M + alt * KM
        assert cal.cases[f"alt_{alt}"].run.site == base.run.site
    no_rot = cal.cases["no_rotation"].run
    assert no_rot.site.omega_p_rads == 0.0
    assert no_rot.site.latitude_deg == base.run.site.latitude_deg
    for case in cal.cases.values():
        assert case.run.planar.search == base.run.planar.search
        assert case.run.planar.guidance == base.run.planar.guidance
        assert case.run.assist == base.run.assist and case.run.ignition == base.run.ignition


def test_case_rules(raw: dict[str, dict[str, Any]], gate_vehicle: dict[str, Any]) -> None:
    cal = raw["calibration_f9_2d"]
    unlabelled = {k: v for k, v in cal.items() if k != "label"}
    with pytest.raises(ValidationError, match="cases need label: calibration"):
        ExperimentConfig.model_validate(unlabelled)
    with pytest.raises(ValueError, match="needs load_vehicle"):
        resolve_experiment(cal, gate_vehicle)  # no loader: config.py reads no files
    for case, message in (
        ({}, "must change"),
        ({"overrides": {"assist.stroke_m": 50}}, "vehicle. paths only"),
        ({"search": {"final_rtol": 1.0e-11}}, "Extra inputs"),
    ):
        bad = copy.deepcopy(cal)
        bad["cases"] = {"c": case}
        with pytest.raises(ValidationError, match=message):
            ExperimentConfig.model_validate(bad)
    clash = copy.deepcopy(cal)
    clash["cases"] = {"pad": {"target_orbit": {"altitude_km": 300}}}
    with pytest.raises(ValidationError, match="'pad' is used twice"):
        ExperimentConfig.model_validate(clash)


# ------------------------------------------------------ amendments 4, 5 and 6


def test_failed_ignition_and_impact_skip_the_search(
    resolved: dict[str, ResolvedExperiment], silo2d: dict[str, Any], gate_vehicle: dict
) -> None:
    """Amendment 4: end: impact (every failed ignition) skips the search; the search
    block itself stays forbidden in variants (tested above)."""
    failed = resolved["silo_screening_2d"].variants["silo_failed"].run
    assert failed.search_skip_reason == "end: impact (ignition stage1 fails)"
    assert failed.figure_of_merit == "none"
    assert failed.planar.search.figure_of_merit == "payload"  # the shared block is untouched
    for name, rr in resolved["silo_screening_2d"].variants.items():
        if name != "silo_failed":
            assert rr.run.search_skip_reason is None and rr.run.figure_of_merit == "payload"
    # a lit stage 1 cannot fly without the search's guidance ...
    exp = _small(silo2d)
    exp["variants"] = {"lit_impact": {"end": "impact"}}
    with pytest.raises(ValueError, match="skips the search, but stage stage1 lights"):
        resolve_experiment(exp, gate_vehicle)
    # ... unless the shared search flies fixed guidance (figure_of_merit none)
    exp["search"] = {
        **exp["search"],
        "figure_of_merit": "none",
        "fixed_gamma_star_deg": 20.0,
        "fixed_ltg_a": 1.0,
        "fixed_ltg_b_per_s": 0.004,
    }
    r = resolve_experiment(exp, gate_vehicle)
    assert r.variants["lit_impact"].run.figure_of_merit == "none"
    assert r.baseline.run.planar.search.fixed_gamma_star_rad == pytest.approx(math.radians(20.0))


def test_sensitivity_paths_perturb_the_vehicle_numbers(
    resolved: dict[str, ResolvedExperiment], gate_vehicle: dict[str, Any]
) -> None:
    """Amendment 5: vehicle.stages.<stage>... paths move the vehicle file's numbers."""
    stages = {s["name"]: s for s in gate_vehicle["stages"]}
    nominal = {
        "vehicle.stages.stage1.dry_mass_t": stages["stage1"]["dry_mass_t"]["value"],
        "vehicle.stages.stage1.engine.isp_vac_s": stages["stage1"]["engine"]["isp_vac_s"]["value"],
        "vehicle.stages.stage2.engine.isp_vac_s": stages["stage2"]["engine"]["isp_vac_s"]["value"],
        "vehicle.aero.cd_scale": gate_vehicle["aero"]["cd_scale"]["value"],
    }
    cases = resolved["calibration_f9_2d"].sensitivity
    assert {(c.param, c.fraction) for c in cases} == {
        (p, s * 0.1) for p in nominal for s in (+1.0, -1.0)
    }
    for c in cases:
        vehicle = c.run.to_vehicle()
        got = {
            "vehicle.stages.stage1.dry_mass_t": vehicle.stages[0].dry_mass_kg / KM,
            "vehicle.stages.stage1.engine.isp_vac_s": vehicle.stages[0].engine.isp_vac_s,
            "vehicle.stages.stage2.engine.isp_vac_s": vehicle.stages[1].engine.isp_vac_s,
            "vehicle.aero.cd_scale": vehicle.aero.cd_scale,
        }[c.param]
        assert got == pytest.approx(nominal[c.param] * (1.0 + c.fraction), rel=1e-12)
    silo = resolved["silo_screening_2d"].sensitivity
    stage2 = [c for c in silo if c.param == "vehicle.stages.stage2.engine.isp_vac_s"]
    assert sorted(c.of for c in stage2) == ["silo_cold"] * 2 + ["silo_hot_full"] * 2


def test_aero_bound_pairs_the_baseline(
    resolved: dict[str, ResolvedExperiment], silo2d: dict[str, Any], gate_vehicle: dict
) -> None:
    """Amendment 6: the bound re-runs silo_cold and the pad at A_ref 21.24 m^2."""
    silo = resolved["silo_screening_2d"]
    (bound,) = silo.bounds
    assert bound.name == "aero_bound" and list(bound.runs) == ["silo_cold"]
    bounded, pair = bound.runs["silo_cold"], bound.baseline
    assert (bounded.name, pair.name) == ("silo_cold__aero_bound", "pad__aero_bound")
    for rr in (bounded, pair):
        assert rr.vehicle.aero.reference_area_m2.value == 21.24
    assert bounded.run == silo.variants["silo_cold"].run.model_copy(update={"name": bounded.name})
    assert pair.run == silo.baseline.run.model_copy(update={"name": pair.name})
    assert (
        silo.variants["silo_cold"].vehicle.aero.reference_area_m2.value
        == (gate_vehicle["aero"]["reference_area_m2"]["value"])
    )
    for of, message in ((["pad"], "list variants only"), (["nope"], "no such run")):
        bad = copy.deepcopy(silo2d)
        bad["bounds"][0]["of"] = of
        with pytest.raises(ValidationError, match=message):
            ExperimentConfig.model_validate(bad)


# --------------------------------------------------------------- block validators


def test_search_block_validators() -> None:
    SearchConfig()  # defaults are the plan's section 7 values and valid
    for bad, message in (
        ({"gamma_grid_deg": [8, 36, 3]}, "whole number of steps"),
        ({"gamma_grid_deg": [36, 8, 2]}, "start < stop"),
        ({"final_rtol": 1.0e-7}, "must not be looser"),
        ({"final_payload_xtol_kg": 1.0}, "must not exceed"),
        ({"figure_of_merit": "none"}, "needs fixed_gamma_star_deg"),
        ({"fixed_ltg_a": 1.0}, "only for search.figure_of_merit: none"),
        ({"brentq_rtol": BRENTQ_MIN_RTOL / 2}, "greater than or equal"),
        ({"delta_bracket_deg": [0.0, 45]}, "must start above 0"),
        ({"final_bracket_kg": [1000, 20]}, "low < high"),
        ({"ltg": {"pitch_bounds_deg": [75, -45]}}, "low < high"),
        ({"ltg": {"grid_max_rungs": 5}}, "less than or equal"),
        ({"ltg": {"mass_floor_factor": 1.0}}, "less than"),
    ):
        with pytest.raises(ValidationError, match=message):
            SearchConfig.model_validate(bad)
    with pytest.raises(ValidationError, match="ratio bounds"):
        ChecksConfig.model_validate({"grav_ratio_bounds": [3.0, 0.33]})


def test_search_units_and_budget_id() -> None:
    s = SearchConfig()
    assert s.gamma_grid_points_rad[0] == pytest.approx(math.radians(8.0), rel=1e-15)
    assert s.delta_bracket_rad == pytest.approx((math.radians(0.1), math.radians(45.0)))
    assert s.payload_half_bracket_kg == 2.0 * KM
    assert s.ltg.pitch_bounds_rad == pytest.approx((math.radians(-45.0), math.radians(75.0)))
    assert s.penalty.per_rad_kg == pytest.approx(1.0e4 * 180.0 / math.pi, rel=1e-15)
    same = SearchConfig.model_validate(s.model_dump())
    assert same.budget_id() == s.budget_id() and len(s.budget_id()) == 64
    assert SearchConfig(gamma_xatol_deg=0.02).budget_id() != s.budget_id()


def test_planar_site_serialises_without_warnings(resolved: dict[str, ResolvedExperiment]) -> None:
    run = resolved["silo_screening_2d"].baseline.run
    dumped = run.model_dump()
    assert dumped["site"] == {
        "latitude_deg": SITE_LAT_DEG,
        "azimuth_deg": 90.0,
        "include_rotation": True,
    }
    assert RunConfig.model_validate(dumped) == run


# ------------------------------------------- per-run levers, angle ranges, known gaps


@pytest.mark.parametrize(
    "integrator",
    [
        {"method": "RK45"},
        {"ramp_steps": 1},
        {"first_step_s": 1.0},
        {"t_max_s": 100.0},
        {"sample_dt_s": 0.5},
    ],
)
def test_planar_variants_integrate_like_the_baseline(
    silo2d: dict[str, Any], gate_vehicle: dict[str, Any], integrator: dict[str, Any]
) -> None:
    """Compared planar runs share every integrator setting, the sampling included (a
    peak read from the samples must not move with a per-run sample_dt)."""
    exp = _small(silo2d)
    exp["variants"] = {"silo_cold": {**exp["variants"]["silo_cold"], "integrator": integrator}}
    with pytest.raises(ValidationError, match="no integrator setting may differ"):
        resolve_experiment(exp, gate_vehicle)


@pytest.mark.parametrize(
    "path", ["integrator.method", "integrator.ramp_steps", "integrator.sample_dt_s"]
)
@pytest.mark.parametrize("where", ["sweep", "sensitivity", "bound"])
def test_planar_per_run_paths_may_not_move_the_integrator(
    silo2d: dict[str, Any], path: str, where: str
) -> None:
    exp = _small(silo2d)
    if where == "sweep":
        exp["sweeps"] = [{"of": "silo_cold", "axes": {path: ["RK45"]}}]
    elif where == "sensitivity":
        exp["sensitivity"] = {"of": ["silo_cold"], "params": {path: 0.1}}
    else:
        exp["bounds"] = [{"name": "b", "of": ["silo_cold"], "overrides": {path: "RK45"}}]
    with pytest.raises(ValidationError, match="no integrator setting may differ"):
        ExperimentConfig.model_validate(exp)


PLANAR_MAX_STEP_S = 2.0
"""The shipped planar flight-phase step cap [s] (user decision of 2026-09-30)."""


def test_every_shipped_planar_experiment_is_checked(repo_root: Path) -> None:
    """PLANAR_EXPERIMENTS lists every planar_2d experiment in experiments/, so the
    explicit-field checks (the planar cap and every shared threshold) cannot miss a new
    one: validation lets an omitted planar_max_step_s take its 2 s default, and only
    these tests require it to be written out."""
    planar = {
        path.stem
        for path in (repo_root / "experiments").glob("*.yaml")
        if _load(path).get("dynamics") == "planar_2d"
    }
    assert planar == set(PLANAR_EXPERIMENTS)


def test_shipped_planar_cap_is_explicit_and_shared(
    raw: dict[str, dict[str, Any]], resolved: dict[str, ResolvedExperiment]
) -> None:
    """Every shipped planar experiment states integrator.planar_max_step_s explicitly
    (2 s; no silent default), and every run it resolves (baseline, variants, sweep
    points, sensitivity cases, bounds and calibration cases) carries that one value, down
    to the IntegratorSettings the planner reads."""
    for name in PLANAR_EXPERIMENTS:
        assert raw[name]["baseline"]["integrator"]["planar_max_step_s"] == PLANAR_MAX_STEP_S
        r = resolved[name]
        runs = [*r.runs.values()]
        for sweep in r.sweeps:
            for point in sweep:
                runs.append(point.run)
                if point.paired_baseline is not None:
                    runs.append(point.paired_baseline)
        runs += [c.run for c in r.sensitivity]
        for bound in r.bounds:
            runs += [*bound.runs.values(), bound.baseline]
        runs += list(r.cases.values())
        assert len(runs) > 1, name
        caps = {run.run.integrator.planar_max_step_s for run in runs}
        assert caps == {PLANAR_MAX_STEP_S}, name
        settings = IntegratorSettings.from_config(r.baseline.run.integrator)
        assert settings.planar_max_step_s == PLANAR_MAX_STEP_S


@pytest.mark.parametrize("where", ["variant", "sweep", "sensitivity", "bound", "case"])
def test_planar_cap_may_not_differ_between_runs(
    raw: dict[str, dict[str, Any]], silo2d: dict[str, Any], where: str
) -> None:
    """A per-run planar_max_step_s (any value, the shipped one included) is refused with
    a message naming the setting: the cap is one integrator setting of the whole
    experiment. A calibration case cannot address the integrator at all."""
    path = "integrator.planar_max_step_s"
    exp = _small(silo2d)
    message = r"no integrator setting may differ.*planar_max_step_s"
    if where == "variant":
        exp["variants"] = {
            "silo_cold": {**exp["variants"]["silo_cold"], "integrator": {"planar_max_step_s": 1.0}}
        }
    elif where == "sweep":
        exp["sweeps"] = [{"of": "silo_cold", "axes": {path: [1.0, 2.0]}}]
    elif where == "sensitivity":
        exp["sensitivity"] = {"of": ["silo_cold"], "params": {path: 0.1}}
    elif where == "bound":
        exp["bounds"] = [{"name": "b", "of": ["silo_cold"], "overrides": {path: 1.0}}]
    else:
        exp = copy.deepcopy(raw["calibration_f9_2d"])
        exp["cases"] = {"c": {"overrides": {path: 1.0}}}
        message = "vehicle. paths only"
    with pytest.raises(ValidationError, match=message):
        ExperimentConfig.model_validate(exp)


@pytest.mark.parametrize("bad", [0.0, -2.0, math.inf, math.nan])
def test_planar_cap_is_finite_and_positive(bad: float) -> None:
    """integrator.planar_max_step_s must be finite and > 0 [s]; the default is the shipped
    2 s, and IntegratorSettings copies it from the config."""
    with pytest.raises(ValidationError, match="planar_max_step_s"):
        IntegratorConfig.model_validate({"planar_max_step_s": bad})
    assert IntegratorConfig().planar_max_step_s == PLANAR_MAX_STEP_S
    assert IntegratorSettings.from_config(IntegratorConfig()) == IntegratorSettings()


def test_one_d_variants_keep_their_integrator_freedom(
    repo_root: Path, f9_vehicle_dict: dict[str, Any]
) -> None:
    """The planar lock does not reach vertical_1d experiments (Phase 1 unchanged)."""
    exp = _load(repo_root / "experiments" / "silo_screening_1d.yaml")
    exp["variants"]["silo_cold"]["integrator"] = {"ramp_steps": 5}
    r = resolve_experiment(_small(exp), f9_vehicle_dict)
    assert r.variants["silo_cold"].run.integrator.ramp_steps == 5


def test_later_stages_ignite_after_their_coast(
    silo2d: dict[str, Any], gate_vehicle: dict[str, Any]
) -> None:
    exp = _small(silo2d)
    exp["variants"] = {"early": {"ignition": {"stage2": {"t_ign_s": -11.0}}}}
    with pytest.raises(ValueError, match="ignition stage2: a later stage ignites at t_ign_s >= 0"):
        resolve_experiment(exp, gate_vehicle)


def test_search_angles_stay_physical() -> None:
    for bad, message in (
        ({"gamma_grid_deg": [-10, 100, 10]}, r"inside \(-90, 90\) deg"),
        ({"gamma_grid_deg": [-90, 30, 10]}, r"inside \(-90, 90\) deg"),
        ({"delta_bracket_deg": [0.1, 120]}, "must end below 90 deg"),
        (
            {
                "figure_of_merit": "none",
                "fixed_gamma_star_deg": 95.0,
                "fixed_ltg_a": 1.0,
                "fixed_ltg_b_per_s": 0.004,
            },
            r"fixed_gamma_star_deg must lie inside \(-90, 90\)",
        ),
    ):
        with pytest.raises(ValidationError, match=message):
            SearchConfig.model_validate(bad)
    assert SearchConfig(gamma_grid_deg=(-80.0, 80.0, 10.0)).gamma_grid_points_deg[-1] == 80.0


@pytest.mark.parametrize(
    "bad",
    [
        {"pitch_bounds_deg": [-120, 75]},
        {"pitch_bounds_deg": [-45, 90]},
        {"steep_p0_deg": 95.0},
        {"pf_deg": -90.0},
        {"p0_offset_deg": 90.0},
    ],
)
def test_ltg_angles_stay_inside_the_tangent_range(bad: dict[str, Any]) -> None:
    """tan p = a - b tau is singular at +/-90 deg: every LTG angle stays inside."""
    with pytest.raises(ValidationError, match=r"must lie inside \(-90, 90\) deg"):
        LtgConfig.model_validate(bad)


def test_search_is_never_tighter_than_the_final_run() -> None:
    with pytest.raises(ValidationError, match="greater than or equal to 1"):
        SearchConfig(search_atol_scale=0.01)
    assert SearchConfig(search_atol_scale=1.0).search_atol_scale == 1.0


@pytest.mark.parametrize(
    ("lat_deg", "az_deg"),
    [(0.0, 90.0), (SITE_LAT_DEG, 45.0), (SITE_LAT_DEG, 270.0), (SITE_LAT_DEG, 0.0)],
)
def test_omega_p_follows_latitude_and_azimuth(lat_deg: float, az_deg: float) -> None:
    """omega_p = omega_E cos(lat) sin(az), signed: westward launches see negative rotation."""
    site = PlanarSiteConfig(latitude_deg=lat_deg, azimuth_deg=az_deg, include_rotation=True)
    lat, az = math.radians(lat_deg), math.radians(az_deg)
    expected = OMEGA_EARTH_RADS * math.cos(lat) * math.sin(az)
    assert site.omega_p_rads == pytest.approx(expected, rel=1e-14, abs=1e-20)
    if (lat_deg, az_deg) == (0.0, 90.0):
        assert site.omega_p_rads * R_EARTH_M == pytest.approx(EQUATOR_EAST_SITE_SPEED_MPS, abs=0.05)
    if az_deg == 270.0:
        assert site.omega_p_rads < 0.0


def test_checks_carry_the_section_11_run_thresholds() -> None:
    """The per-run acceptance numbers of plan section 11 are config fields too."""
    c = ChecksConfig()
    assert (c.identity_tol_mps, c.insertion_e_max) == (1.0e-5, 1.0e-6)
    with pytest.raises(ValidationError):
        ChecksConfig(insertion_e_max=1.0)


def test_m2_role_defaults_to_diagnostic_and_is_explicit(
    raw: dict[str, dict[str, Any]], resolved: dict[str, ResolvedExperiment]
) -> None:
    """checks.m2_role (user decision of 2026-09-30): diagnostic by default, blocking
    accepted, anything else refused; every shipped planar experiment writes it out as
    diagnostic, and every resolved run carries it in its planar checks."""
    assert ChecksConfig().m2_role == DIAGNOSTIC_ROLE == "diagnostic"
    assert ChecksConfig(m2_role="blocking").m2_role == BLOCKING_ROLE == "blocking"
    with pytest.raises(ValidationError, match="m2_role"):
        ChecksConfig.model_validate({"m2_role": "advisory"})
    for name in PLANAR_EXPERIMENTS:
        assert raw[name]["checks"]["m2_role"] == DIAGNOSTIC_ROLE, name
        roles = {run.run.planar.checks.m2_role for run in resolved[name].runs.values()}
        assert roles == {DIAGNOSTIC_ROLE}, name


def test_m2_role_may_not_differ_between_runs(
    silo2d: dict[str, Any], gate_vehicle: dict[str, Any]
) -> None:
    """The M2 role is part of the experiment-level checks block: a variant may not set
    its own."""
    exp = _small(silo2d)
    exp["variants"] = {
        "silo_cold": {**exp["variants"]["silo_cold"], "checks": {"m2_role": "blocking"}}
    }
    with pytest.raises(ValidationError, match="experiment-level shared block"):
        resolve_experiment(exp, gate_vehicle)


def test_convergence_block_defaults() -> None:
    c = ConvergenceConfig()
    assert (c.rel_tol, c.tighten_factor, c.max_step_factor) == (1.0e-3, 10.0, 0.5)
    assert c.gamma_resolution_rad == pytest.approx(math.radians(0.1), rel=1e-15)


def test_experiment_accepts_the_raw_form_only(raw: dict[str, dict[str, Any]]) -> None:
    """Documented: a dumped experiment holds the injected baseline, which the raw
    form refuses; results are re-resolved from the raw dict."""
    exp = ExperimentConfig.model_validate(_small(raw["silo_screening_2d"]))
    with pytest.raises(ValidationError, match="declare it once"):
        ExperimentConfig.model_validate(exp.model_dump())


def test_sim_dispatches_planar_runs_to_the_planar_model(
    resolved: dict[str, ResolvedExperiment],
) -> None:
    """Formerly a strict-xfail tripwire (build step 19); since build step 24 sim.run
    dispatches planar_2d runs to the planar model, whose time series has downrange_m
    (the 1-D one has z_m): the shipped silo_failed (end impact, search skipped) runs
    there, not through the 1-D model."""
    failed = resolved["silo_screening_2d"].variants["silo_failed"]
    out = sim.run_resolved(failed)
    columns = set(out.result.timeseries.columns)
    assert "downrange_m" in columns, "sim.run ran a planar_2d run through the 1-D model"
    assert out.result.model == "planar_2d" and "z_m" not in columns


# ------------------------------------- SP1 step 8: the pre-registered offload experiments

OFFLOAD_EXPERIMENT = "silo_offload_2d"
OFFLOAD_BRIDGE = "silo_offload_2d_readme"
HEADLINE_CASE = "silo_cold_s1"
"""The headline stage-1 case of both offload experiments (one name on both vehicles)."""
SCREENED_RUNS: dict[str, tuple[str, tuple[str, ...]]] = {
    OFFLOAD_EXPERIMENT: ("silo_screening_2d", ("pad", "silo_cold", "silo_hot_ramp_on_track")),
    OFFLOAD_BRIDGE: ("silo_bridge_2d_readme", ("pad", "silo_cold")),
}
"""The runs each offload experiment shares with the experiment it builds on."""
HEADLINE_SENSITIVITY_PARAMS = {
    "vehicle.stages.stage1.dry_mass_t": 0.10,
    "vehicle.stages.stage1.engine.isp_vac_s": 0.10,
    "vehicle.aero.cd_scale": 0.10,
    "assist.drive_efficiency": 0.10,
}
"""CLAUDE.md's headline sensitivity: +/-10% on stage-1 dry mass, Isp, C_D and drive
efficiency."""
GATE_LOX_T = {"stage1": 287.4, "stage2": 75.2}
"""Oxidiser (LOX) of each gate-fork stage's full load [t], copied from the source strings
of the vehicle file's propellant masses (Espace & Exploration No.39 via Wikipedia, Falcon
9 Full Thrust: "<LOX> LOX + <RP-1> RP-1"), which the energy test reads back; the energy
block gives the RP-1 and the vehicle the total."""
SPLIT_TEXT = "{lox} LOX + {fuel} RP-1"
"""How the gate fork's propellant sources (and the energy block's fuel sources, which quote
them) write a stage's LOX/RP-1 split [t]."""
RP1_NET_HEAT_BTU_PER_LB = 18_500.0
"""Minimum net heat of combustion of RP-1 [Btu/lb] (MIL-DTL-25576E, by ASTM D240)."""
KJ_PER_KG_PER_BTU_PER_LB = 2.326
"""One International Table Btu per pound in kJ/kg (exact)."""
KJ_PER_MJ = 1000.0
LHV_WRITTEN_DECIMALS = 2
"""The energy block writes the heating value to 0.01 MJ/kg."""
NO_IGNITION_MARGIN_M = 100.0
"""How far below the drag-free coast apex v_e^2 / (2 g_eff) [m] every ramp-start height
of the offload sweeps lies. The flown apex sits about 0.4 m below that bound on the gate
fork and moves by centimetres with payload and C_D (300.605-300.690 m; SP1 step 4,
deviation 4), so no swept height comes near the no_ignition band."""


@pytest.mark.parametrize("name", [OFFLOAD_EXPERIMENT, OFFLOAD_BRIDGE])
def test_offload_experiments_fly_the_screened_runs(
    resolved: dict[str, ResolvedExperiment], name: str
) -> None:
    """The offload is measured on the runs the earlier experiments screened: the pad and
    the silo variants silo_offload_2d (its bridge) shares with silo_screening_2d
    (silo_bridge_2d_readme) resolve to the very same run and vehicle dicts, key order
    included, so writing the variants out in full changed nothing a run flies."""
    source, names = SCREENED_RUNS[name]
    for run in names:
        new, old = resolved[name].runs[run], resolved[source].runs[run]
        assert json.dumps(new.run_dict) == json.dumps(old.run_dict), (name, run)
        assert json.dumps(new.vehicle_dict) == json.dumps(old.vehicle_dict), (name, run)


def _push_settings(run_dict: dict[str, Any]) -> dict[str, Any]:
    """A constant_accel run's assist block without the keys that state the push."""
    push = ("net_accel_g", "exit_speed_mps", "stroke_m")
    return {k: v for k, v in run_dict["assist"].items() if k not in push}


def test_silo_cold_200m_releases_at_the_exit_speed_of_silo_cold(
    resolved: dict[str, ResolvedExperiment],
) -> None:
    """silo_cold_200m states its push by silo_cold's exit speed v = sqrt(2 a g0 L), from
    silo_cold's own a [g0] and L, written unrounded: the configured speed is that very
    double, both built pushes release at it (silo_cold_200m over twice the stroke), and
    the net acceleration v^2 / (2 x 2L) is half of silo_cold's (1.5 g0). Every other
    assist and ignition setting is silo_cold's."""
    r = resolved[OFFLOAD_EXPERIMENT]
    cold, long = r.variants["silo_cold"], r.variants["silo_cold_200m"]
    a_cold, a_long = cold.run.assist, long.run.assist
    assert isinstance(a_cold, ConstantAccelConfig) and isinstance(a_long, ConstantAccelConfig)
    assert a_cold.net_accel_g is not None
    v_exit = math.sqrt(2.0 * a_cold.net_accel_g * G0_MPS2 * a_cold.stroke_m)
    assert a_long.exit_speed_mps == v_exit
    assert a_long.net_accel_g is None and a_long.stroke_m == 2.0 * a_cold.stroke_m
    half = a_cold.net_accel_g * G0_MPS2 / 2.0
    assert a_long.net_accel_mps2 == pytest.approx(half, rel=1e-15)
    for run in (cold, long):
        setup = sim.planar_setup(run.run, run.to_vehicle())
        assert isinstance(setup.assist, ConstantAccelAssist) and setup.track is not None
        released = setup.assist.exit_speed_mps(setup.track.length_m)
        assert released == pytest.approx(v_exit, rel=1e-15), run.name
    assert _push_settings(long.run_dict) == _push_settings(cold.run_dict)
    assert long.run_dict["ignition"] == cold.run_dict["ignition"]


def test_offload_sweeps_stay_inside_the_push_and_below_the_coast_apex(
    raw: dict[str, dict[str, Any]], resolved: dict[str, ResolvedExperiment]
) -> None:
    """Every sweep of silo_offload_2d names one stage-1 case of the block built on the
    sweep's own variant, rebuilt at each point on the point's run (``<run>__<case>``, the
    point's vehicle). Ramp-start depths lie within the stroke L and convert to t =
    sqrt(2 (L - d) / a) after push start (d = 0, a time at the release, snaps to it);
    heights lie NO_IGNITION_MARGIN_M or more below the drag-free apex v_e^2 / (2 g_eff),
    with v_e = sqrt(2 a L) and the track's g_eff = mu/R_E^2 - omega_p^2 R_E, omega_p =
    omega_E cos(lat) sin(az) of the site; a closed-form height converts to dt = 2 h /
    (v_e + sqrt(v_e^2 - 2 g_eff h)) after release, and the closed-form heights are event
    heights too (point-for-point comparison). The fixed-exit-speed sweep keeps
    silo_cold_200m's speed: a = a_cold L_cold / L."""
    r = resolved[OFFLOAD_EXPERIMENT]
    assert r.offload is not None
    site = raw[OFFLOAD_EXPERIMENT]["site"]
    lat, az = math.radians(site["latitude_deg"]), math.radians(site["azimuth_deg"])
    omega_p = OMEGA_EARTH_RADS * math.cos(lat) * math.sin(az)
    g_eff = MU_EARTH_M3S2 / R_EARTH_M**2 - omega_p**2 * R_EARTH_M
    cold = r.variants["silo_cold"].run.assist
    long = r.variants["silo_cold_200m"].run.assist
    assert isinstance(cold, ConstantAccelConfig) and isinstance(long, ConstantAccelConfig)
    assert cold.net_accel_g is not None
    a_cold = cold.net_accel_g * G0_MPS2
    depths: list[float] = []
    heights: dict[str, set[float]] = {"event": set(), "closed_form": set()}
    for sweep, points in zip(r.experiment.sweeps, r.sweeps, strict=True):
        assert len(sweep.offload) == 1
        case = r.offload.config.case(sweep.offload[0])
        assert (case.solve, case.of) == ("stage1", sweep.of)
        for point in points:
            assert [c.name for c in point.offload] == [case.name]
            start = point.offload[0].start
            assert start.name == f"{point.run.name}__{case.name}"
            assert json.dumps(start.vehicle_dict) == json.dumps(point.run.vehicle_dict)
            assist = point.run.run.assist
            assert isinstance(assist, ConstantAccelConfig)
            length = assist.stroke_m
            if assist.exit_speed_mps is not None:
                assert assist.exit_speed_mps == long.exit_speed_mps
                expected = a_cold * cold.stroke_m / length
                assert assist.net_accel_mps2 == pytest.approx(expected, rel=1e-15)
                continue
            assert assist.net_accel_g == cold.net_accel_g
            v_exit = math.sqrt(2.0 * a_cold * length)
            ign = point.run.run.ignition_for("stage1")
            spec = sim.run_ignition_specs(point.run.run, point.run.to_vehicle())["stage1"]
            if ign.at_depth_m is not None:
                depths.append(ign.at_depth_m)
                assert 0.0 <= ign.at_depth_m <= length
                if ign.at_depth_m == 0.0:
                    assert (spec.t_ign_s, spec.reference) == (0.0, "release")
                else:
                    t_push = math.sqrt(2.0 * (length - ign.at_depth_m) / a_cold)
                    assert spec.reference == "push_start"
                    assert spec.t_ign_s == pytest.approx(t_push, rel=1e-12, abs=1e-12)
            if ign.at_height_m is not None:
                h = ign.at_height_m
                assert ign.height_method is not None
                heights[ign.height_method].add(h)
                assert h <= v_exit**2 / (2.0 * g_eff) - NO_IGNITION_MARGIN_M, h
                if ign.height_method == "closed_form":
                    dt = 2.0 * h / (v_exit + math.sqrt(v_exit**2 - 2.0 * g_eff * h))
                    assert spec.reference == "release"
                    assert spec.t_ign_s == pytest.approx(dt, rel=1e-12)
    assert depths and heights["event"] and heights["closed_form"]
    assert heights["closed_form"] <= heights["event"]


def test_offload_energy_inputs_close_on_the_gate_vehicle_and_its_sources(
    resolved: dict[str, ResolvedExperiment],
) -> None:
    """The energy block of silo_offload_2d: each stage's RP-1 and the LOX of GATE_LOX_T
    are the split the vehicle file's own propellant source states ("287.4 LOX + 123.5
    RP-1", "75.2 LOX + 32.3 RP-1"), which the fuel's source quotes too, and they sum to
    the vehicle's propellant load (410.9 and 107.5 t); the heating value is
    MIL-DTL-25576E's 18,500 Btu/lb times 2.326 kJ/kg per Btu/lb (43.031 MJ/kg) written to
    0.01 MJ/kg and not above it (a specification minimum; the rounding does not favour
    the assist), sourced. The bridge declares no energy block (its fork has no sourced
    fuel split)."""
    r = resolved[OFFLOAD_EXPERIMENT]
    assert r.offload is not None and r.offload.config.energy is not None
    energy = r.offload.config.energy
    for stage in r.baseline.vehicle.stages:
        fuel = energy.fuel_mass_t[stage.name]
        assert fuel.source and not fuel.assumed
        split = SPLIT_TEXT.format(lox=GATE_LOX_T[stage.name], fuel=fuel.value)
        load_source = stage.propellant_mass_t.source
        assert load_source is not None and split in load_source, (stage.name, split)
        assert split in fuel.source, (stage.name, split)
        total = fuel.value + GATE_LOX_T[stage.name]
        assert total == pytest.approx(stage.propellant_mass_t.value, rel=1e-12), stage.name
    lhv = energy.heating_value_MJ_per_kg
    expected_mj = RP1_NET_HEAT_BTU_PER_LB * KJ_PER_KG_PER_BTU_PER_LB / KJ_PER_MJ
    assert lhv.source and not lhv.assumed
    assert lhv.value == round(expected_mj, LHV_WRITTEN_DECIMALS) and lhv.value <= expected_mj
    bridge = resolved[OFFLOAD_BRIDGE].offload
    assert bridge is not None and bridge.config.energy is None


def test_offload_block_cases_arms_and_derived_names(
    raw: dict[str, dict[str, Any]], resolved: dict[str, ResolvedExperiment]
) -> None:
    """The block of silo_offload_2d: pad controls of the three solve modes (D-SP1-10);
    the headline first and the only case with a paired pad; each penalty row adds its
    assumed dry mass to stage 1 of the assisted run only (restated ``assumed: true``,
    the vehicle's dry mass plus the row); each fixed case imposes its fraction of the
    stage-1 load; the headline alone carries sensitivity arms, two per parameter of the
    headline sensitivity, while the experiment's own sensitivity block lists no run; and
    every name the block derives (case runs, paired pads, pad controls, arms with their
    variants and pads, sweep-point cases) is a valid results name within MAX_NAME_LEN."""
    r = resolved[OFFLOAD_EXPERIMENT]
    block = r.offload
    assert block is not None
    cfg = block.config
    assert block.pad_control_modes == ("stage1", "stage2", "both")
    assert (cfg.cases[0].name, cfg.cases[0].solve) == (HEADLINE_CASE, "stage1")
    assert [c.name for c in cfg.cases if c.paired_pad] == [HEADLINE_CASE]
    base_vehicle = r.baseline.vehicle
    dry_t = base_vehicle.stages[0].dry_mass_t.value
    load_kg = r.baseline.to_vehicle().stages[0].propellant_mass_kg
    for case in block.cases:
        added = case.config.stage1_dry_mass_added_t
        dry = case.start.vehicle_dict["stages"][0]["dry_mass_t"]
        if added is None:
            assert dry == r.baseline.vehicle_dict["stages"][0]["dry_mass_t"], case.name
        else:
            assert dry["assumed"] is True and case.config.solve == "stage1"
            assert dry["value"] == pytest.approx(dry_t + added, rel=1e-15), case.name
            assert case.pad_start is None
        fixed = case.config.fixed
        if fixed is not None:
            assert fixed.stage1_fraction is not None and case.imposed_kg is not None
            assert case.imposed_kg == pytest.approx(fixed.stage1_fraction * load_kg, rel=1e-15)
    assert {c.config.stage1_dry_mass_added_t for c in block.cases} > {None}
    assert any(c.config.fixed is not None for c in block.cases)
    assert cfg.sensitivity_of == [HEADLINE_CASE]
    sensitivity = r.experiment.sensitivity
    assert sensitivity is not None and sensitivity.params == HEADLINE_SENSITIVITY_PARAMS
    assert raw[OFFLOAD_EXPERIMENT]["sensitivity"]["of"] == [] and r.sensitivity == []
    expected_arms = {(p, s * f) for p, f in HEADLINE_SENSITIVITY_PARAMS.items() for s in (1, -1)}
    assert {(a.param, a.fraction) for a in block.arms} == expected_arms
    assert len(block.arms) == len(expected_arms) and {a.case for a in block.arms} == {HEADLINE_CASE}
    names = offload_run_names(cfg, r.baseline.name)
    names += [n for a in block.arms for n in (a.start.name, a.pad.name)]
    names += [a.variant.name for a in block.arms if a.variant is not None]
    names += [c.start.name for points in r.sweeps for p in points for c in p.offload]
    for name in names:
        check_name(name, "derived offload run name")


def test_offload_bridge_is_the_headline_case_on_the_readme_loads_fork(
    raw: dict[str, dict[str, Any]], resolved: dict[str, ResolvedExperiment]
) -> None:
    """The README-loads bridge (D-SP1-13) solves exactly the headline case of
    silo_offload_2d (same name, variant, mode and paired pad) with its stage-1 pad
    control, on silo_bridge_2d_readme's vehicle fork, and nothing else: no sweep, no
    sensitivity, no arm. The main experiment flies silo_screening_2d's vehicle file."""
    main, bridge = resolved[OFFLOAD_EXPERIMENT].offload, resolved[OFFLOAD_BRIDGE].offload
    assert main is not None and bridge is not None
    headline = main.config.case(HEADLINE_CASE)
    assert [c.model_dump() for c in bridge.config.cases] == [headline.model_dump()]
    assert bridge.pad_control_modes == ("stage1",) and not bridge.arms
    assert not resolved[OFFLOAD_BRIDGE].sweeps and not resolved[OFFLOAD_BRIDGE].sensitivity
    assert raw[OFFLOAD_BRIDGE]["vehicle"] == raw["silo_bridge_2d_readme"]["vehicle"]
    assert raw[OFFLOAD_EXPERIMENT]["vehicle"] == raw["silo_screening_2d"]["vehicle"]


def test_offload_reports_name_the_arms_and_the_bridge_calibration(
    resolved: dict[str, ResolvedExperiment],
) -> None:
    """SP1 step 8a, on the pre-registered files (nothing run): silo_offload_2d's
    sensitivity block lists no run and serves the offload arms, so its payload
    Sensitivity note points to the section "Propellant saved at fixed payload" instead of
    saying no block is declared; the bridge's vehicle fork has a calibration record,
    100 (P*/reference - 1) inside +/-10 %, so its offload caveat states it instead of "no
    calibration record"; the bridge declares no sensitivity block and keeps that note."""
    main = resolved[OFFLOAD_EXPERIMENT]
    assert main.experiment.sensitivity is not None and main.experiment.sensitivity.of == []
    assert main.offload is not None and main.offload.arms
    note = results_io.planar_sensitivity_note(
        main, sensitivity=True, offload=True, variants=main.variants
    )
    assert "no sensitivity block declared" not in note
    assert '"Propellant saved at fixed payload"' in note
    bridge = resolved[OFFLOAD_BRIDGE]
    name = bridge.baseline.vehicle.name
    model_kg, reference_kg, _note = plots.CALIBRATION_RECORDS[name]
    assert abs(100.0 * (model_kg / reference_kg - 1.0)) <= 10.0
    caveat = summary.offload_caveats(name, plots.CALIBRATION_RECORDS.get(name))[0]
    assert "no calibration record" not in caveat and f"{model_kg:,.0f} kg" in caveat
    bridge_note = results_io.planar_sensitivity_note(
        bridge, sensitivity=True, offload=True, variants=bridge.variants
    )
    assert bridge_note.startswith("(no sensitivity block declared; ")
