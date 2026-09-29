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
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from scipy.optimize import brentq

from launchsim.constants import G0_MPS2

StartupKind = Literal["step", "ramp", "lag"]
FairingDrop = Literal["staging", "never"]

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


@dataclass(frozen=True)
class Vehicle:
    """A stack of stages (index 0 lit first), fairing and payload masses [kg], the fairing
    drop rule, and the per-stage effective Isp [s] used only by the ideal screening."""

    stages: tuple[Stage, ...]
    fairing_mass_kg: float = 0.0
    payload_mass_kg: float = 0.0
    fairing_drop: FairingDrop = "staging"
    screening_isp_s: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        if not self.stages:
            raise ValueError("a vehicle needs at least one stage")
        if self.fairing_mass_kg < 0.0 or self.payload_mass_kg < 0.0:
            raise ValueError("fairing and payload masses must be >= 0")
        if self.fairing_drop not in ("staging", "never"):
            raise ValueError(f"unknown fairing_drop {self.fairing_drop!r}")
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

    def fairing_carried_kg(self, i: int) -> float:
        """Fairing mass [kg] still attached while stage i burns."""
        if self.fairing_drop == "never" or i == 0:
            return self.fairing_mass_kg
        return 0.0

    def stack_mass_kg(self, i: int) -> float:
        """Mass [kg] at ignition of stage i: stages i.. fully fuelled, payload, and the
        fairing if not yet dropped."""
        self._check_index(i)
        above = sum(s.wet_mass_kg for s in self.stages[i:])
        return above + self.payload_mass_kg + self.fairing_carried_kg(i)

    def stack_dry_mass_kg(self, i: int) -> float:
        """Mass [kg] at burnout of stage i: stack_mass_kg(i) minus stage i's propellant."""
        return self.stack_mass_kg(i) - self.stages[i].propellant_mass_kg

    def mass_after_staging_kg(self, i: int) -> float:
        """Mass [kg] after stage i separates: its burnout mass minus its dry mass and, when
        the fairing drops at staging and i == 0, minus the fairing."""
        fairing = self.fairing_mass_kg if (self.fairing_drop == "staging" and i == 0) else 0.0
        return self.stack_dry_mass_kg(i) - self.stages[i].dry_mass_kg - fairing

    def liftoff_mass_kg(self) -> float:
        """Total mass [kg] at liftoff."""
        return self.stack_mass_kg(0)

    def _check_index(self, i: int) -> None:
        if not 0 <= i < len(self.stages):
            raise IndexError(f"stage index {i} out of range for {len(self.stages)} stages")


def with_payload(vehicle: Vehicle, payload_kg: float) -> Vehicle:
    """Copy of vehicle with a different payload mass [kg]."""
    return dataclasses.replace(vehicle, payload_mass_kg=payload_kg)


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
