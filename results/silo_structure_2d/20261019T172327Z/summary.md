# silo_structure_2d: sweeps

Comparison basis: sweep-optimized (every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, delta and the LTG pair are solved per run); planar_2d: rotating spherical Earth, ICAO atmosphere, drag, back-pressure, unthrottled; figure of merit: payload capacity P* at the target orbit

Guidance is sweep-optimized: every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, the kick angle delta and the LTG pair (a, b) are solved per run. Not an optimal-control solution (Phase 5).

- Baseline: pad (status inserted)
- Timestamp (UTC): 20261019T172327Z
- Git: 2b343d7f25eb-dirty

## sweep_1: silo_cold over assist.stroke_m

| point | assist.stroke_m | run_dir | of | paired_baseline | exit_speed_mps | payload_kg | payload_delta_kg | ideal_screening_payload_at_release_speed_at_pbase_kg | screening_yardstick_kg | payload_beyond_screening_kg | gamma_star_rad | speed_at_kick_mps | peak_q_alpha | delta_peak_q_alpha | max_q_pa | delta_max_q_pa | facility_length_m | drive_energy_J | drive_power_peak_W | kick_regime | unconstrained_kick | payload_delta_upper_bound | search_status | screening_status | screening_diagnostic_failed | silo_cold_s1.status | silo_cold_s1.offload_kg | silo_cold_s1.stage1_fraction | silo_cold_s1.total_fraction | silo_cold_s1.reference_payload_kg | silo_cold_s1.payload_kg | silo_cold_s1.payload_delta_kg | silo_cold_s1.verification_delta_kg | silo_cold_s1.decomposition_status | silo_cold_s1.screening_ratio | silo_cold_s1.max_q_pa | silo_cold_s1.electrical_energy_J | silo_cold_s1.solve_gamma_star_rad | silo_cold_s1.n_flags | silo_cold_s1.dv_shortfall_mps | silo_cold_s1_st.status | silo_cold_s1_st.offload_kg | silo_cold_s1_st.stage1_fraction | silo_cold_s1_st.total_fraction | silo_cold_s1_st.reference_payload_kg | silo_cold_s1_st.payload_kg | silo_cold_s1_st.payload_delta_kg | silo_cold_s1_st.verification_delta_kg | silo_cold_s1_st.decomposition_status | silo_cold_s1_st.screening_ratio | silo_cold_s1_st.max_q_pa | silo_cold_s1_st.electrical_energy_J | silo_cold_s1_st.solve_gamma_star_rad | silo_cold_s1_st.n_flags | silo_cold_s1_st.dv_shortfall_mps | silo_cold_s1_st.structure_set | silo_cold_s1_st.structure_sizing | silo_cold_s1_st.structure_dynamic | silo_cold_s1_st.structure_entry | silo_cold_s1_st.structure_margin | silo_cold_s1_st.structure_cap_g | silo_cold_s1_st.structure_dm_kg | silo_cold_s1_st.structure_dm_stage2_kg | silo_cold_s1_st.structure_dm_x0_kg | silo_cold_s1_st.structure_dlf | silo_cold_s1_st.structure_n_peak_g | silo_cold_s1_st.structure_F_peak_N | silo_cold_s1_st.structure_ramp_cost_rel | silo_cold_s1_st.structure_plausibility_factor | silo_cold_s1_st.structure_flags | silo_cold_s1_st.structure_plausibility_scaled | silo_cold_s1_st.structure_overrides | silo_cold_s1_st.structure_plausibility_ratio | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 25 | sweep_1/run_0001 | silo_cold | n/a | 38.3536 | 26674.7 | 620.349 | 380.086 | 335.388 | 284.961 | 0.391233 | 50 | 58.8981 | -15.8327 | 34171 | -3020.34 | 40 | 5.61401e+08 | 8.6127e+08 | after_vertical_rise | False | False | ok | ok | m2 | ok | 18765.1 | 0.0456684 | 0.0361982 | 26054.4 | 26054.4 | 0 | 0.00830587 | explained | 2.48942 | 37264.5 | 1.08481e+09 | 0.400947 | 0 | n/a | no_offload | 0 | 0 | 0 | 26054.4 | 26054.4 | 0 | n/a | explained | 0 | 33133.7 | 1.13438e+09 | 0.405789 | 2 | 60.2313 | central | flown | rise_time | aft_ring | 0 | n/a | 6526.53 | 0 | 6526.53 | 1.12732 | 4.42095 | 2.50972e+07 | 0.0125684 | n/a | structure_release_unload; structure_payload_limit | False | none | 1.75905 | inserted |
| 2 | 50 | sweep_1/run_0002 | silo_cold | n/a | 54.2402 | 27041.9 | 987.495 | 539.061 | 475.645 | 511.851 | 0.385584 | 50 | 49.4442 | -25.2867 | 32764.8 | -4426.54 | 80 | 1.12352e+09 | 1.2188e+09 | after_vertical_rise | False | False | ok | ok | m2 | ok | 28653.6 | 0.0697337 | 0.0552731 | 26054.4 | 26054.4 | 0 | 0.00618235 | explained | 2.69526 | 37614.8 | 2.13087e+09 | 0.40107 | 0 | n/a | no_offload | 0 | 0 | 0 | 26054.4 | 26054.4 | 0 | n/a | explained | 0 | 31822 | 2.2686e+09 | 0.398288 | 2 | 18.2654 | central | flown | rise_time | aft_ring | 0 | n/a | 6486.6 | 0 | 6486.6 | 1.12732 | 4.39943 | 2.49734e+07 | 0.00620546 | n/a | structure_release_unload; structure_payload_limit | False | none | 1.75905 | inserted |
| 3 | 100 | sweep_1/run_0003 | silo_cold | n/a | 76.7072 | 27553.2 | 1498.83 | 765.442 | 675.346 | 823.485 | 0.377803 | 71.8083 | 129.916 | 55.1852 | 31237.6 | -5953.74 | 160 | 2.24905e+09 | 1.72518e+09 | at_first_lit_instant | False | True | ok | ok | none | ok | 41262.9 | 0.100421 | 0.0795967 | 26054.4 | 26054.4 | 0 | 0.00845215 | explained | 2.75516 | 38438.5 | 4.16291e+09 | 0.401188 | 0 | n/a | ok | 11420.2 | 0.0277933 | 0.0220298 | 26054.4 | 26054.4 | 0 | 0.0014407 | explained | 0.762539 | 32130.7 | 4.44625e+09 | 0.395182 | 2 | n/a | central | flown | rise_time | aft_ring | 0 | n/a | 6305.19 | 0 | 6467.02 | 1.12732 | 4.38888 | 2.44141e+07 | 0.00308351 | n/a | structure_release_unload; structure_payload_limit | False | none | 1.75905 | inserted |
| 4 | 200 | sweep_1/run_0004 | silo_cold | n/a | 108.48 | 28261.9 | 2207.47 | 1088.73 | 960.488 | 1246.98 | 0.367746 | 103.569 | 574.085 | 499.354 | 29887.4 | -7303.94 | 320 | 4.50365e+09 | 2.44279e+09 | at_first_lit_instant | False | True | ok | ok | none | ok | 56827.2 | 0.138299 | 0.10962 | 26054.4 | 26054.4 | 0 | 0.672381 | explained | 2.69774 | 40201.2 | 8.08183e+09 | 0.398794 | 0 | n/a | ok | 31618.3 | 0.0769488 | 0.060992 | 26054.4 | 26054.4 | 0 | 0.00189927 | explained | 1.501 | 34195.3 | 8.5714e+09 | 0.395939 | 2 | n/a | central | flown | rise_time | aft_ring | 0 | n/a | 6020.43 | 0 | 6457.36 | 1.12732 | 4.38365 | 2.35045e+07 | 0.001537 | n/a | structure_release_unload; structure_payload_limit | False | none | 1.75905 | inserted |
| 5 | 300 | sweep_1/run_0005 | silo_cold | n/a | 132.861 | 28794.5 | 2740.13 | 1339.33 | 1181.47 | 1558.66 | 0.360578 | 127.937 | 1293.3 | 1218.57 | 29410.9 | -7780.47 | 480 | 6.76174e+09 | 2.99456e+09 | at_first_lit_instant | True | True | ok | ok | none | ok | 67285.8 | 0.163752 | 0.129795 | 26054.4 | 26054.4 | 0 | 0.722248 | explained | 2.61902 | 41845.8 | 1.18768e+10 | 0.399415 | 0 | n/a | ok | 44727.9 | 0.108854 | 0.0862807 | 26054.4 | 26054.4 | 0 | 0.488054 | explained | 1.74098 | 36117.3 | 1.25447e+10 | 0.394123 | 2 | n/a | central | flown | rise_time | aft_ring | 0 | n/a | 5846.14 | 0 | 6454.16 | 1.12732 | 4.38191 | 2.29243e+07 | 0.00102362 | n/a | structure_release_unload; structure_payload_limit | False | none | 1.75905 | inserted |

Structural offload cases of this sweep (SP7, D-SP7-22):

- silo_cold_s1_st (5 points of 5): silo_cold_s1_st.structure_dm_kg is the modelled structural mass of the push load at each point's x* (dm1 + dm2, never an assumed penalty), a first-order station sizing of the push load (layer and set central (every coefficient at its central value): central; configs/structures/generic_f9_class_2d.yaml), a first-order estimate with its stated ranges, not a detailed structural design; its fired flags are in silo_cold_s1_st.structure_flags and the Checks section.

Sweep points at which an offload case ended no_offload (SP7 step S3c; pre-registration section 9):

- sweep_1/run_0001 silo_cold_s1_st: no offload at P_ref: the full-load push carrying dm 6526.53 kg falls short of P_ref by 60.2313 m/s of delta-v (the solver's dv_shortfall_mps at x = 0; column silo_cold_s1_st.dv_shortfall_mps); payload deficit at the full load not flown (a payload case flies a variant, not a sweep point)
- sweep_1/run_0002 silo_cold_s1_st: no offload at P_ref: the full-load push carrying dm 6486.6 kg falls short of P_ref by 18.2654 m/s of delta-v (the solver's dv_shortfall_mps at x = 0; column silo_cold_s1_st.dv_shortfall_mps); payload deficit at the full load not flown (a payload case flies a variant, not a sweep point)

## sweep_2: silo_cold_200m over assist.stroke_m

| point | assist.stroke_m | run_dir | of | paired_baseline | exit_speed_mps | payload_kg | payload_delta_kg | ideal_screening_payload_at_release_speed_at_pbase_kg | screening_yardstick_kg | payload_beyond_screening_kg | gamma_star_rad | speed_at_kick_mps | peak_q_alpha | delta_peak_q_alpha | max_q_pa | delta_max_q_pa | facility_length_m | drive_energy_J | drive_power_peak_W | kick_regime | unconstrained_kick | payload_delta_upper_bound | search_status | screening_status | screening_diagnostic_failed | silo_cold_200m_s1.status | silo_cold_200m_s1.offload_kg | silo_cold_200m_s1.stage1_fraction | silo_cold_200m_s1.total_fraction | silo_cold_200m_s1.reference_payload_kg | silo_cold_200m_s1.payload_kg | silo_cold_200m_s1.payload_delta_kg | silo_cold_200m_s1.verification_delta_kg | silo_cold_200m_s1.decomposition_status | silo_cold_200m_s1.screening_ratio | silo_cold_200m_s1.max_q_pa | silo_cold_200m_s1.electrical_energy_J | silo_cold_200m_s1.solve_gamma_star_rad | silo_cold_200m_s1.n_flags | silo_cold_200m_s1.dv_shortfall_mps | silo_cold_200m_s1_st.status | silo_cold_200m_s1_st.offload_kg | silo_cold_200m_s1_st.stage1_fraction | silo_cold_200m_s1_st.total_fraction | silo_cold_200m_s1_st.reference_payload_kg | silo_cold_200m_s1_st.payload_kg | silo_cold_200m_s1_st.payload_delta_kg | silo_cold_200m_s1_st.verification_delta_kg | silo_cold_200m_s1_st.decomposition_status | silo_cold_200m_s1_st.screening_ratio | silo_cold_200m_s1_st.max_q_pa | silo_cold_200m_s1_st.electrical_energy_J | silo_cold_200m_s1_st.solve_gamma_star_rad | silo_cold_200m_s1_st.n_flags | silo_cold_200m_s1_st.dv_shortfall_mps | silo_cold_200m_s1_st.structure_set | silo_cold_200m_s1_st.structure_sizing | silo_cold_200m_s1_st.structure_dynamic | silo_cold_200m_s1_st.structure_entry | silo_cold_200m_s1_st.structure_margin | silo_cold_200m_s1_st.structure_cap_g | silo_cold_200m_s1_st.structure_dm_kg | silo_cold_200m_s1_st.structure_dm_stage2_kg | silo_cold_200m_s1_st.structure_dm_x0_kg | silo_cold_200m_s1_st.structure_dlf | silo_cold_200m_s1_st.structure_n_peak_g | silo_cold_200m_s1_st.structure_F_peak_N | silo_cold_200m_s1_st.structure_ramp_cost_rel | silo_cold_200m_s1_st.structure_plausibility_factor | silo_cold_200m_s1_st.structure_flags | silo_cold_200m_s1_st.structure_plausibility_scaled | silo_cold_200m_s1_st.structure_overrides | silo_cold_200m_s1_st.structure_plausibility_ratio | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 50 | sweep_2/run_0001 | silo_cold_200m | n/a | 76.7072 | 27553.2 | 1498.83 | 765.442 | 675.346 | 823.485 | 0.377803 | 71.8083 | 129.916 | 55.1852 | 31237.6 | -5953.74 | 110 | 1.96866e+09 | 3.02021e+09 | at_first_lit_instant | False | True | ok | ok | none | ok | 41263 | 0.100421 | 0.0795968 | 26054.4 | 26054.4 | 0 | 0.00516445 | explained | 2.75516 | 38437.4 | 3.64392e+09 | 0.401248 | 0 | n/a | no_offload | 0 | 0 | 0 | 26054.4 | 26054.4 | 0 | n/a | explained | 0 | 28868.1 | 4.03715e+09 | 0.412672 | 3 | 189.99 | central | flown | rise_time | aft_ring | 0 | n/a | 16049.1 | 506.058 | 16049.1 | 1.12732 | 7.84543 | 4.52702e+07 | 0.0125684 | n/a | structure_release_unload; structure_upper_stack_exceeded; structure_payload_limit | False | none | 1.75905 | inserted |
| 2 | 100 | sweep_2/run_0002 | silo_cold_200m | n/a | 76.7072 | 27553.2 | 1498.83 | 765.442 | 675.346 | 823.485 | 0.377804 | 71.8083 | 129.916 | 55.185 | 31237.6 | -5953.75 | 160 | 2.24905e+09 | 1.72518e+09 | at_first_lit_instant | False | True | ok | ok | none | ok | 41263 | 0.100421 | 0.0795968 | 26054.4 | 26054.4 | 0 | 0.00595928 | explained | 2.75516 | 38437.4 | 4.16291e+09 | 0.401246 | 0 | n/a | ok | 11420.2 | 0.0277932 | 0.0220298 | 26054.4 | 26054.4 | 0 | 0.00143547 | explained | 0.762539 | 32130.7 | 4.44625e+09 | 0.395181 | 2 | n/a | central | flown | rise_time | aft_ring | 0 | n/a | 6305.19 | 0 | 6467.02 | 1.12732 | 4.38888 | 2.44141e+07 | 0.00308351 | n/a | structure_release_unload; structure_payload_limit | False | none | 1.75905 | inserted |
| 3 | 200 | sweep_2/run_0003 | silo_cold_200m | n/a | 76.7072 | 27553.2 | 1498.83 | 765.442 | 675.346 | 823.485 | 0.377803 | 71.8083 | 129.916 | 55.1851 | 31237.6 | -5953.74 | 260 | 2.80982e+09 | 1.07767e+09 | at_first_lit_instant | False | True | ok | ok | none | ok | 41263 | 0.100421 | 0.0795968 | 26054.4 | 26054.4 | 0 | 0.00599645 | explained | 2.75516 | 38437.4 | 5.20089e+09 | 0.401245 | 0 | n/a | ok | 26686.4 | 0.0649463 | 0.0514785 | 26054.4 | 26054.4 | 0 | 0.00345351 | explained | 1.78188 | 35169.6 | 5.37499e+09 | 0.39818 | 2 | n/a | central | flown | rise_time | aft_ring | 0 | n/a | 3201.77 | 0 | 3441.53 | 1.12732 | 2.68876 | 1.44724e+07 | 0.000767321 | n/a | structure_release_unload; structure_payload_limit | False | none | 1.75905 | inserted |
| 4 | 300 | sweep_2/run_0004 | silo_cold_200m | n/a | 76.7072 | 27553.2 | 1498.83 | 765.442 | 675.346 | 823.485 | 0.377804 | 71.8083 | 129.916 | 55.185 | 31237.6 | -5953.75 | 360 | 3.3706e+09 | 8.6183e+08 | at_first_lit_instant | False | True | ok | ok | none | ok | 41262.9 | 0.100421 | 0.0795967 | 26054.4 | 26054.4 | 0 | 0.00880487 | explained | 2.75516 | 38438.5 | 6.23886e+09 | 0.401188 | 0 | n/a | ok | 32031 | 0.0779534 | 0.0617883 | 26054.4 | 26054.4 | 0 | 0.00525828 | explained | 2.13874 | 36323.8 | 6.37145e+09 | 0.399256 | 2 | n/a | central | flown | rise_time | aft_ring | 0 | n/a | 2055.3 | 0 | 2304.8 | 1.12732 | 2.12418 | 1.12984e+07 | 0.000340741 | n/a | structure_release_unload; structure_payload_limit | False | none | 1.75905 | inserted |

Structural offload cases of this sweep (SP7, D-SP7-22):

- silo_cold_200m_s1_st (4 points of 4): silo_cold_200m_s1_st.structure_dm_kg is the modelled structural mass of the push load at each point's x* (dm1 + dm2, never an assumed penalty), a first-order station sizing of the push load (layer and set central (every coefficient at its central value): central; configs/structures/generic_f9_class_2d.yaml), a first-order estimate with its stated ranges, not a detailed structural design; its fired flags are in silo_cold_200m_s1_st.structure_flags and the Checks section.

Sweep points at which an offload case ended no_offload (SP7 step S3c; pre-registration section 9):

- sweep_2/run_0001 silo_cold_200m_s1_st: no offload at P_ref: the full-load push carrying dm 16049.1 kg falls short of P_ref by 189.99 m/s of delta-v (the solver's dv_shortfall_mps at x = 0; column silo_cold_200m_s1_st.dv_shortfall_mps); payload deficit at the full load not flown (a payload case flies a variant, not a sweep point)

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
- constant_accel: prescribed net acceleration 3 g0 (assumed); drive force unconstrained, solved from the track equation [sweep_1/run_0001, sweep_1/run_0002, sweep_1/run_0003, sweep_1/run_0004, sweep_1/run_0005, sweep_2/run_0002]
- constant_accel: carriage mass 0 t (assumed) [all sweep points]
- constant_accel: braking deceleration 5 g0 (assumed) [all sweep points]
- constant_accel: drive efficiency 0.5 (assumed) [all sweep points]
- constant_accel: exhaust impingement fraction 0 (assumed); the system keeps (1 - f_imp) T of the on-track thrust [all sweep points]
- constant_accel: shaft vented (no air column), no friction [all sweep points]
- constant_accel: constant g_eff = 9.772092 m/s^2 on the track (mu/R_E^2 - omega_p^2 R_E with omega_p = 6.408435e-05 rad/s, the planar rotation rate of the site), flat 1-DOF track frame, Coriolis neglected [all sweep points]
- constant_accel: infinite jerk at push start and release [all sweep points]
- constant_accel: vehicle clamped to the carriage during any hold before the push [all sweep points]
- track: straight, L = 50 m at 1.5708 rad above horizontal, start altitude -50 m (exit at 0 m) [sweep_1/run_0002, sweep_2/run_0001]
- track: straight, L = 100 m at 1.5708 rad above horizontal, start altitude -100 m (exit at 0 m) [sweep_1/run_0003, sweep_2/run_0002]
- track: straight, L = 200 m at 1.5708 rad above horizontal, start altitude -200 m (exit at 0 m) [sweep_1/run_0004, sweep_2/run_0003]
- track: straight, L = 300 m at 1.5708 rad above horizontal, start altitude -300 m (exit at 0 m) [sweep_1/run_0005, sweep_2/run_0004]
- constant_accel: prescribed net acceleration 6 g0 (assumed); drive force unconstrained, solved from the track equation [sweep_2/run_0001]
- constant_accel: the net acceleration is derived from the configured exit speed 76.7072 m/s (assumed) and the track length L, a = v_exit^2 / (2 L); the push time is 2 L / v_exit [sweep_2/run_0001, sweep_2/run_0002, sweep_2/run_0003, sweep_2/run_0004]
- constant_accel: prescribed net acceleration 1.5 g0 (assumed); drive force unconstrained, solved from the track equation [sweep_2/run_0003]
- constant_accel: prescribed net acceleration 1 g0 (assumed); drive force unconstrained, solved from the track equation [sweep_2/run_0004]

## Checks

- pad: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.45116e-08: ok
- sweep_1/run_0001: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.38822e-08: ok
- sweep_1/run_0002: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36369e-08: ok
- sweep_1/run_0003: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35972e-08: ok
- sweep_1/run_0004: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.31566e-08: ok
- sweep_1/run_0005: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.28372e-08: ok
- sweep_1/run_0001__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_1/run_0001__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.41859e-08: ok
- sweep_1/run_0001__silo_cold_s1_st: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0.0154103: ok
- sweep_1/run_0002__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_1/run_0002__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.39164e-08: ok
- sweep_1/run_0002__silo_cold_s1_st: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0.0046859: ok
- sweep_1/run_0003__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_1/run_0003__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36282e-08: ok
- sweep_1/run_0003__silo_cold_s1_st: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_1/run_0003__silo_cold_s1_st (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.33492e-08: ok
- sweep_1/run_0004__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_1/run_0004__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.32428e-08: ok
- sweep_1/run_0004__silo_cold_s1_st: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_1/run_0004__silo_cold_s1_st (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.32013e-08: ok
- sweep_1/run_0005__silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_1/run_0005__silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.29521e-08: ok
- sweep_1/run_0005__silo_cold_s1_st: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_1/run_0005__silo_cold_s1_st (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.28963e-08: ok
- sweep_2/run_0001: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35972e-08: ok
- sweep_2/run_0002: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35972e-08: ok
- sweep_2/run_0003: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35974e-08: ok
- sweep_2/run_0004: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35968e-08: ok
- sweep_2/run_0001__silo_cold_200m_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_2/run_0001__silo_cold_200m_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36427e-08: ok
- sweep_2/run_0001__silo_cold_200m_s1_st: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0.0481953: ok
- sweep_2/run_0002__silo_cold_200m_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_2/run_0002__silo_cold_200m_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36438e-08: ok
- sweep_2/run_0002__silo_cold_200m_s1_st: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_2/run_0002__silo_cold_200m_s1_st (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.3349e-08: ok
- sweep_2/run_0003__silo_cold_200m_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_2/run_0003__silo_cold_200m_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36408e-08: ok
- sweep_2/run_0003__silo_cold_200m_s1_st: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_2/run_0003__silo_cold_200m_s1_st (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36248e-08: ok
- sweep_2/run_0004__silo_cold_200m_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_2/run_0004__silo_cold_200m_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36408e-08: ok
- sweep_2/run_0004__silo_cold_200m_s1_st: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- sweep_2/run_0004__silo_cold_200m_s1_st (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36272e-08: ok

- sweep_1/run_0001: screening status ok (failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: none)
- sweep_1/run_0002: screening status ok (failed checks: none; failed diagnostic checks: M2; gamma*-sensitive: M2 (diagnostic))
- sweep_1/run_0003: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_1/run_0004: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_1/run_0005: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_2/run_0001: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_2/run_0002: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_2/run_0003: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_2/run_0004: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)

Offload checks (the screening rule for offload rows: an offload beyond the ideal screening estimate is explained only by a decomposition that closes, else bug_suspect; offload rows never enter the unexplained-beats list):
- sweep_1/run_0001 silo_cold_s1 offload decomposition: explained
- sweep_1/run_0001 silo_cold_s1_st offload decomposition: explained
- sweep_1/run_0002 silo_cold_s1 offload decomposition: explained
- sweep_1/run_0002 silo_cold_s1_st offload decomposition: explained
- sweep_1/run_0003 silo_cold_s1 offload decomposition: explained
- sweep_1/run_0003 silo_cold_s1_st offload decomposition: explained
- sweep_1/run_0004 silo_cold_s1 offload decomposition: explained
- sweep_1/run_0004 silo_cold_s1_st offload decomposition: explained
- sweep_1/run_0005 silo_cold_s1 offload decomposition: explained
- sweep_1/run_0005 silo_cold_s1_st offload decomposition: explained
- sweep_2/run_0001 silo_cold_200m_s1 offload decomposition: explained
- sweep_2/run_0001 silo_cold_200m_s1_st offload decomposition: explained
- sweep_2/run_0002 silo_cold_200m_s1 offload decomposition: explained
- sweep_2/run_0002 silo_cold_200m_s1_st offload decomposition: explained
- sweep_2/run_0003 silo_cold_200m_s1 offload decomposition: explained
- sweep_2/run_0003 silo_cold_200m_s1_st offload decomposition: explained
- sweep_2/run_0004 silo_cold_200m_s1 offload decomposition: explained
- sweep_2/run_0004 silo_cold_200m_s1_st offload decomposition: explained

Offload flags at each point (the case record's: its solve's and its recorded run's; sweep_index.csv gives their number, `<case>.n_flags`, beside the solve's gamma*_ref, `<case>.solve_gamma_star_rad`):
- sweep_1/run_0001 silo_cold_s1 offload flags: none
- sweep_1/run_0001 silo_cold_s1_st offload flags: structure_release_unload: the push's instant release unloads the stack further than the pad's MECO shutdown (release swing -4.42 g0 against MECO's -5.2 g0; stage-1 LOX and RP-1 bottom pressures -9.37e+05 and -2.36e+05 Pa absolute; common-dome reverse pressure 3.63e+05 Pa against MECO's 1.3e+05 Pa; upper-stack swing -6.04e+06 N against MECO's -7.1e+06 N); structure_payload_limit: the push's peak axial load 4.42 g0 and release swing -4.42 g0 against the payload's axial limits -2 to 6 g0
- sweep_1/run_0002 silo_cold_s1 offload flags: none
- sweep_1/run_0002 silo_cold_s1_st offload flags: structure_release_unload: the push's instant release unloads the stack further than the pad's MECO shutdown (release swing -4.4 g0 against MECO's -5.2 g0; stage-1 LOX and RP-1 bottom pressures -9.31e+05 and -2.34e+05 Pa absolute; common-dome reverse pressure 3.63e+05 Pa against MECO's 1.3e+05 Pa; upper-stack swing -6.01e+06 N against MECO's -7.1e+06 N); structure_payload_limit: the push's peak axial load 4.4 g0 and release swing -4.4 g0 against the payload's axial limits -2 to 6 g0
- sweep_1/run_0003 silo_cold_s1 offload flags: none
- sweep_1/run_0003 silo_cold_s1_st offload flags: structure_release_unload: the push's instant release unloads the stack further than the pad's MECO shutdown (release swing -4.39 g0 against MECO's -5.2 g0; stage-1 LOX and RP-1 bottom pressures -8.96e+05 and -2.18e+05 Pa absolute; common-dome reverse pressure 3.63e+05 Pa against MECO's 1.3e+05 Pa; upper-stack swing -5.99e+06 N against MECO's -7.1e+06 N); structure_payload_limit: the push's peak axial load 4.39 g0 and release swing -4.39 g0 against the payload's axial limits -2 to 6 g0
- sweep_1/run_0004 silo_cold_s1 offload flags: none
- sweep_1/run_0004 silo_cold_s1_st offload flags: structure_release_unload: the push's instant release unloads the stack further than the pad's MECO shutdown (release swing -4.38 g0 against MECO's -5.2 g0; stage-1 LOX and RP-1 bottom pressures -8.37e+05 and -1.93e+05 Pa absolute; common-dome reverse pressure 3.63e+05 Pa against MECO's 1.3e+05 Pa; upper-stack swing -5.99e+06 N against MECO's -7.1e+06 N); structure_payload_limit: the push's peak axial load 4.38 g0 and release swing -4.38 g0 against the payload's axial limits -2 to 6 g0
- sweep_1/run_0005 silo_cold_s1 offload flags: none
- sweep_1/run_0005 silo_cold_s1_st offload flags: structure_release_unload: the push's instant release unloads the stack further than the pad's MECO shutdown (release swing -4.38 g0 against MECO's -5.2 g0; stage-1 LOX and RP-1 bottom pressures -7.99e+05 and -1.76e+05 Pa absolute; common-dome reverse pressure 3.63e+05 Pa against MECO's 1.3e+05 Pa; upper-stack swing -5.98e+06 N against MECO's -7.1e+06 N); structure_payload_limit: the push's peak axial load 4.38 g0 and release swing -4.38 g0 against the payload's axial limits -2 to 6 g0
- sweep_2/run_0001 silo_cold_200m_s1 offload flags: none
- sweep_2/run_0001 silo_cold_200m_s1_st offload flags: structure_release_unload: the push's instant release unloads the stack further than the pad's MECO shutdown (release swing -7.85 g0 against MECO's -5.2 g0; stage-1 LOX and RP-1 bottom pressures -1.91e+06 and -6.68e+05 Pa absolute; common-dome reverse pressure 3.63e+05 Pa against MECO's 1.3e+05 Pa; upper-stack swing -1.08e+07 N against MECO's -7.1e+06 N); structure_upper_stack_exceeded: the push's peak upper-stack load 1.075e+07 N exceeds the pad envelope's 7.095e+06 N, so stage 2's tanks and the interstage were sized; structure_payload_limit: the push's peak axial load 7.85 g0 and release swing -7.85 g0 against the payload's axial limits -2 to 6 g0
- sweep_2/run_0002 silo_cold_200m_s1 offload flags: none
- sweep_2/run_0002 silo_cold_200m_s1_st offload flags: structure_release_unload: the push's instant release unloads the stack further than the pad's MECO shutdown (release swing -4.39 g0 against MECO's -5.2 g0; stage-1 LOX and RP-1 bottom pressures -8.96e+05 and -2.18e+05 Pa absolute; common-dome reverse pressure 3.63e+05 Pa against MECO's 1.3e+05 Pa; upper-stack swing -5.99e+06 N against MECO's -7.1e+06 N); structure_payload_limit: the push's peak axial load 4.39 g0 and release swing -4.39 g0 against the payload's axial limits -2 to 6 g0
- sweep_2/run_0003 silo_cold_200m_s1 offload flags: none
- sweep_2/run_0003 silo_cold_200m_s1_st offload flags: structure_release_unload: the push's instant release unloads the stack further than the pad's MECO shutdown (release swing -2.69 g0 against MECO's -5.2 g0; stage-1 LOX and RP-1 bottom pressures -3.97e+05 and 2.32e+03 Pa absolute; common-dome reverse pressure 3.63e+05 Pa against MECO's 1.3e+05 Pa; upper-stack swing -3.67e+06 N against MECO's -7.1e+06 N); structure_payload_limit: the push's peak axial load 2.69 g0 and release swing -2.69 g0 against the payload's axial limits -2 to 6 g0
- sweep_2/run_0004 silo_cold_200m_s1 offload flags: none
- sweep_2/run_0004 silo_cold_200m_s1_st offload flags: structure_release_unload: the push's instant release unloads the stack further than the pad's MECO shutdown (release swing -2.12 g0 against MECO's -5.2 g0; stage-1 LOX and RP-1 bottom pressures -2.39e+05 and 7.25e+04 Pa absolute; common-dome reverse pressure 3.63e+05 Pa against MECO's 1.3e+05 Pa; upper-stack swing -2.9e+06 N against MECO's -7.1e+06 N); structure_payload_limit: the push's peak axial load 2.12 g0 and release swing -2.12 g0 against the payload's axial limits -2 to 6 g0

No run and no comparison is bug_suspect.
Diagnostic checks that failed (computed and reported only: they give no bug_suspect and block no finding; user decision of 2026-09-30, docs/physics.md, 'Screening-beat rule (2-D)'): sweep_1/run_0001 (M2), sweep_1/run_0002 (M2)
Checks whose verdict changes within the variant's gamma* +/- h (the gamma*-sensitivity step; the verdict at gamma*_ref stands as pre-registered, but the gravity and steering terms trade against each other with gamma*, so these verdicts are not robust): sweep_1/run_0002 (M2 (diagnostic))
