# Code survey: config, search, run pipeline, comparison and summary

Read-only survey made in the SP1 planning session on 2026-09-30. Line numbers are for
commit 2eebcae and drift as SP1 edits the files; re-check before relying on one. Input to
docs/phases/SP1-fuel-offload-planar.md.

## A. config.py (src/launchsim/config.py)

**Constants (lines 65-135)**

- `PLANAR_SHARED_KEYS = ("guidance","search","target_orbit","checks")` (86) and
  `RUN_SHARED_KEYS = ("dynamics","site")` (88).
- `SHARED_PATH_ROOTS` (92) is those six names plus `planar`.
- Paired sweeps: `PAIRED_SWEEP_ROOT="guidance"` (95), `VEHICLE_ROOT="vehicle"` (97),
  `PAIRED_SWEEP_ROOTS` (99).
- Figures of merit: `FigureOfMerit = Literal["payload","residual","none"]` (105),
  `SEARCHED_FIGURES=("payload","residual")` (106), `NO_SEARCH` (108).
- `SWITCH_KEYS=("model","kind")` (70): a dict whose discriminator changes replaces the
  base dict wholesale on merge.

**ExperimentConfig (1325-1490)**

- Fields (1345-1359): `name, vehicle: str, label: calibration|guidance_study|None,
  dynamics, site, guidance, search, target_orbit, checks, baseline: RunConfig,
  variants: dict[str, dict[str, Any]], sweeps: list[SweepConfig],
  sensitivity: SensitivityConfig|None, bounds: list[BoundConfig],
  cases: dict[str, CaseConfig]`.
- `_inject_into_baseline` (1361) refuses shared blocks in the raw baseline, then injects
  them.
- `_shared_blocks_stay_shared` (1388) refuses shared paths in variants, sweeps,
  sensitivity and bounds, and on planar locks the integrator (`_lock_integrator` 1412).
- `_labelled_features` (1429-1468): an unpaired planar `vehicle.*` sweep fails with
  "sweep {k}: on planar_2d a sweep of vehicle.* paths needs paired: true (the baseline is
  re-run with the same vehicle, as in a sensitivity case or a bound)". Paired roots must
  be a subset of `{guidance, vehicle}`. "a paired sweep of the baseline has no pair; sweep
  a variant".
- `_bound_and_case_names` (1470) checks name collisions.

**Figure-of-merit selection.** It exists only as `SearchConfig.figure_of_merit` (840),
inside the shared `search` block. It is therefore identical for every run and part of
`budget_id()` (981-985, "every field, defaults included"). Per run,
`RunConfig.figure_of_merit` (1162-1170) returns `none` when the search is skipped.
`_dynamics_rules` (1140-1148) requires `end: insertion` and a target orbit for a searched
figure.

**Other shared blocks**

- `SearchConfig` (820-985); `LtgConfig` (751), `PenaltyConfig` (737).
- `ChecksConfig` (1013-1058): `m2_role`, `convergence: ConvergenceConfig` (988).
- `TargetOrbitConfig` (719): `kind: circular`, `altitude_km`, property `radius_m`.
- `GuidanceConfig` (708), `KickConfig` (686).
- `PlanarShared` (1061) is what gets injected as `RunConfig.planar`.

**Sweeps, sensitivity, bounds, cases**

- `SweepConfig` (1189-1207): `of, axes: dict[str, list], paired: bool=False`. The
  docstring says "a vehicle change is never booked as an assist gain".
- `SensitivityConfig` (1210-1221): `of: list[str], params: dict[str, float]`, fractions in
  (0, 1).
- `BoundConfig` (1224-1233): `name, of (min 1), overrides, paired_baseline: Literal[True]`.
- `CaseConfig` (1236-1257): calibration only; never compared; `overrides` take `vehicle.`
  paths only.

**ConstantAccelConfig (537-568), quoted**

```
model: Literal["constant_accel"]
net_accel_g: float = Field(gt=0.0)          # required, no default
stroke_m: float = Field(gt=0.0)
carriage_mass_t: float = Field(default=0.0, ge=0.0)
brake_decel_g: float = Field(gt=0.0)
drive_efficiency: float = Field(default=1.0, gt=0.0, le=1.0)
exhaust_impingement_fraction: float = Field(default=0.0, ge=0.0, le=1.0)
shaft: Literal["vented"] = "vented"
allow_negative_drive_force: bool = False
track: TrackConfig = TrackConfig()
```

- There is no model validator. The SI properties are
  `net_accel_mps2 = units.from_g(net_accel_g)` (556), `carriage_mass_kg`,
  `brake_decel_mps2`.
- `TrackConfig` (508): `angle_deg` must equal 90 ("a Phase 3 feature");
  `exit_altitude_m = 0.0`.
- `AssistConfig` (584) is the discriminated union on `model`.
- `PlannedAssistConfig` (571) has `extra="allow"`, so the "planned for Phase 3" message
  wins over an extra-key error.

**Ignition models**

- `IgnitionConfig` (624-636): `t_ign_s: float = 0.0`,
  `reference: Literal["release","push_start"] = "release"`,
  `startup: StartupOverride|None`, `fails: bool = False`. It has no validator of its own,
  and its `extra="forbid"` is why `at_depth_m` fails today.
- `StartupOverride.resolve(base)` (589-621).
- `RunConfig._ignition_rules` (1172-1182): `fails` requires `end: impact`; with
  `assist.model == "none"`, push_start fails with "ignition {stage}: reference push_start
  needs an assist model (a pad run has no push)".
- `resolve_run` (1764-1779): later stages may not use push_start ("only for the first
  stage") or `t_ign_s < 0`, and startup overrides must resolve against the vehicle.
- `RunConfig.ignition_for` (1184) falls back to `IgnitionConfig()` for an unlisted stage.

**Merging and resolution**

- `merge_run_dicts(base, override)` (1519): dicts merge by key; scalars and lists replace.
- `apply_overrides(run_dict, overrides, vehicle_dict) -> (run, vehicle)` (1606-1626): a
  `vehicle.` path goes to the vehicle dict through `_set_path(..., quantity=True)`
  (1585-1603). A number aimed at a Quantity becomes
  `{"value": v, "assumed": True, "note": "override"}`.
- `resolve_experiment(exp_dict, vehicle_dict, load_vehicle=None) -> ResolvedExperiment`
  (1858-1918):
  - baseline: `base_dict = inject_shared(exp_dict["baseline"], shared_run_blocks(exp_dict))`
    (1874)
  - variants: `resolve_run(vname, merge_run_dicts(base_dict, override), vehicle_dict)`
    (1878); every variant gets the experiment vehicle
  - sweep points (1881-1896) and their paired baselines:
    `_perturb(baseline, run_overrides, ...)` (1893)
  - sensitivity cases (1898-1910)
  - bounds: `_resolve_bound` (1812)
  - cases: `_resolve_case` (1826)
- `resolve_run(name, run_dict, vehicle_dict) -> ResolvedRun` (1747). `ResolvedRun` (1638)
  holds `name, run, vehicle, run_dict, vehicle_dict` and has `to_vehicle()`.

**Where `vehicle:` in a variant is refused, and why.** There is no explicit refusal. The
variant dict is merged into the run dict, and `RunConfig` (base `_Model`, `extra="forbid"`,
line 141) rejects the key inside `resolve_run` (1751). The error, from
docs/findings/probes/handoff-2026-09-30/probe_resolve.out line 29:
`ValidationError: 1 validation error for RunConfig vehicle   Extra inputs are not permitted`.

- A dotted `vehicle.stages...` key fails the same way: the `vehicle` root is not in
  `SHARED_PATH_ROOTS`, so `_refuse_shared_path` lets it through, and the merge stores it
  as a literal key.
- The rationale is in the ExperimentConfig docstring ("Variant values are partial run
  dicts merged over the baseline"), in SweepConfig (1192-1196) and in docs/physics.md
  lines 4475-4477.

**Sensitivity with a vehicle path (1898-1910)**

- `_nominal_value(parent, param)` (1799) reads `_read_any(...)`, which unwraps the
  Quantity.
- Each case sets `value = nominal*(1 +/- f)`, applies it with
  `_perturb(parent, {param: value}, "sensitivity")`, and is named
  `f"{of}__{param}__{'+'|'-'}{fraction:g}"`.
- The comparison baselines are in `compare._run_planar_sensitivity` (1320-1403):
  - against the unchanged pad: `compare_planar(..., attribution_required=False)`
    (1364-1371), which gives `not_checked`
  - against a same-perturbation pad:
    `resolve_run(baseline.name, resolved.baseline.run_dict, case.run.vehicle_dict)`
    (1379-1381), with attribution
- Both the + and the - case always run.

**Vehicle sweeps (`paired: true`).** Each point applies
`_perturb(parent, run_overrides, ...)` and also `_perturb(baseline, run_overrides, ...)`,
named `run_NNNN__<baseline>` (`paired_baseline_name` 1507). So the pad is offloaded too,
as the handoff probe showed.

**Tests that pin the resolved dicts**

- `tests/test_config_planar.py::test_phase1_resolved_run_dicts_are_byte_identical`
  (257-278) compares `json.dumps` with key order against
  `tests/data/golden/{silo_screening_1d,vertical_1d_paths}/experiment/resolved_config.json`
  and `objects.json`.
- `::test_inject_shared_is_a_plain_copy_when_nothing_is_declared` (281).
- `::test_calibration_and_silo_baselines_differ_only_in_sample_dt` (170).
- `tests/golden_1d_support.py`: `EXACT_SUBTREES = {"run_dict","vehicle_dict","overrides"}`
  (115) are compared exactly.

## B. search.py (src/launchsim/search.py)

**Budget, store, context**

- `SearchBudget` (186); `from_config(search, checks)` (256).
  - Payload half-widths: `payload_halves_kg = half*2**k, k=0..payload_max_expand` (270),
    i.e. 2, 4, ... 128 t.
  - Final half-widths: `doubling_halves(20, 1000)` = 20, 40, ... 640, 1000 kg (325).
  - `tightened(factor)` (295).
- `WarmStore` (351). `claim(owner)` (369) raises "this WarmStore belongs to another search
  problem" if a store is reused. The kick cache is keyed by `(payload, tol class)`.
- `SearchProblem` and `RecordingProblem` protocols (460-495): `budget`, `payload_kg`,
  `evaluate(payload_kg, gamma_star_rad, warm, mode, *, seed=None) -> ResidualResult`,
  `record(res) -> RecordedRun`.
- `SearchContext` (501), fields `vehicle, ignition, guidance, env, target, settings,
  budget, assist, track, z_ground_m, end`.
  - `from_run(run, vehicle, checks=None)` (533).
  - `evaluate(...)` (609): kick point, delta solve, LTG with virtual propellant.
  - `record(res) -> RecordedRun` (652): re-flies the evaluation with dense output and the
    real depletion event.
  - `planner(payload, mode)` uses `with_payload(self.vehicle, ...)` (585).

**Public search functions**

- `residual(problem, payload_kg, gamma_star_rad, warm, mode=SEARCH_MODE)` (714). Rung 2:
  m_res and dv_margin at a fixed (P, gamma*).
- `payload_root(fn, hint_kg, halves_kg, *, backoff_max, xtol_kg, rtol,
  gamma_star_rad=nan, mode=SEARCH_MODE, low_toward_hint=False) -> PayloadResult`
  (805-949).
  - Bracket: `[max(0, hint-h), hint+h]`. The low end must have m_res >= 0 and the high end
    m_res < 0; each end expands through `halves_kg`. An infeasible end backs off halfway,
    at most `backoff_max` times. Running out raises `SearchFailed('bracket')`.
  - m_res(0) < 0 gives `no_orbit`.
  - Then brentq through `_PayloadLog`; an infeasible evaluation inside the bracket raises
    `SearchFailed('root')`.
  - It returns P_lo, the largest logged payload with m_res >= 0, not the interpolated
    root. It reads the abscissa from `res.payload_kg`.
- `payload_capacity(problem, gamma_star_rad, hint_kg, warm, mode=SEARCH_MODE)` (973).
  Rung 3 with the budget's halves, backoffs, xtol 0.5 kg and rtol 4 eps.
- `optimise_gamma(problem, warm, payload_kg, *, find_payload=True) -> GammaResult` (1335).
  - Steps: 15-point grid at P0, centre-out, with warm retries (`_evaluate_grid` 1114);
    edge check; P1; bounded-Brent `_refine` (1221) over +/-4 deg; P2.
  - With `find_payload=False` the refine runs at P0, which is the `residual` figure.
- `final_verify(problem, gamma_star_rad, p_lo_kg, warm) -> FinalResult` (1568).
  - Final-mode `payload_root`, bracket starting at 20 kg, `low_toward_hint=True`.
  - xtol = `min(0.05, 0.05/|slope|)` (`_final_xtol` 1516), then `_bisect_to_residual`
    (1529).
  - The recorded run must end inserted with 0 <= m_res < 0.05 kg (`_check_recorded` 1492).
- `final_residual(problem, gamma_star_rad, payload_kg, warm) -> FinalResult` (1635). One
  final evaluation plus its recorded run.
- `run_search(problem, warm=None) -> SearchRecord` (1722).
  - Dispatch: `if fom not in ("payload", "residual"): raise ValueError(...)` (1733).
  - payload: `optimise_gamma`, then `final_verify` from P2, then `_rung2_at_p0` (1710).
  - `SearchFailed` becomes a record with status `search_failed`.
- `as_plain(obj)` (1784), plus `backoff_flags(name, payload)` (958) and `penalty_kg`
  (1106).

**Cost.** docs/physics.md 2173-2179 gives 38 evaluations for the gate pad: 15 grid, 18 in
P1 + refine + P2, 4 final, 1 rung 2 at P0. That is about 0.2 s per evaluation. With the
2 s cap a searched run takes 12.1 s for the pad and 14.1 s for silo_cold (2650);
`sim.matched_run` with neighbours takes 0.83 s (2578).

**Flags and failures**

- `_refine` appends a window-shift flag and "refine_capped: gamma*_ref ... again within
  gamma_xatol of an interior edge of the shifted window ..." (1304-1310).
- Other sources: a maxiter flag, a grid fallback, P1/P2/final backoff flags,
  `search_final_mismatch`, `search_vs_final_payload`.
- All of these go into `SearchRecord.flags`, then `run_flags` in `sim.run_planar`, then
  `Result.flags`, then the summary Flags section.
- `SEARCH_FAILURE_KINDS` (112) are edge, grid, bracket, root, final_bracket, final_run.
- Sentinels live in `src/launchsim/guidance.py`:
  `SENTINEL_GAMMA_RAD = {"impact": -pi/2, "kick_timeout": pi}` (80), applied inside
  `solve_delta_for_gamma` (367, around 410). A false root raises `GuidanceFailure`, which
  becomes a grid penalty.

## C. sim.py and results_io.py

src/launchsim/sim.py

- `run_resolved(resolved) -> RunResult` (841) calls
  `run(resolved.run, resolved.to_vehicle())`.
- `run(run_config, vehicle) -> Result` (812) dispatches planar runs to `run_planar`.
- `run_planar(run_config, vehicle)` (1393-1435):
  - `planar_setup` (955) builds `PlanarSetup` (935).
  - `search_context(setup, vehicle, end)` (981) is a second context builder besides
    `SearchContext.from_run`.
  - `run_search`, then `flown = with_payload(vehicle, record.final.at_final.payload_kg)`,
    then `simulate_planar(...)` (1109).
  - `simulate_planar` runs the per-run checks in `_run_checks` (1081): closure, identity
    and insertion e give `bug_suspect`.
- `ignition_specs(run_config, vehicle)` (803) is one of two places IgnitionSpecs are
  built; the other is `search.py:549`.
- `matched_run(resolved, result, payload_kg, *, neighbours=False) -> MatchedRun|None`
  (1480) re-evaluates a variant at P_ref. This is the pattern for extra per-variant work
  that needs the baseline's P*.
- `rerun_planar` (1438) and `rerun_resolved` (1472) handle energy-only reuse.

src/launchsim/results_io.py

- `run_experiment(resolved, out_root, plots, only_variant=None, repo_root=None,
  sensitivity=True)` (703):
  - runs the baseline, then each variant with no baseline passed in (741-742)
  - then `planar_experiment_result` (945): `run_sensitivity` (964), `planar_comparisons`
    (864: P_ref = `reference_payload_kg(baseline)`, `sim.matched_run`, `compare_planar`),
    `planar_bounds` (903: the pair is run once per bound)
- `run_sweep` (1068) and `_run_sweeps_into` (1103): planar points use
  `point.paired_baseline` as `ref` when paired (1157-1160).
- Provenance:
  - `git_info` (319) runs on every run.
  - `preregistration_state` (377) runs only for `label == calibration` (753-754).
  - `_resolved_config_dict` (509) already writes a run's vehicle dict when it differs from
    the baseline's (516-517).
  - `_metrics_dict` (573) is where planar records such as `bounds` and `cases` are added.

## D. compare.py, summary.py, metrics_planar.py

**`compare_planar(result, baseline, vehicle, *, checks, name="", matched=None,
matched_baseline=None, anchor=None, attribution_required=True)`**
(src/launchsim/compare.py 1124-1241)

- `delta_<metric>` for every numeric metric (1165-1169). This covers losses, max-Q, loads,
  energy and facility length.
- `payload_delta_kg` (1171).
- Yardsticks (1173-1196): `payload_gain_kg(vehicle, v0)` at P0 and at the baseline's P*,
  the stricter one in `screening_yardstick_kg`, then `payload_beyond_screening_kg` and
  `beats_screening`.
- Upper-bound flags (1197-1214).
- `matched_attribution` (657, `ATTRIBUTION_TERMS` 554).
- Check records (1219-1240). `_attribution_check` (1080) fails when an attribution is
  required, missing, and the run beats the yardstick. `screening_status` is `bug_suspect`,
  `not_checked` or `ok`.

**Energy, efficiency, power** (src/launchsim/metrics_planar.py)

- `planar_track_metrics` (922-982):
  - `drive_energy_J = budget.work_drive`, `electrical = work_in / assist.efficiency` (945)
  - `drive_power_peak_W` from `drive_power_extrema` (946)
  - `facility_length_m = assist.facility_length_m(track, v_exit)`
- Aliases `assist_energy_J/kWh` and `peak_drive_power_W` come from
  src/launchsim/metrics.py 101-106.
- `PAD_ASSIST_ZEROS` (841): the pad reports these as 0.
- The budget comes from `losses.assist_energy_budget` (src/launchsim/losses.py 130),
  called in `sim.simulate_planar` 1154-1160.
- `liftoff_mass_kg` is in `_release_items` (757).

**Screening-estimate check in the summary** (src/launchsim/summary.py)

- `screening_line` (1075) prints "beats it by ... (the attribution must explain this)".
- `planar_checks_section` (1144) prints `UNEXPLAINED_BEAT_TEXT` (1175) for comparisons
  that are `not_checked` and beat the yardstick.
- `blocked_lines` (1236) prints `FINDINGS_BLOCKED` (733).
- The 1-D version is `compare.unexplained_gain_mps` (323-327) and
  `summary.payload_yardstick_lines` (441).

**Patterns for a new "propellant saved" block**

- `PLANAR_VARIANT_ROWS` (759-858): `(label, source, key)`, where source `"m"` is a metric
  and `"c"` is a comparison item.
- `planar_variant_rows` (873-883) appends `PLANAR_FAILED_ROWS` (862) only when some run
  carries the key. An offload row block can be gated the same way.
- Alternatively, add a section like `bounds_section` (1316) to
  `planar_experiment_summary` (1392-1450, between "## Variants" and "## Bounds"), plus a
  list in `_metrics_dict`.
- Keep any new keys out of `PLANAR_REQUIRED_METRICS` (`metrics_planar.py` 270):
  `test_planar_pipeline` requires every required key to be filled for every searched run,
  and the pad would have none.

## E. vehicle.py (src/launchsim/vehicle.py)

- `Stage` (156): `name, dry_mass_kg, propellant_mass_kg, engine, n_engines, startup,
  coast_before_ignition_s`. It requires propellant > 0.
- `Vehicle` (474): `stages, fairing_mass_kg, payload_mass_kg, fairing_drop,
  screening_isp_s, aero`, plus `liftoff_mass_kg()` (571).
- Copy helpers that already exist: `with_payload` (580), `with_cd_scale` (586),
  **`with_stage_propellant(vehicle, i, propellant_kg)` (595)**. No dry-mass helper.
- **`stage1_propellant_saved_kg(vehicle, v_assist_mps)` (650)** is the ideal-screening
  offload at fixed payload, a ready-made yardstick. It is tested in
  tests/test_vehicle_screening.py 118-140.
- There is no mixture ratio and no RP-1 or LOX data anywhere in code. The split exists
  only inside source strings: configs/vehicles/generic_f9_class_2d.yaml line 47
  ("first-stage propellant 287.4 LOX + 123.5 RP-1") and line 59 ("75.2 LOX + 32.3 RP-1").
  No heating value appears anywhere in src/ (`constants.py` has none).

## F. Tests (gates to keep green)

- tests/test_golden_1d.py with tests/golden_1d_support.py. Every 1-D output is pinned:
  every metric key and its order; flags and assumption strings; `summary.md` text;
  `metrics.json`, `resolved_config`; `run_dict`/`vehicle_dict` exactly; `sweep_index.csv`
  columns (`SWEEP_INDEX_METRICS`).
- tests/test_config.py: 1-D schema and units (`test_constant_accel_units` 295);
  push_start rules (249); `test_run_defaults` (322) asserts `t_ign_s == 0.0` and
  `reference == "release"`; "variants keep the baseline vehicle" (542-544).
- tests/test_config_planar.py:
  - shipped planar experiments resolve (113)
  - shared blocks identical across `PLANAR_EXPERIMENTS`, with one `budget_id` (155-167)
  - `test_shipped_blocks_state_every_threshold` (184-207) checks the `model_fields` of
    SearchConfig, LtgConfig, ChecksConfig, ConvergenceConfig, GuidanceConfig, KickConfig,
    Stage2GuidanceConfig and PenaltyConfig against the YAML
  - Phase 1 byte-identity (257)
  - paired-sweep and vehicle-sweep rules (490-569), sensitivity vehicle paths (658), aero
    bound (687)
  - `test_every_shipped_planar_experiment_is_checked` (805): any new planar YAML must be
    added to `PLANAR_EXPERIMENTS` (52)
  - explicit planar cap (818)
- tests/test_search.py: toy closed-form sweep, flags and failure kinds; the `_contexts`
  helper (702) uses `dataclasses.replace(ctx, vehicle=...)`, which can be copied for
  propellant tests.
- tests/test_payload_search.py: payload closed form (`SpeedTargetToy`, 103), bracket and
  backoff logic, final verification.
- tests/test_planar_pipeline.py: every required metric present (119); summary rows (161)
  and pinned assumptions (329); unexplained-beat and not_checked behaviour (592); CLI
  loads every shipped planar experiment (384).
- tests/test_closure.py: `matched_attribution`.
- tests/test_results_io.py: layout, JSON, git.
- tests/test_preregistration.py: frozen-input state.
- tests/test_calibration.py (slow): P* regression against
  tests/data/calibration_record.json, which also records `search_budget_id` without
  asserting it.
- tests/test_silo.py::test_assist_registry_builds_every_config_model (472) reads
  `ConstantAccelConfig.model_fields["model"]`.
- tests/test_vehicle_screening.py: offload screening.
- No test enumerates the allowed keys of the assist or ignition config.

## G. Probes (docs/findings/probes/handoff-2026-09-30/)

**`probe_offload.py`**

1. Loads `silo_screening_2d.yaml` and the gate vehicle with `yaml.safe_load`, and drops
   sweeps, sensitivity and bounds.
2. Keeps only `silo_cold` and adds a paired sweep
   `vehicle.stages.stage1.propellant_mass_t` over 410.9 x (1 - {0, 0.02, 0.05, 0.10}).
3. Calls `resolve_experiment(exp0, veh)`, then `sim.run_resolved(point.run)` and
   `sim.run_resolved(point.paired_baseline)`, and reads `rr.result.metrics["payload_kg"]`
   and the other headline metrics.
4. The offload is read off by hand, where the silo's P*(m_p1) crosses the full-load pad's
   P*.

**`probe_resolve.py`** uses `resolve_experiment` and `build_assist`. It shows: a
`vehicle:` key in a variant fails; an unpaired planar vehicle sweep fails; a paired sweep,
a bound and a sensitivity case all resolve, but each one offloads or pairs the pad;
`at_depth_m` fails as an extra key; a paired sweep of the baseline fails.

## Reusable functions to build on

- `vehicle.with_stage_propellant` and `with_payload`, and `stage1_propellant_saved_kg` as
  the offload yardstick.
- `dataclasses.replace(ctx, vehicle=...)` on `SearchContext`; `optimise_gamma` and
  `final_verify` on any `SearchProblem`. Use a fresh `WarmStore` for each problem.
- `config.apply_overrides`, `_perturb` and `resolve_run` to build an offloaded vehicle
  dict, as `_run_planar_sensitivity` and `planar_bounds` do.
- `compare.reference_payload_kg(baseline)` for P*, and `sim.matched_run` as the model for
  a post-pass that needs the baseline result.
- `compare_planar(..., attribution_required=False)` for comparisons across two vehicles;
  `attributed_comparison` for same-vehicle pairs.
- The `PLANAR_FAILED_ROWS` gating, `bounds_section` and `_metrics_dict` for reporting;
  `electrical_energy_J` already exists per run.
- `ConstantAccelAssist.exit_speed_mps` and `push_time_s`
  (src/launchsim/assist/constant_accel.py 135-141) and `IgnitionSpec.t_ign_abs_s`
  (src/launchsim/phases/prelude.py 104) for the depth and speed closed forms.

## Constraints that make the changes awkward

1. **The figure of merit sits in the shared `search` block.** A new experiment with a new
   `figure_of_merit` value breaks the shared-block tests, and adding any `SearchConfig`
   field changes every experiment's `budget_id` and forces editing all four shipped
   YAMLs, which are pre-registered inputs. A separate top-level `offload:` block avoids
   this.
2. **The offload needs the baseline's P* before the variant runs.** `run_planar` is
   per-run and `run_experiment` gives variants no baseline, so the offload must be a
   post-pass in `results_io`, like `planar_comparisons`.
3. **The matched-payload attribution assumes the same ideal delta-v on both sides.** An
   offloaded variant against the unchanged pad leaves a residual equal to that
   difference, so the attribution check fails and gives `bug_suspect`. Use a separate
   cross-vehicle decomposition.
4. **`payload_root` reads `res.payload_kg` internally** (lines 801, 890, 907, 911, 936);
   an adapter problem that puts the offload in that field avoids generalising it.
5. **Per-variant vehicle overrides** would have to be popped out of the variant before
   `merge_run_dicts`; `test_config.py` 542-544 asserts variants keep the baseline vehicle.
   The design keeps vehicle changes out of variants.
6. **Golden 1-D.** New metrics, assumption text or summary rows must not appear on 1-D
   runs. The net_accel text of `ConstantAccelAssist.assumptions()` must stay as it is,
   and so must `VARIANT_ROWS` and `SWEEP_INDEX_METRICS`.
7. **Merge semantics for exit speed and ignition triggers.** Only `model` and `kind`
   replace a dict wholesale; mutually exclusive keys need the exclusive-family rule. Also,
   src/launchsim/replay.py 478 and 675 read the raw `net_accel_g` for labels.
8. **Ignition by depth or speed.** `IgnitionConfig` cannot see the assist, so the
   conversion belongs at both IgnitionSpec build sites (`sim.py:807`, `search.py:550`)
   through one resolver. The `t_ign_s` default of 0.0 is pinned by `test_run_defaults`.
9. **Cost.** Each propellant trial is a full residual or payload search of about 25-38
   evaluations (5-14 s).
10. **RP-1 fraction and heating value.** Both are needed as sourced inputs. They cannot go
    into the gate vehicle file, so they live in the experiment's offload block. Derived
    run names must stay within `MAX_NAME_LEN` = 64 characters.
