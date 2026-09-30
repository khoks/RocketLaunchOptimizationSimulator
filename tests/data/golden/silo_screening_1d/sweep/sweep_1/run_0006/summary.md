# silo_screening_1d (<timestamp>, git <label>)

Comparison basis: sweep-optimized (Phase 1 has no guidance parameters); 1-D vertical, vacuum thrust, no drag, no rotation, no throttling

- Vehicle: generic_f9_class
- Baseline: pad
- Sweep: sweep_1, point 6 of 12 (of silo_cold): assist.net_accel_g = 1, assist.stroke_m = 300

## Variants against the baseline

| quantity | pad (baseline) | run_0006 |
|---|---|---|
| status | nominal | nominal |
| flags (see Flags) | - | - |
| stage-1 ignition, t_ign relative to release [s] (negative = lit before release) | -2 | 0.5 |
| stage-1 startup kind (step = instant full thrust: a yardstick, not achievable) | ramp | ramp |
|   its t_ramp or tau [s] | 2 | 2 |
| speed at release [m/s] | 0 | 76.7072 |
|   delta vs baseline [m/s] | (baseline) | 76.7072 |
| propellant burned before release [kg] | 2697.46 | 0 |
|   its dv_vac equivalent [m/s] | 15.2007 | 0 |
| stage-1 burnout speed [m/s] | 2557.65 | 2627.29 |
|   delta vs baseline [m/s] | (baseline) | 69.6421 |
| stage-1 burnout altitude [m] | 124667 | 134771 |
|   delta vs baseline [m] | (baseline) | 10104 |
| identity point (stage1_burnout, or the run's end) | (baseline) | stage1_burnout |
| identity: delta speed there [m/s] | (baseline) | 69.6421 |
|   = delta speed at release [m/s] | (baseline) | 76.7072 |
|   + delta dv_vac [m/s] | (baseline) | 15.2007 |
|   - delta gravity loss, duration part [m/s] | (baseline) | 24.4957 |
|   - delta gravity loss, altitude part [m/s] | (baseline) | -2.22998 |
|   - delta drag loss [m/s] | (baseline) | 0 |
|   - delta steering loss [m/s] | (baseline) | 0 |
|   - delta back-pressure loss [m/s] | (baseline) | 0 |
|   identity residual [m/s] (must be < 0.01) | (baseline) | 0 |
| hold-down credit vs baseline [m/s] (baseline's pre-flight burn cost minus this run's) | (baseline) | 5.40237 |
|   pre-flight burn cost of this run [m/s] (c ln(m0/m_flight) - g_eff dt_full) | 5.40237 | 0 |
| ignition loss, integrated vs silo_instant [m/s] (same release state only) | (baseline) | n/a |
| ignition loss, constant-g formula vs an instant start at release [m/s] | 5.40237 | 14.6974 |
| ideal-screening payload equivalent of the burnout speed delta [kg] (ideal rocket equation at fixed losses; not a payload result) | (baseline) | 620.888 |
|   ideal screening at this run's speed at release [kg] (the README yardstick; same equation, not a payload result) | (baseline) | 684.758 |
| gravity loss [m/s] | 1412.63 | 1434.89 |
|   duration part [m/s] | 1427.55 | 1452.04 |
|   altitude part [m/s] | -14.9193 | -17.1493 |
| drag loss [m/s] | 0 | 0 |
| steering loss [m/s] | 0 | 0 |
| back-pressure loss [m/s] | 0 | 0 |
| dv_vac from the flight start [m/s] | 3970.27 | 3985.47 |
| max-Q [Pa] | n/a (Phase 2) | n/a (Phase 2) |
| peak felt axial g, run-wide [g0] (phase) | 5.71192 (BURN) | 5.71192 (BURN) |
|   at t after release [s] | 145.694 | 148.194 |
|   mass there [kg] | 146870 | 146870 |
| peak felt g on the track [g0] | n/a | 1.99915 |
|   at t after release [s] | n/a | -7.82195 |
|   mass there [kg] | n/a | 542570 |
| peak felt g in flight [g0] | 5.71192 | 5.71192 |
|   at t after release [s] | 145.694 | 148.194 |
|   mass there [kg] | 146870 | 146870 |
| interface force, peak [N] | 0 | 1.0637e+07 |
| interface force, minimum [N] | 0 | 1.0637e+07 |
| hold-down force m g_eff - T, minimum over the hold [N] (negative = the clamps in tension, holding the vehicle down) | -2.93707e+06 | n/a |
| peak track-normal g [g0] | 0 | 0 |
|   vehicle [g0] | 0 | 0 |
|   carriage [g0] | 0 | 0 |
| assist (drive) energy [J] | 0 | 3.19111e+09 |
| assist (drive) energy [kWh] | 0 | 886.421 |
| electrical energy [J] (positive drive work / efficiency) | 0 | 6.38223e+09 |
| electrical energy [kWh] | 0 | 1772.84 |
| peak drive power [W] | 0 | 8.15938e+08 |
| braking (negative) drive power, minimum [W] | 0 | 0 |
| braking distance [m] | 0 | 60 |
| facility length incl. braking [m] | 0 | 360 |

## Sensitivity

(no sensitivity cases: a sweep point runs none)

## Flags

(none)

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
- track phase: 1-DOF along the track in a flat local frame with constant g_eff; the carriage stays on the track at release; carriage braking is not modelled as a phase (its distance v^2/(2 a_brake) is added to the facility length) [all variants]
- hot start: the propellant burned before release is reported with its delta-v equivalent; the exhaust impingement fraction f_imp on the carriage is an assumed amendment to the track equation (the system keeps (1 - f_imp) T) [all variants]
- drive energy: electrical_energy = (positive drive work) / efficiency; no regeneration is credited for any negative (braking) drive work [all variants]
- track: straight, L = 300 m at 1.5708 rad above horizontal, start altitude -300 m (exit at 0 m) [all variants]
- constant_accel: prescribed net acceleration 1 g0 (assumed); drive force unconstrained, solved from the track equation [all variants]
- constant_accel: carriage mass 0 t (assumed) [all variants]
- constant_accel: braking deceleration 5 g0 (assumed) [all variants]
- constant_accel: drive efficiency 0.5 (assumed) [all variants]
- constant_accel: exhaust impingement fraction 0 (assumed); the system keeps (1 - f_imp) T of the on-track thrust [all variants]
- constant_accel: shaft vented (no air column), no friction [all variants]
- constant_accel: constant g_eff = 9.798285 m/s^2 on the track, omega_p = 0, Coriolis neglected [all variants]
- constant_accel: infinite jerk at push start and release [all variants]
- constant_accel: vehicle clamped to the carriage during any hold before the push [all variants]

## Checks

- run_0006: delta speed at stage1_burnout +69.6421 = +76.7072 (speed at release) + +15.2007 (dv_vac) - +24.4957 (gravity, duration) - -2.22998 (gravity, altitude) - +0 (drag) - +0 (steering) - +0 (back-pressure); residual 3.98e-13 m/s: closes (< 0.01 m/s)

- run_0006: gain +69.6421 m/s against the bound +76.7072 (speed at release) +5.40237 (hold-down credit) +2.22998 (altitude term): excess -14.6974 m/s

No variant exceeds its release speed + hold-down credit + altitude term by more than 0.01 m/s.

No variant's ideal-screening payload equivalent exceeds the README yardstick at its release speed.
