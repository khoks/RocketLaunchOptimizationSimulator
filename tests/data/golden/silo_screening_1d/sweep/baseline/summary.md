# silo_screening_1d (<timestamp>, git <label>)

Comparison basis: sweep-optimized (Phase 1 has no guidance parameters); 1-D vertical, vacuum thrust, no drag, no rotation, no throttling

- Vehicle: generic_f9_class
- Baseline: pad

## Variants against the baseline

| quantity | pad (baseline) |
|---|---|
| status | nominal |
| flags (see Flags) | - |
| stage-1 ignition, t_ign relative to release [s] (negative = lit before release) | -2 |
| stage-1 startup kind (step = instant full thrust: a yardstick, not achievable) | ramp |
|   its t_ramp or tau [s] | 2 |
| speed at release [m/s] | 0 |
|   delta vs baseline [m/s] | (baseline) |
| propellant burned before release [kg] | 2697.46 |
|   its dv_vac equivalent [m/s] | 15.2007 |
| stage-1 burnout speed [m/s] | 2557.65 |
|   delta vs baseline [m/s] | (baseline) |
| stage-1 burnout altitude [m] | 124667 |
|   delta vs baseline [m] | (baseline) |
| identity point (stage1_burnout, or the run's end) | (baseline) |
| identity: delta speed there [m/s] | (baseline) |
|   = delta speed at release [m/s] | (baseline) |
|   + delta dv_vac [m/s] | (baseline) |
|   - delta gravity loss, duration part [m/s] | (baseline) |
|   - delta gravity loss, altitude part [m/s] | (baseline) |
|   - delta drag loss [m/s] | (baseline) |
|   - delta steering loss [m/s] | (baseline) |
|   - delta back-pressure loss [m/s] | (baseline) |
|   identity residual [m/s] (must be < 0.01) | (baseline) |
| hold-down credit vs baseline [m/s] (baseline's pre-flight burn cost minus this run's) | (baseline) |
|   pre-flight burn cost of this run [m/s] (c ln(m0/m_flight) - g_eff dt_full) | 5.40237 |
| ignition loss, integrated vs silo_instant [m/s] (same release state only) | (baseline) |
| ignition loss, constant-g formula vs an instant start at release [m/s] | 5.40237 |
| ideal-screening payload equivalent of the burnout speed delta [kg] (ideal rocket equation at fixed losses; not a payload result) | (baseline) |
|   ideal screening at this run's speed at release [kg] (the README yardstick; same equation, not a payload result) | (baseline) |
| gravity loss [m/s] | 1412.63 |
|   duration part [m/s] | 1427.55 |
|   altitude part [m/s] | -14.9193 |
| drag loss [m/s] | 0 |
| steering loss [m/s] | 0 |
| back-pressure loss [m/s] | 0 |
| dv_vac from the flight start [m/s] | 3970.27 |
| max-Q [Pa] | n/a (Phase 2) |
| peak felt axial g, run-wide [g0] (phase) | 5.71192 (BURN) |
|   at t after release [s] | 145.694 |
|   mass there [kg] | 146870 |
| peak felt g on the track [g0] | n/a |
|   at t after release [s] | n/a |
|   mass there [kg] | n/a |
| peak felt g in flight [g0] | 5.71192 |
|   at t after release [s] | 145.694 |
|   mass there [kg] | 146870 |
| interface force, peak [N] | 0 |
| interface force, minimum [N] | 0 |
| hold-down force m g_eff - T, minimum over the hold [N] (negative = the clamps in tension, holding the vehicle down) | -2.93707e+06 |
| peak track-normal g [g0] | 0 |
|   vehicle [g0] | 0 |
|   carriage [g0] | 0 |
| assist (drive) energy [J] | 0 |
| assist (drive) energy [kWh] | 0 |
| electrical energy [J] (positive drive work / efficiency) | 0 |
| electrical energy [kWh] | 0 |
| peak drive power [W] | 0 |
| braking (negative) drive power, minimum [W] | 0 |
| braking distance [m] | 0 |
| facility length incl. braking [m] | 0 |

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

## Checks

(no variants)


No variant exceeds its release speed + hold-down credit + altitude term by more than 0.01 m/s.

No variant's ideal-screening payload equivalent exceeds the README yardstick at its release speed.
