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
