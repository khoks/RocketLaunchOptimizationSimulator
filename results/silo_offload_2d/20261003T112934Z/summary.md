# silo_offload_2d (20261003T112934Z, git b3150c1754ee)

Comparison basis: sweep-optimized (every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, delta and the LTG pair are solved per run); planar_2d: rotating spherical Earth, ICAO atmosphere, drag, back-pressure, unthrottled; figure of merit: payload capacity P* at the target orbit

Guidance is sweep-optimized: every run shares the guidance parametrisation, the gamma* grid and the search budget; gamma*, the kick angle delta and the LTG pair (a, b) are solved per run. Not an optimal-control solution (Phase 5).

- Vehicle: generic_f9_class_2d
- Baseline: pad
- Search budget id: a17a01601d0f4ae0c48cac48342127d5597e056e769da83503d7364c7d65a7df
- Timestamp (UTC): 20261003T112934Z
- Git: b3150c1754ee

## Variants against the baseline

| quantity | pad (baseline) | silo_cold | silo_hot_ramp_on_track | silo_cold_200m |
|---|---|---|---|---|
| status | inserted | inserted | inserted | inserted |
| search status | ok | ok | ok | ok |
| run checks (closure, loss identity, insertion e) | ok | ok | ok | ok |
| screening status (closure, attribution, M3 to M5; M2 only when blocking; a failed diagnostic check in brackets) | (baseline) | ok | ok | ok |
| flags (see Flags) | - | - | - | - |
| stage-1 ignition, t_ign relative to release [s] (negative = lit before release) | -2 | 0.5 | -2 | 0.5 |
| stage-1 startup kind (step = instant full thrust: a yardstick, not achievable) | ramp | ramp | ramp | ramp |
|   its t_ramp or tau [s] | 2 | 2 | 2 | 2 |
| payload capacity P* [kg] (sweep-optimized) | 26054.4 | 27553.2 | 27788.2 | 27553.2 |
|   dP* vs baseline [kg] | (baseline) | 1498.83 | 1733.8 | 1498.83 |
|   ideal screening at this run's release speed, at the baseline's P* [kg] | (baseline) | 765.442 | 765.442 | 765.442 |
|   ideal screening at this run's release speed, at the vehicle payload P0 [kg] | (baseline) | 675.346 | 675.346 | 675.346 |
|   screening yardstick used, the stricter of the two [kg] | (baseline) | 675.346 | 675.346 | 675.346 |
|     its basis | (baseline) | P0 | P0 | P0 |
|   dP* beyond the screening yardstick [kg] | (baseline) | 823.485 | 1058.46 | 823.485 |
|   beats the screening yardstick | (baseline) | True | True | True |
|   dP* is an unthrottled/unconstrained upper bound (max-Q, q-alpha or kick) | (baseline) | True | True | True |
|   payload excess P0 - P* [kg] | -3254.4 | -4753.23 | -4988.2 | -4753.23 |
| residual propellant at P0 [kg] (signed; negative = virtual, massless shortfall) | 3235.4 | 4696.05 | 4920.58 | 4696.05 |
|   its basis | at gamma*_ref (P*-optimal guidance) | at gamma*_ref (P*-optimal guidance) | at gamma*_ref (P*-optimal guidance) | at gamma*_ref (P*-optimal guidance) |
| dv margin at P0 [m/s] (signed) | 388.964 | 551.018 | 575.26 | 551.018 |
| gamma*_ref, the flight-path angle at MECO [deg] | 22.9891 | 21.6465 | 21.455 | 21.6465 |
| kick angle delta [deg] | 2.83435 | 2.36146 | 3.65713 | 2.36146 |
| LTG a (tan of the initial pitch) | 0.610193 | 0.592158 | 0.58963 | 0.592157 |
| LTG b [1/s] | 0.00156085 | 0.00149175 | 0.00148227 | 0.00149175 |
| kick regime | after_vertical_rise | at_first_lit_instant | at_first_lit_instant | at_first_lit_instant |
|   |v_rel| at the kick [m/s] | 50 | 71.8083 | 76.7072 | 71.8083 |
|   unconstrained kick (faster than checks.unconstrained_kick_mps) | (baseline) | False | False | False |
|   kick steering loss [m/s] | 0.0258347 | 0.020867 | 0.0615533 | 0.020867 |
| speed at release [m/s] | 0 | 76.7072 | 76.7072 | 76.7072 |
| propellant burned before the flight [kg] | 2697.46 | 0 | 2697.46 | 0 |
|   its dv_vac equivalent [m/s] | 14.4078 | 0 | 14.3641 | 0 |
| MECO: t after release [s] | 151.328 | 153.828 | 151.328 | 153.828 |
|   altitude [m] | 69485.8 | 75202.2 | 75956.6 | 75202.3 |
|   |v_rel| [m/s] | 2665.03 | 2765.92 | 2781.54 | 2765.92 |
|   gamma_rel [deg] | 22.9891 | 21.6465 | 21.455 | 21.6465 |
|   downrange [m] | 99171 | 110155 | 111948 | 110155 |
| fairing drop | in the stage-2 burn (heating event) | in the stage-2 burn (heating event) | in the stage-2 burn (heating event) | in the stage-2 burn (heating event) |
|   t after release [s] | 196.808 | 193.816 | 190.609 | 193.816 |
|   altitude [m] | 110483 | 110993 | 111075 | 110993 |
| stage-2 end: t after release [s] | 536.301 | 538.801 | 536.301 | 538.801 |
|   eccentricity | 1.45116e-08 | 1.35972e-08 | 1.33923e-08 | 1.35974e-08 |
|   perigee altitude [m] | 200000 | 200000 | 200000 | 200000 |
|   apogee altitude [m] | 200000 | 200000 | 200000 | 200000 |
| gravity loss [m/s] | 1491.98 | 1450.41 | 1416.22 | 1450.41 |
| drag loss [m/s] | 26.0363 | 22.3972 | 22.5225 | 22.3972 |
| steering loss [m/s] | 88.988 | 90.1832 | 90.3055 | 90.1831 |
| back-pressure loss [m/s] | 63.1439 | 49.5718 | 46.5175 | 49.5718 |
| dv_vac from the flight start [m/s] | 9032.85 | 8898.56 | 8861.57 | 8898.56 |
|   loss-identity residual [m/s] | 0 | 0 | 0 | 0 |
| rocket-equation closure residual [m/s] | 0 | 0 | 0 | 0 |
|   pre-flight term c1 ln(m0/m_fs) [m/s] | 14.4078 | 0 | 14.3641 | 0 |
|   fairing-carry term [m/s] | 3.23341 | 2.62644 | 2.54954 | 2.62644 |
| max-Q [Pa] (unthrottled: an upper bound) | 37191.4 | 31237.6 | 31372.9 | 31237.6 |
|   at t after release [s] | 65.7515 | 57.6096 | 53.9304 | 57.6096 |
|   altitude [m] | 11019.1 | 11019.1 | 11019.1 | 11019.1 |
|   Mach | 1.53218 | 1.4042 | 1.40723 | 1.4042 |
|   above the baseline | (baseline) | False | False | False |
| peak q-alpha [Pa rad] (alpha = psi; unconstrained) | 74.7309 | 129.916 | 230.036 | 129.916 |
|   at t after release [s] | 12.4937 | 0.5 | 0 | 0.5 |
|   above the baseline | (baseline) | True | True | True |
| peak felt axial g, run-wide [g0] (phase) | 5.19547 (GRAVITY_TURN) | 5.14794 (GRAVITY_TURN) | 5.14055 (GRAVITY_TURN) | 5.14794 (GRAVITY_TURN) |
| peak felt axial g in flight [g0] | 5.19547 | 5.14794 | 5.14055 | 5.14794 |
| peak felt lateral g in flight [g0] | 6.39136e-05 | 0.000101065 | 0.00017868 | 0.000101065 |
| peak felt g on the track [g0] | n/a | 3.99648 | 3.99648 | 2.49648 |
| interface force, peak [N] | 0 | 2.24905e+07 | 2.24997e+07 | 1.40491e+07 |
| interface force, minimum [N] | 0 | 2.24905e+07 | 1.47872e+07 | 1.40491e+07 |
| hold-down force m g_ref - T, minimum over the hold [N] | -2.04006e+06 | n/a | n/a | n/a |
| peak track-normal g [g0] | 0 | 0 | 0 | 0 |
|   vehicle [g0] | 0 | 0 | 0 | 0 |
|   carriage [g0] | 0 | 0 | 0 | 0 |
| assist (drive) energy [J] | 0 | 2.24905e+09 | 1.83364e+09 | 2.80982e+09 |
| assist (drive) energy [kWh] | 0 | 624.736 | 509.343 | 780.506 |
| electrical energy [kWh] (positive drive work / efficiency) | 0 | 1249.47 | 1018.69 | 1561.01 |
| peak drive power [W] | 0 | 1.72518e+09 | 1.13428e+09 | 1.07767e+09 |
| braking distance [m] | 0 | 60 | 60 | 60 |
| facility length incl. braking [m] | 0 | 160 | 160 | 260 |
| search: P2 - P1 [kg] | 18.435 | 60.2761 | 48.0554 | 60.2761 |
|   search minus final payload [kg] | -0.03725 | -0.0367046 | -0.0364931 | -0.0367231 |
| RHS evaluations of the recorded run | 6210 | 7478 | 7162 | 7514 |

## Propellant saved at fixed payload

Offload basis: propellant saved at fixed payload. Different vehicles (each run's own propellant load, tanks partly filled, dry masses unchanged unless a row says so), the same payload and the same orbit: every offload is measured at the reference payload P_ref, the full-load pad baseline's payload capacity P* on the same vehicle and orbit (sweep-optimized guidance, the shared search budget). Reference payload P_ref = 26054.4 kg (pad's payload capacity P*).

Offload sensitivity basis: each arm perturbs the assisted run and the pad alike (a vehicle. parameter on both, a run parameter on the assisted run only: a pad has no drive); an arm's reference payload is the payload capacity of the pad under the same perturbation, and its offload is solved at that P_ref (not at the nominal one); arms carry no independent verification search.

Caveats (they travel with every number below):

- calibration: the vehicle generic_f9_class_2d carries 26,054 kg in its calibration run against the published 22,800 kg, +14.3% high, a documented calibration result (docs/findings/CAL-f9-leo-2d); read every offload as a difference between runs of the vehicle model, not as a Falcon 9 figure
- guidance is sweep-optimized (a shared gamma* grid refined per run, not optimal control) and the engines never throttle
- no structural mass is charged for the push load (the fully fuelled stack rides the push at the net acceleration plus g); the penalty rows add an assumed stage-1 dry mass, a parametric assumption, not a sized structure
- the drive is a prescribed constant acceleration with no force or power limit, the carriage is massless unless the variant states a carriage mass, and the shaft is vented (no air drag in it)
- max-Q of each offloaded run is reported beside the pad's: a lighter stack climbs faster, and no max-Q limit constrains it (there is no throttle model)
- the tanks are partly filled: dry masses and tank structure unchanged, the mixture ratio kept, no ullage, centre-of-gravity or tank-mass effect
- stage 1 is the headline: stage-2 and both-stage offloads are a property of the vehicle model (stage-2 propellant is worth about nothing at the margin on the gate vehicle), quoted net of the pad control (the gross rows beside them are not a saving of the assist); a stage-1-only offload is not assumed to maximise the total tonnes ('both' may remove more, its stage-2 share riding about free), and stage 1 stays the only headline either way

| quantity | silo_cold_s1 | silo_cold_s2 | silo_cold_both | silo_cold_s1_s2pre2t | silo_cold_s1_dry+2t | silo_cold_s1_dry+4t | silo_cold_s1_dry+8.1t | silo_cold_fix5pct | silo_cold_fix10pct | silo_hot_ramp_s1 | silo_cold_200m_s1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| assisted run (of) | silo_cold | silo_cold | silo_cold | silo_cold | silo_cold | silo_cold | silo_cold | silo_cold | silo_cold | silo_hot_ramp_on_track | silo_cold_200m |
| kind | solved, stage1 | solved, stage2 | solved, both | solved, stage1 | solved, stage1 | solved, stage1 | solved, stage1 | fixed, stage1_fraction = 0.05 | fixed, stage1_fraction = 0.1 | solved, stage1 | solved, stage1 |
| status (the solve, or a fixed case's payload search) | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| recorded run (replay it beside the pad) | silo_cold_s1 | silo_cold_s2 | silo_cold_both | silo_cold_s1_s2pre2t | silo_cold_s1_dry+2t | silo_cold_s1_dry+4t | silo_cold_s1_dry+8.1t | silo_cold_fix5pct | silo_cold_fix10pct | silo_hot_ramp_s1 | silo_cold_200m_s1 |
|   its status | inserted | inserted | inserted | inserted | inserted | inserted | inserted | inserted | inserted | inserted | inserted |
| quoted offload [t] | 41.2629 | 31.3907 | 46.1682 | 40.7685 | 32.2852 | 22.876 | 1.98048 | 20.545 | 41.09 | 46.0134 | 41.263 |
|   basis | x* at P_ref, gross: stage 1, the headline | x* net of the pad control's x_pad: a property of the vehicle model, not of the assist | x* net of the pad control's x_pad: a property of the vehicle model, not of the assist | x* at P_ref, gross: stage 1, the headline | x* at P_ref, gross: stage 1, the headline | x* at P_ref, gross: stage 1, the headline | x* at P_ref, gross: stage 1, the headline | imposed: a fixed case, whose figure is its payload capacity against P_ref | imposed: a fixed case, whose figure is its payload capacity against P_ref | x* at P_ref, gross: stage 1, the headline | x* at P_ref, gross: stage 1, the headline |
| stage-1 propellant removed, gross [t] | 41.2629 | 0 | 36.5943 | 40.7685 | 32.2852 | 22.876 | 1.98048 | 20.545 | 41.09 | 46.0134 | 41.263 |
| stage-2 propellant removed, gross [t] (a stage-2 pre-offload included) | 0 | 31.9043 | 9.57384 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| total propellant removed, gross [t] | 41.2629 | 31.9043 | 46.1682 | 42.7685 | 32.2852 | 22.876 | 1.98048 | 20.545 | 41.09 | 46.0134 | 41.263 |
|   % of the stage-1 load | 10.0421 | 0 | 8.90589 | 9.92176 | 7.85719 | 5.56728 | 0.481985 | 5 | 10 | 11.1982 | 10.0421 |
|   % of the stage-2 load | 0 | 29.6784 | 8.90589 | 1.86047 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
|   % of the total load | 7.95967 | 6.15437 | 8.90589 | 8.2501 | 6.22786 | 4.4128 | 0.382036 | 3.96316 | 7.92631 | 8.87605 | 7.95968 |
| assumed stage-1 dry mass added [t] (an assumption, not a sized structure) | 0 | 0 | 0 | 0 | 2 | 4 | 8.1 | 0 | 0 | 0 | 0 |
| payload flown [kg] (solved: P_ref; fixed: its own P*) | 26054.4 | 26054.4 | 26054.4 | 26054.4 | 26054.4 | 26054.4 | 26054.4 | 26837.6 | 26061.2 | 26054.4 | 26054.4 |
|   minus P_ref [kg] | +0 | +0 | +0 | +0 | +0 | +0 | +0 | +783.163 | +6.80004 | +0 | +0 |
| verification: P* of the offloaded vehicle [kg] | 26054.4 | 26069.8 | 26054.4 | 26054.8 | 26054.4 | 26054.4 | 26054.4 | n/a | n/a | 26054.4 | 26054.4 |
|   P* - P_ref [kg] | +0.00845215 | +15.3595 | -0.00034364 | +0.368808 | +0.00298696 | +0.0029226 | +0.000649211 | n/a | n/a | +0.00879778 | +0.00599645 |
|   tolerance [kg] (checks.search_final_flag_rel x P_ref) | 2.60544 | 2.60544 | 2.60544 | 2.60544 | 2.60544 | 2.60544 | 2.60544 | n/a | n/a | 2.60544 | 2.60544 |
|   passed | True | False | True | True | True | True | True | n/a | n/a | True | True |
| pad control's offload in this mode [t] | 0 | 0.513556 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | 0 | 0 |
|   offload net of the pad control [t] | 41.2629 | 31.3907 | 46.1682 | 40.7685 | 32.2852 | 22.876 | 1.98048 | n/a | n/a | 46.0134 | 41.263 |
| liftoff mass [kg] | 531091 | 540450 | 526186 | 529586 | 542069 | 553478 | 578474 | 552593 | 531271 | 526341 | 531091 |
|   pad's [kg] | 572354 | 572354 | 572354 | 572354 | 572354 | 572354 | 572354 | 572354 | 572354 | 572354 | 572354 |
| MECO: t after release [s] | 138.531 | 153.828 | 140.262 | 138.715 | 141.86 | 145.348 | 153.094 | 146.212 | 138.596 | 134.27 | 138.531 |
|   pad's [s] | 151.328 | 151.328 | 151.328 | 151.328 | 151.328 | 151.328 | 151.328 | 151.328 | 151.328 | 151.328 | 151.328 |
| max-Q [Pa] (unthrottled: an upper bound) | 38438.5 | 37884.7 | 39972.3 | 38890.4 | 36378.8 | 34376.6 | 30424.5 | 34610.2 | 38399.9 | 39712.6 | 38437.4 |
|   pad's [Pa] | 37191.4 | 37191.4 | 37191.4 | 37191.4 | 37191.4 | 37191.4 | 37191.4 | 37191.4 | 37191.4 | 37191.4 | 37191.4 |
|   above the pad's | True | True | True | True | False | False | False | False | True | True | True |
| peak felt axial g in flight [g0] | 5.19546 | 6.47524 | 5.52293 | 5.2606 | 5.13197 | 5.07 | 4.94751 | 5.17054 | 5.19525 | 5.19545 | 5.19546 |
|   pad's [g0] | 5.19547 | 5.19547 | 5.19547 | 5.19547 | 5.19547 | 5.19547 | 5.19547 | 5.19547 | 5.19547 | 5.19547 | 5.19547 |
| speed at release [m/s] | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 | 76.7072 |
| peak felt g on the track [g0] | 3.99648 | 3.99648 | 3.99648 | 3.99648 | 3.99648 | 3.99648 | 3.99648 | 3.99648 | 3.99648 | 3.99648 | 2.49648 |
| interface force, peak [N] | 2.08146e+07 | 2.11813e+07 | 2.06223e+07 | 2.07556e+07 | 2.12448e+07 | 2.16919e+07 | 2.26716e+07 | 2.16572e+07 | 2.08216e+07 | 2.06284e+07 | 1.30022e+07 |
| facility length incl. braking [m] | 160 | 160 | 160 | 160 | 160 | 160 | 160 | 160 | 160 | 160 | 260 |
| ideal-screening offload at this release speed [t] | 14.9766 | 14.9766 | 14.9766 | 14.9766 | 14.9766 | 14.9766 | 14.9766 | 14.9766 | 14.9766 | 14.9766 | 14.9766 |
|   stage-1 offload / screening offload | 2.75516 | n/a | n/a | n/a | 2.15571 | 1.52745 | 0.132238 | 1.37181 | 2.74361 | 3.07235 | 2.75516 |
|   beats the screening estimate | True | n/a | n/a | n/a | True | True | False | True | True | True | True |
| decomposition status | explained | explained | explained | explained | explained | explained | explained | explained | explained | explained | explained |
|   residual [m/s] | 4.52e-12 | -1.19e-12 | -4.09e-12 | 2.89e-11 | -6.93e-12 | 8.36e-10 | -6.59e-12 | 3.99e-12 | -1.49e-11 | -9.58e-12 | 5.2e-12 |
| paired pad (the same propellant change, no penalty) | silo_cold_s1__pad | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
|   its P* [kg] | 24652.4 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
|   its P* - P_ref [kg] | -1402.03 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
|   assisted P* - paired pad P* [kg] (one vehicle, attributed) | +1402.04 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
|   screening status (against the paired pad) | ok | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| flags (see Flags) | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| RP-1 removed [kg] | 12402 | 9586.12 | 13875.4 | 12854.3 | 9703.63 | 6875.59 | 595.252 | 6175 | 12350 | 13829.8 | 12402 |
| LOX removed [kg] | 28860.9 | 22318.2 | 32292.8 | 29914.2 | 22581.6 | 16000.4 | 1385.23 | 14370 | 28740 | 32183.7 | 28861 |
| combustion heat of the removed RP-1, lower heating value [MJ] | 533657 | 412491 | 597058 | 553121 | 417547 | 295857 | 25613.7 | 265710 | 531420 | 595096 | 533658 |
|   [kWh] | 148238 | 114581 | 165849 | 153645 | 115985 | 82182.4 | 7114.91 | 73808.4 | 147617 | 165304 | 148238 |
| electrical energy of the push [MJ] | 4162.91 | 4236.27 | 4124.46 | 4151.11 | 4248.96 | 4338.39 | 4534.31 | 4331.45 | 4164.32 | 3293.01 | 5200.89 |
|   [kWh] | 1156.36 | 1176.74 | 1145.68 | 1153.09 | 1180.27 | 1205.11 | 1259.53 | 1203.18 | 1156.76 | 914.724 | 1444.69 |
| heat / electricity (not an efficiency claim) | 128.193 | 97.3712 | 144.76 | 133.246 | 98.2705 | 68.1951 | 5.64885 | 61.3445 | 127.613 | 180.715 | 102.609 |


Energy comparison: the fuel (RP-1) removed is each stage's removed propellant times its fuel fraction (the energy block's fuel mass over the experiment vehicle's full load: the mixture ratio kept, on any load; the lower heating value from the energy block), the oxidiser (LOX) the rest; the combustion heat is the removed fuel's mass times its lower heating value, and the electrical energy is the offloaded run's push (positive drive work over the drive efficiency). The heat / electricity ratio is not an efficiency claim; it leaves out the energy to produce the removed oxidiser (LOX: air separation and liquefaction); the energy to extract, refine and deliver the removed fuel; electricity generation, transmission and storage losses (the push's electrical energy is its positive drive work over the drive efficiency, metered at the drive); the energy of the push's facility beyond the drive (braking, the carriage's return).

### Decomposition

Cross-vehicle decomposition of each case against the pad, both at P_ref (docs/physics.md, 'Cross-vehicle decomposition'): the ideal delta-v the case's vehicle does without, D_id(pad) - D_id(case), split into the release-speed head start and the differences in the losses, the pre-flight burn, the fairing term and the margin; each cell is m/s (kg of the offload, a proportional split). Only the joint gravity + steering term is read as physics. The residual must stay below checks.closure_tol_mps: explained when it does, bug_suspect (findings blocked) when it does not.

| term: m/s (kg) | silo_cold_s1 | silo_cold_s2 | silo_cold_both | silo_cold_s1_s2pre2t | silo_cold_s1_dry+2t | silo_cold_s1_dry+4t | silo_cold_s1_dry+8.1t | silo_cold_fix5pct | silo_cold_fix10pct | silo_hot_ramp_s1 | silo_cold_200m_s1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| release speed | +76.7072 (+13869.9) | +76.7072 (+6056.83) | +76.7072 (+11197.6) | +76.7072 (+13184.3) | +76.7072 (+12178.4) | +76.7072 (+9918.43) | +76.7072 (+1300) | +76.7072 (+14135.3) | +76.7072 (+13872.1) | +76.7072 (+13808.6) | +76.7072 (+13869.9) |
| final speed | +2.74331e-05 (+0.00496035) | +2.20986e-05 (+0.00174491) | +2.83062e-05 (+0.00413209) | +2.75308e-05 (+0.00473195) | +2.7499e-05 (+0.00436586) | +2.75701e-05 (+0.00356488) | +2.77101e-05 (+0.00046962) | +2.72821e-05 (+0.00502746) | +2.50612e-05 (+0.0045322) | +2.73546e-05 (+0.00492427) | +2.74256e-05 (+0.00495899) |
| gravity | +124.775 (+22561.3) | +219.927 (+17365.5) | +178.661 (+26080.6) | +139.26 (+23935.7) | +99.866 (+15855.2) | +73.5904 (+9515.42) | +14.0736 (+238.514) | +87.2554 (+16079.1) | +124.266 (+22472.9) | +165.803 (+29847.3) | +124.727 (+22552.6) |
| drag | -0.876616 (-158.506) | -1.2167 (-96.0709) | -2.13313 (-311.391) | -1.24058 (-213.229) | +0.433758 (+68.8653) | +1.70878 (+220.949) | +4.23472 (+71.7684) | +1.43913 (+265.198) | -0.85108 (-153.914) | -1.72482 (-310.496) | -0.875423 (-158.291) |
| steering | -0.0652669 (-11.8013) | +83.0987 (+6561.51) | +36.4168 (+5316.06) | +6.72613 (+1156.08) | -1.59189 (-252.735) | -3.26292 (-421.903) | -6.69561 (-113.475) | +5.13195 (+945.698) | +0.179762 (+32.5092) | +0.069473 (+12.5063) | -0.0197315 (-3.56777) |
| back pressure | +13.2798 (+2401.2) | +13.0346 (+1029.22) | +13.0369 (+1903.1) | +13.2105 (+2270.6) | +13.4239 (+2131.23) | +13.5302 (+1749.49) | +13.6143 (+230.729) | +13.4937 (+2486.57) | +13.2835 (+2402.26) | +16.0555 (+2890.25) | +13.2801 (+2401.26) |
| preflight | +14.4078 (+2605.16) | +14.4078 (+1137.64) | +14.4078 (+2103.22) | +14.4078 (+2476.38) | +14.4078 (+2287.44) | +14.4078 (+1862.96) | +14.4078 (+244.177) | +14.4078 (+2655.01) | +14.4078 (+2605.58) | -1.26279 (-227.322) | +14.4078 (+2605.16) |
| fairing | -0.0242456 (-4.38399) | -1.9041 (-150.348) | -0.829478 (-121.086) | -0.240606 (-41.3549) | +0.106309 (+16.8781) | +0.236651 (+30.5995) | +0.516724 (+8.75724) | +0.31262 (+57.6086) | -0.0156293 (-2.82649) | -0.0407213 (-7.3305) | -0.0229342 (-4.14687) |
| margin | +4.90546e-05 (+0.00886987) | -1.06653e-05 (-0.000842135) | +4.90689e-05 (+0.00716299) | +5.18096e-05 (+0.00890495) | +4.8977e-05 (+0.00777579) | +5.21052e-05 (+0.00673734) | +4.98196e-05 (+0.000844324) | -87.2577 (-16079.5) | -0.766726 (-138.659) | +4.88084e-05 (+0.00878632) | +4.89062e-05 (+0.00884304) |
| gravity + steering | +124.71 (+22549.5) | +303.026 (+23927) | +215.078 (+31396.7) | +145.986 (+25091.8) | +98.2741 (+15602.4) | +70.3275 (+9093.52) | +7.37797 (+125.039) | +92.3873 (+17024.8) | +124.446 (+22505.4) | +165.873 (+29859.8) | +124.707 (+22549.1) |
| D_id(pad) - D_id(case) [m/s] | 228.204 | 404.054 | 316.267 | 248.83 | 203.353 | 176.918 | 116.859 | 111.49 | 227.211 | 255.607 | 228.204 |
| offload split [kg] | 41262.9 | 31904.3 | 46168.2 | 42768.5 | 32285.2 | 22876 | 1980.48 | 20545 | 41090 | 46013.4 | 41263 |
| residual [m/s] | 4.52e-12 | -1.19e-12 | -4.09e-12 | 2.89e-11 | -6.93e-12 | 8.36e-10 | -6.59e-12 | 3.99e-12 | -1.49e-11 | -9.58e-12 | 5.2e-12 |
| status | explained | explained | explained | explained | explained | explained | explained | explained | explained | explained | explained |

### Pad controls

| quantity | stage1 | stage2 | both |
|---|---|---|---|
| recorded run | pad__offload_stage1 | pad__offload_stage2 | pad__offload_both |
| status | no_offload | ok | ok |
| x_pad [kg] | 0 | 513.556 | 0 |
| m_res at x_pad [kg] (signed) | -0.00163769 | 6.10574e-06 | 0.000572554 |
| dv margin at x_pad [m/s] (signed) | -0.000185962 | 6.93314e-07 | 6.50142e-05 |
| abs(dm_res/dx) from the solve's own logs [kg/kg] | 0.0309062 | 0.00314715 | 0.025202 |
| stage 1: bound final_payload_xtol_kg / abs(dm_res/dx) [kg] | 1.6178 | n/a | n/a |
|   0 <= x_pad <= bound (an ok control) | n/a | n/a | n/a |
| ended no_offload by grams (a resolution effect) | True | False | False |
| stage 1: consistency test of the solver (section 5.3) | pass | n/a | n/a |
| verification: P* - P_ref [kg] | n/a | +0.2306 | +0 |
|   passed | n/a | True | True |

- pad control stage1: x_pad = 0, m_res(0) = -0.00163769 kg: a resolution effect: the full-load pad misses P_ref by grams of residual propellant at the feasible-side convention's resolution, within final_payload_xtol_kg; not a failure; consistency test pass
- pad control stage2: x_pad = 513.556 kg (status ok); a property of the vehicle model, which the assisted cases are net of
- pad control both: x_pad = 0 kg (status ok); a property of the vehicle model, which the assisted cases are net of

### Sensitivity

| case | parameter | change | pad perturbed | P_ref [kg] (the same-perturbation pad's P*) | status | offload [t] | change vs nominal [t] | % of the stage-1 load | decomposition | offload / screening | solve reused (same trajectory) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| silo_cold_s1 | vehicle.stages.stage1.dry_mass_t | +10% | yes | 25661 | ok | 41.6395 | 0.376641 | 10.1337 | explained | 2.77146 | no |
| silo_cold_s1 | vehicle.stages.stage1.dry_mass_t | -10% | yes | 26456.3 | ok | 40.8924 | -0.370538 | 9.9519 | explained | 2.73912 | no |
| silo_cold_s1 | vehicle.stages.stage1.engine.isp_vac_s | +10% | yes | 29927.4 | ok | 38.668 | -2.59489 | 9.41057 | explained | 2.56454 | no |
| silo_cold_s1 | vehicle.stages.stage1.engine.isp_vac_s | -10% | yes | 22478.3 | ok | 44.4645 | 3.20164 | 10.8213 | explained | 2.9876 | no |
| silo_cold_s1 | vehicle.aero.cd_scale | +10% | yes | 26015.5 | ok | 41.222 | -0.0408864 | 10.0321 | explained | 2.75262 | no |
| silo_cold_s1 | vehicle.aero.cd_scale | -10% | yes | 26093.5 | ok | 41.3042 | 0.0412721 | 10.0521 | explained | 2.75773 | no |
| silo_cold_s1 | assist.drive_efficiency | +10% | no | 26054.4 | ok | 41.2629 | 0 | 10.0421 | explained | 2.75516 | yes |
| silo_cold_s1 | assist.drive_efficiency | -10% | no | 26054.4 | ok | 41.2629 | 0 | 10.0421 | explained | 2.75516 | yes |

## Bounds

(no bounds declared)

## Cases

(no cases declared)

## Sensitivity

(no run has payload sensitivity cases: the sensitivity block's `of` lists no run; its params perturb the offload block's sensitivity arms, reported in the section "Propellant saved at fixed payload"; C_D: drag is modelled: see the vehicle.aero.cd_scale cases)

## Flags

- pad__offload_stage2: offload: (P = offload x) search_vs_final_payload: the search payload 513.443 kg differs from the final 513.556 kg by -0.113967 kg (above 0.0001 of P_final)
- silo_cold_s2: offload: (P = offload x) P1_backoff: the P1 payload search backed off 3 time(s) from evaluations that failed at P = 32000, 28000 kg (nonconverged), offload: (P = offload x) refine: gamma* = 0.400453089 rad is infeasible only by the direct-root rule, offload: (P = offload x) refine: the first optimum 0.314261631 rad ended within gamma_xatol of an interior edge of [0.314159265, 0.453785606] rad; the window was shifted once to [0.244448461, 0.384074801] rad, where the search ended at 0.305231777 rad, offload: offload_verify_mismatch: the payload search of the vehicle offloaded by 31904.3 kg ended 'ok' with P* = 26069.8 kg, +15.3595 kg from P_ref (tolerance 2.60544 kg)

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
- pad: held down to the release at t = 0 s; stage 1 lit at t = -2 s with a ramp startup, then clamped until its thrust exceeds its weight [pad, pad__offload_stage1, pad__offload_stage2, pad__offload_both, silo_cold_s1__pad]
- atmosphere: ICAO standard atmosphere closed forms (layer table of ambiance.CONST) from -5,004 m to 81,020 m geometric altitude; the geometric to geopotential conversion uses the ICAO radius 6,356,766 m, not R_E. [all runs]
- atmosphere: above 81,020 m an isothermal extension at 196.649 K with scale height 5,908 m (R_air T_top / g(h_top)); not US76 (denser near 110 km, far thinner above 150 km). [all runs]
- atmosphere: static, spherically symmetric, no wind; it co-rotates with Earth, so drag and Mach use the Earth-relative velocity v_rel. [all runs]
- atmosphere: in flight, an altitude below the -5,004 m floor is held at the floor state (ambient_scalar clamp; a dive ends at the ground event). [all runs]
- track phase: 1-DOF along the track in a flat local frame with constant g_eff; the carriage stays on the track at release; carriage braking is not modelled as a phase (its distance v^2/(2 a_brake) is added to the facility length) [silo_cold, silo_hot_ramp_on_track, silo_cold_200m, silo_cold_s1, silo_cold_s2, silo_cold_both, silo_cold_s1_s2pre2t, silo_cold_s1_dry+2t, silo_cold_s1_dry+4t, silo_cold_s1_dry+8.1t, silo_cold_fix5pct, silo_cold_fix10pct, silo_hot_ramp_s1, silo_cold_200m_s1]
- hot start: the propellant burned before release is reported with its delta-v equivalent; the exhaust impingement fraction f_imp on the carriage is an assumed amendment to the track equation (the system keeps (1 - f_imp) T) [silo_cold, silo_hot_ramp_on_track, silo_cold_200m, silo_cold_s1, silo_cold_s2, silo_cold_both, silo_cold_s1_s2pre2t, silo_cold_s1_dry+2t, silo_cold_s1_dry+4t, silo_cold_s1_dry+8.1t, silo_cold_fix5pct, silo_cold_fix10pct, silo_hot_ramp_s1, silo_cold_200m_s1]
- drive energy: electrical_energy = (positive drive work) / efficiency; no regeneration is credited for any negative (braking) drive work [silo_cold, silo_hot_ramp_on_track, silo_cold_200m, silo_cold_s1, silo_cold_s2, silo_cold_both, silo_cold_s1_s2pre2t, silo_cold_s1_dry+2t, silo_cold_s1_dry+4t, silo_cold_s1_dry+8.1t, silo_cold_fix5pct, silo_cold_fix10pct, silo_hot_ramp_s1, silo_cold_200m_s1]
- track: straight, L = 100 m at 1.5708 rad above horizontal, start altitude -100 m (exit at 0 m) [silo_cold, silo_hot_ramp_on_track, silo_cold_s1, silo_cold_s2, silo_cold_both, silo_cold_s1_s2pre2t, silo_cold_s1_dry+2t, silo_cold_s1_dry+4t, silo_cold_s1_dry+8.1t, silo_cold_fix5pct, silo_cold_fix10pct, silo_hot_ramp_s1]
- constant_accel: prescribed net acceleration 3 g0 (assumed); drive force unconstrained, solved from the track equation [silo_cold, silo_hot_ramp_on_track, silo_cold_s1, silo_cold_s2, silo_cold_both, silo_cold_s1_s2pre2t, silo_cold_s1_dry+2t, silo_cold_s1_dry+4t, silo_cold_s1_dry+8.1t, silo_cold_fix5pct, silo_cold_fix10pct, silo_hot_ramp_s1]
- constant_accel: carriage mass 0 t (assumed) [silo_cold, silo_hot_ramp_on_track, silo_cold_200m, silo_cold_s1, silo_cold_s2, silo_cold_both, silo_cold_s1_s2pre2t, silo_cold_s1_dry+2t, silo_cold_s1_dry+4t, silo_cold_s1_dry+8.1t, silo_cold_fix5pct, silo_cold_fix10pct, silo_hot_ramp_s1, silo_cold_200m_s1]
- constant_accel: braking deceleration 5 g0 (assumed) [silo_cold, silo_hot_ramp_on_track, silo_cold_200m, silo_cold_s1, silo_cold_s2, silo_cold_both, silo_cold_s1_s2pre2t, silo_cold_s1_dry+2t, silo_cold_s1_dry+4t, silo_cold_s1_dry+8.1t, silo_cold_fix5pct, silo_cold_fix10pct, silo_hot_ramp_s1, silo_cold_200m_s1]
- constant_accel: drive efficiency 0.5 (assumed) [silo_cold, silo_hot_ramp_on_track, silo_cold_200m, silo_cold_s1, silo_cold_s2, silo_cold_both, silo_cold_s1_s2pre2t, silo_cold_s1_dry+2t, silo_cold_s1_dry+4t, silo_cold_s1_dry+8.1t, silo_cold_fix5pct, silo_cold_fix10pct, silo_hot_ramp_s1, silo_cold_200m_s1]
- constant_accel: exhaust impingement fraction 0 (assumed); the system keeps (1 - f_imp) T of the on-track thrust [silo_cold, silo_hot_ramp_on_track, silo_cold_200m, silo_cold_s1, silo_cold_s2, silo_cold_both, silo_cold_s1_s2pre2t, silo_cold_s1_dry+2t, silo_cold_s1_dry+4t, silo_cold_s1_dry+8.1t, silo_cold_fix5pct, silo_cold_fix10pct, silo_hot_ramp_s1, silo_cold_200m_s1]
- constant_accel: shaft vented (no air column), no friction [silo_cold, silo_hot_ramp_on_track, silo_cold_200m, silo_cold_s1, silo_cold_s2, silo_cold_both, silo_cold_s1_s2pre2t, silo_cold_s1_dry+2t, silo_cold_s1_dry+4t, silo_cold_s1_dry+8.1t, silo_cold_fix5pct, silo_cold_fix10pct, silo_hot_ramp_s1, silo_cold_200m_s1]
- constant_accel: constant g_eff = 9.772092 m/s^2 on the track (mu/R_E^2 - omega_p^2 R_E with omega_p = 6.408435e-05 rad/s, the planar rotation rate of the site), flat 1-DOF track frame, Coriolis neglected [silo_cold, silo_hot_ramp_on_track, silo_cold_200m, silo_cold_s1, silo_cold_s2, silo_cold_both, silo_cold_s1_s2pre2t, silo_cold_s1_dry+2t, silo_cold_s1_dry+4t, silo_cold_s1_dry+8.1t, silo_cold_fix5pct, silo_cold_fix10pct, silo_hot_ramp_s1, silo_cold_200m_s1]
- constant_accel: infinite jerk at push start and release [silo_cold, silo_hot_ramp_on_track, silo_cold_200m, silo_cold_s1, silo_cold_s2, silo_cold_both, silo_cold_s1_s2pre2t, silo_cold_s1_dry+2t, silo_cold_s1_dry+4t, silo_cold_s1_dry+8.1t, silo_cold_fix5pct, silo_cold_fix10pct, silo_hot_ramp_s1, silo_cold_200m_s1]
- constant_accel: vehicle clamped to the carriage during any hold before the push [silo_cold, silo_hot_ramp_on_track, silo_cold_200m, silo_cold_s1, silo_cold_s2, silo_cold_both, silo_cold_s1_s2pre2t, silo_cold_s1_dry+2t, silo_cold_s1_dry+4t, silo_cold_s1_dry+8.1t, silo_cold_fix5pct, silo_cold_fix10pct, silo_hot_ramp_s1, silo_cold_200m_s1]
- track: straight, L = 200 m at 1.5708 rad above horizontal, start altitude -200 m (exit at 0 m) [silo_cold_200m, silo_cold_200m_s1]
- constant_accel: prescribed net acceleration 1.5 g0 (assumed); drive force unconstrained, solved from the track equation [silo_cold_200m, silo_cold_200m_s1]
- constant_accel: the net acceleration is derived from the configured exit speed 76.7072 m/s (assumed) and the track length L, a = v_exit^2 / (2 L); the push time is 2 L / v_exit [silo_cold_200m, silo_cold_200m_s1]
- offload: the propellant removed from a full load leaves the tanks partly filled; every dry mass (tank structure included), engine, the payload, the fairing and the aerodynamics are unchanged and each stage keeps its mixture ratio; no ullage, centre-of-gravity or tank-mass effect is modelled [pad__offload_stage1, pad__offload_stage2, pad__offload_both, silo_cold_s1, silo_cold_s1__pad, silo_cold_s2, silo_cold_both, silo_cold_s1_s2pre2t, silo_cold_s1_dry+2t, silo_cold_s1_dry+4t, silo_cold_s1_dry+8.1t, silo_cold_fix5pct, silo_cold_fix10pct, silo_hot_ramp_s1, silo_cold_200m_s1]
- offload: stage-1 dry mass +2 t is an assumed structural penalty (a parametric row), not a structure sized for the push load [silo_cold_s1_dry+2t]
- offload: stage-1 dry mass +4 t is an assumed structural penalty (a parametric row), not a structure sized for the push load [silo_cold_s1_dry+4t]
- offload: stage-1 dry mass +8.1 t is an assumed structural penalty (a parametric row), not a structure sized for the push load [silo_cold_s1_dry+8.1t]

## Checks

- pad: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.45116e-08: ok
- silo_cold: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35972e-08: ok
- silo_hot_ramp_on_track: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.33923e-08: ok
- silo_cold_200m: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.35974e-08: ok
- pad__offload_stage1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.03271e-07: ok
- pad__offload_stage2: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- pad__offload_both: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- silo_cold_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- silo_cold_s1__pad: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.42975e-08: ok
- silo_cold_s2: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 4.56768e-09: ok
- silo_cold_both: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- silo_cold_s1_s2pre2t: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- silo_cold_s1_dry+2t: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- silo_cold_s1_dry+4t: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- silo_cold_s1_dry+8.1t: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- silo_cold_fix5pct: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.33193e-08: ok
- silo_cold_fix10pct: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.3659e-08: ok
- silo_hot_ramp_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- silo_cold_200m_s1: closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- pad__offload_stage2 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.44647e-08: ok
- pad__offload_both (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.45116e-08: ok
- silo_cold_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36282e-08: ok
- silo_cold_s2 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 5.32478e-09: ok
- silo_cold_both (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.06035e-08: ok
- silo_cold_s1_s2pre2t (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.2724e-08: ok
- silo_cold_s1_dry+2t (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36281e-08: ok
- silo_cold_s1_dry+4t (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36248e-08: ok
- silo_cold_s1_dry+8.1t (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.33651e-08: ok
- silo_hot_ramp_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.33661e-08: ok
- silo_cold_200m_s1 (verification search): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.36408e-08: ok
- pad__vehicle.stages.stage1.dry_mass_t__+0.1 (offload sensitivity pad): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.45787e-08: ok
- silo_cold_s1__vehicle.stages.stage1.dry_mass_t__+0.1 (offload sensitivity): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- pad__vehicle.stages.stage1.dry_mass_t__-0.1 (offload sensitivity pad): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.4546e-08: ok
- silo_cold_s1__vehicle.stages.stage1.dry_mass_t__-0.1 (offload sensitivity): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- pad__vehicle.stages.stage1.engine.isp_vac_s__+0.1 (offload sensitivity pad): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.41435e-08: ok
- silo_cold_s1__vehicle.stages.stage1.engine.isp_vac_s__+0.1 (offload sensitivity): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- pad__vehicle.stages.stage1.engine.isp_vac_s__-0.1 (offload sensitivity pad): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.4939e-08: ok
- silo_cold_s1__vehicle.stages.stage1.engine.isp_vac_s__-0.1 (offload sensitivity): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- pad__vehicle.aero.cd_scale__+0.1 (offload sensitivity pad): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.45804e-08: ok
- silo_cold_s1__vehicle.aero.cd_scale__+0.1 (offload sensitivity): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- pad__vehicle.aero.cd_scale__-0.1 (offload sensitivity pad): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 1.46179e-08: ok
- silo_cold_s1__vehicle.aero.cd_scale__-0.1 (offload sensitivity): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- silo_cold_s1__assist.drive_efficiency__+0.1 (offload sensitivity): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok
- silo_cold_s1__assist.drive_efficiency__-0.1 (offload sensitivity): closure residual 0 m/s, loss-identity residual 0 m/s, insertion e 0: ok

- silo_cold: dP* +1498.83 kg (an unthrottled/unconstrained upper bound: q-alpha above the baseline) against the ideal screening yardstick 675.346 kg at its release speed 76.7072 m/s (the stricter of 675.346 kg at P0 and 765.442 kg at the baseline's P*: P0): beats it by 823.485 kg (the attribution must explain this). matched-payload attribution at P_ref = 26054.4 kg: d dv_margin +165.248 m/s = release speed +76.7072, final speed +1.19114e-05, gravity +47.16, drag +3.50712, steering +9.27295, back pressure +13.5742, preflight +14.4078, fairing +0.618272 m/s (residual 0 m/s); gravity + steering together +56.4329 m/s; dP* split in kg: release speed +695.751, final speed +0.000108039, gravity +427.751, drag +31.8104, steering +84.1076, back pressure +123.121, preflight +130.682, fairing +5.60786 (gravity + steering together +511.859 kg). The gravity and steering terms trade against each other as gamma* moves (the total is nearly stationary in gamma*), so only their sum is read as physics, never the split between them (docs/physics.md, 'Screening-beat rule (2-D)'). Over gamma* +/- 0.5 deg the gravity term moves -15.1386 m/s per deg, the steering term +13.06 m/s per deg, their sum -2.0786 m/s per deg. Checks: closure pass (worst residual 1.27e-11 m/s); attribution pass (worst closure 8.7e-12 m/s, worst identity 1.27e-11 m/s); M2 (diagnostic) pass (d -47.16 m/s against the time-shift estimate -105.055 m/s: ratio 0.448907; over gamma* +/- h: 0.376919..0.521021, robust; stage 1 alone d -14.4231 m/s: ratio 0.137291, a diagnostic); M3 pass (d -13.5742 m/s against the time-shift estimate -20.1817 m/s: ratio 0.672602; over gamma* +/- h: 0.670781..0.674368, robust); M4 pass (drag + steering +12.7801 m/s of +88.5403 m/s beyond the release speed: share 0.144342; over gamma* +/- h: 0.0626049..0.216255, robust); M5 n/a. Screening status: ok
- silo_hot_ramp_on_track: dP* +1733.8 kg (an unthrottled/unconstrained upper bound: q-alpha above the baseline) against the ideal screening yardstick 675.346 kg at its release speed 76.7072 m/s (the stricter of 675.346 kg at P0 and 765.442 kg at the baseline's P*: P0): beats it by 1058.46 kg (the attribution must explain this). matched-payload attribution at P_ref = 26054.4 kg: d dv_margin +190.151 m/s = release speed +76.7072, final speed -1.64382e-07, gravity +82.1139, drag +3.35604, steering +10.6576, back pressure +16.6201, preflight +0, fairing +0.696231 m/s (residual 1.0366e-09 m/s); gravity + steering together +92.7715 m/s; dP* split in kg: release speed +699.419, final speed -1.49884e-06, gravity +748.718, drag +30.6005, steering +97.1761, back pressure +151.543, preflight +0, fairing +6.34826 (gravity + steering together +845.894 kg). The gravity and steering terms trade against each other as gamma* moves (the total is nearly stationary in gamma*), so only their sum is read as physics, never the split between them (docs/physics.md, 'Screening-beat rule (2-D)'). Over gamma* +/- 0.5 deg the gravity term moves -15.2017 m/s per deg, the steering term +12.9292 m/s per deg, their sum -2.27251 m/s per deg. Checks: closure pass (worst residual 1.82e-11 m/s); attribution pass (worst closure 1.04e-09 m/s, worst identity 1.04e-09 m/s); M2 (diagnostic) pass (d -82.1139 m/s against the time-shift estimate -105.055 m/s: ratio 0.781626; over gamma* +/- h: 0.709339..0.854041, robust; stage 1 alone d -44.9057 m/s: ratio 0.427449, a diagnostic); M3 pass (d -16.6201 m/s against the time-shift estimate -20.1817 m/s: ratio 0.823524; over gamma* +/- h: 0.82171..0.825285, robust); M4 pass (drag + steering +14.0136 m/s of +113.444 m/s beyond the release speed: share 0.123529; over gamma* +/- h: 0.0602129..0.178751, robust); M5 n/a. Screening status: ok
- silo_cold_200m: dP* +1498.83 kg (an unthrottled/unconstrained upper bound: q-alpha above the baseline) against the ideal screening yardstick 675.346 kg at its release speed 76.7072 m/s (the stricter of 675.346 kg at P0 and 765.442 kg at the baseline's P*: P0): beats it by 823.485 kg (the attribution must explain this). matched-payload attribution at P_ref = 26054.4 kg: d dv_margin +165.248 m/s = release speed +76.7072, final speed +1.19122e-05, gravity +47.1599, drag +3.50712, steering +9.27301, back pressure +13.5742, preflight +14.4078, fairing +0.618274 m/s (residual 0 m/s); gravity + steering together +56.4329 m/s; dP* split in kg: release speed +695.751, final speed +0.000108046, gravity +427.751, drag +31.8104, steering +84.1082, back pressure +123.121, preflight +130.682, fairing +5.60788 (gravity + steering together +511.859 kg). The gravity and steering terms trade against each other as gamma* moves (the total is nearly stationary in gamma*), so only their sum is read as physics, never the split between them (docs/physics.md, 'Screening-beat rule (2-D)'). Over gamma* +/- 0.5 deg the gravity term moves -15.1386 m/s per deg, the steering term +13.06 m/s per deg, their sum -2.07862 m/s per deg. Checks: closure pass (worst residual 9.09e-12 m/s); attribution pass (worst closure 7.28e-12 m/s, worst identity 4.55e-12 m/s); M2 (diagnostic) pass (d -47.1599 m/s against the time-shift estimate -105.055 m/s: ratio 0.448906; over gamma* +/- h: 0.376919..0.52102, robust; stage 1 alone d -14.4231 m/s: ratio 0.137291, a diagnostic); M3 pass (d -13.5742 m/s against the time-shift estimate -20.1817 m/s: ratio 0.672602; over gamma* +/- h: 0.670781..0.674368, robust); M4 pass (drag + steering +12.7801 m/s of +88.5403 m/s beyond the release speed: share 0.144342; over gamma* +/- h: 0.0626057..0.216255, robust); M5 n/a. Screening status: ok

Offload checks (a stage-1 pad control is a consistency test of the solver, and a failing one blocks findings; the screening rule for offload rows: an offload beyond the ideal screening estimate is explained only by a decomposition that closes, else bug_suspect; offload rows never enter the unexplained-beats list):
- pad control stage1: x_pad = 0, m_res(0) = -0.00163769 kg: a resolution effect: the full-load pad misses P_ref by grams of residual propellant at the feasible-side convention's resolution, within final_payload_xtol_kg; not a failure; consistency test pass
- silo_cold_s1: decomposition explained (residual 4.52e-12 m/s; stage-1 offload / screening 2.75516)
- silo_cold_s2: decomposition explained (residual -1.19e-12 m/s; stage-1 offload / screening n/a)
- silo_cold_both: decomposition explained (residual -4.09e-12 m/s; stage-1 offload / screening n/a)
- silo_cold_s1_s2pre2t: decomposition explained (residual 2.89e-11 m/s; stage-1 offload / screening n/a)
- silo_cold_s1_dry+2t: decomposition explained (residual -6.93e-12 m/s; stage-1 offload / screening 2.15571)
- silo_cold_s1_dry+4t: decomposition explained (residual 8.36e-10 m/s; stage-1 offload / screening 1.52745)
- silo_cold_s1_dry+8.1t: decomposition explained (residual -6.59e-12 m/s; stage-1 offload / screening 0.132238)
- silo_cold_fix5pct: decomposition explained (residual 3.99e-12 m/s; stage-1 offload / screening 1.37181)
- silo_cold_fix10pct: decomposition explained (residual -1.49e-11 m/s; stage-1 offload / screening 2.74361)
- silo_hot_ramp_s1: decomposition explained (residual -9.58e-12 m/s; stage-1 offload / screening 3.07235)
- silo_cold_200m_s1: decomposition explained (residual 5.2e-12 m/s; stage-1 offload / screening 2.75516)
- silo_cold_s1__vehicle.stages.stage1.dry_mass_t__+0.1: decomposition explained (residual 4.26e-11 m/s)
- silo_cold_s1__vehicle.stages.stage1.dry_mass_t__-0.1: decomposition explained (residual -3.52e-10 m/s)
- silo_cold_s1__vehicle.stages.stage1.engine.isp_vac_s__+0.1: decomposition explained (residual 1.54e-11 m/s)
- silo_cold_s1__vehicle.stages.stage1.engine.isp_vac_s__-0.1: decomposition explained (residual -2.29e-11 m/s)
- silo_cold_s1__vehicle.aero.cd_scale__+0.1: decomposition explained (residual -1e-11 m/s)
- silo_cold_s1__vehicle.aero.cd_scale__-0.1: decomposition explained (residual 8.85e-11 m/s)
- silo_cold_s1__assist.drive_efficiency__+0.1: decomposition explained (residual 4.52e-12 m/s)
- silo_cold_s1__assist.drive_efficiency__-0.1: decomposition explained (residual 4.52e-12 m/s)

No run and no comparison is bug_suspect.
