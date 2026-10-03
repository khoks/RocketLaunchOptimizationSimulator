"""The screening drive: a prescribed constant net acceleration along the track
(docs/physics.md, "Silo model (constant_accel, vertical) and every reported quantity").

The acceleration is imposed, sddot = a exactly, and the drive force is solved from the
track equation at every instant, so every closed form is exact (v_exit = sqrt(2 a L),
t_push = sqrt(2 L / a), s = a t^2 / 2) and a hot start changes only the forces and the
energy, never the exit speed. The acceleration is either the configured one or derived
from a configured exit speed v over the stroke L, a = v^2 / (2 L), in which case
t_push = 2 L / v (``config.ConstantAccelConfig``; the model below is the same either
way and only its assumptions say which was the input). Force and power limits are
Phase 3's ``linear_motor`` behind the same interface. SI, radians, pure.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

import numpy as np

from launchsim import units
from launchsim.assist.base import AssistForces, TrackGeometry
from launchsim.assist.track import StraightTrack

if TYPE_CHECKING:
    from launchsim.config import ConstantAccelConfig


@dataclass(frozen=True)
class ConstantAccelAssist:
    """Prescribed-acceleration drive (``assist.base.AssistModel``).

    net_accel_mps2: the net acceleration a along the track [m/s^2]; carriage_mass_kg:
    the carriage (sled) mass [kg] that rides with the vehicle and stays on the track;
    brake_decel_mps2: the carriage's braking deceleration after release [m/s^2];
    efficiency: electrical-to-mechanical drive efficiency in (0, 1]; f_imp: exhaust
    impingement fraction in [0, 1]; allow_negative_drive: whether a negative drive
    force (the drive braking the engine) is allowed rather than ending the run with
    status ``drive_limit``; g_eff_mps2: the track's effective gravity [m/s^2], quoted in
    the assumptions only (the dynamics receive g_eff through ``state_rate``);
    omega_p_rads: the planar rotation rate [rad/s] folded into that g_eff (g_eff =
    mu/R_E^2 - omega_p^2 R_E), quoted in the assumptions only (0 in the 1-D model; the
    planar pipeline sets the site's value); exit_speed_input_mps: the configured exit
    speed v [m/s] when net_accel_mps2 was derived from it (a = v^2 / (2 L), L the track
    length), None when the acceleration itself is the input; quoted in the assumptions
    only (the dynamics use net_accel_mps2 alone). name and
    extra_state_names are class constants (the registry key and the track state layout
    cannot change per instance). At each instant, with M = m_v + m_c and T the
    vehicle's delivered thrust along the track,

        F_drive = M (a + g_eff sin phi) - (1 - f_imp) T
        F_int   = m_v (a + g_eff sin phi) - T

    (drive_normal = 0, dissipated = 0).
    """

    name: ClassVar[str] = "constant_accel"
    extra_state_names: ClassVar[tuple[str, ...]] = ()

    net_accel_mps2: float
    carriage_mass_kg: float
    brake_decel_mps2: float
    efficiency: float = 1.0
    f_imp: float = 0.0
    allow_negative_drive: bool = False
    g_eff_mps2: float | None = None
    omega_p_rads: float = 0.0
    exit_speed_input_mps: float | None = None

    @classmethod
    def from_config(
        cls, config: ConstantAccelConfig, g_eff_mps2: float
    ) -> tuple[ConstantAccelAssist, StraightTrack]:
        """The model and its ``StraightTrack`` from a validated config
        (``assist.build_assist``): the config's SI properties feed the model, g_eff_mps2
        [m/s^2] is quoted in its assumptions, and the track starts at exit_altitude -
        L sin phi so that its exit sits at the configured altitude in the datum frame
        (a buried silo starts at -L). ``config.net_accel_mps2`` is the acceleration
        either way (the configured one, or v^2 / (2 L) from a configured exit speed,
        which is then recorded as exit_speed_input_mps for the assumptions)."""
        phi = config.track.phi_rad
        track = StraightTrack(
            length_m=config.stroke_m,
            phi_rad=phi,
            start_altitude_m=config.track.exit_altitude_m - config.stroke_m * math.sin(phi),
        )
        model = cls(
            net_accel_mps2=config.net_accel_mps2,
            carriage_mass_kg=config.carriage_mass_kg,
            brake_decel_mps2=config.brake_decel_mps2,
            efficiency=config.drive_efficiency,
            f_imp=config.exhaust_impingement_fraction,
            allow_negative_drive=config.allow_negative_drive_force,
            g_eff_mps2=g_eff_mps2,
            exit_speed_input_mps=config.exit_speed_mps,
        )
        return model, track

    def __post_init__(self) -> None:
        if self.net_accel_mps2 <= 0.0:
            raise ValueError("net_accel_mps2 must be > 0")
        if self.carriage_mass_kg < 0.0:
            raise ValueError("carriage_mass_kg must be >= 0")
        if self.brake_decel_mps2 <= 0.0:
            raise ValueError("brake_decel_mps2 must be > 0")
        if not 0.0 < self.efficiency <= 1.0:
            raise ValueError("efficiency must lie in (0, 1]")
        if not 0.0 <= self.f_imp <= 1.0:
            raise ValueError("f_imp must lie in [0, 1]")
        if not math.isfinite(self.omega_p_rads):
            raise ValueError("omega_p_rads must be finite")
        v_in = self.exit_speed_input_mps
        if v_in is not None and not (math.isfinite(v_in) and v_in > 0.0):
            raise ValueError("exit_speed_input_mps must be finite and > 0")

    def initial_extra(self) -> np.ndarray:
        """No extra states."""
        return np.zeros(0)

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
        """sddot = a; F_drive = M (a + g_eff sin phi) - (1 - f_imp) T; F_int =
        m_v (a + g_eff sin phi) - T; no normal drive force, no dissipation. Inputs as in
        ``AssistModel.state_rate`` (SI, track frame); m_carriage_kg is the carriage mass
        the phase carries (the planner passes this model's own)."""
        a_up = self.net_accel_mps2 + g_eff_mps2 * math.sin(track.phi(s_m))
        total = m_vehicle_kg + m_carriage_kg
        return AssistForces(
            sddot_mps2=self.net_accel_mps2,
            drive_force_N=total * a_up - (1.0 - self.f_imp) * thrust_axial_N,
            drive_normal_N=0.0,
            interface_force_N=m_vehicle_kg * a_up - thrust_axial_N,
            dissipated_W=0.0,
            extra_rate=np.zeros(0),
        )

    def exit_speed_mps(self, length_m: float) -> float:
        """Speed [m/s] at the end of a push over length_m [m] from rest: sqrt(2 a L)."""
        return math.sqrt(2.0 * self.net_accel_mps2 * length_m)

    def push_time_s(self, length_m: float) -> float:
        """Push duration [s] over length_m [m] from rest: sqrt(2 L / a)."""
        return math.sqrt(2.0 * length_m / self.net_accel_mps2)

    def time_to_speed_s(self, speed_mps: float) -> float:
        """Time [s] from rest at the push start to the speed speed_mps [m/s] along the
        track: v / a (constant acceleration; valid up to the exit speed, which the
        caller checks)."""
        return speed_mps / self.net_accel_mps2

    def push_time_estimate(self, track: TrackGeometry) -> float:
        """Exact push duration [s] for the track: sqrt(2 L / a)."""
        return self.push_time_s(track.length_m)

    def braking_distance_m(self, v_mps: float) -> float:
        """Carriage braking distance [m] from v_mps [m/s]: v^2 / (2 a_brake)."""
        return v_mps * v_mps / (2.0 * self.brake_decel_mps2)

    def facility_length_m(self, track: TrackGeometry, v_exit_mps: float) -> float:
        """Track length plus the braking distance [m] from the exit speed v_exit_mps."""
        return track.length_m + self.braking_distance_m(v_exit_mps)

    def track_gravity_assumption(self) -> str:
        """The track-gravity assumption line: the constant g_eff the track used [m/s^2]
        and the rotation behind it. With omega_p = 0 (the 1-D model) the Phase 1 text,
        unchanged; with rotation (planar_2d) the value, its formula mu/R_E^2 - omega_p^2
        R_E with the omega_p [rad/s] actually folded in, and Coriolis neglected on the
        track (about 2 omega_p v, 0.01 m/s^2 at 77 m/s)."""
        g_eff = (
            "constant g_eff = mu/R_E^2 - omega_p^2 R_E on the track"
            if self.g_eff_mps2 is None
            else f"constant g_eff = {self.g_eff_mps2:.7g} m/s^2 on the track"
        )
        if self.omega_p_rads == 0.0:
            return f"constant_accel: {g_eff}, omega_p = 0, Coriolis neglected"
        return (
            f"constant_accel: {g_eff} (mu/R_E^2 - omega_p^2 R_E with omega_p = "
            f"{self.omega_p_rads:.7g} rad/s, the planar rotation rate of the site), flat "
            "1-DOF track frame, Coriolis neglected"
        )

    def exit_speed_assumption(self) -> tuple[str, ...]:
        """The one line a push stated by its exit speed adds (empty when the net
        acceleration is the input, so those runs keep their Phase 1 list): the
        configured exit speed [m/s] and the derivation a = v_exit^2 / (2 L) of the
        acceleration the line before it quotes."""
        if self.exit_speed_input_mps is None:
            return ()
        return (
            "constant_accel: the net acceleration is derived from the configured exit speed "
            f"{self.exit_speed_input_mps:g} m/s (assumed) and the track length L, a = "
            "v_exit^2 / (2 L); the push time is 2 L / v_exit",
        )

    def assumptions(self) -> tuple[str, ...]:
        """The drive's assumptions, every parameter being an assumption in Phase 1; the
        track-gravity line from ``track_gravity_assumption`` (unchanged for omega_p =
        0). A push stated by its exit speed adds ``exit_speed_assumption`` after the
        net-acceleration line; one stated by its acceleration has the Phase 1 lines
        unchanged."""
        return (
            f"constant_accel: prescribed net acceleration {units.to_g(self.net_accel_mps2):g} g0 "
            "(assumed); drive force unconstrained, solved from the track equation",
            *self.exit_speed_assumption(),
            f"constant_accel: carriage mass {units.kg_to_t(self.carriage_mass_kg):g} t (assumed)",
            f"constant_accel: braking deceleration {units.to_g(self.brake_decel_mps2):g} g0 "
            "(assumed)",
            f"constant_accel: drive efficiency {self.efficiency:g} (assumed)",
            f"constant_accel: exhaust impingement fraction {self.f_imp:g} (assumed); the "
            "system keeps (1 - f_imp) T of the on-track thrust",
            "constant_accel: shaft vented (no air column), no friction",
            self.track_gravity_assumption(),
            "constant_accel: infinite jerk at push start and release",
            "constant_accel: vehicle clamped to the carriage during any hold before the push",
        )
