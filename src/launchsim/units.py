"""Unit conversions at the YAML and plot boundary.

Internally everything is SI and radians. Degrees, km, kN, tonnes, g, kWh and MJ appear
only in configuration files, plot labels and reports and are converted here, as are the
structure file's units (GPa, MPa, bar, mm, kg/MN and kg/kN; SP7 step S1). Nothing else
in the package multiplies by 1000, 1e5, 1e6, 1e9, pi/180 or g0. Percent is a reporting
format, not covered by that rule: the offload reports and the calibration footnote in
plots.py use ``to_percent``, other labels Python's ``%`` format spec or a factor 100 of
their own (the replay page's labels in replay.py). All functions accept floats or numpy
arrays.
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


def mj_to_j(energy_mj: Quantity) -> Quantity:
    """Megajoules to joules; also a specific energy in MJ/kg to J/kg (the heating value of
    the offload block's energy comparison)."""
    return energy_mj * 1.0e6


def j_to_mj(energy_j: Quantity) -> Quantity:
    """Joules to megajoules (reports); also J/kg to MJ/kg."""
    return energy_j / 1.0e6


def to_percent(fraction: Quantity) -> Quantity:
    """A dimensionless fraction to percent (reports)."""
    return fraction * 100.0


def gpa_to_pa(stress_gpa: Quantity) -> Quantity:
    """Gigapascals to pascals (a modulus such as the structure file's E_GPa)."""
    return stress_gpa * 1.0e9


def pa_to_gpa(stress_pa: Quantity) -> Quantity:
    """Pascals to gigapascals (reports)."""
    return stress_pa / 1.0e9


def mpa_to_pa(stress_mpa: Quantity) -> Quantity:
    """Megapascals to pascals (a strength or pressure such as F_tu_MPa)."""
    return stress_mpa * 1.0e6


def pa_to_mpa(stress_pa: Quantity) -> Quantity:
    """Pascals to megapascals (reports)."""
    return stress_pa / 1.0e6


def bar_to_pa(pressure_bar: Quantity) -> Quantity:
    """Bar to pascals (1 bar = 1e5 Pa exactly), for the structure file's gauge tank
    pressures, measured from the ambient pressure outside the vehicle (never across an
    inner wall), the form structure.py's sizing primitives take; the conversion keeps that
    reference: a gauge pressure in bar stays a gauge pressure in Pa."""
    return pressure_bar * 1.0e5


def pa_to_bar(pressure_pa: Quantity) -> Quantity:
    """Pascals to bar (reports); keeps a gauge reference, like ``bar_to_pa``."""
    return pressure_pa / 1.0e5


def mm_to_m(length_mm: Quantity) -> Quantity:
    """Millimetres to metres (a wall thickness such as t_min_mm)."""
    return length_mm / 1000.0


def m_to_mm(length_m: Quantity) -> Quantity:
    """Metres to millimetres (reports, such as a sized wall thickness)."""
    return length_m * 1000.0


def kg_per_mn_to_kg_per_n(coeff_kg_per_mn: Quantity) -> Quantity:
    """A mass per unit load in kg/MN to kg/N."""
    return coeff_kg_per_mn / 1.0e6


def kg_per_n_to_kg_per_mn(coeff_kg_per_n: Quantity) -> Quantity:
    """A mass per unit load in kg/N to kg/MN (reports)."""
    return coeff_kg_per_n * 1.0e6


def kg_per_kn_to_kg_per_n(coeff_kg_per_kn: Quantity) -> Quantity:
    """A mass per unit load in kg/kN to kg/N (such as k_ts_kg_per_kN)."""
    return coeff_kg_per_kn / 1000.0


def kg_per_n_to_kg_per_kn(coeff_kg_per_n: Quantity) -> Quantity:
    """A mass per unit load in kg/N to kg/kN (reports)."""
    return coeff_kg_per_n * 1000.0
