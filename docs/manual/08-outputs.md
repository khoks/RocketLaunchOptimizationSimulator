# 8. Outputs

[Manual contents](README.md) · Previous: [7. Commands](07-commands.md) · Next: [9. Reading results](09-reading-results.md)

Every `run` and `sweep` writes a new directory under the results root; nothing is ever
overwritten. Results are generated, never edited by hand.

## Where results go

`<results root>/<experiment name>/<UTC timestamp>/`, with the timestamp as
`YYYYMMDDTHHMMSSZ` (no colons, so it is a valid Windows name). If that directory already
exists, `-2`, `-3`, ... are appended. The results root defaults to `results/` in the
repository ([7. Commands](07-commands.md#run)).

Only each directory's top-level `summary.md` is tracked in git (see `.gitignore`); the CSVs,
plots and JSON stay local. The shipped summaries are under `results/` in the repository.

The directory is created before the first run starts, so an unwritable results root fails
at once. `summary.md` is written last. If anything raises in between, the directory gets
`FAILED.txt` with the traceback and no `summary.md`.

## A run directory

```text
results/<experiment>/<timestamp>/
├── summary.md            the report: every variant against the pad, losses, loads, energy,
│                         sensitivity, flags, assumptions, checks
├── metrics.json          every number in the summary, machine-readable
├── resolved_config.yaml  the vehicle and every run as it ran (merged, shared blocks injected)
├── plots/                <run>_<kind>.png
└── <run>/                one folder per run
    ├── timeseries.csv    the sampled state, loads, losses and track quantities
    └── events.csv        one row per event
```

A 2-D directory also has a folder (and plots) for every bound re-run and its paired
baseline (`<variant>__<bound>`, `<baseline>__<bound>`) and for every calibration case.
With an `offload:` block it also has one for every offload run: each case's recorded run
(`<case>`), each paired pad (`<case>__<baseline>`) and each pad control
(`<baseline>__offload_<mode>`) ([5b](05b-offload.md#the-runs-it-writes)). Sensitivity cases
and offload sensitivity arms get no folder: their numbers are in `metrics.json` and the
summary.

## A sweep directory

```text
results/<experiment>/<timestamp>/
├── summary.md            one table per sweep, then assumptions (and checks, 2-D)
├── baseline/             the baseline, flat layout
└── sweep_<n>/
    ├── sweep_index.csv   one row per point
    ├── run_<nnnn>/       one point, flat layout
    └── run_<nnnn>__pad/  its paired baseline (paired sweeps only)
```

The flat layout of `baseline/` and of each point holds `summary.md`, `metrics.json`,
`resolved_config.yaml`, `timeseries.csv`, `events.csv` and `plots/` in one folder. There is
no top-level `metrics.json` in a sweep directory, so `animate` and `replay` cannot take one
([11. Troubleshooting](11-troubleshooting.md#animate-and-replay)). Offload cases solved at a
sweep point write no folder of their own; their results are columns of `sweep_index.csv`.

### sweep_index.csv

One row per point: `point`, the axis values (one column per dotted path), `run_dir`, `of`,
`paired_baseline`, then the point's figures against the baseline (in 2-D: exit speed, P\*
and dP\*, the screening yardsticks and the gain beyond them, gamma\*, the kick speed, peak
q-alpha and max-Q with their deltas, facility length, drive energy and peak power, kick
regime, the upper-bound flags, search status, screening status and any failed diagnostic
check), and last the run's `status`. Floats are written with 12 significant digits.

When the sweep names offload cases, each case adds these columns, written
`<case>.<column>` and placed before `status`:

| Column | Unit | Meaning |
|---|---|---|
| `status` | | The solve's status (`ok`, `no_offload`, `search_failed`), or a fixed case's payload-search status; `reference_failed` when the point's baseline has no P\* |
| `offload_kg` | kg | The offload x\* (a fixed case's imposed one) |
| `stage1_fraction`, `total_fraction` | - | Its share of the stage-1 load and of the total load |
| `reference_payload_kg` | kg | The point's P_ref (its baseline's P\*) |
| `payload_kg`, `payload_delta_kg` | kg | The payload the recorded run flies and that less P_ref: P_ref and 0 for a solved case; a fixed case's own P\* and its figure P\* - P_ref |
| `verification_delta_kg` | kg | The independent verification's P\* - P_ref (a solved case's; a fixed case has none) |
| `decomposition_status` | | `explained` or `bug_suspect` ([9](09-reading-results.md#the-cross-vehicle-decomposition)) |
| `screening_ratio` | - | Stage-1 offload over the ideal-screening offload at the point's release speed |
| `max_q_pa` | Pa | Max-Q of the offloaded run (unthrottled) |
| `electrical_energy_J` | J | Electrical energy of the offloaded run's push |
| `solve_gamma_star_rad` | rad | The solve's own gamma\*_ref (Earth-relative flight-path angle at MECO), not the point's payload-search `gamma_star_rad` column. Empty for a fixed case (no solve) and for a solve that ended `search_failed` |
| `n_flags` | | The number of the case record's flags (its solve's and its recorded run's); the flags themselves are listed in the sweep summary's Checks section. Empty for a record without a flag list (a `reference_failed` point) |

From `results/silo_offload_2d/20261003T112949Z` (sweep 1, its 100 m point; the CSVs are
local, not in git): `silo_cold_s1.offload_kg` 41262.9080373, `silo_cold_s1.stage1_fraction`
0.100420803206, `silo_cold_s1.verification_delta_kg` 0.00845215498703,
`silo_cold_s1.solve_gamma_star_rad` 0.40118836928, `silo_cold_s1.n_flags` 0. The other load and
power columns of a sweep row describe the point's full-load run, because the offloaded run
of a point is not written; only `max_q_pa` and `electrical_energy_J` of the case columns
describe the offloaded run.

## summary.md

| Section | Run (1-D) | Run (2-D) | Sweep |
|---|---|---|---|
| Header: experiment, timestamp, git hash, comparison basis, vehicle, baseline (2-D: the search budget id and a guidance note) | yes | yes | yes |
| Variants against the baseline: one column per run, one row per quantity | yes | yes | |
| `sweep_<n>`: the sweep index as a table | | | yes |
| Propellant saved at fixed payload (only with an `offload:` block; [5b](05b-offload.md#what-the-summary-reports)) | | yes | |
| Bounds | | yes | |
| Cases (calibration) | | yes | |
| Sensitivity | yes | yes | |
| Flags | yes | yes | |
| Assumptions, each with the runs it applies to | yes | yes | yes |
| Checks | yes | yes | 2-D |

The git hash ends in `-dirty` when the working tree had uncommitted changes outside
`results/` at run time.

**The 2-D variant table** has these groups of rows, in order: status, search status, run
checks, screening status and flags; stage-1 ignition time and startup; payload capacity P\*,
the gain over the pad, both screening yardsticks and the one used, the gain beyond it, and
whether the gain is an unthrottled upper bound; residual propellant and delta-v margin at
the vehicle payload; the guidance found (gamma\*, kick angle, LTG a and b) and the kick
regime; release speed and the propellant burned before flight; MECO; fairing drop; stage-2
end and the orbit; the four losses and the identity and closure residuals; max-Q and
q-alpha; felt g (run-wide, in flight, lateral, on the track); interface force and hold-down
force; track-normal g; drive energy, electrical energy, peak power, braking distance and
facility length; search diagnostics; and the failed-ignition items. "n/a" marks an item a
run did not reach.

**The 1-D variant table** reports burnout speed instead of payload: release speed and its
delta, propellant burned before release, stage-1 burnout speed and altitude with deltas,
the loss-identity line term by term, the hold-down credit, the ignition loss (integrated and
by formula), the ideal-screening payload equivalents (labelled "not a payload result"), the
losses, loads, energy and power, and the failed-ignition items.

How to read these rows is the subject of [9. Reading results](09-reading-results.md).

## metrics.json

UTF-8 JSON with no NaN (non-finite numbers are written as `null`).

| Key | What it holds |
|---|---|
| `experiment`, `timestamp_utc` | Identify the run |
| `git` | `{hash, dirty, error}`: the commit (12 characters), whether the tree was dirty, and git's message if it failed |
| `comparison_basis` | The basis line of the summary header |
| `baseline` | The baseline's name |
| `runs` | Per run: every metric, plus `status` and `flags` |
| `comparison` | Per variant: its comparison with the baseline |
| `sensitivity` | One record per case: the parameter, the fraction, the value (SI and YAML units), status, flags, the case's metrics and its comparisons |
| `model`, `label`, `search_budget_id` | 2-D only |
| `bounds` | 2-D only: per bound run, its overrides, both runs' metrics and the comparisons with the paired and the unchanged baseline |
| `cases` | 2-D only: each calibration case's metrics |
| `offload` | Only with an `offload:` block: the offload record (below) |
| `preregistration` | Calibration only: the last commit touching `configs/` and `experiments/` and whether they were dirty |

A sweep point's `metrics.json` holds `experiment`, `timestamp_utc`, `git`, `run`,
`baseline`, `metrics` and `comparison`.

### The offload record

`metrics.json` of a `run` with an `offload:` block gains the key `offload`. With
`--no-offload` it holds only `basis`, `reference`, `skipped` (the skip note) and an empty
`runs`. Otherwise:

| Key | What it holds |
|---|---|
| `basis`, `reference`, `reference_payload_kg` | The basis line (different vehicles, same payload and orbit), the baseline's name and P_ref [kg] |
| `caveats` | The caveat lines the summary prints, the vehicle's calibration first |
| `energy_inputs` | Each stage's fuel mass [kg] and the heating value [J/kg], each with its provenance (null without an `energy` block) |
| `pad_control`, `pad_controls` | The setting, and one record per control: `mode`, `run`, `status`, `offload_kg` (x_pad), `fraction_of_load`, `m_res_kg`, `dv_margin_mps`, `slope_kg_per_kg`, `bound_kg`, `within_bound`, `resolution_effect`, `consistency` (`pass`, `fail`, `not_checked`; `n/a` for stage 2 and both), `solve`, `verification`, `flags` |
| `cases` | One record per case (below); a case whose variant did not run holds only `name`, `of` and `skipped` |
| `sensitivity_basis`, `sensitivity` | The arms' basis line, and one record per arm: `case`, `run`, `param`, `fraction`, `pad_perturbed`, `reference_payload_kg` and `nominal_reference_payload_kg`, `status`, `offload_kg`, `nominal_offload_kg`, `offload_delta_kg`, `payload_kg`, `payload_delta_kg`, `stage1_fraction`, `total_fraction`, `decomposition_status`, `decomposition_residual_mps`, `screening_ratio`, `electrical_energy_J`, `trajectory_reused`, `flags` |
| `notes` | For example the note that `--no-sensitivity` skipped the arms |
| `runs` | The metrics record of every run the block writes, by name (the same keys as `runs` above) |

**A case record** holds:

- what it is: `name`, `of`, `kind` (`solve` or `fixed`), `mode`, `fixed_key` and
  `fixed_fraction` (a fraction key's value; a mass key's is `offload_kg`), `run` (its
  recorded run), `status` (the solve's, or a fixed case's payload search), `run_status`;
- the figure: `reference_payload_kg`, `quoted_offload_kg` and `quoted_basis` (the stage-1
  x\* gross; for stage 2 and both, x\* net of the pad control; for a fixed case the imposed
  offload), `offload_kg`, `net_offload_kg`, `pad_control_offload_kg`;
- what was removed, gross: `stage2_preoffload_kg`, `stage1_offload_kg`,
  `stage2_offload_kg`, `total_offload_kg`, the loads (`stage1_load_kg`, `stage2_load_kg`,
  `total_load_kg`) and the shares (`stage1_fraction`, `stage2_fraction`,
  `total_fraction`); the penalty (`stage1_dry_mass_added_kg`, `assumed_penalty`);
- the payload: `payload_kg` (P_ref for a solved case, its own P\* for a fixed one) and
  `payload_delta_kg`;
- `solve` (status, `offload_kg`, `root_kg`, `load_kg`, `fraction_of_load`,
  `gamma_star_rad`, `m_res_kg`, `dv_margin_mps`, `dv_shortfall_mps` of a `no_offload`
  solve, `n_evaluations`, `failure_kind`, `failure_message`, `flags` and the logged
  `evaluations`) and `verification` (`status`, `payload_kg`, `delta_kg`, `tolerance_kg`,
  `passed`, `run`);
- `vs_pad`: `liftoff_mass_kg`, `stage1_burnout_t_s`, `max_q_pa` and
  `peak_felt_axial_g_flight`, each with `pad_<key>` and `delta_<key>`, `max_q_above_pad`,
  and the push's `speed_at_release_mps`, `felt_g_track_peak`, `peak_interface_force_N`,
  `facility_length_m`, `electrical_energy_J`;
- `decomposition` (the cross-vehicle terms `xv_<term>_mps` and `xv_<term>_kg`, the D_id
  change `xv_ideal_dv_reduction_mps`, `xv_residual_mps`, `xv_check`, `xv_status` and
  more), with `decomposition_status`, `release_speed_mps`, `screening_offload_kg`,
  `screening_ratio` and `beats_screening` beside it;
- `paired_pad` (null without one): `run`, `status`, `payload_kg`,
  `payload_delta_vs_reference_kg`, `assisted_run`, `assisted_payload_kg`,
  `payload_delta_kg` (assisted P\* minus paired pad P\*), `screening_status` and the full
  `comparison` (with its matched-payload attribution `attr_*`);
- `energy` (null without an `energy` block): `fuel_removed_kg`, `oxidizer_removed_kg`
  and their per-stage lists, `fuel_fraction_per_stage`, `heating_value_J_per_kg`,
  `heat_J`, `heat_kWh`, `electrical_energy_J`, `electrical_energy_kWh`,
  `heat_to_electricity_ratio`, `ratio_label` ("not an efficiency claim") and `excludes`;
- `flags`.

### Run metrics worth knowing

All SI, with the unit in the name; times are seconds after release unless the name says
otherwise. These are 2-D keys; the 1-D model has the same loss, load and assist keys where
they apply.

| Key | Meaning |
|---|---|
| `payload_kg` | P\*, the payload capacity (null when the search failed or did not run) |
| `payload_excess_kg` | P0 - P\* (negative: the vehicle can carry more than its file payload) |
| `residual_propellant_kg`, `dv_margin_mps` | Stage-2 propellant left at insertion with the file payload P0, and its delta-v; negative is a virtual shortfall (`residual_propellant_virtual`) |
| `search_status`, `figure_of_merit` | `ok`, `no_orbit`, `search_failed`, or a skip reason; `payload`, `residual` or `none`. An offload solve's recorded run reports `offload` and the solve's status (`ok`, `no_offload`, `search_failed`), its `payload_kg` is P_ref, and it adds `offload_mode`, `offload_kg`, `offload_status` and `offload_reference_payload_kg` |
| `gamma_star_rad`, `delta_rad`, `ltg_a`, `ltg_b_per_s` | The guidance found for this run |
| `kick_regime`, `speed_at_kick_mps` | `after_vertical_rise`, `at_first_lit_instant` or `none`; the air-relative speed at the kick |
| `dv_vac_mps`, `gravity_loss_mps`, `drag_loss_mps`, `steering_loss_mps`, `back_pressure_loss_mps` | The loss budget from the flight start |
| `identity_residual_mps`, `closure_residual_mps` | How well the loss identity and the rocket-equation closure close |
| `max_q_pa`, `max_q_time_s`, `max_q_alt_m`, `max_q_mach` | Maximum dynamic pressure (unthrottled: an upper bound) and where it occurs |
| `peak_q_alpha` | Peak q times the angle between thrust and air-relative velocity [Pa rad] |
| `peak_felt_axial_g` (and `_phase`, `_t_s`, `_mass_kg`) | Run-wide peak felt axial acceleration [g0]: hold, track and flight |
| `peak_felt_axial_g_flight`, `peak_felt_lateral_g`, `felt_g_track_peak` | The same in flight, sideways in flight, and on the track |
| `interface_force_peak_N` (alias `peak_interface_force_N`) | Peak force between vehicle and carriage |
| `peak_track_normal_g` | Larger of the vehicle and carriage track-normal loads [g0] |
| `drive_energy_J`, `drive_energy_kWh` (aliases `assist_energy_J`, `assist_energy_kWh`) | Net drive work |
| `electrical_energy_J`, `electrical_energy_kWh` | Positive drive work / drive efficiency |
| `drive_power_peak_W` (alias `peak_drive_power_W`), `drive_power_peak_t_s` | Peak drive power and its time on the run clock (t = 0 at push start) |
| `braking_distance_m`, `facility_length_m` | Carriage braking distance; stroke plus braking |
| `exit_speed_mps`, `push_time_s` | Track exit speed and push duration |
| `stroke_m`, `net_accel_mps2`, `net_accel_g` | The push as flown, however it was stated (2-D) |
| `ramp_start_*` | The achieved stage-1 ramp start; with a depth, speed or height trigger also `ramp_start_trigger` and `ramp_start_requested_*` (`ramp_start_requested_t_s` is empty for a height reached by the altitude event; 2-D; [5](05-assist-and-ignition.md#ramp-start-by-depth-speed-or-height)) |
| `propellant_burned_before_release_kg`, `propellant_burned_before_flight_kg` | Propellant burned while clamped or on the track |
| `meco_*`, `stage1_burnout_*`, `stage2_end_*`, `insertion_e`, `perigee_alt_m`, `apogee_alt_m` | Stage-1 burnout and the orbit at stage-2 cutoff |
| `failed_stage`, `apex_alt_m`, `apex_t_s`, `impact_t_s`, `impact_speed_mps` | Failed ignition: the stage that did not light, the coast's highest point and when, and the impact time and speed. The 1-D model writes these keys too (the apex and impact keys for every run, `null` when there is no apex or impact), plus `failed_`-prefixed ones for a failed ignition (`failed_apex_alt_m`, `failed_t_apex_s`, `failed_carriage_alt_m`, `failed_t_carriage_s`, `failed_speed_at_carriage_mps`, `failed_t_return_s`, `failed_impact_speed_mps`, `failed_speed_at_shaft_bottom_mps`) |
| `run_checks`, `run_checks_failed`, `trace_status` | The per-run checks (`ok` or `bug_suspect`) and the trajectory's own status |

The pad reports every assist item (drive energy, interface force, facility length, ...) as
0: no drive, no carriage, no facility.

### Comparison keys (2-D)

Each variant's `comparison` holds `delta_<metric>` for its numeric metrics, plus:
`payload_delta_kg` (dP\*), `ideal_screening_payload_at_release_speed_kg` (the screening
yardstick on the vehicle at P0), `ideal_screening_payload_at_release_speed_at_pbase_kg` (at
the baseline's P\*), `screening_yardstick_kg` and `screening_yardstick_basis` (the stricter
of the two), `payload_beyond_screening_kg`, `beats_screening`, `max_q_above_baseline`,
`q_alpha_above_baseline`, `unconstrained_kick`, `payload_delta_upper_bound`, the
matched-payload attribution (`attr_*`, in m/s and kg), the mechanism checks
(`checks_closure`, `checks_attribution`, `checks_m2` to `checks_m5`), `screening_failed`,
`screening_diagnostic_failed` and `screening_status`. They are explained in
[9. Reading results](09-reading-results.md).

The 1-D comparison holds the deltas, the identity line terms (`d_*`,
`identity_line_residual_mps`), `hold_down_credit_mps`, the ignition losses, the
ideal-screening payload equivalents and `unexplained_gain_mps`.

## resolved_config.yaml

The vehicle dict and every run's dict as it ran: variants merged over the baseline and the
shared blocks injected, in the YAML units of the input files (degrees, tonnes, g), with
`experiment`, `timestamp_utc`, `git`, `comparison_basis` and `baseline`. A run whose vehicle
differs (a vehicle sensitivity case, a vehicle sweep point) carries its own vehicle dict. A
2-D file adds `model`, `label`, `bound_runs` and `cases`, and, with an `offload:` block,
`offload_runs`: every offload run it wrote, each with its run dict and its offloaded vehicle
dict (the changed masses restated as `{value, assumed: true, note}`). With `--no-offload`
`offload_runs` is empty.

## timeseries.csv

One row per sample: every `sample_dt_s` inside each phase plus both ends of every phase, so
phase boundaries are always in the series. Floats are written with 12 significant digits.

### 2-D columns

| Column | Unit | Meaning |
|---|---|---|
| `t_s` | s | Run clock: t = 0 at push start (track) or hold-down release (pad) |
| `t_rel_release_s` | s | Time after release (negative during a hold or push) |
| `phase`, `stage` | | Phase kind ([3. Concepts](03-concepts.md#the-phases-of-a-run)) and stage name |
| `alt_m` | m | Altitude above the datum (negative in the shaft) |
| `downrange_m` | m | Earth-fixed arc along the datum sphere (0 before the flight) |
| `speed_rel_mps`, `speed_inertial_mps` | m/s | Speed relative to the co-rotating air, and inertial speed |
| `gamma_rel_rad` | rad | Flight-path angle of the air-relative velocity, unwrapped (a fall-back reads 3 pi/2 on the way down) |
| `pitch_rad` | rad | Thrust direction above local horizontal (along the air-relative velocity when unpowered), unwrapped |
| `psi_rad` | rad | Angle between thrust and air-relative velocity |
| `m_kg` | kg | Vehicle mass |
| `thrust_N`, `thrust_vac_N` | N | Delivered thrust (vacuum thrust minus ambient pressure on the exit, clamped at 0) and vacuum thrust |
| `drag_N` | N | Drag |
| `q_pa`, `mach` | Pa, - | Dynamic pressure and Mach number. Empty on track rows: the vented shaft has no air model |
| `q_alpha_pa_rad` | Pa rad | q times psi (empty on track rows) |
| `felt_axial_g`, `felt_lateral_g` | g0 | Felt acceleration along and across the thrust axis. Hold rows read 1 g; track rows give the axial value on the push and the vehicle's track-normal load |
| `J_vac_mps`, `J_grav_mps`, `J_alt_mps`, `J_drag_mps`, `J_steer_mps`, `J_bp_mps` | m/s | Cumulative loss quadratures from the flight start (0 before it). `J_alt_mps` is the part of the gravity loss due to gravity weakening with altitude |
| `s_m` | m | Position along the track (track rows only) |
| `drive_force_N`, `interface_force_N` | N | Drive force and vehicle-carriage interface force (track rows only) |
| `drive_power_W` | W | Drive power (track rows only) |
| `track_normal_g_vehicle`, `track_normal_g_carriage` | g0 | Track-normal load per body (track rows only) |

### 1-D columns

`t_s`, `z_m` (altitude above the pad datum, +z up), `v_mps` (vertical speed), `m_kg`,
`t_rel_release_s`, `thrust_N`, `thrust_vac_N`, `accel_felt_g`, `phase`, `stage`,
`J_vac_mps`, `J_grav_mps`, `J_alt_mps`, `J_bp_mps`, `J_steer_mps`, and the same six track
columns. The 1-D model has no atmosphere, so there is no drag, q or Mach.

Load one with pandas: `pandas.read_csv("<run>/timeseries.csv")`.

## events.csv

One row per event, in time order.

| Model | Columns |
|---|---|
| 2-D | `t_s`, `event`, `phase`, `stage`, `alt_m`, `downrange_m`, `speed_rel_mps`, `speed_inertial_mps`, `gamma_rel_rad`, `m_kg` |
| 1-D | `t_s`, `event`, `phase`, `stage`, `z_m`, `v_mps`, `m_kg` |

`t_s` is on the run clock. Event names you will see:

| Event | When |
|---|---|
| `push_start` | The push begins (t = 0 on a track) |
| `ignition_height` | The coast after release crosses the height of a ramp start stated by `height_method: event`; logged right before the `ignition` it triggers |
| `ignition` | A stage's thrust ramp starts |
| `ignition_failed` | A stage with `fails: true` would have lit |
| `liftoff` | Thrust passes weight after the clamp was due to open (an extended hold) |
| `release` | Track exit, or hold-down release on a pad |
| `ramp_end` | A thrust ramp reaches full thrust |
| `kick_start`, `kick_end` | The pitch kick (2-D) |
| `propellant` | A stage runs out of propellant |
| `staging` | Stage separation |
| `fairing` | Fairing jettison |
| `cutoff` | Stage-2 energy cutoff at the target orbit (2-D) |
| `apex`, `impact` | Top of a coast; reaching the ground |
| `drive_limit` | The drive force would turn negative: the run stops on the track |
| `end` | The run's last state |

From the 2-D record `results/silo_screening_2d/20260930T175743Z` (its CSVs are local, not
in git; re-running the experiment reproduces them), silo_cold's first events read `push_start` at 0 s (altitude -100 m), `release` at 2.607 s (76.7 m/s),
then `ignition` and `kick_start` together at 3.107 s: the silo run is already faster than
the 50 m/s kick trigger when its engines light.

## Plots

`plots/<run>_<kind>.png`, 768 x 432 px (6.4 x 3.6 in at 120 dpi). Characters outside
`[A-Za-z0-9_.-]` in a name become `_`.

| Kind | 2-D | 1-D |
|---|---|---|
| `trajectory` | altitude [km] against downrange [km] | |
| `altitude` | | z [m] against time |
| `speed` | `speed_rel_mps` and `speed_inertial_mps` | `v_mps` |
| `angles` | `gamma_rel_rad` (unwrapped) and `pitch_rad`, in degrees | |
| `q_mach` | q [Pa] and Mach (twin axis) | |
| `mass_thrust` | mass and thrust (twin axis) | mass and thrust (twin axis) |
| `felt_g` | felt axial and lateral g | felt axial g |
| `losses` | cumulative gravity, drag, steering and back-pressure losses | |
| `track_forces` | drive and interface force (runs with a track) | the same |
| `drive_power` | drive power (runs with a track) | the same |

Every panel except `trajectory` is plotted against `t_rel_release_s`. The findings notes
copy the plots they rest on into [docs/findings/](../findings/README.md#plot-files) with a
prefix naming the note.

Next: [9. Reading results](09-reading-results.md)
