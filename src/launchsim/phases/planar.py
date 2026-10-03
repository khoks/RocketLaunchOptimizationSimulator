"""The planar planner (``PlanarPlanner``): the flight of the ``planar_2d`` model
(docs/physics.md, "Planar release map", "Stage-1 guidance and events (planar)", "gamma*
inner solve", "Stage 2 and insertion (planar)" and "LTG shooting").

A planar run is the shared prelude (``phases.prelude``: the hold-down, or the track push
up to the track exit) run in ``PLANAR_LAYOUT``, the release map into the planar ECI
frame (``map_release_planar``), then the stage-1 phases: an optional pre-ignition coast,
VERTICAL_RISE (radial thrust) until the kick trigger, KICK (fixed tilt delta) until the
velocity is aligned with the thrust, GRAVITY_TURN (thrust along v_rel) to MECO, the
staging map and the staging coast (COAST_STAGING, 11 s on the Phase 2 forks, split at
the radial apex) up to stage-2 ignition, which is where ``stage1`` hands over
(``Handover``). ``stage2`` flies LTG_BURN (linear-tangent steering) from the hand-over
to the energy cutoff E = E* of the target orbit, with the fairing dropped at the
heating-criterion event (the FAIRING map) and, in a search, virtual propellant under a
mass floor; ``solve_stage2`` solves the steering pair (a, b) by shooting
(``guidance.solve_ltg``). A failed ignition coasts unpowered to the apex and falls to
the ground. A first stage stated by ``height_method: event`` (a pending ignition) lights
where its pre-ignition coast crosses the requested altitude upward (the
``ignition_height`` event), or fails with GuidanceFailure("no_ignition") at an apex
below it.

``PlanarView`` is the planar ``StateView`` (alt_m, downrange_m, speed_rel_mps,
speed_inertial_mps, gamma_rel_rad, m_kg); ``PlanarEnvironment`` holds what every
planar phase shares (gravity, rotation, atmosphere, datum). Event states come from
``engine.event_state``, so the planner runs with dense output on (recorded runs) or off
(search evaluations).

Pure: no I/O, no globals, no printing. SI units and radians; times are absolute run
times [s] (t = 0 at push start on a track or at hold-down release on a pad). Frame:
planar Earth-centred inertial, theta = 0 at the site meridian at the flight start t_fs.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from launchsim.constants import R_EARTH_M, V_REL_EPS_MPS
from launchsim.dynamics import (
    PLANAR_LAYOUT,
    PLANAR_STATE_NAMES,
    AtmosphereFn,
    Gravity,
    InverseSquareGravity,
    PlanarDynamics2D,
    PlanarParams,
    StateLayout,
    SteeringLaw,
    TrackParams,
    planar_kinematics,
    rhs_planar,
)
from launchsim.guidance import (
    AlongVrel,
    FixedTilt,
    GuidanceFailure,
    GuidanceSpec,
    LinearTangent,
    LtgSettings,
    LtgSolution,
    Radial,
    ltg_guess_ladder,
    solve_ltg,
)
from launchsim.orbit import TargetOrbit, orbit_elements, specific_energy_Jkg
from launchsim.phases.engine import (
    ATOL_KG,
    ATOL_M,
    ATOL_MPS,
    EVENT_ZERO_TOL,
    ZERO_SPAN_S,
    EventSpec,
    IntegratorSettings,
    PhaseResult,
    PhaseSpec,
    _pass_through,
    atol_for,
    ev_altitude_up,
    ev_ground,
    ev_kick_aligned,
    ev_kick_start,
    ev_propellant,
    ev_radial_apex,
    ev_radial_turnaround,
    ev_time,
    event_state,
    integrate_phase,
)
from launchsim.phases.prelude import (
    IGNITION_HEIGHT_EVENT,
    VERTICAL_TRACK_TOL_RAD,
    HoldParams,
    IgnitionSpec,
    PreludeLayout,
    TrackExit,
    flag_ignored_ignition_settings,
    fly_track,
    hold_closed_form,
    hold_until_liftoff,
    max_step_cap,
)
from launchsim.phases.trace import (
    ASSIST_KIND,
    HOLD_KIND,
    MASS_COLUMN,
    RELEASE_LABEL,
    HoldSummary,
    RunTrace,
    TraceBuilder,
)
from launchsim.vehicle import ThrustSchedule, Vehicle

if TYPE_CHECKING:
    from launchsim.assist.base import AssistModel, TrackGeometry

PLANAR_MODEL = "planar_2d"
"""Name of the planar dynamics model (``config`` ``dynamics: planar_2d``)."""
COAST_PRE_IGN = "COAST_PRE_IGN"
"""Unpowered flight from the flight start (or the staging coast's end) to a stage's
ignition; split at the radial apex."""
VERTICAL_RISE = "VERTICAL_RISE"
"""Stage-1 burn with radial thrust (``guidance.Radial``) until the kick trigger."""
KICK = "KICK"
"""Stage-1 burn with the thrust tilted by delta from local vertical
(``guidance.FixedTilt``) until the velocity is aligned with it."""
GRAVITY_TURN = "GRAVITY_TURN"
"""Stage-1 burn with the thrust along v_rel (``guidance.AlongVrel``) to MECO."""
COAST_STAGING = "COAST_STAGING"
"""Unpowered flight from MECO over the next stage's coast_before_ignition_s."""
LTG_BURN = "LTG_BURN"
"""Stage-2 burn under linear-tangent steering (``guidance.LinearTangent``) to the energy
cutoff; split at the fairing event (the FAIRING map) and at the thrust kinks."""
FAIRING_EVENT = "fairing"
"""Name of the fairing jettison event (the heating criterion inside LTG_BURN, or already
met at staging or at stage-2 ignition)."""
CUTOFF_EVENT = "cutoff"
"""Name of the stage-2 energy cutoff event, E - E* crossing zero upward (insertion)."""
INSERTED_STATUS = "inserted"
"""Run status of a recorded run whose stage 2 reached the energy cutoff inside the LTG
acceptance (|r_c - r_t| < accept_r_m and |v_r,c| < accept_vr_mps)."""
OFF_TARGET_STATUS = "off_target"
"""Run status of a recorded run whose stage 2 reached the energy cutoff outside the LTG
acceptance: the flown (a, b) is not a converged root at the run's settings (the run is
flagged with the misses, the eccentricity and the perigee)."""
SHORT_OF_ORBIT_STATUS = "short_of_orbit"
"""Run status of a recorded run whose stage 2 burned out (real depletion) before the
energy cutoff."""
COAST = "COAST"
"""Terminal unpowered flight after a failed ignition or a stage-2 burnout short of
orbit: to the apex, then to the ground."""
PLANAR_ASCENT_KINDS = (
    COAST_PRE_IGN,
    VERTICAL_RISE,
    KICK,
    GRAVITY_TURN,
    COAST_STAGING,
    LTG_BURN,
    COAST,
)
"""Phase kinds of the planar free flight after release (``PlanarView.ascent_kinds``):
the loss budget sums over these."""
LIT_KINDS = (VERTICAL_RISE, KICK, GRAVITY_TURN, LTG_BURN)
"""Planar phase kinds with an engine lit."""
PLANAR_END_KINDS = ("stage1_burnout", "insertion", "apex", "impact")
"""Where a planar run stops (``config.PLANAR_ENDS``)."""
EARTH_FIXED_LABELS = (HOLD_KIND, ASSIST_KIND, RELEASE_LABEL)
"""Event/row labels of a vehicle not yet in free flight: the planar view reports an
Earth-fixed downrange of 0 for them (the Phase 2 datum)."""
PLANAR_COLUMNS = (
    "alt_m",
    "downrange_m",
    "speed_rel_mps",
    "speed_inertial_mps",
    "gamma_rel_rad",
    MASS_COLUMN,
)
"""The event-record columns of the planar StateView."""

_R = PLANAR_LAYOUT.index("r_m")
_TH = PLANAR_LAYOUT.index("theta_rad")
_VR = PLANAR_LAYOUT.index("v_r_mps")
_VT = PLANAR_LAYOUT.index("v_theta_mps")
_M = PLANAR_LAYOUT.index("m_kg")
_J_NAMES = tuple(n for n in PLANAR_STATE_NAMES if n.startswith("J_"))


# ------------------------------------------------------------------------ state view


@dataclass(frozen=True)
class PlanarView:
    """The planar StateView: what an event record shows of a ``PLANAR_LAYOUT`` state.

    omega_p_rads [rad/s] and r_datum_m [m] are the run's rotation rate and altitude
    datum; t_fs_s [s] is the flight-start time at which theta = 0 is the site meridian
    (NaN until the flight starts; the planner rebinds the view then). Columns: alt_m =
    r - r_datum [m] (geometric); downrange_m = r_datum (theta - omega_p (t - t_fs)) [m],
    the Earth-fixed arc along the datum sphere, and 0 for rows before the flight
    (HOLD, ASSIST, RELEASE labels: the vehicle is Earth-fixed or on the track);
    speed_rel_mps = |v_rel| [m/s]; speed_inertial_mps = hypot(v_r, v_theta) [m/s];
    gamma_rel_rad = atan2(w, u) [rad] in (-pi, pi], pi/2 below V_REL_EPS_MPS (not
    unwrapped); m_kg [kg]. Frame: planar ECI; gamma and |v_rel| are Earth-relative.
    """

    omega_p_rads: float
    r_datum_m: float = R_EARTH_M
    t_fs_s: float = math.nan

    @property
    def model(self) -> str:
        """PLANAR_MODEL."""
        return PLANAR_MODEL

    @property
    def layout(self) -> StateLayout:
        """``dynamics.PLANAR_LAYOUT``."""
        return PLANAR_LAYOUT

    @property
    def columns(self) -> tuple[str, ...]:
        """PLANAR_COLUMNS."""
        return PLANAR_COLUMNS

    @property
    def ascent_kinds(self) -> tuple[str, ...]:
        """PLANAR_ASCENT_KINDS."""
        return PLANAR_ASCENT_KINDS

    def row(self, t: float, y: np.ndarray, phase: str) -> dict[str, float]:
        """The column values for the planar state y at time t [s] in a phase (or event
        label) ``phase``. A flight row before the view knows t_fs raises ValueError."""
        kin = planar_kinematics(y, self.omega_p_rads)
        if phase in EARTH_FIXED_LABELS:
            downrange = 0.0
        else:
            if math.isnan(self.t_fs_s):
                raise ValueError(
                    f"PlanarView: a {phase} row at t = {t:.6g} s needs the flight-start "
                    "time (rebind the view when the flight starts)"
                )
            theta = float(y[_TH])
            downrange = self.r_datum_m * (theta - self.omega_p_rads * (t - self.t_fs_s))
        return {
            "alt_m": float(y[_R]) - self.r_datum_m,
            "downrange_m": downrange,
            "speed_rel_mps": kin.V_mps,
            "speed_inertial_mps": math.hypot(float(y[_VR]), float(y[_VT])),
            "gamma_rel_rad": gamma_rel_rad(y, self.omega_p_rads),
            MASS_COLUMN: float(y[_M]),
        }


def gamma_rel_rad(y: np.ndarray, omega_p_rads: float) -> float:
    """Earth-relative flight-path angle gamma_rel = atan2(w, u) [rad] of a planar state
    (pi/2 below V_REL_EPS_MPS, the local-vertical fallback)."""
    kin = planar_kinematics(y, omega_p_rads)
    if kin.V_mps < V_REL_EPS_MPS:
        return 0.5 * math.pi
    return math.atan2(kin.w_mps, kin.u_mps)


# ------------------------------------------------------------------ environment


@dataclass(frozen=True)
class PlanarEnvironment:
    """What every planar phase of a run shares: gravity (g(r) [m/s^2], mu/r^2 in runs),
    omega_p_rads (the planar rotation rate [rad/s], 0 with rotation off), atmosphere
    (altitude [m] -> (p [Pa], rho [kg/m^3], a [m/s]); ``ambient_scalar`` in runs) and
    r_datum_m (the radius [m] of the altitude datum, R_E in runs).

    g_ref_mps2 = g(r_datum) - omega_p^2 r_datum is the effective gravity at the datum:
    the pad's hold-down and liftoff balance, the track's constant g_eff
    (``dynamics.g_eff_track(omega_p)`` for mu/r^2 at R_E) and the reference of the
    gravity-loss split. ``params`` builds the PlanarParams of one phase.
    """

    gravity: Gravity
    omega_p_rads: float
    atmosphere: AtmosphereFn
    r_datum_m: float = R_EARTH_M

    def __post_init__(self) -> None:
        if not math.isfinite(self.omega_p_rads):
            raise ValueError("omega_p_rads must be finite")
        if not (math.isfinite(self.r_datum_m) and self.r_datum_m > 0.0):
            raise ValueError("r_datum_m must be finite and > 0")
        if not self.g_ref_mps2 >= 0.0:
            raise ValueError(
                f"g_ref = g(r_datum) - omega_p^2 r_datum must be >= 0, got {self.g_ref_mps2}"
            )

    @property
    def g_ref_mps2(self) -> float:
        """Effective gravity at the datum [m/s^2]: g(r_datum) - omega_p^2 r_datum."""
        r = self.r_datum_m
        return self.gravity(r) - self.omega_p_rads * self.omega_p_rads * r

    def ambient_pa(self, alt_m: float) -> float:
        """Ambient pressure [Pa] at altitude alt_m [m] above the datum."""
        return self.atmosphere(alt_m)[0]

    @property
    def mu_m3s2(self) -> float:
        """Gravitational parameter mu [m^3/s^2] of an inverse-square gravity (the run
        model), which the orbital energy of the insertion cutoff needs; ValueError for
        any other gravity model (no Kepler energy)."""
        if not isinstance(self.gravity, InverseSquareGravity):
            raise ValueError(
                "the insertion cutoff needs InverseSquareGravity, got "
                f"{type(self.gravity).__name__}"
            )
        return self.gravity.mu_m3s2

    def params(
        self,
        schedule: ThrustSchedule | None,
        steering: SteeringLaw | None,
        vehicle: Vehicle,
    ) -> PlanarParams:
        """PlanarParams of one phase: this environment, the lit stage's schedule (None
        for an unpowered phase), its steering law, and the vehicle's drag model
        (``vehicle.aero``; None means no drag)."""
        return PlanarParams(
            gravity=self.gravity,
            omega_p_rads=self.omega_p_rads,
            g_ref_mps2=self.g_ref_mps2,
            schedule=schedule,
            drag=vehicle.aero,
            atmosphere=self.atmosphere,
            steering=steering,
            r_datum_m=self.r_datum_m,
        )


# ------------------------------------------------------------------- release maps


def planar_rest_state(
    z_m: float, m_kg: float, omega_p_rads: float, r_datum_m: float = R_EARTH_M
) -> np.ndarray:
    """A PLANAR_LAYOUT state at rest relative to the ground at altitude z_m [m] above
    the datum on the site meridian: r = r_datum + z, theta = 0, v_r = 0, v_theta =
    omega_p r (the ground's own velocity), mass m_kg [kg], quadratures 0. The pad
    (z = 0): |v_in| = omega_p R_E (465.1 m/s on the equator, 408.74 m/s at 28.5 deg
    east) and V = |v_rel| = 0 exactly."""
    r = r_datum_m + z_m
    return PLANAR_LAYOUT.build(r_m=r, v_theta_mps=omega_p_rads * r, m_kg=m_kg)


def release_state_planar(
    z_exit_m: float,
    x_exit_m: float,
    sdot_mps: float,
    phi_rad: float,
    m_kg: float,
    omega_p_rads: float,
    r_datum_m: float = R_EARTH_M,
) -> np.ndarray:
    """The exact general release map from the flat track frame into the planar ECI frame.

    Inputs: the exit's altitude z_exit_m [m] above the datum and downrange offset
    x_exit_m [m] from the site (the track frame: x downrange, z up, origin on the datum
    at the site); the speed along the track sdot_mps [m/s]; the track angle phi_rad
    [rad] above the site's horizontal at the exit; the vehicle mass m_kg [kg]; the
    planar rotation rate [rad/s]; the datum radius [m]. The exit lies at the angle
    theta_x = atan2(x_e, r_datum + z_e) downrange, where the local vertical is tilted
    downrange by theta_x, so the flat-frame velocity sdot (cos phi, sin phi) projects
    onto r_hat = (sin theta_x, cos theta_x) and theta_hat = (cos theta_x,
    -sin theta_x):

        r = hypot(r_datum + z_e, x_e),  theta = theta_x,
        v_r = sdot sin(phi + theta_x),  v_theta = sdot cos(phi + theta_x) + omega_p r

    (the ground's velocity omega_p r added to the Earth-relative downrange component),
    quadratures 0. Output: the PLANAR_LAYOUT state. Phase 2 releases only from vertical
    tracks (``map_release_planar``); this general form is the Phase 3 seam.
    """
    rz = r_datum_m + z_exit_m
    theta_x = math.atan2(x_exit_m, rz)
    r = math.hypot(rz, x_exit_m)
    ang = phi_rad + theta_x
    return PLANAR_LAYOUT.build(
        r_m=r,
        theta_rad=theta_x,
        v_r_mps=sdot_mps * math.sin(ang),
        v_theta_mps=sdot_mps * math.cos(ang) + omega_p_rads * r,
        m_kg=m_kg,
    )


def map_release_planar(
    exit_: TrackExit, omega_p_rads: float, r_datum_m: float = R_EARTH_M
) -> np.ndarray:
    """Map the vehicle at the track exit into the planar ascent frame (Phase 2: vertical
    tracks only).

    Inputs: the TrackExit (``prelude.fly_track``); the planar rotation rate [rad/s]; the
    datum radius [m]. The Phase 2 assertion: the exit must be vertical
    (|phi - pi/2| <= VERTICAL_TRACK_TOL_RAD) with a known downrange offset of 0
    (``TrackExit.x_exit_m``; None, a geometry without x(s), raises), else ValueError.
    Output: ``release_state_planar`` at x_e = 0, phi = pi/2 written exactly: r =
    r_datum + z_e, theta = 0, v_r = sdot, v_theta = omega_p r, mass the vehicle's,
    quadratures 0 (the accounting starts at release).
    """
    if exit_.x_exit_m is None:
        raise ValueError(
            "map_release_planar: the track geometry has no x(s), so the exit's downrange "
            "offset is unknown (Phase 3 adds it)"
        )
    if exit_.x_exit_m != 0.0 or abs(exit_.phi_rad - 0.5 * math.pi) > VERTICAL_TRACK_TOL_RAD:
        raise ValueError(
            f"map_release_planar: Phase 2 releases from vertical tracks only (x_exit = "
            f"{exit_.x_exit_m:.6g} m, phi = {exit_.phi_rad:.6g} rad); the general map "
            "release_state_planar is the Phase 3 seam"
        )
    r = r_datum_m + exit_.z_exit_m
    return PLANAR_LAYOUT.build(
        r_m=r, v_r_mps=exit_.sdot_mps, v_theta_mps=omega_p_rads * r, m_kg=exit_.m_kg
    )


def planar_prelude(omega_p_rads: float, r_datum_m: float = R_EARTH_M) -> PreludeLayout:
    """The prelude layout of the planar model: holds in PLANAR_LAYOUT at rest relative
    to the ground (``planar_rest_state``), and the planar view of a track state for
    event logging: a vertical track (Phase 2) at arc length s with speed sdot is
    r = r_datum + z_start + z(s), theta = 0, v_r = sdot, v_theta = omega_p r."""

    def hold_state(z_m: float, m_kg: float) -> np.ndarray:
        return planar_rest_state(z_m, m_kg, omega_p_rads, r_datum_m)

    def from_track(y_track: np.ndarray, params: TrackParams) -> np.ndarray:
        lay = params.layout
        s = float(lay.get(y_track, "s_m"))
        r = r_datum_m + params.track.start_altitude_m + params.track.z(s)
        return PLANAR_LAYOUT.build(
            r_m=r,
            v_r_mps=float(lay.get(y_track, "sdot_mps")),
            v_theta_mps=omega_p_rads * r,
            m_kg=float(lay.get(y_track, "m_kg")),
        )

    return PreludeLayout(PLANAR_LAYOUT, hold_state, from_track)


def map_staging_planar(
    y: np.ndarray, vehicle: Vehicle, stage_index: int, drop_fairing: bool
) -> np.ndarray:
    """Drop stage ``stage_index`` after its burnout (instantaneous, impulse-free): the
    state with the stage's dry mass [kg] removed, plus the fairing mass when
    drop_fairing (the planner decides: rule ``staging``, or the heating criterion
    already met at staging). r, theta, v_r, v_theta and every quadrature are
    unchanged. Output: a new PLANAR_LAYOUT state."""
    dropped = vehicle.stages[stage_index].dry_mass_kg
    if drop_fairing:
        dropped += vehicle.fairing_mass_kg
    out = np.array(y, dtype=float, copy=True)
    out[_M] -= dropped
    return out


def fmh_rate_W_m2(y: np.ndarray, env: PlanarEnvironment) -> float:
    """Free-molecular heating rate 0.5 rho V^3 [W/m^2] of a planar state, with rho at
    h = r - r_datum and V = |v_rel| (the fairing rule's criterion)."""
    kin = planar_kinematics(y, env.omega_p_rads)
    rho = env.atmosphere(float(y[_R]) - env.r_datum_m)[1]
    return 0.5 * rho * kin.V_mps**3


def map_fairing_planar(y: np.ndarray, fairing_mass_kg: float) -> np.ndarray:
    """The FAIRING map (instantaneous, impulse-free jettison): the state with the fairing
    mass [kg] removed; r, theta, v_r, v_theta and every quadrature unchanged. Output: a
    new PLANAR_LAYOUT state."""
    out = np.array(y, dtype=float, copy=True)
    out[_M] -= fairing_mass_kg
    return out


def orbital_energy_Jkg(y: np.ndarray, mu_m3s2: float) -> float:
    """Specific orbital energy E = (v_r^2 + v_theta^2)/2 - mu/r [J/kg] of a planar state
    (inertial velocity; ``orbit.specific_energy_Jkg``)."""
    return specific_energy_Jkg(float(y[_R]), float(y[_VR]), float(y[_VT]), mu_m3s2)


# ------------------------------------------------------------- stage-2 event factories


def ev_energy_cutoff(target: TargetOrbit, mu_m3s2: float) -> EventSpec:
    """Insertion cutoff: g = E - E* crosses zero upward (terminal; called ``cutoff``).

    Inputs: the circular target (radius r_t [m]) and mu [m^3/s^2]; E = (v_r^2 +
    v_theta^2)/2 - mu/r [J/kg] of the PLANAR_LAYOUT state (inertial velocity) and
    E* = -mu/(2 r_t). While stage 2 thrusts with a pitch inside the direct-root window
    the thrust does positive work on the inertial velocity, so E rises monotonically and
    the crossing is unique (docs/physics.md, "Stage 2 and insertion (planar)"): at it
    the semi-major axis equals r_t, and the LTG shooting drives r_c to r_t and v_r,c to
    0. zero_tol = ATOL_MPS sqrt(mu/r_t) [J/kg], the energy of one velocity tolerance at
    the circular speed.
    """
    e_star = target.energy_Jkg(mu_m3s2)

    def fn(t: float, y: np.ndarray) -> float:
        return orbital_energy_Jkg(y, mu_m3s2) - e_star

    tol = ATOL_MPS * target.v_circ_mps(mu_m3s2)
    return EventSpec(CUTOFF_EVENT, fn, terminal=True, direction=+1, zero_tol=tol)


def ev_fmh(limit_W_m2: float, env: PlanarEnvironment) -> EventSpec:
    """Fairing jettison: g = ln(0.5 rho V^3 / q_fmh) crosses zero downward (terminal;
    called ``fairing``), with rho at h = r - r_datum and V = |v_rel| (``fmh_rate_W_m2``)
    and q_fmh = limit_W_m2 [W/m^2] (> 0). The logarithm keeps the function of order 1
    while the rate falls through six decades; a zero rate (no air) gives -inf, which the
    engine's already-past rule ends at t0. Listed in LTG_BURN while the fairing is on;
    the rate falls monotonically there (rho drops by e over one scale height of climb
    faster than V^3 grows). g is dimensionless; zero_tol = EVENT_ZERO_TOL.
    """
    if not (math.isfinite(limit_W_m2) and limit_W_m2 > 0.0):
        raise ValueError(f"limit_W_m2 must be finite and > 0, got {limit_W_m2!r}")

    def fn(t: float, y: np.ndarray) -> float:
        rate = fmh_rate_W_m2(y, env)
        return math.log(rate / limit_W_m2) if rate > 0.0 else -math.inf

    return EventSpec(FAIRING_EVENT, fn, terminal=True, direction=-1, zero_tol=EVENT_ZERO_TOL)


def ev_mass_floor(m_floor_kg: float) -> EventSpec:
    """Search mass floor: m - m_floor crosses zero downward (terminal; ``mass_floor``).

    Input: the floor [kg], mass_floor_factor (m_d2 + P) (plan section 6): in a search
    stage 2 burns virtual propellant past its real load (no depletion event), and the
    floor stops a shot that would otherwise burn on toward zero mass, as GuidanceFailure
    ``mass_floor``. zero_tol = ATOL_KG.
    """
    if not m_floor_kg > 0.0:
        raise ValueError(f"m_floor_kg must be > 0, got {m_floor_kg!r}")

    def fn(t: float, y: np.ndarray) -> float:
        return float(y[_M]) - m_floor_kg

    return EventSpec("mass_floor", fn, terminal=True, direction=-1, zero_tol=ATOL_KG)


# --------------------------------------------------------------- planner records


@dataclass(frozen=True, eq=False)
class FlightStart:
    """Where the free flight begins, after the prelude.

    prefix: the trace so far (HOLD and ASSIST phases, the release and liftoff events;
    view bound to t_fs once the flight starts); status: "nominal", or the prelude's
    "no_liftoff" / "drive_limit" (no flight follows); t_fs_s [s] and y_fs (planar
    state, theta = 0): the flight start (release, or the liftoff root of an extended
    hold), None without a flight; t_ign1_s [s]: stage 1's absolute ignition time, None
    when its ignition fails or when it lights at an altitude; ign1_alt_m [m]: the
    altitude above the datum at which stage 1 lights (the track exit plus the height of
    ``height_method: event``, a pending ignition the planner resolves in flight), None
    otherwise. ``stage1_lights`` tells the two None cases apart: a stage that lights at
    a height never counts as a failed ignition.
    """

    prefix: RunTrace
    status: str
    t_fs_s: float | None
    y_fs: np.ndarray | None
    t_ign1_s: float | None
    ign1_alt_m: float | None = None

    def __post_init__(self) -> None:
        if self.t_ign1_s is not None and self.ign1_alt_m is not None:
            raise ValueError("stage 1 lights at a time or at an altitude, not both")

    @property
    def stage1_lights(self) -> bool:
        """Whether stage 1 lights: at its ignition time, or at its ignition altitude (a
        pending ignition); False only for a failed ignition (or no flight)."""
        return self.t_ign1_s is not None or self.ign1_alt_m is not None


@dataclass(frozen=True, eq=False)
class KickPoint:
    """Stage 1 at the kick trigger (or at burnout for vertical-only guidance).

    start: the FlightStart; prefix: the trace through the end of the rise; t_s [s] and
    y (planar state): where the rise ended; schedule: stage 1's ThrustSchedule;
    kicked: True when the rise ended at ``kick_start`` (False: the vertical-only rise
    reached burnout, and t_s, y are MECO). Independent of delta, so a gamma* search
    flies it once per vehicle and payload.
    """

    start: FlightStart
    prefix: RunTrace
    t_s: float
    y: np.ndarray
    schedule: ThrustSchedule
    kicked: bool


@dataclass(frozen=True, eq=False)
class Handover:
    """Stage 1 flown: MECO, and (through_staging) the state at stage-2 ignition.

    delta_rad: the kick angle [rad] (None for vertical-only guidance); meco: the MECO
    record (t_s, alt_m, downrange_m, speed_rel_mps, speed_inertial_mps,
    gamma_rel_rad, m_kg, every J_*_mps, t_kick_s, kick_duration_s,
    kick_steering_loss_mps; SI, Earth-relative angles and speeds); t_ign2_s [s] and
    y_ign2 (planar state): stage-2 ignition after the staging map and coast, None when
    the flight stopped at MECO; fairing_on: whether the fairing is still carried into
    stage 2; prefix: the trace through the end of the flight segment.
    """

    delta_rad: float | None
    meco: Mapping[str, float]
    t_ign2_s: float | None
    y_ign2: np.ndarray | None
    fairing_on: bool
    prefix: RunTrace

    @property
    def gamma_meco_rad(self) -> float:
        """Earth-relative flight-path angle at MECO [rad] (the gamma* knob)."""
        return self.meco["gamma_rel_rad"]

    @property
    def gamma_in_ign2_rad(self) -> float:
        """Inertial flight-path angle atan2(v_r, v_theta) [rad] at stage-2 ignition (the
        LTG physics guess starts from it); ValueError without a stage-2 ignition."""
        if self.y_ign2 is None:
            raise ValueError("the hand-over stopped at MECO: no stage-2 ignition state")
        return math.atan2(float(self.y_ign2[_VR]), float(self.y_ign2[_VT]))


@dataclass(frozen=True, eq=False)
class Stage2Result:
    """One stage-2 burn (LTG_BURN) from the hand-over, as ``PlanarPlanner.stage2`` flew it.

    a and b_per_s [1/s]: the linear-tangent pair; t_ign2_s [s]: stage-2 ignition;
    ended_by: ``cutoff`` (the energy cutoff E = E*) or ``propellant`` (the real
    depletion before it, final mode only); t_cut_s [s] and y_cut (planar state): where
    the burn ended; virtual_propellant: whether the burn ran in search mode (no
    depletion event, the mass floor armed); fairing_on: whether the fairing is still
    carried at the end; t_fairing_s [s]: when it dropped in or at the start of the burn
    (None when it dropped at staging or never); m_after_fairing_kg [kg]: the mass just
    after that drop (None likewise); m_empty_kg [kg]: m_d2 + P, plus the fairing when
    still on (the mass with every drop of stage-2 propellant gone); c_mps [m/s]: stage
    2's exhaust velocity; prefix: the trace through the end of the burn. Frame: planar
    ECI.
    """

    a: float
    b_per_s: float
    t_ign2_s: float
    ended_by: str
    t_cut_s: float
    y_cut: np.ndarray
    virtual_propellant: bool
    fairing_on: bool
    t_fairing_s: float | None
    m_after_fairing_kg: float | None
    m_empty_kg: float
    c_mps: float
    prefix: RunTrace

    @property
    def r_cut_m(self) -> float:
        """Radius at the end of the burn [m]."""
        return float(self.y_cut[_R])

    @property
    def v_r_cut_mps(self) -> float:
        """Radial velocity at the end of the burn [m/s]."""
        return float(self.y_cut[_VR])

    @property
    def tau_cut_s(self) -> float:
        """Burn time from stage-2 ignition to the end [s]."""
        return self.t_cut_s - self.t_ign2_s

    @property
    def m_cut_kg(self) -> float:
        """Mass at the end of the burn [kg]."""
        return float(self.y_cut[_M])

    @property
    def m_res_kg(self) -> float:
        """Residual propellant m_c - m_empty [kg] (negative in a search when the virtual
        propellant was needed: the run is short of orbit at this payload)."""
        return self.m_cut_kg - self.m_empty_kg

    @property
    def dv_margin_mps(self) -> float:
        """Delta-v margin c2 ln(m_c / m_empty) [m/s], signed (the vacuum delta-v the
        residual propellant would still give, or the shortfall)."""
        return self.c_mps * math.log(self.m_cut_kg / self.m_empty_kg)


def resume_builder(trace: RunTrace, stage_names: tuple[str, ...]) -> TraceBuilder:
    """A TraceBuilder holding everything of a frozen trace (its view, phases, events,
    status, flags, assumptions, release, flight start, hold, ignition times, burnouts
    and failure), to continue the run from where the trace stopped. The phase results
    are shared, not copied (they are never mutated)."""
    tr = TraceBuilder(stage_names, trace.view)
    tr.phases = list(trace.phases)
    tr.events = list(trace.events)
    tr.status = trace.status
    tr.flags = list(trace.flags)
    tr.assumptions = list(trace.assumptions)
    tr.t_release_s = trace.t_release_s
    tr.y_release = None if trace.y_release is None else trace.y_release.copy()
    tr.t_flight_start_s = trace.t_flight_start_s
    tr.y_flight_start = None if trace.y_flight_start is None else trace.y_flight_start.copy()
    tr.hold = trace.hold
    tr.t_ign_abs_s = dict(trace.t_ign_abs_s)
    tr.burnouts = dict(trace.burnouts)
    tr.failed_stage = trace.failed_stage
    tr.t_fail_s = trace.t_fail_s
    return tr


def _no_kick_info() -> dict[str, float]:
    """The kick fields of a MECO record without a kick (vertical-only guidance): no
    kick time (NaN), zero duration [s] and zero kick steering loss [m/s]."""
    return {"t_kick_s": math.nan, "kick_duration_s": 0.0, "kick_steering_loss_mps": 0.0}


def _check_delta(delta_rad: float | None) -> float:
    """delta_rad [rad] itself when it lies in (0, pi/2), else ValueError (a kicking
    flight needs a kick angle)."""
    if delta_rad is None or not 0.0 < delta_rad < 0.5 * math.pi:
        raise ValueError(f"delta_rad must lie in (0, pi/2), got {delta_rad!r}")
    return delta_rad


def _check_no_delta(delta_rad: float | None) -> None:
    """ValueError unless delta_rad is None: a flight that never kicks (vertical-only
    guidance) takes no kick angle, so none is recorded for it."""
    if delta_rad is not None:
        raise ValueError(
            f"vertical-only guidance never kicks: delta_rad must be None, got {delta_rad!r}"
        )


# -------------------------------------------------------------------------- planner


class PlanarPlanner:
    """The planar state machine (docs/physics.md, "Stage-1 guidance and events
    (planar)") for one vehicle (one payload).

    Inputs: the Vehicle (its ``aero`` is the drag model; None means no drag); ignition,
    an IgnitionSpec per stage name (later stages: reference release, t_ign_s >= 0);
    guidance, the GuidanceSpec; env, the PlanarEnvironment; end, one of
    PLANAR_END_KINDS; settings, the IntegratorSettings (dense output on for a recorded
    run, off for a search evaluation; event states come from ``event_state`` either
    way); z_ground_m, the ground altitude [m] of the impact event (0: the pad and the
    silo mouth); target, the circular TargetOrbit of the insertion cutoff, and ltg, the
    LtgSettings (the stage-2 limits tau_max_factor and mass_floor_factor, and the
    shooting): both needed by the stage-2 burn only.

    Entry points: ``start`` (the prelude to the flight start), ``to_kick`` (the
    delta-independent part of stage 1), ``from_kick`` (the kick, the gravity turn,
    MECO, and optionally the staging map and coast to stage-2 ignition), ``stage1``
    (both), ``stage2`` (one LTG burn from a hand-over), ``solve_stage2`` (the LTG
    shooting) and ``run`` (a recorded run at fixed guidance inputs). Every
    phase lists only the events that can end it and never the one that ended the
    previous phase; every flight phase that can reach the ground lists the ground
    event (a rising coast or rise cannot: it is split at the radial apex first, so it
    lists the apex instead); lit phases are split at the thrust kinks; coasts and the
    rise are split at the radial apex (and a falling lit rise at the radial
    turnaround), so w/V never flips sign inside a phase.
    """

    def __init__(
        self,
        vehicle: Vehicle,
        ignition: Mapping[str, IgnitionSpec],
        guidance: GuidanceSpec,
        env: PlanarEnvironment,
        end: str,
        settings: IntegratorSettings,
        *,
        z_ground_m: float = 0.0,
        target: TargetOrbit | None = None,
        ltg: LtgSettings | None = None,
    ) -> None:
        if end not in PLANAR_END_KINDS:
            raise ValueError(f"end must be one of {PLANAR_END_KINDS}, got {end!r}")
        missing = [s.name for s in vehicle.stages if s.name not in ignition]
        if missing:
            raise ValueError(f"no IgnitionSpec for stages {missing}")
        for stage in vehicle.stages[1:]:
            spec = ignition[stage.name]
            if spec.reference != "release" or spec.t_ign_s < 0.0:
                raise ValueError(
                    f"stage {stage.name!r}: a later stage ignites at t_ign_s >= 0 after its "
                    "staging coast (reference 'release')"
                )
        self.vehicle = vehicle
        self.ignition = dict(ignition)
        self.guidance = guidance
        self.env = env
        self.end = end
        self.settings = settings
        self.z_ground_m = z_ground_m
        self.target = target
        self.ltg = ltg
        self.model = PlanarDynamics2D(env.omega_p_rads, env.r_datum_m)
        self.atol = atol_for(PLANAR_STATE_NAMES)
        self.prelude = planar_prelude(env.omega_p_rads, env.r_datum_m)

    # ------------------------------------------------------------------ flight start

    def new_builder(self) -> TraceBuilder:
        """An empty TraceBuilder with the planar view (t_fs unknown yet)."""
        return TraceBuilder(
            self.vehicle.stage_names, PlanarView(self.env.omega_p_rads, self.env.r_datum_m)
        )

    def start(
        self, assist: AssistModel | None = None, track: TrackGeometry | None = None
    ) -> FlightStart:
        """The prelude to the flight start: a pad (``assist`` None or the ``none``
        model, no track) or a track push (``start_track``)."""
        if track is None:
            if assist is not None and assist.name != "none":
                raise ValueError(f"assist model {assist.name!r} needs a track")
            return self.start_pad()
        if assist is None or assist.name == "none":
            raise ValueError("a track was given without an assist model")
        return self.start_track(assist, track)

    def start_pad(self) -> FlightStart:
        """A pad start: t = 0 at hold-down release, the vehicle at rest on the pad
        (``planar_rest_state`` at z = 0, theta = 0, v_theta = omega_p R_E, V = 0).

        With stage 1 lit before t = 0 the vehicle is clamped from ignition to release
        (closed-form mass). At release it stays clamped until its delivered thrust
        (at the pad pressure p(0), so the back-pressure p(0) A_e counts) exceeds its
        weight m g_ref (``prelude.hold_until_liftoff`` in PLANAR_LAYOUT: the liftoff
        root; status no_liftoff if never). The flight starts at release or at the
        liftoff root, whichever is later (t_fs), with theta = 0 there.
        """
        stage0 = self.vehicle.stages[0]
        spec = self.ignition[stage0.name]
        if spec.reference != "release":
            raise ValueError("a pad run has no push: use reference 'release' for the first stage")
        if spec.lights_at_height:
            raise ValueError("a pad run has no track exit: a ramp start by height needs a push")
        tr = self.new_builder()
        g_ref = self.env.g_ref_mps2
        p0 = self.env.ambient_pa(0.0)
        t_release = 0.0
        t_ign = spec.t_ign_abs_s(t_release)
        if not spec.fails:
            tr.t_ign_abs_s[stage0.name] = t_ign
        flag_ignored_ignition_settings(tr, stage0.name, spec)
        schedule = stage0.schedule(t_ign, spec.startup, spec.fails)
        params = HoldParams(schedule, g_ref, p0)
        m0 = self.vehicle.liftoff_mass_kg()
        y = planar_rest_state(0.0, m0, self.env.omega_p_rads, self.env.r_datum_m)
        hold_start = t_release
        force_min = math.inf
        if t_ign < t_release and not spec.fails:
            hold_start = t_ign
            tr.add_event("ignition", t_ign, HOLD_KIND, 0, y)
            y, f_min = hold_closed_form(
                tr,
                params,
                t_ign,
                t_release,
                y,
                vehicle=self.vehicle,
                settings=self.settings,
                layout=PLANAR_LAYOUT,
            )
            force_min = min(force_min, f_min)
        tr.t_release_s = t_release
        tr.y_release = y.copy()
        label = HOLD_KIND if hold_start < t_release else RELEASE_LABEL
        tr.add_event("release", t_release, label, 0, y)
        t_start, y, f_min = hold_until_liftoff(
            tr,
            params,
            t_release,
            y,
            vehicle=self.vehicle,
            settings=self.settings,
            layout=PLANAR_LAYOUT,
        )
        force_min = min(force_min, f_min)
        if hold_start < t_release or t_start > t_release:
            burned = m0 - float(y[_M])
            tr.hold = HoldSummary(hold_start, t_start, t_start - t_release, force_min, burned)
        if tr.status == "no_liftoff":
            if spec.fails:
                tr.failed_stage = stage0.name
            return FlightStart(tr.finish(), tr.status, None, None, None)
        return self._begin_flight(tr, t_start, y, None if spec.fails else t_ign)

    def start_track(self, assist: AssistModel, track: TrackGeometry) -> FlightStart:
        """A track start: t = 0 at push start, the shared prelude ``fly_track`` in
        PLANAR_LAYOUT with the track's constant g_eff = g_ref and the constant ambient
        pressure p(z_exit), then ``map_release_planar`` (vertical tracks only in Phase 2)
        at the track-end root; the flight starts at release (t_fs = t_release, theta =
        0). A drive-limit stop on the track ends the start with status drive_limit. A
        first stage stated by ``height_method: event`` flies the push unlit and starts
        the flight with a pending ignition at the altitude z_exit + h
        (``FlightStart.ign1_alt_m``), which ``_fly_to_kick`` resolves."""
        stage0 = self.vehicle.stages[0]
        spec = self.ignition[stage0.name]
        tr = self.new_builder()
        z_exit = track.start_altitude_m + track.z(track.length_m)
        exit_ = fly_track(
            tr,
            assist,
            track,
            spec,
            vehicle=self.vehicle,
            settings=self.settings,
            g_eff_mps2=self.env.g_ref_mps2,
            p_amb_pa=self.env.ambient_pa(z_exit),
            prelude=self.prelude,
        )
        if exit_ is None:
            return FlightStart(tr.finish(), tr.status, None, None, None)
        y_rel = map_release_planar(exit_, self.env.omega_p_rads, self.env.r_datum_m)
        t = exit_.t_release_s
        tr.t_release_s = t
        tr.y_release = y_rel.copy()
        tr.add_event("release", t, ASSIST_KIND, 0, y_rel)
        t_ign = tr.t_ign_abs_s.get(stage0.name)
        ign_alt = None
        if spec.lights_at_height and not spec.fails and spec.trigger_value is not None:
            ign_alt = exit_.z_exit_m + spec.trigger_value
        return self._begin_flight(tr, t, y_rel, t_ign, ign_alt)

    def _begin_flight(
        self,
        tr: TraceBuilder,
        t: float,
        y: np.ndarray,
        t_ign: float | None,
        ign_alt_m: float | None = None,
    ) -> FlightStart:
        """Record the flight start (t_fs, theta = 0 there) and bind the view to it.
        t_ign [s]: stage 1's ignition time, or ign_alt_m [m]: the altitude above the
        datum at which it lights (a pending ignition); both None for a failed one."""
        tr.t_flight_start_s = t
        tr.y_flight_start = np.array(y, dtype=float, copy=True)
        tr.rebind_view(PlanarView(self.env.omega_p_rads, self.env.r_datum_m, t))
        return FlightStart(
            tr.finish(), "nominal", t, tr.y_flight_start.copy(), t_ign, ign1_alt_m=ign_alt_m
        )

    # ---------------------------------------------------------------------- stage 1

    def to_kick(self, start: FlightStart) -> KickPoint:
        """Stage 1 from the flight start to the kick trigger (independent of delta).

        An unpowered COAST_PRE_IGN runs from t_fs to the ignition time when it is
        later (apex split, ground event; no kick trigger: the trigger is judged from
        the first lit instant on); with a pending ignition (``FlightStart.ign1_alt_m``,
        ``height_method: event``) it runs instead to the ``ignition_height`` event,
        the altitude crossed upward, listed in its rising sub-phase, and stage 1 lights
        at that root (at once when the flight start is already within ATOL_M of it).
        At the first lit instant the planner evaluates the
        trigger g = min(V - v_k, w) itself: g > zero_tol (a release or an ignition
        already faster than v_k while rising) logs ``kick_start`` there and the kick
        starts at once, with no VERTICAL_RISE phase. Otherwise VERTICAL_RISE with
        radial thrust, split at the thrust kinks and at the radial apex/turnaround,
        listing propellant, the rising apex split or (falling) the ground and the
        turnaround split, ``kick_start`` and ``kick_deadline`` (t_ign + deadline). Raises
        GuidanceFailure: "impact" (the ground before the kick), "no_kick" (the deadline,
        or burnout before the trigger), "no_ignition" (a pending ignition whose coast
        reaches its apex below the ignition altitude). With vertical-only guidance the
        rise runs to burnout (KickPoint.kicked False). ValueError when the start has no
        flight or stage 1's ignition fails.
        """
        if start.status != "nominal" or start.t_fs_s is None or start.y_fs is None:
            raise ValueError(f"no flight to guide: the prelude ended with status {start.status!r}")
        if not start.stage1_lights:
            raise ValueError("stage 1's ignition fails: there is nothing to guide")
        tr = resume_builder(start.prefix, self.vehicle.stage_names)
        how, t, y, schedule = self._fly_to_kick(
            tr, start.t_fs_s, start.y_fs, start.t_ign1_s, start.ign1_alt_m
        )
        if how == "impact":
            raise GuidanceFailure(
                "impact", f"the vehicle hit the ground at t = {t:.6g} s before the kick"
            )
        return KickPoint(start, tr.finish(), t, y, schedule, how == "kick")

    def from_kick(
        self, delta_rad: float | None, kick: KickPoint, *, through_staging: bool = True
    ) -> Handover:
        """Stage 1 from the kick trigger to MECO at the kick angle delta_rad [rad] (in
        (0, pi/2); None, and only None, for vertical-only guidance: ValueError
        otherwise), then, with through_staging, the staging map and the staging coast to
        stage-2 ignition.

        KICK (FixedTilt(delta)) lists propellant, the ground, ``kick_end``
        (sin(beta_rel - delta) = 0 upward) and ``kick_timeout`` (t_kick + kick_max);
        GRAVITY_TURN (AlongVrel) lists propellant and the ground. MECO is the
        propellant event (in the kick if the velocity never aligned). Raises
        GuidanceFailure "impact" (the ground before stage-2 ignition, including in the
        staging coast) or "kick_timeout".
        """
        tr = resume_builder(kick.prefix, self.vehicle.stage_names)
        t, y = kick.t_s, kick.y
        kick_info = _no_kick_info()
        if kick.kicked:
            delta_rad = _check_delta(delta_rad)
            how, t, y, kick_info = self._fly_kick_turn(tr, delta_rad, t, y, kick.schedule)
            if how == "impact":
                raise GuidanceFailure(
                    "impact", f"the vehicle hit the ground at t = {t:.6g} s before MECO"
                )
        else:
            _check_no_delta(delta_rad)
        meco = self._meco_record(tr, t, y, kick_info)
        if not through_staging:
            fairing_on = self.vehicle.fairing_mass_kg > 0.0  # nothing drops before staging
            return Handover(delta_rad, meco, None, None, fairing_on, tr.finish())
        if self.vehicle.n_stages < 2:
            raise ValueError("through_staging needs a second stage")
        how, t, y, fairing_on = self._stage_and_coast(tr, t, y)
        if how == "impact":
            raise GuidanceFailure(
                "impact", f"the vehicle hit the ground at t = {t:.6g} s in the staging coast"
            )
        return Handover(delta_rad, meco, t, y, fairing_on, tr.finish())

    def stage1(
        self, delta_rad: float | None, start: FlightStart, *, through_staging: bool = True
    ) -> Handover:
        """``from_kick(delta_rad, to_kick(start), through_staging=...)``: one stage-1
        flight (the unit of the gamma* inner solve)."""
        return self.from_kick(delta_rad, self.to_kick(start), through_staging=through_staging)

    # --------------------------------------------------------------- recorded run

    def run(
        self,
        delta_rad: float | None,
        assist: AssistModel | None = None,
        track: TrackGeometry | None = None,
        *,
        ltg: tuple[float, float] | None = None,
    ) -> RunTrace:
        """A recorded run at fixed guidance inputs: the kick angle delta_rad [rad] (None
        for vertical-only guidance, where a delta raises ValueError, or for a failed
        stage-1 ignition) and, for a lit stage 2, the linear-tangent pair ltg = (a,
        b [1/s]) (ValueError when missing).

        Ends: ``stage1_burnout`` (the run stops at MECO with an ``end`` event);
        ``insertion`` (stage 2 flies LTG_BURN with the real depletion event, no mass
        floor: at the energy cutoff status inserted when the cutoff state meets the LTG
        acceptance, |r_c - r_t| < accept_r_m and |v_r,c| < accept_vr_mps, else
        off_target with a flag giving the misses, e and the perigee altitude;
        short_of_orbit when the propellant runs out first; an ``end`` event closes the
        run); ``apex`` and ``impact`` (after a failed ignition of stage 1, or of stage 2
        after the staging coast, or after a lit stage 2's burnout short of orbit: the
        unpowered COAST to the apex, and for impact on to the ground, status impact; a
        short-of-orbit vehicle whose perigee lies above the ground never comes down, so
        such a coast ends at the integrator's t_max guard with RuntimeError). After a
        lit stage 2 that reaches the energy cutoff, apex and impact end the run at the
        cutoff like insertion (status inserted or off_target, with a flag): there is no
        terminal coast. An impact before the end ends the run with status impact. Other
        GuidanceFailure kinds (no_kick, no_ignition, kick_timeout, lofted_overshoot)
        propagate. A stage 1 that lights at an altitude (a pending ignition) is a lit
        stage 1, never a failed one.
        """
        start = self.start(assist, track)
        tr = resume_builder(start.prefix, self.vehicle.stage_names)
        if start.status != "nominal" or start.t_fs_s is None or start.y_fs is None:
            return tr.finish()
        t, y = start.t_fs_s, start.y_fs
        if not start.stage1_lights:
            self._fail_ignition(tr, 0, t, y)
            self._terminal_coast(tr, 0, t, y)
            return tr.finish()
        how, t, y, schedule = self._fly_to_kick(tr, t, y, start.t_ign1_s, start.ign1_alt_m)
        kick_info = _no_kick_info()
        if how == "kick":
            delta_rad = _check_delta(delta_rad)
            how, t, y, kick_info = self._fly_kick_turn(tr, delta_rad, t, y, schedule)
        elif how == "meco":
            _check_no_delta(delta_rad)
        if how == "impact":
            return tr.finish()
        self._meco_record(tr, t, y, kick_info)
        if self.end == "stage1_burnout":
            tr.add_event("end", t, tr.phases[-1].spec.kind, 0, y)
            return tr.finish()
        if self.vehicle.n_stages < 2:
            raise ValueError(f"end {self.end!r} needs a second stage")
        how, t, y, fairing_on = self._stage_and_coast(tr, t, y)
        if how == "impact":
            return tr.finish()
        stage2 = self.vehicle.stages[1]
        if self.ignition[stage2.name].fails:
            if self.end not in ("impact", "apex"):
                raise ValueError(f"stage {stage2.name!r} fails: the run must end at impact")
            flag_ignored_ignition_settings(tr, stage2.name, self.ignition[stage2.name])
            self._fail_ignition(tr, 1, t, y)
            self._terminal_coast(tr, 1, t, y)
            return tr.finish()
        if ltg is None:
            raise ValueError("a lit stage 2 needs the linear-tangent pair ltg = (a, b)")
        burn = self._fly_stage2(tr, t, y, fairing_on, ltg[0], ltg[1], virtual=False)
        t, y = burn.t_cut_s, burn.y_cut
        if burn.ended_by == "impact":
            tr.status = "impact"
            return tr.finish()
        cut = burn.ended_by == CUTOFF_EVENT
        tr.status = self._cutoff_status(tr, y) if cut else SHORT_OF_ORBIT_STATUS
        if self.end == "insertion" or cut:
            if self.end != "insertion":
                tr.flags.append(
                    f"end {self.end}: stage 2 reached the target orbit at t = {t:.6g} s; "
                    "the run ends at the cutoff (no terminal coast: an orbit has no "
                    "impact, and its apex is the apogee)"
                    if tr.status == INSERTED_STATUS
                    else f"end {self.end}: stage 2 reached the energy cutoff off target at "
                    f"t = {t:.6g} s; the run ends at the cutoff (no terminal coast)"
                )
            tr.add_event("end", t, LTG_BURN, 1, y)
            return tr.finish()
        self._terminal_coast(tr, 1, t, y)
        return tr.finish()

    # ---------------------------------------------------------------------- stage 2

    def _require_stage2(self) -> tuple[TargetOrbit, LtgSettings]:
        """The target orbit and the LTG settings a stage-2 burn needs (ValueError when
        the planner was built without them or the vehicle has one stage)."""
        if self.vehicle.n_stages < 2:
            raise ValueError("a stage-2 burn needs a second stage")
        if self.target is None or self.ltg is None:
            raise ValueError("a stage-2 burn needs the planner's target and ltg settings")
        return self.target, self.ltg

    def _cutoff_status(self, tr: TraceBuilder, y: np.ndarray) -> str:
        """Status of a recorded run whose stage 2 ended at the energy cutoff in state y
        (planar, inertial): INSERTED_STATUS when |r_c - r_t| < accept_r_m [m] and
        |v_r,c| < accept_vr_mps [m/s] (the acceptance of a converged LTG root), else
        OFF_TARGET_STATUS with a run flag giving both misses, the eccentricity and the
        perigee altitude above r_datum (the cutoff fires for any pair that raises E to
        E*, so a pair that is not a root still reaches it)."""
        target, st = self._require_stage2()
        r, v_r = float(y[_R]), float(y[_VR])
        dr = r - target.r_m
        if abs(dr) < st.accept_r_m and abs(v_r) < st.accept_vr_mps:
            return INSERTED_STATUS
        elements = orbit_elements(r, v_r, float(y[_VT]), self.env.mu_m3s2)
        tr.flags.append(
            f"off target: the energy cutoff state misses the LTG acceptance (r_c - r_t = "
            f"{dr:.6g} m against {st.accept_r_m:.3g} m, v_r,c = {v_r:.6g} m/s against "
            f"{st.accept_vr_mps:.3g} m/s; e = {elements.e:.3g}, perigee altitude "
            f"{elements.r_p_m - self.env.r_datum_m:.6g} m): the flown (a, b) is not a "
            "converged root at this run's settings"
        )
        return OFF_TARGET_STATUS

    @property
    def tau_b2_s(self) -> float:
        """Stage 2's full-thrust burn time tau_b = m_p2 c2 / T2_vac [s] (the no_cutoff
        limit and the LTG physics guess read it)."""
        return self.vehicle.stages[1].burn_time_s

    def stage2(
        self, handover: Handover, a: float, b_per_s: float, *, virtual_propellant: bool
    ) -> Stage2Result:
        """One stage-2 burn (LTG_BURN under ``LinearTangent(a, b, t_ign2)``) from the
        hand-over's stage-2 ignition, to the energy cutoff.

        Inputs: the Handover (with its stage-2 ignition state; the fairing as it left
        staging); a (dimensionless) and b_per_s [1/s]; virtual_propellant: True for a
        search shot (no depletion event: stage 2 burns on past its real load, and the
        mass floor mass_floor_factor (m_d2 + P) is armed), False for the final mode (the
        real depletion event, no floor). Output: the Stage2Result (the trace through
        the burn in ``prefix``). Raises GuidanceFailure: lofted_overshoot (E >= E*
        already at ignition), impact (the ground), no_cutoff (tau beyond tau_max_factor
        tau_b), mass_floor; ValueError when the hand-over stopped at MECO or stage 2
        fails. A real depletion before the cutoff returns ended_by ``propellant``.
        """
        if handover.y_ign2 is None or handover.t_ign2_s is None:
            raise ValueError("the hand-over stopped at MECO: fly it through staging")
        if self.ignition[self.vehicle.stages[1].name].fails:
            raise ValueError("stage 2's ignition fails: there is no stage-2 burn")
        tr = resume_builder(handover.prefix, self.vehicle.stage_names)
        burn = self._fly_stage2(
            tr,
            handover.t_ign2_s,
            handover.y_ign2,
            handover.fairing_on,
            a,
            b_per_s,
            virtual=virtual_propellant,
        )
        if burn.ended_by == "impact":
            raise GuidanceFailure(
                "impact", f"the vehicle hit the ground at t = {burn.t_cut_s:.6g} s in stage 2"
            )
        return burn

    def solve_stage2(
        self,
        handover: Handover,
        *,
        warm: tuple[float, float] | None = None,
        max_rungs: int | None = None,
    ) -> LtgSolution[Stage2Result]:
        """The LTG shooting from a hand-over (``guidance.solve_ltg``): search shots
        (virtual propellant, mass floor) at the planner's settings, the target radius
        r_t, the ladder of ``ltg_guess_ladder`` from the hand-over's inertial
        flight-path angle at stage-2 ignition and tau_b (warm first when given), at
        most max_rungs rungs (default: the LtgSettings' max_rungs). Raises
        GuidanceFailure (lofted_overshoot at once, else nonconverged when the ladder is
        exhausted)."""
        target, st = self._require_stage2()
        if handover.y_ign2 is None:
            raise ValueError("the hand-over stopped at MECO: fly it through staging")
        self._check_not_lofted(handover.y_ign2, target)
        if max_rungs is not None:
            st = dataclasses.replace(st, max_rungs=max_rungs)
        ladder = ltg_guess_ladder(st, handover.gamma_in_ign2_rad, self.tau_b2_s, warm)

        def shoot(a: float, b: float) -> Stage2Result:
            return self.stage2(handover, a, b, virtual_propellant=True)

        return solve_ltg(shoot, target.r_m, st, ladder)

    def _check_not_lofted(self, y: np.ndarray, target: TargetOrbit) -> None:
        """GuidanceFailure("lofted_overshoot") when the orbital energy of the stage-2
        ignition state y is already at or above the target's E* (the cutoff could only
        fire at once, so no LTG pair can reach the target)."""
        mu = self.env.mu_m3s2
        energy, e_star = orbital_energy_Jkg(y, mu), target.energy_Jkg(mu)
        if energy >= e_star:
            raise GuidanceFailure(
                "lofted_overshoot",
                f"orbital energy {energy:.9g} J/kg at stage-2 ignition is already at or "
                f"above the target's {e_star:.9g} J/kg",
            )

    def _fly_stage2(
        self,
        tr: TraceBuilder,
        t: float,
        y: np.ndarray,
        fairing_on: bool,
        a: float,
        b_per_s: float,
        *,
        virtual: bool,
    ) -> Stage2Result:
        """LTG_BURN from stage-2 ignition at t [s] (state y; the fairing on or not) under
        LinearTangent(a, b, t): the ignition event, the fairing checked at ignition
        (dropped there, with a flag, when the heating criterion was met during the
        staging coast), then sub-phases listing the energy cutoff, no_cutoff at t +
        tau_max_factor tau_b, the ground, the fairing event while the fairing is on, and
        the mass floor (virtual) or the real depletion at m_empty (final). A fairing
        event applies the FAIRING map and continues with the same law. A fairing still
        on when the burn ends at the cutoff or the depletion is part of m_empty (m_d2 +
        P + F) and raises a run flag. Returns the Stage2Result with ended_by in
        {cutoff, propellant, impact}; raises GuidanceFailure for lofted_overshoot,
        no_cutoff and mass_floor."""
        target, st = self._require_stage2()
        self._check_not_lofted(y, target)
        vehicle = self.vehicle
        stage2 = vehicle.stages[1]
        spec = self.ignition[stage2.name]
        t_ign2 = t
        tr.t_ign_abs_s[stage2.name] = t_ign2
        tr.add_event("ignition", t, LTG_BURN, 1, y)
        schedule = stage2.schedule(t_ign2, spec.startup, spec.fails)
        law = LinearTangent(a, b_per_s, t_ign2)
        m_bare = stage2.dry_mass_kg + vehicle.payload_mass_kg
        fairing = vehicle.fairing_mass_kg
        common: tuple[EventSpec, ...] = (
            ev_energy_cutoff(target, self.env.mu_m3s2),
            ev_time(t_ign2 + st.tau_max_factor * self.tau_b2_s, "no_cutoff"),
        )
        if virtual:
            common += (ev_mass_floor(st.mass_floor_factor * m_bare),)
        rule = vehicle.fairing_rule
        t_fair: float | None = None
        m_after: float | None = None
        if fairing_on and rule.limit_W_m2 is not None:
            if fmh_rate_W_m2(y, self.env) < rule.limit_W_m2:
                tr.add_event(FAIRING_EVENT, t, LTG_BURN, 1, y)
                tr.flags.append(
                    f"fairing: the heating criterion 0.5 rho V^3 < {rule.limit_W_m2:.6g} W/m^2 "
                    f"was met during the staging coast; the fairing drops at stage-2 "
                    f"ignition (t = {t:.6g} s)"
                )
                y = map_fairing_planar(y, fairing)
                fairing_on, t_fair, m_after = False, t, float(y[_M])
        while True:
            extra = common
            if fairing_on and rule.limit_W_m2 is not None:
                extra += (ev_fmh(rule.limit_W_m2, self.env),)
            m_empty = m_bare + (fairing if fairing_on else 0.0)
            m_event = math.nan if virtual else m_empty
            ended, t, y = self._burn(
                tr, LTG_BURN, 1, schedule, law, extra, t, y, m_empty_kg=m_event
            )
            if ended == FAIRING_EVENT:
                y = map_fairing_planar(y, fairing)
                fairing_on, t_fair, m_after = False, t, float(y[_M])
                continue
            if ended in ("no_cutoff", "mass_floor"):
                raise GuidanceFailure(
                    ended,
                    f"stage 2 reached {ended} at t = {t:.6g} s (tau = {t - t_ign2:.6g} s) "
                    f"before the energy cutoff (a = {a:.6g}, b = {b_per_s:.6g} 1/s)",
                )
            if ended != "impact":
                tr.burnouts[stage2.name] = (t, y.copy())
                if fairing_on:
                    tr.flags.append(
                        f"fairing: still on at the end of the stage-2 burn ({ended}, t = "
                        f"{t:.6g} s); m_res and dv_margin count it as empty mass"
                    )
            return Stage2Result(
                a=a,
                b_per_s=b_per_s,
                t_ign2_s=t_ign2,
                ended_by=ended,
                t_cut_s=t,
                y_cut=y,
                virtual_propellant=virtual,
                fairing_on=fairing_on,
                t_fairing_s=t_fair,
                m_after_fairing_kg=m_after,
                m_empty_kg=m_empty,
                c_mps=stage2.c_mps,
                prefix=tr.finish(),
            )

    # --------------------------------------------------------------- phase helpers

    def _integrate(self, tr: TraceBuilder, spec: PhaseSpec, y: np.ndarray) -> PhaseResult:
        """Run one planar phase, add it to the builder and log every event occurrence
        with its state from ``event_state`` (dense output not needed)."""
        self.model.check_params(spec.params)
        res = tr.add_phase(integrate_phase(spec, y, self.settings))
        for name, te in res.event_times:
            tr.add_event(name, te, spec.kind, spec.stage_index, event_state(res, name, te))
        return res

    def _step_cap(self, schedule: ThrustSchedule | None, t: float) -> float:
        """The max_step [s] of a planar flight phase starting at t [s]: the ramp or lag
        cap of ``prelude.max_step_cap`` (math.inf for a coast, schedule None, or a
        burn at full thrust) capped at ``settings.planar_max_step_s`` (docs/physics.md,
        "Integrator": the cap keeps DOP853 from stepping across the clustered transonic
        C_D knots in one step, the noise floor of the gamma* inner solve). The HOLD and
        the track push (``prelude``) do not use it."""
        return min(max_step_cap(schedule, t, self.settings), self.settings.planar_max_step_s)

    def _unpowered(self) -> PlanarParams:
        """PlanarParams of an unpowered phase."""
        return self.env.params(None, None, self.vehicle)

    def _rising(self, t: float, y: np.ndarray, params: PlanarParams, hint: bool | None) -> bool:
        """Whether the next phase starts rising (w > 0): the caller's hint when it
        knows, else the sign of w, and within ATOL_MPS of w = 0 the sign of dv_r/dt
        from the phase's own RHS (rising when >= 0)."""
        if hint is not None:
            return hint
        w = float(y[_VR])
        if w > ATOL_MPS:
            return True
        if w < -ATOL_MPS:
            return False
        return float(rhs_planar(t, y, params)[_VR]) >= 0.0

    def _on_ground_falling(self, y: np.ndarray) -> bool:
        """True for a state within ATOL_M of the ground altitude (the impact surface)."""
        return abs(float(self.model.altitude(y)) - self.z_ground_m) <= ATOL_M

    def _coast(
        self,
        tr: TraceBuilder,
        kind: str,
        k: int,
        t: float,
        t_end: float | None,
        y: np.ndarray,
        *,
        hint: bool | None = None,
        stop_at_apex: bool = False,
        extra: tuple[EventSpec, ...] = (),
    ) -> tuple[float, np.ndarray, str]:
        """Unpowered flight of kind ``kind`` from t to t_end (None: open-ended) [s],
        split at the radial apex: a rising phase lists ``apex``, a falling one the
        ground. Returns (t, y, how), how in {"time", "apex", "impact"} or the name of
        an ``extra`` event; an apex continues falling unless stop_at_apex; an impact
        sets tr.status. extra: terminal events listed after ``apex`` in the rising
        sub-phases only (none by default, which leaves every event list as before),
        so an event of the altitude is monotone where it is listed (the altitude rises
        monotonically up to the apex split; the step that overshoots the apex is
        covered by the fold of ``engine.ev_altitude_up``, docs/physics.md, "Event
        rules"); when one fires the coast returns at its root with how = its name. A
        falling phase that starts on
        the ground (within ATOL_M, moving down) is the impact itself (a zero-length
        pass-through), as in the 1-D planner. Every sub-phase integrates with max_step
        = planar_max_step_s (``_step_cap``)."""
        params = self._unpowered()
        extra_names = {ev.name for ev in extra}
        while True:
            rising = self._rising(t, y, params, hint)
            hint = None
            events: tuple[EventSpec, ...] = (
                (ev_radial_apex(), *extra) if rising else (ev_ground(self.model, self.z_ground_m),)
            )
            spec = PhaseSpec(
                kind, k, t, t_end, rhs_planar, params, events, self.atol, self._step_cap(None, t)
            )
            if not rising and self._on_ground_falling(y):
                note = (
                    f"{kind} starts on the ground (alt within {ATOL_M:.3g} m of "
                    f"{self.z_ground_m:.6g} m) moving down: impact at t0"
                )
                tr.add_phase(_pass_through(spec, y, "impact", [note], (("impact", t),)))
                tr.add_event("impact", t, kind, k, y)
                tr.status = "impact"
                return t, y, "impact"
            res = self._integrate(tr, spec, y)
            t, y = res.t_end, res.y_end
            if res.ended_by in ("t_end", "zero_span"):
                return t, y, "time"
            if res.ended_by in extra_names:
                return t, y, res.ended_by
            if res.ended_by == "apex":
                if stop_at_apex:
                    return t, y, "apex"
                hint = False
                continue
            tr.status = "impact"
            return t, y, "impact"

    def _burn(
        self,
        tr: TraceBuilder,
        kind: str,
        k: int,
        schedule: ThrustSchedule,
        law: SteeringLaw,
        extra: tuple[EventSpec, ...],
        t: float,
        y: np.ndarray,
        *,
        ground: bool = True,
        m_empty_kg: float | None = None,
    ) -> tuple[str, float, np.ndarray]:
        """One lit mode of stage k from t [s]: sub-phases of kind ``kind`` split at the
        thrust kinks (the ramp end is logged as ``ramp_end``), each with the step cap
        ``_step_cap`` (``prelude.max_step_cap``, capped at planar_max_step_s) and the
        events propellant (m - m_empty_kg, with
        m_empty_kg defaulting to stage 1's burnout mass ``stack_dry_mass_kg(k)``; NaN
        leaves the event out: stage 2's virtual propellant in a search), the ground
        (unless ground is False: a rising rise, which its apex split ends before it can
        reach the ground) and ``extra``. Returns (ended_by, t, y) for the first
        terminal event."""
        m_dry = self.vehicle.stack_dry_mass_kg(k) if m_empty_kg is None else m_empty_kg
        params = self.env.params(schedule, law, self.vehicle)
        base: tuple[EventSpec, ...] = ()
        if not math.isnan(m_dry):
            base += (ev_propellant(m_dry, PLANAR_LAYOUT),)
        if ground:
            base += (ev_ground(self.model, self.z_ground_m),)
        while True:
            kinks = [kk for kk in schedule.kink_times() if kk > t + ZERO_SPAN_S]
            t_b = kinks[0] if kinks else None
            spec = PhaseSpec(
                kind,
                k,
                t,
                t_b,
                rhs_planar,
                params,
                (*base, *extra),
                self.atol,
                self._step_cap(schedule, t),
            )
            res = self._integrate(tr, spec, y)
            t, y = res.t_end, res.y_end
            if res.ended_by in ("t_end", "zero_span"):
                if t_b is not None and schedule.startup.effective_kind == "ramp":
                    tr.add_event("ramp_end", t, kind, k, y)
                continue
            return res.ended_by, t, y

    def _fly_to_kick(
        self,
        tr: TraceBuilder,
        t: float,
        y: np.ndarray,
        t_ign: float | None,
        ign_alt_m: float | None = None,
    ) -> tuple[str, float, np.ndarray, ThrustSchedule]:
        """The pre-ignition coast and the vertical rise (see ``to_kick``) from the flight
        start t [s] (planar state y, theta = 0) with stage 1 lit at the absolute time
        t_ign [s], or, when t_ign is None, at the altitude ign_alt_m [m] above the datum
        (a pending ignition: ``_coast_to_ignition``, which sets t_ign to the event root
        and records it in tr.t_ign_abs_s); the callers have checked that a flight exists
        and stage 1 lights. From the ignition on, the thrust schedule, its step caps and
        the kick deadline are built from t_ign exactly as for a time-lit stage. Returns
        (how, t, y, schedule), how in {"kick", "meco", "impact"} ("meco" only for
        vertical-only guidance). Raises GuidanceFailure("no_kick", "no_ignition").

        The kick at the first lit instant is decided here, not by a zero-length rise
        ended through the engine's already-past rule, so this nominal case (every
        release faster than v_k) leaves no engine note, hence no run flag. The rising
        rise does not list the ground event: its apex split ends it first, and at a pad
        liftoff root (v_r = 0 and dv_r/dt = 0) the engine's predictor would see the
        altitude stay at zero and disarm the event with a spurious flag."""
        stage0 = self.vehicle.stages[0]
        spec = self.ignition[stage0.name]
        hint: bool | None = True  # a flight starts at a liftoff root or a release moving up
        if t_ign is None:
            if ign_alt_m is None:
                raise ValueError("stage 1 needs an ignition time or an ignition altitude")
            t, y, coasted = self._coast_to_ignition(tr, t, y, ign_alt_m)
            if coasted:
                hint = None
            t_ign = t
            tr.t_ign_abs_s[stage0.name] = t_ign
        schedule = stage0.schedule(t_ign, spec.startup, spec.fails)
        if t_ign > t + ZERO_SPAN_S:
            t, y, how = self._coast(tr, COAST_PRE_IGN, 0, t, t_ign, y, hint=hint)
            hint = None
            if how == "impact":
                return "impact", t, y, schedule
        g = self.guidance
        kick_events: tuple[EventSpec, ...] = ()
        kick_now = False
        if g.kicks:
            trigger = ev_kick_start(g.v_kick_mps, self.env.omega_p_rads)
            kick_events = (trigger, ev_time(t_ign + g.kick_deadline_s, "kick_deadline"))
            kick_now = trigger.fn(t, y) > trigger.zero_tol
        if not tr.has_event("ignition", 0):
            tr.add_event("ignition", t, KICK if kick_now else VERTICAL_RISE, 0, y)
        if kick_now:
            tr.add_event("kick_start", t, KICK, 0, y)
            return "kick", t, y, schedule
        law = Radial()
        params = self.env.params(schedule, law, self.vehicle)
        while True:
            rising = self._rising(t, y, params, hint)
            hint = None
            split = ev_radial_apex() if rising else ev_radial_turnaround()
            ended, t, y = self._burn(
                tr, VERTICAL_RISE, 0, schedule, law, (split, *kick_events), t, y, ground=not rising
            )
            if ended == "kick_start":
                return "kick", t, y, schedule
            if ended == "impact":
                tr.status = "impact"
                return "impact", t, y, schedule
            if ended == "propellant":
                if g.kicks:
                    raise GuidanceFailure(
                        "no_kick",
                        f"stage 1 burned out at t = {t:.6g} s before the kick trigger "
                        f"(v_k = {g.v_kick_mps:.6g} m/s)",
                    )
                return "meco", t, y, schedule
            if ended == "kick_deadline":
                raise GuidanceFailure(
                    "no_kick",
                    f"|v_rel| did not reach v_k = {g.v_kick_mps:.6g} m/s while rising within "
                    f"{g.kick_deadline_s:.6g} s of stage-1 ignition",
                )
            hint = ended == "turnaround"  # an apex hands over falling, a turnaround rising

    def _coast_to_ignition(
        self, tr: TraceBuilder, t: float, y: np.ndarray, ign_alt_m: float
    ) -> tuple[float, np.ndarray, bool]:
        """A pending stage-1 ignition (``height_method: event``): COAST_PRE_IGN from the
        flight start t [s] (planar state y, moving up) to the ``ignition_height`` event
        (``ev_altitude_up``: alt - ign_alt_m crossing upward, ign_alt_m [m] above the
        datum), listed in the rising sub-phase beside the apex split (the altitude is
        monotone there). Returns (t, y, coasted): the event root and the state there with
        coasted True (a COAST_PRE_IGN phase was flown), or the flight start itself with
        coasted False when it is already within the event's zero_tol (ATOL_M) below the
        altitude or above it, which the planner decides here, as it decides the kick at
        the first lit instant, so no zero-length phase and no engine note is involved
        (the same flag, with the same meaning, as ``VerticalPlanner._coast_to_ignition``).
        Raises GuidanceFailure("no_ignition") when the coast reaches its apex first: the
        stage never gets to its ignition altitude (drag, mu/r^2 and rotation put the real
        apex off the drag-free apex v_e^2 / (2 g_eff), which the resolver checks before
        the run). Frame: planar ECI; altitudes above the datum."""
        event = ev_altitude_up(self.model, ign_alt_m, IGNITION_HEIGHT_EVENT)
        if event.fn(t, y) >= -event.zero_tol:
            return t, y, False
        t, y, how = self._coast(
            tr, COAST_PRE_IGN, 0, t, None, y, hint=True, stop_at_apex=True, extra=(event,)
        )
        if how == IGNITION_HEIGHT_EVENT:
            return t, y, True
        if how != "apex":
            raise RuntimeError(f"the pre-ignition coast ended by {how!r} (planner bug)")
        alt = float(self.model.altitude(y))
        raise GuidanceFailure(
            "no_ignition",
            f"the coast after release reached its apex at {alt:.9g} m (t = {t:.6g} s), "
            f"{ign_alt_m - alt:.6g} m below the ignition altitude {ign_alt_m:.9g} m of "
            "height_method: event: stage 1 never lights",
        )

    def _fly_kick_turn(
        self,
        tr: TraceBuilder,
        delta_rad: float,
        t: float,
        y: np.ndarray,
        schedule: ThrustSchedule,
    ) -> tuple[str, float, np.ndarray, dict[str, float]]:
        """KICK then GRAVITY_TURN from the kick trigger at t [s] to MECO (see
        ``from_kick``). Returns (how, t, y, kick_info), how in {"meco", "impact"};
        kick_info holds t_kick_s, kick_duration_s and kick_steering_loss_mps (the
        steering loss booked inside KICK). Raises GuidanceFailure("kick_timeout")."""
        t_kick = t
        j_steer0 = float(PLANAR_LAYOUT.get(y, "J_steer_mps"))
        extra = (
            ev_kick_aligned(delta_rad, self.env.omega_p_rads),
            ev_time(t_kick + self.guidance.kick_max_s, "kick_timeout"),
        )
        ended, t, y = self._burn(tr, KICK, 0, schedule, FixedTilt(delta_rad), extra, t, y)
        info = {
            "t_kick_s": t_kick,
            "kick_duration_s": t - t_kick,
            "kick_steering_loss_mps": float(PLANAR_LAYOUT.get(y, "J_steer_mps")) - j_steer0,
        }
        if ended == "kick_timeout":
            raise GuidanceFailure(
                "kick_timeout",
                f"the velocity did not align with the kick (delta = {delta_rad:.6g} rad) "
                f"within {self.guidance.kick_max_s:.6g} s",
            )
        if ended == "impact":
            tr.status = "impact"
            return "impact", t, y, info
        if ended == "kick_end":
            ended, t, y = self._burn(tr, GRAVITY_TURN, 0, schedule, AlongVrel(), (), t, y)
            if ended == "impact":
                tr.status = "impact"
                return "impact", t, y, info
        return "meco", t, y, info

    def _meco_record(
        self, tr: TraceBuilder, t: float, y: np.ndarray, kick_info: Mapping[str, float]
    ) -> dict[str, float]:
        """Record stage 1's burnout (tr.burnouts) and return the MECO record."""
        tr.burnouts[self.vehicle.stages[0].name] = (t, y.copy())
        row = tr.view.row(t, y, tr.phases[-1].spec.kind)
        meco = {"t_s": t, **row}
        meco.update({n: float(PLANAR_LAYOUT.get(y, n)) for n in _J_NAMES})
        meco.update(kick_info)
        return meco

    def _stage_and_coast(
        self, tr: TraceBuilder, t: float, y: np.ndarray
    ) -> tuple[str, float, np.ndarray, bool]:
        """The staging map at MECO (t [s], y) and the staging coast up to stage 2's
        ignition. The fairing drops with stage 1 under rule ``staging``, or under the
        heating rule when 0.5 rho V^3 is already below its limit at staging (logged as
        ``fairing`` with a flag); otherwise it stays on (rule never, or the heating
        criterion not yet met: build step 22 drops it in the stage-2 burn).
        COAST_STAGING runs for stage 2's coast_before_ignition_s, then COAST_PRE_IGN up
        to t_ign_s after it; both split at the radial apex. Returns (how, t, y,
        fairing_on), how in {"ignition", "impact"}."""
        rule = self.vehicle.fairing_rule
        drop = rule.trigger == "staging"
        heating_met = False
        if rule.limit_W_m2 is not None:
            heating_met = fmh_rate_W_m2(y, self.env) < rule.limit_W_m2
            drop = heating_met
        y = map_staging_planar(y, self.vehicle, 0, drop)
        tr.add_event("staging", t, COAST_STAGING, 1, y)
        if heating_met:
            tr.add_event("fairing", t, COAST_STAGING, 1, y)
            tr.flags.append(
                f"fairing: the heating criterion 0.5 rho V^3 < {rule.limit_W_m2:.6g} W/m^2 is "
                f"already met at staging (t = {t:.6g} s); the fairing drops with stage 1"
            )
        fairing_on = self.vehicle.fairing_mass_kg > 0.0 and not drop
        stage2 = self.vehicle.stages[1]
        t_coast_end = t + stage2.coast_before_ignition_s
        t, y, how = self._coast(tr, COAST_STAGING, 1, t, t_coast_end, y)
        if how == "impact":
            return "impact", t, y, fairing_on
        t_ign2 = t_coast_end + self.ignition[stage2.name].t_ign_s
        if t_ign2 > t + ZERO_SPAN_S:
            t, y, how = self._coast(tr, COAST_PRE_IGN, 1, t, t_ign2, y)
            if how == "impact":
                return "impact", t, y, fairing_on
        return "ignition", t, y, fairing_on

    def _fail_ignition(self, tr: TraceBuilder, k: int, t: float, y: np.ndarray) -> None:
        """Record that stage k's ignition failed at t [s] (state y): tr.failed_stage,
        tr.t_fail_s and the ``ignition_failed`` event in the terminal COAST."""
        tr.failed_stage = self.vehicle.stages[k].name
        tr.t_fail_s = t
        tr.add_event("ignition_failed", t, COAST, k, y)

    def _terminal_coast(self, tr: TraceBuilder, k: int, t: float, y: np.ndarray) -> None:
        """The unpowered COAST after a failed ignition of stage k, or after stage 2
        burned out short of orbit, for end apex (stop at the radial apex; a vehicle
        already falling stops at once with a flag) or impact (to the apex, then to the
        ground: status impact); an ``end`` event closes the run."""
        if self.end not in ("apex", "impact"):
            raise ValueError(f"a failed ignition needs end apex or impact, got {self.end!r}")
        if self.end == "apex":
            if not self._rising(t, y, self._unpowered(), None):
                tr.flags.append("end apex: the vehicle was already falling when the coast began")
                tr.add_event("end", t, COAST, k, y)
                return
            t, y, _how = self._coast(tr, COAST, k, t, None, y, stop_at_apex=True)
            tr.add_event("end", t, COAST, k, y)
            return
        t, y, _how = self._coast(tr, COAST, k, t, None, y)
        tr.add_event("end", t, COAST, k, y)
