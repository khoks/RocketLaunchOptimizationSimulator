<!-- Copied unchanged from results/silo_offload_2d/20261003T112934Z/summary.md, lines 98 to 226 (the section 'Propellant saved at fixed payload' with its subsections), written by commit b3150c1 (clean tree). -->

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
