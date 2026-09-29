# launch-assist-sim: physics and assumptions

Phase 0, Phase 1 (the 1-D vertical model) and the constant-acceleration vertical silo
pulled forward from Phase 3. This file is the source of truth for the equations in
`src/launchsim/`; when code and this document disagree, one of them is wrong and the
change that fixes it updates both. Every section names the module it describes,
states its frame, units and assumptions, and points at the test that validates it.
The sections run in the order a run does: the atmosphere (a Phase 0 deliverable the
Phase 1 dynamics do not use), frames and datum, the 1-D state and equations of motion,
gravity (with the Phase 2 note on rotation), thrust startup, the integrator and its
event rules, the phase state machine, loss accounting, the ignition-after-release
loss, the assist energy identity, the silo model and its reported quantities, hot
starts, the failed-ignition coast, the figures of merit and their convergence; then
every assumption the code emits, collected in one list, and the test-to-equation map.

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

### Assumptions (module docstring only; to be emitted with every result that uses the module)

- The ICAO geometric to geopotential conversion uses the ICAO nominal Earth radius
  6,356,766 m, not `R_EARTH_M`; altitudes passed in must be geometric.
- Above 81,020 m the atmosphere is isothermal at 196.649 K (the ICAO state at
  81,020 m) with scale height `R_air T_top / g(h_top)`; not US76.
- The atmosphere is spherically symmetric and static; co-rotation with Earth enters
  through `v_rel` in the dynamics, not here.

## Frames and datum

Modules: `src/launchsim/dynamics.py`, `src/launchsim/phases.py`. Tests:
`tests/test_rocket_equation.py`, `tests/test_vertical_burn.py`, `tests/test_coast.py`,
`tests/test_events.py`.

**Ascent (Phase 1, 1-D).** One axis, +z up, z = 0 at the pad or silo mouth (the
release point), r = r_datum + z with r_datum = `R_EARTH_M`. The velocity v = dz/dt is
signed: positive rising, negative falling. Earth rotation is off in Phase 1
(omega_p = 0), so inertial and Earth-relative velocities coincide and the Earth-relative
flight-path angle is gamma_rel = +90 deg for v > 0, -90 deg for v < 0, and +90 deg (local
vertical) when |v| < `V_REL_EPS_MPS` (a pad start). The 2-D polar ascent frame of
CLAUDE.md (state [r, theta, v_r, v_theta, m], omega_p = omega_E cos(lat) sin(az)) is
Phase 2; `planar_rotation_rate(lat, az)` already computes omega_p for it.

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
decided in Phase 2 together with those quadratures; nothing in the Phase 1 code
implements it.

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

Module: `phases.py` (`IntegratorSettings`, `PhaseSpec`, `PhaseResult`,
`integrate_phase`, `atol_for`). One `scipy.integrate.solve_ivp` call per phase:

- DOP853 (`IntegratorSettings.method`; RK45 is the only other method accepted, per
  CLAUDE.md), rtol 1e-10 by default and in tests (CLAUDE.md asks for <= 1e-9),
  `dense_output=True` so callers resample at `sample_dt_s` (0.05 s) from the dense
  output; the result carries the integrator's own steps plus the event point.
- Per-state absolute tolerances from the unit suffix of the state name
  (`atol_for`): `_m` 1e-6 m, `_mps` 1e-9 m/s (velocity and the loss quadratures),
  `_kg` 1e-6 kg, `_J` 1e-3 J (track energies). A state with an unknown suffix is
  rejected so a new state cannot silently get a tolerance. These and the engine guards
  (`ZERO_SPAN_S`, `EVENT_ZERO_TOL`) are solver settings, not physics: they live as
  named, documented constants beside the solver in `phases.py` (as `vehicle.py` keeps
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
  `integrator:` block field for field.

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

## Phases and events

Module: `phases.py` (`VerticalPlanner`, `TraceBuilder`, `RunTrace`, `IgnitionSpec`,
`AscentStart`, `HoldParams`, `rhs_hold`, `map_release`, `map_staging`); `sim.simulate`
turns the trace into a `Result`. Tests: `tests/test_hold.py`, `tests/test_staging.py`,
`tests/test_ignition_loss.py`, `tests/test_loss_identity.py`, `tests/test_events.py`
(release map and pad start).

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
HOLD when a hold ran before t = 0 and RELEASE (`phases.RELEASE_LABEL`, not a phase
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
`track_observables`, `track_to_vertical`), `phases.py` (`VerticalPlanner.run_track`,
`ev_track_end`, `ev_drive_limit`, `map_release`), `sim.py` (`track_metrics`,
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
(`sim.TRACK_METRIC_ALIASES`) so the summary rows and REQUIRED_METRICS can use the
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

Modules: `phases.py` (`IgnitionSpec.fails`, `VerticalPlanner.ascend` and
`_fail_ignition`, `RunTrace.failed_stage` / `t_fail_s`), `sim.py`
(`failed_ignition_metrics`, `last_burn_end_s`, `descent_crossing`,
`carriage_park_altitude_m`, `failed_ignition_flags`, `FAILED_IGNITION_ASSUMPTIONS`,
`FAILED_IGNITION_TRACK_ASSUMPTIONS`). Test: `tests/test_failed_ignition.py`.

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
  (`sim.carriage_park_altitude_m`), which for a vertical silo is d_brake above the
  mouth, in the fall-back path. It stops at t = v_exit/a_brake after release (1.56 s
  for the shipped case) while the vehicle, decelerating only at g, is already above
  it; on the way down the vehicle meets it first, before the mouth. Constant g: at
  t_up + sqrt(2 (h - d_brake)/g) at |v| = sqrt(v0^2 - 2 g d_brake); mu/r^2: the time
  from the apex to a drop x below it is sqrt(a^3/mu) (delta + sin delta) with delta =
  2 asin(sqrt(x/r_a)) (the t_up form with x = h), and |v|^2 = v0^2 - 2 mu d_brake /
  (R_E (R_E + d_brake)) by energy. The code reads both off the FALL phase's dense
  output (`sim.descent_crossing` at z_carriage); it is reported so the mouth and
  shaft-bottom numbers are not mistaken for the first thing the vehicle hits.

**Reported** (`failed_*` metrics, present only when a stage failed; times relative to
release): `failed_stage`; `failed_apex_alt_m` and `failed_t_apex_s`, the highest apex
of the unpowered flight that ends in the failure, i.e. after the last burnout before
it (`sim.last_burn_end_s`; release for a first stage), so an apex reached inside a
long staging coast before a later stage fails still counts (None when the vehicle was
already falling at that burnout); on a track, `failed_carriage_alt_m`,
`failed_t_carriage_s` and `failed_speed_at_carriage_mps`, where the braked carriage
parks and when and how fast the falling vehicle first comes down to it (None when
the apex is below it; all three None on a pad); `failed_t_return_s`, when the vehicle is back down
at its release altitude (the mouth, or the pad): the first downward crossing of
z_release after that burn, found by brentq on the FALL phase's dense output
(`sim.descent_crossing_time_s`), which is the impact event itself when the mouth is at
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
...` says which altitude each item refers to (`sim.failed_ignition_flags`; it prints
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

Modules: `sim.py` (`compare`, `identity_budget`, `payload_equiv_kg`,
`ignition_timing_metrics`, `run_sensitivity`, `variants_table`, `checks_section`,
`sweep_index_frame`, `write_plots`). Without an orbit there is no payload capacity and
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
key's YAML suffix through units.py by `sim.si_value`: `_t` to kg, `_kN` to N, `_deg`
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

The atmosphere module ("Atmosphere"): these three are documented in the module
docstring of `atmosphere.py` only; no code path emits them and no Phase 1 result
carries them, because no Phase 1 run uses the module. When Phase 2 turns drag on,
the module must export them as an `ATMOSPHERE_ASSUMPTIONS` tuple that `simulate`
appends, or the promise in the docstring stays empty:

- the geometric to geopotential conversion uses the ICAO radius 6,356,766 m, not
  `R_EARTH_M`; altitudes are geometric.
- above 81,020 m the atmosphere is isothermal at 196.649 K with scale height
  R_air T_top / g(h_top); not US76.
- the atmosphere is spherically symmetric and static; co-rotation enters through
  v_rel in the dynamics.

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
| `test_config.py::test_f9_converts_to_si`, `::test_engine_exit_area_rules`, `::test_constant_accel_units` | unit conversion at the boundary: 542,570 kg, 9 x 914.1 kN, A_e = (T_vac - T_sl)/P_SL, 3 g0 = 29.41995 m/s^2 | 1e-12 relative |
| `test_config.py` (every other test) | config rules: bare numbers and provenance in vehicle files, unknown keys, Phase 2 and Phase 3 gates, `fails` requires `end: impact`, `push_start` needs an assist, merge and override semantics, the shipped and tiny experiments resolve | structural / raises |
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
| `test_assist_energy.py::test_cold_push_energy_is_the_mechanical_energy_gained` | E_drive = M (a + g_eff) L = delta KE + delta PE, W_thrust = massflow = 0, m_c in {0, 20 t} ("Assist energy identity") | 1e-10 relative; residual_rel < 1e-9 (CLAUDE.md 1e-6) |
| `test_assist_energy.py::test_hot_full_thrust_energy_closed_forms` | E_drive + W_thrust = (a + g) a [M0 t_p^2/2 - mdot t_p^3/3], W_thrust = (1 - f_imp) T L, delta_mech = M_exit (a + g) L, massflow = mdot (a + g) a t_p^3/6, f_imp in {0, 0.5, 1} | 1e-10 relative; residual_rel < 1e-9 |
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
