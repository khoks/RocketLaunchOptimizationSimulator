"""The seam every ground-assist drive plugs into: track geometry, drive forces and the
model protocol (docs/physics.md, "Silo model" and "Assist energy identity").

Everything is SI, radians and pure. Frame (CLAUDE.md, track frame): origin at the track
start, arc length s along the track, track angle phi(s) above horizontal, tangent
t_hat = (cos phi, sin phi), normal n_hat = (-sin phi, cos phi), signed curvature
kappa = dphi/ds (positive when curving up), z(s) the height above the track start.
The track phase uses a flat local frame with the constant effective gravity g_eff
(``dynamics.g_eff_track``); Coriolis is neglected.

Along the track the system (vehicle m_v plus carriage m_c, M = m_v + m_c) obeys

    M sddot = F_drive + T_sys - M g_eff sin phi - F_other

with T_sys = (1 - f_imp) T the part of the vehicle's thrust the system keeps once the
exhaust impinging on the carriage (fraction f_imp, an amendment to the CLAUDE.md track
equation stated in docs/physics.md) is taken out, and F_other the model's friction,
piston and cable terms (zero for the screening drive and the linear motor of SP7 step
S4). The interface force between vehicle and carriage is F_int = m_v (sddot + g_eff sin
phi) - T (positive: the carriage pushes the vehicle).

The protocol members the force-limited drive needs (SP7 step S4, design D-SP7-24 and
D-SP7-25) are backward compatible: ``push_time_exact`` (True for the existing models),
``at_push_start`` (they return themselves), ``kink_times``, ``push_watches`` (both
empty for them), ``stall_reason`` and, since SP7 step S4a, ``release_speed_mps`` (None
for them: release at the track end), so for an existing model the integration of the
push (RHS, sub-phase boundaries, events, step cap) is that of SP1.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Literal, Protocol

import numpy as np

if TYPE_CHECKING:
    from launchsim.config import AssistConfig

type TrackFn = Callable[
    [float, float, float, np.ndarray, float, float, float, float, TrackGeometry], float
]
"""A function of one instant of the push with ``AssistModel.state_rate``'s arguments (t
[s], s [m], sdot [m/s], the extra states, m_vehicle [kg], m_carriage [kg], the delivered
thrust [N], g_eff [m/s^2], the track) returning a float in the watch's unit."""
WatchUnit = Literal["m", "mps", "N"]
"""Unit of a PushWatch value: a length [m], a speed [m/s] or a force [N]; it sets the
event's zero tolerance (``phases.engine.ev_push_watch``)."""


@dataclass(frozen=True)
class PushWatch:
    """A crossing during a push that the planner logs as an event (SP7 step S4):
    ``name`` is the event name, ``fn`` the watched value (TrackFn) in ``unit``
    (WatchUnit), and the event fires when the value crosses zero upward (the limit
    starts binding); the crossing ends the track sub-phase (the kink it marks is split)
    and the push goes on. A value already past zero at a sub-phase start (at push
    start, say) is logged there. ``end_name``, for a two-way watch, is the event logged
    when the value crosses zero downward again (the limit stops binding; also a
    sub-phase end); None for a one-way watch, which is not watched again once it binds.
    Used for the linear motor's ``power_limit`` and ``drive_cap`` (two-way, ending in
    ``power_limit_end`` and ``drive_cap_end``) and ``taper_start`` (one-way); the
    existing models have none."""

    name: str
    fn: TrackFn
    unit: WatchUnit
    end_name: str | None = None


class TrackGeometry(Protocol):
    """Geometry of a track as functions of arc length s [m] from the track start.

    length_m: total track length L [m]; phi(s): angle above horizontal [rad];
    kappa(s): signed curvature dphi/ds [1/m], positive when curving up; z(s): height
    [m] above the track start (track frame); start_altitude_m: altitude [m] of s = 0 in
    the +z-up datum frame, so the exit altitude is start_altitude_m + z(L).
    """

    @property
    def length_m(self) -> float:
        """Track length L [m]."""
        ...

    @property
    def start_altitude_m(self) -> float:
        """Altitude [m] of the track start in the datum frame (z = 0 at the pad)."""
        ...

    def phi(self, s_m: float) -> float:
        """Track angle above horizontal [rad] at arc length s_m [m]."""
        ...

    def kappa(self, s_m: float) -> float:
        """Signed curvature dphi/ds [1/m] at arc length s_m [m] (positive: curving up)."""
        ...

    def z(self, s_m: float) -> float:
        """Height [m] above the track start at arc length s_m [m]."""
        ...


@dataclass(frozen=True)
class AssistForces:
    """What a drive model returns for one instant of the track phase (SI, track frame).

    sddot_mps2: acceleration along the track [m/s^2]; drive_force_N: the drive's force
    along the tangent [N]; drive_normal_N: the drive's force along the normal n_hat [N]
    (a cable pulled from a fixed point; 0 for a linear drive), entering the carriage's
    track-normal load; interface_force_N: the force the carriage exerts on the vehicle
    along the tangent [N] (negative: tension, the vehicle would have to be held back);
    dissipated_W: power lost to friction and damping [W]; extra_rate: d/dt of the
    model's extra states (``AssistModel.extra_state_names``), an array of that length.
    """

    sddot_mps2: float
    drive_force_N: float
    drive_normal_N: float
    interface_force_N: float
    dissipated_W: float
    extra_rate: np.ndarray


class AssistModel(Protocol):
    """A swappable ground-assist drive (docs/physics.md, "Silo model").

    name: the registry key (``none``, ``constant_accel``, ...); extra_state_names: names
    (with unit suffixes for ``phases.atol_for``) of the states the model integrates
    beside [s, sdot, m] (a drum angle, a cable stretch); f_imp: exhaust impingement
    fraction in [0, 1] (the part of the vehicle's thrust the carriage absorbs, so the
    system keeps (1 - f_imp) T); efficiency: electrical-to-mechanical drive efficiency
    in (0, 1] (electrical energy = drive work / efficiency); carriage_mass_kg: the
    carriage that rides with the vehicle [kg]; allow_negative_drive: whether the drive
    may pull back (a negative drive force) instead of ending the run with status
    ``drive_limit``; state_rate: the forces at one instant; push_time_exact: whether
    push_time_estimate is the exact push time before the push is flown (True for a
    prescribed acceleration; False for a force-limited drive, whose release-referenced
    ignition the planner resolves at the flown release); push_time_estimate: the push
    duration the planner uses to resolve a release-referenced ignition time when it is
    exact, to cap the step (t_push / push_steps) and, for a drive whose push time is not
    exact, to scale the watch look-ahead (``prelude.WATCH_LOOKAHEAD_REL`` of it; never an
    ignition time there); at_push_start: the model bound to the stack at push
    start (a force-limited drive's holding force; the others return themselves);
    kink_times: (event name, time) kinks of the drive force inside the push, which the
    planner makes sub-phase boundaries and logs; push_watches: the crossings the
    planner logs and splits the push at (``PushWatch``); stall_reason: why the bound
    drive cannot start the push (None when it can); release_speed_mps: the speed along
    the track [m/s] at which the push releases before the track end (SP7 step S4a; the
    planner's ``target_speed`` event; None: release at the track end); braking_distance_m
    and facility_length_m: what the carriage needs after release; assumptions: the
    strings every summary lists.
    """

    push_time_exact: ClassVar[bool]
    """Whether ``push_time_estimate`` is the exact push time (class constant)."""

    @property
    def release_speed_mps(self) -> float | None:
        """The release speed v_release [m/s] along the track (sdot crossing it upward
        releases the push before the track end), or None: release at the track end."""
        ...

    @property
    def name(self) -> str:
        """The assist model key."""
        ...

    @property
    def extra_state_names(self) -> tuple[str, ...]:
        """Names of the model's extra track states (unit-suffixed)."""
        ...

    @property
    def f_imp(self) -> float:
        """Exhaust impingement fraction in [0, 1]."""
        ...

    @property
    def efficiency(self) -> float:
        """Drive efficiency in (0, 1]: electrical energy = drive work / efficiency."""
        ...

    @property
    def carriage_mass_kg(self) -> float:
        """Carriage mass [kg] (0 for none)."""
        ...

    @property
    def allow_negative_drive(self) -> bool:
        """Whether a negative drive force is allowed (else status ``drive_limit``)."""
        ...

    def initial_extra(self) -> np.ndarray:
        """Initial values of the extra states at push start."""
        ...

    def state_rate(
        self,
        t: float,
        s_m: float,
        sdot_mps: float,
        extra: np.ndarray,
        m_vehicle_kg: float,
        m_carriage_kg: float,
        thrust_axial_N: float,
        g_eff_mps2: float,
        track: TrackGeometry,
    ) -> AssistForces:
        """Forces and accelerations at absolute time t [s], position s_m [m] and speed
        sdot_mps [m/s] along the track, with the vehicle's delivered thrust
        thrust_axial_N [N] along the tangent (before impingement) and g_eff [m/s^2]."""
        ...

    def push_time_estimate(self, track: TrackGeometry) -> float:
        """Expected push duration [s] from s = 0 at rest to s = L (exact for a
        prescribed acceleration; an estimate for a force-limited drive, which needs the
        model bound by ``at_push_start``)."""
        ...

    def at_push_start(
        self,
        m_vehicle_kg: float,
        thrust_axial_N: float,
        g_eff_mps2: float,
        track: TrackGeometry,
    ) -> AssistModel:
        """The model bound to the push start: the vehicle mass m_vehicle_kg [kg] and its
        delivered axial thrust thrust_axial_N [N] at t = 0, the track's g_eff [m/s^2]
        and the track (whose angle at s = 0 sets the weight component). A model with
        nothing to bind returns itself."""
        ...

    def kink_times(self) -> tuple[tuple[str, float], ...]:
        """(event name, absolute time [s] on the push clock, t = 0 at push start) of
        each kink of the drive force inside the push; empty for a model without any."""
        ...

    def push_watches(self) -> tuple[PushWatch, ...]:
        """The crossings the planner logs during the push, each ending a track
        sub-phase there (``PushWatch``; empty for a model without any)."""
        ...

    def stall_reason(self) -> str | None:
        """Why the bound drive cannot start the push (the drive and the thrust cannot
        lift the stack at push start), naming the numbers; None when it can."""
        ...

    def braking_distance_m(self, v_mps: float) -> float:
        """Carriage braking distance [m] from speed v_mps [m/s]."""
        ...

    def facility_length_m(self, track: TrackGeometry, v_exit_mps: float) -> float:
        """Facility length [m]: the track plus the carriage braking distance."""
        ...

    def assumptions(self) -> Sequence[str]:
        """Assumption strings the model adds to every summary."""
        ...


class AssistBuilder(Protocol):
    """What a class must provide to be registered in ``assist.ASSIST_MODELS``: the
    class-level registry key ``name`` (the ``model`` discriminator of its
    ``config.AssistConfig``) and a ``from_config`` classmethod that turns the validated
    config and the track's g_eff [m/s^2] into the ``AssistModel`` instance and its
    ``TrackGeometry`` (None for a model without a track phase)."""

    name: ClassVar[str]

    @classmethod
    def from_config(
        cls, config: AssistConfig, g_eff_mps2: float
    ) -> tuple[AssistModel, TrackGeometry | None]:
        """The model and its track (or None) from a validated config."""
        ...


def normal_load_N(
    m_kg: float,
    sdot_mps: float,
    kappa_1pm: float,
    phi_rad: float,
    g_eff_mps2: float,
    other_normal_N: float = 0.0,
) -> float:
    """Track-normal load [N] a body of mass m_kg needs from the track (CLAUDE.md):

        N = m (kappa sdot^2 + g_eff cos phi) - F_other . n_hat

    Inputs: mass [kg]; speed along the track sdot_mps [m/s]; signed curvature kappa
    [1/m] (positive curving up); track angle phi [rad] above horizontal; g_eff [m/s^2];
    other_normal_N, the normal component [N] of any applied force other than the track
    reaction (a cable pulled from a fixed point). Frame: the track normal n_hat =
    (-sin phi, cos phi), so n_hat . z_hat = cos phi: N is the centripetal demand plus the
    weight component across the track, less what the applied force already supplies.
    Positive N is the track pushing the body along +n_hat. A vertical straight track
    (phi = pi/2, kappa = 0) carries no normal load.
    """
    return (
        m_kg * (kappa_1pm * sdot_mps * sdot_mps + g_eff_mps2 * math.cos(phi_rad)) - other_normal_N
    )
