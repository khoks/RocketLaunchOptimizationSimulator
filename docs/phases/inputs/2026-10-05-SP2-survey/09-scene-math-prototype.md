Provenance: SP2 step A0 survey 09 of 9 (read-only agent report, 2026-10-05, line numbers checked at commit b69ff0c); below this header, a byte copy from the session scratchpad (a0/09-scene-math-prototype.md); a record, not edited (README.md).

# 09 - Scene math prototype (SP2 step A0, read-only survey)

HEAD b69ff0c. Data read, never written:

- `results/silo_screening_2d/20260930T175743Z` (scr): pad, silo_cold, silo_hot_ramp_on_track, silo_failed; also silo_cold_lag, silo_hot_full and silo_instant for the plume study.
- `results/silo_offload_2d/20261003T112934Z` (off): pad, silo_cold_s1, silo_cold_fix5pct, silo_cold_s1_dry+8.1t, pad__offload_stage1, pad__offload_both, silo_cold_s2.

Scratch scripts and their outputs are in this folder: `s09_common.py` (loaders), `s09_overview.py/.out`, `s09_tanks.py/.out`, `s09_separation.py/.out`, `s09_transform.py/.out`, `s09_camera.py` / `s09_camera_v2.out`, `s09_grid.py/.out` (first pass, superseded), `s09_grid2.py/.out`, `s09_plume.py/.out`, `s09_extra.py/.out`. Run as `uv run python <script>` from the repository root. No pytest was run. No repository file was touched.

Constants used (src/launchsim/constants.py): `MU_EARTH_M3S2 = 3.986004418e14` (line 7), `R_EARTH_M = 6_378_137.0` (line 10), `OMEGA_EARTH_RADS = 7.2921150e-5` (line 13), `G0_MPS2 = 9.80665` (line 16). Site of every run: latitude 28.5 deg, azimuth 90 deg, `include_rotation: true`, so omega_p = 6.408435e-05 rad/s (`config.py` 545-549).

## 0. Facts about the recorded files that the design depends on

| Fact | Evidence |
|---|---|
| CSV rows sit at multiples of `sample_dt_s` = 0.05 s on the absolute clock `t_s`, plus both ends of every integration segment (`metrics_planar.py` 539-541). For a silo run `t_rel_release_s = t_s - 2.607318179`, so its rows are NOT on round values of the release clock (first ramp row at t_rel 0.5427 s) | `s09_overview.out` |
| Duplicate times (two rows, same time) mark every segment boundary. They are not only phase changes: the ramp end inside KICK (t_rel 2.5 s), the hot-start ignition inside ASSIST (-2.0 s), the fairing drop inside LTG_BURN and the apex inside COAST (silo_failed, 7.8426 s) are duplicates with the same phase name on both sides | `s09_overview.out` |
| Rows per run: 10,779 (pad), 10,844 (silo_cold), 10,792 (silo_hot_ramp_on_track), 371 (silo_failed), 10,538 (silo_cold_s1), 10,691 (fix5pct), 10,829 (dry+8.1t), 8,624 (silo_cold_s2); 6 or 7 duplicate times per orbital run, 2 for silo_failed | same |
| Phase names present: HOLD, ASSIST, COAST_PRE_IGN (cold silo, release to ignition, 0.5 s), VERTICAL_RISE (pad only), KICK, GRAVITY_TURN, COAST_STAGING, LTG_BURN, COAST (silo_failed) | `phases/planar.py` 123-153 |
| `events.csv` is on the absolute clock `t_s`. Every event's `t_s` equals a time-series row's `t_s` exactly (0 unmatched over 12 runs), but `event t_s - t_release` differs from that row's `t_rel_release_s` by up to 5e-11 s (both columns are written to 12 significant digits) | `s09_grid2.out`, first block |
| The stage-1 `propellant` row carries the pre-drop mass and the `staging` row the post-drop mass; the `fairing` row (LTG_BURN) carries the pre-drop mass (event m - pre-drop CSV row = 0.0 kg on all 10 flights) | `s09_tanks.out` table 1c |
| `propellant` is not always MECO: `pad__offload_stage1/events.csv` line 10 is `536.30068678,propellant,LTG_BURN,stage2,...` (stage-2 depletion; that run has no `cutoff` row). Line 6 is the stage-1 one | file |
| All 28 flown runs of the two directories that have a `fairing_drop` metric say "in the stage-2 burn (heating event)"; silo_failed has None. The other three fairing cases of section 5.8 item 1 (at stage-2 ignition, at staging, rule `staging` with no row) do not occur in recorded data | `s09_explore3.py` |
| A run's startup shape can be overridden in the run block, not the vehicle block: `runs.silo_cold_lag.run.ignition.stage1.startup = {kind: lag, tau_s: 1.0}`, `runs.silo_instant...startup = {kind: step}` | `s09_plume.out` |

## 1. Tank levels

### 1.1 The algorithm that closes

Inputs: every row of `timeseries.csv` in file order (duplicates kept), `events.csv`, the run's vehicle block V (entry's `vehicle`, else the top-level block), the top-level block V0, the payload P (`metrics.json` `runs.<name>.payload_kg`, or `offload.runs.<name>.payload_kg`, or V's `payload_mass_t` when null).

Masses [kg] from V: d1, p1 (stage-1 dry and loaded propellant), d2, p2, f (fairing). From V0: p1_full = 410,900, p2_full = 107,500.

1. `fairing_on(row)`:
   - a `fairing` event with phase LTG_BURN at time t_f: on for rows with `t_s < t_f`; of the rows with `t_s == t_f` the first in file order is on (pre-drop), the rest off;
   - a `fairing` event with phase COAST_STAGING, or rule `staging` with no row: on exactly while `stage == stage1`;
   - no `fairing` event and another rule: on throughout.
2. Rows with `stage == stage1`: `prop2 = p2`; `prop1 = m_kg - P - d2 - f*fairing_on - p2 - d1`.
3. Rows with `stage == stage2`: `prop2 = m_kg - P - d2 - f*fairing_on`; `prop1` = its value on the last stage-1 row (the MECO residual, dropped with the stage).
4. `fill1 = prop1 / p1_full`, `fill2 = prop2 / p2_full`.

Checks that are not true by construction: (a) first row `prop1 == p1` (the liftoff identity); (b) `prop1` at the last stage-1 row is 0; (c) the mass step at the staging duplicate is -d1 (or -(d1+f)); (d) `prop2 == p2` on every COAST_STAGING row; (e) the mass step at the fairing duplicate is -f; (f) `prop2` at the last row equals `recorded_m_res_kg`; (g) an independent rebuild, with the burned propellant integrated from `thrust_vac_N/(g0 Isp_vac)` by the trapezoid rule over the rows of each stage, equals `m_kg`.

Mass burned before release needs no special case. The first row is the start of the hold (pad, t_rel -2.0 s, the ignition instant) or the push start (silo, -2.607 s) and carries `liftoff_mass_kg`; HOLD and ASSIST rows carry the falling `m_kg`, so `prop1` falls from ignition onward.

### 1.2 Results (`s09_tanks.out`)

| Run | Payload kg (source) | Liftoff identity error kg | max abs(rebuilt - m_kg), independent rebuild, kg | Staging step kg (expected) | Fairing step kg |
|---|---|---|---|---|---|
| scr/pad | 26,054.3962 (runs.payload_kg) | -4.9e-07 | 8.1e-07 | -22,200.0000 (-22,200) | -1,700.0000 |
| scr/silo_cold | 27,553.2271 | -1.9e-07 | 1.1e-06 | -22,200.0000 | -1,700.0000 |
| scr/silo_hot_ramp_on_track | 27,788.2010 | -3.0e-07 | 1.0e-06 | -22,200.0000 | -1,700.0000 |
| scr/silo_failed | 22,800.0000 (vehicle block, metric null) | 0 | 0 | none | none (kept) |
| off/pad | 26,054.3962 | -4.9e-07 | 8.1e-07 | -22,200.0000 | -1,700.0000 |
| off/silo_cold_s1 | 26,054.3962 (offload.runs) | -1.6e-07 | 9.9e-07 | -22,200.0000 | -1,700.0000 |
| off/silo_cold_fix5pct | 26,837.5588 (offload.runs) | +6.8e-08 | 7.0e-07 | -22,200.0000 | -1,700.0000 |
| off/silo_cold_s1_dry+8.1t | 26,054.3962 | +1.2e-07 | 5.7e-07 | -30,300.0000 (-30,300) | -1,700.0000 |
| off/pad__offload_stage1 | 26,054.3962 | -4.9e-07 | 8.1e-07 | -22,200.0000 | -1,700.0000 |
| off/pad__offload_both | 26,054.3962 | -4.9e-07 | 8.1e-07 | -22,200.0000 | -1,700.0000 |
| off/silo_cold_s2 | 26,054.3962 | +4.3e-07 | 1.8e-06 | -22,200.0000 | -1,700.0000 |

The errors are the CSV's 12 significant digits (1e-6 kg at 5.7e5 kg). The definition rebuild (steps 2-3 summed back) equals `m_kg` to 6e-11 kg.

| Run | p1 of the run kg | 1 - stage-1 offload fraction | fill1, first row | fill1 at release | t_MECO s after release | prop1 at MECO kg |
|---|---|---|---|---|---|---|
| scr/pad | 410,900.000 | 1.000000000 | 1.000000000 | 0.993435 | 151.328438 | -4.9e-07 |
| scr/silo_cold | 410,900.000 | 1.000000000 | 1.000000000 | 1.000000 | 153.828438 | -1.9e-07 |
| scr/silo_hot_ramp_on_track | 410,900.000 | 1.000000000 | 1.000000000 | 0.993435 | 151.328438 | -3.0e-07 |
| scr/silo_failed | 410,900.000 | 1.000000000 | 1.000000000 | 1.000000 | no MECO | stays 410,900 |
| off/silo_cold_s1 | 369,637.092 | 0.899579197 | 0.899579197 | 0.899579 | 138.531493 | -4.9e-07 |
| off/silo_cold_fix5pct | 390,355.000 | 0.950000000 | 0.950000000 | 0.950000 | 146.212016 | +6.8e-08 |
| off/silo_cold_s1_dry+8.1t | 408,919.523 | 0.995180149 | 0.995180149 | 0.995180 | 153.094237 | -4.9e-07 |
| off/pad__offload_stage1 | 410,900.000 | 1.000000000 | 1.000000000 | 0.993435 | 151.328438 | -4.9e-07 |
| off/pad__offload_both | 410,900.000 | 1.000000000 | 1.000000000 | 0.993435 | 151.328438 | -4.9e-07 |
| off/silo_cold_s2 | 410,900.000 | 1.000000000 | 1.000000000 | 1.000000 | 153.828438 | +4.3e-07 |

fill1 at the first row equals 1 minus the offload fraction to 1.2e-12. Propellant burned before release, from the rebuilt tank: 2,697.4609 kg on the pad (metric `hold_propellant_burned_kg` 2,697.4608722) and on silo_hot_ramp_on_track (metric `propellant_burned_on_track_kg` 2,697.4608722); 0 on the cold silo runs.

| Run | p2 of the run kg | fill2, first row | max abs(prop2 - p2) over the 222 staging-coast rows kg | prop2 at the last row kg | fill2 at the last row | `recorded_m_res_kg` |
|---|---|---|---|---|---|---|
| scr/pad | 107,500.000 | 1.000000000 | 5.0e-07 | 0.000466 | 4.3e-09 | 0.000466 |
| scr/silo_cold | 107,500.000 | 1.000000000 | 1.9e-07 | 0.000490 | 4.6e-09 | 0.000490 |
| scr/silo_hot_ramp_on_track | 107,500.000 | 1.000000000 | 3.0e-07 | 0.000485 | 4.5e-09 | 0.000485 |
| off/silo_cold_s1 | 107,500.000 | 1.000000000 | 5.0e-07 | 0.000034 | 3.2e-10 | 0.0000342 |
| off/silo_cold_fix5pct | 107,500.000 | 1.000000000 | 6.8e-08 | 0.000463 | 4.3e-09 | 0.000463 |
| off/silo_cold_s1_dry+8.1t | 107,500.000 | 1.000000000 | 5.0e-07 | 0.000028 | 2.6e-10 | 0.0000275 |
| off/pad__offload_stage1 | 107,500.000 | 1.000000000 | 5.0e-07 | 0.000000 | 4.7e-14 | -0.001638 (virtual; the run ends on stage-2 depletion) |
| off/pad__offload_both | 107,500.000 | 1.000000000 | 5.0e-07 | 0.000573 | 5.3e-09 | 0.000573 |
| off/silo_cold_s2 | 75,595.729 | 0.703216087 | 4.3e-07 | 0.000560 | 5.2e-09 | 0.000560 |

Note: the fixed case silo_cold_fix5pct has `residual_propellant_kg` = 3,985.46 in its metrics (a figure at the reference payload), while its recorded run ends empty; the cross-check key is `recorded_m_res_kg`.

### 1.3 Is 1 kg achievable on an interpolated grid?

Yes, under four conditions (numbers in section 5):

1. The stack mass is never interpolated across a drop. Interpolating `m_kg` itself on a keep-last grid is wrong by up to 20,280 kg (pad) to 29,800 kg (dry+8.1t) on 30 to 52 rows before staging and before the fairing drop. Either send two continuous tank series (`prop1`, `prop2`) and rebuild `m = P + d2 + f*fairing_on + prop2 + stage1_on*(d1 + prop1)` with flags that switch at the event times, or keep both rows of every duplicate time.
2. The startup ramp needs CSV-row density. On a 0.1 s step the 2 s linear ramp gives 1.686 kg (= mdot_full dt^2 / (8 t_ramp), mdot_full = 2,697.46 kg/s) on 20 rows, 1.86 kg when the samples are themselves interpolated at round release-clock times, and 2.9 to 3.3 kg on the lag startup (tau = 1 s). With every CSV row of the ramp in the grid (20 more samples) the error is 1e-6 kg (ramp) and 0.48 kg (lag).
3. Sample times carry at least 4 decimals. 1 kg is 0.37 ms of stage-1 burn. With the replay's `REPLAY_TIME_DECIMALS = 3` (replay.py 77) the error reaches 1.08 kg (pad), 1.91 kg (hot start), 2.09 kg (silo_cold_s1) on 1 to 24 rows; with 4 decimals 0.09 to 0.52 kg and no row out; with 6 decimals 0.001 to 0.48 kg.
4. Tank masses carry 0.1 kg. The replay's rounding (tonnes, 3 decimals = 1 kg, replay.py 124) leaves 0.50 to 0.94 kg of the 1 kg budget used by rounding alone.

## 2. Separation states and the ballistic coast

### 2.1 Rebuilt state against the row's inertial speed (`s09_separation.out`)

State as section 5.5 writes it: r = R_E + alt, v_r = V_rel sin(gamma_rel), u = V_rel cos(gamma_rel), v_theta = u + omega_p r.

| Run | Staging t_rel s | alt km | downrange km | V_rel m/s | gamma_rel deg | hypot(v_r, v_theta) m/s | row `speed_inertial_mps` | difference m/s |
|---|---|---|---|---|---|---|---|---|
| scr/pad | 151.328 | 69.486 | 99.171 | 2,665.032 | 22.9891 | 3,049.679962 | 3,049.679962 | +5.7e-09 |
| scr/silo_cold | 153.828 | 75.202 | 110.155 | 2,765.925 | 21.6465 | 3,154.009133 | 3,154.009133 | -8.9e-09 |
| scr/silo_hot_ramp_on_track | 151.328 | 75.957 | 111.948 | 2,781.542 | 21.4550 | 3,170.099859 | 3,170.099859 | +1.9e-09 |
| off/silo_cold_s1 | 138.531 | 69.300 | 99.243 | 2,665.476 | 22.9864 | 3,050.118908 | 3,050.118908 | +2.7e-09 |
| off/silo_cold_fix5pct | 146.212 | 72.357 | 104.897 | 2,718.521 | 22.2843 | 3,104.982206 | 3,104.982206 | +3.8e-09 |
| off/silo_cold_s1_dry+8.1t | 153.094 | 74.336 | 104.263 | 2,657.831 | 22.5418 | 3,043.872179 | 3,043.872179 | +6.9e-09 |
| off/pad__offload_stage1 | 151.328 | 69.491 | 99.166 | 2,664.989 | 22.9929 | 3,049.628023 | 3,049.628023 | +5.6e-10 |
| off/pad__offload_both | 151.328 | 69.491 | 99.166 | 2,664.989 | 22.9929 | 3,049.628022 | 3,049.628022 | -4.1e-09 |
| off/silo_cold_s2 | 153.828 | 76.823 | 141.100 | 3,373.382 | 17.4885 | 3,769.973826 | 3,769.973826 | -8.9e-10 |

The fairing rows close the same way (differences 3e-11 to 8e-09 m/s). silo_failed has neither event. The phase file's "about 3049 against 3049.68" is the same check at lower precision; it holds to 1e-8 m/s, so a test tolerance of 1e-6 m/s is safe.

### 2.2 Spent stage 1, vacuum two-body coast to r = R_E

Integration: the CLAUDE.md planar polar equations with no thrust and no drag, state [r, theta, v_r, v_theta], DOP853, rtol 1e-12, terminal event r = R_E. Downrange at impact is Earth-fixed: downrange_0 + R_E (delta theta - omega_p tof).

| Run | Time of flight s | Impact t_rel s | Run ends t_rel s | Apex altitude km | Apex after s | Downrange at impact km (Earth-fixed) | Inertial arc km | Impact V_rel m/s | Energy drift (relative) | h drift (relative) | RHS calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| scr/pad | 308.27 | 459.60 | 536.30 | 135.254 | 126.77 | 839.24 | 965.24 | 2,906.2 | 1.7e-13 | 2.1e-13 | 149 |
| scr/silo_cold | 311.59 | 465.41 | 538.80 | 139.325 | 126.08 | 894.06 | 1,021.41 | 3,017.1 | 1.6e-13 | 2.2e-13 | 149 |
| scr/silo_hot_ramp_on_track | 312.07 | 463.40 | 536.30 | 139.860 | 126.00 | 902.55 | 1,030.10 | 3,033.8 | 1.6e-13 | 2.2e-13 | 149 |
| off/silo_cold_s1 | 308.15 | 446.68 | 523.50 | 135.075 | 126.78 | 839.18 | 965.13 | 2,906.0 | 1.6e-13 | 2.0e-13 | 149 |
| off/silo_cold_fix5pct | 310.08 | 456.29 | 531.18 | 137.361 | 126.50 | 868.17 | 994.91 | 2,964.6 | 1.3e-13 | 1.9e-13 | 149 |
| off/silo_cold_s1_dry+8.1t | 307.31 | 460.40 | 538.07 | 137.449 | 124.26 | 842.67 | 968.27 | 2,915.5 | 1.7e-13 | 2.1e-13 | 149 |
| off/pad__offload_stage1 | 308.30 | 459.63 | 536.30 | 135.277 | 126.79 | 839.27 | 965.28 | 2,906.1 | 2.0e-13 | 2.5e-13 | 149 |
| off/pad__offload_both | 308.30 | 459.63 | 536.30 | 135.277 | 126.79 | 839.27 | 965.28 | 2,906.1 | 1.6e-13 | 2.0e-13 | 149 |
| off/silo_cold_s2 | 334.41 | 488.24 | 427.81 | 145.749 | 136.40 | 1,192.97 | 1,329.65 | 3,586.5 | 7.9e-14 | 2.3e-13 | 149 |

In silo_cold_s2 the run ends 60 s before the spent stage lands: at the last sample it is at 75.62 km altitude and 998.37 km downrange.

### 2.3 Fairing halves, same coast from the `fairing` row

| Run | Drop t_rel s | alt km | downrange km | V_rel m/s | gamma_rel deg | Time of flight s | Impact t_rel s | Apex altitude km | Apex after s | Downrange at impact km | Impact V_rel m/s | Energy drift | h drift |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| scr/pad | 196.808 | 110.483 | 212.324 | 2,766.553 | 16.7050 | 293.80 | 490.61 | 150.133 | 99.90 | 977.08 | 3,126.7 | 1.6e-13 | 2.9e-13 |
| scr/silo_cold | 193.816 | 110.993 | 213.627 | 2,847.373 | 16.3184 | 297.35 | 491.17 | 151.536 | 101.54 | 1,011.61 | 3,199.9 | 1.5e-13 | 2.9e-13 |
| scr/silo_hot_ramp_on_track | 190.609 | 111.075 | 214.202 | 2,860.453 | 16.2512 | 297.87 | 488.48 | 151.732 | 101.77 | 1,017.51 | 3,211.8 | 1.6e-13 | 3.0e-13 |
| off/silo_cold_s1 | 184.250 | 110.493 | 213.043 | 2,768.089 | 16.6772 | 293.69 | 477.94 | 150.066 | 99.82 | 978.07 | 3,128.1 | 1.5e-13 | 2.8e-13 |
| off/silo_cold_fix5pct | 188.953 | 110.760 | 213.504 | 2,810.151 | 16.4936 | 295.70 | 484.65 | 150.888 | 100.78 | 996.09 | 3,166.2 | 1.6e-13 | 3.0e-13 |
| off/silo_cold_s1_dry+8.1t | 193.399 | 110.299 | 204.005 | 2,737.983 | 16.9278 | 293.26 | 486.66 | 150.003 | 99.79 | 958.58 | 3,100.9 | 1.6e-13 | 2.9e-13 |
| off/pad__offload_stage1 | 196.793 | 110.482 | 212.275 | 2,766.428 | 16.7095 | 293.83 | 490.62 | 150.148 | 99.92 | 977.05 | 3,126.6 | 1.6e-13 | 2.9e-13 |
| off/pad__offload_both | 196.793 | 110.482 | 212.275 | 2,766.428 | 16.7095 | 293.83 | 490.62 | 150.148 | 99.92 | 977.05 | 3,126.6 | 1.6e-13 | 2.9e-13 |
| off/silo_cold_s2 | 196.756 | 115.012 | 281.099 | 3,571.945 | 12.8138 | 324.40 | 521.16 | 159.379 | 112.22 | 1,389.38 | 3,868.7 | 1.4e-13 | 3.5e-13 |

In silo_cold_s2 the fairing is at 109.62 km and 1,063.86 km downrange when the run ends.

### 2.4 How far the bodies drift from the vehicle (`s09_extra.out`)

| Body | +1 s | +5 s | +11 s | +20 s | +30 s | +60 s | +120 s |
|---|---|---|---|---|---|---|---|
| Spent stage 1, scr/pad | 0.0 m | 0.1 m | 0.2 m | 284 m | 1,274 m | 8,647 m | 44,895 m |
| Spent stage 1, scr/silo_cold | 0.0 m | 0.0 m | 0.1 m | 281 m | 1,259 m | 8,555 m | 44,384 m |
| Fairing, scr/pad | 3.8 m | 95 m | 462 m | 1,538 m | 3,484 m | 14,246 m | 59,839 m |
| Fairing, scr/silo_cold | 3.7 m | 93 m | 451 m | 1,501 m | 3,400 m | 13,892 m | 58,270 m |

For the whole 11 s staging coast the vacuum-coasting stage and the vehicle (which coasts unpowered with negligible drag at 70 to 86 km) are the same point to 0.2 m. At the camera scale of that time (about 360 to 440 m per px, section 4) the gap is below 1 px until about 20 s after staging and 3 px at 30 s.

### 2.5 Closed form against numerical integration

Closed form: h = r0 v_theta0, E = v^2/2 - mu/r0, p = h^2/mu, e = sqrt(1 + 2 E h^2/mu^2), a = -mu/(2E); true anomaly from e cos f0 = p/r0 - 1, e sin f0 = v_r0 h/mu; impact on the descending branch f_imp = 2 pi - acos((p/R_E - 1)/e); times from the eccentric anomaly. Sampling at uniformly spaced true anomaly gives (t, r, theta) with no Kepler-equation solve.

| Quantity | Closed form minus numeric, all 9 flights, both bodies |
|---|---|
| Time of flight | at most 7.4e-10 s |
| Apex altitude | at most 2.4e-07 m |
| Downrange at impact | at most 3.3e-06 m |
| 200 true-anomaly samples against the dense numeric solution | radius at most 1.4e-06 m, arc at most 4.4e-06 m |
| Orbit of the spent stage | e = 0.754 to 0.868, perigee altitude -5,461 to -5,920 km |

Which is simpler as a pure, tested function: the numerical coast. It is one code path (a 4-state right-hand side of five lines, `solve_ivp` DOP853 with a terminal event at r = R_E and a time limit) for every state, including the ones the closed form needs branches for: no impact inside the time limit, a near-radial state (h near 0, p near 0, which a run with `include_rotation: false` and a vertical failure would give), e at or above 1. It costs 134 to 149 right-hand-side calls per body. Its test is the one the phase file asks for (energy and angular-momentum drift, measured here at 3.5e-13 relative or better) plus the closed-form time of flight, apex and impact arc as the oracle, which agree to 1e-9 s and 1e-5 m. The closed form is exact and needs no tolerance, but it is about 35 lines with three guarded branches, and its own test would need the integrator anyway. Keep the right-hand side in the scene module, not in `dynamics.py`, so the validated physics core is not touched.

## 3. Earth-fixed drawing transform

x = (R_E + alt) sin(downrange/R_E), y = (R_E + alt) cos(downrange/R_E) - R_E.

### 3.1 Sign of the drawn attitude

Local up at the point is (sin phi, cos phi) and local horizontal toward increasing downrange is (cos phi, -sin phi), with phi = downrange/R_E. A direction at pitch above local horizontal is therefore (cos(pitch - phi), sin(pitch - phi)): the screen angle, counter-clockwise from +x with y up, is **pitch minus downrange/R_E**. On a canvas whose y axis points down the rotation passed to the canvas is the negative of that.

Numeric check (`s09_transform.out`, block 3b): the direction of the drawn path, from central differences of (x, y), against gamma_rel - downrange/R_E and, where thrust is along v_rel, against pitch - downrange/R_E.

| Phase | Rows | max abs(path tangent - (gamma_rel - phi)) deg | max abs(path tangent - (pitch - phi)) deg | With the wrong sign (pitch + phi) deg |
|---|---|---|---|---|
| GRAVITY_TURN (10 flights) | 2,609 to 2,915 | 1.9e-05 to 3.0e-05 | 0.0000 | 1.78 to 2.53 |
| COAST_STAGING | 218 | 8e-08 to 1.2e-07 | 0.0000 | 2.26 to 3.16 |
| COAST (silo_failed) | 290 | 5.6e-06 | 0.0000 | 0.000 (downrange about 0) |
| LTG_BURN | 5,256 to 7,476 | 2.7e-07 to 4.4e-07 | 5.04 to 15.46 (thrust is not along the velocity) | 20.3 to 32.8 |

### 3.2 Positions at the events (state of the last row at the event time)

scr/pad:

| Event | t_rel s | alt m | downrange m | x m | y m | x - downrange m | y - alt m | pitch deg | downrange/R_E deg | screen angle deg |
|---|---|---|---|---|---|---|---|---|---|---|
| ignition (stage 1) | -2.0000 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 90.0000 | 0.00000 | 90.0000 |
| release | 0.0000 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 90.0000 | 0.00000 | 90.0000 |
| kick_start | 12.4937 | 301.049 | -0.158 | -0.158 | 301.049 | 0.000 | 0.000 | 87.1657 | 0.00000 | 87.1657 |
| kick_end | 17.7740 | 628.767 | 9.438 | 9.439 | 628.767 | +0.001 | 0.000 | 87.1657 | 0.00008 | 87.1656 |
| propellant, staging | 151.3284 | 69,485.8 | 99,171.0 | 100,247.4 | 68,706.5 | +1,076.4 | -779.4 | 22.9891 | 0.89087 | 22.0983 |
| ignition (stage 2) | 162.3284 | 80,432.6 | 125,813.4 | 127,391.7 | 79,176.1 | +1,578.3 | -1,256.5 | 31.3912 | 1.13020 | 30.2610 |
| fairing | 196.8075 | 110,483.0 | 212,323.8 | 215,961.8 | 106,888.1 | +3,638.0 | -3,594.9 | 29.0905 | 1.90734 | 27.1832 |
| cutoff, end | 536.3007 | 199,999.98 | 1,660,290.9 | 1,693,079.7 | -21,615.4 | +32,788.9 | -221,615.4 | 1.5167 | 14.91465 | -13.3979 |

scr/silo_cold:

| Event | t_rel s | alt m | downrange m | x m | y m | pitch deg | downrange/R_E deg | screen angle deg |
|---|---|---|---|---|---|---|---|---|
| push_start | -2.6073 | -100.0 | 0.0 | 0.0 | -100.0 | 90.0000 | 0.00000 | 90.0000 |
| release | 0.0000 | 0.0 | 0.0 | 0.0 | 0.0 | 90.0000 | 0.00000 | 90.0000 |
| ignition, kick_start | 0.5000 | 37.129 | -0.001 | -0.001 | 37.129 | 87.6385 | 0.00000 | 87.6385 |
| ramp_end | 2.5000 | 168.740 | 0.285 | 0.285 | 168.740 | 87.6385 | 0.00000 | 87.6385 |
| kick_end | 8.0256 | 581.277 | 11.295 | 11.296 | 581.277 | 87.6385 | 0.00010 | 87.6384 |
| propellant, staging | 153.8284 | 75,202.2 | 110,154.8 | 111,448.1 | 74,239.8 | 21.6465 | 0.98954 | 20.6570 |
| ignition (stage 2) | 164.8284 | 85,930.4 | 138,050.0 | 139,899.0 | 84,416.3 | 30.6322 | 1.24012 | 29.3921 |
| fairing | 193.8165 | 110,993.4 | 213,627.5 | 217,304.4 | 107,353.9 | 28.7630 | 1.91905 | 26.8440 |
| cutoff, end | 538.8007 | 199,999.98 | 1,705,290.2 | 1,737,884.1 | -33,718.6 | 1.9635 | 15.31888 | -13.3554 |

scr/silo_failed: push_start (-2.6073 s, alt -100 m, 90 deg); release and ignition_failed (0 s, 0 m, 90 deg); apex (7.8426 s, 300.647 m, downrange -0.201 m, pitch 180 deg); impact and end (15.6891 s, 0 m, downrange -0.403 m, pitch 270 deg = -90 deg wrapped).

off/silo_cold_s1: release 0 s; ignition and kick_start 0.5 s (37.129 m, pitch 85.8725 deg); ramp_end 2.5 s (169.331 m); kick_end 7.9483 s (596.461 m); propellant and staging 138.5315 s (69,300.1 m, 99,243.2 m, screen 22.0949 deg); stage-2 ignition 149.5315 s (80,247.5 m, screen 30.2995 deg); fairing 184.2505 s (110,492.9 m); cutoff 523.5037 s (199,999.999 m, 1,660,430.9 m, x 1,693,219.3 m, y -21,652.5 m, pitch 1.4888 deg, screen -13.4271 deg).

Screen y is not altitude. At cutoff the pad run is at y = -21.6 km while its altitude is 200 km; the ground under it is at y = -214.9 km. The largest y of the pad run is 151.1 km at 320.4 s. The HUD altitude must come from `alt_m`.

### 3.3 Range of pitch_rad and where it jumps

| Run | pitch_rad as written (deg) | wrapped (deg) | screen angle (deg) |
|---|---|---|---|
| scr/pad, off/pad | 1.517 to 90.000 | same | -13.398 to 90.000 |
| scr/silo_cold | 1.964 to 90.004 | same | -13.355 to 90.004 |
| scr/silo_hot_ramp_on_track | 2.022 to 90.000 | same | -13.359 to 90.000 |
| scr/silo_failed | 90.000 to 270.000 (unwrapped) | -180.000 to 94.509 | same |
| off/silo_cold_s1 | 1.489 to 90.004 | same | -13.427 to 90.004 |
| off/silo_cold_fix5pct | 1.749 to 90.004 | same | -13.379 to 90.004 |
| off/silo_cold_s1_dry+8.1t | 1.696 to 90.004 | same | -13.264 to 90.004 |
| off/pad__offload_stage1, _both | 1.521 to 90.000 | same | -13.393 to 90.000 |
| off/silo_cold_s2 | -5.044 to 90.004 | same | -17.720 to 90.004 |

Steps (two rows at one time):

| Where | Size |
|---|---|
| Kick start: pad VERTICAL_RISE to KICK at 12.4937 s | -2.8343 deg (off pad controls -2.8341) |
| Kick start: cold silo COAST_PRE_IGN to KICK at 0.5 s | -2.3653 (silo_cold), -4.1313 (silo_cold_s1), -3.1584 (fix5pct), -2.1828 (dry+8.1t), -3.9863 (silo_cold_s2) |
| Kick start: hot silo ASSIST to KICK at 0 s | -3.6571 deg |
| Stage-2 ignition, COAST_STAGING to LTG_BURN | +10.1893 (pad), +10.6980 (silo_cold), +10.7709 (hot), +10.2310 (silo_cold_s1), +10.4364 (fix5pct), +10.9077 (dry+8.1t), +3.2866 (silo_cold_s2) |
| Kick end, MECO, fairing drop | 0.0000 deg (continuous) |

Smooth rates: 0 during HOLD, ASSIST, VERTICAL_RISE and KICK (the kick holds its angle); at most 0.69 to 0.77 deg/s in GRAVITY_TURN (near 37 to 50 s); 0.12 to 0.17 deg/s in COAST_STAGING; at most 0.10 deg/s in LTG_BURN; 0.008 deg/s in COAST_PRE_IGN.

silo_failed, unpowered, pitch along v_rel: consecutive CSV rows 0.05 s apart differ by +0.75, +2.25, **+85.49, +85.01**, +2.25, +0.75 deg around the apex (7.6927 to 7.9927 s). The true sweep is faster than the rows show: with 0.0385 m/s of horizontal relative speed at the apex the angle turns through 90 deg in about 4 ms each side.

## 4. Camera

### 4.1 Extents (altitude m ; downrange m), time after release

| Run | first row | 0 s | 5 s | 12 s | 30 s | 60 s | 100 s | 162 s | 300 s | end |
|---|---|---|---|---|---|---|---|---|---|---|
| scr/pad | 0 ; 0 (-2.0 s) | 0 ; 0 | 46.1 ; 0.0 | 276.9 ; -0.1 | 1,926 ; 144 | 8,977 ; 2,833 | 27,949 ; 21,252 | 80,120 ; 125,019 | 171,343 ; 516,640 | 200,000 ; 1,660,291 (536.30 s) |
| scr/silo_cold | -100 ; 0 (-2.607 s) | 0 ; 0 | 341.3 ; 3.2 | 951.6 ; 30.4 | 3,533 ; 389 | 11,889 ; 4,006 | 31,857 ; 24,348 | 83,266 ; 130,888 | 173,300 ; 535,507 | 200,000 ; 1,705,290 (538.80 s) |
| scr/silo_hot_ramp_on_track | -100 ; 0 | 0 ; 0 | 428.6 ; 10.6 | 1,192.6 ; 62.5 | 4,201 ; 586 | 13,305 ; 4,970 | 34,157 ; 27,472 | 86,349 ; 139,197 | 174,638 ; 548,397 | 200,000 ; 1,712,237 (536.30 s) |
| scr/silo_failed | -100 ; 0 | 0 ; 0 | 261.2 ; -0.1 | 216.2 ; -0.3 | - | - | - | - | - | 0 ; -0.4 (15.69 s) |
| off/silo_cold_s1 | -100 ; 0 | 0 ; 0 | 347.6 ; 6.1 | 1,010.3 ; 57.9 | 3,979 ; 696 | 13,631 ; 6,213 | 36,192 ; 33,507 | 91,731 ; 156,441 | 176,061 ; 560,231 | 200,000 ; 1,660,431 (523.50 s) |
| off/silo_cold_fix5pct | -100 ; 0 | 0 ; 0 | 344.3 ; 4.5 | 979.8 ; 42.4 | 3,748 ; 526 | 12,742 ; 5,027 | 33,961 ; 28,679 | 87,647 ; 144,124 | 174,800 ; 548,579 | 200,000 ; 1,684,059 (531.18 s) |
| off/silo_cold_s1_dry+8.1t | -100 ; 0 | 0 ; 0 | 340.7 ; 2.9 | 945.7 ; 27.7 | 3,488 ; 357 | 11,721 ; 3,749 | 31,568 ; 23,176 | 83,081 ; 125,838 | 172,706 ; 515,849 | 200,000 ; 1,665,391 (538.07 s) |
| off/silo_cold_s2 | -100 ; 0 | 0 ; 0 | 346.1 ; 5.8 | 996.5 ; 54.9 | 3,870 ; 669 | 13,089 ; 6,115 | 33,875 ; 33,343 | 84,856 ; 167,042 | 175,695 ; 687,751 | 200,000 ; 1,411,120 (427.81 s) |

off/pad, pad__offload_stage1 and pad__offload_both follow scr/pad to within 20 m. Downrange first exceeds altitude at 101 to 122 s. Peak altitude is 200.4 to 200.8 km at 467 to 479 s (the path overshoots the 200 km target by under 1 km before cutoff). The most negative downrange is -0.159 m (pad, before the kick) and -0.403 m (silo_failed).

### 4.2 Proposed law (display-only, a pure function of the scene time)

    E(t) = running max over [first row, t] of hypot( max(alt, 0) - alt_floor + L_rocket , downrange / aspect )
    H(t) = sqrt( H0^2 + (k E(t))^2 )          view height in metres

with alt_floor = min(0, lowest altitude of the run) (-100 m for the shipped silo, 0 for the pad), L_rocket = 70 m, aspect = panel width / height, H0 = 150 m, k = 1.25. The square root of the sum of squares is a smooth maximum, so the floor blends into the growth without a corner, which is the smoothing in log scale. E is a running maximum, so H never shrinks (silo_failed stays zoomed out after its apex). Because H depends only on the scene time, scrubbing gives the same view as playing; a filter in wall-clock time would not. Two panels on one zoom level take the larger H.

View height H in metres, aspect 1.0 (`s09_camera_v2.out`):

| Run | first row | 0 s | 5 s | 12 s | 30 s | 60 s | 100 s | 162 s | 300 s | cutoff or end | m per px at the end (520 px) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| scr/pad | 173.7 | 173.7 | 208.7 | 458.8 | 2,505.9 | 11,851 | 43,959 | 185,659 | 680,418 | 2,090.4 km | 4,020 |
| scr/silo_cold | 260.1 | 260.1 | 656.5 | 1,410.5 | 4,656.1 | 15,884 | 50,290 | 194,025 | 703,629 | 2,146.2 km | 4,127 |
| scr/silo_hot_ramp_on_track | 260.1 | 260.1 | 763.3 | 1,711.6 | 5,515.2 | 17,954 | 54,959 | 204,868 | 719,480 | 2,154.9 km | 4,144 |
| scr/silo_failed | 260.1 | 260.1 | 559.4 | 607.1 | - | - | - | - | - | 0.61 km | 1.2 |
| off/silo_cold_s1 | 260.1 | 260.1 | 664.2 | 1,484.8 | 5,261.4 | 18,920 | 61,808 | 226,797 | 734,120 | 2,090.6 km | 4,020 |
| off/silo_cold_fix5pct | 260.1 | 260.1 | 660.2 | 1,446.0 | 4,944.1 | 17,321 | 55,726 | 210,963 | 719,758 | 2,119.9 km | 4,077 |
| off/silo_cold_s1_dry+8.1t | 260.1 | 260.1 | 655.7 | 1,403.1 | 4,596.5 | 15,586 | 49,124 | 188,605 | 680,058 | 2,096.7 km | 4,032 |
| off/silo_cold_s2 | 260.1 | 260.1 | 662.4 | 1,467.4 | 5,121.4 | 18,252 | 59,567 | 234,296 | 887,350 | 1,781.6 km | 3,426 |
| pad + silo_cold, shared | 260.1 | 260.1 | 656.5 | 1,410.5 | 4,656.1 | 15,884 | 50,290 | 194,025 | 703,629 | 2,146.2 km | - |
| pad + silo_cold_s1, shared | 260.1 | 260.1 | 664.2 | 1,484.8 | 5,261.4 | 18,920 | 61,808 | 226,797 | 734,120 | 2,090.6 km | - |
| pad + silo_failed, shared | 260.1 | 260.1 | 559.4 | 607.1 | 2,505.9 | 11,851 | 43,959 | 185,659 | 680,418 | 2,090.4 km | - |

With aspect 1.5 the early values are the same and the late ones shrink: 144,574 m at 162 s, 480,905 m at 300 s and 1,406.0 km at cutoff for the pad.

The bounding box of the path so far (launch site, shaft floor, rocket top, ground under the vehicle) stays inside 0.81 of the view at all times (0.775 for silo_failed), so about 10% margin each side.

### 4.3 Thresholds

| Question | Answer |
|---|---|
| A 70 m rocket is under 6 px on a 520 px panel when | H > 6,066.7 m |
| Time of that switch, one run alone | pad 45.0 s (altitude 4,710 m); silo_cold 35.4 s; silo_hot_ramp_on_track 32.0 s; silo_cold_s1 32.7 s; fix5pct 34.0 s; dry+8.1t 35.7 s; silo_cold_s2 33.3 s; silo_failed never (H peaks at 607 m, the rocket is 60 px) |
| Time of that switch, shared zoom | pad + silo_cold 35.4 s; pad + silo_cold_s1 32.7 s; pad + silo_failed 45.0 s |
| Earth's limb drops more than 3 px across the view width, launch site at the view edge (W^2 / 2 R_E) | H = 73.6 km (aspect 1): 107 to 120 s. H = 32.7 km (aspect 1.5): 80 to 93 s |
| Sagitta of the ground chord across the view exceeds 3 px (W^2 / 8 R_E) | H = 294.4 km (aspect 1): 177 to 195 s. H = 130.9 km (aspect 1.5): 143 to 156 s |
| Fastest zoom in scene time | d ln H / dt = 0.30 per s at release (silo), 0.125 per s at 10.7 s (pad) |
| Fastest zoom per wall second under the Auto rate (1x to 12 s, 5x to 45 s, 30x after) | a factor 3.2 to 4.5 per second at 45 s, where the rate steps to 30x |

At the end the whole flight is about 1,700 km wide and 200 km high: the 200 km altitude is 50 px and the spent stage's 135 km apex 34 px. That is the true proportion.

## 5. Time grid

`replay.replay_grid` (replay.py 394-402): the first time, 0.1 s steps to 40 s after release, 1 s steps after, the last time; `read_series` (365-377) keeps the last of duplicate times; times are written to 3 decimals (77).

Tolerances of exit criterion 5 applied at every CSV row: altitude max(0.5%, 1 m); downrange max(0.5%, 10 m); attitude 0.5 deg; plume fraction 0.02; mass 1 kg (criterion 6).

Variants (`s09_grid2.out`, `s09_extra.out`):

- A0: the replay grid, keep-last, linear.
- A: A0 plus every event time (the phase file's proposal for continuous fields).
- B: A plus both rows of every duplicate time (left and right value), piecewise-linear.
- E: B plus CSV rows inserted until every row is within half of each tolerance.
- F: a subset of the CSV rows with no resampling (both rows of every duplicate time, every event row, every 2nd row to 40 s after release, every 20th after), then the same insertion.

Samples per run:

| Run | A0 | A | B | E | F before insertion | F |
|---|---|---|---|---|---|---|
| scr/pad, off/pad | 918 | 924 | 930 | 950 | 928 | 948 |
| scr/silo_cold | 927 | 933 | 940 | 960 | 940 | 960 |
| scr/silo_hot_ramp_on_track | 925 | 931 | 937 | 957 | 935 | 955 |
| scr/silo_failed | 185 | 188 | 190 | 195 | 188 | 191 |
| off/silo_cold_s1 | 912 | 918 | 925 | 945 | 924 | 944 |
| off/silo_cold_fix5pct | 920 | 926 | 933 | 953 | 932 | 952 |
| off/silo_cold_s1_dry+8.1t | 927 | 933 | 940 | 960 | 940 | 960 |
| off/pad__offload_stage1, _both | 918 | 924 | 930 | 950 | 928 | 948 |
| off/silo_cold_s2 | 816 | 822 | 829 | 849 | 827 | 847 |
| scr/silo_cold_lag | 927 | 933 | 939 | 964 | 938 | 957 |

Largest error against the CSV rows, where it occurs, and the number of rows outside tolerance:

| Field | A0 | A | B | E and F |
|---|---|---|---|---|
| Altitude | 1.42 m at 150.5 s; 0 rows out (at most 4.3% of tolerance) | same | same | same |
| Downrange | 5.6 m at 150.5 s (7.15 m on silo_cold_s2); 0 rows out (at most 10% of tolerance) | same | same | same |
| Pitch | 3.7 to 9.9 deg at the kick and at stage-2 ignition; 17 to 21 rows out. silo_failed 11.4 deg at 7.79 s, 6 rows | 3.7 to 10.7 deg; 4 to 18 rows out. silo_failed 11.4 deg, 4 rows | 0.0011 deg; 0 rows out. silo_failed 11.4 deg, 4 rows | 0.0011 deg; silo_failed 0.097 deg (E), 0.075 deg (F); 0 rows out |
| Plume fraction, linear | 0.49 to 0.91 at MECO; 40 rows out | 0.89 to 0.98; 4 to 32 rows out | 2e-12 (ramp), 0.0012 (lag); 0 rows out | 0.0002 at most; 0 rows out |
| Plume fraction, last sample at or before | - | 0.025 (pad) to 0.046 (silo) inside the 2 s ramp; 20 to 40 rows out | same in the ramp | not used |
| `m_kg` interpolated directly | 11,100 to 27,700 kg; 79 to 83 rows out | 19,800 to 29,800 kg; 30 to 52 rows out | 1.69 kg (pad), 1.86 kg (silo), 3.31 kg (lag), in the startup; 16 to 20 rows out | 1e-6 kg (pad), 0.43 kg (silo, E), 0.48 kg (lag); 0 rows out |
| Stack mass rebuilt from two tank series and step flags | 226 to 623 kg at MECO (MECO is not a sample); 42 to 57 rows out | 1.69 to 1.86 kg in the ramp, 3.31 kg (lag); 16 to 20 rows out | same as A | same as the row above |

What the insertion adds: 20 rows inside the 2 s ramp (25 for the lag under E, 19 under F), 5 rows (E) or 3 rows (F) around the apex of silo_failed. E needs up to 11 passes on the silo runs because its samples are themselves interpolated at round release-clock times; F needs one pass on every run.

Time stamps and value rounding, variant E:

| Setting | Result |
|---|---|
| Sample and query times to 3 decimals | mass error 1.08 kg (pad, 1 row), 1.91 kg (hot start, 10 rows), 2.09 kg (silo_cold_s1, 14 rows), 1.99 kg (lag, 24 rows); altitude up to 1.75 m, downrange up to 6.4 m, pitch unchanged |
| 4 decimals | mass 0.09 to 0.52 kg, no row out |
| 6 decimals | mass 0.001 to 0.48 kg, no row out |
| Values rounded to alt 0.1 m, downrange 0.1 m, pitch 0.01 deg, fraction 0.001, tank masses 0.1 kg (times 4 decimals) | altitude 1.45 m, downrange 7.2 m, pitch 0.006 deg (0.098 silo_failed), fraction 0.0005, mass 0.10 to 0.54 kg; no row out |
| Same with tank masses to 1 kg | mass 0.50 to 0.94 kg; no row out, but almost the whole budget |

Size: seven series (time, altitude, downrange, pitch, fraction, two tanks) under E or F are 38 to 45 kB of JSON per orbital run and 8.5 kB for silo_failed, so about 180 kB for four runs on top of the replay's fields.

Verdict on criterion 5 at every CSV row:

- Altitude and downrange hold on the plain replay grid with a tenfold margin.
- Attitude, plume fraction and mass do not hold on the phase file's proposal (variant A). They hold with three changes: both rows of every duplicate time are kept; the plume fraction is interpolated, and only the on or off flag and the stage are step-wise; CSV rows are inserted in the startup ramp and around an unpowered apex (or the insertion rule above is used, which covers both and any future case).
- A sample at an event must take its time from the time-series row whose `t_s` equals the event's `t_s`. Subtracting the release time from the event time can land 5e-11 s before the duplicate rows and sample the wrong side; in the first pass that produced a 22,200 kg error at staging on three of the eleven runs (silo_cold, silo_hot_ramp_on_track, silo_cold_s2; `s09_grid.out`, variants B and C).

## 6. Plume fraction

Fraction = `thrust_vac_N` / (engine count x per-engine vacuum thrust) of the row's stage: stage 1 = 9 x 914.1 kN = 8,226,900 N; stage 2 = 1 x 981 kN = 981,000 N. The largest `thrust_vac_N` in each stage equals these values exactly.

| Situation | Run | Rows with 0 < fraction < 1 | Time after release | Fraction |
|---|---|---|---|---|
| Hold on the pad, 2 s linear ramp | scr/pad, off pad controls | 39 | -1.95 to -0.05 s | 0 at -2.0 s, linear, 1 at release |
| Hold before the push, engines at full on the track | scr/silo_hot_full | 39 | -4.557 to -2.657 s | 1 through the whole ASSIST phase |
| Hot start on the track (ignition 2 s before release) | scr/silo_hot_ramp_on_track | 40 | -1.957 to -0.007 s | 0 before -2.0 s, linear, 1 at release |
| Cold silo, ignition 0.5 s after release, 2 s ramp | silo_cold, silo_cold_s1, fix5pct, dry+8.1t, silo_cold_s2 | 40 | 0.543 to 2.493 s | 0 in ASSIST and COAST_PRE_IGN, linear in KICK, 1 from 2.5 s |
| Step startup at release | scr/silo_instant | 0 | - | two rows at 0 s: 0 then 1 |
| Lag startup, tau 1 s | scr/silo_cold_lag | 564 | 0.543 to 28.593 s | 1 - exp(-dt/tau): 0.632 at 1 s, 0.865 at 2 s, 0.950 at 3 s; first row at or above 0.98 is 3.94 s after ignition, 0.999 at 6.94 s; the CSV's 12 digits read exactly 1 from 28.14 s |
| Stage 2 (step) | every flight | 0 | - | 0 in COAST_STAGING, 1 in LTG_BURN; two rows at ignition: 0 then 1 |
| Failed ignition | scr/silo_failed | 0 | - | 0 throughout |

Outside those windows the distinct values are exactly {0, 1} in every run; there is no throttling.

- At a ramp or lag ignition the fraction is exactly 0 on the ignition row, so "thrust on" cannot be `thrust_vac_N > 0` at that instant; take it from the events (ignition at or before t, and before the stage's `propellant`, `cutoff` or `end`).
- A lag has no end: `vehicle.py` 111 and no `ramp_end` event (`vehicle.py` 266). "Outside a startup ramp" needs a definition for it, for example fraction at or above 0.98 (3.9 tau after ignition).
- The last row of every flight still has fraction 1 (the engine is on at the cutoff instant). The plume must be switched off by the `cutoff` (or final `propellant`) event, or the last frame shows a burning engine.
- Delivered thrust `thrust_N` is zero on the first 3 rows of a sea-level ramp (fraction up to 0.075) because of the back-pressure clamp, and is 0.9246 of the vacuum value at sea level. The plume should follow `thrust_vac_N`, as the phase file says.

## 7. What the scene would show that the model does not support

1. Attitude of an unpowered body. `pitch_rad` follows v_rel when thrust is off. In silo_failed the drawn rocket would turn 180 deg within 0.1 s at the apex and fall nose first. A point mass has no attitude; this is a display choice and needs its own rule.
2. Instant attitude changes: 2.2 to 4.1 deg at the kick start and 3.3 to 10.9 deg at stage-2 ignition in zero time. The model has no rotational dynamics.
3. In the stage-2 burn the drawn axis (thrust) is up to 15.5 deg from the flight path, and at cutoff the nose points 13.4 deg below the screen horizontal (pitch +1.5 deg above a local horizontal that has tilted 14.9 deg).
4. The spent stage and the fairing coast in vacuum: they hit at 2.9 to 3.9 km/s, 839 to 1,389 km downrange, with no re-entry drag. For the 11 s staging coast the spent stage and the vehicle are the same point (0.2 m), so any visible gap is drawn, not computed. Both fairing halves follow one path.
5. In silo_cold_s2 the run ends before the spent stage (60 s short) and the fairing (93 s short) land.
6. After cutoff there is no data. The last row is still at full thrust.
7. During ASSIST the downrange is 0 and the pitch is the track angle; q and Mach are undefined.
8. The vehicle is one point. Which point of a 70 m drawing sits at `alt_m` is a display choice; reading it as the base matches push start at the shaft floor (-100 m) and release at the mouth.
9. One propellant mass per stage: a level drawn as a height assumes volume fraction equals mass fraction and one tank per stage.
10. The fraction is 0 or 1 outside the startup: no throttle-down at max-Q or before MECO.
11. Before a run's first row (pad -2.0 s, silo -2.607 s, silo_hot_full -4.607 s) there is no state; a shared clock that starts earlier shows the first row held.

## 8. Contradictions and gaps against the phase file

1. Section 5.4 (lines 466-469) and exit criterion 6 (line 1082) read `propellant` as MECO. In `pad__offload_stage1/events.csv` line 10 `propellant` is the stage-2 depletion. Select the row with `stage == stage1`.
2. Section 5.3 (lines 392-397) proposes the replay grid plus the event times, with keep-last duplicates. On the recorded data that misses criterion 5 (lines 1076-1080): pitch by up to 10.7 deg, plume fraction by up to 0.98, directly interpolated mass by up to 29,800 kg.
3. Section 5.3 (lines 395-396) lists "thrust on or off" among the step-like fields. The plume fraction must not be step-wise: on a 0.1 s step the 2 s ramp is off by 0.025 to 0.046, above the 0.02 of line 1078.
4. Exit criterion 5 (lines 1077-1078), "thrust on or off exactly outside a startup ramp", has no meaning for a lag startup (silo_cold_lag: 564 rows between 0 and 1).
5. Exit criterion 5, attitude within 0.5 deg, fails on silo_failed around the apex on any grid without the CSV rows there (11.4 deg, 4 rows).
6. Exit criterion 6 (lines 1081-1082), "within 1%", cannot tell the penalty run silo_cold_s1_dry+8.1t (offload 0.482%, fill 0.995180) from a full tank. The reconstruction is exact to 1e-12, so the tolerance can be 1e-4 of full load.
7. Section 5.5 (line 501) quotes the speed check as "about 3049 against 3049.68 m/s". It closes to 1e-8 m/s; nothing to fix, but the test tolerance can be tight.
