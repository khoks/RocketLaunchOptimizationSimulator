# Design input: launch settings and fixed-payload propellant offload (SP1)

Produced in the SP1 planning session on 2026-09-30 by a read-only design agent and checked
against the code at commit 2eebcae. Line numbers refer to that commit and drift as SP1
edits the files; re-check before relying on one. `src\` means `src\launchsim\`. This is an
input to docs/phases/SP1-fuel-offload-planar.md, which holds the steps as approved.

## 1. Claim check (planning claims against the code)

| # | Claim | Verdict | Correction |
|---|---|---|---|
| 1 | `search.figure_of_merit` is a shared block; a new figure of merit would touch pre-registered files | Confirmed | `tests\test_config_planar.py:184-196` also requires every `SearchConfig` field to be written in each shipped YAML, so a new field would edit pre-registered files. A separate `offload:` block plus a post-pass is right. |
| 2 | Sensitivity is the only path comparing a vehicle change against the unchanged pad | Partly wrong | `results_io.planar_bounds` (903-942) already re-runs a variant with `vehicle.` overrides and compares it with a paired pad (attributed) and with the unchanged pad (`comparison_vs_nominal`, not attributed). The plain "reduce propellant" knob is one input conversion away from a bound. |
| 3 | `payload_root` must be generalised to root-find on propellant | Simpler route exists | `optimise_gamma` and `final_verify` run on any `SearchProblem` (`search.py:460-495`), so an adapter can present the offload as the abscissa. |
| 4 | An offload decomposition can close with existing integrals | Confirmed | Section 2d. |
| 5 | Ignition specs are built at two sites; `FlightStart.t_ign1_s = None` means failed ignition | Confirmed | A fourth `FlightStart` consumer is `sim._solve_fixed_delta` (1345-1348). |
| 6 | Merge pitfall for mutually exclusive keys | Confirmed | Every variant inherits the pad's `t_ign_s: -2.0`, so a variant that sets only `at_depth_m` always ends up with both keys. Explicit nulls or a `trigger` discriminator do not fix sweep axes. |
| 7 | Golden 1-D pins metric keys, summary text and resolved dicts | Confirmed | Make no 1-D metric, summary or assumption change at all; achieved ramp-start values are already in 1-D `events.csv`. |
| 8-10 | Reporting patterns, missing propellant split, costs | Confirmed | `ideal_dv_at_payload_mps` (D_id) is already a per-run metric. |

**One finding changes the design.** `docs\physics.md` "Virtual propellant" (1961-1966)
records that 975 kg more real stage-2 propellant moved m_res from -975.0 to -990.3 kg. The
marginal value of stage-2 propellant is about zero or slightly negative at full load.
Consequences:

- m_res is not monotone in a stage-2 offload, and the pad itself may be able to offload
  stage 2 at P_ref.
- The stage-2 and both-stage numbers will be large and ill-conditioned.
- They are only honest with a pad control solve reported beside them (section 2b).

## 2. Design decisions

**a. No vehicle keys in variants.** `planar_comparisons` (864) would run
`matched_attribution` on a different-vehicle variant; its residual would equal the D_id
difference and give a false `bug_suspect`. Vehicle-changed runs go in `offload.cases`,
built on the bounds machinery (`_perturb`, `resolve_run`, `attributed_comparison`).

**b. Offload definition.**

- Offload x >= 0 is removed along a mode direction; dry mass is unchanged.
  - `stage1`, `stage2`, or `both` (equal fraction of each stage's load).
  - Optional pre-applied `stage2_offload_t` and assumed `stage1_dry_mass_added_t`.
- F(x) = m_res at P_ref with gamma* optimised. x* is the largest evaluated x with F >= 0
  in final mode, the same feasible-side convention as P*.
- The recorded run must be inserted with 0 <= m_res < `final_payload_xtol_kg` (0.05 kg),
  checked by the existing `_check_recorded`.
- Monotonicity is argued, not assumed. For stage 1, each tonne is worth about 35 kg of
  payload at T/W 1.4 (probe). In general only a single sign change on the bracket is
  required; the logged evaluations are checked for it afterwards, and a violation raises
  the flag `offload_nonmonotone`.
- Pad control: the same solve on the pad in each mode. It must return x within xtol of 0
  for `stage1` (a consistency test). For `stage2` and `both` it is reported, and the
  silo's number is quoted net of it.
- "Both": equal fraction, plus one frontier point (max stage-1 offload at a fixed stage-2
  offload). Say plainly that total tonnes are maximised by stage-1-only offload, so "both"
  cannot beat the headline.

**c. Formulation.** A new `OffloadProblem` implements `RecordingProblem`:

- `evaluate(x, gamma, warm, mode)` flies the offloaded vehicle at P_ref and returns a
  `ResidualResult` whose abscissa field carries x.
- `optimise_gamma(find_payload=True)` then `final_verify` run unchanged: grid at x = 0,
  X1, refine, X2, final bracket, recorded run.
- An x beyond the stage load raises a typed infeasible, which the existing back-off
  handles. m_res(0) < 0 maps to status `no_offload`.
- Then an independent `sim.run_resolved` payload search at x* must reproduce P_ref within
  `checks.search_final_flag_rel` x P_ref (about 2.6 kg), else the flag
  `offload_verify_mismatch`.
- Requirement from the 3-D design: build `OffloadProblem` from a problem factory
  (vehicle -> `RecordingProblem`), not from `SearchContext` directly, so the spatial
  search context inherits it.

| Formulation | Evaluations | Time per case | Note |
|---|---|---|---|
| Recommended (adapter + verification) | about 55 + 38 | about 33 s | Recorded run exactly at P_ref |
| Root-find on max-gamma m_res | 5-7 gamma sweeps | about 70 s | |
| Nested payload search | 4-6 full searches | 55-80 s | No recorded run exactly at P_ref |

**d. Decomposition.** For any two runs at the same payload and orbit, the closure and the
loss identity give

    d(dv_margin) - d(D_id) = dV_0 - dV_f - dJ_grav - dJ_drag - dJ_steer - dJ_bp - d(pre) - d(fair),   d = variant - pad

- It reuses `compare.attribution_terms` (607: `loss_budget` plus `rocket_equation_closure`,
  each with its own vehicle) and `compare._contributions` (641).
- The only addition is exposing `closure.d_id_mps`. No loss accounting changes.
- The residual is the difference of the two runs' closure and identity residuals, judged
  by the `_attribution_check` thresholds.
- For a stage-1 offload, D_id(pad) - D_id(offloaded) = c1 ln(m0/(m0 - x)) exactly, so each
  term is also reported in tonnes as a proportional split.

**e. Merge rule.** Exclusive key families, declared once in `config.py`:

- Assist: {`net_accel_g`} or {`exit_speed_mps`}.
- Ignition: {`t_ign_s`, `reference`}, {`at_depth_m`}, {`at_speed_mps`}, or
  {`at_height_m`, `height_method`}.
- An override that sets a key of one parameterisation drops the base's keys of the others,
  in both `merge_run_dicts` and `_set_path`.
- A validator enforces "exactly one", using `model_fields_set` so the `t_ign_s = 0.0` and
  `reference = "release"` defaults that `test_run_defaults` pins stay.

**f. Ramp start.** Depth, speed and closed-form height convert to the existing
`(t_ign_s, reference)` pair at the boundary, so the planners change only for the altitude
event.

## 3. Steps

**Step 1. Guard and merge rule (config only).**

- Files: `src\config.py`, `tests\test_config.py`, `tests\test_config_planar.py`.
- First add a test pinning sha256 digests of every resolved run and vehicle dict of the
  four shipped planar experiments, captured before any change.
- Then add the exclusive families to `merge_run_dicts` (1519) and `_set_path` (1585).
- Tests: family drops; both-keys given in memory is a ValueError; sweep axis
  `assist.exit_speed_mps` over a `net_accel_g` parent.
- Gate: digests and the golden `test_phase1_resolved_run_dicts_are_byte_identical`
  unchanged.

**Step 2. Exit-speed option.**

- Files: `src\config.py` (`ConstantAccelConfig` 537-568), `src\assist\constant_accel.py`,
  `src\metrics_planar.py`, `src\replay.py`.
- `net_accel_g` and `exit_speed_mps` become optional, exactly one required;
  `net_accel_mps2` returns v^2/(2L) in the second case. The `net_accel_g` path stays
  `units.from_g`, bit-identical.
- An extra assumption line appears only on the exit-speed path.
- New planar-only metrics in `planar_track_metrics` (922): `net_accel_mps2`, `net_accel_g`,
  `stroke_m`. `replay.py:478,675` read the metric first and fall back to the config key.
- Tests: integrated exit speed equals the configured v, and push time equals 2L/v, to
  1e-9; the trajectory equals the `net_accel_g = v^2/(2 g0 L)` run.
- Gate: fast suite, golden.

**Step 3. Ramp start by depth, speed and closed-form height.**

- Files: `src\config.py` (624-636, 1172, 1764-1779), `src\phases\prelude.py`,
  `src\assist\constant_accel.py`, `src\sim.py` (803), `src\search.py` (549),
  `src\metrics_planar.py`, `src\summary.py`, `src\results_io.py`.
- `IgnitionConfig` gains `at_depth_m` (>= 0), `at_speed_mps` (>= 0), `at_height_m` (> 0)
  and `height_method: event | closed_form`.
- Config refusals: a pad run, any later stage, and `at_depth_m > stroke_m`. With
  `fails: true` the settings are flagged as ignored (extend
  `flag_ignored_ignition_settings`).
- One resolver, `prelude.resolve_ignition(cfg, startup, assist, track, g_eff)`, used by
  both build sites:
  - depth: `push_time_s(L - d)`, reference push_start (139);
  - speed: v/a, via a new `time_to_speed_s`;
  - closed-form height: dt = (v_e - sqrt(v_e^2 - 2 g_eff h))/g_eff, reference release;
  - a result within `ZERO_SPAN_S` of release snaps to (0, release);
  - ValueError for v > v_exit, for h >= v_e^2/(2 g_eff), or for a non-`constant_accel`
    model.
- A preflight `sim.check_resolved(resolved)` builds assist and ignition specs for every
  run before `make_run_dir`, so nothing is written on a bad config.
- Hot-start clamp: depth and speed always fall inside the push. Full thrust at push start
  still needs `t_ign_s < 0` with `reference: push_start`.
- `IgnitionSpec` carries `trigger_kind` and `trigger_value`.
- Planar metrics from the stage-1 `ignition` event record: `ramp_start_trigger`,
  `ramp_start_requested_{t_s,depth_m,speed_mps,height_m}`, and achieved
  `ramp_start_{t_rel_release_s,alt_m,depth_m,height_m,speed_mps,phase}`. Summary rows go
  after `ignition_rows`.
- Tests: 1-D and planar ignition-event depth and speed against closed forms (1e-9);
  closed-form height exact under an injected `ConstantGravity`; the handoff table rows
  (-94.6 m at 17.9 m/s; 50 m at 54.2 m/s).
- Gate: full suite, golden exact tier.

**Step 4. Altitude event (events change; update physics.md in the same change).**

- Files: `src\phases\engine.py`, `src\phases\planar.py`, `src\phases\vertical.py`,
  `src\phases\prelude.py`, `src\guidance.py`, `docs\physics.md`.
- `ev_altitude_up(model, z, "ignition_height")`, modelled on `ev_ground` (700),
  direction +1.
- `fly_track`: for this trigger the push uses a `fails=True` schedule (the validated unlit
  path) and writes no ignition time.
- `FlightStart` gains `ign1_alt_m` and a `stage1_lights` property; the three
  `t_ign1_s is None` checks use it.
- Planar `_coast` (1344) gains `extra` events, listed on rising sub-phases only.
  `_fly_to_kick` coasts to the event, sets `t_ign` there, and builds the schedule and kick
  deadline from it.
- Apex before h raises a new `GuidanceFailure("no_ignition")`. A searched run reports
  `search_failed`; a fixed-guidance run reports `guidance_failed`.
- 1-D `ascend` and `_coast` (561) mirror this; apex first is a ValueError.
- The search path is covered because `SearchContext._kick` calls `to_kick`.
- Tests: event altitude equals z_exit + h to the event tolerance (1-D, and planar with
  drag and rotation); event time equals the closed form in constant-g vacuum; the two
  methods agree there; `no_ignition` when h lies between the true and the drag-free apex;
  a default-argument run has identical event tuples.
- Gate: full suite with slow tests, golden exact tier.

**Step 5. Offload solver core (pure).**

- Files: new `src\offload.py`, `src\vehicle.py`, `src\search.py`, `tests\test_offload.py`.
- `vehicle.with_offload(vehicle, mode, x)` builds on `with_stage_propellant` (595).
- Extract the body of `SearchContext.evaluate` (609-650) into a helper taking the planner
  and kick-cache key. `joint_root_crosscheck` already duplicates it.
- `OffloadProblem` and `solve_offload` as in 2c. Flags are prefixed `offload:`; search
  failures become a status with their kind.
- Tests:
  - `SpeedTargetToy` (`tests\test_payload_search.py:103`) with a head start v0:
    x* = m0 - m1 exp((V* - v0 - c ln(m2/m3))/c) for stage 1; brentq forms for stage 2 and
    both.
  - In vacuum with no gravity, x* equals `vehicle.stage1_propellant_saved_kg` (650) when
    Isp_eff = Isp.
  - `no_offload` at v0 = 0; range back-off.
  - Slow, gate vehicle, small grid: recorded-run rule, verification within tolerance, pad
    control near 0, 10x-tightened budget moves x* by less than 0.1%.
- Gate: full suite; pad and silo_cold P* reproduce 26,054.4 and 27,553.2 kg within
  0.002 kg after the refactor.

**Step 6. Cross-vehicle decomposition.**

- Files: `src\compare.py`, `tests\test_closure.py`.
- `cross_vehicle_decomposition(variant, baseline)` per 2d, taking `MatchedRun`s. Solved
  cases use the two final evaluations; fixed cases use `sim.matched_run` (1480) at P_ref.
- `matched_attribution` and `ATTRIBUTION_KEYS` are untouched.
- Tests: toy with all losses zero gives ideal-dv change equal to the release-speed term;
  gate vehicle residual below `closure_tol_mps`.

**Step 7. `offload:` block, pipeline and reporting.**

- Files: `src\config.py`, `src\results_io.py`, `src\summary.py`, `src\units.py`,
  `src\compare.py`, `src\cli.py`, `src\replay.py`.
- Block shape:
  - `reference` (must be the baseline).
  - `cases: [{name, of, solve: stage1|stage2|both} or {fixed: {stage1_t | stage1_fraction
    | stage2_t | ...}}]`, each with optional `stage2_offload_t`,
    `stage1_dry_mass_added_t`, `paired_pad`.
  - `pad_control: true`, `sensitivity_of: [...]` (uses the experiment's
    `sensitivity.params`, perturbing pad and silo alike).
  - `energy`: sourced Quantities for per-stage `fuel_mass_t` and
    `heating_value_MJ_per_kg`. Validated to sum with the remainder to the vehicle's
    propellant, so the gate file stays unedited.
- `SweepConfig.offload: [case names]` solves those cases at each sweep point and adds
  columns to `sweep_index.csv`.
- `planar_offload(...)` is called inside `planar_experiment_result` (945), which is pure,
  so the SP2 app can call `resolve_experiment(dict, vehicle_dict)` then
  `sim.run_resolved` then `planar_experiment_result` without writing.
- `ExperimentResult.offload` rows; the `metrics.json` key `offload` and the summary
  section are written only when the block is declared, so existing planar outputs do not
  change.
- Summary block "Propellant saved at fixed payload", with a basis line
  (`OFFLOAD_COMPARISON_BASIS`: different vehicles, same payload and orbit):
  - tonnes; % of stage-1, stage-2 and total load;
  - RP-1 and LOX removed; heat (LHV), electricity, and ratio labelled "not an efficiency";
  - liftoff mass, MECO, max-Q against the pad, felt g, interface force, facility length;
  - ideal-screening offload at this release speed and the ratio; the decomposition table;
  - verification delta, pad control and net, paired-pad P*;
  - the caveat list (`OFFLOAD_CAVEATS`).
- Checks: a decomposition that passes is "explained"; one that fails is `bug_suspect` and
  blocks findings. Offload rows never enter the "Unexplained beats" list.
- Replay: `replay.run_source` sorts run folders into roles (run, bound, paired_baseline,
  case); add an offload role so the offloaded run can be replayed beside the pad (the SP1
  demo).
- Tests: schema refusals, energy arithmetic, summary and metrics on a small-grid run, an
  in-memory dict run.
- Gate: full suite, golden exact.

**Step 8. Experiment and pre-registration.**

- Files: `experiments\silo_offload_2d.yaml`, a one-case bridge on the README-loads vehicle
  (`generic_f9_class_2d_readme_loads.yaml`, following the `silo_bridge_2d_readme`
  precedent), `tests\test_config_planar.py` (`PLANAR_EXPERIMENTS`).
- Shared blocks are copied verbatim; the baseline is the pad.
- Variants: `silo_cold`; `silo_hot_ramp_on_track`; `silo_cold_200m` (200 m,
  `exit_speed_mps` 76.71).
- Cases on `silo_cold`: stage1 (headline, paired pad, sensitivity); stage2; both; stage1
  with a 2 t stage-2 offload; stage1 with +2, +4 and +8.1 t; fixed 5% and 10%; pad
  controls. On the hot ramp: stage1.
- Sweeps, each solving the stage-1 offload:
  - stroke [25, 50, 100, 200, 300] at 3 g;
  - stroke [50, 100, 200, 300] at exit speed 76.71 (same offload expected; lower g and
    power, longer facility);
  - `at_depth_m` [100, 75, 50, 25, 0];
  - `at_height_m` [10, 40, 100, 200] by event, plus two closed-form points.
- Serial runtime: `run` about 15 min, `sweep` about 17 min (20 points at about 48 s).
  `--jobs` is not needed; if either command exceeds 30 min, trim the fixed-exit-speed
  sweep.
- Commit before running; run from a clean tree.

**Step 9. Run, findings and close-out.**

- `docs\findings\RQ1-fuel-offload-2d.md` (README question 1, "Net benefit", has no note
  yet). Outline:
  1. definition;
  2. headline with caveats inline;
  3. why about 3x the screening estimate (decomposition; yardstick on both the gate
     vehicle and README masses);
  4. penalty rows and break-even;
  5. stage 2 and both, with the pad control;
  6. depth;
  7. ramp start;
  8. energy;
  9. sensitivity;
  10. limits;
  11. reproduction.
- `docs\physics.md` additions:
  - "Silo model": exit-speed form.
  - "Phases and events" and "Event rules": the four triggers, `ignition_height`,
    `no_ignition`.
  - "Figures of merit (planar)": "Propellant offload at fixed payload".
  - "Screening-beat rule": "Cross-vehicle decomposition".
  - "Reporting definitions": energy comparison.
  - "Experiment schema": offload block, exclusive families.
  - "Assumptions": partly filled tanks, mixture ratio kept, no ullage or CG effects.
  - Test-to-equation map.
- `CLAUDE.md`: layout line for `offload.py`, status line. `README.md`: results and RQ1
  status. Trackers updated.
- Gate: honesty review.

## 4. Risks and recommended resolutions

1. **Stage-2 marginal value near zero.** Keep stage 1 as the only headline. Report stage 2
   and both net of the pad control and labelled as a property of the vehicle model.
2. **gamma\* optimum moves with the offload.** `refine_capped` is flagged; the independent
   payload search catches a suboptimal gamma*, and x* is then a flagged lower bound.
3. **Final bracket in x.** The shared 20 kg start spans only about 0.7 kg of m_res, so
   `search_final_mismatch` may flag harmlessly. If it does, add bracket-only settings to
   the `offload` block rather than touching `search`.
4. **Max-Q of the offloaded run exceeds the pad's** (38.4 against 37.2 kPa in the probe).
   Report it beside the number; do not solve a constrained variant, since there is no
   throttle model.
5. **Heating value.** Needs a citable LHV source; if none is at hand, mark it
   `assumed: true`. The ratio excludes LOX production and generation losses.
6. **Calibration miss (+14.3%).** One headline case on the README-loads fork as a
   robustness row (approved in the plan as part of step 8).
7. **Existing cross-vehicle sensitivity rows** still print as "Unexplained beats" (a known
   issue). Passing them the new decomposition would fix that but changes existing
   summaries on re-run, so defer it.

## 5. Effect on validated numbers and pre-registered inputs

- No shipped experiment or vehicle file changes; `budget_id` is unchanged.
- Validated code touched with neutral defaults: `merge_run_dicts` and `_set_path`, both
  `_coast` functions, `fly_track`, `FlightStart`, `SearchContext.evaluate` (refactor),
  `GUIDANCE_FAILURE_KINDS` (+1), `attribution_terms` (+1 internal key).
- Each is gated by the exact golden tier, the new planar digest pin, and the two
  reproduced P* values.
- The only edit to an existing test is appending the new experiment to
  `PLANAR_EXPERIMENTS`.

## Critical files

- src\launchsim\config.py
- src\launchsim\search.py
- src\launchsim\phases\planar.py
- src\launchsim\compare.py
- src\launchsim\results_io.py
