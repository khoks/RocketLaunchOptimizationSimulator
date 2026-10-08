<!-- Record of SP7 step 0: read-only survey 05-recorded-loads (recorded load-case histories for the structural envelope), made by a workflow agent on 2026-10-07/08 at HEAD 22c62e9 and saved byte for byte from the workflow journal. Line numbers are for 22c62e9; scratch scripts and paths it names are not in the repository. Not edited; corrections go into the phase file. -->

# SP7 step 0 survey 05: recorded load-case histories for a first-order structural envelope

I read the recorded CSVs without writing to them: results/silo_offload_2d/20261003T112934Z (git b3150c1754ee, clean) and results/silo_screening_2d/20260930T175743Z (git 7ad381f227a9, clean). From them I rebuilt, for 15 runs, the stage-1 propellant on board, its LOX and RP-1 parts (constant mixture ratio 287.4/123.5) and the products n x m_above that a quasi-static axial envelope needs. On the pad, each element's envelope is set at a different instant. MECO (5.195 g0 on 161.5 t, stage 1 empty) sets n U and n (U+LOX): 723.5 t g0, 7.095 MN. Mid-burn (t = 93.8 s) sets the aft station n (U+LOX+RP-1): 773.6 t g0, 7.586 MN. Liftoff sets both tank-bottom heads, n LOX and n RP-1: 388.8 and 167.1 t g0. MECO sets thrust: 8.227 MN. The 3 g0 net push gives 3.996 g0 felt, exact to 5e-12. At the top of stage 1 it stays inside the envelope (n U 0.769-0.779x). Everywhere stage-1 propellant sits above a station it exceeds the envelope: n (U+LOX) by 2.197x (offloaded headline) to 2.367x (full load), the aft station by 2.605-2.852x, and both tank-bottom heads by 2.624-2.954x. With these stacks, any push above 1.35-1.52 g0 felt (0.36-0.52 g0 net) exceeds the hydrostatic envelope. Under constant_accel a hot start cuts the interface force (14.50-14.79 MN against 22.49 MN) but changes the tank loads only by the propellant already burned. A run's in-memory Result holds everything a structural function needs except two things: the vehicle's stage masses (these can be recovered from its events) and the LOX/RP-1 split. The offload solve's own evaluations have no time series (dense output off). So a structural mass coupled inside the problem factory must be sized from the Vehicle and the assist model, not from a Result.

## 1. Sources, method and conventions

Facts:

- Runs read: offload directory: pad, pad__offload_stage1, silo_cold, silo_cold_s1, silo_hot_ramp_on_track, silo_hot_ramp_s1, silo_cold_200m_s1, silo_cold_s1_dry+2t, +4t and +8.1t. Screening directory: pad (a cross-check; identical to the offload pad to 4 s.f. in every quantity), silo_hot_full, silo_sled_22t, silo_instant and silo_failed. Each has timeseries.csv and events.csv; the run settings come from the directory's resolved_config.yaml.
- Scripts and outputs are in C:/Users/rahul/AppData/Local/Temp/claude/D--DEV-ClaudeProjects-SpaceRocketOptimization/3e237173-2609-4e7b-ac46-15c1a393670f/scratchpad/a0/05-recorded-loads/: loads.py, tables.py, history.py, events_check.py and explore_cfg.py, plus loads_out.txt, tables_out.txt, loads.json and history_{pad,silo_cold,silo_cold_s1,silo_hot_full}.csv. That last set is the stage-1 rows with every derived column, ready for a design input.
- The harness refused to write REPORT.md there ("Subagents should return findings as text"), so this message is the only copy of the report. Nothing was written under results/ or anywhere in the repository, and the tree is clean.
- CSV precision is `%.12g` (results_io.py:165; `write_csv` 553-557). "CSV line" below is the 1-based line of that run's timeseries.csv, with the header as line 1 (data row index + 2). At a phase boundary the CSV has two rows at the same t, one ending a phase and one starting the next, because `_phase_samples` includes both ends (metrics.py:147-158). I name the row I used.
- Masses. dry1 and the loaded stage-1 propellant come from each run's resolved vehicle; the offload_runs entries carry their own vehicle, with the solved offload and any added dry mass.
  - U = m_kg(first row) - dry1 - prop1_loaded = stage-2 dry + stage-2 propellant + fairing + the payload flown.
  - prop1(t) = m_kg(t) - dry1 - U on stage1 rows.
  - LOX = 0.69944 prop1 and RP-1 = 0.30056 prop1 (287.4/410.9 and 123.5/410.9). The code's energy block uses the same constant-ratio rule (compare.py:1681-1688).
  - The fairing leaves during the stage-2 burn in every run that gets that far (events.csv `fairing` at 182.8-196.8 s, always after `staging`), so U is constant through stage 1.
- Consistency checks (events_check.py, loads.py):
  - At the stage-1 `propellant` event, prop1 = 0 within 9e-7 kg in all 14 runs that stage.
  - m(`propellant`, stage1) - m(`staging`) equals the configured dry1 to 1e-6 kg (22.2, 24.2, 26.2 and 30.3 t).
  - m0 - m(`propellant`) equals the configured loaded propellant to 1e-6 kg. For example, silo_cold_s1 gives 369,637.092 kg = 410.9 t - 41,262.908 kg.
- Quantities:
  - n = `felt_axial_g`.
  - The station products n U, n (U+LOX), n (U+LOX+RP-1), n LOX and n RP-1, each given in t g0 and as a force (x g0) in MN.
  - n m, the whole vehicle: the load if the carriage pushes through the thrust structure.
  - T = `thrust_N`, the delivered thrust.
  - Stage-1 dry mass above a station is not included; that is the task's definition (section 8).

Assumptions I made (inferred, not in any repository file I read):

- The station order is Falcon 9's, with the LOX tank above the RP-1 tank. That makes n U the upper (LOX) tank wall in compression, n (U+LOX) the intertank and RP-1 tank wall, and n (U+LOX+RP-1) the aft skirt above the thrust structure.
- The hydrostatic pressures in kPa are p = n g0 m / A_ref, with A_ref = 10.52 m^2 (the vehicle's reference area), a flat bottom and no ullage pressure. They are for orientation only, because the tank bore and the domes differ.

## 2. Time-series columns and phase labels (item 1)

Facts:

- Columns, 32 in this order (`PLANAR_TIMESERIES_COLUMNS`, metrics_planar.py:340-348):
  - Labels: t_s, t_rel_release_s, phase, stage.
  - Flight columns (298-315): alt_m, downrange_m, speed_rel_mps, speed_inertial_mps, gamma_rel_rad, pitch_rad, psi_rad, m_kg, thrust_N, thrust_vac_N, drag_N, q_pa, mach, q_alpha_pa_rad, felt_axial_g, felt_lateral_g.
  - Quadratures (331-338): J_vac_mps, J_grav_mps, J_alt_mps, J_drag_mps, J_steer_mps, J_bp_mps.
  - TRACK_COLUMNS (metrics.py:60-67): s_m, drive_force_N, interface_force_N, drive_power_W, track_normal_g_vehicle, track_normal_g_carriage. These are NaN outside ASSIST rows (docstring metrics_planar.py:349).
- Phase labels found:
  - HOLD (trace.py:31).
  - ASSIST (trace.py:33).
  - The planar flight kinds (phases/planar.py:123-153; `PLANAR_ASCENT_KINDS` 156-164): COAST_PRE_IGN, VERTICAL_RISE, KICK, GRAVITY_TURN, COAST_STAGING, LTG_BURN and COAST.
  - The stage column reads stage1 or stage2.
- Phases each run passes through:

  | Run | Phases in order |
  |---|---|
  | pad, pad__offload_stage1 | HOLD, VERTICAL_RISE, KICK, GRAVITY_TURN, COAST_STAGING, LTG_BURN |
  | cold silo runs (silo_cold, _s1, _200m_s1, the penalty rows, silo_sled_22t) | ASSIST, COAST_PRE_IGN (0.5 s), KICK, GRAVITY_TURN, COAST_STAGING, LTG_BURN |
  | silo_hot_ramp_on_track, silo_hot_ramp_s1, silo_instant | ASSIST, KICK, GRAVITY_TURN, COAST_STAGING, LTG_BURN |
  | silo_hot_full | HOLD (clamped at the silo bottom, alt -100 m), ASSIST, KICK, ... |
  | silo_failed | ASSIST, COAST |

- What felt_axial_g holds depends on the row type:
  - Flight rows: (T - D cos psi)/(m g0) (metrics_planar.py:461).
  - HOLD rows: g_eff/g0 = 0.996476, whatever the thrust ("the clamp carries the weight", `_hold_row` 466-483).
  - ASSIST rows: (F_int + T)/m_v (dynamics.py:505, through metrics_planar.py:518). Track rows also have q_pa and mach NaN and drag_N 0, since the vented shaft has no air model (515-517).
- Two pitfalls (inferred from the numbers):
  - silo_hot_ramp_on_track's ASSIST block has 56 rows where the cold runs have 54. It appears to be split at the ignition kink (`TrackParams.lit`, dynamics.py:380-383 and 392).
  - Some metrics.json times are relative to release, while events.csv t_s is the run clock (push_start = 0 on a silo). For example, silo_cold_s1's `stage1_burnout_t_s` is 138.53 s against its `propellant` event at 141.14 s, and `felt_g_track_peak_t_s` is -2.607 s.

## 3. The pad run (item 2)

All facts below come from results/silo_offload_2d/20261003T112934Z/pad. U = 139,254.396 kg (4.0 + 107.5 + 1.7 t + P_ref 26,054.396 kg), dry1 = 22.2 t.

**3.1 Points**

| Point | CSV line | t_s | Phase | m [t] | n [g0] | prop1 [t] | LOX [t] | RP-1 [t] | T [MN] | D [kN] |
|---|---|---|---|---|---|---|---|---|---|---|
| hold start (ignition) | 2 | -2 | HOLD | 572.4 | 0.9965 | 410.9 | 287.4 | 123.5 | 0 | 0 |
| hold end | 42 | 0 | HOLD | 569.7 | 0.9965 | 408.2 | 285.5 | 122.7 | 7.607 | 0 |
| release = liftoff | 43 | 0 | VERTICAL_RISE | 569.7 | 1.362 | 408.2 | 285.5 | 122.7 | 7.607 | 0 |
| max-Q (row nearest 65.7515 s) | 1362 | 65.75 | GRAVITY_TURN | 392.3 | 2.042 | 230.8 | 161.5 | 69.38 | 8.088 | 232.8 |
| MECO (stage-1 depletion) | 3074 | 151.3 | GRAVITY_TURN | 161.5 | 5.195 | 0 | 0 | 0 | 8.227 | 0.7313 |

- Max-Q in metrics.json: 37,191.38 Pa at 65.7515 s. The CSV row at line 1362 reads 37,191.1 Pa.
- The peak felt g in metrics.json is 5.19547 g0 at 151.328 s on 161,454 kg, the same as line 3074.

**3.2 Hold-down (lines 2-42, t = -2 to 0 s)**

- n = 0.9965 g0 on all 41 rows (the clamp convention above). The tanks feel 1 g with full tanks.
- Delivered thrust builds from 0 to 7.607 MN. It reads 0 on lines 3-5, where thrust_vac_N is 0.21-0.62 MN, until the vacuum thrust exceeds p_amb A_e.
- The clamp force, m g_eff - T, goes from +5.593 MN (line 2, carrying the weight) to -2.040 MN (line 42, holding the vehicle down).
- metrics.json agrees: `hold_down_force_min_N` = -2,040,060 N (the `HoldSummary.force_min_N` of trace.py:219-221) and `hold_propellant_burned_kg` = 2,697.5 kg.
- So in the hold the thrust structure carries up to 7.607 MN, while every station above it carries only the weight.

**3.3 Stage-1 propellant at the events (events.csv; prop1 = m_kg - 161,454.396 kg)**

| Event | t_s | m_kg | prop1 [t] | LOX [t] | RP-1 [t] |
|---|---|---|---|---|---|
| ignition | -2 | 572,354.4 | 410.9 | 287.4 | 123.5 |
| release | 0 | 569,656.9 | 408.2 | 285.5 | 122.7 |
| kick_start | 12.49 | 535,955.6 | 374.5 | 261.9 | 112.6 |
| kick_end | 17.77 | 521,712.2 | 360.3 | 252.0 | 108.3 |
| propellant (stage 1) | 151.3 | 161,454.4 | 0 (-5.8e-11 kg) | 0 | 0 |

**3.4 History (pad; the station products in MN)**

| CSV line | t_s | Phase | m [t] | n | prop1 [t] | T [MN] | D [kN] | n U | n (U+LOX) | n (U+LOX+RP-1) | n LOX | n RP-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | -2 | HOLD | 572.4 | 0.9965 | 410.9 | 0 | 0 | 1.361 | 4.169 | 5.376 | 2.808 | 1.207 |
| 43 | 0 | VERTICAL_RISE | 569.7 | 1.362 | 408.2 | 7.607 | 0 | 1.860 | 5.672 | 7.310 | 3.813 | 1.638 |
| 243 | 10 | VERTICAL_RISE | 542.7 | 1.431 | 381.2 | 7.621 | 4.204 | 1.954 | 5.697 | 7.305 | 3.742 | 1.608 |
| 447 | 20 | GRAVITY_TURN | 515.7 | 1.512 | 354.3 | 7.664 | 17.92 | 2.065 | 5.738 | 7.317 | 3.674 | 1.579 |
| 847 | 40 | GRAVITY_TURN | 461.8 | 1.713 | 300.3 | 7.831 | 75.12 | 2.339 | 5.867 | 7.383 | 3.528 | 1.516 |
| 1247 | 60 | GRAVITY_TURN | 407.8 | 1.946 | 246.4 | 8.038 | 255.4 | 2.657 | 5.946 | 7.359 | 3.288 | 1.413 |
| 1362 | 65.75 | GRAVITY_TURN | 392.3 | 2.042 | 230.8 | 8.088 | 232.8 | 2.788 | 6.022 | 7.411 | 3.233 | 1.389 |
| 1647 | 80 | GRAVITY_TURN | 353.9 | 2.318 | 192.4 | 8.173 | 128.6 | 3.166 | 6.225 | 7.540 | 3.059 | 1.315 |
| 1923 | 93.8 | GRAVITY_TURN | 316.6 | 2.627 | 155.2 | 8.209 | 51.38 | 3.588 | 6.384 | 7.586 | 2.797 | 1.202 |
| 2047 | 100 | GRAVITY_TURN | 299.9 | 2.783 | 138.5 | 8.217 | 33.21 | 3.800 | 6.442 | 7.578 | 2.643 | 1.136 |
| 2447 | 120 | GRAVITY_TURN | 246.0 | 3.407 | 84.51 | 8.225 | 8.360 | 4.652 | 6.627 | 7.475 | 1.975 | 0.8486 |
| 2847 | 140 | GRAVITY_TURN | 192.0 | 4.368 | 30.56 | 8.227 | 2.080 | 5.965 | 6.880 | 7.274 | 0.9155 | 0.3934 |
| 3074 | 151.3 | GRAVITY_TURN | 161.5 | 5.195 | 0 | 8.227 | 0.7313 | 7.095 | 7.095 | 7.095 | 0 | 0 |

**3.5 The pad envelope (maximum over every stage-1 row: HOLD plus flight)**

| Quantity | Max [t g0] | Max [MN] | t_s | Phase | CSV line | Element it sizes (inferred) |
|---|---|---|---|---|---|---|
| n | 5.195 g0 | | 151.3 | GRAVITY_TURN | 3074 | |
| n U | 723.5 | 7.095 | 151.3 | GRAVITY_TURN | 3074 | upper (LOX) tank wall in compression; interstage |
| n (U+LOX) | 723.5 | 7.095 | 151.3 | GRAVITY_TURN | 3074 | intertank, lower (RP-1) tank wall |
| n (U+LOX+RP-1) | 773.6 | 7.586 | 93.80 | GRAVITY_TURN | 1923 | aft skirt above the thrust structure |
| n LOX | 388.8 | 3.813 (362.4 kPa) | 0 | VERTICAL_RISE | 43 | LOX tank bottom, hydrostatic |
| n RP-1 | 167.1 | 1.638 (155.7 kPa) | 0 | VERTICAL_RISE | 43 | RP-1 tank bottom, hydrostatic |
| n m (whole vehicle) | 838.8 | 8.226 | 151.3 | GRAVITY_TURN | 3074 | thrust structure as a through-path |
| T | | 8.227 | 151.3 | GRAVITY_TURN | 3074 | thrust structure |

- The HOLD maxima are all lower: n 0.9965; n U 1.361, n (U+LOX) 4.169, n (U+LOX+RP-1) 5.376, n LOX 2.808, n RP-1 1.207 and n m 5.593 MN (line 2); T 7.607 MN (line 42).
- The governing instant differs by element. Two cases stand out:
  - n (U+LOX) peaks at MECO, when the LOX is gone, not at liftoff.
  - The aft station peaks inside the burn, where the product is flat: 7.540 / 7.586 / 7.578 MN at 80 / 93.8 / 100 s.
- A drag-at-the-nose bound on the top station, n U g0 + D (inferred: all drag acting above the station), gives 7.096 MN at MECO and only 3.021 MN at max-Q. MECO governs, and the drag term moves the envelope by 0.01%.
- pad__offload_stage1 and the screening pad reproduce every maximum to 4 s.f.

## 4. The push against the pad envelope (item 3)

Facts: values are the maximum over each run's ASSIST rows, with the ratio to the section 3.5 envelope in parentheses.

- Cold runs: every ASSIST row carries the same values (CSV lines 2-55; 2-107 for the 200 m stroke).
- silo_hot_ramp_on_track and silo_hot_ramp_s1 (lines 2-57): the station maxima are on line 2 and the thrust maximum on line 57 (release).
- silo_hot_full: ASSIST lines 43-96, maxima on line 43 (push start, after the 2 s hold).
- "prop1" is the stage-1 propellant at push start.
- n m g0 = F_int + T.

| Run | U [t] | prop1 [t] | n [g0] | n U [MN] | n (U+LOX) [MN] | n (U+LOX+RP-1) [MN] | n LOX [MN] | n RP-1 [MN] | T on track [MN] | F_int max / min [MN] | n m g0 [MN] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| silo_cold (full load, own P*) | 140.8 | 410.9 | 3.996 (0.7692) | 5.516 (0.7775) | 16.78 (2.365) | 21.62 (2.850) | 11.26 (2.954) | 4.840 (2.954) | 0 | 22.49 / 22.49 | 22.49 (2.734) |
| silo_cold_s1 (headline, P_ref) | 139.3 | 369.6 | 3.996 (0.7692) | 5.458 (0.7692) | 15.59 (2.197) | 19.94 (2.629) | 10.13 (2.658) | 4.354 (2.658) | 0 | 20.81 / 20.81 | 20.81 (2.530) |
| silo_hot_ramp_on_track | 141.0 | 410.9 | 3.996 (0.7692) | 5.526 (0.7788) | 16.79 (2.366) | 21.63 (2.851) | 11.26 (2.954) | 4.840 (2.954) | 7.607 (0.9246) | 22.50 / 14.79 | 22.50 (2.735) |
| silo_hot_ramp_s1 | 139.3 | 364.9 | 3.996 (0.7692) | 5.458 (0.7692) | 15.46 (2.179) | 19.76 (2.605) | 10.00 (2.624) | 4.298 (2.624) | 7.607 (0.9246) | 20.63 / 12.92 | 20.63 (2.508) |
| silo_hot_full (screening) | 140.7 | 408.2 | 3.996 (0.7692) | 5.516 (0.7774) | 16.71 (2.355) | 21.51 (2.836) | 11.19 (2.935) | 4.808 (2.935) | 7.607 (0.9246) | 14.78 / 14.50 | 22.38 (2.721) |
| silo_sled_22t (screening) | 140.8 | 410.9 | 3.996 (0.7692) | 5.516 (0.7775) | 16.78 (2.365) | 21.62 (2.850) | 11.26 (2.954) | 4.840 (2.954) | 0 | 22.49 / 22.49 | 22.49 (2.734) |
| silo_instant (screening) | 141.1 | 410.9 | 3.996 (0.7692) | 5.529 (0.7793) | 16.79 (2.367) | 21.63 (2.852) | 11.26 (2.954) | 4.840 (2.954) | 0 | 22.50 / 22.50 | 22.50 (2.736) |
| silo_failed (screening, P0 22.8 t) | 136.0 | 410.9 | 3.996 (0.7692) | 5.330 (0.7512) | 16.59 (2.339) | 21.43 (2.825) | 11.26 (2.954) | 4.840 (2.954) | 0 | 22.30 / 22.30 | 22.30 (2.711) |
| silo_cold_200m_s1 (1.5 g0 net) | 139.3 | 369.6 | 2.496 (0.4805) | 3.409 (0.4805) | 9.739 (1.373) | 12.46 (1.642) | 6.330 (1.660) | 2.720 (1.660) | 0 | 13.00 / 13.00 | 13.00 (1.581) |
| silo_cold_s1_dry+2t | 139.3 | 378.6 | 3.996 (0.7692) | 5.458 (0.7692) | 15.84 (2.232) | 20.30 (2.675) | 10.38 (2.722) | 4.460 (2.722) | 0 | 21.24 / 21.24 | 21.24 (2.583) |
| silo_cold_s1_dry+4t | 139.3 | 388.0 | 3.996 (0.7692) | 5.458 (0.7692) | 16.09 (2.268) | 20.67 (2.724) | 10.64 (2.790) | 4.571 (2.790) | 0 | 21.69 / 21.69 | 21.69 (2.637) |
| silo_cold_s1_dry+8.1t | 139.3 | 408.9 | 3.996 (0.7692) | 5.458 (0.7692) | 16.67 (2.349) | 21.48 (2.832) | 11.21 (2.940) | 4.817 (2.940) | 0 | 22.67 / 22.67 | 22.67 (2.756) |

In t g0 (silo_cold / silo_cold_s1): n U 562.5 / 556.5, n (U+LOX) 1711 / 1590, n (U+LOX+RP-1) 2205 / 2034, n LOX 1149 / 1033, n RP-1 493.6 / 444.0.

As hydrostatic pressure (orientation only, section 1):

| | LOX bottom [kPa] | RP-1 bottom [kPa] |
|---|---|---|
| pad liftoff | 362.4 | 155.7 |
| silo_cold | 1071 | 460.1 |
| silo_cold_s1 | 963.2 | 413.9 |

**What the push exceeds** (facts from the table; the element names follow the inferred station order):

- **Upper (LOX) tank wall and interstage (n U): not exceeded.** The push is at 0.751-0.779x of the MECO envelope, because the push's 4.0 g0 is below MECO's 5.2 g0 on the same upper mass. This confirms the brief's first look (SP7 file section 5.2).
- **Intertank and RP-1 tank wall (n (U+LOX)): exceeded** by 2.197x (headline) to 2.367x (full load). The pad's governing case for this element is MECO, not liftoff.
- **Aft structure (n (U+LOX+RP-1)): exceeded** by 2.605x (hot ramp, offloaded) to 2.852x (full load).
- **LOX and RP-1 tank bottoms (hydrostatic): exceeded** by 2.624-2.954x. The two ratios are equal by construction, because of the constant mixture ratio. The planar full-load ratio, 2.954x against liftoff, compares with the README's "about 2.8 times" (quoted in SP7 file section 5.1).
- **Thrust structure: depends on where the carriage load enters** (question Q5):
  - Through an aft ring, the thrust structure carries only T. That is 0 on a cold push and 7.607 MN on a hot one, 0.9246x of the flight maximum, so inside the envelope.
  - Through the thrust structure, it carries n m g0 = 22.38-22.50 MN on a full stack (2.721-2.736x) and 20.81 MN on the headline (2.530x).
- **Interface hardware: no flight analog.** Its sizing input is F_int itself:

  | Case | F_int [MN] | vs max thrust 8.227 MN | vs sea-level thrust 7.607 MN | vs pad clamp support 5.593 MN |
  |---|---|---|---|---|
  | full-load cold | 22.49 | 2.734x | 2.957x | 4.021x |
  | headline | 20.81 | 2.530x | 2.736x | 3.721x |
  | hot starts | 12.92-14.79 | | | |

- **Hot starts under constant_accel.** The felt g is unchanged (3.996 g0 on every hot ASSIST row). The interface force falls by T (silo_hot_full 14.50-14.78 MN). The tank products fall only by the propellant already burned: silo_hot_full is 0.66% lower in n (U+LOX+RP-1) at push start (2.697 t burned in the hold, 7.03 t more by release).
- **silo_sled_22t:** vehicle loads identical to silo_cold. Only the drive force changes (23.35 MN against 22.49 MN).

**Break-even felt g.** For each element, the felt n at which the push's product equals the pad envelope, with the stack at push start (n_max = envelope / m_above):

| Stack | U [t] | prop1 [t] | n (U+LOX) | n (U+LOX+RP-1) | n LOX = n RP-1 | n U |
|---|---|---|---|---|---|---|
| silo_cold (full load) | 140.8 | 410.9 | 1.690 | 1.402 | 1.353 | 5.140 |
| silo_hot_full (push start) | 140.7 | 408.2 | 1.697 | 1.409 | 1.362 | 5.141 |
| silo_cold_s1 (headline) | 139.3 | 369.6 | 1.819 | 1.520 | 1.504 | 5.195 |
| silo_cold_s1_dry+8.1t | 139.3 | 408.9 | 1.701 | 1.411 | 1.359 | 5.195 |

In net acceleration on the vertical track (n - 0.9965), the tank bottoms' break-even is about 0.36 g0 net (full) and 0.51 g0 net (headline).

## 5. Post-release stage-1 flight of the assisted runs against the pad envelope

Facts (ratio to the section 3.5 envelope; CSV line of each maximum):

| Run | n U at MECO | n (U+LOX+RP-1) peak | n LOX peak |
|---|---|---|---|
| silo_cold | 1.0015 (line 3139) | 1.0062 (t 90.95 s, line 1829) | 0.9975 (t 5.107 s, line 109, at full thrust after the cold start) |
| silo_hot_ramp_on_track | 1.0017 | 1.0069 | 0.9949 |
| silo_hot_full | 1.0015 | 1.0059 | 0.9904 |
| silo_instant | 1.0018 | 1.0073 | 0.9966 |
| silo_sled_22t | same as silo_cold | same as silo_cold | same as silo_cold |
| runs at P_ref (silo_cold_s1, silo_hot_ramp_s1, silo_cold_200m_s1) | 1.0000 | 0.9995-0.9997 | 0.963-0.969 |
| penalty rows (+2, +4, +8.1 t) | 0.9878 / 0.9758 / 0.9523 | 0.9949 / 0.9904 / 0.9819 | 0.9727 / 0.9765 / 0.9847 |

- The small exceedances belong to the full-load runs, which fly their own P* (27.54-27.88 t, against P_ref 26.05 t). U is 1.5-1.8 t heavier on the same thrust. This is a payload effect, not a push effect.
- Max-Q, which none of these products uses:

  | Run | Max-Q [kPa] | Source |
  |---|---|---|
  | pad | 37.19 | metrics |
  | silo_cold_s1 | 38.44 | metrics |
  | silo_hot_ramp_s1 | 39.71 | CSV line 1056 |
  | silo_cold | 31.24 | metrics |

- On the cold runs, n is about -0.003 g0 (drag only) through COAST_PRE_IGN. For silo_cold, n falls from 3.996 g0 at release (line 55) to -0.00279 g0 on the next row (line 56, t = 2.607 s), at q 3.604 kPa and D 15.70 kN.

## 6. Checks on the track quantities (item 4)

Facts:

- g_eff = mu/R_E^2 - omega_p^2 R_E = 9.772092 m/s^2, with omega_p = 6.408435e-5 rad/s at 28.5 deg, azimuth 90 (dynamics.py:114-121). So (3 g0 + g_eff)/g0 = 3.996476035905.
- Every ASSIST row of all 12 runs at 3 g0 net reads felt_axial_g = 3.99647603591, a maximum deviation of 4.6e-12 (the CSV's 12 digits).
- silo_cold_200m_s1, with a = 76.70717^2/(2 x 200) = 14.71 m/s^2 = 1.5 g0, reads 2.49647603591 against 2.496476035905.
- Without rotation, (3 g0 + mu/R_E^2)/g0 = 3.999147, the 1-D "3.9991" of docs/physics.md.
- F_int = m_v (a + g_eff) - T (constant_accel.py:137-144) holds on every ASSIST row within 6.6e-5 N, relative < 3e-12, including the hot runs where T changes during the push.
- metrics.json agrees: `felt_g_track_peak` 3.9964760359053533; `interface_force_peak_N` 22,490,479.62 N (silo_cold) and 20,814,559.76 N (silo_cold_s1). The latter is computed at metrics_planar.py:997-1001.
- `track_normal_g_vehicle` is at most 6.1e-17 g0 (the vertical straight track has no normal load).

## 7. What a pure structural function of a Result can read (item 5)

Facts:

- `Result` (sim.py:627-661) has the fields metrics, timeseries, loss_budget, assist_budget, assumptions, phases, status, flags, events, model, search, closure and trace (649-661).
- For a planar run, `simulate_planar` builds the frame once (`frame = sample_trace_planar(...)`, sim.py:1239) and stores it as `timeseries=frame` (1278). `write_timeseries` writes exactly `result.timeseries` and `result.events` (results_io.py:560-564). So the CSV is the in-memory frame rounded to 12 significant digits.

| Need | In memory | Where |
|---|---|---|
| n(t), m_v(t), T(t), D(t), phase, stage | `Result.timeseries`: felt_axial_g, m_kg, thrust_N, drag_N, phase, stage | sim.py:650, 1239, 1278; metrics_planar.py:298-348 |
| interface and drive force, s | `Result.timeseries`: interface_force_N, drive_force_N, s_m | metrics.py:60-67 |
| dry1, U, loaded prop1 | `Result.events`: m_kg at `propellant` (stage1) and `staging`, with the first time-series row (verified on all 14 staging runs, section 1); or `Result.trace.burnouts` (t, state) per stage | sim.py:657, 1285; trace.py:165-170, 272 |
| hold-down force | `Result.trace.hold.force_min_N`; metrics `hold_down_force_min_N` | trace.py:216-227, 270; sim.py:661 |
| release time | `Result.trace.t_release_s` | trace.py:266 |
| carriage mass, g_eff, assist model of the push | `Result.trace.phases[i].spec.params` (TrackParams: track, assist, carriage_mass_kg, g_eff_mps2, schedule, lit) | dynamics.py:386-392 |
| payload flown | `Result.metrics["payload_kg"]` | metrics.json of every run |

Not in a Result:

- **The Vehicle.** `simulate_planar` receives it (sim.py:1211) but no Result field keeps it. The resolved vehicle on `RunResult.resolved` (config.py:2359-2370; `to_vehicle` 2368) carries the YAML payload of 22.8 t, not the payload flown. silo_cold_s1's resolved vehicle says 22.8 t while it flew 26,054.396 kg. An offload run's flown vehicle is `with_payload(offload.offloaded_vehicle, P_ref)` (sim.py:1738-1743), which lives on the OffloadResult, not the Result.
- **The LOX/RP-1 split.** It exists only in an experiment's offload energy block (`OffloadEnergyConfig.fuel_mass_t`, config.py:1680-1711, whose docstring says "the vehicle file holds no fuel split"; experiments/silo_offload_2d.yaml:205-206). The silo_screening_2d resolved config has no offload block.

The offload solve's evaluations have no time series. Search evaluations integrate with dense output off (`settings_for`, search.py:579-591), and `sample_trace_planar` refuses a dense-off trace (metrics_planar.py:547; `RunTrace.require_dense`, trace.py:293-305). Only the recorded final run of a solve, which `offload_run_result` assembles (sim.py:1728-1753), has a timeseries. The factory seam receives a Vehicle (`problem_at`, offload.py:206-208; `planar_problem_factory` 256-264).

Inferred conclusions:

- The envelope side can be a pure function of the pad's recorded Result plus the split.
- The push side can be a pure function of a recorded Result plus the split, which is how the results here were checked.
- dm(x) inside option (i) of SP7 section 5.5 cannot read a Result. It has to come from the Vehicle at x and the assist model. For constant_accel that is closed form (n = (a + g_eff)/g0, masses from the stages), and section 6 shows the recorded rows reproduce it to 5e-12. For linear_motor, the track phase alone sets n(t), so it can be flown once per x or solved in closed form.

## 8. Limits of these numbers

Facts:

- The model has no throttling (TODO B-003; out of scope in SP7 file section 2). The MECO envelope of 5.195 g0, which keeps the push inside at the top of stage 1, is the model's own unthrottled case.
- The products omit stage-1 dry mass above each station. Including it on the aft station changes the full-load ratio from 2.850x (n (U+LOX+RP-1)) to 2.734x (n m, all 22.2 t above). The pad maximum of n m falls at MECO, where dry mass is a larger share.
- The 0.05 s sampling resolves every phase-boundary maximum exactly. The one interior maximum, the aft station at 93.8 s, is resolved to the sample, on a flat peak.
- The gate vehicle's +14.3% calibration miss (D-P2-08) applies to every number here.
- Cold silo runs have no row before push start: the CSV starts at 3.996 g0 on line 2. The step onto the push and the release reversal (3.996 to -0.003 g0 in one sample) are constant_accel's "infinite jerk at push start and release" (constant_accel.py:224). They are quasi-static values, with no dynamic load factor.

Inferred:

- Falcon 9's actual MECO acceleration and real structural margins are not in the repository. A lower real envelope at the upper stations would narrow the 0.77x headroom.
- The kPa figures assume flat bottoms at A_ref and no ullage pressure.
- The penalty rows' added dry mass is placed in no station.

## 9. Recommendations for SP7's Plan mode (not facts)

1. **Build the envelope per element** as the maximum over the pad Result's stage-1 rows (HOLD plus flight), and record the governing instant, since it differs by element (section 3.5). For the aft station's interior maximum, use the dense output through `scan_peak` (metrics_planar.py:180-256, the max-Q method), or accept the row maximum and state the sampling.
2. **Take U and dry1 from the flown vehicle or the events**, never from the resolved vehicle dict's payload. Put the LOX/RP-1 split and the tank order in the structure file, sourced; reusing the offload energy block would leave the screening experiment without one.
3. **Size dm(x) inside the factory from the Vehicle at x and the assist model**, as closed forms (section 7). Charge the hot starts at push start, which is conservative by at most 0.66% (silo_hot_full) to 2.4% (the hot ramp at release). Then check against the recorded run's rows after the solve, with a test that recomputes section 4's products from a Result.
4. **Decide how the payload form treats the full-load runs' small flight exceedances** (+0.15-0.18% at the interstage, +0.59-0.73% at the aft station; section 5). Either charge them, or define the envelope at the payload actually flown. They come from P* > P_ref, not from the push, and should be reported separately from the push increment.
5. **Report the break-even felt g per element** (section 4). Under Q3's zero margin it shows that every stroke of SP1's sweep 2 (2.0-7.0 g0 felt) charges the tank bottoms and the aft structure. As inferred arithmetic on the headline stack, the 300 m stroke's 2.0 g0 is 1.33x the hydrostatic envelope.
6. **Carry two sensitivities:** the MECO envelope (an unthrottled-model caveat, inferred), and the stage-1 dry-mass placement (2.734-2.850x on the aft station for the full load).
7. **Size the interface hardware from F_int directly** (22.49 / 20.81 MN cold, 12.92-14.79 MN hot), with the 5.593 MN clamp support as the only on-pad comparison. For Q5, show the aft-ring row (thrust structure inside its envelope) beside the through-thrust-structure row (2.53-2.74x).
8. **Note the release reversal and the near-zero-g pre-ignition coast** (n about -0.003 g0 for 0.5 s on cold starts) as dynamic load factor and propellant-settling items. They are inferred consequences for the linear-motor and hot-start cases, outside the quasi-static mass.
