"""Phase sequencing and events (docs/physics.md, "Integrator", "Event rules" and "Phases
and events"), split into four modules:

- ``engine``: the generic phase engine (``integrate_phase``), its specs and result,
  the integrator settings, per-state tolerances, ``event_state`` and the event
  factories
- ``trace``: the run trace (``TraceBuilder``, ``RunTrace``, ``EventRecord``) and the
  per-model ``StateView`` that decides what an event record shows (``VERTICAL_VIEW``
  for the 1-D model)
- ``prelude``: ignition specs, the hold-down and the track push up to the track exit,
  parameterised by the flight model's state layout
- ``vertical``: the 1-D planner (``VerticalPlanner``), ``AscentStart`` and the 1-D
  release and staging maps

Every name the single-module ``phases.py`` of Phase 1 defined (private helpers
included) is re-exported here, so each ``from launchsim.phases import <name>`` of
Phase 1 keeps working. So are the launchsim names that module imported (from
``constants``, ``dynamics`` and ``vehicle``; they stay out of ``__all__``, which lists
the package's own names); the standard-library, numpy and scipy names it imported
(``math``, ``np``, ``solve_ivp``, ``OdeSolution``, typing and dataclass helpers) are
not, and are imported from their own modules. Pure: no I/O, no globals, no printing.
"""

# The launchsim names the Phase 1 ``phases.py`` imported, re-exported (redundant
# aliases) so ``from launchsim.phases import VERTICAL_LAYOUT`` and the like still work.
from launchsim.constants import R_EARTH_M as R_EARTH_M
from launchsim.dynamics import VERTICAL_LAYOUT as VERTICAL_LAYOUT
from launchsim.dynamics import VERTICAL_STATE_NAMES as VERTICAL_STATE_NAMES
from launchsim.dynamics import Gravity as Gravity
from launchsim.dynamics import StateLayout as StateLayout
from launchsim.dynamics import TrackParams as TrackParams
from launchsim.dynamics import VerticalParams as VerticalParams
from launchsim.dynamics import rhs_track as rhs_track
from launchsim.dynamics import rhs_vertical as rhs_vertical
from launchsim.dynamics import track_state_names as track_state_names
from launchsim.dynamics import track_to_vertical as track_to_vertical
from launchsim.phases.engine import (
    _ATOL_BY_SUFFIX,
    ATOL_J,
    ATOL_KG,
    ATOL_M,
    ATOL_MPS,
    ATOL_RAD,
    DEFAULT_METHOD,
    EVENT_ZERO_TOL,
    SAMPLE_GRID_REL_EPS,
    SUPPORTED_METHODS,
    ZERO_SPAN_S,
    EventFn,
    EventSpec,
    IntegratorSettings,
    PhaseResult,
    PhaseSpec,
    RhsFn,
    _already_past,
    _event_callable,
    _guard_value,
    _pass_through,
    _predict_state,
    _terminal_event_at,
    _would_fire,
    atol_for,
    ev_apex,
    ev_drive_limit,
    ev_impact,
    ev_liftoff,
    ev_propellant,
    ev_track_end,
    ev_turnaround,
    event_state,
    integrate_phase,
    is_lit,
    sample_grid,
)
from launchsim.phases.prelude import (
    _DEFAULT_IGNITION,
    IGNITION_REFERENCES,
    VERTICAL_PRELUDE,
    VERTICAL_TRACK_TOL_RAD,
    HoldParams,
    IgnitionSpec,
    PreludeLayout,
    TrackExit,
    check_layout,
    flag_ignored_ignition_settings,
    fly_track,
    hold_closed_form,
    hold_rhs_for,
    hold_until_liftoff,
    log_liftoff,
    max_step_cap,
    rhs_hold,
    track_params,
)
from launchsim.phases.trace import (
    ASCENT_KINDS,
    ASSIST_KIND,
    HOLD_KIND,
    MASS_COLUMN,
    MAX_PHASES_PER_RUN,
    RELEASE_LABEL,
    VERTICAL_MODEL,
    VERTICAL_VIEW,
    EventRecord,
    HoldSummary,
    RecordValues,
    RunTrace,
    StateView,
    TraceBuilder,
    VerticalView,
)
from launchsim.phases.vertical import (
    _IM,
    _IV,
    _IZ,
    END_KINDS,
    AscentStart,
    VerticalPlanner,
    map_release,
    map_staging,
)
from launchsim.vehicle import Startup as Startup
from launchsim.vehicle import ThrustSchedule as ThrustSchedule
from launchsim.vehicle import Vehicle as Vehicle
from launchsim.vehicle import propellant_burned_kg as propellant_burned_kg

__all__ = [
    "ASCENT_KINDS",
    "ASSIST_KIND",
    "ATOL_J",
    "ATOL_KG",
    "ATOL_M",
    "ATOL_MPS",
    "ATOL_RAD",
    "DEFAULT_METHOD",
    "END_KINDS",
    "EVENT_ZERO_TOL",
    "HOLD_KIND",
    "IGNITION_REFERENCES",
    "MASS_COLUMN",
    "MAX_PHASES_PER_RUN",
    "RELEASE_LABEL",
    "SAMPLE_GRID_REL_EPS",
    "SUPPORTED_METHODS",
    "VERTICAL_MODEL",
    "VERTICAL_PRELUDE",
    "VERTICAL_TRACK_TOL_RAD",
    "VERTICAL_VIEW",
    "ZERO_SPAN_S",
    "_ATOL_BY_SUFFIX",
    "_DEFAULT_IGNITION",
    "_IM",
    "_IV",
    "_IZ",
    "AscentStart",
    "EventFn",
    "EventRecord",
    "EventSpec",
    "HoldParams",
    "HoldSummary",
    "IgnitionSpec",
    "IntegratorSettings",
    "PhaseResult",
    "PhaseSpec",
    "PreludeLayout",
    "RecordValues",
    "RhsFn",
    "RunTrace",
    "StateView",
    "TraceBuilder",
    "TrackExit",
    "VerticalPlanner",
    "VerticalView",
    "_already_past",
    "_event_callable",
    "_guard_value",
    "_pass_through",
    "_predict_state",
    "_terminal_event_at",
    "_would_fire",
    "atol_for",
    "check_layout",
    "ev_apex",
    "ev_drive_limit",
    "ev_impact",
    "ev_liftoff",
    "ev_propellant",
    "ev_track_end",
    "ev_turnaround",
    "event_state",
    "flag_ignored_ignition_settings",
    "fly_track",
    "hold_closed_form",
    "hold_rhs_for",
    "hold_until_liftoff",
    "integrate_phase",
    "is_lit",
    "log_liftoff",
    "map_release",
    "map_staging",
    "max_step_cap",
    "rhs_hold",
    "sample_grid",
    "track_params",
]
