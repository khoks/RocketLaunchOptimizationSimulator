"""Gravity models, the state layout and the right-hand side of the 1-D vertical ascent.

Everything is SI, radians and pure: no I/O, no globals, no printing. Frames:

- Ascent (1-D, Phase 1): one axis, +z up, z = 0 at the pad or silo mouth, r = r_datum + z
  with r_datum = R_EARTH_M. The velocity v = dz/dt is signed (positive upward). Earth
  rotation is off in Phase 1 (omega_p = 0), so inertial and Earth-relative velocities
  coincide. Gravity is g(r) = mu / r^2 (``InverseSquareGravity``); the constant-g model
  exists only for analytic tests.
- Track (the ASSIST phase): 1-DOF along the track, arc length s from the track start,
  flat local frame with the constant g_eff = mu / R_E^2 - omega_p^2 R_E
  (``g_eff_track``); Coriolis neglected. The state is [s, sdot, m, *extra, E_drive,
  W_thrust, J_mass] (``track_layout``), the forces come from the assist model
  (``TrackParams.assist``) and the three energy quadratures feed the assist energy
  identity (``losses.assist_energy_budget``).

The full derivation lives in docs/physics.md ("Frames and datum", "1-D ascent state and
equations of motion", "Gravity", "Silo model", "Assist energy identity").
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

import numpy as np

from launchsim.constants import MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M
from launchsim.units import to_g

if TYPE_CHECKING:
    from launchsim.assist.base import AssistForces, AssistModel, TrackGeometry
    from launchsim.vehicle import ThrustSchedule


# ----------------------------------------------------------------------------- gravity


class Gravity(Protocol):
    """Downward gravitational acceleration magnitude as a function of radius.

    Inputs: r_m, distance from Earth's centre [m]. Output: g [m/s^2], positive downward
    (toward decreasing r). Frame-free: the caller applies the sign.
    """

    def __call__(self, r_m: float) -> float:
        """Gravitational acceleration magnitude [m/s^2] at radius r_m [m]."""
        ...


@dataclass(frozen=True)
class InverseSquareGravity:
    """Point-mass gravity g(r) = mu / r^2.

    Inputs: mu_m3s2, gravitational parameter [m^3/s^2]; r_m [m]. Output: [m/s^2], positive
    downward. This is the ascent gravity model for every run (CLAUDE.md: gravity in the
    ascent is mu/r^2).
    """

    mu_m3s2: float

    def __post_init__(self) -> None:
        if self.mu_m3s2 <= 0.0:
            raise ValueError("mu must be > 0")

    def __call__(self, r_m: float) -> float:
        """g = mu / r^2 [m/s^2] at radius r_m [m]."""
        return self.mu_m3s2 / (r_m * r_m)


@dataclass(frozen=True)
class ConstantGravity:
    """Uniform gravity g(r) = g_mps2, independent of radius.

    Analytic tests only; never constructed from configuration. It exists so that the
    closed forms in the validation tests (rocket equation with gravity, ballistic apex,
    ignition-delay loss) hold exactly. Inputs: g_mps2 [m/s^2]. Output: [m/s^2], positive
    downward.
    """

    g_mps2: float

    def __post_init__(self) -> None:
        if self.g_mps2 < 0.0:
            raise ValueError("a constant gravity must be >= 0 (0 is the vacuum, no-gravity case)")

    def __call__(self, r_m: float) -> float:
        """The constant g [m/s^2]; r_m [m] is ignored."""
        return self.g_mps2


def planar_rotation_rate(lat_rad: float, az_rad: float) -> float:
    """Planar Earth rotation rate omega_p = omega_E cos(lat) sin(az) [rad/s].

    Inputs: geodetic latitude lat_rad [rad]; launch azimuth az_rad [rad], measured from
    north through east. Output: the rotation rate of the launch plane about the axis
    normal to it [rad/s], exact for an equatorial east launch and an approximation
    otherwise (CLAUDE.md ascent frame). Phase 1 forces omega_p = 0; Phase 2 uses this.
    """
    return OMEGA_EARTH_RADS * math.cos(lat_rad) * math.sin(az_rad)


def g_eff_track(omega_p_rads: float) -> float:
    """Constant effective gravity on the track, g_eff = mu / R_E^2 - omega_p^2 R_E [m/s^2].

    Inputs: omega_p_rads, the planar rotation rate [rad/s] (0 in Phase 1). Output:
    [m/s^2], positive downward, in the flat local track frame. Centrifugal relief is
    folded in; Coriolis is neglected (stated in every assumptions list).
    """
    return MU_EARTH_M3S2 / (R_EARTH_M * R_EARTH_M) - omega_p_rads * omega_p_rads * R_EARTH_M


# ------------------------------------------------------------------------ state layout


@dataclass(frozen=True)
class StateLayout:
    """Names of the entries of a state vector and their indices.

    Every module that reads a state vector goes through this helper (``index``, ``get``,
    ``build``) so no integer index is written anywhere else. Inputs: names, a tuple of
    unique state names carrying their unit suffix (``z_m``, ``v_mps``, ``m_kg``, ...).
    """

    names: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(set(self.names)) != len(self.names):
            raise ValueError("state names must be unique")

    def __len__(self) -> int:
        return len(self.names)

    def index(self, name: str) -> int:
        """Index of the state called name; raises KeyError if absent."""
        try:
            return self.names.index(name)
        except ValueError:
            raise KeyError(f"no state named {name!r}; states are {self.names}") from None

    def get(self, y: np.ndarray, name: str) -> Any:
        """The entry called name of a state vector (shape (n,)) or of a time series
        (shape (n, n_samples)); returns a float or a row respectively."""
        return y[self.index(name)]

    def zeros(self) -> np.ndarray:
        """An all-zero state vector of this layout."""
        return np.zeros(len(self.names))

    def build(self, **values: float) -> np.ndarray:
        """A state vector with the named entries set and every other entry zero."""
        y = self.zeros()
        for name, value in values.items():
            y[self.index(name)] = value
        return y


class DynamicsModel(Protocol):
    """What the phase engine and the planner need from a dynamics model.

    state_names: the layout of the state vector; i_mass: index of the vehicle mass [kg];
    rhs(t, y, params): time derivative of y [SI per second]; altitude(y) [m] above the
    datum and speed(y) [m/s], both frame-specific to the model. ``VerticalDynamics1D``
    implements it now; Phase 2 adds ``PlanarDynamics2D`` with the polar state.
    state_names and layout are class-level constants of a model (ClassVar here and in
    every implementation, so a static checker accepts the implementations).
    """

    state_names: ClassVar[tuple[str, ...]]
    layout: ClassVar[StateLayout]

    @property
    def i_mass(self) -> int:
        """Index of the vehicle mass [kg] in the state vector."""
        ...

    def rhs(self, t: float, y: np.ndarray, params: Any) -> np.ndarray:
        """dy/dt at absolute time t [s] for state y with the phase parameters."""
        ...

    def altitude(self, y: np.ndarray) -> Any:
        """Altitude above the datum [m] of a state vector or time series."""
        ...

    def speed(self, y: np.ndarray) -> Any:
        """Speed magnitude [m/s] of a state vector or time series."""
        ...


# ------------------------------------------------------------------- 1-D vertical model

VERTICAL_STATE_NAMES: tuple[str, ...] = (
    "z_m",
    "v_mps",
    "m_kg",
    "J_vac_mps",
    "J_grav_mps",
    "J_alt_mps",
    "J_bp_mps",
    "J_steer_mps",
)
"""State of the 1-D vertical ascent: altitude, signed velocity, mass and the five loss
quadratures (vacuum delta-v, gravity, altitude part of gravity, back-pressure, steering)."""

VERTICAL_LAYOUT = StateLayout(VERTICAL_STATE_NAMES)

# Indices derived from the layout (never written as integers).
_IZ = VERTICAL_LAYOUT.index("z_m")
_IV = VERTICAL_LAYOUT.index("v_mps")
_IM = VERTICAL_LAYOUT.index("m_kg")
_IJ_VAC = VERTICAL_LAYOUT.index("J_vac_mps")
_IJ_GRAV = VERTICAL_LAYOUT.index("J_grav_mps")
_IJ_ALT = VERTICAL_LAYOUT.index("J_alt_mps")
_IJ_BP = VERTICAL_LAYOUT.index("J_bp_mps")
_IJ_STEER = VERTICAL_LAYOUT.index("J_steer_mps")


@dataclass(frozen=True)
class VerticalParams:
    """Parameters of one 1-D ascent phase.

    gravity: the Gravity model (mu/r^2 in runs; constant only in analytic tests);
    g_ref_mps2: reference gravity [m/s^2] that splits the gravity loss into a duration
    part (g_ref) and an altitude part (g - g_ref); schedule: the stage's ThrustSchedule
    on the absolute run clock, or None for an unpowered phase; r_datum_m: radius [m] of
    z = 0 (R_EARTH_M: the pad or silo mouth); p_amb_pa: ambient pressure [Pa] for the
    back-pressure clamp, a constant-per-phase placeholder (0 in Phase 1, no atmosphere
    in flight; Phase 2 replaces it with p_amb(z) evaluated inside the RHS, since a
    constant over a phase would be wrong physics); v_sign: +1 while the vehicle rises,
    -1 while it falls (sigma in docs/physics.md), fixed for the phase.
    """

    gravity: Gravity
    g_ref_mps2: float
    schedule: ThrustSchedule | None
    r_datum_m: float = R_EARTH_M
    p_amb_pa: float = 0.0
    v_sign: int = 1

    def __post_init__(self) -> None:
        if self.v_sign not in (1, -1):
            raise ValueError("v_sign must be +1 (rising) or -1 (falling)")
        if self.r_datum_m <= 0.0:
            raise ValueError("r_datum_m must be > 0")
        if self.p_amb_pa < 0.0:
            raise ValueError("p_amb_pa must be >= 0")
        if self.g_ref_mps2 < 0.0:
            raise ValueError("g_ref_mps2 must be >= 0")


def rhs_vertical(t: float, y: np.ndarray, p: VerticalParams) -> np.ndarray:
    """Time derivative of the 1-D vertical state (docs/physics.md, "1-D ascent state").

    Inputs: t, absolute run time [s]; y in the VERTICAL_LAYOUT order (z [m], v [m/s],
    m [kg], J_vac, J_grav, J_alt, J_bp, J_steer [m/s]); p, the phase parameters. Output:
    dy/dt in the same order. Frame: +z up from the datum, r = r_datum + z, gravity
    positive downward, thrust along +z (magnitude T = max(0, T_vac(t) - p_amb A_e));
    the mass flow always follows T_vac(t), the vacuum thrust of the schedule (zero when
    there is no schedule, before ignition, or when the ignition fails).

        dz/dt = v
        dv/dt = T/m - g(r)
        dm/dt = -T_vac / c
        dJ_vac/dt   = T_vac / m
        dJ_grav/dt  = g sigma
        dJ_alt/dt   = (g - g_ref) sigma      <= 0 above ground while rising; sign flips
                                             with sigma (positive while falling)
        dJ_bp/dt    = (T_vac - T) / m
        dJ_steer/dt = (T/m) (1 - sigma)      sigma = p.v_sign
    """
    z = y[_IZ]
    v = y[_IV]
    m = y[_IM]
    g = p.gravity(p.r_datum_m + z)
    sigma = p.v_sign
    schedule = p.schedule
    if schedule is None:
        t_vac = 0.0
        thrust = 0.0
        mdot = 0.0
    else:
        t_vac = schedule.thrust_vac_N(t)
        # Same clamp as ThrustSchedule.thrust_N(t, p_amb), inlined so the schedule is
        # evaluated once per RHS call; the two must stay identical (test_vertical_burn
        # checks them against each other with p_amb > 0).
        thrust = max(0.0, t_vac - p.p_amb_pa * schedule.exit_area_total_m2)
        mdot = t_vac / schedule.c_mps
    a_thrust = thrust / m
    dy = np.empty(len(VERTICAL_STATE_NAMES))
    dy[_IZ] = v
    dy[_IV] = a_thrust - g
    dy[_IM] = -mdot
    dy[_IJ_VAC] = t_vac / m
    dy[_IJ_GRAV] = g * sigma
    dy[_IJ_ALT] = (g - p.g_ref_mps2) * sigma
    dy[_IJ_BP] = (t_vac - thrust) / m
    dy[_IJ_STEER] = a_thrust * (1 - sigma)
    return dy


@dataclass(frozen=True)
class VerticalDynamics1D:
    """The 1-D vertical ascent model (DynamicsModel implementation).

    State: VERTICAL_STATE_NAMES in the +z-up frame with z = 0 at the datum; parameters:
    VerticalParams; rhs: ``rhs_vertical``. altitude(y) is z [m]; speed(y) is |v| [m/s].
    """

    state_names: ClassVar[tuple[str, ...]] = VERTICAL_STATE_NAMES
    layout: ClassVar[StateLayout] = VERTICAL_LAYOUT

    @property
    def i_mass(self) -> int:
        """Index of the vehicle mass [kg] in the state vector."""
        return _IM

    def rhs(self, t: float, y: np.ndarray, params: VerticalParams) -> np.ndarray:
        """dy/dt at time t [s]; see ``rhs_vertical``."""
        return rhs_vertical(t, y, params)

    def altitude(self, y: np.ndarray) -> Any:
        """Altitude z [m] above the datum of a state vector or a (n, n_samples) series."""
        return y[_IZ]

    def speed(self, y: np.ndarray) -> Any:
        """Speed |v| [m/s] of a state vector or a (n, n_samples) series."""
        return np.abs(y[_IV])


# ------------------------------------------------------------------------ track model

TRACK_BASE_STATE_NAMES: tuple[str, ...] = ("s_m", "sdot_mps", "m_kg")
"""Position along the track [m], speed along it [m/s] and the vehicle mass [kg]."""
TRACK_QUADRATURE_NAMES: tuple[str, ...] = ("E_drive_J", "W_thrust_J", "J_mass_J")
"""Energy quadratures of the track phase: drive work, work of the on-track thrust the
system keeps, and the integral of Mdot (sdot^2/2 + g_eff z) (negative: the energy the
expelled propellant takes with it, see ``rhs_track``)."""


def track_state_names(assist: AssistModel) -> tuple[str, ...]:
    """State names of the track phase for an assist model: the base states, the model's
    extra states, then the energy quadratures."""
    return (*TRACK_BASE_STATE_NAMES, *assist.extra_state_names, *TRACK_QUADRATURE_NAMES)


def track_layout(assist: AssistModel) -> StateLayout:
    """The ``StateLayout`` of the track phase for an assist model."""
    return StateLayout(track_state_names(assist))


@dataclass(frozen=True)
class TrackParams:
    """Parameters of one ASSIST (track) phase.

    track: the TrackGeometry; assist: the AssistModel supplying the forces (its f_imp
    is the impingement fraction of the energy quadratures); carriage_mass_kg: the
    carriage mass [kg] the phase carries (the planner passes the model's own);
    g_eff_mps2: the constant track gravity [m/s^2]; schedule: the first stage's
    ThrustSchedule on the absolute clock, or None for a cold push; p_amb_pa: ambient
    pressure [Pa] for the delivered thrust (0 in Phase 1); lit: False for a sub-phase
    that ends at the ignition kink, where the engine has not lit yet and T is
    identically 0 whatever the schedule says at the closing boundary (as
    ``phases.HoldParams.lit``). layout is derived from the assist model.
    """

    track: TrackGeometry
    assist: AssistModel
    carriage_mass_kg: float
    g_eff_mps2: float
    schedule: ThrustSchedule | None
    p_amb_pa: float = 0.0
    lit: bool = True
    layout: StateLayout = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.carriage_mass_kg < 0.0:
            raise ValueError("carriage_mass_kg must be >= 0")
        if self.g_eff_mps2 <= 0.0:
            raise ValueError("g_eff_mps2 must be > 0")
        if self.p_amb_pa < 0.0:
            raise ValueError("p_amb_pa must be >= 0")
        object.__setattr__(self, "layout", track_layout(self.assist))

    def thrust_vac_N(self, t: float) -> float:
        """Vacuum thrust [N] at time t [s]: the schedule's, or 0 while not lit / cold."""
        if self.schedule is None or not self.lit:
            return 0.0
        return self.schedule.thrust_vac_N(t)

    def thrust_N(self, t: float) -> float:
        """Delivered thrust [N] at time t [s]: max(0, T_vac - p_amb A_e), 0 when cold."""
        if self.schedule is None or not self.lit:
            return 0.0
        return self.schedule.thrust_N(t, self.p_amb_pa)

    def extra(self, y: np.ndarray) -> np.ndarray:
        """The model's extra states out of a track state vector."""
        i0 = self.layout.index(TRACK_BASE_STATE_NAMES[-1]) + 1
        return np.asarray(y[i0 : i0 + len(self.assist.extra_state_names)], dtype=float)

    def forces(self, t: float, y: np.ndarray, thrust_N: float | None = None) -> AssistForces:
        """The assist model's ``AssistForces`` at time t [s] for the track state y, with
        the delivered thrust thrust_N [N] (evaluated from the schedule when None)."""
        lay = self.layout
        return self.assist.state_rate(
            t,
            float(lay.get(y, "s_m")),
            float(lay.get(y, "sdot_mps")),
            self.extra(y),
            float(lay.get(y, "m_kg")),
            self.carriage_mass_kg,
            self.thrust_N(t) if thrust_N is None else thrust_N,
            self.g_eff_mps2,
            self.track,
        )


def rhs_track(t: float, y: np.ndarray, p: TrackParams) -> np.ndarray:
    """Time derivative of the track state (docs/physics.md, "Silo model").

    Inputs: t, absolute run time [s]; y in ``p.layout`` order (s [m], sdot [m/s], m
    [kg], the model's extra states, E_drive [J], W_thrust [J], J_mass [J]); p, the
    phase parameters. Output: dy/dt in the same order. Frame: the track frame of
    ``assist/base.py`` (s along the track, z(s) the height above the track start,
    g_eff positive downward); the thrust T is the delivered thrust along the tangent
    before impingement and the mass flow follows T_vac.

        ds/dt        = sdot
        dsdot/dt     = sddot                    (from the assist model)
        dm/dt        = -T_vac / c
        dE_drive/dt  = F_drive sdot
        dW_thrust/dt = (1 - f_imp) T sdot        the system's share of the thrust work
        dJ_mass/dt   = (dM/dt) (sdot^2/2 + g_eff z(s))   dM/dt = dm/dt <= 0

    so the assist energy identity reads E_drive + W_thrust = delta(M sdot^2/2 +
    M g_eff z) - J_mass + dissipated with M = m + m_carriage.
    """
    lay = p.layout
    s = float(lay.get(y, "s_m"))
    sdot = float(lay.get(y, "sdot_mps"))
    schedule = p.schedule
    if schedule is None or not p.lit:
        t_vac = 0.0
        thrust = 0.0
        mdot = 0.0
    else:
        t_vac = schedule.thrust_vac_N(t)
        # Same clamp as ThrustSchedule.thrust_N (one schedule evaluation per RHS call).
        thrust = max(0.0, t_vac - p.p_amb_pa * schedule.exit_area_total_m2)
        mdot = t_vac / schedule.c_mps
    f = p.forces(t, y, thrust)
    dy = np.empty(len(lay))
    dy[lay.index("s_m")] = sdot
    dy[lay.index("sdot_mps")] = f.sddot_mps2
    dy[lay.index("m_kg")] = -mdot
    i0 = lay.index(TRACK_BASE_STATE_NAMES[-1]) + 1
    dy[i0 : i0 + len(p.assist.extra_state_names)] = f.extra_rate
    dy[lay.index("E_drive_J")] = f.drive_force_N * sdot
    dy[lay.index("W_thrust_J")] = (1.0 - p.assist.f_imp) * thrust * sdot
    dy[lay.index("J_mass_J")] = -mdot * (0.5 * sdot * sdot + p.g_eff_mps2 * p.track.z(s))
    return dy


def track_observables(t: float, y: np.ndarray, p: TrackParams) -> dict[str, float]:
    """Reported quantities of the track phase at one instant (SI unless the key says g).

    Inputs: t [s], the track state y (``p.layout``), the TrackParams. Output keys:
    F_drive_N (drive force along the track), F_int_N (interface force, carriage on
    vehicle; negative = tension), P_drive_W (F_drive sdot), felt_g (the vehicle's
    proper axial acceleration (F_int + T)/m_v in units of g0, which is
    (sddot + g_eff sin phi)/g0), N_vehicle_g and N_carriage_g (track-normal loads
    ``assist.base.normal_load_N`` of the vehicle and the carriage in g0 per unit mass;
    for a massless carriage the kinematic demand kappa sdot^2 + g_eff cos phi is
    reported so the value stays defined). Frame: the track frame.
    """
    from launchsim.assist.base import normal_load_N  # runtime import: no package cycle

    lay = p.layout
    s = float(lay.get(y, "s_m"))
    sdot = float(lay.get(y, "sdot_mps"))
    m_v = float(lay.get(y, "m_kg"))
    thrust = p.thrust_N(t)
    f = p.forces(t, y, thrust)
    phi = p.track.phi(s)
    kappa = p.track.kappa(s)
    m_c = p.carriage_mass_kg
    n_v = normal_load_N(m_v, sdot, kappa, phi, p.g_eff_mps2)
    if m_c > 0.0:
        n_c_per_mass = normal_load_N(m_c, sdot, kappa, phi, p.g_eff_mps2, f.drive_normal_N) / m_c
    else:
        n_c_per_mass = kappa * sdot * sdot + p.g_eff_mps2 * math.cos(phi)
    return {
        "F_drive_N": f.drive_force_N,
        "F_int_N": f.interface_force_N,
        "P_drive_W": f.drive_force_N * sdot,
        "felt_g": float(to_g((f.interface_force_N + thrust) / m_v)),
        "N_vehicle_g": float(to_g(n_v / m_v)),
        "N_carriage_g": float(to_g(n_c_per_mass)),
    }


def track_to_vertical(
    y: np.ndarray, p: TrackParams, layout: StateLayout = VERTICAL_LAYOUT
) -> np.ndarray:
    """The ascent-frame view of a track state: z = start altitude + z(s) [m], v = sdot
    sin phi [m/s] (the vertical component of the track velocity; the whole velocity on
    a vertical track), m [kg], quadratures zero. Used for event logging and the time
    series rows of the ASSIST phase; the release itself is ``phases.map_release``."""
    lay = p.layout
    s = float(lay.get(y, "s_m"))
    sdot = float(lay.get(y, "sdot_mps"))
    return layout.build(
        z_m=p.track.start_altitude_m + p.track.z(s),
        v_mps=sdot * math.sin(p.track.phi(s)),
        m_kg=float(lay.get(y, "m_kg")),
    )
