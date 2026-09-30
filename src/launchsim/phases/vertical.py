"""The 1-D planner (``VerticalPlanner``) that strings HOLD, COAST, BURN and FALL phases
together for a run (docs/physics.md, "Phases and events"), and for an assisted run the
ASSIST (track) phase and its release into the ascent (``VerticalPlanner.run_track``,
``map_release``); the assist models supply the track forces through
``dynamics.TrackParams``. Also the 1-D start state (``AscentStart``) and the release
and staging maps.

The hold and the track push come from the shared prelude (``phases.prelude``) run with
the 1-D layout; phases are integrated by the engine (``phases.engine``) and recorded
into a ``phases.trace.TraceBuilder`` through the 1-D StateView.

Everything is SI and pure: no I/O, no globals, no printing. Frame: the +z-up ascent
datum frame of ``dynamics.VERTICAL_LAYOUT`` (z [m] above the datum, v [m/s] signed,
positive rising); times are absolute run times [s].
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from launchsim.constants import R_EARTH_M
from launchsim.dynamics import (
    VERTICAL_LAYOUT,
    VERTICAL_STATE_NAMES,
    Gravity,
    StateLayout,
    VerticalParams,
    rhs_vertical,
)
from launchsim.phases.engine import (
    ATOL_M,
    ATOL_MPS,
    ZERO_SPAN_S,
    EventSpec,
    IntegratorSettings,
    PhaseResult,
    PhaseSpec,
    _pass_through,
    atol_for,
    ev_apex,
    ev_impact,
    ev_propellant,
    ev_turnaround,
    integrate_phase,
)
from launchsim.phases.prelude import (
    VERTICAL_PRELUDE,
    VERTICAL_TRACK_TOL_RAD,
    HoldParams,
    IgnitionSpec,
    flag_ignored_ignition_settings,
    fly_track,
    hold_closed_form,
    hold_until_liftoff,
    log_liftoff,
    max_step_cap,
    track_params,
)
from launchsim.phases.trace import (
    ASSIST_KIND,
    HOLD_KIND,
    RELEASE_LABEL,
    HoldSummary,
    RunTrace,
    TraceBuilder,
)
from launchsim.vehicle import ThrustSchedule, Vehicle

if TYPE_CHECKING:
    from launchsim.assist.base import AssistModel, TrackGeometry
    from launchsim.dynamics import TrackParams

END_KINDS = ("stage1_burnout", "all_burnout", "apex", "impact")
"""Where a run stops (``config.RunEnd``)."""

_IZ = VERTICAL_LAYOUT.index("z_m")
_IV = VERTICAL_LAYOUT.index("v_mps")
_IM = VERTICAL_LAYOUT.index("m_kg")


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
        """True for a vehicle that is not moving at release (|v0| within ATOL_MPS of 0,
        the same floor the sigma rule treats as v = 0)."""
        return abs(self.v0_mps) <= ATOL_MPS

    def on_ground(self, z_ground_m: float) -> bool:
        """True for a vehicle standing on the ground: at rest within ATOL_M of
        z_ground_m [m] (the pad); only such a start is held down."""
        return self.at_rest and abs(self.z0_m - z_ground_m) <= ATOL_M


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
    vacuum thrust from sea level; Phase 2 hands in the pad pressure). The settings must
    keep dense output on (ValueError otherwise): every 1-D trace is a recorded run that
    ``sim`` resamples. ``run_pad`` runs a pad
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
        if not settings.dense_output:
            raise ValueError(
                "the 1-D planner produces recorded runs, whose time series, crossings and "
                "drive-power scans resample the dense output; dense_output = False is for "
                "search evaluations only"
            )
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
        """An empty TraceBuilder for this vehicle (1-D StateView)."""
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
        if not spec.fails:
            tr.t_ign_abs_s[stage0.name] = t_ign
        self._flag_ignored_ignition_settings(tr, stage0.name, spec)
        schedule = stage0.schedule(t_ign, spec.startup, spec.fails)
        params = HoldParams(schedule, self.g_eff_mps2, self.p_amb_pa)
        m0 = self.vehicle.liftoff_mass_kg()
        y = VERTICAL_LAYOUT.build(z_m=start.z0_m, v_mps=start.v0_mps, m_kg=m0)
        hold_start = t_release
        force_min = math.inf
        if t_ign < t_release and not spec.fails:
            # A failed engine has no ignition to hold through: nothing burns before
            # release and no ignition is logged (the schedule's T_vac is 0 throughout).
            hold_start = t_ign
            tr.add_event("ignition", t_ign, HOLD_KIND, 0, y)
            y, f_min = self.hold_closed_form(tr, params, t_ign, t_release, y)
            force_min = min(force_min, f_min)
        tr.t_release_s = t_release
        tr.y_release = y.copy()
        label = HOLD_KIND if hold_start < t_release else RELEASE_LABEL
        tr.add_event("release", t_release, label, 0, y)
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
            if spec.fails:
                tr.failed_stage = stage0.name  # never left the ground: t_fail_s stays None
            return tr.finish()
        self.ascend(tr, t_start, y, sigma_hint=sigma_hint)
        return tr.finish()

    def run_track(self, assist: AssistModel, track: TrackGeometry) -> RunTrace:
        """A track run: t = 0 at push start, release at the track end (docs/physics.md,
        "Silo model").

        The push up to the track exit is the shared prelude ``prelude.fly_track`` run
        with the 1-D layout (VERTICAL_PRELUDE), this planner's g_eff and pad pressure:
        ignition against the push-time estimate, the closed-form HOLD for t_ign < 0,
        the ASSIST phase split at the thrust kinks with the ``track_end``,
        ``drive_limit`` (status ``drive_limit``: the run stops on the track) and
        ``propellant`` (ValueError) events. At release the state maps into the ascent
        frame (``map_release``), t_release is the track-end root, and ``ascend`` runs
        the flight. Events logged on the track: push_start, ignition (when inside the
        push), ramp_end, drive_limit, release.
        """
        stage0 = self.vehicle.stages[0]
        spec = self.ignition[stage0.name]
        tr = self.new_builder()
        exit_ = fly_track(
            tr,
            assist,
            track,
            spec,
            vehicle=self.vehicle,
            settings=self.settings,
            g_eff_mps2=self.g_eff_mps2,
            p_amb_pa=self.p_amb_pa,
            prelude=VERTICAL_PRELUDE,
        )
        if exit_ is None:
            return tr.finish()
        y_rel = map_release(exit_.sdot_mps, exit_.m_kg, exit_.phi_rad, exit_.z_exit_m)
        t = exit_.t_release_s
        tr.t_release_s = t
        tr.y_release = y_rel.copy()
        tr.add_event("release", t, ASSIST_KIND, 0, y_rel)
        self.ascend(tr, t, y_rel)
        return tr.finish()

    def _track_params(
        self, assist: AssistModel, track: TrackGeometry, schedule: ThrustSchedule, t: float
    ) -> TrackParams:
        """TrackParams of the sub-phase starting at t [s] (``prelude.track_params`` with
        this planner's g_eff and pad pressure)."""
        return track_params(assist, track, schedule, t, self.g_eff_mps2, self.p_amb_pa)

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
        A stage whose ignition fails (``IgnitionSpec.fails``; the run must end at
        impact) gets no ignition time and no burn: ``_fail_ignition`` records it and
        the terminal coast (COAST to apex, FALL to the ground) follows at once.
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
            if spec.fails:
                # Failed ignition (docs/physics.md, "Failed-ignition coast"): the stage's
                # T_vac is 0 for the whole run, so its scheduled ignition time is moot
                # (no COAST_PRE_IGN, no ignition time recorded); the vehicle coasts
                # unpowered from here to apex and falls to the ground.
                if self.end != "impact":
                    raise ValueError(f"stage {stage.name!r} fails: the run must end at impact")
                if k > 0:  # the first stage's settings were flagged by run_pad/run_track
                    self._flag_ignored_ignition_settings(tr, stage.name, spec)
                self._fail_ignition(tr, k, t, y, sigma_hint)
                self._terminal_coast(tr, k, t, y, sigma_hint)
                return
            tr.t_ign_abs_s[stage.name] = t_ign
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

    @staticmethod
    def _flag_ignored_ignition_settings(
        tr: TraceBuilder, stage_name: str, spec: IgnitionSpec
    ) -> None:
        """``prelude.flag_ignored_ignition_settings``: flag the settings a failed stage
        ignores (no flag for a stage that lights)."""
        flag_ignored_ignition_settings(tr, stage_name, spec)

    def _fail_ignition(
        self, tr: TraceBuilder, k: int, t: float, y: np.ndarray, sigma_hint: int | None
    ) -> None:
        """Record that stage k's ignition failed at time t [s] (state y): sets
        tr.failed_stage and tr.t_fail_s and logs the ``ignition_failed`` event in the
        terminal-coast phase that starts here (COAST when rising, FALL when falling).
        The stage's thrust schedule is identically zero, so nothing else changes: the
        coast that follows is the same unpowered flight as after a last burnout."""
        tr.failed_stage = self.vehicle.stages[k].name
        tr.t_fail_s = t
        kind = "COAST" if self._sigma(y, None, t, sigma_hint) == 1 else "FALL"
        tr.add_event("ignition_failed", t, kind, k, y)

    # ------------------------------------------------------------------------ holds

    def hold_closed_form(
        self, tr: TraceBuilder, params: HoldParams, t0: float, t1: float, y: np.ndarray
    ) -> tuple[np.ndarray, float]:
        """Clamp the vehicle from t0 to t1 [s] (``prelude.hold_closed_form`` on the 1-D
        layout): z and v are held, the mass follows ``propellant_burned_kg`` in closed
        form (no ODE; constant while ``params.lit`` is False), sampled at
        settings.sample_dt_s. Only the burn between t0 and t1 is subtracted from y's
        mass, so the segment may start any time after ignition (a lit hold split into
        several calls gives the single-call result). Returns the state at t1 and the
        minimum hold-down force [N] over the samples. Raises ValueError if the first
        stage's propellant runs out by t1."""
        return hold_closed_form(
            tr,
            params,
            t0,
            t1,
            y,
            vehicle=self.vehicle,
            settings=self.settings,
            layout=VERTICAL_LAYOUT,
        )

    def hold_until_liftoff(
        self, tr: TraceBuilder, params: HoldParams, t0: float, y: np.ndarray
    ) -> tuple[float, np.ndarray, float]:
        """Keep a vehicle at rest on the ground clamped past t0 [s] until its thrust
        exceeds its weight (``prelude.hold_until_liftoff`` on the 1-D layout): split at
        the thrust kinks, unlit sub-phases sampled directly, the balance re-evaluated at
        the start of every lit sub-phase, the mass alone integrated with the liftoff and
        propellant events. Liftoff records the extension as an assumption; propellant
        exhaustion raises ValueError; no liftoff by t_max sets tr.status = "no_liftoff"
        and a flag. Returns (liftoff time [s], state, minimum hold-down force [N] over
        the extension).
        """
        return hold_until_liftoff(
            tr, params, t0, y, vehicle=self.vehicle, settings=self.settings, layout=VERTICAL_LAYOUT
        )

    @staticmethod
    def _liftoff(
        tr: TraceBuilder, t: float, y: np.ndarray, force_min: float
    ) -> tuple[float, np.ndarray, float]:
        """``prelude.log_liftoff``: log the liftoff at t [s] (state y) that ends an
        extended hold, record the extension as an assumption, and return (t, y,
        force_min)."""
        return log_liftoff(tr, t, y, force_min)

    # ---------------------------------------------------------------------- phases

    def _max_step(self, schedule: ThrustSchedule | None, t: float) -> float:
        """Step cap [s] at time t (``prelude.max_step_cap``): t_ramp / ramp_steps inside
        a ramp, tau / lag_steps_per_tau during a lag burn, unbounded otherwise."""
        return max_step_cap(schedule, t, self.settings)

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
        a coast never lists a turnaround; the propellant event belongs to burns only.
        A falling phase that starts on the ground (z within ATOL_M of z_ground, moving
        down: an apex within ATOL_M of the ground, or a start at the ground already
        sinking) is the "phase starting on the event surface moving into it" case the
        engine's disarm rule cannot resolve (``integrate_phase``), so it is the impact
        itself: the phase is a zero-length pass-through ended by impact at t0."""
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
            if sigma == -1 and abs(float(y[_IZ]) - self.z_ground_m) <= ATOL_M:
                note = (
                    f"{kind} starts on the ground (z = {float(y[_IZ]):.6g} m, within "
                    f"{ATOL_M:.3g} m of z_ground = {self.z_ground_m:.6g} m) moving down: "
                    "impact at t0"
                )
                tr.add_phase(_pass_through(spec, y, "impact", [note], (("impact", t),)))
                tr.add_event("impact", t, kind, k, y)
                tr.status = "impact"
                return t, y, "impact"
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
