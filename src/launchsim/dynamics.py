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
- Ascent (2-D, Phase 2, ``planar_2d``): planar Earth-centred inertial frame in the plane
  of the site and the launch azimuth, polar state [r, theta, v_r, v_theta, m] plus six
  loss quadratures (``PLANAR_LAYOUT``), theta increasing downrange, h = r - R_E on a
  spherical Earth. The atmosphere co-rotates at the planar rate omega_p = omega_E
  cos(lat) sin(az), so drag, Mach and the loss identity use v_rel = (v_r, v_theta -
  omega_p r); gravity mu/r^2 (``rhs_planar``, ``PlanarParams``, ``PlanarDynamics2D``).
  ``H0Gravity`` is the test-only gravity of its exact 1-D reduction.

The full derivation lives in docs/physics.md ("Frames and datum", "1-D ascent state and
equations of motion", "Gravity", "Planar ascent state and equations of motion", "Planar
reductions", "2-D loss identity", "Silo model", "Assist energy identity").
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple, Protocol

import numpy as np

from launchsim.assist.base import normal_load_N
from launchsim.constants import MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M, V_REL_EPS_MPS
from launchsim.units import to_g

if TYPE_CHECKING:
    from launchsim.assist.base import AssistForces, AssistModel, TrackGeometry
    from launchsim.vehicle import DragModel, ThrustSchedule


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


def thrust_terms(
    schedule: ThrustSchedule | None, t: float, p_amb_pa: float
) -> tuple[float, float, float]:
    """The engine terms every right-hand side needs at absolute time t [s], from one
    evaluation of the schedule: (T_vac, T, mdot).

    Inputs: the stage's ThrustSchedule, or None for an unpowered (or unlit) phase;
    t [s]; p_amb_pa, the ambient pressure [Pa]. Output: the vacuum thrust T_vac [N],
    the delivered thrust T = max(0, T_vac - p_amb A_e) [N] (the same clamp as
    ``ThrustSchedule.thrust_N``, which test_vertical_burn checks against it with
    p_amb > 0) and the mass flow mdot = T_vac / c [kg/s], which follows the vacuum
    thrust; all zero without a schedule. Frame-free scalars along the thrust axis.
    """
    if schedule is None:
        return 0.0, 0.0, 0.0
    t_vac = schedule.thrust_vac_N(t)
    thrust = max(0.0, t_vac - p_amb_pa * schedule.exit_area_total_m2)
    return t_vac, thrust, t_vac / schedule.c_mps


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
    and ``PlanarDynamics2D`` (the polar state, speed = |v_rel|) implement it.
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
    t_vac, thrust, mdot = thrust_terms(p.schedule, t, p.p_amb_pa)
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
    _t_vac, thrust, mdot = thrust_terms(p.schedule if p.lit else None, t, p.p_amb_pa)
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


# --------------------------------------------------------------------- planar 2-D model

PLANAR_STATE_NAMES: tuple[str, ...] = (
    "r_m",
    "theta_rad",
    "v_r_mps",
    "v_theta_mps",
    "m_kg",
    "J_vac_mps",
    "J_grav_mps",
    "J_alt_mps",
    "J_drag_mps",
    "J_steer_mps",
    "J_bp_mps",
)
"""State of the planar ascent (docs/physics.md, "Planar ascent state and equations of
motion"): radius from Earth's centre, the downrange angle, the inertial radial and
horizontal velocity components, the mass, and the six loss quadratures of the 2-D loss
identity (vacuum delta-v, gravity, the altitude part of gravity, drag, steering,
back-pressure)."""

PLANAR_LAYOUT = StateLayout(PLANAR_STATE_NAMES)

# Indices derived from the layout (never written as integers).
_PR = PLANAR_LAYOUT.index("r_m")
_PTH = PLANAR_LAYOUT.index("theta_rad")
_PVR = PLANAR_LAYOUT.index("v_r_mps")
_PVT = PLANAR_LAYOUT.index("v_theta_mps")
_PM = PLANAR_LAYOUT.index("m_kg")
_PJ_VAC = PLANAR_LAYOUT.index("J_vac_mps")
_PJ_GRAV = PLANAR_LAYOUT.index("J_grav_mps")
_PJ_ALT = PLANAR_LAYOUT.index("J_alt_mps")
_PJ_DRAG = PLANAR_LAYOUT.index("J_drag_mps")
_PJ_STEER = PLANAR_LAYOUT.index("J_steer_mps")
_PJ_BP = PLANAR_LAYOUT.index("J_bp_mps")
_N_PLANAR = len(PLANAR_STATE_NAMES)

type AtmosphereFn = Callable[[float], tuple[float, float, float]]
"""An ambient-state function: geometric altitude [m] -> (p [Pa], rho [kg/m^3], a [m/s]),
the shape of ``atmosphere.ambient_scalar`` (the run model)."""


@dataclass(frozen=True)
class H0Gravity:
    """Radial gravity with the centrifugal term of a conserved angular momentum folded
    in: g(r) = mu / r^2 - h0^2 / r^3.

    Analytic tests only; never constructed from configuration. It is the exact 1-D
    reduction of the planar model under inertially radial thrust with no drag, where
    r v_theta = h0 stays constant (docs/physics.md, "Planar reductions"). Inputs:
    mu_m3s2 [m^3/s^2] (> 0) and h0_m2s, the specific angular momentum [m^2/s]; r_m [m].
    Output: [m/s^2], positive downward (toward decreasing r).
    """

    mu_m3s2: float
    h0_m2s: float

    def __post_init__(self) -> None:
        if self.mu_m3s2 <= 0.0:
            raise ValueError("mu must be > 0")

    def __call__(self, r_m: float) -> float:
        """g = mu / r^2 - h0^2 / r^3 [m/s^2] at radius r_m [m]."""
        return self.mu_m3s2 / (r_m * r_m) - self.h0_m2s * self.h0_m2s / (r_m * r_m * r_m)


def vacuum_atmosphere(alt_m: float) -> tuple[float, float, float]:
    """No atmosphere: (p, rho, a) = (0 Pa, 0 kg/m^3, inf m/s) at any altitude alt_m [m].

    The infinite speed of sound is a convention that makes the Mach number exactly 0,
    so a drag model evaluated in vacuum returns exactly 0 N (q = 0) and no NaN appears.
    Frame-free. For analytic tests; runs use ``atmosphere.ambient_scalar``.
    """
    return 0.0, 0.0, math.inf


class PlanarKinematics(NamedTuple):
    """Earth-relative kinematics of a planar state (docs/physics.md, "Planar ascent
    state and equations of motion").

    w_mps = v_r, the radial (up) component, and u_mps = v_theta - omega_p r, the
    horizontal (downrange) component of v_rel [m/s]; V_mps = hypot(w, u) = |v_rel|
    [m/s]; sin_g = w / V and cos_g = u / V, the sine and cosine of the Earth-relative
    flight-path angle gamma_rel above local horizontal. Below V_REL_EPS_MPS the angle
    falls back to local vertical: sin_g = 1, cos_g = 0 (v_hat_rel = r_hat). Frame: the
    local (radial, horizontal) frame, which is the same inertially and Earth-fixed.
    """

    w_mps: float
    u_mps: float
    V_mps: float
    sin_g: float
    cos_g: float


def planar_kinematics(y: np.ndarray, omega_p_rads: float) -> PlanarKinematics:
    """Earth-relative kinematics of one planar state vector.

    Inputs: y in the PLANAR_LAYOUT order (r [m], theta [rad], v_r, v_theta [m/s], ...);
    omega_p_rads, the planar rotation rate [rad/s]. Output: ``PlanarKinematics`` (w, u,
    V [m/s], sin gamma_rel, cos gamma_rel), with the local-vertical fallback below
    V_REL_EPS_MPS. Frame: planar ECI state; velocities relative to the co-rotating air.
    """
    return _kinematics(float(y[_PR]), float(y[_PVR]), float(y[_PVT]), omega_p_rads)


def _kinematics(r: float, v_r: float, v_theta: float, omega_p: float) -> PlanarKinematics:
    """``planar_kinematics`` on Python floats (the RHS path)."""
    u = v_theta - omega_p * r
    speed = math.hypot(v_r, u)
    if speed < V_REL_EPS_MPS:
        return PlanarKinematics(v_r, u, speed, 1.0, 0.0)
    return PlanarKinematics(v_r, u, speed, v_r / speed, u / speed)


class SteeringLaw(Protocol):
    """A thrust-direction law of the planar model (the run laws live in guidance.py,
    build step 21).

    direction(t [s], y (PLANAR_LAYOUT), kin (the PlanarKinematics of y)) returns the
    unit thrust direction (e_r, e_theta) in the local (radial up, horizontal downrange)
    frame; the pitch above local horizontal is atan2(e_r, e_theta). along_vrel is True
    exactly for a law that points the thrust along v_rel, e = (sin_g, cos_g) (the
    gravity turn): the RHS then sets cos psi = 1 and the steering-loss rate to exactly
    0 instead of evaluating (T/m)(1 - cos psi) from a rounding-level cos psi. The RHS
    trusts |e| = 1 and does not renormalise.
    """

    @property
    def along_vrel(self) -> bool:
        """True when the law points the thrust along v_rel."""
        ...

    def direction(self, t: float, y: np.ndarray, kin: PlanarKinematics) -> tuple[float, float]:
        """Unit thrust direction (e_r, e_theta) at time t [s] for the state y."""
        ...


@dataclass(frozen=True)
class PlanarParams:
    """Parameters of one planar flight phase.

    gravity: the Gravity model g(r) [m/s^2] (mu/r^2 in runs; ConstantGravity or
    H0Gravity only in analytic tests); omega_p_rads: planar Earth rotation rate [rad/s]
    (0 with rotation off); g_ref_mps2: reference gravity [m/s^2] of the gravity-loss
    split (g_eff at the datum in runs); schedule: the lit stage's ThrustSchedule on the
    absolute run clock, or None for an unpowered phase; drag: the DragModel, or None
    for no drag; atmosphere: altitude [m] -> (p [Pa], rho [kg/m^3], a [m/s])
    (``ambient_scalar`` in runs; ``vacuum_atmosphere`` or a test profile otherwise),
    evaluated at h = r - r_datum_m; steering: the SteeringLaw, required whenever there
    is a schedule (None only for an unpowered phase, whose thrust direction is reported
    along v_rel by convention); r_datum_m: radius [m] of the altitude datum (R_EARTH_M,
    the spherical Earth; a large radius in flat-Earth tests).
    """

    gravity: Gravity
    omega_p_rads: float
    g_ref_mps2: float
    schedule: ThrustSchedule | None
    drag: DragModel | None
    atmosphere: AtmosphereFn
    steering: SteeringLaw | None
    r_datum_m: float = R_EARTH_M

    def __post_init__(self) -> None:
        if not math.isfinite(self.omega_p_rads):
            raise ValueError("omega_p_rads must be finite")
        if not (math.isfinite(self.r_datum_m) and self.r_datum_m > 0.0):
            raise ValueError("r_datum_m must be finite and > 0")
        if not (math.isfinite(self.g_ref_mps2) and self.g_ref_mps2 >= 0.0):
            raise ValueError("g_ref_mps2 must be finite and >= 0")
        if self.schedule is not None and self.steering is None:
            raise ValueError("a planar phase with a thrust schedule needs a steering law")


class PlanarForces(NamedTuple):
    """Every force-level term of the planar RHS at one instant (SI).

    T_vac_N and T_N: vacuum and delivered thrust [N], T = max(0, T_vac - p A_e);
    mdot_kgps: mass flow [kg/s], which follows T_vac; e_r and e_theta: the unit thrust
    direction in the local frame; D_N: drag magnitude [N], along -v_hat_rel; q_pa:
    dynamic pressure 0.5 rho V^2 [Pa]; mach: V / a; V_mps: |v_rel| [m/s]; cos_psi: the
    cosine of the angle psi between thrust and v_rel (exactly 1 for an along-v_rel law
    and for an unpowered phase); sin_g: sin gamma_rel (1 below V_REL_EPS_MPS);
    g_eff_mps2: g(r) - omega_p^2 r [m/s^2]; cos_g: cos gamma_rel (0 below
    V_REL_EPS_MPS); g_mps2: g(r) [m/s^2]; w_mps and u_mps: the radial and horizontal
    components of v_rel [m/s]; p_pa, rho_kgm3 and a_mps: the ambient state at
    h = r - r_datum. Frame: local (radial up, horizontal downrange).
    """

    T_vac_N: float
    T_N: float
    mdot_kgps: float
    e_r: float
    e_theta: float
    D_N: float
    q_pa: float
    mach: float
    V_mps: float
    cos_psi: float
    sin_g: float
    g_eff_mps2: float
    cos_g: float
    g_mps2: float
    w_mps: float
    u_mps: float
    p_pa: float
    rho_kgm3: float
    a_mps: float


def planar_forces(t: float, y: np.ndarray, p: PlanarParams) -> PlanarForces:
    """The force-level terms of the planar RHS at one instant.

    Inputs: t, absolute run time [s]; y in the PLANAR_LAYOUT order; p, the phase
    parameters. Output: ``PlanarForces`` (thrust, mass flow, thrust direction, drag,
    dynamic pressure, Mach, |v_rel|, cos psi, gamma_rel's sine and cosine, g and g_eff,
    the components of v_rel and the ambient state): exactly the values ``rhs_planar``
    uses. Frame: local (radial up, horizontal downrange); every aerodynamic term uses
    the velocity relative to the co-rotating air.
    """
    r = float(y[_PR])
    omega_p = p.omega_p_rads
    kin = _kinematics(r, float(y[_PVR]), float(y[_PVT]), omega_p)
    speed = kin.V_mps
    p_amb, rho, a = p.atmosphere(r - p.r_datum_m)
    t_vac, thrust, mdot = thrust_terms(p.schedule, t, p_amb)
    steering = p.steering
    if steering is None:
        e_r, e_th, cos_psi = kin.sin_g, kin.cos_g, 1.0
    else:
        e_r, e_th = steering.direction(t, y, kin)
        cos_psi = 1.0 if steering.along_vrel else e_r * kin.sin_g + e_th * kin.cos_g
    q = 0.5 * rho * speed * speed
    mach = speed / a
    drag = 0.0 if p.drag is None else p.drag.force_N(q, mach)
    g = p.gravity(r)
    return PlanarForces(
        t_vac,
        thrust,
        mdot,
        e_r,
        e_th,
        drag,
        q,
        mach,
        speed,
        cos_psi,
        kin.sin_g,
        g - omega_p * omega_p * r,
        kin.cos_g,
        g,
        kin.w_mps,
        kin.u_mps,
        p_amb,
        rho,
        a,
    )


def rhs_planar(t: float, y: np.ndarray, p: PlanarParams) -> np.ndarray:
    """Time derivative of the planar state (docs/physics.md, "Planar ascent state and
    equations of motion" and "2-D loss identity").

    Inputs: t, absolute run time [s]; y in the PLANAR_LAYOUT order (r [m], theta [rad],
    v_r, v_theta [m/s], m [kg], J_vac, J_grav, J_alt, J_drag, J_steer, J_bp [m/s]); p,
    the phase parameters. Output: dy/dt in the same order. Frame: planar Earth-centred
    inertial, polar (r, theta) with theta increasing downrange. Thrust T acts along the
    steering law's unit e = (e_r, e_theta), drag D along -v_hat_rel with v_rel = (w, u)
    = (v_r, v_theta - omega_p r). With sin_g = w/V and cos_g = u/V (1 and 0 when
    V < V_REL_EPS_MPS), g = gravity(r), g_eff = g - omega_p^2 r and
    cos psi = e_r sin_g + e_theta cos_g:

        dr/dt        = v_r
        dtheta/dt    = v_theta / r
        dv_r/dt      = v_theta^2 / r - g + (T e_r - D sin_g) / m
        dv_theta/dt  = -v_r v_theta / r + (T e_theta - D cos_g) / m
        dm/dt        = -T_vac / c                    (mass flow follows T_vac)
        dJ_vac/dt    = T_vac / m
        dJ_grav/dt   = g_eff sin_g
        dJ_alt/dt    = (g_eff - g_ref) sin_g
        dJ_drag/dt   = D / m
        dJ_steer/dt  = (T / m)(1 - cos psi)          exactly 0 along v_rel
        dJ_bp/dt     = (T_vac - T) / m

    so that dV/dt = dJ_vac - dJ_grav - dJ_drag - dJ_steer - dJ_bp at every instant with
    V >= V_REL_EPS_MPS. Below it the sum is T e_r/m - g_eff - D/m (v_hat_rel = r_hat),
    which is the one-sided limit of dV/dt from rest only when the relative acceleration
    at rest is radial and upward (the pad with radial thrust and T e_r/m > g_eff + D/m,
    which the liftoff root guarantees in runs). Otherwise, e.g. a start from rest that
    sinks or a non-radial law at V = 0, it is a measure-zero convention whose closure
    error is one RHS stage (docs/physics.md, "2-D loss identity").
    """
    f = planar_forces(t, y, p)
    r = float(y[_PR])
    v_r = float(y[_PVR])
    v_theta = float(y[_PVT])
    m = float(y[_PM])
    thrust = f.T_N
    drag = f.D_N
    dy = np.empty(_N_PLANAR)
    dy[_PR] = v_r
    dy[_PTH] = v_theta / r
    dy[_PVR] = v_theta * v_theta / r - f.g_mps2 + (thrust * f.e_r - drag * f.sin_g) / m
    dy[_PVT] = -v_r * v_theta / r + (thrust * f.e_theta - drag * f.cos_g) / m
    dy[_PM] = -f.mdot_kgps
    dy[_PJ_VAC] = f.T_vac_N / m
    dy[_PJ_GRAV] = f.g_eff_mps2 * f.sin_g
    dy[_PJ_ALT] = (f.g_eff_mps2 - p.g_ref_mps2) * f.sin_g
    dy[_PJ_DRAG] = drag / m
    dy[_PJ_STEER] = thrust / m * (1.0 - f.cos_psi)
    dy[_PJ_BP] = (f.T_vac_N - thrust) / m
    return dy


def planar_observables(t: float, y: np.ndarray, p: PlanarParams, t_fs: float) -> dict[str, float]:
    """Reported quantities of a planar flight state at one instant (SI, radians).

    Inputs: t, absolute run time [s]; y (PLANAR_LAYOUT); p, the phase parameters; t_fs,
    the flight-start time [s] at which theta = 0 is the site meridian (release, or the
    liftoff root when later). Output keys: alt_m (r - r_datum, geometric), downrange_m
    (Earth-fixed arc along the datum sphere, r_datum (theta - omega_p (t - t_fs))),
    speed_rel_mps (|v_rel|), speed_inertial_mps (hypot(v_r, v_theta)), gamma_rel_rad
    (atan2(w, u) in (-pi, pi]; pi/2 below V_REL_EPS_MPS; not unwrapped), pitch_rad
    (atan2(e_r, e_theta), the thrust direction above local horizontal), psi_rad (the
    angle between thrust and v_rel, from cos psi clipped to [-1, 1]), q_pa, mach,
    thrust_N, thrust_vac_N, drag_N and g_eff_mps2 (as in ``planar_forces``; orbital
    elements are ``orbit.orbit_elements``). Frame: local (radial, horizontal);
    gamma_rel and psi use the Earth-relative velocity.
    """
    f = planar_forces(t, y, p)
    r = float(y[_PR])
    theta = float(y[_PTH])
    if f.V_mps < V_REL_EPS_MPS:
        gamma_rel = 0.5 * math.pi
    else:
        gamma_rel = math.atan2(f.w_mps, f.u_mps)
    return {
        "alt_m": r - p.r_datum_m,
        "downrange_m": p.r_datum_m * (theta - p.omega_p_rads * (t - t_fs)),
        "speed_rel_mps": f.V_mps,
        "speed_inertial_mps": math.hypot(float(y[_PVR]), float(y[_PVT])),
        "gamma_rel_rad": gamma_rel,
        "pitch_rad": math.atan2(f.e_r, f.e_theta),
        "psi_rad": math.acos(min(1.0, max(-1.0, f.cos_psi))),
        "q_pa": f.q_pa,
        "mach": f.mach,
        "thrust_N": f.T_N,
        "thrust_vac_N": f.T_vac_N,
        "drag_N": f.D_N,
        "g_eff_mps2": f.g_eff_mps2,
    }


@dataclass(frozen=True)
class PlanarDynamics2D:
    """The planar ascent model (DynamicsModel implementation).

    State: PLANAR_STATE_NAMES in the planar ECI frame (polar r, theta); parameters:
    PlanarParams; rhs: ``rhs_planar``. omega_p_rads [rad/s] and r_datum_m [m] are the
    model's rotation rate and altitude datum, which altitude and speed need:
    altitude(y) = r - r_datum [m] and speed(y) = |v_rel| = hypot(v_r, v_theta -
    omega_p r) [m/s] (the Earth-relative speed of the loss identity), for a state
    vector or a (n, n_samples) series. Both are required (no default, so a model
    without rotation is a deliberate omega_p_rads=0.0) and must equal the phase
    parameters' values: build the model with ``for_params`` and check a phase once with
    ``check_params`` (the RHS reads the params and does not compare them per call).
    """

    state_names: ClassVar[tuple[str, ...]] = PLANAR_STATE_NAMES
    layout: ClassVar[StateLayout] = PLANAR_LAYOUT
    omega_p_rads: float
    r_datum_m: float

    @classmethod
    def for_params(cls, params: PlanarParams) -> PlanarDynamics2D:
        """The model whose rotation rate [rad/s] and altitude datum [m] are those of
        the phase parameters ``params``."""
        return cls(omega_p_rads=params.omega_p_rads, r_datum_m=params.r_datum_m)

    def check_params(self, params: PlanarParams) -> None:
        """Raise ValueError unless params.omega_p_rads [rad/s] and params.r_datum_m [m]
        equal the model's (once per phase; speed() and altitude() use the model's)."""
        if params.omega_p_rads != self.omega_p_rads or params.r_datum_m != self.r_datum_m:
            raise ValueError(
                "PlanarDynamics2D and PlanarParams disagree on omega_p_rads or r_datum_m"
            )

    @property
    def i_mass(self) -> int:
        """Index of the vehicle mass [kg] in the state vector."""
        return _PM

    def rhs(self, t: float, y: np.ndarray, params: PlanarParams) -> np.ndarray:
        """dy/dt at time t [s]; see ``rhs_planar``. params.omega_p_rads and r_datum_m
        must equal the model's (the RHS reads the params; see ``check_params``)."""
        return rhs_planar(t, y, params)

    def altitude(self, y: np.ndarray) -> Any:
        """Altitude r - r_datum [m] of a state vector or a (n, n_samples) series."""
        return y[_PR] - self.r_datum_m

    def speed(self, y: np.ndarray) -> Any:
        """Earth-relative speed |v_rel| [m/s] of a state vector or a series."""
        return np.hypot(y[_PVR], y[_PVT] - self.omega_p_rads * y[_PR])
