"""Planar experiment schema (build step 19): the model selector, the experiment-level
shared blocks (dynamics, site, guidance, search, target_orbit, checks) injected into
every run and refused per run, end: insertion, integrator.method, the search, LTG and
checks blocks, paired sweeps (guidance_study only), calibration cases, bounds, the
automatic search skip (amendment 4), sensitivity paths (amendment 5), the aero bound
(amendment 6) and baseline identity across experiments (amendment 15). The shipped
Phase 2 experiments must resolve, and the Phase 1 run dicts must stay byte-identical
to the 1-D golden. Expected numbers are computed here from the YAML inputs."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from launchsim import cli, sim
from launchsim.config import (
    BRENTQ_MIN_RTOL,
    PLANAR_SHARED_KEYS,
    SHARED_KEYS,
    ChecksConfig,
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
    resolve_experiment,
    resolve_run,
    shared_run_blocks,
)
from launchsim.constants import OMEGA_EARTH_RADS, R_EARTH_M
from launchsim.phases import IntegratorSettings

PLANAR_EXPERIMENTS = (
    "calibration_f9_2d",
    "silo_screening_2d",
    "silo_bridge_2d_readme",
    "guidance_trigger_2d",
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
    """Raw dicts of the four shipped planar experiments."""
    return {n: _load(_experiment_path(repo_root, n)) for n in PLANAR_EXPERIMENTS}


@pytest.fixture(scope="module")
def resolved(repo_root: Path) -> dict[str, ResolvedExperiment]:
    """The four shipped planar experiments, resolved."""
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
