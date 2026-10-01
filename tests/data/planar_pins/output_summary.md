# silo_screening_2d (<timestamp>, git <label>)

Comparison basis: fixed guidance (every run flies the shared fixed gamma* and LTG pair (a, b); only the kick angle delta is solved per run; no payload search, so no P*); planar_2d: rotating spherical Earth, ICAO atmosphere, drag, back-pressure, unthrottled; figures of merit: residual propellant and dv margin of the recorded run at the vehicle payload (a run can end off target)

Guidance is fixed, not sweep-optimized: every run flies the shared fixed gamma* and LTG pair (a, b) (figure_of_merit none); only the kick angle delta is solved per run. There is no payload search, so no P*, and a run can end off target.

- Vehicle: generic_f9_class_2d
- Baseline: pad
- Search budget id: 503cea2d7fa057eb3808a8a862cb776f6ac1eaf14564f506f0ffb7a8eb160992

## Variants against the baseline

| quantity | pad (baseline) | silo_cold | silo_failed |
|---|---|---|---|
| status | inserted | off_target | impact |
| search status | none (fixed guidance) | none (fixed guidance) | skipped (end: impact (ignition stage1 fails)) |
| run checks (closure, loss identity, insertion e) | ok | ok | ok |
| screening status (closure, attribution, M3 to M5; M2 only when blocking; a failed diagnostic check in brackets) | (baseline) | ok (diagnostic fail: M2) | not_checked |
| flags (see Flags) | - | 1 | - |
| stage-1 ignition, t_ign relative to release [s] (negative = lit before release) | -2 | 0.5 | n/a |
| stage-1 startup kind (step = instant full thrust: a yardstick, not achievable) | ramp | ramp | ramp |
|   its t_ramp or tau [s] | 2 | 2 | 2 |
| payload capacity P* [kg] (sweep-optimized) | n/a | n/a | n/a |
|   dP* vs baseline [kg] | (baseline) | n/a | n/a |
|   ideal screening at this run's release speed, at the baseline's P* [kg] | (baseline) | n/a | n/a |
|   ideal screening at this run's release speed, at the vehicle payload P0 [kg] | (baseline) | 675.346 | 675.346 |
|   screening yardstick used, the stricter of the two [kg] | (baseline) | 675.346 | 675.346 |
|     its basis | (baseline) | P0 | P0 |
|   dP* beyond the screening yardstick [kg] | (baseline) | n/a | n/a |
|   beats the screening yardstick | (baseline) | n/a | n/a |
|   dP* is an unthrottled/unconstrained upper bound (max-Q, q-alpha or kick) | (baseline) | True | False |
|   payload excess P0 - P* [kg] | n/a | n/a | n/a |
| residual propellant at P0 [kg] (signed; negative = virtual, massless shortfall) | 3135.72 | 4222.78 | n/a |
|   its basis | at the fixed guidance (no search) | at the fixed guidance (no search) | n/a |
| dv margin at P0 [m/s] (signed) | 377.618 | 499.348 | n/a |
| gamma*_ref, the flight-path angle at MECO [deg] | 20 | 20 | n/a |
| kick angle delta [deg] | 3.12845 | 2.61086 | n/a |
| LTG a (tan of the initial pitch) | 0.75679 | 0.75679 | n/a |
| LTG b [1/s] | 0.00219338 | 0.00219338 | n/a |
| kick regime | after_vertical_rise | at_first_lit_instant | none |
|   |v_rel| at the kick [m/s] | 50 | 71.8082 | n/a |
|   unconstrained kick (faster than checks.unconstrained_kick_mps) | (baseline) | False | n/a |
|   kick steering loss [m/s] | 0.0313554 | 0.0255199 | n/a |
| speed at release [m/s] | 0 | 76.7072 | 76.7072 |
| propellant burned before the flight [kg] | 2697.46 | 0 | 0 |
|   its dv_vac equivalent [m/s] | 14.4904 | 0 | 0 |
| MECO: t after release [s] | 151.328 | 153.828 | n/a |
|   altitude [m] | 66091.9 | 73868.3 | n/a |
|   |v_rel| [m/s] | 2748.08 | 2856.52 | n/a |
|   gamma_rel [deg] | 20 | 20 | n/a |
|   downrange [m] | 105584 | 115887 | n/a |
| fairing drop | in the stage-2 burn (heating event) | in the stage-2 burn (heating event) | n/a |
|   t after release [s] | 208.878 | 198.164 | n/a |
|   altitude [m] | 111481 | 111724 | n/a |
| stage-2 end: t after release [s] | 525.392 | 524.11 | n/a |
|   eccentricity | 1.09906e-07 | 0.0146274 | n/a |
|   perigee altitude [m] | 199999 | 103779 | n/a |
|   apogee altitude [m] | 200001 | 296221 | n/a |
| gravity loss [m/s] | 1435.06 | 1473.77 | -0.0367726 |
| drag loss [m/s] | 27.5358 | 23.3023 | 0.145751 |
| steering loss [m/s] | 119.167 | 109.217 | 0 |
| back-pressure loss [m/s] | 63.3196 | 49.695 | 0 |
| dv_vac from the flight start [m/s] | 9007.79 | 8901.99 | 0 |
|   loss-identity residual [m/s] | 0 | 0 | 4.34742e-09 |
| rocket-equation closure residual [m/s] | 0 | 0 | n/a |
|   pre-flight term c1 ln(m0/m_fs) [m/s] | 14.4904 | 0 | n/a |
|   fairing-carry term [m/s] | 4.71739 | 3.276 | n/a |
| max-Q [Pa] (unthrottled: an upper bound) | 38697.5 | 32314.1 | 3603.94 |
|   at t after release [s] | 65.5094 | 57.213 | 0 |
|   altitude [m] | 11019.1 | 11019.1 | 0 |
|   Mach | 1.5629 | 1.42819 | 0.225414 |
|   above the baseline | (baseline) | False | False |
| peak q-alpha [Pa rad] (alpha = psi; unconstrained) | 82.3877 | 143.614 | 0 |
|   at t after release [s] | 12.2682 | 0.5 | 0 |
|   above the baseline | (baseline) | True | False |
| peak felt axial g, run-wide [g0] (phase) | 5.30201 (GRAVITY_TURN) | 5.30255 (GRAVITY_TURN) | 3.99648 (ASSIST) |
| peak felt axial g in flight [g0] | 5.30201 | 5.30255 | 0 |
| peak felt lateral g in flight [g0] | 7.16026e-05 | 0.000112647 | 0 |
| peak felt g on the track [g0] | n/a | 3.99648 | 3.99648 |
| interface force, peak [N] | 0 | 2.23042e+07 | 2.23042e+07 |
| interface force, minimum [N] | 0 | 2.23042e+07 | 2.23042e+07 |
| hold-down force m g_ref - T, minimum over the hold [N] | -2.07186e+06 | n/a | n/a |
| peak track-normal g [g0] | 0 | 0 | 0 |
|   vehicle [g0] | 0 | 0 | 0 |
|   carriage [g0] | 0 | 0 | 0 |
| assist (drive) energy [J] | 0 | 2.23042e+09 | 2.23042e+09 |
| assist (drive) energy [kWh] | 0 | 619.561 | 619.561 |
| electrical energy [kWh] (positive drive work / efficiency) | 0 | 1239.12 | 1239.12 |
| peak drive power [W] | 0 | 1.71089e+09 | 1.71089e+09 |
| braking distance [m] | 0 | 60 | 60 |
| facility length incl. braking [m] | 0 | 160 | 160 |
| search: P2 - P1 [kg] | n/a | n/a | n/a |
|   search minus final payload [kg] | n/a | n/a | n/a |
| RHS evaluations of the recorded run | 6255 | 7268 | 1560 |
| failed ignition: stage | n/a | n/a | stage1 |
|   apex altitude of the fall-back coast [m] | n/a | n/a | 300.647 |
|   time of that apex after release [s] | n/a | n/a | 7.84265 |
|   impact time after release [s] | n/a | n/a | 15.6891 |
|   impact speed |v_rel| at the ground [m/s] | n/a | n/a | 76.5982 |

## Bounds

(no bounds declared)

## Cases

(no cases declared)

## Sensitivity

| variant | parameter | change | value [SI] (unit in the cell) | value (in the parameter's YAML units) | status | P* [kg] | dP* vs baseline, unchanged [kg] | dP* vs baseline with the same vehicle perturbation [kg] | trajectory reused (energy-only or yardstick case) | beats the screening yardstick (vs the baseline of the same vehicle) | screening status (vs the baseline of the same vehicle) | electrical energy [kWh] | peak drive power [W] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| silo_cold | assist.drive_efficiency | +10% | 0.55 - | 0.55 | off_target | n/a | n/a | n/a (= unchanged) | yes | n/a | ok (diagnostic fail: M2) | 1126.47 | 1.71089e+09 |
| silo_cold | assist.drive_efficiency | -10% | 0.45 - | 0.45 | off_target | n/a | n/a | n/a (= unchanged) | yes | n/a | ok (diagnostic fail: M2) | 1376.8 | 1.71089e+09 |
| silo_cold | vehicle.screening.stage_isp_eff_s.0 | +10% | 324.5 s | 324.5 | off_target | n/a | n/a | n/a | yes | n/a | ok (diagnostic fail: M2) | 1239.12 | 1.71089e+09 |
| silo_cold | vehicle.screening.stage_isp_eff_s.0 | -10% | 265.5 s | 265.5 | off_target | n/a | n/a | n/a | yes | n/a | ok (diagnostic fail: M2) | 1239.12 | 1.71089e+09 |

## Flags

- silo_cold: off target: the energy cutoff state misses the LTG acceptance (r_c - r_t = 32166 m against 1 m, v_r,c = 106.791 m/s against 0.001 m/s; e = 0.0146, perigee altitude 103779 m): the flown (a, b) is not a converged root at this run's settings

## Assumptions

- planar ascent in the plane of the site and the launch azimuth, with omega_p = omega_E cos(lat) sin(az); the air's out-of-plane velocity omega_E sin(lat) r sin(theta) is neglected (exact for an equatorial east launch, and for the inertial dynamics, inclination and site velocity of an az 90 launch at i = lat) [all runs]
- spherical Earth of radius R_E, point-mass gravity mu/r^2, geometric altitude h = r - R_E [all runs]
- the atmosphere co-rotates with Earth and has no wind: drag, Mach, q and gamma_rel use v_rel = (v_r, v_theta - omega_p r) [all runs]
- point mass: the thrust points where the steering law says, instantly (no attitude dynamics); the body axis is the thrust axis, so the angle of attack of q-alpha is psi, the angle between thrust and v_rel [all runs]
- pure drag along -v_rel (no lift, no angle-of-attack dependence), one A_ref for the whole flight (through staging and the fairing drop) [all runs]
- the power-on C_D table (base drag included) is also used in unlit coasts (a small bias toward cold starts) [all runs]
- below |v_rel| = 1e-9 m/s the flight-path angle is local vertical (the pad) [all runs]
- loss quadratures accumulate from the flight start (release, or the liftoff root of an extended hold); a clamped vehicle accrues no gravity loss [all runs]
- stage-1 guidance: a vertical rise with inertially radial thrust, a kick held at the angle delta from local vertical until the velocity is aligned with it, then a gravity turn along v_rel; the kick starts at the first lit instant at which |v_rel| >= v_k while rising; delta is solved so that gamma_rel at MECO equals gamma* (searched per run, or the shared fixed value of fixed guidance) [all runs]
- the track push is flat and 1-DOF with g_eff = mu/R_E^2 - omega_p^2 R_E and the constant ambient pressure of the exit; no Coriolis and no air drag in the vented shaft: under a prescribed net acceleration (constant_accel) the drive force would absorb that drag, so the release speed is unchanged, and the drive energy, the peak drive power and the interface force are biased low (by int D v dt, D v_exit and D); release from a vertical track only [all runs]
- staging is instantaneous and impulse-free; the fairing stays on through staging under the heating rule unless the criterion is already met there [all runs]
- stage 2 flies linear-tangent steering (tan p = a - b tau in the local horizontal frame); the engine cuts off instantly when the orbital energy reaches the target's [all runs]
- the fairing is jettisoned instantly and impulse-free when 0.5 rho |v_rel|^3 falls below the vehicle's limit (in the stage-2 burn, or at stage-2 ignition when the criterion was met during the staging coast) [all runs]
- no throttling (max-Q and q-alpha are unthrottled and unconstrained: upper bounds on the flown values), no flight-performance reserve, no unusable residuals; a payload adapter counts as payload [all runs]
- with rotation a vertical fall-back has u < 0, so gamma_rel = atan2(w, u) wraps through +/-180 deg at the apex; the time series and events report gamma_rel and the pitch unwrapped per run (numpy.unwrap; a step within the integrator's angular tolerance of -pi, the rotation-off apex, is taken as +pi, so a vertical fall reads 3 pi/2 with or without rotation; the apex itself reads pi/2 without rotation, the local-vertical fallback, and about pi with it) [all runs]
- fixed guidance (figure_of_merit none): gamma* and the LTG pair (a, b) are shared fixed inputs, not solved; only delta is solved for gamma* (at the final tolerance); there is no payload search and no P*, so a run can end off target, and its residual propellant and dv margin are the recorded run's own at its cutoff [pad, silo_cold]
- site latitude 28.5 deg, azimuth 90 deg, rotation on: omega_p = 6.408435e-05 rad/s, g_ref = mu/R_E^2 - omega_p^2 R_E = 9.7720917 m/s^2 (the pad balance, the track's g_eff and the reference of the gravity-loss split) [all runs]
- target: circular orbit of radius 6578137 m (altitude 200000 m above R_E), energy cutoff [all runs]
- drag: C_D(Mach) through the vehicle's 23-knot power-on table (PCHIP, held beyond the end knots) x cd_scale 1, on A_ref = 10.52 m^2 [all runs]
- stage 2 (stage2) starts at full thrust (step startup); its exit area 8.6 m^2 (the vehicle file's value; the Phase 2 forks mark it assumed, not published) sets the back-pressure p A_e [all runs]
- fairing (1700 kg): dropped when 0.5 rho |v_rel|^3 < 1135 W/m^2 [all runs]
- pad: held down to the release at t = 0 s; stage 1 lit at t = -2 s with a ramp startup, then clamped until its thrust exceeds its weight [pad]
- atmosphere: ICAO standard atmosphere closed forms (layer table of ambiance.CONST) from -5,004 m to 81,020 m geometric altitude; the geometric to geopotential conversion uses the ICAO radius 6,356,766 m, not R_E. [all runs]
- atmosphere: above 81,020 m an isothermal extension at 196.649 K with scale height 5,908 m (R_air T_top / g(h_top)); not US76 (denser near 110 km, far thinner above 150 km). [all runs]
- atmosphere: static, spherically symmetric, no wind; it co-rotates with Earth, so drag and Mach use the Earth-relative velocity v_rel. [all runs]
- atmosphere: in flight, an altitude below the -5,004 m floor is held at the floor state (ambient_scalar clamp; a dive ends at the ground event). [all runs]
- track phase: 1-DOF along the track in a flat local frame with constant g_eff; the carriage stays on the track at release; carriage braking is not modelled as a phase (its distance v^2/(2 a_brake) is added to the facility length) [all variants]
- hot start: the propellant burned before release is reported with its delta-v equivalent; the exhaust impingement fraction f_imp on the carriage is an assumed amendment to the track equation (the system keeps (1 - f_imp) T) [all variants]
- drive energy: electrical_energy = (positive drive work) / efficiency; no regeneration is credited for any negative (braking) drive work [all variants]
- track: straight, L = 100 m at 1.5708 rad above horizontal, start altitude -100 m (exit at 0 m) [all variants]
- constant_accel: prescribed net acceleration 3 g0 (assumed); drive force unconstrained, solved from the track equation [all variants]
- constant_accel: carriage mass 0 t (assumed) [all variants]
- constant_accel: braking deceleration 5 g0 (assumed) [all variants]
- constant_accel: drive efficiency 0.5 (assumed) [all variants]
- constant_accel: exhaust impingement fraction 0 (assumed); the system keeps (1 - f_imp) T of the on-track thrust [all variants]
- constant_accel: shaft vented (no air column), no friction [all variants]
- constant_accel: constant g_eff = 9.772092 m/s^2 on the track (mu/R_E^2 - omega_p^2 R_E with omega_p = 6.408435e-05 rad/s, the planar rotation rate of the site), flat 1-DOF track frame, Coriolis neglected [all variants]
- constant_accel: infinite jerk at push start and release [all variants]
- constant_accel: vehicle clamped to the carriage during any hold before the push [all variants]
- failed ignition: no abort is modelled; the unpowered coast to the apex and the ground is flown with drag, rotation and mu/r^2, from the track exit (or the pad) [silo_failed]

## Checks

- pad: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.09906e-07: ok
- silo_cold: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0.0146274: ok
- silo_failed: closure residual n/a m/s, loss-identity residual 4.34742e-09 m/s, insertion e n/a: ok
- silo_cold__assist.drive_efficiency__+0.1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0.0146274: ok
- silo_cold__assist.drive_efficiency__-0.1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0.0146274: ok
- silo_cold__vehicle.screening.stage_isp_eff_s.0__+0.1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0.0146274: ok
- silo_cold__vehicle.screening.stage_isp_eff_s.0__-0.1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0.0146274: ok

- silo_cold: dP* n/a kg (an unthrottled/unconstrained upper bound: q-alpha above the baseline) against the ideal screening yardstick 675.346 kg at its release speed 76.7072 m/s (the stricter of 675.346 kg at P0 and n/a kg at the baseline's P*: P0): n/a. matched-payload attribution at P_ref = 22800 kg: d dv_margin +121.729 m/s = release speed +76.7072, final speed +39.99, gravity -38.7076, drag +4.23352, steering +9.94999, back pressure +13.6246, preflight +14.4904, fairing +1.44139 m/s (residual 0 m/s); gravity + steering together -28.7576 m/s. The gravity and steering terms trade against each other as gamma* moves (the total is nearly stationary in gamma*), so only their sum is read as physics, never the split between them (docs/physics.md, 'Screening-beat rule (2-D)'). Checks: closure pass (worst residual 7.28e-12 m/s); attribution pass (worst closure 1.82e-11 m/s, worst identity 4.73e-11 m/s); M2 (diagnostic) fail (d +38.7076 m/s against the time-shift estimate -111.608 m/s: ratio -0.346816; stage 1 alone d +0.569274 m/s: ratio -0.00510064, a diagnostic); M3 pass (d -13.6246 m/s against the time-shift estimate -19.9465 m/s: ratio 0.683055); M4 pass (drag + steering +14.1835 m/s of +45.0222 m/s beyond the release speed: share 0.315034); M5 n/a. Screening status: ok (failed diagnostic checks, which block no finding: M2)
- silo_failed: dP* n/a kg against the ideal screening yardstick 675.346 kg at its release speed 76.7072 m/s (the stricter of 675.346 kg at P0 and n/a kg at the baseline's P*: P0): n/a. matched-payload attribution n/a (no rung-2 run at the matched payload). Checks: closure n/a (the variant burned no stage 2); attribution n/a (no rung-2 run at the matched payload); M2 (diagnostic) n/a; M3 n/a; M4 n/a; M5 n/a. Screening status: not_checked

Sensitivity cases and bounds against the baseline of the same vehicle (the screening-beat rule applies to them too):
- silo_cold assist.drive_efficiency +10% vs baseline: dP* n/a kg against the yardstick 675.346 kg (beats: n/a); failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: none; screening status ok
- silo_cold assist.drive_efficiency -10% vs baseline: dP* n/a kg against the yardstick 675.346 kg (beats: n/a); failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: none; screening status ok
- silo_cold vehicle.screening.stage_isp_eff_s.0 +10% vs same-perturbation baseline: dP* n/a kg against the yardstick 667.503 kg (beats: n/a); failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: none; screening status ok
- silo_cold vehicle.screening.stage_isp_eff_s.0 -10% vs same-perturbation baseline: dP* n/a kg against the yardstick 683.377 kg (beats: n/a); failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: none; screening status ok

No run and no comparison is bug_suspect.
Diagnostic checks that failed (computed and reported only: they give no bug_suspect and block no finding; user decision of 2026-09-30, docs/physics.md, 'Screening-beat rule (2-D)'): silo_cold (M2), silo_cold assist.drive_efficiency +10% vs baseline (M2), silo_cold assist.drive_efficiency -10% vs baseline (M2), silo_cold vehicle.screening.stage_isp_eff_s.0 +10% vs same-perturbation baseline (M2), silo_cold vehicle.screening.stage_isp_eff_s.0 -10% vs same-perturbation baseline (M2)
Screening not checked (no matched-payload attribution, so no loss breakdown explains the dP*; no finding about a beat rests on it): silo_failed
