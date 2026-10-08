<!-- Record of SP7 step 0: independent adversarial review (delivery-scope) of design draft v1 (draft-v1.md in this folder), made by a workflow agent on 2026-10-08 at HEAD 22c62e9 and rendered from its structured output. The disposition of every finding is appendix A of ../2026-10-08-SP7-design.md. Not edited. -->

# Review: delivery-scope

Delivery-scope verdict: the plan does not fit one session in its current form, and one step cannot work as written. Three things go wrong. (1) S2's "exhaustive 2^k corner search, closed form, seconds" is out by orders of magnitude. The design ranges about 23 coefficients. S08's own vectorised probe model takes about 1.5 s per corner (timed: scratchpad review/delivery-scope/time_corner.py), so 2^20 corners is about 430 h, and the frozen sets that S6 and S7 need would never exist. (2) The close (C) puts back everything SP2's delivery review took out of its close: the demo, the public face, a new gallery entry, the deck and its PDF, the manual, CLAUDE.md, README, SP3's fact-check, the handoff, memory, the cold read and the exit gate. It also plans code changes (replay.penalty_structure_sentence, app.SP1_HEADLINE's "Structure." caveat) after the finding runs, in a step with no code gate. (3) The deferral order cuts experiment cases that cost minutes of background compute and saves no session time. One of those cuts (the Isp and drive-efficiency arms) breaks CLAUDE.md's rule that a headline gets a sensitivity check. Ordering problems: the structural headline waits for the whole drive build because S6 and S7 register and run all three files from one commit, and file B cannot even resolve before S4. S3's coupling is built and tested only on constant_accel, and no S4 or S4a test checks the structure fed by a linear-motor push before file B flies seven of them. S3 is oversized, and it leaves out the sweep and arm columns that exit criterion 6 needs. Several gates cannot be checked by an independent agent as written ("every output byte-identical", "the pages looked at", closed forms with no tolerance). The frozen sets cannot record "the commit that computed them": a file cannot hold its own commit's hash, and nothing re-checks the sets after later steps change the code. KI-038's renderer git line conflicts with the gallery criterion that the six pages regenerate byte for byte. physics.md is missing from the S1, S2, S3 and S4a rows, and S4a adds an event. The run budget is credible at SP1's measured rates: my count is about 17.5-23, 11-14.5, 11-15 and 2.5-3 min for the four commands. File A is missing the fixed-exit-speed variant its sweep needs, and one sweep can name all three structure cases instead of three sweeps. The real gap is that the plan has no session-effort budget. SP2's log shows three review passes and three fix rounds on nearly every step, against the protocol's "up to two", plus six or more full-suite runs at 15-60 min each. The exit criteria leave out KI-030, KI-035, KI-038, KI-021 to KI-023, the app's basis, the frozen-set check and the grep for leftover "no structural model exists" text. They also give no "changes against the brief's 10" list.

## D1 [blocker] (3.2 D-SP7-15; 4.2.5; 5 S2) favours_assist=False

Issue: The low-mass and high-mass sets come from an 'exhaustive corner search of the sizing model (2^k evaluations, closed form, seconds)'. The ranged coefficients listed in 4.2.5 number about 23: E, nu, rho_w, F_tu, eta_w, FS_u, p_u,LOX, p_u,RP1, two p_u,min, s_dg, k_s, C, n, NOF, t_min, L_s, a/b, k_entry, k_ts, f, two densities and the ullage fraction. More come in if the breakdown and mixture entries are also range quantities, as 4.3's 'every number is a range quantity' says. Each corner must re-size the pad envelope, because t_env depends on the same coefficients. The monocoque thickness is implicit in t (the gamma(t) fixed point plus the Delta_gamma lookup), so 'closed form' is not true either. As written, S2 cannot produce the frozen sets that S6 and S7 depend on.

Evidence: Design lines 105 and 237-241. Timed S08's own vectorised probe (scratchpad/a0/08-closed-forms-and-probe/b_probe.py; 200 stations, 618 pad samples) with scratchpad/a0/review/delivery-scope/time_corner.py: 1.44-1.60 s per corner (envelope plus push). At 1.48 s: 2^16 = 27 h, 2^20 = 432 h, 2^23 = 3,453 h serial. A model 30 times faster still needs about 14.6 h for 2^20. The probe itself ranged only sigma, FS, E and p_u per buckling form (S08 lines 160-172).

Recommendation: State k, and make the search feasible by design. Group the coefficients that come from one source: the alloy set (E, nu, rho_w, F_tu), the pressure set (p_u and p_u,min tied), and k_ts out of the aft_ring headline. Run the one-at-a-time tornado first. Take each coefficient whose sign does not change between the corners and forms tested straight to the end of its range that lowers or raises dm. Enumerate only the coefficients whose sign flips (the pressures, s_dg, the buckling form): 2^4 to 2^6 corners. Time one evaluation in S1's gate and budget the search in S2's gate (for example, under 10 min). Label the band 'the extremes over the enumerated corners after the stated screen'.

## D2 [major] (5 (C row); 4.5; 6 crit. 10-11) favours_assist=False

Issue: C holds what SP2 had to spread over A7, A8 part 1 and A8 part 2: the exit gate, the full suite, the demo, trackers, CLAUDE.md, README, the landing page, the deck and its PDF re-print, the gallery (protocol 7.6 asks for a new entry for the phase's demo runs, and the design never names one), the manual chapters, SP3's fact-check, the handoff, memory and the cold read. 4.5 also puts code changes at the close: replay.penalty_structure_sentence ('no structural model exists'), app.SP1_HEADLINE's 'Structure.' caveat (app.py 1473-1478) and site/build.py 227. Those changes come after the S7 runs, in a bookkeeping step that lists no src file, no standing gates and no full suite, and they move the closing commit.

Evidence: Design lines 345-348 and 545. SP2 phase file lines 1918-1930: the delivery review moved public-site material from the close into A7 because the close would overrun. Lines 1979-1981: A8 still needed two parts. Protocol lines 215-222 (item 6) and 249-253 (closing commit = last commit that changed code). Manual chapters the design never assigns (S09 section 5): 05-assist-and-ignition.md 14-16 ('Refused today'), 08-outputs.md 278-281, 06-vehicles.md (a new structures section), 12-faq-glossary.md 80-81. site/index.html 131 and 316 say 'no structural model exists yet (phase SP7, next)'.

Recommendation: Add S7b after the note exists: the program-level code wording (replay, app, site/build.py), the pinned tests, the gallery regenerated with the diff recorded, the standing gates and the full suite, and an honesty review. Add S8: the demo, a new gallery entry (replay and scene pages of pad and silo_cold_s1_st), the deck slides and PDF, the manual chapters listed by S09, and the landing page, with visual, honesty and compliance reviews and a site-build gate. Split C into C1 (documents and SP3's fact-check, committed) and C2 (the independent exit gate and the close), as SP2's A8 did.

## D3 [major] (5 'If room runs out') favours_assist=False

Issue: The deferral order relieves the wrong constraint. Most items it cuts are experiment cases that run in the background for minutes: lm_cold_r07 and lm_sled22 (2 S + 4 V, about 3 min), the low-mass and high-mass stroke sweeps (8 S + 8 V, about 8 min), the margin rows (2 V, which the user asked for in Q3, D-SP7-03) and 'the arms beyond stage-1 dry mass and C_D'. Session effort, which is what runs out, is spent on build steps. Cutting the Isp and drive-efficiency arms saves about 1.5 min (the efficiency arm reuses the nominal solve for constant_accel) and drops a sensitivity check CLAUDE.md requires for headline numbers. Braking, which D-SP7-04 names 'first to cut' with the air column, is not in the list. The costly build items are not in it either: the payload form (a new record kind and a two-pass search), S4a's target-speed release, the thrust-structure row, the thickness figure and KI-030.

Evidence: Design lines 89, 456 and 547-549. CLAUDE.md, 'Experiments and reporting': 'Headline numbers get a sensitivity check: +/-10% on stage-1 dry mass, Isp, C_D and drive efficiency'. S09 3.1 rate set M: V 34-46 s, S 20-26 s. experiments/silo_offload_2d.yaml shows sensitivity_of naming one case.

Recommendation: Order the cuts by build cost: S5 and lm_sealed; then the payload form; then S4a with lm_cold_target (keeping release at L); then the bridge's second structure file and file C; then the thrust-structure row. Never cut a case that costs only compute, and never cut the CLAUDE.md arms. Add a last-resort line tied to checkpoint 1: run the structural files and write an in-progress handoff before building the drive.

## D4 [major] (5 order (S3a, S4-S5, S6, S7); 4.10) favours_assist=False

Issue: The main deliverable, the structural headline in file A, cannot run until S4, S4a and S5 are built, because S6 registers and S7 runs all three files from one commit. File B cannot be registered early: it uses model: linear_motor, which PlannedAssistConfig refuses until S4, and test_every_shipped_planar_experiment_is_checked requires every planar file under experiments/ to be listed and to resolve. So a slip in the drive steps, which carry the riskiest engine changes (kink times, a pending release-referenced ignition, a terminal event, work_other), holds up the answer the phase exists for.

Evidence: Design lines 538, 543-544 and 488-490. tests/test_config_planar.py 880-890. Brief section 1 and D-SP1-18: the structural answer decides whether the 10% survives. Checkpoint 1 already marks file A as producible after S3a.

Recommendation: Split into S6a/S7a, which register and run files A and C (run A, sweep A, run C) right after checkpoint 1, and S6b/S7b, which register and run file B after S5. File B's variants and its linear-motor rule are already fixed by the approved design, so registering B after A's results does not reopen any choice. Say so in B's pre-registration, under 'what is already known'. Let the findings note be drafted on A while the drive is built.

## D5 [major] (5 S3, S4, S4a; 4.4; 4.6) favours_assist=False

Issue: No step tests the structural transform fed by a linear-motor push. S3 builds and tests the transform on constant_accel only. The linear motor's inputs to it arrive later: the holding force F_0 and the resting n_0/F_0 of a hot start, the drive's own t_r in the DLF, F_peak at the ramp end and at the power corner, release at s_release < L, and the upper-stack flag at r = 0.7. Yet the S4 and S4a test lists contain no structural test. File B's seven central structural solves would be the first time the combination runs, which goes against 'No physics feature is used in an experiment until its test passes'.

Evidence: Design lines 292-298 (the transform takes 'every push sample and event (ramp end, power-limit corner, release)'), 200-203 (n_0, F_0 'the hold's for a hot one'), 536, 539 and 540. S03 line 134: under a linear motor dm feeds back through M into the push itself.

Recommendation: Add to S4a, or a small S4b, fast tests of the transform on linear-motor pushes. (a) A cold push at r = 1: n_peak, F_peak and DLF equal the closed forms of 4.6 with the drive's t_r. (b) A hot push: n_0 and F_0 come from the hold. (c) A target-speed release below L: the load cases stop at s_release. (d) A slow coupled solve for one lm case with dm'(x) > 0 and no offload_nonmonotone flag. Name these tests in exit criterion 1.

## D6 [major] (5 S3; 4.4; 6 crit. 6) favours_assist=False

Issue: S3 is the largest step in the plan. It spans config (the offload-case field, the experiment block, five refusals, and inheritance by sweeps and arms), the solver (transform, builder, inner iteration), the verification signature, memo keys, a new payload-form record kind with a two-pass search, about 16 record keys, structure_inputs, the summary subsection, the thickness figure (which needs a visual review) and two new slow pins. It also leaves out deliverables that exit criterion 6 needs. OFFLOAD_SWEEP_COLUMNS has no dm, DLF, n_peak or set column, so the three stroke sweeps could not report dm per point. The arms' record has no dm column either. Neither appears anywhere in 4.4 or the step table.

Evidence: Design line 536 and lines 319-337. src/launchsim/results_io.py 1841-1856 (OFFLOAD_SWEEP_COLUMNS: status, offload_kg, ... n_flags; no structure field), 1593 (_offload_arm_record), 2035-2040 (sweep_index columns per case). S03 lines 86 and 93-94 recommend both columns. SP2 split steps of this size (A3/A3b, A4/A4b; SP2 lines 1918-1930).

Recommendation: Split S3 into S3 (config field and refusals, transform and builder, verification with dm, memo keys, record keys, the 0.002 kg pins, byte identity without a structure block) and S3b (the payload form, structure_inputs, the Structure subsection, conditional structure columns in sweep_index.csv and the arm records, and the thickness figure, with visual and honesty reviewers). Add the sweep and arm columns to the file table, conditional on a structural case so the 1-D tier and the output capture stay as they are.

## D7 [major] (5 gate column; 7) favours_assist=False

Issue: Several gates cannot be checked by an independent agent. S3's 'without a structure block every output byte-identical' names no run, command or comparison: the planar output capture checks structure, not values. S4a's 'the replay and scene pages of a linear-motor run looked at' names no run, no way to make it (a CLI run without --results-root writes into the repository's results/, whose summary.md is tracked) and no pass rule. S1's 'each closed form against a hand-computed value' has no tolerance. S2's 'the sizing-only table' has no defined content. S6 does not have the gate recompute the linear-motor rule numbers (F_max, P_max, t_r) from the closed form, or the frozen sets from the code, which is the check that guards against tuning.

Evidence: Design lines 534-544 and 588-599. src/launchsim/cli.py 92 and 110: run and sweep accept --results-root, but the design never says to use it outside app runs (line 527). Protocol 4.4 requires a gate an independent agent can check. SP2's gates named runs, times and tolerances (SP2 lines 1238-1251).

Recommendation: Write each gate as a command plus a tolerance. S3: run 'launchsim run experiments/silo_offload_2d_readme.yaml --results-root <scratch> --no-plots' at the start commit and at S3's commit, then diff metrics.json and summary.md ignoring timestamp and git. S4a: a scratch lm_cold_target-like file outside experiments/, run with --results-root <scratch>; replay and scene pages written into the scratch folder; a visual reviewer checks that no constant acceleration is claimed, that the exit speed is the measured one and that the drive clause is present, against metrics.json. S1: 1e-12 relative, with CLAUDE.md's bound quoted where one exists. S6: an independent recomputation of the rule's numbers to 1e-12 relative and of the sets.

## D8 [major] (3.2 D-SP7-15; 4.3 'sets'; 6) favours_assist=False

Issue: The frozen sets are to be 'written into the structure file with the commit that computed them'. The file is committed in that same commit, and a file cannot contain its own commit's hash (the protocol states the same limit for the closing commit). The code that flies the pad baseline and SP1's headline push for the corner search has no home: structure.py is pure, and S2's files (structure.py, config.py, cli.py, configs/structures/) include no runner. That points to a scratch script, which would make the sets impossible to reproduce from the repository. Nothing re-checks the sets after S3-S5 change the push path, the load-case builder or structure.py in fix rounds. No exit criterion covers them.

Evidence: Design lines 105, 239-241 and 254-256. SESSION_PROTOCOL.md lines 249-253 (a file cannot hold the hash of the commit it is in). S2 row, line 535.

Recommendation: Record the parent commit and a committed command or slow test that rebuilds the sets: it flies the pad and the headline push, runs the screened corner search (D1) and asserts the file's sets. Run it in S6's gate and in the exit gate. Add an exit criterion: 'the frozen sets equal a fresh recomputation at the S6 commit'.

## D9 [major] (2; 4.5; 4.6; 6 crit. 3) favours_assist=False

Issue: KI-038's fix and the gallery criterion conflict. S4a's KI-038 adds 'the renderer's version and git state' to the scene page. After S4a, the gallery's scene page (pad-vs-silo-offload-scene.html) cannot regenerate byte for byte, because the git state differs at every commit. The only regeneration gate is S3a, which comes before S4a, so exit criterion 3 ('six gallery pages byte-identical on regeneration') would fail at the close. The owner is also misassigned: S3a edits scene.py (structure_note), so KI-038's rule ('the phase that next edits scene.py') fires at S3a, not at S4a as section 2 says.

Evidence: TODO.md 355 (KI-038: the scene page names only the run directory's git, 'unlike the replay page's meta'). src/launchsim/replay.py 1819-1821 (meta has the run's git and __version__). Design line 75 ('KI-038 (S4a edits scene.py)'), lines 537 and 540, and lines 355-358 and 562-563.

Recommendation: Define KI-038's fix in the design: either the version only, which keeps pages stable, or the version plus git, with the scene gallery page's expected one-line diff recorded. Regenerate the gallery after the last change to replay or scene code (S4a, or S7b from D2), not only at S3a. Rewrite exit criterion 3 to name the expected diff. Assign KI-038 to the first step that edits scene.py.

## D10 [major] (5 S1, S2, S3, S4a; 6 crit. 8) favours_assist=False

Issue: docs/physics.md appears only in the S4 and S5 rows. S4a adds a terminal event (sdot = v_release), changes TrackExit and changes the facility-length rule. CLAUDE.md requires physics.md in the same change for events. S1, S2 and S3 add the structural model, the DLF, the flags and the offload coupling, all of which exit criterion 8 needs in physics.md, but none of those rows lists the file. The independent gate of each step therefore has no physics.md check to hold the implementer to.

Evidence: Design lines 534-541 and 580-581. CLAUDE.md, 'Working rules': 'Use Plan mode for anything touching equations of motion, frames, events ... and update docs/physics.md in the same change.' Protocol 4.1.

Recommendation: Add physics.md (the section and the test-map rows) to the files and gates of S1, S2, S3 and S4a. Make 'physics.md section and test-map rows present for this step's tests' a standing gate on every code step.

## D11 [major] (5 (loop); 8 'Run time') favours_assist=False

Issue: The design budgets only compute (about 20-60 min of runs). It gives no estimate of session effort for 12 steps, though effort is the binding constraint. SP2's session log shows three review passes and three fix rounds on nearly every step (A1a, A2, A3, A3b, A4, A4b, A5, A6v, A7). The protocol and this design say 'up to two fix rounds', and SP2 never logged the excess as a deviation. Usage limits stopped SP2's agents twice. The plan also calls for six or more full-suite runs (after S3, S4, S4a and S5, before the close, and at the exit gate), each 15-51 min under load, with more slow tests to come (S09 section 4: +4-12 min). No in-progress handoff point is named, though SP2's plan had one.

Evidence: SP2 phase file lines 1708-1876 (for example 'three passes; three fix rounds' at 1725-1727, 1744-1745, 1779-1780, 1805-1807 and 1822-1823) and 1887-1891 (full suite 51 min, 28 spurious 0xC0000142 failures). SESSION_PROTOCOL.md line 115 ('Up to two'). Design lines 517-521 and 613-614. SP2 line 1259-1260 ('An in-progress handoff is written at a checkpoint').

Recommendation: Add a session-effort estimate per step from SP2's measured rhythm, about 13 steps over 3 days. Either amend the protocol to SP2's practice (a third round for minors, logged) or size steps so that two rounds suffice. Run full suites in the background while reviewers work. Run S0 (documents only) in parallel with S1. Name checkpoint 1 and checkpoint 2 as in-progress handoff points.

## D12 [minor] (4.10 A (sweeps); 4.10 budget) favours_assist=False

Issue: File A declares only silo_cold (3 g0 net), so a stroke sweep 'of' it varies the exit speed at 3 g0 (SP1's sweep 1), not 'the fixed exit speed 76.70717046013364 m/s'. SP1's fixed-speed sweep needed a variant with exit_speed_mps (silo_cold_200m). Separately, 'three sweeps' for three sets flies 12 point runs where 4 would do: a sweep's offload list may name several cases.

Evidence: experiments/silo_offload_2d.yaml (silo_cold_200m with exit_speed_mps; sweep 2 'of: silo_cold_200m'). src/launchsim/config.py 2080-2084 (a sweep's offload names cases of the block, each once, several allowed). Design lines 442 and 461-463.

Recommendation: Add the exit-speed variant to file A, with the same assist block as silo_cold_200m and a 100 m stroke or SP1's 200 m. Declare one sweep 'of' it naming the central, low-mass and high-mass structural cases. Re-cost: +1 S in run A, -8 S in the sweep command.

## D13 [minor] (4.4 (inner iteration); 4.10 budget) favours_assist=False

Issue: The inner iteration runs 'until |dm_k+1 - dm_k| < 1e-6 kg or six iterations (contraction about 0.05, S03)'. S03's 0.05 is the outer x-dm fixed point (option ii), not this inner loop. At 0.05 the cap always stops the loop before the tolerance is met: the steps are 2000, 100, 5, 0.25, 0.0125 and 6e-4 kg. The design does not say what happens at the cap: whether a flag is raised or a value is recorded. The per-evaluation cost of sizing dense push samples × N stations × iterations is also unmeasured and missing from the run budget. S09 assumed it adds nothing.

Evidence: Design lines 295-297. S03 line 44 ('The fixed point contracts by about |E dm'|, roughly 0.05': the outer loop), line 134 (the inner loop) and line 155. Timed the probe's push-only sizing: 18.3 ms per iteration for a single sample at 200 stations, while the 618-sample envelope takes about 1.5 s. Dense push output means tens of samples.

Recommendation: Measure the inner contraction and the per-evaluation sizing time in S3's gate. Set the cap from the measured contraction, for example 10 iterations. Make reaching the cap a recorded flag. Add the measured sizing time to the S6 runtime estimate.

## D14 [minor] (4.9; 5 S1, S2, S4, S6) favours_assist=False

Issue: Several dependencies between steps can trip a step's tests or behaviour. (1) S1 makes the docstring check strict and D-SP7-26 adds assist/linear_motor to PHYSICS_MODULES and RUN_PATH_MODULES, but that file does not exist until S4, and the AST guard fails on a missing file. (2) S4's LinearMotorConfig accepts release_speed_mps while S4a's event does not exist yet, so a run would silently release at L. (3) S1's 'Delta_gamma table read-back' needs the digitised table, which first exists in S2's structure file; the digitisation itself has no accuracy check. (4) It is unclear whether S2 or S3 adds the experiment-level structure block and the offload-case field. (5) S6's resolved fixture in tests/test_config_planar.py must pass load_structure for the new files.

Evidence: Design lines 432-435, 366, 534-536 and 543. S09 section 2 (the AST part fails on a missing file, test_scene.py 1380-1381). tests/test_config_planar.py 62-69 and 880-890.

Recommendation: Stage the lists: structure in S1, assist/linear_motor in S4. Refuse release_speed_mps until S4a, or move the field to S4a. Put the digitised table with its source points in S0's note, and check it in S2 against labelled points of SP-8007 Fig. 6. Name the step for each config addition. Add the fixture change to S6's tests.

## D15 [minor] (6) favours_assist=False

Issue: Items are missing from the exit criteria. KI-030, which is medium severity and owned by SP7 (brief scope item 9), has no criterion, and neither do KI-035, KI-038 and KI-021 to KI-023. Only KI-039 and KI-036 appear (criterion 7). There is no criterion that the app's basis stays valid: brief entry criterion 8, app.sp1_files_same true, and the SP1_HEADLINE preset reproducing 41,262.908 kg after KI-030's strict validators. There is no check that current public text no longer says 'no structural model exists', and none for the frozen sets (D8). There is no 'changes against the brief's 10' list, which S09 1.3 names as part of the template and SP2 gave (D-SP2-38).

Evidence: Design lines 551-586. Brief lines 93-101 (KI-030 in scope) and 240-252 (entry criterion 8). TODO.md 347, 352, 355 and 314-322. SP2 phase file line 1931 ('17 instead of 14' with the changes listed).

Recommendation: Add four criteria: (a) KI-030, KI-035, KI-038 and KI-021 to KI-023 closed, with S02's 16-case refusal table refused and the digests unchanged; (b) the app's basis unchanged and the app's slow launch reproducing 41,262.908 kg within 0.002 kg; (c) 'git grep -n "no structural model exists"' matches only dated or archived records; (d) the frozen sets recomputed. Add the change list against the brief's criteria 1-10, for example criterion 3's tolerance going from 3.8 kg to 0.002 kg.

## D16 [minor] (5 (reviewers); 4.4 Summary/Figure; 4.6 readers) favours_assist=False

Issue: Reviewer coverage leaves gaps. S3 writes new reporting text: the Structure subsection, the band sentence ('the bounds of the stated coefficient ranges'), flag wording and figure labels. S4a writes new summary rows and the linear-motor drive clause. The honesty auditor is named only for S0, S3a, S6 and S7, and 'every caveat or label reworded' does not clearly cover new text. The app's run browser and results panel, which list every directory under results/, are not checked against structural or linear-motor directories, and app.py is not in S4a's files.

Evidence: Design lines 517-520 and 329-337 (the band line). SP2's A4b gate: 'the repository's results folder lists read-only with every directory's state and no 500' (SP2 lines 1797-1801).

Recommendation: Put the honesty auditor on S3, S3b and S4a. Add to S4a's gate: the app, started with a scratch root holding a structural directory and a linear-motor directory, lists and plays both with no 500, and the panel's wording follows the three-way branch.

## D17 [minor] (4.11; 5 S7; 7; brief 9) favours_assist=False

Issue: The design has no demo section of its own. The brief's demo asks for 'the linear-motor run: drive force against speed (force limit, then power limit)', but no planned plot draws force against speed: plots.py has only a force-against-time panel. S7's 'derived figures' name no command, so the figures in the findings note could come from scratch scripts that are not in the repository. CLAUDE.md's layout needs lines for structure.py and configs/structures/. The protocol's standing gotcha 'no structural mass charged for the 4 g push' (SESSION_PROTOCOL.md 440-442) has to change once SP7 charges one, and the design does not plan that edit.

Evidence: Brief lines 872-901. src/launchsim/plots.py 89 ('track_forces': drive and interface force against time). Design lines 544, 588-599 and 545. SESSION_PROTOCOL.md 440-442.

Recommendation: Add a demo section modelled on docs/demos/SP1/README.md: console captures of the four commands with start and end times, the Structure subsection, the stroke table, and a linear-motor replay and scene with hyphenated names. Add a force-against-speed figure to S4a's plots, or drop the demo item. Produce the derived figures with a committed function or script, named in the note's Reproduction section. List the CLAUDE.md layout lines and the protocol gotcha edit in C.

## D18 [minor] (4.2.4) favours_assist=True

Issue: The brief says the plausibility check's 'large disagreement is reported and widens the band'. The design keeps the report but drops the widening ('it changes no coefficient') and does not list this among its changes against the brief. If the model's envelope masses come out well below the real tank and skirt masses, the model probably under-sizes the push increment too, and with no widening the band stays narrow.

Evidence: Brief lines 365-367. Design lines 228-231. S06: Heineman's relation is good to +/-30%.

Recommendation: Restore the brief's rule with a threshold fixed before any flight, for example 'if the envelope mass falls outside the Heineman +/-30% band, the high-mass set's breakdown or NOF is widened by the ratio and said so'. Otherwise list the change and report the ratio beside the headline.

## D19 [minor] (4.10 budget; 8) favours_assist=False

Issue: The compute budget holds at set M. My count gives: run A 3 S + C1 + 16 V + 6 S (payload) + 6 (S + O) arms + about 30 directories, about 17.5-23 min (38-55 min at P), once D12's variant is added. Run B 8 S + C1 + 14 V, about 11-14.5 min. Sweep, as three sweeps, about 11-15 min. Run C about 2.5-3 min. But set M was measured with three concurrent commands and nothing else running. SP2's close shows parallel gates and suites stretching the full suite to 51 min and causing 28 spurious subprocess failures. The design says nothing on keeping the machine quiet during S7, and gives no per-solve timing record, which the run command does not write.

Evidence: S09 3.1-3.2 (set M; 32 logical processors; the run command writes all directories at the end). SP2 lines 1887-1891. Design lines 488-490.

Recommendation: Keep the estimate, and add the run rules: no test suite or app-driving agent runs during S7's commands; record each command's start time and each directory's last file time in the note's Reproduction section; re-cost with D12's change.
