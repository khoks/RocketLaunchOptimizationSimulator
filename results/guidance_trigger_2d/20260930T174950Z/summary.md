# guidance_trigger_2d: sweeps

Comparison basis: sweep-optimized (every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, delta and the LTG pair are solved per run); planar_2d: rotating spherical Earth, ICAO atmosphere, drag, back-pressure, unthrottled; figure of merit: payload capacity P* at the target orbit

Guidance is sweep-optimized: every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, the kick angle delta and the LTG pair (a, b) are solved per run. Not an optimal-control solution (Phase 5).

- Baseline: pad (status inserted)
- Timestamp (UTC): 20260930T174950Z
- Git: 7ad381f227a9

## sweep_1: silo_cold over guidance.kick.v_kick_mps

Paired sweep: every point is compared with the baseline re-run under the same overrides (column paired_baseline), not with the experiment's baseline.

| point | guidance.kick.v_kick_mps | run_dir | of | paired_baseline | exit_speed_mps | payload_kg | payload_delta_kg | ideal_screening_payload_at_release_speed_at_pbase_kg | screening_yardstick_kg | payload_beyond_screening_kg | gamma_star_rad | speed_at_kick_mps | peak_q_alpha | delta_peak_q_alpha | max_q_pa | delta_max_q_pa | facility_length_m | drive_energy_J | drive_power_peak_W | kick_regime | unconstrained_kick | payload_delta_upper_bound | search_status | screening_status | screening_diagnostic_failed | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 30 | sweep_1/run_0001 | silo_cold | run_0001__pad | 76.7072 | 27553.2 | 1498.11 | 765.462 | 675.346 | 822.763 | 0.377803 | 71.8083 | 129.916 | 119.347 | 31237.6 | -5952.44 | 160 | 2.24905e+09 | 1.72518e+09 | at_first_lit_instant | False | True | ok | ok | none | inserted |
| 2 | 50 | sweep_1/run_0002 | silo_cold | run_0002__pad | 76.7072 | 27553.2 | 1498.83 | 765.442 | 675.346 | 823.485 | 0.377803 | 71.8083 | 129.916 | 55.1852 | 31237.6 | -5953.74 | 160 | 2.24905e+09 | 1.72518e+09 | at_first_lit_instant | False | True | ok | ok | none | inserted |
| 3 | 80 | sweep_1/run_0003 | silo_cold | run_0003__pad | 76.7072 | 27550.6 | 1502.9 | 765.255 | 675.346 | 827.553 | 0.377888 | 80 | 306.501 | -157.312 | 31238.2 | -5952.74 | 160 | 2.24904e+09 | 1.72517e+09 | after_vertical_rise | False | False | ok | ok | none | inserted |
| 4 | 120 | sweep_1/run_0004 | silo_cold | run_0004__pad | 76.7072 | 27526.6 | 1514.04 | 764.273 | 675.346 | 838.694 | 0.378638 | 120 | 1520.53 | -421.103 | 31188.3 | -5904.24 | 160 | 2.24894e+09 | 1.7251e+09 | after_vertical_rise | False | False | ok | ok | none | inserted |

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
- track: straight, L = 100 m at 1.5708 rad above horizontal, start altitude -100 m (exit at 0 m) [all sweep points]
- constant_accel: prescribed net acceleration 3 g0 (assumed); drive force unconstrained, solved from the track equation [all sweep points]
- constant_accel: carriage mass 0 t (assumed) [all sweep points]
- constant_accel: braking deceleration 5 g0 (assumed) [all sweep points]
- constant_accel: drive efficiency 0.5 (assumed) [all sweep points]
- constant_accel: exhaust impingement fraction 0 (assumed); the system keeps (1 - f_imp) T of the on-track thrust [all sweep points]
- constant_accel: shaft vented (no air column), no friction [all sweep points]
- constant_accel: constant g_eff = 9.772092 m/s^2 on the track (mu/R_E^2 - omega_p^2 R_E with omega_p = 6.408435e-05 rad/s, the planar rotation rate of the site), flat 1-DOF track frame, Coriolis neglected [all sweep points]
- constant_accel: infinite jerk at push start and release [all sweep points]
- constant_accel: vehicle clamped to the carriage during any hold before the push [all sweep points]

## Checks

- pad: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.45116e-08: ok
- sweep_1/run_0001: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35972e-08: ok
- sweep_1/run_0001__pad: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.45656e-08: ok
- sweep_1/run_0002: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35972e-08: ok
- sweep_1/run_0002__pad: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.45116e-08: ok
- sweep_1/run_0003: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35931e-08: ok
- sweep_1/run_0003__pad: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.46554e-08: ok
- sweep_1/run_0004: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35722e-08: ok
- sweep_1/run_0004__pad: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.45333e-08: ok

- sweep_1/run_0001: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_1/run_0002: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_1/run_0003: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)
- sweep_1/run_0004: screening status ok (failed checks: none; failed diagnostic checks: none; gamma*-sensitive: none)

No run and no comparison is bug_suspect.
