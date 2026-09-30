"""The run trace: what a planner writes (phases, events, status, flags) and the frozen
``RunTrace`` it hands to ``sim`` (docs/physics.md, "Phases and events").

The trace is model-agnostic. What an event record shows of the state is decided by a
``StateView`` (one per dynamics model), which also names the state layout the model's
event states come in and the phase kinds of its free flight: the 1-D view
``VERTICAL_VIEW`` records the altitude z_m [m] above the datum, the signed vertical
velocity v_mps [m/s] (negative while falling, so events.csv keeps the sign on
fall-back rows) and the mass m_kg [kg], exactly as the Phase 1 records did. The
phase-kind labels shared by the planners and the reporting modules (HOLD, ASSIST,
RELEASE, the 1-D ascent kinds) live here too.

Pure: no I/O, no globals, no printing. Times are absolute run times [s] (t = 0 at push
start on a track or at hold-down release on a pad).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from launchsim.dynamics import VERTICAL_LAYOUT, StateLayout
from launchsim.phases.engine import PhaseResult

MAX_PHASES_PER_RUN = 200
"""Guard: a run that issues more phases than this raises RuntimeError (a planner loop,
not physics)."""
HOLD_KIND = "HOLD"
"""Phase kind of a clamped vehicle (before t = 0, or extended past it until liftoff)."""
ASSIST_KIND = "ASSIST"
"""Phase kind of the track push (state in the track layout, not VERTICAL_LAYOUT)."""
RELEASE_LABEL = "RELEASE"
"""Phase label of a pad's release event when no hold ran before it (nothing was lit
before t = 0): the event belongs to no phase, so it carries this label instead of
HOLD_KIND."""
ASCENT_KINDS = (
    "COAST_PRE_IGN",
    "FALL_PRE_IGN",
    "BURN",
    "COAST_STAGING",
    "FALL_STAGING",
    "COAST",
    "FALL",
)
"""Phase kinds of the 1-D free flight after release (``VERTICAL_VIEW.ascent_kinds``);
the loss budget sums over these."""
MASS_COLUMN = "m_kg"
"""The event-record column every StateView must provide: the vehicle mass [kg]."""
VERTICAL_MODEL = "vertical_1d"
"""Name of the 1-D dynamics model (``config`` ``dynamics: vertical_1d``)."""


# ------------------------------------------------------------------------ state views


class StateView(Protocol):
    """What an event record shows of a model's state vector.

    model: the dynamics model's name; layout: the StateLayout of the states the view
    reads (every event state logged through it must have len(layout) entries, and the
    prelude refuses a builder whose view reads another layout); columns: the record
    columns in output order, SI with the unit in each name, always including
    MASS_COLUMN; ascent_kinds: the phase kinds of the model's free flight after
    release (``RunTrace.ascent_phases``, the loss budget); row(t, y, phase): the values
    of those columns (Python floats) for the state y [the layout's order] at absolute
    time t [s] in a phase of kind ``phase`` (the kind lets a view treat clamped and
    track rows differently from flight rows, e.g. an Earth-fixed downrange of 0).
    """

    @property
    def model(self) -> str:
        """Name of the dynamics model the view reads."""
        ...

    @property
    def layout(self) -> StateLayout:
        """The state layout of the states the view reads."""
        ...

    @property
    def columns(self) -> tuple[str, ...]:
        """The record columns, in output order (MASS_COLUMN among them)."""
        ...

    @property
    def ascent_kinds(self) -> tuple[str, ...]:
        """Phase kinds of the free flight after release."""
        ...

    def row(self, t: float, y: np.ndarray, phase: str) -> dict[str, float]:
        """The column values at time t [s] for state y in a phase of kind ``phase``,
        keyed by column name."""
        ...


@dataclass(frozen=True)
class VerticalView:
    """The 1-D StateView: z_m [m] (altitude above the datum, +z up), v_mps [m/s] (the
    signed vertical velocity: positive rising, negative falling) and m_kg [kg], read
    from a state in ``dynamics.VERTICAL_LAYOUT``. The frame is the +z-up ascent datum
    frame; t does not enter."""

    @property
    def model(self) -> str:
        """VERTICAL_MODEL."""
        return VERTICAL_MODEL

    @property
    def layout(self) -> StateLayout:
        """``dynamics.VERTICAL_LAYOUT``."""
        return VERTICAL_LAYOUT

    @property
    def columns(self) -> tuple[str, ...]:
        """("z_m", "v_mps", "m_kg")."""
        return ("z_m", "v_mps", MASS_COLUMN)

    @property
    def ascent_kinds(self) -> tuple[str, ...]:
        """ASCENT_KINDS (the 1-D free-flight phase kinds)."""
        return ASCENT_KINDS

    def row(self, t: float, y: np.ndarray, phase: str) -> dict[str, float]:
        """z, signed v and m of a VERTICAL_LAYOUT state y (floats, SI); the time t [s]
        and the phase kind do not enter (a clamped or track row reads the same
        columns)."""
        return {
            "z_m": float(y[VERTICAL_LAYOUT.index("z_m")]),
            "v_mps": float(y[VERTICAL_LAYOUT.index("v_mps")]),
            MASS_COLUMN: float(y[VERTICAL_LAYOUT.index("m_kg")]),
        }


VERTICAL_VIEW = VerticalView()
"""The StateView of the 1-D model (the default of TraceBuilder)."""


# ---------------------------------------------------------------------------- records

RecordValues = Mapping[str, float] | Iterable[tuple[str, float]]
"""What ``EventRecord`` accepts for ``values``: a column -> value Mapping or an iterable
of (column, value) pairs; it stores them as a tuple of (str, float) pairs."""


@dataclass(frozen=True)
class EventRecord:
    """One logged event: name, absolute time t_s [s], the phase kind and stage it
    happened in, the mass m_kg [kg] there, and values: the other columns of the run's
    StateView at that instant as (column, value) pairs in the view's column order (for
    the 1-D view z_m [m] and the signed v_mps [m/s]).

    The stored field is always ``tuple[tuple[str, float], ...]``; as constructor input
    ``values`` may also be a ``Mapping[str, float]`` or any iterable of (column, value)
    pairs (``RecordValues``). ``__post_init__`` freezes it into the tuple, turning every
    column into str and every value into a Python float (the sign of zero kept), and
    rejects duplicate columns (ValueError), so a record is immutable and hashable (as
    the Phase 1 record of floats was). ``z_m`` and ``v_mps`` read those
    two 1-D columns (AttributeError for a record written through a view without them);
    ``value(column)`` reads any column. The Phase 1 record carried z_m and v_mps as
    fields between stage and m_kg; the positional order changed with the StateView."""

    name: str
    t_s: float
    phase: str
    stage: str
    m_kg: float
    values: tuple[tuple[str, float], ...]

    def __post_init__(self) -> None:
        given: RecordValues = self.values
        raw: Iterable[tuple[str, float]] = given.items() if isinstance(given, Mapping) else given
        pairs = tuple((str(c), float(v)) for c, v in raw)
        if len({c for c, _ in pairs}) != len(pairs):
            raise ValueError(f"event {self.name!r}: duplicate columns in {pairs}")
        object.__setattr__(self, "values", pairs)

    @property
    def columns(self) -> tuple[str, ...]:
        """The columns in values, in order (MASS_COLUMN is the separate m_kg)."""
        return tuple(c for c, _ in self.values)

    def value(self, column: str) -> float:
        """The value of one StateView column (MASS_COLUMN included); KeyError if the
        view that wrote this record has no such column."""
        if column == MASS_COLUMN:
            return self.m_kg
        for c, v in self.values:
            if c == column:
                return v
        raise KeyError(f"event {self.name!r}: no column {column!r} (columns: {self.columns})")

    def _one_d(self, column: str) -> float:
        try:
            return self.value(column)
        except KeyError:
            raise AttributeError(
                f"event {self.name!r}: the record has no 1-D column {column!r} "
                f"(columns: {self.columns})"
            ) from None

    @property
    def z_m(self) -> float:
        """Altitude above the datum [m] (1-D view column)."""
        return self._one_d("z_m")

    @property
    def v_mps(self) -> float:
        """Signed vertical velocity [m/s], positive rising (1-D view column)."""
        return self._one_d("v_mps")


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
    root on a track); y_release: the ascent state at release (the model's layout;
    quadratures zero): on a pad the state at the hold-down release t = 0, which always
    happens; None when a track run stopped before the track end (drive_limit);
    t_flight_start_s and y_flight_start: when and in what state the free flight (the
    loss accounting) began: release, or the liftoff root of an extended hold; None when
    it never began; hold: the HoldSummary or None; t_ign_abs_s: absolute ignition time
    [s] per stage name (stages that never got to ignite, including one whose ignition
    failed, are absent); burnouts: (t [s], state) at burnout per stage name;
    failed_stage: the name of the stage whose ignition failed (``IgnitionSpec.fails``)
    once the planner reached it, else None; t_fail_s: the absolute time [s] its
    unpowered coast began (release for a first stage, the end of the staging coast for
    a later one), or None when the vehicle never left the ground (a pad, status
    ``no_liftoff``); view: the StateView the event records were written through (its
    ``columns`` are the event columns after name, time, phase and stage; its
    ``ascent_kinds`` select ``ascent_phases``).
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
    failed_stage: str | None = None
    t_fail_s: float | None = None
    view: StateView = VERTICAL_VIEW

    @property
    def model(self) -> str:
        """Name of the dynamics model that produced the trace (the view's)."""
        return self.view.model

    @property
    def nfev_total(self) -> int:
        """Right-hand-side evaluations over every phase (sum of PhaseResult.nfev)."""
        return sum(p.nfev for p in self.phases)

    @property
    def dense_off(self) -> bool:
        """Whether any phase was integrated with dense output off
        (``PhaseResult.dense_off``: a search evaluation, not a recorded run)."""
        return any(p.dense_off for p in self.phases)

    def require_dense(self, purpose: str) -> None:
        """Raise ValueError when the trace has a phase integrated with dense output
        off. The reporting path (resampled time series, crossings, drive-power scans)
        reads a missing dense output as "nothing to resample" and would return wrong
        numbers silently, so it must call this first; purpose names the caller for the
        message."""
        if self.dense_off:
            kinds = sorted({p.spec.kind for p in self.phases if p.dense_off})
            raise ValueError(
                f"{purpose}: the trace has phases integrated with dense output off "
                f"({', '.join(kinds)}); dense_output = False is for search evaluations "
                "only, and a recorded run needs the dense output"
            )

    def ascent_phases(self) -> list[PhaseResult]:
        """The free-flight phases after release (kinds in the view's ascent_kinds;
        ASCENT_KINDS for the 1-D view), in order."""
        kinds = self.view.ascent_kinds
        return [p for p in self.phases if p.spec.kind in kinds]

    def assist_phases(self) -> list[PhaseResult]:
        """The track phases (kind ASSIST, states in the track layout), in order."""
        return [p for p in self.phases if p.spec.kind == ASSIST_KIND]

    def first_event(self, name: str) -> EventRecord | None:
        """The first logged event called name, or None."""
        return next((e for e in self.events if e.name == name), None)


class TraceBuilder:
    """Mutable accumulator the planner writes into; ``finish`` freezes it as a RunTrace.

    Inputs: stage_names, the vehicle's stage names in order; view, the StateView the
    event records are written through (VERTICAL_VIEW by default; it must provide
    MASS_COLUMN). Public so the assist models can prepend their track phases and events
    before handing the released state to ``VerticalPlanner.ascend``. ``add_phase``
    enforces the MAX_PHASES_PER_RUN guard and turns every engine note into a run flag;
    ``add_event`` refuses a state whose length is not the view's layout;
    ``rebind_view`` swaps in a view of the same model, layout and columns (for a view
    whose parameters are known only once the flight starts).
    """

    def __init__(self, stage_names: tuple[str, ...], view: StateView = VERTICAL_VIEW) -> None:
        if MASS_COLUMN not in view.columns:
            raise ValueError(f"a StateView must provide {MASS_COLUMN!r}, got {view.columns}")
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
        self.failed_stage: str | None = None
        self.t_fail_s: float | None = None
        self.view = view
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

    def rebind_view(self, view: StateView) -> None:
        """Write later event records through view instead. It must read the same model,
        layout and columns as the current view (records already logged stay as they
        are, so the columns cannot change mid-run); ValueError otherwise."""
        old = self.view
        if (view.model, view.layout, view.columns) != (old.model, old.layout, old.columns):
            raise ValueError(
                f"rebind_view: the new view ({view.model}, {view.columns}) must read the "
                f"model, layout and columns of the current one ({old.model}, {old.columns})"
            )
        self.view = view

    def add_event(self, name: str, t_s: float, phase: str, stage_index: int, y: np.ndarray) -> None:
        """Log an event at time t_s [s] in a phase of kind ``phase`` with the state y
        (the view's layout; ValueError for a state of another length), recorded through
        the view: m_kg as its own field, every other column in values."""
        n = len(self.view.layout)
        if np.shape(y) != (n,):
            raise ValueError(
                f"event {name!r}: state of shape {np.shape(y)}, but the {self.view.model} "
                f"view reads {n} states {self.view.layout.names}"
            )
        row = self.view.row(float(t_s), y, phase)
        self.events.append(
            EventRecord(
                name,
                float(t_s),
                phase,
                self.stage_name(stage_index),
                row[MASS_COLUMN],
                tuple((c, row[c]) for c in self.view.columns if c != MASS_COLUMN),
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
            failed_stage=self.failed_stage,
            t_fail_s=self.t_fail_s,
            view=self.view,
        )
