"""The hold and track prelude shared by the planners: how and when stage 1 lights
(``IgnitionSpec``, built by ``resolve_ignition``, which converts a ramp start stated by
depth, speed or closed-form height to a time before the run), the hold-down
(closed-form clamp and the liftoff extension) and the
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
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from launchsim.assist.constant_accel import ConstantAccelAssist
from launchsim.assist.track import StraightTrack
from launchsim.config import (
    HEIGHT_EVENT_STEP,
    HEIGHT_METHOD_EVENT,
    RAMP_START_DEPTH,
    RAMP_START_HEIGHT_CLOSED_FORM,
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
    ev_track_end,
    event_state,
    integrate_phase,
    is_lit,
    sample_grid,
)
from launchsim.phases.trace import ASSIST_KIND, HOLD_KIND, HoldSummary, TraceBuilder
from launchsim.vehicle import Startup, ThrustSchedule, Vehicle, propellant_burned_kg

if TYPE_CHECKING:
    from launchsim.assist.base import AssistModel, TrackGeometry
    from launchsim.config import IgnitionConfig, RunConfig

IGNITION_REFERENCES = ("release", "push_start")
"""What ``IgnitionSpec.t_ign_s`` counts from."""
TRIGGER_KEYS: dict[str, str] = {
    RAMP_START_DEPTH: "at_depth_m",
    RAMP_START_SPEED: "at_speed_mps",
    RAMP_START_HEIGHT_CLOSED_FORM: "at_height_m",
}
"""The config key that states each non-time ramp-start trigger (for messages)."""
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
    t_ign_s and reference above); trigger_value: the requested depth [m], speed [m/s]
    or height [m] of a non-time trigger, None for "time". The two are a record of the
    request for the metrics and messages: every consumer of the spec reads t_ign_s and
    reference only, and their defaults leave every time-stated spec as it was (equal
    and hashing alike). Built from ``config.IgnitionConfig`` at the boundary by
    ``resolve_ignition`` (``from_config`` for the time family only).
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
        "release", t_push_start + t_ign_s for "push_start"."""
        origin = t_release_s if self.reference == "release" else t_push_start_s
        return origin + self.t_ign_s


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
    ramp-start conversions). The one resolver of both spec build sites
    (``sim.ignition_specs`` and ``search.SearchContext.from_run``, through
    ``resolve_stage_ignitions``, which also refuses a non-time trigger on a later
    stage).

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
    "release"). The spec records the request (trigger_kind, trigger_value). Raises
    ValueError for a non-time trigger without the ``constant_accel`` drive and its
    track (the conversion is exact only for a prescribed acceleration), for d > L, for
    a speed whose time v / a lies more than ZERO_SPAN_S after the release (v > v_e),
    for h at or above the drag-free apex v_e^2 / (2 g_eff), for g_eff <= 0 with a
    height, and for ``height_method: event`` (HEIGHT_EVENT_STEP). Frame: the flat track
    frame; times on the internal clock (t = 0 at push start)."""
    kind, value = cfg.ramp_start
    if kind == RAMP_START_TIME or value is None:
        return IgnitionSpec.from_config(cfg, startup)
    key = TRIGGER_KEYS[kind]
    if cfg.height_method == HEIGHT_METHOD_EVENT:
        raise ValueError(f"ignition height_method: event arrives in {HEIGHT_EVENT_STEP}")
    if not isinstance(assist, ConstantAccelAssist) or track is None:
        name = "none" if assist is None else assist.name
        raise ValueError(
            f"a ramp start by {key} needs the constant_accel drive and its track (assist "
            f"model {name!r}): the conversion to a time is exact only for a prescribed "
            "acceleration (force-limited drives arrive in Phase 3)"
        )
    t_ign, reference = _ramp_start_time(kind, value, assist, track, g_eff_mps2)
    return IgnitionSpec(t_ign, reference, _startup_override(cfg, startup), cfg.fails, kind, value)


def _ramp_start_time(
    kind: str,
    value: float,
    assist: ConstantAccelAssist,
    track: TrackGeometry,
    g_eff_mps2: float,
) -> tuple[float, str]:
    """(t_ign_s [s], reference) of a non-time ramp start on the constant_accel drive
    (see ``resolve_ignition`` for the closed forms, the snap and the refusals): value is
    the depth [m], speed [m/s] or height [m] of trigger ``kind``."""
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
        if not g_eff_mps2 > 0.0:
            raise ValueError(f"a closed-form height needs g_eff > 0, got {g_eff_mps2:g}")
        v_e = assist.exit_speed_mps(length)
        apex = v_e * v_e / (2.0 * g_eff_mps2)
        if value >= apex:
            raise ValueError(
                f"at_height_m {value:g} m is at or above the drag-free apex v_e^2 / "
                f"(2 g_eff) = {apex:.9g} m of the coast after release (v_e = {v_e:.9g} "
                f"m/s, g_eff = {g_eff_mps2:.9g} m/s^2)"
            )
        # (v_e - sqrt(v_e^2 - 2 g h)) / g, rationalised: no cancellation at small h
        t = 2.0 * value / (v_e + math.sqrt(v_e * v_e - 2.0 * g_eff_mps2 * value))
        reference = "release"
    after_release = t - t_push if reference == "push_start" else t
    if abs(after_release) <= ZERO_SPAN_S:
        return 0.0, "release"
    return t, reference


def ramp_start_assumption(spec: IgnitionSpec, g_eff_mps2: float) -> str | None:
    """The assumption line of a first stage whose ramp start the config stated by
    depth, speed or closed-form height (``resolve_ignition``): the request, the
    converted time and the closed form behind it (for the height also the track's
    constant g_eff [m/s^2] it used, and that the flown coast reaches a slightly
    different height, recorded by the ignition event). None for a time-stated or a
    failed stage (whose settings ``flag_ignored_ignition_settings`` flags)."""
    if spec.fails or spec.trigger_kind == RAMP_START_TIME:
        return None
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
    ValueError otherwise). Any TrackGeometry is accepted; the exit's downrange offset
    is known only for a ``StraightTrack`` (``TrackExit.x_exit_m`` is None otherwise).
    The first stage's ignition time
    resolves against the model's push-time estimate (``push_time_estimate``, exact for
    the prescribed-acceleration drive) for reference ``release`` and against t = 0 for
    ``push_start`` (a ramp start the config stated by depth, speed or height arrives
    here already converted to that pair, ``resolve_ignition``, and adds its
    ``ramp_start_assumption`` line to tr.assumptions). With t_ign < 0 the vehicle is
    clamped to the carriage from ignition
    to the push start (closed-form HOLD carrying the weight component along the track,
    m g_eff sin phi; no liftoff extension: the push starts at t = 0 regardless of the
    thrust). The ASSIST phase integrates the track state (``rhs_track``) from s = 0 at
    rest, split at the thrust kinks inside the push (a sub-phase ending at the ignition
    kink is unlit), with max_step = t_push/push_steps (tightened by the ramp or lag cap
    when lit) and the events ``track_end`` (release), ``drive_limit`` (unless the model
    allows a negative drive force) and ``propellant`` (exhausted on the track:
    ValueError). Events logged on the track: push_start, ignition (when inside the
    push), ramp_end, drive_limit; their states come from ``event_state`` (the step's
    own interpolant), so they need no dense output. Output: the TrackExit, or None
    when the drive limit stopped the run on the track (tr.status = "drive_limit" and a
    flag). The release map, the release event and the ascent are the planner's.
    """
    check_layout(tr, prelude.layout, "fly_track")
    stage0 = vehicle.stages[0]
    t_push_start = 0.0
    t_push_est = assist.push_time_estimate(track)
    if t_push_est <= 0.0:
        raise ValueError(f"assist model {assist.name!r} estimates no push (t_push <= 0)")
    t_ign = spec.t_ign_abs_s(t_push_est, t_push_start)
    if not spec.fails:
        tr.t_ign_abs_s[stage0.name] = t_ign
    flag_ignored_ignition_settings(tr, stage0.name, spec)
    stated = ramp_start_assumption(spec, g_eff_mps2)
    if stated is not None:
        tr.assumptions.append(stated)
    schedule = stage0.schedule(t_ign, spec.startup, spec.fails)
    m0 = vehicle.liftoff_mass_kg()
    y_hold = prelude.hold_state(track.start_altitude_m, m0)
    if t_ign < t_push_start and not spec.fails:
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
    push_cap = t_push_est / settings.push_steps
    kinks = sorted(k for k in schedule.kink_times() if k > t_push_start + ZERO_SPAN_S)
    boundaries: list[float | None] = [*kinks, None]
    t = t_push_start
    params = track_params(assist, track, schedule, t, g_eff_mps2, p_amb_pa)
    tr.add_event("push_start", t, ASSIST_KIND, 0, prelude.from_track(y, params))
    for t_b in boundaries:
        params = track_params(assist, track, schedule, t, g_eff_mps2, p_amb_pa)
        if params.lit and not tr.has_event("ignition", 0):
            tr.add_event("ignition", t, ASSIST_KIND, 0, prelude.from_track(y, params))
        events: list[EventSpec] = [ev_track_end(length, layout), ev_propellant(m_dry, layout)]
        if not assist.allow_negative_drive:
            events.append(ev_drive_limit(params))
        step = min(push_cap, max_step_cap(schedule, t, settings)) if params.lit else push_cap
        phase = PhaseSpec(ASSIST_KIND, 0, t, t_b, rhs_track, params, tuple(events), atol, step)
        res = tr.add_phase(integrate_phase(phase, y, settings))
        for name, te in res.event_times:
            if name != "track_end":
                y_e = event_state(res, name, te)
                tr.add_event(name, te, ASSIST_KIND, 0, prelude.from_track(y_e, params))
        t, y = res.t_end, res.y_end
        if res.ended_by == "drive_limit":
            tr.status = "drive_limit"
            tr.flags.append(
                f"drive_limit: the drive force crossed zero at t = {t:.6g} s (the prescribed "
                "acceleration would need the drive to brake the engine); the run stopped "
                "on the track"
            )
            return None
        if res.ended_by == "propellant":
            raise ValueError(
                f"stage {stage0.name!r} exhausted its propellant at t = {t:.6g} s on the track"
            )
        # A ramp ending at this sub-phase's boundary is logged before a release at
        # the same instant (the flight's burn skips a ramp segment already over).
        if t_b is not None and t >= t_b - ZERO_SPAN_S:
            if schedule.startup.effective_kind == "ramp" and (
                abs(t_b - (schedule.t_ign_abs_s + schedule.startup.t_ramp_s)) <= ZERO_SPAN_S
            ):
                tr.add_event("ramp_end", t, ASSIST_KIND, 0, prelude.from_track(y, params))
        s_end = float(layout.get(y, "s_m"))
        if res.ended_by == "track_end" or s_end >= length - ATOL_M:
            return TrackExit(
                t_release_s=t,
                y_track=y,
                sdot_mps=float(layout.get(y, "sdot_mps")),
                m_kg=float(layout.get(y, "m_kg")),
                phi_rad=track.phi(length),
                x_exit_m=_exit_x_m(track),
                z_exit_m=track.start_altitude_m + track.z(length),
            )
    raise RuntimeError("track phase ended without reaching the track end (planner bug)")
