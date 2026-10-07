> **EXPLORATORY app run, not a finding.** Launched from the local app's form, not from a committed experiment file, and not pre-registered. Code: the commit imported at server start (fb34b2417c56, clean); working tree at launch: clean. Do not cite; findings are in docs/findings/. Calibration +14.3%, no structural mass for the push, sweep-optimized, unthrottled. No sensitivity check ran: the Sensitivity section's vehicle.aero.cd_scale cases are those of the committed experiments, not of this directory. A run or case under a committed name (every name but silo, pad_variant, a neutral case name `silo_<tag>` such as silo_s1 or silo_fix7pct, and that case's paired pad `silo_<tag>__pad`) has that name's configuration in the experiment files at commit fb34b2417c56: a reproduction, not new evidence (the code may differ from the recorded run's). The M5 anchor check (dP* against silo_instant minus pad_instant plus the pad's pre-flight term) needs both anchor runs in one experiment; an app launch flies one variant, so M5 reads n/a.

# app (20261007T130817Z, git fb34b2417c56)

Comparison basis: sweep-optimized (every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, delta and the LTG pair are solved per run); planar_2d: rotating spherical Earth, ICAO atmosphere, drag, back-pressure, unthrottled; figure of merit: payload capacity P* at the target orbit

Guidance is sweep-optimized: every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, the kick angle delta and the LTG pair (a, b) are solved per run. Not an optimal-control solution (Phase 5).

- Vehicle: generic_f9_class_2d
- Baseline: pad
- Search budget id: a17a01601d0f4ae0c48cac48342127d5597e056e769da83503d7364c7d65a7df
- Timestamp (UTC): 20261007T130817Z
- Git: fb34b2417c56

## Variants against the baseline

| quantity | pad (baseline) | silo_cold |
|---|---|---|
| status | inserted | inserted |
| search status | ok | ok |
| run checks (closure, loss identity, insertion e) | ok | ok |
| screening status (closure, attribution, M3 to M5; M2 only when blocking; a failed diagnostic check in brackets) | (baseline) | ok |
| flags (see Flags) | - | - |
| stage-1 ignition, t_ign relative to release [s] (negative = lit before release) | -2 | 0.5 |
| stage-1 startup kind (step = instant full thrust: a yardstick, not achievable) | ramp | ramp |
|   its t_ramp or tau [s] | 2 | 2 |
| payload capacity P* [kg] (sweep-optimized) | 26054.4 | 27553.2 |
|   dP* vs baseline [kg] | (baseline) | 1498.83 |
|   ideal screening at this run's release speed, at the baseline's P* [kg] | (baseline) | 765.442 |
|   ideal screening at this run's release speed, at the vehicle payload P0 [kg] | (baseline) | 675.346 |
|   screening yardstick used, the stricter of the two [kg] | (baseline) | 675.346 |
|     its basis | (baseline) | P0 |
|   dP* beyond the screening yardstick [kg] | (baseline) | 823.485 |
|   beats the screening yardstick | (baseline) | True |
|   dP* is an unthrottled/unconstrained upper bound (max-Q, q-alpha or kick) | (baseline) | True |
|   payload excess P0 - P* [kg] | -3254.4 | -4753.23 |
| residual propellant at P0 [kg] (signed; negative = virtual, massless shortfall) | 3235.4 | 4696.05 |
|   its basis | at gamma*_ref (P*-optimal guidance) | at gamma*_ref (P*-optimal guidance) |
| dv margin at P0 [m/s] (signed) | 388.964 | 551.018 |
| gamma*_ref, the flight-path angle at MECO [deg] | 22.9891 | 21.6465 |
| kick angle delta [deg] | 2.83435 | 2.36146 |
| LTG a (tan of the initial pitch) | 0.610193 | 0.592158 |
| LTG b [1/s] | 0.00156085 | 0.00149175 |
| kick regime | after_vertical_rise | at_first_lit_instant |
|   |v_rel| at the kick [m/s] | 50 | 71.8083 |
|   unconstrained kick (faster than checks.unconstrained_kick_mps) | (baseline) | False |
|   kick steering loss [m/s] | 0.0258347 | 0.020867 |
| speed at release [m/s] | 0 | 76.7072 |
| propellant burned before the flight [kg] | 2697.46 | 0 |
|   its dv_vac equivalent [m/s] | 14.4078 | 0 |
| MECO: t after release [s] | 151.328 | 153.828 |
|   altitude [m] | 69485.8 | 75202.2 |
|   |v_rel| [m/s] | 2665.03 | 2765.92 |
|   gamma_rel [deg] | 22.9891 | 21.6465 |
|   downrange [m] | 99171 | 110155 |
| fairing drop | in the stage-2 burn (heating event) | in the stage-2 burn (heating event) |
|   t after release [s] | 196.808 | 193.816 |
|   altitude [m] | 110483 | 110993 |
| stage-2 end: t after release [s] | 536.301 | 538.801 |
|   eccentricity | 1.45116e-08 | 1.35972e-08 |
|   perigee altitude [m] | 200000 | 200000 |
|   apogee altitude [m] | 200000 | 200000 |
| gravity loss [m/s] | 1491.98 | 1450.41 |
| drag loss [m/s] | 26.0363 | 22.3972 |
| steering loss [m/s] | 88.988 | 90.1832 |
| back-pressure loss [m/s] | 63.1439 | 49.5718 |
| dv_vac from the flight start [m/s] | 9032.85 | 8898.56 |
|   loss-identity residual [m/s] | 0 | 0 |
| rocket-equation closure residual [m/s] | 0 | 0 |
|   pre-flight term c1 ln(m0/m_fs) [m/s] | 14.4078 | 0 |
|   fairing-carry term [m/s] | 3.23341 | 2.62644 |
| max-Q [Pa] (unthrottled: an upper bound) | 37191.4 | 31237.6 |
|   at t after release [s] | 65.7515 | 57.6096 |
|   altitude [m] | 11019.1 | 11019.1 |
|   Mach | 1.53218 | 1.4042 |
|   above the baseline | (baseline) | False |
| peak q-alpha [Pa rad] (alpha = psi; unconstrained) | 74.7309 | 129.916 |
|   at t after release [s] | 12.4937 | 0.5 |
|   above the baseline | (baseline) | True |
| peak felt axial g, run-wide [g0] (phase) | 5.19547 (GRAVITY_TURN) | 5.14794 (GRAVITY_TURN) |
| peak felt axial g in flight [g0] | 5.19547 | 5.14794 |
| peak felt lateral g in flight [g0] | 6.39136e-05 | 0.000101065 |
| peak felt g on the track [g0] | n/a | 3.99648 |
| interface force, peak [N] | 0 | 2.24905e+07 |
| interface force, minimum [N] | 0 | 2.24905e+07 |
| hold-down force m g_ref - T, minimum over the hold [N] | -2.04006e+06 | n/a |
| peak track-normal g [g0] | 0 | 0 |
|   vehicle [g0] | 0 | 0 |
|   carriage [g0] | 0 | 0 |
| assist (drive) energy [J] | 0 | 2.24905e+09 |
| assist (drive) energy [kWh] | 0 | 624.736 |
| electrical energy [kWh] (positive drive work / efficiency) | 0 | 1249.47 |
| peak drive power [W] | 0 | 1.72518e+09 |
| braking distance [m] | 0 | 60 |
| facility length incl. braking [m] | 0 | 160 |
| search: P2 - P1 [kg] | 18.435 | 60.2761 |
|   search minus final payload [kg] | -0.03725 | -0.0367046 |
| RHS evaluations of the recorded run | 6210 | 7478 |

## Propellant saved at fixed payload

Offload basis: propellant saved at fixed payload. Different vehicles (each run's own propellant load, tanks partly filled, dry masses unchanged unless a row says so), the same payload and the same orbit: every offload is measured at the reference payload P_ref, the full-load pad baseline's payload capacity P* on the same vehicle and orbit (sweep-optimized guidance, the shared search budget). Reference payload P_ref = 26054.4 kg (pad's payload capacity P*).

Caveats (they travel with every number below):

- calibration: the vehicle generic_f9_class_2d carries 26,054 kg in its calibration run against the published 22,800 kg, +14.3% high, a documented calibration result (docs/findings/CAL-f9-leo-2d); read every offload as a difference between runs of the vehicle model, not as a Falcon 9 figure
- guidance is sweep-optimized (a shared gamma* grid refined per run, not optimal control) and the engines never throttle
- no structural mass is charged for the push load (the fully fuelled stack rides the push at the net acceleration plus g); the penalty rows add an assumed stage-1 dry mass, a parametric assumption, not a sized structure
- the drive is a prescribed constant acceleration with no force or power limit, the carriage is massless unless the variant states a carriage mass, and the shaft is vented (no air drag in it)
- max-Q of each offloaded run is reported beside the pad's: a lighter stack climbs faster, and no max-Q limit constrains it (there is no throttle model)
- the tanks are partly filled: dry masses and tank structure unchanged, the mixture ratio kept, no ullage, centre-of-gravity or tank-mass effect
- stage 1 is the headline: stage-2 and both-stage offloads are a property of the vehicle model (stage-2 propellant is worth about nothing at the margin on the gate vehicle), quoted net of the pad control (the gross rows beside them are not a saving of the assist); a stage-1-only offload is not assumed to maximise the total tonnes ('both' may remove more, its stage-2 share riding about free), and stage 1 stays the only headline either way

| quantity | silo_cold_s1_dry+8.1t |
|---|---|
| assisted run (of) | silo_cold |
| kind | solved, stage1 |
| status (the solve, or a fixed case's payload search) | ok |
| recorded run (replay it beside the pad) | silo_cold_s1_dry+8.1t |
|   its status | inserted |
| quoted offload [t] | 1.98048 |
|   basis | x* at P_ref, gross: stage 1, the headline |
| stage-1 propellant removed, gross [t] | 1.98048 |
| stage-2 propellant removed, gross [t] (a stage-2 pre-offload included) | 0 |
| total propellant removed, gross [t] | 1.98048 |
|   % of the stage-1 load | 0.481985 |
|   % of the stage-2 load | 0 |
|   % of the total load | 0.382036 |
| assumed stage-1 dry mass added [t] (an assumption, not a sized structure) | 8.1 |
| payload flown [kg] (solved: P_ref; fixed: its own P*) | 26054.4 |
|   minus P_ref [kg] | +0 |
| verification: P* of the offloaded vehicle [kg] | 26054.4 |
|   P* - P_ref [kg] | +0.000649211 |
|   tolerance [kg] (checks.search_final_flag_rel x P_ref) | 2.60544 |
|   passed | True |
| pad control's offload in this mode [t] | 0 |
|   offload net of the pad control [t] | 1.98048 |
| liftoff mass [kg] | 578474 |
|   pad's [kg] | 572354 |
| MECO: t after release [s] | 153.094 |
|   pad's [s] | 151.328 |
| max-Q [Pa] (unthrottled: an upper bound) | 30424.5 |
|   pad's [Pa] | 37191.4 |
|   above the pad's | False |
| peak felt axial g in flight [g0] | 4.94751 |
|   pad's [g0] | 5.19547 |
| speed at release [m/s] | 76.7072 |
| peak felt g on the track [g0] | 3.99648 |
| interface force, peak [N] | 2.26716e+07 |
| facility length incl. braking [m] | 160 |
| ideal-screening offload at this release speed [t] | 14.9766 |
|   stage-1 offload / screening offload | 0.132238 |
|   beats the screening estimate | False |
| decomposition status | explained |
|   residual [m/s] | -6.59e-12 |
| paired pad (the same propellant change, no penalty) | n/a |
|   its P* [kg] | n/a |
|   its P* - P_ref [kg] | n/a |
|   assisted P* - paired pad P* [kg] (one vehicle, attributed) | n/a |
|   screening status (against the paired pad) | n/a |
| flags (see Flags) | 0 |
| RP-1 removed [kg] | 595.252 |
| LOX removed [kg] | 1385.23 |
| combustion heat of the removed RP-1, lower heating value [MJ] | 25613.7 |
|   [kWh] | 7114.91 |
| electrical energy of the push [MJ] | 4534.31 |
|   [kWh] | 1259.53 |
| heat / electricity (not an efficiency claim) | 5.64885 |


Energy comparison: the fuel (RP-1) removed is each stage's removed propellant times its fuel fraction (the energy block's fuel mass over the experiment vehicle's full load: the mixture ratio kept, on any load; the lower heating value from the energy block), the oxidiser (LOX) the rest; the combustion heat is the removed fuel's mass times its lower heating value, and the electrical energy is the offloaded run's push (positive drive work over the drive efficiency). The heat / electricity ratio is not an efficiency claim; it leaves out the energy to produce the removed oxidiser (LOX: air separation and liquefaction); the energy to extract, refine and deliver the removed fuel; electricity generation, transmission and storage losses (the push's electrical energy is its positive drive work over the drive efficiency, metered at the drive); the energy of the push's facility beyond the drive (braking, the carriage's return).

### Decomposition

Cross-vehicle decomposition of each case against the pad, both at P_ref (docs/physics.md, 'Cross-vehicle decomposition'): the ideal delta-v the case's vehicle does without, D_id(pad) - D_id(case), split into the release-speed head start and the differences in the losses, the pre-flight burn, the fairing term and the margin; each cell is m/s (kg of the offload, a proportional split). Only the joint gravity + steering term is read as physics. The residual must stay below checks.closure_tol_mps: explained when it does, bug_suspect (findings blocked) when it does not.

| term: m/s (kg) | silo_cold_s1_dry+8.1t |
|---|---|
| release speed | +76.7072 (+1300) |
| final speed | +2.77101e-05 (+0.00046962) |
| gravity | +14.0736 (+238.514) |
| drag | +4.23472 (+71.7684) |
| steering | -6.69561 (-113.475) |
| back pressure | +13.6143 (+230.729) |
| preflight | +14.4078 (+244.177) |
| fairing | +0.516724 (+8.75724) |
| margin | +4.98196e-05 (+0.000844324) |
| gravity + steering | +7.37797 (+125.039) |
| D_id(pad) - D_id(case) [m/s] | 116.859 |
| offload split [kg] | 1980.48 |
| residual [m/s] | -6.59e-12 |
| status | explained |

### Pad controls

| quantity | stage1 |
|---|---|
| recorded run | pad__offload_stage1 |
| status | no_offload |
| x_pad [kg] | 0 |
| m_res at x_pad [kg] (signed) | -0.00163769 |
| dv margin at x_pad [m/s] (signed) | -0.000185962 |
| abs(dm_res/dx) from the solve's own logs [kg/kg] | 0.0309062 |
| stage 1: bound final_payload_xtol_kg / abs(dm_res/dx) [kg] | 1.6178 |
|   0 <= x_pad <= bound (an ok control) | n/a |
| ended no_offload by grams (a resolution effect) | True |
| stage 1: consistency test of the solver (section 5.3) | pass |
| verification: P* - P_ref [kg] | n/a |
|   passed | n/a |

- pad control stage1: x_pad = 0, m_res(0) = -0.00163769 kg: a resolution effect: the full-load pad misses P_ref by grams of residual propellant at the feasible-side convention's resolution, within final_payload_xtol_kg; not a failure; consistency test pass

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
- stage 2's (a, b) are solved by shooting for the target radius and zero radial velocity [all runs]
- searches burn virtual stage-2 propellant past the real load, down to a mass floor (the final verification's evaluations too, at the final tolerance); only the recorded run carries the real depletion, and one that runs dry before the cutoff reports its evaluation's signed (negative) m_res and dv_margin. A negative m_res is a virtual (massless) shortfall, propellant that weighs nothing until burned, not the load of a larger tank (which would make the shortfall worse) [all runs]
- the residual propellant at the vehicle payload of a payload search is taken at the P*-optimal gamma*_ref, not re-optimised at P0 (a few kg low, against the assist) [all runs]
- "sweep-optimized" guidance: gamma* is the best point of the shared grid refined by a bounded Brent search at the first payload estimate, delta and (a, b) are solved for it, and P* is the largest verified payload with m_res >= 0 (not an optimal-control solution; Phase 5) [all runs]
- site latitude 28.5 deg, azimuth 90 deg, rotation on: omega_p = 6.408435e-05 rad/s, g_ref = mu/R_E^2 - omega_p^2 R_E = 9.7720917 m/s^2 (the pad balance, the track's g_eff and the reference of the gravity-loss split) [all runs]
- target: circular orbit of radius 6578137 m (altitude 200000 m above R_E), energy cutoff [all runs]
- drag: C_D(Mach) through the vehicle's 23-knot power-on table (PCHIP, held beyond the end knots) x cd_scale 1, on A_ref = 10.52 m^2 [all runs]
- stage 2 (stage2) starts at full thrust (step startup); its exit area 8.6 m^2 (the vehicle file's value; the Phase 2 forks mark it assumed, not published) sets the back-pressure p A_e [all runs]
- fairing (1700 kg): dropped when 0.5 rho |v_rel|^3 < 1135 W/m^2 [all runs]
- pad: held down to the release at t = 0 s; stage 1 lit at t = -2 s with a ramp startup, then clamped until its thrust exceeds its weight [pad, pad__offload_stage1]
- atmosphere: ICAO standard atmosphere closed forms (layer table of ambiance.CONST) from -5,004 m to 81,020 m geometric altitude; the geometric to geopotential conversion uses the ICAO radius 6,356,766 m, not R_E. [all runs]
- atmosphere: above 81,020 m an isothermal extension at 196.649 K with scale height 5,908 m (R_air T_top / g(h_top)); not US76 (denser near 110 km, far thinner above 150 km). [all runs]
- atmosphere: static, spherically symmetric, no wind; it co-rotates with Earth, so drag and Mach use the Earth-relative velocity v_rel. [all runs]
- atmosphere: in flight, an altitude below the -5,004 m floor is held at the floor state (ambient_scalar clamp; a dive ends at the ground event). [all runs]
- track phase: 1-DOF along the track in a flat local frame with constant g_eff; the carriage stays on the track at release; carriage braking is not modelled as a phase (its distance v^2/(2 a_brake) is added to the facility length) [silo_cold, silo_cold_s1_dry+8.1t]
- hot start: the propellant burned before release is reported with its delta-v equivalent; the exhaust impingement fraction f_imp on the carriage is an assumed amendment to the track equation (the system keeps (1 - f_imp) T) [silo_cold, silo_cold_s1_dry+8.1t]
- drive energy: electrical_energy = (positive drive work) / efficiency; no regeneration is credited for any negative (braking) drive work [silo_cold, silo_cold_s1_dry+8.1t]
- track: straight, L = 100 m at 1.5708 rad above horizontal, start altitude -100 m (exit at 0 m) [silo_cold, silo_cold_s1_dry+8.1t]
- constant_accel: prescribed net acceleration 3 g0 (assumed); drive force unconstrained, solved from the track equation [silo_cold, silo_cold_s1_dry+8.1t]
- constant_accel: carriage mass 0 t (assumed) [silo_cold, silo_cold_s1_dry+8.1t]
- constant_accel: braking deceleration 5 g0 (assumed) [silo_cold, silo_cold_s1_dry+8.1t]
- constant_accel: drive efficiency 0.5 (assumed) [silo_cold, silo_cold_s1_dry+8.1t]
- constant_accel: exhaust impingement fraction 0 (assumed); the system keeps (1 - f_imp) T of the on-track thrust [silo_cold, silo_cold_s1_dry+8.1t]
- constant_accel: shaft vented (no air column), no friction [silo_cold, silo_cold_s1_dry+8.1t]
- constant_accel: constant g_eff = 9.772092 m/s^2 on the track (mu/R_E^2 - omega_p^2 R_E with omega_p = 6.408435e-05 rad/s, the planar rotation rate of the site), flat 1-DOF track frame, Coriolis neglected [silo_cold, silo_cold_s1_dry+8.1t]
- constant_accel: infinite jerk at push start and release [silo_cold, silo_cold_s1_dry+8.1t]
- constant_accel: vehicle clamped to the carriage during any hold before the push [silo_cold, silo_cold_s1_dry+8.1t]
- offload: the propellant removed from a full load leaves the tanks partly filled; every dry mass (tank structure included), engine, the payload, the fairing and the aerodynamics are unchanged and each stage keeps its mixture ratio; no ullage, centre-of-gravity or tank-mass effect is modelled [pad__offload_stage1, silo_cold_s1_dry+8.1t]
- offload: stage-1 dry mass +8.1 t is an assumed structural penalty (a parametric row), not a structure sized for the push load [silo_cold_s1_dry+8.1t]

## Checks

- pad: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.45116e-08: ok
- silo_cold: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35972e-08: ok
- pad__offload_stage1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.03271e-07: ok
- silo_cold_s1_dry+8.1t: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- silo_cold_s1_dry+8.1t (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.33651e-08: ok

- silo_cold: dP* +1498.83 kg (an unthrottled/unconstrained upper bound: q-alpha above the baseline) against the ideal screening yardstick 675.346 kg at its release speed 76.7072 m/s (the stricter of 675.346 kg at P0 and 765.442 kg at the baseline's P*: P0): beats it by 823.485 kg (the attribution must explain this). matched-payload attribution at P_ref = 26054.4 kg: d dv_margin +165.248 m/s = release speed +76.7072, final speed +1.19114e-05, gravity +47.16, drag +3.50712, steering +9.27295, back pressure +13.5742, preflight +14.4078, fairing +0.618272 m/s (residual 0 m/s); gravity + steering together +56.4329 m/s; dP* split in kg: release speed +695.751, final speed +0.000108039, gravity +427.751, drag +31.8104, steering +84.1076, back pressure +123.121, preflight +130.682, fairing +5.60786 (gravity + steering together +511.859 kg). The gravity and steering terms trade against each other as gamma* moves (the total is nearly stationary in gamma*), so only their sum is read as physics, never the split between them (docs/physics.md, 'Screening-beat rule (2-D)'). Over gamma* +/- 0.5 deg the gravity term moves -15.1386 m/s per deg, the steering term +13.06 m/s per deg, their sum -2.0786 m/s per deg. Checks: closure pass (worst residual 1.27e-11 m/s); attribution pass (worst closure 8.7e-12 m/s, worst identity 1.27e-11 m/s); M2 (diagnostic) pass (d -47.16 m/s against the time-shift estimate -105.055 m/s: ratio 0.448907; over gamma* +/- h: 0.376919..0.521021, robust; stage 1 alone d -14.4231 m/s: ratio 0.137291, a diagnostic); M3 pass (d -13.5742 m/s against the time-shift estimate -20.1817 m/s: ratio 0.672602; over gamma* +/- h: 0.670781..0.674368, robust); M4 pass (drag + steering +12.7801 m/s of +88.5403 m/s beyond the release speed: share 0.144342; over gamma* +/- h: 0.0626049..0.216255, robust); M5 n/a. Screening status: ok

Offload checks (a stage-1 pad control is a consistency test of the solver, and a failing one blocks findings; the screening rule for offload rows: an offload beyond the ideal screening estimate is explained only by a decomposition that closes, else bug_suspect; offload rows never enter the unexplained-beats list):
- pad control stage1: x_pad = 0, m_res(0) = -0.00163769 kg: a resolution effect: the full-load pad misses P_ref by grams of residual propellant at the feasible-side convention's resolution, within final_payload_xtol_kg; not a failure; consistency test pass
- silo_cold_s1_dry+8.1t: decomposition explained (residual -6.59e-12 m/s; stage-1 offload / screening 0.132238)

No run and no comparison is bug_suspect.
