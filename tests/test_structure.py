"""The structural sizing primitives of the push load (docs/physics.md, "Structural sizing
of the push load (first order)"; SP7 step S1, design docs/phases/inputs/
2026-10-08-SP7-design.md section 4.2).

Every expected value is computed in the test from the closed form written out here, from
typed-out arithmetic, or from an independent method (a bisection or numpy's interp in the
test), never from structure.py's own helpers. Closed forms are asserted at 1e-12 relative
(REL); CLAUDE.md sets no bound for these primitives. The closed forms:

- hydrostatic pressure p = p_u + rho n g0 max(h, 0);
- hoop t = (FS p - p_relief) r / (F_tu eta) (and the transfer tube's wall), the relief
  unfactored (NASA-STD-5001B FSR 19), 0 when that is <= 0;
- the SP-8007 knockdown gamma = 1 - 0.901 (1 - exp(-sqrt(r/t)/16)) (0.3217 at r/t = 500,
  survey 06/08);
- Delta_gamma: piecewise-linear in x = (p/E)(r/t)^2, exact at the points, constant beyond
  the last, compared with numpy's interp;
- monocoque: the root t of 2 pi E t^2 (gamma/sqrt(3 (1 - nu^2)) + s Delta_gamma) = N,
  against the test's own bisection; plugging t back gives N within 1e-9 relative (the
  root is solved to 1e-12 m), N lies between the left side at t -/+ 2e-12 m, and the left
  side is strictly increasing on the stated bracket (its ends widened by 1e-6 relative),
  at whose ends it is below and above N; loads down to 1e-9 N solve without the pressure
  credit, where the unwidened bracket's sign change is lost to rounding;
- Gerard t = (d/4) C (N/(2 pi r) / (k_s E d))^n per Table 2 row; plate-limited t_ref N/N_ref;
- von Mises t = sqrt(A^2 - A B + B^2)/(F_tu eta), A = FS max(p, 0) r, B = -N_d/(2 pi r),
  with its two limits (B = 0: hoop; A = 0: |B|/(F_tu eta)) and a net external pressure
  clamped to A = 0;
- dome crown t = (FS p - p_relief) r (a/b)/2 / (F_tu eta) for a/b in [1, sqrt(2)]; the
  half oblate spheroid's area pi a^2 + (pi b^2/(2 e)) ln((1 + e)/(1 - e)), 2 pi a^2 for a
  hemisphere;
- the ring frame M = q r^2 (1 - alpha cot alpha), alpha = pi/N_p (the closed ring's moment
  at the pads, also checked against a quadrature of the half span's equilibrium, and
  tending to q l^2/12), Z = FS f_fit M / F_tu, b = (6 Z / k^2)^(1/3), m = 2 pi r rho k b^2;
- DLF min(2, 1 + T/(pi t_r)) (2 at t_r = 0), 1 and 2; peak n_0 + DLF (n_q - n_0);
- the ramped plateau a' = [L - sqrt(L^2 - v_e^2 t_r^2/12)]/(t_r^2/12) checked by the
  ramp's own kinematics; v_e^2/(2 L) at t_r = 0;
- increments NOF sum 2 pi r rho dz max(0, t_push - t_env) and NOF A rho max(0, ...): zero
  inside the envelope, positive parts only;
- monotone: hoop thickness of the hydrostatic pressure non-decreasing in n and in depth
  (the propellant above the station); the monocoque thickness in N.

One test times each primitive group (time.perf_counter around a loop) and records the
per-evaluation times in the test's user_properties (nothing printed; a junit XML written
with junit_family=legacy carries them); its ceilings are generous, so it fails only on a
gross slow-down.
"""

from __future__ import annotations

import ast
import itertools
import math
import time
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from launchsim import structure as st
from launchsim.constants import G0_MPS2

REL = 1e-12
"""Relative tolerance of the closed forms."""
INVERSE_REL = 1e-9
"""Relative tolerance of N_cr(t) = N at the solved monocoque thickness (xtol 1e-12 m)."""
XTOL_M = 1e-12
"""The design's monocoque root tolerance [m] (design 4.2: brentq to 1e-12 m)."""
BRACKET_MARGIN = 1e-6
"""The relative widening of the monocoque bracket's ends (structure.py states it)."""

# 2195-T8R78-like inputs of the survey (06: E 75.8 GPa, nu 0.33, F_tu 558 MPa, rho 2713;
# friction-stir welds at 70%; FS 1.4) and the gate vehicle's radius (3.66 m diameter).
E_PA = 75.8e9
NU = 0.33
F_TU_PA = 558.0e6
ETA_W = 0.7
FS = 1.4
RHO_W = 2713.0
R_M = 1.83
RHO_LOX = 1141.0

DG_TABLE: tuple[tuple[float, float], ...] = (
    (0.0, 0.0),
    (0.015, 0.023),
    (0.02, 0.028),
    (0.04, 0.046),
    (0.06, 0.060),
    (0.08, 0.075),
    (0.1, 0.09),
    (0.2, 0.13),
    (0.4, 0.17),
    (0.6, 0.20),
    (1.0, 0.22),
    (2.0, 0.245),
    (4.0, 0.25),
    (10.0, 0.25),
)
"""Survey 06's reading of SP-8007 Fig. 6 / Fig. 4-5 (about +/-10%), prefixed with (0, 0): a
test input only (S2's structure file holds the digitization S0 adopts)."""
SMALL_TABLE: tuple[tuple[float, float], ...] = (
    (0.0, 0.0),
    (0.02, 0.028),
    (0.1, 0.09),
    (1.0, 0.22),
    (4.0, 0.25),
)
"""A short hand table for the interpolation checks."""


def _gamma(r_over_t: float) -> float:
    """SP-8007 1968 Eq. 5 written out: 1 - 0.901 (1 - exp(-sqrt(r/t)/16))."""
    return 1.0 - 0.901 * (1.0 - math.exp(-math.sqrt(r_over_t) / 16.0))


def _n_cr(t: float, r: float, p: float, s: float, table: Any = DG_TABLE) -> float:
    """The monocoque buckling load written out in the test (numpy interp for Delta_gamma,
    constant beyond the last point as np.interp's right default)."""
    xs = [pt[0] for pt in table]
    ys = [pt[1] for pt in table]
    x = (p / E_PA) * (r / t) ** 2
    dg = float(np.interp(x, xs, ys))
    k3 = math.sqrt(3.0 * (1.0 - NU**2))
    return 2.0 * math.pi * E_PA * t**2 * (_gamma(r / t) / k3 + s * dg)


def _bisect_t(n: float, r: float, p: float, s: float) -> float:
    """The test's own root of _n_cr(t) = n by bisection on [1e-6, 1] m to 1e-16 m."""
    lo, hi = 1e-6, 1.0
    assert _n_cr(lo, r, p, s) < n < _n_cr(hi, r, p, s)
    while hi - lo > 1e-16:
        mid = 0.5 * (lo + hi)
        if mid in (lo, hi):
            break
        if _n_cr(mid, r, p, s) < n:
            lo = mid
        else:
            hi = mid
    return hi


# ------------------------------------------------------------------ constants and module


def test_published_constants_and_rows() -> None:
    """The SP-8007 constants (constants.py) and the four Gerard Table 2 rows as published;
    the brentq tolerances (xtol 1e-12 m; rtol scipy's default, four machine epsilons), the
    bracket margin, the DLF values and the domain bounds as the design and the module
    state them."""
    from launchsim.constants import SP8007_KNOCKDOWN_A, SP8007_PHI_DIVISOR

    assert SP8007_KNOCKDOWN_A == 0.901
    assert SP8007_PHI_DIVISOR == 16.0
    rows = {(row.name, row.c, row.exponent) for row in st.GERARD_ROWS}
    assert rows == {
        ("ring_common_z", 6.48, 3.0 / 5.0),
        ("ring_common_y", 5.93, 3.0 / 5.0),
        ("ring_improved_z", 7.14, 7.0 / 11.0),
        ("ring_improved_y", 6.01, 7.0 / 11.0),
    }
    assert st.MONOCOQUE_XTOL_M == XTOL_M
    assert st.MONOCOQUE_RTOL == 4.0 * float(np.finfo(float).eps)
    assert st.MONOCOQUE_BRACKET_MARGIN == BRACKET_MARGIN
    assert st.DLF_QUASI_STATIC == 1.0 and st.DLF_STEP == 2.0
    assert st.DOME_AXIS_RATIO_MAX == math.sqrt(2.0)
    assert st.POISSON_RATIO_MAX == 0.5
    assert st.RING_PADS_MIN == 3
    for bad in ((0.0, 0.6), (-1.0, 0.6), (6.0, 0.0), (6.0, 1.5), (math.nan, 0.6)):
        with pytest.raises(ValueError):
            st.GerardRow("bad", *bad)


def test_structure_imports_no_io_module() -> None:
    """structure.py is pure: it imports only the standard library (math, operator, bisect,
    collections, dataclasses, typing, and itertools for S2's search), numpy, scipy.optimize,
    and launchsim's constants and units (never sim, results_io, plots, run_data, replay,
    scene, app or config)."""
    path = Path(st.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add(str(node.module))
        elif isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
    package = {m for m in imported if m.startswith("launchsim")}
    assert package == {"launchsim.constants", "launchsim.units"}, package
    third_party = {m.split(".")[0] for m in imported} - {
        "__future__",
        "math",
        "operator",
        "bisect",
        "collections",
        "dataclasses",
        "typing",
        "itertools",
        "launchsim",
    }
    assert third_party == {"numpy", "scipy"}, third_party
    assert {m for m in imported if m.startswith("scipy")} == {"scipy.optimize"}
    calls = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    calls |= {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert not ({"open", "print", "read_text", "write_text"} & calls)


# ------------------------------------------------------------------ pressure and hoop


def test_hydrostatic_pressure_against_hand_values() -> None:
    """p = p_u + rho n g0 max(h, 0): a LOX column 20 m deep at 3.996 g0 under 3 bar; the
    ullage pressure alone above the surface; a negative n (a release swing) lowers it."""
    got = st.hydrostatic_pressure_pa(3.0e5, RHO_LOX, 3.996, 20.0)
    assert math.isclose(got, 3.0e5 + 1141.0 * 3.996 * G0_MPS2 * 20.0, rel_tol=REL)
    assert st.hydrostatic_pressure_pa(3.0e5, RHO_LOX, 3.996, -1.0) == 3.0e5
    assert st.hydrostatic_pressure_pa(3.0e5, RHO_LOX, 3.996, 0.0) == 3.0e5
    low = st.hydrostatic_pressure_pa(1.0e5, RHO_LOX, -4.0, 30.0)
    assert math.isclose(low, 1.0e5 - 1141.0 * 4.0 * G0_MPS2 * 30.0, rel_tol=REL)
    assert low < 0.0  # the column would separate: the caller's flag
    for bad in ((math.nan, RHO_LOX, 1.0, 1.0), (1.0, -1.0, 1.0, 1.0), (1.0, 1.0, math.inf, 1.0)):
        with pytest.raises(ValueError):
            st.hydrostatic_pressure_pa(*bad)


def test_hoop_thickness_against_hand_values() -> None:
    """t = FS p r / (F_tu eta): 1 MPa in the 1.83 m barrel at FS 1.4, 558 MPa, eta 0.7 is
    6.5591 mm; no hoop tension (p <= 0) gives 0; the tube's wall is the same closed form
    with its own radius and its inside pressure (from ambient), and a relieving outside
    pressure is subtracted once, unfactored: t = (FS p - p_relief) r / (F_tu eta), 0 when
    it exceeds FS p; refusals (a negative relief among them)."""
    got = st.hoop_thickness_m(1.0e6, R_M, FS, F_TU_PA, ETA_W)
    expected = 1.4 * 1.0e6 * 1.83 / (558.0e6 * 0.7)
    assert math.isclose(got, expected, rel_tol=REL)
    assert round(got * 1000.0, 4) == 6.5591  # hand number, a cross-check only
    assert st.hoop_thickness_m(0.0, R_M, FS, F_TU_PA, ETA_W) == 0.0
    assert st.hoop_thickness_m(-2.0e5, R_M, FS, F_TU_PA, ETA_W) == 0.0
    tube = st.tube_hoop_thickness_m(1.2e6, 0.25, 1.4, 558.0e6, 1.0)
    assert math.isclose(tube, 1.4 * 1.2e6 * 0.25 / 558.0e6, rel_tol=REL)
    assert st.tube_hoop_thickness_m(-1.0, 0.25, 1.4, 558.0e6, 1.0) == 0.0
    relieved = st.tube_hoop_thickness_m(2.0e6, 0.25, 1.4, 558.0e6, 1.0, p_relief_pa=3.0e5)
    assert math.isclose(relieved, (1.4 * 2.0e6 - 3.0e5) * 0.25 / 558.0e6, rel_tol=REL)
    barrel = st.hoop_thickness_m(1.0e6, R_M, FS, F_TU_PA, ETA_W, p_relief_pa=2.0e5)
    assert math.isclose(barrel, (1.4 * 1.0e6 - 2.0e5) * 1.83 / (558.0e6 * 0.7), rel_tol=REL)
    assert st.hoop_thickness_m(1.0e5, R_M, FS, F_TU_PA, ETA_W, p_relief_pa=1.4e5) == 0.0
    assert st.hoop_thickness_m(1.0e5, R_M, FS, F_TU_PA, ETA_W, p_relief_pa=2.0e5) == 0.0
    with pytest.raises(ValueError):
        st.hoop_thickness_m(1.0e6, R_M, FS, F_TU_PA, ETA_W, p_relief_pa=-1.0)
    bad_cases = (
        (1.0e6, 0.0, FS, F_TU_PA, ETA_W),
        (1.0e6, R_M, 0.0, F_TU_PA, ETA_W),
        (1.0e6, R_M, FS, 0.0, ETA_W),
        (1.0e6, R_M, FS, F_TU_PA, 0.0),
        (1.0e6, R_M, FS, F_TU_PA, 1.01),
        (math.nan, R_M, FS, F_TU_PA, ETA_W),
    )
    for bad in bad_cases:
        with pytest.raises(ValueError):
            st.hoop_thickness_m(*bad)


def test_hoop_of_the_head_is_monotone_in_n_and_in_depth() -> None:
    """The hoop thickness of p_u + rho n g0 h never falls as n or the depth (the propellant
    above the station) grows, and rises strictly for rho, h, n > 0."""
    ns = np.linspace(0.0, 7.0, 29)
    depths = np.linspace(0.0, 40.0, 41)
    grid = np.array(
        [
            [
                st.hoop_thickness_m(
                    st.hydrostatic_pressure_pa(2.5e5, RHO_LOX, float(n), float(h)),
                    R_M,
                    FS,
                    F_TU_PA,
                    ETA_W,
                )
                for h in depths
            ]
            for n in ns
        ]
    )
    assert np.all(np.diff(grid, axis=0) >= 0.0)
    assert np.all(np.diff(grid, axis=1) >= 0.0)
    assert np.all(np.diff(grid[1:, 1:], axis=0) > 0.0)
    assert np.all(np.diff(grid[1:, 1:], axis=1) > 0.0)


# ------------------------------------------------------------------ knockdown and Delta_gamma


def test_sp8007_knockdown_against_the_closed_form() -> None:
    """gamma at r/t = 500 is 0.3217 (surveys 06 and 08), computed here from the written-out
    formula; survey 06's table (200: 0.471, 300: 0.404, 400: 0.357, 1000: 0.224) to its
    three decimals; the limits 1 (thick) and 1 - 0.901 (thin); decreasing in r/t;
    refusals."""
    assert math.isclose(st.sp8007_knockdown(500.0), _gamma(500.0), rel_tol=REL)
    assert round(st.sp8007_knockdown(500.0), 4) == 0.3217
    for rt, quoted in ((200.0, 0.471), (300.0, 0.404), (400.0, 0.357), (1000.0, 0.224)):
        assert math.isclose(st.sp8007_knockdown(rt), _gamma(rt), rel_tol=REL)
        assert round(st.sp8007_knockdown(rt), 3) == quoted
    assert math.isclose(st.sp8007_knockdown(1e-12), 1.0, rel_tol=1e-6)
    assert math.isclose(st.sp8007_knockdown(1e12), 1.0 - 0.901, rel_tol=1e-9)
    values = [st.sp8007_knockdown(rt) for rt in np.geomspace(1.0, 1e5, 200)]
    assert np.all(np.diff(values) < 0.0)
    for bad in (0.0, -500.0, math.nan, math.inf):
        with pytest.raises(ValueError):
            st.sp8007_knockdown(bad)


def test_delta_gamma_interpolation() -> None:
    """Exact at the table's points, the mean at midpoints, constant beyond the last point,
    equal to numpy's interp on a dense grid, monotone; refusals of x < 0 and bad tables."""
    xs = [p[0] for p in SMALL_TABLE]
    ys = [p[1] for p in SMALL_TABLE]
    for x, y in SMALL_TABLE:
        assert st.delta_gamma(x, SMALL_TABLE) == y
    for (x0, y0), (x1, y1) in itertools.pairwise(SMALL_TABLE):
        mid = st.delta_gamma(0.5 * (x0 + x1), SMALL_TABLE)
        assert math.isclose(mid, 0.5 * (y0 + y1), rel_tol=REL)
    assert st.delta_gamma(4.5, SMALL_TABLE) == 0.25
    assert st.delta_gamma(1.0e9, SMALL_TABLE) == 0.25
    grid = np.linspace(0.0, 6.0, 2001)
    got = np.array([st.delta_gamma(float(x), SMALL_TABLE) for x in grid])
    np.testing.assert_allclose(got, np.interp(grid, xs, ys), rtol=REL, atol=1e-15)
    assert np.all(np.diff(got) >= 0.0)
    with pytest.raises(ValueError):
        st.delta_gamma(-1e-9, SMALL_TABLE)
    bad_tables: list[Any] = [
        ((0.0, 0.0),),  # one point
        ((0.01, 0.0), (1.0, 0.2)),  # does not start at (0, 0)
        ((0.0, 0.01), (1.0, 0.2)),
        ((0.0, 0.0), (1.0, 0.2), (1.0, 0.3)),  # repeated x
        ((0.0, 0.0), (1.0, 0.2), (0.5, 0.3)),  # descending x
        ((0.0, 0.0), (1.0, 0.2), (2.0, 0.1)),  # decreasing value
        ((0.0, 0.0), (1.0, math.nan)),
        ((0.0, 0.0), (1.0, 0.2, 0.3)),  # not a pair
    ]
    for table in bad_tables:
        with pytest.raises(ValueError):
            st.delta_gamma(0.5, table)


# ------------------------------------------------------------------ monocoque


MONOCOQUE_CASES = (
    (1.0e7, R_M, 0.0, 0.0),
    (1.0e7, R_M, 2.0e5, 1.0),
    (2.5e7, R_M, 3.0e5, 1.0),
    (3.0e6, R_M, 1.0e5, 1.0),
    (6.0e7, 1.2, 4.0e5, 1.0),
    (1.0e7, R_M, 2.0e5, 0.0),
)
"""(N_d [N], r [m], p_min [Pa], s_dg): unpressurized, the F9-like barrel at 1-4 bar, a
smaller radius at a larger load, and the increment switched off."""


@pytest.mark.parametrize(("n", "r", "p", "s"), MONOCOQUE_CASES)
def test_monocoque_thickness_inverts_the_buckling_load(
    n: float, r: float, p: float, s: float
) -> None:
    """The solved t matches the test's own bisection to 2e-12 m; N_cr(t) = N within 1e-9
    relative; N lies between N_cr(t - 2e-12 m) and N_cr(t + 2e-12 m); the code's N_cr equals
    the written-out one."""
    t = st.monocoque_buckling_thickness_m(n, r, E_PA, NU, p, s, DG_TABLE)
    t_hand = _bisect_t(n, r, p, s)
    assert abs(t - t_hand) <= 2.0 * XTOL_M
    assert math.isclose(_n_cr(t, r, p, s), n, rel_tol=INVERSE_REL)
    assert _n_cr(t - 2.0 * XTOL_M, r, p, s) < n < _n_cr(t + 2.0 * XTOL_M, r, p, s)
    code = st.monocoque_buckling_load_N(t, r, E_PA, NU, p, s, DG_TABLE)
    assert math.isclose(code, _n_cr(t, r, p, s), rel_tol=REL)


def test_monocoque_hand_case() -> None:
    """The unpressurized 1.83 m barrel at N_d = 10 MN (E 75.8 GPa, nu 0.33): the fixed point
    t = sqrt(N sqrt(3 (1 - nu^2)) / (2 pi E gamma(r/t))), iterated in the test from 5 mm to
    convergence, is the solved t (about 8.6 mm); a 2 bar minimum pressure with the
    increment needs less wall, and with the increment off the same as unpressurized."""
    n = 1.0e7
    k3 = math.sqrt(3.0 * (1.0 - 0.33**2))
    t = 5.0e-3
    for _ in range(200):
        t = math.sqrt(n * k3 / (2.0 * math.pi * 75.8e9 * _gamma(1.83 / t)))
    got = st.monocoque_buckling_thickness_m(n, 1.83, 75.8e9, 0.33, 0.0, 0.0, DG_TABLE)
    assert abs(got - t) <= 2.0 * XTOL_M
    assert round(got * 1000.0, 1) == 8.6  # hand number, a cross-check only
    pressurized = st.monocoque_buckling_thickness_m(n, 1.83, 75.8e9, 0.33, 2.0e5, 1.0, DG_TABLE)
    assert pressurized < got
    switched_off = st.monocoque_buckling_thickness_m(n, 1.83, 75.8e9, 0.33, 2.0e5, 0.0, DG_TABLE)
    assert switched_off == got


@pytest.mark.parametrize(("n", "r", "p", "s"), MONOCOQUE_CASES)
def test_monocoque_load_is_increasing_on_the_bracket(
    n: float, r: float, p: float, s: float
) -> None:
    """On the stated bracket [t_lo, t_hi] (t_lo = (1 - 1e-6) sqrt(N / (2 pi E (1/k3 +
    s g_max))), t_hi = (1 + 1e-6) sqrt(N k3 / (2 pi E (1 - 0.901))), written out here) the
    written-out N_cr is below N at t_lo, above it at t_hi, and strictly increasing on 4001
    points, and so is the code's."""
    k3 = math.sqrt(3.0 * (1.0 - NU**2))
    t_lo = (1.0 - 1e-6) * math.sqrt(n / (2.0 * math.pi * E_PA * (1.0 / k3 + s * 0.25)))
    t_hi = (1.0 + 1e-6) * math.sqrt(n * k3 / (2.0 * math.pi * E_PA * (1.0 - 0.901)))
    lo, hi = st.monocoque_bracket_m(n, E_PA, NU, s, DG_TABLE)
    assert math.isclose(lo, t_lo, rel_tol=REL) and math.isclose(hi, t_hi, rel_tol=REL)
    assert _n_cr(t_lo, r, p, s) < n < _n_cr(t_hi, r, p, s)
    ts = np.linspace(t_lo, t_hi, 4001)
    hand = np.array([_n_cr(float(t), r, p, s) for t in ts])
    code = np.array(
        [st.monocoque_buckling_load_N(float(t), r, E_PA, NU, p, s, DG_TABLE) for t in ts]
    )
    assert np.all(np.diff(hand) > 0.0)
    assert np.all(np.diff(code) > 0.0)
    np.testing.assert_allclose(code, hand, rtol=REL)


TINY_LOAD_CASES = ((0.0, 0.0), (2.0e5, 0.0), (0.0, 1.0), (2.0e5, 1.0))
"""(p_min [Pa], s_dg): no pressure credit three ways (s_dg = 0, p = 0, both), and with it."""


@pytest.mark.parametrize(("p", "s"), TINY_LOAD_CASES)
def test_monocoque_solves_tiny_loads(p: float, s: float) -> None:
    """Loads far below any wall sized here still solve (review PHYS-S1-01): at r/t_hi above
    about 3.6e5 gamma rounds to exactly 1 - 0.901, and the unwidened bracket's N_cr(t_hi)
    equals N to rounding with either sign. At 0.01 N the solved t is finite and N_cr(t) = N
    to the root tolerance (xtol 1e-12 m on a t of about 0.6 um, so 1e-5 relative); on 200
    loads from 1e-9 N to 1e8 N every solve returns a t with N between the written-out
    N_cr(t -/+ 2e-12 m), and the written-out N_cr is below N at the code's t_lo and above
    it at its t_hi."""
    t = st.monocoque_buckling_thickness_m(0.01, R_M, E_PA, NU, p, s, DG_TABLE)
    assert math.isfinite(t) and t > 0.0
    assert math.isclose(_n_cr(t, R_M, p, s), 0.01, rel_tol=1e-5)
    for n in np.geomspace(1e-9, 1e8, 200):
        load = float(n)
        t = st.monocoque_buckling_thickness_m(load, R_M, E_PA, NU, p, s, DG_TABLE)
        assert t > 2.0 * XTOL_M
        assert _n_cr(t - 2.0 * XTOL_M, R_M, p, s) < load < _n_cr(t + 2.0 * XTOL_M, R_M, p, s)
        lo, hi = st.monocoque_bracket_m(load, E_PA, NU, s, DG_TABLE)
        assert _n_cr(lo, R_M, p, s) < load < _n_cr(hi, R_M, p, s)


def test_monocoque_wall_is_never_short() -> None:
    """Review PHYS2-01: the returned wall carries the load. On 720 solves (N_d 1e3-5e7 N,
    p_min 0-2 MPa, s_dg 0 and 1) the code's N_cr(t) >= N_d, and the written-out N_cr
    exceeds N_d by less than 2.6e-12 m / t relative (brentq's bound xtol + rtol t on
    t - t*, about 1e-12 m, times the log slope d ln N_cr / d ln t, at most 2.5534), plus
    1e-14 for rounding."""
    for s in (0.0, 1.0):
        for p in np.linspace(0.0, 2.0e6, 6):
            for n in np.geomspace(1.0e3, 5.0e7, 60):
                load, pressure = float(n), float(p)
                t = st.monocoque_buckling_thickness_m(load, R_M, E_PA, NU, pressure, s, DG_TABLE)
                code = st.monocoque_buckling_load_N(t, R_M, E_PA, NU, pressure, s, DG_TABLE)
                assert code >= load
                assert _n_cr(t, R_M, pressure, s) / load - 1.0 < 2.6e-12 / t + 1e-14


def test_monocoque_raises_a_short_estimate(monkeypatch: pytest.MonkeyPatch) -> None:
    """A brentq estimate short of the root (the test's own bisection) by half the tolerance
    is raised by xtol + rtol t (written out here) and then carries the load; one still
    short after that (brentq's bound broken: here the bracket's lower end) is a
    RuntimeError, never a returned wall."""
    from scipy.optimize import brentq as real_brentq

    n, p, s = 1.0e7, 2.0e5, 1.0
    root = st.monocoque_buckling_thickness_m(n, R_M, E_PA, NU, p, s, DG_TABLE)
    short = _bisect_t(n, R_M, p, s) - 0.5 * XTOL_M
    assert st.monocoque_buckling_load_N(short, R_M, E_PA, NU, p, s, DG_TABLE) < n
    monkeypatch.setattr(st, "brentq", lambda *args, **kwargs: short)
    got = st.monocoque_buckling_thickness_m(n, R_M, E_PA, NU, p, s, DG_TABLE)
    assert got == short + 1e-12 + 4.0 * float(np.finfo(float).eps) * short
    assert st.monocoque_buckling_load_N(got, R_M, E_PA, NU, p, s, DG_TABLE) >= n
    monkeypatch.setattr(st, "brentq", lambda f, a, b, **kwargs: a)
    with pytest.raises(RuntimeError, match="still below"):
        st.monocoque_buckling_thickness_m(n, R_M, E_PA, NU, p, s, DG_TABLE)
    monkeypatch.setattr(st, "brentq", real_brentq)
    assert st.monocoque_buckling_thickness_m(n, R_M, E_PA, NU, p, s, DG_TABLE) == root


def test_monocoque_zero_load_monotone_and_refusals() -> None:
    """No net compression sizes 0; the thickness rises with N and falls with the minimum
    pressure; a table whose chord slope rises, nu outside [0, 0.5), a negative pressure,
    s_dg outside [0, 1] and a non-finite load are refused."""
    assert st.monocoque_buckling_thickness_m(0.0, R_M, E_PA, NU, 2e5, 1.0, DG_TABLE) == 0.0
    assert st.monocoque_buckling_thickness_m(-5.0e6, R_M, E_PA, NU, 2e5, 1.0, DG_TABLE) == 0.0
    loads = np.geomspace(1.0e5, 1.0e8, 25)
    ts = [
        st.monocoque_buckling_thickness_m(float(n), R_M, E_PA, NU, 2e5, 1.0, DG_TABLE)
        for n in loads
    ]
    assert np.all(np.diff(ts) > 0.0)
    pressures = np.linspace(0.0, 1.0e6, 21)
    tp = [
        st.monocoque_buckling_thickness_m(1e7, R_M, E_PA, NU, float(p), 1.0, DG_TABLE)
        for p in pressures
    ]
    assert np.all(np.diff(tp) <= 0.0)
    rising_chord = ((0.0, 0.0), (1.0, 0.1), (2.0, 0.3))
    with pytest.raises(ValueError, match="chord"):
        st.monocoque_buckling_thickness_m(1e7, R_M, E_PA, NU, 2e5, 1.0, rising_chord)
    with pytest.raises(ValueError, match="chord"):
        st.monocoque_buckling_load_N(5e-3, R_M, E_PA, NU, 2e5, 1.0, rising_chord)
    bad_cases = (
        (1e7, R_M, E_PA, 0.5, 2e5, 1.0),
        (1e7, R_M, E_PA, -0.1, 2e5, 1.0),
        (1e7, R_M, E_PA, NU, -1.0, 1.0),
        (1e7, R_M, E_PA, NU, 2e5, 1.5),
        (1e7, R_M, E_PA, NU, 2e5, -0.5),
        (math.nan, R_M, E_PA, NU, 2e5, 1.0),
        (1e7, 0.0, E_PA, NU, 2e5, 1.0),
        (1e7, R_M, 0.0, NU, 2e5, 1.0),
    )
    for bad in bad_cases:
        with pytest.raises(ValueError):
            st.monocoque_buckling_thickness_m(*bad, DG_TABLE)
    with pytest.raises(ValueError):
        st.monocoque_bracket_m(0.0, E_PA, NU, 1.0, DG_TABLE)


# ------------------------------------------------------------------ stiffened walls


def test_gerard_rows_against_hand_values() -> None:
    """t_bar = (d/4) C (N_x / (k_s E d))^n at N_x = 1.652 MN/m, d = 3.66 m, k_s 0.65 for each
    of the four rows (review SP-4: 5.6 mm for ring + common Z); no compression sizes 0;
    monotone in N; refusals."""
    n_x = 1.652e6
    n = n_x * 2.0 * math.pi * 1.83
    for row in st.GERARD_ROWS:
        got = st.gerard_stiffened_thickness_m(n, 1.83, 75.8e9, 0.65, row.c, row.exponent)
        expected = (3.66 / 4.0) * row.c * (1.652e6 / (0.65 * 75.8e9 * 3.66)) ** row.exponent
        assert math.isclose(got, expected, rel_tol=REL), row
    common_z = st.gerard_stiffened_thickness_m(n, 1.83, 75.8e9, 0.65, 6.48, 0.6)
    assert round(common_z * 1000.0, 1) == 5.6  # review SP-4's number, a cross-check only
    assert st.gerard_stiffened_thickness_m(0.0, 1.83, 75.8e9, 0.65, 6.48, 0.6) == 0.0
    assert st.gerard_stiffened_thickness_m(-1e6, 1.83, 75.8e9, 0.65, 6.48, 0.6) == 0.0
    loads = np.geomspace(1e5, 1e8, 20)
    ts = [st.gerard_stiffened_thickness_m(float(x), 1.83, 75.8e9, 0.65, 6.48, 0.6) for x in loads]
    assert np.all(np.diff(ts) > 0.0)
    bad_cases = (
        (n, 1.83, 75.8e9, 0.0, 6.48, 0.6),
        (n, 1.83, 75.8e9, 1.2, 6.48, 0.6),
        (n, 1.83, 75.8e9, 0.65, 0.0, 0.6),
        (n, 1.83, 75.8e9, 0.65, 6.48, 0.0),
        (n, 1.83, 75.8e9, 0.65, 6.48, 1.1),
        (n, 0.0, 75.8e9, 0.65, 6.48, 0.6),
    )
    for bad in bad_cases:
        with pytest.raises(ValueError):
            st.gerard_stiffened_thickness_m(*bad)


def test_plate_limited_thickness() -> None:
    """t = t_ref N / N_ref: the anchor itself, 2.5 times the load, no compression; refusals
    of N_ref <= 0 and t_ref < 0."""
    assert st.plate_limited_thickness_m(1.0e7, 1.0e7, 5.0e-3) == 5.0e-3
    got = st.plate_limited_thickness_m(2.5e7, 1.0e7, 5.0e-3)
    assert math.isclose(got, 5.0e-3 * 2.5e7 / 1.0e7, rel_tol=REL)
    assert st.plate_limited_thickness_m(0.0, 1.0e7, 5.0e-3) == 0.0
    assert st.plate_limited_thickness_m(-1.0, 1.0e7, 5.0e-3) == 0.0
    for bad in ((1e7, 0.0, 5e-3), (1e7, -1e7, 5e-3), (1e7, 1e7, -1e-3), (math.inf, 1e7, 5e-3)):
        with pytest.raises(ValueError):
            st.plate_limited_thickness_m(*bad)


# ------------------------------------------------------------------ combined membrane


def test_von_mises_thickness_hand_value_and_limits() -> None:
    """t = sqrt(A^2 - A B + B^2)/(F_tu eta) with A = FS max(p, 0) r and B = -N_d/(2 pi r); at
    that t the von Mises stress is exactly F_tu eta; B = 0 is the hoop thickness, A = 0 is
    |B|/(F_tu eta); a net compression under hoop tension needs more wall than either; a net
    external pressure (p < 0) is clamped to A = 0, so with B = 0 it sizes 0 as the hoop
    mode does, and with a compression it gives |B|/(F_tu eta) (review S1-C2)."""
    p, n_d = 4.0e5, 2.0e7
    a = 1.4 * 4.0e5 * 1.83
    b = -2.0e7 / (2.0 * math.pi * 1.83)
    expected = math.sqrt(a * a - a * b + b * b) / (558.0e6 * 0.7)
    got = st.von_mises_thickness_m(p, R_M, n_d, FS, F_TU_PA, ETA_W)
    assert math.isclose(got, expected, rel_tol=REL)
    s_h, s_x = a / got, b / got
    assert math.isclose(math.sqrt(s_h**2 - s_h * s_x + s_x**2), 558.0e6 * 0.7, rel_tol=REL)
    hoop_only = st.von_mises_thickness_m(p, R_M, 0.0, FS, F_TU_PA, ETA_W)
    assert math.isclose(hoop_only, a / (558.0e6 * 0.7), rel_tol=REL)
    assert math.isclose(hoop_only, st.hoop_thickness_m(p, R_M, FS, F_TU_PA, ETA_W), rel_tol=REL)
    axial_only = st.von_mises_thickness_m(0.0, R_M, n_d, FS, F_TU_PA, ETA_W)
    assert math.isclose(axial_only, abs(b) / (558.0e6 * 0.7), rel_tol=REL)
    assert got > max(hoop_only, axial_only)
    # a net axial tension (N_d < 0) with hoop tension: the closed form with B > 0
    b_t = 1.0e7 / (2.0 * math.pi * 1.83)
    tension = st.von_mises_thickness_m(p, R_M, -1.0e7, FS, F_TU_PA, ETA_W)
    assert math.isclose(
        tension, math.sqrt(a * a - a * b_t + b_t * b_t) / (558.0e6 * 0.7), rel_tol=REL
    )
    # a net external pressure: no hoop stress sized or credited
    assert st.von_mises_thickness_m(-4.0e5, R_M, 0.0, FS, F_TU_PA, ETA_W) == 0.0
    assert st.hoop_thickness_m(-4.0e5, R_M, FS, F_TU_PA, ETA_W) == 0.0
    external = st.von_mises_thickness_m(-4.0e5, R_M, n_d, FS, F_TU_PA, ETA_W)
    assert math.isclose(external, abs(b) / (558.0e6 * 0.7), rel_tol=REL)
    assert external == axial_only
    unclamped = math.sqrt((1.4 * 4.0e5 * 1.83) ** 2 - (-1.4 * 4.0e5 * 1.83) * b + b * b)
    assert external > unclamped / (558.0e6 * 0.7)  # crediting hoop compression would thin it
    for bad in ((p, 0.0, n_d, FS, F_TU_PA, ETA_W), (p, R_M, n_d, FS, F_TU_PA, 1.5)):
        with pytest.raises(ValueError):
            st.von_mises_thickness_m(*bad)


# ------------------------------------------------------------------ domes


def test_dome_crown_thickness() -> None:
    """t = FS p a (a/b)/2 / (F_tu eta): the hemisphere (half the hoop thickness) and
    a/b = sqrt(2); the common dome's case (LOX side 3 bar plus 30 m of head at 4 g0, the
    RP-1 side's 1.5 bar minimum subtracted once, unfactored: review SP-10) written out;
    a reverse pressure sizes 0; a/b outside [1, sqrt(2)] refused."""
    hemi = st.dome_crown_thickness_m(5.0e5, R_M, 1.0, FS, F_TU_PA, ETA_W)
    assert math.isclose(hemi, 1.4 * 5.0e5 * 1.83 * 0.5 / (558.0e6 * 0.7), rel_tol=REL)
    assert math.isclose(
        hemi, 0.5 * st.hoop_thickness_m(5.0e5, R_M, FS, F_TU_PA, ETA_W), rel_tol=REL
    )
    k = math.sqrt(2.0)
    ell = st.dome_crown_thickness_m(5.0e5, R_M, k, FS, F_TU_PA, ETA_W)
    assert math.isclose(ell, 1.4 * 5.0e5 * 1.83 * (k / 2.0) / (558.0e6 * 0.7), rel_tol=REL)
    p_lox = 3.0e5 + 1141.0 * 4.0 * G0_MPS2 * 30.0
    common = st.dome_crown_thickness_m(p_lox, R_M, 1.2, FS, F_TU_PA, ETA_W, p_relief_pa=1.5e5)
    expected = (1.4 * p_lox - 1.5e5) * 1.83 * (1.2 / 2.0) / (558.0e6 * 0.7)
    assert math.isclose(common, expected, rel_tol=REL)
    assert st.dome_crown_thickness_m(-1.0e5, R_M, 1.2, FS, F_TU_PA, ETA_W) == 0.0
    assert st.dome_crown_thickness_m(1.0e5, R_M, 1.2, FS, F_TU_PA, ETA_W, p_relief_pa=2e5) == 0.0
    for bad_k in (0.99, 1.42, 2.0, math.nan):
        with pytest.raises(ValueError):
            st.dome_crown_thickness_m(5.0e5, R_M, bad_k, FS, F_TU_PA, ETA_W)


def test_spheroid_head_area() -> None:
    """The half oblate spheroid: 2 pi a^2 for a hemisphere; at a/b = sqrt(2) and 2 the
    written-out pi a^2 + (pi b^2/(2 e)) ln((1 + e)/(1 - e)) (1.6232 pi a^2 at sqrt(2),
    survey 08); continuous at a/b -> 1; less than the hemisphere and above the flat disc;
    refusals."""
    a = 1.83
    assert math.isclose(st.spheroid_head_area_m2(a, 1.0), 2.0 * math.pi * a * a, rel_tol=REL)
    for k in (math.sqrt(2.0), 2.0, 1.1):
        b = a / k
        e = math.sqrt(1.0 - b * b / (a * a))
        expected = math.pi * a * a + (math.pi * b * b / (2.0 * e)) * math.log((1.0 + e) / (1.0 - e))
        assert math.isclose(st.spheroid_head_area_m2(a, k), expected, rel_tol=REL), k
    ratio = st.spheroid_head_area_m2(a, math.sqrt(2.0)) / (math.pi * a * a)
    assert round(ratio, 4) == 1.6232  # survey 08's number, a cross-check only
    near = st.spheroid_head_area_m2(a, 1.0 + 1e-9)
    assert math.isclose(near, 2.0 * math.pi * a * a, rel_tol=1e-8)
    areas = [st.spheroid_head_area_m2(a, float(k)) for k in np.linspace(1.0, 3.0, 41)]
    assert np.all(np.diff(areas) < 0.0) and areas[-1] > math.pi * a * a
    for bad in ((a, 0.9), (0.0, 1.2), (-1.0, 1.2), (a, math.inf)):
        with pytest.raises(ValueError):
            st.spheroid_head_area_m2(*bad)


# ------------------------------------------------------------------ load entry


def _ring_mass_from_moment(moment: float, r: float) -> float:
    """m = 2 pi r rho k b^2 with Z = FS f M / F_tu and b = (6 Z/k^2)^(1/3), written out at
    h/b 2, FS 1.4, F_tu 558 MPa, fitting factor 1.15 and 2713 kg/m^3."""
    z = 1.4 * 1.15 * moment / 558.0e6
    b = (6.0 * z / 4.0) ** (1.0 / 3.0)
    return 2.0 * math.pi * r * 2713.0 * 2.0 * b * b


def _ring(f: float, pads: Any) -> float:
    """ring_frame_mass_kg on the 1.83 m ring at the hand case's section and material."""
    return st.ring_frame_mass_kg(f, 1.83, pads, 2.0, 1.4, 558.0e6, 1.15, 2713.0)


def test_ring_frame_mass_hand_value() -> None:
    """20 MN through 8 pads on the 1.83 m ring (h/b 2, FS 1.4, F_tu 558 MPa, fitting factor
    1.15, 2713 kg/m^3), written out: q = F/(2 pi r), alpha = pi/8, the moment at the pads
    M = q r^2 (1 - alpha cos(alpha)/sin(alpha)), Z = FS f M / F_tu, b = (6 Z/k^2)^(1/3),
    m = 2 pi r rho k b^2 (about 747 kg; 1.0% above the straight beam's q l^2/12, review
    PHYS-S1-02); the section modulus of b x 2b is Z; mass scales as F^(2/3) and as
    (1 - alpha cot alpha)^(2/3) in N_p, which at many pads is q l^2/12 and N_p^(-4/3); a
    numpy integer pad count is accepted; refusals (fewer than 3 pads, a float, a bool, a
    string)."""
    circ = 2.0 * math.pi * 1.83
    q = 20.0e6 / circ
    alpha = math.pi / 8.0
    moment = q * 1.83**2 * (1.0 - alpha * math.cos(alpha) / math.sin(alpha))
    expected = _ring_mass_from_moment(moment, 1.83)
    got = _ring(20.0e6, 8)
    assert math.isclose(got, expected, rel_tol=REL)
    z = 1.4 * 1.15 * moment / 558.0e6
    b = (6.0 * z / 4.0) ** (1.0 / 3.0)
    assert math.isclose(b * (2.0 * b) ** 2 / 6.0, z, rel_tol=REL)  # Z of a b x h section
    assert round(got) == 747  # hand number, a cross-check only
    beam = q * (circ / 8.0) ** 2 / 12.0
    assert round(moment / beam, 4) == 1.0104  # review PHYS-S1-02's ratio, a cross-check only
    assert math.isclose(_ring(40.0e6, 8) / got, 2.0 ** (2.0 / 3.0), rel_tol=REL)
    a16 = math.pi / 16.0
    ratio_16 = (1.0 - a16 * math.cos(a16) / math.sin(a16)) / (
        1.0 - alpha * math.cos(alpha) / math.sin(alpha)
    )
    assert math.isclose(_ring(20.0e6, 16) / got, ratio_16 ** (2.0 / 3.0), rel_tol=1e-11)
    # many pads: the straight beam's q l^2/12, and the mass ratio of doubling N_p 2^(-4/3)
    many = 400
    a_many = math.pi / many
    near = q * 1.83**2 * (1.0 - a_many * math.cos(a_many) / math.sin(a_many))
    assert math.isclose(near, q * (circ / many) ** 2 / 12.0, rel_tol=1e-4)
    assert math.isclose(
        _ring(20.0e6, 2 * many) / _ring(20.0e6, many), 2.0 ** (-4 / 3), rel_tol=1e-4
    )
    assert _ring(20.0e6, np.int64(8)) == got
    assert _ring(0.0, 8) == 0.0
    for pads in (2, 0, -8, 8.0, np.float64(8.0), True, np.bool_(True), "8", None):
        with pytest.raises(ValueError):
            _ring(20.0e6, pads)
    with pytest.raises(ValueError):
        st.ring_frame_mass_kg(20.0e6, 1.83, 8, 0.0, 1.4, 558.0e6, 1.15, 2713.0)


@pytest.mark.parametrize("pads", [3, 4, 6, 8, 16])
def test_ring_support_moment_against_the_half_span_statics(pads: int) -> None:
    """The ring's moment at the pads from an independent statics solve: the half span from a
    midspan (angle 0, moment M_m along x, no shear and no torsion there by symmetry) to a
    pad (angle alpha, moment M along (cos alpha, sin alpha), no torsion by symmetry), its
    load's moment about the pad integrated by scipy's quad, the two in-plane moment
    equations solved for M and M_m. The code's mass equals the mass from that M; M_m is
    q r^2 (alpha/sin alpha - 1); M is above the straight beam's q l^2/12."""
    from scipy.integrate import quad

    r, f = 1.83, 20.0e6
    q = f / (2.0 * math.pi * r)
    alpha = math.pi / pads
    # load q r dtheta at r (cos theta, sin theta), along -z; its moment about the pad
    l_x = -quad(lambda th: q * r * r * (math.sin(th) - math.sin(alpha)), 0.0, alpha)[0]
    l_y = quad(lambda th: q * r * r * (math.cos(th) - math.cos(alpha)), 0.0, alpha)[0]
    # M_m (1, 0) + M_pad (cos alpha, sin alpha) + (l_x, l_y) = 0
    m_pad = -l_y / math.sin(alpha)
    m_mid = -l_x - m_pad * math.cos(alpha)
    moment = abs(m_pad)
    assert math.isclose(_ring(f, pads), _ring_mass_from_moment(moment, r), rel_tol=1e-10)
    assert math.isclose(abs(m_mid), q * r * r * (alpha / math.sin(alpha) - 1.0), rel_tol=1e-10)
    beam = q * (2.0 * math.pi * r / pads) ** 2 / 12.0
    assert moment > beam


# ------------------------------------------------------------------ dynamics


def test_dynamic_load_factor_values() -> None:
    """rise_time: 2 at t_r = 0; 1 + T/(pi t_r) in between (0.5 s at 5 Hz: 1.1273); near 1
    when T/(pi t_r) is small; capped at 2; never below the exact single-mode response
    1 + |sin(pi t_r/T)|/(pi t_r/T); quasi_static 1 and step 2; refusals."""
    assert st.dynamic_load_factor(0.0, 0.2, "rise_time") == 2.0
    got = st.dynamic_load_factor(0.5, 0.2, "rise_time")
    assert math.isclose(got, 1.0 + 0.2 / (math.pi * 0.5), rel_tol=REL)
    assert round(got, 4) == 1.1273
    slow = st.dynamic_load_factor(10.0, 0.01, "rise_time")
    assert math.isclose(slow, 1.0 + 0.01 / (math.pi * 10.0), rel_tol=REL) and slow < 1.0004
    assert st.dynamic_load_factor(0.01, 0.5, "rise_time") == 2.0
    for ratio in np.linspace(0.05, 6.0, 120):
        t_r = float(ratio) * 0.2
        exact = 1.0 + abs(math.sin(math.pi * ratio)) / (math.pi * ratio)
        assert st.dynamic_load_factor(t_r, 0.2, "rise_time") >= exact - 1e-15
    assert st.dynamic_load_factor(0.5, 0.2, "quasi_static") == 1.0
    assert st.dynamic_load_factor(0.5, 0.2, "step") == 2.0
    for bad in (
        (0.5, 0.2, "sinc"),
        (-0.1, 0.2, "rise_time"),
        (0.5, 0.0, "rise_time"),
        (math.nan, 0.2, "step"),
    ):
        with pytest.raises(ValueError):
            st.dynamic_load_factor(*bad)  # type: ignore[arg-type]


def test_peak_load() -> None:
    """n_0 + DLF (n_q - n_0): 1 -> 4 g0 at 1.1 is 4.3 g0; in newtons the same; a release
    from 4 g0 to 0 at 2 swings to -4 g0; DLF < 1 refused."""
    assert math.isclose(st.peak_load(4.0, 1.0, 1.1), 1.0 + 1.1 * 3.0, rel_tol=REL)
    assert math.isclose(st.peak_load(21.0e6, 5.3e6, 1.3), 5.3e6 + 1.3 * 15.7e6, rel_tol=REL)
    assert st.peak_load(0.0, 4.0, 2.0) == -4.0
    assert st.peak_load(3.0, 3.0, 2.0) == 3.0
    for bad in ((4.0, 1.0, 0.99), (4.0, 1.0, math.nan), (math.inf, 1.0, 1.1)):
        with pytest.raises(ValueError):
            st.peak_load(*bad)


def test_ramped_plateau_acceleration() -> None:
    """The linear-ramp plateau at L = 100 m, v_e = 76.70717046013364 m/s (3 g0 over 100 m),
    t_r = 1.061 s: the written-out a' = [L - sqrt(L^2 - v_e^2 t_r^2/12)]/(t_r^2/12), and the
    ramp's own kinematics (v_r = a' t_r/2, s_r = a' t_r^2/6, then constant a') reach v_e at
    exactly L; 29.84 m/s^2, 1.42% above v_e^2/(2 L) (the closed form does not reproduce
    review SP-8's "about 29.77" at 1.061 s, which the S1 spec repeated; 29.77 corresponds
    to t_r of about 0.97 s); t_r = 0 is v_e^2/(2 L) and t_r -> 0 tends to it; refusals of a
    ramp that cannot reach v_e or does not finish in the stroke."""
    length, v_e, t_r = 100.0, 76.70717046013364, 1.061
    got = st.ramped_plateau_accel_mps2(length, v_e, t_r)
    expected = (length - math.sqrt(length**2 - v_e**2 * t_r**2 / 12.0)) / (t_r**2 / 12.0)
    assert math.isclose(got, expected, rel_tol=REL)
    v_r = got * t_r / 2.0
    s_r = got * t_r**2 / 6.0
    assert s_r < length and v_r < v_e
    assert math.isclose(math.sqrt(v_r**2 + 2.0 * got * (length - s_r)), v_e, rel_tol=REL)
    t_c = (v_e - v_r) / got
    assert math.isclose(s_r + v_r * t_c + 0.5 * got * t_c**2, length, rel_tol=REL)
    assert round(got, 2) == 29.84  # hand number, a cross-check only
    constant = v_e**2 / (2.0 * length)
    assert math.isclose(constant, 3.0 * G0_MPS2, rel_tol=REL)
    assert got > constant
    assert st.ramped_plateau_accel_mps2(length, v_e, 0.0) == constant
    assert math.isclose(st.ramped_plateau_accel_mps2(length, v_e, 1e-6), constant, rel_tol=1e-9)
    assert st.ramped_plateau_accel_mps2(length, 0.0, 1.0) == 0.0
    assert st.ramped_plateau_accel_mps2(100.0, 290.0, 1.0) > 0.0  # v_e t_r = 2.9 L: finishes
    bad_cases = (
        (0.0, v_e, t_r),
        (length, -1.0, t_r),
        (length, v_e, -0.1),
        (1.0, 100.0, 1.0),  # L^2 < v_e^2 t_r^2 / 12: no real plateau
        (100.0, 320.0, 1.0),  # v_e t_r > 3 L: the ramp does not finish within the stroke
    )
    for bad in bad_cases:
        with pytest.raises(ValueError):
            st.ramped_plateau_accel_mps2(*bad)


# ------------------------------------------------------------------ increments


def test_barrel_increment_counts_positive_parts_only() -> None:
    """NOF sum 2 pi r rho dz max(0, t_push - t_env), written out: only the station where the
    push needs more wall counts; a push inside the envelope adds exactly 0; refusals."""
    t_push = [3.0e-3, 5.0e-3, 4.0e-3, 6.5e-3]
    t_env = [4.0e-3, 4.0e-3, 4.0e-3, 6.0e-3]
    dz = [1.0, 2.0, 3.0, 0.5]
    got = st.barrel_increment_kg(t_push, t_env, dz, 1.83, 2713.0, 1.8)
    expected = 0.0
    for tp, te, d in zip(t_push, t_env, dz, strict=True):
        if tp > te:
            expected += 2.0 * math.pi * 1.83 * 2713.0 * d * (tp - te)
    expected *= 1.8
    assert math.isclose(got, expected, rel_tol=REL)
    assert st.barrel_increment_kg(t_env, t_env, dz, 1.83, 2713.0, 1.8) == 0.0
    inside = [2.0e-3, 4.0e-3, 1.0e-3, 6.0e-3]
    assert st.barrel_increment_kg(inside, t_env, dz, 1.83, 2713.0, 1.9) == 0.0
    arrays = st.barrel_increment_kg(
        np.array(t_push), np.array(t_env), np.array(dz), 1.83, 2713.0, 1.8
    )
    assert arrays == got
    bad_cases: tuple[tuple[Any, ...], ...] = (
        (t_push[:3], t_env, dz, 1.83, 2713.0, 1.8),
        (t_push, t_env, [1.0, -2.0, 3.0, 0.5], 1.83, 2713.0, 1.8),
        ([-1e-3, 5e-3, 4e-3, 6e-3], t_env, dz, 1.83, 2713.0, 1.8),
        (t_push, t_env, dz, 1.83, 2713.0, 0.9),
        (t_push, t_env, dz, 0.0, 2713.0, 1.8),
        ([math.nan, 5e-3, 4e-3, 6e-3], t_env, dz, 1.83, 2713.0, 1.8),
    )
    for bad in bad_cases:
        with pytest.raises(ValueError):
            st.barrel_increment_kg(*bad)


def test_area_increment_counts_the_positive_part_only() -> None:
    """NOF A rho max(0, t_push - t_env): a dome 0.4 mm thicker; 0 inside the envelope;
    refusals."""
    area = 1.6232 * math.pi * 1.83**2
    got = st.area_increment_kg(4.4e-3, 4.0e-3, area, 2713.0, 1.9)
    assert math.isclose(got, 1.9 * area * 2713.0 * (4.4e-3 - 4.0e-3), rel_tol=REL)
    assert st.area_increment_kg(3.9e-3, 4.0e-3, area, 2713.0, 1.9) == 0.0
    assert st.area_increment_kg(4.0e-3, 4.0e-3, area, 2713.0, 1.9) == 0.0
    for bad in ((4.4e-3, 4.0e-3, -1.0, 2713.0, 1.9), (4.4e-3, 4.0e-3, area, 2713.0, 0.5)):
        with pytest.raises(ValueError):
            st.area_increment_kg(*bad)


# ------------------------------------------------------------------ timing


def _per_call_s(fn: Any, args: tuple[Any, ...], calls: int) -> float:
    """Mean wall time [s] of ``calls`` calls of fn(*args)."""
    start = time.perf_counter()
    for _ in range(calls):
        fn(*args)
    return (time.perf_counter() - start) / calls


def test_primitive_timing(request: pytest.FixtureRequest) -> None:
    """One call of each primitive group, timed over a loop and recorded (user_properties;
    nothing printed). The ceilings are generous (S2's screened search needs a few thousand
    sizings of about a hundred stations each), so this fails only on a gross slow-down."""
    groups: dict[str, tuple[Any, tuple[Any, ...], int, float]] = {
        "hydrostatic_and_hoop": (
            lambda: st.hoop_thickness_m(
                st.hydrostatic_pressure_pa(3e5, RHO_LOX, 4.0, 20.0), R_M, FS, F_TU_PA, ETA_W
            ),
            (),
            5000,
            1e-3,
        ),
        "monocoque_solve": (
            st.monocoque_buckling_thickness_m,
            (2.0e7, R_M, E_PA, NU, 2.0e5, 1.0, DG_TABLE),
            500,
            1e-2,
        ),
        "gerard": (st.gerard_stiffened_thickness_m, (2e7, R_M, E_PA, 0.65, 6.48, 0.6), 5000, 1e-3),
        "von_mises": (st.von_mises_thickness_m, (4e5, R_M, 2e7, FS, F_TU_PA, ETA_W), 5000, 1e-3),
        "dome_and_area": (
            lambda: (
                st.dome_crown_thickness_m(5e5, R_M, 1.2, FS, F_TU_PA, ETA_W)
                * st.spheroid_head_area_m2(R_M, 1.2)
            ),
            (),
            5000,
            1e-3,
        ),
        "ring": (st.ring_frame_mass_kg, (2e7, R_M, 8, 2.0, FS, F_TU_PA, 1.15, RHO_W), 5000, 1e-3),
        "dlf_peak_plateau": (
            lambda: st.peak_load(
                st.ramped_plateau_accel_mps2(100.0, 76.7, 0.5),
                0.0,
                st.dynamic_load_factor(0.5, 0.2, "rise_time"),
            ),
            (),
            5000,
            1e-3,
        ),
        "barrel_increment_100_stations": (
            st.barrel_increment_kg,
            (np.full(100, 5e-3), np.full(100, 4e-3), np.full(100, 0.13), R_M, RHO_W, 1.8),
            2000,
            1e-2,
        ),
    }
    for name, (fn, args, calls, ceiling) in groups.items():
        per_call = _per_call_s(fn, args, calls)
        request.node.user_properties.append((f"{name}_s_per_eval", per_call))
        assert per_call < ceiling, (name, per_call)
