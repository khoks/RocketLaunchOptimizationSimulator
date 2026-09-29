"""Phase and event engine: one ``solve_ivp`` per phase, with the event rules that make
phase boundaries robust (docs/physics.md, "Integrator" and "Event rules").

A run is a sequence of phases joined by events. This module holds the engine
(``integrate_phase``), the specs it consumes, the integrator settings, the event
factories, the release and staging maps, and the 1-D planner (``VerticalPlanner``) that
strings HOLD, COAST, BURN and FALL phases together for a run (docs/physics.md, "Phases
and events"). The track (ASSIST) phase and its release into the ascent arrive with the
assist models; the planner exposes ``TraceBuilder`` and ``ascend`` so they can prepend
their phases and hand over the released state.

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
    VERTICAL_LAYOUT,
    VERTICAL_STATE_NAMES,
    Gravity,
    StateLayout,
    TrackParams,
    VerticalParams,
    rhs_track,
    rhs_vertical,
    track_state_names,
    track_to_vertical,
)
from launchsim.vehicle import Startup, ThrustSchedule, Vehicle, propellant_burned_kg

if TYPE_CHECKING:
    from launchsim.assist.base import AssistModel, TrackGeometry
    from launchsim.config import IgnitionConfig, IntegratorConfig

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
SAMPLE_GRID_REL_EPS = 1e-9
"""Relative slack (of the larger of 1 s and the phase's end times) that keeps a sample
grid point that coincides with a phase boundary out of ``sample_grid`` (the boundary is
sampled separately)."""
VERTICAL_TRACK_TOL_RAD = 1e-12
"""|phi - pi/2| above which ``map_release`` refuses a track angle: the 1-D map is exact
only for a vertical track; the planar branch (Phase 2) carries the rest."""

ATOL_M = 1e-6
"""Absolute tolerance for length states [m]."""
ATOL_MPS = 1e-9
"""Absolute tolerance for velocity and loss-quadrature states [m/s]."""
ATOL_KG = 1e-6
"""Absolute tolerance for mass states [kg]."""
ATOL_J = 1e-3
"""Absolute tolerance for energy quadrature states [J] (track phase)."""
_ATOL_BY_SUFFIX: dict[str, float] = {"_m": ATOL_M, "_mps": ATOL_MPS, "_kg": ATOL_KG, "_J": ATOL_J}


# --------------------------------------------------------------------------- settings


@dataclass(frozen=True)
class IntegratorSettings:
    """solve_ivp settings for a run; mirrors ``config.IntegratorConfig``.

    method: scipy method name; rtol: relative tolerance; first_step_s: first step [s]
    (capped at half the phase span); ramp_steps, lag_steps_per_tau, push_steps: how
    finely the planner caps max_step during a thrust ramp (t_ramp / ramp_steps), a lag
    (tau / lag_steps_per_tau) and a track push (t_push / push_steps); t_max_s: the guard
    [s] on open-ended phases; sample_dt_s: the output resampling interval [s] (the
    caller's job, from the dense output).
    """

    method: str = "DOP853"
    rtol: float = 1e-10
    first_step_s: float = 1e-3
    ramp_steps: int = 10
    lag_steps_per_tau: int = 4
    push_steps: int = 50
    t_max_s: float = 3600.0
    sample_dt_s: float = 0.05

    def __post_init__(self) -> None:
        if self.method not in SUPPORTED_METHODS:
            raise ValueError(f"method must be one of {SUPPORTED_METHODS}, got {self.method!r}")
        if self.rtol <= 0.0 or self.first_step_s <= 0.0:
            raise ValueError("rtol and first_step_s must be > 0")
        if min(self.ramp_steps, self.lag_steps_per_tau, self.push_steps) < 1:
            raise ValueError("step counts must be >= 1")
        if self.t_max_s <= 0.0 or self.sample_dt_s <= 0.0:
            raise ValueError("t_max_s and sample_dt_s must be > 0")

    @classmethod
    def from_config(cls, cfg: IntegratorConfig) -> IntegratorSettings:
        """Settings from a validated ``IntegratorConfig`` (the method stays DOP853)."""
        return cls(
            rtol=cfg.rtol,
            first_step_s=cfg.first_step_s,
            ramp_steps=cfg.ramp_steps,
            lag_steps_per_tau=cfg.lag_steps_per_tau,
            push_steps=cfg.push_steps,
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
    dense: the OdeSolution for resampling, None for a pass-through; ended_by: the name
    of the terminal event, "t_end", or "zero_span"; t_end and y_end: the final time [s]
    and state; notes: what the pre-solve event rules did; event_times: every event
    occurrence (name, t [s]) including non-terminal ones, in time order.
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

    @property
    def span_s(self) -> float:
        """Duration of the phase [s]."""
        return self.t_end - self.spec.t0


# ----------------------------------------------------------------------- tolerances


def atol_for(state_names: tuple[str, ...]) -> np.ndarray:
    """Per-state absolute tolerance vector from the unit suffix of each state name.

    Inputs: state names ending in ``_m`` (1e-6 m), ``_mps`` (1e-9 m/s, also the loss
    quadratures), ``_kg`` (1e-6 kg) or ``_J`` (1e-3 J). Output: array of len(names).
    An unknown suffix raises ValueError so a new state cannot silently get a tolerance.
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
    """A zero-length result: the state at t0 handed straight back."""
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
    )


def integrate_phase(spec: PhaseSpec, y0: np.ndarray, settings: IntegratorSettings) -> PhaseResult:
    """Integrate one phase from y0 at spec.t0 until a terminal event, t_end or failure.

    Inputs: spec (rhs, params, events, atol, max_step, times [s]); y0, the state at t0;
    settings. Output: a PhaseResult with the integrator's own sample points (the event
    point last) and the dense output; resampling at sample_dt_s is the caller's job.

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
    4. solve_ivp(method, rtol, atol, dense_output, max_step, first_step, events).
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

    sol = solve_ivp(
        lambda t, y: spec.rhs(t, y, spec.params),
        (t0, t_end),
        y0,
        method=settings.method,
        rtol=settings.rtol,
        atol=spec.atol,
        dense_output=True,
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
    )


def _terminal_event_at(spec: PhaseSpec, t_events: list[np.ndarray], t_last: float) -> str:
    """Name of the terminal event whose last root is the final sample time.

    Exact equality is correct: scipy copies the terminal root verbatim into sol.t[-1].
    """
    for ev, tes in zip(spec.events, t_events, strict=True):
        if ev.terminal and len(tes) and float(tes[-1]) == t_last:
            return ev.name
    raise RuntimeError(f"phase {spec.kind}: solver stopped on an event that cannot be identified")


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


# ------------------------------------------------------------------- planner inputs

MAX_PHASES_PER_RUN = 200
"""Guard: a run that issues more phases than this raises RuntimeError (a planner loop,
not physics)."""
END_KINDS = ("stage1_burnout", "all_burnout", "apex", "impact")
"""Where a run stops (``config.RunEnd``)."""
IGNITION_REFERENCES = ("release", "push_start")
"""What ``IgnitionSpec.t_ign_s`` counts from."""
HOLD_KIND = "HOLD"
"""Phase kind of a clamped vehicle (before t = 0, or extended past it until liftoff)."""
ASSIST_KIND = "ASSIST"
"""Phase kind of the track push (state in the track layout, not VERTICAL_LAYOUT)."""
ASCENT_KINDS = (
    "COAST_PRE_IGN",
    "FALL_PRE_IGN",
    "BURN",
    "COAST_STAGING",
    "FALL_STAGING",
    "COAST",
    "FALL",
)
"""Phase kinds of the free flight after release; the loss budget sums over these."""

_IZ = VERTICAL_LAYOUT.index("z_m")
_IV = VERTICAL_LAYOUT.index("v_mps")
_IM = VERTICAL_LAYOUT.index("m_kg")


@dataclass(frozen=True)
class IgnitionSpec:
    """How and when one stage lights, on the internal clock (t = 0 at push start on a
    track or at hold-down release on a pad).

    t_ign_s: ignition time [s] counted from ``reference``: "release" (first stage: track
    exit or hold-down release, t_release; later stages: the end of their staging coast)
    or "push_start" (t = 0 of a track run; first stage only, a pad has no push).
    startup: a Startup overriding the stage's own shape, or None to keep it. fails: the
    engines never light (T identically 0). Built from ``config.IgnitionConfig`` at the
    boundary by ``from_config``.
    """

    t_ign_s: float = 0.0
    reference: str = "release"
    startup: Startup | None = None
    fails: bool = False

    def __post_init__(self) -> None:
        if self.reference not in IGNITION_REFERENCES:
            raise ValueError(f"reference must be one of {IGNITION_REFERENCES}")

    @classmethod
    def from_config(cls, cfg: IgnitionConfig, base_startup: Startup) -> IgnitionSpec:
        """Spec from a validated IgnitionConfig; the startup override is resolved against
        the stage's own Startup (None when the config gives no override)."""
        startup = None if cfg.startup is None else cfg.resolved_startup(base_startup)
        return cls(cfg.t_ign_s, cfg.reference, startup, cfg.fails)

    def t_ign_abs_s(self, t_release_s: float, t_push_start_s: float = 0.0) -> float:
        """Absolute ignition time [s] of a first stage: t_release + t_ign_s for reference
        "release", t_push_start + t_ign_s for "push_start"."""
        origin = t_release_s if self.reference == "release" else t_push_start_s
        return origin + self.t_ign_s


@dataclass(frozen=True)
class AscentStart:
    """Where a pad run starts its ascent frame: altitude z0_m [m] above the datum and
    signed vertical velocity v0_mps [m/s] at release (t = 0). The default (0, 0) is the
    pad; a non-zero v0 is the injection point tests use to start a vertical burn at
    speed without a track model. A vehicle at rest on the ground (v0 = 0 and z0 at the
    planner's z_ground) is held down until its thrust exceeds its weight; one at rest
    above the ground is in free fall (nothing holds it: with its thrust below its
    weight it sinks, sigma = -1, until a turnaround), and a moving one is already
    flying. A moving start combined with an ignition before release (t_ign < 0) is a
    test-only emulation of "lit on the carriage" without a track model: the HOLD
    phase before t = 0 burns propellant in closed form while z and v stay at (z0, v0),
    which is not a physical state (its time-series rows show a clamped vehicle moving
    at v0) but reproduces the straddle form of ``losses.ignition_loss_analytic_mps``
    exactly, since only the mass at release matters to the flight that follows."""

    z0_m: float = 0.0
    v0_mps: float = 0.0

    @property
    def at_rest(self) -> bool:
        """True for a vehicle that is not moving at release (v0 = 0)."""
        return self.v0_mps == 0.0

    def on_ground(self, z_ground_m: float) -> bool:
        """True for a vehicle standing on the ground: at rest within ATOL_M of
        z_ground_m [m] (the pad); only such a start is held down."""
        return self.at_rest and abs(self.z0_m - z_ground_m) <= ATOL_M


@dataclass(frozen=True)
class HoldParams:
    """Parameters of a HOLD phase: the lit stage's ThrustSchedule on the absolute clock,
    the effective gravity at the pad g_eff_mps2 [m/s^2] (mu/R_E^2 - omega_p^2 R_E), the
    pad pressure p_amb_pa [Pa] (0 in Phase 1) for the delivered thrust, and ``lit``:
    False for a hold sub-phase that ends at the ignition kink, where the engine has not
    lit yet and T is identically 0 whatever the schedule says at the closing boundary
    (a step's f(0) = 1 would otherwise leak into the integrator's last stage at the
    kink and bias the mass by more than ATOL_KG)."""

    schedule: ThrustSchedule
    g_eff_mps2: float
    p_amb_pa: float = 0.0
    lit: bool = True

    def thrust_N(self, t: float) -> float:
        """Delivered thrust [N] at time t [s]: the schedule's, or 0 while not lit."""
        return self.schedule.thrust_N(t, self.p_amb_pa) if self.lit else 0.0

    def thrust_vac_N(self, t: float) -> float:
        """Vacuum thrust [N] at time t [s]: the schedule's, or 0 while not lit."""
        return self.schedule.thrust_vac_N(t) if self.lit else 0.0

    def hold_down_force_N(self, t: float, m_kg: float) -> float:
        """Force [N] the hold-down carries at time t [s] with vehicle mass m_kg:
        m g_eff - T(t), positive while the weight exceeds the thrust; its minimum over
        the hold is reported (it is not a tensile flag)."""
        return m_kg * self.g_eff_mps2 - self.thrust_N(t)


def rhs_hold(t: float, y: np.ndarray, p: HoldParams) -> np.ndarray:
    """Time derivative of a clamped vehicle: only the mass changes.

    Inputs: t, absolute run time [s]; y in VERTICAL_LAYOUT order; p, HoldParams. Output:
    dy/dt with dm/dt = -T_vac(t)/c (0 while the engine is not lit) and every other entry
    (z, v, loss quadratures) zero. Frame: the pad; the vehicle does not move, so no
    gravity loss accrues.
    """
    dy = np.zeros(len(VERTICAL_STATE_NAMES))
    if p.lit:
        dy[_IM] = -p.schedule.mass_flow_kgps(t)
    return dy


# ----------------------------------------------------------------------- run trace


@dataclass(frozen=True)
class EventRecord:
    """One logged event: name, absolute time t_s [s], the phase kind and stage it
    happened in, and the state there (z_m [m], v_mps [m/s] signed, m_kg [kg])."""

    name: str
    t_s: float
    phase: str
    stage: str
    z_m: float
    v_mps: float
    m_kg: float


@dataclass(frozen=True)
class HoldSummary:
    """What the hold-down did: t_start_s and t_end_s [s] (absolute), extension_s [s]
    past t = 0 until liftoff (0 when the thrust already exceeded the weight at
    release), force_min_N [N] the minimum hold-down force m g_eff - T over the hold
    (sampled), and propellant_burned_kg [kg] burned over the whole clamp, ignition to
    liftoff (before release and during any extension past t = 0)."""

    t_start_s: float
    t_end_s: float
    extension_s: float
    force_min_N: float
    propellant_burned_kg: float

    @property
    def duration_s(self) -> float:
        """Total clamped time [s], ignition to liftoff."""
        return self.t_end_s - self.t_start_s


@dataclass(frozen=True, eq=False)
class RunTrace:
    """Everything the planner produced for one run (pure data; ``sim.simulate`` turns
    it into a Result).

    phases: every PhaseResult in order; events: EventRecords in time order; status:
    "nominal", "impact", "no_liftoff" or "drive_limit"; flags: run flags (every
    disarmed-event note, no_liftoff, ...); assumptions: run-specific assumption strings
    (hold extension); t_release_s: absolute release time [s] (0 on a pad, the track-end
    root on a track); y_release: the ascent state at release (VERTICAL_LAYOUT;
    quadratures zero), None when the vehicle never lifted off or left the track;
    t_flight_start_s and y_flight_start: when and in what state the free flight (the
    loss accounting) began: release, or the liftoff root of an extended hold; None when
    it never began; hold: the HoldSummary or None; t_ign_abs_s: absolute ignition time
    [s] per stage name (stages that never got to ignite are absent); burnouts: (t [s],
    state) at burnout per stage name.
    """

    phases: tuple[PhaseResult, ...]
    events: tuple[EventRecord, ...]
    status: str
    flags: tuple[str, ...]
    assumptions: tuple[str, ...]
    t_release_s: float
    y_release: np.ndarray | None
    t_flight_start_s: float | None
    y_flight_start: np.ndarray | None
    hold: HoldSummary | None
    t_ign_abs_s: Mapping[str, float]
    burnouts: Mapping[str, tuple[float, np.ndarray]]

    def ascent_phases(self) -> list[PhaseResult]:
        """The free-flight phases after release (kinds in ASCENT_KINDS), in order."""
        return [p for p in self.phases if p.spec.kind in ASCENT_KINDS]

    def assist_phases(self) -> list[PhaseResult]:
        """The track phases (kind ASSIST, states in the track layout), in order."""
        return [p for p in self.phases if p.spec.kind == ASSIST_KIND]

    def first_event(self, name: str) -> EventRecord | None:
        """The first logged event called name, or None."""
        return next((e for e in self.events if e.name == name), None)


class TraceBuilder:
    """Mutable accumulator the planner writes into; ``finish`` freezes it as a RunTrace.

    Public so the assist models can prepend their track phases and events before handing
    the released state to ``VerticalPlanner.ascend``. ``add_phase`` enforces the
    MAX_PHASES_PER_RUN guard and turns every engine note into a run flag.
    """

    def __init__(self, stage_names: tuple[str, ...]) -> None:
        self.phases: list[PhaseResult] = []
        self.events: list[EventRecord] = []
        self.status = "nominal"
        self.flags: list[str] = []
        self.assumptions: list[str] = []
        self.t_release_s = 0.0
        self.y_release: np.ndarray | None = None
        self.t_flight_start_s: float | None = None
        self.y_flight_start: np.ndarray | None = None
        self.hold: HoldSummary | None = None
        self.t_ign_abs_s: dict[str, float] = {}
        self.burnouts: dict[str, tuple[float, np.ndarray]] = {}
        self._stage_names = stage_names

    def stage_name(self, index: int) -> str:
        """Name of the stage with this index."""
        return self._stage_names[index]

    def has_event(self, name: str, stage_index: int) -> bool:
        """Whether an event called name has been logged for this stage."""
        stage = self.stage_name(stage_index)
        return any(e.name == name and e.stage == stage for e in self.events)

    def add_phase(self, res: PhaseResult) -> PhaseResult:
        """Append a phase; its engine notes become flags; more than MAX_PHASES_PER_RUN
        phases raises RuntimeError."""
        self.phases.append(res)
        if len(self.phases) > MAX_PHASES_PER_RUN:
            raise RuntimeError(
                f"run issued more than {MAX_PHASES_PER_RUN} phases (last: {res.spec.kind} at "
                f"t = {res.spec.t0:.6g} s); the planner is looping"
            )
        self.flags += [f"{res.spec.kind} at t = {res.spec.t0:.6g} s: {n}" for n in res.notes]
        return res

    def add_event(self, name: str, t_s: float, phase: str, stage_index: int, y: np.ndarray) -> None:
        """Log an event with the state y (VERTICAL_LAYOUT) at time t_s [s]."""
        self.events.append(
            EventRecord(
                name,
                float(t_s),
                phase,
                self.stage_name(stage_index),
                float(y[_IZ]),
                float(y[_IV]),
                float(y[_IM]),
            )
        )

    def finish(self) -> RunTrace:
        """Freeze into a RunTrace (events sorted by time, stable)."""
        return RunTrace(
            phases=tuple(self.phases),
            events=tuple(sorted(self.events, key=lambda e: e.t_s)),
            status=self.status,
            flags=tuple(self.flags),
            assumptions=tuple(self.assumptions),
            t_release_s=self.t_release_s,
            y_release=None if self.y_release is None else self.y_release.copy(),
            t_flight_start_s=self.t_flight_start_s,
            y_flight_start=None if self.y_flight_start is None else self.y_flight_start.copy(),
            hold=self.hold,
            t_ign_abs_s=dict(self.t_ign_abs_s),
            burnouts=dict(self.burnouts),
        )


# ---------------------------------------------------------------------------- maps


def map_release(
    sdot_mps: float,
    m_kg: float,
    phi_rad: float,
    exit_altitude_m: float,
    layout: StateLayout = VERTICAL_LAYOUT,
) -> np.ndarray:
    """Map the track state at release into the 1-D ascent frame (vertical track only).

    Inputs: sdot_mps, the speed along the track [m/s] at s = L; m_kg, the vehicle mass
    [kg] (the carriage stays); phi_rad, the track angle above horizontal [rad] at the
    exit, which must be pi/2 within VERTICAL_TRACK_TOL_RAD (a vertical silo);
    exit_altitude_m, the altitude [m] of the track exit in the +z-up datum frame.
    Output: the ascent state (layout order) with z = exit_altitude, v = sdot, m = m_kg
    and every loss quadrature zero (the accounting starts at release). A tilted exit
    raises ValueError: projecting sdot onto the vertical would silently discard the
    downrange component (three quarters of the kinetic energy at 30 deg), so the 1-D map
    is exact only for a vertical track; Phase 2's planar branch carries a tilted exit
    and adds omega_p r to the downrange component.
    """
    if abs(phi_rad - 0.5 * math.pi) > VERTICAL_TRACK_TOL_RAD:
        raise ValueError(
            f"map_release: the 1-D ascent needs a vertical track (phi = pi/2), got phi = "
            f"{phi_rad:.6g} rad; a tilted exit is the planar branch of Phase 2"
        )
    return layout.build(z_m=exit_altitude_m, v_mps=sdot_mps, m_kg=m_kg)


def map_staging(
    y: np.ndarray, vehicle: Vehicle, stage_index: int, layout: StateLayout = VERTICAL_LAYOUT
) -> np.ndarray:
    """Drop stage ``stage_index`` after its burnout: the state with the stage's dry mass
    removed, plus the fairing when ``vehicle.fairing_drop == "staging"`` and this is the
    first stage. Inputs: y (layout order, [m], [m/s], [kg], ...); the vehicle; the index
    of the stage that just burned out. Output: a new state vector; z, v and the loss
    quadratures are unchanged (instantaneous, impulse-free separation)."""
    stage = vehicle.stages[stage_index]
    dropped = stage.dry_mass_kg
    if vehicle.fairing_drop == "staging" and stage_index == 0:
        dropped += vehicle.fairing_mass_kg
    out = np.array(y, dtype=float, copy=True)
    out[layout.index("m_kg")] -= dropped
    return out


# -------------------------------------------------------------------------- planner


def sample_grid(t0: float, t1: float, dt: float) -> np.ndarray:
    """Multiples of dt [s] strictly inside (t0, t1) [s], on the absolute clock (k dt for
    integer k), so every phase samples the same grid; a point within
    SAMPLE_GRID_REL_EPS (relative) of an end is left to the boundary sample."""
    eps = SAMPLE_GRID_REL_EPS * max(1.0, abs(t0), abs(t1))
    k0 = math.ceil((t0 + eps) / dt)
    k1 = math.floor((t1 - eps) / dt)
    return np.arange(k0, k1 + 1) * dt if k1 >= k0 else np.empty(0)


class VerticalPlanner:
    """The 1-D state machine (docs/physics.md, "Phases and events") for one vehicle.

    Inputs: the Vehicle; ignition, an IgnitionSpec per stage name; gravity, the ascent
    Gravity model (mu/r^2 in runs; ConstantGravity only through tests); g_eff_mps2, the
    effective gravity at the pad or track [m/s^2] (also the reference g_ref that splits
    the gravity loss into duration and altitude parts unless g_ref_mps2 is given); end,
    one of END_KINDS; settings, the IntegratorSettings; z_ground_m, the impact altitude
    [m] in the datum frame; r_datum_m, the radius of z = 0 [m]; p_amb_pa, the one
    ambient pressure [Pa] the hold-down balance, the sigma rule at v = 0 and the burn
    right-hand side all use for the delivered thrust (0: the Phase 1 assumption of
    vacuum thrust from sea level; Phase 2 hands in the pad pressure). ``run_pad`` runs a pad
    start (HOLD then ascent); ``ascend`` runs the ascent from a released state into a
    TraceBuilder, for the assist models to call after their track phase. Every phase
    lists only the events that can end it and never the one that ended the previous
    phase; sigma is fixed per phase; the engine's disarm notes become run flags.
    """

    def __init__(
        self,
        vehicle: Vehicle,
        ignition: Mapping[str, IgnitionSpec],
        gravity: Gravity,
        g_eff_mps2: float,
        end: str,
        settings: IntegratorSettings,
        *,
        g_ref_mps2: float | None = None,
        z_ground_m: float = 0.0,
        r_datum_m: float = R_EARTH_M,
        p_amb_pa: float = 0.0,
    ) -> None:
        if end not in END_KINDS:
            raise ValueError(f"end must be one of {END_KINDS}, got {end!r}")
        missing = [s.name for s in vehicle.stages if s.name not in ignition]
        if missing:
            raise ValueError(f"no IgnitionSpec for stages {missing}")
        if g_eff_mps2 <= 0.0:
            raise ValueError("g_eff_mps2 must be > 0")
        if p_amb_pa < 0.0:
            raise ValueError("p_amb_pa must be >= 0")
        self.p_amb_pa = p_amb_pa
        self.vehicle = vehicle
        self.ignition = dict(ignition)
        self.gravity = gravity
        self.g_eff_mps2 = g_eff_mps2
        self.g_ref_mps2 = g_eff_mps2 if g_ref_mps2 is None else g_ref_mps2
        self.end = end
        self.settings = settings
        self.z_ground_m = z_ground_m
        self.r_datum_m = r_datum_m
        self.atol = atol_for(VERTICAL_STATE_NAMES)

    # ------------------------------------------------------------------ entry points

    def new_builder(self) -> TraceBuilder:
        """An empty TraceBuilder for this vehicle."""
        return TraceBuilder(self.vehicle.stage_names)

    def run_pad(self, start: AscentStart | None = None) -> RunTrace:
        """A pad run: t = 0 at hold-down release, t_release = 0.

        With the first stage lit before t = 0 the vehicle is clamped from ignition to
        release (closed-form mass; no ODE). A vehicle at rest on the ground whose thrust
        is below its weight at t = 0 stays clamped until the liftoff event (mass-only
        ODE); no liftoff by t_max ends the run with status "no_liftoff". A start at rest
        above the ground is not held: it falls (``AscentStart``). A moving start (v0 !=
        0) with t_ign < 0 is the test-only emulation of an engine lit before release
        described in ``AscentStart``: the pre-release HOLD burns mass only, and its rows
        carry z0 and v0 unchanged. Then ``ascend``.
        """
        start = AscentStart() if start is None else start
        stage0 = self.vehicle.stages[0]
        spec = self.ignition[stage0.name]
        if spec.reference != "release":
            raise ValueError("a pad run has no push: use reference 'release' for the first stage")
        tr = self.new_builder()
        t_release = 0.0
        t_ign = spec.t_ign_abs_s(t_release)
        tr.t_ign_abs_s[stage0.name] = t_ign
        schedule = stage0.schedule(t_ign, spec.startup, spec.fails)
        params = HoldParams(schedule, self.g_eff_mps2, self.p_amb_pa)
        m0 = self.vehicle.liftoff_mass_kg()
        y = VERTICAL_LAYOUT.build(z_m=start.z0_m, v_mps=start.v0_mps, m_kg=m0)
        hold_start = t_release
        force_min = math.inf
        if t_ign < t_release:
            hold_start = t_ign
            tr.add_event("ignition", t_ign, HOLD_KIND, 0, y)
            y, f_min = self.hold_closed_form(tr, params, t_ign, t_release, y)
            force_min = min(force_min, f_min)
        tr.t_release_s = t_release
        tr.y_release = y.copy()
        tr.add_event("release", t_release, HOLD_KIND if t_ign < t_release else "RELEASE", 0, y)
        t_start, sigma_hint = t_release, None
        if start.on_ground(self.z_ground_m):
            t_start, y, f_min = self.hold_until_liftoff(tr, params, t_release, y)
            force_min = min(force_min, f_min)
            if t_start > t_release:
                sigma_hint = 1
        if hold_start < t_release or t_start > t_release:
            burned = m0 - float(y[_IM])  # over the whole clamp, ignition to liftoff
            tr.hold = HoldSummary(hold_start, t_start, t_start - t_release, force_min, burned)
        if tr.status == "no_liftoff":
            return tr.finish()
        self.ascend(tr, t_start, y, sigma_hint=sigma_hint)
        return tr.finish()

    def run_track(self, assist: AssistModel, track: TrackGeometry) -> RunTrace:
        """A track run: t = 0 at push start, release at the track end (docs/physics.md,
        "Silo model").

        The first stage's ignition time resolves against the model's push-time estimate
        (``push_time_estimate``, exact for the prescribed-acceleration drive) for
        reference ``release`` and against t = 0 for ``push_start``. With t_ign < 0 the
        vehicle is clamped to the carriage from ignition to the push start (the pad's
        closed-form HOLD; no liftoff extension: the push starts at t = 0 regardless of
        the thrust). The ASSIST phase integrates the track state (``rhs_track``) from
        s = 0 at rest, split at the thrust kinks inside the push (a sub-phase ending at
        the ignition kink is unlit), with max_step = t_push/push_steps (tightened by the
        ramp or lag cap when lit) and the events ``track_end`` (release),
        ``drive_limit`` (unless the model allows a negative drive force: status
        ``drive_limit``, the run stops on the track) and ``propellant`` (exhausted on
        the track: ValueError). At release the state maps into the ascent frame
        (``map_release``), t_release is the track-end root, and ``ascend`` runs the
        flight. Events logged on the track: push_start, ignition (when inside the
        push), ramp_end, drive_limit, release.
        """
        stage0 = self.vehicle.stages[0]
        spec = self.ignition[stage0.name]
        tr = self.new_builder()
        t_push_start = 0.0
        t_push_est = assist.push_time_estimate(track)
        if t_push_est <= 0.0:
            raise ValueError(f"assist model {assist.name!r} estimates no push (t_push <= 0)")
        t_ign = spec.t_ign_abs_s(t_push_est, t_push_start)
        tr.t_ign_abs_s[stage0.name] = t_ign
        schedule = stage0.schedule(t_ign, spec.startup, spec.fails)
        m0 = self.vehicle.liftoff_mass_kg()
        y_hold = VERTICAL_LAYOUT.build(z_m=track.start_altitude_m, m_kg=m0)
        if t_ign < t_push_start:
            # The clamp carries the weight component along the track, m g_eff sin phi.
            g_axial = self.g_eff_mps2 * math.sin(track.phi(0.0))
            hold = HoldParams(schedule, g_axial, self.p_amb_pa)
            tr.add_event("ignition", t_ign, HOLD_KIND, 0, y_hold)
            y_hold, f_min = self.hold_closed_form(tr, hold, t_ign, t_push_start, y_hold)
            m_push = float(y_hold[_IM])
            tr.hold = HoldSummary(t_ign, t_push_start, 0.0, f_min, m0 - m_push)
        else:
            m_push = m0

        layout = StateLayout(track_state_names(assist))
        atol = atol_for(layout.names)
        y = layout.build(s_m=0.0, sdot_mps=0.0, m_kg=m_push)
        extra0 = np.asarray(assist.initial_extra(), dtype=float)
        if extra0.size:
            i0 = layout.index("m_kg") + 1
            y[i0 : i0 + extra0.size] = extra0
        m_dry = self.vehicle.stack_dry_mass_kg(0)
        length = track.length_m
        push_cap = t_push_est / self.settings.push_steps
        kinks = sorted(k for k in schedule.kink_times() if k > t_push_start + ZERO_SPAN_S)
        boundaries: list[float | None] = [*kinks, None]
        t = t_push_start
        params = self._track_params(assist, track, schedule, t)
        tr.add_event("push_start", t, ASSIST_KIND, 0, track_to_vertical(y, params))
        released = False
        for t_b in boundaries:
            params = self._track_params(assist, track, schedule, t)
            if params.lit and not tr.has_event("ignition", 0):
                tr.add_event("ignition", t, ASSIST_KIND, 0, track_to_vertical(y, params))
            events: list[EventSpec] = [ev_track_end(length, layout), ev_propellant(m_dry, layout)]
            if not assist.allow_negative_drive:
                events.append(ev_drive_limit(params))
            step = min(push_cap, self._max_step(schedule, t)) if params.lit else push_cap
            phase = PhaseSpec(ASSIST_KIND, 0, t, t_b, rhs_track, params, tuple(events), atol, step)
            res = tr.add_phase(integrate_phase(phase, y, self.settings))
            for name, te in res.event_times:
                if name != "track_end":
                    y_e = res.y_end if te == res.t_end or res.dense is None else res.dense(te)
                    tr.add_event(
                        name, te, ASSIST_KIND, 0, track_to_vertical(np.asarray(y_e), params)
                    )
            t, y = res.t_end, res.y_end
            if res.ended_by == "drive_limit":
                tr.status = "drive_limit"
                tr.flags.append(
                    f"drive_limit: the drive force crossed zero at t = {t:.6g} s (the prescribed "
                    "acceleration would need the drive to brake the engine); the run stopped "
                    "on the track"
                )
                return tr.finish()
            if res.ended_by == "propellant":
                raise ValueError(
                    f"stage {stage0.name!r} exhausted its propellant at t = {t:.6g} s on the track"
                )
            s_end = float(layout.get(y, "s_m"))
            if res.ended_by == "track_end" or s_end >= length - ATOL_M:
                released = True
                break
            if t_b is not None and schedule.startup.effective_kind == "ramp":
                if abs(t_b - (schedule.t_ign_abs_s + schedule.startup.t_ramp_s)) <= ZERO_SPAN_S:
                    tr.add_event("ramp_end", t, ASSIST_KIND, 0, track_to_vertical(y, params))
        if not released:
            raise RuntimeError("track phase ended without reaching the track end (planner bug)")
        y_rel = map_release(
            float(layout.get(y, "sdot_mps")),
            float(layout.get(y, "m_kg")),
            track.phi(length),
            track.start_altitude_m + track.z(length),
        )
        tr.t_release_s = t
        tr.y_release = y_rel.copy()
        tr.add_event("release", t, ASSIST_KIND, 0, y_rel)
        self.ascend(tr, t, y_rel)
        return tr.finish()

    def _track_params(
        self, assist: AssistModel, track: TrackGeometry, schedule: ThrustSchedule, t: float
    ) -> TrackParams:
        """TrackParams of the sub-phase starting at t [s]: lit once the ignition time has
        passed (never for a failed ignition)."""
        lit = not schedule.fails and t >= schedule.t_ign_abs_s - ZERO_SPAN_S
        return TrackParams(
            track=track,
            assist=assist,
            carriage_mass_kg=assist.carriage_mass_kg,
            g_eff_mps2=self.g_eff_mps2,
            schedule=schedule,
            p_amb_pa=self.p_amb_pa,
            lit=lit,
        )

    def ascend(
        self,
        tr: TraceBuilder,
        t_start_s: float,
        y: np.ndarray,
        *,
        sigma_hint: int | None = None,
    ) -> None:
        """Run the ascent from the released state into the builder.

        Inputs: tr, a TraceBuilder whose t_release_s and y_release are set (and whose
        t_ign_abs_s carries the first stage's ignition time when a track or hold fixed
        it; otherwise it is t_release + t_ign_s); t_start_s, the absolute time [s] the
        free flight starts (t_release, or the liftoff time after an extended hold); y,
        the ascent state then; sigma_hint, the velocity sign of the first phase when the
        caller knows it (+1 after a liftoff root). Records t_flight_start_s and
        y_flight_start (where the loss accounting begins), then runs COAST_PRE_IGN,
        BURN, STAGING, COAST_STAGING, ... and the terminal coast the run's ``end`` asks
        for; sets tr.status ("nominal", "impact") and tr.burnouts. The first stage's
        ignition event is logged here only when its burn starts at ignition and the
        caller has not logged it (a hold or a track logs an earlier ignition itself).
        """
        t = t_start_s
        tr.t_flight_start_s = t
        tr.y_flight_start = np.array(y, dtype=float, copy=True)
        n = self.vehicle.n_stages
        for k, stage in enumerate(self.vehicle.stages):
            spec = self.ignition[stage.name]
            if k == 0:
                t_ign = tr.t_ign_abs_s.get(stage.name)
                if t_ign is None:
                    t_ign = spec.t_ign_abs_s(tr.t_release_s)
                    tr.t_ign_abs_s[stage.name] = t_ign
            else:
                if spec.reference != "release" or spec.t_ign_s < 0.0:
                    raise ValueError(
                        f"stage {stage.name!r}: a later stage ignites at t_ign_s >= 0 after "
                        "its staging coast (reference 'release')"
                    )
                t_coast_end = t + stage.coast_before_ignition_s
                t, y, how = self._coast(
                    tr, ("COAST_STAGING", "FALL_STAGING"), k, t, t_coast_end, y, sigma_hint
                )
                sigma_hint = None
                if how == "impact":
                    return
                t_ign = t_coast_end + spec.t_ign_s
                tr.t_ign_abs_s[stage.name] = t_ign
            if spec.fails:
                if self.end != "impact":
                    raise ValueError(f"stage {stage.name!r} fails: the run must end at impact")
                self._terminal_coast(tr, k, t, y, sigma_hint)
                return
            if t_ign > t + ZERO_SPAN_S:
                t, y, how = self._coast(
                    tr, ("COAST_PRE_IGN", "FALL_PRE_IGN"), k, t, t_ign, y, sigma_hint
                )
                sigma_hint = None
                if how == "impact":
                    return
            schedule = stage.schedule(t_ign, spec.startup, spec.fails)
            if t_ign >= t - ZERO_SPAN_S and not tr.has_event("ignition", k):
                tr.add_event("ignition", t, "BURN", k, y)
            t, y, how = self._burn(tr, k, schedule, t, y, sigma_hint)
            sigma_hint = None
            if how == "impact":
                return
            tr.burnouts[stage.name] = (t, y.copy())
            last_stage = k == n - 1
            if (self.end == "stage1_burnout" and k == 0) or (
                last_stage and self.end == "all_burnout"
            ):
                tr.add_event("end", t, "BURN", k, y)
                return
            if not last_stage:
                y = map_staging(y, self.vehicle, k)
                tr.add_event("staging", t, "COAST_STAGING", k + 1, y)
                continue
            self._terminal_coast(tr, k, t, y, None)
            return

    # ------------------------------------------------------------------------ holds

    def hold_closed_form(
        self, tr: TraceBuilder, params: HoldParams, t0: float, t1: float, y: np.ndarray
    ) -> tuple[np.ndarray, float]:
        """Clamp the vehicle from t0 to t1 [s]: z and v are held, the mass follows
        ``propellant_burned_kg`` in closed form (no ODE; constant while ``params.lit``
        is False), sampled at settings.sample_dt_s. Only the burn between t0 and t1 is
        subtracted from y's mass, so the segment may start any time after ignition (a
        lit hold split into several calls gives the single-call result). Returns the
        state at t1 and the minimum hold-down force [N] over the samples. Raises
        ValueError if the first stage's propellant runs out by t1."""
        stage = self.vehicle.stages[0]
        m0 = float(y[_IM])
        m_dry = self.vehicle.stack_dry_mass_kg(0)

        def burned(t: float) -> float:
            return propellant_burned_kg(params.schedule, t) if params.lit else 0.0

        # The closed form counts from ignition; the segment subtracts its own increment,
        # so a lit hold may be split at any time without counting an earlier segment's
        # burn twice (a track prelude splitting the hold at a startup kink does this).
        burned_t0 = burned(t0)
        m_end = m0 - (burned(t1) - burned_t0)
        if m_end <= m_dry:
            raise ValueError(
                f"stage {stage.name!r} burns {burned(t1):.6g} kg by the end of a hold lasting "
                f"until t = {t1:.6g} s, more than its {stage.propellant_mass_kg:.6g} kg of "
                "propellant"
            )
        ts = np.concatenate(([t0], sample_grid(t0, t1, self.settings.sample_dt_s), [t1]))
        ys = np.repeat(y.reshape(-1, 1), len(ts), axis=1)
        ys[_IM] = [m0 - (burned(float(t)) - burned_t0) for t in ts]
        spec = PhaseSpec(HOLD_KIND, 0, t0, t1, rhs_hold, params, (), self.atol)
        res = PhaseResult(spec, ts, ys, None, "t_end", t1, ys[:, -1].copy())
        tr.add_phase(res)
        force_min = min(
            params.hold_down_force_N(float(t), float(m)) for t, m in zip(ts, ys[_IM], strict=True)
        )
        return res.y_end, force_min

    def hold_until_liftoff(
        self, tr: TraceBuilder, params: HoldParams, t0: float, y: np.ndarray
    ) -> tuple[float, np.ndarray, float]:
        """Keep a vehicle at rest on the ground clamped past t0 until its thrust exceeds
        its weight.

        If T(t0) >= m g_eff already, returns (t0, y, m g_eff - T) at once. Otherwise the
        hold is split at the thrust kinks up to t0 + t_max_s. A sub-phase before the
        ignition kink is unlit (T = 0; z, v, m constant; sampled directly, no events).
        At the start of every lit sub-phase the balance is re-evaluated with the lit
        schedule, so a step whose thrust exceeds the weight lifts off exactly at its
        kink: no root search across the discontinuity, and no mass bias from the
        integrator's last stage seeing the step's f(0) = 1. A lit sub-phase integrates
        the mass alone (``rhs_hold``) with the liftoff and propellant events. An
        ignition inside the extension is logged (in the HOLD); liftoff records the
        extension as an assumption; propellant exhaustion raises ValueError; no liftoff
        by t_max sets tr.status = "no_liftoff" and a flag. Returns (liftoff time [s],
        state, minimum hold-down force [N] over the extension).
        """
        g = params.g_eff_mps2
        schedule = params.schedule
        force0 = params.hold_down_force_N(t0, float(y[_IM]))
        if force0 <= ATOL_KG * g:
            return t0, y, force0
        stage = self.vehicle.stages[0]
        m_dry = self.vehicle.stack_dry_mass_kg(0)
        t_max = t0 + self.settings.t_max_s
        kinks = [k for k in schedule.kink_times() if t0 < k < t_max]
        t = t0
        force_min = force0
        for t_b in sorted({t_max, *kinks}):
            lit = not schedule.fails and t >= schedule.t_ign_abs_s - ZERO_SPAN_S
            if not lit:
                unlit = HoldParams(schedule, g, params.p_amb_pa, lit=False)
                y, f_min = self.hold_closed_form(tr, unlit, t, t_b, y)
                t = t_b
                force_min = min(force_min, f_min)
                continue
            if not tr.has_event("ignition", 0):
                tr.add_event("ignition", schedule.t_ign_abs_s, HOLD_KIND, 0, y)
            force = params.hold_down_force_N(t, float(y[_IM]))
            force_min = min(force_min, force)
            if force <= ATOL_KG * g:
                return self._liftoff(tr, t, y, force_min)
            spec = PhaseSpec(
                HOLD_KIND,
                0,
                t,
                t_b,
                rhs_hold,
                params,
                (ev_liftoff(schedule, g, params.p_amb_pa), ev_propellant(m_dry)),
                self.atol,
                self._max_step(schedule, t),
            )
            res = tr.add_phase(integrate_phase(spec, y, self.settings))
            t, y = res.t_end, res.y_end
            forces = [
                params.hold_down_force_N(float(ti), float(mi))
                for ti, mi in zip(res.t, res.y[_IM], strict=True)
            ]
            force_min = min(force_min, *forces)
            if res.ended_by == "propellant":
                raise ValueError(
                    f"stage {stage.name!r} exhausted its propellant at t = {t:.6g} s while held "
                    "down waiting for liftoff (thrust below weight)"
                )
            if res.ended_by == "liftoff":
                return self._liftoff(tr, t, y, force_min)
        tr.status = "no_liftoff"
        tr.flags.append(
            f"no_liftoff: thrust never exceeded the weight by t_max = {self.settings.t_max_s:.6g} s"
        )
        return t, y, force_min

    @staticmethod
    def _liftoff(
        tr: TraceBuilder, t: float, y: np.ndarray, force_min: float
    ) -> tuple[float, np.ndarray, float]:
        """Log the liftoff at t [s] (state y) that ends an extended hold, record the
        extension as an assumption, and return (t, y, force_min)."""
        tr.add_event("liftoff", t, HOLD_KIND, 0, y)
        tr.assumptions.append(f"hold extended to t = {t:.6g} s for liftoff (TWR < 1 at release)")
        return t, y, force_min

    # ---------------------------------------------------------------------- phases

    def _max_step(self, schedule: ThrustSchedule | None, t: float) -> float:
        """Step cap [s] at time t: t_ramp / ramp_steps inside a ramp, tau /
        lag_steps_per_tau during a lag burn, unbounded otherwise."""
        if schedule is None or schedule.fails:
            return math.inf
        kind = schedule.startup.effective_kind
        if kind == "ramp":
            t_r = schedule.startup.t_ramp_s
            if t < schedule.t_ign_abs_s + t_r:
                return t_r / self.settings.ramp_steps
            return math.inf
        if kind == "lag":
            return schedule.startup.tau_s / self.settings.lag_steps_per_tau
        return math.inf

    def _segments(self, schedule: ThrustSchedule) -> list[tuple[float, float | None, float]]:
        """Burn sub-phases (t_start, t_end | None, max_step) split at the thrust kinks:
        ramp = [ramp, full burn]; lag or step = [one open-ended burn]."""
        t_ign = schedule.t_ign_abs_s
        kind = schedule.startup.effective_kind
        if kind == "ramp":
            t_r = schedule.startup.t_ramp_s
            return [
                (t_ign, t_ign + t_r, t_r / self.settings.ramp_steps),
                (t_ign + t_r, None, math.inf),
            ]
        if kind == "lag":
            return [(t_ign, None, schedule.startup.tau_s / self.settings.lag_steps_per_tau)]
        return [(t_ign, None, math.inf)]

    def _sigma(
        self, y: np.ndarray, schedule: ThrustSchedule | None, t: float, hint: int | None
    ) -> int:
        """The velocity sign of the next phase: the caller's hint when it knows (after
        an apex: -1; after a turnaround or a liftoff root: +1), else the sign of v, and
        at v = 0 the sign of the net acceleration (+1 when it is zero)."""
        if hint is not None:
            return hint
        v = float(y[_IV])
        if v > ATOL_MPS:
            return 1
        if v < -ATOL_MPS:
            return -1
        thrust = 0.0 if schedule is None else schedule.thrust_N(t, self.p_amb_pa)
        accel = thrust / float(y[_IM]) - self.gravity(self.r_datum_m + float(y[_IZ]))
        return 1 if accel >= 0.0 else -1

    def _params(self, schedule: ThrustSchedule | None, sigma: int) -> VerticalParams:
        return VerticalParams(
            gravity=self.gravity,
            g_ref_mps2=self.g_ref_mps2,
            schedule=schedule,
            r_datum_m=self.r_datum_m,
            p_amb_pa=self.p_amb_pa,
            v_sign=sigma,
        )

    def _integrate(self, tr: TraceBuilder, spec: PhaseSpec, y: np.ndarray) -> PhaseResult:
        """Run one ascent phase, add it to the builder, log its events with the state
        there, and assert that v never left the phase's half-line (sigma v >= -ATOL_MPS
        on every sample; the identity closes even when it does, so this is the check)."""
        res = tr.add_phase(integrate_phase(spec, y, self.settings))
        v = np.asarray(res.y[_IV], dtype=float)
        if np.any(spec.sigma * v < -ATOL_MPS):
            raise RuntimeError(
                f"phase {spec.kind} at t0 = {spec.t0:.6g} s: v changed sign inside a phase "
                f"with sigma = {spec.sigma} (planner bug)"
            )
        for name, te in res.event_times:
            y_e = res.y_end if te == res.t_end or res.dense is None else res.dense(te)
            tr.add_event(name, te, spec.kind, spec.stage_index, np.asarray(y_e))
        return res

    def _coast(
        self,
        tr: TraceBuilder,
        kinds: tuple[str, str],
        k: int,
        t: float,
        t_end: float | None,
        y: np.ndarray,
        sigma_hint: int | None,
        *,
        stop_at_apex: bool = False,
    ) -> tuple[float, np.ndarray, str]:
        """Unpowered flight from t to t_end (None: open-ended). kinds = (rising kind,
        falling kind). Rising phases list apex; falling ones impact. Returns (t, y, how)
        with how in {"time", "apex", "impact"}; an apex flips sigma and continues unless
        stop_at_apex; an impact sets tr.status. The event lists are partitioned by
        sigma, and that partition is what keeps the event that ended the previous phase
        off the next one's list: an apex hands over sigma = -1, whose list has no apex;
        a coast never lists a turnaround; the propellant event belongs to burns only."""
        while True:
            sigma = self._sigma(y, None, t, sigma_hint)
            if sigma == 1:
                kind = kinds[0]
                events: tuple[EventSpec, ...] = (ev_apex(),)
            else:
                kind = kinds[1]
                events = (ev_impact(self.z_ground_m),)
            spec = PhaseSpec(
                kind,
                k,
                t,
                t_end,
                rhs_vertical,
                self._params(None, sigma),
                events,
                self.atol,
                sigma=sigma,
            )
            res = self._integrate(tr, spec, y)
            t, y = res.t_end, res.y_end
            if res.ended_by in ("t_end", "zero_span"):
                return t, y, "time"
            if res.ended_by == "apex":
                if stop_at_apex:
                    return t, y, "apex"
                sigma_hint = -1
                continue
            tr.status = "impact"
            return t, y, "impact"

    def _burn(
        self,
        tr: TraceBuilder,
        k: int,
        schedule: ThrustSchedule,
        t: float,
        y: np.ndarray,
        sigma_hint: int | None,
    ) -> tuple[float, np.ndarray, str]:
        """Burn stage k from t until its propellant event (how = "burnout") or an impact
        while falling under thrust (how = "impact"). Sub-phases follow ``_segments``;
        an apex flips sigma to -1 (turnaround, impact listed), a turnaround flips it
        back to +1 (apex listed), and the burn continues in the same segment. As in
        ``_coast`` the sigma partition of the event lists is what keeps the event that
        ended the previous phase off the next one's list: the rising list has no
        turnaround, the falling list no apex."""
        m_dry = self.vehicle.stack_dry_mass_kg(k)
        for t_a, t_b, max_step in self._segments(schedule):
            if t_b is not None and t_b <= t + ZERO_SPAN_S:
                continue  # this sub-phase ended during a hold
            if t < t_a - ZERO_SPAN_S:
                raise RuntimeError(f"burn of stage {k} starts at t = {t} before ignition {t_a}")
            while True:
                sigma = self._sigma(y, schedule, t, sigma_hint)
                events: list[EventSpec] = [ev_propellant(m_dry)]
                if sigma == 1:
                    events.append(ev_apex())
                else:
                    events += [ev_turnaround(), ev_impact(self.z_ground_m)]
                spec = PhaseSpec(
                    "BURN",
                    k,
                    t,
                    t_b,
                    rhs_vertical,
                    self._params(schedule, sigma),
                    tuple(events),
                    self.atol,
                    max_step,
                    sigma,
                )
                res = self._integrate(tr, spec, y)
                t, y = res.t_end, res.y_end
                ended = res.ended_by
                if ended in ("t_end", "zero_span"):
                    if t_b is not None:
                        tr.add_event("ramp_end", t, "BURN", k, y)
                    sigma_hint = None
                    break
                if ended == "propellant":
                    return t, y, "burnout"
                if ended == "impact":
                    tr.status = "impact"
                    return t, y, "impact"
                sigma_hint = -1 if ended == "apex" else 1
        raise RuntimeError(f"burn of stage {k} ran out of sub-phases without a burnout")

    def _terminal_coast(
        self,
        tr: TraceBuilder,
        k: int,
        t: float,
        y: np.ndarray,
        sigma_hint: int | None,
    ) -> None:
        """What happens after the last burnout (or a failed ignition) for end "apex" or
        "impact": COAST to apex, then FALL to z_ground (status impact). A vehicle already
        falling at end "apex" has passed its apex: the run ends there with a flag.
        ``ascend`` returns before calling this for the burnout ends, so any other end
        here is a planner bug."""
        if self.end not in ("apex", "impact"):
            raise RuntimeError(f"terminal coast reached with end = {self.end!r} (planner bug)")
        sigma = self._sigma(y, None, t, sigma_hint)
        if self.end == "apex":
            if sigma == -1:
                tr.flags.append("end apex: the vehicle was already falling at burnout")
                tr.add_event("end", t, "FALL", k, y)
                return
            t, y, _how = self._coast(
                tr, ("COAST", "FALL"), k, t, None, y, sigma_hint, stop_at_apex=True
            )
            tr.add_event("end", t, "COAST", k, y)
            return
        t, y, _how = self._coast(tr, ("COAST", "FALL"), k, t, None, y, sigma_hint)
        tr.add_event("end", t, "FALL", k, y)
