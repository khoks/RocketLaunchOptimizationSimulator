# silo_offload_2d: sweeps

Comparison basis: sweep-optimized (every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, delta and the LTG pair are solved per run); planar_2d: rotating spherical Earth, ICAO atmosphere, drag, back-pressure, unthrottled; figure of merit: payload capacity P* at the target orbit

Guidance is sweep-optimized: every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, the kick angle delta and the LTG pair (a, b) are solved per run. Not an optimal-control solution (Phase 5).

- Baseline: pad (status inserted)
- Timestamp (UTC): 20261003T112949Z
- Git: b3150c1754ee

## sweep_1: silo_cold over assist.stroke_m

| point | assist.stroke_m | run_dir | of | paired_baseline | exit_speed_mps | payload_kg | payload_delta_kg | ideal_screening_payload_at_release_speed_at_pbase_kg | screening_yardstick_kg | payload_beyond_screening_kg | gamma_star_rad | speed_at_kick_mps | peak_q_alpha | delta_peak_q_alpha | max_q_pa | delta_max_q_pa | facility_length_m | drive_energy_J | drive_power_peak_W | kick_regime | unconstrained_kick | payload_delta_upper_bound | search_status | screening_status | screening_diagnostic_failed | silo_cold_s1.status | silo_cold_s1.offload_kg | silo_cold_s1.stage1_fraction | silo_cold_s1.total_fraction | silo_cold_s1.reference_payload_kg | silo_cold_s1.payload_kg | silo_cold_s1.payload_delta_kg | silo_cold_s1.verification_delta_kg | silo_cold_s1.decomposition_status | silo_cold_s1.screening_ratio | silo_cold_s1.max_q_pa | silo_cold_s1.electrical_energy_J | silo_cold_s1.solve_gamma_star_rad | silo_cold_s1.n_flags | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 25 | sweep_1/run_0001 | silo_cold | n/a | 38.3536 | 26674.7 | 620.349 | 380.086 | 335.388 | 284.961 | 0.391233 | 50 | 58.8981 | -15.8327 | 34171 | -3020.34 | 40 | 5.61401e+08 | 8.6127e+08 | after_vertical_rise | False | False | ok | ok | m2 | ok | 18765.1 | 0.0456684 | 0.0361982 | 26054.4 | 26054.4 | 0 | 0.00830587 | explained | 2.48942 | 37264.5 | 1.08481e+09 | 0.400947 | 0 | inserted |
| 2 | 50 | sweep_1/run_0002 | silo_cold | n/a | 54.2402 | 27041.9 | 987.495 | 539.061 | 475.645 | 511.851 | 0.385584 | 50 | 49.4442 | -25.2867 | 32764.8 | -4426.54 | 80 | 1.12352e+09 | 1.2188e+09 | after_vertical_rise | False | False | ok | ok | m2 | ok | 28653.6 | 0.0697337 | 0.0552731 | 26054.4 | 26054.4 | 0 | 0.00618235 | explained | 2.69526 | 37614.8 | 2.13087e+09 | 0.40107 | 0 | inserted |
| 3 | 100 | sweep_1/run_0003 | silo_cold | n/a | 76.7072 | 27553.2 | 1498.83 | 765.442 | 675.346 | 823.485 | 0.377803 | 71.8083 | 129.916 | 55.1852 | 31237.6 | -5953.74 | 160 | 2.24905e+09 | 1.72518e+09 | at_first_lit_instant | False | True | ok | ok | none | ok | 41262.9 | 0.100421 | 0.0795967 | 26054.4 | 26054.4 | 0 | 0.00845215 | explained | 2.75516 | 38438.5 | 4.16291e+09 | 0.401188 | 0 | inserted |
| 4 | 200 | sweep_1/run_0004 | silo_cold | n/a | 108.48 | 28261.9 | 2207.47 | 1088.73 | 960.488 | 1246.98 | 0.367746 | 103.569 | 574.085 | 499.354 | 29887.4 | -7303.94 | 320 | 4.50365e+09 | 2.44279e+09 | at_first_lit_instant | False | True | ok | ok | none | ok | 56827.2 | 0.138299 | 0.10962 | 26054.4 | 26054.4 | 0 | 0.672381 | explained | 2.69774 | 40201.2 | 8.08183e+09 | 0.398794 | 0 | inserted |
| 5 | 300 | sweep_1/run_0005 | silo_cold | n/a | 132.861 | 28794.5 | 2740.13 | 1339.33 | 1181.47 | 1558.66 | 0.360578 | 127.937 | 1293.3 | 1218.57 | 29410.9 | -7780.47 | 480 | 6.76174e+09 | 2.99456e+09 | at_first_lit_instant | True | True | ok | ok | none | ok | 67285.8 | 0.163752 | 0.129795 | 26054.4 | 26054.4 | 0 | 0.722248 | explained | 2.61902 | 41845.8 | 1.18768e+10 | 0.399415 | 0 | inserted |

## sweep_2: silo_cold_200m over assist.stroke_m

| point | assist.stroke_m | run_dir | of | paired_baseline | exit_speed_mps | payload_kg | payload_delta_kg | ideal_screening_payload_at_release_speed_at_pbase_kg | screening_yardstick_kg | payload_beyond_screening_kg | gamma_star_rad | speed_at_kick_mps | peak_q_alpha | delta_peak_q_alpha | max_q_pa | delta_max_q_pa | facility_length_m | drive_energy_J | drive_power_peak_W | kick_regime | unconstrained_kick | payload_delta_upper_bound | search_status | screening_status | screening_diagnostic_failed | silo_cold_200m_s1.status | silo_cold_200m_s1.offload_kg | silo_cold_200m_s1.stage1_fraction | silo_cold_200m_s1.total_fraction | silo_cold_200m_s1.reference_payload_kg | silo_cold_200m_s1.payload_kg | silo_cold_200m_s1.payload_delta_kg | silo_cold_200m_s1.verification_delta_kg | silo_cold_200m_s1.decomposition_status | silo_cold_200m_s1.screening_ratio | silo_cold_200m_s1.max_q_pa | silo_cold_200m_s1.electrical_energy_J | silo_cold_200m_s1.solve_gamma_star_rad | silo_cold_200m_s1.n_flags | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 50 | sweep_2/run_0001 | silo_cold_200m | n/a | 76.7072 | 27553.2 | 1498.83 | 765.442 | 675.346 | 823.485 | 0.377803 | 71.8083 | 129.916 | 55.1852 | 31237.6 | -5953.74 | 110 | 1.96866e+09 | 3.02021e+09 | at_first_lit_instant | False | True | ok | ok | none | ok | 41263 | 0.100421 | 0.0795968 | 26054.4 | 26054.4 | 0 | 0.00516445 | explained | 2.75516 | 38437.4 | 3.64392e+09 | 0.401248 | 0 | inserted |
| 2 | 100 | sweep_2/run_0002 | silo_cold_200m | n/a | 76.7072 | 27553.2 | 1498.83 | 765.442 | 675.346 | 823.485 | 0.377804 | 71.8083 | 129.916 | 55.185 | 31237.6 | -5953.75 | 160 | 2.24905e+09 | 1.72518e+09 | at_first_lit_instant | False | True | ok | ok | none | ok | 41263 | 0.100421 | 0.0795968 | 26054.4 | 26054.4 | 0 | 0.00595928 | explained | 2.75516 | 38437.4 | 4.16291e+09 | 0.401246 | 0 | inserted |
| 3 | 200 | sweep_2/run_0003 | silo_cold_200m | n/a | 76.7072 | 27553.2 | 1498.83 | 765.442 | 675.346 | 823.485 | 0.377803 | 71.8083 | 129.916 | 55.1851 | 31237.6 | -5953.74 | 260 | 2.80982e+09 | 1.07767e+09 | at_first_lit_instant | False | True | ok | ok | none | ok | 41263 | 0.100421 | 0.0795968 | 26054.4 | 26054.4 | 0 | 0.00599645 | explained | 2.75516 | 38437.4 | 5.20089e+09 | 0.401245 | 0 | inserted |
| 4 | 300 | sweep_2/run_0004 | silo_cold_200m | n/a | 76.7072 | 27553.2 | 1498.83 | 765.442 | 675.346 | 823.485 | 0.377804 | 71.8083 | 129.916 | 55.185 | 31237.6 | -5953.75 | 360 | 3.3706e+09 | 8.6183e+08 | at_first_lit_instant | False | True | ok | ok | none | ok | 41262.9 | 0.100421 | 0.0795967 | 26054.4 | 26054.4 | 0 | 0.00880487 | explained | 2.75516 | 38438.5 | 6.23886e+09 | 0.401188 | 0 | inserted |

## sweep_3: silo_cold over ignition.stage1.at_depth_m

| point | ignition.stage1.at_depth_m | run_dir | of | paired_baseline | exit_speed_mps | payload_kg | payload_delta_kg | ideal_screening_payload_at_release_speed_at_pbase_kg | screening_yardstick_kg | payload_beyond_screening_kg | gamma_star_rad | speed_at_kick_mps | peak_q_alpha | delta_peak_q_alpha | max_q_pa | delta_max_q_pa | facility_length_m | drive_energy_J | drive_power_peak_W | kick_regime | unconstrained_kick | payload_delta_upper_bound | search_status | screening_status | screening_diagnostic_failed | silo_cold_s1.status | silo_cold_s1.offload_kg | silo_cold_s1.stage1_fraction | silo_cold_s1.total_fraction | silo_cold_s1.reference_payload_kg | silo_cold_s1.payload_kg | silo_cold_s1.payload_delta_kg | silo_cold_s1.verification_delta_kg | silo_cold_s1.decomposition_status | silo_cold_s1.screening_ratio | silo_cold_s1.max_q_pa | silo_cold_s1.electrical_energy_J | silo_cold_s1.solve_gamma_star_rad | silo_cold_s1.n_flags | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 100 | sweep_3/run_0001 | silo_cold | n/a | 76.7072 | 27731.7 | 1677.33 | 765.442 | 675.346 | 1001.98 | 0.375323 | 76.7072 | 234.884 | 160.153 | 31633.9 | -5557.45 | 160 | 1.64151e+09 | 1.12919e+09 | at_first_lit_instant | False | True | ok | ok | none | ok | 44375.2 | 0.107995 | 0.0856004 | 26054.4 | 26054.4 | 0 | 0.0087446 | explained | 2.96297 | 39712.6 | 2.92205e+09 | 0.401494 | 0 | inserted |
| 2 | 75 | sweep_3/run_0002 | silo_cold | n/a | 76.7072 | 27814.1 | 1759.69 | 765.442 | 675.346 | 1084.35 | 0.374077 | 76.7072 | 218.949 | 144.218 | 31142.4 | -6049.02 | 160 | 2.06997e+09 | 1.35874e+09 | at_first_lit_instant | False | True | ok | ok | none | ok | 46958.5 | 0.114282 | 0.0905835 | 26054.4 | 26054.4 | 0 | 0.00872671 | explained | 3.13546 | 39596.5 | 3.75806e+09 | 0.401464 | 0 | inserted |
| 3 | 50 | sweep_3/run_0003 | silo_cold | n/a | 76.7072 | 27780.9 | 1726.5 | 765.442 | 675.346 | 1051.16 | 0.374529 | 76.7072 | 203.03 | 128.3 | 31061.9 | -6129.49 | 160 | 2.19504e+09 | 1.53129e+09 | at_first_lit_instant | False | True | ok | ok | none | ok | 46393.8 | 0.112908 | 0.0894942 | 26054.4 | 26054.4 | 0 | 0.00866982 | explained | 3.09775 | 39351.6 | 4.01289e+09 | 0.401403 | 0 | inserted |
| 4 | 25 | sweep_3/run_0004 | silo_cold | n/a | 76.7072 | 27723.7 | 1669.3 | 765.442 | 675.346 | 993.952 | 0.375289 | 76.7072 | 186.823 | 112.092 | 31068.6 | -6122.77 | 160 | 2.24363e+09 | 1.66279e+09 | at_first_lit_instant | False | True | ok | ok | none | ok | 45170.2 | 0.10993 | 0.0871339 | 26054.4 | 26054.4 | 0 | 0.00606383 | explained | 3.01605 | 39080.8 | 4.1201e+09 | 0.401396 | 0 | inserted |
| 5 | 0 | sweep_3/run_0005 | silo_cold | n/a | 76.7072 | 27655.7 | 1601.29 | 765.442 | 675.346 | 925.941 | 0.376248 | 76.7072 | 170.942 | 96.2116 | 31125.1 | -6066.31 | 160 | 2.24945e+09 | 1.72549e+09 | at_first_lit_instant | False | True | ok | ok | none | ok | 43631.2 | 0.106185 | 0.0841652 | 26054.4 | 26054.4 | 0 | 0.00849604 | explained | 2.91329 | 38813.2 | 4.14435e+09 | 0.401275 | 0 | inserted |

## sweep_4: silo_cold over ignition.stage1.at_height_m, ignition.stage1.height_method

| point | ignition.stage1.at_height_m | ignition.stage1.height_method | run_dir | of | paired_baseline | exit_speed_mps | payload_kg | payload_delta_kg | ideal_screening_payload_at_release_speed_at_pbase_kg | screening_yardstick_kg | payload_beyond_screening_kg | gamma_star_rad | speed_at_kick_mps | peak_q_alpha | delta_peak_q_alpha | max_q_pa | delta_max_q_pa | facility_length_m | drive_energy_J | drive_power_peak_W | kick_regime | unconstrained_kick | payload_delta_upper_bound | search_status | screening_status | screening_diagnostic_failed | silo_cold_s1.status | silo_cold_s1.offload_kg | silo_cold_s1.stage1_fraction | silo_cold_s1.total_fraction | silo_cold_s1.reference_payload_kg | silo_cold_s1.payload_kg | silo_cold_s1.payload_delta_kg | silo_cold_s1.verification_delta_kg | silo_cold_s1.decomposition_status | silo_cold_s1.screening_ratio | silo_cold_s1.max_q_pa | silo_cold_s1.electrical_energy_J | silo_cold_s1.solve_gamma_star_rad | silo_cold_s1.n_flags | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 10 | event | sweep_4/run_0001 | silo_cold | n/a | 76.7072 | 27628.8 | 1574.42 | 765.442 | 675.346 | 899.07 | 0.376656 | 75.4189 | 159.35 | 84.6192 | 31152 | -6039.42 | 160 | 2.24934e+09 | 1.72541e+09 | at_first_lit_instant | False | True | ok | ok | none | ok | 43014.8 | 0.104684 | 0.082976 | 26054.4 | 26054.4 | 0 | 0.00599382 | explained | 2.87213 | 38711.1 | 4.14918e+09 | 0.401309 | 0 | inserted |
| 2 | 40 | event | sweep_4/run_0002 | silo_cold | n/a | 76.7072 | 27545 | 1490.58 | 765.442 | 675.346 | 815.238 | 0.37792 | 71.4156 | 126.975 | 52.2445 | 31248 | -5943.39 | 160 | 2.24902e+09 | 1.72516e+09 | at_first_lit_instant | False | True | ok | ok | none | ok | 41070.2 | 0.0999519 | 0.079225 | 26054.4 | 26054.4 | 0 | 0.00589625 | explained | 2.74229 | 38408.4 | 4.16442e+09 | 0.401241 | 0 | inserted |
| 3 | 100 | event | sweep_4/run_0003 | silo_cold | n/a | 76.7072 | 27359.7 | 1305.27 | 765.442 | 675.346 | 629.925 | 0.380491 | 62.6501 | 73.1988 | -1.53203 | 31528.2 | -5663.2 | 160 | 2.24829e+09 | 1.7246e+09 | at_first_lit_instant | False | False | ok | ok | m2 | ok | 36655.6 | 0.089208 | 0.070709 | 26054.4 | 26054.4 | 0 | 0.0057835 | explained | 2.44752 | 37805.8 | 4.19903e+09 | 0.40111 | 0 | inserted |
| 4 | 200 | event | sweep_4/run_0004 | silo_cold | n/a | 76.7072 | 26964.6 | 910.213 | 765.442 | 675.346 | 234.868 | 0.386639 | 50 | 53.1085 | -21.6224 | 32420.8 | -4770.55 | 160 | 2.24674e+09 | 1.72341e+09 | after_vertical_rise | False | False | ok | ok | m2 | ok | 26664.4 | 0.0648927 | 0.051436 | 26054.4 | 26054.4 | 0 | 0.00856899 | explained | 1.7804 | 36823.9 | 4.27734e+09 | 0.400866 | 0 | inserted |

## sweep_5: silo_cold over ignition.stage1.at_height_m, ignition.stage1.height_method

| point | ignition.stage1.at_height_m | ignition.stage1.height_method | run_dir | of | paired_baseline | exit_speed_mps | payload_kg | payload_delta_kg | ideal_screening_payload_at_release_speed_at_pbase_kg | screening_yardstick_kg | payload_beyond_screening_kg | gamma_star_rad | speed_at_kick_mps | peak_q_alpha | delta_peak_q_alpha | max_q_pa | delta_max_q_pa | facility_length_m | drive_energy_J | drive_power_peak_W | kick_regime | unconstrained_kick | payload_delta_upper_bound | search_status | screening_status | screening_diagnostic_failed | silo_cold_s1.status | silo_cold_s1.offload_kg | silo_cold_s1.stage1_fraction | silo_cold_s1.total_fraction | silo_cold_s1.reference_payload_kg | silo_cold_s1.payload_kg | silo_cold_s1.payload_delta_kg | silo_cold_s1.verification_delta_kg | silo_cold_s1.decomposition_status | silo_cold_s1.screening_ratio | silo_cold_s1.max_q_pa | silo_cold_s1.electrical_energy_J | silo_cold_s1.solve_gamma_star_rad | silo_cold_s1.n_flags | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 40 | closed_form | sweep_5/run_0001 | silo_cold | n/a | 76.7072 | 27545 | 1490.6 | 765.442 | 675.346 | 815.249 | 0.377921 | 71.4161 | 126.979 | 52.2483 | 31248 | -5943.42 | 160 | 2.24902e+09 | 1.72516e+09 | at_first_lit_instant | False | True | ok | ok | none | ok | 41070.5 | 0.0999524 | 0.0792254 | 26054.4 | 26054.4 | 0 | 0.00877127 | explained | 2.74231 | 38409.6 | 4.16442e+09 | 0.401182 | 0 | inserted |
| 2 | 200 | closed_form | sweep_5/run_0002 | silo_cold | n/a | 76.7072 | 26965.1 | 910.749 | 765.442 | 675.346 | 235.403 | 0.386638 | 50 | 53.0933 | -21.6375 | 32419.2 | -4772.14 | 160 | 2.24674e+09 | 1.72341e+09 | after_vertical_rise | False | False | ok | ok | m2 | ok | 26679.3 | 0.0649289 | 0.0514647 | 26054.4 | 26054.4 | 0 | 0.00565082 | explained | 1.7814 | 36824 | 4.27722e+09 | 0.400926 | 0 | inserted |

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
- track: straight, L = 25 m at 1.5708 rad above horizontal, start altitude -25 m (exit at 0 m) [sweep_1/run_0001]
- constant_accel: prescribed net acceleration 3 g0 (assumed); drive force unconstrained, solved from the track equation [sweep_1/run_0001, sweep_1/run_0002, sweep_1/run_0003, sweep_1/run_0004, sweep_1/run_0005, sweep_2/run_0002, sweep_3/run_0001, sweep_3/run_0002, sweep_3/run_0003, sweep_3/run_0004, sweep_3/run_0005, sweep_4/run_0001, sweep_4/run_0002, sweep_4/run_0003, sweep_4/run_0004, sweep_5/run_0001, sweep_5/run_0002]
- constant_accel: carriage mass 0 t (assumed) [all sweep points]
- constant_accel: braking deceleration 5 g0 (assumed) [all sweep points]
- constant_accel: drive efficiency 0.5 (assumed) [all sweep points]
- constant_accel: exhaust impingement fraction 0 (assumed); the system keeps (1 - f_imp) T of the on-track thrust [all sweep points]
- constant_accel: shaft vented (no air column), no friction [all sweep points]
- constant_accel: constant g_eff = 9.772092 m/s^2 on the track (mu/R_E^2 - omega_p^2 R_E with omega_p = 6.408435e-05 rad/s, the planar rotation rate of the site), flat 1-DOF track frame, Coriolis neglected [all sweep points]
- constant_accel: infinite jerk at push start and release [all sweep points]
- constant_accel: vehicle clamped to the carriage during any hold before the push [all sweep points]
- track: straight, L = 50 m at 1.5708 rad above horizontal, start altitude -50 m (exit at 0 m) [sweep_1/run_0002, sweep_2/run_0001]
- track: straight, L = 100 m at 1.5708 rad above horizontal, start altitude -100 m (exit at 0 m) [sweep_1/run_0003, sweep_2/run_0002, sweep_3/run_0001, sweep_3/run_0002, sweep_3/run_0003, sweep_3/run_0004, sweep_3/run_0005, sweep_4/run_0001, sweep_4/run_0002, sweep_4/run_0003, sweep_4/run_0004, sweep_5/run_0001, sweep_5/run_0002]
- track: straight, L = 200 m at 1.5708 rad above horizontal, start altitude -200 m (exit at 0 m) [sweep_1/run_0004, sweep_2/run_0003]
- track: straight, L = 300 m at 1.5708 rad above horizontal, start altitude -300 m (exit at 0 m) [sweep_1/run_0005, sweep_2/run_0004]
- constant_accel: prescribed net acceleration 6 g0 (assumed); drive force unconstrained, solved from the track equation [sweep_2/run_0001]
- constant_accel: the net acceleration is derived from the configured exit speed 76.7072 m/s (assumed) and the track length L, a = v_exit^2 / (2 L); the push time is 2 L / v_exit [sweep_2/run_0001, sweep_2/run_0002, sweep_2/run_0003, sweep_2/run_0004]
- constant_accel: prescribed net acceleration 1.5 g0 (assumed); drive force unconstrained, solved from the track equation [sweep_2/run_0003]
- constant_accel: prescribed net acceleration 1 g0 (assumed); drive force unconstrained, solved from the track equation [sweep_2/run_0004]
- ramp start: stage-1 ignition stated by depth 100 m below the track exit, converted before the run to t_ign = 0 s after push start by t = sqrt(2 (L - d) / a) (exact for the prescribed acceleration) [sweep_3/run_0001]
- ramp start: stage-1 ignition stated by depth 75 m below the track exit, converted before the run to t_ign = 1.30365909 s after push start by t = sqrt(2 (L - d) / a) (exact for the prescribed acceleration) [sweep_3/run_0002]
- ramp start: stage-1 ignition stated by depth 50 m below the track exit, converted before the run to t_ign = 1.84365237 s after push start by t = sqrt(2 (L - d) / a) (exact for the prescribed acceleration) [sweep_3/run_0003]
- ramp start: stage-1 ignition stated by depth 25 m below the track exit, converted before the run to t_ign = 2.25800378 s after push start by t = sqrt(2 (L - d) / a) (exact for the prescribed acceleration) [sweep_3/run_0004]
- ramp start: stage-1 ignition stated by depth 0 m below the track exit, converted before the run to t_ign = 0 s after release by t = sqrt(2 (L - d) / a) (exact for the prescribed acceleration) [sweep_3/run_0005]
- ramp start: stage-1 ignition stated by height 10 m above the track exit, reached by an altitude event: nothing is converted before the run; stage 1 lights at the root where the flown coast after release (mu/r^2, and on planar_2d drag and rotation) crosses that height upward (an apex below it is a failure, not an ignition) [sweep_4/run_0001]
- ramp start: stage-1 ignition stated by height 40 m above the track exit, reached by an altitude event: nothing is converted before the run; stage 1 lights at the root where the flown coast after release (mu/r^2, and on planar_2d drag and rotation) crosses that height upward (an apex below it is a failure, not an ignition) [sweep_4/run_0002]
- ramp start: stage-1 ignition stated by height 100 m above the track exit, reached by an altitude event: nothing is converted before the run; stage 1 lights at the root where the flown coast after release (mu/r^2, and on planar_2d drag and rotation) crosses that height upward (an apex below it is a failure, not an ignition) [sweep_4/run_0003]
- ramp start: stage-1 ignition stated by height 200 m above the track exit, reached by an altitude event: nothing is converted before the run; stage 1 lights at the root where the flown coast after release (mu/r^2, and on planar_2d drag and rotation) crosses that height upward (an apex below it is a failure, not an ignition) [sweep_4/run_0004]
- ramp start: stage-1 ignition stated by height 40 m above the track exit, converted before the run to t_ign = 0.540040584 s after release by the closed form of a drag-free coast at the track's constant g_eff = 9.772092 m/s^2, dt = (v_e - sqrt(v_e^2 - 2 g_eff h)) / g_eff; the flown coast (mu/r^2, and on planar_2d drag and rotation) reaches a slightly different height, which the ignition event records [sweep_5/run_0001]
- ramp start: stage-1 ignition stated by height 200 m above the track exit, converted before the run to t_ign = 3.30169573 s after release by the closed form of a drag-free coast at the track's constant g_eff = 9.772092 m/s^2, dt = (v_e - sqrt(v_e^2 - 2 g_eff h)) / g_eff; the flown coast (mu/r^2, and on planar_2d drag and rotation) reaches a slightly different height, which the ignition event records [sweep_5/run_0002]

## Checks

- pad: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.45116e-08: ok
- sweep_1/run_0001: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.38822e-08: ok
- sweep_1/run_0002: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36369e-08: ok
- sweep_1/run_0003: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35972e-08: ok
- sweep_1/run_0004: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.31566e-08: ok
- sweep_1/run_0005: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.28372e-08: ok
- sweep_1/run_0001__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_1/run_0001__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.41859e-08: ok
- sweep_1/run_0002__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_1/run_0002__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.39164e-08: ok
- sweep_1/run_0003__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_1/run_0003__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36282e-08: ok
- sweep_1/run_0004__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_1/run_0004__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.32428e-08: ok
- sweep_1/run_0005__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_1/run_0005__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.29521e-08: ok
- sweep_2/run_0001: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35972e-08: ok
- sweep_2/run_0002: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35972e-08: ok
- sweep_2/run_0003: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35974e-08: ok
- sweep_2/run_0004: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35968e-08: ok
- sweep_2/run_0001__silo_cold_200m_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_2/run_0001__silo_cold_200m_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36427e-08: ok
- sweep_2/run_0002__silo_cold_200m_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_2/run_0002__silo_cold_200m_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36438e-08: ok
- sweep_2/run_0003__silo_cold_200m_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_2/run_0003__silo_cold_200m_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36408e-08: ok
- sweep_2/run_0004__silo_cold_200m_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_2/run_0004__silo_cold_200m_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36408e-08: ok
- sweep_3/run_0001: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.3392e-08: ok
- sweep_3/run_0002: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.34089e-08: ok
- sweep_3/run_0003: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.34454e-08: ok
- sweep_3/run_0004: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.34886e-08: ok
- sweep_3/run_0005: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35329e-08: ok
- sweep_3/run_0001__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_3/run_0001__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.34455e-08: ok
- sweep_3/run_0002__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_3/run_0002__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual -1.90357e-09 m/s, insertion e 1.34804e-08: ok
- sweep_3/run_0003__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_3/run_0003__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.34639e-08: ok
- sweep_3/run_0004__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_3/run_0004__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35403e-08: ok
- sweep_3/run_0005__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_3/run_0005__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35871e-08: ok
- sweep_4/run_0001: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35503e-08: ok
- sweep_4/run_0002: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36033e-08: ok
- sweep_4/run_0003: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.37274e-08: ok
- sweep_4/run_0004: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.3694e-08: ok
- sweep_4/run_0001__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_4/run_0001__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35964e-08: ok
- sweep_4/run_0002__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_4/run_0002__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36522e-08: ok
- sweep_4/run_0003__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_4/run_0003__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36499e-08: ok
- sweep_4/run_0004__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_4/run_0004__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.39788e-08: ok
- sweep_5/run_0001: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36027e-08: ok
- sweep_5/run_0002: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36937e-08: ok
- sweep_5/run_0001__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_5/run_0001__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36432e-08: ok
- sweep_5/run_0002__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_5/run_0002__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.39801e-08: ok

- sweep_1/run_0001: screening status ok (failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: none)
- sweep_1/run_0002: screening status ok (failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: M2 (diagnostic))
- sweep_1/run_0003: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_1/run_0004: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_1/run_0005: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_2/run_0001: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_2/run_0002: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_2/run_0003: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_2/run_0004: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_3/run_0001: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_3/run_0002: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_3/run_0003: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_3/run_0004: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_3/run_0005: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_4/run_0001: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_4/run_0002: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_4/run_0003: screening status ok (failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: M2 (diagnostic))
- sweep_4/run_0004: screening status ok (failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: M4)
- sweep_5/run_0001: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_5/run_0002: screening status ok (failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: M4)

Offload checks (the screening rule for offload rows: an offload beyond the ideal screening estimate is explained only by a decomposition that closes, else bug_suspect; offload rows never enter the unexplained-beats list):
- sweep_1/run_0001 silo_cold_s1 offload decomposition: explained
- sweep_1/run_0002 silo_cold_s1 offload decomposition: explained
- sweep_1/run_0003 silo_cold_s1 offload decomposition: explained
- sweep_1/run_0004 silo_cold_s1 offload decomposition: explained
- sweep_1/run_0005 silo_cold_s1 offload decomposition: explained
- sweep_2/run_0001 silo_cold_200m_s1 offload decomposition: explained
- sweep_2/run_0002 silo_cold_200m_s1 offload decomposition: explained
- sweep_2/run_0003 silo_cold_200m_s1 offload decomposition: explained
- sweep_2/run_0004 silo_cold_200m_s1 offload decomposition: explained
- sweep_3/run_0001 silo_cold_s1 offload decomposition: explained
- sweep_3/run_0002 silo_cold_s1 offload decomposition: explained
- sweep_3/run_0003 silo_cold_s1 offload decomposition: explained
- sweep_3/run_0004 silo_cold_s1 offload decomposition: explained
- sweep_3/run_0005 silo_cold_s1 offload decomposition: explained
- sweep_4/run_0001 silo_cold_s1 offload decomposition: explained
- sweep_4/run_0002 silo_cold_s1 offload decomposition: explained
- sweep_4/run_0003 silo_cold_s1 offload decomposition: explained
- sweep_4/run_0004 silo_cold_s1 offload decomposition: explained
- sweep_5/run_0001 silo_cold_s1 offload decomposition: explained
- sweep_5/run_0002 silo_cold_s1 offload decomposition: explained

Offload flags at each point (the case record's: its solve's and its recorded run's; sweep_index.csv gives their number, `<case>.n_flags`, beside the solve's gamma*_ref, `<case>.solve_gamma_star_rad`):
- sweep_1/run_0001 silo_cold_s1 offload flags: none
- sweep_1/run_0002 silo_cold_s1 offload flags: none
- sweep_1/run_0003 silo_cold_s1 offload flags: none
- sweep_1/run_0004 silo_cold_s1 offload flags: none
- sweep_1/run_0005 silo_cold_s1 offload flags: none
- sweep_2/run_0001 silo_cold_200m_s1 offload flags: none
- sweep_2/run_0002 silo_cold_200m_s1 offload flags: none
- sweep_2/run_0003 silo_cold_200m_s1 offload flags: none
- sweep_2/run_0004 silo_cold_200m_s1 offload flags: none
- sweep_3/run_0001 silo_cold_s1 offload flags: none
- sweep_3/run_0002 silo_cold_s1 offload flags: none
- sweep_3/run_0003 silo_cold_s1 offload flags: none
- sweep_3/run_0004 silo_cold_s1 offload flags: none
- sweep_3/run_0005 silo_cold_s1 offload flags: none
- sweep_4/run_0001 silo_cold_s1 offload flags: none
- sweep_4/run_0002 silo_cold_s1 offload flags: none
- sweep_4/run_0003 silo_cold_s1 offload flags: none
- sweep_4/run_0004 silo_cold_s1 offload flags: none
- sweep_5/run_0001 silo_cold_s1 offload flags: none
- sweep_5/run_0002 silo_cold_s1 offload flags: none

No run and no comparison is bug_suspect.
Diagnostic checks that failed (computed and reported only: they give no bug_suspect and block no finding; user decision of 2026-09-30, docs/physics.md, 'Screening-beat rule (2-D)'): sweep_1/run_0001 (M2), sweep_1/run_0002 (M2), sweep_4/run_0003 (M2), sweep_4/run_0004 (M2), sweep_5/run_0002 (M2)
Checks whose verdict changes within the variant's gamma* +/- h (the gamma*-sensitivity step; the verdict at gamma*_ref stands as pre-registered, but the gravity and steering terms trade against each other with gamma*, so these verdicts are not robust): sweep_1/run_0002 (M2 (diagnostic)), sweep_4/run_0003 (M2 (diagnostic)), sweep_4/run_0004 (M4), sweep_5/run_0002 (M4)
