# silo_offload_2d_readme (20261003T112956Z, git b3150c1754ee)

Comparison basis: sweep-optimized (every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, delta and the LTG pair are solved per run); planar_2d: rotating spherical Earth, ICAO atmosphere, drag, back-pressure, unthrottled; figure of merit: payload capacity P* at the target orbit

Guidance is sweep-optimized: every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, the kick angle delta and the LTG pair (a, b) are solved per run. Not an optimal-control solution (Phase 5).

- Vehicle: generic_f9_class_2d_readme_loads
- Baseline: pad
- Search budget id: a17a01601d0f4ae0c48cac48342127d5597e056e769da83503d7364c7d65a7df
- Timestamp (UTC): 20261003T112956Z
- Git: b3150c1754ee

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
| payload capacity P* [kg] (sweep-optimized) | 24700 | 26094.4 |
|   dP* vs baseline [kg] | (baseline) | 1394.42 |
|   ideal screening at this run's release speed, at the baseline's P* [kg] | (baseline) | 738.687 |
|   ideal screening at this run's release speed, at the vehicle payload P0 [kg] | (baseline) | 684.758 |
|   screening yardstick used, the stricter of the two [kg] | (baseline) | 684.758 |
|     its basis | (baseline) | P0 |
|   dP* beyond the screening yardstick [kg] | (baseline) | 709.661 |
|   beats the screening yardstick | (baseline) | True |
|   dP* is an unthrottled/unconstrained upper bound (max-Q, q-alpha or kick) | (baseline) | True |
|   payload excess P0 - P* [kg] | -1900.01 | -3294.43 |
| residual propellant at P0 [kg] (signed; negative = virtual, massless shortfall) | 1814.4 | 3126.91 |
|   its basis | at gamma*_ref (P*-optimal guidance) | at gamma*_ref (P*-optimal guidance) |
| dv margin at P0 [m/s] (signed) | 224.371 | 377.95 |
| gamma*_ref, the flight-path angle at MECO [deg] | 20.9443 | 19.757 |
| kick angle delta [deg] | 3.99627 | 3.60254 |
| LTG a (tan of the initial pitch) | 0.531786 | 0.517876 |
| LTG b [1/s] | 0.0017502 | 0.0016882 |
| kick regime | after_vertical_rise | at_first_lit_instant |
|   |v_rel| at the kick [m/s] | 50 | 71.8077 |
|   unconstrained kick (faster than checks.unconstrained_kick_mps) | (baseline) | False |
|   kick steering loss [m/s] | 0.0512826 | 0.0490858 |
| speed at release [m/s] | 0 | 76.7072 |
| propellant burned before the flight [kg] | 2697.46 | 0 |
|   its dv_vac equivalent [m/s] | 15.1475 | 0 |
| MECO: t after release [s] | 145.694 | 148.194 |
|   altitude [m] | 67509.8 | 72621.7 |
|   |v_rel| [m/s] | 2844.41 | 2944.25 |
|   gamma_rel [deg] | 20.9443 | 19.757 |
|   downrange [m] | 106868 | 117844 |
| fairing drop | in the stage-2 burn (heating event) | in the stage-2 burn (heating event) |
|   t after release [s] | 196.964 | 194.582 |
|   altitude [m] | 112094 | 112520 |
| stage-2 end: t after release [s] | 479.075 | 481.575 |
|   eccentricity | 9.45148e-09 | 9.10057e-09 |
|   perigee altitude [m] | 200000 | 200000 |
|   apogee altitude [m] | 200000 | 200000 |
| gravity loss [m/s] | 1372.94 | 1336.97 |
| drag loss [m/s] | 29.9268 | 25.9905 |
| steering loss [m/s] | 38.1969 | 39.3299 |
| back-pressure loss [m/s] | 62.5123 | 49.8929 |
| dv_vac from the flight start [m/s] | 8866.28 | 8738.18 |
|   loss-identity residual [m/s] | 0 | 0 |
| rocket-equation closure residual [m/s] | 0 | 0 |
|   pre-flight term c1 ln(m0/m_fs) [m/s] | 15.1475 | 0 |
|   fairing-carry term [m/s] | 5.55095 | 4.70396 |
| max-Q [Pa] (unthrottled: an upper bound) | 42732.6 | 36386.8 |
|   at t after release [s] | 62.1327 | 55.002 |
|   altitude [m] | 11019.1 | 11019.1 |
|   Mach | 1.64236 | 1.51552 |
|   above the baseline | (baseline) | False |
| peak q-alpha [Pa rad] (alpha = psi; unconstrained) | 105.155 | 198.081 |
|   at t after release [s] | 10.7181 | 0.5 |
|   above the baseline | (baseline) | True |
| peak felt axial g, run-wide [g0] (phase) | 5.63819 (GRAVITY_TURN) | 5.58621 (GRAVITY_TURN) |
| peak felt axial g in flight [g0] | 5.63819 | 5.58621 |
| peak felt lateral g in flight [g0] | 9.39485e-05 | 0.000161932 |
| peak felt g on the track [g0] | n/a | 3.99648 |
| interface force, peak [N] | 0 | 2.13935e+07 |
| interface force, minimum [N] | 0 | 2.13935e+07 |
| hold-down force m g_ref - T, minimum over the hold [N] | -2.31255e+06 | n/a |
| peak track-normal g [g0] | 0 | 0 |
|   vehicle [g0] | 0 | 0 |
|   carriage [g0] | 0 | 0 |
| assist (drive) energy [J] | 0 | 2.13935e+09 |
| assist (drive) energy [kWh] | 0 | 594.265 |
| electrical energy [kWh] (positive drive work / efficiency) | 0 | 1188.53 |
| peak drive power [W] | 0 | 1.64104e+09 |
| braking distance [m] | 0 | 60 |
| facility length incl. braking [m] | 0 | 160 |
| search: P2 - P1 [kg] | 19.293 | 1.18037 |
|   search minus final payload [kg] | -0.0274297 | -0.249505 |
| RHS evaluations of the recorded run | 6027 | 7016 |

## Propellant saved at fixed payload

Offload basis: propellant saved at fixed payload. Different vehicles (each run's own propellant load, tanks partly filled, dry masses unchanged unless a row says so), the same payload and the same orbit: every offload is measured at the reference payload P_ref, the full-load pad baseline's payload capacity P* on the same vehicle and orbit (sweep-optimized guidance, the shared search budget). Reference payload P_ref = 24700 kg (pad's payload capacity P*).

Caveats (they travel with every number below):

- calibration: the vehicle generic_f9_class_2d_readme_loads carries 24,700 kg in its calibration run against the published 22,800 kg, +8.3% high, a documented calibration result (docs/findings/CAL-f9-leo-2d); read every offload as a difference between runs of the vehicle model, not as a Falcon 9 figure
- guidance is sweep-optimized (a shared gamma* grid refined per run, not optimal control) and the engines never throttle
- no structural mass is charged for the push load (the fully fuelled stack rides the push at the net acceleration plus g); the penalty rows add an assumed stage-1 dry mass, a parametric assumption, not a sized structure
- the drive is a prescribed constant acceleration with no force or power limit, the carriage is massless unless the variant states a carriage mass, and the shaft is vented (no air drag in it)
- max-Q of each offloaded run is reported beside the pad's: a lighter stack climbs faster, and no max-Q limit constrains it (there is no throttle model)
- the tanks are partly filled: dry masses and tank structure unchanged, the mixture ratio kept, no ullage, centre-of-gravity or tank-mass effect
- stage 1 is the headline: stage-2 and both-stage offloads are a property of the vehicle model (stage-2 propellant is worth about nothing at the margin on the gate vehicle), quoted net of the pad control (the gross rows beside them are not a saving of the assist); a stage-1-only offload is not assumed to maximise the total tonnes ('both' may remove more, its stage-2 share riding about free), and stage 1 stays the only headline either way

| quantity | silo_cold_s1 |
|---|---|
| assisted run (of) | silo_cold |
| kind | solved, stage1 |
| status (the solve, or a fixed case's payload search) | ok |
| recorded run (replay it beside the pad) | silo_cold_s1 |
|   its status | inserted |
| quoted offload [t] | 36.0064 |
|   basis | x* at P_ref, gross: stage 1, the headline |
| stage-1 propellant removed, gross [t] | 36.0064 |
| stage-2 propellant removed, gross [t] (a stage-2 pre-offload included) | 0 |
| total propellant removed, gross [t] | 36.0064 |
|   % of the stage-1 load | 9.09943 |
|   % of the stage-2 load | 0 |
|   % of the total load | 7.37278 |
| assumed stage-1 dry mass added [t] (an assumption, not a sized structure) | 0 |
| payload flown [kg] (solved: P_ref; fixed: its own P*) | 24700 |
|   minus P_ref [kg] | +0 |
| verification: P* of the offloaded vehicle [kg] | 24700 |
|   P* - P_ref [kg] | +0.0039773 |
|   tolerance [kg] (checks.search_final_flag_rel x P_ref) | 2.47 |
|   passed | True |
| pad control's offload in this mode [t] | 0 |
|   offload net of the pad control [t] | 36.0064 |
| liftoff mass [kg] | 508464 |
|   pad's [kg] | 544470 |
| MECO: t after release [s] | 134.845 |
|   pad's [s] | 145.694 |
| max-Q [Pa] (unthrottled: an upper bound) | 43923.3 |
|   pad's [Pa] | 42732.6 |
|   above the pad's | True |
| peak felt axial g in flight [g0] | 5.63818 |
|   pad's [g0] | 5.63819 |
| speed at release [m/s] | 76.7072 |
| peak felt g on the track [g0] | 3.99648 |
| interface force, peak [N] | 1.99277e+07 |
| facility length incl. braking [m] | 160 |
| ideal-screening offload at this release speed [t] | 14.247 |
|   stage-1 offload / screening offload | 2.52731 |
|   beats the screening estimate | True |
| decomposition status | explained |
|   residual [m/s] | -2.05e-11 |
| paired pad (the same propellant change, no penalty) | silo_cold_s1__pad |
|   its P* [kg] | 23390.6 |
|   its P* - P_ref [kg] | -1309.46 |
|   assisted P* - paired pad P* [kg] (one vehicle, attributed) | +1309.46 |
|   screening status (against the paired pad) | ok |
| flags (see Flags) | 0 |


### Decomposition

Cross-vehicle decomposition of each case against the pad, both at P_ref (docs/physics.md, 'Cross-vehicle decomposition'): the ideal delta-v the case's vehicle does without, D_id(pad) - D_id(case), split into the release-speed head start and the differences in the losses, the pre-flight burn, the fairing term and the margin; each cell is m/s (kg of the offload, a proportional split). Only the joint gravity + steering term is read as physics. The residual must stay below checks.closure_tol_mps: explained when it does, bug_suspect (findings blocked) when it does not.

| term: m/s (kg) | silo_cold_s1 |
|---|---|
| release speed | +76.7072 (+13236) |
| final speed | +1.51575e-05 (+0.00261546) |
| gravity | +105.784 (+18253.3) |
| drag | -0.836207 (-144.289) |
| steering | -0.105572 (-18.2167) |
| back pressure | +12.0029 (+2071.12) |
| preflight | +15.1475 (+2613.73) |
| fairing | -0.0298778 (-5.15548) |
| margin | +5.66193e-05 (+0.00976978) |
| gravity + steering | +105.678 (+18235) |
| D_id(pad) - D_id(case) [m/s] | 208.67 |
| offload split [kg] | 36006.4 |
| residual [m/s] | -2.05e-11 |
| status | explained |

### Pad controls

| quantity | stage1 |
|---|---|
| recorded run | pad__offload_stage1 |
| status | no_offload |
| x_pad [kg] | 0 |
| m_res at x_pad [kg] (signed) | -0.00158773 |
| dv margin at x_pad [m/s] (signed) | -0.000189457 |
| abs(dm_res/dx) from the solve's own logs [kg/kg] | 0.0390649 |
| stage 1: bound final_payload_xtol_kg / abs(dm_res/dx) [kg] | 1.27992 |
|   0 <= x_pad <= bound (an ok control) | n/a |
| ended no_offload by grams (a resolution effect) | True |
| stage 1: consistency test of the solver (section 5.3) | pass |
| verification: P* - P_ref [kg] | n/a |
|   passed | n/a |

- pad control stage1: x_pad = 0, m_res(0) = -0.00158773 kg: a resolution effect: the full-load pad misses P_ref by grams of residual propellant at the feasible-side convention's resolution, within final_payload_xtol_kg; not a failure; consistency test pass

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
- fairing (1900 kg): dropped when 0.5 rho |v_rel|^3 < 1135 W/m^2 [all runs]
- pad: held down to the release at t = 0 s; stage 1 lit at t = -2 s with a ramp startup, then clamped until its thrust exceeds its weight [pad, pad__offload_stage1, silo_cold_s1__pad]
- atmosphere: ICAO standard atmosphere closed forms (layer table of ambiance.CONST) from -5,004 m to 81,020 m geometric altitude; the geometric to geopotential conversion uses the ICAO radius 6,356,766 m, not R_E. [all runs]
- atmosphere: above 81,020 m an isothermal extension at 196.649 K with scale height 5,908 m (R_air T_top / g(h_top)); not US76 (denser near 110 km, far thinner above 150 km). [all runs]
- atmosphere: static, spherically symmetric, no wind; it co-rotates with Earth, so drag and Mach use the Earth-relative velocity v_rel. [all runs]
- atmosphere: in flight, an altitude below the -5,004 m floor is held at the floor state (ambient_scalar clamp; a dive ends at the ground event). [all runs]
- track phase: 1-DOF along the track in a flat local frame with constant g_eff; the carriage stays on the track at release; carriage braking is not modelled as a phase (its distance v^2/(2 a_brake) is added to the facility length) [silo_cold, silo_cold_s1]
- hot start: the propellant burned before release is reported with its delta-v equivalent; the exhaust impingement fraction f_imp on the carriage is an assumed amendment to the track equation (the system keeps (1 - f_imp) T) [silo_cold, silo_cold_s1]
- drive energy: electrical_energy = (positive drive work) / efficiency; no regeneration is credited for any negative (braking) drive work [silo_cold, silo_cold_s1]
- track: straight, L = 100 m at 1.5708 rad above horizontal, start altitude -100 m (exit at 0 m) [silo_cold, silo_cold_s1]
- constant_accel: prescribed net acceleration 3 g0 (assumed); drive force unconstrained, solved from the track equation [silo_cold, silo_cold_s1]
- constant_accel: carriage mass 0 t (assumed) [silo_cold, silo_cold_s1]
- constant_accel: braking deceleration 5 g0 (assumed) [silo_cold, silo_cold_s1]
- constant_accel: drive efficiency 0.5 (assumed) [silo_cold, silo_cold_s1]
- constant_accel: exhaust impingement fraction 0 (assumed); the system keeps (1 - f_imp) T of the on-track thrust [silo_cold, silo_cold_s1]
- constant_accel: shaft vented (no air column), no friction [silo_cold, silo_cold_s1]
- constant_accel: constant g_eff = 9.772092 m/s^2 on the track (mu/R_E^2 - omega_p^2 R_E with omega_p = 6.408435e-05 rad/s, the planar rotation rate of the site), flat 1-DOF track frame, Coriolis neglected [silo_cold, silo_cold_s1]
- constant_accel: infinite jerk at push start and release [silo_cold, silo_cold_s1]
- constant_accel: vehicle clamped to the carriage during any hold before the push [silo_cold, silo_cold_s1]
- offload: the propellant removed from a full load leaves the tanks partly filled; every dry mass (tank structure included), engine, the payload, the fairing and the aerodynamics are unchanged and each stage keeps its mixture ratio; no ullage, centre-of-gravity or tank-mass effect is modelled [pad__offload_stage1, silo_cold_s1, silo_cold_s1__pad]

## Checks

- pad: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 9.45148e-09: ok
- silo_cold: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 9.10057e-09: ok
- pad__offload_stage1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.10423e-07: ok
- silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- silo_cold_s1__pad: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.03231e-08: ok
- silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 8.84954e-09: ok

- silo_cold: dP* +1394.42 kg (an unthrottled/unconstrained upper bound: q-alpha above the baseline) against the ideal screening yardstick 684.758 kg at its release speed 76.7072 m/s (the stricter of 684.758 kg at P0 and 738.687 kg at the baseline's P*: P0): beats it by 709.661 kg (the attribution must explain this). matched-payload attribution at P_ref = 24700 kg: d dv_margin +154.914 m/s = release speed +76.7072, final speed +1.20348e-05, gravity +40.8395, drag +3.78638, steering +4.98559, back pressure +12.6074, preflight +15.1475, fairing +0.840656 m/s (residual 0 m/s); gravity + steering together +45.8251 m/s; dP* split in kg: release speed +690.459, final speed +0.000108328, gravity +367.606, drag +34.0821, steering +44.8764, back pressure +113.483, preflight +136.346, fairing +7.56695 (gravity + steering together +412.482 kg). The gravity and steering terms trade against each other as gamma* moves (the total is nearly stationary in gamma*), so only their sum is read as physics, never the split between them (docs/physics.md, 'Screening-beat rule (2-D)'). Over gamma* +/- 0.5 deg the gravity term moves -14.5588 m/s per deg, the steering term +12.252 m/s per deg, their sum -2.30677 m/s per deg. Checks: closure pass (worst residual 1.82e-12 m/s); attribution pass (worst closure 1.69e-10 m/s, worst identity 1.57e-10 m/s); M2 (diagnostic) pass (d -40.8395 m/s against the time-shift estimate -96.6616 m/s: ratio 0.4225; over gamma* +/- h: 0.347241..0.497857, robust; stage 1 alone d -13.6777 m/s: ratio 0.141501, a diagnostic); M3 pass (d -12.6074 m/s against the time-shift estimate -18.3489 m/s: ratio 0.687096; over gamma* +/- h: 0.684336..0.689772, robust); M4 pass (drag + steering +8.77197 m/s of +78.2071 m/s beyond the release speed: share 0.112163; over gamma* +/- h: 0.0229805..0.18756, robust); M5 n/a. Screening status: ok

Offload checks (a stage-1 pad control is a consistency test of the solver, and a failing one blocks findings; the screening rule for offload rows: an offload beyond the ideal screening estimate is explained only by a decomposition that closes, else bug_suspect; offload rows never enter the unexplained-beats list):
- pad control stage1: x_pad = 0, m_res(0) = -0.00158773 kg: a resolution effect: the full-load pad misses P_ref by grams of residual propellant at the feasible-side convention's resolution, within final_payload_xtol_kg; not a failure; consistency test pass
- silo_cold_s1: decomposition explained (residual -2.05e-11 m/s; stage-1 offload / screening 2.52731)

No run and no comparison is bug_suspect.
