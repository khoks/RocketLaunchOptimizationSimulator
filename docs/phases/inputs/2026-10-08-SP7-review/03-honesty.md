<!-- Record of SP7 step 0: independent adversarial review (honesty) of design draft v1 (draft-v1.md in this folder), made by a workflow agent on 2026-10-08 at HEAD 22c62e9 and rendered from its structured output. The disposition of every finding is appendix A of ../2026-10-08-SP7-design.md. Not edited. -->

# Review: honesty

Honesty lens verdict: several choices are conservative and correctly argued. Those are zero margin, the quasi-static pad envelope with no DLF on the pad's own release step, uncredited damping, the aft skirt envelope taken at the 5.593 MN hold-down load rather than the 7.586 MN flight aft-station load (a larger increment), the three-way wording with its own record keys, and disclosing the probe. But the choices that set the headline lean toward the assist, and as written the band would be labelled "the bounds of the stated coefficient ranges" while the largest driver is removed by construction. Six problems drive this. (1) For constant_accel, the rise-time rule t_r = 10 T_low/pi fixes DLF at 1.03-1.10 whatever frequency range is assumed. t_r is not a band coefficient. The trajectory keeps its step, so the ramp's own cost goes uncharged: +1.07% F_max at 100 m (not "under 1%") and +5.3% at 50 m. And no ramp-down is modelled at all, although the design's own release flag says the LOX column separates. A ramp-down over the same t_r would cost +21% to +52% F_max (4.8-6.1 g0). (2) Rows the design calls bounds are not bounds. The step row and the 50 m stroke leave stage 2 unsized, the reason D-SP7-13 gives is false for the quasi-static 50 m case, and both exceed the published +6.0 g payload limit. (3) Some coefficients sit at the favourable end. NOF is central 1.5 with a low of 1.0, although the source's coarse-model values are 1.54-1.90. The k_entry central has no source and is fixed after the probe showed its leverage. (4) Sensitivity to the envelope runs one way only. It is the model's unthrottled MECO, S05's recommended MECO sensitivity was dropped, and margin is limited to >= 0. (5) Checks that could only hurt the assist have been weakened. The brief said the plausibility check "widens the band"; the design drops that rule and files the check in metrics.json. The "band wider than the offload" and "cancels most" triggers are undefined. The corner band misses interior maxima (S08's p_u), is frozen at one push, and its "seconds" runtime is implausible. (6) The pre-registration can be contaminated by S3 test solves, and there is no freeze on the structure file after S2. The release and upper-stack flags are missing from the note's caveats-first list. What would make the design neutral: carry t_r (or the DLF) in the band, or report constant_accel at its modelled step with the ramp case labelled as a different drive whose cost is charged; model or cost a ramp-down; size stage 2, or label those rows as upper bounds on x*; use coarse-fidelity NOFs; fix k_entry's central by a rule stated now; add a throttled-envelope row; restore the plausibility rule; search the full coefficient box; fix numeric reading triggers; freeze the structure file. Scratch computations are in C:/Users/rahul/AppData/Local/Temp/claude/D--DEV-ClaudeProjects-SpaceRocketOptimization/3e237173-2609-4e7b-ac46-15c1a393670f/scratchpad/a0/review/honesty/ (rampdown2.py, rampdown3.py, rampstroke.py).

## H1 [blocker] (3.2 D-SP7-12, 4.2.1, 4.2.5) favours_assist=True

Issue: For constant_accel, the structure is charged for a drive the run does not fly. t_r = 10 T_low/pi is set to hit a target outcome (DLF <= 1.10), so the dynamic charge nearly vanishes by construction. With T_low taken from the 3 Hz low end, DLF is 1.10 at 3 Hz, 1.06 at 5 Hz and 1.03 at 10 Hz; read per set as 10 T(f)/pi, it is exactly 1.10 at every frequency. Either way the frequency coefficient barely matters, and t_r is not in 4.2.5's coefficient list, so the band cannot reach DLF 1.3-2.0. S08 shows that range moves the offload from about 30 t to 0-20 t. The trajectory keeps its infinite jerk, so the ramp's own cost is never charged. The stated justification ('keeps the ramp's own cost under 1% of F_max') is false at the rule's own t_r = 1.061 s (+1.07% at 100 m) and at 50 m (+5.3%, felt 6.996 to 7.370 g0, 6% of the increment). The frequency anchors are free-flight modes (Saturn V 3.75 Hz at lift-off). A stack driven from its base on a carriage plausibly has a lower first mode (fixed-free is about half of free-free for a uniform bar; inferred), and at 1.5-2 Hz the same t_r gives DLF 1.15-1.20, outside the band.

Evidence: Design lines 102, 200-204, 233-235 (t_r absent from the band list), 43-45; S08 lines 66 and 240 (recommends constant_accel at DLF 2), 213-217 (coupled x* at DLF 1.1: 8.7-31.8 t; 1.3: 1.6-29.5 t; 2.0: 0-20.2 t); S07 lines 188-191, 226-244; src/launchsim/assist/constant_accel.py:224 ('infinite jerk at push start and release'); scratch rampstroke.py (closed-form kinematics, g_eff 9.772092): ramp cost +5.3/+1.1/+0.2/+0.1% F_max at 50/100/200/300 m

Recommendation: Pick one honest form and state it in D-SP7-12. (a) Report constant_accel at the DLF its trajectory implies (2, the step) as the modelled case, and make the ramped push a separate, labelled drive. Either fly it with linear_motor, or charge its quasi-static cost: the felt n after the ramp at the same (L, v_e), from S08 A1's closed forms. (b) Or keep the rule for the headline, but carry t_r as a ranged coefficient in the band: low end a short ramp (for example t_r = T_low, DLF up to 1.32, or 0.25 s), central the rule, high end the rule. The band's high-mass corner then holds the dynamic uncertainty. In every case: show t_r, DLF and n_peak in each Structure row of summary.md; give a structural constant_accel run an assumption line that reconciles 'infinite jerk' with the assumed ramp; correct the '<1% of F_max' claim; mark the free-flight frequency anchors as an assumption whose direction is unfavourable to the assist.

## H2 [major] (1 (Magnitude bullet), 3.2 D-SP7-12) favours_assist=True

Issue: The design's own summary of the probe, which the user approves, gives only the quasi-static range: 12-33 t, 30-80%. It leaves out the probe's DLF 1.3 range (1.6-29.5 t) and DLF 2.0 range (0-20.2 t). It also leaves out S08's explicit recommendation to report constant_accel at DLF 2. D-SP7-12 departs from that recommendation without saying so. The rise-time bullet, 'costs +0.2-0.9% of F_max ... brings the DLF from 2 to about 1.0-1.2', is one-sided: it counts the ramp-up only, at 100 m only.

Evidence: Design lines 35-40, 43-45, 102; S08 lines 3, 66, 213-217, 240

Recommendation: In section 1, add the probe's DLF 1.3 and 2.0 rows and S08's recommendation. In D-SP7-12, state why the design departs from it. Carry the same full table into the S6 pre-registration ('what is already known'), so readers see that the central's DLF is a choice that moves the headline by tens of tonnes.

## H3 [major] (4.2.2 structure_release_unload, D-SP7-13, 4.6, 4.11) favours_assist=True

Issue: No drive models a ramp-down, so the release flag fires on every structural case, the headline included. Its own number, about -0.53 MPa absolute at the LOX bottom, means the liquid column separates from the dome. The design takes the benefit of a gentle start (DLF about 1.06) but neither the cost nor the structure of a gentle stop. Avoiding the release step is not cheap. At 100 m and the rule's t_r = 1.061 s, ramping the drive down to 1 g felt before release costs +20.8% F_max (felt peak 4.83 g0) over t_r/2 and +51.5% (6.06 g0, above MECO's 5.195 g0, which would also size stage 2) over t_r. The flag sits in records and a summary column. Section 4.11's caveats-first list does not name it, and the note mentions 'the flags' only after the payload form.

Evidence: Design lines 211-215, 103, 371-386 (force law has a ramp-up only), 504-511; S08 line 65; S07 lines 309-313; scratch rampdown3.py (closed-form ramp-up/hold/ramp-down kinematics at L = 100 m, v_e = 76.70717 m/s)

Recommendation: Add a ramp-down to linear_motor (force back to the holding force over a stated t_r,down, then release) and a pre-registered variant flying it, so the structural and performance cost of a jerk-limited stop is measured. For constant_accel, state the estimated ramp-down cost beside the headline. Move the release flag and its number into the headline sentence and the caveats-first list: the push as modelled ends in a load step that the structural model itself says separates the LOX column.

## H4 [major] (4.2.2 structure_upper_stack_exceeded, D-SP7-13, 4.10 A (_st_step, stroke sweeps)) favours_assist=True

Issue: The step row (n_peak about 6.99 g0) and the 50 m stroke (7.0 g0 quasi-static) exceed the 5.195 g0 upper-stack envelope. Their dm therefore leaves out stage-2, interstage and adapter strengthening, and their x* is an upper bound. Yet the experiment table calls _st_step the 'step bound'. D-SP7-13 justifies leaving the upper stack unsized as 'dynamic or out-of-model', which is false for the quasi-static 50 m case. Stage 2's construction is public and the same as stage 1's (Table 2-1 uses the same wording), so the same closed forms apply. Both rows also exceed the Falcon User's Guide payload limit of +6.0 g, and nothing flags that. Short strokes therefore look better than they are in the depth comparison.

Evidence: Design lines 103, 207-210, 452-453 ('Q7's quasi-static value and step bound'), 461-463; S06 line 28 (Table 2-1 'same wording for stage 2'); S07 lines 257-269 (+6.0 g axial for payloads over 1,800 kg); S08 line 66 (n_peak 6.993 g0 at DLF 2); scratch rampstroke.py (50 m ramped felt 7.37 g0)

Recommendation: Either size the upper stack with the same closed forms (dm2 on stage-2 dry mass, reported separately), or label every flagged row 'x* is an upper bound (dm excludes the upper stack)' in the table, summary.md and the note, and keep those rows out of any depth trend. Rename the step row 'step (upper stack unsized)', not 'bound'. Add a flag at the published +6.0 g payload limit.

## H5 [major] (4.2.5 NOF) favours_assist=True

Issue: The design's NOF central is 1.5 and its range runs down to 1.0. In Wu's source the non-optimum factor depends on model fidelity: coarse models need 1.54-1.80 on barrels (SLWT average 1.80, acreage 1.54; Ares V coarse 1.54) and an average of 1.90 on bulkheads (1.28-2.76). Only a unit-cell model justifies 1.03. SP7's model is the coarsest kind (closed-form monocoque, smeared Gerard), and it leaves out Y-rings, frames, joints and weld lands (S08 section 9), so the average rather than the acreage value applies. NOF multiplies the whole membrane increment, so the low-mass corner at 1.0 is about 35% lighter than any coarse-model value supports, and the central sits at the bottom of the coarse range.

Evidence: S06 lines 215-218, 290, 320; S08 lines 227-229; design lines 196, 234

Recommendation: Apply the NOF by fidelity, as Wu does: barrels central 1.8 (SLWT average), range 1.54-1.9; domes central 1.9, range 1.28-2.76 (or the coarse range Wu reports). Record that NOF 1.0 is a unit-cell value that does not apply to this model. Fix this in the design, not in S0, so the choice is made before its effect on dm is known.

## H6 [major] (3.2 D-SP7-11, 4.2 envelope, 4.3 margin, D-SP7-03) favours_assist=True

Issue: The envelope is the model's unthrottled flight. MECO at 5.195 g0 governs the RP-1 barrel (n(U+LOX) = 7.095 MN, the element carrying the largest increment) and the LOX barrel, and it sets the upper-stack threshold. The Falcon guide says either stage may throttle to stay within acceleration limits. S05 recommended a MECO-envelope sensitivity, and the design dropped it. A lower envelope raises dm. At a 4.0 g0 cap, the n U envelope (5.46 MN) equals the push's quasi-static n U, so any DLF above 1 would exceed it and trigger the upper-stack flag on the headline. Meanwhile every envelope sensitivity in the design favours the assist: the 10% and 25% margin rows only lower dm, and the validator (margin >= 0) cannot express a lower envelope.

Evidence: S05 lines 277, 285, 296 (recommendation 6), 121-131; S07 line 271; design lines 101, 194-197, 281 ('margin >= 0'), 455; computed: U = 139,254 kg x 4.0 x 9.80665 = 5.46 MN against the push's 5.458 MN at 3.996 g0, and n_peak 4.18 g0 at DLF 1.06

Recommendation: Add a pre-registered envelope row: the pad envelope rebuilt with stage-1 acceleration capped at a stated, assumed value (for example 4.5 and 4.0 g0; the trajectory stays unthrottled). Report it beside the margin rows, so the sensitivities run both ways. Put the direction ('an unthrottled envelope favours the assist') in the caveats. Alternatively, allow a negative margin.

## H7 [major] (4.2.4 plausibility) favours_assist=True

Issue: The brief's commitment was that 'a large disagreement is reported and widens the band'. The design keeps only 'reported in the structure inputs; it changes no coefficient'. The table goes to metrics.json, and 4.11 has no plausibility section. A model whose envelope masses fall far from Heineman's +/-30% relation, or from 22.2 t less the engines, would therefore change nothing a reader sees. Within the model, the increment scales with the envelope thickness, so a model that is too light understates dm. The one safeguard that could only widen the band has been dropped.

Evidence: Brief docs/phases/SP7-structural-mass-push-load.md lines 365-367; design lines 228-231, 325, 504-511; S06 lines 92, 268 ('a first-order model may therefore come out heavy'); S08 lines 104-113

Recommendation: Fix the rule now. If the model's envelope mass for the sized elements (x NOF) falls outside the reference relation's stated range, the band is widened by the ratio, with the formula stated in the design and applied mechanically. Print the plausibility table in summary.md's Structure subsection, and give it its own section in the findings note.

## H8 [major] (4.2.3 load entry, D-SP7-14) favours_assist=True

Issue: k_entry may be the largest term and is the least sourced. Its central is anchored on 'the order of hold-down hardpoint structure per unit load', which has no source: S06 found no public mass for hold-down fittings. Its value is 'fixed in S0', after the probe showed it is the second-largest driver (k from 20 to 100 kg/MN moves the coupled x* from 27 to 18 t). The only sourced per-load relation, the thrust structure at 0.20-0.36 kg/kN (200-360 kg/MN), is made the high anchor, so the central must fall below it. The choice also decides which entry path looks lighter. At the probe's 50 kg/MN, the aft-ring hardware is about 1.0 t, against the thrust_structure row's 2.10 t x 1.53 = 3.2 t. At k_entry = k_ts, the aft ring is about 5.3 t plus the skirt.

Evidence: Design lines 104, 217-226, 606; S06 lines 3, 84, 93-94, 229, 267, 286-289; S08 lines 186, 204-206

Recommendation: State k_entry's central rule in this design, before S0 and independent of its effect on x*. For example, take the thrust-structure relation as central, since the ring gathers the whole push, with a closed-form annular ring in bearing as the low end. Say in the pre-registration that S0's values were set after the probe. Give the aft_ring and thrust_structure rows equal prominence in the headline, and do not present the central path as the more likely one.

## H9 [major] (3.2 D-SP7-15, 4.2.5 corner band) favours_assist=True

Issue: The band label, 'the bounds of the stated coefficient ranges, all at once', is not guaranteed by the method. (a) A 2^k corner search misses interior extrema: S08's stiffened case gives 1,932, 1,972 and 1,804 kg at p_u = 2.5, 3.5 and 4.5 bar, so the maximum is interior. (b) The sets are frozen at SP1's headline push and reused for the 50-300 m strokes, the linear-motor variants and the full-load row. The governing modes change with n (hoop at 2 g0, buckling at 7 g0), so the sets do not bound dm at those pushes. (c) With about 22-24 coefficients, 2^k is 4-17 million sizings, each recomputing the envelope over thousands of samples, not 'seconds' (70 min to 4.7 h even at 1 ms each). An implementer facing that will prune without any stated rule.

Evidence: Design lines 105, 233-242; S08 lines 141-149 (stiffened 3x row; the sign flips by form), 164-172; arithmetic: 2^22 = 4.19e6, 2^24 = 1.68e7

Recommendation: State the search now. Fix monotone coefficients at their directional end (from the tornado's sign, checked across the full range). For the non-monotone ones (p_u, t_min, any whose sign flips) search a grid that includes the central and interior points, or a bounded optimizer from several starts. Recompute the extremal sets at each sweep point and drive case (sizing only, cheap), or label the band 'the sets that bound dm at the headline push; not bounds at other pushes'. Have the band line in summary.md name what lies outside it: t_r, the entry path, the sizing basis and the margin.

## H10 [major] (4.10 pre-registration, 6 item 7, 8) favours_assist=True

Issue: The readings that decide the honesty of the result have no fixed trigger. 'A band wider than the offload' could mean the range exceeds the central x*, or the high-mass end reaching zero, and 'plainly whether the structure cancels most of the offload' has no threshold. With the DLF capped by the rule (H1), the band is unlikely to trigger the 'cannot decide' sentence, while the step row (0-20 t in the probe) would. Yet no reading is fixed for the bound rows.

Evidence: Design lines 496-499, 576-577, 605; S09 line 178 onward (item 4); S08 lines 213-220

Recommendation: Pre-register numeric triggers. For example, 'cannot decide' if x*_high-mass <= 0 or (x*_low - x*_high) >= x*_central; 'cancels most' if x*_central < 0.5 x 41,262.9 kg. Apply the same tests, each with its own fixed sentence, to the step, full_load, thrust_structure and throttled-envelope rows, and report every sentence that fires in the note's headline.

## H11 [major] (5 S2-S6, 6 item 2) favours_assist=True

Issue: Nothing keeps the structural headline unseen before the pre-registration, or keeps the coefficients frozen after S2. S3's tests ('xv_dry_mass_delta_kg = dm(x*)', the payload two-pass check, memo separation) need structural solves. If they run on the gate vehicle with the central file, the headline x* is known before S6. The structure file's values (S0 central, S2 sets) have no freeze gate. Exit criterion 2 checks only that the file validates, and S3-S5 may edit it to make tests pass.

Evidence: Design lines 535-536, 543-544, 555-557; S09 lines 48 and 144-170 (SP1 template: 'the headline is not unknown' section, amendment rule)

Recommendation: S3-S5 tests use synthetic structure coefficients or a short vehicle, never the pre-registered cases. Any pre-registered case solved before S6 is listed under 'what is already known'. Gate S6 and S7 on `git diff --quiet <S2 commit> -- configs/structures/`; any change is a logged amendment. In the pre-registration, state that S0's central values were chosen after the probe, with the rule behind each.

## H12 [major] (4.4 payload form, 4.5 wording) favours_assist=False

Issue: The three-way wording keys on 'the run's own record', but every page reaches that record through `replay.case_record`, which returns None for any run that is not an offload case's recorded run. The payload-case runs are explicitly 'a new record kind in the structure section, never under the offload heading', so `uncharged_structure_sentence` and `scene.structure_note` would print 'No structural mass is charged' on runs that charged one. Sweep points and sensitivity arms of structural cases need the same lookup. The modelled sentence says 'with a band', but not the band's ends or the run's own flags (release, upper stack). The compare.py docstring calls the dry-mass delta 'an assumed structural penalty', which becomes false for a modelled dm.

Evidence: src/launchsim/replay.py:902-911 (case_record), 948-976, 1011-1044; src/launchsim/scene.py:1296-1314; src/launchsim/compare.py:1417-1421; design lines 313-317, 341-349

Recommendation: Branch on a run-level field written into every structural run's own metrics (for example `structure_charged`, `structure_dm_kg`), whatever kind the run is. Add one test per run kind: solved case, payload case, arm, sweep point. Make the modelled sentence carry the band's ends (from structure_inputs) and the run's flags. Fix the compare.py docstring.

## H13 [major] (4.11 findings note, 4.4 summary) favours_assist=True

Issue: The caveats-first list leaves out the conditions the headline actually rests on: the release flag on every case; the upper-stack and payload-limit flags on the bound rows; the flown-stack sizing basis; the unthrottled-envelope direction; the NOF basis; and what the band excludes (t_r, the entry path, the sizing basis, the margin). As planned, the note could print a central x* with a 'band' and no condition sentence beside it.

Evidence: Design lines 504-511, 329-334

Recommendation: Fix the headline sentence's form now. It should say: with a first-order structure, assuming a jerk-limited start the constant_accel trajectory does not fly and no ramp-down (the release step separates the LOX column), sized for the offloaded stack, against the model's unthrottled envelope and an assumed load-entry coefficient, the central offload is X t (band [a, b] over the stated ranges); the step drive gives at most y t, an upper bound. List the flags and the band's exclusions in the caveats-first block.

## H14 [minor] (3.1 D-SP7-02, 4.4, 4.11) favours_assist=True

Issue: The headline uses the favourable sizing basis: the structure is sized for the offloaded stack flown, which the user chose. That vehicle cannot be pushed with full tanks, and the payload form re-sizes for full tanks, so no single vehicle realises both the offload headline and the payload result. The design does not require the headline sentence to say so.

Evidence: Design lines 87, 297-298, 313-317; S08 line 218 (full-load bound 0.6-2.6 t below coupled)

Recommendation: State in the headline sentence and in each modelled caveat that the structure is sized for the offloaded stack only, with the full-load row beside it at equal prominence. Say that the payload form uses a different, full-tank structure.

## H15 [minor] (4.10 B linear-motor rule) favours_assist=True

Issue: F_max is sized for the full-load vehicle (572,354.4 kg), so the offloaded stack at SP1's x feels about 4.31 g0, against constant_accel's 3.996 g0. lm_cold_atL also exits faster than 76.7 m/s. Any constant_accel-versus-linear-motor difference therefore mixes the drive model with a different push and a different exit speed. Read as 'what a realistic drive gives', lm_cold_atL's extra offload from extra speed would favour the assist.

Evidence: Design lines 470-482; computed: 3.9965 x 572,354.4 / 531,091.5 = 4.31 g0 (S08 line 13 stack mass)

Recommendation: Make lm_cold_target (same exit speed) the like-for-like comparison. Attribute lm_cold_atL's difference to exit speed and to felt g separately, using the decomposition, and state in the note that the rule sets those differences.

## H16 [minor] (4.2.3, 4.2.5 sources) favours_assist=True

Issue: Two numbers rest on sources the surveys could not open. k_ts's central 0.255 kg/kN comes from a search summary only (Akin; S06 marks it 'Q (central)'). F_tu's high end of 590 MPa comes from makeitfrom.com, which S06 itself says not to cite, and the low-mass corner would rest on it.

Evidence: S06 lines 93-94, 109, 295, 309, 331; design lines 222-223

Recommendation: Take k_ts's central from the opened Castellini range (midpoint about 0.28 kg/kN), with 0.255 as a quoted cross-check. Take F_tu's high end from an opened source, or mark it assumed with a stated reason.

## H17 [minor] (4.10 C bridge, 4.3) favours_assist=False

Issue: The README-loads bridge gets its own structure file. That is a second set of coefficients, which could diverge from the gate file's without anything noticing.

Evidence: Design lines 139, 246-248, 485-486

Recommendation: Add a test that every coefficient not derived from the vehicle is identical in the two structure files, and record any deliberate difference as a decision.

## H18 [minor] (5 'If room runs out') favours_assist=True

Issue: The cut order drops the low-mass and high-mass stroke sweeps before the margin rows. Margin rows only lower dm, so the rows that favour the assist would be kept while the depth question loses its band.

Evidence: Design lines 547-549

Recommendation: Cut the margin rows before the band sweeps. If the band sweeps are cut anyway, pre-register that the depth reading then reports only the central trend and claims nothing about robustness.
