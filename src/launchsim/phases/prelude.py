"""The hold and track prelude shared by the planners: how and when stage 1 lights
(``IgnitionSpec``, built by ``resolve_ignition``, which converts a ramp start stated by
depth, speed or closed-form height to a time before the run; a height reached by an
altitude event stays a height, and the planners light stage 1 at that event after the
release), the hold-down (closed-form clamp and the liftoff extension) and the
track push up to the track exit (``fly_track`` -> ``TrackExit``), docs/physics.md,
"Phases and events" and "Silo model".

Every function is parameterised by the state layout of the flight model, so the 1-D
planner (``phases.vertical``) and later planners run the same prelude: a hold works on
any layout with ``m_kg`` (only the mass changes), and ``fly_track`` writes its hold
state and its track events through a ``PreludeLayout`` (``VERTICAL_PRELUDE`` for the
1-D model). The layout must be the one the builder's StateView reads (ValueError
otherwise), so a state is never recorded through the wrong model's columns. The track
state itself is the assist model's layout (``dynamics.rhs_track``).

Pure: no I/O, no globals, no printing. SI units; times are absolute run times [s] on
the internal clock (t = 0 at push start on a track or at hold-down release on a pad).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

import numpy as np
from scipy.optimize import brentq

from launchsim.assist.constant_accel import ConstantAccelAssist
from launchsim.assist.track import StraightTrack
from launchsim.config import (
    RAMP_START_DEPTH,
    RAMP_START_HEIGHT_CLOSED_FORM,
    RAMP_START_HEIGHT_EVENT,
    RAMP_START_SPEED,
    RAMP_START_TIME,
    RAMP_START_TRIGGERS,
)
from launchsim.dynamics import (
    VERTICAL_LAYOUT,
    VERTICAL_STATE_NAMES,
    StateLayout,
    TrackParams,
    rhs_track,
    track_state_names,
    track_to_vertical,
)
from launchsim.phases.engine import (
    ATOL_KG,
    ATOL_M,
    ZERO_SPAN_S,
    EventSpec,
    IntegratorSettings,
    PhaseResult,
    PhaseSpec,
    RhsFn,
    atol_for,
    ev_drive_limit,
    ev_liftoff,
    ev_propellant,
    ev_push_watch,
    ev_track_end,
    event_state,
    first_step_value,
    integrate_phase,
    is_lit,
    sample_grid,
)
from launchsim.phases.trace import ASSIST_KIND, HOLD_KIND, HoldSummary, TraceBuilder
from launchsim.vehicle import Startup, ThrustSchedule, Vehicle, propellant_burned_kg

if TYPE_CHECKING:
    from launchsim.assist.base import AssistModel, PushWatch, TrackGeometry
    from launchsim.config import IgnitionConfig, RunConfig

IGNITION_REFERENCES = ("release", "push_start")
"""What ``IgnitionSpec.t_ign_s`` counts from."""
TRIGGER_KEYS: dict[str, str] = {
    RAMP_START_DEPTH: "at_depth_m",
    RAMP_START_SPEED: "at_speed_mps",
    RAMP_START_HEIGHT_CLOSED_FORM: "at_height_m",
    RAMP_START_HEIGHT_EVENT: "at_height_m",
}
"""The config key that states each non-time ramp-start trigger (for messages)."""
IGNITION_HEIGHT_EVENT = "ignition_height"
"""Name of the altitude event (``engine.ev_altitude_up``) at which a first stage stated
by ``height_method: event`` lights: the root of altitude = track exit + h, crossed
upward on the coast after release."""
DRIVE_STALL = "drive_stall"
"""Run status of a push whose drive cannot start it (``AssistModel.stall_reason``: the
linear motor at its force limit and the thrust cannot lift the stack at push start); the
run stops on the track, like ``drive_limit``."""
RELEASE_TIE_M = 1e-9
"""A push on a drive whose push time is not exact (the linear motor) that stops within
this distance [m] of the track end, at a sub-phase boundary or a watch crossing, is
released there (``fly_track``); any farther short, it flies on to the track end. A solver
setting, not physics: small enough that a release it accepts is off the track-end state
by sddot / sdot x 1e-9 m in speed (below 1e-11 relative for the pushes the tests fly),
and above zero so that a sub-phase ending a rounding error short of L (a second flight
to the track-end root) is not followed by a closing sub-phase of a few ulps.
constant_accel keeps ATOL_M (SP1)."""
WATCH_LOOKAHEAD_REL = 1e-9
"""The step, as a fraction of the bound drive's push-time estimate (2.9e-9 s on the
tests' pushes), over which ``_arm_watches`` takes the change of a drive watch's value
that is at zero, or a hair past it, at a sub-phase start, when no crossing has just set
the watch's side (a Heun step, ``engine.first_step_value``): a rate test, which way the
value moves from t0, not where rule 3's first step (first_step_s, 1 ms) would put it,
which passed over a power cap binding for 0.28 ms and looped the planner (review pass 3,
P3-M1). A solver setting, not physics: short, so that a limit binding or released for
longer than it is judged right, and long enough that a moving watch's change over it
stands clear of rounding (at the restarts of the tests' brief power cap, 4e-8 to 2e-7
m/s, 3e-2 to 1.3e-1 N and 2e-7 m, 3e6 to 3.5e7 times the spacing of the doubles the
values come from; measured). A briefer binding is not lost: its events are armed guarded
(``_guarded``) and the watch whose side was just set is not judged again
(``_WatchBook``). ``_passed_over`` reads a watch's rate over the same look-ahead at the
step ends of a flight, to find a binding inside one step."""
WATCH_TOGGLES_PER_INSTANT = 2
"""The most times one drive watch may change side (start or stop binding) at one instant
(within ZERO_SPAN_S of its last change): a touch, the limit starting and stopping at
once. A watch whose side was just set is not judged again while its value stays in its
zero band, and its next event is armed guarded, so a third change would need the value
to cross the band twice more within ZERO_SPAN_S; ``fly_track`` raises RuntimeError (a
planner bug) instead of looping."""
EVENT_ROOT_TOL = 4.0 * float(np.finfo(float).eps)
"""The relative and absolute tolerance [s, and relative] of the root ``_passed_over``
finds for a crossing scipy's flight passed over: scipy's own for an event root
(``solve_ivp``'s brentq on the step's interpolant, 4 machine epsilons), so that root is
placed as scipy places a crossing it sees."""
VERTICAL_TRACK_TOL_RAD = 1e-12
"""|phi - pi/2| within which a track exit counts as vertical: ``map_release`` refuses
any other angle (the 1-D map is exact only for a vertical track; the planar branch
carries the rest), and ``fly_track`` reports the downrange offset of a vertical
``StraightTrack``'s exit as exactly 0."""


# ------------------------------------------------------------------------- ignition


@dataclass(frozen=True)
class IgnitionSpec:
    """How and when one stage lights, on the internal clock (t = 0 at push start on a
    track or at hold-down release on a pad).

    t_ign_s: ignition time [s] counted from ``reference``: "release" (first stage: track
    exit or hold-down release, t_release; later stages: the end of their staging coast)
    or "push_start" (t = 0 of a track run; first stage only, a pad has no push).
    startup: a Startup overriding the stage's own shape, or None to keep it. fails: the
    engines never light (T identically 0). trigger_kind: how the config stated the ramp
    start (``config.RampStartTrigger``: "time", or "depth", "speed" or
    "height_closed_form", which ``resolve_ignition`` has already converted to the
    t_ign_s and reference above, or "height_event"); trigger_value: the requested depth
    [m], speed [m/s] or height [m] of a non-time trigger, None for "time". For the
    converted triggers the two are a record of the request for the metrics and
    messages: every consumer of such a spec reads t_ign_s and reference only, and their
    defaults leave every time-stated spec as it was (equal and hashing alike).
    "height_event" is not a time (``lights_at_height``): the stage lights at the
    altitude event track exit + trigger_value after the release, which the planner
    finds in flight; t_ign_s and reference keep their defaults (0.0, "release"; any
    other value is refused) and are not read, and ``t_ign_abs_s`` refuses such a spec.
    Built from ``config.IgnitionConfig`` at the boundary by ``resolve_ignition``
    (``from_config`` for the time family only).
    """

    t_ign_s: float = 0.0
    reference: str = "release"
    startup: Startup | None = None
    fails: bool = False
    trigger_kind: str = RAMP_START_TIME
    trigger_value: float | None = None

    def __post_init__(self) -> None:
        if self.reference not in IGNITION_REFERENCES:
            raise ValueError(f"reference must be one of {IGNITION_REFERENCES}")
        if self.trigger_kind not in RAMP_START_TRIGGERS:
            raise ValueError(f"trigger_kind must be one of {RAMP_START_TRIGGERS}")
        if (self.trigger_kind == RAMP_START_TIME) != (self.trigger_value is None):
            raise ValueError(
                "trigger_value is the requested depth, speed or height of a non-time "
                "trigger, and None for a time trigger"
            )
        if self.lights_at_height and (
            self.t_ign_s != _TIME_DEFAULTS[0] or self.reference != _TIME_DEFAULTS[1]
        ):
            raise ValueError(
                "a height_event spec lights at an altitude event, not at a time: t_ign_s "
                f"and reference keep their defaults {_TIME_DEFAULTS}"
            )
        if self.lights_at_height and not (
            self.trigger_value is not None and math.isfinite(self.trigger_value)
        ):
            raise ValueError("a height_event spec needs a finite height trigger_value [m]")

    @property
    def lights_at_height(self) -> bool:
        """True when the stage lights at the altitude event of ``height_method: event``
        (trigger_kind "height_event") rather than at a time."""
        return self.trigger_kind == RAMP_START_HEIGHT_EVENT

    @classmethod
    def from_config(cls, cfg: IgnitionConfig, base_startup: Startup) -> IgnitionSpec:
        """Spec from a validated IgnitionConfig whose ramp start is stated by time
        (t_ign_s, reference); the startup override is resolved against the stage's own
        Startup (None when the config gives no override). Raises ValueError for a ramp
        start stated by depth, speed or height, which only ``resolve_ignition`` can
        convert (it needs the run's assist model, track and g_eff): read here, its
        defaults would silently light the stage at the release."""
        kind = cfg.ramp_start[0]
        if kind != RAMP_START_TIME:
            raise ValueError(
                f"IgnitionSpec.from_config takes a ramp start stated by time; one stated by "
                f"{TRIGGER_KEYS[kind]} is converted by phases.prelude.resolve_ignition"
            )
        return cls(cfg.t_ign_s, cfg.reference, _startup_override(cfg, base_startup), cfg.fails)

    def t_ign_abs_s(self, t_release_s: float, t_push_start_s: float = 0.0) -> float:
        """Absolute ignition time [s] of a first stage: t_release + t_ign_s for reference
        "release", t_push_start + t_ign_s for "push_start". Raises ValueError for a spec
        that lights at the altitude event (``lights_at_height``), which has no time
        before the flight finds it."""
        if self.lights_at_height:
            raise ValueError(
                "this stage lights at the altitude event of height_method: event, which "
                "the planner finds in flight; it has no ignition time before that"
            )
        origin = t_release_s if self.reference == "release" else t_push_start_s
        return origin + self.t_ign_s


_TIME_DEFAULTS: tuple[float, str] = (IgnitionSpec.t_ign_s, IgnitionSpec.reference)
"""The (t_ign_s, reference) field defaults of IgnitionSpec (0.0, "release"), which a
height_event spec keeps (they are not read for it)."""
_DEFAULT_IGNITION = IgnitionSpec()
"""The field defaults of IgnitionSpec, the reference for "set away from the default"."""


def _startup_override(cfg: IgnitionConfig, base_startup: Startup) -> Startup | None:
    """The config's startup override resolved against the stage's own Startup, None
    when the config gives no override."""
    return None if cfg.startup is None else cfg.resolved_startup(base_startup)


def resolve_stage_ignitions(
    run_config: RunConfig,
    vehicle: Vehicle,
    assist: AssistModel | None,
    track: TrackGeometry | None,
    g_eff_mps2: float,
) -> dict[str, IgnitionSpec]:
    """One IgnitionSpec per stage of ``vehicle`` from the run's ignition block (the
    defaults when a stage has none), each through ``resolve_ignition`` with the run's
    assist model, its track and the track's g_eff [m/s^2]: the spec build of both
    build sites (``sim.ignition_specs`` and ``search.SearchContext.from_run``). Raises
    ValueError for a ramp start stated by depth, speed or height on a stage after the
    first, which ignites at t_ign_s >= 0 after its staging coast (a conversion would
    read stage 1's push and track exit; ``config.resolve_run`` refuses it too, and this
    covers a RunConfig validated without it), and wherever ``resolve_ignition``
    refuses a conversion."""
    specs: dict[str, IgnitionSpec] = {}
    for k, stage in enumerate(vehicle.stages):
        cfg = run_config.ignition_for(stage.name)
        kind = cfg.ramp_start[0]
        if k > 0 and kind != RAMP_START_TIME:
            raise ValueError(
                f"ignition {stage.name}: a ramp start by {TRIGGER_KEYS[kind]} is only for "
                "the first stage (a later stage ignites at t_ign_s >= 0 after its staging "
                "coast)"
            )
        specs[stage.name] = resolve_ignition(cfg, stage.startup, assist, track, g_eff_mps2)
    return specs


def resolve_ignition(
    cfg: IgnitionConfig,
    startup: Startup,
    assist: AssistModel | None,
    track: TrackGeometry | None,
    g_eff_mps2: float,
) -> IgnitionSpec:
    """The IgnitionSpec of one stage from its validated IgnitionConfig, with a ramp
    start stated by depth, speed or closed-form height converted to the (t_ign_s,
    reference) pair before anything is integrated (docs/physics.md, "Silo model",
    ramp-start conversions), and one stated by a height reached by an altitude event
    (``height_method: event``) kept as that height for the planners. The one resolver
    of both spec build sites (``sim.ignition_specs`` and
    ``search.SearchContext.from_run``, through ``resolve_stage_ignitions``, which also
    refuses a non-time trigger on a later stage).

    Inputs: cfg, the stage's IgnitionConfig; startup, the stage's own Startup (the
    config's override is resolved against it); assist and track, the run's assist
    model and its track (None, None or NoAssist for a pad); g_eff_mps2, the track's
    constant effective gravity g_eff = mu/R_E^2 - omega_p^2 R_E [m/s^2] (the value the
    planner hands ``fly_track``). Output: the spec. A time-stated config gives
    ``IgnitionSpec.from_config`` unchanged. Otherwise, with the stroke L [m], the net
    acceleration a [m/s^2], v_e = sqrt(2 a L) and t_push = sqrt(2 L / a) of the
    ``constant_accel`` drive (``_ramp_start_time``): depth d below the track exit (along
    the track: the depth on a vertical track) -> t = sqrt(2 (L - d) / a) from push
    start (``push_time_s(L - d)``); speed v on the push -> t = v / a from push start
    (``time_to_speed_s``); height h above the exit, closed form -> dt = (v_e -
    sqrt(v_e^2 - 2 g_eff h)) / g_eff after release (the drag-free constant-g_eff coast;
    exact only there). A result within ZERO_SPAN_S of the release snaps to (0,
    "release"). A height by event is not converted: the spec is (0.0, "release") with
    trigger "height_event" (``IgnitionSpec.lights_at_height``), refused like the
    closed form when h lies at or above the drag-free apex v_e^2 / (2 g_eff). That
    preflight bound is the apex of a drag-free coast at the constant g_eff, not the
    flown apex, and it is conservative only for a coast without drag: under mu/r^2
    such a coast peaks slightly higher (about 1.4 cm on the 3 g0, 100 m silo), so on
    vertical_1d the event method also refuses that thin band of reachable heights.
    With drag (every planar_2d run) it is permissive: the flown apex is lower (about
    0.41 m on the gate fork at its file payload), and a height between it and the
    bound resolves but never lights, which the planner reports in flight
    (GuidanceFailure "no_ignition"). The spec records the request
    (trigger_kind, trigger_value). Raises ValueError for a non-time trigger without the
    ``constant_accel`` drive and its track (the conversion is exact only for a
    prescribed acceleration, and the apex check needs v_e), for d > L, for a speed
    whose time v / a lies more than ZERO_SPAN_S after the release (v > v_e), for h at
    or above the drag-free apex v_e^2 / (2 g_eff) by either height method, and for
    g_eff <= 0 with a height. Frame: the flat track frame; times on the internal clock
    (t = 0 at push start)."""
    kind, value = cfg.ramp_start
    if kind == RAMP_START_TIME or value is None:
        return IgnitionSpec.from_config(cfg, startup)
    key = TRIGGER_KEYS[kind]
    if not isinstance(assist, ConstantAccelAssist) or track is None:
        name = "none" if assist is None else assist.name
        raise ValueError(
            f"a ramp start by {key} needs the constant_accel drive and its track (assist "
            f"model {name!r}): the conversion to a time is exact only for a prescribed "
            "acceleration (a force-limited drive's push is known only once it is flown)"
        )
    override = _startup_override(cfg, startup)
    if kind == RAMP_START_HEIGHT_EVENT:
        _drag_free_exit_speed(value, assist, track, g_eff_mps2)
        return IgnitionSpec(*_TIME_DEFAULTS, override, cfg.fails, kind, value)
    t_ign, reference = _ramp_start_time(kind, value, assist, track, g_eff_mps2)
    return IgnitionSpec(t_ign, reference, override, cfg.fails, kind, value)


def _drag_free_exit_speed(
    height_m: float, assist: ConstantAccelAssist, track: TrackGeometry, g_eff_mps2: float
) -> float:
    """The exit speed v_e = sqrt(2 a L) [m/s] of the constant_accel push on track, after
    checking that a height height_m [m] above the track exit lies below the drag-free
    apex v_e^2 / (2 g_eff) of the coast after release (g_eff [m/s^2], the track's
    constant). Raises ValueError for g_eff <= 0 and for a height at or above that apex,
    by either height method. For the closed form the bound is where its root ceases to
    exist; for the event method it is a preflight bound, the apex of a drag-free coast
    at constant g_eff, conservative only for a coast without drag (one under mu/r^2
    exceeds it slightly: vertical_1d) and permissive with drag (every planar_2d run:
    the flown apex lies below it, and a height between the two fails in flight with
    GuidanceFailure "no_ignition"; docs/physics.md, "Silo model", the height by
    event)."""
    if not g_eff_mps2 > 0.0:
        raise ValueError(f"a ramp start by height needs g_eff > 0, got {g_eff_mps2:g}")
    v_e = assist.exit_speed_mps(track.length_m)
    apex = v_e * v_e / (2.0 * g_eff_mps2)
    if height_m >= apex:
        raise ValueError(
            f"at_height_m {height_m:g} m is at or above the drag-free apex v_e^2 / "
            f"(2 g_eff) = {apex:.9g} m of the coast after release (v_e = {v_e:.9g} "
            f"m/s, g_eff = {g_eff_mps2:.9g} m/s^2)"
        )
    return v_e


def _ramp_start_time(
    kind: str,
    value: float,
    assist: ConstantAccelAssist,
    track: TrackGeometry,
    g_eff_mps2: float,
) -> tuple[float, str]:
    """(t_ign_s [s], reference) of a ramp start by depth, speed or closed-form height on
    the constant_accel drive (see ``resolve_ignition`` for the closed forms, the snap
    and the refusals): value is the depth [m], speed [m/s] or height [m] of trigger
    ``kind``."""
    length = track.length_m
    t_push = assist.push_time_estimate(track)
    if kind == RAMP_START_DEPTH:
        if value > length:
            raise ValueError(f"at_depth_m {value:g} m is deeper than the track (L = {length:g} m)")
        t, reference = assist.push_time_s(length - value), "push_start"
    elif kind == RAMP_START_SPEED:
        t, reference = assist.time_to_speed_s(value), "push_start"
        if t > t_push + ZERO_SPAN_S:
            raise ValueError(
                f"at_speed_mps {value:g} m/s exceeds the exit speed "
                f"{assist.exit_speed_mps(length):.9g} m/s: the push never reaches it"
            )
    else:  # RAMP_START_HEIGHT_CLOSED_FORM
        v_e = _drag_free_exit_speed(value, assist, track, g_eff_mps2)
        # (v_e - sqrt(v_e^2 - 2 g h)) / g, rationalised: no cancellation at small h
        t = 2.0 * value / (v_e + math.sqrt(v_e * v_e - 2.0 * g_eff_mps2 * value))
        reference = "release"
    after_release = t - t_push if reference == "push_start" else t
    if abs(after_release) <= ZERO_SPAN_S:
        return 0.0, "release"
    return t, reference


def ramp_start_assumption(spec: IgnitionSpec, g_eff_mps2: float) -> str | None:
    """The assumption line of a first stage whose ramp start the config stated by
    depth, speed or height (``resolve_ignition``): the request, the converted time and
    the closed form behind it (for the closed-form height also the track's constant
    g_eff [m/s^2] it used, and that the flown coast reaches a slightly different
    height, recorded by the ignition event); for a height reached by the altitude event,
    that nothing is converted and stage 1 lights at the event root on the flown coast.
    None for a time-stated or a failed stage (whose settings
    ``flag_ignored_ignition_settings`` flags)."""
    if spec.fails or spec.trigger_kind == RAMP_START_TIME:
        return None
    if spec.lights_at_height:
        return (
            f"ramp start: stage-1 ignition stated by height {spec.trigger_value:g} m above "
            "the track exit, reached by an altitude event: nothing is converted before the "
            "run; stage 1 lights at the root where the flown coast after release (mu/r^2, "
            "and on planar_2d drag and rotation) crosses that height upward (an apex below "
            "it is a failure, not an ignition)"
        )
    when = "after push start" if spec.reference == "push_start" else "after release"
    converted = f"converted before the run to t_ign = {spec.t_ign_s:.9g} s {when}"
    value = spec.trigger_value
    if spec.trigger_kind == RAMP_START_DEPTH:
        return (
            f"ramp start: stage-1 ignition stated by depth {value:g} m below the track "
            f"exit, {converted} by t = sqrt(2 (L - d) / a) (exact for the prescribed "
            "acceleration)"
        )
    if spec.trigger_kind == RAMP_START_SPEED:
        return (
            f"ramp start: stage-1 ignition stated by speed {value:g} m/s on the push, "
            f"{converted} by t = v / a (exact for the prescribed acceleration)"
        )
    return (
        f"ramp start: stage-1 ignition stated by height {value:g} m above the track exit, "
        f"{converted} by the closed form of a drag-free coast at the track's constant "
        f"g_eff = {g_eff_mps2:.7g} m/s^2, dt = (v_e - sqrt(v_e^2 - 2 g_eff h)) / g_eff; "
        "the flown coast (mu/r^2, and on planar_2d drag and rotation) reaches a slightly "
        "different height, which the ignition event records"
    )


def flag_ignored_ignition_settings(tr: TraceBuilder, stage_name: str, spec: IgnitionSpec) -> None:
    """A failed stage (``spec.fails``) never lights, so its t_ign_s, reference and
    startup override play no part; any of them set away from the IgnitionSpec
    field defaults (``_DEFAULT_IGNITION``) is recorded as a run flag so a config
    that combines them with ``fails: true`` is not misread as a hot start that then
    failed. A ramp start stated by depth, speed or height is flagged by its config key
    and value instead of the t_ign_s and reference it was converted to. No flag for a
    stage that lights."""
    if not spec.fails:
        return
    ignored: list[str] = []
    if spec.trigger_kind != RAMP_START_TIME:
        ignored.append(f"{TRIGGER_KEYS[spec.trigger_kind]} = {spec.trigger_value:g}")
    else:
        if spec.t_ign_s != _DEFAULT_IGNITION.t_ign_s:
            ignored.append(f"t_ign_s = {spec.t_ign_s:g}")
        if spec.reference != _DEFAULT_IGNITION.reference:
            ignored.append(f"reference = {spec.reference!r}")
    if spec.startup is not _DEFAULT_IGNITION.startup:
        ignored.append("the startup override")
    if ignored:
        tr.flags.append(
            f"ignition_failed: stage {stage_name!r} has fails: true, so nothing burns; "
            f"ignored: {', '.join(ignored)}"
        )


def check_layout(tr: TraceBuilder, layout: StateLayout, caller: str) -> None:
    """Raise ValueError unless the builder's StateView reads ``layout``: the prelude
    logs its phases and events in that layout, and a state recorded through another
    model's view would be written into the wrong columns without complaint. caller
    names the prelude function for the message."""
    if tr.view.layout != layout:
        raise ValueError(
            f"{caller}: the prelude runs in the layout {layout.names}, but the trace's "
            f"{tr.view.model} view reads {tr.view.layout.names}"
        )


def max_step_cap(schedule: ThrustSchedule | None, t: float, settings: IntegratorSettings) -> float:
    """Step cap [s] at time t [s]: t_ramp / ramp_steps inside a ramp, tau /
    lag_steps_per_tau during a lag burn, unbounded (math.inf) otherwise (no schedule,
    or a failed ignition)."""
    if schedule is None or schedule.fails:
        return math.inf
    kind = schedule.startup.effective_kind
    if kind == "ramp":
        t_r = schedule.startup.t_ramp_s
        if t < schedule.t_ign_abs_s + t_r:
            return t_r / settings.ramp_steps
        return math.inf
    if kind == "lag":
        return schedule.startup.tau_s / settings.lag_steps_per_tau
    return math.inf


# ----------------------------------------------------------------------------- hold


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


_IM = VERTICAL_LAYOUT.index("m_kg")


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


def hold_rhs_for(layout: StateLayout) -> RhsFn:
    """The HOLD right-hand side for a state layout: ``rhs_hold`` itself for
    VERTICAL_LAYOUT, else the same law (only ``m_kg`` changes, dm/dt = -T_vac(t)/c
    while lit; every other entry, positions, velocities and quadratures alike, is 0)
    on that layout. Inputs of the returned function: t [s], y (layout order),
    HoldParams; output dy/dt (layout order). Frame: the pad, Earth-fixed: every row
    but the mass is held, so a planar hold keeps its release-datum values (theta = 0
    and v_theta = omega_p R_E stay constant; theta does not advance at omega_p, per the
    Phase 2 datum), and no gravity loss accrues."""
    if layout == VERTICAL_LAYOUT:
        return rhs_hold
    i_m = layout.index("m_kg")
    n = len(layout)

    def rhs(t: float, y: np.ndarray, p: HoldParams) -> np.ndarray:
        dy = np.zeros(n)
        if p.lit:
            dy[i_m] = -p.schedule.mass_flow_kgps(t)
        return dy

    return rhs


def hold_closed_form(
    tr: TraceBuilder,
    params: HoldParams,
    t0: float,
    t1: float,
    y: np.ndarray,
    *,
    vehicle: Vehicle,
    settings: IntegratorSettings,
    layout: StateLayout = VERTICAL_LAYOUT,
) -> tuple[np.ndarray, float]:
    """Clamp the vehicle from t0 to t1 [s]: every entry but the mass is held, the mass
    follows ``propellant_burned_kg`` in closed form (no ODE; constant while
    ``params.lit`` is False), sampled at settings.sample_dt_s. Only the burn between t0
    and t1 is subtracted from y's mass, so the segment may start any time after
    ignition (a lit hold split into several calls gives the single-call result). y is
    in ``layout`` order, which must be the layout tr.view reads (ValueError otherwise).
    Returns the state at t1 and the minimum hold-down force [N] over the samples.
    Raises ValueError if the first stage's propellant runs out by t1."""
    check_layout(tr, layout, "hold_closed_form")
    i_m = layout.index("m_kg")
    stage = vehicle.stages[0]
    m0 = float(y[i_m])
    m_dry = vehicle.stack_dry_mass_kg(0)

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
    ts = np.concatenate(([t0], sample_grid(t0, t1, settings.sample_dt_s), [t1]))
    ys = np.repeat(y.reshape(-1, 1), len(ts), axis=1)
    ys[i_m] = [m0 - (burned(float(t)) - burned_t0) for t in ts]
    spec = PhaseSpec(HOLD_KIND, 0, t0, t1, hold_rhs_for(layout), params, (), atol_for(layout.names))
    res = PhaseResult(spec, ts, ys, None, "t_end", t1, ys[:, -1].copy())
    tr.add_phase(res)
    force_min = min(
        params.hold_down_force_N(float(t), float(m)) for t, m in zip(ts, ys[i_m], strict=True)
    )
    return res.y_end, force_min


def hold_until_liftoff(
    tr: TraceBuilder,
    params: HoldParams,
    t0: float,
    y: np.ndarray,
    *,
    vehicle: Vehicle,
    settings: IntegratorSettings,
    layout: StateLayout = VERTICAL_LAYOUT,
) -> tuple[float, np.ndarray, float]:
    """Keep a vehicle at rest on the ground clamped past t0 until its thrust exceeds
    its weight.

    Inputs: the builder; params (the schedule, the pad's g_eff [m/s^2] and pressure
    [Pa] that set the balance T(t) - m g_eff); t0 [s]; y, the state (``layout`` order,
    the layout tr.view reads: ValueError otherwise); the vehicle and settings. If
    T(t0) >= m g_eff already, returns (t0, y, m g_eff - T) at once. Otherwise the hold
    is split at the thrust kinks up to t0 + t_max_s. A sub-phase before the ignition
    kink is unlit (T = 0; the state is constant; sampled directly, no events). At the
    start of every lit sub-phase the balance is re-evaluated with the lit schedule, so
    a step whose thrust exceeds the weight lifts off exactly at its kink: no root
    search across the discontinuity, and no mass bias from the integrator's last stage
    seeing the step's f(0) = 1. A lit sub-phase
    integrates the mass alone (``hold_rhs_for(layout)``) with the liftoff and propellant
    events. An ignition inside the extension is logged (in the HOLD); liftoff records
    the extension as an assumption; propellant exhaustion raises ValueError; no liftoff
    by t_max sets tr.status = "no_liftoff" and a flag. Returns (liftoff time [s],
    state, minimum hold-down force [N] over the extension).
    """
    check_layout(tr, layout, "hold_until_liftoff")
    i_m = layout.index("m_kg")
    g = params.g_eff_mps2
    schedule = params.schedule
    force0 = params.hold_down_force_N(t0, float(y[i_m]))
    if force0 <= ATOL_KG * g:
        return t0, y, force0
    stage = vehicle.stages[0]
    m_dry = vehicle.stack_dry_mass_kg(0)
    t_max = t0 + settings.t_max_s
    kinks = [k for k in schedule.kink_times() if t0 < k < t_max]
    t = t0
    force_min = force0
    atol = atol_for(layout.names)
    for t_b in sorted({t_max, *kinks}):
        lit = is_lit(schedule, t)
        if not lit:
            unlit = HoldParams(schedule, g, params.p_amb_pa, lit=False)
            y, f_min = hold_closed_form(
                tr, unlit, t, t_b, y, vehicle=vehicle, settings=settings, layout=layout
            )
            t = t_b
            force_min = min(force_min, f_min)
            continue
        if not tr.has_event("ignition", 0):
            tr.add_event("ignition", schedule.t_ign_abs_s, HOLD_KIND, 0, y)
        force = params.hold_down_force_N(t, float(y[i_m]))
        force_min = min(force_min, force)
        if force <= ATOL_KG * g:
            return log_liftoff(tr, t, y, force_min)
        spec = PhaseSpec(
            HOLD_KIND,
            0,
            t,
            t_b,
            hold_rhs_for(layout),
            params,
            (
                ev_liftoff(schedule, g, params.p_amb_pa, layout),
                ev_propellant(m_dry, layout),
            ),
            atol,
            max_step_cap(schedule, t, settings),
        )
        res = tr.add_phase(integrate_phase(spec, y, settings))
        t, y = res.t_end, res.y_end
        forces = [
            params.hold_down_force_N(float(ti), float(mi))
            for ti, mi in zip(res.t, res.y[i_m], strict=True)
        ]
        force_min = min(force_min, *forces)
        if res.ended_by == "propellant":
            raise ValueError(
                f"stage {stage.name!r} exhausted its propellant at t = {t:.6g} s while held "
                "down waiting for liftoff (thrust below weight)"
            )
        if res.ended_by == "liftoff":
            return log_liftoff(tr, t, y, force_min)
    tr.status = "no_liftoff"
    tr.flags.append(
        f"no_liftoff: thrust never exceeded the weight by t_max = {settings.t_max_s:.6g} s"
    )
    return t, y, force_min


def log_liftoff(
    tr: TraceBuilder, t: float, y: np.ndarray, force_min: float
) -> tuple[float, np.ndarray, float]:
    """Log the liftoff at t [s] (state y) that ends an extended hold, record the
    extension as an assumption, and return (t, y, force_min [N])."""
    tr.add_event("liftoff", t, HOLD_KIND, 0, y)
    tr.assumptions.append(f"hold extended to t = {t:.6g} s for liftoff (TWR < 1 at release)")
    return t, y, force_min


# ---------------------------------------------------------------------------- track


def _vertical_hold_state(z_m: float, m_kg: float) -> np.ndarray:
    """A VERTICAL_LAYOUT state at rest at altitude z_m [m] with mass m_kg [kg]."""
    return VERTICAL_LAYOUT.build(z_m=z_m, m_kg=m_kg)


@dataclass(frozen=True)
class PreludeLayout:
    """How the track prelude writes states for a flight model.

    layout: the model's state layout (the hold before the push integrates in it, and
    the track events are logged in it); hold_state(z_m, m_kg): the state of a vehicle
    clamped at rest at altitude z_m [m] (datum frame) with mass m_kg [kg];
    from_track(y_track, params): the model-layout view of a track state (TrackParams
    of the sub-phase) for event logging.
    """

    layout: StateLayout
    hold_state: Callable[[float, float], np.ndarray]
    from_track: Callable[[np.ndarray, TrackParams], np.ndarray]


VERTICAL_PRELUDE = PreludeLayout(VERTICAL_LAYOUT, _vertical_hold_state, track_to_vertical)
"""The 1-D prelude layout: VERTICAL_LAYOUT states, track events through
``dynamics.track_to_vertical``."""


@dataclass(frozen=True, eq=False)
class TrackExit:
    """The vehicle at the track exit (the release), in the track frame.

    t_release_s: the track-end root [s] (absolute); y_track: the track state there (the
    assist model's layout); sdot_mps: speed along the track [m/s]; m_kg: vehicle mass
    [kg] (the carriage stays); phi_rad: track angle above horizontal at the exit [rad];
    x_exit_m: downrange offset of the exit from the track start [m] for a
    ``StraightTrack`` (0 for a vertical one, L cos phi for a tilted one), None for any
    other geometry (the TrackGeometry protocol has no x(s) until Phase 3; the 1-D
    release map does not use it, and a map that needs it must refuse None); z_exit_m:
    exit altitude in the +z-up datum frame [m] (start altitude + z(L)).
    """

    t_release_s: float
    y_track: np.ndarray
    sdot_mps: float
    m_kg: float
    phi_rad: float
    x_exit_m: float | None
    z_exit_m: float


def track_params(
    assist: AssistModel,
    track: TrackGeometry,
    schedule: ThrustSchedule,
    t: float,
    g_eff_mps2: float,
    p_amb_pa: float,
) -> TrackParams:
    """TrackParams of the track sub-phase starting at t [s]: lit once the ignition time
    has passed (never for a failed ignition); g_eff [m/s^2] and the ambient pressure
    [Pa] of the track."""
    lit = is_lit(schedule, t)
    return TrackParams(
        track=track,
        assist=assist,
        carriage_mass_kg=assist.carriage_mass_kg,
        g_eff_mps2=g_eff_mps2,
        schedule=schedule,
        p_amb_pa=p_amb_pa,
        lit=lit,
    )


def _exit_x_m(track: TrackGeometry) -> float | None:
    """Downrange offset [m] of the track exit, track frame: for a ``StraightTrack`` 0
    for a vertical exit (within VERTICAL_TRACK_TOL_RAD), else L cos phi; None for any
    other geometry, because the TrackGeometry protocol has no x(s) and L cos phi(L)
    would be silently wrong for a curved track (Phase 3 adds x(s)). Only a release map
    that needs the offset refuses None; the 1-D map reads phi(L) and z(L) alone."""
    if not isinstance(track, StraightTrack):
        return None
    phi = track.phi(track.length_m)
    if abs(phi - 0.5 * math.pi) <= VERTICAL_TRACK_TOL_RAD:
        return 0.0
    return track.length_m * math.cos(phi)


def pending_until_release(spec: IgnitionSpec, assist: AssistModel | None) -> bool:
    """Whether a first stage's ignition stays pending through the push and is resolved
    at the flown release, t_release + t_ign_s (D-SP7-25): a lit, release-referenced
    time on a drive whose push time is not exact (``AssistModel.push_time_exact`` False:
    the linear motor). Such an ignition at t_ign_s < 0 (on the track) cannot be placed
    before the push is flown: ValueError (``config.resolve_run`` refuses it when the
    experiment resolves). False for a pad (assist None), an exact drive, a push_start
    reference, a failed stage and a height reached by the altitude event."""
    if assist is None or assist.push_time_exact or spec.fails or spec.lights_at_height:
        return False
    if spec.reference != "release":
        return False
    if spec.t_ign_s < 0.0:
        raise ValueError(
            f"a release-referenced t_ign_s {spec.t_ign_s:g} s (lit on the track) is refused on "
            f"the {assist.name} drive, whose push time is known only once the push is flown; "
            "state it with reference push_start"
        )
    return True


def thrust_clamp_time(schedule: ThrustSchedule, p_amb_pa: float) -> float | None:
    """The absolute time [s] at which the delivered thrust max(0, T_vac - p_amb A_e)
    leaves its clamp at zero during a ramp or lag start, where T_vac(t) = p_amb A_e: a
    C0 kink of the delivered thrust that ``ThrustSchedule.kink_times`` does not list.
    With share = p_amb A_e/T_full: ramp t_ign + t_ramp share; lag t_ign - tau ln(1 -
    share). None for a step start (the thrust jumps at the ignition kink), a failed
    schedule, share <= 0 (no clamp: vacuum) and share >= 1 (the delivered thrust is zero
    throughout). Inputs: the stage's schedule (absolute clock) and the ambient pressure
    [Pa]."""
    if schedule.fails or schedule.thrust_vac_total_N <= 0.0:
        return None
    share = p_amb_pa * schedule.exit_area_total_m2 / schedule.thrust_vac_total_N
    if not 0.0 < share < 1.0:
        return None
    startup = schedule.startup
    kind = startup.effective_kind
    if kind == "ramp":
        return schedule.t_ign_abs_s + startup.t_ramp_s * share
    if kind == "lag":
        return schedule.t_ign_abs_s - startup.tau_s * math.log1p(-share)
    return None


def push_boundaries(
    thrust_kinks: Sequence[float],
    drive_kinks: Sequence[tuple[str, float]],
    t_push_start_s: float,
    thrust_clamp_s: float | None = None,
) -> list[float]:
    """The sub-phase boundaries [s] of a push: the thrust kinks (``ThrustSchedule.
    kink_times``), the drive's own kink times (``AssistModel.kink_times``, (name, time)
    pairs) and the delivered thrust's clamp time thrust_clamp_s [s] (``thrust_clamp_time``;
    None: not split) after the push start t_push_start_s [s] (by more than ZERO_SPAN_S),
    sorted; a drive kink or the clamp within ZERO_SPAN_S of a kink already listed is not
    repeated. With no drive kink and no clamp the list is the thrust kinks' alone, as
    before SP7."""
    after = t_push_start_s + ZERO_SPAN_S
    kinks = sorted(k for k in thrust_kinks if k > after)
    extra = [t_k for _name, t_k in drive_kinks]
    if thrust_clamp_s is not None:
        extra.append(thrust_clamp_s)
    for t_k in extra:
        if t_k > after and all(abs(t_k - k) > ZERO_SPAN_S for k in kinks):
            kinks.append(t_k)
    return sorted(kinks)


def fly_track(
    tr: TraceBuilder,
    assist: AssistModel,
    track: TrackGeometry,
    spec: IgnitionSpec,
    *,
    vehicle: Vehicle,
    settings: IntegratorSettings,
    g_eff_mps2: float,
    p_amb_pa: float,
    prelude: PreludeLayout = VERTICAL_PRELUDE,
) -> TrackExit | None:
    """The track prelude: t = 0 at push start, up to the release at the track end
    (docs/physics.md, "Silo model").

    Inputs: the builder (t_ign_abs_s and flags are written here); the assist model and
    its track; spec, the first stage's IgnitionSpec; the vehicle and settings; g_eff
    [m/s^2] and the ambient pressure [Pa] of the track; prelude, the flight model's
    layout (VERTICAL_PRELUDE for the 1-D model; it must be the layout tr.view reads,
    ValueError otherwise). Any TrackGeometry is accepted; the exit's downrange offset is
    known only for a ``StraightTrack`` (``TrackExit.x_exit_m`` is None otherwise). The
    first stage's ignition time resolves, on a drive whose push time is exact
    (``push_time_exact``: the prescribed-acceleration drive), against the model's
    push-time estimate for reference ``release`` and against t = 0 for ``push_start`` (a
    ramp start the config stated by depth, speed or closed-form height arrives here
    already converted to that pair, ``resolve_ignition``, and adds its
    ``ramp_start_assumption`` line to tr.assumptions). A first stage that lights at the
    altitude event (``IgnitionSpec.lights_at_height``) or, on a drive whose push time is
    not exact (the linear motor), at a release-referenced t_ign_s >= 0
    (``pending_until_release``; t_ign_s < 0 raises ValueError) is a pending ignition
    with no time yet: the push runs unlit, on the schedule of a failed ignition (the
    validated unlit path), no ignition time is written, nothing is flagged as failed,
    and the planner lights the stage after the release (at the event, or at t_release +
    t_ign_s; a height's assumption line is added here too). With t_ign < 0 the vehicle
    is clamped to the carriage from ignition to the push start (closed-form HOLD
    carrying the weight component along the track, m g_eff sin phi; no liftoff
    extension: the push starts at t = 0 regardless of the thrust). At push start the
    drive is bound to the stack (``at_push_start`` with the vehicle mass, the delivered
    thrust at t = 0, g_eff and the track; an existing model returns itself) and every
    later call uses the bound drive; a drive that cannot start the push
    (``stall_reason``) ends the run on the track at once (tr.status = DRIVE_STALL, the
    reason as a flag, a zero-length ASSIST phase holding the push-start state). The
    ASSIST phase integrates the track state (``rhs_track``) from s = 0 at rest, split at
    the thrust kinks, the drive's own kinks and, on a drive whose push time is not exact,
    the delivered thrust's clamp (``thrust_clamp_time``: where a ramp's or lag's T_vac
    reaches p_amb A_e) inside the push (``push_boundaries``; a sub-phase ending at the
    ignition kink is unlit), with max_step = t_push/push_steps
    (the bound drive's push-time estimate when it is not exact; tightened by the ramp or
    lag cap when lit) and the events ``track_end`` (release), ``drive_limit`` (unless
    the model allows a negative drive force), ``propellant`` (exhausted on the track:
    ValueError) and the drive's watches (``push_watches``, ``ev_push_watch``, armed by
    ``_arm_watches``): a watch crossing (a limit starting to bind, or a two-way watch's
    limit stopping) ends its sub-phase, is logged, and the push goes on from there to
    the same boundary, so every kink of the drive force short of the release is a
    sub-phase end (split, and among the sampled rows the track peaks are read from).
    That includes a crossing a flight passed over: scipy tests an event's sign only at
    its step ends, so a limit that binds and is released inside one step changes no
    sign; ``_passed_over`` scans the first flight of each sub-phase of this drive (its
    dense output, which ``fly_track`` turns on for it: no step moves; a second flight
    covers part of an interval already scanned, and ``_fly_to_crossing``'s loop catches
    an earlier crossing it finds) for an interior maximum of each two-way watch's value
    above its zero band, and the sub-phase is flown again to that crossing as to any
    other (left unflown: a binding whose margin stays inside the band and, should a step
    hold two extrema of one watch value, a maximum the scan does not see, ``_passed_over``).
    Which way each watch stands is kept in a ``_WatchBook``: a crossing
    sets it, and so does a change logged at a sub-phase start, where a watch past its
    zero band changes side (at push start for a step command already capped) and one at
    zero or a hair past it is judged by its rate over a short look-ahead
    (WATCH_LOOKAHEAD_REL of the push), never by rule 3's 1 ms first step, unless a
    crossing or a change has just set its side (it is then fresh, and not judged again
    until its value leaves its zero band below, at a sub-phase start or at a step of a
    kept flight, ``_settle_fresh``); an event armed with its value in its band is
    guarded (``_guarded``; one still below zero fires at its true root), so it neither
    fires on the zero at t0 nor is disarmed with a run flag, and a watch changing side a
    third time at one instant raises RuntimeError (``_arm_watches``). A binding two-way
    watch arms its end, a binding one-way watch (taper_start) nothing. On a drive whose
    push time is not exact (the linear motor) every crossing, the release included, is
    flown again to its root as a fixed end, and to an earlier crossing that flight finds
    (a limit that bound and was released inside one step of the first flight, should the
    scan not have found it first) in turn (``_fly_to_crossing``), so the state the push
    goes on from or releases at is never read off an interpolant whose step passes a
    kink by more than the root's error; and the push releases only at the track end:
    ``track_end`` has zero_tol 0 (never disarmed), and a sub-phase that ends short of L
    by more than RELEASE_TIE_M (at a watch crossing just before L, or a flight a hair
    short of the track end) flies on to it (ATOL_M for constant_accel, as in SP1).
    Events logged on the track: push_start, ignition (when inside the push), ramp_end
    (at a thrust kink of a lit schedule only), the drive's kink events (drive_ramp_end),
    its watches (power_limit, power_limit_end, drive_cap, drive_cap_end, taper_start),
    drive_limit. An event that ends a sub-phase takes its
    state from ``event_state`` (the step's interpolant at the root, after the flight to
    it that of a step that passes the kink by at most the root's error); the kink events
    and a watch logged at a sub-phase start take the sub-phase's boundary state, a step
    end; none needs dense output. For a drive that returns itself and lists no kink and
    no watch (constant_accel) the integration (RHS, sub-phase boundaries, events, step
    cap) is that of SP1. Output: the TrackExit, or None when the drive limit or a stall
    stopped the run on the track (tr.status "drive_limit" or DRIVE_STALL and a flag).
    The release map, the release event and the ascent are the planner's.
    """
    check_layout(tr, prelude.layout, "fly_track")
    stage0 = vehicle.stages[0]
    t_push_start = 0.0
    exact = assist.push_time_exact
    t_push_est = assist.push_time_estimate(track) if exact else math.nan
    if exact and t_push_est <= 0.0:
        raise ValueError(f"assist model {assist.name!r} estimates no push (t_push <= 0)")
    if spec.lights_at_height or pending_until_release(spec, assist):
        # Pending ignition: no time before the altitude event or, on a drive whose push
        # time is not exact, before the flown release; the push is unlit. The schedule's
        # ignition time is a placeholder that a failed schedule never reads.
        t_ign, unlit = (t_push_est if exact else t_push_start), True
    elif exact or spec.reference == "push_start":
        t_ign, unlit = spec.t_ign_abs_s(t_push_est, t_push_start), spec.fails
    else:
        # A failed stage referenced to the release on such a drive: never lit, so its
        # placeholder time is never read either.
        t_ign, unlit = t_push_start, True
    if not unlit:
        tr.t_ign_abs_s[stage0.name] = t_ign
    flag_ignored_ignition_settings(tr, stage0.name, spec)
    stated = ramp_start_assumption(spec, g_eff_mps2)
    if stated is not None:
        tr.assumptions.append(stated)
    schedule = stage0.schedule(t_ign, spec.startup, unlit)
    m0 = vehicle.liftoff_mass_kg()
    y_hold = prelude.hold_state(track.start_altitude_m, m0)
    if t_ign < t_push_start and not unlit:
        # A failed engine has no ignition to hold through (see run_pad).
        # The clamp carries the weight component along the track, m g_eff sin phi.
        g_axial = g_eff_mps2 * math.sin(track.phi(0.0))
        hold = HoldParams(schedule, g_axial, p_amb_pa)
        tr.add_event("ignition", t_ign, HOLD_KIND, 0, y_hold)
        y_hold, f_min = hold_closed_form(
            tr,
            hold,
            t_ign,
            t_push_start,
            y_hold,
            vehicle=vehicle,
            settings=settings,
            layout=prelude.layout,
        )
        m_push = float(prelude.layout.get(y_hold, "m_kg"))
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
    m_dry = vehicle.stack_dry_mass_kg(0)
    length = track.length_m
    t = t_push_start
    # The drive bound to the stack at push start (the linear motor's holding force);
    # an existing model returns itself, so its push integrates as in SP1.
    params = track_params(assist, track, schedule, t, g_eff_mps2, p_amb_pa)
    drive = assist.at_push_start(m_push, params.thrust_N(t), g_eff_mps2, track)
    params = track_params(drive, track, schedule, t, g_eff_mps2, p_amb_pa)
    tr.add_event("push_start", t, ASSIST_KIND, 0, prelude.from_track(y, params))
    stall = drive.stall_reason()
    if stall is not None:
        # Nothing moves: a zero-length ASSIST phase records the push-start state.
        phase = PhaseSpec(ASSIST_KIND, 0, t, t, rhs_track, params, (), atol)
        tr.add_phase(integrate_phase(phase, y, settings))
        tr.status = DRIVE_STALL
        tr.flags.append(stall)
        return None
    t_push_scale = t_push_est if exact else drive.push_time_estimate(track)
    push_cap = t_push_scale / settings.push_steps
    thrust_kinks = schedule.kink_times()
    # The delivered thrust's clamp (T_vac = p_amb A_e inside a ramp or lag) kinks the
    # force law's motion and the acceleration law's drive force: split on a drive whose
    # push time is not exact only (constant_accel keeps the boundaries of SP1).
    clamp = None if exact else thrust_clamp_time(schedule, p_amb_pa)
    kinks = push_boundaries(thrust_kinks, drive.kink_times(), t_push_start, clamp)
    boundaries: list[float | None] = [*kinks, None]
    watches = drive.push_watches()
    # A drive whose push time is not exact (the linear motor) flies every crossing again to
    # its root as a fixed end, scans the first flight of each sub-phase for a crossing it
    # passed over (with the dense output on, which moves no step) and releases only at
    # the track end;
    # constant_accel keeps the integration of SP1 (no watches, no second flight, no scan,
    # the ATOL_M release tie, the caller's settings).
    refine = not exact
    flight = settings if exact else replace(settings, dense_output=True)
    end_event = ev_track_end(length, layout, zero_tol=ATOL_M if exact else 0.0)
    release_tie_m = ATOL_M if exact else RELEASE_TIE_M
    crossings = {"track_end"} | {w.name for w in watches}
    crossings |= {w.end_name for w in watches if w.end_name is not None}
    book = _WatchBook()  # which watches bind, which were just set, their changes
    lookahead_s = WATCH_LOOKAHEAD_REL * t_push_scale
    short_of: str | None = None  # the crossing a second flight just fell short of
    for t_b in boundaries:
        while True:  # once per sub-phase; again after a crossing ends one early
            params = track_params(drive, track, schedule, t, g_eff_mps2, p_amb_pa)
            if params.lit and not tr.has_event("ignition", 0):
                tr.add_event("ignition", t, ASSIST_KIND, 0, prelude.from_track(y, params))
            events: list[EventSpec] = [end_event, ev_propellant(m_dry, layout)]
            if not drive.allow_negative_drive:
                events.append(ev_drive_limit(params))
            step = min(push_cap, max_step_cap(schedule, t, settings)) if params.lit else push_cap
            phase = PhaseSpec(ASSIST_KIND, 0, t, t_b, rhs_track, params, tuple(events), atol, step)
            if watches:
                phase = _arm_watches(tr, prelude, phase, y, watches, book, lookahead_s, flight)
            res = integrate_phase(phase, y, flight)
            passed = _passed_over(phase, res, watches, lookahead_s, flight) if refine else None
            stand_in: PhaseResult | None = None
            if passed is not None:
                # A stand-in for the first flight: only the crossing's name and time are
                # read (``_fly_to_crossing`` flies to it; it is never kept).
                res = stand_in = replace(res, ended_by=passed[0], t_end=passed[1])
            short = False
            if refine and (
                passed is not None or (res.ended_by in crossings and res.ended_by != short_of)
            ):
                res, flown_to = _fly_to_crossing(phase, res, y, flight)
                if res is stand_in:
                    raise RuntimeError("a passed-over crossing was not flown (planner bug)")
                short = res.ended_by == "t_end"
                short_of = flown_to if short else None
            else:
                short_of = None
            res = tr.add_phase(res)
            for name, te in res.event_times:
                if name != "track_end":
                    y_e = event_state(res, name, te)
                    tr.add_event(name, te, ASSIST_KIND, 0, prelude.from_track(y_e, params))
            t, y = res.t_end, res.y_end
            _settle_fresh(res, watches, book)
            crossed = _record_crossing(res.ended_by, watches, book, t)
            if res.ended_by == "drive_limit":
                tr.status = "drive_limit"
                why = (
                    "the prescribed acceleration would need the drive to brake the engine"
                    if isinstance(drive, ConstantAccelAssist)
                    else f"the {drive.name} drive would have to hold the vehicle back: its law "
                    "asks for less force on the stack than the thrust's share (1 - f_imp) T "
                    "supplies"
                )
                tr.flags.append(
                    f"drive_limit: the drive force crossed zero at t = {t:.6g} s ({why}); the "
                    "run stopped on the track"
                )
                return None
            if res.ended_by == "propellant":
                raise ValueError(
                    f"stage {stage0.name!r} exhausted its propellant at t = {t:.6g} s on the track"
                )
            # A ramp ending at this sub-phase's boundary is logged before a release at
            # the same instant (the flight's burn skips a ramp segment already over);
            # only at a thrust kink of a lit schedule (an unlit one has none, so a drive
            # kink that falls on its placeholder ramp end logs no ramp_end).
            reached = t_b is not None and t >= t_b - ZERO_SPAN_S
            if t_b is not None and reached:
                if (
                    schedule.startup.effective_kind == "ramp"
                    and abs(t_b - (schedule.t_ign_abs_s + schedule.startup.t_ramp_s)) <= ZERO_SPAN_S
                    and any(abs(t_b - k) <= ZERO_SPAN_S for k in thrust_kinks)
                ):
                    tr.add_event("ramp_end", t, ASSIST_KIND, 0, prelude.from_track(y, params))
                for name, t_k in drive.kink_times():  # the drive's own kink (drive_ramp_end)
                    if abs(t_b - t_k) <= ZERO_SPAN_S:
                        tr.add_event(name, t, ASSIST_KIND, 0, prelude.from_track(y, params))
            s_end = float(layout.get(y, "s_m"))
            if res.ended_by == "track_end" or s_end >= length - release_tie_m:
                return TrackExit(
                    t_release_s=t,
                    y_track=y,
                    sdot_mps=float(layout.get(y, "sdot_mps")),
                    m_kg=float(layout.get(y, "m_kg")),
                    phi_rad=track.phi(length),
                    x_exit_m=_exit_x_m(track),
                    z_exit_m=track.start_altitude_m + track.z(length),
                )
            if reached or not (crossed or short):
                break
    raise RuntimeError("track phase ended without reaching the track end (planner bug)")


def _fly_to_crossing(
    phase: PhaseSpec,
    first: PhaseResult,
    y0: np.ndarray,
    settings: IntegratorSettings,
) -> tuple[PhaseResult, str]:
    """The track sub-phase ``phase`` flown again from y0 (its track state at phase.t0)
    to the crossing (a drive watch or ``track_end``) that ended its first flight
    ``first``, with that crossing's time as the fixed end; output: the flight to keep
    and the name of the crossing it was last flown to. A crossing's time is its root on
    the dense interpolant of a step whose stages straddle the kink it marks (at a watch
    the kink is the crossing itself; at the track end a power corner or a cap that
    starts binding just beyond L), less accurate than a step end (1e-8 relative at rtol
    1e-10 at a watch on the horizontal test, 4.6e-9 at the track end, measured). The
    flight to it stops its last step there, so no stage passes the kink by more than the
    root's error, and: the same crossing fires again inside that step, its root and
    state (the step's interpolant at the root) accurate to second order in that error
    (the usual case); or the flight ends a hair short of the crossing (ended_by
    "t_end"), and the next sub-phase starts there with the crossing a hair ahead, inside
    the very start of its first step, where the interpolant matches the step's start
    state and slope (``fly_track`` does not fly that crossing twice); or another
    crossing ends it earlier. That one may lie well before the fixed end: a limit that
    binds and is released inside one step of the first flight changes no sign at its
    step ends, so that flight passes over it (a power cap binding for 0.28 ms across a
    taper start, review pass 3), while the second flight, whose steps differ, finds it
    off a step that passes its kink by up to the rest of the span (2.2e-9 s early at
    rtol 1e-10, and 1.1e-9 relative fast at the cap's release, measured before the scan
    for passed-over crossings, ``_passed_over``, which now finds that binding in the
    first flight). The sub-phase is then flown again to that crossing, and so on until
    a flight ends at the crossing it was flown to, short of it, or not earlier. The
    events are those of the first flight, none of which fired before its end, less any
    at zero at phase.t0 (within its zero_tol: rule 3 would judge them again with the
    shorter span's first step; the
    watches armed at zero are guarded, ``_guarded``, and so are kept); the first
    flight's notes are kept. The first flight is returned as it is when its crossing
    came within ZERO_SPAN_S of phase.t0 (an already-past event at t0 among them: no step
    to fly) or was itself at zero at phase.t0."""
    t0 = phase.t0
    if first.t_end - t0 <= ZERO_SPAN_S:
        return first, first.ended_by
    at_zero = {ev.name for ev in phase.events if abs(float(ev.fn(t0, y0))) <= ev.zero_tol}
    if first.ended_by in at_zero:
        return first, first.ended_by
    events = tuple(ev for ev in phase.events if ev.name not in at_zero)
    target = first
    while True:
        flown = integrate_phase(replace(phase, t_end=target.t_end, events=events), y0, settings)
        earlier = flown.ended_by not in ("t_end", target.ended_by)
        if not earlier or flown.t_end >= target.t_end or flown.t_end - t0 <= ZERO_SPAN_S:
            return replace(flown, notes=(*first.notes, *flown.notes)), target.ended_by
        target = flown  # a crossing the earlier flight passed over: fly to it


def _passed_over(
    phase: PhaseSpec,
    res: PhaseResult,
    watches: Sequence[PushWatch],
    lookahead_s: float,
    settings: IntegratorSettings,
) -> tuple[str, float] | None:
    """The earliest crossing of a two-way drive watch that the flight ``res`` of the
    track sub-phase ``phase`` passed over: (its event name, its time [s]), or None.
    scipy sees an event only through a sign change at its step ends, so a limit that
    starts binding and is released (or released and binds again) inside one step changes
    no sign there, and the flight neither stops at it nor applies it (a power cap
    binding for 2.8 to 7 ms inside a 90 m taper flew uncapped, the exit 1.15e-8 fast;
    review pass 1 rerun, H1). Each two-way watch event armed in the phase is scanned
    through the rate of its unguarded value (``ev_push_watch``): at every step end of the
    flight, rising or not over a Heun step of lookahead_s [s] (``engine.
    first_step_value``, as ``_arm_watches`` judges a watch at zero); a step that starts
    rising and ends not rising holds an interior maximum, placed by bisection on the
    same test over the flight's dense output to ZERO_SPAN_S. A maximum above the event's
    zero band at which the event as armed (``_guarded`` or not) is positive is a
    crossing passed over: its time is the armed event's root between the step's start
    and the maximum, on the same interpolant at scipy's own tolerance (EVENT_ROOT_TOL),
    which is where scipy would have put it had the sign changed at a step end. Returned:
    the earliest, later than phase.t0 by more than ZERO_SPAN_S and before the flight's
    end; ``fly_track`` flies the sub-phase again to it (``_fly_to_crossing``). Limits:
    one extremum of a watch value per step is assumed (a maximum is seen only in a step
    that starts rising, so one after a minimum in the same step is not; the values are
    smooth inside a sub-phase, and a step at rtol <= 1e-9 resolves them); a binding whose
    margin stays
    inside the zero band is not reported (one way or the other it moves the push by
    far less than the integrator's error); the one-way taper_start only rises. None
    for a flight without dense output (``fly_track`` turns it on for this drive) or
    with a single sample. Inputs: the sub-phase (its events as armed, params, rhs, t0),
    its first flight, the drive's watches, the look-ahead [s] and the settings."""
    if res.dense is None or res.t.size < 2:
        return None
    raw: dict[str, EventSpec] = {}
    for watch in watches:
        if watch.end_name is not None:
            raw[watch.name] = ev_push_watch(phase.params, watch)
            raw[watch.end_name] = ev_push_watch(phase.params, watch, end=True)
    judge = replace(settings, first_step_s=lookahead_s)
    found: tuple[str, float] | None = None
    for armed in phase.events:
        value = raw.get(armed.name)
        if value is None:
            continue
        t_hit = _first_passed_over(phase, res, armed, value, judge)
        if t_hit is not None and (found is None or t_hit < found[1]):
            found = (armed.name, t_hit)
    return found


def _first_passed_over(
    phase: PhaseSpec,
    res: PhaseResult,
    armed: EventSpec,
    value: EventSpec,
    judge: IntegratorSettings,
) -> float | None:
    """The time [s] of the first crossing of the armed watch event ``armed`` that the
    flight ``res`` passed over inside one of its steps (``_passed_over``, which states
    the rule), or None. value: the same watch event unguarded (its rate and maximum are
    read from it); judge: the settings with first_step_s the look-ahead."""
    dense = res.dense
    if dense is None:
        return None

    def state(t: float) -> np.ndarray:
        return np.asarray(dense(t), dtype=float)

    def rising(t: float, y: np.ndarray) -> bool:
        ahead = first_step_value(replace(phase, t0=t), value, y, judge)
        return ahead - float(value.fn(t, y)) > 0.0

    ts = [float(t) for t in res.t]
    up = [rising(t, np.asarray(res.y[:, i], dtype=float)) for i, t in enumerate(ts)]
    for i in range(len(ts) - 1):
        if not up[i] or up[i + 1]:
            continue
        lo, hi = ts[i], ts[i + 1]
        while hi - lo > ZERO_SPAN_S:
            mid = 0.5 * (lo + hi)
            if rising(mid, state(mid)):
                lo = mid
            else:
                hi = mid
        y_top = state(lo)
        if float(value.fn(lo, y_top)) <= value.zero_tol or float(armed.fn(lo, y_top)) <= 0.0:
            continue
        if float(armed.fn(ts[i], state(ts[i]))) >= 0.0:
            continue  # not passed over: scipy saw this side at the step's start

        def armed_at(t: float) -> float:
            return float(armed.fn(t, state(t)))

        root = float(brentq(armed_at, ts[i], lo, xtol=EVENT_ROOT_TOL, rtol=EVENT_ROOT_TOL))
        if root - phase.t0 > ZERO_SPAN_S and root < res.t_end:
            return root
    return None


@dataclass
class _WatchBook:
    """The track prelude's bookkeeping of the drive watches over one push (mutable,
    owned by ``fly_track``): binding, the watches whose limit binds (a one-way watch,
    taper_start, once crossed); fresh, the watches whose side a crossing or a logged
    change has set and whose next event's value has not yet left its zero band below
    (``_arm_watches`` never judges them); last_change, per watch the time [s] of its
    last change of side and how many changes fell within ZERO_SPAN_S of each other up to
    it."""

    binding: set[str] = field(default_factory=set)
    fresh: set[str] = field(default_factory=set)
    last_change: dict[str, tuple[float, int]] = field(default_factory=dict)

    def set_side(self, name: str, binds: bool, t_s: float) -> None:
        """The watch name changes side at t_s [s]: its limit binds from here (binds
        True) or stops binding; it becomes fresh. RuntimeError (a planner bug, not
        physics) on more than WATCH_TOGGLES_PER_INSTANT changes within ZERO_SPAN_S of
        each other."""
        t_last, count = self.last_change.get(name, (-math.inf, 0))
        count = count + 1 if t_s - t_last <= ZERO_SPAN_S else 1
        if count > WATCH_TOGGLES_PER_INSTANT:
            raise RuntimeError(
                f"watch {name!r} changed side {count} times at t = {t_s:.12g} s on the track "
                "(planner bug: a watch whose side was just set is armed guarded, never judged)"
            )
        self.last_change[name] = (t_s, count)
        if binds:
            self.binding.add(name)
        else:
            self.binding.discard(name)
        self.fresh.add(name)


def _settle_fresh(res: PhaseResult, watches: Sequence[PushWatch], book: _WatchBook) -> None:
    """Clears ``book.fresh`` of each two-way watch whose next event's value (its end's
    while it binds, its own otherwise; ``ev_push_watch`` on the flight's params, not
    guarded) fell below its zero band (below -zero_tol) at a step of the kept flight res:
    as at a sub-phase start (``_arm_watches``), the value has left its band since a
    crossing set the watch's side, so at its next zero it is judged, not armed guarded
    (a brief binding with no sub-phase start inside it stayed fresh to its end, and its
    end, armed guarded with its value a hair past zero, fired zero_tol/rate late: 1.7e-8
    s for a power cap binding 7 ms inside a taper, 8e-9 relative in its logged speed).
    Called before the flight's own crossing is recorded (``_record_crossing``), which
    makes that watch fresh again."""
    params = res.spec.params
    for watch in watches:
        if watch.end_name is None or watch.name not in book.fresh:
            continue
        nxt = ev_push_watch(params, watch, end=watch.name in book.binding)
        if any(float(nxt.fn(float(t), res.y[:, i])) < -nxt.zero_tol for i, t in enumerate(res.t)):
            book.fresh.discard(watch.name)


def _record_crossing(
    ended_by: str, watches: Sequence[PushWatch], book: _WatchBook, t_s: float
) -> bool:
    """Whether the sub-phase ended at a drive watch's crossing (ended_by, its name or
    end name) at t_s [s], recording it in ``book`` (``_WatchBook.set_side``): a watch's
    crossing makes its limit bind, a two-way watch's end crossing releases it. Inputs:
    how the sub-phase ended, the drive's watches, the bookkeeping and the time."""
    for watch in watches:
        if ended_by == watch.name:
            book.set_side(watch.name, True, t_s)
            return True
        if watch.end_name is not None and ended_by == watch.end_name:
            book.set_side(watch.name, False, t_s)
            return True
    return False


def _guarded(ev: EventSpec, g0: float) -> EventSpec:
    """The upward watch event ev armed with its value g0 at the sub-phase start within
    its zero band (|g0| <= ev.zero_tol), where the engine's rule 3 would judge it with
    its own first step and could disarm it with a run flag. Its function reads a
    constant just beyond -zero_tol (``below``), so rule 3 leaves it armed and
    ``_fly_to_crossing`` keeps it in a second flight:
    - g0 <= 0 (not yet crossed): while g <= 0, so it fires where g crosses zero upward,
      the true root, and never on a value that stays at zero (the law's force equal to
      the limit);
    - g0 > 0 (a hair past zero, a side not taken): while |g| <= zero_tol, so the value
      at t0 cannot fire, and the event fires once g has left the band upward, at g =
      +zero_tol (zero_tol/rate after the root: below 1e-10 s for the two-way watches on
      the tests' pushes, whose zero_tols are ATOL_MPS and ATOL_KG g_eff).
    ValueError for an event that does not fire upward."""
    if ev.direction != 1:
        raise ValueError(f"event {ev.name!r}: only an upward watch event is guarded")
    tol = ev.zero_tol
    below = -math.nextafter(tol, math.inf)
    fn = ev.fn

    if g0 <= 0.0:

        def guarded(t: float, y: np.ndarray) -> float:
            g = fn(t, y)
            return g if g > 0.0 else min(g, below)

    else:

        def guarded(t: float, y: np.ndarray) -> float:
            g = fn(t, y)
            return below if abs(g) <= tol else g

    return replace(ev, fn=guarded)


def _arm_watches(
    tr: TraceBuilder,
    prelude: PreludeLayout,
    phase: PhaseSpec,
    y: np.ndarray,
    watches: Sequence[PushWatch],
    book: _WatchBook,
    lookahead_s: float,
    settings: IntegratorSettings,
) -> PhaseSpec:
    """The track sub-phase ``phase`` (starting at phase.t0 [s] in the track state y)
    with the drive's watch events that can cross in it (``ev_push_watch``, terminal,
    upward) added to its events; ``book`` is updated in place. Each watch's next event
    is the one that changes its side: its own event when its limit does not bind, its
    end event when it binds (a binding one-way watch, taper_start, has none: it arms
    nothing, and leaves ``binding`` unlogged once a sub-phase starts with its value
    below zero). With g the next event's value at t0 and tol its zero_tol:
    - g < -tol: the event is armed as it is, and the watch is no longer fresh;
    - -tol <= g < 0: armed guarded (``_guarded``), so it fires at its true root;
    - 0 <= g <= tol and the watch is fresh (a crossing or a logged change set its side,
      and its value has not left the band below since): not judged, armed guarded, so a
      limit that binds for less than any look-ahead is never logged as released at the
      instant it starts;
    - 0 <= g <= tol otherwise (a sub-phase boundary on the kink, the second of two
      watches that cross together): judged by the change of g over a Heun step of
      lookahead_s [s] (``engine.first_step_value`` with first_step_s = lookahead_s,
      never rule 3's own first step): rising, the watch changes side here; falling or
      unchanged (the law's force equal to the limit, no kink), armed guarded;
    - g > tol: the watch changes side here (at push start, a step command already
      capped).
    A change of side at t0 is logged there (an ASSIST event through the prelude's view,
    the sub-phase's start state), recorded (``_WatchBook.set_side``: the watch becomes
    fresh) and arms the opposite event of a two-way watch (guarded when within its
    band). Inputs: the builder, the prelude layout, the sub-phase, its start state, the
    drive's watches, the bookkeeping, the look-ahead [s] and the settings."""
    params = phase.params
    t0 = phase.t0
    judge = replace(settings, first_step_s=lookahead_s)
    armed: list[EventSpec] = []

    def value(ev: EventSpec) -> float:
        return float(ev.fn(t0, y))

    def rises(ev: EventSpec) -> bool:
        return first_step_value(phase, ev, y, judge) - value(ev) > 0.0

    def arm(ev: EventSpec) -> None:
        g0 = value(ev)
        armed.append(ev if g0 < -ev.zero_tol else _guarded(ev, g0))

    for watch in watches:
        on = watch.name in book.binding
        up = ev_push_watch(params, watch)
        other: EventSpec | None = None
        if watch.end_name is None:  # one-way (taper_start)
            if on:
                if value(up) < -up.zero_tol:
                    book.binding.discard(watch.name)
                    book.fresh.discard(watch.name)
                    armed.append(up)
                continue
            nxt = up
        else:
            down = ev_push_watch(params, watch, end=True)
            nxt, other = (down, up) if on else (up, down)
        g = value(nxt)
        if g < -nxt.zero_tol:
            book.fresh.discard(watch.name)
        if g < 0.0 or (g <= nxt.zero_tol and (watch.name in book.fresh or not rises(nxt))):
            arm(nxt)
            continue
        tr.add_event(nxt.name, t0, ASSIST_KIND, 0, prelude.from_track(y, params))
        book.set_side(watch.name, not on, t0)
        if other is not None:
            arm(other)
    return replace(phase, events=(*phase.events, *armed))
