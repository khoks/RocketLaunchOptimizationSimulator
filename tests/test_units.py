"""Unit conversions round-trip and use the documented factors."""

from __future__ import annotations

import math

import numpy as np

from launchsim import units
from launchsim.constants import G0_MPS2, J_PER_KWH


def test_scalar_round_trips() -> None:
    pairs = [
        (units.deg_to_rad, units.rad_to_deg, 28.5),
        (units.km_to_m, units.m_to_km, 200.0),
        (units.kn_to_n, units.n_to_kn, 914.1),
        (units.t_to_kg, units.kg_to_t, 25.6),
        (units.from_g, units.to_g, 3.0),
        (units.kwh_to_j, units.j_to_kwh, 1.2e3),
    ]
    for forward, back, value in pairs:
        assert math.isclose(back(forward(value)), value, rel_tol=1e-12)


def test_documented_factors() -> None:
    assert math.isclose(units.deg_to_rad(180.0), math.pi, rel_tol=1e-15)
    assert units.km_to_m(1.0) == 1000.0
    assert units.kn_to_n(1.0) == 1000.0
    assert units.t_to_kg(1.0) == 1000.0
    assert units.from_g(1.0) == G0_MPS2
    assert units.kwh_to_j(1.0) == J_PER_KWH


def test_array_inputs() -> None:
    a = np.array([0.0, 1.0, 3.0])
    np.testing.assert_allclose(units.from_g(a), a * G0_MPS2, rtol=1e-15)
    np.testing.assert_allclose(units.to_g(units.from_g(a)), a, rtol=1e-15)


def test_pa_to_kpa() -> None:
    assert units.pa_to_kpa(101_325.0) == 101.325
    np.testing.assert_allclose(units.pa_to_kpa(np.array([0.0, 2500.0])), [0.0, 2.5], rtol=1e-15)


def test_structure_file_units() -> None:
    """The structure file's units (SP7 step S1): GPa, MPa, bar (gauge stays gauge), mm,
    kg/MN and kg/kN to SI by their documented factors, and back."""
    assert units.gpa_to_pa(75.8) == 75.8e9
    assert units.mpa_to_pa(558.0) == 558.0e6
    assert units.bar_to_pa(3.0) == 3.0e5
    assert units.mm_to_m(1.0) == 1.0e-3
    assert math.isclose(units.mm_to_m(4.2), 4.2e-3, rel_tol=1e-15)
    assert units.kg_per_mn_to_kg_per_n(100.0) == 1.0e-4
    assert units.kg_per_kn_to_kg_per_n(0.255) == 0.255 / 1000.0
    pairs = [
        (units.gpa_to_pa, units.pa_to_gpa, 75.8),
        (units.mpa_to_pa, units.pa_to_mpa, 558.0),
        (units.bar_to_pa, units.pa_to_bar, 3.2),
        (units.mm_to_m, units.m_to_mm, 4.2),
        (units.kg_per_mn_to_kg_per_n, units.kg_per_n_to_kg_per_mn, 60.0),
        (units.kg_per_kn_to_kg_per_n, units.kg_per_n_to_kg_per_kn, 0.28),
    ]
    for forward, back, value in pairs:
        assert math.isclose(back(forward(value)), value, rel_tol=1e-12)
    a = np.array([0.0, 1.0, 2.5])
    np.testing.assert_allclose(units.bar_to_pa(a), a * 1.0e5, rtol=1e-15)
    np.testing.assert_allclose(units.m_to_mm(units.mm_to_m(a)), a, rtol=1e-15)
