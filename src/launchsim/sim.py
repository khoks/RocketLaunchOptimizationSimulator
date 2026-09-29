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
        metrics.json           per-run metrics and the comparison against the baseline
        summary.md             tables against the baseline, assumptions, git hash, timestamp
        <run>/timeseries.csv   sampled state (t_s, z_m, v_mps, m_kg, ...)
        <run>/events.csv       phase-boundary events (t_s, event, phase)
        plots/<run>_<name>.png only when a run has time-series data (plot_stem sanitises)

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
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
import yaml
from matplotlib.figure import Figure

from launchsim.assist import NoAssist, build_assist
from launchsim.assist.base import AssistModel, TrackGeometry
from launchsim.config import ResolvedExperiment, ResolvedRun, RunConfig, SweepPoint
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
from launchsim.losses import AssistEnergyBudget, LossBudget, assist_energy_budget, loss_budget
from launchsim.phases import (
    ASCENT_KINDS,
    ASSIST_KIND,
    AscentStart,
    HoldParams,
    IgnitionSpec,
    IntegratorSettings,
    PhaseResult,
    RunTrace,
    VerticalPlanner,
    sample_grid,
)
from launchsim.units import j_to_kwh, to_g
from launchsim.vehicle import Vehicle

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
    "gravity mu/r^2 in flight (InverseSquareGravity; ConstantGravity exists only for tests)",
    "pad and track g_eff = mu/R_E^2 - omega_p^2 R_E with omega_p = "
    f"{OMEGA_P_PHASE1_RADS:g} rad/s, continuous with mu/r^2 at z = 0",
)
# Time-series columns write_plots skips: the abscissa itself, t_rel_release_s (a straight
# line against t_s) and thrust_vac_N (equal to thrust_N while p_amb = 0). Build step 9
# curates the set for the summaries.
PLOT_SKIP_COLUMNS: frozenset[str] = frozenset({"t_s", "t_rel_release_s", "thrust_vac_N"})
# Metric keys every summary must report (CLAUDE.md "Every summary reports"). metrics_table
# prints them first, "n/a" when a run does not carry one, so a missing item is visible;
# the loss and load items are filled by ``run_metrics``, the assist ones by build step 7,
# the comparison ones (payload equivalent) by build step 9.
REQUIRED_METRICS: tuple[str, ...] = (
    "payload_equiv_ideal_kg",  # ideal-screening payload equivalent (Phase 1: no payload)
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
    loss_budget: LossBudget from release onward (None when not simulated);
    assist_budget: AssistEnergyBudget (build step 7).
    assumptions: attributed assumption strings for the summary.
    phases: the PhaseResult list of the run; empty when not simulated.
    status: nominal, impact, no_liftoff, drive_limit or not_simulated.
    flags: warnings such as interface_tensile or a disarmed event.
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
class ExperimentResult:
    """Baseline, variants, their comparison, and the provenance of one experiment run."""

    experiment_name: str
    vehicle_name: str
    baseline: RunResult
    variants: dict[str, RunResult]
    comparison: dict[str, dict[str, Any]]
    git: dict[str, Any]
    timestamp_utc: str
    comparison_basis: str = COMPARISON_BASIS

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
)


def gravity_assumption(gravity: Gravity) -> str:
    """The assumption line naming the ascent gravity model ``simulate`` was handed."""
    if isinstance(gravity, InverseSquareGravity):
        return f"gravity mu/r^2 in flight (mu = {gravity.mu_m3s2:.10g} m^3/s^2)"
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


def _peak_felt(frame: pd.DataFrame) -> tuple[float | None, float | None, float | None]:
    """(peak T/m in g0, its time relative to release [s], the mass there [kg]) over the
    free-flight rows, or Nones when there are none."""
    flight = frame[frame["phase"].isin(ASCENT_KINDS)]
    if flight.empty:
        return None, None, None
    i = int(flight["accel_felt_g"].to_numpy().argmax())
    row = flight.iloc[i]
    return float(row["accel_felt_g"]), float(row["t_rel_release_s"]), float(row["m_kg"])


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
    """
    layout = VERTICAL_LAYOUT
    stage0 = vehicle.stages[0]
    m0 = vehicle.liftoff_mass_kg()
    t_rel = trace.t_release_s
    y_rel = trace.y_release
    y_fs = trace.y_flight_start
    m_release = m0 if y_rel is None else float(layout.get(y_rel, "m_kg"))
    m_flight = None if y_fs is None else float(layout.get(y_fs, "m_kg"))
    metrics: dict[str, Any] = {
        "liftoff_mass_kg": m0,
        "assist_model": assist_name,
        "t_release_s": t_rel,
        "speed_at_release_mps": None if y_rel is None else abs(float(layout.get(y_rel, "v_mps"))),
        "alt_at_release_m": None if y_rel is None else float(layout.get(y_rel, "z_m")),
        "mass_at_release_kg": m_release,
        "propellant_burned_before_release_kg": m0 - m_release,
        "dv_vac_equiv_before_release_mps": stage0.c_mps * math.log(m0 / m_release),
        "t_flight_start_s": (
            None if trace.t_flight_start_s is None else trace.t_flight_start_s - t_rel
        ),
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
        t_ign = trace.t_ign_abs_s.get(stage.name)
        metrics[f"t_ign_rel_release_s_{stage.name}"] = None if t_ign is None else t_ign - t_rel
    bo = trace.burnouts.get(stage0.name)
    metrics["stage1_burnout_t_s"] = None if bo is None else bo[0] - t_rel
    metrics["stage1_burnout_speed_mps"] = (
        None if bo is None else abs(float(layout.get(bo[1], "v_mps")))
    )
    metrics["stage1_burnout_alt_m"] = None if bo is None else float(layout.get(bo[1], "z_m"))
    metrics["stage1_burnout_mass_kg"] = None if bo is None else float(layout.get(bo[1], "m_kg"))
    if trace.phases:
        last = trace.phases[-1]
        metrics["final_t_s"] = last.t_end - t_rel
        metrics["final_speed_mps"] = abs(float(layout.get(last.y_end, "v_mps")))
        metrics["final_alt_m"] = float(layout.get(last.y_end, "z_m"))
        metrics["final_mass_kg"] = float(layout.get(last.y_end, "m_kg"))
    apexes = [e for e in trace.events if e.name == "apex"]
    top = max(apexes, key=lambda e: e.z_m) if apexes else None
    metrics["apex_alt_m"] = None if top is None else top.z_m
    metrics["apex_t_s"] = None if top is None else top.t_s - t_rel
    impact = trace.first_event("impact")
    metrics["impact_t_s"] = None if impact is None else impact.t_s - t_rel
    metrics["impact_speed_mps"] = None if impact is None else abs(impact.v_mps)
    peak_g, peak_t, peak_m = _peak_felt(frame)
    metrics["peak_felt_g_flight"] = peak_g
    metrics["peak_felt_g_flight_t_s"] = peak_t
    metrics["peak_felt_g_flight_mass_kg"] = peak_m
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
            # CLAUDE.md summary items the pad answers trivially; the track ones (build
            # step 7) overwrite them for assisted runs.
            "peak_felt_axial_g": peak_g,
            "peak_track_normal_g": 0.0,
            "assist_energy_J": 0.0,
            "assist_energy_kWh": 0.0,
            "peak_drive_power_W": 0.0,
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

    Peaks and minima are taken over the sampled ASSIST rows of the time series (every
    sample_dt_s plus both ends of every sub-phase, so the push start and the release
    are always included). exit_speed_mps and push_time_s are the release state (None
    when the run stopped on the track); the facility length includes the carriage
    braking distance from the exit speed; electrical energy = drive work / efficiency;
    propellant_burned_on_track_kg counts from the push start to the end of the last
    track phase.
    """
    rows = frame[frame["phase"] == ASSIST_KIND]
    assist_phases = trace.assist_phases()
    y_rel = trace.y_release
    layout = VERTICAL_LAYOUT
    v_exit = None if y_rel is None else abs(float(layout.get(y_rel, "v_mps")))
    first, last = assist_phases[0], assist_phases[-1]
    m_start = float(first.spec.params.layout.get(first.y[:, 0], "m_kg"))
    m_end = float(last.spec.params.layout.get(last.y_end, "m_kg"))
    e_drive = budget.work_drive
    felt_peak = float(rows["accel_felt_g"].max())
    n_v = float(rows["track_normal_g_vehicle"].max())
    n_c = float(rows["track_normal_g_carriage"].max())
    return {
        "exit_speed_mps": v_exit,
        "push_time_s": None if y_rel is None else trace.t_release_s,
        "felt_g_track_peak": felt_peak,
        "interface_force_peak_N": float(rows["interface_force_N"].max()),
        "interface_force_min_N": float(rows["interface_force_N"].min()),
        "drive_force_peak_N": float(rows["drive_force_N"].max()),
        "drive_energy_J": e_drive,
        "drive_energy_kWh": float(j_to_kwh(e_drive)),
        "electrical_energy_J": e_drive / assist.efficiency,
        "electrical_energy_kWh": float(j_to_kwh(e_drive / assist.efficiency)),
        "drive_power_peak_W": float(rows["drive_power_W"].max()),
        "braking_distance_m": None if v_exit is None else assist.braking_distance_m(v_exit),
        "facility_length_m": (None if v_exit is None else assist.facility_length_m(track, v_exit)),
        "propellant_burned_on_track_kg": m_start - m_end,
        "track_normal_g_vehicle_peak": n_v,
        "track_normal_g_carriage_peak": n_c,
        "assist_energy_residual_rel": budget.residual_rel(),
        "track_start_altitude_m": track.start_altitude_m,
        "carriage_mass_kg": assist.carriage_mass_kg,
        # CLAUDE.md summary items: the track values overwrite the pad's zeros.
        "peak_track_normal_g": max(n_v, n_c),
        "assist_energy_J": e_drive,
        "assist_energy_kWh": float(j_to_kwh(e_drive)),
        "peak_drive_power_W": float(rows["drive_power_W"].max()),
        "peak_interface_force_N": float(rows["interface_force_N"].max()),
    }


def track_flags(frame: pd.DataFrame) -> list[str]:
    """Run flags read off the ASSIST rows: ``interface_tensile`` when the interface
    force is negative anywhere during the push (the vehicle would have to be held back
    on the carriage)."""
    rows = frame[frame["phase"] == ASSIST_KIND]
    if rows.empty:
        return []
    f_min = float(rows["interface_force_N"].min())
    if f_min < 0.0:
        t_min = float(rows["t_s"].iloc[int(rows["interface_force_N"].to_numpy().argmin())])
        return [
            f"interface_tensile: the carriage-vehicle interface force reaches {f_min:.6g} N "
            f"(tension) at t = {t_min:.6g} s during the push"
        ]
    return []


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
    (``interface_tensile`` is evaluated over the ASSIST rows only). The assumptions
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
        flags += track_flags(frame)
        assumptions += [
            *TRACK_ASSUMPTIONS,
            f"track: straight, L = {track.length_m:.6g} m at {track.phi(0.0):.6g} rad above "
            f"horizontal, start altitude {track.start_altitude_m:.6g} m (exit at "
            f"{track.start_altitude_m + track.z(track.length_m):.6g} m)",
        ]
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


def compare(result: Result, baseline: Result) -> dict[str, Any]:
    """Deltas (variant minus baseline) of every numeric metric both results carry.

    Keys are ``delta_<metric>``; non-numeric metrics are skipped. A delta whose operands
    are not both finite (NaN, inf, pd.NA, pd.NaT) is None (written as null in JSON, an
    empty CSV cell, "n/a" in a summary). Status is always carried as ``status`` and
    ``baseline_status``.
    """
    out: dict[str, Any] = {"status": result.status, "baseline_status": baseline.status}
    for key, value in result.metrics.items():
        base = baseline.metrics.get(key)
        if _is_numeric_or_missing(value) and _is_numeric_or_missing(base):
            finite = _is_finite_number(value) and _is_finite_number(base)
            out[f"delta_{key}"] = float(value) - float(base) if finite else None
    return out


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


def _plot_columns(frame: pd.DataFrame) -> list[str]:
    return [
        c
        for c in frame.columns
        if c not in PLOT_SKIP_COLUMNS and pd.api.types.is_numeric_dtype(frame[c])
    ]


def plot_stem(prefix: str, column: str) -> str:
    """File stem ``<prefix>_<column>`` with every run of characters outside
    ``[A-Za-z0-9_.-]`` replaced by ``_`` (a column such as ``F/N`` becomes ``F_N``)."""
    return PLOT_STEM_UNSAFE.sub("_", f"{prefix}_{column}")


def _plot_text(text: str) -> str:
    """Escape ``$`` so matplotlib does not read the label as mathtext."""
    return text.replace("$", "\\$")


def write_plots(result: Result, plots_dir: Path, prefix: str) -> list[Path]:
    """Write plots/<plot_stem(prefix, column)>.png, one single-series panel per numeric
    column against t_s, skipping PLOT_SKIP_COLUMNS. Nothing is written when the time
    series is empty.

    Figures are built from matplotlib.figure.Figure and saved through the Agg canvas
    that PNG output selects, so no pyplot state and no global backend switch is needed:
    importing this module leaves a notebook's inline backend alone.
    """
    frame = result.timeseries
    if frame.empty or "t_s" not in frame.columns:
        return []
    plots_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for col in _plot_columns(frame):
        fig = Figure(figsize=PLOT_FIGSIZE_IN, dpi=PLOT_DPI)
        ax = fig.subplots()
        ax.plot(frame["t_s"], frame[col], color=PLOT_SERIES_COLOR, linewidth=PLOT_LINE_WIDTH)
        ax.set_xlabel("t [s]")
        ax.set_ylabel(_plot_text(col))
        ax.set_title(_plot_text(f"{prefix}: {col}"))
        ax.grid(True, color=PLOT_GRID_COLOR, linewidth=PLOT_GRID_LINE_WIDTH)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        fig.tight_layout()
        path = plots_dir / f"{plot_stem(prefix, col)}.png"
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
    if value is None or _is_pandas_missing(value):
        return "n/a"
    if isinstance(value, bool):
        return str(value)
    if _is_number(value):
        return f"{float(value):.6g}" if _is_finite_number(value) else "n/a"
    return str(value)


def _metric_keys(results: Iterable[Result]) -> list[str]:
    """REQUIRED_METRICS first, then every other metric key in first-seen order."""
    keys = list(REQUIRED_METRICS)
    for r in results:
        for k in r.metrics:
            if k not in RESERVED_METRIC_KEYS and k not in keys:  # status has its own column
                keys.append(k)
    return keys


def _table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def metrics_table(runs: Mapping[str, RunResult], baseline_name: str) -> str:
    """Markdown table of every metric per run, baseline first; the REQUIRED_METRICS
    columns always come first and read "n/a" when a run does not carry them."""
    keys = _metric_keys(r.result for r in runs.values())
    rows = []
    for name, rr in runs.items():
        label = f"{name} (baseline)" if name == baseline_name else name
        rows.append([label, rr.result.status, *(_fmt(rr.result.metrics.get(k)) for k in keys)])
    return _table(["run", "status", *keys], rows)


def comparison_table(comparison: Mapping[str, Mapping[str, Any]]) -> str:
    """Markdown table of the deltas of every variant against the baseline."""
    if not comparison:
        return "(no variants)"
    keys: list[str] = []
    for comp in comparison.values():
        keys += [k for k in comp if k.startswith("delta_") and k not in keys]
    rows = [[name, *(_fmt(comp.get(k)) for k in keys)] for name, comp in comparison.items()]
    return _table(["variant", *keys], rows)


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
    """The summary.md text of an experiment run; ``header_lines`` (already formatted as
    ``- ...`` bullets, e.g. a sweep point's axis values) go under the baseline line."""
    runs = er.runs
    return "\n".join(
        [
            f"# {er.experiment_name}",
            "",
            er.comparison_basis,
            "",
            f"- Vehicle: {er.vehicle_name}",
            f"- Baseline: {er.baseline.name}",
            *header_lines,
            provenance_lines(er.git, er.timestamp_utc),
            "",
            "## Metrics",
            "",
            metrics_table(runs, er.baseline.name),
            "",
            "## Deltas against the baseline",
            "",
            comparison_table(er.comparison),
            "",
            "## Flags",
            "",
            flags_section(runs),
            "",
            "## Assumptions",
            "",
            assumptions_section(runs, er.baseline.name),
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
) -> Path:
    """Flat single-run layout for a sweep point (or the sweep's baseline copy):
    resolved_config.yaml, metrics.json, summary.md, timeseries.csv, events.csv, plots/.
    ``header_lines`` (see sweep_point_header) name the point in its summary.md."""
    out_dir = Path(out_dir)
    rr = run_result
    check_name(rr.name, "run name")  # sweep points are run_NNNN, so no reserved check here
    out_dir.mkdir(parents=True, exist_ok=True)
    comparison = {} if rr is baseline else {rr.name: compare(rr.result, baseline.result)}
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
) -> tuple[ExperimentResult, Path]:
    """Run the baseline and every variant (or one), write the results, return them.

    Inputs: a ResolvedExperiment (from config.resolve_experiment), the results root, the
    plots switch, an optional single variant name, and the repository root for the git
    hash (default: the current directory). Output: the ExperimentResult and the run
    directory results/<experiment>/<timestamp>/, created before any run starts; an
    exception after that leaves FAILED.txt in it (write_failure_marker) and propagates.
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
        comparison = {
            name: compare(rr.result, baseline.result) for name, rr in variant_results.items()
        }
        er = ExperimentResult(
            experiment_name=exp.name,
            vehicle_name=resolved.baseline.vehicle.name,
            baseline=baseline,
            variants=variant_results,
            comparison=comparison,
            git=git,
            timestamp_utc=utc_timestamp(now),
        )
        write_run(er, out_dir, plots)
    except BaseException as exc:
        write_failure_marker(out_dir, exc)
        raise
    return er, out_dir


SWEEP_INDEX_FIXED_COLUMNS: tuple[str, ...] = ("point", "run_dir", "of", "status")


def sweep_index_frame(sweep: SweepResult, baseline: RunResult, root: Path) -> pd.DataFrame:
    """One row per sweep point: point, run_dir (relative to root), of, the axis values,
    status, every numeric metric (non-finite -> empty cell) and its delta against the
    baseline. Raises ValueError if a metric or delta key collides with a bookkeeping
    column (a programming error in the metrics schema, not a user error)."""
    rows = []
    bookkeeping = {*SWEEP_INDEX_FIXED_COLUMNS, *sweep.axes}
    for point, rr, comp, run_dir in zip(
        sweep.points, sweep.results, sweep.comparisons, sweep.run_dirs, strict=True
    ):
        row: dict[str, Any] = {
            "point": point.point_index,
            "run_dir": run_dir.relative_to(root).as_posix(),
            "of": sweep.of,
        }
        row.update({axis: point.overrides[axis] for axis in sweep.axes})
        row["status"] = rr.result.status
        values = {k: v for k, v in rr.result.metrics.items() if _is_numeric_or_missing(v)}
        values.update({k: v for k, v in comp.items() if k.startswith("delta_")})
        clash = sorted(bookkeeping & set(values))
        if clash:
            raise ValueError(f"sweep index: metric keys collide with index columns: {clash}")
        row.update({k: (v if _is_finite_number(v) else None) for k, v in values.items()})
        rows.append(row)
    return pd.DataFrame(rows)


def sweep_summary(
    exp_name: str,
    sweeps: list[SweepResult],
    frames: list[pd.DataFrame],
    baseline: RunResult,
    git: Mapping[str, Any],
    timestamp_utc: str,
) -> str:
    """The top-level summary.md text of a sweep run. The assumptions section is the
    union over the baseline and every sweep point (attributed as sweep_<n>/run_NNNN)."""
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
            run_dir = write_single(rr, baseline, er, sweep_dir / point.run.name, plots, header)
            results.append(rr)
            comparisons.append(compare(rr.result, baseline.result))
            run_dirs.append(run_dir)
        sweep = SweepResult(k, exp.sweeps[k - 1].of, axes, points, results, comparisons, run_dirs)
        frame = sweep_index_frame(sweep, baseline, out_dir)
        sweep_dir.mkdir(parents=True, exist_ok=True)
        write_csv(sweep_dir / "sweep_index.csv", frame)
        sweeps.append(sweep)
        frames.append(frame)
    return sweeps, frames, baseline
