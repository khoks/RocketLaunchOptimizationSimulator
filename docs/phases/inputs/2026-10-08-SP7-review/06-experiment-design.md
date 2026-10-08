<!-- Record of SP7 step 0: independent adversarial review (experiment-design) of design draft v1 (draft-v1.md in this folder), made by a workflow agent on 2026-10-08 at HEAD 22c62e9 and rendered from its structured output. The disposition of every finding is appendix A of ../2026-10-08-SP7-design.md. Not edited. -->

# Review: experiment-design

Verdict from the experiment-design lens: the case list can produce a central structural x* next to SP1's rows, but as drafted it cannot answer the research question honestly or usefully. (1) The uncertainty band is the experiment's main deliverable, and the method as written cannot produce it. An exhaustive search over 2^k corners of about 22 coefficients is roughly 4 million evaluations. That is about 117 h at the probe's vectorised speed, not "seconds". dm is also not monotone in every coefficient: the probe has an interior maximum in ullage pressure, and its direction flips between 4 and 7 g0. So "the bounds of the stated ranges" would be a false label. (2) Even if computed, the band is all coefficients at their extremes at once. With the design's own ranges (NOF up to 1.9; k_entry anchored high at the thrust-structure relation of 200-360 kg/MN) the high end is no_offload, so the pre-registered "cannot decide" reading is close to certain. The headline then rests on an unanchored central k_entry. Threshold values (break-even k_entry, NOF and DLF), a sourced-physics band and a tornado in x* would say more. (3) Several rows are lower bounds of a large unmodelled cost. The release is a step in every drive, so the unload flag fires on every case and the payload sees about -4 g against Falcon's -2 g limit. The step row, the 50 m point and lm_hot exceed the 5.195 g0 MECO envelope, and stage-2 mass costs about 24 kg of offload per kg. (4) The linear-motor rule (F_max fixed for the full-load pad vehicle) pushes the offloaded stack at 4.11-4.35 g0 against 3.996. lm_hot under that rule keeps the interface force at F_max while the tanks see 5.4-5.8 g0. So the drive variants mix several effects and cannot show the hot start's structural lever. (5) The axes most likely to change the answer are missing: an exit-speed axis, where a near-fixed structural cost per push may make small assists net-negative (the "every m/s helps" test), and the constant_accel full-thrust hot start, which cuts the interface force by 34% and acts directly on the dominant k_entry x F_peak term. These can be paid for by dropping duplicate solves (the 100 m sweep points, three sweeps instead of one, re-runs of pinned rows). The three-set stroke sweep is mostly a re-measurement of the known X(dm) curve: at a fixed exit speed the flight after release is identical. Its low/high sets are not bounds at other felt g, and it lacks the per-element break-even g. The pre-registration also needs numeric thresholds for "survives" and "most". Every probe number below comes from S08's placeholder model or from my own closed-form scripts in scratchpad a0/review/experiment-design/. They are planning estimates, not findings.

## E1 [blocker] (4.2.5, D-SP7-15, S2) favours_assist=True

Issue: The low-mass and high-mass sets are to be found by "an exhaustive corner search of the sizing model (2^k evaluations, closed form, seconds)". 4.2.5 lists about 22 coefficients: E, nu, rho_w, F_tu, eta_w, FS_u, p_u,LOX, p_u,RP1, p_u,min, s_dg, k_s, (C,n), NOF, t_min, L_s, a/b, k_entry, k_ts, f, two densities, ullage fraction. That is about 4.2 million evaluations, not seconds. Worse, dm is not monotone in every coefficient, so the extremes need not lie at corners. The label "the bounds of the stated coefficient ranges" would then be false, and the high-mass set could understate the maximum.

Evidence: Design lines 105 and 233-242. My timing of S08's vectorised probe (time_eval.py): 0.100 s per warm evaluation, so 2^20 = 29 h and 2^22 = 117 h. S08 section 7 and my corner_transfer.py: in the stiffened-3x form at n = 4.0 g0, p_u 2.5 bar gives -40 kg and 4.5 bar gives -168 kg against central, so the maximum is interior. A higher minimum gauge lowers dm (-50 to -346 kg).

Recommendation: Replace the exhaustive corner search with a stated bounded min/max method. Check each coefficient for monotonicity on a 5-point grid at the headline push; take the range end for monotone coefficients and the interior extremum for the others; or use a bounded multi-start optimiser that exploits the per-element separability. Record the method, the number of evaluations and each coefficient's direction in the structure file with the frozen sets. Label the band "the extremes found by <method> over the stated ranges" and drop "seconds".

## E2 [major] (4.2.5, 4.10 (_st_low/_st_high), D-SP7-15) favours_assist=False

Issue: Taking every coefficient at its worst at once makes the band's outcome close to certain, and the band has no probabilistic meaning. With the design's own ranges, the high-mass set holds NOF 1.9 and k_entry at its stated high anchor, the thrust-structure relation. At 20.8-22.4 MN that hardware alone is 4.2-8.1 t, around or beyond SP1's roughly 8.5 t break-even, so the high-mass case is almost surely no_offload. The low-mass set (about 1.4 t of tanks, NOF 1.0, a light ring) leaves about 33 t. The pre-registered "cannot decide" sentence is then a foregone conclusion that restates S08.

Evidence: Design 4.2.3 lines 223-226 (k_entry high = thrust-structure relation). S06 coefficient table (k_ts 0.20-0.36 kg/kN) and S06 recommendation 6 (NOF 1.0-1.9, applied to increments). S08 section 7 (corner dm 1,390-3,487 kg before NOF). RQ1-fuel-offload-2d.md:296-299 and 310-316 (penalty rows; break-even about 8.5 t, slope 4.49-5.10 t/t).

Recommendation: Report uncertainty in three layers. (i) A one-at-a-time tornado in x*, using the coupled placement and labelled as an estimate, for every coefficient. (ii) A "physics band" from E1's extremes over the sourced or physical coefficients only (materials, factors, pressures, knockdown, geometry, densities), with k_entry, NOF and f at central. (iii) The assumed design coefficients (k_entry, NOF, f/t_r, margin) as explicit axes with pre-registered break-even values: the k_entry, NOF and DLF at which x* falls to 50% and to 0% of 41.263 t (sizing-only plus one confirming solve each). Keep the all-at-once extremes only as a labelled outer envelope.

## E3 [major] (4.2.3, 4.10 (silo_cold_s1_st headline)) favours_assist=False

Issue: The headline is the central set, but its likely largest term, k_entry x F_peak, is charged on the whole interface force with no envelope credit, and its central value has no anchor. "The order of hold-down hardpoint structure per unit load" has no public source: S06 found no mass or load capacity for Falcon 9's hold-downs, octaweb or aft skirt. The headline x* is therefore mostly a statement about one assumed number, yet it will be read as a model result.

Evidence: Design lines 217-226. S06 section 7 ("Falcon 9 octaweb, aft skirt and hold-down fittings: no public mass or load capacity"). S06 section 9 (load entry 3.6 t, "least sourced ... largest"). S08 section 7 (0.4-2.1 t at 20-100 kg/MN against 1.4-3.5 t of tanks).

Recommendation: In the headline row, the summary and the findings, split dm into the closed-form part (barrels, domes, skirt) and the coefficient part (k_entry x F_peak). Beside the headline, report a closed-form-elements-only row (k_entry = 0), labelled as leaving out the load-entry hardware and never as a lower bound for the vehicle, together with the break-even k_entry from E2. If S0 cannot source the central, the pre-registration says so in its first lines.

## E4 [major] (4.2.2 (structure_release_unload), 4.2.1, 4.6, D-SP7-13) favours_assist=True

Issue: Start and release are treated inconsistently. The central DLF credits a 1.06 s force ramp at push start, but release is a step for every drive ("no ramp-down is modelled for any drive"). The release flag therefore fires on every structural case, the headline included. The design's own formula gives an effective n of 2 n_after - n_rel, about -4.0 g0 for a cold release, and S08 gives -0.53 MPa absolute at the LOX bottom (column separation). About -4 g at the payload is twice the published Falcon payload tension limit of -2.0 g. A flag on every row is noise, and the headline would be presented as feasible although its modelled release is not.

Evidence: Design lines 102, 200-204 and 211-215. constant_accel.py:224 ("infinite jerk at push start and release"). S08 section 3 (release check, -0.53 MPa). S07 section 7.3 (Falcon User's Guide v8 Table 5-3: -2.0 g for payloads over 1,800 kg; P_ref is 26 t). S07 section 5 (a 0.5-1 s ramp costs +0.2-0.9% of F_max).

Recommendation: Ramp the release the same way as the start. For linear_motor, model a force ramp-down over t_r before s_release, so its exit-speed cost is in the trajectory. For constant_accel, assume the same ramp-down, report its closed-form cost and evaluate the release flag at the ramp's DLF (about 1.06, a swing of about -0.24 g), with the step as a labelled bound row. Add a payload-environment flag (+6.0/-2.0 g, Falcon User's Guide v8) and pre-register how flagged rows are read.

## E5 [major] (4.2.2 (structure_upper_stack_exceeded), 4.10 (_st_step, 50 m point, lm_hot, lm_r07)) favours_assist=True

Issue: Rows that exceed MECO's 5.195 g0 are lower bounds of a large unmodelled cost, yet _st_step is presented as "Q7's step bound". Mass added to stage 2 costs about 24 kg of offload per kg, so a few hundred kg on stage 2 or the payload adapter would remove several tonnes. The step row (6.99 g0) and the 50 m point (7.0 g0) also exceed the published +6.0 g payload axial limit. The design's list of rows that trigger the flag leaves out lm_hot, which reaches 5.39-5.81 g0 quasi-static under the stated rule, and lm_r07, which reaches about 4.9-5.1 g0 with the DLF.

Evidence: Design lines 207-210 and 452-453. Derived: 4.49 t of offload per t of stage-1 dry mass (RQ1-fuel-offload-2d.md:297) divided by 184 kg of payload per t (README.md:256) gives about 24 kg of offload per kg of payload-equivalent mass. lm_hot.py: peak felt 5.39/5.59/5.81 g0 at x = 0/20/41.3 t. S07 section 4 table (r = 0.7: 25.26 MN), giving 4.67-4.85 g0 at 531-552 t before the DLF. S07 section 7.3 (+6.0 g).

Recommendation: Either size the interstage and the stage-2 barrels and domes with the same station model against the pad's own full-flight envelope (stage-2 burn included), charging that mass to stage 2, or keep flagged rows out of every comparison and label them "lower bound, not a bound". Rename _st_step accordingly. Pre-register which rows are expected to flag: step, 50 m, lm_hot, and possibly lm_r07.

## E6 [major] (4.10 B (the linear-motor rule; lm_cold_target, lm_cold_atL, lm_cold_r07)) favours_assist=False

Issue: F_max is sized once, for the pad's full-load vehicle, and every offloaded stack is then pushed at full force. constant_accel instead adapts its force to the stack. So lm_cold_target minus silo_cold_s1_st mixes three effects: the ramp in the trajectory, an over-push of 3-9% in felt g and 5-9% in interface force, and an earlier release. The over-push dominates, so the comparison cannot attribute anything to drive realism. lm_cold_r07's baseline (release at v_e or at L) is not stated.

Evidence: lm_rule.py (design rule: r = 1, m_c = 0, t_r = 1.061 s, 572,354.4 kg): F_max = 22.671 MN, felt 4.039 g0 at full load. At x = 10/20/30/41.3 t the felt load is 4.111/4.185/4.262/4.353 g0 against 3.996, F_int is 22.67 MN against 22.04-20.81 MN, and v_e is reached at s = 97.8/95.5/93.4/90.9 m. ramp_cost.py: the ramp alone adds +1.1% to n at 100 m. Design 4.4 lines 300-303 (dm' > 0 under this rule); lines 471-483.

Recommendation: State the rule as "a facility sized for the full-load pad vehicle, run at full force". Add one variant fixed before any run that isolates realism at equal felt g: either F_max by the same rule for SP1's headline offloaded stack (531,091.5 kg), or a force command capped at the constant_accel net acceleration, F = min(F_max, P_max/v, M (a_cmd + g_eff)). For every lm variant, report the felt g at x* and the sizing-only dm at constant_accel's felt g, so the split is explicit. Name lm_cold_r07's baseline.

## E7 [major] (4.10 B (lm_hot), 4.6) favours_assist=False

Issue: With m_c = 0, the track equation gives F_int = F - f_imp T. At f_imp = 0 the interface force therefore stays at F_max while thrust adds to the tank load and the exit speed. lm_hot cannot show the hot start's structural lever, a lower interface force. It mixes three effects (exit speed rises to about 90-93 m/s, felt g goes above the MECO envelope, the interface force is unchanged) and tests one timing only, although RQ1 found that the hot-start ordering depends on timing.

Evidence: Design 4.6 lines 374-376. lm_hot.py: release at 2.68-2.78 s, v_exit 89.8-93.2 m/s, peak felt 5.39-5.81 g0, F_int peak 22.67 MN at x = 0-41.3 t. RQ1-fuel-offload-2d.md:418-427 (the 75 m-deep start is best, the push-start start is worst) and 708. Brief section 1 lines 48-50.

Recommendation: Fix the hot start's drive command before any run, two ways: (a) as stated, force-limited only; (b) total-acceleration-limited, with the motor force reduced as thrust builds so the felt g stays at the cold value, which is how a facility protecting the structure would run. Fly at least two timings with the push_start reference (lit at push start; full thrust at release) and f_imp 0 and 1. Pre-register that (a) will raise the upper-stack flag.

## E8 [major] (4.10 A (case list)) favours_assist=False

Issue: Experiment A has no constant_accel hot start, although the code can already fly the case that acts on the dominant term. silo_hot_full (lit 2 s before the push, full thrust on the track) carries 14.78 MN at the interface against 22.49 MN, with the same tank felt g and almost the same payload gain. With aft-ring entry, the skirt increment and k_entry x F_peak fall by about 34%. SP1's best run-command variant, silo_hot_ramp_s1 (46.0 t), is not re-solved with structure either, so whether RQ1's hot-start gain survives stays unanswered.

Evidence: RQ3-silo-screening-2d.md:499 (silo_hot_full interface 14.78 MN against 22.49) and 164 (+1,488.6 kg against silo_cold's +1,498.8 kg). experiments/silo_screening_2d.yaml:82 (push_start reference). RQ1-fuel-offload-2d.md:421. Derived: 7.7 MN x 50-255 kg/MN = 0.4-2.0 t of hardware, about 1.7-8.9 t of offload at 4.49 t/t.

Recommendation: Add silo_hot_full (copied verbatim) and silo_hot_ramp_on_track to A, each with an uncharged and a central structural stage-1 solve (four solves, about 3 min at S09's rates). Pre-register the expected sign: less hardware, more propellant burned on the track. State that impingement does not change constant_accel's interface force.

## E9 [major] (4.10 A (sweeps)) favours_assist=True

Issue: The only sweep varies the stroke at a fixed exit speed. There is no exit-speed axis, so the regime most likely to undercut the hypothesis is never run. At a fixed felt g, dm barely depends on x, so the structure is close to a fixed cost per push, while the offload shrinks with exit speed. Below some assist speed, the structure would cancel all of the offload: that is the direct test of "every m/s of assist helps".

Evidence: S08 section 7 (dm slope -9 to -14 kg per t of offload). RQ1-fuel-offload-2d.md:330-334 (sweep 1 at 3 g0: 18.8 t at 38 m/s, 28.7 t at 54 m/s, uncharged). At RQ1's 4.5-5.1 t of offload per t of dm, a central dm of a few tonnes leaves the 25 m point a few tonnes or nothing (an estimate). CLAUDE.md "Project" (report findings that undercut the hypothesis).

Recommendation: Add SP1's sweep 1 axis (of: silo_cold, stroke 25-300 m at 3 g0; silo_offload_2d.yaml:129) with the central structure: five solves, about 4 min. Alternatively, an exit-speed axis at a fixed 100 m stroke (38-108 m/s, felt about 1.75-7.0 g0). Pre-register the reading "the lowest exit speed that still offloads" and the break-even speed.

## E10 [major] (4.10 A (three sets x four strokes)) favours_assist=False

Issue: Three problems with the depth design. (1) The low-mass and high-mass sets are frozen at the 4 g0 headline push, but the governing modes and some coefficient directions change with felt g, so at 50, 200 and 300 m those sets are not the extremes. (2) At a fixed exit speed the flight after release is identical, so x*(L) = X(dm(L)), SP1's already-measured penalty curve; the 12 solves mostly re-measure it. (3) There is no break-even g. In the design, the aft skirt's envelope is the 5.593 MN hold-down load and the hardware gets no envelope credit, so no stroke ever reaches dm = 0, and the long-stroke end is set by k_entry x F_peak. The plan does not say so.

Evidence: corner_transfer.py: stiffened-3x p_u at 2.5 bar gives -40 kg at n = 4.0 but +47 kg at n = 7.0. breakeven.py (probe, tanks only, quasi-static): dm 0 up to 1.4 g0, 16-28 kg at 1.6 g0, 250-297 kg at 2.0 g0, 1.97-2.55 t at 4.0 g0, with the governing element changing. RQ1-fuel-offload-2d.md:401-407 (the flight after release does not depend on the stroke). Design lines 217-221 and 461-463.

Recommendation: Run the stroke sweep through the solver with the central set only (4 points). For low and high, either recompute E1's extremes at each stroke's push (sizing only, frozen before flight) or give sizing-only placements labelled as estimates. Add a sizing-only table of dm against felt g (1.2-7 g0) per element, with each element's break-even n and the stroke it implies at 76.7 m/s. Pre-register that the long-stroke dm is set by the skirt and k_entry terms.

## E11 [major] (4.10 (pre-registration), 6 (exit criterion 7)) favours_assist=True

Issue: The readings are not fixed numerically. "The sentence fixed in advance for a band wider than the offload" leaves open which width is compared with which offload (the band width against central x*, against 41.263 t, or high-mass x* <= 0). Exit criterion 7, "plainly whether the structure cancels most of the offload", does not define "most", and nothing defines "survives". The reading can then be chosen after the run.

Evidence: Design lines 497-500 and 576-579. Brief section 5.6 lines 410-411.

Recommendation: Pre-register numeric rules. For example: "survives" if the physics band's adverse end keeps more than 50% of 41.263 t; "cancels most" if central x* is below 50%; "undecided" if the physics band straddles 50% or any band end is no_offload. Define each word in terms of the same cases, and say how no_offload ends are read (E15).

## E12 [minor] (4.2.1, D-SP7-12 (constant_accel rise-time rule)) favours_assist=True

Issue: constant_accel structural cases get the DLF of a ramp that their trajectory does not fly. The quasi-static n of a drive that ramps over t_r and still reaches v_e at L is higher than constant_accel's, and the gap grows as the stroke shortens. The ramp is credited, but its cost is not charged.

Evidence: ramp_cost.py (vertical, ramp from the 1 g support, t_r = 1.061 s): n = 4.039 against 3.996 at 100 m (+1.1%), 7.370 against 6.996 at 50 m (+5.3%; the ramp fills 82% of the 1.30 s push), 2.502 against 2.496 at 200 m. constant_accel.py:224.

Recommendation: For constant_accel structural cases, size with the quasi-static n the ramped drive would need (closed form), or report the understatement per stroke in the Structure subsection. Use the equal-felt-g linear-motor variant of E6 as the headline's cross-check.

## E13 [minor] (1 (Magnitude), 4.10 (pre-registration "what is already known")) favours_assist=True

Issue: The planning magnitude the user approves on, "12-33 t (30-80% of the headline)", comes from S08's probe without NOF and with k = 20-100 kg/MN. The design's own ranges add NOF 1.0-1.9 on every increment and a k_entry high anchor of 200-360 kg/MN, so the expected outcome reaches no_offload. Section 1 understates the downside.

Evidence: Design lines 35-40, 197 (NOF on the increment) and 223-226. S06 recommendation 6 and coefficient table. S08 sections 7-8.

Recommendation: Restate the planning range with the design's ranges (NOF and the k_entry anchors) before approval, and in the pre-registration's "what is already known", alongside the probe's own numbers.

## E14 [minor] (4.4 (payload form), 4.10 (payload cases)) favours_assist=False

Issue: Three payload cases cost a new record kind, a two-pass search, summary rows and tests for numbers that mostly track 1,498.8 kg - 0.184 x dm. The structure in the payload form is sized at full load, so it belongs beside _st_full, not the flown headline. Its real value is a non-extrapolated payload deficit where dm exceeds the ±2.22 t RQ3 tested, chiefly at the adverse end.

Evidence: Design lines 313-317 and 458-459. README.md:256 (184 kg per t). RQ3-2d (±10% dry-mass cases only).

Recommendation: Keep the central and high-mass payload cases (the high-mass one measures the adverse end when x* = 0) and drop the low-mass one. Place them beside _st_full with the sizing basis stated. Add the payload form to the cut list before the margin rows.

## E15 [minor] (4.4 (summary band line), 6 (exit criterion 4)) favours_assist=True

Issue: The high-mass case and the step row are likely no_offload (E2, E5). The solver records x* = 0 and a Δv shortfall for such a solve, and the planned band line "x* from <high-mass> to <low-mass> t" would print 0. That hides how far beyond break-even the adverse end lies. Exit criterion 4 expects every case to end ok or flagged.

Evidence: src/launchsim/offload.py:94-95 (NO_OFFLOAD_STATUS) and 311-317 (offload_kg 0 for no_offload; dv_shortfall_mps). Design lines 331-334 and 564-570.

Recommendation: Pre-register that a no_offload end is reported with its Δv shortfall and its payload deficit (from the payload form), never as "0 t". Accept no_offload in exit criterion 4 as an outcome with those numbers.

## E16 [minor] (4.10 (redundancy), 5 (cut list)) favours_assist=False

Issue: Several solves only reproduce what is already known. The sweep's 100 m points duplicate _st, _st_low and _st_high. Three separate sweeps fly each point's full-load run three times, although a sweep's offload field takes a list. Experiment B's silo_cold pair duplicates A's. The three penalty rows re-run configurations D-SP7-25 already pins. The answers of lm_cold_r07 and lm_sealed are largely set by closed forms. That budget is better spent on E8 and E9.

Evidence: src/launchsim/config.py:1464 (sweep offload: list[str]). Design lines 448-449, 461-463, 470 and 547-549. S07 section 4 table (r against felt g). S08 section 4 (sealed column at most about 5% of the interface force).

Recommendation: Use one sweep carrying the three structural cases (or the central one only; E10). Keep the reproduction rows labelled as reproduction checks, or cite the pins. Move the saved minutes to silo_hot_full and the exit-speed axis.

## E17 [minor] (4.10 A (variants and sweep definition)) favours_assist=False

Issue: A lists only "variant silo_cold as SP1", which sets net_accel_g: 3.0. Sweeping assist.stroke_m on it varies the exit speed at 3 g0 (SP1's sweep 1), not the fixed-exit-speed series the design describes. SP1's fixed-v_e sweep ran over silo_cold_200m, which uses exit_speed_mps.

Evidence: experiments/silo_offload_2d.yaml:129 (sweep 1 of silo_cold) and 136 (sweep 2 of silo_cold_200m). src/launchsim/config.py:618-646 (exactly one of net_accel_g or exit_speed_mps). Design lines 442-444 and 461-463.

Recommendation: Add silo_cold_200m (copied verbatim), or a 100 m exit-speed variant, to A and name it as the fixed-v_e sweep's of. Per E9, also run the of: silo_cold axis on purpose.

## E18 [minor] (4.2 (Envelope and increment)) favours_assist=True

Issue: t_push is the maximum over the push samples only. The assisted run's own stage-1 flight is not checked against the envelope, although its max-Q is above the pad's and rises with depth. q-alpha at the kick, 1.7-3.4 times the pad's, is uncharged bending. Both favour the assist and are not listed with a bias direction.

Evidence: Design lines 193-196. RQ1-fuel-offload-2d.md:296 (offloaded max-Q +3.35%) and 349 (+12.5% at 300 m). README.md:261 (RQ6, q-alpha). Design 4.11 lines 504-508 (caveats: "free kick" only).

Recommendation: Take the required thickness as the maximum over both the push and the assisted run's own stage-1 flight samples (same machinery, small cost). In the note's caveats, list q-alpha bending as uncharged, with its direction.

## E19 [minor] (4.10 C (bridge), 4.3) favours_assist=False

Issue: The bridge has its own structure file, but the plan does not require its coefficients to equal the gate file's. If they differ, the bridge mixes the calibration miss with coefficient changes. The fork also has no sourced LOX/RP-1 split, so its mixture fraction and tank lengths are assumptions.

Evidence: experiments/silo_offload_2d_readme.yaml header ("this fork has no sourced LOX / RP-1 split"). configs/vehicles/generic_f9_class_2d_readme_loads.yaml:38-39 (25.6 t dry, 395.7 t propellant, assumed). Design lines 139 and 485-486.

Recommendation: The bridge file reuses the gate file's coefficient values and frozen sets unchanged. Only the layout from the fork's propellant masses (mixture fraction stated as assumed) and its breakdown differ. A test compares the two files' coefficient sections. Central only.

## E20 [minor] (4.10 (pre-registration "what nothing measures"), 4.11 (caveats)) favours_assist=True

Issue: The plan does not list the questions a skeptical referee will ask that this experiment cannot answer. Propellant settling for the 0.5 s-late ignition after a 4 g0 to 0 g release. The LOX transfer tube, COPVs, engine mounts, joints and weld lands under 4 g0 (only partly covered by NOF). Lateral and bending loads in the shaft. Fatigue from a push on every flight of a reused stage. The payload environment. A strengthened vehicle that must always fly assisted, since its pad flights pay dm. A clean-sheet vehicle designed for the push (RQ7, out of scope). Also, the exemption of the LOX barrel, interstage and stage 2 rests on the unthrottled model's 5.195 g0 MECO.

Evidence: S08 section 9 (items left out, including settling). Design lines 29-34 (LOX barrel at 0.77 of MECO's 7.095 MN; stage 2 not sized because 3.996 < 5.195). Brief section 2 (RQ7 and bending out of scope).

Recommendation: List each item in the pre-registration and in the note's limits, with its bias direction where known. Add a sizing-only envelope sensitivity with the MECO case capped (for example at 4.5 g0) to show how much the LOX-barrel and upper-stack exemptions depend on the unthrottled MECO.

## E21 [minor] (4.10 (missing design-for-the-push row)) favours_assist=False

Issue: There is no row for pressure stabilisation, that is, raising the tank pressure during the push only, though a referee will ask for it. The probe suggests the lever is small and form-dependent: raising both tanks increases dm through LOX hoop, and raising RP-1 only helps the monocoque form a little. Saying so with a number answers the referee cheaply.

Evidence: push_ullage.py (S08 placeholder model; envelope at 3.5 bar, push-only pressure). RP-1 only, +1/+2/+3 bar: dm changes by -148/-295/-444 kg (monocoque), -65/-116/-76 kg (stiffened 2x), +73/+241/+499 kg (stiffened 3x). Both tanks: up to +1,787 kg (stiffened 3x at 6.5 bar).

Recommendation: Add a sizing-only row (no flight) at a push-time RP-1 pressure fixed before any run, for example the S06 range's 4.0 bar high end or a proof-limited value from S0. Fly it only if it moves dm by more than a pre-registered threshold (for example 0.5 t).
