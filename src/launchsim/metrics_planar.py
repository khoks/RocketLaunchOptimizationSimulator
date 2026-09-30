"""Planar peak and load metrics, time series, events and the per-run metrics
(docs/physics.md, "Max-Q and loads (planar)" and "Reporting definitions (planar)").

The functions here read a planar run's phases (``phases.planar``; PLANAR_LAYOUT states
with ``PlanarParams``) and find peaks by a scan that does not depend on the output
sampling interval: ``scan_peak`` samples each flight phase's dense output at a fixed
number of uniform points plus the phase ends, and refines every local maximum with a
bounded Brent search on the dense output, so a peak inside a phase is located to the
configured time tolerance and a peak on a phase boundary (a thrust kink, a mass map)
is exact. ``max_q`` applies it to the dynamic pressure; ``q_alpha_pa_rad``,
``felt_axial_g`` and ``felt_lateral_g`` are the other instantaneous load quantities
(q-alpha with alpha = psi, the angle between thrust and v_rel; the proper acceleration
along and across the thrust axis), for the same scan.

The reporting side: ``sample_trace_planar`` samples a recorded planar RunTrace into the
time series (PLANAR_TIMESERIES_COLUMNS; gamma_rel unwrapped per run by ``unwrap_rad``,
amendment 14),
``events_frame_planar`` lists its events (PLANAR_EVENT_COLUMNS), ``planar_run_metrics``
gives the flat metrics of the flight (loss budget, MECO, fairing, cutoff and its
elements, max-Q, peak q-alpha, felt loads, kick), ``planar_track_metrics`` the items of
a push, ``search_metrics`` and ``closure_metrics`` the figures of merit and the
rocket-equation closure; PLANAR_REQUIRED_METRICS (amendment 10) are the keys every
planar summary reports.

Pure: no I/O, no globals, no printing. SI units and radians; loads in units of g0 only
through ``units.to_g``. Frame: planar ECI, every aerodynamic quantity relative to the
co-rotating air.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

from launchsim.assist.base import AssistModel, TrackGeometry
from launchsim.constants import V_REL_EPS_MPS
from launchsim.dynamics import PLANAR_LAYOUT, PlanarParams, TrackParams, planar_forces
from launchsim.losses import (
    AssistEnergyBudget,
    ClosureTerms,
    LossBudget,
    drive_power_extrema,
    drive_work_split,
)
from launchsim.metrics import (
    REQUIRED_METRICS,
    TRACK_COLUMNS,
    TRACK_METRIC_ALIASES,
    _phase_samples,
    _rel_release,
    _track_rows,
)
from launchsim.orbit import orbit_elements
from launchsim.phases import (
    ASSIST_KIND,
    ATOL_RAD,
    HOLD_KIND,
    HoldParams,
    PhaseResult,
    RunTrace,
)
from launchsim.phases.planar import (
    COAST_STAGING,
    FAIRING_EVENT,
    KICK,
    LTG_BURN,
    PLANAR_ASCENT_KINDS,
    PLANAR_COLUMNS,
    VERTICAL_RISE,
    PlanarView,
)
from launchsim.units import j_to_kwh, to_g
from launchsim.vehicle import Vehicle

if TYPE_CHECKING:
    from scipy.integrate import OdeSolution

    from launchsim.search import SearchRecord

PeakFn = Callable[[float, np.ndarray, PlanarParams], float]
"""A scalar of one planar instant: fn(t [s], y (PLANAR_LAYOUT), the phase's
PlanarParams) -> value (any unit)."""

_R = PLANAR_LAYOUT.index("r_m")
_M = PLANAR_LAYOUT.index("m_kg")


@dataclass(frozen=True, eq=False)
class Peak:
    """The largest value of a scanned quantity over a run's flight phases: value (the
    quantity's unit), the absolute time t_s [s], the phase kind and stage index it lies
    in, the state y there (PLANAR_LAYOUT; from the dense output inside a phase, the
    phase's own end state at a boundary) and the phase's PlanarParams."""

    value: float
    t_s: float
    phase: str
    stage_index: int
    y: np.ndarray
    params: PlanarParams


@dataclass(frozen=True)
class MaxQ:
    """Maximum dynamic pressure of a flight: q_pa [Pa] = 0.5 rho V^2 with V = |v_rel|,
    its absolute time t_s [s], the altitude alt_m [m] above the datum and the Mach
    number there, and the phase kind it lies in (unthrottled: the model has no throttle
    bucket, so the value is an upper bound on the flown max-Q)."""

    q_pa: float
    t_s: float
    alt_m: float
    mach: float
    phase: str


def dynamic_pressure_pa(t: float, y: np.ndarray, p: PlanarParams) -> float:
    """Dynamic pressure q = 0.5 rho(h) V^2 [Pa] of a planar state at time t [s]
    (V = |v_rel|, rho at h = r - r_datum; ``dynamics.planar_forces``)."""
    return planar_forces(t, y, p).q_pa


def psi_rad(t: float, y: np.ndarray, p: PlanarParams) -> float:
    """The angle psi [rad] between the thrust axis and v_rel, acos(cos psi) with
    cos psi clipped to [-1, 1] (0 for an along-v_rel law and, by the convention of
    ``planar_forces``, for an unpowered phase). The model has no lift, so this is the
    angle of attack alpha the q-alpha metric reads (body axis = thrust axis)."""
    return math.acos(min(1.0, max(-1.0, planar_forces(t, y, p).cos_psi)))


def q_alpha_pa_rad(t: float, y: np.ndarray, p: PlanarParams) -> float:
    """q-alpha = q psi [Pa rad] of a planar state at time t [s] (alpha = psi, the angle
    between thrust and v_rel; the kick's aerodynamic load indicator)."""
    f = planar_forces(t, y, p)
    return f.q_pa * math.acos(min(1.0, max(-1.0, f.cos_psi)))


def felt_accel_g(t: float, y: np.ndarray, p: PlanarParams) -> tuple[float, float]:
    """The felt (proper) acceleration of a planar state at time t [s] along and across
    the thrust axis, in units of g0: axial (T - D cos psi)/(m g0) and lateral
    D sin psi/(m g0) >= 0, from the non-gravitational acceleration (T e - D v_hat_rel)/m
    projected on the thrust direction e and on its normal (T the delivered thrust, D the
    drag along -v_hat_rel, psi the angle between e and v_rel). In an unpowered phase
    the axis is v_rel by convention (psi = 0): axial -D/(m g0), lateral 0. Frame: the
    body (thrust) axis; the gravitational acceleration is not felt."""
    f = planar_forces(t, y, p)
    m = float(y[_M])
    cos_psi = min(1.0, max(-1.0, f.cos_psi))
    sin_psi = math.sqrt(1.0 - cos_psi * cos_psi)
    return to_g((f.T_N - f.D_N * cos_psi) / m), to_g(f.D_N * sin_psi / m)


def felt_axial_g(t: float, y: np.ndarray, p: PlanarParams) -> float:
    """Felt axial acceleration (T - D cos psi)/(m g0) [g] (``felt_accel_g``)."""
    return felt_accel_g(t, y, p)[0]


def felt_lateral_g(t: float, y: np.ndarray, p: PlanarParams) -> float:
    """Felt lateral acceleration D sin psi/(m g0) [g] (``felt_accel_g``)."""
    return felt_accel_g(t, y, p)[1]


def scan_peak(
    phases: Sequence[PhaseResult],
    fn: PeakFn,
    *,
    n_points: int,
    xatol_s: float,
    kinds: Sequence[str] = PLANAR_ASCENT_KINDS,
) -> Peak | None:
    """The largest value of fn over the phases whose kind is in kinds (the planar
    flight phases by default), independent of any output sampling interval.

    Inputs: the run's PhaseResults (planar states and PlanarParams; dense output
    required for every phase of those kinds that spans time: a phase integrated with
    dense output off raises ValueError, since its interior is unknown); fn(t, y,
    params); n_points (>= 2) uniform scan samples per phase, ends included; xatol_s
    [s], the time tolerance of the refine. Method: every phase's two end states (its
    own, not interpolated) are candidates, so a peak on a phase boundary is exact;
    inside a phase fn is evaluated at the n_points samples of one vectorised
    dense-output evaluation, and every sample at least as high as both neighbours and
    strictly higher than one of them (one neighbour at an end sample) brackets a local
    maximum that a bounded Brent
    search (``scipy.optimize.minimize_scalar``, xatol_s) refines on the dense output
    over the two neighbouring intervals; the refined value competes only when it
    exceeds the sample's. A maximum narrower than the scan spacing (span/(n_points - 1))
    between two lower samples can be missed. Output: the Peak, or None when no phase
    of those kinds exists.
    """
    if n_points < 2:
        raise ValueError(f"n_points must be >= 2, got {n_points}")
    best: Peak | None = None

    def offer(value: float, t: float, res: PhaseResult, y: np.ndarray) -> None:
        nonlocal best
        if best is None or value > best.value:
            spec = res.spec
            best = Peak(value, float(t), spec.kind, spec.stage_index, y, spec.params)

    for res in phases:
        if res.spec.kind not in kinds:
            continue
        params = res.spec.params
        y_start = np.asarray(res.y[:, 0], dtype=float)
        offer(fn(res.spec.t0, y_start, params), res.spec.t0, res, y_start)
        offer(fn(res.t_end, res.y_end, params), res.t_end, res, np.asarray(res.y_end))
        if res.span_s <= 0.0:
            continue
        if res.dense is None:
            raise ValueError(
                f"scan_peak: phase {res.spec.kind} at t = {res.spec.t0:.6g} s has no dense "
                "output (a search evaluation); peaks need a recorded run"
            )
        dense = res.dense

        def value_at(t: float, dense: OdeSolution = dense, params: PlanarParams = params) -> float:
            return fn(t, np.asarray(dense(t), dtype=float), params)

        ts = np.linspace(res.spec.t0, res.t_end, n_points)
        ys = np.asarray(dense(ts), dtype=float)  # one vectorised dense evaluation
        vals = np.array([fn(float(t), ys[:, i], params) for i, t in enumerate(ts)])
        for i in range(n_points):
            lo, hi = max(i - 1, 0), min(i + 1, n_points - 1)
            left, right = vals[lo], vals[hi]
            if not (vals[i] >= left and vals[i] >= right and (vals[i] > left or vals[i] > right)):
                continue
            sol = minimize_scalar(
                lambda t: -value_at(t),
                bounds=(float(ts[lo]), float(ts[hi])),
                method="bounded",
                options={"xatol": xatol_s},
            )
            t_ref = float(sol.x)
            v_ref = -float(sol.fun)
            if v_ref > vals[i]:
                offer(v_ref, t_ref, res, np.asarray(dense(t_ref), dtype=float))
            elif 0 < i < n_points - 1:
                offer(float(vals[i]), float(ts[i]), res, ys[:, i].copy())
    return best


def max_q(
    phases: Sequence[PhaseResult],
    *,
    n_points: int,
    xatol_s: float,
    kinds: Sequence[str] = PLANAR_ASCENT_KINDS,
) -> MaxQ | None:
    """Maximum dynamic pressure over the planar flight phases (``scan_peak`` of
    ``dynamic_pressure_pa`` with n_points scan samples per phase, the config's
    ``checks.maxq_scan_points``, and the refine tolerance xatol_s [s],
    ``checks.maxq_xatol_s``), with the altitude above the datum [m] and the Mach number
    there; None without flight phases."""
    peak = scan_peak(phases, dynamic_pressure_pa, n_points=n_points, xatol_s=xatol_s, kinds=kinds)
    if peak is None:
        return None
    f = planar_forces(peak.t_s, peak.y, peak.params)
    alt = float(peak.y[_R]) - peak.params.r_datum_m
    return MaxQ(q_pa=peak.value, t_s=peak.t_s, alt_m=alt, mach=f.mach, phase=peak.phase)


# ------------------------------------------------------------------------- reporting

PLANAR_REQUIRED_METRICS: tuple[str, ...] = (
    *REQUIRED_METRICS,
    "payload_kg",
    "residual_propellant_kg",
    "dv_margin_mps",
    "search_status",
    "peak_felt_axial_g_flight",
    "peak_felt_lateral_g",
    "peak_q_alpha",
    "max_q_time_s",
    "max_q_mach",
)
"""Metric keys every planar summary reports (amendment 10): the 1-D REQUIRED_METRICS
plus the figures of merit (P*, the residual propellant and the dv margin at the vehicle
payload P0, the search status) and the planar loads. Each is a row of
``summary.PLANAR_VARIANT_ROWS``; a searched run fills every one (non-null)."""

PLANAR_FLIGHT_COLUMNS: tuple[str, ...] = (
    "alt_m",
    "downrange_m",
    "speed_rel_mps",
    "speed_inertial_mps",
    "gamma_rel_rad",
    "pitch_rad",
    "psi_rad",
    "m_kg",
    "thrust_N",
    "thrust_vac_N",
    "drag_N",
    "q_pa",
    "mach",
    "q_alpha_pa_rad",
    "felt_axial_g",
    "felt_lateral_g",
)
"""State and load columns of a planar time-series row (SI, radians, loads in g0):
alt_m = r - r_datum; downrange_m, the Earth-fixed arc (0 before the flight);
speed_rel_mps = |v_rel| and speed_inertial_mps = hypot(v_r, v_theta); gamma_rel_rad =
atan2(w, u) of v_rel, UNWRAPPED per run (``unwrap_rad``, amendment 14: with rotation a
vertical fall-back has u < 0, so the raw angle would jump from +pi to -pi at the apex;
the unwrapped series runs on past pi instead, to 3 pi/2 in the fall; without rotation
u = 0 exactly and the ambiguous jump of exactly -pi is taken as +pi, so the fall reads
3 pi/2 too); pitch_rad, the thrust direction above
local horizontal (along v_rel in an unpowered phase, by convention, so it is unwrapped
the same way); psi_rad, the angle
between thrust and v_rel (alpha of q-alpha); m_kg; thrust_N (delivered, T_vac - p A_e
clamped at 0), thrust_vac_N, drag_N; q_pa and mach (NaN on the track: the vented shaft
has no air model); q_alpha_pa_rad = q psi; felt_axial_g and felt_lateral_g, the proper
acceleration along and across the thrust axis (hold rows: 1 g_ref, clamped; track rows:
(F_int + T)/m_v and the vehicle's track-normal load)."""
PLANAR_QUADRATURE_COLUMNS: tuple[str, ...] = (
    "J_vac_mps",
    "J_grav_mps",
    "J_alt_mps",
    "J_drag_mps",
    "J_steer_mps",
    "J_bp_mps",
)
"""The loss quadratures of a planar row (0 before the flight start)."""
PLANAR_TIMESERIES_COLUMNS: tuple[str, ...] = (
    "t_s",
    "t_rel_release_s",
    "phase",
    "stage",
    *PLANAR_FLIGHT_COLUMNS,
    *PLANAR_QUADRATURE_COLUMNS,
    *TRACK_COLUMNS,
)
"""Columns of a planar timeseries.csv (TRACK_COLUMNS NaN outside the ASSIST rows)."""
PLANAR_TIMESERIES_TEXT_COLUMNS: frozenset[str] = frozenset({"phase", "stage"})
UNWRAPPED_COLUMNS: tuple[str, ...] = ("gamma_rel_rad", "pitch_rad")
"""Angle columns a planar time series reports unwrapped per run (``unwrap_rad``): the
Earth-relative flight-path angle and the pitch, which follows it in unpowered phases. A
vertical fall-back reads 3 pi/2 in the fall with or without rotation; its apex reads
pi/2 without rotation (the local-vertical fallback below V_REL_EPS_MPS) and about pi
with it."""


def unwrap_rad(angles: np.ndarray) -> np.ndarray:
    """A series of angles [rad] unwrapped in order: numpy.unwrap (every step of more than
    pi taken the short way round), then every remaining step within ATOL_RAD (the
    integrator's angular tolerance) of -pi (ambiguous: numpy.unwrap leaves a step of
    -pi, or of -pi plus a rounding-level amount, as it is) taken as +pi instead. The
    second rule makes a vertical fall-back without rotation (u = 0: gamma_rel steps from
    +pi/2 to -pi/2 at the apex) read 3 pi/2 in the fall, as it does with rotation (u < 0:
    the angle passes through pi), so the fall has one representation (amendment 14). The
    apex itself still reads differently: pi/2 without rotation (|v_rel| below
    V_REL_EPS_MPS there, so the local-vertical fallback applies) and about pi with
    rotation (|v_rel| = 2 omega_p h at the apex, horizontal and westward). Output: a new
    float array of the same length."""
    out = np.unwrap(np.asarray(angles, dtype=float))
    if out.size < 2:
        return out
    ambiguous = np.diff(out) <= -math.pi + ATOL_RAD
    if ambiguous.any():
        out[1:] += 2.0 * math.pi * np.cumsum(ambiguous)
    return out


PLANAR_EVENT_COLUMNS: tuple[str, ...] = ("t_s", "event", "phase", "stage", *PLANAR_COLUMNS)
"""Columns of a planar events.csv: the event and the PlanarView columns (gamma_rel_rad
unwrapped over the run's events in time order, as in the time series)."""
PLANAR_EVENT_TEXT_COLUMNS: frozenset[str] = frozenset({"event", "phase", "stage"})

KICK_AT_FIRST_LIT = "at_first_lit_instant"
"""Kick regime of a run already faster than v_k (while rising) when stage 1 lights:
the kick starts there, with no vertical rise."""
KICK_AFTER_RISE = "after_vertical_rise"
"""Kick regime of a run that rises vertically until |v_rel| reaches v_k."""
KICK_NONE = "none"
"""Kick regime of a run that never kicked (failed ignition, vertical-only guidance)."""

FAIRING_IN_BURN = "in the stage-2 burn (heating event)"
"""Fairing-drop form: the heating event inside LTG_BURN (the only true event)."""
FAIRING_AT_IGNITION = "at stage-2 ignition (heating criterion met in the staging coast)"
"""Fairing-drop form: dropped at the stage-2 ignition map."""
FAIRING_AT_STAGING = "at staging"
"""Fairing-drop form: dropped with stage 1 (rule staging, or the criterion already met)."""
FAIRING_KEPT = "kept to the end of the run"
"""Fairing-drop form: never dropped (rule never, or the criterion never met)."""

RESIDUAL_BASIS_PAYLOAD = "at gamma*_ref (P*-optimal guidance)"
"""Label of the residual propellant and dv margin at P0 of a payload search."""
RESIDUAL_BASIS_RESIDUAL = "at gamma* refined at P0"
"""Label of the same figures of a residual search (never compared with the above)."""
RESIDUAL_BASIS_FIXED = "at the fixed guidance (no search)"
"""Label of the same figures of a fixed-guidance run (figure_of_merit none)."""


def empty_planar_timeseries() -> pd.DataFrame:
    """An empty planar time-series frame with PLANAR_TIMESERIES_COLUMNS."""
    return pd.DataFrame(
        {
            c: pd.Series(dtype="str" if c in PLANAR_TIMESERIES_TEXT_COLUMNS else "float64")
            for c in PLANAR_TIMESERIES_COLUMNS
        }
    )


def empty_planar_events() -> pd.DataFrame:
    """An empty planar events frame with PLANAR_EVENT_COLUMNS."""
    return pd.DataFrame(
        {
            c: pd.Series(dtype="str" if c in PLANAR_EVENT_TEXT_COLUMNS else "float64")
            for c in PLANAR_EVENT_COLUMNS
        }
    )


def planar_view(trace: RunTrace) -> PlanarView:
    """The trace's PlanarView (ValueError for a trace of another model)."""
    view = trace.view
    if not isinstance(view, PlanarView):
        raise ValueError(f"a planar trace is needed, got a {trace.model} one")
    return view


def _flight_row(
    t: float, y: np.ndarray, p: PlanarParams, view: PlanarView, phase: str
) -> dict[str, float]:
    """One flight row (PLANAR_FLIGHT_COLUMNS) of a planar state at time t [s] in a phase
    of kind ``phase`` with the phase's PlanarParams: the view's state columns and one
    ``planar_forces`` call for the rest (the formulas of ``felt_accel_g`` and
    ``q_alpha_pa_rad``)."""
    row = view.row(t, y, phase)
    f = planar_forces(t, y, p)
    m = float(y[_M])
    cos_psi = min(1.0, max(-1.0, f.cos_psi))
    psi = math.acos(cos_psi)
    sin_psi = math.sqrt(1.0 - cos_psi * cos_psi)
    return {
        **row,
        "pitch_rad": math.atan2(f.e_r, f.e_theta),
        "psi_rad": psi,
        "thrust_N": f.T_N,
        "thrust_vac_N": f.T_vac_N,
        "drag_N": f.D_N,
        "q_pa": f.q_pa,
        "mach": f.mach,
        "q_alpha_pa_rad": f.q_pa * psi,
        "felt_axial_g": float(to_g((f.T_N - f.D_N * cos_psi) / m)),
        "felt_lateral_g": float(to_g(f.D_N * sin_psi / m)),
    }


def _hold_row(t: float, y: np.ndarray, p: HoldParams, view: PlanarView) -> dict[str, float]:
    """One HOLD row at time t [s]: the vehicle clamped on the pad (the view's
    Earth-fixed state y), the hold's delivered and vacuum thrust [N], radial thrust
    (pitch pi/2, psi 0), no air load, and a felt axial acceleration of 1 g_ref [g0] (the
    clamp carries the weight)."""
    return {
        **view.row(t, y, HOLD_KIND),
        "pitch_rad": 0.5 * math.pi,
        "psi_rad": 0.0,
        "thrust_N": p.thrust_N(t),
        "thrust_vac_N": p.thrust_vac_N(t),
        "drag_N": 0.0,
        "q_pa": 0.0,
        "mach": 0.0,
        "q_alpha_pa_rad": 0.0,
        "felt_axial_g": float(to_g(p.g_eff_mps2)),
        "felt_lateral_g": 0.0,
    }


def _track_part(ts: np.ndarray, ys: np.ndarray, p: TrackParams, view: PlanarView) -> dict[str, Any]:
    """The columns of an ASSIST phase's samples (times ts [s], track-layout states ys):
    the rows of ``metrics._track_rows`` (altitude, forces, felt g, normal loads) in the
    planar columns. speed_rel = |sdot|, gamma_rel = the track angle phi (pi/2 at rest),
    speed_inertial = |sdot t_hat + omega_p (r_datum + z) theta_hat|, pitch = phi,
    psi = 0, no drag; q, Mach and q-alpha NaN (the vented shaft has no air model);
    felt_lateral_g the vehicle's track-normal load [g0]; quadratures 0. Frame: the
    flat track frame, Earth-fixed."""
    part = _track_rows(ts, ys, p)
    lay = p.layout
    s = np.asarray(lay.get(ys, "s_m"), dtype=float)
    sdot = np.asarray(lay.get(ys, "sdot_mps"), dtype=float)
    phi = np.array([p.track.phi(float(x)) for x in s])
    z = np.asarray(part["z_m"], dtype=float)
    v_up = sdot * np.sin(phi)
    v_h = sdot * np.cos(phi) + view.omega_p_rads * (view.r_datum_m + z)
    n = len(ts)
    out: dict[str, Any] = {
        "alt_m": z,
        "downrange_m": np.zeros(n),
        "speed_rel_mps": np.abs(sdot),
        "speed_inertial_mps": np.hypot(v_up, v_h),
        "gamma_rel_rad": np.where(np.abs(sdot) >= V_REL_EPS_MPS, phi, 0.5 * math.pi),
        "pitch_rad": phi,
        "psi_rad": np.zeros(n),
        "m_kg": np.asarray(part["m_kg"], dtype=float),
        "thrust_N": part["thrust_N"],
        "thrust_vac_N": part["thrust_vac_N"],
        "drag_N": np.zeros(n),
        "q_pa": np.full(n, np.nan),
        "mach": np.full(n, np.nan),
        "q_alpha_pa_rad": np.full(n, np.nan),
        "felt_axial_g": part["accel_felt_g"],
        "felt_lateral_g": part["track_normal_g_vehicle"],
    }
    out.update({c: np.zeros(n) for c in PLANAR_QUADRATURE_COLUMNS})
    out.update({c: part[c] for c in TRACK_COLUMNS})
    return out


def _rows_part(rows: list[dict[str, float]], ys: np.ndarray) -> dict[str, Any]:
    """Column arrays of a list of hold or flight rows, plus the planar quadratures from
    the states ys (PLANAR_LAYOUT) and NaN track columns."""
    n = len(rows)
    out: dict[str, Any] = {c: np.array([r[c] for r in rows], dtype=float) for c in rows[0]}
    for c in PLANAR_QUADRATURE_COLUMNS:
        out[c] = np.asarray(PLANAR_LAYOUT.get(ys, c), dtype=float)
    out.update({c: np.full(n, np.nan) for c in TRACK_COLUMNS})
    return out


def sample_trace_planar(trace: RunTrace, vehicle: Vehicle, sample_dt_s: float) -> pd.DataFrame:
    """The time series of a recorded planar run (PLANAR_TIMESERIES_COLUMNS): every phase
    sampled at the multiples of sample_dt_s [s] inside it plus its two ends (the
    ``metrics`` sampling rule), hold rows (``_hold_row``), track rows (``_track_part``)
    and flight rows (``_flight_row``); t_rel_release_s = t - t_release [s].
    gamma_rel_rad and pitch_rad (UNWRAPPED_COLUMNS) are unwrapped over the whole run
    (``unwrap_rad``, amendment 14).
    ValueError for a trace with a dense-off phase (``RunTrace.require_dense``: a search
    evaluation is not a recorded run) or with a phase whose parameters are none of the
    three kinds. Frame: planar ECI states, Earth-relative angles and speeds."""
    trace.require_dense("sample_trace_planar")
    view = planar_view(trace)
    parts: list[dict[str, Any]] = []
    for res in trace.phases:
        ts, ys = _phase_samples(res, sample_dt_s)
        params = res.spec.params
        kind = res.spec.kind
        if isinstance(params, TrackParams):
            part = _track_part(ts, ys, params, view)
        elif isinstance(params, HoldParams):
            rows = [_hold_row(float(t), ys[:, i], params, view) for i, t in enumerate(ts)]
            part = _rows_part(rows, ys)
        elif isinstance(params, PlanarParams):
            rows = [_flight_row(float(t), ys[:, i], params, view, kind) for i, t in enumerate(ts)]
            part = _rows_part(rows, ys)
        else:
            raise ValueError(f"sample_trace_planar: phase {kind} has {type(params).__name__}")
        stage = vehicle.stage_names[res.spec.stage_index]
        part.update(
            {
                "t_s": ts,
                "t_rel_release_s": ts - trace.t_release_s,
                "phase": np.full(len(ts), kind, dtype=object),
                "stage": np.full(len(ts), stage, dtype=object),
            }
        )
        parts.append(part)
    if not parts:
        return empty_planar_timeseries()
    frame = pd.concat([pd.DataFrame(p) for p in parts], ignore_index=True)
    for column in UNWRAPPED_COLUMNS:
        frame[column] = unwrap_rad(frame[column].to_numpy(dtype=float))
    return frame[list(PLANAR_TIMESERIES_COLUMNS)]


def events_frame_planar(trace: RunTrace) -> pd.DataFrame:
    """The events of a planar run (PLANAR_EVENT_COLUMNS: time [s], name, phase, stage and
    the PlanarView columns of each record, SI; gamma_rel_rad unwrapped over the events
    in time order)."""
    planar_view(trace)
    if not trace.events:
        return empty_planar_events()
    rows = [
        {
            "t_s": e.t_s,
            "event": e.name,
            "phase": e.phase,
            "stage": e.stage,
            **{c: e.value(c) for c in PLANAR_COLUMNS},
        }
        for e in trace.events
    ]
    frame = pd.DataFrame(rows)[list(PLANAR_EVENT_COLUMNS)]
    frame["gamma_rel_rad"] = unwrap_rad(frame["gamma_rel_rad"].to_numpy(dtype=float))
    return frame


# ------------------------------------------------------------------------ run metrics


def _state_row(trace: RunTrace, t: float, y: np.ndarray, label: str) -> dict[str, float]:
    """The PlanarView columns (SI) of the planar state y at time t [s] under label."""
    return planar_view(trace).row(t, y, label)


def _burnout_items(
    trace: RunTrace, vehicle: Vehicle, mu_m3s2: float, target_r_m: float | None
) -> dict[str, Any]:
    """Stage-1 burnout (MECO) and stage-2 end items (SI, times after release): altitude,
    |v_rel|, mass, and at MECO gamma_rel [rad], downrange [m] and the inertial speed;
    at the stage-2 end (cutoff or depletion) also the osculating elements from mu_m3s2
    [m^3/s^2] (e, perigee and apogee altitude above the datum) and, with a target
    radius target_r_m [m], the radius miss r_c - r_t and v_r,c. Frame: planar ECI."""
    view = planar_view(trace)
    names = vehicle.stage_names
    bo = trace.burnouts.get(names[0])
    row = None if bo is None else _state_row(trace, bo[0], bo[1], "GRAVITY_TURN")
    out: dict[str, Any] = {
        "stage1_burnout_t_s": None if bo is None else _rel_release(trace, bo[0]),
        "stage1_burnout_speed_mps": None if row is None else row["speed_rel_mps"],
        "stage1_burnout_alt_m": None if row is None else row["alt_m"],
        "stage1_burnout_mass_kg": None if row is None else row["m_kg"],
        "meco_gamma_rel_rad": None if row is None else row["gamma_rel_rad"],
        "meco_downrange_m": None if row is None else row["downrange_m"],
        "meco_speed_inertial_mps": None if row is None else row["speed_inertial_mps"],
    }
    keys = (
        "stage2_end_t_s",
        "stage2_end_alt_m",
        "stage2_end_speed_mps",
        "stage2_end_mass_kg",
        "insertion_e",
        "perigee_alt_m",
        "apogee_alt_m",
        "insertion_dr_m",
        "insertion_v_r_mps",
    )
    out.update(dict.fromkeys(keys))
    bo2 = trace.burnouts.get(names[1]) if len(names) > 1 else None
    if bo2 is None:
        return out
    t2, y2 = bo2
    row2 = _state_row(trace, t2, y2, LTG_BURN)
    r = float(y2[_R])
    v_r = float(PLANAR_LAYOUT.get(y2, "v_r_mps"))
    el = orbit_elements(r, v_r, float(PLANAR_LAYOUT.get(y2, "v_theta_mps")), mu_m3s2)
    out.update(
        {
            "stage2_end_t_s": _rel_release(trace, t2),
            "stage2_end_alt_m": row2["alt_m"],
            "stage2_end_speed_mps": row2["speed_rel_mps"],
            "stage2_end_mass_kg": row2["m_kg"],
            "insertion_e": el.e,
            "perigee_alt_m": el.r_p_m - view.r_datum_m,
            "apogee_alt_m": el.r_a_m - view.r_datum_m if math.isfinite(el.r_a_m) else None,
            "insertion_dr_m": None if target_r_m is None else r - target_r_m,
            "insertion_v_r_mps": v_r,
        }
    )
    return out


def fairing_items(trace: RunTrace, vehicle: Vehicle) -> dict[str, Any]:
    """Where the fairing went: ``fairing_drop`` (FAIRING_IN_BURN, FAIRING_AT_IGNITION,
    FAIRING_AT_STAGING or FAIRING_KEPT; None without a fairing or before staging),
    ``fairing_t_s`` [s after release] and ``fairing_alt_m`` [m] of the drop (None when
    kept). Only the first form is the heating event itself; the other two record the
    drop at a map (docs/physics.md, the three fairing-record forms)."""
    none: dict[str, Any] = {"fairing_drop": None, "fairing_t_s": None, "fairing_alt_m": None}
    if vehicle.fairing_mass_kg <= 0.0 or vehicle.n_stages < 2:
        return none
    staging = trace.first_event("staging")
    event = trace.first_event(FAIRING_EVENT)
    if event is None and vehicle.fairing_rule.trigger == "staging" and staging is not None:
        event, form = staging, FAIRING_AT_STAGING
    elif event is None:
        return {**none, "fairing_drop": FAIRING_KEPT if staging is not None else None}
    elif event.phase == COAST_STAGING:
        form = FAIRING_AT_STAGING
    elif event.t_s == trace.t_ign_abs_s.get(vehicle.stage_names[1]):
        form = FAIRING_AT_IGNITION
    else:
        form = FAIRING_IN_BURN
    return {
        "fairing_drop": form,
        "fairing_t_s": _rel_release(trace, event.t_s),
        "fairing_alt_m": event.value("alt_m"),
    }


def kick_items(trace: RunTrace) -> dict[str, Any]:
    """The kick: ``kick_regime`` (KICK_AT_FIRST_LIT, KICK_AFTER_RISE or KICK_NONE),
    ``kick_t_s`` [s after release], ``speed_at_kick_mps`` (|v_rel| at the trigger),
    ``kick_duration_s`` [s] (the KICK phases' span) and ``kick_steering_loss_mps`` [m/s]
    (J_steer booked inside KICK)."""
    start = trace.first_event("kick_start")
    if start is None:
        return {
            "kick_regime": KICK_NONE,
            "kick_t_s": None,
            "speed_at_kick_mps": None,
            "kick_duration_s": None,
            "kick_steering_loss_mps": None,
        }
    rise = any(p.spec.kind == VERTICAL_RISE for p in trace.phases)
    kicks = [p for p in trace.phases if p.spec.kind == KICK]
    steer = sum(
        float(PLANAR_LAYOUT.get(p.y_end, "J_steer_mps"))
        - float(PLANAR_LAYOUT.get(p.y[:, 0], "J_steer_mps"))
        for p in kicks
    )
    return {
        "kick_regime": KICK_AFTER_RISE if rise else KICK_AT_FIRST_LIT,
        "kick_t_s": _rel_release(trace, start.t_s),
        "speed_at_kick_mps": start.value("speed_rel_mps"),
        "kick_duration_s": sum(p.span_s for p in kicks),
        "kick_steering_loss_mps": steer,
    }


def _peak_items(
    trace: RunTrace, fn: PeakFn, key: str, n_points: int, xatol_s: float
) -> tuple[dict[str, Any], Peak | None]:
    """``<key>``, ``<key>_t_s`` [s after release] and ``<key>_phase`` of the
    flight-phase peak of fn (``scan_peak`` with n_points, xatol_s [s]), None without
    flight phases; and the Peak."""
    peak = scan_peak(trace.ascent_phases(), fn, n_points=n_points, xatol_s=xatol_s)
    if peak is None:
        return {key: None, f"{key}_t_s": None, f"{key}_phase": None}, None
    return {
        key: peak.value,
        f"{key}_t_s": _rel_release(trace, peak.t_s),
        f"{key}_phase": peak.phase,
    }, peak


def _run_wide_felt(frame: pd.DataFrame, flight: Peak | None, trace: RunTrace) -> dict[str, Any]:
    """The run-wide peak felt axial acceleration [g0] (the CLAUDE.md item): the largest of
    the sampled hold and track rows of the frame and the flight scan peak, with its time
    after release [s], the mass there [kg] and the phase kind."""
    best: tuple[float, float | None, float, str] | None = None
    rows = frame[~frame["phase"].isin(PLANAR_ASCENT_KINDS)]
    if not rows.empty:
        i = int(rows["felt_axial_g"].to_numpy(dtype=float).argmax())
        row = rows.iloc[i]
        best = (
            float(row["felt_axial_g"]),
            float(row["t_rel_release_s"]),
            float(row["m_kg"]),
            str(row["phase"]),
        )
    if flight is not None and (best is None or flight.value > best[0]):
        best = (flight.value, _rel_release(trace, flight.t_s), float(flight.y[_M]), flight.phase)
    return {
        "peak_felt_axial_g": None if best is None else best[0],
        "peak_felt_axial_g_t_s": None if best is None else best[1],
        "peak_felt_axial_g_mass_kg": None if best is None else best[2],
        "peak_felt_axial_g_phase": None if best is None else best[3],
    }


def _release_items(trace: RunTrace, vehicle: Vehicle) -> dict[str, Any]:
    """Release, flight-start and hold items (as the 1-D ``run_metrics``, SI): |v_rel|,
    altitude and mass at release, the propellant burned before release and before the
    flight with their vacuum delta-v equivalents c1 ln(m0/m), and the hold summary."""
    stage0 = vehicle.stages[0]
    m0 = vehicle.liftoff_mass_kg()
    y_rel, y_fs = trace.y_release, trace.y_flight_start
    rel = None if y_rel is None else _state_row(trace, trace.t_release_s, y_rel, ASSIST_KIND)
    m_rel = None if rel is None else rel["m_kg"]
    m_fs = None if y_fs is None else float(y_fs[_M])
    hold = trace.hold
    return {
        "liftoff_mass_kg": m0,
        "t_release_s": None if y_rel is None else trace.t_release_s,
        "speed_at_release_mps": None if rel is None else rel["speed_rel_mps"],
        "alt_at_release_m": None if rel is None else rel["alt_m"],
        "mass_at_release_kg": m_rel,
        "propellant_burned_before_release_kg": None if m_rel is None else m0 - m_rel,
        "dv_vac_equiv_before_release_mps": (
            None if m_rel is None else stage0.c_mps * math.log(m0 / m_rel)
        ),
        "t_flight_start_s": _rel_release(trace, trace.t_flight_start_s),
        "mass_at_flight_start_kg": m_fs,
        "propellant_burned_before_flight_kg": None if m_fs is None else m0 - m_fs,
        "dv_vac_equiv_before_flight_mps": (
            None if m_fs is None else stage0.c_mps * math.log(m0 / m_fs)
        ),
        "hold_duration_s": None if hold is None else hold.duration_s,
        "hold_extension_s": None if hold is None else hold.extension_s,
        "hold_down_force_min_N": None if hold is None else hold.force_min_N,
        "hold_propellant_burned_kg": None if hold is None else hold.propellant_burned_kg,
    }


def _final_items(trace: RunTrace) -> dict[str, Any]:
    """The run's end (the last phase's end state: time after release [s], altitude [m],
    |v_rel| [m/s], mass [kg], downrange [m]), the highest apex and the impact (time,
    |v_rel|)."""
    out: dict[str, Any] = dict.fromkeys(
        ("final_t_s", "final_alt_m", "final_speed_mps", "final_mass_kg", "final_downrange_m")
    )
    if trace.phases:
        last = trace.phases[-1]
        row = _state_row(trace, last.t_end, last.y_end, last.spec.kind)
        out.update(
            {
                "final_t_s": _rel_release(trace, last.t_end),
                "final_alt_m": row["alt_m"],
                "final_speed_mps": row["speed_rel_mps"],
                "final_mass_kg": row["m_kg"],
                "final_downrange_m": row["downrange_m"],
            }
        )
    apexes = [e for e in trace.events if e.name == "apex"]
    top = max(apexes, key=lambda e: e.value("alt_m")) if apexes else None
    impact = trace.first_event("impact")
    out.update(
        {
            "apex_alt_m": None if top is None else top.value("alt_m"),
            "apex_t_s": None if top is None else _rel_release(trace, top.t_s),
            "impact_t_s": None if impact is None else _rel_release(trace, impact.t_s),
            "impact_speed_mps": None if impact is None else impact.value("speed_rel_mps"),
        }
    )
    return out


def loss_items(budget: LossBudget) -> dict[str, Any]:
    """The loss budget from the flight start [m/s] under the 1-D metric names, plus the
    identity residual (speed_end - speed_start) - (dv_vac - losses) [m/s]."""
    return {
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
    }


PAD_ASSIST_ZEROS: tuple[str, ...] = (
    "peak_track_normal_g",
    "track_normal_g_vehicle_peak",
    "track_normal_g_carriage_peak",
    "assist_energy_J",
    "assist_energy_kWh",
    "electrical_energy_J",
    "electrical_energy_kWh",
    "peak_drive_power_W",
    "drive_power_min_W",
    "peak_interface_force_N",
    "interface_force_min_N",
    "braking_distance_m",
    "facility_length_m",
)
"""Assist items a pad reports as 0 (no drive, carriage or facility: zero, not
unmeasured; the 1-D convention); ``planar_track_metrics`` overwrites them."""


def planar_run_metrics(
    trace: RunTrace,
    vehicle: Vehicle,
    budget: LossBudget,
    frame: pd.DataFrame,
    assist_name: str,
    *,
    n_points: int,
    xatol_s: float,
    mu_m3s2: float,
    target_r_m: float | None,
) -> dict[str, Any]:
    """The flat metrics of a recorded planar run (SI; times after release unless a key
    says otherwise; None for an item the run did not reach; docs/physics.md, "Reporting
    definitions (planar)").

    Inputs: the RunTrace (dense output on); the Vehicle it flew; the LossBudget from the
    flight start; the time series (``sample_trace_planar``); the assist model's name;
    n_points and xatol_s [s], the peak scan (``checks.maxq_scan_points``,
    ``checks.maxq_xatol_s``); mu_m3s2 [m^3/s^2] for the orbital elements; target_r_m
    [m], the target radius (None without one). Output: the release, flight-start and
    hold items; the ignition times; stage-1 burnout (MECO, with gamma_rel and
    downrange) and the stage-2 end with its elements; the fairing; the end, apex and
    impact; the kick; the loss budget; max-Q (``max_q``: q, time, altitude, Mach,
    phase), peak q-alpha [Pa rad], peak felt axial and lateral g in flight (scans
    independent of the sampling interval), the run-wide peak felt axial g (hold, track
    and flight); a pad's zero assist items; and nfev_total. Frame: planar ECI,
    Earth-relative angles and speeds.
    """
    out: dict[str, Any] = {"assist_model": assist_name, **_release_items(trace, vehicle)}
    for stage in vehicle.stages:
        out[f"t_ign_rel_release_s_{stage.name}"] = _rel_release(
            trace, trace.t_ign_abs_s.get(stage.name)
        )
    out.update(_burnout_items(trace, vehicle, mu_m3s2, target_r_m))
    out.update(fairing_items(trace, vehicle))
    out.update(_final_items(trace))
    out.update(kick_items(trace))
    out.update(loss_items(budget))
    mq = max_q(trace.ascent_phases(), n_points=n_points, xatol_s=xatol_s)
    out.update(
        {
            "max_q_pa": None if mq is None else mq.q_pa,
            "max_q_time_s": None if mq is None else _rel_release(trace, mq.t_s),
            "max_q_alt_m": None if mq is None else mq.alt_m,
            "max_q_mach": None if mq is None else mq.mach,
            "max_q_phase": None if mq is None else mq.phase,
        }
    )
    items, _ = _peak_items(trace, q_alpha_pa_rad, "peak_q_alpha", n_points, xatol_s)
    out.update(items)
    items, axial = _peak_items(trace, felt_axial_g, "peak_felt_axial_g_flight", n_points, xatol_s)
    out.update(items)
    out["peak_felt_axial_g_flight_mass_kg"] = None if axial is None else float(axial.y[_M])
    items, _ = _peak_items(trace, felt_lateral_g, "peak_felt_lateral_g", n_points, xatol_s)
    out.update(items)
    out.update(_run_wide_felt(frame, axial, trace))
    out.update(dict.fromkeys(PAD_ASSIST_ZEROS, 0.0))
    out["nfev_total"] = trace.nfev_total
    return out


def planar_track_metrics(
    trace: RunTrace,
    assist: AssistModel,
    track: TrackGeometry,
    budget: AssistEnergyBudget,
    frame: pd.DataFrame,
) -> dict[str, Any]:
    """The track metrics of a planar assisted run: the items and names of the 1-D
    ``metrics.track_metrics`` (docs/physics.md, "Silo model"; SI), with the exit speed
    |v_rel| at release from the planar state and the felt g from the planar frame's
    ASSIST rows (felt_axial_g). The TRACK_METRIC_ALIASES are written beside their
    canonical keys, and peak_track_normal_g = max(vehicle, carriage). Frame: the flat
    track frame with constant g_eff."""
    rows = frame[frame["phase"] == ASSIST_KIND]
    phases = trace.assist_phases()
    y_rel = trace.y_release
    v_exit = None
    if y_rel is not None:
        v_exit = _state_row(trace, trace.t_release_s, y_rel, ASSIST_KIND)["speed_rel_mps"]
    layout = phases[0].spec.params.layout
    m_start = float(layout.get(phases[0].y[:, 0], "m_kg"))
    m_end = float(layout.get(phases[-1].y_end, "m_kg"))
    work_in, work_out = drive_work_split(phases, layout)
    electrical = work_in / assist.efficiency
    p_max, t_p_max, p_min, _t_min = drive_power_extrema(phases, layout)
    felt = rows["felt_axial_g"].to_numpy(dtype=float)
    i = int(felt.argmax())
    n_v = float(rows["track_normal_g_vehicle"].max())
    n_c = float(rows["track_normal_g_carriage"].max())
    out: dict[str, Any] = {
        "exit_speed_mps": v_exit,
        "push_time_s": None if y_rel is None else trace.t_release_s,
        "felt_g_track_peak": float(felt[i]),
        "felt_g_track_peak_t_s": (
            None if y_rel is None else float(rows["t_rel_release_s"].iloc[i])
        ),
        "felt_g_track_peak_mass_kg": float(rows["m_kg"].iloc[i]),
        "interface_force_peak_N": float(rows["interface_force_N"].max()),
        "interface_force_min_N": float(rows["interface_force_N"].min()),
        "drive_force_peak_N": float(rows["drive_force_N"].max()),
        "drive_energy_J": budget.work_drive,
        "drive_energy_kWh": float(j_to_kwh(budget.work_drive)),
        "drive_work_in_J": work_in,
        "drive_work_out_J": work_out,
        "electrical_energy_J": electrical,
        "electrical_energy_kWh": float(j_to_kwh(electrical)),
        "drive_power_peak_W": max(0.0, p_max),
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
        "peak_track_normal_g": max(n_v, n_c),
    }
    out.update({alias: out[canonical] for alias, canonical in TRACK_METRIC_ALIASES.items()})
    return out


# ------------------------------------------------------------------ figures of merit


def _finite_or_none(x: float | None) -> float | None:
    """x as a float when finite, else None (null in JSON, n/a in a summary)."""
    return None if x is None or not math.isfinite(x) else float(x)


SEARCH_METRIC_KEYS: tuple[str, ...] = (
    "search_status",
    "figure_of_merit",
    "search_budget_id",
    "payload_kg",
    "payload_excess_kg",
    "residual_propellant_kg",
    "dv_margin_mps",
    "residual_propellant_basis",
    "residual_propellant_virtual",
    "dv_shortfall_mps",
    "gamma_star_rad",
    "gamma_best_grid_rad",
    "gamma_grid_payload_kg",
    "gamma_refine_payload_kg",
    "p2_minus_p1_kg",
    "search_vs_final_payload_kg",
    "delta_rad",
    "ltg_a",
    "ltg_b_per_s",
    "ltg_rung",
    "recorded_m_res_kg",
    "recorded_dv_margin_mps",
    "recorded_figures_from",
    "search_failure_kind",
    "search_failure_message",
    "search_record",
)
"""The figure-of-merit keys every planar run carries (``search_metrics``,
``fixed_guidance_metrics``), in this order."""


def search_metrics(record: SearchRecord, payload0_kg: float) -> dict[str, Any]:
    """The figures of merit of a searched run (docs/physics.md, "Figures of merit
    (planar)"), SEARCH_METRIC_KEYS: ``search_status``, ``figure_of_merit``,
    ``search_budget_id``; ``payload_kg`` = P* [kg] (payload search; None otherwise or
    when it failed) and ``payload_excess_kg`` = P0 - P*; ``residual_propellant_kg`` [kg]
    and ``dv_margin_mps`` [m/s], the signed final-tolerance rung 2 at the vehicle payload
    P0 = payload0_kg (``SearchRecord.at_p0``), labelled by
    ``residual_propellant_basis`` (RESIDUAL_BASIS_*) and flagged
    ``residual_propellant_virtual`` when negative (a virtual, massless shortfall);
    ``dv_shortfall_mps`` of a no_orbit search; the guidance found (gamma_star_rad,
    gamma_best_grid_rad, delta_rad [rad], ltg_a, ltg_b_per_s [1/s], ltg_rung); the
    search diagnostics (grid and refine payloads, P2 - P1, search minus final payload
    [kg]); the recorded run's own m_res and dv margin and where they come from; the
    failure kind and message of a failed search; and ``search_record``, the plain copy
    of the whole record (``search.as_plain``)."""
    from launchsim.search import as_plain  # late: search imports what this module does

    fom = record.figure_of_merit
    p_star = _finite_or_none(record.payload_kg) if fom == "payload" else None
    m_res = _finite_or_none(record.m_res_p0_kg)
    final = record.final
    at_final = None if final is None else final.at_final
    gamma = record.gamma
    payload = None if final is None else final.payload
    recorded = None if final is None else final.recorded
    ltg = None if at_final is None else at_final.ltg
    return {
        "search_status": record.status,
        "figure_of_merit": fom,
        "search_budget_id": record.budget_id,
        "payload_kg": p_star,
        "payload_excess_kg": None if p_star is None else payload0_kg - p_star,
        "residual_propellant_kg": m_res,
        "dv_margin_mps": _finite_or_none(record.dv_margin_p0_mps),
        "residual_propellant_basis": (
            RESIDUAL_BASIS_PAYLOAD if fom == "payload" else RESIDUAL_BASIS_RESIDUAL
        ),
        "residual_propellant_virtual": None if m_res is None else m_res < 0.0,
        "dv_shortfall_mps": None if payload is None else _finite_or_none(payload.dv_shortfall_mps),
        "gamma_star_rad": None if gamma is None else gamma.gamma_star_rad,
        "gamma_best_grid_rad": None if gamma is None else gamma.gamma_best_grid_rad,
        "gamma_grid_payload_kg": None if gamma is None else gamma.grid_payload_kg,
        "gamma_refine_payload_kg": None if gamma is None else gamma.refine_payload_kg,
        "p2_minus_p1_kg": None if gamma is None else _finite_or_none(gamma.p2_minus_p1_kg),
        "search_vs_final_payload_kg": (
            None if final is None else _finite_or_none(final.search_vs_final_payload_kg)
        ),
        "delta_rad": None if at_final is None else at_final.delta_rad,
        "ltg_a": None if ltg is None else ltg[0],
        "ltg_b_per_s": None if ltg is None else ltg[1],
        "ltg_rung": None if at_final is None else at_final.rung,
        "recorded_m_res_kg": None if recorded is None else _finite_or_none(recorded.m_res_kg),
        "recorded_dv_margin_mps": (
            None if recorded is None else _finite_or_none(recorded.dv_margin_mps)
        ),
        "recorded_figures_from": None if recorded is None else recorded.figures_from,
        "search_failure_kind": record.failure_kind,
        "search_failure_message": record.failure_message,
        "search_record": as_plain(record),
    }


def empty_mass_kg(trace: RunTrace, vehicle: Vehicle) -> float:
    """m_empty [kg] at a planar run's stage-2 end: m_d2 + P, plus the fairing when it is
    still carried (rule never, or the heating rule without a drop), the bookkeeping of
    ``losses.rocket_equation_closure``."""
    s2 = vehicle.stages[1]
    m3 = s2.dry_mass_kg + vehicle.payload_mass_kg
    dropped = (
        vehicle.fairing_rule.trigger == "staging" or trace.first_event(FAIRING_EVENT) is not None
    )
    return m3 if dropped else m3 + vehicle.fairing_mass_kg


def fixed_guidance_metrics(
    trace: RunTrace,
    vehicle: Vehicle,
    status: str,
    *,
    gamma_star_rad: float | None = None,
    delta_rad: float | None = None,
    ltg: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """The SEARCH_METRIC_KEYS of a run flown without a search (figure_of_merit none: the
    fixed gamma* [rad], the delta [rad] solved for it and the fixed LTG pair (a, b
    [1/s]); or a skipped search), with search_status ``status``: no P* (None); the
    residual propellant m_c - m_empty [kg] and the dv margin c2 ln(m_c/m_empty) [m/s] of
    the recorded run itself when it reached the energy cutoff (``empty_mass_kg``), else
    None."""
    names = vehicle.stage_names
    bo2 = trace.burnouts.get(names[1]) if len(names) > 1 else None
    m_res: float | None = None
    dv: float | None = None
    if bo2 is not None and trace.status in ("inserted", "off_target"):
        m_c = float(bo2[1][_M])
        m_e = empty_mass_kg(trace, vehicle)
        m_res, dv = m_c - m_e, vehicle.stages[1].c_mps * math.log(m_c / m_e)
    out: dict[str, Any] = dict.fromkeys(SEARCH_METRIC_KEYS)
    out.update(
        {
            "search_status": status,
            "figure_of_merit": "none",
            "residual_propellant_kg": m_res,
            "dv_margin_mps": dv,
            "residual_propellant_basis": None if m_res is None else RESIDUAL_BASIS_FIXED,
            "residual_propellant_virtual": None if m_res is None else m_res < 0.0,
            "gamma_star_rad": gamma_star_rad,
            "delta_rad": delta_rad,
            "ltg_a": None if ltg is None else ltg[0],
            "ltg_b_per_s": None if ltg is None else ltg[1],
            "recorded_m_res_kg": m_res,
            "recorded_dv_margin_mps": dv,
        }
    )
    return out


CLOSURE_METRIC_KEYS: tuple[str, ...] = (
    "ideal_dv_at_payload_mps",
    "closure_j_vac_mps",
    "preflight_dv_mps",
    "fairing_carry_mps",
    "closure_dv_margin_mps",
    "closure_residual_mps",
)
"""The rocket-equation closure items of ``closure_metrics``, in this order."""


def closure_metrics(closure: ClosureTerms | None) -> dict[str, Any]:
    """The rocket-equation closure items [m/s] (docs/physics.md, "Rocket-equation
    closure (planar)"), CLOSURE_METRIC_KEYS: the ideal delta-v D_id(P), J_vac, the
    pre-flight term c1 ln(m0/m_fs), the fairing-carry term, the closure's dv margin and
    the residual; None without a stage-2 burn."""
    if closure is None:
        return dict.fromkeys(CLOSURE_METRIC_KEYS)
    values = (
        closure.d_id_mps,
        closure.j_vac_mps,
        closure.pre_mps,
        closure.fair_mps,
        closure.dv_margin_mps,
        closure.residual_mps,
    )
    return dict(zip(CLOSURE_METRIC_KEYS, values, strict=True))


def missing_required(metrics: Mapping[str, Any]) -> list[str]:
    """The PLANAR_REQUIRED_METRICS keys a metrics dict lacks or holds as None or a
    non-finite number, in declaration order."""
    missing = []
    for key in PLANAR_REQUIRED_METRICS:
        value = metrics.get(key)
        if value is None or (isinstance(value, float) and not math.isfinite(value)):
            missing.append(key)
    return missing
