> **EXPLORATORY app run, not a finding.** Launched from the local app's form, not from a committed experiment file, and not pre-registered. Code: the commit imported at server start (fb34b2417c56, clean); working tree at launch: clean. Do not cite; findings are in docs/findings/. Calibration +14.3%, no structural mass for the push, sweep-optimized, unthrottled. No sensitivity check ran: the Sensitivity section's vehicle.aero.cd_scale cases are those of the committed experiments, not of this directory. A run or case under a committed name (every name but silo, pad_variant, a neutral case name `silo_<tag>` such as silo_s1 or silo_fix7pct, and that case's paired pad `silo_<tag>__pad`) has that name's configuration in the experiment files at commit fb34b2417c56: a reproduction, not new evidence (the code may differ from the recorded run's). The M5 anchor check (dP* against silo_instant minus pad_instant plus the pad's pre-flight term) needs both anchor runs in one experiment; an app launch flies one variant, so M5 reads n/a.

# app (20261007T131031Z, git fb34b2417c56)

Comparison basis: sweep-optimized (every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, delta and the LTG pair are solved per run); planar_2d: rotating spherical Earth, ICAO atmosphere, drag, back-pressure, unthrottled; figure of merit: payload capacity P* at the target orbit

Guidance is sweep-optimized: every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, the kick angle delta and the LTG pair (a, b) are solved per run. Not an optimal-control solution (Phase 5).

- Vehicle: generic_f9_class_2d
- Baseline: pad
- Search budget id: a17a01601d0f4ae0c48cac48342127d5597e056e769da83503d7364c7d65a7df
- Timestamp (UTC): 20261007T131031Z
- Git: fb34b2417c56

## Variants against the baseline

| quantity | pad (baseline) | silo_failed |
|---|---|---|
| status | inserted | impact |
| search status | ok | skipped (end: impact (ignition stage1 fails)) |
| run checks (closure, loss identity, insertion e) | ok | ok |
| screening status (closure, attribution, M3 to M5; M2 only when blocking; a failed diagnostic check in brackets) | (baseline) | not_checked |
| flags (see Flags) | - | - |
| stage-1 ignition, t_ign relative to release [s] (negative = lit before release) | -2 | n/a |
| stage-1 startup kind (step = instant full thrust: a yardstick, not achievable) | ramp | ramp |
|   its t_ramp or tau [s] | 2 | 2 |
| payload capacity P* [kg] (sweep-optimized) | 26054.4 | n/a |
|   dP* vs baseline [kg] | (baseline) | n/a |
|   ideal screening at this run's release speed, at the baseline's P* [kg] | (baseline) | 765.442 |
|   ideal screening at this run's release speed, at the vehicle payload P0 [kg] | (baseline) | 675.346 |
|   screening yardstick used, the stricter of the two [kg] | (baseline) | 675.346 |
|     its basis | (baseline) | P0 |
|   dP* beyond the screening yardstick [kg] | (baseline) | n/a |
|   beats the screening yardstick | (baseline) | n/a |
|   dP* is an unthrottled/unconstrained upper bound (max-Q, q-alpha or kick) | (baseline) | False |
|   payload excess P0 - P* [kg] | -3254.4 | n/a |
| residual propellant at P0 [kg] (signed; negative = virtual, massless shortfall) | 3235.4 | n/a |
|   its basis | at gamma*_ref (P*-optimal guidance) | n/a |
| dv margin at P0 [m/s] (signed) | 388.964 | n/a |
| gamma*_ref, the flight-path angle at MECO [deg] | 22.9891 | n/a |
| kick angle delta [deg] | 2.83435 | n/a |
| LTG a (tan of the initial pitch) | 0.610193 | n/a |
| LTG b [1/s] | 0.00156085 | n/a |
| kick regime | after_vertical_rise | none |
|   |v_rel| at the kick [m/s] | 50 | n/a |
|   unconstrained kick (faster than checks.unconstrained_kick_mps) | (baseline) | n/a |
|   kick steering loss [m/s] | 0.0258347 | n/a |
| speed at release [m/s] | 0 | 76.7072 |
| propellant burned before the flight [kg] | 2697.46 | 0 |
|   its dv_vac equivalent [m/s] | 14.4078 | 0 |
| MECO: t after release [s] | 151.328 | n/a |
|   altitude [m] | 69485.8 | n/a |
|   |v_rel| [m/s] | 2665.03 | n/a |
|   gamma_rel [deg] | 22.9891 | n/a |
|   downrange [m] | 99171 | n/a |
| fairing drop | in the stage-2 burn (heating event) | n/a |
|   t after release [s] | 196.808 | n/a |
|   altitude [m] | 110483 | n/a |
| stage-2 end: t after release [s] | 536.301 | n/a |
|   eccentricity | 1.45116e-08 | n/a |
|   perigee altitude [m] | 200000 | n/a |
|   apogee altitude [m] | 200000 | n/a |
| gravity loss [m/s] | 1491.98 | -0.0367726 |
| drag loss [m/s] | 26.0363 | 0.145751 |
| steering loss [m/s] | 88.988 | 0 |
| back-pressure loss [m/s] | 63.1439 | 0 |
| dv_vac from the flight start [m/s] | 9032.85 | 0 |
|   loss-identity residual [m/s] | 0 | 4.34742e-09 |
| rocket-equation closure residual [m/s] | 0 | n/a |
|   pre-flight term c1 ln(m0/m_fs) [m/s] | 14.4078 | n/a |
|   fairing-carry term [m/s] | 3.23341 | n/a |
| max-Q [Pa] (unthrottled: an upper bound) | 37191.4 | 3603.94 |
|   at t after release [s] | 65.7515 | 0 |
|   altitude [m] | 11019.1 | 0 |
|   Mach | 1.53218 | 0.225414 |
|   above the baseline | (baseline) | False |
| peak q-alpha [Pa rad] (alpha = psi; unconstrained) | 74.7309 | 0 |
|   at t after release [s] | 12.4937 | 0 |
|   above the baseline | (baseline) | False |
| peak felt axial g, run-wide [g0] (phase) | 5.19547 (GRAVITY_TURN) | 3.99648 (ASSIST) |
| peak felt axial g in flight [g0] | 5.19547 | 0 |
| peak felt lateral g in flight [g0] | 6.39136e-05 | 0 |
| peak felt g on the track [g0] | n/a | 3.99648 |
| interface force, peak [N] | 0 | 2.23042e+07 |
| interface force, minimum [N] | 0 | 2.23042e+07 |
| hold-down force m g_ref - T, minimum over the hold [N] | -2.04006e+06 | n/a |
| peak track-normal g [g0] | 0 | 0 |
|   vehicle [g0] | 0 | 0 |
|   carriage [g0] | 0 | 0 |
| assist (drive) energy [J] | 0 | 2.23042e+09 |
| assist (drive) energy [kWh] | 0 | 619.561 |
| electrical energy [kWh] (positive drive work / efficiency) | 0 | 1239.12 |
| peak drive power [W] | 0 | 1.71089e+09 |
| braking distance [m] | 0 | 60 |
| facility length incl. braking [m] | 0 | 160 |
| search: P2 - P1 [kg] | 18.435 | n/a |
|   search minus final payload [kg] | -0.03725 | n/a |
| RHS evaluations of the recorded run | 6210 | 1560 |
| failed ignition: stage | n/a | stage1 |
|   apex altitude of the fall-back coast [m] | n/a | 300.647 |
|   time of that apex after release [s] | n/a | 7.84265 |
|   impact time after release [s] | n/a | 15.6891 |
|   impact speed |v_rel| at the ground [m/s] | n/a | 76.5982 |

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
- stage 2's (a, b) are solved by shooting for the target radius and zero radial velocity [pad]
- searches burn virtual stage-2 propellant past the real load, down to a mass floor (the final verification's evaluations too, at the final tolerance); only the recorded run carries the real depletion, and one that runs dry before the cutoff reports its evaluation's signed (negative) m_res and dv_margin. A negative m_res is a virtual (massless) shortfall, propellant that weighs nothing until burned, not the load of a larger tank (which would make the shortfall worse) [pad]
- the residual propellant at the vehicle payload of a payload search is taken at the P*-optimal gamma*_ref, not re-optimised at P0 (a few kg low, against the assist) [pad]
- "sweep-optimized" guidance: gamma* is the best point of the shared grid refined by a bounded Brent search at the first payload estimate, delta and (a, b) are solved for it, and P* is the largest verified payload with m_res >= 0 (not an optimal-control solution; Phase 5) [pad]
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
- track phase: 1-DOF along the track in a flat local frame with constant g_eff; the carriage stays on the track at release; carriage braking is not modelled as a phase (its distance v^2/(2 a_brake) is added to the facility length) [all variants]
- hot start: the propellant burned before release is reported with its delta-v equivalent; the exhaust impingement fraction f_imp on the carriage is an assumed amendment to the track equation (the system keeps (1 - f_imp) T) [all variants]
- drive energy: electrical_energy = (positive drive work) / efficiency; no regeneration is credited for any negative (braking) drive work [all variants]
- track: straight, L = 100 m at 1.5708 rad above horizontal, start altitude -100 m (exit at 0 m) [all variants]
- failed ignition: no abort is modelled; the unpowered coast to the apex and the ground is flown with drag, rotation and mu/r^2, from the track exit (or the pad) [all variants]
- constant_accel: prescribed net acceleration 3 g0 (assumed); drive force unconstrained, solved from the track equation [all variants]
- constant_accel: carriage mass 0 t (assumed) [all variants]
- constant_accel: braking deceleration 5 g0 (assumed) [all variants]
- constant_accel: drive efficiency 0.5 (assumed) [all variants]
- constant_accel: exhaust impingement fraction 0 (assumed); the system keeps (1 - f_imp) T of the on-track thrust [all variants]
- constant_accel: shaft vented (no air column), no friction [all variants]
- constant_accel: constant g_eff = 9.772092 m/s^2 on the track (mu/R_E^2 - omega_p^2 R_E with omega_p = 6.408435e-05 rad/s, the planar rotation rate of the site), flat 1-DOF track frame, Coriolis neglected [all variants]
- constant_accel: infinite jerk at push start and release [all variants]
- constant_accel: vehicle clamped to the carriage during any hold before the push [all variants]

## Checks

- pad: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.45116e-08: ok
- silo_failed: closure residual n/a m/s, loss-identity residual 4.34742e-09 m/s, insertion e n/a: ok

- silo_failed: dP* n/a kg against the ideal screening yardstick 675.346 kg at its release speed 76.7072 m/s (the stricter of 675.346 kg at P0 and 765.442 kg at the baseline's P*: P0): n/a. matched-payload attribution n/a (no rung-2 run at the matched payload). Checks: closure n/a (the variant burned no stage 2); attribution n/a (no rung-2 run at the matched payload); M2 (diagnostic) n/a; M3 n/a; M4 n/a; M5 n/a. Screening status: not_checked

No run and no comparison is bug_suspect.
Screening not checked (no matched-payload attribution, so no loss breakdown explains the dP*; no finding about a beat rests on it): silo_failed
