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
Sensitivity cases get no folder: their numbers are in `metrics.json` and the summary's
Sensitivity table.

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
([11. Troubleshooting](11-troubleshooting.md#animate-and-replay)).

## summary.md

| Section | Run (1-D) | Run (2-D) | Sweep |
|---|---|---|---|
| Header: experiment, timestamp, git hash, comparison basis, vehicle, baseline (2-D: the search budget id and a guidance note) | yes | yes | yes |
| Variants against the baseline: one column per run, one row per quantity | yes | yes | |
| `sweep_<n>`: the sweep index as a table | | | yes |
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
| `preregistration` | Calibration only: the last commit touching `configs/` and `experiments/` and whether they were dirty |

A sweep point's `metrics.json` holds `experiment`, `timestamp_utc`, `git`, `run`,
`baseline`, `metrics` and `comparison`.

### Run metrics worth knowing

All SI, with the unit in the name; times are seconds after release unless the name says
otherwise. These are 2-D keys; the 1-D model has the same loss, load and assist keys where
they apply.

| Key | Meaning |
|---|---|
| `payload_kg` | P\*, the payload capacity (null when the search failed or did not run) |
| `payload_excess_kg` | P0 - P\* (negative: the vehicle can carry more than its file payload) |
| `residual_propellant_kg`, `dv_margin_mps` | Stage-2 propellant left at insertion with the file payload P0, and its delta-v; negative is a virtual shortfall (`residual_propellant_virtual`) |
| `search_status`, `figure_of_merit` | `ok`, `no_orbit`, `search_failed`, or a skip reason; `payload`, `residual` or `none` |
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
| `ramp_start_*` | The achieved stage-1 ramp start; with a depth, speed or height trigger also `ramp_start_trigger` and `ramp_start_requested_*` (2-D; [5](05-assist-and-ignition.md#ramp-start-by-depth-speed-or-height-sp1-step-3)) |
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
2-D file adds `model`, `label`, `bound_runs` and `cases`.

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
