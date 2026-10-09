"""First-order structural sizing of the push load: the sizing primitives (SP7 step S1).

docs/physics.md, "Structural sizing of the push load (first order)"; the approved design
docs/phases/inputs/2026-10-08-SP7-design.md, section 4.2 (modes, domes, increments),
4.2.1 (the dynamic load factor and the ramped plateau), 4.2.3 (the ring frame), D-SP7-14,
D-SP7-16 and D-SP7-17.

A ground push loads the stack with a felt axial load factor n (in units of g0) that the
pad's own flight never reaches at some stations. The structural model (S2) sizes each
station of each tank stage for the pad's envelope and for the push, and charges the mass
of the positive part of the difference. This module holds the closed forms it is built
from, all first order (membrane-level relations for the axisymmetric thin shells):

- the hydrostatic pressure p = p_u + rho n g0 h;
- hoop tension, t = (FS_u p - p_relief) r / (F_tu eta_w) (also the transfer tube's wall),
  the pressure of a pressurized volume on the wall's other side subtracted once,
  unfactored;
- monocoque buckling in axial compression with the SP-8007 knockdown gamma(r/t) and its
  internal-pressure increment Delta_gamma, solved for the wall thickness by brentq;
- the smeared thickness of a stiffened wall from one row of Gerard & Lakshmikantham's
  (1966) Table 2, and the plate-limited alternative (thickness proportional to load);
- the von Mises membrane check of hoop with net axial stress at ultimate (a net external
  pressure carries no hoop stress there, as in the hoop mode);
- a dome sized at its crown and the area of a half oblate spheroid;
- a ring frame between carriage pads, sized for the support moment of a closed ring on
  equally spaced supports;
- the single-mode envelope of the dynamic load factor and the peak it gives;
- the plateau acceleration of a linear ramp that reaches a given exit speed at a given
  stroke;
- the mass increment over an envelope: the positive part of t_push - t_env times a
  non-optimum factor (NOF).

The station model of both stages, the load cases, the envelope over a pad's records, the
flags, the structure file and the coupling to the offload solve arrive in S2 and S3.

Conventions: SI throughout (m, Pa, N, kg, s); a load factor n is in units of g0 and is
converted by ``units.from_g``; a "design" load (``n_design_N``) is at ultimate, already
multiplied by the ultimate factor FS_u and relieved by the caller (NASA-STD-5001B FSR 19
and 53-54: relieving pressure at its minimum, unfactored); thicknesses are >= 0, and a mode
with no demand (a load <= 0, no net internal pressure) sizes 0.0. Inputs outside a
function's domain raise ValueError.

Pressures: every pressure argument (``p_pa``, ``p_ullage_pa``, ``p_stab_pa``,
``p_relief_pa``) is a gauge pressure relative to the ambient pressure outside the vehicle
at the load case's time, never a difference across an inner wall. A wall whose other side
is that ambient (a barrel; an aft or forward dome) is sized from p alone. A wall whose
other side is another pressurized volume (the common dome's RP-1 side; the RP-1 around the
LOX transfer tube) is given that volume's pressure as ``p_relief_pa``, measured from the
same ambient, at its minimum and unfactored (FSR 19), and subtracts it once:
FS_u p - p_relief. Passing p_LOX - p_RP1 as p and p_RP1 again as the relief would count
the relief twice.

Pure: no I/O, no globals, no printing; imports the standard library, constants, units,
numpy and scipy.optimize only.
"""

from __future__ import annotations

import math
import operator
from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike
from scipy.optimize import brentq

from launchsim.constants import SP8007_KNOCKDOWN_A, SP8007_PHI_DIVISOR
from launchsim.units import from_g

type DeltaGammaTable = Sequence[tuple[float, float]]
"""The SP-8007 pressure-increment curve as (x, Delta_gamma) pairs, x = (p/E)(r/t)^2:
x strictly ascending from (0, 0), Delta_gamma non-decreasing; constant beyond the last
point (``delta_gamma``)."""

type DynamicMode = Literal["rise_time", "quasi_static", "step"]
"""How the dynamic load factor is charged (design 4.2.1): the single-mode envelope bound
from a rise time, 1 (quasi-static) or 2 (a step)."""

DYNAMIC_MODES: tuple[DynamicMode, ...] = ("rise_time", "quasi_static", "step")
"""The accepted values of ``dynamic_load_factor``'s mode."""

MONOCOQUE_XTOL_M: float = 1.0e-12
"""brentq's absolute tolerance [m] on the monocoque thickness (design 4.2; review N11):
1e-12 m on a 13 m barrel of r = 1.83 m in 2195 is about 4e-7 kg, far below the offload
bisection's 0.05 kg."""

MONOCOQUE_RTOL: float = 4.0 * float(np.finfo(float).eps)
"""brentq's relative tolerance [-] on the monocoque thickness: scipy's default and the
smallest value brentq accepts, four machine epsilons. With MONOCOQUE_XTOL_M it bounds the
returned estimate x0 of the root t*: |t* - x0| < xtol + rtol |x0| (brentq stops when its
sign-change bracket around x0 is narrower than that), which
``monocoque_buckling_thickness_m`` uses to move a short estimate onto the safe side."""

MONOCOQUE_BRACKET_MARGIN: float = 1.0e-6
"""Relative widening [-] of both ends of the monocoque bracket, t_lo (1 - margin) and
t_hi (1 + margin), so that its sign change survives rounding. Without it, at r/t_hi above
about 3.6e5 (loads below about 0.75 N at r = 1.83 m without the pressure credit), gamma
rounds to exactly 1 - A and N_cr(t_hi) equals N_d to rounding, with either sign. The
margin is ten orders of magnitude above that rounding and moves no root (the root is
unique)."""

POISSON_RATIO_MAX: float = 0.5
"""Poisson's ratio [-] at and above which the buckling functions refuse nu: the isotropic
incompressible limit, the upper bound of a stable isotropic solid (structural metals lie
near 0.3)."""

DLF_QUASI_STATIC: float = 1.0
"""Dynamic load factor [-] of the ``quasi_static`` mode: no overshoot."""

DLF_STEP: float = 2.0
"""Dynamic load factor [-] of a step on an undamped single mode: the ``step`` mode's value
and the cap of the ``rise_time`` bound (a ramp never overshoots more than a step)."""

DOME_AXIS_RATIO_MIN: float = 1.0
"""Smallest dome axis ratio a/b [-]: a hemisphere (a prolate head is not modelled)."""

DOME_AXIS_RATIO_MAX: float = math.sqrt(2.0)
"""Largest dome axis ratio a/b [-] the crown sizing accepts: above sqrt(2) the membrane
hoop stress at the equator, (p a / t)(1 - (a/b)^2 / 2), turns compressive, a mode a crown
check misses (design 4.2; review SP-10)."""

RING_PADS_MIN: int = 3
"""Fewest carriage pads [-] under the ring frame: three point supports are the fewest that
hold a ring against tilting as a rigid body (two leave it free to rotate about the line
through them)."""

NOF_MIN: float = 1.0
"""Smallest non-optimum factor [-]: the ratio of real to ideal mass, so at least 1 (1.0 is
a unit-cell value; the design's coarse-model ranges, Wu 2024, are 1.54-1.9 for barrels and
skirts and 1.28-2.76 for domes)."""


# ------------------------------------------------------------------ input checks


def _require_finite(name: str, value: float) -> float:
    """``value`` as a float, or ValueError when it is not a finite real number."""
    if isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number, got {value!r}")
    return float(value)


def _require_positive(name: str, value: float) -> float:
    """``value`` as a float, or ValueError unless it is finite and > 0."""
    x = _require_finite(name, value)
    if x <= 0.0:
        raise ValueError(f"{name} must be > 0, got {value!r}")
    return x


def _require_non_negative(name: str, value: float) -> float:
    """``value`` as a float, or ValueError unless it is finite and >= 0."""
    x = _require_finite(name, value)
    if x < 0.0:
        raise ValueError(f"{name} must be >= 0, got {value!r}")
    return x


def _require_unit_fraction(name: str, value: float) -> float:
    """``value`` as a float, or ValueError unless 0 < value <= 1 (an efficiency or a
    knockdown)."""
    x = _require_positive(name, value)
    if x > 1.0:
        raise ValueError(f"{name} must be in (0, 1], got {value!r}")
    return x


def _require_strength(fs_ult: float, f_tu_pa: float, eta_weld: float) -> tuple[float, float, float]:
    """(FS_u, F_tu, eta_w) as floats, after checking FS_u > 0, F_tu > 0 and
    0 < eta_w <= 1."""
    fs = _require_positive("fs_ult", fs_ult)
    f_tu = _require_positive("f_tu_pa", f_tu_pa)
    eta = _require_unit_fraction("eta_weld", eta_weld)
    return fs, f_tu, eta


def _require_gerard_pair(c: float, exponent: float) -> tuple[float, float]:
    """(C, n) of a Gerard row as floats, after checking C > 0 and 0 < n <= 1."""
    c_val = _require_positive("c", c)
    n_val = _require_unit_fraction("exponent", exponent)
    return c_val, n_val


def _require_nof(nof: float) -> float:
    """``nof`` as a float, or ValueError unless finite and >= NOF_MIN."""
    x = _require_finite("nof", nof)
    if x < NOF_MIN:
        raise ValueError(f"nof must be >= {NOF_MIN}, got {nof!r}")
    return x


# ------------------------------------------------------------------ Gerard rows


@dataclass(frozen=True)
class GerardRow:
    """One row of Gerard & Lakshmikantham (1966), Table 2: the minimum-weight solidity of an
    axially compressed stiffened cylinder, Sigma = 4 t_bar / d = C (N_x / (E d))^n, with
    t_bar the smeared wall thickness [m], d the diameter [m], N_x the axial load per unit
    circumference [N/m] and E Young's modulus [Pa]. ``name`` labels the construction,
    ``c`` is C [-] and ``exponent`` is n [-]; C and n are a published pair, used together,
    never as independent coefficients (design 4.2; review SP-4)."""

    name: str
    c: float
    exponent: float

    def __post_init__(self) -> None:
        """Refuse a non-positive or non-finite C, or an exponent outside (0, 1]."""
        _require_gerard_pair(self.c, self.exponent)


# Gerard, G. and Lakshmikantham, C., "Optimum Thin-Walled Cylinders under Axial
# Compression", Allied Research Associates TR 292-2 (NASA contract NASw-1174, 1966,
# NTRS 19660015694), Table 2 (PDF p.31, printed p.27): the ring-stiffened rows with
# k_a = 1, which the authors treat as the reliable ones (docs/phases/inputs/
# 2026-10-08-SP7-survey/06-sources-structures.md, section 6). A published table, not
# tunable coefficients.
GERARD_RING_COMMON_Z = GerardRow("ring_common_z", 6.48, 3.0 / 5.0)
"""Ring-stiffened cylinder with common Z stringers (Table 2: C = 6.48, n = 3/5)."""
GERARD_RING_COMMON_Y = GerardRow("ring_common_y", 5.93, 3.0 / 5.0)
"""Ring-stiffened cylinder with common Y stringers (Table 2: C = 5.93, n = 3/5)."""
GERARD_RING_IMPROVED_Z = GerardRow("ring_improved_z", 7.14, 7.0 / 11.0)
"""Ring-stiffened cylinder with improved Z stringers (Table 2: C = 7.14, n = 7/11)."""
GERARD_RING_IMPROVED_Y = GerardRow("ring_improved_y", 6.01, 7.0 / 11.0)
"""Ring-stiffened cylinder with improved Y stringers (Table 2: C = 6.01, n = 7/11)."""
GERARD_ROWS: tuple[GerardRow, ...] = (
    GERARD_RING_COMMON_Z,
    GERARD_RING_COMMON_Y,
    GERARD_RING_IMPROVED_Z,
    GERARD_RING_IMPROVED_Y,
)
"""The four rows the design adopts, in Table 2's order."""


# ------------------------------------------------------------------ pressure and hoop


def hydrostatic_pressure_pa(
    p_ullage_pa: float, rho_kgm3: float, n_g: float, depth_m: float
) -> float:
    """The pressure in a liquid column under a felt axial load factor.

    Inputs: p_ullage_pa, the ullage (gas) pressure above the liquid surface [Pa, gauge
    relative to the ambient outside the vehicle]; rho_kgm3, the liquid density [kg/m^3],
    >= 0; n_g, the felt axial load factor along the stack axis [g0], positive when it
    presses the liquid toward the tank bottom (any sign: a negative n, as after a release,
    lowers the pressure and may make it negative, which the caller reads as a column
    separating); depth_m, the depth of the point below the liquid surface along the stack
    axis [m] (a point above the surface, depth < 0, sees the ullage pressure alone).
    Output: p = p_u + rho n g0 max(depth, 0) [Pa, gauge relative to the same ambient].
    Frame: the stack axis, depth measured from the liquid surface toward the tank bottom.
    """
    p_u = _require_finite("p_ullage_pa", p_ullage_pa)
    rho = _require_non_negative("rho_kgm3", rho_kgm3)
    n = _require_finite("n_g", n_g)
    h = max(_require_finite("depth_m", depth_m), 0.0)
    return p_u + rho * from_g(n) * h


def _design_pressure_pa(p_pa: float, fs: float, p_relief_pa: float) -> float:
    """FS_u p - p_relief [Pa]: the loading pressure factored and the pressure of a
    pressurized volume on the other side of the wall subtracted once, unfactored
    (NASA-STD-5001B FSR 19); both relative to the ambient outside the vehicle."""
    p = _require_finite("p_pa", p_pa)
    relief = _require_non_negative("p_relief_pa", p_relief_pa)
    return fs * p - relief


def hoop_thickness_m(
    p_pa: float,
    radius_m: float,
    fs_ult: float,
    f_tu_pa: float,
    eta_weld: float,
    *,
    p_relief_pa: float = 0.0,
) -> float:
    """The wall thickness a cylinder needs to carry its hoop tension at ultimate.

    Inputs: p_pa, the pressure inside the cylinder [Pa, gauge relative to the ambient
    outside the vehicle], at its maximum expected operating value plus any head (the
    caller's MEOP, unfactored; factored here); radius_m, the mid-surface radius [m];
    fs_ult, the ultimate design factor FS_u [-]; f_tu_pa, the ultimate tensile strength
    F_tu [Pa]; eta_weld, the weld efficiency on the hoop direction eta_w, in (0, 1];
    p_relief_pa (keyword, default 0), the pressure outside the wall when that side is
    another pressurized volume [Pa, gauge relative to the same ambient], >= 0, at its
    minimum, unfactored (FSR 19; the RP-1 around the transfer tube, design 4.2); 0 when
    the outside is the vehicle's ambient itself, as for a barrel.
    Output: t = (FS_u p - p_relief) r / (F_tu eta_w) [m], so FS_u p r / (F_tu eta_w) without
    a relief; 0.0 when FS_u p - p_relief <= 0 (no net hoop tension: an external pressure is
    a buckling or collapse case, not sized here).
    Frame: none (a membrane relation of an axisymmetric shell).
    """
    r = _require_positive("radius_m", radius_m)
    fs, f_tu, eta = _require_strength(fs_ult, f_tu_pa, eta_weld)
    p_design = _design_pressure_pa(p_pa, fs, p_relief_pa)
    if p_design <= 0.0:
        return 0.0
    return p_design * r / (f_tu * eta)


def tube_hoop_thickness_m(
    p_pa: float,
    tube_radius_m: float,
    fs_ult: float,
    f_tu_pa: float,
    eta_weld: float,
    *,
    p_relief_pa: float = 0.0,
) -> float:
    """The hoop thickness of a tube (the LOX transfer tube through the RP-1 tank, design
    4.2): ``hoop_thickness_m`` with the tube's own radius.

    Inputs: p_pa, the pressure inside the tube (the LOX at the tube's bottom, ullage plus
    head, unfactored) [Pa, gauge relative to the ambient outside the vehicle, not to the
    RP-1 around the tube]; tube_radius_m [m]; fs_ult [-], f_tu_pa [Pa], eta_weld [-] as
    ``hoop_thickness_m``; p_relief_pa (keyword, default 0), the RP-1 pressure outside the
    tube [Pa, gauge relative to the same ambient], >= 0, at its minimum, unfactored.
    Output: t = (FS_u p - p_relief) r_tube / (F_tu eta_w) [m]; 0.0 when that is <= 0
    (the tube then sees a net external pressure, a collapse case not sized here).
    Frame: none (a membrane relation of the tube's wall).
    """
    return hoop_thickness_m(p_pa, tube_radius_m, fs_ult, f_tu_pa, eta_weld, p_relief_pa=p_relief_pa)


# ------------------------------------------------------------------ monocoque buckling


def sp8007_knockdown(r_over_t: float) -> float:
    """The SP-8007 knockdown of an unstiffened isotropic cylinder in axial compression.

    Input: r_over_t, the radius over the wall thickness [-], > 0.
    Output: gamma = 1 - A (1 - exp(-sqrt(r/t) / D)) [-], A = SP8007_KNOCKDOWN_A (0.901),
    D = SP8007_PHI_DIVISOR (16); NASA SP-8007 (1968) Eq. 5, NASA/SP-8007-2020/REV 2
    Eq. 9-10, stated there for r/t < 1500 as a lower bound to test data (r/t beyond 1500
    is evaluated by the same formula, not refused). Between 1 - A = 0.099 and 1, and
    decreasing in r/t.
    Frame: none.
    """
    rt = _require_positive("r_over_t", r_over_t)
    phi = math.sqrt(rt) / SP8007_PHI_DIVISOR
    # 1 - A (1 - e^-phi) = 1 + A (e^-phi - 1), with expm1 for a small phi
    return 1.0 + SP8007_KNOCKDOWN_A * math.expm1(-phi)


def _dgamma_points(table: DeltaGammaTable) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """The table's (x, Delta_gamma) columns, after checking that it has at least two
    points, starts at (0, 0), has finite values, strictly ascending x and non-decreasing
    Delta_gamma; ValueError otherwise."""
    pairs = [tuple(p) for p in table]
    if len(pairs) < 2 or any(len(p) != 2 for p in pairs):
        raise ValueError("a Delta_gamma table needs at least two (x, Delta_gamma) pairs")
    xs = tuple(_require_finite("Delta_gamma table x", p[0]) for p in pairs)
    ys = tuple(_require_finite("Delta_gamma table value", p[1]) for p in pairs)
    if xs[0] != 0.0 or ys[0] != 0.0:
        raise ValueError(f"a Delta_gamma table must start at (0, 0), got {pairs[0]!r}")
    for i in range(len(xs) - 1):
        if not xs[i + 1] > xs[i]:
            raise ValueError(f"Delta_gamma table x must be strictly ascending at {xs[i + 1]!r}")
        if ys[i + 1] < ys[i]:
            raise ValueError(
                f"Delta_gamma table values must be non-decreasing at x = {xs[i + 1]!r}"
            )
    return xs, ys


def _check_dgamma_chords(xs: Sequence[float], ys: Sequence[float]) -> None:
    """ValueError unless the chord slope Delta_gamma(x)/x is non-increasing in x, i.e.
    y[i+1] x[i] <= y[i] x[i+1] at every vertex with x[i] > 0. Every segment's line then
    meets x = 0 at or above 0, which keeps t^2 Delta_gamma((p/E)(r/t)^2) non-decreasing
    in t (``monocoque_buckling_load_N``)."""
    for i in range(1, len(xs) - 1):
        if ys[i + 1] * xs[i] > ys[i] * xs[i + 1]:
            raise ValueError(
                "the Delta_gamma table's chord slope Delta_gamma(x)/x must not increase "
                f"with x (it does between x = {xs[i]!r} and {xs[i + 1]!r}): the buckling "
                "load would then not be monotone in t"
            )


def _interp(x: float, xs: Sequence[float], ys: Sequence[float]) -> float:
    """Piecewise-linear interpolation of (xs, ys) at x >= 0, exact at the table points and
    constant beyond the last point (inputs checked by the caller)."""
    if x >= xs[-1]:
        return ys[-1]
    i = bisect_right(xs, x) - 1  # xs[i] <= x < xs[i + 1]
    x0, x1, y0, y1 = xs[i], xs[i + 1], ys[i], ys[i + 1]
    return y0 + (y1 - y0) * ((x - x0) / (x1 - x0))


def delta_gamma(x: float, table: DeltaGammaTable) -> float:
    """The SP-8007 increment of the buckling coefficient from internal pressure.

    Inputs: x = (p/E)(r/t)^2 [-], >= 0 (p the stabilizing internal pressure at its minimum,
    unfactored, E Young's modulus, r/t the radius over the thickness); table, the digitized
    curve of NASA SP-8007 (1968) Fig. 6 / NASA/SP-8007-2020/REV 2 Fig. 4-5 (for use with
    the 2020 edition's Eq. 48-49 only) as (x, Delta_gamma) pairs: x strictly ascending from
    (0, 0), Delta_gamma non-decreasing.
    Output: Delta_gamma [-] by piecewise-linear interpolation (monotone; exact at the
    table's points), constant at the last value beyond the last point.
    Frame: none.
    """
    xs, ys = _dgamma_points(table)
    xv = _require_non_negative("x", x)
    return _interp(xv, xs, ys)


def _poisson_factor(nu: float) -> float:
    """sqrt(3 (1 - nu^2)) [-] of the classical buckling stress, after checking
    0 <= nu < POISSON_RATIO_MAX."""
    v = _require_non_negative("nu", nu)
    if v >= POISSON_RATIO_MAX:
        raise ValueError(f"nu must be in [0, {POISSON_RATIO_MAX}), got {nu!r}")
    return math.sqrt(3.0 * (1.0 - v * v))


def _require_s_dg(s_dg: float) -> float:
    """``s_dg`` as a float, or ValueError unless 0 <= s_dg <= 1."""
    s = _require_non_negative("s_dg", s_dg)
    if s > 1.0:
        raise ValueError(f"s_dg must be in [0, 1], got {s_dg!r}")
    return s


def _monocoque_inputs(
    radius_m: float,
    e_pa: float,
    nu: float,
    p_stab_pa: float,
    s_dg: float,
    dgamma_table: DeltaGammaTable,
) -> tuple[float, float, float, float, float, tuple[float, ...], tuple[float, ...]]:
    """Checked (r, E, sqrt(3(1 - nu^2)), p, s_dg, xs, ys) of the monocoque functions."""
    r = _require_positive("radius_m", radius_m)
    e = _require_positive("e_pa", e_pa)
    k3 = _poisson_factor(nu)
    p = _require_non_negative("p_stab_pa", p_stab_pa)
    s = _require_s_dg(s_dg)
    xs, ys = _dgamma_points(dgamma_table)
    _check_dgamma_chords(xs, ys)
    return r, e, k3, p, s, xs, ys


def _monocoque_load(
    t: float,
    r: float,
    e: float,
    k3: float,
    p: float,
    s: float,
    xs: Sequence[float],
    ys: Sequence[float],
) -> float:
    """2 pi E t^2 (gamma(r/t)/k3 + s Delta_gamma((p/E)(r/t)^2)) [N] for checked inputs."""
    r_over_t = r / t
    term = sp8007_knockdown(r_over_t) / k3
    if s > 0.0 and p > 0.0:
        term += s * _interp((p / e) * r_over_t * r_over_t, xs, ys)
    return 2.0 * math.pi * e * t * t * term


def monocoque_buckling_load_N(
    t_m: float,
    radius_m: float,
    e_pa: float,
    nu: float,
    p_stab_pa: float,
    s_dg: float,
    dgamma_table: DeltaGammaTable,
) -> float:
    """The axial buckling load of a pressurized monocoque cylinder, without the pressure's
    own end load (SP-8007-2020 Eq. 48's p pi r^2 term is the relief the caller subtracts
    from the design load instead).

    Inputs: t_m, the wall thickness [m], > 0; radius_m [m]; e_pa, Young's modulus [Pa];
    nu, Poisson's ratio [-] in [0, 0.5); p_stab_pa, the stabilizing internal pressure at
    its minimum, unfactored [Pa, gauge relative to the ambient outside the vehicle, the
    barrel's outside], >= 0; s_dg, the weight of the pressure increment
    [-] in [0, 1] (the structure file's switch, 0 or 1); dgamma_table, the Delta_gamma
    curve (``delta_gamma``), whose chord slope Delta_gamma(x)/x must not increase with x.
    Output: N_cr(t) = 2 pi E t^2 (gamma(r/t) / sqrt(3 (1 - nu^2)) + s_dg Delta_gamma(
    (p/E)(r/t)^2)) [N] (NASA SP-8007 (1968) Eq. 5 and section 4.2.5.4; NASA/SP-8007-2020/
    REV 2 Eq. 9-10 and 48-49).
    Monotone: strictly increasing in t. The first term grows because t^2 grows and gamma
    rises as r/t falls; the second is s c Delta_gamma(y)/y with c = p r^2 / E and
    y = c/t^2 falling in t, and the table's chord condition makes Delta_gamma(y)/y
    non-increasing in y, so the term does not fall as t grows.
    Frame: none (a cylinder of radius r).
    """
    r, e, k3, p, s, xs, ys = _monocoque_inputs(radius_m, e_pa, nu, p_stab_pa, s_dg, dgamma_table)
    t = _require_positive("t_m", t_m)
    return _monocoque_load(t, r, e, k3, p, s, xs, ys)


def monocoque_bracket_m(
    n_design_N: float, e_pa: float, nu: float, s_dg: float, dgamma_table: DeltaGammaTable
) -> tuple[float, float]:
    """The bracket [t_lo, t_hi] of the monocoque root solve.

    Inputs: n_design_N, the net design compression N_d [N], > 0; e_pa [Pa]; nu [-] in
    [0, 0.5); s_dg [-] in [0, 1]; dgamma_table (``delta_gamma``).
    Output: (t_lo, t_hi) [m] with N_cr(t_lo) < N_d < N_cr(t_hi) for every radius and
    stabilizing pressure: gamma <= 1 and Delta_gamma <= its last value g_max give
    N_cr(t) <= 2 pi E t^2 (1/k3 + s_dg g_max), and gamma >= 1 - A and Delta_gamma >= 0
    give N_cr(t) >= 2 pi E t^2 (1 - A)/k3, so the two roots of those bounds,
    sqrt(N_d / (2 pi E (1/k3 + s_dg g_max))) and sqrt(N_d k3 / (2 pi E (1 - A))), bracket
    the root; k3 = sqrt(3 (1 - nu^2)), A = SP8007_KNOCKDOWN_A. Each end is then moved
    outward by the relative MONOCOQUE_BRACKET_MARGIN (1e-6): t_lo = (1 - margin) times the
    first, t_hi = (1 + margin) times the second, so the inequalities are strict by about
    2e-6 relative and survive rounding. (The bounds alone fail in floating point at small
    loads: at r/t_hi above about 3.6e5 gamma rounds to exactly 1 - A.) t_hi / t_lo is
    below 4 for nu = 0.33 and s_dg g_max <= 0.25.
    Frame: none.
    """
    n = _require_positive("n_design_N", n_design_N)
    e = _require_positive("e_pa", e_pa)
    k3 = _poisson_factor(nu)
    s = _require_s_dg(s_dg)
    _, ys = _dgamma_points(dgamma_table)
    return _bracket(n, e, k3, s, ys[-1])


def _bracket(n: float, e: float, k3: float, s: float, g_max: float) -> tuple[float, float]:
    """(t_lo, t_hi) [m] of ``monocoque_bracket_m`` for checked inputs, the margin applied."""
    t_lo = math.sqrt(n / (2.0 * math.pi * e * (1.0 / k3 + s * g_max)))
    t_hi = math.sqrt(n * k3 / (2.0 * math.pi * e * (1.0 - SP8007_KNOCKDOWN_A)))
    return t_lo * (1.0 - MONOCOQUE_BRACKET_MARGIN), t_hi * (1.0 + MONOCOQUE_BRACKET_MARGIN)


def monocoque_buckling_thickness_m(
    n_design_N: float,
    radius_m: float,
    e_pa: float,
    nu: float,
    p_stab_pa: float,
    s_dg: float,
    dgamma_table: DeltaGammaTable,
) -> float:
    """The monocoque wall thickness whose axial buckling load equals the design compression.

    Inputs: n_design_N, the net design compression N_d = FS_u N - p_min pi r^2 [N]
    (ultimate, relieved by the caller with the tank's minimum pressure, unfactored;
    NASA-STD-5001B FSR 19 and 53-54); radius_m [m]; e_pa [Pa]; nu [-]; p_stab_pa, the
    minimum (stabilizing) internal pressure, unfactored [Pa, gauge relative to the ambient
    outside the vehicle] (design 4.2: Delta_gamma is evaluated at p_min only); s_dg [-] in
    [0, 1]; dgamma_table (``delta_gamma``; its chord slope must not increase with x).
    Output: a wall t [m] at or just above the root t* of N_cr(t) = N_d
    (``monocoque_buckling_load_N``), so N_cr(t) >= N_d always. The root is unique and is
    the smallest t with N_cr(t) >= N_d because N_cr is continuous and strictly increasing
    in t. brentq on ``monocoque_bracket_m``'s bracket (xtol MONOCOQUE_XTOL_M = 1e-12 m,
    rtol MONOCOQUE_RTOL = 4 machine epsilons) returns an estimate x0 with
    |t* - x0| < delta = xtol + rtol x0 on either side; it is short of the root
    (N_cr(x0) < N_d) in most solves. A short x0 (x0 < t*) is raised by delta, which puts
    it at or above t*; an x0 that is not short is at or above t* already. So
    0 <= t - t* < delta (about 1e-12 m), and 0 <= N_cr(t) / N_d - 1 < 2.56 delta / t
    (about 2.6e-12 m / t): d ln N_cr / d ln t is at most 2.5534, the unpressurized wall's
    maximum at r/t of about 1,140, and the pressure term's is in [0, 2]. Measured on
    6,600 solves (N_d 1e3-5e7 N at r = 1.83 m, p_min 0-2 MPa, s_dg 0 and 1, walls
    0.08-17 mm): 85% raised, and the excess up to 2.4e-9 at walls of 1 mm and more and
    1.5e-10 at 17 mm; the mass is below 1e-6 kg on a 13 m barrel. RuntimeError if the
    raised x0 is still short (brentq's bound broken). 0.0 when N_d <= 0 (no net
    compression).
    Frame: none (a cylinder of radius r).
    """
    r, e, k3, p, s, xs, ys = _monocoque_inputs(radius_m, e_pa, nu, p_stab_pa, s_dg, dgamma_table)
    n = _require_finite("n_design_N", n_design_N)
    if n <= 0.0:
        return 0.0
    t_lo, t_hi = _bracket(n, e, k3, s, ys[-1])

    def excess(t: float) -> float:
        return _monocoque_load(t, r, e, k3, p, s, xs, ys) - n

    t = float(brentq(excess, t_lo, t_hi, xtol=MONOCOQUE_XTOL_M, rtol=MONOCOQUE_RTOL))
    if excess(t) >= 0.0:
        return t
    raised = t + MONOCOQUE_XTOL_M + MONOCOQUE_RTOL * t
    if excess(raised) < 0.0:
        raise RuntimeError(
            f"monocoque solve: N_cr({raised!r} m) is still below N_d = {n!r} N after "
            "raising brentq's estimate by its tolerance"
        )
    return raised


# ------------------------------------------------------------------ stiffened walls


def gerard_stiffened_thickness_m(
    n_design_N: float, radius_m: float, e_pa: float, knockdown: float, c: float, exponent: float
) -> float:
    """The smeared wall thickness of a minimum-weight stiffened cylinder in axial
    compression (Gerard & Lakshmikantham 1966, Eq. 32 with Table 2).

    Inputs: n_design_N, the net design compression N_d [N] (ultimate, relieved by the
    caller; none for an unpressurized skirt); radius_m [m]; e_pa, Young's modulus [Pa];
    knockdown, the stiffened-shell knockdown k_s [-] in (0, 1], applied to the load (the
    table's weights are perfect-theory values); c and exponent, one row's C [-] and n [-]
    (a ``GerardRow``'s pair).
    Output: t_bar = (d/4) C (N_x / (k_s E d))^n [m] with d = 2 r and N_x = N_d/(2 pi r)
    [N/m]: the solidity 4 t_bar / d of Eq. 32 at the knocked-down load; 0.0 when N_d <= 0.
    Frame: none (a cylinder of radius r).
    """
    n = _require_finite("n_design_N", n_design_N)
    r = _require_positive("radius_m", radius_m)
    e = _require_positive("e_pa", e_pa)
    k_s = _require_unit_fraction("knockdown", knockdown)
    c_val, n_exp = _require_gerard_pair(c, exponent)
    if n <= 0.0:
        return 0.0
    d = 2.0 * r
    n_x = n / (2.0 * math.pi * r)
    return (d / 4.0) * c_val * (n_x / (k_s * e * d)) ** n_exp


def plate_limited_thickness_m(n_design_N: float, n_ref_N: float, t_ref_m: float) -> float:
    """The plate-limited alternative of a stiffened wall: thickness proportional to the
    load, anchored at a reference (design 4.2: the envelope load; Lovejoy et al. 2010
    found optimized 2195 orthogrid weights rising as N^0.90-1.00, which they attribute to
    the plate-thickness limit).

    Inputs: n_design_N, the net design compression N_d [N]; n_ref_N, the anchor's load
    N_ref [N], > 0; t_ref_m, the anchor's thickness t_ref [m], >= 0.
    Output: t = t_ref N_d / N_ref [m]; 0.0 when N_d <= 0.
    Frame: none.
    """
    n = _require_finite("n_design_N", n_design_N)
    n_ref = _require_positive("n_ref_N", n_ref_N)
    t_ref = _require_non_negative("t_ref_m", t_ref_m)
    if n <= 0.0:
        return 0.0
    return t_ref * n / n_ref


# ------------------------------------------------------------------ combined membrane


def von_mises_thickness_m(
    p_pa: float, radius_m: float, n_design_N: float, fs_ult: float, f_tu_pa: float, eta_weld: float
) -> float:
    """The smallest barrel wall thickness whose von Mises membrane stress of hoop and net
    axial stress at ultimate stays within F_tu eta_w (design 4.2, D-SP7-14; review SP-3).

    Inputs: p_pa, the internal pressure at the barrel station (MEOP plus head, unfactored;
    factored here by FS_u) [Pa, gauge relative to the ambient outside the vehicle, which is
    the barrel's outside, so there is no relief term]; radius_m [m]; n_design_N, the net
    design compression N_d [N], positive in compression, already factored and relieved by
    the caller (a negative N_d is a net axial tension and is used as given); fs_ult [-];
    f_tu_pa [Pa]; eta_weld [-] in (0, 1].
    Output: with A = FS_u max(p, 0) r and B = -N_d/(2 pi r) the hoop and axial membrane
    stress resultants [N/m] (s_h = A/t, s_x = B/t), the closed form t = sqrt(A^2 - A B +
    B^2) / (F_tu eta_w) [m] of sqrt(s_h^2 - s_h s_x + s_x^2) <= F_tu eta_w: a compressive
    axial stress (B < 0) under hoop tension (A > 0) raises the combined stress.
    A net external pressure (p < 0) is clamped to A = 0, as ``hoop_thickness_m`` sizes it
    0: hoop compression is an external-pressure buckling or collapse case, not sized here,
    and a factored compressive hoop stress would lower the von Mises stress of a net axial
    compression, crediting a factored load against FSR 19. The combination of a net
    external pressure with a net axial tension, where hoop compression would raise the
    combined stress, is therefore not sized either (in the design it arises only in the
    release swing, a flagged check, design 4.2.2). Limits: B = 0 gives
    ``hoop_thickness_m`` without a relief for every p (FS_u p r / (F_tu eta_w), 0 for
    p <= 0); A = 0 (p <= 0) gives |B| / (F_tu eta_w).
    Frame: none (membrane stresses of a cylinder of radius r; x axial, h hoop).
    """
    p = _require_finite("p_pa", p_pa)
    r = _require_positive("radius_m", radius_m)
    n = _require_finite("n_design_N", n_design_N)
    fs, f_tu, eta = _require_strength(fs_ult, f_tu_pa, eta_weld)
    a = fs * max(p, 0.0) * r
    b = -n / (2.0 * math.pi * r)
    return math.sqrt(a * a - a * b + b * b) / (f_tu * eta)


# ------------------------------------------------------------------ domes


def _require_axis_ratio(axis_ratio: float, upper: float | None) -> float:
    """``axis_ratio`` as a float, or ValueError unless finite, >= DOME_AXIS_RATIO_MIN and,
    when ``upper`` is given, <= upper."""
    k = _require_finite("axis_ratio", axis_ratio)
    if k < DOME_AXIS_RATIO_MIN or (upper is not None and k > upper):
        bound = (
            f"[{DOME_AXIS_RATIO_MIN}, {upper!r}]"
            if upper is not None
            else f">= {DOME_AXIS_RATIO_MIN}"
        )
        raise ValueError(f"axis_ratio must be {bound}, got {axis_ratio!r}")
    return k


def dome_crown_thickness_m(
    p_pa: float,
    radius_m: float,
    axis_ratio: float,
    fs_ult: float,
    f_tu_pa: float,
    eta_weld: float,
    *,
    p_relief_pa: float = 0.0,
) -> float:
    """The membrane thickness of an oblate spheroidal dome, sized at its crown.

    Inputs: p_pa, the pressure on the dome's concave side at the crown (ullage plus head,
    unfactored; factored here) [Pa, gauge relative to the ambient outside the vehicle];
    p_relief_pa (keyword, default 0), the pressure on its convex side when that side is
    another tank [Pa, gauge relative to the same ambient], >= 0, at its minimum,
    unfactored (FSR 19: the RP-1 tank's minimum pressure under the common dome, design
    4.2; review SP-10); 0 when the convex side is the vehicle's ambient (an aft or forward
    dome); radius_m, the equatorial radius a = the barrel radius [m];
    axis_ratio, a/b [-] in [1, sqrt(2)] (b the dome's height; 1 is a hemisphere; above
    sqrt(2) the equator's hoop stress turns compressive, which a crown check misses, so it
    is refused); fs_ult [-]; f_tu_pa [Pa]; eta_weld [-] in (0, 1].
    Output: t = (FS_u p - p_relief) a k_d / (F_tu eta_w) [m] with k_d = (a/b)/2: the crown's
    radius of curvature is a^2/b and its membrane stress p a^2 / (2 b t); 0.0 when
    FS_u p - p_relief <= 0 (a reverse pressure is a buckling case, flagged by the station
    model, not sized here).
    Frame: none (an axisymmetric head).
    """
    a = _require_positive("radius_m", radius_m)
    k = _require_axis_ratio(axis_ratio, DOME_AXIS_RATIO_MAX)
    fs, f_tu, eta = _require_strength(fs_ult, f_tu_pa, eta_weld)
    p_design = _design_pressure_pa(p_pa, fs, p_relief_pa)
    if p_design <= 0.0:
        return 0.0
    return p_design * a * (k / 2.0) / (f_tu * eta)


def spheroid_head_area_m2(radius_m: float, axis_ratio: float) -> float:
    """The surface area of a half oblate spheroid (a dome).

    Inputs: radius_m, the equatorial semi-axis a [m]; axis_ratio, a/b [-] >= 1 (b = a /
    axis_ratio the polar semi-axis; the formula holds for any oblate head, so only a/b < 1,
    a prolate head, is refused).
    Output: A = pi a^2 + (pi b^2 / (2 e)) ln((1 + e)/(1 - e)) [m^2], e = sqrt(1 - b^2/a^2)
    the eccentricity (half the standard oblate-spheroid area, the surface of revolution of
    the ellipse about its minor axis; derived in docs/physics.md), evaluated as
    pi a^2 + pi b^2 atanh(e)/e; the hemisphere's 2 pi a^2 at a/b = 1 (the limit of
    atanh(e)/e -> 1).
    Frame: none.
    """
    a = _require_positive("radius_m", radius_m)
    k = _require_axis_ratio(axis_ratio, None)
    b = a / k
    e = math.sqrt(1.0 - 1.0 / (k * k))
    if e == 0.0:
        return 2.0 * math.pi * a * a
    return math.pi * a * a + math.pi * b * b * math.atanh(e) / e


# ------------------------------------------------------------------ load entry


def ring_frame_mass_kg(
    f_peak_N: float,
    radius_m: float,
    n_pads: int,
    aspect_h_over_b: float,
    fs_ult: float,
    f_tu_pa: float,
    fitting_factor: float,
    rho_kgm3: float,
) -> float:
    """The mass of a ring frame at the stage base that carries the push from N_p equally
    spaced carriage pads into the aft skirt (design 4.2.3, D-SP7-17).

    Inputs: f_peak_N, the peak push force through the pads [N] (limit; factored here by
    FS_u and the fitting factor); radius_m, the ring radius r [m]; n_pads, the number of
    pads N_p, an integer >= RING_PADS_MIN (3): a Python or numpy integer, not a bool or a
    float; aspect_h_over_b, the section's depth over its width k [-]; fs_ult [-];
    f_tu_pa [Pa]; fitting_factor [-], > 0; rho_kgm3, the ring material's density [kg/m^3].
    Output: the ring as a closed thin ring on N_p equally spaced point supports under the
    skirt's uniform reaction q = F / (2 pi r) [N/m], loaded normal to its plane. With
    alpha = pi / N_p (each span subtends 2 alpha), symmetry about the planes through the
    pads and through the midspans makes it statically determinate, and its bending moment
    at the pads is M = q r^2 (1 - alpha cot alpha) [N m] (docs/physics.md derives it). It
    tends to the straight continuous beam's interior-span support moment q l^2 / 12,
    l = 2 pi r / N_p (design 4.2.3), as N_p grows and exceeds it by 1.0% at 8 pads and
    8.2% at 3. The torsion is not checked: it vanishes at the pads and peaks in the span,
    where the bending moment is zero, at 0.076 M (8 pads) to 0.209 M (3 pads). The
    required (elastic) section modulus Z = FS_u f_fit M / F_tu [m^3], no plastic shape
    factor credited; a solid rectangle b x h with h = k b has Z = k^2 b^3 / 6 and area
    k b^2, so b = (6 Z / k^2)^(1/3); mass = 2 pi r rho k b^2 [kg], the ideal mass before
    the non-optimum factor: the caller multiplies it by the barrels' NOF (design 4.2.3).
    No envelope credit (new hardware). 0.0 when F <= 0.
    Frame: none (the ring's own plane; the load acts along the stack axis).
    """
    f = _require_finite("f_peak_N", f_peak_N)
    r = _require_positive("radius_m", radius_m)
    pads = _require_pad_count(n_pads)
    k = _require_positive("aspect_h_over_b", aspect_h_over_b)
    fs = _require_positive("fs_ult", fs_ult)
    f_tu = _require_positive("f_tu_pa", f_tu_pa)
    fit = _require_positive("fitting_factor", fitting_factor)
    rho = _require_positive("rho_kgm3", rho_kgm3)
    if f <= 0.0:
        return 0.0
    circumference = 2.0 * math.pi * r
    q = f / circumference
    alpha = math.pi / pads
    moment = q * r * r * (1.0 - alpha / math.tan(alpha))
    z = fs * fit * moment / f_tu
    b = (6.0 * z / (k * k)) ** (1.0 / 3.0)
    return circumference * rho * k * b * b


def _require_pad_count(n_pads: int) -> int:
    """``n_pads`` as an int, or ValueError unless it is an integer (a Python or numpy
    integer; a bool, a float or anything else without ``__index__`` is refused) and
    >= RING_PADS_MIN."""
    message = f"n_pads must be an integer >= {RING_PADS_MIN}, got {n_pads!r}"
    if isinstance(n_pads, (bool, np.bool_)):
        raise ValueError(message)
    try:
        pads = operator.index(n_pads)
    except TypeError:
        raise ValueError(message) from None
    if pads < RING_PADS_MIN:
        raise ValueError(message)
    return pads


# ------------------------------------------------------------------ dynamics


def dynamic_load_factor(t_rise_s: float, period_s: float, mode: DynamicMode) -> float:
    """The dynamic load factor (DLF) applied to the push's increment over its resting load
    (design 4.2.1, D-SP7-16).

    Inputs: t_rise_s, the force rise time t_r [s], >= 0 (a linear ramp from the resting to
    the plateau load); period_s, the assumed first axial period T = 1/f [s], > 0; mode,
    one of DYNAMIC_MODES.
    Output [-]: ``rise_time``: the undamped single-mode envelope bound of a ramp-step,
    min(DLF_STEP, 1 + T/(pi t_r)): the exact peak 1 + |sin(pi t_r/T)|/(pi t_r/T) (the
    classical rise-time result, Biggs 1964; derived in docs/physics.md) with |sin| <= 1, so
    it never credits the zeros of the exact response at integer t_r/T; DLF_STEP (2) at
    t_r = 0; ``quasi_static``: DLF_QUASI_STATIC (1); ``step``: DLF_STEP (2).
    Damping is not credited. The single-mode value is not conservative at the upper
    stations of a multi-mass stack for short rise times (design 4.2.1; review SP-7).
    Frame: none.
    """
    if mode not in DYNAMIC_MODES:
        raise ValueError(f"mode must be one of {DYNAMIC_MODES}, got {mode!r}")
    t_r = _require_non_negative("t_rise_s", t_rise_s)
    period = _require_positive("period_s", period_s)
    if mode == "quasi_static":
        return DLF_QUASI_STATIC
    if mode == "step" or t_r == 0.0:
        return DLF_STEP
    return min(DLF_STEP, 1.0 + period / (math.pi * t_r))


def peak_load(n_quasi: float, n_rest: float, dlf: float) -> float:
    """The peak of a load that moves from a resting value to a quasi-static value with a
    dynamic overshoot (design 4.2.1).

    Inputs: n_quasi, the quasi-static (plateau) load; n_rest, the resting load before the
    change (the same unit: g0 for a load factor, N for a force); dlf, the dynamic load
    factor [-], >= 1.
    Output: n_rest + dlf (n_quasi - n_rest), in the unit of the inputs. A drop
    (n_quasi < n_rest, such as a release) swings below n_quasi by the same rule: with
    dlf = 2, to n_quasi - (n_rest - n_quasi).
    Frame: none.
    """
    n_q = _require_finite("n_quasi", n_quasi)
    n_0 = _require_finite("n_rest", n_rest)
    factor = _require_finite("dlf", dlf)
    if factor < DLF_QUASI_STATIC:
        raise ValueError(f"dlf must be >= {DLF_QUASI_STATIC}, got {dlf!r}")
    return n_0 + factor * (n_q - n_0)


def ramped_plateau_accel_mps2(stroke_m: float, exit_speed_mps: float, t_rise_s: float) -> float:
    """The plateau of a net acceleration that ramps linearly from 0 over t_r and then stays
    constant, chosen so the push reaches the exit speed at the end of the stroke (design
    4.2.1; review SP-8).

    Inputs: stroke_m, the stroke L [m], > 0; exit_speed_mps, the exit speed v_e [m/s],
    >= 0; t_rise_s, the ramp time t_r [s], >= 0. Starts from rest.
    Output: a' [m/s^2]. The ramp ends at v_r = a' t_r / 2 and s_r = a' t_r^2 / 6, and the
    plateau gives v_e^2 = v_r^2 + 2 a' (L - s_r) = 2 a' L - a'^2 t_r^2 / 12, whose smaller
    root is a' = [L - sqrt(L^2 - v_e^2 t_r^2 / 12)] / (t_r^2 / 12), evaluated in the
    equivalent form v_e^2 / (L + sqrt(L^2 - v_e^2 t_r^2 / 12)) (no cancellation; exactly
    v_e^2 / (2 L) at t_r = 0). Refused when L^2 < v_e^2 t_r^2 / 12 (no real root) or when
    the ramp does not finish within the stroke (s_r > L, which happens for v_e t_r > 3 L).
    Frame: along the track (net acceleration, gravity and drag already netted out).
    """
    length = _require_positive("stroke_m", stroke_m)
    v_e = _require_non_negative("exit_speed_mps", exit_speed_mps)
    t_r = _require_non_negative("t_rise_s", t_rise_s)
    deficit = v_e * v_e * t_r * t_r / 12.0
    disc = length * length - deficit
    if disc < 0.0:
        raise ValueError(
            f"no ramped plateau reaches {v_e!r} m/s in {length!r} m with t_rise {t_r!r} s "
            "(L^2 < v_e^2 t_r^2 / 12)"
        )
    plateau = v_e * v_e / (length + math.sqrt(disc))
    s_ramp = plateau * t_r * t_r / 6.0
    if s_ramp > length:
        raise ValueError(
            f"the ramp of {t_r!r} s does not finish within the {length!r} m stroke "
            f"(s_r = {s_ramp!r} m)"
        )
    return plateau


# ------------------------------------------------------------------ increments


def barrel_increment_kg(
    t_push_m: ArrayLike,
    t_env_m: ArrayLike,
    station_lengths_m: ArrayLike,
    radius_m: float,
    rho_kgm3: float,
    nof: float,
) -> float:
    """The mass a barrel adds when the push needs a thicker wall than its envelope.

    Inputs: t_push_m and t_env_m, the push's and the envelope's thickness at each station
    [m], >= 0; station_lengths_m, each station's length dz [m], >= 0 (all three the same
    shape); radius_m [m]; rho_kgm3, the wall material's density [kg/m^3]; nof, the
    non-optimum factor [-], >= NOF_MIN.
    Output: NOF sum over stations of 2 pi r rho dz max(0, t_push - t_env) [kg]: only the
    positive parts count, so a push inside the envelope adds exactly 0.0.
    Frame: the stations along the stack axis (their order does not matter here).
    """
    t_push = np.asarray(t_push_m, dtype=float)
    t_env = np.asarray(t_env_m, dtype=float)
    dz = np.asarray(station_lengths_m, dtype=float)
    if not (t_push.shape == t_env.shape == dz.shape):
        raise ValueError(
            "t_push_m, t_env_m and station_lengths_m must have the same shape, got "
            f"{t_push.shape}, {t_env.shape} and {dz.shape}"
        )
    for name, arr in (("t_push_m", t_push), ("t_env_m", t_env), ("station_lengths_m", dz)):
        if not np.all(np.isfinite(arr)) or np.any(arr < 0.0):
            raise ValueError(f"{name} must be finite and >= 0")
    r = _require_positive("radius_m", radius_m)
    rho = _require_positive("rho_kgm3", rho_kgm3)
    factor = _require_nof(nof)
    excess = np.maximum(t_push - t_env, 0.0)
    return float(factor * 2.0 * math.pi * r * rho * np.sum(dz * excess))


def area_increment_kg(
    t_push_m: float, t_env_m: float, area_m2: float, rho_kgm3: float, nof: float
) -> float:
    """The mass a dome or the transfer tube adds when the push needs a thicker wall than its
    envelope.

    Inputs: t_push_m and t_env_m, the push's and the envelope's thickness [m], >= 0;
    area_m2, the element's area [m^2], >= 0 (``spheroid_head_area_m2`` for a dome);
    rho_kgm3 [kg/m^3]; nof [-], >= NOF_MIN.
    Output: NOF area rho max(0, t_push - t_env) [kg]; exactly 0.0 inside the envelope.
    Frame: none.
    """
    t_push = _require_non_negative("t_push_m", t_push_m)
    t_env = _require_non_negative("t_env_m", t_env_m)
    area = _require_non_negative("area_m2", area_m2)
    rho = _require_positive("rho_kgm3", rho_kgm3)
    factor = _require_nof(nof)
    return factor * area * rho * max(0.0, t_push - t_env)
