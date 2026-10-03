"""Phase and event engine: one ``solve_ivp`` per phase, with the event rules that make
phase boundaries robust (docs/physics.md, "Integrator" and "Event rules").

A run is a sequence of phases joined by events. This module holds the model-agnostic
engine (``integrate_phase``), the specs it consumes (``EventSpec``, ``PhaseSpec``), what
it returns (``PhaseResult``), the integrator settings, the per-state absolute
tolerances (``atol_for``), the event-state lookup (``event_state``), the output sample
grid, and the event factories (the 1-D ones, the model-agnostic altitude events
``ev_ground`` and ``ev_altitude_up``, and the planar ones of the stage-1 guidance:
``ev_radial_apex``, ``ev_radial_turnaround``, ``ev_kick_start``, ``ev_kick_aligned``,
``ev_time``). The planners that string phases
together live in ``phases.vertical`` (1-D) and ``phases.planar`` (2-D) and share the
hold and track prelude in ``phases.prelude``; the run trace they write is
``phases.trace``.

Everything is SI and pure: no I/O, no globals, no printing. Every time in this module
(t, t0, t_end, max_step, the entries of PhaseResult.t) is an absolute run time or a
duration in seconds; the ``_s`` suffix is written only where a name is not obviously a
time. Event functions take (t [s], y) and return a float; the sign-change convention is
scipy's (direction -1 fires when g crosses from positive to negative, +1 the other way,
0 either way).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
from scipy.integrate import OdeSolution, solve_ivp

from launchsim.constants import R_EARTH_M
from launchsim.dynamics import (
    PLANAR_LAYOUT,
    VERTICAL_LAYOUT,
    DynamicsModel,
    StateLayout,
    TrackParams,
    planar_kinematics,
)
from launchsim.vehicle import ThrustSchedule

if TYPE_CHECKING:
    from launchsim.config import IntegratorConfig

EventFn = Callable[[float, np.ndarray], float]
RhsFn = Callable[[float, np.ndarray, Any], np.ndarray]

# Engine tolerances (solver settings, not physics). Documented in docs/physics.md.
ZERO_SPAN_S = 1e-12
"""A phase shorter than this [s] is not solved; the state passes through unchanged."""
EVENT_ZERO_TOL = 1e-12
"""Default ``EventSpec.zero_tol`` for an event with no state tolerance to inherit. The
factories set zero_tol from the atol of the state they read (ATOL_KG for the propellant
event, ATOL_MPS for apex and turnaround, ...) because the integrator does not resolve a
state below its atol, and the residue scipy leaves at an event root (up to one ulp of
the state, 2.9e-11 kg for a 147 t stage) exceeds 1e-12 in absolute terms."""
SUPPORTED_METHODS = ("DOP853", "RK45")
"""solve_ivp methods CLAUDE.md allows (DOP853 by default)."""
DEFAULT_METHOD = "DOP853"
"""The solve_ivp method used when neither the caller nor the config names one."""
SAMPLE_GRID_REL_EPS = 1e-9
"""Relative slack (of the larger of 1 s and the phase's end times) that keeps a sample
grid point that coincides with a phase boundary out of ``sample_grid`` (the boundary is
sampled separately)."""

ATOL_M = 1e-6
"""Absolute tolerance for length states [m]."""
ATOL_MPS = 1e-9
"""Absolute tolerance for velocity and loss-quadrature states [m/s]."""
ATOL_KG = 1e-6
"""Absolute tolerance for mass states [kg]."""
ATOL_J = 1e-3
"""Absolute tolerance for energy quadrature states [J] (track phase)."""
ATOL_RAD = ATOL_M / R_EARTH_M
"""Absolute tolerance for angle states [rad]: the angle that one length tolerance
(ATOL_M) subtends at the Earth's surface, about 1.57e-13 rad (the planar downrange
angle theta, Phase 2)."""
APEX_FOLD_ACCEL_MPS2 = 1.0
"""The smallest downward acceleration [m/s^2] past an apex for which the fold of
``ev_altitude_up`` keeps its function rising (gravity alone is about 9.8 m/s^2; drag on a
vehicle falling from an apex for one step relieves it by millimetres per second
squared): an event solver setting, not physics."""
APEX_FOLD_GAIN_S2PM = 1.0 / (2.0 * APEX_FOLD_ACCEL_MPS2)
"""The fold gain k = 1 / (2 a_min) [s^2/m] of ``ev_altitude_up``: past an apex it adds
k w^2 to the altitude, and w^2 >= 2 a_min (apex - altitude) there, so the folded value
never falls below apex - z."""
_ATOL_BY_SUFFIX: dict[str, float] = {
    "_m": ATOL_M,
    "_mps": ATOL_MPS,
    "_kg": ATOL_KG,
    "_J": ATOL_J,
    "_rad": ATOL_RAD,
}


# --------------------------------------------------------------------------- settings


@dataclass(frozen=True)
class IntegratorSettings:
    """solve_ivp settings for a run; mirrors ``config.IntegratorConfig``.

    method: scipy method name; rtol: relative tolerance; first_step_s: first step [s]
    (capped at half the phase span); ramp_steps, lag_steps_per_tau, push_steps: how
    finely the planner caps max_step during a thrust ramp (t_ramp / ramp_steps), a lag
    (tau / lag_steps_per_tau) and a track push (t_push / push_steps);
    planar_max_step_s: the step cap [s] of every planar flight phase (> 0; math.inf
    for none), combined with the ramp or lag cap by min, read only by the planar
    planner (the HOLD, the track and every 1-D phase ignore it); t_max_s: the guard
    [s] on open-ended phases; sample_dt_s: the output resampling interval [s] (the
    caller's job, from the dense output); dense_output: whether solve_ivp builds the
    dense output (``PhaseResult.dense``; off only for search evaluations, which read
    event states from ``PhaseResult.y_events`` through ``event_state``; a recorded run
    needs it on: ``VerticalPlanner`` refuses it off, and ``RunTrace.require_dense``
    is the check for the reporting path); atol_scale: a
    factor (> 0) on every per-state absolute tolerance of a phase (1.0 leaves the
    ``atol_for`` values untouched; a search uses a looser value). dense_output and
    atol_scale are code-level settings with no YAML key.
    """

    method: str = DEFAULT_METHOD
    rtol: float = 1e-10
    first_step_s: float = 1e-3
    ramp_steps: int = 10
    lag_steps_per_tau: int = 4
    push_steps: int = 50
    planar_max_step_s: float = 2.0
    t_max_s: float = 3600.0
    sample_dt_s: float = 0.05
    dense_output: bool = True
    atol_scale: float = 1.0

    def __post_init__(self) -> None:
        if self.method not in SUPPORTED_METHODS:
            raise ValueError(f"method must be one of {SUPPORTED_METHODS}, got {self.method!r}")
        if self.rtol <= 0.0 or self.first_step_s <= 0.0:
            raise ValueError("rtol and first_step_s must be > 0")
        if min(self.ramp_steps, self.lag_steps_per_tau, self.push_steps) < 1:
            raise ValueError("step counts must be >= 1")
        if self.t_max_s <= 0.0 or self.sample_dt_s <= 0.0:
            raise ValueError("t_max_s and sample_dt_s must be > 0")
        if not self.planar_max_step_s > 0.0:
            raise ValueError(
                f"planar_max_step_s must be > 0 (math.inf for no cap), got "
                f"{self.planar_max_step_s!r}"
            )
        if not math.isfinite(self.atol_scale) or self.atol_scale <= 0.0:
            raise ValueError(f"atol_scale must be finite and > 0, got {self.atol_scale!r}")

    @classmethod
    def from_config(cls, cfg: IntegratorConfig) -> IntegratorSettings:
        """Settings from a validated ``IntegratorConfig``. The method is the config's
        ``method`` when the config model carries that field, else DEFAULT_METHOD;
        dense_output and atol_scale keep their defaults (no YAML key)."""
        method = getattr(cfg, "method", None)
        return cls(
            method=DEFAULT_METHOD if method is None else method,
            rtol=cfg.rtol,
            first_step_s=cfg.first_step_s,
            ramp_steps=cfg.ramp_steps,
            lag_steps_per_tau=cfg.lag_steps_per_tau,
            push_steps=cfg.push_steps,
            planar_max_step_s=cfg.planar_max_step_s,
            t_max_s=cfg.t_max_s,
            sample_dt_s=cfg.sample_dt_s,
        )


# ------------------------------------------------------------------------------ specs


@dataclass(frozen=True)
class EventSpec:
    """One event of a phase.

    name: label used in ``PhaseResult.ended_by`` and the event log; fn(t, y) -> float,
    the event function [any unit]; terminal: whether firing ends the phase; direction:
    -1 (fires on a positive-to-negative crossing), +1 (negative-to-positive) or 0 (either);
    zero_tol: |fn| at or below this [same unit as fn] counts as "on the event surface"
    in the pre-solve rules of ``integrate_phase`` (the factories use the atol of the
    state the event reads; the default is EVENT_ZERO_TOL).
    """

    name: str
    fn: EventFn
    terminal: bool
    direction: int
    zero_tol: float = EVENT_ZERO_TOL

    def __post_init__(self) -> None:
        if self.direction not in (-1, 0, 1):
            raise ValueError("direction must be -1, 0 or +1")
        if self.zero_tol < 0.0:
            raise ValueError("zero_tol must be >= 0")


@dataclass(frozen=True, eq=False)
class PhaseSpec:
    """Everything ``integrate_phase`` needs for one phase.

    kind: phase label (HOLD, ASSIST, COAST, BURN, FALL, ...); stage_index: the stage in
    charge; t0 and t_end: absolute run times [s], t_end None for an open-ended phase
    (guarded by IntegratorSettings.t_max_s); rhs(t, y, params) -> dy/dt; params: the
    object handed to rhs; events: the events that can occur in this phase (only those);
    atol: per-state absolute tolerances (``atol_for``); max_step: step cap [s]
    (math.inf for none); sigma: the velocity sign the phase assumes (+1 rising,
    -1 falling; recorded for the loss identity). When params carries a ``v_sign``
    (VerticalParams does) it must equal sigma: the RHS reads params.v_sign, so a
    mismatch would silently flip the sign of J_grav, J_alt and J_steer for the phase.
    """

    kind: str
    stage_index: int
    t0: float
    t_end: float | None
    rhs: RhsFn
    params: Any
    events: tuple[EventSpec, ...]
    atol: np.ndarray
    max_step: float = math.inf
    sigma: int = 1

    def __post_init__(self) -> None:
        if self.t_end is not None and self.t_end < self.t0:
            raise ValueError(f"phase {self.kind}: t_end {self.t_end} < t0 {self.t0}")
        if self.max_step <= 0.0:
            raise ValueError("max_step must be > 0 (math.inf for no cap)")
        if self.sigma not in (1, -1):
            raise ValueError("sigma must be +1 or -1")
        v_sign = getattr(self.params, "v_sign", None)
        if v_sign is not None and v_sign != self.sigma:
            raise ValueError(
                f"phase {self.kind}: sigma {self.sigma} != params.v_sign {v_sign}; the loss "
                "quadratures would carry the wrong sign"
            )
        names = [e.name for e in self.events]
        if len(set(names)) != len(names):
            raise ValueError(f"phase {self.kind}: event names must be unique, got {names}")


@dataclass(frozen=True, eq=False)
class PhaseResult:
    """What one phase produced.

    spec: the PhaseSpec; t: the integrator's own sample times [s] ending at the event
    or t_end (a single entry for a pass-through); y: states, shape (n_states, len(t));
    dense: the OdeSolution for resampling, None for a pass-through or when the settings
    turn dense output off; ended_by: the name of the terminal event, "t_end", or
    "zero_span"; t_end and y_end: the final time [s] and state; notes: what the
    pre-solve event rules did; event_times: every event occurrence (name, t [s])
    including non-terminal ones, in time order; nfev: the number of right-hand-side
    evaluations solve_ivp reports for the phase (0 for a pass-through or a closed-form
    phase; the engine's two Heun evaluations for the pre-solve rules are not counted);
    y_events: per event name listed in spec.events, the state at each of its
    occurrences, shape (n_occurrences, n_states), in the order of that name's entries
    in event_times (scipy's ``sol.y_events``; the state at t0 for an event already
    past at t0; a listed event that never fired maps to shape (0, n_states), for an
    integrated phase and a pass-through alike). Read one with ``event_state``.
    dense_off: True only for a phase integrated with ``IntegratorSettings.dense_output``
    False: its dense is None although it spans time, so its interior is known only at
    the solver's own steps and events (search evaluations; the reporting pipeline must
    refuse it, see ``RunTrace.require_dense``). False for every pass-through and
    closed-form phase, whose dense is None because there is nothing to resample.
    """

    spec: PhaseSpec
    t: np.ndarray
    y: np.ndarray
    dense: OdeSolution | None
    ended_by: str
    t_end: float
    y_end: np.ndarray
    notes: tuple[str, ...] = ()
    event_times: tuple[tuple[str, float], ...] = field(default=())
    nfev: int = 0
    y_events: Mapping[str, np.ndarray] = field(default_factory=dict)
    dense_off: bool = False

    @property
    def span_s(self) -> float:
        """Duration of the phase [s]."""
        return self.t_end - self.spec.t0


# ----------------------------------------------------------------------- tolerances


def atol_for(state_names: tuple[str, ...]) -> np.ndarray:
    """Per-state absolute tolerance vector from the unit suffix of each state name.

    Inputs: state names ending in ``_m`` (1e-6 m), ``_mps`` (1e-9 m/s, also the loss
    quadratures), ``_kg`` (1e-6 kg), ``_J`` (1e-3 J) or ``_rad`` (ATOL_RAD, 1e-6 m /
    R_E = 1.57e-13 rad). Output: array of len(names). An unknown suffix raises
    ValueError so a new state cannot silently get a tolerance.
    """
    out = np.empty(len(state_names))
    for i, name in enumerate(state_names):
        for suffix, tol in _ATOL_BY_SUFFIX.items():
            if name.endswith(suffix):
                out[i] = tol
                break
        else:
            raise ValueError(f"state {name!r} has no unit suffix in {tuple(_ATOL_BY_SUFFIX)}")
    return out


# --------------------------------------------------------------------------- engine


def _already_past(direction: int, g0: float) -> bool:
    """Whether g0 lies on the side of zero an event of this direction lands on after
    firing: negative for direction -1, positive for +1, negative for 0 (convention)."""
    if direction == 0:
        return g0 < 0.0
    return direction * g0 > 0.0


def _would_fire(direction: int, g_pred: float) -> bool:
    """scipy's sign-change test with g(t0) = 0: fires when the next value is on or past
    the firing side, or for any next value when direction is 0."""
    if direction == 0:
        return True
    return direction * g_pred >= 0.0


def _guard_value(direction: int, g_pred: float) -> float:
    """The constant a disarmed event reports while |g| <= zero_tol: a value already on
    its firing side, so the transition to the real values cannot count as a crossing."""
    if direction != 0:
        return float(direction)
    return math.copysign(1.0, g_pred) if g_pred != 0.0 else 1.0


def _event_callable(spec: EventSpec, guard_value: float | None) -> EventFn:
    """scipy event callable with terminal/direction attributes.

    With a guard value the event is disarmed: it reports guard_value whenever
    |g| <= spec.zero_tol, so neither the stale zero at t0 nor a value that never leaves
    the tolerance band can register as a crossing (scipy fires on g = g_new = 0). A
    genuine later crossing is still found, at the edge of the band, i.e. within the
    state's atol.
    """
    if guard_value is None:

        def fn(t: float, y: np.ndarray) -> float:
            return spec.fn(t, y)

    else:
        tol = spec.zero_tol

        def fn(t: float, y: np.ndarray) -> float:
            g = spec.fn(t, y)
            return guard_value if abs(g) <= tol else g

    fn.terminal = spec.terminal  # type: ignore[attr-defined]
    fn.direction = spec.direction  # type: ignore[attr-defined]
    return fn


def _predict_state(spec: PhaseSpec, t0: float, y0: np.ndarray, h: float) -> np.ndarray:
    """State after one explicit step of length h [s] (Heun, second order), used only to
    judge which side an event exactly at zero will move to. Second order matters: a
    state with zero first derivative (altitude at apex) would be predicted unchanged by
    an Euler step and the guard would land on the wrong side."""
    f0 = np.asarray(spec.rhs(t0, y0, spec.params), dtype=float)
    f1 = np.asarray(spec.rhs(t0 + h, y0 + h * f0, spec.params), dtype=float)
    return y0 + 0.5 * h * (f0 + f1)


def _pass_through(
    spec: PhaseSpec,
    y0: np.ndarray,
    ended_by: str,
    notes: list[str],
    event_times: tuple[tuple[str, float], ...] = (),
) -> PhaseResult:
    """A zero-length result: the state at t0 handed straight back. Every event in
    event_times occurred at t0, so its y_events entry is the state at t0; every other
    event of spec.events maps to an empty (0, n_states) array, as in an integrated
    phase."""
    y_events = {ev.name: np.empty((0, y0.size)) for ev in spec.events}
    y_events.update({name: y0.reshape(1, -1).copy() for name, _ in event_times})
    return PhaseResult(
        spec=spec,
        t=np.array([spec.t0]),
        y=y0.reshape(-1, 1).copy(),
        dense=None,
        ended_by=ended_by,
        t_end=spec.t0,
        y_end=y0.copy(),
        notes=tuple(notes),
        event_times=event_times,
        y_events=y_events,
    )


def integrate_phase(spec: PhaseSpec, y0: np.ndarray, settings: IntegratorSettings) -> PhaseResult:
    """Integrate one phase from y0 at spec.t0 until a terminal event, t_end or failure.

    Inputs: spec (rhs, params, events, atol, max_step, times [s]); y0, the state at t0;
    settings. Output: a PhaseResult with the integrator's own sample points (the event
    point last), the dense output (unless settings.dense_output is False), the state at
    every event occurrence (``y_events``) and the solver's RHS count (``nfev``);
    resampling at sample_dt_s is the caller's job.

    Rules (docs/physics.md, "Event rules"):
    1. span = t_end - t0 (t_end = t0 + t_max_s when open-ended); span <= 1e-12 s returns
       a pass-through with ended_by "zero_span".
    2. first_step = min(first_step_s, span / 2): scipy raises when the first step exceeds
       the span.
    3. Before solving, every event is evaluated at (t0, y0). A terminal event with
       |g(t0)| > zero_tol already on its fired side (direction * g > 0; g < 0 for
       direction 0) ends the phase at t0 with ended_by = its name, event_times
       ((name, t0),) and a note. An event with |g(t0)| <= zero_tol that would fire on
       the first step (a second-order Heun prediction of g at t0 + first_step, judged
       by scipy's sign-change test) is disarmed: it reports a constant on its firing
       side whenever |g| <= zero_tol, so neither the stale zero at t0 nor a value that
       never leaves the band can count as a crossing. Without this guard scipy fires a
       direction-matched exact zero at t0. The guard is a backstop: it cannot tell a
       stale zero (the apex that ended the previous phase) from a phase that starts on
       the event surface moving into it (impact at z = 0 while sinking, apex at a
       TWR < 1 pad start), so the planner must not list the event that ended the
       previous phase, must start pad burns after the liftoff root, and must surface
       every "disarmed" note as a run flag.
    4. solve_ivp(method, rtol, atol, dense_output, max_step, first_step, events), with
       atol = spec.atol times settings.atol_scale (spec.atol itself when the scale is
       1.0).
    5. An open-ended phase that reaches t_max_s without a terminal event raises
       RuntimeError naming the phase kind; an integrator failure raises RuntimeError.
    6. ended_by is the terminal event that fired, else "t_end". A terminal root that
       coincides with t_end is reported either as the event (scipy status 1, with an
       event_times entry) or as "t_end" (status 0, no entry), depending on the sign of
       the ~1e-13 residue at the last sample: scipy sets status 0 on reaching t_bound
       and then overrides it with 1 if the event test fires at that final sample. Either
       report is consistent, so ended_by, not event_times, is authoritative for how a
       phase ended.
    """
    y0 = np.asarray(y0, dtype=float)
    if y0.ndim != 1 or y0.shape != spec.atol.shape:
        raise ValueError(
            f"phase {spec.kind}: y0 has shape {y0.shape}, atol has shape {spec.atol.shape}"
        )
    t0 = spec.t0
    open_ended = spec.t_end is None
    t_end = t0 + settings.t_max_s if spec.t_end is None else spec.t_end
    span = t_end - t0
    notes: list[str] = []
    if span <= ZERO_SPAN_S:
        return _pass_through(spec, y0, "zero_span", notes)
    first_step = min(settings.first_step_s, 0.5 * span)

    callables: list[EventFn] = []
    y_pred: np.ndarray | None = None
    for ev in spec.events:
        g0 = float(ev.fn(t0, y0))
        if abs(g0) <= ev.zero_tol:
            if y_pred is None:
                y_pred = _predict_state(spec, t0, y0, first_step)
            g_pred = float(ev.fn(t0 + first_step, y_pred))
            if _would_fire(ev.direction, g_pred):
                callables.append(_event_callable(ev, _guard_value(ev.direction, g_pred)))
                notes.append(
                    f"event {ev.name} is at zero at t0 = {t0:.6g} s (g = {g0:.3g}, tolerance "
                    f"{ev.zero_tol:.3g}) and would fire on the first step; disarmed while "
                    "|g| stays within the tolerance (a stale zero from the previous phase "
                    "boundary, or a phase starting on the event surface moving into it)"
                )
                continue
        elif ev.terminal and _already_past(ev.direction, g0):
            notes.append(
                f"terminal event {ev.name} already past at t0 = {t0:.6g} s (g = {g0:.6g}); "
                "phase ended at t0"
            )
            return _pass_through(spec, y0, ev.name, notes, ((ev.name, t0),))
        callables.append(_event_callable(ev, None))

    atol = spec.atol if settings.atol_scale == 1.0 else spec.atol * settings.atol_scale
    sol = solve_ivp(
        lambda t, y: spec.rhs(t, y, spec.params),
        (t0, t_end),
        y0,
        method=settings.method,
        rtol=settings.rtol,
        atol=atol,
        dense_output=settings.dense_output,
        max_step=spec.max_step,
        first_step=first_step,
        events=callables or None,
    )
    if sol.status < 0:
        raise RuntimeError(f"phase {spec.kind}: integrator failed: {sol.message}")

    event_times = sorted(
        (
            (ev.name, float(te))
            for ev, tes in zip(spec.events, sol.t_events or (), strict=True)
            for te in tes
        ),
        key=lambda item: item[1],
    )
    y_events = {
        ev.name: np.asarray(ys, dtype=float).reshape(-1, y0.size)
        for ev, ys in zip(spec.events, sol.y_events or (), strict=True)
    }
    t_last = float(sol.t[-1])
    if sol.status == 1:
        ended_by = _terminal_event_at(spec, sol.t_events, t_last)
    elif open_ended:
        raise RuntimeError(
            f"phase {spec.kind} reached t_max = {settings.t_max_s:.6g} s after t0 = "
            f"{t0:.6g} s without a terminal event"
        )
    else:
        ended_by = "t_end"
    return PhaseResult(
        spec=spec,
        t=sol.t,
        y=sol.y,
        dense=sol.sol,
        ended_by=ended_by,
        t_end=t_last,
        y_end=sol.y[:, -1].copy(),
        notes=tuple(notes),
        event_times=tuple(event_times),
        nfev=int(sol.nfev),
        y_events=y_events,
        dense_off=not settings.dense_output,
    )


def _terminal_event_at(spec: PhaseSpec, t_events: list[np.ndarray], t_last: float) -> str:
    """Name of the terminal event whose last root is the final sample time.

    Exact equality is correct: scipy copies the terminal root verbatim into sol.t[-1].
    """
    for ev, tes in zip(spec.events, t_events, strict=True):
        if ev.terminal and len(tes) and float(tes[-1]) == t_last:
            return ev.name
    raise RuntimeError(f"phase {spec.kind}: solver stopped on an event that cannot be identified")


def event_state(res: PhaseResult, name: str, te: float) -> np.ndarray:
    """The state at one occurrence of an event, from ``PhaseResult.y_events``.

    Inputs: res, a PhaseResult; name, the event name; te, the occurrence's time [s]
    exactly as it appears in res.event_times. Output: a copy of the state vector (the
    phase's layout) at that root, as scipy's event locator evaluated it on the step's
    own interpolant. It needs no dense output, so it is the lookup for phases run with
    ``IntegratorSettings.dense_output = False``. Raises ValueError when the phase has
    no such occurrence. (The 1-D planner keeps its own lookup: a terminal root is
    y_end, anything else is read from the dense output.)
    """
    times = [t for n, t in res.event_times if n == name]
    states = res.y_events.get(name)
    if states is None or len(states) != len(times):
        raise ValueError(
            f"phase {res.spec.kind}: no event states for {name!r} "
            f"({len(times)} occurrence(s) logged)"
        )
    for i, t in enumerate(times):
        if t == te:
            return np.array(states[i], dtype=float, copy=True)
    raise ValueError(f"phase {res.spec.kind}: event {name!r} did not occur at t = {te!r} s")


def is_lit(schedule: ThrustSchedule, t: float) -> bool:
    """Whether a stage's engine is lit at time t [s] on the absolute clock: never for a
    failed ignition (``schedule.fails``), else once t has reached the ignition time
    within ZERO_SPAN_S (a sub-phase starting at the ignition kink counts as lit)."""
    return not schedule.fails and t >= schedule.t_ign_abs_s - ZERO_SPAN_S


def sample_grid(t0: float, t1: float, dt: float) -> np.ndarray:
    """Multiples of dt [s] strictly inside (t0, t1) [s], on the absolute clock (k dt for
    integer k), so every phase samples the same grid; a point within
    SAMPLE_GRID_REL_EPS (relative) of an end is left to the boundary sample."""
    eps = SAMPLE_GRID_REL_EPS * max(1.0, abs(t0), abs(t1))
    k0 = math.ceil((t0 + eps) / dt)
    k1 = math.floor((t1 - eps) / dt)
    return np.arange(k0, k1 + 1) * dt if k1 >= k0 else np.empty(0)


# ------------------------------------------------------------------- event factories


def ev_propellant(m_dry_stack_kg: float, layout: StateLayout = VERTICAL_LAYOUT) -> EventSpec:
    """Burnout: m - m_dry_stack crosses zero downward (terminal).

    Inputs: the stack mass at burnout [kg] (vehicle.stack_dry_mass_kg); the state layout
    (needs ``m_kg``). The schedule itself is not capped by the propellant on board, so
    this event is what ends every burn. zero_tol = ATOL_KG.
    """
    i_m = layout.index("m_kg")

    def fn(t: float, y: np.ndarray) -> float:
        return y[i_m] - m_dry_stack_kg

    return EventSpec("propellant", fn, terminal=True, direction=-1, zero_tol=ATOL_KG)


def ev_apex(layout: StateLayout = VERTICAL_LAYOUT) -> EventSpec:
    """Apex: the signed vertical velocity v [m/s] crosses zero downward (terminal).

    Frame: +z up; v > 0 rising. Ends a rising phase so the next one runs with sigma = -1.
    zero_tol = ATOL_MPS.
    """
    i_v = layout.index("v_mps")

    def fn(t: float, y: np.ndarray) -> float:
        return y[i_v]

    return EventSpec("apex", fn, terminal=True, direction=-1, zero_tol=ATOL_MPS)


def ev_turnaround(layout: StateLayout = VERTICAL_LAYOUT) -> EventSpec:
    """Turnaround: v [m/s] crosses zero upward while thrusting during a fall (terminal).

    Frame: +z up. Ends a falling phase so the next one runs with sigma = +1.
    zero_tol = ATOL_MPS.
    """
    i_v = layout.index("v_mps")

    def fn(t: float, y: np.ndarray) -> float:
        return y[i_v]

    return EventSpec("turnaround", fn, terminal=True, direction=+1, zero_tol=ATOL_MPS)


def ev_impact(z_ground_m: float, layout: StateLayout = VERTICAL_LAYOUT) -> EventSpec:
    """Impact: z - z_ground crosses zero downward (terminal).

    Inputs: the ground altitude [m] in the +z-up datum frame (0 for the silo mouth or
    pad; -L for the bottom of a buried silo). zero_tol = ATOL_M.
    """
    i_z = layout.index("z_m")

    def fn(t: float, y: np.ndarray) -> float:
        return y[i_z] - z_ground_m

    return EventSpec("impact", fn, terminal=True, direction=-1, zero_tol=ATOL_M)


def ev_liftoff(
    schedule: ThrustSchedule,
    g_eff_mps2: float,
    p_amb_pa: float = 0.0,
    layout: StateLayout = VERTICAL_LAYOUT,
) -> EventSpec:
    """Liftoff from a hold-down: T(t) - m(t) g_eff crosses zero upward (terminal).

    Inputs: the stage's ThrustSchedule on the absolute clock; the effective gravity at
    the pad [m/s^2]; p_amb_pa, the ambient pressure at the pad [Pa] so that T is the
    delivered thrust ``schedule.thrust_N(t, p_amb)`` = max(0, T_vac - p_amb A_e) (0 in
    Phase 1, where vacuum thrust from sea level is a stated assumption; Phase 2 must
    pass the pad pressure, or the pad would lift off early by the p_amb A_e deficit,
    ~7% of thrust for the F9 stage, flattering the pad baseline); the layout (needs
    ``m_kg``, the mass taken from the state). Used when a pad run's thrust is still
    below the weight when the hold-down would release. zero_tol = ATOL_KG * g_eff [N],
    the weight of one mass tolerance.
    """
    if p_amb_pa < 0.0:
        raise ValueError("p_amb_pa must be >= 0")
    i_m = layout.index("m_kg")

    def fn(t: float, y: np.ndarray) -> float:
        return schedule.thrust_N(t, p_amb_pa) - y[i_m] * g_eff_mps2

    return EventSpec("liftoff", fn, terminal=True, direction=+1, zero_tol=ATOL_KG * g_eff_mps2)


def ev_track_end(length_m: float, layout: StateLayout) -> EventSpec:
    """Track end: s - L crosses zero upward (terminal); the vehicle releases there.

    Inputs: the track length L [m]; the track state layout (needs ``s_m``).
    zero_tol = ATOL_M.
    """
    i_s = layout.index("s_m")

    def fn(t: float, y: np.ndarray) -> float:
        return y[i_s] - length_m

    return EventSpec("track_end", fn, terminal=True, direction=+1, zero_tol=ATOL_M)


def ev_drive_limit(params: TrackParams) -> EventSpec:
    """Drive limit: the drive force F_drive(t, y) [N] crosses zero downward (terminal).

    Inputs: the TrackParams of the phase (the force comes from its assist model with
    the delivered thrust at t). Under a prescribed acceleration a negative drive force
    means the drive would have to brake the engine; unless the model allows it the run
    stops there with status ``drive_limit``. A phase that starts with F_drive already
    negative ends at t0 by the engine's already-past rule. zero_tol = ATOL_KG g_eff
    [N], the weight of one mass tolerance.
    """

    def fn(t: float, y: np.ndarray) -> float:
        return params.forces(t, y).drive_force_N

    return EventSpec(
        "drive_limit", fn, terminal=True, direction=-1, zero_tol=ATOL_KG * params.g_eff_mps2
    )


# ------------------------------------------------------------ planar event factories


def ev_ground(model: DynamicsModel, z_ground_m: float) -> EventSpec:
    """Impact on the ground: model.altitude(y) - z_ground crosses zero downward (terminal).

    Inputs: the dynamics model whose ``altitude`` reads the state (``PlanarDynamics2D``:
    h = r - r_datum [m], geometric, spherical Earth); z_ground_m, the ground altitude
    [m] above the datum (0 for the pad and the silo mouth). The event is called
    ``impact`` (the 1-D name, status ``impact``). zero_tol = ATOL_M, which is below the
    ~rtol R_E to which a planar r is resolved ("Integrator"): the root is located to
    the integrator's resolution of r, not to ATOL_M. Listed in every planar flight
    phase that can reach the ground: falling coasts and falling lit rises, the kick
    and the gravity turn (which can dive). A rising coast or rise does not list it: it
    is split at the radial apex before it could come down. That also keeps the event
    out of the pad's first rise, which starts at the liftoff root with v_r = 0 and
    dv_r/dt = 0: there the engine's second-order predictor sees the altitude stay at
    zero, so it would disarm the event with a run flag (harmless, as the guard re-arms
    above ATOL_M, but a spurious flag). A kick starting on the ground at a silo release
    (v_r > 0) is predicted to rise, so the event starts armed there.
    """

    def fn(t: float, y: np.ndarray) -> float:
        return float(model.altitude(y)) - z_ground_m

    return EventSpec("impact", fn, terminal=True, direction=-1, zero_tol=ATOL_M)


def _altitude_rate_index(layout: StateLayout) -> int:
    """Index of the signed altitude rate in a flight layout: v_r [m/s] (planar, dr/dt)
    or v [m/s] (1-D, dz/dt); ValueError for a layout with neither."""
    for name in ("v_r_mps", "v_mps"):
        if name in layout.names:
            return layout.index(name)
    raise ValueError(f"layout {layout.names} has no altitude rate (v_r_mps or v_mps)")


def ev_altitude_up(model: DynamicsModel, z_m: float, name: str) -> EventSpec:
    """An altitude reached on the way up (terminal; the mirror of ``ev_ground``):
    g = model.altitude(y) - z_m + APEX_FOLD_GAIN_S2PM min(w, 0)^2 crosses zero upward,
    w the signed altitude rate (v_r on the planar model, v on the 1-D one).

    Inputs: the dynamics model whose ``altitude`` reads the state (``VerticalDynamics1D``:
    z [m]; ``PlanarDynamics2D``: h = r - r_datum [m], geometric) and whose ``layout``
    holds the rate; z_m, the altitude [m] above the datum (finite); name, the event's
    label (``prelude.IGNITION_HEIGHT_EVENT`` for the ramp start of ``height_method:
    event``: the track exit's altitude plus the requested height). Listed only in rising
    unpowered sub-phases, which end at the apex (w = 0), so inside the phase g is the
    altitude minus z_m exactly and its root is the altitude crossing. The fold term
    (zero while w >= 0, continuous at the apex) is for the step that overshoots the
    apex before the phase is cut there: scipy tests a sign change only at step ends,
    and a crossing just below the apex has the altitude back below z_m at the end of
    such a step. With the fold, g keeps rising past the apex (dg/dt = w (1 - 2 k |a|) >
    0 for a downward acceleration |a| > 1 / (2 k), and g(t_end) >= apex - z_m), so the
    crossing is found; with the apex below z_m any root lies after the apex root, which
    ends the phase first (scipy drops events later than a terminal one). A state already
    within zero_tol below z_m or above it is the planner's to decide (it lights at once)
    and is never handed to a phase listing the event (the engine would end the phase at
    t0 by its already-past rule). zero_tol = ATOL_M; as for ``ev_ground``, a planar root
    is located to the integrator's resolution of r (~rtol R_E), not to ATOL_M.
    """
    if not math.isfinite(z_m):
        raise ValueError(f"z_m must be finite, got {z_m!r}")
    i_w = _altitude_rate_index(model.layout)
    k = APEX_FOLD_GAIN_S2PM

    def fn(t: float, y: np.ndarray) -> float:
        w = min(float(y[i_w]), 0.0)
        return float(model.altitude(y)) - z_m + k * w * w

    return EventSpec(name, fn, terminal=True, direction=+1, zero_tol=ATOL_M)


def ev_radial_apex(layout: StateLayout = PLANAR_LAYOUT) -> EventSpec:
    """Radial apex: v_r [m/s] crosses zero downward (terminal; a phase split).

    Frame: planar, v_r the inertial (and Earth-relative) radial velocity. Ends a rising
    planar phase so the next one runs with the falling event list (ground listed, apex
    not), which keeps w/V = sin gamma_rel from flipping sign inside a step of a coast
    ("2-D loss identity"). zero_tol = ATOL_MPS.
    """
    i_w = layout.index("v_r_mps")

    def fn(t: float, y: np.ndarray) -> float:
        return float(y[i_w])

    return EventSpec("apex", fn, terminal=True, direction=-1, zero_tol=ATOL_MPS)


def ev_radial_turnaround(layout: StateLayout = PLANAR_LAYOUT) -> EventSpec:
    """Radial turnaround: v_r [m/s] crosses zero upward while thrusting during a fall
    (terminal; a phase split, the mirror of ``ev_radial_apex``). zero_tol = ATOL_MPS."""
    i_w = layout.index("v_r_mps")

    def fn(t: float, y: np.ndarray) -> float:
        return float(y[i_w])

    return EventSpec("turnaround", fn, terminal=True, direction=+1, zero_tol=ATOL_MPS)


def ev_kick_start(v_kick_mps: float, omega_p_rads: float) -> EventSpec:
    """Kick trigger: g = min(V - v_k, w) crosses zero upward (terminal).

    Inputs: the trigger speed v_kick_mps [m/s] (> 0, finite); the planar rotation rate
    [rad/s]. The state is in ``PLANAR_LAYOUT``: w = v_r and V = |v_rel| =
    hypot(w, v_theta - omega_p r) [m/s] (Earth-relative). g > 0 exactly when the
    vehicle is faster than v_k relative to the air AND rising, so a falling vehicle
    (w < 0) never kicks, whatever its speed. Listed only in lit VERTICAL_RISE
    phases. The planner evaluates g itself at the first lit instant and starts the
    kick there when g > zero_tol (a release or an ignition already faster than v_k
    while rising), so no zero-length rise and no engine note is involved; a rise
    handed a state already past the trigger would still end at t0 by the engine's
    already-past rule. zero_tol = ATOL_MPS.
    """
    if not (math.isfinite(v_kick_mps) and v_kick_mps > 0.0):
        raise ValueError(f"v_kick_mps must be finite and > 0, got {v_kick_mps!r}")

    def fn(t: float, y: np.ndarray) -> float:
        kin = planar_kinematics(y, omega_p_rads)
        return min(kin.V_mps - v_kick_mps, kin.w_mps)

    return EventSpec("kick_start", fn, terminal=True, direction=+1, zero_tol=ATOL_MPS)


def ev_kick_aligned(delta_rad: float, omega_p_rads: float) -> EventSpec:
    """Kick end: g = (u cos delta - w sin delta)/V = sin(beta_rel - delta) crosses zero
    upward (terminal; the event is called ``kick_end``).

    Inputs: the kick angle delta_rad [rad] (the thrust's tilt from local vertical during
    the kick); the planar rotation rate [rad/s]; the state is in ``PLANAR_LAYOUT``.
    beta_rel = pi/2 - gamma_rel is the Earth-relative velocity's angle from local
    vertical, so the event fires when the velocity has turned to the thrust
    direction and the gravity turn (thrust along v_rel) can take over with a
    continuous thrust direction. Below V_REL_EPS_MPS the kinematic fallback gives
    g = -sin delta. g is dimensionless; zero_tol = EVENT_ZERO_TOL.
    """
    c, s = math.cos(delta_rad), math.sin(delta_rad)

    def fn(t: float, y: np.ndarray) -> float:
        kin = planar_kinematics(y, omega_p_rads)
        return kin.cos_g * c - kin.sin_g * s

    return EventSpec("kick_end", fn, terminal=True, direction=+1, zero_tol=EVENT_ZERO_TOL)


def ev_time(t_event_s: float, name: str) -> EventSpec:
    """A terminal event at the absolute time t_event_s [s]: g = t - t_event crosses zero
    upward. Used for the kick timeout (``kick_timeout``, t_kick + kick_max) and the kick
    deadline (``kick_deadline``, t_ign + deadline). A phase starting after t_event ends
    at t0 by the already-past rule. zero_tol = EVENT_ZERO_TOL [s]."""
    if not math.isfinite(t_event_s):
        raise ValueError(f"t_event_s must be finite, got {t_event_s!r}")

    def fn(t: float, y: np.ndarray) -> float:
        return t - t_event_s

    return EventSpec(name, fn, terminal=True, direction=+1, zero_tol=EVENT_ZERO_TOL)
