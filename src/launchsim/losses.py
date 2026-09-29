"""Loss budgets and residuals (docs/physics.md, "Loss accounting" and "Ignition-after-
release loss").

Everything is SI and pure. The ascent budget is assembled from the loss quadrature
states the ODE carries (J_vac, J_grav, J_alt, J_bp, J_steer in ``VERTICAL_LAYOUT``),
summed over the free-flight phases from release onward, and checked against CLAUDE.md's
identity

    |v_rel,f| - |v_rel,0| = dv_vac - gravity - drag - steering - back_pressure

(drag = 0 in Phase 1; omega_p = 0 so v_rel = v). ``ignition_loss_analytic_mps`` is the
constant-gravity closed form of the speed lost by lighting the engines late or slowly,
against which the integrated runs are reported side by side.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.special import lambertw

from launchsim.dynamics import VERTICAL_LAYOUT, StateLayout
from launchsim.phases import PhaseResult
from launchsim.vehicle import Startup, startup_deficit_s

RESIDUAL_FLOOR_J = 1.0
"""Denominator floor [J] of ``AssistEnergyBudget.residual_rel`` (a push that does no
work has no relative scale)."""


@dataclass(frozen=True)
class LossBudget:
    """Speed budget of an ascent from release to its end, all in m/s.

    dv_vac: integral of T_vac/m dt from the flight start, c ln(m_flight_start/m_end)
    whenever the propellant is burned (the flight start is release, or the liftoff root
    of a hold extended past release; what burned before it is the ``before_flight``
    pair of ``sim.run_metrics``); gravity: integral of g sigma dt (negative while
    falling: speed regained);
    gravity_alt: the altitude part integral of (g - g_ref) sigma dt (<= 0 above the
    datum while rising), so ``gravity_duration`` = gravity - gravity_alt = g_ref times
    the signed flight time; drag: 0 in Phase 1; steering: integral of (T/m)(1 - cos psi)
    dt (2 T/m while thrusting against the velocity); back_pressure: integral of
    (T_vac - T)/m dt (0 while p_amb = 0); speed_start and speed_end: |v| at release and
    at the end. Frame: 1-D vertical, Earth-relative = inertial (omega_p = 0).
    """

    dv_vac: float
    gravity: float
    gravity_alt: float
    drag: float
    steering: float
    back_pressure: float
    speed_start: float
    speed_end: float

    @property
    def gravity_duration(self) -> float:
        """The duration part of the gravity loss [m/s]: gravity - gravity_alt = g_ref
        times the signed time of flight (rising counts +, falling -)."""
        return self.gravity - self.gravity_alt

    def residual_mps(self) -> float:
        """(speed_end - speed_start) - (dv_vac - gravity - drag - steering - back_pressure)
        [m/s]; ~1e-7 expected, < 0.01 required (CLAUDE.md), tests assert < 1e-6."""
        gained = self.speed_end - self.speed_start
        explained = self.dv_vac - self.gravity - self.drag - self.steering - self.back_pressure
        return gained - explained


@dataclass(frozen=True)
class AssistEnergyBudget:
    """Energy budget of a track push (CLAUDE.md assist identity), all in J.

    work_drive: integral of F_drive sdot dt; work_thrust: integral of T_sys sdot dt (the
    on-track thrust's work on the system, T_sys = (1 - f_imp) T); delta_mech: the
    change of 1/2 M sdot^2 + M g_eff z over the push (M = m_v + m_c, z the height above
    the track start); massflow_term: -integral of Mdot (1/2 sdot^2 + g_eff z) dt (the
    energy the expelled propellant takes with it; >= 0); dissipated: friction and
    damping (0 for the screening drive). Built by ``assist_energy_budget`` from the
    quadrature states of the ASSIST phases; the identity is work_drive + work_thrust =
    delta_mech + massflow_term + dissipated (docs/physics.md, "Assist energy
    identity").
    """

    work_drive: float
    work_thrust: float
    delta_mech: float
    massflow_term: float
    dissipated: float

    def residual_J(self) -> float:
        """work_drive + work_thrust - delta_mech - massflow_term - dissipated [J]."""
        supplied = self.work_drive + self.work_thrust
        return supplied - self.delta_mech - self.massflow_term - self.dissipated

    def residual_rel(self) -> float:
        """|lhs - rhs| / max(|lhs|, 1 J) with lhs the supplied work (work_drive +
        work_thrust) and rhs the explained energy; tests require < 1e-6."""
        lhs = self.work_drive + self.work_thrust
        return abs(self.residual_J()) / max(abs(lhs), RESIDUAL_FLOOR_J)


def assist_energy_budget(
    phases: Sequence[PhaseResult], layout: StateLayout, carriage_mass_kg: float, g_eff_mps2: float
) -> AssistEnergyBudget:
    """The AssistEnergyBudget of the ASSIST phases of a run (docs/physics.md, "Assist
    energy identity").

    Inputs: the ASSIST PhaseResults in time order, whose states (``layout``, the track
    layout) carry ``s_m``, ``sdot_mps``, ``m_kg`` and the quadratures ``E_drive_J``,
    ``W_thrust_J``, ``J_mass_J``; the carriage mass [kg] and the track g_eff [m/s^2]
    (the same values the phases integrated with); the phases' TrackParams supply the
    track geometry for z(s). Output: work_drive and work_thrust as the summed per-phase
    increments of E_drive and W_thrust, delta_mech = [M sdot^2/2 + M g_eff z(s)] from
    the first phase's start to the last phase's end, massflow_term = -(summed increment
    of J_mass), dissipated 0 (the screening drive dissipates nothing; a dissipative
    drive of Phase 3 must add its own quadrature). An empty sequence gives an all-zero
    budget.
    """
    if not phases:
        return AssistEnergyBudget(0.0, 0.0, 0.0, 0.0, 0.0)
    sums = dict.fromkeys(("E_drive_J", "W_thrust_J", "J_mass_J"), 0.0)
    for res in phases:
        y0 = np.asarray(res.y[:, 0], dtype=float)
        for name in sums:
            sums[name] += float(layout.get(res.y_end, name)) - float(layout.get(y0, name))

    def mech(res: PhaseResult, y: np.ndarray) -> float:
        s = float(layout.get(y, "s_m"))
        sdot = float(layout.get(y, "sdot_mps"))
        total = float(layout.get(y, "m_kg")) + carriage_mass_kg
        return total * (0.5 * sdot * sdot + g_eff_mps2 * res.spec.params.track.z(s))

    first, last = phases[0], phases[-1]
    delta_mech = mech(last, last.y_end) - mech(first, np.asarray(first.y[:, 0], dtype=float))
    return AssistEnergyBudget(
        work_drive=sums["E_drive_J"],
        work_thrust=sums["W_thrust_J"],
        delta_mech=delta_mech,
        massflow_term=-sums["J_mass_J"],
        dissipated=0.0,
    )


def loss_budget(phases: Sequence[PhaseResult], layout: StateLayout = VERTICAL_LAYOUT) -> LossBudget:
    """The LossBudget of a sequence of free-flight phases (release onward).

    Inputs: the ascent PhaseResults in time order, each carrying the loss quadrature
    states (``J_vac_mps``, ``J_grav_mps``, ``J_alt_mps``, ``J_bp_mps``, ``J_steer_mps``)
    and the signed velocity ``v_mps``; the state layout. Output: the per-phase
    increments of every quadrature summed (so a reset between phases would not be
    hidden), speed_start = |v| at the start of the first phase and speed_end = |v| at
    the end of the last one, all in m/s. An empty sequence gives an all-zero budget.
    """
    names = ("J_vac_mps", "J_grav_mps", "J_alt_mps", "J_bp_mps", "J_steer_mps")
    sums = dict.fromkeys(names, 0.0)
    if not phases:
        return LossBudget(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    for res in phases:
        y0 = np.asarray(res.y[:, 0], dtype=float)
        for name in names:
            sums[name] += float(layout.get(res.y_end, name)) - float(layout.get(y0, name))
    v_start = float(layout.get(np.asarray(phases[0].y[:, 0], dtype=float), "v_mps"))
    v_end = float(layout.get(phases[-1].y_end, "v_mps"))
    return LossBudget(
        dv_vac=sums["J_vac_mps"],
        gravity=sums["J_grav_mps"],
        gravity_alt=sums["J_alt_mps"],
        drag=0.0,
        steering=sums["J_steer_mps"],
        back_pressure=sums["J_bp_mps"],
        speed_start=abs(v_start),
        speed_end=abs(v_end),
    )


def prerelease_full_thrust_seconds(startup: Startup, t_ign_s: float) -> float:
    """Phi_pre [s]: full-thrust-equivalent seconds burned before release by an engine
    lit at t_ign_s [s] relative to release (0 for t_ign_s >= 0): the integral of f over
    [t_ign, 0]. ramp: t_ign^2/(2 t_r) for -t_r < t_ign < 0, -t_ign - t_r/2 for
    t_ign <= -t_r; lag: -t_ign - tau (1 - exp(t_ign/tau)); step: -t_ign."""
    if t_ign_s >= 0.0:
        return 0.0
    kind = startup.effective_kind
    if kind == "step":
        return -t_ign_s
    if kind == "ramp":
        t_r = startup.t_ramp_s
        if t_ign_s > -t_r:
            return t_ign_s * t_ign_s / (2.0 * t_r)
        return -t_ign_s - 0.5 * t_r
    tau = startup.tau_s
    return -t_ign_s + tau * math.expm1(t_ign_s / tau)


def lag_deficit_exact_s(tau_s: float, t_ign_s: float, t_burn_s: float) -> float:
    """Exact post-release deficit [s] of a first-order lag lit at t_ign_s [s] relative
    to release, for a propellant load worth t_burn_s [s] of full thrust.

    With a = exp(min(t_ign, 0)/tau) (1 when lit at or after release) and t_b' = t_b -
    Phi_pre the full-thrust seconds left at release, the burn after release ends at
    s_e = tau u with u = a + t_b'/tau + W0(-a exp(-a - t_b'/tau)), so the deficit is
    max(t_ign, 0) + s_e - t_b' = max(t_ign, 0) + tau (a + W0(...)); its asymptote for a
    long burn is max(t_ign, 0) + tau a (``startup_deficit_s``). Requires t_b' > 0.
    """
    startup = Startup("lag", tau_s=tau_s)
    t_left = t_burn_s - prerelease_full_thrust_seconds(startup, t_ign_s)
    if t_left <= 0.0:
        raise ValueError("the propellant is exhausted before release")
    a = math.exp(min(t_ign_s, 0.0) / tau_s)
    w = float(lambertw(-a * math.exp(-a - t_left / tau_s), k=0).real)
    return max(t_ign_s, 0.0) + tau_s * (a + w)


def ignition_loss_analytic_mps(
    g_ref_mps2: float,
    t_ign_s: float,
    startup: Startup,
    c_mps: float,
    mdot_kgps: float,
    m0_kg: float,
    t_burn_s: float | None = None,
) -> float:
    """Speed lost [m/s] at burnout, under constant gravity g_ref and v > 0 throughout,
    by lighting the engines at t_ign_s [s] relative to release with the given startup
    shape, against an instant full-thrust start at release from the same state
    (docs/physics.md, "Ignition-after-release loss").

    Inputs: g_ref_mps2 [m/s^2]; t_ign_s [s] (negative: lit before release); startup;
    c_mps, the exhaust velocity [m/s]; mdot_kgps, the full-thrust mass flow [kg/s];
    m0_kg, the mass at ignition [kg] (the release mass of the reference); t_burn_s, the
    full-thrust burn time of the propellant [s], which makes a lag exact (without it the
    lag term is its long-burn asymptote tau exp(min(t_ign, 0)/tau)). Output:

        loss = c ln(m0 / (m0 - mdot Phi_pre)) - g Phi_pre + g D_post

    where Phi_pre is the full-thrust seconds burned before release
    (``prerelease_full_thrust_seconds``: delta-v spent while clamped, minus the gravity
    loss it would have cost in flight) and D_post is the post-release deficit
    ``startup_deficit_s`` (the delay plus the missing fraction of the ramp or lag; it
    already contains max(t_ign, 0)). Exact for a step and a ramp when the propellant
    outlasts the ramp; exact for a lag when t_burn_s is given.
    """
    phi_pre = prerelease_full_thrust_seconds(startup, t_ign_s)
    m_release = m0_kg - mdot_kgps * phi_pre
    if m_release <= 0.0:
        raise ValueError("more propellant burned before release than the vehicle carries")
    if startup.effective_kind == "lag" and t_burn_s is not None:
        d_post = lag_deficit_exact_s(startup.tau_s, t_ign_s, t_burn_s)
    else:
        d_post = startup_deficit_s(startup, t_ign_s)
    return c_mps * math.log(m0_kg / m_release) - g_ref_mps2 * phi_pre + g_ref_mps2 * d_post
