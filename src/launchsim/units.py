"""Unit conversions at the YAML and plot boundary.

Internally everything is SI and radians. Degrees, km, kN, tonnes, g and kWh appear only
in configuration files and plot labels and are converted here. Nothing else in the
package multiplies by 1000, pi/180 or g0. All functions accept floats or numpy arrays.
"""

from __future__ import annotations

import math

import numpy as np

from launchsim.constants import G0_MPS2, J_PER_KWH

type Quantity = float | np.ndarray
"""A scalar or a numpy array; conversions preserve the shape of their input."""


def deg_to_rad(angle_deg: Quantity) -> Quantity:
    """Degrees to radians."""
    return angle_deg * (math.pi / 180.0)


def rad_to_deg(angle_rad: Quantity) -> Quantity:
    """Radians to degrees."""
    return angle_rad * (180.0 / math.pi)


def km_to_m(length_km: Quantity) -> Quantity:
    """Kilometres to metres."""
    return length_km * 1000.0


def m_to_km(length_m: Quantity) -> Quantity:
    """Metres to kilometres."""
    return length_m / 1000.0


def kn_to_n(force_kn: Quantity) -> Quantity:
    """Kilonewtons to newtons."""
    return force_kn * 1000.0


def n_to_kn(force_n: Quantity) -> Quantity:
    """Newtons to kilonewtons."""
    return force_n / 1000.0


def t_to_kg(mass_t: Quantity) -> Quantity:
    """Tonnes to kilograms."""
    return mass_t * 1000.0


def kg_to_t(mass_kg: Quantity) -> Quantity:
    """Kilograms to tonnes."""
    return mass_kg / 1000.0


def from_g(accel_g: Quantity) -> Quantity:
    """Acceleration in units of standard gravity g0 to m/s^2."""
    return accel_g * G0_MPS2


def to_g(accel_mps2: Quantity) -> Quantity:
    """Acceleration in m/s^2 to units of standard gravity g0."""
    return accel_mps2 / G0_MPS2


def j_to_kwh(energy_j: Quantity) -> Quantity:
    """Joules to kilowatt-hours."""
    return energy_j / J_PER_KWH


def kwh_to_j(energy_kwh: Quantity) -> Quantity:
    """Kilowatt-hours to joules."""
    return energy_kwh * J_PER_KWH


def pa_to_kpa(pressure_pa: Quantity) -> Quantity:
    """Pascals to kilopascals (plot labels and reports)."""
    return pressure_pa / 1000.0
