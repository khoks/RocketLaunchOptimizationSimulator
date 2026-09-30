"""Stages, engines, thrust startup, mass bookkeeping and the ideal-rocket-equation screening.

Everything here is SI and pure: no I/O, no globals. Time arguments are absolute run time
(t = 0 at push start on a track or at hold-down release on a pad); ignition times are
absolute as well. Frames do not enter: thrust magnitudes are scalars and the caller
decides the direction.

Startup shapes (f is the thrust fraction, dt = t - t_ign):
    step:  f = 1[dt >= 0]
    ramp:  f = clip(dt / t_ramp, 0, 1)
    lag:   f = 1 - exp(-dt / tau)      for dt >= 0, else 0
A ramp with t_ramp = 0 or a lag with tau = 0 is a step.

Aerodynamics (docs/physics.md, "Atmosphere, drag and back-pressure in flight"): a
``CdTable`` is C_D versus Mach, a C1 monotone piecewise cubic (PCHIP) through the knots
whose coefficients are computed once by scipy and evaluated in pure Python (bisect plus
Horner), held at the end values outside the knots. A ``DragModel`` combines the table
with the reference area and a ``cd_scale`` sensitivity knob; drag acts along -v_rel,
the velocity relative to the co-rotating air. ``FairingDrop`` says when the payload
fairing separates. The 1-D model uses none of the aerodynamics.
"""

from __future__ import annotations

import bisect
import dataclasses
import itertools
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal, get_args

from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq

from launchsim.constants import G0_MPS2

StartupKind = Literal["step", "ramp", "lag"]
FairingDropKind = Literal["staging", "never"]
"""The Phase 1 fairing rules, which ``Vehicle.fairing_drop`` stores as plain strings."""
FairingTrigger = Literal["staging", "never", "free_molecular_heating"]
FAIRING_TRIGGERS: tuple[str, ...] = get_args(FairingTrigger)
HEATING_TRIGGER: FairingTrigger = "free_molecular_heating"
CD_POLY_TERMS = 4
"""Coefficients per PCHIP interval: (c3, c2, c1, c0) of a cubic in M - M_i."""

# Root-finder settings for the ideal screening (solver tolerances, not physics).
_BRENTQ_XTOL_KG = 1e-12
_BRENTQ_RTOL = 1e-15
_BRENTQ_MAXITER = 500
_BRACKET_GROWTH = 2.0
"""Factor by which the upper bracket grows until it encloses the root."""
_BRACKET_DOUBLINGS = 64
"""Bracket expansions tried before giving up."""
_PAYLOAD_BRACKET_MIN_KG = 1.0
"""First upper bracket for the payload root when the vehicle carries no payload."""
_MIN_PROPELLANT_FRACTION = 1e-9
"""Lower bracket for the stage-1 propellant root, as a fraction of the nominal load."""


@dataclass(frozen=True)
class Startup:
    """Thrust startup shape of an engine set.

    kind: "step", "ramp" (linear over t_ramp_s) or "lag" (first order, time constant tau_s).
    Times in seconds; a zero duration degenerates to a step, negative durations raise.
    """

    kind: StartupKind = "step"
    t_ramp_s: float = 0.0
    tau_s: float = 0.0

    def __post_init__(self) -> None:
        if self.kind not in ("step", "ramp", "lag"):
            raise ValueError(f"unknown startup kind {self.kind!r}")
        if self.t_ramp_s < 0.0 or self.tau_s < 0.0:
            raise ValueError("startup durations must be >= 0 s")

    @property
    def effective_kind(self) -> StartupKind:
        """The kind after collapsing zero-duration ramps and lags to a step."""
        if self.kind == "ramp" and self.t_ramp_s == 0.0:
            return "step"
        if self.kind == "lag" and self.tau_s == 0.0:
            return "step"
        return self.kind

    @property
    def full_thrust_delay_s(self) -> float:
        """Time [s] after ignition at which the ramp reaches full thrust (0 for step and lag)."""
        return self.t_ramp_s if self.effective_kind == "ramp" else 0.0


def thrust_fraction(startup: Startup, dt: float) -> float:
    """Thrust fraction f in [0, 1] at dt seconds after ignition (dt < 0 gives 0).

    Inputs: startup shape; dt [s]. Output: dimensionless.
    """
    if dt < 0.0:
        return 0.0
    kind = startup.effective_kind
    if kind == "step":
        return 1.0
    if kind == "ramp":
        return min(dt / startup.t_ramp_s, 1.0)
    return -math.expm1(-dt / startup.tau_s)  # 1 - exp(-x) without cancellation at small x


def startup_deficit_s(startup: Startup, t_ign: float) -> float:
    """Post-release full-thrust seconds lost to the startup: integral over t >= 0 of (1 - f).

    Inputs: startup shape; t_ign [s], ignition time relative to release (negative when lit
    before release). Output: seconds of full thrust missing after release. For a ramp the
    integral is finite; for a lag it is the exact integral to infinity, which is the
    asymptote of the loss for a burn much longer than tau.
    """
    kind = startup.effective_kind
    if kind == "step":
        return max(t_ign, 0.0)
    if kind == "ramp":
        t_r = startup.t_ramp_s
        if t_ign >= 0.0:
            return t_ign + 0.5 * t_r
        if t_ign > -t_r:
            return (t_r + t_ign) ** 2 / (2.0 * t_r)
        return 0.0
    tau = startup.tau_s
    if t_ign >= 0.0:
        return t_ign + tau
    return tau * math.exp(t_ign / tau)


@dataclass(frozen=True)
class Engine:
    """One engine: vacuum thrust [N], vacuum Isp [s], nozzle exit area [m^2]."""

    thrust_vac_N: float
    isp_vac_s: float
    exit_area_m2: float = 0.0

    def __post_init__(self) -> None:
        if self.thrust_vac_N <= 0.0 or self.isp_vac_s <= 0.0 or self.exit_area_m2 < 0.0:
            raise ValueError("engine needs thrust > 0, Isp > 0 and exit area >= 0")

    @property
    def c_mps(self) -> float:
        """Effective exhaust velocity c = g0 * Isp_vac [m/s]."""
        return G0_MPS2 * self.isp_vac_s

    @property
    def mdot_full_kgps(self) -> float:
        """Mass flow at full vacuum thrust [kg/s]."""
        return self.thrust_vac_N / self.c_mps


@dataclass(frozen=True)
class Stage:
    """One stage: masses [kg], engine, engine count, startup shape and the coast [s]
    between the previous stage's separation and this stage's ignition."""

    name: str
    dry_mass_kg: float
    propellant_mass_kg: float
    engine: Engine
    n_engines: int = 1
    startup: Startup = Startup()
    coast_before_ignition_s: float = 0.0

    def __post_init__(self) -> None:
        if self.dry_mass_kg < 0.0 or self.propellant_mass_kg <= 0.0:
            raise ValueError("stage needs dry mass >= 0 and propellant > 0")
        if self.n_engines < 1 or self.coast_before_ignition_s < 0.0:
            raise ValueError("stage needs n_engines >= 1 and coast >= 0 s")

    @property
    def thrust_vac_total_N(self) -> float:
        """Total vacuum thrust of all engines [N]."""
        return self.n_engines * self.engine.thrust_vac_N

    @property
    def mdot_full_kgps(self) -> float:
        """Total mass flow at full thrust [kg/s]."""
        return self.n_engines * self.engine.mdot_full_kgps

    @property
    def exit_area_total_m2(self) -> float:
        """Total nozzle exit area [m^2]."""
        return self.n_engines * self.engine.exit_area_m2

    @property
    def c_mps(self) -> float:
        """Effective exhaust velocity [m/s]."""
        return self.engine.c_mps

    @property
    def burn_time_s(self) -> float:
        """Full-thrust burn time of the whole propellant load [s]."""
        return self.propellant_mass_kg / self.mdot_full_kgps

    @property
    def wet_mass_kg(self) -> float:
        """Dry plus propellant mass [kg]."""
        return self.dry_mass_kg + self.propellant_mass_kg

    def schedule(
        self, t_ign_abs_s: float, startup: Startup | None = None, fails: bool = False
    ) -> ThrustSchedule:
        """Thrust schedule for this stage lit at absolute time t_ign_abs_s [s].

        startup overrides the stage's own shape; fails makes the schedule identically zero.
        """
        return ThrustSchedule(
            thrust_vac_total_N=self.thrust_vac_total_N,
            c_mps=self.c_mps,
            exit_area_total_m2=self.exit_area_total_m2,
            t_ign_abs_s=t_ign_abs_s,
            startup=self.startup if startup is None else startup,
            fails=fails,
        )


@dataclass(frozen=True)
class ThrustSchedule:
    """Thrust versus absolute time for one stage's engine set.

    thrust_vac_total_N and exit_area_total_m2 are totals over the engines; c_mps is the
    exhaust velocity; t_ign_abs_s is the ignition time on the run clock. The schedule does
    not know about propellant depletion: the phase engine stops it at burnout. With fails
    the thrust is identically zero.
    """

    thrust_vac_total_N: float
    c_mps: float
    exit_area_total_m2: float
    t_ign_abs_s: float
    startup: Startup = Startup()
    fails: bool = False

    @property
    def mdot_full_kgps(self) -> float:
        """Mass flow at full thrust [kg/s]."""
        return self.thrust_vac_total_N / self.c_mps

    def thrust_vac_N(self, t: float) -> float:
        """Vacuum thrust [N] at absolute time t [s]: T_full * f(t - t_ign)."""
        if self.fails:
            return 0.0
        return self.thrust_vac_total_N * thrust_fraction(self.startup, t - self.t_ign_abs_s)

    def mass_flow_kgps(self, t: float) -> float:
        """Propellant mass flow [kg/s] at absolute time t [s]; follows the vacuum thrust."""
        return self.thrust_vac_N(t) / self.c_mps

    def thrust_N(self, t: float, p_amb_pa: float) -> float:
        """Delivered thrust [N] at ambient pressure p_amb_pa [Pa]: max(0, T_vac - p_amb A_e)."""
        return max(0.0, self.thrust_vac_N(t) - p_amb_pa * self.exit_area_total_m2)

    def kink_times(self) -> tuple[float, ...]:
        """Absolute times [s] where the thrust curve has a kink (phase boundaries).

        Step and lag: ignition. Ramp: ignition and the end of the ramp. Failed: none.
        """
        if self.fails:
            return ()
        t0 = self.t_ign_abs_s
        if self.startup.effective_kind == "ramp":
            return (t0, t0 + self.startup.t_ramp_s)
        return (t0,)


def propellant_burned_kg(schedule: ThrustSchedule, t: float) -> float:
    """Propellant burned [kg] from ignition to absolute time t [s], in closed form.

    step: mdot dt; ramp: mdot dt^2 / (2 t_ramp) up to t_ramp, then mdot (dt - t_ramp/2);
    lag: mdot (dt - tau (1 - exp(-dt/tau))). Zero before ignition and always when the
    schedule fails. Not capped by the propellant on board.
    """
    if schedule.fails:
        return 0.0
    dt = t - schedule.t_ign_abs_s
    if dt <= 0.0:
        return 0.0
    mdot = schedule.mdot_full_kgps
    kind = schedule.startup.effective_kind
    if kind == "step":
        return mdot * dt
    if kind == "ramp":
        t_r = schedule.startup.t_ramp_s
        if dt <= t_r:
            return mdot * dt * dt / (2.0 * t_r)
        return mdot * (dt - 0.5 * t_r)
    tau = schedule.startup.tau_s
    # dt - tau (1 - exp(-dt/tau)) via expm1: the plain form cancels to a negative mass
    # just after ignition; the clamp covers denormal dt where even expm1 underflows.
    return max(0.0, mdot * (dt + tau * math.expm1(-dt / tau)))


def _finite(values: Sequence[float]) -> bool:
    """True when every entry is a finite real number."""
    return all(math.isfinite(v) for v in values)


def _float_tuple(values: Sequence[float], what: str) -> tuple[float, ...]:
    """The entries of values as a tuple of floats; TypeError for a non-number or a bool."""
    if any(isinstance(v, bool) or not isinstance(v, int | float) for v in values):
        raise TypeError(f"{what} entries must be numbers")
    return tuple(float(v) for v in values)


def _check_knots(mach: Sequence[float], cd: Sequence[float]) -> None:
    """Raise ValueError unless (mach, cd) are valid C_D table knots (see CdTable)."""
    if len(mach) < 2 or len(cd) != len(mach):
        raise ValueError("a C_D table needs >= 2 knots and one C_D per knot")
    if not (_finite(mach) and _finite(cd)):
        raise ValueError("C_D table knots must be finite")
    if mach[0] < 0.0 or any(b <= a for a, b in itertools.pairwise(mach)):
        raise ValueError("C_D table Mach knots must start at >= 0 and strictly increase")
    if any(c < 0.0 for c in cd):
        raise ValueError("C_D table values must be >= 0")


@dataclass(frozen=True)
class CdTable:
    """Drag coefficient C_D versus Mach number M (both dimensionless): a C1 piecewise cubic.

    mach: knot Mach numbers, strictly increasing, the first >= 0, at least two.
    cd: C_D at the knots (finite, >= 0).
    coeffs: for interval i, [mach[i], mach[i+1]], the cubic's coefficients (c3, c2, c1,
    c0) in dM = M - mach[i], so that C_D = ((c3 dM + c2) dM + c1) dM + c0 with c0 =
    cd[i] exactly. ``CdTable.pchip`` builds them; a hand-built table must satisfy the
    same shape rules (checked here), and its smoothness is the caller's responsibility.
    Any sequences of numbers are accepted and stored as tuples of floats, so every table
    is immutable and hashable.

    Calling the table evaluates it: bisect finds the interval and Horner's rule the
    cubic. Outside [mach[0], mach[-1]] the end values are held (C_D constant), so the
    curve is C0 at the end knots and C1 inside. Frame-free (a scalar coefficient).
    """

    mach: tuple[float, ...]
    cd: tuple[float, ...]
    coeffs: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "mach", _float_tuple(self.mach, "C_D table Mach"))
        object.__setattr__(self, "cd", _float_tuple(self.cd, "C_D table C_D"))
        coeffs = tuple(_float_tuple(poly, "C_D cubic") for poly in self.coeffs)
        object.__setattr__(self, "coeffs", coeffs)
        _check_knots(self.mach, self.cd)
        if len(self.coeffs) != len(self.mach) - 1:
            raise ValueError("a C_D table needs one cubic per interval (n - 1 for n knots)")
        for i, poly in enumerate(self.coeffs):
            if len(poly) != CD_POLY_TERMS or not _finite(poly):
                raise ValueError(f"C_D cubic {i} needs {CD_POLY_TERMS} finite coefficients")
            if poly[-1] != self.cd[i]:
                raise ValueError(f"C_D cubic {i} does not start at its knot value")

    @classmethod
    def pchip(cls, mach: Sequence[float], cd: Sequence[float]) -> CdTable:
        """PCHIP table through (mach, cd): scipy's PchipInterpolator coefficients, frozen.

        Inputs: knot Mach numbers (strictly increasing, >= 0) and C_D values (>= 0),
        dimensionless. Output: a CdTable whose cubics are scipy's (weighted harmonic-mean
        slopes at interior knots, zero at a local extremum; the three-point
        shape-preserving rule at the two ends), so the curve is C1, passes through every
        knot and does not overshoot between them.
        """
        m = tuple(float(x) for x in mach)
        c = tuple(float(x) for x in cd)
        _check_knots(m, c)
        poly = PchipInterpolator(m, c).c
        coeffs = tuple(
            tuple(float(poly[k, i]) for k in range(CD_POLY_TERMS)) for i in range(len(m) - 1)
        )
        return cls(mach=m, cd=c, coeffs=coeffs)

    def __call__(self, mach: float) -> float:
        """C_D (dimensionless) at Mach number mach (dimensionless); end values held.

        Pure Python (bisect plus Horner), about 0.3 us per call, for use inside an ODE
        right-hand side. A NaN Mach number gives NaN.
        """
        knots = self.mach
        if mach <= knots[0]:
            return self.cd[0]
        if mach >= knots[-1]:
            return self.cd[-1]
        i = min(bisect.bisect_right(knots, mach) - 1, len(knots) - 2)
        dm = mach - knots[i]
        c3, c2, c1, c0 = self.coeffs[i]
        return ((c3 * dm + c2) * dm + c1) * dm + c0


@dataclass(frozen=True)
class DragModel:
    """Aerodynamic drag of the whole stack: D = q cd_scale C_D(M) A_ref, along -v_rel.

    table: C_D(M) (power-on, base drag included); reference_area_m2: A_ref [m^2], the
    area the table is normalised by (finite, > 0); cd_scale: dimensionless multiplier on
    every C_D (finite, > 0; 1 nominal; the sensitivity knob). q = 0.5 rho V^2 [Pa] and
    M = V / a use the speed V relative to the co-rotating atmosphere. No lift and no
    angle-of-attack dependence: the force is pure drag. One A_ref applies to every stage.
    """

    table: CdTable
    reference_area_m2: float
    cd_scale: float = 1.0

    def __post_init__(self) -> None:
        if not (math.isfinite(self.reference_area_m2) and self.reference_area_m2 > 0.0):
            raise ValueError("drag reference area must be finite and > 0 m^2")
        if not (math.isfinite(self.cd_scale) and self.cd_scale > 0.0):
            raise ValueError("cd_scale must be finite and > 0")

    def cd(self, mach: float) -> float:
        """Scaled drag coefficient cd_scale * C_D(mach) (dimensionless) at Mach mach."""
        return self.cd_scale * self.table(mach)

    def force_N(self, q_pa: float, mach: float) -> float:
        """Drag magnitude [N] at dynamic pressure q_pa [Pa] and Mach number mach
        (dimensionless): q * cd_scale * C_D(M) * A_ref. Frame-free; the caller points it
        along -v_rel."""
        return q_pa * self.cd(mach) * self.reference_area_m2

    def components_N(
        self, rho_kgm3: float, a_mps: float, w_mps: float, u_mps: float
    ) -> tuple[float, float]:
        """Drag vector [N] in the local (radial, horizontal) frame of the planar ascent.

        Inputs: air density rho [kg/m^3] and speed of sound a [m/s] at the vehicle; the
        Earth-relative velocity components w = v_r (radial, up) and u = v_theta -
        omega_p r (horizontal, downrange) [m/s]. Output: (D_r, D_theta) [N] =
        -0.5 rho V cd_scale C_D(V/a) A_ref (w, u) with V = hypot(w, u): magnitude
        0.5 rho V^2 cd_scale C_D A_ref along -v_rel. Written without dividing by V, so
        V = 0 gives exactly (0, 0).
        """
        speed = math.hypot(w_mps, u_mps)
        k = 0.5 * rho_kgm3 * speed * self.cd(speed / a_mps) * self.reference_area_m2
        return -k * w_mps, -k * u_mps


@dataclass(frozen=True)
class FairingDrop:
    """When the payload fairing separates.

    trigger: "staging" (with stage 1, in the staging map), "never" (carried to the end)
    or "free_molecular_heating" (the planar stage-2 burn drops it at the first instant
    the free-molecular heating rate 0.5 rho V^3 [W/m^2], with V the speed relative to
    the co-rotating air, falls below limit_W_m2). limit_W_m2: the heating limit [W/m^2],
    finite and > 0 for the heating trigger, None for the other two. The ideal screening
    treats the heating trigger as a drop at staging.
    """

    trigger: FairingTrigger = "staging"
    limit_W_m2: float | None = None

    def __post_init__(self) -> None:
        if self.trigger not in FAIRING_TRIGGERS:
            raise ValueError(f"unknown fairing trigger {self.trigger!r}")
        if self.trigger == HEATING_TRIGGER:
            limit = self.limit_W_m2
            if limit is None or not (math.isfinite(limit) and limit > 0.0):
                raise ValueError("the heating fairing trigger needs a finite limit_W_m2 > 0")
        elif self.limit_W_m2 is not None:
            raise ValueError(f"fairing trigger {self.trigger!r} takes no limit_W_m2")

    @property
    def drops_at_staging_in_screening(self) -> bool:
        """True when the ideal screening drops the fairing with stage 1 (every trigger but
        never; the heating trigger counts as a drop at staging there)."""
        return self.trigger != "never"


@dataclass(frozen=True)
class Vehicle:
    """A stack of stages (index 0 lit first), fairing and payload masses [kg], the fairing
    drop rule, the per-stage effective Isp [s] used only by the ideal screening, and the
    aerodynamics (None: no drag model; the 1-D model ignores it either way).

    fairing_drop keeps the Phase 1 string shim: "staging" and "never" are stored as
    those strings (a FairingDrop with either trigger is normalised to its string, so the
    1-D code that compares ``fairing_drop == "staging"`` keeps working), and only the
    heating rule is stored as a FairingDrop. ``fairing_rule`` always returns a
    FairingDrop.
    """

    stages: tuple[Stage, ...]
    fairing_mass_kg: float = 0.0
    payload_mass_kg: float = 0.0
    fairing_drop: FairingDropKind | FairingDrop = "staging"
    screening_isp_s: tuple[float, ...] = ()
    aero: DragModel | None = None

    def __post_init__(self) -> None:
        if not self.stages:
            raise ValueError("a vehicle needs at least one stage")
        if self.fairing_mass_kg < 0.0 or self.payload_mass_kg < 0.0:
            raise ValueError("fairing and payload masses must be >= 0")
        if isinstance(self.fairing_drop, FairingDrop):
            if self.fairing_drop.trigger != HEATING_TRIGGER:
                object.__setattr__(self, "fairing_drop", self.fairing_drop.trigger)
        elif self.fairing_drop not in get_args(FairingDropKind):
            raise ValueError(f"unknown fairing_drop {self.fairing_drop!r}")
        if self.aero is not None and not isinstance(self.aero, DragModel):
            raise ValueError("aero must be a DragModel or None")
        names = [s.name for s in self.stages]
        if len(set(names)) != len(names):
            raise ValueError("stage names must be unique")
        if self.screening_isp_s and len(self.screening_isp_s) != len(self.stages):
            raise ValueError("screening_isp_s needs one entry per stage")
        if any(isp <= 0.0 for isp in self.screening_isp_s):
            raise ValueError("screening_isp_s entries must be > 0 s")

    @property
    def n_stages(self) -> int:
        """Number of stages."""
        return len(self.stages)

    @property
    def stage_names(self) -> tuple[str, ...]:
        """Stage names in firing order."""
        return tuple(s.name for s in self.stages)

    def stage_index(self, name: str) -> int:
        """Index of the stage called name; raises KeyError if absent."""
        for i, stage in enumerate(self.stages):
            if stage.name == name:
                return i
        raise KeyError(f"no stage named {name!r}; stages are {self.stage_names}")

    @property
    def fairing_rule(self) -> FairingDrop:
        """The fairing drop rule as a FairingDrop (the stored string or the heating rule)."""
        if isinstance(self.fairing_drop, FairingDrop):
            return self.fairing_drop
        return FairingDrop(trigger=self.fairing_drop)

    def fairing_carried_kg(self, i: int) -> float:
        """Fairing mass [kg] still attached at ignition of stage i, as the ideal screening
        counts it: always on stage 0; on later stages only when the rule is never (the
        heating rule counts as a drop at staging here; the planar model drops it at the
        heating event and keeps its own bookkeeping)."""
        if not self.fairing_rule.drops_at_staging_in_screening or i == 0:
            return self.fairing_mass_kg
        return 0.0

    def stack_mass_kg(self, i: int) -> float:
        """Mass [kg] at ignition of stage i: stages i.. fully fuelled, payload, and the
        fairing if not yet dropped.

        Screening semantics (see fairing_carried_kg): under the heating rule the fairing
        is left out from stage 1 on, although the planar ascent still carries it then.
        Trajectory mass bookkeeping must not use this helper or the two built on it.
        """
        self._check_index(i)
        above = sum(s.wet_mass_kg for s in self.stages[i:])
        return above + self.payload_mass_kg + self.fairing_carried_kg(i)

    def stack_dry_mass_kg(self, i: int) -> float:
        """Mass [kg] at burnout of stage i: stack_mass_kg(i) minus stage i's propellant."""
        return self.stack_mass_kg(i) - self.stages[i].propellant_mass_kg

    def mass_after_staging_kg(self, i: int) -> float:
        """Mass [kg] after stage i separates: its burnout mass minus its dry mass and, when
        the fairing drops at staging (the heating rule counts, as in fairing_carried_kg)
        and i == 0, minus the fairing."""
        drops = self.fairing_rule.drops_at_staging_in_screening and i == 0
        fairing = self.fairing_mass_kg if drops else 0.0
        return self.stack_dry_mass_kg(i) - self.stages[i].dry_mass_kg - fairing

    def liftoff_mass_kg(self) -> float:
        """Total mass [kg] at liftoff."""
        return self.stack_mass_kg(0)

    def _check_index(self, i: int) -> None:
        if not 0 <= i < len(self.stages):
            raise IndexError(f"stage index {i} out of range for {len(self.stages)} stages")


def with_payload(vehicle: Vehicle, payload_kg: float) -> Vehicle:
    """Copy of vehicle with a different payload mass [kg]; everything else, the
    aerodynamics included, is kept."""
    return dataclasses.replace(vehicle, payload_mass_kg=payload_kg)


def with_cd_scale(vehicle: Vehicle, cd_scale: float) -> Vehicle:
    """Copy of vehicle whose drag model has cd_scale (dimensionless, > 0) instead of its
    own; the C_D table and A_ref are kept. Raises ValueError when the vehicle has no
    drag model (aero None)."""
    if vehicle.aero is None:
        raise ValueError("the vehicle has no drag model (aero is None); cd_scale needs one")
    return dataclasses.replace(vehicle, aero=dataclasses.replace(vehicle.aero, cd_scale=cd_scale))


def with_stage_propellant(vehicle: Vehicle, i: int, propellant_kg: float) -> Vehicle:
    """Copy of vehicle with stage i carrying propellant_kg [kg] of propellant."""
    stages = list(vehicle.stages)
    stages[i] = dataclasses.replace(stages[i], propellant_mass_kg=propellant_kg)
    return dataclasses.replace(vehicle, stages=tuple(stages))


def ideal_dv_mps(vehicle: Vehicle, payload_kg: float | None = None) -> float:
    """Ideal rocket-equation delta-v [m/s]: sum over stages of g0 Isp_eff ln(m_ign/m_bo).

    Uses vehicle.screening_isp_s (effective, loss-averaged Isp per stage) and the
    vehicle's staging and fairing rules. payload_kg overrides the vehicle's payload.
    Losses are not modelled; this is a screening yardstick, not a trajectory result.
    """
    if not vehicle.screening_isp_s:
        raise ValueError("vehicle has no screening_isp_s; the ideal screening needs it")
    v = vehicle if payload_kg is None else with_payload(vehicle, payload_kg)
    return sum(
        G0_MPS2 * isp * math.log(v.stack_mass_kg(i) / v.stack_dry_mass_kg(i))
        for i, isp in enumerate(v.screening_isp_s)
    )


def _solve_increasing(f: Callable[[float], float], lo: float, hi0: float) -> float:
    """Root of f on [lo, hi] with f(lo) <= 0, expanding hi until f(hi) > 0."""
    hi = hi0
    for _ in range(_BRACKET_DOUBLINGS):
        if f(hi) > 0.0:
            return _brentq(f, lo, hi)
        hi *= _BRACKET_GROWTH
    raise ValueError("could not bracket the screening root")


def _brentq(f: Callable[[float], float], lo: float, hi: float) -> float:
    """brentq with the screening tolerances."""
    return float(
        brentq(f, lo, hi, xtol=_BRENTQ_XTOL_KG, rtol=_BRENTQ_RTOL, maxiter=_BRENTQ_MAXITER)
    )


def payload_gain_kg(vehicle: Vehicle, v_assist_mps: float) -> float:
    """Extra payload [kg] the ideal screening allows when the ground supplies v_assist_mps
    [m/s]: the payload at which the ideal delta-v drops by exactly v_assist, minus the
    vehicle's payload. Found by brentq on the monotone delta-v(payload)."""
    if v_assist_mps < 0.0:
        raise ValueError("v_assist_mps must be >= 0")
    if v_assist_mps == 0.0:
        return 0.0
    target = ideal_dv_mps(vehicle) - v_assist_mps
    p0 = vehicle.payload_mass_kg
    hi0 = max(_BRACKET_GROWTH * p0, _PAYLOAD_BRACKET_MIN_KG)
    root = _solve_increasing(lambda p: target - ideal_dv_mps(vehicle, p), p0, hi0)
    return root - p0


def stage1_propellant_saved_kg(vehicle: Vehicle, v_assist_mps: float) -> float:
    """Stage-1 propellant [kg] that can be offloaded at fixed payload when the ground
    supplies v_assist_mps [m/s], per the ideal screening (brentq on propellant)."""
    if v_assist_mps < 0.0:
        raise ValueError("v_assist_mps must be >= 0")
    if v_assist_mps == 0.0:
        return 0.0
    target = ideal_dv_mps(vehicle) - v_assist_mps
    m_p0 = vehicle.stages[0].propellant_mass_kg

    def f(m_p: float) -> float:
        return ideal_dv_mps(with_stage_propellant(vehicle, 0, m_p)) - target

    tiny = _MIN_PROPELLANT_FRACTION * m_p0
    if f(tiny) > 0.0:
        raise ValueError("v_assist exceeds the whole stage-1 delta-v")
    return m_p0 - _brentq(f, tiny, m_p0)


def payload_per_mps_kg(vehicle: Vehicle, v_assist_mps: float) -> float:
    """Average payload gain per m/s of assist [kg per m/s] at v_assist_mps [m/s] (> 0)."""
    if v_assist_mps <= 0.0:
        raise ValueError("v_assist_mps must be > 0")
    return payload_gain_kg(vehicle, v_assist_mps) / v_assist_mps
