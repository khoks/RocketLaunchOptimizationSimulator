# launch-assist-sim: physics and assumptions

Phase 0, Phase 1 (the 1-D vertical model) and the constant-acceleration vertical silo
pulled forward from Phase 3. This file is the source of truth for the equations in
`src/launchsim/`; when code and this document disagree, one of them is wrong and the
change that fixes it updates both. Every section names the module it describes,
states its frame, units and assumptions, and points at the test that validates it.
The sections run in the order a run does: the atmosphere (a Phase 0 deliverable the
Phase 1 dynamics do not use) and its in-flight use by the Phase 2 planar model (drag,
C_D(M), back-pressure, the fairing rule and the 2-D vehicle forks), frames and datum,
the 1-D state and equations of motion, gravity (with the Phase 2 note on rotation),
the planar state and equations of motion with its loss identity, reductions and
orbital elements (Phase 2, build step 20), the planar release map, the stage-1
guidance and events, the gamma* inner solve and the time-shift mechanism of the
planar gravity loss (build step 21), stage 2 and insertion, LTG shooting, the
rocket-equation closure and max-Q (build step 22), the planar figures of merit, virtual
propellant, the payload and gamma* search, the shared budget and their convergence
(build step 23), thrust startup, the integrator and its event
rules, the phase state machine, loss accounting, the ignition-after-release
loss, the assist energy identity, the silo model and its reported quantities, hot
starts, the failed-ignition coast, the figures of merit and their convergence, and
the planar experiment schema (the shared blocks every run of an experiment carries);
then every assumption the code emits, collected in one list, and the test-to-equation
map.

## Atmosphere

Module: `src/launchsim/atmosphere.py`. Test: `tests/test_atmosphere.py`. Not used by
the 1-D dynamics (no drag); the Phase 2 planar model evaluates it in flight through
the fast path `ambient_scalar` ("Atmosphere, drag and back-pressure in flight").

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

### Assumptions (module docstring; emitted as `ATMOSPHERE_ASSUMPTIONS`, next section)

- The ICAO geometric to geopotential conversion uses the ICAO nominal Earth radius
  6,356,766 m, not `R_EARTH_M`; altitudes passed in must be geometric.
- Above 81,020 m the atmosphere is isothermal at 196.649 K (the ICAO state at
  81,020 m) with scale height `R_air T_top / g(h_top)`; not US76.
- The atmosphere is spherically symmetric and static; co-rotation with Earth enters
  through `v_rel` in the dynamics, not here.

## Atmosphere, drag and back-pressure in flight

Modules: `atmosphere.py` (`ambient_scalar`, `ATMOSPHERE_ASSUMPTIONS`), `vehicle.py`
(`CdTable`, `DragModel`, `FairingDrop`, `Vehicle.aero`, `Vehicle.fairing_rule`,
`with_cd_scale`), `config.py` (`AeroConfig`, `CdMachConfig` on the `QuantityList`
base, `FairingDropConfig`). Test: `tests/test_aero.py`. This is the Phase 2 data layer
(build step 18): the planar model is its only user. The 1-D model has no atmosphere in
flight, ignores `Vehicle.aero` (its assumptions say "no atmosphere, no drag"), and
refuses the heating fairing rule (see "Fairing rule").

**Ambient state inside a right-hand side.** `ambient_scalar(h)` returns the plain tuple
`(p [Pa], rho [kg/m^3], a [m/s])` at the geometric altitude h (the planar model passes
h = r - R_E, a sphere). It evaluates the same closed forms as `standard_atmosphere`
("Atmosphere") with the same operations, so at and above the floor its fields equal
`standard_atmosphere(h)`'s bit for bit (the test checks 50 altitudes from the floor,
next to every layer base (geometric, rounded to 0.1 m), on both sides of the 81,020 m
seam and up to 300 km, at 0 ulp).
It differs in two deliberate ways:

- Below `ALT_AMBIANCE_MIN_M` (-5,004 m) it holds the floor state instead of raising, so
  a trial step that overshoots the ground cannot raise before the ground event ends the
  phase. The ground (the pad, or a silo bottom at -L) is far above the floor, so the
  clamp never acts on an accepted state.
- It validates nothing and builds no dataclass: a NaN altitude gives NaN in all three
  fields (NaN takes the ICAO branch), +inf gives p = rho = 0.

Measured cost on the development machine: about 0.7 us in the ICAO range and 0.25 us
in the extension, against about 2 us for `standard_atmosphere` with its checks. At sea
level p(0) is exactly 101,325 Pa = `P_SEA_LEVEL_PA` (the 0 km base row evaluated at
H - H_b = 0), which the back-pressure and liftoff formulas rely on; a test pins it.

The isothermal extension ("Isothermal extension above 81,020 m") is used unchanged. Its
density at 110 km is 1.16e-7 kg/m^3, against US76's 9.7e-8 (about 20% denser there),
and at 150 km it is 1.3e-10, about 1/16 of US76. Near the fairing-jettison altitude
(100-130 km) the heating rate 0.5 rho V^3 therefore falls through its limit at a
slightly different height than it would in US76; the shift is the same for every run
and variant and is stated, not corrected.

`ATMOSPHERE_ASSUMPTIONS` (a tuple of strings, numbers formatted from the constants; the
planar model appends it to every run's assumptions, and no 1-D result carries it):

- atmosphere: ICAO standard atmosphere closed forms (layer table of ambiance.CONST) from
  -5,004 m to 81,020 m geometric altitude; the geometric to geopotential conversion
  uses the ICAO radius 6,356,766 m, not R_E.
- atmosphere: above 81,020 m an isothermal extension at 196.649 K with scale height
  5,908 m (R_air T_top / g(h_top)); not US76 (denser near 110 km, far thinner above
  150 km).
- atmosphere: static, spherically symmetric, no wind; it co-rotates with Earth, so drag
  and Mach use the Earth-relative velocity v_rel.
- atmosphere: in flight, an altitude below the -5,004 m floor is held at the floor state
  (ambient_scalar clamp; a dive ends at the ground event).

**Mach number, dynamic pressure and drag.** The air co-rotates with Earth and there is
no wind, so every aerodynamic quantity uses the Earth-relative velocity. In the planar
local frame (radial up, horizontal downrange) its components are w = v_r and
u = v_theta - omega_p r, and V = hypot(w, u) = |v_rel|:

    M = V / a(h),    q = 0.5 rho(h) V^2
    D = q cd_scale C_D(M) A_ref                         (magnitude, along -v_rel)
    (D_r, D_theta) = -0.5 rho V cd_scale C_D(M) A_ref (w, u)

`DragModel.force_N(q, M)` is the magnitude and `DragModel.components_N(rho, a, w, u)`
the vector. The vector form has no division by V, so V = 0 (a pad start) gives exactly
(0, 0). There is no lift and no angle-of-attack dependence: the force is pure drag
along -v_rel whatever the thrust direction. One `A_ref` applies to the whole flight,
through staging and fairing jettison, and the power-on table is used in unlit coasts
too (a small bias toward cold starts, stated with the planar assumptions).

**The C_D(M) table.** Braeunig's generic launcher curve (Braeunig 2020, "ballpark"
average of Saturn V, NASA TM X-53770 and MPR-SAT-FE-69-1, and Mercury-Atlas MA-6,
TOR-930(2101)-3): total power-on C_D including base drag, generic and not Falcon 9, so
it is `assumed: true` in every fork. 23 knots:

| M | 0 | 0.3 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 0.95 | 1.0 | 1.05 | 1.1 | 1.15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C_D | 0.460 | 0.404 | 0.387 | 0.385 | 0.388 | 0.400 | 0.450 | 0.510 | 0.589 | 0.660 | 0.710 | 0.730 |

| M | 1.2 | 1.3 | 1.5 | 1.75 | 2.0 | 2.5 | 3.0 | 3.25 | 3.5 | 4.0 | 4.5 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C_D | 0.722 | 0.680 | 0.606 | 0.527 | 0.460 | 0.350 | 0.273 | 0.250 | 0.236 | 0.222 | 0.220 |

Interpolation is PCHIP: a Fritsch-Carlson monotone piecewise cubic Hermite with
Fritsch-Butland (1984) weighted harmonic-mean slopes. With knot
spacings h_k = M_{k+1} - M_k and secants delta_k = (C_{k+1} - C_k)/h_k, the knot slopes
d_k are

    interior:  d_k = 0 if delta_{k-1} delta_k <= 0, else
               d_k = (w1 + w2) / (w1/delta_{k-1} + w2/delta_k),
               w1 = 2 h_k + h_{k-1},  w2 = h_k + 2 h_{k-1}
    ends:      d_0 = ((2 h_0 + h_1) delta_0 - h_0 delta_1) / (h_0 + h_1), set to 0 when
               its sign differs from delta_0's, and to 3 delta_0 when delta_0 and
               delta_1 differ in sign and |d_0| > 3 |delta_0| (mirrored at the right end)

and each interval carries the cubic Hermite through (C_k, d_k) and (C_{k+1}, d_{k+1}).
The curve passes through every knot, is C1 on [0, 4.5], and is monotone on each
interval, so it never overshoots: the peak is exactly the 0.730 knot at M = 1.15 and the
subsonic minimum the 0.385 knot at M = 0.6 (the smallest value, 0.220, is the last
knot). `CdTable.pchip` takes the cubic coefficients (c3, c2, c1, c0) in dM = M - M_k
once from scipy's `PchipInterpolator` (which implements exactly the slopes above) and
stores them as tuples (a hand-built `CdTable` given lists or other sequences stores
tuples of floats too, so every table is immutable and hashable); `CdTable.__call__`
evaluates by `bisect` and Horner's rule in pure Python, about 0.3 us per call. Outside
the knots the end values are held: C_D = 0.460 below M = 0 (unreachable) and 0.220
above M = 4.5. The held right end is C1 for
this table (its end slope is 0) but only C0 in general. Why PCHIP: a C1 curve cut the
planar RHS evaluations by 38% against linear interpolation in the planning prototype,
and the monotone form adds no invented transonic peak.

`cd_scale` multiplies every C_D (`DragModel.cd(M) = cd_scale C_D(M)`); it is 1.0
(assumed) in every fork and is the sensitivity knob (`vehicle.aero.cd_scale`, +/-10%).
`with_cd_scale(vehicle, s)` copies a vehicle with a different scale; `with_payload`
keeps the drag model.

**Reference area.** A_ref = 10.52 m^2 = pi 3.66^2/4 (the 3.66 m body, User's Guide 2021
Table 2-1), because the Braeunig table is normalised by the main-body section with
base drag scaling with the body. The 5.2 m fairing section (21.24 m^2) is a named bound
case in the calibration and silo summaries, not the nominal value; it raises the drag
of every run, pad included.

**Back-pressure.** Unchanged from Phase 1 in form, now with a real p(h):

    T = max(0, T_vac(t) - p(h) A_e)   while lit;   mdot = T_vac(t) / c;   dJ_bp/dt = (T_vac - T)/m

(`ThrustSchedule.thrust_N`). Stage 1: A_e = 9 (914.1 - 845.2) kN / 101,325 Pa =
6.1199 m^2 (0.680 m^2 per Merlin, from the published vacuum and sea-level thrusts), so
T(0) = 8,226.9 - 620.1 = 7,606.8 kN at full thrust, the published 7,607 kN. During the
2 s ramp T_vac < p0 A_e for the first t_r p0 A_e / T_full = 0.1507 s: the thrust is
clamped to zero while propellant still flows, and the whole vacuum thrust is booked as
back-pressure loss (dJ_bp/dt = T_vac/m). The pad baseline (lit at t = -2 s) spends it
under hold-down, before release, outside the release-onward budget; an ignition after
release books it in flight. Stage 2: A_e = 8.6 m^2, assumed
(MVac expansion ratio about 165 with a 3.3 m exit), given as `stage2.engine.exit_area_m2`
(mutually exclusive with `thrust_sl_kN`); p A_e = 44.9 N at 70 km, 0.005% of the 981 kN.
It keeps T = max(0, T_vac - p A_e) complete rather than silently zero.

**Fairing rule.** `FairingDrop(trigger, limit_W_m2)`: `staging` (dropped with stage 1 in
the staging map), `never`, or `free_molecular_heating` (dropped in the planar stage-2
burn at the first instant the free-molecular heating rate 0.5 rho V^3 [W/m^2], V the
speed relative to the air, falls below `limit_W_m2`; 1,135 W/m^2 from the User's Guide
2021 p.38 in every fork; the event is in the stage-2 burn, "Stage 2 and insertion
(planar)"). `Vehicle.fairing_drop`
keeps the Phase 1 string shim: `staging` and `never` are stored as those strings (a
`FairingDrop` with either trigger is normalised to its string) so the 1-D code that
compares `fairing_drop == "staging"` is untouched, and only the heating rule is stored
as a `FairingDrop`; `Vehicle.fairing_rule` always returns a `FairingDrop`. The ideal
screening and `Vehicle.fairing_carried_kg` / `stack_mass_kg` / `mass_after_staging_kg`
count the heating rule as a drop at staging (the planar model keeps its own mass
bookkeeping, and must not use these helpers). A 1-D run refuses a heating-rule vehicle
at resolve time ("a planar_2d feature"; the 1-D model supports only the staging and
never rules), because the 1-D staging map would keep that fairing while the stack
bookkeeping drops it; since build step 19 the refusal applies to `dynamics:
vertical_1d` runs only, and planar_2d runs on the three forks resolve. Since build
step 24 `sim.run` dispatches on `dynamics`: a planar_2d run goes to the planar model
(`sim.run_planar`, "Reporting definitions (planar)"), so no planar run reaches the 1-D
planner and its staging map (the gap build step 19 recorded, where a planar run not
ending in insertion was flown by the 1-D model and burned the heating-rule fairing as
phantom stage-2 propellant, is closed). `test_config_planar.py::
test_sim_dispatches_planar_runs_to_the_planar_model`, the former strict-xfail
tripwire, now asserts that the shipped `silo_failed` runs in the planar model.

**Vehicle-file schema.** Vehicle files stay all-provenance. `aero:` holds
`reference_area_m2` and `cd_scale` (Quantities, both required; `cd_scale` is 1.0 in
every fork, and requiring it lets a `vehicle.aero.cd_scale` sensitivity case always
read its nominal value),
`interpolation: pchip` (the only choice) and `cd_mach: {mach: [...], cd: [...],
source | assumed: true, note}`. `cd_mach` is a `QuantityList`: one provenance covers
the whole table, every list entry must be a finite number (a bool, string or NaN raises
instead of being coerced), and the knots must be valid for `CdTable` (equal lengths, at
least two, Mach strictly increasing from >= 0, C_D >= 0). `fairing_drop:` is the string
`staging` or `never`, or the block `{trigger, limit_W_m2}` with `limit_W_m2` a Quantity
required exactly for the heating trigger.

**The three 2-D vehicle forks** (decision 1 and amendment 2; forked 2026-09-29 from
`generic_f9_class.yaml`, which is unchanged; never edited after the first calibration
run). They are identical except for the five masses below: the same engines (9 x
914.1 / 845.2 kN, Isp_vac 311 s, 2 s ramp; MVac 981 kN, 348 s), stage-2 A_e 8.6 m^2,
an 11 s staging coast (User's Guide 2021 Table 8-4, MECO T+145 s to SES-1 T+156 s;
the 1-D file has 3 s, assumed), the heating fairing rule, the aero block, 22.8 t of
payload and the 295 / 348 s screening Isp. `test_aero.py` checks that the forks differ
only in these masses.

| Set | File | Stage 1 dry / prop [t] | Stage 2 dry / prop [t] | Fairing [t] | Without payload [t] |
|---|---|---|---|---|---|
| C (default gate) | `generic_f9_class_2d.yaml` | 22.2 / 410.9 | 4.0 / 107.5 | 1.7 | 546.3 |
| A (README loads) | `generic_f9_class_2d_readme_loads.yaml` | 25.6 / 395.7 | 3.9 / 92.67 | 1.9 | 519.77 |
| B (recorded scope) | `generic_f9_class_2d_recorded_scope.yaml` | 25.6 / 410.9 | 4.0 / 107.5 | 1.9 | 549.9 |

Set C's masses are the Full Thrust (2017) table (Espace & Exploration No.39 via
Wikipedia) with Block 5 thrust, because the 22,800 kg claim is a Block 5 figure; the
same table gives 934 kN for the FT upper stage, so the fork is a version mix, disclosed
in its header. The published launch mass is 549 t (549,054 kg on spacex.com, which
does not say whether it includes a payload), so the closure is quoted without payload.
Set A keeps every README value and its provenance. Set B re-sources exactly what the
Phase 1 notes recorded (both propellant loads and the stage-2 dry mass) and keeps the
assumed 25.6 t stage-1 dry mass and the 1.9 t fairing.

## Frames and datum

Modules: `src/launchsim/dynamics.py`, the `src/launchsim/phases/` package (`engine.py`,
`trace.py`, `prelude.py`, `vertical.py`; see "Integrator" and "Phases and events"). Tests:
`tests/test_rocket_equation.py`, `tests/test_vertical_burn.py`, `tests/test_coast.py`,
`tests/test_events.py`.

**Ascent (Phase 1, 1-D).** One axis, +z up, z = 0 at the pad or silo mouth (the
release point), r = r_datum + z with r_datum = `R_EARTH_M`. The velocity v = dz/dt is
signed: positive rising, negative falling. Earth rotation is off in Phase 1
(omega_p = 0), so inertial and Earth-relative velocities coincide and the Earth-relative
flight-path angle is gamma_rel = +90 deg for v > 0, -90 deg for v < 0, and +90 deg (local
vertical) when |v| < `V_REL_EPS_MPS` (a pad start). The 2-D polar ascent frame of
CLAUDE.md (state [r, theta, v_r, v_theta, m], omega_p = omega_E cos(lat) sin(az),
`planar_rotation_rate(lat, az)`) is the `planar_2d` model: "Planar ascent state and
equations of motion".

**Track.** Origin at the track start, arc length s in [0, L]; track angle phi(s)
above horizontal, tangent t_hat = (cos phi, sin phi), normal n_hat = (-sin phi,
cos phi), signed curvature kappa = dphi/ds (positive curving up), z(s) the height above
the track start (`assist/base.py`, `TrackGeometry`; `assist/track.py`,
`StraightTrack`: phi constant, kappa = 0, z = s sin phi). A vertical silo has
phi = pi/2, z = s and starts at altitude exit_altitude - L (a buried silo whose mouth
is the datum starts at -L; `track_start_altitude_m` is reported). Flat local frame with
the constant effective gravity

    g_eff = mu / R_E^2 - omega_p^2 R_E        (`g_eff_track(omega_p)`)

which is 9.7982855 m/s^2 for omega_p = 0 (Phase 1) and 9.7720917 m/s^2 for the 28.5 deg
east launch of Phase 2 (omega_p = 6.408435e-5 rad/s). Coriolis (~0.01 m/s^2 at 77 m/s)
is neglected. Both are stated in every assumptions list.

**Internal clock.** t = 0 at push start (silo) or hold-down release (pad); ignition
times are absolute on this clock; reports quote t - t_release.

## 1-D ascent state and equations of motion

Module: `dynamics.py` (`VerticalDynamics1D`, `VerticalParams`, `rhs_vertical`). The
state is named by `VERTICAL_LAYOUT` (a `StateLayout`; no integer index is written
anywhere else):

    y = [z_m, v_mps, m_kg, J_vac_mps, J_grav_mps, J_alt_mps, J_bp_mps, J_steer_mps]

With sigma = `v_sign` (+1 rising, -1 falling; fixed per phase; at v = 0 the planner
sets it from the net acceleration, see "Phases and events"), the vacuum
thrust T_vac(t) of the stage's `ThrustSchedule`, the delivered thrust
T = max(0, T_vac(t) - p_amb A_e) (p_amb = 0 in Phase 1: no atmosphere in flight, so the
clamp and J_bp are hooks for Phase 2), c = g0 Isp_vac and g = g(r_datum + z):

    dz/dt       = v
    dv/dt       = T/m - g
    dm/dt       = -T_vac / c                  (mass flow follows the vacuum thrust)
    dJ_vac/dt   = T_vac / m
    dJ_grav/dt  = g sigma
    dJ_alt/dt   = (g - g_ref) sigma            altitude part of the gravity loss (<= 0 above
                                               ground while rising; sign flips with sigma)
    dJ_bp/dt    = (T_vac - T) / m              identically 0 while p_amb = 0
    dJ_steer/dt = (T/m)(1 - sigma)             psi = 0 rising, psi = pi falling

T_vac(t) is zero when the phase has no schedule (coast, fall), before ignition, and for
a failed ignition; the schedule is not capped by the propellant on board, so every burn
is ended by the `propellant` event (stack mass minus stack dry mass crossing zero
downward). g_ref is the reference gravity (mu / R_E^2 in runs) that splits the gravity
loss into a duration part g_ref * integral(sigma dt) and the altitude part J_alt.

The loss quadratures are integrated as ODE states rather than by trapezoid on the
samples: on samples the identity below closes only to ~1e-3 m/s; as states it closes to
rounding, so the 0.01 m/s budget test catches real bugs. Along a phase,
d|v|/dt = sigma (T/m - g) = T_vac/m - g sigma - (T/m)(1 - sigma) - (T_vac - T)/m, so

    |v_f| - |v_0| = J_vac - J_grav - drag - J_steer - J_bp,   drag = 0 in Phase 1,

which is CLAUDE.md's loss identity; the accounting from release onward, across phases,
is the subject of the losses section added with the planner.

What the identity does not check: sigma is fixed per phase, so whenever v_0 and v_f
share a sign the identity reduces to the signed identity v_f - v_0 = integral(T/m - g)
dt and closes to rounding even if v changed sign inside the phase (sigma wrong for part
of it; measured: a TWR < 1 burn from rest that sinks 7.6 km and then rises to burnout
closes to 6.8e-13 m/s with J_grav = g t_b). The disarm notes are then the only signal.
The engine cannot check this generically (`DynamicsModel` exposes only |v|), so the
planner or the losses section asserts on every phase's samples that
`spec.sigma * v >= -ATOL_MPS` (v never leaves the phase's half-line); `PhaseSpec`
itself refuses a sigma that disagrees with `params.v_sign`.

Validation (closed forms written in the tests, never taken from the package):

- `test_rocket_equation.py`: ConstantGravity(0), step and 2 s ramp on the toy stage
  (c = 3000 m/s exactly): v_f = c ln(m0/mf), t_b = m_p/mdot (+ t_ramp/2 for the ramp),
  J_vac = v_f; F9 stage 1: v_f = g0 * 311 * ln(542570/146870). Asserted at 1e-9
  relative (CLAUDE.md requires 1e-6); measured 2e-11.
- `test_vertical_burn.py`: ConstantGravity(g0), step at t = 0, v0 in {0, 30, 77, 300}:
  v_f = v0 + c ln(m0/mf) - g t_b, z_f = z0 + v0 t_b - g t_b^2/2 + c [t_b - (mf/mdot)
  ln(m0/mf)] (derivation in the test docstring), J_grav = g t_b, v > 0 throughout.
  Asserted at 1e-9 in v and 1e-8 in z; measured 3e-11 and 2e-11.

## Gravity

`Gravity` is a protocol: `g(r_m) -> m/s^2`, positive downward.

- `InverseSquareGravity(mu)`: g = mu / r^2 with r = R_E + z. The model of every run
  (CLAUDE.md: gravity in the ascent is mu / r^2). Obligation on the planner step:
  `sim.run` builds it from `MU_EARTH_M3S2` and nothing else constructs a gravity model
  from configuration.
- `ConstantGravity(g)`: analytic tests only; never constructed from configuration. The
  engine tests (`test_events.py`, `test_coast.py`) hand it to `integrate_phase`
  directly; the run path exposes it only through the injection point of
  `sim.simulate(...)`. It makes the rocket-equation,
  vertical-burn, coast and ignition-delay closed forms exact.

`G0_MPS2` converts Isp (c = g0 Isp) and defines the unit "g" for `_g` inputs and load
reports; it is never a gravity model.

Coast validation (`test_coast.py`, a COAST listing `apex` and `impact`, then a FALL
listing only `impact`, the planner pattern, so the disarm backstop is never engaged and
no note is produced): constant g gives apex z0 + v0^2/(2g) at t = v0/g and
the return to z0 at 2 v0/g with |v| = v0. Under mu / r^2 the motion is a radial Kepler
orbit: specific energy v^2/2 - mu/r is conserved at every sample (asserted 1e-10
relative, measured 2e-13), 1/r_a = 1/R_E - v0^2/(2 mu) gives the apex (asserted 1e-5 m;
measured 1e-6 m at 209 km. That residual is the joint error of the step sequence and
the dense-output event root, not a tolerance floor of the altitude state, and it is
insensitive to the altitude atol alone: with the default atol_z = 1e-6 m it is
-9.9e-7 m at rtol 1e-10 and -7.2e-7 m at rtol 1e-12; tightening only atol_z to 1e-9 m
at rtol 1e-10 makes it -4.4e-6 m; tightening both to 1e-12 / 1e-9 brings it to
-9.6e-8 m, and 1e-13 / 1e-12 to +7.5e-8 m; at v0 = 76.7 m/s it is -4e-10 m in every
setting. The convergence test therefore compares altitude changes with an absolute
allowance of that order, `ATOL_M`, as well as relatively), and with a = r_a/2, cos E0 = 1 - R_E/a, t_up = sqrt(a^3/mu) [pi - (E0 - sin E0)]
(asserted 1e-9 relative, measured 1e-12 and rtol-dependent), the vehicle is back at
R_E after 2 t_up with |v| = v0; v0 = 76.707 (the README silo exit speed; apex
300.27 m) and 2000 m/s.

**Phase 2 note (recorded here, decided in Phase 2).** With Earth rotation on, the
planar ascent state [r, theta, v_r, v_theta, m] keeps its angular momentum h = r
v_theta constant as long as nothing acts tangentially (radial thrust, no drag), so the
radial equation reduces exactly to one dimension: dv_r/dt = h0^2/r^3 - mu/r^2 with h0
= omega_p r_release^2 (the angular momentum the release mapping adds when it puts
omega_p r into the downrange component; a vertical exit adds nothing else). The exact
1-D reduction is therefore

    g = mu/r^2 - h0^2/r^3,   h0 = omega_p r_release^2,

which at the release radius equals the track's g_eff = mu/R_E^2 - omega_p^2 R_E, so
the track and the 1-D flight stay continuous at the mouth with rotation on, while
away from it the centrifugal relief falls as 1/r^3 rather than growing as omega_p^2
r. The same conservation gives the Earth-relative velocity a tangential component
v_rel,theta = h0/r - omega_p r = omega_p (R_E^2/r - r), westward above the release
radius: about -17 m/s at the 135 km stage-1 burnout for omega_p = 6.41e-5 rad/s
(28.5 deg, east), which lengthens |v_rel| over v_r by 0.06 m/s and tilts gamma_rel
by 0.37 deg. Inertially radial thrust is therefore not thrust along v_rel (the
gravity-turn law CLAUDE.md prescribes and the reference direction of the loss
identity): the reduction is exact for inertially radial thrust only, a cross-check
of the planar model rather than a substitute for it. CLAUDE.md's loss accounting folds the centrifugal term into g_eff = mu/r^2 -
omega_p^2 r, the same thing evaluated with the instantaneous rate. Phase 1 runs
h0 = 0 (omega_p = 0). Whether the 1-D model is kept as the cross-check of the planar
model with this g, and how the rotating-frame loss quadratures carry the term, is
decided in Phase 2 together with those quadratures. Build step 20 implements it as a
test: `H0Gravity(mu, h0)` is this g, the planar quadratures carry the centrifugal term
in g_eff = mu/r^2 - omega_p^2 r ("2-D loss identity"), and `test_h0_reduction` checks
the reduction ("Planar reductions"). The planner-level reduction of the pad and
silo_cold runs is `test_planner_reduces_to_the_vertical_planner` (build step 21).

## Planar ascent state and equations of motion

Module: `dynamics.py` (`PLANAR_STATE_NAMES`, `PLANAR_LAYOUT`, `planar_kinematics`,
`PlanarKinematics`, `SteeringLaw`, `PlanarParams`, `planar_forces`, `PlanarForces`,
`rhs_planar`, `planar_observables`, `PlanarDynamics2D`, `vacuum_atmosphere`, and the
test-only `H0Gravity`); `orbit.py` for elements ("Orbital elements and the circular
target"). Tests: `tests/test_planar_dynamics.py`, `tests/test_orbit.py`,
`tests/test_planar_reductions.py`. This is the right-hand side of the `planar_2d`
model (build step 20); the planner that strings its phases together is
`phases/planar.py` (hold, release, rise, kick, gravity turn, staging and the staging
coast since build step 21, "Stage-1 guidance and events (planar)"; the stage-2 burn
and insertion since build step 22, "Stage 2 and insertion (planar)"); experiments run
it through the pipeline since build step 24 (`sim.run_planar`), which emits its
assumptions (`sim.PLANAR_ASSUMPTIONS`, "Assumptions", planar block).

**Frame.** Planar Earth-centred inertial, in the plane of the launch site and the launch
azimuth; polar coordinates (r, theta) with theta increasing downrange. theta = 0 is the
site meridian at the flight-start time t_fs (release, or the liftoff root when that is
later; set by the planner, "Planar release map"). Earth is a sphere of radius R_E: the altitude
is h = r - r_datum with r_datum = `R_EARTH_M` in runs (`PlanarParams.r_datum_m`; a huge
radius R in the flat-Earth tests), geometric, and it is the altitude the atmosphere is
evaluated at. Because the state carries r = R + h, h is resolved to ulp(R) at best:
1.9e-9 m at R = 1e7 m, 1.2e-4 m at R = 1e12 m and 1.6e-2 m at R = 1e14 m. A flat-Earth
test therefore uses the smallest R it can (with zero gravity any R is flat; R <= 1e7 m
or R_E): the step-20 review measured the max-Q time t* of the exponential-atmosphere
closed form 3.5e-4 s off at R = 1e9 to 1e12 m, against 1.6e-6 s at R = 1e7 m.

**State** (`PLANAR_LAYOUT`; indices are derived from the names, never written):

    y = [r_m, theta_rad, v_r_mps, v_theta_mps, m_kg,
         J_vac_mps, J_grav_mps, J_alt_mps, J_drag_mps, J_steer_mps, J_bp_mps]

v_r and v_theta are the inertial radial and horizontal velocity components. The six
quadratures are the terms of the 2-D loss identity (next section); the 1-D names are
kept for the five shared terms, so a loss budget reads both models by name. Absolute
tolerances come from the suffixes (`atol_for`): 1e-6 m (inert for r, see
"Integrator"), `ATOL_RAD` = 1.5678e-13 rad, 1e-9 m/s, 1e-6 kg.

**Earth-relative kinematics** (`planar_kinematics`). The air co-rotates with the planar
rate omega_p, so the velocity relative to it has the local components

    w = v_r   (radial, up),     u = v_theta - omega_p r   (horizontal, downrange),
    V = |v_rel| = hypot(w, u),  sin gamma_rel = w/V,  cos gamma_rel = u/V.

gamma_rel is the Earth-relative flight-path angle above local horizontal; its value
atan2(w, u) is reported only (`planar_observables`, in (-pi, pi], not unwrapped; the
reported time series and events are unwrapped per run, amendment 14, "Reporting
definitions (planar)"), and the RHS uses the
sine and cosine. The local (radial, horizontal) frame is the same whether the velocity
is inertial or Earth-relative; only the horizontal component differs by omega_p r.
**Fallback:** when V < `V_REL_EPS_MPS` (1e-9 m/s: a vehicle at rest on the pad, where
v_theta = omega_p R_E and V = 0 exactly), sin gamma_rel = 1, cos gamma_rel = 0 and
v_hat_rel = r_hat (local vertical), as CLAUDE.md prescribes.

**Equations of motion** (`rhs_planar`). The thrust acts along the unit vector
e = (e_r, e_theta) that the phase's steering law returns (pitch p = atan2(e_r, e_theta)
above local horizontal); the drag along -v_hat_rel = -(sin gamma_rel, cos gamma_rel):

    dr/dt       = v_r
    dtheta/dt   = v_theta / r
    dv_r/dt     = v_theta^2 / r - g(r) + (T e_r - D sin gamma_rel) / m
    dv_theta/dt = -v_r v_theta / r + (T e_theta - D cos gamma_rel) / m
    dm/dt       = -T_vac(t) / c,        c = g0 Isp_vac

    T = max(0, T_vac(t) - p(h) A_e)     while a schedule is attached (0 before ignition
                                        and for a failed ignition, as in 1-D)
    D = q cd_scale C_D(M) A_ref,  q = 0.5 rho(h) V^2,  M = V / a(h)

with (p, rho, a) from `PlanarParams.atmosphere(h)` (`ambient_scalar` in runs; the
clamp and the table are "Atmosphere, drag and back-pressure in flight"), the mass flow
following the vacuum thrust, and `thrust_terms` shared with the 1-D RHS. In vacuum
(`vacuum_atmosphere`: p = rho = 0 and a = inf, so M = 0 and D = 0 exactly) and with
`drag = None` the drag is zero. g(r) is the `Gravity` model: mu/r^2
(`InverseSquareGravity`) in runs; `ConstantGravity` and `H0Gravity` only in analytic
tests. The -v_r v_theta/r and v_theta^2/r terms are the polar-coordinate terms of an
inertial frame; there are no Coriolis or centrifugal terms in the dynamics (the frame
is inertial), rotation enters only through the air (u, hence D, M, q and the angles)
and through the loss bookkeeping (g_eff). A circular orbit is an equilibrium of these
equations with any wrong v_theta term, which is why the orbit test is elliptical.

**Steering laws** (`SteeringLaw` protocol; the run laws `Radial`, `FixedTilt` and
`AlongVrel` live in `guidance.py` since build step 21, "Stage-1 guidance and events
(planar)"; the stage-2 `LinearTangent` since build step 22, "Stage 2 and insertion
(planar)"). `direction(t, y, kin)` returns the
unit (e_r, e_theta) given the state and its `PlanarKinematics`; `along_vrel` is True
exactly for the law that thrusts along v_rel (the gravity turn), for which the RHS sets
cos psi = 1 and the steering-loss rate to exactly 0 rather than evaluating
1 - cos psi from a rounding-level cos psi. psi is the angle between thrust and v_rel,
cos psi = e_r sin gamma_rel + e_theta cos gamma_rel. The RHS trusts |e| = 1. A phase
with a thrust schedule must carry a law (`PlanarParams` refuses otherwise); an
unpowered phase has none, and its thrust direction is reported along v_rel by
convention (the thrust is zero).

**Parameters** (`PlanarParams`, frozen): gravity, omega_p_rads, g_ref_mps2, schedule
(or None), drag (a `DragModel`, or None), atmosphere, steering (or None), r_datum_m.
`planar_forces(t, y, p)` returns every force-level term the RHS uses
(`PlanarForces`: T_vac, T, mdot, e, D, q, M, V, cos psi, sin and cos gamma_rel, g_eff,
g, w, u, p, rho, a), and `planar_observables(t, y, p, t_fs)` the reported quantities
of one instant: alt_m, downrange_m = r_datum (theta - omega_p (t - t_fs)) (the
Earth-fixed arc; the hold rows of the planner report 0), speed_rel_mps,
speed_inertial_mps, gamma_rel_rad, pitch_rad, psi_rad, q_pa, mach, thrust_N,
thrust_vac_N, drag_N, g_eff_mps2. `PlanarDynamics2D(omega_p_rads, r_datum_m)` is the
`DynamicsModel`: altitude = r - r_datum and speed = |v_rel| (the speed of the loss
identity), for a state or a series. Both fields are required (no default: a wrong
omega_p would shift |v_rel| by up to omega_p R_E = 409 m/s at the pad without raising,
because the RHS reads the params and speed() reads the model);
`PlanarDynamics2D.for_params(p)` builds the model from the phase parameters and
`check_params(p)` refuses parameters that disagree, once per phase rather than per RHS
call. Cost of `rhs_planar` with the ICAO atmosphere and
the Braeunig table: 4.6 us per call on the development machine (the plan's budget).

**Rotation.** omega_p = omega_E cos(lat) sin(az) (`planar_rotation_rate`, from the site
block; 6.408435e-5 rad/s at 28.5 deg, az 90, so omega_p R_E = 408.7388 m/s; 465.1011
m/s on the equator). The planar model is exact for the inertial dynamics, the
inclination and the site velocity of an az 90 launch at i = lat; the air's out-of-plane
velocity omega_E sin(lat) r sin(theta) is neglected (0.35 m/s at 10 km downrange,
about 3.5 m/s at 100 km), so the planar |v_rel| at a 200 km circular insertion,
7,362.706 m/s, is about 0.3 m/s below the 3-D value. It is exact for an equatorial east
launch and an approximation otherwise (CLAUDE.md). The centrifugal relief enters the
loss accounting through

    g_eff(r) = g(r) - omega_p^2 r,    g_ref = g_eff(R_E) = 9.7720917 m/s^2 (28.5 deg, east;
                                      9.7982855 m/s^2 with rotation off)

which at r = R_E equals the track's constant g_eff ("Frames and datum").

**Validation** (closed forms written in the tests):

- `test_orbit.py::test_elliptical_orbit_ten_revolutions` (CLAUDE.md's orbit test), DOP853
  and RK45 at rtol 1e-10: e = 0.3 from apoapsis, r_p = R_E + 500 km, so a = 9,825,910 m,
  r_a = 12,773,683 m, v_theta = sqrt(mu (1 - e)/r_a), rotation on (it must not act in
  vacuum). E = -mu/(2a) and h = sqrt(mu a (1 - e^2)) at every step within 1e-8
  (measured 3.6e-11 and 9.6e-12 for DOP853, 2.0e-11 and 1.2e-10 for RK45); the period
  2 pi sqrt(a^3/mu) = 9,693.2665 s from the ten periapsis events (v_r crossing zero
  upward) within 1e-9 (DOP853) and 1e-8 (RK45) (measured 2.9e-11 and 1.4e-11); every
  periapsis event at r_p (1e-8); theta after 10 periods = 20 pi within 1e-7 rad
  (measured 5.3e-10 and 6.5e-11). nfev 5,479 (DOP853) and 11,053 (RK45).
- `test_orbit.py::test_radial_coast_constant_g_apex` and `::test_radial_coast_inverse_square_apex`,
  v0 in {300, 3000} m/s: apex v0^2/(2 g_test) at t = v0/g_test, and 1/r_max =
  1/R_E - v0^2/(2 mu) with v^2/2 - mu/r conserved at every step (1e-10); apex altitudes
  within 1e-9 relative (measured at most 6.7e-13).
  `::test_non_radial_coast_conserves_energy_and_angular_momentum`: a 5 km/s launch
  40 deg above horizontal with rotation on, E and h = r v_theta at every step within
  1e-10 down to the start radius, and the return speed equals the launch speed.
- `test_planar_dynamics.py::test_rocket_equation_2d_along_velocity` (CLAUDE.md's rocket
  equation in 2-D): mu = 0 (ConstantGravity(0)), omega_p = 0, the along-v law from a
  start 30 deg above horizontal, v0 in {1e-3, 100, 3000} m/s: V_f - V_0 = c ln(m0/m_f),
  J_vac equal to it, J_steer and J_grav exactly 0, and the end point on the start line
  at the distance v0 t_b + c [t_b - (m_f/mdot) ln(m0/m_f)] (all 1e-9 relative; CLAUDE.md
  asks 1e-6).
- `::test_rhs_components_match_the_equations_of_motion`: every row of `rhs_planar` on
  300 seeded states against the equations above written in the test (1e-12 of the
  largest term of the row).

## 2-D loss identity

Module: `dynamics.py` (the quadrature rows of `rhs_planar`); `losses.py` (the budget
over a run, `loss_budget(phases, layout, speed)`: the per-phase increments of the
quadratures, J_drag when the layout carries it, and |v_rel| at the two ends from the
model's `speed`, `PlanarDynamics2D.speed`; the 1-D call, without `speed`, reads
|v_mps| and is unchanged bit for bit; and `pointwise_dVdt(t, y, p)`, both sides of
the identity's rate at one state with their scale); the rocket-equation closure is
"Rocket-equation closure (planar)". Tests:
`tests/test_planar_dynamics.py::test_pointwise_speed_identity` (an inline form of the
identity's rate), `tests/test_loss_identity_2d.py::test_pointwise_dVdt_along_the_recorded_pad`
(`pointwise_dVdt` itself),
`tests/test_planar_events.py::test_loss_identity_closes_to_stage2_ignition`,
`tests/test_loss_identity_2d.py` (CLAUDE.md's full-ascent budget).

With the acceleration a = (T e - D v_hat_rel)/m, the Earth-relative components change
as

    w' = v_r'                   = v_theta^2/r - g + a_r
    u' = v_theta' - omega_p r'  = -w v_theta/r + a_theta - omega_p w

so, with v_theta = u + omega_p r,

    w w' + u u' = w [v_theta^2/r - g - u v_theta/r - omega_p u] + a . v_rel
                = w [v_theta^2/r - g - (v_theta - omega_p r) v_theta/r
                     - omega_p (v_theta - omega_p r)] + a . v_rel
                = w (-g + omega_p^2 r) + a . v_rel

(the two omega_p v_theta Coriolis terms cancel: Coriolis does no work in the rotating
frame). With a . v_rel = (T cos psi - D) V / m and V' = (w w' + u u')/V:

    dV/dt = -g_eff sin gamma_rel + (T cos psi - D)/m,        g_eff = g - omega_p^2 r
    T cos psi = T_vac - (T_vac - T) - T (1 - cos psi)

    =>  V_f - V_0 = J_vac - J_grav - J_drag - J_steer - J_bp

    dJ_vac/dt   = T_vac / m                    dJ_drag/dt  = D / m
    dJ_grav/dt  = g_eff sin gamma_rel          dJ_steer/dt = (T/m)(1 - cos psi)
    dJ_alt/dt   = (g_eff - g_ref) sin gamma_rel  (the altitude part of J_grav)
    dJ_bp/dt    = (T_vac - T) / m

which is CLAUDE.md's identity with v_rel, the gravity loss integrated against
g_eff sin gamma_rel and the back-pressure term keeping it exact while the thrust is
clamped at zero. The quadratures are ODE states integrated with the motion, so over
any phase the identity closes to rounding; accumulation starts at t_fs (release) and
mass maps (staging, fairing) leave V and the quadratures unchanged (`map_staging_planar`
since build step 21; the FAIRING map `map_fairing_planar` since build step 22).
At the fallback (V < `V_REL_EPS_MPS`) the quadrature sum is T e_r/m - g_eff - D/m
(v_hat_rel taken as r_hat). It is the one-sided limit of dV/dt from rest when the
relative acceleration at rest is radial and upward: on the pad w = u = 0 and, with
radial thrust, the tangential force is zero; for T e_r/m > g_eff + D/m, which the
liftoff root guarantees in runs, V grows as (T/m - g_eff) t along +r_hat. It is not the
limit otherwise. A start from rest that sinks (T/m < g_eff) moves along -r_hat, where
dV/dt = g_eff - T/m is the negative of the fallback sum, and a non-radial law at V = 0
gives dV/dt = |a_rel|, not its radial projection. Since the fallback holds for a single
instant, the cost is one RHS stage: the step-20 review measured a closure error of
9.9e-9 to 1.04e-8 m/s for a sinking start (T = 0.5 m g_eff, with and without rotation),
not growing with the phase length. No run reaches either case, because the kick needs
V >= v_k and liftoff is the root of T = m g_eff. Whenever w/V could jump
inside a step (through an apex with thrust off) the planner splits the phase there
(`ev_radial_apex` in every coast, and the apex/turnaround split of a lit vertical rise;
"Stage-1 guidance and events (planar)"), as the 1-D planner splits at apex. Measured
closure of the planner (gate fork, rtol 1e-10): about 1e-9 m/s from the flight start
to MECO and to stage-2 ignition, pad and silo alike.

**Reduction to 1-D.** With omega_p = 0, v_theta = 0 and e = (1, 0): u = 0, V = |w|,
sin gamma_rel = sigma = sign(v_r) (+1 at the fallback), cos psi = sigma, so
dJ_grav = g sigma, dJ_alt = (g - g_ref) sigma, dJ_steer = (T/m)(1 - sigma) and
dJ_drag = 0 with no drag: the 1-D quadratures of "1-D ascent state and equations of
motion" row for row. The 1-D model fixes sigma per phase while the planar model reads
it from the state, which is the same thing inside a phase that does not cross v = 0.

**Validation.** `test_pointwise_speed_identity`: on 1,000 seeded states (rotation 0,
28.5 deg east and equatorial; the ICAO atmosphere and the Braeunig drag; stage 1 of
the gate fork inside the back-pressure clamp window of its ramp and at full thrust,
stage 2, unlit and unpowered phases; radial, fixed-tilt, along-v_rel and
linear-tangent laws; one state in ten with V < 1e-9 m/s), (w w' + u u')/V from the
kinematic rows of the RHS equals the quadrature sum from its J rows and the closed
form -g_eff w/V + (T cos psi - D)/m written in the test, within 1e-12 x max(T/m,
T_vac/m, g_eff, D/m, |w w'|/V, |u u'|/V) (measured 5.7e-16 and 7.1e-16), and at the
fallback the sum equals T e_r/m - g_eff - D/m (measured 1.8e-16). T_vac/m joins the
plan's scale list because inside the clamp T = 0 while T_vac/m and the back-pressure
rate are the largest terms. The test asserts that every regime (clamped, lit, unlit,
fallback, drag, rotation) is visited more than ten times.
`::test_fallback_is_the_one_sided_limit`: on the pad with rotation, radial thrust
2e4 N on 1,000 kg, the sum and dv_r/dt equal T/m - g_eff and dv_theta/dt is 0; at
w = 1e-6 m/s, u = 0 the ordinary identity gives the same value; integrated for 1e-3 s
from the pad, V equals the rocket closed form c ln(m0/(m0 - mdot h)) - g_eff h
(1e-9 relative), so V/h -> T/m - g_eff, and the identity closes to 1e-14 m/s.

**Full ascent** (CLAUDE.md's required loss-budget test, `test_loss_identity_2d.py`).
`loss_budget` over every ascent phase of a recorded run (rtol 1e-10, dense output on),
gamma* = 20 deg with delta solved and the LTG pair solved: |V_f - V_0 - (J_vac - J_grav
- J_drag - J_steer - J_bp)| below `checks.identity_tol_mps` = 1e-5 m/s (CLAUDE.md asks
0.01). Measured: 5.5e-9 m/s for the pad to insertion (hold, rise, kick, turn, the 11 s
staging coast, the fairing drop, LTG), 8.1e-9 for silo_cold, 8.3e-9 for silo_hot_full,
8.8e-9 for the silo lit at release with a 10 s ramp (the delivered thrust clamped at
zero for the first 0.75 s of flight, where J_bp grows exactly as J_vac: 1e-12
relative), and -1.1e-9 for silo_failed through its apex to impact (no thrust terms;
76.71 m/s up, 76.60 m/s down: 0.146 m/s of drag, -0.037 m/s of net gravity loss). Every
inserted run ends at V_rel = v_c - omega_p r_t = 7,362.706 m/s.

## Planar reductions

Test: `tests/test_planar_reductions.py` (RHS level, build step 20; the planner-level
reduction of the pad and silo_cold runs to burnout, build step 21, amendment 11, is the
last paragraph).

**No rotation, radial.** With omega_p = 0, v_theta = 0, radial thrust, no drag and a
constant ambient pressure (the 1-D model's constant p_amb), the planar state
[R_E + z, 0, v, 0, m, J..., J_drag = 0] obeys the 1-D equations row for row:
dr = dz, dv_r = dv, dm and each quadrature equal the 1-D row, and dtheta = dv_theta =
dJ_drag = 0 exactly. `test_rhs_rows_equal_the_vertical_rows` checks 500 seeded states
(z from -100 m to 300 km, v of either sign and 0, the gate stage-1 ramp from before
ignition to full thrust, p_amb 0 or 101,325 Pa) at 1e-15 relative (the rows are
bit-equal in practice). `test_integrated_stage1_burn_matches_the_vertical_model`
integrates the gate stage 1 released at 77 m/s and lit at release (2 s ramp, split at
the kink; 101,325 Pa, so the clamp books J_bp) to burnout in both models: r - R_E, v_r,
m and every quadrature agree within 1e-10 relative (measured: altitude 2.6e-9 m at
208 km, v 4.1e-12, the quadratures at most 2.8e-12). The constant-g test
(`test_vertical_burn_constant_g_through_the_planar_rhs`) is CLAUDE.md's vertical burn
under ConstantGravity(g_test) through the planar RHS, v0 in {0, 30, 77, 300} m/s:
v_f = v0 + c ln(m0/mf) - g t_b and z_f = v0 t_b - g t_b^2/2 + c [t_b - (mf/mdot)
ln(m0/mf)] within 1e-10 relative (measured 2.4e-11 to 3.2e-11 in v, -3.2e-6 to -4.5e-6 m in z at 161-209 km, the r-form
error of "Integrator"), J_grav = g t_b.

**Rotation, radial thrust (the h0 reduction).** This is the recorded Phase 2 note of
"Gravity", now implemented as a test. With inertially radial thrust and no drag there is
no tangential force, so h = r v_theta = h0 = omega_p R_E^2 is conserved from a pad start
(r = R_E, v_theta = omega_p R_E, V = 0), and the radial equation is

    dv_r/dt = h0^2/r^3 - mu/r^2 + T/m,

the 1-D model with g = mu/r^2 - h0^2/r^3 (`H0Gravity(mu, h0)`, test-only; it equals
g_eff at R_E, so the track and the flight stay continuous at the mouth), while the air
moves relative to the vehicle: u = h0/r - omega_p r = omega_p (R_E^2/r - r) < 0
(westward) above the pad. `test_h0_reduction` (28.5 deg east and equatorial rates, the
toy stage with A_e = 0, 160 s burn to about 162 km): r v_theta = h0 at every step
(1e-12; measured 3e-15), u equal to the closed form (1e-11 of omega_p R_E; measured
3e-15), and altitude, v_r and m equal to the 1-D run under `H0Gravity` at 16 common
segment ends (1e-10 relative with a 1e-6 m floor; measured 1.6e-7 m and 1.2e-12). The
two gravity losses differ by construction (the 1-D run books mu/r^2 - h0^2/r^3 against
sigma = 1, the planar run g_eff sin gamma_rel with g_eff = mu/r^2 - omega_p^2 r), and
the planar J_steer is positive because u != 0 tilts v_rel away from the radial thrust
(0.059 m/s at 28.5 deg, 0.077 m/s on the equator, u_f = -20.6 and -23.4 m/s); the
planar identity closes (measured 2e-12 m/s). This reduction is exact for inertially
radial thrust only: the run's gravity turn thrusts along v_rel, so it is a cross-check
of the planar model, not a substitute for it.

**Planner level** (amendment 11). `test_planner_reduces_to_the_vertical_planner` flies
the gate stage 1 through `PlanarPlanner` with no drag (`aero` None), no rotation, a
constant 101,325 Pa (the 1-D model's p_amb, so the hold-down balance, the track and the
thrust clamp book the same back-pressure), mu/r^2 and the vertical-only guidance
(`GuidanceSpec.vertical_only()`: radial thrust to burnout), against `VerticalPlanner`
with the same pad pressure and g_eff = mu/R_E^2, for the pad (lit 2 s before release)
and silo_cold (3 g, 100 m, lit 0.5 s after release: push, release, 0.5 s coast, ramp,
burn). The event names, times and phase kinds agree (COAST_PRE_IGN for COAST_PRE_IGN,
VERTICAL_RISE for BURN), and at burnout t, r - R_E, v_r, m and every loss quadrature
equal the 1-D values within 1e-10 relative (altitude with the 1e-6 m floor), with
theta, v_theta and J_drag exactly 0. It runs at rtol 1e-12: at 1e-10 each model's own
global error at the silo_cold burnout (114 km) is up to 5.0e-5 m in altitude (the
1-D run; the planar run 8.3e-7 m) against its rtol-1e-13 reference, so the two differ
by 4.2e-10 relative in altitude and 1.0e-10 in speed; at 1e-12 they differ by 3.1e-11
and 1.3e-11 (pad: 4.6e-13 and 1.5e-13).

## Orbital elements and the circular target

Module: `orbit.py` (`TargetOrbit`, `OrbitElements`, `orbit_elements`). Test:
`tests/test_orbit.py`. Frame: planar ECI; the inertial velocity (never v_rel).

- `TargetOrbit(r_m)`: a circular target; `energy_Jkg(mu)` = E* = -mu/(2 r_t) and
  `v_circ_mps(mu)` = sqrt(mu/r_t). For the 200 km reference, r_t = 6,578,137 m:
  E* = -30,297,365.5 J/kg and v_c = 7,784.2617 m/s (the planar V_rel at insertion is
  v_c - omega_p r_t = 7,362.7061 m/s at 28.5 deg, `speed_rel_mps(mu, omega_p)`;
  `altitude_m(r_datum)` = r_t - r_datum).
- `specific_energy_Jkg(r, v_r, v_theta, mu)` = (v_r^2 + v_theta^2)/2 - mu/r, the
  energy of the insertion cutoff ("Stage 2 and insertion (planar)").
- `orbit_elements(r, v_r, v_theta, mu)`: E = (v_r^2 + v_theta^2)/2 - mu/r, h = r v_theta,
  p = h^2/mu, and the eccentricity as the length of the eccentricity vector in the local
  frame, e = hypot(p/r - 1, h v_r/mu). That equals the plan's sqrt(1 + 2 E h^2/mu^2)
  exactly but keeps its relative accuracy near a circular orbit, where the square-root
  form cancels (at e = 2e-7, the insertion acceptance scale, it would carry an
  error of order 1e-9). r_p = p/(1 + e); r_a = p/(1 - e) for e < 1, else inf;
  a = -mu/(2E) (inf at E = 0, negative for a hyperbola). A radial state (h = 0) is the
  degenerate conic e = 1, r_p = 0, r_a = inf.

Validation: the e = 0.3 ellipse at four true anomalies (a, e, r_p, r_a, E, h within
1e-12; e equal to the square-root form within 1e-10); the 200 km target numbers
(E* within 0.05 J/kg, v_c within 5e-5 m/s); a circular state has e < 1e-15, and
v_r = 1e-3 m/s at r_t gives e = v_r/v_c within 1e-6 relative; a hyperbola (e > 1,
a < 0, r_a = inf) and the radial conic; bad inputs raise.

## Planar release map

Module: `phases/planar.py` (`planar_rest_state`, `release_state_planar`,
`map_release_planar`, `planar_prelude`). Test: `tests/test_release_planar.py`. Frame:
from the flat Earth-fixed track frame (x downrange along the launch azimuth, z up,
origin on the datum at the site) into the planar ECI frame of "Planar ascent state and
equations of motion", with theta = 0 at the site meridian at the flight start t_fs.

**Pad.** A vehicle at rest on the ground at altitude z above the datum is
`planar_rest_state`: r = R_E + z, theta = 0, v_r = 0, v_theta = omega_p r (the
ground's own velocity), the mass, every quadrature 0. On the pad (z = 0) its inertial
speed is omega_p R_E, 465.1011 m/s for an equatorial east launch and 408.7388 m/s at
28.5 deg east, and |v_rel| = 0 exactly (the kinematic fallback to local vertical).
The hold-down (the shared prelude run in `PLANAR_LAYOUT`, `hold_rhs_for`) changes only
the mass, so theta stays 0 and v_theta stays omega_p R_E through the hold: the hold
rows are Earth-fixed and theta = 0 is the site meridian at the liftoff root (the Phase
2 datum; no spurious downrange accrues on the pad).

**Exact general map** (`release_state_planar`, the Phase 3 seam for tilted and curved
tracks). An exit at altitude z_e and downrange offset x_e lies at the angle
theta_x = atan2(x_e, R_E + z_e) from the site, where the local vertical is tilted
downrange by theta_x. The flat-frame velocity sdot (cos phi, sin phi) (phi the track
angle above the site's horizontal) projects onto r_hat = (sin theta_x, cos theta_x)
and theta_hat = (cos theta_x, -sin theta_x):

    r = hypot(R_E + z_e, x_e),   theta = theta_x,
    v_r = sdot sin(phi + theta_x),   v_theta = sdot cos(phi + theta_x) + omega_p r

(the ground's velocity omega_p r added to the Earth-relative downrange component;
quadratures 0). So |v_rel| = sdot and the Earth-relative flight-path angle at release
is phi + theta_x. This is the sign plan section 5 derives (it rejects sin(phi -
theta_x)): the local horizontal at a downrange exit is rotated downrange, so the same
flat-frame velocity is steeper relative to it.

**Phase 2 assertion** (`map_release_planar`). Phase 2 releases from vertical tracks
only (the config refuses any other `angle_deg`): the map refuses an exit whose
downrange offset is unknown (`TrackExit.x_exit_m` None, a geometry without x(s)), not
zero, or whose angle is not pi/2 within `VERTICAL_TRACK_TOL_RAD`, and then writes the
vertical case exactly: r = R_E + z_e, theta = 0, v_r = sdot, v_theta = omega_p r. (The
general form at phi = pi/2 carries sdot cos(pi/2) = 4.7e-15 m/s of floating-point
horizontal speed at 76.7 m/s, which the exact form avoids.)

**Track rows.** The track push is the unchanged flat 1-DOF model ("Silo model") run by
the shared prelude with the planar prelude layout (`planar_prelude`): the hold state
before the push is `planar_rest_state` at the track start altitude, the track's
constant gravity is g_eff = g_ref = g(R_E) - omega_p^2 R_E (`dynamics.g_eff_track`
for mu/r^2), the ambient pressure is the constant p(z_exit), and the track events are
logged through the planar view of a vertical track state (r = R_E + z_start + z(s),
theta = 0, v_r = sdot, v_theta = omega_p r). No Coriolis on the track (~0.01 m/s^2 at
77 m/s) and no air drag in the vented shaft: both stated assumptions (plan section 5).
Under `constant_accel` the net acceleration is prescribed, so the omitted drag D would
be absorbed by the drive force: the release speed is unchanged, and the drive energy,
the peak drive power and the interface force are biased low, by int D v dt, D v_exit
and D. For the 3 g, 100 m silo at the gate fork (A_ref 10.52 m^2, C_D about 0.42 at
Mach 0.23, q = 3.6 kPa at the exit): D is about 16 kN at the exit, int D v dt = 0.5
rho C_D A_ref a^3 t_p^4 / 4 is about 0.8 MJ against about 2.2 GJ of drive work, and D
v_exit is about 1.2 MW against a peak drive power of about 1.7 GW (hand estimates, rho
at sea level). Plan section 5's "about 30 kN, a 0.05 to 0.2 m/s bias toward the
assist" used the 21.24 m^2 fairing section and a speed effect that a prescribed
acceleration does not have; it is replaced by this statement.

**Flight start.** t_fs is the release (a track) or the later of release and the
liftoff root (a pad); the loss quadratures start there at 0, and the planar view is
rebound to t_fs (`TraceBuilder.rebind_view`) so that the Earth-fixed downrange
r_datum (theta - omega_p (t - t_fs)) of every later row counts from the site.

**Earth-fixed downrange of a radial rise** (amendment 11; the Coriolis drift). With
inertially radial thrust and no drag there is no tangential force, so r v_theta =
h0 = omega_p R_E^2 is conserved from the pad and theta' = h0/r^2. The ground turns at
omega_p, so the Earth-fixed downrange rate is

    d(downrange)/dt = R_E (h0/r^2 - omega_p) = omega_p R_E (R_E^2/r^2 - 1) ~ -2 omega_p h:

a radially rising vehicle falls behind the rotating ground (drifts west). For a
constant radial acceleration a from rest, r = R_E + a t^2/2 and the integral has a
closed form,

    int_0^t ds/(R + b s^2)^2 = t / (2R (R + b t^2)) + atan(t sqrt(b/R)) / (2 R sqrt(R b)),
    b = a/2,

whose leading term is the flat-Earth Coriolis drift -omega_p a t^3/3, corrected by the
factor (1 - 0.9 h/R_E) at altitude h. `test_radial_rise_earth_fixed_downrange` flies
it through the planner (equatorial rate, a test gravity h0^2/r^3 + g_c that cancels
the centrifugal term so a = A - g_c exactly, v_k = 1500 m/s at about 147 s and 110 km):
the kick-trigger event's downrange is -777.82 m, equal to the closed form within
1.2e-8 (asserted 1e-7), its altitude within 1.4e-11 (asserted 1e-9), and the leading
term with the 0.9 h/R correction within (h/R)^2. On the gate pad the rise to the
50 m/s trigger lasts 12.3 s, so the drift before the kick is of order
omega_p a t^3/3: about 15 cm (-0.152 m at the kick trigger, 296 m up).

**Validation** (`test_release_planar.py`): the pad starts at omega_E cos(lat) R_E
(465.1 m/s equatorial, CLAUDE.md's release-mapping test; 408.7388 m/s at 28.5 deg) with
v_r = 0, V = 0 exactly and theta = 0 (1e-9 m/s absolute against omega_E cos(lat) R_E
computed in the test, as plan section 8 asks; 1e-4 m/s against the quoted digits;
exact otherwise), and the pad's release row reports gamma_rel = pi/2 (the fallback at
V = 0); a 3 g, 100 m vertical silo releases at t = sqrt(2L/a) with v_r = sdot =
sqrt(2 a L) = 76.71 m/s and v_theta = omega_p R_E (1e-9 relative); the general map
against a Cartesian projection written in the test for four exits (x_e up to 50 km,
phi from 10 to 89 deg; 1e-12 relative), with |v_rel| = sdot and gamma_rel = phi +
theta_x; the vertical map equal to the general one at x_e = 0 (1e-13 m/s), at the
datum and at an exit 500 m above it (r = R_E + z_e and v_theta = omega_p (R_E + z_e)
exactly), and the rest state its sdot = 0 case; the refusals; the radial-rise drift above; and the datum of
flight rows after a track start: the cold silo's ignition row, 0.5 s after release,
shows the classical Coriolis drift of a vertical throw, -omega_p (v0 t^2 - g t^3/3) =
-1.20 mm with g = g_ref (1e-3 relative; measured 1.2e-4, the drag), where a view bound
to push start would show about -1,066 m (R_E omega_p t_release).

## Stage-1 guidance and events (planar)

Modules: `guidance.py` (the steering laws `Radial`, `FixedTilt`, `AlongVrel`,
`GuidanceSpec`, `GuidanceFailure`), `phases/planar.py` (`PlanarPlanner`, `PlanarView`,
`PlanarEnvironment`, `FlightStart`, `KickPoint`, `Handover`, `map_staging_planar`,
`fmh_rate_W_m2`, `resume_builder`), `phases/engine.py` (the planar event factories
`ev_ground`, `ev_radial_apex`, `ev_radial_turnaround`, `ev_kick_start`,
`ev_kick_aligned`, `ev_time`). Tests: `tests/test_planar_events.py`,
`tests/test_gravity_turn.py`, `tests/test_guidance.py`, `tests/test_planar_reductions.py`
(planner level). Frame: planar ECI; every angle and speed below is Earth-relative
(v_rel) unless it says inertial. The stage-2 burn (linear-tangent steering, the energy
cutoff, the fairing event, insertion) is "Stage 2 and insertion (planar)".

**Steering laws** (`dynamics.SteeringLaw`; unit thrust direction (e_r, e_theta) in the
local frame, pitch p = atan2(e_r, e_theta) above local horizontal):

| Mode | Law | (e_r, e_theta) | pitch | J_steer rate |
|---|---|---|---|---|
| VERTICAL_RISE | `Radial` | (1, 0) | pi/2 | (T/m)(1 - sin gamma_rel): small, the air drifts past the rise with rotation |
| KICK | `FixedTilt(delta)` | (cos delta, sin delta) | pi/2 - delta | (T/m)(1 - cos psi) |
| GRAVITY_TURN | `AlongVrel` | (w, u)/V = (sin gamma_rel, cos gamma_rel) | gamma_rel | exactly 0 (`along_vrel`) |

The rise thrusts inertially radially, not along v_rel: on the pad v_rel = 0, and with
rotation the air drifts past a radially rising vehicle (u = omega_p (R_E^2/r - r) < 0
without drag, "Planar reductions"), so along v_rel would lean the rise west. At
V < `V_REL_EPS_MPS` `AlongVrel` falls back to radial. There is no lift and no
angle-of-attack aerodynamics, so the kick costs no aerodynamic penalty in the model; it
is reported through q-alpha and felt lateral g ("Max-Q and loads (planar)"; the
comparison flags q_alpha_above_baseline, "Reporting definitions (planar)").

**Guidance specification** (`GuidanceSpec`, from `guidance.kick` of the shared config
block): v_kick_mps (the trigger speed |v_rel|, 50 m/s shipped), kick_max_s (the kick's
time limit, 60 s) and kick_deadline_s (60 s after stage-1 ignition). Only the
hold_to_alignment kick exists. `GuidanceSpec.vertical_only()` (v_k = inf, no deadline)
flies the rise to burnout and exists for the planner-level reductions; it is never
built from a config.

**Stage-1 phases** (each a `solve_ivp` call; every flight phase that can reach the
ground lists the ground event `impact`: h - z_ground crossing downward, z_ground = 0 at
the pad and the silo mouth; a rising coast or rise lists the `apex` split instead,
which ends it before it could come down; lit phases are split at the thrust kinks with the ramp and lag `max_step` caps, and a
ramp end inside a flight phase is logged as `ramp_end`):

| Phase | RHS / law | Events (direction; all terminal) | Next |
|---|---|---|---|
| HOLD (pad) | the prelude in `PLANAR_LAYOUT`: mass only | `liftoff`: T(t, p(0)) - m g_ref (+), the delivered thrust at the pad pressure, g_ref = g(R_E) - omega_p^2 R_E | flight start (t_fs, theta = 0) |
| ASSIST (track) | the prelude's flat 1-DOF track, g_eff = g_ref, p = p(z_exit) | `track_end`, `propellant`, `drive_limit` | `map_release_planar`, flight start |
| COAST_PRE_IGN | unpowered (a release before ignition) | rising: `apex` (v_r, -), a split; falling: `impact`; t_end = t_ign | VERTICAL_RISE at ignition |
| VERTICAL_RISE | `Radial` | `propellant` (-); rising: `apex` as a split; falling: `impact` and `turnaround` (v_r, +) as a split; `kick_start` (+): min(V - v_k, w); `kick_deadline` (+): t - (t_ign + deadline) | KICK (with no rise at all when the trigger is already past at the first lit instant); GuidanceFailure `no_kick` at the deadline or at burnout before the trigger; status impact |
| KICK | `FixedTilt(delta)` | `propellant` (MECO), `impact`, `kick_end` (+): (u cos delta - w sin delta)/V = sin(beta_rel - delta), `kick_timeout` (+): t - (t_kick + kick_max) | GRAVITY_TURN; GuidanceFailure `kick_timeout` |
| GRAVITY_TURN | `AlongVrel` | `propellant` (MECO), `impact` | STAGING |
| STAGING (map) | `map_staging_planar`: m -= m_d1, plus the fairing F under rule `staging`, or under the heating rule when 0.5 rho V^3 is already below its limit at staging (logged `fairing`, with a flag); r, theta, v and every quadrature unchanged | | COAST_STAGING |
| COAST_STAGING | unpowered for stage 2's coast_before_ignition_s (11 s on the Phase 2 forks) | `apex` split while rising, `impact` while falling | COAST_PRE_IGN (stage 2 t_ign_s > 0), then the hand-over at stage-2 ignition |
| COAST (failed ignition) | unpowered, from release (stage 1) or the end of the staging coast (stage 2) | `apex` split, `impact` | end `apex` (stop at the apex) or `impact` (status impact) |

beta_rel = pi/2 - gamma_rel is the Earth-relative velocity's angle from local
vertical. The heating criterion uses V = |v_rel| and rho at h. Under the heating rule
the fairing stays on at staging unless the criterion is already met (at the MECOs
below, 58 to 73 km, 0.5 rho V^3 is 5e5 to 4e6 W/m^2 against the 1,135 W/m^2 limit);
the stage-2
burn drops it at the heating event ("Stage 2 and insertion (planar)"). The planar
mass bookkeeping never
uses the screening helpers `Vehicle.stack_mass_kg` and relatives beyond stage 1's own
burnout mass `stack_dry_mass_kg(0)` (which carries the fairing, as it must).

**Kick trigger at the first lit instant** (decision 5). The trigger g = min(V - v_k,
w) is positive exactly when the vehicle is faster than v_k relative to the air and
rising. It is judged from the first lit instant of free flight on. There the planner
evaluates g itself: when g > zero_tol (a release or an ignition already faster than
v_k while rising) it logs `kick_start` (phase KICK) and KICK starts at once, with no
VERTICAL_RISE phase; otherwise the trigger is listed in the lit VERTICAL_RISE phases.
Deciding it there, rather than letting a zero-length rise end at t0 through the
engine's already-past rule, leaves no engine note, so this nominal, pre-registered
case raises no run flag. The kick starts at
max(ignition, release, the first time V >= v_k with w > 0). The kick deadline counts
from stage-1 ignition, not from the flight start (amendment 13). On the gate
fork: the pad kicks 12.268 s after release (14.268 s after its ignition at -2 s); a
cold silo start (release at 76.7 m/s, lit 0.5 s later at 71.8 m/s) kicks at its
ignition; a hot start (lit on the carriage) kicks at release; a release at 54 m/s with
a 0.5 s coast is below 50 m/s at ignition and does a vertical rise first. A falling
vehicle (w < 0) never kicks, whatever its speed: g = w < 0 until the lit rise has
turned the fall around (split at the radial `turnaround`), after which the trigger is
V = v_k with w > 0. The pre-ignition coast does not list the trigger, so the unlit
flight after a release never kicks.

**Event rules** ("Event rules", rule 4). The phase after one a terminal event ended
never lists that event (the kick trigger is gone after the kick starts, the alignment
after the turn starts, the apex after an apex split: the falling list has `impact`,
the rising one `apex`, the falling lit rise `turnaround`), which a test checks over a
pad, a silo and a falling-start run. Every event is monotone within its phase:
`kick_start` in a rise (V and w grow while the thrust exceeds the weight; while
falling, w < 0 keeps g negative), `kick_end` in the kick for every kick that aligns
(the tilted thrust and gravity turn the velocity away from vertical toward the thrust,
so beta_rel grows through delta), `apex`/`turnaround` by the partition, `impact` on the
falling coasts, and the time events. `kick_end` is not monotone for tiny kicks: with
rotation beta_rel peaks below delta and turns back west (the Coriolis stall, "gamma*
inner solve": below 0.11662 deg on the gate pad), so the event never fires and the
kick timeout ends the kick; nothing is missed, since g never reaches zero. The ground
event in a lit phase is not monotone in a dive, but it can only be missed if the
altitude crossed zero twice inside one step, which the ramp and lag caps and the
kilometre-scale altitudes exclude. A rising rise or coast does not list the ground
event (its apex split ends it first). That matters at the pad's liftoff root, where
v_r = 0 and dv_r/dt = 0: the engine's second-order predictor sees the altitude stay at
zero there and would disarm a listed ground event with a run flag (harmless, as the
guard re-arms above `ATOL_M`, but spurious). A kick starting on the ground at a silo
release (v_r > 0) is predicted to rise, so its ground event starts armed. The
shipped pad and silo runs (pad lit at -2, 0 or +1 s, ramp or step; silo cold, hot and
lit at release) carry no run flags. Event states are read with
`event_state`, so the planner runs with dense output off (search evaluations) and on
(recorded runs) alike; the two take the same steps and log identical event records and
hand-overs.

**Planar view** (`PlanarView`, the planar `StateView`): alt_m = r - r_datum;
downrange_m = r_datum (theta - omega_p (t - t_fs)), the Earth-fixed arc along the datum
sphere, and 0 for rows before the flight (HOLD, ASSIST and RELEASE labels, where the
vehicle is Earth-fixed or on the track; a flight row before t_fs is known raises);
speed_rel_mps = |v_rel|; speed_inertial_mps = hypot(v_r, v_theta); gamma_rel_rad =
atan2(w, u) in (-pi, pi] (pi/2 below `V_REL_EPS_MPS`; not unwrapped in the record; the
reported events.csv and time series are unwrapped per run, amendment 14); m_kg. Its
ascent kinds (the loss
budget's phases) are COAST_PRE_IGN, VERTICAL_RISE, KICK, GRAVITY_TURN, COAST_STAGING,
LTG_BURN and COAST. A radial rise with rotation leans slightly west of vertical
(u < 0), so gamma_rel is just above pi/2 in the rise (90.04 deg at the pad's kick
trigger).

**Planner interface** (`PlanarPlanner(vehicle, ignition, guidance, env, end, settings,
*, z_ground_m=0)`; `PlanarEnvironment(gravity, omega_p_rads, atmosphere, r_datum_m)`
holds what every planar phase shares, with g_ref = g(r_datum) - omega_p^2 r_datum; the
drag model is `vehicle.aero`). `start` runs the prelude to a `FlightStart`; `to_kick`
flies the delta-independent part (the pre-ignition coast and the rise) to a
`KickPoint`, once per vehicle and payload; `from_kick(delta, kick)` flies the kick, the
turn, MECO and (by default) the staging map and coast to a `Handover` (the MECO record
with t, altitude, downrange, speeds, gamma_rel, mass, every quadrature, the kick start,
duration and steering loss; the stage-2 ignition time and state; whether the fairing is
still on; the trace so far); `stage1` is both. `run(delta, assist, track, ltg=(a,
b))` is a recorded run at fixed guidance inputs: `stage1_burnout` (stops at MECO with
an `end` event), a failed stage-1 ignition (the unpowered COAST to the apex and the
ground), a failed stage-2 ignition after the staging coast, and a lit stage 2 flown to
insertion ("Stage 2 and insertion (planar)"; `stage2` and `solve_stage2` there too).
An impact before MECO ends a recorded run with status impact; in `from_kick`/`stage1`
it raises GuidanceFailure("impact"), as the inner solve needs, and so does an impact in
the staging coast when they fly through staging (the default). A `Handover` records the
kick angle only for a flight that kicked: with vertical-only guidance `delta_rad` is
None, and `from_kick` and `run` refuse a kick angle (ValueError).

**Guidance failures** (`GuidanceFailure(kind, message)`, a RuntimeError whose args are
(kind, message), so it pickles): `impact`, `no_kick`, `kick_timeout` (this step);
`no_cutoff`, `mass_floor`, `nonconverged`, `not_direct_root` and `lofted_overshoot`
(the stage-2 burn and its shooting, "Stage 2 and insertion (planar)" and "LTG
shooting"); `gamma_unattainable` and `false_root` (the inner solve, next section).
They are typed outcomes a search turns into a penalty, never warnings.

**Measured on the gate fork** (28.5 deg east, rotation, ICAO, Braeunig drag, v_k 50
m/s, the pad lit at -2 s; recorded settings, rtol 1e-10). MECO is 151.328 s after
release for every delta (the burn does not depend on the steering). The kick lasts
5.25 to 5.28 s and books 0.025 to 0.039 m/s of steering loss; the loss identity closes
to about 1e-9 m/s at MECO:

| gamma* [deg] | delta [deg] | MECO h [km] | V_rel [m/s] | V_in [m/s] | downrange [km] | J_vac | J_grav (J_alt) | J_drag | J_steer | J_bp | total loss [m/s] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 15 | 3.49415 | 58.131 | 2,810.14 | 3,210.33 | 112.814 | 3,889.939 | 985.529 (-3.958) | 30.246 | 0.039 | 63.985 | 1,079.80 |
| 20 | 3.12845 | 66.092 | 2,748.08 | 3,139.32 | 105.584 | 3,889.939 | 1,051.047 (-4.905) | 27.465 | 0.031 | 63.319 | 1,141.86 |
| 25 | 2.80306 | 73.252 | 2,690.39 | 3,070.07 | 98.208 | 3,889.939 | 1,111.064 (-5.871) | 25.626 | 0.025 | 62.833 | 1,199.55 |

These sit inside the plan's sanity ranges for MECO (t 140 to 175 s, h 60 to 90 km,
gamma_rel 15 to 30 deg), except the 15 deg row's 58 km. They are stage-1 numbers only:
the stage-2 burn is "Stage 2 and insertion (planar)" and the gamma* optimum comes
from the search ("Payload and gamma* search"). A stage-1
flight to MECO costs 30 to 45 ms with dense output at rtol 1e-10 (2,500 to 3,500 RHS
calls), 21 ms at rtol 1e-9 and 16 ms at the search setting (rtol 1e-8, atol x 10),
both with dense output off.

**Validation.**

- `test_gravity_turn.py::test_culler_fried_gravity_turn`: the gravity turn (`AlongVrel`)
  against the Culler-Fried closed form. Flat Earth (R = 1e12 m, mu = g_test R^2), no
  air, a constant thrust acceleration n g_test (n = 1.5, c = 1e30), from v0 = 100 m/s
  at beta0 = 0.05 rad to beta = 1.2 rad (stopped by `ev_kick_aligned(1.2)`). With
  z = tan(beta/2) and C = v0 sin beta0 / z0^n (from dv/dt = g (n - cos beta) and
  v dbeta/dt = g sin beta):

      v = C z^n / sin beta
      t = (C/2g) [z^(n-1)/(n-1) + z^(n+1)/(n+1)]
      h = (C^2/4g) [z^(2n-2)/(2n-2) - z^(2n+2)/(2n+2)]
      x = (C^2/2g) [z^(2n-1)/(2n-1) + z^(2n+1)/(2n+1)]
      J_grav = int g cos beta dt = (C/2) [z^(n-1)/(n-1) - z^(n+1)/(n+1)]
      J_vac = n g t,  J_steer = 0

  each as a difference from z0. Asserted 1e-6 relative (measured 4e-8 to 1.7e-7, the
  finite-R curvature: h/R = 2.6e-8, x/R = 2.3e-8), J_steer exactly 0 (1e-12), and the
  identity V_f - V_0 = J_vac - J_grav within 1e-9 m/s. This is the validation of the
  gravity-loss attribution the matched-payload checks rest on (plan section 5).
- `test_planar_events.py`: the pad liftoff with back-pressure and rotation at the root
  of T_vac t/t_r - p0 A_e = (m0 - mdot t^2/(2 t_r)) g_ref solved in the test (1e-9 s;
  the mass 1e-12; the pad state Earth-fixed; later than the vacuum-thrust root); the
  kick trigger at V = v_k with w > 0 (1e-9 m/s; measured 7e-15) and the alignment at
  gamma_rel = pi/2 -
  delta (1e-9 rad) with a continuous thrust direction into the turn; the kick at the
  first lit instant for a cold and a hot silo start (no VERTICAL_RISE phase, no run
  flag); a rise from the pad's liftoff root without the ground event and without a
  flag; a falling vehicle that does not kick before its turnaround; the typed
  kick_timeout and no_kick (deadline and burnout) failures; the deadline counted from
  ignition, not from the flight start (the pad lit at -2 s, deadlines 0.75 s short of
  and 0.25 s past the trigger); a dive that ends at the ground (status impact; GuidanceFailure impact in the
  search path); the heating rate 0.5 rho(h) |v_rel|^3 against ambiance's rho and v_rel
  computed in the test (40 seeded states and the pad MECO; 1e-12 relative), and a
  staging decision that flips on it (a limit between the |v_rel| rate and the 1.5x
  larger inertial-speed rate at MECO drops the fairing, one just below the |v_rel| rate
  keeps it); vertical-only guidance recording no kick angle and refusing one; the
  staging map (exactly m_d1, plus F for rule staging or an already-met heating
  criterion; every other entry bit-equal) and the 11 s coast (and a stage-2
  t_ign_s of 1.5 s adding a COAST_PRE_IGN); the loss identity from the flight start to
  MECO and to stage-2 ignition within the shipped 1e-5 m/s (measured about 1e-9) for the
  pad and silo_cold, with exactly zero steering loss booked in the turn and the coasts;
  the failed stage-1 ignition on a silo (coast, apex, impact at the mouth, identity
  closed) and on the pad (no_liftoff); a failed stage 2 (coast to the ground after the
  staging coast); the event-list discipline (with no run flag on the pad, silo and
  falling-start runs); and dense-off hand-overs identical to dense-on ones.
- `test_planar_reductions.py::test_planner_reduces_to_the_vertical_planner`: the
  planner-level reduction ("Planar reductions").

## gamma* inner solve

Module: `guidance.py` (`solve_delta_for_gamma`, `DeltaSolveSettings`, `DeltaSolution`,
`IMPACT_GAMMA_RAD`, `TIMEOUT_GAMMA_RAD`). Test: `tests/test_guidance.py`. The shared
stage-1 knob is gamma*, the Earth-relative flight-path angle at MECO (decision 5); the
kick angle delta that reaches it is solved per run and per payload.

**Map.** f(delta) = gamma_MECO(delta) - gamma*, where one evaluation is one stage-1
flight (`PlanarPlanner.from_kick`, from the run's `KickPoint`; by default through the
staging coast to stage-2 ignition). A harder kick turns over sooner, so gamma_MECO
decreases with delta. On the gate pad (rtol 1e-10): 79.80 deg at delta = 0.5 deg, 65.01
at 1, 40.03 at 2, 21.91 at 3, 8.99 at 4, -0.52 at 5 deg. Flights stopped at MECO reach
it up to delta = 6.7618 deg (gamma_MECO -12.99 deg, 2e-5 m up; a harder kick dives into
the ground before MECO). Flown through the 11 s staging coast, the last flight that
reaches stage-2 ignition is delta = 6.3621 deg (MECO at -10.41 deg and 5.3 km); a
harder kick still reaches MECO (-11.31 deg at 3.4 km at 6.5 deg) but falls into the
ground within the coast.

**Coriolis stall of tiny kicks.** With rotation the Earth-relative downrange velocity
obeys u' = a_theta - 2 omega_p w - w u / r ("2-D loss identity", with v_theta =
omega_p r + u): the Coriolis term -2 omega_p w grows with the climb rate, and a small
tilt's (T/m) sin(delta) cannot keep up with it. The velocity then leans away from
vertical only for a while: beta_rel peaks below delta and turns back west, so
`kick_end` never fires. On the gate pad (v_k 50 m/s, kick at 12.268 s) this happens
for every kick below delta = 0.11662 deg: a 0.1 deg kick reaches at most beta_rel =
0.085 deg (at t = 31.1 s), and held to MECO (139.06 s after the kick start; that is
MECO, not an alignment) it ends at gamma_rel = 90.20 deg, still leaning west (90.17 to
90.20 deg over the stalled range). Just above the threshold the kick aligns after at
most 19.1 s and ends at 90.96 deg, the largest gamma_MECO any real flight reaches; from
there the map decreases (90.90 deg at 0.12 deg, 90.20 at 0.15, 88.82 at 0.2 deg with an
8.4 s kick). So the map of real flights is not monotone at the stall threshold: it
jumps up there, from about 90.2 to 90.96 deg. Without rotation every kick from 0.1 to
0.2 deg aligns and the map decreases monotonically (86.81 to 83.64 deg). With the
shipped kick_max_s = 60 s the stalled kicks time out.

**Sentinels.** A flight that hits the ground before its end (GuidanceFailure
`impact`: before MECO, or in the staging coast before stage-2 ignition when the flight
goes through staging, as the inner solve's flights do by default) counts as
gamma_MECO = -pi/2, below every real value, and a kick that times out
(`kick_timeout`) as +pi, the top of gamma_rel's range (-pi, pi] and so above every real
value. With a kick_max_s between the slowest aligning kick (19.1 s) and a stalled
kick's hold to MECO (139 s), which includes the shipped 60 s, the timeouts are exactly
the stalled kicks, so gamma_MECO(delta) with both sentinels is non-increasing over the
whole bracket and a cold start can evaluate both ends. A +pi/2 sentinel would sit
below the aligned flights next to the stall (90.07 to 90.96 deg), so the map would
rise again there and a gamma* between 90 and 90.96 deg would be reported unattainable;
with +pi, gamma* = 90.1 deg solves at delta = 0.15369 deg. A
kick_max_s above 139 s would let stalled kicks reach MECO as real flights at about
90.2 deg, below the aligned ones, and the map would again be non-monotone at the stall
threshold; the false-root guard below still rejects any root brentq lands on across
that jump, and the shipped gamma* grid (8 to 36 deg) lies far from it. `no_kick`
(independent of delta) and every other failure propagate. The plan lists the kick
timeout among the failures that go straight to the grid penalty; mapping it to a
sentinel inside the inner solve is this step's choice, a Plan-mode deviation awaiting
the user's decision: with rotation a kick at the shipped bracket's low end (0.1 deg)
never aligns and times out, so the literal reading would make every cold solve fail
at its low end.

**Bracket and root.** Cold (no warm delta): f at both bracket ends. Warm (the last
solved delta of this run for the nearest gamma*, clipped to the bracket): step by
`delta_step_deg` toward the root (up when f > 0), doubling, until f changes sign; a
bracket end reached without a sign change raises GuidanceFailure
`gamma_unattainable`. Then brentq (`delta_xtol_rad`, `brentq_rtol`) on the
sign-change interval. Flights are cached by delta (brentq's end-point evaluations fly
nothing twice). **False-root guard** (amendment 7): the root must be a real flight
with |gamma_MECO(delta*) - gamma*| <= `gamma_root_tol_deg` (0.01 deg); brentq also
converges onto a discontinuity where f changes sign, which a gamma* inside the impact
gap (between the shallowest real flight, -10.41 deg on the gate pad through the staging
coast or -12.99 deg stopped at MECO, and the -90 deg sentinel) or above the timeout
jump (between 90.96 deg and the
+180 deg sentinel) produces, and the guard turns that into GuidanceFailure
`false_root` (the grid penalty).

**Noise floor.** With the planar flight phases uncapped (no `max_step` outside the
thrust ramp), gamma_MECO(delta) is not smooth at the integration-error level. The
cause is the step-size control across the derivative kinks of the RHS, above all the
clustered C1 knots of the transonic PCHIP C_D table (M 0.95, 1.0 and 1.05, 0.05
apart): DOP853 sometimes accepts one long step across all three, and whether it does
changes with delta. Two kicks 2e-10 rad apart at delta = 3.25 deg fly identically (to
1e-9 rad) until t = 45 s; then one takes a single 3.59 s step from M 0.924 (t =
49.47 s, h about 6 km, below every ICAO layer base) to M 1.044, where its gamma error
against an rtol-1e-13 reference grows from -2e-9 to -6.1e-8 rad (the other's stays
below 7e-11 rad), and it ends 6.9e-7 rad apart at MECO. Measured on the gate pad as
the largest deviation from a local linear fit over 31 kicks 2e-10 rad apart, at 66 kick
angles (61 evenly spaced from 2.5 to 4 deg, the three roots below and two neighbours;
the map's slope is about -15 rad/rad), uncapped:

| setting | largest deviation [rad] (at delta) | median | 90th percentile | largest step jump |
|---|---|---|---|---|
| rtol 1e-10 (recorded runs, the test) | 6.7e-7 (3.25 deg) | 2.2e-8 | 9.2e-8 | 6.9e-7 |
| rtol 1e-9 | 1.6e-6 (2.55 deg) | 1.9e-7 | 6.3e-7 | 1.8e-6 |
| search (rtol 1e-8, atol x 10) | 1.8e-5 (3.15 deg) | 1.1e-6 | 1.9e-6 | 1.8e-5 |

Sparse samples: 1.9e-9 to 3.2e-9 rad at rtol 1e-11; without drag 2.6e-9 (rtol 1e-10)
to 6.4e-9 rad (1e-9); in vacuum 1.5e-12 to 1e-11 rad, consistent with the drag table as
the source.

The floor is not intrinsic. A `max_step` cap on the planar flight phases removes it
(largest deviation over 31 kicks 2e-10 rad apart at five kick angles, 2.7 to 3.6 deg,
with the mean time per stage-1 flight to MECO, dense output off):

| cap | rtol 1e-10 | search setting (rtol 1e-8, atol x 10) |
|---|---|---|
| none (current) | 1.5e-9 to 6.3e-7 rad, 33 to 36 ms | 4.0e-7 to 1.6e-5 rad, 21 to 23 ms |
| 2 s | 1.4e-9 to 2.7e-8 rad, 32 to 36 ms | 7e-9 to 5.5e-8 rad, 20 to 23 ms |
| 1 s | 1.1e-9 to 4.8e-9 rad, 37 to 44 ms | 1.3e-10 to 1.3e-8 rad, 24 to 30 ms |

A 2 s cap costs nothing measurable and puts the search-setting floor about 3,000x below
the 0.01 deg (1.75e-4 rad) root guard (uncapped: about 10x); at the search setting the
uncapped MECO altitude deviates from its linear trend by up to 1.9 m (V_rel by 1e-3
m/s) over 31 kicks spanning 6e-9 rad, and by 3 to 7 mm (2e-5 m/s) with a 2 s cap. A
cap is an integrator setting, so it is a Plan-mode change awaiting the user's decision
(it would be planar-only, leaving the 1-D golden untouched); none is in the code.

brentq can only land on a sign change of the map, so with the current uncapped phases
the plan's 1e-9 rad acceptance for the inner solve is below the floor, and even a
noise-free map could not meet it: brentq stops at delta_xtol = 1e-10 rad, which at the
slope of about 15 rad/rad leaves up to 1.5e-9 rad in gamma. The test asserts 3e-6 rad
(1.7e-4 deg, about 4x the largest uncapped step jump at rtol 1e-10; measured residuals
about 1e-9 rad at the three roots), below the root guard and the 0.1 deg gamma*
resolution (amendment 3); with a 2 s cap about 1e-7 rad (4x the capped 2.7e-8) would
do. This acceptance is a
Plan-mode deviation awaiting the user's decision together with the cap. For the search:
the refine, LTG finite-difference and convergence tolerances should be sized after the
floor is removed, not from the uncapped floor (whose noise/slope, 1.2e-6 rad in delta
at the search setting, is four orders above delta_xtol, so brentq's last iterations
would bisect noise). Pending that decision the search keeps the shipped tolerances and
their measured effect on the figures of merit is small ("Payload and gamma* search",
Noise floor and the budget; "Convergence (planar)").

**Cost** (gate pad, rtol 1e-10, the shipped delta settings): a cold solve takes 11 to
13 flights (13 at gamma* = 20 deg, about 0.43 s), a warm one from the 20 deg kick 8 or
9 (gamma* 10 to 30 deg); the false-root case bisects onto the jump (about 20 flights
from a 5 to 10 deg bracket at xtol 1e-7 rad).

**Validation** (`test_guidance.py`): the laws and the spec; typed, picklable failures;
the settings from `SearchConfig`; gamma_MECO strictly decreasing on 10 kicks from 1 to
5.5 deg and an impact at 7 deg; gamma* = 20 deg cold and 10 and 30 deg warm within
3e-6 rad (a Plan-mode deviation, see Noise floor) (the warm solves in fewer flights; delta(10) > delta(20) > delta(30)); the
hand-over is the flight at delta* and re-flies bit for bit; gamma* = -45 deg in the
impact gap is a false root; on a toy map with a timeout below delta = 0.01 and impacts
from 0.2, the roots from cold and three warm starts (two of them on sentinels), false
roots on both jumps, unattainable targets beyond both sentinels and from a narrow warm
bracket, and `no_kick` propagating; and on a toy map whose aligned flights end above
pi/2 next to the timeout (as the gate pad's do past the Coriolis stall), gamma* = 1.7
rad solved cold and warm, which the +pi sentinel allows and a +pi/2 one would not.

## Time-shift mechanism (2-D gravity loss)

This is the mechanism plan section 5 names for the planar gravity-loss change of an
assist, the basis of the matched-payload mechanism check M2 ("Screening-beat rule
(2-D)", built in step 24 as pre-registered). It is
not a port of the 1-D RQ3 mechanism, and the 1-D bound `unexplained_gain_mps <= 0`
does not apply to planar runs.

**Statement.** A release at V0 removes the baseline's first t_v0 seconds of
near-vertical flight (sin gamma_rel about 1), t_v0 being the baseline's time from t_fs
to V = V0, and the same propellant then burns t_v0 seconds "later", at the end of stage
1 where sin gamma_rel is about sin gamma* (0.34 at 20 deg). The estimate over the
baseline's own trajectory is

    dJ_grav_est = int_{t_MECO - t_v0}^{t_MECO} g_eff sin gamma_rel dt
                - int_{t_fs}^{t_fs + t_v0} g_eff sin gamma_rel dt        (both baseline)

(M2 asks the matched-payload d J_grav to have its sign and lie within [0.33, 3] of it).

**Measurement (stage 1 only, not a finding).** Flying the gate pad and the 3 g, 100 m
silo (V0 = 76.71 m/s) to the same gamma* at MECO with the delta inner solve (rtol
1e-10), d J_grav = variant - baseline at MECO; t_v0 is the baseline's time from t_fs
to V0:

| pair | t_v0 [s] | gamma* [deg] | d J_grav [m/s] | estimate [m/s] | ratio |
|---|---|---|---|---|---|
| silo_instant vs pad_instant (both lit at release, step) | 18.15 | 15 / 20 / 25 | -32.1 / -27.7 / -23.8 | -127.4 / -113.2 / -99.5 | 0.25 / 0.24 / 0.24 |
| silo_cold vs pad (lit 0.5 s after release with the 2 s ramp; pad lit at -2 s) | 17.90 | 15 / 20 / 25 | -3.2 / +0.6 / +3.9 | -125.6 / -111.6 / -98.1 | 0.03 / -0.01 / -0.04 |

At equal gamma*, the assist saves a quarter of the estimated gravity loss when both
runs are lit at release, and none when the silo lights 0.5 s after release. The
cold-start case flies 0.5 s unpowered and 2 s of ramp in the air near sin gamma_rel =
1, which the pad spends clamped on the ground, so it pays gravity loss the pad does
not.

**The gap is not a guidance effect** (gamma* = 20 deg, rtol 1e-10). Under the shared
kick rule the silo kicks at 77 m/s rather than 50 m/s and needs a different kick (3.87
deg against 3.03 deg), which suggests the different gamma_rel(t) history as the cause.
Separating it refutes that: with both runs kicking at the same
speed (v_k = 80 m/s, above the 76.7 m/s release, so the silo too rises to its trigger)
the instant pair gives d J_grav = -27.94 m/s against the estimate -113.19 m/s (ratio
0.247), against -27.70 / -113.15 (0.245) at v_k = 50 m/s; with no drag, no rotation
and no atmosphere, -23.02 / -93.28 (0.247) at v_k = 50 and -23.27 / -93.31 (0.249) at
v_k = 80. The ratio stays near 0.25 whatever the kick speed, the drag or the rotation,
so the estimator itself is about 4x optimistic.

**Why: the premise fails.** The estimate treats the variant as the baseline shifted
by t_v0: from V0 on it would fly the baseline's path and add t_v0 seconds of shallow
flight at the end. But at V0 the variant still carries the propellant the baseline
burned to reach V0: the silo leaves at 569.1 t, while the pad_instant baseline passes
76.7 m/s at about 520 t (about 49 t burned in its t_v0 = 18.15 s at 2.7 t/s). At the same speed the variant
is about 9 % heavier with a lower thrust-to-weight ratio, so it cannot follow the
baseline's path. This is the leading explanation; a mass-consistent estimator has not
been built or tested.

**Consequence for the pre-registration.** On stage 1 at equal gamma*, matching the
guidance would not bring the ratio into M2's [0.33, 3] band (about 0.25 lit at
release, about 0 for the cold start). These are equal-gamma* stage-1 comparisons, not
M2 as built in step 24, which compares the whole-flight matched d J_grav with each run
at its own sweep-optimized gamma*; there the 77 m/s variants pass and the low-speed cold
starts fail, largely for reasons the estimator does not model (the measured table and
the options are in "Screening-beat rule (2-D)"). Redefining the estimator or dropping
the check is the user's decision before the pre-registration commit. The result
undercuts the plan's expectation of a large stage-1 gravity-loss gain from a 77 m/s
vertical assist; it is recorded here, not tuned around.

## Stage 2 and insertion (planar)

Modules: `guidance.py` (`LinearTangent`, the test-only `LinearTangentEps`),
`phases/planar.py` (`PlanarPlanner.stage2`, `solve_stage2` and `run`, `Stage2Result`,
`map_fairing_planar`, `orbital_energy_Jkg`, and the stage-2 event factories
`ev_energy_cutoff`, `ev_fmh`, `ev_mass_floor`), `orbit.py` (`TargetOrbit`,
`specific_energy_Jkg`, `orbit_elements`). Tests: `tests/test_insertion.py`,
`tests/test_ltg.py`, `tests/test_engine_planar.py`, `tests/test_loss_identity_2d.py`,
`tests/test_closure.py`. Frame: planar ECI; the orbital energy and the elements use
the inertial velocity, the heating rate and every aerodynamic term v_rel. This section
runs at fixed guidance inputs (a solved delta and LTG pair at one gamma* and the
vehicle's payload); the payload search is "Payload and gamma* search".

**Steering law.** LTG_BURN flies `LinearTangent(a, b, t_ign2)`:

    tan p = s = a - b tau,   tau = t - t_ign2,   e = (e_r, e_theta) = (s, 1) / sqrt(1 + s^2)

in the local horizontal frame (it turns with the radius vector; CLAUDE.md's form), a
dimensionless (tan p at stage-2 ignition), b [1/s] the rate at which tan p falls. The
pair is solved by shooting ("LTG shooting"); a recorded run flies the solved pair.

**Energy cutoff (insertion).** The burn ends at the terminal event `cutoff`
(`ev_energy_cutoff`): E - E* crossing zero upward, with

    E = (v_r^2 + v_theta^2)/2 - mu/r      (inertial),      E* = -mu/(2 r_t)

and zero_tol = `ATOL_MPS` v_c, the energy of one velocity tolerance at the circular
speed. Gravity is conservative, so only the thrust and the drag change E:
dE/dt = (T e - D v_hat_rel) . v_in / m. With the pitch inside the direct-root window
the thrust works positively on the inertial velocity (the angle between e and v_in
stays far below 90 deg), and the drag above 70 km is five orders smaller, so E rises
monotonically through the burn and the crossing is unique; a speed cutoff would target
the wrong radius. At the cutoff the semi-major axis is r_t to the root's accuracy, and
the shooting drives r_c to r_t and v_r,c to 0, which with E = E* makes the orbit
circular. Acceptance (`search.ltg`): |r_c - r_t| < `accept_r_m` (1 m) and |v_r,c| <
`accept_vr_mps` (1e-3 m/s); the eccentricity is then of order hypot(dr/r_t, v_r/v_c),
about 2e-7, below `checks.insertion_e_max` (1e-6), and the elements come from
`orbit_elements`. **Pre-screen:** an orbital energy already at or above E* at stage-2
ignition raises GuidanceFailure `lofted_overshoot` (the cutoff could only fire at
once, so no pair reaches the target). The plan wrote the pre-screen as "E > 0 at
t_ign2"; E >= E* is the condition that makes the target unreachable, and E > 0 implies
it.

**Mass bookkeeping.** Stage 2 ignites with m_p2 + m_d2 + P + F2, where F2 = F when the
fairing is still on (the heating rule not met at staging: `map_staging_planar`
removes m_d1 only) and 0 otherwise. The planner never uses the screening helpers
(`Vehicle.stack_mass_kg` and relatives count the heating rule as a drop at staging).
m_empty = m_d2 + P (+ F while the fairing is on) is the mass with every kilogram of
stage-2 propellant gone. The plan wrote m_res = m_c - (m_d2 + P) with "fairing always
gone by cutoff; otherwise flagged": a fairing still on when the burn ends (rule never,
or the heating criterion not met before the cutoff) stays in m_empty, so m_res and
dv_margin never count it as propellant (the final mode's depletion fires at m_d2 + P +
F), and the run carries the flag `fairing: still on at the end of the stage-2 burn`.
On the shipped forks every converged shot drops the fairing at about 111 km, so the
flag does not fire there.

**Fairing event and map.** While the fairing is on under the heating rule, LTG_BURN
lists `fairing` (`ev_fmh`): g = ln(0.5 rho V^3 / q_fmh) crossing zero downward, V =
|v_rel|, rho at h, q_fmh the vehicle's `limit_W_m2` (1,135 W/m^2). The logarithm keeps g
of order 1 while the rate falls through six decades; a zero density gives -inf, which
the engine's already-past rule ends at t0. The rate falls monotonically in the burn
(rho drops by e per scale height, 6 to 7 km of climb at about 1 km/s, while V^3 grows
by a few percent per second). At the event the FAIRING map (`map_fairing_planar`)
removes F and leaves r, theta, v_r, v_theta and every quadrature unchanged (V is
unchanged, so the identity is untouched), and LTG_BURN continues with the same (a, b,
t_ign2) without the fairing event. The event record carries the state just before the
drop. A criterion first met in the staging coast (after staging, where the staging map
handles an already-met criterion) drops the fairing at stage-2 ignition, logged there
in LTG_BURN with a run flag (a rule the plan does not specify; it is on the list of
Plan-mode deviations for the user). The `fairing` record therefore has three forms,
and reports must not mix them (`metrics_planar.fairing_items` names the form in
`fairing_drop`): in LTG_BURN at the heating event, the
state just before the drop (F included) at the time the criterion is met; in LTG_BURN
at stage-2 ignition, the state before the drop at ignition, not at the (earlier)
coast instant where 0.5 rho V^3 crossed the limit; in COAST_STAGING, the state after
the staging map (m_d1 and F removed). The "fairing t and h" of a summary come from
the first form; the other two are labelled.

**Search mode and final mode** (`stage2(handover, a, b, virtual_propellant=...)`):

- A search shot (virtual_propellant True) lists no depletion event: stage 2 burns on
  past its real load ("virtual propellant"), so the residual m_res = m_c - m_empty is
  continuous through zero as the payload changes, and negative when the payload is
  above capacity. The mass floor `mass_floor` (`ev_mass_floor`: m -
  k_floor (m_d2 + P), k_floor = `ltg.mass_floor_factor` = 0.5) stops a shot that would
  burn toward zero mass: GuidanceFailure `mass_floor`.
- The final mode (False) lists the real depletion (`propellant`: m - m_empty) and no
  floor: a burnout before the cutoff returns ended_by `propellant`, and a recorded run
  reports status `short_of_orbit`.
- Both list `no_cutoff` (`ev_time` at t_ign2 + k_tau tau_b, k_tau =
  `ltg.tau_max_factor` = 2, tau_b = m_p2 c2 / T2_vac = 373.97 s on the gate fork;
  GuidanceFailure `no_cutoff`) and the ground (GuidanceFailure `impact` from `stage2`,
  status impact in a recorded run).
- `no_cutoff` is a guard: with the shipped settings it never fires first. Stage 2
  burns at the constant mdot = T2_vac/c2 (full thrust from ignition), so the final
  mode's depletion comes at tau_b < k_tau tau_b (k_tau > 1 is validated), and a search
  shot reaches the floor at tau_floor = (m_p2 + (1 - k_floor)(m_d2 + P) + F_kept)/mdot,
  with F_kept = F when the fairing is still on at the floor, else 0: 420.6 s (fairing
  dropped) to 426.5 s (still on) = 1.125 to 1.14 tau_b on the gate fork at 22.8 t,
  against k_tau tau_b = 747.9 s. `no_cutoff` fires first only when k_tau < 1 + ((1 -
  k_floor)(m_d2 + P) + F_kept)/m_p2 (1.14 here), or for m_d2 + P above 2 (m_p2 - F),
  about 211.6 t on the gate fork. So a grid table shows `mass_floor` (or `impact`)
  where a burn fails to reach the cutoff, not `no_cutoff`; the one test that reaches
  `no_cutoff` sets k_tau = 1.01.
- `Stage2Result` carries a, b, t_ign2, ended_by, the end time and state, the fairing
  status (still on, when dropped, the mass just after the drop), m_empty and c2, the
  trace through the burn; m_res_kg = m_c - m_empty and dv_margin_mps =
  c2 ln(m_c / m_empty), signed.

**Recorded run.** `run(delta, assist, track, ltg=(a, b))` flies stage 1, the staging
map and coast, logs stage 2's `ignition`, and flies LTG_BURN in the final mode, with
the stage-2 burnout (`RunTrace.burnouts`) at the end state. At the cutoff the status
depends on the cutoff state, not on the event alone: the cutoff fires for any pair that
raises E to E*, including a pair that is not a root (a stale warm pair, one solved at
another payload, a fixed pair of `figure_of_merit: none`). Status `inserted` requires
the LTG acceptance, |r_c - r_t| < `accept_r_m` and |v_r,c| < `accept_vr_mps` (the
planner's LtgSettings); otherwise the status is `off_target` and the run carries the
flag `off target: the energy cutoff state misses the LTG acceptance (...)` with r_c -
r_t, v_r,c, e and the perigee altitude. Measured on the gate pad at gamma* 20 deg: the
solved pair with a scaled by 1.05 cuts off 18.9 km high with v_r 154 m/s (e 0.020,
perigee 68 km), b scaled by 0.9 gives perigee 8 km, and (0.8 a, 1.2 b) a suborbital
cutoff (e 0.139, perigee -711 km); all three would have been labelled inserted without
the check. The eccentricity gate `checks.insertion_e_max` is one of the per-run checks
("Screening-beat rule (2-D)"). A depletion before the cutoff gives `short_of_orbit`. End
`insertion`
closes with an `end` event. After a cutoff, ends `apex` and `impact` do the same
(status inserted or off_target, an `end` event at the cutoff, and a flag `end apex:
stage 2 reached the target orbit ...`, or `... reached the energy cutoff off target
...`): an orbit has no impact and its apex is the apogee, so there is no terminal
coast, and an off-target cutoff is not flown on (its status already says the pair is
not a root).
After a burnout short of orbit they continue with the terminal COAST (to the apex; for
impact on to the ground); a short orbit whose perigee lies above the ground never
comes down, so that combination ends at the t_max guard with RuntimeError (build step
24 refuses or documents it at the config level). A lit stage 2 without the pair is
refused (ValueError). Run statuses are now nominal,
impact, no_liftoff, drive_limit, inserted, off_target and short_of_orbit.

**Phases and events (planar, complete)** (terminal unless noted; every phase that can
reach the ground lists `impact`, a rising one the `apex` split instead; lit phases are
split at the thrust kinks):

| Phase | RHS / law | Events (direction) | Next |
|---|---|---|---|
| HOLD (pad) | the prelude in `PLANAR_LAYOUT`: mass only | `liftoff` (+) | flight start |
| ASSIST (track) | the flat 1-DOF track | `track_end`, `propellant`, `drive_limit` | release map, flight start |
| COAST_PRE_IGN | unpowered | `apex` split (-) or `impact` (-); t_end = t_ign | VERTICAL_RISE or KICK |
| VERTICAL_RISE | `Radial` | `propellant` (-), `apex`/`turnaround` splits, `impact` (falling), `kick_start` (+), `kick_deadline` (+) | KICK; GuidanceFailure no_kick |
| KICK | `FixedTilt(delta)` | `propellant` (MECO), `impact`, `kick_end` (+), `kick_timeout` (+) | GRAVITY_TURN; GuidanceFailure kick_timeout |
| GRAVITY_TURN | `AlongVrel` | `propellant` (MECO), `impact` | STAGING |
| STAGING (map) | m -= m_d1 (+ F under rule staging or an already-met heating criterion) | | COAST_STAGING |
| COAST_STAGING | unpowered, stage 2's coast_before_ignition_s (11 s) | `apex` split or `impact` | COAST_PRE_IGN or stage-2 ignition |
| LTG_BURN | `LinearTangent(a, b, t_ign2)` | `cutoff` (+): E - E*; `fairing` (-) while the fairing is on; `mass_floor` (-, search) or `propellant` (-, final); `no_cutoff` (+); `impact` | FAIRING map; insertion (status inserted, or off_target outside the LTG acceptance); short_of_orbit; GuidanceFailure |
| FAIRING (map) | m -= F; r, theta, v and the quadratures unchanged | | LTG_BURN, same law |
| COAST (terminal) | unpowered, after a failed ignition or a lit stage 2's burnout short of orbit | `apex` split, `impact` | end apex or impact |

Ends: `stage1_burnout`, `insertion`, `apex`, `impact`. Every open phase carries the
t_max guard.

**Measured on the gate fork** (the pad lit at -2 s, 28.5 deg east with rotation, ICAO,
Braeunig drag, v_k 50 m/s, gamma* = 20 deg with delta = 3.12845 deg, 22.8 t, rtol
1e-10). Stage 2 ignites 162.33 s after release at 75.9 km and 3,109.1 m/s inertial
(gamma_in 15.86 deg). The solved pair (a, b) = (0.756790, 2.19338e-3 1/s) pitches from
37.12 deg at ignition to -2.26 deg at the cutoff. The fairing drops at 208.88 s, 111.5
km (sanity range 100 to 130 km; flown T+195 s, User's Guide sample). The cutoff comes at
525.39 s after release, tau_c = 363.06 s of tau_b = 373.97 s: |r_c - r_t| = 2.5 cm,
v_r,c = -1.2e-4 m/s, e = 1.6e-8, perigee and apogee 0.105 m below and above 200 km,
V_rel = 7,362.7061 m/s. Stage 2 keeps m_res = 3,135.7 kg (dv_margin 377.6 m/s) at 22.8
t. Losses from the flight start to insertion [m/s]: J_vac 9,007.79, J_grav 1,435.06,
J_drag 27.54, J_steer 119.17, J_bp 63.32, total 1,645.1, inside the 1,319 to 1,817
m/s sanity range; gravity inside 1.15 to 1.58 km/s; drag and back-pressure as at MECO
(MECO to insertion adds 0.07 m/s of drag: 0.05 in the staging coast, 0.02 in the
burn). SECO at 525.4 s against the flown T+514 s
(no throttle in the model). These are fixed-gamma* numbers, not a payload capacity:
the 3.1 t residual says the gate fork would carry more than 22.8 t on this trajectory,
the direction the plan's prototype disclosed (decision 1). The payload search is
"Payload and gamma* search"; the gate fork's P* is a calibration output, reported only
by the labelled calibration run (build step 26).

## LTG shooting

Module: `guidance.py` (`solve_ltg`, `LtgSettings`, `LtgSolution`, the `LtgShot`
protocol, `ltg_guess_ladder`, `ltg_physics_guess`, `is_direct_root`,
`LTG_B_SCALE_S`); `phases/planar.py` (`PlanarPlanner.solve_stage2`). Test:
`tests/test_ltg.py`.

**Unknowns and residual.** x = (a, 100 b) (`LTG_B_SCALE_S` = 100 s, so both entries
are of order 0.1 to 1 and one finite-difference step suits both), and

    F(x) = ((r_c - r_t) / r_scale, v_r,c / vr_scale),    r_scale 1e4 m, vr_scale 100 m/s

from one shot: LTG_BURN alone from the per-payload hand-over at stage-2 ignition, in
search mode (virtual propellant, mass floor). The hand-over is a local of the caller,
reused for every shot at that payload.

**Damped Newton** (one rung): the Jacobian by forward differences with step h in x
units (`ltg.fd_step_search` 1e-4 in a search, `fd_step_final` 1e-5 in a final solve;
`LtgSettings.from_config(final=...)`), a backward difference for a column whose
forward shot raises; the step dx = -J^-1 F; the step halved at most `max_halvings`
(6) times while a trial shot raises GuidanceFailure or ||F|| does not decrease; at
most `max_iters` (25) iterations. A rung converges when |r_c - r_t| < `accept_r_m`
and |v_r,c| < `accept_vr_mps`, and the root must then be **direct**: b > 0 and the
pitch atan(a - b tau) inside (`pitch_bounds_deg`, -45 to 75 deg) over 0 <= tau <=
tau_c (the pitch is monotone in tau, so its two ends decide; `is_direct_root`), else
the rung fails with `not_direct_root`. The plan's rationale for the rule is that
different variants cannot then land on different roots; the measurement below shows
that at high gamma* the b > 0 part does not choose between roots but cuts one root
family short (**Direct-root boundary**). A rung also fails on a failed starting shot,
a singular Jacobian, a non-finite step, a failed line search or the iteration limit.

**Guess ladder** (`ltg_guess_ladder`, in order): warm (this run's last converged pair,
when given, from the run's `search.WarmStore`), physics (p0 = gamma_in + 5 deg with
gamma_in = atan2(v_r, v_theta) the inertial flight-path angle at stage-2 ignition, p_f
= -1 deg over tau_b: a = tan p0, b = (tan p0 - tan p_f)/tau_b; `ltg_physics_guess`),
steep (p0 = 35 deg with the same p_f) and shallow (x = (0.3, 0.3)). A gamma* grid
point tries at most `grid_max_rungs` (2) rungs (`LtgSettings.from_config(grid=True)`),
any other solve the whole ladder. Exhausted, the ladder raises GuidanceFailure
`nonconverged` naming each rung's outcome; an unconverged x is never returned.
`solve_stage2` first applies the `lofted_overshoot` pre-screen.

**Measured** (gate pad, gamma* 20 deg, 22.8 t, rtol 1e-10 with dense output off): the
physics rung converges in 3 iterations and 10 shots (0.056 s; a shot is 4.5 ms and 488
RHS calls at rtol 1e-10, 3.1 ms at the search setting rtol 1e-8 with atol x 10, where
the same solve takes 0.030 s and moves m_res by 0.09 g); the steep rung in 2
iterations and 7 shots; the shallow rung's first shot dives into the ground at 461.9 s
(typed impact). Roots from different rungs agree within 1.1e-7 in a and 3e-10 1/s in b,
and wider random guesses within 5.8e-7 and 1.6e-9 (review probe, 120 guesses). The
acceptance box, not the solver, bounds that spread: through the Jacobian at the root
(d(r_c, v_r,c)/d(a, 100 b) = [[5.05e5 m, -8.64e5 m], [4.10e3 m/s, -1.03e4 m/s]],
scaled condition number 13.3) a root inside the box can lie up to 6.7e-6 in a and
2.8e-8 1/s in b from the exact one, so two accepted roots up to twice that apart;
the tests compare roots at that box-implied tolerance, computed from a
finite-difference Jacobian (measured 1.34e-5 and 5.5e-8 1/s), not at the observed
spread. Newton converges quadratically well inside the box, which is why the observed
spread is 20 to 100 times smaller. Of 40 seeded random guesses (a in
[-1, 3], 100 b in [-1, 2]) 13 converge to the same root in 4 to 5 iterations and 27 dive
into the ground on their first shot (the plan's prototype had 18 of 40). With 30 t of
payload the physics rung's first shot dives (impact at 511.6 s) and the steep rung
converges: the ladder is in use, not decoration. The search-setting finite-difference
step and the rung cap stay as shipped until the stage-1 noise floor decision ("gamma*
inner solve", Noise floor); on the gate pad every grid point after the cold midpoint
converges from the warm rung ("Payload and gamma* search", Measured).

**Direct-root boundary** (measured; the rule is pre-registered, and whether to keep
its b > 0 part is a question for the user). Scanning gamma* at 22.8 t with the b > 0
test switched off (the pitch window kept; rtol 1e-10, warm continuation), each case
has a single root family whose b falls smoothly through zero while m_res stays
positive and smooth:

| Case | m_res optimum (gamma*, m_res) | last gamma* with b > 0 | first gamma* with b < 0 | b = 0 at |
|---|---|---|---|---|
| pad | 22 deg, 3,242.7 kg (23: 3,235.1) | 30 deg: +2.78e-5 1/s, 2,342.2 kg | 31 deg: -1.33e-4, 2,126.2 kg | 30.2 deg |
| silo_cold (3 g, 100 m, lit 0.5 s) | 21 deg, 4,713.1 kg | 27 deg: +9.35e-5, 3,985.9 kg | 28 deg: -9.38e-5, 3,765.2 kg | 27.5 deg |
| 5 g, 300 m (lit 0.5 s) | 19 deg, 6,708.7 kg | 24 deg: +1.02e-4, 6,093.8 kg | 25 deg: -1.21e-4, 5,858.6 kg | 24.5 deg |

At gamma* 32 deg on the pad 200 random guesses find only the b < 0 root (a = 0.0948,
b = -2.86e-4 1/s, m_res 1,894.7 kg; review probe), and the physics and steep rungs
both converge to it (`test_the_only_high_gamma_root_is_indirect_by_rule`). So with the
rule as shipped, grid points above the boundary (32 to 36 deg on the pad; 28 to 36 deg
for silo_cold and, in a review probe, silo_hot_full: 5 of the 15 grid points) end `nonconverged` with
every converging rung reporting `not_direct_root`: infeasible by the pre-registered
rule, not by the physics. The boundary lies 8 deg above the pad's optimum, 6.5 deg
above silo_cold's and 5.5 deg above the fastest sweep point's; it moves toward the
optimum as the release speed rises, and it binds on none of the shipped runs at
fixed gamma*. If it ever bound, it would cap the variant, which is conservative for
the assist. The search labels such grid points `not_direct_root` rather than
physically infeasible, and flags a run whose refine window (the best grid point +/- 4
deg) holds one ("Payload and gamma* search").

**Cold-ladder coverage** (measured, rule as shipped, no warm pair, rtol 1e-10). The
physics rung's first shot dives into the ground for gamma* <= 16 deg on the pad and <=
14 deg for silo_cold (there an initial pitch of about 50 to 70 deg is needed, far above
gamma_in + 5 deg). The steep rung then solves 12 to 16 deg on the pad and 10 to 14 deg
for silo_cold; nothing in the cold ladder solves 10 deg or below on the pad (physics
and shallow impact, steep mass_floor) or 8 deg for silo_cold (all three impact),
although warm continuation from a converged neighbour in 2 deg steps reaches those
roots (pad 10 deg: m_res -1,017 kg; 8 deg: -2,845 kg; review probe). The shallow rung
dives into the ground at every grid point from 8 to 36 deg, so it never contributes;
at 45 and 50 t of payload the cold ladder fails where a warm start converges. A grid
point tries warm then physics only (`grid_max_rungs` 2), so a failed warm start falls
back to the rung that fails in this regime. So a cold `nonconverged` is not by itself
evidence of infeasibility: the search retries such a point from each adjacent
converged grid point before applying the penalty, and flags any point solved only
after that retry ("Payload and gamma* search"). Replacing
the shallow rung (for example by a lofted rung at p0 about 65 deg) is a change to a
shared solver setting, left to the user before the pre-registration commit.

**Validation** (`test_ltg.py`):

- Flat linear tangent: a constant thrust acceleration A = 15 m/s^2, g_test, tan p =
  tan p0 - c t (p0 = 40 deg, c = 0.004 1/s) for 300 s from rest, 1,000 km above a datum
  of radius 1e14 m, vacuum: v_x = (A/c) ln[(tan p0 + sec p0)/(tan p + sec p)] and
  v_y = (A/c)(sec p0 - sec p) - g t (1e-6 relative; measured 1.4e-9 and 3.6e-8, the
  curvature v^2/R).
- LTG optimality (amendment 11; slow as the plan asks, 0.1 s measured): on a flat
  Earth in uniform gravity with a fixed burn time a linear tangent maximises v_x,f for
  given (h_f, v_y,f), so adding eps tau^2 (`LinearTangentEps`, eps = +/-5.6e-7 1/s^2)
  and re-solving (a, b) with `solve_ltg` for the same h_f and v_y,f = 0 (from p0 = 70
  deg, datum 1e10 m, acceptance 1e-4 m and 1e-8 m/s) leaves v_x,f unchanged to first
  order: |v(+eps) - v(-eps)| / (2 v(0)) = 5e-9 (< 1e-6 asserted) against a
  second-order drop of 2.4e-6, and v_x,f is largest at eps = 0.
- The Newton on a synthetic linear residual (no flight): when the forward shot of the
  a column raises, the column comes from the backward shot at a - h, and one step lands
  on the root (1 iteration, 5 shots); when the first trial raises, the step is halved
  to the midpoint (2 iterations, 8 shots); the root's b = x_2/100.
- On the gate fork: every rung (warm 2 % off, physics, steep) converges to the same
  direct root with E = E* (1e-9 relative), |r - r_t| < 1 m, |v_r| < 1e-3 m/s, e < 1e-6
  (roots compared at the box-implied tolerance);
  a diving guess raises typed impact and its ladder nonconverged; one Newton
  iteration is not enough (nonconverged); a pitch window from -1 deg excludes the
  root's -2.3 deg final pitch (not_direct_root, then nonconverged); the 40 random
  guesses (slow).

## Rocket-equation closure (planar)

Module: `losses.py` (`rocket_equation_closure`, `ClosureTerms` with the fields
`d_id_mps`, `j_vac_mps`, `pre_mps`, `fair_mps`, `dv_margin_mps` and the property
`residual_mps`). Test: `tests/test_closure.py`. Every term in m/s; c = g0 Isp_vac per
stage.

With m0 the stack at stage-1 ignition, m_fs the mass at the flight start, m1 = m0 -
m_p1, m2 = m1 - m_d1 - F (the fairing always counted as dropped at staging, as the
screening does), m3 = m_d2 + P, F2 the fairing carried into stage 2 (F unless it
dropped at staging, else 0), m_f+ the mass just after its drop and m_c the mass at the
cutoff:

    D_id(P) = c1 ln(m0/m1) + c2 ln(m2/m3)
    J_vac   = c1 ln(m_fs/m1) + c2 [ln((m2 + F2)/(m_f+ + F2)) + ln(m_f+/m_c)]

because every burn has dm/dt = -T_vac/c. With dv_margin = c2 ln(m_c/m3):

    D_id(P) = J_vac + c1 ln(m0/m_fs) + c2 ln[(1 + F2/m_f+)/(1 + F2/m2)] + dv_margin

(pre = c1 ln(m0/m_fs): the hold-down and the track burn; fair: the cost of carrying the
fairing into stage 2, 0 when it dropped at staging). A fairing never dropped (rule
never) is the limit m_f+ = m3 with dv_margin = c2 ln(m_c/(m3 + F2)). The residual
D_id - (J_vac + pre + fair + dv_margin) is zero up to the integration error of J_vac
when the mass bookkeeping (payload, fairing, staging, the maps, the depletion) is right;
`checks.closure_tol_mps` (1e-5 m/s) gates it (status `bug_suspect`, "Screening-beat
rule (2-D)").
The run supplies m_fs (flight start), the stage burnouts and the `fairing` event (its
record holds the mass before the drop; the drop counts as at staging under rule
staging or when the event lies in COAST_STAGING).

**Measured** (gamma* 20 deg, 22.8 t, the LTG pair solved, recorded at rtol 1e-10):
residual -7.7e-8 m/s (pad), -9.3e-8 (silo_cold), -9.4e-8 (silo_hot_full), -7.8e-8
(the 10 s ramp). Pad terms: D_id 9,404.61, J_vac 9,007.79, pre 14.49 (2,697 kg on the
hold-down), fair 4.72, dv_margin 377.62. The same trace checked against a payload 100
kg lighter misses by 0.58 m/s, 5e4 times the tolerance.

At the same gamma* silo_cold ends with dv_margin 551.8 m/s against the pad's 377.6.
That is not a result (gamma* is fixed here, not optimised per run as the search does: at 20 deg
silo_cold sits near its optimum and the pad about 107 kg below its own), and the split
behind the +174.1 m/s is not mainly gravity. At equal P, D_id is the same for both
runs, and the closure with the loss identity gives D_id = (V_f - V_0) + L + pre + fair
+ dv_margin (L = J_grav + J_drag + J_steer + J_bp, up to the two residuals of order
1e-8 m/s). So with d = silo_cold - pad, exactly,

    d dv_margin = dV_0 - dV_f - dL - d pre - d fair

term by term [m/s]. V_f equals the target's V_rel,f only to within the LTG acceptance,
not exactly (the plan's attribution assumed "V_f equal, exactly"):

| Term | pad | silo_cold | contribution to d dv_margin |
|---|---|---|---|
| V_0 (release speed) | 0 | 76.71 | +76.7 |
| V_f - V_rel,f (acceptance) | +3.140e-5 (dr -2.5 cm) | -1.2e-6 (dr +0.96 mm) | +3.26e-5 |
| J_grav | 1,435.06 | 1,407.96 | +27.1 |
| J_drag | 27.54 | 23.30 | +4.2 |
| J_steer | 119.17 | 82.56 | +36.6 |
| J_bp | 63.32 | 49.70 | +13.6 |
| pre | 14.49 | 0 | +14.5 |
| fair | 4.72 | 3.33 | +1.4 |

(J_vac 9,007.79 and 8,849.53.) With the dV_f row the terms sum to d dv_margin =
174.1393376 m/s within 1.9e-8 m/s (the difference of the two runs' closure
residuals); without it the gap is 3.26e-5 m/s. At E = E*, a radius error of 1 m moves
V_f by -(g/v + omega_p) = -1.247e-3 m/s, so inside the shipped acceptance |dV_f| can
reach about 2.5e-3 m/s, 250 times the 1e-5 m/s of the plan's matched-payload
attribution test. `compare.matched_attribution` therefore carries the dV_f term, and
its test checks it (with V_f assumed equal the test could not pass at 1e-5 m/s). Of the 97.4 m/s gained beyond the release speed, the
steering term (kick and stage 2) is the largest single one, and drag plus steering
carry 40.9 m/s, 42 % of it (50 % of the loss part alone), close to the 50 % limit of
mechanism check M4. Reading 551.8 against 377.6 as a gravity-loss (time-shift) gain
would overstate that mechanism. The pipeline checks M4 on the per-run-optimised
matched-payload runs, not on fixed-gamma* runs like these.

**Validation** (`test_closure.py`): D_id from the vehicle's masses (1e-14); the per-stage
J_vac against c ln(m_start/m_end) with the logged masses (1e-9 relative); pre, fair
and dv_margin written in the test; the residual below 1e-5 m/s for the heating rule,
rule staging (fair exactly 0), rule never (m_f+ = m3, flagged) and silo_hot_full (the
track burn mdot (t_r/2 + sqrt(2L/a)) in closed form within 1e-6 kg); a payload
mismatch is caught; a run without a stage-2 burnout is refused. Under rule never the
search shot's m_empty is m_d2 + P + F and, at 30 t, the final mode ends at the
depletion at exactly that mass after tau_b (`test_a_fairing_still_on_is_empty_mass`).

## Max-Q and loads (planar)

Module: `metrics_planar.py` (`scan_peak`, `Peak`, `max_q`, `MaxQ`,
`dynamic_pressure_pa`, `psi_rad`, `q_alpha_pa_rad`, `felt_accel_g`, `felt_axial_g`,
`felt_lateral_g`). Test: `tests/test_max_q.py`. The metrics dictionary, the flags
against the baseline and the time series: "Reporting definitions (planar)".

**Scan and refine** (`scan_peak(phases, fn, n_points, xatol_s, kinds)`), independent
of the output sampling interval, which the planar integrator lock needs ("Integrator"):
every flight phase contributes its two end states (its own, not interpolated, so a
peak on a phase boundary, a thrust kink or a mass map, is exact) and n_points uniform
samples of fn on its dense output (`checks.maxq_scan_points` = 256; one vectorised
dense-output evaluation per phase since build step 24, which cut the four scans of a
recorded run from about 0.7 s to 0.17 s). Every sample at
least as high as both neighbours and strictly higher than one (one neighbour at an end
sample) brackets a local maximum that a bounded Brent search refines on the dense
output over the two neighbouring intervals (`checks.maxq_xatol_s` = 1e-6 s). A maximum
narrower than the scan spacing (span/255, 0.6 s on a 150 s phase) between two lower
samples can be missed. A phase integrated with dense output off is refused (a search
evaluation has no interior).

**Quantities.** q = 0.5 rho V^2 with V = |v_rel| and rho at h (`max_q` reports q, the
time, the altitude, the Mach number and the phase); unthrottled, so an upper bound on
the flown max-Q (plan decision 6). q-alpha = q psi, psi the angle between the thrust
axis and v_rel (alpha = psi: point mass, body axis = thrust axis, no lift). The felt
(proper) acceleration is the non-gravitational one, (T e - D v_hat_rel)/m, projected on
the thrust axis and its normal:

    axial = (T - D cos psi) / (m g0),     lateral = D sin psi / (m g0)

(`units.to_g`); in an unpowered phase the axis is v_rel by convention (psi = 0): axial
-D/(m g0), lateral 0.

**Measured** (gamma* 20 deg, recorded runs; fixed-gamma* numbers, not findings):

| run | max-Q [kPa] | t after release [s] | h [m] | Mach | peak q-alpha [Pa rad] (where) | peak felt axial [g] | peak felt lateral [g] |
|---|---|---|---|---|---|---|---|
| pad | 38.70 | 65.51 | 11,019.1 | 1.563 | 82 (kick start, 12.27 s) | 5.30 (MECO) | 1e-4 |
| silo_cold | 32.31 | 57.21 | 11,019.1 | 1.428 | 144 (kick at ignition, 0.5 s) | 5.30 (MECO) | 1e-4 |
| silo_hot_full | 33.67 | 52.92 | 11,019.1 | 1.458 | 275 (kick at release) | 5.30 (MECO) | 2e-4 |

All three peak exactly at the tropopause (11,000 m geopotential, 11,019.1 m
geometric). There the ICAO density's logarithmic slope steepens by L/T = 3.0e-5 1/m
(d ln rho/dh = -(g/(R T) - L/T) below it and -g/(R T) above), so d ln q/dh changes
sign on the kink and the refine lands on it. The unthrottled 38.7 kPa exceeds the
flown 22 to 30 kPa at Mach 0.9 to 1.3 (F9 throttles through max-Q); this is the stated
bias. q-alpha peaks where each kick starts: the pad kicks at 50 m/s (q about 1.5 kPa
times 3.1 deg), while the silo releases kick at 72 to 77 m/s low over the mouth, with 2
to 3.4 times the pad's q-alpha. The model has no angle-of-attack aerodynamics, so this
load costs nothing in the trajectory: it is reported (and flagged against the
baseline, `q_alpha_above_baseline`), not penalised.

**Validation** (`test_max_q.py`): from rest under a constant radial 20 m/s^2 in no
gravity through rho0 exp(-h/H) (1.225 kg/m^3, 7,000 m) on a datum of radius 1e7 m: t* =
sqrt(2H/a) = 26.4575 s within 1e-4 s, q* = rho0 a H/e = 63,091 Pa within 1e-9, at h = H
(1e-3 m) (the plan's R = 1e12 m would put t* 3.5e-4 s off through the altitude
quantisation, step-20 review); the thrust cut at 20 s: the peak on the boundary, t
exactly 20 s and q = 0.5 rho0 (a t_b)^2 exp(-a t_b^2/(2H)) within 1e-9; 32, 256 and
1,024 scan points agree (1e-5 s, 1e-12); on the gate pad no q sample on a 0.01 s grid
beats the scan; the felt axial and lateral acceleration, psi and q-alpha of a
hand-built state against the force balance written in the test (1e-12 relative).

## Figures of merit (planar)

Module: `search.py` (`ResidualResult`, `PayloadResult`, `FinalResult`, `RecordedRun`,
`SearchRecord`). Tests: `tests/test_payload_search.py`, `tests/test_search.py`,
`tests/test_convergence_2d.py`. CLAUDE.md's ladder, in increasing fidelity:

1. **Ideal screening** (`vehicle.py`, unchanged): the rocket equation from the vehicle's
   masses and screening Isp; a heating-criterion fairing counts as a drop at staging.
2. **Residual propellant at a fixed payload P** (rung 2, `residual`): the stage-1
   flight at gamma* (delta solved, "gamma* inner solve"), the LTG pair solved ("LTG
   shooting"), and at the energy cutoff

       m_res = m_c - m_empty,    dv_margin = c2 ln(m_c / m_empty),    m_empty = m_d2 + P (+ F if still on)

   both signed (a fairing still on at the cutoff is empty mass and flagged, "Stage 2
   and insertion (planar)"). A search evaluation flies with virtual propellant (next
   section), so m_res < 0 means the burn to the cutoff expels |m_res| more than the
   real load: a virtual, massless shortfall with no hardware meaning (not the
   propellant a larger tank would need). The physically meaningful shortfall of a
   vehicle above its capacity is the payload excess P0 - P* (`payload_excess_kg`,
   reported beside the virtual figure) and the signed dv_margin along the flown
   trajectory.
   The reported rung 2 is the final-tolerance evaluation at the vehicle payload P0 and
   the run's gamma*_ref (`SearchRecord.at_p0`: for figure_of_merit `payload` one extra
   final-mode evaluation after the final verification; for `residual` the final
   evaluation itself). A negative value keeps its sign in every record; for
   figure_of_merit `residual` it gives the run status `short_of_orbit` (plan section
   5), otherwise `ok`. When P0 cannot fly at all, at_p0 is None and flagged.
   **Which gamma*.** For `payload`, gamma*_ref is the P*-optimal gamma* (refined at
   P1), not re-optimised at P0, so m_res at P0 sits below the best m_res at P0 by an
   amount that grows with P* - P0. Measured in the step-23 review (final mode, a
   bounded Brent over gamma* at P0): pad 9.0 kg (gamma*_ref 22.99 deg against the P0
   optimum at 22.30 deg), silo_cold 18.8 kg, silo_cold at 5 g / 300 m 36.4 kg. This
   under-states an assisted run's residual-propellant gain against the pad (it works
   against the assist, never for it). For `residual`, gamma* is refined at P0 itself,
   so the two figures of merit report different quantities under the same name: the
   pipeline labels the payload-run value "at gamma*_ref (P*-optimal guidance)"
   (`residual_propellant_basis`) and never compares residual_propellant_kg across
   figures of merit.
3. **Payload capacity** (rung 3, `payload_capacity`, `final_verify`): P* with
   m_res(P*; gamma*) = 0 at the run's sweep-optimized gamma*. The reported P* is
   P_final, the largest payload the final verification evaluated with m_res >= 0 at
   the final tolerance, so 0 <= m_res(P_final) < `final_payload_xtol_kg` (0.05 kg):
   an actually verified payload, never an interpolated root. When even P = 0 misses
   the orbit (m_res(0) < 0) the status is `no_orbit` with P* = 0 and the shortfall
   dv_shortfall = -dv_margin(0) [m/s], reported, not NaN.

**Recorded run.** The trajectory every reported number comes from is the recorded run
at P_final (`SearchContext.record`): `PlanarPlanner.run` with the delta and the LTG pair
of the final verification's evaluation at P_final, dense output on, the final
tolerance, and the real stage-2 depletion event (no mass floor, no virtual
propellant). It must end `inserted` with 0 <= m_res < final_payload_xtol_kg, else
the search fails (`final_run`). It re-flies that evaluation: DOP853 takes the same
steps with dense output on and off and the event lists do not change the steps, so on
the gate pad its stage-2 end state equals the evaluation's cutoff state bit for bit
(tested to 1e-9 relative), and every event of the evaluation is logged again at the
same time and state. For figure_of_merit `residual` the recorded run is at the
vehicle's payload, where a negative m_res ends it `short_of_orbit` (the real
propellant runs out before the cutoff); so does the recorded run of a `no_orbit`
search at P = 0. Such a run has no cutoff state, and its own m_res at depletion is ~0
by construction, which would hide the shortfall: `RecordedRun` then carries the signed
m_res and dv_margin of the final evaluation it re-flies (`figures_from` =
`final_evaluation`, `cut_state_rel_diff` NaN), never the clipped value. A recorded run
that reaches the cutoff has `figures_from` = `recorded_run` (measured at its cutoff).
The search checks the agreement (`final_run` otherwise): m_res >= 0 needs an inserted
recorded run (with m_res < 0.05 kg after a payload search), m_res < 0 a recorded run
short of the cutoff.

Results are "sweep-optimized": gamma* is the best point of a shared grid refined by
a bounded Brent search, not an optimal-control solution (Phase 5).

## Virtual propellant

In every search evaluation stage 2 has no depletion event: at the same thrust and mass
flow it burns on past its real load m_p2 until the energy cutoff (`PlanarPlanner.stage2`
with virtual_propellant; `m_empty_kg = NaN` leaves the propellant event out). m_res(P)
is then one smooth function through zero, where a real stage 2 would run dry exactly
at the cutoff, instead of a function that stops existing there (a real depletion
before the cutoff has no cutoff state, hence no m_res): brentq needs values of both
signs. **Meaning of a negative m_res.** Past the real load the burn goes on expelling
mass below the empty mass m_d2 + P, so a negative m_res is |m_res| of extra propellant
that weighed nothing until it was burned: a continuation that keeps m_res(P)
continuous for the root finders, with no hardware meaning. It is not the propellant a
stretched tank (same dry mass, same engine) would need: carried from liftoff, extra
propellant slows stage 1 and stage 2 (T/W < 1) and makes the shortfall larger. The
step-23 review measured this on the gate pad at gamma* 22 deg about 0.95 t above its
payload root (search mode, rtol 1e-9): m_res = -975.0 kg with the real load, -990.3 kg
with 975 kg more real stage-2 propellant, -1,098.5 kg with 4.9 t more and -5,643.8 kg
with 37.5 t more; m_res falls monotonically with the added propellant, so no stretched
tank reaches the orbit. The negative value is nevertheless reported, signed, where the
search is asked for rung 2 at a payload above capacity (`SearchRecord.at_p0`, a
`short_of_orbit` residual run, a recorded run with `figures_from` =
`final_evaluation`); the summary labels it a "virtual, massless shortfall"
(`residual_propellant_virtual`) and reports the payload excess P0 - P* next to it for a
payload search.

The mass floor keeps a shot from burning on toward zero mass: at m = mass_floor_factor
(m_d2 + P) (0.5; the fairing not counted) the shot ends with GuidanceFailure
`mass_floor`, the LTG ladder tries its next rung, and an evaluation whose ladder is
exhausted raises `nonconverged` naming it. The floor only bounds absurd shots: it sits
far below any payload near P*.

**Measured** (gate pad). The slope |d m_res / d P| near the zero of m_res depends on
gamma*: 1.0255 kg/kg at gamma* = 20 deg (each kg of payload also slows the ascent;
1.0186 as the secant from 22.8 t) and 1.0011 at the searched gamma*_ref = 22.99 deg
(the secant over the final bracket and the local slope over +/-0.5 kg agree). At 20
deg the second differences over 20 kg steps stay below 0.006 kg at the shipped search
rtol (2e-3 kg at the tests' 1e-9), so the virtual propellant adds no kink at
depletion. Evaluation noise at gamma*_ref: final mode, 21 payloads over P* +/- 0.5 kg
(linear trend removed), std 3e-5 kg (largest 1.3e-4 kg), and over P* +/- 500 kg in 25
kg steps (quadratic trend removed, step-23 review) std 2.3e-4 kg (largest 5.1e-4 kg),
no outliers: at least two orders of magnitude below its 0.05 kg xtol. Search mode
(rtol 1e-8) has a heavier tail: std 1.2e-3 kg over +/- 0.5 kg, but over +/- 500 kg std
1.4e-2 kg with reproducible outliers up to 0.08 to 0.09 kg (the search-mode m_res 425
kg below P* sits 0.091 kg below its neighbours from four different warm starts, the
final mode 0.002 kg: tied to the search tolerance, not to the warm start), about 5x
below the 0.5 kg search xtol; the same payload evaluated from four different warm
stores spreads by 6e-4 kg (final) and 7e-4 kg (search). In gamma* at P1 (search mode,
22 to 24 deg in 0.02 deg steps) the residual std is 2.5e-3 kg with outliers up to 0.02
kg, while m_res changes by only 1.8e-3 kg over one gamma_xatol (0.01 deg; curvature
-36.8 kg/deg^2): the refine is noise-limited at the search rtol and resolves gamma* to
about 0.01 to 0.07 deg (a fitted vertex 22.980 deg against the refine's 22.989 deg),
harmless at the 0.1 deg reporting resolution (P* moves by at most about 0.1 kg).
Continued in payload from 22.8 t, 35 and 45 t still reach the cutoff on virtual
propellant (m_res negative and falling) and at 60 t the warm shot reaches the floor
(typed; the other rungs dive into the ground). In the closed-form toy (validation
below) the payload root's first high end hits the floor and backs off.

## Payload and gamma* search

Module: `search.py`. The algorithms act on any `SearchProblem`: a `budget`
(`SearchBudget`), the payload P0 of the grid (`payload_kg`, the vehicle's own
payload) and `evaluate(P, gamma*, warm, mode)`, which returns a `ResidualResult` or
raises one of `INFEASIBLE` (a typed `GuidanceFailure`, or `PreludeFailure` when the
prelude ends without a flight: `no_liftoff`, `drive_limit`, a failed stage-1
ignition); any other exception is a code error and propagates. `SearchContext` is the
planar problem, built from a validated run by `SearchContext.from_run` (mu/r^2,
omega_p from the site, ICAO, the assist and track with g_eff = g_ref, the
IgnitionSpecs, the kick guidance, r_t, the run's integrator settings, the shared
budget).

**Evaluation modes.** `grid` and `search`: rtol `search_rtol` (1e-8), every atol x
`search_atol_scale` (10), dense output off, `fd_step_search`; a grid point tries at
most `grid_max_rungs` (2) LTG rungs, every other evaluation the whole ladder. `final`:
rtol `final_rtol` (1e-10, the run's integrator rtol), the per-state atol, dense output
off, `fd_step_final`. One evaluation: the kick point of this payload (the prelude and
the vertical rise, independent of delta; flown once per payload and tolerance class
and cached), the delta solve for gamma* through the staging coast, and the LTG
shooting from that hand-over (virtual propellant).

**Warm starts** (`WarmStore`, one per run). Every solved evaluation is remembered
(gamma*, P, delta, (a, b)); an evaluation starts its delta solve and its LTG ladder
from the entry with the nearest gamma* (the latest on a tie), cold when the store is
empty (the first grid point). There is no cross-run seeding and no module-level cache:
a run's results depend only on its own inputs and its own deterministic evaluation
order, never on which run went before (tested by swapping the run order). A warm start
changes only where the solves begin; their tolerances decide where they end. A store
also caches the kick point per (payload, tolerance class), which depends on the
vehicle, the assist and the ignition, not only on that key, so a store is bound to the
first problem that evaluates with it (`WarmStore.claim`): any other context, a
perturbed vehicle or the same run tightened included, raises ValueError instead of
reusing its kick point (a shared store gave a 70 kg error with stage-1 dry mass +10 %
in the step-23 review).

**Payload root** (`payload_root`, used by `payload_capacity` and `final_verify`).
m_res(P) is decreasing and, with virtual propellant, continuous. Bracket: low = max(0,
P_hint - h), high = P_hint + h with h = `payload_half_bracket_t` (2 t), doubled at
most `payload_max_expand` (6) times. The low end must fly with m_res >= 0: a negative
low end becomes the high end and the low end expands downward (never above that high
end minus the first half-width), and a negative m_res at P = 0 is `no_orbit`. The high
end must fly with m_res < 0: a non-negative one becomes the new low end and the high
end expands. An end that raises backs off, at most `payload_backoff_max` (4) times in
all: the low end halfway toward the nearest payload above it that flew, or, when none
flew, halfway toward 0 (in this problem a payload fails because the vehicle is too
heavy: the mass floor, an impact; toward the hint only from P = 0), except in the
final verification, whose hint flew at search tolerance, where it backs off halfway
toward the hint; the high end is never probed again at or above a payload that failed,
so it moves halfway between the low end and the lowest failure. Out of expansions or
backoffs: SearchFailed `bracket`. Every backoff of P1, P2 and the final verification
is flagged (`P1_backoff`, `P2_backoff`, `final_backoff`) with the failed payloads and
their failure kinds, so an evaluation that fails near P* is reported, not only
counted. Then scipy brentq (xtol `payload_xtol_kg` 0.5 kg, rtol `brentq_rtol` 4 eps)
through a logging wrapper: every evaluation is logged with its payload, m_res and
dv_margin or its failure, and evaluations are cached by payload (brentq's end-point
calls fly nothing). brentq returns a root, not its bracket, so the result is P_lo, the
largest logged payload with m_res >= 0, with the root and the bracket recorded beside
it. An infeasible evaluation inside the bracket is SearchFailed `root`. P_hint is the
vehicle's payload for the run's first payload search, then P1.

**gamma* sweep** (`optimise_gamma`, deterministic):

1. The grid over gamma* in [8, 36] deg, step 2 (15 points), at P0, objective m_res,
   evaluated centre-out from the midpoint (22, 24, 20, 26, 18, ..., 36, 8 deg), each
   point warm-started from its nearest solved neighbour. Then, in the same order, each
   point that failed with `nonconverged` (an exhausted LTG ladder, which depends on its
   starting pair) is retried from each adjacent converged grid point whose solution it
   did not start from (a cold `nonconverged` is not evidence of infeasibility, "LTG
   shooting", Cold-ladder coverage); stage-1 failures (`gamma_unattainable`,
   `false_root`, `no_kick`) and `lofted_overshoot` do not depend on the starting pair
   and are not retried. The retry pass repeats until a pass solves no new point, so a
   point whose neighbours converge only in a retry gets its turn (bounded: each
   neighbour seeds a point once; deterministic). Points solved only after a retry are
   flagged.
2. Labels: `feasible`; `infeasible`; `not_direct_root` when the ladder converged only
   to roots the pre-registered direct-root rule rejects (a `nonconverged` whose rung
   outcomes name `not_direct_root`: infeasible by the rule, not by the physics, "LTG
   shooting", Direct-root boundary). An infeasible point scores the finite penalty
   -(`penalty.base_kg` + `penalty.per_deg_kg` x the distance in degrees to the
   nearest feasible grid point) (1e6 kg + 1e4 kg/deg): below every real m_res,
   decreasing away from the feasible region, never -inf (a bounded Brent would warn
   on it, and warnings are errors in the tests). No feasible point at P0: for
   figure_of_merit `payload` the grid is run once more at P = 0 (flagged; the rest of
   the sweep then starts from P = 0, so a vehicle too heavy for P0 is reported as
   `no_orbit` with its shortfall, or with its small P*, instead of NaN, as the plan's
   "low-capacity runs must be reported" requires); for `residual`, or when the grid at
   P = 0 fails too, SearchFailed `grid`. A run whose refine window (best point +/- 4
   deg) holds a `not_direct_root` point is flagged.
3. The best grid point on a grid bound: SearchFailed `edge`; the run gets status
   `search_failed` with NaN figures of merit and the experiment continues. The remedy
   is to widen the shared grid for every run, never for one.
4. P1 = `payload_capacity`(gamma_best, hint = the grid's payload, P0 or 0).
5. Refine: scipy's bounded Brent (`minimize_scalar`, method bounded) on -m_res(gamma*;
   P1) over gamma_best +/- `gamma_refine_halfwidth_deg` (4) clipped to the grid, xatol
   `gamma_xatol_deg` (0.01 deg), at most `gamma_refine_maxiter` (30) evaluations; a
   failed evaluation scores its penalty. m_res at fixed P1 is smooth, where P* carries
   brentq's 0.5 kg steps; by the envelope argument the gamma* that maximises m_res at
   P1 also maximises P* to first order. A result within xatol of an interior window
   edge shifts the window once (centred on the result) and is flagged; a result that
   is not a feasible evaluation (only when every refine evaluation failed) falls back
   to the best grid point, flagged, with the refine objective recorded as NaN (that
   point's m_res is known at P0, not at P1). The shift flag names both results; a
   result that ends again within xatol of an interior edge of the shifted window is
   flagged `refine_capped`: the optimum at P1 may lie beyond it, which happens when the
   optimum moves between P0 (the grid) and P1 (the refine), for example for a vehicle
   payload far above capacity (a flat, misleading grid at P0). Such a run is reported
   with the flag; whether it should fail its search instead, or re-run the grid at P1,
   is a pending user decision. The result is gamma*_ref. A gamma*_ref
   within gamma_xatol of a grid bound means the optimum at P1 lies at or beyond the
   shared grid (the optimum moves with the payload): SearchFailed `edge`, as in step 3,
   never a result silently capped by the grid.
6. P2 = `payload_capacity`(gamma*_ref, hint P1). |P2 - P1| and the grid table are
   recorded.

**Final verification** (`final_verify`): the payload root at gamma*_ref in final mode
(delta and the LTG pair re-solved at the final tolerance, warm from the search), from
P2's P_lo with the half-widths 20, 40, ..., 640, 1000 kg (`final_bracket_kg` [20,
1000]); an expansion is flagged `search_final_mismatch` and the final value is used;
no bracket within 1 t is SearchFailed `final_bracket`. brentq's xtol is
min(`final_payload_xtol_kg`, `final_payload_xtol_kg` / |slope|) with |slope| the
secant |d m_res / d P| over the bracket: the criterion is on m_res, and with a slope
above 1 kg/kg (it depends on gamma*: 1.0255 at 20 deg on the gate pad, 1.0011 at its
gamma*_ref) a 0.05 kg payload tolerance alone could leave m_res above 0.05 kg at P_lo.
P_final = the largest evaluated payload with m_res >= 0. A local slope above the
secant (curvature, noise) could still leave m_res(P_final) >= 0.05 kg; then the logged
bracket is bisected until it is not (flagged; never seen on the shipped runs), instead
of failing the run. A failing low end with nothing lighter flown backs off halfway
toward the hint (it flew at search tolerance), and every backoff is flagged
(`final_backoff`). Then the recorded run (above). `search_vs_final_payload_kg` =
P_lo(P2) - P_final is recorded and flagged above `checks.search_final_flag_rel` (1e-4)
x P_final.

**Whole search** (`run_search`): figure_of_merit `payload` runs the sweep (P1, the
refine, P2), the final verification and then rung 2 at (P0, gamma*_ref) in final mode
(`at_p0`; after everything else, so it changes no earlier number); `residual` runs the
grid and the refine at P0 (no payload searches) and then one final-mode evaluation at
P0 and its recorded run (`final_residual`). A `SearchFailed` (`edge`, `grid`,
`bracket`, `root`, `final_bracket`, `final_run`) becomes a `SearchRecord` with status
`search_failed`, NaN figures of merit, the failure and the grid table whenever the grid
was evaluated (a failed payload search or final verification keeps it); every other
exception propagates (FAILED.txt). Status otherwise: `ok` or `no_orbit` for `payload`,
`ok` or `short_of_orbit` for `residual`. The signed rung-2 figures at P0 are
`SearchRecord.m_res_p0_kg` and `dv_margin_p0_mps`; P* is `SearchRecord.payload_kg`
(P_final). figure_of_merit
`none` (fixed guidance, the skipped search of a failed ignition) has no search;
`sim.fly_without_search` flies its recorded run. The search record goes into the run's
metrics as `search_record` (`as_plain` gives the plain data; the stage-2 shots and
traces are left out).

**Test-only joint root** (`joint_root_crosscheck`): the three equations r_c = r_t,
v_r,c = 0, m_res = 0 solved jointly for (a, 100 b, P / 1e4 kg) at fixed gamma* with the
delta re-solved per payload, by a damped Newton with forward-difference Jacobians
(the mode's LTG settings; converged inside the LTG acceptance and |m_res| <
final_payload_xtol_kg). Rejected in production (plan section 3); the slow test uses it
as an independent check of the nested solve.

**Measured on the gate pad** (experiments/silo_screening_2d.yaml's pad; a search run,
not a calibration: the labelled calibration is build step 26, so no absolute payload
or m_res at P0 is quoted here). The grid's m_res at P0 relative to its best point (22
deg) [kg]: 8 deg -6,087.4; 10: -4,260.0; 12: -2,809.1; 14: -1,711.3; 16: -924.3; 18:
-403.2; 20: -107.0; 22: 0; 24: -51.1; 26: -233.3; 28: -523.2; 30: -900.5; 32, 34, 36:
`not_direct_root` (the Direct-root boundary at 30.2 deg). Every point after the cold
midpoint converged from the warm rung, none needed a retry, and the refine window [18,
26] deg holds no rule-infeasible point. The refine took 7 evaluations and moved gamma*
from the 22 deg grid point to 22.989 deg; P2 - P1 = +18.4 kg; the final verification
took 4 evaluations and moved the payload by 0.037 kg from P2 (no expansion, no
bisection, no flag); the recorded run ends inserted with m_res = 0.0004 kg and its
cutoff state equal to the evaluation's. Cost: 38 evaluations (15 grid, 18 in P1, the
refine and P2, 4 in the final verification and 1 rung 2 at P0; 3 of the grid ones
fail by the rule), 346 stage-1 flights and 260 stage-2 shots, 773,164 RHS calls over
1,780 phases, 8.3 to 9.5 s for the search (9.8 to 11.4 s with the import and the
experiment load; plan budget 30 s). By mode: grid 3.5 s (0.23 s per point), payload searches and
refine 3.8 s (0.21 s per evaluation), final 1.0 s (0.20 s per evaluation), recorded
run 0.05 s. The delta solve takes 10.8 stage-1 flights per flown grid point on
average (130 flights over the 12 flown points; 8.7 over all 15 grid points, the
denominator "Performance (measured)" uses),
10.4 per payload or refine evaluation and 5.8 per final evaluation (warm from the
search's delta), 13 to 19 cold (the plan estimated about 6): the inner solve dominates
every evaluation, as the step-22 review expected; the LTG shooting takes 10, 6.3 and
4.0 shots on average. A run with a lag startup costs more: the lag's step cap (tau /
lag_steps_per_tau = 0.25 s at tau = 1 s) holds for the whole lag-lit stage-1 burn, so
silo_cold_lag needs about 2.5x the pad's RHS calls (1.9 million; 25 to 26 s of
search, 27 to 28 s wall, measured in the step-23 reviews), 86 to 92 % of the 30 s
budget (capping the lag step over the first few tau only, a Plan-mode integrator
change, was left open in build step 25: "Performance (measured)"). Every other searched variant of silo_screening_2d takes 10 to 14
s of search, status ok, no flags (step-23 review).

**Noise floor and the budget** ("gamma* inner solve", Noise floor). The search
tolerances are not re-sized here: whether the planar flight phases get a max_step cap
is still the user's decision. With the uncapped floor, tightening the whole budget
10x moves P* by at most 3.4e-3 kg and gamma* by at most 6.3e-3 deg on the pad,
silo_cold and silo_cold_lag (build step 25), but the margins at P0 and the
gravity/steering split follow the noise in gamma*_ref: a variant difference in m_res
at P0 below about 0.4 kg, or in the split below about 0.15 m/s per term, is not
resolved ("Convergence (planar)", Finding). The
final-mode evaluation noise (above, "Virtual propellant": std 3e-5 to 2.3e-4 kg, no
outliers) is two orders of magnitude below its 0.05 kg xtol. The search mode is
noisier than the +/-0.5 kg scan suggested: outliers up to 0.09 kg in m_res(P) (about
5x below the 0.5 kg xtol) and 0.02 kg in m_res(gamma*), so gamma_xatol (0.01 deg) lies
below the search noise floor and the refine resolves gamma* to about 0.01 to 0.07 deg.
That is harmless at the 0.1 deg resolution gamma* is reported to (amendment 3) and
moves P* by at most about 0.1 kg, but it belongs to the pending decision on the planar
max_step cap and the search tolerances: a tighter search rtol or a coarser gamma_xatol
would make the refine tolerance-limited rather than noise-limited.

**Validation.** The planar tests fly the test budget: the shared search block with
search_rtol 1e-9 (CLAUDE.md: rtol <= 1e-9 in tests; the plan's test_budget), final
1e-10 as shipped; only the convergence tests fly the shipped 1e-8, because amendment 3
asks for the convergence of the shipped budget itself. `tests/test_payload_search.py`:
the toy two-stage rocket (c = 3000 m/s both stages, zero gravity, vacuum, thrust along
v from rest, flown with `integrate_phase` and `rhs_planar` to a speed target V* with
virtual propellant): `payload_capacity` finds P* with c ln(m0/m1) + c ln(m2/(m_d2 +
P*)) = V* (brentq in the test) within 0.5 kg, every flown evaluation's m_res equals
the rocket equation's (1e-6 kg), the high end that hits the mass floor backs off
(typed `mass_floor`), and P* is the largest evaluated payload with m_res >= 0 (never
the interpolated root); V* beyond the empty vehicle gives `no_orbit` with shortfall V*
- D_id(0) (1e-6 relative); the bracket's expansions, backoffs and `bracket` failures
on analytic m_res(P), a failing low end that backs off toward lighter payloads (toward
the hint under the final verification's rule), and a failure inside the bracket as
`root`; on the gate pad m_res(P) monotone and continuous through zero, the final
verification's recorded run (inserted, 0 <= m_res < 0.05 kg, the same cutoff state and
events as its evaluation to 1e-9, the real depletion event armed and the floor not),
and a recorded run short of orbit that carries its evaluation's negative m_res and
dv_margin; slow: the typed failure beyond the floor, the joint root equals the nested
solution (1 kg; measured 0.004 kg), and a pad with 32 t more stage-2 dry mass (no grid
point flies at P0) searched to `no_orbit` with its shortfall. `tests/test_search.py`:
on a closed-form toy m_res(P, gamma*) = A - K (gamma* - g0)^2 - S (P - P0), the
sweep's P1, gamma*_ref and P2, identical results on repetition, the labels, penalties
and warm retry, the edge failure and its record, a refine that converges onto a grid
bound (an optimum drifting with P) as `edge`, a vehicle too heavy at P0 reported as
`no_orbit` through the grid re-run at P = 0, the signed rung-2 figures at P0 for both
figures of merit (`short_of_orbit` for a negative residual), the grid table kept by a
failed payload search, a refine whose evaluations all fail falling back to the grid
(NaN objective), a failing refine interval scored without warnings, the warm retry
repeated until no new point solves, a refine capped by its shifted window
(`refine_capped`), P1 backoffs flagged, the final verification's backoff toward the
hint and its flags (`final_backoff`, `search_final_mismatch`,
`search_vs_final_payload`), its typed failures (`final_bracket`; `final_run` for a
recorded run that is off_target, keeps m_res >= 0.05 kg, stops short with m_res >= 0,
or reaches the cutoff at no_orbit), the bisection of a bracket whose secant slope
under-states the local slope, whole toy searches identical in swapped run order, the
budget and its tightening, the warm store; on the gate fork, the contexts of pad and
silo_cold, a warm store bound to one problem, and bitwise-identical evaluations in
swapped run order; slow: figure_of_merit residual at 30 t (`short_of_orbit`, the
signed figures in the record) and whole searches of pad and silo_cold on a three-point
grid identical in swapped order.

## Shared budget

CLAUDE.md: every run of an experiment shares the guidance settings and the optimizer
budget. Plan decision 4 reads this as the shared parametrisation, sweep grid and
optimizer budget, with the free guidance parameters sweep-optimized per run.
Concretely:

- **Shared** (experiment level, refused in variants, sweeps, sensitivity and bounds;
  "Experiment schema (planar)"): the stage-1 parametrisation (speed trigger v_k,
  hold-to-alignment kick, gravity turn along v_rel), the stage-2 law (local-horizontal
  linear tangent, energy cutoff), the gamma* grid, the refine window and tolerances,
  the delta, LTG, payload and final-verification settings, the integration tolerances
  of each mode, the penalties, and this algorithm (the centre-out order, the warm
  retry, the labels). `SearchBudget` holds them in SI; its `budget_id`, the sha256 of
  the experiment's search block, goes into every run, so equal ids mean equal budgets.
- **Per run**: gamma* (the best grid point, refined), the kick angle delta (solved for
  gamma*), the LTG pair (a, b) (solved by shooting) and the payload P* (solved). Each
  run keeps its own warm store; nothing learned in one run seeds another, so the
  order of the runs changes no result.
- **What a failure means**: a grid point that fails is a result of the shared budget
  and is reported (labelled, penalised), never fixed by a per-run setting. An optimum
  on the grid edge fails the run's search (`edge`) and calls for a wider grid for all
  runs; a grid point infeasible only by the direct-root rule is labelled as such, so a
  variant capped by the rule is visible (the cap is conservative for the assist).
- **Convergence** of the budget itself is checked by tightening it as a whole
  (`SearchContext.tightened`, "Convergence (planar)"), never by loosening it for a run
  that fails.

## Convergence (planar)

Test: `tests/test_convergence_2d.py`. Amendment 3 and CLAUDE.md: tightening the
tolerances 10x must change the payload and the margins by less than 0.1 %.
`SearchContext.tightened(checks.convergence)` divides every tolerance of the shared
budget by `tighten_factor` (10): search rtol 1e-8 -> 1e-9 and final 1e-10 -> 1e-11,
every atol (search and final), the LTG acceptance (1 m -> 0.1 m, 1e-3 -> 1e-4 m/s),
the delta xtol (1e-10 -> 1e-11 rad), the payload xtols (0.5 -> 0.05 kg, 0.05 -> 0.005
kg) and gamma_xatol (0.01 -> 0.001 deg); it multiplies the max_step caps by
`max_step_factor` (0.5: ramp, lag and push step counts doubled; the planar flight
phases have no other cap, "gamma* inner solve", Noise floor); the LTG
finite-difference steps, the brackets, the penalties and the false-root guard stay.
Values must agree within `rel_tol` (1e-3), with the absolute floors `loss_floor_mps`
(1e-3 m/s) for a loss term and `margin_floor_kg` (0.5 kg, or its dv equivalent c2 x
0.5 kg / m_c for dv_margin) for a margin; gamma* only to `gamma_resolution_deg` (0.1
deg). Every reported figure comes from the final-tolerance runs. The halved max_step
caps change nothing on the pad: its 2 s startup ramp runs in the closed-form hold (lit
at -2 s) and MVac starts at a step, so no ramp, lag or push step count is used (the
step-23 review measured m_res bit-identical; on silo_cold the halving alone moves m_res
by 1.6e-5 kg, on silo_cold_lag by 2.7e-6 kg). The fixed-gamma tests (gamma* = 20
deg) fly the pad and silo_cold (the push cap on the track and the ramp cap of its 2 s
ramp lit 0.5 s after release) in the fast tier and silo_cold_lag (the push cap and the
lag cap of its first-order startup, which caps the whole stage-1 burn) in the slow
tier; they apply amendment 3's per-term rule to every loss term one by one. The slow
re-optimised test (build step 25) repeats the whole search of the same three runs.
Both assert that the recorded run pushes on the track exactly on the silo runs, and
that the recorded traces fly a finite max_step in exactly the expected phase kinds
(the pad none; silo_cold ASSIST and KICK, the push and ramp caps; silo_cold_lag
ASSIST, KICK and GRAVITY_TURN, the push and lag caps), each tightened cap half the
shipped one (measured: ASSIST 0.052146 -> 0.026073 s, the ramp KICK 0.2 -> 0.1 s,
the lag KICK and GRAVITY_TURN 0.25 -> 0.125 s). These tests fly the shipped search
rtol of 1e-8 on the baseline side of each comparison (the budget itself is what
amendment 3 asks to converge); every other planar test flies the test budget (search
rtol 1e-9). The re-optimised test also compares the signed rung-2 figures at P0
(`SearchRecord.at_p0`) and compares gravity plus steering jointly, not one by one
(Finding below), at the steering term's own tolerance (1e-3 of |steering| or
loss_floor_mps, about 0.09 m/s), not at 1e-3 of the sum (about 1.5 m/s), so the
steering term is not checked more loosely than the per-term rule would check it.

**Measured** (build step 25; tightened minus shipped; the pad, silo_cold and
silo_cold_lag of silo_screening_2d, gate fork, P0 = 22.8 t).

At a fixed gamma* = 20 deg (final verification from the same start payload):

| quantity | pad | silo_cold | silo_cold_lag |
|---|---|---|---|
| P* | -8.0e-4 kg | -1.0e-3 kg | -1.0e-3 kg |
| m_res at P0 | -5.6e-4 kg | -1.6e-6 kg | +8.2e-7 kg |
| dv_margin at P0 | -6.4e-5 m/s | -1.8e-7 m/s | +8.9e-8 m/s |
| loss terms one by one (recorded run) | at most 4.6e-5 m/s (gravity; J_vac 3.5e-5, steering 2.0e-5, drag 1.5e-7, back-pressure 2.5e-8) | at most 4.0e-5 m/s (gravity; J_vac 2.1e-5, steering 1.1e-5, drag 2.4e-6) | at most 4.1e-5 m/s (gravity; J_vac 2.4e-5, steering 1.1e-5) |
| max-Q | 5.2e-9 relative (time 1.7e-9) | 4.2e-9 (time 1.3e-9) | 5.1e-9 (time 1.5e-9) |

Re-optimised (the whole search at each budget):

| quantity | pad | silo_cold | silo_cold_lag |
|---|---|---|---|
| P* | -9.2e-4 kg | -3.4e-3 kg | -2.8e-3 kg |
| m_res at P0 (at the shifted gamma*_ref) | +0.021 kg | +0.25 kg | +0.21 kg |
| dv_margin at P0 | +2.4e-3 m/s | +0.027 m/s | +0.023 m/s |
| gamma*_ref | -8.1e-4 deg | -6.3e-3 deg | -5.2e-3 deg |
| gravity plus steering (asserted) | -6.2e-4 m/s | -4.3e-3 m/s | -3.6e-3 m/s |
| gravity, steering (not asserted, Finding) | -0.012, +0.011 m/s (steering 1.3e-4 relative) | -0.095, +0.091 m/s (steering 1.01e-3 relative) | -0.080, +0.076 m/s (steering 8.4e-4 relative) |
| J_vac, drag, back-pressure | -2.9e-4, +2.9e-4, +7.6e-5 m/s | -2.1e-3, +1.7e-3, +4.5e-4 m/s | -1.8e-3, +1.4e-3, +3.8e-4 m/s |
| max-Q | 6.8e-6 relative (time 8.6e-7) | 4.3e-5 (time 5.6e-6) | 3.6e-5 (time 4.7e-6) |

Wall time of the whole search, shipped / tightened: pad 9.2 / 15.0 s, silo_cold 12.6 /
19.2 s, silo_cold_lag 24.5 / 52.5 s; of the fixed-gamma pair, pad 1.6 / 1.5 s,
silo_cold 1.6 / 2.1 s, silo_cold_lag 3.3 / 5.8 s. At a fixed gamma* the integration is
converged far inside every floor on all three runs, the capped silo phases included:
every loss term within 4.6e-5 m/s, P* within 1.0e-3 kg, m_res at P0 within 6e-4 kg.
After a re-optimisation P* moves by at most 3.4e-3 kg (7e-3 of the payload xtol).
CLAUDE.md's rule (payload and margins within 0.1 %) holds on all three runs. Sign:
the tightened search gives more m_res at P0 than the shipped one on every run, by
0.25 kg on silo_cold, 0.21 kg on silo_cold_lag and 0.021 kg on the pad, so the
shipped budget under-states the silo runs' margin at P0 by about 0.2 kg more than the
pad's: a bias against the assist, below the 0.4 kg interpretation threshold of the
Finding. Headroom of the re-optimised m_res at P0 assertion: its tolerance is
max(1e-3 |m_res at P0|, 0.5 kg) and the relative term binds on all three runs; the
shipped-against-tightened offsets use at most 0.05 of it, and over 13 first_step and
gamma_xatol draws of the step-25 review at most 0.07. Of every re-optimised
assertion, the largest share used in those draws is gamma* (0.077 of 0.1 deg), then
the joint gravity plus steering at the steering tolerance (0.07).

**Finding (build step 25; a user decision): after a re-optimisation the margins at P0
and the gravity/steering split are limited by search-mode noise in gamma*_ref.** At a
fixed payload m_res, dv_margin and the split of the loss between gravity and steering
follow gamma*_ref, and at the shipped budget gamma*_ref on the pad and silo_cold is set
by search-mode integration noise (uncapped planar flight phases at search rtol 1e-8:
the refine resolves gamma* to about 0.01 to 0.07 deg, "Payload and gamma* search",
Noise floor and the budget), not by gamma_xatol (0.01 deg). The step-25 review
repeated the shipped search with only `IntegratorSettings.first_step_s` changed (0.8e-3
to 1.3e-3 s, five draws per run with the shipped 1e-3 s among them; same tolerances,
same budget, no physics change). Against the tightened search gamma*_ref then differs
by up to 7.2e-3 deg on the pad and 6.3e-3 deg on silo_cold; two shipped draws of
silo_cold differ from each other by 9.6e-3 deg, 0.14 m/s in steering (1.5e-3 relative)
and 0.38 kg in m_res at P0. Gravity (about 1,450 m/s on silo_cold) and steering (about
90 m/s) move in opposite directions by about 15.2 and 14.5 m/s per deg of gamma*_ref
(the pad: steering about 13.9 m/s per deg), so their sum moves only about 0.7 m/s per
deg. Amendment 3's per-term rule (1e-3 relative or 1e-3 m/s) for the steering term
after a re-optimisation therefore passes or fails with the draw: it failed in 3 of 5
draws on silo_cold (the shipped one included: +0.091 m/s, 1.01e-3 relative) and 1 of 5
on the pad (1.13e-3), while P*, gamma* (0.1 deg) and gravity plus steering jointly
passed in every draw. silo_cold_lag is the exception that confirms the cause: its lag
cap (tau / lag_steps_per_tau over the whole stage-1 burn) removes the first_step
sensitivity, and gamma*_ref sits 5.24e-3 deg from the tightened value in every draw
(steering 8.4e-4 relative, m_res at P0 0.21 kg). That remaining offset is systematic
and set by the LTG acceptance box (accept_r_m 1 m, accept_vr_mps 1e-3 m/s), not by
gamma_xatol. The step-25 review tightened one part of the budget at a time and
compared with the fully tightened search: the LTG acceptance alone (10x) brought
silo_cold_lag to 9.0e-4 deg and 0.036 kg in m_res at P0; gamma_xatol / 10 and / 100
left gamma*_ref bit-identical (the refine took 7, 15 and 21 evaluations to the same
point); the search rtol alone (with or without the atol) and the halved caps alone
left it at 5.24e-3 deg. On the pad and silo_cold the LTG acceptance alone does not
remove the first_step spread (gamma*_ref of the probe minus the tightened one: pad
+1.5e-3 to +8.0e-3 deg, silo_cold -3.2e-3 to +6.3e-3 deg; steering up to 1.25 of its
per-term tolerance), which confirms the noise attribution there. At a fixed gamma*
every term of all three runs converges to within 4.6e-5 m/s (first table), so the
per-term rule is asserted there, where it measures the integration; the re-optimised
test asserts gravity plus steering jointly, at the steering term's own tolerance (the
only reading the screening rule interprets, "Screening-beat rule (2-D)"), and does not
assert the split. No tolerance was loosened.
Consequences for interpretation: a variant difference in m_res at P0 below about 0.4 kg
(the spread between shipped draws; margin_floor_kg is 0.5 kg) and a gravity/steering
split finer than about 0.15 m/s per term are not resolved by the shipped budget and are
not interpreted. Tightening gamma_xatol would not change this on any of the three
runs: the remedy is a planar max_step cap or a tighter search rtol for the noise (the
pad, silo_cold), then a tighter LTG acceptance for the systematic offset that remains
once the noise is gone (silo_cold_lag), not gamma_xatol; it belongs to the pending
decision on the planar max_step cap and the search tolerances
("gamma* inner solve", Noise floor), which is the user's.

## Performance (measured)

Build step 25, against the budgets of plan section 9. Measured on the development
machine (Windows 11, Intel64 family 6 model 183, 32 logical CPUs; Python 3.12.11,
numpy 2.5.3, scipy 1.18.1), serial, one process, nothing else running. Timings move by
about 5 % between repeats; RHS counts (`PhaseResult.nfev`, `RunTrace.nfev_total`) are
deterministic. These are costs, not results: no payload is quoted here.

**Budgets**

| Item | Budget | Measured |
|---|---|---|
| Fast tier, `uv run pytest -q -m "not slow"` | < 60 s | 856 tests in 48.2 s (pytest), 50.0 s wall with start-up (exact golden tier); 43.2 to 53.3 s in other runs of this step and its fix rounds |
| Any fast test | < 5 s | the slowest are 3.2 to 3.9 s (the fixed-gamma pairs of `test_convergence_2d.py` for silo_cold and the pad, the in-process 1-D golden run); the silo_cold_lag fixed-gamma pair (9.6 s) is slow-marked |
| Slow tier, `uv run pytest -q -m slow` | < 10 min | 16 tests in 212.8 s (pytest), 3 min 35 s wall; the re-optimised convergence of silo_cold_lag is the longest test (64 to 72 s), and the whole suite runs in 227.7 to 259.6 s (3 min 49 s to 4 min 21 s wall, 872 passed) |
| One searched run | < 30 s | the pad of silo_screening_2d 9.3 s in `sim.run_resolved` (search 9.2 s, recorded-run assembly `simulate_planar` 0.16 s); plus 1.6 s to import `launchsim.sim` and 0.1 s to load the experiment; writing its files and plots 1.2 s. The worst shipped run is silo_cold_lag (and the tau = 1 s point of the lag sweep, the same run): 23.9 s here, 19.2 s on the step-25 reviewer's run of the same code, 64 to 80 % of the budget and the smallest margin of any budget, because its lag cap holds over the whole stage-1 burn (below) |
| Any shipped experiment, serial | < 30 min | at most 7.3 min per command (dry estimate below); the `--jobs` trigger (plan decision 7) does not fire |

**Where one searched run spends its RHS calls** (the pad of silo_screening_2d, shipped
budget, 773,164 RHS calls over 1,780 integrated phases, bit-identical to build step 23;
about 12 us per RHS call including the solver, against 4.6 us for `rhs_planar` alone)

| Mode | Evaluations | Stage-1 flights / stage-2 shots | Phases | RHS calls | Time |
|---|---|---|---|---|---|
| grid (15 points at P0, search rtol 1e-8, atol x 10) | 12 flown, 3 infeasible by the direct-root rule | 130 / 120 | 830 | 320,171 | 3.8 s |
| search (P1, the refine, P2) | 18 | 187 / 114 | 800 | 353,231 | 4.2 s |
| final (verification and rung 2 at P0, rtol 1e-10) | 5 | 29 / 26 | 144 | 95,805 | 1.2 s |
| recorded run (dense output) | 1 | 1 / 1 | 6 | 3,957 | with the final |

| Phase kind | Phases | RHS calls | Per phase | Share |
|---|---|---|---|---|
| GRAVITY_TURN | 376 | 619,531 | 1,648 | 80 % |
| LTG_BURN | 636 | 94,383 | 148 | 12 % |
| KICK | 377 | 29,579 | 78 | 4 % |
| COAST_STAGING | 373 | 28,144 | 75 | 4 % |
| VERTICAL_RISE | 18 | 1,527 | 85 | 0.2 % |

The stage-1 flights of the gamma* inner solve dominate (8.7 per grid evaluation,
counting all 15 grid points; 10.8 per flown grid point, as "Payload and gamma*
search" counts them; 10.4
per search evaluation, 5.8 per final evaluation, against the plan's estimate of about
6), and within them the gravity turn: every flight integrates the whole turn to MECO.
The LTG shots are cheap (148 RHS calls each).

**Per-run cost** (`sim.run_resolved`, wall time, shipped budget)

| Run | Wall | RHS calls | Phases |
|---|---|---|---|
| pad | 9.3 s | 773,164 | 1,780 |
| pad_instant | 9.8 s | 821,727 | 1,890 |
| silo_instant | 12.7 s | 1,032,691 | 2,086 |
| silo_cold | 12.7 s | 1,019,035 | 2,452 |
| silo_cold_lag | 23.9 s | 1,941,817 | 1,423 |
| silo_hot_ramp_on_track | 12.5 s | 960,385 | 2,032 |
| silo_hot_full | 10.8 s | 851,958 | 2,007 |
| silo_hot_full_impinged | 11.2 s | 851,958 | 2,007 |
| silo_sled_22t | 12.9 s | 1,019,035 | 2,452 |
| silo_failed (no search) | 0.06 s | 1,527 | 3 |
| sweep_1 corners (0.5 g x 50 m, 0.5 g x 300 m, 5 g x 50 m, 5 g x 300 m) | 10.9 to 12.7 s | 0.87 to 1.01 M | |
| sweep_2 corners (t_ign 0 / t_ramp 1 s, t_ign 1 s / t_ramp 3 s) | 12.9, 13.0 s | 1.04, 1.03 M | |
| sweep_3, lag tau 2 s and 3 s | 15.0, 12.5 s | 1.18, 0.95 M | |
| two sensitivity cases (silo_cold stage-1 dry +10 %, silo_hot_full dry -10 %) | 14.4, 10.8 s | 1.16, 0.88 M | |
| calibration_f9_2d pad and its 7 cases | 9.7 to 12.3 s (aref_fairing the slowest) | 0.77 to 1.01 M | |
| `sim.matched_run` with neighbours (3 final-mode evaluations) | 0.83 s | | |
| writing one run with plots (`write_single`) | 1.2 s (0.27 s without plots) | | |

A carriage mass or exhaust impingement changes only the drive, not the vehicle's
flight, so silo_sled_22t and silo_hot_full_impinged fly exactly the RHS calls of
silo_cold and silo_hot_full. silo_cold_lag costs twice silo_cold because the lag
startup's step cap (tau / lag_steps_per_tau = 0.25 s, `prelude.max_step_cap`) applies
to the whole stage-1 burn, not only to the first few tau: its gravity turn takes 7,029
RHS calls per phase against 1,648 on the pad. The cap is shared with the 1-D planner,
so changing it would change the 1-D golden; a planar-only cap limited to the first few
tau is an integrator setting (Plan mode) and is left open, since every budget is met
without it.

**Dry estimate of the shipped experiments** (serial). `results_io.run_experiment` and
`run_sweep` were not run; their call sequences (planar branch: baseline and variants,
`run_sensitivity` with its trajectory-key memo, cases, `planar_comparisons`,
`planar_bounds`, the sweep loop with paired baselines, and the runs written with plots)
were replayed without flying, counting the searched runs, the reused trajectories, the
final-mode matched evaluations and the written runs, and multiplied by the measured
costs above. A run not measured is costed as the run it perturbs (a sweep point as its
`of`, a sensitivity case as its `of`, a perturbed baseline as the pad; 10 of 24 sweep
points, 2 of 24 sensitivity cases and all 8 calibration runs were measured, and the
measured runs of one family spread by about +/-15 %).

| Command | Searched runs | Reused | Matched evaluations | Written with plots | Estimate |
|---|---|---|---|---|---|
| `run experiments/calibration_f9_2d.yaml` | 16 (pad, 7 cases, 8 sensitivity cases) | 0 | 0 | 8 | 2.8 min |
| `run experiments/silo_screening_2d.yaml` | 35 (+1 without search: silo_failed) | 20 | 81 | 12 | 7.3 min |
| `sweep experiments/silo_screening_2d.yaml` | 25 | 0 | 72 | 25 | 6.3 min |
| `run experiments/silo_bridge_2d_readme.yaml` | 4 | 0 | 9 | 4 | 0.9 min |
| `sweep experiments/guidance_trigger_2d.yaml` | 9 (4 points, 4 paired baselines) | 0 | 12 | 9 | 1.8 min |

silo_screening_2d as a whole (run and sweep) is about 14 min serial, against amendment
17's 16 min and the 30 min budget. The 20 reused trajectories (energy-only
`assist.drive_efficiency` and yardstick `vehicle.screening` cases, and the perturbed
pad baselines shared by the two runs of the sensitivity block) save about 4 min.
Searched runs are about 90 % of the total. The bridge and trigger experiments use the
gate-fork costs of the same run names (the README-loads fork costs about the same: as
a calibration case it took 9.9 s against 9.7 s for the gate pad of the same
experiment).

**First-step carry-over (plan section 9, speedup 9): measured, not adopted.** Amendment
8 made it an optional Plan-mode integrator change, to be implemented only if measured
beneficial. A probe started every planar phase with first_step equal to the previous
phase's last full step instead of 1e-3 s:

| Run | Carried into | RHS calls | Wall |
|---|---|---|---|
| pad | no phase (shipped) | 773,164 | 9.4 s |
| pad | the C1 boundaries only (KICK to GRAVITY_TURN, splits inside one mode) | 756,304 (-2.2 %) | 9.4 s |
| pad | every phase (an upper bound) | 761,056 (-1.6 %) | 9.7 s |
| silo_cold_lag | every phase (an upper bound) | 1,864,291 (-4.0 %) | 23.6 s (-1.4 %) |

DOP853 grows a 1e-3 s first step to the phase's working step within a few steps
(scipy allows at most 10x per step), so
the start-up is a small share of a phase (the gravity turn takes 1,648 RHS calls); the
saving is a few percent of RHS calls and none in wall time, and the carried step
changes the search path (the pad flew 1,852 instead of 1,780 phases). It is not
implemented: the engine's first step stays `first_step_s` = 1e-3 s (or half the span),
the Integrator and Event-rules sections are unchanged, and the 1-D golden is untouched.

**What remains open** (none needed for a budget): the planar-only lag cap above; the
stage-1 flight count of the inner solve (8.7 to 10.4 flights per evaluation against
about 6 planned, which the pending max_step-cap and gamma* acceptance decision may
change, "gamma* inner solve", Noise floor); `--jobs` stays deferred (plan decision 7).
The probe scripts are not kept (they were step-25 scratch, not part of the package or
the tests); the method, to redo them: time `sim.run_resolved` with
`time.perf_counter`; wrap `SearchContext.evaluate` to tag the current mode (grid,
search, final, recorded) and the planar `integrate_phase` to sum `PhaseResult.nfev` and
count phases by mode and `PhaseSpec.kind`; for the first-step probe start each phase's
integration from the previous phase's last step; for the convergence deltas run
`run_search` (or `final_verify` at a fixed gamma*) on `SearchContext.from_run` and on
its `tightened(checks.convergence)`, and for the noise draws replace
`settings.first_step_s` with `dataclasses.replace`. Probes print differences only, no
absolute payload.

## Screening-beat rule (2-D)

Modules: `compare.py` (`compare_planar`, `matched_attribution`, `attribution_terms`,
`MatchedRun`, `ATTRIBUTION_TERMS`, `ATTRIBUTION_KEYS`, `gamma_sensitivity_step_rad`,
`Anchor`, `anchor_from`, `reference_payload_kg`, `attributed_comparison`,
`time_to_speed_s`, `time_shift_estimate_mps`), `sim.py` (`matched_run`, the per-run
checks of `simulate_planar`), `results_io.py` (`planar_comparisons`, `planar_bounds`).
Tests: `tests/test_closure.py::test_matched_payload_attribution`,
`::test_gamma_sensitivity_bookkeeping`, `tests/test_planar_pipeline.py`.

CLAUDE.md: an assisted run that beats the README's ideal screening estimate for its
release speed must be explained by its loss breakdown, else it is treated as a bug. The
1-D bound `unexplained_gain_mps <= 0` does not carry over (the 2-D gravity mechanism is a
time shift, "Time-shift mechanism"), and the plan's earlier linear 5 %/15 % check was
rejected as tautological. The 2-D rule has four parts; a failure of any gives status
`bug_suspect` and blocks findings until it is investigated (the summary's Checks
section says so).

**(a) Per-run checks** (`simulate_planar`): the rocket-equation closure residual below
`checks.closure_tol_mps` (1e-5 m/s, "Rocket-equation closure (planar)"), the loss
identity residual below `checks.identity_tol_mps` (1e-5 m/s) and, for an inserted run,
the osculating e below `checks.insertion_e_max` (1e-6). A failure sets the Result's
status to `bug_suspect` (the trajectory's own status stays in `trace_status`), writes
`run_checks` = bug_suspect with the reasons in `run_checks_failed`, and a
`bug_suspect: ...` flag.

**(b) Matched-payload attribution** (amendment 16). The matched payload P_ref is the
baseline's P* (a payload search), or the vehicle payload P0 (fixed guidance, a residual
search). Each run is taken at rung 2 at P_ref with its own sweep-optimized gamma*
(`sim.matched_run`, executed in `results_io.planar_comparisons` and passed to the pure
`compare_planar`): the baseline reuses its final evaluation at P* (no extra run), a
variant is evaluated once more in final mode at (P_ref, its gamma*_ref), delta and the
LTG pair re-solved and warm-started from its own final evaluation, and a fixed-guidance
run reuses its recorded run at P0. The stage-2 burn of these evaluations runs on virtual
propellant, so a variant above or below its capacity still has a cutoff state. With d =
variant - baseline and the same D_id(P_ref) on both sides, the closure and the loss
identity give, exactly up to the two runs' closure and identity residuals,

    d dv_margin = dV_0 - dV_f - dJ_grav - dJ_drag - dJ_steer - dJ_bp - d pre - d fair

(`ATTRIBUTION_TERMS`: release speed, final speed, gravity, drag, steering,
back-pressure, pre-flight, fairing; each a contribution in the variant's favour, m/s).
dV_f is carried explicitly: V_f equals the target's V_rel,f only to within the LTG
acceptance ("Rocket-equation closure (planar)"), so the plan's "V_f equal, exactly" is
replaced. `attr_residual_mps` = d dv_margin - sum of the terms; the dP* split in kg
allocates dP* in proportion to the terms (dP* x term / sum), so the split adds up to dP*
exactly. `attr_beyond_release_mps` is the sum without the release-speed term.

**Only gravity + steering together is physics.** The total d dv_margin is (nearly)
stationary in the variant's gamma*, but its gravity and steering terms trade against
each other to first order as gamma* moves: a steeper MECO costs more gravity loss and
less steering loss. The matched run is taken at gamma*_ref, which is optimal at the
variant's own first payload estimate P1, not at P_ref, and which moves with the search
window. So the per-term split, the kg split and M2 to M4 depend on where the search
landed, not only on the physics. The attribution therefore also carries the joint term
`attr_gravity_steering_mps` (and `_kg`), and the summary prints it and the caveat with
every attribution: only that sum is interpreted, never the split between gravity and
steering. The gamma*-sensitivity diagnostic: a searched variant's matched run is also
evaluated at gamma*_ref -/+ h (`compare.gamma_sensitivity_step_rad` of the pre-registered `checks.gamma_sensitivity_step_deg`, h = 0.5 deg;
`MatchedRun.neighbours`, two more final-mode evaluations per variant; none for the
baseline or for fixed guidance, whose fixed LTG pair would miss the target), giving
`attr_<term>_dgamma_mps_per_rad` (central difference) and the contributions at -h and
+h (`attr_neighbours`). The M2, M3 and M4 records carry the ratio (or share) at the
three points (`value_range`), the verdicts at -h and +h (`neighbour_status`) and
`gamma_robust` (all three verdicts agree). This is a diagnostic: the verdict at
gamma*_ref stays the pre-registered one; the summary marks a non-robust verdict and the
Checks section lists them. h is a module constant pending a `checks` field (the
config's owner). Measured (methods check, not a finding; searched pad and silo_cold on
the fast test's small grid, 20 to 24 deg, refine half-width 1 deg and 3 iterations, P0
26 t, P_ref = 26,050.39 kg, gamma*_ref = 21.764 deg): gravity -867 m/s per rad (-15.1
m/s per deg), steering +718 m/s per rad (+12.5 m/s per deg), the sum -149 m/s per rad
(-2.6 m/s per deg). M2's ratio is 0.363 at gamma*_ref and ranges 0.292 to 0.434 over
+/- 0.5 deg: it fails at +0.5 deg (not robust); M3 (0.673 to 0.677) and M4 (share 0.161
to 0.311) are robust. With the wider grid of the M2 table below (16 to 28 deg, refine
half-width 2 deg, 6 iterations) the same variant's ratio is 0.448: the search window
alone moves the verdict's margin.

**Screening yardstick.** `vehicle.payload_gain_kg` of the run's release speed, on the
vehicle at P0 (`ideal_screening_payload_at_release_speed_kg`) and on the vehicle at the
baseline's P* (`..._at_pbase_kg`). The verdict uses the stricter, smaller of the two
(`screening_yardstick_kg`, basis `screening_yardstick_basis`: `P0` or `P*_base`), so a
run that beats either yardstick counts as a beat: with P*_base above P0 (the gate fork)
the P0 one is smaller (at 76.707 m/s: 675.35 kg at 22.8 t against 765.33 kg at 26.05 t).
`payload_beyond_screening_kg` = dP* - screening_yardstick_kg, `beats_screening` when
positive. The summary's screening line prints dP*, both yardsticks and the one used,
the verdict, the attribution (m/s and kg, the joint term and the caveat) and every
check.

**(c) Mechanism checks** (thresholds in `checks:`):

- closure: the variant's rocket-equation closure and the baseline's
  (`closure_residual_mps` below `closure_tol_mps`); n/a when the variant burned no
  stage 2 (a failed ignition), with the baseline's residual recorded (the baseline's
  closure is its own per-run check, part (a)).
- attribution: the attribution must close: `attr_residual_mps` and both matched runs'
  closure residuals below `closure_tol_mps`, both matched runs' loss-identity residuals
  below `identity_tol_mps`. Without an attribution it fails when one is required
  (`attribution_required`: every assist-versus-baseline pair of one vehicle, namely each
  named variant and sweep point, each sensitivity case against the baseline of its own
  vehicle and each bound against its paired baseline) and the run beats the screening
  yardstick, an unexplained beat that CLAUDE.md treats as a bug; otherwise n/a with the
  reason (no rung-2 run at P_ref, or not attributed by design: a comparison across two
  vehicles).
- M2 (gravity): a variant that releases faster than the baseline (the time-shift
  mechanism exists; otherwise n/a) must have its matched d J_grav within
  `grav_ratio_bounds` [0.33, 3] of the estimate over the baseline's recorded trajectory
  at P_ref, dJ_grav_est = [J_grav(t_MECO) - J_grav(t_MECO - t_v0)] - [J_grav(t_fs +
  t_v0) - J_grav(t_fs)], t_v0 the baseline's time from its flight start to |v_rel| =
  the variant's release speed (brentq on the dense output; the quadrature read off the
  dense output). A positive ratio in the band passes (same sign). The record also
  carries, as a diagnostic that does not change the verdict, the stage-1 part of the
  matched d J_grav (flight start to MECO, `d_stage1_mps`, from
  `attr_gravity_stage1_mps`) and its ratio to the same estimate (`ratio_stage1`): the
  estimate models stage 1 only. With the attribution's neighbours it also carries the
  ratio's range over gamma* +/- h (the baseline and its estimate fixed) and
  `gamma_robust`.
- M3 (back-pressure): the same with J_bp and `bp_ratio_bounds`, applied when |d J_bp| >
  `min_term_mps` (1 m/s) and the variant releases faster.
- M4 (drag and steering): -(d J_drag + d J_steer) at most `max_drag_steer_share` (0.5)
  of `attr_beyond_release_mps`; n/a when that gain is below `min_term_mps` (1 m/s:
  amendment 3's absolute floor, since a share of a near-zero gain is noise). M3 and M4
  carry the same gamma* range items as M2.

**(d) Anchor bound M5**: when the experiment runs `silo_instant` and `pad_instant`
(both lit at release with a step: the release speed alone), a named variant released at
silo_instant's speed (within 1e-6 m/s; not the anchor pair itself) must satisfy dP* <=
dP*(silo_instant vs pad_instant) + the ideal-screening payload equivalent of the
baseline pad's pre-flight term c1 ln(m0/m_fs) (on the vehicle at P*_base) +
`anchor_margin_kg` (1.5 kg); n/a otherwise.

`screening_status` is `bug_suspect` when any applicable check fails (listed in
`screening_failed`); `not_checked` when there is no attribution and nothing failed (a
comparison across two vehicles, by design: `attribution_required` False, namely a
vehicle-parameter sensitivity case or a bound against the unchanged baseline; a
variant without a rung-2 run at P_ref that does not beat the yardstick, such as a
failed ignition); else `ok`. A not_checked dP* is not explained by a loss breakdown, so
no finding about a beat may rest on it; the summary's Checks section lists the
not_checked comparisons and, separately, any not_checked comparison that beats its
yardstick ("Unexplained beats"). Sensitivity cases and bounds get the rule too
(`compare.attributed_comparison`): a run-parameter case against the unchanged
baseline, a vehicle-parameter case against the same-perturbation baseline and a bound
against its paired baseline are attributed at that baseline's P* (one more final-mode
evaluation of the case, plus its two gamma* neighbours; memoised by trajectory key
within one sensitivity call; a case with the baseline's own trajectory key, such as a
case of the baseline itself, is not re-flown: dP* = 0). The sensitivity and bounds
tables print, for that comparison, whether it beats the yardstick and its status, and
the Checks section gives each such comparison a line (dP*, the yardstick used, beats,
failed checks, gamma*-sensitive checks, status) and counts its bug_suspect among the
blocked findings. Sweep points are compared with their own baseline (the experiment's,
or the paired baseline of a paired sweep) with the attribution and M2-M4 (no anchor
pair in a sweep: M5 n/a); the top-level sweep summary has its own Checks section
(`summary.sweep_checks_section`: per-run checks of the baseline, every point and every
paired baseline, each point's screening status, failed and gamma*-sensitive checks,
and the blocked-findings line).

**M2 as pre-registered: measured behaviour (the user's decision before the
pre-registration commit).** It is implemented as pre-registered and reported, not
redefined here. Methods check, not a finding: silo_screening_2d's runs on the gate fork
with a small search (gamma* grid 16 to 28 deg, refine half-width 2 deg and 6
iterations, vehicle payload P0 26 t, search rtol 1e-9, the shipped final rtol 1e-10),
compared through `planar_comparisons` (P_ref = the pad's P* = 26,054.40 kg; t_v0 =
18.206 s for 76.71 m/s). The matched d J_grav (variant - baseline; negative = less
gravity loss) is split into flight start to MECO (`d_stage1_mps`) and MECO to cutoff:

| variant | V0 [m/s] | d J_grav = to MECO + after MECO [m/s] | estimate [m/s] | M2 ratio | stage-1 ratio | M2 |
|---|---|---|---|---|---|---|
| silo_instant | 76.71 | -76.58 = -37.44 - 39.14 | -105.05 | 0.729 | 0.356 | pass |
| silo_cold | 76.71 | -47.09 = -14.37 - 32.73 | -105.05 | 0.448 | 0.137 | pass |
| silo_hot_full | 76.71 | -95.75 = -63.80 - 31.95 | -105.05 | 0.911 | 0.607 | pass |
| silo_cold at 0.5 g, 50 m | 22.14 | +12.76 = +18.29 - 5.52 | -34.98 | -0.365 | -0.523 | fail |
| silo_cold at 1 g, 50 m | 31.32 | +2.27 = +12.67 - 10.40 | -48.22 | -0.047 | -0.263 | fail |
| silo_cold at 5 g, 300 m | 171.52 | -138.20 = -66.86 - 71.34 | -188.73 | 0.732 | 0.354 | pass |

Every attribution closes (residual below 5e-7 m/s; matched closures below 7e-7 m/s,
identities 6e-9 m/s) and M3, M4 and M5 pass wherever they apply, so no bug is
indicated anywhere in the table. What it shows:

- The estimator models stage 1 only, but a third to two thirds of the matched d J_grav
  accrues after MECO (the staging coast and the stage-2 burn), where each run flies its
  own gamma* and MECO state. M2's whole-flight ratio for the 77 m/s variants passes
  partly on that post-MECO term: on stage 1 alone silo_cold's ratio is 0.137 (it would
  fail), silo_instant's 0.356 and silo_hot_full's 0.607. The earlier equal-gamma*
  stage-1 measurement ("Time-shift mechanism": about 0.25 and about 0) did not predict
  M2's verdicts here.
- The low-speed cold starts of the shipped sweep fail M2 with no bug: at least the 0.5 g
  and 1 g points at 50 m (the other sweep points were not probed). Their d J_grav is
  positive: the cold start flies 0.5 s unpowered and a 2 s ramp in the air near
  vertical, a gravity loss the pad does not pay because it spends its ramp clamped (the
  pad's pre-flight term, +14.41 m/s in the variant's favour in every row, is the other
  side of that trade). The time-shift estimate does not model it, and it dominates when
  t_v0 is short (5.9 s at 22 m/s).
- Fixed-guidance comparisons (figure_of_merit none, as in the fast pipeline test: every
  run flies the pad's LTG pair) end off target (silo_cold's |dV_f| is 40 m/s), so their M2
  verdicts are not evidence either way (all three 77 m/s silo variants fail there:
  ratios -0.24, -0.35, 0.10).

- The whole-flight d J_grav depends on where the variant's gamma*_ref landed (the
  gamma*-sensitivity diagnostic above): silo_cold's ratio is 0.448 with this grid and
  0.363 with the fast test's small window, and within +/- 0.5 deg of the latter it
  spans 0.292 to 0.434 (a fail at +0.5 deg). At the pad's own gamma* (+0.77 deg) it
  would be about 0.25 (reviewer's probe). The verdict for silo_cold is therefore not
  robust to gamma*, while the joint gravity + steering term moves about 2.6 m/s per deg
  against about 15 m/s per deg for gravity alone.

Options for the user: keep M2 as pre-registered (false bug_suspect at the low-speed cold
sweep points, a pass for silo_cold that rests on post-MECO differences, and a verdict
that is not robust to gamma*); compare the estimate with the stage-1 part only
(silo_cold and the low-speed cold points would fail); pre-register the check on the
joint J_grav + J_steer term, which is nearly stationary in gamma*; evaluate the matched
variant at its P_ref-optimal gamma* (a refine at P_ref, more runs); mark a verdict
indeterminate when its gamma* range spans a bound (the `gamma_robust` field already
records it); build a mass-consistent estimator from the variant's own trajectory that
also books the cold start's unpowered and ramp time; or drop M2 and rely on the closing
attribution (the attribution check), M3, M4 and M5.

## Reporting definitions (planar)

Modules: `sim.py` (dispatch, `run_planar`, `simulate_planar`, `PLANAR_ASSUMPTIONS`),
`metrics_planar.py` (time series, events, metrics), `compare.py`, `summary.py`,
`results_io.py`, `plots.py`, `cli.py`. Test: `tests/test_planar_pipeline.py`.

**Dispatch.** `sim.run` sends a `planar_2d` RunConfig to `run_planar`; a `vertical_1d`
run takes the Phase 1 path byte for byte (the 1-D golden). A searched figure of merit
(payload, residual) runs `search.run_search` on the run's `SearchContext` (a fresh
WarmStore per run) and assembles the recorded run at P_final (`simulate_planar`, which
first calls `RunTrace.require_dense`); a failed search gives a Result with status
`search_failed`, empty frames, None figures and a flag naming the failure (kind `edge`
adds "widen the shared gamma* grid for every run"). Without a search: a failed stage-1
ignition (the search skipped, amendment 4) flies no guidance (search status `skipped
(<reason>)`); figure_of_merit `none` flies the shared fixed guidance (delta solved for
the fixed gamma* at the final tolerance, the fixed LTG pair; `none (fixed guidance)`),
whose residual propellant and margin are the recorded run's own at its cutoff (m_empty
= m_d2 + P, plus the fairing still carried), and which may end off target. A typed
guidance failure of a fixed-guidance run (`search.INFEASIBLE`: GuidanceFailure, such as
no_kick when v_k is never reached, or PreludeFailure), which a search would turn into a
penalty, gives status `guidance_failed` (`sim.guidance_failed_result`: empty frames, the
fixed gamma* and LTG pair, `guidance_failure_kind` and `_message`, a flag) instead of
aborting the experiment.

**Figures of merit** (`search_metrics`): `payload_kg` = P* (P_final); the signed
`residual_propellant_kg` and `dv_margin_mps` at P0 (`SearchRecord.at_p0`, final
tolerance) labelled by `residual_propellant_basis` ("at gamma*_ref (P*-optimal
guidance)" for a payload search, "at gamma* refined at P0" for a residual search: never
compared across figures of merit), `residual_propellant_virtual` when negative (a
virtual, massless shortfall), `payload_excess_kg` = P0 - P* beside it,
`dv_shortfall_mps` of a no_orbit search; gamma*_ref, the best grid point, delta and the
LTG pair of the final evaluation; the search diagnostics; `search_record`, the plain
copy of the whole record (`search.as_plain`).

**Time series** (`sample_trace_planar`, `PLANAR_TIMESERIES_COLUMNS`): every phase at
the multiples of `sample_dt_s` plus its ends; alt_m, downrange_m, |v_rel|, |v_in|,
gamma_rel_rad (unwrapped per run by `metrics_planar.unwrap_rad`, amendment 14: a
vertical fall-back with rotation has u < 0 and would wrap from +pi to -pi at the apex;
the unwrapped series runs on past pi, to 3 pi/2 in the fall. Without rotation u = 0
exactly, the raw angle steps from +pi/2 to -pi/2 at the apex, a step of exactly -pi
that numpy.unwrap leaves alone; `unwrap_rad` takes a step within ATOL_RAD, the
integrator's angular tolerance, of -pi as +pi (a rounding-level u at the apex would
otherwise leave a step of -pi + epsilon), so the fall reads 3 pi/2 with rotation on or
off, with a single step of pi at the rotation-off apex. The apex itself still reads
differently: pi/2 without rotation (|v_rel| is about 1e-14 m/s there, below
V_REL_EPS_MPS, so the local-vertical fallback applies) and about pi with it (|v_rel| =
2 omega_p h, horizontal and westward: 0.0385 m/s at h = 300.6 m for silo_failed)),
pitch (unwrapped the same way: it follows v_rel in an unpowered phase) and psi [rad],
m, the delivered and vacuum thrust, drag, q,
Mach, q-alpha, the felt axial and lateral g, the six loss quadratures and the track
columns. Hold rows: the pad state, radial thrust, felt axial 1 g_ref (the clamp carries
the weight). Track rows: |sdot|, gamma = phi, the track's felt g and the vehicle's
track-normal load as the lateral g, q, Mach and q-alpha NaN (the vented shaft has no air
model). Events (`events_frame_planar`, `PLANAR_EVENT_COLUMNS`): the PlanarView columns
of every record, gamma_rel unwrapped over the events in time order.

**Metrics** (`planar_run_metrics`, SI, times after release): the release, flight-start
and hold items of the 1-D model; MECO (t, altitude, |v_rel|, gamma_rel, downrange); the
stage-2 end with its osculating elements (e, perigee and apogee altitude, the radius
miss and v_r); the fairing drop in one of the three record forms (`fairing_drop`: in
the stage-2 burn at the heating event, at stage-2 ignition, at staging; or kept), with
t and altitude; the end, the highest apex, the impact; the kick (`kick_regime`:
`at_first_lit_instant` when the run is already faster than v_k while rising as stage 1
lights, `after_vertical_rise`, or `none`; |v_rel| at the kick, its duration and its
steering loss); the loss budget and its identity residual; max-Q (`max_q`: q, time,
altitude, Mach, phase), peak q-alpha and peak felt axial and lateral g in flight, all by
the `scan_peak` scan (one vectorised dense-output evaluation per phase, then a bounded
Brent refine: independent of the sampling interval); the run-wide peak felt axial g
(hold, track and flight); a pad's zero assist items or the push's
(`planar_track_metrics`: the 1-D track items, with the exit speed |v_rel| at release;
the track-normal load for the vehicle and the carriage separately, both in the summary
table under the peak, as CLAUDE.md asks); for a failed ignition the highest apex and the
impact (`summary.PLANAR_FAILED_ROWS`: failed stage, apex altitude and time, impact time
and |v_rel|);
how stage 1 starts; the closure items (`closure_metrics`); `trace_status`, `run_checks`
and `nfev_total`. `PLANAR_REQUIRED_METRICS` (amendment 10: the 1-D REQUIRED_METRICS plus
payload_kg, residual_propellant_kg, dv_margin_mps, search_status,
peak_felt_axial_g_flight, peak_felt_lateral_g, peak_q_alpha, max_q_time_s, max_q_mach)
are rows of `summary.PLANAR_VARIANT_ROWS` and are all non-null for a searched run; a run
without a search has no P*.

**Comparison** (`compare_planar`): the numeric deltas, `payload_delta_kg` = dP*, the
screening yardsticks (both, and the stricter one used with its basis),
`beats_screening`, `max_q_above_baseline`,
`q_alpha_above_baseline` and `unconstrained_kick` (|v_rel| at the kick above
`checks.unconstrained_kick_mps`, 120 m/s, amendment 13: the model has no
angle-of-attack aerodynamics, so a fast kick costs nothing it would cost in flight);
`payload_delta_upper_bound` is True when any of the three is, and the dP* is then an
unthrottled, unconstrained upper bound (the summary's dP* row and screening line say so
and why); the attribution, the checks of the screening-beat rule and
`screening_status` (ok, not_checked, bug_suspect).

**Sensitivity** (`compare.run_sensitivity` on a planar experiment): every
trajectory-changing case is a full searched run, compared with the unchanged baseline
and, for a `vehicle.` parameter, with the baseline re-run under the same perturbation
(once per distinct perturbation). A case whose `trajectory_key` (the sha256 of its run
and vehicle dicts without the run name, the energy-only keys of its assist model,
`compare.ENERGY_ONLY_ASSIST_KEYS`: `drive_efficiency` for constant_accel only, since a
drive with an electrical power limit would fly differently with another efficiency,
and without `vehicle.screening`) equals a run already flown (the nominal runs, then
each case and perturbed baseline as it runs) reuses that trajectory and search
(`sim.rerun_resolved`):
the energy-only `assist.drive_efficiency` and the yardstick `vehicle.screening.*`
cases fly nothing, and only their track metrics (the electrical energy) and assumptions
are recomputed (`trajectory_reused`); the screening Isp enters only the comparison's
yardstick. The memo lives for one call, so no result depends on run order. The table
prints P* and dP* against both baselines, and whether the comparison against the
baseline of the case's own vehicle beats the yardstick with its screening status (that
comparison is attributed: "Screening-beat rule (2-D)"); C_D is a real case
(`vehicle.aero.cd_scale`), so there is no filler row.

**Bounds, cases, paired sweeps.** A bound (amendment 6) re-runs the baseline with its
overrides once (the pair) and each listed run, compared with the pair (attributed) and
with the unchanged baseline (two vehicles: not_checked); both are written
(`<of>__<bound>`, `<baseline>__<bound>`).
Calibration cases run independently, are written, and are never compared; a
calibration-labelled summary opens with the CALIBRATION banner. A paired sweep point is
compared with its paired baseline (`run_NNNN__<baseline>`, run once and written beside
it); the planar sweep index adds the paired baseline, P*, dP*, the screening yardstick,
gamma*, |v_rel| at the kick, q-alpha and max-Q with their deltas, the kick regime per
point (plan decision 5), `unconstrained_kick` and `payload_delta_upper_bound` per point
(the label plan section 13 asks for above about 120 m/s), the search and screening
statuses.

**Summary** (`planar_experiment_summary`): the CALIBRATION banner (label calibration),
the comparison basis (`compare.planar_comparison_basis` of the shared figure of merit:
sweep-optimized, or `PLANAR_FIXED_COMPARISON_BASIS` for figure_of_merit none) and the
guidance label (`summary.guidance_label`: `SWEEP_OPTIMIZED_LABEL` when any run
searched, else `FIXED_GUIDANCE_LABEL`; a fixed-guidance result is never labelled
sweep-optimized, and its runs carry `FIXED_GUIDANCE_ASSUMPTIONS`, not the search
lines), the search budget id, the per-variant table (degrees only in its cells), the
bounds, the cases, the sensitivity table, the flags, the assumptions and the checks.
The Checks section lists the per-run checks of every run (cases, sensitivity and bound
runs included), the screening line of every variant, one line per attributed
sensitivity or bound comparison, the comparisons that are bug_suspect (findings
blocked), those that are not_checked, the not_checked ones that beat their yardstick
(unexplained beats) and the gamma*-sensitive verdicts. The planar sweep summary
(`planar_sweep_summary`) has the same basis and label rule and a Checks section.
Plots (`write_planar_plots`): altitude against downrange, |v_rel| and |v_in|, gamma_rel
and pitch in degrees, q and Mach, mass and thrust, the felt g, the cumulative losses,
plus the track panels. The CLI reads a case's vehicle file through the experiment's
lookup, checks the names of cases, bound runs and paired baselines before anything is
written, and prints P*, gamma*_ref and max-Q per planar run.

**Measured** (fixed guidance, gamma* 20 deg, 22.8 t): a fixed-guidance run takes 1.5
s (pad) to 2.0 s (silo_cold), of which the cold delta solve is about 1.1 s;
`simulate_planar` 0.43 to 0.56 s at sample 0.05 s (10,560 rows: the sampling 0.30 to
0.37 s, the four peak scans 0.17 s); an energy-only sensitivity case flies nothing. The pad's recorded run reproduces build step 22's fixed-gamma*
figures (m_res, dv margin, max-Q, closure residual) to every printed digit; gamma_rel of
silo_failed's fall-back rises past pi after the apex.

## Thrust startup

Module: `vehicle.py` (`Startup`, `thrust_fraction`, `ThrustSchedule`,
`propellant_burned_kg`, `startup_deficit_s`); test: `tests/test_thrust_schedule.py`.
With dt = t - t_ign the thrust fraction f is

    step:  f = 1[dt >= 0]
    ramp:  f = clip(dt / t_ramp, 0, 1)
    lag:   f = 1 - exp(-dt / tau)           (dt >= 0, else 0)

T_vac(t) = T_full f(t - t_ign) and the mass flow is T_vac(t)/c, so a ramp burns
mdot t_ramp/2 before reaching full thrust and a lag burns mdot [dt - tau (1 - e^(-dt/tau))]
(`propellant_burned_kg`, used by the hold phase in closed form). A zero-duration ramp or
lag is a step. `fails: true` makes T_vac identically zero. Cutoff is instantaneous
(assumption). The kinks of the thrust curve, t_ign and t_ign + t_ramp
(`ThrustSchedule.kink_times()`), are phase boundaries so the integrator never steps
across a derivative discontinuity; the planner also caps `max_step` at t_ramp /
`ramp_steps` inside a ramp and tau / `lag_steps_per_tau` inside a lag.

## Integrator

Module: `phases/engine.py` (`IntegratorSettings`, `PhaseSpec`, `PhaseResult`,
`integrate_phase`, `atol_for`, `event_state`). One `scipy.integrate.solve_ivp` call per
phase:

- DOP853 (`IntegratorSettings.method`; RK45 is the only other method accepted, per
  CLAUDE.md), rtol 1e-10 by default and in tests (CLAUDE.md asks for <= 1e-9). Dense
  output is on by default (`IntegratorSettings.dense_output = True`) so callers
  resample at `sample_dt_s` (0.05 s) from it; the result carries the integrator's own
  steps plus the event point. A search evaluation (Phase 2) turns it off: the steps,
  the end state and the event roots are unchanged (the solver's stepping does not
  depend on it), `PhaseResult.dense` is None, and event states come from
  `PhaseResult.y_events` ("Event rules", rule 4). scipy then builds a step's
  interpolant only in steps where an event is active. For DOP853, whose interpolant
  needs three extra right-hand-side evaluations per step, that saves RHS calls
  (measured on the toy burn of `test_phases_package.py`: 283 instead of 322 with two
  events, and fewer still without events); for RK45, whose interpolant needs none, the
  count is unchanged (307 either way on the same burn). Dense output off is for search
  evaluations only: a recorded run and every reported metric come from a dense-output
  run, because the reporting path reads a missing dense output as "nothing to
  resample" (a pass-through or the closed-form HOLD) and would silently fall back to
  the solver's own steps or the phase-start state. So `VerticalPlanner` refuses
  settings with dense output off (every 1-D trace is a recorded run), an integrated
  phase run without it carries `PhaseResult.dense_off = True`, and
  `RunTrace.require_dense(purpose)` raises on a trace that has such a phase; the
  planar recorded path (Phase 2, `sim.simulate_planar`) must call it before sampling.
- Per-state absolute tolerances from the unit suffix of the state name (`atol_for`); a
  state with an unknown suffix is rejected so a new state cannot silently get a
  tolerance:

  | Suffix | atol | States |
  |---|---|---|
  | `_m` | `ATOL_M` = 1e-6 m | z, s (and r in Phase 2, where it is inert: see below) |
  | `_mps` | `ATOL_MPS` = 1e-9 m/s | velocities and the loss quadratures |
  | `_kg` | `ATOL_KG` = 1e-6 kg | mass |
  | `_J` | `ATOL_J` = 1e-3 J | the track energy quadratures |
  | `_rad` | `ATOL_RAD` = `ATOL_M` / R_E = 1.5678e-13 rad | angles (the planar downrange angle theta, Phase 2): the angle one length tolerance subtends at the surface |

  solve_ivp bounds each state's local error by atol + rtol |y|, so for the planar
  radius r ~ R_E the bound is set by rtol, not by `ATOL_M`: about 6.4e-4 m per step at
  rtol 1e-10 and 6.4e-2 m at the search setting (rtol 1e-8, atol x 10). A probe of an
  F9-class radial burn and coast under mu/r^2 integrated once in r and once in
  z = r - R_E measured, against an rtol-1e-13 reference, a burnout-altitude error of
  3.6e-6 m in r against 4.2e-7 m in z (rtol 1e-10; step-17 review probe). A planar altitude is therefore
  resolved to a few micrometres, not to `ATOL_M`, and the ground event's
  `zero_tol = ATOL_M` is below what r resolves. The planar-vs-1-D and closed-form
  altitude tests of build step 20 (`test_planar_reductions.py`) therefore compare
  altitudes at 1e-10 relative with a 1e-6 m floor, which the measured r-form errors
  satisfy through the relative term (the constant-g vertical burn through the planar
  RHS: -3.2e-6 to -4.5e-6 m at 161-209 km, 2e-11 relative; planar vs 1-D stage-1
  burn: 2.6e-9 m at 208 km, the two integrations taking nearly the same steps).
  Altitude is not carried as a datum-relative state.

  `IntegratorSettings.atol_scale` (default 1.0, must be finite and > 0) multiplies
  every entry for a phase (the Phase 2 search uses 10 with its looser rtol); at 1.0 the
  engine passes the `atol_for` vector itself, so the 1-D runs are bit-for-bit
  unchanged. These tolerances and the engine guards
  (`ZERO_SPAN_S`, `EVENT_ZERO_TOL`) are solver settings, not physics: they live as
  named, documented constants beside the solver in `phases/engine.py` (as `vehicle.py` keeps
  its brentq settings), while Earth and physical constants live only in
  `constants.py`. That is the reading of CLAUDE.md's "no magic numbers" rule
  throughout the package (`losses.py` keeps its scan and search settings the same way).
- `first_step = min(first_step_s, span/2)` with first_step_s = 1e-3 s: scipy raises
  when the first step exceeds the span, and 1e-4 s phases occur (staging coasts,
  the tail of a ramp).
- A phase whose span is <= 1e-12 s is not solved: the state passes through unchanged
  (`ended_by = "zero_span"`). Zero-length phases occur routinely (the kink at release,
  a zero staging coast).
- `max_step` is per phase and the planner sets it in `PhaseSpec.max_step`
  from the settings: t_ramp / ramp_steps (10) in a ramp, tau / lag_steps_per_tau (4)
  in a lag, t_push / push_steps (50) on the track, unbounded (`math.inf`, the default)
  elsewhere. The engine only consumes the value.
- Open-ended phases (`t_end = None`) are guarded by `t_max_s` (3600 s): reaching it
  without a terminal event raises `RuntimeError` naming the phase kind. An integrator
  failure raises too. A run that must stop cleanly (no liftoff, drive limit) does so
  through a terminal event and `Result.status`, never through the guard.
- `IntegratorSettings.from_config(IntegratorConfig)` mirrors the YAML
  `integrator:` block field for field. The method is the config's `integrator.method`
  (`DOP853`, the default, or `RK45`; any other value is a validation error; the field
  exists since build step 19, and `from_config` still falls back to `DEFAULT_METHOD`
  = DOP853 for a config object without it). `dense_output` and `atol_scale` have no
  YAML key: they are set in code by the search.
- Planar tolerance rule (a config rule, build step 19): on a `dynamics: planar_2d` run
  `integrator.rtol` must equal the shared `search.final_rtol`, so the recorded run and
  the final payload verification integrate at one tolerance and every reported number
  comes from it (amendment 3). A search evaluation integrates at `search.search_rtol`
  with `atol_scale = search.search_atol_scale`; `final_rtol` may not be looser than
  `search_rtol`, and `search_atol_scale` may not be below 1 (a search is never
  integrated more tightly than the final run). On planar_2d every integrator setting
  (method, rtol, first step, max_step caps, t_max and `sample_dt_s`) is the baseline's
  in every compared run: variants, sweeps, sensitivity cases and bounds may not address
  `integrator` at all, so no two compared runs integrate differently while claiming
  one budget, and no peak read from the sampled time series (the 1-D felt-g peaks are)
  moves between compared runs with a per-run sampling interval. Absolute sampled peaks
  still depend on `sample_dt_s`, so the planar peak metrics (q-alpha, felt axial and
  lateral g) are found by a scan independent of it, as max-Q is
  (`metrics_planar.scan_peak`, "Max-Q and loads (planar)"; the reporting is build step
  24). Two experiments may still differ in `sample_dt_s` (amendment 15). The 1-D
  model has neither rule ("Experiment schema (planar)").
- `PhaseResult.nfev` records solve_ivp's right-hand-side count for the phase (0 for a
  pass-through or the closed-form HOLD; the two Heun evaluations of the pre-solve rule
  are not counted), and `RunTrace.nfev_total` sums it over a run, for the Phase 2
  performance budget.

## Event rules

Events are `EventSpec(name, fn(t, y) -> float, terminal, direction, zero_tol)` with
scipy's sign-change convention: direction -1 fires on a positive-to-negative crossing,
+1 on the reverse, 0 on either. `zero_tol` is the band |fn| <= zero_tol that counts as
"on the event surface" in the rules below; the factories set it to the atol of the
state the event reads, because the integrator does not resolve a state below its atol
and the residue scipy leaves at a root is not an exact zero (see rule 2). Each phase
lists only the events that can end it. Factories:

| Event | Function | Direction | zero_tol | Ends |
|---|---|---|---|---|
| `propellant` | m - m_dry_stack | -1 | `ATOL_KG` 1e-6 kg | every burn |
| `apex` | v | -1 | `ATOL_MPS` 1e-9 m/s | a rising coast or burn (next phase runs sigma = -1) |
| `turnaround` | v | +1 | `ATOL_MPS` 1e-9 m/s | a falling burn (next phase runs sigma = +1) |
| `impact` | z - z_ground | -1 | `ATOL_M` 1e-6 m | a fall (status `impact`) |
| `liftoff` | T(t) - m(t) g_eff, T = max(0, T_vac - p_amb A_e) | +1 | `ATOL_KG` g_eff [N] | a hold-down extended past t = 0 |
| `track_end` | s - L | +1 | `ATOL_M` 1e-6 m | the push (RELEASE follows) |
| `drive_limit` | F_drive(t, y), the assist model's drive force at the delivered thrust | -1 | `ATOL_KG` g_eff [N] | the push (status `drive_limit`); listed only when the model forbids a negative drive force |

The two track events read the track state (`ev_track_end`, `ev_drive_limit`; "Silo
model" for the drive-limit threshold and its disarm behaviour). An event built
by hand gets `EVENT_ZERO_TOL` = 1e-12 in its own unit. `ev_liftoff` takes the pad
pressure `p_amb_pa` (0 in Phase 1, where vacuum thrust from sea level is a stated
assumption); Phase 2 must pass the real pad pressure, because on vacuum thrust the pad
would lift off early by the p_amb A_e deficit (~0.6 MN, 7% of thrust, for the F9 stage),
which flatters the pad baseline.

`integrate_phase` applies these rules before and after `solve_ivp`:

1. **Already past.** Every terminal event is evaluated at (t0, y0). If |g(t0)| >
   zero_tol and it is on the side it lands on after firing (direction * g(t0) > 0;
   g(t0) < 0 for a direction-0 event, whose function is by convention positive while
   the phase may continue), the phase ends at t0 with `ended_by` = that event,
   `event_times = ((name, t0),)` and a note; nothing is integrated. scipy alone would
   never fire it (no sign change) and the phase would run on to t_max.
2. **On the surface at t0.** The root scipy leaves at an event is not an exact zero:
   brentq stops at 4 eps in time, so the event function at the root is 0 or a few ulp
   of the state on either side (measured: the F9 stage-1 propellant root lands at
   m - m_dry in {0, +2.9e-11, -2.9e-11} kg = {0, +1, -1} ulp of 146,870 kg depending on
   t_ign; an apex found at t = 3000 s leaves v = +1.4e-12 or -1.2e-12 m/s). Any fixed
   absolute test smaller than that would classify the next phase at random, so the test
   is |g(t0)| <= zero_tol, i.e. within the state's atol. scipy *does* fire a
   direction-matched (or direction-0) value at or on the non-firing side of zero at t0
   (verified on scipy 1.18: its test is `g >= 0 and g_new <= 0`, which an exact zero
   or a +1 ulp residue satisfies). The engine therefore predicts where the event will
   be after the first step with a second-order (Heun) step of the phase's own RHS and
   applies scipy's test to (0, g_pred): if it would fire, the event is **disarmed**:
   its callable returns a constant on its firing side whenever |g| <= zero_tol, so
   neither the stale residue at t0 nor a function that never leaves the band (m = m_dry
   exactly with no thrust; scipy fires on g = g_new = 0) can register as a crossing,
   while a genuine later crossing (v going back through zero under thrust) fires as
   usual, located at the edge of the band, i.e. within the state's atol. Heun rather
   than Euler because a state with zero first derivative (altitude at apex, velocity
   at a turnaround under exactly balanced thrust) is predicted unchanged by Euler and
   the guard would sit on the wrong side. If the prediction says the event moves away
   from its firing side (the apex event at a TWR > 1 pad start: v grows; the
   turnaround at the start of any fall), it stays armed unguarded; scipy does not fire
   it either.

   **The disarm is a backstop, not a planner pattern.** It cannot tell a stale zero
   (the apex that ended the previous phase) from a phase that starts *on* the event
   surface moving into it: a burn listing `impact` from z = 0 while sinking runs to
   t_max and raises instead of reporting the impact; a pad burn at TWR < 1 listing
   `apex` and `impact` disarms both and sinks below the pad with a nominal-looking
   result; a ramp lit exactly at t0 from rest sinks 11 m before rising. In the plan's
   state machine the rule is never needed: a falling phase re-crosses v = 0 only upward
   (`turnaround`, which stays armed by construction), the apex can fire again only in
   a later rising phase, and the propellant event after burnout belongs to no later
   phase. The planner therefore (a) never lists the event that ended the previous
   phase, (b) starts pad burns only after the liftoff root (the HOLD rule), and (c)
   surfaces every "disarmed" note as a run flag. One such case can still arise from an
   `AscentStart` (never from a config): an unpowered falling phase that starts on the
   ground, z within ATOL_M of z_ground and moving down (a start at the ground already
   sinking, or an apex within ATOL_M of the ground, i.e. v0 < sqrt(2 g ATOL_M) =
   4.4 mm/s). `VerticalPlanner._coast` resolves it itself: the phase is a zero-length
   pass-through ended by `impact` at t0, with a note (a run flag) saying so, instead of
   an integration that would disarm the impact and run to t_max.
3. The terminal event whose root equals the last sample time is `ended_by`;
   non-terminal events are logged in `event_times` with their roots. A terminal root
   that coincides with t_end is reported either as the event (scipy status 1, with an
   `event_times` entry) or as `"t_end"` (status 0, no entry), depending on the sign of
   the ~1e-13 residue at the last sample: scipy sets status 0 on reaching t_bound and
   then, in the same iteration, overrides it with 1 if the event test fires at that
   final sample (measured on scipy 1.18: a constant-g coast with `apex` and t_end =
   v0/g exactly ended by `apex` for v0 in {g0, 2 g0, 30 m/s} with v_end = 0, -1.8e-15,
   -7.1e-15). Either report is consistent, so the planner treats `ended_by`, not
   `event_times`, as authoritative for how a phase ended.
4. **Event states.** `PhaseResult.y_events[name]` holds the state at each occurrence
   of an event (shape (occurrences, states), in the order of that name's entries in
   `event_times`): scipy's `sol.y_events`, which its event locator evaluates on the
   step's own interpolant at the root, so it needs no dense output. An event already
   past at t0 (rule 1) gets the state at t0; a listed event that never fired maps to
   an empty (0, states) array, in an integrated phase and a pass-through alike (a
   zero-span phase lists every event of its spec with no occurrence). `event_state(res, name, te)` returns the state of the
   occurrence at exactly te (as logged in `event_times`) and raises ValueError for
   anything else. It is the only correct lookup when `dense_output` is off: the
   Phase 1 lookup (the terminal root is `y_end`, any other occurrence is read from the
   dense output, and `y_end` when there is none) would silently return the phase's
   last state for a non-terminal event. The track prelude (`fly_track`, shared with
   the Phase 2 planar search) reads its event states with `event_state`. The 1-D
   planner keeps that Phase 1 lookup, which is exact for it: every event it lists is
   terminal, so its root is the phase's last sample and the lookup returns `y_end`
   (the dense branch is never reached). For a terminal root the two lookups are
   bit-identical, because scipy evaluates `y_end` and the last `y_events` entry with
   the same interpolant call at the same root; a planner that lists non-terminal
   events must use `event_state`. With dense output on, `event_state` and the dense
   output agree to round-off at every root (1e-12 relative asserted), and dense-off
   and dense-on runs log identical event states (exact); repeated occurrences of one
   event keep their time order (`test_repeated_event_occurrences_keep_their_order`).
   Every event, terminal or not, must be monotone within its phase, or the phase must
   cap `max_step` below the shortest excursion of the event function: scipy only sees
   a sign change between step ends, so an event crossed twice inside one step is
   never logged, and a terminal one then never ends the phase (a direction-0 altitude
   mark on a coast whose DOP853 step grows tenfold per step with no cap is missed; so
   is a terminal crest event x - (A - 1e-3) on x = 5 cos(2 pi t / 3), which ran to t_end
   with `max_step` inf or 0.05 s and fired at the closed-form root only with
   0.005 s). In the 1-D planner the coasts are monotone by construction (the sigma
   partition: v changes sign only at the phase-ending apex or turnaround, and z is
   monotone between them); a burn's v need not be monotone (a TWR < 1 burn), and the
   burns rely on the ramp and lag `max_step` caps and on the slow change of thrust
   and mass for their events. Planners that add events (Phase 2) carry this as a
   design rule for every event they list.

Validation (`test_events.py`): the propellant event lands with |m - m_dry| < 1e-6 kg;
the apex event does not re-fire at the start of a fall from v = 0 (engine robustness
check) and the fall reaches the ground at sqrt(2 z0 / g); apex residues of +/-2e-12 and
+/-1e-10 m/s at the start of a fall neither end it at t0 nor fire on the first step; an
F9 propellant residue of -1, 0, +1 ulp at the start of a coast that still lists the
event does not end it (the coast reaches its apex); a fall started from an apex root at
t0 = 3000 s (v0 = 2000 m/s, mu/r^2) with turnaround, apex and impact listed reaches
impact after exactly the rise time; an event function that never moves (m = m_dry with
no thrust) never fires; the turnaround does not fire at the start of a fall from v in
{0, -1e-13, -1e-15}; a TWR > 1 pad start does not trigger the apex at t = 0; a
turnaround under a ramp lit after a guarded start fires at the real crossing; a phase
already past a terminal event ends at t0 with the state untouched and the event in
`event_times`; zero-length and 1e-4 s phases; an open-ended phase without a terminal
event raises at t_max; the direction-0 convention; an unknown integrator method is
rejected; a `PhaseSpec` whose sigma disagrees with `params.v_sign` is rejected; the
liftoff event uses the delivered thrust when a pad pressure is given;
`planar_rotation_rate(0, pi/2) R_E = 465.101 m/s`,
`planar_rotation_rate(28.5 deg, 90 deg) = 6.408435e-5 rad/s`, `g_eff_track(0) =
9.7982855`, `g_eff_track(6.408435e-5) = 9.7720917 m/s^2`.

The RHS branches a rising vacuum burn never touches are covered in
`test_vertical_burn.py`: a 10 s burn while falling at -300 m/s (sigma = -1) gives
J_steer = 2 c ln(m0/mf), J_grav = -g t and v_f = v0 + c ln(m0/mf) - g t; a 2 s ramp at
sea level with p_amb A_e = T_full/2 delivers zero thrust for 1 s while burning
mdot t^2/(2 t_r) with J_bp = J_vac, then v(2) = c ln(m(1)/m(2)) - p_amb A_e
integral dt/m in closed form; both close the per-phase identity
|v_f| - |v_0| = J_vac - J_grav - J_steer - J_bp to < 1e-9 m/s, and the inlined clamp
in `rhs_vertical` is checked against `ThrustSchedule.thrust_N`.

**Planar event factories (build step 21).** `ev_ground(model, z_ground)` (called
`impact`: model.altitude(y) - z_ground, -1, `ATOL_M`), `ev_radial_apex` and
`ev_radial_turnaround` (`apex` and `turnaround`: v_r, -1 and +1, `ATOL_MPS`),
`ev_kick_start(v_k, omega_p)` (min(V - v_k, w), +1, `ATOL_MPS`),
`ev_kick_aligned(delta, omega_p)` (called `kick_end`: sin(beta_rel - delta), +1,
`EVENT_ZERO_TOL`) and `ev_time(t, name)` (t - t_event, +1, `EVENT_ZERO_TOL`; the kick
deadline and timeout). Their use, monotonicity and the event lists per phase are in
"Stage-1 guidance and events (planar)"; the planar planner reads every event state
with `event_state`. The stage-2 factories live beside the planner in
`phases/planar.py` (build step 22; `phases/engine.py` was not a file of that step):
`ev_energy_cutoff(target, mu)` (`cutoff`: E - E*, +1, `ATOL_MPS` v_c),
`ev_fmh(limit, env)` (`fairing`: ln(0.5 rho V^3 / limit), -1, `EVENT_ZERO_TOL`) and
`ev_mass_floor(m_floor)` (`mass_floor`: m - m_floor, -1, `ATOL_KG`); the stage-2
depletion is `ev_propellant` at m_empty and `no_cutoff` is `ev_time`. Each is
monotone in LTG_BURN ("Stage 2 and insertion (planar)").

**Planar event tolerance (build step 19).** A planar_2d recorded run locates every
event root at `integrator.rtol`, which the config forces equal to `search.final_rtol`
("Integrator"): the final verification and the recorded run see the same event times.
A search evaluation locates them at `search.search_rtol` with dense output off (rule 4).

## Phases and events

Modules (the `phases/` package; `launchsim.phases` re-exports every name the Phase 1
single-module `phases.py` defined, so imports are unchanged):
`phases/vertical.py` (`VerticalPlanner`, `AscentStart`, `map_release`, `map_staging`,
`END_KINDS`), `phases/prelude.py` (the hold and track prelude shared by the planners:
`IgnitionSpec`, `HoldParams`, `rhs_hold` and `hold_rhs_for(layout)`,
`hold_closed_form`, `hold_until_liftoff`, `fly_track` -> `TrackExit`, each
parameterised by the flight model's state layout; the 1-D planner runs them with
`VERTICAL_LAYOUT` / `VERTICAL_PRELUDE`), `phases/trace.py` (`TraceBuilder`, `RunTrace`,
`EventRecord`, `HoldSummary`, the phase-kind labels and the `StateView` protocol) and
`phases/engine.py` (the engine and the event factories, the stage-1 planar ones
included; the stage-2 factories `ev_energy_cutoff`, `ev_fmh` and `ev_mass_floor` are in
`phases/planar.py`, "Event rules");
`phases/planar.py` is the planar planner ("Stage-1 guidance and events (planar)" and
"Stage 2 and insertion (planar)", imported from its own module: the package's `__all__` does not list it yet);
`sim.simulate` turns the 1-D trace into a `Result`. Tests: `tests/test_hold.py`, `tests/test_staging.py`,
`tests/test_ignition_loss.py`, `tests/test_loss_identity.py`, `tests/test_events.py`
(release map and pad start), `tests/test_phases_package.py` (the package, the event
records, search-mode event states).

**Event records and state views.** An `EventRecord` holds the event's name, absolute
time, phase kind, stage, mass `m_kg` and `values`, the other columns of the run's
`StateView` as (column, value) pairs, frozen so a record is immutable and hashable
(a Mapping or any iterable of pairs is accepted and stored as a tuple of (str, float)
pairs, every value converted to a Python float with the sign of zero kept). A
`StateView` is one per dynamics model: `model`, the `layout` of the states it reads,
`columns` in output order (always including `m_kg`), `ascent_kinds` (the model's
free-flight phase kinds, which `RunTrace.ascent_phases` and so the loss budget select)
and `row(t, y, phase)`, which receives the phase kind so a view can treat clamped and
track rows differently from flight rows (the planar Earth-fixed downrange of 0 before
flight start). The 1-D view `VERTICAL_VIEW` (layout `VERTICAL_LAYOUT`, ascent kinds
`ASCENT_KINDS`) gives z_m [m] and the signed v_mps [m/s] (negative while falling, and
the sign of zero kept), read from the state exactly as the Phase 1 records did, so
events.csv keeps its columns and every fall-back row its sign (`EventRecord.z_m` and
`.v_mps` read those two columns). `TraceBuilder.add_event` refuses a state whose
length is not the view's layout, the prelude functions refuse a builder whose view
reads another layout than the one they run in (`check_layout`), and
`TraceBuilder.rebind_view` swaps in a view of the same model, layout and columns (for
a view whose parameters, like the planar flight-start time, are known only once the
flight starts). `RunTrace.view` records the view and `RunTrace.model` its model name
(`vertical_1d`). The track prelude accepts any `TrackGeometry`, as the Phase 1
planner did, and reports the exit's downrange offset (`TrackExit.x_exit_m`: 0 for a
vertical exit, L cos phi otherwise) for a `StraightTrack` only: for any other geometry
it is None, because `TrackGeometry` has no x(s) before Phase 3 and L cos phi(L) would
be wrong for a curved track. The 1-D release map reads only phi(L) and z(L), so a
curved track that ends vertical still runs in 1-D; a release map that needs the
offset (the planar one) must refuse None.

**Clock and ignition times.** t = 0 at push start (silo) or hold-down release (pad); a
HOLD runs at negative t; t_release is recorded (0 on a pad; the push time on a track)
and every metric quotes t - t_release. `IgnitionSpec(t_ign_s, reference, startup,
fails)` is built from `config.IgnitionConfig` at the boundary. First stage:
t_ign_abs = t_release + t_ign_s for reference `release`, t_ign_abs = t_ign_s for
`push_start` (t_release = sqrt(2L/a) is closed-form for the constant-acceleration
drive, so both resolve before anything is integrated). Stage k > 0: t_ign_abs = end of
its staging coast + t_ign_s, with t_ign_s >= 0 and reference `release` (the staging
coast is unpowered). `t_ign_rel_release_s_<stage>` is reported for every stage that
got to ignite; a stage whose ignition fails (`fails: true`) gets none: its scheduled
t_ign_s is moot because its T_vac is identically zero ("Failed-ignition coast"), and a
t_ign_s, reference or startup override set away from the defaults on such a stage is
recorded as an `ignition_failed: ... ignored` run flag.

**State machine.** One `solve_ivp` per phase; the phase issued after event E never
lists E, and that is structural: the event lists are partitioned by sigma (a rising
phase lists `apex`, never `turnaround`; a falling one `turnaround` and `impact`, never
`apex`; `propellant` belongs to burns only), so the apex that hands over sigma = -1 is
absent from the next list by construction, not by a guard. Sub-phase boundaries sit at
every thrust kink so the right-hand side is smooth inside a phase; sigma is fixed per
phase and, at v = 0, +1 unless the net acceleration is negative (a fall from rest: a
vehicle at rest above the ground with its thrust below its weight sinks first); at most
`MAX_PHASES_PER_RUN` = 200 phases per run. The planner holds one ambient pressure
`p_amb_pa` (0 in Phase 1: vacuum thrust from sea level) that the hold-down balance, the
sigma rule at v = 0 and the burn right-hand side all use for the delivered thrust, so
they cannot disagree about whether a vehicle lifts or sinks; `sim.run` likewise takes
omega_p from the single `OMEGA_P_PHASE1_RADS` = 0 it quotes in the assumptions.

| Phase | State / RHS | Ends by | Then |
|---|---|---|---|
| HOLD (t_ign_abs < 0; pad, or a silo with the engine lit before the push) | vehicle clamped: z, v held, mass by closed form `propellant_burned_kg` (no ODE; `hold_closed_form` subtracts only its own segment's increment of that closed form, so a lit hold split at any time after ignition, as a track prelude splitting at a startup kink does, gives the single-call mass); hold-down force m g_eff - T(t) tracked, its minimum reported (`hold_down_force_min_N`; not a tensile flag). On a silo the clamp carries the weight component along the track, m g_eff sin phi, and there is no liftoff extension: the push starts at t = 0 whatever the thrust | t = 0 | ASSIST or RELEASE |
| HOLD extension (pad, vehicle at rest on the ground, T(0) < m g_eff) | split at the thrust kinks. Before the ignition kink the sub-phase is *unlit* (`HoldParams.lit = False`: T = 0, nothing changes, sampled directly, no events), and at the start of every lit sub-phase the balance T - m g_eff is re-evaluated with the lit schedule, so a step whose thrust exceeds the weight lifts off exactly at its kink with the mass untouched (no root search across the discontinuity; the integrator's last stage never sees the step's f(0) = 1 from the left, which would bias the mass by 5e-6 kg, above `ATOL_KG`). A lit sub-phase integrates the mass alone (`rhs_hold`), max_step as in a burn. An ignition inside the extension is logged in the HOLD | `liftoff` (T - m g_eff, +1) -> "hold extended to t = X s for liftoff (TWR < 1 at release)" in the assumptions; `propellant` -> ValueError; t_max -> status `no_liftoff` (no exception) | BURN from the liftoff root, sigma = +1 |
| ASSIST (track) | state [s, sdot, m_v, *extra, E_drive, W_thrust, J_mass] in the track layout (`dynamics.rhs_track`, "Silo model" below); sub-phases split at the thrust kinks inside the push (ignition, ramp end); a sub-phase that ends at the ignition kink is *unlit* (T = 0 whatever the schedule says at its closing boundary, as for the HOLD); max_step = t_push/push_steps, tightened by the ramp or lag cap once lit; the ignition, ramp_end and drive_limit events are logged with the ascent-frame view of the track state (`track_to_vertical`: z = start altitude + z(s), v = sdot sin phi); a ramp that ends at the very instant of release (`silo_hot_ramp_on_track`) logs its ramp_end on the track, right before the release, and the flight's burn skips the finished segment, so the event appears once | `track_end` (s - L, +1) -> RELEASE; `drive_limit` (F_drive, -1; not listed when the model allows a negative drive force) -> status `drive_limit`, the run stops on the track (a push that starts with F_drive already negative ends at t0 by the engine's already-past rule); `propellant` -> ValueError (exhausted on the track) | RELEASE |
| RELEASE (map) | pad: z = z0, v = v0 of the `AscentStart` (0, 0 for the pad; only a start at rest *on the ground* is held down, one at rest above it falls; a *moving* start lit before release is a test-only emulation of "lit on the carriage" without a track: the HOLD burns mass only and its rows keep v0, which is not a physical state but reproduces the straddle form exactly), m = m(0); track: `map_release` (z = exit altitude, v = sdot, m; a track angle other than pi/2 raises: projecting sdot onto the vertical would silently discard the downrange component, so the 1-D map is exact for a vertical track only and a tilted exit waits for the planar branch); quadratures reset; t_release recorded | | COAST_PRE_IGN or BURN |
| COAST_PRE_IGN | T = 0, sigma = +1 | t = t_ign_abs; `apex` -> FALL_PRE_IGN (sigma = -1, `impact` listed) | BURN; impact -> status `impact` |
| BURN k | ramp sub-phase (ends at t_ign + t_ramp, max_step t_ramp/ramp_steps) then the full burn (open-ended); lag: one burn with max_step tau/lag_steps_per_tau; step: one burn; `propellant` always listed | sigma = +1: `apex` -> same burn with sigma = -1 (`turnaround`, `impact` listed); sigma = -1: `turnaround` -> sigma = +1 (`apex` listed), `impact` -> status `impact`; `propellant` -> burnout | STAGING, or end |
| STAGING (map) | m -= dry mass of stage k (+ fairing when `fairing_drop: staging` and k = 0): `map_staging`; z, v, quadratures unchanged | | COAST_STAGING |
| COAST_STAGING / FALL_STAGING | T = 0 for stage k+1's `coast_before_ignition_s` (zero-length pass-through when 0); events by sigma as for COAST_PRE_IGN | t = coast end | COAST_PRE_IGN (t_ign_s > 0) or BURN k+1 |
| COAST / FALL (terminal) | T = 0 after the last burnout, or after a failed ignition (`fails: true`, which requires `end: impact`; the `ignition_failed` event marks where the coast began and `RunTrace.failed_stage` / `t_fail_s` record it; no COAST_PRE_IGN, whatever the stage's t_ign_s) | `apex` (end `apex`: stop), then `impact` at z_ground = 0 | status `impact` |

`end` = `stage1_burnout` stops after the first stage's burnout, `all_burnout` after the
last stage's, `apex` coasts to the apex (a vehicle already falling at burnout has
passed it: the run stops there with a flag), `impact` coasts to apex and falls to z = 0.
Every phase is `integrate_phase`'s job; the planner meets the obligations of the
"Event rules" section: it never lists the event that ended the previous phase, starts
pad burns only after the liftoff root, turns every engine note (a disarmed event) into
a run flag, treats `ended_by` as authoritative, and asserts on every ascent phase's
samples that sigma v >= -`ATOL_MPS` (a sign change inside a phase raises RuntimeError:
the identity would still close, so this is the only check).

**Per-phase tolerances.** atol from the state layout (`atol_for`); max_step =
t_ramp/ramp_steps in a ramp sub-phase, tau/lag_steps_per_tau in a lag burn, unbounded on
coasts and step burns; open-ended phases carry the t_max guard.

**Result content.** The time series samples every phase at `sample_dt_s` on the
absolute clock (multiples of the interval, so phases share the grid) plus every phase
boundary, from the dense output (the closed-form HOLD is sampled directly): t_s,
t_rel_release_s, z_m, v_mps, m_kg, thrust_N, thrust_vac_N, accel_felt_g, phase, stage
and the five quadratures, plus the track columns s_m, drive_force_N,
interface_force_N, drive_power_W, track_normal_g_vehicle and track_normal_g_carriage
(`dynamics.track_observables`; NaN outside ASSIST rows). accel_felt_g is the proper
(felt) axial acceleration in units of g0 through `units.to_g`: T/m in free flight
(vacuum thrust, unthrottled), g_eff while clamped, because the hold-down carries the
weight and the vehicle feels 1 g_eff, not the thrust building under it, and
(F_int + T)/m_v = sddot + g_eff sin phi on the track. ASSIST rows show the ascent-frame
view of the track state (z from the track start altitude, v = sdot sin phi) with the
ascent quadratures at 0 (the accounting starts at release). Both ends of a phase
boundary are kept (the staging mass drop is visible, and the release row appears
once in the track frame and once in the ascent frame). Events (t_s, event, phase,
stage, z_m, v_mps, m_kg): push_start, ignition, release, liftoff, ramp_end,
drive_limit, ignition_failed, propellant, apex, turnaround, staging, impact, end. The
`phase` of an event is the phase it ended or started; a pad's release row is labelled
HOLD when a hold ran before t = 0 and RELEASE (`phases.trace.RELEASE_LABEL`, not a phase
kind) when nothing was lit before release, since it then belongs to no phase; a
track's release row is labelled ASSIST. Metrics: the release state and what was burned before it (with its
delta-v equivalent c ln(m0/m_release)); the flight start (`t_flight_start_s`,
`mass_at_flight_start_kg`, `propellant_burned_before_flight_kg`,
`dv_vac_equiv_before_flight_mps`: release, or the liftoff root of an extended hold,
where the loss accounting begins); the hold (duration, extension, minimum hold-down
force, `hold_propellant_burned_kg` over the whole clamp); the first stage's burnout
(time from release, speed, altitude, mass); the final state; the highest apex and the
impact when reached; the peak felt acceleration in flight with its time and mass
(`peak_felt_g_flight`) and the run-wide peak `peak_felt_axial_g` (the CLAUDE.md
summary item: the largest accel_felt_g over the hold, the track and the flight, with
`peak_felt_axial_g_phase` and `_t_s` saying where it occurs, so a push above ~4.7 g0
net or a failed ignition reports the track's a + g_eff rather than the flight's T/m);
t_ign_rel_release_s per stage; the loss budget below; and, for a track run, the silo
quantities of the "Silo model" section. Status (nominal, impact, no_liftoff,
drive_limit) and flags (every disarmed-event note, no_liftoff, drive_limit,
interface_tensile, drive_braking) live on the Result (metrics.json adds them). A track
run that stopped with drive_limit never released: its release items and every time
counted from release are None ("Silo model"). The assumptions list names the gravity model and the
g_eff `simulate` was actually handed (`ConstantGravity` in a test is reported as such);
`sim.run` prepends the run-model lines (mu/r^2, g_eff = mu/R_E^2 with omega_p = 0).

**Hold-down bookkeeping.** With the F9 lit at t = -2 s (its 2 s ramp) 2,697 kg burn
on the pad (`mdot t_r/2`), the release mass is 539,873 kg and the hold-down carries
2.94 MN of tension at release (full thrust above the weight). Lit at t = 0 instead,
the hold extends to the root of T_full t/t_r = (m0 - mdot t^2/(2 t_r)) g_eff,
t* = 1.28974 s (matched to 2e-14 s by the liftoff event), and the burnout comes
t_b + t_r/2 after ignition regardless. Time clamped past t = 0 is not a gravity loss:
the hold-down carries the weight and v stays 0, so the identity starts at liftoff with
speed_start = 0 and nothing accrues; the extension is reported instead. What *is*
spent while clamped past t = 0 is propellant: 1,122 kg burn between t = 0 and t*, worth
c ln(m0/m_lift) = 6.31 m/s, and `dv_vac_mps` (which starts from the liftoff mass,
3,979.2 m/s) is short of c ln(m0/m_dry) = 3,985.5 m/s by exactly that. The
`*_before_release` metrics stay 0 for this run (nothing burned before t = 0); the
`*_before_flight` metrics carry the 1,122 kg / 6.31 m/s, and
dv_vac_mps + dv_vac_equiv_before_flight_mps = c ln(m0/m_dry) holds for every pad run,
so an identity line against the liftoff mass must use the `before_flight` pair (for
the -2 s baseline both pairs agree). A failed ignition on the pad never lifts off: the
run ends at t_max with status `no_liftoff` and the flight-start metrics are n/a.

## Loss accounting (release onward, 1-D, including a fall-back through apex)

Module: `losses.py` (`LossBudget`, `loss_budget`); the quadrature states are in
`dynamics.py`. Tests: `tests/test_loss_identity.py` (a to e), `tests/test_staging.py`,
`tests/test_ignition_loss.py`.

With sigma the sign of v (fixed per phase) and omega_p = 0 (v_rel = v, drag = 0):

    d|v|/dt = sigma (T/m - g)
            = T_vac/m - g sigma - (T/m)(1 - sigma) - (T_vac - T)/m

The four terms are the quadratures dJ_vac, dJ_grav, dJ_steer and dJ_bp of the 1-D
state, so over one phase |v_f| - |v_0| = J_vac - J_grav - J_steer - J_bp exactly. sigma
is constant per phase and |v| is continuous across every phase boundary (the release
and staging maps change m, not v), so summing the per-phase increments closes the
accounting from release to the end of the run:

    |v_f| - |v_0| = dv_vac - gravity - drag - steering - back_pressure

which is CLAUDE.md's identity with v_rel = v. `LossBudget(dv_vac, gravity,
gravity_alt, drag, steering, back_pressure, speed_start, speed_end)` holds the sums,
`residual_mps()` the closure, and `gravity_duration` = gravity - gravity_alt = g_ref
times the signed time of flight: the gravity loss splits into a duration part (which
holds the ignition-delay loss and the hold-down credit) and an altitude part
J_alt = integral of (g - g_ref) sigma dt (the "flew higher" effect, <= 0 above the
datum while rising: -14.9 m/s for the F9 first stage under mu/r^2). The quadratures
reset at release (t = 0 on a pad, the track-end root on a silo), speed_start = |v| at
release (the exit speed sqrt(2 a L) on the silo), and the HOLD and ASSIST phases
contribute nothing (the track has its own energy budget, "Assist energy identity"
below; what burns there is reported as burned before release); the budget sums the
free-flight phases
(`RunTrace.ascent_phases()`, kinds COAST_PRE_IGN, FALL_PRE_IGN, BURN, COAST_STAGING,
FALL_STAGING, COAST, FALL).

Falling with thrust on (sigma = -1): the gravity term is negative (speed is regained
while falling) and the steering term is 2T/m (psi = pi: thrust against the velocity),
so a burn that slows a fall shows up as dv_vac spent, 2 dv_vac of steering loss and a
negative gravity "loss", and |v| decreases by dv_vac - g t as it must. Through a
turnaround the burn splits into a sigma = -1 phase (steering 2 c ln(m_ign/m_turn)) and
a sigma = +1 phase (no steering), and the closure holds across the split because |v|
is continuous (0) there. J_vac = c ln(m_release/m_final) whenever the propellant is
burned, so at fixed propellant every variant's dv_vac is the same and the speed delta
between variants is exactly the delta of their loss terms plus the delta of their
release speed: that is the printed identity line of the summaries ("Figures of merit in
1-D").

Validation: (b) toy at 1000 kg with 50 kg of propellant, constant g, released upward at
300 m/s, lit at t = 40 s while falling at -92.3 m/s and 4155 m, a 10 s burn against the
velocity (v < 0 throughout), then a fall to impact: steering = 2 c ln(m(40)/m(50)),
the fall's gravity increment negative, impact speed from energy; (c) the same with
150 kg (30 s): exactly one apex (before ignition) and one turnaround, burnout speed
v_ign + c ln(m0/mf) - g t_b, steering = 2 c ln(m0/m_turn); with end `impact` a second
apex at z_bo + v_bo^2/(2g) and the fall; (d) the F9 pad start (lit at -2 s) under mu/r^2
to stage-1 burnout: gravity_duration = g_ref t_b exactly, gravity_alt < 0, dv_vac =
c ln(m_release/m_dry); (e) an apex *inside a burn*: the toy released at z0 = 1000 m
with v0 = 3 m/s and a 4 s ramp lit at release, so the thrust is below the weight until
t = t_r m g/T = 2.6 s and the vehicle tops out under thrust: the burn splits BURN(+1,
apex) -> BURN(-1, ramp end) -> BURN(-1, turnaround) -> BURN(+1, propellant), exactly one
apex and one turnaround, steering = 2 c ln(m_apex/m_turn) and the signed burnout speed
v0 + c ln(m0/mf) - g (t_b + t_r/2) (dv/dt = T/m - g whatever the sign of v); from
z0 = 0 the same start hits the ground while thrusting: BURN(+1, apex) -> BURN(-1,
impact), status `impact`, no burnout; (a) the F9 through the 3 g0 / 100 m silo
(`silo_cold`: 0.5 s delay and the 2 s ramp after release) under mu/r^2 via `sim.run`
from the experiment's assist block: speed_start = sqrt(2 a L), quadratures zero at
release, dv_vac = c ln(m0/m_dry) (nothing burns on the track), burnout t_d + t_r/2 +
t_b after release with gravity_duration = g_ref times that. The residual is asserted
< 1e-6 m/s in every case (CLAUDE.md allows 0.01) and measured at 1e-12 m/s: v and the quadratures are
integrated by the same solver from the same expressions, so only rounding separates
them. The identity is also recomputed in the tests from the reported metrics, not
through `residual_mps()`.

## Ignition-after-release loss (exactness)

Module: `losses.py` (`ignition_loss_analytic_mps`, `prerelease_full_thrust_seconds`,
`lag_deficit_exact_s`). Test: `tests/test_ignition_loss.py`.

Reference: instant full thrust at release from the same state and mass m0, propellant
m_p, full-thrust burn time t_b = m_p/mdot. Every variant burns the same propellant, so
J_vac is identical; with constant g and v > 0 throughout, the speed at burnout differs
only by g times the extra time the burn takes.

- Delay t_d then a linear ramp t_r (propellant outlasting the ramp): the ramp burns
  mdot t_r/2, burnout is at t_d + t_r/2 + t_b, loss = g (t_d + t_r/2), **exactly**.
- Delay t_d then a first-order lag tau: after ignition the burned propellant is
  mdot [s - tau (1 - e^(-s/tau))], so the burn ends at s_e = tau u with
  u - 1 + e^(-u) = t_b/tau, i.e. u = 1 + t_b/tau + W0(-e^(-1 - t_b/tau)) (Lambert W,
  principal branch; the argument lies in (-1/e, 0)), and the exact loss is
  g [t_d + tau (1 - e^(-u))]. g (t_d + tau) is the long-burn asymptote, short by
  g tau e^(-u): 0.024 m/s for a 5 s toy burn with tau = 1 s (resolved by the test),
  1e-63 m/s for the 147 s F9 burn.
- Lit before release (t_ign < 0; a hot start on the track or a held-down pad): Phi_pre
  full-thrust seconds burn before release (ramp: t_ign^2/(2 t_r) for -t_r < t_ign < 0,
  -t_ign - t_r/2 for t_ign <= -t_r; lag: -t_ign - tau (1 - e^(t_ign/tau)); step:
  -t_ign). Their delta-v c ln(m0/(m0 - mdot Phi_pre)) is spent into the clamp, the
  gravity g Phi_pre they would have cost in flight is saved, and D_post (the
  post-release deficit of the remaining ramp or lag, `startup_deficit_s`, which
  already contains max(t_ign, 0)) still costs g D_post:

      loss vs instant = c ln(m0/(m0 - mdot Phi_pre)) - g Phi_pre + g D_post

  Because T/m0 > g whenever the vehicle can lift off, burning on the pad always costs
  more delta-v than the gravity it saves: the F9 lit a full ramp before release
  (Phi_pre = 1 s, 2,697 kg, 15.20 m/s of delta-v spent into the clamp) is behind an
  instant start by 5.40 m/s under constant g_eff = 9.79829 m/s^2 (15.20 - 9.80), and
  by 5.58 m/s integrated under mu/r^2, of which 0.17 m/s is the altitude term (the
  instant start flies higher for the whole burn): that is the "hold-down credit" the
  unphysical `pad_instant` and `silo_instant` yardsticks enjoy, and the summaries
  print both figures. (`test_ignition_loss.py` checks the same formula under the
  g0 = 9.80665 m/s^2 it injects: 5.39 m/s to 5e-3, bracketed by T/m0 - g0 and
  T/(m0 - mdot) - g0; a test number, not the run model's. `test_hold.py` integrates
  it through the moving-start emulation.) For the lag the exact
  post-release deficit is tau (a + W0(-a e^(-a - t_b'/tau))) + max(t_ign, 0) with
  a = e^(min(t_ign, 0)/tau) and t_b' = t_b - Phi_pre (`lag_deficit_exact_s`; a = 1
  recovers the case above).

`ignition_loss_analytic_mps(g_ref, t_ign, startup, c, mdot, m0, t_burn_s=None)`
implements the formula; with `t_burn_s` the lag term is exact, without it the
asymptote. Under mu/r^2 the delayed vehicle flies lower for the whole burn, which adds
~0.1-0.7 m/s (about 3%) to the constant-g value; runs report the integrated
difference and the constant-g formula side by side, the difference being the
`gravity_loss_alt_mps` delta. Validation (F9 stage 1, v0 = 77 m/s, g0 injected):
(0 s, 1 s) 4.903 m/s, (0.5 s, 2 s) 14.710 m/s, (1 s, 3 s) 24.517 m/s, each matched by
the integrated difference to < 1e-5 m/s with identical dv_vac (1e-10 relative) and
burnout at t_d + t_r/2 + t_b; lag tau = 1 s on the 5 s toy burn and on the F9 burn to
< 1e-5 m/s; the straddle formula for t_ign = -1.5 s, t_r = 2 s (Phi_pre = 0.5625 s,
D_post = 0.0625 s) is checked against the function and integrated through the
3 g0 / 100 m silo (`test_ramp_straddling_the_release_through_the_silo`: constant g in
flight and the same g as the track's g_eff, against `silo_instant` from the same
track): the difference matches to < 1e-5 m/s, the release mass is m0 - mdot Phi_pre
and the burnout comes (t_b - Phi_pre) + D_post after release. Lighting on the
carriage costs speed; it adds none.

## Assist energy identity

Module: `losses.py` (`AssistEnergyBudget`, `assist_energy_budget`); the quadrature
states are in `dynamics.rhs_track`. Test: `tests/test_assist_energy.py`.

Along the track (CLAUDE.md, phase 2) the system riding it, M = m_v + m_c, obeys

    M sddot = F_drive + T_sys - M g_eff sin phi - F_other,      T_sys = (1 - f_imp) T

**Impingement amendment.** CLAUDE.md's track equation carries the vehicle's full
axial thrust T. With the engines lit on the carriage a fraction f_imp of the exhaust
impinges on the carriage and pushes it back with -f_imp T, so the *system* keeps
T_sys = (1 - f_imp) T; f_imp = 0 recovers the CLAUDE.md equation and f_imp = 1 means
the drive carries the whole M (a + g_eff sin phi) as if the engines were off. f_imp is
an assumed parameter (0 and 1 both run; `exhaust_impingement_fraction` in the config),
stated as such in every assumptions list. The vehicle always feels its own full thrust:
the interface force the carriage exerts on it is F_int = m_v (sddot + g_eff sin phi) - T
(negative: tension, the vehicle would have to be held back), and the vehicle's felt
axial acceleration is (F_int + T)/m_v = sddot + g_eff sin phi.

**Derivation.** With the mechanical energy E = M sdot^2/2 + M g_eff z and dz/dt =
sdot sin phi,

    dE/dt = M sdot sddot + Mdot sdot^2/2 + M g_eff sdot sin phi + Mdot g_eff z
          = (F_drive + T_sys - F_other) sdot + Mdot (sdot^2/2 + g_eff z)

so, integrated over the push (Mdot = mdot_v <= 0: the expelled propellant leaves with
the kinetic and potential energy it had),

    integral (F_drive + T_sys) sdot dt
        = delta(M sdot^2/2 + M g_eff z) - integral Mdot (sdot^2/2 + g_eff z) dt + dissipated

with dissipated = integral F_other sdot dt (friction, damping: 0 for the screening
drive). The three integrals are quadrature states of the track phase (atol 1e-3 J):

    dE_drive/dt  = F_drive sdot
    dW_thrust/dt = (1 - f_imp) T sdot
    dJ_mass/dt   = (dm_v/dt) (sdot^2/2 + g_eff z(s))        <= 0

`AssistEnergyBudget(work_drive, work_thrust, delta_mech, massflow_term, dissipated)`
holds E_drive, W_thrust, delta(M sdot^2/2 + M g_eff z) from the first ASSIST phase's
start to the last one's end, -J_mass (>= 0) and 0; `residual_J()` = work_drive +
work_thrust - delta_mech - massflow_term - dissipated and `residual_rel()` =
|residual|/max(|work_drive + work_thrust|, 1 J) is reported as
`assist_energy_residual_rel` (required < 1e-6, asserted < 1e-9, measured 1e-16 cold
and 2e-15 hot). Validation (F9, 3 g0, L = 100 m, g_eff = mu/R_E^2): cold, m_c in
{0, 20 t}: E_drive = M (a + g_eff) L (= delta KE + delta PE), W_thrust = massflow = 0;
hot with full thrust for the whole push (the ramp completed in the hold before it, so
M(t) = M0 - mdot t with M0 = m0 - mdot t_r/2, sdot = a t): E_drive + W_thrust =
(a + g) a [M0 t_p^2/2 - mdot t_p^3/3] whatever f_imp (impingement only moves thrust
work from W_thrust to E_drive), W_thrust = (1 - f_imp) T L, delta_mech =
M_exit (a + g) L, massflow_term = mdot (a + g) a t_p^3/6, all at 1e-10 relative
(DOP853 integrates these polynomials exactly); and a ramp lit inside the push
(`silo_hot_ramp_on_track`), where only the closure is asserted.

## Silo model (constant_accel, vertical) and every reported quantity

Modules: `assist/constant_accel.py` (`ConstantAccelAssist`), `assist/base.py`
(`AssistModel`, `AssistForces`, `normal_load_N`), `assist/track.py`, `assist/__init__.py`
(`build_assist`, the registry), `dynamics.py` (`TrackParams`, `rhs_track`,
`track_observables`, `track_to_vertical`), `phases/prelude.py` (`fly_track`: the push
to the track exit), `phases/vertical.py` (`VerticalPlanner.run_track`, `map_release`),
`phases/engine.py` (`ev_track_end`, `ev_drive_limit`), `metrics.py` (`track_metrics`,
`track_flags`). Tests: `tests/test_silo.py`, `tests/test_assist_energy.py`,
`tests/test_events.py` (release map from a track), `tests/test_loss_identity.py` (a),
`tests/test_ignition_loss.py` (straddle through the silo).

**Model.** The drive prescribes the net acceleration along the track, sddot = a
exactly, and the drive force is solved from the track equation at every instant:

    F_drive = M (a + g_eff sin phi) - (1 - f_imp) T
    F_int   = m_v (a + g_eff sin phi) - T
    N       = m (kappa sdot^2 + g_eff cos phi) - F_other . n_hat     (per body; 0 vertical)

so every closed form is exact (v_exit = sqrt(2 a L), t_push = sqrt(2 L/a), s = a t^2/2)
and a hot start changes the forces and the energy, never the exit speed; force and
power limits are Phase 3's `linear_motor` behind the same `AssistModel` interface
(`state_rate(t, s, sdot, extra, m_v, m_c, T, g_eff, track) -> AssistForces(sddot,
F_drive, F_drive_normal, F_int, dissipated, extra_rate)`, `push_time_estimate(track)`,
`braking_distance_m(v)`, `facility_length_m(track, v_exit)`: the model does not own
the track, so the plan's `push_time_estimate()` and `facility_length_m(v)` take it as
an argument; a registered class also provides `from_config(config, g_eff) -> (model,
track | None)`, the `assist.base.AssistBuilder` protocol). Track state
[s_m, sdot_mps, m_kg, *extra, E_drive_J, W_thrust_J, J_mass_J]; dm/dt = -T_vac/c
follows the vacuum thrust as in flight. The push runs from s = 0 at rest at t = 0
(after any hold, "Phases and events") to the `track_end` root, where `map_release`
carries (sdot, m_v) into the ascent frame at z = exit altitude with the quadratures
reset and t_release = the root (sqrt(2 L/a) to 1e-14 s); the carriage stays. Braking
is not modelled as a phase: d_brake = v_exit^2/(2 a_brake) = L a/a_brake is added to
the facility length. A vertical straight track has no normal load (phi = pi/2, kappa =
0); the horizontal check N = m g_eff and the untouched sddot = a exist at unit level
only (Phase 1's config accepts 90 deg alone).

**Reported quantities** (F9, 542,570 kg, a = 3 g0 = 29.41995 m/s^2, L = 100 m,
m_c = 0, cold, g_eff = 9.7982855 m/s^2; `sim.run` on `experiments/silo_screening_1d.yaml`):

| Quantity (metric) | Definition | Value |
|---|---|---|
| exit speed, push time (`exit_speed_mps`, `push_time_s`, `t_release_s`) | sqrt(2 a L), sqrt(2 L/a) | 76.70717 m/s, 2.60732 s |
| felt axial g on the track (`felt_g_track_peak`) | (F_int + T)/m_v = a + g_eff = 39.2182 m/s^2, in g0 | 3.9992 g0 on the full stack |
| peak felt g in flight (`peak_felt_g_flight`) | max T/m over the burn (unthrottled, stated) | 5.712 g0 at stage-1 burnout, every variant |
| peak felt axial g, run-wide (`peak_felt_axial_g`, `_phase`, `_t_s`) | max over the hold (g_eff), the track (a + g_eff sin phi) and the flight (T/m); the CLAUDE.md summary item | 5.712 g0 (BURN) at 3 g0 net; 5.999 g0 (ASSIST) at the sweep's 5 g0; 3.999 g0 (ASSIST) for `silo_failed` |
| interface force (`interface_force_peak_N`, `_min_N`, `peak_interface_force_N`) | F_int = m_v (a + g_eff) - T over the push; `interface_tensile` flag if F_int < 0 at any ASSIST sample (the hold-down load is reported separately) | 21.2786 MN (README 21.5 MN at 549 t) |
| drive force (`drive_force_peak_N`) | F_drive = F_int + m_c (a + g_eff) + f_imp T | 21.2786 MN (22.1414 MN with the 22 t sled) |
| track-normal load (`track_normal_g_vehicle_peak`, `_carriage_peak`, `peak_track_normal_g`) | N/m per body in g0 (the kinematic demand for a massless carriage) | 0 g0 |
| drive energy (`drive_energy_J`, `_kWh`, `assist_energy_J`, `_kWh`) | E_drive = integral F_drive sdot dt, the net drive work of the energy identity; cold: M (a + g_eff) L = delta KE + delta PE | 2.1279 GJ = 591.1 kWh |
| drive work in and out (`drive_work_in_J`, `drive_work_out_J`) | integral max(P, 0) dt and integral max(-P, 0) dt with P = F_drive sdot (`losses.drive_work_split`: since sdot >= 0 on a push, P changes sign where F_drive does, so the sign changes of F_drive(t) are scanned on the dense output, brentq-refined, a sample exactly at zero counting as a cut; between cuts the E_drive state increment is the signed work); in - out = E_drive; out > 0 only when the drive brakes the engine (flag `drive_braking`) | 2.1279 GJ; 0 |
| electrical energy (`electrical_energy_J`, `_kWh`) | drive_work_in / eta (eta assumed); no regeneration credited for braking work (assumed, listed) | 4.2557 GJ = 1.182 MWh at eta = 0.5 |
| peak drive power (`drive_power_peak_W`, `peak_drive_power_W`, `drive_power_peak_t_s`) | max(0, max P) with P = F_drive sdot from the dense output (`losses.drive_power_extrema`), and its absolute time; at release when cold | 1.6322 GW at 2.607 s |
| braking power (`drive_power_min_W`) | min(0, min P): the power the drive absorbs when it brakes the engine; 0 when it only pushes | 0 |
| braking, facility (`braking_distance_m`, `facility_length_m`) | v_exit^2/(2 a_brake) = L a/a_brake; L + d_brake | 60.000 m; 160.000 m at 5 g0 |
| propellant on the track / before release (`propellant_burned_on_track_kg`, `_before_release_kg`, `dv_vac_equiv_before_release_mps`, `hold_propellant_burned_kg`) | integral mdot dt over the push / over hold plus push, and c ln(m0/m_release) | 0 (cold) |
| energy closure (`assist_energy_residual_rel`) | "Assist energy identity" | 1e-16 |
| geometry (`track_start_altitude_m`, `carriage_mass_kg`) | exit_altitude - L sin phi; m_c | -100 m; 0 |

Where a row lists two keys for one number (`drive_energy_J` and `assist_energy_J`,
`drive_power_peak_W` and `peak_drive_power_W`, `interface_force_peak_N` and
`peak_interface_force_N`), the first is the canonical metric and the second the
CLAUDE.md summary name, written as an alias with the same value
(`metrics.TRACK_METRIC_ALIASES`) so the summary rows and REQUIRED_METRICS can use the
CLAUDE.md wording; sweep_index.csv and the findings notes read the canonical key.

Force peaks and minima and the felt g are read off the sampled ASSIST rows of the
time series (every `sample_dt_s` plus both ends of every sub-phase, so the push
start, the kinks and the release are always among them). That is exact for the
prescribed acceleration, F_int and F_drive being monotone within a lit sub-phase, but
the drive power P = F_drive sdot is not monotone in general: with full thrust, P(t) =
(F_drive(0) - mdot (a + g) t) a t is a downward parabola with its vertex at t* =
F_drive(0)/(2 mdot (a + g)), which lies inside the push for a hot push near the
drive-limit threshold (or under a force-limited Phase 3 drive). The power extrema are
therefore taken from the dense output (`losses.drive_power_extrema`: P scanned on 256
points per sub-phase, every bracketed interior extremum refined by a bounded Brent
search to 1e-10 s, the sub-phase ends as candidates): for every shipped variant the
peak sits at release (t* = 61 s for `silo_hot_full` at 3 g0 against t_push = 2.6 s)
and equals F_drive(t_push) v_exit to 1e-15, while for a 0.6 g0 hot push (t* = 2.83 s
inside t_push = 5.83 s) it is the vertex value F_drive(0)^2 a/(4 mdot (a + g)) to
3e-14, 4e-5 above the sampled maximum (`test_silo.py`). A push in which the drive
only brakes has a zero positive peak and its braking peak in `drive_power_min_W`.
The `interface_tensile` flag is evaluated over the ASSIST rows only. Status
`drive_limit` means F_drive crossed zero inside the push (the prescribed
acceleration would need the drive to brake the engine): the run stops on the track at
the root (its time is logged as a `drive_limit` event), the ASSIST rows end at the
root, and no release happened, so every release item (`t_release_s`,
`speed_at_release_mps`, `alt_at_release_m`, `mass_at_release_kg`, the
`*_before_release` pair, `exit_speed_mps`, `push_time_s`, the braking and facility
lengths), every flight metric and every time counted from release
(`t_ign_rel_release_s_*`, `final_t_s`, `peak_felt_axial_g_t_s`) is n/a; what burned
is in `hold_propellant_burned_kg` and `propellant_burned_on_track_kg`, and the time
series' `t_rel_release_s` column counts from the push start.
`allow_negative_drive_force: true` drops the event and lets the drive pull back: the
bookkeeping then keeps `drive_energy_J` as the net work (the identity's E_drive, which
can be negative), reports the braking work separately in `drive_work_out_J` and the
braking power in `drive_power_min_W`, charges the electricity for the positive part
only (`electrical_energy_J` = `drive_work_in_J`/eta, no regeneration credited, stated
in the assumptions) and raises the `drive_braking` flag. A push exactly at the
threshold a = T/M0 - g_eff (F_drive = 0 at t0 and falling) has its `drive_limit`
event disarmed at t0 by the engine's rule and completes with status nominal; the
disarmed-event note and, since the drive then brakes for the whole push, the
`drive_braking` flag mark it. Under a prescribed
acceleration the felt g, the exit speed and the push
time are the same for every hot or cold variant of one (a, L): the silo's distinctive
load is the ~4 g0 on the full stack, since the flight peak (5.7 g0, unthrottled) is
common to every variant including the pad.

**Failed ignition through the silo** (`silo_failed`, status `impact`): exit at
76.707 m/s, apex 300.270 m at 7.8291 s after release, back at the mouth at 15.658 s at
76.707 m/s (mu/r^2; the constant-g values are v0^2/(2 g0) = 300.00 m, 7.822 s,
15.644 s), 88.56 m/s at the shaft bottom (v^2 = v_exit^2 + 2 g_eff L). The braked
carriage parks d_brake = 60.0 m above the mouth, in the fall-back path, and the vehicle
would meet it first, at 14.83 s after release at 68.6 m/s; the mouth and shaft-bottom
numbers are the obstacle-free values. The closed forms, the `failed_*` metrics and the
assumptions (drag-free coast, carriage in the path, no abort, no Coriolis) are the
"Failed-ignition coast" section.

**Assumptions the model adds to every summary** (`ConstantAccelAssist.assumptions`):
prescribed net acceleration (assumed; drive force unconstrained), carriage mass
(assumed), braking deceleration (assumed), drive efficiency (assumed), exhaust
impingement fraction (assumed; the system keeps (1 - f_imp) T), vented shaft (no air
column) and no friction, constant g_eff on the track with omega_p = 0 and Coriolis
neglected, infinite jerk at push start and release, vehicle clamped to the carriage
during any hold before the push. `sim.simulate` adds the track geometry line and the
carriage-braking and impingement notes.

## Hot start

An engine lit before release burns on the track. Two references: `release` (t_ign_s
counts from the track-end time, closed-form for this drive) and `push_start` (from
t = 0); with t_ign_abs < 0 the vehicle is clamped on the carriage from ignition to the
push start (the closed-form HOLD of the pad, the clamp carrying m g_eff sin phi, no
liftoff extension), and the push starts at t = 0 regardless of the thrust. Inside the
push the thrust kinks split the ASSIST phase; a ramp may straddle the release (its
second sub-phase then continues as the first BURN sub-phase in flight).

Under a prescribed acceleration the thrust buys no exit speed. It trades propellant
for drive energy and peak power, and it lowers the interface force:

| Variant (F9, 3 g0, 100 m, m_c = 0) | burned before release | F_int over the push | E_drive | P_peak | stage-1 burnout speed vs `silo_instant` |
|---|---|---|---|---|---|
| `silo_instant` (step at release; unphysical yardstick) | 0 | 21.28 MN | 2.128 GJ | 1.632 GW | 0 |
| `silo_cold` (0.5 s delay + 2 s ramp) | 0 | 21.28 MN | 2.128 GJ | 1.632 GW | -15.12 m/s (constant-g formula 14.70) |
| `silo_hot_ramp_on_track` (ramp lit 2 s before release) | 2,697 kg = 15.20 m/s of dv_vac | 21.28 -> 12.95 MN | 1.654 GJ | 0.993 GW | -5.61 m/s (constant-g 5.40) |
| `silo_hot_full` (full thrust for the whole push, f_imp = 0) | 9,731 kg = 55.19 m/s | 12.95 -> 12.67 MN | 1.276 GJ | 0.972 GW | -20.60 m/s (constant-g 19.85) |
| `silo_hot_full_impinged` (f_imp = 1) | 9,731 kg | 12.95 -> 12.67 MN | 2.099 GJ | 1.603 GW | -20.60 m/s |

The hot-full closed forms (E_drive = (a + g) a [M0 t_p^2/2 - mdot t_p^3/3] - T L =
2.099 - 0.823 GJ, W_thrust = T L = 0.823 GJ, P_peak(f_imp = 1)/P_cold =
(M0 - mdot t_p)/m0) are the "Assist energy identity" validation. The burnout-speed
cost is the straddle form of "Ignition-after-release loss": for `silo_hot_full`
Phi_pre = t_r/2 + t_p = 3.607 s, c ln(m0/(m0 - mdot Phi_pre)) = 55.19 m/s spent on the
track against g_eff Phi_pre = 35.35 m/s of gravity loss saved, 19.85 m/s under
constant g and 20.60 m/s integrated (0.75 m/s altitude term: the lighter, later-lit
vehicle flies lower). F_drive at the push start is M0 (a + g_eff) - T, which is
negative for the F9 (M0 = 539,873 kg after the hold's burn) below a = T/M0 - g_eff =
5.44 m/s^2 = 0.555 g0 net; with m_c = 0 and f_imp = 0 that is also where F_int turns
tensile (F_int = F_drive there), so a slow hot push ends with status `drive_limit`
at t0, while with f_imp = 1 the drive still pushes (F_drive = M (a + g_eff) > 0) and
the run completes with the `interface_tensile` flag. A ramp lit inside a 0.5 g0 push
crosses F_drive = 0 at the root of m(t)(a + g_eff) = T(t) (`test_silo.py` solves the
quadratic and matches the event time to 1e-9).

**Against the pad** (stage-1 burnout speed, sweep-optimized; the pad lit at -2 s so
that full thrust arrives at release, burning 2,697 kg on the pad): `silo_instant`
+84.8 m/s, `silo_hot_ramp_on_track` +79.2, `silo_cold` +69.6 (`silo_cold_lag` the
same to 0.01 m/s, tau = 1 s), `silo_hot_full` +64.2, `silo_sled_22t` +69.6 (the sled
changes F_drive, E and P only: 22.14 MN, 2.214 GJ, 1.698 GW). The CLAUDE.md check that
no assisted run beats its release speed unexplained is the identity line,

    delta(speed) = delta(exit speed) + delta(dv_vac) - delta(gravity, duration)
                   - delta(gravity, altitude) - delta(steering)

closed to 1e-12 m/s for every variant (`sim.run`, mu/r^2, g_ref = 9.79829 m/s^2):

| Variant vs `pad` | delta(speed) | = exit | + dv_vac | - gravity duration | - gravity altitude |
|---|---|---|---|---|---|
| `silo_instant` | +84.77 | +76.71 | +15.20 | +9.80 (1.0 s) | -2.66 |
| `silo_cold`, `silo_sled_22t` | +69.64 | +76.71 | +15.20 | +24.50 (2.5 s) | -2.23 |
| `silo_hot_ramp_on_track` | +79.16 | +76.71 | 0.00 | 0.00 | -2.45 |
| `silo_hot_full` | +64.17 | +76.71 | -39.99 | -25.55 (-2.607 s) | -1.91 |

The +15.20 m/s of dv_vac is c ln(542570/539873): what the pad spent while clamped,
which a variant that lights after release still has at release. The gravity-duration
term is g_ref times the longer burn measured from release: the pad's 1.0 s (half its
ramp) plus, for `silo_cold`, the 1.5 s of delay and half-ramp after release. Grouped
the constant-g way, `silo_cold` = +76.71 (exit) + 5.40 (hold-down credit: 15.20 - 9.80)
- 14.70 (ignition loss, 0.5 s + 2 s ramp, `ignition_loss_analytic_mps`) + 2.23
(altitude term: the silo run flies higher for the whole burn; the integrated ignition
loss against `silo_instant` is 15.12 m/s because 0.43 m/s of it is altitude), and
`silo_instant` = +76.71 + 5.40 + 2.66.

**Hold-down credit.** The 5.40 m/s (integrated: `pad_instant` - `pad` = +5.58 m/s,
0.17 of it altitude) is a property of the locked pad-baseline convention (the pad
ramps under hold-down and burns 2,697 kg before t = 0 to save 9.80 m/s of gravity
loss), not of the instant yardsticks alone: every silo variant that lights after
release (`silo_instant`, `silo_cold`, `silo_cold_lag`, `silo_sled_22t`) carries it in
full, because none of them burns anything while clamped, and the hot variants carry
what they do not burn before release (`silo_hot_ramp_on_track` burns the same 2,697 kg
on the carriage, so its delta dv_vac is 0). The concept-A delta therefore depends on
the pad convention: `silo_cold` is +69.64 m/s against this pad, +67.65 m/s against a
pad lit at t = 0 with its ramp and 1.29 s hold extension (1,122 kg = 6.31 m/s burned
clamped), and +64.07 m/s against `pad_instant`; exit speed less the integrated
ignition loss alone is 76.71 - 15.12 = 61.58 m/s. The summary prints the credit as
its own row per variant, `hold_down_credit_mps` = the baseline's
`preflight_burn_cost_mps` minus the variant's (the net figure: delta-v burned before
flight less the gravity loss those full-thrust seconds buy, 5.40 m/s for this pad),
under which each run's own `preflight_burn_cost_mps` is printed, rather than folding
it into delta dv_vac; see "Figures of merit in 1-D" for the definitions.

Finding, stated plainly: at fixed exit speed and felt g a hot start converts 2.7-9.7 t
of propellant into a 0.47-0.85 GJ drive-energy saving and a 39-40 % lower peak
power, at a cost of 5.6-20.6 m/s at burnout against the instant-lit silo; any
exit-speed benefit from on-track thrust needs a force-limited drive (Phase 3
`linear_motor`). The concept-A gain over the locked pad baseline is the 76.7 m/s of
exit speed, plus the 5.4 m/s hold-down credit of that baseline and a 2.2 m/s altitude
term, less the 5-25 m/s ignition loss after release (`silo_cold`: +69.6 m/s over the
pad, of which 61.6 m/s is exit speed less ignition loss).

## Failed-ignition coast

Modules: `phases/prelude.py` (`IgnitionSpec.fails`,
`flag_ignored_ignition_settings`), `phases/vertical.py` (`VerticalPlanner.ascend` and
`_fail_ignition`), `phases/trace.py` (`RunTrace.failed_stage` / `t_fail_s`), `metrics.py`
(`failed_ignition_metrics`, `last_burn_end_s`, `descent_crossing`,
`carriage_park_altitude_m`, `failed_ignition_flags`), `sim.py`
(`FAILED_IGNITION_ASSUMPTIONS`, `FAILED_IGNITION_TRACK_ASSUMPTIONS`). Test: `tests/test_failed_ignition.py`.

`fails: true` on a stage makes its `ThrustSchedule` identically zero (T_vac = 0, no
mass flow) for the whole run; the config requires `end: impact`, because the only
thing left to compute is where and how fast the vehicle comes down. The run is the
HOLD and ASSIST phases as configured (on a track the engine that fails is simply never
lit: no ignition event, no hold from a negative t_ign, nothing burned before release),
RELEASE, then the terminal coast at once: COAST (sigma = +1, ends at `apex`), FALL
(sigma = -1, ends at `impact` at the ground z = z_ground = 0, which is the silo mouth
in the plan's datum, `exit_altitude_m: 0`), status `impact`. The stage's scheduled
t_ign_s, reference and startup override play no part (there is no COAST_PRE_IGN and
`t_ign_rel_release_s_<stage>` is None); any of them set away from the defaults is
recorded as the run flag `ignition_failed: stage '<name>' has fails: true, so nothing
burns; ignored: ...` so a hot-start-then-fail config is not misread (as long as the
shipped `silo_failed` variant inherits the baseline's t_ign_s = -2 by dict merge it
carries that flag; setting t_ign_s: 0 in the variant would silence it, and the test
allows either). The `ignition_failed` event is logged at the start of the coast with the state
there, in the COAST (or FALL, for a vehicle already falling) phase. A failed *later*
stage does the same from the end of its staging coast, with the mass already staged.
A failed first stage on a pad never lifts off: the hold extends to t_max and the run
ends with status `no_liftoff` ("Hold-down bookkeeping"); `failed_stage` is still
reported and the coast metrics are n/a.

**Closed forms** (release at z = 0 at speed v0 = sqrt(2 a L), the loss identity's
|v_f| - |v_0| = -J_grav with J_vac = J_steer = J_bp = 0):

- Constant g (the analytic device, `ConstantGravity` through `sim.simulate` only):
  h = v0^2/(2 g), t_up = v0/g, back at the mouth at t_return = 2 v0/g with |v| = v0.
  With g = g0 in flight and on the track, h = a L/g0 = 3 L exactly for a 3 g0 push.
- mu/r^2 (the run model): a radial Kepler orbit ("Gravity" and `tests/test_coast.py`)
  with r_a = 1/(1/R_E - v0^2/(2 mu)), a = r_a/2, cos E0 = 1 - R_E/a at the surface,
  t_up = sqrt(a^3/mu) [pi - (E0 - sin E0)], t_return = 2 t_up by time symmetry and
  |v_impact| = v0 by energy conservation; the coast nets no gravity loss (J_grav =
  integral of g sigma dt cancels between the rise and the fall), so speed_end =
  speed_start. Near cos E0 = -1 the acos in that spelling loses ~2e-13 relative in
  double precision (its condition number is ~70 here); the same closed form written
  through delta = pi - E0 = 2 asin(sqrt(h/r_a)), h = r_a - R_E = h_c/(1 - h_c/R_E),
  h_c = v0^2/(2 g_s), g_s = mu/R_E^2, t_up = sqrt(a^3/mu) (delta + sin delta), is
  conditioned to rounding, and the test uses it.
- Shaft bottom (track runs only; derived, not integrated):
  v_bottom^2 = v_impact^2 + 2 g_eff (z_impact - z_track_start), the mirror of the push
  under the track's constant g_eff from the impact point (the ground) down to the
  track start; z_impact - z_track_start = L when the mouth is at the ground, and
  L - exit_altitude in general (the fall between the mouth and the ground is in
  v_impact already, so it is neither double-counted nor missed). The braked carriage
  is in the way, so this is the speed the vehicle *would* have at the track start, a
  bound for what a catch or a crush structure must absorb; no impact with the carriage
  is modelled.
- The carriage (track runs only): after release it brakes along the track tangent and
  parks d_brake = v_exit^2/(2 a_brake) beyond the exit ("Silo model", the run's own
  `braking_distance_m`), at z_carriage = z_exit + d_brake sin phi(L)
  (`metrics.carriage_park_altitude_m`), which for a vertical silo is d_brake above the
  mouth, in the fall-back path. It stops at t = v_exit/a_brake after release (1.56 s
  for the shipped case) while the vehicle, decelerating only at g, is already above
  it; on the way down the vehicle meets it first, before the mouth. Constant g: at
  t_up + sqrt(2 (h - d_brake)/g) at |v| = sqrt(v0^2 - 2 g d_brake); mu/r^2: the time
  from the apex to a drop x below it is sqrt(a^3/mu) (delta + sin delta) with delta =
  2 asin(sqrt(x/r_a)) (the t_up form with x = h), and |v|^2 = v0^2 - 2 mu d_brake /
  (R_E (R_E + d_brake)) by energy. The code reads both off the FALL phase's dense
  output (`metrics.descent_crossing` at z_carriage); it is reported so the mouth and
  shaft-bottom numbers are not mistaken for the first thing the vehicle hits.

**Reported** (`failed_*` metrics, present only when a stage failed; times relative to
release): `failed_stage`; `failed_apex_alt_m` and `failed_t_apex_s`, the highest apex
of the unpowered flight that ends in the failure, i.e. after the last burnout before
it (`metrics.last_burn_end_s`; release for a first stage), so an apex reached inside a
long staging coast before a later stage fails still counts (None when the vehicle was
already falling at that burnout); on a track, `failed_carriage_alt_m`,
`failed_t_carriage_s` and `failed_speed_at_carriage_mps`, where the braked carriage
parks and when and how fast the falling vehicle first comes down to it (None when
the apex is below it; all three None on a pad); `failed_t_return_s`, when the vehicle is back down
at its release altitude (the mouth, or the pad): the first downward crossing of
z_release after that burn, found by brentq on the FALL phase's dense output
(`metrics.descent_crossing_time_s`), which is the impact event itself when the mouth is at
the ground and None when the ground is above the mouth (a sunken exit: in the 1-D
model the vehicle rises through z = 0 unhindered, a rising phase listing no impact,
and "hits the ground" there on the way back, so that case is a bookkeeping check of
the altitude split, not a consistent geometry); `failed_impact_speed_mps`, |v| at
the impact (the ground); and,
on a track, `failed_speed_at_shaft_bottom_mps` from the formula above. With the mouth
at the ground they duplicate the generic `apex_*` / `impact_*` items under their own
names so a summary can print the failed-ignition line without deciding which apex it
means; with a track exit away from the ground (`exit_altitude_m` is not validated
against 0 in Phase 1) the run flag `failed ignition: the track exit (mouth) is at z =
...` says which altitude each item refers to (`metrics.failed_ignition_flags`; it prints
the planner's ground altitude, not the impact root's 1e-13 m residue).

**Numbers** (F9, 3 g0, L = 100 m, v0 = 76.70717 m/s; `sim.run`, mu/r^2, rtol 1e-10):
apex 300.27024 m at 7.8291233 s after release, the parked carriage (d_brake =
60.000 m above the mouth, a_brake = 5 g0) met at 14.832503 s at 68.61637 m/s, back at
the mouth at 15.6582467 s at 76.70717 m/s, 88.56437 m/s at the shaft bottom (g_eff =
9.7982855 m/s^2). Against the
closed forms in the conditioned (asin) spelling: apex -2.9e-9 m (the test allows
1e-5 m; "Gravity" on what sets that residual), t_up 5.8e-15 relative, t_return -5.4e-12 relative, |v_impact| -1.1e-11
relative, J_grav 8.3e-10 m/s, identity residual -2.8e-14 m/s, the carriage time
-2.9e-12 and speed -6.1e-12 relative. (Against the acos spelling t_up reads -2.4e-13
relative: that is the closed form's own roundoff, not the integrator's.) Under g0
(constant g in flight and on the track): 300.00000 m, 7.8219545 s, the carriage at
14.8181234 s at 68.60898 m/s, 15.6439091 s, 88.57381 m/s at the bottom. The README's
"~300 m, ~7.8 s" are these numbers rounded. Of the 0.27 m the mu/r^2 apex gains over
the g0 one, 0.256 m is g_eff = 9.79829 m/s^2 against g0 = 9.80665 at the surface
(v0^2/(2 g_eff) = 300.256 m) and 0.014 m (h^2/R_E) is the weakening of gravity over the
climb.

**Assumptions added to a failed run whose coast ran** (`FAILED_IGNITION_ASSUMPTIONS`,
plus the carriage lines on a track; a pad `no_liftoff` with `fails: true` never
coasted and gets none of them): the fall-back coast is drag-free (the strings stay generic and
point here for the order of magnitude: at 77 m/s the drag on the F9 class is about
0.4 % of its weight, q = 3.6 kPa on ~10.5 m^2 at C_D ~ 0.5 against 5.3 MN, so the
apex and the return time are good to ~1 %; another vehicle needs its own figure); the
braked carriage parks its braking distance beyond the exit, in the fall-back path, and
the vehicle would meet it there first unless it is withdrawn in time (~14.8 s after
release for the shipped case), no impact with it is modelled, and the return, the
impact and the shaft-bottom speed are the obstacle-free values; the shaft-bottom speed
is derived from the impact speed and the fall from the ground to the track start, not
integrated; no
abort is modelled (a tilted exit that carries the vehicle clear of the mouth is the
planar branch of Phase 2/3); Coriolis drift during the coast is neglected (omega_p =
0), so the vehicle comes straight back down the shaft.

Validation (`tests/test_failed_ignition.py`, every expected value a closed form in the
test): the shipped `silo_failed` variant, resolved from the experiment YAML, through
`sim.run` (apex r_a - R_E to 1e-5 m, t_up from the Kepler form and t_return = 2 t_up
to 1e-9 relative, |v_impact| = v_exit and the shaft-bottom speed to 1e-9 relative,
status `impact`, exactly one apex and one impact event, one `ignition_failed`, no
`ignition`, T_vac = 0 and the mass constant on every row, |J_grav| < 1e-6 m/s, the
carriage at d_brake = braking_distance_m, met at t_up + the Kepler fall of h - d_brake
at the energy speed, both to 1e-9 relative, and no flag other than the
ignored-settings one); the same through `sim.simulate` with `ConstantGravity(g0)` and
g_eff = g0 (apex 3 L, t_up = v0/g0, t_return = 2 v0/g0, the carriage at v0/g0 +
sqrt(2 (h - d)/g0) at sqrt(v0^2 - 2 g0 d), to 1e-9 relative); the mouth 50 m above
the ground (return at 2 v0/g at the mouth, impact at sqrt(v0^2 + 2 g 50) at 2 v0/g +
(v_impact - v0)/g, shaft bottom sqrt(v0^2 + 2 g L) as before, the carriage at 50 +
d_brake, the flag naming z = 50 m and the ground z = 0 m, and the gravity loss
v0 - v_impact < 0, which pins the sign of the integrand) and 30 m below it (the
bookkeeping check: return None, impact at sqrt(v0^2 - 2 g 30), shaft bottom
sqrt(v_impact^2 + 2 g 130) = sqrt(v0^2 + 2 g L)); `fails: true` with t_ign_s = -2
from push_start and a startup override (nothing burns, no hold, the same coast, the
ignored settings named in the one flag); a failed first stage on the pad still ends
`no_liftoff` with every coast metric None and no failed-ignition assumption; a falling
coast starting on the ground (a pad start sinking at 5 m/s: impact at t = 0 at 5 m/s;
one rising at 1 mm/s: apex 51 nm at v0/g, then a zero-length FALL ended by impact
there; neither runs to t_max); a failed *second* stage on the two-stage toy under
constant g (apex z_bo + v_bo^2/(2 g) and impact at sqrt(v_bo^2 + 2 g z_bo) at t_bo +
(v_bo + v_impact)/g from the vertical-burn closed forms of the first stage, the
`ignition_failed` event at the burnout with the staged mass, the gravity loss g t_b +
(v_bo - v_impact) with the coast's share negative, the carriage items None on a pad);
and the same with a staging coast of 1.2 v_bo/g, so the apex sits in COAST_STAGING
before the failure in FALL and the `failed_*` items still report it.

## Figures of merit in 1-D

Modules: `compare.py` (`compare`, `identity_budget`, `payload_equiv_kg`,
`run_sensitivity`), `metrics.py` (`ignition_timing_metrics`), `summary.py`
(`variants_table`, `checks_section`), `results_io.py` (`sweep_index_frame`), `plots.py`
(`write_plots`). Without an orbit there is no payload capacity and
no residual propellant in Phase 1 (a residual at a fixed altitude misleads: every variant
burns the same propellant in the same time), so the figure of merit of a variant is
the change of the stage-1 burnout state against the pad baseline, decomposed by the
loss identity so that every m/s is attributed, plus two yardsticks stated as such.

**Identity line.** For each run `identity_budget` gives the loss budget at the run's
stage-1 burnout (the sum of the per-phase increments over the ascent phases up to and
including the BURN ended by the propellant event, whatever the run's `end`), or at
its end when it has no stage-1 burnout (a failed ignition ends at the impact). Every
such budget closes exactly, so the difference of two of them closes too:

    d(speed) = d(speed at release) + d(J_vac) - d(J_grav,duration) - d(J_grav,altitude)
               - d(drag) - d(J_steer) - d(J_bp) + residual

with `speed at release` the budget's start speed (0 on a pad, also when the hold
extends past t = 0; the exit speed on a track). `compare` reports the seven terms as
`d_*_mps`, the point (`identity_point`: `stage1_burnout`, or `end vs stage1_burnout`
when the variant never burned out) and `identity_line_residual_mps`; the summary's
Checks section prints the line for every variant, and marks a line whose point is not
a stage-1 burnout on both sides (`silo_failed`: its impact against the pad's burnout)
as "not a figure of merit", since that delta speed is the difference of two exact
budgets at unlike points, not a result. Measured on the shipped experiment:
every residual is below 3e-12 m/s (CLAUDE.md allows 0.01; a residual above that is
the test's failure). The `d_speed_release_mps` term is why a silo variant gains its
exit speed one for one; `d_dv_vac_mps` is minus the difference of the delta-v burned
before flight (the pad's 15.20 m/s clamp burn; `silo_hot_full`'s 55.19 m/s, hence
d_dv_vac = -39.99 m/s), the duration term g_ref times the difference of the flight
times, the altitude term the "flew higher" effect (about -2.2 m/s for a 100 m silo,
i.e. a 2.2 m/s gain).

**Hold-down credit and ignition loss (constant-g yardsticks).** Each run carries
`preflight_burn_cost_mps` = c ln(m0/m_flight) - g_eff (m0 - m_flight)/mdot_full: the
delta-v spent on the propellant burned before the free flight (on the pad, on the
carriage, on the track) less the gravity loss those full-thrust seconds would have
cost in flight. It is Phi_pre-exact for a step or a ramp (the pad baseline lit at -2 s
with a 2 s ramp: 15.20 - 9.80 = 5.40 m/s) and handles an extended hold by its actual
burn. `compare` reports `hold_down_credit_mps` = baseline cost - variant cost: +5.40
for every variant that burns nothing before flight, 0 for `silo_hot_ramp_on_track`
(the same 2,697 kg, burned on the carriage), -14.45 for `silo_hot_full` (19.85 - 5.40).
`ignition_loss_formula_mps` is `losses.ignition_loss_analytic_mps` with g_ref = g_eff,
the run's stage-1 ignition time relative to release, its startup shape, the liftoff
mass and the stage's burn time (so the lag form is exact): the pad's 5.40, `silo_cold`'s
14.70, `silo_hot_full`'s 19.85 (all "Ignition-after-release loss" numbers); it equals
`preflight_burn_cost_mps` plus g_eff times the post-release deficit.
`ignition_loss_integrated_mps` is the `silo_instant` stage-1 burnout speed minus the
variant's, defined only when both flew from the same release state (speed and altitude
within 1e-6), so a pad reads n/a: `silo_cold` 15.12 (0.43 m/s of it altitude),
`silo_hot_ramp_on_track` 5.61, `silo_hot_full` 20.60. The two are printed side by
side; their difference is the altitude effect the constant-g formula cannot see.

**The CLAUDE.md check.** A variant's gain is explained when it does not exceed its
release speed plus the hold-down credit plus the altitude term:
`unexplained_gain_mps` = d(speed) - (d(speed at release) + hold_down_credit -
d(J_grav,altitude)). For the same vehicle, d(J_vac) - d(J_grav,duration) =
-(formula_variant - formula_baseline) exactly (mass bookkeeping fixes the burn time
after the flight start, gravity model or not), so the excess is minus the post-release
part of the ignition loss, minus the steering and back-pressure deltas: never positive
beyond rounding. Measured: `silo_instant` +4e-8 m/s, `silo_cold` -14.70, `silo_hot_full`
-5e-8 m/s. An excess above 0.01 m/s names the variant in the Checks section as a bug.
The check is defined only at a stage-1 burnout on both sides (`identity_point` =
`stage1_burnout`): a run without one (`silo_failed`, whose line is written at its
impact) gets `unexplained_gain_mps` = None and is listed as "not checkable", because
the credit and the altitude term of an impact-to-burnout difference mean nothing.
A vehicle perturbation (sensitivity) breaks the equality, which is why the sensitivity
table compares against a baseline carrying the same perturbation as well.

The same rule in kg (CLAUDE.md names "the README's ideal screening estimate for its
release speed"): `compare` also reports `ideal_screening_payload_at_release_speed_kg`
= `payload_gain_kg(vehicle, speed at release)`, the README yardstick itself (0 for a
pad, 684.8 kg at 76.71 m/s for the F9 class), and the Checks section names every
variant whose payload equivalent exceeds it: `silo_instant` (757.8 kg against 684.8)
and `pad_instant` (49.1 kg against 0) exceed it by exactly the hold-down credit and
the altitude term converted through the same equation (the m/s beyond the release
speed on their bound lines); `silo_hot_ramp_on_track` by the altitude term alone
(its credit is 0); the cold and hot starts stay below it by their post-release
ignition loss. Nothing else may put a variant above the yardstick.

**Ideal-screening payload equivalent.** `ideal_screening_payload_equiv_kg` is
`payload_equiv_kg(vehicle, d(stage-1 burnout speed))`: the payload change at which the
vehicle's ideal rocket-equation delta-v (`vehicle.ideal_dv_mps`, the loss-averaged
screening Isp of the vehicle file) moves by exactly minus that speed delta
(`payload_gain_kg` for a gain; brentq on [0, payload] for a loss, None when even an
empty bay cannot recover it). Labelled in every summary as "ideal rocket equation at
fixed losses; not a payload result": it is the README's screening yardstick applied
to the integrated speed delta (`silo_cold` +69.64 m/s -> 621 kg; the README's 687 kg
at 77 m/s is the same yardstick applied to the exit speed alone, before any ignition
loss), and it inherits the screening Isp's assumptions, which is why the sensitivity
block perturbs `vehicle.screening.stage_isp_eff_s.0` (+/-10 % moves the 621 kg to
613/629 kg with the flight unchanged).

**Sensitivity.** `run_sensitivity` runs every case of the experiment's sensitivity
block (each a resolved run with the parameter moved by +/- the fraction through
`config.apply_overrides`, in memory) and compares it against the unchanged baseline
and, for a `vehicle.` parameter, against the baseline re-run with the same vehicle
perturbation (one re-run per perturbation). Both deltas are printed and labelled: the
first is the sensitivity of the headline number to the vehicle (a 10 % lighter stage 1
puts `silo_cold` 109 m/s above the nominal pad, 39 m/s more than nominal), the second
the sensitivity of the concept's benefit (the same perturbation on both sides leaves
+69.7 m/s, 0.07 m/s more than nominal). A run parameter such as `assist.drive_efficiency` leaves
the baseline alone, so its second column is marked "= unchanged". The payload
equivalent of both deltas is tabulated: the one of the same-perturbation delta is the
concept's benefit in kg (`silo_cold`: 613-629 kg across its eight cases against 621
nominal; `silo_hot_full`: 564-579 kg against 572), the one of the unchanged delta is
mostly the vehicle change (+3085 kg for +10 % Isp on `silo_cold`) and is labelled as
such. The
perturbed value is printed in SI (`value_si` with `value_si_unit`, converted from the
key's YAML suffix through units.py by `compare.si_value`: `_t` to kg, `_kN` to N, `_deg`
to rad, `_g` to m/s^2; a key without a unit suffix is dimensionless) and, beside it,
as it stands in the config (`value_yaml_units`: t, s, a fraction), the one column of
the table and key of the record that is not in SI, kept so the case can be
reproduced from the file. One C_D row per run that has cases reads "n/a: no drag in
Phase 1". When no case ran, the section prints why instead of a table: none declared,
skipped with `--no-sensitivity`, or a sweep point (sweeps run no sensitivity case).

**Files.** summary.md holds the per-variant table (one row per quantity, one column
per run, the baseline first: the CLAUDE.md list in its order, opened by how each
column ignites (stage-1 t_ign relative to release, the effective startup kind and its
t_ramp or tau, from `ignition_timing_metrics`: `startup_kind_<stage>`,
`t_startup_s_<stage>`), with the identity decomposition, the two payload yardsticks,
the loads with their times and masses (the run-wide, track and flight peaks of the
felt g each with the time and the mass there; the hold-down force m g_eff - T with
its sign convention, negative = the clamps in tension), the energies and powers, the
facility length and the failed-ignition items; a pad, which has no track, reads 0 for
every assist item, one convention for the whole set; the before-flight burn pair is
printed only when some run's hold extended past t = 0, so that it differs from the
before-release pair), followed by a note naming the runs whose stage-1 startup is a
`step` (instant full thrust: `pad_instant`, `silo_instant`; a yardstick that isolates
the ignition-timing loss, which no engine achieves, so those columns bound the
others and are not designs; the sweep summary carries the same note when a point is
one), the sensitivity table, the flags, the attributed assumptions (the run model's
gravity is one line: mu/r^2 with the value of mu, InverseSquareGravity, ConstantGravity
for tests only) and the Checks section. Summary cells print a magnitude below 1e-9 in
the quantity's unit as 0 (the 6e-17 g0 track-normal load of a vertical track is
cos(pi/2) roundoff, a -2.5e-13 m/s credit is an exact 0) and a bound line's excess
below 1e-6 m/s as "0 (|excess| < 1e-06)"; metrics.json keeps every raw value.
metrics.json carries every run's metrics, every comparison and every
sensitivity case (with both comparisons). sweep_index.csv carries, per point, the axis
values, the run directory, exit speed, stage-1 burnout speed and its delta, the
formula ignition loss, drive energy, peak drive power, peak felt g on the track,
facility length and status; a sweep point's comparison is computed once and shared by
its metrics.json and the index. Plots per run: altitude, speed, mass and thrust (each
on its own y axis: kg and N never share a scale), felt g against the time since
release, and on a track the drive and interface forces and the drive power.

## Convergence

Test: `tests/test_convergence.py`. CLAUDE.md requires that tightening the tolerances
10x changes payload and margins by less than 0.1 %. Phase 1 has no orbit, so no
payload capacity and no propellant margin exist yet; the test stands in for the Phase
2 payload/margin convergence test with the 1-D figures of merit above. The shipped
`pad`, `silo_cold`, `silo_cold_lag`, `silo_hot_full` and `silo_failed` runs of
`experiments/silo_screening_1d.yaml` go through `sim.run` (mu/r^2) twice: at the
experiment's own settings (rtol 1e-10, ramp_steps 10, lag_steps_per_tau 4,
push_steps 50, sample_dt 0.05 s: 3,024 time-series rows for `silo_cold`, 371 for
`silo_failed`) and at rtol 1e-11 with every max_step cap halved (20, 8, 100) and
sample_dt 0.01 s (15,088 and 1,832 rows). The lag run exercises the lag cap, the
hot-full run is the one where every assist-energy term (drive work, thrust work,
mass-flow term, dense-output power extrema) is non-zero, and the failed run covers
the apex and impact events and the fall-back metrics.

Compared, at 1e-8 relative (100x the measured agreement, so that a genuinely looser
solver fails; the 0.1 % rule is asserted beside it and the plan's 1e-6 bound is
implied): the final time and speed, dv_vac, the gravity loss and its duration and
altitude parts, speed_start and speed_end, the flight peak felt g and the release
state for every run; the stage-1 burnout time, speed, mass and altitude for the runs
that end there; for the silo runs the exit speed, push time, drive energy and work
in, electrical energy, peak drive power and its time, peak and minimum interface
force, peak track felt g, facility length, the propellant burned before release
with its dv_vac equivalent and the preflight burn cost; for the failed run the apex
altitude and time, the impact time and speed, the return time, the carriage
encounter and the shaft-bottom speed. The burnout-speed delta against the pad and
its identity terms (each variant against the pad run at the same settings) are
asserted within 1e-5 m/s absolute and 1e-8 relative as two separate assertions
(neither bound stands in for the other); the payload equivalent of that delta at
1e-8 relative; and every event's time (1e-9 s floor at t = 0), mass and altitude
(`ATOL_M` allowance). Altitudes carry the `ATOL_M` allowance for the reason given
under "Gravity"; the loss quadratures carry an `ATOL_MPS` (1e-9 m/s) allowance
because the failed run's gravity loss integrates to ~1e-9 m/s over its symmetric
coast, where a relative test is moot.

Measured, worst case over the five runs: the largest relative change of any
compared scalar is 1.3e-10 (`gravity_loss_alt_mps` of the pad, 1.9e-9 m/s); the
burnout speed moves by up to 5.7e-8 m/s (`silo_hot_full`, 2.2e-11 relative; 3.7e-8
m/s for `silo_cold`); the delta against the pad by 1.9e-8 m/s (`silo_cold`),
1.8e-8 m/s (`silo_cold_lag`) and 4.0e-8 m/s (`silo_hot_full`); the payload
equivalent by up to 3.6e-7 kg; event times by up to 1.4e-11 s (the failed run's
impact; 5.8e-12 s for `silo_cold_lag`, 5.7e-14 s for the pad, 9e-16 s for
`silo_cold`); event masses by up to 5.8e-9 kg (`silo_hot_full`; 1.2e-10 kg for
`silo_cold`); event altitudes by up to 1.0e-5 m at the pad's 125 km burnout (8e-11
relative; 8.4e-6 m at the 135 km burnout of `silo_cold`, 2.1e-9 m at the failed
run's 300 m apex); the drive energy by 1.4e-5 J of 1.276 GJ (`silo_hot_full`) and
the failed run's return time by 1.4e-11 s and its impact speed by 1.4e-10 m/s. The
identity residual stays below 1e-6 m/s and the assist energy residual below 1e-9 at
both settings. Nothing among the 1-D figures of merit is tolerance-limited: the
burnout altitudes move by 1e-5 m (1e-10 relative), of the same order as the apex
error discussed under "Gravity", and the `ATOL_M` allowance only keeps altitudes at
z = 0 (push start, release, impact) comparable.

For reference, the assertion is calibrated so that a solver 1e4x looser than the
nominal one (rtol 1e-6, ramp_steps 2, lag_steps_per_tau 1, push_steps 5, sample_dt
0.5 s) still agrees with it to 1e-7 relative and 2.5e-4 m/s on the delta, inside
the plan's 1e-6 / 1e-3 m/s bounds; the asserted 1e-8 / 1e-5 m/s bounds are what
separate the nominal settings from that.

## Experiment schema (planar)

Module: `config.py` (build step 19). Test: `tests/test_config_planar.py`. The schema
carries no physics; it fixes what every run of an experiment shares, so that a delta
between two runs is a delta of the assist and nothing else (CLAUDE.md: "all of them
share guidance settings and optimizer budget"; decision 4 reads this as the shared
parametrisation, sweep grid and optimizer budget, with the free guidance parameters
sweep-optimized per run).

**Model selector.** `dynamics:` is declared once, at experiment level: `vertical_1d`
(the default: the Phase 1 model, unchanged) or `planar_2d`. A delta between models is
meaningless, so no run may change it.

**Shared blocks.** `dynamics`, `site`, `guidance`, `search`, `target_orbit` and
`checks` live at experiment level. `resolve_experiment` injects the declared ones into
every run dict (`shared_run_blocks`, `inject_shared`): `dynamics` and `site` as run
keys, the other four under `planar` (`RunConfig.planar: PlanarShared`), placed right
after `name`. They are refused, with the path named, when a baseline declares them
itself, when a variant sets them, as sweep axes, as sensitivity parameters and as bound
overrides (`SHARED_PATH_ROOTS`: the six names plus `planar`). The one exception is a
paired sweep of a `guidance_study` (below). Nothing is injected when nothing is
declared, so a Phase 1 experiment resolves to exactly the run dicts it had before
(`test_phase1_resolved_run_dicts_are_byte_identical` compares every run, sweep-point
and sensitivity run dict of both 1-D golden sets, key order included). A Phase 1
baseline may still carry its own `site` (the Phase 1 form) when the experiment
declares none; variants may no longer move it.

| Block | Fields (units at the boundary; SI and radians through properties) |
|---|---|
| `site` | `latitude_deg`, `azimuth_deg`, `include_rotation`. On planar_2d all three are required (`PlanarSiteConfig`), so rotation is always a stated choice; omega_p = omega_E cos(lat) sin(az), the orbit-normal component of Earth rotation (at az 90 the site velocity and the inclination are exact; the air's out-of-plane velocity omega_E sin(lat) r sin(theta) is neglected, so the model is exact only for an equatorial east launch). On vertical_1d rotation raises ("a Phase 2 feature: it needs dynamics: planar_2d"), also for a `PlanarSiteConfig` instance handed to a vertical_1d `RunConfig`; the 1-D model keeps omega_p = 0 |
| `target_orbit` | `kind: circular` (only), `altitude_km`; `radius_m` = R_E + altitude (spherical Earth) |
| `guidance` | `kick: {v_kick_mps, mode: hold_to_alignment, max_duration_s, deadline_s}`, `stage1: gravity_turn`, `stage2: {law: linear_tangent, frame: local_horizontal, cutoff: energy}` |
| `search` | `figure_of_merit` (payload, residual, none); gamma* grid `[start, stop, step]` deg (a whole number of steps, inside (-90, 90) deg, as is a fixed gamma*), refine half-width, xatol and maxiter, false-root guard `gamma_root_tol_deg` (amendment 7); delta bracket (inside (0, 90) deg), step and xtol; payload half-bracket (t), expansions, back-offs, xtol, brentq rtol (>= 4 eps); final xtol and bracket; `search_rtol`, `search_atol_scale` (>= 1), `final_rtol`; `penalty: {base_kg, per_deg_kg}`; `ltg:` acceptance, residual scales, finite-difference steps, iteration and halving limits, rungs per grid point, guess-ladder angles, direct-root pitch window (every LTG angle inside (-90, 90) deg, where tan p is finite), `tau_max_factor`, `mass_floor_factor`. `budget_id()` is the sha256 of its canonical JSON |
| `checks` | closure tolerance; the 2-D loss-identity tolerance `identity_tol_mps` (1e-5 m/s) and the insertion eccentricity limit `insertion_e_max` (1e-6), the per-run acceptance numbers of plan section 11; M2 and M3 ratio bounds and the M3 floor; the M4 share; the M5 anchor margin; the search-vs-final flag; max-Q scan points and xatol; `unconstrained_kick_mps`, `vk_margin_kg` (amendment 13); `convergence:` the amendment-3 rules (relative tolerance, absolute floors for loss terms and margins, gamma* resolution, tightening factor, max_step factor). The tightening divides the search and final rtol, atol, the LTG acceptance thresholds and the delta, payload and gamma xtols by the factor; the finite-difference steps stay |

Every threshold of plan section 7, the per-run acceptance numbers of section 11
(loss identity, eccentricity; the radius and residual-propellant acceptance are
`ltg.accept_r_m` and `final_payload_xtol_kg`) and amendments 3, 7 and 13 is a field
here, and the shipped experiments write every field out (a test checks the key sets),
so no pre-registered number hides in a default. A later step that needs a threshold
not listed adds a field and pre-registers it before step 26. The pydantic defaults
equal the plan's values. `guidance.kick.deadline_s` = 60 s after stage-1 ignition is
this step's choice for the amendment-13 threshold the plan names without a value. Its
basis is the gate fork the trigger study flies (569.1 t at liftoff with payload, 9 x
845.2 kN sea-level thrust, held down through the 2 s ramp, g_ref 9.7720917 m/s^2): an
independent vertical-rise estimate reaches 50 m/s about 12.3 s and 120 m/s about 26 s
after release (about 14.3 s and 28 s after ignition): 12.27 s and 26.02 s with drag,
back-pressure, mu/r^2 and rotation; 12.26 s and 25.93 s with drag alone removed; and
12.29 s and 26.23 s in a cruder estimate without drag but with sea-level thrust and
g_ref held constant (the constant thrust, not the missing drag, makes it slower).
Under every shipped perturbation and fork the 120 m/s time stays at or below about
28.5 s after ignition. The deadline therefore leaves
about 2.1x margin at the trigger study's highest v_k (120 m/s); logged for the
decisions log. Re-measured with the planar planner (build step 21, the pad lit at
-2 s, kick trigger time after ignition for v_k = 30 / 50 / 80 / 120 m/s): gate fork
9.667 / 14.268 / 20.558 / 28.025 s, matching the estimate; across the three forks with
stage-1 dry mass +10 %, stage-1 Isp -10 %, cd_scale +10 % or A_ref 21.24 m^2 the
120 m/s time is at most 28.806 s (set B, dry mass +10 %), slightly above the 28.5 s
quoted above, so the margin at v_k = 120 m/s is 2.08x. Two rules keep the fixed-guidance mode honest:
`figure_of_merit: none` requires `fixed_gamma_star_deg`, `fixed_ltg_a` and
`fixed_ltg_b_per_s`, and they are refused with any other figure of merit.

**Run-level rules** (`RunConfig`). `end` gains `insertion`, allowed only on planar_2d.
A planar_2d run needs an explicit site, the planar block (guidance, search, checks),
an end in (`stage1_burnout`, `insertion`, `apex`, `impact`) (`all_burnout` is
deferred), `integrator.rtol == search.final_rtol` (an integrator setting, see
"Integrator"), `end: insertion` for a searched figure of merit, and `target_orbit`
when it inserts or searches. With the vehicle (`resolve_run`): an aero block, two
stages (one guidance law each), and no heating-rule refusal (that refusal is
vertical_1d only, "Atmosphere, drag and back-pressure in flight"). On both models a
later stage must ignite at `t_ign_s >= 0` after its staging coast (refused at resolve
time; the 1-D planner also refuses it at run time), so no variant can shorten the
pre-registered staging coast by a negative stage-2 ignition. Every per-run integrator
setting, `sample_dt_s` included, is locked on planar_2d ("Integrator").
`integrator.method` (DOP853 or RK45, default DOP853) is new for both models.

**Search skip (amendment 4).** A planar run with `end: impact` (which every failed
ignition already requires) skips the search: `RunConfig.search_skip_reason` names why
and `RunConfig.figure_of_merit` is `none` while the shared `search` block itself is
untouched. A skipped run whose stage 1 lights would need guidance the search did not
produce, so it is refused unless the shared search flies fixed guidance. The shipped
`silo_failed` never lights.

**Paired sweeps.** `sweeps[].paired: true` is allowed only on planar_2d (a
vertical_1d experiment is refused with that rule), only with `guidance.*` axes
(applied under `planar.guidance` in the run dict; these need `label: guidance_study`)
and `vehicle.*` axes, and not on the baseline itself. Each point also resolves the
baseline re-run with the same overrides (`SweepPoint.paired_baseline`, named
`run_NNNN__<baseline>`), so a silo at v_k = 30 m/s is compared with a pad at v_k =
30 m/s, never at 50. On planar_2d a sweep with a `vehicle.*` axis must be paired: an
unpaired one would compare, say, a silo with half the drag area against the nominal
pad and book the vehicle change as assist gain. The 1-D model keeps its unpaired
vehicle sweeps (Phase 1 unchanged).

**Calibration cases.** `cases:` is allowed only with `label: calibration`. A case is
an independent run of the baseline, never compared: another vehicle file (`vehicle:`,
read through the caller's `load_vehicle`; config.py does no file I/O and refuses such
a case without a loader), a partial `site` or `target_orbit` merged over the
experiment's, and overrides on `vehicle.` paths only. Case names must not collide with
run or bound names. Cases are not part of `ResolvedExperiment.runs`.

**Bounds (amendment 6).** `bounds:` is a list of `{name, of, overrides,
paired_baseline: true}`. Each run in `of` (never the baseline) is re-run with the
overrides as `<of>__<name>`, and the baseline is re-run with the same overrides as
`<baseline>__<name>`, its pair, as in a sensitivity case with a perturbed baseline.
silo_screening_2d carries the fairing-area aero bound: silo_cold and the pad at
A_ref = 21.24 m^2.

**Sensitivity paths (amendment 5).** Vehicle parameters use the resolver's prefix:
`vehicle.stages.stage1.dry_mass_t`, `vehicle.stages.stage1.engine.isp_vac_s`,
`vehicle.stages.stage2.engine.isp_vac_s`, `vehicle.aero.cd_scale` (list items by
name). A value moved past a model limit (a drive efficiency above 1) is refused at
resolve time. The schema resolves only the perturbed run (`SensitivityCase.run`), not
its same-perturbation baseline: `run_sensitivity` (as in 1-D) re-runs the baseline under
each trajectory-changing `vehicle.` perturbation; an energy-only `assist.*` parameter
leaves the baseline alone (a pad has no drive, so perturbing it would raise
ConfigPathError), and the yardstick `vehicle.screening.*` cases and their baselines
reuse the nominal trajectories without flying (the `trajectory_key` memo, "Reporting
definitions (planar)"). A bound, by contrast, carries its paired baseline already
(`BoundCase.baseline`).

**The shipped Phase 2 experiments** (amendment 1: created with the schema, before any
planar run). All four declare identical shared blocks (a test compares them key for
key; one `budget_id`): planar_2d; 28.5 deg, azimuth 90, rotation on; 200 km circular;
v_k 50 m/s; the gamma* grid 8-36 deg step 2; search rtol 1e-8, final 1e-10.

| File | Label | Vehicle | Runs |
|---|---|---|---|
| `calibration_f9_2d.yaml` | calibration | gate fork (set C) | baseline pad (sample 0.1 s); cases readme_loads (set A), recorded_scope (set B), aref_fairing (A_ref 21.24), alt_185, alt_250, alt_300, no_rotation; sensitivity of the pad on stage-1 dry mass, both Isp_vac and cd_scale (+/-10 %) |
| `silo_screening_2d.yaml` | none | gate fork | the nine 1-D variants (silo_failed skips the search); the 1-D sweeps (accel x stroke, 12; t_ign x t_ramp, 9; lag tau, 3: amendment 12; the pad keeps its 2 s ramp at every point, so the t_ramp and lag axes carry an engine-startup change the pad does not get, which favours the silo at short ramps: only t_ramp = 2 s is like for like, and the report must say so, as in RQ2-1d); sensitivity of silo_cold and silo_hot_full on stage-1 dry mass, both Isp_vac, cd_scale, screening Isp and drive efficiency; the aero bound |
| `silo_bridge_2d_readme.yaml` | none | README-loads fork (set A) | pad, pad_instant, silo_instant, silo_cold |
| `guidance_trigger_2d.yaml` | guidance_study | gate fork | pad and silo_cold; paired sweep v_k in {30, 50, 80, 120} m/s |

Baseline identity (amendment 15): the resolved baseline run dicts of
calibration_f9_2d and silo_screening_2d are identical except `integrator.sample_dt_s`
(0.1 s and 0.05 s), and both fly the same vehicle file.

The schema resolves these files and, since build step 24, `sim.run` dispatches
their runs to the planar model (`sim.run_planar`). `cli.load_experiment` passes a
vehicle loader, so a calibration case that names its own vehicle file resolves through
the experiment's vehicle lookup, and `results_io.check_result_names` checks the names of
cases, bound runs and paired baselines before anything is written.

An `ExperimentConfig` validates the raw experiment dict only: its `model_dump()`
holds the injected baseline, which the raw form refuses, so a stored experiment is
re-resolved from its raw dict, never from a dump.

## Assumptions

Every assumption string the code emits, in one place, with the code that emits it.
A run's assumptions list is the union of the blocks that apply to it, in the order
`simulate` assembles them below (the `sim.run` block is prepended by `run` after
`simulate` returns); `summary.md` prints the union over its runs, attributed.

Every `sim.run` (`sim.RUN_MODEL_ASSUMPTIONS`, prepended by `run`; a `simulate` call
in a test does not carry it):

- pad and track g_eff = mu/R_E^2 - omega_p^2 R_E with omega_p = 0 rad/s (the value
  of `sim.OMEGA_P_PHASE1_RADS`), continuous with mu/r^2 at z = 0.

Every run (`sim.PHASE1_ASSUMPTIONS`):

- 1-D vertical motion.
- vacuum thrust from sea level (no back-pressure), no atmosphere, no drag.
- no Earth rotation (omega_p = 0), Coriolis neglected.
- no throttling; instantaneous cutoff at propellant depletion.

Every `simulate`, derived from what it was handed (`sim.gravity_assumption` and the
g_eff line):

- gravity mu/r^2 in flight (mu = 3.986004418e+14 m^3/s^2; InverseSquareGravity, the
  run model; ConstantGravity exists only for tests); or, in a test, constant gravity
  g = <value> m/s^2 in flight (analytic test model, not the run model).
- pad/track effective gravity g_eff = <value> m/s^2, also the g_ref of the
  gravity-loss split (9.7982855 for every run).

Every `simulate` (`sim.SIM_ASSUMPTIONS`):

- loss quadratures reset at release; the identity is accounted from release onward.
- a vehicle at rest on the ground is clamped until its thrust exceeds its weight; no
  gravity loss accrues while clamped (propellant burned then is reported as burned
  before flight).
- felt axial acceleration is T/m in flight (vacuum thrust, unthrottled), g_eff while
  clamped and (F_int + T)/m_v = sddot + g_eff sin phi on the track.

Every track run (`sim.TRACK_ASSUMPTIONS` and the geometry line):

- track phase: 1-DOF along the track in a flat local frame with constant g_eff; the
  carriage stays on the track at release; carriage braking is not modelled as a phase
  (its distance v^2/(2 a_brake) is added to the facility length).
- hot start: the propellant burned before release is reported with its delta-v
  equivalent; the exhaust impingement fraction f_imp on the carriage is an assumed
  amendment to the track equation (the system keeps (1 - f_imp) T).
- drive energy: electrical_energy = (positive drive work) / efficiency; no
  regeneration is credited for any negative (braking) drive work.
- track: straight, L = <L> m at <phi> rad above horizontal, start altitude <z0> m
  (exit at <z_exit> m).

A run whose fall-back coast ran after a failed ignition
(`sim.FAILED_IGNITION_ASSUMPTIONS`; not a pad `no_liftoff`):

- failed ignition: the fall-back coast is drag-free (no atmosphere in Phase 1;
  docs/physics.md, 'Failed-ignition coast', gives the order of magnitude of the
  neglected drag for the F9 class at its exit speed).
- failed ignition: no abort is modelled (a tilted exit that carries the vehicle clear
  of the mouth is the planar branch of Phase 2/3); Coriolis drift during the coast is
  neglected (omega_p = 0).

The same on a track (`sim.FAILED_IGNITION_TRACK_ASSUMPTIONS`):

- failed ignition: the braked carriage parks its braking distance beyond the track
  exit, in the fall-back path (failed_carriage_alt_m); the vehicle would meet it
  there first, on the way down (failed_t_carriage_s, failed_speed_at_carriage_mps,
  from the drag-free coast), unless the carriage is withdrawn in time, and no impact
  with it is modelled: the return to the mouth, the impact at the ground and the
  shaft-bottom speed are the obstacle-free values.
- failed ignition: the speed at the shaft bottom is derived from the impact speed at
  the ground and the fall from there to the track start (v^2 = v_impact^2 + 2 g_eff
  (z_impact - z_track_start)), not integrated.

A pad whose hold extended past t = 0 (`VerticalPlanner._liftoff`, in the trace;
appended after the failed-ignition blocks, before the drive's):

- hold extended to t = <t_liftoff> s for liftoff (TWR < 1 at release).

The `constant_accel` drive (`ConstantAccelAssist.assumptions`; every parameter is an
assumption in Phase 1, and `NoAssist` emits nothing):

- constant_accel: prescribed net acceleration <a> g0 (assumed); drive force
  unconstrained, solved from the track equation.
- constant_accel: carriage mass <m_c> t (assumed).
- constant_accel: braking deceleration <a_brake> g0 (assumed).
- constant_accel: drive efficiency <eta> (assumed).
- constant_accel: exhaust impingement fraction <f_imp> (assumed); the system keeps
  (1 - f_imp) T of the on-track thrust.
- constant_accel: shaft vented (no air column), no friction.
- constant_accel: constant g_eff = <value> m/s^2 on the track, omega_p = 0, Coriolis
  neglected.
- constant_accel: infinite jerk at push start and release.
- constant_accel: vehicle clamped to the carriage during any hold before the push.

The atmosphere module ("Atmosphere"): these three, plus the in-flight floor clamp,
are exported as the `ATMOSPHERE_ASSUMPTIONS` tuple (exact texts in "Atmosphere,
drag and back-pressure in flight"). No 1-D result carries them, because no 1-D run
evaluates the atmosphere; the planar model's `simulate_planar` appends the tuple to
every planar run (`sim.planar_assumption_list`):

- the geometric to geopotential conversion uses the ICAO radius 6,356,766 m, not
  `R_EARTH_M`; altitudes are geometric.
- above 81,020 m the atmosphere is isothermal at 196.649 K with scale height
  R_air T_top / g(h_top); not US76.
- the atmosphere is spherically symmetric and static; co-rotation enters through
  v_rel in the dynamics.

Every planar run (`sim.PLANAR_ASSUMPTIONS`, emitted by `simulate_planar` since build
step 24: the equations of motion, "Planar ascent state and equations of motion"; the
stage-1 planner, "Planar release map" and "Stage-1 guidance and events (planar)"; stage
2, "Stage 2 and insertion (planar)"; the search; plan section 5 and amendment 14). The
exact texts are the tuple's; in summary:

- planar ascent in the plane of the site and the launch azimuth, with omega_p = omega_E
  cos(lat) sin(az); the air's out-of-plane velocity omega_E sin(lat) r sin(theta) is
  neglected (exact for an equatorial east launch, and for the inertial dynamics,
  inclination and site velocity of an az 90 launch at i = lat).
- spherical Earth of radius R_E, point-mass gravity mu/r^2, geometric altitude
  h = r - R_E.
- the atmosphere co-rotates with Earth and has no wind: drag, Mach, q and gamma_rel use
  v_rel = (v_r, v_theta - omega_p r).
- point mass: the thrust points where the steering law says, instantly (no attitude
  dynamics); the body axis is the thrust axis, so the angle of attack of q-alpha is
  psi, the angle between thrust and v_rel.
- pure drag along -v_rel (no lift, no angle-of-attack dependence), one A_ref for the
  whole flight (through staging and the fairing drop; amendment 14).
- the power-on C_D table (base drag included) is also used in unlit coasts, a small
  bias toward cold starts (amendment 14).
- below |v_rel| = 1e-9 m/s the flight-path angle is local vertical (the pad).
- loss quadratures accumulate from the flight start; a clamped vehicle accrues no
  gravity loss.
- stage-1 guidance: a vertical rise with inertially radial thrust, a kick held at the
  angle delta from local vertical until the velocity is aligned with it, then a gravity
  turn along v_rel; the kick starts at the first lit instant at which |v_rel| >= v_k
  while rising; delta is solved so that gamma_rel at MECO equals gamma* (searched per
  run, or the shared fixed value of fixed guidance).
- the track push is flat and 1-DOF with g_eff = mu/R_E^2 - omega_p^2 R_E and the
  constant ambient pressure of the exit; no Coriolis and no air drag in the vented
  shaft: under a prescribed net acceleration (constant_accel) the drive force would
  absorb that drag, so the release speed is unchanged, and the drive energy, the peak
  drive power and the interface force are biased low (by int D v dt, D v_exit and D);
  release from a vertical track only.
- staging is instantaneous and impulse-free; the fairing stays on through staging
  under the heating rule unless the criterion is already met there.
- stage 2 flies linear-tangent steering (tan p = a - b tau in the local horizontal
  frame); the engine cuts off instantly when the orbital energy reaches the target's.
- the fairing is jettisoned instantly and impulse-free when 0.5 rho |v_rel|^3 falls
  below the vehicle's limit (in the stage-2 burn, or at stage-2 ignition when the
  criterion was met during the staging coast).
- no throttling (max-Q and q-alpha unthrottled and unconstrained: upper bounds), no
  flight-performance reserve, no unusable residuals; a payload adapter counts as
  payload.
- with rotation a vertical fall-back has u < 0, so gamma_rel wraps through +/-180 deg at
  the apex; the time series and events report it and the pitch unwrapped per run
  (amendment 14; `metrics_planar.unwrap_rad`, which also reads a rotation-off fall-back
  as 3 pi/2; the apex itself reads pi/2 without rotation, the local-vertical fallback,
  and about pi with it).

A run whose figure of merit is searched (payload, residual) adds
`sim.SEARCH_ASSUMPTIONS` (the search-only items of plan section 5):

- stage 2's (a, b) are solved by shooting for the target radius and zero radial
  velocity.
- searches burn virtual stage-2 propellant past the real load, down to a mass floor
  (the final verification's evaluations too, at the final tolerance); only the
  recorded run carries the real depletion, and one that runs dry before the cutoff
  reports its evaluation's signed (negative) m_res and dv_margin. A negative m_res is
  a virtual (massless) shortfall, propellant that weighs nothing until burned, not the
  load of a larger tank (which would make the shortfall worse).
- the residual propellant at the vehicle payload of a payload search is taken at the
  P*-optimal gamma*_ref, not re-optimised at P0 (a few kg low, against the assist).
- "sweep-optimized" guidance: gamma* is the best point of the shared grid refined by a
  bounded Brent search at the first payload estimate, delta and (a, b) are solved for
  it, and P* is the largest verified payload with m_res >= 0 (not an optimal-control
  solution; Phase 5).

A run flown at the shared fixed guidance (figure_of_merit none, stage 1 lit) adds
`sim.FIXED_GUIDANCE_ASSUMPTIONS` instead: gamma* and (a, b) are fixed inputs, only
delta is solved; no payload search and no P*, so a run can end off target and its
residual propellant and dv margin are the recorded run's own at its cutoff. A failed
stage-1 ignition flies no guidance and adds neither.

Every planar run also carries its own lines (`sim.planar_run_assumptions`): the site
(latitude, azimuth, rotation, omega_p and g_ref); the target orbit; the drag model (the
table's knots, PCHIP, cd_scale, A_ref); stage 2's startup (MVac starts at full thrust:
a step, amendment 14) and exit area (the vehicle file's value; the Phase 2 forks mark
it assumed, not published); the fairing rule; and for a pad lit before
release the hold-down convention (held to the release at t = 0 after the ramp,
amendment 14). A planar push adds `sim.TRACK_ASSUMPTIONS` and the track geometry, a
failed ignition whose coast ran `sim.PLANAR_FAILED_IGNITION_ASSUMPTIONS` (no abort; the
coast flown with drag, rotation and mu/r^2; the 1-D texts assume no atmosphere and are
not reused), and the drive's lines follow. On a planar run the `constant_accel`
track-gravity line names the g_eff actually used and the rotation behind it
(`ConstantAccelAssist.track_gravity_assumption`): "constant_accel: constant g_eff =
9.772092 m/s^2 on the track (mu/R_E^2 - omega_p^2 R_E with omega_p = 6.408435e-05 rad/s,
the planar rotation rate of the site), flat 1-DOF track frame, Coriolis neglected"; with
omega_p = 0 (every 1-D run) the Phase 1 text is unchanged. The planar-azimuth caveat
(`site.azimuth_rad` other than `sim.PLANAR_EXACT_AZIMUTH_RAD` = pi/2, due east) is a
run flag and the assumption line `sim.PLANAR_AZIMUTH_ASSUMPTION` (amendment 13).

Stated in this document and in the configs rather than emitted as strings: the datum
(z = 0 at the pad, the silo mouth and the release point; the ground and the impact
event are there; `exit_altitude_m` is not validated against 0), the locked pad
baseline convention (lit at t = -2 s so that full thrust arrives at release, 2,697 kg
burned on the pad; "Hold-down credit"), the vehicle file's vacuum thrust from sea
level (TWR 1.55 against 1.43 real) and its screening Isp (the ideal yardstick only),
that a thrust schedule is not capped by the propellant on board (every burn ends at
the `propellant` event), that staging is instantaneous and impulse-free, that the
config accepts a vertical track only and no rotation (Phase 2 gates), and that a
`drive_limit` run stops on the track without releasing. The run flags (disarmed-event
notes, `no_liftoff`, `drive_limit`, `interface_tensile`, `drive_braking`,
`ignition_failed ... ignored`, the mouth-not-at-ground flag, `end apex`, `FALL starts
on the ground`) are listed under "Result content"; they mark what a run did, not what
it assumes.

## Test-to-equation map

Every expected value in a test is computed there from constants and closed forms,
never from the package's own formulas; where a test asserts a rounded hand number as
well, that row says so. Tolerances are what the test asserts (CLAUDE.md's minimum
requirements are quoted where they are looser). Parametrised cases are one row.

| Test | Equation / section | Tolerance |
|---|---|---|
| `test_scaffold.py::test_package_imports_and_version` | the package imports; `__version__` | exact |
| `test_scaffold.py::test_earth_constants_only_in_constants_py` | mu, R_E, omega_E, g0 (and 9.81) appear only in `constants.py` ("Frames and datum", "Gravity") | exact (grep of `src/`) |
| `test_scaffold.py::test_every_file_open_declares_encoding` | every `open`/`read_text`/`write_text` passes `encoding=` | exact |
| `test_scaffold.py::test_public_physics_functions_have_docstrings` | every public physics docstring states inputs, outputs, units and frame | exact |
| `test_scaffold.py::test_pyproject_dev_tooling_installable_both_ways` | dev extra is a subset of the dev group | exact |
| `test_constants.py::test_literals_are_the_documented_values` | the `constants.py` values | exact |
| `test_constants.py::test_surface_gravity_and_equatorial_rotation_speed` | mu/R_E^2 = 9.7982855 m/s^2, omega_E R_E = 465.101 m/s ("Frames and datum") | 1e-7 and 1e-5 relative (the quoted digits) |
| `test_units.py::test_scalar_round_trips` | every conversion inverts its partner (`units.py`) | 1e-12 relative |
| `test_units.py::test_documented_factors` | 1000, 9.80665, pi/180, 3.6e6 as documented | 1e-15 relative (pi/180); exact for 1000, g0 and 3.6e6 |
| `test_units.py::test_array_inputs` | conversions accept arrays | exact |
| `test_atmosphere.py::test_icao_table_points` | ICAO layer closed forms at the table rows 0 to 80 km geopotential, converted with h = r0 H/(r0 - H) ("ICAO range") | 1e-4 relative p, rho; 1e-6 K abs; 1e-5 relative a |
| `test_atmosphere.py::test_constants_agree_with_ambiance_table` | R_air, r0, floor and top equal `ambiance.CONST` | exact |
| `test_atmosphere.py::test_matches_ambiance_on_dense_grid`, `::test_scalar_path_matches_ambiance` | the in-house layer forms against `ambiance.Atmosphere` on 20,001 points plus every layer base, both branches | 1e-12 relative (measured 8e-15) |
| `test_atmosphere.py::test_geopotential_conversion_matters` | p(11,000 m geometric) is not the 22,632 Pa tropopause value | > 0.1 % apart |
| `test_atmosphere.py::test_below_sea_level_and_floor`, `::test_non_finite_altitude_raises`, `::test_non_numeric_altitude_raises`, `::test_scalar_like_inputs_return_floats`, `::test_shape_preserved_and_empty_input`, `::test_array_results_are_read_only_and_input_untouched`, `::test_convenience_functions_match_state`, `::test_mixed_array_in_and_above_range`, `::test_array_matches_scalar_elementwise` | input contract of `standard_atmosphere` ("Atmosphere") | exact / raises |
| `test_atmosphere.py::test_top_state_anchored_to_table` | the 81,020 m state is the table's 80 km row (196.65 K, 0.88627 Pa) | 1e-3 K abs; 1e-4 relative |
| `test_atmosphere.py::test_extension_continuous_at_seam` | p, rho, T, a continuous at 81,020 m ("Isothermal extension") | 1e-6 relative (measured ~1e-13) |
| `test_atmosphere.py::test_extension_density_closed_form` | rho(h) = rho_top exp(-(h - h_top)/H_s), H_s = R_air T_top/(mu/(R_E + h_top)^2) | 1e-9 relative (anchor T); 1e-4 (table T) |
| `test_atmosphere.py::test_extension_never_steps_to_zero`, `::test_density_and_pressure_monotone_to_300_km` | the extension is positive and monotone | exact (sign) |
| `test_aero.py::test_table_passes_through_every_knot`, `::test_table_is_c1_with_the_pchip_slopes`, `::test_table_equals_scipy_pchip`, `::test_table_holds_the_end_values` | PCHIP through the Braeunig knots: C_D(M_k) = C_k; knot slopes from the Fritsch-Butland and three-point end formulas written in the test, equal from both sides; equal to scipy's `PchipInterpolator` on 9,001 points; end values held beyond [0, 4.5], NaN in NaN out ("Atmosphere, drag and back-pressure in flight") | knots 1e-15; slopes 1e-10; scipy 1e-14 abs; exact |
| `test_aero.py::test_table_rejects_bad_knots`, `::test_drag_model_rejects_bad_parameters` | `CdTable` and `DragModel` input rules (a non-number or bool knot raises TypeError) | raises |
| `test_aero.py::test_hand_built_table_is_stored_as_tuples` | a `CdTable` built from lists stores tuples of floats, hashes like its tuple twin, and evaluates its cubic | exact |
| `test_aero.py::test_drag_vector_against_ambiance_and_scipy` | (D_r, D_theta) = -0.5 rho V cd_scale C_D(V/a) A_ref (w, u) with rho, a from `ambiance.Atmosphere` (ICAO range) or the isothermal-extension closed form written in the test from the ambiance top state (above 81,020 m) and C_D from scipy, 8 states from sea level to 95 km including a descending one; magnitude = q cd_scale C_D A_ref; D antiparallel to v_rel | 1e-12 relative |
| `test_aero.py::test_drag_is_exactly_zero_at_rest`, `::test_cd_scale_is_exact_and_with_cd_scale_keeps_the_rest` | V = 0 gives (0, 0); cd(M) = cd_scale C_D(M) bit for bit; `with_cd_scale` and `with_payload` keep the rest of the vehicle | exact |
| `test_aero.py::test_ambient_scalar_equals_standard_atmosphere` | `ambient_scalar(h)` = `standard_atmosphere(h)` fields at 50 altitudes (floor, layer bases, seam, extension to 300 km), Python floats for np.float64 input | 0 ulp |
| `test_aero.py::test_ambient_scalar_clamps_below_the_floor`, `::test_sea_level_pressure_is_the_constant`, `::test_atmosphere_assumptions_are_ascii_strings` | floor state held below -5,004 m (where `standard_atmosphere` raises), NaN propagates; p(0) = `P_SEA_LEVEL_PA` = 101,325 Pa; the assumption strings | exact |
| `test_aero.py::test_stage1_sea_level_thrust_with_back_pressure`, `::test_stage2_back_pressure_at_70_km`, `::test_clamp_region_burns_at_full_vacuum_rate` | T = n T_vac - p0 A_e = 7,606.8 kN with A_e = n (T_vac - T_sl)/p0 from each fork's YAML; T2 = 981 kN - p(70 km) 8.6 m^2 (45 N); T = 0 and (T_vac - T)/m = T_vac/m until t_r p0 A_e / T_full | 1e-12 relative; exact |
| `test_aero.py::test_fairing_rule_and_string_shim`, `::test_screening_counts_the_heating_rule_as_a_drop_at_staging` | `FairingDrop` rules; staging/never normalised to strings; the heating rule counts as a drop at staging in the screening | exact / raises |
| `test_aero.py::test_quantity_list_rules`, `::test_aero_config_builds_the_drag_model`, `::test_fairing_drop_config_rules`, `::test_one_d_run_refuses_the_heating_rule` | vehicle-file schema of `aero`, `cd_mach` (`QuantityList`) and `fairing_drop`; a 1-D run refuses the heating rule | structural / raises |
| `test_aero.py::test_fork_numbers_all_have_provenance`, `::test_fork_masses_and_launch_mass_closure`, `::test_readme_fork_masses_are_the_one_d_files`, `::test_forks_differ_only_in_masses`, `::test_gate_fork_inputs` | the three 2-D forks: every number sourced or assumed; masses and launch mass without payload (546.3 / 519.77 / 549.9 t) from the YAML numbers; set A = the 1-D file's masses and provenance; identical apart from the five masses; the gate's Braeunig table, A_ref = pi 3.66^2/4 (0.01 m^2), heating rule 1,135 W/m^2, 11 s coast, stage-2 A_e 8.6 m^2 | exact; 1e-12 relative |
| `test_config.py::test_f9_converts_to_si`, `::test_engine_exit_area_rules`, `::test_constant_accel_units` | unit conversion at the boundary: 542,570 kg, 9 x 914.1 kN, A_e = (T_vac - T_sl)/P_SL, 3 g0 = 29.41995 m/s^2 | 1e-12 relative |
| `test_config.py` (every other test) | config rules: bare numbers and provenance in vehicle files, unknown keys, Phase 2 and Phase 3 gates, `fails` requires `end: impact`, `push_start` needs an assist, merge and override semantics, the shipped and tiny experiments resolve | structural / raises |
| `test_config_planar.py::test_shipped_planar_experiments_resolve`, `::test_shared_blocks_are_identical_across_the_planar_experiments`, `::test_calibration_and_silo_baselines_differ_only_in_sample_dt`, `::test_shipped_blocks_state_every_threshold` | "Experiment schema (planar)": the four shipped planar experiments resolve (cases through a CLI-style vehicle loader); identical shared blocks and one `budget_id`; amendment 15 baseline identity; every search, LTG, checks and guidance field written out | exact / structural |
| `test_config_planar.py::test_phase1_resolved_run_dicts_are_byte_identical`, `::test_inject_shared_is_a_plain_copy_when_nothing_is_declared` | no injection for a 1-D experiment: every run, sweep-point and sensitivity run dict of both 1-D golden sets equals the golden, key order included | exact (JSON text) |
| `test_config_planar.py` (model rules) | rotation only on planar_2d; explicit site; guidance, search, checks and target; aero and two stages; `integrator.rtol == search.final_rtol`; insertion and planar ends; `integrator.method` round trip; Phase 3 track message; heating refusal on vertical_1d only; shared blocks refused in baselines, variants, sweeps, sensitivity and bounds; paired sweeps (guidance_study only); cases (calibration only); search skip (amendment 4); sensitivity paths perturb the vehicle numbers (amendment 5, expected values from the vehicle file); the aero bound and its paired baseline (amendment 6); search and checks validators; radian and kg properties; `budget_id`; planar variants, sweeps, sensitivity and bounds may not change the integrator block, `sample_dt_s` included (1-D keeps its freedom); paired sweeps planar_2d only, planar vehicle sweeps paired (1-D unchanged); later-stage `t_ign_s >= 0`; gamma*, fixed gamma*, delta and LTG pitch ranges; `search_atol_scale >= 1`; omega_p against omega_E cos(lat) sin(az) at four sites (465.1 m/s at the equator, negative westward); the section-11 checks fields; raw-form-only experiments; `sim.run` runs the shipped silo_failed in the planar model (the former strict-xfail tripwire of the step-19 gap) | exact / raises / 1e-12 relative |
| `test_thrust_schedule.py::test_thrust_fraction_shapes`, `::test_zero_duration_is_a_step` | f for step, ramp, lag ("Thrust startup") | 1e-12 relative |
| `test_thrust_schedule.py::test_propellant_burned_closed_forms`, `::test_lag_forms_are_exact_just_after_ignition` | `propellant_burned_kg`: mdot t_r/2 at t_r; mdot [dt - tau (1 - e^(-dt/tau))]; just after ignition the lag forms follow their series, never a negative mass | 1e-12 relative; series 1e-6 relative |
| `test_thrust_schedule.py::test_integrated_mass_flow_matches_closed_form` | dm/dt = -T_vac/c integrated at g = 0 against the closed forms | 1e-9 relative |
| `test_thrust_schedule.py::test_startup_deficit_formulas`, `::test_startup_deficit_is_the_post_release_integral` | `startup_deficit_s` = integral over t >= 0 of (1 - f) ("Ignition-after-release loss"), the closed forms and a `quad` of 1 - f for step, ramp and lag at t_ign in {-3, -1.2, 0, 0.8} s | 1e-12 relative; 1e-9 relative against the quadrature |
| `test_thrust_schedule.py::test_schedule_thrust_and_back_pressure` | T = max(0, T_vac - p_amb A_e); kink times | 1e-12 relative |
| `test_rocket_equation.py::test_toy_step_thrust_matches_rocket_equation`, `::test_toy_ramp_gives_the_same_delta_v` | v_f = c ln(m0/mf), t_b = m_p/mdot (+ t_r/2), J_vac = v_f, g = 0 ("1-D ascent state") | 1e-9 relative (CLAUDE.md 1e-6; measured 2e-11) |
| `test_rocket_equation.py::test_f9_stage1_matches_rocket_equation` | g0 311 ln(542570/146870) | 1e-9 relative |
| `test_vertical_burn.py::test_vertical_burn_closed_form` | v_f = v0 + c ln(m0/mf) - g t_b; z_f = z0 + v0 t_b - g t_b^2/2 + c [t_b - (mf/mdot) ln(m0/mf)]; J_grav = g t_b; v0 in {0, 30, 77, 300} | 1e-9 relative v; 1e-8 z |
| `test_vertical_burn.py::test_burn_while_falling_counts_steering_and_regained_speed` | sigma = -1: J_steer = 2 c ln(m0/mf), J_grav = -g t; per-phase identity | 1e-9 relative; residual < 1e-9 m/s |
| `test_vertical_burn.py::test_back_pressure_clamp_burns_mass_without_thrust` | T = 0 while p_amb A_e > T_vac, m = m0 - mdot t^2/(2 t_r), J_bp = J_vac; then v(2) in closed form; `rhs_vertical` clamp equals `ThrustSchedule.thrust_N` | 1e-9 relative; residual < 1e-9 m/s |
| `test_coast.py::test_constant_g_apex_and_return` | apex z0 + v0^2/(2g) at v0/g, back at 2 v0/g with abs(v) = v0; one apex, one impact ("Gravity") | 1e-9 relative |
| `test_coast.py::test_inverse_square_apex_time_and_energy` | v^2/2 - mu/r conserved; 1/r_a = 1/R_E - v0^2/(2 mu); t_up = sqrt(a^3/mu) [pi - (E0 - sin E0)]; abs(v_impact) = v0 | energy 1e-10 relative; apex 1e-5 m; t 1e-9 relative |
| `test_events.py::test_propellant_event_lands_on_dry_mass` | the `propellant` root ("Event rules") | abs(m - m_dry) < 1e-6 kg |
| `test_events.py::test_apex_does_not_refire_at_the_start_of_a_fall`, `::test_apex_residue_within_atol_does_not_end_a_fall`, `::test_propellant_residue_within_atol_does_not_end_the_next_phase`, `::test_persistent_zero_never_fires`, `::test_turnaround_does_not_fire_at_the_start_of_a_fall`, `::test_twr_above_one_pad_start_does_not_trigger_apex` | rule 2: on the surface at t0 (disarm, band guard, Heun prediction) | the phase ends where the closed form says (sqrt(2 z0/g), the apex, the burnout) at 1e-9 relative; no spurious event |
| `test_events.py::test_fall_from_a_late_apex_root_reaches_impact` | a fall from an apex root at t0 = 3000 s under mu/r^2 reaches impact after the rise time | 1e-9 relative |
| `test_events.py::test_turnaround_fires_for_a_real_crossing_after_a_guarded_start` | a genuine later crossing of a disarmed event fires | at the band edge (ATOL_MPS) |
| `test_events.py::test_phase_already_past_a_terminal_event_ends_at_t0` | rule 1: already past | exact (t0, state untouched, event logged) |
| `test_events.py::test_direction_zero_convention`, `::test_non_terminal_events_are_logged_but_do_not_end_the_phase`, `::test_zero_length_phase_passes_the_state_through`, `::test_very_short_phase_integrates`, `::test_open_ended_phase_without_terminal_event_raises_at_t_max` | engine rules ("Integrator", "Event rules"): direction 0, non-terminal logging, ZERO_SPAN_S pass-through, first_step cap, t_max guard | exact / raises |
| `test_events.py::test_liftoff_event_is_thrust_minus_weight` | T(t, p_amb) - m g_eff with the clamp at 0 | 1e-12 relative |
| `test_events.py::test_atol_by_unit_suffix`, `::test_state_layout_and_model`, `::test_integrator_settings_from_config`, `::test_sigma_must_match_params_v_sign` | `atol_for`, `StateLayout`, `VerticalDynamics1D`, `IntegratorSettings`, the sigma/v_sign check | exact / raises |
| `test_phases_package.py::test_dense_output_off_gives_identical_event_states` | rule 4 (event states): a toy vertical burn under constant g_test from (z0, v0) with a non-terminal mark at 2 km and the terminal propellant event; dense off vs on: same steps, event times and `event_state`s, fewer RHS calls; the mark's state against v(t) = v0 - g t + c ln(m0/u), z(t) = z0 + v0 t - g t^2/2 + c [t - (u/mdot) ln(m0/u)], u = m0 - mdot t ("Integrator", "Event rules") | exact (dense off vs on); 1e-12 relative (against the dense output); v 1e-9, z 1e-8 relative; abs(z - z_mark) <= ATOL_M |
| `test_phases_package.py::test_repeated_event_occurrences_keep_their_order` | rule 4 with repeated occurrences: x'' = -w^2 x (A = 5 m, period 3 s) from t = 0.1 s to 10 s with non-terminal direction-0 events x = 1 (7 roots at (+-acos(1/A) + 2 pi k)/w) and v = 0 (6 roots at pi k / w); every occurrence's `event_state` equals the closed-form state (A cos w t, -A w sin w t) at the k-th root, dense on and off; on and off identical; dense output agrees | t 1e-9 s; state 1e-8 abs; exact (on vs off); 1e-11 abs (dense) |
| `test_phases_package.py::test_track_prelude_with_dense_output_off_logs_the_same_events` | a toy push at a = 3 g_test, lit mid-track, with dense output off logs the events and exit of the dense run (every track event is terminal, rule 4); sdot = sqrt(2 a L) | exact; 1e-10 relative |
| `test_phases_package.py::test_dense_output_off_is_refused_for_recorded_runs`, `::test_pass_through_lists_every_event` | `VerticalPlanner` refuses dense output off; `PhaseResult.dense_off` and `RunTrace.require_dense` flag a dense-off phase but not a closed-form HOLD or a pass-through ("Integrator"); a pass-through lists every event of its spec, (0, n) unless it fired (rule 4) | exact / raises |
| `test_phases_package.py::test_nfev_counts_the_solver_rhs_calls`, `::test_dense_output_off_saves_rhs_calls_without_events`, `::test_already_past_event_state_is_the_start_state`, `::test_event_state_rejects_an_unknown_occurrence`, `::test_pass_through_result_defaults` | `PhaseResult.nfev` equals a counting RHS's calls (0 for a pass-through); an already-past event's state is y0; `event_state` rejects an unknown occurrence | exact / raises |
| `test_phases_package.py::test_rad_suffix_and_atol_scale`, `::test_method_comes_from_the_config` | `_rad` -> ATOL_M / R_E; `atol_scale` equals a hand-scaled atol vector; invalid scales rejected; the method from a config that carries one, DOP853 otherwise ("Integrator") | exact / raises |
| `test_phases_package.py::test_vertical_view_keeps_z_and_signed_v`, `::test_records_and_views_outside_the_1d_columns`, `::test_event_records_are_frozen_and_hashable`, `::test_builder_refuses_a_state_of_another_layout` | the 1-D StateView keeps z_m and the signed v_mps (including -0.0); a view must provide m_kg; records are frozen and hashable, their values Python floats (sign of zero kept); a state of another layout is refused; a view rebinds only to the same model, layout and columns; `ascent_phases` follows the view's `ascent_kinds` ("Phases and events") | exact / raises |
| `test_phases_package.py::test_hold_on_another_layout_burns_only_the_mass`, `::test_liftoff_on_another_layout_matches_the_closed_form` | the prelude on a six-state planar-like layout: dm/dt = -T/c (5 kg/s: 10 kg in 2 s) with every other entry held and the minimum hold-down force m g - T; a step-lit hold with m0 g > T lifts off at t = (m0 - T/g)/mdot (32 s) with m = T/g; a builder with the 1-D view is refused ("Phases and events") | 1e-12 relative; liftoff 1e-8 s, mass 1e-10 relative |
| `test_phases_package.py::test_tilted_track_exit_closed_form`, `::test_curved_track_has_no_x_and_still_runs_in_1d`, `::test_fly_track_refuses_a_foreign_view` | a cold push up a straight 60 deg track from z0 = 5 m exits at x = L cos phi, z = z0 + L sin phi, sdot = sqrt(2 a L), t = sqrt(2 L / a), mass unchanged; a vertical exit has x = 0 exactly; a quarter-circle arc (r = 2 L / pi, no x(s)) exits vertical at z0 + r with the same sdot and t and x_exit None, and `VerticalPlanner.run_track` runs it to apex, releasing at that speed; a builder whose view reads another layout is refused | x, z 1e-15; sdot, t 1e-10 relative; arc z 1e-12 r / raises |
| `test_phases_package.py::test_every_phase1_name_is_still_importable`, `::test_public_package_functions_have_docstrings`, `::test_old_single_module_is_gone` | every name of the Phase 1 `phases.py`, and every launchsim name it imported, importable from `launchsim.phases`; the scaffold docstring rule on each module of the package | exact |
| `test_events.py::test_rotation_rate_and_track_gravity` | omega_p(0, pi/2) R_E = 465.101 m/s; omega_p(28.5 deg, 90 deg) = 6.408435e-5; g_eff_track(0) = 9.7982855, g_eff_track(6.408435e-5) = 9.7720917 | 1e-7 relative (the quoted digits) |
| `test_events.py::test_release_map_1d` | z = exit altitude, v = sdot, m; quadratures 0; a tilted track raises ("Phases and events", RELEASE) | exact |
| `test_events.py::test_pad_start_through_simulate_is_the_release_state` | an `AscentStart` (z0, v0) is the release state, v0 in {0, 77} | 1e-12 relative |
| `test_events.py::test_release_map_from_a_track_through_simulate` | release at t = sqrt(2L/a) with v = sqrt(2 a L), m = m_v (carriage stays); abs(s - L) at the root; time-series continuity | 1e-10 relative; abs(s - L) < 1e-9 m |
| `test_staging.py::test_two_stage_burn_with_staging_coast` | v_f = v0 + c1 ln(m0/mf1) + c2 ln(m02/mf2) - g (t_b1 + t_c + t_b2), m02 = mf1 - dry1 - fairing; g in {g0, 0}, coast in {0, 3} s ("Phases and events", STAGING) | 1e-9 relative |
| `test_hold.py::test_hold_with_ramp_lit_two_seconds_before_release` | m_release = m0 - mdot t_r/2, z = v = 0 at release, hold-down tension at release ("Hold-down bookkeeping") | 1e-10 relative |
| `test_hold.py::test_hold_extends_to_the_liftoff_root_when_lit_at_release` | t* from T_full t/t_r = (m0 - mdot t^2/(2 t_r)) g_eff (the quadratic solved in the test); 1,122 kg / 6.31 m/s burned in the extension | 1e-10 relative |
| `test_hold.py::test_step_lit_after_release_lifts_off_at_the_kink_with_the_mass_untouched` | a step above the weight lifts off at its kink; m - m0 = 0; burnout t_ign + t_b | exact mass; 1e-12 relative time |
| `test_hold.py::test_a_start_at_rest_above_the_ground_is_not_held_down` | `AscentStart.on_ground`: a start above the ground falls | structural |
| `test_hold.py::test_failed_ignition_on_the_pad_never_lifts_off` | `fails: true` on a pad: status `no_liftoff` at t_max, no exception | structural |
| `test_hold.py::test_a_lit_hold_split_after_ignition_burns_the_segment_increment_only` | `hold_closed_form` subtracts its own segment's increment: mdot/4 at -1 s, mdot/2 at 0 s | 1e-10 relative |
| `test_hold.py::test_a_moving_start_lit_before_release_emulates_a_burn_on_the_carriage` | the straddle form c ln(m0/(m0 - mdot t_r/2)) - g t_r/2 against an instant start ("Ignition-after-release loss") | 1e-5 m/s abs |
| `test_hold.py::test_propellant_exhausted_during_a_hold_raises` | ValueError when the hold burns the stage out | raises |
| `test_ignition_loss.py::test_ramp_loss_is_g_times_delay_plus_half_ramp` | v_f(step) - v_f(delayed) = g (t_d + t_r/2) for (0, 1), (0.5, 2), (1, 3) s; equal dv_vac; burnout t_d + t_r/2 + t_b | 1e-5 m/s abs; dv_vac 1e-10 relative |
| `test_ignition_loss.py::test_lag_loss_on_a_short_toy_burn_resolves_the_lambert_correction`, `::test_lag_loss_on_the_f9_burn` | g [t_d + tau (1 - e^(-u))], u = 1 + t_b/tau + W0(-e^(-1 - t_b/tau)) | 1e-5 m/s abs |
| `test_ignition_loss.py::test_analytic_loss_for_an_engine_lit_before_release` | `ignition_loss_analytic_mps` for t_ign = -t_r: 5.39 m/s under g0, bracketed by T/m0 - g0 and T/(m0 - mdot) - g0 | 5e-3 m/s abs (the documented figure) |
| `test_ignition_loss.py::test_ramp_straddling_the_release_through_the_silo` | loss = c ln(m0/(m0 - mdot Phi_pre)) - g Phi_pre + g D_post with Phi_pre = 0.5625 s, D_post = 0.0625 s through the 3 g0 / 100 m silo | 1e-5 m/s abs |
| `test_loss_identity.py::test_b_burn_against_the_velocity_then_coast_to_impact` | case (b): J_steer = 2 c ln(m(40)/m(50)), impact speed from energy ("Loss accounting") | residual < 1e-6 m/s (CLAUDE.md 0.01); closed forms 1e-9 relative |
| `test_loss_identity.py::test_c_burn_through_turnaround_to_burnout`, `::test_c_with_end_impact_reaches_a_second_apex` | case (c): one apex, one turnaround, v_bo = v_ign + c ln(m0/mf) - g t_b, steering 2 c ln(m0/m_turn); second apex z_bo + v_bo^2/(2g) | residual < 1e-6 m/s; 1e-9 relative |
| `test_loss_identity.py::test_d_f9_pad_start_under_inverse_square_gravity` | case (d): gravity_duration = g_ref t_b, gravity_alt < 0, dv_vac = c ln(m_release/m_dry) | residual < 1e-6 m/s; 1e-9 relative |
| `test_loss_identity.py::test_e_apex_inside_a_burn_flips_sigma_and_continues`, `::test_e_impact_while_thrusting_from_the_ground` | case (e): BURN(+1) -> BURN(-1) -> turnaround -> burnout; signed v_bo = v0 + c ln(m0/mf) - g (t_b + t_r/2); from z0 = 0 impact while thrusting | residual < 1e-6 m/s; 1e-9 relative |
| `test_loss_identity.py::test_a_silo_cold_f9_under_inverse_square_gravity` | case (a): speed_start = sqrt(2 a L), quadratures 0 at release, dv_vac = c ln(m0/m_dry), burnout t_d + t_r/2 + t_b after release, gravity_duration = g_ref times that | residual < 1e-6 m/s (measured 1e-12); 1e-9 relative |
| `test_assist_energy.py::test_cold_push_energy_is_the_mechanical_energy_gained` | E_drive = M (a + g_eff) L = delta KE + delta PE, W_thrust = massflow = 0, m_c in {0, 20 t}, g_eff = mu/R_E^2 - omega_p^2 R_E for omega_p in {0, omega_E cos 28.5 deg} (the identity with rotation, plan section 8) ("Assist energy identity") | 1e-10 relative; residual_rel < 1e-9 (CLAUDE.md 1e-6) |
| `test_assist_energy.py::test_hot_full_thrust_energy_closed_forms` | E_drive + W_thrust = (a + g) a [M0 t_p^2/2 - mdot t_p^3/3], W_thrust = (1 - f_imp) T L, delta_mech = M_exit (a + g) L, massflow = mdot (a + g) a t_p^3/6, f_imp in {0, 0.5, 1}, both omega_p | 1e-10 relative; residual_rel < 1e-9 |
| `test_assist_energy.py::test_planar_prelude_closes_with_rotation` | the planar planner's track prelude with the site's omega_p (g_eff = g_ref = mu/R_E^2 - omega_p^2 R_E written here, the on-track thrust T_vac - p(0) A_e) meets the hot closed forms | 1e-10 relative; residual_rel < 1e-9 |
| `test_assist_energy.py::test_ramp_straddling_the_push_closes` | closure only for a ramp lit inside the push; release at t_push | residual_rel < 1e-9; abs(s - L) < 1e-9 m |
| `test_silo.py::test_cold_push_kinematics_and_drive_force` | v_exit = sqrt(2 a L), t = sqrt(2L/a), s = a t^2/2, F_drive = M (a + g_eff), m_c in {0, 20 t} ("Silo model") | 1e-10 relative |
| `test_silo.py::test_vertical_track_carries_no_normal_load`, `::test_horizontal_track_unit_level` | N = m (kappa sdot^2 + g_eff cos phi): 0 at phi = pi/2, m g_eff at phi = 0 (unit level), sddot = a unchanged | abs(N) < 1e-6 N; 1e-10 relative |
| `test_silo.py::test_cold_felt_acceleration_and_interface_force`, `::test_peak_felt_axial_g_folds_in_the_track` | felt = a + g_eff = 39.2182 m/s^2 = 3.9992 g0; F_int = m_v (a + g_eff) = 21.2786 MN; run-wide peak = max(track, flight) with its phase (5 g0 push: ASSIST) | 1e-10 relative (hand numbers to 1e-4 as a cross-check) |
| `test_silo.py::test_hot_full_thrust_interface_and_drive_force` | F_int(t) = m_v(t)(a + g) - T at every sample, minimum at exit; F_drive at f_imp in {0, 1} | 1e-10 relative |
| `test_silo.py::test_interface_tensile_flag_for_a_slow_hot_push` | 0.5 g0 hot with f_imp = 1: F_drive > 0, F_int < 0 -> `interface_tensile` | sign / flag |
| `test_silo.py::test_drive_limit_when_a_ramp_crosses_zero_drive_force`, `::test_drive_force_negative_at_push_start_ends_at_t0` | `drive_limit` at the root of m(t)(a + g) = T(t) (the quadratic solved in the test); already negative at t0 -> ends at t0, release items None; `allow_negative_drive_force` completes with `drive_braking`, work_in equals the drive_limit run's net E_drive at the root | root 1e-9 relative; work 1e-9 relative |
| `test_silo.py::test_ramp_ending_at_the_track_end_is_logged_once` | `ramp_end` logged once, at release or inside the push | exact (event list) |
| `test_silo.py::test_assist_registry_builds_every_config_model` | `build_assist` through `ASSIST_MODELS`; unregistered key raises | exact / raises |
| `test_silo.py::test_cold_energy_power_and_facility` | E_drive = M (a + g) L, P_peak = F v_exit, d_brake = v^2/(2 a_brake) = L a/a_brake = 60 m, facility 160 m | 1e-10 relative |
| `test_silo.py::test_hot_full_thrust_energy_and_peak_power` | E_drive = (a + g) a [M0 t_p^2/2 - mdot t_p^3/3] - T L, W_thrust = T L, P(f_imp = 1)/P_cold = (M0 - mdot t_p)/m0, P(f_imp = 0) = ((M0 - mdot t_p)(a + g) - T) v_exit; P_hot at least 35 % below P_cold | 1e-10 relative |
| `test_silo.py::test_hot_push_peak_power_from_the_dense_output` | 0.6 g0 hot: vertex value F_drive(0)^2 a/(4 mdot (a + g)) at t* = F_drive(0)/(2 mdot (a + g)) inside the push; braking minimum at release | 1e-9 relative (t* to 1e-6 s abs; the sampled maximum within 1e-3; measured 3e-14) |
| `test_failed_ignition.py::test_silo_failed_under_inverse_square_gravity_via_sim_run` | apex r_a - R_E, t_up in the conditioned Kepler form, t_return = 2 t_up, abs(v_impact) = v_exit, shaft bottom sqrt(v^2 + 2 g_eff L), carriage at d_brake met at the Kepler fall time and energy speed; status, events, T_vac = 0, abs(J_grav) ("Failed-ignition coast") | apex 1e-5 m; 1e-9 relative; abs(J_grav) < 1e-6 m/s (hand numbers 300.270 m, 7.8291 s, 88.56 m/s as a cross-check) |
| `test_failed_ignition.py::test_silo_failed_under_constant_gravity_via_simulate` | h = 3 L, t_up = v0/g0, t_return = 2 v0/g0, carriage at v0/g0 + sqrt(2 (h - d)/g0) at sqrt(v0^2 - 2 g0 d) | 1e-9 relative |
| `test_failed_ignition.py::test_mouth_above_the_ground_splits_return_and_impact`, `::test_mouth_below_the_ground_never_returns` | return at the mouth, impact at sqrt(v0^2 + 2 g dz), shaft bottom sqrt(v0^2 + 2 g L) either way; the flag; gravity loss v0 - v_impact < 0 | 1e-8 relative |
| `test_failed_ignition.py::test_ignition_settings_of_a_failed_stage_are_flagged_as_ignored`, `::test_failed_ignition_on_the_pad_still_reports_no_liftoff` | nothing burns; the `ignition_failed ... ignored` flag; a pad `no_liftoff` gets no coast metric and no coast assumption | structural |
| `test_failed_ignition.py::test_falling_coast_starting_on_the_ground_ends_at_impact_at_once` | a falling coast within ATOL_M of the ground ends by impact at t0 ("Event rules") | exact |
| `test_failed_ignition.py::test_failed_second_stage_coasts_from_the_first_burnout`, `::test_apex_inside_a_long_staging_coast_is_the_failed_apex` | apex z_bo + v_bo^2/(2g), impact sqrt(v_bo^2 + 2 g z_bo) at t_bo + (v_bo + v_impact)/g from the vertical-burn forms; gravity loss g t_b + (v_bo - v_impact); the apex in COAST_STAGING still reported | 1e-9 relative |
| `test_vehicle_screening.py::test_mass_bookkeeping_two_stage_toy`, `::test_f9_bookkeeping_matches_independent_model` | stack, dry and post-staging masses against sums written in the test | 1e-12 relative |
| `test_vehicle_screening.py::test_toy_ideal_dv_is_the_rocket_equation` | `ideal_dv_mps` = sum of g0 Isp ln(m_ign/m_bo) | 1e-12 relative |
| `test_vehicle_screening.py::test_payload_gain_matches_independent_brentq`, `::test_propellant_saved_matches_independent_brentq` | the screening roots against an independent brentq in the test, v in {25, 50, 77, 99, 150, 300} m/s | 1e-6 relative |
| `test_vehicle_screening.py::test_readme_screening_table` | README's rounded table (220 ... 2790 kg; 14/18/53 t saved); labelled calibration-flavoured | 5 kg / 0.3 t |
| `test_vehicle_screening.py::test_payload_per_mps_about_nine_kg`, `::test_carrying_the_fairing_raises_the_77_mps_gain`, `::test_screening_needs_isps`, `::test_screening_isp_must_be_positive` | screening conveniences and their guards | loose bounds / raises |
| `test_convergence.py::test_scalar_metrics_converge` | rtol 1e-10 -> 1e-11, max_step caps halved, sample_dt 0.05 -> 0.01 s, five runs: burnout state, losses, release, silo energies and powers, preflight burn, failed-ignition coast ("Convergence") | 1e-8 relative (CLAUDE.md 0.1 % asserted beside it); altitudes also ATOL_M abs, loss quadratures also ATOL_MPS abs |
| `test_convergence.py::test_event_times_and_masses_converge` | every event's time, mass and altitude, five runs | 1e-8 relative; 1e-9 s at t = 0; ATOL_M |
| `test_convergence.py::test_delta_against_the_pad_converges` | the burnout-speed delta against the pad, its identity terms and the payload equivalent (cold, cold lag, hot full) | 1e-5 m/s abs and 1e-8 relative, asserted separately |
| `test_convergence.py::test_tight_settings_are_actually_tighter` | every tightened run has > 4x the rows and the settings are 10x / 2x | exact |
| `test_readme_numbers.py` (18 tests) | README hand numbers through `sim.run` on the shipped experiment, labelled calibration-flavoured: 76.71 m/s, 2.607 s, 3.999 g0, 21.5 MN, 2.2 GJ, 1.65 GW, 1.2 MWh, 60 m, failed apex 300.3 m / 7.83 s, burnout deltas +85/+70/+79/+64 m/s, hot-full 1.28 / 2.10 GJ and 0.97 / 1.60 GW, P_hot at least 35 % below P_cold; exact checks: silo_instant - variant = d J_grav at identical dv_vac with g_eff (t_d + t_r/2) and g_eff (t_d + tau) from constants, identity line, unexplained gain | the plan's tolerances (0.01 m/s, 0.001 s, 0.001 g0, 2-4 % on the hand numbers, +/- 0.8 and +/- 2 m/s); 1e-6 m/s on d J_grav; residual < 0.01 m/s |
| `test_results_io.py::test_compare_identity_line_closes_on_the_tiny_experiment` | the identity line d(speed) = d(release) + d(dv_vac) - d(gravity, duration) - d(gravity, altitude) - ... ("Figures of merit"); `payload_equiv_kg` both signs against the two-stage rocket equation written in the test | residual < 0.01 m/s; 1e-9 relative |
| `test_results_io.py::test_sensitivity_rows_compare_against_both_baselines_and_table_shape`, `::test_run_experiment_writes_sensitivity_and_the_no_sensitivity_switch`, `::test_si_value_converts_by_the_yaml_suffix`, `::test_variant_rows_insert_the_ignition_rows_and_the_flight_pair_only_when_it_differs`, `::test_summary_formatting_prints_rounding_noise_as_zero`, `::test_sweep_index_frame_has_the_curated_columns_and_rejects_axis_collisions`, `::test_write_plots_curated_panels_with_safe_names` | sensitivity semantics, SI conversion of the perturbed value, the summary table, display snapping, the sweep index, the plotted panels ("Figures of merit", Files) | structural / 1e-12 relative |
| `test_results_io.py` (every other test) | results directories, metrics.json round trip without NaN, summary encoding in a cp1252 subprocess, `git_info` states, name safety, failure markers | structural |
| `test_cli.py::test_full_experiment_writes_identity_lines_and_sensitivity`, `::test_full_sweep_writes_every_point_and_index`, `::test_full_experiment_plots_for_one_variant` | the shipped experiment end to end: every identity line closes, the bound lines, the yardstick lines, the 16 sensitivity cases, 12 + 9 + 3 sweep points, the curated plots | residual < 0.01 m/s; structural |
| `test_cli.py` (every other test) | the CLI contract: layout, ASCII stdout, exit codes, path rules, `--help`, `--version` | structural |
| `test_planar_dynamics.py::test_rocket_equation_2d_along_velocity` | CLAUDE.md's rocket equation in 2-D: mu = 0, omega_p = 0, thrust along v from 30 deg above horizontal, v0 in {1e-3, 100, 3000}: V_f - V_0 = c ln(m0/m_f) = J_vac; J_steer = J_grav = 0; straight-line end point at v0 t_b + c [t_b - (m_f/mdot) ln(m0/m_f)] ("Planar ascent state and equations of motion") | 1e-9 relative (CLAUDE.md 1e-6); exact zeros |
| `test_planar_dynamics.py::test_rhs_components_match_the_equations_of_motion` | every `rhs_planar` row against the planar EOM and quadrature rates written in the test, 300 seeded states | 1e-12 of the row's largest term |
| `test_planar_dynamics.py::test_pointwise_speed_identity`, `::test_fallback_is_the_one_sided_limit` | (w w' + u u')/V = dJ_vac - dJ_grav - dJ_drag - dJ_steer - dJ_bp = -g_eff w/V + (T cos psi - D)/m on 1,000 seeded states (rotation, ICAO drag, the clamp, every law form, unlit, unpowered); T e_r/m - g_eff - D/m below V_REL_EPS_MPS, the same value at w = 1e-6 m/s, and a 1e-3 s pad step against c ln(m0/(m0 - mdot h)) - g_eff h ("2-D loss identity") | 1e-12 x max(T/m, T_vac/m, g_eff, D/m, abs(w w')/V, abs(u u')/V); 1e-14 relative; 1e-9 relative; closure 1e-14 m/s |
| `test_planar_dynamics.py::test_atmosphere_is_evaluated_above_the_datum`, `::test_planar_fixture_factories` | with r_datum = 1e7 m, p, rho, a, the clamp, q, D and dv_r come from the atmosphere at r - r_datum (ICAO and exponential); the conftest factories `large_R_params`, `exp_atmosphere`, `const_atmosphere` and `const_accel_schedule` (100 s radial burn: m constant, J_vac = A t, v and z closed forms) ("Frame") | 1e-12 relative; 1e-10 relative |
| `test_planar_dynamics.py::test_planar_params_validate`, `::test_kinematics_and_model_views`, `::test_planar_observables` | `PlanarParams` refusals; w, u, V and the fallback; `PlanarDynamics2D` altitude and speed, required fields, `for_params` and `check_params`; alt, downrange R_E (theta - omega_p (t - t_fs)), speeds, gamma_rel, pitch, psi, q, M and the clamp of a hand state | raises; 1e-12 relative |
| `test_orbit.py::test_elliptical_orbit_ten_revolutions` | CLAUDE.md's orbit test: e = 0.3 from apoapsis (r_p = R_E + 500 km), 10 revolutions, DOP853 and RK45 at rtol 1e-10: E and h constant; P = 2 pi sqrt(a^3/mu) = 9,693.2665 s from the periapsis events; theta(10 P) = 20 pi | drift < 1e-8; period 1e-9 (DOP853) / 1e-8 (RK45); theta 1e-7 rad |
| `test_orbit.py::test_radial_coast_constant_g_apex`, `::test_radial_coast_inverse_square_apex`, `::test_non_radial_coast_conserves_energy_and_angular_momentum` | apex v0^2/(2 g_test) at v0/g_test; 1/r_max = 1/R_E - v0^2/(2 mu) with E conserved; E and h conserved on a non-radial coast with rotation on | 1e-9 relative; 1e-10 relative |
| `test_orbit.py::test_orbit_elements_of_the_ellipse`, `::test_circular_target_and_near_circular_eccentricity`, `::test_open_and_radial_conics` | a, e, r_p, r_a, E and h of the ellipse at four true anomalies; e = sqrt(1 + 2 E h^2/mu^2); E* = -30,297,365.5 J/kg and v_c = 7,784.2617 m/s; e = v_r/v_c near circular; hyperbola and radial conic ("Orbital elements and the circular target") | 1e-12 relative; 0.05 J/kg and 5e-5 m/s; 1e-6 relative |
| `test_planar_reductions.py::test_rhs_rows_equal_the_vertical_rows`, `::test_integrated_stage1_burn_matches_the_vertical_model`, `::test_state_names_share_the_1d_quadratures` | no rotation, v_theta = 0, radial, no drag, constant p (`const_atmosphere`): every planar row equals its 1-D row (500 seeded states), and an integrated gate stage-1 burn gives the 1-D altitude, speed, mass and quadratures ("Planar reductions") | 1e-15 relative (rows); 1e-10 relative with a 1e-6 m altitude floor |
| `test_planar_reductions.py::test_vertical_burn_constant_g_through_the_planar_rhs` | CLAUDE.md's vertical burn through the planar RHS: v_f = v0 + c ln(m0/mf) - g t_b, the z_f closed form, J_grav = g t_b, v0 in {0, 30, 77, 300} | 1e-10 relative with a 1e-6 m altitude floor |
| `test_planar_reductions.py::test_h0_reduction` | rotation, radial thrust, no drag: r v_theta = omega_p R_E^2; u = omega_p (R_E^2/r - r); altitude, v_r and m equal the 1-D model under H0Gravity (g = mu/r^2 - h0^2/r^3); J_steer > 0; the planar identity closes ("Planar reductions") | h 1e-12; u 1e-11 of omega_p R_E; 1e-10 relative with a 1e-6 m altitude floor; closure 1e-9 m/s |
| `test_planar_reductions.py::test_planner_reduces_to_the_vertical_planner` | planner level (amendment 11): the gate stage 1 through `PlanarPlanner` (no drag, no rotation, constant 101,325 Pa, vertical-only guidance) against `VerticalPlanner` for the pad and silo_cold to burnout: event names and times, phase kinds, t, r - R_E, v_r, m and every quadrature; theta, v_theta, J_drag = 0 ("Planar reductions") | 1e-10 relative (altitude with 1e-6 m) at rtol 1e-12; exact for the zero rows |
| `test_release_planar.py::test_pad_starts_at_the_ground_speed` | CLAUDE.md's release mapping: an east pad starts at omega_E cos(lat) R_E, 465.1 m/s equatorial and 408.7388 m/s at 28.5 deg; v_r = 0, V = 0, theta = 0; gamma_rel = pi/2 on the release row (the V = 0 fallback) ("Planar release map") | 1e-9 m/s absolute; 1e-4 m/s of the quoted digits; round(v, 1) = 465.1; exact otherwise |
| `test_release_planar.py::test_vertical_silo_release` | a 3 g, 100 m silo releases at t = sqrt(2L/a) with v_r = sqrt(2aL), v_theta = omega_p R_E; Earth-fixed push rows | 1e-9 relative; exact |
| `test_release_planar.py::test_silo_flight_rows_use_the_release_datum` | flight rows after a track start count downrange from the release (t_fs = t_release): the cold silo's ignition row equals the classical Coriolis drift -omega_p (v0 t^2 - g t^3/3) | 1e-3 relative (measured 1.2e-4) |
| `test_release_planar.py::test_general_release_map`, `::test_vertical_map_is_the_general_map_at_x0`, `::test_map_release_refuses_non_vertical_exits` | the exact general map against a Cartesian projection written in the test (four exits), |v_rel| = sdot, gamma_rel = phi + theta_x; the vertical and rest cases at the datum and at an exit 500 m above it (v_theta = omega_p (R_E + z_e)); the Phase 2 refusals | 1e-12 relative; 1e-13 m/s; raises |
| `test_release_planar.py::test_radial_rise_earth_fixed_downrange` | amendment 11: the Earth-fixed downrange of a radial rise, R (h0 int dt/r^2 - omega t) in closed form for r = R + a t^2/2 (test gravity h0^2/r^3 + g_c); the leading Coriolis term -omega a t^3/3 (1 - 0.9 h/R) | 1e-7 relative (measured 1.2e-8); altitude 1e-9; (h/R)^2 |
| `test_planar_events.py::test_liftoff_with_back_pressure_and_rotation` | the liftoff root of T_vac t/t_r - p0 A_e = (m0 - mdot t^2/(2 t_r)) g_ref (quadratic solved in the test), g_ref = mu/R_E^2 - omega_p^2 R_E; the mass there; the Earth-fixed pad state; the rise from the root lists no ground event and raises no flag ("Stage-1 guidance and events (planar)") | 1e-9 s; 1e-12 relative; exact |
| `test_planar_events.py::test_kick_trigger_and_alignment`, `::test_kick_at_the_first_lit_instant_when_already_past`, `::test_falling_vehicle_never_kicks` | the kick trigger at V = v_k with w > 0; the alignment at gamma_rel = pi/2 - delta and the continuous thrust direction into the turn; the kick at the first lit instant (cold and hot silo starts; no VERTICAL_RISE phase, no run flag); no kick while falling, before the turnaround | 1e-9 m/s; 1e-9 rad; 1e-12 s; exact order |
| `test_planar_events.py::test_kick_timeout_and_deadline_are_typed`, `::test_kick_deadline_counts_from_ignition`, `::test_a_dive_ends_at_the_ground` | GuidanceFailure kick_timeout and no_kick (deadline, burnout before the trigger); the deadline counts from stage-1 ignition, not from the flight start; a dive ends at the ground event (status impact; GuidanceFailure impact on the search path) | typed; altitude 1e-3 m |
| `test_planar_events.py::test_staging_map_and_coast`, `::test_later_stage_ignition_delay_adds_a_coast` | the staging map drops exactly m_d1 (+ F for rule staging or an already-met heating criterion) and leaves every other entry; the 11 s staging coast; a stage-2 t_ign_s adds COAST_PRE_IGN | 1e-12 relative; bit-equal; 1e-12 s |
| `test_planar_events.py::test_heating_rate_uses_v_rel_and_the_local_density`, `::test_vertical_only_guidance_takes_no_kick_angle` | the heating rate 0.5 rho(h) |v_rel|^3 with ambiance's rho and v_rel = (v_r, v_theta - omega_p r) computed in the test; the staging drop decision flips between the |v_rel| and inertial-speed rates at MECO; a vertical-only hand-over records delta None and a kick angle is refused | 1e-12 relative; exact; raises |
| `test_planar_events.py::test_loss_identity_closes_to_stage2_ignition` | V - V0 = J_vac - J_grav - J_drag - J_steer - J_bp at MECO and at stage-2 ignition (pad, silo_cold); zero steering loss in the turn and the coasts ("2-D loss identity") | 1e-5 m/s (measured ~1e-9); exact zeros |
| `test_planar_events.py::test_failed_stage1_ignition_on_a_silo`, `::test_failed_stage1_ignition_on_the_pad`, `::test_failed_stage2_ignition_coasts_to_the_ground` | failed ignitions: the COAST to the apex and the ground (identity closed), no_liftoff on the pad, a failed stage 2 after the staging coast | 1e-5 m/s; exact event lists |
| `test_planar_events.py::test_no_phase_lists_the_event_that_ended_the_previous_one`, `::test_search_mode_flies_the_same_stage1`, `::test_planar_modules_have_docstrings` | the event-list discipline ("Event rules"); dense-off hand-overs and event records equal to dense-on ones; docstrings of `guidance.py`, `phases/planar.py` and `phases/engine.py` | exact |
| `test_gravity_turn.py::test_culler_fried_gravity_turn` | the gravity turn against Culler-Fried: v, t, h, x, J_grav = (C/2)[z^(n-1)/(n-1) - z^(n+1)/(n+1)], J_vac = n g t, J_steer = 0 ("Stage-1 guidance and events (planar)") | 1e-6 relative (measured <= 1.7e-7); J_steer 1e-12 |
| `test_guidance.py::test_steering_laws`, `::test_guidance_spec_and_failures`, `::test_delta_settings_from_config` | Radial, FixedTilt, AlongVrel directions and pitches; the spec's rules; typed, picklable failures; the settings from the search block | 1e-15; exact |
| `test_guidance.py::test_gamma_meco_is_monotone_in_delta`, `::test_inner_solve_cold`, `::test_inner_solve_warm`, `::test_impact_gap_false_root_is_rejected`, `::test_timeout_sentinel_lies_above_every_real_gamma`, `::test_toy_inner_solve_roots_gaps_and_propagation` | gamma_MECO(delta) decreasing; gamma_rel(MECO; delta(gamma*)) = gamma* for 20 (cold) and 10, 30 deg (warm); the impact-gap false root; the +pi timeout sentinel above aligned flights steeper than pi/2; the toy map's sentinels, false roots, unattainable targets and propagation ("gamma* inner solve") | 3e-6 rad (Plan-mode deviation: the plan's 1e-9 is below the uncapped noise floor, up to 6.7e-7 rad); exact on the toy |
| `test_ltg.py::test_flat_linear_tangent_closed_form`, `::test_linear_tangent_law` | tan p = tan p0 - c t with constant A and g_test: v_x = (A/c) ln[(tan p0 + sec p0)/(tan p + sec p)], v_y = (A/c)(sec p0 - sec p) - g t; the law's direction (s, 1)/sqrt(1 + s^2) and pitch atan(s) ("LTG shooting") | 1e-6 relative (measured 1.4e-9, 3.6e-8); 1e-15 |
| `test_ltg.py::test_linear_tangent_is_optimal_on_a_flat_earth` (slow) | amendment 11: with eps tau^2 added and (a, b) re-solved for the same h_f and v_y,f = 0, d v_x,f/d eps = 0 by central difference, v_x,f largest at eps = 0 | 1e-6 relative and 1 % of the second-order drop (measured 5e-9 against 2.4e-6) |
| `test_ltg.py::test_ltg_ladder_and_physics_guess`, `::test_shooting_converges_from_every_rung`, `::test_shooting_failures_are_typed`, `::test_direct_root_window` | the physics guess a = tan(gamma_in + 5 deg), b = (a - tan(-1 deg))/tau_b and the ladder; warm, physics and steep rungs reach the same direct root with E = E*, abs(r - r_t) < 1 m, abs(v_r) < 1e-3 m/s, e < 1e-6; typed impact, nonconverged and not_direct_root; the direct-root window | 1e-14; 1e-9 relative, the acceptance, a and b within the acceptance box's image 2 abs(J^-1) (accept_r, accept_vr) (measured 1.34e-5 and 5.5e-8 1/s); typed |
| `test_ltg.py::test_solve_ltg_backward_difference_on_a_failed_forward_shot`, `::test_solve_ltg_halves_the_step_on_a_typed_failure` | `solve_ltg` on a synthetic linear residual in x = (a, 100 b): the backward-difference column when the forward shot raises (one exact step: 1 iteration, 5 shots, the shots at a +/- h logged); the step halved to the midpoint when the first trial raises (2 iterations, 8 shots) ("LTG shooting") | root 1e-9 in a, 1e-11 1/s in b; exact counts |
| `test_ltg.py::test_the_only_high_gamma_root_is_indirect_by_rule` | gamma* 32 deg on the gate pad: physics and steep reach one root with b < 0 (not_direct_root, then nonconverged); without the b > 0 test it inserts with m_res > 1 t ("LTG shooting", Direct-root boundary); `LTG_RUNGS == config.LTG_GUESS_RUNGS` (in `::test_direct_root_window`) | typed; 1e-9 relative, the acceptance, e < 1e-6 |
| `test_ltg.py::test_random_guesses_reach_the_same_root_or_fail_typed` (slow) | 40 seeded guesses converge to the same inserting direct root or raise GuidanceFailure (measured 13 converge) | the box-implied tolerance on a and b; typed |
| `test_ltg.py::test_step22_modules_have_docstrings` | docstrings of `guidance.py`, `orbit.py`, `losses.py`, `metrics_planar.py`, `phases/planar.py` | exact |
| `test_insertion.py::test_target_orbit_numbers` | E* = -mu/(2 r_t) = -30,297,365.5 J/kg, v_c = 7,784.2617 m/s, V_rel,f = v_c - omega_p r_t = 7,362.7061 m/s; the specific energy ("Orbital elements and the circular target") | 1e-15 relative; the quoted digits |
| `test_insertion.py::test_recorded_run_inserts` | the recorded pad run inserts: E = E*, abs(r - r_t) < 1 m, abs(v_r) < 1e-3 m/s, e < 1e-6, perigee and apogee within 10 m of 200 km, V_rel = v_c - omega_p r_t; the recorded end state equals the search shot's; the event list ("Stage 2 and insertion (planar)") | 1e-9 relative; as stated; 1e-2 m/s; bit-equal |
| `test_insertion.py::test_fairing_event_and_map`, `::test_heating_rule_carries_the_fairing_into_stage2` | 0.5 rho V^3 = 1,135 W/m^2 at the fairing event, rho from the isothermal extension written in the test; the FAIRING map drops exactly F, every other entry bit-equal; stage 2 ignites with m_p2 + m_d2 + P + F under the heating rule | 1e-9 relative; 1e-12 relative, exact; 1e-5 kg |
| `test_insertion.py::test_virtual_propellant_depletion_and_limits`, `::test_lofted_overshoot_and_missing_inputs_are_refused` | 30 t payload: virtual propellant gives m_res < 0 and dv_margin = c2 ln(m_c/(m_d2 + P)) < 0; the final mode ends at the real depletion (tau = tau_b = m_p2 g0 Isp / T2_vac written in the test, status short_of_orbit); every search shot arms the mass floor at exactly 0.5 (m_d2 + P), without the fairing; typed mass_floor and no_cutoff; typed lofted_overshoot; refusals | 1e-14 relative; 1e-6 kg, 1e-9 relative; exact; typed; raises |
| `test_engine_planar.py::test_dense_off_logs_the_same_events_to_insertion`, `::test_stage2_event_factories`, `::test_fairing_criterion_met_in_the_staging_coast` | dense output off and on log the same EventRecords, burnouts and status to insertion ("Event rules", rule 4); E - E*, m - m_floor and ln(0.5 rho V^3/q_fmh) written in the test; the fairing drops at stage-2 ignition with a flag when the criterion is met in the staging coast | exact (plan 1e-9 relative); 1e-12 relative; exact |
| `test_loss_identity_2d.py::test_pointwise_dVdt_along_the_recorded_pad` | `losses.pointwise_dVdt` on the recorded pad run: lhs = rhs, lhs = a central difference of abs(v_rel) from the dense output; the V = 0 fallback equals the ordinary branch at w = 1e-6 m/s ("2-D loss identity") | 1e-12 x scale (measured 4e-16); 1e-5 x scale (5e-8); 1e-9 relative |
| `test_loss_identity_2d.py::test_full_ascent_loss_budget_closes`, `::test_clamped_thrust_books_back_pressure` | CLAUDE.md's loss budget over a full planar ascent: V_f - V_0 = dv_vac - gravity - drag - steering - back_pressure for the pad to insertion, silo_cold, silo_hot_full, a 10 s ramp clamped at zero thrust for 0.75 s of flight (J_bp = J_vac there) and silo_failed through apex to impact ("2-D loss identity") | 1e-5 m/s (CLAUDE.md 0.01; measured 5e-9 to 9e-9); 1e-12 relative |
| `test_closure.py::test_matched_payload_attribution` | pad against silo_cold at one payload and gamma* 20 deg: every attribution term (dV_0, -dV_f, -dJ_grav, -dJ_drag, -dJ_steer, -dJ_bp, -d pre, -d fair) against the traces' |v_rel|, quadratures and masses written in the test; d dv_margin = sum of the terms; dV_f carried (nonzero); the kg split of a dP* adds up to it; the joint gravity + steering term and its kg share; different payloads refused ("Screening-beat rule (2-D)") | terms 1e-9 m/s; identity 1e-5 m/s; split 1e-12 relative |
| `test_closure.py::test_gamma_sensitivity_bookkeeping` | with the pad's run as the -h neighbour and silo_cold's as the +h one: each d(term)/d(gamma*) equals the silo_cold contribution written in the test over 2 h, the neighbours' contributions are 0 and silo_cold's, beyond_release their sum without the release speed ("Screening-beat rule (2-D)") | 1e-9 relative |
| `test_planar_pipeline.py` (fast: fixed guidance) | pad, silo_cold and silo_failed end to end through `sim.run_experiment`: every PLANAR_REQUIRED_METRICS key non-null but P* (no search); planar statuses and columns; gamma_rel and pitch unwrapped past pi in the fall-back with every step below pi; every PLANAR_VARIANT_ROWS label and required key in the summary, the fixed-guidance basis and label (not the sweep-optimized ones, no search assumption), the gamma* caveat, the screening line of every variant, blocked findings iff bug_suspect; the attribution closes (1e-5 m/s) with the release-speed term equal to the release speed; energy-only and screening sensitivity cases reuse the trajectory, electrical energy E/(1 + f), each attributed against its own vehicle's baseline (a screening case against the unchanged baseline not_checked); every pinned PLANAR_ASSUMPTIONS item (plan section 5, amendment 14), the search-only items in SEARCH_ASSUMPTIONS, FIXED_GUIDANCE_ASSUMPTIONS on the fixed-guidance runs; azimuth 80 deg gives the flag and PLANAR_AZIMUTH_ASSUMPTION; v_k 5000 m/s gives status guidance_failed (kind no_kick) with the summary written; the track's actual g_eff = mu/R_E^2 - omega_p^2 R_E (written here) and Coriolis neglected in the planar silo's assumptions; no planar or atmosphere assumption in a 1-D summary ("Reporting definitions (planar)") | exact; 1e-5 m/s; 1e-12 relative |
| `test_planar_pipeline.py` (fast: the screening-beat machinery) | on the recorded pad: t_v0 is the first instant hypot(v_r, v_theta - omega_p r) reaches silo_cold's release speed, and the time-shift estimate equals the integral of (mu/r^2 - omega_p^2 r) v_r/abs(v_rel) by scipy quad phase by phase (written in the test); `_ratio_check` passes inside the bounds and fails for the opposite sign, below and above, and for an estimate of 0 with d != 0; M4 at and above its share and n/a below min_term_mps; M5's bound direction, n/a for the anchor runs, other release speeds and no anchor; `anchor_from` wiring; a per-run check failure (tolerances 1e-15) gives status bug_suspect with trace_status inserted, three reasons and three flags; an injected beat without an attribution is bug_suspect when one is required and not_checked when not; a sub-yardstick run without one and a failed ignition are not_checked, the latter with closure n/a; a matched run with a vehicle 100 kg off its trace fails the attribution check; M2's d equals J_grav(silo_cold end) - J_grav(pad end) read off the recorded traces (variant minus baseline) and its ratio d/estimate; the M2 stage-1 diagnostic equals the J_grav difference at the two burnouts; M3 n/a at and applied below its floor; beats_screening uses the smaller of payload_gain_kg at P0 and at P*_base (written in the test) for P*_base above and below P0; neighbours equal to the centre give a robust M2 with a zero rate, the pad as the -h neighbour makes M2's verdict change there (not robust, named in the Checks text) while the verdict at gamma*_ref is unchanged; the trajectory key drops drive_efficiency for constant_accel only; an unconstrained kick labels the dP* an upper bound; `unwrap_rad` takes an exact -pi step, and one within ATOL_RAD of it, as +pi ("Screening-beat rule (2-D)", "Reporting definitions (planar)") | 1e-7 relative (quad); 1e-9 relative (t_v0); exact |
| `test_planar_pipeline.py::test_searched_runs_fill_every_required_metric`, `::test_bounds_cases_and_paired_sweeps` (slow) | searched pad and silo_cold on a small grid: every PLANAR_REQUIRED_METRICS key non-null, inserted, dP* the difference of the P*, the attribution at the pad's P* closes and its kg split adds up to dP*, the gamma* neighbours' rates finite and M2's gamma_robust set, the sweep-optimized basis, label and search assumptions, the planar plots; with fixed guidance, a bound (pair written, drag grows with A_ref, attributed against the pair, not_checked against the baseline), a calibration case (independent, CALIBRATION banner) and a paired v_k sweep (paired baselines written and indexed, kick regime per point, the fixed-guidance label and a Checks section with blocked findings iff a point is bug_suspect) | exact; 1e-5 m/s; 1e-6 kg |
| `test_closure.py` | D_id(P) = J_vac + c1 ln(m0/m_fs) + c2 ln[(1 + F2/m_f+)/(1 + F2/m2)] + dv_margin, with J_vac per stage = c ln(m_start/m_end) from the logged masses; heating rule, rules staging and never (flagged), silo_hot_full's track burn in closed form; a payload mismatch is caught; a fairing still on is empty mass (m_empty = m_d2 + P + F; the final-mode depletion at that mass after tau_b) ("Rocket-equation closure (planar)") | 1e-5 m/s (measured 8e-8 to 9e-8); 1e-9 relative; 1e-6 kg |
| `test_insertion.py::test_apex_and_impact_ends_stop_at_the_cutoff_after_insertion` | after an insertion, ends apex and impact stop at the cutoff like insertion (status inserted, the same end record, no COAST, one flag) ("Stage 2 and insertion (planar)", Recorded run) | exact |
| `test_insertion.py::test_a_cutoff_off_the_acceptance_is_not_inserted` | recorded runs at non-root pairs (1.05 a; 0.8 a with 1.2 b; 0.9 b with end impact) reach E = E* outside the LTG acceptance: status off_target with one flag, ending at the cutoff, no COAST ("Stage 2 and insertion (planar)", Recorded run) | 1e-9 relative; exact |
| `test_max_q.py::test_max_q_closed_form`, `::test_max_q_on_a_phase_boundary`, `::test_scan_does_not_depend_on_the_sampling`, `::test_gate_pad_max_q_beats_every_dense_sample` | t* = sqrt(2H/a) = 26.4575 s, q* = rho0 a H/e = 63,091 Pa for a = 20 m/s^2 through rho0 exp(-h/H) with no gravity; a peak on a phase boundary, q = 0.5 rho0 (a t_b)^2 exp(-a t_b^2/(2H)) at t_b exactly; the scan independent of its point count; no 0.01 s sample of the gate pad beats the scan ("Max-Q and loads (planar)") | t* 1e-4 s, q* 1e-9 relative; exact t, 1e-9; 1e-5 s and 1e-12 |
| `test_max_q.py::test_felt_loads_and_q_alpha_of_a_hand_built_state` | amendment 11: felt axial (T - D cos psi)/(m g0) and lateral D sin psi/(m g0), psi and q-alpha = q psi of a hand-built state against (T e - D v_hat)/m written in the test; the unpowered convention | 1e-12 relative |
| `test_payload_search.py::test_payload_matches_the_rocket_equation_closed_form`, `::test_no_orbit_reports_the_shortfall_at_zero_payload` | the toy two-stage rocket (c = 3000 m/s, zero gravity, vacuum, along v, virtual propellant to a speed target V*): P* from c ln(m0/m1) + c ln(m2/(m_d2 + P)) = V* (brentq in the test); every flown evaluation's m_res = m_c - (m_d2 + P) with m_c from the rocket equation; the high end at the mass floor backs off; no_orbit with shortfall V* - D_id(0) ("Figures of merit (planar)", "Virtual propellant", "Payload and gamma* search") | 0.5 kg; 1e-6 kg; typed; 1e-6 relative |
| `test_payload_search.py::test_bracket_expands_backs_off_and_fails_typed`, `::test_low_end_backs_off_toward_lighter_payloads`, `::test_a_failure_inside_the_bracket_is_search_failed_root` | the payload bracket on analytic m_res(P): high-end expansions, low-end expansion to P = 0, backoffs from an infeasible high end (halfway toward the low end, never again at or above a failure), SearchFailed bracket when backoffs or half-widths run out; a failing low end with nothing lighter flown backs off toward 0 (toward the hint under low_toward_hint, the final verification's rule) and the low end then expands below the new high end; P_lo is the largest evaluated payload with m_res >= 0; an infeasible evaluation inside the bracket is SearchFailed root | 0.5 kg; exact counts, brackets and payloads |
| `test_payload_search.py::test_m_res_is_monotone_and_continuous_across_depletion`, `::test_beyond_the_mass_floor_the_evaluation_fails_typed` (slow) | gate pad, gamma* 20 deg, search mode at the test rtol 1e-9: m_res(P) through zero strictly decreasing (the slope is recorded, not pinned), second differences below 0.05 kg (measured 2e-3); dv_margin = c2 ln(m_c/m_empty) of the same shot; slow: at 60 t a typed failure naming mass_floor ("Virtual propellant") | exact signs; 1e-12 relative; typed |
| `test_payload_search.py::test_final_run_is_inserted_with_a_tiny_residual` | the final verification at gamma* 20 deg: the recorded run inserted with 0 <= m_res < 0.05 kg, its stage-2 end state and every event equal to the final evaluation's, the real depletion event armed and the mass floor not, no flag ("Figures of merit (planar)", Recorded run) | 1e-9 relative; exact |
| `test_payload_search.py::test_short_of_orbit_record_carries_the_signed_figures`; `::test_vehicle_that_misses_orbit_is_no_orbit_through_run_search` (slow) | a recorded run short of orbit (final_residual 3 t above the root at 20 deg) ends short_of_orbit by depletion and carries its evaluation's negative m_res and dv_margin (figures_from final_evaluation, NaN cut-state difference); slow: the pad with 32 t more stage-2 dry mass, where no grid point flies at P0, searched through the grid re-run at P = 0 to no_orbit with a positive shortfall -dv_margin(0), at_p0 None and flagged ("Figures of merit (planar)", Recorded run) | exact |
| `test_payload_search.py::test_nested_solution_equals_the_joint_root` (slow) | the joint root of r_c = r_t, v_r,c = 0, m_res = 0 in (a, 100 b, P/1e4) from two perturbed guesses equals the nested P*, a and b | 1 kg (measured 0.004 kg); 2e-5 in a, 1e-7 1/s in b |
| `test_search.py::test_toy_sweep_is_deterministic_and_finds_the_closed_form`, `::test_grid_labels_penalties_and_warm_retry`, `::test_edge_optimum_is_search_failed_edge`, `::test_failing_refine_interval_scores_a_finite_penalty_without_warnings`, `::test_infeasible_grid_is_search_failed_grid` | on m_res = A - K (gamma* - g0)^2 - S (P - P0): identical results on repetition; the centre-out grid at P0; P1 and P2 at the closed-form roots, gamma*_ref at g0; labels feasible, infeasible and not_direct_root with penalties -(1e6 + 1e4 x distance in deg); the warm retry from an unused converged neighbour, flagged; edge and grid failures; finite penalties in the refine with warnings as errors ("Payload and gamma* search") | exact (as plain data); 0.5 kg; 0.01 deg; exact |
| `test_search.py::test_centre_out_order_and_halves`, `::test_budget_from_the_shared_config_and_tightened`, `::test_warm_store_nearest_and_kick_cache`, `::test_failures_are_typed_and_pickle`, `::test_context_from_the_resolved_runs` | the grid order and the final half-widths; SearchBudget from the shared blocks and its 10x tightening ("Convergence (planar)"); the nearest-gamma* warm start (latest on a tie) and the cached kick point; SearchFailed and PreludeFailure pickle; the contexts of pad and silo_cold ("Shared budget") | exact |
| `test_search.py::test_refine_onto_a_grid_bound_is_search_failed_edge`, `::test_vehicle_too_heavy_at_p0_is_no_orbit_not_nan`, `::test_signed_figures_at_the_vehicle_payload`, `::test_a_failed_payload_search_keeps_the_grid_table`, `::test_refine_with_every_evaluation_failing_falls_back_to_the_grid` | on the toy: an optimum drifting with P that the refine meets at the 8 deg bound is SearchFailed edge; every P >= 1 t failing gives the grid re-run at P = 0 and no_orbit with shortfall -dv_margin(0); the signed rung-2 figures at P0 in the record (payload: one final-mode evaluation at (P0, gamma*_ref); residual: status ok or short_of_orbit, the recorded run carrying the negative figures); a failed P1 bracket keeps the grid table; a refine with no feasible evaluation falls back to the best grid point with a NaN objective, flagged ("Payload and gamma* search") | exact; 0.01 kg; 1e-3 m/s |
| `test_search.py::test_grid_retry_repeats_until_no_new_point_solves`, `::test_refine_capped_by_the_shifted_window_is_flagged`, `::test_payload_search_backoffs_are_flagged`, `::test_final_verification_backs_off_toward_the_hint_and_flags`, `::test_final_verification_failures_are_typed`, `::test_final_bisection_keeps_the_residual_rule`, `::test_whole_toy_searches_do_not_depend_on_the_run_order`, `::test_a_warm_store_serves_one_problem` | on the toy: a grid point whose neighbours converge only in a retry is retried in a second pass; an optimum drifting above P0 caps the refine at its shifted window (refine_capped, the shift flag with both results); P1 backoffs flagged with the failed payload and kind; the final verification's low end backs off toward the hint (final_backoff), expansions flag search_final_mismatch and search_vs_final_payload; final_bracket, and final_run for an off_target recorded run, m_res >= 0.05 kg, a short run with m_res >= 0 and a no_orbit run reaching the cutoff; a steep local slope bisected until 0 <= m_res < 0.05 kg (flagged); whole toy searches identical as plain data in both run orders; on the gate fork a WarmStore bound to its first context raises ValueError for another context or the same context tightened ("Payload and gamma* search", "Shared budget") | exact; 0.05 kg / slope; typed |
| `test_search.py::test_residual_figure_short_of_orbit_is_signed` (slow) | figure_of_merit residual on the gate pad at a 30 t vehicle payload: no P1 or P2, the refine at P0, one final evaluation at P0 with m_res < 0: status short_of_orbit, the recorded run short of the cutoff with the evaluation's signed m_res and dv_margin ("Payload and gamma* search", Whole search) | exact |
| `test_search.py::test_swapped_run_order_gives_identical_evaluations`; `::test_swapped_order_whole_searches_are_identical` (slow) | pad and silo_cold evaluated (and, slow, searched on a three-point grid) in both orders give bitwise-identical results ("Shared budget") | exact |
| `test_convergence_2d.py::test_fixed_gamma_payload_and_margins_converge`, `::test_fixed_gamma_losses_and_max_q_converge` (pad, silo_cold; silo_cold_lag slow); `::test_reoptimised_search_converges` (slow; pad, silo_cold, silo_cold_lag) | CLAUDE.md's convergence rule with amendment 3's floors: the shipped budget (search rtol 1e-8, the only planar tests at it) against its 10x tightening (the ramp, lag and push step counts doubled) at fixed gamma* 20 deg (P*, m_res and dv_margin at 22.8 t, every loss term one by one, max-Q value and time) and re-optimised (P*, m_res and dv_margin at P0, gamma*, J_vac, drag, back-pressure, gravity plus steering jointly, max-Q value and time); the recorded run pushes exactly on the silo runs, and the recorded traces fly finite max_step caps in exactly the expected kinds, halved when tightened; after a re-optimisation gravity plus steering is compared jointly at the steering term's tolerance and the split is not asserted ("Convergence (planar)", Finding) | rel 1e-3 with floors 0.5 kg and 1e-3 m/s; gamma* 0.1 deg (measured: fixed gamma* every term within 4.6e-5 m/s, P* within 1.0e-3 kg; re-optimised P* at most 3.4e-3 kg, gamma* at most 6.3e-3 deg, m_res at P0 at most 0.25 kg) |
