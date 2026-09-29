"""Validated configuration: pydantic v2 models for vehicle and experiment YAML.

No file I/O here: cli.py reads the YAML and hands plain dicts to these models. Vehicle
files are all-Quantity (every number is ``{value, source}`` or ``{value, assumed: true}``;
a bare number raises). Experiment files use bare numbers. Units are carried by field
suffixes (``_t``, ``_kN``, ``_s``, ``_m``, ``_deg``, ``_g``) and converted to SI here and
nowhere else, through launchsim.units.

Phase 1 limits are enforced as validation errors: no Earth rotation ("Phase 2"), vertical
tracks only ("Phase 2"), and only the ``none`` and ``constant_accel`` assist models
(``linear_motor`` and ``cable_winch`` are "planned for Phase 3").
"""

from __future__ import annotations

import copy
import itertools
import math
from dataclasses import dataclass
from typing import Annotated, Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from launchsim import units
from launchsim.constants import OMEGA_EARTH_RADS, P_SEA_LEVEL_PA
from launchsim.vehicle import Engine, Stage, Startup, StartupKind, Vehicle

VEHICLE_PREFIX = "vehicle."
OVERRIDE_NOTE = "override"
PlannedModel = Literal["linear_motor", "cable_winch"]
PLANNED_MODELS: tuple[str, ...] = get_args(PlannedModel)
"""Assist models the README names that are not implemented yet (one source of truth)."""
SWITCH_KEYS = ("model", "kind")
"""Discriminator keys: a dict whose value for one of these differs from the base's
replaces the base dict wholesale when merging, so no stale keys of the old choice
survive (assist ``model``; startup ``kind``)."""
LATITUDE_RANGE_DEG = (-90.0, 90.0)
AZIMUTH_RANGE_DEG = (0.0, 360.0)
VERTICAL_TRACK_DEG = 90.0


class _Model(BaseModel):
    """Base for every config model: unknown keys are errors and instances are frozen."""

    model_config = ConfigDict(extra="forbid", frozen=True)


def _is_number(x: object) -> bool:
    """True for int or float but not bool."""
    return isinstance(x, int | float) and not isinstance(x, bool)


# --------------------------------------------------------------------------- vehicle file


class Quantity(_Model):
    """A sourced number from a vehicle file: exactly one of ``source`` or ``assumed``.

    The value is a finite number (NaN and inf are rejected) and a source is non-blank."""

    value: float = Field(allow_inf_nan=False)
    source: str | None = None
    assumed: bool = False
    note: str | None = None

    @field_validator("source")
    @classmethod
    def _source_not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("source must not be blank")
        return v

    @model_validator(mode="before")
    @classmethod
    def _reject_bare(cls, data: Any) -> Any:
        if isinstance(data, Quantity):
            return data
        if not isinstance(data, dict):
            raise ValueError(
                "bare value; vehicle files need {value, source} or {value, assumed: true}"
            )
        if not _is_number(data.get("value")):
            raise ValueError("Quantity value must be a number")
        return data

    @model_validator(mode="after")
    def _one_provenance(self) -> Quantity:
        if (self.source is not None) == self.assumed:
            raise ValueError("give exactly one of source or assumed: true")
        return self


class StartupConfig(_Model):
    """Vehicle-file startup shape (all-Quantity durations).

    A ramp needs t_ramp_s and a lag needs tau_s; a duration that belongs to another
    shape is an error (the same rule as the experiment-side StartupOverride)."""

    kind: StartupKind
    t_ramp_s: Quantity | None = None
    tau_s: Quantity | None = None

    @model_validator(mode="after")
    def _shape_matches_duration(self) -> StartupConfig:
        if self.kind == "ramp" and self.t_ramp_s is None:
            raise ValueError("startup kind ramp needs t_ramp_s")
        if self.kind == "lag" and self.tau_s is None:
            raise ValueError("startup kind lag needs tau_s")
        if self.t_ramp_s is not None and self.kind != "ramp":
            raise ValueError(f"startup gives t_ramp_s but the kind is {self.kind!r}")
        if self.tau_s is not None and self.kind != "lag":
            raise ValueError(f"startup gives tau_s but the kind is {self.kind!r}")
        return self

    def to_startup(self) -> Startup:
        """The frozen Startup dataclass."""
        return Startup(
            kind=self.kind,
            t_ramp_s=0.0 if self.t_ramp_s is None else self.t_ramp_s.value,
            tau_s=0.0 if self.tau_s is None else self.tau_s.value,
        )


class EngineConfig(_Model):
    """One engine type on a stage. Exit area comes from ``exit_area_m2`` or, when only
    ``thrust_sl_kN`` is given, from (T_vac - T_sl) / p_sea_level; otherwise it is 0."""

    count: Quantity
    thrust_vac_kN: Quantity
    isp_vac_s: Quantity
    thrust_sl_kN: Quantity | None = None
    exit_area_m2: Quantity | None = None

    @model_validator(mode="after")
    def _checks(self) -> EngineConfig:
        if not float(self.count.value).is_integer() or self.count.value < 1:
            raise ValueError("engine count must be a positive integer")
        if self.thrust_sl_kN is not None and self.exit_area_m2 is not None:
            raise ValueError("give thrust_sl_kN or exit_area_m2, not both")
        if self.thrust_sl_kN is not None and self.thrust_sl_kN.value > self.thrust_vac_kN.value:
            raise ValueError("sea-level thrust cannot exceed vacuum thrust")
        return self

    @property
    def n_engines(self) -> int:
        """Engine count."""
        return int(self.count.value)

    def exit_area_per_engine_m2(self) -> float:
        """Nozzle exit area per engine [m^2]."""
        if self.exit_area_m2 is not None:
            return self.exit_area_m2.value
        if self.thrust_sl_kN is not None:
            dt_n = units.kn_to_n(self.thrust_vac_kN.value - self.thrust_sl_kN.value)
            return dt_n / P_SEA_LEVEL_PA
        return 0.0

    def to_engine(self) -> Engine:
        """The frozen Engine dataclass (SI)."""
        return Engine(
            thrust_vac_N=units.kn_to_n(self.thrust_vac_kN.value),
            isp_vac_s=self.isp_vac_s.value,
            exit_area_m2=self.exit_area_per_engine_m2(),
        )


class StageConfig(_Model):
    """One stage of a vehicle file."""

    name: str
    dry_mass_t: Quantity
    propellant_mass_t: Quantity
    engine: EngineConfig
    startup: StartupConfig = StartupConfig(kind="step")
    coast_before_ignition_s: Quantity | None = None

    def to_stage(self) -> Stage:
        """The frozen Stage dataclass (SI)."""
        coast = 0.0 if self.coast_before_ignition_s is None else self.coast_before_ignition_s.value
        return Stage(
            name=self.name,
            dry_mass_kg=units.t_to_kg(self.dry_mass_t.value),
            propellant_mass_kg=units.t_to_kg(self.propellant_mass_t.value),
            engine=self.engine.to_engine(),
            n_engines=self.engine.n_engines,
            startup=self.startup.to_startup(),
            coast_before_ignition_s=coast,
        )


class ScreeningConfig(_Model):
    """Effective per-stage Isp [s] for the ideal-rocket-equation screening only."""

    stage_isp_eff_s: list[Quantity]


class VehicleConfig(_Model):
    """A vehicle file: stages in firing order, fairing and payload, fairing drop rule.

    Validation builds the Vehicle dataclass once, so the physical checks that live there
    (thrust and Isp > 0, dry mass >= 0, propellant > 0, coast and startup durations >= 0,
    payload and fairing >= 0, screening Isp > 0) fail at load with the vehicle named."""

    name: str
    description: str | None = None
    stages: list[StageConfig]
    fairing_mass_t: Quantity
    payload_mass_t: Quantity
    fairing_drop: Literal["staging", "never"] = "staging"
    screening: ScreeningConfig | None = None

    @model_validator(mode="after")
    def _checks(self) -> VehicleConfig:
        names = [s.name for s in self.stages]
        if not names:
            raise ValueError("a vehicle needs at least one stage")
        if len(set(names)) != len(names):
            raise ValueError("stage names must be unique")
        if self.screening is not None and len(self.screening.stage_isp_eff_s) != len(names):
            raise ValueError("screening.stage_isp_eff_s needs one entry per stage")
        try:
            self.to_vehicle()
        except ValueError as exc:
            raise ValueError(f"vehicle {self.name!r}: {exc}") from exc
        return self

    def to_vehicle(self) -> Vehicle:
        """The frozen Vehicle dataclass (SI)."""
        isps = (
            () if self.screening is None else tuple(q.value for q in self.screening.stage_isp_eff_s)
        )
        return Vehicle(
            stages=tuple(s.to_stage() for s in self.stages),
            fairing_mass_kg=units.t_to_kg(self.fairing_mass_t.value),
            payload_mass_kg=units.t_to_kg(self.payload_mass_t.value),
            fairing_drop=self.fairing_drop,
            screening_isp_s=isps,
        )


# ------------------------------------------------------------------------ experiment file


class SiteConfig(_Model):
    """Launch site: latitude [-90, 90] and azimuth [0, 360] in degrees (clockwise from
    north); Earth rotation is a Phase 2 feature."""

    latitude_deg: float = Field(default=28.5, ge=LATITUDE_RANGE_DEG[0], le=LATITUDE_RANGE_DEG[1])
    azimuth_deg: float = Field(default=90.0, ge=AZIMUTH_RANGE_DEG[0], le=AZIMUTH_RANGE_DEG[1])
    include_rotation: bool = False

    @field_validator("include_rotation")
    @classmethod
    def _no_rotation_yet(cls, v: bool) -> bool:
        if v:
            raise ValueError("include_rotation: true is a Phase 2 feature (omega_p = 0 now)")
        return v

    @property
    def latitude_rad(self) -> float:
        """Latitude [rad]."""
        return units.deg_to_rad(self.latitude_deg)

    @property
    def azimuth_rad(self) -> float:
        """Launch azimuth [rad], clockwise from north."""
        return units.deg_to_rad(self.azimuth_deg)

    @property
    def omega_p_rads(self) -> float:
        """Planar Earth rotation rate omega_E cos(lat) sin(az) [rad/s]; 0 without rotation."""
        if not self.include_rotation:
            return 0.0
        return OMEGA_EARTH_RADS * math.cos(self.latitude_rad) * math.sin(self.azimuth_rad)


class TrackConfig(_Model):
    """Straight track: angle above horizontal [deg] (90 only in Phase 1) and the altitude
    of its exit [m] relative to the pad datum z = 0."""

    angle_deg: float = VERTICAL_TRACK_DEG
    exit_altitude_m: float = 0.0

    @field_validator("angle_deg")
    @classmethod
    def _vertical_only(cls, v: float) -> float:
        if v != VERTICAL_TRACK_DEG:
            raise ValueError("track angle_deg other than 90 is a Phase 2 feature")
        return v

    @property
    def phi_rad(self) -> float:
        """Track angle above horizontal [rad]."""
        return units.deg_to_rad(self.angle_deg)


class NoAssistConfig(_Model):
    """Pad launch: no track phase."""

    model: Literal["none"] = "none"


class ConstantAccelConfig(_Model):
    """Prescribed constant net acceleration along a straight track (screening drive).

    The ``_g`` and ``_t`` fields hold the YAML-side units and exist only for the file
    boundary and reporting; dynamics and the assist model must use the SI properties
    net_accel_mps2, carriage_mass_kg and brake_decel_mps2."""

    model: Literal["constant_accel"]
    net_accel_g: float = Field(gt=0.0)
    stroke_m: float = Field(gt=0.0)
    carriage_mass_t: float = Field(default=0.0, ge=0.0)
    brake_decel_g: float = Field(gt=0.0)
    drive_efficiency: float = Field(default=1.0, gt=0.0, le=1.0)
    exhaust_impingement_fraction: float = Field(default=0.0, ge=0.0, le=1.0)
    shaft: Literal["vented"] = "vented"
    allow_negative_drive_force: bool = False
    track: TrackConfig = TrackConfig()

    @property
    def net_accel_mps2(self) -> float:
        """Prescribed net acceleration [m/s^2]."""
        return units.from_g(self.net_accel_g)

    @property
    def carriage_mass_kg(self) -> float:
        """Carriage mass [kg]."""
        return units.t_to_kg(self.carriage_mass_t)

    @property
    def brake_decel_mps2(self) -> float:
        """Carriage braking deceleration [m/s^2]."""
        return units.from_g(self.brake_decel_g)


class PlannedAssistConfig(_Model):
    """Placeholder for drives that exist in the README but not yet in the code. Extra keys
    are allowed so that the "planned for Phase 3" message wins over an extra-key error."""

    model_config = ConfigDict(extra="allow", frozen=True)

    model: PlannedModel

    @model_validator(mode="after")
    def _not_yet(self) -> PlannedAssistConfig:
        raise ValueError(f"assist model {self.model!r} is planned for Phase 3")


AssistConfig = Annotated[
    NoAssistConfig | ConstantAccelConfig | PlannedAssistConfig, Field(discriminator="model")
]


class StartupOverride(_Model):
    """Experiment-side startup override (bare numbers); unset fields keep the vehicle's."""

    kind: StartupKind | None = None
    t_ramp_s: float | None = Field(default=None, ge=0.0)
    tau_s: float | None = Field(default=None, ge=0.0)

    def resolve(self, base: Startup) -> Startup:
        """Merge this override over the vehicle's Startup.

        A kind switched to ramp or lag needs its duration, from this override or from the
        vehicle (a zero inherited duration would silently make it a step, so it raises);
        restating the vehicle's own kind changes nothing and is always allowed. A
        duration given for a shape other than the resolved kind raises too. The duration
        of the other shape is zeroed so the resolved Startup reads as what it is.
        """
        kind = base.kind if self.kind is None else self.kind
        t_ramp = base.t_ramp_s if self.t_ramp_s is None else self.t_ramp_s
        tau = base.tau_s if self.tau_s is None else self.tau_s
        if kind != base.kind:
            if kind == "ramp" and self.t_ramp_s is None and t_ramp == 0.0:
                raise ValueError("startup override kind ramp needs t_ramp_s")
            if kind == "lag" and self.tau_s is None and tau == 0.0:
                raise ValueError("startup override kind lag needs tau_s")
        if self.t_ramp_s is not None and kind != "ramp":
            raise ValueError(f"startup override gives t_ramp_s but the kind is {kind!r}")
        if self.tau_s is not None and kind != "lag":
            raise ValueError(f"startup override gives tau_s but the kind is {kind!r}")
        return Startup(
            kind=kind,
            t_ramp_s=t_ramp if kind == "ramp" else 0.0,
            tau_s=tau if kind == "lag" else 0.0,
        )


class IgnitionConfig(_Model):
    """When a stage lights: t_ign_s [s] relative to ``release`` (stage 1: track exit or
    hold-down release; later stages: end of their staging coast) or to ``push_start``
    (first stage only, and only on a run with an assist model: a pad has no push)."""

    t_ign_s: float = 0.0
    reference: Literal["release", "push_start"] = "release"
    startup: StartupOverride | None = None
    fails: bool = False

    def resolved_startup(self, base: Startup) -> Startup:
        """The stage's Startup after applying this ignition's override, if any."""
        return base if self.startup is None else self.startup.resolve(base)


class IntegratorConfig(_Model):
    """solve_ivp settings and the output sampling interval."""

    rtol: float = Field(default=1e-10, gt=0.0)
    first_step_s: float = Field(default=1e-3, gt=0.0)
    ramp_steps: int = Field(default=10, ge=1)
    lag_steps_per_tau: int = Field(default=4, ge=1)
    push_steps: int = Field(default=50, ge=1)
    t_max_s: float = Field(default=3600.0, gt=0.0)
    sample_dt_s: float = Field(default=0.05, gt=0.0)


RunEnd = Literal["stage1_burnout", "all_burnout", "apex", "impact"]


class RunConfig(_Model):
    """One run: site, assist, per-stage ignition (keyed by stage name) and where to stop."""

    name: str
    site: SiteConfig = SiteConfig()
    assist: AssistConfig = Field(default_factory=NoAssistConfig)
    ignition: dict[str, IgnitionConfig] = Field(default_factory=dict)
    end: RunEnd = "stage1_burnout"
    integrator: IntegratorConfig = IntegratorConfig()

    @model_validator(mode="after")
    def _ignition_rules(self) -> RunConfig:
        if any(ign.fails for ign in self.ignition.values()) and self.end != "impact":
            raise ValueError("ignition fails: true requires end: impact")
        pushed = [n for n, ign in self.ignition.items() if ign.reference == "push_start"]
        if pushed and self.assist.model == "none":
            raise ValueError(
                f"ignition {pushed[0]}: reference push_start needs an assist model "
                "(a pad run has no push)"
            )
        return self

    def ignition_for(self, stage_name: str) -> IgnitionConfig:
        """Ignition settings of a stage; the default when the run does not list it."""
        return self.ignition.get(stage_name, IgnitionConfig())


class SweepConfig(_Model):
    """A full grid over dotted-path axes applied to the run named ``of``."""

    of: str
    axes: dict[str, list[Any]]

    @field_validator("axes")
    @classmethod
    def _non_empty(cls, v: dict[str, list[Any]]) -> dict[str, list[Any]]:
        if not v or any(len(vals) == 0 for vals in v.values()):
            raise ValueError("sweep axes must be non-empty lists")
        return v


class SensitivityConfig(_Model):
    """+/- fraction on each dotted-path parameter, for each run named in ``of``."""

    of: list[str]
    params: dict[str, float]

    @field_validator("params")
    @classmethod
    def _fractions(cls, v: dict[str, float]) -> dict[str, float]:
        if any(not 0.0 < f < 1.0 for f in v.values()):
            raise ValueError("sensitivity fractions must lie in (0, 1)")
        return v


class ExperimentConfig(_Model):
    """An experiment file: vehicle path, baseline run, variant overrides, sweeps and
    sensitivity. Variant values are partial run dicts merged over the baseline."""

    name: str
    vehicle: str
    baseline: RunConfig
    variants: dict[str, dict[str, Any]] = Field(default_factory=dict)
    sweeps: list[SweepConfig] = Field(default_factory=list)
    sensitivity: SensitivityConfig | None = None

    @model_validator(mode="after")
    def _names(self) -> ExperimentConfig:
        known = {self.baseline.name, *self.variants}
        if self.baseline.name in self.variants:
            raise ValueError(f"variant {self.baseline.name!r} has the baseline's name")
        for sweep in self.sweeps:
            if sweep.of not in known:
                raise ValueError(f"sweep of {sweep.of!r}: no such run")
        if self.sensitivity is not None:
            for of in self.sensitivity.of:
                if of not in known:
                    raise ValueError(f"sensitivity of {of!r}: no such run")
        return self


# ---------------------------------------------------------------- overrides and merging


class ConfigPathError(ValueError):
    """A dotted override path that does not address the run or vehicle dict."""


def merge_run_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge a variant override over a run dict: dicts merge by key, scalars and lists
    replace. A dict carrying a discriminator key (SWITCH_KEYS: assist ``model``, startup
    ``kind``) that the base's dict lacks or differs from replaces it wholesale, so
    switching assist models or startup shapes leaves no stale keys behind. Inputs are not
    mutated."""
    out = copy.deepcopy(base)
    for key, value in override.items():
        current = out.get(key)
        if isinstance(value, dict) and isinstance(current, dict) and not _switches(current, value):
            out[key] = merge_run_dicts(current, value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _switches(current: dict[str, Any], value: dict[str, Any]) -> bool:
    """True when value changes a discriminator key of current (see SWITCH_KEYS)."""
    return any(k in value and current.get(k) != value[k] for k in SWITCH_KEYS)


def _split(path: str) -> list[str]:
    parts = path.split(".")
    if not path or any(p == "" for p in parts):
        raise ConfigPathError(f"malformed override path {path!r}")
    return parts


def _step(node: Any, seg: str, path: str, create: bool) -> tuple[Any, Any]:
    """Return (container, key) addressing seg inside node, creating a dict when allowed."""
    if isinstance(node, dict):
        if seg not in node:
            if not create:
                raise ConfigPathError(f"{path}: key {seg!r} not found")
            node[seg] = {}
        return node, seg
    if isinstance(node, list):
        if seg.lstrip("-").isdigit():
            idx = int(seg)
            if not -len(node) <= idx < len(node):
                raise ConfigPathError(f"{path}: index {idx} out of range")
            return node, idx
        for i, item in enumerate(node):
            if isinstance(item, dict) and item.get("name") == seg:
                return node, i
        raise ConfigPathError(f"{path}: no list item named {seg!r}")
    raise ConfigPathError(f"{path}: cannot descend into {type(node).__name__} at {seg!r}")


def read_path(root: dict[str, Any], path: str) -> Any:
    """The raw node at a dotted path (list segments by name or integer index)."""
    node: Any = root
    for seg in _split(path):
        container, key = _step(node, seg, path, create=False)
        node = container[key]
    return node


def read_value(root: dict[str, Any], path: str) -> Any:
    """The value at a dotted path, unwrapping a Quantity dict to its ``value``."""
    node = read_path(root, path)
    if isinstance(node, dict) and "value" in node:
        return node["value"]
    return node


def _set_path(root: dict[str, Any], path: str, value: Any, quantity: bool) -> None:
    segs = _split(path)
    node: Any = root
    for seg in segs[:-1]:
        container, key = _step(node, seg, path, create=True)
        node = container[key]
    if isinstance(node, dict):
        container, key, current = node, segs[-1], node.get(segs[-1])
    else:
        container, key = _step(node, segs[-1], path, create=False)
        current = container[key]
    is_quantity = isinstance(current, dict) and "value" in current
    if quantity and _is_number(value) and (is_quantity or current is None):
        container[key] = {"value": value, "assumed": True, "note": OVERRIDE_NOTE}
    elif not quantity and key in SWITCH_KEYS and isinstance(container, dict) and current != value:
        container.clear()  # switching model or kind: drop the old keys (see merge_run_dicts)
        container[key] = value
    else:
        container[key] = copy.deepcopy(value)


def apply_overrides(
    run_dict: dict[str, Any], overrides: dict[str, Any], vehicle_dict: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply ``{dotted.path: value}`` overrides and return new (run, vehicle) dicts.

    Paths starting with ``vehicle.`` go to the vehicle dict, where a number aimed at a
    Quantity (or at a key that does not exist yet) becomes ``{value, assumed: true, note:
    override}``; any other target takes the raw value and validation reports a type
    mismatch. Missing intermediate dict keys are created (validation catches typos); a
    missing named list item or index raises ConfigPathError; list segments match an item's
    ``name`` or an integer index. Setting a discriminator key (``model``, ``kind``) to a
    different value replaces its whole dict, as merge_run_dicts does.
    """
    run = copy.deepcopy(run_dict)
    vehicle = copy.deepcopy(vehicle_dict)
    for path, value in overrides.items():
        if path.startswith(VEHICLE_PREFIX):
            _set_path(vehicle, path[len(VEHICLE_PREFIX) :], value, quantity=True)
        else:
            _set_path(run, path, value, quantity=False)
    return run, vehicle


def _read_any(run: dict[str, Any], vehicle: dict[str, Any], path: str) -> Any:
    if path.startswith(VEHICLE_PREFIX):
        return read_value(vehicle, path[len(VEHICLE_PREFIX) :])
    return read_value(run, path)


# ----------------------------------------------------------------------- resolution


@dataclass(frozen=True)
class ResolvedRun:
    """A validated run with its vehicle, plus the raw dicts that produced them."""

    name: str
    run: RunConfig
    vehicle: VehicleConfig
    run_dict: dict[str, Any]
    vehicle_dict: dict[str, Any]

    def to_vehicle(self) -> Vehicle:
        """The frozen Vehicle dataclass."""
        return self.vehicle.to_vehicle()


@dataclass(frozen=True)
class SweepPoint:
    """One grid point of a sweep.

    ``run.name`` is ``run_NNNN`` with NNNN = point_index, numbered within its own sweep,
    so it is unique only per sweep: results must be namespaced by sweep_index as well
    (for example ``sweep_1/run_0001``) or the sweeps of one experiment would collide.
    """

    sweep_index: int
    point_index: int
    of: str
    overrides: dict[str, Any]
    run: ResolvedRun


@dataclass(frozen=True)
class SensitivityCase:
    """One +/- perturbation of one parameter of one run."""

    of: str
    param: str
    fraction: float
    run: ResolvedRun


@dataclass(frozen=True)
class ResolvedExperiment:
    """Everything an experiment declares, validated, nothing run."""

    experiment: ExperimentConfig
    baseline: ResolvedRun
    variants: dict[str, ResolvedRun]
    sweeps: list[list[SweepPoint]]
    sensitivity: list[SensitivityCase]

    @property
    def runs(self) -> dict[str, ResolvedRun]:
        """Baseline first, then every variant, keyed by name."""
        return {self.baseline.name: self.baseline, **self.variants}


def resolve_run(name: str, run_dict: dict[str, Any], vehicle_dict: dict[str, Any]) -> ResolvedRun:
    """Validate one run dict and its vehicle dict together."""
    run_dict = {**copy.deepcopy(run_dict), "name": name}
    run = RunConfig.model_validate(run_dict)
    vehicle = VehicleConfig.model_validate(vehicle_dict)
    unknown = set(run.ignition) - {s.name for s in vehicle.stages}
    if unknown:
        raise ValueError(f"run {name!r}: ignition names unknown stages {sorted(unknown)}")
    for i, stage in enumerate(vehicle.stages):
        ignition = run.ignition_for(stage.name)
        if i > 0 and ignition.reference == "push_start":
            raise ValueError(
                f"run {name!r}, ignition {stage.name}: reference push_start is only for "
                "the first stage"
            )
        try:  # startup overrides must resolve against this vehicle
            ignition.resolved_startup(stage.startup.to_startup())
        except ValueError as exc:
            raise ValueError(f"run {name!r}, ignition {stage.name}: {exc}") from exc
    return ResolvedRun(
        name=name,
        run=run,
        vehicle=vehicle,
        run_dict=run_dict,
        vehicle_dict=copy.deepcopy(vehicle_dict),
    )


def _perturb(
    parent: ResolvedRun, overrides: dict[str, Any], what: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """apply_overrides on a resolved run, naming the run and the caller on a bad path."""
    try:
        return apply_overrides(parent.run_dict, overrides, parent.vehicle_dict)
    except ConfigPathError as exc:
        raise ConfigPathError(f"{what} on run {parent.name!r}: {exc}") from exc


def _nominal_value(parent: ResolvedRun, param: str) -> float:
    """The number a sensitivity parameter currently has on a resolved run."""
    try:
        nominal = _read_any(parent.run_dict, parent.vehicle_dict, param)
    except ConfigPathError as exc:
        raise ConfigPathError(f"sensitivity on run {parent.name!r}: {exc}") from exc
    if not _is_number(nominal):
        raise ValueError(
            f"sensitivity {param} on run {parent.name!r}: value {nominal!r} is not a number"
        )
    return float(nominal)


def resolve_experiment(
    exp_dict: dict[str, Any], vehicle_dict: dict[str, Any]
) -> ResolvedExperiment:
    """Validate the baseline, every variant, every sweep point and every sensitivity case
    of an experiment against one vehicle dict, without running anything.

    Raises pydantic ValidationError, ConfigPathError or ValueError (all ValueError
    subclasses) with the run and path named; nothing else escapes for a bad file."""
    experiment = ExperimentConfig.model_validate(exp_dict)
    base_dict = exp_dict["baseline"]
    baseline = resolve_run(experiment.baseline.name, base_dict, vehicle_dict)
    variants: dict[str, ResolvedRun] = {}
    for vname, override in experiment.variants.items():
        variants[vname] = resolve_run(vname, merge_run_dicts(base_dict, override), vehicle_dict)
    runs = {baseline.name: baseline, **variants}

    sweeps: list[list[SweepPoint]] = []
    for k, sweep in enumerate(experiment.sweeps):
        parent = runs[sweep.of]
        points: list[SweepPoint] = []
        paths = list(sweep.axes)
        for i, values in enumerate(itertools.product(*(sweep.axes[p] for p in paths)), start=1):
            overrides = dict(zip(paths, values, strict=True))
            r, v = _perturb(parent, overrides, f"sweep {k + 1}")
            point = resolve_run(f"run_{i:04d}", r, v)
            points.append(SweepPoint(k, i, sweep.of, overrides, point))
        sweeps.append(points)

    cases: list[SensitivityCase] = []
    if experiment.sensitivity is not None:
        for of in experiment.sensitivity.of:
            parent = runs[of]
            for param, fraction in experiment.sensitivity.params.items():
                nominal = _nominal_value(parent, param)
                for sign in (+1.0, -1.0):
                    value = nominal * (1.0 + sign * fraction)
                    r, v = _perturb(parent, {param: value}, "sensitivity")
                    label = f"{of}__{param}__{'+' if sign > 0 else '-'}{fraction:g}"
                    cases.append(
                        SensitivityCase(of, param, sign * fraction, resolve_run(label, r, v))
                    )
    return ResolvedExperiment(experiment, baseline, variants, sweeps, cases)
