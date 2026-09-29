"""ICAO standard atmosphere plus a documented isothermal extension.

Inputs to every function are GEOMETRIC altitudes above mean sea level in metres.
Between ``ALT_AMBIANCE_MIN_M`` (-5,004 m) and ``ALT_AMBIANCE_MAX_M`` (81,020 m) the
values follow the ICAO Standard Atmosphere (ICAO Doc 7488, extended to 80 km
geopotential). The layer closed forms are evaluated here, directly from the constant
table that the ``ambiance`` package ships (``ambiance.CONST``), so that a scalar lookup
costs a few microseconds instead of the ~1 ms that ``ambiance.Atmosphere`` needs per
call; ``ambiance.Atmosphere`` remains the reference implementation and the test suite
asserts agreement with it to 1e-12 relative on a dense grid. With geopotential height
H = r0 h / (r0 + h) (r0 = ICAO nominal radius 6,356,766 m) and, in the layer whose base
is (H_b, T_b, beta, p_b):

    T(H) = T_b + beta (H - H_b)
    p(H) = p_b (T / T_b)^(-g0 / (R_air beta))        beta != 0
    p(H) = p_b exp(-g0 (H - H_b) / (R_air T_b))      beta == 0
    rho  = p / (R_air T),   a = sqrt(kappa R_air T)

Here g0 is the ICAO standard's definitional constant of the geopotential metre (a
constant of the table, taken from ``ambiance.CONST.g_0``, not a gravity model and not
this package's ``G0_MPS2``). For H >= 71 km the 71-80 km layer is used and extrapolated
to the 81,020 m geometric top (H = 80,000.36 m), and below H = -5,000 m the -5 km row
is extrapolated 7.9 m downward to the -5,004 m geometric floor (H = -5,007.9 m); both
exactly as ``ambiance`` does. The base pressures p_b are the table's rounded values
(six significant figures) rather than pressures propagated from 101,325 Pa through the
layers, so p and rho have relative jumps of up to 4e-6 at the layer bases (largest at
47 and 51 km); ``ambiance`` has the same jumps, and they are far below the loss-budget
resolution and do not slow the integrator measurably.

Above 81,020 m the module continues the profile with an isothermal exponential started
from the ICAO state at the top:

    T(h)   = T_top
    p(h)   = p_top * exp(-(h - h_top) / H_s)
    rho(h) = p(h) / (R_air * T_top)
    a(h)   = a_top
    H_s    = R_air * T_top / g(h_top),   g(h_top) = mu / (R_E + h_top)^2

The extension is a drag-order-of-magnitude device for the last seconds in which drag
matters at all. It is NOT the US Standard Atmosphere 1976 (which has a thermosphere
whose temperature rises steeply above 90 km and whose density falls more slowly than
this exponential). It continues to any altitude and never steps to zero until float64
underflow, which happens roughly 4,400 km above the top (well beyond any use here).

Assumptions carried into every result that uses this module:

- The ICAO geometric-to-geopotential conversion uses the ICAO nominal Earth radius,
  6,356,766 m, not this package's ``R_EARTH_M``. The ICAO tables are defined at
  geopotential height, so the altitudes passed in here must be geometric; the small
  radius mismatch is accepted.
- Above 81,020 m the atmosphere is isothermal at T_top = 196.649 K (the ICAO state at
  81,020 m) with the scale height above; real density above ~100 km differs from it
  by large factors and is strongly solar-activity dependent.
- The atmosphere is spherically symmetric, static and co-rotating with Earth (the
  co-rotation enters through v_rel in the dynamics, not here).
"""

from __future__ import annotations

import bisect
import functools
import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from ambiance import CONST as _ICAO

from launchsim.constants import (
    ALT_AMBIANCE_MAX_M,
    ALT_AMBIANCE_MIN_M,
    MU_EARTH_M3S2,
    R_AIR_JKGK,
    R_EARTH_M,
)
from launchsim.units import Quantity

type AltitudeInput = Quantity | Sequence[float]
"""A geometric altitude [m], or an array or sequence of them, accepted by this module."""

_MSG_NOT_FINITE = "altitude must be finite (NaN or infinite value given)"
_MSG_BELOW_FLOOR = f"altitude below the ICAO atmosphere floor of {ALT_AMBIANCE_MIN_M} m"


def _layer_table() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """ICAO layer bases from ambiance's table D: (H_b [m], T_b [K], beta [K/m], p_b [Pa]).

    The table's last row (80 km geopotential) is only the top of the 71-80 km layer and
    is dropped, so the last base row is extrapolated up to the 81,020 m geometric top.
    The arrays are read-only module constants; p_b are the table's rounded values (see
    the module docstring).
    """
    rows = _ICAO.LAYER_SPEC_PROP[:-1]
    columns = tuple(np.array([row[i] for row in rows], dtype=float) for i in range(4))
    for column in columns:
        column.flags.writeable = False
    return columns


_H_BASE_M, _T_BASE_K, _BETA_KPM, _P_BASE_PA = _layer_table()
_H_BASE_LIST_M: tuple[float, ...] = tuple(_H_BASE_M.tolist())
_R0_ICAO_M = float(_ICAO.r)
_G0_ICAO_MPS2 = float(_ICAO.g_0)
_KAPPA_AIR = float(_ICAO.kappa)


@dataclass(frozen=True)
class AtmosphereState:
    """Ambient air state at one or more geometric altitudes.

    Fields are Python floats for a scalar altitude (a float, an int, a numpy scalar or a
    0-d array) and read-only numpy arrays of the input's shape for an array altitude.
    Units: p_pa [Pa], rho_kgm3 [kg/m^3], T_K [K], a_mps [m/s].
    """

    p_pa: Quantity
    rho_kgm3: Quantity
    T_K: Quantity
    a_mps: Quantity


def _icao_scalar(alt_m: float) -> tuple[float, float, float, float]:
    """ICAO (p [Pa], rho [kg/m^3], T [K], a [m/s]) at one geometric altitude [m].

    Pure-Python evaluation of the layer closed forms in the module docstring; valid on
    [ALT_AMBIANCE_MIN_M, ALT_AMBIANCE_MAX_M]. About 2 us per call.
    """
    H = _R0_ICAO_M * alt_m / (_R0_ICAO_M + alt_m)
    i = bisect.bisect_right(_H_BASE_LIST_M, H) - 1
    i = min(max(i, 0), len(_H_BASE_LIST_M) - 1)
    dH = H - _H_BASE_LIST_M[i]
    T_b = float(_T_BASE_K[i])
    beta = float(_BETA_KPM[i])
    p_b = float(_P_BASE_PA[i])
    T = T_b + beta * dH
    if beta == 0.0:
        p = p_b * math.exp(-_G0_ICAO_MPS2 * dH / (R_AIR_JKGK * T_b))
    else:
        p = p_b * (T / T_b) ** (-_G0_ICAO_MPS2 / (R_AIR_JKGK * beta))
    rho = p / (R_AIR_JKGK * T)
    a = math.sqrt(_KAPPA_AIR * R_AIR_JKGK * T)
    return p, rho, T, a


def _icao_array(alt_m: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Vectorised ICAO (p, rho, T, a) at geometric altitudes [m] in a 1-D float array.

    Same closed forms as ``_icao_scalar``; valid on [ALT_AMBIANCE_MIN_M, ALT_AMBIANCE_MAX_M].
    """
    H = _R0_ICAO_M * alt_m / (_R0_ICAO_M + alt_m)
    i = np.searchsorted(_H_BASE_M, H, side="right") - 1
    i = np.clip(i, 0, _H_BASE_M.size - 1)
    dH = H - _H_BASE_M[i]
    T_b = _T_BASE_K[i]
    beta = _BETA_KPM[i]
    p_b = _P_BASE_PA[i]
    T = T_b + beta * dH
    isothermal = beta == 0.0
    exponent = np.divide(
        -_G0_ICAO_MPS2, R_AIR_JKGK * beta, out=np.zeros_like(beta), where=~isothermal
    )
    p_isothermal = p_b * np.exp(-_G0_ICAO_MPS2 * dH / (R_AIR_JKGK * T_b))
    p_gradient = p_b * (T / T_b) ** exponent
    p = np.where(isothermal, p_isothermal, p_gradient)
    rho = p / (R_AIR_JKGK * T)
    a = np.sqrt(_KAPPA_AIR * R_AIR_JKGK * T)
    return p, rho, T, a


@functools.cache
def _top_state() -> AtmosphereState:
    """ICAO state at ALT_AMBIANCE_MAX_M, the anchor of the isothermal extension."""
    return AtmosphereState(*_icao_scalar(ALT_AMBIANCE_MAX_M))


@functools.cache
def extension_scale_height_m() -> float:
    """Scale height H_s [m] of the isothermal extension above ALT_AMBIANCE_MAX_M.

    H_s = R_air * T_top / g(h_top) with g(h_top) = mu / (R_E + h_top)^2 evaluated at the
    geometric altitude h_top = ALT_AMBIANCE_MAX_M. Roughly 5.9 km; a constant.
    """
    g_top = MU_EARTH_M3S2 / (R_EARTH_M + ALT_AMBIANCE_MAX_M) ** 2
    return R_AIR_JKGK * _top_state().T_K / g_top


def _extension_scalar(alt_m: float) -> tuple[float, float, float, float]:
    """Isothermal extension (p, rho, T, a) at one geometric altitude above ALT_AMBIANCE_MAX_M."""
    top = _top_state()
    p = top.p_pa * math.exp(-(alt_m - ALT_AMBIANCE_MAX_M) / extension_scale_height_m())
    return p, p / (R_AIR_JKGK * top.T_K), top.T_K, top.a_mps


def _extension_array(
    alt_m: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Isothermal extension (p, rho, T, a) at geometric altitudes above ALT_AMBIANCE_MAX_M."""
    top = _top_state()
    p = top.p_pa * np.exp(-(alt_m - ALT_AMBIANCE_MAX_M) / extension_scale_height_m())
    rho = p / (R_AIR_JKGK * top.T_K)
    T = np.full_like(alt_m, top.T_K)
    a = np.full_like(alt_m, top.a_mps)
    return p, rho, T, a


def _state_scalar(alt_m: float) -> AtmosphereState:
    """State at one validated geometric altitude [m]: ICAO range or extension."""
    if alt_m <= ALT_AMBIANCE_MAX_M:
        return AtmosphereState(*_icao_scalar(alt_m))
    return AtmosphereState(*_extension_scalar(alt_m))


def _check_floor(alt_m: float | np.ndarray) -> None:
    """Raise ValueError for a non-finite altitude or one below ALT_AMBIANCE_MIN_M."""
    if not np.all(np.isfinite(alt_m)):
        raise ValueError(_MSG_NOT_FINITE)
    if not np.all(alt_m >= ALT_AMBIANCE_MIN_M):
        raise ValueError(_MSG_BELOW_FLOOR)


def _state_array(alt_m: np.ndarray) -> AtmosphereState:
    """State at a validated float array of geometric altitudes [m], any shape.

    ICAO and extension entries are evaluated separately through a mask; the returned
    arrays have the input's shape and are read-only.
    """
    flat = alt_m.reshape(-1)
    fields = tuple(np.empty_like(flat) for _ in range(4))
    icao = flat <= ALT_AMBIANCE_MAX_M
    above = ~icao
    for field, value in zip(fields, _icao_array(flat[icao]), strict=True):
        field[icao] = value
    for field, value in zip(fields, _extension_array(flat[above]), strict=True):
        field[above] = value
    shaped = []
    for field in fields:
        out = field.reshape(alt_m.shape)
        out.flags.writeable = False
        shaped.append(out)
    return AtmosphereState(*shaped)


def standard_atmosphere(alt_m: AltitudeInput) -> AtmosphereState:
    """Ambient air state at a geometric altitude above mean sea level.

    Input: alt_m, geometric altitude [m]: a real number (float, int or numpy real
    scalar), a 0-d array, or a numpy array (or sequence) of any shape.
    Output: AtmosphereState with p [Pa], rho [kg/m^3], T [K] and a [m/s]; Python floats
    for a scalar or 0-d input, read-only arrays of the input's shape otherwise.

    Altitudes in [ALT_AMBIANCE_MIN_M, ALT_AMBIANCE_MAX_M] use the ICAO closed forms;
    higher ones use the isothermal extension described in the module docstring. Any
    altitude below ALT_AMBIANCE_MIN_M, or a NaN or infinite one, raises ValueError;
    non-numeric input (strings, None, complex, bool) raises TypeError.

    Cost: about 2 us for a Python float or int or a numpy real scalar (np.float64 is
    what solve_ivp hands out), about 10 us for a 0-d array, and about 0.07 us per
    element for arrays, so it is safe inside an ODE right-hand side.
    """
    if isinstance(alt_m, float | int | np.floating | np.integer) and not isinstance(
        alt_m, bool | np.bool_
    ):
        h_scalar = float(alt_m)
        if not math.isfinite(h_scalar):
            raise ValueError(_MSG_NOT_FINITE)
        if h_scalar < ALT_AMBIANCE_MIN_M:
            raise ValueError(_MSG_BELOW_FLOOR)
        return _state_scalar(h_scalar)

    h = np.asarray(alt_m)
    if not np.issubdtype(h.dtype, np.number) or np.issubdtype(h.dtype, np.complexfloating):
        raise TypeError(f"altitude must be a real number or numeric array, got dtype {h.dtype}")
    h = h.astype(float)
    _check_floor(h)
    if h.ndim == 0:
        return _state_scalar(float(h))
    return _state_array(h)


def pressure_pa(alt_m: AltitudeInput) -> Quantity:
    """Ambient pressure [Pa] at a geometric altitude [m]; see standard_atmosphere."""
    return standard_atmosphere(alt_m).p_pa


def density_kgm3(alt_m: AltitudeInput) -> Quantity:
    """Ambient density [kg/m^3] at a geometric altitude [m]; see standard_atmosphere."""
    return standard_atmosphere(alt_m).rho_kgm3


def speed_of_sound_mps(alt_m: AltitudeInput) -> Quantity:
    """Speed of sound [m/s] at a geometric altitude [m]; see standard_atmosphere."""
    return standard_atmosphere(alt_m).a_mps


__all__ = [
    "AltitudeInput",
    "AtmosphereState",
    "density_kgm3",
    "extension_scale_height_m",
    "pressure_pa",
    "speed_of_sound_mps",
    "standard_atmosphere",
]
