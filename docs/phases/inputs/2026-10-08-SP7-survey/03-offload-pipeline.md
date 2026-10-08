<!-- Record of SP7 step 0: read-only survey 03-offload-pipeline (the offload solver, the payload search and their reporting), made by a workflow agent on 2026-10-07/08 at HEAD 22c62e9 and saved byte for byte from the workflow journal. Line numbers are for 22c62e9; scratch scripts and paths it names are not in the repository. Not edited; corrections go into the phase file. -->

# SP7 step 0 survey 03: the offload solver, the payload search and their reporting, for a modelled structural dry mass dm(x)

Read-only survey at HEAD 22c62e9 (clean tree, checked before and after every probe). I read offload.py, the offload parts of sim.py, vehicle.py, config.py, results_io.py, compare.py and summary.py, the search path in search.py, and the track prelude. Then I ran six scratch probes that write nothing under results/. Main findings. (a) A factory wrapper that adds a constant 2 t to stage 1's dry mass reproduces SP1's `silo_cold_s1_dry+2t` solve bit for bit (x* = 32,285.203295407457 kg, the same 42 evaluations, the same m_res), so `solve_offload` itself needs no change. (b) Brief 5.5 option (i), as written ("`solve_offload` is unchanged"), is not enough for the pipeline. `OffloadResult.offloaded_vehicle` comes from `OffloadProblem.vehicle_at`, which knows nothing of dm. The pipeline's verification flies a ResolvedRun whose vehicle dict lacks dm. The solve memo keys on run and vehicle dicts only. In a probe, the recorded run assembled on the dm-less vehicle reads `bug_suspect` (closure residual 37.5 m/s, start-mass error -2,000 kg). The same run with dm in the vehicle closes, and its decomposition is explained with `xv_dry_mass_delta_kg` = 2,000 kg. (c) m_res(x, dm(x)) keeps falling as long as dm'(x) > -1/E. E is the measured offload lost per kg of dry mass (4.38 at the headline, 4.58 at +2 t), so the bound is about -0.22 kg/kg, far from what a load-scaled structure plausibly gives (inferred, order 0.01 kg/kg). (d) For `constant_accel` the push's load case is analytic. The flown felt g and interface force equal (a + g_eff)/g0 and m_v (a + g_eff) to 10 digits. A track flight costs about 8 ms against about 0.8 s for one cold evaluation, so a linear motor can fly its push inside the factory. (e) One stage-1 solve costs about 20 s unloaded on this machine without verification. The slow offload tier takes 188 s and pins no headline value.

## 1. offload.py: the problem, the factory contract and the solve

Facts:

- `ProblemFactory = Callable[[Vehicle], RecordingProblem]` (offload.py:85-87). The factory receives a `Vehicle` and nothing else. `OffloadProblem.vehicle_at(x)` = `vehicle.with_offload(self.vehicle, mode, x)`, with `OffloadRangeError` turned into `OffloadInfeasible` (offload.py:197-204). `problem_at(x)` = `self.factory(self.vehicle_at(x))` (offload.py:206-208).
- The vehicle the factory sees carries the vehicle's own payload P0. It never carries P_ref: every evaluation flies `reference_payload_kg` (offload.py:244), and `SearchContext.planner` applies the payload with `with_payload` per evaluation (search.py:593-605). Measured: the factory's vehicle has payload 22,800 kg, the vehicle file's `payload_mass_t` (configs/vehicles/generic_f9_class_2d.yaml:70). P_ref is 26,054.396 kg.
- `planar_problem_factory(ctx)` returns `dataclasses.replace(ctx, vehicle=vehicle)` (offload.py:256-264). Everything else stays: assist model, track, environment, ignition specs, target, settings and budget. The ignition specs were built once for the start vehicle (sim.py:1072, search.py:560). Today they depend on assist and track only, not on masses (phases/prelude.py:201-294), and ramp-start conversions refuse any drive but `constant_accel` (prelude.py:282-288).
- The factory is called in these places: once in `from_factory` for the budget (offload.py:183); once per distinct evaluated x, cached with that x's own WarmStore in `OffloadWarmStore.member` (offload.py:138-147, 237); again, uncached, in `record` (offload.py:253); and in `verify_offload` (offload.py:423). The solver therefore relies on the factory being pure and deterministic.
- `solve_offload` (offload.py:472-567) works as follows:
  - `optimise_gamma(..., find_payload=True)` runs on the OffloadProblem: the gamma* grid at x = 0 (`OFFLOAD_GRID_X_KG`, offload.py:100, 185-190), the search in x at the best grid point (X1, hint 0), the Brent refine, then X2 at gamma*_ref.
  - `final_verify` follows (offload.py:507-509). The search in x is `search.payload_root`, which assumes "fn decreasing in P" (search.py:875). It brackets from the hint with half-widths `payload_half_bracket_t` 2 t, `payload_max_expand` 6 and `payload_backoff_max` 4 (experiments/silo_offload_2d.yaml:39-41), then calls brentq.
  - The search tolerance is `payload_xtol_kg` 0.5 kg (yaml:42). The final xtol is min(`final_payload_xtol_kg`, `final_payload_xtol_kg` / |slope|), with 0.05 kg from yaml:43 (search.py:1574-1584, 1651-1661). A bisection keeps the recorded run's 0 <= m_res < 0.05 kg (search.py:1587-1623, 1673-1682).
- Monotonicity is checked after the fact, on logged evaluations only. `sign_changes` / `nonmonotone_flags` (offload.py:368-399) flag `offload_nonmonotone` for any logged search (X1, X2, final) whose m_res changes sign more than once, or once from < 0 to >= 0, as x grows. Grid points are not logged (`offload_logs`, offload.py:358-365). Measured: 18 logged evaluations against 42 `n_evaluations` for the +2 t solve.
- Verification. Inside `solve_offload` (verify=True, the slow tests' path), `verify_offload` runs `run_search(factory(offloaded))` and passes when |P* - P_ref| <= `search_final_flag_rel` x P_ref = 1e-4 x 26,054.4 = 2.605 kg (offload.py:402-424; yaml `checks.search_final_flag_rel`). The pipeline instead calls `solve_offload(..., verify=False)` (sim.py:1725) and verifies through `run_resolved` of a separate ResolvedRun (section 3).
- Flags, all prefixed `offload:`: the inner search's flags with `ABSCISSA_NOTE` (offload.py:538), `offload_nonmonotone` (offload.py:539), `offload_verify_mismatch` and the verification search's own flags (offload.py:457-469). Statuses are `ok`, `no_offload` and `search_failed` (offload.py:94-99).
- `OffloadResult.offloaded_vehicle` = `problem.vehicle_at(x_star)` (offload.py:540, 559).

Can a wrapper add dm(x) without touching `solve_offload` (brief 5.5 option (i))? For the solve, yes: measured bit for bit (section 6). For the result, no. A wrapper factory `v -> base(add_dry(v, dm(v)))` leaves `vehicle_at`, and so `offloaded_vehicle`, without dm. Probe probe_record.py measured the consequences:

| Recorded run built by `sim.offload_run_result` | Run status | Closure residual | Decomposition | `xv_dry_mass_delta_kg` | Start-mass error |
|---|---|---|---|---|---|
| on `vehicle_at(x)` (no dm) | `bug_suspect` | 37.5 m/s | `bug_suspect`, residual -37.5 m/s | 0.0 | -2,000 kg |
| on `vehicle_at(x)` + dm | `inserted`, checks ok | -5.5e-12 m/s | explained, 9.4e-12 m/s | 2,000.0 | 0.0 |

The closure reads m0 from the vehicle (losses.py:429) and the decomposition reads both vehicles (compare.py:1417-1433, 1490-1503, 1611). The same table holds for a wrapper whose dm varies with x (inferred).

A trap, inferred: if dm were placed in `vehicle_at` and the wrapper also added it, `verify_offload` (offload.py:423) would add dm twice. Exactly one of the two may carry the transform.

What breaks if dm falls as x grows? Probe probe_slopes.py ran cold final-mode evaluations at SP1's gamma*_ref:

| Point | s_x = -dm_res/dx [kg/kg] | s_d = -dm_res/d(dm) [kg/kg] | E = s_d / s_x |
|---|---|---|---|
| headline (x = 41,262.9 kg, dm = 0) | 0.039112 | 0.171342 | 4.381 |
| +2 t row (x = 32,285.2 kg, dm = 2 t) | 0.037212 | 0.170580 | 4.584 |

These match RQ1's secant erosion of 4.49 t/t between 0 and 2 t (docs/findings/RQ1-fuel-offload-2d.md, "Structural penalty rows"). Coupled, dm_res/dx = -s_x (1 + E dm'(x)). So m_res stays strictly decreasing, and the solver's assumption (search.py:875) holds, while dm'(x) > -1/E, that is about -0.228 kg/kg at the headline and -0.218 at +2 t.

Inferred: a structure that scales with the load it carries changes by order dm/M, about 0.01 kg/kg for a few tonnes on a 500-570 t stack. Even all 22.2 t of stage-1 dry mass scaling with stage-1 propellant would give 0.054 kg/kg. What could break monotonicity is a step in dm(x), such as gauge rounding or a discrete switch of material or knockdown. A max() envelope floor gives only a kink, which brentq handles. The nonmonotone check would catch a reversal only where it lands on a logged evaluation.

Also inferred: with a continuous dm the coupled solve (i) and the fixed point (ii) solve the same equation. The fixed point contracts by about |E dm'|, roughly 0.05, so 2 to 3 solves.

## 2. sim.py and vehicle.py: where the penalty row's dry mass goes today

Facts, the chain of the penalty row:

1. `OffloadCaseConfig.stage1_dry_mass_added_t` (config.py:1642; refused together with `paired_pad` at config.py:1659-1664) goes to `_resolve_offload` (config.py:2792-2799).
2. Then `offload_case_start(case, variant, name)` (config.py:2721-2744; `dry = t_to_kg(added)` at 2740-2741).
3. Then `offload_overrides(vehicle_dict, removed, dry, what)`. It restates `vehicle.stages.0.dry_mass_t` as a Quantity with `assumed: true` and the note "an assumed structural penalty, not a sized structure" (config.py:2698-2708, `_restated_quantity` 2652-2668). This happens through `_offloaded` / `_perturb` / `resolve_run` (config.py:2712-2718).
4. The result is `ResolvedOffloadCase.start`, whose vehicle dict carries 24.2 t. Measured: `to_vehicle()` gives exactly 24,200.0 kg, bit-equal to 22,200.0 + 2,000.0.
5. `results_io._solve` calls `sim.solve_resolved_offload(start, mode, P_ref)` (results_io.py:1178). That runs `offload_problem_factory(start)` (sim.py:1708-1714: `start.to_vehicle()`, `planar_setup`, `search_context`, `planar_problem_factory`) and then `solve_offload(factory, start.to_vehicle(), mode, P_ref, verify=False)` (sim.py:1717-1725).
6. So the penalty sits in `OffloadProblem.vehicle` and survives `with_offload`, which changes propellant only (vehicle.py:653-674).
7. After the solve, `offload_solved_run(start, mode, x*)` rebuilds the dict from start's dict. It passes dry 0.0 (config.py:2747-2756), but start's dict already holds 24.2 t. The verification is `run_resolved` of that dict (results_io.py:1183-1194). `offload_run_result(final, res)` assembles the recorded run on `res.offloaded_vehicle` (sim.py:1728-1752). The assumption line `offload_penalty_assumption(added)` is added from the case config (sim.py:1690-1696; results_io.py:1291-1300, 1354).

The pad keeps its vehicle: the paired pad uses `penalty=False` (config.py:2798) and the pad control runs on `base.resolved` (results_io.py:1517). Sensitivity arms and sweep points get the penalty, since `offload_case_start` is called on the perturbed variant or on the point (config.py:2812, 2878).

Vehicle detail available:

- `Stage` has name, `dry_mass_kg`, `propellant_mass_kg`, engine, `n_engines`, startup and coast (vehicle.py:161-172). `Vehicle` has stages, `fairing_mass_kg`, `payload_mass_kg`, `fairing_drop`, `screening_isp_s` and `aero` (vehicle.py:479-497).
- There is no mixture ratio, no LOX/RP-1 split, no tank geometry and no dry-mass breakdown.
- `offload_split_kg` splits by stage only: `both` takes the same fraction of each stage's total (vehicle.py:613-638). `with_stage_propellant` replaces a stage total (vehicle.py:600-604).
- The LOX/RP-1 split exists only as text in the vehicle file's source string (generic_f9_class_2d.yaml:47: 287.4 LOX + 123.5 RP-1). It is also in the experiment's offload `energy.fuel_mass_t` (experiments/silo_offload_2d.yaml:205-207; `OffloadEnergyConfig`, config.py:1681-1711), which only `compare.offload_energy` uses at the baseline vehicle's mixture ratio (results_io.py:1430-1438; compare.py:1674-1736).
- `sim.OFFLOAD_ASSUMPTIONS` states that "each stage keeps its mixture ratio" (sim.py:1680-1685).
- The body diameter enters only through `aero.reference_area_m2` 10.52 m^2 (generic_f9_class_2d.yaml:84).
- Every config model refuses unknown keys (`extra="forbid"`, config.py:219-222), so a vehicle file cannot carry a structure block without a schema change.

## 3. Reporting: the post-pass, the memos and where structural rows would go

Facts:

- `planar_offload` (results_io.py:1687-1807) runs in this order:
  - pad controls per solved mode (`_pad_control`, 1496-1560: solve on `base.resolved`, verified, recorded run `<baseline>__offload_<mode>`);
  - the cases (`_offload_case`, 1303-1390);
  - the sensitivity arms (1759-1790): each against the pad under the same perturbation, P_ref that pad's P*, `verify=False` (1778);
  - the record, with `energy_inputs` and the caveats (1795-1806; caveats from `summary.offload_caveats` at 1798).
- `_offload_case`, for a solve, runs `_solve` → `offload_solved_run` → `_verified` (`ctx.run(final)`, i.e. `sim.run_resolved`) → `sim.offload_run_result`. It then runs the decomposition `offload_matched_run(start.name, res, ...)` on `res.offloaded_vehicle` (compare.py:1400-1414), the paired pad (1366-1388) and the record (`_case_record`, 1393-1493).
- Penalty keys today: `stage1_dry_mass_added_kg` and `assumed_penalty`, both read from the case config (results_io.py:1462-1467).
- Memo collision risk. `_solve` keys its memo on `(trajectory_key(start), P_ref, mode)` (results_io.py:1174-1177). `trajectory_key` hashes the run and vehicle dicts only (compare.py:1768-1783). `_run_memo` keys on the same thing (results_io.py:1118-1138). Measured: the headline start's key equals the variant `silo_cold`'s key. A structural case `of: silo_cold, solve: stage1` whose switch lives outside those dicts would silently reuse `silo_cold_s1`'s unstructured solve. Its verification would fly the dm-less vehicle unless dm(x*) is written into `final`'s dict.
- `compare.cross_vehicle_decomposition` already reports `xv_dry_mass_delta_kg` = total dry mass variant - pad, read from the two vehicles (compare.py:1417-1433, 1611). No summary row prints it (`OFFLOAD_CASE_ROWS`, summary.py:1802-1861; `offload_decomposition_table`, 1951-1985).
- `summary.offload_section` (summary.py:2074-2118) prints the basis, the caveats (`OFFLOAD_CAVEATS`, block-level, with the structural sentence at 1680-1682 and the drive sentence at 1683-1685), the cases table with the assumed dry-mass row (1820-1824), energy, decomposition, pad controls, sensitivity and notes.
- The metrics.json `offload` record is `report.record` plus `runs` (`offload_record`, results_io.py:1902-1908), appended last in metrics.json (results_io.py:682-683).
- `resolved_config.yaml` writes run dicts and vehicle dicts (with `offload_runs`), never the offload block's case configs (results_io.py:590-622). A new optional field on `OffloadCaseConfig` therefore enters no resolved dict. The planar output capture's fast experiment has no offload block (tests/test_planar_pipeline.py:1146-1164, "no offload key").
- Sweep-point solves write `OFFLOAD_SWEEP_COLUMNS` into sweep_index.csv. The precedent is to append new columns, as KI-028 did (results_io.py:1841-1874).

Recommendations, by place:

- metrics.json case record. Next to the penalty keys (results_io.py:1462-1467) add: model id, coefficient set, sizing basis (flown or full_load), dm at x*, dm at x = 0, the per-element breakdown, the load case used (felt g, interface force, stage-1 propellant on board, payload) and the structure file's provenance. Plus a block-level `structure_inputs` beside `energy_inputs` (results_io.py:1799).
- summary.md. New rows after summary.py:1824, plus a printed `xv_dry_mass_delta_kg` row as the visible check that the flown vehicle carried dm. A "Structure" subsection for the band: one row per coefficient set (dm at x*, x*, % of stage 1), the full-load-sizing bound row and the penalty rows beside it.
- Caveats. Word them per case rather than per block (some cases charged, some penalty rows, some neither).
- Arms. A dm column in `_offload_arm_record` (results_io.py:1593-1631).
- Sweeps. Appended sweep columns.
- Assumption line. `_offload_assumptions` (results_io.py:1291-1300) must receive the solved dm, so its signature changes.

## 4. The payload-capacity path (P* of a variant with structure)

Facts:

- A variant is a run dict merged over the baseline and resolved against the experiment's single vehicle dict (config.py:2851-2857). Variants carry no vehicle overrides (inferred from 2857).
- Vehicle overrides exist only in these places:
  - sweep axes (config.py:2865-2869);
  - sensitivity (2883-2895);
  - bounds (`BoundConfig`, config.py:1488-1497). These perturb the paired baseline too, which is the wrong semantics for structure on the assisted run only (D-SP1-03).
  - calibration cases (config.py:1500-1521), which are never compared.
- `run_resolved` → `run_planar(resolved.run, resolved.to_vehicle())` → `run_search(search_context(...))` (sim.py:876-880, 1512-1541). The payload search varies P on a fixed vehicle (`with_payload`, search.py:593-605; `run_search`, 1780-1834).
- Many consumers call `resolved.to_vehicle()` directly: `matched_run` (sim.py:1617), `rerun_planar` (sim.py:1566), `offload_problem_factory` (sim.py:1712), `offload_case_start` (config.py:2731) and `_case_record` (results_io.py:1414).
- An offload `fixed` case flies its start and reports its own P* against P_ref (results_io.py:1348-1352). Its offload must be > 0 (config.py:1574-1578).

Recommendations:

- Put the modelled dm into the derived run's vehicle dict as a restated Quantity with a note naming the model and the set. That is the existing `offload_overrides(dict, [0, 0], dm, what)` path (config.py:2698-2708). Do it for a new kind of block entry in the new experiment only, for example a "payload case" of the offload block, or a structure block naming variants. Every `to_vehicle()` consumer and the trajectory-key memos then see dm, and no shipped resolved dict changes.
- Avoid a run-dict switch that `run_planar` interprets. It would have to be repeated at each `to_vehicle()` call site above.
- dm depends weakly on P (only through the stack above the stage-1 tanks; inferred). Size it at a stated payload (P_ref is recommended over the file's P0 of 22.8 t), or take one fixed-point step at P*. Report d(dm)/dP from the sizing model alone.
- For `constant_accel` the full-load load case is analytic (section 5), so dm can be computed before any flight. A linear motor needs a pre-pass that flies the push (section 5).

## 5. What `problem_at(x)` can know before the ascent, and what it costs

Facts:

- Inside a factory wrapper the following are available:
  - the offloaded vehicle at P0, with stage-1 propellant m_p1 - x (measured 369,637.09 kg at x*) and dry 22,200 kg;
  - whatever the wrapper closes over: the base `SearchContext` with `assist` (for `constant_accel`: `net_accel_mps2`, `carriage_mass_kg`, `f_imp`), `track` (L, phi), `env.g_ref_mps2` (9.772091717511234 m/s^2 on the gate site) and the ignition specs;
  - P_ref, if the wrapper is given it.
- Not available: the per-tank split (section 2).
- `constant_accel`, cold start:
  - felt g = (a + g_eff sin phi)/g0;
  - F_int = m_v (a + g_eff sin phi) - T (constant_accel.py:137, 143).
- Measured on the flown push at x* and P_ref:
  - felt g flown = analytic = 3.9964760359 g0 (min = max over the push);
  - peak interface force flown = analytic = 20,814,559.761591 N. This matches RQ1's 20.81 MN and metrics.json `vs_pad.peak_interface_force_N`.
- Hot start (inferred from constant_accel.py:137-143): felt g stays a + g_eff sin phi, F_int falls by T(t), and stage-1 propellant falls by the mass burned on the hold and track. The load case is still computable from the ignition spec's schedule without the ascent.
- A linear motor must fly the push: F = min(F_max, P_max / sdot) depends on M, and so on dm itself. That is a small inner fixed point dm = S(push(M + dm)), contracting since dS/dM is small (inferred).
- The public, standalone way to fly only the push is `ctx.planner(P, mode).start(ctx.assist, ctx.track)`. It returns a `FlightStart` whose `prefix.assist_phases()` holds the track states (phases/planar.py:826-837, 907-942; `fly_track`, prelude.py:774-922). Per-instant forces come from `assist.state_rate(...)` (assist/base.py:69-85).
- Inferred, an S4 point: `fly_track` resolves a release-referenced ignition against `assist.push_time_estimate(track)`, which takes no mass (prelude.py:823-831). For a force-limited drive that estimate cannot follow the vehicle the factory hands it.

Measured wall times (probe time_track.py, this machine, unloaded, shipped budget):

| Operation | Time |
|---|---|
| `load_experiment` with preflight | 0.18 s |
| `offload_problem_factory` | 0.6 ms |
| `problem_at(x*)` (factory call, nothing flown) | 24 us |
| track flight alone (`planner.start`), final or search mode | 7.5-7.9 ms (628 RHS calls, one assist phase) |
| one assisted ascent at P_ref, final mode, cold (track, kick, delta solve 14 flights, LTG 10 shots) | 0.82 s |
| same, warm store (kick cached) | 0.14 s |
| same, search mode, cold | 0.61 s |
| recorded run (dense output) | 0.094 s |
| `OffloadProblem.evaluate(x*)`, cold | 0.78 s |
| full stage-1 solve, shipped budget, without verification (42 evaluations) | 20.0-20.8 s (probe_solve_2t.py) |

SP1's recorded costs, taken under three concurrent commands: 87-89 s per solve with verification at the shipped budget, 92-109 s at the test budget, a pad control about 30 s (docs/physics.md:2192-2198). The run command took 14.1 min and the sweep 20.9 min (docs/physics.md:6126-6131). A pad payload search alone took 9.3 s and silo_cold 12.7 s (physics.md:2848-2855).

Inferred: the push is about 1% of one cold evaluation. A solve calls the factory roughly once per distinct x, about 20 times. Flying the push in the factory, even a few times for an inner fixed point, therefore adds well under a second per solve.

## 6. The constant-2 t cross-check (brief 5.5)

Facts, measured with probe_solve_2t.py at SP1's recorded P_ref 26,054.396243494975 kg, shipped budget, `verify=False`:

| Path | x* [kg] | − SP1's recorded 32,285.203295407457 | Evaluations | m_res at x* [kg] | `offloaded_vehicle` stage-1 dry |
|---|---|---|---|---|---|
| (a) SP1's own path: `sim.solve_resolved_offload` of `silo_cold_s1_dry+2t`'s start | 32,285.203295407457 | 0 (bit-identical) | 42 | 3.49311922036577e-05 | 24,200 kg |
| (b) factory wrapper adding 2,000.0 kg on the no-penalty start | 32,285.203295407457 | 0 (bit-identical) | 42 | 3.49311922036577e-05 | 22,200 kg (no dm) |

The 18 logged evaluations of (a) and (b) are identical, and m_res equals the recorded `solve.m_res_kg`. This works because the vehicle at every x is bit-identical: 24,200.0 kg either way, and the propellant is the same.

A single cold evaluation is not the comparison. It gives m_res 3.15e-5 kg at x*, against the solve's warm-started 3.49e-5 kg. The figure depends on the warm-store history, so bit identity requires the whole solve sequence.

So the solver-level cross-check is byte-level. It stays byte-level end to end only if:

- the model's constant arrives as exactly 2000.0 kg (not 1999.9999999999998 from a unit chain);
- P_ref re-solves to the same bits (SP2's step A4 reproduced SP1's P_ref and headline to 0.000 kg; phase file section 4, item 3);
- `offloaded_vehicle` and the verification dict carry dm (sections 1 and 3).

SP1's tolerance is "about 3.8 kg against a re-solved P_ref". It breaks down as 1.3 kg from P_ref's tolerance, 0.25 kg, and the gamma* allowance at its 2.30 kg cap, needed because the validation measurement's gamma*_ref was on record only to 0.01 deg (docs/phases/inputs/2026-10-03-sp1-preregistration.md:44-49, 110-117). RQ1's Headline table records the headline reproduced to +0.00004 kg "against about 3.8 kg of resolution" (RQ1-fuel-offload-2d.md:155; reading at 729). The app uses `REPRODUCTION_TOL_KG` = 0.002 kg (app.py:1542).

Recommendation: gate the cross-check on bit identity, or at most 0.002 kg, of x* and of the verification's P*, not 3.8 kg. Same code, budget and P_ref give the same bits, and 3.8 kg would hide a coupling bug of several hundred grams of offload. Run it through the whole pipeline (`planar_offload` with a structural case whose model returns 2 t) and compare the full case record with SP1's row. A slow test costs about 20 s for the solve plus about 13 s for the verification search, plus a pad P* search (inferred from the timings above).

## 7. The slow tests that pin the offload solver

Facts:

- tests/test_offload.py:725-879 runs on the gate fork through `GATE_EXPERIMENT` = experiments/silo_screening_2d.yaml, not silo_offload_2d.yaml (tests/test_offload.py:145). It uses `TEST_SEARCH_RTOL` = 1e-9 (147) and `VERIFY_GAP_GUARD_XTOLS` = 2.0 (150).
- The module fixture `gate` (770-776) runs the pad's P* search, the stage-1 pad control and silo_cold's stage-1 solve with verification.
- `test_gate_silo_offload_recorded_run_and_verification` (794-826) asserts:
  - status ok and 0 < x* < load;
  - the recorded run inserted with 0 <= m_res < xtol;
  - release mass = full - x*;
  - verification within tolerance and within 2 x `final_payload_xtol_kg`;
  - no nonmonotone or mismatch flag.

  It does not pin x* to 41,262.9 kg ("a validation measurement only", 804-805). No test in the repository pins SP1's headline or penalty-row x*. The app's `SP1_HEADLINE` (app.py:1420-1437) is a display record, checked against the findings note's text (tests/test_app_server.py:3049-3060), not re-solved.
- `test_gate_pad_control_is_within_the_bound` (829-857).
- `test_gate_offload_converges_under_a_tightened_budget` (860-879): the shipped and 10x-tightened chains without verification, |dx*| <= 1e-3 x*.

Measured (`uv run pytest -q -p no:cacheprovider tests/test_offload.py -m slow --durations=0`, this machine, nothing else heavy running): 3 passed in 187.7 s. The `gate` fixture setup took 72.85 s, the convergence test 114.57 s, and the two gate assertions under 5 ms each.

Recommendation: exit criterion 3 (SP1's headline with the structural model off) needs a new slow pin. One option is a pipeline run of `silo_cold_s1` from silo_offload_2d.yaml against 41,262.90803733282 kg at <= 0.002 kg, about 35-45 s with verification (inferred). A second option is to extend tests/data/silo_screening_2d_record.json with an offload record.

## 8. Recommendations for the design (not facts)

1. Coupling. Give `OffloadProblem` / `solve_offload` one optional vehicle transform, for example `structure: Callable[[Vehicle, float], Vehicle] | None = None`, taking the vehicle and P_ref and applied inside `vehicle_at`. The factory stays plain. With None, every line of SP1's path is unchanged.
   - Then `offloaded_vehicle`, `record`, `problem_at` and `verify_offload` all see the same dm with no double application.
   - This is about five lines in offload.py, against brief 5.5's "`solve_offload` unchanged". The alternative is a factory wrapper plus re-applying the transform at sim.py:1737 and compare.py:1410-1413 and in `offload_solved_run`. That spreads one rule over four places and leaves `OffloadResult.offloaded_vehicle` misdescribed.
2. The pipeline must write dm(x*) into `final`'s vehicle dict, through a dry-mass argument on `offload_solved_run` (config.py:2747-2756, today hard-coded 0.0). The verification and the recorded run then fly the same vehicle, `trajectory_key` separates them, and resolved_config.yaml records the charged mass. The note must say "modelled by <model>, set <name>", never "assumed".
3. Put the structural switch (model, set, sizing basis) in the solve memo key (results_io.py:1174) or in a dict the key hashes, so it cannot collide with an unstructured case on the same variant (measured: the keys collide today).
4. Refuse `stage1_dry_mass_added_t` together with a structural switch, and `paired_pad` with structure, for the reason config.py:1659-1664 gives.
5. Make dm(x) continuous: no gauge rounding, envelope by max(). Assert dm'(x) > -1/E in a test from the sizing model alone. E is about 4.4-4.6, so the bound is about -0.22 kg/kg. Keep `offload_nonmonotone` as the in-run check. Option (ii), the fixed point, stays the fallback and needs no solver change.
6. Size with the stack that flies P_ref, not the factory's P0 (22.8 t vs 26.05 t). The factory never sees P_ref, so the transform must receive it.
7. The structure model needs a sourced LOX/RP-1 split and tank geometry in its own structure file. The vehicle model has neither, and the energy block's split is an offload-block input, not a vehicle property. A loader beside `load_vehicle` should read the file (cli.py:330-352; config.py does no I/O), and its content should be recorded in the run's outputs. `preregistration_state` covers configs/ (results_io.py:447) but runs only for calibration-labelled experiments (results_io.py:849-850).
8. The band as three cases (low, central, high) plus a full-load bound case fits the existing one-column-per-case table and arms machinery. A small summary subsection collects them into the band.

## 9. Probe scripts and outputs (scratch only; nothing written in the repository)

All under C:/Users/rahul/AppData/Local/Temp/claude/D--DEV-ClaudeProjects-SpaceRocketOptimization/3e237173-2609-4e7b-ac46-15c1a393670f/scratchpad/a0/03-offload-pipeline/:

| Script | What it did | Output file |
|---|---|---|
| read_record.py | SP1's recorded case figures | (none) |
| time_track.py | timings and the analytic-vs-flown load case | time_track.out.txt |
| check_dry.py | dry-mass bit equality and memo keys | (none) |
| probe_record.py | recorded run and decomposition with and without dm | probe_record.out.txt |
| probe_solve_2t.py | the two full solves of section 6 | probe_solve_2t.out.txt |
| probe_slopes.py | E and the monotonicity bound | probe_slopes.out.txt |
| (pytest run) | the slow tier timing | slow_offload_tests.out.txt |

`git status --short` was empty after every run. REPORT.md was not written to the scratch directory: the harness refused report files for this subagent, so this message is the only copy of the report.
