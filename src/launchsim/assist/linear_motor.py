"""The linear motor: a force- and power-limited drive along a straight track (SP7 step
S4; docs/physics.md, "Linear motor"; design section 4.6, D-SP7-24, D-SP7-25, D-SP7-12).

Track equation (``assist/base.py``), with M = m_v + m_c, T the vehicle's delivered axial
thrust, T_sys = (1 - f_imp) T and F_other = F_p(s), the trapped column's force on the
carriage (0 for the vented shaft; no friction):

    M sddot = F + T_sys - M g_eff sin phi - F_p,      F_int = m_v (sddot + g_eff sin phi) - T

The sealed shaft (SP7 step S5; ``SealedShaft``; design 4.8, D-SP7-26): the carriage seals
the bore above a gap h_0 of air trapped at the push-start pressure p_0 = p_atm(z_start),
which expands adiabatically as the carriage rises, F_p(s) = max(0, p_0 - p_0 (h_0/(h_0 +
s))^gamma) A_bore <= p_0 A_bore, against the motion, on the carriage. Under the force law
the drive's force is unchanged and the stack slows (F_int lower by (m_v/M) F_p); under the
acceleration law the drive supplies F_p too (then capped as below). The work done against
it, W_p = int F_p sdot dt, is the model's extra state ``W_piston_J`` (WORK_STATE).

Two control laws (t on the push clock, t = 0 at push start; r(t) = min(1, t / t_r), 1
for a step t_r = 0):

- ``force``: F = min(F_lim(t), F_max, P_max / sdot), F_lim = F_0 + (F_max - F_0) r(t),
  the power term only for sdot > 0, F_0 = max(0, M_0 g_eff sin phi_0 - T_sys(0)) the
  holding force fixed at push start (``at_push_start``);
- ``acceleration``: a net acceleration command a(t) = a_cmd r(t), F = M (a(t) + g_eff
  sin phi) - T_sys + F_p(s), then capped by F_max and P_max / sdot; while a cap binds
  sddot follows from the capped F.

The stop taper (release at L) over the last s_taper metres scales, by w(s) = min(1,
(L - s) / s_taper), the acceleration law's command, or the force law's force limit toward
the holding value F_h = M g_eff sin phi - T_sys, and the power cap applies to the force
that is flown (D-SP7-50, SP7 step S4a): F = min(F_h + (min(F_lim(t), F_max) - F_h) w(s),
P_max / sdot) under the force law, so F sdot <= P_max on every branch (the force law's
taper is refused with a sealed shaft, whose column its holding value leaves out: S5).
The push releases at the track end, or (S4a, ``release_speed_mps``) where sdot reaches
the release speed v_release before it (``phases.prelude.fly_track``; refused with a
taper, a release-at-L device). P_max is the mechanical power at the carriage; the
electricity is the drive work over the efficiency, which moves no trajectory. The
carriage brakes after release in closed form at the constant total deceleration a_b,
from the release point (facility max(L, s_release + d_brake): within the stroke left, or
past the track end). SI, radians, pure.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, ClassVar, Literal, get_args

import numpy as np

from launchsim import units
from launchsim.assist.base import AssistForces, PushWatch, TrackGeometry
from launchsim.assist.track import StraightTrack
from launchsim.atmosphere import KAPPA_AIR, standard_atmosphere

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
(``pre_power_force_N``; after the force law's rise and before its taper: sdot crossing
the corner speed P_max / F_max upward). Under the force law's stop taper that force is
the tapered one (D-SP7-50), so where the event has fired the flown power is P_max."""
POWER_LIMIT_END = "power_limit_end"
"""Event where the power limit stops binding (the law's force before the power term
falling back below P_max / sdot: the force law's tapered force or the acceleration law's
command in the taper, say)."""
DRIVE_CAP = "drive_cap"
"""Event where a cap (F_max or P_max / sdot) starts binding the acceleration law's
command."""
DRIVE_CAP_END = "drive_cap_end"
"""Event where the acceleration law's command falls back below its cap (in the taper,
or under a rising thrust), so the cap stops binding."""
TAPER_START = "taper_start"
"""Event where the push enters the stop taper (s crossing L - s_taper upward)."""
RELEASE_TRIGGER_TRACK_END = "track_end"
"""How the push released: at the track end s = L (the ``track_end`` event, or a push
that stops within ``prelude.RELEASE_TIE_M`` of L)."""
RELEASE_TRIGGER_TARGET_SPEED = "target_speed"
"""How the push released (SP7 step S4a): where sdot reached the release speed
``release_speed_mps`` before the track end (the ``target_speed`` event,
``phases.engine.ev_release_speed``, whose name it is)."""
RELEASE_TRIGGERS: tuple[str, ...] = (RELEASE_TRIGGER_TRACK_END, RELEASE_TRIGGER_TARGET_SPEED)
"""The values of the ``release_trigger`` metric of a run that released."""
ShaftKind = Literal["vented", "sealed"]
"""The shaft below the carriage (SP7 step S5): ``vented`` (no air column) or ``sealed``
(the carriage seals a trapped column, ``SealedShaft``); ``config.ShaftKind`` states the
same set at the YAML boundary (a test keeps the two equal)."""
SHAFT_SEALED: ShaftKind = "sealed"
"""The sealed shaft's ShaftKind (``from_config`` builds a SealedShaft for it)."""
WORK_STATE = "W_piston_J"
"""The extra track state of a sealed-shaft push: W_p = int F_p sdot dt [J], the work done
against the trapped column's net force F_p on the carriage, drive work the stack does
not receive (``SealedShaft``; the ``_J`` suffix gives it its atol,
``phases.engine.atol_for``)."""
SEALED_TAPER_REFUSAL = (
    "a sealed shaft is refused with a stop taper under the force law: the taper scales the "
    "force toward the open shaft's holding value M g_eff sin phi - (1 - f_imp) T, so the "
    "trapped column would decelerate the stack at the track end and could stop it in the "
    "shaft; leave one of them out (the acceleration law's taper flies its command, the "
    "column included)"
)
"""Why ``LinearMotorAssist`` and ``config.LinearMotorConfig`` refuse a sealed shaft with
the force law's stop taper (SP7 step S5)."""


@dataclass(frozen=True)
class SealedShaft:
    """The trapped air column of a sealed shaft (SP7 step S5; design 4.8, D-SP7-26;
    docs/physics.md, "The sealed shaft").

    The carriage seals the bore (diameter bore_m [m], area A = pi bore^2 / 4) above a gap
    gap_m = h_0 [m] of air trapped at the push-start pressure p0_pa = p_0 [Pa] (p_atm at
    the track start, ``LinearMotorAssist.from_config``); as the carriage rises s [m] along
    the track the column expands adiabatically with the ratio of specific heats gamma (>
    1), uniformly and quasi-statically:

        p(s)   = p_0 (h_0 / (h_0 + s))^gamma                          [Pa]
        F_p(s) = max(0, p_0 - p(s)) A        (0 <= F_p < p_0 A)      [N]
        W_p(s) = p_0 A s - p_0 V_0 [1 - (V_0 / V)^(gamma - 1)] / (gamma - 1)   [J]

    with V_0 = A h_0 and V = A (h_0 + s): the open shaft above the carriage (p_0, the
    vehicle in the air above it) against the column below, the net force on the carriage
    against the motion, and the work done against it from s = 0 (the integral of F_p ds;
    the net force's own work on the carriage is -W_p). Valid for s >= 0
    (F_p = W_p = 0 for s <= 0, where the column would be compressed, which a push from
    rest never does). Near the end of a small-gap stroke the cooled gas expands
    non-uniformly and unsteadily, so the uniform, quasi-static adiabat is first order
    there; the bound p_0 A holds regardless. SI, pure."""

    bore_m: float
    gap_m: float
    gamma: float
    p0_pa: float

    def __post_init__(self) -> None:
        """Refuse (ValueError) a bore, gap or p_0 not finite and > 0, and a gamma not
        finite and > 1 (the work's closed form divides by gamma - 1)."""
        for label, value in (
            ("bore_m", self.bore_m),
            ("gap_m", self.gap_m),
            ("p0_pa", self.p0_pa),
        ):
            if not (math.isfinite(value) and value > 0.0):
                raise ValueError(f"sealed shaft {label} must be finite and > 0")
        if not (math.isfinite(self.gamma) and self.gamma > 1.0):
            raise ValueError("sealed shaft gamma must be finite and > 1")

    @property
    def area_m2(self) -> float:
        """The bore's cross-section A = pi bore^2 / 4 [m^2]."""
        return math.pi * self.bore_m * self.bore_m / 4.0

    @property
    def force_bound_N(self) -> float:
        """The bound p_0 A [N] that F_p never reaches (the column at zero pressure)."""
        return self.p0_pa * self.area_m2

    def pressure_pa(self, s_m: float) -> float:
        """The column's pressure p(s) = p_0 (h_0 / (h_0 + s))^gamma [Pa] at the carriage
        position s_m [m] along the track (p_0 for s <= 0)."""
        if s_m <= 0.0:
            return self.p0_pa
        return self.p0_pa * (self.gap_m / (self.gap_m + s_m)) ** self.gamma

    def force_N(self, s_m: float) -> float:
        """The column's net force on the carriage F_p(s) = max(0, p_0 - p(s)) A [N],
        against the motion, at s_m [m] (0 for s <= 0); written p_0 A (1 - (h_0 / (h_0 +
        s))^gamma) through expm1 and log1p so the difference keeps its digits near s =
        0."""
        if s_m <= 0.0:
            return 0.0
        return -self.force_bound_N * math.expm1(-self.gamma * math.log1p(s_m / self.gap_m))

    def work_J(self, s_m: float) -> float:
        """The work done against the column W_p(s) = int_0^s F_p ds' = p_0 A s - p_0 V_0
        [1 - (V_0 / V)^(gamma - 1)] / (gamma - 1) [J] from s = 0 to s_m [m] (V_0 = A h_0,
        V = A (h_0 + s); 0 for s <= 0)."""
        if s_m <= 0.0:
            return 0.0
        v0_frac = -math.expm1(-(self.gamma - 1.0) * math.log1p(s_m / self.gap_m))
        return self.force_bound_N * (s_m - self.gap_m * v0_frac / (self.gamma - 1.0))


@dataclass(frozen=True)
class PushStart:
    """The stack at push start, bound by ``LinearMotorAssist.at_push_start``.

    m_total_kg: M_0 = m_v + m_c [kg]; thrust_N: T(0), the vehicle's delivered axial
    thrust at t = 0 [N] (before impingement); g_axial_mps2: g_eff sin phi(0) [m/s^2],
    the weight component per unit mass along the track at its start; holding_force_N:
    F_0 = max(0, M_0 g_axial - (1 - f_imp) T(0)) [N], the drive force that holds the
    stack at rest (0 when the thrust alone lifts it); column_end_N: a sealed shaft's
    column force at the track end F_p(L) [N], its largest on the stroke (0 for the vented
    shaft; SP7 step S5, ``LinearMotorAssist.stall_reason``).
    """

    m_total_kg: float
    thrust_N: float
    g_axial_mps2: float
    holding_force_N: float
    column_end_N: float = 0.0


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
    ``push_time_estimate``, ``push_watches`` and ``stall_reason`` need it);
    release_speed_mps: v_release [m/s], the speed along the track at which the push
    releases before the track end (SP7 step S4a; ``phases.prelude.fly_track`` watches
    sdot - v_release; None: release at the track end; refused with a stop taper);
    shaft: the SealedShaft below the carriage (SP7 step S5), None for the vented shaft
    (refused with a stop taper under the force law: ``__post_init__``). name,
    push_time_exact (False: the push time is a result of the flown push) and
    allow_negative_drive (False: a negative drive force ends the run with
    ``drive_limit``) are class constants; extra_state_names is () for the vented shaft
    and (WORK_STATE,) for a sealed one. Forces of one instant: see the module docstring
    (drive_normal = 0, dissipated = 0: the work done against the column is held in its
    own state, not dissipated).
    """

    name: ClassVar[str] = "linear_motor"
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
    release_speed_mps: float | None = None
    shaft: SealedShaft | None = None

    @classmethod
    def from_config(
        cls, config: LinearMotorConfig, g_eff_mps2: float
    ) -> tuple[LinearMotorAssist, StraightTrack]:
        """The model (unbound) and its ``StraightTrack`` from a validated config
        (``assist.build_assist``): the config's SI properties feed the model, g_eff_mps2
        [m/s^2] is quoted in its assumptions, and the track starts at exit_altitude -
        L sin phi so that its exit sits at the configured altitude (a buried silo starts
        at -L). A sealed shaft (SP7 step S5) traps its column at p_0 = p_atm(z_start), the
        ICAO standard atmosphere's pressure at the track start's altitude
        (``atmosphere.standard_atmosphere``, which raises ValueError for a track start
        below its floor ALT_AMBIANCE_MIN_M, -5,004 m, never clamping it; the config
        refuses such a sealed track first), whatever the flight model's own
        atmosphere."""
        phi = config.track.phi_rad
        track = StraightTrack(
            length_m=config.stroke_m,
            phi_rad=phi,
            start_altitude_m=config.track.exit_altitude_m - config.stroke_m * math.sin(phi),
        )
        shaft = None
        if config.shaft == SHAFT_SEALED:
            if (
                config.shaft_bore_m is None
                or config.shaft_gap_m is None
                or config.shaft_gamma is None
            ):
                raise ValueError("a sealed shaft needs shaft_bore_m, shaft_gap_m and shaft_gamma")
            shaft = SealedShaft(
                bore_m=config.shaft_bore_m,
                gap_m=config.shaft_gap_m,
                gamma=config.shaft_gamma,
                p0_pa=float(standard_atmosphere(track.start_altitude_m).p_pa),
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
            release_speed_mps=config.release_speed_mps,
            shaft=shaft,
        )
        return model, track

    def __post_init__(self) -> None:
        """Refuse (ValueError) a control law outside CONTROL_LAWS; F_max or P_max not
        finite and > 0; t_r not finite and >= 0; a_cmd given for the force law, missing
        for the acceleration law, or not finite and > 0; a taper, carriage mass or brake
        deceleration out of range; an efficiency outside (0, 1]; f_imp outside [0, 1];
        omega_p not finite; (SP7 step S4a) a release speed not finite and > 0, or set
        together with a stop taper longer than 0 m (``tapered``: the taper is a
        release-at-L device); and (SP7 step S5) a shaft that is not a SealedShaft or None,
        or a sealed shaft under the force law with a stop taper (the taper scales the
        force toward the open shaft's holding value M g_eff sin phi - (1 - f_imp) T, so
        the column would decelerate the stack at the track end and could stop it in the
        shaft)."""
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
        v_release = self.release_speed_mps
        if v_release is not None:
            if not (math.isfinite(v_release) and v_release > 0.0):
                raise ValueError("release_speed_mps must be finite and > 0")
            if self.tapered:
                raise ValueError(
                    "release_speed_mps is refused with a stop taper (the taper is a "
                    "release-at-L device)"
                )
        if self.shaft is not None and not isinstance(self.shaft, SealedShaft):
            raise ValueError("shaft must be a SealedShaft or None (vented)")
        if self.shaft is not None and self.control == CONTROL_FORCE and self.tapered:
            raise ValueError(SEALED_TAPER_REFUSAL)

    # ------------------------------------------------------------------ the shaft

    @property
    def extra_state_names(self) -> tuple[str, ...]:
        """The extra track states: () for the vented shaft, (WORK_STATE,) for a sealed
        one (the column's work W_p [J])."""
        return () if self.shaft is None else (WORK_STATE,)

    @property
    def sealed(self) -> bool:
        """Whether the shaft below the carriage is sealed (``shaft`` set)."""
        return self.shaft is not None

    def piston_force_N(self, s_m: float) -> float:
        """The trapped column's force F_p(s) [N] on the carriage, against the motion, at
        s_m [m] along the track (``SealedShaft.force_N``); 0 for the vented shaft."""
        return 0.0 if self.shaft is None else self.shaft.force_N(s_m)

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
        = g_eff sin phi [m/s^2]; with a sealed shaft plus the column's force F_p(s) (SP7
        step S5: the drive supplies it to fly the command)."""
        a_cmd = self.accel_command_mps2 if self.accel_command_mps2 is not None else 0.0
        a = a_cmd * self.rise_fraction(t) * self.taper_weight(s_m, length_m)
        if self.shaft is None:
            return m_total_kg * (a + g_axial_mps2) - thrust_sys_N
        return m_total_kg * (a + g_axial_mps2) - thrust_sys_N + self.shaft.force_N(s_m)

    def pre_power_force_N(
        self,
        t: float,
        s_m: float,
        m_total_kg: float,
        thrust_sys_N: float,
        g_axial_mps2: float,
        length_m: float,
    ) -> float:
        """The law's force before the power term [N] (inputs as in ``command_force_N``):
        for the force law min(F_lim(t), F_max), scaled inside the stop taper toward the
        holding value F_h = M g_axial - T_sys by the taper weight, F_h + (min(F_lim(t),
        F_max) - F_h) w(s) (untouched where w = 1: before the taper and without one);
        for the acceleration law min(command, F_max), the command already tapered.
        ``drive_force_N`` caps this force by P_max / sdot (D-SP7-50: the cap applies to
        the force that is flown, after the taper)."""
        if self.control == CONTROL_FORCE:
            force = self.force_limit_N(t)
            w = self.taper_weight(s_m, length_m)
            if w < 1.0:
                hold = m_total_kg * g_axial_mps2 - thrust_sys_N
                force = hold + (force - hold) * w
            return force
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
        force (``pre_power_force_N``: the force law's force limit scaled toward the
        holding value F_h = M g_axial - T_sys by the taper weight, or the acceleration
        law's capped command, its taper in the command), capped by P_max / sdot for
        sdot > 0. The power cap applies to the force that is flown, after the taper
        (D-SP7-50, design 4.10): F = min(F_h + (min(F_lim(t), F_max) - F_h) w(s), P_max /
        sdot) under the force law, so F sdot <= P_max on every branch, the taper's
        included (where the holding value itself exceeds P_max / sdot the cap binds below
        it and the stack slows)."""
        force = self.pre_power_force_N(t, s_m, m_total_kg, thrust_sys_N, g_axial_mps2, length_m)
        if sdot_mps > 0.0:
            force = min(force, self.power_max_W / sdot_mps)
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
        """sddot = (F + T_sys - F_p)/M - g_eff sin phi with F from ``drive_force_N`` and
        F_p the sealed shaft's column force on the carriage (0 vented); F_int = m_v
        (sddot + g_eff sin phi) - T, so under the force law a sealed shaft lowers it by
        (m_v/M) F_p (the column pulls the carriage, which carries the vehicle); no
        normal drive force, no dissipation; the extra state's rate dW_p/dt = F_p sdot
        with a sealed shaft (none vented). Inputs as in ``AssistModel.state_rate`` (SI,
        track frame, t on the push clock); the model must be bound (``at_push_start``)."""
        self._bound()
        g_axial = g_eff_mps2 * math.sin(track.phi(s_m))
        total = m_vehicle_kg + m_carriage_kg
        t_sys = (1.0 - self.f_imp) * thrust_axial_N
        force = self.drive_force_N(t, s_m, sdot_mps, total, t_sys, g_axial, track.length_m)
        if self.shaft is None:
            sddot = (force + t_sys) / total - g_axial
            rate = np.zeros(0)
        else:
            piston = self.shaft.force_N(s_m)
            sddot = (force + t_sys - piston) / total - g_axial
            rate = np.array([piston * sdot_mps])
        return AssistForces(
            sddot_mps2=sddot,
            drive_force_N=force,
            drive_normal_N=0.0,
            interface_force_N=m_vehicle_kg * (sddot + g_axial) - thrust_axial_N,
            dissipated_W=0.0,
            extra_rate=rate,
        )

    def initial_extra(self) -> np.ndarray:
        """The extra states at push start: none for the vented shaft, W_p = 0 J for a
        sealed one."""
        return np.zeros(len(self.extra_state_names))

    # ------------------------------------------------------------- the push protocol

    def at_push_start(
        self,
        m_vehicle_kg: float,
        thrust_axial_N: float,
        g_eff_mps2: float,
        track: TrackGeometry,
    ) -> LinearMotorAssist:
        """A copy bound to the push start: M_0 = m_vehicle_kg + m_c [kg], T(0) =
        thrust_axial_N [N], g_axial = g_eff_mps2 sin phi(0) [m/s^2], the holding
        force F_0 = max(0, M_0 g_axial - (1 - f_imp) T(0)) [N] and a sealed shaft's
        column force at the track end F_p(L) [N] (``PushStart``; 0 vented). A push starts
        at s = 0, where F_p = 0, so the column does not enter F_0."""
        total = m_vehicle_kg + self.carriage_mass_kg
        g_axial = g_eff_mps2 * math.sin(track.phi(0.0))
        hold = max(0.0, total * g_axial - (1.0 - self.f_imp) * thrust_axial_N)
        if self.shaft is None:
            return replace(self, push_start=PushStart(total, thrust_axial_N, g_axial, hold))
        column = self.shaft.force_N(track.length_m)
        start = PushStart(total, thrust_axial_N, g_axial, hold, column)
        return replace(self, push_start=start)

    def stall_reason(self) -> str | None:
        """The stall at push start (D-SP7-24): F_max + (1 - f_imp) T(0) <= M_0 g_eff sin
        phi_0, the drive at its limit and the thrust cannot lift the stack; with a sealed
        shaft (SP7 step S5) also F_max + (1 - f_imp) T(0) <= M_0 g_eff sin phi_0 + F_p(L),
        the drive at its limit and the push-start thrust do not outweigh the weight and
        the column at the track end, where the column is largest. A conservative guard
        for every push: beyond the point where F_p(s) = F_max + (1 - f_imp) T - M g_eff
        sin phi the column outweighs the drive and the thrust, and the speed falls from
        its peak there; a cold step push (the power cap never reached) then stops before
        L (and swings about that point, with no event to end the run, which would reach
        t_max_s and the planner's RuntimeError) only when (F_max + (1 - f_imp) T - M g_eff
        sin phi) L <= W_p(L), and between W_p(L)/L and F_p(L) it would still reach L,
        slowly, on its momentum, which the rule refuses too. Not credited: the stack's
        momentum, a rising thrust and a falling mass, and with a release speed a release
        at that speed before the track end, where the column is below F_p(L) (the flag
        says so). The one-line reason with the numbers, None when the push can start.
        Needs the bound model."""
        b = self._bound()
        lift = self.force_max_N + (1.0 - self.f_imp) * b.thrust_N
        weight = b.m_total_kg * b.g_axial_mps2
        if lift > weight:
            if self.shaft is None or lift > weight + b.column_end_N:
                return None
            credited = (
                "the stack's momentum, a rising thrust and a falling mass are not credited"
                if self.release_speed_mps is None
                else (
                    "the stack's momentum, a rising thrust, a falling mass and a release at "
                    "the release speed before the track end, where the column is below "
                    "F_p(L), are not credited"
                )
            )
            return (
                f"drive_stall: the drive at F_max and the thrust at push start cannot hold "
                f"the stack against the sealed shaft's trapped column at the track end: F_max "
                f"+ (1 - f_imp) T(0) = {lift:.6g} N <= M_0 g_eff sin phi + F_p(L) = "
                f"{weight + b.column_end_N:.6g} N (F_max = {self.force_max_N:.6g} N, T(0) = "
                f"{b.thrust_N:.6g} N, f_imp = {self.f_imp:g}, M_0 = {b.m_total_kg:.6g} kg, "
                f"F_p(L) = {b.column_end_N:.6g} N of the bound p_0 A = "
                f"{self.shaft.force_bound_N:.6g} N); the push could stop in the shaft "
                f"({credited}), so the run stopped on the track at push start (nothing "
                "moved; the felt g and interface-force metrics are None)"
            )
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
        It leaves out the power limit, the caps, the taper, the burn and a sealed
        shaft's column (SP7 step S5), so it is not the push time; it is exact whenever
        the net acceleration is a_p r(t) throughout (the uncapped, untapered acceleration
        law, the column included, since that law supplies F_p; a cold, untapered
        force-law push in a vented shaft that the power limit never reaches). Needs the
        bound model; ValueError when a_p <= 0 (a stall)."""
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
        before the power term (``pre_power_force_N``; after the force law's rise and
        before its taper this is sdot - P_max / F_max; inside the force law's taper the
        tapered force, the force the cap applies to, D-SP7-50: the margin is that of
        P_max / sdot over the flown force, written as a product so it stays finite at
        sdot = 0), two-way (POWER_LIMIT_END when it stops binding); for the
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
        """(F_pre sdot - P_max) / F_max [m/s] with F_pre = ``pre_power_force_N`` (the
        force law's tapered force inside its taper; POWER_LIMIT; inputs as in
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
        """The nominal release position [m] along the track: the track end L. A push
        with a release speed (``release_speed_mps``) releases where sdot reaches it,
        which only the flown push knows (``phases.prelude.TrackExit.release_position_m``;
        the metrics read it from the trace, ``metrics.release_point``)."""
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

    def facility_length_m(
        self, track: TrackGeometry, v_exit_mps: float, s_release_m: float | None = None
    ) -> float:
        """Facility length [m]: max(L, s_release + d_brake), with d_brake from the speed
        at release v_exit_mps [m/s] and s_release_m [m] the release position along the
        track (None: the track end L, so L + d_brake): the carriage brakes in the stroke
        left beyond an early release, and past L only by what that stroke does not
        hold."""
        s_release = self.release_position_m(track) if s_release_m is None else s_release_m
        return max(track.length_m, s_release + self.braking_distance_m(v_exit_mps))

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
        """The control-law line: the law, its limits, its rise and the no-pull rule (the
        acceleration law's force with a sealed shaft's column F_p(s), SP7 step S5; the
        vented line unchanged)."""
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
        force = (
            "M (a + g_eff sin phi) - (1 - f_imp) T,"
            if self.shaft is None
            else "M (a + g_eff sin phi) - (1 - f_imp) T + F_p(s) (the sealed shaft's column),"
        )
        return (
            f"linear_motor: acceleration law, net acceleration command a_cmd = {a_g:g} g0 "
            f"(assumed) {rise}; the drive force {force} capped "
            f"by F_max = {f_kn:g} kN and P_max / sdot with P_max = {p_mw:g} MW (assumed); "
            f"while a cap binds the acceleration follows from the capped force{never_pulls}"
        )

    def release_assumption(self) -> str:
        """The release line: a release at the release speed (``release_speed_mps``,
        SP7 step S4a), else ``taper_assumption`` (the track end, with or without the
        stop taper)."""
        v_release = self.release_speed_mps
        if v_release is None:
            return self.taper_assumption()
        return (
            f"linear_motor: release where the speed along the track reaches the release "
            f"speed {v_release:g} m/s (assumed), before the track end, or at the track end "
            "(s = L) when the push does not reach it there (flag release_speed_not_reached); "
            "no stop taper: the drive force drops to zero in a step at release, and the "
            "carriage brakes from the release (facility max(L, s_release + braking "
            "distance): within the stroke left, or past the track end when the braking "
            "distance exceeds it)"
        )

    def taper_assumption(self) -> str:
        """The release line of a push released at the track end: the stop taper, or a
        step release (the acceleration law's holding force at L with a sealed shaft's
        column F_p(L), SP7 step S5; the force law's taper is refused with a sealed shaft;
        the vented line unchanged)."""
        if not self.tapered:
            return (
                "linear_motor: release at the track end (s = L) with no stop taper: the drive "
                "force drops to zero in a step at release"
            )
        hold = "the holding force M g_eff sin phi - (1 - f_imp) T"
        if self.shaft is not None:
            hold += " plus the sealed shaft's column force F_p(L) at the track end"
        if self.control == CONTROL_FORCE:
            what = (
                f"the force limit is scaled toward {hold} by min(1, (L - s) / s_taper), and "
                "the power cap P_max / sdot applies to the scaled force (D-SP7-50)"
            )
            at_end = (
                f"at L the drive force is {hold} (zero net acceleration) unless the power cap "
                "binds there (never on a straight track a config builds)"
            )
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
        """The shaft line: vented (or, SP7 step S5, sealed below the carriage, its column
        in ``sealed_assumptions``, and the vented shaft that a planar run's track-push
        line names, and with a release speed an early-release line, read as the shaft
        open above the carriage), no friction, and what the neglected air drag on the
        vehicle in the shaft during the push would do under this control law (with a
        release speed, SP7 step S4a: what it would do to where the push reaches that
        speed, and to the speed of a push that releases at the track end without reaching
        it; after a release before the track end the flight model flies on in the shaft
        after it, whether the vehicle leaves the shaft or falls back in it, which the run's
        early-release line words: fix round 5, m2, C5-m3)."""
        if self.release_speed_mps is not None and self.control == CONTROL_FORCE:
            drag = (
                "under the force law it would delay the release at the release speed (the "
                "release position and the push time are biased low; the speed at release "
                "stays the release speed while the push still reaches it before the track "
                "end, and is biased high when the push releases at the track end without "
                "reaching it) and raise the interface force (by D m_c / M at a given drive "
                "force, zero then without a carriage mass, and in the power phase also "
                "through P_max / sdot at the lower speed) and the drive work (a longer push "
                "to the same speed): both are biased low; the felt g and the mean "
                "acceleration are biased high"
            )
        elif self.release_speed_mps is not None:
            drag = (
                "under the acceleration law the drive force would absorb it while no cap "
                "binds (the drive work, the peak drive power and the interface force are "
                "biased low, as for constant_accel, and the release position is unchanged), "
                "and while a cap binds it would delay the release at the release speed (the "
                "release position and the push time biased low, or the speed at a release "
                "at the track end biased high; drag can also make a cap bind that the "
                "drag-free push never reaches)"
            )
        elif self.control == CONTROL_FORCE:
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
        if self.shaft is None:
            shaft = "shaft vented (no air column)"
        else:
            named = (
                "the track-push line of a planar run"
                if self.release_speed_mps is None
                else (
                    "the track-push line of a planar run and the early-release line of a "
                    "release before the track end"
                )
            )
            shaft = (
                "shaft sealed below the carriage (its trapped air column: the three lines "
                "that start 'linear_motor: sealed shaft'; above the carriage the shaft is "
                f"open at the mouth: the vented shaft named by {named} is, for this run, that "
                "open shaft above the carriage)"
            )
        if self.release_speed_mps is not None:
            return (
                f"linear_motor: {shaft}, no friction; air drag on the "
                "vehicle in the shaft is neglected during the push (after a release before "
                "the track end the flight model flies on in the shaft after it, as the run's "
                f"early-release line says): {drag}"
            )
        return (
            f"linear_motor: {shaft}, no friction; air drag on the vehicle in the shaft is "
            f"neglected: {drag}"
        )

    def sealed_assumptions(self) -> tuple[str, ...]:
        """The sealed shaft's three lines (SP7 step S5; none for the vented shaft): the
        column model (bore, gap, p_0, gamma, assumed when it differs from the ICAO air's
        KAPPA_AIR, the pressure law, the force on the carriage and its bound, what it does
        under this control law, the work done against it); what is not modelled on the
        push, with the direction of each bias (the air pushed out of the mouth ahead of
        the vehicle, the open shaft's hydrostatic drop, the non-uniform, unsteady
        expansion of the cooled gas near the end of a small-gap stroke, the exhaust of an
        engine lit on the track); and what is not modelled after the release or in the
        geometry (the column after the release and the braking metrics it bounds, the
        bore checked against the run's A_ref section only, the vent area a vented shaft
        needs). Under the force law the column line's comparison with a vented shaft
        names the exit speed, or with a release speed the release position and the push
        time. With a release speed, under either law, the column line adds that the
        sealed push's speed can peak and fall inside the track, so that a release speed
        just below the peak can be passed over inside one integrator step (the push then
        releases at the track end with the flag release_speed_not_reached), and the third
        line adds what a release before the track end leaves out: the cavity under the
        departing vehicle, closed below by the braking carriage, and the exhaust of a
        stage lit in it. The reference numbers are the surveys' cases, labelled as such,
        not this run's."""
        sh = self.shaft
        if sh is None:
            return ()
        measured = (
            "on every push S5's tests and probes measured (docs/physics.md, \"The sealed "
            'shaft"; not guaranteed: a rising force or thrust and a falling mass give the '
            "slower sealed stack more force per metre)"
        )
        if self.control == CONTROL_FORCE:
            same_state = (
                "under the force law the drive's force is unchanged, so the stack slows: the "
                "interface force is lower by (m_v / M) F_p and the felt g by F_p / (M g0) "
                "than in a vented shaft at the same state (on a cold push's F_max plateau "
                "the felt g falls as F_p grows, so the felt g at the end of the rise is the "
                "plateau's largest, not a value held on it)"
            )
            if self.release_speed_mps is None:
                law = f"{same_state}, and the exit speed is lower {measured}"
            else:
                law = (
                    f"{same_state}; with the release speed the stack reaches it later along "
                    "the track: the release position and the push time are larger than in "
                    f"a vented shaft {measured}; the speed at release stays the release "
                    "speed while the push still reaches it before the track end, and is "
                    "below it when the push reaches the track end first (flag "
                    "release_speed_not_reached)"
                )
        else:
            law = (
                "under the acceleration law the drive supplies F_p too: while no cap binds "
                "the drive force and power rise by F_p and F_p sdot and the interface force "
                "is unchanged, and while no cap binds on the whole push the drive work rises "
                "by W_p and the electricity by W_p / efficiency; a cap that binds leaves the "
                "stack to slow as under the force law"
            )
        after_release = (
            "(the carriage brakes by its own closed form with no column force on it, and the "
            "vehicle above it sees the shaft open at the mouth, flown as the vented shaft's "
            "flight model flies it)"
        )
        if self.release_speed_mps is not None:
            law = (
                f"{law}; the speed of a sealed push can peak inside the track and then fall, "
                "where the drive's force and the thrust's share fall below the weight and "
                "the column (under a power cap once P_max / sdot drops below M g_eff sin phi "
                "+ F_p(s) - (1 - f_imp) T; under the force law also in a slow rise against a "
                "gap far below the sources' 1 to 20 m), and a release speed just below such "
                "a peak can be passed over inside one integrator step (up to 2e-5 m/s below "
                "it on the pushes measured): the push then releases at the track end with "
                "the flag release_speed_not_reached although it reached the release speed "
                '(docs/physics.md, "The sealed shaft")'
            )
            after_release = (
                "(the carriage brakes by its own closed form with no column force on it, and "
                "the vehicle above it is flown as the vented shaft's flight model flies it: "
                "in the shaft open at the mouth after a release at the track end, while "
                "after a release before the track end the braking carriage still seals the "
                "bore below the departing vehicle, and the cavity that opens between the "
                "vehicle's base and the carriage, fed only through the annulus between the "
                "bore and the vehicle, is left out: a suction on the vehicle's base section "
                "A_body of up to about p_0 A_body (inferred; the vehicle's speed in the "
                "shaft after the release is biased high), and the exhaust of a stage lit "
                "before its base clears the mouth, trapped in that cavity (inferred; the "
                "other way))"
            )
        if sh.gamma == KAPPA_AIR:
            stated = (
                "the bore and the gap assumed; gamma that of air in the ICAO standard atmosphere"
            )
        else:
            stated = (
                "the bore, the gap and gamma assumed; air in the ICAO standard atmosphere has "
                f"{KAPPA_AIR:g}"
            )
        return (
            f"linear_motor: sealed shaft: the carriage seals the {sh.bore_m:g} m bore (A = "
            f"{sh.area_m2:.6g} m^2) above a {sh.gap_m:g} m gap of air trapped at p_0 = "
            f"{sh.p0_pa:.6g} Pa (the ICAO standard atmosphere at the track start), which "
            f"expands adiabatically with gamma = {sh.gamma:g} ({stated}) as the carriage "
            "rises, uniform and quasi-static: p(s) = p_0 (h_0 / (h_0 + s))^gamma; its force "
            "F_p(s) = (p_0 - p(s)) A acts on the carriage against the motion, below its "
            f"bound p_0 A = {sh.force_bound_N:.6g} N, from push start to the release; {law}; "
            "W_p = int F_p sdot dt = p_0 A s - p_0 V_0 [1 - (V_0 / V)^(gamma - 1)] / (gamma "
            "- 1) is the work done against the column, drive work the stack does not "
            "receive (p_0 dV done on the atmosphere above, less the internal energy the "
            "expanding gas gives up), booked beside the assist energy identity's terms, not "
            "as dissipated; p_0 A and W_p scale with the bore's area",
            "linear_motor: sealed shaft, not modelled on the push: the air ahead of the "
            "vehicle pushed out of the mouth by the rising stack (a momentum flux of the "
            "order of rho v^2 A_bore at the exit; survey 08's reference case, 76.7 m/s in a "
            "3.7 m bore: about 77 kN, plus 4 to 23 kN at 3 g0 to accelerate the air pushed "
            "out, 0.4% to 0.5% of a 20.81 MN interface force), which acts on the vehicle as "
            "the neglected shaft drag does; the open shaft's hydrostatic drop over the "
            "stroke (the open side is held at p_0, so F_p is biased high by up to rho g s "
            "sin phi A: about 13 kN, 1.2% of F_p(L), for a 3.7 m bore, a 5 m gap and a 100 "
            "m vertical stroke); the non-uniform, unsteady expansion near the end of a "
            "small-gap stroke (survey 08's case: the gas has cooled to 35 to 110 K, from "
            "about 288 K, for 0.5 to 10 m gaps, and its sound speed, 118 to 211 m/s, is only "
            "1.5 to 3 times the carriage's 76.7 m/s), so the uniform, quasi-static adiabat "
            "is first order there: the face pressure would be lower and F_p nearer "
            "its bound, so F_p is biased low there (inferred; heat from the walls would act "
            "the other way; the bound p_0 A holds regardless); and, for an engine lit on "
            "the track, its exhaust, which the sealing carriage leaves only the annulus "
            "between the bore and the vehicle to escape by (0.231 m^2, 2.15% of a 3.7 m "
            "bore around a 3.66 m body: survey 07's case): the pressure it would build "
            "above the carriage, which would dominate the push (inferred, not computed), is "
            "left out (the thrust and the impingement are those of the open shaft)",
            "linear_motor: sealed shaft, not modelled after the release and in the "
            f"geometry: the trapped column after the release {after_release}; the "
            f"column's pull, up to p_0 A = {sh.force_bound_N:.6g} N, would add to the "
            "brake's m_c (a_b - g_eff sin phi) (0.78 MN for a 5 g0 brake on a 20 t carriage "
            "on a vertical track), so the brake force, the brake energy and the facility "
            "length are upper bounds, a massless carriage leaves the column no mass to act "
            "on, and a stopped carriage is pulled back down by about p_0 A + m_c g_eff sin "
            "phi, which the brake would have to hold; the bore is checked against the "
            "diameter sqrt(4 A_ref / pi) of the run's A_ref only (the main-body section in "
            "the vehicle files), not the vehicle's largest section, so a wider fairing that "
            "starts below the mouth is not checked (the F9 class's 5.2 m fairing, 30.0 to "
            "43.1 m below the mouth of a 100 m silo, would not pass a 3.7 m bore, and a bore "
            "that clears it has more than (5.2 / 3.7)^2 = 1.975 times the area (3.58 times "
            "for the 7.0 m shaft the 2-D scene draws), so more than 1.975 times p_0 A and "
            "W_p at the same gap); and a vented shaft, the alternative, needs vents of about "
            "the bore area (inferred, survey 07's case: a 3.7 m bore around a 3.66 m body is "
            "choked)",
        )

    def assumptions(self) -> tuple[str, ...]:
        """The drive's assumption lines: the control law, its limits and the no-pull
        rule, the power limit's meaning, the release and taper, the carriage, the
        braking closed forms, the impingement, the shaft and the neglected shaft air
        drag, a sealed shaft's three lines (``sealed_assumptions``, SP7 step S5; none for the
        vented shaft, whose ten lines are S4a's), the track gravity, the clamp and the
        ignition rule of the drive."""
        return (
            self.control_assumption(),
            "linear_motor: P_max is the mechanical power at the carriage (F sdot); the "
            "electricity is the positive drive work / efficiency and the electrical power "
            f"peak the mechanical peak / efficiency, drive efficiency {self.efficiency:g} "
            "(assumed), which moves no trajectory",
            self.release_assumption(),
            f"linear_motor: carriage mass {units.kg_to_t(self.carriage_mass_kg):g} t (assumed)",
            "linear_motor: carriage braking in closed form at a constant total deceleration "
            f"a_b = {units.to_g(self.brake_decel_mps2):g} g0 (assumed): distance v^2 / (2 "
            "a_b), time v / a_b, brake force m_c (a_b - g_eff sin phi), brake energy "
            "(1/2) m_c v^2 (1 - g_eff sin phi / a_b); no braking phase in the trace",
            f"linear_motor: exhaust impingement fraction {self.f_imp:g} (assumed); the "
            "system keeps (1 - f_imp) T of the on-track thrust",
            self.shaft_assumption(),
            *self.sealed_assumptions(),
            self.track_gravity_assumption(),
            "linear_motor: vehicle clamped to the carriage during any hold before the push",
            "linear_motor: a release-referenced stage-1 ignition lights at the flown release "
            "plus t_ign_s (the push time is a result of the push); one lit on the track must "
            "be stated from push_start (a release-referenced t_ign_s < 0 on a stage that "
            "lights is refused)",
        )
