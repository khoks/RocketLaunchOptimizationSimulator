"""Validated configuration: pydantic v2 models for vehicle and experiment YAML.

No file I/O here: cli.py reads the YAML and hands plain dicts to these models. Vehicle
files are all-Quantity (every number is ``{value, source}`` or ``{value, assumed: true}``,
or an entry of a QuantityList table such as the C_D(M) table, which carries one
provenance for all its lists; a bare number raises). Experiment files use bare numbers.
Units are carried by field suffixes (``_t``, ``_kN``, ``_s``, ``_m``, ``_m2``, ``_W_m2``,
``_deg``, ``_g``) and converted to SI here and nowhere else, through launchsim.units.

Model selector and shared blocks (Phase 2). An experiment picks its model once with the
experiment-level ``dynamics`` (``vertical_1d``, the default, or ``planar_2d``). The
experiment-level shared blocks ``dynamics``, ``site``, ``guidance``, ``search``,
``target_orbit`` and ``checks`` are injected into every run dict by resolve_experiment
(``dynamics`` and ``site`` as run keys; the last four under ``RunConfig.planar``), only
when the experiment declares them, so a 1-D experiment that declares none resolves to
the same run dicts as before. Variants, sweeps (except a paired guidance sweep of a
``guidance_study``), sensitivity cases and bounds may not touch them; calibration
``cases`` may change ``site``, ``target_orbit`` and the vehicle, and are never compared.

The ``offload`` block (planar_2d with a payload search only; SP1 step 7) is not a
shared block: it names cases built on the variants (``offload_case_start``, the vehicle
changes restated through ``apply_overrides``), the pad control, sensitivity arms and
energy inputs, resolved into ``ResolvedOffload`` and run by ``results_io``.

Limits enforced as validation errors: Earth rotation only on planar_2d runs (the 1-D
model keeps omega_p = 0: "a Phase 2 feature"), vertical tracks only ("a Phase 3
feature"), only the ``none`` and ``constant_accel`` assist models (``linear_motor`` and
``cable_winch`` are "planned for Phase 3"), no heating-rule fairing on a vertical_1d run
("a planar_2d feature"), and ``end: insertion`` only on planar_2d runs.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import sys
from collections.abc import Callable, Collection, Iterator
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal, get_args

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_serializer,
    model_validator,
)

from launchsim import units
from launchsim.constants import OMEGA_EARTH_RADS, P_SEA_LEVEL_PA, R_EARTH_M
from launchsim.vehicle import (
    HEATING_TRIGGER,
    OFFLOAD_MODES,
    CdTable,
    DragModel,
    Engine,
    FairingDrop,
    FairingDropKind,
    FairingTrigger,
    OffloadMode,
    Stage,
    Startup,
    StartupKind,
    Vehicle,
    offload_load_kg,
    offload_split_kg,
)

VEHICLE_PREFIX = "vehicle."
OVERRIDE_NOTE = "override"
PlannedModel = Literal["linear_motor", "cable_winch"]
PLANNED_MODELS: tuple[str, ...] = get_args(PlannedModel)
"""Assist models the README names that are not implemented yet (one source of truth)."""
SWITCH_KEYS = ("model", "kind")
"""Discriminator keys: a dict whose value for one of these differs from the base's
replaces the base dict wholesale when merging, so no stale keys of the old choice
survive (assist ``model``; startup ``kind``)."""
KeyFamilies = tuple[tuple[str, ...], ...]
"""Alternative parameterisations of one setting: each inner tuple is a family, the keys
that together state the setting one way; a dict uses the keys of one family only."""
ASSIST_KEY_FAMILIES: KeyFamilies = (("net_accel_g",), ("exit_speed_mps",))
"""How a constant_accel assist states its push besides ``stroke_m``: by the net
acceleration or by the exit speed."""
IGNITION_KEY_FAMILIES: KeyFamilies = (
    ("t_ign_s", "reference"),
    ("at_depth_m",),
    ("at_speed_mps",),
    ("at_height_m", "height_method"),
)
"""How an ignition states when the thrust ramp starts: by time, by depth below the track
exit, by speed on the push, or by height above the exit."""
EXCLUSIVE_KEY_FAMILIES: tuple[KeyFamilies, ...] = (ASSIST_KEY_FAMILIES, IGNITION_KEY_FAMILIES)
"""The exclusive key families of run dicts, declared here once. Every variant, sweep
point, sensitivity case and bound inherits its parent's keys by a per-key merge, so
without this rule a variant that states a setting another way (``exit_speed_mps`` over
an inherited ``net_accel_g``, ``at_depth_m`` over an inherited ``t_ign_s`` and
``reference``) would carry both parameterisations.

Rule (merge_run_dicts for variants; apply_overrides for the run paths of sweep axes,
sensitivity cases and bounds): an override that sets a key of one family removes, from
the dict it is merged into, the base's keys of the other families of the same group.
An override that sets only keys of the family the base already uses merges as before
(per key). Keys of two families of one group given together at one dict level raise
ExclusiveKeysError: the merge cannot say which one is meant. A key counts as given when
it is present in the override, whatever its value, an explicit null included (pydantic's
``model_fields_set``, on which the "exactly one" validators are built, counts it the
same way): ``{at_depth_m: null}`` displaces an inherited ``t_ign_s`` and ``reference``,
so a null is not a way to unset a key.

Scope: by key name within one dict level of a run dict, as SWITCH_KEYS is. The names
are not tied to a path (the ignition dict of any stage, the assist dict); no other
run-level model may use them as field names and no key belongs to two families (a test
checks both). Vehicle dicts are not subject to the rule. In the dotted-path form the
rule acts on the key the path names: a dict given as a path's value replaces whatever
was at that path whole (apply_overrides), so nothing inside it is inherited and there
is nothing left for the rule to displace.

The assist group's fields exist since SP1 step 2: ``ConstantAccelConfig`` takes
``net_accel_g`` or ``exit_speed_mps`` and its validator enforces "exactly one family"
on the resolved model. The ignition group's fields exist since SP1 step 3:
``IgnitionConfig`` takes ``t_ign_s``/``reference``, ``at_depth_m``, ``at_speed_mps`` or
``at_height_m`` with ``height_method``, and its validator enforces "at most one family
given" (none given is the time family at its defaults)."""
RampStartTrigger = Literal["time", "depth", "speed", "height_closed_form", "height_event"]
"""How the stage-1 thrust ramp start is stated, the vocabulary of ``IgnitionConfig.ramp_start``,
of ``phases.prelude.IgnitionSpec.trigger_kind`` and of the planar metric
``ramp_start_trigger``: by time (``t_ign_s`` with ``reference``), by depth below the
track exit, by speed on the push, by height above the track exit through the closed
form of a drag-free coast, or by height above the track exit reached by an altitude
event in flight (SP1 step 4; docs/physics.md, "Silo model")."""
RAMP_START_TIME: RampStartTrigger = "time"
RAMP_START_DEPTH: RampStartTrigger = "depth"
RAMP_START_SPEED: RampStartTrigger = "speed"
RAMP_START_HEIGHT_CLOSED_FORM: RampStartTrigger = "height_closed_form"
RAMP_START_HEIGHT_EVENT: RampStartTrigger = "height_event"
RAMP_START_TRIGGERS: tuple[str, ...] = get_args(RampStartTrigger)
HeightMethod = Literal["event", "closed_form"]
"""How ``at_height_m`` is reached: ``closed_form`` (converted to a time after release
before the run) or ``event`` (an altitude event in flight: stage 1 lights at the root
of altitude = track exit + h on the coast after release, SP1 step 4)."""
HEIGHT_METHOD_EVENT: HeightMethod = "event"
HEIGHT_METHOD_CLOSED_FORM: HeightMethod = "closed_form"
LATITUDE_RANGE_DEG = (-90.0, 90.0)
AZIMUTH_RANGE_DEG = (0.0, 360.0)
VERTICAL_TRACK_DEG = 90.0

DynamicsKind = Literal["vertical_1d", "planar_2d"]
VERTICAL_1D: DynamicsKind = "vertical_1d"
PLANAR_2D: DynamicsKind = "planar_2d"
ExperimentLabel = Literal["calibration", "guidance_study"]
CALIBRATION_LABEL: ExperimentLabel = "calibration"
GUIDANCE_STUDY_LABEL: ExperimentLabel = "guidance_study"
PLANAR_KEY = "planar"
"""Run-dict key that holds the injected planar shared blocks (``RunConfig.planar``)."""
PLANAR_SHARED_KEYS = ("guidance", "search", "target_orbit", "checks")
"""Experiment-level blocks injected under ``RunConfig.planar``, in this order."""
RUN_SHARED_KEYS = ("dynamics", "site")
"""Experiment-level blocks injected as run keys of the same name, in this order."""
SHARED_KEYS = (*RUN_SHARED_KEYS, *PLANAR_SHARED_KEYS)
"""Every experiment-level shared block (identical for every run of an experiment)."""
SHARED_PATH_ROOTS = frozenset({*SHARED_KEYS, PLANAR_KEY})
"""First segments of the run paths a variant, sweep, sensitivity case or bound may not
address (the shared blocks, under either their experiment or their run-dict name)."""
PAIRED_SWEEP_ROOT = "guidance"
"""The one shared block a paired sweep of a guidance_study may vary."""
VEHICLE_ROOT = "vehicle"
"""First segment of a vehicle path: on planar_2d a sweep may vary it only when paired."""
PAIRED_SWEEP_ROOTS = frozenset({PAIRED_SWEEP_ROOT, VEHICLE_ROOT})
"""The path roots a paired sweep may vary: both are re-applied to the paired baseline."""
INSERTION_END = "insertion"
IMPACT_END = "impact"
PLANAR_ENDS = ("stage1_burnout", "insertion", "apex", "impact")
"""Ends a planar_2d run supports in Phase 2 (all_burnout is deferred)."""
FigureOfMerit = Literal["payload", "residual", "none"]
SEARCHED_FIGURES: tuple[str, ...] = ("payload", "residual")
"""Figures of merit that run the guidance search (payload capacity, residual at P)."""
NO_SEARCH: FigureOfMerit = "none"
CheckRole = Literal["diagnostic", "blocking"]
"""Role of a screening-beat check: a blocking check's fail gives status bug_suspect and
blocks findings; a diagnostic check's is computed and reported only (docs/physics.md,
"Screening-beat rule (2-D)")."""
DIAGNOSTIC_ROLE: CheckRole = "diagnostic"
BLOCKING_ROLE: CheckRole = "blocking"
PLANAR_STAGE_COUNT = 2
"""planar_2d guidance has one law per stage: stage1 (kick, gravity turn), stage2 (LTG)."""
LTG_GUESS_RUNGS = ("warm", "physics", "steep", "shallow")
"""The LTG guess ladder, in the order solve_ltg tries it (plan section 6)."""
BRENTQ_MIN_RTOL = 4.0 * sys.float_info.epsilon
"""scipy.optimize.brentq's smallest accepted rtol (also its default), 8.88e-16."""
GRID_STEP_REL_TOL = 1e-9
"""Relative slack when checking that a grid's span is a whole number of steps."""
FLIGHT_PATH_RANGE_DEG = (-90.0, 90.0)
"""Open interval a flight-path angle (gamma* grid points, fixed gamma*) must lie in."""
PITCH_RANGE_DEG = (-90.0, 90.0)
"""Open interval an LTG pitch angle must lie in (tan p finite, no sign flip past vertical)."""
KICK_RANGE_DEG = (0.0, 90.0)
"""Open interval the kick-angle bracket must lie in (0: no turn; 90: horizontal)."""
INTEGRATOR_KEY = "integrator"
"""Run-dict key of the integrator block; on planar_2d no per-run path may address it."""
ROTATION_REFUSAL = (
    "include_rotation: true is a Phase 2 feature: it needs dynamics: planar_2d "
    "(vertical_1d keeps omega_p = 0)"
)
"""Refusal text for Earth rotation on a vertical_1d site (SiteConfig and RunConfig)."""


class _Model(BaseModel):
    """Base for every config model: unknown keys are errors and instances are frozen."""

    model_config = ConfigDict(extra="forbid", frozen=True)


def _is_number(x: object) -> bool:
    """True for int or float but not bool."""
    return isinstance(x, int | float) and not isinstance(x, bool)


# --------------------------------------------------------------------------- vehicle file


def _check_provenance(source: str | None, assumed: bool) -> None:
    """Raise ValueError unless exactly one of a non-blank source or assumed: true is given."""
    if source is not None and not source.strip():
        raise ValueError("source must not be blank")
    if (source is not None) == assumed:
        raise ValueError("give exactly one of source or assumed: true")


class Quantity(_Model):
    """A sourced number from a vehicle file: exactly one of ``source`` or ``assumed``.

    The value is a finite number (NaN and inf are rejected) and a source is non-blank."""

    value: float = Field(allow_inf_nan=False)
    source: str | None = None
    assumed: bool = False
    note: str | None = None

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
        _check_provenance(self.source, self.assumed)  # the rule QuantityList shares
        return self


FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]


class QuantityList(_Model):
    """Sourced list data from a vehicle file: one provenance for a whole table.

    Base for vehicle-file tables whose numbers come as lists (the C_D(M) table): exactly
    one of ``source`` or ``assumed: true`` (plus an optional ``note``), checked by the
    same ``_check_provenance`` as Quantity, covers every number in the table.
    Subclasses declare the list fields; every entry of every list field must be a finite
    number (a bool, a string or NaN raises instead of being coerced). A bare list where a
    QuantityList is expected raises.
    """

    source: str | None = None
    assumed: bool = False
    note: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _numbers_only(cls, data: Any) -> Any:
        if isinstance(data, QuantityList):
            return data
        if not isinstance(data, dict):
            raise ValueError(
                "bare value; vehicle-file tables need their lists plus a source or assumed: true"
            )
        for key in cls.model_fields.keys() - {"source", "assumed", "note"}:
            values = data.get(key)
            if isinstance(values, list) and not all(_is_number(v) for v in values):
                raise ValueError(f"{key}: every entry must be a number")
        return data

    @model_validator(mode="after")
    def _one_provenance(self) -> QuantityList:
        _check_provenance(self.source, self.assumed)
        return self


class CdMachConfig(QuantityList):
    """The C_D(M) table of a vehicle file: knot Mach numbers and C_D values (both
    dimensionless), equal length, Mach strictly increasing from >= 0, C_D >= 0."""

    mach: list[FiniteFloat]
    cd: list[FiniteFloat]

    @model_validator(mode="after")
    def _valid_table(self) -> CdMachConfig:
        self.to_table()  # CdTable raises ValueError with the rule that failed
        return self

    def to_table(self) -> CdTable:
        """The frozen PCHIP CdTable through the knots."""
        return CdTable.pchip(self.mach, self.cd)


class AeroConfig(_Model):
    """Vehicle aerodynamics: reference area [m^2], C_D(M) table, interpolation and the
    cd_scale knob (a required Quantity, 1.0 nominal, so that a ``vehicle.aero.cd_scale``
    sensitivity case always finds its nominal value). SI already; nothing is converted."""

    reference_area_m2: Quantity
    cd_scale: Quantity
    interpolation: Literal["pchip"] = "pchip"
    cd_mach: CdMachConfig

    def to_drag_model(self) -> DragModel:
        """The frozen DragModel (DragModel checks A_ref > 0 and cd_scale > 0)."""
        return DragModel(
            table=self.cd_mach.to_table(),
            reference_area_m2=self.reference_area_m2.value,
            cd_scale=self.cd_scale.value,
        )


class FairingDropConfig(_Model):
    """Vehicle-file fairing rule as a block: ``trigger`` (staging, never or
    free_molecular_heating) and, for the heating trigger only, ``limit_W_m2`` [W/m^2] as
    a Quantity. The plain strings ``staging`` and ``never`` remain accepted in place of
    the block."""

    trigger: FairingTrigger
    limit_W_m2: Quantity | None = None

    @model_validator(mode="after")
    def _limit_matches_trigger(self) -> FairingDropConfig:
        self.to_fairing_drop()  # FairingDrop raises ValueError with the rule that failed
        return self

    def to_fairing_drop(self) -> FairingDrop:
        """The frozen FairingDrop."""
        limit = None if self.limit_W_m2 is None else self.limit_W_m2.value
        return FairingDrop(trigger=self.trigger, limit_W_m2=limit)


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
    """A vehicle file: stages in firing order, fairing and payload, fairing drop rule,
    screening Isp and (optional) aerodynamics.

    fairing_drop is the string ``staging`` or ``never`` (Phase 1 form) or a
    FairingDropConfig block (needed for the heating trigger). Validation builds the
    Vehicle dataclass once, so the physical checks that live there (thrust and Isp > 0,
    dry mass >= 0, propellant > 0, coast and startup durations >= 0, payload and fairing
    >= 0, screening Isp > 0, A_ref and cd_scale > 0) fail at load with the vehicle
    named."""

    name: str
    description: str | None = None
    stages: list[StageConfig]
    fairing_mass_t: Quantity
    payload_mass_t: Quantity
    fairing_drop: FairingDropKind | FairingDropConfig = "staging"
    screening: ScreeningConfig | None = None
    aero: AeroConfig | None = None

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
        fairing = self.fairing_drop
        return Vehicle(
            stages=tuple(s.to_stage() for s in self.stages),
            fairing_mass_kg=units.t_to_kg(self.fairing_mass_t.value),
            payload_mass_kg=units.t_to_kg(self.payload_mass_t.value),
            fairing_drop=fairing if isinstance(fairing, str) else fairing.to_fairing_drop(),
            screening_isp_s=isps,
            aero=None if self.aero is None else self.aero.to_drag_model(),
        )


# ------------------------------------------------------------------------ experiment file


class SiteConfig(_Model):
    """Launch site of a vertical_1d run: latitude [-90, 90] and azimuth [0, 360] in
    degrees (clockwise from north). Earth rotation is refused here (the 1-D model keeps
    omega_p = 0); a planar_2d run's site is a PlanarSiteConfig, which allows it."""

    latitude_deg: float = Field(default=28.5, ge=LATITUDE_RANGE_DEG[0], le=LATITUDE_RANGE_DEG[1])
    azimuth_deg: float = Field(default=90.0, ge=AZIMUTH_RANGE_DEG[0], le=AZIMUTH_RANGE_DEG[1])
    include_rotation: bool = False

    @field_validator("include_rotation")
    @classmethod
    def _no_rotation_yet(cls, v: bool) -> bool:
        if v:
            raise ValueError(ROTATION_REFUSAL)
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


class PlanarSiteConfig(SiteConfig):
    """Launch site of a planar_2d run: the SiteConfig fields, every one explicit (no
    defaults, so rotation is always a stated choice), and Earth rotation allowed.

    omega_p_rads is omega_E cos(lat) sin(az) [rad/s] with rotation on, 0 with it off:
    the orbit-normal component of Earth rotation. At azimuth 90 deg the site velocity
    omega_p R_E and the inclination are exact, but the air's out-of-plane velocity
    omega_E sin(lat) r sin(theta) is neglected, so the planar model is exact only for an
    equatorial east launch (an approximation otherwise)."""

    latitude_deg: float = Field(ge=LATITUDE_RANGE_DEG[0], le=LATITUDE_RANGE_DEG[1])
    azimuth_deg: float = Field(ge=AZIMUTH_RANGE_DEG[0], le=AZIMUTH_RANGE_DEG[1])
    include_rotation: bool

    @field_validator("include_rotation")
    @classmethod
    def _no_rotation_yet(cls, v: bool) -> bool:
        return v  # overrides SiteConfig's refusal: rotation is a planar_2d feature


def planar_site(site: dict[str, Any]) -> PlanarSiteConfig:
    """Validate a raw site dict as a planar_2d site; raises ValueError naming the rule
    (every field explicit) and pydantic's error."""
    try:
        return PlanarSiteConfig.model_validate(site)
    except ValidationError as exc:
        raise ValueError(
            "a planar_2d site needs latitude_deg, azimuth_deg and include_rotation, each "
            f"given explicitly: {exc}"
        ) from exc


class TrackConfig(_Model):
    """Straight track: angle above horizontal [deg] (90 only until Phase 3) and the
    altitude of its exit [m] relative to the pad datum z = 0."""

    angle_deg: float = VERTICAL_TRACK_DEG
    exit_altitude_m: float = 0.0

    @field_validator("angle_deg")
    @classmethod
    def _vertical_only(cls, v: float) -> float:
        if v != VERTICAL_TRACK_DEG:
            raise ValueError(
                "track angle_deg other than 90 is a Phase 3 feature (Phase 2 releases "
                "from vertical tracks only)"
            )
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

    The push over ``stroke_m`` (the track length L [m]) is stated in exactly one of two
    ways (ASSIST_KEY_FAMILIES; docs/physics.md, "Silo model"): ``net_accel_g``, the net
    acceleration a in units of g0, or ``exit_speed_mps``, the speed v [m/s] along the
    track at its exit, from which the acceleration is derived, a = v^2 / (2 L) (a push
    from rest at constant acceleration; push time 2 L / v). Both must be > 0 and the
    exit speed finite, and so must the derived acceleration. A key counts as given when
    it is present, an explicit null included (pydantic's ``model_fields_set``; the merge
    rule of EXCLUSIVE_KEY_FAMILIES counts it the same way): both keys present is refused
    whatever their values, neither present is refused, and the one key present must
    hold a number, so a null is never a way to leave a key out. The unused key is
    therefore left out of ``model_dump`` (``_dump_one_push_key``): a dump states the
    push by its one key, as the input did, and validates again to an equal model.

    The ``_g`` and ``_t`` fields hold the YAML-side units and exist only for the file
    boundary and reporting; dynamics and the assist model must use the SI properties
    net_accel_mps2, carriage_mass_kg and brake_decel_mps2."""

    model: Literal["constant_accel"]
    net_accel_g: float | None = Field(default=None, gt=0.0)
    exit_speed_mps: float | None = Field(default=None, gt=0.0, allow_inf_nan=False)
    stroke_m: float = Field(gt=0.0)
    carriage_mass_t: float = Field(default=0.0, ge=0.0)
    brake_decel_g: float = Field(gt=0.0)
    drive_efficiency: float = Field(default=1.0, gt=0.0, le=1.0)
    exhaust_impingement_fraction: float = Field(default=0.0, ge=0.0, le=1.0)
    shaft: Literal["vented"] = "vented"
    allow_negative_drive_force: bool = False
    track: TrackConfig = TrackConfig()

    @model_validator(mode="after")
    def _one_push_parameterisation(self) -> ConstantAccelConfig:
        """Exactly one push key given (present, a null counting as given), holding a
        number; on the exit-speed path the derived a = v^2 / (2 L) [m/s^2] finite and
        > 0 (an overflow or underflow of absurd inputs, or an infinite stroke)."""
        keys = [key for family in ASSIST_KEY_FAMILIES for key in family]
        given = [key for key in keys if key in self.model_fields_set]
        if len(given) != 1:
            found = ", ".join(given) if given else "neither"
            raise ValueError(
                f"constant_accel needs exactly one of {' or '.join(keys)} beside stroke_m "
                f"(given: {found}; a key given as null counts as given)"
            )
        if getattr(self, given[0]) is None:
            raise ValueError(
                f"constant_accel {given[0]} is null: the key that states the push must "
                "hold a number (a null does not unset a key)"
            )
        if self.exit_speed_mps is not None:
            accel = self.net_accel_mps2
            if not (math.isfinite(accel) and accel > 0.0):
                raise ValueError(
                    f"constant_accel: exit_speed_mps {self.exit_speed_mps:g} over stroke_m "
                    f"{self.stroke_m:g} gives the net acceleration v^2 / (2 L) = {accel:g} "
                    "m/s^2, which must be finite and > 0"
                )
        return self

    @model_serializer(mode="wrap")
    def _dump_one_push_key(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        """The default dump without the push key that is not used (the one holding
        None; the validator guarantees exactly one holds a number), so ``model_dump``
        states the push as the input did and ``model_validate`` of it gives an equal
        model, which a null key would make it refuse. A dump of a push stated by
        ``net_accel_g`` is the dict it was before ``exit_speed_mps`` existed."""
        out: dict[str, Any] = handler(self)
        for key in (key for family in ASSIST_KEY_FAMILIES for key in family):
            if key in out and getattr(self, key) is None:
                del out[key]
        return out

    @property
    def net_accel_mps2(self) -> float:
        """Prescribed net acceleration a [m/s^2]: ``net_accel_g`` in SI when the push is
        stated by its acceleration, else v^2 / (2 L) from ``exit_speed_mps`` v [m/s] and
        ``stroke_m`` L [m] (constant acceleration from rest along the track)."""
        if self.exit_speed_mps is not None:
            return self.exit_speed_mps * self.exit_speed_mps / (2.0 * self.stroke_m)
        if self.net_accel_g is None:  # unreachable on a validated instance
            raise ValueError("constant_accel has neither net_accel_g nor exit_speed_mps")
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
    """When a stage lights (the start of its thrust ramp), stated in one of four ways
    (IGNITION_KEY_FAMILIES; docs/physics.md, "Silo model"):

    - by time: ``t_ign_s`` [s] relative to ``reference``, ``release`` (stage 1: track
      exit or hold-down release; later stages: end of their staging coast) or
      ``push_start`` (first stage only, and only on a run with an assist model: a pad
      has no push). The defaults (0 s after release) apply when no family is given;
    - by ``at_depth_m`` [m] (>= 0): the depth d below the track exit at which the
      ramp starts on the push;
    - by ``at_speed_mps`` [m/s] (>= 0): the speed along the track at which it starts;
    - by ``at_height_m`` [m] (> 0) with ``height_method``: the height above the track
      exit after release, ``closed_form`` (the drag-free constant-g_eff coast) or
      ``event`` (an altitude event in flight).

    The last three are for the first stage of a run with a ``constant_accel`` assist
    only (RunConfig and ``resolve_run`` refuse a pad and a later stage); depth, speed
    and the closed-form height are converted to a (t_ign_s, reference) pair before the
    run (``phases.prelude.resolve_ignition``), and the event height is found in flight
    by the planners. At most one family is given: a key counts as
    given when it is present, an explicit null included (``model_fields_set``; the merge
    rule of EXCLUSIVE_KEY_FAMILIES counts it the same way), so the defaults of t_ign_s
    and reference never count, and the keys of the other families must hold a value
    (a null never unsets a key). ``at_height_m`` and ``height_method`` come together.
    ``model_dump`` leaves out the keys of the families not in use
    (``_dump_one_ramp_start``), so a dump states the ramp start as the input did and
    validates again to an equal model; a time-family dump is the dict it was before
    the other families existed."""

    t_ign_s: float = 0.0
    reference: Literal["release", "push_start"] = "release"
    at_depth_m: float | None = Field(default=None, ge=0.0, allow_inf_nan=False)
    at_speed_mps: float | None = Field(default=None, ge=0.0, allow_inf_nan=False)
    at_height_m: float | None = Field(default=None, gt=0.0, allow_inf_nan=False)
    height_method: HeightMethod | None = None
    startup: StartupOverride | None = None
    fails: bool = False

    @model_validator(mode="after")
    def _one_ramp_start(self) -> IgnitionConfig:
        """At most one family of IGNITION_KEY_FAMILIES given (present, a null counting
        as given); the keys of a non-time family hold a value; ``at_height_m`` and
        ``height_method`` together."""
        given_keys = self.model_fields_set
        named = [f for f in IGNITION_KEY_FAMILIES if any(k in given_keys for k in f)]
        if len(named) > 1:
            found = ", ".join(k for f in named for k in f if k in given_keys)
            options = " or ".join("{" + ", ".join(f) + "}" for f in IGNITION_KEY_FAMILIES)
            raise ValueError(
                f"ignition states the ramp start in more than one way (given: {found}; a "
                f"key given as null counts as given); use one of {options}"
            )
        for key in (k for f in IGNITION_KEY_FAMILIES[1:] for k in f):
            if key in given_keys and getattr(self, key) is None:
                raise ValueError(
                    f"ignition {key} is null: a key that states the ramp start must hold "
                    "a value (a null does not unset a key)"
                )
        if ("at_height_m" in given_keys) != ("height_method" in given_keys):
            raise ValueError(
                "ignition at_height_m and height_method come together: the height above "
                "the track exit and how it is reached (closed_form or event)"
            )
        return self

    @model_serializer(mode="wrap")
    def _dump_one_ramp_start(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        """The default dump without the keys of the ramp-start families not in use
        (``ramp_start_keys``), so ``model_dump`` states the ramp start by its one family
        and ``model_validate`` of it gives an equal model (a dumped null or a dumped
        t_ign_s beside at_depth_m would be refused). A time-family dump keeps t_ign_s
        and reference, as before the other families existed."""
        out: dict[str, Any] = handler(self)
        used = self.ramp_start_keys
        for key in (k for f in IGNITION_KEY_FAMILIES for k in f if k not in used):
            out.pop(key, None)
        return out

    @property
    def ramp_start_keys(self) -> tuple[str, ...]:
        """The family of IGNITION_KEY_FAMILIES that states the ramp start: the first
        family whose non-time keys hold a value, else the time family (t_ign_s,
        reference), given or at its defaults."""
        for family in IGNITION_KEY_FAMILIES[1:]:
            if any(getattr(self, k) is not None for k in family):
                return family
        return IGNITION_KEY_FAMILIES[0]

    @property
    def ramp_start(self) -> tuple[RampStartTrigger, float | None]:
        """(trigger, requested value) of the ramp start: (RAMP_START_TIME, None) for the
        time family, (RAMP_START_DEPTH, at_depth_m [m]), (RAMP_START_SPEED, at_speed_mps
        [m/s]), or for a height (RAMP_START_HEIGHT_CLOSED_FORM, at_height_m [m]) with
        ``height_method: closed_form`` and (RAMP_START_HEIGHT_EVENT, at_height_m [m])
        with ``height_method: event``."""
        if self.at_depth_m is not None:
            return RAMP_START_DEPTH, self.at_depth_m
        if self.at_speed_mps is not None:
            return RAMP_START_SPEED, self.at_speed_mps
        if self.at_height_m is not None:
            if self.height_method == HEIGHT_METHOD_EVENT:
                return RAMP_START_HEIGHT_EVENT, self.at_height_m
            return RAMP_START_HEIGHT_CLOSED_FORM, self.at_height_m
        return RAMP_START_TIME, None

    def resolved_startup(self, base: Startup) -> Startup:
        """The stage's Startup after applying this ignition's override, if any."""
        return base if self.startup is None else self.startup.resolve(base)


IntegratorMethod = Literal["DOP853", "RK45"]
"""solve_ivp methods CLAUDE.md allows."""


class IntegratorConfig(_Model):
    """solve_ivp settings and the output sampling interval: method (DOP853 or RK45),
    rtol, first step [s], max_step caps (steps per ramp, per lag tau, per push), the
    planar flight-phase step cap planar_max_step_s [s] (finite, > 0; every planar
    flight phase integrates with max_step = min(its ramp or lag cap, this); the HOLD,
    the track push and every vertical_1d phase ignore it, so a value set on a
    vertical_1d run is accepted and has no effect; omitted, it takes the 2 s default,
    and the shipped planar experiments state it explicitly (a test, not this model,
    enforces that): user decision of 2026-09-30),
    the open-phase guard t_max [s] and the time-series interval sample_dt [s]. On a
    planar_2d run rtol must equal ``search.final_rtol`` (RunConfig checks it), and no
    integrator setting, planar_max_step_s included, may differ between the runs of an
    experiment (ExperimentConfig refuses it)."""

    method: IntegratorMethod = "DOP853"
    rtol: float = Field(default=1e-10, gt=0.0)
    first_step_s: float = Field(default=1e-3, gt=0.0)
    ramp_steps: int = Field(default=10, ge=1)
    lag_steps_per_tau: int = Field(default=4, ge=1)
    push_steps: int = Field(default=50, ge=1)
    planar_max_step_s: float = Field(default=2.0, gt=0.0, allow_inf_nan=False)
    t_max_s: float = Field(default=3600.0, gt=0.0)
    sample_dt_s: float = Field(default=0.05, gt=0.0)


# ------------------------------------------------ planar shared blocks (experiment level)


def _ordered_pair(v: tuple[float, float], what: str) -> tuple[float, float]:
    """Raise ValueError unless a (low, high) pair has low < high."""
    if not v[0] < v[1]:
        raise ValueError(f"{what} must be [low, high] with low < high, got {list(v)}")
    return v


def _check_pitch(v: float, what: str) -> float:
    """Raise ValueError unless an LTG pitch angle [deg] lies inside PITCH_RANGE_DEG."""
    lo, hi = PITCH_RANGE_DEG
    if not lo < v < hi:
        raise ValueError(f"{what} must lie inside ({lo:g}, {hi:g}) deg (tan p finite), got {v}")
    return v


class KickConfig(_Model):
    """Stage-1 pitch kick (hold-to-alignment): trigger speed v_kick [m/s] (|v_rel| with
    v_r > 0; a vehicle already faster at its first lit instant kicks at ignition), the
    kick law, the kick's time limit max_duration [s] (kick_timeout beyond it) and the
    deadline [s] after stage-1 ignition by which v_kick must be reached with v_r > 0
    (no_kick otherwise). Both limits are guidance failures, never warnings."""

    v_kick_mps: float = Field(default=50.0, gt=0.0)
    mode: Literal["hold_to_alignment"] = "hold_to_alignment"
    max_duration_s: float = Field(default=60.0, gt=0.0)
    deadline_s: float = Field(default=60.0, gt=0.0)


class Stage2GuidanceConfig(_Model):
    """Stage-2 steering: linear-tangent law tan p = a - b tau in the local-horizontal
    frame (tau from stage-2 ignition), cut off on the orbital energy E = E*."""

    law: Literal["linear_tangent"] = "linear_tangent"
    frame: Literal["local_horizontal"] = "local_horizontal"
    cutoff: Literal["energy"] = "energy"


class GuidanceConfig(_Model):
    """The shared guidance parametrisation: stage-1 kick then gravity turn along v_rel,
    stage-2 linear-tangent steering. Free parameters (gamma*, delta, a, b) are solved or
    sweep-optimized per run, never set here (except the fixed guidance of
    ``search.figure_of_merit: none``)."""

    kick: KickConfig = KickConfig()
    stage1: Literal["gravity_turn"] = "gravity_turn"
    stage2: Stage2GuidanceConfig = Stage2GuidanceConfig()


class TargetOrbitConfig(_Model):
    """Target orbit: circular (the only kind in Phase 2) at altitude_km [km] above the
    R_E sphere (geometric, spherical Earth)."""

    kind: Literal["circular"] = "circular"
    altitude_km: float = Field(gt=0.0)

    @property
    def altitude_m(self) -> float:
        """Target altitude above the R_E sphere [m]."""
        return units.km_to_m(self.altitude_km)

    @property
    def radius_m(self) -> float:
        """Target radius r_t = R_E + altitude [m] (ECI, spherical Earth)."""
        return R_EARTH_M + self.altitude_m


class PenaltyConfig(_Model):
    """Finite objective for an infeasible gamma* grid point [kg]: -(base_kg + per_deg_kg x
    the distance in degrees to the nearest feasible grid point). Finite and monotone, so
    a bounded Brent refine never sees -inf (which would warn, and warnings fail tests)."""

    base_kg: float = Field(default=1.0e6, gt=0.0)
    per_deg_kg: float = Field(default=1.0e4, ge=0.0)

    @property
    def per_rad_kg(self) -> float:
        """The distance slope per radian [kg/rad]."""
        return self.per_deg_kg * units.rad_to_deg(1.0)


class LtgConfig(_Model):
    """LTG shooting settings (``solve_ltg``, plan section 6).

    Acceptance: |r_c - r_t| < accept_r_m [m] and |v_r,c| < accept_vr_mps [m/s].
    Residual scaling: F = ((r_c - r_t)/r_scale_m, v_r,c/vr_scale_mps). Damped Newton on
    x = (a, 100 b): forward-difference steps fd_step_search / fd_step_final (in x units),
    at most max_iters iterations and max_halvings step halvings. Guess ladder (warm,
    physics, steep, shallow), at most grid_max_rungs rungs per grid point: physics
    p0 = gamma_in + p0_offset_deg, p_f = pf_deg; steep p0 = steep_p0_deg; shallow x =
    shallow_guess. Direct root: b > 0 and pitch inside pitch_bounds_deg over the burn.
    no_cutoff when tau exceeds tau_max_factor x tau_b; the search mass floor is
    mass_floor_factor x (m_d2 + P). Every angle (p0_offset_deg, pf_deg, steep_p0_deg and
    both pitch bounds) lies inside the open interval (-90, 90) deg (PITCH_RANGE_DEG),
    where tan p is finite. Degrees here, radians through the ``_rad`` properties."""

    accept_r_m: float = Field(default=1.0, gt=0.0)
    accept_vr_mps: float = Field(default=1.0e-3, gt=0.0)
    r_scale_m: float = Field(default=1.0e4, gt=0.0)
    vr_scale_mps: float = Field(default=100.0, gt=0.0)
    fd_step_search: float = Field(default=1.0e-4, gt=0.0)
    fd_step_final: float = Field(default=1.0e-5, gt=0.0)
    max_iters: int = Field(default=25, ge=1)
    max_halvings: int = Field(default=6, ge=0)
    grid_max_rungs: int = Field(default=2, ge=1, le=len(LTG_GUESS_RUNGS))
    p0_offset_deg: float = 5.0
    pf_deg: float = -1.0
    steep_p0_deg: float = 35.0
    shallow_guess: tuple[float, float] = (0.3, 0.3)
    pitch_bounds_deg: tuple[float, float] = (-45.0, 75.0)
    tau_max_factor: float = Field(default=2.0, gt=1.0)
    mass_floor_factor: float = Field(default=0.5, gt=0.0, lt=1.0)

    @field_validator("pitch_bounds_deg")
    @classmethod
    def _bounds(cls, v: tuple[float, float]) -> tuple[float, float]:
        _ordered_pair(v, "ltg.pitch_bounds_deg")
        for x in v:
            _check_pitch(x, "ltg.pitch_bounds_deg")
        return v

    @field_validator("p0_offset_deg", "pf_deg", "steep_p0_deg")
    @classmethod
    def _pitch_angles(cls, v: float, info: ValidationInfo) -> float:
        return _check_pitch(v, f"ltg.{info.field_name}")

    @property
    def p0_offset_rad(self) -> float:
        """Physics-guess initial pitch offset above gamma_in [rad]."""
        return units.deg_to_rad(self.p0_offset_deg)

    @property
    def pf_rad(self) -> float:
        """Physics-guess final pitch [rad]."""
        return units.deg_to_rad(self.pf_deg)

    @property
    def steep_p0_rad(self) -> float:
        """Steep-guess initial pitch [rad]."""
        return units.deg_to_rad(self.steep_p0_deg)

    @property
    def pitch_bounds_rad(self) -> tuple[float, float]:
        """Direct-root pitch window (low, high) [rad]."""
        return (
            units.deg_to_rad(self.pitch_bounds_deg[0]),
            units.deg_to_rad(self.pitch_bounds_deg[1]),
        )


class SearchConfig(_Model):
    """The shared search budget (plan section 6 and amendments 7, 13): identical for
    every run of an experiment; ``budget_id`` hashes it.

    figure_of_merit: payload (P* by the gamma* sweep), residual (m_res at the vehicle
    payload) or none (no search: fixed_gamma_star_deg, fixed_ltg_a and fixed_ltg_b_per_s
    [1/s] are then required, and allowed only then). gamma* grid [start, stop, step] in
    degrees, refined by bounded Brent over +/- gamma_refine_halfwidth_deg to
    gamma_xatol_deg in at most gamma_refine_maxiter evaluations; a delta root counts only
    when |gamma_MECO - gamma*| <= gamma_root_tol_deg (false-root guard). Inner delta
    solve: bracket delta_bracket_deg, stepping delta_step_deg (doubling), brentq to
    delta_xtol_rad [rad]. Payload: bracket P_hint +/- payload_half_bracket_t [t],
    expanded x2 at most payload_max_expand times, backed off at most payload_backoff_max
    times, brentq to payload_xtol_kg [kg] with rtol brentq_rtol (>= 4 eps). Final
    verification: bracket final_bracket_kg [kg] (start, maximum), brentq to
    final_payload_xtol_kg [kg]. Integration: search_rtol with atol x search_atol_scale,
    final_rtol (also the run's integrator.rtol) for the reported numbers; search_atol_scale
    >= 1, so a search is never integrated more tightly than the final run. Penalty and
    LTG settings in their blocks."""

    figure_of_merit: FigureOfMerit = "payload"
    gamma_grid_deg: tuple[float, float, float] = (8.0, 36.0, 2.0)
    gamma_refine_halfwidth_deg: float = Field(default=4.0, gt=0.0)
    gamma_xatol_deg: float = Field(default=0.01, gt=0.0)
    gamma_refine_maxiter: int = Field(default=30, ge=1)
    gamma_root_tol_deg: float = Field(default=0.01, gt=0.0)
    delta_bracket_deg: tuple[float, float] = (0.1, 45.0)
    delta_step_deg: float = Field(default=0.25, gt=0.0)
    delta_xtol_rad: float = Field(default=1.0e-10, gt=0.0)
    payload_half_bracket_t: float = Field(default=2.0, gt=0.0)
    payload_max_expand: int = Field(default=6, ge=0)
    payload_backoff_max: int = Field(default=4, ge=0)
    payload_xtol_kg: float = Field(default=0.5, gt=0.0)
    brentq_rtol: float = Field(default=BRENTQ_MIN_RTOL, ge=BRENTQ_MIN_RTOL)
    final_payload_xtol_kg: float = Field(default=0.05, gt=0.0)
    final_bracket_kg: tuple[float, float] = (20.0, 1000.0)
    search_rtol: float = Field(default=1.0e-8, gt=0.0)
    search_atol_scale: float = Field(default=10.0, ge=1.0)
    final_rtol: float = Field(default=1.0e-10, gt=0.0)
    penalty: PenaltyConfig = PenaltyConfig()
    ltg: LtgConfig = LtgConfig()
    fixed_gamma_star_deg: float | None = None
    fixed_ltg_a: float | None = None
    fixed_ltg_b_per_s: float | None = None

    @field_validator("gamma_grid_deg")
    @classmethod
    def _grid(cls, v: tuple[float, float, float]) -> tuple[float, float, float]:
        start, stop, step = v
        if not (start < stop and step > 0.0):
            raise ValueError(
                "gamma_grid_deg must be [start, stop, step] with start < stop and step > 0, "
                f"got {list(v)}"
            )
        n = round((stop - start) / step)
        if not math.isclose(n * step, stop - start, rel_tol=GRID_STEP_REL_TOL):
            raise ValueError(
                f"gamma_grid_deg: stop - start must be a whole number of steps, got {list(v)}"
            )
        lo, hi = FLIGHT_PATH_RANGE_DEG
        if not (lo < start and stop < hi):
            raise ValueError(
                f"gamma_grid_deg must lie inside ({lo:g}, {hi:g}) deg (a flight-path angle), "
                f"got {list(v)}"
            )
        return v

    @field_validator("delta_bracket_deg")
    @classmethod
    def _delta_bracket(cls, v: tuple[float, float]) -> tuple[float, float]:
        lo, hi = KICK_RANGE_DEG
        if v[0] <= lo:
            raise ValueError("delta_bracket_deg must start above 0 (a zero kick never turns)")
        if v[1] >= hi:
            raise ValueError(
                f"delta_bracket_deg must end below {hi:g} deg (a kick past horizontal dives)"
            )
        return _ordered_pair(v, "delta_bracket_deg")

    @field_validator("final_bracket_kg")
    @classmethod
    def _final_bracket(cls, v: tuple[float, float]) -> tuple[float, float]:
        if v[0] <= 0.0:
            raise ValueError("final_bracket_kg must start above 0")
        return _ordered_pair(v, "final_bracket_kg")

    @model_validator(mode="after")
    def _budget_rules(self) -> SearchConfig:
        if self.final_rtol > self.search_rtol:
            raise ValueError("search.final_rtol must not be looser than search.search_rtol")
        if self.final_payload_xtol_kg > self.payload_xtol_kg:
            raise ValueError("search.final_payload_xtol_kg must not exceed payload_xtol_kg")
        fixed = (self.fixed_gamma_star_deg, self.fixed_ltg_a, self.fixed_ltg_b_per_s)
        given = [x is not None for x in fixed]
        if self.figure_of_merit == NO_SEARCH and not all(given):
            raise ValueError(
                "search.figure_of_merit: none needs fixed_gamma_star_deg, fixed_ltg_a and "
                "fixed_ltg_b_per_s (the guidance a run flies without a search)"
            )
        if self.figure_of_merit != NO_SEARCH and any(given):
            raise ValueError(
                "fixed_gamma_star_deg, fixed_ltg_a and fixed_ltg_b_per_s are only for "
                "search.figure_of_merit: none (a search solves them)"
            )
        lo, hi = FLIGHT_PATH_RANGE_DEG
        g = self.fixed_gamma_star_deg
        if g is not None and not lo < g < hi:
            raise ValueError(f"fixed_gamma_star_deg must lie inside ({lo:g}, {hi:g}), got {g}")
        return self

    @property
    def gamma_grid_points_deg(self) -> tuple[float, ...]:
        """The gamma* grid points [deg], start + i step for i = 0..n (stop included)."""
        start, stop, step = self.gamma_grid_deg
        n = round((stop - start) / step)
        return tuple(start + i * step for i in range(n + 1))

    @property
    def gamma_grid_points_rad(self) -> tuple[float, ...]:
        """The gamma* grid points [rad]."""
        return tuple(units.deg_to_rad(g) for g in self.gamma_grid_points_deg)

    @property
    def gamma_refine_halfwidth_rad(self) -> float:
        """Half-width of the refine window [rad]."""
        return units.deg_to_rad(self.gamma_refine_halfwidth_deg)

    @property
    def gamma_xatol_rad(self) -> float:
        """Refine tolerance on gamma* [rad]."""
        return units.deg_to_rad(self.gamma_xatol_deg)

    @property
    def gamma_root_tol_rad(self) -> float:
        """False-root guard on |gamma_MECO(delta*) - gamma*| [rad]."""
        return units.deg_to_rad(self.gamma_root_tol_deg)

    @property
    def delta_bracket_rad(self) -> tuple[float, float]:
        """Kick-angle bracket (low, high) [rad]."""
        return (
            units.deg_to_rad(self.delta_bracket_deg[0]),
            units.deg_to_rad(self.delta_bracket_deg[1]),
        )

    @property
    def delta_step_rad(self) -> float:
        """Initial kick-angle bracketing step [rad]."""
        return units.deg_to_rad(self.delta_step_deg)

    @property
    def payload_half_bracket_kg(self) -> float:
        """Initial payload half-bracket [kg]."""
        return units.t_to_kg(self.payload_half_bracket_t)

    @property
    def fixed_gamma_star_rad(self) -> float | None:
        """The fixed gamma* of figure_of_merit none [rad], else None."""
        g = self.fixed_gamma_star_deg
        return None if g is None else units.deg_to_rad(g)

    def budget_id(self) -> str:
        """sha256 hex digest of this block's canonical JSON (sorted keys, every field,
        defaults included): equal budgets give equal ids, for ``search_budget_id``."""
        text = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ConvergenceConfig(_Model):
    """Convergence of the shipped budget (amendment 3 and the plan's section-8
    convergence row): dividing every tolerance by tighten_factor (search and final
    rtol, atol, the LTG acceptance thresholds ltg.accept_r_m and ltg.accept_vr_mps, and
    the delta, payload and gamma xtols; the LTG finite-difference steps unchanged) and
    multiplying the max_step caps by max_step_factor (the ramp, lag and push caps and
    the planar flight-phase cap planar_max_step_s) must move each figure of merit by
    less than rel_tol, with absolute
    floors for near-zero terms: loss_floor_mps [m/s] for any loss term and
    margin_floor_kg [kg-equivalent] for margins. gamma* is interpreted only to
    gamma_resolution_deg [deg]."""

    rel_tol: float = Field(default=1.0e-3, gt=0.0)
    loss_floor_mps: float = Field(default=1.0e-3, gt=0.0)
    margin_floor_kg: float = Field(default=0.5, gt=0.0)
    gamma_resolution_deg: float = Field(default=0.1, gt=0.0)
    tighten_factor: float = Field(default=10.0, gt=1.0)
    max_step_factor: float = Field(default=0.5, gt=0.0, lt=1.0)

    @property
    def gamma_resolution_rad(self) -> float:
        """gamma* reporting resolution [rad]."""
        return units.deg_to_rad(self.gamma_resolution_deg)


class ChecksConfig(_Model):
    """Bug and flag thresholds of the planar pipeline (plan sections 5 and 7, amendments
    3 and 13); a failed blocking check gives status bug_suspect or a flag, never a
    warning (M2 blocks only with m2_role blocking).

    closure_tol_mps [m/s]: rocket-equation closure. identity_tol_mps [m/s]: the 2-D
    loss-identity residual of a run. insertion_e_max: the largest eccentricity an
    inserted run may have (plan section 11). grav_ratio_bounds and
    bp_ratio_bounds: (low, high) of d J / estimate for mechanism checks M2 and M3, the
    latter only when |d J_bp| > min_term_mps [m/s]. max_drag_steer_share: M4, the
    largest share of the beyond-screening part d(J_drag + J_steer) may carry.
    anchor_margin_kg [kg]: M5 slack. search_final_flag_rel: flag |P_search - P_final| /
    P above it. maxq_scan_points per phase and maxq_xatol_s [s]: the max-Q scan and
    refine. unconstrained_kick_mps [m/s]: kicks faster than this are labelled
    unconstrained. vk_margin_kg [kg]: the v_k fairness rule (decision 5).
    gamma_sensitivity_step_deg [deg]: the gamma* step h of the gamma*-sensitivity
    diagnostic (a matched run is also evaluated at gamma*_ref -/+ h; a diagnostic that
    never changes a check's verdict). m2_role: ``diagnostic`` (the default, the user's
    decision of 2026-09-30) or ``blocking`` (the pre-registered rule): with diagnostic an
    M2 fail is still computed and reported but gives no bug_suspect and blocks no
    finding; the closure, the loss identity, the attribution check and M3 to M5 block
    findings either way. convergence: amendment 3."""

    closure_tol_mps: float = Field(default=1.0e-5, gt=0.0)
    identity_tol_mps: float = Field(default=1.0e-5, gt=0.0)
    insertion_e_max: float = Field(default=1.0e-6, gt=0.0, lt=1.0)
    grav_ratio_bounds: tuple[float, float] = (0.33, 3.0)
    bp_ratio_bounds: tuple[float, float] = (0.33, 3.0)
    min_term_mps: float = Field(default=1.0, ge=0.0)
    max_drag_steer_share: float = Field(default=0.5, gt=0.0, le=1.0)
    anchor_margin_kg: float = Field(default=1.5, ge=0.0)
    search_final_flag_rel: float = Field(default=1.0e-4, gt=0.0)
    maxq_scan_points: int = Field(default=256, ge=2)
    maxq_xatol_s: float = Field(default=1.0e-6, gt=0.0)
    unconstrained_kick_mps: float = Field(default=120.0, gt=0.0)
    vk_margin_kg: float = Field(default=5.0, ge=0.0)
    gamma_sensitivity_step_deg: float = Field(default=0.5, gt=0.0, le=5.0)
    m2_role: CheckRole = DIAGNOSTIC_ROLE
    convergence: ConvergenceConfig = ConvergenceConfig()

    @field_validator("grav_ratio_bounds", "bp_ratio_bounds")
    @classmethod
    def _ratio_bounds(cls, v: tuple[float, float]) -> tuple[float, float]:
        if v[0] <= 0.0:
            raise ValueError("ratio bounds must be positive")
        return _ordered_pair(v, "ratio bounds")


class PlanarShared(_Model):
    """The planar shared blocks of one run (``RunConfig.planar``), filled only by
    injection from the experiment level: guidance, search and checks (required) and the
    target orbit (required for end: insertion and for a searched figure of merit)."""

    guidance: GuidanceConfig
    search: SearchConfig
    target_orbit: TargetOrbitConfig | None = None
    checks: ChecksConfig


RunEnd = Literal["stage1_burnout", "all_burnout", "apex", "impact", "insertion"]


class RunConfig(_Model):
    """One run: model, site, assist, per-stage ignition (keyed by stage name), where to
    stop, integrator settings and, on a planar_2d run, the planar shared blocks.

    ``dynamics``, ``site`` and ``planar`` come from the experiment level by injection
    (resolve_experiment); a vertical_1d run may still carry its own ``site`` in the
    baseline (the Phase 1 form). Rules: a vertical_1d run has no planar block, no Earth
    rotation (SiteConfig) and no end: insertion; a planar_2d run needs an explicit
    PlanarSiteConfig, the planar block, an end in PLANAR_ENDS, integrator.rtol equal to
    search.final_rtol, end: insertion for a searched figure of merit, and a target
    orbit for end: insertion or a search. end: impact (which every failed ignition
    requires) skips the search automatically (``search_skip_reason``)."""

    name: str
    dynamics: DynamicsKind = VERTICAL_1D
    site: SiteConfig = SiteConfig()
    assist: AssistConfig = Field(default_factory=NoAssistConfig)
    ignition: dict[str, IgnitionConfig] = Field(default_factory=dict)
    end: RunEnd = "stage1_burnout"
    integrator: IntegratorConfig = IntegratorConfig()
    planar: PlanarShared | None = None

    @model_validator(mode="before")
    @classmethod
    def _planar_site(cls, data: Any) -> Any:
        """On a planar_2d run dict, validate ``site`` as a PlanarSiteConfig (every field
        explicit, rotation allowed); a vertical_1d site stays a SiteConfig."""
        if not (isinstance(data, dict) and data.get("dynamics") == PLANAR_2D):
            return data
        site = data.get("site")
        if not isinstance(site, dict):
            return data
        return {**data, "site": planar_site(site)}

    @model_validator(mode="after")
    def _dynamics_rules(self) -> RunConfig:
        if self.dynamics == VERTICAL_1D:
            if self.planar is not None:
                raise ValueError(
                    "guidance, search, target_orbit and checks are planar_2d blocks "
                    "(this run's dynamics is vertical_1d)"
                )
            if self.end == INSERTION_END:
                raise ValueError("end: insertion needs dynamics: planar_2d")
            if self.site.include_rotation:  # a PlanarSiteConfig instance slips past SiteConfig
                raise ValueError(ROTATION_REFUSAL)
            return self
        if not isinstance(self.site, PlanarSiteConfig):
            raise ValueError(
                "a planar_2d run needs an explicit experiment-level site "
                "{latitude_deg, azimuth_deg, include_rotation}"
            )
        if self.planar is None:
            raise ValueError(
                "a planar_2d run needs the experiment-level guidance, search and checks blocks"
            )
        if self.end not in PLANAR_ENDS:
            raise ValueError(f"end: {self.end} is not a planar_2d end (one of {PLANAR_ENDS})")
        search = self.planar.search
        if self.integrator.rtol != search.final_rtol:
            raise ValueError(
                f"planar_2d: integrator.rtol ({self.integrator.rtol:g}) must equal "
                f"search.final_rtol ({search.final_rtol:g}); the recorded run is flown at "
                "the final verification's tolerance"
            )
        searched = self.figure_of_merit in SEARCHED_FIGURES
        if searched and self.end != INSERTION_END:
            raise ValueError(
                f"search.figure_of_merit: {search.figure_of_merit} needs end: insertion "
                f"(end: {self.end} runs only with figure_of_merit: none, or end: impact, "
                "which skips the search)"
            )
        if (searched or self.end == INSERTION_END) and self.planar.target_orbit is None:
            raise ValueError("a planar_2d run that inserts or searches needs target_orbit")
        return self

    @property
    def search_skip_reason(self) -> str | None:
        """Why a planar_2d run skips the search (amendment 4): ``end: impact`` (which
        every failed ignition requires); None when it does not skip or on vertical_1d."""
        if self.dynamics != PLANAR_2D or self.end != IMPACT_END:
            return None
        failed = [name for name, ign in self.ignition.items() if ign.fails]
        if failed:
            return f"end: impact (ignition {failed[0]} fails)"
        return "end: impact"

    @property
    def figure_of_merit(self) -> FigureOfMerit | None:
        """The figure of merit this run is searched for: the shared
        search.figure_of_merit, ``none`` when the search is skipped, None on vertical_1d."""
        if self.planar is None:
            return None
        if self.search_skip_reason is not None:
            return NO_SEARCH
        return self.planar.search.figure_of_merit

    @model_validator(mode="after")
    def _ignition_rules(self) -> RunConfig:
        """``fails`` needs ``end: impact``; ``push_start`` and a ramp start stated by
        depth, speed or height need an assist model (a pad has no push and no track
        exit); a depth no deeper than the stroke (``at_depth_m <= stroke_m``). The
        first-stage-only rule needs the vehicle's stage order (``resolve_run``)."""
        if any(ign.fails for ign in self.ignition.values()) and self.end != "impact":
            raise ValueError("ignition fails: true requires end: impact")
        pushed = [n for n, ign in self.ignition.items() if ign.reference == "push_start"]
        if pushed and self.assist.model == "none":
            raise ValueError(
                f"ignition {pushed[0]}: reference push_start needs an assist model "
                "(a pad run has no push)"
            )
        for name, ign in self.ignition.items():
            keys = ign.ramp_start_keys
            if keys == IGNITION_KEY_FAMILIES[0]:
                continue
            if self.assist.model == "none":
                raise ValueError(
                    f"ignition {name}: a ramp start by {keys[0]} needs an assist model "
                    "(a pad run has no push and no track exit)"
                )
            depth = ign.at_depth_m
            if isinstance(self.assist, ConstantAccelConfig) and depth is not None:
                if depth > self.assist.stroke_m:
                    raise ValueError(
                        f"ignition {name}: at_depth_m {depth:g} m is deeper than the "
                        f"track (stroke_m {self.assist.stroke_m:g} m)"
                    )
        return self

    def ignition_for(self, stage_name: str) -> IgnitionConfig:
        """Ignition settings of a stage; the default when the run does not list it."""
        return self.ignition.get(stage_name, IgnitionConfig())


class SweepConfig(_Model):
    """A full grid over dotted-path axes applied to the run named ``of``.

    ``paired: true`` (planar_2d only; axes on ``guidance.*``, which address the shared
    guidance block and need label ``guidance_study``, and on ``vehicle.*``) also re-runs
    the baseline at every point with the same overrides, so each point is compared with
    its own pair. On planar_2d a ``vehicle.*`` axis must be paired, so a vehicle change
    is never booked as an assist gain.

    ``offload`` (planar_2d only; SP1 step 7) names cases of the experiment's ``offload``
    block (stage-1 solves and fixed cases only, on a sweep of a variant): at every point
    each is solved (or fixed) with the point's run in place of the case's ``of``, at the
    reference payload of the point's baseline, and its results become columns of
    sweep_index.csv."""

    of: str
    axes: dict[str, list[Any]]
    paired: bool = False
    offload: list[str] = Field(default_factory=list)

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


class BoundConfig(_Model):
    """A named bound (amendment 6): each run in ``of`` (not the baseline) re-run with
    ``overrides`` (dotted paths; ``vehicle.`` paths go to the vehicle), compared with
    the baseline re-run under the same overrides (``paired_baseline``, always true),
    like a paired sensitivity case. Shared-block paths are refused."""

    name: str
    of: list[str] = Field(min_length=1)
    overrides: dict[str, Any] = Field(min_length=1)
    paired_baseline: Literal[True] = True


class CaseConfig(_Model):
    """A calibration case (label calibration only): an independent run of the baseline,
    never compared, with another vehicle file (``vehicle``, a path the caller's loader
    reads), a partial ``site`` or ``target_orbit`` merged over the experiment's, and
    ``overrides`` on ``vehicle.`` paths only. It must change at least one of them."""

    vehicle: str | None = None
    site: dict[str, Any] | None = None
    target_orbit: dict[str, Any] | None = None
    overrides: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _changes_something(self) -> CaseConfig:
        given = (self.vehicle, self.site, self.target_orbit)
        if all(x is None for x in given) and not self.overrides:
            raise ValueError(
                "a case must change the vehicle, site, target_orbit or a vehicle. path"
            )
        bad = sorted(p for p in self.overrides if not p.startswith(VEHICLE_PREFIX))
        if bad:
            raise ValueError(f"case overrides take vehicle. paths only, got {bad}")
        return self


# ------------------------------------------------------------------------ offload block

OFFLOAD_FIXED_KEYS: tuple[str, ...] = (
    "stage1_t",
    "stage1_fraction",
    "stage2_t",
    "stage2_fraction",
    "both_fraction",
)
"""The ways an imposed (``fixed:``) offload is stated: a mass [t] taken from the first or
the second stage, a fraction of that stage's load, or one fraction of each stage's load
(mode both)."""
OFFLOAD_FIXED_MODES: dict[str, OffloadMode] = {
    "stage1_t": "stage1",
    "stage1_fraction": "stage1",
    "stage2_t": "stage2",
    "stage2_fraction": "stage2",
    "both_fraction": "both",
}
"""The offload mode (``vehicle.OFFLOAD_MODES``) of each OFFLOAD_FIXED_KEYS key."""
OFFLOAD_MASS_KEY_SUFFIX = "_t"
"""Suffix of the OFFLOAD_FIXED_KEYS keys that state a mass in tonnes (the others state a
fraction of a load)."""
OFFLOAD_STAGE1_INDEX = 0
OFFLOAD_STAGE2_INDEX = 1
"""Stage indices of the offload modes: ``stage1`` is the vehicle's first stage, ``stage2``
its second, whatever their names."""
OFFLOAD_PROPELLANT_KEY = "propellant_mass_t"
OFFLOAD_DRY_MASS_KEY = "dry_mass_t"
"""Vehicle-file keys an offload case restates (``offload_overrides``)."""
OFFLOAD_GROSS_MODES: tuple[OffloadMode, ...] = ("stage1",)
"""Solve modes quoted gross, never netted against a pad control: stage 1, the headline
(its pad control is a consistency test of the solver, not a correction). A stage2 or
both solve is quoted net of the pad control (D-SP1-10), so it needs ``pad_control:
true`` and is never solved at a sweep point or in a sensitivity arm (neither solves a
pad control)."""
PAD_CONTROL_PREFIX = "offload_"
"""Name of a pad-control run: ``<baseline>__offload_<mode>`` (``pad_control_run_name``)."""


class OffloadFixedConfig(_Model):
    """An imposed offload (an offload case's ``fixed:``; docs/physics.md, "Experiment
    schema (planar)"): exactly one of OFFLOAD_FIXED_KEYS, a mass [t] (> 0) taken from the
    first stage (``stage1_t``) or the second (``stage2_t``), a fraction in (0, 1) of that
    stage's load (``stage1_fraction``, ``stage2_fraction``), or the same fraction in (0,
    1) of each stage's load (``both_fraction``, mode both). A key counts as given when it
    is present, a null included (as the exclusive families count it), so a null is
    refused, never ignored. A mass at or beyond the stage's load is refused when the
    experiment is resolved against its vehicle."""

    stage1_t: float | None = Field(default=None, gt=0.0, allow_inf_nan=False)
    stage1_fraction: float | None = Field(default=None, gt=0.0, lt=1.0)
    stage2_t: float | None = Field(default=None, gt=0.0, allow_inf_nan=False)
    stage2_fraction: float | None = Field(default=None, gt=0.0, lt=1.0)
    both_fraction: float | None = Field(default=None, gt=0.0, lt=1.0)

    @model_validator(mode="after")
    def _exactly_one(self) -> OffloadFixedConfig:
        """Exactly one key of OFFLOAD_FIXED_KEYS given (a null counting as given),
        holding a number."""
        given = [k for k in OFFLOAD_FIXED_KEYS if k in self.model_fields_set]
        if len(given) != 1:
            found = ", ".join(given) if given else "none"
            raise ValueError(
                f"a fixed offload states exactly one of {', '.join(OFFLOAD_FIXED_KEYS)} "
                f"(given: {found})"
            )
        if getattr(self, given[0]) is None:
            raise ValueError(f"fixed offload {given[0]} is null: it must hold a number")
        return self

    @property
    def key(self) -> str:
        """The OFFLOAD_FIXED_KEYS key that states the offload."""
        return next(k for k in OFFLOAD_FIXED_KEYS if getattr(self, k) is not None)

    @property
    def mode(self) -> OffloadMode:
        """The offload mode (stage1, stage2 or both) of the stated key."""
        return OFFLOAD_FIXED_MODES[self.key]

    @property
    def fraction(self) -> float | None:
        """The stated fraction (dimensionless) of a ``*_fraction`` key; None for a mass key
        (``stage1_t``, ``stage2_t``), whose SI value is ``offload_kg``."""
        if self.key.endswith(OFFLOAD_MASS_KEY_SUFFIX):
            return None
        return float(getattr(self, self.key))

    def offload_kg(self, vehicle: Vehicle) -> float:
        """The imposed offload x [kg] along ``mode`` on vehicle: the stated mass in kg, or
        the stated fraction of ``vehicle.offload_load_kg`` (the stage's load, or both
        loads together for ``both_fraction``). Raises ValueError for a vehicle without the
        mode's stages."""
        fraction = self.fraction
        if fraction is None:
            return float(units.t_to_kg(float(getattr(self, self.key))))
        return fraction * offload_load_kg(vehicle, self.mode)


class OffloadCaseConfig(_Model):
    """One case of the ``offload`` block: ``name`` (its recorded run's name), ``of`` (a
    variant, never the baseline: the pad's own offload is the pad control) and exactly
    one of ``solve`` (the mode solved for the largest offload that still carries the
    reference payload: stage1, stage2 or both) or ``fixed`` (an imposed offload,
    OffloadFixedConfig: the variant flies it, its payload capacity is compared with the
    reference payload). Optional: ``stage2_offload_t`` [t] (> 0) taken from the second
    stage before the case (stage-1 cases only: the frontier point of a both-stage
    offload), ``stage1_dry_mass_added_t`` [t] (> 0), an assumed structural penalty added
    to the first stage's dry mass of the assisted run only (a penalty row, never a sized
    structure), and ``paired_pad`` (also fly the pad with the same final propellant
    change, without the penalty, and compare the case with it on one vehicle)."""

    name: str
    of: str
    solve: OffloadMode | None = None
    fixed: OffloadFixedConfig | None = None
    stage2_offload_t: float | None = Field(default=None, gt=0.0, allow_inf_nan=False)
    stage1_dry_mass_added_t: float | None = Field(default=None, gt=0.0, allow_inf_nan=False)
    paired_pad: bool = False

    @model_validator(mode="after")
    def _one_way(self) -> OffloadCaseConfig:
        """Exactly one of solve and fixed; stage2_offload_t only on a stage-1 case;
        paired_pad not on a penalty row (the paired pad must fly the case's vehicle)."""
        if (self.solve is None) == (self.fixed is None):
            raise ValueError(
                f"offload case {self.name!r}: give exactly one of solve (a mode to solve) "
                "or fixed (an imposed offload)"
            )
        if self.stage2_offload_t is not None and self.mode != "stage1":
            raise ValueError(
                f"offload case {self.name!r}: stage2_offload_t is taken before a stage-1 "
                f"case only (this case's mode is {self.mode})"
            )
        if self.paired_pad and self.stage1_dry_mass_added_t is not None:
            raise ValueError(
                f"offload case {self.name!r}: paired_pad compares the case with the pad on "
                "one vehicle (the matched-payload attribution), but stage1_dry_mass_added_t "
                "is the assisted run's only; give the penalty row without paired_pad"
            )
        return self

    @property
    def mode(self) -> OffloadMode:
        """The case's offload mode: ``solve``, or the mode of its ``fixed`` key."""
        if self.solve is not None:
            return self.solve
        assert self.fixed is not None
        return self.fixed.mode

    @property
    def solved(self) -> bool:
        """True for a solved case (``solve``), False for an imposed one (``fixed``)."""
        return self.solve is not None


class OffloadEnergyConfig(_Model):
    """Inputs of the offload's energy comparison (docs/physics.md, "Reporting definitions
    (planar)"), sourced Quantities because the vehicle file holds no fuel split:
    ``fuel_mass_t``, the fuel (RP-1) mass [t] of each stage's full load, keyed by stage
    name (every stage of the vehicle; the oxidiser, LOX, is the remainder of the stage's
    propellant, so each value must be > 0 and no more than that propellant, checked
    against the vehicle when the experiment is resolved), and
    ``heating_value_MJ_per_kg``, the fuel's lower heating value [MJ/kg] (> 0)."""

    fuel_mass_t: dict[str, Quantity] = Field(min_length=1)
    heating_value_MJ_per_kg: Quantity

    @model_validator(mode="after")
    def _positive(self) -> OffloadEnergyConfig:
        """Every fuel mass and the heating value > 0 (the bounds against the vehicle's
        propellant are checked at resolve time, ``_check_offload_energy``)."""
        for stage, q in self.fuel_mass_t.items():
            if not q.value > 0.0:
                raise ValueError(f"offload energy fuel_mass_t {stage}: must be > 0 t")
        if not self.heating_value_MJ_per_kg.value > 0.0:
            raise ValueError("offload energy heating_value_MJ_per_kg must be > 0")
        return self

    @property
    def heating_value_J_per_kg(self) -> float:
        """The lower heating value [J/kg]."""
        return float(units.mj_to_j(self.heating_value_MJ_per_kg.value))

    def fuel_kg(self, stage: str) -> float:
        """The fuel mass [kg] of a stage's full load."""
        return float(units.t_to_kg(self.fuel_mass_t[stage].value))


class OffloadConfig(_Model):
    """The experiment's ``offload`` block (SP1 step 7; docs/physics.md, "Experiment schema
    (planar)"): ``reference`` (the baseline, whose payload capacity is the reference
    payload P_ref), ``cases`` (OffloadCaseConfig, unique names), ``pad_control`` (solve
    every distinct solve mode of the cases once on the reference baseline at P_ref;
    required by a stage2 or both solve, which is quoted net of it),
    ``sensitivity_of`` (case names re-solved under the experiment's sensitivity params,
    pad and assisted run perturbed alike) and ``energy`` (OffloadEnergyConfig, optional).
    Not a shared block: nothing in it changes a run of the experiment.

    The YAML key ``reference`` is read into the field ``reference_run`` (a pydantic
    alias): ``reference`` is a key of the ignition time family (IGNITION_KEY_FAMILIES),
    which no other config model may use as a field name (the exclusive-family rule is by
    key name; tests/test_config.py checks it). The block is not a run dict, so the YAML
    key itself is never merged by that rule."""

    reference_run: str = Field(alias="reference")
    cases: list[OffloadCaseConfig] = Field(min_length=1)
    pad_control: bool = False
    sensitivity_of: list[str] = Field(default_factory=list)
    energy: OffloadEnergyConfig | None = None

    @model_validator(mode="after")
    def _names(self) -> OffloadConfig:
        """Unique case names; sensitivity_of names known cases, each once; a stage2 or
        both solve only with pad_control and never in sensitivity_of (its offload is
        quoted net of the pad's, D-SP1-10, which an arm does not solve)."""
        names = [c.name for c in self.cases]
        dup = sorted({n for n in names if names.count(n) > 1})
        if dup:
            raise ValueError(f"offload case names are used twice: {dup}")
        unknown = [n for n in self.sensitivity_of if n not in names]
        if unknown:
            raise ValueError(f"offload sensitivity_of names no case: {unknown}")
        if len(set(self.sensitivity_of)) != len(self.sensitivity_of):
            raise ValueError("offload sensitivity_of names a case twice")
        for c in self.cases:
            netted = c.solve is not None and c.solve not in OFFLOAD_GROSS_MODES
            if netted and not self.pad_control:
                raise ValueError(
                    f"offload case {c.name!r}: a {c.solve} solve is quoted net of the pad "
                    "control (stage-2 and both-stage offloads are a property of the vehicle "
                    "model, D-SP1-10), so the block needs pad_control: true"
                )
            if netted and c.name in self.sensitivity_of:
                raise ValueError(
                    f"offload sensitivity_of {c.name!r}: a {c.solve} solve is quoted net of "
                    "the pad control, which an arm does not solve under its perturbation; "
                    "name stage-1 solves and fixed cases"
                )
        return self

    @property
    def pad_control_modes(self) -> tuple[str, ...]:
        """The distinct modes of the solved cases, in OFFLOAD_MODES order, when
        pad_control is set; () otherwise."""
        if not self.pad_control:
            return ()
        solved = {c.solve for c in self.cases if c.solve is not None}
        return tuple(m for m in OFFLOAD_MODES if m in solved)

    def case(self, name: str) -> OffloadCaseConfig:
        """The case of that name (KeyError when there is none)."""
        for c in self.cases:
            if c.name == name:
                return c
        raise KeyError(name)


def _path_root(path: str) -> str:
    """First segment of a dotted path."""
    return path.split(".", 1)[0]


def _refuse_shared_path(path: str, what: str, paired: bool = False) -> None:
    """Raise ValueError when a per-run path addresses an experiment-level shared block
    (a ``guidance.*`` path is allowed only in a paired sweep)."""
    root = _path_root(path)
    if root in SHARED_PATH_ROOTS and not (paired and root == PAIRED_SWEEP_ROOT):
        raise ValueError(
            f"{what} {path!r}: {root} is an experiment-level shared block, identical for "
            "every run (only a paired sweep of a guidance_study may vary guidance.*)"
        )


def _check_baseline_shared(exp: dict[str, Any]) -> None:
    """Raise ValueError when the baseline declares a shared block itself. The one
    exception is the Phase 1 form: a vertical_1d baseline's own ``site`` when the
    experiment declares no site."""
    base = exp["baseline"]
    phase1_site = exp.get("site") is None and exp.get("dynamics") in (None, VERTICAL_1D)
    for key in (*SHARED_KEYS, PLANAR_KEY):
        if key not in base or (key == "site" and phase1_site):
            continue
        raise ValueError(
            f"baseline sets {key!r}: {key} is an experiment-level shared block; declare it "
            "once at the top of the experiment file"
        )


def shared_run_blocks(exp_dict: dict[str, Any]) -> dict[str, Any]:
    """The run-dict entries an experiment injects into every run: ``dynamics`` and
    ``site`` as declared, and ``planar`` holding the declared guidance, search,
    target_orbit and checks (in that order). Only what the experiment declares (not
    None); an empty dict for a Phase 1 experiment. Deep copies of the raw blocks."""
    out = {k: copy.deepcopy(exp_dict[k]) for k in RUN_SHARED_KEYS if exp_dict.get(k) is not None}
    planar = {
        k: copy.deepcopy(exp_dict[k]) for k in PLANAR_SHARED_KEYS if exp_dict.get(k) is not None
    }
    if planar:
        out[PLANAR_KEY] = planar
    return out


def inject_shared(run_dict: dict[str, Any], shared: dict[str, Any]) -> dict[str, Any]:
    """A deep copy of ``run_dict`` with the ``shared`` entries placed right after
    ``name``. With nothing to inject it is an equal copy with the key order kept, so a
    Phase 1 run dict resolves byte-identically."""
    if not shared:
        return copy.deepcopy(run_dict)
    out: dict[str, Any] = {}
    if "name" in run_dict:
        out["name"] = copy.deepcopy(run_dict["name"])
    out.update(copy.deepcopy(shared))
    out.update({k: copy.deepcopy(v) for k, v in run_dict.items() if k not in out})
    return out


def _run_path(path: str) -> str:
    """The run-dict path of a dotted path: ``guidance.*`` (a planar shared block) lives
    under ``planar.`` in the run dict; every other path is unchanged."""
    return f"{PLANAR_KEY}.{path}" if _path_root(path) in PLANAR_SHARED_KEYS else path


class ExperimentConfig(_Model):
    """An experiment file: vehicle path, optional label, the shared blocks, baseline run,
    variant overrides, sweeps, sensitivity, bounds and calibration cases.

    Shared blocks (experiment level, identical for every run): ``dynamics``
    (vertical_1d when absent), ``site`` (a PlanarSiteConfig on planar_2d, where it is
    required), and the planar_2d-only ``guidance``, ``search``, ``target_orbit`` and
    ``checks``. They are injected into the baseline before it is validated (so
    ``baseline`` is the injected run) and refused in the baseline itself (except a
    Phase 1 site), in variants, sweeps, sensitivity parameters and bounds. Variant
    values are partial run dicts merged over the baseline. ``label: calibration`` allows
    ``cases``; ``label: guidance_study`` allows paired ``guidance.*`` sweeps. On
    planar_2d a sweep of ``vehicle.*`` paths must be paired, and no per-run path may
    change the ``integrator`` block (sample_dt_s included), so every compared run
    integrates and samples alike.

    Input is the raw experiment dict (as read from YAML). ``model_dump()`` of a
    validated experiment does not validate again: its baseline already holds the
    injected blocks, which the raw form refuses; re-resolve from the raw dict instead."""

    name: str
    vehicle: str
    label: ExperimentLabel | None = None
    dynamics: DynamicsKind | None = None
    site: SiteConfig | None = None
    guidance: GuidanceConfig | None = None
    search: SearchConfig | None = None
    target_orbit: TargetOrbitConfig | None = None
    checks: ChecksConfig | None = None
    baseline: RunConfig
    variants: dict[str, dict[str, Any]] = Field(default_factory=dict)
    sweeps: list[SweepConfig] = Field(default_factory=list)
    sensitivity: SensitivityConfig | None = None
    bounds: list[BoundConfig] = Field(default_factory=list)
    cases: dict[str, CaseConfig] = Field(default_factory=dict)
    offload: OffloadConfig | None = None

    @model_validator(mode="before")
    @classmethod
    def _inject_into_baseline(cls, data: Any) -> Any:
        """Refuse shared blocks in the raw baseline, then inject the declared ones; a
        planar_2d experiment's site is validated as a PlanarSiteConfig."""
        if not (isinstance(data, dict) and isinstance(data.get("baseline"), dict)):
            return data
        _check_baseline_shared(data)
        out = {**data, "baseline": inject_shared(data["baseline"], shared_run_blocks(data))}
        if data.get("dynamics") == PLANAR_2D and isinstance(data.get("site"), dict):
            out["site"] = planar_site(data["site"])
        return out

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

    @model_validator(mode="after")
    def _shared_blocks_stay_shared(self) -> ExperimentConfig:
        if self.dynamics != PLANAR_2D:
            declared = [k for k in PLANAR_SHARED_KEYS if getattr(self, k) is not None]
            if declared:
                raise ValueError(
                    f"{', '.join(declared)}: planar_2d blocks; declare dynamics: planar_2d"
                )
        for vname, override in self.variants.items():
            for key in override:
                _refuse_shared_path(key, f"variant {vname!r} sets")
        for k, sweep in enumerate(self.sweeps, start=1):
            for path in sweep.axes:
                _refuse_shared_path(path, f"sweep {k} axis", paired=sweep.paired)
        if self.sensitivity is not None:
            for param in self.sensitivity.params:
                _refuse_shared_path(param, "sensitivity parameter")
        for bound in self.bounds:
            for path in bound.overrides:
                _refuse_shared_path(path, f"bound {bound.name!r} override")
        if self.dynamics == PLANAR_2D:
            self._lock_integrator()
        return self

    def _lock_integrator(self) -> None:
        """planar_2d: refuse every per-run integrator change (sample_dt_s included)."""
        for vname, override in self.variants.items():
            block = override.get(INTEGRATOR_KEY)
            if block is None:
                continue
            keys = sorted(block) if isinstance(block, dict) else [repr(block)]
            if keys:
                _refuse_integrator(f"variant {vname!r} sets integrator {keys}")
        paths = [(p, f"sweep {k} axis") for k, sw in enumerate(self.sweeps, 1) for p in sw.axes]
        if self.sensitivity is not None:
            paths += [(p, "sensitivity parameter") for p in self.sensitivity.params]
        paths += [(p, f"bound {b.name!r} override") for b in self.bounds for p in b.overrides]
        for path, what in paths:
            if _path_root(path) == INTEGRATOR_KEY:
                _refuse_integrator(f"{what} {path!r}")

    @model_validator(mode="after")
    def _labelled_features(self) -> ExperimentConfig:
        for k, sweep in enumerate(self.sweeps, start=1):
            roots = {_path_root(p) for p in sweep.axes}
            if not sweep.paired:
                if self.dynamics == PLANAR_2D and VEHICLE_ROOT in roots:
                    raise ValueError(
                        f"sweep {k}: on planar_2d a sweep of {VEHICLE_ROOT}.* paths needs "
                        "paired: true (the baseline is re-run with the same vehicle, as in "
                        "a sensitivity case or a bound)"
                    )
                continue
            if self.dynamics != PLANAR_2D:
                raise ValueError(
                    f"sweep {k}: a paired sweep re-runs the baseline under the planar shared "
                    "blocks: it needs dynamics: planar_2d"
                )
            if not roots <= PAIRED_SWEEP_ROOTS:
                raise ValueError(
                    f"sweep {k}: a paired sweep varies guidance.* and vehicle.* paths only"
                )
            if PAIRED_SWEEP_ROOT in roots and self.label != GUIDANCE_STUDY_LABEL:
                raise ValueError(
                    f"sweep {k}: paired sweeps need label: {GUIDANCE_STUDY_LABEL} to vary "
                    "guidance.*"
                )
            if sweep.of == self.baseline.name:
                raise ValueError(
                    f"sweep {k}: a paired sweep of the baseline has no pair; sweep a variant"
                )
        if self.cases and self.label != CALIBRATION_LABEL:
            raise ValueError(f"cases need label: {CALIBRATION_LABEL}")
        for cname, case in self.cases.items():
            if case.site is not None and self.site is None:
                raise ValueError(f"case {cname!r} changes site, but the experiment declares none")
            if case.target_orbit is not None and self.target_orbit is None:
                raise ValueError(
                    f"case {cname!r} changes target_orbit, but the experiment declares none"
                )
        return self

    @model_validator(mode="after")
    def _bound_and_case_names(self) -> ExperimentConfig:
        known = {self.baseline.name, *self.variants}
        names = [*known]
        for bound in self.bounds:
            for of in bound.of:
                if of not in known:
                    raise ValueError(f"bound {bound.name!r} of {of!r}: no such run")
                if of == self.baseline.name:
                    raise ValueError(
                        f"bound {bound.name!r}: the baseline is re-run with the bound's "
                        "overrides automatically; list variants only"
                    )
            names += [bound_run_name(of, bound.name) for of in (self.baseline.name, *bound.of)]
        names += list(self.cases)
        what = "runs, bounds and cases"
        if self.offload is not None:
            names += offload_run_names(self.offload, self.baseline.name)
            what = "runs, bounds, cases and offload runs"
        seen: set[str] = set()
        for name in names:
            if name in seen:
                raise ValueError(f"run name {name!r} is used twice ({what})")
            seen.add(name)
        return self

    @model_validator(mode="after")
    def _offload_block(self) -> ExperimentConfig:
        """The offload block (SP1 step 7) and the sweeps that name its cases: planar_2d
        with search.figure_of_merit payload (the solve and its verification are payload
        searches); ``reference`` the baseline; every case ``of`` a variant (never the
        baseline); ``sensitivity_of`` needs the sensitivity block (its params); a sweep's
        ``offload`` names cases of the block, each once, on a sweep that is not of the
        baseline (the baseline's own offload is the pad control), and no stage2 or both
        solve (quoted net of a pad control, which a sweep does not solve)."""
        swept = [(k, s) for k, s in enumerate(self.sweeps, start=1) if s.offload]
        block = self.offload
        if block is None:
            if swept:
                raise ValueError(
                    f"sweep {swept[0][0]}: offload names cases of the experiment's offload "
                    "block, which this experiment does not declare"
                )
            return self
        if self.dynamics != PLANAR_2D:
            raise ValueError("offload: a planar_2d block (declare dynamics: planar_2d)")
        fom = None if self.search is None else self.search.figure_of_merit
        if fom != "payload":
            raise ValueError(
                "offload: the offload solve and its verification are payload searches, so "
                f"the block needs search.figure_of_merit payload (got {fom})"
            )
        if block.reference_run != self.baseline.name:
            raise ValueError(
                f"offload reference {block.reference_run!r} must be the baseline "
                f"{self.baseline.name!r}: the reference payload is the full-load pad's P*"
            )
        for case in block.cases:
            if case.of == self.baseline.name:
                raise ValueError(
                    f"offload case {case.name!r}: of {case.of!r} is the baseline; the "
                    "baseline's own offload is the pad control (pad_control: true)"
                )
            if case.of not in self.variants:
                raise ValueError(f"offload case {case.name!r}: of {case.of!r}: no such variant")
        if block.sensitivity_of and self.sensitivity is None:
            raise ValueError(
                "offload sensitivity_of re-solves its cases under the experiment's "
                "sensitivity params: declare the sensitivity block"
            )
        names = {c.name for c in block.cases}
        for k, sweep in swept:
            if sweep.of == self.baseline.name:
                raise ValueError(
                    f"sweep {k}: of {sweep.of!r} is the baseline, so its offload cases would "
                    "solve the baseline's own offload, which is the pad control "
                    "(pad_control: true); name offload cases on a sweep of a variant"
                )
            unknown = [n for n in sweep.offload if n not in names]
            if unknown:
                raise ValueError(f"sweep {k}: offload names no case of the block: {unknown}")
            if len(set(sweep.offload)) != len(sweep.offload):
                raise ValueError(f"sweep {k}: offload names a case twice")
            for name in sweep.offload:
                solve = block.case(name).solve
                if solve is not None and solve not in OFFLOAD_GROSS_MODES:
                    raise ValueError(
                        f"sweep {k}: offload case {name!r} solves {solve}, which is quoted "
                        "net of a pad control; a sweep solves none, so it names stage-1 "
                        "solves and fixed cases only"
                    )
        return self


def _refuse_integrator(what: str) -> None:
    """Raise ValueError for a per-run integrator change on planar_2d."""
    raise ValueError(
        f"{what}: on planar_2d no integrator setting may differ between runs (method, "
        "rtol, steps, the max_step caps including the shared planar_max_step_s, and "
        "sample_dt_s are the baseline's, so compared runs integrate and sample alike)"
    )


def bound_run_name(of: str, bound: str) -> str:
    """Name of the run ``of`` re-run under the bound ``bound``: ``<of>__<bound>``."""
    return f"{of}__{bound}"


def paired_baseline_name(point_name: str, baseline: str) -> str:
    """Name of the baseline re-run paired with a sweep point: ``<point>__<baseline>``."""
    return f"{point_name}__{baseline}"


def pad_control_run_name(baseline: str, mode: str) -> str:
    """Name of the pad control of an offload mode: ``<baseline>__offload_<mode>``."""
    return f"{baseline}__{PAD_CONTROL_PREFIX}{mode}"


def offload_run_names(block: OffloadConfig, baseline: str) -> list[str]:
    """The names of the runs an offload block writes (results directories): every case's
    recorded run (its name), the paired pad of a ``paired_pad`` case
    (``<case>__<baseline>``, ``paired_baseline_name``) and the pad control of each mode
    (``pad_control_run_name``)."""
    names: list[str] = []
    for case in block.cases:
        names.append(case.name)
        if case.paired_pad:
            names.append(paired_baseline_name(case.name, baseline))
    names += [pad_control_run_name(baseline, m) for m in block.pad_control_modes]
    return names


# ---------------------------------------------------------------- overrides and merging


class ConfigPathError(ValueError):
    """A dotted override path that does not address the run or vehicle dict."""


class ExclusiveKeysError(ValueError):
    """Keys of two exclusive families (EXCLUSIVE_KEY_FAMILIES) given together at one
    dict level of an override."""


def merge_run_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge a variant override over a run dict: dicts merge by key, scalars and lists
    replace. A dict carrying a discriminator key (SWITCH_KEYS: assist ``model``, startup
    ``kind``) that the base's dict lacks or differs from replaces it wholesale, so
    switching assist models or startup shapes leaves no stale keys behind. An override
    dict that sets a key of an exclusive family (EXCLUSIVE_KEY_FAMILIES) removes the
    base's keys of the other families of that group at the same level, so restating a
    setting another way leaves one parameterisation; keys of two families given
    together anywhere in the override raise ExclusiveKeysError. A key is given when it
    is present, an explicit None included. Inputs are not mutated."""
    for path, keys in _dict_levels(override, ""):
        _refuse_mixed_families(keys, f"override {path!r}" if path else "override")
    return _merge(base, override)


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """merge_run_dicts without the check of the override (done once, at the top)."""
    out = copy.deepcopy(base)
    for stale in _displaced_keys(out, override):
        del out[stale]
    for key, value in override.items():
        current = out.get(key)
        if isinstance(value, dict) and isinstance(current, dict) and not _switches(current, value):
            out[key] = _merge(current, value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _switches(current: dict[str, Any], value: dict[str, Any]) -> bool:
    """True when value changes a discriminator key of current (see SWITCH_KEYS)."""
    return any(k in value and current.get(k) != value[k] for k in SWITCH_KEYS)


def _named_families(keys: Collection[str], group: KeyFamilies) -> list[tuple[str, ...]]:
    """The families of ``group`` that ``keys`` hold at least one key of, in table order."""
    return [family for family in group if any(k in keys for k in family)]


def _refuse_mixed_families(keys: Collection[str], where: str) -> None:
    """Raise ExclusiveKeysError when ``keys`` (the keys given together at one dict
    level) belong to two families of one group of EXCLUSIVE_KEY_FAMILIES."""
    for group in EXCLUSIVE_KEY_FAMILIES:
        named = _named_families(keys, group)
        if len(named) > 1:
            given = [k for family in named for k in family if k in keys]
            options = " or ".join("{" + ", ".join(family) + "}" for family in group)
            raise ExclusiveKeysError(
                f"{where}: keys {given} of two exclusive families are given together; "
                f"state the setting one way only ({options})"
            )


def _displaced_keys(base: Collection[str], given: Collection[str]) -> list[str]:
    """The keys of ``base`` (a dict, or its keys) that an override setting the keys
    ``given`` at the same dict level displaces: for each group of
    EXCLUSIVE_KEY_FAMILIES of which ``given`` names exactly one family, the base's keys
    of the group's other families. Empty when ``given`` holds no family key or only keys
    of the family the base uses."""
    out: list[str] = []
    for group in EXCLUSIVE_KEY_FAMILIES:
        named = _named_families(given, group)
        if len(named) == 1:
            out += [k for family in group if family is not named[0] for k in family if k in base]
    return out


def _dict_levels(node: Any, path: str) -> Iterator[tuple[str, list[str]]]:
    """(dotted path, keys) of ``node`` and of every dict nested in it, through dicts and
    lists (a list item's segment is its index); ``path`` is the path of ``node``."""
    if isinstance(node, dict):
        yield path, list(node)
        for key, value in node.items():
            yield from _dict_levels(value, f"{path}.{key}" if path else str(key))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _dict_levels(value, f"{path}.{i}" if path else str(i))


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
        if not quantity and isinstance(container, dict):
            for stale in _displaced_keys(container, (key,)):
                del container[stale]  # another parameterisation (EXCLUSIVE_KEY_FAMILIES)
        container[key] = copy.deepcopy(value)


def _refuse_mixed_run_overrides(overrides: dict[str, Any]) -> None:
    """Raise ExclusiveKeysError when the run paths of ``overrides`` (those without the
    ``vehicle.`` prefix) give keys of two exclusive families in one dict: two paths with
    the same parent, a dict value, or a path and a dict value that meet in one dict.
    Parents are compared as written (dotted text), which is exact for run dicts: the
    dicts that hold family keys are reached through dict keys only."""
    given: dict[str, list[str]] = {}
    for path, value in overrides.items():
        if path.startswith(VEHICLE_PREFIX):
            continue
        parent, _, key = path.rpartition(".")
        given.setdefault(parent, []).append(key)
        for level, keys in _dict_levels(value, path):
            given.setdefault(level, []).extend(keys)
    for parent, keys in given.items():
        _refuse_mixed_families(keys, f"overrides under {parent!r}")


def apply_overrides(
    run_dict: dict[str, Any], overrides: dict[str, Any], vehicle_dict: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply ``{dotted.path: value}`` overrides and return new (run, vehicle) dicts.

    A path sets exactly one key; its siblings stay, apart from the discriminator and
    family rules below. Unlike merge_run_dicts, the value is never merged into what was
    there: a dict given as the value replaces the node at that path whole, so no key
    below it is inherited (``ignition.stage1: {at_depth_m: 50}`` drops an inherited
    ``startup`` and ``fails`` along with the time keys; the path
    ``ignition.stage1.at_depth_m`` keeps them).

    Paths starting with ``vehicle.`` go to the vehicle dict, where a number aimed at a
    Quantity (or at a key that does not exist yet) becomes ``{value, assumed: true, note:
    override}``; any other target takes the raw value and validation reports a type
    mismatch. Missing intermediate dict keys are created (validation catches typos); a
    missing named list item or index raises ConfigPathError; list segments match an item's
    ``name`` or an integer index. Setting a discriminator key (``model``, ``kind``) to a
    different value replaces its whole dict, as merge_run_dicts does. Setting a run key
    of an exclusive family (EXCLUSIVE_KEY_FAMILIES) removes the keys of the group's
    other families from its dict, as merge_run_dicts does, so a sweep axis
    ``assist.exit_speed_mps`` over a parent with ``net_accel_g`` leaves only the exit
    speed; run overrides that give keys of two families for one dict (two paths, the
    keys of a dict value, or both; a key given as None counts) raise ExclusiveKeysError.
    Vehicle paths are not subject to the family rule.
    """
    _refuse_mixed_run_overrides(overrides)
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

    ``sweep_index`` and ``point_index`` are both 1-based: sweep_index is the position of
    the sweep in the experiment's ``sweeps`` list and names the ``sweep_<n>`` results
    directory. ``run.name`` is ``run_NNNN`` with NNNN = point_index, numbered within its
    own sweep, so it is unique only per sweep: results must be namespaced by sweep_index
    as well (for example ``sweep_1/run_0001``) or the sweeps of one experiment would
    collide.

    ``overrides`` are the axis paths as declared (a paired ``guidance.*`` path is
    applied under ``planar.`` in the run dict). ``paired_baseline`` is the baseline
    re-run with the same overrides for a paired sweep (named ``<run>__<baseline>``),
    else None.
    """

    sweep_index: int
    point_index: int
    of: str
    overrides: dict[str, Any]
    run: ResolvedRun
    paired_baseline: ResolvedRun | None = None
    offload: tuple[ResolvedOffloadCase, ...] = ()
    """The offload cases the sweep names (``SweepConfig.offload``), each built on this
    point's run (``offload_case_start``, named ``<run>__<case>``; no paired pad); empty
    unless the sweep names some."""


@dataclass(frozen=True)
class SensitivityCase:
    """One +/- perturbation of one parameter of one run."""

    of: str
    param: str
    fraction: float
    run: ResolvedRun


@dataclass(frozen=True)
class BoundCase:
    """One resolved bound (amendment 6): ``runs`` maps each run named in the bound's
    ``of`` to its re-run under ``overrides`` (named ``<of>__<bound>``), and
    ``baseline`` is the baseline re-run under the same overrides (its pair)."""

    name: str
    overrides: dict[str, Any]
    runs: dict[str, ResolvedRun]
    baseline: ResolvedRun


@dataclass(frozen=True)
class ResolvedOffloadCase:
    """One offload case resolved against its runs (nothing flown): ``config``; ``variant``,
    the run it is built on (the variant named in ``of``, or a sweep point's run);
    ``start``, that run with the case's vehicle changes (``offload_case_start``: the
    stage-2 pre-offload, the assumed stage-1 dry mass and, for a fixed case, the imposed
    offload), named after the case: what a solve starts from, or the fixed case's run
    itself; ``pad_start``, the pad with the same propellant changes and no penalty
    (``paired_pad``; None otherwise), named ``<case>__<baseline>``, to which a solved
    case adds its x*; ``imposed_kg``, a fixed case's offload x [kg] along its mode (None
    for a solved case)."""

    config: OffloadCaseConfig
    variant: ResolvedRun
    start: ResolvedRun
    pad_start: ResolvedRun | None
    imposed_kg: float | None

    @property
    def name(self) -> str:
        """The case's name."""
        return self.config.name


@dataclass(frozen=True)
class ResolvedOffloadArm:
    """One sensitivity arm of an offload case (``offload.sensitivity_of``): the case
    ``case`` rebuilt (``start``) on its variant with ``param`` moved by the signed
    ``fraction`` (that perturbed variant is ``variant``), and ``pad``, the reference
    baseline under the same perturbation for a ``vehicle.`` parameter (the vehicle dict
    of the perturbed variant, as a sensitivity case's same-perturbation baseline) or the
    unchanged baseline for a run parameter (``pad_perturbed`` False: a pad has no drive
    to perturb)."""

    case: str
    param: str
    fraction: float
    start: ResolvedRun
    pad: ResolvedRun
    pad_perturbed: bool
    imposed_kg: float | None = None
    """A fixed case's imposed offload x [kg] on the perturbed variant (None when solved)."""
    variant: ResolvedRun | None = None
    """The perturbed variant the arm's start is built on (its full loads)."""


@dataclass(frozen=True)
class ResolvedOffload:
    """The experiment's offload block resolved (nothing flown): ``config``, the
    ResolvedOffloadCase of every case in order, the sensitivity arms and the modes the
    pad control solves (``OffloadConfig.pad_control_modes``)."""

    config: OffloadConfig
    cases: list[ResolvedOffloadCase]
    arms: list[ResolvedOffloadArm]
    pad_control_modes: tuple[str, ...]


@dataclass(frozen=True)
class ResolvedExperiment:
    """Everything an experiment declares, validated, nothing run. ``bounds`` and
    ``cases`` (calibration only; independent runs, never compared) are empty unless
    declared; neither is part of ``runs``. ``offload`` is the resolved offload block
    (None unless declared)."""

    experiment: ExperimentConfig
    baseline: ResolvedRun
    variants: dict[str, ResolvedRun]
    sweeps: list[list[SweepPoint]]
    sensitivity: list[SensitivityCase]
    bounds: list[BoundCase] = field(default_factory=list)
    cases: dict[str, ResolvedRun] = field(default_factory=dict)
    offload: ResolvedOffload | None = None

    @property
    def runs(self) -> dict[str, ResolvedRun]:
        """Baseline first, then every variant, keyed by name."""
        return {self.baseline.name: self.baseline, **self.variants}


VehicleLoader = Callable[[str], dict[str, Any]]
"""Reads a vehicle file named in an experiment (a calibration case's ``vehicle``) and
returns its raw dict; supplied by the caller, since config.py does no file I/O."""


def _check_planar_vehicle(name: str, run: RunConfig, vehicle: VehicleConfig) -> None:
    """planar_2d rules that need the vehicle: an aero block, two stages (one guidance
    law each), and no lit stage 1 on a run whose search is skipped unless the shared
    search flies fixed guidance (figure_of_merit none)."""
    if vehicle.aero is None:
        raise ValueError(f"run {name!r}: planar_2d needs the vehicle's aero block (drag)")
    if len(vehicle.stages) != PLANAR_STAGE_COUNT:
        raise ValueError(
            f"run {name!r}: planar_2d guidance needs a {PLANAR_STAGE_COUNT}-stage vehicle, "
            f"got {len(vehicle.stages)}"
        )
    reason = run.search_skip_reason
    first = vehicle.stages[0].name
    fixed = run.planar is not None and run.planar.search.figure_of_merit == NO_SEARCH
    if reason is not None and not run.ignition_for(first).fails and not fixed:
        raise ValueError(
            f"run {name!r}: {reason} skips the search, but stage {first} lights and its "
            "guidance would come from the search; fail its ignition, or use "
            "search.figure_of_merit: none with fixed guidance"
        )


def resolve_run(name: str, run_dict: dict[str, Any], vehicle_dict: dict[str, Any]) -> ResolvedRun:
    """Validate one run dict and its vehicle dict together (vertical_1d: no heating-rule
    fairing; planar_2d: see _check_planar_vehicle; every stage after the first ignites
    by time, release-referenced and at t_ign_s >= 0, never by depth, speed or height)."""
    run_dict = {**copy.deepcopy(run_dict), "name": name}
    run = RunConfig.model_validate(run_dict)
    vehicle = VehicleConfig.model_validate(vehicle_dict)
    heating = vehicle.to_vehicle().fairing_rule.trigger == HEATING_TRIGGER
    if run.dynamics == VERTICAL_1D and heating:
        raise ValueError(
            f"run {name!r}: fairing_drop trigger {HEATING_TRIGGER} is a planar_2d feature "
            "(Phase 2); the 1-D model supports only the staging and never rules"
        )
    if run.dynamics == PLANAR_2D:
        _check_planar_vehicle(name, run, vehicle)
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
        if i > 0 and ignition.t_ign_s < 0.0:
            raise ValueError(
                f"run {name!r}, ignition {stage.name}: a later stage ignites at t_ign_s "
                ">= 0 after its staging coast"
            )
        if i > 0 and ignition.ramp_start_keys != IGNITION_KEY_FAMILIES[0]:
            raise ValueError(
                f"run {name!r}, ignition {stage.name}: a ramp start by "
                f"{ignition.ramp_start_keys[0]} is only for the first stage (a later stage "
                "ignites at t_ign_s >= 0 after its staging coast)"
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
    """apply_overrides on a resolved run, naming the run and the caller on a bad path or
    on overrides that mix exclusive key families."""
    try:
        return apply_overrides(parent.run_dict, overrides, parent.vehicle_dict)
    except ConfigPathError as exc:
        raise ConfigPathError(f"{what} on run {parent.name!r}: {exc}") from exc
    except ExclusiveKeysError as exc:
        raise ExclusiveKeysError(f"{what} on run {parent.name!r}: {exc}") from exc


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


def _resolve_bound(
    bound: BoundConfig, baseline: ResolvedRun, runs: dict[str, ResolvedRun]
) -> BoundCase:
    """Resolve a bound: each ``of`` run and the baseline re-run with its overrides."""
    what = f"bound {bound.name!r}"
    r, v = _perturb(baseline, bound.overrides, what)
    paired = resolve_run(bound_run_name(baseline.name, bound.name), r, v)
    resolved: dict[str, ResolvedRun] = {}
    for of in bound.of:
        r, v = _perturb(runs[of], bound.overrides, what)
        resolved[of] = resolve_run(bound_run_name(of, bound.name), r, v)
    return BoundCase(bound.name, dict(bound.overrides), resolved, paired)


def _resolve_case(
    cname: str,
    case: CaseConfig,
    exp_dict: dict[str, Any],
    vehicle_dict: dict[str, Any],
    load_vehicle: VehicleLoader | None,
) -> ResolvedRun:
    """Resolve a calibration case: the raw baseline with the experiment's shared blocks,
    the case's site and target_orbit merged over them, its vehicle file (read through
    ``load_vehicle``) or the experiment's vehicle, then its vehicle. overrides."""
    shared = shared_run_blocks(exp_dict)
    if case.site is not None:
        shared["site"] = merge_run_dicts(shared["site"], case.site)
    if case.target_orbit is not None:
        planar = shared[PLANAR_KEY]
        planar["target_orbit"] = merge_run_dicts(planar["target_orbit"], case.target_orbit)
    run_dict = inject_shared(exp_dict["baseline"], shared)
    vdict = vehicle_dict
    if case.vehicle is not None:
        if load_vehicle is None:
            raise ValueError(
                f"case {cname!r} names vehicle file {case.vehicle!r}; resolve_experiment "
                "needs load_vehicle to read it (config.py does no file I/O)"
            )
        vdict = load_vehicle(case.vehicle)
    try:
        r, v = apply_overrides(run_dict, case.overrides, vdict)
    except ConfigPathError as exc:
        raise ConfigPathError(f"case {cname!r}: {exc}") from exc
    return resolve_run(cname, r, v)


def _restated_quantity(
    vehicle_dict: dict[str, Any], stage_index: int, key: str, value_t: float, note: str
) -> dict[str, Any]:
    """The vehicle-file Quantity of a stage mass an offload restates: ``value_t`` [t],
    ``assumed: true`` (a derived number, not the source's), and a note that names the
    change and the vehicle dict's own value [t] and provenance. Raises ConfigPathError
    when the mass is not a Quantity."""
    path = f"stages.{stage_index}.{key}"
    orig = read_path(vehicle_dict, path)
    if not (isinstance(orig, dict) and _is_number(orig.get("value"))):
        raise ConfigPathError(f"{path}: not a Quantity, cannot restate it")
    provenance = f"source: {orig['source']}" if orig.get("source") else "assumed"
    return {
        "value": value_t,
        "assumed": True,
        "note": f"{note}; the vehicle's value was {orig['value']:g} t ({provenance})",
    }


def offload_overrides(
    vehicle_dict: dict[str, Any], removed_kg: list[float], dry_added_kg: float, what: str
) -> dict[str, Any]:
    """The ``vehicle.`` overrides of an offload (docs/physics.md, "Experiment schema
    (planar)"): every stage's ``propellant_mass_t`` less removed_kg[i] [kg] (stages with
    0 left alone; the tanks partly filled, every dry mass unchanged) and the first
    stage's ``dry_mass_t`` plus dry_added_kg [kg] (an assumed structural penalty; left
    alone at 0), each a restated Quantity [t] (``_restated_quantity``). Raises
    ValueError naming ``what`` when a stage would keep no propellant (a stage needs
    propellant > 0)."""
    out: dict[str, Any] = {}
    for i, taken in enumerate(removed_kg):
        if taken == 0.0:
            continue
        load_t = read_value(vehicle_dict, f"stages.{i}.{OFFLOAD_PROPELLANT_KEY}")
        load_kg = float(units.t_to_kg(load_t))
        if not taken < load_kg:
            raise ValueError(
                f"{what}: takes {units.kg_to_t(taken):g} t of propellant from stage "
                f"{vehicle_dict['stages'][i].get('name', i)!r}, which carries "
                f"{units.kg_to_t(load_kg):g} t (an offload beyond the load; a stage keeps "
                "some propellant)"
            )
        note = f"{what}: {units.kg_to_t(taken):.9g} t of propellant removed (tanks partly filled)"
        path = f"{VEHICLE_PREFIX}stages.{i}.{OFFLOAD_PROPELLANT_KEY}"
        value_t = float(units.kg_to_t(load_kg - taken))
        out[path] = _restated_quantity(vehicle_dict, i, OFFLOAD_PROPELLANT_KEY, value_t, note)
    if dry_added_kg > 0.0:
        i = OFFLOAD_STAGE1_INDEX
        dry_t = read_value(vehicle_dict, f"stages.{i}.{OFFLOAD_DRY_MASS_KEY}")
        dry_kg = float(units.t_to_kg(dry_t))
        note = (
            f"{what}: {units.kg_to_t(dry_added_kg):.9g} t of stage-1 dry mass added, an "
            "assumed structural penalty, not a sized structure"
        )
        path = f"{VEHICLE_PREFIX}stages.{i}.{OFFLOAD_DRY_MASS_KEY}"
        value_t = float(units.kg_to_t(dry_kg + dry_added_kg))
        out[path] = _restated_quantity(vehicle_dict, i, OFFLOAD_DRY_MASS_KEY, value_t, note)
    return out


def _offloaded(run: ResolvedRun, overrides: dict[str, Any], name: str, what: str) -> ResolvedRun:
    """run with the vehicle overrides applied (``_perturb``), resolved under name (only
    renamed when there are none)."""
    if not overrides:
        return resolve_run(name, run.run_dict, run.vehicle_dict)
    r, v = _perturb(run, overrides, what)
    return resolve_run(name, r, v)


def offload_case_start(
    case: OffloadCaseConfig, run: ResolvedRun, name: str, *, penalty: bool = True
) -> tuple[ResolvedRun, float | None]:
    """The start of an offload case on run (a variant, a sweep point, or with penalty
    False the pad for a paired pad), resolved under name, and a fixed case's imposed
    offload x [kg] (None for a solved case): run's vehicle with the case's
    ``stage2_offload_t`` taken from the second stage, for a fixed case the imposed
    offload taken along its mode (``vehicle.offload_split_kg`` on run's vehicle), and,
    with penalty, ``stage1_dry_mass_added_t`` added to the first stage's dry mass
    (``offload_overrides``). Raises ValueError for an offload beyond a stage's load."""
    vehicle = run.to_vehicle()
    removed = [0.0] * vehicle.n_stages
    if case.stage2_offload_t is not None:
        removed[OFFLOAD_STAGE2_INDEX] += float(units.t_to_kg(case.stage2_offload_t))
    imposed: float | None = None
    if case.fixed is not None:
        imposed = case.fixed.offload_kg(vehicle)
        split = offload_split_kg(vehicle, case.fixed.mode, imposed)
        removed = [a + b for a, b in zip(removed, split, strict=True)]
    added = case.stage1_dry_mass_added_t if penalty else None
    dry = 0.0 if added is None else float(units.t_to_kg(added))
    what = f"offload case {case.name!r}"
    overrides = offload_overrides(run.vehicle_dict, removed, dry, what)
    return _offloaded(run, overrides, name, what), imposed


def offload_solved_run(
    start: ResolvedRun, mode: OffloadMode, offload_kg: float, case: str, name: str
) -> ResolvedRun:
    """start with the solved offload x* = offload_kg [kg] removed along mode
    (``vehicle.offload_split_kg`` on start's vehicle, ``offload_overrides``), resolved
    under name: the vehicle dict of a solved case's recorded run, or of its paired pad.
    At x* = 0 only the name changes."""
    removed = list(offload_split_kg(start.to_vehicle(), mode, offload_kg))
    what = f"offload case {case!r} (solved)"
    return _offloaded(start, offload_overrides(start.vehicle_dict, removed, 0.0, what), name, what)


def _check_offload_energy(energy: OffloadEnergyConfig | None, vehicle: VehicleConfig) -> None:
    """The energy block against the vehicle: a fuel mass for every stage and no other
    key, each no more than its stage's propellant (the oxidiser is the remainder).
    Raises ValueError."""
    if energy is None:
        return
    stages = {s.name: s for s in vehicle.stages}
    unknown = sorted(set(energy.fuel_mass_t) - set(stages))
    if unknown:
        raise ValueError(f"offload energy fuel_mass_t names no stage of the vehicle: {unknown}")
    missing = [n for n in stages if n not in energy.fuel_mass_t]
    if missing:
        raise ValueError(f"offload energy fuel_mass_t needs every stage; missing {missing}")
    for name, q in energy.fuel_mass_t.items():
        propellant = stages[name].propellant_mass_t.value
        if q.value > propellant:
            raise ValueError(
                f"offload energy fuel_mass_t {name}: {q.value:g} t is more than the stage's "
                f"propellant ({propellant:g} t; the oxidiser is the remainder)"
            )


def _resolve_offload(
    experiment: ExperimentConfig, baseline: ResolvedRun, variants: dict[str, ResolvedRun]
) -> ResolvedOffload | None:
    """The offload block resolved: each case's start (and paired-pad start), each
    sensitivity arm and the pad-control modes; the energy block checked against the
    vehicle. None without a block."""
    block = experiment.offload
    if block is None:
        return None
    _check_offload_energy(block.energy, baseline.vehicle)
    cases: list[ResolvedOffloadCase] = []
    for case in block.cases:
        variant = variants[case.of]
        start, imposed = offload_case_start(case, variant, case.name)
        pad_start = None
        if case.paired_pad:
            pad_name = paired_baseline_name(case.name, baseline.name)
            pad_start, _ = offload_case_start(case, baseline, pad_name, penalty=False)
        cases.append(ResolvedOffloadCase(case, variant, start, pad_start, imposed))
    arms: list[ResolvedOffloadArm] = []
    params = {} if experiment.sensitivity is None else experiment.sensitivity.params
    for name in block.sensitivity_of:
        case = block.case(name)
        variant = variants[case.of]
        for param, fraction in params.items():
            nominal = _nominal_value(variant, param)
            for sign in (+1.0, -1.0):
                tag = f"{param}__{'+' if sign > 0 else '-'}{fraction:g}"
                what = f"offload sensitivity of {name!r}"
                r, v = _perturb(variant, {param: nominal * (1.0 + sign * fraction)}, what)
                arm_variant = resolve_run(f"{case.of}__{tag}", r, v)
                start, imposed = offload_case_start(case, arm_variant, f"{name}__{tag}")
                perturbed = param.startswith(VEHICLE_PREFIX)
                pad = (
                    resolve_run(
                        f"{baseline.name}__{tag}", baseline.run_dict, arm_variant.vehicle_dict
                    )
                    if perturbed
                    else baseline
                )
                arms.append(
                    ResolvedOffloadArm(
                        name, param, sign * fraction, start, pad, perturbed, imposed, arm_variant
                    )
                )
    return ResolvedOffload(block, cases, arms, block.pad_control_modes)


def resolve_experiment(
    exp_dict: dict[str, Any],
    vehicle_dict: dict[str, Any],
    load_vehicle: VehicleLoader | None = None,
) -> ResolvedExperiment:
    """Validate the baseline, every variant, every sweep point (and its paired baseline
    and offload cases), every sensitivity case, every bound, every calibration case and
    the offload block (its cases, paired pads, sensitivity arms and energy inputs) of an
    experiment against its vehicle dict, without running anything. Pure (dicts in, a
    ResolvedExperiment out): a caller with an in-memory experiment dict (the SP2 app)
    resolves it here, runs it with ``sim.run_resolved`` and assembles the result with
    ``results_io.planar_experiment_result`` without writing anything.

    The experiment's declared shared blocks are injected into every run dict
    (shared_run_blocks, inject_shared); a Phase 1 experiment that declares none gets
    run dicts identical to the ones it got before Phase 2. ``load_vehicle`` reads the
    vehicle file a calibration case names (None: such a case raises). Raises pydantic
    ValidationError, ConfigPathError, ExclusiveKeysError or ValueError (all ValueError
    subclasses) with the run and path named; nothing else escapes for a bad file."""
    experiment = ExperimentConfig.model_validate(exp_dict)
    base_dict = inject_shared(exp_dict["baseline"], shared_run_blocks(exp_dict))
    baseline = resolve_run(experiment.baseline.name, base_dict, vehicle_dict)
    variants: dict[str, ResolvedRun] = {}
    for vname, override in experiment.variants.items():
        try:
            merged = merge_run_dicts(base_dict, override)
        except ExclusiveKeysError as exc:
            raise ExclusiveKeysError(f"variant {vname!r}: {exc}") from exc
        variants[vname] = resolve_run(vname, merged, vehicle_dict)
    runs = {baseline.name: baseline, **variants}

    sweeps: list[list[SweepPoint]] = []
    for k, sweep in enumerate(experiment.sweeps, start=1):
        parent = runs[sweep.of]
        points: list[SweepPoint] = []
        paths = list(sweep.axes)
        for i, values in enumerate(itertools.product(*(sweep.axes[p] for p in paths)), start=1):
            overrides = dict(zip(paths, values, strict=True))
            run_overrides = {_run_path(p): x for p, x in overrides.items()}
            r, v = _perturb(parent, run_overrides, f"sweep {k}")
            point = resolve_run(f"run_{i:04d}", r, v)
            paired = None
            if sweep.paired:
                rb, vb = _perturb(baseline, run_overrides, f"sweep {k}")
                paired = resolve_run(paired_baseline_name(point.name, baseline.name), rb, vb)
            offload: list[ResolvedOffloadCase] = []
            for cname in sweep.offload:
                assert experiment.offload is not None  # ExperimentConfig checks it
                case = experiment.offload.case(cname)
                start, imposed = offload_case_start(case, point, f"{point.name}__{cname}")
                offload.append(ResolvedOffloadCase(case, point, start, None, imposed))
            points.append(SweepPoint(k, i, sweep.of, overrides, point, paired, tuple(offload)))
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
    bounds = [_resolve_bound(b, baseline, runs) for b in experiment.bounds]
    calibration = {
        cname: _resolve_case(cname, case, exp_dict, vehicle_dict, load_vehicle)
        for cname, case in experiment.cases.items()
    }
    offload = _resolve_offload(experiment, baseline, variants)
    return ResolvedExperiment(
        experiment,
        baseline,
        variants,
        sweeps,
        cases,
        bounds=bounds,
        cases=calibration,
        offload=offload,
    )
