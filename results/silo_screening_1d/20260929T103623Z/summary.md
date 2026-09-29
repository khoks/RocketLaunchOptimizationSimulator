# silo_screening_1d (20260929T103623Z, git 98c752d58f52-dirty)

Comparison basis: sweep-optimized (Phase 1 has no guidance parameters); 1-D vertical, vacuum thrust, no drag, no rotation, no throttling

- Vehicle: generic_f9_class
- Baseline: pad
- Timestamp (UTC): 20260929T103623Z
- Git: 98c752d58f52-dirty

## Variants against the baseline

| quantity | pad (baseline) | pad_instant | silo_instant | silo_cold | silo_cold_lag | silo_hot_ramp_on_track | silo_hot_full | silo_hot_full_impinged | silo_failed | silo_sled_22t |
|---|---|---|---|---|---|---|---|---|---|---|
| status | nominal | nominal | nominal | nominal | nominal | nominal | nominal | nominal | impact | nominal |
| flags (see Flags) | - | - | - | - | - | - | - | - | 1 | - |
| stage-1 ignition, t_ign relative to release [s] (negative = lit before release) | -2 | 0 | 0 | 0.5 | 0.5 | -2 | -4.60732 | -4.60732 | n/a | 0.5 |
| stage-1 startup kind (step = instant full thrust: a yardstick, not achievable) | ramp | step | step | ramp | lag | ramp | ramp | ramp | ramp | ramp |
|   its t_ramp or tau [s] | 2 | 0 | 0 | 2 | 1 | 2 | 2 | 2 | 2 | 2 |
| speed at release [m/s] | 0 | 0 | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 |
|   delta vs baseline [m/s] | (baseline) | 0 | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 |
| propellant burned before release [kg] | 2697.46 | 0 | 0 | 0 | 0 | 2697.46 | 9730.6 | 9730.6 | 0 | 0 |
|   its dv_vac equivalent [m/s] | 15.2007 | 0 | 0 | 0 | 0 | 15.2007 | 55.1936 | 55.1936 | 0 | 0 |
| stage-1 burnout speed [m/s] | 2557.65 | 2563.22 | 2642.41 | 2627.29 | 2627.29 | 2636.8 | 2621.82 | 2621.82 | n/a | 2627.29 |
|   delta vs baseline [m/s] | (baseline) | 5.57637 | 84.7667 | 69.6421 | 69.6443 | 79.1567 | 64.1707 | 64.1707 | n/a | 69.6421 |
| stage-1 burnout altitude [m] | 124667 | 125465 | 136840 | 134771 | 134776 | 135963 | 133649 | 133649 | n/a | 134771 |
|   delta vs baseline [m] | (baseline) | 798.342 | 12173.4 | 10104 | 10109.3 | 11295.8 | 8981.78 | 8981.78 | n/a | 10104 |
| identity point (stage1_burnout, or the run's end) | (baseline) | stage1_burnout | stage1_burnout | stage1_burnout | stage1_burnout | stage1_burnout | stage1_burnout | stage1_burnout | end vs stage1_burnout | stage1_burnout |
| identity: delta speed there [m/s] | (baseline) | 5.57637 | 84.7667 | 69.6421 | 69.6443 | 79.1567 | 64.1707 | 64.1707 | -2480.94 | 69.6421 |
|   = delta speed at release [m/s] | (baseline) | 0 | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 |
|   + delta dv_vac [m/s] | (baseline) | 15.2007 | 15.2007 | 15.2007 | 15.2007 | -2.65777e-08 | -39.9929 | -39.9929 | -3970.27 | 15.2007 |
|   - delta gravity loss, duration part [m/s] | (baseline) | 9.79829 | 9.79829 | 24.4957 | 24.4957 | 0 | -25.5472 | -25.5472 | -1427.55 | 24.4957 |
|   - delta gravity loss, altitude part [m/s] | (baseline) | -0.174001 | -2.65714 | -2.22998 | -2.23224 | -2.44955 | -1.9092 | -1.9092 | 14.9193 | -2.22998 |
|   - delta drag loss [m/s] | (baseline) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
|   - delta steering loss [m/s] | (baseline) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
|   - delta back-pressure loss [m/s] | (baseline) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
|   identity residual [m/s] (must be < 0.01) | (baseline) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hold-down credit vs baseline [m/s] (baseline's pre-flight burn cost minus this run's) | (baseline) | 5.40237 | 5.40237 | 5.40237 | 5.40237 | 0 | -14.4457 | -14.4457 | 5.40237 | 5.40237 |
|   pre-flight burn cost of this run [m/s] (c ln(m0/m_flight) - g_eff dt_full) | 5.40237 | 0 | 0 | 0 | 0 | 5.40237 | 19.8481 | 19.8481 | 0 | 0 |
| ignition loss, integrated vs silo_instant [m/s] (same release state only) | (baseline) | n/a | 0 | 15.1246 | 15.1223 | 5.60995 | 20.596 | 20.596 | n/a | 15.1246 |
| ignition loss, constant-g formula vs an instant start at release [m/s] | 5.40237 | 0 | 0 | 14.6974 | 14.6974 | 5.40237 | 19.8481 | 19.8481 | n/a | 14.6974 |
| ideal-screening payload equivalent of the burnout speed delta [kg] (ideal rocket equation at fixed losses; not a payload result) | (baseline) | 49.1403 | 757.818 | 620.888 | 620.909 | 706.941 | 571.538 | 571.538 | n/a | 620.888 |
|   ideal screening at this run's speed at release [kg] (the README yardstick; same equation, not a payload result) | (baseline) | 0 | 684.758 | 684.758 | 684.758 | 684.758 | 684.758 | 684.758 | 684.758 | 684.758 |
| gravity loss [m/s] | 1412.63 | 1422.25 | 1419.77 | 1434.89 | 1434.89 | 1410.18 | 1385.17 | 1385.17 | 0 | 1434.89 |
|   duration part [m/s] | 1427.55 | 1437.34 | 1437.34 | 1452.04 | 1452.04 | 1427.55 | 1402 | 1402 | 0 | 1452.04 |
|   altitude part [m/s] | -14.9193 | -15.0933 | -17.5764 | -17.1493 | -17.1515 | -17.3689 | -16.8285 | -16.8285 | 0 | -17.1493 |
| drag loss [m/s] | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| steering loss [m/s] | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| back-pressure loss [m/s] | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dv_vac from the flight start [m/s] | 3970.27 | 3985.47 | 3985.47 | 3985.47 | 3985.47 | 3970.27 | 3930.28 | 3930.28 | 0 | 3985.47 |
| max-Q [Pa] | n/a (Phase 2) | n/a (Phase 2) | n/a (Phase 2) | n/a (Phase 2) | n/a (Phase 2) | n/a (Phase 2) | n/a (Phase 2) | n/a (Phase 2) | n/a (Phase 2) | n/a (Phase 2) |
| peak felt axial g, run-wide [g0] (phase) | 5.71192 (BURN) | 5.71192 (BURN) | 5.71192 (BURN) | 5.71192 (BURN) | 5.71192 (BURN) | 5.71192 (BURN) | 5.71192 (BURN) | 5.71192 (BURN) | 3.99915 (ASSIST) | 5.71192 (BURN) |
|   at t after release [s] | 145.694 | 146.694 | 146.694 | 148.194 | 148.194 | 145.694 | 143.086 | 143.086 | -2.60732 | 148.194 |
|   mass there [kg] | 146870 | 146870 | 146870 | 146870 | 146870 | 146870 | 146870 | 146870 | 542570 | 146870 |
| peak felt g on the track [g0] | n/a | n/a | 3.99915 | 3.99915 | 3.99915 | 3.99915 | 3.99915 | 3.99915 | 3.99915 | 3.99915 |
|   at t after release [s] | n/a | n/a | -2.60732 | -2.60732 | -2.60732 | -2.60732 | -2.60732 | -2.60732 | -2.60732 | -2.60732 |
|   mass there [kg] | n/a | n/a | 542570 | 542570 | 542570 | 542570 | 539873 | 539873 | 542570 | 542570 |
| peak felt g in flight [g0] | 5.71192 | 5.71192 | 5.71192 | 5.71192 | 5.71192 | 5.71192 | 5.71192 | 5.71192 | 0 | 5.71192 |
|   at t after release [s] | 145.694 | 146.694 | 146.694 | 148.194 | 148.194 | 145.694 | 143.086 | 143.086 | 0 | 148.194 |
|   mass there [kg] | 146870 | 146870 | 146870 | 146870 | 146870 | 146870 | 146870 | 146870 | 542570 | 146870 |
| interface force, peak [N] | 0 | 0 | 2.12786e+07 | 2.12786e+07 | 2.12786e+07 | 2.12786e+07 | 1.29459e+07 | 1.29459e+07 | 2.12786e+07 | 2.12786e+07 |
| interface force, minimum [N] | 0 | 0 | 2.12786e+07 | 2.12786e+07 | 2.12786e+07 | 1.29459e+07 | 1.26701e+07 | 1.26701e+07 | 2.12786e+07 | 2.12786e+07 |
| hold-down force m g_eff - T, minimum over the hold [N] (negative = the clamps in tension, holding the vehicle down) | -2.93707e+06 | n/a | n/a | n/a | n/a | n/a | -2.93707e+06 | -2.93707e+06 | n/a | n/a |
| peak track-normal g [g0] | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
|   vehicle [g0] | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
|   carriage [g0] | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| assist (drive) energy [J] | 0 | 0 | 2.12786e+09 | 2.12786e+09 | 2.12786e+09 | 1.65379e+09 | 1.27621e+09 | 2.0989e+09 | 2.12786e+09 | 2.21414e+09 |
| assist (drive) energy [kWh] | 0 | 0 | 591.073 | 591.073 | 591.073 | 459.385 | 354.502 | 583.027 | 591.073 | 615.04 |
| electrical energy [J] (positive drive work / efficiency) | 0 | 0 | 4.25573e+09 | 4.25573e+09 | 4.25573e+09 | 3.30757e+09 | 2.55241e+09 | 4.19779e+09 | 4.25573e+09 | 4.42829e+09 |
| electrical energy [kWh] | 0 | 0 | 1182.15 | 1182.15 | 1182.15 | 918.77 | 709.004 | 1166.05 | 1182.15 | 1230.08 |
| peak drive power [W] | 0 | 0 | 1.63222e+09 | 1.63222e+09 | 1.63222e+09 | 9.93047e+08 | 9.71889e+08 | 1.60295e+09 | 1.63222e+09 | 1.69841e+09 |
| braking (negative) drive power, minimum [W] | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| braking distance [m] | 0 | 0 | 60 | 60 | 60 | 60 | 60 | 60 | 60 | 60 |
| facility length incl. braking [m] | 0 | 0 | 160 | 160 | 160 | 160 | 160 | 160 | 160 | 160 |
| failed ignition: stage | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | stage1 | n/a |
|   apex altitude of the fall-back coast [m] | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 300.27 | n/a |
|   time of that apex after release [s] | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 7.82912 | n/a |
|   parked carriage altitude [m] | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 60 | n/a |
|   time the vehicle comes down to the carriage [s] | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 14.8325 | n/a |
|   speed there [m/s] | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 68.6164 | n/a |
|   return to the release altitude [s] | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 15.6582 | n/a |
|   impact speed at the ground [m/s] | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 76.7072 | n/a |
|   speed at the shaft bottom [m/s] (derived) | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 88.5644 | n/a |

Note: pad_instant, silo_instant: stage-1 startup kind step is instant full thrust at ignition, a yardstick that isolates the ignition-timing loss; no engine achieves it (unphysical), so these columns bound the others, they are not designs.

## Sensitivity

| variant | parameter | change | value [SI] (unit in the cell) | value (in the parameter's YAML units) | status | stage-1 burnout speed [m/s] | delta vs baseline, unchanged [m/s] | delta vs baseline with the same vehicle perturbation [m/s] | ideal-screening payload equiv. of the unchanged delta [kg] | ideal-screening payload equiv. of the same-perturbation delta [kg] | exit speed [m/s] | electrical energy [kWh] | peak drive power [W] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| silo_cold | vehicle.stages.stage1.dry_mass_t | +10% | 28160 kg | 28.16 | nominal | 2588.75 | +31.1076 | +69.5689 | +276.167 | +621.974 | 76.7072 | 1187.72 | 1.63993e+09 |
| silo_cold | vehicle.stages.stage1.dry_mass_t | -10% | 23040 kg | 23.04 | nominal | 2666.68 | +109.038 | +69.716 | +976.258 | +619.75 | 76.7072 | 1176.57 | 1.62452e+09 |
| silo_cold | vehicle.stages.stage1.engine.isp_vac_s | +10% | 342.1 s | 342.1 | nominal | 2887.46 | +329.81 | +70.0907 | +3085.02 | +624.939 | 76.7072 | 1182.15 | 1.63222e+09 |
| silo_cold | vehicle.stages.stage1.engine.isp_vac_s | -10% | 279.9 s | 279.9 | nominal | 2368.03 | -189.613 | +69.2337 | -1613.4 | +617.201 | 76.7072 | 1182.15 | 1.63222e+09 |
| silo_cold | vehicle.screening.stage_isp_eff_s.0 | +10% | 324.5 s | 324.5 | nominal | 2627.29 | +69.6421 | +69.6421 | +612.961 | +612.961 | 76.7072 | 1182.15 | 1.63222e+09 |
| silo_cold | vehicle.screening.stage_isp_eff_s.0 | -10% | 265.5 s | 265.5 | nominal | 2627.29 | +69.6421 | +69.6421 | +629.026 | +629.026 | 76.7072 | 1182.15 | 1.63222e+09 |
| silo_cold | assist.drive_efficiency | +10% | 0.55 - | 0.55 | nominal | 2627.29 | +69.6421 | +69.6421 (= unchanged) | +620.888 | +620.888 | 76.7072 | 1074.68 | 1.63222e+09 |
| silo_cold | assist.drive_efficiency | -10% | 0.45 - | 0.45 | nominal | 2627.29 | +69.6421 | +69.6421 (= unchanged) | +620.888 | +620.888 | 76.7072 | 1313.5 | 1.63222e+09 |
| silo_hot_full | vehicle.stages.stage1.dry_mass_t | +10% | 28160 kg | 28.16 | nominal | 2583.55 | +25.906 | +64.3672 | +229.77 | +574.921 | 76.7072 | 714.581 | 9.7959e+08 |
| silo_hot_full | vehicle.stages.stage1.dry_mass_t | -10% | 23040 kg | 23.04 | nominal | 2660.94 | +103.294 | +63.9723 | +923.866 | +568.098 | 76.7072 | 703.426 | 9.64188e+08 |
| silo_hot_full | vehicle.stages.stage1.engine.isp_vac_s | +10% | 342.1 s | 342.1 | nominal | 2881.98 | +324.336 | +64.6172 | +3030.72 | +575.562 | 76.7072 | 710.467 | 9.7455e+08 |
| silo_hot_full | vehicle.stages.stage1.engine.isp_vac_s | -10% | 279.9 s | 279.9 | nominal | 2362.55 | -195.095 | +63.7514 | -1658.43 | +567.761 | 76.7072 | 707.215 | 9.68637e+08 |
| silo_hot_full | vehicle.screening.stage_isp_eff_s.0 | +10% | 324.5 s | 324.5 | nominal | 2621.82 | +64.1707 | +64.1707 | +564.253 | +564.253 | 76.7072 | 709.004 | 9.71889e+08 |
| silo_hot_full | vehicle.screening.stage_isp_eff_s.0 | -10% | 265.5 s | 265.5 | nominal | 2621.82 | +64.1707 | +64.1707 | +579.016 | +579.016 | 76.7072 | 709.004 | 9.71889e+08 |
| silo_hot_full | assist.drive_efficiency | +10% | 0.55 - | 0.55 | nominal | 2621.82 | +64.1707 | +64.1707 (= unchanged) | +571.538 | +571.538 | 76.7072 | 644.549 | 9.71889e+08 |
| silo_hot_full | assist.drive_efficiency | -10% | 0.45 - | 0.45 | nominal | 2621.82 | +64.1707 | +64.1707 (= unchanged) | +571.538 | +571.538 | 76.7072 | 787.782 | 9.71889e+08 |
| silo_cold | C_D | +/-10% | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 |
| silo_hot_full | C_D | +/-10% | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 | n/a: no drag in Phase 1 |

## Flags

- silo_failed: ignition_failed: stage 'stage1' has fails: true, so nothing burns; ignored: t_ign_s = -2

## Assumptions

- pad and track g_eff = mu/R_E^2 - omega_p^2 R_E with omega_p = 0 rad/s, continuous with mu/r^2 at z = 0 [all runs]
- 1-D vertical motion [all runs]
- vacuum thrust from sea level (no back-pressure), no atmosphere, no drag [all runs]
- no Earth rotation (omega_p = 0), Coriolis neglected [all runs]
- no throttling; instantaneous cutoff at propellant depletion [all runs]
- gravity mu/r^2 in flight (mu = 3.986004418e+14 m^3/s^2; InverseSquareGravity, the run model; ConstantGravity exists only for tests) [all runs]
- pad/track effective gravity g_eff = 9.798285 m/s^2, also the g_ref of the gravity-loss split [all runs]
- loss quadratures reset at release; the identity is accounted from release onward [all runs]
- a vehicle at rest on the ground is clamped until its thrust exceeds its weight; no gravity loss accrues while clamped (propellant burned then is reported as burned before flight) [all runs]
- felt axial acceleration is T/m in flight (vacuum thrust, unthrottled), g_eff while clamped and (F_int + T)/m_v = sddot + g_eff sin phi on the track [all runs]
- track phase: 1-DOF along the track in a flat local frame with constant g_eff; the carriage stays on the track at release; carriage braking is not modelled as a phase (its distance v^2/(2 a_brake) is added to the facility length) [silo_instant, silo_cold, silo_cold_lag, silo_hot_ramp_on_track, silo_hot_full, silo_hot_full_impinged, silo_failed, silo_sled_22t]
- hot start: the propellant burned before release is reported with its delta-v equivalent; the exhaust impingement fraction f_imp on the carriage is an assumed amendment to the track equation (the system keeps (1 - f_imp) T) [silo_instant, silo_cold, silo_cold_lag, silo_hot_ramp_on_track, silo_hot_full, silo_hot_full_impinged, silo_failed, silo_sled_22t]
- drive energy: electrical_energy = (positive drive work) / efficiency; no regeneration is credited for any negative (braking) drive work [silo_instant, silo_cold, silo_cold_lag, silo_hot_ramp_on_track, silo_hot_full, silo_hot_full_impinged, silo_failed, silo_sled_22t]
- track: straight, L = 100 m at 1.5708 rad above horizontal, start altitude -100 m (exit at 0 m) [silo_instant, silo_cold, silo_cold_lag, silo_hot_ramp_on_track, silo_hot_full, silo_hot_full_impinged, silo_failed, silo_sled_22t]
- constant_accel: prescribed net acceleration 3 g0 (assumed); drive force unconstrained, solved from the track equation [silo_instant, silo_cold, silo_cold_lag, silo_hot_ramp_on_track, silo_hot_full, silo_hot_full_impinged, silo_failed, silo_sled_22t]
- constant_accel: carriage mass 0 t (assumed) [silo_instant, silo_cold, silo_cold_lag, silo_hot_ramp_on_track, silo_hot_full, silo_hot_full_impinged, silo_failed]
- constant_accel: braking deceleration 5 g0 (assumed) [silo_instant, silo_cold, silo_cold_lag, silo_hot_ramp_on_track, silo_hot_full, silo_hot_full_impinged, silo_failed, silo_sled_22t]
- constant_accel: drive efficiency 0.5 (assumed) [silo_instant, silo_cold, silo_cold_lag, silo_hot_ramp_on_track, silo_hot_full, silo_hot_full_impinged, silo_failed, silo_sled_22t]
- constant_accel: exhaust impingement fraction 0 (assumed); the system keeps (1 - f_imp) T of the on-track thrust [silo_instant, silo_cold, silo_cold_lag, silo_hot_ramp_on_track, silo_hot_full, silo_failed, silo_sled_22t]
- constant_accel: shaft vented (no air column), no friction [silo_instant, silo_cold, silo_cold_lag, silo_hot_ramp_on_track, silo_hot_full, silo_hot_full_impinged, silo_failed, silo_sled_22t]
- constant_accel: constant g_eff = 9.798285 m/s^2 on the track, omega_p = 0, Coriolis neglected [silo_instant, silo_cold, silo_cold_lag, silo_hot_ramp_on_track, silo_hot_full, silo_hot_full_impinged, silo_failed, silo_sled_22t]
- constant_accel: infinite jerk at push start and release [silo_instant, silo_cold, silo_cold_lag, silo_hot_ramp_on_track, silo_hot_full, silo_hot_full_impinged, silo_failed, silo_sled_22t]
- constant_accel: vehicle clamped to the carriage during any hold before the push [silo_instant, silo_cold, silo_cold_lag, silo_hot_ramp_on_track, silo_hot_full, silo_hot_full_impinged, silo_failed, silo_sled_22t]
- constant_accel: exhaust impingement fraction 1 (assumed); the system keeps (1 - f_imp) T of the on-track thrust [silo_hot_full_impinged]
- failed ignition: the fall-back coast is drag-free (no atmosphere in Phase 1; docs/physics.md, 'Failed-ignition coast', gives the order of magnitude of the neglected drag for the F9 class at its exit speed) [silo_failed]
- failed ignition: no abort is modelled (a tilted exit that carries the vehicle clear of the mouth is the planar branch of Phase 2/3); Coriolis drift during the coast is neglected (omega_p = 0) [silo_failed]
- failed ignition: the braked carriage parks its braking distance beyond the track exit, in the fall-back path (failed_carriage_alt_m); the vehicle would meet it there first, on the way down (failed_t_carriage_s, failed_speed_at_carriage_mps, from the drag-free coast), unless the carriage is withdrawn in time, and no impact with it is modelled: the return to the mouth, the impact at the ground and the shaft-bottom speed are the obstacle-free values [silo_failed]
- failed ignition: the speed at the shaft bottom is derived from the impact speed at the ground and the fall from there to the track start (v^2 = v_impact^2 + 2 g_eff (z_impact - z_track_start)), not integrated [silo_failed]
- constant_accel: carriage mass 22 t (assumed) [silo_sled_22t]

## Checks

- pad_instant: delta speed at stage1_burnout +5.57637 = +0 (speed at release) + +15.2007 (dv_vac) - +9.79829 (gravity, duration) - -0.174001 (gravity, altitude) - +0 (drag) - +0 (steering) - +0 (back-pressure); residual 8.35e-14 m/s: closes (< 0.01 m/s)
- silo_instant: delta speed at stage1_burnout +84.7667 = +76.7072 (speed at release) + +15.2007 (dv_vac) - +9.79829 (gravity, duration) - -2.65714 (gravity, altitude) - +0 (drag) - +0 (steering) - +0 (back-pressure); residual -3.84e-13 m/s: closes (< 0.01 m/s)
- silo_cold: delta speed at stage1_burnout +69.6421 = +76.7072 (speed at release) + +15.2007 (dv_vac) - +24.4957 (gravity, duration) - -2.22998 (gravity, altitude) - +0 (drag) - +0 (steering) - +0 (back-pressure); residual 4.12e-13 m/s: closes (< 0.01 m/s)
- silo_cold_lag: delta speed at stage1_burnout +69.6443 = +76.7072 (speed at release) + +15.2007 (dv_vac) - +24.4957 (gravity, duration) - -2.23224 (gravity, altitude) - +0 (drag) - +0 (steering) - +0 (back-pressure); residual -2.36e-12 m/s: closes (< 0.01 m/s)
- silo_hot_ramp_on_track: delta speed at stage1_burnout +79.1567 = +76.7072 (speed at release) + -2.65777e-08 (dv_vac) - +0 (gravity, duration) - -2.44955 (gravity, altitude) - +0 (drag) - +0 (steering) - +0 (back-pressure); residual 1.34e-12 m/s: closes (< 0.01 m/s)
- silo_hot_full: delta speed at stage1_burnout +64.1707 = +76.7072 (speed at release) + -39.9929 (dv_vac) - -25.5472 (gravity, duration) - -1.9092 (gravity, altitude) - +0 (drag) - +0 (steering) - +0 (back-pressure); residual -6.82e-13 m/s: closes (< 0.01 m/s)
- silo_hot_full_impinged: delta speed at stage1_burnout +64.1707 = +76.7072 (speed at release) + -39.9929 (dv_vac) - -25.5472 (gravity, duration) - -1.9092 (gravity, altitude) - +0 (drag) - +0 (steering) - +0 (back-pressure); residual -6.82e-13 m/s: closes (< 0.01 m/s)
- silo_failed: delta speed at end vs stage1_burnout -2480.94 = +76.7072 (speed at release) + -3970.27 (dv_vac) - -1427.55 (gravity, duration) - +14.9193 (gravity, altitude) - +0 (drag) - +0 (steering) - +0 (back-pressure); residual 0 m/s: closes (< 0.01 m/s) (not a figure of merit: the identity point is not a stage-1 burnout on both sides, so this delta speed is the difference of two exact budgets at unlike points)
- silo_sled_22t: delta speed at stage1_burnout +69.6421 = +76.7072 (speed at release) + +15.2007 (dv_vac) - +24.4957 (gravity, duration) - -2.22998 (gravity, altitude) - +0 (drag) - +0 (steering) - +0 (back-pressure); residual 4.12e-13 m/s: closes (< 0.01 m/s)

- pad_instant: gain +5.57637 m/s against the bound +0 (speed at release) +5.40237 (hold-down credit) +0.174001 (altitude term): excess 0 (|excess| < 1e-06) m/s
- silo_instant: gain +84.7667 m/s against the bound +76.7072 (speed at release) +5.40237 (hold-down credit) +2.65714 (altitude term): excess 0 (|excess| < 1e-06) m/s
- silo_cold: gain +69.6421 m/s against the bound +76.7072 (speed at release) +5.40237 (hold-down credit) +2.22998 (altitude term): excess -14.6974 m/s
- silo_cold_lag: gain +69.6443 m/s against the bound +76.7072 (speed at release) +5.40237 (hold-down credit) +2.23224 (altitude term): excess -14.6974 m/s
- silo_hot_ramp_on_track: gain +79.1567 m/s against the bound +76.7072 (speed at release) +0 (hold-down credit) +2.44955 (altitude term): excess 0 (|excess| < 1e-06) m/s
- silo_hot_full: gain +64.1707 m/s against the bound +76.7072 (speed at release) -14.4457 (hold-down credit) +1.9092 (altitude term): excess 0 (|excess| < 1e-06) m/s
- silo_hot_full_impinged: gain +64.1707 m/s against the bound +76.7072 (speed at release) -14.4457 (hold-down credit) +1.9092 (altitude term): excess 0 (|excess| < 1e-06) m/s
- silo_sled_22t: gain +69.6421 m/s against the bound +76.7072 (speed at release) +5.40237 (hold-down credit) +2.22998 (altitude term): excess -14.6974 m/s

No variant exceeds its release speed + hold-down credit + altitude term by more than 0.01 m/s.
Not checkable (no stage-1 burnout on both sides, or no flight budget): silo_failed

- pad_instant: payload equivalent 49.1403 kg exceeds the README yardstick 0 kg at its release speed; the +5.57637 m/s beyond the release speed are the hold-down credit +5.40237 and the altitude term +0.174001 m/s (unexplained 0 (|excess| < 1e-06) m/s)
- silo_instant: payload equivalent 757.818 kg exceeds the README yardstick 684.758 kg at its release speed; the +8.05951 m/s beyond the release speed are the hold-down credit +5.40237 and the altitude term +2.65714 m/s (unexplained 0 (|excess| < 1e-06) m/s)
- silo_hot_ramp_on_track: payload equivalent 706.941 kg exceeds the README yardstick 684.758 kg at its release speed; the +2.44955 m/s beyond the release speed are the hold-down credit +0 and the altitude term +2.44955 m/s (unexplained 0 (|excess| < 1e-06) m/s)
A payload equivalent above the README yardstick at the release speed is the hold-down credit and the altitude term in kg (ideal rocket equation, both); the bound lines above say whether anything else contributed.
