"""Orbit targets, the specific orbital energy and two-body orbital elements of a planar
state (the insertion cutoff of the planar stage 2 fires on the energy).

Everything is SI and pure: no I/O, no globals, no printing. Frame: the planar
Earth-centred inertial frame of the ascent (docs/physics.md, "Planar ascent state and
equations of motion"); r is the distance from Earth's centre [m], v_r and v_theta the
inertial radial and horizontal velocity components [m/s]. The elements are those of the
osculating Kepler orbit under the point-mass gravitational parameter mu [m^3/s^2]; they
use the inertial velocity, never v_rel. Formulas: docs/physics.md, "Orbital elements
and the circular target".
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class TargetOrbit:
    """A circular target orbit of radius r_m [m] (from Earth's centre; > 0).

    Phase 2 targets circular orbits only. The insertion cutoff of the planar model is
    the specific orbital energy reaching ``energy_Jkg(mu)``; the circular speed is
    ``v_circ_mps(mu)``. Frame: planar ECI (inertial speed and energy).
    """

    r_m: float

    def __post_init__(self) -> None:
        if not (math.isfinite(self.r_m) and self.r_m > 0.0):
            raise ValueError("target radius must be finite and > 0 m")

    def energy_Jkg(self, mu_m3s2: float) -> float:
        """Specific orbital energy of the circular orbit, E* = -mu / (2 r) [J/kg].

        Input: mu_m3s2, the gravitational parameter [m^3/s^2]. Output: [J/kg] (m^2/s^2),
        inertial.
        """
        return -mu_m3s2 / (2.0 * self.r_m)

    def v_circ_mps(self, mu_m3s2: float) -> float:
        """Inertial circular speed sqrt(mu / r) [m/s] at the target radius.

        Input: mu_m3s2 [m^3/s^2]. Output: [m/s], purely horizontal (v_r = 0).
        """
        return math.sqrt(mu_m3s2 / self.r_m)

    def speed_rel_mps(self, mu_m3s2: float, omega_p_rads: float) -> float:
        """Earth-relative speed |v_rel| = v_c - omega_p r_t [m/s] on the circular target
        orbit in the planar model (the air co-rotates at omega_p, and v_r = 0 there).

        Inputs: mu_m3s2 [m^3/s^2]; omega_p_rads, the planar rotation rate [rad/s].
        Output: [m/s], the V_f of the loss identity at an exact insertion (7,362.7061 m/s
        for 200 km at 28.5 deg east).
        """
        return self.v_circ_mps(mu_m3s2) - omega_p_rads * self.r_m

    def altitude_m(self, r_datum_m: float) -> float:
        """Altitude r_t - r_datum [m] of the target above a datum sphere of radius
        r_datum_m [m] (R_E in runs)."""
        return self.r_m - r_datum_m


def specific_energy_Jkg(r_m: float, v_r_mps: float, v_theta_mps: float, mu_m3s2: float) -> float:
    """Specific orbital energy E = (v_r^2 + v_theta^2)/2 - mu/r [J/kg] of a planar state.

    Inputs: r_m [m] from Earth's centre; v_r_mps and v_theta_mps, the inertial velocity
    components [m/s]; mu_m3s2 [m^3/s^2]. Output: [J/kg]. Frame: planar ECI (inertial
    velocity). The planar insertion cutoff fires where it reaches E* = -mu/(2 r_t).
    """
    return 0.5 * (v_r_mps * v_r_mps + v_theta_mps * v_theta_mps) - mu_m3s2 / r_m


@dataclass(frozen=True)
class OrbitElements:
    """Osculating two-body elements of a planar state.

    a_m: semi-major axis [m] (-mu / (2E); negative for a hyperbola, inf for a parabola);
    e: eccentricity (dimensionless, >= 0); r_p_m and r_a_m: periapsis and apoapsis
    radii [m] from Earth's centre (r_a inf when e >= 1); energy_Jkg: specific orbital
    energy E = (v_r^2 + v_theta^2)/2 - mu/r [J/kg]; h_m2s: specific angular momentum
    r v_theta [m^2/s] (signed; positive for motion toward increasing theta). Frame:
    planar ECI.
    """

    a_m: float
    e: float
    r_p_m: float
    r_a_m: float
    energy_Jkg: float
    h_m2s: float


def orbit_elements(r_m: float, v_r_mps: float, v_theta_mps: float, mu_m3s2: float) -> OrbitElements:
    """Two-body elements from a planar inertial state.

    Inputs: r_m, radius from Earth's centre [m] (> 0); v_r_mps and v_theta_mps, the
    inertial radial and horizontal velocity components [m/s]; mu_m3s2, the
    gravitational parameter [m^3/s^2] (> 0). Output: ``OrbitElements``. Frame: planar
    ECI.

    E = (v_r^2 + v_theta^2)/2 - mu/r and h = r v_theta. The eccentricity is the length of
    the eccentricity vector in the local frame, e = hypot(h^2/(mu r) - 1, h v_r/mu),
    which equals sqrt(1 + 2 E h^2/mu^2) exactly but keeps its relative accuracy near a
    circular orbit, where the square-root form cancels to rounding (an e of 1e-7 would
    carry an error of order 1e-9 there). r_p = h^2 / (mu (1 + e)); r_a = h^2 /
    (mu (1 - e)) for e < 1, else inf; a = -mu / (2E) (inf when E = 0). A purely radial
    state (h = 0) gives the degenerate conic e = 1, r_p = 0, r_a = inf whatever its
    energy, while a keeps -mu / (2E).
    """
    if not (math.isfinite(r_m) and r_m > 0.0):
        raise ValueError("r must be finite and > 0 m")
    if not (math.isfinite(mu_m3s2) and mu_m3s2 > 0.0):
        raise ValueError("mu must be finite and > 0")
    energy = specific_energy_Jkg(r_m, v_r_mps, v_theta_mps, mu_m3s2)
    h = r_m * v_theta_mps
    p_m = h * h / mu_m3s2
    e = math.hypot(p_m / r_m - 1.0, h * v_r_mps / mu_m3s2)
    a = math.inf if energy == 0.0 else -mu_m3s2 / (2.0 * energy)
    r_p = p_m / (1.0 + e)
    r_a = p_m / (1.0 - e) if e < 1.0 else math.inf
    return OrbitElements(a_m=a, e=e, r_p_m=r_p, r_a_m=r_a, energy_Jkg=energy, h_m2s=h)
