Provenance: SP2 step A0 survey 05 of 9 (read-only agent report, 2026-10-05, line numbers checked at commit b69ff0c); below this header, a byte copy from the session scratchpad (a0/05-run-data-on-disk.md); a record, not edited (README.md).

# 05 - Recorded run data on disk (SP2 step A0 survey)

Repository `D:/DEV/ClaudeProjects/SpaceRocketOptimization`, HEAD `b69ff0c`, clean tree. Read-only
survey; nothing in the repository or under `results/` was written. Environment: Python 3.12.11,
pandas 3.0.6, numpy 2.5.3 (`uv run`). All numbers below were read from the files on 2026-10-05 by
the scratch scripts listed at the end. Times are seconds after release unless marked "absolute".

Directories surveyed:

- S = `results/silo_screening_2d/20260930T175743Z` (git `7ad381f227a9`, clean; recorded before SP1)
- O = `results/silo_offload_2d/20261003T112934Z` (git `b3150c1754ee`, clean)
- W = `results/silo_offload_2d/20261003T112949Z` (the sweep)
- one 1-D directory, `results/silo_screening_1d/20260929T105657Z`, and its sweep `...105707Z`

---

## 1. Directory layout

### 1.1 Experiment directory (S and O)

Top level: three files, one folder per run, one shared `plots/` folder.

| | S | O |
|---|---|---|
| total bytes | 45,946,129 | 74,260,469 |
| `metrics.json` | 1,841,134 | 512,999 |
| `resolved_config.yaml` | 54,055 | 135,731 |
| `summary.md` | 54,765 | 52,400 |
| `plots/` | 102 png, 3,224,245 bytes | 161 png, 5,092,281 bytes |
| run folders | 12 | 19 |

Every run folder holds exactly two files: `events.csv` and `timeseries.csv`. There is no per-run
metrics or config file; a run's metrics and config live only in the two top-level files.

S run folders (bytes of `events.csv` / `timeseries.csv`):

| run | events | timeseries |
|---|---|---|
| pad | 1,227 | 3,636,073 |
| pad__aero_bound | 1,226 | 3,635,493 |
| pad_instant | 1,237 | 3,636,510 |
| silo_cold | 1,490 | 3,729,167 |
| silo_cold__aero_bound | 1,487 | 3,728,760 |
| silo_cold_lag | 1,376 | 3,732,192 |
| silo_failed | 653 | 94,739 |
| silo_hot_full | 1,297 | 3,700,110 |
| silo_hot_full_impinged | 1,297 | 3,700,109 |
| silo_hot_ramp_on_track | 1,426 | 3,714,538 |
| silo_instant | 1,315 | 3,719,550 |
| silo_sled_22t | 1,490 | 3,729,168 |

O run folders:

| run | events | timeseries |
|---|---|---|
| pad | 1,227 | 3,636,073 |
| pad__offload_both | 1,220 | 3,636,247 |
| pad__offload_stage1 | 1,223 | 3,636,127 |
| pad__offload_stage2 | 1,224 | 3,623,481 |
| silo_cold | 1,490 | 3,729,167 |
| silo_cold_200m | 1,501 | 3,743,756 |
| silo_cold_200m_s1 | 1,500 | 3,646,869 |
| silo_cold_both | 1,488 | 3,405,436 |
| silo_cold_fix10pct | 1,491 | 3,632,156 |
| silo_cold_fix5pct | 1,489 | 3,681,059 |
| silo_cold_s1 | 1,494 | 3,630,414 |
| silo_cold_s1__pad | 1,216 | 3,538,625 |
| silo_cold_s1_dry+2t | 1,491 | 3,653,912 |
| silo_cold_s1_dry+4t | 1,493 | 3,675,788 |
| silo_cold_s1_dry+8.1t | 1,488 | 3,724,775 |
| silo_cold_s1_s2pre2t | 1,497 | 3,584,312 |
| silo_cold_s2 | 1,493 | 2,944,070 |
| silo_hot_ramp_on_track | 1,426 | 3,714,538 |
| silo_hot_ramp_s1 | 1,432 | 3,603,370 |

`pad`, `silo_cold` and `silo_hot_ramp_on_track` have byte-identical sizes in S and O; their run
blocks and the top-level vehicle block are equal in the two resolved configs.

How the roles are laid out. On disk every role is a sibling folder; nothing in the folder says
what it is. The role is only in `metrics.json` and `resolved_config.yaml`:

| Role | Folder name | `metrics.json` | `resolved_config.yaml` |
|---|---|---|---|
| run | `<name>` | `runs.<name>` (dict) | `runs.<name>` |
| bound re-run | `<of>__<bound>` (`silo_cold__aero_bound`) | `bounds[i].metrics`, where `bounds[i].run == name` (a LIST of records) | `bound_runs.<name>` |
| paired baseline of a bound | `<baseline>__<bound>` (`pad__aero_bound`) | `bounds[i].paired_baseline_metrics`, where `bounds[i].paired_baseline == name` | `bound_runs.<name>` |
| case | `<name>` | `cases.<name>` (dict; empty in S and O) | `cases.<name>` (empty in S and O) |
| offload case's recorded run | the case name (`silo_cold_s1`) | `offload.runs.<name>`; the case record is `offload.cases[i]` with `run == name` (a LIST) | `offload_runs.<name>` |
| paired pad of an offload case | `<case>__pad` (`silo_cold_s1__pad`) | `offload.runs.<name>`; `offload.cases[i].paired_pad.run` | `offload_runs.<name>` |
| pad control | `pad__offload_<mode>` | `offload.runs.<name>`; `offload.pad_controls[i].run` (a LIST of 3) | `offload_runs.<name>` |

There is no `bound_runs` key in `metrics.json` (it is `bounds`, a list) and no `bounds` key in
`resolved_config.yaml` (it is `bound_runs`, a dict). `replay.run_source` (replay.py 244) already
resolves this; `plots.offload_role` (plots.py 722, new in 5007515) tells the three offload kinds
apart.

Sensitivity arms (`sensitivity`, 24 records in S; `offload.sensitivity`, 8 records in O) have no
folders: their `run` names (`silo_cold__vehicle.stages.stage1.dry_mass_t__+0.1`) exist only in
`metrics.json`.

Run-folder names contain `+` and `.` (`silo_cold_s1_dry+8.1t`). The plot files replace `+` by `_`
(`silo_cold_s1_dry_8.1t_angles.png`).

Plots: 7 per pad-type run (`_angles`, `_felt_g`, `_losses`, `_mass_thrust`, `_q_mach`, `_speed`,
`_trajectory`), 9 per assisted run (plus `_drive_power`, `_track_forces`), all in the one
`plots/` folder.

### 1.2 `FAILED.txt`

No file named `FAILED*` exists anywhere under `results/`. (It is written by
`results_io.write_failure_marker`, results_io.py 567-574, `FAILED_MARKER` 167, only when a run
raises after its directory was created.) Non-png file names under `results/`: `metrics.json` 139,
`resolved_config.yaml` 139, `summary.md` 145, `events.csv` 216, `timeseries.csv` 216,
`sweep_index.csv` 18, `.gitkeep` 1.

### 1.3 Sweep directory W (85,489,444 bytes)

Top level: only `summary.md` (40,579 bytes). No top-level `metrics.json` or
`resolved_config.yaml`. Sub-folders `baseline/` and `sweep_1` .. `sweep_5`.

- `baseline/` (3,911,077 bytes) is a single-run folder: `events.csv` 1,227, `metrics.json`
  30,003, `resolved_config.yaml` 7,072, `summary.md` 10,934, `timeseries.csv` 3,636,073,
  `plots/` (7 png).
- `sweep_N/` holds `sweep_index.csv` (1,808 to 3,115 bytes) and `run_0001` .. : sweep_1 5 points,
  sweep_2 4, sweep_3 5, sweep_4 4, sweep_5 2 (20 points). Each point is a single-run folder
  (about 4.07 MB): `events.csv`, `metrics.json` (about 42.4 to 43.4 kB), `resolved_config.yaml`
  (about 7.3 kB), `summary.md`, `timeseries.csv`, `plots/` (9 png).
- A point's `metrics.json` has top-level keys `experiment`, `timestamp_utc`, `git`, `run`,
  `baseline`, `metrics`, `comparison`: no `runs`, no `model`, no `offload`. Its
  `resolved_config.yaml` has `experiment`, `timestamp_utc`, `git`, `run`, `vehicle` (the model is
  `run.dynamics: planar_2d`).
- The offload columns of a sweep point are in `sweep_index.csv` only
  (`silo_cold_s1.status`, `.offload_kg`, `.stage1_fraction`, ... ); the offloaded run of a sweep
  point has no folder and no trajectory on disk.
- Swept axes: sweep_1 `assist.stroke_m`; sweep_2 `assist.stroke_m` (of `silo_cold_200m`);
  sweep_3 `ignition.stage1.at_depth_m`; sweep_4 and sweep_5 `ignition.stage1.at_height_m` with
  `ignition.stage1.height_method` (`event`, `closed_form`).

### 1.4 A 1-D directory

`results/silo_screening_1d/20260929T105657Z` (5,986,383 bytes): the same shape as S (three
top-level files, `plots/`, 10 run folders with `events.csv` and `timeseries.csv`), but:

- `metrics.json` top-level keys: `experiment`, `timestamp_utc`, `git`, `comparison_basis`,
  `baseline`, `runs`, `comparison`, `sensitivity`. No `model` key.
- `resolved_config.yaml` top-level keys: `experiment`, `timestamp_utc`, `git`,
  `comparison_basis`, `baseline`, `vehicle`, `runs`. No `model`, `label`, `bound_runs`, `cases`.
- `timeseries.csv` columns: `t_s, z_m, v_mps, m_kg, t_rel_release_s, thrust_N, thrust_vac_N,
  accel_felt_g, phase, stage, J_vac_mps, J_grav_mps, J_alt_mps, J_bp_mps, J_steer_mps` plus the
  six track columns (no `alt_m`, `downrange_m`, `pitch_rad`).
- `events.csv` columns: `t_s, event, phase, stage, z_m, v_mps, m_kg`.
- 1-D sweep `...105707Z`: `summary.md`, `baseline/`, `sweep_1` .. `sweep_3`; the same single-run
  point layout.

### 1.5 Telling the kinds apart (what `replay.check_replay_run_dir`, replay.py 166-195, does)

1. No `metrics.json` at the top: not a results directory (a sweep directory lands here).
2. `metrics.json` without a `runs` dict: a sweep point or the sweep's `baseline/`.
3. `metrics.json` with `runs` but `model != "planar_2d"` (a 1-D file has no `model` key at all):
   a vertical_1d experiment directory.
4. Otherwise a planar experiment directory.

All experiment timestamps under `results/` (bytes; top-level files; sub-folders):

| Directory | Bytes | Kind |
|---|---|---|
| calibration_f9_2d/20260930T100100Z | 16,841,430 | planar experiment, 8 runs |
| calibration_f9_2d/20260930T173928Z | 16,847,862 | planar experiment, 8 runs |
| guidance_trigger_2d/20260930T174950Z | 35,921,990 | sweep (`summary.md`, `baseline`, `sweep_1`) |
| silo_bridge_2d_readme/20260930T185034Z | 14,318,581 | planar experiment, 4 runs |
| silo_offload_2d/20261003T112934Z | 74,260,469 | planar experiment with offload, 19 runs |
| silo_offload_2d/20261003T112949Z | 85,489,444 | sweep, 20 points |
| silo_offload_2d_readme/20261003T112956Z | 17,635,887 | planar experiment with offload, 5 runs |
| silo_screening_1d/2026092910xxxxZ (3) | 5,986,383 each | 1-D experiment |
| silo_screening_1d/2026092910xxxxZ (3) | 16,216,571 each | 1-D sweep |
| silo_screening_2d/20260930T175743Z | 45,946,129 | planar experiment, 12 runs |
| silo_screening_2d/20260930T182453Z | 101,882,858 | sweep (`baseline`, `sweep_1` .. `sweep_3`) |

---

## 2. `timeseries.csv`

### 2.1 Columns (32, identical header in all 31 run folders of S and O)

```
t_s, t_rel_release_s, phase, stage,
alt_m, downrange_m, speed_rel_mps, speed_inertial_mps, gamma_rel_rad, pitch_rad, psi_rad, m_kg,
thrust_N, thrust_vac_N, drag_N, q_pa, mach, q_alpha_pa_rad, felt_axial_g, felt_lateral_g,
J_vac_mps, J_grav_mps, J_alt_mps, J_drag_mps, J_steer_mps, J_bp_mps,
s_m, drive_force_N, interface_force_N, drive_power_W, track_normal_g_vehicle, track_normal_g_carriage
```

Source: `metrics_planar.PLANAR_TIMESERIES_COLUMNS` (metrics_planar.py 340-348) =
4 + `PLANAR_FLIGHT_COLUMNS` (298-315, 16) + `PLANAR_QUADRATURE_COLUMNS` (331-338, 6) +
`metrics.TRACK_COLUMNS` (metrics.py 60, 6).

dtypes as pandas 3.0.6 reads them: `phase` and `stage` are `str`; everything else `float64`,
EXCEPT in `silo_failed`, where `psi_rad`, `m_kg`, `thrust_N`, `thrust_vac_N`, `J_vac_mps`,
`J_steer_mps`, `J_bp_mps` come back `int64` (the file writes `569100` and `0` with no decimal
point; numbers are written with 12 significant digits, `%.12g` style). A loader must cast to
float (`replay` does: `to_numpy(dtype=float)`).

`stage` is the text `stage1` or `stage2` (the vehicle's stage names), not a number. It switches
to `stage2` on the first COAST_STAGING row.

### 2.2 Rows, time span, phases (S)

| run | rows | t_s first..last (absolute) | t_rel first..last | phases in order |
|---|---|---|---|---|
| pad | 10,779 | -2.000 .. 536.300685 | -2.000 .. 536.300685 | HOLD, VERTICAL_RISE, KICK, GRAVITY_TURN, COAST_STAGING, LTG_BURN |
| pad__aero_bound | 10,779 | -2.000 .. 536.300685 | same | same as pad |
| pad_instant | 10,758 | 0 .. 537.300685 | 0 .. 537.300685 | VERTICAL_RISE, KICK, GRAVITY_TURN, COAST_STAGING, LTG_BURN |
| silo_cold | 10,844 | 0 .. 541.408003 | -2.607318 .. 538.800685 | ASSIST, COAST_PRE_IGN, KICK, GRAVITY_TURN, COAST_STAGING, LTG_BURN |
| silo_cold__aero_bound | 10,844 | 0 .. 541.408003 | same | same as silo_cold |
| silo_cold_lag | 10,842 | 0 .. 541.408003 | -2.607318 .. 538.800685 | same as silo_cold |
| silo_failed | 371 | 0 .. 18.296378 | -2.607318 .. 15.689059 | ASSIST, COAST |
| silo_hot_full | 10,779 | -2.000 .. 536.300685 | -4.607318 .. 533.693367 | HOLD, ASSIST, KICK, GRAVITY_TURN, COAST_STAGING, LTG_BURN |
| silo_hot_full_impinged | 10,779 | same | same | same as silo_hot_full |
| silo_hot_ramp_on_track | 10,792 | 0 .. 538.908003 | -2.607318 .. 536.300685 | ASSIST, KICK, GRAVITY_TURN, COAST_STAGING, LTG_BURN |
| silo_instant | 10,810 | 0 .. 539.908003 | -2.607318 .. 537.300685 | ASSIST, KICK, GRAVITY_TURN, COAST_STAGING, LTG_BURN |
| silo_sled_22t | 10,844 | 0 .. 541.408003 | -2.607318 .. 538.800685 | same as silo_cold |

O (rows; t_rel span):

| run | rows | t_rel first..last |
|---|---|---|
| pad | 10,779 | -2.000 .. 536.300685 |
| pad__offload_both | 10,779 | -2.000 .. 536.300685 |
| pad__offload_stage1 | 10,779 | -2.000 .. 536.300687 |
| pad__offload_stage2 | 10,743 | -2.000 .. 534.514121 |
| silo_cold | 10,844 | -2.607318 .. 538.800685 |
| silo_cold_200m | 10,896 | -5.214636 .. 538.800685 |
| silo_cold_200m_s1 | 10,590 | -5.214636 .. 523.503719 |
| silo_cold_both | 9,906 | -2.607318 .. 491.928904 |
| silo_cold_fix10pct | 10,539 | -2.607318 .. 523.567841 |
| silo_cold_fix5pct | 10,691 | -2.607318 .. 531.184263 |
| silo_cold_s1 | 10,538 (10,539 lines) | -2.607318 .. 523.503743 |
| silo_cold_s1__pad | 10,473 | -2.000 .. 521.003741 |
| silo_cold_s1_dry+2t | 10,604 | -2.607318 .. 526.831948 |
| silo_cold_s1_dry+4t | 10,674 | -2.607318 .. 530.320134 |
| silo_cold_s1_dry+8.1t | 10,829 | -2.607318 .. 538.066486 |
| silo_cold_s1_s2pre2t | 10,402 | -2.607318 .. 516.729396 |
| silo_cold_s2 | 8,624 | -2.607318 .. 427.811737 |
| silo_hot_ramp_on_track | 10,792 | -2.607318 .. 536.300685 |
| silo_hot_ramp_s1 | 10,450 | -2.607318 .. 519.242631 |

Phase names on disk across all 111 planar `timeseries.csv` under `results/` (files containing the
phase): HOLD 36, ASSIST 75, COAST_PRE_IGN 59, VERTICAL_RISE 48, KICK 110, GRAVITY_TURN 110,
COAST_STAGING 110, LTG_BURN 110, COAST 1 (silo_failed). No other name.

Clock. `t_s` is the run's absolute clock: 0 at release for a pad (the hold is -2 .. 0), 0 at
push start for a silo run (a held hot start, `silo_hot_full`, has its hold at -2 .. 0 and its
release at 2.607318). `t_rel_release_s = t_s - t_release_s` (metrics_planar.py 568).

### 2.3 Sampling step

`run.integrator.sample_dt_s: 0.05` in every run. Each phase is sampled at the multiples of
0.05 s inside it plus its two ends (`sample_trace_planar`, metrics_planar.py 537-579). Measured on
`pad`: 10,761 of the 10,772 positive steps are exactly 0.05 s; the others are the partial steps
next to a phase end (0.000685 to 0.0437 s). No negative step in any file.

### 2.4 Duplicate rows

Every boundary between integrator segments is written twice (same `t_s`, the end of one segment
and the start of the next). That is every phase boundary AND every in-phase event that restarts
the integration (`ramp_end`, the on-track `ignition`, `fairing`, `apex`). Counts: 6 per pad run,
7 per cold silo run with a ramp start (6 with the lag start, which has no `ramp_end`), 6 for the
hot runs, 5 for the instant runs, 2 for `silo_failed`.

`pad` (S), row index pair, t_rel, what differs between the two rows:

| rows | t_rel | boundary | columns that differ |
|---|---|---|---|
| 40/41 | 0.000000 | HOLD -> VERTICAL_RISE | `phase`, `felt_axial_g` 0.996476 -> 1.361658 |
| 291/292 | 12.493729 | VERTICAL_RISE -> KICK | `phase`, `pitch_rad` 1.570796 -> 1.521328, `psi_rad`, `q_alpha_pa_rad`, felt g |
| 399/400 | 17.774014 | KICK -> GRAVITY_TURN | `phase` only |
| 3072/3073 | 151.328438 | GRAVITY_TURN -> COAST_STAGING | `phase`, `stage` stage1 -> stage2, `m_kg` 161,454.396243 -> 139,254.396243, `thrust_N` 8,226,865.46 -> 0, `thrust_vac_N` 8,226,900 -> 0, `felt_axial_g` 5.1955 -> -0.0005 |
| 3294/3295 | 162.328438 | COAST_STAGING -> LTG_BURN | `phase`, `pitch_rad` 0.370044 -> 0.547881, `psi_rad` 0 -> 0.177837, `thrust_N` 0 -> 980,991.58, `thrust_vac_N` 0 -> 981,000, felt g |
| 3986/3987 | 196.807531 | LTG_BURN -> LTG_BURN (fairing) | `m_kg` 129,343.226242 -> 127,643.226242, felt g |

`silo_cold` (S):

| rows | t_rel | boundary | columns that differ |
|---|---|---|---|
| 53/54 | 0.000000 | ASSIST -> COAST_PRE_IGN | `phase`, `alt_m` 1.42e-14 -> 0.0, `drag_N` 0 -> 15,696.6, `q_pa` NaN -> 3,603.94, `mach` NaN -> 0.2254, `q_alpha_pa_rad` NaN -> 0, `felt_axial_g` 3.9965 -> -0.0028, the six track columns value -> NaN (`s_m` 100.0, `drive_force_N` 22,490,479.6, `drive_power_W` 1,725,181,053.7) |
| 65/66 | 0.500000 | COAST_PRE_IGN -> KICK | `phase`, `pitch_rad` 1.570863 -> 1.529581, `psi_rad`, `q_alpha_pa_rad`, felt g |
| 107/108 | 2.500000 | KICK -> KICK (`ramp_end`) | nothing (two identical rows) |
| 219/220 | 8.025553 | KICK -> GRAVITY_TURN | `phase` only |
| 3137/3138 | 153.828438 | GRAVITY_TURN -> COAST_STAGING | `stage`, `m_kg` 162,953.227114 -> 140,753.227114, thrust -> 0 |
| 3359/3360 | 164.828438 | COAST_STAGING -> LTG_BURN | `pitch_rad` 0.347917 -> 0.534633, thrust 0 -> 981,000 |
| 3941/3942 | 193.816497 | fairing | `m_kg` 132,420.479541 -> 130,720.479541 |

`silo_hot_ramp_on_track`: an extra identical pair at t_rel = -2.000 (the on-track `ignition`,
ASSIST -> ASSIST), and the release pair is ASSIST -> KICK. `silo_hot_full`: HOLD -> ASSIST at
t_rel = -2.607318 (`q_pa`, `mach` 0.0 -> NaN; track columns NaN -> value). `silo_failed`:
ASSIST -> COAST at 0, and an identical pair at the apex (t_rel 7.842648).

Rows that are NOT doubled: the first row of a run and the last row (the `cutoff`/`end` or
`impact`/`end` events sit on a single row).

`replay.read_series` (replay.py 365-377) sorts on `t_rel_release_s` and keeps the LAST row of
each duplicate pair. For the two mass drops that is the mass after the drop.

### 2.5 NaN by phase

| Columns | NaN in | Value elsewhere |
|---|---|---|
| `s_m`, `drive_force_N`, `interface_force_N`, `drive_power_W`, `track_normal_g_vehicle`, `track_normal_g_carriage` | every phase except ASSIST | defined on all ASSIST rows |
| `q_pa`, `mach`, `q_alpha_pa_rad` | ASSIST only (vented shaft, no air model) | 0.0 in HOLD; defined in flight |

No other column has a NaN and no column has an infinity in the runs checked in full (`pad`,
`silo_cold`, `silo_hot_ramp_on_track`, `silo_failed`, `silo_hot_full`). `pad`: the six track
columns are NaN on all 10,779 rows.

### 2.6 Column behaviour that matters for the scene

- `alt_m` is `r - r_datum` (`PlanarView.row`, phases/planar.py 234-254). In the shaft it runs
  from `track_start_altitude_m` (-100.0; -200.0 on `silo_cold_200m`) to 0; the last ASSIST row
  reads 1.42e-14, the first flight row 0.0. `s_m` runs 0 .. 100.0 (0 .. 200.0).
- `downrange_m` is 0.0 on every HOLD and ASSIST row (`EARTH_FIXED_LABELS`, phases/planar.py 171)
  and `r_datum (theta - omega_p (t - t_fs))` in flight. It goes slightly NEGATIVE: `pad` reaches
  -0.159 m during the vertical rise (the kick_start row reads -0.157654 m); `silo_failed` ends at
  -0.402578 m.
- `pitch_rad`: pi/2 in HOLD; the track angle (pi/2) in ASSIST; the thrust direction in a lit
  phase; the direction of v_rel in an unpowered phase (COAST_PRE_IGN, COAST_STAGING, COAST).
  It is unwrapped per run with `gamma_rel_rad` (`UNWRAPPED_COLUMNS`, metrics_planar.py 351).
  - Orbital runs stay inside [-5.04 deg, 90.004 deg] and need no wrapping
    (`pad` 1.517 .. 90.000 deg; `silo_cold` 1.964 .. 90.004; `silo_cold_s1` 1.489 .. 90.004;
    `silo_cold_s2` -5.044 .. 90.004: its final pitch is below the horizon).
  - It STEPS at the kick start (`pad` 90.000 -> 87.166 deg; `silo_cold` 90.004 -> 87.639;
    `silo_cold_s1` 90.004 -> 85.872; `silo_hot_ramp_on_track` 90.000 -> 86.343 at release) and at
    stage-2 ignition (`pad` 21.202 -> 31.391 deg; `silo_cold` 19.934 -> 30.632; `silo_cold_s1`
    21.199 -> 31.430; `silo_cold_s2` 16.172 -> 19.459). During KICK the pitch is constant.
  - `silo_failed`: raw range 1.570796 .. 4.712390 rad (90 .. 270 deg). The whole turn happens
    around the apex: 92.26 deg at t_rel 7.7427, 94.51 at 7.7927, 180.00 at 7.8426 (the apex,
    |v_rel| 0.0385 m/s), 265.50 at 7.8927, 267.74 at 7.9427. A rocket drawn along `pitch_rad`
    would flip end over end in about 0.2 s.
- `thrust_vac_N` and `thrust_N` in HOLD: the hold rows carry the ramp. `pad` first rows
  (t_rel, thrust_vac_N, thrust_N, m_kg): (-2.00, 0, 0, 572,354.40), (-1.95, 205,672.5, 0,
  572,352.71), (-1.90, 411,345.0, 0, 572,347.65), (-1.85, 617,017.5, 0, 572,339.22),
  (-1.80, 822,690.0, 202,590.0, 572,327.42). `thrust_N` (delivered, clamped at 0) stays 0 until
  the vacuum thrust passes the sea-level back-pressure term (620,100 N = 9 x (914.1 - 845.2) kN):
  the plume must be driven by `thrust_vac_N`, not `thrust_N`.
- Full thrust: stage 1 `thrust_vac_N` = 8,226,900 N (9 x 914.1 kN), `thrust_N` 7,606,800 N at
  the pad release (9 x 845.2 kN) rising to 8,226,865 to 8,226,889 N at MECO; stage 2
  `thrust_vac_N` = 981,000 N from the first LTG_BURN row (step start). `silo_failed`: 0 on every
  row.
- `felt_axial_g`: 0.996476 in HOLD (the clamp carries the weight; g_eff/g0), 3.996476 on every
  ASSIST row of a 3 g push (2.496476 on `silo_cold_200m`), about -0.003 in a coast in the air.
- `m_kg`: decreases in the HOLD of a hot start (`pad` 572,354.396 -> 569,656.935 kg: 2,697.461
  kg burned in the 2 s ramp); constant in a cold ASSIST.

---

## 3. `events.csv`

Columns (`PLANAR_EVENT_COLUMNS`, metrics_planar.py 380): `t_s` (absolute), `event`, `phase`,
`stage`, `alt_m`, `downrange_m`, `speed_rel_mps`, `speed_inertial_mps`, `gamma_rel_rad`, `m_kg`.
`t_s` has 12 significant digits (2.607318179 against `t_release_s` 2.6073181789953286 in
`metrics.json`), so a time after release from the two files is exact only to about 5e-12 s:
match event times to samples by tolerance.

### 3.1 S / pad (10 rows; t_release_s = 0.0)

```
t_s,event,phase,stage,alt_m,downrange_m,speed_rel_mps,speed_inertial_mps,gamma_rel_rad,m_kg
-2,ignition,HOLD,stage1,0,0,0,408.738792526,1.57079632679,572354.396243
0,release,HOLD,stage1,0,0,0,408.738792526,1.57079632679,569656.935371
12.4937285829,kick_start,VERTICAL_RISE,stage1,301.049241526,-0.157654391569,50,411.766502884,1.5715674239,535955.591371
17.7740137061,kick_end,KICK,stage1,628.767272356,9.43828290663,74.5892327112,419.141166759,1.52132762784,521712.228857
151.328437545,propellant,GRAVITY_TURN,stage1,69485.8215604,99171.0174982,2665.03179069,3049.67996229,0.401236345341,161454.396243
151.328437545,staging,COAST_STAGING,stage2,69485.8215604,99171.0174982,2665.03179069,3049.67996229,0.401236345341,139254.396243
162.328437545,ignition,LTG_BURN,stage2,80432.6079593,125813.413132,2625.50190527,3015.09732638,0.370043768089,139254.396243
196.807530921,fairing,LTG_BURN,stage2,110483.039548,212323.816172,2766.55347389,3167.08004395,0.291557609584,129343.226242
536.300685158,cutoff,LTG_BURN,stage2,199999.977256,1660290.86263,7362.70611351,7784.26177548,-1.49005924872e-08,30054.3967097
536.300685158,end,LTG_BURN,stage2,199999.977256,1660290.86263,7362.70611351,7784.26177548,-1.49005924872e-08,30054.3967097
```

Time after release = `t_s` (release at 0).

### 3.2 S / silo_cold (12 rows; t_release_s = 2.6073181789953286)

```
t_s,event,phase,stage,alt_m,downrange_m,speed_rel_mps,speed_inertial_mps,gamma_rel_rad,m_kg
0,push_start,ASSIST,stage1,-100,0,0,408.73238409,1.57079632679,573853.227114
2.607318179,release,ASSIST,stage1,0,0,76.7071704601,415.87424844,1.57079632679,573853.227114
3.107318179,ignition,KICK,stage1,37.1288008513,-0.00120269174959,71.8083206998,414.996253816,1.57086259106,573853.227114
3.107318179,kick_start,KICK,stage1,37.1288008513,-0.00120269174959,71.8083206998,414.996253816,1.57086259106,573853.227114
5.107318179,ramp_end,KICK,stage1,168.739748336,0.284640500666,64.5284094989,414.291134012,1.56327069898,571155.766242
10.632870813,kick_end,KICK,stage1,581.276559361,11.294964268,85.2320853411,420.991088938,1.52958106732,556250.804215
156.435755724,propellant,GRAVITY_TURN,stage1,75202.2481184,110154.819422,2765.92476877,3154.00913335,0.377802892096,162953.227114
156.435755724,staging,COAST_STAGING,stage2,75202.2481184,110154.819422,2765.92476877,3154.00913335,0.377802892096,140753.227114
167.435755724,ignition,LTG_BURN,stage2,85930.3828684,138050.021646,2728.7023527,3121.32526204,0.347917007982,140753.227114
196.423814814,fairing,LTG_BURN,stage2,110993.425411,213627.467757,2847.37293024,3248.57413593,0.284809550538,132420.479541
541.408003255,cutoff,LTG_BURN,stage2,199999.978844,1705290.2458,7362.70611153,7784.2617736,-1.39678464015e-08,31553.2276041
541.408003255,end,LTG_BURN,stage2,199999.978844,1705290.2458,7362.70611153,7784.2617736,-1.39678464015e-08,31553.2276041
```

After release: push_start -2.607318, release 0, ignition and kick_start 0.500000, ramp_end
2.500000, kick_end 8.025553, propellant and staging 153.828438, ignition (stage 2) 164.828438,
fairing 193.816497, cutoff and end 538.800685.

### 3.3 S / silo_hot_ramp_on_track (12 rows; t_release_s = 2.6073181789953295)

```
t_s,event,phase,stage,alt_m,downrange_m,speed_rel_mps,speed_inertial_mps,gamma_rel_rad,m_kg
0,push_start,ASSIST,stage1,-100,0,0,408.73238409,1.57079632679,574088.200989
0.607318178995,ignition,ASSIST,stage1,-94.5744409207,0,17.8672704601,409.123068752,1.57079632679,574088.200989
2.607318179,ramp_end,ASSIST,stage1,0,0,76.7071704601,415.87424844,1.57079632679,571390.740117
2.607318179,release,ASSIST,stage1,0,0,76.7071704601,415.87424844,1.57079632679,571390.740117
2.607318179,kick_start,KICK,stage1,0,0,76.7071704601,415.87424844,1.57079632679,571390.740117
10.5962821311,kick_end,KICK,stage1,730.221417834,27.1181310119,107.110745787,429.143472114,1.5069673531,549840.822447
153.935755724,propellant,GRAVITY_TURN,stage1,75956.5500573,111947.750955,2781.54226367,3170.09985907,0.374459819345,163188.200989
153.935755724,staging,COAST_STAGING,stage2,75956.5500573,111947.750955,2781.54226367,3170.09985907,0.374459819345,140988.200989
164.935755724,ignition,LTG_BURN,stage2,86654.0531304,140034.463274,2744.64779164,3137.68559344,0.344772371255,140988.200989
193.216257548,fairing,LTG_BURN,stage2,111074.664533,214202.15046,2860.45317204,3261.770886,0.283637190069,132858.843925
538.908003273,cutoff,LTG_BURN,stage2,199999.979189,1712236.80921,7362.7061111,7784.26177319,-1.3758400667e-08,31788.2014739
538.908003273,end,LTG_BURN,stage2,199999.979189,1712236.80921,7362.7061111,7784.26177319,-1.3758400667e-08,31788.2014739
```

After release: push_start -2.607318, ignition -2.000000 (5.43 m above the floor, 17.87 m/s),
ramp_end, release and kick_start all at 0, kick_end 7.988964, propellant and staging 151.328438,
ignition (stage 2) 162.328438, fairing 190.608939, cutoff and end 536.300685.

### 3.4 S / silo_failed (6 rows; t_release_s = 2.6073181789953286)

```
t_s,event,phase,stage,alt_m,downrange_m,speed_rel_mps,speed_inertial_mps,gamma_rel_rad,m_kg
0,push_start,ASSIST,stage1,-100,0,0,408.73238409,1.57079632679,569100
2.607318179,release,ASSIST,stage1,0,0,76.7071704601,415.87424844,1.57079632679,569100
2.607318179,ignition_failed,COAST,stage1,0,0,76.7071704601,415.87424844,1.57079632679,569100
10.4499662983,apex,COAST,stage1,300.647274262,-0.201362797179,0.0385048071014,408.719554505,3.14159265359,569100
18.2963775797,impact,COAST,stage1,0,-0.402578432318,76.5981921741,415.854216121,4.71238970711,569100
18.2963775797,end,COAST,stage1,0,-0.402578432318,76.5981921741,415.854216121,4.71238970711,569100
```

After release: push_start -2.607318, release and ignition_failed 0, apex 7.842648 (300.65 m),
impact and end 15.689059 (altitude 0, the mouth level, 0.40 m west of it, 76.60 m/s).
`gamma_rel_rad` is unwrapped (pi at the apex, 3 pi/2 at impact). `m_kg` reads back as `int64`.

### 3.5 O / silo_cold_s1 (12 rows; t_release_s = 2.6073181789953286)

```
t_s,event,phase,stage,alt_m,downrange_m,speed_rel_mps,speed_inertial_mps,gamma_rel_rad,m_kg
0,push_start,ASSIST,stage1,-100,0,0,408.73238409,1.57079632679,531091.488206
2.607318179,release,ASSIST,stage1,0,0,76.7071704601,415.87424844,1.57079632679,531091.488206
3.107318179,ignition,KICK,stage1,37.1285369713,-0.00120268044619,71.8072876335,414.996075112,1.57086259108,531091.488206
3.107318179,kick_start,KICK,stage1,37.1285369713,-0.00120268044619,71.8072876335,414.996075112,1.57086259108,531091.488206
5.107318179,ramp_end,KICK,stage1,169.330938049,0.562054113793,65.4986554002,414.887255205,1.55650715397,528394.027334
10.5556566799,kick_end,KICK,stage1,596.460658911,21.0707599389,91.9506396713,425.399123226,1.49875701335,513697.347409
141.138811674,propellant,GRAVITY_TURN,stage1,69300.1312149,99243.2414222,2665.47577848,3050.11890797,0.401188370014,161454.396243
141.138811674,staging,COAST_STAGING,stage2,69300.1312149,99243.2414222,2665.47577848,3050.11890797,0.401188370014,139254.396243
152.138811674,ignition,LTG_BURN,stage2,80247.5208905,125891.37769,2625.94728452,3015.5365947,0.370000067587,139254.396243
186.857800743,fairing,LTG_BURN,stage2,110492.874845,213043.365712,2768.08900153,3168.66578516,0.291071687368,129274.26715
526.111060791,cutoff,LTG_BURN,stage2,199999.999247,1660430.87212,7362.70608608,7784.26174946,-5.27129683274e-10,30054.3962777
526.111060791,end,LTG_BURN,stage2,199999.999247,1660430.87212,7362.70608608,7784.26174946,-5.27129683274e-10,30054.3962777
```

After release: push_start -2.607318, release 0, ignition and kick_start 0.500000, ramp_end
2.500000, kick_end 7.948339, propellant and staging 138.531493, ignition (stage 2) 149.531493,
fairing 184.250483, cutoff and end 523.503743.

### 3.6 O / pad__offload_stage1 (10 rows; t_release_s = 0.0)

```
t_s,event,phase,stage,alt_m,downrange_m,speed_rel_mps,speed_inertial_mps,gamma_rel_rad,m_kg
-2,ignition,HOLD,stage1,0,0,0,408.738792526,1.57079632679,572354.396243
0,release,HOLD,stage1,0,0,0,408.738792526,1.57079632679,569656.935371
12.4937285829,kick_start,VERTICAL_RISE,stage1,301.049241526,-0.157654391569,50,411.766502884,1.5715674239,535955.591371
17.7740278155,kick_end,KICK,stage1,628.76836396,9.4375136983,74.589301486,419.140884077,1.52133173355,521712.190798
151.328437545,propellant,GRAVITY_TURN,stage1,69491.0615638,99165.5158691,2664.98879008,3049.62802302,0.401302390956,161454.396243
151.328437545,staging,COAST_STAGING,stage2,69491.0615638,99165.5158691,2664.98879008,3049.62802302,0.401302390956,139254.396243
162.328437545,ignition,LTG_BURN,stage2,80439.4407605,125806.705568,2625.45256698,3015.03982558,0.37011003979,139254.396243
196.792534323,fairing,LTG_BURN,stage2,110482.236246,212274.572564,2766.42809668,3166.94660173,0.291635222481,129347.537082
536.30068678,propellant,LTG_BURN,stage2,200000.185769,1660270.67972,7362.70566751,7784.26134284,7.39218925729e-08,30054.3962435
536.30068678,end,LTG_BURN,stage2,200000.185769,1660270.67972,7362.70566751,7784.26134284,7.39218925729e-08,30054.3962435
```

The run ends on a second `propellant` row (stage 2 ran dry; status `short_of_orbit`), not on
`cutoff`. A reader that looks for "the `propellant` row" to find MECO must filter on
`stage == "stage1"`.

### 3.7 Observations on the event rows

- Event names on disk, all 111 planar `events.csv` under `results/` (count of rows): `release`
  111, `end` 111, `ignition` 220, `kick_start` 110, `kick_end` 110, `propellant` 112, `staging`
  110, `fairing` 110, `cutoff` 108, `push_start` 75, `ramp_end` 66, `ignition_height` 4,
  `ignition_failed` 1, `apex` 1, `impact` 1. There is NO `liftoff` row in any file (it is logged
  only when a hold is extended past release because thrust is below weight).
- A pad run has no `ramp_end` row: its ramp ends at the release instant inside the HOLD, which is
  not integrated as a lit phase. The end of the ramp is `t_ign_rel_release_s_stage1 +
  t_startup_s_stage1` (-2.0 + 2.0 = 0).
- The `phase` column of an event row is not a consistent "before" or "after" label: `release`
  carries HOLD, ASSIST or RELEASE (2 rows on disk, the instant pads); `kick_start` carries
  VERTICAL_RISE on a pad (48 rows) and KICK when the kick starts at ignition (62 rows);
  `ignition` (stage 1) carries HOLD (36), ASSIST (7), KICK (53) or VERTICAL_RISE (14);
  `ramp_end` carries ASSIST (4), KICK (50) or VERTICAL_RISE (12); `propellant` carries
  GRAVITY_TURN (110, MECO) or LTG_BURN (2, a stage-2 depletion). Key on the event name and the
  `stage` column.
- Several events share one time: `ignition` + `kick_start` (cold silo); `ramp_end` + `release` +
  `kick_start` (hot ramp); `propellant` + `staging`; `cutoff` + `end`.
- `staging` row: phase COAST_STAGING, stage `stage2`, mass AFTER the stage-1 drop. `propellant`
  (stage 1) row: the mass BEFORE. Difference = 22,200.0 kg on every run of S and O except the
  three penalty rows (24,200.0, 26,200.0, 30,300.0 kg), each equal to that run's stage-1 dry
  mass.

### 3.8 The fairing row's mass convention

On all five of the requested runs that drop a fairing, the `fairing` row carries the mass BEFORE
the drop, and the metric `fairing_drop` is `"in the stage-2 burn (heating event)"`
(`FAIRING_IN_BURN`, metrics_planar.py 393):

| run | event `m_kg` | timeseries rows at that time (before, after) | `fairing_t_s` (metric) | event t after release |
|---|---|---|---|---|
| S pad | 129,343.226242 | 129,343.226242, 127,643.226242 | 196.8075309210838 | 196.807531 |
| S silo_cold | 132,420.479541 | 132,420.479541, 130,720.479541 | 193.81649663536862 | 193.816497 |
| S silo_hot_ramp_on_track | 132,858.843925 | 132,858.843925, 131,158.843925 | 190.60893936946815 | 190.608939 |
| O silo_cold_s1 | 129,274.26715 | 129,274.26715, 127,574.26715 | 184.25048256373196 | 184.250483 |
| O pad__offload_stage1 | 129,347.537082 | 129,347.537082, 127,647.537082 | 196.79253432259836 | 196.792534 |

The two timeseries rows differ by exactly the fairing mass, 1,700.0 kg. `silo_failed` has no
`fairing` row and `fairing_drop: null`.

The same holds for every one of the 30 fairing rows of S and O, and across all of `results/`:
110 `fairing` rows, all in phase LTG_BURN, all with the form `FAIRING_IN_BURN` (110 planar run
records; the 111th is `silo_failed` with null). No recorded run on disk exercises
`FAIRING_AT_IGNITION`, `FAIRING_AT_STAGING` or `FAIRING_KEPT`; those three cases of section 5.8
item 1 can only be tested with synthetic fixtures.

The fairing items of a run's metrics are three keys (`fairing_items`, metrics_planar.py 669-694):
`fairing_drop` (one of the four strings, or null), `fairing_t_s` (after release), `fairing_alt_m`.

---

## 4. `metrics.json`

### 4.1 Top-level keys

| Key | S | O |
|---|---|---|
| `experiment`, `timestamp_utc` | strings | strings |
| `git` | `{hash: 7ad381f227a9, dirty: false, error: null}` | `{hash: b3150c1754ee, dirty: false, error: null}` |
| `comparison_basis` | string | string |
| `baseline` | `pad` | `pad` |
| `runs` | dict, 10 | dict, 4 (`pad`, `silo_cold`, `silo_hot_ramp_on_track`, `silo_cold_200m`) |
| `comparison` | dict, 9 (every run but the baseline) | dict, 3 |
| `sensitivity` | list, 24 | list, 0 |
| `model` | `planar_2d` | `planar_2d` |
| `label` | null | null |
| `search_budget_id` | `a17a0160...` | the same |
| `bounds` | list, 1 | list, 0 |
| `cases` | dict, 0 | dict, 0 |
| `offload` | absent | dict, 12 keys |

`bounds[0]` (S) keys: `bound` (`aero_bound`), `of` (`silo_cold`), `overrides`
(`{"vehicle.aero.reference_area_m2": 21.24}`), `run` (`silo_cold__aero_bound`),
`paired_baseline` (`pad__aero_bound`), `metrics` (150 keys), `paired_baseline_metrics` (133
keys), `comparison_vs_paired_baseline`, `comparison_vs_baseline`.

### 4.2 Per-run keys the scene and the results panel need

A run record has 133 keys (pad, S), 139 (pad, O), 150 or 151 (assisted, S), 159 (assisted, O),
163 (an offload run: +4). Values below: S for `pad`, `silo_cold`, `silo_failed`; O for
`silo_cold_s1`.

| Key | pad | silo_cold | silo_failed | silo_cold_s1 (O) |
|---|---|---|---|---|
| `status` | inserted | inserted | impact | inserted |
| `trace_status` | inserted | inserted | impact | inserted |
| `figure_of_merit` | payload | payload | none | offload |
| `search_status` | ok | ok | `skipped (end: impact (ignition stage1 fails))` | ok |
| `payload_kg` | 26,054.396243494975 | 27,553.227114190096 | null | 26,054.396243494975 |
| `liftoff_mass_kg` | 572,354.3962434949 | 573,853.2271141901 | 569,100.0 | 531,091.4882061621 |
| `t_release_s` (absolute) | 0.0 | 2.6073181789953286 | 2.6073181789953286 | 2.6073181789953286 |
| `hold_duration_s` | 2.0 | null | null | null |
| `push_time_s` | key absent | 2.6073181789953286 | 2.6073181789953286 | 2.6073181789953286 |
| `t_ign_rel_release_s_stage1` | -2.0 | 0.5000000000000009 | null | 0.5000000000000009 |
| `t_ign_rel_release_s_stage2` | 162.3284375445184 | 164.82843754451855 | null | 149.53149349518756 |
| `startup_kind_stage1`, `t_startup_s_stage1` | ramp, 2.0 | ramp, 2.0 | ramp, 2.0 | ramp, 2.0 |
| `kick_regime` | after_vertical_rise | at_first_lit_instant | none | at_first_lit_instant |
| `kick_t_s`, `kick_duration_s` | 12.4937, 5.2803 | 0.5, 7.5256 | null, null | 0.5, 7.4483 |
| `speed_at_kick_mps` | 50.0 | 71.808 | null | 71.807 |
| `stage1_burnout_t_s` | 151.3284375445184 | 153.82843754451855 | null | 138.53149349518756 |
| `stage1_burnout_mass_kg` | 161,454.396 | 162,953.227 | null | 161,454.396 |
| `fairing_drop` | in the stage-2 burn (heating event) | the same | null | the same |
| `fairing_t_s` | 196.8075309210838 | 193.81649663536862 | null | 184.25048256373196 |
| `fairing_alt_m` | 110,483.04 | 110,993.43 | null | 110,492.87 |
| `final_t_s` | 536.3006851579923 | 538.8006850756861 | 15.689059400699954 | 523.5037426115222 |
| `final_alt_m`, `final_downrange_m` | 199,999.977, 1,660,290.86 | 199,999.979, 1,705,290.25 | 0.0, -0.4026 | 199,999.999, 1,660,430.87 |
| `apex_alt_m`, `apex_t_s` | null | null | 300.6472742622718, 7.842648119271583 | null |
| `impact_t_s`, `impact_speed_mps` | null | null | 15.689059400699954, 76.598 | null |
| `max_q_pa` | 37,191.382881367266 | 31,237.64473870668 | 3,603.9439283215665 | 38,438.46630938909 |
| `max_q_time_s` | 65.75150361445013 | 57.60962050637106 | 0.0 | 53.49899127111228 |
| `max_q_alt_m`, `max_q_mach` | 11,019.07, 1.5322 | 11,019.07, 1.4042 | 0.0, 0.2254 | 11,019.07, 1.5577 |
| `peak_felt_axial_g` (run-wide) | 5.1954747 (GRAVITY_TURN, 151.33 s) | 5.1479431 (GRAVITY_TURN, 153.83 s) | 3.9964760 (ASSIST, -2.607 s) | 5.1954619 (GRAVITY_TURN, 138.53 s) |
| `peak_felt_axial_g_flight` | 5.1954747 | 5.1479431 | -7.6e-10 | 5.1954619 |
| `felt_g_track_peak` | key absent | 3.9964760359053533 | 3.9964760359053533 | 3.9964760359053533 |
| `peak_interface_force_N` (= `interface_force_peak_N`) | 0.0 | 22,490,479.616787788 | 22,304,190.941435643 | 20,814,559.76159103 |
| `drive_force_peak_N` | key absent | 22,490,479.6 | 22,304,190.9 | 20,814,559.8 |
| `peak_drive_power_W` (= `drive_power_peak_W`) | 0.0 | 1,725,181,053.6951025 | 1,710,891,376.5200732 | 1,596,625,983.6850023 |
| `drive_energy_J` | key absent (`assist_energy_J` 0.0) | 2,249,047,961.68 (624.74 kWh) | 2,230,419,094.14 | 2,081,455,976.16 |
| `electrical_energy_J` | 0.0 | 4,498,095,923.36 | 4,460,838,188.29 | 4,162,911,952.32 |
| `exit_speed_mps` | key absent | 76.70717046013367 | 76.70717046013367 | 76.70717046013367 |
| `facility_length_m` | 0.0 | 160.00000000000006 | 160.00000000000006 | 160.00000000000006 |
| `braking_distance_m` | 0.0 | 60.00000000000004 | 60.00000000000004 | 60.00000000000004 |
| `track_start_altitude_m` | key absent | -100.0 | -100.0 | -100.0 |
| `carriage_mass_kg` | key absent | 0.0 | 0.0 | 0.0 |
| `stroke_m` | key absent | KEY ABSENT (pre-SP1) | KEY ABSENT | 100.0 |
| `net_accel_mps2`, `net_accel_g` | key absent | KEY ABSENT (pre-SP1) | KEY ABSENT | 29.41995, 3.0 |
| `ramp_start_t_rel_release_s` | KEY ABSENT in S (O: -2.0) | KEY ABSENT | KEY ABSENT | 0.5000000000000009 |
| `ramp_start_alt_m` | (O: 0.0) | - | - | 37.12853697128594 |
| `ramp_start_depth_m` | (O: null) | - | - | null |
| `ramp_start_height_m` | (O: null) | - | - | 37.12853697128594 |
| `ramp_start_speed_mps` | (O: 0.0) | - | - | 71.80728763353207 |
| `ramp_start_phase` | (O: HOLD) | - | - | KICK |
| `gamma_star_rad` | 0.4012363454 (22.989 deg) | 0.3778028919 (21.647 deg) | null | 0.4011883693 (22.986 deg) |
| `flags` | [] | [] | [] | [] |
| `run_checks` | ok | ok | ok | ok |
| `failed_stage` | absent | absent | stage1 | absent |
| `offload_mode`, `offload_kg`, `offload_status`, `offload_reference_payload_kg` | absent | absent | absent | stage1, 41,262.90803733282, ok, 26,054.396243494975 |

Notes.

- A pad record has no track keys at all: `exit_speed_mps`, `push_time_s`, `felt_g_track_peak`,
  `drive_force_peak_N`, `drive_energy_J`, `track_start_altitude_m`, `carriage_mass_kg`,
  `stroke_m`, `net_accel_g` are ABSENT (not null). It has the zero-valued pad set instead
  (`assist_energy_J`, `electrical_energy_J`, `peak_drive_power_W`, `peak_interface_force_N`,
  `braking_distance_m`, `facility_length_m`, `peak_track_normal_g` all 0.0).
- Time keys. After release: `t_ign_rel_release_s_stage1/2`, `stage1_burnout_t_s`,
  `stage2_end_t_s`, `fairing_t_s`, `final_t_s`, `apex_t_s`, `impact_t_s`, `kick_t_s`,
  `max_q_time_s`, `peak_*_t_s`, `felt_g_track_peak_t_s` (-2.607), `ramp_start_t_rel_release_s`,
  `t_flight_start_s` (0.0). Absolute (the run clock): `t_release_s` AND `drive_power_peak_t_s`
  (2.6073181789953286 on `silo_cold`, 5.214636357990658 on `silo_cold_200m`: the release
  instant, which would read 0.0 after release; metrics_planar.py 1012). Durations:
  `hold_duration_s`, `hold_extension_s`, `kick_duration_s`, `push_time_s` (metrics_planar.py 996
  writes `trace.t_release_s`), `t_startup_s_stage1`.
- Requested ramp start. The five keys of `RAMP_START_REQUEST_METRICS` (metrics_planar.py
  1041-1047: `ramp_start_trigger`, `ramp_start_requested_t_s`, `ramp_start_requested_depth_m`,
  `ramp_start_requested_speed_mps`, `ramp_start_requested_height_m`) are written only for a
  non-time trigger. No run of S or O has them (all are time-stated). On disk they exist in 11
  records, all sweep points of W (sweep_3 depth, sweep_4 `height_event`, sweep_5
  `height_closed_form`). The six achieved keys exist in 45 records (every run of O, of W and of
  `silo_offload_2d_readme`), and in no record of S.

### 4.3 Keys missing in S (recorded before SP1)

- Top level: `offload`.
- Assisted runs (150 keys against 159): `stroke_m`, `net_accel_mps2`, `net_accel_g`, and the six
  `ramp_start_*` keys.
- Pad runs (133 against 139): the six `ramp_start_*` keys.
- Nothing is present in S that is absent in O.

Fallbacks available in S: `resolved_config.yaml` `runs.<name>.run.assist.stroke_m` (100) and
`.net_accel_g` (3.0) (`replay.push_accel_g`, replay.py 519-526, already does the second); the
ramp start from the stage-1 `ignition` event row (the first `ignition` row with
`stage == "stage1"`) and `t_ign_rel_release_s_stage1`, which S does have.
A config may state the push by `exit_speed_mps` instead of `net_accel_g`
(O `silo_cold_200m`: `assist: {model: constant_accel, exit_speed_mps: 76.70717046013364,
stroke_m: 200, ...}`); then only the metric `net_accel_g` (1.4999999999999998) gives the
acceleration directly (else a = v^2 / (2 L)).

### 4.4 The offload record (`metrics.json` `offload`, O only)

Keys, in order: `basis`, `reference`, `reference_payload_kg`, `caveats`, `energy_inputs`,
`pad_control`, `pad_controls`, `cases`, `sensitivity_basis`, `sensitivity`, `notes`, `runs`.

- `basis`: "Offload basis: propellant saved at fixed payload. Different vehicles (each run's own
  propellant load, tanks partly filled, dry masses unchanged unless a row says so), the same
  payload and the same orbit: every offload is measured at the reference payload P_ref, the
  full-load pad baseline's payload capacity P* on the same vehicle and orbit (sweep-optimized
  guidance, the shared search budget)"
- `reference`: `pad`; `reference_payload_kg`: 26054.396243494975; `pad_control`: true;
  `notes`: [].
- `energy_inputs`: `fuel_mass_kg` {stage1: 123500.0, stage2: 32299.999999999996},
  `fuel_mass_provenance`, `heating_value_J_per_kg` 43030000.0, `heating_value_provenance`.
- `pad_controls`: list of 3; `cases`: list of 11; `sensitivity`: list of 8; `runs`: dict of 15.

`caveats`, quoted in full (7 strings):

0. "calibration: the vehicle generic_f9_class_2d carries 26,054 kg in its calibration run against
   the published 22,800 kg, +14.3% high, a documented calibration result
   (docs/findings/CAL-f9-leo-2d); read every offload as a difference between runs of the vehicle
   model, not as a Falcon 9 figure"
1. "guidance is sweep-optimized (a shared gamma* grid refined per run, not optimal control) and
   the engines never throttle"
2. "no structural mass is charged for the push load (the fully fuelled stack rides the push at
   the net acceleration plus g); the penalty rows add an assumed stage-1 dry mass, a parametric
   assumption, not a sized structure"
3. "the drive is a prescribed constant acceleration with no force or power limit, the carriage is
   massless unless the variant states a carriage mass, and the shaft is vented (no air drag in
   it)"
4. "max-Q of each offloaded run is reported beside the pad's: a lighter stack climbs faster, and
   no max-Q limit constrains it (there is no throttle model)"
5. "the tanks are partly filled: dry masses and tank structure unchanged, the mixture ratio kept,
   no ullage, centre-of-gravity or tank-mass effect"
6. "stage 1 is the headline: stage-2 and both-stage offloads are a property of the vehicle model
   (stage-2 propellant is worth about nothing at the margin on the gate vehicle), quoted net of
   the pad control (the gross rows beside them are not a saving of the assist); a stage-1-only
   offload is not assumed to maximise the total tonnes ('both' may remove more, its stage-2 share
   riding about free), and stage 1 stays the only headline either way"

Case record keys (41): `name`, `of`, `kind`, `mode`, `fixed_key`, `fixed_fraction`, `run`,
`status`, `run_status`, `reference_payload_kg`, `quoted_offload_kg`, `quoted_basis`,
`offload_kg`, `stage2_preoffload_kg`, `stage1_dry_mass_added_kg`, `assumed_penalty`,
`stage1_offload_kg`, `stage2_offload_kg`, `total_offload_kg`, `stage1_load_kg`,
`stage2_load_kg`, `total_load_kg`, `stage1_fraction`, `stage2_fraction`, `total_fraction`,
`payload_kg`, `payload_delta_kg`, `solve`, `verification`, `pad_control_offload_kg`,
`net_offload_kg`, `vs_pad`, `decomposition`, `decomposition_status`, `release_speed_mps`,
`screening_offload_kg`, `screening_ratio`, `beats_screening`, `paired_pad`, `energy`, `flags`.

The full case record of `silo_cold_s1` (`offload.cases[0]`; the two large nested blocks are
listed by key):

```
name: silo_cold_s1            of: silo_cold          kind: solve       mode: stage1
fixed_key: null               fixed_fraction: null   run: silo_cold_s1
status: ok                    run_status: inserted
reference_payload_kg: 26054.396243494975
quoted_offload_kg: 41262.90803733282
quoted_basis: "x* at P_ref, gross: stage 1, the headline"
offload_kg: 41262.90803733282
stage2_preoffload_kg: 0.0     stage1_dry_mass_added_kg: 0.0     assumed_penalty: false
stage1_offload_kg: 41262.90803733282   stage2_offload_kg: 0.0   total_offload_kg: 41262.90803733282
stage1_load_kg: 410900.0      stage2_load_kg: 107500.0          total_load_kg: 518400.0
stage1_fraction: 0.10042080320596938   stage2_fraction: 0.0     total_fraction: 0.07959665902263276
payload_kg: 26054.396243494975         payload_delta_kg: 0.0
solve: {status: ok, offload_kg: 41262.90803733282, root_kg: 41262.90803733282, load_kg: 410900.0,
        fraction_of_load: 0.10042080320596938, gamma_star_rad: 0.4011883692799067,
        m_res_kg: 3.424752503633499e-05, dv_margin_mps: 3.888849378645963e-06,
        dv_shortfall_mps: null, n_evaluations: 42, failure_kind: null, failure_message: null,
        flags: [], evaluations: [20 records {search, offload_kg, m_res_kg, dv_margin_mps, failure}]}
verification: {status: ok, payload_kg: 26054.404695649962, delta_kg: 0.008452154987026006,
               tolerance_kg: 2.6054396243494975, passed: true, run: silo_cold_s1}
pad_control_offload_kg: 0.0   net_offload_kg: 41262.90803733282
vs_pad: {liftoff_mass_kg: 531091.4882061621, pad_liftoff_mass_kg: 572354.3962434949,
         delta_liftoff_mass_kg: -41262.90803733282,
         stage1_burnout_t_s: 138.53149349518756, pad_stage1_burnout_t_s: 151.3284375445184,
         delta_stage1_burnout_t_s: -12.796944049330847,
         max_q_pa: 38438.46630938909, pad_max_q_pa: 37191.382881367266,
         delta_max_q_pa: 1247.083428021826,
         peak_felt_axial_g_flight: 5.195461906331904, pad_peak_felt_axial_g_flight: 5.1954747362886655,
         delta_peak_felt_axial_g_flight: -1.282995676188392e-05,
         max_q_above_pad: true, speed_at_release_mps: 76.70717046013367,
         felt_g_track_peak: 3.9964760359053533, peak_interface_force_N: 20814559.76159103,
         facility_length_m: 160.00000000000006, electrical_energy_J: 4162911952.3182073}
decomposition: dict of 48 keys (xv_variant, xv_baseline, xv_payload_kg, xv_gamma_star_rad, ...,
               xv_offload_kg, xv_stage1_offload_kg, ..., in m/s and in kg)
decomposition_status: explained
release_speed_mps: 76.70717046013367
screening_offload_kg: 14976.603619194531   screening_ratio: 2.7551579174098495   beats_screening: true
paired_pad: {run: silo_cold_s1__pad, status: inserted, payload_kg: 24652.367997256966,
             payload_delta_vs_reference_kg: -1402.0282462380092, assisted_run: silo_cold_s1,
             assisted_payload_kg: 26054.404695649962, payload_delta_kg: 1402.0366983929962,
             screening_status: ok, comparison: dict of 165 keys}
energy: {fuel_fraction_per_stage: [0.3005597468970552, 0.30046511627906974],
         fuel_removed_per_stage_kg: [12401.969195937218, 0.0],
         oxidizer_removed_per_stage_kg: [28860.9388413956, 0.0],
         fuel_removed_kg: 12401.969195937218, oxidizer_removed_kg: 28860.9388413956,
         heating_value_J_per_kg: 43030000.0, heat_J: 533656734501.17847, heat_kWh: 148237.9818058829,
         electrical_energy_J: 4162911952.3182073, electrical_energy_kWh: 1156.364431199502,
         heat_to_electricity_ratio: 128.19313514521974, ratio_label: "not an efficiency claim",
         excludes: [4 strings]}
flags: []
```

Only `silo_cold_s1` has a `paired_pad`; the other ten cases have `paired_pad: null`.

All eleven cases:

| name | of | kind | mode | offload_kg | S1 dry added | S2 pre-offload | stage1_fraction | payload_kg | net_offload_kg |
|---|---|---|---|---|---|---|---|---|---|
| silo_cold_s1 | silo_cold | solve | stage1 | 41,262.908 | 0 | 0 | 0.100421 | 26,054.396 | 41,262.908 |
| silo_cold_s2 | silo_cold | solve | stage2 | 31,904.271 (quoted 31,390.714) | 0 | 0 | 0.0 | 26,054.396 | 31,390.714 |
| silo_cold_both | silo_cold | solve | both | 46,168.156 | 0 | 0 | 0.089059 | 26,054.396 | 46,168.156 |
| silo_cold_s1_s2pre2t | silo_cold | solve | stage1 | 40,768.527 | 0 | 2,000 | 0.099218 | 26,054.396 | 40,768.527 |
| silo_cold_s1_dry+2t | silo_cold | solve | stage1 | 32,285.203 | 2,000 | 0 | 0.078572 | 26,054.396 | 32,285.203 |
| silo_cold_s1_dry+4t | silo_cold | solve | stage1 | 22,875.961 | 4,000 | 0 | 0.055673 | 26,054.396 | 22,875.961 |
| silo_cold_s1_dry+8.1t | silo_cold | solve | stage1 | 1,980.477 | 8,100 | 0 | 0.004820 | 26,054.396 | 1,980.477 |
| silo_cold_fix5pct | silo_cold | fixed (`stage1_fraction` 0.05) | stage1 | 20,545.0 | 0 | 0 | 0.05 | 26,837.559 | null |
| silo_cold_fix10pct | silo_cold | fixed (0.1) | stage1 | 41,090.0 | 0 | 0 | 0.1 | 26,061.196 | null |
| silo_hot_ramp_s1 | silo_hot_ramp_on_track | solve | stage1 | 46,013.437 | 0 | 0 | 0.111982 | 26,054.396 | 46,013.437 |
| silo_cold_200m_s1 | silo_cold_200m | solve | stage1 | 41,262.971 | 0 | 0 | 0.100421 | 26,054.396 | 41,262.971 |

All have `status: ok`, `run_status: inserted`, `decomposition_status: explained`. Flags are empty
on every case except `silo_cold_s2`.

Flags of `silo_cold_s2` (the same 4 strings on `offload.cases[1].flags` and
`offload.runs.silo_cold_s2.flags`):

1. "offload: (P = offload x) P1_backoff: the P1 payload search backed off 3 time(s) from
   evaluations that failed at P = 32000, 28000 kg (nonconverged)"
2. "offload: (P = offload x) refine: gamma* = 0.400453089 rad is infeasible only by the
   direct-root rule"
3. "offload: (P = offload x) refine: the first optimum 0.314261631 rad ended within gamma_xatol
   of an interior edge of [0.314159265, 0.453785606] rad; the window was shifted once to
   [0.244448461, 0.384074801] rad, where the search ended at 0.305231777 rad"
4. "offload: offload_verify_mismatch: the payload search of the vehicle offloaded by 31904.3 kg
   ended 'ok' with P* = 26069.8 kg, +15.3595 kg from P_ref (tolerance 2.60544 kg)"

Pad control records (`offload.pad_controls`, 16 keys each: `mode`, `run`, `status`,
`reference_payload_kg`, `offload_kg`, `fraction_of_load`, `m_res_kg`, `dv_margin_mps`,
`slope_kg_per_kg`, `bound_kg`, `within_bound`, `resolution_effect`, `consistency`, `solve`,
`verification`, `flags`):

| mode | run | status | offload_kg | m_res_kg | slope_kg_per_kg | bound_kg | resolution_effect | consistency | verification | flags |
|---|---|---|---|---|---|---|---|---|---|---|
| stage1 | pad__offload_stage1 | no_offload | 0.0 | -0.0016376905186916701 | 0.030906 | 1.6177993622441336 | true | pass | null | [] |
| stage2 | pad__offload_stage2 | ok | 513.5564707732123 | 6.1e-06 | 0.003147 | null | false | n/a | passed (delta 0.2306 kg, tol 2.6054) | 1 (`search_vs_final_payload`: 513.443 against 513.556 kg) |
| both | pad__offload_both | ok | 0.0 (root_kg 0.025) | 0.00057 | 0.025202 | null | false | n/a | passed (delta 0.0) | [] |

Their recorded runs in `offload.runs`:

| run | status | figure_of_merit | search_status | offload_kg | payload_kg | liftoff_mass_kg | recorded_m_res_kg |
|---|---|---|---|---|---|---|---|
| pad__offload_stage1 | short_of_orbit | offload | no_offload | 0.0 | 26,054.396 | 572,354.396 | -0.0016376905 |
| pad__offload_stage2 | inserted | offload | ok | 513.556 | 26,054.396 | 571,840.840 | 6.1e-06 |
| pad__offload_both | inserted | offload | ok | 0.0 | 26,054.396 | 572,354.396 | 0.00057 |

Other `offload.runs`: `silo_cold_s1__pad` (figure `payload`, payload 24,652.368 kg, liftoff
529,689.460, no offload keys set: `offload_mode` null), `silo_cold_fix5pct` and
`silo_cold_fix10pct` (figure `payload`, payload 26,837.559 and 26,061.196 kg, `offload_*` null:
a fixed case's recorded run is its own payload search), and the eight solved cases (figure
`offload`, payload = P_ref).

Statuses on disk (all 111 planar run records under `results/`): `inserted` 108,
`short_of_orbit` 2, `impact` 1. `figure_of_merit`: `payload` 96, `offload` 14, `none` 1.

---

## 5. `resolved_config.yaml`

### 5.1 Top-level keys

S: `experiment`, `timestamp_utc`, `git`, `comparison_basis`, `baseline`, `vehicle`, `runs` (10),
`model`, `label`, `bound_runs` (2), `cases` (0). O: the same plus `offload_runs` (15);
`bound_runs` and `cases` are empty dicts. Written by `results_io._resolved_config_dict`
(results_io.py 590-622) and `_run_entry` (625-631).

### 5.2 The top-level `vehicle` block (identical in S and O; `name: generic_f9_class_2d`)

Every quantity is a mapping `{value, source}` or `{value, assumed: true, note}`; plain scalars
only for `kind`, `trigger`, `interpolation`.

| Path | value | form |
|---|---|---|
| `stages[0].name` | stage1 | scalar |
| `stages[0].dry_mass_t` | 22.2 | value + source |
| `stages[0].propellant_mass_t` | 410.9 | value + source (287.4 LOX + 123.5 RP-1) |
| `stages[0].engine.count` | 9 | value + source |
| `stages[0].engine.thrust_vac_kN` | 914.1 (per engine) | value + source |
| `stages[0].engine.thrust_sl_kN` | 845.2 (per engine) | value + source |
| `stages[0].engine.isp_vac_s` | 311 | value + source |
| `stages[0].startup` | `kind: ramp`, `t_ramp_s: {value: 2.0, assumed: true, note}` | |
| `stages[0].coast_before_ignition_s` | 0.0 | value + assumed |
| `stages[1].name` | stage2 | scalar |
| `stages[1].dry_mass_t` | 4.0 | value + source |
| `stages[1].propellant_mass_t` | 107.5 | value + source (75.2 LOX + 32.3 RP-1) |
| `stages[1].engine.count` | 1 | value + source |
| `stages[1].engine.thrust_vac_kN` | 981 | value + source |
| `stages[1].engine.isp_vac_s` | 348 | value + source |
| `stages[1].engine.exit_area_m2` | 8.6 | value + assumed |
| `stages[1].startup` | `kind: step` | |
| `stages[1].coast_before_ignition_s` | 11.0 | value + source |
| `fairing_mass_t` | 1.7 | value + source |
| `payload_mass_t` | 22.8 | value + source |
| `fairing_drop` | `trigger: free_molecular_heating`, `limit_W_m2: {value: 1135, source}` | |
| `screening.stage_isp_eff_s` | [295 (assumed), 348 (source)] | list of mappings |
| `aero.reference_area_m2` | 10.52 | value + source |
| `aero.cd_scale` | 1.0 | value + assumed |
| `aero.interpolation` | pchip | scalar |
| `aero.cd_mach` | `mach` (23 values, 0 .. 4.5), `cd` (23 values, 0.46 .. 0.22), `assumed: true`, `note` | |

Stage 1 has no `exit_area_m2` (it states `thrust_sl_kN`); stage 2 has no `thrust_sl_kN`.
`stages` is a LIST (index 0 and 1), not a dict keyed by stage name.

### 5.3 A run entry

Every entry under `runs`, `bound_runs`, `cases`, `offload_runs` has `run`; it has `vehicle` only
when the run's vehicle differs from the top-level block. `run` keys: `name`, `dynamics`, `site`,
`planar`, `assist`, `ignition`, `end`, `integrator`.

`runs.silo_cold.run` (O; S is equal), with the long `planar.search` and `planar.checks` blocks
shortened:

```yaml
run:
  name: silo_cold
  dynamics: planar_2d
  site: {latitude_deg: 28.5, azimuth_deg: 90, include_rotation: true}
  planar:
    guidance:
      kick: {v_kick_mps: 50, mode: hold_to_alignment, max_duration_s: 60, deadline_s: 60}
      stage1: gravity_turn
      stage2: {law: linear_tangent, frame: local_horizontal, cutoff: energy}
    search: {figure_of_merit: payload, gamma_grid_deg: [8, 36, 2], ...}
    target_orbit: {kind: circular, altitude_km: 200}
    checks: {...}
  assist:
    model: constant_accel
    net_accel_g: 3.0
    stroke_m: 100
    carriage_mass_t: 0
    brake_decel_g: 5
    drive_efficiency: 0.5
    exhaust_impingement_fraction: 0.0
    shaft: vented
    track: {angle_deg: 90, exit_altitude_m: 0}
  ignition:
    stage1: {t_ign_s: 0.5, reference: release}
    stage2: {t_ign_s: 0.0}
  end: insertion
  integrator: {method: DOP853, rtol: 1.0e-10, planar_max_step_s: 2.0, sample_dt_s: 0.05}
```

`assist` and `ignition` are direct children of `run` (`<section>.<name>.run.assist`,
`<section>.<name>.run.ignition`). Variants seen:

| run | `run.assist` | `run.ignition.stage1` | `run.end` |
|---|---|---|---|
| pad (and every pad-type run) | `{model: none}` | `{t_ign_s: -2.0, reference: release}` | insertion |
| pad_instant | `{model: none}` | `{t_ign_s: 0.0, reference: release, startup: {kind: step}}` | insertion |
| silo_cold | as above | `{t_ign_s: 0.5, reference: release}` | insertion |
| silo_cold_lag | same assist | `{t_ign_s: 0.5, reference: release, startup: {kind: lag, tau_s: 1.0}}` | insertion |
| silo_hot_ramp_on_track | same assist | `{t_ign_s: -2.0, reference: release}` | insertion |
| silo_hot_full | same assist | `{t_ign_s: -2.0, reference: push_start}` | insertion |
| silo_hot_full_impinged | `exhaust_impingement_fraction: 1.0` | as silo_hot_full | insertion |
| silo_failed | same assist | `{t_ign_s: 0.0, reference: release, fails: true}` | impact |
| silo_sled_22t | `carriage_mass_t: 22` | as silo_cold | insertion |
| silo_cold_200m (O) | `{model: constant_accel, exit_speed_mps: 76.70717046013364, stroke_m: 200, ...}` (no `net_accel_g`) | as silo_cold | insertion |

`run.ignition.stage2` is `{t_ign_s: 0.0}` everywhere. No recorded run of S or O has a track angle
other than 90 or an exit altitude other than 0.

Note: an offload run's entry has `run.planar.search.figure_of_merit: payload` (the run block is
the parent's); the figure the run was recorded under (`offload`) is only in `metrics.json`.

### 5.4 Which entries carry a `vehicle` block

- S `runs`: none of the 10. S `bound_runs`: both, differing from the top-level block only in
  `aero.reference_area_m2` (`{value: 21.24, assumed: true, note: override}`).
- O `runs`: none of the 4. O `offload_runs`: 13 of 15; `pad__offload_stage1` (`no_offload`) and
  `pad__offload_both` (`ok`, 0.0 kg) have `run` only.

An offloaded run's own block is a complete vehicle block (keys `name`, `description`, `stages`,
`fairing_mass_t`, `payload_mass_t`, `fairing_drop`, `screening`, `aero`); it differs from the
top-level block only in the restated masses. `offload_runs.silo_cold_s1.vehicle`, the masses:

```yaml
name: generic_f9_class_2d
stages:
- name: stage1
  dry_mass_t: {value: 22.2, source: ...}
  propellant_mass_t:
    value: 369.63709196266717
    assumed: true
    note: 'offload case ''silo_cold_s1'' (solved): 41.262908 t of propellant removed (tanks partly
      filled); the vehicle''s value was 410.9 t (source: Espace & Exploration No.39 via Wikipedia
      Falcon 9 Full Thrust (..., first-stage propellant 287.4 LOX + 123.5 RP-1))'
- name: stage2
  dry_mass_t: {value: 4.0, source: ...}
  propellant_mass_t: {value: 107.5, source: ...}
fairing_mass_t: {value: 1.7, source: ...}
payload_mass_t: {value: 22.8, source: ...}     # the nominal payload, NOT the payload the run flies
```

A penalty row also restates the dry mass (`silo_cold_s1_dry+8.1t`: `dry_mass_t: {value: 30.3,
assumed: true, note: "offload case 'silo_cold_s1_dry+8.1t': 8.1 t of stage-1 dry mass added, an
assumed structural penalty, not a sized structure; the vehicle's value was 22.2 t (...)"}` and
`propellant_mass_t: {value: 408.9195232113834, assumed: true, ...}`).

Restated values in O (t):

| offload run | stage-1 dry | stage-1 propellant | stage-2 propellant |
|---|---|---|---|
| pad__offload_stage2 | 22.2 | 410.9 | 106.98644352922679 |
| silo_cold_s1 | 22.2 | 369.63709196266717 | 107.5 |
| silo_cold_s1__pad | 22.2 | 369.63709196266717 | 107.5 |
| silo_cold_s2 | 22.2 | 410.9 | 75.59572935307025 |
| silo_cold_both | 22.2 | 374.3056802374333 | 97.92616360555871 |
| silo_cold_s1_s2pre2t | 22.2 | 370.13147288161224 | 105.5 |
| silo_cold_s1_dry+2t | 24.2 | 378.61479670459255 | 107.5 |
| silo_cold_s1_dry+4t | 26.2 | 388.02403946711144 | 107.5 |
| silo_cold_s1_dry+8.1t | 30.3 | 408.9195232113834 | 107.5 |
| silo_cold_fix5pct | 22.2 | 390.355 | 107.5 |
| silo_cold_fix10pct | 22.2 | 369.81 | 107.5 |
| silo_hot_ramp_s1 | 22.2 | 364.88656269251675 | 107.5 |
| silo_cold_200m_s1 | 22.2 | 369.6370294258513 | 107.5 |

`payload_mass_t` is 22.8 in every block; `fairing_mass_t` 1.7 and stage-2 dry 4.0 everywhere.

---

## 6. Key numbers for a mock-up and the camera design

Each row: time after release [s]; altitude [m]; Earth-fixed downrange [m]; Earth-relative speed
[m/s]; pitch [deg] (thrust direction above local horizontal; "a -> b" is the step across the
doubled row); stack mass [kg] (event row; "a -> b" across a drop).

### 6.1 S / pad

Hold 2.0 s (t -2.0 .. 0); no push; release (= liftoff: `hold_extension_s` 0.0, felt g
0.9965 -> 1.3617) at t = 0.

| event | t | alt | downrange | v_rel | pitch | mass |
|---|---|---|---|---|---|---|
| ignition (ramp start) | -2.000 | 0 | 0 | 0 | 90.000 | 572,354.396 |
| ramp end (not a row) = release = liftoff | 0.000 | 0 | 0 | 0 | 90.000 | 569,656.935 |
| kick_start | 12.4937 | 301.05 | -0.16 | 50.000 | 90.000 -> 87.166 | 535,955.591 |
| kick_end | 17.7740 | 628.77 | 9.44 | 74.589 | 87.166 | 521,712.229 |
| max-Q (37,191 Pa, Mach 1.532) | 65.7515 | 11,019.1 | 4,110.2 | 452.10 | 56.005 | 392,294.8 |
| MECO (`propellant`) | 151.3284 | 69,485.82 | 99,171.02 | 2,665.032 | 22.989 | 161,454.396 |
| staging | 151.3284 | 69,485.82 | 99,171.02 | 2,665.032 | 22.989 | 161,454.396 -> 139,254.396 |
| stage-2 ignition | 162.3284 | 80,432.61 | 125,813.41 | 2,625.502 | 21.202 -> 31.391 | 139,254.396 |
| fairing | 196.8075 | 110,483.04 | 212,323.82 | 2,766.553 | 29.091 | 129,343.226 -> 127,643.226 |
| cutoff | 536.3007 | 199,999.98 | 1,660,290.86 | 7,362.706 | 1.517 | 30,054.397 |

Maximum altitude 200,437.76 m at t = 479.2 s (the path rises 438 m above the target and comes
back down to it). Maximum downrange 1,660,290.86 m (the last row; 14.91 deg of arc on R_E);
minimum -0.159 m. Pitch range 1.517 .. 90.000 deg. psi (thrust to v_rel) up to 14.93 deg.

### 6.2 S / silo_cold

No hold; push 2.607318 s (t -2.607318 .. 0) from -100 m to 0 m at 3 g net (felt 3.9965 g);
release at 76.707 m/s.

| event | t | alt | downrange | v_rel | pitch | mass |
|---|---|---|---|---|---|---|
| push_start | -2.6073 | -100.00 | 0 | 0 | 90.000 | 573,853.227 |
| release | 0.000 | 0.00 | 0 | 76.707 | 90.000 | 573,853.227 |
| ignition + kick_start | 0.500 | 37.13 | -0.0012 | 71.808 | 90.004 -> 87.639 | 573,853.227 |
| ramp_end | 2.500 | 168.74 | 0.28 | 64.528 | 87.639 | 571,155.766 |
| kick_end | 8.0256 | 581.28 | 11.29 | 85.232 | 87.639 | 556,250.804 |
| max-Q (31,238 Pa, Mach 1.404) | 57.6096 | 11,019.1 | 3,473.7 | 414.34 | 59.307 | 422,499.7 |
| MECO | 153.8284 | 75,202.25 | 110,154.82 | 2,765.925 | 21.647 | 162,953.227 |
| staging | 153.8284 | 75,202.25 | 110,154.82 | 2,765.925 | 21.647 | 162,953.227 -> 140,753.227 |
| stage-2 ignition | 164.8284 | 85,930.38 | 138,050.02 | 2,728.702 | 19.934 -> 30.632 | 140,753.227 |
| fairing | 193.8165 | 110,993.43 | 213,627.47 | 2,847.373 | 28.763 | 132,420.480 -> 130,720.480 |
| cutoff | 538.8007 | 199,999.98 | 1,705,290.25 | 7,362.706 | 1.964 | 31,553.228 |

Maximum altitude 200,759.80 m at t = 470.4 s; minimum -100.0 m. Maximum downrange
1,705,290.25 m (15.32 deg of arc); minimum -0.0031 m. Pitch 1.964 .. 90.004 deg. The speed
falls from 76.71 m/s at release to a minimum of 63.665 m/s at t = 1.993 s (136 m up; the unlit
coast, then the thrust ramp) before it rises again (`silo_cold_s1`: 64.149 m/s at 1.893 s). Track: `drive_force_N` = `interface_force_N` = 22,490,479.6 N
constant; `drive_power_W` 0 -> 1,725,181,053.7 W, linear in time.

### 6.3 O / silo_cold_s1 (the headline offload run)

Push as silo_cold (2.607318 s, -100 m, 3 g net); stage-1 tank 89.958% full at the start.

| event | t | alt | downrange | v_rel | pitch | mass |
|---|---|---|---|---|---|---|
| push_start | -2.6073 | -100.00 | 0 | 0 | 90.000 | 531,091.488 |
| release | 0.000 | 0.00 | 0 | 76.707 | 90.000 | 531,091.488 |
| ignition + kick_start | 0.500 | 37.13 | -0.0012 | 71.807 | 90.004 -> 85.872 | 531,091.488 |
| ramp_end | 2.500 | 169.33 | 0.56 | 65.499 | 85.872 | 528,394.027 |
| kick_end | 7.9483 | 596.46 | 21.07 | 91.951 | 85.872 | 513,697.347 |
| max-Q (38,438 Pa, Mach 1.558) | 53.4990 | 11,019.1 | 4,277.6 | 459.62 | 55.614 | 390,826.2 |
| MECO | 138.5315 | 69,300.13 | 99,243.24 | 2,665.476 | 22.986 | 161,454.396 |
| staging | 138.5315 | 69,300.13 | 99,243.24 | 2,665.476 | 22.986 | 161,454.396 -> 139,254.396 |
| stage-2 ignition | 149.5315 | 80,247.52 | 125,891.38 | 2,625.947 | 21.199 -> 31.430 | 139,254.396 |
| fairing | 184.2505 | 110,492.87 | 213,043.37 | 2,768.089 | 29.109 | 129,274.267 -> 127,574.267 |
| cutoff | 523.5037 | 200,000.00 | 1,660,430.87 | 7,362.706 | 1.489 | 30,054.396 |

Maximum altitude 200,418.91 m at t = 467.1 s. Maximum downrange 1,660,430.87 m. Pitch
1.489 .. 90.004 deg. Track: drive force 20,814,559.8 N constant; power 0 -> 1,596,625,983.7 W.
MECO comes 12.797 s earlier than the pad's; max-Q is 1,247 Pa ABOVE the pad's
(`vs_pad.max_q_above_pad: true`).

### 6.4 S / silo_failed

Push as silo_cold; stage 1 never lights; no kick, no MECO, no staging, no fairing.

| event | t | alt | downrange | v_rel | pitch (raw; wrapped) | mass |
|---|---|---|---|---|---|---|
| push_start | -2.6073 | -100.00 | 0 | 0 | 90.0 | 569,100 |
| release + ignition_failed | 0.000 | 0.00 | 0 | 76.707 | 90.0 | 569,100 |
| max-Q (3,603.9 Pa, Mach 0.225) | 0.000 | 0.0 | 0 | 76.707 | 90.0 | 569,100 |
| apex | 7.8426 | 300.65 | -0.20 | 0.039 | 180.0; -180.0 | 569,100 |
| impact + end | 15.6891 | 0.00 | -0.40 | 76.598 | 270.0; -90.0 | 569,100 |

Maximum altitude 300.65 m; downrange 0 .. -0.4026 m. Thrust 0 on every row; mass constant.
The whole run spans 18.3 s. `pitch_rad` raw range 90 .. 270 deg (section 2.6).

### 6.5 Other runs, briefly

- S `silo_hot_ramp_on_track`: ignition on the track at t = -2.000 (5.43 m above the floor),
  ramp_end = release = kick_start at 0 (pitch 90.000 -> 86.343), kick_end 7.9890 (730.2 m),
  MECO 151.3284 (75,956.6 m, 111,947.8 m downrange), fairing 190.6089, cutoff 536.3007
  (1,712,236.8 m). Max altitude 200,805.95 m. Drive force falls 22,499,688.7 -> 14,787,169.7 N
  as the thrust builds; power peaks at 1,134,281,948.6 W.
- S `silo_hot_full`: HOLD t -4.6073 .. -2.6073 at alt -100.0 m (thrust ramps in the hold, mass
  573,843.0 -> 571,145.5 kg), push -2.6073 .. 0 at full thrust (drive force 14,777,560.1 ->
  14,501,917.1 N), MECO 148.7211, cutoff 533.6934.
- O `silo_cold_200m`: push 5.214636 s from -200 m at 1.5 g net (felt 2.4965 g, drive force
  14,049,113.0 N, peak power 1,077,667,705 W), `facility_length_m` 260.0; the flight equals
  silo_cold's.
- O `silo_cold_s2`: MECO 153.8284 at 76,823.2 m and 141,100.0 m downrange (3,373.4 m/s, mass
  129,550.1 -> 107,350.1 kg); cutoff 427.8117 at 1,411,119.9 m downrange with pitch -5.044 deg;
  peak felt g 6.475. The run is 108.5 s shorter than the pad's.
- O `pad__offload_stage1`: the pad's flight to within metres (cutoff row replaced by a stage-2
  `propellant` row at 536.3007, altitude 200,000.19 m).

### 6.6 State at fixed times (interpolated)

| t | pad alt / downrange [m] | silo_cold alt / downrange [m] | silo_cold_s1 alt / downrange [m] |
|---|---|---|---|
| -2 | 0 / 0 | -94.6 / 0 | -94.6 / 0 |
| 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 2 | 7.2 / 0 | 136.8 / 0.1 | 137.0 / 0.2 |
| 5 | 46.1 / 0 | 341.3 / 3.2 | 347.6 / 6.1 |
| 8 | 120.2 / 0 | 579.1 / 11.2 | 601.2 / 21.4 |
| 12 | 276.9 / -0.1 | 951.6 / 30.4 | 1,010.3 / 57.9 |
| 20 | 806.8 / 19.6 | 1,904.2 / 116.2 | 2,090.5 / 217.5 |
| 40 | 3,623.5 / 512.6 | 5,710.8 / 990.8 | 6,519.6 / 1,688.0 |
| 60 | 8,977 / 2,833 | 11,889 / 4,006 | 13,631 / 6,213 |
| 90 | 22,158 / 14,196 | 25,916 / 16,792 | 29,502 / 23,644 |
| 120 | 41,645 / 42,126 | 45,606 / 46,128 | 51,785 / 61,325 |
| 150 | 68,113 / 95,987 | 71,371 / 100,753 | 80,692 / 127,025 |
| 200 | 113,000 / 220,669 | 115,858 / 230,346 | 122,479 / 254,836 |
| 300 | 171,343 / 516,640 | 173,300 / 535,507 | 176,061 / 560,231 |
| 400 | 196,410 / 900,214 | 197,378 / 926,291 | 197,713 / 957,849 |
| 500 | 200,311 / 1,419,922 | 200,468 / 1,448,692 | 200,163 / 1,500,790 |

In the first 12 s the pad climbs 277 m and the silo run 952 m; the downrange of both is under
60 m. The trajectory is taller than it is long until about t = 120 s (altitude and downrange
cross near 42 to 46 km).

### 6.7 Thrust levels and flow

- Stage 1 full vacuum thrust 8,226,900 N (`thrust_vac_N`), 7,606,800 N delivered at sea level;
  2 s linear ramp (205,672.5 N per 0.05 s sample); mass flow at full thrust 2,697.46 kg/s
  (= 8,226,900 / (g0 x 311)); 2,697.461 kg burned in the ramp.
- Stage 2: 981,000 N, a step at ignition; 287.45 kg/s.
- Between MECO and stage-2 ignition (11.0 s) both thrust columns are 0.

### 6.8 Display-only coast extents (PROBE, not a finding; vacuum, no drag, section 5.5's rebuild)

Rebuild check on the S pad `staging` row with omega_p = omega_E cos(28.5 deg) sin(90 deg) =
6.408435449e-05 rad/s: r = 6,447,622.822 m, v_r = 1,040.8463, u = 2,453.3719, v_theta =
2,866.5636 m/s; hypot = 3,049.679962 m/s against the row's `speed_inertial_mps`
3,049.679962 (agreement to the printed digits). omega_p R_E = 408.738793 m/s = the pad's
`speed_inertial_mps` at rest.

| run | object | apex [km] at t [s] | reaches the surface at t [s], downrange [km] | run ends at t [s] |
|---|---|---|---|---|
| S pad | stage 1 | 135.25 at 278.0 | 459.6, 839.2 | 536.3 |
| S pad | fairing | 150.13 at 296.7 | 490.6, 977.1 | 536.3 |
| S silo_cold | stage 1 | 139.33 at 279.9 | 465.4, 894.1 | 538.8 |
| S silo_cold | fairing | 151.54 at 295.4 | 491.2, 1,011.6 | 538.8 |
| O silo_cold_s1 | stage 1 | 135.07 at 265.3 | 446.7, 839.2 | 523.5 |
| O silo_cold_s1 | fairing | 150.07 at 284.1 | 477.9, 978.1 | 523.5 |
| O silo_cold_s2 | stage 1 | 145.75 at 290.3 | 488.2, 1,193.0 | 427.8 (stage 1 still at 75.6 km) |
| O silo_cold_s2 | fairing | 159.38 at 309.0 | 521.2, 1,389.4 | 427.8 (fairing at 109.6 km) |

The debris stays inside the frame that holds the whole trajectory (under 160 km altitude, under
the vehicle's final downrange), and on the standard runs it is down before the run ends.

---

## 7. The liftoff-mass identity and the tank-level inputs

Checked on all 31 run folders of S and O, the two bound runs included:

    liftoff_mass_kg = stage-1 dry + stage-1 propellant + stage-2 dry + stage-2 propellant
                      + fairing + payload

with the masses from the run's own vehicle block (`<entry>.vehicle`, else the top-level
`vehicle`) and the payload = the run's `payload_kg` metric, or the block's `payload_mass_t` when
that metric is null (`silo_failed`). The difference is 0.0 at 6 decimals of a kilogram on every
run. The first `m_kg` of `timeseries.csv` equals `liftoff_mass_kg` to the same precision.

S (kg):

| run | metrics at | payload | S1 dry | S1 prop | S2 dry | S2 prop | fairing | stack = liftoff_mass_kg |
|---|---|---|---|---|---|---|---|---|
| pad | `runs` | 26,054.396 | 22,200 | 410,900 | 4,000 | 107,500 | 1,700 | 572,354.396 |
| pad__aero_bound | `bounds[0].paired_baseline_metrics` | 25,663.505 | 22,200 | 410,900 | 4,000 | 107,500 | 1,700 | 571,963.505 |
| pad_instant | `runs` | 26,137.464 | same | | | | | 572,437.464 |
| silo_cold | `runs` | 27,553.227 | same | | | | | 573,853.227 |
| silo_cold__aero_bound | `bounds[0].metrics` | 27,190.339 | same | | | | | 573,490.339 |
| silo_cold_lag | `runs` | 27,553.184 | same | | | | | 573,853.184 |
| silo_failed | `runs` (payload from the vehicle block) | 22,800.000 | same | | | | | 569,100.000 |
| silo_hot_full | `runs` | 27,543.009 | same | | | | | 573,843.009 |
| silo_hot_full_impinged | `runs` | 27,543.009 | same | | | | | 573,843.009 |
| silo_hot_ramp_on_track | `runs` | 27,788.201 | same | | | | | 574,088.201 |
| silo_instant | `runs` | 27,880.355 | same | | | | | 574,180.355 |
| silo_sled_22t | `runs` | 27,553.227 | same | | | | | 573,853.227 |

O (kg; metrics at `runs` for the first four, `offload.runs` for the rest):

| run | payload | S1 dry | S1 prop | S2 prop | stack = liftoff_mass_kg | S1 fill at start | S2 fill at start | dropped at staging |
|---|---|---|---|---|---|---|---|---|
| pad | 26,054.396 | 22,200 | 410,900.000 | 107,500.000 | 572,354.396 | 1.00000 | 1.00000 | 22,200 |
| silo_cold | 27,553.227 | 22,200 | 410,900.000 | 107,500.000 | 573,853.227 | 1.00000 | 1.00000 | 22,200 |
| silo_cold_200m | 27,553.227 | 22,200 | 410,900.000 | 107,500.000 | 573,853.227 | 1.00000 | 1.00000 | 22,200 |
| silo_hot_ramp_on_track | 27,788.201 | 22,200 | 410,900.000 | 107,500.000 | 574,088.201 | 1.00000 | 1.00000 | 22,200 |
| pad__offload_stage1 | 26,054.396 | 22,200 | 410,900.000 | 107,500.000 | 572,354.396 | 1.00000 | 1.00000 | 22,200 |
| pad__offload_both | 26,054.396 | 22,200 | 410,900.000 | 107,500.000 | 572,354.396 | 1.00000 | 1.00000 | 22,200 |
| pad__offload_stage2 | 26,054.396 | 22,200 | 410,900.000 | 106,986.444 | 571,840.840 | 1.00000 | 0.99522 | 22,200 |
| silo_cold_s1 | 26,054.396 | 22,200 | 369,637.092 | 107,500.000 | 531,091.488 | 0.89958 | 1.00000 | 22,200 |
| silo_cold_s1__pad | 24,652.368 | 22,200 | 369,637.092 | 107,500.000 | 529,689.460 | 0.89958 | 1.00000 | 22,200 |
| silo_cold_s2 | 26,054.396 | 22,200 | 410,900.000 | 75,595.729 | 540,450.126 | 1.00000 | 0.70322 | 22,200 |
| silo_cold_both | 26,054.396 | 22,200 | 374,305.680 | 97,926.164 | 526,186.240 | 0.91094 | 0.91094 | 22,200 |
| silo_cold_s1_s2pre2t | 26,054.396 | 22,200 | 370,131.473 | 105,500.000 | 529,585.869 | 0.90078 | 0.98140 | 22,200 |
| silo_cold_s1_dry+2t | 26,054.396 | 24,200 | 378,614.797 | 107,500.000 | 542,069.193 | 0.92143 | 1.00000 | 24,200 |
| silo_cold_s1_dry+4t | 26,054.396 | 26,200 | 388,024.039 | 107,500.000 | 553,478.436 | 0.94433 | 1.00000 | 26,200 |
| silo_cold_s1_dry+8.1t | 26,054.396 | 30,300 | 408,919.523 | 107,500.000 | 578,473.919 | 0.99518 | 1.00000 | 30,300 |
| silo_cold_fix5pct | 26,837.559 | 22,200 | 390,355.000 | 107,500.000 | 552,592.559 | 0.95000 | 1.00000 | 22,200 |
| silo_cold_fix10pct | 26,061.196 | 22,200 | 369,810.000 | 107,500.000 | 531,271.196 | 0.90000 | 1.00000 | 22,200 |
| silo_hot_ramp_s1 | 26,054.396 | 22,200 | 364,886.563 | 107,500.000 | 526,340.959 | 0.88802 | 1.00000 | 22,200 |
| silo_cold_200m_s1 | 26,054.396 | 22,200 | 369,637.029 | 107,500.000 | 531,091.426 | 0.89958 | 1.00000 | 22,200 |

(S2 dry 4,000 and fairing 1,700 kg on every run. Fill = the run's start load over the
top-level block's full load, 410,900 and 107,500 kg.)

Tank-level computation, checked on every run against `m_kg`:

- rows with `stage == "stage1"`: stage-1 propellant left = `m_kg` - (S1 dry + S2 dry + S2
  propellant load + fairing + payload). It starts at the run's stage-1 load and ends at 0.0
  (every stage 1 burns to depletion; never negative beyond rounding). Stage 2 is full at its own
  load throughout.
- rows with `stage == "stage2"`: stage-2 propellant left = `m_kg` - (S2 dry + payload) -
  (fairing while it is attached). The fairing is attached up to and including the FIRST of the
  two rows at the fairing time and gone from the second. Computed that way the series starts at
  the stage-2 load, never steps up (largest upward step 0.0), and ends at the residual: 0.0004
  to 0.0006 kg on the payload-search runs and on two offload runs (`pad__offload_both`,
  `silo_cold_s2`), 6e-06 to 4e-05 kg on the other offload solves, 0.000000 on
  `pad__offload_stage1` (which ran dry).
- `silo_failed`: stage-1 propellant 410,900 kg on every row.

---

## 8. Sizes

Bytes per directory: section 1 (S 45,946,129; O 74,260,469; W 85,489,444). An orbital run's
`timeseries.csv` is 2.94 to 3.76 MB (8,624 to 10,896 rows, 337 to 344 bytes per row);
`silo_failed` 94,739 bytes.

Replay page, measured at HEAD in memory with `replay.replay_data` + `replay.render_page` (nothing
written; the template is 32,008 bytes and the token 15):

| Selection | JSON bytes | page bytes |
|---|---|---|
| S, `--runs pad silo_cold silo_hot_ramp_on_track silo_failed` (the reference page) | 215,956 | 247,949 (sha256 `3ca23dc5ce6532e6b9e3fd4656ab4846bcb4cdddfced7a077ce05c9411fd1eab`, LF only) |
| S, default selection (`pad`, `pad_instant`, `silo_instant`, `silo_cold`) | 268,817 | 300,810 |
| O, default selection (`pad`, `silo_cold`, `silo_hot_ramp_on_track`, `silo_cold_200m`) | 272,809 | 304,802 |
| O, `pad silo_cold silo_cold_s1 pad__offload_stage1` | 269,139 | 301,132 |
| O, `pad silo_cold_s1 silo_cold_s1__pad pad__offload_stage1` | 266,598 (page minus 31,993) | 298,591 |

Where the 215,956 bytes go (the reference selection): the resampled series 205,831; the events
3,420; other per-run fields 3,475; `meta` 3,208.

Per run (`pad`): grid of 918 samples (t -2.0 .. 536.301: 0.1 s steps to 40 s, 1 s after);
series 64,320 bytes = `t` 4,931, `alt_m` 6,875, `x_km` 6,072, `v` 6,459, `gamma_deg` 5,162,
`m_t` 6,994, `g_ax` 5,401, `q_kpa` 4,895, `mach` 5,708, `phase` 11,823. `silo_cold` 927 samples,
65,431 bytes; `silo_hot_ramp_on_track` 925, 65,395; `silo_failed` 185, 10,685. The `phase` array
(one string per sample) is the largest single array, 18% of a run.

Scene estimate, MEASURED by resampling the extra columns on the same grid with
`replay.series_values`: seven more series (`pitch_deg` 2 decimals, `thrust_vac` and `thrust` in
kN at 1 decimal, `s_m`, drive and interface force in MN, drive power in MW) plus a per-sample
stage index, plus two samples at every event time that is off the grid (4 or 5 distinct times
per run):

| Selection | replay JSON | + 7 series | + stage | + event samples | scene estimate |
|---|---|---|---|---|---|
| S reference four | 215,956 | 114,083 | 5,914 | 3,081 | 339,034 bytes |
| S default four | 268,817 | 142,451 | 7,344 | 4,003 | 422,615 bytes |
| O default four | 272,809 | 144,634 | 7,450 | 3,781 | 428,674 bytes |
| O pad + silo_cold + s1 + control | 269,139 | 142,547 | 7,354 | 3,997 | 423,037 bytes |

That is 8 value series growing to 15 plus the stage (the brief's "about fourteen"); a plain 14/8
scaling of the value series gives 331,121 bytes for the reference four. Per run the added series
cost (`pad`): `pitch_deg` 5,195, `T_vac_kN` 6,014, `T_kN` 6,011, and 4,591 for each of the four
track series, which on a pad are 918 `null`s. Not yet counted: the events' extra columns, the
vehicle masses, the assist geometry, the rebuilt debris paths and the display block; a few kB
per run at most unless the debris paths are sampled densely (a 1 s path of 300 s with 3 numbers
is about 6 kB per object).

So four full-length runs come to roughly 0.42 to 0.45 MB of JSON, under half of the 1 MB bound.
Easy savings if wanted: `phase` as an index into a list of names (about 9 kB per run); the track
series only over the ASSIST window (27 samples at 0.1 s for a 2.6 s push) instead of 918 values
(about 18 kB per run).

---

## 9. The vehicle file `configs/vehicles/generic_f9_class_2d.yaml` (91 lines)

```yaml
name: generic_f9_class_2d
description: Generic Falcon 9-class vehicle for the planar model (calibration gate, mass set C, FT masses with Block 5 thrust).

stages:
  - name: stage1
    dry_mass_t: {value: 22.2, source: "Espace & Exploration No.39 via Wikipedia Falcon 9 Full Thrust (en.wikipedia.org/wiki/Falcon_9_Full_Thrust, first-stage empty mass)"}
    propellant_mass_t: {value: 410.9, source: "... first-stage propellant 287.4 LOX + 123.5 RP-1)"}
    engine:
      count: {value: 9, source: "spacex.com Falcon 9 page (9 Merlin 1D)"}
      thrust_vac_kN: {value: 914.1, source: "spacex.com Falcon 9 page, 8,227 kN vacuum / 9 = 914.11, rounded to 0.1 kN"}
      thrust_sl_kN: {value: 845.2, source: "spacex.com Falcon 9 page, 7,607 kN sea level / 9 = 845.22, rounded to 0.1 kN"}
      isp_vac_s: {value: 311, source: "en.wikipedia.org/wiki/SpaceX_Merlin specification table, Merlin 1D vacuum Isp 311 s"}
    startup:
      kind: ramp
      t_ramp_s: {value: 2.0, assumed: true, note: "linear ramp; F9 ignites at T-3 s and holds down"}
    coast_before_ignition_s: {value: 0.0, assumed: true, note: "first stage; no coast"}
  - name: stage2
    dry_mass_t: {value: 4.0, source: "... second-stage empty mass)"}
    propellant_mass_t: {value: 107.5, source: "... second-stage propellant 75.2 LOX + 32.3 RP-1)"}
    engine:
      count: {value: 1, source: "spacex.com Falcon 9 page (1 Merlin Vacuum)"}
      thrust_vac_kN: {value: 981, source: "spacex.com Falcon 9 page, MVac thrust (Block 5)"}
      isp_vac_s: {value: 348, source: "en.wikipedia.org/wiki/Falcon_9 specification table, second-stage Isp 348 s"}
      exit_area_m2: {value: 8.6, assumed: true, note: "MVac eps 165, ~3.3 m exit; p*A_e = 45 N at 70 km"}
    startup:
      kind: step
    coast_before_ignition_s: {value: 11.0, source: "Falcon User's Guide 2021 Table 8-4: MECO T+145 s, SES-1 T+156 s"}

fairing_mass_t: {value: 1.7, source: "... fairing mass)"}
payload_mass_t: {value: 22.8, source: "spacex.com Falcon 9 page, LEO expendable (the rung-2 reference payload)"}
fairing_drop:
  trigger: free_molecular_heating
  limit_W_m2: {value: 1135, source: "Falcon User's Guide 2021 p.38 (fairing jettison when the free-molecular heating rate 0.5 rho V^3 falls below 1,135 W/m^2)"}

screening:
  stage_isp_eff_s:
    - {value: 295, assumed: true, note: "README stage-1 average Isp between sea level and vacuum"}
    - {value: 348, source: "... second-stage Isp 348 s (vacuum stage)"}

aero:
  reference_area_m2: {value: 10.52, source: "Falcon User's Guide 2021 Table 2-1, 3.66 m body; pi*3.66^2/4; Braeunig convention = main-body section"}
  cd_scale: {value: 1.0, assumed: true, note: "nominal; the sensitivity knob (vehicle.aero.cd_scale)"}
  interpolation: pchip
  cd_mach:
    mach: [0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.2, 1.3, 1.5, 1.75, 2.0, 2.5, 3.0, 3.25, 3.5, 4.0, 4.5]
    cd: [0.460, 0.404, 0.387, 0.385, 0.388, 0.400, 0.450, 0.510, 0.589, 0.660, 0.710, 0.730, 0.722, 0.680, 0.606, 0.527, 0.460, 0.350, 0.273, 0.250, 0.236, 0.222, 0.220]
    assumed: true
    note: "Braeunig 2020 ballpark launcher curve: avg Saturn V ... and Mercury-Atlas MA-6 ...; total power-on C_D incl. base; generic, not Falcon 9"
```

File lines: stages 44-67, fairing 69, payload 70, fairing_drop 71-73, screening 78-81, aero
83-91. Header comment (lines 32-35): stages 22.2 + 410.9 + 4.0 + 107.5 = 544.6 t, plus the 1.7 t
fairing = 546.3 t without payload, against the published launch mass of 549 t; 569.1 t with the
22.8 t reference payload.

No geometry exists in this file beyond `aero.reference_area_m2` = 10.52 m^2 (a 3.66 m body
diameter, stated in its `source` text) and stage 2's `exit_area_m2` = 8.6 m^2 (assumed; about
3.3 m exit diameter per its note). No length, no fairing diameter, no engine layout, no tank
split. The same is true of the `vehicle` block in `resolved_config.yaml` (a copy of this file's
content).

---

## 10. Statements of the phase file that the data or code at HEAD contradicts

1. Section 5.3 "Size" (phase file lines 436-438) and section 7 (lines 1028-1029) say the replay
   page "was 300,810 and 268,817 bytes at 2eebcae, so SP1 changed the page" / "the page changed
   from 300,810 to 247,949 bytes". At HEAD both pairs are produced by the same code for two
   different selections: the default selection of S (`replay.select_runs`, replay.py 198-218:
   `pad`, `pad_instant`, `silo_instant`, `silo_cold`) renders to 300,810 bytes with 268,817 of
   JSON, and the four named runs to 247,949 / 215,956. The difference is the run selection
   (`silo_failed` has 185 samples against about 920), so the two figures are not evidence that
   SP1 changed the page. The reference sha256 itself is unchanged at HEAD (`3ca23dc5...1eab`).
2. Section 6 "Recorded data" (line 948): "metrics times: after release, except `t_release_s`
   (absolute)". `drive_power_peak_t_s` is also on the absolute clock (metrics_planar.py 1012,
   `t_p_max` of `drive_power_extrema`): 2.6073181789953286 on `silo_cold`, 5.214636357990658 on
   `silo_cold_200m` (the release instant; 0.0 after release). `felt_g_track_peak_t_s` beside it
   (998-1000) is after release (-2.607...).
3. Line numbers of `replay.py` and `plots.py` are those of b3150c1; commit 5007515 (SP1 step
   10a) changed both files afterwards. At HEAD: `replay.push_accel_g` 519 (phase file 521, line
   443), `replay.run_events` 445 (447), `replay.calibration_caveat` 662 (664),
   `replay.drive_caveat` 734 (736), `replay.results_ancestors` 1188 (1190),
   `replay.check_replay_out` 1222 (1224); `replay.py` has 1,244 lines (1,246). `plots._read_json`
   627 (579), `plots._read_yaml` 636 (588), `plots._events` 683 (635), `plots._results_tree` 962
   (809), `plots.check_animation_out` 996 (843), `plots.calibration_caveat` 1128 (956). The same
   commit added `plots.offload_role` (722) with `OFFLOAD_CASE`, `OFFLOAD_PAIRED_PAD`,
   `OFFLOAD_PAD_CONTROL` (488-490), which `replay.offload_note` (322) now calls: a name the
   run-data module should take over that the phase file's lists do not mention. Lines of
   `metrics_planar.py`, `metrics.py`, `phases/planar.py`, `phases/prelude.py` and `results_io.py`
   quoted in sections 5.3, 5.8 and 6 are correct at HEAD.

Statements that are true but incomplete (not contradictions):

- Section 5.3: "Phase boundaries are written twice in the CSV". So are in-phase event
  boundaries (`ramp_end`, the on-track `ignition`, `fairing`, `apex`); the first and last rows of
  a run are single (section 2.4).
- Section 5.3 "Payload": bound runs are not mentioned. Their metrics are under `metrics.json`
  `bounds[i].metrics` and `bounds[i].paired_baseline_metrics` (a list), and the identity holds
  for both bound runs of S (section 7), which the phase file left unchecked.
- Section 5.3 table, "ramp start: metrics `ramp_start_*` (requested and achieved)": no run of S
  or O has a requested key; S has no `ramp_start_*` key at all (section 4.2).
- Section 5.4 lists `liftoff` among the events: no `liftoff` row exists in any recorded file.
- Section 5.5: "about 3049 against 3049.68 m/s": the rebuild gives 3,049.679962 against
  3,049.679962.
- Section 6 "Data on disk": the sizes are rounded (S 45,946,129 bytes; O 74,260,469; W
  85,489,444).

---

## 11. Consequences for the SP2 design

1. One lookup, two shapes. A run is found in `metrics.json` under `runs`, `bounds[]` (list;
   `run` or `paired_baseline`), `cases` or `offload.runs`, and in `resolved_config.yaml` under
   `runs`, `bound_runs`, `cases` or `offload_runs`. `replay.run_source` (replay.py 244) returns
   role, metrics and run block but only the vehicle NAME. The scene builder needs the vehicle
   BLOCK: `entry.get("vehicle") or config["vehicle"]`.
2. Payload for the tank levels: `payload_kg` of the run's metrics, else
   `vehicle.payload_mass_t.value * 1000` when null. Never the block's `payload_mass_t` when the
   metric exists (it is 22.8 t in every block, offloaded ones included). The identity of
   section 7 is a cheap load-time check that holds on all 31 runs to 1e-6 kg.
3. Tank levels need the fairing state per sample. Either carry a per-sample "fairing attached"
   flag or compute the levels in Python and ship two fill series; do not recompute them in the
   page from an interpolated `m_kg` across the drop.
4. The fairing row is "mass before" on every recorded run (110 of 110 on disk). `read_events`
   can return before and after from the two timeseries rows at the event time (they differ by
   the fairing mass exactly) or from the vehicle's fairing mass; the other three forms need
   synthetic fixtures, since no directory on disk has them.
5. MECO lookup must be `event == "propellant" and stage == "stage1"`; a run that ends
   `short_of_orbit` has a second `propellant` row (2 on disk).
6. Do not key logic on an event row's `phase` (section 3.7). Use the name and the stage.
7. Events to synthesise: a pad has no `ramp_end` row and no run has a `liftoff` row. For a pad,
   liftoff = release (t = 0) and ramp end = `t_ign_rel_release_s_stage1 + t_startup_s_stage1`.
8. Steps. Keeping the last of each duplicate pair loses the "before" side. On the 1 s part of
   the grid the 22.2 t staging drop, thrust-off at MECO, the 1.7 t fairing drop and the pitch
   step at stage-2 ignition (about 10 deg) would be smeared over up to 1 s. The grid needs BOTH
   rows at each such time (two samples with the same t, or a tiny offset), or these fields must
   be step-held. Off-grid event times are few (4 or 5 per run).
9. Plume from `thrust_vac_N` over the stage's full value (8,226,900 N; 981,000 N), not from
   `thrust_N`, which is clamped to 0 for the first 0.15 s of a sea-level ramp.
10. Attitude. Orbital runs need no angle wrapping (pitch stays in [-5.1, 90.01] deg). The pitch
    steps at kick start (3 to 4 deg) and at stage-2 ignition (10 deg) are real model output: the
    scene either shows them as steps or slews, as a stated display choice. In an unpowered phase
    `pitch_rad` is the velocity direction; on `silo_failed` that turns the rocket through
    180 deg in about 0.2 s at the apex. Holding the last track attitude through a COAST after a
    failed ignition (labelled display-only) avoids a tumbling artefact that the model does not
    claim.
11. Clock. Pre-release spans differ per run: pad -2.0 s (HOLD), silo -2.607 s (ASSIST),
    `silo_cold_200m` -5.215 s, `silo_hot_full` -4.607 s (HOLD then ASSIST). Side by side on the
    release clock, the playback must start at the earliest of the shown runs and hold the others
    at their first sample.
12. Camera extents: shaft floor -100 m (-200 m); first 12 s within 1 km of altitude and 60 m of
    downrange; max-Q at 11.02 km altitude and 3.5 to 4.3 km downrange (t 53 to 66 s); MECO at 69
    to 77 km and 99 to 141 km downrange; apogee of the path 200.4 to 200.8 km (above the target,
    t 467 to 479 s); final downrange 1,411 to 1,712 km = 12.7 to 15.4 deg of arc, so the
    Earth-fixed circle of section 5.3 matters only in the last zoom level. Downrange can be
    slightly negative (-0.16 m on the pad, -0.40 m on the failed run): do not clamp at 0 or use
    a log scale without an offset. Display-only debris stays under 160 km and inside the
    vehicle's downrange (section 6.8, a probe).
13. Old directories. S lacks `stroke_m`, `net_accel_mps2`, `net_accel_g` and all `ramp_start_*`.
    Fall back to `run.assist.stroke_m`, `run.assist.net_accel_g` (or v^2 / (2 L) from
    `exit_speed_mps`), `run.assist.track.exit_altitude_m`, and the stage-1 `ignition` event row.
    `track_start_altitude_m`, `exit_speed_mps`, `braking_distance_m`, `facility_length_m` exist
    in S for assisted runs. A pad record has none of the track keys (absent, not null); use
    `.get`.
14. `drive_power_peak_t_s` is on the absolute clock; subtract `t_release_s` before showing it on
    the release clock.
15. The figure of merit of a run comes from `metrics.json` (`offload`), not from the run block
    (`payload` on every offload entry).
16. Cast every numeric column to float on load (`silo_failed` reads back as int in seven
    columns). `stage` is text; map it to 1 / 2 by its position in `vehicle.stages`.
17. Run names contain `+` and `.`. In the app's URLs a `+` in a query string decodes to a space:
    percent-encode run names (`%2B`) and never use them unescaped as element ids or in paths.
18. Directory kinds for the run browser: use the three tests of section 1.5. A sweep directory
    has no top-level `metrics.json`; its points are single-run folders with their own
    `metrics.json` (`metrics`, no `runs`) and both CSVs, so a point could be shown by a small
    adapter, but the offloaded run of a sweep point has no trajectory on disk.
19. The offload caveats are a list of 7 strings in `metrics.json` `offload.caveats`; the
    calibration caveat is the first. A run's own flags are under `offload.runs.<name>.flags`
    (4 strings on `silo_cold_s2`, 1 on `pad__offload_stage2`, none elsewhere). The results panel
    should show `vs_pad.max_q_above_pad` (true on `silo_cold_s1`: +1,247 Pa).
20. `pad__offload_stage1`: `status: short_of_orbit`, `search_status: no_offload`,
    `recorded_m_res_kg` -0.0016, no vehicle block, `pad_controls[0].resolution_effect: true`,
    `consistency: pass`. Label it from the pad-control record, not from `status`.
21. Size is not a constraint (about 0.34 MB for the reference four, 0.43 MB for four full runs
    with 15 series). The cheap savings are optional.
22. Braking: `braking_distance_m` 60.0 and `facility_length_m` 160.0 (260.0) with the mouth at
    altitude 0 and release at s = L. The facility length counts 60 m that the vehicle's
    trajectory never occupies; where to draw it stays a display choice.

---

## Scratch scripts (all read-only, in this folder)

`s05_layout.py` (tree and sizes), `s05_timeseries.py` (columns, dtypes, phases, duplicates, NaN),
`s05_events.py` (event rows, fairing convention), `s05_metrics.py`, `s05_offload.py`,
`s05_offload2.py` (metrics and the offload record), `s05_config.py`, `s05_config2.py`
(resolved config, sweep point, 1-D), `s05_keynumbers.py`, `s05_timeline.py` (section 6),
`s05_mass.py` (section 7), `s05_sizes.py` (section 8), `s05_scan.py` (all of `results/`: event
names, fairing forms, statuses; the staging-state rebuild), `s05_coast.py` (section 6.8 probe).
