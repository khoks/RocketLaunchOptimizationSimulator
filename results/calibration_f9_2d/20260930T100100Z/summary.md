> **CALIBRATION, not validation.** This experiment compares the pad's payload capacity with a published figure as a benchmark, never a target: no parameter may be tuned toward it, and a miss (high or low) is reported as it is, with the same checklist as a pass (CLAUDE.md; docs/findings/CAL-f9-leo-2d.md holds the band verdict and the checklist).

- Pre-registered inputs: configs/ and experiments/ clean at commit c2849b72e01d.

# calibration_f9_2d (20260930T100100Z, git c2849b72e01d)

Comparison basis: sweep-optimized (every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, delta and the LTG pair are solved per run); planar_2d: rotating spherical Earth, ICAO atmosphere, drag, back-pressure, unthrottled; figure of merit: payload capacity P* at the target orbit

Guidance is sweep-optimized: every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, the kick angle delta and the LTG pair (a, b) are solved per run. Not an optimal-control solution (Phase 5).

- Vehicle: generic_f9_class_2d
- Baseline: pad
- Search budget id: a17a01601d0f4ae0c48cac48342127d5597e056e769da83503d7364c7d65a7df
- Timestamp (UTC): 20260930T100100Z
- Git: c2849b72e01d

## Variants against the baseline

| quantity | pad (baseline) |
|---|---|
| status | inserted |
| search status | ok |
| run checks (closure, loss identity, insertion e) | ok |
| screening status (closure, attribution, M2 to M5) | (baseline) |
| flags (see Flags) | - |
| stage-1 ignition, t_ign relative to release [s] (negative = lit before release) | -2 |
| stage-1 startup kind (step = instant full thrust: a yardstick, not achievable) | ramp |
|   its t_ramp or tau [s] | 2 |
| payload capacity P* [kg] (sweep-optimized) | 26054.4 |
|   dP* vs baseline [kg] | (baseline) |
|   ideal screening at this run's release speed, at the baseline's P* [kg] | (baseline) |
|   ideal screening at this run's release speed, at the vehicle payload P0 [kg] | (baseline) |
|   screening yardstick used, the stricter of the two [kg] | (baseline) |
|     its basis | (baseline) |
|   dP* beyond the screening yardstick [kg] | (baseline) |
|   beats the screening yardstick | (baseline) |
|   dP* is an unthrottled/unconstrained upper bound (max-Q, q-alpha or kick) | (baseline) |
|   payload excess P0 - P* [kg] | -3254.4 |
| residual propellant at P0 [kg] (signed; negative = virtual, massless shortfall) | 3235.4 |
|   its basis | at gamma*_ref (P*-optimal guidance) |
| dv margin at P0 [m/s] (signed) | 388.964 |
| gamma*_ref, the flight-path angle at MECO [deg] | 22.9892 |
| kick angle delta [deg] | 2.83434 |
| LTG a (tan of the initial pitch) | 0.610186 |
| LTG b [1/s] | 0.00156083 |
| kick regime | after_vertical_rise |
|   |v_rel| at the kick [m/s] | 50 |
|   unconstrained kick (faster than checks.unconstrained_kick_mps) | (baseline) |
|   kick steering loss [m/s] | 0.0258346 |
| speed at release [m/s] | 0 |
| propellant burned before the flight [kg] | 2697.46 |
|   its dv_vac equivalent [m/s] | 14.4078 |
| MECO: t after release [s] | 151.328 |
|   altitude [m] | 69486 |
|   |v_rel| [m/s] | 2665.03 |
|   gamma_rel [deg] | 22.9892 |
|   downrange [m] | 99170.9 |
| fairing drop | in the stage-2 burn (heating event) |
|   t after release [s] | 196.807 |
|   altitude [m] | 110483 |
| stage-2 end: t after release [s] | 536.301 |
|   eccentricity | 1.45442e-08 |
|   perigee altitude [m] | 200000 |
|   apogee altitude [m] | 200000 |
| gravity loss [m/s] | 1491.98 |
| drag loss [m/s] | 26.0362 |
| steering loss [m/s] | 88.9866 |
| back-pressure loss [m/s] | 63.1439 |
| dv_vac from the flight start [m/s] | 9032.85 |
|   loss-identity residual [m/s] | 5.93445e-09 |
| rocket-equation closure residual [m/s] | -1.84933e-07 |
|   pre-flight term c1 ln(m0/m_fs) [m/s] | 14.4078 |
|   fairing-carry term [m/s] | 3.23337 |
| max-Q [Pa] (unthrottled: an upper bound) | 37191.4 |
|   at t after release [s] | 65.7515 |
|   altitude [m] | 11019.1 |
|   Mach | 1.53218 |
|   above the baseline | (baseline) |
| peak q-alpha [Pa rad] (alpha = psi; unconstrained) | 74.7307 |
|   at t after release [s] | 12.4937 |
|   above the baseline | (baseline) |
| peak felt axial g, run-wide [g0] (phase) | 5.19547 (GRAVITY_TURN) |
| peak felt axial g in flight [g0] | 5.19547 |
| peak felt lateral g in flight [g0] | 6.39135e-05 |
| peak felt g on the track [g0] | n/a |
| interface force, peak [N] | 0 |
| interface force, minimum [N] | 0 |
| hold-down force m g_ref - T, minimum over the hold [N] | -2.04006e+06 |
| peak track-normal g [g0] | 0 |
|   vehicle [g0] | 0 |
|   carriage [g0] | 0 |
| assist (drive) energy [J] | 0 |
| assist (drive) energy [kWh] | 0 |
| electrical energy [kWh] (positive drive work / efficiency) | 0 |
| peak drive power [W] | 0 |
| braking distance [m] | 0 |
| facility length incl. braking [m] | 0 |
| search: P2 - P1 [kg] | 18.4366 |
|   search minus final payload [kg] | -0.0370332 |
| RHS evaluations of the recorded run | 3957 |

## Bounds

(no bounds declared)

## Cases

Independent runs: never compared with the baseline or with each other.

| case | status | search status | P* [kg] | gamma*_ref [deg] | MECO t [s] | MECO altitude [m] | fairing altitude [m] | max-Q [Pa] |
|---|---|---|---|---|---|---|---|---|
| readme_loads | inserted | ok | 24700 | 20.9443 | 145.694 | 67509.8 | 112094 | 42732.6 |
| recorded_scope | inserted | ok | 25416.3 | 23.4105 | 151.328 | 69174.3 | 110167 | 36641.9 |
| aref_fairing | inserted | ok | 25663.5 | 23.4036 | 151.328 | 69012.5 | 110283 | 35484.2 |
| alt_185 | inserted | ok | 26290.6 | 22.1162 | 151.328 | 68196.9 | 110690 | 37435.8 |
| alt_250 | inserted | ok | 25188.9 | 25.9519 | 151.328 | 73741.5 | 109941 | 36453.7 |
| alt_300 | inserted | ok | 24214.4 | 28.9599 | 151.328 | 77885 | 109553 | 35830.8 |
| no_rotation | inserted | ok | 22130 | 23.212 | 151.328 | 71096.1 | 110735 | 37330.5 |

## Sensitivity

| variant | parameter | change | value [SI] (unit in the cell) | value (in the parameter's YAML units) | status | P* [kg] | dP* vs baseline, unchanged [kg] | dP* vs baseline with the same vehicle perturbation [kg] | trajectory reused (energy-only or yardstick case) | beats the screening yardstick (vs the baseline of the same vehicle) | screening status (vs the baseline of the same vehicle) | electrical energy [kWh] | peak drive power [W] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pad | vehicle.stages.stage1.dry_mass_t | +10% | 24420 kg | 24.42 | inserted | 25661 | -393.396 | +0 | no | False | not_checked | 0 | 0 |
| pad | vehicle.stages.stage1.dry_mass_t | -10% | 19980 kg | 19.98 | inserted | 26456.3 | +401.858 | +0 | no | False | not_checked | 0 | 0 |
| pad | vehicle.stages.stage1.engine.isp_vac_s | +10% | 342.1 s | 342.1 | inserted | 29927.4 | +3872.97 | +0 | no | False | not_checked | 0 | 0 |
| pad | vehicle.stages.stage1.engine.isp_vac_s | -10% | 279.9 s | 279.9 | inserted | 22478.3 | -3576.1 | +0 | no | False | not_checked | 0 | 0 |
| pad | vehicle.stages.stage2.engine.isp_vac_s | +10% | 382.8 s | 382.8 | inserted | 30357.7 | +4303.27 | +0 | no | False | not_checked | 0 | 0 |
| pad | vehicle.stages.stage2.engine.isp_vac_s | -10% | 313.2 s | 313.2 | inserted | 21585 | -4469.37 | +0 | no | False | not_checked | 0 | 0 |
| pad | vehicle.aero.cd_scale | +10% | 1.1 - | 1.1 | inserted | 26015.5 | -38.9431 | +0 | no | False | not_checked | 0 | 0 |
| pad | vehicle.aero.cd_scale | -10% | 0.9 - | 0.9 | inserted | 26093.5 | +39.0716 | +0 | no | False | not_checked | 0 | 0 |

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
- site latitude 28.5 deg, azimuth 90 deg, rotation on: omega_p = 6.408435e-05 rad/s, g_ref = mu/R_E^2 - omega_p^2 R_E = 9.7720917 m/s^2 (the pad balance, the track's g_eff and the reference of the gravity-loss split) [pad, readme_loads, recorded_scope, aref_fairing, alt_185, alt_250, alt_300]
- target: circular orbit of radius 6578137 m (altitude 200000 m above R_E), energy cutoff [pad, readme_loads, recorded_scope, aref_fairing, no_rotation]
- drag: C_D(Mach) through the vehicle's 23-knot power-on table (PCHIP, held beyond the end knots) x cd_scale 1, on A_ref = 10.52 m^2 [pad, readme_loads, recorded_scope, alt_185, alt_250, alt_300, no_rotation]
- stage 2 (stage2) starts at full thrust (step startup); its exit area 8.6 m^2 (the vehicle file's value; the Phase 2 forks mark it assumed, not published) sets the back-pressure p A_e [all runs]
- fairing (1700 kg): dropped when 0.5 rho |v_rel|^3 < 1135 W/m^2 [pad, aref_fairing, alt_185, alt_250, alt_300, no_rotation]
- pad: held down to the release at t = 0 s; stage 1 lit at t = -2 s with a ramp startup, then clamped until its thrust exceeds its weight [all runs]
- atmosphere: ICAO standard atmosphere closed forms (layer table of ambiance.CONST) from -5,004 m to 81,020 m geometric altitude; the geometric to geopotential conversion uses the ICAO radius 6,356,766 m, not R_E. [all runs]
- atmosphere: above 81,020 m an isothermal extension at 196.649 K with scale height 5,908 m (R_air T_top / g(h_top)); not US76 (denser near 110 km, far thinner above 150 km). [all runs]
- atmosphere: static, spherically symmetric, no wind; it co-rotates with Earth, so drag and Mach use the Earth-relative velocity v_rel. [all runs]
- atmosphere: in flight, an altitude below the -5,004 m floor is held at the floor state (ambient_scalar clamp; a dive ends at the ground event). [all runs]
- fairing (1900 kg): dropped when 0.5 rho |v_rel|^3 < 1135 W/m^2 [readme_loads, recorded_scope]
- drag: C_D(Mach) through the vehicle's 23-knot power-on table (PCHIP, held beyond the end knots) x cd_scale 1, on A_ref = 21.24 m^2 [aref_fairing]
- target: circular orbit of radius 6563137 m (altitude 185000 m above R_E), energy cutoff [alt_185]
- target: circular orbit of radius 6628137 m (altitude 250000 m above R_E), energy cutoff [alt_250]
- target: circular orbit of radius 6678137 m (altitude 300000 m above R_E), energy cutoff [alt_300]
- site latitude 28.5 deg, azimuth 90 deg, rotation off: omega_p = 0 rad/s, g_ref = mu/R_E^2 - omega_p^2 R_E = 9.7982855 m/s^2 (the pad balance, the track's g_eff and the reference of the gravity-loss split) [no_rotation]

## Checks

- pad: closure residual -1.84933e-07 m/s, loss-identity residual 5.93445e-09 m/s, insertion e 1.45442e-08: ok
- readme_loads: closure residual -1.14325e-07 m/s, loss-identity residual 9.97716e-09 m/s, insertion e 1.00629e-08: ok
- recorded_scope: closure residual -1.72769e-07 m/s, loss-identity residual 2.07565e-08 m/s, insertion e 1.45965e-08: ok
- aref_fairing: closure residual -1.80329e-07 m/s, loss-identity residual 5.99448e-09 m/s, insertion e 1.31211e-08: ok
- alt_185: closure residual -2.84359e-07 m/s, loss-identity residual 4.9331e-09 m/s, insertion e 1.62501e-08: ok
- alt_250: closure residual -6.45978e-08 m/s, loss-identity residual 6.79756e-09 m/s, insertion e 1.36724e-08: ok
- alt_300: closure residual -7.78637e-08 m/s, loss-identity residual 7.02676e-09 m/s, insertion e 1.32631e-08: ok
- no_rotation: closure residual -3.47922e-07 m/s, loss-identity residual 4.37831e-09 m/s, insertion e 1.54703e-08: ok
- pad__vehicle.stages.stage1.dry_mass_t__+0.1: closure residual -1.75169e-07 m/s, loss-identity residual 5.95082e-09 m/s, insertion e 1.45879e-08: ok
- pad__vehicle.stages.stage1.dry_mass_t__-0.1: closure residual -1.83636e-07 m/s, loss-identity residual 5.62977e-09 m/s, insertion e 1.45491e-08: ok
- pad__vehicle.stages.stage1.engine.isp_vac_s__+0.1: closure residual -2.39015e-07 m/s, loss-identity residual 4.15457e-09 m/s, insertion e 1.41454e-08: ok
- pad__vehicle.stages.stage1.engine.isp_vac_s__-0.1: closure residual 7.22903e-08 m/s, loss-identity residual 1.28284e-08 m/s, insertion e 1.84099e-08: ok
- pad__vehicle.stages.stage2.engine.isp_vac_s__+0.1: closure residual -2.04711e-07 m/s, loss-identity residual 9.7516e-09 m/s, insertion e 1.76202e-08: ok
- pad__vehicle.stages.stage2.engine.isp_vac_s__-0.1: closure residual -1.00927e-07 m/s, loss-identity residual 7.01948e-09 m/s, insertion e 1.16191e-08: ok
- pad__vehicle.aero.cd_scale__+0.1: closure residual -1.82079e-07 m/s, loss-identity residual 5.82168e-09 m/s, insertion e 1.45677e-08: ok
- pad__vehicle.aero.cd_scale__-0.1: closure residual -1.49848e-07 m/s, loss-identity residual 4.68299e-09 m/s, insertion e 1.4453e-08: ok

(no variants)

Sensitivity cases and bounds against the baseline of the same vehicle (the screening-beat rule applies to them too):
- pad vehicle.stages.stage1.dry_mass_t +10% vs same-perturbation baseline: dP* +0 kg against the yardstick 0 kg (beats: False); failed checks: none; gamma*-sensitive: none; screening status not_checked
- pad vehicle.stages.stage1.dry_mass_t -10% vs same-perturbation baseline: dP* +0 kg against the yardstick 0 kg (beats: False); failed checks: none; gamma*-sensitive: none; screening status not_checked
- pad vehicle.stages.stage1.engine.isp_vac_s +10% vs same-perturbation baseline: dP* +0 kg against the yardstick 0 kg (beats: False); failed checks: none; gamma*-sensitive: none; screening status not_checked
- pad vehicle.stages.stage1.engine.isp_vac_s -10% vs same-perturbation baseline: dP* +0 kg against the yardstick 0 kg (beats: False); failed checks: none; gamma*-sensitive: none; screening status not_checked
- pad vehicle.stages.stage2.engine.isp_vac_s +10% vs same-perturbation baseline: dP* +0 kg against the yardstick 0 kg (beats: False); failed checks: none; gamma*-sensitive: none; screening status not_checked
- pad vehicle.stages.stage2.engine.isp_vac_s -10% vs same-perturbation baseline: dP* +0 kg against the yardstick 0 kg (beats: False); failed checks: none; gamma*-sensitive: none; screening status not_checked
- pad vehicle.aero.cd_scale +10% vs same-perturbation baseline: dP* +0 kg against the yardstick 0 kg (beats: False); failed checks: none; gamma*-sensitive: none; screening status not_checked
- pad vehicle.aero.cd_scale -10% vs same-perturbation baseline: dP* +0 kg against the yardstick 0 kg (beats: False); failed checks: none; gamma*-sensitive: none; screening status not_checked

No run and no comparison is bug_suspect.
Screening not checked (no matched-payload attribution, so no loss breakdown explains the dP*; no finding about a beat rests on it): pad vehicle.stages.stage1.dry_mass_t +10% vs same-perturbation baseline, pad vehicle.stages.stage1.dry_mass_t -10% vs same-perturbation baseline, pad vehicle.stages.stage1.engine.isp_vac_s +10% vs same-perturbation baseline, pad vehicle.stages.stage1.engine.isp_vac_s -10% vs same-perturbation baseline, pad vehicle.stages.stage2.engine.isp_vac_s +10% vs same-perturbation baseline, pad vehicle.stages.stage2.engine.isp_vac_s -10% vs same-perturbation baseline, pad vehicle.aero.cd_scale +10% vs same-perturbation baseline, pad vehicle.aero.cd_scale -10% vs same-perturbation baseline
Unexplained beats (not_checked and beating the screening yardstick: no loss breakdown explains them, so they support no finding): pad vehicle.stages.stage1.dry_mass_t -10% vs baseline, pad vehicle.stages.stage1.engine.isp_vac_s +10% vs baseline, pad vehicle.stages.stage2.engine.isp_vac_s +10% vs baseline, pad vehicle.aero.cd_scale -10% vs baseline
