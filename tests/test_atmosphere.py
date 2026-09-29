"""Atmosphere: ICAO table points, agreement with the ambiance reference implementation,
the geopotential-height guard, the isothermal extension above 81,020 m, input
validation and array handling. Expected values come from the ICAO Standard Atmosphere
tables and closed forms evaluated here from constants; ``ambiance.Atmosphere`` is the
independent oracle for the in-house layer evaluation.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from ambiance import CONST as ICAO_CONST
from ambiance import Atmosphere

from launchsim.atmosphere import (
    AtmosphereState,
    density_kgm3,
    extension_scale_height_m,
    pressure_pa,
    speed_of_sound_mps,
    standard_atmosphere,
)
from launchsim.constants import (
    ALT_AMBIANCE_MAX_M,
    ALT_AMBIANCE_MIN_M,
    MU_EARTH_M3S2,
    R_AIR_JKGK,
    R_EARTH_M,
)

R_ICAO_M = 6_356_766.0
"""ICAO nominal Earth radius [m] used to convert geopotential to geometric height."""

T_TOP_TABLE_K = 196.65
"""ICAO table temperature [K] at 80 km geopotential, the top of the standard."""

# (geopotential height H [m], p [Pa], rho [kg/m^3] or None, T [K] or None, a [m/s] or None)
# ICAO Doc 7488 table values at the layer bases; p rounded to five significant figures.
ICAO_POINTS = [
    (0.0, 101_325.0, 1.225, 288.15, 340.294),
    (11_000.0, 22_632.0, None, 216.65, None),
    (20_000.0, 5_474.9, None, 216.65, None),
    (32_000.0, 868.02, None, 228.65, None),
    (47_000.0, 110.91, None, 270.65, None),
    (51_000.0, 66.938, None, 270.65, None),
    (71_000.0, 3.9564, None, 214.65, None),
    (80_000.0, 0.88627, None, T_TOP_TABLE_K, 281.12),
]
LAYER_BASES_GEOPOTENTIAL_M = [-5_000.0] + [row[0] for row in ICAO_POINTS]

REL_P_RHO = 1e-4
ABS_T = 1e-6
REL_A = 1e-5
REL_ORACLE = 1e-12


def geometric_m(geopotential_m: float) -> float:
    """h = r0 H / (r0 - H) with the ICAO nominal radius."""
    return R_ICAO_M * geopotential_m / (R_ICAO_M - geopotential_m)


def scale_height_from_table_m() -> float:
    """H_s = R_air T_top / g(h_top) with the ICAO table temperature at the top."""
    g_top = MU_EARTH_M3S2 / (R_EARTH_M + ALT_AMBIANCE_MAX_M) ** 2
    return R_AIR_JKGK * T_TOP_TABLE_K / g_top


def assert_matches_ambiance(alt_m: np.ndarray | float, state: AtmosphereState) -> None:
    ref = Atmosphere(alt_m)
    for mine, theirs in (
        (state.p_pa, ref.pressure),
        (state.rho_kgm3, ref.density),
        (state.T_K, ref.temperature),
        (state.a_mps, ref.speed_of_sound),
    ):
        np.testing.assert_allclose(
            np.asarray(mine), theirs.reshape(np.shape(mine)), rtol=REL_ORACLE
        )


@pytest.mark.parametrize("H_m,p_pa,rho_kgm3,T_K,a_mps", ICAO_POINTS)
def test_icao_table_points(
    H_m: float, p_pa: float, rho_kgm3: float | None, T_K: float | None, a_mps: float | None
) -> None:
    state = standard_atmosphere(geometric_m(H_m))
    assert isinstance(state, AtmosphereState)
    assert isinstance(state.p_pa, float)
    assert state.p_pa == pytest.approx(p_pa, rel=REL_P_RHO)
    if rho_kgm3 is not None:
        assert state.rho_kgm3 == pytest.approx(rho_kgm3, rel=REL_P_RHO)
    if T_K is not None:
        assert state.T_K == pytest.approx(T_K, abs=ABS_T)
    if a_mps is not None:
        assert state.a_mps == pytest.approx(a_mps, rel=REL_A)


def test_constants_agree_with_ambiance_table() -> None:
    """The extension's R_air is the ICAO value ambiance uses, so density is continuous."""
    assert R_AIR_JKGK == ICAO_CONST.R
    assert R_ICAO_M == ICAO_CONST.r
    assert ALT_AMBIANCE_MIN_M == ICAO_CONST.h_min
    assert ALT_AMBIANCE_MAX_M == ICAO_CONST.h_max


def test_matches_ambiance_on_dense_grid() -> None:
    """The in-house layer evaluation reproduces ambiance.Atmosphere everywhere in range."""
    bases = np.array([geometric_m(H) for H in LAYER_BASES_GEOPOTENTIAL_M])
    grid = np.concatenate(
        [
            np.linspace(ALT_AMBIANCE_MIN_M, ALT_AMBIANCE_MAX_M, 20_001),
            bases,
            bases[1:] - 1e-6,
            bases[:-1] + 1e-6,
            [11_000.0, ALT_AMBIANCE_MIN_M, ALT_AMBIANCE_MAX_M],
        ]
    )
    grid = grid[(grid >= ALT_AMBIANCE_MIN_M) & (grid <= ALT_AMBIANCE_MAX_M)]
    assert_matches_ambiance(grid, standard_atmosphere(grid))


def test_scalar_path_matches_ambiance() -> None:
    """The pure-Python scalar branch is a separate code path from the array branch."""
    points = [geometric_m(H) for H in LAYER_BASES_GEOPOTENTIAL_M]
    points += [ALT_AMBIANCE_MIN_M, -100.0, 1_234.5, 11_000.0, 25e3, 60e3, ALT_AMBIANCE_MAX_M]
    for h in points:
        assert_matches_ambiance(h, standard_atmosphere(h))


def test_geopotential_conversion_matters() -> None:
    """11,000 m geometric is not the 11 km tropopause: the table is at geopotential H."""
    p_geometric = standard_atmosphere(11_000.0).p_pa
    assert abs(p_geometric - 22_632.0) / 22_632.0 > 1e-3


def test_below_sea_level_and_floor() -> None:
    state = standard_atmosphere(-100.0)
    assert state.p_pa > 101_325.0
    assert state.T_K > 288.15
    assert standard_atmosphere(ALT_AMBIANCE_MIN_M).p_pa > 0.0
    with pytest.raises(ValueError):
        standard_atmosphere(ALT_AMBIANCE_MIN_M - 0.5)
    with pytest.raises(ValueError):
        standard_atmosphere(np.array([0.0, -6_000.0]))


@pytest.mark.parametrize(
    "bad", [math.nan, math.inf, -math.inf, np.array([0.0, np.nan]), np.array([0.0, np.inf])]
)
def test_non_finite_altitude_raises(bad: float | np.ndarray) -> None:
    with pytest.raises(ValueError, match="finite"):
        standard_atmosphere(bad)


@pytest.mark.parametrize(
    "bad", ["1000", None, True, np.bool_(True), 1 + 2j, np.array([True, False])]
)
def test_non_numeric_altitude_raises(bad: object) -> None:
    with pytest.raises(TypeError):
        standard_atmosphere(bad)  # type: ignore[arg-type]


def test_scalar_like_inputs_return_floats() -> None:
    reference = standard_atmosphere(5.0)
    for h in (5, np.int64(5), np.float32(5.0), np.float64(5.0), np.array(5.0)):
        state = standard_atmosphere(h)
        assert isinstance(state.p_pa, float) and isinstance(state.a_mps, float)
        assert state.p_pa == pytest.approx(reference.p_pa, rel=1e-6)


def test_top_state_anchored_to_table() -> None:
    """The extension anchor is the ICAO state at 81,020 m (H = 80,000.36 m), not a guess."""
    top = standard_atmosphere(ALT_AMBIANCE_MAX_M)
    assert top.T_K == pytest.approx(T_TOP_TABLE_K, abs=1e-3)
    assert top.p_pa == pytest.approx(0.88627, rel=1e-4)
    assert extension_scale_height_m() == pytest.approx(scale_height_from_table_m(), rel=1e-4)
    assert_matches_ambiance(ALT_AMBIANCE_MAX_M, top)


def test_extension_continuous_at_seam() -> None:
    h_top = ALT_AMBIANCE_MAX_M
    below = standard_atmosphere(h_top - 1e-3)
    at = standard_atmosphere(h_top)
    above = standard_atmosphere(h_top + 1e-3)
    for field in ("p_pa", "rho_kgm3", "T_K", "a_mps"):
        v_below, v_at, v_above = (getattr(s, field) for s in (below, at, above))
        assert v_at == pytest.approx(v_below, rel=1e-6), field
        assert v_above == pytest.approx(v_at, rel=1e-6), field


def test_extension_density_closed_form() -> None:
    """rho(100 km) = rho_top exp(-dh / H_s) with H_s from constants and the table T_top.

    The tolerance covers the 3.6e-6 difference between the table's 196.65 K and the
    anchor's 196.6493 K (the 71-80 km lapse rate over the last 0.36 m); the anchor itself
    is pinned in test_top_state_anchored_to_table.
    """
    h_top = ALT_AMBIANCE_MAX_M
    top = standard_atmosphere(h_top)
    h = 100_000.0
    expected_rho = top.rho_kgm3 * math.exp(-(h - h_top) / scale_height_from_table_m())
    state = standard_atmosphere(h)
    assert state.rho_kgm3 == pytest.approx(expected_rho, rel=1e-4)
    # exact form with the anchor's own temperature
    g_top = MU_EARTH_M3S2 / (R_EARTH_M + h_top) ** 2
    h_s_anchor = R_AIR_JKGK * top.T_K / g_top
    assert state.rho_kgm3 == pytest.approx(
        top.rho_kgm3 * math.exp(-(h - h_top) / h_s_anchor), rel=1e-9
    )
    assert state.T_K == pytest.approx(top.T_K, rel=1e-12)
    assert state.a_mps == pytest.approx(top.a_mps, rel=1e-12)
    # ideal gas closes with the same T and R_air
    assert state.p_pa == pytest.approx(state.rho_kgm3 * R_AIR_JKGK * state.T_K, rel=1e-12)


def test_extension_never_steps_to_zero() -> None:
    for h in (200e3, 300e3, 1_000e3):
        state = standard_atmosphere(h)
        assert 0.0 < state.p_pa < 1.0
        assert 0.0 < state.rho_kgm3 < 1e-5


def test_density_and_pressure_monotone_to_300_km() -> None:
    grid = np.linspace(0.0, 300e3, 3001)
    state = standard_atmosphere(grid)
    assert np.all(np.diff(state.rho_kgm3) < 0.0)
    assert np.all(np.diff(state.p_pa) < 0.0)
    assert np.all(np.isfinite(state.T_K)) and np.all(state.T_K > 0.0)


def test_array_matches_scalar_elementwise() -> None:
    grid = np.array([-100.0, 0.0, 5e3, 11_019.0, 50e3, ALT_AMBIANCE_MAX_M, 90e3, 200e3])
    arr = standard_atmosphere(grid)
    assert isinstance(arr.p_pa, np.ndarray) and arr.p_pa.shape == grid.shape
    for i, h in enumerate(grid):
        one = standard_atmosphere(float(h))
        assert arr.p_pa[i] == pytest.approx(one.p_pa, rel=1e-12)
        assert arr.rho_kgm3[i] == pytest.approx(one.rho_kgm3, rel=1e-12)
        assert arr.T_K[i] == pytest.approx(one.T_K, rel=1e-12)
        assert arr.a_mps[i] == pytest.approx(one.a_mps, rel=1e-12)


def test_mixed_array_in_and_above_range() -> None:
    grid = np.array([0.0, 50e3, 100e3, 200e3])
    state = standard_atmosphere(grid)
    for field in ("p_pa", "rho_kgm3", "T_K", "a_mps"):
        values = getattr(state, field)
        assert values.shape == (4,)
        assert np.all(np.isfinite(values)) and np.all(values > 0.0), field
    assert state.p_pa[0] == pytest.approx(101_325.0, rel=REL_P_RHO)
    assert np.all(np.diff(state.p_pa) < 0.0)


def test_shape_preserved_and_empty_input() -> None:
    grid = np.array([[0.0, 90e3], [40e3, 300e3]])
    state = standard_atmosphere(grid)
    assert state.p_pa.shape == (2, 2)
    assert state.p_pa[0, 0] == pytest.approx(101_325.0, rel=REL_P_RHO)
    empty = standard_atmosphere(np.array([]))
    assert empty.p_pa.shape == (0,)
    assert standard_atmosphere([0.0, 1_000.0]).p_pa.shape == (2,)


def test_array_results_are_read_only_and_input_untouched() -> None:
    grid = np.array([0.0, 90e3])
    original = grid.copy()
    state = standard_atmosphere(grid)
    with pytest.raises(ValueError):
        state.p_pa[0] = 1.0
    with pytest.raises(ValueError):
        state.T_K[0] = 1.0
    assert np.array_equal(grid, original)


def test_convenience_functions_match_state() -> None:
    for h in (0.0, 30e3, 150e3):
        state = standard_atmosphere(h)
        assert pressure_pa(h) == state.p_pa
        assert density_kgm3(h) == state.rho_kgm3
        assert speed_of_sound_mps(h) == state.a_mps
