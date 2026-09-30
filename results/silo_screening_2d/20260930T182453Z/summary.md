# silo_screening_2d: sweeps

Comparison basis: sweep-optimized (every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, delta and the LTG pair are solved per run); planar_2d: rotating spherical Earth, ICAO atmosphere, drag, back-pressure, unthrottled; figure of merit: payload capacity P* at the target orbit

Guidance is sweep-optimized: every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, the kick angle delta and the LTG pair (a, b) are solved per run. Not an optimal-control solution (Phase 5).

- Baseline: pad (status inserted)
- Timestamp (UTC): 20260930T182453Z
- Git: 7ad381f227a9

## sweep_1: silo_cold over assist.net_accel_g, assist.stroke_m

| point | assist.net_accel_g | assist.stroke_m | run_dir | of | paired_baseline | exit_speed_mps | payload_kg | payload_delta_kg | ideal_screening_payload_at_release_speed_at_pbase_kg | screening_yardstick_kg | payload_beyond_screening_kg | gamma_star_rad | speed_at_kick_mps | peak_q_alpha | delta_peak_q_alpha | max_q_pa | delta_max_q_pa | facility_length_m | drive_energy_J | drive_power_peak_W | kick_regime | unconstrained_kick | payload_delta_upper_bound | search_status | screening_status | screening_diagnostic_failed | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.5 | 50 | sweep_1/run_0001 | silo_cold | n/a | 22.1435 | 26294.6 | 240.232 | 218.804 | 193.083 | 47.1497 | 0.397337 | 50 | 68.617 | -6.11383 | 35910.4 | -1280.95 | 55 | 4.20153e+08 | 1.86073e+08 | after_vertical_rise | False | False | ok | ok | m2 | inserted |
| 2 | 0.5 | 100 | sweep_1/run_0002 | silo_cold | n/a | 31.3156 | 26510.5 | 456.054 | 309.946 | 273.503 | 182.551 | 0.393885 | 50 | 63.0959 | -11.635 | 34886.1 | -2305.29 | 110 | 8.40623e+08 | 2.63246e+08 | after_vertical_rise | False | False | ok | ok | m2 | inserted |
| 3 | 0.5 | 300 | sweep_1/run_0003 | silo_cold | n/a | 54.2402 | 27041.9 | 987.495 | 539.061 | 475.645 | 511.851 | 0.385598 | 50 | 49.4434 | -25.2875 | 32764.7 | -4426.72 | 330 | 2.52421e+09 | 4.56378e+08 | after_vertical_rise | False | False | ok | ok | m2 | inserted |
| 4 | 1 | 50 | sweep_1/run_0004 | silo_cold | n/a | 31.3156 | 26510.5 | 456.054 | 309.946 | 273.503 | 182.551 | 0.393886 | 50 | 63.0959 | -11.635 | 34886.1 | -2305.29 | 60 | 5.60745e+08 | 3.51201e+08 | after_vertical_rise | False | False | ok | ok | m2 | inserted |
| 5 | 1 | 100 | sweep_1/run_0005 | silo_cold | n/a | 44.2869 | 26812.4 | 758.043 | 439.354 | 387.679 | 370.364 | 0.389092 | 50 | 55.3673 | -19.3635 | 33612.6 | -3578.77 | 120 | 1.12208e+09 | 4.96935e+08 | after_vertical_rise | False | False | ok | ok | m2 | inserted |
| 6 | 1 | 300 | sweep_1/run_0006 | silo_cold | n/a | 76.7072 | 27553.2 | 1498.83 | 765.442 | 675.346 | 823.485 | 0.377803 | 71.8083 | 129.916 | 55.1851 | 31237.6 | -5953.74 | 360 | 3.3706e+09 | 8.6183e+08 | at_first_lit_instant | False | True | ok | ok | none | inserted |
| 7 | 3 | 50 | sweep_1/run_0007 | silo_cold | n/a | 54.2402 | 27041.9 | 987.495 | 539.061 | 475.645 | 511.851 | 0.385584 | 50 | 49.4442 | -25.2867 | 32764.8 | -4426.54 | 80 | 1.12352e+09 | 1.2188e+09 | after_vertical_rise | False | False | ok | ok | m2 | inserted |
| 8 | 3 | 100 | sweep_1/run_0008 | silo_cold | n/a | 76.7072 | 27553.2 | 1498.83 | 765.442 | 675.346 | 823.485 | 0.377803 | 71.8083 | 129.916 | 55.1852 | 31237.6 | -5953.74 | 160 | 2.24905e+09 | 1.72518e+09 | at_first_lit_instant | False | True | ok | ok | none | inserted |
| 9 | 3 | 300 | sweep_1/run_0009 | silo_cold | n/a | 132.861 | 28794.5 | 2740.13 | 1339.33 | 1181.47 | 1558.66 | 0.360578 | 127.937 | 1293.3 | 1218.57 | 29410.9 | -7780.47 | 480 | 6.76174e+09 | 2.99456e+09 | at_first_lit_instant | True | True | ok | ok | none | inserted |
| 10 | 5 | 50 | sweep_1/run_0010 | silo_cold | n/a | 70.0237 | 27402.1 | 1347.7 | 697.908 | 615.773 | 731.922 | 0.379912 | 65.127 | 85.9071 | 11.1762 | 31640.7 | -5550.65 | 100 | 1.68684e+09 | 2.36237e+09 | at_first_lit_instant | False | True | ok | ok | none | inserted |
| 11 | 5 | 100 | sweep_1/run_0011 | silo_cold | n/a | 99.0285 | 28052.7 | 1998.35 | 992.175 | 875.329 | 1123.02 | 0.370678 | 94.1213 | 393.223 | 318.492 | 30197.1 | -6994.25 | 200 | 3.3775e+09 | 3.34469e+09 | at_first_lit_instant | False | True | ok | ok | none | inserted |
| 12 | 5 | 300 | sweep_1/run_0012 | silo_cold | n/a | 171.522 | 29617.7 | 3563.28 | 1741.26 | 1535.84 | 2027.44 | 0.349861 | 166.575 | 3408.77 | 3334.04 | 29567.6 | -7623.76 | 600 | 1.01601e+10 | 5.80896e+09 | at_first_lit_instant | True | True | ok | ok | none | inserted |

## sweep_2: silo_cold over ignition.stage1.t_ign_s, ignition.stage1.startup.t_ramp_s

| point | ignition.stage1.t_ign_s | ignition.stage1.startup.t_ramp_s | run_dir | of | paired_baseline | exit_speed_mps | payload_kg | payload_delta_kg | ideal_screening_payload_at_release_speed_at_pbase_kg | screening_yardstick_kg | payload_beyond_screening_kg | gamma_star_rad | speed_at_kick_mps | peak_q_alpha | delta_peak_q_alpha | max_q_pa | delta_max_q_pa | facility_length_m | drive_energy_J | drive_power_peak_W | kick_regime | unconstrained_kick | payload_delta_upper_bound | search_status | screening_status | screening_diagnostic_failed | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 1 | sweep_2/run_0001 | silo_cold | n/a | 76.7072 | 27768.3 | 1713.89 | 765.442 | 675.346 | 1038.54 | 0.374677 | 76.7072 | 195.983 | 121.253 | 31022.7 | -6168.66 | 160 | 2.24989e+09 | 1.72583e+09 | at_first_lit_instant | False | True | ok | ok | none | inserted |
| 2 | 0 | 2 | sweep_2/run_0002 | silo_cold | n/a | 76.7072 | 27655.7 | 1601.29 | 765.442 | 675.346 | 925.941 | 0.376248 | 76.7072 | 170.942 | 96.2116 | 31125.1 | -6066.31 | 160 | 2.24945e+09 | 1.72549e+09 | at_first_lit_instant | False | True | ok | ok | none | inserted |
| 3 | 0 | 3 | sweep_2/run_0003 | silo_cold | n/a | 76.7072 | 27542.5 | 1488.15 | 765.442 | 675.346 | 812.807 | 0.377955 | 76.7072 | 147.15 | 72.4195 | 31253.8 | -5937.56 | 160 | 2.24901e+09 | 1.72515e+09 | at_first_lit_instant | False | True | ok | ok | none | inserted |
| 4 | 0.5 | 1 | sweep_2/run_0004 | silo_cold | n/a | 76.7072 | 27666.5 | 1612.11 | 765.442 | 675.346 | 936.766 | 0.376107 | 71.8083 | 150.76 | 76.029 | 31107.2 | -6084.22 | 160 | 2.24949e+09 | 1.72552e+09 | at_first_lit_instant | False | True | ok | ok | none | inserted |
| 5 | 0.5 | 2 | sweep_2/run_0005 | silo_cold | n/a | 76.7072 | 27553.2 | 1498.83 | 765.442 | 675.346 | 823.485 | 0.377803 | 71.8083 | 129.916 | 55.1852 | 31237.6 | -5953.74 | 160 | 2.24905e+09 | 1.72518e+09 | at_first_lit_instant | False | True | ok | ok | none | inserted |
| 6 | 0.5 | 3 | sweep_2/run_0006 | silo_cold | n/a | 76.7072 | 27439.4 | 1385 | 765.442 | 675.346 | 709.654 | 0.379423 | 71.8083 | 110.298 | 35.5673 | 31397.9 | -5793.5 | 160 | 2.2486e+09 | 1.72484e+09 | at_first_lit_instant | False | True | ok | ok | none | inserted |
| 7 | 1 | 1 | sweep_2/run_0007 | silo_cold | n/a | 76.7072 | 27564 | 1509.64 | 765.442 | 675.346 | 834.293 | 0.377649 | 66.9111 | 113.674 | 38.9432 | 31218 | -5973.37 | 160 | 2.24909e+09 | 1.72521e+09 | at_first_lit_instant | False | True | ok | ok | none | inserted |
| 8 | 1 | 2 | sweep_2/run_0008 | silo_cold | n/a | 76.7072 | 27450.1 | 1395.66 | 765.442 | 675.346 | 720.314 | 0.379271 | 66.9111 | 96.6312 | 21.9004 | 31379.8 | -5811.55 | 160 | 2.24864e+09 | 1.72487e+09 | at_first_lit_instant | False | True | ok | ok | none | inserted |
| 9 | 1 | 3 | sweep_2/run_0009 | silo_cold | n/a | 76.7072 | 27335.5 | 1281.12 | 765.442 | 675.346 | 605.771 | 0.380843 | 66.9111 | 80.7312 | 6.00034 | 31572 | -5619.41 | 160 | 2.24819e+09 | 1.72453e+09 | at_first_lit_instant | False | True | ok | ok | m2 | inserted |

## sweep_3: silo_cold_lag over ignition.stage1.startup.tau_s

| point | ignition.stage1.startup.tau_s | run_dir | of | paired_baseline | exit_speed_mps | payload_kg | payload_delta_kg | ideal_screening_payload_at_release_speed_at_pbase_kg | screening_yardstick_kg | payload_beyond_screening_kg | gamma_star_rad | speed_at_kick_mps | peak_q_alpha | delta_peak_q_alpha | max_q_pa | delta_max_q_pa | facility_length_m | drive_energy_J | drive_power_peak_W | kick_regime | unconstrained_kick | payload_delta_upper_bound | search_status | screening_status | screening_diagnostic_failed | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | sweep_3/run_0001 | silo_cold_lag | n/a | 76.7072 | 27553.2 | 1498.79 | 765.442 | 675.346 | 823.442 | 0.377801 | 71.8083 | 129.863 | 55.1325 | 31221.2 | -5970.23 | 160 | 2.24905e+09 | 1.72518e+09 | at_first_lit_instant | False | True | ok | ok | none | inserted |
| 2 | 2 | sweep_3/run_0002 | silo_cold_lag | n/a | 76.7072 | 27326.6 | 1272.23 | 765.442 | 675.346 | 596.88 | 0.380958 | 71.8083 | 92.1897 | 17.4589 | 31516.7 | -5674.69 | 160 | 2.24816e+09 | 1.7245e+09 | at_first_lit_instant | False | True | ok | ok | m2 | inserted |
| 3 | 3 | sweep_3/run_0003 | silo_cold_lag | n/a | 76.7072 | 27099.6 | 1045.17 | 765.442 | 675.346 | 369.824 | 0.38459 | 71.8083 | 61.2109 | -13.5199 | 31884.8 | -5306.57 | 160 | 2.24727e+09 | 1.72382e+09 | at_first_lit_instant | False | False | ok | ok | m2 | inserted |

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
- fairing (1700 kg): dropped when 0.5 rho |v_rel|^3 < 1135 W/m^2 [all runs]
- pad: held down to the release at t = 0 s; stage 1 lit at t = -2 s with a ramp startup, then clamped until its thrust exceeds its weight [pad]
- atmosphere: ICAO standard atmosphere closed forms (layer table of ambiance.CONST) from -5,004 m to 81,020 m geometric altitude; the geometric to geopotential conversion uses the ICAO radius 6,356,766 m, not R_E. [all runs]
- atmosphere: above 81,020 m an isothermal extension at 196.649 K with scale height 5,908 m (R_air T_top / g(h_top)); not US76 (denser near 110 km, far thinner above 150 km). [all runs]
- atmosphere: static, spherically symmetric, no wind; it co-rotates with Earth, so drag and Mach use the Earth-relative velocity v_rel. [all runs]
- atmosphere: in flight, an altitude below the -5,004 m floor is held at the floor state (ambient_scalar clamp; a dive ends at the ground event). [all runs]
- track phase: 1-DOF along the track in a flat local frame with constant g_eff; the carriage stays on the track at release; carriage braking is not modelled as a phase (its distance v^2/(2 a_brake) is added to the facility length) [all sweep points]
- hot start: the propellant burned before release is reported with its delta-v equivalent; the exhaust impingement fraction f_imp on the carriage is an assumed amendment to the track equation (the system keeps (1 - f_imp) T) [all sweep points]
- drive energy: electrical_energy = (positive drive work) / efficiency; no regeneration is credited for any negative (braking) drive work [all sweep points]
- track: straight, L = 50 m at 1.5708 rad above horizontal, start altitude -50 m (exit at 0 m) [sweep_1/run_0001, sweep_1/run_0004, sweep_1/run_0007, sweep_1/run_0010]
- constant_accel: prescribed net acceleration 0.5 g0 (assumed); drive force unconstrained, solved from the track equation [sweep_1/run_0001, sweep_1/run_0002, sweep_1/run_0003]
- constant_accel: carriage mass 0 t (assumed) [all sweep points]
- constant_accel: braking deceleration 5 g0 (assumed) [all sweep points]
- constant_accel: drive efficiency 0.5 (assumed) [all sweep points]
- constant_accel: exhaust impingement fraction 0 (assumed); the system keeps (1 - f_imp) T of the on-track thrust [all sweep points]
- constant_accel: shaft vented (no air column), no friction [all sweep points]
- constant_accel: constant g_eff = 9.772092 m/s^2 on the track (mu/R_E^2 - omega_p^2 R_E with omega_p = 6.408435e-05 rad/s, the planar rotation rate of the site), flat 1-DOF track frame, Coriolis neglected [all sweep points]
- constant_accel: infinite jerk at push start and release [all sweep points]
- constant_accel: vehicle clamped to the carriage during any hold before the push [all sweep points]
- track: straight, L = 100 m at 1.5708 rad above horizontal, start altitude -100 m (exit at 0 m) [sweep_1/run_0002, sweep_1/run_0005, sweep_1/run_0008, sweep_1/run_0011, sweep_2/run_0001, sweep_2/run_0002, sweep_2/run_0003, sweep_2/run_0004, sweep_2/run_0005, sweep_2/run_0006, sweep_2/run_0007, sweep_2/run_0008, sweep_2/run_0009, sweep_3/run_0001, sweep_3/run_0002, sweep_3/run_0003]
- track: straight, L = 300 m at 1.5708 rad above horizontal, start altitude -300 m (exit at 0 m) [sweep_1/run_0003, sweep_1/run_0006, sweep_1/run_0009, sweep_1/run_0012]
- constant_accel: prescribed net acceleration 1 g0 (assumed); drive force unconstrained, solved from the track equation [sweep_1/run_0004, sweep_1/run_0005, sweep_1/run_0006]
- constant_accel: prescribed net acceleration 3 g0 (assumed); drive force unconstrained, solved from the track equation [sweep_1/run_0007, sweep_1/run_0008, sweep_1/run_0009, sweep_2/run_0001, sweep_2/run_0002, sweep_2/run_0003, sweep_2/run_0004, sweep_2/run_0005, sweep_2/run_0006, sweep_2/run_0007, sweep_2/run_0008, sweep_2/run_0009, sweep_3/run_0001, sweep_3/run_0002, sweep_3/run_0003]
- constant_accel: prescribed net acceleration 5 g0 (assumed); drive force unconstrained, solved from the track equation [sweep_1/run_0010, sweep_1/run_0011, sweep_1/run_0012]

## Checks

- pad: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.45116e-08: ok
- sweep_1/run_0001: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.4442e-08: ok
- sweep_1/run_0002: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.39925e-08: ok
- sweep_1/run_0003: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36363e-08: ok
- sweep_1/run_0004: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.39927e-08: ok
- sweep_1/run_0005: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.3789e-08: ok
- sweep_1/run_0006: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35975e-08: ok
- sweep_1/run_0007: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36369e-08: ok
- sweep_1/run_0008: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35972e-08: ok
- sweep_1/run_0009: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.28372e-08: ok
- sweep_1/run_0010: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36977e-08: ok
- sweep_1/run_0011: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.32835e-08: ok
- sweep_1/run_0012: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.23681e-08: ok
- sweep_2/run_0001: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.3462e-08: ok
- sweep_2/run_0002: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35329e-08: ok
- sweep_2/run_0003: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36025e-08: ok
- sweep_2/run_0004: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.3528e-08: ok
- sweep_2/run_0005: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35972e-08: ok
- sweep_2/run_0006: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36704e-08: ok
- sweep_2/run_0007: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35921e-08: ok
- sweep_2/run_0008: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36652e-08: ok
- sweep_2/run_0009: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.37418e-08: ok
- sweep_3/run_0001: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35976e-08: ok
- sweep_3/run_0002: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.37468e-08: ok
- sweep_3/run_0003: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35997e-08: ok

- sweep_1/run_0001: screening status ok (failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: M4)
- sweep_1/run_0002: screening status ok (failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: M4)
- sweep_1/run_0003: screening status ok (failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: M2 (diagnostic))
- sweep_1/run_0004: screening status ok (failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: M4)
- sweep_1/run_0005: screening status ok (failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: none)
- sweep_1/run_0006: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_1/run_0007: screening status ok (failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: M2 (diagnostic))
- sweep_1/run_0008: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_1/run_0009: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_1/run_0010: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_1/run_0011: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_1/run_0012: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_2/run_0001: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_2/run_0002: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_2/run_0003: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_2/run_0004: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_2/run_0005: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_2/run_0006: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: M2 (diagnostic))
- sweep_2/run_0007: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_2/run_0008: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: M2 (diagnostic))
- sweep_2/run_0009: screening status ok (failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: M2 (diagnostic))
- sweep_3/run_0001: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_3/run_0002: screening status ok (failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: none)
- sweep_3/run_0003: screening status ok (failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: none)

No run and no comparison is bug_suspect.
Diagnostic checks that failed (computed and reported only: they give no bug_suspect and block no finding; user decision of 2026-09-30, docs/physics.md, 'Screening-beat rule (2-D)'): sweep_1/run_0001 (M2), sweep_1/run_0002 (M2), sweep_1/run_0003 (M2), sweep_1/run_0004 (M2), sweep_1/run_0005 (M2), sweep_1/run_0007 (M2), sweep_2/run_0009 (M2), sweep_3/run_0002 (M2), sweep_3/run_0003 (M2)
Checks whose verdict changes within the variant's gamma* +/- h (the gamma*-sensitivity step; the verdict at gamma*_ref stands as pre-registered, but the gravity and steering terms trade against each other with gamma*, so these verdicts are not robust): sweep_1/run_0001 (M4), sweep_1/run_0002 (M4), sweep_1/run_0003 (M2 (diagnostic)), sweep_1/run_0004 (M4), sweep_1/run_0007 (M2 (diagnostic)), sweep_2/run_0006 (M2 (diagnostic)), sweep_2/run_0008 (M2 (diagnostic)), sweep_2/run_0009 (M2 (diagnostic))
