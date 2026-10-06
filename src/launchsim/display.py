"""Display-only geometry and reconstructions of the 2-D launch scene (pure: no I/O, no
printing; nothing here is model output).

The scene (SP2, docs/phases/inputs/2026-10-05-SP2-design.md section 4.4) replays the
recorded time series of a planar_2d run and draws around it what the model does not
compute: a vehicle with a length and a diameter, tank levels, a spent stage and fairing
halves falling away, a held attitude when the engines are off, and a camera. This module
holds those reconstructions as pure functions of recorded rows and of two display files
(configs/display/<vehicle>.yaml for the shapes, configs/display/scene.yaml for the camera
and the generic proportions; every number there is ``{value, source}`` or ``{value,
assumed: true, note}``, the vehicle file's own Quantity). docs/physics.md,
"Display-only reconstructions (not part of the model)", states every formula.

Sections, in the order the scene builder uses them:

- the display files (``VehicleDisplayConfig``, ``SceneDisplayConfig``, ``DisplayGeometry``
  and the generic shape of a vehicle without a display file);
- tank levels from the recorded mass (``tank_levels``), the per-row step series (stage
  index, fairing on, thrust on) and the load-time checks (``tank_checks``: a structured
  verdict, never an exception);
- the separation state of a dropped body (``separation_state``), its vacuum coast
  (``vacuum_coast``, ``kepler_coast`` as the closed-form oracle of the tests) and the
  measured screen gap of that coast from the vehicle's recorded rows (``coast_gap_m``);
- the screen transform and the camera law (``screen_xy``, ``screen_angle_rad``,
  ``running_extent_m``, ``view_height_m``);
- the row selection of the scene's time grid (``select_rows``, D-SP2-16) and the
  rebuilt-mass check of the rounded payload (``rebuilt_mass_residual_kg``);
- the held attitude (``held_screen_angle_rad``, D-SP2-17).

Units are SI and radians throughout: metres, seconds, kilograms, newtons, radians. Rows
are the rows of one run's timeseries.csv in file order (``RunRows``), both rows of every
duplicate time kept. Frames: ``alt_m`` and ``downrange_m`` are the recorded Earth-fixed
altitude above the datum R_E and the Earth-fixed downrange arc; the separation state and
the coast use the planar Earth-centred inertial frame of CLAUDE.md ([r, theta, v_r,
v_theta], theta increasing downrange); the screen is a plane through the launch site
with x downrange and y up (a canvas negates y). Constants come from constants.py; the one
degree figure (criterion 5's 0.5 deg) is converted through units.py; the event and phase
names come from phases.planar and phases.trace. This module never imports the I/O reader
run_data (its EventRow and VehicleMasses appear here as type annotations only): the scene
reads the files and hands the rows, events, masses and fairing form in.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
from pydantic import BaseModel, ConfigDict, model_validator
from scipy.integrate import solve_ivp

from launchsim.config import PLANAR_STAGE_COUNT, Quantity
from launchsim.constants import MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M
from launchsim.metrics_planar import FAIRING_AT_STAGING
from launchsim.phases.planar import (
    COAST,
    COAST_PRE_IGN,
    COAST_STAGING,
    CUTOFF_EVENT,
    FAIRING_EVENT,
)
from launchsim.phases.trace import ASSIST_KIND, HOLD_KIND
from launchsim.units import deg_to_rad

if TYPE_CHECKING:
    # Types only: this module never imports the I/O reader at run time (design 4.1, pure).
    from launchsim.run_data import EventRow, VehicleMasses

# ------------------------------------------------------------------ tolerances (criteria 5 and 6)

ALT_TOL_REL = 0.005
"""Altitude tolerance of exit criterion 5, relative part [-]: the larger of this times
the recorded altitude and ALT_TOL_MIN_M."""
ALT_TOL_MIN_M = 1.0
"""Altitude tolerance of exit criterion 5, floor [m]."""
DOWNRANGE_TOL_REL = 0.005
"""Downrange tolerance of exit criterion 5, relative part [-]."""
DOWNRANGE_TOL_MIN_M = 10.0
"""Downrange tolerance of exit criterion 5, floor [m]."""
PITCH_TOL_DEG = 0.5
"""Attitude tolerance of exit criterion 5 [deg], as the criterion states it, where the
model defines an attitude: thrust on, in the hold or on the track."""
PITCH_TOL_RAD = float(deg_to_rad(PITCH_TOL_DEG))
"""PITCH_TOL_DEG in radians (units.deg_to_rad), the tolerance the code compares against."""
PLUME_TOL = 0.02
"""Plume-fraction tolerance of exit criterion 5 [-] at every CSV row but a run's last."""
MASS_TOL_KG = 1.0
"""Mass tolerance of exit criterion 6 [kg]: the rebuilt stack mass against ``m_kg``, the
stage-1 tank at the stage-1 depletion event, the liftoff identity."""
EVENT_TIME_TOL_S = 1e-6
"""Tolerance [s] on an event's time against its matched row (criterion 5), and the
widest gap at which an event row is matched to a time-series row by time
(``match_events``) when no row holds its t_s exactly (every recorded event does)."""
FILL_START_TOL = 1e-4
"""Tolerance [-] of exit criterion 6 on a tank's start fill against one minus its offload
fraction (a fraction of the full load; the rebuild itself is exact to 1e-12)."""
TANK_STEP_TOL_KG = 1.0
"""Largest step [kg] a tank series may take between the two rows of one time (staging,
the fairing drop and every other boundary), and the tolerance of the stage-2 tank
against its load before stage-2 ignition and against ``recorded_m_res_kg`` on the last
row (design 4.4, review 01 finding 1)."""
TANK_RISE_TOL_KG = 1e-3
"""Largest rise [kg] a tank series may show between consecutive rows: the CSV's 12
significant digits leave about 1e-6 kg of noise at 6e5 kg, so a thousandfold margin
still catches any real rise (a wrong fairing flag raises the stage-2 tank by 1,700 kg)."""

# ------------------------------------------------------------------ row selection (D-SP2-16)

SELECTION_EARLY_END_S = 40.0
"""End of the densely selected launch segment [s after release]: every
SELECTION_EARLY_STEP-th row before it, every SELECTION_LATE_STEP-th after."""
SELECTION_EARLY_STEP = 2
"""Row stride of the base selection before SELECTION_EARLY_END_S."""
SELECTION_LATE_STEP = 20
"""Row stride of the base selection after SELECTION_EARLY_END_S."""
SELECTION_HALF = 0.5
"""Share of each tolerance every CSV row must be within under linear interpolation of
the selected rows: half, so that the page's rounding keeps the other half."""
SELECTION_MAX_PASSES = 30
"""Most insertion passes ``select_rows`` runs; measured: one pass on every recorded run
(review 01). A selection that still fails after this many is reported as not converged."""

# ------------------------------------------------------------------ vacuum coast (D-SP2-19)

COAST_RTOL = 1e-12
"""Relative tolerance of the coast integration (DOP853)."""
COAST_ATOL_R_M = 1e-6
"""Absolute tolerance on the radius [m]: rtol times a 6.4e6 m radius."""
COAST_ATOL_THETA_RAD = 1e-14
"""Absolute tolerance on the inertial angle [rad]: a tenth of rtol times a 0.1 rad arc
(tighter than the radius and velocity floors, so the relative tolerance governs)."""
COAST_ATOL_V_MPS = 1e-9
"""Absolute tolerance on either velocity component [m/s]: rtol times 3,000 m/s."""
COAST_T_MAX_S = 20_000.0
"""Time limit of a coast that never reaches the surface [s] (a body left in orbit)."""
COAST_SAMPLE_DT_S = 1.0
"""Sample step of the returned coast path [s]: a 300 s fall is 300 samples."""

# ------------------------------------------------------------------ small helpers


def _positive(name: str, value: float) -> None:
    """Raise ValueError unless ``value`` is above zero."""
    if not value > 0.0:
        raise ValueError(f"{name} must be above zero, not {value}")


# ------------------------------------------------------------------ display files


class _DisplayModel(BaseModel):
    """Base of every display-file model: unknown keys are errors, instances are frozen
    (the vehicle file's own rule, config._Model). No units are converted: every length
    is in metres and every pixel size in CSS pixels as written."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def values(self) -> dict[str, float]:
        """The model's Quantity fields as plain floats, keyed by field name (SI, as the
        file holds them)."""
        out: dict[str, float] = {}
        for name in type(self).model_fields:
            field = getattr(self, name)
            if isinstance(field, Quantity):
                out[name] = float(field.value)
        return out

    def provenance(self) -> dict[str, str]:
        """Each Quantity field's provenance text: its ``source``, or ``assumed`` plus its
        note, keyed by field name."""
        out: dict[str, str] = {}
        for name in type(self).model_fields:
            field = getattr(self, name)
            if isinstance(field, Quantity):
                out[name] = quantity_provenance(field)
        return out


def quantity_provenance(quantity: Quantity) -> str:
    """One line of provenance for a display Quantity: ``source: <text>`` for a sourced
    number, ``assumed`` plus ``: <note>`` when it has one. Dimensionless text."""
    if quantity.source is not None:
        return f"source: {quantity.source}"
    return "assumed" if not quantity.note else f"assumed: {quantity.note}"


class VehicleShapeConfig(_DisplayModel):
    """The drawn vehicle of a display file [m]: body diameter, the lengths of stage 1, the
    interstage, stage 2 and the fairing (their sum is the stack length), the fairing
    diameter and the engine-section length drawn at the base of stage 1 (part of its
    length). Every length is above zero and the engine section fits inside stage 1."""

    body_diameter_m: Quantity
    stage1_length_m: Quantity
    interstage_length_m: Quantity
    stage2_length_m: Quantity
    fairing_length_m: Quantity
    fairing_diameter_m: Quantity
    engine_section_length_m: Quantity

    @model_validator(mode="after")
    def _lengths(self) -> VehicleShapeConfig:
        for name, value in self.values().items():
            _positive(name, value)
        if self.engine_section_length_m.value > self.stage1_length_m.value:
            raise ValueError("engine_section_length_m must not exceed stage1_length_m")
        return self


class SiloShapeConfig(_DisplayModel):
    """The drawn silo of a display file [m]: shaft diameter (wider than the fairing, checked
    by VehicleDisplayConfig), the pitch and size of the rings drawn on the shaft wall, the
    carriage height and the brake-rail width above the mouth. Every length above zero."""

    shaft_diameter_m: Quantity
    ring_pitch_m: Quantity
    ring_size_m: Quantity
    carriage_height_m: Quantity
    brake_rail_width_m: Quantity

    @model_validator(mode="after")
    def _lengths(self) -> SiloShapeConfig:
        for name, value in self.values().items():
            _positive(name, value)
        return self


class PadShapeConfig(_DisplayModel):
    """The drawn pad of a display file [m]: the mount height under the vehicle's base and
    the size of the hold-down clamps. Every length above zero."""

    mount_height_m: Quantity
    clamp_size_m: Quantity

    @model_validator(mode="after")
    def _lengths(self) -> PadShapeConfig:
        for name, value in self.values().items():
            _positive(name, value)
        return self


class VehicleDisplayConfig(_DisplayModel):
    """One display file (configs/display/<name>.yaml): ``name``, the vehicle names it
    ``applies_to`` (configs/vehicles/*.yaml ``name`` fields; at least one, no repeats), and
    the ``vehicle``, ``silo`` and ``pad`` shapes. The shaft must be wider than the fairing.
    Every number is a Quantity with a source or ``assumed: true``; unknown keys are
    refused. Lengths in metres."""

    name: str
    applies_to: list[str]
    vehicle: VehicleShapeConfig
    silo: SiloShapeConfig
    pad: PadShapeConfig

    @model_validator(mode="after")
    def _consistent(self) -> VehicleDisplayConfig:
        if not self.applies_to:
            raise ValueError("applies_to needs at least one vehicle name")
        if len(set(self.applies_to)) != len(self.applies_to):
            raise ValueError("applies_to repeats a vehicle name")
        if self.silo.shaft_diameter_m.value <= self.vehicle.fairing_diameter_m.value:
            raise ValueError("silo.shaft_diameter_m must exceed vehicle.fairing_diameter_m")
        return self

    def geometry(self) -> DisplayGeometry:
        """The DisplayGeometry of this file: its numbers [m] with their provenance, not
        generic."""
        return DisplayGeometry(
            vehicle=self.vehicle.values(),
            silo=self.silo.values(),
            pad=self.pad.values(),
            provenance={
                **{f"vehicle.{k}": v for k, v in self.vehicle.provenance().items()},
                **{f"silo.{k}": v for k, v in self.silo.provenance().items()},
                **{f"pad.{k}": v for k, v in self.pad.provenance().items()},
            },
            generic=False,
            reason=f"display file {self.name}",
        )


class CameraConfig(_DisplayModel):
    """The camera of scene.yaml: the minimum view height [m] (H_MIN of ``view_height_m``,
    above zero) and the margin [-] on the running extent (at least 1)."""

    min_view_height_m: Quantity
    margin: Quantity

    @model_validator(mode="after")
    def _ranges(self) -> CameraConfig:
        _positive("min_view_height_m", self.min_view_height_m.value)
        if self.margin.value < 1.0:
            raise ValueError("camera.margin must be at least 1")
        return self


class GenericShapeConfig(_DisplayModel):
    """Proportions of the generic shape drawn for a vehicle without a display file
    (``generic_geometry``), all dimensionless ratios: ``fineness`` (stack length over body
    diameter), the fairing, stage-2, interstage and engine-section lengths as fractions of
    the stack length (the four together under 1; stage 1 takes the rest), the fairing
    diameter over the body diameter (at least 1), and the ground items over the body
    diameter: shaft diameter (above the fairing ratio), ring pitch, ring size, carriage
    height, brake-rail width, pad mount height and clamp size. Every ratio above zero."""

    fineness: Quantity
    fairing_fraction: Quantity
    stage2_fraction: Quantity
    interstage_fraction: Quantity
    engine_section_fraction: Quantity
    fairing_diameter_ratio: Quantity
    shaft_diameter_ratio: Quantity
    ring_pitch_ratio: Quantity
    ring_size_ratio: Quantity
    carriage_height_ratio: Quantity
    brake_rail_width_ratio: Quantity
    pad_mount_height_ratio: Quantity
    clamp_size_ratio: Quantity

    @model_validator(mode="after")
    def _ratios(self) -> GenericShapeConfig:
        for name, value in self.values().items():
            _positive(name, value)
        parts = (
            self.fairing_fraction.value
            + self.stage2_fraction.value
            + self.interstage_fraction.value
            + self.engine_section_fraction.value
        )
        if parts >= 1.0:
            raise ValueError("generic fractions must leave room for stage 1 (sum below 1)")
        if self.fairing_diameter_ratio.value < 1.0:
            raise ValueError("generic.fairing_diameter_ratio must be at least 1")
        if self.shaft_diameter_ratio.value <= self.fairing_diameter_ratio.value:
            raise ValueError("generic.shaft_diameter_ratio must exceed fairing_diameter_ratio")
        return self


class SceneDisplayConfig(_DisplayModel):
    """configs/display/scene.yaml: the ``camera``, the body width in CSS pixels under which
    the true-scale view switches from the drawn rocket to a marker
    (``to_scale_min_body_px``, D-SP2-35), the marker size [px], the close-up stack length
    [px] and the ``generic`` proportions. Pixel sizes above zero."""

    camera: CameraConfig
    to_scale_min_body_px: Quantity
    marker_size_px: Quantity
    closeup_stack_px: Quantity
    generic: GenericShapeConfig

    @model_validator(mode="after")
    def _pixels(self) -> SceneDisplayConfig:
        for name, value in self.values().items():
            _positive(name, value)
        return self


@dataclass(frozen=True)
class DisplayGeometry:
    """What the scene draws for one vehicle: the ``vehicle``, ``silo`` and ``pad`` lengths
    [m] keyed as the display file names them, the ``provenance`` of each
    (``<group>.<field>``: a source or an assumption), whether the shape is ``generic``
    (built from the reference area, no display file) and the ``reason`` it was chosen."""

    vehicle: dict[str, float]
    silo: dict[str, float]
    pad: dict[str, float]
    provenance: dict[str, str]
    generic: bool
    reason: str

    @property
    def stack_length_m(self) -> float:
        """Stage 1 plus interstage plus stage 2 plus fairing [m]."""
        return (
            self.vehicle["stage1_length_m"]
            + self.vehicle["interstage_length_m"]
            + self.vehicle["stage2_length_m"]
            + self.vehicle["fairing_length_m"]
        )

    def as_dict(self) -> dict[str, Any]:
        """The geometry as JSON-ready data (plain floats, strings and a bool)."""
        return {
            "vehicle": dict(self.vehicle),
            "silo": dict(self.silo),
            "pad": dict(self.pad),
            "stack_length_m": self.stack_length_m,
            "provenance": dict(self.provenance),
            "generic": self.generic,
            "reason": self.reason,
        }


def body_diameter_from_area_m(reference_area_m2: float) -> float:
    """Body diameter [m] of a circular section of area ``reference_area_m2`` [m^2]:
    sqrt(4 A / pi). Raises ValueError for an area that is not above zero."""
    _positive("reference_area_m2", reference_area_m2)
    return math.sqrt(4.0 * reference_area_m2 / math.pi)


def generic_geometry(
    reference_area_m2: float, generic: GenericShapeConfig, reason: str
) -> DisplayGeometry:
    """The generic DisplayGeometry of a vehicle without a display file: the body diameter
    D from its reference area [m^2] (``body_diameter_from_area_m``), the stack length
    fineness x D, the fairing, stage-2, interstage and engine-section lengths as their
    fractions of it, stage 1 the rest, and the ground items as their ratios times D (all
    [m]; the ``generic`` proportions of scene.yaml). ``reason`` says why the generic
    shape was used. Every value's provenance names the ratio it came from."""
    g = generic
    diameter = body_diameter_from_area_m(reference_area_m2)
    length = g.fineness.value * diameter
    fairing = g.fairing_fraction.value * length
    stage2 = g.stage2_fraction.value * length
    interstage = g.interstage_fraction.value * length
    engine = g.engine_section_fraction.value * length
    vehicle = {
        "body_diameter_m": diameter,
        "stage1_length_m": length - fairing - stage2 - interstage,
        "interstage_length_m": interstage,
        "stage2_length_m": stage2,
        "fairing_length_m": fairing,
        "fairing_diameter_m": g.fairing_diameter_ratio.value * diameter,
        "engine_section_length_m": engine,
    }
    silo = {
        "shaft_diameter_m": g.shaft_diameter_ratio.value * diameter,
        "ring_pitch_m": g.ring_pitch_ratio.value * diameter,
        "ring_size_m": g.ring_size_ratio.value * diameter,
        "carriage_height_m": g.carriage_height_ratio.value * diameter,
        "brake_rail_width_m": g.brake_rail_width_ratio.value * diameter,
    }
    pad = {
        "mount_height_m": g.pad_mount_height_ratio.value * diameter,
        "clamp_size_m": g.clamp_size_ratio.value * diameter,
    }
    ratios = g.provenance()
    from_ratio = {
        "vehicle.body_diameter_m": (
            f"derived: sqrt(4 A_ref / pi) of the vehicle's reference area {reference_area_m2} m^2"
        ),
        "vehicle.stage1_length_m": "derived: the stack length less the fairing, stage-2 and "
        "interstage lengths (generic fractions)",
        "vehicle.interstage_length_m": (
            f"generic interstage_fraction; {ratios['interstage_fraction']}"
        ),
        "vehicle.stage2_length_m": f"generic stage2_fraction; {ratios['stage2_fraction']}",
        "vehicle.fairing_length_m": f"generic fairing_fraction; {ratios['fairing_fraction']}",
        "vehicle.fairing_diameter_m": (
            f"generic fairing_diameter_ratio; {ratios['fairing_diameter_ratio']}"
        ),
        "vehicle.engine_section_length_m": (
            f"generic engine_section_fraction; {ratios['engine_section_fraction']}"
        ),
        "silo.shaft_diameter_m": f"generic shaft_diameter_ratio; {ratios['shaft_diameter_ratio']}",
        "silo.ring_pitch_m": f"generic ring_pitch_ratio; {ratios['ring_pitch_ratio']}",
        "silo.ring_size_m": f"generic ring_size_ratio; {ratios['ring_size_ratio']}",
        "silo.carriage_height_m": (
            f"generic carriage_height_ratio; {ratios['carriage_height_ratio']}"
        ),
        "silo.brake_rail_width_m": (
            f"generic brake_rail_width_ratio; {ratios['brake_rail_width_ratio']}"
        ),
        "pad.mount_height_m": f"generic pad_mount_height_ratio; {ratios['pad_mount_height_ratio']}",
        "pad.clamp_size_m": f"generic clamp_size_ratio; {ratios['clamp_size_ratio']}",
    }
    return DisplayGeometry(
        vehicle=vehicle, silo=silo, pad=pad, provenance=from_ratio, generic=True, reason=reason
    )


# ------------------------------------------------------------------ rows and events


@dataclass(frozen=True)
class RunRows:
    """Every row of one run's timeseries.csv in file order, both rows of every duplicate
    time kept: ``t_s`` [s, the run's clock], ``t_rel_s`` [s after release], ``phase`` and
    ``stage`` (the text columns), ``alt_m`` [m above the datum], ``downrange_m`` [m,
    Earth-fixed], ``speed_rel_mps`` [m/s, Earth-relative], ``pitch_rad`` [rad above local
    horizontal, unwrapped as written], ``m_kg`` [kg] and ``thrust_vac_N`` [N]. All arrays
    have one length; times never decrease."""

    t_s: np.ndarray
    t_rel_s: np.ndarray
    phase: tuple[str, ...]
    stage: tuple[str, ...]
    alt_m: np.ndarray
    downrange_m: np.ndarray
    speed_rel_mps: np.ndarray
    pitch_rad: np.ndarray
    m_kg: np.ndarray
    thrust_vac_N: np.ndarray

    def __post_init__(self) -> None:
        n = len(self.t_s)
        arrays = (
            self.t_rel_s,
            self.alt_m,
            self.downrange_m,
            self.speed_rel_mps,
            self.pitch_rad,
            self.m_kg,
            self.thrust_vac_N,
        )
        if n == 0:
            raise ValueError("RunRows needs at least one row")
        if any(len(a) != n for a in arrays) or len(self.phase) != n or len(self.stage) != n:
            raise ValueError("every column of RunRows must have the same length")
        if np.any(np.diff(self.t_s) < 0.0):
            raise ValueError("RunRows times must not decrease")

    def __len__(self) -> int:
        """The row count."""
        return len(self.t_s)


@dataclass(frozen=True)
class EventMatch:
    """An event row matched to the time-series rows: the ``event`` (EventRow), the
    ``index`` of the first row at its time (None when no row lies within
    EVENT_TIME_TOL_S of it) and the ``count`` of rows at that time (0 when unmatched;
    2 at a boundary that was written twice)."""

    event: EventRow
    index: int | None
    count: int

    @property
    def last_index(self) -> int | None:
        """Index of the last row at the event's time (the state after a map), or None."""
        return None if self.index is None else self.index + self.count - 1


def duplicate_groups(t: np.ndarray) -> list[tuple[int, int]]:
    """(first index, count) of every group of consecutive rows with one time [same unit
    as ``t``, which must not decrease] that holds more than one row."""
    out: list[tuple[int, int]] = []
    n = len(t)
    i = 0
    while i < n:
        j = i + 1
        while j < n and t[j] == t[i]:
            j += 1
        if j - i > 1:
            out.append((i, j - i))
        i = j
    return out


def match_events(t_s: np.ndarray, events: Sequence[EventRow]) -> list[EventMatch]:
    """Each event of ``events`` matched to the rows whose ``t_s`` [s, the run's clock]
    equals the event's t_s exactly (every recorded event's does: the planner logs events
    at integration boundaries, which the sampler writes); failing that, to the rows at the
    nearest time within EVENT_TIME_TOL_S; else unmatched (index None, count 0). The
    survey showed that subtracting the release time from an event's t_s can land 5e-11 s
    off the duplicate rows, so events are matched on the run clock, never on the release
    clock."""
    out: list[EventMatch] = []
    for event in events:
        hits = np.nonzero(t_s == event.t_s)[0]
        if len(hits) == 0:
            nearest = int(np.argmin(np.abs(t_s - event.t_s)))
            if abs(float(t_s[nearest]) - event.t_s) <= EVENT_TIME_TOL_S:
                hits = np.nonzero(t_s == t_s[nearest])[0]
        if len(hits) == 0:
            out.append(EventMatch(event, None, 0))
        else:
            out.append(EventMatch(event, int(hits[0]), len(hits)))
    return out


def stage_indices(stage: Sequence[str], stage_names: Sequence[str]) -> np.ndarray:
    """The index of each row's ``stage`` text in ``stage_names`` (the vehicle's stages in
    firing order) as an int array. Raises ValueError for a stage the vehicle does not
    have."""
    unknown = sorted({s for s in stage if s not in stage_names})
    if unknown:
        raise ValueError(f"stage column names stages the vehicle lacks: {unknown}")
    lookup = {name: k for k, name in enumerate(stage_names)}
    return np.array([lookup[s] for s in stage], dtype=int)


def fairing_on_flags(
    rows: RunRows,
    events: Sequence[EventRow],
    masses: VehicleMasses,
    stage_idx: np.ndarray,
    fairing_form: str | None,
) -> tuple[np.ndarray, str | None]:
    """(flags, form): per row, whether the fairing is still attached, and the fairing
    form the flags follow (metrics_planar's FAIRING_* text, or None for a vehicle without
    a fairing or a run that never dropped it). ``fairing_form`` is how the fairing left
    as the reader read it (run_data.fairing_case on the same event rows and masses; the
    scene computes it, this pure module only consumes it).

    Rule (design 4.4): a ``fairing`` event row in COAST_STAGING, or no row under a rule
    that drops it at staging (``fairing_form`` FAIRING_AT_STAGING; run_data.with_drop_masses
    adds such a row marked not recorded), means attached exactly on the stage-1 rows (the
    staging map took it); a ``fairing`` row elsewhere (the heating event in the stage-2
    burn, or at stage-2 ignition) means attached on every row before its time and on the
    first of the rows at its time (the state before the drop), gone from the rest; no
    row and another rule: attached throughout. A vehicle without a fairing mass
    (``fairing_kg`` not above zero) is never attached (nothing to draw or weigh)."""
    n = len(rows)
    if not masses.fairing_kg > 0.0:
        return np.zeros(n, dtype=bool), None
    fairing_rows = [e for e in events if e.name == FAIRING_EVENT]
    at_staging = any(e.phase == COAST_STAGING for e in fairing_rows) or (
        not fairing_rows and fairing_form == FAIRING_AT_STAGING
    )
    if at_staging:
        return stage_idx == 0, FAIRING_AT_STAGING
    if not fairing_rows:
        return np.ones(n, dtype=bool), fairing_form
    (match,) = match_events(rows.t_s, fairing_rows[:1])
    on = rows.t_s < match.event.t_s
    if match.index is not None:
        on[match.index] = True
        on[match.index + 1 : match.index + match.count] = False
    return on, fairing_form


IGNITION_EVENT = "ignition"
"""events.csv name of a stage's ignition row (the planner's name, which run_data spells
too; repeated here so that this pure module never imports the I/O reader)."""
THRUST_OFF_EVENTS = (CUTOFF_EVENT, "ignition_failed", "end")
"""Event names that end a lit stage for the thrust-on rule, besides the stage's own
``propellant`` (depletion) row (exit criterion 5: thrust on from a stage's ignition row
time up to, not including, its propellant, cutoff, ignition_failed or end row time)."""
PROPELLANT_EVENT = "propellant"
"""events.csv name of a stage's depletion (MECO is stage 1's; a run short of orbit has
stage 2's too, so the stage column tells them apart)."""


def thrust_on_flags(
    t_s: np.ndarray, events: Sequence[EventRow], stage_names: Sequence[str]
) -> np.ndarray:
    """Per row, whether an engine is on under the event rule of exit criterion 5: for each
    stage, from the time of its ``ignition`` row (inclusive) to the earliest time, at or
    after it, of its own ``propellant`` row or of a cutoff, ignition_failed or end row
    (exclusive). A stage without an ignition row (a failed ignition, a run that ended
    first) is never on; one without an end row stays on. ``t_s`` on the run's clock [s];
    events in the same clock."""
    on = np.zeros(len(t_s), dtype=bool)
    for name in stage_names:
        lit = [e.t_s for e in events if e.name == IGNITION_EVENT and e.stage == name]
        if not lit:
            continue
        t_on = min(lit)
        ends = [
            e.t_s
            for e in events
            if e.t_s >= t_on
            and ((e.name == PROPELLANT_EVENT and e.stage == name) or e.name in THRUST_OFF_EVENTS)
        ]
        t_off = min(ends) if ends else math.inf
        on |= (t_s >= t_on) & (t_s < t_off)
    return on


# ------------------------------------------------------------------ tank levels


@dataclass(frozen=True)
class TankLevels:
    """The rebuilt tank levels of one run, per row of its RunRows: ``prop_kg`` (stage-1
    and stage-2 propellant left [kg]; after staging the stage-1 series holds its last
    value, the residual that left with the stage), ``fill`` (each over the FULL load of the
    fill-reference block [-]), the step series ``stage_index`` (0 or 1), ``fairing_on``
    and ``thrust_on``; the ``fairing_form`` the flags follow; the run's own ``load_kg``
    per stage, the reference ``full_kg`` per stage and the ``payload_kg`` used (all
    [kg])."""

    prop_kg: tuple[np.ndarray, np.ndarray]
    fill: tuple[np.ndarray, np.ndarray]
    stage_index: np.ndarray
    fairing_on: np.ndarray
    thrust_on: np.ndarray
    fairing_form: str | None
    load_kg: tuple[float, float]
    full_kg: tuple[float, float]
    payload_kg: float

    @property
    def offload_fraction(self) -> tuple[float, float]:
        """Per stage, 1 - load / full load [-]: the share of the reference tank never
        loaded (0 for a full tank)."""
        (l1, l2), (f1, f2) = self.load_kg, self.full_kg
        return (1.0 - l1 / f1, 1.0 - l2 / f2)

    @property
    def not_loaded_kg(self) -> tuple[float, float]:
        """Per stage, full load less the run's load [kg]."""
        (l1, l2), (f1, f2) = self.load_kg, self.full_kg
        return (f1 - l1, f2 - l2)


def tank_levels(
    rows: RunRows,
    masses: VehicleMasses,
    payload_kg: float,
    events: Sequence[EventRow],
    reference: VehicleMasses,
    fairing_form: str | None,
) -> TankLevels:
    """The two propellant series of a run from its recorded mass (design 4.4).

    Inputs: the run's RunRows; ``masses``, the VehicleMasses of the run's OWN vehicle
    block (d1, p1, d2, p2, fairing f); ``payload_kg`` P, the payload the run flew [kg];
    the event rows (run_data.with_drop_masses output, so that a fairing dropped by rule
    at staging has its row); ``reference``, the VehicleMasses of the fill-reference block
    whose full loads the fills are drawn against (the experiment's vehicle for runs, bound
    runs and offload runs; the entry's own block for a case); ``fairing_form``, how the
    fairing left as run_data.fairing_case read it (``fairing_on_flags``).

    Per row, with m = ``m_kg`` and on = fairing attached (``fairing_on_flags``): on a
    stage-1 row prop1 = m - P - d2 - f on - p2 - d1 and prop2 = p2; on a stage-2 row
    prop2 = m - P - d2 - f on and prop1 holds its last stage-1 value. fill_k = prop_k /
    (full load k of ``reference``). Output: TankLevels (kg and fractions). Raises
    ValueError for a vehicle without exactly PLANAR_STAGE_COUNT stages (the planar
    model's two; one formula per stage of the pair) or a stage name the vehicle lacks;
    the checks that can fail on recorded data are ``tank_checks``."""
    if (
        len(masses.stage_names) != PLANAR_STAGE_COUNT
        or len(reference.stage_names) != PLANAR_STAGE_COUNT
    ):
        raise ValueError("tank_levels needs two-stage vehicle blocks (the planar model's)")
    stage_idx = stage_indices(rows.stage, masses.stage_names)
    fairing_on, form = fairing_on_flags(rows, events, masses, stage_idx, fairing_form)
    thrust_on = thrust_on_flags(rows.t_s, events, masses.stage_names)
    d1, d2 = masses.stage_dry_kg
    p1, p2 = masses.stage_propellant_kg
    f = masses.fairing_kg
    m = rows.m_kg
    on_stage1 = stage_idx == 0
    fixed = payload_kg + d2 + f * fairing_on.astype(float)
    prop1 = np.where(on_stage1, m - fixed - p2 - d1, np.nan)
    stage1_rows = np.nonzero(on_stage1)[0]
    held = float(prop1[stage1_rows[-1]]) if len(stage1_rows) else p1
    prop1 = np.where(on_stage1, prop1, held)
    prop2 = np.where(on_stage1, p2, m - fixed)
    full1, full2 = reference.stage_propellant_kg
    return TankLevels(
        prop_kg=(prop1, prop2),
        fill=(prop1 / full1, prop2 / full2),
        stage_index=stage_idx,
        fairing_on=fairing_on,
        thrust_on=thrust_on,
        fairing_form=form,
        load_kg=(p1, p2),
        full_kg=(full1, full2),
        payload_kg=payload_kg,
    )


def rebuilt_mass_kg(levels: TankLevels, masses: VehicleMasses) -> np.ndarray:
    """The stack mass [kg] rebuilt per row from the two tank series and the step flags:
    P + d2 + f fairing_on + prop2 + (d1 + prop1) on stage-1 rows (the page's formula).
    Equal to ``m_kg`` by construction on the rows the series were built from; the
    identity trap of review 01 finding 1, so it is an interpolation check only."""
    d1, d2 = masses.stage_dry_kg
    prop1, prop2 = levels.prop_kg
    on_stage1 = levels.stage_index == 0
    return (
        levels.payload_kg
        + d2
        + masses.fairing_kg * levels.fairing_on.astype(float)
        + prop2
        + np.where(on_stage1, d1 + prop1, 0.0)
    )


# ------------------------------------------------------------------ load-time checks


@dataclass(frozen=True)
class CheckResult:
    """One load-time check: its ``name``, whether it ``passed`` (None: not applicable to
    this run, e.g. no stage-2 end for the residual check), the ``worst`` residual in the
    check's unit (``unit``), the ``tolerance`` it was held to and a one-line ``detail``."""

    name: str
    passed: bool | None
    worst: float | None
    tolerance: float | None
    unit: str
    detail: str

    def as_dict(self) -> dict[str, Any]:
        """The result as JSON-ready data (NaN never written: a NaN residual reads None)."""
        worst = None if self.worst is None or not math.isfinite(self.worst) else self.worst
        return {
            "name": self.name,
            "passed": self.passed,
            "worst": worst,
            "tolerance": self.tolerance,
            "unit": self.unit,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class CheckReport:
    """The load-time checks of one run (``tank_checks``): ``items`` in a fixed order;
    ``passed`` is True when no item failed (a not-applicable item does not fail)."""

    items: tuple[CheckResult, ...]

    @property
    def passed(self) -> bool:
        """True when every applicable item passed."""
        return all(item.passed is not False for item in self.items)

    @property
    def failed(self) -> tuple[str, ...]:
        """Names of the items that failed."""
        return tuple(item.name for item in self.items if item.passed is False)

    def as_dict(self) -> dict[str, Any]:
        """The report as JSON-ready data."""
        return {
            "passed": self.passed,
            "failed": list(self.failed),
            "items": [item.as_dict() for item in self.items],
        }


def _result(
    name: str, worst: float | None, tol: float, unit: str, detail: str, applicable: bool = True
) -> CheckResult:
    """A CheckResult judged by |worst| <= tol (not applicable: passed None)."""
    if not applicable or worst is None:
        return CheckResult(name, None, None, tol, unit, detail)
    passed = bool(math.isfinite(worst) and abs(worst) <= tol)
    return CheckResult(name, passed, float(worst), tol, unit, detail)


def _largest_rise(values: np.ndarray) -> float:
    """The largest increase between consecutive entries of ``values`` (0.0 for fewer than
    two entries or a series that never rises)."""
    if len(values) < 2:
        return 0.0
    return float(max(0.0, float(np.max(np.diff(values)))))


def tank_checks(
    rows: RunRows,
    levels: TankLevels,
    masses: VehicleMasses,
    events: Sequence[EventRow],
    *,
    liftoff_mass_kg: float | None = None,
    recorded_m_res_kg: float | None = None,
    offload_fractions: tuple[float | None, float | None] = (None, None),
) -> CheckReport:
    """The load-time checks of design 4.4 and exit criterion 6 on one run, as a structured
    verdict (never an exception). Inputs: the RunRows, the TankLevels built from them,
    the run's own VehicleMasses, the event rows (with drop masses), the run's metrics
    ``liftoff_mass_kg`` and ``recorded_m_res_kg`` [kg] when it has them, and the offload
    fractions of its case record per stage (None: derived from the two blocks).

    Items, in order: liftoff identity (first-row mass against d1 + p1 + d2 + p2 + f + P,
    and the metric when given, within MASS_TOL_KG); stage-1 tank never rises and stage-2
    tank never rises (TANK_RISE_TOL_KG); no tank step across the two rows of any one time,
    staging and the fairing drop included (TANK_STEP_TOL_KG); stage-2 tank at its load
    before stage-2 ignition (TANK_STEP_TOL_KG); stage-2 tank equal to recorded_m_res_kg on
    the last row of a flight that reached cutoff or depletion (TANK_STEP_TOL_KG; else not
    applicable); stage-1 tank under MASS_TOL_KG at the stage-1 propellant event (else not
    applicable); each tank's start fill equal to one minus its offload fraction
    (FILL_START_TOL). Units: kg, or a fraction of the full load for the fills."""
    d1, d2 = masses.stage_dry_kg
    p1, p2 = masses.stage_propellant_kg
    f = masses.fairing_kg
    prop1, prop2 = levels.prop_kg
    on_stage1 = levels.stage_index == 0
    items: list[CheckResult] = []

    stack = d1 + p1 + d2 + p2 + f + levels.payload_kg
    first = float(rows.m_kg[0]) - stack
    detail = f"first-row m_kg {rows.m_kg[0]:.6f} kg against the block's stack {stack:.6f} kg"
    worst = first
    if liftoff_mass_kg is not None and math.isfinite(liftoff_mass_kg):
        metric = liftoff_mass_kg - stack
        detail += f"; metric liftoff_mass_kg differs by {metric:+.6f} kg"
        worst = max((first, metric), key=abs)
    items.append(_result("liftoff identity", worst, MASS_TOL_KG, "kg", detail))

    rise1 = _largest_rise(prop1[on_stage1])
    items.append(
        _result(
            "stage-1 tank never rises",
            rise1,
            TANK_RISE_TOL_KG,
            "kg",
            f"largest rise between consecutive stage-1 rows {rise1:.3e} kg",
        )
    )
    rise2 = _largest_rise(prop2)
    items.append(
        _result(
            "stage-2 tank never rises",
            rise2,
            TANK_RISE_TOL_KG,
            "kg",
            f"largest rise between consecutive rows {rise2:.3e} kg",
        )
    )

    step = 0.0
    where = "no duplicate time"
    for start, count in duplicate_groups(rows.t_s):
        for tank, series in (("stage-1", prop1), ("stage-2", prop2)):
            span = float(
                np.max(series[start : start + count]) - np.min(series[start : start + count])
            )
            if span > step:
                step = span
                where = f"{tank} tank at t = {rows.t_rel_s[start]:.6f} s after release"
    items.append(
        _result(
            "no tank step at a doubled time",
            step,
            TANK_STEP_TOL_KG,
            "kg",
            f"largest step across the rows of one time {step:.3e} kg ({where})",
        )
    )

    stage2 = masses.stage_names[1]
    lit2 = [e.t_s for e in events if e.name == IGNITION_EVENT and e.stage == stage2]
    before = rows.t_s < min(lit2) if lit2 else np.ones(len(rows), dtype=bool)
    dev = float(np.max(np.abs(prop2[before] - p2))) if before.any() else 0.0
    items.append(
        _result(
            "stage-2 tank at its load before stage-2 ignition",
            dev,
            TANK_STEP_TOL_KG,
            "kg",
            f"largest |prop2 - {p2:.3f} kg| over {int(before.sum())} rows before stage-2 "
            f"ignition {dev:.3e} kg",
        )
    )

    ended = any(
        e.name == CUTOFF_EVENT or (e.name == PROPELLANT_EVENT and e.stage == stage2) for e in events
    )
    has_res = recorded_m_res_kg is not None and math.isfinite(recorded_m_res_kg)
    res = float(prop2[-1]) - float(recorded_m_res_kg) if (ended and has_res) else None
    items.append(
        _result(
            "stage-2 tank equals recorded_m_res_kg on the last row",
            res,
            TANK_STEP_TOL_KG,
            "kg",
            (
                f"last-row prop2 {prop2[-1]:.6f} kg against recorded_m_res_kg {recorded_m_res_kg}"
                if ended and has_res
                else "not applicable: the flight reached neither cutoff nor stage-2 depletion"
                if not ended
                else "not applicable: no recorded_m_res_kg metric"
            ),
            applicable=ended and has_res,
        )
    )

    meco = [
        m
        for m in match_events(rows.t_s, events)
        if m.event.name == PROPELLANT_EVENT
        and m.event.stage == masses.stage_names[0]
        and m.index is not None
    ]
    left = float(prop1[meco[0].index]) if meco else None  # type: ignore[index]
    items.append(
        _result(
            "stage-1 tank empty at the stage-1 propellant event",
            left,
            MASS_TOL_KG,
            "kg",
            f"prop1 at the depletion row {left:.6f} kg"
            if left is not None
            else "not applicable: no stage-1 propellant event",
            applicable=left is not None,
        )
    )

    for k, (fill, load, full, given) in enumerate(
        zip(levels.fill, levels.load_kg, levels.full_kg, offload_fractions, strict=True)
    ):
        expected = (1.0 - given) if given is not None else load / full
        source = "the case record's fraction" if given is not None else "the two blocks' loads"
        gap = float(fill[0]) - expected
        items.append(
            _result(
                f"stage-{k + 1} start fill equals one minus the offload fraction",
                gap,
                FILL_START_TOL,
                "fraction of the full load",
                f"start fill {fill[0]:.9f} against 1 - offload fraction {expected:.9f} "
                f"({source}; load {load:.3f} kg of {full:.3f} kg)",
            )
        )
    return CheckReport(tuple(items))


# ------------------------------------------------------------------ separation state and coast


@dataclass(frozen=True)
class PlanarState:
    """A point-mass state in the planar Earth-centred inertial frame of CLAUDE.md:
    radius ``r_m`` [m], inertial angle ``theta_rad`` [rad, increasing downrange], radial
    speed ``v_r_mps`` and transverse (inertial) speed ``v_theta_mps`` [m/s]."""

    r_m: float
    theta_rad: float
    v_r_mps: float
    v_theta_mps: float

    @property
    def speed_inertial_mps(self) -> float:
        """hypot(v_r, v_theta) [m/s]: the recorded ``speed_inertial_mps`` of the row the
        state was rebuilt from (the check of survey 09 section 2.1)."""
        return math.hypot(self.v_r_mps, self.v_theta_mps)

    def as_array(self) -> np.ndarray:
        """[r, theta, v_r, v_theta] as a float array (the integrator's state)."""
        return np.array([self.r_m, self.theta_rad, self.v_r_mps, self.v_theta_mps], dtype=float)


def planar_omega_p(latitude_rad: float, azimuth_rad: float, include_rotation: bool = True) -> float:
    """The planar Earth rotation rate omega_p = omega_E cos(lat) sin(az) [rad/s]
    (CLAUDE.md; exact for an equatorial east launch), 0 when rotation is off. Inputs in
    radians."""
    if not include_rotation:
        return 0.0
    return OMEGA_EARTH_RADS * math.cos(latitude_rad) * math.sin(azimuth_rad)


def separation_state(
    alt_m: float,
    downrange_m: float,
    speed_rel_mps: float,
    gamma_rel_rad: float,
    t_rel_s: float,
    omega_p_rads: float,
) -> PlanarState:
    """The planar inertial state of a body released from the vehicle at an event row
    (survey 09 section 2; CLAUDE.md's frames). Inputs: the row's altitude above the datum
    R_E [m], Earth-fixed downrange [m], Earth-relative speed [m/s] and flight-path angle
    of the Earth-relative velocity [rad], its time after release [s] and the site's
    omega_p [rad/s]. Output: r = R_E + alt; theta = downrange / R_E + omega_p t (the
    Earth-fixed arc plus the rotation since release: the inverse of the model's downrange
    r_datum (theta - omega_p (t - t_fs)) when the flight start t_fs is the release, as on
    every recorded run; an extended hold shifts theta by the constant omega_p x
    hold_extension_s, which cancels in the coast, whose equations are autonomous in
    theta and whose downrange uses theta - theta0 only); v_r = V sin(gamma); v_theta =
    V cos(gamma) + omega_p r."""
    r = R_EARTH_M + alt_m
    return PlanarState(
        r_m=r,
        theta_rad=downrange_m / R_EARTH_M + omega_p_rads * t_rel_s,
        v_r_mps=speed_rel_mps * math.sin(gamma_rel_rad),
        v_theta_mps=speed_rel_mps * math.cos(gamma_rel_rad) + omega_p_rads * r,
    )


def coast_rhs(t: float, y: np.ndarray) -> list[float]:
    """Right-hand side of the planar two-body coast, CLAUDE.md's ascent equations with
    T = 0 and D = 0: y = [r, theta, v_r, v_theta] (SI, inertial frame); returns [v_r,
    v_theta / r, v_theta^2 / r - mu / r^2, -v_r v_theta / r]. ``t`` [s] is unused (the
    field is autonomous)."""
    r, _theta, v_r, v_theta = y
    return [v_r, v_theta / r, v_theta * v_theta / r - MU_EARTH_M3S2 / (r * r), -v_r * v_theta / r]


def specific_energy_j_per_kg(y: np.ndarray) -> np.ndarray:
    """Specific orbital energy v^2 / 2 - mu / r [J/kg] of states ``y`` ([4, n] or [4])."""
    return 0.5 * (y[2] ** 2 + y[3] ** 2) - MU_EARTH_M3S2 / y[0]


def specific_angular_momentum_m2ps(y: np.ndarray) -> np.ndarray:
    """Specific angular momentum r v_theta [m^2/s] of states ``y`` ([4, n] or [4])."""
    return y[0] * y[3]


@dataclass(frozen=True)
class CoastPath:
    """A display-only vacuum coast from a separation state (``vacuum_coast``): samples
    ``t_s`` [s since separation], ``alt_m`` [m above R_E], ``downrange_m`` [m,
    Earth-fixed] and ``speed_rel_mps`` [m/s, Earth-relative]; the apex (``apex_t_s``,
    ``apex_alt_m``: the separation point itself for a body already descending); the
    impact (``impact_t_s``, ``impact_speed_rel_mps``, ``impact_downrange_m``: None when
    the surface is not reached inside the time limit); ``energy_drift_rel`` and
    ``h_drift_rel``, the largest relative drift of the specific energy and angular
    momentum over the samples [-]; ``nfev``, the right-hand-side calls."""

    t_s: np.ndarray
    alt_m: np.ndarray
    downrange_m: np.ndarray
    speed_rel_mps: np.ndarray
    apex_t_s: float
    apex_alt_m: float
    impact_t_s: float | None
    impact_speed_rel_mps: float | None
    impact_downrange_m: float | None
    energy_drift_rel: float
    h_drift_rel: float
    nfev: int

    @property
    def reached_surface(self) -> bool:
        """True when the coast ended at r = R_E inside the time limit."""
        return self.impact_t_s is not None


def earth_fixed_downrange_m(
    theta_rad: np.ndarray | float,
    theta0_rad: float,
    downrange0_m: float,
    dt_s: np.ndarray | float,
    omega_p_rads: float,
) -> np.ndarray | float:
    """Earth-fixed downrange [m] of a body at inertial angle ``theta_rad`` a time ``dt_s``
    [s] after separation: downrange0 + R_E ((theta - theta0) - omega_p dt), the model's
    downrange convention (r_datum (theta - omega_p (t - t_release)) with the separation
    point as the reference)."""
    return downrange0_m + R_EARTH_M * ((theta_rad - theta0_rad) - omega_p_rads * dt_s)


def earth_relative_speed_mps(y: np.ndarray, omega_p_rads: float) -> np.ndarray:
    """Earth-relative speed [m/s] of states ``y`` ([4, n] or [4]): hypot(v_r, v_theta -
    omega_p r), since the atmosphere co-rotates (CLAUDE.md)."""
    return np.hypot(y[2], y[3] - omega_p_rads * y[0])


def vacuum_coast(
    state: PlanarState,
    downrange0_m: float,
    omega_p_rads: float,
    *,
    t_max_s: float = COAST_T_MAX_S,
    sample_dt_s: float = COAST_SAMPLE_DT_S,
    rtol: float = COAST_RTOL,
    clip_s: float | None = None,
) -> CoastPath:
    """The drag-free two-body coast of a separated body (D-SP2-19; display-only, not model
    output). Inputs: its PlanarState at separation, the Earth-fixed downrange there [m],
    the site's omega_p [rad/s]; the time limit [s], the sample step [s], the relative
    tolerance (DOP853 with COAST_ATOL_* absolute tolerances) and ``clip_s``, the time [s]
    after separation at which the returned samples stop (the run's last time; None: at
    the impact or the time limit). Integrates ``coast_rhs`` with a terminal event at
    r = R_E (descending) and a direction-sensitive event at v_r = 0 for the apex, and
    returns the CoastPath sampled every ``sample_dt_s`` from separation, the last sample
    at the clip or impact instant; the apex, the impact and the drifts are those of the
    whole coast whatever the clip. Downrange and speed are Earth-fixed and Earth-relative
    (``earth_fixed_downrange_m``, ``earth_relative_speed_mps``). Ignores drag, lift,
    attitude and the body's shape: a body falling through the atmosphere would not
    follow this path."""
    _positive("t_max_s", t_max_s)
    _positive("sample_dt_s", sample_dt_s)
    if clip_s is not None and clip_s < 0.0:
        raise ValueError(f"clip_s must not be negative, not {clip_s}")

    def surface(_t: float, y: np.ndarray) -> float:
        return float(y[0] - R_EARTH_M)

    surface.terminal = True  # type: ignore[attr-defined]
    surface.direction = -1.0  # type: ignore[attr-defined]

    def apex(_t: float, y: np.ndarray) -> float:
        return float(y[2])

    apex.direction = -1.0  # type: ignore[attr-defined]

    sol = solve_ivp(
        coast_rhs,
        (0.0, t_max_s),
        state.as_array(),
        method="DOP853",
        rtol=rtol,
        atol=[COAST_ATOL_R_M, COAST_ATOL_THETA_RAD, COAST_ATOL_V_MPS, COAST_ATOL_V_MPS],
        events=[surface, apex],
        dense_output=True,
    )
    if not sol.success:
        raise RuntimeError(f"vacuum coast did not integrate: {sol.message}")
    hit = sol.t_events[0]
    t_end = float(hit[0]) if len(hit) else float(sol.t[-1])
    t_stop = t_end if clip_s is None else min(t_end, clip_s)
    times = np.arange(0.0, t_stop, sample_dt_s)
    if len(times) == 0 or times[-1] < t_stop:
        times = np.append(times, t_stop)
    y = sol.sol(times)
    whole = sol.sol(np.append(np.arange(0.0, t_end, sample_dt_s), t_end))
    e0 = float(specific_energy_j_per_kg(state.as_array()))
    h0 = float(specific_angular_momentum_m2ps(state.as_array()))
    energy = specific_energy_j_per_kg(whole)
    h = specific_angular_momentum_m2ps(whole)
    e_drift = float(np.max(np.abs(energy - e0)) / abs(e0)) if e0 != 0.0 else float("nan")
    h_drift = float(np.max(np.abs(h - h0)) / abs(h0)) if h0 != 0.0 else float("nan")
    apex_hits = sol.t_events[1]
    if len(apex_hits) and state.v_r_mps > 0.0:
        apex_t = float(apex_hits[0])
        apex_alt = float(sol.y_events[1][0][0]) - R_EARTH_M
    else:
        apex_t, apex_alt = 0.0, state.r_m - R_EARTH_M
    downrange = earth_fixed_downrange_m(y[1], state.theta_rad, downrange0_m, times, omega_p_rads)
    speed = earth_relative_speed_mps(y, omega_p_rads)
    reached = len(hit) > 0
    y_end = whole[:, -1]
    end_downrange = earth_fixed_downrange_m(
        float(y_end[1]), state.theta_rad, downrange0_m, t_end, omega_p_rads
    )
    end_speed = earth_relative_speed_mps(y_end, omega_p_rads)
    return CoastPath(
        t_s=times,
        alt_m=y[0] - R_EARTH_M,
        downrange_m=np.asarray(downrange, dtype=float),
        speed_rel_mps=np.asarray(speed, dtype=float),
        apex_t_s=apex_t,
        apex_alt_m=apex_alt,
        impact_t_s=t_end if reached else None,
        impact_speed_rel_mps=float(end_speed) if reached else None,
        impact_downrange_m=float(end_downrange) if reached else None,
        energy_drift_rel=e_drift,
        h_drift_rel=h_drift,
        nfev=int(sol.nfev),
    )


def coast_gap_m(
    state: PlanarState,
    downrange0_m: float,
    omega_p_rads: float,
    dt_s: np.ndarray,
    alt_m: np.ndarray,
    downrange_m: np.ndarray,
    *,
    rtol: float = COAST_RTOL,
) -> float:
    """The largest screen gap [m] between the display-only vacuum coast from ``state`` and
    recorded points of the vehicle's own path: the measured distance the scene quotes
    for each spent stage (not model output). Inputs: the PlanarState at separation, the
    Earth-fixed downrange there [m], the site's omega_p [rad/s]; per recorded point its
    time ``dt_s`` [s after separation, >= 0, non-decreasing; the same time may repeat],
    its altitude ``alt_m`` [m above R_E] and Earth-fixed downrange ``downrange_m`` [m].
    The coast (``coast_rhs``, DOP853 at ``rtol`` with the COAST_ATOL_* absolute
    tolerances, as ``vacuum_coast``) is evaluated exactly at those times through the
    integrator's dense output, never interpolated between samples; both the coast point
    and the recorded point are mapped to the screen (``screen_xy``) and the hypot of
    their x and y differences is taken; the maximum over the points. NaN with no
    points. Raises ValueError for a negative or decreasing time."""
    dt = np.asarray(dt_s, dtype=float).reshape(-1)
    alt = np.asarray(alt_m, dtype=float).reshape(-1)
    down = np.asarray(downrange_m, dtype=float).reshape(-1)
    if not len(dt) == len(alt) == len(down):
        raise ValueError("dt_s, alt_m and downrange_m must have the same length")
    if len(dt) == 0:
        return math.nan
    if np.any(dt < 0.0) or np.any(np.diff(dt) < 0.0):
        raise ValueError("dt_s must be non-negative and non-decreasing")
    times, inverse = np.unique(dt, return_inverse=True)
    if times[-1] > 0.0:
        sol = solve_ivp(
            coast_rhs,
            (0.0, float(times[-1])),
            state.as_array(),
            method="DOP853",
            rtol=rtol,
            atol=[COAST_ATOL_R_M, COAST_ATOL_THETA_RAD, COAST_ATOL_V_MPS, COAST_ATOL_V_MPS],
            t_eval=times,
        )
        if not sol.success:
            raise RuntimeError(f"vacuum coast did not integrate: {sol.message}")
        y = sol.y[:, inverse]
    else:
        y = np.repeat(state.as_array()[:, None], len(dt), axis=1)
    coast_alt = y[0] - R_EARTH_M
    coast_down = earth_fixed_downrange_m(y[1], state.theta_rad, downrange0_m, dt, omega_p_rads)
    xs, ys = screen_xy(coast_alt, np.asarray(coast_down, dtype=float))
    xr, yr = screen_xy(alt, down)
    return float(np.max(np.hypot(np.asarray(xs) - xr, np.asarray(ys) - yr)))


@dataclass(frozen=True)
class KeplerCoast:
    """The closed-form coast of ``kepler_coast``: eccentricity ``e`` [-], semi-major axis
    ``a_m`` [m], apex altitude ``apex_alt_m`` [m above R_E], time of flight to the surface
    ``tof_s`` [s] and the inertial arc swept to it ``impact_arc_rad`` [rad]."""

    e: float
    a_m: float
    apex_alt_m: float
    tof_s: float
    impact_arc_rad: float


def _mean_anomaly(f: float, e: float) -> float:
    """Mean anomaly [rad] at true anomaly ``f`` [rad] on an ellipse of eccentricity e."""
    big_e = 2.0 * math.atan2(
        math.sqrt(1.0 - e) * math.sin(0.5 * f), math.sqrt(1.0 + e) * math.cos(0.5 * f)
    )
    return big_e - e * math.sin(big_e)


def kepler_coast(state: PlanarState) -> KeplerCoast:
    """Closed-form oracle of ``vacuum_coast`` for the tests (survey 09 section 2.5): from a
    PlanarState (inertial frame, SI) the orbit h = r v_theta, E = v^2 / 2 - mu / r,
    p = h^2 / mu, e = sqrt(1 + 2 E h^2 / mu^2), a = -mu / (2 E); the true anomaly from
    e cos f0 = p / r - 1 and e sin f0 = v_r h / mu; impact on the descending branch at
    f_imp = 2 pi - acos((p / R_E - 1) / e); times through the eccentric and mean anomaly.
    Raises ValueError for an orbit that is not an ellipse (E >= 0) or does not reach the
    surface (perigee above R_E, or the state outside the orbit's reach)."""
    r, v_r, v_t = state.r_m, state.v_r_mps, state.v_theta_mps
    h = r * v_t
    energy = 0.5 * (v_r * v_r + v_t * v_t) - MU_EARTH_M3S2 / r
    if energy >= 0.0:
        raise ValueError("kepler_coast needs a bound orbit (specific energy below zero)")
    p = h * h / MU_EARTH_M3S2
    e = math.sqrt(max(0.0, 1.0 + 2.0 * energy * h * h / (MU_EARTH_M3S2 * MU_EARTH_M3S2)))
    a = -MU_EARTH_M3S2 / (2.0 * energy)
    if e <= 0.0 or a * (1.0 - e) >= R_EARTH_M:
        raise ValueError("kepler_coast needs an orbit whose perigee lies below the surface")
    cos_imp = (p / R_EARTH_M - 1.0) / e
    if abs(cos_imp) > 1.0:
        raise ValueError("kepler_coast: the orbit does not cross r = R_E")
    f0 = math.atan2(v_r * h / MU_EARTH_M3S2, p / r - 1.0)
    f_imp = 2.0 * math.pi - math.acos(cos_imp)
    n = math.sqrt(MU_EARTH_M3S2 / a**3)
    dm = (_mean_anomaly(f_imp, e) - _mean_anomaly(f0, e)) % (2.0 * math.pi)
    return KeplerCoast(
        e=e,
        a_m=a,
        apex_alt_m=a * (1.0 + e) - R_EARTH_M,
        tof_s=dm / n,
        impact_arc_rad=f_imp - f0,
    )


# ------------------------------------------------------------------ screen transform and camera


def screen_xy(
    alt_m: np.ndarray | float, downrange_m: np.ndarray | float
) -> tuple[np.ndarray | float, np.ndarray | float]:
    """Screen position [m] of a point at altitude ``alt_m`` [m above R_E] and Earth-fixed
    downrange ``downrange_m`` [m]: x = (R_E + alt) sin(d / R_E), y = (R_E + alt)
    cos(d / R_E) - R_E, in a plane through the launch site with x downrange and y up
    (the site at the origin, Earth's surface a circle through it). A y-down canvas negates
    y. Scalars or arrays."""
    phi = downrange_m / R_EARTH_M
    radius = R_EARTH_M + alt_m
    return radius * np.sin(phi), radius * np.cos(phi) - R_EARTH_M


def screen_angle_rad(
    pitch_rad: np.ndarray | float, downrange_m: np.ndarray | float
) -> np.ndarray | float:
    """The drawn angle [rad] of a body at pitch ``pitch_rad`` above its local horizontal
    and downrange ``downrange_m`` [m], counter-clockwise from +x on a y-up screen:
    pitch - d / R_E (the local horizontal tilts by the arc). A y-down canvas rotates by
    the negative of this."""
    return pitch_rad - downrange_m / R_EARTH_M


def running_extent_m(
    alt_m: np.ndarray,
    downrange_m: np.ndarray,
    *,
    floor_m: float,
    body_length_m: float,
    aspect: float = 1.0,
) -> np.ndarray:
    """The camera's running extent E [m] per sample: the running maximum over time of
    hypot(max(alt, 0) - floor + body length, |downrange| / aspect), with ``floor_m`` the
    lowest altitude the view must hold (the shaft floor, <= 0 [m]), ``body_length_m`` the
    stack length [m] (so the nose stays in view) and ``aspect`` the panel width over its
    height [-]. A running maximum: the view never shrinks (D-SP2-35, survey 09 section 4)."""
    _positive("aspect", aspect)
    height = np.maximum(np.asarray(alt_m, dtype=float), 0.0) - floor_m + body_length_m
    width = np.abs(np.asarray(downrange_m, dtype=float)) / aspect
    return np.maximum.accumulate(np.hypot(height, width))


def view_height_m(
    extent_m: np.ndarray | float, min_view_height_m: float, margin: float
) -> np.ndarray | float:
    """The camera law (design 4.5): the view height H [m] = sqrt(H_MIN^2 + (margin E)^2)
    for a running extent E [m], ``min_view_height_m`` H_MIN [m] (scene.yaml
    camera.min_view_height_m) and ``margin`` [-] (camera.margin): a smooth maximum, so
    the launch view blends into the growing one without a corner, and a pure function of
    the scene time, so scrubbing and playing give the same view."""
    return np.sqrt(min_view_height_m**2 + (margin * extent_m) ** 2)


# ------------------------------------------------------------------ row selection (D-SP2-16)


@dataclass(frozen=True)
class SelectionField:
    """One interpolated series of the row selection: its ``name``, its ``values`` per CSV
    row (any unit) and the tolerance every row must meet, the larger of ``tol_rel``
    times |value| and ``tol_abs`` (the same unit)."""

    name: str
    values: np.ndarray
    tol_abs: float
    tol_rel: float = 0.0

    def tolerance(self) -> np.ndarray:
        """The per-row tolerance max(tol_rel |value|, tol_abs)."""
        return np.maximum(self.tol_rel * np.abs(self.values), self.tol_abs)


@dataclass(frozen=True)
class WorstResidual:
    """The worst interpolation residual of one field over the CSV rows: ``abs`` in the
    field's unit, ``frac`` as a fraction of that row's tolerance, at row ``index`` and
    time ``t_s`` [s after release]."""

    abs: float
    frac: float
    index: int
    t_s: float

    def as_dict(self) -> dict[str, float | int]:
        """The residual as JSON-ready data."""
        return {"abs": self.abs, "frac_of_tol": self.frac, "index": self.index, "t": self.t_s}


@dataclass(frozen=True)
class RowSelection:
    """The scene's time grid of one run (``select_rows``): the selected CSV row
    ``indices`` (sorted, both rows of every doubled time), the insertion ``passes`` run,
    whether the selection ``converged`` (every CSV row within ``half`` of every field's
    tolerance) and the ``worst`` residual per field name."""

    indices: np.ndarray
    passes: int
    converged: bool
    worst: dict[str, WorstResidual]

    def as_dict(self) -> dict[str, Any]:
        """The selection report as JSON-ready data (the indices are not repeated)."""
        return {
            "samples": len(self.indices),
            "passes": self.passes,
            "converged": self.converged,
            "worst": {name: w.as_dict() for name, w in self.worst.items()},
        }


def base_selection(
    t_rel_s: np.ndarray,
    event_indices: Sequence[int],
    *,
    early_end_s: float = SELECTION_EARLY_END_S,
    early_step: int = SELECTION_EARLY_STEP,
    late_step: int = SELECTION_LATE_STEP,
) -> np.ndarray:
    """The first selection of D-SP2-16 as sorted unique row indices: the first and last
    rows, both rows of every doubled time (``duplicate_groups``), every event row
    (``event_indices``), every ``early_step``-th row while t < ``early_end_s`` [s after
    release] and every ``late_step``-th row after."""
    n = len(t_rel_s)
    keep = {0, n - 1}
    for start, count in duplicate_groups(t_rel_s):
        keep.update(range(start, start + count))
    keep.update(int(i) for i in event_indices if 0 <= int(i) < n)
    stride = np.where(t_rel_s < early_end_s, early_step, late_step)
    keep.update(int(i) for i in np.nonzero(np.arange(n) % stride == 0)[0])
    return np.array(sorted(keep), dtype=int)


def interpolation_residuals(t: np.ndarray, values: np.ndarray, selected: np.ndarray) -> np.ndarray:
    """|linear interpolation of ``values`` between the nearest selected rows - value| at
    every row (0 at a selected row). ``selected`` are sorted row indices that include the
    first and last rows; two rows of one time are either both selected or both not, so a
    non-selected row lies strictly between its neighbours in time. Any unit."""
    n = len(t)
    mask = np.zeros(n, dtype=bool)
    mask[selected] = True
    idx = np.arange(n)
    prev = np.maximum.accumulate(np.where(mask, idx, 0))
    nxt = np.minimum.accumulate(np.where(mask, idx, n - 1)[::-1])[::-1]
    span = t[nxt] - t[prev]
    w = np.divide(t - t[prev], span, out=np.zeros(n), where=span > 0.0)
    guess = values[prev] + w * (values[nxt] - values[prev])
    residual = np.abs(guess - values)
    residual[mask] = 0.0
    return residual


def _stretches(flags: np.ndarray) -> list[tuple[int, int]]:
    """(start, stop) of every maximal run of True in ``flags`` (stop exclusive)."""
    out: list[tuple[int, int]] = []
    idx = np.nonzero(flags)[0]
    if len(idx) == 0:
        return out
    start = prev = int(idx[0])
    for j in idx[1:]:
        if int(j) != prev + 1:
            out.append((start, prev + 1))
            start = int(j)
        prev = int(j)
    out.append((start, prev + 1))
    return out


def select_rows(
    t_rel_s: np.ndarray,
    fields: Sequence[SelectionField],
    event_indices: Sequence[int],
    *,
    half: float = SELECTION_HALF,
    max_passes: int = SELECTION_MAX_PASSES,
    early_end_s: float = SELECTION_EARLY_END_S,
    early_step: int = SELECTION_EARLY_STEP,
    late_step: int = SELECTION_LATE_STEP,
) -> RowSelection:
    """The scene's time grid of one run (D-SP2-16): ``base_selection``, then, in bounded
    passes, the row with the worst residual-over-tolerance of each contiguous stretch of
    rows outside ``half`` of its tolerance is inserted, until every CSV row of every
    field is within it under linear interpolation of the selected rows
    (``interpolation_residuals``) or ``max_passes`` is reached (then ``converged`` is
    False). Inputs: times [s after release] of every CSV row (in file order), the
    SelectionFields, the event row indices and the grid settings. Step series are never
    interpolated and take no part here."""
    if not fields:
        raise ValueError("select_rows needs at least one field")
    selected = base_selection(
        t_rel_s, event_indices, early_end_s=early_end_s, early_step=early_step, late_step=late_step
    )
    tolerances = {f.name: f.tolerance() for f in fields}
    passes = 0
    converged = False
    worst: dict[str, WorstResidual] = {}
    while True:
        ratio = np.zeros(len(t_rel_s))
        worst = {}
        for field in fields:
            residual = interpolation_residuals(t_rel_s, field.values, selected)
            frac = residual / tolerances[field.name]
            i = int(np.argmax(frac))
            worst[field.name] = WorstResidual(
                float(residual[i]), float(frac[i]), i, float(t_rel_s[i])
            )
            ratio = np.maximum(ratio, frac)
        bad = ratio > half
        if not bad.any():
            converged = True
            break
        if passes >= max_passes:
            break
        added = [start + int(np.argmax(ratio[start:stop])) for start, stop in _stretches(bad)]
        selected = np.unique(np.concatenate([selected, np.array(added, dtype=int)]))
        passes += 1
    return RowSelection(indices=selected, passes=passes, converged=converged, worst=worst)


def rebuilt_mass_residual_kg(
    rows: RunRows,
    levels: TankLevels,
    masses: VehicleMasses,
    selected: np.ndarray,
    *,
    time_decimals: int,
    tank_decimals: int,
) -> np.ndarray:
    """|rebuilt stack mass - m_kg| [kg] at every CSV row when the page interpolates the
    ROUNDED tank samples (``tank_decimals``) at the ROUNDED selected times
    (``time_decimals`` [s]) between the nearest selected rows and adds the row's own step
    flags (the interpolation and rounding check of exit criterion 6). Each tank is
    interpolated on its own; the flags are exact at every CSV row by construction."""
    t = np.round(rows.t_rel_s, time_decimals)
    prop1, prop2 = (np.round(p, tank_decimals) for p in levels.prop_kg)
    n = len(t)
    mask = np.zeros(n, dtype=bool)
    mask[selected] = True
    idx = np.arange(n)
    prev = np.maximum.accumulate(np.where(mask, idx, 0))
    nxt = np.minimum.accumulate(np.where(mask, idx, n - 1)[::-1])[::-1]
    span = t[nxt] - t[prev]
    w = np.divide(t - t[prev], span, out=np.zeros(n), where=span > 0.0)
    p1 = prop1[prev] + w * (prop1[nxt] - prop1[prev])
    p2 = prop2[prev] + w * (prop2[nxt] - prop2[prev])
    page = TankLevels(
        prop_kg=(p1, p2),
        fill=levels.fill,
        stage_index=levels.stage_index,
        fairing_on=levels.fairing_on,
        thrust_on=levels.thrust_on,
        fairing_form=levels.fairing_form,
        load_kg=levels.load_kg,
        full_kg=levels.full_kg,
        payload_kg=levels.payload_kg,
    )
    return np.abs(rebuilt_mass_kg(page, masses) - rows.m_kg)


# ------------------------------------------------------------------ held attitude (D-SP2-17)

ATTITUDE_PHASES = (HOLD_KIND, ASSIST_KIND)
"""Phases in which the model defines an attitude without thrust: the hold (vertical on
the pad) and the track (the track angle)."""
UNPOWERED_PHASES = (COAST_PRE_IGN, COAST_STAGING, COAST)
"""Phases in which the model has no thrust direction, whatever the time-based thrust flag
says at an ignition instant: the pre-map row of an ignition pair is still the coast."""


def attitude_defined(phase: Sequence[str], thrust_on: np.ndarray) -> np.ndarray:
    """Per row, whether the model defines an attitude (D-SP2-17): the row in the hold or
    on the track (ATTITUDE_PHASES), or thrust on at a row outside the unpowered phases
    (UNPOWERED_PHASES). A row in an unpowered phase is never defined, including the
    pre-map row at an ignition time, which the time-based ``thrust_on`` rule already
    marks on while its recorded thrust is 0 N and its ``pitch_rad`` is the coast's v_rel
    angle: the held angle must run up to the ignition step, not dip before it. Elsewhere
    ``pitch_rad`` follows v_rel and a point mass has no body axis."""
    held = np.array([p in ATTITUDE_PHASES for p in phase], dtype=bool)
    coast = np.array([p in UNPOWERED_PHASES for p in phase], dtype=bool)
    return held | (np.asarray(thrust_on, dtype=bool) & ~coast)


def held_screen_angle_rad(
    pitch_rad: np.ndarray, downrange_m: np.ndarray, defined: np.ndarray
) -> np.ndarray:
    """The drawn screen angle [rad, y up, counter-clockwise from +x] per row: pitch - d /
    R_E (``screen_angle_rad``) where the attitude is ``defined`` (``attitude_defined``),
    else the last defined screen angle held (the screen angle, not the pitch: the local
    horizontal keeps tilting under a held body). A row with no defined row before it
    keeps its own screen angle. The model's instant steps at the kick and at stage-2
    ignition pass through as recorded (D-SP2-17, review 01 finding 11)."""
    angle = np.asarray(
        screen_angle_rad(np.asarray(pitch_rad, dtype=float), downrange_m), dtype=float
    )
    defined = np.asarray(defined, dtype=bool)
    out = angle.copy()
    last: float | None = None
    for i in range(len(out)):
        if defined[i]:
            last = float(angle[i])
        elif last is not None:
            out[i] = last
    return out


__all__ = [
    "ALT_TOL_MIN_M",
    "ALT_TOL_REL",
    "ATTITUDE_PHASES",
    "COAST_ATOL_R_M",
    "COAST_ATOL_THETA_RAD",
    "COAST_ATOL_V_MPS",
    "COAST_RTOL",
    "COAST_SAMPLE_DT_S",
    "COAST_T_MAX_S",
    "DOWNRANGE_TOL_MIN_M",
    "DOWNRANGE_TOL_REL",
    "EVENT_TIME_TOL_S",
    "FILL_START_TOL",
    "IGNITION_EVENT",
    "MASS_TOL_KG",
    "PITCH_TOL_DEG",
    "PITCH_TOL_RAD",
    "PLUME_TOL",
    "PROPELLANT_EVENT",
    "SELECTION_EARLY_END_S",
    "SELECTION_EARLY_STEP",
    "SELECTION_HALF",
    "SELECTION_LATE_STEP",
    "SELECTION_MAX_PASSES",
    "TANK_RISE_TOL_KG",
    "TANK_STEP_TOL_KG",
    "THRUST_OFF_EVENTS",
    "UNPOWERED_PHASES",
    "CameraConfig",
    "CheckReport",
    "CheckResult",
    "CoastPath",
    "DisplayGeometry",
    "EventMatch",
    "GenericShapeConfig",
    "KeplerCoast",
    "PadShapeConfig",
    "PlanarState",
    "RowSelection",
    "RunRows",
    "SceneDisplayConfig",
    "SelectionField",
    "SiloShapeConfig",
    "TankLevels",
    "VehicleDisplayConfig",
    "VehicleShapeConfig",
    "WorstResidual",
    "attitude_defined",
    "base_selection",
    "body_diameter_from_area_m",
    "coast_gap_m",
    "coast_rhs",
    "duplicate_groups",
    "earth_fixed_downrange_m",
    "earth_relative_speed_mps",
    "fairing_on_flags",
    "generic_geometry",
    "held_screen_angle_rad",
    "interpolation_residuals",
    "kepler_coast",
    "match_events",
    "planar_omega_p",
    "quantity_provenance",
    "rebuilt_mass_kg",
    "rebuilt_mass_residual_kg",
    "running_extent_m",
    "screen_angle_rad",
    "screen_xy",
    "select_rows",
    "separation_state",
    "specific_angular_momentum_m2ps",
    "specific_energy_j_per_kg",
    "stage_indices",
    "tank_checks",
    "tank_levels",
    "thrust_on_flags",
    "vacuum_coast",
    "view_height_m",
]
