# silo_bridge_2d_readme (20260930T185034Z, git 7ad381f227a9)

Comparison basis: sweep-optimized (every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, delta and the LTG pair are solved per run); planar_2d: rotating spherical Earth, ICAO atmosphere, drag, back-pressure, unthrottled; figure of merit: payload capacity P* at the target orbit

Guidance is sweep-optimized: every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, the kick angle delta and the LTG pair (a, b) are solved per run. Not an optimal-control solution (Phase 5).

- Vehicle: generic_f9_class_2d_readme_loads
- Baseline: pad
- Search budget id: a17a01601d0f4ae0c48cac48342127d5597e056e769da83503d7364c7d65a7df
- Timestamp (UTC): 20260930T185034Z
- Git: 7ad381f227a9

## Variants against the baseline

| quantity | pad (baseline) | pad_instant | silo_instant | silo_cold |
|---|---|---|---|---|
| status | inserted | inserted | inserted | inserted |
| search status | ok | ok | ok | ok |
| run checks (closure, loss identity, insertion e) | ok | ok | ok | ok |
| screening status (closure, attribution, M3 to M5; M2 only when blocking; a failed diagnostic check in brackets) | (baseline) | ok | ok | ok |
| flags (see Flags) | - | - | - | - |
| stage-1 ignition, t_ign relative to release [s] (negative = lit before release) | -2 | 0 | 0 | 0.5 |
| stage-1 startup kind (step = instant full thrust: a yardstick, not achievable) | ramp | step | step | ramp |
|   its t_ramp or tau [s] | 2 | 0 | 0 | 2 |
| payload capacity P* [kg] (sweep-optimized) | 24700 | 24790.9 | 26395.7 | 26094.4 |
|   dP* vs baseline [kg] | (baseline) | 90.8976 | 1695.68 | 1394.42 |
|   ideal screening at this run's release speed, at the baseline's P* [kg] | (baseline) | 0 | 738.687 | 738.687 |
|   ideal screening at this run's release speed, at the vehicle payload P0 [kg] | (baseline) | 0 | 684.758 | 684.758 |
|   screening yardstick used, the stricter of the two [kg] | (baseline) | 0 | 684.758 | 684.758 |
|     its basis | (baseline) | P0 | P0 | P0 |
|   dP* beyond the screening yardstick [kg] | (baseline) | 90.8976 | 1010.92 | 709.661 |
|   beats the screening yardstick | (baseline) | True | True | True |
|   dP* is an unthrottled/unconstrained upper bound (max-Q, q-alpha or kick) | (baseline) | False | True | True |
|   payload excess P0 - P* [kg] | -1900.01 | -1990.91 | -3595.69 | -3294.43 |
| residual propellant at P0 [kg] (signed; negative = virtual, massless shortfall) | 1814.4 | 1901.44 | 3407.89 | 3126.91 |
|   its basis | at gamma*_ref (P*-optimal guidance) | at gamma*_ref (P*-optimal guidance) | at gamma*_ref (P*-optimal guidance) | at gamma*_ref (P*-optimal guidance) |
| dv margin at P0 [m/s] (signed) | 224.371 | 234.772 | 409.948 | 377.95 |
| gamma*_ref, the flight-path angle at MECO [deg] | 20.9443 | 20.8596 | 19.5255 | 19.757 |
| kick angle delta [deg] | 3.99627 | 3.88235 | 5.14797 | 3.60254 |
| LTG a (tan of the initial pitch) | 0.531786 | 0.531087 | 0.514834 | 0.517876 |
| LTG b [1/s] | 0.0017502 | 0.00174707 | 0.00167488 | 0.0016882 |
| kick regime | after_vertical_rise | after_vertical_rise | at_first_lit_instant | at_first_lit_instant |
|   |v_rel| at the kick [m/s] | 50 | 50 | 76.7072 | 71.8077 |
|   unconstrained kick (faster than checks.unconstrained_kick_mps) | (baseline) | False | False | False |
|   kick steering loss [m/s] | 0.0512826 | 0.0483752 | 0.123914 | 0.0490858 |
| speed at release [m/s] | 0 | 0 | 76.7072 | 76.7072 |
| propellant burned before the flight [kg] | 2697.46 | 0 | 0 | 0 |
|   its dv_vac equivalent [m/s] | 15.1475 | 0 | 0 | 0 |
| MECO: t after release [s] | 145.694 | 146.694 | 146.694 | 148.194 |
|   altitude [m] | 67509.8 | 67841.8 | 73619 | 72621.7 |
|   |v_rel| [m/s] | 2844.41 | 2851.11 | 2965.32 | 2944.25 |
|   gamma_rel [deg] | 20.9443 | 20.8596 | 19.5255 | 19.757 |
|   downrange [m] | 106868 | 107578 | 120281 | 117844 |
| fairing drop | in the stage-2 burn (heating event) | in the stage-2 burn (heating event) | in the stage-2 burn (heating event) | in the stage-2 burn (heating event) |
|   t after release [s] | 196.964 | 197.662 | 192.122 | 194.582 |
|   altitude [m] | 112094 | 112124 | 112611 | 112520 |
| stage-2 end: t after release [s] | 479.075 | 480.075 | 480.075 | 481.575 |
|   eccentricity | 9.45148e-09 | 9.82287e-09 | 8.95949e-09 | 9.10057e-09 |
|   perigee altitude [m] | 200000 | 200000 | 200000 | 200000 |
|   apogee altitude [m] | 200000 | 200000 | 200000 | 200000 |
| gravity loss [m/s] | 1372.94 | 1378.66 | 1309.86 | 1336.97 |
| drag loss [m/s] | 29.9268 | 29.6014 | 25.8507 | 25.9905 |
| steering loss [m/s] | 38.1969 | 38.3138 | 39.5422 | 39.3299 |
| back-pressure loss [m/s] | 62.5123 | 62.5795 | 46.9266 | 49.8929 |
| dv_vac from the flight start [m/s] | 8866.28 | 8871.86 | 8708.18 | 8738.18 |
|   loss-identity residual [m/s] | 0 | 0 | 0 | 0 |
| rocket-equation closure residual [m/s] | 0 | 0 | 0 | 0 |
|   pre-flight term c1 ln(m0/m_fs) [m/s] | 15.1475 | 0 | 0 | 0 |
|   fairing-carry term [m/s] | 5.55095 | 5.49641 | 4.54213 | 4.70396 |
| max-Q [Pa] (unthrottled: an upper bound) | 42732.6 | 42214.6 | 36114.2 | 36386.8 |
|   at t after release [s] | 62.1327 | 62.4942 | 51.8056 | 55.002 |
|   altitude [m] | 11019.1 | 11019.1 | 11019.1 | 11019.1 |
|   Mach | 1.64236 | 1.63238 | 1.50983 | 1.51552 |
|   above the baseline | (baseline) | False | False | False |
| peak q-alpha [Pa rad] (alpha = psi; unconstrained) | 105.155 | 102.163 | 323.811 | 198.081 |
|   at t after release [s] | 10.7181 | 10.8807 | 0 | 0.5 |
|   above the baseline | (baseline) | False | True | True |
| peak felt axial g, run-wide [g0] (phase) | 5.63819 (GRAVITY_TURN) | 5.63478 (GRAVITY_TURN) | 5.57508 (GRAVITY_TURN) | 5.58621 (GRAVITY_TURN) |
| peak felt axial g in flight [g0] | 5.63819 | 5.63478 | 5.57508 | 5.58621 |
| peak felt lateral g in flight [g0] | 9.39485e-05 | 9.0863e-05 | 0.00026296 | 0.000161932 |
| peak felt g on the track [g0] | n/a | n/a | 3.99648 | 3.99648 |
| interface force, peak [N] | 0 | 0 | 2.14053e+07 | 2.13935e+07 |
| interface force, minimum [N] | 0 | 0 | 2.14053e+07 | 2.13935e+07 |
| hold-down force m g_ref - T, minimum over the hold [N] | -2.31255e+06 | n/a | n/a | n/a |
| peak track-normal g [g0] | 0 | 0 | 0 | 0 |
|   vehicle [g0] | 0 | 0 | 0 | 0 |
|   carriage [g0] | 0 | 0 | 0 | 0 |
| assist (drive) energy [J] | 0 | 0 | 2.14053e+09 | 2.13935e+09 |
| assist (drive) energy [kWh] | 0 | 0 | 594.593 | 594.265 |
| electrical energy [kWh] (positive drive work / efficiency) | 0 | 0 | 1189.19 | 1188.53 |
| peak drive power [W] | 0 | 0 | 1.64194e+09 | 1.64104e+09 |
| braking distance [m] | 0 | 0 | 60 | 60 |
| facility length incl. braking [m] | 0 | 0 | 160 | 160 |
| search: P2 - P1 [kg] | 19.293 | 16.4117 | 5.3402 | 1.18037 |
|   search minus final payload [kg] | -0.0274297 | -0.0275909 | -0.249536 | -0.249505 |
| RHS evaluations of the recorded run | 6027 | 6048 | 6858 | 7016 |

## Bounds

(no bounds declared)

## Cases

(no cases declared)

## Sensitivity

(no sensitivity block declared; C_D: drag is modelled: see the vehicle.aero.cd_scale cases)

## Flags

(none)

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
- stage 2's (a, b) are solved by shooting for the target radius and zero radial velocity [all runs]
- searches burn virtual stage-2 propellant past the real load, down to a mass floor (the final verification's evaluations too, at the final tolerance); only the recorded run carries the real depletion, and one that runs dry before the cutoff reports its evaluation's signed (negative) m_res and dv_margin. A negative m_res is a virtual (massless) shortfall, propellant that weighs nothing until burned, not the load of a larger tank (which would make the shortfall worse) [all runs]
- the residual propellant at the vehicle payload of a payload search is taken at the P*-optimal gamma*_ref, not re-optimised at P0 (a few kg low, against the assist) [all runs]
- "sweep-optimized" guidance: gamma* is the best point of the shared grid refined by a bounded Brent search at the first payload estimate, delta and (a, b) are solved for it, and P* is the largest verified payload with m_res >= 0 (not an optimal-control solution; Phase 5) [all runs]
- site latitude 28.5 deg, azimuth 90 deg, rotation on: omega_p = 6.408435e-05 rad/s, g_ref = mu/R_E^2 - omega_p^2 R_E = 9.7720917 m/s^2 (the pad balance, the track's g_eff and the reference of the gravity-loss split) [all runs]
- target: circular orbit of radius 6578137 m (altitude 200000 m above R_E), energy cutoff [all runs]
- drag: C_D(Mach) through the vehicle's 23-knot power-on table (PCHIP, held beyond the end knots) x cd_scale 1, on A_ref = 10.52 m^2 [all runs]
- stage 2 (stage2) starts at full thrust (step startup); its exit area 8.6 m^2 (the vehicle file's value; the Phase 2 forks mark it assumed, not published) sets the back-pressure p A_e [all runs]
- fairing (1900 kg): dropped when 0.5 rho |v_rel|^3 < 1135 W/m^2 [all runs]
- pad: held down to the release at t = 0 s; stage 1 lit at t = -2 s with a ramp startup, then clamped until its thrust exceeds its weight [pad]
- atmosphere: ICAO standard atmosphere closed forms (layer table of ambiance.CONST) from -5,004 m to 81,020 m geometric altitude; the geometric to geopotential conversion uses the ICAO radius 6,356,766 m, not R_E. [all runs]
- atmosphere: above 81,020 m an isothermal extension at 196.649 K with scale height 5,908 m (R_air T_top / g(h_top)); not US76 (denser near 110 km, far thinner above 150 km). [all runs]
- atmosphere: static, spherically symmetric, no wind; it co-rotates with Earth, so drag and Mach use the Earth-relative velocity v_rel. [all runs]
- atmosphere: in flight, an altitude below the -5,004 m floor is held at the floor state (ambient_scalar clamp; a dive ends at the ground event). [all runs]
- track phase: 1-DOF along the track in a flat local frame with constant g_eff; the carriage stays on the track at release; carriage braking is not modelled as a phase (its distance v^2/(2 a_brake) is added to the facility length) [silo_instant, silo_cold]
- hot start: the propellant burned before release is reported with its delta-v equivalent; the exhaust impingement fraction f_imp on the carriage is an assumed amendment to the track equation (the system keeps (1 - f_imp) T) [silo_instant, silo_cold]
- drive energy: electrical_energy = (positive drive work) / efficiency; no regeneration is credited for any negative (braking) drive work [silo_instant, silo_cold]
- track: straight, L = 100 m at 1.5708 rad above horizontal, start altitude -100 m (exit at 0 m) [silo_instant, silo_cold]
- constant_accel: prescribed net acceleration 3 g0 (assumed); drive force unconstrained, solved from the track equation [silo_instant, silo_cold]
- constant_accel: carriage mass 0 t (assumed) [silo_instant, silo_cold]
- constant_accel: braking deceleration 5 g0 (assumed) [silo_instant, silo_cold]
- constant_accel: drive efficiency 0.5 (assumed) [silo_instant, silo_cold]
- constant_accel: exhaust impingement fraction 0 (assumed); the system keeps (1 - f_imp) T of the on-track thrust [silo_instant, silo_cold]
- constant_accel: shaft vented (no air column), no friction [silo_instant, silo_cold]
- constant_accel: constant g_eff = 9.772092 m/s^2 on the track (mu/R_E^2 - omega_p^2 R_E with omega_p = 6.408435e-05 rad/s, the planar rotation rate of the site), flat 1-DOF track frame, Coriolis neglected [silo_instant, silo_cold]
- constant_accel: infinite jerk at push start and release [silo_instant, silo_cold]
- constant_accel: vehicle clamped to the carriage during any hold before the push [silo_instant, silo_cold]

## Checks

- pad: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 9.45148e-09: ok
- pad_instant: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 9.82287e-09: ok
- silo_instant: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 8.95949e-09: ok
- silo_cold: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 9.10057e-09: ok

- pad_instant: dP* +90.8976 kg against the ideal screening yardstick 0 kg at its release speed 0 m/s (the stricter of 0 kg at P0 and 0 kg at the baseline's P*: P0): beats it by 90.8976 kg (the attribution must explain this). matched-payload attribution at P_ref = 24700 kg: d dv_margin +10.3799 m/s = release speed +0, final speed +1.60413e-05, gravity -5.37687, drag +0.315909, steering +0.304095, back pressure -0.0647437, preflight +15.1475, fairing +0.0540595 m/s (residual 0 m/s); gravity + steering together -5.07278 m/s; dP* split in kg: release speed +0, final speed +0.000140474, gravity -47.0856, drag +2.76643, steering +2.66298, back pressure -0.566964, preflight +132.647, fairing +0.473402 (gravity + steering together -44.4226 kg). The gravity and steering terms trade against each other as gamma* moves (the total is nearly stationary in gamma*), so only their sum is read as physics, never the split between them (docs/physics.md, 'Screening-beat rule (2-D)'). Over gamma* +/- 0.5 deg the gravity term moves -14.1561 m/s per deg, the steering term +12.7742 m/s per deg, their sum -1.3819 m/s per deg. Checks: closure pass (worst residual 5.46e-12 m/s); attribution pass (worst closure 3.64e-12 m/s, worst identity 1.64e-11 m/s); M2 (diagnostic) n/a; M3 n/a; M4 pass (drag + steering +0.620004 m/s of +10.3799 m/s beyond the release speed: share 0.059731; over gamma* +/- h: -0.675903..0.682565, NOT robust (the verdict changes)); M5 n/a. Screening status: ok
- silo_instant: dP* +1695.68 kg (an unthrottled/unconstrained upper bound: q-alpha above the baseline) against the ideal screening yardstick 684.758 kg at its release speed 76.7072 m/s (the stricter of 684.758 kg at P0 and 738.687 kg at the baseline's P*: P0): beats it by 1010.92 kg (the attribution must explain this). matched-payload attribution at P_ref = 24700 kg: d dv_margin +187.212 m/s = release speed +76.7072, final speed +7.4872e-06, gravity +68.9073, drag +3.89072, steering +5.99289, back pressure +15.565, preflight +15.1475, fairing +1.00139 m/s (residual 0 m/s); gravity + steering together +74.9002 m/s; dP* split in kg: release speed +694.778, final speed +6.78155e-05, gravity +624.13, drag +35.2403, steering +54.2808, back pressure +140.981, preflight +137.199, fairing +9.07013 (gravity + steering together +678.411 kg). The gravity and steering terms trade against each other as gamma* moves (the total is nearly stationary in gamma*), so only their sum is read as physics, never the split between them (docs/physics.md, 'Screening-beat rule (2-D)'). Over gamma* +/- 0.5 deg the gravity term moves -14.6503 m/s per deg, the steering term +12.1163 m/s per deg, their sum -2.53398 m/s per deg. Checks: closure pass (worst residual 3.64e-12 m/s); attribution pass (worst closure 9.09e-12 m/s, worst identity 1.36e-11 m/s); M2 (diagnostic) pass (d -68.9073 m/s against the time-shift estimate -96.6616 m/s: ratio 0.712872; over gamma* +/- h: 0.637142..0.788704, robust; stage 1 alone d -36.4855 m/s: ratio 0.377456, a diagnostic); M3 pass (d -15.565 m/s against the time-shift estimate -18.3489 m/s: ratio 0.848283; over gamma* +/- h: 0.845564..0.850918, robust); M4 pass (drag + steering +9.88361 m/s of +110.505 m/s beyond the release speed: share 0.0894405; over gamma* +/- h: 0.0268499..0.141681, robust); M5 n/a. Screening status: ok
- silo_cold: dP* +1394.42 kg (an unthrottled/unconstrained upper bound: q-alpha above the baseline) against the ideal screening yardstick 684.758 kg at its release speed 76.7072 m/s (the stricter of 684.758 kg at P0 and 738.687 kg at the baseline's P*: P0): beats it by 709.661 kg (the attribution must explain this). matched-payload attribution at P_ref = 24700 kg: d dv_margin +154.914 m/s = release speed +76.7072, final speed +1.20348e-05, gravity +40.8395, drag +3.78638, steering +4.98559, back pressure +12.6074, preflight +15.1475, fairing +0.840656 m/s (residual 0 m/s); gravity + steering together +45.8251 m/s; dP* split in kg: release speed +690.459, final speed +0.000108328, gravity +367.606, drag +34.0821, steering +44.8764, back pressure +113.483, preflight +136.346, fairing +7.56695 (gravity + steering together +412.482 kg). The gravity and steering terms trade against each other as gamma* moves (the total is nearly stationary in gamma*), so only their sum is read as physics, never the split between them (docs/physics.md, 'Screening-beat rule (2-D)'). Over gamma* +/- 0.5 deg the gravity term moves -14.5588 m/s per deg, the steering term +12.252 m/s per deg, their sum -2.30677 m/s per deg. Checks: closure pass (worst residual 1.82e-12 m/s); attribution pass (worst closure 1.69e-10 m/s, worst identity 1.57e-10 m/s); M2 (diagnostic) pass (d -40.8395 m/s against the time-shift estimate -96.6616 m/s: ratio 0.4225; over gamma* +/- h: 0.347241..0.497857, robust; stage 1 alone d -13.6777 m/s: ratio 0.141501, a diagnostic); M3 pass (d -12.6074 m/s against the time-shift estimate -18.3489 m/s: ratio 0.687096; over gamma* +/- h: 0.684336..0.689772, robust); M4 pass (drag + steering +8.77197 m/s of +78.2071 m/s beyond the release speed: share 0.112163; over gamma* +/- h: 0.0229805..0.18756, robust); M5 pass (dP* +1394.42 kg against the anchor bound +1750.51 kg). Screening status: ok

No run and no comparison is bug_suspect.
Checks whose verdict changes within the variant's gamma* +/- h (the gamma*-sensitivity step; the verdict at gamma*_ref stands as pre-registered, but the gravity and steering terms trade against each other with gamma*, so these verdicts are not robust): pad_instant (M4)
