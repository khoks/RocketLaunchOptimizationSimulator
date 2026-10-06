"""The local app's form, pure (SP2 step A4; docs/phases/inputs/2026-10-05-SP2-design.md,
section 4.7, decisions D-SP2-07, 10, 12, 25, 27, 31): what a launch request may say, the
experiment dict it becomes, the values the page shows live and the one-line refusals.
Nothing here reads or writes a file: ``app.load_basis`` reads the committed files and
hands their raw dicts to ``make_basis``.

- ``make_basis(offload_experiment, screening_experiment, vehicle, commit=None) -> Basis``:
  the frozen record of experiments/silo_offload_2d.yaml, experiments/silo_screening_2d.yaml
  and the vehicle file they name, as loaded (three search numbers are strings in the YAML,
  so the blocks are copied, never re-typed): the six shared blocks, the baseline, the
  vehicle path and dict, the offload energy block, the preset fragments, the committed
  runs and cases resolved, for the naming rule, and the commit the files were read from
  (None: no name is kept as committed).
- ``parse_request(obj) -> Form | Refusal``: whitelisted keys only (FIELDS); choices from
  fixed enumerations; real booleans; numbers whose type is int or float (never bool), an
  int bounded in magnitude before it is converted, finite, inside the form's range (-0.0
  kept as 0.0); a silo push whose net acceleration and exit speed, typed or derived, are
  both inside their ranges. The request never carries a run, case or experiment name; a
  refusal never echoes an unknown key or a value.
- ``preset_form(basis, name)``, ``presets(basis)``: the presets of design 4.7, each a Form
  built from the committed fragments, with a plain label and an expected duration range
  with its note.
- ``build_experiment(basis, form) -> dict``: the experiment ``app`` (label exploratory),
  the shared blocks and the baseline verbatim, at most one variant, at most one offload
  case; on a basis read from a commit, a committed run or case name is kept only when its
  resolved RunConfig and vehicle equal the committed one (D-SP2-31), and then with its
  committed fragment verbatim, else ``silo`` and ``silo_<mode>``; ``committed_names``
  lists the names kept (a reproduction).
- ``derived(resolved) -> dict``: exit speed or net acceleration, push time, felt g,
  braking and facility length, the drag-free apex, the ramp start four ways, the run
  names and the expected duration; a FormError rather than a value that is not finite.
- ``refusal_text(exc) -> (field, line)``: one line of at most MAX_REFUSAL_CHARS from a
  pydantic ValidationError (``errors(include_url=False, include_input=False)``), a
  FormError or the first line of a ValueError; never the full text of a ValidationError.

Units: the form's fields carry the config's units (m, s, t, g0, m/s); derived values are
SI except ``net_accel_g`` and ``felt_g`` [g0]. Frame: the flat track frame of the push
(vertical silo, x up the shaft) and, after release, the drag-free coast at the track's
constant g_eff (display estimates only; the model flies mu/r^2 with drag).
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Any

from pydantic import ValidationError

from launchsim.assist import build_assist
from launchsim.assist.constant_accel import ConstantAccelAssist
from launchsim.atmosphere import ambient_scalar
from launchsim.compare import ANCHOR_NAMES
from launchsim.config import (
    EXPLORATORY_LABEL,
    HEIGHT_METHOD_CLOSED_FORM,
    HEIGHT_METHOD_EVENT,
    IMPACT_END,
    OFFLOAD_FIXED_KEYS,
    OFFLOAD_FIXED_MODES,
    OFFLOAD_GROSS_MODES,
    PLANNED_MODELS,
    SEARCHED_FIGURES,
    SHARED_KEYS,
    ResolvedExperiment,
    ResolvedOffloadCase,
    ResolvedRun,
    merge_run_dicts,
    offload_run_names,
    resolve_experiment,
)
from launchsim.constants import MU_EARTH_M3S2
from launchsim.dynamics import InverseSquareGravity
from launchsim.phases.planar import PlanarEnvironment
from launchsim.phases.prelude import IgnitionSpec, resolve_stage_ignitions
from launchsim.units import from_g, to_g, to_percent
from launchsim.vehicle import OFFLOAD_MODES

Number = int | float
"""A form number as the request gave it (an int stays an int, so a committed fragment
sent back unchanged keeps its raw type)."""

# ------------------------------------------------------------------ names and choices

APP_EXPERIMENT_NAME = "app"
"""The experiment name of every launch: results/app/<UTC timestamp>/ (D-SP2-03)."""
NEUTRAL_SILO_VARIANT = "silo"
"""The variant name of a silo launch that equals no committed variant (D-SP2-31)."""
NEUTRAL_PAD_VARIANT = "pad_variant"
"""The variant name of a pad launch whose ignition differs from the baseline's and that
equals no committed variant (pad_instant is the committed one)."""
NEUTRAL_CASE_PREFIX = "silo"
"""Prefix of the name of an offload case that equals no committed case: silo_<mode>."""
SILO_FRAGMENT_VARIANT = "silo_cold"
"""The committed variant of experiments/silo_offload_2d.yaml whose assist block gives the
silo details the form does not edit (brake, drive efficiency, shaft, track)."""

SITE_PAD = "pad"
SITE_SILO = "silo"
SITES = (SITE_PAD, SITE_SILO)
"""Launch site: the pad alone (the baseline, or a pad variant with another ignition) or
the vertical constant_accel silo."""
PUSH_KEYS = ("net_accel_g", "exit_speed_mps")
"""How the push is stated besides the depth (config.ASSIST_KEY_FAMILIES, one key each)."""
RAMP_TIME_RELEASE = "time_release"
RAMP_TIME_PUSH_START = "time_push_start"
RAMP_DEPTH = "depth"
RAMP_SPEED = "speed"
RAMP_HEIGHT_EVENT = "height_event"
RAMP_HEIGHT_CLOSED_FORM = "height_closed_form"
RAMP_BY = (
    RAMP_TIME_RELEASE,
    RAMP_TIME_PUSH_START,
    RAMP_DEPTH,
    RAMP_SPEED,
    RAMP_HEIGHT_EVENT,
    RAMP_HEIGHT_CLOSED_FORM,
)
"""How the stage-1 ramp start is stated (config.IGNITION_KEY_FAMILIES): a time from the
release or from the push start, a depth below the mouth, a speed on the push, a height
above the mouth by the altitude event or by the closed form."""
RAMP_VALUE_KEYS: dict[str, str] = {
    RAMP_TIME_RELEASE: "t_ign_s",
    RAMP_TIME_PUSH_START: "t_ign_s",
    RAMP_DEPTH: "at_depth_m",
    RAMP_SPEED: "at_speed_mps",
    RAMP_HEIGHT_EVENT: "at_height_m",
    RAMP_HEIGHT_CLOSED_FORM: "at_height_m",
}
"""The form field (and config key) that holds the value of each ramp-start way."""
RELEASE_REFERENCE = "release"
PUSH_START_REFERENCE = "push_start"
"""The two values of config.IgnitionConfig.reference."""
STARTUP_VEHICLE = "vehicle_default"
STARTUP_STEP = "step"
STARTUP_RAMP = "ramp"
STARTUP_LAG = "lag"
STARTUPS = (STARTUP_VEHICLE, STARTUP_STEP, STARTUP_RAMP, STARTUP_LAG)
"""Stage-1 startup: the vehicle file's own shape, or an override (step, ramp, lag)."""
STARTUP_VALUE_KEYS: dict[str, str] = {STARTUP_RAMP: "t_ramp_s", STARTUP_LAG: "tau_s"}
"""The form field that holds the duration of a ramp or lag override."""
PROPELLANT_FULL = "full"
PROPELLANT_FIXED = "fixed"
PROPELLANT_SOLVE = "solve"
PROPELLANTS = (PROPELLANT_FULL, PROPELLANT_FIXED, PROPELLANT_SOLVE)
"""Full load (no offload block), an imposed offload or a solved one (D-SP2-07)."""
FIXED_KEYS = OFFLOAD_FIXED_KEYS
"""How an imposed offload is stated (config.OFFLOAD_FIXED_KEYS)."""
SOLVE_MODES = OFFLOAD_MODES
"""The modes a solved offload takes propellant along (vehicle.OFFLOAD_MODES)."""
ADVANCED_SOLVE_MODES = tuple(m for m in SOLVE_MODES if m not in OFFLOAD_GROSS_MODES)
ADVANCED_FIXED_KEYS = tuple(
    k for k in FIXED_KEYS if OFFLOAD_FIXED_MODES[k] not in OFFLOAD_GROSS_MODES
)
"""The stage-2 and both-stage forms, offered only with ``advanced: true`` (D-SP2-07): a
property of the vehicle model, quoted net of the pad control when solved."""
ADVANCED_SOLVE_READING = (
    "quoted net of its pad control: a property of the vehicle model, not of the assist"
)
"""How a stage-2 or both-stage solve reads in a form's label (D-SP2-07, design 4.7)."""
ADVANCED_FIXED_READING = (
    "a property of the vehicle model, not netted: an imposed offload has no pad control"
)
"""How an imposed stage-2 or both-stage offload reads in a form's label (design 4.7)."""
CASE_MODE_TAGS: dict[str, str] = {"stage1": "s1", "stage2": "s2", "both": "both"}
"""Short tag of each offload mode in a neutral case name (SP1's names: silo_cold_s1)."""
FIXED_KEY_TAGS: dict[str, str] = {
    "stage1_t": "fix{}t",
    "stage1_fraction": "fix{}pct",
    "stage2_t": "s2fix{}t",
    "stage2_fraction": "s2fix{}pct",
    "both_fraction": "bothfix{}pct",
}
"""The tag of an imposed offload in a neutral case name, {} replaced by the mass [t] or
the percentage (SP1's names: silo_cold_fix5pct)."""
ASSIST_UNION_TAGS = frozenset({"none", "constant_accel", *PLANNED_MODELS})
"""Discriminator tags pydantic puts into an error location after ``assist``; dropped
from the location a refusal names."""

# ------------------------------------------------------------------ the form's fields


@dataclass(frozen=True)
class FieldSpec:
    """One request field: ``kind`` (choice, number or bool), a plain ``label``, its
    ``unit`` (config units; empty for none), the ``config_key`` it fills, the allowed
    ``choices`` of a choice field and the closed range [``lo``, ``hi``] of a number in
    its unit."""

    kind: str
    label: str
    unit: str
    config_key: str
    choices: tuple[str, ...] = ()
    lo: float | None = None
    hi: float | None = None


CHOICE = "choice"
NUMBER = "number"
BOOLEAN = "bool"

PRESET_BASELINE = "baseline"
PRESET_VARIANT = "variant"
PRESET_CASE = "case"
PRESETS: tuple[tuple[str, str], ...] = (
    ("pad", PRESET_BASELINE),
    ("silo_cold", PRESET_VARIANT),
    ("silo_hot_ramp_on_track", PRESET_VARIANT),
    ("silo_cold_200m", PRESET_VARIANT),
    ("silo_cold_s1", PRESET_CASE),
    ("silo_cold_fix5pct", PRESET_CASE),
    ("silo_cold_fix10pct", PRESET_CASE),
    ("silo_cold_s1_dry+2t", PRESET_CASE),
    ("silo_cold_s1_dry+4t", PRESET_CASE),
    ("silo_cold_s1_dry+8.1t", PRESET_CASE),
    ("silo_cold_lag", PRESET_VARIANT),
    ("silo_hot_full", PRESET_VARIANT),
    ("silo_hot_full_impinged", PRESET_VARIANT),
    ("silo_sled_22t", PRESET_VARIANT),
    ("silo_failed", PRESET_VARIANT),
    ("silo_instant", PRESET_VARIANT),
    ("pad_instant", PRESET_VARIANT),
)
"""The presets of design 4.7, in the page's order, each a committed name (the baseline,
a variant of experiments/silo_offload_2d.yaml or silo_screening_2d.yaml, or a case of the
offload block) and what it names. No number is typed here: each preset's form is read
from its committed fragment (``preset_form``)."""
PRESET_NAMES = tuple(name for name, _ in PRESETS)
DEFAULT_PRESET = "silo_cold"
"""The preset the page opens with (design 4.7)."""

# The form's ranges, in each field's config unit: generous bounds that close the
# config's holes (survey 03 section 3.3: inf and absurd magnitudes are accepted there,
# t_ign_s, the exit altitude and the penalty have no bound) and give the page its
# ranges; within them the simulator's own rules decide (a depth below the stroke, a
# speed below the exit speed, a height below the drag-free apex, a fraction in (0, 1),
# a mass below the load). The push has positive lower ends (a denormal stroke or
# acceleration passes the config's gt=0 and hangs or crashes the track phase), and its
# net acceleration and exit speed are checked together however the push is typed
# (``check_form``: v^2 / (2 L) of a typed exit speed, sqrt(2 a L) of a typed
# acceleration, each inside its range). The startup ramp time and lag time constant have
# positive lower ends too (a small lag slows every flight, a denormal ramp or lag crashes
# it; a zero is the step startup). The other lower ends are the config's own bounds
# where it has one (inclusive, so that its message is the one shown at the edge).
STROKE_RANGE_M = (1.0, 1000.0)
"""Silo depth [m]: the committed sweeps span 25-300 m."""
NET_ACCEL_MIN_G = 0.01
"""The lowest net acceleration [g0] of a push, typed or derived from an exit speed; the
push must also give at least the exit-speed range's 1 m/s (0.01 g0 needs a stroke of at
least 5.1 m). Fixed-guidance flights of 0.0102 g0 over 1000 m (ramp start 10 s before the
push start) and 20 g0 over 637 m took under 1.1 s each (A4 review)."""
NET_ACCEL_RANGE_G = (NET_ACCEL_MIN_G, 20.0)
"""Net acceleration [g0]: the committed sweeps reach 5 g0, sweep 2 of the offload 6 g0."""
EXIT_SPEED_RANGE_MPS = (1.0, 500.0)
"""Exit speed [m/s], typed or derived from a net acceleration: the committed sweeps reach
133 m/s (the README's range is 10-300)."""
CARRIAGE_RANGE_T = (0.0, 100.0)
"""Carriage mass [t]: silo_sled_22t carries 22 t."""
FRACTION_RANGE = (0.0, 1.0)
"""Exhaust impingement fraction [-] (the config's own bounds)."""
IGNITION_TIME_RANGE_S = (-10.0, 60.0)
"""Ramp start time [s] from its reference: the committed runs use -2 to 1 s."""
DEPTH_RANGE_M = (0.0, 1000.0)
"""Ramp start depth [m] (the simulator refuses one deeper than the stroke)."""
SPEED_RANGE_MPS = (0.0, 500.0)
"""Ramp start speed [m/s] (the simulator refuses one above the exit speed)."""
HEIGHT_RANGE_M = (0.0, 10000.0)
"""Ramp start height [m] (the simulator refuses one at or above the drag-free apex)."""
RAMP_TIME_RANGE_S = (1.0e-3, 20.0)
"""Startup ramp time [s]: the vehicle's ramp is 2 s, the sweeps reach 3 s. The lower end
excludes a denormal ramp (5e-324 s overflows the thrust fraction dt / t_ramp, vehicle.py
thrust_fraction); an instant start is the step startup."""
LAG_TAU_RANGE_S = (0.5, 20.0)
"""Startup lag time constant [s]: the committed lags are 1-3 s. The integrator caps its
step at tau / lag_steps_per_tau for the whole burn (prelude.max_step_cap), so one
fixed-guidance flight took 1.0 s at tau 1 s, 1.8 s at 0.5 s, 8.7 s at 0.1 s and 86 s at
0.01 s (A4 review), and 5e-324 crashes; an instant start is the step startup."""
OFFLOAD_VALUE_RANGE = (0.0, 1000.0)
"""Imposed offload [t or fraction]: a fraction must lie in (0, 1) and a mass below the
stage's load (the simulator's rules)."""
PREOFFLOAD_RANGE_T = (0.0, 1000.0)
"""Stage-2 pre-offload [t]; 0 means none (the key is left out)."""
PENALTY_RANGE_T = (0.0, 100.0)
"""Assumed stage-1 dry mass added [t]; 0 means none (the key is left out). SP1's rows
reach 8.1 t."""
INT_MAGNITUDE_MAX = 10**15
"""The largest |int| a number field accepts before converting it to a float (a 400-digit
int would overflow the conversion)."""
MAX_REFUSAL_CHARS = 300
"""A refusal is one line of at most this many characters."""
CHOICES_LISTED_MAX = 6
"""A choice refusal lists the allowed values only when there are at most this many."""

FIELDS: dict[str, FieldSpec] = {
    "site": FieldSpec(CHOICE, "Launch site", "", "assist.model", SITES),
    "stroke_m": FieldSpec(
        NUMBER, "Silo depth (stroke)", "m", "assist.stroke_m", (), *STROKE_RANGE_M
    ),
    "push_by": FieldSpec(CHOICE, "Push stated by", "", "assist", PUSH_KEYS),
    "net_accel_g": FieldSpec(
        NUMBER, "Net acceleration", "g0", "assist.net_accel_g", (), *NET_ACCEL_RANGE_G
    ),
    "exit_speed_mps": FieldSpec(
        NUMBER, "Exit speed", "m/s", "assist.exit_speed_mps", (), *EXIT_SPEED_RANGE_MPS
    ),
    "carriage_mass_t": FieldSpec(
        NUMBER, "Carriage mass", "t", "assist.carriage_mass_t", (), *CARRIAGE_RANGE_T
    ),
    "exhaust_impingement_fraction": FieldSpec(
        NUMBER,
        "Exhaust impingement fraction",
        "",
        "assist.exhaust_impingement_fraction",
        (),
        *FRACTION_RANGE,
    ),
    "ramp_by": FieldSpec(CHOICE, "Ramp start stated by", "", "ignition.stage1", RAMP_BY),
    "t_ign_s": FieldSpec(
        NUMBER, "Ramp start time", "s", "ignition.stage1.t_ign_s", (), *IGNITION_TIME_RANGE_S
    ),
    "at_depth_m": FieldSpec(
        NUMBER,
        "Ramp start depth below the mouth",
        "m",
        "ignition.stage1.at_depth_m",
        (),
        *DEPTH_RANGE_M,
    ),
    "at_speed_mps": FieldSpec(
        NUMBER,
        "Ramp start speed on the push",
        "m/s",
        "ignition.stage1.at_speed_mps",
        (),
        *SPEED_RANGE_MPS,
    ),
    "at_height_m": FieldSpec(
        NUMBER,
        "Ramp start height above the mouth",
        "m",
        "ignition.stage1.at_height_m",
        (),
        *HEIGHT_RANGE_M,
    ),
    "startup": FieldSpec(CHOICE, "Stage-1 startup", "", "ignition.stage1.startup", STARTUPS),
    "t_ramp_s": FieldSpec(
        NUMBER,
        "Startup ramp time",
        "s",
        "ignition.stage1.startup.t_ramp_s",
        (),
        *RAMP_TIME_RANGE_S,
    ),
    "tau_s": FieldSpec(
        NUMBER,
        "Startup lag time constant",
        "s",
        "ignition.stage1.startup.tau_s",
        (),
        *LAG_TAU_RANGE_S,
    ),
    "fails": FieldSpec(BOOLEAN, "Failed ignition", "", "ignition.stage1.fails"),
    "propellant": FieldSpec(CHOICE, "Propellant", "", "offload.cases", PROPELLANTS),
    "fixed_key": FieldSpec(
        CHOICE, "Imposed offload stated as", "", "offload.cases[].fixed", FIXED_KEYS
    ),
    "fixed_value": FieldSpec(
        NUMBER,
        "Imposed offload",
        "t or fraction",
        "offload.cases[].fixed.<key>",
        (),
        *OFFLOAD_VALUE_RANGE,
    ),
    "solve_mode": FieldSpec(
        CHOICE, "Offload solved along", "", "offload.cases[].solve", SOLVE_MODES
    ),
    "stage2_offload_t": FieldSpec(
        NUMBER,
        "Stage-2 pre-offload (0: none)",
        "t",
        "offload.cases[].stage2_offload_t",
        (),
        *PREOFFLOAD_RANGE_T,
    ),
    "stage1_dry_mass_added_t": FieldSpec(
        NUMBER,
        "Assumed structural penalty, stage-1 dry mass added (0: none)",
        "t",
        "offload.cases[].stage1_dry_mass_added_t",
        (),
        *PENALTY_RANGE_T,
    ),
    "paired_pad": FieldSpec(BOOLEAN, "Paired pad", "", "offload.cases[].paired_pad"),
    "advanced": FieldSpec(BOOLEAN, "Advanced: stage-2 and both-stage offloads", "", ""),
    "preset": FieldSpec(CHOICE, "Preset the form started from", "", "", PRESET_NAMES),
    "dry_run": FieldSpec(BOOLEAN, "Check only, do not launch", "", ""),
}
"""Every key a launch request may carry, in the page's order (the whitelist)."""
REQUIRED_CHOICES = ("site", "ramp_by", "startup", "propellant")
"""Choice fields every request states."""
SILO_FIELDS = ("stroke_m", "push_by", "carriage_mass_t", "exhaust_impingement_fraction")
"""Fields a silo launch states (beside the push value push_by names)."""
OFFLOAD_OPTIONAL_FIELDS = ("stage2_offload_t", "stage1_dry_mass_added_t", "paired_pad")
"""Fields an offload launch may state (a 0 or false states none)."""
FREE_FIELDS = ("fails", "advanced", "preset", "dry_run")
"""Fields allowed with any choices."""


# ------------------------------------------------------------------ records


class FormError(ValueError):
    """A refusal of the form itself: ``field`` (a FIELDS key, or None) and the one-line
    ``message``."""

    def __init__(self, field: str | None, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


@dataclass(frozen=True)
class Refusal:
    """A refused request: the form field the page marks (a FIELDS key, or None) and one
    line of at most MAX_REFUSAL_CHARS characters."""

    field: str | None
    message: str


@dataclass(frozen=True)
class Form:
    """One launch as the form states it, every value in its config unit (FIELDS). The
    choice fields decide which other fields are used (``used_fields``); an unused field
    is None (False for a boolean). ``preset`` (the preset the form started from) and
    ``dry_run`` (check only) do not enter the experiment."""

    site: str
    ramp_by: str
    startup: str
    propellant: str
    stroke_m: Number | None = None
    push_by: str | None = None
    net_accel_g: Number | None = None
    exit_speed_mps: Number | None = None
    carriage_mass_t: Number | None = None
    exhaust_impingement_fraction: Number | None = None
    t_ign_s: Number | None = None
    at_depth_m: Number | None = None
    at_speed_mps: Number | None = None
    at_height_m: Number | None = None
    t_ramp_s: Number | None = None
    tau_s: Number | None = None
    fails: bool = False
    fixed_key: str | None = None
    fixed_value: Number | None = None
    solve_mode: str | None = None
    stage2_offload_t: Number | None = None
    stage1_dry_mass_added_t: Number | None = None
    paired_pad: bool = False
    advanced: bool = False
    preset: str | None = None
    dry_run: bool = False


@dataclass(frozen=True)
class Basis:
    """The committed experiments a launch is built from, loaded once (``make_basis``).
    Every dict is the raw YAML dict as loaded and is never mutated (builders deep-copy).

    ``offload_experiment`` and ``screening_experiment``: the two committed files;
    ``vehicle_path`` and ``vehicle``: the vehicle file both name and its dict; ``shared``:
    the six config.SHARED_KEYS blocks in file order; ``baseline``: the baseline block;
    ``energy``: the offload block's energy inputs (None without them); ``silo_assist``:
    the assist block of SILO_FRAGMENT_VARIANT (the silo details the form does not edit);
    ``variant_fragments`` and ``case_fragments``: the committed variants (the offload
    file's first) and offload cases by name; ``committed_runs`` and ``committed_cases``:
    the same resolved (the baseline included under its name), for the naming rule; empty
    cases when the basis cannot carry an offload block (a fixed-guidance test basis);
    ``commit``, the full hash of the commit the three files were read from
    (``app.load_basis``), or None when they were not read from a commit (git gave none at
    server start, or a test basis edited in memory): then no name is committed, every
    variant and case takes its neutral name and nothing is called a reproduction."""

    offload_experiment: dict[str, Any]
    screening_experiment: dict[str, Any]
    vehicle_path: str
    vehicle: dict[str, Any]
    shared: dict[str, Any]
    baseline: dict[str, Any]
    energy: dict[str, Any] | None
    silo_assist: dict[str, Any]
    variant_fragments: dict[str, dict[str, Any]]
    case_fragments: dict[str, dict[str, Any]]
    committed_runs: dict[str, ResolvedRun]
    committed_cases: dict[str, ResolvedOffloadCase]
    commit: str | None = None

    @property
    def baseline_name(self) -> str:
        """The baseline's name (the offload reference and the pad-only launch's run)."""
        return str(self.baseline["name"])

    @property
    def first_stage(self) -> str:
        """The vehicle's first stage name (the stage the ramp start is stated for)."""
        return str(self.vehicle["stages"][0]["name"])

    def vehicle_copy(self) -> dict[str, Any]:
        """A deep copy of the vehicle dict, for a resolve."""
        return copy.deepcopy(self.vehicle)


@dataclass(frozen=True)
class Preset:
    """A preset of the page: ``name``, the committed name it reproduces (the baseline,
    a variant or an offload case); ``kind`` (PRESET_BASELINE, PRESET_VARIANT or
    PRESET_CASE); a plain ``label`` built from its values; its ``form``; ``expected_s``,
    the expected duration range [s] of a launch with the pad not cached
    (``derived``); ``note``, what is shown with that range (EXPECTED_DURATION_NOTE:
    estimated under load, not a promise)."""

    name: str
    kind: str
    label: str
    form: Form
    expected_s: tuple[float, float]
    note: str


# ------------------------------------------------------------------ basis


def _skeleton(exp: Mapping[str, Any]) -> dict[str, Any]:
    """name, vehicle, the shared blocks (file order) and the baseline of an experiment
    dict, deep-copied."""
    keys = ("name", "vehicle", *(k for k in exp if k in SHARED_KEYS), "baseline")
    return {k: copy.deepcopy(exp[k]) for k in keys}


def _resolved_commitments(
    offload: Mapping[str, Any], screening: Mapping[str, Any], vehicle: Mapping[str, Any]
) -> tuple[dict[str, ResolvedRun], dict[str, ResolvedOffloadCase]]:
    """The committed baseline and variants of both files and the offload file's cases,
    resolved from trimmed copies (no sweeps, sensitivity or bounds; the cases without
    sensitivity arms). The cases are {} when the files cannot carry an offload block
    (search.figure_of_merit other than payload: a test basis)."""
    runs: dict[str, ResolvedRun] = {}
    for exp in (offload, screening):
        trimmed = {**_skeleton(exp), "variants": copy.deepcopy(exp.get("variants") or {})}
        resolved = resolve_experiment(trimmed, copy.deepcopy(dict(vehicle)))
        for name, run in resolved.runs.items():
            runs.setdefault(name, run)
    block = offload.get("offload")
    if not block:
        return runs, {}
    trimmed = {**_skeleton(offload), "variants": copy.deepcopy(offload.get("variants") or {})}
    trimmed["offload"] = {
        k: copy.deepcopy(v) for k, v in block.items() if k in ("reference", "pad_control", "cases")
    }
    try:
        resolved = resolve_experiment(trimmed, copy.deepcopy(dict(vehicle)))
    except ValueError:
        return runs, {}
    assert resolved.offload is not None
    return runs, {case.name: case for case in resolved.offload.cases}


def make_basis(
    offload_experiment: Mapping[str, Any],
    screening_experiment: Mapping[str, Any],
    vehicle: Mapping[str, Any],
    *,
    commit: str | None = None,
) -> Basis:
    """The Basis of the raw dicts of experiments/silo_offload_2d.yaml,
    experiments/silo_screening_2d.yaml and the vehicle file they name, as loaded (deep
    copies are kept); ``commit``, the full hash of the commit they were read from (None:
    not read from a commit, so no name is kept as committed; ``Basis.commit``). Raises
    ValueError when the two files name different vehicles, their shared blocks or
    baselines differ, SILO_FRAGMENT_VARIANT is missing, a preset names nothing committed
    or a committed run does not resolve."""
    off = copy.deepcopy(dict(offload_experiment))
    scr = copy.deepcopy(dict(screening_experiment))
    veh = copy.deepcopy(dict(vehicle))
    path = off.get("vehicle")
    if not isinstance(path, str) or scr.get("vehicle") != path:
        raise ValueError("the two committed experiments must name the same vehicle file")
    missing = [k for k in (*SHARED_KEYS, "baseline") if k not in off]
    if missing:
        raise ValueError(f"the offload experiment lacks {missing}")
    if any(scr.get(k) != off[k] for k in (*SHARED_KEYS, "baseline")):
        raise ValueError("the two committed experiments differ in a shared block or the baseline")
    variants: dict[str, dict[str, Any]] = dict(off.get("variants") or {})
    for name, fragment in (scr.get("variants") or {}).items():
        variants.setdefault(name, fragment)
    if SILO_FRAGMENT_VARIANT not in variants:
        raise ValueError(f"the offload experiment lacks the variant {SILO_FRAGMENT_VARIANT}")
    block = off.get("offload") or {}
    cases = {str(c["name"]): c for c in block.get("cases") or []}
    runs, resolved_cases = _resolved_commitments(off, scr, veh)
    known = {**runs, **cases}
    unknown = [name for name, _ in PRESETS if name not in known]
    if unknown:
        raise ValueError(f"presets name nothing committed: {unknown}")
    return Basis(
        offload_experiment=off,
        screening_experiment=scr,
        vehicle_path=path,
        vehicle=veh,
        shared={k: off[k] for k in off if k in SHARED_KEYS},
        baseline=off["baseline"],
        energy=block.get("energy"),
        silo_assist=variants[SILO_FRAGMENT_VARIANT]["assist"],
        variant_fragments=variants,
        case_fragments=cases,
        committed_runs=runs,
        committed_cases=resolved_cases,
        commit=commit,
    )


# ------------------------------------------------------------------ request parser


def _cap(text: str) -> str:
    """One line (whitespace runs folded to one space) of at most MAX_REFUSAL_CHARS."""
    line = " ".join(str(text).split())
    if len(line) > MAX_REFUSAL_CHARS:
        line = line[: MAX_REFUSAL_CHARS - 3] + "..."
    return line


def _number(key: str, spec: FieldSpec, raw: object) -> Number:
    """A number field's value: type int or float (never bool), an int no larger than
    INT_MAGNITUDE_MAX in magnitude before it is converted, finite, inside [lo, hi].
    Returned as given (an int stays an int), except -0.0, returned as 0.0. FormError
    otherwise, never echoing the value it refused for its type."""
    if type(raw) not in (int, float):
        raise FormError(key, f"{key}: must be a number ({spec.label})")
    if type(raw) is int and abs(raw) > INT_MAGNITUDE_MAX:
        raise FormError(key, f"{key}: the number is too large for the form ({spec.label})")
    value = float(raw)  # type: ignore[arg-type]
    if not math.isfinite(value):
        raise FormError(key, f"{key}: must be a finite number ({spec.label})")
    assert spec.lo is not None and spec.hi is not None
    if not spec.lo <= value <= spec.hi:
        unit = f" {spec.unit}" if spec.unit else ""
        raise FormError(
            key,
            f"{key}: {value:g}{unit} is outside the form's range {spec.lo:g} to "
            f"{spec.hi:g}{unit} ({spec.label})",
        )
    if value == 0.0:
        return 0 if type(raw) is int else 0.0  # -0.0 is written as 0.0
    return raw  # type: ignore[return-value]


def _value(key: str, raw: object) -> Any:
    """One request value checked against its FieldSpec (FormError otherwise)."""
    spec = FIELDS[key]
    if spec.kind == BOOLEAN:
        if type(raw) is not bool:
            raise FormError(key, f"{key}: must be true or false ({spec.label})")
        return raw
    if spec.kind == CHOICE:
        if type(raw) is not str or raw not in spec.choices:
            listed = (
                f": one of {', '.join(spec.choices)}"
                if len(spec.choices) <= CHOICES_LISTED_MAX
                else ""
            )
            raise FormError(key, f"{key}: not an allowed choice{listed} ({spec.label})")
        return raw
    return _number(key, spec, raw)


def used_fields(choices: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    """(required, optional) form fields for the choices given (site, push_by, ramp_by,
    startup, propellant): the fields the launch uses, beside REQUIRED_CHOICES and
    FREE_FIELDS. Every other field must be left out (a false boolean is accepted)."""
    required: set[str] = set(REQUIRED_CHOICES)
    optional: set[str] = set(FREE_FIELDS)
    if choices.get("site") == SITE_SILO:
        required |= set(SILO_FIELDS)
        if choices.get("push_by") in PUSH_KEYS:
            required.add(choices["push_by"])
    ramp = RAMP_VALUE_KEYS.get(str(choices.get("ramp_by")))
    if ramp is not None:
        required.add(ramp)
    startup = STARTUP_VALUE_KEYS.get(str(choices.get("startup")))
    if startup is not None:
        required.add(startup)
    propellant = choices.get("propellant")
    if propellant == PROPELLANT_FIXED:
        required |= {"fixed_key", "fixed_value"}
        optional |= set(OFFLOAD_OPTIONAL_FIELDS)
    elif propellant == PROPELLANT_SOLVE:
        required.add("solve_mode")
        optional |= set(OFFLOAD_OPTIONAL_FIELDS)
    return required, optional


def _check_one_way(values: Mapping[str, Any]) -> None:
    """Refuse a request that states the push, the ramp start or the startup duration
    two ways (phase file 5.7: both the exit speed and the acceleration; two ramp-start
    families), before the generic unused-field rule."""
    if all(k in values for k in PUSH_KEYS):
        raise FormError(
            "push_by",
            "push: give the net acceleration or the exit speed, not both (push_by names which)",
        )
    ramp = {RAMP_VALUE_KEYS[k] for k in RAMP_BY}
    if len([k for k in ramp if k in values]) > 1:
        raise FormError(
            "ramp_by",
            "ramp start: give it one way only (one of t_ign_s, at_depth_m, at_speed_mps, "
            "at_height_m, the one ramp_by names)",
        )
    if all(k in values for k in STARTUP_VALUE_KEYS.values()):
        raise FormError("startup", "startup: give t_ramp_s or tau_s, not both")


def parse_request(obj: object) -> Form | Refusal:
    """The Form of a launch request (a JSON object already parsed), or the Refusal of
    the first rule it breaks: only FIELDS keys (an unknown key is refused without being
    repeated); every value of its kind (``_value``); the choices of REQUIRED_CHOICES
    given; the push, ramp start and startup duration stated one way (``_check_one_way``);
    every field the choices use given and every other one left out (``used_fields``; a
    false boolean may stay); then the combination rules of ``check_form``."""
    try:
        if not isinstance(obj, dict):
            raise FormError(None, "the request must be a JSON object of form fields")
        for key in obj:
            if not isinstance(key, str) or key not in FIELDS:
                raise FormError(None, "the request has a key the form does not know")
        values = {key: _value(key, raw) for key, raw in obj.items()}
        for key in REQUIRED_CHOICES:
            if key not in values:
                raise FormError(key, f"{key}: missing ({FIELDS[key].label})")
        _check_one_way(values)
        required, optional = used_fields(values)
        for key, value in values.items():
            if key in required or key in optional:
                continue
            if FIELDS[key].kind == BOOLEAN and value is False:
                continue
            raise FormError(key, f"{key}: not used with these choices; leave it out")
        for key in sorted(required, key=list(FIELDS).index):
            if key not in values:
                raise FormError(key, f"{key}: missing ({FIELDS[key].label})")
        form = Form(**values)
        check_form(form)
    except FormError as exc:
        return Refusal(exc.field, _cap(exc.message))
    return form


def push_numbers(form: Form) -> tuple[float, float]:
    """(net acceleration [g0], exit speed [m/s]) of a silo form's push from rest over its
    stroke L: a typed acceleration a gives v_e = sqrt(2 a L), a typed exit speed gives a =
    v_e^2 / (2 L) (the constant_accel model's relations, frame: along the vertical
    track)."""
    stroke = float(form.stroke_m or 0.0)
    if form.push_by == "net_accel_g":
        accel_g = float(form.net_accel_g or 0.0)
        return accel_g, math.sqrt(2.0 * float(from_g(accel_g)) * stroke)
    speed = float(form.exit_speed_mps or 0.0)
    return float(to_g(speed * speed / (2.0 * stroke))), speed


def _check_push(form: Form) -> None:
    """Refuse a silo push whose net acceleration or exit speed, typed or derived from the
    other over the stroke (``push_numbers``), lies outside NET_ACCEL_RANGE_G or
    EXIT_SPEED_RANGE_MPS; the refusal marks the typed push field (the derived value
    follows from it and the stroke)."""
    accel_g, speed = push_numbers(form)
    field = str(form.push_by)
    stated = (
        f"{_num(form.net_accel_g)} g0 net"
        if form.push_by == "net_accel_g"
        else f"exit speed {_num(form.exit_speed_mps)} m/s"
    )
    lo, hi = NET_ACCEL_RANGE_G
    if not lo <= accel_g <= hi:
        raise FormError(
            field,
            f"push: {stated} over a {_num(form.stroke_m)} m stroke is a net acceleration of "
            f"{accel_g:.6g} g0, outside the form's range {lo:g} to {hi:g} g0",
        )
    lo, hi = EXIT_SPEED_RANGE_MPS
    if not lo <= speed <= hi:
        raise FormError(
            field,
            f"push: {stated} over a {_num(form.stroke_m)} m stroke is an exit speed of "
            f"{speed:.6g} m/s, outside the form's range {lo:g} to {hi:g} m/s",
        )


def check_form(form: Form) -> None:
    """The combination rules of the form (FormError naming the field), each value checked
    again for a Form built without ``parse_request``: the four required choices and every
    other choice the launch uses among its allowed values; every boolean a bool; every
    field the choices use given (``used_fields``) and each number inside its range
    (``_number``); a silo push inside the form's ranges of net acceleration and exit
    speed however it is typed (``_check_push``); a pad launch carries no offload (the
    pad's own offload is its pad control, D-SP1-10); a failed ignition carries none (it
    never reaches orbit); the stage-2 and both-stage forms need ``advanced``
    (D-SP2-07)."""
    for name, value in (
        ("site", form.site),
        ("ramp_by", form.ramp_by),
        ("startup", form.startup),
        ("propellant", form.propellant),
    ):
        if value not in FIELDS[name].choices:
            raise FormError(name, f"{name}: not an allowed choice ({FIELDS[name].label})")
    required, optional = used_fields({f.name: getattr(form, f.name) for f in fields(form)})
    for key in sorted(required | optional, key=list(FIELDS).index):
        spec, value = FIELDS[key], getattr(form, key)
        if (
            spec.kind == CHOICE
            and value is not None
            and (type(value) is not str or value not in spec.choices)
        ):
            raise FormError(key, f"{key}: not an allowed choice ({spec.label})")
    for f in fields(form):
        if FIELDS[f.name].kind == BOOLEAN and type(getattr(form, f.name)) is not bool:
            raise FormError(f.name, f"{f.name}: must be true or false ({FIELDS[f.name].label})")
    for key in sorted(required, key=list(FIELDS).index):
        if getattr(form, key) is None:
            raise FormError(key, f"{key}: missing ({FIELDS[key].label})")
    for key in sorted(required | optional, key=list(FIELDS).index):
        if FIELDS[key].kind == NUMBER and getattr(form, key) is not None:
            _number(key, FIELDS[key], getattr(form, key))
    if form.site == SITE_SILO:
        _check_push(form)
    offload = form.propellant != PROPELLANT_FULL
    if offload and form.site == SITE_PAD:
        raise FormError(
            "propellant",
            "propellant: an offload needs the silo; the pad's own offload is its pad control",
        )
    if offload and form.fails:
        raise FormError(
            "propellant", "propellant: a failed ignition never reaches orbit, so no offload"
        )
    if offload and not form.advanced:
        if form.propellant == PROPELLANT_SOLVE and form.solve_mode in ADVANCED_SOLVE_MODES:
            raise FormError(
                "solve_mode",
                f"solve_mode {form.solve_mode} is an Advanced form: set advanced to true (a "
                "stage-2 or both-stage solve is a property of the vehicle model, quoted net "
                "of the pad control)",
            )
        if form.propellant == PROPELLANT_FIXED and form.fixed_key in ADVANCED_FIXED_KEYS:
            raise FormError(
                "fixed_key",
                f"fixed_key {form.fixed_key} is an Advanced form: set advanced to true (an "
                "imposed stage-2 or both-stage offload is a property of the vehicle model, "
                "not netted: it has no pad control)",
            )


def form_to_request(form: Form) -> dict[str, Any]:
    """The request a page sends for ``form``: the fields the choices use, the free
    booleans when true and the preset when set (``parse_request`` gives the form back)."""
    values = {f.name: getattr(form, f.name) for f in fields(form)}
    required, optional = used_fields(values)
    out: dict[str, Any] = {}
    for key in FIELDS:
        value = values[key]
        if key in required or (key in optional and value not in (None, False)):
            out[key] = value
    return out


# ------------------------------------------------------------------ presets


def _form_from_run(basis: Basis, merged: Mapping[str, Any], name: str) -> dict[str, Any]:
    """The form values of a committed run (``merged``: its fragment merged over the
    baseline): site, push and silo details, ramp start, startup, failed ignition.
    ValueError when the run sets something the form cannot state (another silo detail,
    a stage-2 ignition, another end)."""
    out: dict[str, Any] = {}
    assist = merged.get("assist") or {}
    if assist.get("model", "none") == "none":
        out["site"] = SITE_PAD
    else:
        out["site"] = SITE_SILO
        fixed = {k: v for k, v in basis.silo_assist.items() if k not in (*PUSH_KEYS, *SILO_FIELDS)}
        given = {k: v for k, v in assist.items() if k not in (*PUSH_KEYS, *SILO_FIELDS)}
        if given != fixed:
            raise ValueError(f"committed run {name}: a silo detail the form cannot state")
        push = [k for k in PUSH_KEYS if k in assist]
        out["push_by"] = push[0]
        out[push[0]] = assist[push[0]]
        for key in ("stroke_m", "carriage_mass_t", "exhaust_impingement_fraction"):
            out[key] = assist[key]
    ignition = merged.get("ignition") or {}
    if {k: v for k, v in ignition.items() if k != basis.first_stage} != {
        k: v for k, v in basis.baseline["ignition"].items() if k != basis.first_stage
    }:
        raise ValueError(f"committed run {name}: a later stage's ignition the form cannot state")
    stage1 = dict(ignition.get(basis.first_stage) or {})
    if "at_depth_m" in stage1:
        out["ramp_by"], out["at_depth_m"] = RAMP_DEPTH, stage1["at_depth_m"]
    elif "at_speed_mps" in stage1:
        out["ramp_by"], out["at_speed_mps"] = RAMP_SPEED, stage1["at_speed_mps"]
    elif "at_height_m" in stage1:
        event = stage1.get("height_method") == HEIGHT_METHOD_EVENT
        out["ramp_by"] = RAMP_HEIGHT_EVENT if event else RAMP_HEIGHT_CLOSED_FORM
        out["at_height_m"] = stage1["at_height_m"]
    else:
        push_start = stage1.get("reference") == PUSH_START_REFERENCE
        out["ramp_by"] = RAMP_TIME_PUSH_START if push_start else RAMP_TIME_RELEASE
        out["t_ign_s"] = stage1.get("t_ign_s", IgnitionSpec.t_ign_s)
    startup = stage1.get("startup")
    if startup is None:
        out["startup"] = STARTUP_VEHICLE
    elif startup == {"kind": STARTUP_STEP}:
        out["startup"] = STARTUP_STEP
    elif startup.get("kind") in STARTUP_VALUE_KEYS and set(startup) == {
        "kind",
        STARTUP_VALUE_KEYS[startup["kind"]],
    }:
        out["startup"] = startup["kind"]
        out[STARTUP_VALUE_KEYS[startup["kind"]]] = startup[STARTUP_VALUE_KEYS[startup["kind"]]]
    else:
        raise ValueError(f"committed run {name}: a startup override the form cannot state")
    out["fails"] = bool(stage1.get("fails", False))
    end = IMPACT_END if out["fails"] else basis.baseline.get("end")
    if merged.get("end") != end:
        raise ValueError(f"committed run {name}: an end the form cannot state")
    return out


def _form_from_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """The propellant fields of a committed offload case."""
    out: dict[str, Any] = {"propellant": PROPELLANT_FIXED if "fixed" in case else PROPELLANT_SOLVE}
    if "fixed" in case:
        ((key, value),) = case["fixed"].items()
        out["fixed_key"], out["fixed_value"] = key, value
    else:
        out["solve_mode"] = case["solve"]
        out["advanced"] = case["solve"] in ADVANCED_SOLVE_MODES
    for key in ("stage2_offload_t", "stage1_dry_mass_added_t"):
        if key in case:
            out[key] = case[key]
    out["paired_pad"] = bool(case.get("paired_pad", False))
    return out


def preset_form(basis: Basis, name: str) -> Form:
    """The Form of the preset ``name`` (PRESETS), read from its committed fragment: the
    baseline, a variant merged over the baseline, or an offload case with its variant;
    ``preset`` set to the name. Untouched values keep their committed type and digits
    (the 200 m silo's exit speed is the full double). ValueError for an unknown name."""
    kinds = dict(PRESETS)
    if name not in kinds:
        raise ValueError(f"no preset named {name!r}")
    case: Mapping[str, Any] | None = None
    if kinds[name] == PRESET_BASELINE:
        merged = copy.deepcopy(basis.baseline)
        run_name = name
    else:
        if kinds[name] == PRESET_CASE:
            case = basis.case_fragments[name]
            run_name = str(case["of"])
        else:
            run_name = name
        merged = merge_run_dicts(basis.baseline, basis.variant_fragments[run_name])
    values = _form_from_run(basis, merged, run_name)
    values["propellant"] = PROPELLANT_FULL
    if case is not None:
        values.update(_form_from_case(case))
    return Form(**values, preset=name)


def presets(basis: Basis) -> tuple[Preset, ...]:
    """Every preset of PRESETS: its form (``preset_form``), a plain label (``describe``)
    and the expected duration range of its launch with the pad not cached (``derived``
    of the resolved experiment). Raises ValueError when a preset does not resolve on this
    basis (a fixed-guidance test basis cannot carry the offload presets)."""
    out: list[Preset] = []
    for name, kind in PRESETS:
        form = preset_form(basis, name)
        resolved = resolve_experiment(build_experiment(basis, form), basis.vehicle_copy())
        values = derived(resolved)
        lo, hi = values["expected_s"]
        out.append(Preset(name, kind, describe(form), form, (lo, hi), values["expected_note"]))
    return tuple(out)


def _num(value: Number | None) -> str:
    """A form number for a label or a name (6 significant digits)."""
    return f"{float(value or 0.0):g}"


def describe(form: Form) -> str:
    """A plain one-line description of a form, built from its values: the site and push,
    the ramp start, the startup, a failed ignition and the propellant."""
    parts: list[str] = []
    if form.site == SITE_PAD:
        parts.append("pad, held down until release")
    else:
        push = (
            f"{_num(form.net_accel_g)} g0 net"
            if form.push_by == "net_accel_g"
            else f"exit speed {_num(form.exit_speed_mps)} m/s"
        )
        silo = f"silo {_num(form.stroke_m)} m deep, {push}"
        if form.carriage_mass_t:
            silo += f", carriage {_num(form.carriage_mass_t)} t"
        if form.exhaust_impingement_fraction:
            silo += f", exhaust impingement {_num(form.exhaust_impingement_fraction)}"
        parts.append(silo)
    ramp = {
        RAMP_TIME_RELEASE: f"ramp start {float(form.t_ign_s or 0.0):+g} s from release",
        RAMP_TIME_PUSH_START: f"ramp start {float(form.t_ign_s or 0.0):+g} s from push start",
        RAMP_DEPTH: f"ramp start {_num(form.at_depth_m)} m below the mouth",
        RAMP_SPEED: f"ramp start at {_num(form.at_speed_mps)} m/s on the push",
        RAMP_HEIGHT_EVENT: f"ramp start {_num(form.at_height_m)} m above the mouth (event)",
        RAMP_HEIGHT_CLOSED_FORM: (
            f"ramp start {_num(form.at_height_m)} m above the mouth (closed form)"
        ),
    }[form.ramp_by]
    parts.append(ramp)
    parts.append(
        {
            STARTUP_VEHICLE: "the vehicle's own startup",
            STARTUP_STEP: "instant (step) startup: a yardstick, not an engine",
            STARTUP_RAMP: f"{_num(form.t_ramp_s)} s startup ramp",
            STARTUP_LAG: f"lag startup, tau {_num(form.tau_s)} s",
        }[form.startup]
    )
    if form.fails:
        parts.append("stage 1 never lights (failed ignition)")
    if form.propellant == PROPELLANT_SOLVE:
        parts.append(f"offload solved along {form.solve_mode} (the pad control runs too)")
        if form.solve_mode in ADVANCED_SOLVE_MODES:
            parts.append(ADVANCED_SOLVE_READING)
    elif form.propellant == PROPELLANT_FIXED:
        assert form.fixed_key is not None
        value = (
            f"{float(to_percent(float(form.fixed_value or 0.0))):g}% of the load"
            if "fraction" in form.fixed_key
            else f"{_num(form.fixed_value)} t"
        )
        parts.append(f"imposed offload ({form.fixed_key}): {value}")
        if form.fixed_key in ADVANCED_FIXED_KEYS:
            parts.append(ADVANCED_FIXED_READING)
    if form.propellant != PROPELLANT_FULL:
        if form.stage2_offload_t:
            parts.append(f"{_num(form.stage2_offload_t)} t taken from stage 2 first")
        if form.stage1_dry_mass_added_t:
            parts.append(f"assumed +{_num(form.stage1_dry_mass_added_t)} t stage-1 dry mass")
        if form.paired_pad:
            parts.append("with its paired pad")
    return "; ".join(parts)


# ------------------------------------------------------------------ experiment builder


def _assist_dict(basis: Basis, form: Form) -> dict[str, Any]:
    """The whole assist block of a silo launch: the committed silo's keys in their order
    (brake, drive efficiency, shaft and track as committed) with the push key push_by
    names, the depth, the carriage mass and the impingement from the form."""
    assert form.push_by is not None
    edited = {
        form.push_by: getattr(form, form.push_by),
        "stroke_m": form.stroke_m,
        "carriage_mass_t": form.carriage_mass_t,
        "exhaust_impingement_fraction": form.exhaust_impingement_fraction,
    }
    out: dict[str, Any] = {}
    for key, value in basis.silo_assist.items():
        if key in PUSH_KEYS:
            out[form.push_by] = edited[form.push_by]
        elif key in edited:
            out[key] = edited[key]
        else:
            out[key] = copy.deepcopy(value)
    for key, value in edited.items():
        out.setdefault(key, value)
    return out


def _ignition_dict(form: Form) -> dict[str, Any]:
    """The stage-1 ignition block: the ramp-start family ramp_by names (both keys of the
    time family, so nothing is inherited), the startup override unless the vehicle's own,
    and ``fails: true`` for a failed ignition. Never a null."""
    out: dict[str, Any] = {}
    if form.ramp_by in (RAMP_TIME_RELEASE, RAMP_TIME_PUSH_START):
        out["t_ign_s"] = form.t_ign_s
        out["reference"] = (
            RELEASE_REFERENCE if form.ramp_by == RAMP_TIME_RELEASE else PUSH_START_REFERENCE
        )
    elif form.ramp_by == RAMP_DEPTH:
        out["at_depth_m"] = form.at_depth_m
    elif form.ramp_by == RAMP_SPEED:
        out["at_speed_mps"] = form.at_speed_mps
    else:
        out["at_height_m"] = form.at_height_m
        out["height_method"] = (
            HEIGHT_METHOD_EVENT if form.ramp_by == RAMP_HEIGHT_EVENT else HEIGHT_METHOD_CLOSED_FORM
        )
    if form.startup == STARTUP_STEP:
        out["startup"] = {"kind": STARTUP_STEP}
    elif form.startup in STARTUP_VALUE_KEYS:
        key = STARTUP_VALUE_KEYS[form.startup]
        out["startup"] = {"kind": form.startup, key: getattr(form, key)}
    if form.fails:
        out["fails"] = True
    return out


def _variant_dict(basis: Basis, form: Form) -> dict[str, Any]:
    """The variant block: the assist of a silo (a pad variant inherits the baseline's),
    the stage-1 ignition and ``end: impact`` for a failed ignition."""
    out: dict[str, Any] = {}
    if form.site == SITE_SILO:
        out["assist"] = _assist_dict(basis, form)
    out["ignition"] = {basis.first_stage: _ignition_dict(form)}
    if form.fails:
        out["end"] = IMPACT_END
    return out


def _case_dict(form: Form) -> dict[str, Any] | None:
    """The offload case without its name and variant (None for a full load): solve or
    fixed, and the stage-2 pre-offload, the penalty and the paired pad when set (a 0
    leaves the key out)."""
    if form.propellant == PROPELLANT_FULL:
        return None
    out: dict[str, Any] = {}
    if form.propellant == PROPELLANT_SOLVE:
        out["solve"] = form.solve_mode
    else:
        assert form.fixed_key is not None
        out["fixed"] = {form.fixed_key: form.fixed_value}
    if form.stage2_offload_t:
        out["stage2_offload_t"] = form.stage2_offload_t
    if form.stage1_dry_mass_added_t:
        out["stage1_dry_mass_added_t"] = form.stage1_dry_mass_added_t
    if form.paired_pad:
        out["paired_pad"] = True
    return out


def neutral_case_name(form: Form) -> str:
    """silo_<mode> of an offload case that equals no committed one (D-SP2-31): s1, s2,
    both for a solve; fix<x>t, fix<p>pct, s2fix..., bothfix... for an imposed offload;
    then _s2pre<t>t for a stage-2 pre-offload and _dry+<t>t for a penalty (SP1's
    pattern)."""
    if form.propellant == PROPELLANT_SOLVE:
        tag = CASE_MODE_TAGS[str(form.solve_mode)]
    else:
        key = str(form.fixed_key)
        value = float(form.fixed_value or 0.0)
        number = _num(to_percent(value)) if "fraction" in key else _num(value)
        tag = FIXED_KEY_TAGS[key].format(number)
    if form.stage2_offload_t:
        tag += f"_s2pre{_num(form.stage2_offload_t)}t"
    if form.stage1_dry_mass_added_t:
        tag += f"_dry+{_num(form.stage1_dry_mass_added_t)}t"
    return f"{NEUTRAL_CASE_PREFIX}_{tag}"


def _assemble(
    basis: Basis,
    variant: tuple[str, dict[str, Any]] | None,
    case: tuple[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    """The experiment dict: name APP_EXPERIMENT_NAME, the vehicle path, label
    exploratory, the shared blocks and the baseline deep-copied in file order, the one
    variant (if any) and an offload block for the one case (if any): reference the
    baseline, ``pad_control`` true for a solve (every solve, stage 1 included,
    D-SP2-25) and false for an imposed offload (it has none), the committed energy
    block, no sensitivity arms."""
    exp: dict[str, Any] = {
        "name": APP_EXPERIMENT_NAME,
        "vehicle": basis.vehicle_path,
        "label": EXPLORATORY_LABEL,
    }
    exp.update(copy.deepcopy(basis.shared))
    exp["baseline"] = copy.deepcopy(basis.baseline)
    if variant is None:
        return exp
    vname, vdict = variant
    exp["variants"] = {vname: copy.deepcopy(vdict)}
    if case is not None:
        cname, cdict = case
        block: dict[str, Any] = {
            "reference": basis.baseline_name,
            "pad_control": "solve" in cdict,
            "cases": [{"name": cname, "of": vname, **copy.deepcopy(cdict)}],
        }
        if basis.energy is not None:
            block["energy"] = copy.deepcopy(basis.energy)
        exp["offload"] = block
    return exp


def same_run(a: ResolvedRun, b: ResolvedRun) -> bool:
    """True when two resolved runs fly the same: equal RunConfig once a's name is b's,
    and equal vehicles."""
    return a.run.model_copy(update={"name": b.name}) == b.run and a.vehicle == b.vehicle


def _same_case(a: ResolvedOffloadCase, b: ResolvedOffloadCase) -> bool:
    """True when two resolved offload cases of the same name are the same case: equal
    configs, start runs, paired-pad starts and imposed offloads."""
    pads = (a.pad_start is None and b.pad_start is None) or (
        a.pad_start is not None and b.pad_start is not None and same_run(a.pad_start, b.pad_start)
    )
    return (
        a.config == b.config
        and same_run(a.start, b.start)
        and pads
        and a.imposed_kg == b.imposed_kg
    )


def _committed_variant(basis: Basis, run: ResolvedRun, has_case: bool) -> str | None:
    """The committed variant name ``run`` reproduces (RunConfig and vehicle equal), or
    None. The M5 anchor names (compare.ANCHOR_NAMES) only for a launch without an
    offload case, that is when the form equals the preset itself."""
    for name, committed in basis.committed_runs.items():
        if name == basis.baseline_name or not same_run(run, committed):
            continue
        if name in ANCHOR_NAMES and has_case:
            return None
        return name
    return None


def _committed_case(
    basis: Basis,
    vname: str,
    variant: dict[str, Any],
    neutral: ResolvedOffloadCase,
) -> tuple[str, dict[str, Any]] | None:
    """The committed case this launch's case reproduces, as (name, experiment dict
    built with it), or None: a committed case of the variant vname whose config equals
    the launch's (names aside) and which, built from its committed fragment (``variant``
    being the committed variant's) and resolved under its committed name, has the
    committed start run, paired pad and imposed offload. The experiment carries the
    committed raw dicts, so its resolved config is the committed one whatever number
    spelling the request used (3 for 3.0)."""
    for cname, committed in basis.committed_cases.items():
        if committed.config.of != vname:
            continue
        renamed = neutral.config.model_copy(update={"name": cname, "of": vname})
        if renamed != committed.config:
            continue
        fragment = {
            k: copy.deepcopy(v)
            for k, v in basis.case_fragments[cname].items()
            if k not in ("name", "of")
        }
        exp = _assemble(basis, (vname, variant), (cname, fragment))
        resolved = resolve_experiment(exp, basis.vehicle_copy())
        assert resolved.offload is not None
        if _same_case(resolved.offload.cases[0], committed):
            return cname, exp
    return None


def build_experiment(basis: Basis, form: Form) -> dict[str, Any]:
    """The experiment dict of a launch (pure; resolving is the only work): name
    APP_EXPERIMENT_NAME, label exploratory, the six shared blocks and the baseline
    verbatim from the basis, and

    - a pad launch whose ignition resolves equal to the baseline's: nothing else (no
      variants key, no offload);
    - otherwise one variant (``_variant_dict``: the whole silo assist block from the
      committed silo, the chosen ramp-start family, the startup override, a failed
      ignition with ``end: impact``) and, with an offload, one case under a block with
      the committed energy inputs and the pad control on for every solve.

    Names (D-SP2-31): only on a basis read from a commit (``Basis.commit``; else every
    name is neutral), the variant keeps a committed name only when its resolved RunConfig
    and vehicle equal that committed variant's, else NEUTRAL_SILO_VARIANT (or
    NEUTRAL_PAD_VARIANT); the case keeps a committed name only when it resolves, under
    that name, to the committed case (config, start run, paired pad), else
    ``neutral_case_name``. silo_instant and pad_instant only for the preset itself. A
    kept name carries its committed fragment verbatim (variant and case), so the raw run
    dict, resolved_config.yaml and compare.trajectory_key equal the committed run's
    whatever number spelling the request used (a browser sends 3.0 as 3). Raises
    FormError (``check_form``) or what resolve_experiment raises (ValueError subclasses)
    for a refused form."""
    check_form(form)
    variant = _variant_dict(basis, form)
    case = _case_dict(form)
    neutral_v = NEUTRAL_PAD_VARIANT if form.site == SITE_PAD else NEUTRAL_SILO_VARIANT
    neutral_c = None if case is None else neutral_case_name(form)
    trial = _assemble(basis, (neutral_v, variant), None if case is None else (str(neutral_c), case))
    resolved = resolve_experiment(trial, basis.vehicle_copy())
    run = resolved.variants[neutral_v]
    if form.site == SITE_PAD and case is None and same_run(run, resolved.baseline):
        return _assemble(basis, None, None)
    committed = None if basis.commit is None else _committed_variant(basis, run, case is not None)
    vname = committed or neutral_v
    if vname != neutral_v:
        variant = copy.deepcopy(basis.variant_fragments[vname])
    if case is None:
        return _assemble(basis, (vname, variant), None)
    assert resolved.offload is not None and neutral_c is not None
    if vname != neutral_v:
        found = _committed_case(basis, vname, variant, resolved.offload.cases[0])
        if found is not None:
            return found[1]
    return _assemble(basis, (vname, variant), (neutral_c, case))


def committed_names(basis: Basis, resolved: ResolvedExperiment) -> tuple[str, ...]:
    """The names of a resolved launch that are committed names (the variant in
    ``basis.committed_runs``, the case in ``basis.committed_cases``; the baseline aside):
    ``build_experiment`` keeps one only when the configuration equals the committed one,
    so each names a reproduction (D-SP2-36); () on a basis not read from a commit."""
    if basis.commit is None:
        return ()
    out = [
        name
        for name in resolved.variants
        if name in basis.committed_runs and name != basis.baseline_name
    ]
    if resolved.offload is not None:
        out += [c.name for c in resolved.offload.cases if c.name in basis.committed_cases]
    return tuple(out)


# ------------------------------------------------------------------ derived values

# Expected durations [s] of the pieces of a launch: ranges estimated from run times
# measured on this machine, the lower ends near the fastest recorded and the upper ends
# widened from the slowest measured under load (other jobs running). The same searched
# pad has taken from 12.0 s (docs/physics.md, 'With the 2 s planar cap', build step 26a)
# to 46.3 s (survey 07-server-and-worker.md, under load), about 4x. The shipped
# silo_cold_s1 preset launched in 90 s in all in the A4 review (pad 13 s, variant 16 s,
# comparison stage with the stage-1 pad control, the solve with its verification and the
# paired pad 59 s, writing 2 s), 128 s on a loaded machine in the review before it. A
# stage-2 or both pad control or solve is not measured. A stage-1 lag startup slows every
# run that flies it (LAG_SLOWDOWN_REF_S). The page shows EXPECTED_DURATION_NOTE with
# every range.
SEARCHED_RUN_S = (8.0, 50.0)
"""A run with a payload search (the pad, a variant, an imposed offload's run) whose stage
1 lights with a step or a ramp: the upper end widened from the 18.4-46.3 s measured for
the searched pad under load (survey 07); the lower end is not a bound: 12.0 s and 13.9 s
recorded for the capped pad and silo_cold searches on a quieter machine (docs/physics.md,
build step 26a), 13 s and 16 s for the pad and silo_cold in the A4 review's launch."""
LAG_SLOWDOWN_REF_S = 1.0
"""Reference time [s] of the slowdown of a stage-1 lag startup: a run (or a solve with
its verification) whose stage 1 lights with a lag of time constant tau takes k = 1 +
LAG_SLOWDOWN_REF_S / tau times the same run with a ramp (``lag_slowdown``), because the
integrator caps its step at tau / lag_steps_per_tau for the whole lag-lit burn
(prelude.max_step_cap). One searched silo_cold-type variant flown alone on the shipped
basis took 14.9 s with the vehicle's 2 s ramp, 26.0 s with a lag of tau 1.0 s (1.75x,
against k = 2) and 43.4 s at tau 0.5 s (2.9x, against k = 3) in the A4 review; 13.8 s,
24.6 s and 40.9 s when the round-3 fixer flew them again; the capped silo_cold_lag search
took 24.6 s against silo_cold's 13.9 s (docs/physics.md, build step 26a). The form
refuses tau below 0.5 s (LAG_TAU_RANGE_S)."""
UNSEARCHED_RUN_S = (0.5, 5.0)
"""A run flown without a search (fixed guidance, or a failed ignition, whose search is
skipped): 0.7-0.8 s measured, with the load margin."""
SOLVE_WITH_VERIFICATION_S = (25.0, 160.0)
"""A solved offload case with its verification search: a stage-1 solve with its
verification measured at 87-89 s under load (docs/physics.md, SP1's gate fork), a whole
comparison stage with its offload pass at 74.1 s (survey 07, run E) and at 59 s with the
stage-1 pad control and a paired pad as well (the A4 review); the upper end is widened.
A stage-2 or both solve is not measured and takes the same range (SP1's
pre-registration budgets 90-110 s per stage-2 or both pad control)."""
PAD_CONTROL_S: dict[str, tuple[float, float]] = {
    "stage1": (8.0, 60.0),
    "stage2": SOLVE_WITH_VERIFICATION_S,
    "both": SOLVE_WITH_VERIFICATION_S,
}
"""A pad control per mode: stage 1 about 30 s under load (27 evaluations, docs/physics.md;
it ends no_offload, no verification), its lower end that of a searched run; stage 2 and
both are a verified solve each, SP1's budget widened, not measured."""
PAIRED_PAD_S = SEARCHED_RUN_S
"""A paired pad (one payload search)."""
EXPECTED_DURATION_NOTE = (
    "estimated from run times measured on this machine, the upper ends widened from runs "
    "under load (other jobs running); a quiet machine can finish below the lower end (the "
    "silo_cold_s1 preset took 90 s in the A4 review); a stage-1 lag startup multiplies its "
    "runs by 1 + 1 s / tau (2-3x a ramp run, measured at tau 1 s and 0.5 s); a stage-2 or "
    "both pad control or solve is SP1's budget, not measured; the same run has taken from "
    "12 s to 46 s here, so this is a range, not a promise"
)
"""What the page says beside every expected duration (``derived`` and each Preset carry
it)."""


def stage1_lag_tau_s(run: ResolvedRun) -> float | None:
    """The time constant [s] of the lag startup stage 1 of ``run`` lights with (its
    ignition block's startup override resolved over the vehicle stage's own Startup), or
    None when stage 1 lights with a step or a ramp, or never lights (a failed ignition
    has no lag step cap)."""
    stage = run.to_vehicle().stages[0]
    cfg = run.run.ignition_for(stage.name)
    if cfg.fails:
        return None
    startup = stage.startup if cfg.startup is None else cfg.resolved_startup(stage.startup)
    return startup.tau_s if startup.effective_kind == STARTUP_LAG else None


def lag_slowdown(run: ResolvedRun) -> float:
    """The factor [-] by which a stage-1 lag startup slows ``run``: 1 + LAG_SLOWDOWN_REF_S
    / tau for a lag of time constant tau (``stage1_lag_tau_s``), 1 otherwise."""
    tau = stage1_lag_tau_s(run)
    return 1.0 if tau is None else 1.0 + LAG_SLOWDOWN_REF_S / tau


def _scaled(span: tuple[float, float], factor: float) -> tuple[float, float]:
    """A duration range [s] with both ends multiplied by factor."""
    return span[0] * factor, span[1] * factor


def _run_range(run: ResolvedRun) -> tuple[float, float]:
    """The expected duration [s] of one run: searched or not, times its lag slowdown
    (``lag_slowdown``)."""
    base = SEARCHED_RUN_S if run.run.figure_of_merit in SEARCHED_FIGURES else UNSEARCHED_RUN_S
    return _scaled(base, lag_slowdown(run))


def expected_work(
    resolved: ResolvedExperiment, *, pad_cached: bool = False
) -> list[tuple[str, tuple[float, float]]]:
    """(label, expected range [s]) of every piece of a launch, in order: the pad unless
    cached, each variant, the pad control of each solved mode, each case (a solve with
    its verification, or an imposed offload's searched run) and its paired pad. A run, a
    solve or an imposed case whose stage 1 lights with a lag is slowed by its
    ``lag_slowdown``; the pad controls and the paired pad fly the baseline's startup and
    keep their ranges."""
    items: list[tuple[str, tuple[float, float]]] = []
    if not pad_cached:
        items.append((f"pad baseline {resolved.baseline.name}", _run_range(resolved.baseline)))
    for name, run in resolved.variants.items():
        items.append((f"variant {name}", _run_range(run)))
    if resolved.offload is not None:
        for mode in resolved.offload.pad_control_modes:
            items.append((f"pad control {mode}", PAD_CONTROL_S[mode]))
        for case in resolved.offload.cases:
            solved = case.config.solved
            items.append(
                (
                    f"{'solve' if solved else 'imposed offload'} {case.name}",
                    _scaled(SOLVE_WITH_VERIFICATION_S, lag_slowdown(case.start))
                    if solved
                    else _run_range(case.start),
                )
            )
            if case.pad_start is not None:
                items.append((f"paired pad {case.pad_start.name}", PAIRED_PAD_S))
    return items


def _push_values(
    run: ResolvedRun, assist: ConstantAccelAssist, length_m: float, sin_phi: float, g: float
) -> dict[str, Any]:
    """The push of a constant_accel silo: the key typed, depth L [m], net acceleration
    [g0] and exit speed v_e = sqrt(2 a L) [m/s], push time sqrt(2 L / a) [s], felt axial
    g (a + g_eff sin phi) / g0 (a full stack pushed at 3 g0 net feels 4 g0), braking
    distance v_e^2 / (2 a_brake) and facility length L + braking [m], the drag-free apex
    v_e^2 / (2 g_eff) [m] above the mouth (the bound of a height ramp start) and g_eff
    [m/s^2]."""
    a = assist.net_accel_mps2
    v_e = assist.exit_speed_mps(length_m)
    typed = "exit_speed_mps" if getattr(run.run.assist, "exit_speed_mps", None) else "net_accel_g"
    braking = assist.braking_distance_m(v_e)
    return {
        "typed": typed,
        "stroke_m": length_m,
        "net_accel_g": float(to_g(a)),
        "exit_speed_mps": v_e,
        "push_time_s": assist.push_time_s(length_m),
        "felt_g": float(to_g(a + g * sin_phi)),
        "braking_distance_m": braking,
        "facility_length_m": length_m + braking,
        "drag_free_apex_m": v_e * v_e / (2.0 * g),
        "g_eff_mps2": g,
    }


def _ramp_values(
    spec: IgnitionSpec, assist: Any, length_m: float | None, g: float
) -> dict[str, Any]:
    """The stage-1 ramp start four ways from its IgnitionSpec (``resolve_ignition``'s
    conversions): the time after release and from push start [s], and where defined the
    depth below the mouth [m] and speed [m/s] on the push (lit on the floor before the
    push: depth L, speed 0), or the height above the mouth [m] and the speed [m/s] of the
    drag-free coast at g_eff after release (None once that coast is back below the
    mouth). A height reached by the altitude event has no time before the flight: its
    time is the closed-form estimate (``estimate`` true). A pad has a time after release
    only."""
    out: dict[str, Any] = {
        "trigger": spec.trigger_kind,
        "requested": spec.trigger_value,
        "estimate": spec.lights_at_height,
        "time_after_release_s": None,
        "time_from_push_start_s": None,
        "depth_m": None,
        "speed_mps": None,
        "height_m": None,
    }
    if not isinstance(assist, ConstantAccelAssist) or length_m is None:
        out["time_after_release_s"] = spec.t_ign_s
        return out
    a = assist.net_accel_mps2
    v_e = assist.exit_speed_mps(length_m)
    t_push = assist.push_time_s(length_m)
    if spec.lights_at_height:
        h = float(spec.trigger_value or 0.0)
        t_rel = 2.0 * h / (v_e + math.sqrt(max(v_e * v_e - 2.0 * g * h, 0.0)))
        t_ps = t_rel + t_push
    elif spec.reference == RELEASE_REFERENCE:
        t_rel = spec.t_ign_s
        t_ps = t_rel + t_push
    else:
        t_ps = spec.t_ign_s
        t_rel = t_ps - t_push
    out["time_after_release_s"] = t_rel
    out["time_from_push_start_s"] = t_ps
    if t_ps < 0.0:
        out["depth_m"], out["speed_mps"] = length_m, 0.0
    elif t_rel <= 0.0:
        out["depth_m"] = max(length_m - 0.5 * a * t_ps * t_ps, 0.0)
        out["speed_mps"] = a * t_ps
    else:
        height = v_e * t_rel - 0.5 * g * t_rel * t_rel
        if height >= 0.0:
            out["height_m"], out["speed_mps"] = height, v_e - g * t_rel
    return out


def derived(resolved: ResolvedExperiment, *, pad_cached: bool = False) -> dict[str, Any]:
    """The values the page shows live for a resolved launch (plain data, SI except the
    g0 values): ``variant`` (its name, None for the pad alone), ``runs`` (every run
    directory the launch writes: the baseline, the variant, the case, its paired pad and
    the pad controls), ``push`` (``_push_values``; None for a pad), ``ramp_start``
    (``_ramp_values`` of stage 1 of the variant, else of the baseline; None for a failed
    ignition, which never lights), ``fails``,
    ``expected_s`` [lo, hi] and ``expected_items`` (``expected_work``, the pad left out
    when ``pad_cached``) and ``expected_note``. The assist, track and ignition specs are
    built as the planar run builds them (``sim.planar_setup``: g_eff = g_ref of the
    site's planar environment). Raises FormError (NON_FINITE_MESSAGE) rather than return
    a value that is not finite."""
    variant = next(iter(resolved.variants.values()), None)
    run = variant if variant is not None else resolved.baseline
    cfg = run.run
    vehicle = run.to_vehicle()
    env = PlanarEnvironment(
        InverseSquareGravity(MU_EARTH_M3S2), cfg.site.omega_p_rads, ambient_scalar
    )
    g = env.g_ref_mps2
    assist, track = build_assist(cfg.assist, g)
    spec = resolve_stage_ignitions(cfg, vehicle, assist, track, g)[vehicle.stages[0].name]
    push = None
    length = None
    if isinstance(assist, ConstantAccelAssist) and track is not None:
        length = track.length_m
        push = _push_values(run, assist, length, math.sin(track.phi(0.0)), g)
    names = list(resolved.runs)
    if resolved.offload is not None:
        names += offload_run_names(resolved.offload.config, resolved.baseline.name)
    work = expected_work(resolved, pad_cached=pad_cached)
    out = {
        "variant": None if variant is None else variant.name,
        "runs": names,
        "push": push,
        "ramp_start": None if spec.fails else _ramp_values(spec, assist, length, g),
        "fails": spec.fails,
        "expected_s": [sum(r[0] for _, r in work), sum(r[1] for _, r in work)],
        "expected_items": [[label, lo, hi] for label, (lo, hi) in work],
        "expected_note": EXPECTED_DURATION_NOTE,
    }
    bad = _non_finite(out)
    if bad:
        raise FormError(None, f"{NON_FINITE_MESSAGE}: {', '.join(bad)}")
    return out


NON_FINITE_MESSAGE = "a derived value of this launch is not a finite number"
"""The refusal ``derived`` raises rather than return a non-finite value (a page's JSON
must stay strict)."""


def _non_finite(obj: Any, path: str = "") -> list[str]:
    """The paths of every float in a plain-data value (dicts, lists) that is not finite."""
    if isinstance(obj, float):
        return [] if math.isfinite(obj) else [path or "value"]
    if isinstance(obj, Mapping):
        return [p for k, v in obj.items() for p in _non_finite(v, f"{path}.{k}" if path else k)]
    if isinstance(obj, list | tuple):
        return [p for i, v in enumerate(obj) for p in _non_finite(v, f"{path}[{i}]")]
    return []


# ------------------------------------------------------------------ refusal text

VALUE_ERROR_PREFIX = "Value error, "
"""What pydantic puts before the message of a ValueError raised in a validator."""
LOC_FIELDS = frozenset(
    {
        "stroke_m",
        "net_accel_g",
        "exit_speed_mps",
        "carriage_mass_t",
        "exhaust_impingement_fraction",
        "t_ign_s",
        "at_depth_m",
        "at_speed_mps",
        "at_height_m",
        "t_ramp_s",
        "tau_s",
        "fails",
        "stage2_offload_t",
        "stage1_dry_mass_added_t",
        "paired_pad",
    }
)
"""Config keys that are form fields of the same name."""
LOC_KEY_FIELDS: dict[str, str] = {
    "reference": "ramp_by",
    "height_method": "ramp_by",
    "startup": "startup",
    "kind": "startup",
    "solve": "solve_mode",
    "assist": "push_by",
}
"""Other config keys and the form field a refusal at them marks."""
MESSAGE_FIELDS: tuple[tuple[str, str], ...] = (
    ("needs an assist model", "ramp_by"),
    ("push_start", "ramp_by"),
    ("more than one way", "ramp_by"),
    ("override 'assist'", "push_by"),
    ("exclusive families", "ramp_by"),
    ("at_depth_m", "at_depth_m"),
    ("at_speed_mps", "at_speed_mps"),
    ("at_height_m", "at_height_m"),
    ("tau_s", "tau_s"),
    ("t_ramp_s", "t_ramp_s"),
    ("startup", "startup"),
    ("stage2_offload_t", "stage2_offload_t"),
    ("paired_pad", "paired_pad"),
    ("stage1_dry_mass_added_t", "stage1_dry_mass_added_t"),
    ("pad_control", "solve_mode"),
    ("fixed offload", "fixed_value"),
    ("of propellant from stage", "fixed_value"),
    ("exit_speed_mps", "exit_speed_mps"),
    ("net_accel_g", "net_accel_g"),
    ("stroke_m", "stroke_m"),
    ("fails", "fails"),
)
"""(text in a refusal, the form field it marks), tried in order on messages without a
usable location (plain ValueErrors of resolve_run, offload_overrides and the
preflight)."""


def _message_field(text: str, form: Form | None) -> str | None:
    """The form field a refusal message is about (MESSAGE_FIELDS), or None. An offload
    taken from stage 2 marks the stage-2 pre-offload when the form has one before a
    stage-1 case, else the imposed offload."""
    for needle, field in MESSAGE_FIELDS:
        if needle not in text:
            continue
        if needle == "of propellant from stage" and form is not None and form.stage2_offload_t:
            stage1_case = form.propellant == PROPELLANT_SOLVE or (
                form.fixed_key is not None and OFFLOAD_FIXED_MODES[form.fixed_key] == "stage1"
            )
            if stage1_case and "'stage2'" in text:
                return "stage2_offload_t"
        return field
    return None


def _clean_loc(loc: tuple[Any, ...]) -> tuple[Any, ...]:
    """A pydantic error location without the assist union's discriminator tags."""
    out: list[Any] = []
    for i, part in enumerate(loc):
        if i > 0 and loc[i - 1] == "assist" and part in ASSIST_UNION_TAGS:
            continue
        out.append(part)
    return tuple(out)


def _loc_field(loc: tuple[Any, ...], text: str, form: Form | None) -> str | None:
    """The form field a pydantic error location marks: an offload case's fixed value or
    key, a config key named like a form field (LOC_FIELDS, LOC_KEY_FIELDS), else the
    message's field, else the offload block's propellant or solve mode."""
    keys = [str(p) for p in loc if isinstance(p, str)]
    if "fixed" in keys:
        return "fixed_key" if keys[-1] == "fixed" else "fixed_value"
    if keys and keys[-1] in LOC_FIELDS:
        return keys[-1]
    if keys and keys[-1] in LOC_KEY_FIELDS:
        return LOC_KEY_FIELDS[keys[-1]]
    field = _message_field(text, form)
    if field is not None:
        return field
    if keys[:2] == ["offload", "cases"]:
        return "propellant"
    if keys[:1] == ["offload"]:
        return "solve_mode"
    if keys[:2] == ["ignition", "stage1"] or keys[-1:] == ["stage1"]:
        return "ramp_by"
    return None


def refusal_text(exc: BaseException, form: Form | None = None) -> tuple[str | None, str]:
    """(form field or None, one line of at most MAX_REFUSAL_CHARS) for a refused launch:
    a FormError's own field and message; a pydantic ValidationError through its first
    error of ``errors(include_url=False, include_input=False)`` (the location without the
    union tag, then the message without VALUE_ERROR_PREFIX); any other exception, the
    first line of its text. The field comes from the location or the message
    (``_loc_field``, ``_message_field``); ``form`` disambiguates an offload taken from
    stage 2. Never the full text of a ValidationError (which repeats the input)."""
    if isinstance(exc, FormError):
        return exc.field, _cap(exc.message)
    if isinstance(exc, ValidationError):
        errors = exc.errors(include_url=False, include_input=False)
        if not errors:
            return None, _cap(f"{exc.title}: refused")
        first = errors[0]
        loc = _clean_loc(tuple(first.get("loc", ())))
        msg = str(first.get("msg", ""))
        if msg.startswith(VALUE_ERROR_PREFIX):
            msg = msg[len(VALUE_ERROR_PREFIX) :]
        where = ".".join(str(p) for p in loc)
        text = f"{where}: {msg}" if where else msg
        return _loc_field(loc, msg, form), _cap(text)
    lines = str(exc).strip().splitlines()
    text = lines[0] if lines else type(exc).__name__
    return _message_field(text, form), _cap(text)


def refusal(exc: BaseException, form: Form | None = None) -> Refusal:
    """The Refusal of ``refusal_text``."""
    field, message = refusal_text(exc, form)
    return Refusal(field, message)
