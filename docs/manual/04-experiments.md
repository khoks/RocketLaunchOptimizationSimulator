# 4. Experiment files

[Manual contents](README.md) · Previous: [3. Concepts](03-concepts.md) · Next: [5. Assist and ignition](05-assist-and-ignition.md)

An experiment file is one YAML file under `experiments/`. It names a vehicle, defines a pad
baseline and the variants compared with it, and optionally sweeps, sensitivity cases,
bounds and (for calibration) cases. Everything is validated, and every run's settings are
built, before anything is integrated or written: a file that is refused leaves no results
directory and prints one `error:` line.

The examples come from the shipped files and say which one. Snippets marked "written for
this manual" are not in a shipped file; each was checked against the config loader.

## Top-level keys

| Key | Required | What it is |
|---|---|---|
| `name` | yes | The experiment name; it becomes the directory `results/<name>/` |
| `vehicle` | yes | Path to a vehicle file ([6. Vehicle files](06-vehicles.md)) |
| `label` | no | `calibration` (allows `cases`) or `guidance_study` (allows paired `guidance.*` sweeps) |
| `dynamics` | no | `vertical_1d` (default) or `planar_2d` |
| `site` | 2-D: yes | Launch site, shared by every run |
| `target_orbit` | 2-D | Target orbit, shared |
| `guidance` | 2-D: yes | Guidance parametrisation, shared |
| `search` | 2-D: yes | Search budget and figure of merit, shared |
| `checks` | 2-D: yes | Bug and flag thresholds, shared |
| `baseline` | yes | The pad run every other run is compared with |
| `variants` | no | Named partial runs merged over the baseline |
| `sweeps` | no | Grids over dotted paths, run by `launchsim sweep` |
| `sensitivity` | no | Plus/minus fractions on dotted paths, run by `launchsim run` |
| `bounds` | no | Named re-runs with overrides, each against a re-run baseline (2-D) |
| `cases` | no | Independent runs, never compared; only with `label: calibration` |

Unknown keys are errors everywhere, so a typo is caught, not ignored.

**Units.** Experiment files use bare numbers. The key name carries the unit, and the
conversion to SI happens once, at load: `_deg` (degrees), `_km`, `_m`, `_t` (tonnes), `_kg`,
`_g` (multiples of g0 = 9.80665 m/s^2), `_s`, `_mps` (m/s), `_rad`. Inside the code
everything is SI.

**Names.** `name`, every run name and every name that becomes a directory must use letters,
digits, `_`, `.`, `+` or `-`, start with a letter or digit, not end in `.`, and be at most
64 characters long (results paths stay short on Windows). Windows device names (CON, NUL,
COM1, ...) are refused, and run names cannot be `plots`, `baseline`, `sweep_<n>` or
`run_<n>`, which the results layout uses.

**The vehicle path** is looked up relative to the experiment file's folder first, then
relative to the repository root (the nearest folder above with a `pyproject.toml`). The
shipped files write `configs/vehicles/<file>.yaml`, which resolves from the root. Absolute
paths are used as given.

## Choosing the model: `dynamics`

- `vertical_1d` (the default): straight up, vacuum thrust from sea level, no air, no Earth
  rotation, to stage-1 burnout. Fast. Used by `silo_screening_1d.yaml`.
- `planar_2d`: a planar ascent over a spherical, rotating Earth with the ICAO atmosphere,
  drag, back-pressure, guidance and a payload search, to orbit. Used by the other four
  shipped files. The vehicle needs exactly two stages and an `aero` block.

## Shared blocks (experiment level)

`dynamics`, `site`, `target_orbit`, `guidance`, `search` and `checks` are declared once at
the top and injected into every run. They are identical for every run of an experiment by
construction: the baseline may not set them (except a 1-D baseline's own `site`, the Phase 1
form, when the experiment declares none), and variants, sweeps, sensitivity parameters and
bounds may not touch them. The one exception is a paired sweep of a `guidance_study`, which
may vary `guidance.*`.

The four shipped 2-D files declare identical shared blocks (a test pins that). From
`experiments/silo_screening_2d.yaml`:

```yaml
dynamics: planar_2d
site: {latitude_deg: 28.5, azimuth_deg: 90, include_rotation: true}
target_orbit: {kind: circular, altitude_km: 200}
guidance:
  kick: {v_kick_mps: 50, mode: hold_to_alignment, max_duration_s: 60, deadline_s: 60}
  stage1: gravity_turn
  stage2: {law: linear_tangent, frame: local_horizontal, cutoff: energy}
```

### `site`

| Key | 1-D default | 2-D | Meaning |
|---|---|---|---|
| `latitude_deg` | 28.5 | required | Site latitude, -90 to 90 |
| `azimuth_deg` | 90 | required | Launch azimuth clockwise from north, 0 to 360 |
| `include_rotation` | false | required | Earth rotation. Refused on `vertical_1d` |

`experiments/silo_screening_1d.yaml` declares no experiment-level site and puts
`site: {latitude_deg: 28.5, azimuth_deg: 90, include_rotation: false}` inside its baseline
(the Phase 1 form).

The planar model uses the rotation rate in the plane of the launch,
omega_p = omega_E cos(lat) sin(az). It is exact for an equatorial east launch and an
approximation otherwise; a run whose azimuth is not 90 degrees gets an extra assumption line
and a flag.

### `target_orbit`

`kind: circular` (the only kind) and `altitude_km` above the R_E sphere (6,378,137 m). The
shipped value is 200 km, fixed before the calibration run and never moved.

### `guidance`

| Key | Default | Meaning |
|---|---|---|
| `kick.v_kick_mps` | 50 | The kick starts when the air-relative speed reaches this, while rising. A run already faster when stage 1 lights kicks at once |
| `kick.mode` | `hold_to_alignment` | Hold the kick angle until the velocity lines up with the thrust (the only mode) |
| `kick.max_duration_s` | 60 | A kick longer than this is a guidance failure (`kick_timeout`) |
| `kick.deadline_s` | 60 | v_kick must be reached this long after stage-1 ignition (`no_kick` otherwise) |
| `stage1` | `gravity_turn` | Thrust along the air-relative velocity after the kick (the only law) |
| `stage2.law`, `.frame`, `.cutoff` | `linear_tangent`, `local_horizontal`, `energy` | Linear-tangent steering to an energy cutoff (the only choices) |

The free guidance parameters (gamma\*, the kick angle, the stage-2 pair a and b) are not set
here; the search solves them per run ([3. Concepts](03-concepts.md#guidance-and-what-sweep-optimized-means)).

### `search`

The shared search budget. Every run of an experiment uses it; its hash is reported as the
search budget id.

| Key | Default | Meaning |
|---|---|---|
| `figure_of_merit` | `payload` | `payload` (P\* by a gamma\* sweep), `residual` (residual propellant at the vehicle payload) or `none` (no search; fly fixed guidance) |
| `gamma_grid_deg` | [8, 36, 2] | gamma\* grid [start, stop, step] in degrees |
| `gamma_refine_halfwidth_deg`, `gamma_xatol_deg`, `gamma_refine_maxiter` | 4, 0.01, 30 | Bounded refine around the best grid point |
| `gamma_root_tol_deg` | 0.01 | Guard against false roots of the kick-angle solve |
| `delta_bracket_deg`, `delta_step_deg`, `delta_xtol_rad` | [0.1, 45], 0.25, 1e-10 | The kick-angle solve |
| `payload_half_bracket_t`, `payload_max_expand`, `payload_backoff_max`, `payload_xtol_kg` | 2.0, 6, 4, 0.5 | The payload root search |
| `brentq_rtol` | 4 machine epsilon (8.88e-16) | scipy's smallest accepted value |
| `final_payload_xtol_kg`, `final_bracket_kg` | 0.05, [20, 1000] | The final verification |
| `search_rtol`, `search_atol_scale`, `final_rtol` | 1e-8, 10, 1e-10 | Integration tolerances during the search and for the reported run |
| `penalty` | `{base_kg: 1.0e6, per_deg_kg: 1.0e4}` | Finite penalty for an infeasible grid point |
| `ltg` | see `config.LtgConfig` | Stage-2 shooting settings (acceptance, scaling, finite-difference steps, guess ladder, pitch bounds) |
| `fixed_gamma_star_deg`, `fixed_ltg_a`, `fixed_ltg_b_per_s` | none | Required with `figure_of_merit: none`, refused otherwise |

The shipped files write every key out with these values.

### `checks`

Thresholds for the per-run checks and the screening-beat rule
([9. Reading results](09-reading-results.md)).

| Key | Default | Meaning |
|---|---|---|
| `closure_tol_mps` | 1e-5 | Rocket-equation closure tolerance |
| `identity_tol_mps` | 1e-5 | Loss-identity tolerance |
| `insertion_e_max` | 1e-6 | Largest eccentricity an inserted run may have |
| `grav_ratio_bounds`, `bp_ratio_bounds` | [0.33, 3.0] | Bounds of mechanism checks M2 (gravity) and M3 (back-pressure) |
| `min_term_mps` | 1.0 | Floor below which M3 and M4 do not apply |
| `max_drag_steer_share` | 0.5 | M4: the largest share drag plus steering may carry |
| `anchor_margin_kg` | 1.5 | Slack of the anchor bound M5 |
| `search_final_flag_rel` | 1e-4 | Flag when search and final payloads differ by more than this fraction |
| `maxq_scan_points`, `maxq_xatol_s` | 256, 1e-6 | Max-Q scan and refine |
| `unconstrained_kick_mps` | 120 | Kicks faster than this are labelled unconstrained |
| `vk_margin_kg` | 5 | The kick-trigger fairness rule |
| `gamma_sensitivity_step_deg` | 0.5 | Step of the gamma\*-sensitivity diagnostic |
| `m2_role` | `diagnostic` | `diagnostic` (M2 reported, blocks nothing; the user's decision of 2026-09-30) or `blocking` |
| `convergence` | `{rel_tol: 1.0e-3, loss_floor_mps: 1.0e-3, margin_floor_kg: 0.5, gamma_resolution_deg: 0.1, tighten_factor: 10, max_step_factor: 0.5}` | The convergence test's settings |

## `baseline`

The baseline is a run: a name, an assist model, ignition settings per stage, where to stop
and the integrator settings. From `experiments/silo_screening_2d.yaml`:

```yaml
baseline:                                  # pad: held down, full thrust exactly at release
  name: pad
  assist: {model: none}
  ignition: {stage1: {t_ign_s: -2.0, reference: release}, stage2: {t_ign_s: 0.0}}
  end: insertion
  integrator: {method: DOP853, rtol: 1.0e-10, planar_max_step_s: 2.0, sample_dt_s: 0.05}
```

| Run key | Default | Meaning |
|---|---|---|
| `name` | required | Run name (a directory name) |
| `assist` | `{model: none}` | The assist model ([5. Assist and ignition](05-assist-and-ignition.md#assist-models)) |
| `ignition` | every stage at its defaults | Per-stage ignition, keyed by the vehicle's stage names ([5](05-assist-and-ignition.md#ignition)) |
| `end` | `stage1_burnout` | Where the run stops: `stage1_burnout`, `all_burnout` (1-D only), `apex`, `impact`, `insertion` (2-D only) |
| `integrator` | below | solve_ivp settings and the output sampling |

### `integrator`

| Key | Default | Meaning |
|---|---|---|
| `method` | `DOP853` | `DOP853` or `RK45` |
| `rtol` | 1e-10 | Relative tolerance. On `planar_2d` it must equal `search.final_rtol` |
| `first_step_s` | 1e-3 | First step [s] |
| `ramp_steps`, `lag_steps_per_tau`, `push_steps` | 10, 4, 50 | Step caps: steps per thrust ramp, per lag time constant, per push |
| `planar_max_step_s` | 2.0 | Step cap of every planar flight phase [s] (ignored by 1-D runs and by the hold and push) |
| `t_max_s` | 3600 | Guard on an open-ended phase [s] |
| `sample_dt_s` | 0.05 | Time-series output interval [s] |

On `planar_2d` no variant, sweep, sensitivity case or bound may change any integrator
setting, `sample_dt_s` included, so compared runs integrate and sample alike.

## `variants`

A variant is a partial run merged over the baseline. It names only what differs. From
`experiments/silo_screening_2d.yaml`:

```yaml
variants:
  pad_instant:  {ignition: {stage1: {t_ign_s: 0.0, startup: {kind: step}}}}          # yardstick, unphysical
  silo_instant: {assist: &silo {model: constant_accel, net_accel_g: 3.0, stroke_m: 100,
                  carriage_mass_t: 0, brake_decel_g: 5, drive_efficiency: 0.5,
                  exhaust_impingement_fraction: 0.0, shaft: vented,
                  track: {angle_deg: 90, exit_altitude_m: 0}},
                 ignition: {stage1: {t_ign_s: 0.0, startup: {kind: step}}}}          # yardstick, unphysical
  silo_cold:        {assist: *silo, ignition: {stage1: {t_ign_s: 0.5}}}                 # 0.5 s delay + 2 s ramp
  silo_hot_full_impinged: {assist: {<<: *silo, exhaust_impingement_fraction: 1.0},
                           ignition: {stage1: {t_ign_s: -2.0, reference: push_start}}}
```

`&silo` defines a YAML anchor, `*silo` reuses it, and `<<: *silo` copies it and then
overrides one key. These are plain YAML features (PyYAML expands them before validation).

### Merge rules

1. **Dicts merge by key; scalars and lists replace.** silo_cold's
   `ignition: {stage1: {t_ign_s: 0.5}}` over the baseline's
   `{stage1: {t_ign_s: -2.0, reference: release}, stage2: {t_ign_s: 0.0}}` gives
   `{stage1: {t_ign_s: 0.5, reference: release}, stage2: {t_ign_s: 0.0}}`.
2. **Switching a discriminator replaces the whole dict.** A dict whose `model` (assist) or
   `kind` (startup) differs from the base's replaces it wholesale, so no stale keys of the
   old choice survive. silo_cold's `assist` switches `model: none` to
   `model: constant_accel`, so the variant's assist dict is used as written.
3. **Exclusive key families.** Some settings can be stated in more than one way. Setting a
   key of one family removes the base's keys of the other families of the same group, at
   the same level; giving keys of two families together at one level is refused.

| Group | Families (use one) |
|---|---|
| Assist push (`constant_accel`) | `{net_accel_g}` or `{exit_speed_mps}` |
| Ramp start (a stage's `ignition`) | `{t_ign_s, reference}`, `{at_depth_m}`, `{at_speed_mps}` or `{at_height_m, height_method}` |

A key counts as given when it is present, even as `null`, so a null is not a way to unset a
key. One consequence: `{<<: *silo, exit_speed_mps: 76.7}` is refused, because the anchor
brings `net_accel_g` into the same dict. Write the assist dict out instead (an example is in
[5. Assist and ignition](05-assist-and-ignition.md#stating-the-push-two-ways)).

Variants merge over the baseline only, never over each other.

## `sweeps`

A sweep is a full grid over dotted paths, applied to one named run. `launchsim sweep` runs
every sweep of a file; `launchsim run` does not. From `experiments/silo_screening_2d.yaml`:

```yaml
sweeps:
  - {of: silo_cold, axes: {assist.net_accel_g: [0.5, 1, 3, 5], assist.stroke_m: [50, 100, 300]}}
  - {of: silo_cold, axes: {ignition.stage1.t_ign_s: [0, 0.5, 1.0], ignition.stage1.startup.t_ramp_s: [1, 2, 3]}}
  - {of: silo_cold_lag, axes: {ignition.stage1.startup.tau_s: [1, 2, 3]}}
```

The first sweep has 4 x 3 = 12 points, the second 9, the third 3. Each point is named
`run_0001`, `run_0002`, ... within its sweep and written to `sweep_<n>/run_<nnnn>/`
([8. Outputs](08-outputs.md#a-sweep-directory)).

**Dotted paths.** Each segment is a dict key; a list item is addressed by its `name` (as in
`vehicle.stages.stage1.dry_mass_t`) or by an integer index (as in
`vehicle.screening.stage_isp_eff_s.0`). Paths that start with `vehicle.` change the vehicle
in memory, and a number aimed at a sourced quantity becomes
`{value, assumed: true, note: override}`. A path sets exactly one key; its siblings stay,
apart from the discriminator and family rules above. A dict given as a path's value
replaces the node at that path whole.

The family rule applies to sweep axes too. Written for this manual: over silo_cold, which
states its push by `net_accel_g`, the axis `assist.exit_speed_mps: [50, 77, 100]` leaves only
the exit speed at each point; the axis `ignition.stage1.at_depth_m: [0, 25, 50]` removes the
inherited `t_ign_s` and `reference`.

**Paired sweeps** (`paired: true`, 2-D only) re-run the baseline at every point with the same
overrides, so each point is compared with its own pad. Their axes may be `guidance.*` paths
(only with `label: guidance_study`) and `vehicle.*` paths. On `planar_2d`, a sweep of
`vehicle.*` paths must be paired, so a vehicle change is never booked as an assist gain, and
a paired sweep of the baseline itself is refused (it would have no pair). From
`experiments/guidance_trigger_2d.yaml`:

```yaml
label: guidance_study
sweeps:
  - {of: silo_cold, paired: true, axes: {guidance.kick.v_kick_mps: [30, 50, 80, 120]}}
```

Each point's paired pad is written beside it as `run_<nnnn>__pad`.

## `sensitivity`

Each listed parameter is run at plus and minus the given fraction (between 0 and 1) for
each listed run. CLAUDE.md asks for headline numbers to get a +/-10% check on stage-1 dry
mass, Isp, C_D and drive efficiency. From `experiments/silo_screening_2d.yaml`:

```yaml
sensitivity:
  of: [silo_cold, silo_hot_full]
  params: {vehicle.stages.stage1.dry_mass_t: 0.10, vehicle.stages.stage1.engine.isp_vac_s: 0.10,
           vehicle.stages.stage2.engine.isp_vac_s: 0.10, vehicle.aero.cd_scale: 0.10,
           vehicle.screening.stage_isp_eff_s.0: 0.10, assist.drive_efficiency: 0.10}
```

That is 2 runs x 6 parameters x 2 signs = 24 cases. A case is named
`<run>__<param>__+0.1` (or `-0.1`). Each is compared with the unchanged baseline and, for a
vehicle parameter, also with the baseline re-run under the same perturbation (the fair
comparison: same vehicle on both sides). `launchsim run --no-sensitivity` skips them; with
`--variant` only the cases of the runs that ran are flown.

## `bounds` (2-D)

A bound re-runs the listed variants with overrides and compares them with the baseline
re-run under the same overrides. From `experiments/silo_screening_2d.yaml`:

```yaml
bounds:
  - {name: aero_bound, of: [silo_cold], overrides: {vehicle.aero.reference_area_m2: 21.24},
     paired_baseline: true}                # A_ref of the 5.2 m fairing section; pad re-run too
```

The runs are named `silo_cold__aero_bound` and `pad__aero_bound`. `of` lists variants only
(the baseline is always re-run), `paired_baseline` must be `true`, and shared-block paths
are refused. Only the `planar_2d` pipeline flies bounds: a `vertical_1d` file that declares
one is validated, but the bound is not run.

## `cases` (calibration only)

With `label: calibration`, `cases` are independent runs of the baseline that may use another
vehicle file, a partial `site` or `target_orbit`, or `vehicle.` overrides. They are never
compared with the baseline. From `experiments/calibration_f9_2d.yaml`:

```yaml
cases:                                     # independent runs, never compared
  readme_loads: {vehicle: configs/vehicles/generic_f9_class_2d_readme_loads.yaml}      # set A
  aref_fairing: {overrides: {vehicle.aero.reference_area_m2: 21.24}}   # 5.2 m fairing section
  alt_250: {target_orbit: {altitude_km: 250}}
  no_rotation: {site: {include_rotation: false}}   # rotation-credit diagnostic, not quoted in advance
```

A case must change at least one of the four. As with bounds, only the `planar_2d` pipeline
flies cases, and `run --variant` skips them. A calibration run also records whether
`configs/` and `experiments/` were committed (its pre-registration state); see
[10. Validation](10-validation.md#calibration-is-not-validation).

## Rules that catch common mistakes

| Rule | Refusal you will see (shortened) |
|---|---|
| A 2-D site states all three keys | `a planar_2d site needs latitude_deg, azimuth_deg and include_rotation, each given explicitly` |
| Earth rotation needs 2-D | `include_rotation: true is a Phase 2 feature: it needs dynamics: planar_2d` |
| Shared blocks stay shared | `variant 'x' sets 'guidance': guidance is an experiment-level shared block ...` |
| 2-D integrator is locked | `... on planar_2d no integrator setting may differ between runs ...` |
| 2-D rtol equals the final search rtol | `planar_2d: integrator.rtol (...) must equal search.final_rtol (...)` |
| A searched 2-D run ends at insertion | `search.figure_of_merit: payload needs end: insertion ...` |
| A 2-D vehicle sweep is paired | `sweep 1: on planar_2d a sweep of vehicle.* paths needs paired: true ...` |
| One family per setting | `keys [...] of two exclusive families are given together; state the setting one way only ...` |
| Names are directory names | `run name 'baseline' is reserved by the results layout` |

More are listed in [11. Troubleshooting](11-troubleshooting.md#configuration-errors).

## Writing your own experiment

- Start from a copy of a shipped file under a new name. Keep the pad baseline and the
  shared blocks as they are, so your runs compare with the recorded ones.
- Never change baseline settings without re-running every variant compared against it.
- Never tune parameters to make an assist look better; CLAUDE.md treats that as a rule, and
  so should a reader of your results.
- Run with `--no-sensitivity` while you iterate; run the sensitivity cases before you quote
  a number.

Next: [5. Assist and ignition](05-assist-and-ignition.md)
