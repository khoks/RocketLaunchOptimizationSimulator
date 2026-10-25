"""The linear motor: a force- and power-limited drive along a straight track (SP7 step
S4; docs/physics.md, "Linear motor"; design section 4.6, D-SP7-24, D-SP7-25, D-SP7-12).

Track equation (``assist/base.py``), with M = m_v + m_c, T the vehicle's delivered axial
thrust, T_sys = (1 - f_imp) T and F_other = 0 (vented shaft, no friction):

    M sddot = F + T_sys - M g_eff sin phi,      F_int = m_v (sddot + g_eff sin phi) - T

Two control laws (t on the push clock, t = 0 at push start; r(t) = min(1, t / t_r), 1
for a step t_r = 0):

- ``force``: F = min(F_lim(t), F_max, P_max / sdot), F_lim = F_0 + (F_max - F_0) r(t),
  the power term only for sdot > 0, F_0 = max(0, M_0 g_eff sin phi_0 - T_sys(0)) the
  holding force fixed at push start (``at_push_start``);
- ``acceleration``: a net acceleration command a(t) = a_cmd r(t), F = M (a(t) + g_eff
  sin phi) - T_sys, then capped by F_max and P_max / sdot; while a cap binds sddot
  follows from the capped F.

The stop taper (release at L) over the last s_taper metres scales, by w(s) = min(1,
(L - s) / s_taper), the acceleration law's command, or the force law's force toward the
holding value F_h = M g_eff sin phi - T_sys: F = F_h + (F - F_h) w(s). P_max is the
mechanical power at the carriage; the electricity is the drive work over the efficiency,
which moves no trajectory. The carriage brakes after release in closed form at the
constant total deceleration a_b. SI, radians, pure.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, ClassVar, Literal, get_args

import numpy as np

from launchsim import units
from launchsim.assist.base import AssistForces, PushWatch, TrackGeometry
from launchsim.assist.track import StraightTrack

if TYPE_CHECKING:
    from launchsim.config import LinearMotorConfig

ControlLaw = Literal["force", "acceleration"]
"""The two control laws; ``config.ControlLaw`` states the same set at the YAML boundary
(the physics modules import config for typing only; a test keeps the two equal)."""
CONTROL_FORCE: ControlLaw = "force"
CONTROL_ACCELERATION: ControlLaw = "acceleration"
CONTROL_LAWS: tuple[ControlLaw, ...] = get_args(ControlLaw)
"""The control laws, in ControlLaw's order."""
DRIVE_RAMP_END = "drive_ramp_end"
"""Event at the end of the rise (the force law's force or the acceleration law's
command, t = t_r), a sub-phase boundary of the push."""
POWER_LIMIT = "power_limit"
"""Event where the power limit starts binding on the law's force before the power term
(after the force law's rise: sdot crossing the corner speed P_max / F_max upward). Under
the force law's stop taper that force is the untapered one, so the event marks the law's
power branch while the flown power, F_h sdot (1 - w) + P_max w, stays below P_max."""
POWER_LIMIT_END = "power_limit_end"
"""Event where the power limit stops binding (the law's force before the power term
falling back below P_max / sdot: the acceleration law's command in the taper, say)."""
DRIVE_CAP = "drive_cap"
"""Event where a cap (F_max or P_max / sdot) starts binding the acceleration law's
command."""
DRIVE_CAP_END = "drive_cap_end"
"""Event where the acceleration law's command falls back below its cap (in the taper,
or under a rising thrust), so the cap stops binding."""
TAPER_START = "taper_start"
"""Event where the push enters the stop taper (s crossing L - s_taper upward)."""
RELEASE_TRIGGER_TRACK_END = "track_end"
"""How the push released (SP7 step S4: at the track end only; a release at a target
speed is S4a's)."""


@dataclass(frozen=True)
class PushStart:
    """The stack at push start, bound by ``LinearMotorAssist.at_push_start``.

    m_total_kg: M_0 = m_v + m_c [kg]; thrust_N: T(0), the vehicle's delivered axial
    thrust at t = 0 [N] (before impingement); g_axial_mps2: g_eff sin phi(0) [m/s^2],
    the weight component per unit mass along the track at its start; holding_force_N:
    F_0 = max(0, M_0 g_axial - (1 - f_imp) T(0)) [N], the drive force that holds the
    stack at rest (0 when the thrust alone lifts it).
    """

    m_total_kg: float
    thrust_N: float
    g_axial_mps2: float
    holding_force_N: float


@dataclass(frozen=True)
class LinearMotorAssist:
    """Force- and power-limited linear motor (``assist.base.AssistModel``).

    control: ``force`` or ``acceleration`` (CONTROL_LAWS); force_max_N: F_max [N];
    power_max_W: P_max [W], mechanical at the carriage; rise_time_s: t_r [s] (0 is a
    step); carriage_mass_kg: m_c [kg]; brake_decel_mps2: a_b [m/s^2], the carriage's
    constant total deceleration after release; accel_command_mps2: a_cmd [m/s^2] of the
    acceleration law (None for the force law); stop_taper_m: s_taper [m] (None or 0:
    no taper); efficiency: electrical-to-mechanical efficiency in (0, 1]; f_imp: exhaust
    impingement fraction in [0, 1]; g_eff_mps2: the track's g_eff [m/s^2], quoted in the
    assumptions only (the dynamics take g_eff through ``state_rate``); omega_p_rads: the
    planar rotation rate folded into it [rad/s], quoted only (the planar setup sets it);
    push_start: the PushStart bound by ``at_push_start`` (None before; ``state_rate``,
    ``push_time_estimate``, ``push_watches`` and ``stall_reason`` need it). name,
    extra_state_names, push_time_exact (False: the push time is a result of the flown
    push) and allow_negative_drive (False: a negative drive force ends the run with
    ``drive_limit``) are class constants. Forces of one instant: see the module
    docstring (drive_normal = 0, dissipated = 0).
    """

    name: ClassVar[str] = "linear_motor"
    extra_state_names: ClassVar[tuple[str, ...]] = ()
    push_time_exact: ClassVar[bool] = False
    allow_negative_drive: ClassVar[bool] = False

    control: ControlLaw
    force_max_N: float
    power_max_W: float
    rise_time_s: float
    carriage_mass_kg: float
    brake_decel_mps2: float
    accel_command_mps2: float | None = None
    stop_taper_m: float | None = None
    efficiency: float = 1.0
    f_imp: float = 0.0
    g_eff_mps2: float | None = None
    omega_p_rads: float = 0.0
    push_start: PushStart | None = None

    @classmethod
    def from_config(
        cls, config: LinearMotorConfig, g_eff_mps2: float
    ) -> tuple[LinearMotorAssist, StraightTrack]:
        """The model (unbound) and its ``StraightTrack`` from a validated config
        (``assist.build_assist``): the config's SI properties feed the model, g_eff_mps2
        [m/s^2] is quoted in its assumptions, and the track starts at exit_altitude -
        L sin phi so that its exit sits at the configured altitude (a buried silo starts
        at -L)."""
        phi = config.track.phi_rad
        track = StraightTrack(
            length_m=config.stroke_m,
            phi_rad=phi,
            start_altitude_m=config.track.exit_altitude_m - config.stroke_m * math.sin(phi),
        )
        model = cls(
            control=config.control,
            force_max_N=config.force_max_N,
            power_max_W=config.power_max_W,
            rise_time_s=config.force_rise_time_s,
            carriage_mass_kg=config.carriage_mass_kg,
            brake_decel_mps2=config.brake_decel_mps2,
            accel_command_mps2=config.accel_command_mps2,
            stop_taper_m=config.stop_taper_m,
            efficiency=config.drive_efficiency,
            f_imp=config.exhaust_impingement_fraction,
            g_eff_mps2=g_eff_mps2,
        )
        return model, track

    def __post_init__(self) -> None:
        if self.control not in CONTROL_LAWS:
            raise ValueError(f"control must be one of {CONTROL_LAWS}, got {self.control!r}")
        for label, value in (("force_max_N", self.force_max_N), ("power_max_W", self.power_max_W)):
            if not (math.isfinite(value) and value > 0.0):
                raise ValueError(f"{label} must be finite and > 0")
        if not (math.isfinite(self.rise_time_s) and self.rise_time_s >= 0.0):
            raise ValueError("rise_time_s must be finite and >= 0")
        a_cmd = self.accel_command_mps2
        if (self.control == CONTROL_ACCELERATION) != (a_cmd is not None):
            raise ValueError("accel_command_mps2 is given exactly for the acceleration law")
        if a_cmd is not None and not (math.isfinite(a_cmd) and a_cmd > 0.0):
            raise ValueError("accel_command_mps2 must be finite and > 0")
        taper = self.stop_taper_m
        if taper is not None and not (math.isfinite(taper) and taper >= 0.0):
            raise ValueError("stop_taper_m must be finite and >= 0")
        if not (math.isfinite(self.carriage_mass_kg) and self.carriage_mass_kg >= 0.0):
            raise ValueError("carriage_mass_kg must be finite and >= 0")
        if not (math.isfinite(self.brake_decel_mps2) and self.brake_decel_mps2 > 0.0):
            raise ValueError("brake_decel_mps2 must be finite and > 0")
        if not 0.0 < self.efficiency <= 1.0:
            raise ValueError("efficiency must lie in (0, 1]")
        if not 0.0 <= self.f_imp <= 1.0:
            raise ValueError("f_imp must lie in [0, 1]")
        if not math.isfinite(self.omega_p_rads):
            raise ValueError("omega_p_rads must be finite")

    # ------------------------------------------------------------------ the force laws

    @property
    def corner_speed_mps(self) -> float:
        """The corner speed v_c = P_max / F_max [m/s] where the force and power limits
        meet."""
        return self.power_max_W / self.force_max_N

    @property
    def tapered(self) -> bool:
        """Whether the push has a stop taper (s_taper > 0)."""
        return self.stop_taper_m is not None and self.stop_taper_m > 0.0

    def _bound(self) -> PushStart:
        """The PushStart, or ValueError when the model is not bound yet."""
        if self.push_start is None:
            raise ValueError(
                "the linear_motor needs the stack at push start: bind it with at_push_start"
            )
        return self.push_start

    def rise_fraction(self, t: float) -> float:
        """r(t) = min(1, t / t_r) on the push clock t [s] (clamped at 0 before the push;
        1 for a step, t_r = 0)."""
        if self.rise_time_s <= 0.0 or t >= self.rise_time_s:
            return 1.0
        return max(0.0, t / self.rise_time_s)

    def taper_weight(self, s_m: float, length_m: float) -> float:
        """w(s) = min(1, (L - s) / s_taper) at s_m [m] on a track of length_m [m] (1
        without a taper): in [0, 1] on the track, s <= L. It is not floored at 0: past L
        only the trial stages of the step that crosses the release read it, and the
        straight line continued below 0 keeps the force smooth there (a floor would put
        a C0 kink at s = L, inside that step, and the release state is read off its
        interpolant)."""
        if not self.tapered or self.stop_taper_m is None:
            return 1.0
        return min(1.0, (length_m - s_m) / self.stop_taper_m)

    def force_limit_N(self, t: float) -> float:
        """The force law's rising limit min(F_lim(t), F_max) [N], F_lim = F_0 + (F_max -
        F_0) r(t) (F_max once the rise has ended), at push-clock time t [s]."""
        r = self.rise_fraction(t)
        if r >= 1.0:
            return self.force_max_N
        f0 = self._bound().holding_force_N
        return min(f0 + (self.force_max_N - f0) * r, self.force_max_N)

    def command_force_N(
        self,
        t: float,
        s_m: float,
        m_total_kg: float,
        thrust_sys_N: float,
        g_axial_mps2: float,
        length_m: float,
    ) -> float:
        """The acceleration law's uncapped force M (a(t) w(s) + g_axial) - T_sys [N]:
        a(t) = a_cmd r(t) at push-clock time t [s], w(s) the taper weight at s_m [m] on a
        track of length_m [m], M = m_total_kg [kg], T_sys = thrust_sys_N [N] and g_axial
        = g_eff sin phi [m/s^2]."""
        a_cmd = self.accel_command_mps2 if self.accel_command_mps2 is not None else 0.0
        a = a_cmd * self.rise_fraction(t) * self.taper_weight(s_m, length_m)
        return m_total_kg * (a + g_axial_mps2) - thrust_sys_N

    def pre_power_force_N(
        self,
        t: float,
        s_m: float,
        m_total_kg: float,
        thrust_sys_N: float,
        g_axial_mps2: float,
        length_m: float,
    ) -> float:
        """The law's force before the power term [N]: min(F_lim(t), F_max) for the force
        law, min(command, F_max) for the acceleration law (inputs as in
        ``command_force_N``)."""
        if self.control == CONTROL_FORCE:
            return self.force_limit_N(t)
        command = self.command_force_N(t, s_m, m_total_kg, thrust_sys_N, g_axial_mps2, length_m)
        return min(command, self.force_max_N)

    def drive_force_N(
        self,
        t: float,
        s_m: float,
        sdot_mps: float,
        m_total_kg: float,
        thrust_sys_N: float,
        g_axial_mps2: float,
        length_m: float,
    ) -> float:
        """The drive force F [N] along the track at push-clock time t [s], position s_m
        [m], speed sdot_mps [m/s], with M = m_total_kg [kg], T_sys = thrust_sys_N [N],
        g_axial = g_eff sin phi [m/s^2] and the track length length_m [m]: the law's
        force (``pre_power_force_N``), capped by P_max / sdot for sdot > 0, then for the
        force law scaled toward the holding value F_h = M g_axial - T_sys by the taper
        weight (the acceleration law's taper is in its command). The order is the brief's
        (design 4.6): under the force law's taper the cap P_max / sdot applies to the
        untapered force, so where it binds the flown power is F_h sdot (1 - w) + P_max w,
        below P_max."""
        force = self.pre_power_force_N(t, s_m, m_total_kg, thrust_sys_N, g_axial_mps2, length_m)
        if sdot_mps > 0.0:
            force = min(force, self.power_max_W / sdot_mps)
        if self.control == CONTROL_FORCE:
            w = self.taper_weight(s_m, length_m)
            if w < 1.0:
                hold = m_total_kg * g_axial_mps2 - thrust_sys_N
                force = hold + (force - hold) * w
        return force

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
        """sddot = (F + T_sys)/M - g_eff sin phi with F from ``drive_force_N``; F_int =
        m_v (sddot + g_eff sin phi) - T; no normal drive force, no dissipation. Inputs as
        in ``AssistModel.state_rate`` (SI, track frame, t on the push clock); the model
        must be bound (``at_push_start``)."""
        self._bound()
        g_axial = g_eff_mps2 * math.sin(track.phi(s_m))
        total = m_vehicle_kg + m_carriage_kg
        t_sys = (1.0 - self.f_imp) * thrust_axial_N
        force = self.drive_force_N(t, s_m, sdot_mps, total, t_sys, g_axial, track.length_m)
        sddot = (force + t_sys) / total - g_axial
        return AssistForces(
            sddot_mps2=sddot,
            drive_force_N=force,
            drive_normal_N=0.0,
            interface_force_N=m_vehicle_kg * (sddot + g_axial) - thrust_axial_N,
            dissipated_W=0.0,
            extra_rate=np.zeros(0),
        )

    def initial_extra(self) -> np.ndarray:
        """No extra states."""
        return np.zeros(0)

    # ------------------------------------------------------------- the push protocol

    def at_push_start(
        self,
        m_vehicle_kg: float,
        thrust_axial_N: float,
        g_eff_mps2: float,
        track: TrackGeometry,
    ) -> LinearMotorAssist:
        """A copy bound to the push start: M_0 = m_vehicle_kg + m_c [kg], T(0) =
        thrust_axial_N [N], g_axial = g_eff_mps2 sin phi(0) [m/s^2] and the holding
        force F_0 = max(0, M_0 g_axial - (1 - f_imp) T(0)) [N] (``PushStart``)."""
        total = m_vehicle_kg + self.carriage_mass_kg
        g_axial = g_eff_mps2 * math.sin(track.phi(0.0))
        hold = max(0.0, total * g_axial - (1.0 - self.f_imp) * thrust_axial_N)
        return replace(self, push_start=PushStart(total, thrust_axial_N, g_axial, hold))

    def stall_reason(self) -> str | None:
        """The stall at push start (D-SP7-24): F_max + (1 - f_imp) T(0) <= M_0 g_eff sin
        phi_0, the drive at its limit and the thrust cannot lift the stack; the one-line
        reason with the numbers, None when the push can start. Needs the bound model."""
        b = self._bound()
        lift = self.force_max_N + (1.0 - self.f_imp) * b.thrust_N
        weight = b.m_total_kg * b.g_axial_mps2
        if lift > weight:
            return None
        return (
            f"drive_stall: the drive at F_max and the thrust together cannot lift the stack "
            f"at push start: F_max + "
            f"(1 - f_imp) T(0) = {lift:.6g} N <= M_0 g_eff sin phi = {weight:.6g} N "
            f"(F_max = {self.force_max_N:.6g} N, T(0) = {b.thrust_N:.6g} N, f_imp = "
            f"{self.f_imp:g}, M_0 = {b.m_total_kg:.6g} kg); the run stopped on the track "
            "(its push-start row is the drive at F_max with no support reaction, at most the "
            "loads of the stack at rest: the felt g and interface-force metrics are None)"
        )

    def push_time_estimate(self, track: TrackGeometry) -> float:
        """An estimate [s] of the push time over the track, for the step cap
        (t_push / push_steps) and the watch look-ahead (``prelude.WATCH_LOOKAHEAD_REL``
        of it), never for an ignition time (the push time is a result of the flown push;
        ``push_time_exact`` is False): the jerk-limited profile from rest, a net
        acceleration rising linearly over t_r to the plateau a_p and constant after,
        over L, with the bound stack held constant (M_0, T(0)): a_p = (F_max + (1 -
        f_imp) T(0)) / M_0 - g_eff sin phi_0 for the force law, the smaller of that and
        a_cmd for the acceleration law; t = t_r / 2 + sqrt(2 a_p L - a_p^2 t_r^2 / 12) /
        a_p when the rise ends inside the stroke (a_p t_r^2 / 6 < L), (6 L t_r /
        a_p)^(1/3) otherwise, sqrt(2 L / a_p) for a step.
        It leaves out the power limit, the caps, the taper and the burn, so it is not
        the push time; it is exact whenever the net acceleration is a_p r(t) throughout
        (the uncapped, untapered acceleration law; a cold, untapered force-law push that
        the power limit never reaches). Needs the bound model; ValueError when a_p <= 0
        (a stall)."""
        b = self._bound()
        lift = self.force_max_N + (1.0 - self.f_imp) * b.thrust_N
        a_p = lift / b.m_total_kg - b.g_axial_mps2
        if self.accel_command_mps2 is not None:
            a_p = min(a_p, self.accel_command_mps2)
        if not a_p > 0.0:
            raise ValueError(f"linear_motor: no net acceleration at the plateau ({a_p:g} m/s^2)")
        length, t_r = track.length_m, self.rise_time_s
        if t_r <= 0.0:
            return math.sqrt(2.0 * length / a_p)
        if a_p * t_r * t_r / 6.0 >= length:
            return (6.0 * length * t_r / a_p) ** (1.0 / 3.0)
        return 0.5 * t_r + math.sqrt(2.0 * a_p * length - a_p * a_p * t_r * t_r / 12.0) / a_p

    def kink_times(self) -> tuple[tuple[str, float], ...]:
        """The end of the rise (the force law's force or the acceleration law's
        command), (DRIVE_RAMP_END, t_r) on the push clock, when t_r > 0 (the force or
        command is C0 there); empty for a step."""
        if self.rise_time_s <= 0.0:
            return ()
        return ((DRIVE_RAMP_END, self.rise_time_s),)

    def push_watches(self) -> tuple[PushWatch, ...]:
        """The logged crossings (``assist.base.PushWatch``): POWER_LIMIT, the power limit
        starting to bind, (F_pre sdot - P_max) / F_max [m/s] with F_pre the law's force
        before the power term (``pre_power_force_N``; after the force law's rise this is
        sdot - P_max / F_max; under the force law's taper the untapered force, whose
        power branch it marks), two-way (POWER_LIMIT_END when it stops binding); for the
        acceleration law DRIVE_CAP, a cap starting to bind, command - min(F_max, P_max /
        sdot) [N], two-way (DRIVE_CAP_END); with a taper TAPER_START, s - (L - s_taper)
        [m], one-way. Together with the rise end (``kink_times``), the thrust kinks and
        the delivered thrust's clamp (``prelude.thrust_clamp_time``) these are every
        kink of the drive force short of the release: F = min(command, F_max, P_max /
        sdot) changes branch only where one of the two two-way watches crosses zero.
        Needs the bound model."""
        self._bound()
        watches = [PushWatch(POWER_LIMIT, self._power_margin, "mps", POWER_LIMIT_END)]
        if self.control == CONTROL_ACCELERATION:
            watches.append(PushWatch(DRIVE_CAP, self._cap_margin, "N", DRIVE_CAP_END))
        if self.tapered:
            watches.append(PushWatch(TAPER_START, self._taper_margin, "m"))
        return tuple(watches)

    def _power_margin(
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
    ) -> float:
        """(F_pre sdot - P_max) / F_max [m/s] (POWER_LIMIT; inputs as in
        ``state_rate``)."""
        total = m_vehicle_kg + m_carriage_kg
        g_axial = g_eff_mps2 * math.sin(track.phi(s_m))
        t_sys = (1.0 - self.f_imp) * thrust_axial_N
        pre = self.pre_power_force_N(t, s_m, total, t_sys, g_axial, track.length_m)
        return (pre * sdot_mps - self.power_max_W) / self.force_max_N

    def _cap_margin(
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
    ) -> float:
        """command - min(F_max, P_max / sdot) [N] (DRIVE_CAP; P_max / sdot only for
        sdot > 0; inputs as in ``state_rate``)."""
        total = m_vehicle_kg + m_carriage_kg
        g_axial = g_eff_mps2 * math.sin(track.phi(s_m))
        t_sys = (1.0 - self.f_imp) * thrust_axial_N
        command = self.command_force_N(t, s_m, total, t_sys, g_axial, track.length_m)
        cap = self.force_max_N
        if sdot_mps > 0.0:
            cap = min(cap, self.power_max_W / sdot_mps)
        return command - cap

    def _taper_margin(
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
    ) -> float:
        """s - (L - s_taper) [m] (TAPER_START; inputs as in ``state_rate``)."""
        taper = self.stop_taper_m if self.stop_taper_m is not None else 0.0
        return s_m - (track.length_m - taper)

    # -------------------------------------------------------- release and braking

    def release_position_m(self, track: TrackGeometry) -> float:
        """Where the vehicle releases [m] along the track: the track end L (SP7 step S4;
        a release at a target speed before L is S4a's)."""
        return track.length_m

    def braking_distance_m(self, v_mps: float) -> float:
        """Carriage braking distance [m] from v_mps [m/s] at the constant total
        deceleration a_b: v^2 / (2 a_b)."""
        return v_mps * v_mps / (2.0 * self.brake_decel_mps2)

    def braking_time_s(self, v_mps: float) -> float:
        """Carriage braking time [s] from v_mps [m/s]: v / a_b."""
        return v_mps / self.brake_decel_mps2

    def brake_force_N(self, g_eff_mps2: float, phi_rad: float) -> float:
        """The brake's force on the carriage [N] (along -t_hat, constant) for the total
        deceleration a_b on a track at phi_rad [rad] with g_eff [m/s^2]: m_c (a_b -
        g_eff sin phi), gravity supplying the rest (negative: gravity alone decelerates
        the carriage faster than a_b, and the device must push it; 0 for m_c = 0)."""
        return self.carriage_mass_kg * (self.brake_decel_mps2 - g_eff_mps2 * math.sin(phi_rad))

    def brake_energy_J(self, v_mps: float, g_eff_mps2: float, phi_rad: float) -> float:
        """The work [J] the brake absorbs stopping the carriage from v_mps [m/s] on a
        track at phi_rad [rad] with g_eff [m/s^2]: brake force times braking distance,
        (1/2) m_c v^2 (1 - g_eff sin phi / a_b) (the kinetic energy less what the climb
        stores; 0 for m_c = 0)."""
        return (
            0.5
            * self.carriage_mass_kg
            * v_mps
            * v_mps
            * (1.0 - g_eff_mps2 * math.sin(phi_rad) / self.brake_decel_mps2)
        )

    def facility_length_m(self, track: TrackGeometry, v_exit_mps: float) -> float:
        """Facility length [m]: max(L, s_release + d_brake) with d_brake from the exit
        speed v_exit_mps [m/s] (s_release = L in S4, so L + d_brake)."""
        return max(
            track.length_m,
            self.release_position_m(track) + self.braking_distance_m(v_exit_mps),
        )

    def electrical_power_W(self, mechanical_power_W: float) -> float:
        """The electrical power [W] behind a mechanical drive power [W]: max(0, P) /
        efficiency (a negative power, the drive braking, draws none: no regeneration
        is modelled)."""
        return max(0.0, mechanical_power_W) / self.efficiency

    # -------------------------------------------------------------- assumptions

    def track_gravity_assumption(self) -> str:
        """The track-gravity line (as ``ConstantAccelAssist.track_gravity_assumption``):
        the constant g_eff [m/s^2] and the rotation behind it, Coriolis neglected."""
        g_eff = (
            "constant g_eff = mu/R_E^2 - omega_p^2 R_E on the track"
            if self.g_eff_mps2 is None
            else f"constant g_eff = {self.g_eff_mps2:.7g} m/s^2 on the track"
        )
        if self.omega_p_rads == 0.0:
            return f"linear_motor: {g_eff}, omega_p = 0, Coriolis neglected"
        return (
            f"linear_motor: {g_eff} (mu/R_E^2 - omega_p^2 R_E with omega_p = "
            f"{self.omega_p_rads:.7g} rad/s, the planar rotation rate of the site), flat "
            "1-DOF track frame, Coriolis neglected"
        )

    def control_assumption(self) -> str:
        """The control-law line: the law, its limits, its rise and the no-pull rule."""
        f_kn = units.n_to_kn(self.force_max_N)
        p_mw = units.w_to_mw(self.power_max_W)
        rise = (
            f"rising linearly over t_r = {self.rise_time_s:g} s"
            if self.rise_time_s > 0.0
            else "stepping at push start (t_r = 0: infinite jerk)"
        )
        never_pulls = (
            "; the drive never pulls back: a negative drive force (holding the vehicle "
            "back) ends the run (drive_limit)"
        )
        if self.control == CONTROL_FORCE:
            return (
                f"linear_motor: force law F = min(F_lim(t), F_max, P_max / sdot), F_max = "
                f"{f_kn:g} kN and P_max = {p_mw:g} MW (assumed), the limit F_lim {rise} from "
                "the holding force F_0 = max(0, M_0 g_eff sin phi - (1 - f_imp) T(0)) fixed "
                f"at push start{never_pulls}"
            )
        a_g = units.to_g(self.accel_command_mps2 if self.accel_command_mps2 else 0.0)
        return (
            f"linear_motor: acceleration law, net acceleration command a_cmd = {a_g:g} g0 "
            f"(assumed) {rise}; the drive force M (a + g_eff sin phi) - (1 - f_imp) T, capped "
            f"by F_max = {f_kn:g} kN and P_max / sdot with P_max = {p_mw:g} MW (assumed); "
            f"while a cap binds the acceleration follows from the capped force{never_pulls}"
        )

    def taper_assumption(self) -> str:
        """The release line: the stop taper, or a step release."""
        if not self.tapered:
            return (
                "linear_motor: release at the track end (s = L) with no stop taper: the drive "
                "force drops to zero in a step at release"
            )
        hold = "the holding force M g_eff sin phi - (1 - f_imp) T"
        if self.control == CONTROL_FORCE:
            what = f"the force is scaled toward {hold} by min(1, (L - s) / s_taper)"
            at_end = f"at L the drive force is {hold} (zero net acceleration)"
        else:
            what = "the acceleration command is scaled by min(1, (L - s) / s_taper)"
            at_end = (
                f"at L the drive force is {hold} (zero net acceleration) unless a cap binds there"
            )
        return (
            f"linear_motor: release at the track end (s = L) after a stop taper over the last "
            f"{self.stop_taper_m:g} m: {what}; {at_end}, and it drops to zero in a step at "
            "release"
        )

    def shaft_assumption(self) -> str:
        """The shaft line: vented, no friction, and what the neglected air drag on the
        vehicle in the shaft would do under this control law."""
        if self.control == CONTROL_FORCE:
            drag = (
                "under the force law it would lower the exit speed (the exit speed is biased "
                "high) and raise the interface force (by D m_c / M at a given drive force, "
                "zero then without a carriage mass, and in the power phase also through "
                "P_max / sdot at the lower speed) and the drive work (more of the stroke at "
                "F_max after the rise, a longer push at P_max): both are biased low; the "
                "peak drive power when P_max is not reached, the felt g and the mean "
                "acceleration are biased high"
            )
        else:
            drag = (
                "under the acceleration law the drive force would absorb it while no cap "
                "binds (the drive work, the peak drive power and the interface force are "
                "biased low, as for constant_accel), and while a cap binds it would lower "
                "the exit speed (biased high; drag can also make a cap bind that the "
                "drag-free push never reaches)"
            )
        return (
            "linear_motor: shaft vented (no air column), no friction; air drag on the "
            f"vehicle in the shaft is neglected: {drag}"
        )

    def assumptions(self) -> tuple[str, ...]:
        """The drive's assumption lines: the control law, its limits and the no-pull
        rule, the power limit's meaning, the release and taper, the carriage, the
        braking closed forms, the impingement, the shaft and the neglected shaft air
        drag, the track gravity, the clamp and the ignition rule of the drive."""
        return (
            self.control_assumption(),
            "linear_motor: P_max is the mechanical power at the carriage (F sdot); the "
            "electricity is the positive drive work / efficiency and the electrical power "
            f"peak the mechanical peak / efficiency, drive efficiency {self.efficiency:g} "
            "(assumed), which moves no trajectory",
            self.taper_assumption(),
            f"linear_motor: carriage mass {units.kg_to_t(self.carriage_mass_kg):g} t (assumed)",
            "linear_motor: carriage braking in closed form at a constant total deceleration "
            f"a_b = {units.to_g(self.brake_decel_mps2):g} g0 (assumed): distance v^2 / (2 "
            "a_b), time v / a_b, brake force m_c (a_b - g_eff sin phi), brake energy "
            "(1/2) m_c v^2 (1 - g_eff sin phi / a_b); no braking phase in the trace",
            f"linear_motor: exhaust impingement fraction {self.f_imp:g} (assumed); the "
            "system keeps (1 - f_imp) T of the on-track thrust",
            self.shaft_assumption(),
            self.track_gravity_assumption(),
            "linear_motor: vehicle clamped to the carriage during any hold before the push",
            "linear_motor: a release-referenced stage-1 ignition lights at the flown release "
            "plus t_ign_s (the push time is a result of the push); one lit on the track must "
            "be stated from push_start (a release-referenced t_ign_s < 0 on a stage that "
            "lights is refused)",
        )
