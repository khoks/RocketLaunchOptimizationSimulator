"""Config rules: vehicle files are all-Quantity with exactly one provenance, unknown keys
fail, Phase 1 limits raise with the phase named, the F9 file converts to SI correctly,
the shipped experiment resolves every variant, sweep point and sensitivity case, and
the merge and override rules (per-key merge, discriminator switches, and the exclusive
key families of SP1 step 1: an override that states a setting another way displaces the
base's parameterisation; two given together raise)."""

from __future__ import annotations

import copy
import itertools
import math
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel, ValidationError

from launchsim import config
from launchsim.config import (
    PLANNED_MODELS,
    ConfigPathError,
    ConstantAccelConfig,
    ExclusiveKeysError,
    ExperimentConfig,
    IgnitionConfig,
    Quantity,
    RunConfig,
    SiteConfig,
    StartupConfig,
    StartupOverride,
    TrackConfig,
    VehicleConfig,
    apply_overrides,
    merge_run_dicts,
    read_value,
    resolve_experiment,
    resolve_run,
)
from launchsim.constants import G0_MPS2, P_SEA_LEVEL_PA
from launchsim.vehicle import Startup

DATA = Path(__file__).resolve().parent / "data"


def _load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def experiment_dict(repo_root: Path) -> dict[str, Any]:
    return _load(repo_root / "experiments" / "silo_screening_1d.yaml")


@pytest.fixture(scope="module")
def toy_dict() -> dict[str, Any]:
    return _load(DATA / "toy_vehicle.yaml")


@pytest.fixture(scope="module")
def tiny_dict() -> dict[str, Any]:
    return _load(DATA / "tiny_experiment.yaml")


def _numeric_leaves(node: Any, path: str = "") -> list[str]:
    """Paths of every bare number outside a Quantity dict."""
    if isinstance(node, dict):
        if "value" in node:
            return []
        out: list[str] = []
        for k, v in node.items():
            out += _numeric_leaves(v, f"{path}.{k}" if path else str(k))
        return out
    if isinstance(node, list):
        return [p for i, v in enumerate(node) for p in _numeric_leaves(v, f"{path}.{i}")]
    if isinstance(node, int | float) and not isinstance(node, bool):
        return [path]
    return []


# ------------------------------------------------------------------- vehicle file rules


@pytest.mark.parametrize(
    "name", ["configs/vehicles/generic_f9_class.yaml", "tests/data/toy_vehicle.yaml"]
)
def test_vehicle_files_have_no_bare_numbers(repo_root: Path, name: str) -> None:
    raw = _load(repo_root / name)
    assert _numeric_leaves(raw) == []
    VehicleConfig.model_validate(raw)


def test_bare_number_in_vehicle_file_raises(f9_vehicle_dict: dict[str, Any]) -> None:
    bad = copy.deepcopy(f9_vehicle_dict)
    bad["stages"][0]["dry_mass_t"] = 25.6
    with pytest.raises(ValidationError, match="bare value"):
        VehicleConfig.model_validate(bad)


def test_quantity_needs_exactly_one_provenance() -> None:
    assert Quantity.model_validate({"value": 1.0, "source": "x"}).value == 1.0
    assert Quantity.model_validate({"value": 1, "assumed": True, "note": "n"}).assumed
    with pytest.raises(ValidationError, match="exactly one"):
        Quantity.model_validate({"value": 1.0, "source": "x", "assumed": True})
    with pytest.raises(ValidationError, match="exactly one"):
        Quantity.model_validate({"value": 1.0})
    with pytest.raises(ValidationError):
        Quantity.model_validate({"value": True, "source": "x"})
    with pytest.raises(ValidationError):
        Quantity.model_validate({"value": "1.0", "source": "x"})


def test_quantity_rejects_empty_source_and_non_finite_values() -> None:
    with pytest.raises(ValidationError, match="source"):
        Quantity.model_validate({"value": 1.0, "source": ""})
    with pytest.raises(ValidationError, match="blank"):
        Quantity.model_validate({"value": 1.0, "source": " \t"})
    for bad in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValidationError):
            Quantity.model_validate({"value": bad, "source": "x"})
        with pytest.raises(ValidationError):
            Quantity.model_validate({"value": bad, "assumed": True})


def test_unknown_key_raises(f9_vehicle_dict: dict[str, Any]) -> None:
    bad = copy.deepcopy(f9_vehicle_dict)
    bad["stages"][1]["engine"]["thrust_vac_kn"] = bad["stages"][1]["engine"].pop("thrust_vac_kN")
    with pytest.raises(ValidationError, match="thrust_vac_kn"):
        VehicleConfig.model_validate(bad)
    with pytest.raises(ValidationError, match="extra"):
        RunConfig.model_validate({"name": "x", "sight": {}})


def test_f9_converts_to_si(f9_vehicle_dict: dict[str, Any]) -> None:
    cfg = VehicleConfig.model_validate(f9_vehicle_dict)
    vehicle = cfg.to_vehicle()
    assert math.isclose(vehicle.liftoff_mass_kg(), 542_570.0, rel_tol=1e-12)
    s1 = vehicle.stages[0]
    assert s1.n_engines == 9
    assert math.isclose(s1.thrust_vac_total_N, 9 * 914.1e3, rel_tol=1e-12)
    assert math.isclose(s1.engine.c_mps, 311.0 * G0_MPS2, rel_tol=1e-12)
    assert math.isclose(
        s1.engine.exit_area_m2, (914.1 - 845.2) * 1e3 / P_SEA_LEVEL_PA, rel_tol=1e-12
    )
    assert math.isclose(s1.engine.exit_area_m2, 0.6800, rel_tol=1e-3)
    assert s1.startup.kind == "ramp" and s1.startup.t_ramp_s == 2.0
    s2 = vehicle.stages[1]
    assert s2.engine.exit_area_m2 == 0.0  # no sea-level thrust given
    assert s2.startup.kind == "step" and s2.coast_before_ignition_s == 3.0
    assert vehicle.fairing_mass_kg == 1900.0 and vehicle.payload_mass_kg == 22_800.0
    assert vehicle.screening_isp_s == (295.0, 348.0)


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        ("stages.stage1.dry_mass_t", -1.0, "dry mass"),
        ("stages.stage1.propellant_mass_t", 0.0, "propellant > 0"),
        ("stages.stage1.engine.isp_vac_s", -311.0, "Isp > 0"),
        ("stages.stage2.coast_before_ignition_s", -3.0, "coast >= 0"),
        ("stages.stage1.startup.t_ramp_s", -2.0, "durations must be >= 0"),
        ("payload_mass_t", -5.0, "payload masses must be >= 0"),
        ("screening.stage_isp_eff_s.0", 0.0, "screening_isp_s entries must be > 0"),
    ],
)
def test_vehicle_physical_limits_fail_at_load(
    experiment_dict: dict[str, Any],
    f9_vehicle_dict: dict[str, Any],
    path: str,
    value: float,
    message: str,
) -> None:
    """Invalid vehicle numbers are rejected when the file is validated, with the vehicle
    named, not later when the sim builds the Vehicle."""
    _, bad_vehicle = apply_overrides({"name": "x"}, {f"vehicle.{path}": value}, f9_vehicle_dict)
    with pytest.raises(ValidationError, match=f"vehicle 'generic_f9_class': .*{message}"):
        VehicleConfig.model_validate(bad_vehicle)
    with pytest.raises(ValueError, match="vehicle 'generic_f9_class'"):
        resolve_run("x", {"name": "x"}, bad_vehicle)
    with pytest.raises(ValueError, match="vehicle 'generic_f9_class'"):
        resolve_experiment(experiment_dict, bad_vehicle)
    # a vehicle. sweep axis hitting the same limit fails at load too
    bad_exp = copy.deepcopy(experiment_dict)
    bad_exp["sweeps"][0]["axes"] = {f"vehicle.{path}": [value]}
    with pytest.raises(ValueError, match="vehicle 'generic_f9_class'"):
        resolve_experiment(bad_exp, f9_vehicle_dict)


def test_vehicle_startup_rejects_foreign_durations() -> None:
    q = {"value": 2.0, "assumed": True}
    assert StartupConfig.model_validate({"kind": "ramp", "t_ramp_s": q}).to_startup() == Startup(
        "ramp", t_ramp_s=2.0
    )
    with pytest.raises(ValidationError, match="gives t_ramp_s but the kind is 'step'"):
        StartupConfig.model_validate({"kind": "step", "t_ramp_s": q})
    with pytest.raises(ValidationError, match="gives t_ramp_s but the kind is 'lag'"):
        StartupConfig.model_validate({"kind": "lag", "tau_s": q, "t_ramp_s": q})
    with pytest.raises(ValidationError, match="gives tau_s but the kind is 'ramp'"):
        StartupConfig.model_validate({"kind": "ramp", "t_ramp_s": q, "tau_s": q})
    with pytest.raises(ValidationError, match="needs tau_s"):
        StartupConfig.model_validate({"kind": "lag"})


def test_config_models_are_frozen(f9_vehicle_dict: dict[str, Any]) -> None:
    run = RunConfig.model_validate({"name": "pad"})
    with pytest.raises(ValidationError):
        run.end = "impact"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        run.site.latitude_deg = 0.0  # type: ignore[misc]
    vehicle = VehicleConfig.model_validate(f9_vehicle_dict)
    with pytest.raises(ValidationError):
        vehicle.stages[0].dry_mass_t.value = 1.0  # type: ignore[misc]
    with pytest.raises(ValidationError):
        RunConfig.model_validate({"name": "x", "assist": {"model": "linear_motor"}})
    assert PLANNED_MODELS == ("linear_motor", "cable_winch")


def test_engine_exit_area_rules(f9_vehicle_dict: dict[str, Any]) -> None:
    eng = copy.deepcopy(f9_vehicle_dict["stages"][0]["engine"])
    eng["exit_area_m2"] = {"value": 0.7, "assumed": True}
    bad = copy.deepcopy(f9_vehicle_dict)
    bad["stages"][0]["engine"] = eng
    with pytest.raises(ValidationError, match="not both"):
        VehicleConfig.model_validate(bad)
    del eng["thrust_sl_kN"]
    bad["stages"][0]["engine"] = eng
    assert VehicleConfig.model_validate(bad).to_vehicle().stages[0].engine.exit_area_m2 == 0.7
    bad["stages"][0]["engine"]["count"] = {"value": 2.5, "assumed": True}
    with pytest.raises(ValidationError, match="positive integer"):
        VehicleConfig.model_validate(bad)


# ---------------------------------------------------------------- Phase 1 limit rules


def test_rotation_is_phase_2() -> None:
    assert SiteConfig().omega_p_rads == 0.0
    with pytest.raises(ValidationError, match="Phase 2"):
        SiteConfig(include_rotation=True)


def test_site_angle_ranges() -> None:
    assert math.isclose(SiteConfig(latitude_deg=-90, azimuth_deg=360).latitude_rad, -math.pi / 2)
    for bad in (
        {"latitude_deg": 100},
        {"latitude_deg": -91},
        {"azimuth_deg": -1},
        {"azimuth_deg": 361},
    ):
        with pytest.raises(ValidationError):
            SiteConfig.model_validate(bad)


def test_push_start_needs_an_assist_and_the_first_stage(
    experiment_dict: dict[str, Any], f9_vehicle_dict: dict[str, Any]
) -> None:
    push = {"t_ign_s": -2.0, "reference": "push_start"}
    with pytest.raises(ValidationError, match="push_start needs an assist model"):
        RunConfig.model_validate({"name": "pad", "ignition": {"stage1": push}})
    silo = {"model": "constant_accel", "net_accel_g": 3, "stroke_m": 100, "brake_decel_g": 5}
    ok = RunConfig.model_validate({"name": "s", "assist": silo, "ignition": {"stage1": push}})
    assert ok.ignition["stage1"].reference == "push_start"
    with pytest.raises(ValueError, match=r"run 's', ignition stage2: .*first stage"):
        resolve_run("s", {"assist": silo, "ignition": {"stage2": push}}, f9_vehicle_dict)
    bad = copy.deepcopy(experiment_dict)
    bad["variants"]["silo_hot_full"]["assist"] = {"model": "none"}
    with pytest.raises(ValueError, match="push_start needs an assist model"):
        resolve_experiment(bad, f9_vehicle_dict)
    assert IgnitionConfig().reference == "release"


def test_tilted_track_is_phase_2() -> None:
    assert TrackConfig(angle_deg=90).phi_rad == math.pi / 2
    with pytest.raises(ValidationError, match="Phase 2"):
        TrackConfig(angle_deg=45)


@pytest.mark.parametrize("model", ["linear_motor", "cable_winch"])
def test_other_drives_are_phase_3(model: str) -> None:
    with pytest.raises(ValidationError, match="Phase 3"):
        RunConfig.model_validate({"name": "x", "assist": {"model": model}})
    # a realistic Phase 3 block with its own keys gets the phase message, not "extra"
    with pytest.raises(ValidationError, match="Phase 3"):
        RunConfig.model_validate({"name": "x", "assist": {"model": model, "F_max_kN": 1}})


def test_unknown_drive_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RunConfig.model_validate({"name": "x", "assist": {"model": "catapult"}})


def test_failed_ignition_requires_impact() -> None:
    run = {"name": "x", "ignition": {"stage1": {"fails": True}}}
    with pytest.raises(ValidationError, match="end: impact"):
        RunConfig.model_validate(run)
    ok = RunConfig.model_validate({**run, "end": "impact"})
    assert ok.ignition["stage1"].fails and ok.end == "impact"


def test_constant_accel_units() -> None:
    cfg = ConstantAccelConfig.model_validate(
        {
            "model": "constant_accel",
            "net_accel_g": 3,
            "stroke_m": 100,
            "brake_decel_g": 5,
            "carriage_mass_t": 22,
        }
    )
    assert math.isclose(cfg.net_accel_mps2, 3 * G0_MPS2, rel_tol=1e-12)
    assert math.isclose(cfg.net_accel_mps2, 29.41995, rel_tol=1e-7)
    assert cfg.carriage_mass_kg == 22_000.0
    assert math.isclose(cfg.brake_decel_mps2, 5 * G0_MPS2, rel_tol=1e-12)
    assert cfg.track.angle_deg == 90.0 and cfg.shaft == "vented"
    with pytest.raises(ValidationError):
        ConstantAccelConfig.model_validate(
            {
                "model": "constant_accel",
                "net_accel_g": 3,
                "stroke_m": 100,
                "brake_decel_g": 5,
                "exhaust_impingement_fraction": 1.5,
            }
        )


def test_run_defaults() -> None:
    run = RunConfig.model_validate({"name": "pad"})
    assert run.assist.model == "none"
    assert run.end == "stage1_burnout"
    assert run.integrator.rtol == 1e-10 and run.integrator.sample_dt_s == 0.05
    ign = run.ignition_for("stage1")
    assert ign.t_ign_s == 0.0 and ign.reference == "release" and not ign.fails


# --------------------------------------------------------------- overrides and merging


def test_merge_run_dicts_by_key_scalars_and_lists_replace() -> None:
    base = {"a": {"x": 1, "y": [1, 2]}, "b": 2, "assist": {"model": "constant_accel", "k": 1}}
    out = merge_run_dicts(base, {"a": {"y": [3]}, "b": 5, "assist": {"model": "none"}})
    assert out == {"a": {"x": 1, "y": [3]}, "b": 5, "assist": {"model": "none"}}
    assert base["a"]["y"] == [1, 2]  # inputs untouched
    # a base dict without `model` is switched too; the same model merges by key
    assert merge_run_dicts({"assist": {"k": 1}}, {"assist": {"model": "none"}}) == {
        "assist": {"model": "none"}
    }
    same = merge_run_dicts(base, {"assist": {"model": "constant_accel", "k": 2}})
    assert same["assist"] == {"model": "constant_accel", "k": 2}


def test_merge_and_override_switch_startup_kind_wholesale(f9_vehicle_dict: dict[str, Any]) -> None:
    lag = {"ignition": {"stage1": {"t_ign_s": -2.0, "startup": {"kind": "lag", "tau_s": 1.0}}}}
    stepped = merge_run_dicts(lag, {"ignition": {"stage1": {"startup": {"kind": "step"}}}})
    assert stepped["ignition"]["stage1"] == {"t_ign_s": -2.0, "startup": {"kind": "step"}}
    resolved = resolve_run("x", stepped, f9_vehicle_dict)
    base = resolved.to_vehicle().stages[0].startup
    assert resolved.run.ignition["stage1"].resolved_startup(base) == Startup("step")
    retimed = merge_run_dicts(lag, {"ignition": {"stage1": {"startup": {"tau_s": 2.0}}}})
    assert retimed["ignition"]["stage1"]["startup"] == {"kind": "lag", "tau_s": 2.0}
    same = merge_run_dicts(
        lag, {"ignition": {"stage1": {"startup": {"kind": "lag", "tau_s": 3.0}}}}
    )
    assert same["ignition"]["stage1"]["startup"] == {"kind": "lag", "tau_s": 3.0}
    # the dotted-path form does the same
    dotted, _ = apply_overrides(lag, {"ignition.stage1.startup.kind": "step"}, f9_vehicle_dict)
    assert dotted["ignition"]["stage1"]["startup"] == {"kind": "step"}
    kept, _ = apply_overrides(lag, {"ignition.stage1.startup.kind": "lag"}, f9_vehicle_dict)
    assert kept["ignition"]["stage1"]["startup"] == {"kind": "lag", "tau_s": 1.0}


def test_startup_override_kind_switch_needs_its_duration(f9_vehicle_dict: dict[str, Any]) -> None:
    f9 = VehicleConfig.model_validate(f9_vehicle_dict).to_vehicle()
    ramp2 = f9.stages[0].startup  # ramp, 2 s
    assert ramp2.kind == "ramp" and ramp2.t_ramp_s == 2.0 and ramp2.tau_s == 0.0
    with pytest.raises(ValueError, match="needs tau_s"):
        StartupOverride(kind="lag").resolve(ramp2)
    with pytest.raises(ValueError, match="needs t_ramp_s"):
        StartupOverride(kind="ramp").resolve(Startup("step"))
    with pytest.raises(ValueError, match="gives tau_s"):
        StartupOverride(tau_s=1.0).resolve(ramp2)
    with pytest.raises(ValueError, match="gives t_ramp_s"):
        StartupOverride(kind="lag", tau_s=1.0, t_ramp_s=1.0).resolve(ramp2)
    # the resolved Startup carries only the duration of its own kind
    assert StartupOverride(kind="lag", tau_s=1.0).resolve(ramp2) == Startup("lag", tau_s=1.0)
    assert StartupOverride(kind="step").resolve(ramp2) == Startup("step")
    assert StartupOverride(t_ramp_s=1.0).resolve(ramp2) == Startup("ramp", t_ramp_s=1.0)
    assert StartupOverride().resolve(ramp2) == ramp2
    # a kind restated with an inherited non-zero duration is fine
    lag = Startup("lag", tau_s=1.5)
    assert StartupOverride(kind="lag").resolve(lag) == lag
    # restating the vehicle's own kind changes nothing, even a zero-duration (step-like) ramp
    ramp0 = Startup("ramp", t_ramp_s=0.0)
    assert StartupOverride(kind="ramp").resolve(ramp0) == ramp0
    with pytest.raises(ValueError, match="needs t_ramp_s"):
        StartupOverride(kind="ramp").resolve(Startup("lag", tau_s=1.0))


def test_startup_override_errors_surface_at_load(
    experiment_dict: dict[str, Any], f9_vehicle_dict: dict[str, Any]
) -> None:
    bad = copy.deepcopy(experiment_dict)
    bad["variants"]["silo_cold"]["ignition"]["stage1"]["startup"] = {"kind": "lag"}
    with pytest.raises(ValueError, match=r"run 'silo_cold', ignition stage1: .*needs tau_s"):
        resolve_experiment(bad, f9_vehicle_dict)
    bad = copy.deepcopy(experiment_dict)
    bad["sweeps"][0]["axes"]["ignition.stage1.startup.kind"] = ["ramp", "lag"]
    with pytest.raises(ValueError, match="needs tau_s"):
        resolve_experiment(bad, f9_vehicle_dict)
    bad = copy.deepcopy(experiment_dict)
    bad["sweeps"][1]["of"] = "silo_cold_lag"  # t_ramp_s sweep on a lag start
    with pytest.raises(ValueError, match="gives t_ramp_s"):
        resolve_experiment(bad, f9_vehicle_dict)


def test_apply_overrides_paths(f9_vehicle_dict: dict[str, Any]) -> None:
    run = {"name": "r", "assist": {"model": "constant_accel", "stroke_m": 100}, "ignition": {}}
    new_run, new_vehicle = apply_overrides(
        run,
        {
            "assist.stroke_m": 300,
            "ignition.stage1.startup.t_ramp_s": 1.0,
            "vehicle.stages.stage1.dry_mass_t": 28.16,
            "vehicle.screening.stage_isp_eff_s.0": 324.5,
        },
        f9_vehicle_dict,
    )
    assert new_run["assist"]["stroke_m"] == 300
    assert new_run["ignition"] == {"stage1": {"startup": {"t_ramp_s": 1.0}}}
    assert run["assist"]["stroke_m"] == 100 and run["ignition"] == {}
    q = new_vehicle["stages"][0]["dry_mass_t"]
    assert q == {"value": 28.16, "assumed": True, "note": "override"}
    assert new_vehicle["screening"]["stage_isp_eff_s"][0]["value"] == 324.5
    assert f9_vehicle_dict["stages"][0]["dry_mass_t"]["value"] == 25.6
    assert read_value(new_vehicle, "stages.stage1.dry_mass_t") == 28.16
    assert read_value(new_vehicle, "stages.1.engine.isp_vac_s") == 348
    with pytest.raises(ConfigPathError, match="stage9"):
        apply_overrides(run, {"vehicle.stages.stage9.dry_mass_t": 1.0}, f9_vehicle_dict)
    with pytest.raises(ConfigPathError, match="out of range"):
        apply_overrides(run, {"vehicle.stages.7.dry_mass_t": 1.0}, f9_vehicle_dict)
    with pytest.raises(ConfigPathError, match="malformed"):
        apply_overrides(run, {"assist..stroke_m": 1.0}, f9_vehicle_dict)
    assert issubclass(ConfigPathError, ValueError)


def test_vehicle_overrides_wrap_only_quantity_targets(f9_vehicle_dict: dict[str, Any]) -> None:
    _, v = apply_overrides(
        {"name": "r"},
        {
            "vehicle.name": 5,
            "vehicle.stages.stage1.startup.kind": "step",
            "vehicle.stages.stage2.engine.exit_area_m2": 0.7,
        },
        f9_vehicle_dict,
    )
    assert v["name"] == 5  # a non-Quantity target takes the raw value ...
    assert v["stages"][0]["startup"]["kind"] == "step"
    assert v["stages"][1]["engine"]["exit_area_m2"] == {  # ... a new numeric key is a Quantity
        "value": 0.7,
        "assumed": True,
        "note": "override",
    }
    with pytest.raises(ValidationError, match="name"):  # and validation names the type clash
        VehicleConfig.model_validate(v)


def test_apply_overrides_model_switch_drops_stale_keys(f9_vehicle_dict: dict[str, Any]) -> None:
    run = {"name": "r", "assist": {"model": "constant_accel", "stroke_m": 100, "track": {}}}
    switched, _ = apply_overrides(run, {"assist.model": "none"}, f9_vehicle_dict)
    assert switched["assist"] == {"model": "none"}
    assert RunConfig.model_validate(switched).assist.model == "none"
    same, _ = apply_overrides(run, {"assist.model": "constant_accel"}, f9_vehicle_dict)
    assert same["assist"] == run["assist"]


def test_bad_override_paths_are_value_errors_naming_the_run(
    experiment_dict: dict[str, Any], f9_vehicle_dict: dict[str, Any]
) -> None:
    bad = copy.deepcopy(experiment_dict)
    bad["sensitivity"]["params"] = {"assist.drive_eficiency": 0.1}
    with pytest.raises(ValueError, match=r"sensitivity on run 'silo_cold'.*drive_eficiency"):
        resolve_experiment(bad, f9_vehicle_dict)
    bad = copy.deepcopy(experiment_dict)
    bad["sensitivity"]["of"] = ["pad"]  # the pad has no drive efficiency
    with pytest.raises(ValueError, match=r"run 'pad'.*drive_efficiency"):
        resolve_experiment(bad, f9_vehicle_dict)
    bad = copy.deepcopy(experiment_dict)
    bad["sensitivity"]["params"] = {"vehicle.stages.stage1.startup.kind": 0.1}
    with pytest.raises(ValueError, match="not a number"):
        resolve_experiment(bad, f9_vehicle_dict)
    bad = copy.deepcopy(experiment_dict)
    bad["sweeps"][0]["axes"] = {"assist.stroke_m.deep": [1]}
    with pytest.raises(ValueError, match="sweep 1 on run 'silo_cold'"):
        resolve_experiment(bad, f9_vehicle_dict)
    bad = copy.deepcopy(experiment_dict)
    bad["sweeps"][0]["axes"] = {"asist.net_accel_g": [1]}
    with pytest.raises(ValidationError, match="asist"):  # created key, rejected by forbid
        resolve_experiment(bad, f9_vehicle_dict)


# ------------------------------------------------- exclusive key families (SP1 step 1)

ASSIST_FAMILIES = (("net_accel_g",), ("exit_speed_mps",))
"""docs/phases/SP1-fuel-offload-planar.md, section 5.9: one of the two states the push."""
IGNITION_FAMILIES = (
    ("t_ign_s", "reference"),
    ("at_depth_m",),
    ("at_speed_mps",),
    ("at_height_m", "height_method"),
)
"""Section 5.9: one of the four states when the thrust ramp starts."""
FAMILY_GROUPS = (ASSIST_FAMILIES, IGNITION_FAMILIES)
FAMILY_OWNERS = {ASSIST_FAMILIES: ConstantAccelConfig, IGNITION_FAMILIES: IgnitionConfig}
"""The one run-level model whose dict each group's keys belong to."""
SHIPPED_BEFORE_SP1 = (
    "silo_screening_1d",
    "calibration_f9_2d",
    "silo_screening_2d",
    "silo_bridge_2d_readme",
    "guidance_trigger_2d",
)
"""The experiments shipped when the family rule was added (commit c587a08)."""
SILO_ASSIST = {
    "model": "constant_accel",
    "net_accel_g": 3.0,
    "stroke_m": 100,
    "brake_decel_g": 5,
    "track": {"angle_deg": 90, "exit_altitude_m": 0},
}
EXIT_SPEED_MPS = 76.71
"""The exit speed SP1 step 8 plans for the 200 m silo [m/s]; any number would do here."""


def _family_pairs() -> list[tuple[tuple[str, ...], tuple[str, ...]]]:
    """Every ordered pair (base family, override family) inside one group."""
    return [(a, b) for group in FAMILY_GROUPS for a in group for b in group]


def test_exclusive_family_table_is_the_design_and_is_scoped_by_key_name() -> None:
    """The table in config.py is section 5.9's, sits beside SWITCH_KEYS and is safe to
    scope by key name: no key is in two families or is a discriminator, and of all the
    pydantic models config.py defines only ConstantAccelConfig (assist group) and
    IgnitionConfig (ignition group) have a field named like a family key."""
    assert config.ASSIST_KEY_FAMILIES == ASSIST_FAMILIES
    assert config.IGNITION_KEY_FAMILIES == IGNITION_FAMILIES
    assert config.EXCLUSIVE_KEY_FAMILIES == FAMILY_GROUPS
    keys = [k for group in FAMILY_GROUPS for family in group for k in family]
    assert len(keys) == len(set(keys)) and not set(keys) & set(config.SWITCH_KEYS)
    models = [
        obj
        for obj in vars(config).values()
        if isinstance(obj, type)
        and issubclass(obj, BaseModel)
        and obj.__module__ == config.__name__
    ]
    assert ConstantAccelConfig in models and IgnitionConfig in models and len(models) > 20
    for group, owner in FAMILY_OWNERS.items():
        group_keys = {k for family in group for k in family}
        users = {m.__name__ for m in models if group_keys & set(m.model_fields)}
        assert users == {owner.__name__}
    # the fields that exist today are the first family of each group (steps 2 and 3 add
    # the others); the defaults test_run_defaults pins are untouched
    assert set(ASSIST_FAMILIES[0]) <= set(ConstantAccelConfig.model_fields)
    assert set(IGNITION_FAMILIES[0]) <= set(IgnitionConfig.model_fields)


@pytest.mark.parametrize(("base_family", "given_family"), _family_pairs())
def test_merge_keeps_one_family_per_group(
    base_family: tuple[str, ...], given_family: tuple[str, ...]
) -> None:
    """For every ordered pair of families of one group: an override that gives the keys
    of ``given_family`` over a base that uses ``base_family`` ends with the given keys
    and none of the base's other-family keys, keeps every unrelated key in place, and,
    when both are the same family, is today's per-key merge. merge_run_dicts and the
    dotted-path form agree, and neither mutates its inputs."""
    base = {"d": {"before": 1, **{k: f"base {k}" for k in base_family}, "after": {"x": 2}}}
    given = {k: f"new {k}" for k in given_family}
    if base_family == given_family:
        expected = {"before": 1, **given, "after": {"x": 2}}  # replaced in place
    else:
        expected = {"before": 1, "after": {"x": 2}, **given}  # dropped, then appended
    frozen = copy.deepcopy(base)
    merged = merge_run_dicts(base, {"d": given})
    assert merged == {"d": expected} and list(merged["d"]) == list(expected)
    dotted, _ = apply_overrides(base, {f"d.{k}": v for k, v in given.items()}, {})
    assert dotted == {"d": expected} and list(dotted["d"]) == list(expected)
    assert base == frozen


def test_merge_drops_only_what_the_given_key_displaces() -> None:
    """One key of a two-key family displaces the other families and keeps its own
    partner (a variant that only moves t_ign_s keeps the inherited reference, as
    today); an override without a family key displaces nothing; the rule acts at the
    dict level of the key (another stage's ignition is untouched) and inside a dict the
    discriminator rule did not replace."""
    timed = {"stage1": {"t_ign_s": -2.0, "reference": "push_start"}, "stage2": {"t_ign_s": 0.0}}
    base = {"assist": dict(SILO_ASSIST), "ignition": timed}
    moved = merge_run_dicts(base, {"ignition": {"stage1": {"t_ign_s": 0.5}}})
    assert moved["ignition"]["stage1"] == {"t_ign_s": 0.5, "reference": "push_start"}
    by_depth = merge_run_dicts(base, {"ignition": {"stage1": {"at_depth_m": 50.0}}})
    assert by_depth["ignition"] == {"stage1": {"at_depth_m": 50.0}, "stage2": {"t_ign_s": 0.0}}
    assert by_depth["assist"] == SILO_ASSIST
    by_height = {"at_height_m": 40.0, "height_method": "event", "startup": {"kind": "step"}}
    lower = merge_run_dicts({"s": by_height}, {"s": {"at_height_m": 10.0}})
    assert lower["s"] == {**by_height, "at_height_m": 10.0}
    back = merge_run_dicts({"s": by_height}, {"s": {"reference": "release"}})
    assert back["s"] == {"startup": {"kind": "step"}, "reference": "release"}
    shaped = merge_run_dicts({"s": by_height}, {"s": {"startup": {"kind": "lag", "tau_s": 1.0}}})
    assert shaped["s"] == {**by_height, "startup": {"kind": "lag", "tau_s": 1.0}}
    # same assist model: merged by key, the stale acceleration dropped
    by_speed = merge_run_dicts(
        base, {"assist": {"model": "constant_accel", "exit_speed_mps": EXIT_SPEED_MPS}}
    )
    assert by_speed["assist"] == {
        "model": "constant_accel",
        "stroke_m": 100,
        "brake_decel_g": 5,
        "track": {"angle_deg": 90, "exit_altitude_m": 0},
        "exit_speed_mps": EXIT_SPEED_MPS,
    }
    # a model switch still replaces the dict wholesale
    assert merge_run_dicts(base, {"assist": {"model": "none"}})["assist"] == {"model": "none"}


def test_dict_valued_path_replaces_its_dict_whole_while_a_variant_merges() -> None:
    """The two override forms inherit differently (docs/physics.md, "Merge rule"). A
    variant merges a dict per key, so only the family rule removes anything. A dotted
    path puts its value at the path: a single-key path keeps the siblings as the
    variant does, but a dict given as the value replaces the dict there whole, so
    nothing below it is inherited, family key or not (the inherited startup and fails
    go with the time keys). A two-key family given as two paths keeps the rest. The
    expected dicts are written out."""
    startup = {"kind": "ramp", "t_ramp_s": 2.0}
    base = {
        "ignition": {
            "stage1": {
                "t_ign_s": -2.0,
                "reference": "push_start",
                "startup": dict(startup),
                "fails": True,
            },
            "stage2": {"t_ign_s": 0.0},
        }
    }
    frozen = copy.deepcopy(base)
    # a key of the family in use
    variant = merge_run_dicts(base, {"ignition": {"stage1": {"t_ign_s": 0.5}}})
    assert variant["ignition"]["stage1"] == {
        "t_ign_s": 0.5,
        "reference": "push_start",
        "startup": {"kind": "ramp", "t_ramp_s": 2.0},
        "fails": True,
    }
    whole, _ = apply_overrides(base, {"ignition.stage1": {"t_ign_s": 0.5}}, {})
    assert whole == {"ignition": {"stage1": {"t_ign_s": 0.5}, "stage2": {"t_ign_s": 0.0}}}
    # a key of another family: the time keys go in every form, startup and fails only
    # under the dict-valued path
    kept = {"startup": {"kind": "ramp", "t_ramp_s": 2.0}, "fails": True, "at_depth_m": 50.0}
    variant = merge_run_dicts(base, {"ignition": {"stage1": {"at_depth_m": 50.0}}})
    assert variant["ignition"]["stage1"] == kept
    keyed, _ = apply_overrides(base, {"ignition.stage1.at_depth_m": 50.0}, {})
    assert keyed["ignition"]["stage1"] == kept
    whole, _ = apply_overrides(base, {"ignition.stage1": {"at_depth_m": 50.0}}, {})
    assert whole == {"ignition": {"stage1": {"at_depth_m": 50.0}, "stage2": {"t_ign_s": 0.0}}}
    # a two-key family as two paths (the form for a sweep or a bound) keeps the rest
    two, _ = apply_overrides(
        base,
        {"ignition.stage1.at_height_m": 40.0, "ignition.stage1.height_method": "event"},
        {},
    )
    assert two["ignition"]["stage1"] == {
        "startup": {"kind": "ramp", "t_ramp_s": 2.0},
        "fails": True,
        "at_height_m": 40.0,
        "height_method": "event",
    }
    assert two["ignition"]["stage2"] == {"t_ign_s": 0.0}
    assert base == frozen


def test_an_explicit_null_counts_as_a_given_key() -> None:
    """A key is given when it is present in the override, whatever its value: a null
    family key displaces the base's other families like any value and stays in the dict
    (it unsets nothing), in both forms; a null of the family in use replaces in place
    and keeps its partner; a null of one family next to a key of another is two
    families given together."""
    base = {
        "assist": dict(SILO_ASSIST),
        "ignition": {"stage1": {"t_ign_s": -2.0, "reference": "push_start", "fails": True}},
    }
    merged = merge_run_dicts(base, {"ignition": {"stage1": {"at_depth_m": None}}})
    assert merged["ignition"] == {"stage1": {"fails": True, "at_depth_m": None}}
    dotted, _ = apply_overrides(base, {"ignition.stage1.at_depth_m": None}, {})
    assert dotted["ignition"] == {"stage1": {"fails": True, "at_depth_m": None}}
    same = merge_run_dicts(base, {"ignition": {"stage1": {"t_ign_s": None}}})
    assert same["ignition"] == {
        "stage1": {"t_ign_s": None, "reference": "push_start", "fails": True}
    }
    nulled = merge_run_dicts(base, {"assist": {"exit_speed_mps": None}})
    assert nulled["assist"] == {
        "model": "constant_accel",
        "stroke_m": 100,
        "brake_decel_g": 5,
        "track": {"angle_deg": 90, "exit_altitude_m": 0},
        "exit_speed_mps": None,
    }
    with pytest.raises(ExclusiveKeysError, match="two exclusive families"):
        merge_run_dicts(base, {"assist": {"net_accel_g": None, "exit_speed_mps": EXIT_SPEED_MPS}})
    with pytest.raises(ExclusiveKeysError, match="two exclusive families"):
        merge_run_dicts(base, {"ignition": {"stage1": {"t_ign_s": None, "at_depth_m": None}}})
    with pytest.raises(ExclusiveKeysError, match="two exclusive families"):
        apply_overrides(
            base, {"assist.net_accel_g": None, "assist.exit_speed_mps": EXIT_SPEED_MPS}, {}
        )


@pytest.mark.parametrize(
    "override",
    [
        {"assist": {"net_accel_g": 3.0, "exit_speed_mps": EXIT_SPEED_MPS}},
        {"ignition": {"stage1": {"t_ign_s": 0.5, "at_depth_m": 50.0}}},
        {"ignition": {"stage1": {"reference": "release", "at_speed_mps": 20.0}}},
        {"ignition": {"stage1": {"at_depth_m": 50.0, "height_method": "event"}}},
        # also in a dict the merge would take wholesale (a model switch, a new key)
        {"assist": {"model": "other", "net_accel_g": 3.0, "exit_speed_mps": EXIT_SPEED_MPS}},
        {"new": {"deep": [{"at_speed_mps": 20.0, "at_height_m": 40.0}]}},
    ],
)
def test_two_families_given_together_raise_in_merge(override: dict[str, Any]) -> None:
    """Keys of two families of one group in one override dict cannot be merged (which
    one is meant?): ExclusiveKeysError, a ValueError, whatever the base holds."""
    assert issubclass(ExclusiveKeysError, ValueError)
    for base in ({}, {"assist": dict(SILO_ASSIST), "ignition": {"stage1": {"t_ign_s": -2.0}}}):
        with pytest.raises(ExclusiveKeysError, match="two exclusive families"):
            merge_run_dicts(base, override)


def test_two_families_given_together_raise_in_overrides() -> None:
    """The dotted-path form refuses two families for one dict: two paths with one
    parent, a dict value, or a path and a dict value that meet; the message names the
    dict and the keys. Two keys of one family, families of different groups and the
    same group in different dicts are fine, and vehicle paths are outside the rule."""
    run = {"assist": dict(SILO_ASSIST), "ignition": {"stage1": {"t_ign_s": -2.0}}}
    for bad in (
        {"assist.exit_speed_mps": EXIT_SPEED_MPS, "assist.net_accel_g": 1.0},
        {"ignition.stage1.at_depth_m": 50.0, "ignition.stage1.at_speed_mps": 20.0},
        {"ignition.stage1": {"t_ign_s": 0.5, "at_depth_m": 50.0}},
        {"ignition.stage1": {"t_ign_s": 0.5}, "ignition.stage1.at_depth_m": 50.0},
        {"ignition": {"stage1": {"at_height_m": 40.0}}, "ignition.stage1.reference": "release"},
    ):
        with pytest.raises(ExclusiveKeysError, match="two exclusive families"):
            apply_overrides(run, bad, {})
    with pytest.raises(ExclusiveKeysError, match=r"'assist'.*net_accel_g.*exit_speed_mps"):
        apply_overrides(run, {"assist.exit_speed_mps": EXIT_SPEED_MPS, "assist.net_accel_g": 1}, {})
    fine, _ = apply_overrides(
        run,
        {
            "ignition.stage1.at_height_m": 40.0,
            "ignition.stage1.height_method": "event",
            "ignition.stage2.t_ign_s": 1.0,
            "assist.exit_speed_mps": EXIT_SPEED_MPS,
        },
        {},
    )
    assert fine["ignition"] == {
        "stage1": {"at_height_m": 40.0, "height_method": "event"},
        "stage2": {"t_ign_s": 1.0},
    }
    quantity = {"value": 1.0, "source": "test"}
    vehicle = {"x": {"t_ign_s": dict(quantity), "net_accel_g": dict(quantity)}}
    two_families = {  # of each group, in one vehicle dict: neither refused nor displacing
        "vehicle.x.at_depth_m": 2.0,
        "vehicle.x.at_speed_mps": 20.0,
        "vehicle.x.exit_speed_mps": 3.0,
        "vehicle.x.height_method": "event",
    }
    _, v = apply_overrides(run, two_families, vehicle)
    assert list(v["x"]) == [
        "t_ign_s",
        "net_accel_g",
        "at_depth_m",
        "at_speed_mps",
        "exit_speed_mps",
        "height_method",
    ]
    assert v["x"]["t_ign_s"] == quantity and v["x"]["at_depth_m"]["value"] == 2.0
    assert v["x"]["height_method"] == "event"


def test_set_path_applies_the_family_rule_to_run_paths_only() -> None:
    """config._set_path, the function behind every sweep axis, sensitivity case and
    bound: a run path (quantity False) that sets a family key deletes the dict's keys of
    the group's other families and nothing else; a vehicle path (quantity True) never
    does; a key of the family in use is replaced in place."""
    root = {"assist": dict(SILO_ASSIST)}
    config._set_path(root, "assist.exit_speed_mps", EXIT_SPEED_MPS, quantity=False)
    assert list(root["assist"]) == ["model", "stroke_m", "brake_decel_g", "track", "exit_speed_mps"]
    assert root["assist"]["exit_speed_mps"] == EXIT_SPEED_MPS
    config._set_path(root, "assist.net_accel_g", 1.5, quantity=False)
    assert list(root["assist"]) == ["model", "stroke_m", "brake_decel_g", "track", "net_accel_g"]
    same = {"assist": dict(SILO_ASSIST)}
    config._set_path(same, "assist.net_accel_g", 0.5, quantity=False)
    assert same["assist"] == {**SILO_ASSIST, "net_accel_g": 0.5}
    assert list(same["assist"]) == list(SILO_ASSIST)
    as_vehicle = {"assist": dict(SILO_ASSIST)}
    config._set_path(as_vehicle, "assist.exit_speed_mps", EXIT_SPEED_MPS, quantity=True)
    assert as_vehicle["assist"]["net_accel_g"] == SILO_ASSIST["net_accel_g"]
    assert as_vehicle["assist"]["exit_speed_mps"]["value"] == EXIT_SPEED_MPS
    config._set_path(as_vehicle, "assist.exit_speed_mps", "fast", quantity=True)  # not a number
    assert as_vehicle["assist"]["net_accel_g"] == SILO_ASSIST["net_accel_g"]
    assert as_vehicle["assist"]["exit_speed_mps"] == "fast"
    created: dict[str, Any] = {}
    config._set_path(created, "ignition.stage1.at_depth_m", 50.0, quantity=False)
    assert created == {"ignition": {"stage1": {"at_depth_m": 50.0}}}


def test_sweep_axis_exit_speed_over_a_net_accel_parent(
    experiment_dict: dict[str, Any], f9_vehicle_dict: dict[str, Any]
) -> None:
    """A sweep axis ``assist.exit_speed_mps`` over the shipped silo_cold (net_accel_g
    3) ends, at every grid point, with only the exit speed: the override the sweep
    resolver builds for a point (one path per axis) removes net_accel_g and leaves the
    rest of the parent's run dict as it was. The same for a ramp start by depth over the
    inherited t_ign_s and reference. (The fields arrive in SP1 steps 2 and 3, so the
    points are built here with apply_overrides, as resolve_experiment does, and not
    validated.)"""
    parent = resolve_experiment(experiment_dict, f9_vehicle_dict).variants["silo_cold"]
    assert parent.run_dict["assist"]["net_accel_g"] == 3.0
    assert parent.run_dict["ignition"]["stage1"] == {"t_ign_s": 0.5, "reference": "release"}
    for speed_mps, stroke_m in itertools.product([40.0, EXIT_SPEED_MPS], [100, 200]):
        point, vehicle = apply_overrides(
            parent.run_dict,
            {"assist.exit_speed_mps": speed_mps, "assist.stroke_m": stroke_m},
            parent.vehicle_dict,
        )
        expected = {k: v for k, v in parent.run_dict["assist"].items() if k != "net_accel_g"}
        expected.update(stroke_m=stroke_m, exit_speed_mps=speed_mps)
        assert point["assist"] == expected and "net_accel_g" not in point["assist"]
        rest = {k: v for k, v in point.items() if k != "assist"}
        assert rest == {k: v for k, v in parent.run_dict.items() if k != "assist"}
        assert vehicle == parent.vehicle_dict
    by_depth, _ = apply_overrides(
        parent.run_dict, {"ignition.stage1.at_depth_m": 50.0}, parent.vehicle_dict
    )
    assert by_depth["ignition"]["stage1"] == {"at_depth_m": 50.0}
    assert by_depth["ignition"]["stage2"] == parent.run_dict["ignition"]["stage2"]


def test_mixed_families_name_the_variant_or_the_sweep(
    experiment_dict: dict[str, Any], f9_vehicle_dict: dict[str, Any]
) -> None:
    """Through resolve_experiment the error says where the two families meet: a sweep
    whose axes vary both the net acceleration and the exit speed (a grid of both is
    ambiguous at every point), and a variant that writes both."""
    bad = copy.deepcopy(experiment_dict)
    bad["sweeps"] = [
        {"of": "silo_cold", "axes": {"assist.net_accel_g": [1, 3], "assist.exit_speed_mps": [40]}}
    ]
    with pytest.raises(ExclusiveKeysError, match=r"sweep 1 on run 'silo_cold'.*'assist'"):
        resolve_experiment(bad, f9_vehicle_dict)
    bad = copy.deepcopy(experiment_dict)
    bad["variants"]["silo_cold"]["ignition"]["stage1"]["at_depth_m"] = 50.0
    with pytest.raises(ExclusiveKeysError, match=r"variant 'silo_cold'.*'ignition.stage1'"):
        resolve_experiment(bad, f9_vehicle_dict)


def _keys_and_path_segments(node: Any) -> set[str]:
    """Every dict key under ``node`` and every segment of a dotted key (a sweep axis, a
    sensitivity parameter, a bound override)."""
    if isinstance(node, dict):
        out = {seg for key in node for seg in str(key).split(".")}
        return out.union(*(_keys_and_path_segments(v) for v in node.values()))
    if isinstance(node, list):
        return set().union(*(_keys_and_path_segments(v) for v in node))
    return set()


def test_shipped_experiments_use_the_first_family_only(repo_root: Path) -> None:
    """No experiment shipped before SP1 names a key of a second family anywhere (YAML
    anchors resolved, sweep axes, sensitivity parameters and bounds included), so no
    override in them displaces anything and every resolved dict is what it was (the
    1-D golden and the planar digest pin compare them byte for byte)."""
    later = {k for group in FAMILY_GROUPS for family in group[1:] for k in family}
    assert later == {"exit_speed_mps", "at_depth_m", "at_speed_mps", "at_height_m", "height_method"}
    for name in SHIPPED_BEFORE_SP1:
        used = _keys_and_path_segments(_load(repo_root / "experiments" / f"{name}.yaml"))
        assert "t_ign_s" in used, name  # the walk reaches the run dicts
        assert not used & later, name


# ------------------------------------------------------------- shipped experiment


def test_shipped_experiment_resolves(
    experiment_dict: dict[str, Any], f9_vehicle_dict: dict[str, Any]
) -> None:
    exp = ExperimentConfig.model_validate(experiment_dict)
    assert exp.name == "silo_screening_1d" and exp.baseline.name == "pad"
    resolved = resolve_experiment(experiment_dict, f9_vehicle_dict)
    assert list(resolved.variants) == [
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
    assert next(iter(resolved.runs)) == "pad"
    assert [len(points) for points in resolved.sweeps] == [12, 9, 3]
    assert len(resolved.sensitivity) == 2 * 4 * 2

    pad = resolved.baseline.run
    assert pad.assist.model == "none"
    assert pad.ignition["stage1"].t_ign_s == -2.0 and pad.ignition["stage2"].t_ign_s == 0.0

    cold = resolved.variants["silo_cold"].run
    assert isinstance(cold.assist, ConstantAccelConfig)
    assert cold.assist.net_accel_g == 3.0 and cold.assist.stroke_m == 100.0
    assert cold.ignition["stage1"].t_ign_s == 0.5 and cold.ignition["stage1"].reference == "release"
    assert cold.ignition["stage2"].t_ign_s == 0.0  # inherited from the baseline

    imp = resolved.variants["silo_hot_full_impinged"].run
    assert isinstance(imp.assist, ConstantAccelConfig)
    assert imp.assist.exhaust_impingement_fraction == 1.0 and imp.assist.carriage_mass_t == 0.0
    assert imp.ignition["stage1"].reference == "push_start"
    sled = resolved.variants["silo_sled_22t"].run
    assert isinstance(sled.assist, ConstantAccelConfig)
    assert sled.assist.carriage_mass_t == 22.0 and sled.assist.exhaust_impingement_fraction == 0.0
    failed = resolved.variants["silo_failed"].run
    assert failed.ignition["stage1"].fails and failed.end == "impact"
    instant = resolved.variants["silo_instant"].run.ignition["stage1"]
    assert instant.startup is not None and instant.startup.kind == "step"

    # variants keep the baseline vehicle
    for r in resolved.runs.values():
        assert r.vehicle_dict == f9_vehicle_dict


def test_shipped_sweeps_and_sensitivity(
    experiment_dict: dict[str, Any], f9_vehicle_dict: dict[str, Any]
) -> None:
    resolved = resolve_experiment(experiment_dict, f9_vehicle_dict)
    first = resolved.sweeps[0]
    assert first[0].overrides == {"assist.net_accel_g": 0.5, "assist.stroke_m": 50}
    assert first[-1].overrides == {"assist.net_accel_g": 5, "assist.stroke_m": 300}
    assert first[0].run.name == "run_0001" and first[-1].run.name == "run_0012"
    assert first[-1].run.run.assist.net_accel_g == 5.0
    second = resolved.sweeps[1]
    point = second[3]
    assert point.overrides == {
        "ignition.stage1.t_ign_s": 0.5,
        "ignition.stage1.startup.t_ramp_s": 1,
    }
    ign = point.run.run.ignition["stage1"]
    assert ign.startup is not None and ign.startup.t_ramp_s == 1.0 and ign.startup.kind is None
    base_startup = point.run.to_vehicle().stages[0].startup
    resolved_startup = ign.resolved_startup(base_startup)
    assert resolved_startup.kind == "ramp" and resolved_startup.t_ramp_s == 1.0
    third = resolved.sweeps[2]
    assert third[2].run.run.ignition["stage1"].startup.tau_s == 3.0

    by_key = {(c.of, c.param, c.fraction): c for c in resolved.sensitivity}
    up = by_key[("silo_cold", "vehicle.stages.stage1.dry_mass_t", 0.10)]
    q = up.run.vehicle.stages[0].dry_mass_t
    assert math.isclose(q.value, 25.6 * 1.1, rel_tol=1e-12) and q.assumed and q.note == "override"
    assert math.isclose(up.run.to_vehicle().stages[0].dry_mass_kg, 28_160.0, rel_tol=1e-12)
    down = by_key[("silo_hot_full", "assist.drive_efficiency", -0.10)]
    assert math.isclose(down.run.run.assist.drive_efficiency, 0.45, rel_tol=1e-12)
    isp = by_key[("silo_cold", "vehicle.screening.stage_isp_eff_s.0", 0.10)]
    assert math.isclose(isp.run.to_vehicle().screening_isp_s[0], 295 * 1.1, rel_tol=1e-12)
    assert isp.run.to_vehicle().screening_isp_s[1] == 348.0


def test_experiment_name_rules(experiment_dict: dict[str, Any]) -> None:
    bad = copy.deepcopy(experiment_dict)
    bad["sweeps"][0]["of"] = "nope"
    with pytest.raises(ValidationError, match="no such run"):
        ExperimentConfig.model_validate(bad)
    bad = copy.deepcopy(experiment_dict)
    bad["variants"]["pad"] = {}
    with pytest.raises(ValidationError, match="baseline's name"):
        ExperimentConfig.model_validate(bad)


def test_ignition_must_name_a_stage(
    experiment_dict: dict[str, Any], f9_vehicle_dict: dict[str, Any]
) -> None:
    bad = copy.deepcopy(experiment_dict)
    bad["baseline"]["ignition"]["stage3"] = {"t_ign_s": 0.0}
    with pytest.raises(ValueError, match="unknown stages"):
        resolve_experiment(bad, f9_vehicle_dict)


def test_tiny_experiment_resolves(tiny_dict: dict[str, Any], toy_dict: dict[str, Any]) -> None:
    resolved = resolve_experiment(tiny_dict, toy_dict)
    assert list(resolved.variants) == ["silo"]
    assert [len(points) for points in resolved.sweeps] == [4]
    assert resolved.sensitivity == []
    silo = resolved.variants["silo"].run.assist
    assert isinstance(silo, ConstantAccelConfig)
    assert silo.net_accel_g == 1.0 and silo.stroke_m == 20.0
    toy = resolved.baseline.to_vehicle()
    assert math.isclose(toy.stages[0].c_mps, 3000.0, rel_tol=1e-12)
    assert toy.liftoff_mass_kg() == 1360.0


def test_sweep_points_are_numbered_from_one(repo_root: Path) -> None:
    """Sweeps and points are both 1-based so they match the sweep_<n>/run_<NNNN> dirs."""
    exp_path = repo_root / "experiments" / "silo_screening_1d.yaml"
    exp = yaml.safe_load(exp_path.read_text(encoding="utf-8"))
    veh_path = repo_root / exp["vehicle"]
    veh = yaml.safe_load(veh_path.read_text(encoding="utf-8"))
    resolved = resolve_experiment(exp, veh)
    for k, points in enumerate(resolved.sweeps, start=1):
        assert [p.sweep_index for p in points] == [k] * len(points)
        assert [p.point_index for p in points] == list(range(1, len(points) + 1))
        assert all(p.run.name == f"run_{p.point_index:04d}" for p in points)
