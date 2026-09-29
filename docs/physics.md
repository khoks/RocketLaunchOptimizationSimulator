# launch-assist-sim: physics and assumptions

Phase 0/1; sections are added as the code they describe lands. This file is the source
of truth for the equations in `src/launchsim/`; when code and this document disagree,
one of them is wrong and the change that fixes it updates both. Every section names
the module it describes, states its frame, units and assumptions, and points at the
test that validates it.

## Atmosphere

Module: `src/launchsim/atmosphere.py`. Test: `tests/test_atmosphere.py`. Not used by
the Phase 1 dynamics (no drag yet); it is a Phase 0 deliverable for Phase 2.

`standard_atmosphere(alt_m)` returns an `AtmosphereState(p_pa, rho_kgm3, T_K, a_mps)`
for a **geometric** altitude above mean sea level in metres. A real number, numpy
real scalar or 0-d array gives Python floats; an array (or sequence) of any shape
gives read-only arrays of that shape. `pressure_pa`, `density_kgm3` and
`speed_of_sound_mps` are one-field conveniences. Non-numeric input (string, `None`,
bool, complex) raises `TypeError`; NaN, infinite or sub-floor altitudes raise
`ValueError`.

Cost: about 2 us for a Python float or int or a numpy real scalar (`np.float64` is what
`solve_ivp` hands out), about 10 us for a 0-d array, and about 0.07 us per array
element, so the function can sit inside a `solve_ivp` right-hand side.
(`ambiance.Atmosphere` itself costs about 1 ms per call because each property re-runs
its layer masking; that is why the layer formulas are evaluated in-house.)

### ICAO range, -5,004 m to 81,020 m

The ICAO Standard Atmosphere (ICAO Doc 7488, extended to 80 km geopotential) is a
stack of layers with linear temperature; the module evaluates its closed forms directly
from the layer table and primary constants shipped by the `ambiance` package
(`ambiance.CONST`: table D bases `H_b`, `T_b`, `beta`, `p_b`; `g_0`, `R`, `kappa`, `r`),
so no table value is retyped in this repository. With the geopotential height

    H = r0 h / (r0 + h),   r0 = 6,356,766 m (ICAO nominal radius),

and the layer whose base `H_b <= H`:

    T = T_b + beta (H - H_b)
    p = p_b (T / T_b)^(-g0 / (R_air beta))        beta != 0
    p = p_b exp(-g0 (H - H_b) / (R_air T_b))      beta == 0
    rho = p / (R_air T),   a = sqrt(kappa R_air T)

`g0` here is the ICAO definitional constant of the geopotential metre (9.80665 m/s^2,
read from `ambiance.CONST.g_0`); it is a constant of the table, not a gravity model,
and it is deliberately not `G0_MPS2` (which converts Isp and defines the unit "g").
`R_air` = 287.05287 J/(kg K) (`R_AIR_JKGK`, asserted equal to `ambiance.CONST.R`), and
`kappa` = 1.4. Above the last base row (71 km geopotential) the 71-80 km layer is
extrapolated to the 81,020 m geometric top, which is H = 80,000.36 m, 0.36 m past the
table's end; and below the first base row (H = -5,000 m, which is h = -4,996.07 m
geometric) the -5 km row is extrapolated 7.9 m downward to the -5,004 m geometric floor
(H = -5,007.9 m). Both are exactly what `ambiance` does (its `h_min` of -5,004 m sits
just below the table's first base).

The base pressures `p_b` are the table's rounded values (six significant figures:
177687, 101325, 22632.0, 5474.87, 868.014, 110.906, 66.9384, 3.95639 Pa), not pressures
propagated from 101,325 Pa through the layers as ICAO Doc 7488 defines the profile. `p`
and `rho` are therefore only piecewise continuous: evaluating the closed form from either
side of a base gives relative jumps of 2.6e-7 at 0 km, -1.8e-6 at 11 km, 4.1e-6 at
47 km, -4.0e-6 at 51 km and 1.4e-6 at 71 km. `ambiance` has the same jumps. They are
far below the 0.01 m/s loss-budget resolution (a vertical coast with drag through 0-34 km
under DOP853 at rtol 1e-10 changed by 2.6e-4 m/s in speed after 60 s and took no extra
steps when the jumps were removed), so the table values are kept and the oracle agreement
below stays at 1e-12.

`ambiance.Atmosphere` is the reference implementation: `test_matches_ambiance_on_dense_grid`
asserts agreement of `p`, `rho`, `T` and `a` to 1e-12 relative on a 20,001-point grid
plus every layer base (measured: 8e-15), and `test_scalar_path_matches_ambiance` does
the same for the pure-Python scalar branch. `r0` is not the package's `R_EARTH_M`
(6,378,137 m). The tests therefore convert their ICAO table points with
`h = r0 H / (r0 - H)` before calling, check the table rows at 0, 11, 20, 32, 47, 51,
71 and 80 km geopotential to 1e-4 in `p` (table rounding is below 5e-5; the wrong
radius would give 1.5e-4 at 47 km, and would also fail the 1e-12 oracle test), and a
guard test checks that
`p(11,000 m geometric)` differs from the 22,632 Pa tropopause value by more than 0.1%,
so the conversion cannot silently be dropped.

Mixed arrays are split by a mask into the ICAO part and the extension part; an empty
array returns empty fields. Nothing in the module can warn, and pytest runs with
`filterwarnings = error`.

### Isothermal extension above 81,020 m

From the ICAO state at the top (`h_top` = 81,020 m: `T_top` = 196.649 K, `p_top` =
0.8862 Pa, `a_top` = 281.12 m/s; the test pins these to the table's 80 km row):

    T(h)   = T_top
    p(h)   = p_top * exp(-(h - h_top) / H_s)
    rho(h) = p(h) / (R_air * T_top)
    a(h)   = a_top
    H_s    = R_air * T_top / g(h_top),   g(h_top) = mu / (R_E + h_top)^2

with `mu` = `MU_EARTH_M3S2` and `R_E` = `R_EARTH_M`, giving `H_s` = 5908.4 m
(`extension_scale_height_m()`; the test recomputes it from the table temperature).
The extension continues to any altitude and never steps to zero until float64
underflow, roughly 4,400 km above the top, so drag stays a smooth function of state
through orbital altitude. `p`, `rho`, `T` and `a` are continuous across the seam to
better than 1e-6 relative (measured ~1e-13); the slope of `ln p` changes by 0.08%
there, which is the difference between the ICAO `g0 (r0/(r0 + h))^2` and this
package's `mu/(R_E + h)^2`.

This is a drag-order-of-magnitude device, not the US Standard Atmosphere 1976: above
about 90 km the real thermosphere warms steeply and its density falls much more slowly
than this exponential (US76 density is about 16x this model's at 150 km and 1e4x at
200 km), and it varies by large factors with solar activity. At the altitudes where
drag still matters for a launcher (below ~100 km) the difference is small; above that
the drag integrand is negligible either way.

### Assumptions (listed in every result that uses this module)

- The ICAO geometric to geopotential conversion uses the ICAO nominal Earth radius
  6,356,766 m, not `R_EARTH_M`; altitudes passed in must be geometric.
- Above 81,020 m the atmosphere is isothermal at 196.649 K (the ICAO state at
  81,020 m) with scale height `R_air T_top / g(h_top)`; not US76.
- The atmosphere is spherically symmetric and static; co-rotation with Earth enters
  through `v_rel` in the dynamics, not here.
