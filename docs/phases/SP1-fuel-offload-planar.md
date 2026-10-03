# SP1: Launch settings and fuel offload at fixed payload (planar model)

Status: in progress (session 2026-09-30)

This is the starting document and the live record of phase SP1. The program board is
docs/phases/README.md, the way every session runs is docs/process/SESSION_PROTOCOL.md, and
the plan the user approved on 2026-09-30 is
docs/phases/inputs/2026-09-30-SP1-approved-plan.md (the source of truth for scope, steps
and exit criteria). Status marks: [ ] not started, [~] in progress, [x] done, [!] blocked
or needs a decision.

## 1. Goal and what you can see at the end

**Goal.** Answer the headline question on the planar (2-D) model: with the payload and the
200 km orbit held fixed on the Falcon 9-class gate vehicle, how much rocket propellant
does a vertical maglev silo push replace, as tonnes, % of stage-1 propellant and % of total
propellant, with the energy comparison and the structural-mass caveat beside the number.
On the way, make the silo depth and the thrust-ramp start configurable, and build the work
tracking that lets each later phase run in its own fresh session.

**What you can see at the end.**

- docs/findings/RQ1-fuel-offload-2d.md: the % of propellant replaced, with penalty rows,
  sensitivity and every caveat next to the headline.
- `uv run python -m launchsim run experiments/silo_offload_2d.yaml` reproducing it, with a
  "Propellant saved at fixed payload" block in summary.md.
- A replay page showing the full-load pad and the offloaded silo run reaching the same
  orbit with the same payload.
- New YAML settings: `assist.exit_speed_mps` (depth and exit speed set independently), and
  the ramp start by `at_depth_m`, `at_speed_mps` or `at_height_m` besides the existing
  `t_ign_s`.
- The tracking system: docs/process/SESSION_PROTOCOL.md, docs/phases/README.md, phase files
  SP1 to SP6, TODO.md with IDs, and a handoff plus prompt for SP2.
- The recorded demo under docs/demos/SP1/.

**What is known before the phase starts.** Only the handoff probe
(docs/findings/probes/handoff-2026-09-30/probe_offload.py, read off by hand from four
points): the 3 g / 100 m cold-start silo carried the full-load pad's payload with 10% less
stage-1 propellant (41.1 t, 7.9% of the total load). That is a probe, not a result. SP1
replaces it with a solved, verified and caveated number, whatever that number turns out
to be.

## 2. Scope and out of scope

**In scope (steps T and 1 to 10 of section 7).**

- Tracking system (step T).
- Launch settings: exit-speed option for the silo; ramp start by depth, by speed, by
  closed-form height and by an altitude event; the merge rule that makes these safe in
  variants and sweeps.
- Fixed-payload offload solver for stage 1, stage 2 and both, with a pad control, built so
  the 3-D models can reuse it.
- Cross-vehicle decomposition that explains the offload from the existing loss budget.
- The `offload:` experiment block, pipeline, summary block, `metrics.json` key, replay
  support, and an entry point callable with an in-memory experiment dict.
- experiments/silo_offload_2d.yaml and a one-case bridge on the README-loads vehicle, both
  pre-registered (committed before any run).
- Runs, sweeps and the findings note; SP1 close-out and the SP2 handoff.

**Out of scope.**

- The local app and the 2-D launch scene (SP2); any 3-D dynamics or 3-D scene (SP3 to
  SP6). SP1 only writes their phase files.
- A structural-mass model for the 4 g push, force- or power-limited drives, carriage mass,
  shaft air drag, tilted tracks (README Phase 3). SP1 shows the structural penalty only as
  parametric rows with assumed added dry mass.
- Throttling or a max-Q-constrained offload (there is no throttle model).
- Tank dry mass that shrinks with the offload, ullage, centre-of-gravity or mixture-ratio
  effects. Tanks are partly filled and the dry mass is unchanged.
- Any edit to a shipped experiment or vehicle file, any new `search` field, any change to
  `budget_id`, and any new 1-D metric, summary row or assumption text.
- Depth, speed and closed-form-height triggers for drives other than `constant_accel`
  (refused with a ValueError until Phase 3 has a force-limited model).
- Routing the existing cross-vehicle sensitivity rows through the new decomposition (it
  would change existing summaries on re-run; deferred, TODO.md KI-008 and KI-011).
- A parallel `--jobs` option.

## 3. Decisions already taken

All dated 2026-09-30. The full text is in TODO.md's decisions log; this table only says
what each one fixes for SP1.

| ID | Fixes for SP1 |
|---|---|
| D-SP1-01 | 3-D means true 3-D dynamics in three stages (S1, S2, S3). SP1 does none of it, but the offload solver must be reusable by those models (section 5.4). |
| D-SP1-02 | The visual tool is a local app. SP1 only makes the experiment entry point callable with an in-memory dict (step 7) so SP2 can use it. |
| D-SP1-03 | Offload modes: stage 1 (headline), stage 2, both. Tanks partly filled, dry mass unchanged. Fixed payload = the full-load pad's payload capacity on the same vehicle and 200 km orbit. |
| D-SP1-04 | Structural penalty as parametric rows: stage-1 offload re-solved with +2, +4 and +8.1 t of assumed stage-1 dry mass. |
| D-SP1-05 | Silo depth: `stroke_m` with exactly one of `net_accel_g` or `exit_speed_mps`. |
| D-SP1-06 | Ramp start by time (exists), by depth or speed on the push, by height above the mouth through an event, and by height through a closed form. |
| D-SP1-07 | Order: settings and solver, then the headline finding on the planar model, then the app, then 3-D. |
| D-SP1-08 | One fresh session per phase; this file, the handoff and the prompt are how the next session starts. |
| D-SP1-09 | The offload is a separate `offload:` block and a post-pass, not a new `search.figure_of_merit` value. No pre-registered file or budget id changes. |
| D-SP1-10 | Every offload mode is also solved on the pad. Stage-2 and both-stage numbers are reported net of the pad control. Stage 1 is the only headline. |
| D-SP1-11 | Target under J2 (SP5). Not used in SP1; listed so the phase files agree. |
| D-SP1-12 | The 6-DOF model is a fly-out (SP6). Not used in SP1. |
| D-SP1-13 | A one-case bridge of the offload on the README-loads vehicle (inside the calibration band) is part of step 8. |

Earlier decisions that still bind SP1 (IDs assigned in TODO.md's decisions log): the
calibration miss of +14.3% is accepted and travels with every finding; mechanism check M2
is diagnostic only; the planar 2 s step cap; runs share the guidance parametrisation,
sweep grid and optimizer budget, and results are called "sweep-optimized".

D-SP1-01 and D-SP1-02 go beyond the handoff's recommendation. CLAUDE.md's "ask before
expanding scope (6-DOF, 3-D Earth)" is satisfied by the user's answers.

## 4. Entry criteria

| # | Criterion | State on 2026-09-30 |
|---|---|---|
| 1 | Phases 0 to 2 closed (README roadmap, CLAUDE.md status line) | met |
| 2 | Clean working tree at the handoff commit 2eebcae | met (confirmed at session start) |
| 3 | Fast suite green (`uv run pytest -q -m "not slow"`), ruff clean | met (confirmed at session start; the handoff counts 928 fast and 23 slow tests) |
| 4 | The plan approved by the user | met (docs/phases/inputs/2026-09-30-SP1-approved-plan.md) |
| 5 | Design and survey inputs present in docs/phases/inputs/ | met (section 5 lists them) |
| 6 | The four shipped planar experiments and the gate vehicle file present and unedited | met (they are what step 1 pins) |
| 7 | The previous handoff archived | met (docs/handoff/archive/2026-09-30-phases-0-2.md) |

## 5. Design

Summary of the design as approved. The full version, with the claim check against the
code, is docs/phases/inputs/2026-09-30-design-settings-and-offload.md. The code facts
behind it are in docs/phases/inputs/2026-09-30-survey-config-search-compare.md and
docs/phases/inputs/2026-09-30-survey-ignition-assist-physics.md.

### 5.1 An `offload:` block, not a new figure of merit (D-SP1-09)

`search.figure_of_merit` sits in the shared, pre-registered `search` block. Tests require
every `SearchConfig` field except the three `fixed_*` fields (`fixed_gamma_star_deg`,
`fixed_ltg_a`, `fixed_ltg_b_per_s`) to be written in calibration_f9_2d.yaml
(`test_shipped_blocks_state_every_threshold`), and the shared blocks to be identical
across the four shipped planar experiments
(`test_shared_blocks_are_identical_across_the_planar_experiments`); every field is part
of `budget_id()`. A new value or field would force edits to four pre-registered files.
The offload also needs the pad's
payload capacity before it can start, and `run_planar` is per run. So the offload is a
separate top-level `offload:` block and a post-pass inside
`results_io.planar_experiment_result`, like `planar_comparisons` and `planar_bounds`.
Vehicle keys stay out of variants: `planar_comparisons` would run `matched_attribution` on
a different-vehicle variant and report a false `bug_suspect`.

### 5.2 Offload definition (D-SP1-03)

- The offload x >= 0 [kg] is propellant removed along a mode: `stage1`, `stage2`, or `both`
  (the same fraction of each stage's load). Dry mass is unchanged (tanks partly filled),
  so liftoff mass falls one for one. Optional additions per case: a pre-applied
  `stage2_offload_t` and an assumed `stage1_dry_mass_added_t`.
- P_ref is the full-load pad's payload capacity on the same vehicle and orbit.
- F(x) = residual propellant m_res at insertion, flying P_ref, with gamma* optimised.
- The reported x* is the largest evaluated offload with F >= 0 at final tolerance. This is
  the same feasible-side convention as the payload capacity P*.
- The recorded run flies exactly P_ref and must end inserted with 0 <= m_res < 0.05 kg
  (`final_payload_xtol_kg`), checked by the existing `search._check_recorded`.
- Monotonicity is argued, not assumed. Only a single sign change on the bracket is
  required; the logged evaluations are checked for it afterwards and a violation raises
  the flag `offload_nonmonotone`.
- F(0) < 0 (the run cannot carry P_ref even with a full load) gives status `no_offload`.
- A plain "reduce propellant by X" knob is the `fixed:` case form: the offload is given,
  nothing is solved, and the run is compared with the unchanged pad (and, with
  `paired_pad`, with an equally offloaded pad). It builds on the bounds machinery, which
  already re-runs a variant with `vehicle.` overrides against both.

### 5.3 Pad control, and why (D-SP1-10)

docs/physics.md, "Virtual propellant" (line 1948; the measurement is at 1961-1966), records
that on the gate pad, about 0.95 t above its payload root, m_res was -975.0 kg with the
real load and -990.3 kg with 975 kg more real stage-2 propellant. Stage-2 propellant is
worth about nothing, or slightly less than nothing, at the margin on this vehicle and
guidance. The measurement has two limits. It was taken at a fixed gamma* of 22 deg (search
mode, rtol 1e-9), not with gamma* re-optimised. And it covers added propellant only (also
-1,098.5 kg at +4.9 t and -5,643.8 kg at +37.5 t). The offload direction and a
re-optimised gamma* are not measured, which is why the pad control is solved and not
assumed. Three consequences:

- The pad itself may be able to fly P_ref with less stage-2 propellant. A stage-2 offload
  on the silo run would then be a property of the vehicle model, not of the silo.
- m_res is not guaranteed monotone in a stage-2 offload, and the stage-2 and both-stage
  numbers may be large and ill-conditioned.
- They are only honest with the same solve on the pad reported beside them.

So every mode is also solved on the pad. For `stage1` the pad control must return
0 <= x_pad <= `final_payload_xtol_kg` / s, where s = |dm_res/dx| is taken from the pad
control's own logged evaluations; that is a consistency test of the solver. The reason for
this bound: the pad's reference run at P_ref ends with 0 <= m_res < `final_payload_xtol_kg`
(0.05 kg) by the recorded-run rule, so that is the most residual a stage-1 offload can
remove. With the estimate of risk 3 (about 0.7 kg of m_res per 20 kg of offload) the bound
is about 1.4 kg. The design input says only "within xtol of 0"; this is this file's
reading of it, and the bound in kg is written into the step 5 row before the gate is
judged. For `stage2` and `both` the pad
control is reported and the silo's number is quoted net of it, labelled as a property of
the vehicle model. Stage 1 is the only headline. "Both" is the equal-fraction solve plus
one frontier point (the largest stage-1 offload at a fixed stage-2 offload). The note must
say plainly that total tonnes are maximised by a stage-1-only offload, so "both" cannot
beat the headline.

### 5.4 Solver formulation and the problem factory

- `OffloadProblem` implements the existing `RecordingProblem` protocol. Its
  `evaluate(x, gamma, warm, mode)` flies the offloaded vehicle at P_ref and returns a
  `ResidualResult` whose abscissa field (`payload_kg`, which `payload_root` reads) carries
  x. `optimise_gamma(find_payload=True)` and `final_verify` then run unchanged: grid at
  x = 0, X1, refine, X2, final bracket, recorded run.
- An x beyond the stage's load raises a typed infeasible, which the existing bracket
  back-off handles.
- After the solve, an independent full payload search (`sim.run_resolved`) on the vehicle
  offloaded by x* must reproduce P_ref within `checks.search_final_flag_rel` x P_ref (about
  2.6 kg on the gate vehicle). Otherwise the case carries the flag
  `offload_verify_mismatch`.
- **Requirement from the 3-D design (approved plan, step 5).** `OffloadProblem` is built
  from a problem factory, a callable vehicle -> `RecordingProblem`, and never from
  `SearchContext` directly. The
  planar factory wraps `SearchContext`; the spatial search context of SP3 supplies its own
  factory and inherits the solver without change (D-SP1-01).
- Cost (estimates from the design input): about 55 solver evaluations plus about 38 for
  the verification search, about 33 s per solved case. The two alternatives (root-finding
  on the gamma-maximised m_res, about 70 s; nested payload searches, 55 to 80 s and no
  recorded run exactly at P_ref) were rejected.

### 5.5 Cross-vehicle decomposition

The matched-payload attribution assumes the same ideal delta-v on both sides, so it cannot
compare an offloaded run with the unchanged pad. For any two runs at the same payload and
orbit, each on its own vehicle, the rocket-equation closure and the loss identity give

    d(dv_margin) - d(D_id) = dV_0 - dV_f - dJ_grav - dJ_drag - dJ_steer - dJ_bp - d(pre) - d(fair)

with d = variant - pad, D_id the ideal delta-v at the payload (`ideal_dv_at_payload_mps`,
already a per-run metric), V_0 and V_f the Earth-relative speeds at release and at cutoff,
J the loss integrals (gravity, drag, steering, back-pressure), "pre" the pre-release term
and "fair" the fairing term of the closure. Read the other way: the reduction in ideal
delta-v equals the release-speed term plus the differences in the loss, pre-release and
fairing terms.

- It reuses `compare.attribution_terms` (the loss budget plus `rocket_equation_closure`,
  each run with its own vehicle) and `compare._contributions`. The only addition is
  exposing `closure.d_id_mps`. No loss accounting changes.
- The residual is the difference of the two runs' closure and identity residuals. It is
  judged by the `_attribution_check` thresholds and must be below `closure_tol_mps`
  (1e-5 m/s in the shared checks block).
- For a stage-1 offload, D_id(pad) - D_id(offloaded) = c1 ln(m0 / (m0 - x)) exactly, so
  each term is also reported in tonnes as a proportional split.

### 5.6 Structural penalty rows (D-SP1-04)

The stage-1 offload is re-solved with +2, +4 and +8.1 t of assumed stage-1 dry mass on the
assisted run only (the pad keeps its dry mass). 8.1 t is the break-even of the payload
gain derived in the 2-D findings (docs/findings/RQ3-silo-screening-2d.md). These rows are
assumptions, not a structural model.

### 5.7 Energy comparison

Reported per case: RP-1 and LOX removed; the combustion heat of the removed RP-1 (lower
heating value); the push's electricity; and their ratio, labelled "not an efficiency
claim". The LOX/RP-1 split and the heating value are sourced `Quantity` entries in the
experiment's `offload.energy` block, because the gate vehicle file is never edited. The
split exists today only inside source strings of configs/vehicles/generic_f9_class_2d.yaml
(line 47: 287.4 t LOX + 123.5 t RP-1; line 59: 75.2 t LOX + 32.3 t RP-1). The block is
validated to sum, with the remainder, to the vehicle's propellant. LOX production and
generation losses are excluded and the summary says so.

### 5.8 Screening rule

CLAUDE.md: a run that beats the ideal screening estimate must be explained by the loss
breakdown, or it is treated as a bug. The yardstick is
`vehicle.stage1_propellant_saved_kg` at the run's release speed (README: 14 t at 77 m/s on
README masses). Going by the handoff probe, the solved offload is expected to be about
three times that. This is an expectation, not a target. The decomposition of 5.5 must
explain the difference; a decomposition that passes marks the row "explained", one that
fails marks it `bug_suspect` and blocks the finding. Offload rows never enter the
"Unexplained beats" list.

### 5.9 Merge rule: exclusive key families

Every variant inherits the baseline's keys through `merge_run_dicts`, which merges dicts
by key. Only `model` and `kind` replace a dict wholesale. The shipped baselines carry
`ignition: {stage1: {t_ign_s: -2.0, reference: release}}` and the `*silo` anchor carries
`net_accel_g`, so a variant or a sweep axis that sets `at_depth_m` or `exit_speed_mps`
would end up with two parameterisations at once. Explicit nulls or a discriminator do not
fix sweep axes. The rule, declared once in `config.py`:

- Assist families: {`net_accel_g`} or {`exit_speed_mps`}.
- Ignition families: {`t_ign_s`, `reference`}, {`at_depth_m`}, {`at_speed_mps`}, or
  {`at_height_m`, `height_method`}.
- An override that sets a key of one family drops the base's keys of the other families,
  in both `merge_run_dicts` and `_set_path`.
- A validator enforces "exactly one", using `model_fields_set`, so the defaults
  `t_ign_s = 0.0` and `reference = "release"` that `test_run_defaults` pins stay.

### 5.10 Exit-speed option (D-SP1-05)

`ConstantAccelConfig` takes exactly one of `net_accel_g` and `exit_speed_mps`. With the
exit speed v and stroke L:

    a = v^2 / (2 L),    t_push = 2 L / v

The `net_accel_g` path stays `units.from_g(net_accel_g)`, bit-identical. The derived
acceleration adds one assumption line on the exit-speed path only. `from_config` in
assist/constant_accel.py is the only place the acceleration enters the model, so nothing
downstream changes.

### 5.11 Ramp-start conversions (D-SP1-06)

Depth, speed and closed-form height convert to the existing `(t_ign_s, reference)` pair
before the run. The conversion is exact for the constant-acceleration drive. Only the
altitude event changes the planners. With stroke L, net acceleration a, exit speed
v_e = sqrt(2 a L), push time t_push = sqrt(2 L / a) and the track's g_eff:

| Setting | Converts to | Closed form | Refused when |
|---|---|---|---|
| `at_depth_m: d` (below the mouth) | time from push start | t = sqrt(2 (L - d) / a) | d > L |
| `at_speed_mps: v` (on the push) | time from push start | t = v / a | v > v_e |
| `at_height_m: h`, `height_method: closed_form` | time after release | dt = (v_e - sqrt(v_e^2 - 2 g_eff h)) / g_eff | h >= v_e^2 / (2 g_eff), the drag-free apex |
| `at_height_m: h`, `height_method: event` | not converted: an altitude event at mouth + h | none (root found in flight) | apex reached below h: typed failure `no_ignition` |

- A result within `ZERO_SPAN_S` of release snaps to (0, release).
- All three conversions are refused for a pad run, for any later stage, and for an assist
  model other than `constant_accel`.
- The closed-form height is exact only for a drag-free, constant-gravity coast. Under drag,
  mu/r^2 and rotation it is off by centimetres to decimetres, growing with h (survey
  estimate). The event form is exact to the event tolerance. Both are offered; requested
  and achieved values are both reported from the ignition event record.
- Check values from the handoff table (3 g, 100 m, t_push 2.607 s): `t_ign_s: -2.0` from
  release starts the ramp at -94.6 m and 17.9 m/s; d = 50 m is 1.844 s from push start,
  -0.764 s from release, at 54.2 m/s.
- Full thrust exactly at push start still needs `t_ign_s < 0` with `reference: push_start`;
  depth and speed always fall inside the push.

### 5.12 Nothing validated moves

No shipped experiment or vehicle file changes and `budget_id` is unchanged. Validated code
that is touched keeps neutral defaults: `merge_run_dicts` and `_set_path`, both `_coast`
functions, `fly_track`, `FlightStart`, `SearchContext.evaluate` (a refactor),
`GUIDANCE_FAILURE_KINDS` (one more kind), `attribution_terms` (one more internal key).
Guards: the golden 1-D tier, the planar digest pin of step 1, and the two reproduced
payload capacities. The only edit to an existing test is appending the new experiments to
`PLANAR_EXPERIMENTS`.

The two payload capacities are reproduced within 0.002 kg of their recorded values, not of
the one-decimal figures quoted elsewhere (26,054.4 and 27,553.2 kg), which are 0.004 and
0.027 kg away:

| Run | Recorded P* | Source |
|---|---|---|
| pad | 26,054.3962 kg (26054.396243494975) | tests/data/calibration_record.json, `amended_rerun` block (tracked); the same value is in the metrics.json below |
| silo_cold | 27,553.2271 kg (27553.227114190096) | metrics.json of results/silo_screening_2d/20260930T175743Z, git 7ad381f. Not tracked in git; the tracked summary.md prints one decimal. Step 1 copies the value into a tracked test data file |

## 6. Inventory of the code this phase touches

Line numbers were checked on 2026-09-30 at commit 2eebcae. The `def`, `class` and constant
lines below were re-checked by grep while this file was written; line ranges inside
functions come from the two surveys (same commit). The surveys sometimes cite the
decorator line, one above the `def` or `class` line given here. Numbers drift as SP1 edits
the files: re-check before relying on one. `src/` means `src/launchsim/`. The surveys hold
the rest of the inventory (tests that pin behaviour, time-series columns, physics.md
headings).

**Config and merge (steps 1, 2, 3, 7, 8): src/config.py**

| Item | Line | Note |
|---|---|---|
| `SWITCH_KEYS = ("model", "kind")` | 70 | the only keys that replace a dict wholesale on merge |
| `PLANAR_SHARED_KEYS` | 86 | guidance, search, target_orbit, checks |
| `TrackConfig` | 508 | `angle_deg` must be 90 |
| `ConstantAccelConfig` | 537 (fields to 568) | `net_accel_g` required today; no model validator; `net_accel_mps2` property at 556 |
| `IgnitionConfig` | 624 (to 636) | `t_ign_s = 0.0`, `reference = "release"`, `startup`, `fails`; extra keys forbidden |
| `SearchConfig`, `budget_id` | 820, 981 | every field is in the budget id; do not add fields |
| `ChecksConfig` | 1013 | `closure_tol_mps`, `search_final_flag_rel` |
| `RunConfig._ignition_rules` | 1173 | `fails` needs `end: impact`; push_start needs an assist |
| `RunConfig.ignition_for` | 1184 | falls back to `IgnitionConfig()` |
| `SweepConfig`, `SensitivityConfig`, `BoundConfig` | 1189, 1210, 1224 | `SweepConfig` gains `offload: [case names]` in step 7 |
| `ExperimentConfig` | 1325 | gains the `offload` block in step 7; `_labelled_features` at 1430 |
| `merge_run_dicts` | 1519 | step 1 adds the exclusive families |
| `_set_path` | 1585 | step 1 adds the exclusive families (sweep axes, overrides) |
| `apply_overrides` | 1606 | a number aimed at a Quantity becomes `{value, assumed: true, note: override}` |
| `resolve_run` | 1747 | later-stage ignition checks at 1764-1779 |
| `_perturb`, `_resolve_bound` | 1789, 1812 | the bounds machinery the offload cases build on |
| `resolve_experiment` | 1858 | pure; takes dicts, so the SP2 app can call it |

**Assist and ignition (steps 2, 3, 4)**

| Item | File:line | Note |
|---|---|---|
| `ConstantAccelAssist` | src/assist/constant_accel.py:28 | `from_config` 65 is the only place the acceleration enters |
| `exit_speed_mps`, `push_time_s` | :135, :139 | sqrt(2 a L), sqrt(2 L / a); `push_time_s(L - d)` is the depth conversion |
| `push_time_estimate`, `facility_length_m` | :143, :151 | exact for a prescribed acceleration |
| `assumptions` | :174 | the net-acceleration text is pinned by the golden 1-D tier; do not change it |
| `IgnitionSpec` | src/phases/prelude.py:76 | `from_config` 98, `t_ign_abs_s` 104; gains `trigger_kind`, `trigger_value` |
| `flag_ignored_ignition_settings` | src/phases/prelude.py:115 | extend for the new settings under `fails: true` |
| `fly_track` | src/phases/prelude.py:483 | resolves the ignition time at 524-531 before integrating; clamp at the shaft bottom 534-551 |
| `sim.ignition_specs` | src/sim.py:803 | spec build site 1 (806-809) |
| `SearchContext.from_run` | src/search.py:534 | spec build site 2 (549-552) |
| `ZERO_SPAN_S`, `ATOL_M` | src/phases/engine.py:51, :68 | snap tolerance; altitude event tolerance |
| `g_eff_track` | src/dynamics.py:114 | the track's constant g_eff |

**Events and planners (step 4)**

| Item | File:line | Note |
|---|---|---|
| `EventSpec` | src/phases/engine.py:166 | name, fn, terminal, direction, zero_tol |
| `ev_ground` | src/phases/engine.py:700 | the model for `ev_altitude_up` (direction +1) |
| `ev_apex`, `ev_impact`, `ev_radial_apex`, `ev_time` | :594, :622, :725, :797 | existing factories |
| `FlightStart` | src/phases/planar.py:549 | `t_ign1_s` (564): None means failed ignition today |
| `PlanarPlanner.start_track` | src/phases/planar.py:885 | release map, release event, `_begin_flight` (916) |
| `PlanarPlanner.to_kick`, `run` | :927, :1005 | the `t_ign1_s is None` checks at 946 and 1039 |
| `PlanarPlanner._coast` | :1344 | takes only `t_end`; no hook for extra events today |
| `PlanarPlanner._burn`, `_fly_to_kick` | :1394, :1446 | the pre-ignition coast and the ignition event are in `_fly_to_kick` |
| `SearchContext._kick` | src/search.py:599 | third `t_ign1_s is None` check (605-606) |
| `sim._solve_fixed_delta` | src/sim.py:1326 | fourth `FlightStart` consumer (1345-1348) |
| `VerticalPlanner.ascend`, `_coast` | src/phases/vertical.py:336, :561 | 1-D mirror; `ascend` writes `t_ign_abs_s` before the coast |
| `GUIDANCE_FAILURE_KINDS`, `GuidanceFailure` | src/guidance.py:43, :93 | add `no_ignition` |

**Search and vehicle (step 5)**

| Item | File:line | Note |
|---|---|---|
| `SearchBudget`, `tightened` | src/search.py:187, :295 | the 10x-tighter convergence check uses `tightened` |
| `WarmStore` | :352 | one fresh store per problem (`claim` refuses reuse) |
| `SearchProblem`, `RecordingProblem` | :460, :489 | the protocols `OffloadProblem` implements |
| `SearchContext` | :502 | `planner` 585 uses `with_payload` |
| `SearchContext.evaluate` | :609 (to 650) | body to extract into a helper taking the planner and the kick-cache key |
| `SearchContext.record` | :652 | recorded run with dense output and the real depletion event |
| `payload_root` | :805 | reads the abscissa from `res.payload_kg` |
| `optimise_gamma` | :1335 | reused unchanged |
| `_check_recorded`, `final_verify` | :1492, :1568 | reused unchanged |
| `run_search` | :1722 | dispatches on the figure of merit at 1733; not changed |
| `joint_root_crosscheck` | :1822 | already duplicates the `evaluate` body |
| `with_payload`, `with_stage_propellant` | src/vehicle.py:580, :595 | `with_offload` builds on the second; there is no dry-mass helper yet |
| `stage1_propellant_saved_kg` | src/vehicle.py:650 | the ideal-screening offload yardstick |
| `SpeedTargetToy` | tests/test_payload_search.py:102 | the toy for the closed-form tests |

**Comparison, pipeline and reporting (steps 6, 7)**

| Item | File:line | Note |
|---|---|---|
| `ATTRIBUTION_TERMS`, `attribution_terms` | src/compare.py:554, :607 | loss budget plus closure, per run and vehicle |
| `_contributions`, `matched_attribution` | :641, :657 | the second is not touched |
| `ATTRIBUTION_KEYS` | :754 | not touched |
| `_attribution_check`, `compare_planar` | :1080, :1124 | thresholds reused for the decomposition residual |
| `reference_payload_kg` | :1244 | P_ref from the baseline result |
| `_run_planar_sensitivity`, `attributed_comparison` | :1320, :1406 | patterns for same-perturbation pairs |
| `sim.run_resolved`, `sim.matched_run` | src/sim.py:841, :1480 | the independent payload search; a variant re-evaluated at P_ref |
| `sim.run_planar`, `_run_checks` | src/sim.py:1393, :1081 | closure, identity and insertion checks give `bug_suspect` |
| `make_run_dir` | src/results_io.py:284 | the preflight of step 3 runs before it |
| `_resolved_config_dict`, `_metrics_dict` | :509, :573 | where the `offload` records are written |
| `run_experiment` | :703 | baseline, variants, then the post-passes |
| `planar_comparisons`, `planar_bounds` | :864, :903 | models for the offload post-pass |
| `planar_experiment_result` | :945 | pure; `planar_offload(...)` is called here |
| `run_sweep`, `_run_sweeps_into` | :1068, :1103 | per-point offload solves and `sweep_index.csv` columns |
| `PLANAR_REQUIRED_METRICS` | src/metrics_planar.py:270 | keep new keys out of it |
| `planar_track_metrics` | src/metrics_planar.py:922 | new planar-only metrics go here |
| `ignition_rows` | src/summary.py:238 | ramp-start rows go after these |
| `PLANAR_VARIANT_ROWS`, `PLANAR_FAILED_ROWS` | :759, :862 | the gating pattern for optional rows |
| `screening_line`, `planar_checks_section` | :1075, :1144 | the screening text; `UNEXPLAINED_BEAT_TEXT` 1175 |
| `bounds_section`, `planar_experiment_summary` | :1316, :1392 | model and home of the new summary section |
| `run_source` | src/replay.py:241 | sorts run folders into roles; add an offload role |
| raw `net_accel_g` reads | src/replay.py:478, :675 | in `assist_text` (460) and `drive_caveat` (663); read the metric first |

**Pre-registration and tests (steps 1, 8)**

| Item | File:line | Note |
|---|---|---|
| `PLANAR_EXPERIMENTS` | tests/test_config_planar.py:52 | append the two new experiments |
| `test_shared_blocks_are_identical_across_the_planar_experiments` | :155 | the shared blocks and the budget id are the same in the four shipped files |
| `test_shipped_blocks_state_every_threshold` | :184 | every shared field (for `search`, all but the three `fixed_*` fields) written in calibration_f9_2d.yaml; :155 ties the other files to it |
| `test_phase1_resolved_run_dicts_are_byte_identical` | :257 | the golden resolved-dict test |
| `test_every_shipped_planar_experiment_is_checked` | :805 | fails if a planar YAML is not listed |
| `test_constant_accel_units`, `test_run_defaults` | tests/test_config.py:295, :322 | defaults that must stay |
| shared blocks to copy verbatim | experiments/silo_screening_2d.yaml:16-65 | site, target_orbit, guidance, search, checks |
| pad baseline; `*silo` anchor | :66-71; :74-77 | 3 g, 100 m, carriage 0 t, brake 5 g, efficiency 0.5 |
| `silo_cold`, `silo_hot_ramp_on_track` | :79, :81 | variants to copy |
| `sensitivity` block | :96-100 | the +/-10% parameters |
| bridge precedent | experiments/silo_bridge_2d_readme.yaml | README-loads vehicle, same shared blocks |

**docs/physics.md sections to update** (headings at 2eebcae): Stage-1 guidance and events
(planar) 947; Figures of merit (planar) 1877; Virtual propellant 1948; Screening-beat rule
(2-D) 2687; Reporting definitions (planar) 2951; Event rules 3258; Phases and events 3436;
Silo model 3786; Hot start 3914; Experiment schema (planar) 4374; Assumptions 4533;
Test-to-equation map 4796.

## 7. Steps

Each step runs as: implementer, adversarial reviewers (a physics or numerics skeptic and a
CLAUDE.md compliance auditor; an honesty auditor for findings), up to two fix rounds, an
independent gate, commit, tracker update (its own small commit, made at once, so the tree
is clean before the next step; SESSION_PROTOCOL.md section 4). **Standing gate on every
code step:** fast suite
green, ruff clean, golden 1-D byte-identical. **Full suite** (`uv run pytest -q`) after
the physics-core steps 4, 5 and 6 and before closing. The design input also asks for the
full suite at steps 3 and 7; see section 10.

Test files marked "(suggested)" are a proposed home, not fixed by the plan.

| # | Step | Main files | Tests | Gate | Status | Commit |
|---|---|---|---|---|---|---|
| T | Tracking system: protocol, program board, phase files SP1 to SP6, TODO.md restructure with IDs, this session's decisions, handoff archived, memory updated | docs/process, docs/phases, TODO.md, CLAUDE.md, memory | none (documents only); fast suite stays green | Compliance review; commit | [x] | 98eb5a6 |
| 1 | Guard and merge rule: digest pin of the four shipped planar experiments (runs, sweep points, bounds, cases, sensitivity runs); capture of the planar written outputs; the recorded silo_cold P* copied into test data; exclusive key families in `merge_run_dicts` and `_set_path` | src/launchsim/config.py | tests/test_config.py, tests/test_config_planar.py, tests/test_planar_pipeline.py, tests/data/ | Digests and golden unchanged | [x] | e2fb6ab |
| 2 | Exit-speed option: exactly one of `net_accel_g` / `exit_speed_mps`; planar metrics `net_accel_g`, `net_accel_mps2`, `stroke_m`; replay reads the metric | config.py, assist/constant_accel.py, metrics_planar.py, replay.py | tests/test_config.py, tests/test_silo.py (suggested) | Exit speed and push time against the closed form at 1e-9; trajectory equals the equivalent `net_accel_g` run | [x] | 1fc92d3 |
| 3 | Ramp start by depth, speed and closed-form height: one resolver used by both spec build sites; refusals; preflight before a results directory is made; requested and achieved ramp-start metrics | config.py, phases/prelude.py, assist/constant_accel.py, sim.py, search.py, metrics_planar.py, summary.py, results_io.py (the preflight call; cli.py too if the call sits there) | tests/test_config.py, tests/test_silo.py, tests/test_release_planar.py (suggested) | Ignition-event depth and speed against closed forms (1-D and planar); handoff table rows reproduced | [x] | 83d66dd |
| 4 | Altitude event for `height_method: event`: `ev_altitude_up`; `_coast` takes extra events (planar and 1-D); `FlightStart` separates "lights at a height" from "fails"; `no_ignition`; physics.md in the same change | phases/engine.py, planar.py, vertical.py, prelude.py, guidance.py, docs/physics.md | tests/test_events.py, tests/test_planar_events.py (suggested) | Event altitude = mouth + h (with drag and rotation); event time = closed form in constant-g vacuum; default runs have identical event tuples; full suite | [x] | 1a0b2af |
| 5 | Offload solver core: `vehicle.with_offload`; new `offload.py` with `OffloadProblem` (from a problem factory) and `solve_offload`; independent payload search at the solved load | offload.py (new), vehicle.py, search.py | tests/test_offload.py (new) | Toy closed forms; stage-1 pad control within the bound of section 5.3 (0 <= x_pad <= `final_payload_xtol_kg` / s; the bound in kg is written here before the gate is judged); pad and silo_cold reproduce their recorded P* within 0.002 kg (26,054.3962 and 27,553.2271 kg; section 5.12); 10x tighter budget moves the offload < 0.1%; full suite | [x] | a03e218 (branch sp1-step5) |
| 6 | Cross-vehicle decomposition from the existing loss budget and closure | compare.py | tests/test_closure.py | Residual below `closure_tol_mps` on the gate vehicle; toy with zero losses; full suite | [x] | 9ca508b (branch sp1-step5) |
| 7 | `offload:` block, pipeline and reporting: cases, pad control, sensitivity, energy inputs; per-point sweep solves; summary block; `metrics.json` key; replay role; in-memory entry point | config.py, results_io.py, summary.py, units.py (the MJ, kWh and tonne factors), compare.py, replay.py, cli.py | tests/test_config_planar.py, tests/test_planar_pipeline.py, tests/test_results_io.py (suggested) | Schema refusals; energy arithmetic; small-grid end-to-end; without the block, no `offload` key in metrics.json, no offload section in summary.md, and the step 1 output capture unchanged apart from the additions of steps 2 and 3 | [~] | |
| 8 | Experiments, pre-registered: `experiments/silo_offload_2d.yaml` and the one-case bridge on the README-loads vehicle; committed before any run | experiments/ | tests/test_config_planar.py | Resolves; committed; clean tree | [ ] | |
| 9 | Runs and findings: run and sweep from the clean commit; docs/findings/RQ1-fuel-offload-2d.md; physics.md, README results, findings index | results/ (summaries), docs/findings | full suite | No `bug_suspect`; decomposition explains the beat over the ideal screening estimate; honesty review | [ ] | |
| 10 | Close SP1: exit criteria gate; demo recorded; close-out decisions put to the user (B-004 order, which phase is next); the next phase file (SP2 in the planned order) fact-checked; handoff and prompt for it; memory; status lines; cold-read check | docs/, TODO.md, CLAUDE.md, README.md, memory | full suite | Independent gate; final commit | [ ] | |
| P | Public repository and its face (user request 2026-10-02, D-SP1-14 to D-SP1-16): repo khoks/RocketLaunchOptimizationSimulator public, all rights reserved (LICENSE); logo, banner, social preview; user manual docs/manual/; slide deck site/deck/ (HTML and PDF); animation gallery site/examples/; GitHub Pages site built by site/build.py and deployed by .github/workflows/pages.yml; README banner and links; push cadence in the protocol | LICENSE, assets/, docs/manual/, site/, .github/, README.md, docs/process/SESSION_PROTOCOL.md, CLAUDE.md | fast suite; site build with no broken link; visual QA screenshots | Visual, accuracy and compliance reviews; independent gate; Pages deployment succeeds | [x] | 9024d40 (merged e0b9fd8) |

### Step T. Tracking system

- Deliverables: docs/process/SESSION_PROTOCOL.md; docs/phases/README.md; phase files
  SP1 to SP6 (SP2 to SP6 from the designs in the approved plan and
  docs/phases/inputs/2026-09-30-design-3d-dynamics.md); TODO.md restructured with IDs
  (decisions D-, known issues KI-, backlog B-; nothing deleted, the Phase 0 to 2 tables
  stay as history); this session's decisions D-SP1-01 to D-SP1-13; the previous handoff
  moved to docs/handoff/archive/2026-09-30-phases-0-2.md and a new
  docs/handoff/NEXT_SESSION.md; CLAUDE.md "Working rules" pointing to the protocol;
  status lines; memory.
- No file under src/, tests/, experiments/, configs/ or results/ changes.
- Gate: compliance review (template followed, IDs consistent across files, no invented
  results), then one commit.

### Step 1. Guard and merge rule (config only)

- First, before any other change, add a test that pins sha256 digests of every resolved
  run dict and vehicle dict of the four shipped planar experiments
  (`PLANAR_EXPERIMENTS`, tests/test_config_planar.py:52). Capture the digests from the
  untouched code. "Every" means the runs, the sweep points (with their paired baselines),
  the bound runs, the cases and the sensitivity runs: the sweep points and overrides are
  the dicts `_set_path` produces, and `_set_path` is what this step changes. The
  serialisation is the one of `test_phase1_resolved_run_dicts_are_byte_identical`
  (tests/test_config_planar.py:257): `json.dumps` of `run_dict` and `vehicle_dict`, key
  order kept.
- Also before any other change, capture the planar written outputs as the reference for
  step 7's "unchanged" gate. Use the fixed-guidance fast experiment that
  tests/test_planar_pipeline.py already runs in the fast tier (the `fast_run` fixture:
  pad, silo_cold, silo_failed). Per run: the metrics.json key list, the time-series and
  event column lists, and a sha256 of summary.md with the lines that change from run to
  run removed (the title line, Timestamp, Git, and any wall-clock time or path). Steps 2
  and 3 add planar metric keys and summary rows on
  purpose; each of them updates the capture and lists its additions in its commit message.
- Copy the recorded silo_cold payload capacity (27553.227114190096 kg, section 5.12) into
  a tracked test data file with its provenance (results directory, git 7ad381f), because
  metrics.json is not tracked and a fresh clone has no full-precision reference. The pad's
  value is already in tests/data/calibration_record.json. Step 5's slow test compares
  against these two.
- Then add the exclusive families of section 5.9 to `merge_run_dicts` (config.py:1519) and
  `_set_path` (config.py:1585). The "exactly one" validators built on `model_fields_set`
  land with the fields they guard (steps 2 and 3).
- Tests: an override of one family drops the base's other families; keys of two families
  given together in memory is a ValueError; a sweep axis `assist.exit_speed_mps` over a
  `net_accel_g` parent ends with only the exit speed.
- Order note (a reading of the design input, to confirm in the step's review): the family
  rule acts on raw dicts, so its tests can call `merge_run_dicts` and `_set_path` directly
  before the model fields exist. The fields themselves (`exit_speed_mps`, `at_depth_m`,
  `at_speed_mps`, `at_height_m`, `height_method`) and the tests that resolve a full run
  with them arrive in steps 2 and 3.
- Gate: the new digests and the golden
  `test_phase1_resolved_run_dicts_are_byte_identical` (tests/test_config_planar.py:257)
  unchanged; `test_run_defaults` still passes.

### Step 2. Exit-speed option

- `ConstantAccelConfig` (config.py:537): `net_accel_g` and `exit_speed_mps` become
  optional, exactly one required. `net_accel_mps2` returns v^2 / (2 L) on the exit-speed
  path and `units.from_g(net_accel_g)`, unchanged, on the other.
- One extra assumption line, on the exit-speed path only. The existing net-acceleration
  text of `ConstantAccelAssist.assumptions` (constant_accel.py:174) must not change (golden
  1-D).
- New planar-only metrics in `planar_track_metrics` (metrics_planar.py:922):
  `net_accel_mps2`, `net_accel_g`, `stroke_m`. Keep them out of
  `PLANAR_REQUIRED_METRICS` and out of the 1-D `track_metrics`.
- replay.py:478 and :675 read the metric first and fall back to the config key, so a run
  defined by exit speed still gets its labels.
- Tests: integrated exit speed equals the configured v, and push time equals 2 L / v, to
  1e-9; the trajectory equals the run with `net_accel_g = v^2 / (2 g0 L)`.

### Step 3. Ramp start by depth, speed and closed-form height

- `IgnitionConfig` (config.py:624) gains `at_depth_m` (>= 0), `at_speed_mps` (>= 0),
  `at_height_m` (> 0) and `height_method: event | closed_form`.
- Config refusals: a pad run, any later stage, `at_depth_m > stroke_m`. With `fails: true`
  the settings are flagged as ignored (extend `flag_ignored_ignition_settings`,
  prelude.py:115).
- One resolver, `prelude.resolve_ignition(cfg, startup, assist, track, g_eff)`, used by
  both spec build sites (`sim.ignition_specs`, sim.py:803; `SearchContext.from_run`,
  search.py:534). It applies the closed forms of section 5.11:
  - depth: `push_time_s(L - d)` (constant_accel.py:139), reference push_start;
  - speed: v / a through a new `time_to_speed_s`, reference push_start;
  - closed-form height: the dt of 5.11, reference release;
  - snap to (0, release) within `ZERO_SPAN_S`;
  - ValueError for v > v_exit, for h at or above the drag-free apex, and for a model other
    than `constant_accel`.
- A preflight `sim.check_resolved(resolved)` builds the assist and ignition specs of every
  run before `make_run_dir` (results_io.py:284), so a bad config writes nothing. The call
  goes into the experiment and sweep entry points of results_io.py (the design input lists
  that file for this step), or into cli.py if the implementer puts it in the commands.
- `IgnitionSpec` (prelude.py:76) carries `trigger_kind` and `trigger_value`.
- Planar metrics, read from the stage-1 `ignition` event record: `ramp_start_trigger`;
  requested `ramp_start_requested_{t_s,depth_m,speed_mps,height_m}`; achieved
  `ramp_start_{t_rel_release_s,alt_m,depth_m,height_m,speed_mps,phase}`. Summary rows go
  after `ignition_rows` (summary.py:238). No 1-D metric is added: the achieved values are
  already in the 1-D events.csv.
- Tests: 1-D and planar ignition-event depth and speed against the closed forms at 1e-9;
  closed-form height exact under an injected `ConstantGravity`; the handoff table rows
  (-94.6 m at 17.9 m/s; 50 m at 54.2 m/s).
- This step still does not handle `height_method: event`; until step 4 it is refused.

### Step 4. Altitude event (events change: Plan-mode rule applies)

- docs/physics.md is updated in the same change ("Event rules", "Phases and events",
  "Stage-1 guidance and events (planar)").
- `ev_altitude_up(model, z, "ignition_height")`, modelled on `ev_ground` (engine.py:700),
  direction +1, tolerance `ATOL_M`.
- `fly_track` (prelude.py:483): for this trigger the push uses a `fails=True` schedule
  (the validated unlit path) and writes no ignition time.
- `FlightStart` (planar.py:549) gains `ign1_alt_m` and a `stage1_lights` property. The
  three `t_ign1_s is None` checks (planar.py:946 and :1039, search.py:605) and
  `sim._solve_fixed_delta` (sim.py:1326) use it.
- Planar `_coast` (planar.py:1344) gains `extra` events, listed on rising sub-phases only
  (altitude is monotone there because the coast is split at the apex). `_fly_to_kick`
  (planar.py:1446) coasts to the event, sets `t_ign` at the root time, and builds the
  thrust schedule and the kick deadline from it. A release already above h is decided by
  the planner itself, as it does for `kick_now`.
- Apex before h raises a new `GuidanceFailure("no_ignition")` (add the kind to
  `GUIDANCE_FAILURE_KINDS`, guidance.py:43). A searched run reports `search_failed`; a
  fixed-guidance run reports `guidance_failed`.
- 1-D `ascend` (vertical.py:336) and `_coast` (vertical.py:561) mirror this; apex first is
  a ValueError. No 1-D metric, summary row or assumption text changes.
- The search path is covered because `SearchContext._kick` (search.py:599) calls `to_kick`.
- Tests: event altitude equals z_exit + h to the event tolerance (1-D, and planar with
  drag and rotation); event time equals the closed form in constant-g vacuum, and the two
  height methods agree there; `no_ignition` when h lies between the true apex and the
  drag-free apex; a default-argument run has identical event tuples.
- Gate: full suite with the slow tests; golden exact tier.

### Step 5. Offload solver core (pure functions)

- `vehicle.with_offload(vehicle, mode, x)` builds on `with_stage_propellant`
  (vehicle.py:595). `Stage` requires propellant > 0, so x at or beyond a stage's load is
  the typed infeasible of section 5.4.
- Extract the body of `SearchContext.evaluate` (search.py:609-650) into a helper that takes
  the planner and the kick-cache key. `joint_root_crosscheck` (search.py:1822) already
  duplicates it. This is a refactor of validated code: the two payload capacities are its
  guard.
- New src/launchsim/offload.py: `OffloadProblem` and `solve_offload` as in section 5.4,
  built from a problem factory (vehicle -> `RecordingProblem`). Use a fresh `WarmStore`
  per problem (search.py:352). Flags are prefixed `offload:`; a search failure becomes a
  status that carries its kind.
- Tests (tests/test_offload.py):
  - `SpeedTargetToy` (tests/test_payload_search.py:102) with a head start v0: for stage 1,
    x* = m0 - m1 exp((V* - v0 - c ln(m2/m3)) / c); brentq forms for stage 2 and both.
    Symbols, as in that test file: m0 the full-load liftoff mass (both stages and the
    payload); m1 = m0 - m_p1 the mass at stage-1 burnout, which a stage-1 offload leaves
    unchanged; m2 = m1 - m_d1 the mass at stage-2 ignition; m3 = m_d2 + P the stage-2
    empty mass with the payload; c the exhaust velocity common to both stages; V* the
    target speed. The form follows from v0 + c ln((m0 - x)/m1) + c ln(m2/m3) = V*.
  - In vacuum with no gravity, x* equals `vehicle.stage1_propellant_saved_kg`
    (vehicle.py:650) when Isp_eff = Isp.
  - `no_offload` at v0 = 0; the range back-off.
  - Slow, gate vehicle, small grid: the recorded-run rule, verification within tolerance,
    the stage-1 pad control within the bound of section 5.3
    (0 <= x_pad <= `final_payload_xtol_kg` / s), a 10x-tightened budget
    (`SearchBudget.tightened`, search.py:295) moves x* by less than 0.1%.
- Gate: full suite; after the refactor the pad and silo_cold reproduce their recorded P*
  within 0.002 kg: 26,054.3962 kg (tests/data/calibration_record.json, `amended_rerun`)
  and 27,553.2271 kg (the value step 1 copied from the untracked metrics.json; section
  5.12). The one-decimal figures 26,054.4 and 27,553.2 kg are not the reference.
- CLAUDE.md layout gets a line for `offload.py` (done at close-out if not here).

### Step 6. Cross-vehicle decomposition

- `compare.cross_vehicle_decomposition(variant, baseline)` per section 5.5, taking
  `MatchedRun`s. Solved cases use the two final evaluations; fixed cases use
  `sim.matched_run` (sim.py:1480) at P_ref.
- Reuse `attribution_terms` (compare.py:607) and `_contributions` (compare.py:641); expose
  `closure.d_id_mps`. `matched_attribution` (657) and `ATTRIBUTION_KEYS` (754) are not
  touched, and no loss integral changes.
- Tests (tests/test_closure.py): a toy with all losses zero gives an ideal-delta-v change
  equal to the release-speed term; on the gate vehicle the residual is below
  `closure_tol_mps`.
- Gate: full suite.

### Step 7. `offload:` block, pipeline and reporting

- Block shape:
  - `reference`: must be the baseline.
  - `cases`: each `{name, of, solve: stage1, stage2 or both}` or
    `{name, of, fixed: {stage1_t, stage1_fraction, stage2_t, ...}}`, with optional
    `stage2_offload_t`, `stage1_dry_mass_added_t`, `paired_pad`.
  - `pad_control: true`.
  - `sensitivity_of: [...]`: uses the experiment's `sensitivity.params`, perturbing pad and
    silo alike.
  - `energy`: sourced Quantities for per-stage `fuel_mass_t` and
    `heating_value_MJ_per_kg`, validated against the vehicle's propellant.
- `SweepConfig.offload: [case names]` solves those cases at each sweep point and adds
  columns to `sweep_index.csv` (planar only; the 1-D `SWEEP_INDEX_METRICS` stay).
- `planar_offload(...)` is called inside `planar_experiment_result` (results_io.py:945),
  which is pure. The SP2 app can then call `resolve_experiment(dict, vehicle_dict)`,
  `sim.run_resolved` and `planar_experiment_result` without writing anything.
- `ExperimentResult.offload` rows. The `metrics.json` key `offload` and the summary section
  are written only when the block is declared, so existing planar outputs do not change.
- Summary block "Propellant saved at fixed payload", with a basis line
  (`OFFLOAD_COMPARISON_BASIS`: different vehicles, same payload and orbit):
  - tonnes; % of stage-1, stage-2 and total load;
  - RP-1 and LOX removed; heat (LHV), electricity, and the ratio labelled "not an
    efficiency";
  - liftoff mass, MECO, max-Q against the pad's, felt g, interface force, facility length;
  - the ideal-screening offload at this release speed and the ratio; the decomposition
    table;
  - verification delta, pad control and net value, paired-pad P*;
  - the caveat list (`OFFLOAD_CAVEATS`).
- Checks: a passing decomposition is "explained"; a failing one is `bug_suspect` and blocks
  findings. Offload rows never enter the "Unexplained beats" list.
- Replay: `replay.run_source` (replay.py:241) gets an offload role so the offloaded run can
  be replayed beside the pad. Derived run names must stay within `MAX_NAME_LEN` (64).
- Tests: schema refusals; energy arithmetic; summary and metrics on a small-grid run; an
  in-memory dict run; an experiment without the block produces unchanged outputs.
  "Unchanged" is judged against the output capture of step 1: no `offload` key in
  metrics.json, no offload section in summary.md, and the captured key lists, column lists
  and summary digest equal to the capture as steps 2 and 3 left it.
- The MJ, kWh and tonne factors of the energy comparison go into units.py, the only place
  conversion factors appear (CLAUDE.md); the design input lists units.py for this step.
- Note for the implementer: the design input does not spell out the reference payload of
  a sensitivity case. "Perturbing pad and silo alike" implies the perturbed pad's capacity
  (the same-perturbation basis of `_run_planar_sensitivity`); state the choice in the
  basis line.

### Step 8. Experiments and pre-registration

- experiments/silo_offload_2d.yaml on configs/vehicles/generic_f9_class_2d.yaml. Shared
  blocks copied verbatim from experiments/silo_screening_2d.yaml (lines 16-65); baseline
  pad.
- Variants: `silo_cold` (3 g, 100 m, cold start, lit 0.5 s after release with the 2 s
  ramp); `silo_hot_ramp_on_track`; `silo_cold_200m` (200 m, `exit_speed_mps: 76.71`, about
  1.5 g net, so lower felt g).
- Cases on `silo_cold`: stage 1 (headline, paired pad, sensitivity +/-10% on stage-1 dry
  mass, Isp, C_D and drive efficiency); stage 2; both; stage 1 with a 2 t stage-2 offload;
  stage 1 with +2, +4 and +8.1 t; fixed 5% and 10%; pad controls. On the hot ramp: stage 1.
- Sweeps, each solving the stage-1 offload (20 points):
  - stroke [25, 50, 100, 200, 300] m at 3 g;
  - stroke [50, 100, 200, 300] m at exit speed 76.71 m/s (the same offload is expected,
    with lower g and power and a longer facility; if it is not the same, report that);
  - `at_depth_m` [100, 75, 50, 25, 0];
  - `at_height_m` [10, 40, 100, 200] by event, plus two closed-form points. A sweep grid
    is a Cartesian product, so the two closed-form points are their own sweep entry
    (`height_method: closed_form`). Proposed heights: 40 m and 200 m, two of the event
    heights, so the two methods can be compared point for point; both lie below the
    drag-free apex (about 301 m at 76.7 m/s). The plan does not name the heights; the
    choice is fixed by the pre-registration commit of this step.
- A note on 76.71 m/s. It is the rounded exit speed of the 3 g / 100 m silo, which
  releases at sqrt(2 x 3 g0 x 100 m) = 76.70717 m/s (`exit_speed_mps` in the shipped
  run's metrics.json). The rounded value is 0.0028 m/s higher. At the probe's rate (41.1 t
  over 76.7 m/s) that is about 1.5 kg of offload (an estimate), far above the solver
  tolerance of 0.05 kg. So "the same offload" is judged among the fixed-exit-speed sweep's
  own points, all at 76.71 m/s, and `silo_cold_200m` is compared with that sweep's 100 m
  point, not with the 3 g `silo_cold`, which differs by the rounding. The alternative is
  to write the unrounded 76.7071704601 in the file; choose before the pre-registration
  commit and say which in the findings note.
- The bridge: one stage-1 case on configs/vehicles/generic_f9_class_2d_readme_loads.yaml,
  following experiments/silo_bridge_2d_readme.yaml (D-SP1-13). Its file name is the
  implementer's choice.
- Both files are appended to `PLANAR_EXPERIMENTS` (tests/test_config_planar.py:52).
- Estimated serial time: about 15 min for `run` and 17 min for `sweep` (a solved case is
  about 33 s; a sweep point about 48 s). These are estimates; machine speed varies about
  3x under load.
- Commit before any run. Runs start from a clean tree.

### Step 9. Runs and findings

- `run` and `sweep` from the clean commit of step 8. Check summary.md for the offload
  block, the decomposition residual, the pad controls and the flags. Compare the solved
  value with the handoff probe as a sanity check only, never as a target.
- docs/findings/RQ1-fuel-offload-2d.md (README research question 1, "Net benefit"). Outline:
  definition; headline with caveats beside it; why it exceeds the screening estimate
  (decomposition; yardstick on the gate vehicle and on README masses); penalty rows and
  break-even; stage 2 and both with the pad control; depth; ramp start; energy;
  sensitivity; limits; reproduction.
- Caveats that travel with the number: calibration +14.3% (with the bridge row);
  sweep-optimized and unthrottled guidance; no structural mass for the 4 g push;
  prescribed-acceleration drive with a massless carriage and no shaft drag; max-Q of the
  offloaded run against the pad's; tanks partly filled with the mixture ratio kept and no
  ullage or centre-of-gravity effects.
- docs/physics.md additions: "Silo model" (exit-speed form); "Phases and events" and "Event
  rules" (the four triggers, `ignition_height`, `no_ignition`), if not complete from
  step 4; "Figures of merit (planar)" ("Propellant offload at fixed payload");
  "Screening-beat rule" ("Cross-vehicle decomposition"); "Reporting definitions" (energy
  comparison); "Experiment schema" (offload block, exclusive families); "Assumptions";
  the test-to-equation map.
- README results and RQ1 status; docs/findings/README.md index.
- KI-006 (TODO.md): the gamma*-sensitivity diagnostic (`gamma_sensitivity_step_deg: 0.5`
  in the shared checks block) also runs on the offload runs. Report in the note whether M4
  (blocking) and M2 (diagnostic) hold over gamma* +/- 0.5 deg for them, and disclose every
  point where they do not, as the earlier notes do.
- Gate: no `bug_suspect`; the decomposition explains the beat over the ideal screening
  estimate; honesty review of the note. A result that undercuts the hypothesis is reported
  as plainly as one that supports it.

### Step 10. Close SP1

The order is the end checklist of SESSION_PROTOCOL.md, section 7.

- Exit criteria (section 8) checked by an independent gate; full suite; ruff.
- Demo recorded under docs/demos/SP1/ (section 9).
- Close-out decisions put to the user, recommendation first: whether the structural-mass
  model (TODO.md B-004, README Phase 3) moves ahead of the 3-D work (section 10, item 8),
  and which phase runs next (SP2 in the planned order; the board allows SP3 first). The
  answers are logged as decisions. The points below name SP2; if the user chooses another
  phase, they apply to that phase's file instead.
- docs/phases/SP2-launch-app-2d-scene.md fact-checked against the code as it then is
  (line numbers, the offload entry point, the replay role).
- docs/handoff/NEXT_SESSION.md and the SP2 prompt rewritten; this session's handoff
  archived (as 2026-09-30-SP1-in-progress.md, since it was written while SP1 was in
  progress); memory updated.
- Status lines: this file, docs/phases/README.md, TODO.md, CLAUDE.md, README.md.
- Cold-read check of the handoff, the SP2 phase file, the memory notes and the prompt by
  an agent that did not write them (protocol section 7, item 11).
- Final commit, subject `Close SP1: trackers, handoff, next phase file`.

## 8. Exit criteria

1. Tracking system in place; phase files SP1 to SP6 exist; handoff and prompt for SP2
   written (or for the phase the user chooses at close-out, step 10).
2. The exit-speed option and all four new ramp-start parameterisations (depth, speed,
   closed-form height, height by event) pass their closed-form tests.
3. The offload solver passes its toy closed forms; the pad control is about 0 for stage 1,
   meaning 0 <= x_pad <= `final_payload_xtol_kg` / s as defined in section 5.3 (about
   1.4 kg by the estimate there; the bound in kg is in the step 5 row); the independent
   payload search reproduces P_ref at each solved case within
   `checks.search_final_flag_rel` x P_ref (or the case is flagged).
4. The `silo_offload_2d` run and sweeps come from a clean committed tree with no
   `bug_suspect`.
5. The findings note passes the honesty review; the headline is stated with the penalty
   rows and the sensitivity.
6. Full suite green; golden 1-D and planar digests unchanged; ruff clean.
7. Demo recorded under docs/demos/SP1/.
8. The public repository is current (main pushed after the closing commit) and the GitHub Pages
   site is live with the landing page, the user manual, the slide deck and the animation
   gallery, all updated with SP1's finding (step P, D-SP1-14 to D-SP1-16).

Each criterion is checked by an independent gate at step 10. The phase closes with an open
criterion only if the user accepts the miss, and the acceptance is logged in TODO.md.

## 9. Demo script

Run from a clean commit, in the repository root:

    uv run python -m launchsim run experiments/silo_offload_2d.yaml
    uv run python -m launchsim sweep experiments/silo_offload_2d.yaml
    uv run python -m launchsim replay results/silo_offload_2d/<timestamp> --runs pad <offloaded silo run>

What to look at:

- The "Propellant saved at fixed payload" block of summary.md: tonnes and % for stage 1,
  the pad controls, the penalty rows, the decomposition residual, the flags.
- The replay page: the full-load pad and the offloaded silo run reach the same orbit with
  the same payload.

What to save under docs/demos/SP1/: the console output of the three commands, a copy of
the offload block of summary.md, and the replay page (`--out`) or a screenshot of it. To
view the page in the browser pane, serve its folder with `python -m http.server` on
127.0.0.1 (a file opened from outside the project renders as a static snapshot). The name
of the offloaded silo run is fixed by step 7.

A trap with the saved page: `.gitignore` ignores `*_replay.html` (and `*_animation.mp4`,
`*_animation.gif`) at any depth, and the default replay file name ends in `_replay.html`.
A page saved under docs/demos/SP1/ with such a name would not be committed. Either add
`!docs/demos/**` after those patterns in `.gitignore` in step 10, or give the saved page a
name that does not match (for example `pad_vs_offloaded_silo.html`). Check with
`git status` that the demo files show up before the final commit.

## 10. Risks and open questions

Risks from the design input, each with its resolution:

| # | Risk | Resolution | Needs the user |
|---|---|---|---|
| 1 | Stage-2 marginal value is near zero, so stage-2 and both-stage offloads may be large, small after the pad control, or ill-conditioned | Stage 1 is the only headline. Stage 2 and both are reported net of the pad control and labelled as a property of the vehicle model | no |
| 2 | The gamma* optimum moves with the offload | `refine_capped` is flagged; the independent payload search catches a suboptimal gamma*, and x* is then reported as a flagged lower bound | no |
| 3 | Final bracket in x: the shared 20 kg start spans only about 0.7 kg of m_res, so `search_final_mismatch` may flag harmlessly | If it does, add bracket-only settings to the `offload` block. Do not touch `search` | no |
| 4 | Max-Q of the offloaded run exceeds the pad's (38.4 against 37.2 kPa in the handoff probe) | Report it beside the number. No constrained variant: there is no throttle model | no |
| 5 | The heating value needs a citable LHV source | If none is at hand, mark it `assumed: true`. The ratio excludes LOX production and generation losses and says so | no |
| 6 | Calibration miss (+14.3%) | One headline case on the README-loads fork as a robustness row (D-SP1-13, step 8) | no |
| 7 | Existing cross-vehicle sensitivity rows still print as "Unexplained beats" (TODO.md KI-008; KI-011 for a pad baseline) | Deferred: passing them the new decomposition would change existing summaries on re-run | no |

Further points and open questions:

| # | Point | Recommended resolution | Needs the user |
|---|---|---|---|
| 8 | The structural-mass model (README Phase 3) decides whether the headline survives, and it sits after the 3-D work only because of the order chosen (D-SP1-07) | Keep the +2, +4, +8.1 t rows beside every offload number. Offer to move Phase 3's structural mass up at the SP1 session boundary | yes, at close-out |
| 9 | The design input asks for the full suite at steps 3 and 7; the approved plan requires it after steps 4, 5, 6 and before closing | Run it at 3 and 7 as well when time allows (4 to 20 min); the plan's rule is the minimum | no |
| 10 | Either experiment command may exceed 30 min serial | Trim the fixed-exit-speed sweep before the pre-registration commit of step 8. A change after that commit is a pre-registration amendment and is logged | only if amended after the commit |
| 11 | The handoff probe's 10% figure could act as a target | It is compared with the solved value as a sanity check only. A different solved value is reported as it is | no |
| 12 | The reference payload of an offload sensitivity case is not spelled out in the design input | Use the same-perturbation pad's capacity and state it in the basis line (step 7) | no |
| 13 | The closed-form height differs from the event height under drag, mu/r^2 and rotation | Offer both (D-SP1-06); report requested and achieved height from the event record | no |
| 14 | Line numbers in section 6 drift as the steps land | Each step re-checks the lines it uses; step 10 re-checks the SP2 phase file | no |
| 15 | A step's gate cannot be met, or an exit criterion stays open | Stop, report, and ask. The phase closes with an open criterion only on the user's acceptance | yes, if it happens |

## 11. Session log

**2026-09-30 (session 1).**

- Planning in Plan mode, from docs/handoff/NEXT_SESSION.md (now
  docs/handoff/archive/2026-09-30-phases-0-2.md). Three read-only code surveys and two
  designs were made at commit 2eebcae and saved in docs/phases/inputs/.
- The five decisions of the handoff's section 5 were put to the user and answered:
  3-D as true dynamics in three stages (D-SP1-01); a local app as the visual tool
  (D-SP1-02); offload semantics with stage 1 as the headline, plus stage 2 and both
  (D-SP1-03), and the structural penalty as parametric rows (D-SP1-04); depth as
  `stroke_m` with one of two keys (D-SP1-05); the ramp start in all the ways offered
  (D-SP1-06).
- Scope decisions: the order of work (D-SP1-07) and one fresh session per phase with
  matured work tracking (D-SP1-08).
- Design decisions approved with the plan: D-SP1-09 (offload block and post-pass),
  D-SP1-10 (pad control), D-SP1-11 (target under J2, for SP5), D-SP1-12 (6-DOF as a
  fly-out, for SP6), D-SP1-13 (bridge on the README-loads vehicle).
- The plan was approved by the user
  (docs/phases/inputs/2026-09-30-SP1-approved-plan.md).
- Baseline confirmed: clean tree at 2eebcae, fast suite green.
- Step T started: tracking system (protocol, program board, phase files, TODO.md with IDs,
  handoff archive).
- Step T passed its gate: commit 98eb5a6 (38 review findings, 36 fixed in the workflow,
  2 by the main session; README edits beyond the status paragraph accepted, section 12
  item 4). Next: step 1 (planar digest pin and the config merge rule).
- 2026-10-01: step 1 passed its gate: commit e2fb6ab (planar digest pin of 90 resolved
  runs, planar output capture, recorded payload capacities in test data, exclusive key
  families in `merge_run_dicts` and `_set_path`; 42 new tests, fast suite 970 passed; two
  review rounds, no blocker; the gate regenerated the digests from a 2eebcae worktree).
  Next: step 2 (exit-speed option).
- 2026-10-01: the first attempt at step 2 was cut off when the Fable usage limit ran out
  (every agent of the workflow failed; the implementer's edits stayed in the tree with no
  report). The user switched the session to Opus 5.5 and step 2 was relaunched with the
  instruction to review the partial diff critically and finish it.
- 2026-10-02: step 5 started in parallel in a git worktree on branch `sp1-step5` (it
  depends only on step 1 and touches other files); it merges back after its gate.
- 2026-10-02: step 2 passed its gate: commit 1fc92d3 (exit-speed option; three planar push
  metrics; replay label from the metric; fast suite 1004 passed, slow tier 23 passed; one
  review round, four minor findings). Next: step 3 (ramp start by depth, speed and
  closed-form height).
- 2026-10-02: step 5 passed its gate on branch `sp1-step5` (worktree): commit a03e218,
  merged into main after step 3 (offload solver core; 13 fast and 3 slow offload tests;
  refactor guard reproduces the recorded pad and silo_cold payload capacities bit for bit;
  full suite 1011 passed; two review rounds, no blocker left). The stage-1 pad control
  bound is 1.63 kg (s = 0.0307 kg/kg) and the control ends no_offload by grams (section 12).
  Validation measurement only, not a finding: silo_cold's stage-1 offload solves to
  about 41.26 t at the pad's payload. Step 6 started on the same branch.
- 2026-10-02: step 3 passed its gate: commit 83d66dd (ramp start by depth, speed and
  closed-form height; one resolver for both spec build sites; preflight before any results
  directory; planar ramp-start metrics; full suite 1132 passed; two review rounds, the
  round-1 major finding (a preflight refusal reached the CLI as a traceback) fixed).
- 2026-10-02: branch `sp1-step5` (step 5) merged into main: merge commit 04f6542, no
  conflicts; fast suite 1122 passed and ruff clean on the merged tree. Step 6 continues on
  the branch. Next on main: step 4 (altitude event).
- 2026-10-02: the user asked to publish the repository publicly on GitHub, push after every
  step, and add a logo, banner, slide deck, animation examples, user manual and Pages site
  (D-SP1-14 to D-SP1-16; license all rights reserved; repo khoks/RocketLaunchOptimizationSimulator;
  noreply email for new commits). LICENSE committed (e4f36ee), repository created and main
  pushed. Step P started on branch `public-site` (worktree); the protocol gained the push
  rule (section 4, item 7) and the public-face refresh at phase close (section 7, items 6
  and 14).
- 2026-10-02: step 6 passed its gate on branch `sp1-step5`: commit 9ca508b (cross-vehicle
  decomposition; lossless and known-difference toys; slow gate-fork test closes to
  -4.1e-12 m/s; full suite 1019 passed; two review rounds, the round-1 major finding fixed).
  Validation measurement only, not a finding: on the gate fork the 228.2 m/s ideal
  delta-v change of silo_cold's stage-1 offload splits into release speed 76.7, gravity
  124.8, back-pressure 13.3 and the pad's hold-down burn 14.4 m/s (drag, steering and
  fairing small); the offload is 2.755 times the ideal-screening estimate and the row is
  explained. The branch merges into main after step 4.
- 2026-10-02: step 4 passed its gate: commit 1a0b2af (ramp start at a height by an
  altitude event; pending-ignition state; `no_ignition` failure; event function folded
  past the apex; 38 fast and 1 slow new tests; full suite 1192 passed; two review rounds,
  seven round-1 findings fixed). The step's deviations were written into section 12 by the
  step itself; items 1-4 reached main early in the step-6 tracker commit e19d7ed (the
  phase file was staged while step 4 was editing it), and 1a0b2af carries the final text.
- 2026-10-02: branch `sp1-step5` (step 6) merged into main (merge commit c8e0020),
  no conflicts; full suite on the merged tree 1205 passed (exact golden tier). Next: step 7 (offload block,
  pipeline and reporting).
- 2026-10-03: step P passed its gate on branch `public-site`: commit 9024d40, merged into
  main as e0b9fd8 and pushed (brand assets, 12-chapter user manual, 17-slide deck with PDF,
  animation gallery with three interactive replays and three MP4/GIF animations, Pages
  site built by site/build.py with Python-Markdown 3.11 in CI only, README banner and
  License section; visual, accuracy and compliance reviews, two fix rounds). GitHub Pages
  enabled with GitHub Actions as the source; the first deployment succeeded and the site
  is live at https://khoks.github.io/RocketLaunchOptimizationSimulator/ (landing, deck,
  examples and manual checked in the browser). The fuel-offload question is shown there
  as not answered yet; step 10 refreshes the site, deck, gallery and manual with SP1's
  finding.

## 12. Deviations from the plan

Step T (2026-09-30):

1. **Decision ids.** The plan writes decisions as `D-nnn`; the tracking system uses
   `D-<phase>-<nn>` (D-SP1-01, and D-P0, D-P1, D-P2 for the earlier ones). Reason: a
   decision can be traced to its phase, and the groups can grow without renumbering.
   Documented in TODO.md (notes on the SP1 planning group) and SESSION_PROTOCOL.md
   section 9.
2. **Session protocol beyond the plan's outline.** The plan lists a start checklist, a
   step loop and an end checklist. After the step-T review the protocol also has: a
   tracker commit after each step commit, so the tree is clean between steps; a fixed
   subject for the bookkeeping commit, because a handoff cannot contain its own commit
   hash; close-out decisions put to the user before the next phase file is finalised; a
   cold-read check of the handoff, memory and prompt; and a rule for a session that ends
   without its checklist. Reason: the review found that the outline could not be followed
   as written. No scope of SP1 changes.
3. **Gates made checkable.** Additions to the plan's gates, none of them a change of
   scope: step 1 also pins sweep points, bounds, cases and sensitivity runs, captures the
   planar written outputs and copies the recorded silo_cold P* into test data; step 5's
   pad control has a numeric bound (section 5.3) and its P* references are given with
   their digits and sources (section 5.12); step 7's "unchanged" is defined against the
   step 1 capture; step 3 also lists results_io.py and step 7 lists units.py, as the
   design input does; step 8 names the two closed-form heights as a proposal and notes the
   rounding of 76.71 m/s.

4. **README.md edits beyond the status paragraph.** The step-T gate's criterion limited
   README.md to the status paragraph and one bullet. The review also corrected the
   roadmap row for Phase 3 (it now includes the structural mass for the 4 g push and reads
   "Planned, after SP1-SP6 unless moved up" instead of "Next") and the repository layout
   tree (the new docs folders and the TODO.md description). The gate reported this as its
   only failed check. The edits are accurate and within the plan's tracking table
   ("README.md: status lines, layout"), so the step owner accepted them and the gate
   criterion is read with that scope; reverting them would leave the README
   contradicting its own status paragraph.

Step 1 (2026-10-01, commit e2fb6ab):

1. **The summary digest is compared in the capture environment only.** Elsewhere the test
   skips (or fails with `LAUNCHSIM_REQUIRE_EXACT_GOLDEN=1`), as the golden 1-D exact tier
   does, because the summary prints integrated numbers that differ on another numeric
   stack. The structure (files, metrics key paths, CSV columns) is compared everywhere.
2. **The output capture holds more than the brief listed**: the files written, the
   metrics.json key paths outside the runs (where an `offload` key will appear), the
   resolved_config.yaml top-level keys and the normalised summary text, so that a digest
   change reads as a diff.
3. **An existing fixture body moved.** `fast_run` in tests/test_planar_pipeline.py now
   calls a module-level `fast_experiment(repo_root)` with the same statements, so the pin
   helper and the tests build the same experiment. No test body changed.
4. **`ExclusiveKeysError` is a `ValueError` subclass**, and the two-families check also
   covers dicts the merge would replace wholesale and two override paths with one parent.
   A key counts as given when it is present, an explicit null included; the "exactly one"
   validators of steps 2 and 3 must stay consistent with that.
5. **The pin names c587a08 as its reference commit** (HEAD when captured; src, tests,
   experiments and configs identical to 2eebcae).
6. **For step 8:** a YAML merge key (`<<: *silo`) is resolved by the loader, so a variant
   that adds `exit_speed_mps` to an anchor carrying `net_accel_g` arrives with both and is
   refused. `silo_cold_200m` must write its assist block out or use an anchor without the
   acceleration.

Step 2 (2026-10-02, commit 1fc92d3):

1. **Bit identity with the equivalent `net_accel_g` run holds only where the two
   accelerations are the same double.** v^2/(2L) and (v^2/(2 g0 L)) g0 coincide for the
   tested pair (76.71 m/s, 200 m), which the tests assert as a precondition before
   comparing runs exactly. For other pairs they differ by 1-2 ulp and planar runs agree
   to integrator noise (about 5e-8 relative, reproduced at 83.3 m/s and 137 m). Exit
   speed and push time hold to about 5e-16 either way. Documented in docs/physics.md.
2. **A serializer was added**: `ConstantAccelConfig` drops the unused push key from
   `model_dump`, because "a key present as null counts as given" (step 1) otherwise broke
   the existing dump round trip used by tests/test_convergence.py.
3. **The validator also refuses a derived acceleration that is not finite and positive**
   (an overflowing, underflowing or infinite-stroke case).
4. **1-D exit-speed runs also get the extra assumption line.** The standing rule "no new
   assumption text on 1-D runs" is read as protecting the existing `net_accel_g` runs,
   whose text is unchanged; hiding the line would leave a 1-D exit-speed run with an
   assumption it does not state.
5. **The three push metrics are also written for silo_failed and the sensitivity
   records** (9 key paths in the output capture), since `planar_track_metrics` serves all
   of them.
6. **docs/physics.md quoted the 3 g0, 100 m felt load as 3.9992 g0**; the value is
   (3 g0 + mu/R_E^2)/g0 = 3.99915, so 3.9991 g0 to four decimals. physics.md is corrected;
   tests/test_silo.py still quotes 3.9992 (KI-021).

Step 5 (2026-10-02, commit a03e218 on branch sp1-step5):

1. **Run in parallel.** Step 5 ran in a git worktree on branch `sp1-step5` while steps 2
   and 3 ran in the main checkout, because it depends only on step 1 and its files do not
   overlap theirs. The branch is merged into main after step 3 and the full suite is
   re-run on the merged tree.
2. **The stage-1 pad control ends `no_offload`, not `ok`, by grams.** At the shipped and
   test budgets x_pad = 0 with m_res(0) = -0.0016 kg (-0.0017 kg at the test budget); the
   cause is warm-start-dependent LTG convergence inside the acceptance box (docs/physics.md
   "Pad control, and why"). Under the 10x-tightened budget it ends `ok` with x_pad =
   0.044 kg. It is within the section 5.3 bound (measured s = 0.0307 kg/kg, bound
   0.05 / s = 1.63 kg against the estimated 1.4 kg); the slow test accepts `no_offload`
   when -final_payload_xtol_kg < m_res(0) < 0. Step 7 must report such a control as
   "x_pad = 0, m_res(0) = -0.0016 kg", a resolution effect, not a failure.
3. **Toy.** tests/test_offload.py has its own `HeadStartToy`, modelled on `SpeedTargetToy`
   (same masses and physics) plus a quadratic gamma* dependence so the search has an
   interior optimum; the solver needs a RecordingProblem built from a vehicle. The toy's
   verification tolerance is `search_final_flag_rel` = 2e-3 (the shipped 1e-4 is 0.006 kg
   at the toy's 60 kg payload, below the verification's own resolution); the no_offload
   toy test uses P_ref = closed-form capacity + 1 kg (exactly at capacity the sign is
   ambiguous; the own-capacity case is a separate test).
4. **The slow gate tests fly the shipped search budget** (rtol 1e-8; every reported number
   comes from the final mode at 1e-10), as tests/test_calibration.py does; both budgets
   give x* within 0.0003 kg.
5. **The solver does not use the extracted helpers.** `evaluate_planner` and `solve_delta`
   exist as asked and `joint_root_crosscheck` uses `solve_delta`; the offload solver goes
   through the factory with one problem and one fresh WarmStore per x (`OffloadWarmStore`),
   which keeps it generic. The verification runs `search.run_search` on
   `factory(offloaded vehicle)`, equivalent to `sim.run_resolved` for the planar factory.
6. **Cost.** A stage-1 solve with its verification took 89 s at the shipped budget on a
   loaded machine (design estimate about 33 s); the pad control about 30 s. Step 8's
   runtime estimate must use the measured figure.
7. **The refactor guard is its own slow file**, tests/test_silo_screening_record.py.

Step 3 (2026-10-02, commit 83d66dd):

1. **A speed a rounding above the exit speed snaps to release.** A speed is refused only
   when v/a lies more than ZERO_SPAN_S after release; inside that window it snaps to
   release, because with the push stated by `exit_speed_mps` sqrt(2aL) can come out an ulp
   off the configured speed.
2. **The closed-form height uses the rationalized form** 2h / (v_e + sqrt(v_e^2 - 2gh)),
   the same number without cancellation at small h. Measured planar miss of the closed
   form against the achieved height on the gate fork: -6e-5 m at 5 m, -3.8 mm at 40 m,
   -25 mm at 100 m, -0.11 m at 200 m, -0.27 m at 280 m.
3. **1-D runs stated by a trigger get one ramp-start assumption line** (written by
   `fly_track`, which both models share), the same reading as step 2: existing 1-D runs
   and the golden outputs are unchanged.
4. **Achieved ramp-start keys are written on every recorded planar run** (a failed run has
   all six as None; a pad has depth and height None and the others from its HOLD record);
   requested keys only when a trigger is set. `compare_planar` therefore also adds three
   `delta_ramp_start_*` items to comparisons (harmless).
5. **The preflight also runs in `cli.load_experiment`**, so a refused configuration prints
   one `error:` line and exits 1 (a round-1 review finding: it was a traceback). It checks
   every resolved run even for `--variant NAME`, which is stricter than needed.
6. **`IgnitionSpec.from_config` now refuses non-time configs**; specs with a trigger are
   built only through the resolver. `sim.ignition_specs` takes (assist, track, g_eff).
7. **Two comments in existing tests are stale** (KI-023): they were left alone under the
   rule that existing tests stay unmodified.

Step P (2026-10-02, added by the user):

1. **A step added to SP1.** The user asked mid-phase to publish the repository on GitHub in a
   new public repository, to push after every step, and to give it a logo, banner, slide deck,
   animation examples, a user manual and a GitHub Pages site kept current (D-SP1-14 to
   D-SP1-16). Step P builds these on branch `public-site` in a worktree, in parallel with the
   physics steps; exit criterion 8 is added; step 10 refreshes the site, deck, gallery and
   manual with the finding. The repository was created and main pushed on 2026-10-02 at
   e4f36ee (the LICENSE commit).

Step 4 (2026-10-02):

1. **Two existing test files changed, both forced by retiring the step-3 refusal** (step 3:
   "until step 4 it is refused"). tests/test_config.py:
   `test_ignition_states_its_ramp_start_one_way` (RAMP_STARTS gains a height_event entry
   and the RAMP_START_TRIGGERS assertion gains "height_event"; RAMP_STARTS also
   parametrizes `test_ignition_dump_states_the_ramp_start_by_its_one_family`, whose body
   is unchanged and which gains the height_event cases, python and json) and
   `test_ignition_ramp_start_refusals` (the case `{at_height_m: 40, height_method:
   event}` -> "arrives in SP1 step 4" is replaced by `{height_method: event}` without a
   height -> "at_height_m and height_method come together").
   tests/test_silo.py::`test_resolve_snaps_a_start_at_the_release_and_refuses_what_the_push_cannot_reach`
   (the "arrives in SP1 step 4" refusal is replaced by the event method's refusal at the
   drag-free apex and at 1.01 of it, plus a resolve below it). Each old assertion pinned
   step-3 behaviour that step 4 retires, and each replacement is an equal or stronger
   check. Section 5.12's "the only edit to an existing test" is read with this exception.
2. **1-D runs stated by `height_method: event` carry one ramp-start assumption line**
   (written by `fly_track`, which both models share), the same reading as step 2
   deviation 4 and step 3 deviation 3: existing 1-D runs and the golden outputs are
   unchanged, and no 1-D metric or summary row is added.
3. **The preflight bound is conservative for the event method only without drag;
   with drag it is permissive** (review rounds 1 and 2). It refuses h >= v_e^2 /
   (2 g_eff), the apex of a drag-free coast at constant g_eff, for both methods, as the
   brief requires. Without drag (vertical_1d) it is conservative: under mu/r^2 such a
   coast peaks about 1.4 cm higher (1-D: 300.270 m against 300.256 m; the gate fork
   with C_D x 1e-12: 301.075 m against 301.061 m), so heights in that band are refused
   although the coast would reach them
   (`test_one_d_flown_apex_lies_above_the_preflight_bound`). With drag (every planar_2d run) it is permissive: the gate fork at its file payload
   peaks at 300.647 m, so the bound admits [300.647, 301.061) m, a band about 0.41 m
   wide of heights that resolve but never light (GuidanceFailure `no_ignition`;
   `test_planar_apex_below_the_height_is_no_ignition` and the two run-status tests).
   Documented in docs/physics.md ("Silo model", the conversion table and the height by
   event).
4. **For step 8:** the flown apex, and so the `no_ignition` band, moves with payload and
   C_D (gate fork: 300.629 m at P = 0 to 300.653 m at 30 t; 300.605 to 300.690 m for
   C_D +/-10%). A height-event variant within a few centimetres of the apex can fail in
   a sensitivity arm or at a lighter payload (reported as `search_failed` or
   `guidance_failed`). Heights chosen well below the apex avoid it.
5. **`ev_altitude_up` is not the plain mirror of `ev_ground`: it folds its function past
   an apex** (an events-rule addition beyond the brief's "modelled on ev_ground,
   direction +1, tolerance ATOL_M"). g = altitude - z + k min(w, 0)^2, w the altitude
   rate (v_r planar, v on 1-D), k = `APEX_FOLD_GAIN_S2PM` = 1 / (2 a_min) with a_min =
   `APEX_FOLD_ACCEL_MPS2` = 1 m/s^2, two new event-solver constants in engine.py (not
   physics). Why: scipy tests an event's sign only at step ends, and the apex split cuts
   the phase after the step; a step that overshoots the apex has the altitude back below
   z at its end when z lies just below the apex, so the plain mirror loses the crossing
   and the coast ends at the apex (measured on the uncapped 1-D coast: z = 299 m against
   a 300.27 m apex was missed). The fold is zero while w >= 0 and continuous at the
   apex, so inside the rising phase g is the altitude difference exactly and the root is
   unchanged; past the apex (downward acceleration >= a_min) it keeps g >= apex - z and
   rising, so a crossing before the apex is found, and an apex below z still ends the
   coast first. Documented in docs/physics.md ("Event rules", the altitude event) and
   pinned by `test_ev_altitude_up_is_the_altitude_crossing_with_a_fold_past_the_apex` and
   `test_ev_altitude_up_finds_a_crossing_just_below_the_apex` (with the gain set to 0
   the crossings 1, 1e-2 and 1e-4 m below the apex are missed).
6. **Step-3 text and the spec contract changed with the new trigger.** The summary row
   labels of `RAMP_START_ROWS` name height_event ("stated by (time, depth, speed,
   height_closed_form or height_event)", the requested-height row adds "event: the
   flown coast", the converted-time row adds "(none for height_event)"); they appear
   only in tables that carry the step-3 rows (a run stated by a trigger), which a
   depth, speed or closed-form run now renders with the new labels; no recorded summary
   or pinned output carries them, so output_summary.md does not change
   (`test_height_event.py::test_ramp_start_rows_of_a_height_event_run`). The g_eff
   refusal, now shared by both height methods (`prelude._drag_free_exit_speed`), reads
   "a ramp start by height needs g_eff > 0" instead of "a closed-form height needs
   g_eff > 0" (the step-3 test matches "needs g_eff > 0" and is unchanged).
   `IgnitionSpec` now refuses a height_event spec whose t_ign_s or reference is away
   from the defaults (0.0, "release") or whose trigger_value is not a finite height,
   and `IgnitionSpec.t_ign_abs_s` raises on a height_event spec, which has no time
   before the flight finds it (`test_a_height_event_spec_has_no_time_and_needs_a_push`);
   time-stated and converted specs are unaffected.

Step 6 (2026-10-02, commit 9ca508b on branch sp1-step5):

1. **The margin is a ninth term.** The two runs' dv margins are not assumed zero, so
   -d(dv_margin) is carried explicitly; the kg split divides by the sum of the nine terms
   and adds up to the offload exactly, the convention of `matched_attribution`.
2. **A start-mass guard, stricter than the plan.** Besides the residual, each trace's first
   logged event mass must equal its vehicle's liftoff mass within c1 ln(m0/m_start) <
   closure_tol_mps, because the closure cannot see a mislabelled stage-1 load. Documented
   in docs/physics.md and tested.
3. **Keys start with `xv_`**; the yardstick uses the variant's own release speed (from the
   trace's release state) on the baseline vehicle at P_ref, the convention of
   `compare_planar`; the ratio and the beat flag apply only to stage-1 offloads with a
   head start.
4. **No sim.py helper.** Two pure adapters in compare.py (`evaluation_matched_run`,
   `offload_matched_run`) turn a final evaluation or an `OffloadResult` into a
   `MatchedRun`; fixed cases use `sim.matched_run`.
5. **For step 9:** the gravity term of a single pair mixes the head start's effect with
   that of a stack 41 t lighter at liftoff (higher thrust-to-weight). Only the
   `paired_pad` case of step 7 (the pad with the same offload) separates them; physics.md
   says so.
6. **Noted, not changed:** `_attribution_check`, which the decomposition reuses, takes
   max(abs(...)) over a tuple, so a NaN residual that is not first could be skipped. This
   predates SP1 (KI-024).

The program board carries a one-line summary of each phase's entry and exit criteria, as
the plan's tracking table asks; the full criteria are in the phase files. That is not a
deviation.

## 13. Prompt to start this phase

**The prompt that started this session** is section 10 of the archived handoff,
docs/handoff/archive/2026-09-30-phases-0-2.md. It predates the phase split: it asked for
the headline answer, the settings, and a 2-D scene followed by a 3-D view in one session.
Planning in this session narrowed SP1 to the scope of section 2.

**Resume SP1** (paste into a fresh Claude Code session opened in this folder, if this
session ends before SP1 is complete):

> Read docs/handoff/NEXT_SESSION.md first, then docs/process/SESSION_PROTOCOL.md,
> docs/phases/README.md, docs/phases/SP1-fuel-offload-planar.md, CLAUDE.md, TODO.md,
> README.md, the memory index, and the inputs the phase file links. We are resuming phase
> SP1 of launch-assist-sim: launch settings (silo depth with exit speed, thrust-ramp start
> by depth, speed and height) and the fuel offload at fixed payload on the planar model,
> ending in the findings note docs/findings/RQ1-fuel-offload-2d.md. The step table in
> section 7 of the SP1 phase file shows which steps are done and where the last session
> stopped; the session log in section 11 and any deviations in section 12 say why. Follow
> the session protocol: confirm a clean tree and a green fast suite, re-check the file:line
> inventory in section 6 for the remaining steps against the code as it is now, then show
> me in Plan mode the remaining steps (confirmed or refined) before writing any code. Keep
> the per-step loop (implementer, adversarial reviewers, up to two fix rounds, independent
> gate, commit, tracker update committed at once), run the full suite after steps 4, 5 and
> 6 and before closing, and commit the experiment files before any run. Do not edit shipped
> experiment or vehicle files, and do not start SP2: SP1 ends with its seven exit criteria
> checked, the demo recorded under docs/demos/SP1/, the close-out question put to me, and
> the handoff and prompt for the next phase written. Report results that undercut the
> hypothesis as plainly as the others.
