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

**Track (from step 7).** Origin at the track start, arc length s in [0, L]; a vertical
silo has phi = pi/2, kappa = 0, z_track = s and starts at altitude exit_altitude - L
(a buried silo starts at -L). Flat local frame with the constant effective gravity

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
  tests of this step hand it to `integrate_phase` directly; the planner step exposes it
  only through the injection point of `sim.simulate(...)`. It makes the rocket-equation,
  vertical-burn, coast and ignition-delay closed forms exact.

`G0_MPS2` converts Isp (c = g0 Isp) and defines the unit "g" for `_g` inputs and load
reports; it is never a gravity model.

Coast validation (`test_coast.py`, a COAST listing `apex` and `impact`, then a FALL
listing only `impact`, the planner pattern, so the disarm backstop is never engaged and
no note is produced): constant g gives apex z0 + v0^2/(2g) at t = v0/g and
the return to z0 at 2 v0/g with |v| = v0. Under mu / r^2 the motion is a radial Kepler
orbit: specific energy v^2/2 - mu/r is conserved at every sample (asserted 1e-10
relative, measured 2e-13), 1/r_a = 1/R_E - v0^2/(2 mu) gives the apex (asserted 1e-5 m;
measured 1e-6 m at 209 km, which is the `ATOL_M` floor of the altitude state, not an
rtol figure: it is -9.9e-7 m at rtol 1e-10 and -7.2e-7 m at rtol 1e-12, so the
convergence test must compare altitude changes against `ATOL_M`, not only relatively),
and with a = r_a/2, cos E0 = 1 - R_E/a, t_up = sqrt(a^3/mu) [pi - (E0 - sin E0)]
(asserted 1e-9 relative, measured 1e-12 and rtol-dependent), the vehicle is back at
R_E after 2 t_up with |v| = v0; v0 = 76.707 (the README silo exit speed; apex
300.27 m) and 2000 m/s.

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
  `constants.py`. That reading of CLAUDE.md's "no magic numbers" rule applies to the
  later steps too.
- `first_step = min(first_step_s, span/2)` with first_step_s = 1e-3 s: scipy raises
  when the first step exceeds the span, and 1e-4 s phases occur (staging coasts,
  the tail of a ramp).
- A phase whose span is <= 1e-12 s is not solved: the state passes through unchanged
  (`ended_by = "zero_span"`). Zero-length phases occur routinely (the kink at release,
  a zero staging coast).
- `max_step` is per phase and the planner (step 6) sets it in `PhaseSpec.max_step`
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

Track events (`track_end`, `drive_limit`) come with the assist models. An event built
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
   surfaces every "disarmed" note as a run flag.
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
got to ignite.

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
| HOLD (t_ign_abs < 0) | vehicle clamped: z, v held, mass by closed form `propellant_burned_kg` (no ODE; `hold_closed_form` subtracts only its own segment's increment of that closed form, so a lit hold split at any time after ignition, as a track prelude splitting at a startup kink does, gives the single-call mass); hold-down force m g_eff - T(t) tracked, its minimum reported (`hold_down_force_min_N`; not a tensile flag) | t = 0 | ASSIST (build step 7) or RELEASE |
| HOLD extension (pad, vehicle at rest on the ground, T(0) < m g_eff) | split at the thrust kinks. Before the ignition kink the sub-phase is *unlit* (`HoldParams.lit = False`: T = 0, nothing changes, sampled directly, no events), and at the start of every lit sub-phase the balance T - m g_eff is re-evaluated with the lit schedule, so a step whose thrust exceeds the weight lifts off exactly at its kink with the mass untouched (no root search across the discontinuity; the integrator's last stage never sees the step's f(0) = 1 from the left, which would bias the mass by 5e-6 kg, above `ATOL_KG`). A lit sub-phase integrates the mass alone (`rhs_hold`), max_step as in a burn. An ignition inside the extension is logged in the HOLD | `liftoff` (T - m g_eff, +1) -> "hold extended to t = X s for liftoff (TWR < 1 at release)" in the assumptions; `propellant` -> ValueError; t_max -> status `no_liftoff` (no exception) | BURN from the liftoff root, sigma = +1 |
| RELEASE (map) | pad: z = z0, v = v0 of the `AscentStart` (0, 0 for the pad; only a start at rest *on the ground* is held down, one at rest above it falls; a *moving* start lit before release is a test-only emulation of "lit on the carriage" without a track: the HOLD burns mass only and its rows keep v0, which is not a physical state but reproduces the straddle form exactly), m = m(0); track: `map_release` (z = exit altitude, v = sdot, m; a track angle other than pi/2 raises: projecting sdot onto the vertical would silently discard the downrange component, so the 1-D map is exact for a vertical track only and a tilted exit waits for the planar branch); quadratures reset; t_release recorded | | COAST_PRE_IGN or BURN |
| COAST_PRE_IGN | T = 0, sigma = +1 | t = t_ign_abs; `apex` -> FALL_PRE_IGN (sigma = -1, `impact` listed) | BURN; impact -> status `impact` |
| BURN k | ramp sub-phase (ends at t_ign + t_ramp, max_step t_ramp/ramp_steps) then the full burn (open-ended); lag: one burn with max_step tau/lag_steps_per_tau; step: one burn; `propellant` always listed | sigma = +1: `apex` -> same burn with sigma = -1 (`turnaround`, `impact` listed); sigma = -1: `turnaround` -> sigma = +1 (`apex` listed), `impact` -> status `impact`; `propellant` -> burnout | STAGING, or end |
| STAGING (map) | m -= dry mass of stage k (+ fairing when `fairing_drop: staging` and k = 0): `map_staging`; z, v, quadratures unchanged | | COAST_STAGING |
| COAST_STAGING / FALL_STAGING | T = 0 for stage k+1's `coast_before_ignition_s` (zero-length pass-through when 0); events by sigma as for COAST_PRE_IGN | t = coast end | COAST_PRE_IGN (t_ign_s > 0) or BURN k+1 |
| COAST / FALL (terminal) | T = 0 after the last burnout, or after a failed ignition (`fails: true`, which requires `end: impact`) | `apex` (end `apex`: stop), then `impact` at z_ground = 0 | status `impact` |

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
and the five quadratures. accel_felt_g is the proper (felt) axial acceleration in units
of g0 through `units.to_g`: T/m in free flight (vacuum thrust, unthrottled) and g_eff
while clamped, because the hold-down carries the weight and the vehicle feels 1 g_eff,
not the thrust building under it; the track phase supplies its own value,
(a + g_eff sin phi)/g0, with the assist models. Both ends of a phase boundary are kept
(the staging mass drop is visible). Events (t_s, event, phase, stage, z_m, v_mps,
m_kg): ignition, release, liftoff, ramp_end, propellant, apex, turnaround, staging,
impact, end. Metrics: the release state and what was burned before it (with its
delta-v equivalent c ln(m0/m_release)); the flight start (`t_flight_start_s`,
`mass_at_flight_start_kg`, `propellant_burned_before_flight_kg`,
`dv_vac_equiv_before_flight_mps`: release, or the liftoff root of an extended hold,
where the loss accounting begins); the hold (duration, extension, minimum hold-down
force, `hold_propellant_burned_kg` over the whole clamp); the first stage's burnout
(time from release, speed, altitude, mass); the final state; the highest apex and the
impact when reached; the peak felt acceleration in flight with its time and mass;
t_ign_rel_release_s per stage; and the loss budget below. Status and flags live on the
Result (metrics.json adds them). The assumptions list names the gravity model and the
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
`dynamics.py`. Tests: `tests/test_loss_identity.py` (b, c, d; a arrives with the silo),
`tests/test_staging.py`, `tests/test_ignition_loss.py`.

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
reset at release (t = 0 on a pad), speed_start = |v| at release, and the HOLD phases
(v = 0, no motion) contribute nothing; the budget sums the free-flight phases
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
release speed: that is the printed identity line of the summaries (build step 9).

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
impact), status `impact`, no burnout. The residual is asserted < 1e-6 m/s in every
case (CLAUDE.md allows 0.01) and measured at 1e-12 m/s: v and the quadratures are
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
D_post = 0.0625 s) is checked against the function, and its integration through a
track arrives with the silo (build step 7).
