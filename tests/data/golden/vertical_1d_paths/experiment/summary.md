# vertical_1d_paths (<timestamp>, git <label>)

Comparison basis: sweep-optimized (Phase 1 has no guidance parameters); 1-D vertical, vacuum thrust, no drag, no rotation, no throttling

- Vehicle: generic_f9_class
- Baseline: pad

## Variants against the baseline

| quantity | pad (baseline) | pad_apex | pad_no_liftoff | silo_drive_limit | silo_coast_ign | silo_fallback_ign |
|---|---|---|---|---|---|---|
| status | nominal | nominal | no_liftoff | drive_limit | nominal | nominal |
| flags (see Flags) | - | - | 1 | 2 | - | - |
| stage-1 ignition, t_ign relative to release [s] (negative = lit before release) | -2 | -2 | n/a | n/a | 3 | 10 |
| stage-1 startup kind (step = instant full thrust: a yardstick, not achievable) | ramp | ramp | ramp | ramp | ramp | ramp |
|   its t_ramp or tau [s] | 2 | 2 | 2 | 2 | 2 | 2 |
| speed at release [m/s] | 0 | 0 | 0 | n/a | 76.7072 | 76.7072 |
|   delta vs baseline [m/s] | (baseline) | 0 | 0 | n/a | 76.7072 | 76.7072 |
| propellant burned before release [kg] | 2697.46 | 2697.46 | 0 | n/a | 0 | 0 |
|   its dv_vac equivalent [m/s] | 15.2007 | 15.2007 | 0 | n/a | 0 | 0 |
| propellant burned before the free flight (incl. a hold extension) [kg] | 2697.46 | 2697.46 | n/a | n/a | 0 | 0 |
|   its dv_vac equivalent [m/s] | 15.2007 | 15.2007 | n/a | n/a | 0 | 0 |
| stage-1 burnout speed [m/s] | 2557.65 | 2557.65 | n/a | n/a | 2602.06 | 2531.26 |
|   delta vs baseline [m/s] | (baseline) | 0 | n/a | n/a | 44.4109 | -26.3844 |
| stage-1 burnout altitude [m] | 124667 | 124667 | n/a | n/a | 131267 | 121120 |
|   delta vs baseline [m] | (baseline) | 0 | n/a | n/a | 6600.23 | -3546.72 |
| identity point (stage1_burnout, or the run's end) | (baseline) | stage1_burnout | n/a | n/a | stage1_burnout | stage1_burnout |
| identity: delta speed there [m/s] | (baseline) | 0 | n/a | n/a | 44.4109 | -26.3844 |
|   = delta speed at release [m/s] | (baseline) | 0 | n/a | n/a | 76.7072 | 76.7072 |
|   + delta dv_vac [m/s] | (baseline) | 0 | n/a | n/a | 15.2007 | 15.2007 |
|   - delta gravity loss, duration part [m/s] | (baseline) | 0 | n/a | n/a | 48.9914 | -53.6816 |
|   - delta gravity loss, altitude part [m/s] | (baseline) | 0 | n/a | n/a | -1.49454 | 0.724964 |
|   - delta drag loss [m/s] | (baseline) | 0 | n/a | n/a | 0 | 0 |
|   - delta steering loss [m/s] | (baseline) | 0 | n/a | n/a | 0 | 171.249 |
|   - delta back-pressure loss [m/s] | (baseline) | 0 | n/a | n/a | 0 | 0 |
|   identity residual [m/s] (must be < 0.01) | (baseline) | 0 | n/a | n/a | 0 | 0 |
| hold-down credit vs baseline [m/s] (baseline's pre-flight burn cost minus this run's) | (baseline) | 0 | n/a | n/a | 5.40237 | 5.40237 |
|   pre-flight burn cost of this run [m/s] (c ln(m0/m_flight) - g_eff dt_full) | 5.40237 | 5.40237 | n/a | n/a | 0 | 0 |
| ignition loss, integrated vs silo_instant [m/s] (same release state only) | (baseline) | n/a | n/a | n/a | n/a | n/a |
| ignition loss, constant-g formula vs an instant start at release [m/s] | 5.40237 | 5.40237 | n/a | n/a | 39.1931 | 107.781 |
| ideal-screening payload equivalent of the burnout speed delta [kg] (ideal rocket equation at fixed losses; not a payload result) | (baseline) | 0 | n/a | n/a | 394.128 | -231.165 |
|   ideal screening at this run's speed at release [kg] (the README yardstick; same equation, not a payload result) | (baseline) | 0 | 0 | n/a | 684.758 | 684.758 |
| gravity loss [m/s] | 4113.81 | 9081.03 | 0 | 0 | 4150.6 | 4066.95 |
|   duration part [m/s] | 4615.73 | 14416.3 | 0 | 0 | 4664.72 | 4562.05 |
|   altitude part [m/s] | -501.914 | -5335.28 | 0 | 0 | -514.123 | -495.097 |
| drag loss [m/s] | 0 | 0 | 0 | 0 | 0 | 0 |
| steering loss [m/s] | 0 | 0 | 0 | 0 | 0 | 171.249 |
| back-pressure loss [m/s] | 0 | 0 | 0 | 0 | 0 | 0 |
| dv_vac from the flight start [m/s] | 9081.03 | 9081.03 | 0 | 0 | 9096.23 | 9096.23 |
| max-Q [Pa] | n/a (Phase 2) | n/a (Phase 2) | n/a (Phase 2) | n/a (Phase 2) | n/a (Phase 2) | n/a (Phase 2) |
| peak felt axial g, run-wide [g0] (phase) | 5.71192 (BURN) | 5.71192 (BURN) | 0.999147 (HOLD) | 1.49915 (ASSIST) | 5.71192 (BURN) | 5.71192 (BURN) |
|   at t after release [s] | 145.694 | 145.694 | 0 | n/a | 150.694 | 157.694 |
|   mass there [kg] | 146870 | 146870 | 542570 | 542570 | 146870 | 146870 |
| peak felt g on the track [g0] | n/a | n/a | n/a | 1.49915 | 3.99915 | 3.99915 |
|   at t after release [s] | n/a | n/a | n/a | n/a | -2.60732 | -2.60732 |
|   mass there [kg] | n/a | n/a | n/a | 542570 | 542570 | 542570 |
| peak felt g in flight [g0] | 5.71192 | 5.71192 | n/a | n/a | 5.71192 | 5.71192 |
|   at t after release [s] | 145.694 | 145.694 | n/a | n/a | 150.694 | 157.694 |
|   mass there [kg] | 146870 | 146870 | n/a | n/a | 146870 | 146870 |
| interface force, peak [N] | 0 | 0 | 0 | 7.97665e+06 | 2.12786e+07 | 2.12786e+07 |
| interface force, minimum [N] | 0 | 0 | 0 | -1.86265e-09 | 2.12786e+07 | 2.12786e+07 |
| hold-down force m g_eff - T, minimum over the hold [N] (negative = the clamps in tension, holding the vehicle down) | -2.93707e+06 | -2.93707e+06 | 5.31626e+06 | n/a | n/a | n/a |
| peak track-normal g [g0] | 0 | 0 | 0 | 0 | 0 | 0 |
|   vehicle [g0] | 0 | 0 | 0 | 0 | 0 | 0 |
|   carriage [g0] | 0 | 0 | 0 | 0 | 0 | 0 |
| assist (drive) energy [J] | 0 | 0 | 0 | 1.78177e+08 | 2.12786e+09 | 2.12786e+09 |
| assist (drive) energy [kWh] | 0 | 0 | 0 | 49.4935 | 591.073 | 591.073 |
| electrical energy [J] (positive drive work / efficiency) | 0 | 0 | 0 | 3.56353e+08 | 4.25573e+09 | 4.25573e+09 |
| electrical energy [kWh] | 0 | 0 | 0 | 98.987 | 1182.15 | 1182.15 |
| peak drive power [W] | 0 | 0 | 0 | 7.82242e+07 | 1.63222e+09 | 1.63222e+09 |
| braking (negative) drive power, minimum [W] | 0 | 0 | 0 | -3.5895e-08 | 0 | 0 |
| braking distance [m] | 0 | 0 | 0 | n/a | 60 | 60 |
| facility length incl. braking [m] | 0 | 0 | 0 | n/a | 160 | 160 |
| failed ignition: stage | n/a | n/a | stage1 | n/a | n/a | n/a |
|   apex altitude of the fall-back coast [m] | n/a | n/a | n/a | n/a | n/a | n/a |
|   time of that apex after release [s] | n/a | n/a | n/a | n/a | n/a | n/a |
|   parked carriage altitude [m] | n/a | n/a | n/a | n/a | n/a | n/a |
|   time the vehicle comes down to the carriage [s] | n/a | n/a | n/a | n/a | n/a | n/a |
|   speed there [m/s] | n/a | n/a | n/a | n/a | n/a | n/a |
|   return to the release altitude [s] | n/a | n/a | n/a | n/a | n/a | n/a |
|   impact speed at the ground [m/s] | n/a | n/a | n/a | n/a | n/a | n/a |
|   speed at the shaft bottom [m/s] (derived) | n/a | n/a | n/a | n/a | n/a | n/a |

## Sensitivity

(no sensitivity block declared; C_D: n/a: no drag in Phase 1)

## Flags

- pad_no_liftoff: no_liftoff: thrust never exceeded the weight by t_max = 60 s
- silo_drive_limit: drive_limit: the drive force crossed zero at t = 3.93018 s (the prescribed acceleration would need the drive to brake the engine); the run stopped on the track, interface_tensile: the carriage-vehicle interface force reaches -1.86265e-09 N (tension) at t = 3.93018 s during the push

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
- track phase: 1-DOF along the track in a flat local frame with constant g_eff; the carriage stays on the track at release; carriage braking is not modelled as a phase (its distance v^2/(2 a_brake) is added to the facility length) [silo_drive_limit, silo_coast_ign, silo_fallback_ign]
- hot start: the propellant burned before release is reported with its delta-v equivalent; the exhaust impingement fraction f_imp on the carriage is an assumed amendment to the track equation (the system keeps (1 - f_imp) T) [silo_drive_limit, silo_coast_ign, silo_fallback_ign]
- drive energy: electrical_energy = (positive drive work) / efficiency; no regeneration is credited for any negative (braking) drive work [silo_drive_limit, silo_coast_ign, silo_fallback_ign]
- track: straight, L = 100 m at 1.5708 rad above horizontal, start altitude -100 m (exit at 0 m) [silo_drive_limit, silo_coast_ign, silo_fallback_ign]
- constant_accel: prescribed net acceleration 0.5 g0 (assumed); drive force unconstrained, solved from the track equation [silo_drive_limit]
- constant_accel: carriage mass 0 t (assumed) [silo_drive_limit, silo_coast_ign, silo_fallback_ign]
- constant_accel: braking deceleration 5 g0 (assumed) [silo_drive_limit, silo_coast_ign, silo_fallback_ign]
- constant_accel: drive efficiency 0.5 (assumed) [silo_drive_limit, silo_coast_ign, silo_fallback_ign]
- constant_accel: exhaust impingement fraction 0 (assumed); the system keeps (1 - f_imp) T of the on-track thrust [silo_drive_limit, silo_coast_ign, silo_fallback_ign]
- constant_accel: shaft vented (no air column), no friction [silo_drive_limit, silo_coast_ign, silo_fallback_ign]
- constant_accel: constant g_eff = 9.798285 m/s^2 on the track, omega_p = 0, Coriolis neglected [silo_drive_limit, silo_coast_ign, silo_fallback_ign]
- constant_accel: infinite jerk at push start and release [silo_drive_limit, silo_coast_ign, silo_fallback_ign]
- constant_accel: vehicle clamped to the carriage during any hold before the push [silo_drive_limit, silo_coast_ign, silo_fallback_ign]
- constant_accel: prescribed net acceleration 3 g0 (assumed); drive force unconstrained, solved from the track equation [silo_coast_ign, silo_fallback_ign]

## Checks

- pad_apex: delta speed at stage1_burnout +0 = +0 (speed at release) + +0 (dv_vac) - +0 (gravity, duration) - +0 (gravity, altitude) - +0 (drag) - +0 (steering) - +0 (back-pressure); residual 0 m/s: closes (< 0.01 m/s)
- pad_no_liftoff: identity line n/a (a run without a flight budget)
- silo_drive_limit: identity line n/a (a run without a flight budget)
- silo_coast_ign: delta speed at stage1_burnout +44.4109 = +76.7072 (speed at release) + +15.2007 (dv_vac) - +48.9914 (gravity, duration) - -1.49454 (gravity, altitude) - +0 (drag) - +0 (steering) - +0 (back-pressure); residual 1.66e-12 m/s: closes (< 0.01 m/s)
- silo_fallback_ign: delta speed at stage1_burnout -26.3844 = +76.7072 (speed at release) + +15.2007 (dv_vac) - -53.6816 (gravity, duration) - +0.724964 (gravity, altitude) - +0 (drag) - +171.249 (steering) - +0 (back-pressure); residual 2.84e-13 m/s: closes (< 0.01 m/s)

- pad_apex: gain +0 m/s against the bound +0 (speed at release) +0 (hold-down credit) +0 (altitude term): excess 0 (|excess| < 1e-06) m/s
- silo_coast_ign: gain +44.4109 m/s against the bound +76.7072 (speed at release) +5.40237 (hold-down credit) +1.49454 (altitude term): excess -39.1931 m/s
- silo_fallback_ign: gain -26.3844 m/s against the bound +76.7072 (speed at release) +5.40237 (hold-down credit) -0.724964 (altitude term): excess -107.769 m/s

No variant exceeds its release speed + hold-down credit + altitude term by more than 0.01 m/s.
Not checkable (no stage-1 burnout on both sides, or no flight budget): pad_no_liftoff, silo_drive_limit

No variant's ideal-screening payload equivalent exceeds the README yardstick at its release speed.
