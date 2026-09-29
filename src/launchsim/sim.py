"""Run one configuration and return a Result; results I/O (the only module besides cli.py
that touches the file system).

``simulate`` (pure) runs one configuration through the 1-D planner (``phases``) and
assembles the Result: time series, events, metrics and the loss budget (``losses``);
``run`` builds the run-model inputs from a validated RunConfig (mu/r^2 gravity,
g_eff = mu/R_E^2, ignition specs, the assist model and its track through
``assist.build_assist``) and calls it. ``run_experiment`` and ``run_sweep`` are the
stable entry points the CLI calls.

Results layout (never overwritten; CLAUDE.md)::

    results/<experiment>/<YYYYMMDDTHHMMSSZ>[-n]/
        resolved_config.yaml   experiment name, vehicle dict, every run dict, git, timestamp
        metrics.json           per-run metrics, the comparison against the baseline
                               (``compare``) and the sensitivity cases (``run_sensitivity``)
        summary.md             the per-variant table against the baseline, the sensitivity
                               table, the attributed assumptions and the identity checks
        <run>/timeseries.csv   sampled state (t_s, z_m, v_mps, m_kg, ...)
        <run>/events.csv       phase-boundary events (t_s, event, phase)
        plots/<run>_<quantity>.png  altitude, speed, mass_thrust, felt_g and, for a run
                               with a track phase, track_forces and drive_power (PLOT_PANELS)

Experiment and run names become directory names, so they must be single safe path
components (check_name); the CLI validates them before anything is written.

A sweep writes ``sweep_<n>/run_NNNN/`` (flat single-run layout: resolved_config.yaml,
metrics.json, summary.md, timeseries.csv, events.csv, plots/) plus
``sweep_<n>/sweep_index.csv`` and a top-level summary.md; the baseline it compares
against is written once under ``baseline/``.

Both entry points create the run directory before simulating anything, so an unwritable
results root fails before a long run starts. summary.md is written last; if anything
raises before it, ``FAILED.txt`` with the traceback is written into the directory and the
exception propagates, so a directory without summary.md is partial and never mistaken
for a good run (the next run creates a sibling; nothing is ever overwritten).

Every file is written with ``encoding="utf-8"`` and ``newline="\\n"``.
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import traceback
from collections.abc import Callable, Container, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
import yaml
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from scipy.integrate import OdeSolution
from scipy.optimize import brentq

from launchsim.assist import NoAssist, build_assist
from launchsim.assist.base import AssistModel, TrackGeometry
from launchsim.config import (
    VEHICLE_PREFIX,
    ResolvedExperiment,
    ResolvedRun,
    RunConfig,
    SweepPoint,
    read_value,
    resolve_run,
)
from launchsim.constants import MU_EARTH_M3S2
from launchsim.dynamics import (
    VERTICAL_LAYOUT,
    ConstantGravity,
    Gravity,
    InverseSquareGravity,
    TrackParams,
    g_eff_track,
    track_observables,
    track_to_vertical,
)
from launchsim.losses import (
    AssistEnergyBudget,
    LossBudget,
    assist_energy_budget,
    drive_power_extrema,
    drive_work_split,
    ignition_loss_analytic_mps,
    loss_budget,
)
from launchsim.phases import (
    ASCENT_KINDS,
    ASSIST_KIND,
    ATOL_M,
    ZERO_SPAN_S,
    AscentStart,
    HoldParams,
    IgnitionSpec,
    IntegratorSettings,
    PhaseResult,
    RunTrace,
    VerticalPlanner,
    sample_grid,
)
from launchsim.units import deg_to_rad, from_g, j_to_kwh, km_to_m, kn_to_n, kwh_to_j, t_to_kg, to_g
from launchsim.vehicle import Vehicle, ideal_dv_mps, payload_gain_kg

__all__ = ["NoAssist"]  # re-exported: tests build a pad run with sim.NoAssist()

Status = Literal["nominal", "impact", "no_liftoff", "drive_limit"]

COMPARISON_BASIS = (
    "Comparison basis: sweep-optimized (Phase 1 has no guidance parameters); "
    "1-D vertical, vacuum thrust, no drag, no rotation, no throttling"
)
# Track-phase columns of the time series (track_observables); NaN outside ASSIST rows.
TRACK_COLUMNS: tuple[str, ...] = (
    "s_m",
    "drive_force_N",
    "interface_force_N",
    "drive_power_W",
    "track_normal_g_vehicle",
    "track_normal_g_carriage",
)
TIMESERIES_COLUMNS: tuple[str, ...] = (
    "t_s",
    "z_m",
    "v_mps",
    "m_kg",
    "t_rel_release_s",
    "thrust_N",
    "thrust_vac_N",
    "accel_felt_g",
    "phase",
    "stage",
    "J_vac_mps",
    "J_grav_mps",
    "J_alt_mps",
    "J_bp_mps",
    "J_steer_mps",
    *TRACK_COLUMNS,
)
TIMESERIES_TEXT_COLUMNS: frozenset[str] = frozenset({"phase", "stage"})
EVENT_COLUMNS: tuple[str, ...] = ("t_s", "event", "phase", "stage", "z_m", "v_mps", "m_kg")
EVENT_TEXT_COLUMNS: frozenset[str] = frozenset({"event", "phase", "stage"})
TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"
GIT_TIMEOUT_S = 5.0
GIT_EXCLUDE_RESULTS = ":(exclude)results"  # pathspec: the results tree never counts as dirty
NOT_A_REPO_MARKER = "not a git repository"
CSV_FLOAT_FORMAT = "%.12g"
MAX_DIR_SUFFIX = 1000
FAILED_MARKER = "FAILED.txt"  # written into a run directory that raised before summary.md
PLOT_SERIES_COLOR = "#2a78d6"
PLOT_GRID_COLOR = "#d8d8d4"
PLOT_LINE_WIDTH = 2.0
PLOT_GRID_LINE_WIDTH = 0.6
PLOT_FIGSIZE_IN = (6.4, 3.6)
PLOT_DPI = 120
# Metric keys the results records add themselves (Result.status, Result.flags); a metric
# with one of these names would be silently overwritten in metrics.json, so it is refused.
RESERVED_METRIC_KEYS: frozenset[str] = frozenset({"status", "flags"})
PHASE1_ASSUMPTIONS: tuple[str, ...] = (
    "1-D vertical motion",
    "vacuum thrust from sea level (no back-pressure), no atmosphere, no drag",
    "no Earth rotation (omega_p = 0), Coriolis neglected",
    "no throttling; instantaneous cutoff at propellant depletion",
)
# Phase 1 runs without Earth rotation: the planar rate ``run`` hands to g_eff_track, the
# one place the value lives (the assumption string below quotes it).
OMEGA_P_PHASE1_RADS = 0.0
# What ``run`` fixes and ``simulate`` cannot know from its arguments alone: the run
# model's gravity and the origin of its g_eff (simulate states the model it was handed).
RUN_MODEL_ASSUMPTIONS: tuple[str, ...] = (
    "pad and track g_eff = mu/R_E^2 - omega_p^2 R_E with omega_p = "
    f"{OMEGA_P_PHASE1_RADS:g} rad/s, continuous with mu/r^2 at z = 0",
)
# The plotted set per run (write_plots): plots/<run>_<quantity>.png, each a panel
# (quantity, columns, y labels) against the time since release; the track panels only
# when the run has ASSIST rows. One y label: every column shares the axis (same unit);
# one label per column: each column gets its own y axis (a twin axis for the second),
# so quantities with different units (mass and thrust) are never drawn on one scale.
type PlotPanel = tuple[str, tuple[str, ...], tuple[str, ...]]
PLOT_ABSCISSA = "t_rel_release_s"
PLOT_ABSCISSA_LABEL = "t - t_release [s]"
PLOT_PANELS: tuple[PlotPanel, ...] = (
    ("altitude", ("z_m",), ("z [m]",)),
    ("speed", ("v_mps",), ("v [m/s]",)),
    ("mass_thrust", ("m_kg", "thrust_N"), ("m [kg]", "T [N]")),
    ("felt_g", ("accel_felt_g",), ("felt axial acceleration [g0]",)),
)
PLOT_TRACK_PANELS: tuple[PlotPanel, ...] = (
    ("track_forces", ("drive_force_N", "interface_force_N"), ("F_drive, F_int [N]",)),
    ("drive_power", ("drive_power_W",), ("P_drive [W]",)),
)
PLOT_SERIES_COLORS: tuple[str, ...] = (PLOT_SERIES_COLOR, "#d6742a")
# The four CLAUDE.md summary names of track quantities whose canonical metric key is
# the silo-table name (docs/physics.md, "Reported quantities"): ``track_metrics`` writes
# both, the alias holding the same number as its canonical key, so REQUIRED_METRICS and
# the summary rows can use the CLAUDE.md wording while sweep_index.csv and the tests use
# the canonical keys. Later steps should read the canonical key.
TRACK_METRIC_ALIASES: dict[str, str] = {
    "assist_energy_J": "drive_energy_J",
    "assist_energy_kWh": "drive_energy_kWh",
    "peak_drive_power_W": "drive_power_peak_W",
    "peak_interface_force_N": "interface_force_peak_N",
}
# YAML unit suffixes of config keys (config.py converts by the same suffixes) and their
# SI conversion (units.py) and unit, for the sensitivity table's SI column
# (``si_value``); a suffix listed with the identity is already SI. A key with no listed
# suffix is taken as dimensionless (a fraction such as drive_efficiency).
SI_SUFFIX_CONVERSIONS: dict[str, tuple[Callable[[float], float], str]] = {
    "t": (t_to_kg, "kg"),
    "kN": (kn_to_n, "N"),
    "deg": (deg_to_rad, "rad"),
    "km": (km_to_m, "m"),
    "g": (from_g, "m/s^2"),
    "kWh": (kwh_to_j, "J"),
    "s": (lambda x: x, "s"),
    "m": (lambda x: x, "m"),
    "kg": (lambda x: x, "kg"),
    "N": (lambda x: x, "N"),
    "Pa": (lambda x: x, "Pa"),
    "W": (lambda x: x, "W"),
    "J": (lambda x: x, "J"),
    "mps": (lambda x: x, "m/s"),
    "mps2": (lambda x: x, "m/s^2"),
}
DIMENSIONLESS_UNIT = "-"
# Summary display only (metrics.json keeps the raw numbers): a magnitude below
# DISPLAY_ZERO_ABS in the quantity's own unit prints as 0 (cos(pi/2) roundoff in a
# track-normal g, a hold-down credit of -2.5e-13 m/s), and the bound lines print an
# excess whose magnitude is below EXCESS_NOISE_MPS as 0 with the bound named, so that
# rounding noise is not read as signal.
DISPLAY_ZERO_ABS = 1e-9
EXCESS_NOISE_MPS = 1e-6
# The stage-1 startup kind that is a yardstick, not an engine (config: kind step).
STEP_STARTUP_KIND = "step"
# Metric keys every summary must report (CLAUDE.md "Every summary reports"): each is a
# row of the per-variant table (``VARIANT_ROWS`` references it), "n/a" when a run does
# not carry it, so a missing item is visible. The loss and load items are filled by
# ``run_metrics``, the assist ones by ``track_metrics``; the payload equivalent is a
# comparison item (``compare``: ideal_screening_payload_equiv_kg), max_q_pa is Phase 2.
REQUIRED_METRICS: tuple[str, ...] = (
    "gravity_loss_mps",
    "drag_loss_mps",
    "steering_loss_mps",
    "back_pressure_loss_mps",
    "max_q_pa",
    "peak_felt_axial_g",
    "peak_interface_force_N",
    "peak_track_normal_g",
    "assist_energy_J",
    "assist_energy_kWh",
    "peak_drive_power_W",
    "facility_length_m",
)
# CLAUDE.md: the loss budget must close to 0.01 m/s; the same bound decides whether a
# variant's speed gain is "explained" (Checks section of the summary).
IDENTITY_TOL_MPS = 0.01
# A variant's integrated ignition loss is measured against ``silo_instant`` only when both
# start their flight from the same state (speed and altitude within these tolerances).
SAME_RELEASE_SPEED_TOL_MPS = 1e-6
SAME_RELEASE_ALT_TOL_M = 1e-6
INSTANT_VARIANT_NAME = "silo_instant"
# Metric columns of sweep_index.csv, after the axis values and the run directory.
SWEEP_INDEX_METRICS: tuple[str, ...] = (
    "exit_speed_mps",
    "stage1_burnout_speed_mps",
    "stage1_burnout_speed_delta_mps",
    "ignition_loss_formula_mps",
    "drive_energy_J",
    "drive_power_peak_W",
    "felt_g_track_peak",
    "facility_length_m",
)
CD_SENSITIVITY_NOTE = "n/a: no drag in Phase 1"
# What the Sensitivity section prints instead of a table when no case ran: the reason,
# set by the entry point that knows it (ExperimentResult.sensitivity_note).
SENSITIVITY_NONE_DECLARED = f"(no sensitivity block declared; C_D: {CD_SENSITIVITY_NOTE})"
SENSITIVITY_NONE_FOR_RUNS = (
    f"(no sensitivity cases declared for the runs that ran; C_D: {CD_SENSITIVITY_NOTE})"
)
SENSITIVITY_SKIPPED = "(sensitivity cases skipped: --no-sensitivity)"
SENSITIVITY_SWEEP_POINT = "(no sensitivity cases: a sweep point runs none)"

# Names that become directories inside the results tree: one safe path component. The
# length cap keeps results/<name>/<ts>/sweep_n/run_NNNN/plots/<png> under Windows'
# default MAX_PATH (260) from a repository at a normal depth.
NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.+-]*$")
MAX_NAME_LEN = 64
RESERVED_RUN_NAME_PATTERN = re.compile(r"^(plots|baseline|sweep_\d+|run_\d+)$")
WINDOWS_DEVICE_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
)
PLOT_STEM_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")


class InvalidNameError(ValueError):
    """An experiment or run name that cannot be a single, safe results-directory name."""


def check_name(name: str, what: str, reserved: re.Pattern[str] | None = None) -> str:
    """Validate a name that becomes a results directory and return it.

    Allowed: ``[A-Za-z0-9][A-Za-z0-9_.+-]*`` of at most MAX_NAME_LEN characters, not
    ending in ``.`` (Windows strips trailing dots), no Windows device names (CON, NUL,
    COM1, ...), and not matching ``reserved``. Raises InvalidNameError otherwise.
    """
    if not isinstance(name, str) or not NAME_PATTERN.match(name) or name.endswith("."):
        raise InvalidNameError(
            f"{what} {name!r} is not a valid results directory name: use letters, digits, "
            "'_', '.', '+' or '-', starting with a letter or digit and not ending in '.'"
        )
    if len(name) > MAX_NAME_LEN:
        raise InvalidNameError(
            f"{what} {name!r} is longer than {MAX_NAME_LEN} characters ({len(name)}); "
            "results paths must stay short on Windows"
        )
    if name.split(".")[0].upper() in WINDOWS_DEVICE_NAMES:
        raise InvalidNameError(f"{what} {name!r} is a reserved Windows device name")
    if reserved is not None and reserved.match(name):
        raise InvalidNameError(f"{what} {name!r} is reserved by the results layout")
    return name


def check_run_name(name: str) -> str:
    """check_name for a run: additionally rejects plots, baseline, sweep_<n>, run_<n>."""
    return check_name(name, "run name", RESERVED_RUN_NAME_PATTERN)


def check_result_names(resolved: ResolvedExperiment) -> None:
    """Validate the experiment name and every baseline/variant name before anything is
    written; raises InvalidNameError naming the offender."""
    check_name(resolved.experiment.name, "experiment name")
    for name in resolved.runs:
        check_run_name(name)


# ------------------------------------------------------------------------------ results


def empty_timeseries() -> pd.DataFrame:
    """An empty time-series frame with the standard columns (TIMESERIES_COLUMNS)."""
    return pd.DataFrame(
        {
            c: pd.Series(dtype="str" if c in TIMESERIES_TEXT_COLUMNS else "float64")
            for c in TIMESERIES_COLUMNS
        }
    )


def empty_events() -> pd.DataFrame:
    """An empty events frame with the standard columns (EVENT_COLUMNS)."""
    return pd.DataFrame(
        {c: pd.Series(dtype="str" if c in EVENT_TEXT_COLUMNS else "float64") for c in EVENT_COLUMNS}
    )


@dataclass(frozen=True)
class Result:
    """Outcome of one run (SI; times are seconds since the run's internal t = 0).

    metrics: flat name -> value dict (numbers, strings, None); written to metrics.json.
    timeseries: sampled state, columns TIMESERIES_COLUMNS (t_s, z_m, v_mps, m_kg,
    t_rel_release_s, thrust_N, thrust_vac_N, accel_felt_g, phase, stage, J_*_mps).
    events: logged events, columns EVENT_COLUMNS (t_s, event, phase, stage, z_m, v_mps,
    m_kg).
    loss_budget: LossBudget from release onward (all zero when the run never flew);
    assist_budget: the AssistEnergyBudget of the push (None for a pad).
    assumptions: attributed assumption strings for the summary.
    phases: the PhaseResult list of the run.
    status: nominal, impact, no_liftoff or drive_limit.
    flags: warnings such as interface_tensile, drive_braking or a disarmed event.
    """

    metrics: dict[str, Any]
    timeseries: pd.DataFrame
    loss_budget: LossBudget | None
    assist_budget: AssistEnergyBudget | None
    assumptions: list[str]
    phases: list[PhaseResult]
    status: Status
    flags: list[str]
    events: pd.DataFrame = field(default_factory=empty_events)


@dataclass(frozen=True)
class RunResult:
    """A resolved run together with its Result."""

    name: str
    resolved: ResolvedRun
    result: Result


@dataclass(frozen=True)
class SensitivityRow:
    """One sensitivity case: ``of`` re-run with ``param`` moved by the signed ``fraction``
    (its perturbed value ``value_yaml_units``, the number as it stands in the config,
    i.e. in the parameter's YAML units such as t or s, not SI, kept so the case can be
    reproduced from the file; ``value_si`` the same number in SI with its unit
    ``value_si_unit``, from ``si_value``), compared against the unchanged baseline
    (``comparison``) and, for a ``vehicle.`` parameter, against the baseline re-run
    with the same vehicle perturbation (``baseline_perturbed``,
    ``comparison_perturbed``); for a run parameter the baseline is unaffected, so both
    comparisons are the same and ``baseline_perturbed`` is None."""

    of: str
    param: str
    fraction: float
    value_yaml_units: float | None
    value_si: float | None
    value_si_unit: str
    result: RunResult
    comparison: dict[str, Any]
    baseline_perturbed: RunResult | None
    comparison_perturbed: dict[str, Any]

    @property
    def is_vehicle_param(self) -> bool:
        """True when the parameter lives in the vehicle file (``vehicle.`` prefix)."""
        return self.param.startswith(VEHICLE_PREFIX)


@dataclass(frozen=True)
class ExperimentResult:
    """Baseline, variants, their comparison, the sensitivity cases and the provenance of
    one experiment run. ``sensitivity_note`` is what the summary's Sensitivity section
    prints when ``sensitivity`` is empty (why no case ran: none declared, skipped, a
    sweep point)."""

    experiment_name: str
    vehicle_name: str
    baseline: RunResult
    variants: dict[str, RunResult]
    comparison: dict[str, dict[str, Any]]
    git: dict[str, Any]
    timestamp_utc: str
    comparison_basis: str = COMPARISON_BASIS
    sensitivity: list[SensitivityRow] = field(default_factory=list)
    sensitivity_note: str = SENSITIVITY_NONE_DECLARED

    @property
    def runs(self) -> dict[str, RunResult]:
        """Baseline first, then every variant, keyed by name."""
        return {self.baseline.name: self.baseline, **self.variants}


@dataclass(frozen=True)
class SweepResult:
    """One sweep: its 1-based index, the run it perturbs, the axis paths and the points.

    ``sweep_index`` is 1-based and names the ``sweep_<n>`` directory;
    config.SweepPoint.sweep_index (on every entry of ``points``) is 0-based, so
    ``point.sweep_index + 1 == sweep_index`` (checked by run_sweep). Build paths and
    labels from this field, not from the points.
    """

    sweep_index: int
    of: str
    axes: list[str]
    points: list[SweepPoint]
    results: list[RunResult]
    comparisons: list[dict[str, Any]]
    run_dirs: list[Path]


# ------------------------------------------------------------------------ simulate

SIM_ASSUMPTIONS: tuple[str, ...] = (
    "loss quadratures reset at release; the identity is accounted from release onward",
    "a vehicle at rest on the ground is clamped until its thrust exceeds its weight; no "
    "gravity loss accrues while clamped (propellant burned then is reported as burned "
    "before flight)",
    "felt axial acceleration is T/m in flight (vacuum thrust, unthrottled), g_eff while "
    "clamped and (F_int + T)/m_v = sddot + g_eff sin phi on the track",
)
TRACK_ASSUMPTIONS: tuple[str, ...] = (
    "track phase: 1-DOF along the track in a flat local frame with constant g_eff; the "
    "carriage stays on the track at release; carriage braking is not modelled as a phase "
    "(its distance v^2/(2 a_brake) is added to the facility length)",
    "hot start: the propellant burned before release is reported with its delta-v "
    "equivalent; the exhaust impingement fraction f_imp on the carriage is an assumed "
    "amendment to the track equation (the system keeps (1 - f_imp) T)",
    "drive energy: electrical_energy = (positive drive work) / efficiency; no regeneration "
    "is credited for any negative (braking) drive work",
)
# Added to a run in which a stage's ignition failed and the unpowered fall-back coast
# actually ran (docs/physics.md, "Failed-ignition coast"): what that coast leaves out.
FAILED_IGNITION_ASSUMPTIONS: tuple[str, ...] = (
    "failed ignition: the fall-back coast is drag-free (no atmosphere in Phase 1; "
    "docs/physics.md, 'Failed-ignition coast', gives the order of magnitude of the "
    "neglected drag for the F9 class at its exit speed)",
    "failed ignition: no abort is modelled (a tilted exit that carries the vehicle clear "
    "of the mouth is the planar branch of Phase 2/3); Coriolis drift during the coast is "
    "neglected (omega_p = 0)",
)
# Added on top of FAILED_IGNITION_ASSUMPTIONS when the failed run had a track.
FAILED_IGNITION_TRACK_ASSUMPTIONS: tuple[str, ...] = (
    "failed ignition: the braked carriage parks its braking distance beyond the track "
    "exit, in the fall-back path (failed_carriage_alt_m); the vehicle would meet it "
    "there first, on the way down (failed_t_carriage_s, failed_speed_at_carriage_mps, "
    "from the drag-free coast), unless the carriage is withdrawn in time, and no impact "
    "with it is modelled: the return to the mouth, the impact at the ground and the "
    "shaft-bottom speed are the obstacle-free values",
    "failed ignition: the speed at the shaft bottom is derived from the impact speed at "
    "the ground and the fall from there to the track start (v^2 = v_impact^2 + 2 g_eff "
    "(z_impact - z_track_start)), not integrated",
)


def gravity_assumption(gravity: Gravity) -> str:
    """The assumption line naming the ascent gravity model ``simulate`` was handed."""
    if isinstance(gravity, InverseSquareGravity):
        return (
            f"gravity mu/r^2 in flight (mu = {gravity.mu_m3s2:.10g} m^3/s^2; "
            "InverseSquareGravity, the run model; ConstantGravity exists only for tests)"
        )
    if isinstance(gravity, ConstantGravity):
        return (
            f"constant gravity g = {gravity.g_mps2:.7g} m/s^2 in flight (analytic test model, "
            "not the run model)"
        )
    return f"gravity model {type(gravity).__name__} in flight"


def _phase_samples(res: PhaseResult, dt: float) -> tuple[np.ndarray, np.ndarray]:
    """Sample times [s] and states of one PhaseResult: the phase boundaries plus every
    multiple of dt strictly inside, from the dense output; a phase without dense
    output (closed-form hold, pass-through) contributes its own samples."""
    if res.dense is None:
        return np.asarray(res.t, dtype=float), np.asarray(res.y, dtype=float)
    t0, t1 = float(res.spec.t0), float(res.t_end)
    ts = np.concatenate(([t0], sample_grid(t0, t1, dt), [t1]))
    ys = np.asarray(res.dense(ts), dtype=float)
    ys[:, 0] = res.y[:, 0]
    ys[:, -1] = res.y_end
    return ts, ys


def _track_rows(ts: np.ndarray, ys: np.ndarray, params: TrackParams) -> dict[str, Any]:
    """Time-series columns of an ASSIST phase from its track-layout samples: the
    ascent-frame view (z, v, m through ``track_to_vertical``), the thrust, the felt
    axial acceleration and the track observables (``track_observables``)."""
    obs = [track_observables(float(t), ys[:, i], params) for i, t in enumerate(ts)]
    vert = np.column_stack([track_to_vertical(ys[:, i], params) for i in range(len(ts))])
    layout = VERTICAL_LAYOUT
    part: dict[str, Any] = {
        "z_m": layout.get(vert, "z_m"),
        "v_mps": layout.get(vert, "v_mps"),
        "m_kg": layout.get(vert, "m_kg"),
        "thrust_N": np.array([params.thrust_N(float(t)) for t in ts]),
        "thrust_vac_N": np.array([params.thrust_vac_N(float(t)) for t in ts]),
        "accel_felt_g": np.array([o["felt_g"] for o in obs]),
        "s_m": params.layout.get(ys, "s_m"),
        "drive_force_N": np.array([o["F_drive_N"] for o in obs]),
        "interface_force_N": np.array([o["F_int_N"] for o in obs]),
        "drive_power_W": np.array([o["P_drive_W"] for o in obs]),
        "track_normal_g_vehicle": np.array([o["N_vehicle_g"] for o in obs]),
        "track_normal_g_carriage": np.array([o["N_carriage_g"] for o in obs]),
    }
    for name in layout.names:
        if name.startswith("J_"):
            part[name] = np.zeros(len(ts))  # the ascent quadratures start at release
    return part


def sample_trace(trace: RunTrace, vehicle: Vehicle, settings: IntegratorSettings) -> pd.DataFrame:
    """The time series of a run: every phase sampled at settings.sample_dt_s plus every
    phase boundary, with the thrust, the felt (proper) axial acceleration in g0 and the
    loss quadratures; columns TIMESERIES_COLUMNS. accel_felt_g is T/m in free flight,
    g_eff while clamped (the hold-down carries the weight, so the vehicle feels
    1 g_eff, not the thrust building under it) and (F_int + T)/m_v = sddot + g_eff sin
    phi on the track. ASSIST rows show the ascent-frame view of the track state (z from
    the track start altitude, v = sdot sin phi) plus the TRACK_COLUMNS, which are NaN
    everywhere else; their ascent quadratures read 0 (the accounting starts at
    release)."""
    layout = VERTICAL_LAYOUT
    parts: list[dict[str, Any]] = []
    for res in trace.phases:
        ts, ys = _phase_samples(res, settings.sample_dt_s)
        params = res.spec.params
        if isinstance(params, TrackParams):
            part = _track_rows(ts, ys, params)
            part.update(
                {
                    "t_s": ts,
                    "t_rel_release_s": ts - trace.t_release_s,
                    "phase": np.full(len(ts), res.spec.kind, dtype=object),
                    "stage": np.full(
                        len(ts), vehicle.stage_names[res.spec.stage_index], dtype=object
                    ),
                }
            )
            parts.append(part)
            continue
        m = np.asarray(layout.get(ys, "m_kg"), dtype=float)
        if isinstance(params, HoldParams):
            t_vac = np.array([params.thrust_vac_N(float(t)) for t in ts])
            thrust = np.array([params.thrust_N(float(t)) for t in ts])
            felt = np.full(len(ts), to_g(params.g_eff_mps2))
        else:
            schedule = getattr(params, "schedule", None)
            p_amb = float(getattr(params, "p_amb_pa", 0.0))
            if schedule is None:
                t_vac = np.zeros(len(ts))
                thrust = np.zeros(len(ts))
            else:
                t_vac = np.array([schedule.thrust_vac_N(float(t)) for t in ts])
                thrust = np.array([schedule.thrust_N(float(t), p_amb) for t in ts])
            felt = to_g(thrust / m)
        part: dict[str, Any] = {
            "t_s": ts,
            "z_m": layout.get(ys, "z_m"),
            "v_mps": layout.get(ys, "v_mps"),
            "m_kg": m,
            "t_rel_release_s": ts - trace.t_release_s,
            "thrust_N": thrust,
            "thrust_vac_N": t_vac,
            "accel_felt_g": felt,
            "phase": np.full(len(ts), res.spec.kind, dtype=object),
            "stage": np.full(len(ts), vehicle.stage_names[res.spec.stage_index], dtype=object),
        }
        for name in layout.names:
            if name.startswith("J_"):
                part[name] = layout.get(ys, name)
        for name in TRACK_COLUMNS:
            part[name] = np.full(len(ts), np.nan)
        parts.append(part)
    if not parts:
        return empty_timeseries()
    frame = pd.concat([pd.DataFrame(p) for p in parts], ignore_index=True)
    return frame[list(TIMESERIES_COLUMNS)]


def events_frame(trace: RunTrace) -> pd.DataFrame:
    """The events of a run as a DataFrame with columns EVENT_COLUMNS."""
    if not trace.events:
        return empty_events()
    rows = [
        {
            "t_s": e.t_s,
            "event": e.name,
            "phase": e.phase,
            "stage": e.stage,
            "z_m": e.z_m,
            "v_mps": e.v_mps,
            "m_kg": e.m_kg,
        }
        for e in trace.events
    ]
    return pd.DataFrame(rows)[list(EVENT_COLUMNS)]


def _peak_felt(
    frame: pd.DataFrame, kinds: Container[str] | None = None
) -> tuple[float | None, float | None, float | None, str | None]:
    """(peak felt axial acceleration in g0, its time relative to release [s], the mass
    there [kg], the phase kind it occurs in) over the rows of the given phase kinds
    (every row when None), or Nones when there are none."""
    rows = frame if kinds is None else frame[frame["phase"].isin(kinds)]
    if rows.empty:
        return None, None, None, None
    i = int(rows["accel_felt_g"].to_numpy().argmax())
    row = rows.iloc[i]
    return (
        float(row["accel_felt_g"]),
        float(row["t_rel_release_s"]),
        float(row["m_kg"]),
        str(row["phase"]),
    )


def _rel_release(trace: RunTrace, t_s: float | None) -> float | None:
    """t_s - t_release [s]: the run's absolute time t_s on the release clock every
    metric uses; None without a time or before a release (a track run that stopped
    on the track never released)."""
    if t_s is None or trace.y_release is None:
        return None
    return t_s - trace.t_release_s


def run_metrics(
    trace: RunTrace,
    vehicle: Vehicle,
    budget: LossBudget,
    frame: pd.DataFrame,
    assist_name: str,
) -> dict[str, Any]:
    """The flat metrics dict of a run (SI; times relative to release unless the key says
    otherwise). Items a run did not reach are None (n/a in the summary, null in JSON,
    skipped by ``compare``); status and flags live on Result, not here.

    Two "burned before" bookkeepings: ``*_before_release`` counts up to t_release (the
    hold before t = 0 and, with a track, the push); ``*_before_flight`` counts up to the
    start of the free flight, which adds the propellant burned while clamped past
    t = 0 waiting for liftoff (an extended hold). The loss budget starts at the flight
    start, so dv_vac_mps + dv_vac_equiv_before_flight_mps = c ln(m0/m_final) for a
    first-stage burn: the ``before_flight`` pair is what an identity line against the
    liftoff mass must use.

    A pad always releases (the hold-down opens at t = 0, whether or not the vehicle
    then lifts off). A track run that stopped on the track (status ``drive_limit``)
    never released: every release item (t_release_s, speed, altitude, mass, the
    ``before_release`` pair) and every time counted from release
    (``t_ign_rel_release_s_*``, ``final_t_s``, the burnout, apex and impact times) is
    None, and what burned is in ``hold_propellant_burned_kg`` and
    ``propellant_burned_on_track_kg``; the time series' ``t_rel_release_s`` column then
    counts from the push start (t = 0).

    ``peak_felt_axial_g`` (a CLAUDE.md summary item) is the peak felt axial
    acceleration over the whole run: the hold (1 g_eff), the track ((F_int + T)/m_v)
    and the free flight (T/m); ``peak_felt_axial_g_phase``, ``_t_s`` and ``_mass_kg``
    say where it occurs and the mass there. ``peak_felt_g_flight`` (with ``_t_s`` and
    ``_mass_kg``) is the free-flight peak alone.

    A pad has no track: every assist item (drive energy, electrical energy, drive
    power, interface force, track-normal load, braking distance, facility length) is
    0 for it, one convention for the whole set (there is no drive, no carriage and no
    facility, so the quantities are zero, not unmeasured); ``track_metrics`` overwrites
    them for a run with a track.
    """
    layout = VERTICAL_LAYOUT
    stage0 = vehicle.stages[0]
    m0 = vehicle.liftoff_mass_kg()
    t_rel = trace.t_release_s
    y_rel = trace.y_release
    y_fs = trace.y_flight_start
    m_release = None if y_rel is None else float(layout.get(y_rel, "m_kg"))
    m_flight = None if y_fs is None else float(layout.get(y_fs, "m_kg"))
    metrics: dict[str, Any] = {
        "liftoff_mass_kg": m0,
        "assist_model": assist_name,
        "t_release_s": None if y_rel is None else t_rel,
        "speed_at_release_mps": None if y_rel is None else abs(float(layout.get(y_rel, "v_mps"))),
        "alt_at_release_m": None if y_rel is None else float(layout.get(y_rel, "z_m")),
        "mass_at_release_kg": m_release,
        "propellant_burned_before_release_kg": None if m_release is None else m0 - m_release,
        "dv_vac_equiv_before_release_mps": (
            None if m_release is None else stage0.c_mps * math.log(m0 / m_release)
        ),
        "t_flight_start_s": _rel_release(trace, trace.t_flight_start_s),
        "mass_at_flight_start_kg": m_flight,
        "propellant_burned_before_flight_kg": None if m_flight is None else m0 - m_flight,
        "dv_vac_equiv_before_flight_mps": (
            None if m_flight is None else stage0.c_mps * math.log(m0 / m_flight)
        ),
        "hold_duration_s": None if trace.hold is None else trace.hold.duration_s,
        "hold_extension_s": None if trace.hold is None else trace.hold.extension_s,
        "hold_down_force_min_N": None if trace.hold is None else trace.hold.force_min_N,
        "hold_propellant_burned_kg": (
            None if trace.hold is None else trace.hold.propellant_burned_kg
        ),
    }
    for stage in vehicle.stages:
        metrics[f"t_ign_rel_release_s_{stage.name}"] = _rel_release(
            trace, trace.t_ign_abs_s.get(stage.name)
        )
    bo = trace.burnouts.get(stage0.name)
    metrics["stage1_burnout_t_s"] = None if bo is None else _rel_release(trace, bo[0])
    metrics["stage1_burnout_speed_mps"] = (
        None if bo is None else abs(float(layout.get(bo[1], "v_mps")))
    )
    metrics["stage1_burnout_alt_m"] = None if bo is None else float(layout.get(bo[1], "z_m"))
    metrics["stage1_burnout_mass_kg"] = None if bo is None else float(layout.get(bo[1], "m_kg"))
    if trace.phases:
        last = trace.phases[-1]
        metrics["final_t_s"] = _rel_release(trace, last.t_end)
        metrics["final_speed_mps"] = abs(float(layout.get(last.y_end, "v_mps")))
        metrics["final_alt_m"] = float(layout.get(last.y_end, "z_m"))
        metrics["final_mass_kg"] = float(layout.get(last.y_end, "m_kg"))
    apexes = [e for e in trace.events if e.name == "apex"]
    top = max(apexes, key=lambda e: e.z_m) if apexes else None
    metrics["apex_alt_m"] = None if top is None else top.z_m
    metrics["apex_t_s"] = None if top is None else _rel_release(trace, top.t_s)
    impact = trace.first_event("impact")
    metrics["impact_t_s"] = None if impact is None else _rel_release(trace, impact.t_s)
    metrics["impact_speed_mps"] = None if impact is None else abs(impact.v_mps)
    peak_g, peak_t, peak_m, _phase = _peak_felt(frame, ASCENT_KINDS)
    metrics["peak_felt_g_flight"] = peak_g
    metrics["peak_felt_g_flight_t_s"] = peak_t
    metrics["peak_felt_g_flight_mass_kg"] = peak_m
    # The run-wide peak: hold, track and flight rows together (the CLAUDE.md item).
    axial_g, axial_t, axial_m, axial_phase = _peak_felt(frame)
    metrics.update(
        {
            "dv_vac_mps": budget.dv_vac,
            "gravity_loss_mps": budget.gravity,
            "gravity_loss_duration_mps": budget.gravity_duration,
            "gravity_loss_alt_mps": budget.gravity_alt,
            "drag_loss_mps": budget.drag,
            "steering_loss_mps": budget.steering,
            "back_pressure_loss_mps": budget.back_pressure,
            "speed_start_mps": budget.speed_start,
            "speed_end_mps": budget.speed_end,
            "identity_residual_mps": budget.residual_mps(),
            "peak_felt_axial_g": axial_g,
            "peak_felt_axial_g_t_s": None if axial_t is None or y_rel is None else axial_t,
            "peak_felt_axial_g_mass_kg": axial_m,
            "peak_felt_axial_g_phase": axial_phase,
            # A pad has no track: every assist item is 0 (one convention for the whole
            # set); ``track_metrics`` overwrites them for a run with a track.
            "peak_track_normal_g": 0.0,
            "track_normal_g_vehicle_peak": 0.0,
            "track_normal_g_carriage_peak": 0.0,
            "assist_energy_J": 0.0,
            "assist_energy_kWh": 0.0,
            "electrical_energy_J": 0.0,
            "electrical_energy_kWh": 0.0,
            "peak_drive_power_W": 0.0,
            "drive_power_min_W": 0.0,
            "peak_interface_force_N": 0.0,
            "interface_force_min_N": 0.0,
            "braking_distance_m": 0.0,
            "facility_length_m": 0.0,
        }
    )
    return metrics


def track_metrics(
    trace: RunTrace,
    assist: AssistModel,
    track: TrackGeometry,
    budget: AssistEnergyBudget,
    frame: pd.DataFrame,
) -> dict[str, Any]:
    """The track metrics of an assisted run (SI; units in the names; docs/physics.md,
    "Silo model ... and every reported quantity").

    Force peaks and minima are taken over the sampled ASSIST rows of the time series
    (every sample_dt_s plus both ends of every sub-phase, so the push start, the kinks
    and the release are always included; exact for the forces of the
    prescribed-acceleration drive, which are monotone within a lit sub-phase). The
    drive power is not monotone in general, so its extrema come from the dense output
    (``losses.drive_power_extrema``): drive_power_peak_W = max(0, max P) with its
    absolute time drive_power_peak_t_s (0 for a push in which the drive only brakes),
    and drive_power_min_W = min(0, min P), the braking power the drive must absorb (0
    when it only pushes). exit_speed_mps and push_time_s are the release state (None
    when the run stopped on the track); the facility length includes the carriage
    braking distance from the exit speed; drive_energy_J is the net drive work of the
    energy identity, drive_work_in_J and drive_work_out_J its positive and negative
    parts (``losses.drive_work_split``), and electrical_energy_J = drive_work_in_J /
    efficiency: the electricity the drive draws, with no regeneration credited for any
    braking work (an assumption, stated in the assumptions list).
    propellant_burned_on_track_kg counts from the push start to the end of the last
    track phase. felt_g_track_peak is the peak felt axial acceleration over the ASSIST
    rows, with its time relative to release (felt_g_track_peak_t_s; None when the run
    never released) and the vehicle mass there (felt_g_track_peak_mass_kg). The keys
    named here are canonical; the CLAUDE.md summary names of TRACK_METRIC_ALIASES
    (assist_energy_J/kWh, peak_drive_power_W, peak_interface_force_N) are written
    beside them with the same numbers, and peak_track_normal_g = max(vehicle, carriage).
    """
    rows = frame[frame["phase"] == ASSIST_KIND]
    assist_phases = trace.assist_phases()
    y_rel = trace.y_release
    layout = VERTICAL_LAYOUT
    v_exit = None if y_rel is None else abs(float(layout.get(y_rel, "v_mps")))
    first, last = assist_phases[0], assist_phases[-1]
    track_layout = first.spec.params.layout
    m_start = float(track_layout.get(first.y[:, 0], "m_kg"))
    m_end = float(track_layout.get(last.y_end, "m_kg"))
    e_drive = budget.work_drive
    work_in, work_out = drive_work_split(assist_phases, track_layout)
    electrical = work_in / assist.efficiency
    p_max, t_p_max, p_min, _t_p_min = drive_power_extrema(assist_phases, track_layout)
    p_peak = max(0.0, p_max)
    felt_peak, felt_t, felt_m, _phase = _peak_felt(frame, {ASSIST_KIND})
    n_v = float(rows["track_normal_g_vehicle"].max())
    n_c = float(rows["track_normal_g_carriage"].max())
    out: dict[str, Any] = {
        "exit_speed_mps": v_exit,
        "push_time_s": None if y_rel is None else trace.t_release_s,
        "felt_g_track_peak": felt_peak,
        "felt_g_track_peak_t_s": None if y_rel is None else felt_t,
        "felt_g_track_peak_mass_kg": felt_m,
        "interface_force_peak_N": float(rows["interface_force_N"].max()),
        "interface_force_min_N": float(rows["interface_force_N"].min()),
        "drive_force_peak_N": float(rows["drive_force_N"].max()),
        "drive_energy_J": e_drive,
        "drive_energy_kWh": float(j_to_kwh(e_drive)),
        "drive_work_in_J": work_in,
        "drive_work_out_J": work_out,
        "electrical_energy_J": electrical,
        "electrical_energy_kWh": float(j_to_kwh(electrical)),
        "drive_power_peak_W": p_peak,
        "drive_power_peak_t_s": t_p_max,
        "drive_power_min_W": min(0.0, p_min),
        "braking_distance_m": None if v_exit is None else assist.braking_distance_m(v_exit),
        "facility_length_m": (None if v_exit is None else assist.facility_length_m(track, v_exit)),
        "propellant_burned_on_track_kg": m_start - m_end,
        "track_normal_g_vehicle_peak": n_v,
        "track_normal_g_carriage_peak": n_c,
        "assist_energy_residual_rel": budget.residual_rel(),
        "track_start_altitude_m": track.start_altitude_m,
        "carriage_mass_kg": assist.carriage_mass_kg,
        # CLAUDE.md summary item: the track value overwrites the pad's zero.
        "peak_track_normal_g": max(n_v, n_c),
    }
    # The CLAUDE.md-named aliases (same numbers; they overwrite the pad's zeros too).
    out.update({alias: out[canonical] for alias, canonical in TRACK_METRIC_ALIASES.items()})
    return out


def track_flags(frame: pd.DataFrame, drive_work_out_J: float = 0.0) -> list[str]:
    """Run flags of the push: ``interface_tensile`` when the interface force is negative
    anywhere on the sampled ASSIST rows (the vehicle would have to be held back on the
    carriage); ``drive_braking`` when the drive did negative work (drive_work_out_J >
    0: it braked the engine, with allow_negative_drive_force or a push at the
    drive-limit threshold whose event was disarmed at t0)."""
    rows = frame[frame["phase"] == ASSIST_KIND]
    if rows.empty:
        return []
    flags: list[str] = []
    f_min = float(rows["interface_force_N"].min())
    if f_min < 0.0:
        t_min = float(rows["t_s"].iloc[int(rows["interface_force_N"].to_numpy().argmin())])
        flags.append(
            f"interface_tensile: the carriage-vehicle interface force reaches {f_min:.6g} N "
            f"(tension) at t = {t_min:.6g} s during the push"
        )
    if drive_work_out_J > 0.0:
        flags.append(
            f"drive_braking: the drive did {drive_work_out_J:.6g} J of negative work (braking "
            "the engine) during the push; drive_energy_J is the net, electrical_energy_J "
            "counts the positive work only (no regeneration assumed)"
        )
    return flags


def last_burn_end_s(trace: RunTrace, t_fail_s: float) -> float:
    """The absolute time [s] the unpowered flight that ends in a failed ignition began:
    the last burnout at or before t_fail_s [s] (a later stage failing after its staging
    coast), else the flight start (a first stage: release, or the liftoff root). The
    fall-back apex of a failed later stage can sit inside a long staging coast, before
    the failure itself, and still belongs to that coast."""
    burnouts = [t for t, _y in trace.burnouts.values() if t <= t_fail_s + ZERO_SPAN_S]
    if burnouts:
        return max(burnouts)
    return trace.t_release_s if trace.t_flight_start_s is None else trace.t_flight_start_s


def descent_crossing(
    trace: RunTrace, z_m: float, t_from_s: float
) -> tuple[float, np.ndarray] | None:
    """Where a falling ascent phase starting at or after t_from_s [s] first crosses
    altitude z_m [m] downward: (absolute time [s], ascent state there in
    VERTICAL_LAYOUT) from the phases' dense output (brentq), or None when none does. A
    phase boundary within ATOL_M of z_m is taken as the crossing itself, so a crossing
    at the impact altitude is the impact event's time and state exactly. Frame: the
    +z-up datum frame of the ascent state."""
    i_z = VERTICAL_LAYOUT.index("z_m")
    for phase in trace.ascent_phases():
        spec = phase.spec
        if spec.sigma != -1 or spec.t0 < t_from_s - ZERO_SPAN_S:
            continue
        z_start = float(phase.y[i_z, 0])
        z_end = float(phase.y_end[i_z])
        if z_start < z_m - ATOL_M or z_end > z_m + ATOL_M:
            continue
        if abs(z_end - z_m) <= ATOL_M:
            return phase.t_end, np.asarray(phase.y_end, dtype=float)
        if abs(z_start - z_m) <= ATOL_M or phase.dense is None:
            return spec.t0, np.asarray(phase.y[:, 0], dtype=float)

        def height_above(t: float, dense: OdeSolution = phase.dense) -> float:
            return float(dense(t)[i_z]) - z_m

        t_cross = float(brentq(height_above, spec.t0, phase.t_end))
        return t_cross, np.asarray(phase.dense(t_cross), dtype=float)
    return None


def descent_crossing_time_s(trace: RunTrace, z_m: float, t_from_s: float) -> float | None:
    """The absolute time [s] of ``descent_crossing`` (the first downward crossing of
    z_m [m] by a falling ascent phase starting at or after t_from_s [s]), or None."""
    found = descent_crossing(trace, z_m, t_from_s)
    return None if found is None else found[0]


def carriage_park_altitude_m(
    trace: RunTrace, assist: AssistModel, track: TrackGeometry | None
) -> float | None:
    """Altitude [m] in the +z-up datum frame at which the braked carriage comes to rest
    after release: its braking distance from the exit speed (``braking_distance_m``)
    along the track tangent beyond the exit, z = z_exit + d_brake sin phi(L). None on
    a pad or when the run never released."""
    if track is None or trace.y_release is None:
        return None
    v_exit = abs(float(VERTICAL_LAYOUT.get(trace.y_release, "v_mps")))
    d_brake = assist.braking_distance_m(v_exit)
    z_exit = track.start_altitude_m + track.z(track.length_m)
    return z_exit + d_brake * math.sin(track.phi(track.length_m))


def failed_ignition_metrics(
    trace: RunTrace, g_eff_mps2: float, assist: AssistModel, track: TrackGeometry | None
) -> dict[str, Any]:
    """The metrics of a run in which a stage's ignition failed (docs/physics.md,
    "Failed-ignition coast"); an empty dict when no stage failed.

    Inputs: the RunTrace (``failed_stage`` set); g_eff_mps2, the constant effective
    gravity of the track [m/s^2]; assist, the assist model (its carriage braking
    distance); track, the track geometry or None for a pad. Output keys (SI; times
    relative to release; None when the run did not reach the item):
    ``failed_stage`` (the stage name); ``failed_apex_alt_m``, the highest apex [m] of
    the unpowered flight that ends in the failure, i.e. after the last burnout before
    it or after release for a first stage (``last_burn_end_s``; None when the vehicle
    was already falling, or never flew); ``failed_t_apex_s`` [s]; for a track run,
    ``failed_carriage_alt_m`` [m], where the braked carriage parks
    (``carriage_park_altitude_m``), ``failed_t_carriage_s`` [s] and
    ``failed_speed_at_carriage_mps`` [m/s], when and how fast the falling vehicle
    first comes down to that altitude (the first obstacle in the fall-back path; None
    when the apex is below it); ``failed_t_return_s`` [s], when the vehicle is back
    down at its release altitude (the silo mouth, or the pad): the first downward
    crossing of z_release after that last burn (``descent_crossing_time_s``), which is
    the impact event itself when the mouth is at the ground (the plan's datum,
    exit_altitude_m = 0) and None when the ground is above the mouth;
    ``failed_impact_speed_mps`` [m/s], |v| at the impact event (the ground, z =
    z_ground); and, for a track run, ``failed_speed_at_shaft_bottom_mps`` [m/s], the
    speed a vehicle falling on from the impact point would have at the track start
    (the shaft bottom), derived and not integrated: v_bottom^2 = v_impact^2 + 2 g_eff
    (z_impact - z_track_start) under the track's constant g_eff (the mirror of the
    push; z_impact - z_track_start = L when the mouth is at the ground). The carriage
    items and the shaft-bottom speed are the obstacle-free coast values: no impact
    with the carriage is modelled (stated in FAILED_IGNITION_TRACK_ASSUMPTIONS).
    Frame: the +z-up datum frame with z = 0 at the ground.
    """
    if trace.failed_stage is None:
        return {}
    i_v = VERTICAL_LAYOUT.index("v_mps")
    t_fail = trace.t_fail_s
    top = None
    t_return = None
    z_carriage = carriage_park_altitude_m(trace, assist, track)
    at_carriage = None
    if t_fail is not None and trace.y_release is not None:
        t_from = last_burn_end_s(trace, t_fail)
        apexes = [e for e in trace.events if e.name == "apex" and e.t_s >= t_from - ZERO_SPAN_S]
        top = max(apexes, key=lambda e: e.z_m) if apexes else None
        z_release = float(trace.y_release[VERTICAL_LAYOUT.index("z_m")])
        t_return = descent_crossing_time_s(trace, z_release, t_from)
        if z_carriage is not None:
            at_carriage = descent_crossing(trace, z_carriage, t_from)
    impact = trace.first_event("impact")
    v_impact = None if impact is None else abs(impact.v_mps)
    v_bottom = None
    if impact is not None and track is not None:
        depth = impact.z_m - track.start_altitude_m
        v_bottom = math.sqrt(v_impact * v_impact + 2.0 * g_eff_mps2 * depth)
    return {
        "failed_stage": trace.failed_stage,
        "failed_apex_alt_m": None if top is None else top.z_m,
        "failed_t_apex_s": None if top is None else _rel_release(trace, top.t_s),
        "failed_carriage_alt_m": z_carriage,
        "failed_t_carriage_s": None if at_carriage is None else _rel_release(trace, at_carriage[0]),
        "failed_speed_at_carriage_mps": (
            None if at_carriage is None else abs(float(at_carriage[1][i_v]))
        ),
        "failed_t_return_s": _rel_release(trace, t_return),
        "failed_impact_speed_mps": v_impact,
        "failed_speed_at_shaft_bottom_mps": v_bottom,
    }


def failed_ignition_flags(
    trace: RunTrace, track: TrackGeometry | None, z_ground_m: float
) -> list[str]:
    """Run flags of a failed-ignition track run whose mouth (the track exit) is not at
    the ground z_ground_m [m] the impact event fires on: the coast metrics then split
    between the two altitudes, and the flag says which is which. Inputs: the RunTrace
    (with an impact event), the track geometry and the planner's ground altitude; empty
    for a pad, a run without an impact, or a mouth at the ground (within ATOL_M).
    Frame: the +z-up datum frame."""
    if track is None or trace.failed_stage is None or trace.first_event("impact") is None:
        return []
    z_mouth = track.start_altitude_m + track.z(track.length_m)
    if abs(z_mouth - z_ground_m) <= ATOL_M:
        return []
    return [
        f"failed ignition: the track exit (mouth) is at z = {z_mouth:.6g} m and the impact "
        f"at the ground z = {z_ground_m:.6g} m; failed_t_return_s is the downward crossing "
        "of the mouth altitude (None when the ground is above the mouth), "
        "failed_impact_speed_mps is at the ground, and the shaft-bottom speed counts the "
        "fall from the ground to the track start"
    ]


def ignition_timing_metrics(
    trace: RunTrace,
    vehicle: Vehicle,
    ignition: Mapping[str, IgnitionSpec],
    g_eff_mps2: float,
    metrics: Mapping[str, Any],
) -> dict[str, Any]:
    """The constant-g yardsticks of the first stage's ignition timing (SI; docs/physics.md,
    "Ignition-after-release loss" and "Figures of merit in 1-D").

    Inputs: the RunTrace; the Vehicle; the IgnitionSpec per stage; g_eff_mps2, the
    reference gravity of the loss split [m/s^2]; metrics, the ``run_metrics`` dict (the
    ``before_flight`` pair). Output keys: ``ignition_loss_formula_mps`` [m/s], the speed
    lost at burnout against an instant full-thrust start at release from the same state
    (``losses.ignition_loss_analytic_mps`` with g_ref = g_eff, the stage-1 startup shape,
    the ignition time relative to release, the liftoff mass and the exact lag form for
    the stage's burn time); ``preflight_burn_cost_mps`` [m/s], the net delta-v cost of
    the propellant burned before the free flight, c ln(m0/m_flight) - g_eff (m0 -
    m_flight)/mdot_full: the delta-v spent while clamped or on the track less the
    gravity loss those full-thrust seconds would have cost in flight (the pad baseline's
    value is the "hold-down credit" a variant that burns nothing before flight
    receives; ``compare`` takes the difference). Both are None for a failed ignition or
    a run that never released or flew. Also the stage's resolved startup, so the summary
    can say how each run ignites: ``startup_kind_<stage>`` (the effective kind: step,
    ramp or lag; step is instant full thrust, a yardstick no engine achieves) and
    ``t_startup_s_<stage>`` (t_ramp for a ramp, tau for a lag, 0 for a step) [s].
    Frame-free (masses and times only).
    """
    stage0 = vehicle.stages[0]
    spec = ignition[stage0.name]
    startup = stage0.startup if spec.startup is None else spec.startup
    m0 = vehicle.liftoff_mass_kg()
    mdot = stage0.mdot_full_kgps
    t_ign_rel = _rel_release(trace, trace.t_ign_abs_s.get(stage0.name))
    formula = None
    if t_ign_rel is not None and not spec.fails:
        formula = ignition_loss_analytic_mps(
            g_eff_mps2, t_ign_rel, startup, stage0.c_mps, mdot, m0, t_burn_s=stage0.burn_time_s
        )
    burned = metrics.get("propellant_burned_before_flight_kg")
    dv_before = metrics.get("dv_vac_equiv_before_flight_mps")
    cost = None
    if burned is not None and dv_before is not None:
        cost = dv_before - g_eff_mps2 * burned / mdot
    kind = startup.effective_kind
    t_startup = {"ramp": startup.t_ramp_s, "lag": startup.tau_s}.get(kind, 0.0)
    return {
        "ignition_loss_formula_mps": formula,
        "preflight_burn_cost_mps": cost,
        f"startup_kind_{stage0.name}": kind,
        f"t_startup_s_{stage0.name}": t_startup,
    }


def simulate(
    vehicle: Vehicle,
    ignition: Mapping[str, IgnitionSpec],
    gravity: Gravity,
    g_eff_mps2: float,
    assist: AssistModel,
    track: TrackGeometry | None,
    start: AscentStart | None,
    end: str,
    settings: IntegratorSettings,
) -> Result:
    """Run one configuration and return its Result (pure: no I/O).

    Inputs: the Vehicle; ignition, an IgnitionSpec per stage name; gravity, the ascent
    Gravity (``run`` passes InverseSquareGravity(MU); tests may inject
    ConstantGravity); g_eff_mps2, the pad/track effective gravity [m/s^2] and the
    reference g_ref of the gravity-loss split; assist, the assist model (``NoAssist``
    for a pad, ``ConstantAccelAssist`` with its track otherwise); track, the track
    geometry (None for a pad; required for any other model); start, the AscentStart
    of a pad run (z0, v0 at release; None = the pad at rest; a track run accepts only
    the default); end, one of phases.END_KINDS; settings, the IntegratorSettings.
    Output: a Result with the sampled time series, the events, the metrics, the
    LossBudget from release onward, the AssistEnergyBudget of the push (None for a
    pad), the run's status (nominal, impact, no_liftoff, drive_limit) and flags
    (``interface_tensile`` is evaluated over the ASSIST rows only; ``drive_braking``
    when the drive did negative work). A run in which a stage's ignition failed
    (``IgnitionSpec.fails``) carries the ``failed_*`` metrics
    (``failed_ignition_metrics``), the ``failed_ignition_flags`` (a track mouth not at
    the ground) and, when its fall-back coast actually ran (``t_fail_s`` set: not a
    pad ``no_liftoff``), FAILED_IGNITION_ASSUMPTIONS plus the carriage lines of
    FAILED_IGNITION_TRACK_ASSUMPTIONS when it had a track. Every run also carries the
    constant-g ignition-timing yardsticks of ``ignition_timing_metrics``
    (``ignition_loss_formula_mps``, ``preflight_burn_cost_mps``). The assumptions
    name the gravity model and the g_eff actually used, not the run model's (``run``
    adds those).
    """
    planner = VerticalPlanner(vehicle, ignition, gravity, g_eff_mps2, end, settings)
    if track is None:
        if assist.name != "none":
            raise ValueError(f"assist model {assist.name!r} needs a track")
        trace = planner.run_pad(AscentStart() if start is None else start)
    else:
        if assist.name == "none":
            raise ValueError("a track was given with the 'none' assist model")
        if start is not None and start != AscentStart():
            raise ValueError("a track run starts at rest at the track start; no AscentStart")
        trace = planner.run_track(assist, track)
    budget = loss_budget(trace.ascent_phases())
    frame = sample_trace(trace, vehicle, settings)
    metrics = run_metrics(trace, vehicle, budget, frame, assist.name)
    metrics.update(ignition_timing_metrics(trace, vehicle, ignition, g_eff_mps2, metrics))
    flags = list(trace.flags)
    assumptions = [
        *PHASE1_ASSUMPTIONS,
        gravity_assumption(gravity),
        f"pad/track effective gravity g_eff = {g_eff_mps2:.7g} m/s^2, also the g_ref of the "
        "gravity-loss split",
        *SIM_ASSUMPTIONS,
    ]
    assist_budget: AssistEnergyBudget | None = None
    if track is not None:
        assist_phases = trace.assist_phases()
        assist_budget = assist_energy_budget(
            assist_phases,
            assist_phases[0].spec.params.layout,
            assist.carriage_mass_kg,
            g_eff_mps2,
        )
        metrics.update(track_metrics(trace, assist, track, assist_budget, frame))
        flags += track_flags(frame, metrics["drive_work_out_J"])
        assumptions += [
            *TRACK_ASSUMPTIONS,
            f"track: straight, L = {track.length_m:.6g} m at {track.phi(0.0):.6g} rad above "
            f"horizontal, start altitude {track.start_altitude_m:.6g} m (exit at "
            f"{track.start_altitude_m + track.z(track.length_m):.6g} m)",
        ]
    if trace.failed_stage is not None:
        metrics.update(failed_ignition_metrics(trace, g_eff_mps2, assist, track))
        flags += failed_ignition_flags(trace, track, planner.z_ground_m)
        if trace.t_fail_s is not None:  # the coast ran (not a pad no_liftoff)
            assumptions += FAILED_IGNITION_ASSUMPTIONS
            if track is not None:
                assumptions += FAILED_IGNITION_TRACK_ASSUMPTIONS
    assumptions += [*trace.assumptions, *assist.assumptions()]
    return Result(
        metrics=metrics,
        timeseries=frame,
        loss_budget=budget,
        assist_budget=assist_budget,
        assumptions=assumptions,
        phases=list(trace.phases),
        status=trace.status,  # type: ignore[arg-type]
        flags=flags,
        events=events_frame(trace),
    )


def ignition_specs(run_config: RunConfig, vehicle: Vehicle) -> dict[str, IgnitionSpec]:
    """One IgnitionSpec per stage from the run's ignition block (defaults when absent),
    with startup overrides resolved against the vehicle's own Startup."""
    return {
        stage.name: IgnitionSpec.from_config(run_config.ignition_for(stage.name), stage.startup)
        for stage in vehicle.stages
    }


def run(run_config: RunConfig, vehicle: Vehicle) -> Result:
    """Run one validated configuration (SI) and return its Result.

    Builds InverseSquareGravity(MU_EARTH_M3S2) for the ascent, g_eff = g_eff_track(0)
    (omega_p = 0 in Phase 1, stated in the assumptions) for the pad and the track, the
    IgnitionSpecs from the config, the assist model and its track
    (``assist.build_assist``), and calls ``simulate``; RUN_MODEL_ASSUMPTIONS go in front
    of the assumptions ``simulate`` derived from what it was handed.
    """
    g_eff = g_eff_track(OMEGA_P_PHASE1_RADS)
    assist, track = build_assist(run_config.assist, g_eff)
    result = simulate(
        vehicle=vehicle,
        ignition=ignition_specs(run_config, vehicle),
        gravity=InverseSquareGravity(MU_EARTH_M3S2),
        g_eff_mps2=g_eff,
        assist=assist,
        track=track,
        start=AscentStart(),
        end=run_config.end,
        settings=IntegratorSettings.from_config(run_config.integrator),
    )
    return replace(result, assumptions=[*RUN_MODEL_ASSUMPTIONS, *result.assumptions])


def run_resolved(resolved: ResolvedRun) -> RunResult:
    """Run a ResolvedRun and wrap the Result with its name and config. Every exception
    propagates (FAILED.txt is written by the caller)."""
    vehicle = resolved.to_vehicle()
    return RunResult(resolved.name, resolved, run(resolved.run, vehicle))


# ---------------------------------------------------------------------- comparison


def _is_number(x: object) -> bool:
    """True for int/float and numpy numbers (bool excluded), finite or not."""
    return isinstance(x, int | float | np.integer | np.floating) and not isinstance(x, bool)


def _is_finite_number(x: object) -> bool:
    """True for a number that is neither NaN nor infinite."""
    return _is_number(x) and math.isfinite(float(x))


def _is_pandas_missing(x: object) -> bool:
    """True for the pandas missing scalars pd.NA and pd.NaT (an unavailable value)."""
    return x is pd.NA or x is pd.NaT


def _is_numeric_or_missing(x: object) -> bool:
    """True for a number (finite or not) or a pandas missing scalar: a numeric metric
    whose value may be unavailable."""
    return _is_number(x) or _is_pandas_missing(x)


def _delta(a: Any, b: Any) -> float | None:
    """a - b when both are finite numbers, else None (unavailable)."""
    if _is_finite_number(a) and _is_finite_number(b):
        return float(a) - float(b)
    return None


def identity_budget(result: Result) -> tuple[LossBudget, str] | None:
    """The loss budget the identity line of a run is written at, and the name of that
    point: ``stage1_burnout`` when the run reached a stage-1 burnout (the budget over
    the ascent phases up to and including the BURN ended by the propellant event, so
    speed_end is the burnout speed whatever the run's ``end``), else ``end`` (the run's
    own budget, e.g. the impact of a failed-ignition coast). None when the run has no
    budget (a hand-built Result) or never flew (an all-zero budget, no phases)."""
    if result.loss_budget is None:
        return None
    ascent = [p for p in result.phases if p.spec.kind in ASCENT_KINDS]
    if not ascent:
        return None
    for i, phase in enumerate(ascent):
        if phase.spec.stage_index == 0 and phase.ended_by == "propellant":
            return loss_budget(ascent[: i + 1]), "stage1_burnout"
    return result.loss_budget, "end"


def payload_equiv_kg(vehicle: Vehicle, dv_mps: float) -> float | None:
    """Ideal-screening payload equivalent [kg] of a delta-v gain dv_mps [m/s]: the
    payload change at which the ideal rocket-equation delta-v (``ideal_dv_mps``, the
    vehicle's loss-averaged screening Isp) moves by exactly -dv_mps. Positive dv gives
    ``payload_gain_kg`` (payload added); negative dv the payload that would have to be
    removed (brentq on [0, payload]), or None when even an empty payload bay cannot
    recover the loss. An ideal rocket equation at fixed losses: not a payload result.
    """
    if dv_mps >= 0.0:
        return payload_gain_kg(vehicle, dv_mps)
    p0 = vehicle.payload_mass_kg
    if p0 <= 0.0:
        return None
    dv0 = ideal_dv_mps(vehicle)
    target = dv0 - dv_mps  # the higher delta-v a lighter payload must give

    def shortfall(p: float) -> float:
        return ideal_dv_mps(vehicle, p) - target

    if shortfall(0.0) < 0.0:
        return None
    return float(brentq(shortfall, 0.0, p0)) - p0


def compare(
    result: Result,
    baseline: Result,
    vehicle: Vehicle | None = None,
    instant: Result | None = None,
) -> dict[str, Any]:
    """The comparison of a run against the baseline (docs/physics.md, "Figures of merit
    in 1-D"); SI, units in the keys.

    ``delta_<metric>`` for every numeric metric both results carry (unavailable when
    either operand is NaN, inf, pd.NA or pd.NaT: None, i.e. null in JSON, an empty CSV
    cell, "n/a" in a summary); ``status`` and ``baseline_status``. Then the 1-D figures
    of merit: ``stage1_burnout_speed_delta_mps`` and ``stage1_burnout_alt_delta_m``; the
    identity decomposition of the speed delta at ``identity_point`` (``identity_budget``:
    the stage-1 burnout of both runs when they reached it, else the run's end, named
    ``<variant point> vs <baseline point>`` when they differ), ``d_speed_mps`` =
    ``d_speed_release_mps`` (the flight-start speed: 0 on a pad, the exit speed on a
    track) + ``d_dv_vac_mps`` - ``d_gravity_duration_mps`` - ``d_gravity_alt_mps`` -
    ``d_drag_mps`` - ``d_steering_mps`` - ``d_back_pressure_mps`` +
    ``identity_line_residual_mps`` (expected ~1e-12 m/s; CLAUDE.md allows 0.01);
    ``hold_down_credit_mps``, the baseline's ``preflight_burn_cost_mps`` minus the
    run's (what a run gains by not burning while clamped, or loses by burning more);
    ``ignition_loss_formula_mps`` (the run's constant-g yardstick, copied for the side
    by side); ``ignition_loss_integrated_mps``, the ``instant`` run's stage-1 burnout
    speed minus this run's, defined only when both flew from the same release state
    (speed and altitude within SAME_RELEASE_*); ``ideal_screening_payload_equiv_kg``,
    ``payload_equiv_kg`` of the burnout speed delta on ``vehicle`` (ideal rocket
    equation at fixed losses; not a payload result);
    ``ideal_screening_payload_at_release_speed_kg``, the README yardstick the CLAUDE.md
    rule names: ``payload_gain_kg`` of this run's speed at release (0 for a pad), so
    the two payload figures can be compared in summary.md itself; and
    ``unexplained_gain_mps`` = d_speed - (d_speed_release + hold_down_credit -
    d_gravity_alt), the CLAUDE.md "beats the release speed" check: a gain beyond the
    release speed, the hold-down credit and the altitude term is unexplained when it
    exceeds IDENTITY_TOL_MPS (for the same vehicle it is minus the post-release
    ignition loss, the steering and the back-pressure deltas, so at most ~0). The
    check is defined at a stage-1 burnout on both sides only (``identity_point`` ==
    ``stage1_burnout``): a run without one (a failed ignition) gets None, since the
    credit and the altitude term of an impact-to-burnout difference mean nothing.
    Items either run lacks are None.
    """
    out: dict[str, Any] = {"status": result.status, "baseline_status": baseline.status}
    for key, value in result.metrics.items():
        base = baseline.metrics.get(key)
        if _is_numeric_or_missing(value) and _is_numeric_or_missing(base):
            out[f"delta_{key}"] = _delta(value, base)
    m, b = result.metrics, baseline.metrics
    d_bo = _delta(m.get("stage1_burnout_speed_mps"), b.get("stage1_burnout_speed_mps"))
    out["stage1_burnout_speed_delta_mps"] = d_bo
    out["stage1_burnout_alt_delta_m"] = _delta(
        m.get("stage1_burnout_alt_m"), b.get("stage1_burnout_alt_m")
    )
    terms = (
        ("d_speed_mps", "speed_end"),
        ("d_speed_release_mps", "speed_start"),
        ("d_dv_vac_mps", "dv_vac"),
        ("d_gravity_duration_mps", "gravity_duration"),
        ("d_gravity_alt_mps", "gravity_alt"),
        ("d_drag_mps", "drag"),
        ("d_steering_mps", "steering"),
        ("d_back_pressure_mps", "back_pressure"),
    )
    bv, bb = identity_budget(result), identity_budget(baseline)
    if bv is None or bb is None:
        out["identity_point"] = None
        out.update(dict.fromkeys([k for k, _ in terms]))
        out["identity_line_residual_mps"] = None
    else:
        out["identity_point"] = bv[1] if bv[1] == bb[1] else f"{bv[1]} vs {bb[1]}"
        for key, attr in terms:
            out[key] = getattr(bv[0], attr) - getattr(bb[0], attr)
        out["identity_line_residual_mps"] = out["d_speed_mps"] - (
            out["d_speed_release_mps"]
            + out["d_dv_vac_mps"]
            - out["d_gravity_duration_mps"]
            - out["d_gravity_alt_mps"]
            - out["d_drag_mps"]
            - out["d_steering_mps"]
            - out["d_back_pressure_mps"]
        )
    out["hold_down_credit_mps"] = _delta(
        b.get("preflight_burn_cost_mps"), m.get("preflight_burn_cost_mps")
    )
    out["ignition_loss_formula_mps"] = m.get("ignition_loss_formula_mps")
    out["ignition_loss_integrated_mps"] = None
    if instant is not None:
        same_v = _delta(m.get("speed_at_release_mps"), instant.metrics.get("speed_at_release_mps"))
        same_z = _delta(m.get("alt_at_release_m"), instant.metrics.get("alt_at_release_m"))
        if (
            same_v is not None
            and same_z is not None
            and abs(same_v) <= SAME_RELEASE_SPEED_TOL_MPS
            and abs(same_z) <= SAME_RELEASE_ALT_TOL_M
        ):
            out["ignition_loss_integrated_mps"] = _delta(
                instant.metrics.get("stage1_burnout_speed_mps"), m.get("stage1_burnout_speed_mps")
            )
    out["ideal_screening_payload_equiv_kg"] = (
        None if vehicle is None or d_bo is None else payload_equiv_kg(vehicle, d_bo)
    )
    v_release = m.get("speed_at_release_mps")
    out["ideal_screening_payload_at_release_speed_kg"] = (
        None
        if vehicle is None or not _is_finite_number(v_release) or float(v_release) < 0.0
        else payload_gain_kg(vehicle, float(v_release))
    )
    credit = out["hold_down_credit_mps"]
    out["unexplained_gain_mps"] = (
        None
        if out["identity_point"] != "stage1_burnout" or credit is None
        else out["d_speed_mps"] - (out["d_speed_release_mps"] + credit - out["d_gravity_alt_mps"])
    )
    return out


# --------------------------------------------------------------------- sensitivity


def perturbed_value(case_run: ResolvedRun, param: str) -> float | None:
    """The number a sensitivity case's dotted parameter has after the perturbation
    (``config.read_value`` on the case's run or vehicle dict, in the parameter's YAML
    units), or None when it is not a number."""
    if param.startswith(VEHICLE_PREFIX):
        value = read_value(case_run.vehicle_dict, param[len(VEHICLE_PREFIX) :])
    else:
        value = read_value(case_run.run_dict, param)
    return float(value) if _is_finite_number(value) else None


def si_value(param: str, value_yaml: float | None) -> tuple[float | None, str]:
    """A dotted config parameter's value in SI: (value, unit). The unit follows the
    key's YAML suffix (SI_SUFFIX_CONVERSIONS: ``_t`` -> kg through units.t_to_kg,
    ``_kN`` -> N, ``_deg`` -> rad, ``_km`` -> m, ``_g`` -> m/s^2, ``_kWh`` -> J; ``_s``,
    ``_m``, ``_kg`` ... unchanged), read off the last non-index segment of the path
    (``vehicle.screening.stage_isp_eff_s.0`` -> ``stage_isp_eff_s`` -> s). A key with
    no listed suffix (``assist.drive_efficiency``) is dimensionless: unchanged, unit
    DIMENSIONLESS_UNIT. None stays None."""
    segments = [s for s in param.split(".") if not s.isdigit()]
    key = segments[-1] if segments else param
    suffix = key.rsplit("_", 1)[-1] if "_" in key else ""
    convert, unit = SI_SUFFIX_CONVERSIONS.get(suffix, (lambda x: x, DIMENSIONLESS_UNIT))
    return (None if value_yaml is None else float(convert(value_yaml))), unit


def run_sensitivity(
    resolved: ResolvedExperiment,
    baseline: RunResult,
    run_names: Container[str] | None = None,
) -> list[SensitivityRow]:
    """Run every sensitivity case of the experiment (``resolved.sensitivity``, already
    perturbed in memory by ``config.apply_overrides`` at load) whose parent run is in
    ``run_names`` (every case when None) and compare each against the unchanged
    baseline and, for a ``vehicle.`` parameter, against the baseline re-run with the
    same vehicle perturbation (one re-run per distinct perturbation, shared by the
    cases; a case of the baseline itself is its own perturbed baseline). Runs nothing
    when the experiment declares no sensitivity. Returns the rows in declaration
    order."""
    rows: list[SensitivityRow] = []
    perturbed_baselines: dict[tuple[str, float], RunResult] = {}
    for case in resolved.sensitivity:
        if run_names is not None and case.of not in run_names:
            continue
        rr = run_resolved(case.run)
        vehicle = case.run.to_vehicle()
        comparison = compare(rr.result, baseline.result, vehicle)
        base_pert: RunResult | None = None
        if case.param.startswith(VEHICLE_PREFIX):
            if case.of == baseline.name:
                base_pert = rr
            else:
                key = (case.param, case.fraction)
                if key not in perturbed_baselines:
                    perturbed_baselines[key] = run_resolved(
                        resolve_run(
                            baseline.name, resolved.baseline.run_dict, case.run.vehicle_dict
                        )
                    )
                base_pert = perturbed_baselines[key]
        comparison_pert = (
            comparison if base_pert is None else compare(rr.result, base_pert.result, vehicle)
        )
        value_yaml = perturbed_value(case.run, case.param)
        value_si, unit = si_value(case.param, value_yaml)
        rows.append(
            SensitivityRow(
                of=case.of,
                param=case.param,
                fraction=case.fraction,
                value_yaml_units=value_yaml,
                value_si=value_si,
                value_si_unit=unit,
                result=rr,
                comparison=comparison,
                baseline_perturbed=base_pert,
                comparison_perturbed=comparison_pert,
            )
        )
    return rows


def sensitivity_record(row: SensitivityRow) -> dict[str, Any]:
    """The metrics.json record of one sensitivity case: the case, its perturbed value
    in SI (``value_si`` with ``value_si_unit``) and as it stands in the config
    (``value_yaml_units``: the parameter's YAML units, the one key of the record not in
    SI, kept to reproduce the case), the headline deltas against both baselines, the
    full metrics record and both comparisons."""
    m = row.result.result.metrics
    return {
        "of": row.of,
        "param": row.param,
        "fraction": row.fraction,
        "value_si": row.value_si,
        "value_si_unit": row.value_si_unit,
        "value_yaml_units": row.value_yaml_units,
        "run": row.result.name,
        "status": row.result.result.status,
        "flags": row.result.result.flags,
        "stage1_burnout_speed_mps": m.get("stage1_burnout_speed_mps"),
        "stage1_burnout_speed_delta_mps": row.comparison.get("stage1_burnout_speed_delta_mps"),
        "stage1_burnout_speed_delta_vs_perturbed_baseline_mps": row.comparison_perturbed.get(
            "stage1_burnout_speed_delta_mps"
        ),
        "baseline_perturbed": row.baseline_perturbed is not None,
        "baseline_perturbed_stage1_burnout_speed_mps": (
            None
            if row.baseline_perturbed is None
            else row.baseline_perturbed.result.metrics.get("stage1_burnout_speed_mps")
        ),
        "metrics": metrics_record(row.result.result),
        "comparison": row.comparison,
        "comparison_vs_perturbed_baseline": row.comparison_perturbed,
    }


# ---------------------------------------------------------------------- run dir / git


def utc_timestamp(now: datetime | None = None) -> str:
    """UTC timestamp as YYYYMMDDTHHMMSSZ (no colons: NTFS-safe)."""
    now = datetime.now(UTC) if now is None else now.astimezone(UTC)
    return now.strftime(TIMESTAMP_FORMAT)


def make_run_dir(root: Path, experiment_name: str, now: datetime | None = None) -> Path:
    """Create results/<experiment>/<YYYYMMDDTHHMMSSZ>/ and return it.

    On a collision the suffixes -2, -3, ... are tried; every attempt uses
    ``mkdir(exist_ok=False)`` so an existing directory is never reused. The experiment
    name must be a safe single path component (check_name).
    """
    base = Path(root) / check_name(experiment_name, "experiment name")
    base.mkdir(parents=True, exist_ok=True)
    stamp = utc_timestamp(now)
    for n in range(1, MAX_DIR_SUFFIX + 1):
        candidate = base / (stamp if n == 1 else f"{stamp}-{n}")
        try:
            candidate.mkdir(exist_ok=False)
        except FileExistsError:
            continue
        return candidate
    raise FileExistsError(f"more than {MAX_DIR_SUFFIX} run directories for {stamp} in {base}")


def _git(args: list[str], cwd: Path) -> str:
    """Run one git command and return its stdout (raises on failure or timeout)."""
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=GIT_TIMEOUT_S,
        check=True,
    )
    return proc.stdout.strip()


def git_info(repo_root: Path) -> dict[str, Any]:
    """Describe the git state of the repository containing a directory, for provenance.

    Returns ``{"hash": "<sha12>" | "unborn" | "no-git", "dirty": bool | None,
    "error": str | None}``. ``no-git`` when git is missing, fails or the directory is
    outside a repository; ``unborn`` for a repository without commits. ``dirty`` is
    evaluated at the repository top level (``git rev-parse --show-toplevel``), whatever
    subdirectory was given, and counts tracked changes and untracked files outside the
    top-level results tree (results/ holds tracked summaries, so it must not make the
    code look modified); it is None when ``git status`` itself failed or timed out, with
    the reason in ``error``. ``error`` otherwise carries git's own message when git
    refused (for example "dubious ownership"), None for a plain "not a repository".
    Never raises.
    """
    try:
        inside = _git(["rev-parse", "--is-inside-work-tree"], repo_root)
        top = Path(_git(["rev-parse", "--show-toplevel"], repo_root)) if inside == "true" else None
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return {"hash": "no-git", "dirty": False, "error": f"{type(exc).__name__}: {exc}"}
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        error = None if not stderr or NOT_A_REPO_MARKER in stderr else stderr
        return {"hash": "no-git", "dirty": False, "error": error}
    if top is None:  # inside a bare repository: no work tree, nothing to describe
        return {"hash": "no-git", "dirty": False, "error": None}
    try:
        sha = _git(["rev-parse", "--short=12", "HEAD"], top)
    except subprocess.CalledProcessError:
        sha = "unborn"
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"hash": "no-git", "dirty": False, "error": f"{type(exc).__name__}: {exc}"}
    try:
        dirty: bool | None = bool(
            _git(["status", "--porcelain", "--", ".", GIT_EXCLUDE_RESULTS], top)
        )
        error = None
    except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
        dirty, error = None, f"git status failed: {type(exc).__name__}: {exc}"
    return {"hash": sha, "dirty": dirty, "error": error}


def git_label(git: Mapping[str, Any]) -> str:
    """``<sha12>``, ``<sha12>-dirty``, ``<sha12>-dirty?`` (status unknown), ``unborn`` or
    ``no-git`` for summaries."""
    label = str(git.get("hash", "no-git"))
    if label in ("unborn", "no-git"):
        return label
    dirty = git.get("dirty")
    if dirty is None:
        return label + "-dirty?"
    return label + "-dirty" if dirty else label


# -------------------------------------------------------------------------- writers


def json_safe(obj: Any) -> Any:
    """Convert a nested structure to JSON-safe values: NaN/inf/pd.NA/pd.NaT -> None, numpy
    scalars -> Python, tuples/sets -> lists, Path -> POSIX str, keys -> str."""
    if _is_pandas_missing(obj):
        return None
    if isinstance(obj, Mapping):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple | set | frozenset):
        return [json_safe(v) for v in obj]
    if isinstance(obj, bool | np.bool_):
        return bool(obj)
    if isinstance(obj, int | np.integer):
        return int(obj)
    if isinstance(obj, float | np.floating):
        x = float(obj)
        return x if math.isfinite(x) else None
    if isinstance(obj, np.ndarray):
        return json_safe(obj.tolist())
    if isinstance(obj, Path):
        return obj.as_posix()
    if obj is None or isinstance(obj, str):
        return obj
    return str(obj)


def write_json(path: Path, data: Any) -> Path:
    """Write JSON (UTF-8, LF, indent 2, allow_nan=False after json_safe)."""
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(json_safe(data), fh, ensure_ascii=False, indent=2, allow_nan=False)
        fh.write("\n")
    return path


def write_yaml(path: Path, data: Any) -> Path:
    """Write YAML (UTF-8, LF, key order preserved, unicode allowed)."""
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)
    return path


def write_summary(out_dir: Path, text: str) -> Path:
    """Write summary.md (UTF-8, LF) and return its path."""
    path = Path(out_dir) / "summary.md"
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text if text.endswith("\n") else text + "\n")
    return path


def write_csv(path: Path, frame: pd.DataFrame) -> Path:
    """Write a DataFrame as CSV (UTF-8, LF, %.12g floats, no index; header even if empty)."""
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        frame.to_csv(fh, float_format=CSV_FLOAT_FORMAT, lineterminator="\n", index=False)
    return path


def write_timeseries(result: Result, out_dir: Path) -> None:
    """Write <out_dir>/timeseries.csv and <out_dir>/events.csv."""
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "timeseries.csv", result.timeseries)
    write_csv(out_dir / "events.csv", result.events)


def plot_stem(prefix: str, quantity: str) -> str:
    """File stem ``<prefix>_<quantity>`` with every run of characters outside
    ``[A-Za-z0-9_.-]`` replaced by ``_`` (a name such as ``F/N`` becomes ``F_N``)."""
    return PLOT_STEM_UNSAFE.sub("_", f"{prefix}_{quantity}")


def _plot_text(text: str) -> str:
    """Escape ``$`` so matplotlib does not read the label as mathtext."""
    return text.replace("$", "\\$")


def plot_panels(result: Result) -> list[PlotPanel]:
    """The (quantity, columns, y labels) panels ``write_plots`` draws for a run:
    PLOT_PANELS always, plus PLOT_TRACK_PANELS when the run has ASSIST rows (the track
    columns are NaN everywhere else)."""
    frame = result.timeseries
    panels = list(PLOT_PANELS)
    if "phase" in frame.columns and bool((frame["phase"] == ASSIST_KIND).any()):
        panels += PLOT_TRACK_PANELS
    return panels


def write_plots(result: Result, plots_dir: Path, prefix: str) -> list[Path]:
    """Write plots/<plot_stem(prefix, quantity)>.png for every panel of ``plot_panels``
    (altitude, speed, mass_thrust, felt_g and, on a track, track_forces and
    drive_power), each against the time since release (PLOT_ABSCISSA). A panel with
    two columns and one y label draws both on that axis, labelled (same unit); with
    one y label per column each column gets its own axis, the second a twin y axis on
    the right (mass and thrust: different units, never one scale). Nothing is written
    when the time series is empty or lacks the abscissa; a panel whose columns are all
    missing is skipped.

    Figures are built from matplotlib.figure.Figure and saved through the Agg canvas
    that PNG output selects, so no pyplot state and no global backend switch is needed:
    importing this module leaves a notebook's inline backend alone.
    """
    frame = result.timeseries
    if frame.empty or PLOT_ABSCISSA not in frame.columns:
        return []
    plots_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for quantity, columns, ylabels in plot_panels(result):
        present = [c for c in columns if c in frame.columns]
        if not present:
            continue
        twin = len(ylabels) > 1
        fig = Figure(figsize=PLOT_FIGSIZE_IN, dpi=PLOT_DPI)
        ax = fig.subplots()
        axes = [ax]
        handles: list[Line2D] = []
        for i, (col, color) in enumerate(zip(present, PLOT_SERIES_COLORS, strict=False)):
            target = ax if i == 0 or not twin else ax.twinx()
            if target is not ax:
                axes.append(target)
            (handle,) = target.plot(
                frame[PLOT_ABSCISSA],
                frame[col],
                color=color,
                linewidth=PLOT_LINE_WIDTH,
                label=_plot_text(col),
            )
            handles.append(handle)
            if twin:
                target.set_ylabel(_plot_text(ylabels[columns.index(col)]), color=color)
                target.tick_params(axis="y", colors=color)
        if len(present) > 1:
            ax.legend(handles=handles, frameon=False)
        ax.set_xlabel(PLOT_ABSCISSA_LABEL)
        if not twin:
            ax.set_ylabel(_plot_text(ylabels[0]))
        ax.set_title(_plot_text(f"{prefix}: {quantity}"))
        ax.grid(True, color=PLOT_GRID_COLOR, linewidth=PLOT_GRID_LINE_WIDTH)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for extra in axes[1:]:  # a twin axis keeps its own right spine for its scale
            extra.spines["top"].set_visible(False)
        fig.tight_layout()
        path = plots_dir / f"{plot_stem(prefix, quantity)}.png"
        fig.savefig(path, format="png")
        written.append(path)
    return written


def write_failure_marker(out_dir: Path, exc: BaseException) -> Path:
    """Write <out_dir>/FAILED.txt with the exception's traceback and return its path.

    Called when a run raised after its directory was created and before summary.md was
    written, so a partial results directory is recognisable. Best effort: a second error
    while writing the marker is swallowed so the original exception propagates.
    """
    path = Path(out_dir) / FAILED_MARKER
    text = (
        "This run raised before its results were complete; the files here are partial.\n\n"
        + "".join(traceback.format_exception(exc))
    )
    try:
        with path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    except OSError:
        pass
    return path


# ------------------------------------------------------------------- summary text


def _fmt(value: Any) -> str:
    """A summary cell: n/a for None, NaN, inf, pd.NA and pd.NaT; a finite number to 6
    significant digits, printed as 0 when its magnitude is below DISPLAY_ZERO_ABS
    (rounding noise in the quantity's own unit; metrics.json keeps the raw value)."""
    if value is None or _is_pandas_missing(value):
        return "n/a"
    if isinstance(value, bool):
        return str(value)
    if _is_number(value):
        if not _is_finite_number(value):
            return "n/a"
        x = float(value)
        return "0" if abs(x) < DISPLAY_ZERO_ABS else f"{x:.6g}"
    return str(value)


def _signed(value: Any) -> str:
    """``_fmt`` with an explicit sign on finite numbers (for the identity lines); a
    magnitude below DISPLAY_ZERO_ABS prints as +0."""
    if not _is_finite_number(value):
        return _fmt(value)
    x = float(value)
    return "+0" if abs(x) < DISPLAY_ZERO_ABS else f"{x:+.6g}"


def _excess_text(value: Any) -> str:
    """The excess of a bound line: the signed number, or ``0 (|excess| <
    EXCESS_NOISE_MPS)`` when its magnitude is rounding noise, n/a when unavailable."""
    if not _is_finite_number(value):
        return _fmt(value)
    x = float(value)
    return f"0 (|excess| < {EXCESS_NOISE_MPS:g})" if abs(x) < EXCESS_NOISE_MPS else f"{x:+.6g}"


def _table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


# Rows of the per-variant table, in the CLAUDE.md order: (label, source, key). The
# source is "m" for a run metric, "c" for a comparison item (the baseline column reads
# "(baseline)"), "phase2" for a metric Phase 2 introduces (NOT_UNTIL_PHASE2 while
# absent), "felt" for the run-wide peak felt g with its phase and "flags" for the flag
# count. Labels carry the units. ``variant_rows`` inserts the stage-1 ignition rows
# (``ignition_rows``: keyed by the first stage's name) after the flags row and the
# before-flight pair (FLIGHT_BURN_ROWS) after the before-release pair when some run
# burned more before its flight than before its release (an extended hold).
NOT_UNTIL_PHASE2 = "n/a (Phase 2)"
type VariantRow = tuple[str, str, str]
VARIANT_ROWS: tuple[VariantRow, ...] = (
    ("status", "status", ""),
    ("flags (see Flags)", "flags", ""),
    ("speed at release [m/s]", "m", "speed_at_release_mps"),
    ("  delta vs baseline [m/s]", "c", "delta_speed_at_release_mps"),
    ("propellant burned before release [kg]", "m", "propellant_burned_before_release_kg"),
    ("  its dv_vac equivalent [m/s]", "m", "dv_vac_equiv_before_release_mps"),
    ("stage-1 burnout speed [m/s]", "m", "stage1_burnout_speed_mps"),
    ("  delta vs baseline [m/s]", "c", "stage1_burnout_speed_delta_mps"),
    ("stage-1 burnout altitude [m]", "m", "stage1_burnout_alt_m"),
    ("  delta vs baseline [m]", "c", "stage1_burnout_alt_delta_m"),
    ("identity point (stage1_burnout, or the run's end)", "c", "identity_point"),
    ("identity: delta speed there [m/s]", "c", "d_speed_mps"),
    ("  = delta speed at release [m/s]", "c", "d_speed_release_mps"),
    ("  + delta dv_vac [m/s]", "c", "d_dv_vac_mps"),
    ("  - delta gravity loss, duration part [m/s]", "c", "d_gravity_duration_mps"),
    ("  - delta gravity loss, altitude part [m/s]", "c", "d_gravity_alt_mps"),
    ("  - delta drag loss [m/s]", "c", "d_drag_mps"),
    ("  - delta steering loss [m/s]", "c", "d_steering_mps"),
    ("  - delta back-pressure loss [m/s]", "c", "d_back_pressure_mps"),
    ("  identity residual [m/s] (must be < 0.01)", "c", "identity_line_residual_mps"),
    (
        "hold-down credit vs baseline [m/s] (baseline's pre-flight burn cost minus this run's)",
        "c",
        "hold_down_credit_mps",
    ),
    (
        "  pre-flight burn cost of this run [m/s] (c ln(m0/m_flight) - g_eff dt_full)",
        "m",
        "preflight_burn_cost_mps",
    ),
    (
        f"ignition loss, integrated vs {INSTANT_VARIANT_NAME} [m/s] (same release state only)",
        "c",
        "ignition_loss_integrated_mps",
    ),
    (
        "ignition loss, constant-g formula vs an instant start at release [m/s]",
        "m",
        "ignition_loss_formula_mps",
    ),
    (
        "ideal-screening payload equivalent of the burnout speed delta [kg] "
        "(ideal rocket equation at fixed losses; not a payload result)",
        "c",
        "ideal_screening_payload_equiv_kg",
    ),
    (
        "  ideal screening at this run's speed at release [kg] (the README yardstick; "
        "same equation, not a payload result)",
        "c",
        "ideal_screening_payload_at_release_speed_kg",
    ),
    ("gravity loss [m/s]", "m", "gravity_loss_mps"),
    ("  duration part [m/s]", "m", "gravity_loss_duration_mps"),
    ("  altitude part [m/s]", "m", "gravity_loss_alt_mps"),
    ("drag loss [m/s]", "m", "drag_loss_mps"),
    ("steering loss [m/s]", "m", "steering_loss_mps"),
    ("back-pressure loss [m/s]", "m", "back_pressure_loss_mps"),
    ("dv_vac from the flight start [m/s]", "m", "dv_vac_mps"),
    ("max-Q [Pa]", "phase2", "max_q_pa"),
    ("peak felt axial g, run-wide [g0] (phase)", "felt", "peak_felt_axial_g"),
    ("  at t after release [s]", "m", "peak_felt_axial_g_t_s"),
    ("  mass there [kg]", "m", "peak_felt_axial_g_mass_kg"),
    ("peak felt g on the track [g0]", "m", "felt_g_track_peak"),
    ("  at t after release [s]", "m", "felt_g_track_peak_t_s"),
    ("  mass there [kg]", "m", "felt_g_track_peak_mass_kg"),
    ("peak felt g in flight [g0]", "m", "peak_felt_g_flight"),
    ("  at t after release [s]", "m", "peak_felt_g_flight_t_s"),
    ("  mass there [kg]", "m", "peak_felt_g_flight_mass_kg"),
    ("interface force, peak [N]", "m", "peak_interface_force_N"),
    ("interface force, minimum [N]", "m", "interface_force_min_N"),
    (
        "hold-down force m g_eff - T, minimum over the hold [N] "
        "(negative = the clamps in tension, holding the vehicle down)",
        "m",
        "hold_down_force_min_N",
    ),
    ("peak track-normal g [g0]", "m", "peak_track_normal_g"),
    ("  vehicle [g0]", "m", "track_normal_g_vehicle_peak"),
    ("  carriage [g0]", "m", "track_normal_g_carriage_peak"),
    ("assist (drive) energy [J]", "m", "assist_energy_J"),
    ("assist (drive) energy [kWh]", "m", "assist_energy_kWh"),
    ("electrical energy [J] (positive drive work / efficiency)", "m", "electrical_energy_J"),
    ("electrical energy [kWh]", "m", "electrical_energy_kWh"),
    ("peak drive power [W]", "m", "peak_drive_power_W"),
    ("braking (negative) drive power, minimum [W]", "m", "drive_power_min_W"),
    ("braking distance [m]", "m", "braking_distance_m"),
    ("facility length incl. braking [m]", "m", "facility_length_m"),
)
# Inserted after the before-release pair when some run's before-flight burn differs.
FLIGHT_BURN_ROWS: tuple[VariantRow, ...] = (
    (
        "propellant burned before the free flight (incl. a hold extension) [kg]",
        "m",
        "propellant_burned_before_flight_kg",
    ),
    ("  its dv_vac equivalent [m/s]", "m", "dv_vac_equiv_before_flight_mps"),
)
FLIGHT_BURN_AFTER_KEY = "dv_vac_equiv_before_release_mps"
# Appended to VARIANT_ROWS when any run carries the failed-ignition items.
FAILED_ROWS: tuple[VariantRow, ...] = (
    ("failed ignition: stage", "m", "failed_stage"),
    ("  apex altitude of the fall-back coast [m]", "m", "failed_apex_alt_m"),
    ("  time of that apex after release [s]", "m", "failed_t_apex_s"),
    ("  parked carriage altitude [m]", "m", "failed_carriage_alt_m"),
    ("  time the vehicle comes down to the carriage [s]", "m", "failed_t_carriage_s"),
    ("  speed there [m/s]", "m", "failed_speed_at_carriage_mps"),
    ("  return to the release altitude [s]", "m", "failed_t_return_s"),
    ("  impact speed at the ground [m/s]", "m", "failed_impact_speed_mps"),
    ("  speed at the shaft bottom [m/s] (derived)", "m", "failed_speed_at_shaft_bottom_mps"),
)


def ignition_rows(stage_name: str) -> tuple[VariantRow, ...]:
    """The rows that say how the first stage (``stage_name``) ignites: t_ign relative
    to release, the startup kind (``ignition_timing_metrics``) and its duration."""
    return (
        (
            "stage-1 ignition, t_ign relative to release [s] (negative = lit before release)",
            "m",
            f"t_ign_rel_release_s_{stage_name}",
        ),
        (
            f"stage-1 startup kind ({STEP_STARTUP_KIND} = instant full thrust: a yardstick, "
            "not achievable)",
            "m",
            f"startup_kind_{stage_name}",
        ),
        ("  its t_ramp or tau [s]", "m", f"t_startup_s_{stage_name}"),
    )


def first_stage_name(er: ExperimentResult) -> str:
    """The name of the baseline vehicle's first stage (the stage the ignition rows and
    the ignition-timing metrics are keyed by)."""
    return str(er.baseline.resolved.vehicle_dict["stages"][0]["name"])


def _flight_burn_differs(er: ExperimentResult) -> bool:
    """True when some run burned more before its free flight than before its release
    (a hold extended past t = 0), so the before-flight pair is worth its rows."""
    for rr in er.runs.values():
        m = rr.result.metrics
        before_flight = m.get("propellant_burned_before_flight_kg")
        before_release = m.get("propellant_burned_before_release_kg")
        if before_flight is None and before_release is None:
            continue  # never released nor flew: nothing to tell apart
        d = _delta(before_flight, before_release)
        if d is None or d != 0.0:
            return True
    return False


def variant_rows(er: ExperimentResult) -> tuple[VariantRow, ...]:
    """VARIANT_ROWS with the ignition rows after the flags row, the before-flight pair
    after the before-release pair when it differs for some run
    (``_flight_burn_differs``), plus FAILED_ROWS when any run carries a
    failed-ignition item."""
    rows: list[VariantRow] = []
    flight_pair = _flight_burn_differs(er)
    stage = first_stage_name(er)
    for row in VARIANT_ROWS:
        rows.append(row)
        if row[1] == "flags":
            rows += ignition_rows(stage)
        elif row[2] == FLIGHT_BURN_AFTER_KEY and flight_pair:
            rows += FLIGHT_BURN_ROWS
    if any("failed_stage" in rr.result.metrics for rr in er.runs.values()):
        rows += FAILED_ROWS
    return tuple(rows)


def step_startup_note(runs: Mapping[str, RunResult], stage_name: str) -> str:
    """One line naming the runs whose first stage starts with a step (instant full
    thrust at ignition: a yardstick that isolates the ignition-timing loss, which no
    engine achieves), or "" when none does."""
    names = [
        name
        for name, rr in runs.items()
        if rr.result.metrics.get(f"startup_kind_{stage_name}") == STEP_STARTUP_KIND
    ]
    if not names:
        return ""
    return (
        f"Note: {', '.join(names)}: stage-1 startup kind {STEP_STARTUP_KIND} is instant full "
        "thrust at ignition, a yardstick that isolates the ignition-timing loss; no engine "
        "achieves it (unphysical), so these columns bound the others, they are not designs."
    )


def _variant_cell(er: ExperimentResult, name: str, source: str, key: str) -> str:
    """One cell of the per-variant table."""
    rr = er.runs[name]
    if source == "status":
        return rr.result.status
    if source == "flags":
        return str(len(rr.result.flags)) if rr.result.flags else "-"
    if source == "phase2":
        value = rr.result.metrics.get(key)
        return NOT_UNTIL_PHASE2 if value is None else _fmt(value)
    if source == "felt":
        value = rr.result.metrics.get(key)
        phase = rr.result.metrics.get(f"{key}_phase")
        return _fmt(value) if value is None or phase is None else f"{_fmt(value)} ({phase})"
    if source == "m":
        return _fmt(rr.result.metrics.get(key))
    if name == er.baseline.name:
        return "(baseline)"
    return _fmt(er.comparison.get(name, {}).get(key))


def variants_table(er: ExperimentResult) -> str:
    """The per-variant table against the baseline: one row per quantity of
    ``variant_rows`` (labels with units), one column per run, the baseline first."""
    names = list(er.runs)
    header = ["quantity", *(f"{n} (baseline)" if n == er.baseline.name else n for n in names)]
    rows = [
        [label, *(_variant_cell(er, n, source, key) for n in names)]
        for label, source, key in variant_rows(er)
    ]
    return _table(header, rows)


SENSITIVITY_HEADER: tuple[str, ...] = (
    "variant",
    "parameter",
    "change",
    "value [SI] (unit in the cell)",
    "value (in the parameter's YAML units)",
    "status",
    "stage-1 burnout speed [m/s]",
    "delta vs baseline, unchanged [m/s]",
    "delta vs baseline with the same vehicle perturbation [m/s]",
    "ideal-screening payload equiv. of the unchanged delta [kg]",
    "ideal-screening payload equiv. of the same-perturbation delta [kg]",
    "exit speed [m/s]",
    "electrical energy [kWh]",
    "peak drive power [W]",
)
SENSITIVITY_CASE_COLUMNS = 3  # variant, parameter, change: the columns a C_D row keeps


def sensitivity_table(rows: Sequence[SensitivityRow], note: str = SENSITIVITY_NONE_DECLARED) -> str:
    """Markdown table of the sensitivity cases (``run_sensitivity``): the perturbed
    value in SI and as in the YAML, the headline delta of the stage-1 burnout speed
    against the unchanged baseline and against the baseline with the same vehicle
    perturbation (marked "= unchanged" for a run parameter, which leaves the baseline
    alone), the payload equivalent of both deltas (the same-perturbation one is the
    concept's benefit; the unchanged one is mostly the vehicle change), plus one C_D
    row per run that has cases, which reads CD_SENSITIVITY_NOTE in Phase 1 (no drag).
    Without any case the table is replaced by ``note``, the reason none ran."""
    if not rows:
        return note
    table_rows: list[list[str]] = []
    for row in rows:
        m = row.result.result.metrics
        same = "" if row.baseline_perturbed is not None else " (= unchanged)"
        table_rows.append(
            [
                row.of,
                row.param,
                f"{row.fraction:+.0%}",
                f"{_fmt(row.value_si)} {row.value_si_unit}",
                _fmt(row.value_yaml_units),
                row.result.result.status,
                _fmt(m.get("stage1_burnout_speed_mps")),
                _signed(row.comparison.get("stage1_burnout_speed_delta_mps")),
                _signed(row.comparison_perturbed.get("stage1_burnout_speed_delta_mps")) + same,
                _signed(row.comparison.get("ideal_screening_payload_equiv_kg")),
                _signed(row.comparison_perturbed.get("ideal_screening_payload_equiv_kg")),
                _fmt(m.get("exit_speed_mps")),
                _fmt(m.get("electrical_energy_kWh")),
                _fmt(m.get("peak_drive_power_W")),
            ]
        )
    filler = [CD_SENSITIVITY_NOTE] * (len(SENSITIVITY_HEADER) - SENSITIVITY_CASE_COLUMNS)
    for name in sorted({row.of for row in rows}):
        table_rows.append([name, "C_D", "+/-10%", *filler])
    return _table(list(SENSITIVITY_HEADER), table_rows)


NOT_A_FIGURE_OF_MERIT = (
    "not a figure of merit: the identity point is not a stage-1 burnout on both sides, "
    "so this delta speed is the difference of two exact budgets at unlike points"
)


def identity_lines(er: ExperimentResult) -> list[str]:
    """One bullet per variant spelling out its identity line against the baseline with
    the residual and whether it closes (IDENTITY_TOL_MPS). A line whose identity point
    is not ``stage1_burnout`` (a variant that never burned out, written at its end) is
    marked NOT_A_FIGURE_OF_MERIT so its delta speed is not read as a result."""
    lines: list[str] = []
    for name in er.variants:
        c = er.comparison.get(name, {})
        residual = c.get("identity_line_residual_mps")
        if residual is None:
            lines.append(f"- {name}: identity line n/a (a run without a flight budget)")
            continue
        closes = "closes" if abs(residual) < IDENTITY_TOL_MPS else "DOES NOT CLOSE"
        point = c.get("identity_point")
        note = "" if point == "stage1_burnout" else f" ({NOT_A_FIGURE_OF_MERIT})"
        lines.append(
            f"- {name}: delta speed at {point} {_signed(c.get('d_speed_mps'))}"
            f" = {_signed(c.get('d_speed_release_mps'))} (speed at release)"
            f" + {_signed(c.get('d_dv_vac_mps'))} (dv_vac)"
            f" - {_signed(c.get('d_gravity_duration_mps'))} (gravity, duration)"
            f" - {_signed(c.get('d_gravity_alt_mps'))} (gravity, altitude)"
            f" - {_signed(c.get('d_drag_mps'))} (drag)"
            f" - {_signed(c.get('d_steering_mps'))} (steering)"
            f" - {_signed(c.get('d_back_pressure_mps'))} (back-pressure)"
            f"; residual {residual:.3g} m/s: {closes} (< {IDENTITY_TOL_MPS:g} m/s){note}"
        )
    return lines if lines else ["(no variants)"]


def payload_yardstick_lines(er: ExperimentResult) -> list[str]:
    """The CLAUDE.md rule in kg: one bullet per variant whose ideal-screening payload
    equivalent exceeds the README yardstick at its release speed
    (``ideal_screening_payload_at_release_speed_kg``), naming what the extra m/s beyond
    the release speed are (the hold-down credit and the altitude term of the bound
    line), then one closing sentence. Variants at or below the yardstick, or without
    both numbers, get no bullet."""
    lines: list[str] = []
    for name in er.variants:
        c = er.comparison.get(name, {})
        equiv = c.get("ideal_screening_payload_equiv_kg")
        yardstick = c.get("ideal_screening_payload_at_release_speed_kg")
        if not (_is_finite_number(equiv) and _is_finite_number(yardstick)) or equiv <= yardstick:
            continue
        beyond = _delta(c.get("d_speed_mps"), c.get("d_speed_release_mps"))
        lines.append(
            f"- {name}: payload equivalent {_fmt(equiv)} kg exceeds the README yardstick "
            f"{_fmt(yardstick)} kg at its release speed; the {_signed(beyond)} m/s beyond the "
            f"release speed are the hold-down credit {_signed(c.get('hold_down_credit_mps'))} "
            f"and the altitude term {_signed(_delta(0.0, c.get('d_gravity_alt_mps')))} m/s "
            f"(unexplained {_excess_text(c.get('unexplained_gain_mps'))} m/s)"
        )
    if lines:
        lines.append(
            "A payload equivalent above the README yardstick at the release speed is the "
            "hold-down credit and the altitude term in kg (ideal rocket equation, both); "
            "the bound lines above say whether anything else contributed."
        )
    else:
        lines.append(
            "No variant's ideal-screening payload equivalent exceeds the README yardstick "
            "at its release speed."
        )
    return lines


def checks_section(er: ExperimentResult) -> str:
    """The Checks section: every variant's identity line, then the CLAUDE.md bound: no
    variant may gain more than its release speed + the hold-down credit + the altitude
    term unexplained (``unexplained_gain_mps`` > IDENTITY_TOL_MPS names a bug; a
    variant without a stage-1 burnout on both sides is listed as not checkable), then
    the same rule in kg (``payload_yardstick_lines``)."""
    lines = [*identity_lines(er), ""]
    over: list[str] = []
    unknown: list[str] = []
    for name in er.variants:
        c = er.comparison.get(name, {})
        excess = c.get("unexplained_gain_mps")
        if excess is None:
            unknown.append(name)
            continue
        lines.append(
            f"- {name}: gain {_signed(c.get('d_speed_mps'))} m/s against the bound "
            f"{_signed(c.get('d_speed_release_mps'))} (speed at release) "
            f"{_signed(c.get('hold_down_credit_mps'))} (hold-down credit) "
            f"{_signed(-c['d_gravity_alt_mps'])} (altitude term): excess "
            f"{_excess_text(excess)} m/s"
        )
        if excess > IDENTITY_TOL_MPS:
            over.append(f"{name} ({excess:+.6g} m/s)")
    lines.append("")
    if over:
        lines.append(
            "Variants exceeding their release speed + hold-down credit + altitude term by "
            f"more than {IDENTITY_TOL_MPS:g} m/s, which the CLAUDE.md rule treats as a bug: "
            + ", ".join(over)
        )
    else:
        lines.append(
            "No variant exceeds its release speed + hold-down credit + altitude term by "
            f"more than {IDENTITY_TOL_MPS:g} m/s."
        )
    if unknown:
        lines.append(
            "Not checkable (no stage-1 burnout on both sides, or no flight budget): "
            + ", ".join(unknown)
        )
    lines += ["", *payload_yardstick_lines(er)]
    return "\n".join(lines)


def assumptions_section(
    runs: Mapping[str, RunResult],
    baseline_name: str | None = None,
    others_label: str = "all variants",
) -> str:
    """Union of assumptions, each attributed to the runs that carry it: ``all runs``,
    ``others_label`` when every run except ``baseline_name`` carries it, else the names."""
    carriers: dict[str, list[str]] = {}
    for name, rr in runs.items():
        for a in rr.result.assumptions:
            carriers.setdefault(a, []).append(name)
    n_runs = len(runs)
    others = [name for name in runs if name != baseline_name]
    lines = []
    for a, names in carriers.items():
        if len(names) == n_runs:
            who = "all runs"
        elif baseline_name is not None and others and names == others:
            who = others_label
        else:
            who = ", ".join(names)
        lines.append(f"- {a} [{who}]")
    return "\n".join(lines) if lines else "(none)"


def flags_section(runs: Mapping[str, RunResult]) -> str:
    """Flags per run, or a note that there are none."""
    lines = [
        f"- {name}: {', '.join(rr.result.flags)}" for name, rr in runs.items() if rr.result.flags
    ]
    return "\n".join(lines) if lines else "(none)"


def provenance_lines(git: Mapping[str, Any], timestamp_utc: str) -> str:
    """Timestamp and git lines for a summary header."""
    lines = [f"- Timestamp (UTC): {timestamp_utc}", f"- Git: {git_label(git)}"]
    if git.get("error"):
        lines.append(f"- Git error: {git['error']}")
    return "\n".join(lines)


def experiment_summary(er: ExperimentResult, header_lines: Sequence[str] = ()) -> str:
    """The summary.md text of an experiment run, in the CLAUDE.md order: title with the
    experiment name, timestamp and git hash; the comparison basis; the per-variant
    table against the baseline (with ``step_startup_note`` under it when a run is a
    step-thrust yardstick); the sensitivity table; the flags; the assumptions (union,
    attributed); the checks (identity lines and the release-speed bound).
    ``header_lines`` (already formatted as ``- ...`` bullets, e.g. a sweep point's axis
    values) go under the baseline line."""
    runs = er.runs
    note = step_startup_note(runs, first_stage_name(er))
    return "\n".join(
        [
            f"# {er.experiment_name} ({er.timestamp_utc}, git {git_label(er.git)})",
            "",
            er.comparison_basis,
            "",
            f"- Vehicle: {er.vehicle_name}",
            f"- Baseline: {er.baseline.name}",
            *header_lines,
            provenance_lines(er.git, er.timestamp_utc),
            "",
            "## Variants against the baseline",
            "",
            variants_table(er),
            *(["", note] if note else []),
            "",
            "## Sensitivity",
            "",
            sensitivity_table(er.sensitivity, er.sensitivity_note),
            "",
            "## Flags",
            "",
            flags_section(runs),
            "",
            "## Assumptions",
            "",
            assumptions_section(runs, er.baseline.name),
            "",
            "## Checks",
            "",
            checks_section(er),
            "",
        ]
    )


# ------------------------------------------------------------------ experiment I/O


def _resolved_config_dict(er: ExperimentResult) -> dict[str, Any]:
    """The resolved_config.yaml content: one vehicle dict, a run dict per run, and the
    vehicle dict again only for runs whose vehicle differs (sensitivity, vehicle sweeps)."""
    base_vehicle = er.baseline.resolved.vehicle_dict
    runs: dict[str, Any] = {}
    for name, rr in er.runs.items():
        entry: dict[str, Any] = {"run": rr.resolved.run_dict}
        if rr.resolved.vehicle_dict != base_vehicle:
            entry["vehicle"] = rr.resolved.vehicle_dict
        runs[name] = entry
    return {
        "experiment": er.experiment_name,
        "timestamp_utc": er.timestamp_utc,
        "git": dict(er.git),
        "comparison_basis": er.comparison_basis,
        "baseline": er.baseline.name,
        "vehicle": base_vehicle,
        "runs": runs,
    }


def metrics_record(result: Result) -> dict[str, Any]:
    """The metrics.json record of one run: its metrics plus ``status`` and ``flags``.

    Raises ValueError when a metric uses a RESERVED_METRIC_KEYS name, which would
    otherwise be overwritten here while summary.md kept the metric (a schema error).
    """
    clash = sorted(RESERVED_METRIC_KEYS & set(result.metrics))
    if clash:
        raise ValueError(f"metrics use reserved keys {clash}; see sim.RESERVED_METRIC_KEYS")
    return {**result.metrics, "status": result.status, "flags": result.flags}


def _metrics_dict(er: ExperimentResult) -> dict[str, Any]:
    return {
        "experiment": er.experiment_name,
        "timestamp_utc": er.timestamp_utc,
        "git": dict(er.git),
        "comparison_basis": er.comparison_basis,
        "baseline": er.baseline.name,
        "runs": {name: metrics_record(rr.result) for name, rr in er.runs.items()},
        "comparison": er.comparison,
        "sensitivity": [sensitivity_record(row) for row in er.sensitivity],
    }


def write_run(experiment_result: ExperimentResult, out_dir: Path, plots: bool) -> Path:
    """Write an experiment's results into out_dir (see the module docstring) and return it."""
    out_dir = Path(out_dir)
    er = experiment_result
    for name in er.runs:
        check_run_name(name)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_yaml(out_dir / "resolved_config.yaml", _resolved_config_dict(er))
    write_json(out_dir / "metrics.json", _metrics_dict(er))
    for name, rr in er.runs.items():
        write_timeseries(rr.result, out_dir / name)
        if plots:
            write_plots(rr.result, out_dir / "plots", name)
    write_summary(out_dir, experiment_summary(er))
    return out_dir


def sweep_point_header(sweep_index: int, point: SweepPoint, n_points: int) -> list[str]:
    """Summary header bullets naming a sweep point: the sweep_<n> directory (1-based
    ``sweep_index``), the point's position, its parent run and its axis values."""
    values = ", ".join(f"{axis} = {value}" for axis, value in point.overrides.items())
    return [
        f"- Sweep: sweep_{sweep_index}, point {point.point_index} of {n_points} "
        f"(of {point.of}): {values}"
    ]


def write_single(
    run_result: RunResult,
    baseline: RunResult,
    er: ExperimentResult,
    out_dir: Path,
    plots: bool,
    header_lines: Sequence[str] = (),
    comparison: Mapping[str, Any] | None = None,
) -> Path:
    """Flat single-run layout for a sweep point (or the sweep's baseline copy):
    resolved_config.yaml, metrics.json, summary.md, timeseries.csv, events.csv, plots/.
    ``header_lines`` (see sweep_point_header) name the point in its summary.md;
    ``comparison`` is the point's ``compare`` dict against the baseline when the caller
    already has it (the sweep index uses the same one), computed here otherwise; the
    baseline copy has none. A sweep point runs no sensitivity case, and its summary
    says so (SENSITIVITY_SWEEP_POINT)."""
    out_dir = Path(out_dir)
    rr = run_result
    check_name(rr.name, "run name")  # sweep points are run_NNNN, so no reserved check here
    out_dir.mkdir(parents=True, exist_ok=True)
    if rr is baseline:
        comparison = {}
    elif comparison is None:
        comparison = {rr.name: compare(rr.result, baseline.result, rr.resolved.to_vehicle())}
    else:
        comparison = {rr.name: dict(comparison)}
    write_yaml(
        out_dir / "resolved_config.yaml",
        {
            "experiment": er.experiment_name,
            "timestamp_utc": er.timestamp_utc,
            "git": dict(er.git),
            "run": rr.resolved.run_dict,
            "vehicle": rr.resolved.vehicle_dict,
        },
    )
    write_json(
        out_dir / "metrics.json",
        {
            "experiment": er.experiment_name,
            "timestamp_utc": er.timestamp_utc,
            "git": dict(er.git),
            "run": rr.name,
            "baseline": baseline.name,
            "metrics": metrics_record(rr.result),
            "comparison": comparison.get(rr.name, {}),
        },
    )
    write_timeseries(rr.result, out_dir)
    if plots:
        write_plots(rr.result, out_dir / "plots", rr.name)
    single = ExperimentResult(
        experiment_name=er.experiment_name,
        vehicle_name=er.vehicle_name,
        baseline=baseline,
        variants={} if rr is baseline else {rr.name: rr},
        comparison=comparison,
        git=er.git,
        timestamp_utc=er.timestamp_utc,
        comparison_basis=er.comparison_basis,
        sensitivity_note=SENSITIVITY_SWEEP_POINT,
    )
    write_summary(out_dir, experiment_summary(single, header_lines))
    return out_dir


# --------------------------------------------------------------------- entry points


def _repo_root_of(repo_root: Path | None) -> Path:
    return Path.cwd() if repo_root is None else Path(repo_root)


def run_experiment(
    resolved: ResolvedExperiment,
    out_root: Path,
    plots: bool,
    only_variant: str | None = None,
    repo_root: Path | None = None,
    sensitivity: bool = True,
) -> tuple[ExperimentResult, Path]:
    """Run the baseline and every variant (or one), the sensitivity cases of the runs
    that ran (``run_sensitivity``, unless ``sensitivity`` is False), write the results,
    return them.

    Inputs: a ResolvedExperiment (from config.resolve_experiment), the results root, the
    plots switch, an optional single variant name, the repository root for the git
    hash (default: the current directory) and the sensitivity switch. Output: the
    ExperimentResult and the run directory results/<experiment>/<timestamp>/, created
    before any run starts; an exception after that leaves FAILED.txt in it
    (write_failure_marker) and propagates. Every variant is compared with ``compare``
    against the baseline, with its own vehicle and, when the experiment has a variant
    named INSTANT_VARIANT_NAME, that run as the integrated ignition-loss yardstick.
    When no sensitivity case ran, ``ExperimentResult.sensitivity_note`` says why
    (skipped, none declared, or none for the variants that ran).
    """
    exp = resolved.experiment
    variants = resolved.variants
    if only_variant is not None:
        if only_variant not in variants:
            raise ValueError(
                f"variant {only_variant!r} not in experiment {exp.name!r}: {sorted(variants)}"
            )
        variants = {only_variant: variants[only_variant]}
    check_result_names(resolved)
    git = git_info(_repo_root_of(repo_root))
    now = datetime.now(UTC)  # one clock read: the directory name and timestamp_utc agree
    out_dir = make_run_dir(Path(out_root), exp.name, now=now)
    try:
        baseline = run_resolved(resolved.baseline)
        variant_results = {name: run_resolved(r) for name, r in variants.items()}
        instant = variant_results.get(INSTANT_VARIANT_NAME)
        comparison = {
            name: compare(
                rr.result,
                baseline.result,
                rr.resolved.to_vehicle(),
                None if instant is None else instant.result,
            )
            for name, rr in variant_results.items()
        }
        rows = (
            run_sensitivity(resolved, baseline, {baseline.name, *variant_results})
            if sensitivity
            else []
        )
        if not sensitivity:
            note = SENSITIVITY_SKIPPED
        elif not resolved.sensitivity:
            note = SENSITIVITY_NONE_DECLARED
        else:
            note = SENSITIVITY_NONE_FOR_RUNS  # declared, but for variants that did not run
        er = ExperimentResult(
            experiment_name=exp.name,
            vehicle_name=resolved.baseline.vehicle.name,
            baseline=baseline,
            variants=variant_results,
            comparison=comparison,
            git=git,
            timestamp_utc=utc_timestamp(now),
            sensitivity=rows,
            sensitivity_note=note,
        )
        write_run(er, out_dir, plots)
    except BaseException as exc:
        write_failure_marker(out_dir, exc)
        raise
    return er, out_dir


SWEEP_INDEX_FIXED_COLUMNS: tuple[str, ...] = ("point", "run_dir", "of", "status")


def sweep_index_frame(sweep: SweepResult, baseline: RunResult, root: Path) -> pd.DataFrame:
    """One row per sweep point: point, the axis values, run_dir (relative to root), of,
    the SWEEP_INDEX_METRICS (from the point's metrics, or its comparison against the
    baseline for the delta; non-finite or absent -> empty cell) and status. Raises
    ValueError if an axis path collides with a fixed or metric column (a programming
    error in the schema, not a user error)."""
    clash = sorted({*SWEEP_INDEX_FIXED_COLUMNS, *SWEEP_INDEX_METRICS} & set(sweep.axes))
    if clash:
        raise ValueError(f"sweep index: axis paths collide with index columns: {clash}")
    rows = []
    for point, rr, comp, run_dir in zip(
        sweep.points, sweep.results, sweep.comparisons, sweep.run_dirs, strict=True
    ):
        row: dict[str, Any] = {"point": point.point_index}
        row.update({axis: point.overrides[axis] for axis in sweep.axes})
        row["run_dir"] = run_dir.relative_to(root).as_posix()
        row["of"] = sweep.of
        for key in SWEEP_INDEX_METRICS:
            value = comp.get(key) if key in comp else rr.result.metrics.get(key)
            row[key] = value if _is_finite_number(value) else None
        row["status"] = rr.result.status
        rows.append(row)
    columns = ["point", *sweep.axes, "run_dir", "of", *SWEEP_INDEX_METRICS, "status"]
    return pd.DataFrame(rows, columns=columns)


def sweep_summary(
    exp_name: str,
    sweeps: list[SweepResult],
    frames: list[pd.DataFrame],
    baseline: RunResult,
    git: Mapping[str, Any],
    timestamp_utc: str,
) -> str:
    """The top-level summary.md text of a sweep run. The assumptions section is the
    union over the baseline and every sweep point (attributed as sweep_<n>/run_NNNN);
    a ``step_startup_note`` names the baseline or the points that are step-thrust
    yardsticks (the axis values identify a point, so the note alone suffices)."""
    parts = [
        f"# {exp_name}: sweeps",
        "",
        COMPARISON_BASIS,
        "",
        f"- Baseline: {baseline.name} (status {baseline.result.status})",
        provenance_lines(git, timestamp_utc),
        "",
    ]
    if not sweeps:
        parts.append("(no sweeps declared)")
    for sweep, frame in zip(sweeps, frames, strict=True):
        parts += [
            f"## sweep_{sweep.sweep_index}: {sweep.of} over {', '.join(sweep.axes)}",
            "",
        ]
        if frame.empty:
            parts += ["(no points)", ""]
            continue
        header = [str(c) for c in frame.columns]
        rows = [[_fmt(v) for v in rec] for rec in frame.itertuples(index=False, name=None)]
        parts += [_table(header, rows), ""]
    all_runs = {baseline.name: baseline}
    for sweep in sweeps:
        all_runs.update({f"sweep_{sweep.sweep_index}/{rr.name}": rr for rr in sweep.results})
    stage = str(baseline.resolved.vehicle_dict["stages"][0]["name"])
    note = step_startup_note(all_runs, stage)
    if note:
        parts += [note, ""]
    section = assumptions_section(all_runs, baseline.name, "all sweep points")
    parts += ["## Assumptions", "", section, ""]
    return "\n".join(parts)


def run_sweep(
    resolved: ResolvedExperiment,
    out_root: Path,
    plots: bool,
    repo_root: Path | None = None,
) -> tuple[list[SweepResult], Path]:
    """Run every sweep of an experiment and write the results.

    Layout: results/<experiment>/<timestamp>/baseline/ (the pad baseline, flat layout),
    sweep_<n>/run_NNNN/ per grid point (flat layout, compared against the baseline),
    sweep_<n>/sweep_index.csv and a top-level summary.md. Returns the SweepResults and
    the run directory, created before any run starts; an exception after that leaves
    FAILED.txt in it (write_failure_marker) and propagates.
    """
    exp = resolved.experiment
    check_result_names(resolved)
    git = git_info(_repo_root_of(repo_root))
    now = datetime.now(UTC)  # one clock read: the directory name and timestamp_utc agree
    timestamp = utc_timestamp(now)
    out_dir = make_run_dir(Path(out_root), exp.name, now=now)
    try:
        sweeps, frames, baseline = _run_sweeps_into(resolved, out_dir, plots, git, timestamp)
        write_summary(out_dir, sweep_summary(exp.name, sweeps, frames, baseline, git, timestamp))
    except BaseException as exc:
        write_failure_marker(out_dir, exc)
        raise
    return sweeps, out_dir


def _run_sweeps_into(
    resolved: ResolvedExperiment,
    out_dir: Path,
    plots: bool,
    git: Mapping[str, Any],
    timestamp: str,
) -> tuple[list[SweepResult], list[pd.DataFrame], RunResult]:
    """Run the baseline and every sweep point into an existing run directory (see
    run_sweep); returns the SweepResults, their index frames and the baseline."""
    exp = resolved.experiment
    baseline = run_resolved(resolved.baseline)
    er = ExperimentResult(
        experiment_name=exp.name,
        vehicle_name=resolved.baseline.vehicle.name,
        baseline=baseline,
        variants={},
        comparison={},
        git=dict(git),
        timestamp_utc=timestamp,
    )
    write_single(baseline, baseline, er, out_dir / "baseline", plots)

    sweeps: list[SweepResult] = []
    frames: list[pd.DataFrame] = []
    for k, points in enumerate(resolved.sweeps, start=1):
        if any(p.sweep_index != k - 1 for p in points):
            raise ValueError(f"sweep_{k}: config.SweepPoint.sweep_index is expected 0-based")
        sweep_dir = out_dir / f"sweep_{k}"
        axes = list(exp.sweeps[k - 1].axes)
        results: list[RunResult] = []
        comparisons: list[dict[str, Any]] = []
        run_dirs: list[Path] = []
        for point in points:
            rr = run_resolved(point.run)
            header = sweep_point_header(k, point, len(points))
            comparison = compare(rr.result, baseline.result, point.run.to_vehicle())
            run_dir = write_single(
                rr, baseline, er, sweep_dir / point.run.name, plots, header, comparison
            )
            results.append(rr)
            comparisons.append(comparison)
            run_dirs.append(run_dir)
        sweep = SweepResult(k, exp.sweeps[k - 1].of, axes, points, results, comparisons, run_dirs)
        frame = sweep_index_frame(sweep, baseline, out_dir)
        sweep_dir.mkdir(parents=True, exist_ok=True)
        write_csv(sweep_dir / "sweep_index.csv", frame)
        sweeps.append(sweep)
        frames.append(frame)
    return sweeps, frames, baseline
