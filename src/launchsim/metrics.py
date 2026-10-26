"""Time series, events and the per-run metrics of a 1-D run (moved from sim.py; pure: no
I/O).

``sample_trace`` samples a RunTrace into the time series (TIMESERIES_COLUMNS) and
``events_frame`` lists its events (EVENT_COLUMNS). ``run_metrics`` gives the flat
metrics dict of a run, ``track_metrics`` and ``track_flags`` the items of a push,
``failed_ignition_metrics`` and ``failed_ignition_flags`` those of a failed ignition,
``ignition_timing_metrics`` the constant-g ignition-timing yardsticks, ``track_scan``
and ``track_peaks`` the scan and the exact maxima of track quantities on a push's dense
output (SP7 step S4b: a linear motor's felt-g and interface-force peaks,
``linear_motor_track_peaks``, and the samples and load history of
``sim.linear_motor_push_load``), and ``metrics_record`` the metrics.json record of one
run. Units are SI with the unit in each key; times are relative to release unless a key
says otherwise; the frame is the
+z-up ascent datum frame of ``dynamics.VERTICAL_LAYOUT``. ``sim.simulate`` calls these
and ``sim`` re-exports every name.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Container, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
from scipy.integrate import OdeSolution
from scipy.optimize import brentq, minimize_scalar

from launchsim.assist.base import AssistModel, TrackGeometry
from launchsim.assist.linear_motor import (
    CONTROL_ACCELERATION,
    DRIVE_CAP,
    POWER_LIMIT,
    RELEASE_TRIGGER_TARGET_SPEED,
    RELEASE_TRIGGER_TRACK_END,
    TAPER_START,
    LinearMotorAssist,
)
from launchsim.dynamics import (
    VERTICAL_LAYOUT,
    TrackParams,
    track_observables,
    track_to_vertical,
)
from launchsim.losses import (
    AssistEnergyBudget,
    LossBudget,
    PistonWork,
    assist_identity_residual_rel,
    drive_power_extrema,
    drive_work_split,
    ignition_loss_analytic_mps,
    piston_work,
)
from launchsim.phases import (
    ASCENT_KINDS,
    ASSIST_KIND,
    ATOL_M,
    ATOL_MPS,
    ZERO_SPAN_S,
    HoldParams,
    IgnitionSpec,
    IntegratorSettings,
    PhaseResult,
    RunTrace,
    sample_grid,
)
from launchsim.phases.prelude import DRIVE_STALL
from launchsim.units import j_to_kwh, to_g
from launchsim.vehicle import Vehicle

if TYPE_CHECKING:
    from launchsim.sim import Result


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


# Metric keys the results records add themselves (Result.status, Result.flags); a metric
# with one of these names would be silently overwritten in metrics.json, so it is refused.
RESERVED_METRIC_KEYS: frozenset[str] = frozenset({"status", "flags"})


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
    then lifts off). A track run that stopped on the track (status ``drive_limit``
    or ``drive_stall``) never released: every release item (t_release_s, speed, altitude, mass, the
    ``before_release`` pair) and every time counted from release
    (``t_ign_rel_release_s_*``, ``final_t_s``, the burnout, apex and impact times) is
    None, and what burned is in ``hold_propellant_burned_kg`` and
    ``propellant_burned_on_track_kg``; the time series' ``t_rel_release_s`` column then
    counts from the push start (t = 0).

    ``peak_felt_axial_g`` (a CLAUDE.md summary item) is the peak felt axial
    acceleration over the whole run: the hold (1 g_eff), the track ((F_int + T)/m_v)
    and the free flight (T/m); ``peak_felt_axial_g_phase``, ``_t_s`` and ``_mass_kg``
    say where it occurs and the mass there (a ``drive_stall`` run's push-start row is
    left out, ``STALL_UNAVAILABLE_TRACK_METRICS``: None when nothing else is sampled).
    ``peak_felt_g_flight`` (with ``_t_s`` and ``_mass_kg``) is the free-flight peak
    alone.

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
    # The run-wide peak: hold, track and flight rows together (the CLAUDE.md item);
    # a stalled push's one row is not reported (STALL_UNAVAILABLE_TRACK_METRICS).
    felt_frame = frame[frame["phase"] != ASSIST_KIND] if trace.status == DRIVE_STALL else frame
    axial_g, axial_t, axial_m, axial_phase = _peak_felt(felt_frame)
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
    and the release are always included: the thrust kinks, and for the linear motor
    the end of its rise and every watch crossing (power_limit, power_limit_end,
    drive_cap, drive_cap_end, taper_start), each a sub-phase end; exact for the forces
    of the prescribed-acceleration drive, which are monotone within a lit sub-phase).
    On a linear-motor push that did not stall, felt_g_track_peak (with its time and
    mass) and interface_force_peak_N (with its alias) come instead from the dense
    output (``linear_motor_track_peaks``, SP7 step S4b, KI-046): a taper entered during
    the rise (the rising limit or command times the falling taper weight) peaks between
    samples, 2e-5 relative above the sampled rows with t_r 4 s and a 90 m taper on a
    100 m stroke, and so can the felt g and the interface force on a hot push in its
    power phase (docs/physics.md "Linear motor" and "The flown push of a linear motor";
    the minima, drive_force_peak_N and the track-normal peaks stay sampled). The
    drive power is not monotone in general, so its extrema come from the dense output
    (``losses.drive_power_extrema``): drive_power_peak_W = max(0, max P) with its
    absolute time drive_power_peak_t_s (0 for a push in which the drive only brakes),
    and drive_power_min_W = min(0, min P), the braking power the drive must absorb (0
    when it only pushes). exit_speed_mps and push_time_s are the release state (None
    when the run stopped on the track); the facility length includes the carriage
    braking distance from the exit speed (L + d_brake; for a linear-motor push
    ``linear_motor_facility_m``'s max(L, s_release + d_brake), which overwrites it, SP7
    step S4a); drive_energy_J is the net drive work of the
    energy identity, drive_work_in_J and drive_work_out_J its positive and negative
    parts (``losses.drive_work_split``), and electrical_energy_J = drive_work_in_J /
    efficiency: the electricity the drive draws, with no regeneration credited for any
    braking work (an assumption, stated in the assumptions list).
    propellant_burned_on_track_kg counts from the push start to the end of the last
    track phase. felt_g_track_peak is the peak felt axial acceleration over the ASSIST
    rows (a linear motor's that did not stall from the dense output, as above), with its
    time relative to release (felt_g_track_peak_t_s; None when the run never released)
    and the vehicle mass there (felt_g_track_peak_mass_kg). The keys
    named here are canonical; the CLAUDE.md summary names of TRACK_METRIC_ALIASES
    (assist_energy_J/kWh, peak_drive_power_W, peak_interface_force_N) are written
    beside them with the same numbers, and peak_track_normal_g = max(vehicle, carriage).
    A linear-motor push adds LINEAR_MOTOR_METRICS (``linear_motor_metrics``) after
    them, and in a sealed shaft (SP7 step S5) SEALED_SHAFT_METRICS after those
    (``sealed_shaft_metrics``); no other drive gains a key. assist_energy_residual_rel is
    ``losses.assist_identity_residual_rel``: the budget's residual_rel() (bit for bit as
    before) without a sealed shaft, and with one the residual of the identity with the
    work done against the column (``losses.PistonWork``). A ``drive_stall`` run writes
    STALL_UNAVAILABLE_TRACK_METRICS as None (``stall_unavailable_metrics``).
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
    piston = sealed_shaft_piston(trace, assist)
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
        "assist_energy_residual_rel": assist_identity_residual_rel(budget, piston),
        "track_start_altitude_m": track.start_altitude_m,
        "carriage_mass_kg": assist.carriage_mass_kg,
        # CLAUDE.md summary item: the track value overwrites the pad's zero.
        "peak_track_normal_g": max(n_v, n_c),
    }
    # The CLAUDE.md-named aliases (same numbers; they overwrite the pad's zeros too).
    out.update({alias: out[canonical] for alias, canonical in TRACK_METRIC_ALIASES.items()})
    if isinstance(assist, LinearMotorAssist) and trace.status != DRIVE_STALL:
        out.update(linear_motor_track_peaks(trace))  # SP7 step S4b: exact peaks (KI-046)
    out.update(stall_unavailable_metrics(trace))
    if isinstance(assist, LinearMotorAssist):  # SP7 step S4: that drive only
        out.update(linear_motor_metrics(trace, assist, track, v_exit, p_peak))
        out["facility_length_m"] = linear_motor_facility_m(trace, assist, track, v_exit)
        if piston is not None:  # SP7 step S5: a sealed shaft only
            out.update(sealed_shaft_metrics(trace, assist, piston))
    return out


SEALED_SHAFT_METRICS: tuple[str, ...] = (
    "piston_work_J",
    "piston_force_peak_N",
    "bore_pressure_release_pa",
)
"""The track metrics written for a linear-motor push in a sealed shaft only (SP7 step S5;
``sealed_shaft_metrics``), after LINEAR_MOTOR_METRICS: a vented linear-motor run and a
constant_accel run gain none of them (their outputs stay as they were)."""


def sealed_shaft_piston(trace: RunTrace, assist: AssistModel) -> PistonWork | None:
    """The PistonWork of a linear-motor push in a sealed shaft (SP7 step S5;
    ``losses.piston_work`` over the trace's ASSIST phases, in their track layout, with
    the drive's SealedShaft); None for the vented shaft, any other drive and a trace
    without ASSIST phases."""
    if not isinstance(assist, LinearMotorAssist) or assist.shaft is None:
        return None
    phases = trace.assist_phases()
    if not phases:
        return None
    return piston_work(phases, phases[0].spec.params.layout, assist.shaft)


def sealed_shaft_metrics(
    trace: RunTrace, assist: LinearMotorAssist, piston: PistonWork
) -> dict[str, Any]:
    """SEALED_SHAFT_METRICS of a sealed-shaft push (SI; docs/physics.md, "The sealed
    shaft"; SP7 step S5).

    Inputs: the RunTrace; the drive (its SealedShaft); the push's PistonWork. Output:
    piston_work_J, the work done against the column W_p = int F_p sdot dt [J] (the
    quadrature, PistonWork.work_J; its closed form is in the record); piston_force_peak_N, the
    largest column force on the push [N], F_p at the largest position s the push's states
    reach (F_p rises with s: the release position for a push that released; below p_0
    A_bore; 0 for a push that never moved); bore_pressure_release_pa, the column's
    pressure p(s) = p_0 (h_0/(h_0 + s))^gamma at the release state [Pa] (the flown
    release position), None when the run never released. Frame: arc length along the
    track."""
    shaft = assist.shaft
    if shaft is None:
        raise ValueError("sealed_shaft_metrics needs a drive with a sealed shaft")
    phases = trace.assist_phases()
    layout = phases[0].spec.params.layout
    s_max = max(float(np.max(np.asarray(layout.get(res.y, "s_m")))) for res in phases)
    released = trace.y_release is not None
    s_release = float(layout.get(phases[-1].y_end, "s_m"))
    return {
        "piston_work_J": piston.work_J,
        "piston_force_peak_N": shaft.force_N(s_max),
        "bore_pressure_release_pa": shaft.pressure_pa(s_release) if released else None,
    }


STALL_UNAVAILABLE_TRACK_METRICS: tuple[str, ...] = (
    "felt_g_track_peak",
    "felt_g_track_peak_t_s",
    "felt_g_track_peak_mass_kg",
    "interface_force_peak_N",
    "interface_force_min_N",
    "peak_interface_force_N",
)
"""The track metrics a ``drive_stall`` run writes as None (SP7 step S4; review pass 1
rerun, P1-m2): its one ASSIST row, the push-start state, is the drive at F_max with no
support reaction, so its sddot = (F_max + T_sys)/M - g_eff sin phi is not positive (zero
only at the equality, which stalls too) and the felt g and interface force that follow
from it (felt (F_max + T_sys)/M, at most g_eff sin phi; F_int = m_v (sddot + g_eff sin
phi) - T, at most what the vehicle at rest on the carriage presses with) are at most the
loads the stack at rest on its supports sees, and are not reported. The drive
force (F_max: the drive at its limit), the drive power and energy (0: nothing moves) and
the track-normal loads (m g_eff cos phi, which sddot does not enter) stay as sampled."""


def stall_unavailable_metrics(trace: RunTrace) -> dict[str, Any]:
    """STALL_UNAVAILABLE_TRACK_METRICS as None for a ``drive_stall`` run (trace.status),
    an empty dict otherwise (no other run changes). Input: the RunTrace."""
    if trace.status != DRIVE_STALL:
        return {}
    return dict.fromkeys(STALL_UNAVAILABLE_TRACK_METRICS)


LINEAR_MOTOR_METRICS: tuple[str, ...] = (
    "push_control_law",
    "push_force_max_N",
    "push_power_max_W",
    "push_rise_time_s",
    "push_corner_speed_mps",
    "push_accel_command_mps2",
    "push_stop_taper_m",
    "push_release_speed_mps",
    "push_power_limited",
    "push_cap_bound",
    "push_accel_mean_mps2",
    "push_felt_g_plateau",
    "release_position_m",
    "release_trigger",
    "electrical_power_peak_W",
    "braking_time_s",
    "brake_force_N",
    "brake_energy_J",
)
"""The track metrics written for a ``linear_motor`` run only (SP7 step S4; design 4.6;
``linear_motor_metrics``; the control law, a_cmd, s_taper and the release speed since
S4a, KI-052, and whether a cap bound the acceleration law's command, S4a fix round 1),
after every key a constant_accel run writes, which gains none of them
(the 1-D golden tier and the planar output capture)."""
POWER_LIMIT_TIE_REL = 1e-6
"""A ``power_limit`` event later than t_release (1 - POWER_LIMIT_TIE_REL) [relative to
the push time] is a tie at the release, not a power-limited push: the speed where the
power limit starts binding, P_max/F_pre (F_pre the law's force before the power term:
the corner P_max/F_max after the force law's rise, P_max/F_lim(t) inside it, P_max/(M
(a + g) - (1 - f_imp) T) under the acceleration law, P_max/(M (a + g) - (1 - f_imp) T +
F_p(s)) with a sealed shaft), equals the exit speed to within
about 1e-6 (on the force plateau k = P_max/(F_max v_e) = 1, the design's r = 1 point;
not the rise fraction r(t)), a limit the push reaches only in its last instant (k = 1
itself logs no event; 1 - k = 1e-9 logs one 9.1e-10 of the push time before the
release, measured). It does not set ``push_power_limited``."""


def _assist_event_times(trace: RunTrace, name: str) -> list[float]:
    """Times [s] of the ASSIST events called name, in log order."""
    return [e.t_s for e in trace.events if e.name == name and e.phase == ASSIST_KIND]


def _felt_at_rise_end(trace: RunTrace, rise_time_s: float) -> float | None:
    """The felt axial acceleration [g0] at the end of the drive's rise (the plateau's
    start): at the end state of the ASSIST sub-phase that ends at t_r = rise_time_s
    [s] (a sub-phase boundary), at the push-start state for a step (t_r = 0); None when
    no sub-phase ends there (the push released, or stopped, before t_r) and when no
    plateau is reached, because the power limit or the taper began before t_r (a
    ``power_limit`` or ``taper_start`` event earlier than t_r - ZERO_SPAN_S: the force
    at t_r is shaped by the power limit or the taper, not by the rise alone)."""
    early = _assist_event_times(trace, POWER_LIMIT) + _assist_event_times(trace, TAPER_START)
    if any(t_e < rise_time_s - ZERO_SPAN_S for t_e in early):
        return None
    for res in trace.assist_phases():
        params = res.spec.params
        if rise_time_s <= 0.0 and res.spec.t0 == 0.0:
            return track_observables(0.0, np.asarray(res.y[:, 0], dtype=float), params)["felt_g"]
        if rise_time_s > 0.0 and abs(res.t_end - rise_time_s) <= ZERO_SPAN_S:
            return track_observables(res.t_end, res.y_end, params)["felt_g"]
    return None


def _power_limited(trace: RunTrace, released: bool) -> bool:
    """Whether the power limit bound on the push: a ``power_limit`` ASSIST event, earlier
    than t_release (1 - POWER_LIMIT_TIE_REL) when the push released (an event at the
    release itself is the tie k = P_max/(F_max v_e) = 1), any one when it did not. The
    event marks the law's power branch on its force before the power term, the force
    the cap applies to: under the force law's stop taper the tapered force since SP7
    step S4a (D-SP7-50; S4 read the untapered force there, review pass 1 rerun, P1-m1),
    so a push that reads power-limited flew at P_max. A binding inside one integrator step is
    logged (``prelude._passed_over``) unless its margin stays inside the watch's zero
    band (ATOL_MPS) or, should a step hold two extrema of the margin, the scan does not
    see its maximum; such a binding is not logged and does not count."""
    times = _assist_event_times(trace, POWER_LIMIT)
    if not released:
        return bool(times)
    return any(t_e < trace.t_release_s * (1.0 - POWER_LIMIT_TIE_REL) for t_e in times)


def _cap_bound(trace: RunTrace, released: bool, control: str) -> bool | None:
    """Whether a cap (F_max or P_max / sdot) bound the acceleration law's command on the
    push (SP7 step S4a fix round 1): a ``drive_cap`` ASSIST event, earlier than t_release
    (1 - POWER_LIMIT_TIE_REL) when the push released (a cap reached only at the release
    itself is a tie, as for ``_power_limited``), any one when it did not. While no cap
    binds the acceleration law flies its command exactly (the net acceleration a_cmd
    r(t) w(s)); False therefore means no cap bound on the push: it flew its command
    wherever it ran, and held a_cmd after its rise (scaled by the stop taper, if any)
    only when it released after the rise (fix round 2: a release inside the rise, or a
    push that stopped on the track, holds nothing to a release). True says that a cap
    bound, not when (it can bind inside the rise and let go later, ``drive_cap_end``).
    None for the force law, whose force limit is the law itself (its power cap is
    ``push_power_limited``), and for a stalled push (``DRIVE_STALL``: it never moved,
    fix round 2). The same logging limits as ``_power_limited`` apply to a binding inside
    one integrator step."""
    if control != CONTROL_ACCELERATION or trace.status == DRIVE_STALL:
        return None
    times = _assist_event_times(trace, DRIVE_CAP)
    if not released:
        return bool(times)
    return any(t_e < trace.t_release_s * (1.0 - POWER_LIMIT_TIE_REL) for t_e in times)


def release_point(trace: RunTrace, track: TrackGeometry) -> tuple[float, str]:
    """(s_release [m], trigger) of a track push that released: (L, ``track_end``) for a
    release at the track end, or, for a push released at its release speed before it
    (SP7 step S4a: ``prelude.fly_track`` logs the ``target_speed`` ASSIST event there),
    the flown release position, s of the last ASSIST phase's end state (the release
    state), and ``target_speed``. Inputs: the RunTrace and the track. Frame: arc length
    along the track from its start."""
    target = RELEASE_TRIGGER_TARGET_SPEED
    if any(e.name == target and e.phase == ASSIST_KIND for e in trace.events):
        last = trace.assist_phases()[-1]
        layout = last.spec.params.layout
        return float(layout.get(last.y_end, "s_m")), target
    return track.length_m, RELEASE_TRIGGER_TRACK_END


def linear_motor_facility_m(
    trace: RunTrace, assist: LinearMotorAssist, track: TrackGeometry, v_exit_mps: float | None
) -> float | None:
    """The facility length [m] of a linear-motor push: max(L, s_release + d_brake) with
    s_release from ``release_point`` and d_brake from the speed at release v_exit_mps
    [m/s] (``LinearMotorAssist.facility_length_m``: the carriage brakes from an early
    release, within the stroke left or past the track end); None when the run never
    released. It equals L + d_brake,
    to the bit, for a release at the track end."""
    if v_exit_mps is None or trace.y_release is None:
        return None
    s_release, trigger = release_point(trace, track)
    if trigger == RELEASE_TRIGGER_TRACK_END:
        return assist.facility_length_m(track, v_exit_mps)
    return assist.facility_length_m(track, v_exit_mps, s_release)


def linear_motor_metrics(
    trace: RunTrace,
    assist: LinearMotorAssist,
    track: TrackGeometry,
    v_exit_mps: float | None,
    drive_power_peak_W: float,
) -> dict[str, Any]:
    """LINEAR_MOTOR_METRICS of a linear-motor push (SI; docs/physics.md, "Linear motor").

    Inputs: the RunTrace; the drive (its settings: the bound copy the phases carry is
    not needed); the track; v_exit_mps, the exit speed [m/s] (None when the run stopped
    on the track); drive_power_peak_W, the peak mechanical drive power [W] of the push.
    Output: the settings push_control_law (``force`` or ``acceleration``),
    push_force_max_N (F_max), push_power_max_W (P_max, mechanical at the carriage),
    push_rise_time_s (t_r), push_corner_speed_mps (P_max / F_max),
    push_accel_command_mps2 (a_cmd of the acceleration law, None for the force law),
    push_stop_taper_m (s_taper, None without a taper) and push_release_speed_mps
    (v_release, None when no release speed is set; the last four since S4a, KI-052);
    push_power_limited, whether the power limit bound (a ``power_limit`` event logged
    on the push, earlier than the release by more than POWER_LIMIT_TIE_REL of the push
    time: an event at the release itself is the tie k = P_max/(F_max v_e) = 1; under the
    force law's taper it marks the cap binding on the tapered force, D-SP7-50;
    ``_power_limited``); push_cap_bound, under the acceleration law whether a cap (F_max
    or P_max / sdot) bound its command (a ``drive_cap`` event before the release, the
    same tie; False: no cap bound, so the push flew its command wherever it ran; True
    carries no timing), None for the force law and for a stalled push (``_cap_bound``,
    S4a fix rounds 1 and 2);
    push_accel_mean_mps2 =
    v_exit / t_push, a mean over the whole push (the rise, any capped or power-limited
    part and the taper included), not a single held acceleration; push_felt_g_plateau,
    the felt axial acceleration [g0] at the end of the rise (t = t_r, the
    drive_ramp_end boundary; push start for a step), from the flown state: the value
    at t_r, not one held after it (the burn on a hot push, and a power limit or the
    taper beginning later, move it; felt_g_track_peak is the peak); None when the push
    ended before t_r or stalled, and when the power limit or the taper began before
    t_r (no plateau: ``_felt_at_rise_end``);
    release_position_m and release_trigger, the real release (``release_point``: L and
    ``track_end``, or the flown position where sdot reached the release speed and
    ``target_speed``, SP7 step S4a); electrical_power_peak_W = peak mechanical power /
    efficiency; and the carriage's closed-form braking at the constant total
    deceleration a_b from the speed at release: braking_time_s = v / a_b, brake_force_N
    = m_c (a_b - g_eff sin phi) and brake_energy_J = (1/2) m_c v^2 (1 - g_eff sin phi /
    a_b), with the track's g_eff (the phases') and phi at the release position. Items
    that need the release are None without one (brake_force_N does not, except on a
    stall: the carriage never moved). The facility length of such a push, max(L,
    s_release + d_brake), is ``linear_motor_facility_m``'s, which ``track_metrics``
    writes into the common key ``facility_length_m``. Frame: the flat track frame."""
    released = trace.y_release is not None and v_exit_mps is not None
    phases = trace.assist_phases()
    g_eff = phases[0].spec.params.g_eff_mps2
    s_release, trigger = release_point(trace, track)
    phi = track.phi(s_release)
    stalled = trace.status == DRIVE_STALL
    out: dict[str, Any] = {
        "push_control_law": assist.control,
        "push_force_max_N": assist.force_max_N,
        "push_power_max_W": assist.power_max_W,
        "push_rise_time_s": assist.rise_time_s,
        "push_corner_speed_mps": assist.corner_speed_mps,
        "push_accel_command_mps2": assist.accel_command_mps2,
        "push_stop_taper_m": assist.stop_taper_m,
        "push_release_speed_mps": assist.release_speed_mps,
        "push_power_limited": _power_limited(trace, released),
        "push_cap_bound": _cap_bound(trace, released, assist.control),
        "push_accel_mean_mps2": (
            v_exit_mps / trace.t_release_s if released and v_exit_mps is not None else None
        ),
        "push_felt_g_plateau": None if stalled else _felt_at_rise_end(trace, assist.rise_time_s),
        "release_position_m": s_release if released else None,
        "release_trigger": trigger if released else None,
        "electrical_power_peak_W": assist.electrical_power_W(drive_power_peak_W),
        "braking_time_s": assist.braking_time_s(v_exit_mps) if v_exit_mps is not None else None,
        "brake_force_N": None if stalled else assist.brake_force_N(g_eff, phi),
        "brake_energy_J": (
            assist.brake_energy_J(v_exit_mps, g_eff, phi) if v_exit_mps is not None else None
        ),
    }
    return out


# ------------------------------------- exact track peaks (SP7 step S4b; KI-046)

TRACK_PEAK_SCAN_POINTS = 256
"""Samples per ASSIST sub-phase on which ``track_peaks`` brackets the local maxima of
its quantities (the scan of ``losses.drive_power_extrema``, DRIVE_POWER_SCAN_POINTS)."""
TRACK_PEAK_XATOL_S = 1e-10
"""Time tolerance [s] of the bounded Brent search that refines a track peak (the value
error is second order in it; as ``losses.DRIVE_POWER_XATOL_S``)."""
TRACK_PEAK_TIE_REL = 1e-12
"""How far [relative] a candidate must exceed the incumbent in ``track_peaks`` to replace
it (review round 3 of SP7 step S4b, P3-M1). The candidates are offered in time order, so
a maximum that is flat to rounding keeps its earliest instant, a sub-phase boundary,
instead of one rounding picks: on a force plateau without a carriage the interface force
F_max and n m_v = (F_max + T)/g0 are flat, and on a hot push the contents change along
that plateau, so a rounding-chosen instant moved the push's cases with every iterate of
dm and kept the structural fixed point from converging. A sample no more than this above
its neighbours is not refined (``track_peaks``). The value kept lies within 1.25 times
this tolerance of the largest."""

type TrackQuantities = Callable[[float, np.ndarray, TrackParams], tuple[float, ...]]
"""Quantities of one track state, (t [s], track-layout state, the phase's TrackParams) ->
a fixed number of floats, whose maxima ``track_peaks`` locates."""


@dataclass(frozen=True, eq=False)
class TrackScan:
    """``fn`` sampled on one ASSIST sub-phase that spans time (``track_scan``): t_s, the
    n_points scan times [s], ends included; y, the dense-output states there, shape
    (n_states, n_points) in the track layout; values, fn's quantities there, shape
    (n_points, count)."""

    t_s: np.ndarray
    y: np.ndarray
    values: np.ndarray


def track_scan(
    phases: Sequence[PhaseResult],
    fn: TrackQuantities,
    count: int,
    *,
    n_points: int = TRACK_PEAK_SCAN_POINTS,
) -> tuple[TrackScan | None, ...]:
    """The scan ``track_peaks`` brackets its maxima on (SP7 step S4b), one entry per
    phase in order: a TrackScan of fn at n_points (>= 3) equally spaced times of a phase
    that spans time (one vectorised dense-output evaluation), None for a phase that
    spans none. Inputs as ``track_peaks``. ValueError for n_points < 3, a quantity count
    that does not match fn's and a phase that spans time without dense output. Frame:
    the track frame."""
    if n_points < 3:
        raise ValueError(f"n_points must be >= 3, got {n_points}")
    out: list[TrackScan | None] = []
    for res in phases:
        if res.span_s <= 0.0:
            out.append(None)
            continue
        if res.dense is None:
            raise ValueError(
                f"track_peaks: the ASSIST phase at t = {res.spec.t0:.6g} s has no dense "
                "output (a search evaluation); the exact peaks need a flown push"
            )
        params: TrackParams = res.spec.params
        ts = np.linspace(res.spec.t0, res.t_end, n_points)
        ys = np.asarray(res.dense(ts), dtype=float)  # one vectorised dense evaluation
        rows = [fn(float(t), ys[:, i], params) for i, t in enumerate(ts)]
        if any(len(row) != count for row in rows):
            raise ValueError(f"fn gave {len(rows[0])} quantities, expected {count}")
        out.append(TrackScan(ts, ys, np.array(rows, dtype=float)))
    return tuple(out)


@dataclass(frozen=True, eq=False)
class TrackPeak:
    """The largest value of one track quantity over a push (``track_peaks``): value (the
    quantity's unit), the absolute time t_s [s], the track state y there (the phase's own
    start or end state at a sub-phase boundary, the dense output inside a sub-phase) and
    the TrackParams of its sub-phase."""

    value: float
    t_s: float
    y: np.ndarray
    params: TrackParams


def track_peaks(
    phases: Sequence[PhaseResult],
    fn: TrackQuantities,
    count: int,
    *,
    n_points: int = TRACK_PEAK_SCAN_POINTS,
    xatol_s: float = TRACK_PEAK_XATOL_S,
    scans: Sequence[TrackScan | None] | None = None,
) -> tuple[TrackPeak, ...]:
    """The exact maxima of ``count`` quantities over the ASSIST sub-phases of a push, from
    the dense output (SP7 step S4b; KI-046; docs/physics.md, "The flown push of a linear
    motor"): the pattern of ``losses.drive_power_extrema`` and of
    ``metrics_planar.scan_peak``.

    Inputs: phases, the push's ASSIST PhaseResults in time order (track layout and
    TrackParams; each phase that spans time needs its dense output); fn(t, y, params) ->
    ``count`` floats; n_points (>= 3) scan samples per sub-phase, ends included; xatol_s
    [s], the refine's time tolerance; scans, ``track_scan``'s result for the same phases,
    fn and count when the caller has it (computed here otherwise; the same numbers either
    way). Method, per quantity: every sub-phase's own start
    and end states are candidates (a peak at a sub-phase boundary, the drive's kinks, the
    thrust kinks, the watch crossings and the release, is exact); inside a sub-phase fn is
    evaluated on the n_points samples of one vectorised dense-output evaluation, and every
    sample at least as high as its neighbours and strictly higher than one of them (one
    neighbour at an end sample) brackets a local maximum that a bounded Brent search
    refines over the two neighbouring intervals; the refined value competes when it
    exceeds the sample's (an interior sample competes as itself otherwise). Every kink of
    the linear motor's force lies on a sub-phase boundary (D-SP7-49; the exceptions are
    KI-048's), so each quantity is smooth inside a sub-phase and a maximum is missed only
    when two maxima of it lie within one scan spacing (span/(n_points - 1)). The
    candidates are offered in time order (a sub-phase's start, its interior, its end) and
    one replaces the incumbent only when it exceeds it by more than TRACK_PEAK_TIE_REL
    relative (review round 3, P3-M1), so a maximum that is flat to rounding (the interface
    force and n m_v on a force plateau without a carriage) keeps its earliest instant, a
    sub-phase boundary, whatever rounding does. A sample above both neighbours by no more
    than TRACK_PEAK_TIE_REL relative is not refined (on a smooth quantity a refine gains at
    most a quarter of its excess, and on a flat plateau the brackets are rounding): it
    competes as itself. The value kept is then within 1.25 TRACK_PEAK_TIE_REL relative of
    the largest. Output: one TrackPeak per quantity, in fn's order.
    ValueError without a phase, for n_points < 3, for a quantity count that does not match
    fn's, and for a phase that spans time without dense output. Frame: the track frame.
    """
    if not phases:
        raise ValueError("track_peaks needs at least one ASSIST phase")
    if n_points < 3:
        raise ValueError(f"n_points must be >= 3, got {n_points}")
    if scans is None:
        scans = track_scan(phases, fn, count, n_points=n_points)
    if len(scans) != len(phases):
        raise ValueError("track_peaks: one scan entry per phase")
    best: list[TrackPeak | None] = [None] * count

    def offer(k: int, value: float, t: float, y: np.ndarray, params: TrackParams) -> None:
        """Make (value, t, y, params) quantity k's maximum when it exceeds the incumbent
        by more than TRACK_PEAK_TIE_REL relative (offered in time order: the earliest
        instant of a flat maximum stays)."""
        current = best[k]
        if current is None or value > current.value + TRACK_PEAK_TIE_REL * abs(current.value):
            best[k] = TrackPeak(float(value), float(t), np.array(y, dtype=float), params)

    def values(t: float, y: np.ndarray, params: TrackParams) -> tuple[float, ...]:
        out = fn(t, y, params)
        if len(out) != count:
            raise ValueError(f"fn gave {len(out)} quantities, expected {count}")
        return out

    def offer_state(t: float, y: np.ndarray, params: TrackParams) -> None:
        """Offer every quantity of one state (a sub-phase's own start or end)."""
        for k, v in enumerate(values(t, y, params)):
            offer(k, v, t, y, params)

    for res, scan in zip(phases, scans, strict=True):
        params: TrackParams = res.spec.params
        offer_state(res.spec.t0, np.asarray(res.y[:, 0], dtype=float), params)
        if res.span_s > 0.0 and scan is not None:
            dense = res.dense
            ts, ys, vals = scan.t_s, scan.y, scan.values
            n_points = ts.shape[0]
            for k in range(count):
                column = vals[:, k]
                for i in range(n_points):
                    lo, hi = max(i - 1, 0), min(i + 1, n_points - 1)
                    v, left, right = column[i], column[lo], column[hi]
                    if not (v >= left and v >= right and (v > left or v > right)):
                        continue
                    if max(v - left, v - right) <= TRACK_PEAK_TIE_REL * abs(v):
                        # flat to rounding: a refine gains at most a quarter of that
                        if 0 < i < n_points - 1:
                            offer(k, float(v), float(ts[i]), ys[:, i], params)
                        continue

                    def negative(
                        t: float, k: int = k, dense: OdeSolution = dense, p: TrackParams = params
                    ) -> float:
                        return -values(t, np.asarray(dense(t), dtype=float), p)[k]

                    sol = minimize_scalar(
                        negative,
                        bounds=(float(ts[lo]), float(ts[hi])),
                        method="bounded",
                        options={"xatol": xatol_s},
                    )
                    t_ref = float(sol.x)
                    v_ref = -float(sol.fun)
                    if v_ref > v:
                        offer(k, v_ref, t_ref, np.asarray(dense(t_ref), dtype=float), params)
                    elif 0 < i < n_points - 1:
                        offer(k, float(v), float(ts[i]), ys[:, i], params)
        offer_state(res.t_end, np.asarray(res.y_end, dtype=float), params)
    return tuple(peak for peak in best if peak is not None)


def track_felt_and_interface(t: float, y: np.ndarray, params: TrackParams) -> tuple[float, float]:
    """(felt axial acceleration [g0], interface force [N]) of one track state: F_int from
    the drive's ``state_rate`` with the delivered thrust T of the phase at t [s], and the
    felt (F_int + T)/(m_v g0), exactly ``dynamics.track_observables``' ``felt_g`` and
    ``F_int_N`` (the sampled rows' values). Frame: the track frame."""
    thrust = params.thrust_N(t)
    f = params.forces(t, y, thrust)
    m_v = float(params.layout.get(y, "m_kg"))
    return float(to_g((f.interface_force_N + thrust) / m_v)), float(f.interface_force_N)


FELT_AND_INTERFACE_COUNT = 2
"""The number of quantities ``track_felt_and_interface`` gives (felt g, interface force)."""


LINEAR_MOTOR_EXACT_PEAK_METRICS: tuple[str, ...] = (
    "felt_g_track_peak",
    "felt_g_track_peak_t_s",
    "felt_g_track_peak_mass_kg",
    "interface_force_peak_N",
    "peak_interface_force_N",
)
"""The track metrics a linear-motor push takes from ``track_peaks`` instead of the sampled
rows (SP7 step S4b; KI-046): the felt-g peak with its time after release and the mass
there, and the interface-force peak with its CLAUDE.md alias. A constant_accel push keeps
the sampled rows' values, which are exact for its monotone forces (the 1-D golden tier and
the planar output capture)."""


def linear_motor_track_peaks(trace: RunTrace) -> dict[str, Any]:
    """LINEAR_MOTOR_EXACT_PEAK_METRICS of a linear-motor push that did not stall, from
    ``track_peaks`` of (felt g, interface force) over its ASSIST sub-phases (SP7 step S4b):
    felt_g_track_peak [g0] with its time after release [s] (None when the push never
    released) and the vehicle mass there [kg]; interface_force_peak_N [N] and its alias
    peak_interface_force_N. Each is at least the sampled rows' value less 1.25
    TRACK_PEAK_TIE_REL relative (the rows are dense output samples and sub-phase ends, the
    ends are candidates here, and a flat maximum keeps its earliest instant), higher where
    a peak lies between samples: a stop taper entered during the rise, 2e-5 relative
    measured. Input: the RunTrace. Frame: the track frame."""
    felt, f_int = track_peaks(
        trace.assist_phases(), track_felt_and_interface, FELT_AND_INTERFACE_COUNT
    )
    m_kg = float(felt.params.layout.get(felt.y, "m_kg"))
    return {
        "felt_g_track_peak": felt.value,
        "felt_g_track_peak_t_s": _rel_release(trace, felt.t_s),
        "felt_g_track_peak_mass_kg": m_kg,
        "interface_force_peak_N": f_int.value,
        "peak_interface_force_N": f_int.value,
    }


def run_wide_felt_with_track_peak(metrics: Mapping[str, Any]) -> dict[str, Any]:
    """The run-wide felt-g items (``peak_felt_axial_g`` with ``_t_s``, ``_mass_kg`` and
    ``_phase``) lifted to a linear-motor push's exact track peak when it exceeds the
    run-wide value (from the sampled rows; on a planar run with the flight's scan peak
    among them) (SP7 step S4b): the track peak then is the
    run's, at its time and mass, in phase ASSIST; {} otherwise (also when either value is
    missing), so the run-wide peak is never below ``felt_g_track_peak``. Input: the merged
    metrics of the run (``run_metrics`` or ``planar_run_metrics`` updated by the track
    metrics)."""
    track = metrics.get("felt_g_track_peak")
    run = metrics.get("peak_felt_axial_g")
    if track is None or run is None or run >= track:
        return {}
    return {
        "peak_felt_axial_g": track,
        "peak_felt_axial_g_t_s": metrics.get("felt_g_track_peak_t_s"),
        "peak_felt_axial_g_mass_kg": metrics.get("felt_g_track_peak_mass_kg"),
        "peak_felt_axial_g_phase": ASSIST_KIND,
    }


def track_flags(
    frame: pd.DataFrame, drive_work_out_J: float = 0.0, *, stalled: bool = False
) -> list[str]:
    """Run flags of the push: ``interface_tensile`` when the interface force is negative
    anywhere on the sampled ASSIST rows (the vehicle would have to be held back on the
    carriage), never on a stalled push (stalled True: a ``drive_stall`` run, whose one
    ASSIST row is the drive at F_max with no support reaction, at most the loads of the
    stack at rest; its interface-force metrics are None, ``STALL_UNAVAILABLE_TRACK_METRICS``);
    ``drive_braking`` when the drive did negative work (drive_work_out_J > 0: it braked
    the engine, with allow_negative_drive_force or a push at the drive-limit threshold
    whose event was disarmed at t0)."""
    rows = frame[frame["phase"] == ASSIST_KIND]
    if rows.empty:
        return []
    flags: list[str] = []
    f_min = float(rows["interface_force_N"].min())
    if f_min < 0.0 and not stalled:
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
    along the track tangent beyond the release point, z = z_exit + d_brake sin phi(L)
    for a release at the track end, z(s_release) + d_brake sin phi(s_release) for a
    push released at its release speed before it (SP7 step S4a, ``release_point``: the
    carriage brakes from the release point). None on a pad or when the run never
    released."""
    if track is None or trace.y_release is None:
        return None
    v_exit = abs(float(VERTICAL_LAYOUT.get(trace.y_release, "v_mps")))
    d_brake = assist.braking_distance_m(v_exit)
    s_release, trigger = release_point(trace, track)
    if trigger != RELEASE_TRIGGER_TRACK_END:
        z_release = track.start_altitude_m + track.z(s_release)
        return z_release + d_brake * math.sin(track.phi(s_release))
    z_exit = track.start_altitude_m + track.z(track.length_m)
    return z_exit + d_brake * math.sin(track.phi(track.length_m))


def impact_in_shaft(trace: RunTrace, z_ground_m: float) -> bool:
    """True when the run's impact event lies more than ATOL_M below the ground altitude
    z_ground_m [m]: a fall back inside the shaft after a release below the ground (from an
    apex inside the shaft, or through the open mouth from one above it, when the floor
    lies below the ground), onto the parked carriage (``prelude.shaft_floor_m``) or, with
    a carriage braking at less than the vehicle's deceleration, at the apex (SP7 step S4a
    fix rounds 3 and 4, P3-M2, P4-M1). False without an impact. Frame: the +z-up datum
    frame."""
    impact = trace.first_event("impact")
    return impact is not None and impact.z_m < z_ground_m - ATOL_M


def failed_ignition_metrics(
    trace: RunTrace,
    g_eff_mps2: float,
    assist: AssistModel,
    track: TrackGeometry | None,
    z_ground_m: float = 0.0,
) -> dict[str, Any]:
    """The metrics of a run in which a stage's ignition failed (docs/physics.md,
    "Failed-ignition coast"); an empty dict when no stage failed.

    Inputs: the RunTrace (``failed_stage`` set); g_eff_mps2, the constant effective
    gravity of the track [m/s^2]; assist, the assist model (its carriage braking
    distance); track, the track geometry or None for a pad; z_ground_m [m], the
    planner's ground altitude (the impact surface outside the shaft). Output keys (SI;
    times relative to release; None when the run did not reach the item):
    ``failed_stage`` (the stage name); ``failed_apex_alt_m``, the highest apex [m] of
    the unpowered flight that ends in the failure, i.e. after the last burnout before
    it or after release for a first stage (``last_burn_end_s``; None when the vehicle
    was already falling, or never flew); ``failed_t_apex_s`` [s]; for a track run,
    ``failed_carriage_alt_m`` [m], where the braked carriage parks
    (``carriage_park_altitude_m``), ``failed_t_carriage_s`` [s] and
    ``failed_speed_at_carriage_mps`` [m/s], when and how fast the falling vehicle
    first comes down to that altitude (the first obstacle in the fall-back path; None
    when the apex is below it, which a carriage braking at less than the vehicle's
    deceleration gives, inside the shaft or above the ground); ``failed_t_return_s`` [s],
    when the vehicle is back
    down at its release altitude (the silo mouth, or the pad): the first downward
    crossing of z_release after that last burn (``descent_crossing_time_s``), which is
    the impact event itself when the mouth is at the ground (the plan's datum,
    exit_altitude_m = 0) and None when the ground is above the mouth, when the
    vehicle falls back inside the shaft onto the parked carriage, which lies above the
    release point (from an apex inside the shaft or, through the open mouth, above it),
    or when, after a push released at its release speed below the ground whose carriage
    parks at or above the ground, the fall ends at the ground, above the release altitude
    (FAILED_IGNITION_EARLY_TRACK_ASSUMPTIONS; SP7 step S4a fix round 5, P5-m1);
    ``failed_impact_speed_mps`` [m/s], |v| at the impact event at the ground (z =
    z_ground), None for an impact inside the shaft (``impact_in_shaft``: after a release
    below the ground the floor of the flight model there is the parked carriage, so the
    impact's time and speed are ``failed_t_carriage_s`` and
    ``failed_speed_at_carriage_mps``, or, with a carriage braking at less than the
    vehicle's deceleration, the impact is at the apex; SP7 step S4a fix round 3, P3-M2,
    and ``failed_ignition_flags``); and, for a track run,
    ``failed_speed_at_shaft_bottom_mps`` [m/s], the
    speed a vehicle falling on from the impact point would have at the track start
    (the shaft bottom), derived and not integrated: v_bottom^2 = v_impact^2 + 2 g_eff
    (z_impact - z_track_start) under the track's constant g_eff (the mirror of the
    push; z_impact - z_track_start = L when the mouth is at the ground). The carriage
    items and the shaft-bottom speed are the obstacle-free coast values: no impact
    with the carriage is modelled (stated in FAILED_IGNITION_TRACK_ASSUMPTIONS), except
    inside the shaft after a release below the ground, where the carriage is the floor
    and the shaft-bottom speed the obstacle-free value through it
    (FAILED_IGNITION_SHAFT_ASSUMPTIONS).
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
        "failed_impact_speed_mps": None if impact_in_shaft(trace, z_ground_m) else v_impact,
        "failed_speed_at_shaft_bottom_mps": v_bottom,
    }


def failed_ignition_flags(
    trace: RunTrace, track: TrackGeometry | None, z_ground_m: float
) -> list[str]:
    """Run flags of a failed-ignition track run whose mouth (the track exit) is not at
    the ground z_ground_m [m] the impact event fires on: the coast metrics then split
    between the two altitudes, and the flag says which is which; or, for one whose impact
    lies inside the shaft (``impact_in_shaft``; SP7 step S4a fix rounds 3 and 4, P3-M2,
    P4-M1, H4-m2), that flag alone: where the impact is (on the parked carriage, its time
    and speed in the carriage items, after a fall from an apex inside the shaft or through
    the open mouth; or at the apex, the carriage parked above it) and which items are
    None. Inputs: the RunTrace (with an impact event), the track geometry and the
    planner's ground altitude; empty for a pad, a run without an impact, or a mouth at
    the ground (within ATOL_M) with the impact there. Frame: the +z-up datum frame."""
    impact = trace.first_event("impact")
    if track is None or trace.failed_stage is None or impact is None:
        return []
    if impact_in_shaft(trace, z_ground_m):
        if abs(impact.v_mps) > ATOL_MPS:
            return [
                f"failed ignition: the vehicle fell back inside the shaft and its impact is "
                f"at z = {impact.z_m:.6g} m, on the parked carriage (failed_t_carriage_s and "
                "failed_speed_at_carriage_mps are its time and speed); "
                "failed_impact_speed_mps (at the ground) and failed_t_return_s are None (the "
                "fall ends on the carriage, below the ground, whether or not it passed the "
                "mouth, and above the release altitude), and the shaft-bottom speed is the "
                "obstacle-free value through the carriage"
            ]
        return [
            f"failed ignition: the vehicle stopped rising inside the shaft and its impact is "
            f"at z = {impact.z_m:.6g} m, at its apex, at or below the parked carriage's "
            "altitude (a carriage that brakes at less than the vehicle's deceleration); "
            "failed_impact_speed_mps (at the ground) and failed_t_return_s are None (it "
            "never comes back down to the ground or to the release altitude), and the "
            "shaft-bottom speed is the obstacle-free value from the apex, below the carriage"
        ]
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


def metrics_record(result: Result) -> dict[str, Any]:
    """The metrics.json record of one run: its metrics plus ``status`` and ``flags``.

    Raises ValueError when a metric uses a RESERVED_METRIC_KEYS name, which would
    otherwise be overwritten here while summary.md kept the metric (a schema error).
    """
    clash = sorted(RESERVED_METRIC_KEYS & set(result.metrics))
    if clash:
        raise ValueError(f"metrics use reserved keys {clash}; see sim.RESERVED_METRIC_KEYS")
    return {**result.metrics, "status": result.status, "flags": result.flags}
