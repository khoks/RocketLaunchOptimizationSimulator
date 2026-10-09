"""First-order structural sizing of the push load: the sizing primitives (SP7 step S1) and
the station model of both stages (SP7 step S2).

docs/physics.md, "Structural sizing of the push load (first order)"; the approved design
docs/phases/inputs/2026-10-08-SP7-design.md, section 4.2 (modes, domes, increments),
4.2.1 (the dynamic load factor and the ramped plateau), 4.2.2 (the flags), 4.2.3 (the
ring frame and the thrust-structure row), 4.2.4 (stage 2 and the interstage), 4.2.5 (the
plausibility rule), D-SP7-14 to D-SP7-17, D-SP7-33, D-SP7-36 and D-SP7-37; the source note
docs/phases/inputs/2026-10-08-SP7-sources.md (the values, the station placement of masses,
the ring's torsion-and-shear check of its section 11).

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

Step S2 adds the station model built on them: one resolved coefficient set
(``StructureCoefficients``, SI), the layout of both stages (``StackLayout``) and their
station geometry (``build_geometry``, built once from the full-load vehicle's masses), the
load cases (``LoadCase``; ``PushLoad`` for a push, built by sim.py's adapters), the pad's
envelope (``pad_load_set``, ``build_envelope``; ``envelope_reference`` is the full-sample
definition it equals), the push requirement with its dynamic load factor
(``push_requirement``), the increment (``size_increment``; ``size`` builds a fresh
geometry and envelope and sizes, the search's one call), the flags of design 4.2.2, the
ring's torsion-and-shear check (``ring_frame_section``), the interstage and
thrust-structure rows and the plausibility rule (``plausibility``, ``widen_band``). The
structure file and its conversion live in config.py, the Result adapters in sim.py, and
the coupling to the offload solve arrives in S3.

The screened search (S2, source note section 9.3) is pure too: ``band_search`` (design
4.2.6 steps 1-4: the tornado, the scans, step 3's enumeration, the polish of D-SP7-38 and
the extremality checks: the seeded samples and a one-coordinate check), ``stage2_search``
(search B), ``outer_search`` (search C, the design axes' two corners) and
``screened_search`` (A to C, the four frozen sets), ``break_even_search`` (search D) with
``coupled_placement`` on a ``PenaltyCurve`` (SP1's, ``SP1_PENALTY_CURVE``), and
``choose_fallbacks`` (on ``planned_sizings``: the note's plan computed from the
coefficients plus the polish's bound). Each takes a ``SearchEvaluator`` around a sizing callable
(``SizingFn``; sim.structure_sizing builds it from the structure file, the flown pad and
the analytic push) and works on the structure file's coefficient paths and values. Its
sets are labelled ``SEARCH_LABEL``: "the extremes found by the screened search over the
stated ranges", never bounds.

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
numpy and scipy.optimize only (never sim, results_io, plots, run_data or config: the
callers convert the structure file and a Result into this module's dataclasses).
"""

from __future__ import annotations

import itertools
import math
import operator
from bisect import bisect_right
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike
from scipy.optimize import brentq

from launchsim.constants import (
    OFFLOAD_PER_KG_STAGE1_DRY,
    OFFLOAD_PER_KG_STAGE2_DRY,
    P_SEA_LEVEL_PA,
    SP1_PENALTY_DRY_MASS_KG,
    SP1_PENALTY_OFFLOAD_KG,
    SP8007_KNOCKDOWN_A,
    SP8007_PHI_DIVISOR,
)
from launchsim.units import from_g, to_g

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


def check_delta_gamma_table(table: DeltaGammaTable) -> None:
    """Refuse a Delta_gamma table the monocoque mode cannot use (ValueError): at least two
    finite (x, Delta_gamma) pairs from (0, 0), x strictly ascending, Delta_gamma
    non-decreasing, and its chord slope Delta_gamma(x)/x non-increasing in x (so that the
    buckling load stays monotone in t, ``monocoque_buckling_load_N``). Input: the table.
    Output: None. Frame: none."""
    xs, ys = _dgamma_points(table)
    _check_dgamma_chords(xs, ys)


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
    return _monocoque_solve(_require_finite("n_design_N", n_design_N), r, e, k3, p, s, xs, ys)


def _monocoque_solve(
    n: float,
    r: float,
    e: float,
    k3: float,
    p: float,
    s: float,
    xs: Sequence[float],
    ys: Sequence[float],
) -> float:
    """``monocoque_buckling_thickness_m`` for checked inputs (the vectorized envelope
    checks them once per array, then solves station by station with the same arithmetic)."""
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
    8.2% at 3. This primitive checks bending only: the torsion vanishes at the pads and
    peaks in the span, where the bending moment is zero, at 0.076 M (8 pads) to 0.209 M
    (3 pads). The required (elastic) section modulus Z = FS_u f_fit M / F_tu [m^3], no
    plastic shape factor credited; a solid rectangle b x h with h = k b has Z = k^2 b^3 / 6
    and area k b^2, so b = (6 Z / k^2)^(1/3) (``_ring_bending_width_m``); mass = 2 pi r rho
    k b^2 [kg], the ideal mass before the non-optimum factor. In the station model (S2)
    ``ring_frame_section`` widens the section where its torsion-plus-shear and von Mises
    check binds, and the caller multiplies the mass by nof_barrel x nof_entry_ratio
    (D-SP7-37 items 2 and 15). No envelope credit (new hardware). 0.0 when F <= 0.
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
    b = _ring_bending_width_m(f, r, pads, k, fs, f_tu, fit)
    return 2.0 * math.pi * r * rho * k * b * b


def _ring_bending_width_m(
    f_peak_N: float, radius_m: float, n_pads: int, aspect: float, fs: float, f_tu: float, fit: float
) -> float:
    """S1's bending width of the ring frame, b = (6 Z/k^2)^(1/3) [m], with Z = FS_u f_fit
    M_pad/F_tu, M_pad = q r^2 (1 - alpha cot alpha), q = F/(2 pi r) and alpha = pi/N_p (the
    one place this arithmetic lives: ``ring_frame_mass_kg`` and ``ring_frame_section`` both
    call it). Inputs as ``ring_frame_mass_kg`` (F > 0; the other checks are the callers').
    Frame: the ring's section, b radial."""
    alpha = math.pi / _require_pad_count(n_pads)
    q = f_peak_N / (2.0 * math.pi * radius_m)
    moment = q * radius_m * radius_m * (1.0 - alpha / math.tan(alpha))
    z = fs * fit * moment / f_tu
    return (6.0 * z / (aspect * aspect)) ** (1.0 / 3.0)


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


# ======================================================================== S2: names


LOX = "lox"
"""The liquid-oxygen tank of a stage."""
RP1 = "rp1"
"""The RP-1 (fuel) tank of a stage."""
TANK_ORDER: tuple[str, str] = (RP1, LOX)
"""The only tank order the model sizes, bottom to top: RP-1 below LOX with a common dome
between (stage 1: FUG15 PDF p.10; stage 2: assumed the same, source note section 2.2)."""

STAGE1 = "stage1"
"""Role of the first stage (index 0, lit first)."""
STAGE2 = "stage2"
"""Role of the second stage (index 1)."""
STAGE_ROLES: tuple[str, str] = (STAGE1, STAGE2)
"""The two stage roles; the layout names the vehicle's stage of each role."""

REST_AT_BASE = "base"
"""A breakdown's remainder placed at the stage base (stage 1: loads no barrel station)."""
REST_AT_FORWARD_END = "forward_end"
"""A breakdown's remainder placed at the stage's forward end (stage 2: loads every station)."""
REST_PLACEMENTS: tuple[str, ...] = (REST_AT_BASE, REST_AT_FORWARD_END)
"""Where a breakdown's remainder may sit (source note section 5)."""

PLATE_LIMITED = "plate_limited"
"""The plate-limited stiffened row: thickness proportional to the load, anchored at the
central Gerard row's smeared thickness at the station's envelope load, taken before the
gauge floor (design 4.2; source note section 3.3; D-SP7-37)."""
PLATE_ANCHOR_ROW: GerardRow = GERARD_RING_COMMON_Z
"""The row whose envelope thickness anchors the plate-limited row (the central row)."""
GERARD_CHOICES: tuple[str, ...] = (*(row.name for row in GERARD_ROWS), PLATE_LIMITED)
"""Every stiffened-wall choice a coefficient set may name (the band takes ring_common_z
and plate_limited; the other rows are sizing-only lines, source note section 3.3)."""

SKIRT_HOLD_DOWN = "hold_down"
"""Aft-skirt envelope path: the pad's hold-down support (central; FUG15 PDF p.60)."""
SKIRT_FLIGHT_THRUST = "flight_thrust"
"""Aft-skirt envelope path: the flight thrust through the skirt as well (assumed)."""
SKIRT_ENVELOPE_PATHS: tuple[str, ...] = (SKIRT_HOLD_DOWN, SKIRT_FLIGHT_THRUST)
"""The skirt's envelope paths (source note section 3.5)."""

ENTRY_AFT_RING = "aft_ring"
"""Load entry through the aft skirt and a ring frame at the stage base (central)."""
ENTRY_THRUST_STRUCTURE = "thrust_structure"
"""Load entry through the thrust structure (the row of equal prominence)."""
type EntryPath = Literal["aft_ring", "thrust_structure"]
"""Where the push enters the stage (design 4.2.3, D-SP7-17)."""
ENTRY_PATHS: tuple[EntryPath, ...] = (ENTRY_AFT_RING, ENTRY_THRUST_STRUCTURE)
"""The accepted entry paths."""

HOLD = "hold"
"""A HOLD row: the vehicle clamped on the pad (the clamp carries the weight)."""
PUSH = "push"
"""A push on the track."""
FLIGHT = "flight"
"""A powered flight row (a stage burning)."""
type PhaseKind = Literal["hold", "push", "flight"]
"""The phase kind of a load case."""
PHASE_KINDS: tuple[PhaseKind, ...] = (HOLD, PUSH, FLIGHT)
"""The accepted phase kinds."""

AFT_SKIRT = "aft_skirt"
LOAD_RING = "load_ring"
RP1_AFT_DOME = "rp1_aft_dome"
RP1_BARREL = "rp1_barrel"
COMMON_DOME = "common_dome"
LOX_BARREL = "lox_barrel"
FORWARD_DOME = "forward_dome"
TRANSFER_TUBE = "transfer_tube"
INTERSTAGE = "interstage"
THRUST_STRUCTURE = "thrust_structure"
STAGE1_ELEMENTS: tuple[str, ...] = (
    AFT_SKIRT,
    LOAD_RING,
    RP1_AFT_DOME,
    RP1_BARREL,
    COMMON_DOME,
    LOX_BARREL,
    FORWARD_DOME,
    TRANSFER_TUBE,
    INTERSTAGE,
    THRUST_STRUCTURE,
)
"""Stage 1's elements, bottom to top, then the tube and the two relation rows (the
interstage is stage-1 hardware and its increment is charged to stage 1, D-SP7-36)."""
STAGE2_ELEMENTS: tuple[str, ...] = (
    RP1_AFT_DOME,
    RP1_BARREL,
    COMMON_DOME,
    LOX_BARREL,
    FORWARD_DOME,
    TRANSFER_TUBE,
)
"""Stage 2's elements (no aft skirt, ring or interstage: its base is the latch plane)."""
TANK_ELEMENTS: tuple[str, ...] = (FORWARD_DOME, LOX_BARREL, COMMON_DOME, RP1_BARREL, RP1_AFT_DOME)
"""The tank elements of a stage the plausibility rule sums (not the skirt, ring or tube)."""

DOMES = "domes"
"""The structure file's construction key for every dome of a stage (source note section 12)."""
CONSTRUCTION_STIFFENED = "stiffened_gerard"
"""Construction: a stiffened wall sized by a Gerard row or the plate-limited row."""
CONSTRUCTION_MONOCOQUE = "monocoque_sp8007"
"""Construction: a monocoque wall sized by SP-8007 with the pressure increment."""
CONSTRUCTION_MEMBRANE_DOME = "membrane_dome"
"""Construction: a membrane dome sized at its crown."""
CONSTRUCTION_HOOP_TUBE = "hoop_tube"
"""Construction: the LOX transfer tube sized in hoop."""
CONSTRUCTION_RING_FRAME = "ring_frame"
"""Construction: the load ring sized as a closed ring frame (``ring_frame_section``)."""
CONSTRUCTION_COMPOSITE_RELATION = "composite_relation"
"""Construction: the interstage by Castellini's composite relation."""
MODELLED_CONSTRUCTION: dict[str, tuple[tuple[str, str], ...]] = {
    STAGE1: (
        (AFT_SKIRT, CONSTRUCTION_STIFFENED),
        (RP1_BARREL, CONSTRUCTION_STIFFENED),
        (LOX_BARREL, CONSTRUCTION_MONOCOQUE),
        (DOMES, CONSTRUCTION_MEMBRANE_DOME),
        (TRANSFER_TUBE, CONSTRUCTION_HOOP_TUBE),
        (LOAD_RING, CONSTRUCTION_RING_FRAME),
        (INTERSTAGE, CONSTRUCTION_COMPOSITE_RELATION),
    ),
    STAGE2: (
        (RP1_BARREL, CONSTRUCTION_STIFFENED),
        (LOX_BARREL, CONSTRUCTION_MONOCOQUE),
        (DOMES, CONSTRUCTION_MEMBRANE_DOME),
        (TRANSFER_TUBE, CONSTRUCTION_HOOP_TUBE),
    ),
}
"""The construction per element the model sizes, by stage role (the source note's
section 12 vocabulary; design 4.2, 4.2.3, 4.2.4): the structure file's ``construction``
must name exactly this mapping (config.py refuses any other; editing it would not change
the model)."""
INTERSTAGE_CHARGED_TO = STAGE1
"""The stage the interstage's increment is charged to (D-SP7-36): the only value the
model implements; config.py refuses any other ``interstage.charged_to``."""

MODE_HOOP = "hoop"
MODE_MONOCOQUE = "monocoque"
MODE_COMBINED = "combined"
MODE_MIN_GAUGE = "min_gauge"
MODE_MEMBRANE = "membrane"
MODE_RELATION = "relation"
MODE_RING_BENDING = "ring_bending"
MODE_RING_CHECK = "ring_torsion_shear"
STIFFENED_MODES: frozenset[str] = frozenset(GERARD_CHOICES)
"""Station modes sized by a Gerard row or the plate-limited row: their increments take
`nof_stiffened` (source note section 4's table)."""

CASE_BLOCK_SIZE = 32
"""Consecutive pad load cases per block of the envelope's exact block bound (a numerical
partition: any size gives the same envelope; 32 keeps the bound matrix small)."""

FLAG_RELEASE_UNLOAD = "structure_release_unload"
FLAG_UPPER_STACK = "structure_upper_stack_exceeded"
FLAG_PAYLOAD_LIMIT = "structure_payload_limit"

MECO_AMBIENT_PA: float = 0.0
"""The ambient pressure [Pa] the release flag takes at the pad's MECO (its load case
carries no ambient; near vacuum at MECO's altitude), so a MECO gauge value is also its
absolute one there."""


# ======================================================================== S2: coefficients


def _require_fraction(name: str, value: float) -> float:
    """``value`` as a float, or ValueError unless 0 <= value <= 1."""
    x = _require_non_negative(name, value)
    if x > 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value!r}")
    return x


@dataclass(frozen=True)
class StructureCoefficients:
    """One resolved coefficient set of the structural model, in SI (config.py converts the
    structure file's units through units.py; the search builds sets by
    ``dataclasses.replace``).

    Materials (the 2195 block: barrels, aft skirt, ring frame, transfer tube): e_pa,
    Young's modulus [Pa]; nu, Poisson's ratio [-]; rho_wall_kgm3 [kg/m^3]; f_tu_pa, the
    ultimate tensile strength [Pa]; eta_weld, the weld efficiency on the hoop direction
    [-]. The domes: dome_alloy (the discrete choice's name) with its dome_f_tu_pa [Pa] and
    dome_rho_kgm3 [kg/m^3] (the 2195 block's values when the alloy is 2195). Factors:
    fs_ult [-] on loads and pressures; fitting_factor [-] on the ring frame. Pressures,
    each tank's ullage MEOP [Pa, gauge relative to the ambient outside the vehicle, without
    the acceleration head] and its minimum as a fraction of it [-] (p_min = fraction x
    MEOP, unfactored, the relief): ``p_meop_<stage>_<tank>_pa`` and
    ``p_min_fraction_<stage>_<tank>``. Buckling: s_dg [-] in [0, 1] (the SP-8007 pressure
    increment on or off); k_stiff, the stiffened knockdown [-]; gerard_row, one of
    GERARD_CHOICES; t_min_m, the minimum gauge [m]; delta_gamma_table, the SP-8007 curve as
    (x, Delta_gamma) pairs. Geometry: aft_skirt_length_m [m] (stage 1); dome_axis_ratio
    a/b [-] in [1, sqrt(2)] (all domes); ullage_fraction [-] (ullage over liquid volume);
    rho_lox_kgm3 and rho_rp1_kgm3 [kg/m^3] (both stages); tube_diameter_m [m] (stage 1)
    and tube_diameter_ratio [-] (stage 2's over stage 1's); interstage_length_m [m]. Load
    entry: skirt_envelope_path (SKIRT_ENVELOPE_PATHS); ring_h_over_b [-] (>= 1). Design
    axes: nof_barrel, nof_stiffened, nof_dome, nof_entry_ratio [-] (>= 1); rise_time_s [s],
    the assumed real-drive force rise time (constant_accel); axial_frequency_hz [Hz], the
    stack's first axial frequency on its carriage; ring_pads [-], an integer >= 3;
    k_ts_kg_per_n [kg/N], the thrust structure's mass per unit of added load. Fixed
    relations: the interstage relation M = k_sm k1 S D^k2 (k1 is
    interstage_k1_kg_per_m2p4856 [kg per m^2.4856], interstage_k2 [-], interstage_k_sm [-])
    and its increment exponent interstage_exponent [-]; the payload's axial limits
    payload_limit_axial_max_g and payload_limit_axial_min_g [g0]; Heineman's relation
    M = c V^e (heineman_kg_per_m2p25, heineman_exponent [-]) and its band
    heineman_band_fraction [-]; Akin's tank fractions akin_lox_tank_fraction and
    akin_rp1_tank_fraction [-] (printed only).
    """

    e_pa: float
    nu: float
    rho_wall_kgm3: float
    f_tu_pa: float
    eta_weld: float
    dome_alloy: str
    dome_f_tu_pa: float
    dome_rho_kgm3: float
    fs_ult: float
    fitting_factor: float
    p_meop_stage1_lox_pa: float
    p_min_fraction_stage1_lox: float
    p_meop_stage1_rp1_pa: float
    p_min_fraction_stage1_rp1: float
    p_meop_stage2_lox_pa: float
    p_min_fraction_stage2_lox: float
    p_meop_stage2_rp1_pa: float
    p_min_fraction_stage2_rp1: float
    s_dg: float
    k_stiff: float
    gerard_row: str
    t_min_m: float
    delta_gamma_table: tuple[tuple[float, float], ...]
    aft_skirt_length_m: float
    dome_axis_ratio: float
    ullage_fraction: float
    rho_lox_kgm3: float
    rho_rp1_kgm3: float
    tube_diameter_m: float
    tube_diameter_ratio: float
    interstage_length_m: float
    skirt_envelope_path: str
    ring_h_over_b: float
    nof_barrel: float
    nof_stiffened: float
    nof_dome: float
    nof_entry_ratio: float
    rise_time_s: float
    axial_frequency_hz: float
    ring_pads: int
    k_ts_kg_per_n: float
    interstage_k1_kg_per_m2p4856: float
    interstage_k2: float
    interstage_k_sm: float
    interstage_exponent: float
    payload_limit_axial_max_g: float
    payload_limit_axial_min_g: float
    heineman_kg_per_m2p25: float
    heineman_exponent: float
    heineman_band_fraction: float
    akin_lox_tank_fraction: float
    akin_rp1_tank_fraction: float

    def __post_init__(self) -> None:
        """Refuse a value outside its physical domain (ValueError)."""
        for name in (
            "e_pa",
            "rho_wall_kgm3",
            "f_tu_pa",
            "dome_f_tu_pa",
            "dome_rho_kgm3",
            "fs_ult",
            "fitting_factor",
            "k_stiff",
            "t_min_m",
            "rho_lox_kgm3",
            "rho_rp1_kgm3",
            "tube_diameter_m",
            "tube_diameter_ratio",
            "interstage_length_m",
            "ring_h_over_b",
            "axial_frequency_hz",
            "interstage_k1_kg_per_m2p4856",
            "interstage_k_sm",
            "heineman_kg_per_m2p25",
            "heineman_exponent",
        ):
            _require_positive(name, getattr(self, name))
        for name in (
            "p_meop_stage1_lox_pa",
            "p_meop_stage1_rp1_pa",
            "p_meop_stage2_lox_pa",
            "p_meop_stage2_rp1_pa",
            "aft_skirt_length_m",
            "ullage_fraction",
            "rise_time_s",
            "k_ts_kg_per_n",
            "interstage_k2",
            "akin_lox_tank_fraction",
            "akin_rp1_tank_fraction",
        ):
            _require_non_negative(name, getattr(self, name))
        for name in (
            "p_min_fraction_stage1_lox",
            "p_min_fraction_stage1_rp1",
            "p_min_fraction_stage2_lox",
            "p_min_fraction_stage2_rp1",
            "heineman_band_fraction",
        ):
            _require_fraction(name, getattr(self, name))
        _require_unit_fraction("eta_weld", self.eta_weld)
        _require_unit_fraction("k_stiff", self.k_stiff)
        _require_unit_fraction("interstage_exponent", self.interstage_exponent)
        _poisson_factor(self.nu)
        _require_s_dg(self.s_dg)
        xs, ys = _dgamma_points(self.delta_gamma_table)
        _check_dgamma_chords(xs, ys)
        _require_axis_ratio(self.dome_axis_ratio, DOME_AXIS_RATIO_MAX)
        if self.ring_h_over_b < 1.0:
            raise ValueError(
                f"ring_h_over_b must be >= 1 (h the depth), got {self.ring_h_over_b!r}"
            )
        _require_pad_count(self.ring_pads)
        for name in ("nof_barrel", "nof_stiffened", "nof_dome", "nof_entry_ratio"):
            _require_nof(getattr(self, name))
        if self.gerard_row not in GERARD_CHOICES:
            raise ValueError(f"gerard_row must be one of {GERARD_CHOICES}, got {self.gerard_row!r}")
        if self.skirt_envelope_path not in SKIRT_ENVELOPE_PATHS:
            raise ValueError(
                f"skirt_envelope_path must be one of {SKIRT_ENVELOPE_PATHS}, "
                f"got {self.skirt_envelope_path!r}"
            )
        _require_finite("payload_limit_axial_max_g", self.payload_limit_axial_max_g)
        _require_finite("payload_limit_axial_min_g", self.payload_limit_axial_min_g)
        if not self.payload_limit_axial_min_g < self.payload_limit_axial_max_g:
            raise ValueError("payload_limit_axial_min_g must be below payload_limit_axial_max_g")

    def p_meop_pa(self, stage: str, tank: str) -> float:
        """The ullage MEOP [Pa, gauge from the ambient] of one tank (stage in STAGE_ROLES,
        tank LOX or RP1)."""
        return float(getattr(self, f"p_meop_{_check_stage(stage)}_{_check_tank(tank)}_pa"))

    def p_min_pa(self, stage: str, tank: str) -> float:
        """The minimum (relieving) pressure [Pa, gauge from the ambient] of one tank:
        p_min_fraction x MEOP, unfactored (NASA-STD-5001B FSR 19)."""
        fraction = float(getattr(self, f"p_min_fraction_{_check_stage(stage)}_{_check_tank(tank)}"))
        return fraction * self.p_meop_pa(stage, tank)


def _check_stage(stage: str) -> str:
    """``stage`` when it is a STAGE_ROLES entry; ValueError otherwise."""
    if stage not in STAGE_ROLES:
        raise ValueError(f"stage must be one of {STAGE_ROLES}, got {stage!r}")
    return stage


def _check_tank(tank: str) -> str:
    """``tank`` when it is LOX or RP1; ValueError otherwise."""
    if tank not in TANK_ORDER:
        raise ValueError(f"tank must be one of {TANK_ORDER}, got {tank!r}")
    return tank


# ======================================================================== S2: layout


@dataclass(frozen=True)
class StageBreakdown:
    """One stage's dry mass by element [kg] (the structure file's breakdown, source note
    section 5): it places the structural mass above each station (design 4.2: m_s,above
    from the breakdown, not from the sized thicknesses) and feeds the plausibility check.

    interstage_kg and upper_equipment_kg sit at the top of stage 1 (0 for stage 2);
    forward_dome_kg at the top of the LOX barrel; lox_barrel_kg and rp1_barrel_kg uniform
    along their barrels; common_dome_kg at the LOX/RP-1 junction; rp1_aft_dome_kg at the
    bottom of the RP-1 barrel (it loads no barrel station); thrust_structure_kg and
    engines_kg at the base (placement only); rest_kg at ``rest_at`` (REST_AT_BASE: loads no
    barrel station; REST_AT_FORWARD_END: loads every barrel station of the stage).
    """

    interstage_kg: float
    upper_equipment_kg: float
    forward_dome_kg: float
    lox_barrel_kg: float
    common_dome_kg: float
    rp1_barrel_kg: float
    rp1_aft_dome_kg: float
    thrust_structure_kg: float
    engines_kg: float
    rest_kg: float
    rest_at: str

    def __post_init__(self) -> None:
        """Refuse a negative or non-finite mass, or an unknown placement."""
        for name in (
            "interstage_kg",
            "upper_equipment_kg",
            "forward_dome_kg",
            "lox_barrel_kg",
            "common_dome_kg",
            "rp1_barrel_kg",
            "rp1_aft_dome_kg",
            "thrust_structure_kg",
            "engines_kg",
            "rest_kg",
        ):
            _require_non_negative(name, getattr(self, name))
        if self.rest_at not in REST_PLACEMENTS:
            raise ValueError(f"rest_at must be one of {REST_PLACEMENTS}, got {self.rest_at!r}")

    @property
    def total_kg(self) -> float:
        """The stage's dry mass [kg]: the sum of the entries."""
        return (
            self.interstage_kg
            + self.upper_equipment_kg
            + self.forward_dome_kg
            + self.lox_barrel_kg
            + self.common_dome_kg
            + self.rp1_barrel_kg
            + self.rp1_aft_dome_kg
            + self.thrust_structure_kg
            + self.engines_kg
            + self.rest_kg
        )

    @property
    def top_kg(self) -> float:
        """The mass [kg] at the stage's top, above every barrel station: the interstage, the
        upper equipment, the forward dome and the remainder when it sits at the forward
        end."""
        rest = self.rest_kg if self.rest_at == REST_AT_FORWARD_END else 0.0
        return self.interstage_kg + self.upper_equipment_kg + self.forward_dome_kg + rest


@dataclass(frozen=True)
class StageLayout:
    """The layout of one stage (design 4.2, D-SP7-13; source note section 2.3).

    name: the vehicle's stage name of this role; tank_order: bottom to top, only TANK_ORDER
    is modelled; common_dome: only True is modelled; lox_mass_fraction [-] in (0, 1): the
    LOX share of the stage's propellant at every instant (constant mixture ratio);
    breakdown: the dry mass by element; has_aft_skirt: True for stage 1 (its length is the
    coefficient ``aft_skirt_length_m``), False for stage 2 (its base is the interstage's
    latch plane, length 0); has_load_ring: True where a push enters (stage 1).
    """

    name: str
    tank_order: tuple[str, ...]
    common_dome: bool
    lox_mass_fraction: float
    breakdown: StageBreakdown
    has_aft_skirt: bool
    has_load_ring: bool

    def __post_init__(self) -> None:
        """Refuse a layout the model does not size."""
        if tuple(self.tank_order) != TANK_ORDER:
            raise ValueError(
                f"only the tank order {TANK_ORDER} (bottom to top) is modelled, got "
                f"{self.tank_order!r}"
            )
        if self.common_dome is not True:
            raise ValueError("only a common dome between the tanks is modelled")
        x = _require_positive("lox_mass_fraction", self.lox_mass_fraction)
        if x >= 1.0:
            raise ValueError(f"lox_mass_fraction must be in (0, 1), got {x!r}")


@dataclass(frozen=True)
class StackLayout:
    """The layout of both stages: radius_m [m] (both stages; FUG Table 2-1),
    stations_per_barrel (an integer >= 1, every barrel and the aft skirt), and the two
    StageLayouts."""

    radius_m: float
    stations_per_barrel: int
    stage1: StageLayout
    stage2: StageLayout

    def __post_init__(self) -> None:
        """Refuse a non-positive radius or station count, or a stage-2 skirt or ring."""
        _require_positive("radius_m", self.radius_m)
        if (
            isinstance(self.stations_per_barrel, bool)
            or operator.index(self.stations_per_barrel) < 1
        ):
            raise ValueError(
                f"stations_per_barrel must be an integer >= 1, got {self.stations_per_barrel!r}"
            )
        if not self.stage1.has_aft_skirt or self.stage2.has_aft_skirt:
            raise ValueError("stage 1 has the aft skirt and stage 2 none (source note section 2.2)")
        if self.stage2.has_load_ring:
            raise ValueError("the push enters stage 1 only")

    def stage(self, role: str) -> StageLayout:
        """The StageLayout of a role (STAGE1 or STAGE2)."""
        return self.stage1 if _check_stage(role) == STAGE1 else self.stage2


@dataclass(frozen=True)
class StageMasses:
    """A stage's masses and thrust from the full-load vehicle: name, dry_mass_kg [kg],
    propellant_mass_kg [kg] (the full load), thrust_vac_N [N] (all engines, vacuum)."""

    name: str
    dry_mass_kg: float
    propellant_mass_kg: float
    thrust_vac_N: float

    def __post_init__(self) -> None:
        """Refuse non-positive masses or thrust."""
        _require_non_negative("dry_mass_kg", self.dry_mass_kg)
        _require_positive("propellant_mass_kg", self.propellant_mass_kg)
        _require_positive("thrust_vac_N", self.thrust_vac_N)


@dataclass(frozen=True)
class StackMasses:
    """Both stages' StageMasses (sim.stack_masses builds it from a launchsim Vehicle)."""

    stage1: StageMasses
    stage2: StageMasses


# ======================================================================== S2: geometry


@dataclass(frozen=True, eq=False)
class BarrelStations:
    """The stations of one barrel (or of the aft skirt, tank "").

    z_bottom_m and length_m: the barrel's bottom height in the stack frame and its
    length [m]; z_m and dz_m: each station's centre height and length [m] (N stations
    of equal length, centres at fractions (i + 1/2)/N); mass_height_kg: the liquid mass
    [kg] below each station's height at the full tank's density, k = f (1 + u) m_full
    (the head at the station is h = (m - k)+/(rho A), so rho h = (m - k)+/A does not
    depend on rho); structure_above_kg: the breakdown's structural mass above each
    station [kg] (not the propellant).
    Frame: station heights z run up the stack from the stage-1 load ring at the base.
    """

    tank: str
    z_bottom_m: float
    length_m: float
    z_m: np.ndarray
    dz_m: np.ndarray
    mass_height_kg: np.ndarray
    structure_above_kg: np.ndarray


def _stations(
    tank: str,
    z_bottom: float,
    length: float,
    n: int,
    mass_full: float,
    ullage: float,
    above_top: float,
    own_kg: float,
) -> BarrelStations:
    """N stations of a barrel of ``length`` from ``z_bottom``: mass heights f (1 + u)
    m_full and structural mass above them (``above_top`` plus the barrel's own mass above
    the station, uniform along it)."""
    fraction = (np.arange(n, dtype=float) + 0.5) / n
    return BarrelStations(
        tank=tank,
        z_bottom_m=z_bottom,
        length_m=length,
        z_m=z_bottom + fraction * length,
        dz_m=np.full(n, length / n),
        mass_height_kg=fraction * ((1.0 + ullage) * mass_full),
        structure_above_kg=above_top + own_kg * (1.0 - fraction),
    )


@dataclass(frozen=True, eq=False)
class StageGeometry:
    """The station geometry of one stage, built once from the full-load vehicle's masses
    (``build_geometry``) and closed over: the push at any offload is evaluated on the same
    stations as the envelope (design 4.2; D-SP7-13).

    role, name: the stage role and the vehicle's stage name; radius_m, area_m2 [m, m^2];
    z_base_m: the stage base in the stack frame [m]; lox_full_kg, rp1_full_kg,
    dry_mass_kg [kg] and thrust_vac_N [N] from the vehicle; lox_volume_m3, rp1_volume_m3:
    each tank's volume with its ullage [m^3]; rp1_barrel, lox_barrel: their stations
    (length m (1 + u)/(rho A): cylinder-equivalent, dome volumes neglected); skirt: the aft
    skirt's stations (None for stage 2); skirt_structure_above_kg: the structural mass above
    the skirt's top (everything but the base items) [kg]; dome_depth_m b = r/(a/b) and
    dome_area_m2 (every dome); tube_diameter_m, tube_length_m (the RP-1 barrel's length:
    from the common-dome crown to the aft-dome crown, both bulging down by b) and
    tube_area_m2 [m, m, m^2]; lox_length_physical_m, rp1_length_physical_m: the physical
    tank lengths of the plausibility rule [m] (LOX: (V - 2 V_dome)/A; RP-1: V/(A - pi
    d_t^2/4)); breakdown: the stage's StageBreakdown.
    Frame: the stack frame of BarrelStations.
    """

    role: str
    name: str
    radius_m: float
    area_m2: float
    z_base_m: float
    lox_full_kg: float
    rp1_full_kg: float
    dry_mass_kg: float
    thrust_vac_N: float
    lox_volume_m3: float
    rp1_volume_m3: float
    rp1_barrel: BarrelStations
    lox_barrel: BarrelStations
    skirt: BarrelStations | None
    skirt_structure_above_kg: float
    dome_depth_m: float
    dome_area_m2: float
    tube_diameter_m: float
    tube_length_m: float
    tube_area_m2: float
    lox_length_physical_m: float
    rp1_length_physical_m: float
    breakdown: StageBreakdown

    def barrel(self, tank: str) -> BarrelStations:
        """The barrel of a tank (LOX or RP1)."""
        return self.lox_barrel if _check_tank(tank) == LOX else self.rp1_barrel

    @property
    def top_z_m(self) -> float:
        """The top of the LOX barrel (the forward dome's equator) [m, stack frame]."""
        return self.lox_barrel.z_bottom_m + self.lox_barrel.length_m


@dataclass(frozen=True, eq=False)
class StackGeometry:
    """Both stages' StageGeometry, the interstage between them (from the top of the
    stage-1 LOX barrel to the stage-2 latch plane, enclosing both domes there; its length
    interstage_length_m [m] and its mass-estimating-relation mass interstage_mass_kg [kg],
    Castellini 2012 Table 15) and the layout they were built from."""

    layout: StackLayout
    stage1: StageGeometry
    stage2: StageGeometry
    interstage_length_m: float
    interstage_mass_kg: float

    def stage(self, role: str) -> StageGeometry:
        """The StageGeometry of a role (STAGE1 or STAGE2)."""
        return self.stage1 if _check_stage(role) == STAGE1 else self.stage2


def interstage_mass_kg(
    length_m: float, diameter_m: float, k1: float, k2: float, k_sm: float
) -> float:
    """The interstage's mass by Castellini's (2012) lower-stage relation (Table 15, PDF
    p.83), in SI: M = k_sm k1 S D^k2 with S = pi D L the lateral area.

    Inputs: length_m L [m], > 0; diameter_m D [m], > 0; k1 [kg per m^(2 + k2)] (13.740 for
    the source's 7.7165 in feet, 7.7165 x 3.2808^0.4856); k2 [-] (0.4856); k_sm [-] (0.7
    composite, 1.0 aluminium).
    Output: M [kg] (934 kg at 4.5 m, 3.66 m and 0.7: 207.7 kg per metre).
    Frame: none.
    """
    length = _require_positive("length_m", length_m)
    d = _require_positive("diameter_m", diameter_m)
    c1 = _require_positive("k1", k1)
    c2 = _require_non_negative("k2", k2)
    sm = _require_positive("k_sm", k_sm)
    return sm * c1 * (math.pi * d * length) * d**c2


def build_geometry(
    masses: StackMasses, layout: StackLayout, coeffs: StructureCoefficients
) -> StackGeometry:
    """The station geometry of both stages (design 4.2; source note sections 2.3 to 2.4).

    Inputs: masses, the full-load vehicle's stage masses and thrusts (the geometry is built
    once from them and closed over: a geometry that shrank with the offload would favour
    the assist, D-SP7-13); layout, the stack layout (names checked against the masses);
    coeffs, the coefficient set (densities, ullage, skirt length, dome ratio, tube
    diameter, interstage length).
    Output: a StackGeometry. Stage 1, up from the load ring at z = 0: the aft skirt (0 to
    L_s), the RP-1 barrel (L_s to L_s + L_RP1; its aft dome bulges down inside the skirt),
    the common dome at the junction (bulging into the RP-1 tank), the LOX barrel, the
    forward dome at its top (inside the interstage), the interstage (L_is); stage 2 from
    the latch plane at the interstage's top in the same pattern without a skirt. Barrel
    lengths L = m (1 + u)/(rho pi r^2) from the full loads (cylinder-equivalent; dome and
    tube volumes neglected); the transfer tube runs through the RP-1 tank from the
    common-dome crown to the aft-dome crown (length L_RP1).
    Frame: station heights up the stack from the stage-1 load ring.
    """
    for role, stage_masses in ((STAGE1, masses.stage1), (STAGE2, masses.stage2)):
        if stage_masses.name != layout.stage(role).name:
            raise ValueError(
                f"the layout's {role} is {layout.stage(role).name!r}, the vehicle's is "
                f"{stage_masses.name!r}"
            )
    r = layout.radius_m
    area = math.pi * r * r
    n = int(layout.stations_per_barrel)
    u = coeffs.ullage_fraction
    depth = r / coeffs.dome_axis_ratio
    dome_area = spheroid_head_area_m2(r, coeffs.dome_axis_ratio)
    dome_volume = (2.0 / 3.0) * math.pi * r**3 / coeffs.dome_axis_ratio
    if not coeffs.tube_diameter_m < 2.0 * r:
        raise ValueError(f"tube_diameter_m must be below the barrel's diameter {2.0 * r!r} m")

    def stage_geometry(
        role: str, z_base: float, skirt_length: float, tube_d: float
    ) -> StageGeometry:
        lay = layout.stage(role)
        sm = masses.stage1 if role == STAGE1 else masses.stage2
        bd = lay.breakdown
        m_lox = lay.lox_mass_fraction * sm.propellant_mass_kg
        m_rp1 = sm.propellant_mass_kg - m_lox
        v_lox = m_lox * (1.0 + u) / coeffs.rho_lox_kgm3
        v_rp1 = m_rp1 * (1.0 + u) / coeffs.rho_rp1_kgm3
        l_lox = v_lox / area
        l_rp1 = v_rp1 / area
        z_rp1 = z_base + skirt_length
        z_lox = z_rp1 + l_rp1
        top = bd.top_kg
        lox = _stations(LOX, z_lox, l_lox, n, m_lox, u, top, bd.lox_barrel_kg)
        rp1_top = top + bd.lox_barrel_kg + bd.common_dome_kg
        rp1 = _stations(RP1, z_rp1, l_rp1, n, m_rp1, u, rp1_top, bd.rp1_barrel_kg)
        skirt_above = rp1_top + bd.rp1_barrel_kg + bd.rp1_aft_dome_kg
        skirt = None
        if lay.has_aft_skirt:
            if skirt_length <= 0.0:
                raise ValueError("stage 1's aft skirt needs aft_skirt_length_m > 0")
            skirt = _stations("", z_base, skirt_length, n, 0.0, 0.0, skirt_above, 0.0)
        return StageGeometry(
            role=role,
            name=lay.name,
            radius_m=r,
            area_m2=area,
            z_base_m=z_base,
            lox_full_kg=m_lox,
            rp1_full_kg=m_rp1,
            dry_mass_kg=sm.dry_mass_kg,
            thrust_vac_N=sm.thrust_vac_N,
            lox_volume_m3=v_lox,
            rp1_volume_m3=v_rp1,
            rp1_barrel=rp1,
            lox_barrel=lox,
            skirt=skirt,
            skirt_structure_above_kg=skirt_above,
            dome_depth_m=depth,
            dome_area_m2=dome_area,
            tube_diameter_m=tube_d,
            tube_length_m=l_rp1,
            tube_area_m2=math.pi * tube_d * l_rp1,
            lox_length_physical_m=(v_lox - 2.0 * dome_volume) / area,
            rp1_length_physical_m=v_rp1 / (area - math.pi * tube_d * tube_d / 4.0),
            breakdown=bd,
        )

    s1 = stage_geometry(STAGE1, 0.0, coeffs.aft_skirt_length_m, coeffs.tube_diameter_m)
    z2 = s1.top_z_m + coeffs.interstage_length_m
    s2 = stage_geometry(STAGE2, z2, 0.0, coeffs.tube_diameter_m * coeffs.tube_diameter_ratio)
    m_is = interstage_mass_kg(
        coeffs.interstage_length_m,
        2.0 * r,
        coeffs.interstage_k1_kg_per_m2p4856,
        coeffs.interstage_k2,
        coeffs.interstage_k_sm,
    )
    return StackGeometry(
        layout=layout,
        stage1=s1,
        stage2=s2,
        interstage_length_m=coeffs.interstage_length_m,
        interstage_mass_kg=m_is,
    )


def implied_stack_length_m(geometry: StackGeometry, fairing_height_m: float) -> float:
    """The stack length the geometry implies by the source note's section 2.4 arithmetic:
    the aft skirt, the four physical tank lengths, the interstage and the fairing
    [m] (the nozzle protrusion, the MVac's length below its dome and any stage-2 structure
    above its LOX barrel taken as zero; those lengths could only add, so the value is a
    lower bound on the stack the geometry's coefficients imply; the opened overall length
    is 70 m, FUG Table 2-1, and the search does not impose it, source note 9.3).

    Inputs: geometry; fairing_height_m [m] (13.2 m, FUG15 PDF p.36). Output [m].
    Frame: along the stack axis.
    """
    s1, s2 = geometry.stage1, geometry.stage2
    skirt = 0.0 if s1.skirt is None else s1.skirt.length_m
    return (
        skirt
        + s1.lox_length_physical_m
        + s1.rp1_length_physical_m
        + geometry.interstage_length_m
        + s2.lox_length_physical_m
        + s2.rp1_length_physical_m
        + _require_non_negative("fairing_height_m", fairing_height_m)
    )


# ======================================================================== S2: load cases


@dataclass(frozen=True)
class LoadCase:
    """One quasi-static axial load case of the stack (design 4.2; sim.py adapts a Result or
    a push into these).

    label: a name for the records; kind: HOLD, PUSH or FLIGHT; t_s [s] on the run's clock;
    n_g: the felt axial load factor [g0] (HOLD rows: g_eff/g0, the clamp carrying the
    weight); stage1_attached: False on the stage-2 burn (stage 1 gone; the case then
    loads stage-2 elements only); lox_stage1_kg, rp1_stage1_kg, lox_stage2_kg,
    rp1_stage2_kg: the propellant on board [kg], split by each stage's mixture fraction;
    upper_mass_stage1_kg U: everything above stage 1 [kg] (stage 2 wet, the fairing while
    attached, the payload flown; 0 when stage 1 is gone); upper_mass_stage2_kg U2: above
    stage 2 [kg] (the fairing while attached and the payload); vehicle_mass_kg [kg];
    thrust_N: the delivered thrust [N] (along the stack axis); interface_force_N: the
    carriage-to-vehicle force [N] (a push only); hold_down_support_N: the clamps' support
    m_v n g0 - T [N] (a HOLD row only; positive carrying the weight, negative holding the
    vehicle down).
    Frame: the stack axis, compression positive.
    """

    label: str
    kind: str
    t_s: float
    n_g: float
    stage1_attached: bool
    lox_stage1_kg: float
    rp1_stage1_kg: float
    lox_stage2_kg: float
    rp1_stage2_kg: float
    upper_mass_stage1_kg: float
    upper_mass_stage2_kg: float
    vehicle_mass_kg: float
    thrust_N: float
    interface_force_N: float | None = None
    hold_down_support_N: float | None = None

    def __post_init__(self) -> None:
        """Refuse an unknown kind, a negative mass, a non-finite number, a push without its
        interface force or a HOLD row without its support."""
        if self.kind not in PHASE_KINDS:
            raise ValueError(f"kind must be one of {PHASE_KINDS}, got {self.kind!r}")
        _require_finite("t_s", self.t_s)
        _require_finite("n_g", self.n_g)
        _require_finite("thrust_N", self.thrust_N)
        for name in (
            "lox_stage1_kg",
            "rp1_stage1_kg",
            "lox_stage2_kg",
            "rp1_stage2_kg",
            "upper_mass_stage1_kg",
            "upper_mass_stage2_kg",
            "vehicle_mass_kg",
        ):
            _require_non_negative(name, getattr(self, name))
        if (self.kind == PUSH) != (self.interface_force_N is not None):
            raise ValueError("a push case, and only a push case, carries interface_force_N")
        if (self.kind == HOLD) != (self.hold_down_support_N is not None):
            raise ValueError("a HOLD case, and only a HOLD case, carries hold_down_support_N")
        if self.interface_force_N is not None:
            _require_finite("interface_force_N", self.interface_force_N)
        if self.hold_down_support_N is not None:
            _require_finite("hold_down_support_N", self.hold_down_support_N)
        if not self.stage1_attached and self.kind != FLIGHT:
            raise ValueError("only a flight case (the stage-2 burn) has stage 1 gone")

    def stage_lox_kg(self, stage: str) -> float:
        """The LOX on board [kg] of a stage role."""
        return self.lox_stage1_kg if _check_stage(stage) == STAGE1 else self.lox_stage2_kg

    def stage_rp1_kg(self, stage: str) -> float:
        """The RP-1 on board [kg] of a stage role."""
        return self.rp1_stage1_kg if _check_stage(stage) == STAGE1 else self.rp1_stage2_kg

    def upper_mass_kg(self, stage: str) -> float:
        """The mass above a stage role [kg] (U or U2)."""
        return (
            self.upper_mass_stage1_kg
            if _check_stage(stage) == STAGE1
            else self.upper_mass_stage2_kg
        )


@dataclass(frozen=True)
class RampedPlateau:
    """What raises a constant_accel push's plateau under the ``rise_time`` mode (design
    4.2.1): stroke_m L [m], exit_speed_mps v_e [m/s] and accel_net_mps2 a [m/s^2], the
    configured constant net acceleration (v_e^2 = 2 a L)."""

    stroke_m: float
    exit_speed_mps: float
    accel_net_mps2: float

    def __post_init__(self) -> None:
        """Refuse non-positive values."""
        _require_positive("stroke_m", self.stroke_m)
        _require_positive("exit_speed_mps", self.exit_speed_mps)
        _require_positive("accel_net_mps2", self.accel_net_mps2)


@dataclass(frozen=True)
class ReleaseState:
    """The release of a push (design 4.2.2): n_before_g [g0], the felt load just before
    (the plateau; raised with it under ``rise_time``), n_after_g [g0], just after (0 for a
    cold push, T/(m g0) for a lit one, drag neglected), and case, the stack's contents at
    release (a PUSH LoadCase)."""

    n_before_g: float
    n_after_g: float
    case: LoadCase

    def __post_init__(self) -> None:
        """Refuse non-finite loads or a case that is not a push."""
        _require_finite("n_before_g", self.n_before_g)
        _require_finite("n_after_g", self.n_after_g)
        if self.case.kind != PUSH:
            raise ValueError("the release case must be a push case")


@dataclass(frozen=True)
class PushLoad:
    """The quasi-static load cases of one push and what the dynamic load factor acts on
    (design 4.2.1; sim.py builds it: the analytic constant_accel case now, a flown linear
    motor's governing samples in S4b).

    cases: PUSH LoadCases at the quasi-static plateau (n and F_int); n_rest_g [g0] and
    f_rest_N [N]: the resting values the increment is taken over (on the carriage:
    g_eff sin(phi)/g0 and m_v g_eff sin(phi) - T); ramp: a RampedPlateau for constant_accel
    (None for a drive that flies its own rise); rise_time_s: the drive's own force rise
    time [s] (None: the coefficient set's assumed real-drive rise time, constant_accel);
    release: the ReleaseState.
    """

    cases: tuple[LoadCase, ...]
    n_rest_g: float
    f_rest_N: float
    ramp: RampedPlateau | None
    rise_time_s: float | None
    release: ReleaseState

    def __post_init__(self) -> None:
        """Refuse an empty or non-push case list or non-finite resting values."""
        if not self.cases or any(c.kind != PUSH for c in self.cases):
            raise ValueError("a PushLoad needs at least one case, all of kind push")
        _require_finite("n_rest_g", self.n_rest_g)
        _require_finite("f_rest_N", self.f_rest_N)
        if self.rise_time_s is not None:
            _require_non_negative("rise_time_s", self.rise_time_s)


def _features(
    n: np.ndarray, m_lox: np.ndarray, m_rp1: np.ndarray, upper: np.ndarray
) -> dict[str, np.ndarray]:
    """The coefficient-free drivers of a set of cases [kg in units of g0 load], computed in
    one fixed order so that the envelope and the push evaluate them bit for bit alike:
    n, am_lox = n m_LOX and am_rp1 = n m_RP1 (each tank's pressure driver: P = (am - k n)+
    at a station of mass height k), aq_lox = n U and aq_rp1 = n U + n m_LOX (the barrels'
    compression drivers: Q = aq + s n with s the structure above), aq_skirt = n U + n m_LOX
    + n m_RP1 (the skirt's flight product) and n_upper = n U (the upper stack)."""
    n_upper = n * upper
    n_lox = n * m_lox
    return {
        "n": n,
        "am_lox": n_lox,
        "am_rp1": n * m_rp1,
        "aq_lox": n_upper,
        "aq_rp1": n_upper + n_lox,
        "aq_skirt": n_upper + n_lox + n * m_rp1,
        "n_upper": n_upper,
    }


def _block_stats(values: np.ndarray, block: int, fn: Callable[..., np.ndarray]) -> np.ndarray:
    """``fn`` (np.max or np.min) of consecutive blocks of ``block`` values, the last block
    padded with its last value."""
    count = values.shape[0]
    n_blocks = -(-count // block)
    padded = np.concatenate([values, np.full(n_blocks * block - count, values[-1])])
    return fn(padded.reshape(n_blocks, block), axis=1)


@dataclass(frozen=True, eq=False)
class CaseFeatures:
    """The drivers of one stage role's envelope cases at one envelope cap
    (``PadLoadSet.features``): index, the cases' positions in the PadLoadSet; capped, which
    of them are stage-1 rows (the cap acts on those); arrays, the ``_features`` arrays
    (n capped); blocks, each array's block maxima and minima (``<name>_max``,
    ``<name>_min``) over CASE_BLOCK_SIZE consecutive cases."""

    index: np.ndarray
    capped: np.ndarray
    arrays: dict[str, np.ndarray]
    blocks: dict[str, np.ndarray]

    @property
    def count(self) -> int:
        """The number of cases."""
        return int(self.index.shape[0])


@dataclass(frozen=True, eq=False)
class PadLoadSet:
    """The pad baseline's load cases, prepared for the envelope (``pad_load_set``; design
    4.2, D-SP7-15): cases in their given order; stage1_cases, the indices of the cases that
    load stage-1 elements (HOLD and stage-1 flight rows); stage2_cases, those that load
    stage-2 elements (the same rows, with stage 2 full, then the stage-2 burn); hold_cases,
    the HOLD rows; meco_case, the last stage-1 flight row (MECO, the release comparison of
    design 4.2.2). ``features`` caches the drivers per stage role and envelope cap (a
    deterministic cache: the same inputs give the same arrays)."""

    cases: tuple[LoadCase, ...]
    stage1_cases: np.ndarray
    stage2_cases: np.ndarray
    hold_cases: np.ndarray
    meco_case: int
    _cache: dict[tuple[str, float | None], CaseFeatures] = field(default_factory=dict, repr=False)

    def label(self, index: int) -> str | None:
        """The label of case ``index`` (None for -1, no case)."""
        return None if index < 0 else self.cases[index].label

    def features(self, stage: str, envelope_cap_g: float | None) -> CaseFeatures:
        """The drivers of a stage role's cases with the stage-1 rows' n capped at
        envelope_cap_g [g0] (None: uncapped; design 4.3: the pad's stage-1 felt n capped
        when building the envelope, the trajectory left unthrottled)."""
        key = (_check_stage(stage), envelope_cap_g)
        if key not in self._cache:
            self._cache[key] = self._build_features(stage, envelope_cap_g)
        return self._cache[key]

    def _build_features(self, stage: str, cap: float | None) -> CaseFeatures:
        """The CaseFeatures of ``features`` (uncached)."""
        index = self.stage1_cases if stage == STAGE1 else self.stage2_cases
        rows = [self.cases[i] for i in index]
        capped = np.array([c.stage1_attached for c in rows], dtype=bool)
        n = np.array([c.n_g for c in rows], dtype=float)
        if cap is not None:
            n = np.where(capped, np.minimum(n, cap), n)
        m_lox = np.array([c.stage_lox_kg(stage) for c in rows], dtype=float)
        m_rp1 = np.array([c.stage_rp1_kg(stage) for c in rows], dtype=float)
        upper = np.array([c.upper_mass_kg(stage) for c in rows], dtype=float)
        arrays = _features(n, m_lox, m_rp1, upper)
        blocks: dict[str, np.ndarray] = {}
        for name, values in arrays.items():
            blocks[f"{name}_max"] = _block_stats(values, CASE_BLOCK_SIZE, np.max)
            blocks[f"{name}_min"] = _block_stats(values, CASE_BLOCK_SIZE, np.min)
        return CaseFeatures(index=np.asarray(index), capped=capped, arrays=arrays, blocks=blocks)


def pad_load_set(cases: Sequence[LoadCase]) -> PadLoadSet:
    """Prepare the pad baseline's load cases for the envelope.

    Input: the LoadCases of the pad baseline's recorded flight (sim.py's adapter: its HOLD
    rows, the stage-1 flight and the stage-2 burn), at least one HOLD row (the skirt's
    hold-down envelope) and one stage-1 flight row (MECO); no push.
    Output: a PadLoadSet. Stage-1 elements take the HOLD and stage-1 flight rows; stage-2
    elements take the same rows (stage 2 full on them) and the stage-2 burn (design 4.2.4:
    the pad's full-flight envelope). Frame: the stack axis.
    """
    cases = tuple(cases)
    if any(c.kind == PUSH for c in cases):
        raise ValueError("a pad envelope takes HOLD and flight cases only")
    stage1 = np.array([i for i, c in enumerate(cases) if c.stage1_attached], dtype=int)
    hold = np.array([i for i, c in enumerate(cases) if c.kind == HOLD], dtype=int)
    flight1 = [i for i, c in enumerate(cases) if c.kind == FLIGHT and c.stage1_attached]
    burn2 = [i for i, c in enumerate(cases) if not c.stage1_attached]
    if hold.size == 0:
        raise ValueError("the pad's load cases need a HOLD row (the skirt's hold-down envelope)")
    if not flight1:
        raise ValueError("the pad's load cases need the stage-1 flight")
    meco = max(flight1, key=lambda i: (cases[i].t_s, i))
    stage2 = np.array([*stage1.tolist(), *burn2], dtype=int)
    return PadLoadSet(
        cases=cases,
        stage1_cases=stage1,
        stage2_cases=stage2,
        hold_cases=hold,
        meco_case=meco,
    )


# ======================================================================== S2: thickness


def _hoop_array(
    p: np.ndarray, r: float, fs: float, f_tu: float, eta: float, relief: float
) -> np.ndarray:
    """``hoop_thickness_m`` on an array of pressures [Pa] (the same arithmetic)."""
    p_design = fs * p - relief
    return np.where(p_design > 0.0, p_design * r / (f_tu * eta), 0.0)


def _von_mises_array(
    p: np.ndarray, n_design: np.ndarray, r: float, fs: float, f_tu: float, eta: float
) -> np.ndarray:
    """``von_mises_thickness_m`` on arrays (the same arithmetic), sizing net compression
    only: N_d is clamped at 0 (in net tension the hoop mode governs a pressurized wall,
    B <= p_min r/2 <= A/2, and an unpressurized wall in net tension is a tension mode the
    design does not size)."""
    a = fs * np.maximum(p, 0.0) * r
    b = -np.maximum(n_design, 0.0) / (2.0 * math.pi * r)
    return np.sqrt(a * a - a * b + b * b) / (f_tu * eta)


def _gerard_array(
    n_design: np.ndarray, r: float, e: float, k_s: float, row: GerardRow
) -> np.ndarray:
    """``gerard_stiffened_thickness_m`` on an array of loads [N] (the same arithmetic)."""
    d = 2.0 * r
    out = np.zeros_like(n_design, dtype=float)
    pos = n_design > 0.0
    n_x = n_design[pos] / (2.0 * math.pi * r)
    out[pos] = (d / 4.0) * row.c * (n_x / (k_s * e * d)) ** row.exponent
    return out


def _gerard_row(name: str) -> GerardRow:
    """The GERARD_ROWS row called ``name``."""
    for row in GERARD_ROWS:
        if row.name == name:
            return row
    raise ValueError(f"no Gerard row named {name!r}")


def _compression_array(
    mode: str,
    n_design: np.ndarray,
    r: float,
    coeffs: StructureCoefficients,
    p_stab: float,
    anchor: np.ndarray | None,
) -> np.ndarray:
    """The compression mode's thickness [m] at each design load [N] (net, ultimate).

    mode MODE_MONOCOQUE: SP-8007 (S1's solve, one call per load, stabilized at p_stab, the
    tank's minimum pressure); a Gerard row's name: its smeared thickness; PLATE_LIMITED:
    t_ref (N_d / N_env) with t_ref the anchor row's thickness at N_env = ``anchor`` (one per
    station, broadcast along the trailing axis), the anchor row itself where N_env <= 0.
    """
    if mode == MODE_MONOCOQUE:
        checked = _monocoque_inputs(
            r, coeffs.e_pa, coeffs.nu, p_stab, coeffs.s_dg, coeffs.delta_gamma_table
        )
        flat = [
            _monocoque_solve(_require_finite("n_design_N", float(x)), *checked)
            for x in np.ravel(n_design)
        ]
        return np.array(flat, dtype=float).reshape(np.shape(n_design))
    if mode == PLATE_LIMITED:
        if anchor is None:
            raise ValueError("the plate-limited row needs its envelope anchor")
        anchor_b = np.broadcast_to(
            anchor.reshape(anchor.shape + (1,) * (n_design.ndim - anchor.ndim)), n_design.shape
        )
        t_ref = _gerard_array(anchor_b, r, coeffs.e_pa, coeffs.k_stiff, PLATE_ANCHOR_ROW)
        out = np.zeros_like(n_design, dtype=float)
        ok = (n_design > 0.0) & (anchor_b > 0.0)
        out[ok] = t_ref[ok] * (n_design[ok] / anchor_b[ok])
        fallback = (n_design > 0.0) & ~(anchor_b > 0.0)
        if np.any(fallback):
            out[fallback] = _gerard_array(
                n_design[fallback], r, coeffs.e_pa, coeffs.k_stiff, PLATE_ANCHOR_ROW
            )
        return out
    return _gerard_array(n_design, r, coeffs.e_pa, coeffs.k_stiff, _gerard_row(mode))


def _compression_mode(tank: str, coeffs: StructureCoefficients) -> str:
    """The compression mode of a wall: monocoque for a LOX barrel (FUG Table 2-1), the
    active stiffened row for an RP-1 barrel and the aft skirt (tank "")."""
    return MODE_MONOCOQUE if tank == LOX else coeffs.gerard_row


def _station_design_load(
    q: np.ndarray, lam: float, fs: float, p_min: float, area: float
) -> np.ndarray:
    """N_d = FS_u (lambda g0 Q) - p_min A [N]: the factored load of a compression driver Q
    [kg in g0 units] with the margin factor lambda, relieved by the tank's minimum
    pressure (unfactored, unscaled)."""
    return fs * (lam * from_g(q)) - p_min * area


def _station_pressure(p_bar: np.ndarray, lam: float, p_meop: float, area: float) -> np.ndarray:
    """p = lambda (p_meop + g0 P/A) [Pa]: the barrel pressure of a head driver P [kg in g0
    units] at the tank's ullage MEOP, scaled by the margin factor lambda."""
    return lam * (p_meop + from_g(p_bar) / area)


def _head_driver(am: np.ndarray, k: np.ndarray, n: np.ndarray) -> np.ndarray:
    """P = max(am - k n, 0) [kg in g0 units]: the head driver n (m - k)+ of a tank at
    stations of mass height k (am = n m)."""
    return np.maximum(am - k * n, 0.0)


def _rowwise_max(
    value: Callable[[np.ndarray, np.ndarray], np.ndarray],
    bound: np.ndarray,
    n_cases: int,
    floor: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """The exact maximum over cases of value(row, case) for every row, by blocks.

    Inputs: value(rows (S, 1), cases (S, B)) -> (S, B), the exact values; bound (rows,
    blocks), an upper bound of value over each block of CASE_BLOCK_SIZE consecutive cases;
    n_cases; floor (rows,) or None: a value the maximum is only needed above.
    Output: (best, arg) per row. The block with the largest bound is evaluated first; every
    other block whose bound exceeds max(that block's maximum, floor) is evaluated too, and
    a block whose bound does not cannot hold a larger value, so ``best`` is the exact
    maximum wherever it exceeds the floor (elsewhere it is at most the floor). arg is the
    maximizing case (the first block's when the floor wins; -1 never occurs).
    """
    n_rows = bound.shape[0]
    offsets = np.arange(CASE_BLOCK_SIZE)
    rows = np.arange(n_rows)
    first = np.argmax(bound, axis=1)
    cases0 = np.minimum(first[:, None] * CASE_BLOCK_SIZE + offsets, n_cases - 1)
    values0 = value(rows[:, None], cases0)
    pick0 = np.argmax(values0, axis=1)
    best = values0[rows, pick0].copy()
    arg = cases0[rows, pick0].copy()
    level = best if floor is None else np.maximum(best, floor)
    mask = bound > level[:, None]
    mask[rows, first] = False
    if np.any(mask):
        r_s, b_s = np.nonzero(mask)
        cases_s = np.minimum(b_s[:, None] * CASE_BLOCK_SIZE + offsets, n_cases - 1)
        values_s = value(r_s[:, None], cases_s)
        pick = np.argmax(values_s, axis=1)
        vmax = values_s[np.arange(r_s.size), pick]
        cmax = cases_s[np.arange(r_s.size), pick]
        np.maximum.at(best, r_s, vmax)
        won = vmax == best[r_s]
        arg[r_s[won]] = cmax[won]
    return best, arg


def _governing(stack: np.ndarray, names: Sequence[str]) -> tuple[np.ndarray, list[str]]:
    """(max, mode names) along axis 0 of a (modes, ...) stack; ties go to the earlier
    mode."""
    pick = np.argmax(stack, axis=0)
    return np.take_along_axis(stack, pick[None, ...], axis=0)[0], [names[i] for i in np.ravel(pick)]


# ======================================================================== S2: the envelope


@dataclass(frozen=True, eq=False)
class ElementEnvelope:
    """The envelope of one element: stage, element; z_m, the station heights [m, stack
    frame] (one value for a dome or the tube: its crown or bottom); t_m, the required
    thickness at each station [m]; modes, the governing mode at each station; case_index,
    the governing case's index in the PadLoadSet (-1: the minimum gauge, no case);
    design_compression_N, each station's envelope design compression N_env [N] (the
    plate-limited row's anchor; None for the domes and the tube)."""

    stage: str
    element: str
    z_m: np.ndarray
    t_m: np.ndarray
    modes: tuple[str, ...]
    case_index: np.ndarray
    design_compression_N: np.ndarray | None = None


@dataclass(frozen=True, eq=False)
class Envelope:
    """The pad's structural envelope at one margin and cap (``build_envelope``; design 4.2,
    D-SP7-15): the loads and pressures of every pad case times (1 + margin), the pad's
    stage-1 felt n capped at envelope_cap_g [g0] (None: uncapped), drag left out.

    pad: the PadLoadSet; stage1, stage2: element name -> ElementEnvelope (stage2 None when
    not built); upper_stack_nu_kg: the envelope's n U [kg in g0 units], (1 + margin) times
    the stage-1 cases' largest capped n U (the interstage and the upper-stack flag),
    upper_stack_case its case and upper_stack_nu_pad_kg the pad's own largest n U (no
    margin, no cap); skirt_load_N: the skirt's envelope load (1 + margin) S [N] by the
    coefficient set's path and skirt_load_case its case; thrust_structure_N: (1 + margin)
    T_max [N].
    """

    pad: PadLoadSet
    margin: float
    envelope_cap_g: float | None
    stage1: Mapping[str, ElementEnvelope]
    stage2: Mapping[str, ElementEnvelope] | None
    upper_stack_nu_kg: float
    upper_stack_case: int
    upper_stack_nu_pad_kg: float
    skirt_load_N: float
    skirt_load_case: int
    thrust_structure_N: float

    def element(self, stage: str, name: str) -> ElementEnvelope:
        """The ElementEnvelope of a stage role's element (KeyError if not built)."""
        table = self.stage1 if _check_stage(stage) == STAGE1 else self.stage2
        if table is None:
            raise KeyError(f"the envelope of {stage} was not built")
        return table[name]


def _margin_factor(margin: float) -> float:
    """1 + margin, after checking margin >= 0."""
    return 1.0 + _require_non_negative("margin", margin)


def _check_cap(envelope_cap_g: float | None) -> float | None:
    """envelope_cap_g after checking it is None or > 1 g0 (design 4.3)."""
    if envelope_cap_g is None:
        return None
    cap = _require_finite("envelope_cap_g", envelope_cap_g)
    if cap <= 1.0:
        raise ValueError(f"envelope_cap_g must be > 1 g0, got {envelope_cap_g!r}")
    return cap


def _barrel_envelope(
    stage: str,
    sg: StageGeometry,
    barrel: BarrelStations,
    feats: CaseFeatures,
    coeffs: StructureCoefficients,
    lam: float,
) -> ElementEnvelope:
    """The envelope of one barrel: per station, the largest over the cases of the largest of
    hoop, compression, combined and minimum gauge. Hoop rises with the head driver P alone
    and compression with the load driver Q alone, so each is evaluated at its driver's
    exact maximum; the combined mode rises with both and is maximized exactly by blocks
    (``_rowwise_max``) above the other modes' floor."""
    tank = barrel.tank
    r, area = sg.radius_m, sg.area_m2
    fs, f_tu, eta = coeffs.fs_ult, coeffs.f_tu_pa, coeffs.eta_weld
    p_meop, p_min = coeffs.p_meop_pa(stage, tank), coeffs.p_min_pa(stage, tank)
    k, s = barrel.mass_height_kg, barrel.structure_above_kg
    ar, bl = feats.arrays, feats.blocks
    am, aq, n = ar[f"am_{tank}"], ar[f"aq_{tank}"], ar["n"]
    count = feats.count

    def head(rows: np.ndarray, cases: np.ndarray) -> np.ndarray:
        return _head_driver(am[cases], k[rows], n[cases])

    def load(rows: np.ndarray, cases: np.ndarray) -> np.ndarray:
        return aq[cases] + s[rows] * n[cases]

    p_bound = _head_driver(bl[f"am_{tank}_max"][None, :], k[:, None], bl["n_min"][None, :])
    q_bound = bl[f"aq_{tank}_max"][None, :] + s[:, None] * bl["n_max"][None, :]
    p_max, p_arg = _rowwise_max(head, p_bound, count)
    q_max, q_arg = _rowwise_max(load, q_bound, count)
    hoop = _hoop_array(_station_pressure(p_max, lam, p_meop, area), r, fs, f_tu, eta, 0.0)
    n_env = _station_design_load(q_max, lam, fs, p_min, area)
    mode_c = _compression_mode(tank, coeffs)
    comp = _compression_array(mode_c, n_env, r, coeffs, p_min, n_env)
    t_min = np.full(k.shape, coeffs.t_min_m)
    floor = np.maximum(np.maximum(hoop, comp), t_min)

    def combined(rows: np.ndarray, cases: np.ndarray) -> np.ndarray:
        p = _station_pressure(head(rows, cases), lam, p_meop, area)
        return _von_mises_array(
            p, _station_design_load(load(rows, cases), lam, fs, p_min, area), r, fs, f_tu, eta
        )

    vm_bound = _von_mises_array(
        _station_pressure(p_bound, lam, p_meop, area),
        _station_design_load(q_bound, lam, fs, p_min, area),
        r,
        fs,
        f_tu,
        eta,
    )
    vm_best, vm_arg = _rowwise_max(combined, vm_bound, count, floor)
    names = (MODE_HOOP, mode_c, MODE_COMBINED, MODE_MIN_GAUGE)
    t, modes = _governing(np.stack([hoop, comp, vm_best, t_min]), names)
    args = {MODE_HOOP: p_arg, mode_c: q_arg, MODE_COMBINED: vm_arg}
    case = np.array(
        [int(feats.index[args[m][i]]) if m in args else -1 for i, m in enumerate(modes)],
        dtype=int,
    )
    return ElementEnvelope(
        stage=stage,
        element=LOX_BARREL if tank == LOX else RP1_BARREL,
        z_m=barrel.z_m,
        t_m=t,
        modes=tuple(modes),
        case_index=case,
        design_compression_N=n_env,
    )


def _dome_driver_offset(sg: StageGeometry, coeffs: StructureCoefficients, element: str) -> float:
    """The constant c of a dome's or the tube's head driver D = n (m + c) [kg]: rho A b at
    an aft or common dome's crown (the head runs from the liquid surface to the crown, b
    below the dome's equator), rho_LOX A (L_tube + b) at the transfer tube's bottom."""
    if element == RP1_AFT_DOME:
        return coeffs.rho_rp1_kgm3 * sg.area_m2 * sg.dome_depth_m
    if element == COMMON_DOME:
        return coeffs.rho_lox_kgm3 * sg.area_m2 * sg.dome_depth_m
    if element == TRANSFER_TUBE:
        return coeffs.rho_lox_kgm3 * sg.area_m2 * (sg.tube_length_m + sg.dome_depth_m)
    raise ValueError(f"{element!r} has no head driver")


def _area_thickness(
    stage: str,
    sg: StageGeometry,
    coeffs: StructureCoefficients,
    element: str,
    driver: float,
    lam: float,
) -> float:
    """The thickness [m] of a dome or the tube at a head driver D [kg in g0 units] and the
    margin factor lambda, floored at the minimum gauge: aft dome p = lambda (p_meop,RP1 +
    g0 D/A); common dome lambda (p_meop,LOX + g0 D/A) less p_min,RP1 (unfactored, once);
    forward dome lambda p_meop,LOX (ullage only); tube lambda (p_meop,LOX + g0 D/A) less
    p_min,RP1 outside."""
    r, area = sg.radius_m, sg.area_m2
    fs, eta = coeffs.fs_ult, coeffs.eta_weld
    if element == FORWARD_DOME:
        p = lam * coeffs.p_meop_pa(stage, LOX)
        t = dome_crown_thickness_m(p, r, coeffs.dome_axis_ratio, fs, coeffs.dome_f_tu_pa, eta)
    elif element == RP1_AFT_DOME:
        p = lam * (coeffs.p_meop_pa(stage, RP1) + from_g(driver) / area)
        t = dome_crown_thickness_m(p, r, coeffs.dome_axis_ratio, fs, coeffs.dome_f_tu_pa, eta)
    elif element == COMMON_DOME:
        p = lam * (coeffs.p_meop_pa(stage, LOX) + from_g(driver) / area)
        t = dome_crown_thickness_m(
            p,
            r,
            coeffs.dome_axis_ratio,
            fs,
            coeffs.dome_f_tu_pa,
            eta,
            p_relief_pa=coeffs.p_min_pa(stage, RP1),
        )
    elif element == TRANSFER_TUBE:
        p = lam * (coeffs.p_meop_pa(stage, LOX) + from_g(driver) / area)
        t = tube_hoop_thickness_m(
            p,
            0.5 * sg.tube_diameter_m,
            fs,
            coeffs.f_tu_pa,
            eta,
            p_relief_pa=coeffs.p_min_pa(stage, RP1),
        )
    else:
        raise ValueError(f"{element!r} is not a dome or the tube")
    return max(t, coeffs.t_min_m)


_AREA_TANK = {RP1_AFT_DOME: RP1, COMMON_DOME: LOX, TRANSFER_TUBE: LOX}


def _area_z(sg: StageGeometry, element: str) -> float:
    """The height [m, stack frame] an area element is sized at: a dome's crown, the tube's
    bottom (the aft-dome crown)."""
    if element == RP1_AFT_DOME:
        return sg.rp1_barrel.z_bottom_m - sg.dome_depth_m
    if element == COMMON_DOME:
        return sg.lox_barrel.z_bottom_m - sg.dome_depth_m
    if element == FORWARD_DOME:
        return sg.top_z_m + sg.dome_depth_m
    return sg.rp1_barrel.z_bottom_m - sg.dome_depth_m


def _area_envelope(
    stage: str,
    sg: StageGeometry,
    feats: CaseFeatures,
    coeffs: StructureCoefficients,
    element: str,
    lam: float,
) -> ElementEnvelope:
    """The envelope of a dome or the tube: its thickness rises with its single head driver
    D = n (m + c), linear in the case features, so it is evaluated at D's maximum."""
    if element == FORWARD_DOME:
        t = _area_thickness(stage, sg, coeffs, element, 0.0, lam)
        mode, case = MODE_MEMBRANE, -1
    else:
        tank = _AREA_TANK[element]
        drivers = (
            feats.arrays[f"am_{tank}"]
            + _dome_driver_offset(sg, coeffs, element) * feats.arrays["n"]
        )
        j = int(np.argmax(drivers))
        t = _area_thickness(stage, sg, coeffs, element, float(drivers[j]), lam)
        case = int(feats.index[j])
        mode = MODE_HOOP if element == TRANSFER_TUBE else MODE_MEMBRANE
    if t == coeffs.t_min_m:
        mode, case = MODE_MIN_GAUGE, -1
    return ElementEnvelope(
        stage=stage,
        element=element,
        z_m=np.array([_area_z(sg, element)]),
        t_m=np.array([t]),
        modes=(mode,),
        case_index=np.array([case], dtype=int),
    )


def _skirt_design_load(load_N: float | np.ndarray, lam: float, fs: float) -> np.ndarray:
    """N_d = FS_u (lambda S) [N]: the unpressurized skirt's factored compression (no
    relief)."""
    return fs * (lam * np.asarray(load_N, dtype=float))


def _require_skirt(sg: StageGeometry) -> BarrelStations:
    """The stage's aft-skirt stations (ValueError for a stage without a skirt)."""
    if sg.skirt is None:
        raise ValueError(f"{sg.role} has no aft skirt")
    return sg.skirt


def _skirt_thickness(
    sg: StageGeometry, coeffs: StructureCoefficients, n_design: np.ndarray, anchor: float
) -> tuple[np.ndarray, str]:
    """The skirt's thickness at each station [m] for a design load [N] (uniform along it)
    and its mode: the active stiffened row (plate-limited anchored at ``anchor`` [N]),
    floored at the minimum gauge."""
    skirt = _require_skirt(sg)
    loads = np.full(skirt.z_m.shape, float(n_design))
    anchors = np.full(skirt.z_m.shape, float(anchor))
    comp = _compression_array(coeffs.gerard_row, loads, sg.radius_m, coeffs, 0.0, anchors)
    t = np.maximum(comp, coeffs.t_min_m)
    mode = coeffs.gerard_row if comp[0] > coeffs.t_min_m else MODE_MIN_GAUGE
    return t, mode


def _skirt_envelope(
    sg: StageGeometry,
    pad: PadLoadSet,
    feats: CaseFeatures,
    coeffs: StructureCoefficients,
    lam: float,
) -> tuple[ElementEnvelope, float, int]:
    """The aft skirt's envelope, its load (1 + margin) S [N] and that load's case: S the
    pad's largest hold-down support (SKIRT_HOLD_DOWN), or the larger of it and the
    stage-1 cases' largest flight product g0 n (U + s + m_LOX + m_RP1) with s the
    structure above the skirt (SKIRT_FLIGHT_THRUST)."""
    support = np.array([pad.cases[i].hold_down_support_N for i in pad.hold_cases], dtype=float)
    j = int(np.argmax(support))
    load, case = float(support[j]), int(pad.hold_cases[j])
    if coeffs.skirt_envelope_path == SKIRT_FLIGHT_THRUST:
        product = feats.arrays["aq_skirt"] + sg.skirt_structure_above_kg * feats.arrays["n"]
        jf = int(np.argmax(product))
        flight = float(from_g(product[jf]))
        if flight > load:
            load, case = flight, int(feats.index[jf])
    n_design = float(_skirt_design_load(load, lam, coeffs.fs_ult))
    t, mode = _skirt_thickness(sg, coeffs, np.asarray(n_design), n_design)
    skirt = _require_skirt(sg)
    stations = skirt.z_m.shape[0]
    element = ElementEnvelope(
        stage=STAGE1,
        element=AFT_SKIRT,
        z_m=skirt.z_m,
        t_m=t,
        modes=(mode,) * stations,
        case_index=np.full(stations, case if mode != MODE_MIN_GAUGE else -1, dtype=int),
        design_compression_N=np.full(stations, n_design),
    )
    return element, lam * load, case


def _stage_envelope(
    stage: str,
    sg: StageGeometry,
    feats: CaseFeatures,
    coeffs: StructureCoefficients,
    lam: float,
) -> dict[str, ElementEnvelope]:
    """The barrels, domes and tube of one stage."""
    out = {
        RP1_BARREL: _barrel_envelope(stage, sg, sg.rp1_barrel, feats, coeffs, lam),
        LOX_BARREL: _barrel_envelope(stage, sg, sg.lox_barrel, feats, coeffs, lam),
    }
    for element in (RP1_AFT_DOME, COMMON_DOME, FORWARD_DOME, TRANSFER_TUBE):
        out[element] = _area_envelope(stage, sg, feats, coeffs, element, lam)
    return out


def build_envelope(
    geometry: StackGeometry,
    coeffs: StructureCoefficients,
    pad: PadLoadSet,
    *,
    margin: float = 0.0,
    envelope_cap_g: float | None = None,
    stages: Sequence[str] = STAGE_ROLES,
) -> Envelope:
    """The pad's structural envelope, exact and fast (design 4.2, D-SP7-15; docs/physics.md
    "The envelope and its candidate reduction").

    Inputs: geometry and coeffs (one coefficient set); pad, the PadLoadSet; margin >= 0
    (loads and pressures times 1 + margin, not thickness; relief unscaled); envelope_cap_g,
    None or > 1 g0, the cap on the pad's stage-1 felt n; stages, the roles to build
    (stage 2 is needed only when the push exceeds the upper stack's envelope).
    Output: an Envelope equal to ``envelope_reference`` (every case at every station) to
    rounding: every mode's thickness is non-decreasing in the station's head driver
    P = n (m - k)+ and in its load driver Q = n (U + s [+ m_LOX]), each linear in the cases'
    coefficient-free features up to the clamp, so the single-driver modes are evaluated at
    their driver's exact maximum and the combined mode by an exact block bound.
    Frame: the stack frame of the geometry.
    """
    lam = _margin_factor(margin)
    cap = _check_cap(envelope_cap_g)
    feats1 = pad.features(STAGE1, cap)
    s1 = _stage_envelope(STAGE1, geometry.stage1, feats1, coeffs, lam)
    skirt, skirt_load, skirt_case = _skirt_envelope(geometry.stage1, pad, feats1, coeffs, lam)
    s1[AFT_SKIRT] = skirt
    nu = feats1.arrays["n_upper"]
    j = int(np.argmax(nu))
    raw = pad.features(STAGE1, None).arrays["n_upper"]
    s2 = None
    if STAGE2 in stages:
        s2 = _stage_envelope(STAGE2, geometry.stage2, pad.features(STAGE2, cap), coeffs, lam)
    return Envelope(
        pad=pad,
        margin=margin,
        envelope_cap_g=cap,
        stage1=s1,
        stage2=s2,
        upper_stack_nu_kg=lam * float(nu[j]),
        upper_stack_case=int(feats1.index[j]),
        upper_stack_nu_pad_kg=float(np.max(raw)),
        skirt_load_N=skirt_load,
        skirt_load_case=skirt_case,
        thrust_structure_N=lam * geometry.stage1.thrust_vac_N,
    )


def envelope_reference(
    geometry: StackGeometry,
    coeffs: StructureCoefficients,
    pad: PadLoadSet,
    *,
    margin: float = 0.0,
    envelope_cap_g: float | None = None,
    stages: Sequence[str] = STAGE_ROLES,
) -> Envelope:
    """The envelope's definition, evaluated on every case at every station with S1's
    scalar primitives (slow: stations x cases x modes calls; ``build_envelope`` equals it to
    rounding and is what the model uses; tests compare them).

    Inputs and output as ``build_envelope``: per station the largest over the cases of the
    largest of hoop (``hoop_thickness_m``), compression (``monocoque_buckling_thickness_m``,
    ``gerard_stiffened_thickness_m``, ``plate_limited_thickness_m`` anchored at the
    station's largest design compression), combined (``von_mises_thickness_m`` of the net
    compression) and the minimum gauge; domes and the tube at every case; the skirt, the
    upper stack and the thrust structure as ``build_envelope``.
    Frame: the stack frame of the geometry.
    """
    lam = _margin_factor(margin)
    cap = _check_cap(envelope_cap_g)
    fs, f_tu, eta, e, nu = coeffs.fs_ult, coeffs.f_tu_pa, coeffs.eta_weld, coeffs.e_pa, coeffs.nu
    anchor_row = PLATE_ANCHOR_ROW

    def stage_reference(stage: str, sg: StageGeometry) -> dict[str, ElementEnvelope]:
        feats = pad.features(stage, cap)
        ar = feats.arrays
        out: dict[str, ElementEnvelope] = {}
        r, area = sg.radius_m, sg.area_m2
        for barrel in (sg.rp1_barrel, sg.lox_barrel):
            tank = barrel.tank
            p_meop, p_min = coeffs.p_meop_pa(stage, tank), coeffs.p_min_pa(stage, tank)
            mode_c = _compression_mode(tank, coeffs)
            t_out, m_out, c_out, n_out = [], [], [], []
            for i in range(barrel.z_m.shape[0]):
                k, s = float(barrel.mass_height_kg[i]), float(barrel.structure_above_kg[i])
                pressures, loads = [], []
                for c in range(feats.count):
                    n_c = float(ar["n"][c])
                    head = max(float(ar[f"am_{tank}"][c]) - k * n_c, 0.0)
                    pressures.append(lam * (p_meop + float(from_g(head)) / area))
                    q = float(ar[f"aq_{tank}"][c]) + s * n_c
                    loads.append(fs * (lam * float(from_g(q))) - p_min * area)
                n_env = max(loads)
                t_ref = gerard_stiffened_thickness_m(
                    n_env, r, e, coeffs.k_stiff, anchor_row.c, anchor_row.exponent
                )
                best, best_mode, best_case = -1.0, MODE_MIN_GAUGE, -1
                for c in range(feats.count):
                    p, n_d = pressures[c], loads[c]
                    if mode_c == MODE_MONOCOQUE:
                        comp = monocoque_buckling_thickness_m(
                            n_d, r, e, nu, p_min, coeffs.s_dg, coeffs.delta_gamma_table
                        )
                    elif mode_c == PLATE_LIMITED:
                        comp = (
                            plate_limited_thickness_m(n_d, n_env, t_ref)
                            if n_env > 0.0
                            else gerard_stiffened_thickness_m(
                                n_d, r, e, coeffs.k_stiff, anchor_row.c, anchor_row.exponent
                            )
                        )
                    else:
                        row = _gerard_row(mode_c)
                        comp = gerard_stiffened_thickness_m(
                            n_d, r, e, coeffs.k_stiff, row.c, row.exponent
                        )
                    candidates = (
                        (hoop_thickness_m(p, r, fs, f_tu, eta), MODE_HOOP),
                        (comp, mode_c),
                        (von_mises_thickness_m(p, r, max(n_d, 0.0), fs, f_tu, eta), MODE_COMBINED),
                    )
                    for value, mode in candidates:
                        if value > best:
                            best, best_mode, best_case = value, mode, int(feats.index[c])
                if coeffs.t_min_m > best:
                    best, best_mode, best_case = coeffs.t_min_m, MODE_MIN_GAUGE, -1
                t_out.append(best)
                m_out.append(best_mode)
                c_out.append(best_case)
                n_out.append(n_env)
            out[LOX_BARREL if tank == LOX else RP1_BARREL] = ElementEnvelope(
                stage=stage,
                element=LOX_BARREL if tank == LOX else RP1_BARREL,
                z_m=barrel.z_m,
                t_m=np.array(t_out),
                modes=tuple(m_out),
                case_index=np.array(c_out, dtype=int),
                design_compression_N=np.array(n_out),
            )
        for element in (RP1_AFT_DOME, COMMON_DOME, FORWARD_DOME, TRANSFER_TUBE):
            best, best_case = -1.0, -1
            for c in range(feats.count):
                if element == FORWARD_DOME:
                    driver = 0.0
                else:
                    tank = _AREA_TANK[element]
                    driver = float(ar[f"am_{tank}"][c]) + _dome_driver_offset(
                        sg, coeffs, element
                    ) * float(ar["n"][c])
                value = _area_thickness(stage, sg, coeffs, element, driver, lam)
                if value > best:
                    best, best_case = value, int(feats.index[c])
            mode = MODE_HOOP if element == TRANSFER_TUBE else MODE_MEMBRANE
            if best == coeffs.t_min_m or element == FORWARD_DOME:
                best_case = -1
                mode = MODE_MIN_GAUGE if best == coeffs.t_min_m else MODE_MEMBRANE
            out[element] = ElementEnvelope(
                stage=stage,
                element=element,
                z_m=np.array([_area_z(sg, element)]),
                t_m=np.array([best]),
                modes=(mode,),
                case_index=np.array([best_case], dtype=int),
            )
        return out

    feats1 = pad.features(STAGE1, cap)
    s1 = stage_reference(STAGE1, geometry.stage1)
    skirt, skirt_load, skirt_case = _skirt_envelope(geometry.stage1, pad, feats1, coeffs, lam)
    s1[AFT_SKIRT] = skirt
    nu_values = [float(x) for x in feats1.arrays["n_upper"]]
    j = int(np.argmax(nu_values))
    raw = pad.features(STAGE1, None).arrays["n_upper"]
    s2 = stage_reference(STAGE2, geometry.stage2) if STAGE2 in stages else None
    return Envelope(
        pad=pad,
        margin=margin,
        envelope_cap_g=cap,
        stage1=s1,
        stage2=s2,
        upper_stack_nu_kg=lam * nu_values[j],
        upper_stack_case=int(feats1.index[j]),
        upper_stack_nu_pad_kg=float(np.max(raw)),
        skirt_load_N=skirt_load,
        skirt_load_case=skirt_case,
        thrust_structure_N=lam * geometry.stage1.thrust_vac_N,
    )


# ======================================================================== S2: the push


@dataclass(frozen=True)
class PushRequirement:
    """A push at its peak (``push_requirement``; design 4.2.1, D-SP7-16).

    dynamic: the DynamicMode; dlf [-]; rise_time_s [s] (the drive's own, else the
    coefficient set's assumed real-drive value) and axial_frequency_hz [Hz] behind it;
    accel_raise_mps2 = a' - a [m/s^2] (constant_accel under ``rise_time``: the plateau a
    drive ramping over t_r needs to reach the same (L, v_e); 0 otherwise), accel_plateau_mps2
    a' and ramp_cost_rel (a' - a)/a (None without a RampedPlateau); n_rest_g [g0] and
    f_rest_N [N]; cases: the push's LoadCases at the peak, n_g = n_rest + DLF (n_q - n_rest)
    and interface_force_N = F_rest + DLF (F_q - F_rest) (the heads use n_peak); n_q_g and
    f_q_N: the quasi-static plateau of each case [g0, N]; release_n_before_g [g0], the
    plateau just before the release (raised as the cases' under ``rise_time``);
    release_n_peak_g = n_rest + DLF (n_before - n_rest) [g0], the largest instantaneous
    load at the release under the same undamped single mode (the ramp's residual
    oscillation, amplitude (DLF - 1)(n_before - n_rest), is still present: damping is not
    credited, as for the peak); release_n_after_g [g0]; release_swing_g = n_after -
    (n_peak,rel - n_after) [g0], the single-mode swing of an instant drop from that peak
    (the conservative bound the flags fire on); release_swing_plateau_g = n_after -
    (n_before - n_after) [g0], the swing from the plateau (the residual fully damped,
    printed beside); release_case.
    """

    dynamic: str
    dlf: float
    rise_time_s: float
    axial_frequency_hz: float
    accel_raise_mps2: float
    accel_plateau_mps2: float | None
    ramp_cost_rel: float | None
    n_rest_g: float
    f_rest_N: float
    cases: tuple[LoadCase, ...]
    n_q_g: tuple[float, ...]
    f_q_N: tuple[float, ...]
    release_n_before_g: float
    release_n_peak_g: float
    release_n_after_g: float
    release_swing_g: float
    release_swing_plateau_g: float
    release_case: LoadCase

    @property
    def n_peak_g(self) -> float:
        """The largest peak felt load factor over the push's cases [g0]."""
        return max(c.n_g for c in self.cases)

    @property
    def f_peak_N(self) -> float:
        """The largest peak interface force over the push's cases [N]."""
        return max(float(c.interface_force_N or 0.0) for c in self.cases)

    @property
    def n_quasi_g(self) -> float:
        """The largest quasi-static plateau over the push's cases [g0]."""
        return max(self.n_q_g)


def push_requirement(
    push: PushLoad, coeffs: StructureCoefficients, dynamic: DynamicMode
) -> PushRequirement:
    """The peak of a push (design 4.2.1, D-SP7-16).

    Inputs: push, the quasi-static PushLoad; coeffs (rise_time_s when the push has none of
    its own, axial_frequency_hz); dynamic, one of DYNAMIC_MODES.
    Output: a PushRequirement. DLF = ``dynamic_load_factor``(t_r, 1/f, dynamic). For a push
    with a RampedPlateau (constant_accel) under ``rise_time`` the plateau is raised by
    a' - a, a' = ``ramped_plateau_accel_mps2``(L, v_e, t_r): n_q += (a' - a)/g0 and
    F_q += m_v (a' - a) (the trajectory is not re-flown, stated); under ``quasi_static``
    and ``step`` the plain plateau. n_peak = ``peak_load``(n_q, n_rest, DLF), F_peak
    likewise; at the release the plateau n_before (raised the same way) carries the same
    undamped residual, so the largest instantaneous load there is n_peak,rel =
    ``peak_load``(n_before, n_rest, DLF), and the instant drop to n_after swings to
    ``peak_load``(n_after, n_peak,rel, 2) = 2 n_after - n_peak,rel (the swing from the
    plateau, 2 n_after - n_before, printed beside).
    Frame: the stack axis.
    """
    t_r = coeffs.rise_time_s if push.rise_time_s is None else push.rise_time_s
    dlf = dynamic_load_factor(t_r, 1.0 / coeffs.axial_frequency_hz, dynamic)
    raise_mps2 = 0.0
    plateau = None
    cost = None
    if push.ramp is not None:
        plateau = push.ramp.accel_net_mps2
        if dynamic == "rise_time":
            plateau = ramped_plateau_accel_mps2(push.ramp.stroke_m, push.ramp.exit_speed_mps, t_r)
            raise_mps2 = plateau - push.ramp.accel_net_mps2
        cost = raise_mps2 / push.ramp.accel_net_mps2
    n_q, f_q, peaks = [], [], []
    for case in push.cases:
        nq = case.n_g + float(to_g(raise_mps2))
        fq = float(case.interface_force_N) + case.vehicle_mass_kg * raise_mps2
        n_q.append(nq)
        f_q.append(fq)
        peaks.append(
            _replace_case(
                case,
                n_g=peak_load(nq, push.n_rest_g, dlf),
                interface_force_N=peak_load(fq, push.f_rest_N, dlf),
            )
        )
    before = push.release.n_before_g + float(to_g(raise_mps2))
    peak_rel = peak_load(before, push.n_rest_g, dlf)
    after = push.release.n_after_g
    return PushRequirement(
        dynamic=dynamic,
        dlf=dlf,
        rise_time_s=t_r,
        axial_frequency_hz=coeffs.axial_frequency_hz,
        accel_raise_mps2=raise_mps2,
        accel_plateau_mps2=plateau,
        ramp_cost_rel=cost,
        n_rest_g=push.n_rest_g,
        f_rest_N=push.f_rest_N,
        cases=tuple(peaks),
        n_q_g=tuple(n_q),
        f_q_N=tuple(f_q),
        release_n_before_g=before,
        release_n_peak_g=peak_rel,
        release_n_after_g=after,
        release_swing_g=peak_load(after, peak_rel, DLF_STEP),
        release_swing_plateau_g=peak_load(after, before, DLF_STEP),
        release_case=push.release.case,
    )


def _replace_case(case: LoadCase, **changes: float) -> LoadCase:
    """A copy of ``case`` with some numbers changed."""
    values = {name: getattr(case, name) for name in case.__dataclass_fields__}
    values.update(changes)
    return LoadCase(**values)


# ======================================================================== S2: the ring check

SAINT_VENANT_TERMS = 400
"""Odd terms of Saint-Venant's series for a solid rectangle (n = 1, 3, ..., 799): the
torsion constant converges as n^-5 and the long face's shear as n^-2 cosh^-1; the short
face's alternating series converges slowest, to about 1e-6 of its value."""
RING_SPAN_POINTS = 401
"""Points of the half span (midspan to pad) on which the ring's check is evaluated."""
RING_FACE_POINTS = 21
"""Points along each half face (neutral axis or midpoint to corner) of the section."""
RING_CHECK_RTOL = 1.0e-9
"""The relative excess over F_tu at which the ring's combined check binds; below it the
bending at the pads, sized to F_tu exactly by S1, governs (rounding only)."""
RING_BRACKET_MARGIN = 1.0e-9
"""The relative widening of the ring check's upper bracket b_bend sqrt(ratio) (the ratio
falls at least as b^-2, so the root lies at or below it; the margin covers rounding)."""
RING_XTOL_M = 1.0e-15
"""The absolute tolerance [m] of the ring check's brentq root on the width b (far below
the ring's millimetre widths; brentq's relative tolerance is RING_RTOL)."""

RING_RTOL: float = MONOCOQUE_RTOL
"""brentq's relative tolerance [-] on the ring check's width: four machine epsilons, scipy's
default and the smallest brentq accepts (the value MONOCOQUE_RTOL states)."""


def rectangle_torsion_factors(aspect_h_over_b: float) -> tuple[float, float, float]:
    """Saint-Venant torsion of a solid rectangle b x h, h = k b >= b (Timoshenko and
    Goodier, Theory of Elasticity, the rectangular bar).

    Input: aspect_h_over_b k [-], >= 1.
    Output: (beta, alpha, ratio): the torsion constant J = beta h b^3; the largest shear,
    at the midpoint of a long face, tau = T / (alpha h b^2); ratio, the short face's
    midpoint shear over the long face's. With odd n: beta = (1/3)[1 - (192/(pi^5 k)) sum
    tanh(n pi k/2)/n^5], alpha = beta / c_L(0), c_L(0) = 1 - (8/pi^2) sum 1/(n^2 cosh(n pi
    k/2)) (0.208 and 0.141 for a square, 0.246 and 0.229 at k = 2, 1/3 as k grows).
    Frame: the section's own axes.
    """
    k = _require_finite("aspect_h_over_b", aspect_h_over_b)
    if k < 1.0:
        raise ValueError(f"aspect_h_over_b must be >= 1, got {aspect_h_over_b!r}")
    beta, long_face, short_face = _saint_venant(k)
    return beta, float(beta / long_face[0]), float(short_face[0] / long_face[0])


def _saint_venant(k: float) -> tuple[float, np.ndarray, np.ndarray]:
    """(beta, c_L(zeta), c_S(xi)) on RING_FACE_POINTS of each half face: the shear on the
    long face at height zeta h (zeta from 0 at the neutral axis to 1/2 at the corner) and on
    the short face at xi b (from its midpoint to the corner), both as tau = T c/(beta k b^3)
    (G theta = T/(beta k b^4))."""
    odd = 2.0 * np.arange(SAINT_VENANT_TERMS, dtype=float) + 1.0
    w = odd * math.pi * k / 2.0
    beta = (1.0 / 3.0) * (1.0 - (192.0 / (math.pi**5 * k)) * float(np.sum(np.tanh(w) / odd**5)))
    zeta = np.linspace(0.0, 0.5, RING_FACE_POINTS)
    u = odd[None, :] * math.pi * k * zeta[:, None]
    # cosh(u)/cosh(w) without overflow: exp(u - w) (1 + e^-2u)/(1 + e^-2w)
    ratio = np.exp(u - w[None, :]) * (1.0 + np.exp(-2.0 * u)) / (1.0 + np.exp(-2.0 * w[None, :]))
    long_face = 1.0 - (8.0 / math.pi**2) * np.sum(ratio / odd[None, :] ** 2, axis=1)
    xi = np.linspace(0.0, 0.5, RING_FACE_POINTS)
    sign = np.where(np.arange(SAINT_VENANT_TERMS) % 2 == 0, 1.0, -1.0)
    terms = sign[None, :] * np.tanh(w)[None, :] * np.cos(odd[None, :] * math.pi * xi[:, None])
    short_face = (8.0 / math.pi**2) * np.abs(np.sum(terms / odd[None, :] ** 2, axis=1))
    return beta, np.maximum(long_face, 0.0), short_face


def _ring_loads(
    f_peak_N: float, radius_m: float, n_pads: int, fs_ult: float, fitting_factor: float
) -> tuple[float, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(alpha, phi, |M|, |T|, |V|) on RING_SPAN_POINTS of the half span at ultimate: the
    factored q_u = FS_u f_fit F/(2 pi r), M = q_u r^2 ((alpha/sin alpha) cos phi - 1),
    T = q_u r^2 (phi - (alpha/sin alpha) sin phi), V = q_u r phi, phi from the midspan."""
    alpha = math.pi / _require_pad_count(n_pads)
    q = fs_ult * fitting_factor * f_peak_N / (2.0 * math.pi * radius_m)
    phi = np.linspace(0.0, alpha, RING_SPAN_POINTS)
    ratio = alpha / math.sin(alpha)
    moment = np.abs(q * radius_m**2 * (ratio * np.cos(phi) - 1.0))
    torsion = np.abs(q * radius_m**2 * (phi - ratio * np.sin(phi)))
    shear = q * radius_m * phi
    return alpha, phi, moment, torsion, shear


def ring_shear_ratio(
    f_peak_N: float,
    radius_m: float,
    n_pads: int,
    aspect_h_over_b: float,
    fs_ult: float,
    f_tu_pa: float,
    fitting_factor: float,
    *,
    width_m: float | None = None,
) -> float:
    """The ring frame's torsion-plus-shear check at the neutral axis (source note section
    11; section 13 item 15, adopted by D-SP7-37).

    Inputs: as ``ring_frame_mass_kg`` (f_peak_N [N], radius_m [m], n_pads, the integer pad
    count, aspect_h_over_b k >= 1, fs_ult, f_tu_pa [Pa], fitting_factor); width_m, the
    section's width b [m] (None: S1's bending width).
    Output: the largest over the half span of (tau_T + tau_V)/(F_tu/sqrt(3)) [-], with
    tau_T = |T|/(alpha h b^2) the torsion's peak shear on the long face's midpoint and
    tau_V = 1.5 |V|/(b h) the transverse shear there, at ultimate (q factored by FS_u and
    the fitting factor). Below 1 the neutral axis passes (8 pads, k 6.5: 0.85; k 12: 1.28;
    the note's table).
    Frame: the ring's section, h axial (along the push), b radial.
    """
    k = _require_finite("aspect_h_over_b", aspect_h_over_b)
    if k < 1.0:
        raise ValueError(f"aspect_h_over_b must be >= 1, got {aspect_h_over_b!r}")
    b = (
        _ring_bending_width_m(f_peak_N, radius_m, n_pads, k, fs_ult, f_tu_pa, fitting_factor)
        if width_m is None
        else _require_positive("width_m", width_m)
    )
    beta, long_face, _ = _saint_venant(k)
    _, _, _, torsion, shear = _ring_loads(f_peak_N, radius_m, n_pads, fs_ult, fitting_factor)
    tau = torsion * long_face[0] / (beta * k * b**3) + 1.5 * shear / (k * b * b)
    return float(np.max(tau)) / (f_tu_pa / math.sqrt(3.0))


def _ring_von_mises_ratio(
    b: float,
    k: float,
    sv: tuple[float, np.ndarray, np.ndarray],
    loads: tuple[float, np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    f_tu: float,
) -> float:
    """The largest von Mises stress over the half span and the section's boundary, over
    F_tu: on the long face at zeta h, sqrt(sigma^2 + 3 (tau_T + tau_V)^2) with sigma =
    12 M zeta/(k^2 b^3), tau_V = (1.5 V/(k b^2))(1 - 4 zeta^2); on the short face (the
    outer fibre), sqrt(sigma_max^2 + 3 tau_T^2) with no transverse shear."""
    beta, long_face, short_face = sv
    _, _, moment, torsion, shear = loads
    zeta = np.linspace(0.0, 0.5, RING_FACE_POINTS)
    sigma_long = 12.0 * moment[:, None] * zeta[None, :] / (k * k * b**3)
    tau_long = torsion[:, None] * long_face[None, :] / (beta * k * b**3) + (
        1.5 * shear[:, None] / (k * b * b)
    ) * (1.0 - 4.0 * zeta[None, :] ** 2)
    vm_long = np.sqrt(sigma_long**2 + 3.0 * tau_long**2)
    sigma_max = 6.0 * moment[:, None] / (k * k * b**3)
    tau_short = torsion[:, None] * short_face[None, :] / (beta * k * b**3)
    vm_short = np.sqrt(sigma_max**2 + 3.0 * tau_short**2)
    return max(float(np.max(vm_long)), float(np.max(vm_short))) / f_tu


@dataclass(frozen=True)
class RingSizing:
    """The ring frame sized to the larger of S1's bending and the torsion-plus-shear and von
    Mises check (``ring_frame_section``): width_bending_m (S1's b), width_m (the sized b) and
    depth_m h = k b [m]; mass_kg, the ideal mass 2 pi r rho k b^2 [kg] (before the factors);
    mass_bending_kg, S1's (``ring_frame_mass_kg``); shear_ratio and von_mises_ratio at the
    bending width [-]; governing, MODE_RING_BENDING or MODE_RING_CHECK."""

    width_bending_m: float
    width_m: float
    depth_m: float
    mass_kg: float
    mass_bending_kg: float
    shear_ratio: float
    von_mises_ratio: float
    governing: str


def ring_frame_section(
    f_peak_N: float,
    radius_m: float,
    n_pads: int,
    aspect_h_over_b: float,
    fs_ult: float,
    f_tu_pa: float,
    fitting_factor: float,
    rho_kgm3: float,
) -> RingSizing:
    """The ring frame sized to the larger of S1's bending and the combined check (D-SP7-37;
    source note section 13 item 15).

    Inputs: as ``ring_frame_mass_kg`` (aspect_h_over_b k >= 1 here: h is the deeper side).
    Output: a RingSizing. The width b is S1's bending width when the von Mises stress over
    the half span and the section's boundary (torsion by Saint-Venant's series, transverse
    shear 1.5 V/(b h) parabolic over the depth, bending sigma = M z/I; at ultimate) stays
    within F_tu (1 + RING_CHECK_RTOL); else the smallest b at which it does (brentq; every
    stress falls as b^-2 or b^-3, so the ratio falls with b and b <= b_bend sqrt(ratio)).
    The neutral axis of the long face is one of the boundary points, so the shear check of
    ``ring_shear_ratio`` is included. 0 mass for F <= 0.
    Frame: the ring's section, h axial, b radial.
    """
    k = _require_finite("aspect_h_over_b", aspect_h_over_b)
    if k < 1.0:
        raise ValueError(f"aspect_h_over_b must be >= 1, got {aspect_h_over_b!r}")
    rho = _require_positive("rho_kgm3", rho_kgm3)
    r = _require_positive("radius_m", radius_m)
    mass_bending = ring_frame_mass_kg(f_peak_N, r, n_pads, k, fs_ult, f_tu_pa, fitting_factor, rho)
    if f_peak_N <= 0.0:
        return RingSizing(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, MODE_RING_BENDING)
    b_bend = _ring_bending_width_m(f_peak_N, r, n_pads, k, fs_ult, f_tu_pa, fitting_factor)
    sv = _saint_venant(k)
    loads = _ring_loads(f_peak_N, r, n_pads, fs_ult, fitting_factor)
    vm0 = _ring_von_mises_ratio(b_bend, k, sv, loads, f_tu_pa)
    shear0 = ring_shear_ratio(f_peak_N, r, n_pads, k, fs_ult, f_tu_pa, fitting_factor)
    b, governing = b_bend, MODE_RING_BENDING
    if vm0 > 1.0 + RING_CHECK_RTOL:
        b_hi = b_bend * math.sqrt(vm0) * (1.0 + RING_BRACKET_MARGIN)
        b = float(
            brentq(
                lambda w: _ring_von_mises_ratio(w, k, sv, loads, f_tu_pa) - 1.0,
                b_bend,
                b_hi,
                xtol=RING_XTOL_M,
                rtol=RING_RTOL,
            )
        )
        governing = MODE_RING_CHECK
    mass = 2.0 * math.pi * r * rho * k * b * b
    return RingSizing(
        width_bending_m=b_bend,
        width_m=b,
        depth_m=k * b,
        mass_kg=mass if governing == MODE_RING_CHECK else mass_bending,
        mass_bending_kg=mass_bending,
        shear_ratio=shear0,
        von_mises_ratio=vm0,
        governing=governing,
    )


# ======================================================================== S2: relations


def interstage_increment_kg(
    interstage_mass_kg: float, nu_push_kg: float, nu_envelope_kg: float, exponent: float
) -> float:
    """The interstage's increment (design 4.2.4; source note section 5.5; charged to stage 1,
    D-SP7-36): m_is ((N_push/N_env)^n - 1)+ with N = n U g0, the upper stack's load (FS_u
    and g0 cancel in the ratio).

    Inputs: interstage_mass_kg m_is [kg] (the relation's mass); nu_push_kg, the push's peak
    n U and nu_envelope_kg, the envelope's (with margin and cap) [kg in g0 units], > 0;
    exponent n [-] in (0, 1] (0.6, the central Gerard row's, fixed).
    Output [kg]: 0 inside the envelope (no factor: the relation is fitted to as-built
    masses). At n_peak 7.0 against MECO's 5.195 g0, 934 x (1.347^0.6 - 1) = 183 kg.
    Frame: the stack axis.
    """
    m_is = _require_non_negative("interstage_mass_kg", interstage_mass_kg)
    push = _require_non_negative("nu_push_kg", nu_push_kg)
    env = _require_positive("nu_envelope_kg", nu_envelope_kg)
    n = _require_unit_fraction("exponent", exponent)
    return m_is * max(0.0, (push / env) ** n - 1.0)


def thrust_structure_increment_kg(k_ts_kg_per_n: float, load_N: float, envelope_N: float) -> float:
    """The thrust-structure row's increment (design 4.2.3; D-SP7-37): k_ts T_max max(0,
    F/T_max - 1) = k_ts max(0, F - T_env).

    Inputs: k_ts_kg_per_n [kg/N], >= 0 (0.197-0.628 kg/kN, central 0.2805); load_N, the
    push's load through the thrust structure [N] (the peak interface force plus the thrust
    at the same instant: both enter there; the peak interface force for a cold push);
    envelope_N, the envelope's (1 + margin) T_max [N], > 0.
    Output [kg] (no factor: a mass-estimating relation fitted to as-built masses).
    Frame: the stack axis.
    """
    k_ts = _require_non_negative("k_ts_kg_per_n", k_ts_kg_per_n)
    load = _require_finite("load_N", load_N)
    env = _require_positive("envelope_N", envelope_N)
    return k_ts * max(0.0, load - env)


# ======================================================================== S2: the increment


@dataclass(frozen=True, eq=False)
class ElementIncrement:
    """One element's increment (``size_increment``).

    stage, element; kg, the increment [kg] (factors applied); closed_form: False for the
    ring frame only (new hardware sized in closed form, no envelope credit); nof, the factor
    at the governing station (an element without stations: its factor; None when kg is 0);
    the governing point: station_index (None for an element without stations), z_m [m,
    stack frame] at the largest increment, push_mode and envelope_mode there and
    envelope_case (the PadLoadSet index; -1 for the minimum gauge, None when kg is 0); the
    profile (barrels, the skirt, the domes and the tube): z_stations_m, t_env_m and
    t_push_m [m] with push_modes and envelope_modes per station (None for the ring and the
    relation rows).
    """

    stage: str
    element: str
    kg: float
    closed_form: bool
    nof: float | None
    station_index: int | None
    z_m: float | None
    push_mode: str | None
    envelope_mode: str | None
    envelope_case: int | None
    z_stations_m: np.ndarray | None = None
    t_env_m: np.ndarray | None = None
    t_push_m: np.ndarray | None = None
    push_modes: tuple[str, ...] | None = None
    envelope_modes: tuple[str, ...] | None = None


@dataclass(frozen=True)
class StructureFlag:
    """A reported check (design 4.2.2; not sized): name, fired, and its numbers as
    (key, value) pairs in SI or g0 (each key carries its unit)."""

    name: str
    fired: bool
    values: tuple[tuple[str, float], ...]

    def value(self, key: str) -> float:
        """The number recorded under ``key`` (KeyError if absent)."""
        for name, number in self.values:
            if name == key:
                return number
        raise KeyError(key)


@dataclass(frozen=True, eq=False)
class Increment:
    """The structural increment of one push (``size_increment``; design 4.2).

    dm_stage1_kg (the stage-1 elements, the interstage included, D-SP7-36) and
    dm_stage2_kg [kg]; closed_form_kg (every element but the ring) and ring_kg [kg];
    elements, one ElementIncrement per element of both stages (stage 2's zero when not
    sized); governing, the element with the largest increment (None when dm is 0);
    flags: FLAG_RELEASE_UNLOAD, FLAG_UPPER_STACK, FLAG_PAYLOAD_LIMIT; requirement, the
    PushRequirement; entry, dynamic, margin, envelope_cap_g; stage2_sized: whether the push
    exceeded the upper stack's envelope (then stage 2's tanks and the interstage are
    charged, design 4.2.2); ring: the RingSizing (None for the thrust-structure entry).
    """

    dm_stage1_kg: float
    dm_stage2_kg: float
    closed_form_kg: float
    ring_kg: float
    elements: tuple[ElementIncrement, ...]
    governing: ElementIncrement | None
    flags: tuple[StructureFlag, ...]
    requirement: PushRequirement
    entry: str
    dynamic: str
    margin: float
    envelope_cap_g: float | None
    stage2_sized: bool
    ring: RingSizing | None

    @property
    def total_kg(self) -> float:
        """dm_stage1_kg + dm_stage2_kg [kg]."""
        return self.dm_stage1_kg + self.dm_stage2_kg

    def element(self, stage: str, name: str) -> ElementIncrement:
        """The ElementIncrement of a stage role's element (KeyError if absent)."""
        for item in self.elements:
            if item.stage == stage and item.element == name:
                return item
        raise KeyError((stage, name))

    def flag(self, name: str) -> StructureFlag:
        """The flag called ``name`` (KeyError if absent)."""
        for item in self.flags:
            if item.name == name:
                return item
        raise KeyError(name)


def _push_features(req: PushRequirement, stage: str) -> dict[str, np.ndarray]:
    """``_features`` of the push's peak cases for a stage role (n = n_peak, uncapped)."""
    cases = req.cases
    return _features(
        np.array([c.n_g for c in cases], dtype=float),
        np.array([c.stage_lox_kg(stage) for c in cases], dtype=float),
        np.array([c.stage_rp1_kg(stage) for c in cases], dtype=float),
        np.array([c.upper_mass_kg(stage) for c in cases], dtype=float),
    )


def _barrel_push(
    stage: str,
    sg: StageGeometry,
    barrel: BarrelStations,
    feats: dict[str, np.ndarray],
    coeffs: StructureCoefficients,
    env: ElementEnvelope,
) -> tuple[np.ndarray, list[str], np.ndarray]:
    """The push's thickness at each station of a barrel [m], its mode, and the gap [m]
    between the compression mode's and the skin modes' (hoop, combined) largest push
    thickness (the factor switch's locator, ``_nof_cells``): the largest over the push's
    cases of the largest of hoop, compression, combined and the minimum gauge, with the
    same arithmetic as the envelope (no margin)."""
    tank = barrel.tank
    r, area = sg.radius_m, sg.area_m2
    fs, f_tu, eta = coeffs.fs_ult, coeffs.f_tu_pa, coeffs.eta_weld
    p_meop, p_min = coeffs.p_meop_pa(stage, tank), coeffs.p_min_pa(stage, tank)
    k = barrel.mass_height_kg[:, None]
    s = barrel.structure_above_kg[:, None]
    am = feats[f"am_{tank}"][None, :]
    aq = feats[f"aq_{tank}"][None, :]
    n = feats["n"][None, :]
    p = _station_pressure(_head_driver(am, k, n), 1.0, p_meop, area)
    n_d = _station_design_load(aq + s * n, 1.0, fs, p_min, area)
    mode_c = _compression_mode(tank, coeffs)
    anchor = env.design_compression_N
    comp = _compression_array(mode_c, n_d, r, coeffs, p_min, anchor)
    stack = np.stack(
        [
            _hoop_array(p, r, fs, f_tu, eta, 0.0),
            comp,
            _von_mises_array(p, n_d, r, fs, f_tu, eta),
            np.full(n_d.shape, coeffs.t_min_m),
        ]
    )
    names = (MODE_HOOP, mode_c, MODE_COMBINED, MODE_MIN_GAUGE)
    per_case = np.max(stack, axis=0)  # (stations, cases)
    pick_case = np.argmax(per_case, axis=1)
    rows = np.arange(per_case.shape[0])
    t = per_case[rows, pick_case]
    mode_index = np.argmax(stack[:, rows, pick_case], axis=0)
    gap = np.max(stack[1], axis=1) - np.max(np.maximum(stack[0], stack[2]), axis=1)
    return t, [names[i] for i in mode_index], gap


def _nof_cells(
    stiff: np.ndarray,
    gap: np.ndarray | None,
    modes: Sequence[str],
    z: np.ndarray,
    dz: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Each station's cell length [m] under the stiffened factor and under the skin factor.

    The factor is chosen per station by the governing push mode (source note section 4), so
    it jumps where the governing mode switches between a stiffened row and a skin mode; the
    midpoint rule would give that jump an O(dz) error. Where two neighbouring stations
    differ (neither at the minimum gauge) and ``gap`` (compression minus skin thickness)
    changes sign between them, the switch is placed at gap's linear root and the cell it
    falls in is split there, leaving an O(dz^2) error (the stations-doubling test)."""
    dz_stiff = np.where(stiff, dz, 0.0)
    dz_skin = np.where(stiff, 0.0, dz)
    if gap is None:
        return dz_stiff, dz_skin
    for i in np.nonzero(stiff[:-1] != stiff[1:])[0]:
        j = int(i) + 1
        if MODE_MIN_GAUGE in (modes[i], modes[j]) or not gap[i] * gap[j] < 0.0:
            continue
        z_star = z[i] + (gap[i] / (gap[i] - gap[j])) * (z[j] - z[i])
        boundary = z[i] + 0.5 * dz[i]
        cell, moved = (i, boundary - z_star) if z_star < boundary else (j, z_star - boundary)
        moved = min(moved, dz[cell])
        if stiff[cell]:
            dz_stiff[cell] -= moved
            dz_skin[cell] += moved
        else:
            dz_skin[cell] -= moved
            dz_stiff[cell] += moved
    return dz_stiff, dz_skin


def _barrel_increment(
    stage: str,
    sg: StageGeometry,
    barrel: BarrelStations,
    env: ElementEnvelope,
    t_push: np.ndarray,
    push_modes: Sequence[str],
    coeffs: StructureCoefficients,
    *,
    element: str,
    factor_scale: float = 1.0,
    gap: np.ndarray | None = None,
) -> ElementIncrement:
    """A barrel's (or the skirt's) increment by S1's ``barrel_increment_kg``: each station's
    positive part over the envelope, times nof_stiffened where the push is sized by a Gerard
    row or the plate-limited row (the RP-1 barrel and the skirt) and nof_barrel elsewhere
    (every LOX station; a hoop- or combined-sized RP-1 station), times factor_scale
    (nof_entry_ratio on the skirt); with ``gap``, a cell next to a switch of factor is split
    at the switch (``_nof_cells``)."""
    stiff = np.array([m in STIFFENED_MODES for m in push_modes], dtype=bool)
    r, rho = sg.radius_m, coeffs.rho_wall_kgm3
    kg = 0.0
    weights = np.zeros_like(t_push)
    cells = _nof_cells(stiff, gap, push_modes, barrel.z_m, barrel.dz_m)
    for mask, dz, nof in (
        (stiff, cells[0], coeffs.nof_stiffened),
        (~stiff, cells[1], coeffs.nof_barrel),
    ):
        scaled = nof * factor_scale
        if np.any(dz > 0.0):
            kg += barrel_increment_kg(t_push, env.t_m, dz, r, rho, scaled)
        weights = np.where(mask, scaled, weights)
    per_station = (
        weights * 2.0 * math.pi * r * rho * barrel.dz_m * np.maximum(t_push - env.t_m, 0.0)
    )
    if kg > 0.0:
        i = int(np.argmax(per_station))
        station: int | None = i
        z: float | None = float(barrel.z_m[i])
        p_mode: str | None = push_modes[i]
        e_mode: str | None = env.modes[i]
        e_case: int | None = int(env.case_index[i])
        nof_i: float | None = float(weights[i])
    else:
        station = z = p_mode = e_mode = e_case = nof_i = None
    return ElementIncrement(
        stage=stage,
        element=element,
        kg=kg,
        closed_form=True,
        nof=nof_i,
        station_index=station,
        z_m=z,
        push_mode=p_mode,
        envelope_mode=e_mode,
        envelope_case=e_case,
        z_stations_m=barrel.z_m,
        t_env_m=env.t_m,
        t_push_m=t_push,
        push_modes=tuple(push_modes),
        envelope_modes=env.modes,
    )


def _area_increment(
    stage: str,
    sg: StageGeometry,
    env: ElementEnvelope,
    feats: dict[str, np.ndarray],
    coeffs: StructureCoefficients,
    element: str,
) -> ElementIncrement:
    """A dome's or the tube's increment by S1's ``area_increment_kg`` (domes: their alloy's
    density and nof_dome; the tube: the 2195 block's density and nof_barrel)."""
    if element == FORWARD_DOME:
        t_push = _area_thickness(stage, sg, coeffs, element, 0.0, 1.0)
    else:
        tank = _AREA_TANK[element]
        drivers = feats[f"am_{tank}"] + _dome_driver_offset(sg, coeffs, element) * feats["n"]
        t_push = max(_area_thickness(stage, sg, coeffs, element, float(d), 1.0) for d in drivers)
    if element == TRANSFER_TUBE:
        area, rho, nof, mode = sg.tube_area_m2, coeffs.rho_wall_kgm3, coeffs.nof_barrel, MODE_HOOP
    else:
        area, rho, nof, mode = sg.dome_area_m2, coeffs.dome_rho_kgm3, coeffs.nof_dome, MODE_MEMBRANE
    t_env = float(env.t_m[0])
    kg = area_increment_kg(t_push, t_env, area, rho, nof)
    if t_push == coeffs.t_min_m:
        mode = MODE_MIN_GAUGE
    positive = kg > 0.0
    return ElementIncrement(
        stage=stage,
        element=element,
        kg=kg,
        closed_form=True,
        nof=nof if positive else None,
        station_index=None,
        z_m=float(env.z_m[0]) if positive else None,
        push_mode=mode if positive else None,
        envelope_mode=env.modes[0] if positive else None,
        envelope_case=int(env.case_index[0]) if positive else None,
        z_stations_m=env.z_m,
        t_env_m=env.t_m,
        t_push_m=np.array([t_push]),
        push_modes=(mode,),
        envelope_modes=env.modes,
    )


def _zero_increment(stage: str, element: str, closed_form: bool = True) -> ElementIncrement:
    """An element the push does not load (kg 0)."""
    return ElementIncrement(
        stage=stage,
        element=element,
        kg=0.0,
        closed_form=closed_form,
        nof=None,
        station_index=None,
        z_m=None,
        push_mode=None,
        envelope_mode=None,
        envelope_case=None,
    )


def _stage_tank_increments(
    stage: str,
    sg: StageGeometry,
    envelope: Envelope,
    req: PushRequirement,
    coeffs: StructureCoefficients,
) -> list[ElementIncrement]:
    """The barrels, domes and tube of one stage."""
    feats = _push_features(req, stage)
    out = []
    for element in (RP1_AFT_DOME, RP1_BARREL, COMMON_DOME, LOX_BARREL, FORWARD_DOME, TRANSFER_TUBE):
        env = envelope.element(stage, element)
        if element in (RP1_BARREL, LOX_BARREL):
            barrel = sg.barrel(RP1 if element == RP1_BARREL else LOX)
            t_push, modes, gap = _barrel_push(stage, sg, barrel, feats, coeffs, env)
            out.append(
                _barrel_increment(
                    stage, sg, barrel, env, t_push, modes, coeffs, element=element, gap=gap
                )
            )
        else:
            out.append(_area_increment(stage, sg, env, feats, coeffs, element))
    return out


def _release_flag(
    geometry: StackGeometry,
    coeffs: StructureCoefficients,
    envelope: Envelope,
    req: PushRequirement,
) -> StructureFlag:
    """FLAG_RELEASE_UNLOAD (design 4.2.2; D-SP7-39): the push's instant release against the
    pad's MECO shutdown under the same single-mode treatment.

    Inputs: geometry, coeffs and envelope (the pad's MECO case); req, the push at its peak.
    Output: the StructureFlag. The push: the largest instantaneous load at the release,
    n_peak,rel (the ramp's undamped residual included), drops to n_after and swings to
    n_swing = 2 n_after - n_peak,rel (the swing from the plateau, 2 n_after - n_before,
    printed beside); MECO: n_MECO to 0 (a slowly built thrust load, no residual) swings to
    -n_MECO. Per tank of both stages at the swing, with the model's head convention (to
    the bottom dome's crown, m/(rho A) + b, b the dome depth, each stage's own A and b):
    the bottom's minimum gauge pressure p_min + g0 n_swing (m + rho A b)/A [Pa, from the
    ambient] for the push and for MECO, and the push's absolute value p_amb + that (p_amb
    the sea-level ambient of the release at the silo's top; negative: the column would
    separate from its dome; MECO's ambient is MECO_AMBIENT_PA, so its gauge value is also
    its absolute one). The stage-1 tanks are nearly empty at MECO (on the depletion row,
    m = 0, MECO's value is only p_min less the dome's own head), the stage-2 tanks full;
    the stage-2 values (keys ``stage2_*``) are recorded beside so that the comparison is
    not read as push-specific (the same treatment separates the stage-2 LOX column on the
    pad's own MECO at the gate's central coefficients), and only the stage-1 columns fire
    the flag (D-SP7-19). The common dome's reverse pressure
    p_meop,RP1 - max(p_min,LOX + g0 n_swing (m_LOX + rho_LOX A b)/A, -p_amb) [Pa, a
    difference; positive: pushed from its RP-1 side], the LOX side floored at zero
    absolute (a separated column; the vapour pressure neglected, so an upper bound), at
    MECO with MECO_AMBIENT_PA; at zero swing it is already p_meop,RP1 - p_min,LOX, so it
    is judged against MECO's; the upper stack's swing n_swing U g0 [N] against MECO's.
    Fired when either stage-1 column separates at the push, the push's reverse pressure
    is positive and above MECO's, or the upper stack swings further than at MECO.
    Frame: the stack axis, compression positive.
    """
    meco = envelope.pad.cases[envelope.pad.meco_case]
    swing_meco = peak_load(0.0, meco.n_g, DLF_STEP)
    rel = req.release_case
    swing = req.release_swing_g
    values: list[tuple[str, float]] = [
        ("release_n_before_g", req.release_n_before_g),
        ("release_n_peak_g", req.release_n_peak_g),
        ("release_n_after_g", req.release_n_after_g),
        ("release_swing_g", swing),
        ("release_swing_plateau_g", req.release_swing_plateau_g),
        ("release_p_amb_pa", P_SEA_LEVEL_PA),
        ("meco_n_g", meco.n_g),
        ("meco_swing_g", swing_meco),
    ]

    def head_pa(sg: StageGeometry, n_g: float, m_kg: float, rho_kgm3: float) -> float:
        """g0 n (m + rho A b)/A [Pa]: the head to a stage's bottom dome's crown at n [g0]."""
        area = sg.area_m2
        return float(from_g(n_g * (m_kg + rho_kgm3 * area * sg.dome_depth_m))) / area

    separates = False
    for stage, prefix in ((STAGE1, ""), (STAGE2, "stage2_")):
        sg = geometry.stage(stage)
        for tank, rho in ((LOX, coeffs.rho_lox_kgm3), (RP1, coeffs.rho_rp1_kgm3)):
            m_rel = rel.stage_lox_kg(stage) if tank == LOX else rel.stage_rp1_kg(stage)
            m_meco = meco.stage_lox_kg(stage) if tank == LOX else meco.stage_rp1_kg(stage)
            p_min = coeffs.p_min_pa(stage, tank)
            push_gauge = p_min + head_pa(sg, swing, m_rel, rho)
            push_abs = P_SEA_LEVEL_PA + push_gauge
            meco_gauge = p_min + head_pa(sg, swing_meco, m_meco, rho)
            values += [
                (f"{prefix}{tank}_bottom_pressure_min_gauge_pa", push_gauge),
                (f"{prefix}{tank}_bottom_pressure_min_abs_pa", push_abs),
                (f"meco_{prefix}{tank}_bottom_pressure_min_gauge_pa", meco_gauge),
            ]
            if stage == STAGE1:
                separates = separates or push_abs < 0.0
    sg1 = geometry.stage1
    p_meop_rp1 = coeffs.p_meop_pa(STAGE1, RP1)
    p_min_lox = coeffs.p_min_pa(STAGE1, LOX)
    rho_lox = coeffs.rho_lox_kgm3
    lox_side = p_min_lox + head_pa(sg1, swing, rel.lox_stage1_kg, rho_lox)
    lox_side_meco = p_min_lox + head_pa(sg1, swing_meco, meco.lox_stage1_kg, rho_lox)
    reverse = p_meop_rp1 - max(lox_side, -P_SEA_LEVEL_PA)
    reverse_meco = p_meop_rp1 - max(lox_side_meco, -MECO_AMBIENT_PA)
    upper = swing * rel.upper_mass_stage1_kg
    upper_meco = swing_meco * meco.upper_mass_stage1_kg
    values += [
        ("common_dome_reverse_pressure_pa", reverse),
        ("meco_common_dome_reverse_pressure_pa", reverse_meco),
        ("upper_stack_swing_N", float(from_g(upper))),
        ("meco_upper_stack_swing_N", float(from_g(upper_meco))),
    ]
    reverses = reverse > max(0.0, reverse_meco)
    fired = separates or reverses or abs(upper) > abs(upper_meco)
    return StructureFlag(name=FLAG_RELEASE_UNLOAD, fired=fired, values=tuple(values))


def size_increment(
    geometry: StackGeometry,
    coeffs: StructureCoefficients,
    envelope: Envelope,
    push: PushLoad,
    *,
    dynamic: DynamicMode = "rise_time",
    entry: EntryPath = ENTRY_AFT_RING,
) -> Increment:
    """The structural increment of one push over the pad's envelope (design 4.2 to 4.2.4).

    Inputs: geometry, coeffs and envelope (built on the same geometry and coefficients);
    push, the quasi-static PushLoad; dynamic, one of DYNAMIC_MODES; entry, one of
    ENTRY_PATHS.
    Output: an Increment. The push is taken at its peak (``push_requirement``). Each barrel
    station's increment is the positive part of t_push - t_env times 2 pi r rho_w dz and
    its factor (``_barrel_increment``); domes and the tube area x rho x the positive part
    x their factor; zero inside the envelope, exactly. aft_ring: the skirt carries the peak
    interface force (nof_stiffened x nof_entry_ratio) and the ring frame
    (``ring_frame_section``, no envelope credit; nof_barrel x nof_entry_ratio);
    thrust_structure: k_ts max(0, F - (1 + margin) T_max) with F the peak interface force
    plus the thrust, the skirt and ring then unloaded. Stage 2's tanks and the interstage
    (charged to stage 1, D-SP7-36) only when the push's peak n U exceeds the envelope's
    (FLAG_UPPER_STACK); the stage-2 envelope must then be built.
    Frame: the stack frame of the geometry.
    """
    if entry not in ENTRY_PATHS:
        raise ValueError(f"entry must be one of {ENTRY_PATHS}, got {entry!r}")
    req = push_requirement(push, coeffs, dynamic)
    sg1 = geometry.stage1
    elements: list[ElementIncrement] = []
    ring: RingSizing | None = None
    f_peak = req.f_peak_N
    if entry == ENTRY_AFT_RING:
        env_skirt = envelope.element(STAGE1, AFT_SKIRT)
        skirt = _require_skirt(sg1)
        if env_skirt.design_compression_N is None:
            raise ValueError("the skirt's envelope carries no design compression")
        n_design = float(_skirt_design_load(f_peak, 1.0, coeffs.fs_ult))
        anchor = float(env_skirt.design_compression_N[0])
        t_push, mode = _skirt_thickness(sg1, coeffs, np.asarray(n_design), anchor)
        modes = [mode] * t_push.shape[0]
        elements.append(
            _barrel_increment(
                STAGE1,
                sg1,
                skirt,
                env_skirt,
                t_push,
                modes,
                coeffs,
                element=AFT_SKIRT,
                factor_scale=coeffs.nof_entry_ratio,
            )
        )
        ring = ring_frame_section(
            f_peak,
            sg1.radius_m,
            coeffs.ring_pads,
            coeffs.ring_h_over_b,
            coeffs.fs_ult,
            coeffs.f_tu_pa,
            coeffs.fitting_factor,
            coeffs.rho_wall_kgm3,
        )
        ring_nof = coeffs.nof_barrel * coeffs.nof_entry_ratio
        ring_kg = ring_nof * ring.mass_kg
        elements.append(
            ElementIncrement(
                stage=STAGE1,
                element=LOAD_RING,
                kg=ring_kg,
                closed_form=False,
                nof=ring_nof if ring_kg > 0.0 else None,
                station_index=None,
                z_m=0.0 if ring_kg > 0.0 else None,
                push_mode=ring.governing if ring_kg > 0.0 else None,
                envelope_mode=None,
                envelope_case=None,
            )
        )
        elements.append(_zero_increment(STAGE1, THRUST_STRUCTURE))
    else:
        elements.append(_zero_increment(STAGE1, AFT_SKIRT))
        elements.append(_zero_increment(STAGE1, LOAD_RING, closed_form=False))
        load = max(float(c.interface_force_N or 0.0) + c.thrust_N for c in req.cases)
        ts_kg = thrust_structure_increment_kg(
            coeffs.k_ts_kg_per_n, load, envelope.thrust_structure_N
        )
        elements.append(
            ElementIncrement(
                stage=STAGE1,
                element=THRUST_STRUCTURE,
                kg=ts_kg,
                closed_form=True,
                nof=None,
                station_index=None,
                z_m=0.0 if ts_kg > 0.0 else None,
                push_mode=MODE_RELATION if ts_kg > 0.0 else None,
                envelope_mode=None,
                envelope_case=None,
            )
        )
    elements += _stage_tank_increments(STAGE1, sg1, envelope, req, coeffs)
    feats1 = _push_features(req, STAGE1)
    nu_push = float(np.max(feats1["n_upper"]))
    exceeded = nu_push > envelope.upper_stack_nu_kg
    is_kg = interstage_increment_kg(
        geometry.interstage_mass_kg, nu_push, envelope.upper_stack_nu_kg, coeffs.interstage_exponent
    )
    elements.append(
        ElementIncrement(
            stage=STAGE1,
            element=INTERSTAGE,
            kg=is_kg,
            closed_form=True,
            nof=None,
            station_index=None,
            z_m=geometry.stage1.top_z_m if is_kg > 0.0 else None,
            push_mode=MODE_RELATION if is_kg > 0.0 else None,
            envelope_mode=None,
            envelope_case=envelope.upper_stack_case if is_kg > 0.0 else None,
        )
    )
    if exceeded:
        if envelope.stage2 is None:
            raise ValueError(
                "the push exceeds the upper stack's envelope, so stage 2 is sized: build the "
                "envelope with stage 2"
            )
        elements += _stage_tank_increments(STAGE2, geometry.stage2, envelope, req, coeffs)
    else:
        elements += [_zero_increment(STAGE2, name) for name in STAGE2_ELEMENTS]
    dm1 = sum(e.kg for e in elements if e.stage == STAGE1)
    dm2 = sum(e.kg for e in elements if e.stage == STAGE2)
    ring_kg = sum(e.kg for e in elements if e.element == LOAD_RING)
    positive = [e for e in elements if e.kg > 0.0]
    governing = max(positive, key=lambda e: e.kg) if positive else None
    upper_flag = StructureFlag(
        name=FLAG_UPPER_STACK,
        fired=exceeded,
        values=(
            ("push_n_upper_N", float(from_g(nu_push))),
            ("envelope_n_upper_N", float(from_g(envelope.upper_stack_nu_kg))),
            ("pad_n_upper_N", float(from_g(envelope.upper_stack_nu_pad_kg))),
        ),
    )
    n_peak = req.n_peak_g
    payload_flag = StructureFlag(
        name=FLAG_PAYLOAD_LIMIT,
        fired=(n_peak > coeffs.payload_limit_axial_max_g)
        or (req.release_swing_g < coeffs.payload_limit_axial_min_g),
        values=(
            ("n_peak_g", n_peak),
            ("release_swing_g", req.release_swing_g),
            ("release_swing_plateau_g", req.release_swing_plateau_g),
            ("limit_axial_max_g", coeffs.payload_limit_axial_max_g),
            ("limit_axial_min_g", coeffs.payload_limit_axial_min_g),
        ),
    )
    flags = (_release_flag(geometry, coeffs, envelope, req), upper_flag, payload_flag)
    return Increment(
        dm_stage1_kg=dm1,
        dm_stage2_kg=dm2,
        closed_form_kg=dm1 + dm2 - ring_kg,
        ring_kg=ring_kg,
        elements=tuple(elements),
        governing=governing,
        flags=flags,
        requirement=req,
        entry=entry,
        dynamic=dynamic,
        margin=envelope.margin,
        envelope_cap_g=envelope.envelope_cap_g,
        stage2_sized=exceeded,
        ring=ring,
    )


def upper_stack_exceeded(
    pad: PadLoadSet,
    push: PushLoad,
    coeffs: StructureCoefficients,
    *,
    dynamic: DynamicMode = "rise_time",
    margin: float = 0.0,
    envelope_cap_g: float | None = None,
) -> bool:
    """Whether the push's peak n U exceeds the envelope's, the condition under which stage 2
    is sized (FLAG_UPPER_STACK), without building an envelope: ``size`` uses it to build
    stage 2's envelope only when needed.

    Inputs: pad, the PadLoadSet; push, the quasi-static PushLoad; coeffs; dynamic, margin
    and envelope_cap_g [g0] as ``size``.
    Output: True when the largest n_peak U over the push's peak cases [g0 kg] (U the mass
    above stage 1 [kg], n_peak [g0] from ``push_requirement``) exceeds (1 + margin) times
    the largest pad n U with the pad's stage-1 felt n capped at envelope_cap_g [g0 kg]
    (the same comparison ``size_increment`` makes on the built envelope).
    Frame: the stack axis.
    """
    req = push_requirement(push, coeffs, dynamic)
    nu_push = float(np.max(_push_features(req, STAGE1)["n_upper"]))
    lam = _margin_factor(margin)
    nu_env = lam * float(np.max(pad.features(STAGE1, _check_cap(envelope_cap_g)).arrays["n_upper"]))
    return nu_push > nu_env


def size(
    masses: StackMasses,
    layout: StackLayout,
    coeffs: StructureCoefficients,
    pad: PadLoadSet,
    push: PushLoad,
    *,
    dynamic: DynamicMode = "rise_time",
    entry: EntryPath = ENTRY_AFT_RING,
    margin: float = 0.0,
    envelope_cap_g: float | None = None,
) -> Increment:
    """One full sizing with a fresh geometry and envelope, the screened search's one call
    (design 4.2.6): ``build_geometry``, ``build_envelope`` (stage 2 only when the push
    exceeds the upper stack's envelope) and ``size_increment``.

    Inputs: masses, the full-load vehicle's StackMasses; layout; coeffs; pad, the
    PadLoadSet (prepared once: its drivers do not depend on the coefficients); push;
    dynamic, entry, margin, envelope_cap_g as ``size_increment`` and ``build_envelope``.
    Output: the Increment. Frame: the stack frame.
    """
    geometry = build_geometry(masses, layout, coeffs)
    stages = (
        STAGE_ROLES
        if upper_stack_exceeded(
            pad, push, coeffs, dynamic=dynamic, margin=margin, envelope_cap_g=envelope_cap_g
        )
        else (STAGE1,)
    )
    envelope = build_envelope(
        geometry, coeffs, pad, margin=margin, envelope_cap_g=envelope_cap_g, stages=stages
    )
    return size_increment(geometry, coeffs, envelope, push, dynamic=dynamic, entry=entry)


# ======================================================================== S2: plausibility


@dataclass(frozen=True)
class Plausibility:
    """The plausibility check of design 4.2.5 (D-SP7-33, source note section 7; calibration,
    not validation).

    element_kg: the stage-1 tank elements' envelope masses with their factors by the
    envelope's governing mode (hoop, combined, monocoque or the minimum gauge: nof_barrel; a
    stiffened row: nof_stiffened; domes nof_dome), barrels on the physical lengths [kg];
    m_model_kg, their sum, and m_model_cylinder_kg on the cylinder-equivalent lengths [kg];
    lox_length_ratio and rp1_length_ratio L_phys/L_model [-]; relation_kg R = c V^e on the
    combined LOX + RP-1 volume and relation_per_tank_kg (printed beside) [kg]; lower_kg and
    upper_kg, (1 -/+ band) R; adverse_end_factor (0.7 R/M when M < 0.7 R, else 1) and
    favourable_end_factor (1.3 R/M when M > 1.3 R, else 1); akin_kg (printed); the
    interstage relation's mass, the thrust-structure relation k_ts T_max and stage 1's dry
    mass less its engines [kg] (printed beside).
    """

    element_kg: tuple[tuple[str, float], ...]
    m_model_kg: float
    m_model_cylinder_kg: float
    lox_length_ratio: float
    rp1_length_ratio: float
    relation_kg: float
    relation_per_tank_kg: float
    lower_kg: float
    upper_kg: float
    adverse_end_factor: float
    favourable_end_factor: float
    akin_kg: float
    interstage_relation_kg: float
    thrust_structure_relation_kg: float
    stage1_dry_less_engines_kg: float


def plausibility(
    geometry: StackGeometry, coeffs: StructureCoefficients, envelope: Envelope
) -> Plausibility:
    """The model's stage-1 envelope tank mass against Heineman's relation (design 4.2.5,
    D-SP7-33 with the source note's section 7 refinements).

    Inputs: geometry, coeffs and envelope at the central coefficients (the rule's basis).
    Output: a Plausibility (``widen_band`` applies it to the physics band's ends).
    Frame: none.
    """
    sg = geometry.stage1
    r = sg.radius_m
    items: list[tuple[str, float]] = []
    cylinder = 0.0
    model = 0.0
    ratios = {
        LOX_BARREL: sg.lox_length_physical_m / sg.lox_barrel.length_m,
        RP1_BARREL: sg.rp1_length_physical_m / sg.rp1_barrel.length_m,
    }
    for element in TANK_ELEMENTS:
        env = envelope.element(STAGE1, element)
        if element in (LOX_BARREL, RP1_BARREL):
            barrel = sg.barrel(LOX if element == LOX_BARREL else RP1)
            nof = np.array(
                [
                    coeffs.nof_stiffened if m in STIFFENED_MODES else coeffs.nof_barrel
                    for m in env.modes
                ]
            )
            mass = float(
                np.sum(nof * 2.0 * math.pi * r * coeffs.rho_wall_kgm3 * barrel.dz_m * env.t_m)
            )
            cylinder += mass
            mass *= ratios[element]
        else:
            mass = coeffs.nof_dome * sg.dome_area_m2 * coeffs.dome_rho_kgm3 * float(env.t_m[0])
            cylinder += mass
        model += mass
        items.append((element, mass))
    volume = sg.lox_volume_m3 + sg.rp1_volume_m3
    c, e, band = (
        coeffs.heineman_kg_per_m2p25,
        coeffs.heineman_exponent,
        coeffs.heineman_band_fraction,
    )
    relation = c * volume**e
    per_tank = c * sg.lox_volume_m3**e + c * sg.rp1_volume_m3**e
    lower, upper = (1.0 - band) * relation, (1.0 + band) * relation
    adverse, favourable = plausibility_factors(model, relation, band)
    return Plausibility(
        element_kg=tuple(items),
        m_model_kg=model,
        m_model_cylinder_kg=cylinder,
        lox_length_ratio=ratios[LOX_BARREL],
        rp1_length_ratio=ratios[RP1_BARREL],
        relation_kg=relation,
        relation_per_tank_kg=per_tank,
        lower_kg=lower,
        upper_kg=upper,
        adverse_end_factor=adverse,
        favourable_end_factor=favourable,
        akin_kg=coeffs.akin_lox_tank_fraction * sg.lox_full_kg
        + coeffs.akin_rp1_tank_fraction * sg.rp1_full_kg,
        interstage_relation_kg=geometry.interstage_mass_kg,
        thrust_structure_relation_kg=coeffs.k_ts_kg_per_n * sg.thrust_vac_N,
        stage1_dry_less_engines_kg=sg.dry_mass_kg - sg.breakdown.engines_kg,
    )


def plausibility_factors(m_model_kg: float, relation_kg: float, band: float) -> tuple[float, float]:
    """The plausibility rule's two factors (D-SP7-33, applied mechanically): with the band
    [(1 - band) R, (1 + band) R] of the relation R [kg] and the model's tank mass M [kg],
    (adverse, favourable) = ((1 - band) R / M if M < (1 - band) R else 1, (1 + band) R / M
    if M > (1 + band) R else 1). Inputs > 0, band in [0, 1). Frame: none."""
    model = _require_positive("m_model_kg", m_model_kg)
    relation = _require_positive("relation_kg", relation_kg)
    b = _require_fraction("band", band)
    lower, upper = (1.0 - b) * relation, (1.0 + b) * relation
    return (lower / model if model < lower else 1.0, upper / model if model > upper else 1.0)


def widen_band(dm_low_kg: float, dm_high_kg: float, check: Plausibility) -> tuple[float, float]:
    """The physics band's ends after the plausibility rule (D-SP7-33, applied mechanically):
    the adverse (high-mass) end times adverse_end_factor (> 1 when the model's tank mass is
    below 0.7 R), the favourable (low-mass) end times favourable_end_factor (< 1 above
    1.3 R). Inputs [kg]; output (low, high) [kg]. Frame: none."""
    low = _require_finite("dm_low_kg", dm_low_kg)
    high = _require_finite("dm_high_kg", dm_high_kg)
    return low * check.favourable_end_factor, high * check.adverse_end_factor


# ======================================================================== S2: the screened search


type CoefficientValue = float | int | str
"""A coefficient's value as the structure file writes it, in the units its path names (a
pad count is an int, a discrete choice an int or a str)."""

KIND_CONTINUOUS = "continuous"
"""A coefficient ranged by {central, low, high}."""
KIND_INTEGER = "integer"
"""A whole-number coefficient (the pad count)."""
KIND_DISCRETE = "discrete"
"""A discrete choice {central, alternatives}."""
COEFFICIENT_KINDS: tuple[str, ...] = (KIND_CONTINUOUS, KIND_INTEGER, KIND_DISCRETE)
"""The kinds of a CoefficientRange."""
GROUP_PHYSICS = "physics"
"""The sourced or physical coefficients (design 4.2.6, layer 1)."""
GROUP_DESIGN = "design"
"""The design-assumption axes (design 4.2.6, layer 2)."""
COEFFICIENT_GROUPS: tuple[str, ...] = (GROUP_PHYSICS, GROUP_DESIGN)
"""The groups of a CoefficientRange."""


@dataclass(frozen=True)
class CoefficientRange:
    """One coefficient of the screened search (``config.StructureConfig.coefficient_ranges``
    builds them from the structure file; design 4.2.6, source note section 9.1).

    path: the structure file's dotted path (the search's name for it); kind, one of
    COEFFICIENT_KINDS; group, GROUP_PHYSICS or GROUP_DESIGN; central, low and high in the
    file's units (low and high None for a discrete one); choices, a discrete one's, central
    first (() otherwise); stage2_only: one of the stage-2-only five (the stage-2 pressures
    and the interstage length), which act only when the upper stack is sized.
    """

    path: str
    kind: str
    group: str
    central: CoefficientValue
    low: float | int | None
    high: float | int | None
    choices: tuple[int | str, ...]
    stage2_only: bool

    def __post_init__(self) -> None:
        """Refuse an unknown kind or group, a range out of order or a malformed choice."""
        if self.kind not in COEFFICIENT_KINDS:
            raise ValueError(f"kind must be one of {COEFFICIENT_KINDS}, got {self.kind!r}")
        if self.group not in COEFFICIENT_GROUPS:
            raise ValueError(f"group must be one of {COEFFICIENT_GROUPS}, got {self.group!r}")
        if self.kind == KIND_DISCRETE:
            if self.low is not None or self.high is not None:
                raise ValueError(f"{self.path}: a discrete coefficient has no low or high")
            if not self.choices or self.choices[0] != self.central:
                raise ValueError(f"{self.path}: the choices start with the central")
            if len(set(self.choices)) != len(self.choices):
                raise ValueError(f"{self.path}: the choices must be distinct")
            return
        if self.choices:
            raise ValueError(f"{self.path}: only a discrete coefficient has choices")
        if self.low is None or self.high is None:
            raise ValueError(f"{self.path}: a ranged coefficient needs low and high")
        if not self.low <= float(self.central) <= self.high:
            raise ValueError(f"{self.path}: needs low <= central <= high")


PATH_S_DG = "buckling.s_dg"
"""The SP-8007 pressure-increment switch (discrete)."""
PATH_GERARD_ROW = "buckling.gerard_row"
"""The stiffened row (discrete)."""
PATH_SKIRT_ENVELOPE_PATH = "load_entry.skirt_envelope_path"
"""The skirt's envelope path (discrete)."""
PATH_DOME_ALLOY = "materials.dome_alloy"
"""The domes' alloy (discrete)."""
JOINT_DISCRETE_PATHS: tuple[str, ...] = (PATH_S_DG, PATH_GERARD_ROW)
"""The discrete coefficients enumerated jointly in step 3 (source note 9.2: 4 combinations)."""
END_DISCRETE_PATHS: tuple[str, ...] = (PATH_SKIRT_ENVELOPE_PATH, PATH_DOME_ALLOY)
"""The discrete coefficients set at their extreme choice by the tornado (monotone by
construction, source note 9.2)."""
PRESSURE_PATHS_STAGE1: tuple[str, ...] = (
    "pressures.stage1_lox.p_meop_bar",
    "pressures.stage1_lox.p_min_fraction",
    "pressures.stage1_rp1.p_meop_bar",
    "pressures.stage1_rp1.p_min_fraction",
)
"""Stage 1's four pressure coefficients (enumerated in step 3, source note 9.3)."""
PRESSURE_PATHS_STAGE2: tuple[str, ...] = (
    "pressures.stage2_lox.p_meop_bar",
    "pressures.stage2_lox.p_min_fraction",
    "pressures.stage2_rp1.p_meop_bar",
    "pressures.stage2_rp1.p_min_fraction",
)
"""Stage 2's four pressure coefficients (four of the stage-2-only five)."""
PATH_INTERSTAGE_LENGTH = "geometry.interstage_length_m"
"""The interstage length (the fifth stage-2-only coefficient; monotone by construction)."""
NOF_PATHS: tuple[str, ...] = (
    "nof.nof_barrel",
    "nof.nof_stiffened",
    "nof.nof_dome",
    "nof.nof_entry_ratio",
)
"""The four non-optimum factors (design axes; dm is linear in each)."""
PATH_RISE_TIME = "dynamics.rise_time_s"
"""The assumed real-drive rise time (a design axis)."""
PATH_AXIAL_FREQUENCY = "dynamics.axial_frequency_Hz"
"""The stack's first axial frequency (a design axis)."""
PATH_RING_PADS = "ring.ring_pads"
"""The ring frame's pad count (an integer design axis)."""
PATH_K_TS = "thrust_structure.k_ts_kg_per_kN"
"""The thrust structure's mass per added load (a design axis of the thrust-structure row)."""
LINEAR_AXIS_PATHS: tuple[str, ...] = (*NOF_PATHS, PATH_K_TS)
"""The design axes dm is linear in (their break-even values are closed-form, 9.3 D)."""
LINEAR_AXIS_FLOORS: dict[str, float] = {**dict.fromkeys(NOF_PATHS, NOF_MIN), PATH_K_TS: 0.0}
"""Each linear axis's physical floor, in its file units: NOF_MIN for the four non-optimum
factors (StructureCoefficients refuses less), 0 for k_ts (a mass per added load). A
break-even root below it is not reached by any admissible value (``_linear_break_even``)."""
BRACKETED_AXIS_PATHS: tuple[str, ...] = (PATH_RISE_TIME, PATH_AXIAL_FREQUENCY)
"""The design axes whose break-even values are bracketed roots (9.3 D)."""
MARGIN_ROWS: tuple[float, ...] = (0.10, 0.25)
"""The margin rows on the envelope loads (D-SP7-03; margin 0 is the central)."""
ENVELOPE_CAP_ROWS_G: tuple[float, ...] = (4.5, 4.0)
"""The envelope-cap rows [g0] (design 4.2.6 and 4.10; none is the central)."""
RING_PAD_ROW_COUNTS: tuple[int, ...] = (4, 6, 8)
"""The pad-count axis row's counts (source note section 4); the break-even search adds S1's
minimum RING_PADS_MIN and the whole counts between them (9.3 D)."""

SEARCH_LABEL = "the extremes found by the screened search over the stated ranges"
"""The label of the search's sets (design 4.2.6), never "the bounds"."""
SET_PHYSICS_LOW = "physics_low_mass"
SET_PHYSICS_HIGH = "physics_high_mass"
SET_OUTER_LOW = "outer_low_mass"
SET_OUTER_HIGH = "outer_high_mass"
SEARCH_SET_NAMES: tuple[str, ...] = (
    SET_PHYSICS_LOW,
    SET_PHYSICS_HIGH,
    SET_OUTER_LOW,
    SET_OUTER_HIGH,
)
"""The four frozen sets (design 4.2.6, D-SP7-18), in the structure file's order."""
LOW_MASS = "low_mass"
"""The direction that lowers dm."""
HIGH_MASS = "high_mass"
"""The direction that raises dm."""
DIRECTIONS: tuple[str, ...] = (LOW_MASS, HIGH_MASS)
"""Both directions of a band."""
CLASS_MONOTONE = "monotone"
CLASS_NON_MONOTONE = "non_monotone"
CLASS_FLAT = "flat"
CLASS_DISCRETE = "discrete"
SCAN_POINTS = 5
"""Points of each continuous coefficient's scan, its range's ends included (design 4.2.6
step 2)."""
GRID_POINTS = 3
"""Points per enumerated coefficient in step 3: both ends and the interior scan point most
extreme in the set's direction (source note 9.3)."""
GRID_POINTS_FALLBACK = 2
"""Fallback 1's points per enumerated coefficient: the two scan points most extreme in the
set's direction."""
SAMPLES_PHYSICS = 500
"""Search A's extremality samples (both ends)."""
SAMPLES_STAGE2_PER_SET = 50
"""Search B's extremality samples per set."""
SAMPLES_CORNER = 250
"""Search C's extremality samples per corner (one end each)."""
STEP3_BUDGET = 2000
"""The largest step-3 enumeration of one search (design 4.2.6); beyond it the extra
non-monotone coefficients are set by a coordinate sweep (source note 9.3)."""
COORDINATE_PASSES = 2
"""Passes of the coordinate sweep (source note 9.3)."""
POLISH_MAX_PASSES = 4
"""The polish's pass cap (D-SP7-38): after step 3 (and any coordinate sweep), each varied
coefficient in turn is moved alone over its scan points (a discrete one over its choices)
to the most extreme dm in the end's direction, pass after pass until a pass moves nothing
(converged) or this cap is reached (recorded)."""
LOCAL_CHECK_POINTS = 9
"""Points of each continuous coefficient in the one-coordinate check (D-SP7-38), its
range's ends included: finer than the scan's SCAN_POINTS (whose points it contains), so the
check can see an interior optimum the polish's points could not."""
CHECK_SAMPLES = "random_samples"
"""Extremality check: the seeded uniform samples of design 4.2.6 step 4."""
CHECK_ONE_COORDINATE = "one_coordinate"
"""Extremality check (D-SP7-38): every coefficient the search chose, moved alone from the
found end over LOCAL_CHECK_POINTS points or its other choices."""
CHECK_ONE_COORDINATE_HELD = "one_coordinate_held"
"""Extremality check of search B (D-SP7-38): the physics coefficients B holds at search A's
values, moved alone at the step row (how far the headline's sets lie from the step row's
own one-coordinate extremes; they are not re-chosen there, source note 9.3 B)."""
EXTREMALITY_CHECKS: tuple[str, ...] = (
    CHECK_SAMPLES,
    CHECK_ONE_COORDINATE,
    CHECK_ONE_COORDINATE_HELD,
)
"""The extremality checks a found end records (none is acted on)."""
BREAK_EVEN_PLANNED_SIZINGS = 46
"""Search D's planned sizings (source note 9.3 D: about 46)."""
MONOTONE_TOL_KG = 1.0e-6
"""Two dm values closer than this [kg] count as equal when a scan is classified (about the
brentq thickness tolerance's mass, 1e-12 m over the stage-1 walls)."""
SEARCH_SEED = 20261008
"""The seed of the extremality samples (numpy default_rng; each search adds its offset)."""
SEARCH_WALL_TIME_S = 600.0
"""The slow test's wall-time budget [s] (S2's gate: under 10 minutes)."""
FALLBACK_GRID_TWO_POINTS = "fallback_1_grid_two_points"
"""Fallback 1 (source note 9.3): every step-3 grid on two points per coefficient."""
FALLBACK_SAMPLES_HALVED = "fallback_2_samples_halved"
"""Fallback 2: the extremality samples halved."""
SEARCH_FALLBACKS: tuple[str, ...] = (FALLBACK_GRID_TWO_POINTS, FALLBACK_SAMPLES_HALVED)
"""The fallbacks in the order they are applied; the third puts the budget to the user."""
SEED_OFFSET_A, SEED_OFFSET_B_LOW, SEED_OFFSET_B_HIGH, SEED_OFFSET_C_LOW, SEED_OFFSET_C_HIGH = (
    0,
    1,
    2,
    3,
    4,
)
BREAK_EVEN_LEVELS: tuple[float, ...] = (0.5, 0.0)
"""The x* levels of the break-even values, as fractions of the uncharged headline (design
4.2.6 step 5)."""
BREAK_EVEN_XTOL_REL = 1.0e-6
"""The bracketed break-even root's tolerance, relative to its axis's range width."""
PLACEMENT_TOL_KG = 1.0e-3
"""The coupled placement's convergence tolerance on x [kg]."""
PLACEMENT_MAX_ITERATIONS = 100
"""The coupled placement's iteration cap."""
BE_IN_RANGE = "in_range"
BE_OUTSIDE_RANGE = "outside_range"
BE_ABOVE_THROUGHOUT = "above_level_throughout"
BE_BELOW_THROUGHOUT = "below_level_throughout"
BREAK_EVEN_STATUSES: tuple[str, ...] = (
    BE_IN_RANGE,
    BE_OUTSIDE_RANGE,
    BE_ABOVE_THROUGHOUT,
    BE_BELOW_THROUGHOUT,
)
"""A break-even value's status: the root inside the axis's range; a linear axis's root
outside it but at or above the axis's physical floor (LINEAR_AXIS_FLOORS; reported); x*
above the level over the whole range (not reached); x* below it over the whole range. A
linear axis whose root lies below its floor takes one of the last two (its value None):
then no admissible value reaches the level, the range included."""


@dataclass(frozen=True)
class SizingCase:
    """What a search sizing takes besides the coefficients: dynamic and entry
    (``size_increment``), margin and envelope_cap_g [g0] (``build_envelope``), offload_kg
    [kg] (the push's stage-1 offload; None: the headline's), check_ranges (False lets a
    value leave its file range: the break-even search's N_p = RING_PADS_MIN)."""

    dynamic: DynamicMode = "rise_time"
    entry: EntryPath = ENTRY_AFT_RING
    margin: float = 0.0
    envelope_cap_g: float | None = None
    offload_kg: float | None = None
    check_ranges: bool = True


type SizingFn = Callable[[Mapping[str, CoefficientValue], SizingCase], Increment]
"""A sizing of one coefficient assignment (paths to file values; the unnamed ones at their
central) under a SizingCase: sim.structure_sizing builds it (the structure file, the flown
pad's PadLoadSet and the analytic push)."""


@dataclass(frozen=True)
class SizingSummary:
    """What a search keeps of a sizing: dm_stage1_kg and dm_stage2_kg [kg] and whether the
    upper stack was exceeded (stage 2 sized)."""

    dm_stage1_kg: float
    dm_stage2_kg: float
    stage2_sized: bool

    @property
    def total_kg(self) -> float:
        """dm_stage1_kg + dm_stage2_kg [kg], the search's objective."""
        return self.dm_stage1_kg + self.dm_stage2_kg


class SearchEvaluator:
    """The sizings of a search, memoized and counted: each distinct assignment (every
    coefficient's value, the central where none is given) under each SizingCase is sized
    once; ``count`` is the number of distinct sizings (the evaluation count the structure
    file records)."""

    def __init__(
        self,
        sizing: SizingFn,
        ranges: Sequence[CoefficientRange],
        extra_paths: Sequence[str] = (),
    ) -> None:
        """sizing: the SizingFn; ranges: every coefficient (``coefficient_ranges``);
        extra_paths: fixed numbers an assignment may also set (a sizing-only line's, such
        as ``factors.FS_ult``; absent from the assignment unless given)."""
        self._sizing = sizing
        self._ranges = tuple(ranges)
        self._central = {r.path: r.central for r in self._ranges}
        self._extra = frozenset(extra_paths) - set(self._central)
        self._memo: dict[
            tuple[tuple[tuple[str, CoefficientValue], ...], SizingCase], SizingSummary
        ] = {}

    @property
    def ranges(self) -> tuple[CoefficientRange, ...]:
        """The coefficients, in the file's order."""
        return self._ranges

    @property
    def count(self) -> int:
        """The number of distinct sizings so far."""
        return len(self._memo)

    def coefficient(self, path: str) -> CoefficientRange:
        """The CoefficientRange of a path (KeyError if absent)."""
        for item in self._ranges:
            if item.path == path:
                return item
        raise KeyError(path)

    def assignment(self, values: Mapping[str, CoefficientValue]) -> dict[str, CoefficientValue]:
        """Every coefficient's value: the central overridden by values (and any extra path
        given); KeyError for an unknown path."""
        unknown = set(values) - set(self._central) - self._extra
        if unknown:
            raise KeyError(f"unknown coefficient paths {sorted(unknown)}")
        return {**self._central, **values}

    def summary(self, values: Mapping[str, CoefficientValue], case: SizingCase) -> SizingSummary:
        """The SizingSummary of an assignment under a case (sized once, then memoized)."""
        full = self.assignment(values)
        key = (tuple(sorted(full.items())), case)
        if key not in self._memo:
            inc = self._sizing(full, case)
            self._memo[key] = SizingSummary(inc.dm_stage1_kg, inc.dm_stage2_kg, inc.stage2_sized)
        return self._memo[key]

    def dm(self, values: Mapping[str, CoefficientValue], case: SizingCase) -> float:
        """dm1 + dm2 [kg] of an assignment under a case."""
        return self.summary(values, case).total_kg

    def increment(self, values: Mapping[str, CoefficientValue], case: SizingCase) -> Increment:
        """The full Increment of an assignment (sized afresh for a report; not counted)."""
        return self._sizing(self.assignment(values), case)


@dataclass(frozen=True)
class TornadoRow:
    """One coefficient's tornado row: path; values, its range's low and high (a continuous
    or integer one) or its alternatives (a discrete one); dm_kg at each [kg]; base_value
    and base_dm_kg, the base assignment's value and dm."""

    path: str
    values: tuple[CoefficientValue, ...]
    dm_kg: tuple[float, ...]
    base_value: CoefficientValue
    base_dm_kg: float

    @property
    def swing_kg(self) -> float:
        """The largest minus the smallest dm over the row's values and the base [kg]."""
        every = (*self.dm_kg, self.base_dm_kg)
        return max(every) - min(every)


@dataclass(frozen=True)
class Scan:
    """One continuous coefficient's scan: path; values, SCAN_POINTS from its low to its high;
    dm_kg at each [kg]; classification CLASS_MONOTONE, CLASS_NON_MONOTONE or CLASS_FLAT
    (``classify_scan``)."""

    path: str
    values: tuple[float, ...]
    dm_kg: tuple[float, ...]
    classification: str

    def end(self, direction: str) -> float:
        """The range end with the lower (LOW_MASS) or higher (HIGH_MASS) dm."""
        first, last = self.dm_kg[0], self.dm_kg[-1]
        lower = self.values[0] if first <= last else self.values[-1]
        upper = self.values[-1] if last >= first else self.values[0]
        return lower if _direction(direction) == LOW_MASS else upper

    def grid_values(self, direction: str, points: int) -> tuple[float, ...]:
        """The values step 3 enumerates (source note 9.3): with points GRID_POINTS both
        ends and the interior point most extreme in the direction; with
        GRID_POINTS_FALLBACK the two points most extreme in it (in scan order)."""
        sign = 1.0 if _direction(direction) == LOW_MASS else -1.0
        if points == GRID_POINTS:
            interior = range(1, len(self.values) - 1)
            best = min(interior, key=lambda i: (sign * self.dm_kg[i], i))
            return (self.values[0], self.values[best], self.values[-1])
        if points == GRID_POINTS_FALLBACK:
            order = sorted(range(len(self.values)), key=lambda i: (sign * self.dm_kg[i], i))
            return tuple(self.values[i] for i in sorted(order[:2]))
        raise ValueError(f"points must be {GRID_POINTS} or {GRID_POINTS_FALLBACK}, got {points}")


def _direction(direction: str) -> str:
    """direction when it is LOW_MASS or HIGH_MASS; ValueError otherwise."""
    if direction not in DIRECTIONS:
        raise ValueError(f"direction must be one of {DIRECTIONS}, got {direction!r}")
    return direction


def _better(direction: str, candidate: float, incumbent: float | None) -> bool:
    """Whether candidate is strictly more extreme than incumbent in the direction (ties keep
    the incumbent; None is beaten by anything)."""
    if incumbent is None:
        return True
    return candidate < incumbent if direction == LOW_MASS else candidate > incumbent


def classify_scan(dm_kg: Sequence[float], tol_kg: float = MONOTONE_TOL_KG) -> str:
    """CLASS_FLAT when every dm [kg] lies within tol_kg of every other; CLASS_MONOTONE when
    every step is >= -tol_kg (non-decreasing) or every step <= tol_kg (non-increasing);
    CLASS_NON_MONOTONE otherwise. Frame: none."""
    values = [float(v) for v in dm_kg]
    if max(values) - min(values) <= tol_kg:
        return CLASS_FLAT
    steps = [b - a for a, b in itertools.pairwise(values)]
    if all(s >= -tol_kg for s in steps) or all(s <= tol_kg for s in steps):
        return CLASS_MONOTONE
    return CLASS_NON_MONOTONE


def scan_values(item: CoefficientRange, points: int = SCAN_POINTS) -> tuple[float, ...]:
    """``points`` equally spaced values of a continuous coefficient from its low to its high
    (the ends exactly). Frame: none."""
    if item.kind != KIND_CONTINUOUS or item.low is None or item.high is None:
        raise ValueError(f"{item.path}: only a continuous coefficient is scanned")
    return tuple(float(v) for v in np.linspace(float(item.low), float(item.high), points))


@dataclass(frozen=True)
class PolishMove:
    """One move of the polish (D-SP7-38): path; from_value and to_value, in the file's
    units; dm_change_kg [kg], the dm the move adds (negative: it lowers dm, as every move of
    a low-mass end does); pass_index, the pass it was made in (0 first)."""

    path: str
    from_value: CoefficientValue
    to_value: CoefficientValue
    dm_change_kg: float
    pass_index: int


@dataclass(frozen=True)
class Polish:
    """The polish of one found end (``_polish``; D-SP7-38): moves, in the order made;
    passes, the passes run; converged, whether the last pass moved nothing (False when
    POLISH_MAX_PASSES was reached with a move in its last pass); dm_before_kg and
    dm_after_kg [kg], the end's dm before and after."""

    moves: tuple[PolishMove, ...]
    passes: int
    converged: bool
    dm_before_kg: float
    dm_after_kg: float


@dataclass(frozen=True)
class ExtremalityCheck:
    """One extremality check of a found end (recorded, never acted on): check, one of
    EXTREMALITY_CHECKS; trials, the assignments it sized; found_dm_kg [kg], the end's dm;
    extreme_dm_kg [kg], the most extreme trial in the end's direction (None without
    trials); excess_kg [kg], how far that trial lies beyond found_dm_kg in the direction (0
    when the found end holds: the check's power is then how close extreme_dm_kg comes);
    path and value, the coefficient moved and its value in that trial (the one-coordinate
    checks; None for the samples and without trials)."""

    check: str
    trials: int
    found_dm_kg: float
    extreme_dm_kg: float | None
    excess_kg: float
    path: str | None = None
    value: CoefficientValue | None = None

    def __post_init__(self) -> None:
        """Refuse an unknown check or a negative count or excess."""
        if self.check not in EXTREMALITY_CHECKS:
            raise ValueError(f"check must be one of {EXTREMALITY_CHECKS}, got {self.check!r}")
        if self.trials < 0:
            raise ValueError(f"trials must be >= 0, got {self.trials!r}")
        _require_non_negative("excess_kg", self.excess_kg)


@dataclass(frozen=True)
class BandSet:
    """One end of a band (``band_search``, ``stage2_search``): direction; values, the
    assignment of every coefficient the search varied or fixed (path, value) in the file's
    order; dm_kg [kg] at it (after the polish); grid, the step-3 axes (path, the values
    enumerated); combos, the joint discrete combinations enumerated; grid_size, the step-3
    sizings planned for this end; coordinate_swept, the extra non-monotone coefficients set
    by the coordinate sweep; polish, the one-coordinate polish that follows step 3
    (D-SP7-38); checks, its extremality checks (CHECK_SAMPLES first, then the
    one-coordinate checks), recorded and not acted on."""

    direction: str
    values: tuple[tuple[str, CoefficientValue], ...]
    dm_kg: float
    grid: tuple[tuple[str, tuple[CoefficientValue, ...]], ...]
    combos: int
    grid_size: int
    coordinate_swept: tuple[str, ...]
    polish: Polish
    checks: tuple[ExtremalityCheck, ...]

    def value(self, path: str) -> CoefficientValue:
        """The value of a path (KeyError if absent)."""
        for name, value in self.values:
            if name == path:
                return value
        raise KeyError(path)

    def as_dict(self) -> dict[str, CoefficientValue]:
        """The values as a dict."""
        return dict(self.values)

    def check(self, kind: str) -> ExtremalityCheck:
        """The extremality check of a kind (KeyError if not run)."""
        for item in self.checks:
            if item.check == kind:
                return item
        raise KeyError(kind)

    @property
    def samples(self) -> int:
        """The seeded samples that checked this end."""
        return self.check(CHECK_SAMPLES).trials

    @property
    def extreme_sample_kg(self) -> float | None:
        """The samples' most extreme dm [kg] (None without samples)."""
        return self.check(CHECK_SAMPLES).extreme_dm_kg

    @property
    def excess_kg(self) -> float:
        """How far the most extreme sample lies beyond dm_kg in the direction [kg]."""
        return self.check(CHECK_SAMPLES).excess_kg


@dataclass(frozen=True)
class BandSearch:
    """One run of design 4.2.6 steps 1-4 at a base (``band_search``): base, the fixed
    assignment (the design axes; () for central); case; base_dm_kg; stage2_sized (the
    upper stack exceeded at the base: the stage-2-only five are then varied); varied, the
    paths varied; tornado; scans; classification, each varied path's (CLASS_*); sets, one
    BandSet per direction run; samples and seed of the extremality check; evaluations, the
    distinct sizings this search added."""

    base: tuple[tuple[str, CoefficientValue], ...]
    case: SizingCase
    base_dm_kg: float
    stage2_sized: bool
    varied: tuple[str, ...]
    tornado: tuple[TornadoRow, ...]
    scans: tuple[Scan, ...]
    classification: tuple[tuple[str, str], ...]
    sets: tuple[BandSet, ...]
    samples: int
    seed: int
    evaluations: int

    def set(self, direction: str) -> BandSet:
        """The BandSet of a direction (KeyError if not run)."""
        for item in self.sets:
            if item.direction == direction:
                return item
        raise KeyError(direction)

    def scan(self, path: str) -> Scan:
        """The Scan of a path (KeyError if not scanned)."""
        for item in self.scans:
            if item.path == path:
                return item
        raise KeyError(path)


def _tornado(
    evaluator: SearchEvaluator,
    base: Mapping[str, CoefficientValue],
    case: SizingCase,
    items: Sequence[CoefficientRange],
) -> tuple[TornadoRow, ...]:
    """The tornado rows of items about base: a ranged one at its low and high, a discrete
    one at each choice other than the base's."""
    full = evaluator.assignment(base)
    base_dm = evaluator.dm(base, case)
    rows = []
    for item in items:
        current = full[item.path]
        if item.kind == KIND_DISCRETE:
            values: tuple[CoefficientValue, ...] = tuple(c for c in item.choices if c != current)
        else:
            assert item.low is not None and item.high is not None
            values = (item.low, item.high)
        dms = tuple(evaluator.dm({**base, item.path: v}, case) for v in values)
        rows.append(TornadoRow(item.path, values, dms, current, base_dm))
    return tuple(rows)


def _scans(
    evaluator: SearchEvaluator,
    base: Mapping[str, CoefficientValue],
    case: SizingCase,
    items: Sequence[CoefficientRange],
) -> tuple[Scan, ...]:
    """The scans of the continuous items about base."""
    out = []
    for item in items:
        if item.kind != KIND_CONTINUOUS:
            continue
        values = scan_values(item)
        dms = tuple(evaluator.dm({**base, item.path: v}, case) for v in values)
        out.append(Scan(item.path, values, dms, classify_scan(dms)))
    return tuple(out)


def _samples(
    evaluator: SearchEvaluator,
    base: Mapping[str, CoefficientValue],
    case: SizingCase,
    items: Sequence[CoefficientRange],
    count: int,
    seed: int,
) -> list[float]:
    """dm [kg] at count seeded random assignments: each continuous item uniform on its
    range, each discrete one a uniform choice, in items' order per sample (numpy
    default_rng(seed)); the rest at base."""
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(count):
        trial: dict[str, CoefficientValue] = dict(base)
        for item in items:
            if item.kind == KIND_DISCRETE:
                trial[item.path] = item.choices[int(rng.integers(len(item.choices)))]
            elif item.kind == KIND_CONTINUOUS:
                assert item.low is not None and item.high is not None
                trial[item.path] = float(rng.uniform(float(item.low), float(item.high)))
            else:
                raise ValueError(f"{item.path}: an integer coefficient is not sampled")
        out.append(evaluator.dm(trial, case))
    return out


def _excess(
    direction: str, found_kg: float, samples: Sequence[float]
) -> tuple[float | None, float]:
    """(the most extreme sample, its excess beyond the found end in the direction, >= 0)."""
    if not samples:
        return None, 0.0
    if direction == LOW_MASS:
        extreme = min(samples)
        return extreme, max(0.0, found_kg - extreme)
    extreme = max(samples)
    return extreme, max(0.0, extreme - found_kg)


def _sample_check(direction: str, found_kg: float, samples: Sequence[float]) -> ExtremalityCheck:
    """The CHECK_SAMPLES record of a found end [kg] against seeded samples' dm [kg]."""
    extreme, excess = _excess(direction, found_kg, samples)
    return ExtremalityCheck(CHECK_SAMPLES, len(samples), found_kg, extreme, excess)


def _moves_further(direction: str, candidate: float, incumbent: float) -> bool:
    """Whether candidate [kg] lies beyond incumbent [kg] in the direction by more than
    MONOTONE_TOL_KG (the polish moves only on a real change, not on rounding)."""
    if direction == LOW_MASS:
        return candidate < incumbent - MONOTONE_TOL_KG
    return candidate > incumbent + MONOTONE_TOL_KG


def _move_options(item: CoefficientRange, points: int) -> tuple[CoefficientValue, ...]:
    """The values a one-coordinate move tries: ``points`` equally spaced over a continuous
    coefficient's range (its ends exactly), every choice of a discrete one, every whole
    number of an integer one."""
    if item.kind == KIND_DISCRETE:
        return tuple(item.choices)
    if item.kind == KIND_INTEGER:
        assert item.low is not None and item.high is not None
        return tuple(range(int(item.low), int(item.high) + 1))
    return scan_values(item, points)


def _polish(
    evaluator: SearchEvaluator,
    case: SizingCase,
    direction: str,
    values: Mapping[str, CoefficientValue],
    items: Sequence[CoefficientRange],
) -> tuple[dict[str, CoefficientValue], float, Polish]:
    """The polish of a found end (D-SP7-38): each of items in turn moved alone to the value
    of ``_move_options``(item, SCAN_POINTS) whose dm lies furthest in the direction given
    the rest (by more than MONOTONE_TOL_KG; a tie keeps the earlier value), the move kept,
    passes repeated until one moves nothing or POLISH_MAX_PASSES. Returns the polished
    assignment, its dm [kg] and the Polish record. Frame: none."""
    current = dict(values)
    dm = evaluator.dm(current, case)
    before = dm
    moves: list[PolishMove] = []
    passes = 0
    converged = False
    while passes < POLISH_MAX_PASSES:
        moved = False
        for item in items:
            here = evaluator.assignment(current)[item.path]
            best_value, best_dm = here, dm
            for option in _move_options(item, SCAN_POINTS):
                if option == here:
                    continue
                d = evaluator.dm({**current, item.path: option}, case)
                if _moves_further(direction, d, best_dm):
                    best_value, best_dm = option, d
            if best_value != here:
                moves.append(PolishMove(item.path, here, best_value, best_dm - dm, passes))
                current[item.path] = best_value
                dm = best_dm
                moved = True
        passes += 1
        if not moved:
            converged = True
            break
    return current, dm, Polish(tuple(moves), passes, converged, before, dm)


def _one_coordinate_check(
    evaluator: SearchEvaluator,
    case: SizingCase,
    direction: str,
    values: Mapping[str, CoefficientValue],
    found_kg: float,
    items: Sequence[CoefficientRange],
    check: str = CHECK_ONE_COORDINATE,
) -> ExtremalityCheck:
    """A one-coordinate extremality check of a found end (D-SP7-38; recorded, not acted
    on): each of items moved alone from values over ``_move_options``(item,
    LOCAL_CHECK_POINTS) (its current value skipped); the most extreme trial in the
    direction (a tie keeps the earlier) and its excess beyond found_kg [kg]. Frame: none."""
    best: tuple[float, str, CoefficientValue] | None = None
    trials = 0
    full = evaluator.assignment(values)
    for item in items:
        here = full[item.path]
        for option in _move_options(item, LOCAL_CHECK_POINTS):
            if option == here:
                continue
            d = evaluator.dm({**values, item.path: option}, case)
            trials += 1
            if best is None or _better(direction, d, best[0]):
                best = (d, item.path, option)
    if best is None:
        return ExtremalityCheck(check, 0, found_kg, None, 0.0)
    extreme, path, value = best
    _, excess = _excess(direction, found_kg, [extreme])
    return ExtremalityCheck(check, trials, found_kg, extreme, excess, path, value)


def _enumerate(
    evaluator: SearchEvaluator,
    case: SizingCase,
    direction: str,
    fixed: Mapping[str, CoefficientValue],
    combos: Sequence[Mapping[str, CoefficientValue]],
    groups: Sequence[Sequence[tuple[str, tuple[CoefficientValue, ...]]]],
) -> tuple[dict[str, CoefficientValue], float]:
    """Step 3's enumeration: for each joint discrete combination, each group's grid (its
    axes' values crossed) in turn with the earlier groups at their best (the groups are
    separable by stage, source note 9.2); the most extreme assignment and its dm [kg]."""
    best_values: dict[str, CoefficientValue] | None = None
    best_dm: float | None = None
    for combo in combos:
        values: dict[str, CoefficientValue] = {**fixed, **combo}
        dm = None
        for axes in groups:
            if not axes:
                continue
            paths = [path for path, _ in axes]
            group_best: tuple[dict[str, CoefficientValue], float] | None = None
            for point in itertools.product(*(pts for _, pts in axes)):
                trial = {**values, **dict(zip(paths, point, strict=True))}
                d = evaluator.dm(trial, case)
                if group_best is None or _better(direction, d, group_best[1]):
                    group_best = (trial, d)
            assert group_best is not None
            values, dm = group_best
        if dm is None:
            dm = evaluator.dm(values, case)
        if _better(direction, dm, best_dm):
            best_values, best_dm = values, dm
    assert best_values is not None and best_dm is not None
    return best_values, best_dm


def _coordinate_sweep(
    evaluator: SearchEvaluator,
    case: SizingCase,
    direction: str,
    values: Mapping[str, CoefficientValue],
    scans: Sequence[Scan],
) -> tuple[dict[str, CoefficientValue], float]:
    """Each scan's coefficient in turn set to its most extreme scan point given the rest
    (a tie keeps the earlier point), COORDINATE_PASSES passes (source note 9.3)."""
    current = dict(values)
    dm = evaluator.dm(current, case)
    for _ in range(COORDINATE_PASSES):
        for scan in scans:
            best: tuple[dict[str, CoefficientValue], float] | None = None
            for value in scan.values:
                trial = {**current, scan.path: value}
                d = evaluator.dm(trial, case)
                if best is None or _better(direction, d, best[1]):
                    best = (trial, d)
            assert best is not None
            current, dm = best
    return current, dm


def band_search(
    evaluator: SearchEvaluator,
    base: Mapping[str, CoefficientValue],
    case: SizingCase,
    directions: Sequence[str],
    *,
    samples: int,
    seed: int,
    grid_points: int = GRID_POINTS,
    stage2: bool | None = None,
) -> BandSearch:
    """Design 4.2.6 steps 1-4 over the physics group at a base (source note 9.3 A; the
    corners of 9.3 C call it with the design axes at a corner).

    Inputs: evaluator; base, the values held fixed (the design axes; the physics group
    starts at central); case; directions, LOW_MASS and/or HIGH_MASS; samples and seed, the
    extremality check (one sample set checks every direction); grid_points, GRID_POINTS or
    fallback 1's GRID_POINTS_FALLBACK; stage2, whether to vary the stage-2-only five (None:
    when the base sizing exceeds the upper stack, the only case in which they act).
    Output: a BandSearch. Steps: (1) the tornado, every varied coefficient at its range's
    ends or alternatives, the rest at base; (2) a SCAN_POINTS scan of each continuous one,
    classified (``classify_scan``); (3) per direction: a monotone coefficient at the end
    that moves dm that way, a flat one at its base value, END_DISCRETE_PATHS at their most
    extreme tornado choice; the pressures (and any other non-monotone coefficient, in its
    stage's grid) on ``Scan.grid_values`` crossed with every JOINT_DISCRETE_PATHS
    combination, stage 1's grid then stage 2's (separable); if that would exceed
    STEP3_BUDGET sizings over the directions, the extra non-monotone coefficients are set
    afterwards by the coordinate sweep; then the polish (D-SP7-38, ``_polish``): every
    varied coefficient moved alone over its scan points or choices, re-read at the end
    itself (a direction read at the base can reverse there), until a pass moves nothing;
    (4) the extremality checks, recorded and not acted on: samples seeded random
    assignments about the base (the excess beyond each found end), and the one-coordinate
    check (``_one_coordinate_check``: every varied coefficient alone over
    LOCAL_CHECK_POINTS points or its choices from the found end).
    Frame: none.
    """
    start = evaluator.count
    base = dict(base)
    s2 = evaluator.summary(base, case).stage2_sized if stage2 is None else stage2
    varied = [r for r in evaluator.ranges if r.group == GROUP_PHYSICS and (s2 or not r.stage2_only)]
    for item in varied:
        if item.kind == KIND_INTEGER:
            raise ValueError(f"{item.path}: the physics band varies no integer coefficient")
    base_dm = evaluator.dm(base, case)
    tornado = _tornado(evaluator, base, case, varied)
    scans = _scans(evaluator, base, case, varied)
    by_path = {s.path: s for s in scans}
    classification = tuple(
        (r.path, CLASS_DISCRETE if r.kind == KIND_DISCRETE else by_path[r.path].classification)
        for r in varied
    )
    pressures = set(PRESSURE_PATHS_STAGE1) | set(PRESSURE_PATHS_STAGE2)
    extras = [
        s for s in scans if s.classification == CLASS_NON_MONOTONE and s.path not in pressures
    ]
    joint = [r for r in varied if r.path in JOINT_DISCRETE_PATHS]
    combos = [
        dict(zip([r.path for r in joint], choice, strict=True))
        for choice in itertools.product(*(r.choices for r in joint))
    ] or [{}]

    def stage_of(path: str) -> int:
        item = evaluator.coefficient(path)
        return 1 if item.stage2_only else 0

    def grids(
        direction: str, with_extras: bool
    ) -> list[list[tuple[str, tuple[CoefficientValue, ...]]]]:
        out: list[list[tuple[str, tuple[CoefficientValue, ...]]]] = [[], []]
        for scan in scans:
            if scan.path in pressures or (with_extras and scan in extras):
                out[stage_of(scan.path)].append(
                    (scan.path, scan.grid_values(direction, grid_points))
                )
        return out

    def planned(with_extras: bool) -> int:
        total = 0
        for direction in directions:
            per = sum(
                math.prod(len(pts) for _, pts in group)
                for group in grids(direction, with_extras)
                if group
            )
            total += len(combos) * per
        return total

    with_extras = bool(extras) and planned(True) <= STEP3_BUDGET
    torn = {row.path: row for row in tornado}
    sample_dm = _samples(evaluator, base, case, varied, samples, seed)
    sets = []
    for direction in directions:
        _direction(direction)
        fixed: dict[str, CoefficientValue] = dict(base)
        for scan in scans:
            if scan.classification == CLASS_MONOTONE:
                fixed[scan.path] = scan.end(direction)
        for path in END_DISCRETE_PATHS:
            if path not in torn:
                continue
            row = torn[path]
            options = [(row.base_dm_kg, row.base_value), *zip(row.dm_kg, row.values, strict=True)]
            chosen = options[0]
            for option in options[1:]:
                if _better(direction, option[0], chosen[0]):
                    chosen = option
            fixed[path] = chosen[1]
        groups = grids(direction, with_extras)
        values, dm = _enumerate(evaluator, case, direction, fixed, combos, groups)
        swept: tuple[str, ...] = ()
        if extras and not with_extras:
            values, dm = _coordinate_sweep(evaluator, case, direction, values, extras)
            swept = tuple(s.path for s in extras)
        values, dm, polish = _polish(evaluator, case, direction, values, varied)
        checks = (
            _sample_check(direction, dm, sample_dm),
            _one_coordinate_check(evaluator, case, direction, values, dm, varied),
        )
        size_planned = len(combos) * sum(
            math.prod(len(pts) for _, pts in group) for group in groups if group
        )
        full = evaluator.assignment(values)
        kept = {*base, *(r.path for r in varied)}
        recorded = tuple((r.path, full[r.path]) for r in evaluator.ranges if r.path in kept)
        sets.append(
            BandSet(
                direction=direction,
                values=recorded,
                dm_kg=dm,
                grid=tuple((p, v) for group in groups for p, v in group),
                combos=len(combos),
                grid_size=size_planned,
                coordinate_swept=swept,
                polish=polish,
                checks=checks,
            )
        )
    return BandSearch(
        base=tuple(sorted(base.items())),
        case=case,
        base_dm_kg=base_dm,
        stage2_sized=s2,
        varied=tuple(r.path for r in varied),
        tornado=tornado,
        scans=scans,
        classification=classification,
        sets=tuple(sets),
        samples=len(sample_dm),
        seed=seed,
        evaluations=evaluator.count - start,
    )


@dataclass(frozen=True)
class Stage2Search:
    """Search B (source note 9.3 B; ``stage2_search``): the stage-2-only five for the physics
    sets at the step row. case (the step row); tornado (the four stage-2 pressures and the
    interstage length about the central); scans (the four pressures); sets, one BandSet per
    direction (the physics set's values from A, the interstage at its end, the pressures
    enumerated on their grid values with A's values, then the five polished; its checks:
    samples over the four pressures, the one-coordinate check over the five and the held
    check over the physics coefficients B keeps at A's values); evaluations."""

    case: SizingCase
    tornado: tuple[TornadoRow, ...]
    scans: tuple[Scan, ...]
    sets: tuple[BandSet, ...]
    evaluations: int

    def set(self, direction: str) -> BandSet:
        """The BandSet of a direction (KeyError if not run)."""
        for item in self.sets:
            if item.direction == direction:
                return item
        raise KeyError(direction)


def stage2_search(
    evaluator: SearchEvaluator,
    physics_sets: Mapping[str, Mapping[str, CoefficientValue]],
    case: SizingCase,
    *,
    samples_per_set: int,
    seeds: Mapping[str, int],
    grid_points: int = GRID_POINTS,
) -> Stage2Search:
    """Search B (source note 9.3 B): the stage-2-only five, which act only when the upper
    stack is sized, chosen for each physics set at a push that sizes it.

    Inputs: evaluator; physics_sets, direction -> search A's set values; case, the step row
    (dynamic "step": DLF 2 on the plain plateau, n_peak about 7.0 g0, above MECO's 5.195
    g0); samples_per_set and seeds (direction -> seed) of the extremality check;
    grid_points as ``band_search``.
    Output: a Stage2Search. The tornado (the four pressures at their ends, the interstage
    length at its ends) and the pressures' scans are taken about the central; per set the
    interstage length sits at its end in the set's direction (monotone by construction;
    the tornado's dm decides, a tie by construction: the low end for LOW_MASS), and the
    four pressures are enumerated on ``Scan.grid_values`` with every other coefficient at
    the set's value from A; then the five are polished (``_polish``, D-SP7-38). Checks,
    recorded and not acted on: samples_per_set samples over the four pressures about the
    polished set, the one-coordinate check over the five, and CHECK_ONE_COORDINATE_HELD
    over the stage-1 physics coefficients (held at A's values, not re-chosen at the step
    row). Frame: none.
    """
    start = evaluator.count
    pressures = [evaluator.coefficient(p) for p in PRESSURE_PATHS_STAGE2]
    interstage = evaluator.coefficient(PATH_INTERSTAGE_LENGTH)
    five = [*pressures, interstage]
    held = [r for r in evaluator.ranges if r.group == GROUP_PHYSICS and not r.stage2_only]
    if not evaluator.summary({}, case).stage2_sized:
        raise ValueError("search B needs a case that sizes stage 2 (the step row)")
    tornado = _tornado(evaluator, {}, case, five)
    scans = _scans(evaluator, {}, case, pressures)
    row = tornado[-1]
    sets = []
    for direction, values in physics_sets.items():
        _direction(direction)
        low_dm, high_dm = row.dm_kg
        if low_dm == high_dm:
            end = row.values[0] if direction == LOW_MASS else row.values[1]
        else:
            lower = row.values[0] if low_dm < high_dm else row.values[1]
            upper = row.values[1] if low_dm < high_dm else row.values[0]
            end = lower if direction == LOW_MASS else upper
        fixed = {**values, PATH_INTERSTAGE_LENGTH: end}
        group = [(s.path, s.grid_values(direction, grid_points)) for s in scans]
        best, dm = _enumerate(evaluator, case, direction, fixed, [{}], [group])
        best, dm, polish = _polish(evaluator, case, direction, best, five)
        sample_dm = _samples(evaluator, best, case, pressures, samples_per_set, seeds[direction])
        checks = (
            _sample_check(direction, dm, sample_dm),
            _one_coordinate_check(evaluator, case, direction, best, dm, five),
            _one_coordinate_check(
                evaluator, case, direction, best, dm, held, check=CHECK_ONE_COORDINATE_HELD
            ),
        )
        full = evaluator.assignment(best)
        sets.append(
            BandSet(
                direction=direction,
                values=tuple((r.path, full[r.path]) for r in evaluator.ranges if r.path in best),
                dm_kg=dm,
                grid=tuple(group),
                combos=1,
                grid_size=math.prod(len(pts) for _, pts in group),
                coordinate_swept=(),
                polish=polish,
                checks=checks,
            )
        )
    return Stage2Search(
        case=case,
        tornado=tornado,
        scans=scans,
        sets=tuple(sets),
        evaluations=evaluator.count - start,
    )


def design_corner(evaluator: SearchEvaluator, direction: str) -> dict[str, CoefficientValue]:
    """The design axes at a corner, fixed without search because each is monotone by
    construction (source note 9.3 C). LOW_MASS: the four factors at their low ends, the
    rise time at its high end, the frequency at its high end, the most pads, k_ts at its
    low end. HIGH_MASS: the factors and k_ts at their high ends, the frequency at its low
    end, the rise time max(its low end, 1/(pi f)) (the largest at which the DLF cap still
    binds, so the largest n_peak in the box), the fewest pads of the axis. Frame: none."""

    def end(path: str, high: bool) -> CoefficientValue:
        item = evaluator.coefficient(path)
        assert item.low is not None and item.high is not None
        return item.high if high else item.low

    low = _direction(direction) == LOW_MASS
    values: dict[str, CoefficientValue] = {p: end(p, not low) for p in NOF_PATHS}
    values[PATH_K_TS] = end(PATH_K_TS, not low)
    values[PATH_RING_PADS] = end(PATH_RING_PADS, low)
    values[PATH_AXIAL_FREQUENCY] = end(PATH_AXIAL_FREQUENCY, low)
    if low:
        values[PATH_RISE_TIME] = end(PATH_RISE_TIME, True)
    else:
        f_low = float(end(PATH_AXIAL_FREQUENCY, False))
        values[PATH_RISE_TIME] = max(float(end(PATH_RISE_TIME, False)), 1.0 / (math.pi * f_low))
    return values


@dataclass(frozen=True)
class OuterSearch:
    """Search C (source note 9.3 C; ``outer_search``): margin_rows, (margin, dm) at physics
    central and the headline (margin 0 first); margin_low and margin_high, the rows that
    lower and raise dm; cap_low_g and cap_high_g [g0], the envelope caps of the two corners
    (None and the lowest cap row); low and high, the corner BandSearches; sets, direction -> the
    outer set's values (every coefficient, the case fields ``margin`` and
    ``envelope_cap_g`` included); evaluations."""

    margin_rows: tuple[tuple[float, float], ...]
    margin_low: float
    margin_high: float
    cap_low_g: float | None
    cap_high_g: float | None
    low: BandSearch
    high: BandSearch
    sets: tuple[tuple[str, tuple[tuple[str, CoefficientValue | None], ...]], ...]
    evaluations: int

    def set_values(self, direction: str) -> dict[str, CoefficientValue | None]:
        """The outer set of a direction as a dict."""
        for name, values in self.sets:
            if name == direction:
                return dict(values)
        raise KeyError(direction)

    def corner(self, direction: str) -> BandSearch:
        """The corner BandSearch of a direction."""
        return self.low if _direction(direction) == LOW_MASS else self.high


CASE_MARGIN = "margin"
"""The outer sets' key for the margin row (an offload-case field, design 4.3)."""
CASE_ENVELOPE_CAP = "envelope_cap_g"
"""The outer sets' key for the envelope cap [g0] (an offload-case field)."""


def outer_search(
    evaluator: SearchEvaluator,
    physics_sets: Mapping[str, Mapping[str, CoefficientValue]],
    case: SizingCase,
    *,
    samples: int,
    seeds: Mapping[str, int],
    grid_points: int = GRID_POINTS,
) -> OuterSearch:
    """Search C (source note 9.3 C): the outer envelope, the screened search over both
    groups at the design axes' two corners.

    Inputs: evaluator; physics_sets, direction -> the physics set's values after B (their
    stage-2-only five fill a corner that does not size stage 2); case, the headline push;
    samples and seeds (direction -> seed) of each corner's extremality check; grid_points.
    Output: an OuterSearch. The margin's direction from its tornado at physics central (the
    rows MARGIN_ROWS against 0); each corner's design axes by ``design_corner``, its margin
    the row that moves dm its way, its cap none (LOW_MASS) or the lowest of
    ENVELOPE_CAP_ROWS_G (HIGH_MASS; a cap only raises dm); ``band_search`` re-run at each
    corner in its own direction (the physics coefficients' directions may change there;
    the stage-2-only five varied when that corner sizes stage 2). Frame: none.
    """
    start = evaluator.count
    rows = [(0.0, evaluator.dm({}, case))]
    rows += [(m, evaluator.dm({}, replace(case, margin=m))) for m in MARGIN_ROWS]
    margin_low = min(rows, key=lambda r: r[1])[0]
    margin_high = max(rows, key=lambda r: r[1])[0]
    caps = {LOW_MASS: None, HIGH_MASS: min(ENVELOPE_CAP_ROWS_G)}
    margins = {LOW_MASS: margin_low, HIGH_MASS: margin_high}
    corners: dict[str, BandSearch] = {}
    sets = []
    for direction in DIRECTIONS:
        design = design_corner(evaluator, direction)
        corner_case = replace(case, margin=margins[direction], envelope_cap_g=caps[direction])
        search = band_search(
            evaluator,
            design,
            corner_case,
            (direction,),
            samples=samples,
            seed=seeds[direction],
            grid_points=grid_points,
        )
        corners[direction] = search
        values: dict[str, CoefficientValue | None] = {}
        found = search.set(direction).as_dict()
        physics = physics_sets[direction]
        for item in evaluator.ranges:
            if item.path in found:
                values[item.path] = found[item.path]
            elif item.stage2_only and not search.stage2_sized:
                values[item.path] = physics[item.path]
            elif item.path in design:
                values[item.path] = design[item.path]
            else:
                raise ValueError(f"{item.path}: the outer set has no value for it")
        values[CASE_MARGIN] = margins[direction]
        values[CASE_ENVELOPE_CAP] = caps[direction]
        sets.append((direction, tuple(values.items())))
    return OuterSearch(
        margin_rows=tuple(rows),
        margin_low=margin_low,
        margin_high=margin_high,
        cap_low_g=caps[LOW_MASS],
        cap_high_g=caps[HIGH_MASS],
        low=corners[LOW_MASS],
        high=corners[HIGH_MASS],
        sets=tuple(sets),
        evaluations=evaluator.count - start,
    )


def _check_fallbacks(fallbacks: Sequence[str]) -> None:
    """ValueError for a fallback not in SEARCH_FALLBACKS."""
    for item in fallbacks:
        if item not in SEARCH_FALLBACKS:
            raise ValueError(f"unknown fallback {item!r}")


@dataclass(frozen=True)
class _PlanCounts:
    """The coefficient tallies the plan is computed from (``_plan_counts``)."""

    stage1_continuous: int
    stage2_continuous: int
    alternatives: int
    discrete: int
    joint_combinations: int
    stage1_pressures: int
    stage2_pressures: int


def _plan_counts(ranges: Sequence[CoefficientRange]) -> _PlanCounts:
    """The physics group's tallies: stage-1 active and stage-2-only continuous coefficients,
    the discrete coefficients and their alternatives, the joint discrete combinations and
    each stage's pressure coefficients (source note 9.1: 18, 5, 4, 4, 4, 4, 4)."""
    physics = [r for r in ranges if r.group == GROUP_PHYSICS]
    discrete = [r for r in physics if r.kind == KIND_DISCRETE]
    paths = {r.path for r in physics}
    return _PlanCounts(
        stage1_continuous=sum(
            1 for r in physics if r.kind == KIND_CONTINUOUS and not r.stage2_only
        ),
        stage2_continuous=sum(1 for r in physics if r.kind == KIND_CONTINUOUS and r.stage2_only),
        alternatives=sum(len(r.choices) - 1 for r in discrete),
        discrete=len(discrete),
        joint_combinations=math.prod(
            len(r.choices) for r in discrete if r.path in JOINT_DISCRETE_PATHS
        ),
        stage1_pressures=sum(1 for p in PRESSURE_PATHS_STAGE1 if p in paths),
        stage2_pressures=sum(1 for p in PRESSURE_PATHS_STAGE2 if p in paths),
    )


def note_planned_sizings(ranges: Sequence[CoefficientRange], fallbacks: Sequence[str] = ()) -> int:
    """Source note 9.3's budget of searches A-D [sizings], computed from the coefficients
    with the fallbacks applied (the pressures alone non-monotone; the six labelled lines and
    the polish of D-SP7-38 not counted): for the structure files 3,263 with none, 1,833 with
    fallback 1 and 1,283 with both.

    Inputs: ranges, every coefficient (``config.StructureConfig.coefficient_ranges``);
    fallbacks. Output [sizings]: A, the tornado (both ends of the stage-1 active continuous
    ones, each discrete alternative, the central: 41), the scans' interior points (54),
    step 3 (both ends x the joint combinations x the grid over stage 1's pressures: 648)
    and SAMPLES_PHYSICS; B, its tornado (11), the four pressures' scans (12), both sets'
    grids (162) and samples (100); C, the margin rows (2), the low corner as A for one end
    and the high corner over every physics coefficient, stage 2's grid added (669 and
    1,018); D, BREAK_EVEN_PLANNED_SIZINGS. Frame: none.
    """
    _check_fallbacks(fallbacks)
    c = _plan_counts(ranges)
    p = GRID_POINTS_FALLBACK if FALLBACK_GRID_TWO_POINTS in fallbacks else GRID_POINTS
    half = 2 if FALLBACK_SAMPLES_HALVED in fallbacks else 1
    interior = SCAN_POINTS - 2
    grid1 = p**c.stage1_pressures
    grid2 = p**c.stage2_pressures
    tornado_a = 2 * c.stage1_continuous + c.alternatives + 1
    scan_a = interior * c.stage1_continuous
    step3_a = len(DIRECTIONS) * c.joint_combinations * grid1
    search_a = tornado_a + scan_a + step3_a + SAMPLES_PHYSICS // half
    search_b = (
        2 * c.stage2_continuous
        + 1
        + interior * c.stage2_pressures
        + len(DIRECTIONS) * grid2
        + len(DIRECTIONS) * (SAMPLES_STAGE2_PER_SET // half)
    )
    low_corner = tornado_a + scan_a + c.joint_combinations * grid1 + SAMPLES_CORNER // half
    every = c.stage1_continuous + c.stage2_continuous
    high_corner = (
        2 * every
        + c.alternatives
        + 1
        + interior * every
        + c.joint_combinations * (grid1 + grid2)
        + SAMPLES_CORNER // half
    )
    search_c = len(MARGIN_ROWS) + low_corner + high_corner
    return search_a + search_b + search_c + BREAK_EVEN_PLANNED_SIZINGS


def polish_planned_sizings(ranges: Sequence[CoefficientRange]) -> int:
    """The bound [sizings] of D-SP7-38's polish and one-coordinate checks over searches A to
    C (2,935 for the structure files): per polished end, POLISH_MAX_PASSES passes over its
    varied coefficients (SCAN_POINTS values each, a discrete one's alternatives) and the
    one-coordinate check (LOCAL_CHECK_POINTS values each); A's two ends over the stage-1
    active coefficients, B's two over the five (its held check over the stage-1 ones
    besides), C's low corner over the stage-1 ones and its high corner over every physics
    coefficient. An upper bound: the memo and an early convergence take fewer. Frame: none.
    """
    c = _plan_counts(ranges)

    def end(continuous: int, alternatives: int) -> int:
        per_pass = SCAN_POINTS * continuous + alternatives
        check = LOCAL_CHECK_POINTS * continuous + alternatives
        return POLISH_MAX_PASSES * per_pass + check

    stage1 = end(c.stage1_continuous, c.alternatives)
    held = LOCAL_CHECK_POINTS * c.stage1_continuous + c.alternatives
    search_a = len(DIRECTIONS) * stage1
    search_b = len(DIRECTIONS) * (end(c.stage2_continuous, 0) + held)
    search_c = stage1 + end(c.stage1_continuous + c.stage2_continuous, c.alternatives)
    return search_a + search_b + search_c


def planned_sizings(ranges: Sequence[CoefficientRange], fallbacks: Sequence[str] = ()) -> int:
    """The planned sizings [sizings] the wall-time estimate uses: the note's plan
    (``note_planned_sizings``) plus the polish's bound (``polish_planned_sizings``), 6,198
    for the structure files without a fallback. Frame: none."""
    return note_planned_sizings(ranges, fallbacks) + polish_planned_sizings(ranges)


class SearchBudgetExceeded(ValueError):
    """Fallback 3 of source note 9.3: even both fallbacks exceed the wall-time budget, so
    the budget goes to the user (the protocol's section 4, item 4); no rule changes."""


def choose_fallbacks(
    seconds_per_sizing: float,
    ranges: Sequence[CoefficientRange],
    budget_s: float = SEARCH_WALL_TIME_S,
) -> tuple[str, ...]:
    """The fallbacks of source note 9.3, applied in order only while the estimate
    ``planned_sizings``(ranges, fallbacks) x seconds_per_sizing [s] exceeds budget_s [s]:
    () when the measured rate fits. Raises SearchBudgetExceeded when both do not suffice.
    Frame: none."""
    rate = _require_positive("seconds_per_sizing", seconds_per_sizing)
    for chosen in ((), SEARCH_FALLBACKS[:1], SEARCH_FALLBACKS):
        if planned_sizings(ranges, chosen) * rate <= budget_s:
            return tuple(chosen)
    raise SearchBudgetExceeded(
        f"{planned_sizings(ranges, SEARCH_FALLBACKS)} sizings at {rate:.3g} s exceed "
        f"{budget_s} s even with both fallbacks: put the wall-time budget to the user (source "
        "note 9.3, fallback 3)"
    )


@dataclass(frozen=True)
class SearchSet:
    """One frozen set (``screened_search``): name (SEARCH_SET_NAMES); values, (path, value)
    pairs in the file's order (the physics sets every physics coefficient, the outer sets
    every coefficient and the case fields); searches, the searches behind it; polish,
    (search, Polish) per search that chose its values (D-SP7-38); extremality, (search,
    ExtremalityCheck) per check, recorded and not acted on."""

    name: str
    values: tuple[tuple[str, CoefficientValue | None], ...]
    searches: str
    polish: tuple[tuple[str, Polish], ...]
    extremality: tuple[tuple[str, ExtremalityCheck], ...]

    def as_dict(self) -> dict[str, CoefficientValue | None]:
        """The values as a dict."""
        return dict(self.values)

    def coefficient_values(self) -> dict[str, CoefficientValue]:
        """The coefficient values only (the case fields left out)."""
        return {
            k: v
            for k, v in self.values
            if k not in (CASE_MARGIN, CASE_ENVELOPE_CAP) and v is not None
        }

    def case_fields(self) -> dict[str, float | None]:
        """The case fields (margin, envelope_cap_g) an outer set records ({} otherwise)."""
        out: dict[str, float | None] = {}
        for k, v in self.values:
            if k in (CASE_MARGIN, CASE_ENVELOPE_CAP):
                out[k] = None if v is None else float(v)
        return out


@dataclass(frozen=True)
class ScreenedSearch:
    """Searches A to C of source note 9.3 (``screened_search``): physics (A), stage2 (B),
    outer (C); sets, the four SearchSets; label (SEARCH_LABEL); fallbacks used; seed;
    evaluations, the distinct sizings of A to C."""

    physics: BandSearch
    stage2: Stage2Search
    outer: OuterSearch
    sets: tuple[SearchSet, ...]
    label: str
    fallbacks: tuple[str, ...]
    seed: int
    evaluations: int

    def set(self, name: str) -> SearchSet:
        """The SearchSet called name (KeyError if absent)."""
        for item in self.sets:
            if item.name == name:
                return item
        raise KeyError(name)


def screened_search(
    evaluator: SearchEvaluator,
    *,
    headline: SizingCase,
    step: SizingCase,
    fallbacks: Sequence[str] = (),
    seed: int = SEARCH_SEED,
) -> ScreenedSearch:
    """The screened search of design 4.2.6 and source note 9.3, searches A to C (the four
    frozen sets; D, the break-even values, is ``break_even_search``).

    Inputs: evaluator (the SizingFn of the flown pad and the push); headline, the
    headline push's SizingCase (rise_time, aft_ring, margin 0, no cap); step, the step row
    (dynamic "step"); fallbacks, those of SEARCH_FALLBACKS in use (``choose_fallbacks``);
    seed, the extremality samples' (each search adds its SEED_OFFSET).
    Output: a ScreenedSearch: A (``band_search`` at the design axes' central, both
    directions, SAMPLES_PHYSICS samples), B (``stage2_search`` at the step row,
    SAMPLES_STAGE2_PER_SET per set), C (``outer_search``, SAMPLES_CORNER per corner);
    fallback 1 puts every grid on GRID_POINTS_FALLBACK, fallback 2 halves the samples. The
    physics sets carry every physics coefficient (the stage-2-only five from B), the outer
    sets every coefficient with the corner's margin and cap. Labelled SEARCH_LABEL.
    Frame: none.
    """
    _check_fallbacks(fallbacks)
    grid = GRID_POINTS_FALLBACK if FALLBACK_GRID_TWO_POINTS in fallbacks else GRID_POINTS
    half = 2 if FALLBACK_SAMPLES_HALVED in fallbacks else 1
    start = evaluator.count
    a = band_search(
        evaluator,
        {},
        headline,
        DIRECTIONS,
        samples=SAMPLES_PHYSICS // half,
        seed=seed + SEED_OFFSET_A,
        grid_points=grid,
    )
    a_sets = {d: a.set(d).as_dict() for d in DIRECTIONS}
    b = stage2_search(
        evaluator,
        a_sets,
        step,
        samples_per_set=SAMPLES_STAGE2_PER_SET // half,
        seeds={LOW_MASS: seed + SEED_OFFSET_B_LOW, HIGH_MASS: seed + SEED_OFFSET_B_HIGH},
        grid_points=grid,
    )
    physics_paths = [r.path for r in evaluator.ranges if r.group == GROUP_PHYSICS]
    physics: dict[str, dict[str, CoefficientValue]] = {}
    for direction in DIRECTIONS:
        merged = {**a_sets[direction], **b.set(direction).as_dict()}
        physics[direction] = {p: merged[p] for p in physics_paths}
    c = outer_search(
        evaluator,
        physics,
        headline,
        samples=SAMPLES_CORNER // half,
        seeds={LOW_MASS: seed + SEED_OFFSET_C_LOW, HIGH_MASS: seed + SEED_OFFSET_C_HIGH},
        grid_points=grid,
    )
    names = {
        LOW_MASS: (SET_PHYSICS_LOW, SET_OUTER_LOW),
        HIGH_MASS: (SET_PHYSICS_HIGH, SET_OUTER_HIGH),
    }
    sets = []
    for direction in DIRECTIONS:
        phys_name, outer_name = names[direction]
        sets.append(
            SearchSet(
                name=phys_name,
                values=tuple(physics[direction].items()),
                searches="A (headline), B (step row)",
                polish=(("A", a.set(direction).polish), ("B", b.set(direction).polish)),
                extremality=(
                    *(("A", check) for check in a.set(direction).checks),
                    *(("B", check) for check in b.set(direction).checks),
                ),
            )
        )
        corner_search = c.corner(direction)
        corner = corner_search.set(direction)
        searches = "C (headline, design corner)"
        if not corner_search.stage2_sized:
            searches += (
                f"; the stage-2-only five from B via {phys_name}, not searched or checked at"
                " the corner (it does not size stage 2)"
            )
        sets.append(
            SearchSet(
                name=outer_name,
                values=tuple(c.set_values(direction).items()),
                searches=searches,
                polish=(("C", corner.polish),),
                extremality=tuple(("C", check) for check in corner.checks),
            )
        )
    ordered = tuple(sorted(sets, key=lambda s: SEARCH_SET_NAMES.index(s.name)))
    return ScreenedSearch(
        physics=a,
        stage2=b,
        outer=c,
        sets=ordered,
        label=SEARCH_LABEL,
        fallbacks=tuple(fallbacks),
        seed=seed,
        evaluations=evaluator.count - start,
    )


# ======================================================================== S2: the placement


@dataclass(frozen=True)
class PenaltyCurve:
    """A recorded offload against added stage-1 dry mass (SP1's penalty rows): dm_kg,
    ascending from 0 [kg]; x_kg, the solved offload at each [kg] (descending); source.
    Interpolated linearly; beyond the last point extrapolated along the last segment
    (marked); an offload <= 0 means no offload (survey 08 section 8). SP1's recorded curve
    is concave (its segment slopes steepen, -4.489, -4.705 and -5.096 kg/kg), so between
    its points a chord places x low (against the assist) and beyond the last point the
    extended chord places x high (for the assist): a level on the extrapolated segment,
    such as the 0% break-even target, is an assist-favouring estimate."""

    dm_kg: tuple[float, ...]
    x_kg: tuple[float, ...]
    source: str

    def __post_init__(self) -> None:
        """Refuse a curve that is not ascending in dm from 0 and descending in x."""
        if len(self.dm_kg) != len(self.x_kg) or len(self.dm_kg) < 2:
            raise ValueError("a penalty curve needs two or more (dm, x) points")
        if self.dm_kg[0] != 0.0:
            raise ValueError("a penalty curve starts at dm = 0 (the uncharged offload)")
        if any(b <= a for a, b in itertools.pairwise(self.dm_kg)):
            raise ValueError("the curve's dm must be strictly ascending")
        if any(b >= a for a, b in itertools.pairwise(self.x_kg)):
            raise ValueError("the curve's offload must be strictly descending")

    @property
    def uncharged_kg(self) -> float:
        """The offload at dm = 0 [kg] (the headline the levels are fractions of)."""
        return self.x_kg[0]

    def _last_slope(self) -> float:
        """dx/ddm of the last segment [kg/kg] (< 0)."""
        return (self.x_kg[-1] - self.x_kg[-2]) / (self.dm_kg[-1] - self.dm_kg[-2])

    def x_at(self, dm_kg: float) -> float:
        """The offload [kg] at a stage-1 dry-mass increment dm_kg [kg] >= 0 (may be <= 0
        beyond the curve: no offload)."""
        dm = _require_non_negative("dm_kg", dm_kg)
        if dm <= self.dm_kg[-1]:
            return float(np.interp(dm, self.dm_kg, self.x_kg))
        return self.x_kg[-1] + self._last_slope() * (dm - self.dm_kg[-1])

    def dm_at(self, x_kg: float) -> float:
        """The stage-1 dry-mass increment [kg] at which the offload is x_kg [kg] (<= the
        uncharged offload; below the last point along the last segment)."""
        x = _require_finite("x_kg", x_kg)
        if x > self.x_kg[0]:
            raise ValueError(f"x_kg {x!r} is above the uncharged offload {self.x_kg[0]!r}")
        if x >= self.x_kg[-1]:
            return float(np.interp(x, self.x_kg[::-1], self.dm_kg[::-1]))
        return self.dm_kg[-1] + (x - self.x_kg[-1]) / self._last_slope()

    def extrapolated(self, dm_kg: float) -> bool:
        """Whether dm_kg [kg] lies beyond the curve's last point."""
        return dm_kg > self.dm_kg[-1]


SP1_PENALTY_CURVE = PenaltyCurve(
    dm_kg=SP1_PENALTY_DRY_MASS_KG,
    x_kg=SP1_PENALTY_OFFLOAD_KG,
    source=(
        "SP1's silo_cold_s1 and its +2, +4 and +8.1 t stage-1 dry-mass rows, "
        "results/silo_offload_2d/20261003T112934Z/metrics.json (constants.py)"
    ),
)
"""The gate's penalty curve the coupled placement uses (survey 08 section 8; design 4.10)."""

STAGE2_DM_WEIGHT: float = OFFLOAD_PER_KG_STAGE2_DRY / OFFLOAD_PER_KG_STAGE1_DRY
"""A kg of stage-2 increment in kg of stage-1 dry mass of equal offload cost [-] (about
5.5; the coupled placement only, an estimate: constants.OFFLOAD_PER_KG_STAGE2_DRY over
OFFLOAD_PER_KG_STAGE1_DRY)."""


@dataclass(frozen=True)
class Placement:
    """A coupled placement (``coupled_placement``): x_kg, the estimated offload [kg] (0: no
    offload); fraction, x over the curve's uncharged offload; dm_kg, the equivalent stage-1
    increment placed at x [kg] (dm1 + w dm2, times dm_scale); dm_stage1_kg and dm_stage2_kg
    at x [kg]; iterations; converged; extrapolated (the placed dm beyond the curve's last
    point); no_offload."""

    x_kg: float
    fraction: float
    dm_kg: float
    dm_stage1_kg: float
    dm_stage2_kg: float
    iterations: int
    converged: bool
    extrapolated: bool
    no_offload: bool


def coupled_placement(
    summary_at: Callable[[float], SizingSummary],
    curve: PenaltyCurve,
    *,
    stage2_weight: float,
    dm_scale: float = 1.0,
    tol_kg: float = PLACEMENT_TOL_KG,
    max_iterations: int = PLACEMENT_MAX_ITERATIONS,
) -> Placement:
    """The coupled placement of a sizing-only dm on a penalty curve (survey 08 section 8;
    design 4.10): the fixed point x = max(0, X(s (dm1(x) + w dm2(x)))), dm re-evaluated at
    the offload it gives, iterated from the uncharged offload until two iterates agree to
    tol_kg [kg].

    Inputs: summary_at, x [kg] -> the SizingSummary of the push at that stage-1 offload;
    curve; stage2_weight w [-], a kg of stage-2 increment in kg of stage-1 dry mass of
    equal offload cost (an estimate); dm_scale s [-] (the plausibility rule's widening of a
    band end; 1 otherwise); tol_kg; max_iterations.
    Output: a Placement (an estimate, never a solved offload: no trajectory is flown).
    Frame: none.
    """
    w = _require_non_negative("stage2_weight", stage2_weight)
    scale = _require_positive("dm_scale", dm_scale)
    x = curve.uncharged_kg
    for k in range(1, max_iterations + 1):
        s = summary_at(x)
        dm = scale * (s.dm_stage1_kg + w * s.dm_stage2_kg)
        x_new = max(0.0, curve.x_at(dm))
        done = abs(x_new - x) <= tol_kg
        if done or k == max_iterations:
            return Placement(
                x_kg=x_new,
                fraction=x_new / curve.uncharged_kg,
                dm_kg=dm,
                dm_stage1_kg=s.dm_stage1_kg,
                dm_stage2_kg=s.dm_stage2_kg,
                iterations=k,
                converged=done,
                extrapolated=curve.extrapolated(dm),
                no_offload=x_new <= 0.0,
            )
        x = x_new
    raise AssertionError("unreachable")


@dataclass(frozen=True)
class BreakEven:
    """One design axis's break-even value at one level (``break_even_search``; source note
    9.3 D): path; level (a fraction of the uncharged offload); x_target_kg and
    dm_target_kg, the offload and the equivalent stage-1 increment that place there [kg]
    (target_extrapolated: on the curve's extrapolated segment, an assist-favouring
    estimate, PenaltyCurve); method ("linear",
    "bracketed" or "integer"); entry; value, the axis value whose coupled x* is the target
    (None when not reached, and for the integer axis); bracket, the integer axis's two
    adjacent whole counts with x* below the level at the first and above it at the second;
    status (BREAK_EVEN_STATUSES); dm_at_ends_kg, the equivalent dm at x_target at the
    axis's two range ends (the integer axis: its fewest and most counts); evaluations."""

    path: str
    level: float
    x_target_kg: float
    dm_target_kg: float
    target_extrapolated: bool
    method: str
    entry: str
    value: float | None
    bracket: tuple[int, int] | None
    status: str
    dm_at_ends_kg: tuple[float, float]
    evaluations: int


def _equivalent(s: SizingSummary, w: float) -> float:
    """dm1 + w dm2 [kg]."""
    return s.dm_stage1_kg + w * s.dm_stage2_kg


@dataclass(frozen=True)
class _Target:
    """One break-even level: frac, x_t and dm_t [kg] and whether dm_t is extrapolated."""

    frac: float
    x_t: float
    dm_t: float
    extrapolated: bool


def _break_even_row(
    target: _Target,
    path: str,
    method: str,
    entry: str,
    value: float | None,
    bracket: tuple[int, int] | None,
    status: str,
    ends: tuple[float, float],
    evaluations: int,
) -> BreakEven:
    """A BreakEven at a target."""
    return BreakEven(
        path=path,
        level=target.frac,
        x_target_kg=target.x_t,
        dm_target_kg=target.dm_t,
        target_extrapolated=target.extrapolated,
        method=method,
        entry=entry,
        value=value,
        bracket=bracket,
        status=status,
        dm_at_ends_kg=ends,
        evaluations=evaluations,
    )


def _linear_break_even(
    evaluator: SearchEvaluator, path: str, case: SizingCase, target: _Target, w: float
) -> BreakEven:
    """A linear axis's closed-form root from the equivalent dm at its range's two ends: in
    range, outside it (reported with its value) when at or above the axis's physical floor
    (LINEAR_AXIS_FLOORS), else not reached (value None; below or above the level by the
    side the range's dm lies on, as for a bracketed axis)."""
    start = evaluator.count
    item = evaluator.coefficient(path)
    assert item.low is not None and item.high is not None
    entry = ENTRY_THRUST_STRUCTURE if path == PATH_K_TS else case.entry
    at = replace(case, offload_kg=target.x_t, entry=entry)
    lo, hi = float(item.low), float(item.high)
    d_lo = _equivalent(evaluator.summary({path: item.low}, at), w)
    d_hi = _equivalent(evaluator.summary({path: item.high}, at), w)
    ends = (d_lo, d_hi)
    if abs(d_hi - d_lo) <= MONOTONE_TOL_KG:
        status = BE_ABOVE_THROUGHOUT if d_lo < target.dm_t else BE_BELOW_THROUGHOUT
        return _break_even_row(
            target, path, "linear", entry, None, None, status, ends, evaluator.count - start
        )
    root = lo + (target.dm_t - d_lo) * (hi - lo) / (d_hi - d_lo)
    value: float | None = root
    if root < LINEAR_AXIS_FLOORS[path]:
        value = None
        status = BE_BELOW_THROUGHOUT if d_lo > target.dm_t else BE_ABOVE_THROUGHOUT
    else:
        status = BE_IN_RANGE if lo <= root <= hi else BE_OUTSIDE_RANGE
    return _break_even_row(
        target, path, "linear", entry, value, None, status, ends, evaluator.count - start
    )


def _bracketed_break_even(
    evaluator: SearchEvaluator, path: str, case: SizingCase, target: _Target, w: float
) -> BreakEven:
    """A nonlinear axis's root by brentq on its range, or not reached."""
    start = evaluator.count
    item = evaluator.coefficient(path)
    assert item.low is not None and item.high is not None
    at = replace(case, offload_kg=target.x_t)
    lo, hi = float(item.low), float(item.high)

    def gap(v: float) -> float:
        return _equivalent(evaluator.summary({path: v}, at), w) - target.dm_t

    g_lo, g_hi = gap(lo), gap(hi)
    ends = (g_lo + target.dm_t, g_hi + target.dm_t)
    value: float | None = None
    if g_lo == 0.0 or g_hi == 0.0:
        value, status = (lo if g_lo == 0.0 else hi), BE_IN_RANGE
    elif (g_lo > 0.0) != (g_hi > 0.0):
        value = float(brentq(gap, lo, hi, xtol=BREAK_EVEN_XTOL_REL * (hi - lo)))
        status = BE_IN_RANGE
    else:
        status = BE_ABOVE_THROUGHOUT if g_lo < 0.0 else BE_BELOW_THROUGHOUT
    return _break_even_row(
        target, path, "bracketed", at.entry, value, None, status, ends, evaluator.count - start
    )


def _integer_break_even(
    evaluator: SearchEvaluator, case: SizingCase, target: _Target, w: float
) -> BreakEven:
    """The pad count's bracket of adjacent whole counts, or not reached."""
    start = evaluator.count
    at = replace(case, offload_kg=target.x_t, check_ranges=False)
    gaps: dict[int, float] = {}

    def gap(n: int) -> float:
        if n not in gaps:
            s = evaluator.summary({PATH_RING_PADS: n}, at)
            gaps[n] = _equivalent(s, w) - target.dm_t
        return gaps[n]

    counts = sorted({RING_PADS_MIN, *RING_PAD_ROW_COUNTS})
    for n in counts:
        gap(n)
    bracket = None
    for a, b in itertools.pairwise(counts):
        if gap(a) >= 0.0 > gap(b):
            lo_n, hi_n = a, b
            while hi_n - lo_n > 1:
                mid = (lo_n + hi_n) // 2
                if gap(mid) >= 0.0:
                    lo_n = mid
                else:
                    hi_n = mid
            bracket = (lo_n, hi_n)
            break
    ends = (gap(counts[0]) + target.dm_t, gap(counts[-1]) + target.dm_t)
    if bracket is not None:
        status = BE_IN_RANGE
    elif gap(counts[0]) < 0.0:
        status = BE_ABOVE_THROUGHOUT
    else:
        status = BE_BELOW_THROUGHOUT
    return _break_even_row(
        target,
        PATH_RING_PADS,
        "integer",
        at.entry,
        None,
        bracket,
        status,
        ends,
        evaluator.count - start,
    )


def break_even_search(
    evaluator: SearchEvaluator,
    curve: PenaltyCurve,
    *,
    case: SizingCase,
    stage2_weight: float,
    levels: Sequence[float] = BREAK_EVEN_LEVELS,
) -> tuple[BreakEven, ...]:
    """Search D (source note 9.3 D): where each design axis puts the coupled-placement x* at
    each level (50% and 0% of the uncharged offload), the other coefficients at central.

    Because the coupled fixed point is unique (its map rises with x by about 1/20 kg per
    kg), x* equals x_t exactly when the equivalent dm of the push at x_t equals X^-1(x_t),
    so each root is sought at the target offload. Inputs: evaluator; curve; case, the
    headline's (its offload replaced by the target); stage2_weight; levels.
    Output: one BreakEven per axis and level. The four factors and k_ts (k_ts through the
    thrust-structure entry, its own row) are linear: two sizings at the range's ends give
    the root in closed form (reported also when outside the range, unless it lies below the
    axis's physical floor, LINEAR_AXIS_FLOORS: then not reached, value None). The rise time
    and the frequency: brentq on the range (BREAK_EVEN_XTOL_REL of its width) when the
    target lies between the ends' dm, else not reached. The pad count: RING_PADS_MIN and
    RING_PAD_ROW_COUNTS, then the whole counts between the two that bracket the level,
    reported as the adjacent pair; not reached when x* stays above the level at the
    fewest pads or falls below it at the most (that would need more pads, outside the
    axis). Frame: none.
    """
    w = _require_non_negative("stage2_weight", stage2_weight)
    out = []
    for level in levels:
        frac = _require_fraction("level", level)
        x_t = frac * curve.uncharged_kg
        dm_t = curve.dm_at(x_t)
        target = _Target(frac, x_t, dm_t, curve.extrapolated(dm_t))
        out += [_linear_break_even(evaluator, p, case, target, w) for p in LINEAR_AXIS_PATHS]
        out += [_bracketed_break_even(evaluator, p, case, target, w) for p in BRACKETED_AXIS_PATHS]
        out.append(_integer_break_even(evaluator, case, target, w))
    return tuple(out)
