<!-- Record of SP7 step 0: independent adversarial review (numerics-code) of design draft v1 (draft-v1.md in this folder), made by a workflow agent on 2026-10-08 at HEAD 22c62e9 and rendered from its structured output. The disposition of every finding is appendix A of ../2026-10-08-SP7-design.md. Not edited. -->

# Review: numerics-code

Numerics and code feasibility: the coupling seam mostly holds against the code at 22c62e9. An optional transform in OffloadProblem.vehicle_at (offload.py 197-208) is seen by problem_at, record, offloaded_vehicle and verify_offload, and leaves SP1's path unchanged when it is None. Restating dm(x*) through offload_solved_run gives the verification its own trajectory_key. The perturbed pad of an arm comes back from ctx.run(arm.pad) as a full RunResult with its time series, so its envelope is available. A sweep can solve a structural case at every point against the experiment pad, and one sweep can name three set cases.

The design still fails as written in several places:
- **1-D golden tier (blocker).** It adds a dataclass field (work_other) to AssistEnergyBudget, and the 1-D golden tier dumps every field of that dataclass and compares key lists. That tier cannot be recaptured.
- **Corner search (blocker).** It is infeasible as costed: about 22 coefficients, so 2^22 envelopes at about 1.5 s each, measured on the probe. The probe's own table also shows an interior maximum in p_u, so "the bounds of the stated ranges" is a false label and the high-mass set can understate the worst case.
- **Payload two-pass check.** It fires on every case: the expected first correction is about 1 kg against a 0.05 kg threshold, which is also the search's own resolution.
- **Pending ignition.** A release-referenced ignition resolved at the real release fails every planar linear-motor run unless planar.py or fly_track changes. It must also be gated by drive, or every constant_accel run's ignition time moves.
- **Rise-time DLF rule for constant_accel.** Its claimed under-1% ramp cost fails at short strokes. At 50 m the ramp costs +6% to +17% of net acceleration (computed), so dm is understated there.
- **Sweep records.** A sweep has no on-disk home for its structural records, which live only in OFFLOAD_SWEEP_COLUMNS.
- **Smaller items.** Mis-cited inner contraction, per-solve cost, dm(x) smoothness, x-invariant geometry, the hard-coded "assumed" provenance, the ramp_end event name, the division by zero at sdot = 0, and arm records without dm.

## N1 [blocker] (4.1, 4.8, D-SP7-22, S5) favours_assist=False

Issue: The design adds `AssistEnergyBudget.work_other` (default 0.0) and calls it safe because the residual stays bit-identical. But the 1-D golden tier dumps the AssistEnergyBudget object through `dataclasses.fields`, and compare_tree requires the dict keys to match exactly and in order. Every existing 1-D track run would gain the key `work_other` and fail test_objects_match_golden. That test is in the tolerant tier, so it runs in any environment, not only the exact one. The golden data cannot be recaptured, so step S5 can never pass its own standing gate.

Evidence: src/launchsim/losses.py:98-127 (five fields); tests/golden_1d_support.py:388-396 (plain() walks dataclasses.fields), 424-435 (result_objects dumps assist_budget), 599-613 ("keys differ (missing/extra)"); tests/data/golden/silo_screening_1d/experiment/objects.json:393-399 (assist_budget with exactly work_drive, work_thrust, delta_mech, massflow_term, dissipated; 48 such entries); tests/test_golden_1d.py:166-174

Recommendation: Leave AssistEnergyBudget's field list unchanged. Carry the piston work only on sealed-shaft runs, for example as a subclass instance built only when the shaft is sealed, or as a separate record or metric key that the golden dump does not see. Add a fast test that `dataclasses.fields(AssistEnergyBudget)` is still the five names. Re-check the same issue for any other dataclass that the golden plain() dump reaches (Status, LossBudget, SensitivityRow, the comparison objects).

## N2 [blocker] (4.2.5, D-SP7-15, S2) favours_assist=True

Issue: The design asks for an exhaustive search of 2^k coefficient corners, in seconds. It lists about 22 coefficients: E, nu, rho_w, F_tu, eta_w, FS_u, p_u,LOX, p_u,RP1, p_u,min, s_dg, k_s, (C, n), NOF, t_min, L_s, a/b, k_entry, k_ts, f, two densities, the ullage fraction. The envelope depends on the coefficients, so every corner must recompute it over all pad samples. That makes 2^21 to 2^23 envelope evaluations: weeks, not seconds. The corners are also not the extremes. S08 measured an interior maximum in p_u for the stiffened-3x form: 1,932 / 1,972 / 1,804 kg at 2.5 / 3.5 / 4.5 bar. So the max and min over the box need not sit at a corner. Calling the band 'the bounds of the stated coefficient ranges, all at once' would then be false. The high-mass set could understate the worst case, which favours the assist. Constrained pairs (p_u,min <= p_u) also make some corners infeasible, and k_ts does not affect the central (aft_ring) dm at all.

Evidence: Measured with the S08 probe (review/numerics-code/time_probe.py, time_push.py, time_samples.py): an envelope for a new coefficient set takes 1.36-1.46 s; size_case over 618 pad samples takes 1.68 s; at 0.128 s per evaluation with the envelope cached, 2^24 corners take about 595 h, 2^20 about 37 h, 2^16 about 2.3 h. S08 section 7, table 'Buckling form x ullage pressure' (stiffened 3x row) and its note that the direction of p_u's effect flips.

Recommendation: (1) Screen first with the tornado. Keep only the coefficients that move dm at the headline by more than a stated threshold, say 10 kg. Run the exhaustive corners on that subset, k <= 10-12, which takes minutes to hours, or vectorise over corners. (2) Scan each kept coefficient's range on 5-7 interior points; where dm is not monotone, take the interior extreme instead of an end. (3) Or find the max and min with a bounded global optimiser that has a stated seed and budget, and report its result next to the corners. (4) Respect the coefficient constraints, and fix k_ts at its own extremes for the thrust-structure row. (5) Label the band by the method actually used, for example 'the largest and smallest dm found by <method> over the stated ranges', and record the method in the structure file with the frozen sets.

## N3 [major] (4.2.5, 4.10 (A rows, sweeps; B), 6.4, 6.6) favours_assist=True

Issue: The low-mass and high-mass sets are frozen as the extremes at SP1's headline push only: constant_accel at 3 g0, 100 m, x = 41.26 t, central DLF and entry. They are then reused for the stroke sweep, which runs at 7.0, 4.0, 2.5 and 2.0 g0 felt, and for the band language of other cases. S08 shows that the governing element and mode, and the sign of a coefficient's effect, change with the buckling form and the load level. A set that is extreme at 4 g0 need not be extreme at 7 g0 or 2 g0, under the step DLF, or under a linear-motor push. So the band at those points is not a bound, and it may understate the worst case there.

Evidence: S08 section 7: the dominant element shifts between forms; the p_u direction flips. S08 section 3: n_peak per DLF. Design 4.10: three sweeps 'with the central, the low-mass and the high-mass structure'. Design 4.4: the band line in the summary.

Recommendation: Either (a) run the sizing-only extreme search (N2's method) at each pre-registered case's expected push, as part of S2 or S6 and before any flight, and freeze per-case sets; or (b) keep the headline's sets but label every off-headline band 'the headline's coefficient sets, not the bounds at this point'. In case (b), also pre-register a sizing-only check of how far the headline sets fall short of the true extremes at each sweep point and each drive case.

## N4 [major] (4.4 (payload form)) favours_assist=False

Issue: The payload form's convergence check, |P_2* - P_1*| with a flag above 0.05 kg, is mis-specified. It measures the second pass's correction, not the error left after it. The expected correction is about |dP*/d(dm)| x |d(dm)/dP| x (P_1* - P_ref) ≈ 0.184 x 0.008 x ~800 kg ≈ 1.2 kg (0.5-2 kg over the probe's range), so the flag fires on every structural payload case. The error left after two passes is about the contraction (≈0.0015) times that, about 0.002 kg. A 0.05 kg threshold on the difference of two independent payload searches also sits at the search's own resolution (final_payload_xtol_kg 0.05 kg, the bisection 0 <= m_res < 0.05 kg), so even a correct check at that level would flag at random.

Evidence: S08 section 7, last bullet: dm 2,904 kg on the recorded silo_cold push at P* 27,553 kg against 2,892 kg at P_ref 26,054 kg, so d(dm)/dP ≈ 0.008 kg/kg (0.003-0.008 by form), plus k_entry x 4 g0 ≈ 0.002. Brief 5.1: 184 kg of payload per t of stage-1 dry mass. experiments/silo_offload_2d.yaml:43 (final_payload_xtol_kg 0.05); search.py:1587-1623 (the bisection band).

Recommendation: Compute the contraction from the two passes: c = |(P_2* - P_1*)/(dm_1 - dm_0)| x |(dm_1 - dm_0)/(P_1* - P_ref)|. Report c and the estimated remaining error c|P_2* - P_1*|. Flag when that estimate exceeds a stated fraction of final_payload_xtol_kg, or when c > 0.1. Alternatively, test convergence on dm (|dm_2 - dm_1| below 0.05 kg / 0.184, about 0.27 kg) with a third sizing, not a third search. Record dm_0, dm_1, P_1*, P_2* and c.

## N5 [major] (4.6 (pending release-referenced ignition), 4.1 file table, S4) favours_assist=False

Issue: (a) The design resolves a release-referenced ignition with t_ign_s >= 0 at the real release, 'pending through the unlit push', the way lights_at_height works. The planar planner has no such path. start_track reads tr.t_ign_abs_s, which would be None, and passes t_ign = None and ign_alt = None. FlightStart.stage1_lights is then False, and SearchContext._kick raises PreludeFailure('ignition'). Every planar linear-motor run with a release-referenced ignition would therefore fail. phases/planar.py is missing from the 4.1 file table and from the S4 and S4a file lists. (b) The pending path must be gated by drive. Today constant_accel resolves t_ign = t_push_est + t_ign_s from the closed-form push time, not from the track_end event root. Switching it to the root would move every silo_cold-type run's ignition by a rounding-level amount and break the exact golden tier, the planar digest pin and the output capture. (c) Section 4.1 lists a 'mass-aware push time' protocol member, while 4.6 says no closed-form push time is needed in the run path. The two are inconsistent.

Evidence: src/launchsim/phases/planar.py:938-942 (t_ign from tr.t_ign_abs_s, ign_alt only for lights_at_height), :581-584 (stage1_lights), src/launchsim/search.py:615-616 (PreludeFailure 'ignition'); src/launchsim/phases/prelude.py:823-831 (t_ign from push_time_estimate for reference release), 871 (push_cap from the estimate); src/launchsim/phases/vertical.py:384-388 (the 1-D planner already falls back to spec.t_ign_abs_s(tr.t_release_s) when no time is written).

Recommendation: Add a protocol member such as `push_time_exact: bool`: True for constant_accel, which keeps today's code path byte-identical, and False for linear_motor. When it is False and the reference is release with t_ign_s >= 0, write tr.t_ign_abs_s[stage0] = exit_.t_release_s + spec.t_ign_s in fly_track after the exit, so that both planners read it unchanged. Skip flag_ignored_ignition_settings for this kind of pending ignition. Add planar and 1-D tests for t_ign_s = 0 and t_ign_s = 0.5. Drop 'mass-aware push time' from 4.1, or define it as step-cap-only.

## N6 [major] (D-SP7-12, 4.2.1, 4.10 A sweeps) favours_assist=True

Issue: For constant_accel, the trajectory flies a step, but the structure is charged DLF = 1 + T/(pi t_r) <= 1.10, from a rule rise time t_r = 10 T_low/pi that the trajectory never flies. The design justifies this by 'the rule keeps the ramp's own cost under 1% of F_max'. That holds only for strokes of 100 m or more, and only if f_low >= ~3 Hz. A drive with that rise time reaching the same (L, v_e) needs a higher peak acceleration. At the 50 m sweep point the ramp costs +6.2% (f_low 3 Hz) to +17% (f_low 2 Hz) of the net acceleration, felt 7.0 → 7.37-8.0 g0, with t_r/T_push = 0.81-1.22. At 100 m with f_low = 2 Hz it costs +3.3%. The short-stroke points, and the headline itself if S0 sets f_low low, are therefore charged below what any real drive with that rise time would load.

Evidence: Computed in review/numerics-code/ramp_cost.py (a linear net-acceleration ramp over t_r, then constant, hitting v_e = 76.70717 m/s at L). f_low 3 Hz (t_r 1.061 s): 50 m +6.2%, 100 m +1.4%, 200 m +0.3%. f_low 2 Hz (t_r 1.592 s): 50 m +17.0%, 100 m +3.3%. f_low 5 Hz: 50 m +2.1%, 100 m +0.5%.

Recommendation: For constant_accel under `rise_time`, charge n_peak from the ramped profile that reaches the same (L, v_e): its quasi-static peak a_max from the closed form above, times the ramp DLF. Alternatively refuse `rise_time` when t_r/T_push exceeds a stated bound (e.g. 0.25) and charge the step. Record the ramp's own cost (a_max/a_step - 1) for every case and sweep point, not only for the linear-motor runs. State in the pre-registration how the result depends on f_low.

## N7 [major] (4.4 Records, 4.10 sweeps, 6.6) favours_assist=False

Issue: A sweep point's offload solve is recorded only in sweep_index.csv's OFFLOAD_SWEEP_COLUMNS. The code's own docstring calls these columns 'its solve's only record on disk': no run directory and no metrics.json offload record exist per point. The design specifies structure_* keys only in the per-case metrics.json record. The depth sweep's dm, n_peak, DLF, F_peak, set, governing element and flags would therefore not reach disk, and exit criterion 6 could not be checked from the results.

Evidence: src/launchsim/results_io.py:1841-1874 (OFFLOAD_SWEEP_COLUMNS and its docstring), 1877-1899 (offload_index_values); the run_sweep path appends the records to the index frame only (results_io.py ~2239-2245).

Recommendation: Add a conditional column group, for example OFFLOAD_STRUCTURE_SWEEP_COLUMNS (set, sizing, dynamic, entry, dm_kg, dm_x0_kg, dlf, n_peak_g, F_peak_N, upper_stack_exceeded, release_unload, ramp cost). Append it, KI-028 style, only when a sweep names a structural case, so that SP1-type sweep indexes keep their columns. Have the sweep summary print it.

## N8 [minor] (4.10 A (variants, sweeps), budget) favours_assist=False

Issue: Experiment A lists only the variant silo_cold, which has net_accel_g 3. A stroke axis on it changes the exit speed, and exit_speed_mps cannot be added through an axis next to net_accel_g. The fixed-exit-speed sweep therefore needs an exit_speed_mps variant like silo_cold_200m. Running 'three sweeps' with the same axes would also re-fly the four point payload searches three times. The sweep validator checks case names only, and resolve rebuilds each named case on the point, so one sweep of the exit-speed variant can name all three set cases.

Evidence: experiments/silo_offload_2d.yaml:103-108 (silo_cold_200m with exit_speed_mps), 135 (sweep 2); src/launchsim/config.py:2075-2091 (the name checks), 2875-2880 (the case rebuilt on the point).

Recommendation: Add the exit-speed variant to A. Use one sweep that names the three structural set cases: 4 point runs and 12 verified solves instead of 12 point runs. Re-cost the sweep command accordingly.

## N9 [minor] (4.4, D-SP7-16, section 1) favours_assist=False

Issue: The inner dm fixed point has five problems. (1) 'Contraction about 0.05, S03' mis-cites S03: 0.05 is option (ii)'s outer contraction |E dm'|. The inner contraction runs through F_int (k_entry and the skirt), about 0.002-0.004 for constant_accel, and through n, about -0.007, for a fixed-limit motor. (2) Nothing flags when the six-iteration cap is hit before the 1e-6 kg tolerance. (3) Stopping on a tolerance makes the iteration count, and so the last digits of dm, switch at points in x. (4) The transform must never warm-start from another x's dm. OffloadWarmStore caches problems per x and record() rebuilds them uncached, so S03's 'pure and deterministic factory' requirement extends to vehicle_at. (5) Section 1 says a vehicle_at transform 'reproduces SP1's +2 t row bit for bit (S03)'. S03 measured a factory wrapper (path b) and only inferred the vehicle_at form.

Evidence: S03 sections 1 and 8 (0.05 is |E dm'| of option ii; the factory must be pure), S03 section 6 path (b); src/launchsim/offload.py:138-147 (member cache by x), 206-208 (problem_at), 248-253 (record calls problem_at uncached), 540 (offloaded = vehicle_at(x*)).

Recommendation: Always start from dm = 0 (or a fixed first sizing). Either use a fixed iteration count or keep the tolerance but record the iterations and residual, and flag when the cap is hit. Add a test that vehicle_at(x) is bit-identical across call orders and repeated calls. Quote the inner contraction from the sizing model. Make the S3 slow cross-check the first measurement of the vehicle_at form, and say so.

## N10 [minor] (4.4, 4.10 budget, section 9 corrections) favours_assist=False

Issue: The budget rests on S09's assumption that 'the structural sizing ... adds nothing measurable'. The design instead flies the push and re-sizes up to six times on every vehicle_at call, using 'every push sample and event'. The probe sizes a 54-sample push in about 0.10 s, and S03 measured a track flight at 8 ms. That is about 0.5-0.65 s per vehicle_at call, times about 40-45 distinct x plus record and offloaded: about 20-30 s per structural solve, comparable to an unloaded solve itself (about 20 s without verification). Experiment A has about 16 structural solves (10 cases and 6 effective arms), the sweep 12 and experiment B 6, so the commands run roughly 5-8 min longer each than the 18/12/12 min stated. The pessimistic case approaches D-SP1-17's trim threshold.

Evidence: Probe timings (review/numerics-code/time_samples.py): size_case with 54 push samples 102 ms, with 1 sample 20 ms. S03 section 5: track flight 7.5-7.9 ms, stage-1 solve 20-20.8 s. S09 section 3.2: the assumption at line 303.

Recommendation: For constant_accel, size from the analytic load case: n and F_int are constant, so no re-flight is needed. For a flown push, reduce the samples to the governing candidates (maximum n, maximum F_int, maximum liquid head per tank, and the events) before sizing. Re-cost the budget with the measured per-call cost, and recompute the envelope once per coefficient set, not once per case.

## N11 [minor] (4.2 (monocoque root solve, Delta_gamma table), 4.4 monotonicity) favours_assist=False

Issue: The final bisection holds 0 <= m_res < 0.05 kg, and m_res moves about 0.17 kg per kg of dm. Noise in dm(x) must therefore stay well below about 0.3 kg, or the bisection and the nonmonotone check can misbehave. The design specifies no tolerance for the monocoque 'smallest t' root solve, and no interpolation rule for the digitised Delta_gamma curve. Under a loose solve (for example 1e-6 m on a 13 m barrel, about 0.4 kg) dm would be jagged. The probe's dm(x) is smooth, but the probe uses neither the root solve nor the table.

Evidence: Measured on the probe: dm(x) differences at 1 kg steps from -0.0078514 to -0.0078511 kg/kg, and at 10 g steps -0.0078511 (review/numerics-code/time_push.py). S03 section 1: s_d = 0.1713 kg of m_res per kg of dm. search.py:1587-1623.

Recommendation: State the root solve (brentq with xtol about 1e-12 m, or a closed-form inversion) and a monotone interpolation of Delta_gamma (linear or PCHIP). Add a fast test that dm(x) differences at 1 kg and at 10 g agree within a stated tolerance, and keep the 'doubling N' convergence test.

## N12 [minor] (4.2 (stations, barrel lengths), 4.4 (transform signature)) favours_assist=True

Issue: The transform receives only vehicle_at(x), whose stage-1 propellant is m_p1 - x, and P_ref (Callable[[Vehicle, float], Vehicle]). Barrel lengths are defined as 'propellant volume m/rho plus an ullage fraction'. If that m were read from the vehicle passed in, the tanks would shorten as x grows. Fewer stations would exceed the envelope, dm and dm' would fall (favouring the assist), and the push stations would no longer line up with the pad envelope's stations, which are built on the full-load geometry.

Evidence: Design 4.2 'Barrel lengths: propellant volume m/rho'; 4.4 transform signature; src/launchsim/offload.py:197-204 (vehicle_at returns with_offload's vehicle).

Recommendation: Build the geometry once, at transform-build time, from the full-load vehicle (OffloadProblem.vehicle, or the structure file's own masses), and close over it. Add a test that the station grid and lengths are identical at x = 0 and at x*.

## N13 [minor] (4.4 (verification restatement), D-SP7-18) favours_assist=False

Issue: offload_solved_run would gain 'a dry-mass argument and a note argument'. But offload_overrides hard-codes the note 'an assumed structural penalty, not a sized structure', and _restated_quantity hard-codes `assumed: True`. Unless both are parameterised, the verification and recorded run's vehicle dict, and so resolved_config.yaml, would describe the modelled dm as an assumed penalty. That contradicts the 'never assumed' wording and the three-way branch at source.

Evidence: src/launchsim/config.py:2652-2668 (_restated_quantity sets assumed True), 2698-2708 (the penalty note), 2747-2756 (offload_solved_run passes 0.0).

Recommendation: Thread a note and a provenance flag through offload_overrides and _restated_quantity, and decide explicitly what the provenance flag of a modelled number is. Add a test that a structural case's final vehicle dict carries the modelled note, and that a penalty row's dict is byte-identical to today's.

## N14 [minor] (4.6 (events), 4.7) favours_assist=False

Issue: (a) The scene treats any 'ramp_end' event as 'full thrust: the engines' startup ramp ends'. If the linear motor's force-ramp end were logged under that name, the scene would label it wrongly. (b) fly_track returns a TrackExit only when the phase ended by track_end or s >= L - ATOL. A release by the new target-speed event, possibly before the ramp end t_r, must be added to that exit condition, or the loop runs on into the next sub-phase after the release.

Evidence: src/launchsim/scene.py:219 (RAMP_END_EVENT), templates/scene.html:534, 644; src/launchsim/phases/prelude.py:905-921 (ramp_end logging and the exit test at 912).

Recommendation: Give the drive ramp its own event name (e.g. drive_ramp_end) and a scene label. Make fly_track's exit test include the new trigger. Add a test with v_release reached before t_r.

## N15 [minor] (4.6 (model)) favours_assist=False

Issue: F = min(F_lim(t), F_max, P_max/sdot) is evaluated at push start, where sdot = 0. With Python floats that is a ZeroDivisionError (with numpy, inf and a warning). The step case t_r = 0 ('0 is a step') also divides by zero in min(1, t/t_r). Both sit in the RHS and in the drive-limit event function.

Evidence: Design 4.6 formulas; the drive-limit event calls params.forces at t0 (src/launchsim/phases/engine.py:688-704, 458-470).

Recommendation: Define the power term as P_max/sdot only for sdot > 0 (otherwise F_max), and F_lim = F_max when t_r = 0. Add tests at t = 0, at sdot = 0, and with t_r = 0.

## N16 [minor] (4.4 Records, 4.10 arms) favours_assist=False

Issue: An arm of a structural case changes the trajectory and also the envelope, because its pad is flown under the same perturbation. Yet _offload_arm_record carries no dm, so the arm's offload delta cannot be split into those two parts. The stage-1 dry-mass +/-10% arm also leaves the structure file's breakdown (m_struct,above) at its nominal value. arm_ctx = replace(ctx, ...) shares the solves dict, so the structure part of the memo key should also identify the envelope (the pad's trajectory key). Today's arms cannot collide, but nothing enforces that.

Evidence: src/launchsim/results_io.py:1593-1631 (the arm record has no dm), 1759-1790 (arm_ctx via replace shares ctx.solves; pad = ctx.run(arm.pad) is a full RunResult, so the envelope is available), 1174-1177 (the memo key).

Recommendation: Add structure_dm_kg, structure_n_peak_g and the envelope's pad name to the arm record. Include the pad's trajectory_key in the structural memo key. State the breakdown assumption for the dry-mass arm.

## N17 [minor] (4.2 station loads, 4.2.3) favours_assist=False

Issue: The aft skirt's pad envelope is defined as the hold-down support only (5.593 MN). The probe found the skirt governed in flight, at t ≈ 97-101 s and 7.7-7.9 MN, where mass above times n peaks. Left out, the flight case lowers the envelope and overcharges the skirt, which works against the assist and is not a fair measure either. The flight load through the base is not defined for the envelope's flight samples.

Evidence: S08 section 6 ('The aft skirt is governed at t of about 97-101 s ... 7.7-7.9 MN'); design 4.2 'aft skirt: N = the load through the base (push: F_int; pad: the hold-down support)'.

Recommendation: Define the skirt's flight load (everything above the skirt times n g0, plus D) and take the envelope as the maximum of the hold and flight cases. Add a test that the skirt envelope equals the probe's flight-governed value on a synthetic flight.
