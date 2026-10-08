<!-- Record of SP7 step 0: independent adversarial review (compliance-process) of design draft v1 (draft-v1.md in this folder), made by a workflow agent on 2026-10-08 at HEAD 22c62e9 and rendered from its structured output. The disposition of every finding is appendix A of ../2026-10-08-SP7-design.md. Not edited. -->

# Review: compliance-process

Compliance-process lens. The draft follows most of the protocol's form: start checklist, decision ids, step loop, standing gates, a pre-registration in S6 and a clean-commit run in S7. I checked its git and inventory claims at 22c62e9 and they hold. Several gaps break CLAUDE.md or SESSION_PROTOCOL.md rules, and some of them bias the result toward a larger offload.
(1) The central dynamic load factor for the constant_accel headline comes from a rise-time rule (t_r = 10 T_low/pi). That rule is derived from the target DLF <= 1.10. No source supports it, and the drive as flown is a step whose honest DLF is 2 (S08 line 66). The central headline is therefore quasi-static by construction.
(2) The "step bound" row, and every row that trips structure_upper_stack_exceeded, is a lower bound on the added mass, yet it is labelled a bound.
(3) The corner band is not computable "in seconds": 2^22 to 2^24 evaluations. Its corners need not be the extremes of a non-monotone increment. It is frozen at one push and reused at other strokes and drives. Its producing code, provenance and self-referencing commit are unspecified.
(4) docs/physics.md is missing from S1, S2, S3, S3a and S4a, although S4a adds an event and S3 changes the offload, decomposition and quoted assumption lines.
(5) Validation-first gaps. The structural coupling under linear_motor (hot, sealed shaft), the sweep and arm paths with structure, the braking functions, the early-release facility length, the flags and linear-motor convergence have no listed test, yet experiments use them.
(6) Checkpoint 1 and S3's tests can reveal the structural headline before pre-registration, and no freeze or amendment rule covers the structure files.
(7) Honesty review is missing on the steps that write new summary text.
(8) Modelled braking was shrunk to closed forms against the brief and the user's Q4 answer without being put back to the user.
Smaller items: scope additions not surfaced, units.py coverage, structure.py purity, magic numbers, the docstring test-map row, the deferral of mandated sensitivity arms, KI-038 against gallery byte-identity, tracker upkeep, reporting columns, CLI semantics, and S0 review coverage.

## C1 [major] (3.2 D-SP7-12, 4.2.1, 4.10 (linear-motor rule)) favours_assist=True

Issue: The constant_accel headline gets a central DLF from a rise time t_r = 10 T_low/pi. That value is derived from the target 'DLF <= 1.10 at the lowest frequency', not from a source; S07 section 5 says no catapult rise time is published. The model flies constant_accel as a step: infinite jerk, full acceleration from t = 0, no ramp cost. Its structure, however, is credited with a ramp of about 1 s on a 2.6 s push. The justification 'keeps the ramp's own cost under 1% of F_max' applies only to a drive that flies the ramp. S08 line 66 states the honest DLF for constant_accel as modelled is 2. The probe shows the DLF is the largest driver: 8.7-31.8 t of offload at DLF 1.1 against 0-20.2 t at DLF 2. The central headline is therefore quasi-static by construction, which breaks 'never tune parameters to make an assist look better'.

Evidence: design lines 92 (D-SP7-07), 102 (D-SP7-12), 200-204, 478-483; S07 lines 171, 188-191; S08 lines 66, 214-217; src/launchsim/assist/constant_accel.py assumption 'infinite jerk at push start and release' (S07 line 58)

Recommendation: Put this to the user as a question, because it changes what D-SP7-07 means. Either (a) make the constant_accel central DLF the drive as flown (2; 1.94 only if damping is sourced), with the rise-time row labelled 'if the drive ramped over t_r (not flown)'; or (b) make the structural headline a drive that actually flies the ramp (lm_cold_target), with the constant_accel rows beside it. If the rule stays, the pre-registration and the note's first caveat must say 'the central DLF is <= 1.10 by construction of the rise-time rule; the push as flown has DLF 2', and the step row goes into the headline sentence.

## C2 [major] (3.1 D-SP7-07, 4.2.2, 4.10 A (_st_step), sweeps) favours_assist=True

Issue: At DLF 2, n_peak = 0.998 + 2 x 2.998 = 6.99 g0, above MECO's 5.195 g0, so structure_upper_stack_exceeded fires. Stage 2, the interstage and the adapter are then unsized, and the design itself says 'dm is then a lower bound'. Yet D-SP7-07 and the 4.10 table call the step row 'a bound row' / 'step bound'. The same applies to the 50 m sweep point (7.0 g0, quasi-static). A lower bound on mass labelled as a bound in summaries, the note and public text overstates how pessimistic the row is.

Evidence: design lines 92, 207-210 ('Happens for DLF > 1.40 ... dm is then a lower bound'), 453, 461-462; S08 line 66 ('its DLF 2.0 rows are low')

Recommendation: Label every flagged row 'lower bound on dm (upper stack not sized); its x* is an upper bound on the offload' in the records, the Structure subsection, the note and public text. The pre-registered reading of _st_step should treat it that way. Optionally add a labelled, crude upper-stack increment row, or ask the user.

## C3 [major] (4.2.5, 3.2 D-SP7-15, step S2) favours_assist=True

Issue: (a) Section 4.2.5 lists about 22-24 coefficients, which gives 2^22-2^24 (4.2-16.8 M) corner evaluations. Each one re-evaluates the pad envelope (thousands of samples) and the push at N stations with a monocoque root solve, so 'seconds' is off by orders of magnitude. (b) The increment is max(0, t_push - t_env), a difference of two functions of the same coefficients, and the design itself says effect directions flip, so the extremes over the box need not lie at corners. 'The bounds of the stated coefficient ranges' may then be false, and the high-mass end may understate the maximum. (c) The corners are chosen at one push (100 m, 3 g0, cold, x = 41.26 t) and reused at x*, at the 50-300 m strokes and for the linear-motor drives, where the governing mode changes with n. The band label is unverified at those points.

Evidence: design lines 105, 233-242, 463; computation run: 2^22 x 1 ms = 69.9 min, 2^24 x 1 ms = 279.6 min, 2^24 x 0.1 ms = 28 min

Recommendation: Count k exactly. Reduce it by grouping coefficients that cannot vary independently ((C, n), the densities, p_u with p_u,min) and by dropping coefficients that do not act in the evaluated row (k_ts under aft_ring). Measure and record the S2 runtime. Check extremality, for example with interior random samples or a bounded optimiser, and report the largest excess found, or relabel the band as 'the extreme corners found'. Re-run the sizing-only search at each stroke and drive, or label the band there as 'corners chosen at the headline push'.

## C4 [major] (4.3 (sets), D-SP7-15, step S2) favours_assist=False

Issue: No module, command or test is named that computes the frozen sets and writes them into configs/structures/*.yaml. structure.py is pure and cannot write, notebooks/ is 'nothing experiments depend on', and no new command is in scope. The file is to name 'the commit that computed them', but the sets are written in that same commit, which cannot contain its own hash. The probe's push and envelope came from untracked results/ CSVs; if S2 reuses them, a fresh clone cannot reproduce the sets, and any test doing it would read results/, which section 5 forbids. The S2 test only checks that 'the sets are corners', not that they are the minimising and maximising corners. The push that sizes the README-loads file's sets is unspecified.

Evidence: design lines 105, 255-256, 535; SESSION_PROTOCOL.md 249-253 (a file cannot contain its own commit hash); CLAUDE.md layout (notebooks/); S08 line 3 ('the recorded pad envelope and the recorded silo_cold_s1 push'); src/launchsim/results_io.py 447

Recommendation: Put the search in structure.py as a pure function returning the sets. Call it from a slow test that flies the pad and the headline push from the committed experiment and asserts the file's sets equal the recomputed ones. Record the parent commit and the test name in the file. Name the push used for the fork's file.

## C5 [major] (5 step table S1, S2, S3, S3a, S4a; 4.1) favours_assist=False

Issue: CLAUDE.md requires docs/physics.md in the same change for anything touching events or loss accounting, and in sync with the code generally. Five steps break this. S4a adds the target-speed release event and the release position and mapping, but lists no physics.md. S3 changes the offload definition (dry mass becomes dm(x)), the verification and the cross-vehicle decomposition's dry-mass term, and adds assumption lines, but lists no physics.md. S3a rewords sim.offload_penalty_assumption, which physics.md quotes verbatim, also without physics.md. S1 and S2 build the structural model with no physics.md section until exit criterion 8, so their reviewers have no derivation to check against.

Evidence: design lines 534-537, 540, 580-581; docs/physics.md 2009 (Propellant offload), 3243 (Cross-vehicle decomposition), 5997-6000 (quotes sim.offload_penalty_assumption); CLAUDE.md Working rules

Recommendation: Add docs/physics.md to the Main files and the Gate of S1 (primitives, DLF), S2 (stations, envelope, increment, flags), S3 (coupling, payload two-pass, decomposition dm, assumption lines), S3a (the quoted sentence) and S4a (release event and mapping), with test-map rows added beside each test.

## C6 [major] (5 (S3-S5 tests), 6 criterion 1, 4.10 B) favours_assist=False

Issue: Experiment B flies a central structural solve on every linear-motor variant, but no step tests the structural transform on a linear-motor push. Untested pieces: F_0 from at_push_start, the DLF from the drive's own t_r, sampling at ramp end, corner and release, the hot-start resting state, F_int with thrust on the track (lm_hot), and the sealed-shaft force (lm_sealed). The S3 coupling tests are constant_accel only. Also untested before use: the sweep path with structure (three stroke sweeps), arms that re-fly the perturbed pad envelope, and the braking functions (S4 builds them, but its Tests column lists none; brief 5.9 line 495 requires distance and time). The facility length max(L, s_release + d_brake) after an early release and the two flags are also untested. The CLAUDE.md convergence test is never run on a linear-motor run with its new kink and corner events. Exit criterion 1 cannot catch tests that are not listed.

Evidence: design lines 302-305, 413, 465-476, 536-541, 553-554; brief SP7 line 495; CLAUDE.md 'Validation first' (convergence, 'No physics feature is used in an experiment until its test passes')

Recommendation: Add these tests to S4, S4a and S5 before S6: a structural case on short linear-motor pushes (cold, hot, sealed) with n_peak, F_peak and DLF checked against closed forms; braking distance, time, force and energy; the facility length for an early release; both flags against hand thresholds; a slow end-to-end sweep and an arm with a structure block; a linear-motor convergence test (10x tolerances moving P* or x* by < 0.1%).

## C7 [major] (5 checkpoint 1, S3 tests, 4.10 pre-registration, D-SP7-15) favours_assist=True

Issue: Checkpoint 1 ('the structural headline can be produced from an experiment file') sits before S6. S3's slow tests (xv_dry_mass_delta_kg = dm(x*), the payload two-pass check) may also fly central structural solves on the gate vehicle. The structural headline can therefore be known before the readings are registered, while the structure files stay editable. Three rules are missing: a freeze rule for the structure files after S2 (only 'before any flight'), an amendment rule for changes after S6 (configs/ is a pre-registered path), and a requirement that the pre-registration disclose any structural x* seen in S3-S5. Its 'already known' list names only the probe and S2's sizing-only dm.

Evidence: design lines 105, 494-496, 536, 538; src/launchsim/results_io.py 447 (PREREGISTERED_PATHS = configs, experiments); SESSION_PROTOCOL.md 148-150; SP1 pre-registration section 2 'The headline is not unknown' (S09 1.4)

Recommendation: Define checkpoint 1 as resolve plus preflight plus a non-headline short case. Have S3 tests use non-headline settings or synthetic vehicles; otherwise disclose every structural x* computed before S6. Freeze the coefficients at S2's commit, and log any later change as a decision (before S6) or an amendment (after). Record both structure files' sha256 in the pre-registration.

## C8 [major] (5 (reviewers per step)) favours_assist=False

Issue: The protocol requires an honesty auditor on findings and summaries. The design assigns one only to S0, S3a, S6, S7 and 'every caveat or label reworded'. Steps that write new text are left out: S3 writes the Structure subsection, the band line 'the bounds of the stated coefficient ranges, not a confidence interval', the assumption lines and the payload-case record. S4 and S4a write new metric names and summary rows (push_accel_mean_mps2 'named a mean', the always-present drive clause, the scene push labels). S5 writes 'stated, not modelled' assumption lines. None of this text is a rewording, so none of it gets an honesty review.

Evidence: design lines 517-519, 329-334, 388-395, 418-421; SESSION_PROTOCOL.md 110-112

Recommendation: Add the honesty auditor to S3, S4, S4a and S5, or restate the rule as 'every new or reworded sentence of a summary, caveat, label, metric name or assumption line'.

## C9 [major] (3.2 D-SP7-21, 4.8, 8 (B-007 re-target)) favours_assist=False

Issue: Brief scope item 6 is 'Modelled carriage braking after release (distance, time, energy) instead of the closed form added to the facility length', and the user's Q4 answer keeps braking in. D-SP7-21, a design decision 'approved with the plan', reduces this to closed-form functions, which is what constant_accel already has. Section 8 then re-targets B-007's braking to SP7 as if it were delivered. Shrinking a user-confirmed scope line is a deviation that must be put to the user and recorded in section 12.

Evidence: brief SP7 lines 82-87 and 913 (Q4); design lines 89 (D-SP7-04), 111, 409-412, 616-618; src/launchsim/assist/constant_accel.py 166-171 (v^2/(2 a_brake) already exists); SESSION_PROTOCOL.md 181-186

Recommendation: Ask the user explicitly: closed-form braking functions or a modelled braking phase in the trace. Record the choice in section 12. Keep B-007's 'modelled carriage braking' open (later) and re-target only what SP7 builds.

## C10 [minor] (3.2, 4.1, 4.4, 4.6, 9) favours_assist=False

Issue: The design adds deliverables the brief lacks without listing them for approval. They are: tests/data/silo_offload_2d_record.json (copied from an untracked metrics.json, with no provenance test like the screening record's); a thickness-profile figure for every structural case; new record kinds (structure_inputs, the payload-case record); the renderer's version and git state on the scene page (KI-038); the corner search and tornado; steps S3a and S4a; two checkpoints. It also silently drops the brief's propagated one-at-a-time structural sensitivities (brief 5.6; S09 G2) in favour of a sizing-only tornado. appform.py 187 builds ASSIST_UNION_TAGS from PLANNED_MODELS, so the 'one tuple of union tags' means editing appform.py. The 4.1 file table omits that file, and the edit sits awkwardly with D-SP7-08 ('App form: no change').

Evidence: design lines 115, 131, 141, 313-326, 336-337, 394; src/launchsim/appform.py 187; tests/test_planar_pipeline.py 1290-1322 (provenance check of the existing record); brief SP7 lines 406-411; SESSION_PROTOCOL.md 181-185

Recommendation: Add a 'Changes against the brief' section listing every addition, removal and shrink for the user's approval and for section 12. Add appform.py and its test to the file table. Add a provenance test for the new tests/data record.

## C11 [minor] (4.3, 4.1 (units.py), 4.2) favours_assist=False

Issue: units.py converts only deg, km, kN, t, g, kWh, kPa, MJ and percent. The design adds only mw_to_w, but the structure file will carry moduli and strengths (GPa, MPa), pressures, thicknesses (mm), k_entry (kg/MN), k_ts (kg/kN) and a frequency (Hz). The range-quantity fields have no unit suffix in their names (nof, k_entry, f, t_min), and the new figure will label thickness in mm. CLAUDE.md makes units.py the only place conversion factors appear and requires unit-bearing names. The station coordinate z ('up from the load ring') also clashes with the track frame's z.

Evidence: src/launchsim/units.py 24-100; src/launchsim/compare.py 86-102 (SI_SUFFIX_CONVERSIONS); design lines 132, 152, 233-235, 249-258; CLAUDE.md Conventions and Layout (units.py)

Recommendation: Give every structure-file field a unit and a suffix (E_GPa, F_tu_MPa, t_min_mm, k_entry_kg_per_MN, axial_frequency_Hz, and so on). Add the conversions to units.py and, if any field can enter a sensitivity table, to SI_SUFFIX_CONVERSIONS. Name the station coordinate station_height_m and document its frame in physics.md.

## C12 [minor] (4.1, 4.2 (structure.py)) favours_assist=False

Issue: structure.py builds 'load cases from a flown push or a Result'. sim.Result is defined in sim.py, which imports plots and results_io, and sim must also import structure for the transform builder. That creates an import cycle and puts I/O modules in a pure module's import graph. Parameter objects are not stated to be frozen dataclasses.

Evidence: src/launchsim/sim.py 627 (class Result), 200-222 (imports plots, results_io); design lines 128, 291-297; CLAUDE.md Code style (pure physics functions, frozen dataclasses)

Recommendation: Have structure.py take RunTrace/StateView arrays or its own frozen LoadCase dataclasses, with the Result-to-LoadCase adapter in sim.py. Convert StructureConfig to frozen dataclasses at the boundary. Assert in RUN_PATH_MODULES or an import test that structure.py imports no I/O module.

## C13 [minor] (4.4, 4.9, 4.2) favours_assist=False

Issue: Several thresholds are bare literals: the KI-030 bounds (+/-3600 s, +/-500 m), the fixed-point tolerance (1e-6 kg) and its six-iteration cap, the payload two-pass flag (0.05 kg), the SP-8007 constants (0.901, 16) and the rise-time rule's 10/pi. CLAUDE.md forbids magic numbers outside constants.py and configs. Nothing flags a fixed point that fails to converge in six iterations. The 0.05 kg two-pass flag equals final_payload_xtol_kg, so it would fire on search noise.

Evidence: design lines 102, 178-181, 294-296, 314-316, 427-428; experiments/silo_offload_2d.yaml 44 (final_payload_xtol_kg: 0.05)

Recommendation: Make each a named constant with its source. Add a flag such as structure_fixed_point_unconverged. Set the two-pass flag above the search resolution (for example 2 x final_payload_xtol_kg) and state why.

## C14 [minor] (4.9 (D-SP7-26)) favours_assist=False

Issue: The docstring check only tests that a docstring exists, and it silently skips missing paths. physics.md's test map claims it verifies 'every public physics docstring states inputs, outputs, units and frame | exact'. D-SP7-26 fixes the skip but leaves the false row in place, so the docstrings of structure.py and linear_motor.py will be checked only for presence against CLAUDE.md's content rule.

Evidence: tests/test_scaffold.py 81-84; docs/physics.md 6469; CLAUDE.md 'Every physics function's docstring states inputs, outputs, units and frame'

Recommendation: Either reword the row to 'has a docstring', or extend the check for the new modules (for example require input, return and unit statements). Have the compliance auditor check docstring content in S1, S2, S4 and S5.

## C15 [minor] (5 ('If room runs out')) favours_assist=False

Issue: The last item on the cut list, 'the arms beyond stage-1 dry mass and C_D', drops the Isp and drive-efficiency arms that CLAUDE.md requires for every headline. Drive efficiency is energy-only, so that arm reuses the nominal solve and cutting it saves nothing. The margin rows on the same list are the user's own answer (D-SP7-03).

Evidence: design lines 456, 547-549, 132; src/launchsim/compare.py 1744 (ENERGY_ONLY_ASSIST_KEYS); CLAUDE.md 'Headline numbers get a sensitivity check'

Recommendation: Take the CLAUDE.md arms off the deferral list, or mark cutting them as an exit-criterion miss that needs a logged acceptance. Always keep the efficiency arm. Note that cutting the margin rows would reverse D-SP7-03.

## C16 [minor] (4.5, 4.6 (KI-038), 6 criterion 3) favours_assist=False

Issue: S4a adds the renderer's version and git state to the scene page (KI-038), so pad-vs-silo-offload-scene.html will no longer match S3a's byte-identical regeneration. S4a's gate does not regenerate it, and exit criterion 3 still expects byte identity. A page rendered during S4a would also name the parent commit and a dirty tree.

Evidence: TODO.md 355 (KI-038: 'not the renderer's version and git state, unlike the replay page's meta'); src/launchsim/replay.py 1821 (version in meta); design lines 355-358, 394, 562-563

Recommendation: Regenerate the scene gallery page after the S4a commit (in its own commit, or at the close), record the diff, and define what the renderer's git state means on a committed page.

## C17 [minor] (10 (first actions), 8, close) favours_assist=False

Issue: Several tracker and document updates are missing. First actions update the phase file's sections 3, 7, 8 and 10, but not section 6 (protocol 3 item 5 wants the inventory corrected before planning; the design's section 9 holds the corrections), section 2 ('Plan mode confirms each line'), or the section 9 demo script. Survey 09 is dated 2026-10-07 but would be filed under 2026-10-08. D-SP1-03 ('dry masses unchanged except a penalty') is amended by the modelled dm without being named. SESSION_PROTOCOL.md 440-442 requires the caveat 'no structural mass charged for the 4 g push' beside every gate-vehicle headline, which becomes false for SP7's headline. CLAUDE.md's assist-energy identity has no work_other term. Neither update is planned.

Evidence: design lines 644-653, 621-642; SESSION_PROTOCOL.md 75-77, 86-92, 303-308, 440-442; S09 line 3 (dated 2026-10-07); TODO.md D-SP1-03

Recommendation: Add to the first actions: section 6 corrections, section 2 confirmations and the section 9 demo names. Use the surveys' own date for their folder or explain the date. Name D-SP1-03 as amended in a D-SP7 entry. At the close, update the protocol's caveat line and CLAUDE.md's energy identity.

## C18 [minor] (4.4 (Summary), 4.6, 4.11) favours_assist=False

Issue: The Structure subsection omits DLF, n_peak and F_peak beside the trajectory's quasi-static felt g and interface force, so a reader sees 3.996 g0 while the structure was sized at a different n. CLAUDE.md requires a silo run to model the air column or state that the shaft is vented; the design keeps constant_accel's vented line but specifies none for linear_motor with shaft: vented. The findings note's outline also drops the KI-006 M2/M4 robustness disclosure that RQ1 carries.

Evidence: design lines 329-334, 366, 416-421, 502-512; CLAUDE.md Physics model item 2 ('state that the shaft is vented') and Experiments and reporting; docs/findings/RQ1-fuel-offload-2d.md 751-771; TODO.md 287 (KI-006)

Recommendation: Add DLF, n_peak and F_peak columns to the Structure subsection, a vented-shaft assumption line for linear_motor, and a KI-006 section in RQ1-structural-2d.md.

## C19 [minor] (4.3, 7) favours_assist=False

Issue: The design does not say what --no-offload and --no-sensitivity do with the new experiment-level structure block, its payload_cases and the structural arms. CLAUDE.md requires the commands list to stay accurate.

Evidence: CLAUDE.md Commands (--no-offload, --no-sensitivity); design lines 266-284

Recommendation: State the semantics (for example, --no-offload also skips payload_cases) and update CLAUDE.md's commands and the manual chapter 07-commands.md.

## C20 [minor] (5 (S0 reviewers)) favours_assist=False

Issue: S0 fixes every coefficient range, and those ranges set the band and largely the answer: the probe names k_entry and the DLF inputs as dominant. Yet S0 gets only an honesty review. No physics skeptic checks that the ranges are physically sensible and not narrower than their sources' spread.

Evidence: design lines 517-519, 533; S08 line 3 (DLF and k dominate)

Recommendation: Add a physics skeptic to S0 who checks each range against its source and anchors, and records any range narrower than the source spread with a reason.
