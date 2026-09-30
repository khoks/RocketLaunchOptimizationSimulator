"""Time series, events and the per-run metrics of a 1-D run (moved from sim.py; pure: no
I/O).

``sample_trace`` samples a RunTrace into the time series (TIMESERIES_COLUMNS) and
``events_frame`` lists its events (EVENT_COLUMNS). ``run_metrics`` gives the flat
metrics dict of a run, ``track_metrics`` and ``track_flags`` the items of a push,
``failed_ignition_metrics`` and ``failed_ignition_flags`` those of a failed ignition,
``ignition_timing_metrics`` the constant-g ignition-timing yardsticks, and
``metrics_record`` the metrics.json record of one run. Units are SI with the unit in
each key; times are relative to release unless a key says otherwise; the frame is the
+z-up ascent datum frame of ``dynamics.VERTICAL_LAYOUT``. ``sim.simulate`` calls these
and ``sim`` re-exports every name.
"""

from __future__ import annotations

import math
from collections.abc import Container, Mapping
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
from scipy.integrate import OdeSolution
from scipy.optimize import brentq

from launchsim.assist.base import AssistModel, TrackGeometry
from launchsim.dynamics import (
    VERTICAL_LAYOUT,
    TrackParams,
    track_observables,
    track_to_vertical,
)
from launchsim.losses import (
    AssistEnergyBudget,
    LossBudget,
    drive_power_extrema,
    drive_work_split,
    ignition_loss_analytic_mps,
)
from launchsim.phases import (
    ASCENT_KINDS,
    ASSIST_KIND,
    ATOL_M,
    ZERO_SPAN_S,
    HoldParams,
    IgnitionSpec,
    IntegratorSettings,
    PhaseResult,
    RunTrace,
    sample_grid,
)
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


def metrics_record(result: Result) -> dict[str, Any]:
    """The metrics.json record of one run: its metrics plus ``status`` and ``flags``.

    Raises ValueError when a metric uses a RESERVED_METRIC_KEYS name, which would
    otherwise be overwritten here while summary.md kept the metric (a schema error).
    """
    clash = sorted(RESERVED_METRIC_KEYS & set(result.metrics))
    if clash:
        raise ValueError(f"metrics use reserved keys {clash}; see sim.RESERVED_METRIC_KEYS")
    return {**result.metrics, "status": result.status, "flags": result.flags}
